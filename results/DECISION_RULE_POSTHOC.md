# Decision rule: point estimate vs interval upper end (post hoc)

**Not a confirmation.** This rule was found by looking at the
hard-threshold failures (`HARD_RESULTS.md`), and it is evaluated on data
already seen. There is no unseen data left locally to confirm it on.

The rule changed: when a probe runs, each miner's memory enters the ranking
at the upper end of its 90% interval (`INTERVAL_PROTOCOL.md`), not at its
point estimate. With no probe every estimate is the model's, the factor is
common to all miners, and the ranking does not change. With a probe, a model
guess (interval 21.9x wide) can no longer beat a measurement (1.1x wide) by
being optimistic.

`tools/decision_rule_posthoc.py`, rows in `decision_rule_posthoc.csv`.
Geometric-mean memory regret; a failed pick counts as 10.

| set | instances | engine | probe, point | probe, upper end |
|---|---|---|---|---|
| training LODO, all miners completed | 66 | 1.282 | 1.073 | 1.073 |
| training LODO, some miner failed | 31 | 1.086 | 1.082 | 1.007 |
| first confirmation, all completed | 14 | 1.000 | 1.023 | 1.023 |
| first confirmation, some failed | 8 | 1.197 | 1.000 | 1.000 |
| hard thresholds, all completed | 2 | 1.543 | 1.000 | 1.000 |
| hard thresholds, some failed | 4 | 2.577 | 3.162 | 1.778 |
| **all** | 125 | 1.222 | 1.101 | **1.062** |

Failed picks: engine 1, point rule 3, upper-end rule 1. The remaining failure
is mooc_set at 0.0003, where no native miner finished its probe and every
rule is left with the model's guesses.

The upper-end rule is never worse than the point rule, on any subset.

A second change, from the same instance: a native miner that does not finish
its probe is now reported as such. Its runtime is raised to at least the
probe's timeout, and a warning replaces silence. This changes what is
reported, not the ranking.
