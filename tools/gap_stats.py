"""Additional reporting on the baseline comparison (gaps G2-G4, kbs/GAPS.md).

    python tools/gap_stats.py

Not new tests: further views of results/baseline_rows.csv and the stored
probes, computed after BASELINE_RESULTS.md.
  G2  the probe's wall time against the runtime of the implementation it
      leads to, per memory instance with a probe;
  G3  regret in megabytes: the pick's peak minus the best eligible peak;
  G4  Wilcoxon signed-rank tests (per-dataset mean log regret, recommender
      with probe against each method, Holm-corrected) and a Friedman test
      with average ranks over datasets.
Writes results/gap_stats_output.txt.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import baseline_comparison as BC                           # noqa: E402
import probe_eval as PE                                    # noqa: E402

REC = "recommender, probe"


def truth():
    """{(set, dataset, sigma): (eligible completed {algo: (mem, rt)})}."""
    from recommender.capabilities import CapabilityDB
    from recommender.spec import MiningTask
    db = CapabilityDB()
    out = {}
    for tset, path in BC.TESTS.items():
        t = pd.read_csv(path)
        t = t[t.algorithm.isin(BC.MINERS)]
        for (ds, sg), g in t.groupby(["dataset", "param_value"]):
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                              threshold=float(sg), objective="memory")
            el = {v.algorithm for v in db.filter(task)[0]}
            ok = PE.completed(g)
            out[(tset, ds, round(float(sg), 9))] = {
                a: (m, r) for a, m, r in zip(g.algorithm[ok], g.peak_memory_mb[ok], g.runtime_s[ok])
                if a in el}
    return out


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for i, k in enumerate(o):
        run = max(run, (len(p) - i) * p[k])
        adj[k] = min(run, 1.0)
    return adj


def main():
    d = pd.read_csv(_ROOT / "results" / "baseline_rows.csv")
    m = d[(d.objective == "memory") & d[REC].notna()].copy()
    methods = [c for c in m.columns if c not in ("set", "objective", "dataset", "sigma", "primary")
               and "|" not in c and m[c].notna().all()]
    T = truth()
    probes = BC.load_probes()
    L = []

    # ---- G3: megabytes -----------------------------------------------------
    for label, q in (("PRIMARY", m[m.primary]), ("all", m)):
        L.append("== G3 excess peak memory over the best eligible miner, %s (%d instances)"
                 % (label, len(q)))
        best = np.array([min(v[0] for v in T[(s, ds, round(float(sg), 9))].values())
                         for s, ds, sg in zip(q.set, q.dataset, q.sigma)])
        for meth in methods:
            r = q[meth].values
            okk = r < BC.FAIL
            mb = (r[okk] - 1.0) * best[okk]
            L.append("   %-34s median %6.1f MB  mean %7.1f MB  >10 MB %5.1f%%  >100 MB %5.1f%%  failed %d"
                     % (meth, np.median(mb), mb.mean(), 100 * np.mean(mb > 10),
                        100 * np.mean(mb > 100), int((~okk).sum())))

    # ---- G2: probe time --------------------------------------------------
    L.append("== G2 probe wall time against the runtime of the recommended run")
    for label, q in (("PRIMARY", m[m.primary]), ("all", m)):
        rows = []
        for s, ds, sg in zip(q.set, q.dataset, q.sigma):
            pr = probes.get((ds, round(float(sg), 9)))
            tv = T[(s, ds, round(float(sg), 9))]
            # the recommender's memory pick is the lowest-memory eligible miner
            # on 99% of these instances; use the truth's best as its run
            a = min(tv, key=lambda k: tv[k][0])
            rt = tv[a][1]
            already = pr.mode == "direct" and pr.costs.get(a, {}).get("mode") == "measured"
            rows.append((pr.wall_s, rt, already))
        w = np.array([r[0] for r in rows])
        rt = np.array([r[1] for r in rows])
        al = np.array([r[2] for r in rows])
        extra = np.where(al, np.maximum(w - rt, 0.0), w)
        L.append("   %-8s n=%d  probe wall: median %.2f s, 90%% %.1f s, max %.1f s | run: median %.2f s"
                 % (label, len(w), np.median(w), np.percentile(w, 90), w.max(), np.median(rt)))
        L.append("            output already produced by the probe (direct, measured): %.1f%%"
                 % (100 * al.mean()))
        L.append("            extra time beyond the run: median %.2f s, 90%% %.1f s; extra > run on %.1f%%"
                 % (np.median(extra), np.percentile(extra, 90), 100 * np.mean(extra > rt)))
        big = rt >= 10
        if big.any():
            L.append("            on runs of 10 s or more (%d): extra / run median %.3f"
                     % (big.sum(), np.median(extra[big] / rt[big])))

    # ---- G4: tests -------------------------------------------------------
    for label, q in (("PRIMARY", m[m.primary]), ("all", m)):
        per = q.groupby("dataset")[methods].apply(lambda g: np.log(g).mean())
        L.append("== G4 %s: %d datasets; Wilcoxon signed-rank on per-dataset mean log regret, "
                 "recommender with probe vs each, Holm-corrected" % (label, len(per)))
        others = [x for x in methods if x != REC]
        ps, lines = [], []
        for meth in others:
            diff = per[REC] - per[meth]
            if np.allclose(diff, 0):
                ps.append(1.0)
                lines.append((meth, 0, 0, 0))
                continue
            res = stats.wilcoxon(per[REC], per[meth], zero_method="wilcox", alternative="two-sided")
            ps.append(res.pvalue)
            lines.append((meth, int((diff < 0).sum()), int((diff > 0).sum()), int((diff == 0).sum())))
        for (meth, b, w_, t), p, pa in zip(lines, ps, holm(ps)):
            L.append("   vs %-32s better/worse/tied datasets %2d/%2d/%2d  p %.2e  Holm %.2e"
                     % (meth, b, w_, t, p, pa))
        fr = stats.friedmanchisquare(*[per[x] for x in methods])
        ranks = per[methods].rank(axis=1).mean().sort_values()
        L.append("   Friedman chi2 %.1f, p %.2e; average rank (1 = best):" % (fr.statistic, fr.pvalue))
        k, n = len(methods), len(per)
        cd = 3.164 * np.sqrt(k * (k + 1) / (6.0 * n))   # Nemenyi, q_0.05 for k = 10
        for meth, r in ranks.items():
            L.append("      %-34s %.2f" % (meth, r))
        L.append("   Nemenyi critical difference (alpha 0.05, k=%d): %.2f" % (k, cd))
    out = "\n".join(L)
    (_ROOT / "results" / "gap_stats_output.txt").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
