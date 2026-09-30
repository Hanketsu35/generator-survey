# Prediction intervals for cost estimates

Written and committed before the intervals were checked on the test data.

## The problem (measured on training data)

The engine shows a "5-95%" band on memory. It is a bootstrap of the forest's
mean, not a prediction interval. Held out one dataset at a time over the 17
training datasets (`tools/interval_residuals.py`, 794 completed runs), it
contained the measured memory in **8.3%** of runs. The per-tree spread is
uncorrelated with the actual error (r = -0.006), so it cannot be rescaled
into an interval (normalised conformal was tried and gave no gain).

## Method (fixed here)

`recommender/intervals.py`, quantiles in `recommender/data/intervals.json`
(both frozen at this commit): split-conformal intervals on
log10(truth / prediction), alpha = 0.10, quantile level tightened by k/(k+1)
for k calibration datasets. There is one pooled residual distribution per
kind. Runtimes are floored at 0.01 s on both sides.

| kind | calibration | 90% interval |
|---|---|---|
| model memory | 794 LODO residuals, 17 datasets | x0.249 .. x5.441 (width 21.9x) |
| model runtime | same | x0.000 .. x2.018 (upper bound only, in effect) |
| probe memory, measured | 237, 14 datasets | x0.946 .. x1.032 (1.1x) |
| probe memory, sampled (affine) | 147, 9 datasets | x0.377 .. x1.067 (2.8x) |
| probe runtime, measured | 237 | x0.870 .. x1.121 |
| probe runtime, sampled | 147 | x0.555 .. x1.873 |

Variants compared on the training data by nested LODO before this choice
(exploratory): per-algorithm, native/JVM, prediction-size bins, dataset
weighting, and normalisation by forest spread. None was clearly better than
the pooled one on coverage; per-algorithm undercovered (0.84-0.85). The
simplest was kept.

## Test data

The nine datasets that neither the model nor the calibration saw: the five
of the first confirmation (`real_extra3_summary.csv`) and the four of the
hard-threshold confirmation (`hard_summary.csv`, running at the time of
writing). Every completed run of an algorithm the model predicts is
included. Probe estimates come from `probe_points_confirm.csv` and
`probe_points_hard.csv` (affine).

## Criteria (coverage of 90% intervals, pooled over runs)

- **I1 (primary):** model memory interval coverage >= 0.85.
- **I2:** probe memory interval coverage (measured and sampled) >= 0.85.
- **I3:** model runtime interval coverage >= 0.85.
- **I4:** probe runtime interval coverage >= 0.85.

Also reported: the old band's coverage on the same runs, per-dataset
coverage (runs within a dataset are correlated, so the pooled share
overstates precision), and median widths.
