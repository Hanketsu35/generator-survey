"""Layer 3 - performance prediction over the semantically eligible set.

Trained on ``results/summary.csv`` (667 controlled runs).  Targets per
implementation:

    runtime            random survival forest over ALL runs, censored included
    completion         P(T <= cutoff), read off the same survival curve
    log10 peak memory  regression on completed runs (memory is not censored:
                       it is recorded even when a run is killed at the cutoff)

Runtime was originally a regression on completed runs only.  That silently
discards the slowest runs while keeping the fastest, which biases the surrogate
optimistically -- the failure mode Tornede et al. (2020) document, and one that
matters here because 10.5% of runs are censored (Arima 47.6%, FGC-Stream 46.6%,
Zart 31.0%, Pascal 22.4%).  ``recommender/bench_selectors.py`` measures the
difference: on the high-censoring category the survival selector reaches
nPAR10 0.000 against the regression selector's 0.996.

Two design decisions are forced by the size of the meta-instance set.  There
are only seven transactional datasets, so (a) evaluation must be
leave-one-DATASET-out rather than leave-one-run-out -- otherwise the model is
tested on near-duplicates of its training rows, which inflates accuracy
enormously -- and (b) the models are deliberately small and heavily
regularised.  ``evaluate.py`` reports the model against a per-algorithm
constant baseline; if it cannot beat that baseline, the honest conclusion is
that meta-features carry no signal at this sample size, and the paper should
say so.
"""
import os
import numpy as np
import pandas as pd

from . import metafeatures as mf
from . import survival as _sv

_HERE = os.path.dirname(os.path.abspath(__file__))
_SUMMARY = os.path.join(os.path.dirname(_HERE), "results", "summary.csv")

TIMEOUT_S = 3600.0
PAR_PENALTY = 10.0          # PAR10 convention for a non-completing run


def load_runs(path=_SUMMARY):
    """Load summary.csv and attach meta-features. Returns a tidy DataFrame."""
    df = pd.read_csv(path)
    df["completed"] = (
        (df.timed_out.astype(str).str.lower() != "true") & df.error.isna()
    )
    cache = mf.load_cache()
    missing = sorted(set(df.dataset) - set(cache))
    if missing:
        cache = mf.build_cache()
    rows = []
    for name in df.dataset.unique():
        if name not in cache:
            continue
        rows.append(dict(dataset=name, **{k: cache[name][k] for k in mf.FEATURE_NAMES}))
    feats = pd.DataFrame(rows)
    df = df.merge(feats, on="dataset", how="inner")
    # The threshold is part of the instance, not of the dataset.
    df["log_thr"] = np.log10(df.param_value.clip(lower=1e-9))
    return df


def _design(df):
    cols = list(mf.FEATURE_NAMES) + ["log_thr"]
    return df[cols].to_numpy(dtype=float)


