"""Training table over every dataset benchmarked so far, exact memory.

    python tools/build_training_all.py

results/exact/training_runs.csv (22 datasets) plus every confirmation table:
first confirmation, hard thresholds, fresh, fresh2, fresh3, fresh4 (their
exact-memory copies in results/exact/), fresh5 and fresh6 (measured exactly
when run). Those used a 600 s cutoff; a run stopped there enters the
survival model as censored at 600 s, which is what it is.

Why: FRESH6 traced the runtime interval's shortfall to the training data.
FGC-Stream was in it on seven dense or large datasets only, and predicted at
35-3,600 s for runs of 0.01-1.2 s on small ones
(results/FRESH6_RESULTS.md). Output: results/exact/training_all.csv
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "results" / "exact"
TABLES = {"confirm": EX / "real_extra3_summary.csv", "hard": EX / "hard_summary.csv",
          "fresh": EX / "fresh_summary.csv", "fresh2": EX / "fresh2_summary.csv",
          "fresh3": EX / "fresh3_summary.csv", "fresh4": EX / "fresh4_summary.csv",
          "fresh5": ROOT / "results" / "fresh5_summary.csv",
          "fresh6": ROOT / "results" / "fresh6_summary.csv"}


def main():
    base = pd.read_csv(EX / "training_runs.csv", dtype={"generator_count": str})
    cols = list(base.columns)
    parts = [base]
    for src, path in TABLES.items():
        d = pd.read_csv(path, dtype={"generator_count": str})
        d = d.assign(measured="exact", machine="Linux x86_64", source_table=src)
        parts.append(d.reindex(columns=cols))
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(EX / "training_all.csv", index=False)
    t = out[out.category == 1]
    print("%d rows, %d datasets (%d transactional); FGC_Stream on %d datasets"
          % (len(out), out.dataset.nunique(), t.dataset.nunique(),
             out[out.algorithm == "FGC_Stream"].dataset.nunique()))


if __name__ == "__main__":
    main()
