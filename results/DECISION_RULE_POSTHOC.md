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

## Second round: miners stopped in their probe, and the probe's scale

This is also post hoc, on the same seen data. `tools/decision_rule_variants.py`
runs the engine itself, with ProbeResults rebuilt from the recorded probe
points. Rows are in `decision_rule_variants.csv`.

What changed:
- **Lower bounds.** A native miner stopped in its probe (at the 60 s
  timeout, or at its memory cap) had already used a known amount of memory.
  That amount is a lower bound on its peak. `probe.py` now records it, and
  `probe_lower_bounds.csv` holds it for the 10 instances where a miner was
  stopped.
- **Scale.** The probe also measures how far off the model is on this file,
  as the median log10(probe / model) over the native miners. Half of that
  scale is applied to the model's estimates for the other miners
  (`PROBE_SCALE_BETA` = 0.5). On LODO this cut the JVM miners' median
  memory error from 0.248 to 0.213.

| rule | all 125 | failed picks | 5 instances with a stopped native |
|---|---|---|---|
| engine | 1.222 | 1 | 1.702 |
| upper end (first round) | 1.062 | 1 | 1.655 |
| + lower bound, model interval scaled around it | 1.085 | 2 | 2.815 |
| **+ lower bound, model interval raised to it ("floor")** | **1.042** | **0** | **1.044** |
| + lower bound (floor) + scale | 1.042 | 0 | 1.044 |

Adopted: floor and scale.

The scale changes no benchmarked pick. It is adopted for a miner that no
benchmark here includes: FGC-Stream, which is trained on 7 datasets only.
On mooc_set at 0.0003 the engine ranked FGC-Stream first on a model guess
of 109 MB, while every native miner the probe ran was above 2 GB. Measured
afterwards (`fgc_hard_check.csv`, 600 s cutoff), FGC-Stream did not finish,
and had reached 870 MB when stopped. With the scale its estimate is 920 MB
and it ranks fifth. Its other scaled estimates were 618 MB (mooc 0.00082,
measured >= 702 MB, stopped), 89 MB (liquor, measured 63) and 34 MB (sign,
measured 30). On all four hard instances the pick is now the lowest-memory
miner that completed.

Tried and rejected: separate conformal intervals inside and outside the
training domain (Mondrian). On the eight unseen datasets coverage fell from
0.881 to 0.805, and to 0.17 on skin. The out-of-domain residuals come from
four datasets and do not generalise, and mooc_set, where the model was off
100x, is not flagged as out of domain at all.
