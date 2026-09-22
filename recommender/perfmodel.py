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
from . import landmarks as _lm

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
    return attach_landmarks(df)


#: Feature sets available to Layer 3. ``static`` is what the published results
#: used; ``landmarks`` is threshold-dependent (see landmarks.py). Which one a
#: given experiment uses is a reported choice, not a default buried in code,
#: because the ablation in ``feature_ablation.py`` shows the answer depends on
#: the objective: landmarks raise the share of performance variance the instance
#: plane explains from 0.233 to 0.517, but on the memory objective -- the one
#: slice with real headroom -- the static set still selects better.
FEATURE_SETS = ("static", "landmarks", "both")


def design_columns(kind="static"):
    """Column names for a named feature set."""
    static = list(mf.FEATURE_NAMES) + ["log_thr"]
    if kind == "static":
        return static
    if kind == "landmarks":
        return list(_lm.LANDMARK_NAMES)
    if kind == "both":
        return static + list(_lm.LANDMARK_NAMES)
    raise ValueError("unknown feature set %r (expected one of %r)"
                     % (kind, FEATURE_SETS))


def attach_landmarks(df):
    """Left-join cached landmark features on (dataset, param_value).

    Left, not inner: landmarks are only defined where the run parameter IS a
    relative support threshold, so the utility and stream categories -- whose
    parameter is an absolute utility or a window size -- keep their rows with
    NaN landmarks rather than vanishing from the table. A caller that asks for
    landmark columns must therefore drop incomplete rows itself, which
    ``rows_with_features`` does.

    The join is keyed on ``param_name == "minsup"`` as well as on the dataset
    and the value, and that guard is load-bearing rather than defensive. Every
    landmark is a statement about the sub-problem *at or above* a minimum
    support. Arima's parameter is ``maxsup``, an upper bound -- it mines rare
    itemsets -- so a value of 0.2 selects the complement of what the same number
    selects for a frequent miner. Joining on (dataset, value) alone silently
    attached minsup landmarks to 12 Arima runs, describing the opposite region
    of the support axis from the one those runs explored.
    """
    cache = _lm.load_cache()
    if not cache or "param_name" not in df.columns:
        return df
    eligible = df[df.param_name == "minsup"]
    rows = []
    for ds, pv in (eligible[["dataset", "param_value"]]
                   .drop_duplicates().itertuples(index=False)):
        entry = cache.get(_lm._key(ds, pv))
        if entry is not None:
            rows.append(dict(dataset=ds, param_name="minsup", param_value=pv, **entry))
    if not rows:
        return df
    return df.merge(pd.DataFrame(rows),
                    on=["dataset", "param_name", "param_value"], how="left")


def rows_with_features(df, kind="static"):
    """Subset of ``df`` for which every column of the feature set is present."""
    cols = design_columns(kind)
    have = [c for c in cols if c in df.columns]
    if len(have) < len(cols):
        raise KeyError("feature set %r needs %s; missing %s. Build the cache "
                       "with `python -m recommender.landmarks`."
                       % (kind, cols, sorted(set(cols) - set(have))))
    return df.dropna(subset=cols)


def _design(df, kind="static"):
    return df[design_columns(kind)].to_numpy(dtype=float)


