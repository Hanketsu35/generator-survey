# The progress rule where it acted after it was frozen: protocol

Written and committed before any pick on these instances is computed with
the rule off, and before any truth is joined to them.

## Why

`LAG_RESULTS.md` found no instance to test `PROGRESS_DEMOTE` on, and the
README calls the rule untested. A count of the stored probes (miners' probe
progress only, no truth read) shows that the rule's condition did occur
after the rule was frozen:

- rule committed 2ff1a5b (2026-10-01); its criteria `LAG_PROTOCOL.md`
  4a2560d (2026-10-02);
- FRESH5–FRESH8 (probes `results/probe_fresh{5,6,7,8}.jsonl`, truth
  `results/fresh{5,6,7,8}_summary.csv`) were collected from 2026-10-03 on.

So the rule and its criteria predate these data. The rule never acted in
the confirmations' own criteria because those scored intervals, not picks.

## Instances (fixed by the probe alone)

Every stored probe where the four native miners' probe progress (finished
probe runs / probe runs) is not equal, the selection of `LAG_PROTOCOL.md`
without its per-dataset and total caps (all are kept):

- **A (primary):** from `probe_fresh{5,6,7,8}.jsonl`.
- **B (secondary):** from `results/exact/probes.jsonl` (exact re-probes of
  sets collected before the rule), excluding census_kdd and diabetes130, whose
  failures produced the rule.

An instance enters only if its truth table has at least two eligible miners
and one completed eligible miner at that sigma (as in the baseline
comparison).

## Comparison

D is the ranking with `PROGRESS_DEMOTE` = True, S the same with it off;
everything else as committed at this protocol's commit (including the
ranking quantiles decided by `RANKQ_PROTOCOL.md`). Each instance uses its
stored probe. Memory objective; failed pick = 10; regret against the best
completed eligible miner. Engine: trained on `results/exact/training_runs.csv`
(the baseline comparison's, which contains none of these datasets). The
deployed engine (`training_all.csv`) is also reported, and is in-sample for
FRESH5 and FRESH6.

## Criteria (those of LAG_PROTOCOL.md)

- **L1 (primary, on A):** geometric-mean regret D < S, and failed picks
  D <= S.
- **L2 (on A):** among instances where D and S differ, D is better on more
  than it is worse. Every changed pick is reported.
- Fewer than 4 instances in A where D and S differ: underpowered, no pass or
  fail.
- B is reported the same way and does not decide.

## Consequence

- L1 and L2 pass: the rule is reported as confirmed where it acts.
- Either fails: `PROGRESS_DEMOTE` is turned off and the failure is
  reported.
- Underpowered: the rule stays as an untested heuristic, as now.
