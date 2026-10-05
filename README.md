# Minimal generators: survey, benchmark, and a semantics-aware recommender

Code, data and paper for **"Which minimal-generator miner answers the question
asked? A benchmark-grounded, semantics-aware recommender with pre-registered
validation"** (in preparation for *Knowledge-Based Systems*; `kbs/`).

- **Survey.** A systematic search finds 52 minimal-generator algorithms in
  five families. 14 have an executable implementation (`results/litsearch/`).
- **Benchmark.** The 17 executable implementations (the 14 algorithms plus
  three native post-filtering baselines), with exact peak memory
  (`tools/peakrun`). 81 datasets, 3,284 runs in the training table.
- **Output audit.** Every implementation is checked against oracles for
  the definition it claims (`tools/validate_*.py`).
- **Recommender.** `recommender/`: semantic filter, cost model, probe on the
  user's file, and prediction intervals calibrated over datasets. Every test
  was pre-registered (`results/*_PROTOCOL.md`, `results/*_RESULTS.md`).
- **Reproduction.** `kbs/REPRODUCE.md` maps every table and figure of the
  paper to the command that produces it.

The earlier survey manuscript is in `report/`. It is kept as written, and
its counts (25 algorithms) predate the systematic search.

---

## Repository Structure

```
├── src/
│   ├── harness.py        # Main benchmark runner
│   ├── config.py         # Algorithm registry and parameter grids
│   ├── datasets.py       # Dataset download and formatting
│   ├── metrics.py        # SPMF/external runner, memory monitor
│   └── analyze.py        # Results aggregation and plot generation
├── recommender/          # the recommender (engine, probe, intervals, CLI, chat)
├── kbs/                  # the KBS paper (main.tex, sections/, figures/)
├── tools/                # evaluation scripts, validators, peakrun launcher
├── external_algos/
│   ├── Gr_growth/        # Gr-growth C++ source
│   ├── FGC_Stream/       # FGC-Stream C++ source
│   └── borgelt/          # Borgelt's Apriori, Eclat, FP-growth
├── results/
│   ├── summary.csv       # Full 655-run results table
│   └── raw/              # Per-run JSON files
├── plots/                # Generated figures (PDF)
└── report/
    ├── main.tex          # LaTeX source
    ├── main.pdf          # Compiled paper
    └── references.bib
```

---

## Requirements

| Dependency | Version | Purpose |
|---|---|---|
| Python | ≥ 3.9 | Harness and analysis scripts |
| Java JRE | ≥ 8 | Running SPMF algorithms |
| SPMF | v2.65 | Algorithm implementations |
| psutil | any | Peak memory monitoring |
| pandas | any | CSV results handling |
| matplotlib | any | Plot generation |
| requests | any | Dataset download |

Install Python dependencies:

```bash
pip install psutil pandas matplotlib requests
```

---

## Setup

### 1. Download SPMF

SPMF is not bundled in this repository. Download `spmf.jar` from the official site and place it at `spmf/spmf.jar`:

```
https://www.philippe-fournier-viger.com/spmf/index.php?link=download.php
```

```bash
mkdir spmf
# Move the downloaded spmf.jar here:
mv ~/Downloads/spmf.jar spmf/spmf.jar
```

Verify:

```bash
java -jar spmf/spmf.jar
```

### 2. Build the native programs and the memory launcher

On Linux, each native program is built next to its Windows `.exe` name
without the extension, and `src/config.py` picks the extension-less binary
automatically:

```bash
gcc -O2 -static -o tools/peakrun/peakrun tools/peakrun/peakrun.c
cd external_algos/Gr_growth/grgrowth-v1/GrGrowth-PBD-source && g++ -O2 -std=c++17 -o GrGrowth_PBd *.cpp
```

The other native programs are built the same way: FGC-Stream from
`external_algos/FGC_Stream/FGC-Stream/` (`FGC_Stream_release`), and the
Borgelt programs with their own makefiles. Without `tools/peakrun/peakrun`,
the harness warns and falls back to polling memory, which misses short runs.

