"""The analyses fixed in results/REMEASURE_PROTOCOL.md, in its order.

    python tools/remeasure_eval.py            # all of M0-M4
    python tools/remeasure_eval.py --only M0 M1

M4 refits the recommender twelve times (about 15 s each). Nothing here sets
or tests a success criterion; the pre-registered S1-S3 are in bench_status.py
and stand as recorded.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import bench_status as bs                               # noqa: E402

SUMMARY = _ROOT / "results" / "summary.csv"
EXTRA = _ROOT / "results" / "real_extra_summary.csv"
REMEASURED = _ROOT / "results" / "remeasured.csv"
NATIVE = ("Borgelt", "Gr_growth", "FGC_Stream")
CAT1 = ("mushroom", "chess", "connect", "pumsb", "accidents", "retail", "t10i4d100k",
        "bms1", "bms2", "c20d10k", "kosarak", "c73d10k")
RNG = np.random.default_rng(20260924)
N_BOOT = 2000


def gmean(x):
    return bs.gmean(x)


def _key(a, d, p):
    return (a, d, round(float(p), 9))


def valid_remeasured():
    """Rows usable as measurements: all repeats ran, and the count matches."""
    r = pd.read_csv(REMEASURED, dtype={"generator_count": str,
                                       "generator_count_recorded": str})
    def same(a, b):
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return str(a) == str(b)
    r["match"] = [same(a, b) for a, b in zip(r.generator_count, r.generator_count_recorded)]
    ok = (r.failed_reps == 0) & r.match & r.peak_memory_mb.notna()
    return r, r[ok]


def apply(df, rem, source):
    """`df` with runtime and memory replaced by re-measured medians where valid."""
    df = df.copy()
    sub = rem[rem.source == source]
    look = {_key(a, d, p): (rt, mm) for a, d, p, rt, mm in
            zip(sub.algorithm, sub.dataset, sub.param_value, sub.runtime_s, sub.peak_memory_mb)}
    n = 0
    for i, (a, d, p) in enumerate(zip(df.algorithm, df.dataset, df.param_value)):
        v = look.get(_key(a, d, p))
        if v is not None:
            df.iat[i, df.columns.get_loc("runtime_s")] = v[0]
            df.iat[i, df.columns.get_loc("peak_memory_mb")] = v[1]
            n += 1
    return df, n


# ----------------------------------------------------------------------
def m0(r_all, r):
    print("M0  did the measurement change?")
    print("    %d re-measured rows; %d usable (%d with a failed repeat, %d count mismatch)"
          % (len(r_all), len(r), (r_all.failed_reps > 0).sum(), (~r_all.match).sum()))
    if (~r_all.match).any():
        for x in r_all[~r_all.match].itertuples():
            print("      mismatch: %s %s %s recorded %s, now %s"
                  % (x.source, x.algorithm, x.dataset, x.param_value,
                     x.generator_count_recorded, x.generator_count))
    r = r.copy()
    r["native"] = r.algorithm.str.contains("|".join(NATIVE))
    reps = r.memory_reps.astype(str).str.split().apply(lambda v: [float(x) for x in v])
    r["mem_spread"] = [max(v) / min(v) if v and min(v) > 0 else np.nan for v in reps]
    rreps = r.runtime_reps.astype(str).str.split().apply(lambda v: [float(x) for x in v])
    r["rt_spread"] = [max(v) / min(v) if v and min(v) > 0 else np.nan for v in rreps]
    r["short"] = r.runtime_s_recorded < 0.1
    for (src, nat, short), q in r.groupby(["source", "native", "short"]):
        print("    %-7s %-6s %-9s n=%3d | memory new/recorded gmean %6.2fx [%.2f..%.2f]"
              " | repeat spread memory %.3fx runtime %.3fx (median)"
              % (src, "native" if nat else "JVM", "<0.1s" if short else ">=0.1s", len(q),
                 gmean(q.peak_memory_mb / q.peak_memory_mb_recorded),
                 (q.peak_memory_mb / q.peak_memory_mb_recorded).min(),
                 (q.peak_memory_mb / q.peak_memory_mb_recorded).max(),
                 q.mem_spread.median(), q.rt_spread.median()))
    short = r[r.short]
    spread = short.mem_spread.median()
    print("    protocol condition (median memory repeat spread < 1.25x on runs recorded"
          " under 0.1 s): %.3fx -> %s" % (spread, "MET" if spread < 1.25 else "NOT MET"))
    print()
    return spread < 1.25


def m1(r):
    """Test-retest: calibration configs were re-measured twice, once per table."""
    print("M1  noise ceiling, re-measured")
    a = r[r.source == "summary"]
    b = r[r.source == "extra"]
    m = a.merge(b, on=["algorithm", "dataset", "param_value"], suffixes=("_a", "_b"))
    if m.empty:
        print("    no configuration re-measured in both tables\n")
        return
    for obj, col in (("runtime", "runtime_s"), ("memory", "peak_memory_mb")):
        regs = []
        for (ds, p), q in m.groupby(["dataset", "param_value"]):
            if len(q) < 2:
                continue
            pick = q.loc[q[col + "_a"].idxmin()]
            regs.append(pick[col + "_b"] / q[col + "_b"].min())
        print("    %-8s best in one re-measurement, scored in the other: regret %.3fx over"
              " %d configs (recorded, cross-machine: %s)"
              % (obj, gmean(regs), len(regs), "1.106x" if obj == "runtime" else "4.95x"))
    print("    Both sides now share machine and method, so this is the repeatability"
          " floor, not a machine difference.\n")


# ----------------------------------------------------------------------
def score(ext, rec, db):
    """Per (instance, objective): pick, best, fixed-choice cost. As bs.picks."""
    from recommender.spec import MiningTask
    rows = []
    for (ds, sg), g in ext.groupby(["dataset", "param_value"]):
        for obj in ("runtime", "memory"):
            task = MiningTask(dataset=ds, threshold=float(sg), objective=obj)
            eligible = {v.algorithm for v in db.filter(task)[0]}
            cand = g[g.algorithm.isin(eligible)]
            if cand.empty:
                continue
            if obj == "memory":
                if not bs.completed(cand).all():
                    continue
                cost = dict(zip(cand.algorithm, cand.peak_memory_mb))
            else:
                cost = {a: (x if c else bs.CUTOFF * 10) for a, x, c in
                        zip(cand.algorithm, cand.runtime_s, bs.completed(cand))}
            recs, _rej, feats = rec.recommend(task)
            pick = next((x for x in recs if x.algorithm in cost), None)
            if pick is None or bs.FIXED[obj] not in cost:
                continue
            best = min(cost.values())
            rows.append({"dataset": ds, "sigma": sg, "objective": obj,
                         "regret": cost[pick.algorithm] / best,
                         "fixed_regret": cost[bs.FIXED[obj]] / best,
                         "best_runtime": g[bs.completed(g)].runtime_s.min(),
                         "outside": bool(pick.extrapolated)})
    return pd.DataFrame(rows)


def report(p, label):
    for obj in ("memory", "runtime"):
        q = p[p.objective == obj]
        if q.empty:
            continue
        print("    %-8s %3d instances, %2d datasets | regret engine %.3fx, fixed %.3fx"
              % (obj, len(q), q.dataset.nunique(), gmean(q.regret), gmean(q.fixed_regret)))


def m2_m3(rem):
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    db = CapabilityDB()
    ext_raw = pd.read_csv(EXTRA)
    ext_raw = ext_raw[ext_raw.role == "extension"]
    ext, n = apply(ext_raw, rem, "extra")
    print("M2  S2/S3 re-scored on re-measured costs (post-hoc; %d extension rows replaced)" % n)
    rec = Recommender()
    report(score(ext_raw, rec, db), "recorded")
    print("    ^ recorded costs, as bench_status scored them")
    p2 = score(ext, rec, db)
    report(p2, "re-measured")
    print("    ^ re-measured costs, same model")
    print()
    print("M3  model retrained on re-measured training labels, scored as M2")
    summ, n = apply(pd.read_csv(SUMMARY), rem, "summary")
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        summ.to_csv(fh.name, index=False)
        runs = load_runs(fh.name)
    os.unlink(fh.name)
    rec3 = Recommender(runs=runs, cache=False)
    report(score(ext, rec3, db), "retrained")
    print("    (%d training rows re-measured)\n" % n)


def m4(rem):
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    db = CapabilityDB()
    summ, _ = apply(pd.read_csv(SUMMARY), rem, "summary")
    ext = pd.read_csv(EXTRA)
    ext = ext[ext.role == "extension"]
    ext, _ = apply(ext, rem, "extra")
    both = pd.concat([summ, ext[summ.columns]], ignore_index=True)
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        both.to_csv(fh.name, index=False)
        runs = load_runs(fh.name)
    os.unlink(fh.name)
    print("M4  twelve datasets, leave one dataset out")
    parts = []
    cat1 = both[both.category == 1]
    for ds in CAT1:
        if ds not in set(cat1.dataset):
            continue
        rec = Recommender(runs=runs, exclude_dataset=ds, cache=False)
        p = score(cat1[cat1.dataset == ds], rec, db)
        parts.append(p)
        print("    held out %-10s %s" % (ds, "  ".join(
            "%s %.3f/%.3f" % (o[:3], gmean(p[p.objective == o].regret),
                              gmean(p[p.objective == o].fixed_regret))
            for o in ("memory", "runtime") if (p.objective == o).any())), flush=True)
    p = pd.concat(parts, ignore_index=True)
    print("    (engine/fixed regret per held-out dataset)")
    report(p, "all")
    for obj in ("memory", "runtime"):
        q = p[p.objective == obj]
        dss = q.dataset.unique()
        diffs = []
        for _ in range(N_BOOT):
            s = RNG.choice(dss, size=len(dss), replace=True)
            b = pd.concat([q[q.dataset == d] for d in s])
            diffs.append(np.log(gmean(b.regret)) - np.log(gmean(b.fixed_regret)))
        diffs = np.array(diffs)
        print("    %-8s engine/fixed regret ratio %.3f, 5-95%% %.3f..%.3f, P(engine better) %.2f"
              " [cluster bootstrap over %d held-out datasets]"
              % (obj, np.exp(np.median(diffs)), np.exp(np.percentile(diffs, 5)),
                 np.exp(np.percentile(diffs, 95)), (diffs < 0).mean(), len(dss)))
        for out, r in q.groupby("outside"):
            print("        %s training domain: %3d instances, engine %.3fx, fixed %.3fx"
                  % ("outside" if out else "inside ", len(r), gmean(r.regret),
                     gmean(r.fixed_regret)))
    print()
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", default=["M0", "M1", "M2", "M4"])
    args = ap.parse_args(argv)
    r_all, r = valid_remeasured()
    if "M0" in args.only:
        m0(r_all, r)
    if "M1" in args.only:
        m1(r)
    if "M2" in args.only:
        m2_m3(r)
    if "M4" in args.only:
        m4(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
