# Second fresh confirmation: Gr-growth's memory extrapolation, on large data

Written and committed before any miner or probe ran on these datasets.

## Why

In `FRESH_RESULTS.md` one of the two losses on uscensus came from the probe's
affine line, which put Gr-growth at 221 MB for a true 79 MB. On every sampled
instance seen so far (211 instance-miner pairs, 15 datasets) the affine line
is the best form for the three Borgelt miners. For Gr-growth it overshoots
whenever n is far above the largest sample.

Gr-growth holds a fixed hash map plus a prefix tree of the frequent items,
and that tree grows sublinearly. The new form is

  memory(n) = F + (m3 - F) * (n / s3)^k,

with k from the two largest sample sizes, clipped to [0, 1]. F is taken from
the source, not fitted: the pattern map is 1,299,709 pointers (9.9 MiB,
`PatternSet.h`) on top of the 3.9 MiB the binary takes when nothing is
frequent, so F = 13.8 MiB (or the smallest sample reading, if lower).

On the seen data, excluding readings under 2 MB (the sampler's floor for
very short runs), the median |log10 error| for Gr-growth was 0.005, against
0.015 for affine, and the 90th percentile 0.109 against 0.204. That data
chose the form, so it is not evidence for it. This test is.

## Data

Four UCI datasets, downloaded on 2026-10-01, after `FRESH_RESULTS.md`. They
are large enough that the probe samples them (n > 80,000), and none is in
any earlier table or related to one there. Conversion
(`tools/prepare_fresh2.py`, `fresh2_prepare.txt`):
- one item per (column, value);
- numeric columns in 5 equal-frequency bins;
- one-hot columns as an item where the value is 1;
- identifiers and weights dropped.

| dataset | tx | items |
|---|---|---|
| poker (testing file) | 1,000,000 | 95 |
| covertype | 581,012 | 101 |
| census_kdd (train) | 199,523 | 510 |
| diabetes130 | 101,766 | 2,530 |

Instances: the extension levels (`--cap-reachable`). That gives 18, of which
15 are at sigma where the probe samples. Ten implementations, FGC-Stream
included, with a 600 s cutoff:

`tools/bench_real_extra.py --datasets diabetes130 census_kdd covertype poker
--timeout 600 --extra-algos FGC_Stream --no-calibration --cap-reachable
--workers 2 --out results/fresh2_summary.csv`

Probes run after the benchmark, one instance at a time (`tools/fresh2_eval.py
--probe`). The probe's points are stored, and both forms are computed from
the same points.

## Frozen (this commit)

`recommender/probe.py` (GR_FIXED_MB and `_fixed_power`), `engine.py`,
`intervals.py` / `intervals.json`, `perfmodel.py`, `training_runs.csv`.

## Criteria

- **G1 (primary, accuracy):** over the sampled instances where Gr-growth
  completed and every sample reading was at least 2 MB, the new form's
  median |log10 error| of Gr-growth's full-size memory is below the affine
  line's. Every pair is reported.
- **G2 (decision, non-inferiority):** the shipped ranking with the new form
  (C2) is at most 1.00x the shipped ranking with the affine line (C1) in
  geometric-mean memory regret, over all instances with a completed eligible
  miner. A failed pick counts as 10.
- **G3 (secondary):** C2 below the engine (A), with cluster-bootstrap
  P(better) >= 0.95. With four datasets this is weak, and it is reported
  either way.
- **G4:** the probe's memory interval covers >= 0.85 of completed native
  runs.
