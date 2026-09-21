"""Does this portfolio have anything to select between?

Every algorithm-selection result rests on an assumption that is rarely tested:
that the candidate algorithms are *complementary* -- that different ones win on
different instances by margins worth capturing. In SAT, where the field's
methods were developed, that assumption holds strongly. Here it needs checking
before any selector is trained, because if one algorithm dominates, no model
however good can beat simply running it.

Three measurements, all standard:

  marginal contribution   How much worse the virtual best solver gets when an
                          algorithm is removed from the portfolio. An algorithm
                          with zero marginal contribution is redundant: it is
                          never uniquely best.

  SBS/VBS ratio           The headroom available to any selector at all. A
                          ratio near 1 means the single best fixed choice is
                          already near-optimal.

  Shapley-style share     Marginal contribution normalised across algorithms,
                          so portfolios of different sizes can be compared.

Run over several PORTFOLIOS, because the answer depends on what a user actually
has installed. The three Borgelt binaries are native C post-filtering baselines
distributed separately from SPMF; including them changes the conclusion
entirely, and a practitioner without them faces a different problem.

    python -m recommender.complementarity
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from .perfmodel import load_runs, TIMEOUT_S, PAR_PENALTY

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")

SPMF_TRANS = ["DefMe", "Pascal", "Zart", "Talky_G", "TalkyG_Diffset"]
NATIVE = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt"]

PORTFOLIOS = {
    "everything available": None,
    "SPMF only": SPMF_TRANS,
    "dedicated generator miners": SPMF_TRANS + ["Gr_growth"],
    "native post-filters only": NATIVE,
}


def cost_matrix(df, category, algos=None, objective="runtime"):
    sub = df[df.category == category]
    if algos is not None:
        sub = sub[sub.algorithm.isin(algos)]
    if objective == "runtime":
        val = np.where(sub.completed, sub.runtime_s, TIMEOUT_S * PAR_PENALTY)
    else:
        # A run that never finished has no meaningful peak memory to compare,
        # so it is penalised on the same principle as PAR10.
        cap = sub.peak_memory_mb.max() * PAR_PENALTY
        val = np.where(sub.completed, sub.peak_memory_mb, cap)
    sub = sub.assign(_cost=val)
    p = sub.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                        values="_cost", aggfunc="min")
    return p.dropna(axis=1, how="any").dropna(axis=0, how="any")


def analyse(p, label, objective, out_lines):
    if p.shape[1] < 2:
        out_lines.append("  %-30s (fewer than two algorithms)" % label)
        return None
    vbs = p.min(axis=1).mean()
    means = p.mean().sort_values()
    sbs_name, sbs = means.index[0], means.iloc[0]

    rows = []
    for a in p.columns:
        rest = p.drop(columns=[a])
        vbs_without = rest.min(axis=1).mean()
        wins = int((p.idxmin(axis=1) == a).sum())
        rows.append({
            "algorithm": a,
            "mean_cost": float(means[a]),
            "wins": wins,
            "vbs_without": float(vbs_without),
            "marginal": float(vbs_without - vbs),
        })
    mc = pd.DataFrame(rows).sort_values("marginal", ascending=False)
    total_marg = mc.marginal.sum()
    mc["share_%"] = 100 * mc.marginal / total_marg if total_marg > 0 else 0.0

    unit = "s" if objective == "runtime" else "MB"
    out_lines.append("")
    out_lines.append("  %s  [%s, %d configurations, %d algorithms]"
                     % (label, objective, len(p), p.shape[1]))
    out_lines.append("    VBS %.3f %s | SBS %.3f %s (%s) | SBS/VBS %.3fx"
                     % (vbs, unit, sbs, unit, sbs_name, sbs / max(vbs, 1e-12)))
    out_lines.append("    %-24s %10s %7s %12s %8s"
                     % ("algorithm", "mean", "wins", "marginal", "share"))
    out_lines.append("    " + "-" * 66)
    for _, r in mc.iterrows():
        flag = "  redundant" if r.marginal <= 1e-9 else ""
        out_lines.append("    %-24s %10.3f %7d %12.4f %7.1f%%%s"
                         % (r.algorithm, r.mean_cost, r.wins, r.marginal,
                            r["share_%"], flag))
    n_red = int((mc.marginal <= 1e-9).sum())
    out_lines.append("    -> %d of %d algorithms are redundant (removing them "
                     "leaves the oracle unchanged)" % (n_red, len(mc)))
    return {"vbs": vbs, "sbs": float(sbs), "sbs_name": sbs_name,
            "sbs_vbs_ratio": float(sbs / max(vbs, 1e-12)),
            "n_redundant": n_red, "n_algorithms": int(p.shape[1]),
            "marginal": mc.set_index("algorithm").marginal.to_dict()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", type=int, default=1)
    args = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_runs()
    L = ["=" * 78,
         "PORTFOLIO COMPLEMENTARITY  (category %d)" % args.category,
         "=" * 78,
         "",
         "  If one algorithm dominates, no selector can beat simply running it.",
         "  This is a property of the benchmark, and it has to be measured before",
         "  a selection result means anything."]

    summary = {}
    for objective in ("runtime", "memory"):
        L.append("")
        L.append("#" * 70)
        L.append("# OBJECTIVE: %s" % objective.upper())
        L.append("#" * 70)
        for label, algos in PORTFOLIOS.items():
            p = cost_matrix(df, args.category, algos, objective)
            s = analyse(p, label, objective, L)
            if s:
                summary["%s / %s" % (objective, label)] = s

    # --- the conclusion, stated from the numbers --------------------------
    L.append("")
    L.append("=" * 78)
    rt = {k: v for k, v in summary.items() if k.startswith("runtime")}
    if rt:
        best = max(rt.values(), key=lambda v: v["sbs_vbs_ratio"])
        worst = min(rt.values(), key=lambda v: v["sbs_vbs_ratio"])
        L.append("  Headroom for a runtime selector ranges from %.2fx to %.2fx"
                 % (worst["sbs_vbs_ratio"], best["sbs_vbs_ratio"])
                 + " depending on portfolio.")
        L.append("  The portfolio a user actually has therefore decides whether")
        L.append("  selection is worth doing at all -- a result about the")
        L.append("  BENCHMARK, not about any model.")
    mem = {k: v for k, v in summary.items() if k.startswith("memory")}
    if mem and rt:
        r_best = max(v["sbs_vbs_ratio"] for v in rt.values())
        m_best = max(v["sbs_vbs_ratio"] for v in mem.values())
        L.append("")
        L.append("  Best available headroom: runtime %.2fx, memory %.2fx."
                 % (r_best, m_best))
        if m_best > r_best * 1.5:
            L.append("  MEMORY is where selection pays here, not runtime.")

    report = "\n".join(L) + "\n"
    print(report)
    with open(os.path.join(OUT_DIR, "complementarity.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(report)
    with open(os.path.join(OUT_DIR, "complementarity.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
