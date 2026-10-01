"""Build the transactional files for the third fresh confirmation.

    python tools/prepare_fresh3.py

Three UCI datasets, downloaded after FRESH2_RESULTS.md was scored, large
enough for the probe to sample (results/FRESH3_PROTOCOL.md). Rules, fixed
before any miner or probe ran:

- dota2 (dota2Train.csv): the outcome, cluster, game mode and game type as
  one item per (column, value); each hero column (-1 / 0 / 1) as an item for
  (hero, side) where nonzero;
- household power: Date and Time dropped; the 7 measurements in 5
  equal-frequency bins; '?' is missing;
- MiniBooNE: the 50 measurements in 5 equal-frequency bins, plus the class
  (signal for the first 36,499 rows after the header line, background after).

Counts go to results/fresh3_prepare.txt.
"""
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
RAW = _ROOT / "datasets" / "raw"
SRC = _ROOT / "datasets" / "candidates" / "uci3"
LOG = _ROOT / "results" / "fresh3_prepare.txt"
BINS = 5


def binned(d, cols):
    out, base = [], 1
    for c in cols:
        b = pd.qcut(d[c], BINS, labels=False, duplicates="drop")
        out.append(b.map(lambda x, o=base: None if pd.isna(x) else o + int(x)))
        base += int(b.max()) + 1
    return out, base


def write(name, cols):
    m = pd.concat(cols, axis=1)
    n = 0
    with open(RAW / ("%s.txt" % name), "w") as fo:
        for row in m.itertuples(index=False):
            u = sorted({int(x) for x in row if x is not None and x == x})
            if u:
                fo.write(" ".join(map(str, u)) + "\n")
                n += 1
    return n


def main():
    out = []
    # dota2
    d = pd.read_csv(SRC / "dota2+games+results" / "dota2Train.csv", header=None)
    cols, base = [], 1
    for c in range(4):
        codes, uniq = pd.factorize(d[c], sort=True)
        cols.append(pd.Series(codes + base, index=d.index))
        base += len(uniq)
    for c in range(4, d.shape[1]):
        cols.append(d[c].map(lambda x, o=base: o if x == -1 else (o + 1 if x == 1 else None)))
        base += 2
    out.append("dota2        %8d tx" % write("dota2", cols))
    # household power
    d = pd.read_csv(SRC / "individual+household+electric+power+consumption" /
                    "household_power_consumption.txt", sep=";", na_values="?", low_memory=False)
    d = d.drop(columns=["Date", "Time"]).apply(pd.to_numeric)
    cols, _ = binned(d, list(d.columns))
    out.append("power        %8d tx" % write("power", cols))
    # MiniBooNE
    p = SRC / "miniboone+particle+identification" / "MiniBooNE_PID.txt"
    with open(p) as fh:
        n_sig, _n_bg = map(int, fh.readline().split())
    d = pd.read_csv(p, sep=r"\s+", header=None, skiprows=1)
    cols, base = binned(d, list(d.columns))
    cols.append(pd.Series([base if i < n_sig else base + 1 for i in range(len(d))], index=d.index))
    out.append("miniboone    %8d tx" % write("miniboone", cols))
    print("\n".join(out))
    LOG.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
