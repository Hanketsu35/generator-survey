# Confirmation on hard thresholds: the memory probe

Written and committed before any miner ran on these datasets.

## Why

The first confirmation (`CONFIRM_RESULTS.md`) passed non-inferiority but its
registered criterion kept only instances where every miner completed. That
drops the hardest thresholds, and there, looked at afterwards, the engine
picked a miner using up to 2.69x the lowest memory while the probe picked the
lowest. That observation was made after the fact on the same five datasets,
so it is tested here on fresh data, with a criterion that keeps instances
where some miner fails.

## Data

Every dataset available locally that is in neither the training table
(`training_runs.csv` at 5f2467a) nor the first confirmation, and is not a
subset or sibling of one of them. Converted by `tools/prepare_hard.py` with
rules fixed before any run (`hard_prepare.txt`): utility databases keep the
item part, and sequence databases keep the set of items in each sequence.

| dataset | source | tx |
|---|---|---|
| liquor | SPMF liquor_11 (utility) | 52,131 |
| sign_set | SPMF SIGN (sequences) | 730 |
| eshop_set | SPMF e_shop (sequences) | 24,026 |
| mooc_set | SPMF MOOC (timestamped sequences) | 82,535 |

Excluded before any run:
- **Related data:** online_retail_II is the same shop as the training set
  onlineretail, chainstore_fixed is a subset of chainstore, and mushrooms is
  a copy of mushroom.
- **No hard level:** bible_set, leviathan_set and foodmart_fim have flat
  item supports (maximum 100, 44 and 20), so almost no pair reaches the
  minimum absolute support of 10. The level rule below yields no instance
  for them.

## Instances

The two hardest levels of the calibration used for extensions 1-3: the sigma
giving 5,000 and 20,000 frequent pairs (`--cap-reachable`). That gives
8 instances.

Benchmark: `tools/bench_real_extra.py --datasets sign_set liquor eshop_set
mooc_set --targets 5000 20000 --timeout 600 --no-calibration --cap-reachable
--workers 2 --out results/hard_summary.csv`, with 9 miners and 72 runs.

The cutoff is 600 s, not 3,600 s. A miner that does not finish in ten minutes
is treated as failed. For someone asking for the least memory, a miner that
never finishes is not an answer.

## Frozen under test

- engine: `Recommender()` on `training_runs.csv` at 5f2467a, with
  `recommender/engine.py` and `recommender/perfmodel.py` as of this commit;
- probe: `recommender/probe.py` at ced9dc7, affine (log-log also reported);
- decision rule as in the first confirmation: native costs from the probe,
  the rest from the engine, lowest eligible cost wins.

Probes run one at a time after the benchmark, with nothing else running.

## Criteria (memory objective)

Regret of a pick = its peak memory / the lowest peak memory among eligible
miners that completed. A pick that failed (timeout, error) gets regret 10.
The pick is made among all eligible miners, as the product does; it is not
restricted to those that completed.

- **H1 (primary, superiority):** geometric-mean probe regret below the
  engine's, with cluster-bootstrap P(better) >= 0.95 over the four datasets.
  With four clusters the bootstrap is coarse; the per-instance table is
  reported in full.
- **H2 (non-inferiority):** probe regret at most 1.05 x the engine's.
- **H3 (accuracy):** on sampled instances, the probe's median |log10 error|
  of full-size memory is below the engine's for each native miner that
  completed.
- **H4 (budget answers):** for budgets of 25, 50, 100, 200 and 500 MB, the
  share of correct "fits within the budget" answers over (instance, completed
  native miner) pairs is higher with the probe than with the engine.

Also reported, not tested: the same comparison with the pick restricted to
miners that completed (the exploratory rule of `CONFIRM_RESULTS.md`).
