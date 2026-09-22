"""Instance space analysis: where in feature space does each miner win?

Following Smith-Miles' instance space methodology (`literature/pdf/isa-carseq.pdf`,
`e-apr.pdf`): project the benchmark instances into a plane in which performance
varies smoothly, then draw each algorithm's FOOTPRINT -- the region where it
performs well. Three questions get answered that a table of averages cannot:

  1. Does each algorithm win in a coherent REGION, or scattered at random? A
     scattered footprint means the meta-features do not explain performance,
     which would doom any selector built on them.
  2. Do the footprints OVERLAP? Heavy overlap is complementarity's opposite:
     it means the instances where algorithms differ are rare.
  3. Do our 12 datasets COVER the space, or cluster in one corner? This is the
     question `synth.py` exists to answer, and the honest way to justify
     generating synthetic instances.

Projection. The published method optimises the projection so that performance
gradients are linear in the plane. PCA cannot do that -- it never sees
performance. Partial least squares does: it finds the feature directions of
maximum covariance WITH the performance matrix, which is the same objective in
spirit and is stable at this sample size (58 instances). PCA is kept as a
`--projection pca` baseline so the difference is visible rather than asserted.

Footprints are convex hulls over the instances an algorithm is good on, with
the two numbers that make a hull interpretable:

  purity   of the instances falling inside the hull, the fraction the algorithm
           is actually good on. A hull covering the whole plane has high area
           and low purity, and is worthless.
  area     the hull's share of the total instance-space area.

    python -m recommender.instance_space
    python -m recommender.instance_space --objective memory --projection pca
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from . import metafeatures as mf
from .perfmodel import load_runs, TIMEOUT_S, PAR_PENALTY

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")
PLOT_DIR = os.path.join(os.path.dirname(_HERE), "plots")

#: An algorithm is "good" on an instance when its cost is within this factor of
#: the best cost achieved on it. 1.0 would mean "uniquely best", which makes
#: footprints degenerate; a small tolerance is what the ISA literature uses.
GOOD_FACTOR = 1.20


def build_matrix(df, category=1, objective="runtime"):
    """(instances x algorithms) cost matrix plus the instance feature table."""
    sub = df[df.category == category].copy()
    if objective == "runtime":
        sub["cost"] = np.where(sub.completed, sub.runtime_s.clip(lower=1e-3),
                               TIMEOUT_S * PAR_PENALTY)
    else:
        # Memory of a killed run is a lower bound, not a missing value, so it
        # gets no invented penalty; restrict to instances where all candidates
        # completed instead. Same decision as bench_selectors.
        sub = sub[sub.completed]
        sub["cost"] = sub.peak_memory_mb

    cost = sub.pivot_table(index=["dataset", "param_value"], columns="algorithm",
                           values="cost", aggfunc="min")
    cost = cost.dropna(axis=1, how="any").dropna(axis=0, how="any")

    cols = list(mf.FEATURE_NAMES) + ["log_thr"]
    feats = (sub.drop_duplicates(subset=["dataset", "param_value"])
                .set_index(["dataset", "param_value"])[cols])
    feats = feats.reindex(cost.index)
    return cost, feats


def _performance_r2(Z, Y):
    """Share of performance variance a linear map from the 2-D plane explains.

    The SAME metric for every projection. PCA's own
    `explained_variance_ratio_` measures explained FEATURE variance, which is a
    different quantity entirely -- reporting the two side by side made PCA look
    three times better than PLS when it is in fact worse at the job that
    matters here.
    """
    from sklearn.linear_model import LinearRegression
    pred = LinearRegression().fit(Z, Y).predict(Z)
    ss_res = float(((Y - pred) ** 2).sum())
    ss_tot = float(((Y - Y.mean(0)) ** 2).sum())
    return 1.0 - ss_res / max(ss_tot, 1e-12)


def project(feats, cost, kind="pls", seed=0):
    """Feature table -> 2-D coordinates, plus explained performance variance."""
    X = feats.to_numpy(float)
    X = (X - X.mean(0)) / (X.std(0) + 1e-12)
    # Log costs: performance spans orders of magnitude, and covariance on the
    # raw scale would be dominated by the timed-out entries alone.
    Y = np.log10(cost.to_numpy(float))
    Y = (Y - Y.mean(0)) / (Y.std(0) + 1e-12)

    if kind == "pca":
        from sklearn.decomposition import PCA
        p = PCA(n_components=2, random_state=seed)
        Z = p.fit_transform(X)
        return Z, _performance_r2(Z, Y), float(p.explained_variance_ratio_.sum())

    from sklearn.cross_decomposition import PLSRegression
    p = PLSRegression(n_components=2, scale=False)
    p.fit(X, Y)
    Z = p.transform(X)
    return Z, _performance_r2(Z, Y), float("nan")


def footprints(Z, cost, good_factor=GOOD_FACTOR):
    """Convex hull, purity and area for each algorithm's good region."""
    from scipy.spatial import ConvexHull, Delaunay

    best = cost.min(axis=1).to_numpy(float)
    total_hull = ConvexHull(Z) if len(Z) >= 3 else None
    total_area = total_hull.volume if total_hull is not None else 1.0

    out = {}
    for algo in cost.columns:
        good = cost[algo].to_numpy(float) <= good_factor * best
        pts = Z[good]
        rec = {"n_good": int(good.sum()),
               "share_good": float(good.mean())}
        if len(pts) >= 3:
            try:
                hull = ConvexHull(pts)
                tri = Delaunay(pts[hull.vertices])
                inside = tri.find_simplex(Z) >= 0
                rec["area"] = float(hull.volume / max(total_area, 1e-12))
                rec["purity"] = float(good[inside].mean()) if inside.any() else 0.0
                rec["n_inside"] = int(inside.sum())
            except Exception:
                rec["area"] = rec["purity"] = float("nan")
        else:
            rec["area"] = rec["purity"] = float("nan")
        out[algo] = rec
    return out


