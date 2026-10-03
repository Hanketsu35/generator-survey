# Training on every benchmarked dataset, and the intervals that follow (post hoc)

**Not a confirmation.** This was motivated by FRESH6's failures
(`FRESH6_RESULTS.md`), and FRESH5 and FRESH6 data are in the pools. Every
coverage figure below is leave-one-dataset-out, an honest estimate for a new
dataset under exchangeability between datasets, but chosen after seeing
these data. The confirmation is the next registered test.

## Changes

- **Training table.** `results/exact/training_all.csv`: the 22 training
  datasets plus every confirmation table, 81 datasets.
  `tools/build_training_all.py`. FGC-Stream is now seen on 57 datasets, not
  7.
- **Model intervals.** Residuals leave one of 75 datasets out of the model
  trained on the rest (`tools/interval_pool_all.py`). Calibration is
  subsampling (Dunn et al. 2023, Method 2) at 95%, separately for FGC-Stream,
  the other native programs, and the JVM programs. Runtime is centred on
  the survival median.
- **Probe intervals.** The probe pool now includes the 25 small datasets of
  FRESH5/6: 63 datasets measured, 24 sampled. With 63 datasets the measured
  interval can be calibrated at 95% (it needs 39); the sampled one stays at
  90%.

## Leave-one-dataset-out coverage

| interval | level | coverage | datasets >= level | lowest | median width |
|---|---|---|---|---|---|
| model runtime | 95% | 0.979 | 63/75 | 0.57 | x262,000 |
| model memory | 95% | 0.978 | 67/75 | 0.71 | x264 |
| probe memory, measured | 95% | 0.984 | 54/63 | 0.83 | x1.15 |
| probe memory, sampled | 90% | 0.974 | 22/23 | 0.82 | x3.1 |

Probe, measured, at 90% with the small datasets in the pool: 0.919, and 0.878
on the small ones. That was the shortfall FRESH5/6 saw. At 95% the small
ones reach 0.976.

Tried and rejected:
- residuals on log(x + c) to give small peaks an absolute margin: no gain
  for c = 0.25-2 MB;
- calibrating small and large estimates separately: no gain at 95%.

The model's runtime intervals remain enormous: a guaranteed 95% for a
dataset the model has not seen costs five orders of magnitude. The probe's
are what a user can act on.
