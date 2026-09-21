"""Formal specification of a generator-mining request.

This is the interface between the three layers:

    natural language  --Layer 1-->  MiningTask  --Layer 2-->  eligible set
                                                --Layer 3-->  ranked set

A ``MiningTask`` records what the user actually wants, separating the
*semantic* requirements (which pattern family, which reporting conventions)
from the *operational* ones (time and memory budget, objective).  The
separation is the point: the semantic fields are hard constraints that no
amount of speed can compensate for, while the operational fields define the
ranking among implementations that already satisfy them.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional

# Pattern families an implementation can be asked for.  These are the families
# determined empirically in the audit, not the ones claimed by algorithm names.
FAMILIES = (
    "minimal_generator",        # support-minimal itemsets
    "disjunction_free",         # strictly smaller than the generators
    "sequential_generator",     # support-minimal sequential patterns
    "generator_closure_pairs",  # generator + closure of each equivalence class
    "closed_itemset",
    "high_utility_generator",   # support-minimal AND u(X) >= theta
    "ghui",                     # support-minimal AND u(closure(X)) >= theta
    "utility_minimal",          # minimal w.r.t. utility, NOT w.r.t. support
    "minimal_rare_itemset",     # maximum-support (rare) region
)

DATA_TYPES = ("transactional", "sequential", "utility", "graph")

# How strict the caller is about verified correctness.
#   verified_only  : refuse anything not checked against an independent oracle
#   allow_unvalidated : accept unvalidated implementations, but say so
#   allow_defective   : accept even implementations with known violations
TRUST_LEVELS = ("verified_only", "allow_unvalidated", "allow_defective")

OBJECTIVES = ("runtime", "memory", "balanced")


@dataclass
class MiningTask:
    """A fully specified generator-mining request."""

    # --- semantic requirements (hard constraints) -------------------------
    data_type: str = "transactional"
    family: str = "minimal_generator"
    #: 'floor' keeps patterns whose support equals floor(sigma*|D|);
    #: 'ceil' requires support >= ceil(sigma*|D|); 'any' = caller does not care.
    boundary: str = "any"
    #: True  = the empty pattern must be present in the output
    #: False = the empty pattern must be absent
    #: None  = caller does not care
    include_empty: Optional[bool] = None
    trust: str = "verified_only"
    #: Accept an implementation that emits a superset recoverable by a
    #: documented post-filter (e.g. GHUI-Miner -> HUG output).
    allow_post_filter: bool = True

    # --- the instance -----------------------------------------------------
    dataset: Optional[str] = None       # named benchmark dataset, or
    dataset_path: Optional[str] = None  # a path to mine meta-features from
    threshold: Optional[float] = None   # minsup / maxsup / min_utility

    # --- operational budget (soft constraints, drive the ranking) ---------
    max_runtime_s: Optional[float] = None
    max_memory_mb: Optional[float] = None
    objective: str = "balanced"

    def __post_init__(self):
        if self.data_type not in DATA_TYPES:
            raise ValueError("data_type must be one of %s" % (DATA_TYPES,))
        if self.family not in FAMILIES:
            raise ValueError("family must be one of %s" % (FAMILIES,))
        if self.boundary not in ("floor", "ceil", "any"):
            raise ValueError("boundary must be floor, ceil or any")
        if self.trust not in TRUST_LEVELS:
            raise ValueError("trust must be one of %s" % (TRUST_LEVELS,))
        if self.objective not in OBJECTIVES:
            raise ValueError("objective must be one of %s" % (OBJECTIVES,))

    def to_dict(self):
        return asdict(self)

    def describe(self):
        bits = ["%s %s" % (self.data_type, self.family)]
        if self.dataset:
            bits.append("on %s" % self.dataset)
        if self.threshold is not None:
            bits.append("at threshold %g" % self.threshold)
        if self.max_runtime_s:
            bits.append("<= %gs" % self.max_runtime_s)
        if self.max_memory_mb:
            bits.append("<= %gMB" % self.max_memory_mb)
        bits.append("[%s, optimise %s]" % (self.trust, self.objective))
        return ", ".join(bits)
