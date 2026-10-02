"""Score results/LAG_PROTOCOL.md.

    python tools/lag_eval.py
"""
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

FE.TRUTH = _ROOT / "results" / "lag_summary.csv"
FE.PROBES = _ROOT / "results" / "probe_lag.jsonl"
OUT = _ROOT / "results" / "lag_eval_output.txt"
FAIL = 10.0


def frozen_ok():
    import hashlib
    import subprocess
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/LAG_PROTOCOL.md"],
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


def main():
    if not frozen_ok():
        return 2
    from recommender import engine as E
    from recommender.capabilities import CapabilityDB
    from recommender.spec import MiningTask
    rec, db = E.Recommender(), CapabilityDB()
    probes = FE.load_probes()
    sel = pd.read_csv(_ROOT / "results" / "lag_instances.csv")
    t = pd.read_csv(FE.TRUTH)
    rows = []
    for s in sel.itertuples():
        g = t[(t.dataset == s.dataset) & ((t.param_value - s.sigma).abs() < 1e-9)]
        pr = probes[(s.dataset, round(float(s.sigma), 9))]
        task = MiningTask(dataset_path=PE.dataset_path(s.dataset), data_type="transactional",
                          threshold=float(s.sigma), objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        c = g[g.algorithm.isin(el)]
        ok = PE.completed(c)
        done = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
        if not done:
            rows.append({"dataset": s.dataset, "sigma": s.sigma, "note": "no eligible miner completed"})
            continue
        best, bench = min(done.values()), set(c.algorithm)
        reg = lambda a: done[a] / best if a in done else FAIL       # noqa: E731
        pick = lambda recs: next(r.algorithm for r in recs if r.algorithm in bench)  # noqa: E731
        E.PROGRESS_DEMOTE = False
        s_pick = pick(rec.recommend(task, probe=pr)[0])
        E.PROGRESS_DEMOTE = True
        d_pick = pick(rec.recommend(task, probe=pr)[0])
        prog = E.Recommender._probe_progress(pr)
        rows.append({"dataset": s.dataset, "sigma": s.sigma, "mode": pr.mode,
                     "best": min(done, key=done.get), "best_mb": best,
                     "S_pick": s_pick, "S": reg(s_pick), "D_pick": d_pick, "D": reg(d_pick),
                     "progress": {a[:6]: round(v, 2) for a, v in prog.items()},
                     "failed": ",".join(sorted(bench - set(done)))})
    p = pd.DataFrame(rows)
    p.to_csv(_ROOT / "results" / "lag_eval_rows.csv", index=False)
    q = p.dropna(subset=["S"]) if "S" in p else p.iloc[0:0]
    g = PE.gmean
    L = []
    for r in p.itertuples():
        if getattr(r, "note", None) == getattr(r, "note", None) and isinstance(getattr(r, "note", None), str):
            L.append("  %-14s %-11.6g %s" % (r.dataset, r.sigma, r.note))
            continue
        L.append("  %-14s %-11.6g %-7s best %-20s %8.1f MB | S %-20s %5.2f | D %-20s %5.2f | %s | failed: %s"
                 % (r.dataset, r.sigma, r.mode, r.best, r.best_mb, r.S_pick, r.S, r.D_pick, r.D,
                    r.progress, r.failed or "-"))
    if len(q) < 4:
        L.append("%d scorable instances: underpowered, no pass or fail" % len(q))
    else:
        fs, fd = (q.S == FAIL).sum(), (q.D == FAIL).sum()
        L.append("%d instances | S %.3fx  D %.3fx | failed S %d D %d"
                 % (len(q), g(q.S), g(q.D), fs, fd))
        L.append("L1 D < S and failed D <= S -> %s" % ("PASS" if g(q.D) < g(q.S) and fd <= fs else "FAIL"))
        ch = q[q.S_pick != q.D_pick]
        better, worse = (ch.D < ch.S).sum(), (ch.D > ch.S).sum()
        L.append("L2 changed picks %d: D better %d, worse %d -> %s"
                 % (len(ch), better, worse, "PASS" if better > worse else "FAIL"))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
