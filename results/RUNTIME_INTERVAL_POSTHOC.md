# Why the runtime interval undercovered, and what changed (post hoc)

**Not a confirmation.** This was found by looking at FRESH5's W3 shortfall
(`FRESH5_RESULTS.md`). The confirmation is `FRESH6_PROTOCOL.md`.

## Diagnosis

Of 332 completed runs, the 95% runtime interval missed 25, and **every miss
was from below**. All 25 were slow JVM miners or FGC-Stream on small
datasets (Zart 14, FGC-Stream 9, Pascal 2). For example, Zart on
breast_cancer was predicted at 1,114 s and ran 0.22 s.

The interval was centred on the survival model's restricted mean runtime.
That is the right input to an expected cost, and the ranking keeps it. But
for a miner with even a small chance of reaching the 3,600 s cutoff, that
chance times the cutoff dominates the mean, which says little about how long
a run typically takes.

## Change

- **Centre.** Runtime is now centred on the survival median
  (`survival.quantile_runtime`). The engine reports it as the typical
  runtime (`Recommendation.runtime_typical_s`); the UI and the report show
  it, and the ranking still uses the expected cost.
- **Split.** The model's intervals are calibrated separately for native and
  JVM programs, a Mondrian split with each side over about 50 datasets.
  Subsampling (Dunn et al. 2023, Method 2) is kept, at 95%.
- **Cutoff.** The upper end of the runtime interval is capped at the cutoff.

Leave-one-dataset-out over 50 datasets (exact memory pool), at 95%:

| | coverage (unseen) | lowest dataset | median width |
|---|---|---|---|
| runtime, mean-centred, one pool (was) | 0.965 (0.955) | 0.00 | x314,612 |
| runtime, median-centred, one pool | 0.972 (0.967) | 0.43 | x194,720 |
| runtime, median-centred, native/JVM | 0.969 (0.963) | 0.57 | x94,666 |
| memory, one pool (was) | 0.963 (0.953) | 0.14 | x810 |
| memory, native/JVM | 0.964 (0.962) | 0.29 | x536 |

The typical runtime error falls from a factor of 53 (median |log10| 1.73,
mean as the estimate) to 3.4 (0.53, median as the estimate). The intervals
stay very wide, which reflects the model: its runtime estimates are uncertain
by orders of magnitude on a dataset it has not seen.
