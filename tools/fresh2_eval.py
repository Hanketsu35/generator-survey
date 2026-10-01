"""Score results/FRESH2_PROTOCOL.md.

    python tools/fresh2_eval.py --probe    # probe every instance (after the benchmark)
    python tools/fresh2_eval.py            # G1-G4
"""
import argparse
import copy
import math
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

FE.TRUTH = _ROOT / "results" / "fresh2_summary.csv"
FE.PROBES = _ROOT / "results" / "probe_fresh2.jsonl"
OUT = _ROOT / "results" / "fresh2_eval_output.txt"
FAIL = 10.0


def frozen_ok():
    import hashlib
    import subprocess
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/FRESH2_PROTOCOL.md"],
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


def with_form(pr, variant):
    """The probe result with sampled costs recomputed in ``variant``."""
    from recommender import probe as P
    q = copy.deepcopy(pr)
    if q.mode != "sampled":
        return q
    for a, pts in q.points.items():
        if len(pts) >= 2 and q.costs.get(a, {}).get("mode") == "extrapolated":
            m, t = P.estimate(pts, q.n, variant, a)
            q.costs[a] = dict(q.costs[a], memory_mb=m, runtime_s=t)
    return q


def score():
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    rec, db = Recommender(), CapabilityDB()
    probes = FE.load_probes()
    t = pd.read_csv(FE.TRUTH)
    rows, acc, cov = [], [], []
    for (ds, sg), g in t.groupby(["dataset", "param_value"]):
        pr = probes.get((ds, round(float(sg), 9)))
        if pr is None:
            continue
        p1, p2 = with_form(pr, "affine_plain"), with_form(pr, "affine")
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        c = g[g.algorithm.isin(el)]
        ok = PE.completed(c)
        done = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
        # G1: Gr-growth accuracy, both forms, same points
        gp = pr.points.get("Gr_growth") or []
        if pr.mode == "sampled" and "Gr_growth" in done and len(gp) >= 2:
            clean = min(v[0] for _s, v in gp) >= 2.0
            e1 = math.log10(p1.costs["Gr_growth"]["memory_mb"] / done["Gr_growth"])
            e2 = math.log10(p2.costs["Gr_growth"]["memory_mb"] / done["Gr_growth"])
            acc.append({"dataset": ds, "sigma": sg, "clean": clean, "true": done["Gr_growth"],
                        "affine": p1.costs["Gr_growth"]["memory_mb"],
                        "new": p2.costs["Gr_growth"]["memory_mb"], "e_affine": e1, "e_new": e2,
                        "points": [(s, round(v[0], 2)) for s, v in gp]})
        recs2, _r, _f = rec.recommend(task, probe=p2)
        for r in recs2:
            if r.algorithm in done and r.prediction_source.startswith("probe") and r.memory_interval:
                lo, hi = r.memory_interval
                cov.append({"dataset": ds, "hit": lo <= done[r.algorithm] <= hi})
        if not done:
            continue
        best = min(done.values())
        bench = set(c.algorithm)
        reg = lambda a: done[a] / best if a in done else FAIL       # noqa: E731
        pick = lambda recs: next(r.algorithm for r in recs if r.algorithm in bench)  # noqa: E731
        a_pick = pick(rec.recommend(task)[0])
        c1 = pick(rec.recommend(task, probe=p1)[0])
        c2 = pick(recs2)
        rows.append({"dataset": ds, "sigma": sg, "mode": pr.mode, "best": min(done, key=done.get),
                     "best_mb": best, "A": reg(a_pick), "C1": reg(c1), "C2": reg(c2),
                     "A_pick": a_pick, "C1_pick": c1, "C2_pick": c2,
                     "failed": ",".join(sorted(bench - set(done)))})
    p, a, cv = pd.DataFrame(rows), pd.DataFrame(acc), pd.DataFrame(cov)
    p.to_csv(_ROOT / "results" / "fresh2_eval_rows.csv", index=False)
    a.to_csv(_ROOT / "results" / "fresh2_gr_accuracy.csv", index=False)
    g = PE.gmean
    L = ["Gr-growth on sampled instances (true MB | affine | new | log10 errors):"]
    for r in a.itertuples():
        L.append("  %-12s %-10.6g %s %8.1f | %8.1f | %8.1f | %+.3f %+.3f  %s"
                 % (r.dataset, r.sigma, "clean" if r.clean else "FLOOR", r.true, r.affine, r.new,
                    r.e_affine, r.e_new, r.points))
    q = a[a.clean]
    m1, m2 = q.e_affine.abs().median(), q.e_new.abs().median()
    L.append("G1 median |log10 error| (n=%d clean): affine %.3f, new %.3f -> %s"
             % (len(q), m1, m2, "PASS" if m2 < m1 else "FAIL"))
    L.append("   all sampled (n=%d): affine %.3f, new %.3f" % (len(a), a.e_affine.abs().median(),
                                                               a.e_new.abs().median()))
    for r in p.itertuples():
        L.append("  %-12s %-10.6g %-7s best %-20s %8.1f MB | A %-20s %5.2f | C1 %-20s %5.2f | C2 %-20s %5.2f | failed: %s"
                 % (r.dataset, r.sigma, r.mode, r.best, r.best_mb, r.A_pick, r.A, r.C1_pick, r.C1,
                    r.C2_pick, r.C2, r.failed or "-"))
    L.append("%d instances, %d datasets | A engine %.3fx  C1 affine %.3fx  C2 new %.3fx"
             % (len(p), p.dataset.nunique(), g(p.A), g(p.C1), g(p.C2)))
    L.append("G2 C2 <= C1: %.3f vs %.3f -> %s" % (g(p.C2), g(p.C1), "PASS" if g(p.C2) <= g(p.C1) else "FAIL"))
    pb, band = PE.boot(p, "C2", "A")
    L.append("G3 C2 < A: ratio %.3f [5-95%% %.3f..%.3f], P(better) %.3f -> %s"
             % (band[1], band[0], band[2], pb, "PASS" if pb >= 0.95 and g(p.C2) < g(p.A) else "FAIL"))
    L.append("   failed picks: A %d  C1 %d  C2 %d" % tuple((p[k] == FAIL).sum() for k in ("A", "C1", "C2")))
    L.append("G4 probe memory interval coverage %.3f (n=%d) -> %s"
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
