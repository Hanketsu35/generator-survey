"""SEQ1: the recommender on sequential data it has not seen (results/SEQ1_PROTOCOL.md).

    python tools/seq1_eval.py --plan     # thresholds from item supports only
    python tools/seq1_eval.py --run      # FEAT, FSGP, VGEN on every instance
    python tools/seq1_eval.py            # score

Datasets: MSNBC, FIFA and BIKE in SPMF sequence format (datasets/raw/*_seq.txt,
copied from datasets/candidates/), none of them used as sequential data
before (the sequential training data are bible, leviathan and sign).
Thresholds: for each dataset, the sigma at which the number of frequent
single items reaches 5, 10, 15, 20, 30, 60 and 100, with an absolute support of at least
10, placed at s - 0.25 like bench_real_extra.plan. One run at a time, 600 s
cutoff, JVM default heap; a run starts only when 10 GB are free and the
runner is the first the OOM killer takes.
"""
import argparse
import csv
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)
# The JRE the way bench_real_extra.py finds it: the shell's PATH may lack it.
import glob as _glob                                       # noqa: E402
_jre = sorted(_glob.glob(os.path.expanduser("~/.local/opt/jdk-*/bin")))
if _jre:
    os.environ["PATH"] = _jre[-1] + os.pathsep + os.environ.get("PATH", "")

import probe_eval as PE                                    # noqa: E402

RES = _ROOT / "results"
RAW = _ROOT / "datasets" / "raw"
DATASETS = ["msnbc_seq", "fifa_seq", "bike_seq"]
ITEM_TARGETS = (5, 10, 15, 20, 30, 60, 100)
MIN_ABS = 10
MINERS = ["FEAT", "FSGP", "VGEN"]
PLAN = RES / "seq1_instances.csv"
TRUTH = RES / "seq1_summary.csv"
OUT = RES / "seq1_eval_output.txt"
TIMEOUT = 600
FAIL = 10.0


def item_supports(path):
    n, cnt = 0, {}
    for line in open(path):
        toks = [t for t in line.split() if not t.startswith("-")]
        if not line.strip():
            continue
        n += 1
        for it in set(toks):
            cnt[it] = cnt.get(it, 0) + 1
    return n, sorted(cnt.values(), reverse=True)


def plan():
    rows = []
    for ds in DATASETS:
        n, sup = item_supports(RAW / ("%s.txt" % ds))
        seen = set()
        for tg in ITEM_TARGETS:
            if len(sup) < tg:
                continue
            s_abs = sup[tg - 1]
            if s_abs < MIN_ABS or s_abs in seen:
                continue
            seen.add(s_abs)
            rows.append((ds, (s_abs - 0.25) / n, tg, n, len(sup)))
    with open(PLAN, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "sigma", "target_items", "n_seq", "n_items"])
        for r in rows:
            w.writerow([r[0], repr(r[1]), r[2], r[3], r[4]])
    print("%d instances" % len(rows))


def run():
    import psutil
    from src import config as C
    from sweep_synthetic import run_one
    try:
        open("/proc/self/oom_score_adj", "w").write("1000")
    except OSError:
        pass
    done = set()
    if TRUTH.exists():
        for r in csv.DictReader(open(TRUTH)):
            done.add((r["algorithm"], r["dataset"], round(float(r["param_value"]), 9)))
    inst = pd.read_csv(PLAN)
    header = not TRUTH.exists()
    with open(TRUTH, "a", newline="") as fh:
        w = None
        for r in inst.sort_values("target_items").itertuples():
            for a in MINERS:
                if (a, r.dataset, round(float(r.sigma), 9)) in done:
                    continue
                while psutil.virtual_memory().available / 2 ** 30 < 10:
                    time.sleep(30)
                row = run_one((a, C.ALGORITHMS[a], str(RAW / ("%s.txt" % r.dataset)), r.dataset,
                               float(r.sigma), None, int(r.n_seq), int(r.n_items), TIMEOUT, 0, 0.1))
                if w is None:
                    w = csv.DictWriter(fh, fieldnames=list(row), extrasaction="ignore")
                    if header:
                        w.writeheader()
                w.writerow(row)
                fh.flush()
                print("%-5s %-10s %.6f %7.1fs %s" % (a, r.dataset, r.sigma, row.get("runtime_s") or 0,
                                                     "TIMEOUT" if row.get("timed_out") else (row.get("error") or "ok")),
                      flush=True)


def score():
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.evaluate import DEFAULT_REQUEST
    from recommender.spec import MiningTask
    rec, db = Recommender(), CapabilityDB()
    tr = pd.read_csv(RES / "exact" / "training_all.csv")
    tr = tr[tr.algorithm.isin(MINERS) & PE.completed(tr)]
    t = pd.read_csv(TRUTH)
    t["ok"] = PE.completed(t)
    gm = lambda v: float(np.exp(np.log(np.asarray(v, float)).mean()))   # noqa: E731
    rows, viol = [], []
    for (ds, sg), g in t.groupby(["dataset", "param_value"]):
        for obj, col in (("runtime", "runtime_s"), ("memory", "peak_memory_mb")):
            vals = g[col] if obj == "memory" else np.maximum(g[col], 0.01)
            done = {a: v for a, v, k in zip(g.algorithm, vals, g.ok) if k}
            if len(set(g.algorithm)) < 2 or not done:
                continue
            best = min(done.values())
            reg = lambda a: done[a] / best if a in done else FAIL   # noqa: E731
            # SBS: the implementation with the lowest geometric-mean cost on the sequential training runs
            sbs = tr.groupby("algorithm")[col].apply(lambda v: np.exp(np.log(np.maximum(v, 0.01)).mean())).idxmin()
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="sequential",
                              family=DEFAULT_REQUEST["sequential"], threshold=float(sg), objective=obj)
            pick = next(x.algorithm for x in rec.recommend(task)[0])
            rows.append({"dataset": ds, "sigma": sg, "objective": obj, "recommender": reg(pick),
                         "sbs": reg(sbs), "random": float(np.mean([reg(a) for a in MINERS]))})
            cheapest = min(done, key=done.get)
            for side in ("floor", "ceil"):
                tk = MiningTask(dataset_path=PE.dataset_path(ds), data_type="sequential",
                                family=DEFAULT_REQUEST["sequential"], threshold=float(sg),
                                objective=obj, boundary=side)
                v = db.evaluate(cheapest, tk)
                viol.append({"dataset": ds, "objective": obj, "side": side, "violated": not v.eligible})
    d, v = pd.DataFrame(rows), pd.DataFrame(viol)
    d.to_csv(RES / "seq1_eval_rows.csv", index=False)
    L = ["SEQ1: %d instances, %d datasets" % (d.groupby(["dataset", "sigma"]).ngroups, d.dataset.nunique())]
    for obj in ("runtime", "memory"):
        q = d[d.objective == obj]
        r, s = gm(q.recommender), gm(q.sbs)
        L.append("S%d %s: recommender %.3fx vs single best %.3fx (recommender <= SBS): %s | failed %d vs %d"
                 % (1 if obj == "runtime" else 2, obj, r, s, "PASS" if r <= s else "FAIL",
                    int((q.recommender >= FAIL).sum()), int((q.sbs >= FAIL).sum())))
    L.append("S3 (reported) cheapest pick violating a floor/ceiling request: %d of %d (%.1f%%)"
             % (int(v.violated.sum()), len(v), 100 * v.violated.mean()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if args.plan:
        plan()
    elif args.run:
        run()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
