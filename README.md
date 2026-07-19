# Minimal Generator Algorithm Benchmark

Benchmark harness and survey paper for **"An Analytical and Empirical Survey of Minimal Generator Algorithms"** (CENG 643, 2025).

Covers 23 AND-generator algorithms across 5 families (transactional, sequential, high-utility, graph, rare/stream), benchmarks 14 of them over 10 real-world datasets in 209 controlled runs.

---

## Repository Structure

```
├── src/
│   ├── harness.py        # Main benchmark runner
│   ├── config.py         # Algorithm registry and parameter grids
│   ├── datasets.py       # Dataset download and formatting
│   ├── metrics.py        # SPMF/external runner, memory monitor
│   └── analyze.py        # Results aggregation and plot generation
├── external_algos/
│   └── Gr_growth/        # Gr-growth C++ source + Windows binary
├── results/
│   ├── summary.csv       # Full 209-run results table
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

### 2. Build Gr-growth (non-Windows only)

A pre-compiled Windows binary is included at `external_algos/Gr_growth/grgrowth-v1/GrGrowth-PBD-source/GrGrowth_PBd.exe`.

On Linux/macOS, compile from source:

```bash
cd external_algos/Gr_growth/grgrowth-v1/GrGrowth-PBD-source
g++ -O2 -o GrGrowth_PBd *.cpp
```

Then update `config.py` → `"exe"` path for `Gr_growth` to point to the compiled binary.

### 3. FGC-Stream (optional)

FGC-Stream is a Windows-only binary not included in this repository due to size. To enable it, obtain the executable from the authors and place it at:

```
external_algos/FGC_Stream/FGC-Stream/FGC_Stream_release.exe
```

Without this binary, FGC-Stream runs are skipped automatically (`available: False`).

### 4. Download Datasets

Datasets are downloaded automatically from the SPMF public dataset repository:

```bash
python -m src.datasets
```

This creates:
- `datasets/raw/` — original SPMF-format files (10 datasets)
- `datasets/spmf_format/` — utility-fixed versions for high-utility algorithms

Datasets downloaded: `mushroom`, `connect`, `chess`, `T10I4D100K`, `retail` (transactional); `leviathan`, `bible`, `sign` (sequential); `chainstore`, `foodmart` (utility).

---

## Running the Benchmark

**Full benchmark (all 14 available algorithms, all datasets):**

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

---

## Parameter Grids

| Family | Parameter | Values |
|---|---|---|
| Transactional | minsup | 0.2, 0.3, 0.5, 0.7 |
| Sequential | minsup | 0.2, 0.3, 0.5, 0.7 |
| Rare (Arima) | maxsup | 0.1, 0.2, 0.3 |
| High-Utility (chainstore) | min\_utility | 1000, 2000, 5000 |
| High-Utility (foodmart) | min\_utility | 20, 50, 100 |
| Stream (FGC-Stream) | window\_size | 0.1, 0.2 |

---

## Algorithm Availability

| Algorithm | Family | Source |
|---|---|---|
| Gr-growth | Transactional | C++ source (this repo) |
| Pascal, Zart, DefMe, TalkyG, TalkyG-Diffset | Transactional | SPMF v2.65 |
| FEAT, FSGP, VGEN | Sequential | SPMF v2.65 |
| HUG-Miner, GHUI-Miner, HUCI-Miner-Gen. | High-Utility | SPMF v2.65 |
| Arima | Rare | SPMF v2.65 |
| FGC-Stream | Stream | Windows binary (not bundled) |

9 of 23 surveyed algorithms have no public implementation and are not benchmarked.

---

## Citation

```bibtex
@misc{kacikan2025generators,
  author  = {Kacikan, Egemen},
  title   = {An Analytical and Empirical Survey of Minimal Generator Algorithms},
  year    = {2025},
  url     = {https://github.com/Hanketsu35/generator-survey}
}
```
