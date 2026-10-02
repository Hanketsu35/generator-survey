"""Group-level residual pool for the engine's memory/runtime intervals.

    python tools/interval_groups.py

Two kinds of group (= dataset), both out of sample for the prediction:
- the 17 training datasets, leave-one-dataset-out (results/interval_residuals.csv);
- the 24 datasets benchmarked after training (first confirmation, hard
  thresholds, fresh, fresh2, fresh3), predicted by the engine trained on
  results/training_runs.csv, which never saw them.

Output: results/interval_groups.csv (dataset, source, algorithm, sigma,
true/pred memory and runtime).
"""
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402

UNSEEN = ["real_extra3_summary.csv", "hard_summary.csv", "fresh_summary.csv",
          "fresh2_summary.csv", "fresh3_summary.csv"]
OUT = _ROOT / "results" / "interval_groups.csv"


def main():
    from recommender import metafeatures as mf
    from recommender.engine import Recommender
    lodo = pd.read_csv(_ROOT / "results" / "interval_residuals.csv")
    rows = [{"dataset": r.dataset, "source": "training LODO", "algorithm": r.algorithm,
             "sigma": r.sigma, "true_mem": r.true_mem, "pred_mem": r.pred_mem,
             "true_rt": r.true_rt, "pred_rt": r.pred_rt} for r in lodo.itertuples()]
    rec = Recommender()
    for f in UNSEEN:
        t = pd.read_csv(_ROOT / "results" / f)
        t = t[PE.completed(t)]
        for ds, g in t.groupby("dataset"):
            feats = mf.extract(PE.dataset_path(ds), "transactional")
            for r in g.itertuples():
                p = rec.model.predict(r.algorithm, feats, float(r.param_value))
                if p is None:
                    continue
                rows.append({"dataset": ds, "source": f.replace("_summary.csv", ""),
                             "algorithm": r.algorithm, "sigma": r.param_value,
                             "true_mem": r.peak_memory_mb, "pred_mem": p["memory_mb"],
                             "true_rt": r.runtime_s, "pred_rt": p["runtime_s"]})
            print("%-16s %-12s %4d rows" % (ds, f.replace("_summary.csv", ""), len(g)), flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False)
    print("%d rows, %d groups" % (len(d), d.dataset.nunique()))


if __name__ == "__main__":
    main()
