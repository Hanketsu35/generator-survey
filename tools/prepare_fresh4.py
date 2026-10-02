"""Build the transactional files for the fourth fresh confirmation (intervals).

    python tools/prepare_fresh4.py

Ten UCI datasets downloaded on 2026-10-02, after every earlier test had been
scored (results/FRESH4_PROTOCOL.md). One rule for all, fixed before any
miner or probe ran: a column that is numeric with more than 16 distinct
values is cut into 5 equal-frequency bins; any other column is nominal; one
item per (column, value or bin); '?' and empty are missing. Identifiers: none
in these files. Counts go to results/fresh4_prepare.txt.
"""
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
RAW = _ROOT / "datasets" / "raw"
SRC = _ROOT / "datasets" / "candidates" / "uci4"
LOG = _ROOT / "results" / "fresh4_prepare.txt"
BINS, NOMINAL_MAX = 5, 16

#: name -> (file, read_csv kwargs)
SOURCES = {
    "adult": ("adult/adult.data", dict(header=None, skipinitialspace=True)),
    "bank_full": ("bank+marketing/b/bank-full.csv", dict(sep=";")),
    "nursery": ("nursery/nursery.data", dict(header=None)),
    "letter": ("letter+recognition/letter-recognition.data", dict(header=None)),
    "shuttle": ("statlog+shuttle/shuttle.trn", dict(header=None, sep=r"\s+")),
    "krk": ("chess+king+rook+vs+king/krkopt.data", dict(header=None)),
    "shoppers": ("online+shoppers+purchasing+intention+dataset/online_shoppers_intention.csv", {}),
    "car": ("car+evaluation/car.data", dict(header=None)),
    "tictactoe": ("tic+tac+toe+endgame/tic-tac-toe.data", dict(header=None)),
    "yearmsd": ("yearmsd/YearPredictionMSD.txt", dict(header=None)),
}


def convert(d):
    cols, base = [], 1
    for c in d.columns:
        s = d[c].replace({"?": None, "": None})
        num = pd.to_numeric(s, errors="coerce")
        if num.notna().sum() == s.notna().sum() and num.nunique() > NOMINAL_MAX:
            s = pd.qcut(num, BINS, labels=False, duplicates="drop")
        codes, uniq = pd.factorize(s.astype(str).where(s.notna()), sort=True)
        cols.append(pd.Series([base + k if k >= 0 else None for k in codes], index=d.index))
        base += len(uniq)
    return pd.concat(cols, axis=1), base - 1


def main():
    out = []
    for name, (f, kw) in SOURCES.items():
        d = pd.read_csv(SRC / f, dtype=str, **kw).dropna(how="all")
        m, n_items = convert(d)
        n = 0
        with open(RAW / ("%s.txt" % name), "w") as fo:
            for row in m.itertuples(index=False):
                u = sorted({int(x) for x in row if x is not None and x == x})
                if u:
                    fo.write(" ".join(map(str, u)) + "\n")
                    n += 1
        msg = "%-10s %8d tx  %5d items  %3d columns" % (name, n, n_items, d.shape[1])
        print(msg, flush=True)
        out.append(msg)
    LOG.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
