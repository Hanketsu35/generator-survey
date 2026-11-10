# FRESH10: hard instances, and cost models fitted on all 81 datasets

Written and committed before any miner or probe ran on these datasets. The
thresholds (`results/fresh10_instances.csv`) come from the landmark probe
alone.

## Why

1. **Hard instances.** Reviewers noted that most test instances are small
   (the picked run took 0.03 s in the median), so the choice may not matter
   in practice. FRESH9 had only 7 scorable hard instances.
2. **A new configuration.** The cost models are fitted on 22 datasets, not
   the 81 of `training_all.csv`, because `perfmodel.load_runs` drops the
   datasets missing from the meta-feature cache (`TRAINING_SET_NOTE.md`). A
   post hoc check on PRIMARY (`review_learning_curve_output.txt`) found
   fitting on all 81 better on memory without the probe (1.127x against
   2.023x) and worse on runtime (1.370x against 1.220x). Fitting on 81 is
   adopted only if it passes here.

## Data

- **Selection rule:** the rule of FRESH8/FRESH9 (`tools/select_fresh9.py`),
  taking the next 12 datasets by data id after FRESH9's
  (`results/fresh10_selection_rule.json`).
- **One dataset left out:** Quora_Insincere_Questions_2018 is excluded
  because its conversion crashed twice with a segmentation fault
  (1,306,122 free-text rows). This leaves 11
  (`results/fresh10_selection.json`, `results/fresh10_prepare.txt`).
- **Instances:** the 1,000- and 5,000-pair targets only, with
  `cap_reachable` and a minimum absolute support of 10. This gives 21
  instances (11 at 1,000 pairs, 10 at 5,000).
- **Runs:**
  - Every instance is probed with the frozen probe (`probe_fresh10.jsonl`).
  - The ten implementations of FRESH4–9 run on every instance, with a 600 s
    cutoff.
  - One run at a time, and a run starts only when 10 GB are free
    (`bench_real_extra.py --instances results/fresh10_instances.csv
    --no-calibration --timeout 600 --extra-algos FGC_Stream --workers 1
    --min-free-gb 10 --out results/fresh10_summary.csv`).

## Criteria

Scoring: `tools/fresh10_eval.py`. Geometric-mean regret against the
cheapest completed eligible miner; a failed pick counts as 10.

- **H1 (primary):** the deployed recommender with its probe, memory
  objective. Regret <= 1.10, and no more failed picks than probe-argmin.
- **H2:** cost models fitted on all 81 datasets, memory objective without a
  probe. Regret lower than with the deployed models (22 datasets).
- **H3:** the same models, runtime objective. Regret <= 1.05 times that of
  the deployed models.
- **Intervals of the deployed engine:** the bars of FRESH9.
  - Y1, sampled probe (90%): >= 0.90.
  - Y2, model runtime (95%): >= 0.95.
  - Y3, model memory (95%): >= 0.95.
  - Y4, measured probe (95%): >= 0.95, only if at least 3 datasets;
    otherwise reported only.

## Consequences

- **H2 and H3 both pass:** the engine fits its cost models on all 81
  datasets (`load_runs` computes the missing features). The change is
  reported as confirmed here.
- **Either fails:** the engine stays as it is, and the result is reported.
- **H1 and Y1–Y4:** reported as passed or failed.

## Frozen (this commit)

FRESH9's list, plus `tools/review_learning_curve.py` (which builds the
81-dataset runs) and `tools/fresh10_eval.py`.
