"""Score results/FRESH_PROTOCOL.md.

    python tools/fresh_eval.py --probe    # probe every instance (after the benchmark)
    python tools/fresh_eval.py            # F1-F4

Refuses to score if a frozen input changed since the protocol's commit.
"""
import argparse
import hashlib
import json
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

TRUTH = _ROOT / "results" / "fresh_summary.csv"
PROBES = _ROOT / "results" / "probe_fresh.jsonl"
OUT = _ROOT / "results" / "fresh_eval_output.txt"
FROZEN = ["recommender/engine.py", "recommender/probe.py", "recommender/intervals.py",
          "recommender/data/intervals.json", "recommender/perfmodel.py",
          "results/training_runs.csv"]
FAIL = 10.0


def frozen_ok():
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/FRESH_PROTOCOL.md"],
                       capture_output=True, text=True, check=True).stdout.strip()
    ok = True
    for path in FROZEN:
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (c, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, c))
            ok = False
    return ok


def instances():
    t = pd.read_csv(TRUTH)
    return sorted({(d, float(s)) for d, s in zip(t.dataset, t.param_value)})


def run_probes():
    from recommender import probe as P
    done = set()
    if PROBES.exists():
        for line in PROBES.read_text().splitlines():
            r = json.loads(line)
            done.add((r["dataset"], round(r["sigma"], 9)))
    todo = [(d, s) for d, s in instances() if (d, round(s, 9)) not in done]
    print("%d instances to probe (%d cached)" % (len(todo), len(done)), flush=True)
    with open(PROBES, "a") as fh:
        for i, (ds, s) in enumerate(todo, 1):
            r = P.probe(PE.dataset_path(ds), s)
            fh.write(json.dumps({"dataset": ds, "sigma": s, "n": r.n, "mode": r.mode,
                                 "sizes": r.sizes, "wall_s": r.wall_s, "costs": r.costs,
                                 "points": {a: [[z, list(v)] for z, v in p]
                                            for a, p in r.points.items()}}) + "\n")
            fh.flush()
            print("[%2d/%2d] %-14s %-10g %-7s %6.1fs" % (i, len(todo), ds, s, r.mode, r.wall_s),
                  flush=True)


def load_probes():
    from recommender import probe as P
    out = {}
    for line in PROBES.read_text().splitlines():
        r = json.loads(line)
        pr = P.ProbeResult(n=r["n"], sigma=r["sigma"], mode=r["mode"], sizes=r["sizes"],
                           wall_s=r["wall_s"], costs=r["costs"],
                           points={a: [(z, tuple(v)) for z, v in p] for a, p in r["points"].items()})
        out[(r["dataset"], round(r["sigma"], 9))] = pr
    return out


def score():
    from recommender import intervals as I
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    rec, db = Recommender(), CapabilityDB()
    probes = load_probes()
    t = pd.read_csv(TRUTH)
    rows, cov = [], []
    for (ds, sg), g in t.groupby(["dataset", "param_value"]):
        pr = probes.get((ds, round(float(sg), 9)))
        if pr is None:
            continue
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        c = g[g.algorithm.isin(el)]
        ok = PE.completed(c)
        done = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
        bench = set(c.algorithm)
        recs_a, _r, _f = rec.recommend(task)
        recs_c, _r, _f = rec.recommend(task, probe=pr)
        model = {r.algorithm: r.memory_mb for r in recs_a}
        # coverage (F4) on every completed eligible run
        for r in recs_a:
            if r.algorithm in done and r.memory_interval:
                lo, hi = r.memory_interval
                cov.append({"dataset": ds, "kind": "model", "hit": lo <= done[r.algorithm] <= hi})
        for r in recs_c:
            if r.algorithm in done and r.prediction_source.startswith("probe") and r.memory_interval:
                lo, hi = r.memory_interval
                cov.append({"dataset": ds, "kind": "probe", "hit": lo <= done[r.algorithm] <= hi})
        if not done:
            continue
        best = min(done.values())
        reg = lambda a: done[a] / best if a in done else FAIL       # noqa: E731
        a_pick = next(r.algorithm for r in recs_a if r.algorithm in bench)
        c_pick = next(r.algorithm for r in recs_c if r.algorithm in bench)
        est = {}
        for a in bench:
            pc = pr.costs.get(a) or {}
            if pc.get("memory_mb") is not None:
                est[a] = pc["memory_mb"]
            elif a in model:
                est[a] = model[a]
        b_pick = min(est, key=est.get)
        rows.append({"dataset": ds, "sigma": sg, "mode": pr.mode, "wall_s": pr.wall_s,
                     "all_ok": bool(ok.all()), "best": min(done, key=done.get), "best_mb": best,
                     "A": reg(a_pick), "B": reg(b_pick), "C": reg(c_pick),
                     "A_pick": a_pick, "B_pick": b_pick, "C_pick": c_pick,
                     "failed": ",".join(sorted(bench - set(done)))})
    p, cv = pd.DataFrame(rows), pd.DataFrame(cov)
    p.to_csv(_ROOT / "results" / "fresh_eval_rows.csv", index=False)
    g = PE.gmean
    L = []
    for r in p.itertuples():
        L.append("  %-14s %-10.6g %-7s best %-20s %8.1f MB | A %-20s %5.2f | B %-20s %5.2f | C %-20s %5.2f | failed: %s"
                 % (r.dataset, r.sigma, r.mode, r.best, r.best_mb, r.A_pick, r.A, r.B_pick, r.B,
                    r.C_pick, r.C, r.failed or "-"))
    L.append("%d instances, %d datasets | A engine %.3fx  B registered probe rule %.3fx  C shipped %.3fx"
             % (len(p), p.dataset.nunique(), g(p.A), g(p.B), g(p.C)))
    for ds, q in p.groupby("dataset"):
        L.append("   %-14s n=%d  A %.3f  B %.3f  C %.3f" % (ds, len(q), g(q.A), g(q.B), g(q.C)))
    pb, band = PE.boot(p, "C", "A")
    L.append("F1 C < A: ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
             % (band[1], band[0], band[2], pb, "PASS" if pb >= 0.95 and g(p.C) < g(p.A) else "FAIL"))
    L.append("F2 C <= 1.02 x B: %.3f vs %.3f -> %s"
             % (g(p.C), 1.02 * g(p.B), "PASS" if g(p.C) <= 1.02 * g(p.B) else "FAIL"))
    fa, fb, fc = [(p[k] == FAIL).sum() for k in ("A", "B", "C")]
    L.append("F3 failed picks: A %d  B %d  C %d -> %s"
             % (fa, fb, fc, "PASS" if fc <= fa and fc <= fb else "FAIL"))
    for k in ("model", "probe"):
        q = cv[cv.kind == k]
        per = q.groupby("dataset").hit.mean()
        L.append("F4 %-5s memory interval coverage %.3f (n=%d; per dataset min %.2f) -> %s"
                 % (k, q.hit.mean(), len(q), per.min(), "PASS" if q.hit.mean() >= 0.85 else "FAIL"))
    L.append("probe wall-clock: median %.1fs, max %.1fs" % (p.wall_s.median(), p.wall_s.max()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args(argv)
    if not frozen_ok():
        return 2
    if args.probe:
        run_probes()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
