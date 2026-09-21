"""Algorithm-selection strategies, and the metric the field actually uses.

The first version of Layer 3 did one thing: regress log-runtime per algorithm
and take the argmin. Reading the algorithm-selection literature
(`literature/`) turned up three concrete objections to that, each implemented
here as an alternative selector so the comparison is empirical rather than
rhetorical.

1.  *Censoring.*  Timed-out runs were imputed at 10x the cutoff and regressed
    on. Tornede et al. (2020) show that imputation biases the surrogate;
    survival analysis handles censoring in the learning procedure instead.
    -> ``SurvivalSelector``  (see survival.py)

2.  *The wrong loss.*  Hanselle et al. (2022, HARRIS) observe that accurate
    runtime prediction is sufficient but not necessary for a correct ranking:
    regression solves a harder problem than selection requires, and pays for
    it in accuracy. -> ``PairwiseRankSelector``

3.  *The wrong metric.*  Geometric-mean slowdown is not comparable with
    published work. The standard is normalized PAR10,

        nPAR10 = (PAR10_selector - PAR10_VBS) / (PAR10_SBS - PAR10_VBS)

    where 0 means oracle-perfect, 1 means no better than always running the
    single best algorithm, and > 1 means actively harmful. -> ``npar10``

``SBSSelector`` and ``VBSOracle`` bracket the scale.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

from . import survival as sv

CUTOFF = 3600.0
PAR_FACTOR = 10.0


def par10(runtime, completed, cutoff=CUTOFF, factor=PAR_FACTOR):
    """Observed PAR10 cost of a single run."""
    return float(runtime) if completed else cutoff * factor


def add_par10(df):
    df = df.copy()
    df["par10"] = [par10(r, c) for r, c in zip(df.runtime_s, df.completed)]
    return df


# ======================================================================
class Selector:
    name = "base"

    def fit(self, train, cols):
        raise NotImplementedError

    def select(self, x, candidates):
        """Return the chosen algorithm from `candidates` for feature row `x`."""
        raise NotImplementedError


class SBSSelector(Selector):
    """Single Best Solver: one fixed algorithm, chosen on the training set."""
    name = "SBS (fixed choice)"

    def fit(self, train, cols):
        t = add_par10(train)
        self.best_ = t.groupby("algorithm").par10.mean().idxmin()
        self.order_ = t.groupby("algorithm").par10.mean().sort_values().index.tolist()
        return self

    def select(self, x, candidates):
        if self.best_ in candidates:
            return self.best_
        for a in self.order_:                 # fall back down the ranking
            if a in candidates:
                return a
        return candidates[0]


class RegressionSelector(Selector):
    """Per-algorithm regression on PAR10-imputed runtime (the original Layer 3)."""
    name = "regression (PAR10-imputed)"

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, train, cols):
        self.cols_ = cols
        self.models_, self.fallback_ = {}, {}
        for algo, g in add_par10(train).groupby("algorithm"):
            y = np.log10(np.clip(g.par10.values, 1e-3, None))
            self.fallback_[algo] = float(y.mean())
            if len(g) >= 6:
                m = RandomForestRegressor(n_estimators=200, min_samples_leaf=2,
                                          random_state=self.random_state, n_jobs=1)
                m.fit(g[cols].to_numpy(float), y)
                self.models_[algo] = m
        return self

    def score(self, x, algo):
        m = self.models_.get(algo)
        if m is None:
            return self.fallback_.get(algo, np.log10(CUTOFF * PAR_FACTOR))
        return float(m.predict(np.asarray(x, float).reshape(1, -1))[0])

    def select(self, x, candidates):
        return min(candidates, key=lambda a: self.score(x, a))


class SurvivalSelector(Selector):
    """Random survival forest per algorithm + a decision rule over the curve."""

    def __init__(self, rule="expected_par10", alpha=0.3, random_state=0):
        self.rule = rule
        self.alpha = alpha
        self.random_state = random_state
        self.name = "survival (%s)" % rule

    def fit(self, train, cols):
        self.cols_ = cols
        self.models_, self.fallback_ = {}, {}
        for algo, g in train.groupby("algorithm"):
            # Fallback for algorithms a forest cannot be fitted for: the
            # observed mean PAR10, which is what SBS would use anyway.
            self.fallback_[algo] = float(
                np.mean([par10(r, c) for r, c in zip(g.runtime_s, g.completed)]))
            rsf = sv.fit_rsf(g[cols].to_numpy(float), g.runtime_s.values,
                             g.completed.values, random_state=self.random_state)
            if rsf is not None:
                self.models_[algo] = rsf
        return self

    def score(self, x, algo):
        rsf = self.models_.get(algo)
        if rsf is None:
            return self.fallback_.get(algo, CUTOFF * PAR_FACTOR)
        grid, s = sv.curve(rsf, x)
        if self.rule == "risk_averse":
            return sv.risk_averse(grid, s, alpha=self.alpha)
        return sv.RULES[self.rule](grid, s)

    def timeout_risk(self, x, algo):
        rsf = self.models_.get(algo)
        if rsf is None:
            return float("nan")
        grid, s = sv.curve(rsf, x)
        return sv.timeout_probability(grid, s)

    def select(self, x, candidates):
        return min(candidates, key=lambda a: self.score(x, a))


class PairwiseRankSelector(Selector):
    """SATzilla'11-style pairwise classification with cost-sensitive weights.

    For every unordered pair of algorithms a classifier predicts which of the
    two is cheaper on an instance, trained only on configurations where both
    ran. Each training example is weighted by |cost_a - cost_b|, so pairs that
    barely differ cannot outvote pairs that differ by an hour. At prediction
    time the algorithms hold a round robin and the most-wins candidate is
    chosen -- the model never has to predict a runtime.
    """
    name = "pairwise ranking"

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, train, cols):
        self.cols_ = cols
        t = add_par10(train)
        wide = t.pivot_table(index=["dataset", "param_value"],
                             columns="algorithm", values="par10", aggfunc="min")
        feats = (t.drop_duplicates(subset=["dataset", "param_value"])
                  .set_index(["dataset", "param_value"])[cols])
        feats = feats.reindex(wide.index)

        self.algos_ = list(wide.columns)
        self.models_ = {}
        for i, a in enumerate(self.algos_):
            for b in self.algos_[i + 1:]:
                m = wide[[a, b]].dropna()
                if len(m) < 8:
                    continue
                X = feats.loc[m.index].to_numpy(float)
                y = (m[a].values < m[b].values).astype(int)
                if len(np.unique(y)) < 2:       # one always wins: constant rule
                    self.models_[(a, b)] = int(y[0])
                    continue
                w = np.abs(m[a].values - m[b].values)
                w = w / (w.mean() or 1.0)
                clf = RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                             random_state=self.random_state, n_jobs=1)
                clf.fit(X, y, sample_weight=w)
                self.models_[(a, b)] = clf
        return self

    def select(self, x, candidates):
        x = np.asarray(x, float).reshape(1, -1)
        votes = {a: 0.0 for a in candidates}
        for i, a in enumerate(candidates):
            for b in candidates[i + 1:]:
                key, flip = ((a, b), False) if (a, b) in self.models_ else ((b, a), True)
                m = self.models_.get(key)
                if m is None:
                    continue
                if isinstance(m, int):
                    p = float(m)
                else:
                    p = float(m.predict_proba(x)[0][1])
                # p is P(first of the stored pair is cheaper)
                p_a = 1.0 - p if flip else p
                votes[a] += p_a
                votes[b] += 1.0 - p_a
        return max(candidates, key=lambda a: votes[a])


class VBSOracle(Selector):
    """Virtual Best Solver: cheats by reading the true costs. Upper bound only."""
    name = "VBS (oracle)"

    def fit(self, train, cols):
        return self

    def select_true(self, row_costs):
        return min(row_costs, key=row_costs.get)


# ======================================================================
def npar10(selector_cost, sbs_cost, vbs_cost):
    """Normalized PAR10: 0 = oracle, 1 = single best, > 1 = worse than fixed."""
    denom = sbs_cost - vbs_cost
    if abs(denom) < 1e-12:
        return float("nan")
    return (selector_cost - vbs_cost) / denom
