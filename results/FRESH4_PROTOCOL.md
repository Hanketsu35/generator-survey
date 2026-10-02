# Fourth fresh confirmation: dataset-level prediction intervals

Written and committed before any miner or probe ran on these datasets.

## Why

The engine's intervals were calibrated by pooling runs, with a nominal 90%.
On unseen data they covered 79-88% (`INTERVAL_RESULTS.md`,
`FRESH_RESULTS.md`).

The literature explains why. With grouped data, here runs within datasets,
exchangeability holds between groups, not between runs. The guarantee a
user needs is about a new dataset, so calibration must happen at the level of
datasets. Dunn, Wasserman & Ramdas (JASA 2023, "Distribution-free prediction
sets for two-layer hierarchical models"):
- a finite-sample guarantee by subsampling one observation per group needs
  k >= 2/alpha - 1 groups: 19 for 90%, 39 for 95%;
- CDF pooling, which averages the per-group empirical CDFs, is
  asymptotically valid and is their recommendation when that is acceptable.

The first calibration had 17 groups. There are now 40 out-of-sample groups:
17 training datasets, leave-one-out, plus 23 benchmarked after training.
Leave-one-dataset-out over them (`tools/interval_methods.py`,
`tools/interval_groups_probe.py`), CDF pooling at a nominal 95% gave a mean
per-dataset coverage of:
- 0.942 for model memory;
- 0.939 for model runtime;
- 0.949 for the probe, measured;
- 0.943 for the probe, sampled.

The user wants at least 90%. The intervals shown are now these: 95%, CDF
pooling over 40 datasets (`intervals.build_display`). The ranking keeps its
own quantiles, which are unchanged and confirmed three times, so this change
moves no pick.

## Data

Ten UCI datasets, downloaded on 2026-10-02 after every earlier test was
scored. None is in any earlier table or related to one there; bank-full was
taken and its sibling bank-additional left out. Converted by one rule
(`tools/prepare_fresh4.py`, `fresh4_prepare.txt`):
- a numeric column with more than 16 distinct values goes into 5
  equal-frequency bins;
- every other column is nominal.

The datasets: adult, bank_full, nursery, letter, shuttle, krk, shoppers,
car, tictactoe, yearmsd (515,345 transactions, the one the probe samples).
That gives 38 instances at the extension levels, with ten implementations
and a 600 s cutoff:

`tools/bench_real_extra.py --datasets tictactoe car nursery shoppers letter
krk adult shuttle bank_full yearmsd --timeout 600 --extra-algos FGC_Stream
--no-calibration --cap-reachable --workers 2 --out results/fresh4_summary.csv`

Probes run afterwards, one instance at a time.

## Frozen (this commit)

`recommender/intervals.py`, `recommender/data/intervals.json`, `engine.py`,
`probe.py`, `perfmodel.py`, `training_runs.csv`.

## Criteria

Coverage is measured on what the engine shows: `Recommendation.
memory_interval` / `runtime_interval`, over every completed run of an
eligible implementation. It is averaged within each dataset and then over
datasets, the quantity the guarantee is about.

- **V1 (primary):** model memory interval (engine without probe): mean
  per-dataset coverage >= 0.90.
- **V2:** probe memory interval (probed native miners): mean per-dataset
  coverage >= 0.90.
- **V3:** model runtime interval (engine without probe): mean per-dataset
  coverage >= 0.90.

Also reported, not tested:
- coverage of the memory interval shown for model-estimated miners when a
  probe ran, which is scaled by the probe;
- the share of datasets at or above 0.95;
- the old ranking quantiles' coverage on the same runs;
- the widths.
