import sys
sys.path.insert(0, ".")
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless mode - GUI gerektirmez
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from tabulate import tabulate

sns.set_theme(style="whitegrid", palette="tab10")
plt.rcParams["figure.dpi"] = 150

SUMMARY_CSV = Path("results/summary.csv")
PLOTS_DIR = Path("plots")
PLOTS_DIR.mkdir(exist_ok=True)
REPORT_DIR = Path("report")
REPORT_DIR.mkdir(exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(SUMMARY_CSV)
    df = df[~df["timed_out"].astype(bool)]
    df = df[df["error"].isna()]
    df["runtime_s"] = pd.to_numeric(df["runtime_s"], errors="coerce")
    df["peak_memory_mb"] = pd.to_numeric(df["peak_memory_mb"], errors="coerce")
    df["generator_count"] = pd.to_numeric(df["generator_count"], errors="coerce").fillna(0)
    df["param_value"] = pd.to_numeric(df["param_value"], errors="coerce")
    return df.dropna(subset=["runtime_s"])


def plot_runtime_by_param(df: pd.DataFrame, dataset: str, category: int, param_col: str = "param_value"):
    sub = df[(df["dataset"] == dataset) & (df["category"] == category)].copy()
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    for algo, grp in sub.groupby("algorithm"):
        g = grp.sort_values(param_col)
        ax.plot(g[param_col], g["runtime_s"], marker="o", label=algo, linewidth=1.8)
    ax.set_xlabel("Parameter Value (min support / utility threshold)")
    ax.set_ylabel("Runtime (s)")
    ax.set_title(f"Runtime vs Parameter — {dataset} (Category {category})")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
    plt.tight_layout()
    fname = PLOTS_DIR / f"runtime_cat{category}_{dataset}.pdf"
    fig.savefig(fname, bbox_inches="tight")
    plt.close()
    print(f"[PLOT] {fname}")


def plot_memory_heatmap(df: pd.DataFrame):
    sub = df.copy()
    pivot = sub.pivot_table(
        index="algorithm", columns="dataset",
        values="peak_memory_mb", aggfunc="mean"
    ).round(1)
    if pivot.empty:
        return
    fig, ax = plt.subplots(figsize=(max(8, len(pivot.columns) * 1.2), max(4, len(pivot) * 0.6)))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax, linewidths=0.5)
    ax.set_title("Peak Memory Usage (MB) — Algorithm x Dataset")
    ax.set_xlabel("Dataset")
    ax.set_ylabel("Algorithm")
    plt.tight_layout()
    fname = PLOTS_DIR / "memory_heatmap.pdf"
    fig.savefig(fname, bbox_inches="tight")
    plt.close()
    print(f"[PLOT] {fname}")


def plot_generator_count(df: pd.DataFrame, category: int):
    sub = df[df["category"] == category].copy()
    if sub.empty:
        return
    datasets = sub["dataset"].unique()
    fig, axes = plt.subplots(1, min(len(datasets), 3), figsize=(5 * min(len(datasets), 3), 4), squeeze=False)
    for idx, ds in enumerate(datasets[:3]):
        ax = axes[0][idx]
        d = sub[sub["dataset"] == ds].sort_values("param_value")
        for algo, grp in d.groupby("algorithm"):
            g = grp.sort_values("param_value")
            vals = g["generator_count"].clip(lower=1)
            ax.semilogy(g["param_value"], vals, marker="s", label=algo, linewidth=1.5)
        ax.set_title(f"{ds}")
        ax.set_xlabel("Parameter")
        ax.set_ylabel("Generator Count (log)")
        ax.legend(fontsize=8)
    fig.suptitle(f"Generator Count — Category {category}", fontsize=12)
    plt.tight_layout()
    fname = PLOTS_DIR / f"gencount_cat{category}.pdf"
    fig.savefig(fname, bbox_inches="tight")
    plt.close()
    print(f"[PLOT] {fname}")


