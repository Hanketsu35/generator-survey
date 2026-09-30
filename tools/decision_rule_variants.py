"""Post hoc: the engine's memory pick under probe-rule variants, on every
instance probed so far (training LODO, both confirmations).

    python tools/decision_rule_variants.py

Variants: upper-end rule alone (as of a575497); plus lower bounds from miners
stopped in their probe; plus the probe's scale applied to model estimates
(beta 0.5), with the two interval forms for a stopped miner. Uses the engine
itself, with ProbeResults rebuilt from the recorded probe points and
results/probe_lower_bounds.csv. Output: results/decision_rule_variants.csv.
All of this data has been seen; nothing here is a confirmation.
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
from recommender import engine as E                       # noqa: E402
from recommender import probe as P                        # noqa: E402

FAIL = 10.0
SETS = [("training LODO", "results/training_runs.csv", "results/probe_points.csv", True),
        ("confirm", "results/real_extra3_summary.csv", "results/probe_points_confirm.csv", False),
        ("hard", "results/hard_summary.csv", "results/probe_points_hard.csv", False)]
VARIANTS = {"upper": dict(lb=False, beta=0.0, lbi="scaled"),
            "upper+lb": dict(lb=True, beta=0.0, lbi="scaled"),
            "upper+lb floor": dict(lb=True, beta=0.0, lbi="floor"),
            "upper+lb+scale": dict(lb=True, beta=0.5, lbi="scaled"),
            "upper+lb floor+scale": dict(lb=True, beta=0.5, lbi="floor")}


def probes(points, lbs):
    d = pd.read_csv(points)
    out = {}
    for (ds, sg), g in d.groupby(["dataset", "sigma"]):
        mode = g["mode"].iloc[0]
        r = P.ProbeResult(n=int(g.n.iloc[0]), sigma=float(sg), mode=mode, sizes=[],
                          wall_s=float(g.wall_s.iloc[0]))
        for a, h in g.groupby("algorithm"):
            h = h.dropna(subset=["size"]).sort_values("size")
            pts = [(int(q.size), (q.memory_mb, q.runtime_s)) for q in h.itertuples()]
            if mode == "direct" and pts:
                r.costs[a] = {"memory_mb": pts[0][1][0], "runtime_s": pts[0][1][1], "mode": "measured"}
            elif mode == "sampled" and len(pts) >= 2:
                m, t = P.estimate(pts, r.n, "affine")
                r.costs[a] = {"memory_mb": m, "runtime_s": t, "mode": "extrapolated"}
            else:
                r.costs[a] = {"mode": "failed"}
                hit = lbs[(lbs.dataset == ds) & (np.isclose(lbs.sigma, sg)) & (lbs.algorithm == a)]
                if len(hit):
                    r.costs[a].update(memory_lb=float(hit.memory_lb.iloc[0]), why=hit.why.iloc[0])
        out[(ds, round(float(sg), 9))] = r
    return out


def strip_lb(pr):
    q = P.ProbeResult(pr.n, pr.sigma, pr.mode, pr.sizes, pr.wall_s)
    q.costs = {a: {k: v for k, v in c.items() if k not in ("memory_lb", "why")}
               for a, c in pr.costs.items()}
    return q


def main():
    from recommender.capabilities import CapabilityDB
    from recommender.perfmodel import load_runs
    from recommender.spec import MiningTask
    db = CapabilityDB()
    lbs = pd.read_csv(_ROOT / "results" / "probe_lower_bounds.csv")
    runs = load_runs(str(PE.TABLE))
    cache = {}
    rows = []
    for name, truth, points, lodo in SETS:
        t = pd.read_csv(truth)
        if "category" in t:
            t = t[t.category == 1]
        pcs = probes(points, lbs)
        for (ds, sg), g in t.groupby(["dataset", "param_value"]):
            pr = pcs.get((ds, round(float(sg), 9)))
            if pr is None:
                continue
            key = ds if lodo else None
            if key not in cache:
                cache[key] = (E.Recommender(runs=runs, exclude_dataset=ds) if lodo
                              else E.Recommender())
            rec = cache[key]
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                              threshold=float(sg), objective="memory")
            el = {v.algorithm for v in db.filter(task)[0]}
            c = g[g.algorithm.isin(el)]
            ok = PE.completed(c)
            done = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
            if not done:
                continue
            best = min(done.values())
            allc = set(c.algorithm)
            row = {"set": name, "dataset": ds, "sigma": sg, "all_ok": bool(ok.all()),
                   "any_lb": any("memory_lb" in x for x in pr.costs.values())}
            recs, _r, _f = rec.recommend(task)
            eng = next(r.algorithm for r in recs if r.algorithm in allc)
            row["engine"] = done[eng] / best if eng in done else FAIL
            for v, cfg in VARIANTS.items():
                E.PROBE_SCALE_BETA, E.LB_INTERVAL = cfg["beta"], cfg["lbi"]
                recs, _r, _f = rec.recommend(task, probe=pr if cfg["lb"] else strip_lb(pr))
                pick = next(r.algorithm for r in recs if r.algorithm in allc)
                row[v] = done[pick] / best if pick in done else FAIL
                row[v + " pick"] = pick
            rows.append(row)
        print(name, "done", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "decision_rule_variants.csv", index=False)
    cols = ["engine"] + list(VARIANTS)
    g = PE.gmean
    for (s, a), q in d.groupby(["set", "all_ok"]):
        print("%-14s all-complete=%-5s n=%3d | %s" % (s, a, len(q), "  ".join(
            "%s %.3f" % (c, g(q[c])) for c in cols)))
    print("ALL n=%d | %s" % (len(d), "  ".join("%s %.3f" % (c, g(d[c])) for c in cols)))
    print("failed picks: %s" % "  ".join("%s %d" % (c, (d[c] == FAIL).sum()) for c in cols))
    q = d[d.any_lb]
    print("instances with a stopped native (n=%d): %s" % (len(q), "  ".join(
        "%s %.3f" % (c, g(q[c])) for c in cols)))


if __name__ == "__main__":
    main()
