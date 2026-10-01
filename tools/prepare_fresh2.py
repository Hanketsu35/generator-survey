"""Build the transactional files for the second fresh confirmation (large data).

    python tools/prepare_fresh2.py

Four UCI datasets, downloaded after FRESH_RESULTS.md was scored, chosen to be
large enough that the probe samples them (n > 32 x 2,500). None is in any
earlier table or related to a dataset there. Rules fixed before any miner ran
(results/FRESH2_PROTOCOL.md):

- one item per (column, value) for nominal columns; '?' is missing (no item);
- numeric columns: 5 equal-frequency bins over the column (pandas qcut,
  repeated edges dropped), one item per (column, bin);
- one-hot binary columns (covertype 10-53): an item only where the value is 1;
- identifiers and weights dropped: census-income's instance weight (data
  column 24), diabetes130's encounter_id and patient_nbr.

Counts go to results/fresh2_prepare.txt.
"""
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
RAW = _ROOT / "datasets" / "raw"
SRC = _ROOT / "datasets" / "candidates" / "uci2"
LOG = _ROOT / "results" / "fresh2_prepare.txt"
BINS = 5

CENSUS_NUMERIC = [0, 5, 16, 17, 18, 30, 39]       # data columns (weight at 24 shifts later ones)
DIAB_NUMERIC = ["time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications",
                "number_outpatient", "number_emergency", "number_inpatient", "number_diagnoses"]


def load(name):
    if name == "poker":
        d = pd.read_csv(SRC / "poker+hand" / "poker-hand-testing.data", header=None)
        return d, [], []
    if name == "covertype":
        d = pd.read_csv(SRC / "covertype" / "covtype.data", header=None)
        return d, list(range(10)), list(range(10, 54))
    if name == "census_kdd":
        d = pd.read_csv(SRC / "census+income+kdd" / "census-income.data", header=None,
                        skipinitialspace=True, dtype=str)
        d = d.drop(columns=[24])
        for c in CENSUS_NUMERIC:
            d[c] = pd.to_numeric(d[c])
        return d, CENSUS_NUMERIC, []
    if name == "diabetes130":
        d = pd.read_csv(SRC / "diabetes130" / "diabetic_data.csv", dtype=str)
        d = d.drop(columns=["encounter_id", "patient_nbr"])
        for c in DIAB_NUMERIC:
            d[c] = pd.to_numeric(d[c])
        return d, DIAB_NUMERIC, []
    raise KeyError(name)


def items(d, numeric, onehot):
    cols, base = [], 1
    for c in d.columns:
        if c in onehot:
            v = d[c].astype(int)
            cols.append(v.where(v == 1).map(lambda x, b=base: b if x == 1 else None))
            base += 1
            continue
        s = pd.qcut(d[c], BINS, labels=False, duplicates="drop") if c in numeric else d[c]
        s = s.where(s.astype(str) != "?")
        codes, uniq = pd.factorize(s, sort=True)
        cols.append(pd.Series([base + k if k >= 0 else None for k in codes], index=d.index))
        base += len(uniq)
    return pd.concat(cols, axis=1), base - 1


def main():
    out = []
    for name in ("poker", "covertype", "census_kdd", "diabetes130"):
        d, numeric, onehot = load(name)
        m, n_items = items(d, numeric, onehot)
        n = 0
        with open(RAW / ("%s.txt" % name), "w") as fo:
            for row in m.itertuples(index=False):
                u = sorted({int(x) for x in row if x is not None and x == x})
                if u:
                    fo.write(" ".join(map(str, u)) + "\n")
                    n += 1
        msg = "%-12s %8d tx, %5d item codes, %d columns (%d numeric binned, %d one-hot)" % (
            name, n, n_items, d.shape[1], len(numeric), len(onehot))
        print(msg, flush=True)
        out.append(msg)
    LOG.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
