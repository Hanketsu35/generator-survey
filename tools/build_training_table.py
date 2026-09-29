"""Build the engine's default training table: results/training_runs.csv.

    python tools/build_training_table.py

What it is. results/summary.csv (the published table, 7 transactional
datasets plus the sequential, utility and rare categories) and the extension
rows of results/real_extra_summary.csv (5 more transactional datasets), with
runtime and peak memory replaced by the re-measured medians of
results/remeasured.csv wherever a valid re-measurement exists (all repeats
ran, generator count equal to the recorded one). Calibration rows are left
out: they repeat configurations already in summary.csv.

Why it is the default. Every native run under 0.1 s had its memory read once,
at spawn -- under-measured 3.3-3.8x in geometric mean, up to 1423x. Trained
on the re-measured labels plus the new datasets, leave-one-dataset-out memory
regret on the seven original datasets went from 1.807x to 1.450x (fixed
choice 1.502x), with runtime unchanged against the fixed choice
(results/REMEASURE_RESULTS.md).

Provenance per row: ``measured`` is "remeasured" or "recorded", ``machine``
where the value was measured. Runs of 30 s and more keep their recorded
values -- for summary.csv that is the Windows machine; the calibration runs
put the Linux/Windows ratio there at 0.87x runtime and 1.19x memory for the
JVM miners, not the orders of magnitude the short runs were off by.

summary.csv itself is not modified: the published experiments and the
pre-registered evaluation read it, and must stay reproducible.
"""
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import remeasure_eval as E                               # noqa: E402

OUT = _ROOT / "results" / "training_runs.csv"
LINUX = _ROOT / "results" / "summary_linux.csv"
EXTRA2 = _ROOT / "results" / "real_extra2_summary.csv"


def build():
    """Everything measured on the Linux machine, in one table.

    summary        results/summary_linux.csv -- the 667 published
                   configurations, every row measured on this machine
                   (re-measured short runs + tools/rerun_published.py)
    extra          the first extension (bms1, bms2, c20d10k, kosarak,
                   c73d10k), short runs replaced by their re-measured medians
    extra2         the second extension (chicago, kddcup99, onlineretail,
                   pamap, recordlink), measured with the corrected monitor
    """
    _all, rem = E.valid_remeasured()
    summ = pd.read_csv(LINUX, dtype={"generator_count": str})
    cols = [c for c in pd.read_csv(E.SUMMARY, nrows=1).columns]
    summ = summ[cols].assign(measured=summ.source, machine="Linux x86_64",
                             source_table="summary")
    ext = pd.read_csv(E.EXTRA, dtype={"generator_count": str})
    ext = ext[ext.role == "extension"][cols]
    ext, n1 = E.apply(ext, rem, "extra")
    ext = ext.assign(measured="linux", machine="Linux x86_64", source_table="extra")
    ext2 = pd.read_csv(EXTRA2, dtype={"generator_count": str})[cols]
    ext2 = ext2.assign(measured="linux", machine="Linux x86_64", source_table="extra2")
    out = pd.concat([summ, ext, ext2], ignore_index=True)
    out.to_csv(OUT, index=False)
    for src, g in out.groupby("source_table", sort=False):
        print("%-8s %4d rows, %2d datasets" % (src, len(g), g.dataset.nunique()))
    print("-> %s: %d rows, %d datasets, all measured on Linux"
          % (OUT.relative_to(_ROOT), len(out), out.dataset.nunique()))
    return out


if __name__ == "__main__":
    build()
