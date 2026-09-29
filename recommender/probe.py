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


def _run(name, path, n, sigma, timeout, workdir):
    """One native run. -> (peak_mb, runtime_s) or None if it failed."""
    from src import metrics as M
    from src.config import ALGORITHMS, GRGROWTH_K
    cfg = ALGORITHMS[name]
    out = os.path.join(workdir, "out_%s.txt" % name)
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
    if res.get("timed_out") or res.get("peak_memory_mb") is None:
        return None
    if rc not in (0, None) and not _conventional(name, rc, res.get("generator_count")):
        return None
    return res["peak_memory_mb"], res["runtime_s"]


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
    M.NATIVE_MEM_LIMIT_MB = int(psutil.virtual_memory().total / 4 / 2 ** 20)
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
            for a in algorithms:
                got = _run(a, path, n, sigma, DIRECT_TIMEOUT, work)
                r.points[a] = [(n, got)] if got else []
                r.costs[a] = ({"memory_mb": got[0], "runtime_s": got[1], "mode": "measured"}
                              if got else {"mode": "failed"})
        else:
            r = ProbeResult(n=n, sigma=sigma, mode="sampled", sizes=sizes, wall_s=0.0)
            files = {s: _sample(lines, s, os.path.join(work, "s%d.txt" % s)) for s in sizes}
            for a in algorithms:
                pts = []
                for s in sizes:
                    got = _run(a, files[s], s, sigma, SAMPLE_TIMEOUT, work)
                    if got is None:
                        break
                    pts.append((s, got))
                r.points[a] = pts
                if len(pts) < 2:
                    r.costs[a] = {"mode": "failed"}
                    continue
                mem, rt = estimate(pts, n, "affine")
                mem_l, rt_l = estimate(pts, n, "loglog")
                r.costs[a] = {"memory_mb": mem, "runtime_s": rt, "memory_mb_loglog": mem_l,
                              "runtime_s_loglog": rt_l, "mode": "extrapolated"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    r.wall_s = time.perf_counter() - t0
    return r
