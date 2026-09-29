"""Score the confirmation study, results/CONFIRM_PROTOCOL.md.

    python tools/confirm_eval.py --probe     # probe the 22 new instances (after the benchmark)
    python tools/confirm_eval.py             # Q1-Q4

Refuses to score if the frozen inputs changed: results/training_runs.csv must
equal its version at 490be30, and recommender/probe.py its version at b9442dd.
"""
import argparse
import hashlib
import math
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

import probe_eval as PE                                    # noqa: E402

TRUTH = _ROOT / "results" / "real_extra3_summary.csv"
PE.POINTS = _ROOT / "results" / "probe_points_confirm.csv"
OUT = _ROOT / "results" / "confirm_eval_output.txt"
FROZEN = {"results/training_runs.csv": "490be30", "recommender/probe.py": "b9442dd"}
BUDGETS = (25, 50, 100, 200, 500)
NATIVE = ("Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth")


def frozen_ok():
    ok = True
    for path, commit in FROZEN.items():
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (commit, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, commit))
            ok = False
    return ok


def truth():
    d = pd.read_csv(TRUTH)
    return d[d.role == "extension"]


def run_probes():
    PE.instances = lambda: sorted({(ds, float(p)) for ds, p in zip(truth().dataset, truth().param_value)})
    PE.run_probes()


def score(variant, lines):
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    L = lines.append
    rec, db = Recommender(), CapabilityDB()
    pc = PE.probe_costs(variant)
    t = truth()
    rows, acc, bud = [], [], []
    for (ds, sg), g in t.groupby(["dataset", "param_value"]):
        key = (ds, round(float(sg), 9))
        if key not in pc or len(g) < 9:
            continue
        pr = pc[key]
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        eligible = {v.algorithm for v in db.filter(task)[0]}
        cand = g[g.algorithm.isin(eligible)]
        recs, _r, _f = rec.recommend(task)
        model = {r.algorithm: r.memory_mb for r in recs}
        ok = PE.completed(cand)
        # accuracy and budget answers use every completed native run
        for a in NATIVE:
            row = cand[(cand.algorithm == a) & ok]
            if row.empty or a not in model or a not in pr["costs"]:
                continue
            true_m = float(row.peak_memory_mb.iloc[0])
            pm = pr["costs"][a][0]
            if not pr["costs"][a][2]:
                acc.append({"algorithm": a, "probe": abs(math.log10(pm / true_m)),
                            "model": abs(math.log10(model[a] / true_m))})
            for b in BUDGETS:
                bud.append({"budget": b, "probe": (pm <= b) == (true_m <= b),
                            "model": (model[a] <= b) == (true_m <= b)})
        if not ok.all():
            continue
        cost = dict(zip(cand.algorithm, cand.peak_memory_mb))
        eng = next((r.algorithm for r in recs if r.algorithm in cost), None)
        est = {a: (pr["costs"][a][0] if a in pr["costs"] else model[a])
               for a in cost if a in pr["costs"] or a in model}
        pick = min(est, key=est.get)
        best = min(cost.values())
        rows.append({"dataset": ds, "sigma": sg, "engine": cost[eng] / best,
                     "probe": cost[pick] / best, "fixed": cost["Apriori_Gen_Borgelt"] / best,
                     "pick": pick, "eng_pick": eng})
    p, acc, bud = pd.DataFrame(rows), pd.DataFrame(acc), pd.DataFrame(bud)
    g = PE.gmean
    L("=" * 78)
    L("VARIANT: %s" % variant)
    L("=" * 78)
    L("memory: %d instances, %d datasets | engine %.3fx  probe %.3fx  fixed %.3fx"
      % (len(p), p.dataset.nunique(), g(p.engine), g(p.probe), g(p.fixed)))
    for ds, q in p.groupby("dataset"):
        L("   %-15s %d | engine %.3f probe %.3f | picks engine %s, probe %s"
          % (ds, len(q), g(q.engine), g(q.probe), sorted(set(q.eng_pick)), sorted(set(q.pick))))
    q1 = g(p.probe) <= 1.05 * g(p.engine)
    L("Q1 non-inferiority: probe %.3f <= 1.05 x engine %.3f -> %s"
      % (g(p.probe), g(p.engine), "PASS" if q1 else "FAIL"))
    pb, band = PE.boot(p, "probe", "engine")
    L("Q2 superiority: ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
      % (band[1], band[0], band[2], pb, "PASS" if pb >= 0.95 and g(p.probe) < g(p.engine) else "FAIL"))
    if len(acc):
        m = acc.groupby("algorithm")[["probe", "model"]].median()
        q3 = bool((m.probe < m.model).all())
        L("Q3 accuracy (median |log10 error| memory, sampled instances):")
        for a, r in m.iterrows():
            L("   %-22s probe %.3f  model %.3f  (n=%d)" % (a, r.probe, r.model, (acc.algorithm == a).sum()))
        L("   -> %s" % ("PASS" if q3 else "FAIL"))
    else:
        L("Q3: no sampled instance (every probe was a direct measurement)")
    if len(bud):
        bb = bud.groupby("budget")[["probe", "model"]].mean()
        L("Q4 budget answers correct (share):")
        for b, r in bb.iterrows():
            L("   %4d MB  probe %.3f  model %.3f" % (b, r.probe, r.model))
        tot = bud[["probe", "model"]].mean()
        L("   overall probe %.3f  model %.3f -> %s" % (tot.probe, tot.model,
                                                     "PASS" if tot.probe > tot.model else "FAIL"))
    L("")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args(argv)
    if not frozen_ok():
        return 2
    if args.probe:
        run_probes()
        return 0
    lines = []
    for v in ("affine", "loglog"):
        score(v, lines)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
