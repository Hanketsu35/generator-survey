"""The recommender: Layer 2 (semantics) gates Layer 3 (performance).

The ordering is the contribution.  A performance-first recommender -- which is
what the algorithm-selection literature builds -- will happily return an
implementation that runs fast because it is solving a smaller problem than the
one asked for (Gr-growth at k>=2), or one that returns non-minimal itemsets on
exactly the dataset requested (Talky-G on mushroom).  Here nothing reaches the
ranking stage until it has been shown to compute the requested family.
"""
import hashlib
import os
import pickle
from dataclasses import dataclass, field
from typing import List, Optional

from . import metafeatures as mf
from .capabilities import CapabilityDB
from . import intervals as _iv
from . import survival as _sv
from .perfmodel import PerformanceModel, load_runs, pareto_front


def installed_implementations():
    """ids whose program is present on this machine, per src/config.py.

    The recommender used to rank implementations without asking whether they
    could run. Asked for exact association rules on Linux, it recommended
    FGC-Stream -- the only implementation the capability base credits with that
    family, and a Windows-only binary the repository cannot redistribute --
    with no hint that it was not there. ``available`` in the config is
    platform-aware for the native binaries; the SPMF implementations also need
    spmf.jar, which is checked here.

    Returns None when the harness config cannot be imported, meaning "unknown",
    so that the recommender still works outside this repository.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        import sys as _sys
        if root not in _sys.path:
            _sys.path.insert(0, root)
        from src import config as _cfg
    except Exception:                                   # noqa: BLE001
        return None
    jar = os.path.exists(os.path.join(root, "spmf", "spmf.jar"))
    out = set()
    for name, c in _cfg.ALGORITHMS.items():
        if not c.get("available"):
            continue
        if c.get("exe"):
            if os.path.exists(os.path.join(root, c["exe"])):
                out.add(name)
        elif jar:
            out.add(name)
    return out


#: share of the probe's native-miner scale applied to model estimates of the
#: other miners (0 = off); see Recommender._probe_scale. At 0.5 it cut the
#: JVM miners' median memory error from 0.248 to 0.213 (log10, LODO), left
#: every benchmarked pick unchanged, and stops FGC-Stream -- never measured
#: on the confirmation data -- from winning mooc_set on a guess of 109 MB:
#: scaled 915 MB; measured, it had reached 870 MB when stopped at 600 s
#: (results/DECISION_RULE_POSTHOC.md).
PROBE_SCALE_BETA = 0.5
#: interval of a miner stopped in its probe: "scaled" = the model interval
#: around the lower bound; "floor" = the model's own interval, raised to it.
#: "scaled" makes a stopped miner look far heavier than any guess and
#: raised regret (1.085x vs 1.042x post hoc); "floor" is used.
LB_INTERVAL = "floor"


@dataclass
class Recommendation:
    algorithm: str
    display: str
    match: str                      # exact | post_filter
    runtime_s: float
    memory_mb: float
    p_complete: float
    expected_cost: float
    score: float
    on_pareto_front: bool
    within_budget: bool
    prediction_source: str
    #: 5-95% bootstrap band on the expected cost, or None when the model could
    #: not supply one. Candidates whose bands overlap share a tier.
    cost_band: Optional[tuple] = None
    #: The same, on the composite score the ranking actually uses.
    score_band: Optional[tuple] = None
    #: 90% prediction intervals (recommender/intervals.py) on memory_mb and
    #: runtime_s: where the measured cost is expected to fall. cost_band and
    #: memory bands above describe the precision of the MEAN and are used only
    #: to form tiers; these describe the run the user will get.
    memory_interval: Optional[tuple] = None
    runtime_interval: Optional[tuple] = None
    #: 1 = best supported group. Within a tier the ordering is NOT supported by
    #: the data and must not be presented as a preference.
    tier: int = 1
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    budget_notes: List[str] = field(default_factory=list)
    post_filter: Optional[str] = None
    #: Whether this implementation's program is present on THIS machine. Kept
    #: separate from the ranking on purpose: the ranking is a statement about
    #: the implementations, installation a statement about the machine, and a
    #: user who can obtain the missing binary should still see where it ranks.
    installed: bool = True
    #: Ways this instance lies outside the data the implementation's costs were
    #: learned from; non-empty means runtime_s and memory_mb are extrapolations.
    extrapolated: List[str] = field(default_factory=list)


#: The structural features that bound where a prediction was learned. Size and
#: shape, not threshold: the threshold grid differs per dataset by design.
DOMAIN_FEATURES = (("log_n_tx", "records", True), ("log_n_items", "distinct items", True),
                   ("avg_len", "average transaction length", False),
                   ("density", "density", False))
#: Slack on each side of the observed range, in the feature's own units (log10
#: for the sizes: 0.3 is a factor of 2). A prediction a factor of two beyond the
#: largest training dataset is still an interpolation of the trend; one at a
#: tenth of the smallest is not.
DOMAIN_SLACK = {"log_n_tx": 0.3, "log_n_items": 0.3, "avg_len": 0.0, "density": 0.0}


_RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "results")
#: What the engine learns from by default: the published table plus the five
#: extension datasets, with every short run re-measured
#: (tools/build_training_table.py). The published experiments keep reading
#: summary.csv through perfmodel.load_runs(), and so stay reproducible.
TRAINING_TABLE = os.path.join(_RESULTS, "training_runs.csv")
PUBLISHED_TABLE = os.path.join(_RESULTS, "summary.csv")


def default_training_table():
    return TRAINING_TABLE if os.path.exists(TRAINING_TABLE) else PUBLISHED_TABLE


class Recommender:
    #: Fitting the survival forests takes ~12 s, which is tolerable once and
    #: irritating on every CLI invocation. The fitted model is cached on disk
    #: and keyed by the content of the training table together with the
    #: settings that affect fitting, so a stale cache cannot survive a change
    #: to either. Only a model fitted on a table FILE is cached: rows passed in
    #: as `runs` have no file to key on, and keying them on the default table
    #: -- as this class once did -- would return a model fitted on other data.
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

    def __init__(self, runs=None, capdb=None, exclude_dataset=None, cache=True,
                 table=None):
        self.db = capdb or CapabilityDB()
        if runs is None:
            self.table = table or default_training_table()
            self.runs = load_runs(self.table)
        else:
            self.table, self.runs, cache = None, runs, False
        self.excluded = exclude_dataset
        self.model = None
        if cache:
            self.model = self._load_cached(exclude_dataset)
        if self.model is None:
            self.model = PerformanceModel().fit(self.runs,
                                                exclude_dataset=exclude_dataset)
            if cache:
                self._store_cached(exclude_dataset, self.model)
        self._domain = self._training_domain()

    def _training_domain(self):
        """{algorithm: {feature: (min, max)}} over the datasets it was run on.

        Found necessary, not assumed: a 400-record, 10-item file uploaded to
        the chat interface got a predicted 1007 s for Zart, whose fastest
        recorded run is 0.45 s. The smallest training dataset has 3,196
        records; the forests had nothing to say about a file an eighth of
        that size and said it anyway.
        """
        runs = self.runs
        if self.excluded is not None:
            runs = runs[runs.dataset != self.excluded]
        cols = [f for f, _, _ in DOMAIN_FEATURES if f in runs.columns]
        out = {}
        for algo, g in runs.groupby("algorithm"):
            out[algo] = {f: (float(g[f].min()), float(g[f].max())) for f in cols}
        return out

    def outside_domain(self, algorithm, feats):
        """Plain-language reasons this instance is outside the training data."""
        rng = self._domain.get(algorithm) or {}
        out = []
        for f, name, is_log in DOMAIN_FEATURES:
            if f not in rng or f not in feats:
                continue
            lo, hi = rng[f]
            x, slack = feats[f], DOMAIN_SLACK.get(f, 0.0)
            if lo - slack <= x <= hi + slack:
                continue
            show = (lambda v: "{:,}".format(int(round(10 ** v)))) if is_log else (lambda v: "%.3g" % v)
            out.append("%s %s, trained on %s..%s" % (show(x), name, show(lo), show(hi)))
        return out

    # ------------------------------------------------------------------
    def _cache_key(self, exclude_dataset):
        h = hashlib.sha256()
        try:
            with open(self.table, "rb") as fh:
                h.update(fh.read())
        except OSError:
            return None
        h.update(repr(("v3-survival-timeouts-censored", exclude_dataset)).encode())
        return h.hexdigest()[:16]

    def _cache_path(self, exclude_dataset):
        key = self._cache_key(exclude_dataset)
        if key is None:
            return None
        return os.path.join(self.CACHE_DIR, "model_%s.pkl" % key)

    def _load_cached(self, exclude_dataset):
        p = self._cache_path(exclude_dataset)
        if not p or not os.path.exists(p):
            return None
        try:
            with open(p, "rb") as fh:
                return pickle.load(fh)
        except Exception:
            return None            # a stale or unreadable cache is not an error

    def _store_cached(self, exclude_dataset, model):
        p = self._cache_path(exclude_dataset)
        if not p:
            return
        try:
            os.makedirs(self.CACHE_DIR, exist_ok=True)
            with open(p, "wb") as fh:
                pickle.dump(model, fh)
        except Exception:
            pass                   # caching is an optimisation, never required

    # ------------------------------------------------------------------
    def _features(self, task):
        if task.dataset_path:
            return mf.extract(task.dataset_path, task.data_type)
        if task.dataset:
            return mf.for_dataset(task.dataset)
        raise ValueError("MiningTask needs either dataset or dataset_path")

    def _probe_scale(self, probe, feats, thr):
        """Median log10(probe / model) memory over the native miners, or 0.

        A miner that did not finish contributes its lower bound, so the
        scale is itself at least what the probe showed. 0 when fewer than two
        natives say anything.
        """
        import math
        r = []
        for a, c in probe.costs.items():
            v = c.get("memory_mb") if c.get("mode") != "failed" else c.get("memory_lb")
            p = self.model.predict(a, feats, thr)
            if v and p and p["memory_mb"] > 0:
                r.append(math.log10(max(v, 1e-3) / p["memory_mb"]))
        if len(r) < 2:
            return 0.0
        r.sort()
        return (r[len(r) // 2] + r[(len(r) - 1) // 2]) / 2.0

    # ------------------------------------------------------------------
    #: How each recorded empty-set condition is decided from the instance. Both
    #: read only the static meta-features and the requested threshold, so the
    #: prediction costs nothing.
    #:   no_full_support_item  Talky-G: emitted iff no item occurs in every
    #:                         transaction, i.e. max_sup_ratio < 1.
    #:   some_item_frequent    Zart: emitted iff at least one item reaches the
    #:                         threshold, i.e. max_sup_ratio >= sigma.
    EMPTY_SET_CONDITIONS = {
        "no_full_support_item": (lambda f, t: f.get("max_sup_ratio", 0.0) < 1.0,
                                 "max item support ratio is %.4f"),
        "some_item_frequent": (lambda f, t: t is not None
                               and f.get("max_sup_ratio", 0.0) >= t,
                               "max item support ratio is %.4f against the threshold"),
    }

    def _resolve_input_dependent(self, verdict, feats, threshold=None):
        """Turn an input-dependent convention into a concrete prediction.

        The condition is read from the implementation's own capability record.
        This used to apply Talky-G's rule to ANY input-dependent implementation,
        which was harmless while Talky-G and its diffset twin were the only ones.
        Zart's convention, once measured correctly, is also input-dependent --
        but on a different condition, and Talky-G's rule would have predicted
        the opposite of what Zart does on mushroom.
        """
        conv = self.db.impls.get(verdict.algorithm, {}).get("conventions", {})
        cond = self.EMPTY_SET_CONDITIONS.get(conv.get("empty_set_condition"))
        out = []
        for w in verdict.warnings:
            if w.startswith("empty-set output is INPUT-DEPENDENT") and cond:
                test, what = cond
                emitted = test(feats, threshold)
                out.append(
                    "empty-set convention resolved for this instance: %s, so the "
                    "empty set will %s"
                    % (what % feats.get("max_sup_ratio", float("nan")),
                       "be emitted" if emitted else "NOT be emitted"))
            else:
                out.append(w)
        return out

    # ------------------------------------------------------------------
    @staticmethod
    def should_probe(task):
        """Whether a subsample probe is worth its cost for this request.

        Decided by the pre-registered evaluation (results/PROBE_PROTOCOL.md,
        results/probe_eval_output.txt): on memory, the probe beat the model
        (1.073x against 1.282x regret, P1 passed with the amended affine
        extrapolation); on runtime it lost badly once its own wall-clock time
        was charged (6.29x against 1.19x, P3 failed), because where the best
        miner takes milliseconds the probe's 0.35 s median dominates. So:
        memory requests on a transactional file, and nothing else.
        """
        return (task.objective == "memory" and task.data_type == "transactional"
                and bool(task.dataset_path) and task.threshold is not None)

    def recommend(self, task, top=None, probe=None):
        """Rank the eligible implementations for `task`.

        ``probe``: a recommender.probe.ProbeResult for this task's file and
        threshold. Where it costs a native miner -- measured on the full
        database, or extrapolated from samples -- those costs replace the
        model's for that miner, and the miner is not flagged as outside the
        training domain, since nothing about it was learned from other data.
        """
        feats = self._features(task)
        eligible, rejected = self.db.filter(task)
        installed = installed_implementations()

        thr = task.threshold if task.threshold is not None else 0.1
        k_scale = self._probe_scale(probe, feats, thr) if probe is not None else 0.0
        rows = []
        for v in eligible:
            pred = self.model.predict(v.algorithm, feats, thr)
            model_mem = pred["memory_mb"] if pred else None
            if pred is None:
                continue
            probed = False
            pc = (probe.costs.get(v.algorithm) if probe is not None else None) or {}
            kind = ("model", "")
            probe_note = None
            if pc.get("mode") == "failed":
                # A probe that ran out of time is a measurement too: a lower
                # bound on the runtime (on the full file directly; on a sample,
                # a fortiori on the full file). The model's runtime is replaced
                # by it when lower; its memory estimate stays, flagged.
                from .probe import DIRECT_TIMEOUT, SAMPLE_TIMEOUT
                floor = DIRECT_TIMEOUT if probe.mode == "direct" else SAMPLE_TIMEOUT
                probe_note = ("did not finish the probe on your file (%s, %d s): expect "
                              "it to be heavy here; its memory estimate is the model's"
                              % ("full file" if probe.mode == "direct" else "a sample",
                                 floor))
                if pred["runtime_s"] < floor:
                    pred = dict(pred, runtime_s=float(floor))
                # ... and what it had used when it stopped is a lower bound on
                # its memory (the cap itself when it ran out of memory)
                lb = pc.get("memory_lb") or 0.0
                if lb > pred["memory_mb"]:
                    pred = dict(pred, memory_mb=float(lb))
                if lb:
                    probe_note += ("; it had reached %.0f MB when stopped (%s), so it "
                                   "needs at least that" % (lb, pc.get("why", "stopped")))
            if pc.get("memory_mb") is not None:
                m, t = pc["memory_mb"], pc["runtime_s"]
                # Bands from the probe's measured accuracy: median |log10|
                # error 0.02-0.04 on memory and 0.06-0.08 on runtime for
                # extrapolation; a direct measurement is repeatable to ~5%.
                mf_, rf_ = (1.05, 1.1) if pc["mode"] == "measured" else (1.1, 1.2)
                pred = dict(pred, memory_mb=m, runtime_s=t, p_complete=1.0,
                            expected_par10=None,
                            source="probe-%s" % pc["mode"],
                            memory_band=(m, m / mf_, m * mf_),
                            cost_band=(t, t / rf_, t * rf_))
                probed = True
                kind = ("probe", "_measured" if pc["mode"] == "measured" else "_sampled")
            lb = pc.get("memory_lb") if pc.get("mode") == "failed" else None
            if kind[0] == "model" and k_scale and not lb:
                # the probe measured how far off the model is on THIS file for
                # the native miners; move the other estimates part of the way
                pred = dict(pred, memory_mb=pred["memory_mb"] * 10 ** (PROBE_SCALE_BETA * k_scale))
            mem_iv = _iv.interval("%s_memory%s" % kind, pred["memory_mb"])
            if mem_iv and lb:
                hi = (_iv.interval("model_memory", model_mem)[1] if LB_INTERVAL == "floor"
                      else mem_iv[1])
                mem_iv = (max(mem_iv[0], lb), max(hi, lb))
            # The probe's runtime interval undercovered on unseen data (0.83,
            # INTERVAL_RESULTS.md), so it is not offered as a 90% interval.
            rt_iv = (None if kind[0] == "probe"
                     else _iv.interval("%s_runtime%s" % kind, pred["runtime_s"]))
            notes = []
            ok = True
            if task.max_runtime_s and pred["runtime_s"] > task.max_runtime_s:
                ok = False
                notes.append("predicted %.1fs exceeds the %.0fs budget"
                             % (pred["runtime_s"], task.max_runtime_s))
            if task.max_memory_mb and pred["memory_mb"] > task.max_memory_mb:
                ok = False
                notes.append("predicted %.0fMB exceeds the %.0fMB budget"
                             % (pred["memory_mb"], task.max_memory_mb))
            if pred["p_complete"] < 0.6:
                notes.append("predicted completion probability only %.0f%%"
                             % (100 * pred["p_complete"]))
            rows.append({
                "verdict": v,
                "runtime_s": pred["runtime_s"],
                "memory_mb": pred["memory_mb"],
                "p_complete": pred["p_complete"],
                "source": pred["source"],
                "cost_band": pred.get("cost_band"),
                "memory_band": pred.get("memory_band"),
                "expected_cost": PerformanceModel.expected_cost(pred),
                "within_budget": ok,
                "budget_notes": notes,
                "probed": probed,
                "memory_interval": mem_iv,
                "runtime_interval": rt_iv,
                "probe_note": probe_note,
            })

        if not rows:
            return [], rejected, feats

        # (Pareto flags are computed on the sorted list, below.)

        # --- scoring -----------------------------------------------------
        # The objective term uses the RAW predicted cost, and the risk of not
        # finishing is applied once, uniformly, as a multiplier. Folding the
        # PAR10 penalty into the runtime term instead would leave the memory
        # objective blind to completion -- which ranks an implementation with a
        # 6% chance of finishing first, because it fails cheaply.
        #
        # Memory enters at the UPPER end of its 90% interval. With every
        # estimate from the model this is a common factor and changes nothing;
        # with a probe it stops a model guess (22x wide) from beating a
        # measurement (1.1x wide) by being optimistic -- on mooc it picked
        # Pascal at a guessed 252 MB over measured 512 MB, and Pascal timed
        # out (results/HARD_RESULTS.md; the rule's effect, found after that
        # test: results/DECISION_RULE_POSTHOC.md).
        def _mem(r):
            iv = r.get("memory_interval")
            return iv[1] if iv else r["memory_mb"]
        rt_min = min(r["runtime_s"] for r in rows) or 1.0
        mm_min = min(_mem(r) for r in rows) or 1.0
        for r in rows:
            nr = r["runtime_s"] / rt_min
            nm = _mem(r) / mm_min
            if task.objective == "runtime":
                s = nr
            elif task.objective == "memory":
                s = nm
            else:
                s = (nr * nm) ** 0.5
            s /= max(r["p_complete"], 0.01)
            # A predicted budget violation is a hard demotion, not a tiebreak.
            r["score"] = s * (1.0 if r["within_budget"] else 1e6)

            # Uncertainty on the SCORE. The ranking is by score, so a tier
            # computed from the runtime band alone would contradict it -- as it
            # did: Gr-growth landed in tier 1 on a balanced score while a
            # cheaper FP-growth sat in tier 2. Propagate the relative width of
            # whichever bands feed this objective, with the exponent the
            # objective actually applies (balanced takes a square root, so it
            # halves the relative width).
            rel = []
            cb, mb = r.get("cost_band"), r.get("memory_band")
            if task.objective in ("runtime", "balanced") and cb and cb[0] > 0:
                rel.append(((cb[1] / cb[0]), (cb[2] / cb[0])))
            if task.objective in ("memory", "balanced") and mb and mb[0] > 0:
                rel.append(((mb[1] / mb[0]), (mb[2] / mb[0])))
            if rel:
                expo = 0.5 if task.objective == "balanced" and len(rel) == 2 else 1.0
                lo = hi = 1.0
                for a, b in rel:
                    lo *= a ** expo
                    hi *= b ** expo
                r["score_band"] = (r["score"], r["score"] * lo, r["score"] * hi)
            else:
                r["score_band"] = None

        rows.sort(key=lambda r: (r["score"], r["expected_cost"]))

        out = []
        for i, r in enumerate(rows):
            v = r["verdict"]
            out.append(Recommendation(
                algorithm=v.algorithm, display=v.display, match=v.match,
                runtime_s=r["runtime_s"], memory_mb=r["memory_mb"],
                p_complete=r["p_complete"], expected_cost=r["expected_cost"],
                score=r["score"],
                on_pareto_front=False,   # recomputed on the sorted list below
                within_budget=r["within_budget"],
                prediction_source=r["source"],
                cost_band=r.get("cost_band"),
                score_band=r.get("score_band"),
                reasons=list(v.reasons),
                warnings=(self._resolve_input_dependent(v, feats, task.threshold)
                          + ([r["probe_note"]] if r.get("probe_note") else [])),
                memory_interval=r.get("memory_interval"),
                runtime_interval=r.get("runtime_interval"),
                budget_notes=r["budget_notes"],
                post_filter=v.post_filter,
                installed=(True if installed is None
                           else v.algorithm in installed),
                extrapolated=([] if r.get("probed") else self.outside_domain(v.algorithm, feats)),
            ))
        # Recompute the Pareto flags on the sorted list (indices moved).
        front2 = set(pareto_front([{"runtime_s": o.runtime_s,
                                    "memory_mb": o.memory_mb} for o in out]))
        for i, o in enumerate(out):
            o.on_pareto_front = i in front2

        # --- equivalence tiers ------------------------------------------
        # Presenting a strict 1-2-3 ordering over candidates whose predicted
        # costs differ by hundredths of a second asserts a preference the data
        # does not support. Group candidates whose uncertainty bands overlap
        # the band of their tier's leader; within a tier, order is arbitrary.
        # Comparing against the LEADER rather than the previous entry stops a
        # chain of pairwise overlaps from merging everything into one tier.
        tier, leader = 1, None
        for o in out:
            if o.score_band is None:
                o.tier = tier                 # no band: keep it where it sits
                continue
            if leader is None:
                leader = o.score_band
            elif not _sv.indistinguishable(o.score_band, leader):
                tier += 1
                leader = o.score_band
            o.tier = tier

        return (out[:top] if top else out), rejected, feats


# ----------------------------------------------------------------------
def format_report(task, recs, rejected, feats, show_rejected=True):
    """Human-readable recommendation report."""
    L = []
    L.append("=" * 78)
    L.append("REQUEST: %s" % task.describe())
    L.append("=" * 78)
    L.append("")
    L.append("Instance meta-features:")
    L.append("  %d records, %d distinct items, density %.4f, support Gini %.3f, "
             "max item support %.3f"
             % (feats["n_tx"], feats["n_items"], feats["density"],
                feats["sup_gini"], feats["max_sup_ratio"]))
    L.append("")

    L.append("LAYER 2 - semantic eligibility: %d of %d implementations qualify"
             % (len(recs), len(recs) + len(rejected)))
    L.append("")
    if not recs:
        L.append("  NO implementation computes the requested family under the "
                 "requested conventions.")
    else:
        L.append("LAYER 3 - ranked by predicted %s" % task.objective)
        L.append("")
        hdr = ("%-4s %-26s %10s %10s %7s %12s %6s %s"
               % ("tier", "implementation", "runtime_s", "memory_MB", "P(fin)",
                  "PAR10_cost", "pareto", "match"))
        L.append(hdr)
        L.append("-" * len(hdr))
        prev_tier = None
        for r in recs:
            # A blank line between tiers, and the tier number only on its first
            # row: within a tier the order carries no information and should not
            # look like it does.
            if prev_tier is not None and r.tier != prev_tier:
                L.append("")
            label = "%d" % r.tier if r.tier != prev_tier else ""
            prev_tier = r.tier
            flag = "*" if r.on_pareto_front else " "
            bad = "" if r.within_budget else "  <-- OVER BUDGET"
            if not r.installed:
                bad += "  <-- NOT INSTALLED HERE"
            L.append("%-4s %-26s %10.2f %10.1f %6.0f%% %12.1f %6s %s%s"
                     % (label, r.display, r.runtime_s, r.memory_mb,
                        100 * r.p_complete, r.expected_cost, flag, r.match, bad))

        tier1 = [r for r in recs if r.tier == 1]
        if len(tier1) > 1:
            L.append("")
            L.append("  Tier 1 contains %d implementations whose predicted cost"
                     % len(tier1))
            L.append("  bands overlap: %s."
                     % ", ".join(r.display for r in tier1))
            L.append("  The data does not support preferring one over another")
            L.append("  here; choose on whatever else matters to you.")
        L.append("")
        top = recs[0]
        L.append("RECOMMENDED: %s%s"
                 % (top.display,
                    "  (tied with %d other%s)"
                    % (len(tier1) - 1, "s" if len(tier1) > 2 else "")
                    if len(tier1) > 1 else ""))
        if top.memory_interval:
            L.append("   memory: %.1f MB, 90%% prediction interval %.1f..%.1f MB"
                     % (top.memory_mb, top.memory_interval[0], top.memory_interval[1]))
        if top.runtime_interval:
            L.append("   runtime: %.2f s, 90%% prediction interval up to %.2f s"
                     % (top.runtime_s, top.runtime_interval[1]))
        if top.score_band:
            L.append("   ranking score %.3f, precision of the mean 5-95%% %.3f..%.3f"
                     % (top.score_band[0], top.score_band[1], top.score_band[2]))
        for s in top.reasons:
            L.append("   + %s" % s)
        for s in top.warnings:
            L.append("   ! %s" % s)
        for s in top.budget_notes:
            L.append("   ! %s" % s)
        if top.extrapolated:
            L.append("   ! predicted costs are EXTRAPOLATED -- this data is outside")
            L.append("     what the model was measured on: %s" % "; ".join(top.extrapolated))
        if top.post_filter:
            L.append("   > post-filter required: %s" % top.post_filter)
        if not top.installed:
            runnable = [r for r in recs if r.installed]
            L.append("")
            L.append("   ! %s is NOT INSTALLED on this machine." % top.display)
            if runnable:
                L.append("BEST YOU CAN RUN HERE: %s  (tier %d)"
                         % (runnable[0].display, runnable[0].tier))
            else:
                L.append("   ! None of the %d eligible implementations is installed"
                         % len(recs))
                L.append("     here. The request is answerable -- the ranking above")
                L.append("     says by what -- but not on this machine as it stands.")
        others = [r for r in recs[1:] if r.warnings]
        if others:
            L.append("")
            L.append("Caveats on the remaining eligible implementations:")
            for r in others:
                for s in r.warnings:
                    L.append("   ! %-22s %s" % (r.display + ":", s))

    if show_rejected and rejected:
        L.append("")
        L.append("EXCLUDED BY LAYER 2 (%d):" % len(rejected))
        for v in sorted(rejected, key=lambda v: v.algorithm):
            # Input-type mismatches are noise; report them compactly.
            if len(v.reasons) == 1 and "reads" in v.reasons[0]:
                continue
            L.append("   - %-26s %s" % (v.display, v.reasons[0] if v.reasons else ""))
            for extra in v.reasons[1:]:
                L.append("     %s" % extra)
        skipped = [v for v in rejected
                   if len(v.reasons) == 1 and "reads" in v.reasons[0]]
        if skipped:
            L.append("   (%d further implementations read a different input type)"
                     % len(skipped))
    L.append("")
    return "\n".join(L)