class PerformanceModel:
    """Per-implementation runtime / memory / completion predictors."""

    def __init__(self, min_rows=8, seed=0, use_survival=True):
        self.min_rows = min_rows
        self.seed = seed
        #: Model runtime with a random survival forest instead of regressing on
        #: completed runs only. Dropping timed-out runs keeps the short
        #: runtimes and discards the long ones, which biases the surrogate
        #: optimistically -- see survival.py and literature/pdf/run2survive.pdf.
        #: Measured effect (recommender/bench_selectors.py): on the
        #: high-censoring category the survival selector reaches nPAR10 0.000
        #: where the regression selector reaches 0.996.
        self.use_survival = use_survival
        self.rt = {}
        self.mem = {}
        self.comp = {}
        self.surv = {}
        self.fallback = {}      # per-algorithm constants, always available
        self.trained_on = None

    # ------------------------------------------------------------------
    def fit(self, df, exclude_dataset=None):
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

        if exclude_dataset:
            df = df[df.dataset != exclude_dataset]
        self.trained_on = sorted(df.dataset.unique())

        for algo, g in df.groupby("algorithm"):
            ok = g[g.completed]
            # Constant baseline: always defined, used when a model cannot be fit.
            self.fallback[algo] = {
                "rt": float(np.log10(ok.runtime_s.clip(lower=1e-3)).mean()) if len(ok) else np.log10(TIMEOUT_S),
                "mem": float(np.log10(ok.peak_memory_mb.clip(lower=1.0)).mean()) if len(ok) else 3.0,
                "comp": float(g.completed.mean()),
            }
            if len(ok) >= self.min_rows:
                X = _design(ok)
                kw = dict(n_estimators=200, min_samples_leaf=2,
                          random_state=self.seed, n_jobs=1)
                m1 = RandomForestRegressor(**kw)
                m1.fit(X, np.log10(ok.runtime_s.clip(lower=1e-3)))
                self.rt[algo] = m1
                m2 = RandomForestRegressor(**kw)
                m2.fit(X, np.log10(ok.peak_memory_mb.clip(lower=1.0)))
                self.mem[algo] = m2
            # completion needs both classes to be present
            if len(g) >= self.min_rows and g.completed.nunique() > 1:
                c = RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                           random_state=self.seed, n_jobs=1)
                c.fit(_design(g), g.completed.astype(int))
                self.comp[algo] = c

            # Survival model over ALL rows, censored ones included.
            if self.use_survival and len(g) >= self.min_rows:
                rsf = _sv.fit_rsf(_design(g), g.runtime_s.values,
                                  g.completed.values, random_state=self.seed)
                if rsf is not None:
                    self.surv[algo] = rsf
        return self

    # ------------------------------------------------------------------
    def _x(self, feats, threshold):
        v = [float(feats[k]) for k in mf.FEATURE_NAMES]
        v.append(float(np.log10(max(threshold, 1e-9))))
        return np.array([v], dtype=float)

    def predict(self, algo, feats, threshold):
        """Return dict(runtime_s, memory_mb, p_complete, source)."""
        fb = self.fallback.get(algo)
        if fb is None:
            return None
        x = self._x(feats, threshold)
        src = "model"
        if algo in self.rt:
            rt = float(10 ** self.rt[algo].predict(x)[0])
            mem = float(10 ** self.mem[algo].predict(x)[0])
        else:
            rt = float(10 ** fb["rt"])
            mem = float(10 ** fb["mem"])
            src = "constant"
        if algo in self.comp:
            p = float(self.comp[algo].predict_proba(x)[0][1])
        else:
            p = fb["comp"]

        # The survival model supersedes both, where one could be fitted: it is
        # estimated from censored and uncensored runs together, so neither the
        # runtime nor the completion probability is biased by discarding the
        # runs that hit the cutoff.
        par10 = None
        if algo in self.surv:
            grid, s = _sv.curve(self.surv[algo], x)
            rt = _sv.expected_runtime(grid, s)
            p = 1.0 - _sv.timeout_probability(grid, s)
            par10 = _sv.expected_par10(grid, s)
            src = "survival"

        return {"runtime_s": rt, "memory_mb": mem, "p_complete": p,
                "expected_par10": par10, "source": src}

    # ------------------------------------------------------------------
    @staticmethod
    def expected_cost(pred):
        """Expected PAR10 cost of running this implementation.

        Where a survival curve exists this is E[PAR10(T)] taken over the whole
        predicted distribution. The hand-rolled alternative below --
        p*runtime + (1-p)*10C -- multiplies two separately predicted
        quantities and so double-counts their errors; it is kept only as the
        fallback for implementations with too few runs to fit a forest.
        """
        if pred.get("expected_par10") is not None:
            return float(pred["expected_par10"])
        p = pred["p_complete"]
        return p * pred["runtime_s"] + (1.0 - p) * PAR_PENALTY * TIMEOUT_S


# ----------------------------------------------------------------------
def pareto_front(items, keys=("runtime_s", "memory_mb")):
    """Indices of the non-dominated items (minimisation on every key)."""
    front = []
    for i, a in enumerate(items):
        dominated = False
        for j, b in enumerate(items):
            if i == j:
                continue
            le = all(b[k] <= a[k] for k in keys)
            lt = any(b[k] < a[k] for k in keys)
            if le and lt:
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front
