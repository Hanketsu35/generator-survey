# src/harness.py
import sys
import json
import csv
import itertools
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, ".")
from src.config import (
    ALGORITHMS, MINSUP_VALUES, MAXSUP_VALUES, MIN_UTILITY_VALUES,
    MIN_UTILITY_FOODMART, TIMEOUT_SECONDS, DATASETS,
    MINSUP_BY_DATASET, MAX_KEEP_OUTPUT_MB, GRGROWTH_K,
    SEQ_MINSUP_BY_DATASET,
)
from src.metrics import (
    run_spmf, run_external, save_result, count_transactions,
    count_grgrowth_generators, count_fgcstream_generators,
    count_pascal_generators, count_zart_generators,
    count_borgelt_generators, count_plain_lines,
)

# config'deki "count_fn" anahtarindan gercek fonksiyona esleme.
# Varsayilan (None) = bos olmayan satir sayimi.
COUNT_FUNCS = {
    "pascal":  count_pascal_generators,
    "zart":    count_zart_generators,
    "borgelt": count_borgelt_generators,
    "lines":   count_plain_lines,
}
from src.datasets import get_dataset_path, get_utility_dataset_path

RESULTS_DIR = Path("results/raw")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_CSV = Path("results/summary.csv")

FIELDNAMES = [
    "algorithm", "category", "dataset", "param_name", "param_value",
    "runtime_s", "peak_memory_mb", "generator_count", "timed_out", "error", "timestamp",
]



def param_key(v) -> str:
    """
    Resume anahtari icin parametre degerini kanonik hale getirir.

    CSV'den okunan 1000.0 ile config'deki 1000 ayni kosudur; duz str()
    karsilastirmasi bunlari farkli gorup kosuyu tekrar calistiriyordu
    (olculen: 18 utility kosusu iki kez calisti).
    """
    if v is None:
        return "none"
    try:
        return repr(float(v))
    except (TypeError, ValueError):
        return str(v)


def get_param_values(algo_cfg: dict, dataset: str = None) -> tuple:
    """Algoritma konfigurasyonuna ve datasete gore parametre adi ve degerlerini dondurur."""
    params = algo_cfg.get("params", [])
    if not params:
        return "none", [None]
    p = params[0]
    if p == "minsup":
        # Sirali veri kumeleri kendi (cok daha dusuk) gridlerini kullanir;
        # islemsel grid onlar icin matematiksel olarak imkansiz esikler
        # iceriyor (bkz. src/config.py, SEQ_MINSUP_BY_DATASET).
        if dataset in SEQ_MINSUP_BY_DATASET:
            return "minsup", SEQ_MINSUP_BY_DATASET[dataset]
        # Dataset'e ozel grid varsa onu kullan (yogunluga gore ayarlanmis).
        return "minsup", MINSUP_BY_DATASET.get(dataset, MINSUP_VALUES)
    elif p == "maxsup":
        return "maxsup", MAXSUP_VALUES
    elif p == "min_utility":
        # foodmart'in max utility'si ~111 oldugu icin daha dusuk esik kullan
        if dataset == "foodmart":
            return "min_utility", MIN_UTILITY_FOODMART
        return "min_utility", MIN_UTILITY_VALUES
    elif p == "window_size":
        return "minsup", [0.1, 0.2]
    return p, [0.2]


def get_input_path(dataset: str, input_type: str) -> str:
    """Dataset tipine gore dogru input dosyasini dondurur."""
    if input_type == "utility":
        return str(get_utility_dataset_path(dataset))
    return str(get_dataset_path(dataset))


def load_completed_runs() -> set:
    """Mevcut CSV'den tamamlanmis (algorithm, dataset, param_value) uclulerini yukler."""
    if not SUMMARY_CSV.exists():
        return set()
    completed = set()
    try:
        import pandas as pd
        df = pd.read_csv(SUMMARY_CSV)
        for _, row in df.iterrows():
            key = (str(row["algorithm"]), str(row["dataset"]), param_key(row["param_value"]))
            completed.add(key)
    except Exception:
        pass
    return completed


