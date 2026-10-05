"""Old vs exact ranking quantiles: results/RANKQ_PROTOCOL.md (post hoc).

    python tools/rankq_eval.py

The baseline comparison's instances and probes; the recommender ranked once
with the quantiles in intervals.json as committed and once with
intervals.ranking_exact(), everything else fixed. Balanced regret is on the
engine's own balanced cost, sqrt(runtime * memory), over the completed
eligible miners. Writes results/rankq_rows.csv and results/rankq_output.txt.
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

import baseline_comparison as BC                           # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import intervals as I                     # noqa: E402


def main():
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    from recommender.spec import MiningTask
    old = I._load()
    new = I.ranking_exact(old)
    engines = {"comparison": Recommender(runs=load_runs(str(BC.TRAIN))),
               "deployed": Recommender()}
    db = CapabilityDB()
    probes = BC.load_probes()
    rows = []
    for tset, path in BC.TESTS.items():
        t = pd.read_csv(path)
        t = t[t.algorithm.isin(BC.MINERS)].copy()
        t["completed"] = PE.completed(t)
        for (ds, sg), g in t.groupby(["dataset", "param_value"]):
            pr = probes.get((ds, round(float(sg), 9)))
            ok = g.completed.values
            mem = dict(zip(g.algorithm[ok], g.peak_memory_mb[ok]))
            rtm = dict(zip(g.algorithm[ok], np.maximum(g.runtime_s[ok], 0.01)))
            for objective in ("memory", "balanced", "runtime"):
                task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                                  threshold=float(sg), objective=objective)
                el = {v.algorithm for v in db.filter(task)[0]}
                cand = [a for a in sorted(set(g.algorithm)) if a in el]
                if objective == "memory":
                    truth = {a: mem[a] for a in cand if a in mem}
                elif objective == "runtime":
                    truth = {a: rtm[a] for a in cand if a in rtm}
                else:
                    truth = {a: (mem[a] * rtm[a]) ** 0.5 for a in cand if a in mem}
                if len(cand) < 2 or not truth:
                    continue
                best = min(truth.values())
                for ename, eng in engines.items():
                    if ename == "deployed" and tset not in BC.PRIMARY:
                        continue
                    for with_probe in ((True, False) if pr is not None else (False,)):
                        row = {"set": tset, "dataset": ds, "sigma": sg, "objective": objective,
                               "engine": ename, "probe": with_probe,
                               "primary": tset in BC.PRIMARY}
                        for tag, q in (("old", old), ("new", new)):
                            I._q = q
                            recs = eng.recommend(task, probe=pr if with_probe else None)[0]
                            a = next(r.algorithm for r in recs if r.algorithm in cand)
                            row[tag] = a
                            row["reg_" + tag] = truth[a] / best if a in truth else BC.FAIL
                        rows.append(row)
        print("scored", tset, flush=True)
    I._q = None
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "rankq_rows.csv", index=False)
    L = []
    for (ename, objective, probe), q0 in d.groupby(["engine", "objective", "probe"]):
        for label, q in (("PRIMARY", q0[q0.primary]), ("all", q0)):
            if q.empty:
                continue
            ch = (q.old != q.new).sum()
            L.append("%-10s %-8s probe=%-5s %-7s n=%3d ds=%2d | old %.3fx fail %d | new %.3fx fail %d"
                     " | changed %d (%.1f%%) | rel %+.2f%%"
                     % (ename, objective, probe, label, len(q), q.dataset.nunique(),
                        PE.gmean(q.reg_old), (q.reg_old >= BC.FAIL).sum(),
                        PE.gmean(q.reg_new), (q.reg_new >= BC.FAIL).sum(), ch, 100 * ch / len(q),
                        100 * (PE.gmean(q.reg_new) / PE.gmean(q.reg_old) - 1)))
    for r in d[d.old != d.new].itertuples():
        L.append("  changed %-8s %-10s %-7s %-22s %-8s probe=%-5s %s %.3f -> %s %.3f"
                 % (r.set, r.engine, r.objective, r.dataset, r.sigma, r.probe,
                    r.old, r.reg_old, r.new, r.reg_new))
    out = "\n".join(L)
    (_ROOT / "results" / "rankq_output.txt").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
