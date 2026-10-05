# Confirmation on unseen data: the memory probe

Written and committed before any run on these datasets.

## Why a confirmation

The probe's memory result (`PROBE_PROTOCOL.md`, `probe_eval_output.txt`)
passed P1 only with the affine extrapolation, which was added after one
smoke-test instance. A result that depends on a choice made after looking at
data needs fresh data before it is relied on. This is that test.

## Data

The five SPMF transactional datasets that the memory screen admitted to no
extension -- chainstore (itemset form), fruithut, instacart (train), skin,
T20I6D100K -- normalised as in `results/memory_screen_prepare.txt`. They were
screened (two thresholds, five miners) but never benchmarked in full, never
used in training, and never probed. They were *not* selected for memory
disagreement: at screening all miners were within 1.3x or 10 MB of one
another, so on memory they represent ordinary data, and large probe gains
are not expected. Non-inferiority is therefore the primary question.

Benchmark: `tools/bench_real_extra.py --datasets chainstore_fim fruithut
instacart skin t20i6d100k --out results/real_extra3_summary.csv
--no-calibration --cap-reachable` (22 instances, 9 miners, 3,600 s, 2 workers).

## Frozen under test

- engine: `Recommender()` on `results/training_runs.csv` as of commit
  5f2467a (17 transactional datasets, none of these five);
- probe: `recommender/probe.py` as of commit ced9dc7, affine extrapolation
  (log-log also reported);
- decision rule: native costs from the probe, JVM costs from the engine,
  lowest eligible cost wins (as in `tools/probe_eval.py`).

## Criteria

On the memory objective, instances where every eligible miner completed,
geometric-mean regret against the lowest measured cost:

- **Q1 (primary, non-inferiority):** probe regret at most 1.05 x the engine's.
- **Q2 (superiority):** probe regret below the engine's with cluster-
  bootstrap P(better) >= 0.95 over the five datasets (expected to be weak
  on data not selected for memory differences).
- **Q3 (accuracy replicates):** on sampled instances, the probe's median
  |log10 error| of full-size memory is below the engine's for each of the
  four native miners.
- **Q4 (budget answers):** for budgets of 25, 50, 100, 200 and 500 MB, the
  share of (instance, native miner) pairs whose "fits within the budget"
  answer is correct is higher with the probe's estimate than with the
  engine's.

Runtime is not tested: the probe is not used for runtime requests. On the 17
training datasets no threshold on the engine's predicted runtime made
probing pay once its own time was charged (exploration, not registered:
probing only when the prediction was at least 0.5, 1 or 2 s gave 2.52x,
1.85x, 1.44x against the engine's 1.19x).
