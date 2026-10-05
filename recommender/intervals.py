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

#: Shown to the user (``display_interval``), as against the ranking's own
#: quantiles above. Calibrated at the level of DATASETS, not runs: a user's
#: file is a new group, and exchangeability holds between groups, not
#: between the runs inside one (Dunn, Wasserman & Ramdas, JASA 2023,
#: "Distribution-free prediction sets for two-layer hierarchical models").
#: Their CDF pooling: average the per-dataset empirical CDFs of the
#: residual, take the alpha/2 and 1 - alpha/2 quantiles. Pooled runs had
#: covered 79-88% of runs on unseen datasets at a nominal 90%; leave-one-
#: dataset-out over 40 datasets, CDF pooling at 95% covered 94% (model
#: memory) and 95% / 94% (probe, measured / sampled) on average per dataset
#: (tools/interval_methods.py, tools/interval_groups_probe.py).
DISPLAY_ALPHA = 0.05
GROUPS_MODEL = _HERE.parent / "results" / "interval_groups.csv"
GROUPS_PROBE = _HERE.parent / "results" / "interval_groups_probe.csv"


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


def _cdf_pool(values, groups, alpha):
    import numpy as np
    x = np.asarray(values, float)
    g = np.asarray(groups)
    w = np.empty_like(x)
    for k in set(g.tolist()):
        m = g == k
        w[m] = 1.0 / m.sum()
    o = np.argsort(x)
    x, c = x[o], np.cumsum(w[o]) / w.sum()
    lo = x[min(np.searchsorted(c, alpha / 2), len(x) - 1)]
    hi = x[min(np.searchsorted(c, 1 - alpha / 2), len(x) - 1)]
    return [float(lo), float(hi)]


def build_display(out=QUANTILES, alpha=DISPLAY_ALPHA):
    """Add the dataset-level display quantiles to intervals.json."""
    import numpy as np
    import pandas as pd
    q = json.loads(Path(out).read_text())
    m = pd.read_csv(GROUPS_MODEL)
    p = pd.read_csv(GROUPS_PROBE)
    rt = lambda s: np.maximum(s, RT_FLOOR)                        # noqa: E731
    kinds = {"model_memory": (m.dataset, np.log10(m.true_mem / m.pred_mem)),
             "model_runtime": (m.dataset, np.log10(rt(m.true_rt) / rt(m.pred_rt)))}
    for tag in ("measured", "sampled"):
        s = p[p.kind == tag]
        kinds["probe_memory_" + tag] = (s.dataset, np.log10(s.true_mem / s.est_mem))
    disp = {"level": 1 - alpha, "method": "CDF pooling over datasets"}
    for name, (g, r) in kinds.items():
        disp[name] = {"log10": _cdf_pool(r.values, g.values, alpha), "n": int(len(r)),
                      "datasets": int(g.nunique())}
    q["display"] = disp
    Path(out).write_text(json.dumps(q, indent=1) + "\n")
    global _q
    _q = None
    return disp


#: Exact-memory pools (tools/interval_pool_exact.py) and the subsampling
#: calibration that replaced CDF pooling. Dunn, Wasserman & Ramdas's Method 2
#: draws one residual per dataset and takes order statistics floor((k+1)a/2)
#: and ceil((k+1)(1-a/2)): a finite-sample guarantee of 1-a coverage for a
#: new dataset, valid once k >= 2/a - 1. Endpoints here are averaged over
#: SUBSAMPLES draws so the interval does not depend on one random draw.
#: Leave-one-dataset-out on exact memory: probe measured 0.967 and sampled
#: 0.974 at a = 0.10 (39 and 23 datasets; 95% would need 39 per kind), model
#: memory 0.963 and runtime 0.965 at a = 0.05 (50 datasets).
#: Pools as of the all-data model (results/INTERVAL_ALLDATA_POSTHOC.md): the
#: model's residuals leave one of 75 datasets out of a model trained on all 81
#: (tools/interval_pool_all.py); the probe's span 63 datasets measured and 24
#: sampled, the small datasets of FRESH5/6 included.
EXACT_GROUPS_MODEL = _HERE.parent / "results" / "exact" / "interval_groups_all.csv"
EXACT_GROUPS_PROBE = _HERE.parent / "results" / "exact" / "interval_groups_probe_all.csv"
SUBSAMPLES = 200
LEVELS = {"model_memory": 0.95, "model_runtime": 0.95,
          "probe_memory_measured": 0.95, "probe_memory_sampled": 0.90}
#: The model's intervals are calibrated separately for native and JVM
#: programs (a Mondrian split, each side still over ~50 datasets), and the
#: runtime interval is centred on the survival MEDIAN, not the restricted mean.
#: Found on FRESH5's runtime shortfall (results/RUNTIME_INTERVAL_POSTHOC.md):
#: every miss was a slow JVM miner on a small dataset, predicted at its
#: timeout-inflated mean (Zart 1,114 s for a 0.22 s run). Leave-one-dataset-
#: out: runtime 0.969 at x95k (was 0.965 at x315k), memory 0.964 at x536.
NATIVE = {"Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth",
          "FGC_Stream"}


