"""Residual pools for the intervals, rebuilt on exact peak memory.

    python tools/interval_pool_exact.py [--model] [--probe]

--model  results/exact/interval_residuals.csv: leave-one-dataset-out over the
         training datasets of results/exact/training_runs.csv; and
         results/exact/interval_groups.csv: those plus every dataset
         benchmarked after training (results/exact/<table>), predicted by the
         engine trained on the exact training table.
--probe  results/exact/interval_groups_probe.csv: log10(true / probe estimate)
         from the exact re-probes (results/exact/probes.jsonl) against the
         exact truth, every completed native run.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402

EX = _ROOT / "results" / "exact"
UNSEEN = {"confirm": "real_extra3_summary.csv", "hard": "hard_summary.csv",
          "fresh": "fresh_summary.csv", "fresh2": "fresh2_summary.csv",
          "fresh3": "fresh3_summary.csv", "fresh4": "fresh4_summary.csv"}
TRUTH = dict(UNSEEN, training="training_runs.csv", lag=None)


def model_pool():
    from recommender import metafeatures as mf
    from recommender.engine import Recommender
    from recommender.perfmodel import load_runs
    tab = EX / "training_runs.csv"
    runs = load_runs(str(tab))
    t = pd.read_csv(tab)
    t = t[(t.category == 1) & PE.completed(t)]
    rows = []
    for ds in sorted(t.dataset.unique()):
        rec = Recommender(runs=runs, exclude_dataset=ds)
        feats = mf.extract(PE.dataset_path(ds), "transactional")
        for r in t[t.dataset == ds].itertuples():
            p = rec.model.predict(r.algorithm, feats, float(r.param_value))
            if p is not None:
                rows.append({"dataset": ds, "source": "training LODO", "algorithm": r.algorithm,
                             "sigma": r.param_value, "true_mem": r.peak_memory_mb,
                             "pred_mem": p["memory_mb"], "true_rt": r.runtime_s,
                             "pred_rt": p["runtime_s"]})
        print("LODO %-14s" % ds, flush=True)
    lodo = pd.DataFrame(rows)
    lodo.to_csv(EX / "interval_residuals.csv", index=False)
    rec = Recommender(runs=runs)
    for src, f in UNSEEN.items():
        t = pd.read_csv(EX / f)
        t = t[PE.completed(t)]
        for ds, g in t.groupby("dataset"):
            feats = mf.extract(PE.dataset_path(ds), "transactional")
            for r in g.itertuples():
                p = rec.model.predict(r.algorithm, feats, float(r.param_value))
                if p is not None:
                    rows.append({"dataset": ds, "source": src, "algorithm": r.algorithm,
                                 "sigma": r.param_value, "true_mem": r.peak_memory_mb,
                                 "pred_mem": p["memory_mb"], "true_rt": r.runtime_s,
                                 "pred_rt": p["runtime_s"]})
        print("unseen %s" % src, flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(EX / "interval_groups.csv", index=False)
    print("model pool: %d rows, %d datasets" % (len(d), d.dataset.nunique()))


def probe_pool():
    from recommender import probe as P
    truth = {}
    for src, f in TRUTH.items():
        if not f:
            continue
        t = pd.read_csv(EX / f)
        if "category" in t:
            t = t[t.category == 1]
        t = t[PE.completed(t)]
        for r in t.itertuples():
            truth[(r.dataset, round(float(r.param_value), 9), r.algorithm)] = r.peak_memory_mb
    rows, seen = [], set()
    for line in open(EX / "probes.jsonl"):
        r = json.loads(line)
        key = (r["dataset"], round(r["sigma"], 9))
        if key in seen:
            continue
        seen.add(key)
        for a, p in r["points"].items():
            pts = [(z, tuple(v)) for z, v in p]
            if r["mode"] == "direct" and pts:
                kind, est = "measured", pts[0][1][0]
            elif r["mode"] == "sampled" and len(pts) >= 2:
                kind, est = "sampled", P.estimate(pts, r["n"], "affine", a)[0]
            else:
                continue
            tru = truth.get((r["dataset"], key[1], a))
            if tru and est and est > 0:
                rows.append({"dataset": r["dataset"], "set": r["set"], "sigma": r["sigma"],
                             "algorithm": a, "kind": kind, "true_mem": tru, "est_mem": est})
    d = pd.DataFrame(rows)
    d.to_csv(EX / "interval_groups_probe.csv", index=False)
    print("probe pool: %d rows, %d datasets (measured %d, sampled %d)"
          % (len(d), d.dataset.nunique(), d[d.kind == "measured"].dataset.nunique(),
             d[d.kind == "sampled"].dataset.nunique()))


if __name__ == "__main__":
    if "--model" in sys.argv:
        model_pool()
    if "--probe" in sys.argv:
        probe_pool()
