"""Build the transactional files for the seventh fresh confirmation.

    python tools/prepare_fresh7.py

Datasets: OpenML-CC18 (study 99), selected by the rule in
results/FRESH7_PROTOCOL.md (results/fresh7_selection.json), downloaded
2026-10-03. Same conversion rule as tools/prepare_fresh4.py. Names are
prefixed "oml_" so none collides with an earlier dataset. Counts go to
results/fresh7_prepare.txt.
"""
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))

import prepare_fresh5 as P5                                # noqa: E402

SRC = _ROOT / "datasets" / "candidates" / "openml"


def safe(name):
    return "oml_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main():
    from prepare_fresh4 import convert
    sel = json.load(open(_ROOT / "results" / "fresh7_selection.json"))
    out = []
    for _did, name, _n, _f, _fid in sel:
        d = P5.read_arff(SRC / ("%s.arff" % name)).dropna(how="all")
        m, n_items = convert(d)
        n = 0
        with open(P5.RAW / ("%s.txt" % safe(name)), "w") as fo:
            for row in m.itertuples(index=False):
                u = sorted({int(x) for x in row if x is not None and x == x})
                if u:
                    fo.write(" ".join(map(str, u)) + "\n")
                    n += 1
        msg = "%-34s %8d tx  %5d items  %3d columns" % (safe(name), n, n_items, d.shape[1])
        print(msg, flush=True)
        out.append(msg)
    (_ROOT / "results" / "fresh7_prepare.txt").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
