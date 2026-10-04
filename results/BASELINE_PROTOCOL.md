# Baseline comparison: standard algorithm selectors vs the recommender

Written and committed before the comparison was computed.

## Question

How does the recommender compare with the algorithm-selection methods a
reader of that literature expects? Two parts:
- **(a) Performance.** Every method chooses among the same semantically
  eligible implementations.
- **(b) Semantics.** Left unrestricted, how often do standard selectors
  choose an implementation that does not compute minimal generators under
  the requested conventions? This is what the recommender's Layer 2
  prevents.

## Methods

All are trained on the same data, `results/exact/training_runs.csv` (22
datasets, exact memory; the table the probe-backed ranking was frozen with):
- VBS (oracle) and SBS (single best);
- random;
- per-algorithm regression (an empirical performance model, SATzilla-07
  style);
- pairwise ranking (SATzilla-11 style);
- SUNNY (k-NN, k = 16);
- ISAC (k-means clusters);
- survival (Run2Survive, expected PAR10);
- **AutoFolio** (Lindauer et al. 2015), run as released, SMAC-tuned with a
  1,800 s budget per objective; its internal CV folds are whole datasets;
- the recommender without a probe (A);
- the recommender with its probe, as shipped (C).

Features for the learned selectors: the published static meta-features
plus log threshold.

## Test data

Every dataset benchmarked after the training table, with exact memory:
- confirm, hard, fresh, fresh2, fresh3, fresh4 (results/exact/);
- fresh5, fresh6, fresh7, fresh8.

Probes come from results/exact/probes.jsonl (re-run with exact memory) and
probe_fresh5..8.jsonl.

**Primary subset: FRESH7 and FRESH8** (32 OpenML datasets). The probe-backed
ranking was frozen before they were benchmarked, so they informed no design
decision for any method. The earlier sets are reported separately; some of
them shaped the recommender's rules.

## Metrics

- **Memory objective.** Geometric-mean regret against the lowest memory
  among eligible implementations that completed; a pick that failed counts
  as 10.
- **Runtime objective.** Geometric-mean regret against the fastest
  completed eligible implementation (runtimes floored at 0.01 s); a failed
  pick counts as 10.
- **Statistics.** Cluster-bootstrap 5-95% bands over datasets.
- **(b)** The share of instances where a selector restricted only to
  implementations that ran picks one that Layer 2 rejects for the requested
  task (transactional minimal generators, verified only).

No pass/fail criterion: this is a comparison, reported in full.
