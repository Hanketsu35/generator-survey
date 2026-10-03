"""Build the transactional files for the sixth fresh confirmation (runtime
intervals). results/FRESH6_PROTOCOL.md.

    python tools/prepare_fresh6.py

The thirteen remaining UCI datasets of SPMF's uci_datasets.zip that are
neither used before nor relatives of data used before. Excluded: heart-h and
heart-statlog (the same heart-disease study as heart-c), the .ORIG variants,
and labor and iris (57 and 150 rows). Same rule as tools/prepare_fresh5.py.
Counts go to results/fresh6_prepare.txt.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))

import prepare_fresh5 as P5                                # noqa: E402

NAMES = ["audiology", "autos", "balance-scale", "breast-w", "diabetes", "glass", "heart-c",
         "ionosphere", "lymph", "sonar", "vehicle", "vowel", "zoo"]


def main():
    from prepare_fresh4 import convert
    out = []
    for name in NAMES:
        d = P5.read_arff(P5.UCI / ("%s.arff" % name)).dropna(how="all")
        m, n_items = convert(d)
        n = 0
        safe = name.replace("-", "_")
        with open(P5.RAW / ("%s.txt" % safe), "w") as fo:
            for row in m.itertuples(index=False):
                u = sorted({int(x) for x in row if x is not None and x == x})
                if u:
                    fo.write(" ".join(map(str, u)) + "\n")
                    n += 1
        msg = "%-14s %8d tx  %5d items  %3d columns" % (safe, n, n_items, d.shape[1])
        print(msg, flush=True)
        out.append(msg)
    (_ROOT / "results" / "fresh6_prepare.txt").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
