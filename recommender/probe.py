"""Subsample probe: run the cheap miners on samples, extrapolate to full size.

    from recommender.probe import probe
    p = probe("datasets/raw/kosarak.txt", sigma=0.003)
    p.costs["Gr_growth"]   # {'memory_mb': ..., 'runtime_s': ..., 'mode': ...}

Why a probe and not another feature. The engine's static meta-features do
not carry the one regularity the extensions exposed: the memory ranking of the
native miners reverses with the number of transactions. Borgelt's
post-filters hold the transactions and grow with n; Gr-growth holds a prefix
tree of the frequent items and carries a ~14 MB fixed footprint. Which wins
depends on where the two curves cross, and a model that has seen twelve or
seventeen databases has to guess where that is. The miners themselves can
simply be asked. Probing trajectories (Renau & Hart, arXiv 2401.12745)
describe an instance by short runs of the solvers; budget-limited selection
from learning curves (Nguyen et al., arXiv 2410.07696) warns that ranking at a
small budget fails when the curves cross -- so the probe fits how each miner
SCALES and extrapolates, rather than ranking the miners on a sample.

Protocol, fixed in results/PROBE_PROTOCOL.md before the first probe ran:

  sizes      s1 = max(2,500, ceil(10 / sigma)), s2 = 4 s1, s3 = 16 s1;
             the smallest keeps an absolute support of at least 10
  direct     if s3 > n / 2, the miners run on the full database instead
             (60 s timeout each); the probe then MEASURES, and a miner that
             finishes has already produced the answer
  sampled    otherwise uniform samples (seed 0) of the three sizes at the
             same sigma, 20 s timeout each; memory and runtime extrapolated
             to n from the two largest sizes, two ways: the registered
             log-log line (slope clipped to [0, 1.2] memory, [0, 2]
             runtime) and the amended affine line (fixed part plus a
             per-transaction cost), which the costs report by default

The four miners run CONCURRENTLY, one thread each (each run is its own
process, so peak memory -- the process's own VmHWM -- is unaffected). Run one
after another the probe took up to 249 s on hard instances (four 60 s
timeouts, results/HARD_RESULTS.md); concurrently its worst case is one
timeout: 60 s direct, 3 x 20 s sampled. Runtimes measured concurrently are
somewhat higher than alone; the probe's runtime is not used for ranking
(memory requests only) and its runtime interval is not shown. Runs shorter
than RERUN_BELOW are then run again, one at a time: the memory sampler's first
reading comes after launch, and with four monitors sharing the interpreter it
can come after a 5-ms miner has exited. Measured, the concurrent reading was
the sequential one to within 0.001 log10 (median) on runs of 0.05 s or more,
and off by 0.41 on shorter ones (results/probe_parallel_check.csv). Each miner's
address space is capped at an eighth of RAM, so the four together stay under
half of it; a miner that hits the cap is reported as not finishing.

Only the four native miners are probed. A JVM miner's run costs a JVM start
and a heap that grows towards the default ceiling before collecting; that is
neither cheap nor extrapolable from a small sample, and the engine's model
prices it instead.
"""
import math
import os
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PROBED = ("Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth")
MIN_SAMPLE = 2500
MIN_ABS_SUPPORT = 10
GROWTH = 4
SAMPLE_TIMEOUT = 20
DIRECT_TIMEOUT = 60
MEM_SLOPE = (0.0, 1.2)
RT_SLOPE = (0.0, 2.0)
SEED = 0
#: runs faster than this (s) are re-measured alone; see the module docstring
RERUN_BELOW = 0.1
#: fraction of physical RAM each concurrently probed miner may address
MEM_SHARE = 8


@dataclass
class ProbeResult:
    n: int
    sigma: float
    mode: str                                   # "direct" | "sampled"
    sizes: List[int]
    wall_s: float                               # the probe's own cost
    costs: Dict[str, dict] = field(default_factory=dict)
    points: Dict[str, list] = field(default_factory=dict)


def _conventional(name, rc, count):
    """Exit codes that are a program's convention, not a failure (see
    tools/repair_summary._conventional_exit for the source references)."""
    if name == "Gr_growth" and count is not None:
        return rc in (count, count & 0xFF)
    return name.endswith("_Borgelt") and rc == 15


def _run(name, path, n, sigma, timeout, workdir, failures=None):
    """One native run. -> (peak_mb, runtime_s) or None if it failed.

    On failure, ``failures[name]`` records what the run still showed: a
    miner stopped at the timeout had already reached its peak so far, and
    one that ran out of its address-space cap needed more than the cap --
    both LOWER BOUNDS on its memory for this (sub)problem.
    """
    from src import metrics as M
    from src.config import ALGORITHMS, GRGROWTH_K
    cfg = ALGORITHMS[name]
    # one output file per miner and size: the miners now run side by side
    out = os.path.join(workdir, "out_%s_%d.txt" % (name, n))
    if cfg.get("exe_type") == "grgrowth":
        base = out[:-4]
        res = M.run_external(cfg["exe"], [path, max(1, int(round(sigma * n))), GRGROWTH_K, base],
                             base + ".txt", timeout=timeout,
                             count_fn=M.count_grgrowth_generators)
        out = base + ".txt"
    else:
        res = M.run_external(cfg["exe"], ["-tg", "-s%g" % (sigma * 100), path, out], out,
                             timeout=timeout, count_fn=M.count_borgelt_generators)
    try:
        os.remove(out)
    except OSError:
        pass
    rc = res.get("returncode")
    ok = not res.get("timed_out") and res.get("peak_memory_mb") is not None and (
        rc in (0, None) or _conventional(name, rc, res.get("generator_count")))
    if ok:
        return res["peak_memory_mb"], res["runtime_s"]
    if failures is not None:
        lb = res.get("peak_memory_mb") or 0.0
        why = "timeout" if res.get("timed_out") else "error"
        # Borgelt exits 1 with "not enough memory" and Gr-growth aborts on
        # bad_alloc (signal 6) when the cap is reached
        if ("memory" in (res.get("stderr") or "").lower() or "bad_alloc" in (res.get("stderr") or "")
                or rc in (-6, 134)):
            lb, why = max(lb, float(M.NATIVE_MEM_LIMIT_MB or 0)), "memory cap"
        failures[name] = {"memory_lb": lb, "why": why, "size": n}
    return None


