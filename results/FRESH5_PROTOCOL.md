# Fifth fresh confirmation: intervals with a dataset-level guarantee, on exact memory

Written and committed before any miner or probe ran on these datasets.

## What changed since FRESH4

`FRESH4_RESULTS.md` traced the memory intervals' failures to the measurement:
polled VmHWM could not measure runs of a few milliseconds, and read
end-of-run peaks 6-7% low. Since then:
- **Measurement.** Every run goes through `tools/peakrun` (exact
  `ru_maxrss` from `wait4`). Every table was re-measured, 1,999 runs, JVM
  runs as the median of three, since their peak varies by up to 24%
  (`results/exact/`). Every probe was re-run.
- **Training.** The engine trains on `results/exact/training_runs.csv`.
- **Calibration.** Intervals are calibrated over datasets with Dunn,
  Wasserman & Ramdas's subsampling (Method 2), which carries a finite-sample
  guarantee for a new dataset once there are at least 2/alpha - 1 datasets:
  - model memory and runtime at 95%, over 50 datasets;
  - probe memory, measured, at 90%, over 39 datasets;
  - probe memory, sampled, at 90%, over 23 datasets.

  Leave-one-dataset-out, the mean per-dataset coverage was 0.963 (model
  memory), 0.965 (model runtime), 0.967 (probe, measured) and 0.974 (probe,
  sampled).
- **Widths.** The model's 95% interval is about 800x wide; the probe's are
  1.1x (measured) and 3.1x (sampled).

## Data

Twelve datasets. None is in any earlier table or related to one there:
- eleven from SPMF's `uci_datasets.zip` (downloaded 2026-09-30, unused
  until now): anneal, breast_cancer, colic, credit_a, credit_g, hypothyroid,
  primary_tumor, soybean, vote, waveform_5000, segment. Excluded as copies
  or relatives: mushroom, kr-vs-kp, letter, splice, and sick (the same
  thyroid records as hypothyroid);
- SUSY (UCI, downloaded 2026-10-03, 5,000,000 rows), the one the probe
  samples.

Conversion follows the rule of `tools/prepare_fresh4.py`
(`tools/prepare_fresh5.py`, `fresh5_prepare.txt`). That gives 45 instances
at the extension levels, with ten implementations and a 600 s cutoff:

`tools/bench_real_extra.py --datasets breast_cancer primary_tumor colic vote
credit_a soybean anneal credit_g segment hypothyroid waveform_5000 susy
--timeout 600 --extra-algos FGC_Stream --no-calibration --cap-reachable
--workers 2 --out results/fresh5_summary.csv`

Probes run afterwards, one instance at a time.

## Frozen (this commit)

`engine.py`, `probe.py`, `intervals.py`, `data/intervals.json`,
`perfmodel.py`, `results/exact/training_runs.csv`.

## Criteria (mean per-dataset coverage of the intervals the engine shows)

Each bar is the interval's own guarantee:
- **W1 (primary):** probe memory interval (90%): coverage >= 0.90;
- **W2:** model memory interval (95%): coverage >= 0.95;
- **W3:** model runtime interval (95%): coverage >= 0.95.

Also reported, not tested:
- coverage per dataset, and how many datasets reach 0.95;
- the probe split into measured and sampled;
- widths.

With twelve datasets the mean has sampling error. A shortfall of a few
points on one criterion is reported as a fail, as registered.
