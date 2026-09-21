"""
results/summary.csv uzerinde iki duzeltme yapar.  Idempotenttir.

1) SESSIZ COKMELER.  harness.py (bu duzeltmeden once) yalnizca Python
   istisnalarini 'error' sutununa yaziyordu; sifir-disi JVM cikis kodlari
   gozden kaciyordu.  Arima/chess ve Arima/connect kosulari varsayilan
   ~4 GB JVM heap'ini tuketip java.lang.OutOfMemoryError ile coktu, ama
   arkalarinda KISMI cikti dosyasi biraktiklari icin satirlar 'basarili'
   goruntusu verdi ve jeneratör sayilari yanlis kaydedildi.
   Bu satirlar ham JSON'lardan tespit edilip isaretlenir; sayimlari
   gecersiz kilinir (analyze.py hatali satirlari zaten filtreliyor).

2) TEKRARLANAN KOSULAR.  Resume anahtari param_value'yu duz str() ile
   karsilastirdigi icin "1000" ile "1000.0" farkli sanildi ve 18 utility
   kosusu iki kez calisti.  Ikisi de AYNI jeneratör sayisini verdi
   (tekrarlanabilirlik kaniti); en son kosu tutulur.
"""
import json
import glob
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

SUMMARY = Path("results/summary.csv")
RAW = Path("results/raw")


def crashed_runs() -> dict:
    """Ham JSON'lardan (algo, dataset, param) -> hata etiketi haritasi."""
    bad = {}
    for f in glob.glob(str(RAW / "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if str(d.get("timed_out")).lower() == "true":
            continue          # timeout hata degil, protokolun parcasi
        txt = (d.get("stderr") or "") + (d.get("stdout") or "")
        if "OutOfMemoryError" not in txt and "StackOverflowError" not in txt:
            continue          # sadece JVM cokmeleri; Borgelt'in rc=15'i
                              # ("no frequent items") gecerli bos sonuctur
        label = ("java.lang.OutOfMemoryError: Java heap space"
                 if "OutOfMemoryError" in txt else "java.lang.StackOverflowError")
        try:
            key = (str(d["algorithm"]), str(d["dataset"]), repr(float(d["param_value"])))
        except (KeyError, TypeError, ValueError):
            continue
        bad[key] = label
    return bad


def main():
    df = pd.read_csv(SUMMARY)
    df["error"] = df["error"].astype("object")   # bos sutun float64 gelir
    backup = SUMMARY.with_name(
        "summary_prerepair_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(SUMMARY, backup)
    print("[BACKUP] %s" % backup)

    before = len(df)
    df["_key"] = [
        (str(a), str(ds), repr(float(v)))
        for a, ds, v in zip(df.algorithm, df.dataset, df.param_value)
    ]

    # 1) cokmeleri isaretle
    bad = crashed_runs()
    hit = df["_key"].map(lambda k: bad.get(k, ""))
    mask = hit.astype(bool)
    df.loc[mask, "error"] = hit[mask]
    df.loc[mask, "generator_count"] = pd.NA
    print("[CRASH] %d satir OOM/crash olarak isaretlendi:" % mask.sum())
    for _, r in df[mask].iterrows():
        print("         %-8s %-9s %-7s  %8.1fs  %7.0f MB"
              % (r.algorithm, r.dataset, r.param_value,
                 r.runtime_s, r.peak_memory_mb))

    # 2) tekrarlari temizle (en sonu tut)
    dup = df.duplicated("_key", keep="last")
    if dup.any():
        d = df[df.duplicated("_key", keep=False)]
        consistent = d.groupby("_key").generator_count.nunique(dropna=False).le(1).all()
        print("[DUP]   %d tekrar satiri silindi; sayimlar tutarli mi: %s"
              % (dup.sum(), "EVET" if consistent else "HAYIR"))
    df = df[~dup].drop(columns=["_key"])

    df.to_csv(SUMMARY, index=False)
    print("[DONE]  %d -> %d satir" % (before, len(df)))


if __name__ == "__main__":
    main()
