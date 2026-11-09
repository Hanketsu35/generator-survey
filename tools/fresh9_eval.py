"""Ninth fresh confirmation (results/FRESH9_PROTOCOL.md).

    python tools/fresh9_eval.py --plan      # thresholds (landmarks only)
    python tools/fresh9_eval.py --probe     # probe every planned instance
    python tools/fresh9_eval.py --select    # instances that get a truth run
    python tools/bench_real_extra.py --instances results/fresh9_truth_instances.csv ...
    python tools/fresh9_eval.py             # score

Part A tests PROGRESS_DEMOTE on the instances where the native miners' probe
progress differs (selected by the probe alone). Part B tests the current
system, with the ranking quantiles rebuilt after the last confirmation, on
the 10- and 100-pair instances of every dataset. Intervals are scored on
every instance with a truth run.
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import probe_eval as PE                                    # noqa: E402

RES = _ROOT / "results"
SEL = RES / "fresh9_selection.json"
PLAN = RES / "fresh9_instances.csv"
PROBES = RES / "probe_fresh9.jsonl"
TRUTH_INST = RES / "fresh9_truth_instances.csv"
TRUTH = RES / "fresh9_summary.csv"
OUT = RES / "fresh9_eval_output.txt"
ROWS = RES / "fresh9_eval_rows.csv"
PROTOCOL = "results/FRESH9_PROTOCOL.md"
FROZEN = ["recommender/engine.py", "recommender/probe.py", "recommender/intervals.py",
          "recommender/data/intervals.json", "recommender/perfmodel.py",
          "recommender/survival.py", "recommender/capabilities.py",
          "results/exact/training_all.csv", "tools/bench_real_extra.py"]
B_TARGETS = (10, 100)
FAIL = 10.0
MINERS = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth",
          "DefMe", "Pascal", "Zart", "Talky_G", "TalkyG_Diffset"]
BARS = {"Y4 probe memory, measured": 0.95, "Y1 probe memory, sampled": 0.90,
        "Y3 model memory": 0.95, "Y2 model runtime": 0.95}
#: Free memory (GB) required before a probe starts: four miners at one eighth
#: of RAM each is the probe's worst case.
PROBE_MIN_FREE_GB = 16.0


def names():
    import prepare_fresh9 as P9
    return [P9.safe(r[1]) for r in json.load(open(SEL))]


def frozen_ok():
    c = subprocess.run(["git", "log", "-1", "--format=%h", "--", PROTOCOL],
                       capture_output=True, text=True, check=True).stdout.strip()
    if not c:
        print("REFUSED: %s is not committed" % PROTOCOL)
        return False
    ok = True
    for path in FROZEN:
        now = hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
        then = hashlib.sha256(subprocess.run(["git", "show", "%s:%s" % (c, path)],
                                             capture_output=True, check=True).stdout).hexdigest()
        if now != then:
            print("REFUSED: %s differs from its version at %s" % (path, c))
            ok = False
    return ok


def plan():
    import bench_real_extra as B
    rows = B.plan(names(), calibration=False, cap_reachable=True)
    with open(PLAN, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "sigma", "target_pairs", "n_tx", "n_items"])
        for ds, sg, tg, _role, n_tx, n_items in rows:
            w.writerow([ds, repr(sg), tg, n_tx, n_items])
    print("%d instances on %d datasets -> %s" % (len(rows), len({r[0] for r in rows}), PLAN))


def _shared_machine(min_free_gb):
    try:
        with open("/proc/self/oom_score_adj", "w") as fh:
            fh.write("1000")
    except OSError:
        pass
    import psutil
    while psutil.virtual_memory().available / 2 ** 30 < min_free_gb:
        time.sleep(30)


def run_probes():
    from recommender import probe as P
    done = set()
    if PROBES.exists():
        for line in PROBES.read_text().splitlines():
            r = json.loads(line)
            done.add((r["dataset"], round(r["sigma"], 9)))
    inst = pd.read_csv(PLAN)
    todo = [(d, float(s)) for d, s in zip(inst.dataset, inst.sigma) if (d, round(float(s), 9)) not in done]
    print("%d instances to probe (%d cached)" % (len(todo), len(done)), flush=True)
    with open(PROBES, "a") as fh:
        for i, (ds, s) in enumerate(todo, 1):
            _shared_machine(PROBE_MIN_FREE_GB)
            r = P.probe(PE.dataset_path(ds), s)
            fh.write(json.dumps({"dataset": ds, "sigma": s, "n": r.n, "mode": r.mode,
                                 "sizes": r.sizes, "wall_s": r.wall_s, "costs": r.costs,
                                 "points": {a: [[z, list(v)] for z, v in p]
                                            for a, p in r.points.items()}}) + "\n")
            fh.flush()
            print("[%3d/%3d] %-40s %-12g %-7s %6.1fs" % (i, len(todo), ds, s, r.mode, r.wall_s),
                  flush=True)


def load_probes():
    from recommender import probe as P
    out = {}
    for line in PROBES.read_text().splitlines():
        r = json.loads(line)
        out[(r["dataset"], round(r["sigma"], 9))] = P.ProbeResult(
            n=r["n"], sigma=r["sigma"], mode=r["mode"], sizes=r["sizes"], wall_s=r["wall_s"],
            costs=r["costs"], points={a: [(z, tuple(v)) for z, v in p] for a, p in r["points"].items()})
    return out


def lagging(pr):
    from recommender import engine as E
    return len(set(E.Recommender._probe_progress(pr).values())) > 1


def select():
    probes = load_probes()
    inst = pd.read_csv(PLAN)
    rows = []
    for r in inst.itertuples():
        pr = probes.get((r.dataset, round(float(r.sigma), 9)))
        if pr is None:
            raise SystemExit("not probed: %s %s" % (r.dataset, r.sigma))
        a, b = lagging(pr), int(r.target_pairs) in B_TARGETS
        if a or b:
            rows.append((0 if a else 1, int(r.target_pairs), r.dataset, r.sigma, a, b, pr.mode))
    rows.sort()
    with open(TRUTH_INST, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dataset", "sigma", "target_pairs", "part_a", "part_b", "probe_mode"])
        for _k, tg, ds, sg, a, b, mode in rows:
            w.writerow([ds, repr(float(sg)), tg, int(a), int(b), mode])
    print("truth instances: %d (part A %d, part B %d) -> %s"
          % (len(rows), sum(r[4] for r in rows), sum(r[5] for r in rows), TRUTH_INST))


def score():
    from recommender import engine as E
    from recommender.capabilities import CapabilityDB
    from recommender.spec import MiningTask
    import baseline2_comparison as B2
    rec, db = E.Recommender(), CapabilityDB()
    probes = load_probes()
    sel = pd.read_csv(TRUTH_INST)
    truth = pd.read_csv(TRUTH)
    sbs_order = MINERS
    picks, ivs = [], []
    inside = lambda iv, v: bool(iv is not None and iv[0] <= v <= iv[1])   # noqa: E731
    for r in sel.itertuples():
        ds, sg = r.dataset, float(r.sigma)
        g = truth[(truth.dataset == ds) & np.isclose(truth.param_value, sg, rtol=1e-9)]
        if g.empty:
            continue
        pr = probes[(ds, round(sg, 9))]
        task = MiningTask(dataset_path=PE.dataset_path(ds), data_type="transactional",
                          threshold=sg, objective="memory")
        el = {v.algorithm for v in db.filter(task)[0]}
        ok = PE.completed(g)
        mem = dict(zip(g.algorithm[ok], g.peak_memory_mb[ok]))
        rt = dict(zip(g.algorithm[ok], g.runtime_s[ok]))
        done = {a: m for a, m in mem.items() if a in el and a in MINERS}
        cand = [a for a in sorted(set(g.algorithm)) if a in el and a in MINERS]
        if len(cand) >= 2 and done:
            best = min(done.values())
            reg = lambda a: done[a] / best if a in done else FAIL   # noqa: E731
            row = {"dataset": ds, "sigma": sg, "target_pairs": r.target_pairs,
                   "part_a": bool(r.part_a), "part_b": bool(r.part_b), "mode": pr.mode,
                   "progress": json.dumps({a[:6]: round(v, 2)
                                           for a, v in E.Recommender._probe_progress(pr).items()})}
            for tag, flag in (("D", True), ("S", False)):
                E.PROGRESS_DEMOTE = flag
                a = next(x.algorithm for x in rec.recommend(task, probe=pr)[0] if x.algorithm in cand)
                row[tag], row["reg_" + tag] = a, reg(a)
            E.PROGRESS_DEMOTE = True
            a = B2.probe_argmin(pr, cand, sbs_order)
            row["argmin"], row["reg_argmin"] = a, reg(a)
            picks.append(row)
        # intervals, as FRESH8
        for x in rec.recommend(task)[0]:
            if x.algorithm not in mem:
                continue
            ivs.append({"dataset": ds, "kind": "Y3 model memory", "hit": inside(x.memory_interval, mem[x.algorithm]),
                        "width": x.memory_interval[1] / x.memory_interval[0], "level": x.memory_interval_level})
            ivs.append({"dataset": ds, "kind": "Y2 model runtime",
                        "hit": inside(x.runtime_interval, max(rt[x.algorithm], 0.01)),
                        "width": x.runtime_interval[1] / max(x.runtime_interval[0], 1e-9),
                        "level": x.runtime_interval_level})
        for x in rec.recommend(task, probe=pr)[0]:
            if x.algorithm in mem and x.prediction_source.startswith("probe") and x.memory_interval:
                ivs.append({"dataset": ds, "kind": "Y4 probe memory, measured"
                            if x.prediction_source == "probe-measured" else "Y1 probe memory, sampled",
                            "hit": inside(x.memory_interval, mem[x.algorithm]),
                            "width": x.memory_interval[1] / x.memory_interval[0],
                            "level": x.memory_interval_level})
    p = pd.DataFrame(picks)
    p.to_csv(ROWS, index=False)
    pd.DataFrame(ivs).to_csv(RES / "fresh9_interval_rows.csv", index=False)
    L = []
    # Part A
    a = p[p.part_a]
    ch = a[a.D != a.S]
    L.append("PART A (progress rule): %d lagging instances with truth, %d datasets; changed picks %d"
             % (len(a), a.dataset.nunique(), len(ch)))
    if len(a):
        L.append("  D (rule on)  %.3fx, failed %d | S (rule off) %.3fx, failed %d"
                 % (PE.gmean(a.reg_D), (a.reg_D >= FAIL).sum(), PE.gmean(a.reg_S), (a.reg_S >= FAIL).sum()))
    if len(ch) < 4:
        L.append("  fewer than 4 changed picks: UNDERPOWERED, no pass or fail")
    else:
        l1 = PE.gmean(a.reg_D) < PE.gmean(a.reg_S) and (a.reg_D >= FAIL).sum() <= (a.reg_S >= FAIL).sum()
        nb, nw = int((ch.reg_D < ch.reg_S).sum()), int((ch.reg_D > ch.reg_S).sum())
        L.append("  L1 (primary) D < S and failures D <= S: %s" % ("PASS" if l1 else "FAIL"))
        L.append("  L2 changed picks: D better %d, worse %d: %s" % (nb, nw, "PASS" if nb > nw else "FAIL"))
    for mode, q in ch.groupby("mode"):
        L.append("  L3 (secondary, %s probes): changed %d, D better %d, worse %d"
                 % (mode, len(q), (q.reg_D < q.reg_S).sum(), (q.reg_D > q.reg_S).sum()))
    for r in ch.itertuples():
        L.append("    %-36s %-10.6g %-7s %s  D %s %.3f | S %s %.3f"
                 % (r.dataset, r.sigma, r.mode, r.progress, r.D, r.reg_D, r.S, r.reg_S))
    # Part B
    b = p[p.part_b]
    L.append("PART B (current system): %d instances, %d datasets" % (len(b), b.dataset.nunique()))
    if len(b):
        gr, ga = PE.gmean(b.reg_D), PE.gmean(b.reg_argmin)
        fr, fa = int((b.reg_D >= FAIL).sum()), int((b.reg_argmin >= FAIL).sum())
        L.append("  Z1 recommender %.3fx vs probe-argmin %.3fx, ratio %.3f (<= 1.02), failed %d vs %d: %s"
                 % (gr, ga, gr / ga, fr, fa, "PASS" if gr / ga <= 1.02 and fr <= fa else "FAIL"))
        L.append("  Z2 recommender memory regret %.3fx (<= 1.10): %s" % (gr, "PASS" if gr <= 1.10 else "FAIL"))
        L.append("  same pick as probe-argmin on %d of %d" % ((b.D == b.argmin).sum(), len(b)))
    # Intervals
    d = pd.DataFrame(ivs)
    for kind, q in d.groupby("kind"):
        per = q.groupby("dataset").hit.mean()
        if kind.startswith("Y4") and q.dataset.nunique() < 3:
            L.append("%s: only %d dataset(s), reported only: coverage %.3f" % (kind, q.dataset.nunique(), per.mean()))
            continue
        L.append("%-28s level %.2f | mean per-dataset coverage %.3f (bar %.2f) -> %s | datasets >= level %d/%d"
                 " | min %.2f | median width x%.2f"
                 % (kind, q.level.dropna().iloc[0], per.mean(), BARS[kind],
                    "PASS" if per.mean() >= BARS[kind] else "FAIL",
                    (per >= q.level.dropna().iloc[0]).sum(), len(per), per.min(), q.width.median()))
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--probe", action="store_true")
    g.add_argument("--select", action="store_true")
    args = ap.parse_args(argv)
    if args.plan:
        plan()
        return 0
    if not frozen_ok():
        return 2
    if args.probe:
        run_probes()
    elif args.select:
        select()
    else:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