def run_benchmark(
    algo_names=None,
    dataset_names=None,
    categories=None,
    resume=True,
):
    """
    Belirtilen algoritmalar, datasetler ve kategoriler icin benchmark calistirir.
    resume=True: zaten calistirilmis (algo, dataset, param) kombinasyonlarini atlar.
    Tum sonuclar results/summary.csv'ye eklenir; ham JSON'lar results/raw/ altina kaydedilir.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_rows = 0

    completed = load_completed_runs() if resume else set()
    if completed:
        print(f"[INFO] {len(completed)} onceden tamamlanmis calistirma bulundu, atlanacak.")

    write_header = not SUMMARY_CSV.exists()
    csv_file = open(SUMMARY_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
    if write_header:
        writer.writeheader()

    algos_to_run = {
        name: cfg for name, cfg in ALGORITHMS.items()
        if (algo_names is None or name in algo_names)
        and (categories is None or cfg["category"] in categories)
    }

    print(f"[INFO] {len(algos_to_run)} algoritma secildi.")

    try:
        for name, cfg in algos_to_run.items():
            if not cfg.get("available"):
                note = cfg.get("note", "implementasyon mevcut degil")
                print(f"[SKIP] {name}: {note}")
                continue

            spmf_name = cfg["spmf_name"]
            input_type = cfg["input_type"]
            # --datasets bir FILTREDIR, bir OVERRIDE degil.  Eskiden
            # `dataset_names or DATASETS[input_type]` yaziliyordu; bu, secilen
            # datasetleri algoritmanin girdi tipinden BAGIMSIZ olarak
            # calistiriyordu (or. islemsel DefMe'yi sirali leviathan uzerinde).
            # Sonuc sessizce anlamsiz satirlar uretiyordu: -1 ayraclari birer
            # oge gibi okundugu icin kosu "basarili" gorunuyordu.
            valid_ds = DATASETS.get(input_type, [])
            if dataset_names:
                ds_list = [d for d in valid_ds if d in dataset_names]
            else:
                ds_list = valid_ds

            for dataset in ds_list:
                param_name, param_vals = get_param_values(cfg, dataset)
                try:
                    input_path = get_input_path(dataset, input_type)
                except FileNotFoundError as e:
                    print(f"[SKIP] {e}")
                    continue

                exe = cfg.get("exe")
                exe_type = cfg.get("exe_type")
                count_fn = COUNT_FUNCS.get(cfg.get("count_fn"))
                n_transactions = None  # lazy-loaded for external algos

                for param_val in param_vals:
                    safe_param = str(param_val).replace(".", "_")
                    out_file = str(RESULTS_DIR / f"out_{name}_{dataset}_{safe_param}.txt")

                    # Resume: daha once calistirildiysa atla
                    run_key = (name, dataset, param_key(param_val))
                    if resume and run_key in completed:
                        print(f"[SKIP-DONE] {name} | {dataset} | {param_name}={param_val}", flush=True)
                        continue

                    label = f"{name} | {dataset} | {param_name}={param_val}"
                    print(f"[RUN]  {label}", flush=True)

                    error = None
                    try:
                        if exe and exe_type:
                            # External (non-SPMF) executable
                            if n_transactions is None:
                                n_transactions = count_transactions(input_path)
                            abs_sup = max(1, int(round(param_val * n_transactions))) if param_val else 1

                            if exe_type == "grgrowth":
                                # GrGrowth-PBd: exe input abs_sup k output_base
                                # k icin bkz. config.GRGROWTH_K aciklamasi:
                                # k=1 minimal jeneratör, k>1 daha dar bir sinif.
                                out_base = out_file.replace(".txt", "")
                                result = run_external(
                                    exe,
                                    [input_path, abs_sup, GRGROWTH_K, out_base],
                                    out_base + ".txt",
                                    timeout=TIMEOUT_SECONDS,
                                    count_fn=count_grgrowth_generators,
                                )
                            elif exe_type == "borgelt":
                                # Borgelt apriori/eclat/fpgrowth:
                                #   exe -tg -s<pct> input output
                                # -tg  : hedef tipi = generators (free/key itemsets)
                                # -s#  : pozitif deger => transaction yuzdesi
                                pct = param_val * 100
                                pct_str = ("%g" % pct)
                                result = run_external(
                                    exe,
                                    ["-tg", "-s" + pct_str, input_path, out_file],
                                    out_file,
                                    timeout=TIMEOUT_SECONDS,
                                    count_fn=count_fn or count_borgelt_generators,
                                )
                            elif exe_type == "fgcstream":
                                # FGC_Stream: exe input abs_sup 0 output window_size
                                result = run_external(
                                    exe,
                                    [input_path, abs_sup, 0, out_file, n_transactions],
                                    out_file,
                                    timeout=TIMEOUT_SECONDS,
                                    count_fn=count_fgcstream_generators,
                                )
                            else:
                                raise ValueError(f"Bilinmeyen exe_type: {exe_type}")
                        else:
                            # SPMF algoritma
                            params = [param_val] if param_val is not None else []
                            result = run_spmf(
                                spmf_name, input_path, out_file, params,
                                timeout=TIMEOUT_SECONDS, count_fn=count_fn,
                            )
                    except Exception as e:
                        result = {
                            "runtime_s": None,
                            "peak_memory_mb": None,
                            "generator_count": 0,
                            "timed_out": False,
                            "returncode": -1,
                            "stdout": "",
                            "stderr": str(e),
                        }
                        error = str(e)

                    # Sessiz cokme: sifir-disi cikis / OOM.  Bu kosular kismi
                    # cikti biraktigi icin sayim GECERSIZ; hatayi kayda gecir.
                    if not error and result.get("failure"):
                        error = result["failure"]

                    # Disk koruma: sayim yapildi, buyuk cikti dosyasini birak.
                    # Boyut JSON'a yazilir, bilgi kaybi olmaz.
                    out_bytes = None
                    try:
                        for cand in (Path(out_file), Path(out_file.replace(".txt", "") + ".txt")):
                            if cand.exists():
                                out_bytes = cand.stat().st_size
                                if out_bytes > MAX_KEEP_OUTPUT_MB * 1024 * 1024:
                                    cand.unlink()
                                    print(f"       [disk] {cand.name} silindi "
                                          f"({out_bytes/1048576:.0f} MB > "
                                          f"{MAX_KEEP_OUTPUT_MB} MB)", flush=True)
                                break
                    except Exception:
                        pass
                    result["output_bytes"] = out_bytes

                    row = {
                        "algorithm": name,
                        "category": cfg["category"],
                        "dataset": dataset,
                        "param_name": param_name,
                        "param_value": param_val,
                        "runtime_s": result.get("runtime_s"),
                        "peak_memory_mb": result.get("peak_memory_mb"),
                        "generator_count": result.get("generator_count"),
                        "timed_out": result.get("timed_out"),
                        "error": error,
                        "timestamp": ts,
                    }

                    fname = f"{name}_{dataset}_{safe_param}_{ts}.json"
                    save_result({**row, **result}, fname)

                    # Her satırı anında yaz
                    writer.writerow(row)
                    csv_file.flush()
                    total_rows += 1

                    if result.get("timed_out"):
                        status = "TIMEOUT"
                    elif error:
                        status = "ERR"
                    else:
                        status = "OK"

                    print(
                        f"       [{status}] {result.get('runtime_s', '?')}s | "
                        f"{result.get('peak_memory_mb', '?')} MB | "
                        f"{result.get('generator_count', '?')} generators",
                        flush=True,
                    )
    finally:
        csv_file.close()

    print(f"\n[DONE] {total_rows} calistirma tamamlandi -> {SUMMARY_CSV}")
    return total_rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SPMF Generator Algorithm Benchmark Harness"
    )
    parser.add_argument("--algos", nargs="+", help="Belirli algoritmalar (boslukla ayir)")
    parser.add_argument("--datasets", nargs="+", help="Belirli datasetler (boslukla ayir)")
    parser.add_argument(
        "--categories", nargs="+", type=int, help="Kategori numaralari (boslukla ayir)"
    )
    args = parser.parse_args()
    run_benchmark(args.algos, args.datasets, args.categories)
