"""Every number the paper's result text quotes, from one table.

    python tools/paper_numbers_detail.py --table results/summary_linux.csv

tools/paper_numbers.py gives the aggregate tables; this gives the derived
figures quoted in the running text and the figures (per-configuration
values, ratios, "on X of N configurations" counts), so that none of them is
computed by hand when the table changes.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLE = sys.argv[sys.argv.index("--table") + 1] if "--table" in sys.argv else "results/summary.csv"
d = pd.read_csv(ROOT / TABLE, dtype={"generator_count": str})
d["dnf"] = d.timed_out.astype(str).str.lower() == "true"
d["crash"] = d.error.notna()
d["ok"] = ~d.dnf & ~d.crash
d["gc"] = pd.to_numeric(d.generator_count, errors="coerce")
print("table:", TABLE)


def cell(a, ds, p, col="runtime_s"):
    r = d[(d.algorithm == a) & (d.dataset == ds) & np.isclose(d.param_value, p)]
    if r.empty:
        return "n/a"
    r = r.iloc[0]
    tag = "" if r.ok else (" DNF" if r.dnf else " CRASH")
    return "%.3f%s" % (r[col], tag) if pd.notna(r[col]) else "nan" + tag


c1 = d[d.category == 1]
ok1 = c1[c1.ok]

print("\n== CHESS FIGURE (runtime s / memory MB per sigma)")
for a in ["FPgrowth_Gen_Borgelt", "Gr_growth", "DefMe", "TalkyG_Diffset", "Talky_G",
          "Pascal", "Zart", "Eclat_Gen_Borgelt", "Apriori_Gen_Borgelt"]:
    for col in ("runtime_s", "peak_memory_mb"):
        vals = []
        for s in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            r = d[(d.algorithm == a) & (d.dataset == "chess") & np.isclose(d.param_value, s)]
            if r.empty:
                continue
            r = r.iloc[0]
            v = 3600 if (r.dnf and col == "runtime_s") else r[col]
            vals.append("(%.1f,%s)" % (s, ("%.3f" % v) if col == "runtime_s" else ("%.2f" % v)))
        print("  %-22s %-15s %s" % (a, col, "".join(vals)))

print("\n== TRANSACTIONAL TEXT")
m = ok1.groupby("algorithm").agg(rt=("runtime_s", "mean"), mem=("peak_memory_mb", "mean"))
print("  Gr/DefMe runtime ratio  DefMe/Gr = %.2f ; memory DefMe/Gr = %.1f"
      % (m.rt["DefMe"] / m.rt["Gr_growth"], m.mem["DefMe"] / m.mem["Gr_growth"]))
print("  DefMe vs TalkyG runtime: TalkyG/DefMe = %.2f, Diffset/DefMe = %.2f"
      % (m.rt["Talky_G"] / m.rt["DefMe"], m.rt["TalkyG_Diffset"] / m.rt["DefMe"]))
for a in ("FPgrowth_Gen_Borgelt", "Eclat_Gen_Borgelt", "Gr_growth", "DefMe"):
    print("  chess 0.2 %-22s rt %s  mem %s" % (a, cell(a, "chess", 0.2), cell(a, "chess", 0.2, "peak_memory_mb")))
for a in ("Pascal", "Talky_G", "TalkyG_Diffset", "Zart"):
    print("  chess 0.2 %-22s rt %s  mem %s" % (a, cell(a, "chess", 0.2), cell(a, "chess", 0.2, "peak_memory_mb")))
print("  TalkyG_Diffset chess 0.3:", cell("TalkyG_Diffset", "chess", 0.3), "| Talky_G chess 0.3:", cell("Talky_G", "chess", 0.3))
w = ok1.pivot_table(index=["dataset", "param_value"], columns="algorithm", values="peak_memory_mb")
three = w[["DefMe", "Talky_G", "TalkyG_Diffset"]].dropna()
print("  configs all three complete: %d ; TalkyG plain uses less memory than DefMe on %d, diffset on %d, both on %d"
      % (len(three), (three.Talky_G < three.DefMe).sum(), (three.TalkyG_Diffset < three.DefMe).sum(),
         ((three.Talky_G < three.DefMe) & (three.TalkyG_Diffset < three.DefMe)).sum()))
dnf = c1[c1.dnf | c1.crash]
pz = dnf[dnf.algorithm.isin(["Pascal", "Zart"])]
common = set(map(tuple, pz[pz.algorithm == "Pascal"][["dataset", "param_value"]].values)) & \
    set(map(tuple, pz[pz.algorithm == "Zart"][["dataset", "param_value"]].values))
print("  Pascal & Zart both fail on:", sorted(common))
print("  Pascal/Zart failures on t10i4d100k:", len(pz[pz.dataset == "t10i4d100k"]))

print("\n== LIMITATIONS: spread slowest/fastest completer per transactional config")
rt = ok1.pivot_table(index=["dataset", "param_value"], columns="algorithm", values="runtime_s")
spread = rt.max(axis=1) / rt.min(axis=1)
print("  configs %d ; spread >= 10x on %d ; median spread %.0fx" % (len(spread), (spread >= 10).sum(), spread.median()))
top4 = ["FPgrowth_Gen_Borgelt", "Eclat_Gen_Borgelt", "Gr_growth", "DefMe"]
print("  aggregate factor among four fastest (max/min of means): %.1f" % (m.rt[top4].max() / m.rt[top4].min()))
c02 = rt.loc[("chess", 0.2), top4]
print("  chess 0.2 four fastest factor: %.2f" % (c02.max() / c02.min()))
win = rt.apply(lambda r: sorted(r.dropna())[:2], axis=1)
ratio = win.apply(lambda v: v[1] / v[0] if len(v) > 1 else np.nan)
print("  max runner-up/winner ratio over configs: %.2f" % ratio.max())
print("  mean runtime FP %.3f  Gr %.3f  Eclat %.3f ; Gr faster than FP on %d of %d configs"
      % (m.rt["FPgrowth_Gen_Borgelt"], m.rt["Gr_growth"], m.rt["Eclat_Gen_Borgelt"],
         (rt.Gr_growth < rt.FPgrowth_Gen_Borgelt).sum(), rt[["Gr_growth", "FPgrowth_Gen_Borgelt"]].dropna().shape[0]))

print("\n== SEQUENTIAL")
c2 = d[(d.category == 2) & d.ok]
for a in ("FEAT", "FSGP", "VGEN"):
    print("  %-5s sign 0.015 rt %s" % (a, cell(a, "sign", 0.015)))
v = c2[c2.algorithm == "VGEN"]
print("  VGEN peak: %.1f MB at %s %s" % (v.peak_memory_mb.max(), v.loc[v.peak_memory_mb.idxmax(), "dataset"], v.loc[v.peak_memory_mb.idxmax(), "param_value"]))
print("  per-dataset mean memory:")
print(c2.groupby(["dataset", "algorithm"]).peak_memory_mb.mean().unstack().round(1).to_string())
sg = c2[c2.dataset == "sign"].groupby("algorithm").runtime_s.mean()
print("  sign mean runtime:", sg.round(2).to_dict())
lb = c2[c2.dataset.isin(["leviathan", "bible"])].pivot_table(index=["dataset", "param_value"], columns="algorithm", values="runtime_s")
print("  degenerate datasets max within-config factor: %.2f" % (lb.max(axis=1) / lb.min(axis=1)).max())
mm = c2.groupby("algorithm").runtime_s.mean()
print("  FEAT/FSGP mean runtime ratio %.2f" % (mm["FEAT"] / mm["FSGP"]))

print("\n== HIGH UTILITY")
c3 = d[d.category == 3]
print(c3[c3.ok].groupby("algorithm").agg(rt=("runtime_s", "mean"), mem=("peak_memory_mb", "mean"),
                                          out=("gc", "mean"), n=("ok", "size")).round(3).to_string())
print(c3.pivot_table(index=["dataset", "param_value"], columns="algorithm", values="peak_memory_mb").round(1).to_string())
print(c3.pivot_table(index=["dataset", "param_value"], columns="algorithm", values="runtime_s").round(3).to_string())

print("\n== RARE / STREAM")
for a in ("Arima", "FGC_Stream"):
    q = d[d.algorithm == a]
    print("  %s: ok %d dnf %d crash %d of %d | mean rt %.1f mem %.1f out %.1fk"
          % (a, q.ok.sum(), q.dnf.sum(), q.crash.sum(), len(q), q[q.ok].runtime_s.mean(),
             q[q.ok].peak_memory_mb.mean(), q[q.ok].gc.mean() / 1e3))
    print(q.pivot_table(index="dataset", columns="param_value", values="runtime_s", aggfunc="first").round(1).to_string())
    bad = q[~q.ok][["dataset", "param_value", "runtime_s", "peak_memory_mb", "dnf", "crash"]]
    print(bad.to_string())
