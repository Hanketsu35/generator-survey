# Reproducing the paper

Every table and figure of the manuscript, with the command that produces it
and the file it writes. Commands run from the repository root with the
project's Python environment (`.venv`). The AutoFolio baselines need their
own Python 3.10 environment in `tools/autofolio/.venv` (see
`tools/autofolio/af_run.py`). The native programs that are not in this
repository (Borgelt's Apriori, Eclat and FP-growth, FGC-Stream, GC-growth
and DPM-delta; the probe runs three of them) are fetched and built at the measured versions by
`bash tools/fetch_native.sh` (see README, section 2).

**Machine.** One machine was used throughout: Intel Core i7-12700F, 32 GB RAM,
Ubuntu 26.04 (Linux 7.0), Java 21, SPMF 2.65. Absolute times and peaks
depend on the machine. The ranking regularities and the tests do not
assume it.

**Exact memory.** Build the launcher before any run:
`gcc -O2 -static -o tools/peakrun/peakrun tools/peakrun/peakrun.c`
(`tools/peakrun/README.md`). Without it the harness warns and falls back
to polling.

## Section 2: the field

Table and figure numbers are those of the ESWA manuscript.

| item | command | output |
|---|---|---|
| search strings (Table 1) | (recorded) | `results/litsearch/db/SCREENING_DB.md`, `queries*.txt` |
| database records, duplicates, merged list | `python tools/merge_db.py`, `python tools/merge_db.py --supplement` | `results/litsearch/db/merged*.csv` (raw exports are kept locally in `db/raw/`, not redistributed) |
| Google Scholar screening | `python tools/scholar_screen.py` | `results/litsearch/db/scholar_screening.csv` |
| title-and-abstract and full-text decisions | (manual, documented) | `db/screening*.csv`, `db/FULLTEXT_DB.md`, `db/FULLTEXT_SCHOLAR.md` |
| criteria and amendments (Table 2) | (recorded) | `results/litsearch/RULE.md` |
| counted algorithms (Table 3), PRISMA counts (Fig. 1) | (recorded) | `results/litsearch/VERIFIED.md`, `db/SCREENING_DB.md` |
| earlier OpenAlex search and addendum | `python tools/litsearch.py`, `--addendum` | `results/litsearch/hits*.csv`, `ADDENDUM.md` |

## Section 4: benchmark and audit

| item | command | output |
|---|---|---|
| benchmark runs | `python -m src.harness` (grids in `src/config.py`) | `results/raw/`, `results/summary_linux.csv` |
| exact re-measurement | `python tools/remeasure_exact.py`, then `python tools/apply_exact_memory.py` | `results/exact_memory.csv`, `results/exact/` |
| training table (81 datasets) | `python tools/build_training_all.py` | `results/exact/training_all.csv` |
| output audit (Table 4) | `python tools/validate_generators.py`, `validate_sequential.py`, `validate_hui.py`, `validate_rare.py`, `validate_remaining.py` | `results/validate_*.txt`, `results/seqval/` |
| GC-growth and DPM-delta audit | `python tools/validate_nus.py` | `results/validate_nus.txt` |
| GC-growth benchmark | `python tools/bench_nus.py` | `results/gcgrowth_summary.csv` |
| Gr-growth unterminated last line | `python tools/grgrowth_newline.py` | `results/grgrowth_newline.csv` |
| E1 and the regularities of Section 4.3 | `python -m recommender.evaluate` (exact table: see `results/e2_exact_output.txt`) | `results/e2_exact_output.txt` |
| extension memory ranges | `python tools/extension_table.py --exact` | stdout |
| Figure 2 (runtime and memory against the best) | `python tools/make_figures_results.py` | `kbs/figures/perf.pdf` |
| Figure 3 (memory crossing) | `python tools/make_figures.py` | `kbs/figures/crossing.pdf` |

## Section 5: the recommender

| item | command |
|---|---|
| a recommendation | `python -m recommender.cli --data-path <file> --threshold 0.01 --objective memory` |
| chat interface | `python -m recommender.chat` (web: `recommender/web/`) |
| display intervals | `python -m recommender.intervals --display-exact` |
| ranking quantiles | `python -m recommender.intervals --ranking-exact` |

## Sections 6–7: every pre-registered test

Each round has a protocol (`results/<NAME>_PROTOCOL.md`), committed before its
data, and a result (`results/<NAME>_RESULTS.md`). The scorers of the
confirmation rounds check that their frozen inputs are unchanged
(`frozen_ok`).

| round | scorer |
|---|---|
| EXTENSION | `tools/bench_status.py` |
| REMEASURE | `tools/remeasure_eval.py` |
| EXTENSION2 | `tools/bench_status2.py` |
| CONFIRM | `tools/confirm_eval.py` |
| HARD | `tools/hard_eval.py` |
| INTERVAL | `tools/interval_eval.py` |
| FRESH–FRESH8 | `tools/fresh_eval.py`, `tools/fresh2_eval.py` … `tools/fresh8_eval.py` |
| LAG, LAG2 | `tools/lag_eval.py`, `tools/lag2_eval.py` |
| BASELINE (Tables 6 and 7) | `python tools/baseline_comparison.py --af-wallclock 1800` |
| BASELINE2 (probe-argmin, selectors given the probe) | `python tools/baseline2_comparison.py --af-wallclock 1800` |
| AutoFolio seeds | `python tools/autofolio_seeds.py --seed 1` (and `--seed 2`) |
| megabytes (Table 8), probe time, Wilcoxon/Friedman (Table 7) | `python tools/gap_stats.py` → `results/gap_stats_output.txt` |
| ranking quantiles (post hoc) | `python tools/rankq_eval.py` |
| FRESH9 (post hoc decisions) | `python tools/select_fresh9.py`; `python tools/prepare_fresh9.py --download`, `--to-csv`, then without flags; `python tools/fresh9_eval.py --plan`, `--probe`, `--select`; truth runs with `tools/bench_real_extra.py --instances results/fresh9_truth_instances.csv`; score with `python tools/fresh9_eval.py` |
| SEQ1 (sequential data) | `python tools/seq1_eval.py --plan`, `--run`, then without flags |
| FRESH10 (hard instances, 81-dataset fitting) | `python tools/prepare_fresh10.py --download`, `--to-csv`, then without flags; `python tools/fresh10_eval.py --plan`, `--probe`; truth runs with `tools/bench_real_extra.py --instances results/fresh10_instances.csv`; score with `python tools/fresh10_eval.py` |
| post hoc analyses of Section 7.4 (probe memory, one-feature rule, native oracle, penalty, marginal intervals) | `python tools/review_analyses.py` → `results/review_analyses_output.txt` |
| more training data for the selectors (Section 7.4) | `python tools/review_learning_curve.py` → `results/review_learning_curve_output.txt` |
| E2, semantic errors (Section 7.5) | see the Section 4 row above |
| interval coverage (Table 9) | the FRESH7 and FRESH8 scorers |
| Figure 6 (memory regret), Figure 12 (coverage) | `python tools/make_figures.py` |
| Figures 2, 5, 7–11 | `python tools/make_figures_results.py` |
| Table 10 (what each part adds) | compiled from Tables 6 and 9, `results/FRESH9_RESULTS.md` and Section 7.5 |
