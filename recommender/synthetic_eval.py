"""Does filling the instance space with synthetic data make selection work?

E3 reported the negative result that motivates this file: under
leave-one-dataset-out, the learned selector lost to always running the single
best implementation, and the per-algorithm constant beat the meta-feature model.
The diagnosis was not the model. With seven real datasets each fold removes a
seventh of the *feature space*, so the model extrapolates; instance space
analysis put the effective instance count at 7.3.

``tools/sweep_synthetic.py`` benchmarks 162 generated datasets at calibrated
thresholds. This script asks the only question that matters about them: does
adding them to the training set improve prediction on a **held-out real
dataset**?

Three rules, each of which the result would be worthless without
-----------------------------------------------------------------
1.  **The held-out instance is always real.** Synthetic instances may enter
    training only. Holding out a synthetic dataset would measure how predictable
    ``synth.py`` is, not how predictable a miner is, and would report a large
    number meaning nothing.

2.  **Both training sets are evaluated on the identical test set.** The
    comparison is real-only training versus real-plus-synthetic training, with
    the same folds, the same candidates and the same metric, so the difference
    is attributable to the added instances alone.

3.  **One cutoff.** The real table was measured with a 3600 s cutoff and the
    sweep with 300 s. Runtimes are therefore right-censored at different times,
    which PAR10 and the survival models would silently mix. Real runs are
    re-censored at the sweep's cutoff: a run known to have finished in 900 s is
    recorded as "did not finish within 300 s", which is *true* and puts both
    sets on one scale. Censoring known values downward is always valid; the
    reverse never is.

    python -m recommender.synthetic_eval
    python -m recommender.synthetic_eval --objective memory
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from . import landmarks as lm
from . import metafeatures as mf
from .bench_selectors import build_selectors, PORTFOLIOS
from .perfmodel import design_columns, attach_landmarks
from .selectors import npar10

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
OUT_DIR = os.path.join(_HERE, "out")
REAL_CSV = os.path.join(_ROOT, "results", "summary.csv")
SYN_CSV = os.path.join(_ROOT, "results", "synthetic_summary.csv")

#: The sweep's cutoff. Real runs are re-censored here so the two tables share a
#: censoring time (see rule 3).
SWEEP_CUTOFF_S = 300.0


# ----------------------------------------------------------------------
def build_caches(names, verbose=True):
    """Ensure static and landmark features exist for every named dataset."""
    static = mf.load_cache()
    todo = [n for n in names if n not in static and os.path.exists(mf.dataset_path(n))]
    if todo:
        if verbose:
            print("  building static meta-features for %d datasets" % len(todo))
        for n in todo:
            static[n] = mf.extract(mf.dataset_path(n), mf.data_type(n))
        mf.save_cache(static)
    return static


def build_landmark_cache(grid, verbose=True):
    missing = {d: [s for s in ss if lm._key(d, s) not in lm.load_cache()]
               for d, ss in grid.items()}
    missing = {d: ss for d, ss in missing.items() if ss}
    if missing:
        if verbose:
            print("  building landmarks for %d datasets" % len(missing))
        lm.build_cache(missing, verbose=False)
    return lm.load_cache()


def load_combined(objective="runtime", verbose=True):
    """Real (category 1) and synthetic runs in one table, on one censoring time."""
    real = pd.read_csv(REAL_CSV)
    real = real[real.category == 1].copy()
    real["completed"] = ((real.timed_out.astype(str).str.lower() != "true")
                         & real.error.isna())
    real["source"] = "real"

    if not os.path.exists(SYN_CSV):
        raise SystemExit("no synthetic results at %s -- run "
                         "tools/sweep_synthetic.py first" % SYN_CSV)
    syn = pd.read_csv(SYN_CSV)
    syn["completed"] = ((syn.timed_out.astype(str).str.lower() != "true")
                        & syn.error.isna() & syn.runtime_s.notna())
    syn["source"] = "synthetic"

    df = pd.concat([real, syn], ignore_index=True, sort=False)

    # Rule 3: one censoring time for both tables.
    over = df.completed & (df.runtime_s > SWEEP_CUTOFF_S)
    n_recensored = int(over.sum())
    df.loc[over, "completed"] = False
    df.loc[over, "runtime_s"] = SWEEP_CUTOFF_S
    if verbose and n_recensored:
        print("  re-censored %d real runs that exceeded the sweep's %ds cutoff"
              % (n_recensored, int(SWEEP_CUTOFF_S)))

    names = sorted(df.dataset.unique())
    build_caches(names, verbose)
    grid = {d: sorted(g.param_value.unique()) for d, g in df.groupby("dataset")}
    build_landmark_cache(grid, verbose)

    static = mf.load_cache()
    rows = [dict(dataset=n, **{k: static[n][k] for k in mf.FEATURE_NAMES})
            for n in names if n in static]
    df = df.merge(pd.DataFrame(rows), on="dataset", how="inner")
    df["log_thr"] = np.log10(df.param_value.clip(lower=1e-9))
    df = attach_landmarks(df)
    return df


# ----------------------------------------------------------------------
def prepare(df, objective, portfolio="all"):
    """Cost column and candidate filtering, matching bench_selectors."""
    algos = PORTFOLIOS.get(portfolio)
    sub = df if algos is None else df[df.algorithm.isin(algos)]
    sub = sub.copy()
    if objective == "runtime":
        sub["par10"] = np.where(sub.completed, sub.runtime_s,
                                SWEEP_CUTOFF_S * 10.0)
    else:
        # Peak memory of a killed run was observed, so it gets no invented
        # penalty; and a run too short to sample has no memory at all. Keep only
        # instances where every candidate both completed and was measured.
        sub = sub[sub.completed & sub.peak_memory_mb.notna()]
        wide = sub.pivot_table(index=["dataset", "param_value"],
                               columns="algorithm", values="peak_memory_mb",
                               aggfunc="min")
        keep = set(wide.dropna(axis=0, how="any").index)
        sub = sub[[(d, p) in keep for d, p in zip(sub.dataset, sub.param_value)]]
        sub = sub.assign(runtime_s=sub.peak_memory_mb)
        sub["par10"] = sub.peak_memory_mb.astype(float)
    return sub.dropna(subset=["par10"])


def evaluate(sub, cols, train_sources, anchors=None, verbose=True):
    """Leave-one-REAL-dataset-out. Returns a per-selector summary.

    ``anchors`` is ``(vbs, sbs)`` to normalise nPAR10 with. Passing the *same*
    pair to both arms is not a detail, it is what makes the comparison mean
    anything, and getting it wrong manufactured a large fake improvement here
    before this argument existed.

    The SBS is by definition chosen on the training set. Add 90 synthetic
    datasets to training and the single best algorithm over that training set is
    the one that wins on synthetic data -- which is not the one that wins on real
    data. Its cost on the real test set rose from 0.892 s to 1.302 s, and since
    it is nPAR10's denominator, *every* selector's nPAR10 collapsed towards zero:
    the best learned selector appeared to improve from 0.534 to 0.018 while its
    absolute cost got slightly worse, 0.887 s to 0.890 s. Normalising each arm by
    its own baseline rewards an arm for damaging its baseline.
    """
    real_ds = sorted(sub[sub.source == "real"].dataset.unique())
    rows = []
    for held in real_ds:
        train = sub[(sub.dataset != held) & sub.source.isin(train_sources)]
        test = sub[sub.dataset == held]
        train = train.dropna(subset=cols)
        test = test.dropna(subset=cols)
        if train.empty or test.empty:
            continue
        fitted = [s.fit(train, cols) for s in build_selectors()]
        for (thr,), g in test.groupby(["param_value"]):
            costs = dict(zip(g.algorithm, g.par10))
            candidates = sorted(costs)
            if len(candidates) < 2:
                continue
            x = g[cols].iloc[0].to_numpy(float)
            rec = {"dataset": held, "param_value": thr,
                   "vbs": min(costs.values())}
            for s in fitted:
                rec[s.name] = costs[s.select(x, candidates)]
            rows.append(rec)
    res = pd.DataFrame(rows)
    if res.empty:
        return {}, res
    names = [s.name for s in build_selectors()]
    sbs_name = "SBS (fixed choice)"
    own_vbs, own_sbs = res.vbs.mean(), res[sbs_name].mean()
    vbs, sbs = anchors if anchors else (own_vbs, own_sbs)
    out = {}
    for n in names:
        c = res[n].mean()
        out[n] = {"par10_mean": float(c),
                  "npar10": float(npar10(c, sbs, vbs)),
                  "top1": float((res[n] == res.vbs).mean())}
    out["VBS (oracle)"] = {"par10_mean": float(own_vbs),
                           "npar10": float(npar10(own_vbs, sbs, vbs)), "top1": 1.0}
    out["_meta"] = {"n_test": int(len(res)),
                    "own_sbs": float(own_sbs), "own_vbs": float(own_vbs),
                    "anchor_sbs": float(sbs), "anchor_vbs": float(vbs),
                    "headroom": float(own_sbs / max(own_vbs, 1e-12))}
    return out, res



def unit_for(objective):
    return "s" if objective == "runtime" else "MB"


def dose_response(sub, cols, args, unit, selector_name="pairwise ranking",
                  seeds=8):
    """Cost on a held-out REAL dataset as a function of the synthetic dose.

    Separates two explanations of the degradation the two-arm comparison shows:

      *the synthetic data is wrong*    -- cost rises with any amount of it;
      *the synthetic data swamped it*  -- a balanced amount helps and only a
                                          large amount hurts, 642 synthetic
                                          instances against 58 real ones being
                                          an 11:1 training ratio.

    Two things this function must not do, both of which an earlier version did
    and both of which invented a result.

    **It must not pick the best selector on the test data.** Reporting
    ``min`` over six selectors scored on the held-out fold is selection on the
    test set: it is optimistically biased at every dose, and because the winner
    flips between pairwise ranking (~6 MB) and regression or SUNNY (~11 MB) it
    also makes the curve jump between two levels for reasons that have nothing
    to do with the dose. The selector is therefore FIXED in advance.

    **It must not draw one random subset.** Which synthetic datasets are drawn
    matters more than how many: at a dose of 7, eight draws gave 6.077 to 11.138
    MB, beating the real-only baseline in 4 of 8. A single draw showed a 12%
    improvement that the mean over draws does not support.
    """
    syn_ds = sorted(sub[sub.source == "synthetic"].dataset.unique())
    doses = sorted({d for d in (0, 7, 14, 20, 50, 100, len(syn_ds))
                    if d <= len(syn_ds)})

    base, _ = evaluate(sub[sub.source == "real"], cols, ("real",))
    if not base:
        print("no usable folds"); return 1
    anchors = (base["_meta"]["own_vbs"], base["_meta"]["own_sbs"])
    if selector_name not in base:
        selector_name = sorted(n for n in base
                               if not n.startswith("_")
                               and n not in ("VBS (oracle)",))[0]
    base_cost = base[selector_name]["par10_mean"]

    L = ["=" * 78,
         "DOSE RESPONSE  (objective %s, features %s)" % (args.objective, args.features),
         "=" * 78,
         "",
         "  Selector FIXED to '%s' -- picking the best selector per dose"
         % selector_name,
         "  would be selection on the held-out data.",
         "  %d random draws per dose; which datasets are drawn matters more" % seeds,
         "  than how many.",
         "",
         "  real-only baseline: %.3f %s   (anchors VBS %.3f, SBS %.3f)"
         % (base_cost, unit, anchors[0], anchors[1]),
         "",
         "  %8s %10s %9s %9s %9s %9s %8s"
         % ("synth ds", "instances", "mean", "median", "min", "max", "wins"),
         "  " + "-" * 70]

    rows = []
    for k in doses:
        costs, n_inst = [], 0
        for seed in range(1 if k == 0 else seeds):
            rng = np.random.default_rng(seed)
            keep = set(rng.permutation(syn_ds)[:k]) if k else set()
            arm = sub[(sub.source == "real") | sub.dataset.isin(keep)]
            summary, _ = evaluate(arm, cols, ("real", "synthetic"), anchors=anchors)
            if not summary or selector_name not in summary:
                continue
            costs.append(summary[selector_name]["par10_mean"])
            n_inst = arm[arm.source == "synthetic"].groupby(
                ["dataset", "param_value"]).ngroups
        if not costs:
            continue
        c = np.asarray(costs)
        wins = int((c < base_cost).sum())
        L.append("  %8d %10d %9.3f %9.3f %9.3f %9.3f %5d/%-2d"
                 % (k, n_inst, c.mean(), np.median(c), c.min(), c.max(),
                    wins, len(c)))
        rows.append((k, float(c.mean()), wins, len(c)))

    if len(rows) >= 3:
        pos = [r for r in rows if r[0] > 0]
        best = min(pos, key=lambda r: r[1]) if pos else None
        L.append("")
        if best is None or best[1] >= base_cost:
            L.append("  No dose beats the real-only baseline ON AVERAGE. The")
            L.append("  degradation is therefore not a training-ratio effect that")
            L.append("  capping the synthetic share would fix: the synthetic")
            L.append("  instances carry a different algorithm ranking, and")
            L.append("  reweighting cannot repair a wrong ranking -- at best it")
            L.append("  recovers the real-only result by ignoring them.")
        else:
            L.append("  A dose of %d datasets beats the real-only baseline on"
                     % best[0])
            L.append("  average (%.3f vs %.3f %s, winning %d of %d draws), while"
                     % (best[1], base_cost, unit, best[2], best[3]))
            L.append("  the full set does not. That is a training-ratio effect,")
            L.append("  with the usual remedies: cap the share, or weight the")
            L.append("  real instances up.")
    text = "\n".join(L) + "\n"
    print(text)
    path = os.path.join(OUT_DIR, "synthetic_dose_%s_%s.txt"
                        % (args.objective, args.features))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("written: %s" % path)
    return 0

# ----------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--objective", default="runtime", choices=("runtime", "memory"))
    ap.add_argument("--portfolio", default="all", choices=sorted(PORTFOLIOS))
    ap.add_argument("--features", default="landmarks",
                    choices=("static", "landmarks", "both"))
    ap.add_argument("--dose", action="store_true",
                    help="sweep the NUMBER of synthetic datasets in training, "
                         "to separate 'synthetic data is wrong' from 'synthetic "
                         "data swamped the real data'")
    args = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_combined(args.objective)
    sub = prepare(df, args.objective, args.portfolio)
    cols = design_columns(args.features)

    n_real_ds = sub[sub.source == "real"].dataset.nunique()
    n_syn_ds = sub[sub.source == "synthetic"].dataset.nunique()
    n_real_inst = sub[sub.source == "real"].groupby(["dataset", "param_value"]).ngroups
    n_syn_inst = sub[sub.source == "synthetic"].groupby(["dataset", "param_value"]).ngroups

    L = ["=" * 82,
         "SYNTHETIC AUGMENTATION  (objective %s, portfolio %s, features %s)"
         % (args.objective, args.portfolio, args.features),
         "=" * 82,
         "",
         "  real:      %3d datasets, %4d instances" % (n_real_ds, n_real_inst),
         "  synthetic: %3d datasets, %4d instances" % (n_syn_ds, n_syn_inst),
         "  held-out instance is ALWAYS real; synthetic data trains only.",
         "  both arms share folds, candidates and a %ds censoring time."
         % int(SWEEP_CUTOFF_S),
         "",
         "  NOT comparable with bench_selectors' numbers. Re-censoring the real",
         "  runs at %ds (rule 3) drops the ones that needed longer, so this"
         % int(SWEEP_CUTOFF_S),
         "  slice is smaller and easier: on memory, 31 instances at headroom",
         "  3.007x where bench_selectors has 40 at 3.660x. Compare arms within",
         "  this report, never a number here against a number there.",
         ""]

    if args.dose:
        return dose_response(sub, cols, args, unit_for(args.objective))

    arms = {"real only": ("real",),
            "real + synthetic": ("real", "synthetic")}
    # The real-only arm sets the anchors, and the augmented arm is scored against
    # the same ones. Otherwise each arm is graded against its own baseline and an
    # arm is rewarded for degrading that baseline -- see evaluate()'s docstring.
    base_summary, _ = evaluate(sub, cols, arms["real only"])
    if not base_summary:
        print("  no usable folds"); return 1
    anchors = (base_summary["_meta"]["own_vbs"], base_summary["_meta"]["own_sbs"])
    results = {"real only": base_summary}
    for label, srcs in arms.items():
        if label == "real only":
            continue
        results[label], _ = evaluate(sub, cols, srcs, anchors=anchors)

    base = results["real only"]
    if not base:
        L.append("  no usable folds")
        print("\n".join(L)); return 1

    unit = unit_for(args.objective)
    L.append("  Both arms normalised by the REAL-ONLY anchors "
             "(VBS %.3f %s, SBS %.3f %s)."
             % (anchors[0], unit, anchors[1], unit))
    L.append("  Absolute cost is given first, because nPAR10 is a ratio and the")
    L.append("  oracle gap on this slice is only %.3f %s."
             % (anchors[1] - anchors[0], unit))
    L.append("")
    L.append("  %-30s %11s %8s %11s %8s"
             % ("selector", "real only", "nPAR10", "real+synth", "nPAR10"))
    L.append("  " + "-" * 72)
    order = sorted((k for k in base if not k.startswith("_")),
                   key=lambda k: base[k]["par10_mean"])
    for n in order:
        line = "  %-30s" % n
        for label in arms:
            s = results[label].get(n)
            if s:
                line += "%11.3f%9.3f" % (s["par10_mean"], s["npar10"])
            else:
                line += "%20s" % "-"
        L.append(line)
    L.append("")
    for label in arms:
        m = results[label].get("_meta", {})
        L.append("  %-18s own SBS %8.3f %-2s | own headroom %.3fx | %d instances"
                 % (label, m.get("own_sbs", float("nan")), unit,
                    m.get("headroom", float("nan")), m.get("n_test", 0)))
    # Where the two distributions disagree, stated as the ranking they induce.
    # This is the diagnostic for every number above: a selector trained on
    # synthetic data inherits the synthetic ranking.
    from .selectors import add_par10
    rk = {}
    for label, srcs in (("real", ("real",)), ("synthetic", ("synthetic",))):
        t = add_par10(sub[sub.source.isin(srcs)])
        rk[label] = t.groupby("algorithm").par10.mean().sort_values()
    if len(rk["synthetic"]):
        L.append("  MEAN COST RANKING, by source (%s)" % unit)
        L.append("  %-5s %-24s %12s   %-24s %12s"
                 % ("rank", "real", "cost", "synthetic", "cost"))
        L.append("  " + "-" * 82)
        for i in range(max(len(rk["real"]), len(rk["synthetic"]))):
            a = rk["real"].index[i] if i < len(rk["real"]) else ""
            ca = rk["real"].iloc[i] if i < len(rk["real"]) else float("nan")
            b = rk["synthetic"].index[i] if i < len(rk["synthetic"]) else ""
            cb = rk["synthetic"].iloc[i] if i < len(rk["synthetic"]) else float("nan")
            flag = "" if a == b else "   <- differs"
            L.append("  %-5d %-24s %12.3f   %-24s %12.3f%s"
                     % (i + 1, a, ca, b, cb, flag))
        top_real = list(rk["real"].index[:3])
        top_syn = list(rk["synthetic"].index[:3])
        if top_real != top_syn:
            L.append("")
            L.append("  The TOP of the ranking differs, which is where selection")
            L.append("  happens. Real: %s. Synthetic: %s."
                     % (" > ".join(top_real), " > ".join(top_syn)))
            L.append("  Coverage of the meta-feature space is not coverage of the")
            L.append("  PERFORMANCE space: synth.py spans the structural features")
            L.append("  by construction, but plants its patterns, and real dense")
            L.append("  data has correlation structure it does not reproduce. A")
            L.append("  model trained on it inherits the wrong ranking, so 'just")
            L.append("  generate more instances' does not fix a small")
            L.append("  meta-instance set here.")
        L.append("")

    drift = (results["real + synthetic"]["_meta"]["own_sbs"]
             - results["real only"]["_meta"]["own_sbs"])
    if abs(drift) > 1e-9:
        L.append("")
        L.append("  SBS DRIFT: the fixed choice trained with synthetic data costs")
        L.append("  %+.3f %s more on the real test set. The single best algorithm"
                 % (drift, unit))
        L.append("  over the augmented training set is not the one that wins on")
        L.append("  real data, which is a statement about how well synth.py")
        L.append("  reproduces the real instance distribution -- and the reason")
        L.append("  both arms must share one anchor.")
    L.append("")

    # --- the verdict, stated from the numbers -------------------------
    def best(summary):
        cand = [k for k in summary
                if k not in ("VBS (oracle)", "SBS (fixed choice)") and not k.startswith("_")]
        return min(cand, key=lambda k: summary[k]["npar10"]) if cand else None

    b0, b1 = best(results["real only"]), best(results["real + synthetic"])
    if b0 and b1:
        s0 = results["real only"][b0]
        s1 = results["real + synthetic"][b1]
        L.append("  best learned selector, real only:        %-26s %8.3f %s (nPAR10 %.3f)"
                 % (b0, s0["par10_mean"], unit, s0["npar10"]))
        L.append("  best learned selector, real + synthetic: %-26s %8.3f %s (nPAR10 %.3f)"
                 % (b1, s1["par10_mean"], unit, s1["npar10"]))
        # The verdict is read off ABSOLUTE cost. nPAR10 is a ratio against a
        # shared anchor, so it agrees here, but absolute cost is the quantity a
        # user experiences and it cannot be inflated by a damaged baseline.
        d = s1["par10_mean"] - s0["par10_mean"]
        if d < 0:
            L.append("  -> the synthetic instances HELP: %.3f %s cheaper per"
                     % (-d, unit))
            L.append("     configuration, %.1f%% of the %.3f %s oracle gap."
                     % (100 * (-d) / max(anchors[1] - anchors[0], 1e-12),
                        anchors[1] - anchors[0], unit))
        else:
            L.append("  -> the synthetic instances do NOT help: %+.3f %s per"
                     % (d, unit))
            L.append("     configuration. Filling the instance space did not make")
            L.append("     a held-out REAL dataset more predictable.")

    text = "\n".join(L) + "\n"
    print(text)
    base_path = os.path.join(OUT_DIR, "synthetic_eval_%s_%s"
                             % (args.objective, args.features))
    with open(base_path + ".txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(base_path + ".json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=float)
    print("written: %s.{txt,json}" % base_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
