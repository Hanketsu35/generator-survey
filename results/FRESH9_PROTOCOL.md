# Ninth fresh confirmation: the progress rule and the current system

Written and committed before any miner or probe ran on these datasets. The
thresholds (`results/fresh9_instances.csv`) were computed before this commit
from the landmark probe alone, as in every earlier round; no miner ran.

## Why

Two decisions in the system were made post hoc and are reported in the paper
as unconfirmed:

1. **The progress rule** (`PROGRESS_DEMOTE`, `PROGRESS_POSTHOC.md`): a probed
   native miner that finished fewer of its probe runs than another is ranked
   after every miner the probe did not show to be slow. Its record is 4 picks
   right and 4 wrong, and its two targeted tests (`LAG_RESULTS.md`,
   `LAG2_RESULTS.md`) were underpowered: the condition is rare (13 of 319
   stored probes).
2. **The ranking quantiles** were rebuilt from the exact pools after the last
   confirmation (`RANKQ_RESULTS.md`, 4c56655), and the threshold side of
   Gr-growth and FGC-Stream was corrected (19461c6). Neither changed a pick
   on the 335 earlier test instances, but the system as it now stands has
   not been run on new data.

## Data: selection rule, fixed here

The rule of `FRESH8_PROTOCOL.md`, applied to the OpenML listing of
2026-11-09 (`results/fresh9_openml_listing.json`:
every active dataset with 80,000-1,500,000 instances and 3-40 features, 562)
by `tools/select_fresh9.py`, which reproduces FRESH8's eight as the first
eight. The rule's family test (rule 4) is the name prefix up to the first
character that is not a letter or digit; a prefix that starts another is the
same family. **Count:** the next 24 by data id after FRESH8's last
(`results/fresh9_selection.json`): Climate, Run_or_walk_information,
freMTPL2freq, Klaverjas2018, wine-reviews, black_friday,
FOREX_eurchf-minute-Close, 1DUltrasoundMuscleContractionData,
kickstarter_projects, medical_charges, la_crimes, porto-seguro,
particulate-matter-ukair-2017, nyc-taxi-green-dec-2016, Node_Embedding,
Edge_Embedding, Asteroid_Dataset, SoilHydroDB, sf-police-incidents,
hls4ml_lhc_jets_hlf, RelevantImagesDatasetTEST, test, nba-shot-logs,
WorkersCompensation. Selection used metadata only.

Files: OpenML's parquet copies (the ARFF server delivered ~50 KB/s), read as
strings and converted by the rule of FRESH4-8 (`tools/prepare_fresh9.py`,
counts in `results/fresh9_prepare.txt`).

Thresholds: `tools/bench_real_extra.plan` with `cap_reachable`, the five pair
targets (10, 100, 1,000, 5,000, 20,000) and the minimum absolute support of
10, as in FRESH4-8 (`results/fresh9_instances.csv`): 107 instances on the
24 datasets (24 at 10 pairs, 24 at 100, 23 at 1,000, 20 at 5,000, 16 at
20,000). Part B below is therefore 48 instances; Part A is whatever the probe
selects.

## Procedure

1. **Probe** every planned instance with the frozen probe
   (`tools/fresh9_eval.py --probe`, `results/probe_fresh9.jsonl`).
2. **Select** by the probe alone (`--select`, `results/fresh9_truth_instances.csv`):
   - **Part A:** every instance where the four native miners' probe progress
     (finished probe runs / probe runs) is not equal, the selection of
     `LAG2_PROTOCOL.md`, at any target.
   - **Part B:** every instance at the 10- and 100-pair targets.
3. **Truth:** the ten implementations of FRESH4-8 on every selected
   instance, 600 s cutoff, Part A first (`tools/bench_real_extra.py
   --instances results/fresh9_truth_instances.csv --no-calibration
   --timeout 600 --extra-algos FGC_Stream --workers 1 --min-free-gb 10
   --out results/fresh9_summary.csv`). The machine is shared: one run at a
   time, a run starts only when 10 GB are free, and the benchmark's
   processes are the first the kernel's OOM killer takes. None of this
   changes what a run measures (same JVM default heap and native cap as
   before). An instance enters the scoring only if it has at least two
   eligible miners and one completed eligible miner.
4. **Score** (`tools/fresh9_eval.py`): the deployed engine, trained on
   `results/exact/training_all.csv`, which contains none of these datasets.
   Memory objective; failed pick = 10; regret against the best completed
   eligible miner.

## Criteria

**Part A (the progress rule).** D is the ranking with `PROGRESS_DEMOTE` on,
S with it off, each with the instance's stored probe.
- **L1 (primary):** geometric-mean regret D < S, and failed picks D <= S.
- **L2:** among instances where D and S differ, D is better on more than it
  is worse. Every changed pick is reported.
- Fewer than 4 instances where D and S differ: underpowered, no pass or fail.
- **L3 (secondary, reported, does not decide):** L2 separately for direct and
  sampled probes. `LAG2_RESULTS.md` observed after the fact that the rule
  was right mostly on sampled probes and wrong mostly on direct ones; this
  records whether that holds on new data. A rule restricted to one mode
  would be a new rule and would need its own test.

**Part B (the current system).**
- **Z1 (primary):** the recommender with its probe against probe-argmin (the
  smallest probe value), the comparison of `BASELINE2_PROTOCOL.md`: ratio of
  geometric-mean regrets <= 1.02, and failed picks no more than
  probe-argmin's.
- **Z2:** the recommender's geometric-mean memory regret <= 1.10.

**Intervals (every instance with a truth run), the bars of FRESH8:**
- **Y1:** probe memory, sampled (90%): mean per-dataset coverage >= 0.90.
- **Y2:** model runtime (95%): >= 0.95.
- **Y3:** model memory (95%): >= 0.95.
- **Y4:** probe memory, measured (95%): >= 0.95, if at least 3 datasets have
  measured values; otherwise reported only.

## Frozen (this commit)

`recommender/engine.py`, `recommender/probe.py`, `recommender/intervals.py`,
`recommender/data/intervals.json`, `recommender/perfmodel.py`,
`recommender/survival.py`, `recommender/capabilities.py`,
`results/exact/training_all.csv`, `tools/bench_real_extra.py`. The scoring
script refuses to run if any differs from this commit.

## Consequences

- L1 and L2 pass: the progress rule is reported as confirmed where it acts.
- L1 or L2 fails: `PROGRESS_DEMOTE` is turned off and the failure is
  reported.
- Underpowered: the rule stays, reported as untested, with the new count.
- Z1, Z2 and Y1-Y4 are reported as passed or failed as they come out; a
  failure is reported, not repaired in this round.
