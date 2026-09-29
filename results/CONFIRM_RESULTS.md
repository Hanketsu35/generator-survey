# Confirmation on unseen data: results

Protocol: `CONFIRM_PROTOCOL.md` (committed at bc5b8b5, before any run).
Scorer: `tools/confirm_eval.py` (frozen-input check passed). Full output:
`confirm_eval_output.txt`; truth: `real_extra3_summary.csv` (198 runs,
10.1 h, 2 workers); probes: `probe_points_confirm.csv` (run one at a time).

## Registered result

| | affine | log-log |
|---|---|---|
| memory regret, 14 instances / 5 datasets: engine | 1.000x | 1.000x |
| probe | 1.023x | 1.018x |
| Q1 non-inferiority (<= 1.05x engine) | PASS | PASS |
| Q2 superiority | FAIL (P=0.00) | FAIL (P=0.00) |
| Q3 accuracy, median abs log10 error, probe vs model | PASS (0.011-0.060 vs 0.173-0.247) | PASS (0.074-0.161 vs 0.173-0.247) |
| Q4 budget answers correct, overall | PASS (0.964 vs 0.850) | PASS (0.943 vs 0.850) |

On the 14 instances where every eligible miner completed, the engine picked
the lowest-memory miner every time, so the probe could not improve on it.
Its loss is fruithut: miners within a few MB of each other (13-30 MB), where
extrapolation noise swaps near-ties. Q2 failing was anticipated in the
protocol (these data were not selected for memory differences).

The affine variant, chosen on the training data after one smoke test,
replicates its accuracy advantage: its errors are 3-20x smaller than the
model's and 2-9x smaller than log-log's.

## Failures in the truth table

- Talky-G and TalkyG-Diffset: `OutOfMemoryError` at the default heap on every
  chainstore threshold (~8 GB, the JVM default of this machine).
- Pascal and Zart: 7 timeouts each (3,600 s) at the lowest thresholds.

## Exploratory (not registered): instances with a failed miner

The registered criterion drops the 9 instances where some miner failed.
These are the hardest thresholds, where the native miners differ most.
The same rule is applied there, choosing among the miners that completed
(affine):

| instance | engine | probe |
|---|---|---|
| instacart 0.000227 | Apriori 2.69x | Eclat 1.00x |
| instacart 0.000585 | Apriori 1.15x | Eclat 1.00x |
| chainstore 0.0000995 | Gr-growth 1.12x | Eclat 1.00x |
| chainstore 0.000224 | Gr-growth 1.03x | Eclat 1.00x |
| chainstore 0.000537 | Gr-growth 1.17x | Apriori 1.00x |
| other 4 | 1.00x | 1.00x |

This was looked at after the registered result. It is a reason to
pre-register the next test on hard thresholds; it is not evidence on its own.

## Decision

Keep the probe on memory requests, with the affine extrapolation: it is
non-inferior on ordinary data, more accurate, gives better budget answers,
and on hard instances it avoids the engine's worst picks.