def plot_scalability(df: pd.DataFrame):
    """Dataset buyuklugune gore runtime — Category 1 algoritmalar."""
    # Dataset boyutlari (transaction sayisi)
    dataset_sizes = {
        "mushroom": 8124, "chess": 3196, "connect": 67557,
        "t10i4d100k": 100000, "retail": 88162,
        "leviathan": 5834, "bible": 36369, "sign": 730,
        "chainstore": 45000, "foodmart": 4141,
    }
    # Sabit bir param degerinde karsilastir
    param_vals = df["param_value"].dropna().unique()
    if len(param_vals) == 0:
        return
    fixed_param = sorted(param_vals)[len(param_vals) // 2]  # ortanca deger

    sub = df[df["param_value"] == fixed_param].copy()
    sub["n_transactions"] = sub["dataset"].map(dataset_sizes)
    sub = sub.dropna(subset=["n_transactions"])
    if sub.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    for algo, grp in sub.groupby("algorithm"):
        g = grp.sort_values("n_transactions")
        ax.plot(g["n_transactions"], g["runtime_s"], marker="o", label=algo, linewidth=1.8)
    ax.set_xlabel("Number of Transactions")
    ax.set_ylabel("Runtime (s)")
    ax.set_title(f"Scalability Analysis (param={fixed_param})")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
    plt.tight_layout()
    fname = PLOTS_DIR / "scalability.pdf"
    fig.savefig(fname, bbox_inches="tight")
    plt.close()
    print(f"[PLOT] {fname}")


def plot_category_comparison(df: pd.DataFrame):
    """Her kategori icin ortalama runtime bar chart."""
    summary = df.groupby(["algorithm", "category"])["runtime_s"].mean().reset_index()
    summary = summary.sort_values(["category", "runtime_s"])

    categories = sorted(summary["category"].unique())
    fig, axes = plt.subplots(1, len(categories), figsize=(5 * len(categories), 5), squeeze=False)

    for idx, cat in enumerate(categories):
        ax = axes[0][idx]
        sub = summary[summary["category"] == cat]
        bars = ax.barh(sub["algorithm"], sub["runtime_s"], color=sns.color_palette("tab10", len(sub)))
        ax.set_xlabel("Avg Runtime (s)")
        ax.set_title(f"Category {cat}")
        ax.invert_yaxis()

    fig.suptitle("Average Runtime by Category", fontsize=12)
    plt.tight_layout()
    fname = PLOTS_DIR / "category_comparison.pdf"
    fig.savefig(fname, bbox_inches="tight")
    plt.close()
    print(f"[PLOT] {fname}")


def generate_summary_table(df: pd.DataFrame) -> str:
    summary = df.groupby(["algorithm", "category"]).agg(
        avg_runtime_s=("runtime_s", "mean"),
        min_runtime_s=("runtime_s", "min"),
        max_runtime_s=("runtime_s", "max"),
        avg_memory_mb=("peak_memory_mb", "mean"),
        avg_generators=("generator_count", "mean"),
        n_runs=("runtime_s", "count"),
    ).reset_index()
    summary = summary.sort_values(["category", "avg_runtime_s"])
    summary = summary.round(3)
    table_str = tabulate(summary, headers="keys", tablefmt="github", floatfmt=".3f", showindex=False)

    out = REPORT_DIR / "tables.md"
    content = f"# Benchmark Ozet Tablosu\n\nOlusturma tarihi: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n\n{table_str}\n"
    out.write_text(content, encoding="utf-8")
    print(f"[TABLE] {out}")
    return table_str


def run_all_analyses():
    df = load_data()
    if df.empty:
        print("[WARN] Sonuc verisi bulunamadi.")
        return

    print(f"[INFO] {len(df)} basarili calistirma yuklendi")
    print(f"[INFO] Algoritmalar: {sorted(df['algorithm'].unique())}")
    print(f"[INFO] Datasetler: {sorted(df['dataset'].unique())}")

    # Runtime grafikleri - kategori 1
    for ds in df[df["category"] == 1]["dataset"].unique():
        plot_runtime_by_param(df, ds, category=1)

    # Runtime grafikleri - kategori 2
    for ds in df[df["category"] == 2]["dataset"].unique():
        plot_runtime_by_param(df, ds, category=2)

    # Runtime grafikleri - kategori 3
    for ds in df[df["category"] == 3]["dataset"].unique():
        plot_runtime_by_param(df, ds, category=3)

    # Runtime grafikleri - kategori 5
    for ds in df[df["category"] == 5]["dataset"].unique():
        plot_runtime_by_param(df, ds, category=5)

    # Memory heatmap
    plot_memory_heatmap(df)

    # Generator count
    for cat in df["category"].unique():
        plot_generator_count(df, category=cat)

    # Scalability
    plot_scalability(df)

    # Category comparison
    plot_category_comparison(df)

    # Tablo
    table = generate_summary_table(df)
    print("\n" + table)

    print(f"\n[DONE] Tum analizler tamamlandi -> plots/ ve report/")


if __name__ == "__main__":
    run_all_analyses()
