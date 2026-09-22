"""Do threshold-dependent landmarks repair the meta-feature set?

Instance space analysis located the benchmark's binding constraint, and it is
not the model class. Ten of the eleven published meta-features are properties of
the dataset, so the only thing separating two configurations of one dataset is
``log_thr`` -- which is itself not comparable across datasets, the grid running
retail at sigma = 0.0005 and pumsb at 0.95. The plane explained 0.233 of
performance variance and held 7.3 effective instances.

``landmarks.py`` adds 14 features computed from the item-support vector and the
item co-occurrence matrix, both obtained once per dataset, so every threshold is
a thresholding of the same two arrays. This script measures what they buy, on
three metrics, and is written to make the answer reportable whichever way it
comes out.

What it measures, and why each one is here
------------------------------------------
``PLS R2``       share of performance variance a linear map from the 2-D plane
                 explains. Deterministic over the whole instance set, so there
                 is no sampling question: this one either moves or it does not.

``ICC / n_eff``  between-dataset share of positional variance, and the
                 cluster-sampling design effect that converts it into an
                 effective instance count.

``LOO MAE``      leave-one-DATASET-out error of per-algorithm runtime
                 prediction, against the per-algorithm constant baseline that
                 ``evaluate.py`` reports. Given **both** ways: pooled over runs
                 (micro) and averaged over folds (macro). They disagree here,
                 and the disagreement is the finding -- a micro-average is
                 dominated by the datasets contributing the most runs, so a
                 model that avoids two catastrophic folds can post a large
                 pooled gain while being no better on average.

``bootstrap``    paired resampling over the seven held-out datasets. With seven
                 folds almost nothing reaches significance, and reporting the
                 interval is the only way to keep the pooled number from being
                 read as more than it is.

``fingerprint``  accuracy of predicting *which dataset* an instance came from,
                 from its features alone. A set that identifies the dataset
                 perfectly carries dataset identity rather than instance
                 structure, and cannot generalise to an unseen dataset however
                 well it fits.

A warning this script exists to deliver
---------------------------------------
**A better instance plane does not imply a better selector, and it is measured
here that it can mean a worse one.** On the memory objective the landmarks raise
the plane's explained performance variance from 0.296 to 0.514 and cut the ICC
from 0.986 to 0.658 — every instance-space metric improves — while the best
selector's nPAR10 goes from 0.429 to 0.820 and its bootstrap band stops excluding
1.0 (``bench_selectors --objective memory --features landmarks``).

The two quantities are not the same question. The plane's R^2 asks how well a
*linear map from two dimensions* predicts the cost matrix. Selection asks only
for the correct *argmin at each point*, which a projection can get wrong while
fitting the overall surface better. Instance space analysis is a tool for
understanding a benchmark's structure, and reporting its R^2 as evidence that
selection will work is a mistake this repository nearly made.

    python -m recommender.feature_ablation
    python -m recommender.feature_ablation --objective memory
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from . import instance_space as isa
from .perfmodel import (load_runs, design_columns, rows_with_features,
                        FEATURE_SETS, TIMEOUT_S, PAR_PENALTY)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")

SETS = ("static", "landmarks", "both")
LABELS = {"static": "static (published, 11)",
          "landmarks": "landmarks only (14)",
          "both": "static + landmarks (25)"}


# ----------------------------------------------------------------------
def plane_metrics(df, kind, category, objective):
    """PLS/PCA explained performance variance, ICC and effective instances."""
    sub = rows_with_features(df, kind)
    cols = design_columns(kind)
    sub = sub[sub.category == category].copy()
    if objective == "runtime":
        sub["cost"] = np.where(sub.completed, sub.runtime_s.clip(lower=1e-3),
                               TIMEOUT_S * PAR_PENALTY)
    else:
        sub = sub[sub.completed]
        sub["cost"] = sub.peak_memory_mb
    sub = sub.dropna(subset=["cost"])
    cost = sub.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                           values="cost", aggfunc="min")
    cost = cost.dropna(axis=1, how="any").dropna(axis=0, how="any")
    feats = (sub.drop_duplicates(subset=["dataset", "param_value"])
                .set_index(["dataset", "param_value"])[cols]).reindex(cost.index)
    if len(cost) < 5 or cost.shape[1] < 2:
        return None
    Z, r2_pls, _ = isa.project(feats, cost, "pls")
    _Zp, r2_pca, _ = isa.project(feats, cost, "pca")
    eff = isa.effective_instances(Z, feats)
    return {"pls_r2": r2_pls, "pca_r2": r2_pca,
            "icc": eff["between_dataset_share"],
            "n_eff": eff["effective_instances"],
            "n_inst": int(len(cost)), "n_algos": int(cost.shape[1])}


# ----------------------------------------------------------------------
def loo_fold_errors(df, kind, category):
    """Per-held-out-dataset MAE of log10 runtime: model and constant baseline."""
    from sklearn.ensemble import RandomForestRegressor

    sub = rows_with_features(df, kind)
    sub = sub[(sub.category == category) & sub.completed].copy()
    sub["y"] = np.log10(sub.runtime_s.clip(lower=1e-3))
    cols = design_columns(kind)

    out = {}
    for ds in sorted(sub.dataset.unique()):
        tr, te = sub[sub.dataset != ds], sub[sub.dataset == ds]
        em, ec = [], []
        for algo, gte in te.groupby("algorithm"):
            gtr = tr[tr.algorithm == algo]
            if len(gtr) < 8:
                continue
            m = RandomForestRegressor(n_estimators=200, min_samples_leaf=2,
                                      random_state=0, n_jobs=1)
            m.fit(gtr[cols].to_numpy(float), gtr.y.values)
            em.extend(np.abs(m.predict(gte[cols].to_numpy(float)) - gte.y.values))
            ec.extend(np.abs(gtr.y.mean() - gte.y.values))
        if em:
            out[ds] = {"model": float(np.mean(em)), "const": float(np.mean(ec)),
                       "n": len(em), "errors": np.asarray(em)}
    return out


def paired_bootstrap(fold_a, fold_b, n_boot=10000, seed=0):
    """P(a better than b) and a CI on the macro-MAE difference, over folds."""
    keys = sorted(set(fold_a) & set(fold_b))
    a = np.array([fold_a[k]["model"] for k in keys])
    b = np.array([fold_b[k]["model"] for k in keys])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    diffs = a[idx].mean(axis=1) - b[idx].mean(axis=1)
    return {"delta": float(a.mean() - b.mean()),
            "lo": float(np.percentile(diffs, 2.5)),
            "hi": float(np.percentile(diffs, 97.5)),
            "p_better": float((diffs < 0).mean()),
            "n_folds": len(keys)}


def fingerprint_accuracy(df, kind, category, seed=0):
    """How well the features alone identify the source dataset."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score

    sub = rows_with_features(df, kind)
    sub = sub[sub.category == category]
    inst = sub.drop_duplicates(subset=["dataset", "param_value"])
    if inst.dataset.nunique() < 2:
        return float("nan")
    X = inst[design_columns(kind)].to_numpy(float)
    y = inst.dataset.values
    n_min = int(pd.Series(y).value_counts().min())
    cv = max(2, min(5, n_min))
    return float(cross_val_score(
        RandomForestClassifier(n_estimators=200, random_state=seed),
        X, y, cv=cv).mean())


