"""The progress rule where it acted after it was frozen: results/LAG2_PROTOCOL.md.

    python tools/lag2_eval.py

Writes results/lag2_rows.csv and results/lag2_output.txt.
"""
import json
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
from recommender import engine as E                        # noqa: E402
from recommender import probe as P                         # noqa: E402

A = {"fresh%d" % i: _ROOT / ("results/probe_fresh%d.jsonl" % i) for i in (5, 6, 7, 8)}
B_PROBES = BC.EX / "probes.jsonl"
RULE_SOURCES = {"census_kdd", "diabetes130"}


def _pr(r):
    return P.ProbeResult(n=r["n"], sigma=r["sigma"], mode=r["mode"], sizes=r["sizes"],
                         wall_s=r["wall_s"], costs=r["costs"],
                         points={a: [(z, tuple(v)) for z, v in p] for a, p in r["points"].items()})


def lagging(path):
    out = []
    for line in open(path):
        r = json.loads(line)
        pr = _pr(r)
        prog = E.Recommender._probe_progress(pr)
        if len(set(prog.values())) > 1:
            out.append((r["dataset"], float(r["sigma"]), pr))
    return out


def main():
    from recommender.capabilities import CapabilityDB
    from recommender.perfmodel import load_runs
    from recommender.spec import MiningTask
    inst = []
    for tset, f in A.items():
        inst += [("A", tset, ds, sg, pr) for ds, sg, pr in lagging(f)]
    inst += [("B", None, ds, sg, pr) for ds, sg, pr in lagging(B_PROBES)
             if ds not in RULE_SOURCES]
    truths = {k: pd.read_csv(v) for k, v in BC.TESTS.items()}
    engines = {"comparison": E.Recommender(runs=load_runs(str(BC.TRAIN))),
               "deployed": E.Recommender()}
    db = CapabilityDB()
    rows = []
    for grp, tset, ds, sg, pr in inst:
        g = None
        for k, t in truths.items():
            if tset is not None and k != tset:
                continue
            h = t[(t.dataset == ds) & (np.isclose(t.param_value, sg, rtol=1e-6))
                  & t.algorithm.isin(BC.MINERS)]
            if len(h):
                g, tset = h.copy(), k
                break
        if g is None:
            print("no truth", grp, ds, sg)
            continue
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        ok = PE.completed(g)
        done = {a: m for a, m in zip(g.algorithm[ok], g.peak_memory_mb[ok]) if a in el}
        cand = [a for a in sorted(set(g.algorithm)) if a in el]
        if len(cand) < 2 or not done:
            print("skipped", grp, ds, sg)
            continue
        best = min(done.values())
        prog = E.Recommender._probe_progress(pr)
        for ename, eng in engines.items():
            row = {"group": grp, "set": tset, "dataset": ds, "sigma": sg, "engine": ename,
                   "mode": pr.mode, "progress": json.dumps({a[:6]: round(v, 2) for a, v in prog.items()})}
            for tag, flag in (("D", True), ("S", False)):
                E.PROGRESS_DEMOTE = flag
                recs = eng.recommend(task, probe=pr)[0]
                a = next(r.algorithm for r in recs if r.algorithm in cand)
                row[tag] = a
                row["reg_" + tag] = done[a] / best if a in done else BC.FAIL
            E.PROGRESS_DEMOTE = True
            rows.append(row)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "lag2_rows.csv", index=False)
    L = []
    for (grp, ename), q in d.groupby(["group", "engine"]):
        ch = q[q.D != q.S]
        L.append("%s %-10s n=%2d ds=%2d | D %.3fx fail %d | S %.3fx fail %d | changed %d:"
                 " D better %d, worse %d"
                 % (grp, ename, len(q), q.dataset.nunique(), PE.gmean(q.reg_D),
                    (q.reg_D >= BC.FAIL).sum(), PE.gmean(q.reg_S), (q.reg_S >= BC.FAIL).sum(),
                    len(ch), (ch.reg_D < ch.reg_S).sum(), (ch.reg_D > ch.reg_S).sum()))
    for r in d.itertuples():
        L.append("  %s %-10s %-7s %-34s %-10.6g %-7s %s  D %s %.3f | S %s %.3f%s"
                 % (r.group, r.engine, r.set, r.dataset, r.sigma, r.mode, r.progress,
                    r.D, r.reg_D, r.S, r.reg_S, "" if r.D == r.S else "  CHANGED"))
    out = "\n".join(L)
    (_ROOT / "results" / "lag2_output.txt").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
