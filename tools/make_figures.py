"""Figures of the KBS paper (gap G7, kbs/GAPS.md).

    python tools/make_figures.py

  kbs/figures/crossing.pdf   lowest Borgelt peak / Gr-growth peak against the
                             number of transactions (exact training table)
  kbs/figures/regret.pdf     memory regret per method on PRIMARY
                             (results/baseline_rows.csv, baseline2_rows.csv)
  kbs/figures/coverage.pdf   per-dataset interval coverage, FRESH7 and FRESH8
"""
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
import numpy as np                                         # noqa: E402
import pandas as pd                                        # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)
OUT = _ROOT / "kbs" / "figures"
BORGELT = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt"]

plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "pdf.fonttype": 42})


def crossing():
    d = pd.read_csv("results/exact/training_all.csv")
    ok = (d.timed_out.astype(str).str.lower() != "true") & d.error.isna()
    d = d[ok & (d.category == 1)]
    sys.path.insert(0, str(_ROOT / "tools"))
    import probe_eval as PE
    ntx = {}
    rows = []
    for (ds, sg), g in d.groupby(["dataset", "param_value"]):
        gr = g[g.algorithm == "Gr_growth"].peak_memory_mb
        b = g[g.algorithm.isin(BORGELT)].peak_memory_mb
        if len(gr) and len(b):
            if ds not in ntx:
                try:
                    with open(PE.dataset_path(ds)) as fh:
                        ntx[ds] = sum(1 for line in fh if line.strip())
                except (OSError, KeyError):
                    ntx[ds] = None
            n = ntx[ds]
            if n is None:
                continue
            rows.append((n, b.min() / gr.iloc[0]))
    r = np.array(rows)
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.scatter(r[:, 0], r[:, 1], s=6, alpha=0.55, color="#1f4e79", linewidths=0)
    ax.axhline(1.0, color="0.3", lw=0.8, ls="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("transactions in the file")
    ax.set_ylabel("best Borgelt peak / Gr-growth peak")
    fig.tight_layout()
    fig.savefig(OUT / "crossing.pdf", bbox_inches="tight")
    print("crossing: %d instances, %d datasets" % (len(r), len(ntx)))


def regret():
    d = pd.read_csv("results/baseline_rows.csv")
    d = d[(d.objective == "memory") & d.primary & d["recommender, probe"].notna()]
    cols = {"recommender, probe": "recommender + probe", "ISAC (k-means clusters)": "ISAC",
            "AutoFolio (SMAC, 1800s/fold)": "AutoFolio", "pairwise ranking": "pairwise",
            "regression (PAR10-imputed)": "regression", "SUNNY (k-NN, k=16)": "SUNNY",
            "recommender, no probe": "recommender, no probe", "survival (expected_par10)": "survival",
            "SBS (fixed choice)": "SBS"}
    data = {v: d[k].values for k, v in cols.items()}
    p2 = _ROOT / "results" / "baseline2_rows.csv"
    if p2.exists():
        b = pd.read_csv(p2)
        b = b[b.primary]
        data = {"probe-argmin": b["probe-argmin"].values, **data}
        best = [c for c in b.columns if c.endswith("+probe")]
        if best:
            m = min(best, key=lambda c: np.exp(np.log(b[c]).mean()))
            data = {**{k: v for k, v in data.items() if k in ("probe-argmin", "recommender + probe")},
                    m.split(" (")[0].replace(" +probe", "") + " + probe features": b[m].values,
                    **{k: v for k, v in data.items() if k not in ("probe-argmin", "recommender + probe")}}
    names = list(data)[::-1]
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for i, k in enumerate(names):
        v = np.minimum(data[k], 10.0)
        y = i + (np.random.default_rng(i).random(len(v)) - 0.5) * 0.5
        ax.scatter(v, y, s=3, alpha=0.35, color="#1f4e79", linewidths=0)
        g = float(np.exp(np.log(data[k]).mean()))
        ax.plot([g, g], [i - 0.35, i + 0.35], color="#c00000", lw=1.4)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xscale("log")
    ax.set_xlim(0.95, 11)
    ax.set_xticks([1, 1.5, 2, 3, 5, 10])
    ax.set_xticklabels(["1", "1.5", "2", "3", "5", "10 (failed)"])
    ax.set_xlabel("memory regret")
    fig.tight_layout()
    fig.savefig(OUT / "regret.pdf", bbox_inches="tight")
    print("regret: %d methods" % len(names))


def coverage():
    a = pd.read_csv("results/fresh7_eval_rows.csv")
    b = pd.read_csv("results/fresh8_eval_rows.csv")
    kinds = [("X1 model runtime", a, "model runtime (95%)"), ("X2 model memory", a, "model memory (95%)"),
             ("X3 probe memory, measured", a, "probe, measured (95%)"),
             ("Y1 probe memory, sampled (primary)", b, "probe, sampled (90%)")]
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    for i, (k, t, lab) in enumerate(kinds):
        q = t[t.kind == k]
        if q.empty:
            q = t[t.kind.str.startswith(k.split()[0])]
        per = q.groupby("dataset").hit.mean().values
        lev = float(q.level.iloc[0])
        y = i + (np.random.default_rng(i).random(len(per)) - 0.5) * 0.4
        ax.scatter(per, y, s=9, alpha=0.6, color="#1f4e79", linewidths=0)
        ax.plot([per.mean()] * 2, [i - 0.3, i + 0.3], color="#c00000", lw=1.4)
        ax.plot([lev] * 2, [i - 0.4, i + 0.4], color="0.2", lw=0.9, ls=":")
    ax.set_yticks(range(len(kinds)))
    ax.set_yticklabels([k[2] for k in kinds])
    ax.set_xlim(0.55, 1.02)
    ax.set_xlabel("coverage per dataset")
    fig.tight_layout()
    fig.savefig(OUT / "coverage.pdf", bbox_inches="tight")
    print("coverage done")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    crossing()
    regret()
    coverage()
