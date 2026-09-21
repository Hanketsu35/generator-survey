"""Censored-runtime modelling for algorithm selection.

Why this module exists
----------------------
A run that hits the 3,600 s cutoff does not have an unknown runtime -- it has a
runtime *known to exceed 3,600 s*. That is right-censored data, and 10.5% of
our 667 runs are censored: Arima 47.6%, FGC-Stream 46.6%, Zart 31.0%,
Pascal 22.4%.

The first version of this recommender imputed censored runs with the PAR10
value (10 x cutoff) and regressed on the result. Tornede et al. (2020),
`literature/pdf/run2survive.pdf`, name exactly that practice as a source of
systematically biased surrogate models: imputing with the cutoff underestimates
the true runtime, imputing with 10x invents a number nothing observed, and
dropping censored rows keeps the short runtimes while discarding the long ones,
which is worse still.

The estimator is scikit-survival's `RandomSurvivalForest` (Ishwaran et al.,
2008): log-rank splitting, Kaplan-Meier curves in the leaves, censoring handled
inside the learning procedure rather than by patching the data beforehand.

What this module adds on top of the library are the DECISION RULES. A survival
model yields a whole distribution per (instance, algorithm) rather than a point
estimate, so selection becomes decision-theoretic, and which functional of the
distribution to minimise is the actual modelling choice:

    expected_runtime  -- restricted mean survival time on [0, C]
    expected_par10    -- E[PAR10(T)]; the strongest of the Run2Survive variants
    risk_averse(a)    -- convex surrogate weighting the tail more heavily
    timeout_probability -- P(T > C), used to warn rather than to rank

The identity behind the PAR10 rule is worth recording, since it is what makes
the rule computable from a survival curve alone. With PAR10(t) = t for t <= C
and 10C otherwise,

    E[PAR10] = int_0^C t f(t) dt + 10 C S(C)
             = [ int_0^C S(t) dt - C S(C) ] + 10 C S(C)
             = int_0^C S(t) dt + 9 C S(C)

so only S on [0, C] and its endpoint are needed.

Dependency note: scikit-survival must be pinned to 0.23.0. Later releases
require numpy >= 2, which would force an upgrade of pandas, scikit-learn and
matplotlib and so break the benchmark pipeline; 0.22.x predates the
scikit-learn 1.4 API. See requirements.txt.
"""
import numpy as np

from sksurv.ensemble import RandomSurvivalForest
from sksurv.util import Surv

CUTOFF = 3600.0
PAR_FACTOR = 10.0


# ----------------------------------------------------------------------
def make_target(times, completed):
    """Structured survival target.

    `completed[i]` is True when the run finished, i.e. the event was observed;
    a timeout or abort is a right-censored observation at `times[i]`.
    """
    return Surv.from_arrays(event=np.asarray(completed, dtype=bool),
                            time=np.asarray(times, dtype=float))


def fit_rsf(X, times, completed, n_estimators=200, min_samples_leaf=3,
            random_state=0):
    """Random survival forest, or None when the data cannot support one.

    A forest needs at least one observed event; an algorithm that timed out on
    every training configuration carries no event to split on.
    """
    completed = np.asarray(completed, dtype=bool)
    if completed.sum() == 0 or len(times) < 2 * min_samples_leaf:
        return None
    rsf = RandomSurvivalForest(n_estimators=n_estimators,
                               min_samples_leaf=min_samples_leaf,
                               random_state=random_state, n_jobs=1)
    rsf.fit(np.asarray(X, dtype=float), make_target(times, completed))
    return rsf


def curve(rsf, x):
    """(grid, survival) for a single instance."""
    fn = rsf.predict_survival_function(np.asarray(x, dtype=float).reshape(1, -1))[0]
    return np.asarray(fn.x, dtype=float), np.asarray(fn.y, dtype=float)


# ----------------------------------------------------------------------
# Decision rules over a survival curve
# ----------------------------------------------------------------------
def _restricted_integral(grid, surv, upper):
    """int_0^upper S(t) dt, S held stepwise constant between grid points."""
    g = np.clip(np.asarray(grid, float), 0.0, upper)
    s = np.asarray(surv, float)
    if g[0] > 0.0:                       # S = 1 before the first grid point
        g = np.concatenate([[0.0], g])
        s = np.concatenate([[1.0], s])
    keep = np.concatenate([[True], np.diff(g) > 0])
    g, s = g[keep], s[keep]
    if g[-1] < upper:
        g = np.append(g, upper)
        s = np.append(s, s[-1])
    return float(np.sum(s[:-1] * np.diff(g)))


def survival_at(grid, surv, t):
    return float(np.interp(t, grid, surv, left=1.0, right=surv[-1]))


def expected_runtime(grid, surv, cutoff=CUTOFF):
    """Restricted mean survival time on [0, C]  (Run2SurviveExp)."""
    return _restricted_integral(grid, surv, cutoff)


def expected_par10(grid, surv, cutoff=CUTOFF, factor=PAR_FACTOR):
    """E[PAR10(T)] = int_0^C S dt + (factor-1) C S(C)  (Run2SurvivePAR10)."""
    return (_restricted_integral(grid, surv, cutoff)
            + (factor - 1.0) * cutoff * survival_at(grid, surv, cutoff))


def risk_averse(grid, surv, cutoff=CUTOFF, alpha=0.3):
    """Convex surrogate loss; smaller `alpha` is more risk-averse.

    Runtimes are rescaled to [0, 1] so that `alpha` means the same thing
    regardless of the cutoff, as in Run2Survive Section 4.2.
    """
    g = np.clip(np.asarray(grid, float), 0.0, cutoff) / cutoff
    s = np.asarray(surv, float)
    if g[0] > 0.0:
        g = np.concatenate([[0.0], g])
        s = np.concatenate([[1.0], s])
    keep = np.concatenate([[True], np.diff(g) > 0])
    g, s = g[keep], s[keep]
    if g[-1] < 1.0:
        g, s = np.append(g, 1.0), np.append(s, s[-1])
    mid = np.maximum(0.5 * (g[:-1] + g[1:]), 1e-12)
    return float(np.sum(s[:-1] * np.diff(g) * np.power(mid, alpha - 1.0)) * cutoff)


def timeout_probability(grid, surv, cutoff=CUTOFF):
    """P(T > C): the probability the run does not finish within the budget."""
    return survival_at(grid, surv, cutoff)


RULES = {
    "expected_runtime": expected_runtime,
    "expected_par10": expected_par10,
    "risk_averse": risk_averse,
}
