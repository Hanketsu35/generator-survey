"""Score results/FRESH5_PROTOCOL.md (intervals with a dataset-level guarantee,
exact memory).

    python tools/fresh5_eval.py --probe
    python tools/fresh5_eval.py
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

FE.TRUTH = _ROOT / "results" / "fresh5_summary.csv"
FE.PROBES = _ROOT / "results" / "probe_fresh5.jsonl"
FE.FROZEN = FE.FROZEN[:-1] + ["results/exact/training_runs.csv"]
OUT = _ROOT / "results" / "fresh5_eval_output.txt"
BARS = {"W1 probe memory": 0.90, "W2 model memory": 0.95, "W3 model runtime": 0.95}


def frozen_ok():
    import hashlib
    import subprocess
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", "results/FRESH5_PROTOCOL.md"],
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
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    rec, db = Recommender(), CapabilityDB()
    probes = FE.load_probes()
    t = pd.read_csv(FE.TRUTH)
    rows = []
    inside = lambda iv, v: bool(iv is not None and iv[0] <= v <= iv[1])   # noqa: E731
    for (ds, sg), g in t.groupby(["dataset", "param_value"]):
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=float(sg), objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        c = g[g.algorithm.isin(el)]
        ok = PE.completed(c)
        mem = dict(zip(c.algorithm[ok], c.peak_memory_mb[ok]))
        rt = dict(zip(c.algorithm[ok], c.runtime_s[ok]))
        for r in rec.recommend(task)[0]:
            if r.algorithm not in mem:
                continue
            rows.append({"dataset": ds, "kind": "W2 model memory", "hit": inside(r.memory_interval, mem[r.algorithm]),
                         "width": r.memory_interval[1] / r.memory_interval[0], "level": r.memory_interval_level})
            rows.append({"dataset": ds, "kind": "W3 model runtime",
                         "hit": inside(r.runtime_interval, max(rt[r.algorithm], 0.01)),
                         "width": np.nan, "level": r.runtime_interval_level})
        pr = probes.get((ds, round(float(sg), 9)))
        if pr is None:
            continue
        for r in rec.recommend(task, probe=pr)[0]:
            if r.algorithm in mem and r.prediction_source.startswith("probe") and r.memory_interval:
                rows.append({"dataset": ds, "kind": "W1 probe memory",
                             "sub": r.prediction_source, "hit": inside(r.memory_interval, mem[r.algorithm]),
                             "width": r.memory_interval[1] / r.memory_interval[0], "level": r.memory_interval_level})
    d = pd.DataFrame(rows)
    d.to_csv(_ROOT / "results" / "fresh5_eval_rows.csv", index=False)
    L = []
    for kind, q in d.groupby("kind"):
        per = q.groupby("dataset").hit.mean()
        bar = BARS[kind]
        L.append("%-18s level %.2f | mean per-dataset coverage %.3f (bar %.2f) -> %s | runs %.3f | datasets >= 0.95: %d/%d | min %.2f | median width x%.2f"
                 % (kind, q.level.dropna().iloc[0] if q.level.notna().any() else float("nan"), per.mean(),
                    bar, "PASS" if per.mean() >= bar else "FAIL", q.hit.mean(), (per >= 0.95).sum(),
                    len(per), per.min(), q.width.median()))
        for ds, v in per.items():
            L.append("      %-14s n=%3d  %.2f" % (ds, (q.dataset == ds).sum(), v))
    if "sub" in d:
        for s, q in d[d.kind == "W1 probe memory"].groupby("sub"):
            L.append("   %-15s coverage %.3f (n=%d, %d datasets)" % (s, q.groupby("dataset").hit.mean().mean(),
                                                                 len(q), q.dataset.nunique()))
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
