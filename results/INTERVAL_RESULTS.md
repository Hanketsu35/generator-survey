# Prediction intervals: results

Protocol: `INTERVAL_PROTOCOL.md` (f6e8d66). Output: `interval_eval_output.txt`,
rows: `interval_eval_rows.csv`. There are 210 completed runs on 8 unseen
datasets; eshop_set had no completed run.

| | coverage (nominal 0.90) | bar | median width |
|---|---|---|---|
| old band (forest-mean bootstrap) | **0.048** | - | - |
| I1 model memory | 0.881 | >= 0.85 PASS | 21.9x |
| I2 probe memory | 0.991 (measured 0.982, sampled 1.000) | PASS | 1.09x |
| I3 model runtime | 0.890 | PASS | upper bound ~2x |
| I4 probe runtime | 0.833 | FAIL | |

Coverage per dataset for the model's memory interval is uneven: 1.00 on
five datasets, 0.61-0.65 on skin and sign, and 0 of 7 on mooc_set, where
the model was off by 100x. Pooled coverage holds, but it does not hold for
every dataset. The probe's memory interval is over-covering (0.99) and
could be narrower.

I4 fails. The truth runtimes were measured with two runs in parallel, and
the probe runs alone. That difference is a likely cause, but it was not
tested, and the interval stays as registered: it undercovers.

## Decision

- Replace the old band with the conformal interval for memory. The old band
  is a statement about the forest's mean, and it covered 5% of runs.
- Show runtime intervals from the model as an upper bound only.
- Show the probe's runtime interval with its measured coverage (83%), not
  as a 90% interval.
