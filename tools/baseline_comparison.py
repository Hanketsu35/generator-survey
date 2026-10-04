"""Baseline comparison: results/BASELINE_PROTOCOL.md.

    python tools/baseline_comparison.py [--af-wallclock 1800]

Writes results/baseline_rows.csv and results/baseline_output.txt.
"""
import argparse
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

import fresh_eval as FE                                    # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import selectors as S                     # noqa: E402
from recommender.perfmodel import load_runs, design_columns, rows_with_features  # noqa: E402

EX = _ROOT / "results" / "exact"
TRAIN = EX / "training_runs.csv"
TESTS = {"confirm": EX / "real_extra3_summary.csv", "hard": EX / "hard_summary.csv",
         "fresh": EX / "fresh_summary.csv", "fresh2": EX / "fresh2_summary.csv",
         "fresh3": EX / "fresh3_summary.csv", "fresh4": EX / "fresh4_summary.csv",
         "fresh5": _ROOT / "results/fresh5_summary.csv", "fresh6": _ROOT / "results/fresh6_summary.csv",
         "fresh7": _ROOT / "results/fresh7_summary.csv", "fresh8": _ROOT / "results/fresh8_summary.csv"}
PROBES = [EX / "probes.jsonl"] + [_ROOT / ("results/probe_fresh%d.jsonl" % i) for i in (5, 6, 7, 8)]
PRIMARY = {"fresh7", "fresh8"}
FAIL = 10.0
MINERS = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth",
          "DefMe", "Pascal", "Zart", "Talky_G", "TalkyG_Diffset"]


def load_probes():
    from recommender import probe as P
    out = {}
    for f in PROBES:
        for line in open(f):
            r = json.loads(line)
            pr = P.ProbeResult(n=r["n"], sigma=r["sigma"], mode=r["mode"], sizes=r["sizes"],
                               wall_s=r["wall_s"], costs=r["costs"],
                               points={a: [(z, tuple(v)) for z, v in p] for a, p in r["points"].items()})
            out.setdefault((r["dataset"], round(r["sigma"], 9)), pr)
    return out


def selectors(objective, wall):
    out = [S.SBSSelector(), S.RandomSelector(), S.RegressionSelector(), S.PairwiseRankSelector(),
           S.SunnySelector(k=16), S.ISACSelector(), S.SurvivalSelector(rule="expected_par10")]
    if wall:
        out.append(S.AutoFolioSelector(wallclock=wall, objective=objective))
    return out


def train_frame(objective, cols, allowed):
    df = rows_with_features(load_runs(str(TRAIN)), "static")
    df = df[(df.category == 1) & df.algorithm.isin(allowed)].copy()
    if objective == "memory":
        ok = df[df.completed]
        wide = ok.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                              values="peak_memory_mb", aggfunc="min")
        full = set(wide.dropna(how="any").index)
        df = df[[(d, p) in full for d, p in zip(df.dataset, df.param_value)] & df.completed]
        df = df.assign(runtime_s=df.peak_memory_mb)
        df["par10"] = df.peak_memory_mb.astype(float)
    else:
        df["par10"] = [S.par10(r, c) for r, c in zip(df.runtime_s, df.completed)]
    return df


_FEATS = {}