> **Important — the `k` argument.** Gr-growth's third command-line argument is
> the *depth of the subset test*, not a pattern-length cap. Only `k=1` yields
> minimal generators. At `k >= 2` the miner applies an inclusion–exclusion
> condition (`calc_subset_sum`, `PatternSet.cpp:346,440`) that characterises the
> strictly smaller *disjunction-free* family, so the output is sound but
> incomplete — on mushroom at minsup=0.2 it returns 683 of the 1,703 generators.
> This benchmark therefore pins `GRGROWTH_K = 1` in `src/config.py`. Do not
> change it unless you intend to mine a different pattern family.

### 3. Download Datasets

Datasets are downloaded automatically from the SPMF public dataset repository:

```bash
python -m src.datasets
```

This creates:
- `datasets/raw/` — original SPMF-format files (12 datasets)
- `datasets/spmf_format/` — utility-fixed versions for high-utility algorithms

Datasets downloaded: `mushroom`, `connect`, `chess`, `T10I4D100K`, `retail` (transactional); `leviathan`, `bible`, `sign` (sequential); `chainstore`, `foodmart` (utility).

---

## Running the Benchmark

**Full benchmark (all 17 available implementations, all datasets):**

```bash
python -m src.harness
```

Runs are automatically skipped if already present in `results/summary.csv` (resume-safe).

**Subset by algorithm:**

```bash
python -m src.harness --algos DefMe Zart Pascal
```

**Subset by dataset:**

```bash
python -m src.harness --datasets mushroom chess
```

**Subset by category:**

```bash
python -m src.harness --categories 1 2   # transactional + sequential only
```

Each run enforces a **3600-second (1-hour) timeout**. DNF runs are recorded with `timed_out=True` and excluded from per-algorithm averages.

Results are appended to `results/summary.csv` and individual JSON files are saved to `results/raw/`.

---

## Reproducing Plots

```bash
python -m src.analyze
```

Generates all figures from the paper into `plots/`.

Every derived number quoted in the paper comes from:

```bash
python tools/paper_numbers.py     # single source of truth for the text
python -m src.analyze             # figures + report/tables.md
```

---

## Auxiliary Tools

| Script | Purpose |
|---|---|
| `tools/paper_numbers.py` | Regenerates every derived figure quoted in the paper |
| `tools/repair_summary.py` | Idempotent: re-marks crashed runs in `summary.csv` from the raw JSONs |
| `tools/check_grgrowth.py` | Validates Gr-growth output against DefMe and a bitset support oracle |
| `tools/rerun_arima_xmx.py` | Diagnostic re-run of Arima's 5 OOM configs with `-Xmx12g` |
| `tools/validate_hui.py` | Output validation for HUG-Miner: support-minimality + utility threshold |
| `tools/validate_sequential.py` | Subsequence oracle: validates FEAT/FSGP/VGEN and explains their differences |
| `tools/validate_remaining.py` | GHUI/HUCI semantics + FGC-Stream generator–closure verification |
| `tools/validate_rare.py` | Maximum-support oracle for Arima: minimal-rare-itemset soundness **and** negative-border completeness |
| `tools/make_elsevier.py` | Regenerates `report/main_elsevier.tex` (Elsevier `elsarticle`) from the KAIS source, which it never modifies |

> **Two journal formats, one source.** `report/main_kais_sn.tex` (Springer
> `sn-jnl`, KAIS) is the master. The Elsevier version is **generated**, never
> hand-edited:
>
> ```bash
> python tools/make_elsevier.py            # report/main_elsevier.tex
> python tools/make_elsevier.py --review   # double-spaced, line-numbered
> ```
>
> Edit the KAIS file, then re-run the script. The converter rewrites only the
> front matter (`\author`/`\affil` → `\author`/`\affiliation`, `\abstract{}` →
> the `abstract` environment, `\keywords` → `keyword` with `\sep`, `\bmhead` →
> `\section*`, plus `\bibliographystyle{elsarticle-harv}`) and applies three
> class-specific typographic corrections, because `elsarticle` is 12 pt where
> `sn-jnl` is 10 pt: absolute `text width` values in the taxonomy `forest` and
> the fixed `tabularx` columns are scaled by the font ratio, and table notes are
> set ragged-right. Both versions build with 0 errors and 0 overfull boxes.

