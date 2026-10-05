"""Score the hard-threshold confirmation, results/HARD_PROTOCOL.md.

    python tools/hard_eval.py --probe     # probe the instances (after the benchmark)
    python tools/hard_eval.py             # H1-H4

Refuses to score if the frozen inputs changed.
"""
import argparse
import hashlib
import math
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402

TRUTH = _ROOT / "results" / "hard_summary.csv"
PE.POINTS = _ROOT / "results" / "probe_points_hard.csv"
OUT = _ROOT / "results" / "hard_eval_output.txt"
#: engine.py and perfmodel.py are pinned to the protocol's commit (HARD_COMMIT)
HARD_COMMIT = os.environ.get("HARD_COMMIT")
FROZEN = {"results/training_runs.csv": "5f2467a", "recommender/probe.py": "ced9dc7"}
BUDGETS = (25, 50, 100, 200, 500)
NATIVE = ("Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth")
FAIL_REGRET = 10.0


def frozen_ok():
    frozen = dict(FROZEN)
    commit = HARD_COMMIT or subprocess.run(
        ["git", "log", "-1", "--format=%h", "--", "results/HARD_PROTOCOL.md"],
        capture_output=True, text=True, check=True).stdout.strip()
    frozen["recommender/engine.py"] = commit
    frozen["recommender/perfmodel.py"] = commit
    ok = True
    for path, c in frozen.items():
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (c, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, c))
            ok = False
    return ok


def truth():
    return pd.read_csv(TRUTH)


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
    rows, acc, bud = [], [], []
    for (ds, sg), g in truth().groupby(["dataset", "param_value"]):
        key = (ds, round(float(sg), 9))
        if key not in pc:
            continue
        pr = pc[key]
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        eligible = {v.algorithm for v in db.filter(task)[0]}
        cand = g[g.algorithm.isin(eligible)]
        ok = PE.completed(cand)
        done = dict(zip(cand.algorithm[ok], cand.peak_memory_mb[ok]))
        if not done:
            continue
        best = min(done.values())
        recs, _r, _f = rec.recommend(task)
        model = {r.algorithm: r.memory_mb for r in recs}
        for a in NATIVE:
            if a not in done or a not in model or a not in pr["costs"]:
                continue
            pm, true_m = pr["costs"][a][0], done[a]
            if not pr["costs"][a][2]:
                acc.append({"algorithm": a, "probe": abs(math.log10(pm / true_m)),
                            "model": abs(math.log10(model[a] / true_m))})
            for b in BUDGETS:
                bud.append({"budget": b, "probe": (pm <= b) == (true_m <= b),
                            "model": (model[a] <= b) == (true_m <= b)})
        allc = set(cand.algorithm)
        est = {a: (pr["costs"][a][0] if a in pr["costs"] else model[a])
               for a in allc if a in pr["costs"] or a in model}
        eng = next(r.algorithm for r in recs if r.algorithm in allc)
        pick = min(est, key=est.get)
        est_c = {a: v for a, v in est.items() if a in done}
        eng_c = next(r.algorithm for r in recs if r.algorithm in done)
        pick_c = min(est_c, key=est_c.get)
        reg = lambda a: done[a] / best if a in done else FAIL_REGRET   # noqa: E731
        rows.append({"dataset": ds, "sigma": sg, "engine": reg(eng), "probe": reg(pick),
                     "eng_pick": eng, "pick": pick, "engine_c": reg(eng_c),
                     "probe_c": reg(pick_c), "failed": ",".join(sorted(allc - set(done))),
                     "best": min(done, key=done.get), "best_mb": best, "mode": pr["mode"]})
    p, acc, bud = pd.DataFrame(rows), pd.DataFrame(acc), pd.DataFrame(bud)
    g = PE.gmean
    L("=" * 78)
    L("VARIANT: %s" % variant)
    L("=" * 78)
    for r in p.itertuples():
        L("  %-10s %-10.6g %-7s best %-20s %7.1f MB | engine %-20s %5.2fx | probe %-20s %5.2fx | failed: %s"
          % (r.dataset, r.sigma, r.mode, r.best, r.best_mb, r.eng_pick, r.engine, r.pick, r.probe,
             r.failed or "-"))
    L("memory: %d instances, %d datasets | engine %.3fx  probe %.3fx"
      % (len(p), p.dataset.nunique(), g(p.engine), g(p.probe)))
    pb, band = PE.boot(p, "probe", "engine")
    L("H1 superiority: ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
      % (band[1], band[0], band[2], pb, "PASS" if pb >= 0.95 and g(p.probe) < g(p.engine) else "FAIL"))
    L("H2 non-inferiority: probe %.3f <= 1.05 x engine %.3f -> %s"
      % (g(p.probe), g(p.engine), "PASS" if g(p.probe) <= 1.05 * g(p.engine) else "FAIL"))
    if len(acc):
        m = acc.groupby("algorithm")[["probe", "model"]].median()
        L("H3 accuracy (median |log10 error| memory, sampled instances):")
        for a, r in m.iterrows():
            L("   %-22s probe %.3f  model %.3f  (n=%d)" % (a, r.probe, r.model, (acc.algorithm == a).sum()))
        L("   -> %s" % ("PASS" if bool((m.probe < m.model).all()) else "FAIL"))
    else:
        L("H3: no sampled instance (every probe was a direct measurement)")
    if len(bud):
        bb = bud.groupby("budget")[["probe", "model"]].mean()
        L("H4 budget answers correct (share):")
        for b, r in bb.iterrows():
            L("   %4d MB  probe %.3f  model %.3f" % (b, r.probe, r.model))
        tot = bud[["probe", "model"]].mean()
        L("   overall probe %.3f  model %.3f -> %s"
          % (tot.probe, tot.model, "PASS" if tot.probe > tot.model else "FAIL"))
    L("not tested -- pick restricted to completed miners: engine %.3fx  probe %.3fx"
      % (g(p.engine_c), g(p.probe_c)))
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
