"""Score results/FRESH3_PROTOCOL.md.

    python tools/fresh3_eval.py --probe
    python tools/fresh3_eval.py
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import fresh_eval as FE                                    # noqa: E402
import probe_eval as PE                                    # noqa: E402

FE.TRUTH = _ROOT / "results" / "fresh3_summary.csv"
FE.PROBES = _ROOT / "results" / "probe_fresh3.jsonl"
OUT = _ROOT / "results" / "fresh3_eval_output.txt"
FAIL = 10.0


def frozen_ok():
    import hashlib
    import subprocess
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/FRESH3_PROTOCOL.md"],
                       capture_output=True, text=True, check=True).stdout.strip()
    ok = True
    for path in FE.FROZEN:
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (c, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, c))
            ok = False
    return ok


def score():
    from recommender import engine as E
    from recommender.capabilities import CapabilityDB
    from recommender.spec import MiningTask
    rec, db = E.Recommender(), CapabilityDB()
    probes = FE.load_probes()
    t = pd.read_csv(FE.TRUTH)
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
        recs_d = rec.recommend(task, probe=pr)[0]
        for r in recs_d:
            if r.algorithm in done and r.prediction_source.startswith("probe") and r.memory_interval:
                lo, hi = r.memory_interval
                cov.append({"dataset": ds, "hit": lo <= done[r.algorithm] <= hi})
        if not done:
            continue
        best, bench = min(done.values()), set(c.algorithm)
        reg = lambda a: done[a] / best if a in done else FAIL       # noqa: E731
        pick = lambda recs: next(r.algorithm for r in recs if r.algorithm in bench)  # noqa: E731
        E.PROGRESS_DEMOTE = False
        s_pick = pick(rec.recommend(task, probe=pr)[0])
        E.PROGRESS_DEMOTE = True
        a_pick, d_pick = pick(rec.recommend(task)[0]), pick(recs_d)
        prog = E.Recommender._probe_progress(pr)
        rows.append({"dataset": ds, "sigma": sg, "mode": pr.mode, "best": min(done, key=done.get),
                     "best_mb": best, "A": reg(a_pick), "S": reg(s_pick), "D": reg(d_pick),
                     "A_pick": a_pick, "S_pick": s_pick, "D_pick": d_pick,
                     "progress": {a[:6]: round(v, 2) for a, v in prog.items()},
                     "failed": ",".join(sorted(bench - set(done)))})
    p, cv = pd.DataFrame(rows), pd.DataFrame(cov)
    p.to_csv(_ROOT / "results" / "fresh3_eval_rows.csv", index=False)
    g = PE.gmean
    L = []
    for r in p.itertuples():
        L.append("  %-10s %-10.6g %-7s best %-20s %8.1f MB | A %-20s %5.2f | S %-20s %5.2f | D %-20s %5.2f | %s | failed: %s"
                 % (r.dataset, r.sigma, r.mode, r.best, r.best_mb, r.A_pick, r.A, r.S_pick, r.S,
                    r.D_pick, r.D, r.progress, r.failed or "-"))
    fa, fs, fd = [(p[k] == FAIL).sum() for k in ("A", "S", "D")]
    L.append("%d instances, %d datasets | A engine %.3fx  S flag off %.3fx  D shipped %.3fx | failed A %d S %d D %d"
             % (len(p), p.dataset.nunique(), g(p.A), g(p.S), g(p.D), fa, fs, fd))
    L.append("changed picks (S -> D): %d" % (p.S_pick != p.D_pick).sum())
    L.append("P1 D <= S and failed D <= S: %.3f vs %.3f, %d vs %d -> %s"
             % (g(p.D), g(p.S), fd, fs, "PASS" if g(p.D) <= g(p.S) and fd <= fs else "FAIL"))
    pb, band = PE.boot(p, "D", "A")
    L.append("P2 D < A: ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
             % (band[1], band[0], band[2], pb, "PASS" if pb >= 0.95 and g(p.D) < g(p.A) else "FAIL"))
    L.append("P3 probe memory interval coverage %.3f (n=%d) -> %s"
             % (cv.hit.mean(), len(cv), "PASS" if cv.hit.mean() >= 0.85 else "FAIL"))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args(argv)
    if not frozen_ok():
        return 2
    if args.probe:
        FE.run_probes()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
