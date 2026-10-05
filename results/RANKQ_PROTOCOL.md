# Ranking quantiles on exact memory: protocol

Written and committed before the new quantiles are computed or any pick is
compared.

## The gap

The ranking scores memory at the UPPER end of its 90% interval
(`engine.py`, `_mem`; `intervals.interval`). Those quantiles
(`recommender/data/intervals.json`, keys `model_*` and `probe_*`) are still
built by `intervals.build()` from `results/interval_residuals.csv`: 794 runs,
17 datasets, memory read by polling VmHWM and predicted by the model trained
on 17 datasets. Every truth and every displayed interval is now on exact
peak memory (`tools/peakrun`) with the model trained on 81 datasets. The
ranking's quantiles therefore describe a measurement the system no longer
makes.

## The rule (fixed here)

Same construction as `intervals.build()` (pooled over runs, alpha = 0.10,
the k/(k+1) correction for k datasets), on the exact pools the display
intervals already use:

- `model_memory`, `model_runtime`: `results/exact/interval_groups_all.csv`,
  log10(true_mem / pred_mem) and log10(max(true_rt, 0.01) / max(pred_rt, 0.01)).
- `probe_memory_measured`, `probe_memory_sampled`:
  `results/exact/interval_groups_probe_all.csv`, log10(true_mem / est_mem) by kind.
- `probe_runtime_*`: kept as they are. The exact pool has no probe runtime
  estimate, and the runtime measurement did not change.

Neither pool contains FRESH7 or FRESH8 (checked: the sources are summary,
extra, extra2, confirm, hard, fresh–fresh6, training).

## Evaluation (post hoc on these sets, labelled as such)

Old vs new quantiles, everything else fixed, on the baseline comparison's
instances (`tools/baseline_comparison.py`, its training table and probes):
memory objective with the probe, and the balanced objective with the probe.
Reported: geometric-mean regret, failed picks, and the number of changed
picks, per set; PRIMARY = fresh7 + fresh8, which neither pool contains.
Also the same with the deployed engine (trained on `training_all.csv`) on
PRIMARY.

Runtime objective: the score does not use the memory interval, so the picks
cannot change. This is checked, not assumed.

## Decision

- Adopt the new quantiles if, on PRIMARY with the probe, memory regret is
  not worse by more than 1% (relative) and failed picks do not increase.
  The change is a correction of the calibration source, not a tuning, so
  "no worse" is the bar, not "better".
- Otherwise do not adopt. Record why and keep the gap as a stated limitation.
- If adopted and any PRIMARY pick changes, PRIMARY is no longer an untouched
  test of the adopted ranking. A fresh pre-registered confirmation on new
  datasets then follows before the result is reported as confirmed.
