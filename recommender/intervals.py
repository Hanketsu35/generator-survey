"""90% prediction intervals for the engine's and the probe's cost estimates.

Why. The band the engine showed on memory was a 5-95% bootstrap of the
forest's MEAN: a statement about the average of the trees, not about the run
the user will get. Held out one dataset at a time it contained the measured
memory in 8.3% of runs (results/INTERVAL_PROTOCOL.md). The forest's spread
is also uncorrelated with its error there (r = -0.006), so it cannot be
rescaled into an interval.

What. Split-conformal intervals (Vovk et al. 2005; Lei et al. 2018) on the
log10 ratio truth/prediction. The calibration residuals are leave-one-dataset-
out: each comes from a model that never saw that dataset, which is the
situation of a user's new file (the CV+ construction of Barber et al. 2021).
One pooled residual distribution per estimate kind; the quantile level is
tightened by k/(k+1) for k calibration datasets.

Built by ``python -m recommender.intervals`` from results/interval_residuals.csv
(tools/interval_residuals.py) into recommender/data/intervals.json.
"""
import json
import math
from pathlib import Path

_HERE = Path(__file__).resolve().parent
QUANTILES = _HERE / "data" / "intervals.json"
RESIDUALS = _HERE.parent / "results" / "interval_residuals.csv"
ALPHA = 0.10
#: runtimes below this are compared at this value: the harness does not
#: resolve them, and log ratios of milliseconds would dominate the quantiles
RT_FLOOR = 0.01

_q = None


def _quantile(x, alpha, k):
    import numpy as np
    a = alpha * k / (k + 1.0)
    return [float(np.quantile(x, a / 2)), float(np.quantile(x, 1 - a / 2))]


def build(residuals=RESIDUALS, out=QUANTILES, variant="affine"):
    import numpy as np
    import pandas as pd
    d = pd.read_csv(residuals)
    rt = lambda s: np.maximum(s, RT_FLOOR)                        # noqa: E731
    kinds = {
        "model_memory": (d, np.log10(d.true_mem / d.pred_mem)),
        "model_runtime": (d, np.log10(rt(d.true_rt) / rt(d.pred_rt))),
    }
    pm, pr = "probe_%s_mem" % variant, "probe_%s_rt" % variant
    for tag, meas in (("measured", True), ("sampled", False)):
        s = d[(d.probe_measured == meas) & d[pm].notna()]
        kinds["probe_memory_" + tag] = (s, np.log10(s.true_mem / s[pm]))
        kinds["probe_runtime_" + tag] = (s, np.log10(rt(s.true_rt) / rt(s[pr])))
    q = {"alpha": ALPHA, "rt_floor": RT_FLOOR, "variant": variant}
    for name, (sub, r) in kinds.items():
        k = int(sub.dataset.nunique())
        q[name] = {"log10": _quantile(r.values, ALPHA, k), "n": int(len(r)), "datasets": k}
    Path(out).write_text(json.dumps(q, indent=1) + "\n")
    return q


def _load():
    global _q
    if _q is None:
        _q = json.loads(QUANTILES.read_text()) if QUANTILES.exists() else {}
    return _q


def interval(kind, point):
    """(lo, hi) around ``point`` for ``kind`` (e.g. "model_memory"), or None."""
    q = _load().get(kind)
    if q is None or point is None or not (point > 0):
        return None
    if kind.endswith("runtime"):
        point = max(point, _load()["rt_floor"])
    lo, hi = q["log10"]
    return (point * 10 ** lo, point * 10 ** hi)


def width(kind):
    """Ratio hi/lo of the interval for ``kind``."""
    q = _load().get(kind)
    return 10 ** (q["log10"][1] - q["log10"][0]) if q else math.nan


if __name__ == "__main__":
    for name, v in build().items():
        if isinstance(v, dict):
            lo, hi = v["log10"]
            print("%-24s x%.3f .. x%.3f  (width x%.1f, n=%d, %d datasets)"
                  % (name, 10 ** lo, 10 ** hi, 10 ** (hi - lo), v["n"], v["datasets"]))
