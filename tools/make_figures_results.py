"""Additional figures for the results and discussion of the ESWA paper.

    .venv/bin/python tools/make_figures_results.py

  kbs/figures/perf.pdf           runtime and memory of each transactional
                                 implementation against the per-configuration
                                 best (E1, results/e2_exact_output.txt)
  kbs/figures/runtime_regret.pdf runtime regret per method on PRIMARY
  kbs/figures/ranks.pdf          average ranks of per-dataset mean log memory
                                 regret, with the Bonferroni-Dunn CD
  kbs/figures/paired.pdf         per-dataset mean log memory regret,
                                 recommender against AutoFolio and ISAC
  kbs/figures/probe_time.pdf     ECDF of the probe's wall time
  kbs/figures/rounds.pdf         criteria passed and failed per pre-registered round
  kbs/figures/e2.pdf             violations of a cost-only oracle selector by
                                 requirement profile and cause
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
import matplotlib.ticker                                   # noqa: E402,F401
import numpy as np                                         # noqa: E402
import pandas as pd                                        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "kbs" / "figures"
RES = ROOT / "results"
BLUE, RED, GREY, ORANGE = "#1f4e79", "#c00000", "0.55", "#d08000"
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "pdf.fonttype": 42})

METHODS = {"recommender, probe": "recommender + probe",
           "AutoFolio (SMAC, 1800s/fold)": "AutoFolio",
           "ISAC (k-means clusters)": "ISAC",
           "pairwise ranking": "pairwise ranking",
           "regression (PAR10-imputed)": "regression",
           "SUNNY (k-NN, k=16)": "SUNNY",
           "recommender, no probe": "recommender, no probe",
           "SBS (fixed choice)": "SBS",
           "survival (expected_par10)": "survival",
           "random pick": "random"}


def perf():
    # E1 of results/e2_exact_output.txt: 58 configurations (runtime, PAR10
    # geometric mean vs virtual best) and 39 with every implementation
    # completed (memory vs per-configuration best).
    rt = {"Gr-growth": 1.197, "FP-growth (B)": 1.280, "Eclat (B)": 1.404,
          "Apriori (B)": 3.235, "DefMe": 13.699, "Talky-G": 15.710,
          "Talky-G-Diffset": 16.250, "Pascal": 867.121, "Zart": 1861.991}
    mem = {"Apriori (B)": 1.458, "Gr-growth": 1.627, "Eclat (B)": 1.860,
           "FP-growth (B)": 1.924, "Pascal": 20.874, "Talky-G": 37.131,
           "Talky-G-Diffset": 37.684, "DefMe": 40.484, "Zart": 46.748}
    names = sorted(rt, key=rt.get)[::-1]
    fig, axs = plt.subplots(1, 2, figsize=(6.8, 2.3), sharey=True)
    for ax, d, lab in ((axs[0], rt, "runtime / per-configuration best"),
                       (axs[1], mem, "peak memory / per-configuration best")):
        y = np.arange(len(names))
        native = [n.endswith("(B)") or n == "Gr-growth" for n in names]
        ax.barh(y, [d[n] - 1 for n in names], left=1,
                color=[ORANGE if nv else BLUE for nv in native], height=0.6)
        ax.set_xscale("log")
        ax.set_xlabel(lab)
        for yi, n in zip(y, names):
            ax.text(d[n] * 1.08, yi, "%.2f" % d[n], va="center", fontsize=6)
        ax.set_xlim(1, max(d.values()) * 6)
    axs[0].set_yticks(np.arange(len(names)))
    axs[0].set_yticklabels(names)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=ORANGE, label="native (C/C++)"), Patch(color=BLUE, label="Java (SPMF)")], ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.06),
                  frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "perf.pdf", bbox_inches="tight")


def _rows(objective, primary_only):
    d = pd.read_csv(RES / "baseline_rows.csv")
    d = d[(d.objective == objective)]
    if primary_only:
        d = d[d.primary]
    return d


def runtime_regret():
    d = _rows("runtime", True)
    cols = {k: v for k, v in METHODS.items() if k != "recommender, probe"}
    cols = {"recommender, no probe": "recommender", **{k: v for k, v in cols.items()
                                                        if k != "recommender, no probe"}}
    gm = {v: float(np.exp(np.log(d[k]).mean())) for k, v in cols.items()}
    names = sorted(gm, key=gm.get)[::-1]
    inv = {v: k for k, v in cols.items()}
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for i, n in enumerate(names):
        v = np.minimum(d[inv[n]].values, 10.0)
        y = i + (np.random.default_rng(i).random(len(v)) - 0.5) * 0.5
        ax.scatter(v, y, s=3, alpha=0.35, color=BLUE, linewidths=0)
        ax.plot([gm[n]] * 2, [i - 0.35, i + 0.35], color=RED, lw=1.4)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xscale("log")
    ax.set_xlim(0.95, 11)
    ax.set_xticks([1, 1.5, 2, 3, 5, 10])
    ax.set_xticklabels(["1", "1.5", "2", "3", "5", "10 (failed)"])
    ax.set_xlabel("runtime regret")
    fig.tight_layout()
    fig.savefig(OUT / "runtime_regret.pdf", bbox_inches="tight")
    print("runtime geo-means:", {k: round(v, 3) for k, v in gm.items()})


def _per_dataset(primary_only):
    d = _rows("memory", primary_only)
    d = d[d["recommender, probe"].notna()]
    g = d.groupby("dataset")[list(METHODS)].apply(lambda x: np.log(x).mean())
    return g.rename(columns=METHODS)


def ranks():
    res = {}
    for prim in (True, False):
        g = _per_dataset(prim)
        r = g.rank(axis=1, method="average").mean()
        k, n = len(r), len(g)
        res[prim] = (r, 2.773 * np.sqrt(k * (k + 1) / (6.0 * n)))  # Bonferroni-Dunn, a=0.05
        print("primary" if prim else "all", n, {m: round(v, 2) for m, v in r.sort_values().items()},
              "CD", round(res[prim][1], 2))
    order = res[True][0].sort_values().index[::-1]
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    y = np.arange(len(order))
    for prim, c, mk, lab, dy in ((True, BLUE, "o", "PRIMARY (32 datasets)", 0.12),
                                 (False, GREY, "s", "all test sets (90)", -0.12)):
        r, cd = res[prim]
        ax.scatter(r[order].values, y + dy, color=c, marker=mk, s=14, label=lab, zorder=3)
        r0 = r["recommender + probe"]
        ax.axvspan(r0, r0 + cd, ymin=0, ymax=1, color=c, alpha=0.10, lw=0)
    ax.set_yticks(y)
    ax.set_yticklabels(order)
    ax.set_xlabel("average rank of mean log memory regret (1 = best)")
    ax.legend(frameon=False, loc="upper right", fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "ranks.pdf", bbox_inches="tight")


def paired():
    g = _per_dataset(False)
    prim = set(_rows("memory", True).dataset)
    fig, axs = plt.subplots(1, 2, figsize=(6.8, 2.6), sharey=True)
    for ax, m in zip(axs, ("AutoFolio", "ISAC")):
        x, y = np.exp(g[m]), np.exp(g["recommender + probe"])
        isp = np.array([ds in prim for ds in g.index])
        ax.scatter(x[~isp], y[~isp], s=9, alpha=0.6, color=GREY, linewidths=0, label="earlier test sets")
        ax.scatter(x[isp], y[isp], s=11, alpha=0.8, color=BLUE, linewidths=0, label="PRIMARY")
        hi = max(x.max(), y.max()) * 1.1
        ax.plot([1, hi], [1, hi], color="0.3", lw=0.8, ls="--")
        ax.set_xscale("log")
        ax.set_yscale("log")
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%g"))
            axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xticks([1, 1.5, 2, 3, 4])
        ax.set_yticks([1, 1.5, 2, 3, 4])
        ax.set_xlabel("%s: per-dataset memory regret" % m)
        better = int((y < x - 1e-9).sum()); worse = int((y > x + 1e-9).sum())
        ax.set_title("recommender better on %d, worse on %d of %d datasets" % (better, worse, len(x)),
                     fontsize=7)
    axs[0].set_ylabel("recommender + probe")
    axs[0].legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "paired.pdf", bbox_inches="tight")


def probe_time():
    b = pd.read_csv(RES / "baseline2_rows.csv")
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    for sub, lab, c in ((b, "all test sets (335)", GREY), (b[b.primary], "PRIMARY (119)", BLUE)):
        v = np.sort(sub["probe wall s"].values)
        ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=c, label=lab)
        print(lab, "median %.2f p90 %.2f max %.1f" % (np.median(v), np.quantile(v, .9), v.max()))
    ax.set_xscale("log")
    ax.set_xlabel("probe wall time (s)")
    ax.set_ylabel("share of instances")
    ax.axvline(1.0, color="0.3", lw=0.6, ls=":")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "probe_time.pdf", bbox_inches="tight")


def e2():
    # results/e2_exact_output.txt: 160 queries per profile; HUCI-Miner-
    # Generators violates 2 per profile (10 in all), wrong threshold side 78
    # (floor requested) and 44 (ceiling requested).
    prof = ["default", "floor side", "ceiling side", "$\\emptyset$ required", "$\\emptyset$ forbidden"]
    fam = np.array([2, 2, 2, 2, 2]) / 160 * 100
    side = np.array([0, 78, 44, 0, 0]) / 160 * 100
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    x = np.arange(len(prof))
    ax.bar(x, fam, color=RED, width=0.6, label="another family (HUCI-Miner-Gen.)")
    ax.bar(x, side, bottom=fam, color=BLUE, width=0.6, label="wrong threshold side")
    for xi, t in zip(x, fam + side):
        ax.text(xi, t + 1.2, "%.1f%%" % t, ha="center", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels(prof, rotation=20, ha="right")
    ax.set_ylabel("requests violated (%)")
    ax.set_ylim(0, 75)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "e2.pdf", bbox_inches="tight")


def rounds():
    # Table of pre-registered rounds in the paper (criteria passed, failed);
    # LAG, LAG2 (underpowered) and BASELINE (no pass criterion) have none.
    r = [("EXTENSION", 1, 2), ("EXTENSION2", 2, 2), ("PROBE", 1, 2), ("CONFIRM", 3, 1),
         ("HARD", 2, 1), ("INTERVAL", 3, 1), ("FRESH", 2, 3), ("FRESH2", 4, 0),
         ("FRESH3", 3, 0), ("FRESH4", 1, 2), ("FRESH5", 2, 1), ("FRESH6", 2, 2),
         ("FRESH7", 3, 0), ("FRESH8", 3, 0), ("BASELINE2", 2, 0)]
    x = np.arange(len(r))
    fig, ax = plt.subplots(figsize=(6.8, 1.9))
    ax.bar(x, [a for _, a, _ in r], color=BLUE, width=0.6, label="passed")
    ax.bar(x, [-b for _, _, b in r], color=RED, width=0.6, label="failed")
    ax.axhline(0, color="0.3", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([n for n, _, _ in r], rotation=35, ha="right")
    ax.set_yticks([-3, -2, -1, 0, 1, 2, 3, 4])
    ax.set_yticklabels(["3", "2", "1", "0", "1", "2", "3", "4"])
    ax.set_ylabel("criteria")
    ax.axvspan(11.5, 14.5, color="0.9", lw=0, zorder=0)
    ax.text(13, 4.3, "configuration frozen", ha="center", fontsize=6)
    ax.set_ylim(-3.6, 4.9)
    ax.legend(frameon=False, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "rounds.pdf", bbox_inches="tight")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    perf(); runtime_regret(); ranks(); paired(); probe_time(); e2(); rounds()
