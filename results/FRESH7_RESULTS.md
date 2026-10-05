# Seventh fresh confirmation: results

Protocol: `FRESH7_PROTOCOL.md` (a46c8b8). Truth: `fresh7_summary.csv` (920
runs, 7.7 h: 67 timeouts, 11 errors), measured exactly. Probes:
`probe_fresh7.jsonl`. Output: `fresh7_eval_output.txt`; rows:
`fresh7_eval_rows.csv`. The data are 24 OpenML-CC18 datasets, selected by
rule.

## Registered result: all criteria met

| criterion | level | mean per-dataset coverage | datasets >= 0.95 | lowest | median width | result |
|---|---|---|---|---|---|---|
| X1 model runtime | 95% | 0.980 | 19/24 | 0.85 | x42,083 | **PASS** |
| X2 model memory | 95% | 0.991 | 22/24 | 0.84 | x2,800 | **PASS** |
| X3 probe memory, measured | 95% | 0.954 | 13/23 | 0.83 | x1.15 | **PASS** |
| X4 probe memory, sampled | 90% | 1.000 (1 dataset) | - | - | - | reported only (fewer than 3 sampled) |

Not tested: as a runtime estimate, the median beats the restricted mean
again, with median |log10 error| 0.827 against 2.264.

## What it means

On 24 datasets that no design decision saw, every interval the engine shows
met its guarantee:
- **Probe, measured.** 95%, about +/-7% around a value measured on the
  user's file. This is the interval to act on.
- **Model.** 95% for both runtime and memory, but very wide: the model knows
  little about a dataset it has not seen, and the interval says so.

This closes the line that started with FRESH4.
- FRESH4: polled memory, run-pooled calibration; memory intervals 0.76-0.85
  against 90-95%.
- FRESH5: exact measurement, dataset-level subsampling; memory met, runtime
  missed.
- FRESH6: median-centred runtime; still missed, traced to the training data.
- FRESH7: all-data training, a separate class for FGC-Stream, and 95% for
  the probe; everything met.

The sampled probe's 90% interval was exercised on one dataset only (numerai,
96k transactions); its support stays leave-one-dataset-out (0.974 over 24)
and FRESH5 (SUSY, 1.000).
