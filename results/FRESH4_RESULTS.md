# Fourth fresh confirmation: results

Protocol: `FRESH4_PROTOCOL.md` (fee62e9). Truth: `fresh4_summary.csv`
(380 runs, 4.1 h: 40 timeouts, 1 error). Probes: `probe_fresh4.jsonl`.
Output: `fresh4_eval_output.txt`; rows: `fresh4_eval_rows.csv`.

## Registered result (nominal 95%, mean per-dataset coverage, bar 0.90)

| | new (dataset-level) | old quantiles, same runs | result |
|---|---|---|---|
| V1 model memory | 0.853 | 0.696 | **FAIL** |
| V2 probe memory | 0.755 | 0.728 | **FAIL** |
| V3 model runtime | 0.934 | 0.854 | PASS |
| scaled model memory (not tested) | 1.000 | 1.000 | |

The dataset-level calibration raised coverage everywhere: model memory
from 0.70 to 0.85, runtime from 0.85 to 0.93. Two of the three registered
criteria still fail.

## Why they fail

**Car and tic-tac-toe (1,728 and 958 transactions).** Every native run takes
5-10 ms. At that length the memory reading is not a measurement, in the
truth run or in the probe. The same 3 MB binary on the same input reads
anywhere from 0.5 to 2.9 MB from one run to the next. The probe's interval
covered 25% there and the model's 50%. This is the sampler floor already
documented for the harness (`src/metrics.py`, `peak_rss_mb`).

Exploratory, not registered: counting only runs that took at least 0.05 s,
model memory covers 0.925 (10 datasets). The probe covers 0.849 (5
datasets) and 0.780 at 0.1 s or more.

**The probe above the floor.** On bank_full at sigma 0.00196 the probe read
Gr-growth at 67.5 MB and the truth run at 81.6 MB; Eclat read 127 and 139.
These are the same deterministic program on the same input, 0.9-1.2 s
runs, 10-20% apart. The probe's measured interval (x0.95-x1.05) was
calibrated on runs where the two readings agreed. It is too narrow for this
spread.

Both failures point at the measurement, not at the estimate. VmHWM is read
by polling, up to 0.1 s apart after the first quarter second. A peak
reached in the last interval before exit is missed, and a run shorter than
the first reading is not measured at all.
