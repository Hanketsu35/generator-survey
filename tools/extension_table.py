"""Numbers for the paper's Table tab:extension and the claims next to it.

    python tools/extension_table.py [--exact]

Reads the first and second extension (results/real_extra_summary.csv, role
"extension"; results/real_extra2_summary.csv), or their exact-memory copies
in results/exact/ with --exact.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "results" / ("exact" if "--exact" in sys.argv else "")
BORG = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt"]
SPMF = ["DefMe", "Pascal", "Zart", "Talky_G", "TalkyG_Diffset"]
ST1 = ["bms1", "bms2", "c20d10k", "c73d10k", "kosarak"]
ST2 = ["chicago", "kddcup99", "onlineretail", "pamap", "recordlink"]


def rng(x):
    x = x.dropna()
    if x.empty:
        return "-"
    lo, hi = x.min(), x.max()
    f = lambda v: "{:,.0f}".format(v)                      # noqa: E731
    return f(lo) if f(lo) == f(hi) else "%s--%s" % (f(lo), f(hi))


def main():
    a = pd.read_csv(D / "real_extra_summary.csv")
    a = a[a.role == "extension"]
    t = pd.concat([a, pd.read_csv(D / "real_extra2_summary.csv")])
    t = t[t.algorithm.isin(BORG + SPMF + ["Gr_growth"])]
    ok = (t.timed_out.astype(str).str.lower() != "true") & t.error.isna()
    c = t[ok]
    small_cmp = []
    for ds in ST1 + ST2:
        g, gc = t[t.dataset == ds], c[c.dataset == ds]
        gr = gc[gc.algorithm == "Gr_growth"].set_index("param_value").peak_memory_mb
        b = gc[gc.algorithm.isin(BORG)].groupby("param_value").peak_memory_mb.min()
        both = gr.index.intersection(b.index)
        ratio = (b[both] / gr[both])
        print("%-12s done %d/%d | Gr %s | Borgelt %s | SPMF %s | B/Gr %.2f--%.2f"
              % (ds, len(gc), len(g), rng(gr), rng(gc[gc.algorithm.isin(BORG)].peak_memory_mb),
                 rng(gc[gc.algorithm.isin(SPMF)].peak_memory_mb), ratio.min(), ratio.max()))
        if ds in ("bms1", "bms2", "c20d10k", "c73d10k"):
            small_cmp += [(ds, s, r) for s, r in ratio.items()]
    s = pd.DataFrame(small_cmp, columns=["ds", "sigma", "ratio"])
    print("small datasets: Borgelt below Gr on %d of %d thresholds; min ratio %.2f (%s); exceptions: %s"
          % ((s.ratio < 1).sum(), len(s), s.ratio.min(), s.loc[s.ratio.idxmin(), "ds"],
             s[s.ratio >= 1][["ds", "sigma"]].values.tolist()))
    big = c[c.dataset.isin(["chicago", "kddcup99", "onlineretail", "recordlink"])]
    bb = big[big.algorithm.isin(BORG)].groupby(["dataset", "param_value"]).peak_memory_mb.min()
    print("stage-2 (no pamap): Gr %s | best Borgelt %s | SPMF %s"
          % (rng(big[big.algorithm == "Gr_growth"].peak_memory_mb), rng(bb),
             rng(big[big.algorithm.isin(SPMF)].peak_memory_mb)))


if __name__ == "__main__":
    main()
