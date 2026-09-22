"""Benchmark the synthetic grid, to raise the effective instance count.

Why this exists
---------------
Instance space analysis measured the benchmark's central limitation: ten of the
eleven meta-features are properties of the dataset, so the 58 transactional
configurations occupy seven distinct locations in the plane and 95.6% of
positional variance lies between datasets. Under the cluster-sampling design
effect, ``n_eff = n / (1 + (m-1) * ICC)``, that is an effective instance count
of **7.3**. Adding threshold-dependent landmark features (``recommender/
landmarks.py``) lowers the ICC to 0.622, which raises it only to 10.5. No model
and no feature set repairs a meta-instance set of that size; more instances are
the only remedy, which is what ``recommender/synth.py`` generates and what this
script measures.

Two invariants
--------------
1.  **Synthetic runs never enter ``results/summary.csv``.** They are written to
    ``results/synthetic_summary.csv``. The survey's empirical claims are about
    real data and must stay traceable to real runs, and the evaluation protocol
    requires that the held-out instance always be a real dataset -- holding out
    a synthetic one measures the generator, not the miner.

2.  **Thresholds are calibrated per dataset, not fixed.** A fixed relative grid
    is not comparable across datasets: the real benchmark runs retail at
    sigma = 0.0005 and pumsb at 0.95, and sigma = 0.3 is trivial on mushroom
    while near the hardest point of accidents. Here each dataset is instead run
    at the sigma that makes a *target fraction of its items frequent*, which is
    exact rather than searched -- with item supports sorted descending,

        sigma_k = sup_sorted[k - 1] / n_tx   makes exactly k items frequent.

    Instances are then comparable by construction, and ``log_thr`` stops being
    an uninterpretable axis.

Cost control
------------
Output files are deleted after counting (``--keep-output-mb 0``): the count is
the only thing the analysis reads, and retaining output is what made
``results/raw`` 11 GB for 667 runs. Per-run JSON is about 1 KB.

    python tools/sweep_synthetic.py --plan            # cost estimate, runs nothing
    python tools/sweep_synthetic.py --pilot 6         # timing probe
    python tools/sweep_synthetic.py --workers 6       # the sweep
"""
import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src import config as cfg
from src import metrics as _metrics
from src.metrics import (run_spmf, run_external, count_transactions,
                         count_plain_lines, count_pascal_generators,
                         count_zart_generators, count_borgelt_generators,
                         count_grgrowth_generators)
from recommender import synth
from recommender import landmarks as lm

SYN_DIR = _ROOT / "datasets" / "synthetic"
OUT_CSV = _ROOT / "results" / "synthetic_summary.csv"
SCRATCH = _ROOT / "results" / "synthetic_scratch"

COUNT_FNS = {
    "pascal": count_pascal_generators,
    "zart": count_zart_generators,
    "borgelt": count_borgelt_generators,
}

#: Fractions of the item vocabulary that must be frequent. Chosen to keep the
#: level-1 sub-problem moderate -- the point is coverage of the feature space,
#: not reproducing the hardest instances, and every censored run costs the full
#: timeout without adding a location to the plane.
TARGET_FREQ_FRACTIONS = (0.02, 0.05, 0.12, 0.25)

FIELDS = ["algorithm", "category", "dataset", "param_name", "param_value",
          "runtime_s", "peak_memory_mb", "generator_count", "timed_out",
          "error", "timestamp", "n_tx", "n_items", "target_frac"]


# ----------------------------------------------------------------------
def category1_algorithms():
    """The nine executable transactional implementations, in a stable order."""
    out = []
    for name, c in cfg.ALGORITHMS.items():
        if c.get("category") == 1 and c.get("available") and "minsup" in c.get("params", []):
            out.append((name, c))
    return sorted(out)


def calibrated_thresholds(path, fractions=TARGET_FREQ_FRACTIONS):
    """sigma values making a target fraction of items frequent. Exact, not searched.

    Returns ``[(sigma, target_fraction, n_freq1), ...]`` with duplicates removed,
    which happens on small vocabularies where two fractions round to the same
    item count.
    """
    probe = lm.DatasetProbe.build(str(path), "transactional")
    sup = np.sort(probe.sup)[::-1]           # descending item supports
    n_tx, n_items = probe.n_tx, probe.n_items
    seen, out = set(), []
    for f in fractions:
        k = int(round(f * n_items))
        k = max(1, min(k, n_items))
        sigma = float(sup[k - 1]) / n_tx
        # Nudge below the exact support so the k-th item is included rather
        # than sitting exactly on the boundary, where >= vs > conventions differ
        # between implementations.
        sigma = max(sigma * 0.999, 1.0 / n_tx)
        key = round(sigma, 9)
        if key in seen:
            continue
        seen.add(key)
        out.append((sigma, f, k))
    return out, n_tx, n_items


