"""Leave-one-dataset-out comparison of algorithm-selection strategies.

Reports normalized PAR10, the metric used throughout the algorithm-selection
literature, so these numbers can be read against published scenarios rather
than only against each other:

    nPAR10 = (PAR10_selector - PAR10_VBS) / (PAR10_SBS - PAR10_VBS)

    0    oracle-perfect
    < 1  better than always running the single best algorithm
    1    no better than the single best
    > 1  actively worse than not selecting at all

Folds hold out a whole DATASET, never a single run: with seven transactional
datasets, leave-one-run-out would test on near-duplicate configurations of the
same data and inflate every number.

    python -m recommender.bench_selectors
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from . import metafeatures as mf
from .perfmodel import load_runs, design_columns, rows_with_features, FEATURE_SETS
from .selectors import (CUTOFF, PAR_FACTOR, PairwiseRankSelector,
                        RegressionSelector, SBSSelector, SurvivalSelector,
                        npar10, par10, SunnySelector, RandomSelector)

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")


def _cut(objective):
    """The cutoff that defines a censored observation for this objective."""
    return CUTOFF if objective == "runtime" else globals().get("_CUT", CUTOFF)


def build_selectors():
    return [
        SBSSelector(),
        RandomSelector(),
        SunnySelector(k=16),
        RegressionSelector(),
        PairwiseRankSelector(),
        SurvivalSelector(rule="expected_runtime"),
        SurvivalSelector(rule="expected_par10"),
        SurvivalSelector(rule="risk_averse", alpha=0.3),
    ]


SPMF_TRANS = ["DefMe", "Pascal", "Zart", "Talky_G", "TalkyG_Diffset"]
PORTFOLIOS = {
    "all": None,
    "spmf": SPMF_TRANS,
    "dedicated": SPMF_TRANS + ["Gr_growth"],
}


def _cluster_bootstrap(res, names, sbs_name, n_boot=5000, seed=0):
    """Cluster bootstrap over held-out datasets; returns nPAR10 bands.

    Resamples whole datasets with replacement, recomputing the VBS and SBS
    anchors inside each resample so the interval reflects uncertainty in the
    normaliser too. Reported as a 5-95% band to match the equivalence-tier
    convention used elsewhere in the recommender.
    """
    datasets = res.dataset.unique()
    if len(datasets) < 3:
        return {}
    groups = {d: res[res.dataset == d] for d in datasets}
    rng = np.random.default_rng(seed)
    draws = {n: [] for n in names}
    for _ in range(n_boot):
        pick = rng.integers(0, len(datasets), len(datasets))
        sample = pd.concat([groups[datasets[i]] for i in pick], ignore_index=True)
        vbs_b, sbs_b = sample.vbs.mean(), sample[sbs_name].mean()
        if abs(sbs_b - vbs_b) < 1e-12:
            continue
        for n in names:
            draws[n].append(npar10(sample[n].mean(), sbs_b, vbs_b))
    out = {}
    for n, vals in draws.items():
        v = np.asarray([x for x in vals if np.isfinite(x)], dtype=float)
        if v.size < 50:
            continue
        out[n] = {"npar10_lo": float(np.percentile(v, 5)),
                  "npar10_hi": float(np.percentile(v, 95)),
                  "p_beats_sbs": float((v < 1.0).mean())}
    return out


def run(df, category=1, verbose=True, portfolio="all", objective="runtime",
        features="static"):
    """Compare selectors under one portfolio and one objective.

    `objective` matters more than any model choice. Measured with
    ``recommender.complementarity``, runtime headroom on the full portfolio is
    1.011x -- there is essentially nothing to select, and on the dedicated-miner
    portfolio Gr-growth wins 58 of 58 configurations. The one slice with real
    headroom is memory over the full portfolio (3.660x), where the algorithms
    that win are not the ones that win on runtime.

    Peak memory is censored in the same sense as runtime: a run killed at the
    cutoff recorded the memory it had reached, which is a LOWER BOUND on what it
    would have used. The survival machinery therefore applies unchanged.
    """
    # Which feature set is a reported choice, not a hardcoded one: the ablation
    # in feature_ablation.py shows the answer depends on the objective, with
    # threshold-dependent landmarks doubling the instance plane's explained
    # performance variance while not improving selection on memory.
    cols = design_columns(features)
    sub = rows_with_features(df, features)
    sub = sub[sub.category == category].copy()
    algos = PORTFOLIOS.get(portfolio)
    if algos is not None:
        sub = sub[sub.algorithm.isin(algos)]
    if sub.empty:
        return sub, {}

    if objective == "memory":
        # Peak memory must NOT get a PAR10-style penalty. The memory of a run
        # killed at the cutoff was actually observed -- it is a lower bound on
        # what the run would have reached, not a missing value -- so
        # multiplying it by ten invents a number, which is the very practice
        # the censoring literature warns against. Restrict instead to the
        # configurations where every candidate completed, where no penalty and
        # no censoring decision is needed. Measured both ways: the invented
        # penalty produced an apparent 4.35x headroom where the clean subset
        # shows 1.02x, so the penalty was manufacturing the result.
        ok = sub[sub.completed]
        wide = ok.pivot_table(index=["dataset", "param_value"],
                              columns="algorithm", values="peak_memory_mb",
                              aggfunc="min")
        complete_idx = set(wide.dropna(axis=0, how="any").index)
        sub = sub[[(d_, p_) in complete_idx
                   for d_, p_ in zip(sub.dataset, sub.param_value)]]
        sub = sub[sub.completed]
        if sub.empty:
            return sub, {}
        sub = sub.assign(runtime_s=sub.peak_memory_mb)
        sub["par10"] = sub.peak_memory_mb.astype(float)
    else:
        sub["par10"] = [par10(r, c) for r, c in zip(sub.runtime_s, sub.completed)]
    datasets = sorted(sub.dataset.unique())

    rows = []
    for held in datasets:
        train = sub[sub.dataset != held]
        test = sub[sub.dataset == held]
        if train.empty or test.empty:
            continue

        fitted = []
        for s in build_selectors():
            fitted.append(s.fit(train, cols))

        for (thr,), g in test.groupby(["param_value"]):
            costs = dict(zip(g.algorithm, g.par10))
            done = dict(zip(g.algorithm, g.completed))
            candidates = sorted(costs)
            if len(candidates) < 2:
                continue
            x = g[cols].iloc[0].to_numpy(float)

            vbs_algo = min(costs, key=costs.get)
            rec = {"dataset": held, "param_value": thr,
                   "vbs": costs[vbs_algo], "vbs_algo": vbs_algo}
            for s in fitted:
                pick = s.select(x, candidates)
                rec[s.name] = costs[pick]
                rec[s.name + " |pick"] = pick
                rec[s.name + " |timeout"] = not done[pick]
            rows.append(rec)

    res = pd.DataFrame(rows)
    if res.empty:
        return res, {}

    names = [s.name for s in build_selectors()]
    sbs_name = SBSSelector().name
    vbs_total = res.vbs.mean()
    sbs_total = res[sbs_name].mean()

    summary = {}
    for n in names:
        cost = res[n].mean()
        summary[n] = {
            "par10_mean": float(cost),
            "npar10": float(npar10(cost, sbs_total, vbs_total)),
            "top1": float((res[n] == res.vbs).mean()),
            "timeouts": int(res[n + " |timeout"].sum()),
        }
    summary["VBS (oracle)"] = {"par10_mean": float(vbs_total), "npar10": 0.0,
                               "top1": 1.0,
                               "timeouts": int((res.vbs >= CUTOFF * PAR_FACTOR).sum())}

    # Confidence intervals, by resampling the HELD-OUT DATASETS rather than the
    # individual configurations. Configurations of one dataset are not
    # independent -- that non-independence is exactly what the effective instance
    # count of 7.3 measures -- so an instance-level bootstrap would report
    # intervals several times too narrow. Resampling clusters keeps the
    # dependence intact, at the price of intervals wide enough to show how
    # little seven datasets settle. nPAR10 is recomputed inside each resample,
    # because its denominator is itself estimated from the same data.
    ci = _cluster_bootstrap(res, names, sbs_name)
    for n, band in ci.items():
        if n in summary:
            summary[n].update(band)

    if verbose:
        print("=" * 78)
        print("LEAVE-ONE-DATASET-OUT SELECTOR COMPARISON  (category %d)" % category)
        print("=" * 78)
        print("  portfolio=%s  objective=%s" % (portfolio, objective))
        print("  %d datasets, %d held-out configurations, %d candidate algorithms"
              % (len(datasets), len(res), sub.algorithm.nunique()))
        print("  headroom SBS/VBS on this slice: %.3fx"
              % (sbs_total / max(vbs_total, 1e-12)))
        print("  censored runs in this category: %d of %d (%.1f%%)"
              % ((~sub.completed).sum(), len(sub), 100 * (~sub.completed).mean()))
        print()
        print("  %-30s %12s %9s %17s %8s %7s"
              % ("selector", "PAR10 mean", "nPAR10", "5-95% band", "top-1",
                 "P(<SBS)"))
        print("  " + "-" * 90)
        order = sorted(summary, key=lambda k: summary[k]["npar10"])
        for n in order:
            s = summary[n]
            mark = ""
            if n == sbs_name:
                mark = "  <- baseline"
            elif s["npar10"] < 1.0 and n != "VBS (oracle)":
                mark = "  beats SBS"
            band = ("%7.3f..%-7.3f" % (s["npar10_lo"], s["npar10_hi"])
                    if "npar10_lo" in s else "%16s" % "-")
            pb = ("%6.2f" % s["p_beats_sbs"]) if "p_beats_sbs" in s else "     -"
            print("  %-30s %12.1f %9.3f %17s %7.1f%% %7s%s"
                  % (n, s["par10_mean"], s["npar10"], band, 100 * s["top1"],
                     pb, mark))
        print()
        best = min((k for k in summary if k not in (sbs_name, "VBS (oracle)")),
                   key=lambda k: summary[k]["npar10"])
        if summary[best]["npar10"] < 1.0:
            print("  Best learned selector: %s (nPAR10 %.3f), closing %.0f%% of the"
                  % (best, summary[best]["npar10"],
                     100 * (1 - summary[best]["npar10"])))
            print("  gap between the single best algorithm and the oracle.")
        else:
            print("  NO learned selector beats the fixed single-best choice")
            print("  (all nPAR10 >= 1). On this benchmark, per-instance selection")
            print("  on performance is not justified -- report it as such.")
    return res, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", type=int, default=1)
    ap.add_argument("--portfolio", default="all", choices=sorted(PORTFOLIOS))
    ap.add_argument("--features", default="static", choices=FEATURE_SETS,
                    help="feature set for every learned selector (default: the "
                         "published static set)")
    ap.add_argument("--objective", default="runtime",
                    choices=["runtime", "memory"])
    args = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_runs()
    res, summary = run(df, category=args.category, portfolio=args.portfolio,
                       objective=args.objective, features=args.features)
    if res.empty:
        print("no folds")
        return 1
    tag = "%s_%s_%s_cat%d" % (args.portfolio, args.objective, args.features,
                              args.category)
    csv_path = os.path.join(OUT_DIR, "selector_%s.csv" % tag)
    res.to_csv(csv_path, index=False)
    with open(os.path.join(OUT_DIR, "selector_%s.json" % tag), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print("\nwritten: %s" % csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
