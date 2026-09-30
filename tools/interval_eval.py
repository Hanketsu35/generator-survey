"""Score results/INTERVAL_PROTOCOL.md on the nine unseen datasets.

    python tools/interval_eval.py
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402

TRUTH = ["results/real_extra3_summary.csv", "results/hard_summary.csv"]
POINTS = ["results/probe_points_confirm.csv", "results/probe_points_hard.csv"]
OUT = _ROOT / "results" / "interval_eval_output.txt"
FROZEN = ["recommender/intervals.py", "recommender/data/intervals.json"]


def frozen_ok():
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/INTERVAL_PROTOCOL.md"],
                       capture_output=True, text=True, check=True).stdout.strip()
    ok = True
    for path, commit in [(p, c) for p in FROZEN] + [("results/training_runs.csv", "490be30")]:
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (commit, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, commit))
            ok = False
    return ok


def main():
    if not frozen_ok():
        return 2
    from recommender import intervals as I
    from recommender import metafeatures as mf
    from recommender.engine import Recommender
    rec = Recommender()
    t = pd.concat([pd.read_csv(p) for p in TRUTH])
    t = t[PE.completed(t)]
    pc = {}
    for p in POINTS:
        PE.POINTS = _ROOT / p
        pc.update(PE.probe_costs("affine"))
    rows = []
    for ds, g in t.groupby("dataset"):
        feats = mf.extract(PE.dataset_path(ds), "transactional")
        for r in g.itertuples():
            pred = rec.model.predict(r.algorithm, feats, float(r.param_value))
            if pred is None:
                continue
            m, rt = r.peak_memory_mb, r.runtime_s
            mi, ri = I.interval("model_memory", pred["memory_mb"]), I.interval("model_runtime", pred["runtime_s"])
            mb = pred.get("memory_band")
            row = {"dataset": ds, "sigma": r.param_value, "algorithm": r.algorithm,
                   "I1": mi[0] <= m <= mi[1], "I3": ri[0] <= max(rt, I.RT_FLOOR) <= ri[1],
                   "old": (mb[1] <= m <= mb[2]) if mb else np.nan,
                   "w_model_mem": mi[1] / mi[0]}
            c = pc.get((ds, round(float(r.param_value), 9)), {}).get("costs", {})
            if r.algorithm in c:
                pm, prt, meas = c[r.algorithm]
                tag = "measured" if meas else "sampled"
                pi = I.interval("probe_memory_" + tag, pm)
                qi = I.interval("probe_runtime_" + tag, prt)
                row.update({"probe": tag, "I2": pi[0] <= m <= pi[1] if pi else np.nan,
                            "I4": qi[0] <= max(rt, I.RT_FLOOR) <= qi[1] if qi else np.nan,
                            "w_probe_mem": pi[1] / pi[0] if pi else np.nan})
            rows.append(row)
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "interval_eval_rows.csv", index=False)
    L = []
    L.append("%d completed runs, %d datasets" % (len(d), d.dataset.nunique()))
    L.append("old band (bootstrap of the forest mean) coverage: %.3f" % d.old.dropna().astype(float).mean())
    names = {"I1": "model memory", "I2": "probe memory", "I3": "model runtime", "I4": "probe runtime"}
    for k, nm in names.items():
        x = d[k].dropna().astype(float)
        per = d.dropna(subset=[k]).groupby("dataset")[k].apply(lambda s: s.astype(float).mean())
        L.append("%s %-14s coverage %.3f (n=%d) | per dataset mean %.3f, min %.3f -> %s"
                 % (k, nm, x.mean(), len(x), per.mean(), per.min(), "PASS" if x.mean() >= 0.85 else "FAIL"))
    for tag, s in d.dropna(subset=["I2"]).groupby("probe"):
        L.append("   probe %-8s memory coverage %.3f (n=%d)" % (tag, s.I2.astype(float).mean(), len(s)))
    L.append("per dataset (I1, I2):")
    for ds, s in d.groupby("dataset"):
        L.append("   %-14s n=%3d  I1 %.2f  I2 %s" % (ds, len(s), s.I1.mean(),
                 "%.2f" % s.I2.dropna().astype(float).mean() if s.I2.notna().any() else "-"))
    L.append("median width: model memory x%.1f, probe memory x%.2f"
             % (d.w_model_mem.median(), d.w_probe_mem.median()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
