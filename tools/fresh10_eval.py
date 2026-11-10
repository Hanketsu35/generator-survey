"""Tenth fresh confirmation: hard instances, and cost models fitted on all 81
benchmarked datasets (results/FRESH10_PROTOCOL.md).

    python tools/fresh10_eval.py --plan
    python tools/fresh10_eval.py --probe
    python tools/bench_real_extra.py --instances results/fresh10_instances.csv ...
    python tools/fresh10_eval.py            # score

Reuses tools/fresh9_eval.py with FRESH10's files. Every planned instance gets
a truth run (no selection step).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import fresh9_eval as F9                                   # noqa: E402
import prepare_fresh10                                     # noqa: E402,F401  (sets the selection)
import probe_eval as PE                                    # noqa: E402

RES = _ROOT / "results"
F9.SEL = RES / "fresh10_selection.json"
F9.PLAN = RES / "fresh10_instances.csv"
F9.PROBES = RES / "probe_fresh10.jsonl"
F9.TRUTH = RES / "fresh10_summary.csv"
F9.PROTOCOL = "results/FRESH10_PROTOCOL.md"
OUT = RES / "fresh10_eval_output.txt"
TARGETS = (1000, 5000)
FAIL = 10.0


def plan():
    import csv
    import bench_real_extra as B
    rows = B.plan(F9.names(), calibration=False, cap_reachable=True, targets=TARGETS)
    with open(F9.PLAN, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "sigma", "target_pairs", "n_tx", "n_items"])
        for ds, sg, tg, _r, n_tx, n_items in rows:
            w.writerow([ds, repr(sg), tg, n_tx, n_items])
    print("%d instances on %d datasets" % (len(rows), len({r[0] for r in rows})))


def runs81():
    """training_all.csv with the static features of all 81 datasets, computed
    from the files where the meta-feature cache has none (the configuration
    under test)."""
    import review_learning_curve as LC
    return LC._with_features(RES / "exact" / "training_all.csv")


def score():
    from recommender.capabilities import CapabilityDB
    from recommender.engine import Recommender
    from recommender.spec import MiningTask
    import baseline2_comparison as B2
    rec22, rec81, db = Recommender(), Recommender(runs=runs81()), CapabilityDB()
    probes = F9.load_probes()
    inst = pd.read_csv(F9.PLAN)
    truth = pd.read_csv(F9.TRUTH)
    rows, ivs = [], []
    inside = lambda iv, v: bool(iv is not None and iv[0] <= v <= iv[1])   # noqa: E731
    for r in inst.itertuples():
        ds, sg = r.dataset, float(r.sigma)
        g = truth[(truth.dataset == ds) & np.isclose(truth.param_value, sg, rtol=1e-9)]
        if g.empty:
            continue
        pr = probes.get((ds, round(sg, 9)))
        ok = PE.completed(g)
        row = {"dataset": ds, "sigma": sg, "target_pairs": r.target_pairs,
               "mode": pr.mode if pr else None}
        for obj, col in (("memory", "peak_memory_mb"), ("runtime", "runtime_s")):
            task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                              threshold=sg, objective=obj)
            el = {v.algorithm for v in db.filter(task)[0]}
            vals = g[col] if obj == "memory" else np.maximum(g[col], 0.01)
            done = {a: v for a, v, k in zip(g.algorithm, vals, ok) if k and a in el and a in F9.MINERS}
            cand = [a for a in sorted(set(g.algorithm)) if a in el and a in F9.MINERS]
            if len(cand) < 2 or not done:
                continue
            best = min(done.values())
            reg = lambda a: done[a] / best if a in done else FAIL   # noqa: E731
            pick = lambda rec, probe=None: next(x.algorithm for x in rec.recommend(task, probe=probe)[0]  # noqa: E731
                                               if x.algorithm in cand)
            row["%s_22" % obj] = reg(pick(rec22))
            row["%s_81" % obj] = reg(pick(rec81))
            if obj == "memory" and pr is not None:
                row["memory_probe"] = reg(pick(rec22, pr))
                row["memory_argmin"] = reg(B2.probe_argmin(pr, cand, F9.MINERS))
                row["best_mb"], row["best_s"] = best, None
        rows.append(row)
        # intervals of the deployed engine, as FRESH9
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=sg, objective="memory")
        mem = dict(zip(g.algorithm[ok], g.peak_memory_mb[ok]))
        rt = dict(zip(g.algorithm[ok], g.runtime_s[ok]))
        for x in rec22.recommend(task)[0]:
            if x.algorithm in mem:
                ivs.append({"dataset": ds, "kind": "Y3 model memory", "level": x.memory_interval_level,
                            "hit": inside(x.memory_interval, mem[x.algorithm])})
                ivs.append({"dataset": ds, "kind": "Y2 model runtime", "level": x.runtime_interval_level,
                            "hit": inside(x.runtime_interval, max(rt[x.algorithm], 0.01))})
        if pr is not None:
            for x in rec22.recommend(task, probe=pr)[0]:
                if x.algorithm in mem and x.prediction_source.startswith("probe") and x.memory_interval:
                    ivs.append({"dataset": ds, "level": x.memory_interval_level,
                                "kind": "Y4 probe memory, measured" if x.prediction_source == "probe-measured"
                                else "Y1 probe memory, sampled",
                                "hit": inside(x.memory_interval, mem[x.algorithm])})
    d = pd.DataFrame(rows)
    d.to_csv(RES / "fresh10_eval_rows.csv", index=False)
    gm = lambda v: float(np.exp(np.log(np.asarray(v, float)).mean()))   # noqa: E731
    L = ["FRESH10: %d instances on %d datasets" % (len(d), d.dataset.nunique())]
    m = d.dropna(subset=["memory_probe"])
    fp, fa = int((m.memory_probe >= FAIL).sum()), int((m.memory_argmin >= FAIL).sum())
    L.append("H1 (primary) recommender with probe, memory: %.3fx (<= 1.10), failed %d vs probe-argmin %d: %s"
             % (gm(m.memory_probe), fp, fa, "PASS" if gm(m.memory_probe) <= 1.10 and fp <= fa else "FAIL"))
    q = d.dropna(subset=["memory_22", "memory_81"])
    L.append("H2 cost models on 81 datasets, memory without probe: 81 %.3fx vs 22 %.3fx (81 < 22): %s"
             % (gm(q.memory_81), gm(q.memory_22), "PASS" if gm(q.memory_81) < gm(q.memory_22) else "FAIL"))
    q = d.dropna(subset=["runtime_22", "runtime_81"])
    L.append("H3 cost models on 81 datasets, runtime: 81 %.3fx vs 22 %.3fx (81 <= 1.05 x 22): %s"
             % (gm(q.runtime_81), gm(q.runtime_22),
                "PASS" if gm(q.runtime_81) <= 1.05 * gm(q.runtime_22) else "FAIL"))
    bars = {"Y1 probe memory, sampled": 0.90, "Y2 model runtime": 0.95, "Y3 model memory": 0.95,
            "Y4 probe memory, measured": 0.95}
    iv = pd.DataFrame(ivs)
    for kind, q in iv.groupby("kind"):
        per = q.groupby("dataset").hit.mean()
        if kind.startswith("Y4") and q.dataset.nunique() < 3:
            L.append("%s: %d dataset(s), reported only: %.3f" % (kind, q.dataset.nunique(), per.mean()))
            continue
        L.append("%-27s mean per-dataset coverage %.3f (bar %.2f) -> %s | min %.2f | datasets %d"
                 % (kind, per.mean(), bars[kind], "PASS" if per.mean() >= bars[kind] else "FAIL",
                    per.min(), len(per)))
    L.append("sizes: best peak median %.0f MB, max %.0f MB" % (m.best_mb.median(), m.best_mb.max()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--probe", action="store_true")
    args = ap.parse_args(argv)
    if args.plan:
        plan()
        return 0
    F9.FROZEN = F9.FROZEN + ["tools/review_learning_curve.py", "tools/fresh10_eval.py"]
    if not F9.frozen_ok():
        return 2
    if args.probe:
        F9.run_probes()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
