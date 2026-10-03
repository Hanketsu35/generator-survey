# Fifth fresh confirmation: results

Protocol: `FRESH5_PROTOCOL.md` (83d66a5). Truth: `fresh5_summary.csv` (450
runs, 3.6 h: 32 timeouts, 1 error), measured exactly through `tools/peakrun`.
Probes: `probe_fresh5.jsonl`. Output: `fresh5_eval_output.txt`; rows:
`fresh5_eval_rows.csv`. That is 12 datasets.

## Registered result (mean per-dataset coverage; each bar is the interval's guarantee)

| | level | coverage | bar | result | datasets >= 0.95 | median width |
|---|---|---|---|---|---|---|
| W1 probe memory | 90% | 0.908 | 0.90 | **PASS** | 4/12 | x1.10 |
| W2 model memory | 95% | 0.950 | 0.95 | **PASS** | 7/12 | x797 |
| W3 model runtime | 95% | 0.923 | 0.95 | **FAIL** | 4/12 | very wide |

The probe split: measured 0.900 (11 datasets); sampled 1.000 (SUSY only).

## What it means

On exact memory, both memory intervals met their guarantees on data that no
design decision had seen.
- The probe's interval is the useful one: x1.1 wide, at least 90%.
- The model's is honest but wide: x800 at 95%.

The comparison with FRESH4 (0.755 probe, 0.853 model, on polled memory)
shows what the measurement had cost.

The runtime interval fell short: 0.923 against 0.95, with five datasets
between 0.83 and 0.88. The interval was calibrated on runtimes measured with
two runs in parallel on 50 datasets, and so is the truth here; why it
undercovers was not investigated before this result. It stays as
registered: a 95% label it did not earn here. The engine shows runtime
intervals only for the model's estimates, and only as an upper end.

The probe's misses (15 of 163 measured runs) are on the smallest datasets
(anneal, breast_cancer, colic: 286-898 transactions). Peaks there are about
3 MB, and the interval's +/-5% is +/-0.15 MB, less than the run-to-run
difference of a few pages. Not changed here.
