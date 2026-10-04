"""Run AutoFolio (Lindauer et al., JAIR 2015) for recommender.selectors.AutoFolioSelector.

Runs inside tools/autofolio/.venv (Python 3.10, SMAC 1.4), because AutoFolio
needs an older scientific stack than the project's.

    af_run.py fit PERF.csv FEATS.csv CV.csv OBJECTIVE CUTOFF WALLCLOCK SEED MODEL.pkl
    af_run.py predict MODEL.pkl FEATS.csv OUT.json

predict writes {instance: algorithm}, taking the LAST entry of the predicted
schedule (the selected algorithm; a pre-solver, if AutoFolio chose one, comes
first and is not counted, because the benchmark scores one run per instance).
"""
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
logging.disable(logging.INFO)

from aslib_scenario.aslib_scenario import ASlibScenario   # noqa: E402
from autofolio.autofolio import AutoFolio                  # noqa: E402


def fit(perf, feats, cv, objective, cutoff, wallclock, seed, model):
    af = AutoFolio(random_seed=int(seed))
    sc = ASlibScenario()
    sc.read_from_csv(perf_fn=perf, feat_fn=feats, objective=objective,
                     runtime_cutoff=float(cutoff), maximize=False, cv_fn=cv)
    af.cs = af.get_cs(sc, {})
    cfg = af.get_tuned_config(sc, wallclock_limit=int(wallclock), runcount_limit=10 ** 9,
                              autofolio_config={"output-dir": os.path.dirname(model)},
                              seed=int(seed))
    pre, presolver, selector = af.fit(scenario=sc, config=cfg)
    af._save_model(model, sc, pre, presolver, selector, cfg)
    print(cfg)


def predict(model, feats, out):
    import pandas as pd
    af = AutoFolio()
    f = pd.read_csv(feats, index_col=0)
    res = {}
    for inst, row in f.iterrows():
        sched = af.read_model_and_predict(model, [float(v) for v in row.values])
        res[str(inst)] = sched[-1][0] if sched else None
    with open(out, "w") as fh:
        json.dump(res, fh)


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        fit(*sys.argv[2:10])
    else:
        predict(*sys.argv[2:5])
