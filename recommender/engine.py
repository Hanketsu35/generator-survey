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
from .perfmodel import PerformanceModel, load_runs, pareto_front


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
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    budget_notes: List[str] = field(default_factory=list)
    post_filter: Optional[str] = None


class Recommender:
    #: Fitting the survival forests takes ~12 s, which is tolerable once and
    #: irritating on every CLI invocation. The fitted model is cached on disk
    #: and keyed by the content of summary.csv together with the settings that
    #: affect fitting, so a stale cache cannot survive a change to either.
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

    def __init__(self, runs=None, capdb=None, exclude_dataset=None, cache=True):
        self.db = capdb or CapabilityDB()
        self.runs = load_runs() if runs is None else runs
        self.excluded = exclude_dataset
        self.model = None
        if cache:
            self.model = self._load_cached(exclude_dataset)
        if self.model is None:
            self.model = PerformanceModel().fit(self.runs,
                                                exclude_dataset=exclude_dataset)
            if cache:
                self._store_cached(exclude_dataset, self.model)

    # ------------------------------------------------------------------
    def _cache_key(self, exclude_dataset):
        h = hashlib.sha256()
        summary = os.path.join(os.path.dirname(self.CACHE_DIR), "..",
                               "results", "summary.csv")
        try:
            with open(os.path.normpath(summary), "rb") as fh:
                h.update(fh.read())
        except OSError:
            return None
        h.update(repr(("v2-survival", exclude_dataset)).encode())
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

    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_input_dependent(verdict, feats):
        """Turn an input-dependent convention into a concrete prediction.

        Talky-G emits the empty set iff the dataset has no full-support item.
        That condition is exactly ``max_sup_ratio < 1``, which the meta-features
        already carry -- so a convention the audit could only describe as
        'input-dependent' becomes decidable for the instance at hand.
        """
        out = []
        for w in verdict.warnings:
            if w.startswith("empty-set output is INPUT-DEPENDENT"):
                full = feats.get("max_sup_ratio", 0.0) >= 1.0
                out.append(
                    "empty-set convention resolved for this dataset: "
                    "max item support ratio is %.4f, so the empty set will %s"
                    % (feats.get("max_sup_ratio", float("nan")),
                       "NOT be emitted" if full else "be emitted")
                )
            else:
                out.append(w)
        return out

    # ------------------------------------------------------------------
    def recommend(self, task, top=None):
        feats = self._features(task)
        eligible, rejected = self.db.filter(task)

        thr = task.threshold if task.threshold is not None else 0.1
        rows = []
        for v in eligible:
            pred = self.model.predict(v.algorithm, feats, thr)
            if pred is None:
                continue
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
                "expected_cost": PerformanceModel.expected_cost(pred),
                "within_budget": ok,
                "budget_notes": notes,
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
        rt_min = min(r["runtime_s"] for r in rows) or 1.0
        mm_min = min(r["memory_mb"] for r in rows) or 1.0
        for r in rows:
            nr = r["runtime_s"] / rt_min
            nm = r["memory_mb"] / mm_min
            if task.objective == "runtime":
                s = nr
            elif task.objective == "memory":
                s = nm
            else:
                s = (nr * nm) ** 0.5
            s /= max(r["p_complete"], 0.01)
            # A predicted budget violation is a hard demotion, not a tiebreak.
            r["score"] = s * (1.0 if r["within_budget"] else 1e6)

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
                reasons=list(v.reasons),
                warnings=self._resolve_input_dependent(v, feats),
                budget_notes=r["budget_notes"],
                post_filter=v.post_filter,
            ))
        # Recompute the Pareto flags on the sorted list (indices moved).
        front2 = set(pareto_front([{"runtime_s": o.runtime_s,
                                    "memory_mb": o.memory_mb} for o in out]))
        for i, o in enumerate(out):
            o.on_pareto_front = i in front2

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
               % ("rank", "implementation", "runtime_s", "memory_MB", "P(fin)",
                  "PAR10_cost", "pareto", "match"))
        L.append(hdr)
        L.append("-" * len(hdr))
        for i, r in enumerate(recs, 1):
            flag = "*" if r.on_pareto_front else " "
            bad = "" if r.within_budget else "  <-- OVER BUDGET"
            L.append("%-4d %-26s %10.2f %10.1f %6.0f%% %12.1f %6s %s%s"
                     % (i, r.display, r.runtime_s, r.memory_mb,
                        100 * r.p_complete, r.expected_cost, flag, r.match, bad))
        L.append("")
        top = recs[0]
        L.append("RECOMMENDED: %s" % top.display)
        for s in top.reasons:
            L.append("   + %s" % s)
        for s in top.warnings:
            L.append("   ! %s" % s)
        for s in top.budget_notes:
            L.append("   ! %s" % s)
        if top.post_filter:
            L.append("   > post-filter required: %s" % top.post_filter)
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
