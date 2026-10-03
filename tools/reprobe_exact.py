"""Re-run every probe recorded so far, now with exact peak memory.

    python tools/reprobe_exact.py

The probes behind every earlier evaluation measured memory by polling, like
the benchmark did (results/peak_method_check.csv). This repeats each
(dataset, sigma) once, one at a time, with src.metrics measuring through
peakrun. Output: results/exact/probes.jsonl, resume-safe, one line per probe
with the set it came from.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402
from recommender import probe as P                        # noqa: E402

OUT = _ROOT / "results" / "exact" / "probes.jsonl"
CSV = {"training": "results/probe_points.csv", "confirm": "results/probe_points_confirm.csv",
       "hard": "results/probe_points_hard.csv"}
JSONL = {"fresh": "results/probe_fresh.jsonl", "fresh2": "results/probe_fresh2.jsonl",
         "fresh3": "results/probe_fresh3.jsonl", "fresh4": "results/probe_fresh4.jsonl",
         "lag": "results/probe_lag.jsonl"}


def instances():
    out = []
    for s, f in CSV.items():
        d = pd.read_csv(_ROOT / f).drop_duplicates(["dataset", "sigma"])
        out += [(s, r.dataset, float(r.sigma)) for r in d.itertuples()]
    for s, f in JSONL.items():
        for line in open(_ROOT / f):
            r = json.loads(line)
            out.append((s, r["dataset"], float(r["sigma"])))
    return out


def main():
    from src import metrics as M
    assert M.EXACT_PEAK, "peakrun is not available"
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            done.add((r["set"], r["dataset"], round(r["sigma"], 9)))
    todo = [i for i in instances() if (i[0], i[1], round(i[2], 9)) not in done]
    print("%d probes to run (%d done)" % (len(todo), len(done)), flush=True)
    with open(OUT, "a") as fh:
        for k, (s, ds, sg) in enumerate(todo, 1):
            r = P.probe(PE.dataset_path(ds), sg)
            fh.write(json.dumps({"set": s, "dataset": ds, "sigma": sg, "n": r.n, "mode": r.mode,
                                 "sizes": r.sizes, "wall_s": r.wall_s, "costs": r.costs,
                                 "points": {a: [[z, list(v)] for z, v in p]
                                            for a, p in r.points.items()}}) + "\n")
            fh.flush()
            print("[%3d/%3d] %-8s %-14s %-11.6g %-7s %5.1fs" % (k, len(todo), s, ds, sg, r.mode, r.wall_s),
                  flush=True)


if __name__ == "__main__":
    main()
