# Sixth fresh confirmation: results

Protocol: `FRESH6_PROTOCOL.md` (c6029de). Truth: `fresh6_summary.csv` (450
runs, 1.7 h: 14 timeouts, 5 errors). Probes: `probe_fresh6.jsonl`. Output:
`fresh6_eval_output.txt`; rows: `fresh6_eval_rows.csv`. That is 13 small
datasets (101-990 transactions).

## Registered result

| criterion | result |
|---|---|
| R1 model runtime interval (95%) | **FAIL**: 0.853; 1 of 13 datasets >= 0.95 |
| R2 model memory interval (95%) | PASS: 0.950 |
| R3 probe memory interval (90%) | **FAIL**: 0.867 |
| R4 typical (median) vs mean runtime as estimate | PASS: median abs log10 error 0.945 vs 2.435 |

The median is a much better runtime estimate, but the interval around it
undercovered on these datasets, more than on FRESH5.

## Why

The runtime interval missed 50 of 345 runs, 47 of them from below. Most
were FGC-Stream, predicted at 35-3,600 s for runs of 0.01-1.2 s; a few
were Zart and Apriori. FGC-Stream is in the training table on seven
datasets only: the original transactional seven, dense or large, where it is
slow. The model generalises that slowness to every small dataset.

FGC-Stream shares the "native" calibration class with the Borgelt miners and
Gr-growth, whose errors are far smaller, so the interval is too narrow for
it. The three misses from above are the native miners on audiology at
sigma 0.95 (226 transactions, 70 attributes), 40-72 s against a predicted
0.06 s.

The cause is the model's training data, not the interval method. 33
datasets benchmarked after training, FGC-Stream on 25 of them, are not in
the training table.

R3's misses are again the smallest datasets. Peaks there are about 3 MB,
and the probe's +/-5% band is narrower than the run-to-run difference of a
few pages (`FRESH5_RESULTS.md`).