def effective_instances(Z, feats):
    """How many genuinely distinct instances the benchmark contains.

    The plot shows the 58 configurations as vertical stripes: every
    configuration of one dataset lands at nearly the same position, because ten
    of the eleven features are properties of the DATASET and only `log_thr`
    varies within it. So the instance space has as many distinct locations as
    there are datasets, not as there are runs.

    Quantified as the share of positional variance lying BETWEEN datasets. A
    value near 1 means the threshold barely moves an instance, and the
    effective sample size for anything learned across the plane is the number
    of datasets -- here seven, not fifty-eight.
    """
    ds = np.asarray(feats.index.get_level_values(0))
    total = Z.var(axis=0).sum()
    within = 0.0
    for name in pd.unique(ds):
        m = ds == name
        if m.sum() > 1:
            within += Z[m].var(axis=0).sum() * m.sum()
    within /= max(len(Z), 1)
    between_share = 1.0 - within / max(total, 1e-12)

    # The share on its own understates the problem, and "effective sample size
    # equals the number of datasets" overstates it whenever the threshold does
    # move an instance a little. Both are special cases of the design effect
    # from cluster sampling, with the between-dataset share read as an
    # intra-cluster correlation:
    #
    #     n_eff = n / (1 + (mbar - 1) * ICC),   mbar = configurations per dataset
    #
    # At ICC = 1 this returns exactly the number of datasets, at ICC = 0 the
    # number of configurations, and it interpolates in between. On the published
    # static feature set (ICC 0.956, 58 configurations over 7 datasets) it gives
    # 7.3, reproducing the figure that was previously asserted as "7"; with
    # threshold-dependent landmarks (ICC 0.622) it gives 10.5, which is the
    # honest size of the gain -- a doubled share of explained performance
    # variance buys 3 more effective instances, not 51.
    n_conf = int(len(Z))
    n_ds = int(len(pd.unique(ds)))
    mbar = n_conf / max(n_ds, 1)
    n_eff = n_conf / (1.0 + (mbar - 1.0) * max(min(between_share, 1.0), 0.0))
    return {"n_configurations": n_conf,
            "n_datasets": n_ds,
            "between_dataset_share": float(between_share),
            "configs_per_dataset": float(mbar),
            "effective_instances": float(n_eff)}


