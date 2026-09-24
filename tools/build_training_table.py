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
RECORDED_MACHINE = {"summary": "Windows x86_64 (recorded)",
                    "extra": "Linux x86_64"}


def build():
    _all, rem = E.valid_remeasured()
    summ = pd.read_csv(E.SUMMARY, dtype={"generator_count": str})
    ext = pd.read_csv(E.EXTRA, dtype={"generator_count": str})
    ext = ext[ext.role == "extension"][summ.columns]
    parts = []
    for src, df in (("summary", summ), ("extra", ext)):
        keys = {E._key(a, d, p) for a, d, p in
                zip(rem[rem.source == src].algorithm, rem[rem.source == src].dataset,
                    rem[rem.source == src].param_value)}
        new, n = E.apply(df, rem, src)
        hit = [E._key(a, d, p) in keys for a, d, p in
               zip(new.algorithm, new.dataset, new.param_value)]
        new["measured"] = ["remeasured" if h else "recorded" for h in hit]
        new["machine"] = ["Linux x86_64" if h else RECORDED_MACHINE[src] for h in hit]
        new["source_table"] = src
        parts.append(new)
        print("%-8s %4d rows, %4d re-measured" % (src, len(new), n))
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(OUT, index=False)
    print("-> %s: %d rows, %d datasets" % (OUT.relative_to(_ROOT), len(out),
                                            out.dataset.nunique()))
    return out


if __name__ == "__main__":
    build()
