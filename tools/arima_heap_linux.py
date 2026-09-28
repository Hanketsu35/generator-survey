"""Repeat the Arima enlarged-heap diagnostic on the Linux machine.

    python tools/arima_heap_linux.py      # ~1-1.5 h, one run at a time, <= 12 GB

The paper's Table (arima_heap) compared Arima's default-heap aborts with a
-Xmx12g repetition, both measured on the original Windows machine. On this
machine the default heap is ~7.8 GB (a quarter of 32 GB), so the default
column already differs: Chess at sigma_max=0.3 completes by default here.
The four configurations that still abort by default are re-run with -Xmx12g
so the table can be reported from one machine. Output:
results/arima_xmx_diagnostic_linux.csv.
"""
import csv
import glob
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)
_jre = sorted(glob.glob(os.path.expanduser("~/.local/opt/jdk-*/bin")))
if _jre:
    os.environ["PATH"] = _jre[-1] + os.pathsep + os.environ.get("PATH", "")

from src import metrics as M                              # noqa: E402
from src.harness import get_input_path                    # noqa: E402

CONFIGS = [("chess", 0.1), ("chess", 0.2), ("connect", 0.2), ("connect", 0.3)]
OUT = _ROOT / "results" / "arima_xmx_diagnostic_linux.csv"
SCRATCH = _ROOT / "results" / "remeasure_scratch"


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    fields = ["algorithm", "dataset", "param_name", "param_value", "max_heap", "runtime_s",
              "peak_memory_mb", "generator_count", "timed_out", "returncode", "error"]
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for ds, p in CONFIGS:
            out = str(SCRATCH / ("arima_%s_%s.txt" % (ds, p)))
            r = M.run_spmf("AprioriRare", get_input_path(ds, "transactional"), out, [p],
                           timeout=3600, max_heap="-Xmx12g")
            ok = not r.get("timed_out") and not r.get("failure")
            row = {"algorithm": "Arima", "dataset": ds, "param_name": "maxsup",
                   "param_value": p, "max_heap": "-Xmx12g", "runtime_s": r["runtime_s"],
                   "peak_memory_mb": r["peak_memory_mb"],
                   "generator_count": r.get("generator_count") if ok else "",
                   "timed_out": r.get("timed_out"), "returncode": r.get("returncode"),
                   "error": r.get("failure") or ""}
            w.writerow(row)
            fh.flush()
            print(row, flush=True)
            try:
                os.remove(out)
            except OSError:
                pass


if __name__ == "__main__":
    main()
