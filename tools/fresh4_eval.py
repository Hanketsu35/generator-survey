"""Score results/FRESH4_PROTOCOL.md.

    python tools/fresh4_eval.py --probe
    python tools/fresh4_eval.py
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import fresh_eval as FE                                    # noqa: E402

import probe_eval as PE                                    # noqa: E402

FE.TRUTH = _ROOT / "results" / "fresh4_summary.csv"
FE.PROBES = _ROOT / "results" / "probe_fresh4.jsonl"
OUT = _ROOT / "results" / "fresh4_eval_output.txt"


def frozen_ok():
    import hashlib
    import subprocess
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/FRESH4_PROTOCOL.md"],
                       capture_output=True, text=True, check=True).stdout.strip()
    ok = True
    for path in FE.FROZEN:
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (c, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, c))
            ok = False
    return ok


def score():
    from recommender import intervals as I
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    rec, db = Recommender(), CapabilityDB()
    probes = FE.load_probes()
    t = pd.read_csv(FE.TRUTH)
    rows = []
    for (ds, sg), g in t.groupby(["dataset", "param_value"]):
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        c = g[g.algorithm.isin(el)]
        ok = PE.completed(c)
        mem = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
        rt = dict(zip(c.algorithm[ok], c.runtime_s[ok]))
        inside = lambda iv, v: bool(iv is not None and iv[0] <= v <= iv[1])   # noqa: E731
        for r in rec.recommend(task)[0]:
            if r.algorithm not in mem:
                continue
            old = I.interval("model_memory", r.memory_mb)
            rows.append({"dataset": ds, "sigma": sg, "algorithm": r.algorithm, "kind": "V1 model memory",
                         "hit": inside(r.memory_interval, mem[r.algorithm]),
                         "hit_old": inside(old, mem[r.algorithm]),
                         "width": r.memory_interval[1] / r.memory_interval[0]})
            rows.append({"dataset": ds, "sigma": sg, "algorithm": r.algorithm, "kind": "V3 model runtime",
                         "hit": inside(r.runtime_interval, max(rt[r.algorithm], I.RT_FLOOR)),
                         "hit_old": inside(I.interval("model_runtime", r.runtime_s),
                                           max(rt[r.algorithm], I.RT_FLOOR)),
                         "width": np.nan})
        pr = probes.get((ds, round(float(sg), 9)))
        if pr is None:
            continue
        for r in rec.recommend(task, probe=pr)[0]:
            if r.algorithm not in mem or r.memory_interval is None:
                continue
            probed = r.prediction_source.startswith("probe")
            tag = "measured" if r.prediction_source == "probe-measured" else "sampled"
            old = I.interval("probe_memory_" + tag if probed else "model_memory", r.memory_mb)
            rows.append({"dataset": ds, "sigma": sg, "algorithm": r.algorithm,
                         "kind": "V2 probe memory" if probed else "scaled model memory (not tested)",
                         "hit": inside(r.memory_interval, mem[r.algorithm]),
                         "hit_old": inside(old, mem[r.algorithm]),
                         "width": r.memory_interval[1] / r.memory_interval[0]})
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "fresh4_eval_rows.csv", index=False)
    L = []
    for kind, q in d.groupby("kind"):
        per = q.groupby("dataset").agg(hit=("hit", "mean"), hit_old=("hit_old", "mean"), n=("hit", "size"))
        m = per.hit.mean()
        test = kind.startswith("V")
        L.append("%-34s mean per-dataset coverage %.3f (old quantiles %.3f) | runs %.3f | datasets >= 0.95: %d/%d | min %.2f | median width x%.1f%s"
                 % (kind, m, per.hit_old.mean(), q.hit.mean(), (per.hit >= 0.95).sum(), len(per),
                    per.hit.min(), q.width.median(),
                    (" -> %s" % ("PASS" if m >= 0.90 else "FAIL")) if test else ""))
        for ds, r in per.iterrows():
            L.append("      %-12s n=%3d  %.2f  (old %.2f)" % (ds, r.n, r.hit, r.hit_old))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args(argv)
    if not frozen_ok():
        return 2
    if args.probe:
        FE.run_probes()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
