"""Leave-one-dataset-out residuals of the engine's cost predictions.

    python tools/interval_residuals.py

For each transactional training dataset d, the engine is refitted without d
and asked for every completed (algorithm, threshold) run on d. Each row
records the prediction, the truth, and whether the band the engine currently
shows (memory: 5-95% bootstrap of the forest mean) contains the truth. These
residuals are the calibration set for the prediction intervals
(results/INTERVAL_PROTOCOL.md): a residual on d comes from a model that never
saw d, which is the situation of a user's new file.

Also records the probe's residuals on the same instances (from
results/probe_points.csv; the probe learns nothing, so no refit is needed).

Output: results/interval_residuals.csv
"""
import math
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402

OUT = _ROOT / "results" / "interval_residuals.csv"


def main():
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    from recommender import metafeatures as mf
    runs = load_runs(str(PE.TABLE))
    t = pd.read_csv(PE.TABLE)
    t = t[(t.category == 1) & PE.completed(t)]
    pcs = {v: PE.probe_costs(v) for v in ("affine", "loglog")}
    rows = []
    for ds in sorted(t.dataset.unique()):
        rec = Recommender(runs=runs, exclude_dataset=ds)
        feats = mf.extract(PE.dataset_path(ds), "transactional")
        for r in t[t.dataset == ds].itertuples():
            pred = rec.model.predict(r.algorithm, feats, float(r.param_value))
            if pred is None:
                continue
            mb = pred.get("memory_band")
            row = {"dataset": ds, "sigma": r.param_value, "algorithm": r.algorithm,
                   "true_mem": r.peak_memory_mb, "true_rt": r.runtime_s,
                   "pred_mem": pred["memory_mb"], "pred_rt": pred["runtime_s"],
                   "source": pred["source"],
                   "band_lo": mb[1] if mb else None, "band_hi": mb[2] if mb else None}
            for v, pc in pcs.items():
                c = pc.get((ds, round(float(r.param_value), 9)), {}).get("costs", {})
                if r.algorithm in c:
                    row["probe_%s_mem" % v] = c[r.algorithm][0]
                    row["probe_%s_rt" % v] = c[r.algorithm][1]
                    row["probe_measured"] = c[r.algorithm][2]
            rows.append(row)
        print("%-14s %4d rows" % (ds, sum(x["dataset"] == ds for x in rows)), flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False)
    ok = d.band_lo.notna()
    cov = ((d.true_mem >= d.band_lo) & (d.true_mem <= d.band_hi))[ok].mean()
    err = (d.pred_mem / d.true_mem).map(lambda x: abs(math.log10(x)))
    print("%d rows | current memory band covers the truth in %.1f%% (nominal 90%%) | "
          "median |log10 error| %.3f" % (len(d), 100 * cov, err.median()))


if __name__ == "__main__":
    main()
