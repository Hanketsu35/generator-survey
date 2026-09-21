"""Arima'nin OOM ile biten 5 kosusunu BUYUTULMUS heap ile yeniden calistirir.

Amac (tani / diagnostic):
    Ana protokol tum JVM algoritmalarini ayni kosullarda -- JVM varsayilan
    heap'i (fiziksel RAM'in 1/4'u, bu makinede ~4 GB) -- olcer. Arima'nin
    chess ve connect uzerindeki 5 kosusu bu tavana carpip
    java.lang.OutOfMemoryError ile dustu.

    Bu bir ALGORITMA siniri mi, yoksa yalnizca bir KONFIGURASYON siniri mi?
    Bunu ayirt etmenin tek yolu ayni kosuyu daha buyuk bir heap ile
    tekrarlamaktir.

Onemli: sonuclar AYRI bir CSV'ye yazilir (results/arima_xmx_diagnostic.csv).
    results/summary.csv'ye DOKUNULMAZ; makalenin ana tablolarindaki
    tamamlanma oranlari tek-tip protokolu yansitmaya devam eder. Bu kosular
    ek kanit olarak raporlanir, ana olcum olarak degil.
"""
import csv
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, ".")

from src.config import TIMEOUT_SECONDS  # noqa: E402
from src.metrics import run_spmf, save_result  # noqa: E402

MAX_HEAP = "-Xmx12g"        # 16 GB makinede OS'e pay birakir
OUT_CSV = Path("results/arima_xmx_diagnostic.csv")

# summary.csv'de error sutunu OutOfMemoryError olan 5 konfigurasyon
CONFIGS = [
    ("chess", 0.1),
    ("chess", 0.2),
    ("chess", 0.3),
    ("connect", 0.2),
    ("connect", 0.3),
]

FIELDS = [
    "algorithm", "dataset", "param_name", "param_value", "max_heap",
    "runtime_s", "peak_memory_mb", "generator_count",
    "timed_out", "returncode", "error",
]


def main():
    rows = []
    for dataset, maxsup in CONFIGS:
        input_path = "datasets/raw/%s.txt" % dataset
        out_file = "results/output_xmx/Arima_%s_%s.txt" % (dataset, maxsup)
        print("[RUN] Arima %s maxsup=%s heap=%s" % (dataset, maxsup, MAX_HEAP),
              flush=True)

        result = run_spmf(
            "AprioriRare", input_path, out_file, [maxsup],
            timeout=TIMEOUT_SECONDS, max_heap=MAX_HEAP,
        )

        row = {
            "algorithm": "Arima",
            "dataset": dataset,
            "param_name": "maxsup",
            "param_value": maxsup,
            "max_heap": MAX_HEAP,
            "runtime_s": result.get("runtime_s"),
            "peak_memory_mb": result.get("peak_memory_mb"),
            "generator_count": result.get("generator_count"),
            "timed_out": result.get("timed_out"),
            "returncode": result.get("returncode"),
            "error": result.get("failure") or "",
        }
        rows.append(row)
        save_result(result, "Arima_%s_%s_xmx12g.json" % (dataset, maxsup))

        print("      -> %.1fs  %.1f MB  count=%s  timeout=%s  err=%s"
              % (row["runtime_s"] or -1, row["peak_memory_mb"] or -1,
                 row["generator_count"], row["timed_out"], row["error"] or "-"),
              flush=True)

        # Buyuk cikti dosyalarini diskte tutma; sayim zaten alindi.
        try:
            p = Path(out_file)
            if p.exists() and p.stat().st_size > 50 * 1024 * 1024:
                p.unlink()
        except OSError:
            pass

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("\n[DONE] -> %s" % OUT_CSV)


if __name__ == "__main__":
    main()
