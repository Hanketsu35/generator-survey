"""Post hoc analyses requested in the review of the ESWA manuscript (2026-11-11).

    python tools/review_analyses.py

None of these is a test. They are computed from stored rows only (no miner
is run): results/baseline_rows.csv and baseline2_rows.csv (picks and regrets
of the baseline comparison), the stored probes, and the truth tables of the
test sets. Output: results/review_analyses_output.txt.

R1  memory regret split by probe mode (direct: the probe ran every native
    miner on the whole file; sampled: it extrapolated)
R2  the probe's own memory: the four native miners run concurrently, so the
    probe needs about the sum of their sample peaks; set against the best
    eligible peak of the instance
R3  simple baselines on memory: always Gr-growth; a one-feature rule
    (Gr-growth above a number of transactions, a Borgelt program below),
    fitted on the 22 training datasets; the oracle among the native miners
R4  sensitivity to the failed-pick penalty (2, 10, 100)
R5  feature-free intervals: per implementation, the 2.5-97.5% quantiles of
    its peak memory and runtime over the training table, scored on PRIMARY
    like the model's intervals
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import baseline_comparison as BC                           # noqa: E402
import probe_eval as PE                                    # noqa: E402

NATIVE = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth"]
BORGELT = NATIVE[:3]
FAIL = 10.0
OUT = _ROOT / "results" / "review_analyses_output.txt"
L = []


def gm(x):
    x = np.asarray(x, float)
    return float(np.exp(np.log(x).mean())) if len(x) else float("nan")


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    L.append(s)


def truth_tables():
    out = {}
    for k, p in BC.TESTS.items():
        t = pd.read_csv(p)
        out[k] = t[t.algorithm.isin(BC.MINERS)]
    return out


def probe_meta():
    out = {}
    for f in BC.PROBES:
        for line in open(f):
            r = json.loads(line)
            peaks = [max(v[0] for _, v in pts) for pts in r["points"].values() if pts]
            out[(r["dataset"], round(float(r["sigma"]), 9))] = {
                "mode": r["mode"], "n": r["n"], "wall": r["wall_s"],
                "mem_sum": float(sum(peaks)) if peaks else float("nan"),
                "mem_max": float(max(peaks)) if peaks else float("nan")}
    return out


def instance_truth(truths, tset, ds, sg):
    t = truths[tset]
    g = t[(t.dataset == ds) & np.isclose(t.param_value, sg, rtol=1e-6)]
    ok = PE.completed(g)
    return dict(zip(g.algorithm[ok], g.peak_memory_mb[ok])), set(g.algorithm)


def r1_r2(b2, pm, truths):
    say("R1  memory regret by probe mode (geometric mean; failed pick = 10)")
    b2 = b2.copy()
    b2["mode"] = [pm.get((d, round(float(s), 9)), {}).get("mode") for d, s in zip(b2.dataset, b2.sigma)]
    for name, q in (("PRIMARY", b2[b2.primary]), ("all test sets", b2)):
        for mode, qq in q.groupby("mode"):
            say("  %-14s %-8s n=%3d | recommender %.3fx | probe-argmin %.3fx"
                % (name, mode, len(qq), gm(qq["recommender, probe"]), gm(qq["probe-argmin"])))
        say("  %-14s share of instances with a direct probe: %.1f%%"
            % (name, 100 * (q["mode"] == "direct").mean()))
    say("")
    say("R2  the probe's own memory against the best eligible peak of the instance")
    rows = []
    for r in b2.itertuples():
        meta = pm.get((r.dataset, round(float(r.sigma), 9)))
        if meta is None:
            continue
        done, _ = instance_truth(truths, r.set, r.dataset, r.sigma)
        if not done:
            continue
        best = min(done.values())
        rows.append({"primary": r.primary, "mode": meta["mode"],
                     "sum_ratio": meta["mem_sum"] / best, "max_ratio": meta["mem_max"] / best,
                     "excess_mb": meta["mem_sum"] - best})
    d = pd.DataFrame(rows)
    for name, q in (("PRIMARY", d[d.primary]), ("all test sets", d)):
        for mode, qq in q.groupby("mode"):
            say("  %-14s %-8s n=%3d | probe memory (sum of the 4 concurrent peaks) / best peak: median %.2f, "
                "90%% %.2f, max %.1f; above the best peak on %.0f%%; excess median %.1f MB, 90%% %.1f MB"
                % (name, mode, len(qq), qq.sum_ratio.median(), qq.sum_ratio.quantile(.9),
                   qq.sum_ratio.max(), 100 * (qq.sum_ratio > 1).mean(), qq.excess_mb.median(),
                   qq.excess_mb.quantile(.9)))
    say("")


def r3(b2, pm, truths):
    say("R3  simple baselines, memory objective (geometric-mean regret; failed pick = 10)")
    tr = pd.read_csv(BC.TRAIN)
    tr = tr[tr.algorithm.isin(BC.MINERS)]
    tr_n = {}
    for f in [BC.EX / "probes.jsonl"]:
        for line in open(f):
            r = json.loads(line)
            tr_n[r["dataset"]] = r["n"]

    def regrets(frame, n_of, choose):
        out = []
        for (ds, sg), g in frame.groupby(["dataset", "param_value"]):
            ok = PE.completed(g)
            done = dict(zip(g.algorithm[ok], g.peak_memory_mb[ok]))
            if len(set(g.algorithm) & set(BC.MINERS)) < 2 or not done:
                continue
            n = n_of(ds, sg)
            if n is None:
                continue
            a = choose(n)
            best = min(done.values())
            out.append(done[a] / best if a in done else FAIL)
        return out

    # fit the one-feature rule on the training table
    def n_train(ds, sg):
        return tr_n.get(ds)
    cands = []
    ns = sorted({v for v in tr_n.values()})
    for b in BORGELT:
        for t in [0] + ns + [10 ** 12]:
            reg = regrets(tr, n_train, lambda n, t=t, b=b: "Gr_growth" if n >= t else b)
            if reg:
                cands.append((gm(reg), t, b, len(reg)))
    cands.sort()
    fit = cands[0]
    say("  rule fitted on the training table: Gr-growth if |D| >= %d, else %s (training regret %.3fx, n=%d)"
        % (fit[1], fit[2], fit[0], fit[3]))
    rows = {"always Gr-growth": [], "one-feature rule": [], "oracle among native": [],
            "recommender, probe": [], "probe-argmin": []}
    prim = {"always Gr-growth": [], "one-feature rule": [], "oracle among native": [],
            "recommender, probe": [], "probe-argmin": []}
    for r in b2.itertuples():
        meta = pm.get((r.dataset, round(float(r.sigma), 9)))
        if meta is None:
            continue
        done, algs = instance_truth(truths, r.set, r.dataset, r.sigma)
        if not done:
            continue
        best = min(done.values())
        reg = lambda a: done[a] / best if a in done else FAIL   # noqa: E731
        nat = [done[a] for a in NATIVE if a in done]
        vals = {"always Gr-growth": reg("Gr_growth"),
                "one-feature rule": reg("Gr_growth" if meta["n"] >= fit[1] else fit[2]),
                "oracle among native": (min(nat) / best) if nat else FAIL,
                "recommender, probe": getattr(r, "_6"), "probe-argmin": getattr(r, "_8")}
        for k, v in vals.items():
            rows[k].append(v)
            if r.primary:
                prim[k].append(v)
    for k in rows:
        say("  %-22s PRIMARY %.3fx (n=%d, failed %d) | all %.3fx (n=%d, failed %d)"
            % (k, gm(prim[k]), len(prim[k]), sum(np.asarray(prim[k]) >= FAIL),
               gm(rows[k]), len(rows[k]), sum(np.asarray(rows[k]) >= FAIL)))
    say("")


def r4():
    say("R4  sensitivity to the failed-pick penalty (geometric-mean regret, PRIMARY / all)")
    b = pd.read_csv("results/baseline_rows.csv")
    b2 = pd.read_csv("results/baseline2_rows.csv")
    cols = ["recommender, probe", "ISAC (k-means clusters)", "AutoFolio (SMAC, 1800s/fold)",
            "pairwise ranking", "regression (PAR10-imputed)", "SUNNY (k-NN, k=16)",
            "recommender, no probe", "SBS (fixed choice)"]
    for obj in ("memory", "runtime"):
        q = b[b.objective == obj]
        if obj == "memory":
            q = q[q["recommender, probe"].notna()]
        say("  objective %s" % obj)
        for c in cols:
            if c not in q or q[c].isna().all():
                continue
            parts = []
            for pen in (2.0, 10.0, 100.0):
                v = q[c].where(q[c] != FAIL, pen)
                vp = q[q.primary][c].where(q[q.primary][c] != FAIL, pen)
                parts.append("pen %g: %.3f / %.3f" % (pen, gm(vp.dropna()), gm(v.dropna())))
            say("    %-30s %s | failed %d / %d" % (c, " | ".join(parts),
                                                  (q[q.primary][c] == FAIL).sum(), (q[c] == FAIL).sum()))
    say("  (a regret of exactly 10 is a failed pick; completed picks above 10 are kept)")
    say("")


def r5():
    say("R5  feature-free intervals against the model's, PRIMARY (mean per-dataset coverage; median width)")
    tr = pd.read_csv("results/exact/training_all.csv")
    tr = tr[PE.completed(tr)]
    test = pd.concat([pd.read_csv("results/fresh7_summary.csv"), pd.read_csv("results/fresh8_summary.csv")])
    test = test[PE.completed(test)]
    for col, name in (("peak_memory_mb", "memory"), ("runtime_s", "runtime")):
        for lo_q, hi_q, lev in ((0.025, 0.975, "95%"), (0.05, 0.95, "90%")):
            q = tr.groupby("algorithm")[col].quantile([lo_q, hi_q]).unstack()
            t = test[test.algorithm.isin(q.index)].copy()
            v = t[col].clip(lower=0.01) if name == "runtime" else t[col]
            lo = t.algorithm.map(q[lo_q]); hi = t.algorithm.map(q[hi_q])
            if name == "runtime":
                lo = lo.clip(lower=0.01); hi = hi.clip(lower=0.01)
            t["hit"] = (v >= lo) & (v <= hi)
            t["width"] = hi / lo
            per = t.groupby("dataset").hit.mean()
            say("  %-8s %s marginal over the training table: coverage %.3f (min %.2f), median width x%.0f, n=%d runs"
                % (name, lev, per.mean(), per.min(), t.width.median(), len(t)))
    say("  model intervals on PRIMARY (Table of intervals): memory 95%% 0.991 (FRESH7), width x2,800; runtime 95%% 0.980, width x42,083")
    say("")


def main():
    truths = truth_tables()
    pm = probe_meta()
    b2 = pd.read_csv("results/baseline2_rows.csv")
    r1_r2(b2, pm, truths)
    r3(b2, pm, truths)
    r4()
    r5()
    OUT.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
