"""Write copies of every table with peak memory replaced by the exact
re-measurement (results/exact_memory.csv, tools/remeasure_exact.py).

    python tools/apply_exact_memory.py

For each table in remeasure_exact.SOURCES, results/exact/<same name> gets:
- peak_memory_mb = the exact value (median of the JVM repeats) where the
  re-run completed with the recorded generator count;
- the recorded value elsewhere (runs of 600 s and more, timeouts, failures,
  count mismatches);
- memory_method: "exact" or "polled", per row;
- peak_memory_mb_polled: the recorded value, kept for comparison.

The recorded tables are not modified: every pre-registered result was scored
on them and stays reproducible. results/exact/training_runs.csv is the
training table rebuilt from the exact copies.
"""
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import remeasure_exact as X                                # noqa: E402

OUTDIR = _ROOT / "results" / "exact"


def main():
    OUTDIR.mkdir(exist_ok=True)
    ex = pd.read_csv(X.OUT, dtype={"generator_count": str, "generator_count_recorded": str})
    ok = ex[(ex.count_matches.astype(str) == "True") & ex.peak_memory_mb_exact.notna()]
    lookup = {(s, a, d, round(float(p), 9)): m for s, a, d, p, m in
              zip(ok.source, ok.algorithm, ok.dataset, ok.param_value, ok.peak_memory_mb_exact)}
    print("exact rows usable: %d of %d re-measured (%d count mismatches, %d failed reruns)"
          % (len(ok), len(ex), (ex.count_matches.astype(str) == "False").sum(),
             ex.peak_memory_mb_exact.isna().sum()))
    for src, path in X.SOURCES.items():
        d = pd.read_csv(_ROOT / path, dtype={"generator_count": str})
        keys = [(src, a, ds, round(float(p), 9)) for a, ds, p in
                zip(d.algorithm, d.dataset, d.param_value)]
        new = [lookup.get(k) for k in keys]
        d["peak_memory_mb_polled"] = d.peak_memory_mb
        d["memory_method"] = ["exact" if v is not None else "polled" for v in new]
        d["peak_memory_mb"] = [v if v is not None else o for v, o in zip(new, d.peak_memory_mb)]
        d.to_csv(OUTDIR / Path(path).name, index=False)
        print("%-8s %-28s %4d rows, %4d exact" % (src, Path(path).name, len(d),
                                                 (d.memory_method == "exact").sum()))
    # the training table, rebuilt from the exact copies
    import build_training_table as B
    B.OUT = OUTDIR / "training_runs.csv"
    B.LINUX = OUTDIR / "summary_linux.csv"
    B.EXTRA2 = OUTDIR / "real_extra2_summary.csv"
    B.E.EXTRA = OUTDIR / "real_extra_summary.csv"
    B.E.valid_remeasured = lambda: (None, pd.DataFrame(columns=["source", "algorithm", "dataset",
                                                                "param_value"]))
    B.E.apply = lambda df, rem, src: (df, 0)
    B.build()


if __name__ == "__main__":
    main()