# ----------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", type=int, default=1)
    ap.add_argument("--objective", default="runtime", choices=("runtime", "memory"))
    args = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_runs()
    report, L = {}, []

    def say(s=""):
        L.append(s)

    say("=" * 78)
    say("FEATURE-SET ABLATION  (category %d, objective %s)" % (args.category, args.objective))
    say("=" * 78)
    say()
    say("  Does describing the THRESHOLD, not just the dataset, repair the")
    say("  meta-feature set? Reported three ways because they disagree.")
    say()

    # --- 1. the instance plane ---------------------------------------
    say("  INSTANCE PLANE  (deterministic over the whole instance set)")
    say("  %-26s %8s %8s %7s %9s %7s" %
        ("feature set", "PLS R2", "PCA R2", "ICC", "n_eff", "n_inst"))
    say("  " + "-" * 70)
    for kind in SETS:
        m = plane_metrics(df, kind, args.category, args.objective)
        if m is None:
            say("  %-26s (too few instances)" % LABELS[kind]); continue
        report["plane/" + kind] = m
        say("  %-26s %8.3f %8.3f %7.3f %9.1f %7d"
            % (LABELS[kind], m["pls_r2"], m["pca_r2"], m["icc"], m["n_eff"],
               m["n_inst"]))
    say()

    # --- 2. leave-one-dataset-out runtime prediction ------------------
    folds = {k: loo_fold_errors(df, k, args.category) for k in SETS}
    ds_all = sorted(set().union(*[set(f) for f in folds.values()]))
    say("  LEAVE-ONE-DATASET-OUT MAE of log10 runtime, per fold")
    say("  %-14s %6s %9s %10s %11s %8s" %
        ("held out", "n", "constant", "static", "landmarks", "both"))
    say("  " + "-" * 66)
    for ds in ds_all:
        row = "  %-14s" % ds
        f0 = folds["static"].get(ds)
        row += "%6d" % (f0["n"] if f0 else 0)
        row += "%10.3f" % (f0["const"] if f0 else float("nan"))
        for k in SETS:
            f = folds[k].get(ds)
            row += "%11.3f" % (f["model"] if f else float("nan"))
        say(row)
    say("  " + "-" * 66)

    macro = {}
    for k in SETS:
        vals = [folds[k][d]["model"] for d in folds[k]]
        macro[k] = float(np.mean(vals)) if vals else float("nan")
    const_macro = float(np.mean([folds["static"][d]["const"] for d in folds["static"]]))
    micro = {}
    for k in SETS:
        e = np.concatenate([folds[k][d]["errors"] for d in folds[k]]) if folds[k] else np.array([])
        micro[k] = float(e.mean()) if e.size else float("nan")
    const_micro = float(np.concatenate(
        [np.full(folds["static"][d]["n"], folds["static"][d]["const"])
         for d in folds["static"]]).mean()) if folds["static"] else float("nan")

    say("  %-14s %6s %10.3f%s" % ("MACRO (fold)", "", const_macro,
                                  "".join("%11.3f" % macro[k] for k in SETS)))
    say("  %-14s %6s %10.3f%s" % ("MICRO (run)", "", const_micro,
                                  "".join("%11.3f" % micro[k] for k in SETS)))
    report["macro"] = dict(constant=const_macro, **macro)
    report["micro"] = dict(constant=const_micro, **micro)
    say()
    beats_macro = [k for k in SETS if macro[k] < const_macro]
    beats_micro = [k for k in SETS if micro[k] < const_micro]
    say("    beats the constant baseline on the MACRO average: %s"
        % (", ".join(beats_macro) or "none"))
    say("    beats it on the MICRO average: %s"
        % (", ".join(beats_micro) or "none"))
    if set(beats_macro) != set(beats_micro):
        say("    The two averages DISAGREE. A micro-average weights datasets by")
        say("    their run count, so avoiding a few catastrophic folds shows up")
        say("    there and not in the per-fold mean. Report both.")
    say()

    # --- 3. is any of it significant at seven folds? ------------------
    say("  PAIRED BOOTSTRAP over held-out datasets (10000 resamples)")
    for k in ("landmarks", "both"):
        bs = paired_bootstrap(folds[k], folds["static"])
        report["bootstrap/%s_vs_static" % k] = bs
        wins = sum(1 for d in folds[k]
                   if d in folds["static"] and folds[k][d]["model"] < folds["static"][d]["model"])
        say("    %-22s delta %+.3f  95%% CI %+.3f..%+.3f  P(better) %.2f  "
            "wins %d/%d folds"
            % (k + " vs static", bs["delta"], bs["lo"], bs["hi"],
               bs["p_better"], wins, bs["n_folds"]))
    say()
    say("    A CI spanning zero at seven folds is the expected outcome, not a")
    say("    surprise: it is the same small-meta-sample problem the effective")
    say("    instance count measures. It is reported so the pooled gain above is")
    say("    not read as an established improvement.")
    say()

    # --- 4. fingerprinting -------------------------------------------
    say("  DATASET-FINGERPRINT ACCURACY (1.000 = features carry dataset identity)")
    for k in SETS:
        acc = fingerprint_accuracy(df, k, args.category)
        report["fingerprint/" + k] = acc
        say("    %-26s %.3f" % (LABELS[k], acc))
    say()

    text = "\n".join(L) + "\n"
    print(text)
    base = os.path.join(OUT_DIR, "feature_ablation_%s_cat%d"
                        % (args.objective, args.category))
    with open(base + ".txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=float)
    print("written: %s.{txt,json}" % base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
