"""Leave-one-dataset-out residual pool for the model trained on every
benchmarked dataset (results/exact/training_all.csv).

    python tools/interval_pool_all.py

For each of the datasets with transactional runs, the engine is refitted
without it and asked for every completed run on it. The pool is
results/exact/interval_groups_all.csv; each residual comes from a model that
never saw its dataset, the situation of a user's new file.
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

TABLE = _ROOT / "results" / "exact" / "training_all.csv"
OUT = _ROOT / "results" / "exact" / "interval_groups_all.csv"
TRANS_ALGOS = {"Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth",
               "FGC_Stream", "DefMe", "Pascal", "Zart", "Talky_G", "TalkyG_Diffset"}


def main():
    from recommender import metafeatures as mf
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    runs = load_runs(str(TABLE))
    t = pd.read_csv(TABLE)
    t = t[t.algorithm.isin(TRANS_ALGOS) & PE.completed(t)]
    trans = sorted(t[t.category == 1].dataset.unique())
    rows = []
    for i, ds in enumerate(trans, 1):
        rec = Recommender(runs=runs, exclude_dataset=ds)
        feats = mf.extract(PE.dataset_path(ds), "transactional")
        for r in t[t.dataset == ds].itertuples():
            p = rec.model.predict(r.algorithm, feats, float(r.param_value))
            if p is None:
                continue
            rows.append({"dataset": ds, "source": r.source_table, "algorithm": r.algorithm,
                         "sigma": r.param_value, "true_mem": r.peak_memory_mb,
                         "pred_mem": p["memory_mb"], "true_rt": r.runtime_s,
                         "pred_rt": p["runtime_s"],
                         "pred_rt_median": p.get("runtime_median_s", p["runtime_s"])})
        print("[%2d/%2d] %s" % (i, len(trans), ds), flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False)
    print("%d rows, %d datasets" % (len(d), d.dataset.nunique()))


if __name__ == "__main__":
    main()
