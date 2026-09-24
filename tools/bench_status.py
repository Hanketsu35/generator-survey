"""Where the real-dataset benchmark is, and whether the recommender is succeeding.

    python tools/bench_status.py

Two parts: progress with an estimate of the time left, and the success metrics
computed on whatever has finished so far.

THE TEST, and why it is the right one
-------------------------------------
The five new datasets (bms1, bms2, c20d10k, kosarak, c73d10k) are data the
recommender has never seen. It is trained on results/summary.csv -- the seven
published datasets -- and asked to choose on the new ones, which were measured
on a different machine. That is the situation it exists for: a user's own
dataset, on the user's own computer. Every earlier selector number held out one
of seven datasets; this holds out five it never trained near.

PRE-REGISTERED CRITERIA -- written and committed before any recommender result
on the new datasets was computed, so they cannot have been chosen to fit it:

  S1  safety      The recommender's pick never violates the request: 0 of N.
                  Reported beside the performance-first pick (the cheapest
                  implementation that reads the format, chosen with the TRUE
                  measured costs), whose violations are the E2 result checked
                  out of sample. Success: recommender 0, and the comparison
                  reported whatever it shows.

  S2  memory      Geometric-mean regret of the recommender's pick below that of
                  the fixed choice (always run Apriori, the single best on the
                  published data). Regret = cost of pick / cost of the best
                  eligible implementation on that instance. Success: strictly
                  below, on instances where every eligible miner completed.

  S3  runtime     Geometric-mean regret at most 1.10. The published portfolio
                  has 1.011x headroom on runtime, so nothing large is expected
                  and the honest bar is "within 10% of the best".

  Hit rate -- the pick is within 5% of the best -- is shown for both objectives
  because it is easy to read, but it is not a criterion: accuracy and cost
  disagree when the loss is asymmetric (NOTES section 4).

Known confound, stated rather than hidden: the model learned memory on the old
machine and is scored on memory measured on this one. A JVM's resident size
depends on its default heap, which depends on the machine's RAM. If S2 fails,
this is a candidate cause and must be checked against the calibration runs
before anything else is concluded.
"""
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

EXTRA = _ROOT / "results" / "real_extra_summary.csv"
LOG = _ROOT / "results" / "real_extra.log"
NEW = ("bms1", "bms2", "c20d10k", "kosarak", "c73d10k")
FIXED = {"runtime": "FPgrowth_Gen_Borgelt", "memory": "Apriori_Gen_Borgelt"}
CUTOFF = 3600.0
WORKERS = 2


def completed(df):
    return (df.timed_out.astype(str).str.lower() != "true") & df.error.isna()


def progress(df):
    total_ext, total_cal = 216, 72
    ext = df[df.role == "extension"]
    to = (df.timed_out.astype(str).str.lower() == "true").sum()
    err = df.error.notna().sum()
    print("PROGRESS")
    print("  calibration %d / %d | new datasets %d / %d | timeouts %d | errors %d"
          % ((df.role == "calibration").sum(), total_cal, len(ext), total_ext, to, err))
    print("  %-10s %s" % ("", "  ".join("%9s" % d for d in NEW)))
    print("  %-10s %s" % ("runs done", "  ".join("%9d" % (ext.dataset == d).sum()
                                                  for d in NEW)))
    # Time left: every remaining run at a difficulty level is assumed to take
    # the mean of the runs already finished at that level; a level with none
    # finished is assumed to time out, the conservative case.
    left = 0.0
    for tg in (10, 100, 1000, 5000, 20000):
        lvl = ext[ext.target_pairs == tg]
        n_expected = 9 * (4 if tg == 20000 else 5)      # c20d10k skips 20000
        remaining = max(n_expected - len(lvl), 0)
        mean = min(lvl.runtime_s.fillna(CUTOFF).mean(), CUTOFF) if len(lvl) else CUTOFF
        left += remaining * mean
    hours = left / WORKERS / 3600
    print("  estimated time left: %.1f h (finish around %s)"
          % (hours, time.strftime("%a %H:%M", time.localtime(time.time() + left / WORKERS))))
    print()


