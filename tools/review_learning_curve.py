"""Post hoc: do the learned selectors improve with more training data?

    python tools/review_learning_curve.py

The baseline comparison (results/BASELINE_RESULTS.md) trained every method
on the 22 datasets of results/exact/training_runs.csv. Here the same
selectors (all but AutoFolio, whose 1,800 s per fold does not fit this
check) and the recommender's cost model are refitted on the 81 datasets of
results/exact/training_all.csv, which contain none of the PRIMARY datasets,
and scored on PRIMARY (FRESH7, FRESH8) exactly as before. Not a test.
Output: results/review_learning_curve_output.txt.
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
from recommender.perfmodel import design_columns, load_runs   # noqa: E402

OUT = _ROOT / "results" / "review_learning_curve_output.txt"


def _with_features(path):
    """Every run of the table with the static meta-features of its dataset.
    load_runs() keeps only the datasets in the meta-feature cache (22 of the
    81 in training_all.csv), so the features are computed from the files."""
    from recommender import metafeatures as mf
    from recommender.perfmodel import attach_landmarks
    df = pd.read_csv(path)
    df["completed"] = (df.timed_out.astype(str).str.lower() != "true") & df.error.isna()
    cache = mf.load_cache()
    feats = {}
    for ds in sorted(df.dataset.unique()):
        feats[ds] = cache[ds] if ds in cache else mf.extract(PE.dataset_path(ds), "transactional")
    for c in mf.FEATURE_NAMES:
        df[c] = [feats[ds][c] for ds in df.dataset]
    df["log_thr"] = np.log10(df.param_value.clip(lower=1e-9))
    print("features for %d datasets (%d computed from files)"
          % (len(feats), sum(ds not in cache for ds in feats)), flush=True)
    return attach_landmarks(df)


def run(train_path):
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    BC.TRAIN = Path(train_path)
    cols = design_columns("static")
    runs = _with_features(BC.TRAIN)
    BC.load_runs = lambda _p, _r=runs: _r.copy()
    rec = Recommender(runs=runs)
    db = CapabilityDB()
    probes = BC.load_probes()
    res = {}
    for objective in ("memory", "runtime"):
        tr = BC.train_frame(objective, cols, BC.MINERS)
        fitted = [s.fit(tr, cols) for s in BC.selectors(objective, 0)]
        rows = []
        for tset in sorted(BC.PRIMARY):
            t = BC.test_frame(BC.TESTS[tset], cols)
            for (ds, sg), g in t.groupby(["dataset", "param_value"]):
                task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                                  threshold=float(sg), objective=objective)
                el = {v.algorithm for v in db.filter(task)[0]}
                ok = PE.completed(g)
                val = g.peak_memory_mb if objective == "memory" else np.maximum(g.runtime_s, 0.01)
                done = {a: v for a, v in zip(g.algorithm[ok], val[ok]) if a in el}
                cand = [a for a in sorted(set(g.algorithm)) if a in el]
                if len(cand) < 2 or not done:
                    continue
                best = min(done.values())
                reg = lambda a: done[a] / best if a in done else BC.FAIL   # noqa: E731
                x = g[cols].iloc[0].to_numpy(float)
                row = {}
                for s in fitted:
                    if hasattr(s, "prepare"):
                        s.prepare([x])
                    row[s.name] = reg(s.select(x, cand))
                row["recommender, no probe"] = reg(next(r.algorithm for r in rec.recommend(task)[0]
                                                        if r.algorithm in cand))
                pr = probes.get((ds, round(float(sg), 9)))
                if objective == "memory" and pr is not None:
                    row["recommender, probe"] = reg(next(r.algorithm for r in rec.recommend(task, probe=pr)[0]
                                                         if r.algorithm in cand))
                rows.append(row)
        d = pd.DataFrame(rows)
        res[objective] = {c: (PE.gmean(d[c].dropna()), int((d[c] == BC.FAIL).sum()), int(d[c].notna().sum()))
                          for c in d.columns}
        print("done", train_path, objective, len(tr), "training rows,", tr.dataset.nunique(), "datasets", flush=True)
    return res


def main():
    a = run(BC.EX / "training_runs.csv")
    b = run(BC.EX / "training_all.csv")
    L = ["Learned selectors and the recommender trained on 22 vs 81 datasets, scored on PRIMARY",
         "(geometric-mean regret; failed pick = 10; post hoc)"]
    for obj in ("memory", "runtime"):
        L.append("objective %s" % obj)
        for m in a[obj]:
            ga, fa, na = a[obj][m]
            gb, fb, nb = b[obj].get(m, (float("nan"), 0, 0))
            L.append("   %-34s 22 datasets %.3fx (failed %d/%d) | 81 datasets %.3fx (failed %d/%d)"
                     % (m, ga, fa, na, gb, fb, nb))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
