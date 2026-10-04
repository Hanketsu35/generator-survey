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
import os

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


class SunnySelector(Selector):
    """SUNNY (Amadini et al.), in its single-pick form.

    The most-cited k-nearest-neighbour selector in the algorithm-selection
    literature, and the baseline an ASlib-literate reader expects to see before
    believing any learned model. It is also the strongest possible argument that
    a result is not an artefact of model complexity: SUNNY fits nothing.

    For an instance, take the ``k`` nearest training instances in standardised
    feature space, and pick the algorithm that solved the most of them, breaking
    ties by lower mean cost over that neighbourhood. The published method spends
    the remaining budget on a *schedule* over several algorithms; only the
    selection half is implemented, because the benchmark measures one run per
    configuration and a schedule has no meaning against it.

    Features are standardised on the training fold, so the distance is not
    dominated by whichever feature happens to have the largest units --
    ``log_n_tx`` and ``max_len`` differ by two orders of magnitude here.
    """

    def __init__(self, k=16):
        self.k = k
        self.name = "SUNNY (k-NN, k=%d)" % k

    def fit(self, train, cols):
        self.cols_ = cols
        t = add_par10(train)
        wide_cost = t.pivot_table(index=["dataset", "param_value"],
                                  columns="algorithm", values="par10", aggfunc="min")
        wide_done = t.pivot_table(index=["dataset", "param_value"],
                                  columns="algorithm", values="completed",
                                  aggfunc="max")
        feats = (t.drop_duplicates(subset=["dataset", "param_value"])
                  .set_index(["dataset", "param_value"])[cols]).reindex(wide_cost.index)

        X = feats.to_numpy(float)
        self.mu_ = np.nanmean(X, axis=0)
        self.sd_ = np.nanstd(X, axis=0)
        self.sd_[self.sd_ < 1e-12] = 1.0
        self.X_ = (X - self.mu_) / self.sd_
        self.cost_ = wide_cost
        self.done_ = wide_done.reindex(wide_cost.index)
        self.order_ = t.groupby("algorithm").par10.mean().sort_values().index.tolist()
        return self

    def select(self, x, candidates):
        z = (np.asarray(x, float) - self.mu_) / self.sd_
        d = np.linalg.norm(self.X_ - z, axis=1)
        k = min(self.k, len(d))
        idx = np.argsort(d)[:k]

        best, best_key = None, None
        for a in candidates:
            if a not in self.cost_.columns:
                continue
            costs = self.cost_[a].to_numpy(float)[idx]
            done = self.done_[a].to_numpy(float)[idx]
            solved = float(np.nansum(done))
            mean_cost = float(np.nanmean(costs)) if np.isfinite(costs).any() else np.inf
            # More solved is better; then cheaper on the neighbourhood.
            key = (-solved, mean_cost)
            if best_key is None or key < best_key:
                best, best_key = a, key
        if best is not None:
            return best
        for a in self.order_:                 # nothing comparable: fall back
            if a in candidates:
                return a
        return candidates[0]


class ISACSelector(Selector):
    """ISAC (Kadioglu, Malitsky, Sellmann & Tierney, ECAI 2010).

    Instances are clustered in standardised feature space and each cluster is
    assigned the algorithm with the lowest mean cost over its members; a new
    instance gets its nearest cluster's algorithm. ISAC chooses the number of
    clusters with g-means. Here k is chosen by silhouette over 2..10, a
    documented simplification.
    """
    name = "ISAC (k-means clusters)"

    def fit(self, train, cols):
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        t = add_par10(train)
        wide = t.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                             values="par10", aggfunc="min")
        feats = (t.drop_duplicates(subset=["dataset", "param_value"])
                  .set_index(["dataset", "param_value"])[cols]).reindex(wide.index)
        X = feats.to_numpy(float)
        self.mu_ = np.nanmean(X, axis=0)
        self.sd_ = np.nanstd(X, axis=0)
        self.sd_[self.sd_ < 1e-12] = 1.0
        Z = np.nan_to_num((X - self.mu_) / self.sd_)
        best = (None, -2)
        for k in range(2, min(10, len(Z) - 1) + 1):
            km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
            sc = silhouette_score(Z, km.labels_) if len(set(km.labels_)) > 1 else -1
            if sc > best[1]:
                best = (km, sc)
        self.km_ = best[0]
        self.order_ = t.groupby("algorithm").par10.mean().sort_values().index.tolist()
        self.rank_ = {}
        for c in range(self.km_.n_clusters):
            m = wide[self.km_.labels_ == c]
            self.rank_[c] = m.mean().sort_values().index.tolist()
        return self

    def select(self, x, candidates):
        z = np.nan_to_num((np.asarray(x, float) - self.mu_) / self.sd_)
        c = int(self.km_.predict(z.reshape(1, -1))[0])
        for a in self.rank_.get(c, []) + self.order_:
            if a in candidates:
                return a
        return candidates[0]


