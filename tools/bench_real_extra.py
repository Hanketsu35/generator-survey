"""Benchmark five more REAL datasets, and measure what changing machines does.

Why. Every learning result in recommender/ is capped by the number of real
datasets: seven, 7.3 effective instances. The training jackknife showed the
selector ordering changing 11 times in 39 refits, which is that cap showing up
as instability. Synthetic instances could not lift it -- the generator spans the
feature space but permutes the algorithm ranking (NOTES section 7). More real
datasets are the remedy that does not have that problem.

Datasets, all from the SPMF public repository and checked on download to have
sorted, duplicate-free transactions (several SPMF miners assume both):

    kosarak   989,471 tx, 41,265 items, avg 8.1   -- very large, very sparse
    bms1       59,602 tx,    497 items, avg 2.5   -- clickstream, short
    bms2       77,512 tx,  3,340 items, avg 4.6   -- clickstream
    c20d10k    10,000 tx,    192 items, avg 20.0  -- census, dense
    c73d10k    10,000 tx,  1,592 items, avg 73.0  -- census, very dense

Thresholds are calibrated to DIFFICULTY, not fixed. For each dataset, sigma is
found by bisection on the landmark probe so that the number of frequent item
PAIRS hits 10, 100, 1,000, 5,000 and 20,000 -- the level-2 count being the
landmark that best predicted runtime in the feature ablation. A fixed relative
grid would put kosarak (41k items) and c20d10k (192 items) at incomparable
difficulties. A target is skipped when it needs sigma*|D| < 10, where the
instance degenerates: on c20d10k the 20,000-pair target lands at a support of 1
transaction, at which every subset of every transaction is "frequent".

Two roles, recorded per row:

``extension``   the new datasets, at calibrated thresholds.
``calibration`` configurations from results/summary.csv re-run here. The
                published table was measured sequentially on a Windows machine;
                these runs are on Linux, three at a time. Without re-running
                some of the original configurations, a difference between the
                old and new datasets could not be told apart from a difference
                between the machines. connect at 0.8 is among them: it is where
                Zart's published run turned out to be a silent crash.

Protocol matches the published table where it matters: 3600 s cutoff, JVM
default heap, the harness's 0.1 s memory-sampling interval. Output files are
deleted after counting. Rows go to results/real_extra_summary.csv, never to
results/summary.csv. The run is resume-safe: a machine that switches off loses
only the runs in flight.

    python tools/bench_real_extra.py --plan
    python tools/bench_real_extra.py --workers 3
"""
import argparse
import csv
import glob
import math
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

# Find the JRE the way HANDOFF installs it, rather than trusting the shell's
# PATH: after a reboot the shell that exported it is gone, and every SPMF run
# would fail with "java: not found" while looking like an ordinary crash.
_jre = sorted(glob.glob(os.path.expanduser("~/.local/opt/jdk-*/bin")))
if _jre:
    os.environ["PATH"] = _jre[-1] + os.pathsep + os.environ.get("PATH", "")

from recommender import landmarks as lm            # noqa: E402
from sweep_synthetic import category1_algorithms, run_one   # noqa: E402

RAW = _ROOT / "datasets" / "raw"
OUT_CSV = _ROOT / "results" / "real_extra_summary.csv"

EXTENSION = ("bms1", "bms2", "c20d10k", "kosarak", "c73d10k")   # cheap -> costly
PAIR_TARGETS = (10, 100, 1000, 5000, 20000)
MIN_ABS_SUPPORT = 10

#: Original configurations re-run here. Chosen to finish quickly on the old
#: machine for most algorithms, so the calibration costs little, plus connect
#: 0.8 for Zart.
CALIBRATION = [("mushroom", 0.2), ("mushroom", 0.3), ("mushroom", 0.5),
               ("chess", 0.8), ("connect", 0.9), ("connect", 0.8),
               ("retail", 0.01), ("t10i4d100k", 0.01)]

TIMEOUT = 3600
MONITOR_INTERVAL = 0.1           # the published table's sampling interval
MACHINE = "%s %s" % (platform.system(), platform.machine())

FIELDS = ["algorithm", "category", "dataset", "param_name", "param_value",
          "runtime_s", "peak_memory_mb", "generator_count", "timed_out",
          "error", "timestamp", "n_tx", "n_items", "target_pairs",
          "role", "machine"]


def sigma_for_pairs(probe, target):
    """Largest-support sigma giving about `target` frequent pairs (bisection)."""
    lo, hi = 1.0 / probe.n_tx, 1.0
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if 10 ** probe.at(mid)["log_n_freq2"] - 1 > target:
            lo = mid
        else:
            hi = mid
    return hi


def plan(datasets=EXTENSION, calibration=True, cap_reachable=False, targets=PAIR_TARGETS):
    """[(dataset, sigma, target_pairs or None, role, n_tx, n_items)]

    ``cap_reachable`` lowers each target to 90% of the pairs that can reach
    the minimum absolute support. Off by default, so the first extension's
    levels are reproduced exactly; on for attribute data (the second
    extension), where items of one attribute never co-occur and a fixed
    target of 5,000 or 20,000 pairs does not exist.
    """
    out = []
    if calibration:
        for ds, sg in CALIBRATION:
            out.append((ds, sg, None, "calibration", None, None))
    for ds in datasets:
        probe = lm.DatasetProbe.build(str(RAW / ("%s.txt" % ds)))
        seen = set()
        reachable = (10 ** probe.at((MIN_ABS_SUPPORT + 0.25) / probe.n_tx)["log_n_freq2"] - 1
                     if cap_reachable else float("inf"))
        for tg in targets:
            sg = sigma_for_pairs(probe, min(tg, 0.9 * reachable))
            # Bisection converges on the support of the pair that crosses the
            # target -- an INTEGER -- so sigma*|D| lands on an integer to within
            # one ulp. The first run of this benchmark put bms1 at
            # sigma*|D| = 34.00000000000001: ceil-based miners mined at 35
            # (118,696 generators), Gr-growth's round() at 34 (159,225), and
            # the "instance" was two different problems. Placing sigma*|D| at
            # s - 0.25 keeps it far from both integers and from .5, so ceil and
            # round agree on s and only DefMe's documented floor differs.
            s_abs = int(round(sg * probe.n_tx))
            if s_abs < MIN_ABS_SUPPORT:
                continue                        # degenerate: see module doc
            sg = (s_abs - 0.25) / probe.n_tx
            key = round(sg, 9)
            if key in seen:
                continue
            seen.add(key)
            out.append((ds, sg, tg, "extension", probe.n_tx, probe.n_items))
    return out


