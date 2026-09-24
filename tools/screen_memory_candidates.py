"""Screen candidate real datasets for memory disagreement before benchmarking them.

    python tools/screen_memory_candidates.py --prepare   # normalise into datasets/raw
    python tools/screen_memory_candidates.py --plan
    python tools/screen_memory_candidates.py             # the screening runs

Why. Re-measured, the recommender's leave-one-dataset-out test ties the
fixed choice, and the reason is in the data rather than the model: on most
instances every miner's peak memory lies within a few megabytes of every
other's. The instances where memory choice pays are few and specific --
many transactions (kosarak, accidents, t10i4d100k: Gr-growth 14-40 MB where
Apriori takes 60-80 MB) and dense data at low support (chess 0.2: DefMe 575
MB, Apriori 866 MB). A full benchmark of a dataset costs hours; this pass
costs minutes and says whether a dataset belongs to that group.

SELECTION RULE, fixed before any screening run: a dataset QUALIFIES if at
one of its screening levels, among the miners that completed,

    Apriori's peak memory / the lowest peak memory  >= 1.5    and
    Apriori's peak memory - the lowest peak memory  >= 10 MB

The ratio says selection matters (Apriori is the pre-registered fixed
choice); the absolute gap says the difference is measurable, not a
floor-level artefact. Qualifying is a statement about memory disagreement
and nothing else; which datasets qualify is reported with the rule, since
choosing datasets where selection matters is the purpose, and a reader
must know the choice was made.

Candidates: the transactional itemset files in the SPMF public dataset
collection not already benchmarked, downloaded to datasets/candidates/.
Excluded on format: e_shop, online_retail_II (sequences), liquor_11
(utilities), mooc (timestamped sequences).

Normalisation (--prepare), logged per dataset: items sorted within each
transaction, duplicates removed, empty lines dropped. An empty line is a
transaction to some miners and not to others, which changes every relative
support; sorting changes no itemset.

Screening: levels calibrated like tools/bench_real_extra.py (frequent-pair
targets 100 and 5000, sigma*|D| placed at s - 0.25); a target above 90% of
the pairs that can reach support 10 is lowered to that, because on attribute
data items of one attribute never co-occur. Miners: the four native ones and DefMe (the JVM
miner that wins memory on dense data). 300 s timeout, one run at a time,
native address space capped at a quarter of RAM, corrected memory monitor.
Output: results/memory_screen.csv (resume-safe).
"""
import argparse
import csv
import glob
import math
import os
import platform
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

_jre = sorted(glob.glob(os.path.expanduser("~/.local/opt/jdk-*/bin")))
if _jre:
    os.environ["PATH"] = _jre[-1] + os.pathsep + os.environ.get("PATH", "")

from recommender import landmarks as lm                  # noqa: E402
from sweep_synthetic import category1_algorithms, run_one  # noqa: E402

CAND = _ROOT / "datasets" / "candidates"
RAW = _ROOT / "datasets" / "raw"
OUT = _ROOT / "results" / "memory_screen.csv"
PREP_LOG = _ROOT / "results" / "memory_screen_prepare.txt"

#: candidate file -> name used in datasets/raw and every table
CANDIDATES = {
    "chainstoreFIM": "chainstore_fim",
    "Chicago_Crimes_2001_to_2017_FIM": "chicago",
    "fruithut_original": "fruithut",
    "instacart_trainFIM": "instacart",
    "kddcup99": "kddcup99",
    "OnlineRetailZZ": "onlineretail",
    "PAMAP": "pamap",
    "RecordLink": "recordlink",
    "Skin": "skin",
    "t20i6d100k": "t20i6d100k",
}
TARGETS = (100, 5000)
SCREEN_ALGOS = ("Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt",
                "Gr_growth", "DefMe")
TIMEOUT = 300
MIN_ABS = 10
RATIO, GAP_MB = 1.5, 10.0
MACHINE = "%s %s" % (platform.system(), platform.machine())
FIELDS = ["dataset", "param_value", "target_pairs", "algorithm", "runtime_s",
          "peak_memory_mb", "generator_count", "timed_out", "error", "n_tx",
          "n_items", "machine", "timestamp"]


def prepare():
    lines_out = []
    for src, name in CANDIDATES.items():
        n = unsorted = dups = empty = 0
        dst = RAW / ("%s.txt" % name)
        with open(CAND / ("%s.txt" % src)) as fi, open(dst, "w") as fo:
            for line in fi:
                s = line.strip()
                if not s or s[0] in "#@%":
                    empty += not s
                    continue
                t = [int(x) for x in s.split()]
                u = sorted(set(t))
                unsorted += t != sorted(t)
                dups += len(u) != len(t)
                fo.write(" ".join(map(str, u)) + "\n")
                n += 1
        msg = ("%-16s from %-34s %9d tx | re-sorted %d, de-duplicated %d, empty lines "
               "dropped %d" % (name, src + ".txt", n, unsorted, dups, empty))
        print(msg)
        lines_out.append(msg)
    PREP_LOG.write_text("\n".join(lines_out) + "\n")


