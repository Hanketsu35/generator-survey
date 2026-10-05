# Eighth fresh confirmation: results

Protocol: `FRESH8_PROTOCOL.md` (e918d4e). Truth: `fresh8_summary.csv` (310
runs, 5.0 h: 51 timeouts, 17 errors). Probes: `probe_fresh8.jsonl`. Output:
`fresh8_eval_output.txt`; rows: `fresh8_eval_rows.csv`. The data are 8 large
OpenML datasets (100,968-1,496,391 transactions), selected by rule, and the
probe sampled at every level.

## Registered result: all criteria met

| criterion | level | mean per-dataset coverage | datasets >= 0.95 | lowest | median width | result |
|---|---|---|---|---|---|---|
| Y1 probe memory, sampled (primary) | 90% | 0.954 | 5/8 | 0.80 | x3.04 | **PASS** |
| Y2 model runtime | 95% | 1.000 | 8/8 | 1.00 | x42,083 | **PASS** |
| Y3 model memory | 95% | 1.000 | 8/8 | 1.00 | x2,800 | **PASS** |
| Y4 probe memory, measured | 95% | - | - | - | - | no measured values (every instance sampled) |

Not tested: as a runtime estimate, the median beats the restricted mean, with
median |log10 error| 0.487 against 1.240.

## What it means

The probe's interval for values it extrapolates from samples, the one
left open by FRESH7, held at 0.954 against its 90% guarantee on eight large
datasets no design decision saw. Its width is about x3: the price of
extrapolating from at most 16 x 2,500 transactions to up to 1.5 million.

With FRESH7 (24 datasets) and FRESH8 (8 datasets), every interval the engine
shows has now met its registered guarantee on data selected by rule from
OpenML.
