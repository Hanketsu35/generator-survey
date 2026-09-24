# Re-measurement: what will be computed, fixed before the results exist

Committed while `tools/remeasure.py` was running and before any re-measured
value was inspected beyond the first rows of its log. The pre-registered
S1–S3 results of the new-dataset benchmark (`tools/bench_status.py`) stand as
recorded: S1 PASS 0/38 (performance-first also 0/38), S2 FAIL (memory regret
1.637× vs fixed choice 1.446×), S3 FAIL (runtime regret 1.142× vs bar 1.10).
Nothing below re-labels them.

## Why a re-measurement

Short native runs were read once, at spawn: apriori on mushroom at 0.5 was
recorded at 0.02 MB, and measures 3.68–4.19 MB in 30 of 30 repeats with the
corrected monitor (commit "Measure peak memory from the kernel's high-water
mark"). On the 8 calibration configurations, the old machine's own measured
best scored on this machine gives memory regret 4.95× and runtime regret
1.106×. A criterion that the recorded ground truth itself fails cannot
separate recommenders.

## Data

`results/remeasured.csv`: every completed run under 30 s in both tables, 3
sequential repeats, median. A row is used only if all 3 repeats succeeded and
its generator count equals the recorded one numerically; others are reported
and excluded. Runs of 30 s and more keep their recorded values.

## Analyses, in this order

**M0 — did the measurement change?** Per implementation family (native /
JVM), the ratio new/recorded, and the spread of the 3 repeats (max/min). Pass
condition for using the data: median repeat spread below 1.25× for runs that
the recorded values put under 0.1 s.

**M1 — noise ceiling, re-measured.** The calibration configurations' cross-
machine oracle (old machine's best, scored on this one) with re-measured
values on both sides where available. Reported as is; it states how much of
the 4.95× was the monitor.

**M2 — S2/S3 re-scored on re-measured costs.** Same code, same model (trained
on the recorded summary.csv), same instances, same criteria; only the
extension costs are replaced. Labelled "re-measured, post-hoc".

**M3 — model retrained on re-measured training labels**, scored as M2. The
model must be fitted with `cache=False`: the model cache is keyed on the
content of summary.csv, not on the runs passed in.

**M4 — twelve datasets.** The five new datasets added to training;
leave-one-dataset-out over all twelve transactional-family datasets, regret
of the engine vs the fixed choice per objective, cluster bootstrap over held-
out datasets. Reported separately for held-out instances inside and outside
the training domain (`Recommender.outside_domain`).

No criterion is set for M1–M4: these are measurements of what the
re-measurement changes, not a second chance at S2/S3.