# ----------------------------------------------------------------------
def run_one(job):
    """Execute one (dataset, sigma, algorithm) run. Returns a summary row."""
    (name, c, ds_path, ds_name, sigma, frac, n_tx, n_items, timeout, keep_mb,
     mon_interval) = job
    os.chdir(_ROOT)
    # Set inside the worker rather than relying on fork inheritance: the native
    # miners here run in about 10 ms, which the harness default of 0.1 s samples
    # at most once.
    _metrics.MONITOR_INTERVAL = mon_interval
    SCRATCH.mkdir(parents=True, exist_ok=True)
    tag = "%s_%s_%s" % (name, ds_name, ("%.8f" % sigma).replace(".", "_"))
    out_file = str(SCRATCH / ("out_%s.txt" % tag))
    count_fn = COUNT_FNS.get(c.get("count_fn"))

    try:
        if c.get("exe"):
            exe, et = c["exe"], c.get("exe_type")
            if et == "grgrowth":
                base = out_file[:-4]
                res = run_external(exe, [ds_path, max(1, int(round(sigma * n_tx))),
                                         cfg.GRGROWTH_K, base],
                                   base + ".txt", timeout=timeout,
                                   count_fn=count_grgrowth_generators)
                out_file = base + ".txt"
            elif et == "borgelt":
                res = run_external(exe, ["-tg", "-s%g" % (sigma * 100), ds_path, out_file],
                                   out_file, timeout=timeout,
                                   count_fn=count_fn or count_borgelt_generators)
            else:
                raise ValueError("unexpected exe_type %r" % et)
        else:
            res = run_spmf(c["spmf_name"], ds_path, out_file, [sigma],
                           timeout=timeout, count_fn=count_fn)
    except Exception as exc:                        # noqa: BLE001
        res = {"runtime_s": None, "peak_memory_mb": None, "generator_count": 0,
               "timed_out": False, "error": "%s: %s" % (type(exc).__name__, exc)}

    # Discard the output; the count is all the analysis needs.
    try:
        p = Path(out_file)
        if p.exists() and (keep_mb == 0 or p.stat().st_size > keep_mb * 1024 * 1024):
            p.unlink()
        fbd = Path(out_file.replace(".txt", ".fbd"))
        if fbd.exists():
            fbd.unlink()
    except OSError:
        pass

    return {"algorithm": name, "category": 1, "dataset": ds_name,
            "param_name": "minsup", "param_value": sigma,
            "runtime_s": res.get("runtime_s"),
            "peak_memory_mb": res.get("peak_memory_mb"),
            "generator_count": res.get("generator_count"),
            "timed_out": bool(res.get("timed_out")),
            "error": res.get("error") or "",
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
            "n_tx": n_tx, "n_items": n_items, "target_frac": frac}


# ----------------------------------------------------------------------
def already_done():
    """(algorithm, dataset, rounded sigma) triples already in the output CSV."""
    done = set()
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    done.add((r["algorithm"], r["dataset"], round(float(r["param_value"]), 9)))
                except (KeyError, ValueError):
                    continue
    return done


