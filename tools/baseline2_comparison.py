"""Is the memory gain just from measuring? results/BASELINE2_PROTOCOL.md.

    python tools/baseline2_comparison.py [--af-wallclock 1800] [--af-seed 12345]

Writes results/baseline2_rows.csv and results/baseline2_output.txt.
"""
import argparse
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

import baseline_comparison as BC                           # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import selectors as S                     # noqa: E402
from recommender.perfmodel import load_runs, design_columns  # noqa: E402

NATIVE = ("Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth")
PCOLS = ["pm_%s" % a for a in NATIVE] + ["pf_%s" % a for a in NATIVE] + ["p_direct"]


def probe_features(pr):
    out = {}
    for a in NATIVE:
        c = (pr.costs or {}).get(a, {})
        if c.get("mode") in ("measured", "extrapolated") and c.get("memory_mb"):
            out["pm_" + a], out["pf_" + a] = math.log10(max(c["memory_mb"], 1e-3)), 0.0
        else:
            out["pm_" + a] = math.log10(max(c.get("memory_lb") or 1.0, 1.0))
            out["pf_" + a] = 1.0
    out["p_direct"] = 1.0 if pr.mode == "direct" else 0.0
    return out


def training_probes():
    import json
    from recommender import probe as P
    out = {}
    for line in open(BC.EX / "probes.jsonl"):
        r = json.loads(line)
        if r.get("set") != "training":
            continue
        pr = P.ProbeResult(n=r["n"], sigma=r["sigma"], mode=r["mode"], sizes=r["sizes"],
                           wall_s=r["wall_s"], costs=r["costs"], points={})
        out[(r["dataset"], round(float(r["sigma"]), 9))] = pr
    return out


def probe_argmin(pr, cand, sbs_order):
    vals = {a: c["memory_mb"] for a, c in (pr.costs or {}).items()
            if a in cand and c.get("mode") in ("measured", "extrapolated") and c.get("memory_mb")}
    if vals:
        return min(vals, key=vals.get)
    return next(a for a in sbs_order if a in cand)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--af-wallclock", type=int, default=1800)
    ap.add_argument("--af-seed", type=int, default=12345)
    args = ap.parse_args(argv)
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    cols = design_columns("static")
    rec = Recommender(runs=load_runs(str(BC.TRAIN)))
    db = CapabilityDB()
    probes = BC.load_probes()
    tprobes = training_probes()

    tr = BC.train_frame("memory", cols, BC.MINERS)
    keys = list(zip(tr.dataset, [round(float(p), 9) for p in tr.param_value]))
    tr = tr[[k in tprobes for k in keys]].copy()
    pf = pd.DataFrame([probe_features(tprobes[k]) for k in keys if k in tprobes], index=tr.index)
    tr = pd.concat([tr, pf], axis=1)
    print("training: %d rows, %d instances, %d datasets"
          % (len(tr), tr.groupby(["dataset", "param_value"]).ngroups, tr.dataset.nunique()),
          flush=True)
    sbs_order = S.SBSSelector().fit(tr, cols).order_
    xcols = cols + PCOLS
    sels = [S.PairwiseRankSelector(), S.RegressionSelector(), S.SunnySelector(k=16),
            S.ISACSelector()]
    if args.af_wallclock:
        sels.append(S.AutoFolioSelector(wallclock=args.af_wallclock, objective="memory",
                                        seed=args.af_seed))
    fitted = [s.fit(tr, xcols) for s in sels]
    for s in fitted:
        s.name = s.name + " +probe"
    print("fitted", [s.name for s in fitted], flush=True)

    plan = []
    for tset, path in BC.TESTS.items():
        t = BC.test_frame(path, cols)
        for (ds, sg), g in t.groupby(["dataset", "param_value"]):
            pr = probes.get((ds, round(float(sg), 9)))
            if pr is None:
                continue
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                              threshold=float(sg), objective="memory")
            el = {v.algorithm for v in db.filter(task)[0]}
            ok = PE.completed(g)
            done = {a: m for a, m in zip(g.algorithm[ok], g.peak_memory_mb[ok]) if a in el}
            cand = [a for a in sorted(set(g.algorithm)) if a in el]
            if len(cand) < 2 or not done:
                continue
            f = probe_features(pr)
            x = np.concatenate([g[cols].iloc[0].to_numpy(float), [f[c] for c in PCOLS]])
            plan.append((tset, ds, sg, task, pr, cand, done, x))
    for s in fitted:
        if hasattr(s, "prepare"):
            s.prepare([p[-1] for p in plan])
    rows = []
    for tset, ds, sg, task, pr, cand, done, x in plan:
        best = min(done.values())
        reg = lambda a: done[a] / best if a in done else BC.FAIL   # noqa: E731
        row = {"set": tset, "dataset": ds, "sigma": sg, "primary": tset in BC.PRIMARY,
               "probe wall s": pr.wall_s}
        a = next(r.algorithm for r in rec.recommend(task, probe=pr)[0] if r.algorithm in cand)
        row["recommender, probe"], row["pick recommender"] = reg(a), a
        a = probe_argmin(pr, cand, sbs_order)
        row["probe-argmin"], row["pick argmin"] = reg(a), a
        for s in fitted:
            row[s.name] = reg(s.select(x, cand))
        rows.append(row)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "baseline2_rows.csv", index=False)
    methods = ["recommender, probe", "probe-argmin"] + [s.name for s in fitted]
    rng = np.random.default_rng(0)
    L = []
    for label, q in (("PRIMARY fresh7+fresh8", d[d.primary]), ("all test sets", d)):
        L.append("== memory, %s: %d instances, %d datasets" % (label, len(q), q.dataset.nunique()))
        dss = q.dataset.unique()
        idx = {k: np.where(q.dataset.values == k)[0] for k in dss}
        boots = [np.concatenate([idx[k] for k in rng.choice(dss, len(dss))]) for _ in range(2000)]
        lg = {m: np.log(q[m].values) for m in methods}
        for m in methods:
            b = [np.exp(lg[m][ix].mean()) for ix in boots]
            L.append("   %-34s %.3fx [%.3f..%.3f] failed %d"
                     % (m, PE.gmean(q[m]), np.percentile(b, 5), np.percentile(b, 95),
                        int((q[m] >= BC.FAIL).sum())))
        for m in methods[1:]:
            diff = [lg["recommender, probe"][ix].mean() - lg[m][ix].mean() for ix in boots]
            L.append("   recommender vs %-30s ratio %.3f [%.3f..%.3f]  P(rec better) %.4f"
                     % (m, PE.gmean(q["recommender, probe"]) / PE.gmean(q[m]),
                        np.exp(np.percentile(diff, 5)), np.exp(np.percentile(diff, 95)),
                        float(np.mean(np.array(diff) < 0))))
        same = (q["pick recommender"] == q["pick argmin"]).mean()
        L.append("   recommender and probe-argmin pick the same implementation on %.1f%%" % (100 * same))
    out = "\n".join(L)
    (_ROOT / "results" / "baseline2_output.txt").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
