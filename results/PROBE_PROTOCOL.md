# Subsample probe: what will be tested, fixed before any probe runs

Committed before `recommender/probe.py` has been run on any dataset.

## Why

On twelve, then seventeen, transactional datasets the engine ties the fixed
choice. Its one measured systematic miss is memory on large databases with
few distinct items (second extension, T3 failed at 2.58x): Gr-growth needs a
tenth of the post-filters' memory there, the post-filters need less on small
databases, and the static meta-features do not carry that crossover.

Two findings from the literature shape the remedy. Probing trajectories
(Renau & Hart, arXiv 2401.12745): short runs of the solvers themselves
describe an instance better than hand-designed features, and the probe run is
not wasted. Budget-limited selection from learning curves (Nguyen et al.,
arXiv 2410.07696): ranking at a small budget works only when the curves do not
cross -- and ours cross. So the probe must extrapolate how each miner scales
with database size, not rank the miners on a sample.

## The probe

For a transactional dataset of n transactions and a relative threshold sigma:

- sample sizes s1 = max(2,500, ceil(10 / sigma)), s2 = 4 s1, s3 = 16 s1 --
  the smallest keeps an absolute support of at least 10;
- if s3 > n / 2 the four native miners are run on the full database instead
  ("direct"), each with a 60 s timeout; a miner that does not finish is
  unknown to the probe;
- otherwise each native miner (Apriori, Eclat, FP-growth, Gr-growth) runs on
  uniform random samples (seed 0) of the three sizes at the same sigma, 20 s
  timeout each, and its peak memory and runtime are extrapolated to n by a
  log-log line through the two largest sizes, slope clipped to [0, 1.2] for
  memory and [0, 2] for runtime;
- the JVM miners are not probed; their costs come from the engine's model.

The probe's recommendation is the eligible implementation with the lowest
cost, native costs from the probe and JVM costs from the model; a native the
probe could not cost falls back to the model.

## Evaluation

Leave-one-dataset-out over the 17 transactional datasets of
`results/training_runs.csv` (as committed in 490be30); the model is refitted
without the held-out dataset each time. Instances and regret as in
`tools/remeasure_eval.py` M4: memory only where every eligible miner
completed; runtime with failures at 10 x 3,600 s.

Compared per objective: the engine (A), the probe (B), the fixed choice (C:
Apriori for memory, FP-growth for runtime), always-Gr-growth (D, reference).

**Runtime counts the probe.** B's runtime cost is the probe's own wall-clock
time plus the chosen miner's full runtime -- unless the chosen miner already
ran on the full database during a direct probe, in which case its result
exists and only the probe time counts.

## Criteria

- **P1 (primary)** memory: B's geometric-mean regret below A's, with the
  cluster-bootstrap probability (over held-out datasets, 2,000 resamples)
  of B being better at least 0.95.
- **P2** memory: B below C, same test.
- **P3** runtime, probe cost included: B's regret at most 1.10 times A's.

Also reported, not criteria: extrapolation accuracy (log10 absolute error of
the probe's native memory and runtime against the measured full-size values,
against the engine's own predictions for the same runs), probe wall-clock
cost, and results split by the second extension vs the other twelve.
