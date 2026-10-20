"""Benchmark GC-growth on the paper's transactional grid.

    python tools/bench_nus.py

GC-growth (Li et al., PODS 2005; Liu's program, version 2.0) was found after
the benchmark had been run. It is run here on the 58 configurations of
Gr-growth in results/summary_linux.csv, exactly as the harness runs
Gr-growth: absolute threshold round(sigma*|D|), newline-terminated input,
the harness's timeout and the native miners' address-space cap of a quarter
of the RAM, peak memory read exactly (wait4), one run at a time. Writes
results/gcgrowth_summary.csv in the schema of the summary tables, then
compares it with the exact peaks and runtimes of results/exact_memory.csv
(Gr-growth's counts as re-run newline-terminated, results/grgrowth_newline.csv)
and writes results/gcgrowth_compare.txt; --compare does only the comparison.

DPMiner's released program (DPM-delta) is not benchmarked: it returns the
generators of the delta-discriminative equivalence classes only, never the
generator family (tools/validate_nus.py).
"""
import argparse
import csv
import os
import platform
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

import pandas as pd                                        # noqa: E402

from src import metrics as M                               # noqa: E402
from src.config import TIMEOUT_SECONDS                     # noqa: E402
from src.datasets import get_dataset_path                  # noqa: E402

EXE = _ROOT / "external_algos" / "GC_growth" / "GcGrowth"
OUT = _ROOT / "results" / "gcgrowth_summary.csv"
SCRATCH = _ROOT / "results" / "raw" / "gcgrowth"
FIELDS = ["algorithm", "category", "dataset", "param_name", "param_value", "runtime_s",
          "peak_memory_mb", "generator_count", "timed_out", "error", "timestamp", "source",
          "machine"]


def count_keys(path):
    """Generators in <base>.key, the empty set included (as Gr-growth's count)."""
    n = 0
    with open(path) as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def main():
    import psutil
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(_ROOT / "results" / "summary_linux.csv")
    grid = grid[grid.algorithm == "Gr_growth"][["dataset", "param_value"]]
    done = set()
    if OUT.exists():
        d = pd.read_csv(OUT)
        done = {(a, round(float(b), 9)) for a, b in zip(d.dataset, d.param_value)}
    header = not OUT.exists()
    with open(OUT, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if header:
            w.writeheader()
        for ds, sg in grid.itertuples(index=False):
            if (ds, round(float(sg), 9)) in done:
                continue
            path = str(get_dataset_path(ds))
            n = M.count_transactions(path)
            abs_sup = max(1, int(round(sg * n)))
            base = str(SCRATCH / ("out_%s_%s" % (ds, ("%g" % sg).replace(".", "_"))))
            res = M.run_external(str(EXE), [path, abs_sup, base], base + ".key",
                                 timeout=TIMEOUT_SECONDS, count_fn=count_keys)
            rc, cnt = res["returncode"], res["generator_count"]
            ok = not res["timed_out"] and rc in (0, cnt, cnt & 0xFF)
            err = "" if ok else ("timeout" if res["timed_out"] else
                                 "exit %s: %s" % (rc, (res["stderr"] or "")[-200:]))
            w.writerow({"algorithm": "GC_growth", "category": 1, "dataset": ds,
                        "param_name": "minsup", "param_value": sg,
                        "runtime_s": res["runtime_s"], "peak_memory_mb": res["peak_memory_mb"],
                        "generator_count": cnt if ok else "", "timed_out": res["timed_out"],
                        "error": err, "timestamp": time.strftime("%Y%m%d_%H%M%S"),
                        "source": "measured " + res["peak_source"],
                        "machine": "%s %s" % (platform.system(), platform.machine())})
            fh.flush()
            for ext in (".key", ".closed", ".pair"):
                try:
                    os.remove(base + ext)
                except OSError:
                    pass
            print("%-11s %-8g abs %-7d %8.3f s %9.2f MB %10s %s"
                  % (ds, sg, abs_sup, res["runtime_s"], res["peak_memory_mb"] or -1,
                     cnt if ok else "-", err), flush=True)


def compare():
    """GC-growth against Gr-growth and the per-configuration best (exact)."""
    import numpy as np
    g = pd.read_csv(OUT)
    e = pd.read_csv(_ROOT / "results" / "exact_memory.csv")
    e = e[e.source == "paper"]
    nl = pd.read_csv(_ROOT / "results" / "grgrowth_newline.csv")
    nl = nl[nl.source == "paper"]
    e = e.assign(rt=e.rerun_runtime_s.fillna(e.runtime_s_recorded))
    rows = []
    for r in g.itertuples():
        sub = e[(e.dataset == r.dataset) & np.isclose(e.param_value, r.param_value)]
        gr = sub[sub.algorithm == "Gr_growth"].iloc[0]
        m = nl[(nl.dataset == r.dataset) & np.isclose(nl.param_value, r.param_value)]
        gr_n = int(m.count_newline.iloc[0]) if len(m) else int(gr.generator_count)
        rows.append({"gc_mb": r.peak_memory_mb, "gc_rt": r.runtime_s, "gc_n": r.generator_count,
                     "gr_mb": gr.peak_memory_mb_exact, "gr_rt": gr.rt, "gr_n": gr_n,
                     "best_mb": sub.peak_memory_mb_exact.min(), "best_rt": sub.rt.min()})
    o = pd.DataFrame(rows)
    m, t = o.gc_mb / o.gr_mb, o.gc_rt / o.gr_rt
    rt_win = o[o.gc_rt < o.best_rt]
    mb_win = o[o.gc_mb < o.best_mb]
    big = o[o.best_rt > 0.1]
    lines = [
        "%d configurations; generator count equal to Gr-growth's on %d"
        % (len(o), int((o.gc_n == o.gr_n).sum())),
        "peak  GC-growth / Gr-growth: median %.2f, range %.2f-%.2f" % (m.median(), m.min(), m.max()),
        "time  GC-growth / Gr-growth: median %.2f, range %.2f-%.2f" % (t.median(), t.min(), t.max()),
        "below the per-configuration best peak on %d (by at most %.2f MB)"
        % (len(mb_win), (mb_win.best_mb - mb_win.gc_mb).max() if len(mb_win) else 0),
        "below the per-configuration best time on %d (by at most %.3f s)"
        % (len(rt_win), (rt_win.best_rt - rt_win.gc_rt).max() if len(rt_win) else 0),
        "where the best time exceeds 0.1 s (%d): GC-growth / best median %.2f"
        % (len(big), (big.gc_rt / big.best_rt).median()),
    ]
    text = "\n".join(lines) + "\n"
    print(text, end="")
    (_ROOT / "results" / "gcgrowth_compare.txt").write_text(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true")
    if not ap.parse_args().compare:
        main()
    compare()
