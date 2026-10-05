# Is the memory gain just from measuring? Protocol

Written and committed before any of the baselines below was computed. Gap
G1 in `kbs/GAPS.md`.

## Why

In `BASELINE_RESULTS.md` the recommender with its probe (1.030x on
PRIMARY) beats every standard selector on memory. But the probe measures
the user's file at decision time, and the selectors never see that
measurement. Two baselines separate "the recommender" from "measuring":

- **probe-argmin.** Among the eligible implementations the probe returned
  a memory value for (measured or extrapolated), pick the smallest. If the
  probe returned none, fall back to the memory SBS of the training table.
  This is what a user who simply runs the probe and reads it would do.
- **Selectors with probe features.** The learned selectors of the baseline
  comparison (pairwise ranking, per-algorithm regression, SUNNY k=16, ISAC,
  AutoFolio 1,800 s), trained with nine features added to the static set.
  For each of the four native miners: log10 of its probe memory value, or
  of its lower bound (1 MB if none) when it did not finish, plus a 0/1
  flag for not finishing. The ninth feature is 1 if the probe was direct.

## Data (unchanged from the baseline comparison)

- **Training.** The rows of `results/exact/training_runs.csv` at the
  (dataset, sigma) pairs that have a stored probe in
  `results/exact/probes.jsonl` (set "training"). These are the only
  training instances with probe features. As in the baseline comparison,
  memory training uses the configurations where every implementation
  completed. The probe-free selectors are not retrained.
- **Test.** The memory instances of the baseline comparison that have a
  stored probe, the same as "recommender, probe" there. PRIMARY is FRESH7
  and FRESH8; all test sets are reported too.
- Regret, failed pick = 10, eligibility and the 5-95% cluster bootstrap
  over datasets are exactly as in `BASELINE_PROTOCOL.md`.

## Criteria (memory objective, PRIMARY)

- **B1 (primary): non-inferiority to measuring alone.** Geometric-mean
  regret of the recommender with probe <= 1.02 x that of probe-argmin.
- **B2: superiority over selectors given the probe.** Against the best of
  the probe-feature selectors on PRIMARY, the paired bootstrap probability
  that the recommender is better is >= 0.95.
- Everything is reported per method, on PRIMARY and on all sets, with
  failed picks.

## Consequence for the paper (fixed now)

- **B1 passes:** the probe's measurement is the source of the gain, and the
  recommender loses nothing by wrapping it in the filter, the model for the
  JVM miners, and the intervals. The paper says exactly that.
- **B1 fails:** the claim becomes that measuring is what helps, and the
  recommender's ranking adds no memory benefit over reading the probe. The
  recommender's value is then the semantic filter and the calibrated
  uncertainty, and the abstract and highlights are rewritten to say so.
- **B2 fails:** the comparison with standard selectors is reported with
  probe features as the stronger baseline, and "beats AutoFolio" is no
  longer stated without that qualification.
