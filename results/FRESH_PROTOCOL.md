# Fresh confirmation: the probe-backed memory ranking as shipped

Written and committed before the benchmark ran on these datasets.

**Disclosure.** Before this commit, and to check that probe results
serialise, the probe was run once on bike_set at sigma 0.001459, the
5,000-pair level. Its native memory values were seen: 8-25 MB, all four
measured directly. No truth run was made or seen. Also seen: the datasets'
size statistics and the level plan (`bench_real_extra.py --plan`).

## Why

The rule the engine now uses on memory requests was assembled after the
registered tests had been scored, on data that had been seen:
- the upper end of the 90% interval;
- the lower bounds from miners stopped in their probe;
- the probe's scale applied to the model's other estimates.

`DECISION_RULE_POSTHOC.md` says it is not a confirmation. This is the
confirmation, on data downloaded afterwards for the purpose.

## Data

Eight datasets from the SPMF repository, downloaded on 2026-09-30. None is
in the training table, in either earlier confirmation, or a subset, copy or
sibling of a dataset there. Excluded as related:
- UCI mushroom (copy of mushroom) and kr-vs-kp (the source of chess);
- Kosarak10k/25k (subsets of kosarak);
- liquor_5/15 (siblings of liquor);
- online_retail_II and kosarak_sequences.

Converted by `tools/prepare_fresh.py` (`fresh_prepare.txt`):

| dataset | kind | tx | items |
|---|---|---|---|
| uscensus | census attributes | 1,000,000 | 316 |
| t25i10d10k | IBM synthetic | 9,976 | 929 |
| fifa_set | sequences -> sets | 20,450 | 2,990 |
| bike_set | sequences -> sets | 21,078 | 67 |
| msnbc_set | sequences -> sets | 31,790 | 17 |
| microblog_set | sequences -> sets | 429 | 50,505 |
| ecommerce_fim | items of timestamped baskets | 14,975 | 3,468 |
| splice | UCI, one item per (attribute, value) | 3,190 | 290 |

## Instances and truth

Every level of the extension calibration (10 to 20,000 frequent pairs,
`--cap-reachable`) gives 37 instances. Ten implementations run: the nine
benchmarked so far plus FGC-Stream, which the ranking can pick and which no
earlier truth table included. The cutoff is 600 s, and a miner that does not
finish counts as failed.

`tools/bench_real_extra.py --datasets microblog_set splice msnbc_set
bike_set t25i10d10k ecommerce_fim fifa_set uscensus --timeout 600
--extra-algos FGC_Stream --no-calibration --cap-reachable --workers 2
--out results/fresh_summary.csv`

Probes run after the benchmark, one instance at a time, with nothing else
running (`tools/fresh_eval.py --probe`).

## Frozen under test (this commit)

- `recommender/engine.py`: `PROBE_SCALE_BETA` = 0.5, `LB_INTERVAL` = "floor";
- `recommender/probe.py`: concurrent, with lower bounds;
- `recommender/intervals.py` and `recommender/data/intervals.json`;
- `recommender/perfmodel.py`;
- `results/training_runs.csv`.

## Rules compared (memory objective)

- **A, engine:** `Recommender().recommend(task)`, no probe.
- **B, registered probe rule:** the rule of `PROBE_PROTOCOL.md` and both
  earlier confirmations. Native costs come from the probe and the rest from
  the engine, and the lowest point estimate wins.
- **C, as shipped:** `Recommender().recommend(task, probe=...)`.

The pick is the first eligible implementation in the rule's order. Regret is
the pick's peak memory divided by the lowest among eligible miners that
completed. A pick that failed counts as 10. Instances where no eligible miner
completed are dropped.

## Criteria

- **F1 (primary):** C below A in geometric-mean regret, with cluster-
  bootstrap P(better) >= 0.95 over the datasets.
- **F2:** C at most 1.02 x B.
- **F3:** C makes no more failed picks than A, and no more than B.
- **F4:** 90% interval coverage on completed runs is at least 0.85 for the
  model's memory interval (every eligible miner), and at least 0.85 for the
  probe's memory interval (native miners).
