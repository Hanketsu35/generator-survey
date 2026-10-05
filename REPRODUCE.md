# Reproducing the KBS paper

Every table and figure of the manuscript, with the command that produces it
and the file it writes. Commands run from the repository root with the
project's Python environment (`.venv`). The AutoFolio baselines need their
own Python 3.10 environment in `tools/autofolio/.venv` (see
`tools/autofolio/af_run.py`).

**Machine.** One machine was used throughout: Intel Core i7-12700F, 32 GB RAM,
Ubuntu 26.04 (Linux 7.0), Java 21, SPMF 2.65. Absolute times and peaks
depend on the machine. The ranking regularities and the tests do not
assume it.

**Exact memory.** Build the launcher before any run:
`gcc -O2 -static -o tools/peakrun/peakrun tools/peakrun/peakrun.c`
(`tools/peakrun/README.md`). Without it the harness warns and falls back
to polling.

## Section 2: the field

| item | command | output |
|---|---|---|
| systematic search (Table 1) | `python tools/litsearch.py` | `results/litsearch/hits.csv`, `queries.txt` |
| screening decisions, counts | (manual, documented) | `results/litsearch/SCREENING.md` |
| bibliographic metadata | (OpenAlex and Crossref, recorded) | `results/litsearch/bibmeta.json` |

## Section 4: benchmark and audit

| item | command | output |
|---|---|---|
| benchmark runs | `python -m src.harness` (grids in `src/config.py`) | `results/raw/`, `results/summary_linux.csv` |
| exact re-measurement | `python tools/remeasure_exact.py`, then `python tools/apply_exact_memory.py` | `results/exact_memory.csv`, `results/exact/` |
| training table (81 datasets) | `python tools/build_training_all.py` | `results/exact/training_all.csv` |
| output audit (Table 2) | `python tools/validate_generators.py`, `validate_sequential.py`, `validate_hui.py`, `validate_rare.py`, `validate_remaining.py` | `results/validate_*.txt`, `results/seqval/` |
| E1 and the regularities of §4.4 | `python -m recommender.evaluate` (exact table: see `results/e2_exact_output.txt`) | `results/e2_exact_output.txt` |
| extension memory ranges | `python tools/extension_table.py --exact` | stdout |
| Figure 2 (memory crossing) | `python tools/make_figures.py` | `kbs/figures/crossing.pdf` |

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
| BASELINE (Table 4) | `python tools/baseline_comparison.py --af-wallclock 1800` |
| BASELINE2 (probe-argmin, selectors given the probe) | `python tools/baseline2_comparison.py --af-wallclock 1800` |
| AutoFolio seeds | `python tools/autofolio_seeds.py --seed 1` (and `--seed 2`) |
| megabytes, probe time, Wilcoxon/Friedman | `python tools/gap_stats.py` → `results/gap_stats_output.txt` |
| ranking quantiles (post hoc) | `python tools/rankq_eval.py` |
| E2 (semantic errors) | see Section 4 row above |
| Figure 3 (regret), Figure 4 (coverage) | `python tools/make_figures.py` |
