# Ranking quantiles on exact memory: results

Protocol: `RANKQ_PROTOCOL.md` (2ef6ff6). Post hoc on the baseline
comparison's instances. Script `tools/rankq_eval.py`; rows in
`rankq_rows.csv`; output in `rankq_output.txt`.

## The new quantiles (90%, pooled over runs)

| kind | old (polled, 17 datasets) | exact |
|---|---|---|
| model memory | x0.249 .. x5.44 (794 runs) | x0.118 .. x5.86 (2,744 runs, 75 datasets) |
| probe memory, measured | x0.946 .. x1.032 (237) | x0.963 .. x1.040 (882, 63) |
| probe memory, sampled | x0.377 .. x1.067 (147) | x0.637 .. x1.140 (344, 24) |

Probe runtime is unchanged: the exact pool has no probe runtime estimate.

## Effect on the picks: none

No pick changed on any of the 335 instances (90 datasets), for any
objective (memory, balanced, runtime), with or without the probe, and with
either engine (the comparison's, trained on 17 datasets; the deployed one,
trained on 81, on PRIMARY).

| PRIMARY (fresh7 + fresh8, 119 instances) | old | new |
|---|---|---|
| memory, probe | 1.030x | 1.030x |
| balanced, probe | 1.185x | 1.185x |
| memory, no probe | 2.023x | 2.023x |
| runtime | 1.220x | 1.220x |

The swap does act, but it changes scores and not orders. A sanity check
moved Pascal's score from 58.89 to 59.37 on one instance, with the order
unchanged. On one instance the probed miners share one kind of interval, so
their ratios cancel. Only probed miners against model-predicted ones can
change places, and there the gaps are far larger than the move from x5.44
to x5.86.

## Decision

The new quantiles are adopted (`python -m recommender.intervals
--ranking-exact`): they are no worse and add no failed pick. No PRIMARY
pick changed, so the confirmed results (baseline comparison, FRESH7, FRESH8)
stand for the adopted ranking, and no fresh confirmation is needed.
