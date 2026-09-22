"""Layer 2 - semantic capability matching.

Every published algorithm-selection framework (Rice's, SATzilla-style
empirical hardness models, AutoML portfolio methods) assumes the candidate
algorithms are semantically interchangeable and selects among them on a
performance metric.  In generator mining that assumption is false: the audit
in ``tools/validate_*.py`` established that of 17 executable implementations,
one returns a different pattern family than its name states, one silently
switches family on an undocumented parameter, and two return itemsets that
fail the definition their own source paper gives -- on data-dependent
configurations.

This module therefore runs BEFORE any performance model.  It answers "which
implementations actually compute what was asked for?", and refuses the rest
with a citable reason.  It is a knowledge base plus a constraint check, not a
learned model: every claim it makes is traceable to an oracle measurement
recorded in ``data/capabilities.json``.
"""
import json
import os
from dataclasses import dataclass
from typing import List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_HERE, "data", "capabilities.json")


@dataclass
class Verdict:
    """Why one implementation was accepted or rejected for a task."""
    algorithm: str
    display: str
    eligible: bool
    match: str                    # exact | post_filter | rejected
    reasons: List[str]            # human-readable, each traceable to evidence
    warnings: List[str]
    post_filter: Optional[str] = None
    #: configurations where this implementation is known to be defective and
    #: which overlap the requested instance
    defect_hit: Optional[dict] = None


