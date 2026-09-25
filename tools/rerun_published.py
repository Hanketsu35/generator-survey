"""Re-run, on this machine, every published run that re-measurement did not cover.

    python tools/rerun_published.py --plan
    python tools/rerun_published.py --workers 2     # ~1.5 days; worst case ~16 GB

Why. The paper reports results/summary.csv, measured on Windows. Its short
runs (under 30 s) were re-measured here by tools/remeasure.py; the rest --
long completed runs, the 65 timeouts, the crashes, and FGC-Stream, whose
Windows-only binary could not run here until it was compiled from the
tracked source -- are still Windows numbers. A table that mixes two machines
cannot be reported as one measurement, so these are re-run under the
published protocol: one run each, 3600 s cutoff, JVM default heap, the
corrected memory monitor, native address space capped at a quarter of RAM.

Two workers, not the published table's one: the difference is reported with
the results and checked against the calibration runs.

Every completed rerun's generator count is compared with the recorded one;
a mismatch is reported, never silently used. Output:
results/published_linux_rerun.csv (resume-safe), ordered shortest recorded
run first so that the timeouts, which dominate the cost, come last.

FGC-Stream on Linux: `g++ -O2 -std=c++17 -include cstdint -o
FGC_Stream_release *.cpp` in external_algos/FGC_Stream/FGC-Stream/ (the
source omits <cstdint>, as Gr-growth's did; the header is injected rather
than the vendored source edited).
"""
import argparse
import csv
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import pandas as pd                                      # noqa: E402

import remeasure as R                                    # noqa: E402


def _key(a, d, p):
    return (a, d, round(float(p), 9))

TRAINING = _ROOT / "results" / "training_runs.csv"
OUT = _ROOT / "results" / "published_linux_rerun.csv"
TIMEOUT = 3600
MACHINE = "%s %s" % (platform.system(), platform.machine())
FIELDS = ["algorithm", "category", "dataset", "param_name", "param_value",
          "runtime_s", "peak_memory_mb", "generator_count", "timed_out", "error",
          "runtime_s_recorded", "peak_memory_mb_recorded", "generator_count_recorded",
          "timed_out_recorded", "error_recorded", "count_matches", "peak_source",
          "machine", "timestamp"]


def todo():
    t = pd.read_csv(TRAINING, dtype={"generator_count": str})
    s = t[(t.source_table == "summary") & (t.measured == "recorded")]
    rec = pd.read_csv(R.SOURCES["summary"], dtype={"generator_count": str})
    s = s.merge(rec[["algorithm", "dataset", "param_value", "runtime_s", "peak_memory_mb",
                     "generator_count", "timed_out", "error"]],
                on=["algorithm", "dataset", "param_value"], suffixes=("", "_recorded"))
    return s.sort_values("runtime_s_recorded", na_position="last")


def one(row):
    """Run one configuration. Top-level so the pool can pickle it."""
    import psutil
    from src import metrics as M
    from sweep_synthetic import _failure_label
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
    try:
        res = R.run_once(row["algorithm"], row["dataset"], float(row["param_value"]), TIMEOUT)
        err = _failure_label(row["algorithm"], res)
    except Exception as exc:                            # noqa: BLE001
        res, err = {"runtime_s": None, "peak_memory_mb": None, "generator_count": None,
                    "timed_out": False}, "%s: %s" % (type(exc).__name__, exc)
    ok = not res.get("timed_out") and not err
    rec_ok = (str(row["timed_out_recorded"]).lower() != "true"
              and pd.isna(row["error_recorded"]))
    match = (R._same_count(res.get("generator_count"), row["generator_count_recorded"])
             if ok and rec_ok else "")
    return {"algorithm": row["algorithm"], "category": row["category"],
            "dataset": row["dataset"], "param_name": row["param_name"],
            "param_value": row["param_value"], "runtime_s": res.get("runtime_s"),
            "peak_memory_mb": res.get("peak_memory_mb"),
            "generator_count": res.get("generator_count") if ok else "",
            "timed_out": bool(res.get("timed_out")), "error": err or "",
            "runtime_s_recorded": row["runtime_s_recorded"],
            "peak_memory_mb_recorded": row["peak_memory_mb_recorded"],
            "generator_count_recorded": row["generator_count_recorded"],
            "timed_out_recorded": row["timed_out_recorded"],
            "error_recorded": row["error_recorded"] if pd.notna(row["error_recorded"]) else "",
            "count_matches": match, "peak_source": M.PEAK_SOURCE, "machine": MACHINE,
            "timestamp": time.strftime("%Y%m%d_%H%M%S")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args(argv)
    t = todo()
    done = set()
    if OUT.exists():
        d = pd.read_csv(OUT)
        done = {_key(a, ds, p) for a, ds, p in zip(d.algorithm, d.dataset, d.param_value)}
    t = t[[_key(a, ds, p) not in done for a, ds, p in zip(t.algorithm, t.dataset, t.param_value)]]
    to = (t.timed_out_recorded.astype(str).str.lower() == "true").sum()
    print("machine %s | %d runs to re-run (%d already done): %d recorded timeouts, "
          "%d recorded errors, %d completed"
          % (MACHINE, len(t), len(done), to, t.error_recorded.notna().sum(),
             len(t) - to - t.error_recorded.notna().sum()))
    print(t.algorithm.value_counts().to_string())
    if args.plan or t.empty:
        return 0
    rows = t.to_dict("records")
    header = not OUT.exists()
    t0 = time.time()
    with open(OUT, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if header:
            w.writeheader()
        with ProcessPoolExecutor(max_workers=args.workers, max_tasks_per_child=1) as pool:
            futs = [pool.submit(one, r) for r in rows]
            for i, f in enumerate(as_completed(futs), 1):
                row = f.result()
                w.writerow(row)
                fh.flush()
                print("[%3d/%3d] %6.1f min | %-22s %-11s %-8s %8.1fs  %s%s"
                      % (i, len(rows), (time.time() - t0) / 60, row["algorithm"],
                         row["dataset"], row["param_value"], row["runtime_s"] or 0,
                         "TIMEOUT" if row["timed_out"] else (row["error"][:60] or "ok"),
                         "  COUNT MISMATCH" if row["count_matches"] is False else ""),
                      flush=True)
    print("done: %d runs, %.1f h" % (len(rows), (time.time() - t0) / 3600))
    return 0


if __name__ == "__main__":
    sys.exit(main())