> **HUCI-Miner-Generators does not output minimal generators.** Measured on
> foodmart: of its 2,002 patterns at min_utility=50, **0 are support-minimal**
> and **0 are closed**, but 1,976 (98.7%) are minimal with respect to *utility*
> (no immediate subset reaches the threshold). Its counts are therefore **not
> comparable** with HUG-Miner's or GHUI-Miner's. Do not tabulate them in the
> same column.
>
> **GHUI ⊃ HUG, exactly.** All GHUI-Miner patterns are support-minimal with a
> high-utility closure; the subset whose own utility clears the threshold is
> exactly HUG-Miner's output (687 at θ=100, 1,475 at θ=50 — matching HUG-Miner
> run for run).

The Arima diagnostic writes to `results/arima_xmx_diagnostic.csv` and does
**not** touch `summary.csv`. The main protocol deliberately runs every JVM
algorithm on the default heap so that completion rates stay comparable; the
enlarged-heap runs exist only to test whether an OOM is an algorithmic limit or
a configuration artifact. Result: 1 of the 5 recovers (chess maxsup=0.3), 4
abort again at 11.1–11.8 GB.

---

## Parameter Grids

| Family | Parameter | Values |
|---|---|---|
| Transactional | minsup | per-dataset (see `MINSUP_BY_DATASET` in `src/config.py`) |
| Sequential | minsup | per-dataset (see `SEQ_MINSUP_BY_DATASET`) |
| Rare (Arima) | maxsup | 0.1, 0.2, 0.3 |
| High-Utility (chainstore) | min\_utility | 1000, 2000, 5000 |
| High-Utility (foodmart) | min\_utility | 20, 50, 100 |
| Stream (FGC-Stream) | window\_size | 0.1, 0.2 |

> **Sequential thresholds — do not use the transactional grid.** The old
> `{0.2, 0.3, 0.5, 0.7}` grid is *mathematically impossible* for these datasets:
> the most frequent single item reaches only 0.75% on leviathan and 0.27% on
> bible, so 11 of 12 runs returned empty output and the measured times were JVM
> startup.
>
> Worse, on **leviathan and bible no multi-item sequence is frequent at any
> threshold** — the most frequent item *pair* co-occurs in just 3 sequences on
> each. Lower the threshold enough to catch it and the output is already every
> item (9,025 and 13,905 = the distinct-item counts). On those two datasets the
> task degenerates to frequent-item counting and the subsequence relation is
> never exercised. Verified independently with PrefixSpan, which returns the
> same counts. Only **sign** does real sequential mining, and only at
> minsup ≤ 0.05 (at 0.015: 267 singletons + 69,415 pairs + 28 triples).

---

## Algorithm Availability

| Algorithm | Family | Source |
|---|---|---|
| Gr-growth | Transactional | C++ source (this repo) |
| Pascal, Zart, DefMe, TalkyG, TalkyG-Diffset | Transactional | SPMF v2.65 |
| FEAT, FSGP, VGEN | Sequential | SPMF v2.65 |
| HUG-Miner, GHUI-Miner, HUCI-Miner-Gen. | High-Utility | SPMF v2.65 |
| AprioriRare (labelled `Arima` in `src/config.py` and the results tables) | Rare | SPMF v2.65 |
| FGC-Stream | Stream | C++ source (this repo) |

38 of the 52 algorithms found by the systematic search have no executable
implementation (`results/litsearch/SCREENING.md`). Availability depends on age:
13 of the 36 algorithms published up to 2015 are executable (36.1%), and 1 of
the 16 published from 2016 onwards (6.3%).

The rare-itemset implementation in SPMF is AprioriRare, which finds the minimal
rare itemsets. Szathmary et al. (2007) propose it together with Arima, which
restores all rare itemsets. Earlier versions of this repository called the
implementation Arima. The identifier is kept so that the results tables stay
valid.

---

## Citation

```bibtex
@misc{kacikan2026generators,
  author  = {Ka\c{c}{\i}kan, Egemen and Ergen\c{c} Bostano\u{g}lu, Belgin and Onan, Aytug},
  title   = {Which Minimal-Generator Miner Answers the Question Asked? A Benchmark-Grounded,
             Semantics-Aware Recommender with Pre-Registered Validation},
  year    = {2026},
  url     = {https://github.com/Hanketsu35/generator-survey}
}
```
