"""Experiments.

Four experiments, run with ``python -m recommender.evaluate``:

  E1  Oracle gap.  How much does per-instance selection buy on performance
      alone?  This is the standard justification for an algorithm-selection
      paper, and reporting it is what stops the contribution being oversold.

  E2  Semantic error rate of a performance-first selector.  The headline.
      A selector given a PERFECT performance oracle -- strictly stronger than
      anything learnable -- still returns an implementation that answers a
      different question than the one asked, on a measurable fraction of
      queries.  Layer 2 removes those errors by construction.

  E3  Leave-one-dataset-out accuracy of the Layer 3 performance model against
      a per-algorithm constant baseline.  With seven transactional datasets,
      beating the constant is not a foregone conclusion; if the model loses,
      that is the result.

  E4  Is implementation unsoundness predictable from meta-features?  Talky-G
      fails on 7 of its 57 configurations.  A positive result here would be a
      learned predictor of implementation defects; a negative one argues that
      capability profiles must be measured rather than inferred, which is
      itself an argument for the audit.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from . import metafeatures as mf
from .capabilities import CapabilityDB
from .perfmodel import PerformanceModel, load_runs, TIMEOUT_S, PAR_PENALTY
from .spec import MiningTask

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")

#: The family a user asks for, per input type, in the ordinary case.
DEFAULT_REQUEST = {
    "transactional": "minimal_generator",
    "sequential": "sequential_generator",
    "utility": "high_utility_generator",
}

DATA_TYPE_OF_CATEGORY = {1: "transactional", 2: "sequential", 3: "utility",
                         5: "transactional"}


def _banner(title):
    return "\n" + "=" * 78 + "\n" + title + "\n" + "=" * 78


# ======================================================================
# E1 - oracle gap
# ======================================================================
def e1_oracle_gap(df, category=1):
    L = [_banner("E1  ORACLE GAP -- what per-instance selection buys on performance alone")]
    # Restricted to one benchmark category: categories use different parameter
    # grids (minsup vs maxsup vs min_utility), so pooling them would compare
    # implementations that were never run on the same configuration.
    sub = df[df.category == category].copy()
    sub["cost"] = np.where(sub.completed,
                           sub.runtime_s.clip(lower=0.01),
                           TIMEOUT_S * PAR_PENALTY)
    p = sub.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                        values="cost", aggfunc="min")
    p = p.dropna(axis=1, how="any")          # algorithms present on every config
    if p.empty:
        L.append("  (insufficient overlap)")
        return "\n".join(L), {}

    vbs = p.min(axis=1)
    gm = np.exp(np.log(p.div(vbs, axis=0)).mean()).sort_values()
    par = p.mean().sort_values()

    L.append("  %d configurations, %d implementations with full coverage\n"
             % (len(p), p.shape[1]))
    L.append("  %-26s %14s %16s" % ("implementation", "PAR10 mean s", "geo-mean vs VBS"))
    L.append("  " + "-" * 58)
    for a in par.index:
        L.append("  %-26s %14.3f %16.3f" % (a, par[a], gm[a]))
    L.append("  %-26s %14.3f %16.3f" % ("VIRTUAL BEST (oracle)", vbs.mean(), 1.0))

    sbs = par.index[0]
    win = p.idxmin(axis=1).value_counts()
    L.append("")
    L.append("  single best (SBS)          : %s" % sbs)
    L.append("  VBS/SBS on PAR10 mean      : %.3fx" % (par.iloc[0] / vbs.mean()))
    L.append("  VBS/SBS on geo-mean        : %.3fx" % gm.iloc[0])
    L.append("  configurations won by SBS  : %d of %d (%.1f%%)"
             % (win.get(sbs, 0), len(p), 100 * win.get(sbs, 0) / len(p)))
    L.append("")
    L.append("  READ THIS AS A NEGATIVE RESULT: a perfect per-instance selector")
    L.append("  improves on 'always run the single best implementation' by only")
    L.append("  %.1f%% in geometric mean. Performance prediction cannot carry a" % (100 * (gm.iloc[0] - 1)))
    L.append("  paper on this benchmark; it is a supporting component, not the claim.")

    # memory tells a different story, and the two objectives conflict
    ok = sub[sub.completed]
    pm = ok.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                        values="peak_memory_mb", aggfunc="min")
    pm = pm[[c for c in p.columns if c in pm.columns]].dropna(axis=0, how="any")
    stats = {"n_configs": int(len(p)), "vbs_sbs_geo": float(gm.iloc[0]),
             "sbs": sbs, "runtime_geo": {k: float(v) for k, v in gm.items()}}
    if not pm.empty:
        gmm = np.exp(np.log(pm.div(pm.min(axis=1), axis=0)).mean()).sort_values()
        L.append("")
        L.append("  Memory, on the %d configurations where every implementation completed:" % len(pm))
        for a in gmm.index:
            L.append("    %-26s %8.3fx vs per-config best" % (a, gmm[a]))
        best_rt, best_mem = gm.index[0], gmm.index[0]
        stats["memory_geo"] = {k: float(v) for k, v in gmm.items()}
        if best_rt != best_mem:
            L.append("")
            L.append("  The objectives CONFLICT: %s is best on runtime (%.2fx) but"
                     % (best_rt, gm[best_rt]))
            L.append("  %.2fx on memory, while %s is best on memory (%.2fx) but %.2fx"
                     % (gmm.get(best_rt, float('nan')), best_mem, gmm[best_mem],
                        gm.get(best_mem, float('nan'))))
            L.append("  on runtime. Pareto-front recommendation under a declared budget is")
            L.append("  therefore defensible where 'predict the fastest' is not.")
    return "\n".join(L), stats


# ======================================================================
# E2 - semantic error rate of a performance-first selector
# ======================================================================
def e2_semantic_errors(df, db):
    L = [_banner("E2  SEMANTIC ERROR RATE of a performance-first selector  [HEADLINE]")]
    L.append("""
  The selector below is given the TRUE measured runtime and memory of every
  implementation on every configuration -- a perfect performance oracle,
  strictly stronger than any learned model. It then picks the cheapest
  implementation that accepts the input format, exactly as an
  algorithm-selection framework that assumes semantic interchangeability
  would. Layer 2 then checks whether that pick computes what was requested.

  The workload is the cross product of every benchmark configuration with a
  set of REQUIREMENT PROFILES and OBJECTIVES. The profiles matter because a
  user's specification is not exhausted by the pattern family: which side of
  a non-integral threshold is kept, and whether the empty pattern is
  reported, change the output set. A performance-first selector has no
  channel in which those requirements can even be expressed.