class CapabilityDB:
    def __init__(self, path=_DB_PATH):
        with open(path, encoding="utf-8") as fh:
            self.raw = json.load(fh)
        self.impls = {d["id"]: d for d in self.raw["implementations"]}
        self.relation = self.raw["family_relation"]
        self.post_filters = self.raw["post_filters"]

    # ------------------------------------------------------------------
    def ids(self):
        return list(self.impls)

    def get(self, algo):
        return self.impls[algo]

    def family_match(self, emitted, requested):
        """exact | post_filter | no -- how `emitted` can serve `requested`."""
        return self.relation.get(emitted, {}).get(requested, "no")

    # ------------------------------------------------------------------
    def _defect_for(self, impl, task):
        """Return the recorded defect entry if it covers the requested instance.

        A defect that is recorded for specific (dataset, threshold) pairs is
        reported as a *hit* only when the request names one of them.  On any
        other instance the defect is still reported as a warning, because the
        audit covered a subset of configurations and absence of a recorded
        failure is not evidence of correctness.
        """
        snd = impl.get("soundness", {})
        configs = snd.get("defective_configs")
        if not configs or task.dataset is None:
            return None
        for c in configs:
            if c["dataset"] != task.dataset:
                continue
            if task.threshold is None or abs(c["param_value"] - task.threshold) < 1e-12:
                return c
        return None

    # ------------------------------------------------------------------
    def evaluate(self, algo, task) -> Verdict:
        impl = self.impls[algo]
        reasons, warnings = [], []
        display = impl["display"]

        # --- 1. input type ------------------------------------------------
        # 'utility' data is transactional data carrying utilities; a plain
        # transactional miner cannot read it, but the converse also fails
        # because a utility miner needs the utility columns.
        if impl["input_type"] != task.data_type:
            return Verdict(algo, display, False, "rejected",
                           ["reads %s data, request is %s"
                            % (impl["input_type"], task.data_type)], [])

        # --- 2. pattern family -------------------------------------------
        # An implementation may emit more than one family: Zart prints each
        # closed set together with its generators. The primary family is the one
        # the benchmark measured it on; ``also_emits`` lists further families,
        # each admitted ONLY with its own oracle evidence -- being documented as
        # producing a family is not enough, which is the lesson of
        # HUCI-Miner-Generators. The best-matching family serves the request,
        # so adding a secondary family can widen what an implementation serves
        # but never changes how it serves a request its primary family already
        # matched.
        emitted = impl["emits"]["family"]
        match = self.family_match(emitted, task.family)
        via_secondary = None
        rank = {"exact": 0, "post_filter": 1, "no": 2}
        for extra in impl.get("also_emits", []):
            m = self.family_match(extra["family"], task.family)
            if rank[m] < rank[match]:
                emitted, match, via_secondary = extra["family"], m, extra
        if match == "no":
            emitted = impl["emits"]["family"]
            snd = impl.get("soundness", {})
            reasons.append("emits the %s family, not %s" % (emitted, task.family))
            # Only a *misnamed* implementation needs the extra explanation; for
            # an honestly-named one (Arima mines rare itemsets) the family
            # mismatch is self-explanatory and the soundness note is unrelated.
            if snd.get("status") == "different_family":
                if snd.get("summary"):
                    reasons.append(snd["summary"])
                if snd.get("evidence"):
                    reasons.append("evidence: %s" % snd["evidence"])
                if snd.get("consequence"):
                    reasons.append(snd["consequence"])
            return Verdict(algo, display, False, "rejected", reasons, warnings)

        pf = None
        if match == "post_filter":
            if not task.allow_post_filter:
                return Verdict(algo, display, False, "rejected",
                               ["emits %s; %s is recoverable only by a post-filter, "
                                "which the request disallows" % (emitted, task.family)], [])
            key = "%s->%s" % (emitted, task.family)
            pf = self.post_filters.get(key, "documented post-filter")
            warnings.append("requires a post-filter: %s" % pf)

        # --- 3. conditional completeness (Gr-growth's k) -------------------
        comp = impl.get("completeness", {})
        if comp.get("status") == "conditional":
            cond = impl["emits"].get("conditional_on", {})
            cond_s = ", ".join("%s=%s" % kv for kv in cond.items())
            warnings.append("valid ONLY with %s -- %s" % (cond_s, comp.get("hazard", "")))
        elif comp.get("status") == "boundary_dependent":
            warnings.append(comp.get("hazard", "output depends on the threshold boundary"))
        elif comp.get("status") == "unvalidated":
            warnings.append("completeness was not verified against an oracle")

        # --- 4. soundness / trust ----------------------------------------
        snd = impl.get("soundness", {})
        status = snd.get("status")
        defect_hit = None

        if status == "defective":
            defect_hit = self._defect_for(impl, task)
            msg = "%s (%s)" % (snd.get("summary", "returns non-conforming patterns"),
                               snd.get("scope", "scope unrecorded"))
            if defect_hit:
                msg = ("KNOWN DEFECTIVE on exactly this configuration: %s at %g "
                       "returns %d non-minimal itemsets"
                       % (defect_hit["dataset"], defect_hit["param_value"],
                          defect_hit["extra"]))
            if task.trust != "allow_defective":
                reasons.append(msg)
                if snd.get("evidence"):
                    reasons.append("evidence: %s" % snd["evidence"])
                return Verdict(algo, display, False, "rejected", reasons, warnings,
                               defect_hit=defect_hit)
            warnings.append(msg)

        elif status == "unvalidated":
            msg = snd.get("summary", "not checked against an independent oracle")
            if task.trust == "verified_only":
                return Verdict(algo, display, False, "rejected",
                               ["output was never validated: %s" % msg], warnings)
            warnings.append("unvalidated output: %s" % msg)

        elif status == "different_family":
            # Already caught by the family relation, but keep the guard: a
            # request for exactly this family must still surface the caveat.
            warnings.append(snd.get("consequence", ""))

        # --- 5. reporting conventions ------------------------------------
        conv = impl.get("conventions", {})
        b = conv.get("threshold_boundary", "unknown")
        if task.boundary != "any":
            if b == "unknown":
                warnings.append("threshold boundary convention was not determined; "
                                "output may differ by patterns sitting exactly on "
                                "the rounded threshold")
            elif b != task.boundary:
                reasons.append("uses the %s threshold boundary, request requires %s "
                               "-- patterns whose support equals the rounded "
                               "threshold will differ" % (b, task.boundary))
                if conv.get("boundary_evidence"):
                    reasons.append("evidence: %s" % conv["boundary_evidence"])
                return Verdict(algo, display, False, "rejected", reasons, warnings)

        e = conv.get("empty_set", "unknown")
        if task.include_empty is not None:
            if e == "input_dependent":
                warnings.append("empty-set output is INPUT-DEPENDENT: %s"
                                % conv.get("empty_set_rule", ""))
            elif e == "always" and task.include_empty is False:
                warnings.append("always emits the empty set; strip it (offset of one)")
            elif e == "never" and task.include_empty is True:
                warnings.append("never emits the empty set; add it manually "
                                "(support |D|, a generator by definition)")

        if via_secondary is not None:
            reasons.append("also emits %s, verified by %s"
                           % (emitted, via_secondary.get("evidence", "oracle")))
        elif match == "exact":
            reasons.append("emits %s, verified by %s"
                           % (emitted, impl.get("validation", {}).get("oracle", "oracle")))
        return Verdict(algo, display, True, match, reasons, warnings, post_filter=pf,
                       defect_hit=defect_hit)

    # ------------------------------------------------------------------
    def filter(self, task):
        """Return (eligible verdicts, rejected verdicts) for a MiningTask."""
        verdicts = [self.evaluate(a, task) for a in self.impls]
        return ([v for v in verdicts if v.eligible],
                [v for v in verdicts if not v.eligible])
