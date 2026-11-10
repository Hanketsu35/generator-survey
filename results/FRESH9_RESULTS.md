# Ninth fresh confirmation: results

Protocol: `FRESH9_PROTOCOL.md` (2900df7; 22e0aed before the history rewrite of 2026-11-11, `COMMIT_MAP.md`). Probes `probe_fresh9.jsonl`;
selection `fresh9_truth_instances.csv`; truth `fresh9_summary.csv` (570 runs:
Part A 90 runs, 8.7 h; all 480 runs of Part B, 8.3 h; one run at a time, 10 GB
free required before each run); scoring `tools/fresh9_eval.py`, output
`fresh9_eval_output.txt`, rows `fresh9_eval_rows.csv` and
`fresh9_interval_rows.csv`. The frozen files matched the protocol commit.

## Result: every criterion passed (7 of 7)

**Part A, the progress rule.** The probe selected 9 instances where the
native miners' probe progress differs (1 at 1,000 pairs, 4 at 5,000, 4 at
20,000); 7, on 6 datasets, have two eligible miners and a
completed one. The rule changed the pick on 4, the protocol's minimum, so the
test is not underpowered.

| | rule on (D) | rule off (S) |
|---|---|---|
| geometric-mean memory regret | 1.013x | 1.959x |
| failed picks | 0 | 2 |

- L1 (primary): D < S and failures D <= S: **PASS**
- L2: changed picks, D better on 3, worse on 1: **PASS**
- L3 (secondary): direct probes 1 changed, D better 1; sampled probes 3
  changed, D better 2, worse 1.

Changed picks: node_embedding 0.00827 (sampled; Apriori finished no probe run;
rule off picks Apriori, which failed) and porto_seguro 0.0260 (sampled; the
same): D avoids two failures; asteroid_dataset 0.00831 (sampled): D 1.084 vs
S 1.000; soilhydrodb 0.000641 (direct): D 1.000 vs S 1.102.

**Part B, the current system** (rebuilt ranking quantiles, corrected
threshold sides), 48 instances on 24 datasets:
- Z1 (primary): recommender 1.034x vs probe-argmin 1.034x, ratio 1.000
  (<= 1.02), failed picks 0 vs 0: **PASS**. Same pick on 48 of 48.
- Z2: recommender memory regret 1.034x (<= 1.10): **PASS**.

**Intervals** (every instance with a truth run, 24 datasets):
- Y1 probe memory, sampled (90%): 0.949, 19/24 datasets at the level, min
  0.73, median width x3.04: **PASS**
- Y2 model runtime (95%): 0.987, 21/24, min 0.84: **PASS**
- Y3 model memory (95%): 0.990, 22/24, min 0.88: **PASS**
- Y4 probe memory, measured: one dataset only, reported: 1.000.

## Consequence (as the protocol fixes it)

The progress rule is reported as confirmed where it acts. The current
system, with the ranking quantiles rebuilt after FRESH8, is confirmed on new
data.