class PerformanceModel:
    """Per-implementation runtime / memory / completion predictors."""

    #: Class-level default so that a model pickled by an older version -- the
    #: engine caches the fitted model under ``out/`` -- still answers
    #: ``self.features`` after unpickling instead of raising AttributeError.
    #: Unpickling restores ``__dict__`` and never runs ``__init__``, so any
    #: attribute added to the constructor needs a class default or a cache
    #: invalidation; this is the cheaper of the two.
    features = "static"

    def __init__(self, min_rows=8, seed=0, use_survival=True, features="static"):
        self.min_rows = min_rows
        self.seed = seed
        #: Which feature set the per-implementation models are fitted on.
        #: ``static`` is the default deliberately, not by inheritance: the
        #: ablation (feature_ablation.py, bench_selectors --features) finds the
        #: better set depends on the objective. Threshold-dependent landmarks
        #: double the instance plane's explained performance variance and win
        #: decisively on runtime, but on MEMORY they lose -- every selector's
        #: bootstrap band then spans 1.0, where the static set reaches nPAR10
        #: 0.445 with P(beats the fixed choice) = 0.96. Since the engine reports
        #: both runtime and memory from one fitted model, and the runtime gain is
        #: worth 3.1 ms against a 9.9 ms oracle gap while the memory loss is
        #: worth 7.4 MB against a 13.3 MB gap, static is the choice that costs
        #: least where it is wrong.
        self.features = features
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
        # Rows lacking the chosen features cannot train a model on them; for the
        # static set this is a no-op, for landmarks it drops the categories whose
        # parameter is not a support threshold.
        df = rows_with_features(df, self.features)
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
                X = _design(ok, self.features)
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
                c.fit(_design(g, self.features), g.completed.astype(int))
                self.comp[algo] = c

            # Survival model over ALL rows, censored ones included.
            if self.use_survival and len(g) >= self.min_rows:
                rsf = _sv.fit_rsf(_design(g, self.features), g.runtime_s.values,
                                  g.completed.values, random_state=self.seed)
                if rsf is not None:
                    self.surv[algo] = rsf
        return self

    # ------------------------------------------------------------------
    def _x(self, feats, threshold):
        """Feature row for one (dataset features, threshold) pair.

        ``feats`` may carry landmark columns as well as static ones; whichever
        the fitted feature set names are read from it, and ``log_thr`` is derived
        from the threshold because it is a property of the query rather than of
        the dataset.
        """
        merged = dict(feats)
        # ALWAYS derived from the threshold argument, never taken from `feats`.
        # `feats` is often a row of the runs table, which carries the log_thr of
        # the run it came from; letting that win silently ignores the threshold
        # being asked about. A `setdefault` here did exactly that and moved E3's
        # runtime MAE from 0.727 to 1.422 before it was caught.
        merged["log_thr"] = float(np.log10(max(threshold, 1e-9)))
        cols = design_columns(self.features)
        missing = [c for c in cols if c not in merged]
        if missing:
            raise KeyError(
                "feature set %r needs %s, which the caller did not supply. "
                "Landmark features come from landmarks.DatasetProbe(...).at(sigma)."
                % (self.features, missing))
        return np.array([[float(merged[c]) for c in cols]], dtype=float)

    def predict(self, algo, feats, threshold):
        """Return dict(runtime_s, memory_mb, p_complete, source)."""
        fb = self.fallback.get(algo)
        if fb is None:
            return None
        x = self._x(feats, threshold)
        src = "model"
        mem_band = None
        if algo in self.rt:
            rt = float(10 ** self.rt[algo].predict(x)[0])
            mem = float(10 ** self.mem[algo].predict(x)[0])
            # Per-tree spread of the memory forest, bootstrapped the same way
            # as the runtime band so the two are comparable.
            per_tree = np.array([10 ** t.predict(x)[0]
                                 for t in self.mem[algo].estimators_])
            rng = np.random.default_rng(self.seed)
            idx = rng.integers(0, per_tree.size, size=(300, per_tree.size))
            boot = per_tree[idx].mean(axis=1)
            mem_band = (float(per_tree.mean()),
                        float(np.percentile(boot, 5)),
                        float(np.percentile(boot, 95)))
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
        band = None
        if algo in self.surv:
            grid, s = _sv.curve(self.surv[algo], x)
            rt = _sv.expected_runtime(grid, s)
            p = 1.0 - _sv.timeout_probability(grid, s)
            par10 = _sv.expected_par10(grid, s)
            # How precise is that number? The engine needs this to avoid
            # presenting a strict ranking over indistinguishable candidates.
            band = _sv.rule_interval(self.surv[algo], x,
                                     rule=_sv.expected_par10,
                                     random_state=self.seed)
            src = "survival"

        return {"runtime_s": rt, "memory_mb": mem, "p_complete": p,
                "expected_par10": par10, "cost_band": band,
                "memory_band": mem_band, "source": src}

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
