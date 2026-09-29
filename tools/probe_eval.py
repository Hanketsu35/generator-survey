"""Evaluate the subsample probe against results/PROBE_PROTOCOL.md.

    python tools/probe_eval.py --probe      # run the probes (cached, resumable)
    python tools/probe_eval.py              # score P1-P3, both extrapolations

Probes run one at a time: the probe's wall-clock time is itself a measured
cost (it is charged to the probe on the runtime objective), so it must not
share the machine with another run.
"""
import argparse
import csv
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

from recommender import probe as P                        # noqa: E402

TABLE = _ROOT / "results" / "training_runs.csv"
POINTS = _ROOT / "results" / "probe_points.csv"
OUT = _ROOT / "results" / "probe_eval_output.txt"
CUTOFF = 3600.0
FIXED = {"runtime": "FPgrowth_Gen_Borgelt", "memory": "Apriori_Gen_Borgelt"}
REF = "Gr_growth"
N_BOOT = 2000
RNG = np.random.default_rng(20260929)
EXT2 = {"chicago", "kddcup99", "onlineretail", "pamap", "recordlink"}


def completed(df):
    return (df.timed_out.astype(str).str.lower() != "true") & df.error.isna()


def dataset_path(ds):
    from recommender import metafeatures as mf
    try:
        p = mf.dataset_path(ds)
        if os.path.exists(p):
            return p
    except Exception:                                     # noqa: BLE001
        pass
    return str(_ROOT / "datasets" / "raw" / ("%s.txt" % ds))


def instances():
    t = pd.read_csv(TABLE)
    t = t[t.category == 1]
    return sorted({(d, float(p)) for d, p in zip(t.dataset, t.param_value)})


# ---------------------------------------------------------------------------
def run_probes():
    done = set()
    if POINTS.exists():
        d = pd.read_csv(POINTS)
        done = {(a, round(b, 9)) for a, b in zip(d.dataset, d.sigma)}
    todo = [(d, s) for d, s in instances() if (d, round(s, 9)) not in done]
    print("%d instances to probe (%d cached)" % (len(todo), len(done)), flush=True)
    header = not POINTS.exists()
    with open(POINTS, "a", newline="") as fh:
        w = csv.writer(fh)
        if header:
            w.writerow(["dataset", "sigma", "n", "mode", "wall_s", "algorithm", "size",
                        "memory_mb", "runtime_s"])
        for i, (ds, s) in enumerate(todo, 1):
            r = P.probe(dataset_path(ds), s)
            for a in P.PROBED:
                pts = r.points.get(a) or []
                if not pts:
                    w.writerow([ds, s, r.n, r.mode, r.wall_s, a, "", "", ""])
                for size, (m, t) in pts:
                    w.writerow([ds, s, r.n, r.mode, r.wall_s, a, size, m, t])
            fh.flush()
            print("[%3d/%3d] %-13s %-10g %-8s %6.1fs" % (i, len(todo), ds, s, r.mode, r.wall_s),
                  flush=True)


def probe_costs(variant):
    """{(ds, sigma): {"wall": s, "mode": m, "costs": {algo: (mem, rt, measured?)}}}"""
    d = pd.read_csv(POINTS)
    out = {}
    for (ds, s), g in d.groupby(["dataset", "sigma"]):
        rec = {"wall": float(g.wall_s.iloc[0]), "mode": g["mode"].iloc[0], "costs": {}}
        n = int(g.n.iloc[0])
        for a, h in g.groupby("algorithm"):
            h = h.dropna(subset=["size"]).sort_values("size")
            pts = [(int(r.size), (r.memory_mb, r.runtime_s)) for r in h.itertuples()]
            if rec["mode"] == "direct":
                if pts:
                    rec["costs"][a] = (pts[0][1][0], pts[0][1][1], True)
            else:
                e = P.estimate(pts, n, variant)
                if e:
                    rec["costs"][a] = (e[0], e[1], False)
        out[(ds, round(float(s), 9))] = rec
    return out


# ---------------------------------------------------------------------------
def gmean(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.log(x).mean())) if x.size else float("nan")