def build_jobs(paths, algos, timeout, keep_mb, done, mon_interval=0.01,
               verbose=True):
    jobs, n_inst = [], 0
    for p in paths:
        ds_name = p.stem
        thr, n_tx, n_items = calibrated_thresholds(p)
        n_inst += len(thr)
        if verbose:
            print("  %-46s %6d tx x %5d items | sigma %s"
                  % (ds_name, n_tx, n_items,
                     " ".join("%.4g" % s for s, _, _ in thr)))
        for sigma, frac, _k in thr:
            for name, c in algos:
                if (name, ds_name, round(sigma, 9)) in done:
                    continue
                jobs.append((name, c, str(p), ds_name, sigma, frac,
                             n_tx, n_items, timeout, keep_mb, mon_interval))
    return jobs, n_inst


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6,
                    help="parallel runs; each JVM run can hold ~1-2 GB")
    ap.add_argument("--timeout", type=int, default=300,
                    help="per-run cutoff in seconds (the real benchmark uses 3600)")
    ap.add_argument("--keep-output-mb", type=int, default=0,
                    help="0 deletes every output file after counting")
    ap.add_argument("--pilot", type=int, default=0,
                    help="benchmark only the first N synthetic datasets")
    ap.add_argument("--limit", type=int, help="cap the number of grid datasets")
    ap.add_argument("--monitor-interval", type=float, default=0.01,
                    help="peak-RSS sampling interval; the harness default is 0.1")
    ap.add_argument("--plan", action="store_true",
                    help="print the plan and estimated cost, run nothing")
    ap.add_argument("--generate-only", action="store_true")
    args = ap.parse_args(argv)

    os.chdir(_ROOT)
    algos = category1_algorithms()
    specs = synth.grid_specs(limit=args.limit)
    # --pilot benchmarks a prefix of the grid, so it must also generate only
    # that prefix; otherwise a "pilot" pays the full 28-minute generation cost
    # before running a single miner.
    if args.pilot:
        specs = specs[:args.pilot]

    # --- generate ----------------------------------------------------
    SYN_DIR.mkdir(parents=True, exist_ok=True)
    missing = [(nm, kw) for nm, kw in specs
               if not (SYN_DIR / (nm + ".txt")).exists()]
    if missing and not args.plan:
        print("generating %d synthetic datasets into %s" % (len(missing), SYN_DIR))
        t0 = time.time()
        for i, (nm, kw) in enumerate(missing, 1):
            synth.write(str(SYN_DIR / (nm + ".txt")), **kw)
            if i % 20 == 0 or i == len(missing):
                print("  [%3d/%3d] %.1f min elapsed" % (i, len(missing), (time.time() - t0) / 60))
    if args.generate_only:
        return 0

    paths = [SYN_DIR / (nm + ".txt") for nm, _ in specs]
    paths = [p for p in paths if p.exists()]
    if args.pilot:
        paths = paths[:args.pilot]

    print()
    print("=" * 78)
    print("SYNTHETIC SWEEP PLAN")
    print("=" * 78)
    print("  %d datasets x calibrated thresholds x %d algorithms"
          % (len(paths), len(algos)))
    print("  algorithms: %s" % ", ".join(n for n, _ in algos))
    print("  timeout %ds | workers %d | output retained: %s"
          % (args.timeout, args.workers,
             "no" if args.keep_output_mb == 0 else "%d MB cap" % args.keep_output_mb))
    print()
    done = already_done()
    jobs, n_inst = build_jobs(paths, algos, args.timeout, args.keep_output_mb,
                              done, mon_interval=args.monitor_interval,
                              verbose=args.plan or args.pilot > 0)
    print()
    print("  instances (dataset x sigma): %d" % n_inst)
    print("  runs to execute: %d  (%d already recorded)" % (len(jobs), len(done)))
    print("  worst case if every run hits the cutoff: %.1f h"
          % (len(jobs) * args.timeout / 3600.0 / max(args.workers, 1)))
    if args.plan:
        return 0
    if not jobs:
        print("  nothing to do")
        return 0

    # --- execute -----------------------------------------------------
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not OUT_CSV.exists()
    t0 = time.time()
    n_done = n_to = n_err = 0
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        # One task per worker process, so that the kernel's RUSAGE_CHILDREN peak
        # is attributable to exactly one run (see src/metrics.peak_rss_mb). The
        # counter is a high-water mark over every child a process has reaped, so
        # a reused worker would report a small run's memory as the largest run it
        # had previously executed. Process startup is ~30 ms against run times
        # that matter, and it isolates memory between runs as a side benefit.
        with ProcessPoolExecutor(max_workers=args.workers,
                                 max_tasks_per_child=1) as pool:
            futs = {pool.submit(run_one, j): j for j in jobs}
            for fut in as_completed(futs):
                row = fut.result()
                w.writerow(row)
                fh.flush()
                n_done += 1
                n_to += bool(row["timed_out"])
                n_err += bool(row["error"])
                if n_done % 25 == 0 or n_done == len(jobs):
                    el = time.time() - t0
                    rate = n_done / max(el, 1e-9)
                    print("  [%5d/%5d] %5.1f min elapsed | %.2f runs/s | "
                          "eta %5.1f min | %d timeouts %d errors"
                          % (n_done, len(jobs), el / 60, rate,
                             (len(jobs) - n_done) / max(rate, 1e-9) / 60, n_to, n_err),
                          flush=True)

    print()
    print("  wrote %s" % OUT_CSV)
    print("  %d runs in %.1f min | %d timed out | %d errors"
          % (n_done, (time.time() - t0) / 60, n_to, n_err))
    try:
        SCRATCH.rmdir()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
