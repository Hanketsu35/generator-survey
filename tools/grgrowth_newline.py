"""Gr-growth on the four datasets whose last line has no terminator.

    python tools/grgrowth_newline.py

Gr-growth's data reader drops a final line without a newline, so on
mushroom, connect, kosarak and c73d10k it mined one transaction fewer than
the other miners (src/datasets.newline_terminated). This re-runs every
Gr-growth row of results/exact_memory.csv on those datasets with the input
newline-terminated, three times, and compares generator count, exact peak
and runtime with the recorded run. Writes results/grgrowth_newline.csv and
prints a summary.
"""
import csv
import os
import statistics
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import pandas as pd                                        # noqa: E402

import remeasure as R                                      # noqa: E402

AFFECTED = ("mushroom", "connect", "kosarak", "c73d10k")
OUT = _ROOT / "results" / "grgrowth_newline.csv"
REPS = 3


def main():
    import psutil
    from src import metrics as M
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
    R.SCRATCH.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(_ROOT / "results" / "exact_memory.csv")
    rows = d[(d.algorithm == "Gr_growth") & d.dataset.isin(AFFECTED)]
    out = []
    for r in rows.itertuples():
        got = [R.run_once("Gr_growth", r.dataset, float(r.param_value),
                          max(60, int(3 * r.runtime_s_recorded) + 30)) for _ in range(REPS)]
        got = [g for g in got if not R._failed("Gr_growth", g)]
        counts = sorted({int(g["generator_count"]) for g in got})
        rec = {"source": r.source, "dataset": r.dataset, "param_value": r.param_value,
               "count_recorded": int(float(r.generator_count)),
               "count_newline": "|".join(map(str, counts)),
               "peak_mb_recorded": r.peak_memory_mb_exact,
               "peak_mb_newline": statistics.median(g["peak_memory_mb"] for g in got),
               "runtime_s_recorded": r.runtime_s_recorded,
               "runtime_s_newline": statistics.median(g["runtime_s"] for g in got)}
        out.append(rec)
        print("%-6s %-9s %-10.6g count %8d -> %-8s peak %7.2f -> %7.2f  rt %.4f -> %.4f"
              % (rec["source"], rec["dataset"], rec["param_value"], rec["count_recorded"],
                 rec["count_newline"], rec["peak_mb_recorded"], rec["peak_mb_newline"],
                 rec["runtime_s_recorded"], rec["runtime_s_newline"]), flush=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    o = pd.DataFrame(out)
    changed = o[o.count_newline.astype(str) != o.count_recorded.astype(str)]
    print("\n%d runs; generator count changed on %d (max +%d)"
          % (len(o), len(changed),
             max([int(c.split("|")[-1]) - n for c, n in zip(changed.count_newline,
                                                            changed.count_recorded)] or [0])))
    dm = (o.peak_mb_newline - o.peak_mb_recorded).abs()
    print("exact peak: max |difference| %.2f MB, median %.2f MB" % (dm.max(), dm.median()))
    rt = (o.runtime_s_newline / o.runtime_s_recorded)
    print("runtime ratio new/recorded: median %.3f, range %.3f-%.3f" % (rt.median(), rt.min(), rt.max()))


if __name__ == "__main__":
    main()
