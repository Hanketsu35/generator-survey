"""Re-measure peak memory exactly (tools/peakrun, wait4) for every completed
run under --max-runtime seconds, in every table.

    python tools/remeasure_exact.py --plan
    python tools/remeasure_exact.py --workers 2

Why: polled VmHWM read 0.02-0.6 MB for 3-5 ms runs whose exact peak is
2.7-3.4 MB, and missed end-of-run peaks by 6-7% on ~1 s runs
(results/peak_method_check.csv). The exact reading is stable (five repeats
within 0.5 MB), so each run is measured once. The generator count is checked
against the recorded one; a mismatch is reported and the row not used.
Runtimes are not replaced: concurrency would bias them, and the polled
method measured them correctly.

Order: the paper's table first, then the recommender's.
Output: results/exact_memory.csv, resume-safe. Recorded tables untouched.
"""
import argparse
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import pandas as pd                                        # noqa: E402

import remeasure as R                                      # noqa: E402

SOURCES = {"paper": "results/summary_linux.csv",
           "ext1": "results/real_extra_summary.csv",
           "ext2": "results/real_extra2_summary.csv",
           "confirm": "results/real_extra3_summary.csv",
           "hard": "results/hard_summary.csv",
           "fresh": "results/fresh_summary.csv",
           "fresh2": "results/fresh2_summary.csv",
           "fresh3": "results/fresh3_summary.csv",
           "fresh4": "results/fresh4_summary.csv"}
OUT = _ROOT / "results" / "exact_memory.csv"
FIELDS = ["source", "algorithm", "category", "dataset", "param_value", "runtime_s_recorded",
          "peak_memory_mb_recorded", "generator_count_recorded", "peak_memory_mb_exact",
          "peak_source", "generator_count", "count_matches", "rerun_runtime_s", "note"]


def plan(max_runtime):
    out = []
    for src, path in SOURCES.items():
        d = pd.read_csv(_ROOT / path, dtype={"generator_count": str})
        c = d[R._completed(d) & (d.runtime_s < max_runtime)]
        for r in c.itertuples():
            if r.algorithm in R.ALGORITHMS and R.ALGORITHMS[r.algorithm].get("available"):
                out.append((src, r.algorithm, int(getattr(r, "category", 1) or 1), r.dataset,
                            float(r.param_value), float(r.runtime_s), r.peak_memory_mb,
                            r.generator_count))
    return out


def job(t):
    import psutil
    from src import metrics as M
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
    R.SCRATCH.mkdir(parents=True, exist_ok=True)
    src, algo, cat, ds, p, rt, mem, gc = t
    row = {"source": src, "algorithm": algo, "category": cat, "dataset": ds, "param_value": p,
           "runtime_s_recorded": rt, "peak_memory_mb_recorded": mem,
           "generator_count_recorded": gc, "note": ""}
    try:
        res = R.run_once(algo, ds, p, max(60, int(3 * rt) + 30))
    except Exception as exc:                                # noqa: BLE001
        row["note"] = "%s: %s" % (type(exc).__name__, exc)
        return row
    if R._failed(algo, res):
        row["note"] = "rerun failed: %s" % ("timeout" if res.get("timed_out") else
                                            (res.get("stderr") or "")[-120:].replace("\n", " "))
        return row
    row.update(peak_memory_mb_exact=res["peak_memory_mb"], peak_source=res["peak_source"],
               generator_count=res["generator_count"], rerun_runtime_s=res["runtime_s"],
               count_matches=R._same_count(res["generator_count"], gc))
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-runtime", type=float, default=600.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args(argv)
    todo = plan(args.max_runtime)
    done = set()
    if OUT.exists():
        d = pd.read_csv(OUT)
        done = {(a, b, c, round(float(e), 9)) for a, b, c, e in
                zip(d.source, d.algorithm, d.dataset, d.param_value)}
    todo = [t for t in todo if (t[0], t[1], t[3], round(t[4], 9)) not in done]
    by = pd.Series([t[0] for t in todo]).value_counts().to_dict() if todo else {}
    print("%d runs to re-measure (%d done) %s, recorded runtime %.1f h"
          % (len(todo), len(done), by, sum(t[5] for t in todo) / 3600), flush=True)
    if args.plan or not todo:
        return 0
    header = not OUT.exists()
    t0 = time.time()
    with open(OUT, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if header:
            w.writeheader()
        with ProcessPoolExecutor(max_workers=args.workers, max_tasks_per_child=1) as ex:
            futs = [ex.submit(job, t) for t in todo]
            for i, f in enumerate(as_completed(futs), 1):
                row = f.result()
                w.writerow(row)
                fh.flush()
                print("[%5d/%5d] %6.1f min | %-7s %-22s %-14s %-10.6g %9s -> %9s %s%s"
                      % (i, len(todo), (time.time() - t0) / 60, row["source"], row["algorithm"],
                         row["dataset"], row["param_value"], row["peak_memory_mb_recorded"],
                         row.get("peak_memory_mb_exact", "-"),
                         "" if row.get("count_matches") in (True, None, "") else "COUNT MISMATCH ",
                         row["note"]), flush=True)
    print("done in %.1f h" % ((time.time() - t0) / 3600))
    return 0


if __name__ == "__main__":
    sys.exit(main())
