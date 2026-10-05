"""Re-measure every short completed run with the corrected memory monitor.

    python tools/remeasure.py --plan
    python tools/remeasure.py                  # ~70 min, sequential, < 1 GB typical

Why. Up to commit 594fd7a the monitor polled instantaneous RSS every 0.1 s
from a thread. A native miner that runs in 10-15 ms was read once, at spawn:
apriori on mushroom at 0.5 is recorded at 0.02 MB (Linux) and 2.48 MB
(Windows); measured properly it takes 3.7-4.2 MB. The memory labels the
performance model learned from, and the ones the new-dataset criteria were
scored on, are at that floor for every run this short. Taking the old
machine's own measured best and scoring it on this machine gave a memory
regret of 4.95x -- a criterion computed on such numbers cannot tell a good
recommender from a bad one.

What. Every COMPLETED run shorter than --max-runtime seconds, in
results/summary.csv (the training table, measured on Windows) and in
results/real_extra_summary.csv (the new datasets and calibration, Linux), is
run again --repeats times, one at a time, with the corrected monitor. Runs are
dispatched exactly as src/harness.py does. Each row keeps the recorded values
beside the new median and every repeat, so the change is auditable, and the
generator count is compared with the recorded one: a mismatch means the rerun
is not the same computation, and is reported rather than used.

The recorded tables are not modified. Output: results/remeasured.csv,
resume-safe (a row is written when its repeats finish).

Long runs are left as recorded. Above a few seconds the old monitor took
tens of readings, and the 0.1 s poll's error is small relative to the run;
the calibration runs put Linux/Windows JVM memory at 1.19x there, not 446x.
"""
import argparse
import csv
import glob
import os
import platform
import statistics
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

_jre = sorted(glob.glob(os.path.expanduser("~/.local/opt/jdk-*/bin")))
if _jre:
    os.environ["PATH"] = _jre[-1] + os.pathsep + os.environ.get("PATH", "")

import pandas as pd                                   # noqa: E402

from src import metrics as M                           # noqa: E402
from src.config import ALGORITHMS, GRGROWTH_K          # noqa: E402
from src.harness import COUNT_FUNCS, get_input_path    # noqa: E402

SOURCES = {"summary": _ROOT / "results" / "summary.csv",
           "extra": _ROOT / "results" / "real_extra_summary.csv"}
OUT = _ROOT / "results" / "remeasured.csv"
SCRATCH = _ROOT / "results" / "remeasure_scratch"
MACHINE = "%s %s" % (platform.system(), platform.machine())

FIELDS = ["source", "algorithm", "category", "dataset", "param_name", "param_value",
          "runtime_s_recorded", "peak_memory_mb_recorded", "generator_count_recorded",
          "runtime_s", "peak_memory_mb", "generator_count", "count_matches",
          "runtime_reps", "memory_reps", "failed_reps", "peak_source", "machine",
          "timestamp"]


def _completed(d):
    return (d.timed_out.astype(str).str.lower() != "true") & d.error.isna()


def _input_path(cfg, dataset):
    raw = _ROOT / "datasets" / "raw" / ("%s.txt" % dataset)
    try:
        return get_input_path(dataset, cfg["input_type"])
    except (FileNotFoundError, KeyError):
        if raw.exists():                   # the new datasets are not in config
            return str(raw)
        raise


def run_once(name, dataset, param_val, timeout):
    """One run, dispatched as src/harness.py dispatches it. -> result dict"""
    cfg = ALGORITHMS[name]
    path = _input_path(cfg, dataset)
    # One file per run. Named after the algorithm alone, two concurrent runs
    # of the same miner (tools/rerun_published.py runs two at a time) wrote to
    # and deleted the same file, and six Pascal runs were counted from
    # another run's output -- 0 or a fraction of the true generator count.
    out_file = str(SCRATCH / ("out_%s_%s_%s_%d.txt" % (
        name, dataset, ("%.10g" % param_val).replace(".", "_"), os.getpid())))
    count_fn = COUNT_FUNCS.get(cfg.get("count_fn"))
    exe, et = cfg.get("exe"), cfg.get("exe_type")
    if exe and et:
        n_tx = M.count_transactions(path)
        abs_sup = max(1, int(round(param_val * n_tx))) if param_val else 1
        if et == "grgrowth":
            base = out_file[:-4]
            res = M.run_external(exe, [path, abs_sup, GRGROWTH_K, base], base + ".txt",
                                 timeout=timeout, count_fn=M.count_grgrowth_generators)
            out_file = base + ".txt"
        elif et == "borgelt":
            res = M.run_external(exe, ["-tg", "-s%g" % (param_val * 100), path, out_file],
                                 out_file, timeout=timeout,
                                 count_fn=count_fn or M.count_borgelt_generators)
        elif et == "fgcstream":
            res = M.run_external(exe, [path, abs_sup, 0, out_file, n_tx], out_file,
                                 timeout=timeout, count_fn=M.count_fgcstream_generators)
        else:
            raise ValueError(et)
    else:
        # The tables hold every threshold as a float; SPMF's utility miners
        # want an Integer and, given "100.0", fail at exit 0 (src.metrics.
        # spmf_error). The first pass lost all 18 utility rows that way.
        if param_val is not None and float(param_val).is_integer() and param_val >= 1:
            param_val = int(param_val)
        params = [param_val] if param_val is not None else []
        res = M.run_spmf(cfg["spmf_name"], path, out_file, params,
                         timeout=timeout, count_fn=count_fn)
    try:
        os.remove(out_file)
    except OSError:
        pass
    return res


