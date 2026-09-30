"""Does running the probe's miners concurrently change what it measures?

    python tools/probe_parallel_check.py

Re-probes instances already probed one miner at a time (probe_points*.csv) and
compares memory and runtime, miner by miner, and the probe's wall-clock time.
Output: results/probe_parallel_check.csv
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402
from recommender import probe as P                        # noqa: E402

SETS = {"probe_points.csv": ["chicago", "kosarak", "retail", "pumsb", "bms1", "accidents"],
        "probe_points_confirm.csv": ["instacart", "chainstore_fim"],
        "probe_points_hard.csv": ["mooc_set", "eshop_set", "liquor"]}


def main():
    rows = []
    for f, dss in SETS.items():
        old = pd.read_csv(_ROOT / "results" / f)
        for ds in dss:
            for sg, g in old[old.dataset == ds].groupby("sigma"):
                r = P.probe(PE.dataset_path(ds), float(sg))
                for a in P.PROBED:
                    h = g[g.algorithm == a].dropna(subset=["size"]).sort_values("size")
                    new = dict(r.points.get(a) or [])
                    for q in h.itertuples():
                        got = new.get(int(q.size))
                        rows.append({"dataset": ds, "sigma": sg, "algorithm": a, "size": int(q.size),
                                     "mode": r.mode, "old_mem": q.memory_mb, "old_rt": q.runtime_s,
                                     "new_mem": got[0] if got else np.nan,
                                     "new_rt": got[1] if got else np.nan,
                                     "old_wall": q.wall_s, "new_wall": r.wall_s})
                print("%-14s %-10g %-7s wall %6.1fs -> %6.1fs"
                      % (ds, sg, r.mode, g.wall_s.iloc[0], r.wall_s), flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "probe_parallel_check.csv", index=False)
    m = np.log10(d.new_mem / d.old_mem).abs()
    t = d.new_rt / d.old_rt
    w = d.drop_duplicates(["dataset", "sigma"])
    print("points %d (lost %d) | memory |log10 ratio| median %.4f, p95 %.4f, max %.4f"
          % (len(d), d.new_mem.isna().sum(), m.median(), m.quantile(.95), m.max()))
    print("runtime new/old median %.2f, p95 %.2f (runs >= 0.1 s: median %.2f)"
          % (t.median(), t.quantile(.95), t[d.old_rt >= 0.1].median()))
    print("wall: old median %.1fs max %.1fs -> new median %.1fs max %.1fs"
          % (w.old_wall.median(), w.old_wall.max(), w.new_wall.median(), w.new_wall.max()))


if __name__ == "__main__":
    main()