def _sample(lines, k, dest):
    rng = random.Random(SEED)
    idx = sorted(rng.sample(range(len(lines)), k))
    with open(dest, "w") as fh:
        fh.writelines(lines[i] for i in idx)
    return dest


def _extrapolate(pts, n, lo, hi):
    """log-log line through the two largest sizes, slope clipped."""
    (s1, v1), (s2, v2) = pts[-2], pts[-1]
    if v1 <= 0 or v2 <= 0 or s2 <= s1:
        return v2
    slope = (math.log(v2) - math.log(v1)) / (math.log(s2) - math.log(s1))
    slope = min(max(slope, lo), hi)
    return v2 * (n / s2) ** slope


def _affine(pts, n):
    """Fixed part plus a per-transaction cost, from the two largest sizes.

    Added to the protocol after one smoke-test instance (chicago): memory is a
    fixed footprint plus ~47 bytes per transaction for the Borgelt miners, and
    a power law through points dominated by the fixed part underestimated the
    full-size value 3.6-fold. See results/PROBE_PROTOCOL.md, Amendment.
    """
    (s1, v1), (s2, v2) = pts[-2], pts[-1]
    b = max((v2 - v1) / (s2 - s1), 0.0) if s2 > s1 else 0.0
    return v2 + b * (n - s2)


def estimate(points, n, variant="affine"):
    """-> (memory_mb, runtime_s) extrapolated from probe points, or None."""
    if len(points) < 2:
        return None
    mem = [(s, g[0]) for s, g in points]
    rt = [(s, g[1]) for s, g in points]
    if variant == "loglog":
        return _extrapolate(mem, n, *MEM_SLOPE), _extrapolate(rt, n, *RT_SLOPE)
    return _affine(mem, n), _affine(rt, n)


def probe(path, sigma, algorithms=PROBED):
    """Probe `algorithms` on the transactional database at `path`."""
    from src import metrics as M
    import psutil
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / MEM_SHARE / 2 ** 20)
    t0 = time.perf_counter()
    with open(path) as fh:
        lines = [l if l.endswith("\n") else l + "\n" for l in fh if l.strip()]
    n = len(lines)
    s1 = max(MIN_SAMPLE, math.ceil(MIN_ABS_SUPPORT / sigma))
    sizes = [s1, GROWTH * s1, GROWTH * GROWTH * s1]
    work = tempfile.mkdtemp(prefix="probe_")
    try:
        if sizes[-1] > n / 2:
            r = ProbeResult(n=n, sigma=sigma, mode="direct", sizes=[n], wall_s=0.0)
            fails = {}
            with ThreadPoolExecutor(max_workers=len(algorithms)) as ex:
                runs = dict(zip(algorithms, ex.map(
                    lambda a: _run(a, path, n, sigma, DIRECT_TIMEOUT, work, fails), algorithms)))
            for a in algorithms:
                got = runs[a]
                if got and got[1] < RERUN_BELOW:
                    got = _run(a, path, n, sigma, DIRECT_TIMEOUT, work) or got
                r.points[a] = [(n, got)] if got else []
                r.costs[a] = ({"memory_mb": got[0], "runtime_s": got[1], "mode": "measured"}
                              if got else dict({"mode": "failed"}, **fails.get(a, {})))
        else:
            r = ProbeResult(n=n, sigma=sigma, mode="sampled", sizes=sizes, wall_s=0.0)
            files = {s: _sample(lines, s, os.path.join(work, "s%d.txt" % s)) for s in sizes}

            fails = {}

            def climb(a):
                pts = []
                for s in sizes:
                    got = _run(a, files[s], s, sigma, SAMPLE_TIMEOUT, work, fails)
                    if got is None:
                        break
                    pts.append((s, got))
                return pts
            with ThreadPoolExecutor(max_workers=len(algorithms)) as ex:
                climbs = dict(zip(algorithms, ex.map(climb, algorithms)))
            for a in algorithms:
                pts = [(s, (_run(a, files[s], s, sigma, SAMPLE_TIMEOUT, work) or got)
                        if got[1] < RERUN_BELOW else got) for s, got in climbs[a]]
                r.points[a] = pts
                if len(pts) < 2:
                    # a bound on a sample is not a bound on the full file's
                    # peak only if memory could shrink with n; it cannot for
                    # these miners (all hold the data or a tree of it)
                    r.costs[a] = dict({"mode": "failed"}, **fails.get(a, {}))
                    continue
                mem, rt = estimate(pts, n, "affine")
                mem_l, rt_l = estimate(pts, n, "loglog")
                r.costs[a] = {"memory_mb": mem, "runtime_s": rt, "memory_mb_loglog": mem_l,
                              "runtime_s_loglog": rt_l, "mode": "extrapolated"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    r.wall_s = time.perf_counter() - t0
    return r