def model_class(algorithm):
    """Calibration class: FGC-Stream alone (its errors are far larger than the
    other native programs'), the other native programs, the JVM programs."""
    if algorithm == "FGC_Stream":
        return "fgc"
    return "native" if algorithm in NATIVE else "jvm"


def _subsample_interval(values, groups, alpha, seed=0):
    import numpy as np
    by = {}
    for v, g in zip(values, groups):
        by.setdefault(g, []).append(v)
    gs = [np.asarray(v) for v in by.values()]
    k = len(gs)
    r, s_ = int(np.floor((k + 1) * alpha / 2)), int(np.ceil((k + 1) * (1 - alpha / 2)))
    if r < 1 or s_ > k:
        raise ValueError("%d datasets cannot give a %.0f%% interval (need %d)"
                         % (k, 100 * (1 - alpha), int(np.ceil(2 / alpha - 1))))
    rng = np.random.default_rng(seed)
    lo, hi = [], []
    for _ in range(SUBSAMPLES):
        y = np.sort([g[rng.integers(len(g))] for g in gs])
        lo.append(y[r - 1])
        hi.append(y[s_ - 1])
    return [float(np.mean(lo)), float(np.mean(hi))], k


def build_display_exact(out=QUANTILES):
    """Display intervals from the exact-memory pools, by subsampling."""
    import numpy as np
    import pandas as pd
    q = json.loads(Path(out).read_text())
    m = pd.read_csv(EXACT_GROUPS_MODEL)
    p = pd.read_csv(EXACT_GROUPS_PROBE)
    rt = lambda s: np.maximum(s, RT_FLOOR)                        # noqa: E731
    kinds = {}
    cls = m.algorithm.map(model_class)
    for c in ("native", "jvm", "fgc"):
        mm = m[cls == c]
        kinds["model_memory_" + c] = (mm.dataset, np.log10(mm.true_mem / mm.pred_mem))
        kinds["model_runtime_" + c] = (mm.dataset,
                                       np.log10(rt(mm.true_rt) / rt(mm.pred_rt_median)))
    for tag in ("measured", "sampled"):
        s = p[p.kind == tag]
        kinds["probe_memory_" + tag] = (s.dataset, np.log10(s.true_mem / s.est_mem))
    disp = {"method": "subsampling over datasets (Dunn et al. 2023, Method 2), exact memory; "
                      "model split native/JVM, runtime centred on the survival median",
            # only these were in the calibration and the confirmations; an
            # interval for any other implementation would claim a coverage
            # nothing has measured
            "algorithms": sorted(set(m.algorithm))}
    for name, (g, r) in kinds.items():
        lv = LEVELS[name.replace("_native", "").replace("_jvm", "").replace("_fgc", "")]
        iv, k = _subsample_interval(r.values, g.values, 1 - lv)
        disp[name] = {"log10": iv, "n": int(len(r)), "datasets": k, "level": lv}
    q["display"] = disp
    Path(out).write_text(json.dumps(q, indent=1) + "\n")
    global _q
    _q = None
    return disp


def display_interval(kind, point):
    """(lo, hi) shown to the user for ``kind`` around ``point``, or None."""
    d = _load().get("display") or {}
    q = d.get(kind)
    if q is None or point is None or not (point > 0):
        return None
    if kind.endswith("runtime"):
        point = max(point, _load()["rt_floor"])
    lo, hi = q["log10"]
    return (point * 10 ** lo, point * 10 ** hi)


def calibrated(algorithm):
    """Whether the model's display intervals were calibrated on ``algorithm``."""
    algos = (_load().get("display") or {}).get("algorithms")
    return algos is None or algorithm in algos


def display_level(kind=None):
    """Coverage level of the interval shown for ``kind`` (or the common one)."""
    d = _load().get("display") or {}
    if kind and isinstance(d.get(kind), dict) and "level" in d[kind]:
        return d[kind]["level"]
    return d.get("level")


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
    import sys
    if "--display-exact" in sys.argv:
        for name, v in build_display_exact().items():
            if isinstance(v, dict):
                lo, hi = v["log10"]
                print("display %-24s %.0f%%  x%.3f .. x%.3f  (width x%.1f, n=%d, %d datasets)"
                      % (name, 100 * v["level"], 10 ** lo, 10 ** hi, 10 ** (hi - lo), v["n"],
                         v["datasets"]))
        sys.exit(0)
    if "--display" in sys.argv:
        for name, v in build_display().items():
            if isinstance(v, dict):
                lo, hi = v["log10"]
                print("display %-24s x%.3f .. x%.3f  (width x%.1f, n=%d, %d datasets)"
                      % (name, 10 ** lo, 10 ** hi, 10 ** (hi - lo), v["n"], v["datasets"]))
        sys.exit(0)
    for name, v in build().items():
        if isinstance(v, dict):
            lo, hi = v["log10"]
            print("%-24s x%.3f .. x%.3f  (width x%.1f, n=%d, %d datasets)"
                  % (name, 10 ** lo, 10 ** hi, 10 ** (hi - lo), v["n"], v["datasets"]))
