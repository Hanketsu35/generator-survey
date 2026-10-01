# Third fresh confirmation: probe progress as a completion signal

Written and committed before any miner or probe ran on these datasets.

## Why

`PROGRESS_POSTHOC.md`: on seen data, demoting a probed miner that finished
fewer probe runs than another one turned two failed picks into the best ones
(fresh2), cost two others, and lowered regret overall from 1.073x to 1.048x.
That data chose the rule; this tests it.

## Data

Three UCI datasets, downloaded on 2026-10-01 after `FRESH2_RESULTS.md` was
scored. All three are large enough for the probe to sample, and none is in
any earlier table or related to one there. Converted by
`tools/prepare_fresh3.py` (`fresh3_prepare.txt`):

| dataset | tx | items | conversion |
|---|---|---|---|
| dota2 (train) | 92,650 | 283 | 4 nominal columns; (hero, side) where nonzero |
| power (household) | 2,049,280 | 25 | 7 measurements in 5 bins; all-missing rows dropped |
| miniboone | 130,064 | 250 | 50 measurements in 5 bins, plus the class |

There are 13 instances, at the extension levels with `--cap-reachable`. Ten
implementations, with a 600 s cutoff:

`tools/bench_real_extra.py --datasets dota2 miniboone power --timeout 600
--extra-algos FGC_Stream --no-calibration --cap-reachable --workers 2
--out results/fresh3_summary.csv`

Probes run afterwards, one instance at a time (`tools/fresh3_eval.py
--probe`).

## Frozen (this commit)

`recommender/engine.py` (`PROGRESS_DEMOTE` = True), `probe.py`,
`intervals.py` / `intervals.json`, `perfmodel.py`, `training_runs.csv`.

## Criteria (memory objective; failed pick = 10)

Three rankings are compared: D, as shipped with the flag on; S, the same
with the flag off; and A, the engine without a probe.

- **P1 (primary):** D is not worse than S: geometric-mean regret D <= S,
  and failed picks D <= S.
- **P2:** D below A, with cluster-bootstrap P(better) >= 0.95. With three
  datasets this test is weak.
- **P3:** the probe's memory interval covers >= 0.85 of completed native runs.

The flag changes a pick only where a probed miner lags. If it changes none
here, P1 passes trivially and says nothing; the number of changed picks is
reported with the result.
