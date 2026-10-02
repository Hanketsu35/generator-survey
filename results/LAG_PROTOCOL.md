# Targeted confirmation: the progress rule where it acts

Written and committed before the screen ran.

## Why

`PROGRESS_DEMOTE` ranks a probed miner that finished fewer probe runs than
another after every miner not shown to be slow. It was found post hoc
(`PROGRESS_POSTHOC.md`). `FRESH3_RESULTS.md` could not test it, because no
miner lagged on any of its 13 instances. The rule acts only where one lags,
so this test selects such instances. The selection uses only the probe, which
the engine sees at decision time, and never the truth.

## Screen

Datasets: the 13 from the fresh confirmations, except census_kdd and
diabetes130, whose failures produced the rule:

poker, covertype, dota2, miniboone, power, uscensus, splice, fifa_set,
t25i10d10k, ecommerce_fim, microblog_set, msnbc_set, bike_set.

Their truth tables are at other thresholds. Here the screen goes below them,
to the sigma giving 50,000, 100,000 and 200,000 frequent pairs (the
extension calibration with `--cap-reachable`). Any instance whose sigma is
already in a truth table is skipped. Every grid instance is probed once and
kept (`probe_lag.jsonl`, `tools/lag_screen.py`).

## Selection (fixed here)

An instance qualifies when the four native miners' probe progress (finished
probe runs / probe runs) is not equal. Per dataset, at most the 2
qualifying instances with the highest sigma are taken, at most 14 in all,
in the dataset order above. The result is `lag_instances.csv`.

## Truth

`tools/bench_real_extra.py --instances results/lag_instances.csv --timeout
600 --extra-algos FGC_Stream --workers 2 --out results/lag_summary.csv`.

The cutoff is 600 s, as in every fresh confirmation. This favours the rule:
in the training table, where the cutoff is 3,600 s, its two losses were
slow miners that finished.

## Frozen

Everything frozen by `FRESH3_PROTOCOL.md`, at this commit: `engine.py`
(`PROGRESS_DEMOTE` = True), `probe.py`, `intervals.py` / `intervals.json`,
`perfmodel.py`, `training_runs.csv`.

## Criteria (memory objective; failed pick = 10)

D is the ranking as shipped; S is the same with `PROGRESS_DEMOTE` off. Both
use the stored probe of each instance.

- **L1 (primary):** geometric-mean regret D < S, and failed picks D <= S.
- **L2:** among instances where D and S differ, D is better on more than
  it is worse. Every changed pick is reported.
- If fewer than 4 instances qualify, the test is reported as underpowered,
  with no pass or fail.
