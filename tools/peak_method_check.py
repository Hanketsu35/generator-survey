"""Polled VmHWM (the harness) vs exact ru_maxrss (tools/peakrun) on the same runs.

    python tools/peak_method_check.py

Each (miner, dataset, sigma) is run REPS times each way, one at a time.
Output: results/peak_method_check.csv
"""
import os
import statistics as st
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

from src import metrics as M                              # noqa: E402
from src.config import ALGORITHMS, GRGROWTH_K             # noqa: E402

PEAKRUN = str(_ROOT / "tools" / "peakrun" / "peakrun")
REPS = 5
CASES = [("car", 0.1862), ("tictactoe", 0.1584), ("bank_full", 0.001963),
         ("bank_full", 0.03149), ("chess", 0.5), ("retail", 0.001)]
MINERS = ["Apriori_Gen_Borgelt", "Eclat_Gen_Borgelt", "FPgrowth_Gen_Borgelt", "Gr_growth"]


def argv(name, path, n, sigma, out):
    c = ALGORITHMS[name]
    exe = str(Path(c["exe"]).resolve())
    if c.get("exe_type") == "grgrowth":
        return [exe, path, str(max(1, int(round(sigma * n)))), str(GRGROWTH_K), out[:-4]], out
    return [exe, "-tg", "-s%g" % (sigma * 100), path, out], out


def main():
    rows = []
    w = tempfile.mkdtemp(prefix="peakchk_")
    for ds, sg in CASES:
        path = str(_ROOT / "datasets" / "raw" / ("%s.txt" % ds))
        n = sum(1 for _ in open(path))
        for a in MINERS:
            cmd, out = argv(a, path, n, sg, os.path.join(w, "o_%s.txt" % a))
            polled, exact, secs = [], [], []
            for _ in range(REPS):
                r = M.run_external(cmd[0], cmd[1:], out, timeout=120, count_fn=lambda p: 0)
                polled.append(r["peak_memory_mb"] or 0.0)
                secs.append(r["runtime_s"])
                pk = os.path.join(w, "pk.txt")
                subprocess.run([PEAKRUN, pk] + cmd, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=120)
                exact.append(int(open(pk).read()) / 1024.0)
                for f in os.listdir(w):
                    if f.startswith("o_"):
                        os.remove(os.path.join(w, f))
            rows.append({"dataset": ds, "sigma": sg, "algorithm": a, "runtime_s": st.median(secs),
                         "polled_min": min(polled), "polled_max": max(polled),
                         "polled_med": st.median(polled), "exact_min": min(exact),
                         "exact_max": max(exact), "exact_med": st.median(exact)})
            r = rows[-1]
            print("%-10s %-9g %-21s %6.3fs | polled %7.2f..%7.2f | exact %7.2f..%7.2f"
                  % (ds, sg, a, r["runtime_s"], r["polled_min"], r["polled_max"],
                     r["exact_min"], r["exact_max"]), flush=True)
    import pandas as pd
    pd.DataFrame(rows).to_csv(_ROOT / "results" / "peak_method_check.csv", index=False)


if __name__ == "__main__":
    main()