def picks(df):
    """Per new instance: recommender pick, fixed choice, best, and costs."""
    from recommender.engine import Recommender, PUBLISHED_TABLE
    from recommender.spec import MiningTask
    from recommender.capabilities import CapabilityDB
    # Pinned to the published table: the criteria were registered for a model
    # trained on the seven published datasets. The engine's default has since
    # moved to results/training_runs.csv, which CONTAINS the new datasets.
    rec, db = Recommender(table=PUBLISHED_TABLE), CapabilityDB()
    rows = []
    ext = df[df.role == "extension"]
    for (ds, sg), g in ext.groupby(["dataset", "param_value"]):
        if len(g) < 9:
            continue                                   # instance not finished
        for obj in ("runtime", "memory"):
            task = MiningTask(dataset=ds, threshold=float(sg), objective=obj)
            eligible = {v.algorithm for v in db.filter(task)[0]}
            cand = g[g.algorithm.isin(eligible)]
            if obj == "memory":
                if not completed(cand).all():
                    continue                           # killed run: lower bound only
                cost = dict(zip(cand.algorithm, cand.peak_memory_mb))
            else:
                cost = {a: (r if c else CUTOFF * 10) for a, r, c in
                        zip(cand.algorithm, cand.runtime_s, completed(cand))}
            if not cost:
                continue
            recs, _rej, _f = rec.recommend(task)
            pick = next((r.algorithm for r in recs if r.algorithm in cost), None)
            best = min(cost.values())
            # performance-first: cheapest implementation that reads the format,
            # with the TRUE costs -- including the ones Layer 2 rejects.
            allc = g if obj == "runtime" else g[completed(g)]
            pf_cost = (dict(zip(allc.algorithm, np.where(completed(allc), allc.runtime_s,
                                                         CUTOFF * 10)))
                       if obj == "runtime" else dict(zip(allc.algorithm, allc.peak_memory_mb)))
            pf = min(pf_cost, key=pf_cost.get) if pf_cost else None
            rows.append({"dataset": ds, "sigma": sg, "objective": obj,
                         "pick": pick, "best": best,
                         "pick_cost": cost.get(pick, np.nan),
                         "fixed_cost": cost.get(FIXED[obj], np.nan),
                         "pick_ok": pick in eligible,
                         "perf_first": pf, "perf_first_ok": pf in eligible})
    return pd.DataFrame(rows)


def gmean(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.log(x).mean())) if x.size else float("nan")


def metrics(p):
    print("SUCCESS METRICS  (trained on the 7 published datasets; scored on the"
          " new ones)")
    if p.empty:
        print("  no new instance has finished all nine miners yet")
        return
    for obj in ("memory", "runtime"):
        q = p[p.objective == obj]
        if q.empty:
            print("  %-8s no instances yet" % obj)
            continue
        reg = q.pick_cost / q.best
        freg = q.fixed_cost / q.best
        hit = (reg <= 1.05).mean()
        print("  %-8s %2d instances over %d datasets | regret: recommender %.3fx,"
              " fixed choice %.3fx | hit rate %.0f%%"
              % (obj, len(q), q.dataset.nunique(), gmean(reg), gmean(freg), 100 * hit))
    print()
    s1 = (~p.pick_ok).sum()
    pf_bad = (~p.perf_first_ok).sum()
    mem = p[p.objective == "memory"]
    rt = p[p.objective == "runtime"]
    s2 = gmean(mem.pick_cost / mem.best) < gmean(mem.fixed_cost / mem.best) if len(mem) else None
    s3 = gmean(rt.pick_cost / rt.best) <= 1.10 if len(rt) else None
    fmt = lambda v: "n/a yet" if v is None else ("PASS" if v else "FAIL")
    print("  S1 safety   recommender violates the request on %d of %d picks  -> %s"
          % (s1, len(p), "PASS" if s1 == 0 else "FAIL"))
    print("              (performance-first, given the true costs: %d of %d)"
          % (pf_bad, len(p)))
    print("  S2 memory   recommender regret below fixed choice              -> %s" % fmt(s2))
    print("  S3 runtime  recommender regret at most 1.10                    -> %s" % fmt(s3))
    print()
    print("  A result on few instances is a direction, not a verdict: each new")
    print("  dataset contributes up to five instances, and they are not independent.")
    post_hoc(p)


#: Minimum duration of the BEST run for an instance to count as measurable.
#: At 0.1 s memory sampling a 20 ms run is read once, at spawn -- one reading
#: gave 0.84 MB, not a plausible process -- and runtime ratios of 10 ms runs
#: are process-start noise. 1 s gives about ten memory samples.
MEASURABLE_S = 1.0


def post_hoc(p):
    """NOT pre-registered: the same metrics on instances long enough to measure.

    Added after the first results, and labelled so. The pre-registered S2 and S3
    above stand as specified and are not re-scored; this section exists because
    the instances that finish first are the easy ones, where both costs are
    measurement noise, and the criteria omitted a minimum duration that the
    memory monitor's own documentation says any comparison needs.
    """
    df = pd.read_csv(EXTRA)
    fast = df[completed(df)].groupby(["dataset", "param_value"]).runtime_s.min()
    long_enough = set(fast[fast >= MEASURABLE_S].index)
    q = p[[(d, s) in long_enough for d, s in zip(p.dataset, p.sigma)]]
    print()
    print("POST-HOC, NOT PRE-REGISTERED -- instances whose best run takes >= %.0f s"
          % MEASURABLE_S)
    if q.empty:
        print("  none yet: every finished instance is too fast to measure. The")
        print("  hard difficulty levels, still running, are where this is decided.")
        return
    for obj in ("memory", "runtime"):
        r = q[q.objective == obj]
        if r.empty:
            continue
        print("  %-8s %2d instances | regret recommender %.3fx, fixed choice %.3fx"
              % (obj, len(r), gmean(r.pick_cost / r.best), gmean(r.fixed_cost / r.best)))


def main():
    if not EXTRA.exists():
        print("no results yet at %s" % EXTRA)
        return 1
    df = pd.read_csv(EXTRA)
    progress(df)
    metrics(picks(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
