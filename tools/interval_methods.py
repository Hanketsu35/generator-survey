"""Compare interval calibrations by leave-one-group-out over the group pool.

    python tools/interval_methods.py

Methods (Dunn, Wasserman & Ramdas, JASA 2023, "Distribution-free prediction
sets for two-layer hierarchical models"):
  M0 pooled runs        quantiles of all residuals, level tightened by k/(k+1)
                        (what recommender/intervals.py did)
  M1 CDF pooling        quantiles of the average of the per-group empirical
                        CDFs (every dataset weighs the same)
  M2 subsample once     one residual per group, order statistics
                        floor((k+1)a/2), ceil((k+1)(1-a/2)); averaged over seeds
  M3 repeated subsample B subsamples of one residual per group, p-values
                        averaged; guaranteed 1-2a, about 1-a in practice
For each held-out group g the interval is calibrated on the other groups and
its coverage measured on g's runs. Output: results/interval_methods.csv
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_ROOT)
RT_FLOOR = 0.01
B = 200


def m0(groups, a):
    x = np.concatenate(groups)
    k = len(groups)
    aa = a * k / (k + 1.0)
    return np.quantile(x, aa / 2), np.quantile(x, 1 - aa / 2)


def m1(groups, a):
    x = np.concatenate(groups)
    w = np.concatenate([np.full(len(g), 1.0 / len(g)) for g in groups])
    o = np.argsort(x)
    x, c = x[o], np.cumsum(w[o]) / w.sum()
    lo = x[min(np.searchsorted(c, a / 2), len(x) - 1)]
    hi = x[min(np.searchsorted(c, 1 - a / 2), len(x) - 1)]
    return lo, hi


def _sub(groups, rng):
    return np.sort([g[rng.integers(len(g))] for g in groups])


def m2(groups, a, seed=0):
    rng = np.random.default_rng(seed)
    k = len(groups)
    r, s = int(np.floor((k + 1) * a / 2)), int(np.ceil((k + 1) * (1 - a / 2)))
    los, his = [], []
    for _ in range(B):
        y = _sub(groups, rng)
        los.append(y[r - 1] if r >= 1 else -np.inf)
        his.append(y[s - 1] if s <= k else np.inf)
    return float(np.mean(los)), float(np.mean(his))     # average endpoint over draws


def m3(groups, a, seed=0):
    rng = np.random.default_rng(seed)
    k = len(groups)
    subs = np.array([_sub(groups, rng) for _ in range(B)])          # B x k, sorted
    cand = np.unique(np.concatenate(groups))
    # p-value of u in subsample b: 2 (m + 1) / (k + 1), m = points on u's far side
    below = (subs[:, :, None] <= cand[None, None, :]).sum(axis=1)   # B x C
    above = (subs[:, :, None] >= cand[None, None, :]).sum(axis=1)
    m = np.minimum(below, above)
    pv = np.minimum(1.0, 2.0 * m / (k + 1.0)).mean(axis=0)           # m counts u's side incl. ties
    keep = cand[pv >= a]
    if keep.size == 0:
        return -np.inf, np.inf
    return keep.min(), keep.max()


METHODS = {"M0 pooled": m0, "M1 CDF pooling": m1, "M2 subsample": m2, "M3 repeated": m3}


def main():
    d = pd.read_csv(_ROOT / "results" / "interval_groups.csv")
    d["mem"] = np.log10(d.true_mem / d.pred_mem)
    d["rt"] = np.log10(np.maximum(d.true_rt, RT_FLOOR) / np.maximum(d.pred_rt, RT_FLOOR))
    rows = []
    for col in ("mem", "rt"):
        gs = {g: v[col].values for g, v in d.groupby("dataset")}
        for a in (0.10, 0.05):
            for name, f in METHODS.items():
                for g, test in gs.items():
                    cal = [v for h, v in gs.items() if h != g]
                    lo, hi = f(cal, a)
                    rows.append({"target": col, "alpha": a, "method": name, "dataset": g,
                                 "source": d[d.dataset == g].source.iloc[0],
                                 "coverage": float(((test >= lo) & (test <= hi)).mean()),
                                 "width": float(10 ** (hi - lo)) if np.isfinite(hi - lo) else np.inf})
    r = pd.DataFrame(rows)
    r.to_csv(_ROOT / "results" / "interval_methods.csv", index=False)
    for (col, a), q in r.groupby(["target", "alpha"]):
        print("== %s, nominal %.0f%%, %d groups" % (col, 100 * (1 - a), q.dataset.nunique()))
        for name, z in q.groupby("method"):
            un = z[z.source != "training LODO"]
            print("   %-16s mean group coverage %.3f (unseen-after-training groups %.3f) | groups >= nominal %2d/%d | min %.2f | median width x%.1f"
                  % (name, z.coverage.mean(), un.coverage.mean(), (z.coverage >= 1 - a).sum(), len(z),
                     z.coverage.min(), z.width.median()))


if __name__ == "__main__":
    main()