def _same_count(a, b):
    """Numeric comparison: the tables store some counts as '460357.0'."""
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def _failed(name, res):
    """As the benchmark decides it, conventions included: Gr-growth exits with
    its generator count (mod 256 on Linux), and Borgelt's miners exit 15 when
    nothing is frequent. The first pass of this tool ignored both and marked
    115 good runs as failed."""
    sys.path.insert(0, str(_ROOT / "tools"))
    from repair_summary import _conventional_exit
    if res.get("timed_out") or res.get("failure"):
        return True
    rc = res.get("returncode")
    if rc in (0, None):
        return False
    return not _conventional_exit(name, rc, res.get("generator_count"))


def plan(max_runtime):
    rows = []
    for src, path in SOURCES.items():
        d = pd.read_csv(path, dtype={"generator_count": str})
        c = d[_completed(d) & (d.runtime_s < max_runtime)]
        for r in c.itertuples():
            # Not runnable here (FGC-Stream ships a Windows binary only): its
            # recorded values stay, and it is listed as skipped.
            if r.algorithm not in ALGORITHMS or not ALGORITHMS[r.algorithm].get("available"):
                continue
            rows.append((src, r))
    return rows


def done_keys():
    if not OUT.exists():
        return set()
    d = pd.read_csv(OUT)
    return {(s, a, ds, round(float(p), 9)) for s, a, ds, p in
            zip(d.source, d.algorithm, d.dataset, d.param_value)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-runtime", type=float, default=30.0)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args(argv)

    import psutil
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
    SCRATCH.mkdir(parents=True, exist_ok=True)

    todo = plan(args.max_runtime)
    done = done_keys()
    todo = [(s, r) for s, r in todo
            if (s, r.algorithm, r.dataset, round(float(r.param_value), 9)) not in done]
    est = sum(r.runtime_s for _, r in todo) * args.repeats + 0.4 * len(todo) * args.repeats
    print("machine %s | java %s | peak source %s"
          % (MACHINE, _jre[-1] if _jre else "NOT FOUND", M.PEAK_SOURCE))
    print("%d runs to re-measure x %d repeats, estimated %.0f min (%d already done)"
          % (len(todo), args.repeats, est / 60, len(done)))
    if args.plan or not todo:
        return 0

    header = not OUT.exists()
    t0 = time.time()
    with open(OUT, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if header:
            w.writeheader()
        for i, (src, r) in enumerate(todo, 1):
            # A per-run timeout well above the recorded time: a rerun that is
            # suddenly 10x slower is a different computation, not noise.
            timeout = max(60, int(10 * r.runtime_s))
            reps, failed = [], 0
            for _ in range(args.repeats):
                try:
                    res = run_once(r.algorithm, r.dataset, float(r.param_value), timeout)
                except Exception as exc:                # noqa: BLE001
                    print("      repeat failed: %s: %s" % (type(exc).__name__, exc), flush=True)
                    failed += 1
                    continue
                if _failed(r.algorithm, res) or res.get("peak_memory_mb") is None:
                    failed += 1
                    continue
                reps.append(res)
            rts = [x["runtime_s"] for x in reps]
            mems = [x["peak_memory_mb"] for x in reps]
            counts = {str(x["generator_count"]) for x in reps}
            gc = counts.pop() if len(counts) == 1 else "|".join(sorted(counts))
            row = {"source": src, "algorithm": r.algorithm, "category": r.category,
                   "dataset": r.dataset, "param_name": r.param_name,
                   "param_value": r.param_value,
                   "runtime_s_recorded": r.runtime_s,
                   "peak_memory_mb_recorded": r.peak_memory_mb,
                   "generator_count_recorded": r.generator_count,
                   "runtime_s": statistics.median(rts) if rts else "",
                   "peak_memory_mb": statistics.median(mems) if mems else "",
                   "generator_count": gc if reps else "",
                   "count_matches": _same_count(gc, r.generator_count) if reps else "",
                   "runtime_reps": " ".join("%.4f" % x for x in rts),
                   "memory_reps": " ".join("%.2f" % x for x in mems),
                   "failed_reps": failed, "peak_source": M.PEAK_SOURCE,
                   "machine": MACHINE,
                   "timestamp": time.strftime("%Y%m%d_%H%M%S")}
            w.writerow(row)
            fh.flush()
            print("[%4d/%4d] %5.1f min | %-6s %-22s %-10s %-9s mem %8s -> %8s MB  %s"
                  % (i, len(todo), (time.time() - t0) / 60, src, r.algorithm, r.dataset,
                     ("%.6g" % r.param_value), r.peak_memory_mb,
                     ("%.2f" % row["peak_memory_mb"]) if reps else "FAIL",
                     "" if row["count_matches"] in (True, "") else "COUNT MISMATCH"),
                  flush=True)
    print("done: %d rows, %.1f min" % (len(todo), (time.time() - t0) / 60))
    return 0


if __name__ == "__main__":
    sys.exit(main())
