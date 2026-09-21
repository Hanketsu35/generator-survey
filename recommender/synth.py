"""Synthetic transactional instance generator.

E3 and E4 both fail for the same reason: seven real datasets are not a
meta-instance set.  Leave-one-dataset-out gives seven folds, each of which
removes one seventh of the *feature space* rather than one seventh of the
data, so the model is asked to extrapolate rather than interpolate, and a
per-algorithm constant beats it.

This module removes that limitation by generating datasets with CONTROLLED
meta-features, following the IBM Quest design that produced T10I4D100K:

    * a pool of ``n_patterns`` potential maximal itemsets is drawn, with
      itemset lengths from an exponential distribution about ``pattern_len``
      and items drawn under a Zipf weight (``skew`` controls the support
      distribution, hence ``sup_gini``);
    * each transaction is filled by repeatedly picking a potential itemset,
      inserting it whole with probability ``corruption`` of dropping each
      item, until the target transaction length is reached;
    * transaction lengths come from an exponential distribution about
      ``avg_len``, which together with ``n_items`` sets ``density``.

The point is not realism -- real data has correlation structure no generator
reproduces -- but COVERAGE.  Real datasets anchor the space; synthetic ones
fill it in so that a held-out real dataset is interpolated rather than
extrapolated.  The evaluation protocol must therefore always hold out a REAL
dataset, never a synthetic one, or the accuracy is self-congratulatory.

    python -m recommender.synth --grid --out datasets/synthetic
    python -m recommender.synth --n-tx 20000 --n-items 200 --avg-len 20 \
        --skew 1.2 --out-file datasets/synthetic/custom.txt
"""
import argparse
import math
import os
import sys

import numpy as np


def _zipf_weights(n, skew, rng):
    """Item-selection weights: skew=0 uniform, larger = more concentrated."""
    ranks = np.arange(1, n + 1, dtype=float)
    w = 1.0 / np.power(ranks, max(skew, 0.0))
    rng.shuffle(w)
    return w / w.sum()


def generate(n_tx=10000, n_items=200, avg_len=10.0, n_patterns=2000,
             pattern_len=4.0, corruption=0.5, skew=0.8, seed=0):
    """Yield transactions as lists of int item ids (1-based)."""
    rng = np.random.default_rng(seed)
    weights = _zipf_weights(n_items, skew, rng)

    # --- pool of potential maximal itemsets ---------------------------
    plens = np.maximum(1, rng.poisson(max(pattern_len, 1.0), n_patterns))
    patterns = []
    for L in plens:
        L = int(min(L, n_items))
        items = rng.choice(n_items, size=L, replace=False, p=weights)
        patterns.append(items + 1)
    # Pattern selection is itself skewed: a few patterns dominate.
    pw = _zipf_weights(n_patterns, max(skew * 0.5, 0.1), rng)

    tlens = np.maximum(1, rng.poisson(max(avg_len, 1.0), n_tx))
    for i in range(n_tx):
        target = int(tlens[i])
        tx = set()
        guard = 0
        while len(tx) < target and guard < 50:
            guard += 1
            pat = patterns[int(rng.choice(n_patterns, p=pw))]
            keep = pat[rng.random(len(pat)) >= corruption]
            if len(keep) == 0:
                continue
            tx.update(int(x) for x in keep)
        if not tx:
            tx.add(int(rng.choice(n_items, p=weights)) + 1)
        yield sorted(tx)


def write(path, **kw):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for tx in generate(**kw):
            fh.write(" ".join(str(x) for x in tx))
            fh.write("\n")
            n += 1
    return n


# ----------------------------------------------------------------------
# A grid chosen to SPAN the region the seven real datasets occupy, rather
# than to cluster near any one of them. The real corners are:
#   chess/connect  dense, few items      density 0.33-0.49, gini 0.40-0.59
#   mushroom       dense, full-support item
#   pumsb          long transactions, very skewed  gini 0.92
#   accidents      large, moderately dense
#   retail         very sparse, many items, skewed
#   T10I4D100K     sparse, uniform       gini 0.02
# ----------------------------------------------------------------------
GRID = {
    "n_tx": [2000, 10000, 50000],
    "n_items": [80, 300, 2000],
    "avg_len": [8, 20, 40],
    "skew": [0.0, 0.8, 1.6],
    "corruption": [0.25, 0.6],
}


def grid_specs(limit=None, seed=0):
    """Deterministic sweep over GRID; returns [(name, kwargs), ...]."""
    import itertools
    keys = list(GRID)
    out = []
    for i, combo in enumerate(itertools.product(*(GRID[k] for k in keys))):
        kw = dict(zip(keys, combo))
        if kw["avg_len"] >= kw["n_items"]:        # impossible
            continue
        kw["seed"] = seed + i
        kw["n_patterns"] = max(200, kw["n_items"] * 5)
        kw["pattern_len"] = max(2.0, kw["avg_len"] / 3.0)
        name = ("syn_n%d_i%d_l%d_s%s_c%s"
                % (kw["n_tx"], kw["n_items"], kw["avg_len"],
                   str(kw["skew"]).replace(".", ""), str(kw["corruption"]).replace(".", "")))
        out.append((name, kw))
    return out[:limit] if limit else out


def estimate_cost(specs):
    """Rough disk and generation-time estimate, so the cost is stated up front."""
    bytes_total = 0
    for _, kw in specs:
        avg_tok = math.log10(max(kw["n_items"], 10)) + 1
        bytes_total += kw["n_tx"] * kw["avg_len"] * (avg_tok + 1)
    return {"n_datasets": len(specs),
            "est_disk_mb": bytes_total / 1e6,
            "est_gen_minutes": sum(k["n_tx"] for _, k in specs) / 1.2e5}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m recommender.synth",
                                 description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grid", action="store_true", help="generate the full sweep")
    ap.add_argument("--limit", type=int, help="cap the number of grid datasets")
    ap.add_argument("--out", default="datasets/synthetic", help="output directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and its estimated cost, generate nothing")
    ap.add_argument("--out-file", help="single dataset: output path")
    for k, d in [("n-tx", 10000), ("n-items", 200), ("avg-len", 10),
                 ("n-patterns", 2000), ("seed", 0)]:
        ap.add_argument("--" + k, type=int, default=d)
    for k, d in [("pattern-len", 4.0), ("corruption", 0.5), ("skew", 0.8)]:
        ap.add_argument("--" + k, type=float, default=d)
    args = ap.parse_args(argv)

    if args.grid:
        specs = grid_specs(limit=args.limit)
        est = estimate_cost(specs)
        print("grid: %d datasets, ~%.0f MB on disk, ~%.0f min to generate"
              % (est["n_datasets"], est["est_disk_mb"], est["est_gen_minutes"]))
        if args.dry_run:
            for nm, kw in specs[:10]:
                print("   %-44s %s" % (nm, kw))
            if len(specs) > 10:
                print("   ... and %d more" % (len(specs) - 10))
            return 0
        for i, (nm, kw) in enumerate(specs, 1):
            path = os.path.join(args.out, nm + ".txt")
            if os.path.exists(path):
                continue
            n = write(path, **kw)
            print("[%3d/%3d] %-44s %d transactions" % (i, len(specs), nm, n))
        return 0

    path = args.out_file or os.path.join(args.out, "synthetic.txt")
    n = write(path, n_tx=args.n_tx, n_items=args.n_items, avg_len=args.avg_len,
              n_patterns=args.n_patterns, pattern_len=args.pattern_len,
              corruption=args.corruption, skew=args.skew, seed=args.seed)
    print("wrote %s (%d transactions)" % (path, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
