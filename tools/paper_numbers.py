"""Makalede gecen tum turetilmis sayilari tek yerden uretir.

Amac: Results bolumundeki her rakamin summary.csv'den yeniden
uretilebilir olmasi (reproducibility audit iddiasinin geregi).
"""
import os
from pathlib import Path

import pandas as pd

os.chdir(Path(__file__).resolve().parent.parent)

df = pd.read_csv("results/summary.csv")
df["dnf"] = df["timed_out"].astype(str).str.lower() == "true"
df["crash"] = df["error"].notna()
df["ok"] = ~df["dnf"] & ~df["crash"]

CAT = {1: "transactional", 2: "sequential", 3: "high-utility", 5: "rare/stream"}

print("=" * 78)
print("OVERALL")
print("=" * 78)
n = len(df)
print("scheduled runs      : %d" % n)
print("completed           : %d (%.1f%%)" % (df.ok.sum(), 100 * df.ok.mean()))
print("DNF (>3600s)        : %d (%.1f%%)" % (df.dnf.sum(), 100 * df.dnf.mean()))
print("crashed (OOM)       : %d (%.1f%%)" % (df.crash.sum(), 100 * df.crash.mean()))
print("algorithms executed : %d" % df.algorithm.nunique())
print("datasets            : %d  %s" % (df.dataset.nunique(), sorted(df.dataset.unique())))

print("\n" + "=" * 78)
print("PER ALGORITHM (means over successful runs only)")
print("=" * 78)
g = df.groupby(["category", "algorithm"]).agg(
    runs=("ok", "size"), ok=("ok", "sum"), dnf=("dnf", "sum"), crash=("crash", "sum"),
).reset_index()
o = df[df.ok].groupby(["category", "algorithm"]).agg(
    mean_rt=("runtime_s", "mean"), max_rt=("runtime_s", "max"),
    mean_mem=("peak_memory_mb", "mean"), max_mem=("peak_memory_mb", "max"),
).reset_index()
g = g.merge(o, on=["category", "algorithm"], how="left").sort_values(["category", "mean_rt"])
print("%-22s %-4s %4s %4s %5s %10s %10s %9s %9s"
      % ("algorithm", "cat", "runs", "ok", "dnf", "mean_rt", "max_rt", "mean_mem", "max_mem"))
for _, r in g.iterrows():
    print("%-22s %-4d %4d %4d %5d %10.2f %10.1f %9.1f %9.1f"
          % (r.algorithm, r.category, r.runs, r.ok, r.dnf,
             r.mean_rt, r.max_rt, r.mean_mem, r.max_mem))

print("\n" + "=" * 78)
print("PER CATEGORY")
print("=" * 78)
for c, sub in df.groupby("category"):
    print("cat %d (%-13s): %3d runs, %3d ok (%.1f%%), %2d DNF, %d crash, %d algos"
          % (c, CAT.get(c, "?"), len(sub), sub.ok.sum(), 100 * sub.ok.mean(),
             sub.dnf.sum(), sub.crash.sum(), sub.algorithm.nunique()))

print("\n" + "=" * 78)
print("DNF BY DATASET (transactional, cat 1+5)")
print("=" * 78)
t = df[df.category.isin([1, 5])]
piv = t.pivot_table(index="algorithm", columns="dataset", values="dnf", aggfunc="sum")
print(piv.fillna(0).astype(int).to_string())

print("\n" + "=" * 78)
print("GENERATOR-COUNT AGREEMENT (transactional, per dataset/threshold)")
print("=" * 78)
# Bos kume konvansiyonu.  Bos kumenin destegi |D|'dir ve tanim geregi bir
# jeneratördür; DefMe/Zart/Gr-growth/TalkyG bunu da yazar, Pascal ve Borgelt
# yazmaz.  ONEMLI: TalkyG bu konuda TUTARSIZ -- bos kumeyi yalnizca veri
# kumesinde TAM DESTEKLI (support = |D|) bir oge YOKKEN yaziyor.  mushroom'da
# oge 90 tum 8416 islemde bulundugu icin TalkyG orada bos kumeyi atliyor;
# diger alti veri kumesinde yaziyor.  Bu yuzden ofset implementasyon basina
# degil, KONFIGURASYON basina hesaplanmalidir (bkz. makale, sec:validation).
COUNTS_EMPTY_SET = {"DefMe", "Zart", "Gr_growth", "Talky_G", "TalkyG_Diffset"}
# Tam destekli oge iceren veri kumeleri -> TalkyG bos kumeyi yazmaz.
FULL_SUPPORT_ITEM_DATASETS = {"mushroom"}

d1 = df[(df.category == 1) & df.ok].copy()


def empty_set_offset(row) -> int:
    if row.algorithm not in COUNTS_EMPTY_SET:
        return 0
    if (row.algorithm in {"Talky_G", "TalkyG_Diffset"}
            and row.dataset in FULL_SUPPORT_ITEM_DATASETS):
        return 0
    return 1


d1["norm"] = d1.generator_count - d1.apply(empty_set_offset, axis=1)

# Talky-G'nin fazla uretimi ayri bir bulgu; anlasma testinden haric tutulur.
ref = d1[~d1.algorithm.isin({"Talky_G", "TalkyG_Diffset"})]
a = ref.pivot_table(index=["dataset", "param_value"], columns="algorithm", values="norm")
multi = a.notna().sum(axis=1) > 1
disagree = [(i, r.dropna().to_dict()) for i, r in a[multi].iterrows()
            if r.dropna().nunique() > 1]
print("configs with >1 algorithm reporting: %d" % multi.sum())
print("configs where counts DISAGREE     : %d" % len(disagree))
for i, vals in disagree[:10]:
    print("   %s -> %s" % (i, vals))

tg = d1[d1.algorithm == "Talky_G"].set_index(["dataset", "param_value"]).norm
base = a.median(axis=1)
both = tg.index.intersection(base.index)
extra = (tg.loc[both] - base.loc[both])
print("")
print("Talky-G excess over consensus: %d configs, %d exact, max +%d"
      % (len(both), (extra == 0).sum(), extra.max()))
print("\nmushroom rows (illustrative):")
print(a.loc["mushroom"].to_string())