def coverage(Z, feats):
    """How much of the plane the real datasets occupy, and where the holes are."""
    from scipy.spatial import ConvexHull
    res = {}
    if len(Z) >= 3:
        res["hull_area"] = float(ConvexHull(Z).volume)
    # Occupancy of a coarse grid: empty cells inside the hull are the regions
    # no benchmark dataset reaches.
    nb = 6
    xs = np.linspace(Z[:, 0].min(), Z[:, 0].max(), nb + 1)
    ys = np.linspace(Z[:, 1].min(), Z[:, 1].max(), nb + 1)
    occupied = np.zeros((nb, nb), dtype=int)
    for x, y in Z:
        i = min(np.searchsorted(xs, x, "right") - 1, nb - 1)
        j = min(np.searchsorted(ys, y, "right") - 1, nb - 1)
        occupied[max(i, 0), max(j, 0)] += 1
    res["cells_total"] = nb * nb
    res["cells_occupied"] = int((occupied > 0).sum())
    res["max_cell_share"] = float(occupied.max() / max(occupied.sum(), 1))
    return res, occupied


def plot(Z, cost, feats, fp, path, objective, projection, quality):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull

    winner = cost.idxmin(axis=1).to_numpy()
    algos = list(cost.columns)
    cmap = plt.get_cmap("tab10")
    colour = {a: cmap(i % 10) for i, a in enumerate(algos)}

    fig, ax = plt.subplots(figsize=(7.6, 5.6))
    # Footprints as OUTLINES, not fills: with nine algorithms the filled hulls
    # overlapped into an unreadable grey. Only the informative ones are drawn --
    # a hull covering the whole plane says nothing about where an algorithm
    # wins, so footprints occupying more than 90% of the area are skipped and
    # noted in the caption instead.
    best = cost.min(axis=1).to_numpy(float)
    skipped = []
    for a in algos:
        pts = Z[cost[a].to_numpy(float) <= GOOD_FACTOR * best]
        if len(pts) < 3:
            continue
        try:
            h = ConvexHull(pts)
            frac = h.volume / max(ConvexHull(Z).volume, 1e-12)
            if frac > 0.90:
                skipped.append(a)
                continue
            v = np.append(h.vertices, h.vertices[0])
            ax.plot(pts[v, 0], pts[v, 1], color=colour[a], lw=1.6,
                    alpha=0.85, zorder=2)
            ax.fill(pts[h.vertices, 0], pts[h.vertices, 1],
                    color=colour[a], alpha=0.07, lw=0, zorder=1)
        except Exception:
            pass

    for a in algos:
        m = winner == a
        if m.any():
            ax.scatter(Z[m, 0], Z[m, 1], s=34, color=colour[a],
                       edgecolor="k", linewidth=0.4, label=a, zorder=3)

    # Label each dataset once, at its centroid, so the plane is readable.
    ds = feats.index.get_level_values(0)
    for name in pd.unique(ds):
        m = ds == name
        # Above the column of points rather than through it: the
        # configurations of one dataset stack vertically, so a centroid label
        # lands right on top of them.
        ax.annotate(name, (Z[m, 0].mean(), Z[m, 1].max()),
                    textcoords="offset points", xytext=(0, 7),
                    fontsize=7.5, alpha=0.9, ha="center", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="none", alpha=0.7))

    ax.set_xlabel("instance-space dimension 1")
    ax.set_ylabel("instance-space dimension 2")
    ax.set_title("Instance space -- %s projection, %s objective\n"
                 "outlined: footprint within %.0f%% of best   |   "
                 "performance variance explained by the plane: %.2f"
                 % (projection.upper(), objective,
                    100 * (GOOD_FACTOR - 1), quality), fontsize=9)
    if skipped:
        # Below the axes rather than in the title: the list of omitted
        # footprints is long enough to run off the figure edge.
        fig.text(0.01, 0.005,
                 "Footprints covering >90%% of the plane are omitted as "
                 "uninformative: %s." % ", ".join(skipped),
                 fontsize=6.8, alpha=0.8, ha="left", va="bottom", wrap=True)
    ax.legend(fontsize=6.5, loc="best", framealpha=0.9)
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Suppress the PDF CreationDate stamp so an unchanged figure re-saves
    # to identical bytes; see the same fix in src/analyze.py.
    fig.savefig(path, metadata={"CreationDate": None})
    plt.close(fig)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--category", type=int, default=1)
    ap.add_argument("--objective", default="runtime",
                    choices=["runtime", "memory"])
    ap.add_argument("--projection", default="pls", choices=["pls", "pca"])
    args = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_runs()
    cost, feats = build_matrix(df, args.category, args.objective)
    if cost.empty or cost.shape[1] < 2:
        print("insufficient overlap")
        return 1

    Z, quality, feat_var = project(feats, cost, args.projection)
    fp = footprints(Z, cost)
    cov, occupied = coverage(Z, feats)
    eff = effective_instances(Z, feats)

    L = ["=" * 78,
         "INSTANCE SPACE  (category %d, %s, %s projection)"
         % (args.category, args.objective, args.projection.upper()),
         "=" * 78,
         "  %d instances, %d algorithms, %d features"
         % (len(cost), cost.shape[1], feats.shape[1]),
         "  performance variance explained by the 2-D plane: %.3f" % quality,
         "",
         "  FOOTPRINTS -- region where the algorithm is within %.0f%% of best"
         % (100 * (GOOD_FACTOR - 1)),
         "  %-24s %7s %8s %8s %8s" % ("algorithm", "good", "share", "area",
                                      "purity"),
         "  " + "-" * 60]
    for a, r in sorted(fp.items(), key=lambda kv: -kv[1]["share_good"]):
        L.append("  %-24s %7d %7.1f%% %8s %8s"
                 % (a, r["n_good"], 100 * r["share_good"],
                    "%.3f" % r["area"] if r["area"] == r["area"] else "-",
                    "%.2f" % r["purity"] if r["purity"] == r["purity"] else "-"))

    L.append("")
    L.append("  EFFECTIVE INSTANCE COUNT")
    L.append("    %d configurations drawn from %d datasets"
             % (eff["n_configurations"], eff["n_datasets"]))
    L.append("    share of position determined by the dataset alone: %.1f%%"
             % (100 * eff["between_dataset_share"]))
    L.append("    design effect n/(1+(mbar-1)*ICC) with mbar=%.2f configs/dataset"
             % eff["configs_per_dataset"])
    L.append("    -> EFFECTIVE INSTANCES: %.1f  (of %d configurations, %d datasets)"
             % (eff["effective_instances"], eff["n_configurations"],
                eff["n_datasets"]))
    if eff["between_dataset_share"] > 0.85:
        L.append("       The threshold barely moves an instance, so the plane")
        L.append("       holds about as many distinct locations as there are")
        L.append("       datasets. Anything learned ACROSS it is fitted to that")
        L.append("       many points, whatever the row count suggests.")
    L.append("")
    L.append("  COVERAGE")
    L.append("    grid cells containing at least one instance : %d of %d"
             % (cov["cells_occupied"], cov["cells_total"]))
    L.append("    largest single cell holds %.0f%% of all instances"
             % (100 * cov["max_cell_share"]))
    if cov["cells_occupied"] < 0.4 * cov["cells_total"]:
        L.append("    -> the benchmark occupies a minority of its own instance")
        L.append("       space. A selector trained here EXTRAPOLATES to most of")
        L.append("       the plane, which is what synth.py is for.")

    scattered = [a for a, r in fp.items()
                 if r["purity"] == r["purity"] and r["purity"] < 0.5
                 and r["n_good"] >= 3]
    if scattered:
        L.append("")
        L.append("  Footprints with purity below 0.5 (the region is not really")
        L.append("  theirs): %s" % ", ".join(scattered))

    path = plot(Z, cost, feats, fp,
                os.path.join(PLOT_DIR, "instance_space_%s_%s.pdf"
                             % (args.objective, args.projection)),
                args.objective, args.projection, quality)
    L.append("")
    L.append("  figure: %s" % path)

    report = "\n".join(L) + "\n"
    print(report)
    with open(os.path.join(OUT_DIR, "instance_space_%s_%s.txt"
                           % (args.objective, args.projection)),
              "w", encoding="utf-8") as fh:
        fh.write(report)
    with open(os.path.join(OUT_DIR, "instance_space_%s_%s.json"
                           % (args.objective, args.projection)),
              "w", encoding="utf-8") as fh:
        json.dump({"quality": quality, "footprints": fp, "coverage": cov,
                   "effective": eff}, fh, indent=2, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())


