"""AutoFolio's memory regret under another SMAC seed (gap G5, kbs/GAPS.md).

    python tools/autofolio_seeds.py --seed 1

Same training table, instances, eligibility and regret as
tools/baseline_comparison.py; only AutoFolio's seed differs (published run:
12345). Reported, decided before running: the mean and range over the seeds.
Writes results/autofolio_seed<seed>.csv.
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import baseline_comparison as BC                           # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import selectors as S                     # noqa: E402
from recommender.perfmodel import design_columns           # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--af-wallclock", type=int, default=1800)
    args = ap.parse_args(argv)
    import pandas as pd
    from recommender.capabilities import CapabilityDB
    from recommender.spec import MiningTask
    cols = design_columns("static")
    db = CapabilityDB()
    tr = BC.train_frame("memory", cols, BC.MINERS)
    af = S.AutoFolioSelector(wallclock=args.af_wallclock, objective="memory",
                             seed=args.seed).fit(tr, cols)
    plan = []
    for tset, path in BC.TESTS.items():
        t = BC.test_frame(path, cols)
        for (ds, sg), g in t.groupby(["dataset", "param_value"]):
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                              threshold=float(sg), objective="memory")
            el = {v.algorithm for v in db.filter(task)[0]}
            ok = PE.completed(g)
            done = {a: m for a, m in zip(g.algorithm[ok], g.peak_memory_mb[ok]) if a in el}
            cand = [a for a in sorted(set(g.algorithm)) if a in el]
            if len(cand) < 2 or not done:
                continue
            plan.append((tset, ds, sg, cand, done, g[cols].iloc[0].to_numpy(float)))
    af.prepare([p[-1] for p in plan])
    rows = []
    for tset, ds, sg, cand, done, x in plan:
        a = af.select(x, cand)
        rows.append({"set": tset, "dataset": ds, "sigma": sg, "primary": tset in BC.PRIMARY,
                     "pick": a, "regret": done[a] / min(done.values()) if a in done else BC.FAIL})
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / ("autofolio_seed%d.csv" % args.seed), index=False)
    for label, q in (("PRIMARY", d[d.primary]), ("all", d)):
        print("seed %d %-8s n=%d  %.3fx  failed %d"
              % (args.seed, label, len(q), PE.gmean(q.regret), int((q.regret >= BC.FAIL).sum())))


if __name__ == "__main__":
    main()