def levels(name):
    probe = lm.DatasetProbe.build(str(RAW / ("%s.txt" % name)))
    n_items = probe.n_items
    # The pairs that CAN become frequent: those reaching the minimum absolute
    # support of 10. On attribute data (kddcup99, pamap, recordlink, skin)
    # items of one attribute never co-occur, so "all pairs" is unreachable and
    # a fixed target of 5000 may be too; 90% of the reachable count keeps the
    # bisection off the degenerate bottom.
    reachable = 10 ** probe.at((MIN_ABS + 0.25) / probe.n_tx)["log_n_freq2"] - 1
    out, seen = [], set()
    for tg in TARGETS:
        goal = min(tg, 0.9 * reachable)
        lo, hi = 1.0 / probe.n_tx, 1.0
        for _ in range(60):
            mid = math.sqrt(lo * hi)
            if 10 ** probe.at(mid)["log_n_freq2"] - 1 >= goal:
                lo = mid
            else:
                hi = mid
        sg = lo
        s_abs = int(round(sg * probe.n_tx))
        if s_abs < MIN_ABS:
            continue
        sg = (s_abs - 0.25) / probe.n_tx
        if round(sg, 9) in seen:
            continue
        seen.add(round(sg, 9))
        out.append((sg, tg))
    return out, probe.n_tx, n_items


def done_keys():
    if not OUT.exists():
        return set()
    with open(OUT, newline="") as fh:
        return {(r["dataset"], r["algorithm"], round(float(r["param_value"]), 9))
                for r in csv.DictReader(fh)}


def report():
    """Apply the selection rule in the module docstring, exactly as written."""
    import pandas as pd
    d = pd.read_csv(OUT)
    ok = (d.timed_out.astype(str).str.lower() != "true") & d.error.isna()
    print("%-14s %-10s %-7s %-22s %9s %9s %7s %8s  %s"
          % ("dataset", "sigma", "target", "lowest-memory miner", "best MB",
             "Apriori", "ratio", "gap MB", "completed"))
    verdict = {}
    for (ds, sg), g in d.groupby(["dataset", "param_value"], sort=False):
        c = g[ok.loc[g.index]]
        done = "%d/%d" % (len(c), len(g))
        apr = c[c.algorithm == "Apriori_Gen_Borgelt"].peak_memory_mb
        if c.empty or apr.empty:
            print("%-14s %-10.6f %-7s %-22s %9s %9s %7s %8s  %s  (Apriori did not complete)"
                  % (ds, sg, g.target_pairs.iloc[0], "-", "-", "-", "-", "-", done))
            verdict.setdefault(ds, False)
            continue
        best = c.loc[c.peak_memory_mb.idxmin()]
        a = float(apr.iloc[0])
        ratio, gap = a / best.peak_memory_mb, a - best.peak_memory_mb
        q = ratio >= RATIO and gap >= GAP_MB
        verdict[ds] = verdict.get(ds, False) or q
        print("%-14s %-10.6f %-7s %-22s %9.2f %9.2f %7.2f %8.2f  %s%s"
              % (ds, sg, g.target_pairs.iloc[0], best.algorithm, best.peak_memory_mb, a,
                 ratio, gap, done, "  <- qualifies" if q else ""))
    print()
    print("Rule: Apriori / lowest >= %.1f and Apriori - lowest >= %.0f MB at some level."
          % (RATIO, GAP_MB))
    print("QUALIFY:     " + ", ".join(k for k, v in verdict.items() if v))
    print("DO NOT:      " + ", ".join(k for k, v in verdict.items() if not v))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    if args.prepare:
        prepare()
        return 0
    if args.report:
        report()
        return 0

    import psutil
    from src import metrics as M
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
    algos = [(n, c) for n, c in category1_algorithms() if n in SCREEN_ALGOS]
    done = done_keys()
    jobs = []
    for name in CANDIDATES.values():
        lv, n_tx, n_items = levels(name)
        for sg, tg in lv:
            print("  %-14s sigma %.6f  (target %d pairs)" % (name, sg, tg))
            for a, c in algos:
                if (name, a, round(sg, 9)) not in done:
                    jobs.append((a, c, str(RAW / ("%s.txt" % name)), name, sg, None,
                                 n_tx, n_items, TIMEOUT, 0, M.MONITOR_INTERVAL, tg))
    print("%d screening runs, at most %.0f min if every one timed out"
          % (len(jobs), len(jobs) * TIMEOUT / 60))
    if args.plan or not jobs:
        return 0
    header = not OUT.exists()
    t0 = time.time()
    with open(OUT, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if header:
            w.writeheader()
        for i, j in enumerate(jobs, 1):
            row = run_one(j[:-1])
            row["target_pairs"] = j[-1]
            row["machine"] = MACHINE
            w.writerow(row)
            fh.flush()
            print("[%3d/%3d] %5.1f min | %-14s %-20s %.6f %8.2fs %9s MB  %s"
                  % (i, len(jobs), (time.time() - t0) / 60, row["dataset"],
                     row["algorithm"], row["param_value"], row["runtime_s"] or 0,
                     row["peak_memory_mb"],
                     "TIMEOUT" if row["timed_out"] else (row["error"] or "ok")), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
