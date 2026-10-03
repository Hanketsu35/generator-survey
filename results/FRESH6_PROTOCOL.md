# Sixth fresh confirmation: median-centred, class-split runtime intervals

Written and committed before any miner or probe ran on these datasets.

## Why

The runtime interval undercovered in `FRESH5_RESULTS.md` (0.923 against
0.95). Every miss was from below: a slow JVM miner on a small dataset,
predicted at its timeout-inflated mean. `RUNTIME_INTERVAL_POSTHOC.md`:
- the interval is now centred on the survival median, and the engine
  reports that median as the typical runtime;
- the model's intervals are calibrated separately for native and JVM
  programs;
- leave-one-dataset-out gave 0.969 at a third of the width.

That analysis used FRESH5, so FRESH5 cannot confirm it.

## Data

The thirteen remaining UCI datasets of SPMF's `uci_datasets.zip`, never used:
audiology, autos, balance_scale, breast_w, diabetes, glass, heart_c,
ionosphere, lymph, sonar, vehicle, vowel, zoo. Excluded as relatives or too
small: heart-h, heart-statlog, the .ORIG variants, labor, iris. Converted by
`tools/prepare_fresh6.py` (`fresh6_prepare.txt`, same rule as FRESH4/5).
That gives 45 instances, with ten implementations and a 600 s cutoff:

`tools/bench_real_extra.py --datasets zoo lymph sonar autos glass audiology
heart_c ionosphere balance_scale breast_w diabetes vehicle vowel --timeout 600
--extra-algos FGC_Stream --no-calibration --cap-reachable --workers 2
--out results/fresh6_summary.csv`

## Frozen (this commit)

`engine.py`, `probe.py`, `intervals.py`, `data/intervals.json`,
`perfmodel.py`, `survival.py`, `results/exact/training_runs.csv`.

## Criteria (mean per-dataset coverage of the intervals the engine shows)

- **R1 (primary):** model runtime interval (95%): coverage >= 0.95.
- **R2:** model memory interval (95%): coverage >= 0.95.
- **R3:** probe memory interval (90%): coverage >= 0.90.
- **R4:** the typical runtime (median) is a better point estimate than the
  restricted mean: median |log10(true / estimate)| is lower over completed
  runs, both floored at 0.01 s.

All of these datasets are small (101-990 transactions), so the probe will
measure rather than sample, and many runs will be short. That condition is
where the FRESH5 misses occurred.
