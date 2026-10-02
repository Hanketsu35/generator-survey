"""Group-level residual pool for the probe's memory estimates, and the
leave-one-group-out comparison of calibrations (tools/interval_methods.py).

    python tools/interval_groups_probe.py

Residual = log10(true / probe estimate) for every completed native run that
the probe measured (direct) or extrapolated (sampled, current form: affine,
Gr-growth fixed-plus-power). The probe learns nothing, so every group is out
of sample. Output: results/interval_groups_probe.csv
"""
import json
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

import interval_methods as IM                              # noqa: E402
import probe_eval as PE                                    # noqa: E402
from recommender import probe as P                        # noqa: E402

CSV_SETS = [("training", "results/training_runs.csv", "results/probe_points.csv"),
            ("confirm", "results/real_extra3_summary.csv", "results/probe_points_confirm.csv"),
            ("hard", "results/hard_summary.csv", "results/probe_points_hard.csv")]
JSON_SETS = [("fresh", "results/fresh_summary.csv", "results/probe_fresh.jsonl"),
             ("fresh2", "results/fresh2_summary.csv", "results/probe_fresh2.jsonl"),
             ("fresh3", "results/fresh3_summary.csv", "results/probe_fresh3.jsonl"),
             ("lag screen", None, "results/probe_lag.jsonl")]


def estimates_csv(path):
    d = pd.read_csv(path)
    for (ds, sg), g in d.groupby(["dataset", "sigma"]):
        n, mode = int(g.n.iloc[0]), g["mode"].iloc[0]
        for a, h in g.groupby("algorithm"):
            h = h.dropna(subset=["size"]).sort_values("size")
            pts = [(int(q.size), (q.memory_mb, q.runtime_s)) for q in h.itertuples()]
            if mode == "direct" and pts:
                yield ds, sg, a, "measured", pts[0][1][0]
            elif mode == "sampled" and len(pts) >= 2:
                yield ds, sg, a, "sampled", P.estimate(pts, n, "affine", a)[0]


def estimates_json(path):
    for line in open(path):
        r = json.loads(line)
        for a, p in r["points"].items():
            pts = [(z, tuple(v)) for z, v in p]
            if r["mode"] == "direct" and pts:
                yield r["dataset"], r["sigma"], a, "measured", pts[0][1][0]
            elif r["mode"] == "sampled" and len(pts) >= 2:
                yield r["dataset"], r["sigma"], a, "sampled", P.estimate(pts, r["n"], "affine", a)[0]


def main():
    rows = []
    for name, truth, pts, gen in ([(a, b, c, estimates_csv) for a, b, c in CSV_SETS]
                                  + [(a, b, c, estimates_json) for a, b, c in JSON_SETS if b]):
        t = pd.read_csv(truth)
        if "category" in t:
            t = t[t.category == 1]
        t = t[PE.completed(t)]
        tv = {(r.dataset, round(float(r.param_value), 9), r.algorithm): r.peak_memory_mb
              for r in t.itertuples()}
        for ds, sg, a, kind, est in gen(pts):
            tru = tv.get((ds, round(float(sg), 9), a))
            if tru and est and est > 0:
                rows.append({"dataset": ds, "set": name, "sigma": sg, "algorithm": a, "kind": kind,
                             "true_mem": tru, "est_mem": est})
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "interval_groups_probe.csv", index=False)
    d["r"] = np.log10(d.true_mem / d.est_mem)
    print("%d residuals, %d groups (measured %d groups, sampled %d groups)"
          % (len(d), d.dataset.nunique(), d[d.kind == "measured"].dataset.nunique(),
             d[d.kind == "sampled"].dataset.nunique()))
    for kind in ("measured", "sampled"):
        q = d[d.kind == kind]
        gs = {g: v.r.values for g, v in q.groupby("dataset")}
        for a in (0.10, 0.05):
            print("== probe %s, nominal %.0f%%, %d groups" % (kind, 100 * (1 - a), len(gs)))
            for mname, f in IM.METHODS.items():
                cov, wid = [], []
                for g, test in gs.items():
                    lo, hi = f([v for h, v in gs.items() if h != g], a)
                    cov.append(((test >= lo) & (test <= hi)).mean())
                    wid.append(10 ** (hi - lo) if np.isfinite(hi - lo) else np.inf)
                cov = np.array(cov)
                print("   %-16s mean group coverage %.3f | groups >= nominal %2d/%d | min %.2f | width x%.2f"
                      % (mname, cov.mean(), (cov >= 1 - a).sum(), len(cov), cov.min(), np.median(wid)))


if __name__ == "__main__":
    main()
