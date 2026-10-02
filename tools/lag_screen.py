"""Screen for instances where a probed miner lags, and select them
(results/LAG_PROTOCOL.md).

    python tools/lag_screen.py

Only the probe runs here; no truth. Every probe is kept in
results/probe_lag.jsonl (the scorer reads it, so instances are not probed
twice), and the selection goes to results/lag_instances.csv.
"""
import csv
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import bench_real_extra as B                               # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import probe as P                        # noqa: E402
from recommender.engine import Recommender                 # noqa: E402

DATASETS = ["poker", "covertype", "dota2", "miniboone", "power", "uscensus", "splice",
            "fifa_set", "t25i10d10k", "ecommerce_fim", "microblog_set", "msnbc_set", "bike_set"]
TARGETS = (50000, 100000, 200000)
PER_DATASET = 2
CAP = 14
PROBES = _ROOT / "results" / "probe_lag.jsonl"
OUT = _ROOT / "results" / "lag_instances.csv"
TRUTHS = ["results/fresh_summary.csv", "results/fresh2_summary.csv", "results/fresh3_summary.csv"]


def main():
    import pandas as pd
    seen = set()
    for t in TRUTHS:
        d = pd.read_csv(_ROOT / t)
        seen |= {(a, round(float(b), 9)) for a, b in zip(d.dataset, d.param_value)}
    grid = [i for i in B.plan(DATASETS, calibration=False, cap_reachable=True, targets=TARGETS)
            if (i[0], round(i[1], 9)) not in seen]
    print("%d grid instances" % len(grid), flush=True)
    lagging = []
    with open(PROBES, "w") as fh:
        for ds, sg, tg, _role, _n, _m in grid:
            r = P.probe(PE.dataset_path(ds), sg)
            fh.write(json.dumps({"dataset": ds, "sigma": sg, "n": r.n, "mode": r.mode,
                                 "sizes": r.sizes, "wall_s": r.wall_s, "costs": r.costs,
                                 "points": {a: [[z, list(v)] for z, v in p]
                                            for a, p in r.points.items()},
                                 "target_pairs": tg}) + "\n")
            fh.flush()
            prog = Recommender._probe_progress(r)
            lag = len(set(prog.values())) > 1
            print("%-14s %-11.6g %-7s %5.1fs %s %s" % (ds, sg, r.mode, r.wall_s,
                  {a[:6]: round(v, 2) for a, v in prog.items()}, "LAG" if lag else ""), flush=True)
            if lag:
                lagging.append((ds, sg, tg))
    # selection: at most PER_DATASET per dataset, highest sigma first, then CAP overall
    # in dataset order of DATASETS
    chosen = []
    for ds in DATASETS:
        mine = sorted([x for x in lagging if x[0] == ds], key=lambda x: -x[1])[:PER_DATASET]
        chosen += mine
    chosen = chosen[:CAP]
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "sigma", "target_pairs"])
        w.writerows(chosen)
    print("lagging %d, selected %d -> %s" % (len(lagging), len(chosen), OUT))


if __name__ == "__main__":
    main()