def evaluate(variant):
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    from recommender.spec import MiningTask
    runs = load_runs(str(TABLE))
    truth = pd.read_csv(TABLE)
    truth = truth[truth.category == 1]
    pc = probe_costs(variant)
    db = CapabilityDB()
    rows, acc = [], []
    for ds in sorted(truth.dataset.unique()):
        rec = Recommender(runs=runs, exclude_dataset=ds)
        for sg, g in truth[truth.dataset == ds].groupby("param_value"):
            key = (ds, round(float(sg), 9))
            if key not in pc:
                continue
            pr = pc[key]
            for obj in ("memory", "runtime"):
                task = MiningTask(dataset_path=dataset_path(ds), data_type="transactional",
                                  threshold=float(sg), objective=obj)
                eligible = {v.algorithm for v in db.filter(task)[0]}
                cand = g[g.algorithm.isin(eligible)]
                if cand.empty:
                    continue
                ok = completed(cand)
                if obj == "memory":
                    if not ok.all():
                        continue
                    cost = dict(zip(cand.algorithm, cand.peak_memory_mb))
                else:
                    cost = {a: (x if c else CUTOFF * 10) for a, x, c in
                            zip(cand.algorithm, cand.runtime_s, ok)}
                recs, _rej, _f = rec.recommend(task)
                model = {r.algorithm: (r.memory_mb, r.runtime_s) for r in recs}
                eng = next((r.algorithm for r in recs if r.algorithm in cost), None)
                if eng is None:
                    continue
                est = {}
                for a in cost:
                    if a in pr["costs"]:
                        m, t, _meas = pr["costs"][a]
                        est[a] = m if obj == "memory" else t
                    elif a in model:
                        est[a] = model[a][0] if obj == "memory" else model[a][1]
                pick = min(est, key=est.get) if est else eng
                best = min(cost.values())
                realized = cost[pick]
                if obj == "runtime":
                    meas = pr["costs"].get(pick, (None, None, False))[2]
                    realized = pr["wall"] + (0.0 if meas else cost[pick])
                rows.append({"dataset": ds, "sigma": sg, "objective": obj, "ext2": ds in EXT2,
                             "engine": cost[eng] / best, "probe": realized / best,
                             "fixed": cost.get(FIXED[obj], np.nan) / best,
                             "gr": cost.get(REF, np.nan) / best, "wall": pr["wall"],
                             "mode": pr["mode"], "pick": pick, "eng_pick": eng,
                             "eng_pred_rt": model[eng][1],
                             "eng_cost": cost[eng], "probe_cost": realized, "best": best})
                if obj == "memory":
                    for a, (m, t, meas) in pr["costs"].items():
                        if a in cost and not meas and a in model:
                            tr = g[g.algorithm == a].iloc[0]
                            acc.append({"algorithm": a, "dataset": ds,
                                        "probe_mem": abs(math.log10(m / tr.peak_memory_mb)) if m > 0 else np.nan,
                                        "model_mem": abs(math.log10(model[a][0] / tr.peak_memory_mb)),
                                        "probe_rt": abs(math.log10(max(t, 1e-3) / max(tr.runtime_s, 1e-3))),
                                        "model_rt": abs(math.log10(max(model[a][1], 1e-3) / max(tr.runtime_s, 1e-3)))})
    return pd.DataFrame(rows), pd.DataFrame(acc)


def boot(q, a, b):
    """P(a's gmean regret < b's) over held-out datasets, and the ratio band."""
    dss = q.dataset.unique()
    diffs = []
    for _ in range(N_BOOT):
        s = RNG.choice(dss, size=len(dss), replace=True)
        x = pd.concat([q[q.dataset == d] for d in s])
        diffs.append(np.log(gmean(x[a])) - np.log(gmean(x[b])))
    diffs = np.array(diffs)
    return (diffs < 0).mean(), np.exp(np.percentile(diffs, [5, 50, 95]))


def report(variant, p, acc, lines):
    L = lines.append
    L("=" * 78)
    L("VARIANT: %s%s" % (variant, "  (amended after one smoke-test instance)" if variant == "affine" else "  (registered)"))
    L("=" * 78)
    for obj in ("memory", "runtime"):
        q = p[p.objective == obj]
        L("%-8s %3d instances, %2d datasets | engine %.3fx  probe %.3fx  fixed %.3fx  always-Gr %.3fx"
          % (obj, len(q), q.dataset.nunique(), gmean(q.engine), gmean(q.probe), gmean(q.fixed), gmean(q.gr)))
        for ext, r in q.groupby("ext2"):
            L("         %-19s %3d | engine %.3fx  probe %.3fx  fixed %.3fx"
              % ("second extension" if ext else "other twelve", len(r), gmean(r.engine),
                 gmean(r.probe), gmean(r.fixed)))
    m, r = p[p.objective == "memory"], p[p.objective == "runtime"]
    pb, band = boot(m, "probe", "engine")
    L("P1 memory, probe < engine: ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
      % (band[1], band[0], band[2], pb, "PASS" if pb >= 0.95 and gmean(m.probe) < gmean(m.engine) else "FAIL"))
    pb2, band2 = boot(m, "probe", "fixed")
    L("P2 memory, probe < fixed : ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
      % (band2[1], band2[0], band2[2], pb2, "PASS" if pb2 >= 0.95 and gmean(m.probe) < gmean(m.fixed) else "FAIL"))
    ratio = gmean(r.probe) / gmean(r.engine)
    L("P3 runtime incl. probe cost: probe/engine %.3f (bar <= 1.10) -> %s"
      % (ratio, "PASS" if ratio <= 1.10 else "FAIL"))
    L("probe wall-clock: median %.2fs, max %.1fs (%s)" % (
        p.drop_duplicates(["dataset", "sigma"]).wall.median(),
        p.drop_duplicates(["dataset", "sigma"]).wall.max(),
        p.drop_duplicates(["dataset", "sigma"])["mode"].value_counts().to_dict()))
    if len(acc):
        L("extrapolation accuracy on sampled instances, |log10 error| median (probe vs model):")
        for a, g in acc.groupby("algorithm"):
            L("   %-22s memory %.3f vs %.3f   runtime %.3f vs %.3f  (n=%d)"
              % (a, g.probe_mem.median(), g.model_mem.median(), g.probe_rt.median(),
                 g.model_rt.median(), len(g)))
    L("")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args(argv)
    if args.probe:
        run_probes()
        return 0
    lines = []
    for variant in ("loglog", "affine"):
        p, acc = evaluate(variant)
        report(variant, p, acc, lines)
        p.to_csv(_ROOT / "results" / ("probe_eval_%s.csv" % variant), index=False)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