""".rstrip())

    profiles = [
        ("default", dict()),
        ("floor boundary", dict(boundary="floor")),
        ("ceil boundary", dict(boundary="ceil")),
        ("empty set required", dict(include_empty=True)),
        ("empty set forbidden", dict(include_empty=False)),
    ]
    objectives = ("runtime", "memory")

    rows = []
    for (ds, thr), g in df.groupby(["dataset", "param_value"]):
        dtype = mf.DATASET_TYPES.get(ds)
        family = DEFAULT_REQUEST.get(dtype) if dtype else None
        if family is None:
            continue
        cand = g[g.completed]
        if cand.empty:
            continue
        for obj in objectives:
            col = "runtime_s" if obj == "runtime" else "peak_memory_mb"
            if cand[col].isna().all():
                continue
            pick = cand.loc[cand[col].idxmin(), "algorithm"]
            for pname, extra in profiles:
                task = MiningTask(data_type=dtype, family=family, dataset=ds,
                                  threshold=float(thr), trust="verified_only",
                                  objective=obj, **extra)
                v = db.evaluate(pick, task)
                elig = [a for a in cand.algorithm if db.evaluate(a, task).eligible]
                safe, safe_cost = None, float("nan")
                if elig:
                    sub = cand[cand.algorithm.isin(elig)]
                    safe = sub.loc[sub[col].idxmin(), "algorithm"]
                    safe_cost = float(sub[col].min())
                rows.append({
                    "dataset": ds, "threshold": thr, "data_type": dtype,
                    "profile": pname, "objective": obj,
                    "perf_pick": pick, "perf_ok": v.eligible,
                    "reason": "ok" if v.eligible else (v.reasons[0] if v.reasons else "rejected"),
                    "perf_cost": float(cand[col].min()),
                    "safe_pick": safe, "safe_cost": safe_cost,
                    "no_safe_option": safe is None,
                })

    r = pd.DataFrame(rows)
    if r.empty:
        L.append("  (no queries)")
        return "\n".join(L), {}

    bad = r[~r.perf_ok]
    L.append("")
    L.append("  queries = %d configurations x %d profiles x %d objectives = %d"
             % (r.groupby(['dataset', 'threshold']).ngroups, len(profiles),
                len(objectives), len(r)))
    L.append("  performance-first pick violates the specification : %d (%.1f%%)"
             % (len(bad), 100 * len(bad) / len(r)))
    L.append("  semantics-first pick violates it                  : 0 (0.0%) by construction")
    L.append("")

    L.append("  By requirement profile:")
    L.append("    %-22s %8s %8s %9s" % ("profile", "queries", "wrong", "rate"))
    L.append("    " + "-" * 50)
    for pname, _ in profiles:
        sub = r[r.profile == pname]
        w = int((~sub.perf_ok).sum())
        L.append("    %-22s %8d %8d %8.1f%%"
                 % (pname, len(sub), w, 100 * w / max(len(sub), 1)))
    L.append("")
    L.append("  By objective:")
    for obj in objectives:
        sub = r[r.objective == obj]
        w = int((~sub.perf_ok).sum())
        L.append("    %-22s %8d %8d %8.1f%%"
                 % (obj, len(sub), w, 100 * w / max(len(sub), 1)))

    if not bad.empty:
        L.append("")
        L.append("  Failure modes:")
        for reason, gg in bad.groupby("reason"):
            L.append("    %4d x  %s" % (len(gg), reason[:92]))
            picks = ", ".join("%s(%d)" % (k, v)
                              for k, v in gg.perf_pick.value_counts().items())
            L.append("            picked: %s" % picks)
            L.append("            on: %s" % ", ".join(sorted(gg.dataset.unique())))

    # Price of correctness, only where a compliant alternative exists.
    both = r[r.perf_ok.eq(False) & r.safe_cost.notna() & (r.perf_cost > 0)]
    if not both.empty:
        ratio = (both.safe_cost / both.perf_cost).replace([np.inf], np.nan).dropna()
        L.append("")
        L.append("  PRICE OF CORRECTNESS on the %d queries where the performance-first"
                 % len(ratio))
        L.append("  pick was non-compliant -- cost of the cheapest COMPLIANT")
        L.append("  implementation relative to that non-compliant pick:")
        L.append("    geometric mean %.3fx, median %.3fx, worst %.2fx"
                 % (float(np.exp(np.log(ratio.clip(lower=1e-9)).mean())),
                    float(ratio.median()), float(ratio.max())))

    unmet = r[r.no_safe_option]
    if not unmet.empty:
        L.append("")
        L.append("  UNSATISFIABLE: %d queries (%.1f%%) admit no compliant implementation"
                 % (len(unmet), 100 * len(unmet) / len(r)))
        for pname, gg in unmet.groupby("profile"):
            L.append("    %-22s %4d queries, e.g. %s"
                     % (pname, len(gg), ", ".join(sorted(gg.dataset.unique())[:4])))
        L.append("  A recommender that reports 'no implementation satisfies this")
        L.append("  specification' is giving the correct answer; a performance-first")
        L.append("  selector returns a fast implementation instead.")

    stats = {"n_queries": int(len(r)), "n_wrong": int(len(bad)),
             "wrong_rate": float(len(bad) / len(r)),
             "unsatisfiable": int(len(unmet)),
             "by_profile": {p: float((~r[r.profile == p].perf_ok).mean())
                            for p, _ in profiles}}
    r.to_csv(os.path.join(OUT_DIR, "e2_semantic_errors.csv"), index=False)
    return "\n".join(L), stats


# ======================================================================
# E3 - leave-one-dataset-out accuracy of the performance model
# ======================================================================
def e3_lodo(df, data_type="transactional"):
    L = [_banner("E3  LEAVE-ONE-DATASET-OUT accuracy of the Layer 3 performance model")]
    from scipy.stats import spearmanr

    sub = df[df.dataset.map(mf.DATASET_TYPES).eq(data_type)].copy()
    datasets = sorted(sub.dataset.unique())
    L.append("  %d datasets, %d runs, folds = leave one DATASET out"
             % (len(datasets), len(sub)))
    L.append("  (leave-one-RUN-out would test on near-duplicates and inflate every number)")
    L.append("")

    recs, regret_rows = [], []
    for held in datasets:
        train = sub[sub.dataset != held]
        test = sub[(sub.dataset == held) & sub.completed]
        if test.empty or train.empty:
            continue
        model = PerformanceModel().fit(train)
        feats = mf.for_dataset(held)
        # Single Best Solver for this fold, chosen on the TRAINING datasets only.
        tr_ok = train[train.completed]
        sbs_algo = (np.log10(tr_ok.runtime_s.clip(lower=1e-3))
                    .groupby(tr_ok.algorithm).mean().idxmin()) if len(tr_ok) else None
        per_cfg = defaultdict(dict)
        for _, row in test.iterrows():
            pred = model.predict(row.algorithm, feats, row.param_value)
            if pred is None:
                continue
            per_cfg[row.param_value][row.algorithm] = (pred["runtime_s"], row.runtime_s)
            recs.append({
                "dataset": held, "algorithm": row.algorithm,
                "param_value": row.param_value,
                "pred_log": np.log10(max(pred["runtime_s"], 1e-3)),
                "true_log": np.log10(max(row.runtime_s, 1e-3)),
                "const_log": model.fallback[row.algorithm]["rt"],
                "pred": pred["runtime_s"], "true": row.runtime_s,
            })
        # selection regret per configuration
        for thr, d in per_cfg.items():
            if len(d) < 2:
                continue
            chosen = min(d, key=lambda a: d[a][0])
            best = min(d, key=lambda a: d[a][1])
            sbs_true = d[sbs_algo][1] if sbs_algo in d else np.nan
            regret_rows.append({"dataset": held, "param_value": thr,
                                "chosen": chosen, "best": best,
                                "sbs": sbs_algo, "sbs_true": sbs_true,
                                "chosen_true": d[chosen][1], "best_true": d[best][1]})

    e = pd.DataFrame(recs)
    if e.empty:
        L.append("  (no folds)")
        return "\n".join(L), {}

    mae_model = float(np.abs(e.pred_log - e.true_log).mean())
    mae_const = float(np.abs(e.const_log - e.true_log).mean())
    rho = spearmanr(e.pred_log, e.true_log).statistic

    L.append("  runtime prediction, mean absolute error in log10 seconds")
    L.append("    meta-feature model      : %.3f  (=> typical factor %.2fx off)"
             % (mae_model, 10 ** mae_model))
    L.append("    per-algorithm constant  : %.3f  (=> typical factor %.2fx off)"
             % (mae_const, 10 ** mae_const))
    L.append("    improvement             : %+.1f%%"
             % (100 * (mae_const - mae_model) / mae_const))
    L.append("    Spearman rho (model)    : %.3f" % rho)
    L.append("")

    reg = pd.DataFrame(regret_rows)
    stats = {"mae_model": mae_model, "mae_const": mae_const, "spearman": float(rho)}
    if not reg.empty:
        reg["regret"] = reg.chosen_true - reg.best_true
        reg["ratio"] = reg.chosen_true / reg.best_true.clip(lower=1e-3)
        hit = float((reg.chosen == reg.best).mean())
        L.append("  selection quality on held-out datasets (%d configurations)" % len(reg))
        L.append("    picked the truly fastest : %.1f%%" % (100 * hit))
        L.append("    geometric-mean slowdown  : %.3fx"
                 % float(np.exp(np.log(reg.ratio.clip(lower=1e-9)).mean())))
        L.append("    median slowdown          : %.3fx" % float(reg.ratio.median()))
        geo = float(np.exp(np.log(reg.ratio.clip(lower=1e-9)).mean()))
        stats.update(top1=hit, geo_slowdown=geo)
        sb = reg.dropna(subset=["sbs_true"])
        if not sb.empty:
            sbs_ratio = (sb.sbs_true / sb.best_true.clip(lower=1e-3)).clip(lower=1e-9)
            sbs_geo = float(np.exp(np.log(sbs_ratio).mean()))
            stats["sbs_geo_slowdown"] = sbs_geo
            L.append("")
            L.append("  THE BASELINE THAT MATTERS -- always run the single best")
            L.append("  implementation, chosen on the training datasets only:")
            L.append("    single-best geo-mean slowdown : %.3fx" % sbs_geo)
            L.append("    learned selector              : %.3fx" % geo)
            if geo <= sbs_geo:
                L.append("    the learned selector WINS by %.1f%%"
                         % (100 * (sbs_geo - geo) / sbs_geo))
            else:
                L.append("    the learned selector LOSES to the fixed choice by %.1f%%"
                         % (100 * (geo - sbs_geo) / sbs_geo))
                L.append("    -- per-instance selection on performance is not")
                L.append("       justified on this benchmark. Report it as such.")
        reg.to_csv(os.path.join(OUT_DIR, "e3_selection_regret.csv"), index=False)
    e.to_csv(os.path.join(OUT_DIR, "e3_lodo_predictions.csv"), index=False)

    if mae_model >= mae_const:
        L.append("")
        L.append("  NOTE: a later analysis supersedes part of the remedy below.")
        L.append("  `recommender.complementarity` shows the runtime portfolio is")
        L.append("  not complementary at all -- Gr-growth wins 58 of 58 among the")
        L.append("  dedicated miners, and headroom over the full portfolio is")
        L.append("  1.011x. More meta-instances cannot manufacture complementarity")
        L.append("  that is not there, so synthetic data is a prerequisite for the")
        L.append("  MEMORY objective (headroom 3.642x), not for this one.")
        L.append("")
        L.append("  The model does NOT beat the constant baseline. At this")
        L.append("  meta-instance count that is the honest finding: report it, and")
        L.append("  treat synthetic instance generation as a prerequisite rather")
        L.append("  than an enhancement.")
    return "\n".join(L), stats



# ======================================================================
# E4 - is unsoundness predictable from meta-features?
# ======================================================================
def e4_defect_prediction(df, db):
    L = [_banner("E4  IS IMPLEMENTATION UNSOUNDNESS PREDICTABLE FROM META-FEATURES?")]
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score

    impl = db.get("Talky_G")
    defects = {(d["dataset"], float(d["param_value"]))
               for d in impl["soundness"]["defective_configs"]}
    sub = df[(df.algorithm == "Talky_G") & df.completed].copy()
    sub["defective"] = [
        (r.dataset, float(r.param_value)) in defects for r in sub.itertuples()]

    n_pos = int(sub.defective.sum())
    L.append("  target: does Talky-G return non-minimal itemsets on this configuration?")
    L.append("  %d completed configurations, %d positive (%.1f%%)"
             % (len(sub), n_pos, 100 * n_pos / max(len(sub), 1)))
    L.append("")
    if n_pos < 3:
        L.append("  Too few positives to evaluate.")
        return "\n".join(L), {}

    cols = list(mf.FEATURE_NAMES) + ["log_thr"]
    preds, truth, folds = [], [], []
    for held in sorted(sub.dataset.unique()):
        tr, te = sub[sub.dataset != held], sub[sub.dataset == held]
        if tr.defective.nunique() < 2 or te.empty:
            continue
        clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=1,
                                     class_weight="balanced", random_state=0)
        clf.fit(tr[cols].to_numpy(float), tr.defective.astype(int))
        p = clf.predict_proba(te[cols].to_numpy(float))[:, 1]
        preds.extend(p); truth.extend(te.defective.astype(int)); folds.extend([held] * len(te))

    if len(set(truth)) < 2:
        L.append("  Leave-one-dataset-out is degenerate here: every positive lies")
        L.append("  in a single held-out dataset, so no fold contains both classes")
        L.append("  in training AND testing. This is itself the finding -- the defect")
        L.append("  is dataset-level, not configuration-level, and 7 datasets cannot")
        L.append("  support a generalising predictor.")
        return "\n".join(L), {"status": "degenerate"}

    auc = float(roc_auc_score(truth, preds))
    # With 7 positives concentrated in a single dataset, a bare AUC is not
    # evidence. Permute the labels within the same fold structure to obtain a
    # null distribution and report the resulting p-value.
    rng = np.random.default_rng(0)
    y = np.asarray(truth)
    null = np.asarray([roc_auc_score(rng.permutation(y), preds)
                       for _ in range(2000)])
    pval = float((null >= auc).mean())
    L.append("  leave-one-dataset-out ROC AUC : %.3f" % auc)
    L.append("  label-permutation null        : mean %.3f, 95th pct %.3f, p = %.3f"
             % (null.mean(), np.percentile(null, 95), pval))
    L.append("")
    res = pd.DataFrame({"dataset": folds, "p_defective": preds, "defective": truth})
    res.to_csv(os.path.join(OUT_DIR, "e4_defect_prediction.csv"), index=False)
    for ds, g in res.groupby("dataset"):
        L.append("    %-14s %d/%d defective, mean predicted risk %.3f"
                 % (ds, int(g.defective.sum()), len(g), g.p_defective.mean()))
    L.append("")

    # A pooled AUC can be driven entirely by WITHIN-dataset ordering (which
    # threshold on a known-bad dataset is worse), which is useless to a user
    # holding a new dataset. Separate the two questions.
    per_ds = res.groupby("dataset").agg(risk=("p_defective", "mean"),
                                        pos=("defective", "sum"))
    per_ds["has_defect"] = per_ds.pos > 0
    within = []
    for ds, g in res.groupby("dataset"):
        if g.defective.nunique() > 1:
            within.append(roc_auc_score(g.defective, g.p_defective))
    if per_ds.has_defect.nunique() > 1:
        across = float(roc_auc_score(per_ds.has_defect.astype(int), per_ds.risk))
        L.append("  DECOMPOSITION of the pooled AUC")
        L.append("    across datasets (does this DATASET carry the defect?) : %.3f"
                 % across)
        if within:
            L.append("    within datasets (which THRESHOLD is affected?)        : %.3f"
                     % float(np.mean(within)))
        worst = per_ds.risk.idxmax()
        L.append("    highest-risk dataset: %s (%d defective configurations)"
                 % (worst, int(per_ds.loc[worst, "pos"])))
        L.append("")
        if across < 0.6:
            L.append("    The across-dataset AUC is what a user actually needs, and it")
            L.append("    is near chance: the model ranks %s highest while that dataset"
                     % worst)
            L.append("    carries no defect at all. The pooled figure is therefore")
            L.append("    carried by within-dataset ordering and must NOT be reported")
            L.append("    as a transferable defect predictor.")
            L.append("")
        stats_extra = {"auc_across": across,
                       "auc_within": float(np.mean(within)) if within else None}
    else:
        stats_extra = {}
    transferable = stats_extra.get("auc_across", 0.0) >= 0.7
    if auc >= 0.75 and pval < 0.05 and transferable:
        L.append("  Unsoundness IS predictable from cheap structural features at this")
        L.append("  sample size. Layer 2 can therefore issue a calibrated risk warning")
        L.append("  on datasets the audit never covered -- which is what makes the")
        L.append("  capability profile extrapolate rather than merely record.")
    else:
        L.append("  Unsoundness is NOT predictable from these features at this sample")
        L.append("  size. The capability profile must be MEASURED per implementation")
        L.append("  rather than inferred -- an argument for the audit, and against")
        L.append("  assuming that a benchmark on one dataset transfers to another.")
    if pval < 0.05 and not transferable:
        L.append("  Significant in the pooled ranking, but NOT transferable across")
        L.append("  datasets. The usable conclusion is the conservative one: a")
        L.append("  capability profile must be MEASURED per implementation, and a")
        L.append("  benchmark result on one dataset does not license an inference")
        L.append("  about another. That is an argument for the audit.")
    if pval >= 0.05:
        L.append("")
        L.append("  The AUC is NOT significant under label permutation (p = %.3f)."
                 % pval)
        L.append("  With %d positives concentrated in one dataset this experiment"
                 % n_pos)
        L.append("  cannot settle the question either way. It is reported as an open")
        L.append("  question and as a concrete motivation for enlarging the")
        L.append("  meta-instance set, not as a result.")
    return "\n".join(L), dict({"auc": auc, "n_pos": n_pos, "p_value": pval}, **stats_extra)


# ======================================================================
def main(argv=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_runs()
    db = CapabilityDB()
    out, stats = [], {}

    t, s = e1_oracle_gap(df, category=1); out.append(t); stats["E1"] = s
    t, s = e2_semantic_errors(df, db); out.append(t); stats["E2"] = s
    t, s = e3_lodo(df); out.append(t); stats["E3"] = s
    t, s = e4_defect_prediction(df, db); out.append(t); stats["E4"] = s

    report = "\n".join(out) + "\n"
    print(report)
    with open(os.path.join(OUT_DIR, "experiments.txt"), "w", encoding="utf-8") as fh:
        fh.write(report)
    with open(os.path.join(OUT_DIR, "experiments.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2, default=float)
    print("written: %s" % os.path.join(OUT_DIR, "experiments.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
