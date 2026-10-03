"""Build the transactional files for the fifth fresh confirmation (intervals,
exact memory). results/FRESH5_PROTOCOL.md.

    python tools/prepare_fresh5.py

Eleven UCI datasets from SPMF's uci_datasets.zip (downloaded 2026-09-30,
never used) and SUSY (UCI, downloaded 2026-10-03, 5,000,000 rows). Excluded
as copies or relatives of data used before: mushroom, kr-vs-kp, letter,
splice, and sick (the same thyroid records as hypothyroid). One rule, as in
tools/prepare_fresh4.py: a numeric column with more than 16 distinct values
in 5 equal-frequency bins, every other column nominal, one item per (column,
value or bin), '?' missing. Counts go to results/fresh5_prepare.txt.
"""
import re
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
RAW = _ROOT / "datasets" / "raw"
UCI = _ROOT / "datasets" / "candidates" / "uci"
LOG = _ROOT / "results" / "fresh5_prepare.txt"
ARFF = ["anneal", "breast-cancer", "colic", "credit-a", "credit-g", "hypothyroid",
        "primary-tumor", "soybean", "vote", "waveform-5000", "segment"]


def read_arff(path):
    names, rows, data = [], [], False
    for line in open(path, errors="ignore"):
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        low = s.lower()
        if low.startswith("@attribute"):
            m = re.match(r"@attribute\s+('[^']*'|\"[^\"]*\"|\S+)", s, re.I)
            names.append(m.group(1).strip("'\""))
        elif low.startswith("@data"):
            data = True
        elif data:
            rows.append([v.strip().strip("'\"") for v in s.split(",")])
    return pd.DataFrame(rows, columns=names, dtype=str)


def main():
    import sys
    sys.path.insert(0, str(_ROOT / "tools"))
    from prepare_fresh4 import convert
    out = []
    todo = [(n, lambda n=n: read_arff(UCI / ("%s.arff" % n))) for n in ARFF]
    susy = _ROOT / "datasets" / "candidates" / "uci5" / "SUSY.csv.gz"
    if susy.exists():
        todo.append(("susy", lambda: pd.read_csv(susy, header=None, dtype="float32")))
    for name, load in todo:
        d = load().dropna(how="all")
        m, n_items = convert(d)
        n = 0
        with open(RAW / ("%s.txt" % name.replace("-", "_")), "w") as fo:
            for row in m.itertuples(index=False):
                u = sorted({int(x) for x in row if x is not None and x == x})
                if u:
                    fo.write(" ".join(map(str, u)) + "\n")
                    n += 1
        msg = "%-14s %8d tx  %5d items  %3d columns" % (name.replace("-", "_"), n, n_items, d.shape[1])
        print(msg, flush=True)
        out.append(msg)
    LOG.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
