"""Post hoc: demote a probed miner that finished fewer probe runs than another.

    python tools/progress_posthoc.py

Runs the engine on every instance probed so far (training LODO, the first
confirmation, the hard thresholds, both fresh confirmations), with the
probe's costs recomputed in the current form, with and without
engine.PROGRESS_DEMOTE. All of this data has been seen; nothing here is a
confirmation. Output: results/progress_posthoc.csv
"""
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

import fresh_eval as FE                                    # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import engine as E                       # noqa: E402
from recommender import probe as P                        # noqa: E402

FAIL = 10.0


def from_csv(points, lbs):
    d = pd.read_csv(points)
    out = {}
    for (ds, sg), g in d.groupby(["dataset", "sigma"]):
        n, mode = int(g.n.iloc[0]), g["mode"].iloc[0]
        s1 = max(P.MIN_SAMPLE, math.ceil(P.MIN_ABS_SUPPORT / sg))
        sizes = [n] if mode == "direct" else [s1, P.GROWTH * s1, P.GROWTH ** 2 * s1]
        r = P.ProbeResult(n=n, sigma=float(sg), mode=mode, sizes=sizes,
                          wall_s=float(g.wall_s.iloc[0]))
        for a, h in g.groupby("algorithm"):
            h = h.dropna(subset=["size"]).sort_values("size")
            pts = [(int(q.size), (q.memory_mb, q.runtime_s)) for q in h.itertuples()]
            r.points[a] = pts
            if mode == "direct" and pts:
                r.costs[a] = {"memory_mb": pts[0][1][0], "runtime_s": pts[0][1][1], "mode": "measured"}
            elif mode == "sampled" and len(pts) >= 2:
                m, t = P.estimate(pts, n, "affine", a)
                r.costs[a] = {"memory_mb": m, "runtime_s": t, "mode": "extrapolated"}
            else:
                r.costs[a] = {"mode": "failed"}
                hit = lbs[(lbs.dataset == ds) & np.isclose(lbs.sigma, sg) & (lbs.algorithm == a)]
                if len(hit):
                    r.costs[a].update(memory_lb=float(hit.memory_lb.iloc[0]), why=hit.why.iloc[0])
        out[(ds, round(float(sg), 9))] = r
    return out


def from_jsonl(path):
    import fresh2_eval as F2
    FE.PROBES = Path(path)
    return {k: F2.with_form(v, "affine") for k, v in FE.load_probes().items()}


def main():
    from recommender.capabilities import CapabilityDB
    from recommender.perfmodel import load_runs
    from recommender.spec import MiningTask
    db = CapabilityDB()
    lbs = pd.read_csv(_ROOT / "results" / "probe_lower_bounds.csv")
    tr = pd.read_csv(PE.TABLE)
    sets = [("training LODO", tr[tr.category == 1], from_csv("results/probe_points.csv", lbs), True),
            ("confirm", pd.read_csv("results/real_extra3_summary.csv"),
             from_csv("results/probe_points_confirm.csv", lbs), False),
            ("hard", pd.read_csv("results/hard_summary.csv"),
             from_csv("results/probe_points_hard.csv", lbs), False),
            ("fresh", pd.read_csv("results/fresh_summary.csv"), from_jsonl("results/probe_fresh.jsonl"), False),
            ("fresh2", pd.read_csv("results/fresh2_summary.csv"), from_jsonl("results/probe_fresh2.jsonl"), False)]
    runs = load_runs(str(PE.TABLE))
    cache, rows = {}, []
    for name, truth, probes, lodo in sets:
        for (ds, sg), g in truth.groupby(["dataset", "param_value"]):
            pr = probes.get((ds, round(float(sg), 9)))
            if pr is None:
                continue
            key = ds if lodo else None
            if key not in cache:
                cache[key] = E.Recommender(runs=runs, exclude_dataset=ds) if lodo else E.Recommender()
            rec = cache[key]
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                              threshold=float(sg), objective="memory")
            el = {v.algorithm for v in db.filter(task)[0]}
            c = g[g.algorithm.isin(el)]
            ok = PE.completed(c)
            done = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
            if not done:
                continue
            best, bench = min(done.values()), set(c.algorithm)
            reg = lambda a: done[a] / best if a in done else FAIL       # noqa: E731
            pick = lambda recs: next(r.algorithm for r in recs if r.algorithm in bench)  # noqa: E731
            row = {"set": name, "dataset": ds, "sigma": sg, "mode": pr.mode}
            row["A_pick"] = pick(rec.recommend(task)[0])
            for v, flag in (("shipped", False), ("progress", True)):
                E.PROGRESS_DEMOTE = flag
                row[v + "_pick"] = pick(rec.recommend(task, probe=pr)[0])
            E.PROGRESS_DEMOTE = False
            for k in ("A", "shipped", "progress"):
                row[k] = reg(row[k + "_pick"])
            rows.append(row)
        print(name, "done", flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "progress_posthoc.csv", index=False)
    g = PE.gmean
    for s, q in d.groupby("set", sort=False):
        print("%-14s n=%3d | engine %.3f  shipped %.3f  progress %.3f | failed %d %d %d"
              % (s, len(q), g(q.A), g(q.shipped), g(q.progress), (q.A == FAIL).sum(),
                 (q.shipped == FAIL).sum(), (q.progress == FAIL).sum()))
    print("ALL n=%d | engine %.3f  shipped %.3f  progress %.3f | failed %d %d %d"
          % (len(d), g(d.A), g(d.shipped), g(d.progress), (d.A == FAIL).sum(),
             (d.shipped == FAIL).sum(), (d.progress == FAIL).sum()))
    ch = d[d.shipped_pick != d.progress_pick]
    print("changed picks: %d" % len(ch))
    print(ch[["set", "dataset", "sigma", "mode", "shipped_pick", "shipped", "progress_pick", "progress"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
