"""Does the ENGINE's memory ranking share the volatility the jackknife found?

The training jackknife in NOTES section 8 compared the selectors of
bench_selectors.py and found regression volatile on memory (nPAR10 0.009-0.853
over 39 refits) and pairwise ranking stable (0.143-0.480). The engine predicts
memory with a random-forest regression too, so it is tempting to conclude the
engine inherits the volatility. That would be an analogy, not a measurement:
the engine's model is not RegressionSelector. It is fitted on every completed
run of the training datasets, where RegressionSelector sees only the clean
subset, and it divides by a completion probability. More data could make it
more stable, or not. This file measures the engine's actual decision rule
before anything in the engine is changed.

Protocol, identical for both arms so the comparison is fair:

  test set    the 39 memory configurations where every candidate completed --
              the same set bench_selectors scores -- held out one DATASET at a
              time
  engine      PerformanceModel fitted on ALL rows of the other datasets, as in
              production; pick argmin(predicted memory / P(complete)), which is
              the engine's memory score
  pairwise    PairwiseRankSelector fitted on the clean subset of the other
              datasets, as in bench_selectors
  metric      nPAR10 against one fixed pair of anchors

and a training jackknife: each configuration removed from the data entirely,
both arms refitted, 39 times.

The survival forest is switched off in the engine arm. It feeds the runtime
prediction and P(complete); on this test set every candidate completed, so
P(complete) comes from the completion classifier instead, and the memory
prediction -- the thing being measured -- is untouched. It makes each fit
about ten times faster, which matters because a benchmark measuring runtimes
runs on the same machine.

    python -m recommender.engine_memory_eval
"""
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from .perfmodel import PerformanceModel, load_runs, design_columns
from .selectors import PairwiseRankSelector, npar10

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")
CATEGORY = 1
ARMS = ("engine", "pairwise", "pairwise_all")


def clean_instances(df):
    """(dataset, threshold) pairs where every category-1 candidate completed."""
    c1 = df[df.category == CATEGORY]
    ok = c1[c1.completed]
    wide = ok.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                          values="peak_memory_mb", aggfunc="min")
    return set(wide.dropna(axis=0, how="any").index)


def evaluate(df, drop=None):
    """Per-instance picks of both arms, leave-one-dataset-out."""
    if drop is not None:
        df = df[~((df.dataset == drop[0]) & np.isclose(df.param_value, drop[1]))]
    c1 = df[df.category == CATEGORY]
    keep = clean_instances(df)
    clean = c1[[(d, p) in keep for d, p in zip(c1.dataset, c1.param_value)] & c1.completed]
    clean = clean.assign(runtime_s=clean.peak_memory_mb,
                         par10=clean.peak_memory_mb.astype(float))
    cols = design_columns("static")

    rows = []
    for held in sorted(clean.dataset.unique()):
        eng = PerformanceModel(use_survival=False).fit(
            c1[c1.dataset != held])                          # all rows, as in production
        pw = PairwiseRankSelector().fit(clean[clean.dataset != held], cols)
        # The same selector trained on every completed run of the training
        # datasets, as the engine is. Pairwise ranking only needs the two
        # algorithms of a pair to have completed on an instance, so the clean
        # subset throws away usable pairs; this arm tests whether that
        # restriction, rather than the method, explains the difference.
        done = c1[(c1.dataset != held) & c1.completed]
        pw_all = PairwiseRankSelector().fit(
            done.assign(runtime_s=done.peak_memory_mb), cols)
        for thr, g in clean[clean.dataset == held].groupby("param_value"):
            costs = dict(zip(g.algorithm, g.par10))
            cand = sorted(costs)
            feats = g.iloc[0].to_dict()
            scores = {}
            for a in cand:
                p = eng.predict(a, feats, thr)
                if p is not None:
                    scores[a] = p["memory_mb"] / max(p["p_complete"], 0.01)
            e_pick = min(scores, key=scores.get) if scores else cand[0]
            x = g[cols].iloc[0].to_numpy(float)
            p_pick = pw.select(x, cand)
            pa_pick = pw_all.select(x, cand)
            rows.append({"dataset": held, "param_value": thr,
                         "vbs": min(costs.values()),
                         "engine": costs[e_pick], "pairwise": costs[p_pick],
                         "pairwise_all": costs[pa_pick]})
    return pd.DataFrame(rows)


def score(res, anchors):
    vbs, sbs = anchors
    return {k: npar10(res[k].mean(), sbs, vbs) for k in ARMS}


def _jack(args):
    inst, anchors = args
    return inst, score(evaluate(load_runs(), drop=inst), anchors)


def main(argv=None):
    df = load_runs()
    full = evaluate(df)
    # One anchor pair for every number below: VBS from the test set, SBS the
    # fixed choice bench_selectors reports on the same 39 configurations.
    c1 = df[df.category == CATEGORY]
    keep = clean_instances(df)
    clean = c1[[(d, p) in keep for d, p in zip(c1.dataset, c1.param_value)] & c1.completed]
    sbs_algo = clean.groupby("algorithm").peak_memory_mb.mean().idxmin()
    sbs = clean[clean.algorithm == sbs_algo].groupby(
        ["dataset", "param_value"]).peak_memory_mb.min().mean()
    anchors = (full.vbs.mean(), sbs)
    base = score(full, anchors)

    print("=" * 74)
    print("ENGINE MEMORY RANKING vs PAIRWISE RANKING  (%d configurations)" % len(full))
    print("=" * 74)
    print("  anchors: VBS %.2f MB, fixed choice (%s) %.2f MB" % (anchors[0], sbs_algo, anchors[1]))
    for k in ARMS:
        print("  full data:  %-13s nPAR10 %.3f   mean %.2f MB" % (k, base[k], full[k].mean()))

    insts = list(zip(full.dataset, full.param_value))
    with ProcessPoolExecutor(max_workers=2) as ex:
        out = list(ex.map(_jack, [(i, anchors) for i in insts]))
    vals = {k: np.array([o[1][k] for o in out]) for k in ARMS}
    print()
    print("  training jackknife, %d refits:" % len(out))
    print("  %-13s %8s %8s %8s   %s" % ("arm", "min", "median", "max", "beats fixed choice"))
    for k in ARMS:
        v = vals[k]
        print("  %-13s %8.3f %8.3f %8.3f   %d / %d"
              % (k, v.min(), np.median(v), v.max(), int((v < 1).sum()), len(v)))
    n = len(out)
    print("  better than engine: pairwise %d/%d, pairwise_all %d/%d"
          % (int((vals["pairwise"] < vals["engine"]).sum()), n,
             int((vals["pairwise_all"] < vals["engine"]).sum()), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