def test_frame(path, cols):
    """Test runs with the same features the selectors were trained on,
    computed from each dataset's file (the meta-feature cache covers only the
    configured datasets)."""
    from recommender import metafeatures as mf
    t = pd.read_csv(path)
    t = t[t.algorithm.isin(MINERS)].copy()
    t["completed"] = PE.completed(t)
    for ds in t.dataset.unique():
        if ds not in _FEATS:
            _FEATS[ds] = mf.extract(PE.dataset_path(ds), "transactional")
    for c in mf.FEATURE_NAMES:
        t[c] = [_FEATS[ds][c] for ds in t.dataset]
    t["log_thr"] = np.log10(t.param_value.clip(lower=1e-9))
    return t.dropna(subset=cols)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--af-wallclock", type=int, default=1800)
    args = ap.parse_args(argv)
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    cols = design_columns("static")
    runs = load_runs(str(TRAIN))
    rec = Recommender(runs=runs)
    db = CapabilityDB()
    probes = load_probes()
    rows = []
    for objective in ("memory", "runtime"):
        fitted = {}
        for mode, allowed in (("eligible", None), ("unrestricted", MINERS)):
            pool = MINERS if allowed is None else allowed
            tr = train_frame(objective, cols, pool)
            fitted[mode] = [s.fit(tr, cols) for s in selectors(objective,
                            args.af_wallclock if mode == "eligible" else 0)]
            print("fitted %s/%s on %d rows" % (objective, mode, len(tr)), flush=True)
        for tset, path in TESTS.items():
            t = test_frame(path, cols)
            for (ds, sg), g in t.groupby(["dataset", "param_value"]):
                task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                                  threshold=float(sg), objective=objective)
                el = {v.algorithm for v in db.filter(task)[0]}
                ok = PE.completed(g)
                val = g.peak_memory_mb if objective == "memory" else np.maximum(g.runtime_s, 0.01)
                done = dict(zip(g.algorithm[ok], val[ok]))
                ran = sorted(set(g.algorithm))
                cand = [a for a in ran if a in el]
                done_el = {a: v for a, v in done.items() if a in el}
                if len(cand) < 2 or not done_el:
                    continue
                best = min(done_el.values())
                reg = lambda a: done_el[a] / best if a in done_el else FAIL   # noqa: E731
                x = g[cols].iloc[0].to_numpy(float)
                row = {"set": tset, "objective": objective, "dataset": ds, "sigma": sg,
                       "primary": tset in PRIMARY}
                for s in fitted["eligible"]:
                    if hasattr(s, "prepare"):
                        s.prepare([x])
                    row[s.name] = reg(s.select(x, cand))
                for s in fitted["unrestricted"]:
                    pick = s.select(x, ran)
                    row[s.name + " |unsound"] = pick not in el
                recs = rec.recommend(task)[0]
                row["recommender, no probe"] = reg(next(r.algorithm for r in recs if r.algorithm in cand))
                pr = probes.get((ds, round(float(sg), 9)))
                if objective == "memory" and pr is not None:
                    recs = rec.recommend(task, probe=pr)[0]
                    row["recommender, probe"] = reg(next(r.algorithm for r in recs if r.algorithm in cand))
                rows.append(row)
            print("scored %s/%s" % (objective, tset), flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "baseline_rows.csv", index=False)
    methods = [c for c in d.columns if c not in ("set", "objective", "dataset", "sigma", "primary")
               and "|" not in c]
    L = []
    rng = np.random.default_rng(0)
    for objective in ("memory", "runtime"):
        for label, q in (("PRIMARY fresh7+fresh8", d[(d.objective == objective) & d.primary]),
                         ("all test sets", d[d.objective == objective])):
            L.append("== %s, %s: %d instances, %d datasets" % (objective, label, len(q), q.dataset.nunique()))
            dss = q.dataset.unique()
            res = []
            for m in methods:
                if q[m].isna().all():
                    continue
                v = q[m].dropna()
                g = PE.gmean(v)
                boots = []
                for _ in range(1000):
                    pick = rng.choice(dss, len(dss))
                    boots.append(PE.gmean(pd.concat([q[q.dataset == x][m] for x in pick]).dropna()))
                res.append((g, m, np.percentile(boots, 5), np.percentile(boots, 95), (v == FAIL).sum(), len(v)))
            for g, m, lo, hi, nf, n in sorted(res):
                L.append("   %-34s regret %.3fx  [%.3f..%.3f]  failed picks %d/%d" % (m, g, lo, hi, nf, n))
            uns = [c for c in q.columns if c.endswith("|unsound")]
            if uns:
                L.append("   unrestricted selectors picking an implementation Layer 2 rejects:")
                for c in uns:
                    L.append("      %-31s %.1f%%" % (c.replace(" |unsound", ""), 100 * q[c].mean()))
    (_ROOT / "results" / "baseline_output.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
