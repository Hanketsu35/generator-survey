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


#: Exit codes that are a program's convention rather than a failure, each
#: confirmed in the program's own source before being listed here:
#:   Gr-growth   fggrowth.cpp ends ``return (int)gdtotal_generators;`` -- the
#:               exit status IS the generator count.
#:   Borgelt     apriori.c defines ``E_NOITEMS -15 "no (frequent) items
#:               found"``: an empty result, not a crash.
def _conventional_exit(algorithm, rc, generator_count):
    if algorithm == "Gr_growth" and generator_count is not None \
            and rc == generator_count:
        return True
    if str(algorithm).endswith("_Borgelt") and rc == 15:
        return True
    return False


def nonzero_exit_rows(df) -> dict:
    """row index -> error label, for runs that exited non-zero and were kept.

    ``crashed_runs`` detects a crash only by the text it left in stdout or
    stderr. A process killed without a message leaves neither: Zart on connect
    at minsup 0.8 ran 1741 s, exited with -1 (4294967295 unsigned, as Windows
    reports it), wrote no output, and was recorded as a COMPLETED run with 0
    generators -- where DefMe finds 15,108. The layer-3 model trained on it as a
    1741-second success.

    Two differences from ``crashed_runs``, both deliberate:

      * the JSON checked is the one that PRODUCED the row, found by timestamp.
        results/raw also holds superseded re-runs of the same configuration, and
        matching on (algorithm, dataset, threshold) alone would mark a row as
        crashed because an OLDER run of it crashed;
      * exit codes that are a documented program convention are not failures.
        Without that rule this check flags 79 rows, every one of them a correct
        run: 58 Gr-growth rows and 21 Borgelt rows.
    """
    out = {}
    for idx, r in df.iterrows():
        if str(r.timed_out).lower() == "true" or not pd.isna(r.error):
            continue                  # timeout is protocol; error already set
        pv = ("%s" % r.param_value).replace(".", "_")
        f = RAW / ("%s_%s_%s_%s.json" % (r.algorithm, r.dataset, pv, r.timestamp))
        if not f.exists():
            continue
        try:
            d = json.load(open(f, encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        rc = d.get("returncode")
        if rc in (0, None) or _conventional_exit(r.algorithm, rc,
                                                 d.get("generator_count")):
            continue
        signed = rc - (1 << 32) if rc >= (1 << 31) else rc
        out[idx] = ("non-zero exit code %d%s, no error text"
                    % (signed, " (%d unsigned)" % rc if signed != rc else ""))
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change, write nothing")
    args = ap.parse_args(argv)

    # generator_count is read as TEXT and written back untouched. The file mixes
    # "1" and "1.0" for the same kind of value, because rows were appended by
    # runs with different dtypes; reading it as a number and marking one cell
    # NA turns the whole column float and rewrites 48 unrelated rows. The data
    # would be unchanged and the diff unreadable.
    df = pd.read_csv(SUMMARY, dtype={"generator_count": str})
    df["error"] = df["error"].astype("object")   # bos sutun float64 gelir

    silent = nonzero_exit_rows(df)
    print("[EXIT]  %d kept run(s) exited non-zero without error text:" % len(silent))
    for idx, label in silent.items():
        r = df.loc[idx]
        print("         %-8s %-9s %-7s  %8.1fs  gens %-8s  -> %s"
              % (r.algorithm, r.dataset, r.param_value, r.runtime_s,
                 r.generator_count, label))
    if args.dry_run:
        print("[DRY]   nothing written")
        return
    for idx, label in silent.items():
        df.loc[idx, "error"] = label
        df.loc[idx, "generator_count"] = pd.NA

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
