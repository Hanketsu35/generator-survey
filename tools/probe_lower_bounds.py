"""Re-probe the instances where a native miner did not finish its probe, and
record what it had used when stopped (a lower bound on its memory).

    python tools/probe_lower_bounds.py

Output: results/probe_lower_bounds.csv (dataset, sigma, algorithm, memory_lb, why)
"""
import csv
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402
from recommender import probe as P                        # noqa: E402

FILES = ["probe_points.csv", "probe_points_confirm.csv", "probe_points_hard.csv"]
OUT = _ROOT / "results" / "probe_lower_bounds.csv"


def failed_instances():
    out = set()
    for f in FILES:
        d = pd.read_csv(_ROOT / "results" / f)
        n = d.groupby(["dataset", "sigma", "algorithm"])["size"].apply(lambda s: s.notna().sum())
        m = d.groupby(["dataset", "sigma", "algorithm"])["mode"].first()
        bad = n[((m == "direct") & (n == 0)) | ((m == "sampled") & (n < 2))]
        out |= {(ds, float(sg)) for ds, sg, _a in bad.index}
    return sorted(out)


def main():
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "sigma", "mode", "wall_s", "algorithm", "memory_lb", "why", "size"])
        for ds, sg in failed_instances():
            r = P.probe(PE.dataset_path(ds), sg)
            for a, c in r.costs.items():
                if c.get("mode") == "failed":
                    w.writerow([ds, sg, r.mode, round(r.wall_s, 2), a, c.get("memory_lb"),
                                c.get("why"), c.get("size")])
            fh.flush()
            print("%-12s %-12g %-7s %6.1fs  %s" % (ds, sg, r.mode, r.wall_s,
                  {a: (round(c.get("memory_lb") or 0), c.get("why")) for a, c in r.costs.items()
                   if c.get("mode") == "failed"}), flush=True)


if __name__ == "__main__":
    main()
