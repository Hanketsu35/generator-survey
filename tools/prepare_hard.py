"""Build the transactional files for the hard-threshold confirmation.

    python tools/prepare_hard.py

Seven datasets not used in training (results/training_runs.csv) or in the
first confirmation, turned into transactions by rules fixed before any miner
ran on them (results/HARD_PROTOCOL.md):

- utility databases (``items:total:utilities``): the item part;
- sequence databases (``-1`` ends an itemset, ``-2`` a sequence, ``<t>`` a
  timestamp): the set of items in each sequence.

Items are sorted and de-duplicated, as the SPMF miners assume; empty
transactions are dropped. Counts go to results/hard_prepare.txt.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
RAW = _ROOT / "datasets" / "raw"
CAND = _ROOT / "datasets" / "candidates"
LOG = _ROOT / "results" / "hard_prepare.txt"

#: name -> (source file, kind)
SOURCES = {
    "liquor": (CAND / "liquor_11.txt", "utility"),
    "foodmart_fim": (RAW / "foodmart.txt", "utility"),
    "bible_set": (RAW / "bible.txt", "sequence"),
    "leviathan_set": (RAW / "leviathan.txt", "sequence"),
    "sign_set": (RAW / "sign.txt", "sequence"),
    "eshop_set": (CAND / "e_shop.txt", "sequence"),
    "mooc_set": (CAND / "mooc.txt", "sequence"),
}


def items(line, kind):
    if kind == "utility":
        return line.split(":")[0].split()
    return [t for t in line.split() if t not in ("-1", "-2") and not t.startswith("<")]


def main():
    out = []
    for name, (src, kind) in SOURCES.items():
        n = empty = 0
        with open(src) as fi, open(RAW / ("%s.txt" % name), "w") as fo:
            for line in fi:
                s = line.strip()
                if not s or s[0] in "#@%":
                    continue
                u = sorted({int(x) for x in items(s, kind)})
                if not u:
                    empty += 1
                    continue
                fo.write(" ".join(map(str, u)) + "\n")
                n += 1
        msg = "%-14s from %-16s (%s) %8d tx | empty dropped %d" % (name, src.name, kind, n, empty)
        print(msg)
        out.append(msg)
    LOG.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
