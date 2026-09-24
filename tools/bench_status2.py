"""Score the second extension against results/EXTENSION2_PROTOCOL.md.

    python tools/bench_status2.py

The model under test is the engine trained on results/training_runs.csv AS
COMMITTED with the protocol (0f3e5d1). The script refuses to score if the
file differs from that version: a rebuilt training table would be a
different model from the one the criteria were registered for.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import bench_status as bs                               # noqa: E402

PROTOCOL_COMMIT = "0f3e5d1"
TABLE = "results/training_runs.csv"
OUT = _ROOT / "results" / "real_extra2_summary.csv"
DATASETS = ("chicago", "kddcup99", "onlineretail", "pamap", "recordlink")
REF = "Gr_growth"


def _same_as_registered():
    now = hashlib.sha256((_ROOT / TABLE).read_bytes()).hexdigest()
    then = hashlib.sha256(subprocess.run(
        ["git", "show", "%s:%s" % (PROTOCOL_COMMIT, TABLE)],
        capture_output=True, check=True).stdout).hexdigest()
    return now == then


def score(ext, rec, db):
    from recommender.spec import MiningTask
    rows = []
    for (ds, sg), g in ext.groupby(["dataset", "param_value"]):
        if len(g) < 9:
            continue
        for obj in ("runtime", "memory"):
            task = MiningTask(dataset=ds, threshold=float(sg), objective=obj)
            eligible = {v.algorithm for v in db.filter(task)[0]}
            cand = g[g.algorithm.isin(eligible)]
            if obj == "memory":
                if not bs.completed(cand).all():
                    continue
                cost = dict(zip(cand.algorithm, cand.peak_memory_mb))
            else:
                cost = {a: (x if c else bs.CUTOFF * 10) for a, x, c in
                        zip(cand.algorithm, cand.runtime_s, bs.completed(cand))}
            recs, _rej, _f = rec.recommend(task)
            pick = next((x for x in recs if x.algorithm in cost), None)
            if pick is None:
                continue
            best = min(cost.values())
            rows.append({"dataset": ds, "sigma": sg, "objective": obj,
                         "pick": pick.algorithm, "pick_ok": pick.algorithm in eligible,
                         "regret": cost[pick.algorithm] / best,
                         "fixed_regret": cost.get(bs.FIXED[obj], np.nan) / best,
                         "ref_regret": cost.get(REF, np.nan) / best,
                         "outside": bool(pick.extrapolated)})
    return pd.DataFrame(rows)


def main():
    if not _same_as_registered():
        print("REFUSED: %s differs from the version committed in %s; the model"
              " under test would not be the registered one." % (TABLE, PROTOCOL_COMMIT))
        return 2
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    d = pd.read_csv(OUT)
    n9 = d.groupby(["dataset", "param_value"]).size()
    print("PROGRESS  %d runs | %d of %d instances complete (all nine miners)"
          % (len(d), (n9 >= 9).sum(), len(n9)))
    rec = Recommender(table=str(_ROOT / TABLE))
    p = score(d, rec, CapabilityDB())
    if p.empty:
        print("no complete instance yet")
        return 0
    g = bs.gmean
    mem, rt = p[p.objective == "memory"], p[p.objective == "runtime"]
    print()
    for name, q in (("memory", mem), ("runtime", rt)):
        if q.empty:
            continue
        print("  %-8s %2d instances, %d datasets | engine %.3fx | fixed %s %.3fx | %s %.3fx"
              % (name, len(q), q.dataset.nunique(), g(q.regret),
                 bs.FIXED[name].replace("_Gen_Borgelt", ""), g(q.fixed_regret), REF,
                 g(q.ref_regret)))
    print()
    v = (~p.pick_ok).sum()
    fmt = lambda ok: "PASS" if ok else "FAIL"
    print("  T1 safety          %d of %d picks violate the request  -> %s" % (v, len(p), fmt(v == 0)))
    if len(mem):
        print("  T2 memory          engine %.3fx < fixed %.3fx              -> %s"
              "  (expected by dataset choice)" % (g(mem.regret), g(mem.fixed_regret),
                                                   fmt(g(mem.regret) < g(mem.fixed_regret))))
        print("  T3 memory absolute engine %.3fx <= 1.25x                   -> %s"
              % (g(mem.regret), fmt(g(mem.regret) <= 1.25)))
    if len(rt):
        print("  T4 runtime         engine %.3fx <= 1.10x                   -> %s"
              % (g(rt.regret), fmt(g(rt.regret) <= 1.10)))
    print()
    print("  per dataset (memory / runtime engine regret; picks):")
    for ds, q in p.groupby("dataset"):
        m, r = q[q.objective == "memory"], q[q.objective == "runtime"]
        print("    %-13s mem %s  run %s  | memory picks: %s"
              % (ds, "%.3f" % g(m.regret) if len(m) else "  -  ",
                 "%.3f" % g(r.regret) if len(r) else "  -  ",
                 ", ".join(sorted(set(m.pick.str.replace("_Gen_Borgelt", ""))))))
    for out, q in p.groupby("outside"):
        print("  %s training domain: %d picks, memory %.3fx, runtime %.3fx"
              % ("outside" if out else "inside ", len(q),
                 g(q[q.objective == "memory"].regret), g(q[q.objective == "runtime"].regret)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
