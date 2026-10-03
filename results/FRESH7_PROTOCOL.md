# Seventh fresh confirmation: the all-data model and its intervals, on OpenML-CC18

Written and committed before any miner or probe ran on these datasets.

## What is tested

The configuration of `INTERVAL_ALLDATA_POSTHOC.md`, found after FRESH6:
- **Training.** The engine trains on all 81 benchmarked datasets
  (`results/exact/training_all.csv`).
- **Model intervals.** Subsampling over datasets (Dunn et al. 2023, Method
  2) at 95%, calibrated separately for FGC-Stream, the other native
  programs, and the JVM programs; runtime centred on the survival median.
- **Probe intervals.** 95% for measured values (63 datasets), 90% for
  sampled values (24 datasets).
- **Leave-one-dataset-out estimates.** 0.979 (runtime), 0.978 (model
  memory), 0.984 (probe, measured), 0.974 (probe, sampled).

## Data: selection rule, fixed here

OpenML-CC18 (study 99, 72 datasets), downloaded 2026-10-03. The rule:
1. **Exclusions.** Drop every dataset used before or related to one used
   before: kr-vs-kp, letter, splice, dna, car, adult, connect-4,
   credit-approval, credit-g, diabetes, vehicle, vowel, segment,
   tic-tac-toe, breast-w, balance-scale, bank-marketing, sick.
2. **Size.** Keep at most 40 features and at most 100,000 instances.
3. **Families.** Keep one per family, the lowest data id: mfeat-*, and the
   NASA defect sets pc*/kc*/jm1.

That leaves 24 datasets (`fresh7_selection.json`), converted by the rule of
FRESH4-6 (`tools/prepare_fresh7.py`, `fresh7_prepare.txt`), names prefixed
"oml_". That gives 92 instances, with ten implementations and a 600 s
cutoff (`tools/bench_real_extra.py ... --out results/fresh7_summary.csv`).
Probes run afterwards, one instance at a time.

The selection was done from OpenML metadata only, before any of these files
was read.

## Frozen (this commit)

`engine.py`, `probe.py`, `intervals.py`, `data/intervals.json`,
`perfmodel.py`, `survival.py`, `results/exact/training_all.csv`.

## Criteria (mean per-dataset coverage; each bar is the interval's guarantee)

- **X1 (primary):** model runtime interval (95%): >= 0.95.
- **X2:** model memory interval (95%): >= 0.95.
- **X3:** probe memory interval, measured (95%): >= 0.95.
- **X4:** probe memory interval, sampled (90%): >= 0.90, if at least 3
  datasets are sampled; otherwise reported only.
