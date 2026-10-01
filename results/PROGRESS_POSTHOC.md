# Probe progress as a completion signal (post hoc)

**Not a confirmation.** This rule was found from the two failed picks in
`FRESH2_RESULTS.md` and is evaluated on data already seen. Its confirmation
is `FRESH3_PROTOCOL.md`.

The rule: a probed native miner that finished fewer of its probe runs than
another probed miner is ranked after every miner the probe did not show to be
slow. The engine flag is `PROGRESS_DEMOTE`. A probed miner's completion
probability had been taken as 1, even when it was the only one that could not
finish a 40,000-transaction sample in 20 s.

`tools/progress_posthoc.py`, rows in `progress_posthoc.csv`. Geometric-mean
memory regret; a failed pick counts as 10.

| set | n | engine | shipped | + progress |
|---|---|---|---|---|
| training LODO | 97 | 1.216 | 1.052 | 1.058 |
| first confirmation | 22 | 1.067 | 1.014 | 1.014 |
| hard thresholds | 6 | 2.172 | 1.000 | 1.000 |
| fresh | 33 | 1.132 | 1.074 | 1.074 |
| fresh2 | 15 | 1.514 | 1.359 | 1.000 |
| **all** | 173 | 1.227 | 1.073 | **1.048** |

Failed picks: engine 3, shipped 3, with progress 1.

Four picks change:

| instance | shipped | with progress |
|---|---|---|
| fresh2 census_kdd 0.0151 | Apriori, failed (10) | Gr-growth (1.00) |
| fresh2 diabetes130 0.213 | Apriori, failed (10) | Gr-growth (1.00) |
| training chess 0.2 | Apriori (1.14) | Gr-growth (1.63) |
| training pamap 0.045 | Apriori (1.00) | Gr-growth (1.25) |

In the two losses Apriori lagged in the probe, but finished within the
training table's 3,600 s cutoff. The rule gives up some memory for
completion, and only where the probe showed a miner to be the slow one.