def done_keys(out_csv=OUT_CSV):
    keys = set()
    if out_csv.exists():
        with open(out_csv, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    keys.add((r["algorithm"], r["dataset"], round(float(r["param_value"]), 9)))
                except (KeyError, ValueError):
                    pass
    return keys


#: The native miners' address-space cap: the JVM default heap, a quarter of
#: physical RAM, so every implementation has the same memory budget. Without it
#: apriori reached 28.9 GB on bms1 and the OOM killer stopped the machine.
def _native_cap_mb():
    import psutil
    return int(psutil.virtual_memory().total / 4 / (1024 * 1024))


def job_runner(job):
    """run_one plus the columns this table adds."""
    from src import metrics as _m
    _m.NATIVE_MEM_LIMIT_MB = _native_cap_mb()
    target, role = job[-2], job[-1]
    row = run_one(job[:-2])
    row["target_pairs"] = target if target is not None else ""
    row["role"] = role
    row["machine"] = MACHINE
    row.pop("target_frac", None)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=3,
                    help="concurrent runs. Each JVM may take a quarter of RAM by "
                         "default, so 3 keeps the worst case under 30 GB")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--datasets", nargs="+", default=list(EXTENSION))
    ap.add_argument("--out", default=str(OUT_CSV))
    ap.add_argument("--no-calibration", action="store_true")
    ap.add_argument("--cap-reachable", action="store_true",
                    help="see plan(); used for the second extension")
    ap.add_argument("--targets", type=int, nargs="+", default=list(PAIR_TARGETS),
                    help="pair targets to run (default: all five levels)")
    ap.add_argument("--timeout", type=float, default=TIMEOUT)
    args = ap.parse_args(argv)
    os.chdir(_ROOT)
    out_csv = Path(args.out)
    order = list(args.datasets)

    algos = category1_algorithms()
    instances = plan(order, calibration=not args.no_calibration,
                     cap_reachable=args.cap_reachable, targets=args.targets)
    done = done_keys(out_csv)
    jobs = []
    # Easiest difficulty level of EVERY dataset first, hardest last. Dataset by
    # dataset, the first run spent two hours on bms1's two hardest levels while
    # four datasets had not started: there the JVM miners run to the 3600 s
    # cutoff, and an instance where any of them does is excluded from the memory
    # evaluation -- the one objective with headroom -- so those hours bought
    # nothing it can use. Nothing is dropped; the order changes.
    instances = sorted(instances, key=lambda i: (i[3] != "calibration",
                                                 i[2] or 0, order.index(i[0])
                                                 if i[0] in order else -1))
    for ds, sg, tg, role, n_tx, n_items in instances:
        if n_tx is None:
            from recommender import metafeatures as mf
            f = mf.for_dataset(ds)
            n_tx, n_items = f["n_tx"], f["n_items"]
        for name, c in algos:
            if (name, ds, round(sg, 9)) in done:
                continue
            jobs.append((name, c, str(RAW / ("%s.txt" % ds)), ds, sg, None,
                         n_tx, n_items, args.timeout, 0, MONITOR_INTERVAL, tg, role))

    print("machine: %s | java: %s" % (MACHINE, _jre[-1] if _jre else "NOT FOUND"))
    print("%d instances (%d calibration, %d extension) x %d algorithms"
          % (len(instances), sum(i[3] == "calibration" for i in instances),
             sum(i[3] == "extension" for i in instances), len(algos)))
    for ds, sg, tg, role, _, _ in instances:
        print("   %-11s %-10s sigma %.6f%s"
              % (role, ds, sg, "   (target %d pairs)" % tg if tg else ""))
    print("runs to execute: %d  (%d already recorded)" % (len(jobs), len(done)))
    if args.plan or not jobs:
        return 0

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    header = not out_csv.exists()
    t0 = time.time()
    n = n_to = n_err = 0
    with open(out_csv, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if header:
            w.writeheader()
        with ProcessPoolExecutor(max_workers=args.workers,
                                 max_tasks_per_child=1) as pool:
            futs = [pool.submit(job_runner, j) for j in jobs]
            for fut in as_completed(futs):
                row = fut.result()
                w.writerow(row)
                fh.flush()
                n += 1
                n_to += bool(row["timed_out"])
                n_err += bool(row["error"])
                print("[%3d/%3d] %5.1f min | %-20s %-10s %.6f  %8.1fs  %s"
                      % (n, len(jobs), (time.time() - t0) / 60, row["algorithm"],
                         row["dataset"], row["param_value"],
                         row["runtime_s"] or 0,
                         "TIMEOUT" if row["timed_out"] else (row["error"] or "ok")),
                      flush=True)
    print("done: %d runs, %d timeouts, %d errors, %.1f h"
          % (n, n_to, n_err, (time.time() - t0) / 3600))
    return 0


if __name__ == "__main__":
    sys.exit(main())