class AutoFolioSelector(Selector):
    """AutoFolio (Lindauer, Hoos, Hutter & Schaub, JAIR 2015), run as published.

    AutoFolio configures an algorithm selector (pairwise classification or
    regression, per-algorithm regression, multi-class classification, with
    feature preprocessing and optional pre-solving) by SMAC, cross-validating
    on the training data. Here it is trained on each leave-one-dataset-out
    fold through tools/autofolio/af_run.py in its own Python 3.10 environment.
    Its internal cross-validation folds are whole DATASETS, as in the outer
    loop. The budget per fold is ``wallclock`` seconds of SMAC.
    """

    def __init__(self, wallclock=60, objective="runtime", seed=12345):
        self.wallclock = wallclock
        self.objective = objective
        self.seed = seed
        self.name = "AutoFolio (SMAC, %ds/fold)" % wallclock

    def fit(self, train, cols):
        import subprocess
        import tempfile
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tools", "autofolio")
        self.py_ = os.path.join(root, ".venv", "bin", "python")
        self.script_ = os.path.join(root, "af_run.py")
        self.dir_ = tempfile.mkdtemp(prefix="af_")
        t = add_par10(train)
        wide = t.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                             values="par10", aggfunc="min")
        # AutoFolio needs a complete matrix: a missing (instance, algorithm)
        # is scored as a timeout.
        wide = wide.fillna(CUTOFF * PAR_FACTOR)
        feats = (t.drop_duplicates(subset=["dataset", "param_value"])
                  .set_index(["dataset", "param_value"])[cols]).reindex(wide.index)
        names = ["%s@%r" % (d, p) for d, p in wide.index]
        wide.index = feats.index = names
        feats = feats.fillna(feats.median())
        ds = sorted({n.split("@")[0] for n in names})
        fold = {d: 1 + i % 10 for i, d in enumerate(ds)}
        cv = pd.DataFrame({"fold": [fold[n.split("@")[0]] for n in names]}, index=names)
        self.cols_ = cols
        self.fill_ = feats.median()
        self.order_ = t.groupby("algorithm").par10.mean().sort_values().index.tolist()
        paths = {k: os.path.join(self.dir_, k + ".csv") for k in ("perf", "feats", "cv")}
        wide.to_csv(paths["perf"])
        feats.to_csv(paths["feats"])
        cv.to_csv(paths["cv"])
        self.model_ = os.path.join(self.dir_, "model.pkl")
        obj = "runtime" if self.objective == "runtime" else "solution_quality"
        subprocess.run([self.py_, self.script_, "fit", paths["perf"], paths["feats"],
                        paths["cv"], obj, str(CUTOFF), str(self.wallclock), str(self.seed),
                        self.model_], check=True, capture_output=True, text=True)
        self.cache_ = {}
        return self

    def prepare(self, X):
        """Predict a batch of feature rows in one AutoFolio call."""
        import json
        import subprocess
        X = np.asarray(X, float)
        f = pd.DataFrame(X, columns=self.cols_, index=["q%d" % i for i in range(len(X))])
        f = f.fillna(self.fill_)
        fp, out = os.path.join(self.dir_, "q.csv"), os.path.join(self.dir_, "q.json")
        f.to_csv(fp)
        subprocess.run([self.py_, self.script_, "predict", self.model_, fp, out],
                       check=True, capture_output=True, text=True)
        pred = json.load(open(out))
        for i, row in enumerate(X):
            self.cache_[tuple(np.round(row, 12))] = pred.get("q%d" % i)

    def select(self, x, candidates):
        key = tuple(np.round(np.asarray(x, float), 12))
        if key not in self.cache_:
            self.prepare([x])
        a = self.cache_.get(key)
        if a in candidates:
            return a
        for b in self.order_:
            if b in candidates:
                return b
        return candidates[0]


class RandomSelector(Selector):
    """Uniform random pick: the floor a selector has to clear to mean anything.

    Reported because "beats the single best fixed choice" and "better than
    guessing" are different claims, and on a portfolio where one algorithm
    dominates the second is much easier than the first. Seeded per instance from
    the feature vector so the result is reproducible across runs.
    """
    name = "random pick"

    def __init__(self, random_state=0):
        self.random_state = random_state

    def fit(self, train, cols):
        self.cols_ = cols
        return self

    def select(self, x, candidates):
        h = hash((self.random_state, tuple(np.round(np.asarray(x, float), 6))))
        return candidates[h % len(candidates)]


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
