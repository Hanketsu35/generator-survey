"""Build the transactional files for the fresh confirmation.

    python tools/prepare_fresh.py

Eight datasets downloaded from the SPMF repository after every earlier test
had been scored. They are not in training, in either confirmation, or related
to a dataset there (results/FRESH_PROTOCOL.md). Rules, fixed before any miner
ran on them:

- plain transactions: as they are;
- sequence databases (-1 / -2, <t> timestamps): the set of items in each
  sequence;
- items:timestamp lines: the item part;
- ARFF with nominal attributes only (splice): one item per (attribute,
  value), the class attribute included, as UCI data is usually mined; the
  identifier attribute (splice's Instance_name, unique per row) is dropped.

Items are sorted and de-duplicated; empty transactions are dropped. Counts
go to results/fresh_prepare.txt.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
RAW = _ROOT / "datasets" / "raw"
CAND = _ROOT / "datasets" / "candidates"
LOG = _ROOT / "results" / "fresh_prepare.txt"

SOURCES = {
    "uscensus": (CAND / "USCensus.txt", "plain"),
    "t25i10d10k": (CAND / "t25i10d10k.txt", "plain"),
    "fifa_set": (CAND / "FIFA.txt", "sequence"),
    "bike_set": (CAND / "BIKE.txt", "sequence"),
    "msnbc_set": (CAND / "MSNBC.txt", "sequence"),
    "microblog_set": (CAND / "microblogPCU.txt", "sequence"),
    "ecommerce_fim": (CAND / "ecommerce_time_without_utility.txt", "utility"),
    "splice": (CAND / "uci" / "splice.arff", "arff"),
}


def records(src, kind):
    if kind != "arff":
        with open(src) as fh:
            for line in fh:
                s = line.strip()
                if not s or s[0] in "#@%":
                    continue
                if kind == "utility":
                    s = s.split(":")[0]
                toks = s.split()
                if kind == "sequence":
                    toks = [t for t in toks if t not in ("-1", "-2") and not t.startswith("<")]
                yield {int(t) for t in toks}
        return
    codes, data = [], False
    with open(src) as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("%"):
                continue
            low = s.lower()
            if low.startswith("@attribute"):
                vals = s[s.index("{") + 1:s.rindex("}")].split(",")
                ident = "instance_name" in low
                codes.append(None if ident else
                             {v.strip().strip("'\""): i for i, v in enumerate(vals)})
            elif low.startswith("@data"):
                data = True
            elif data:
                base, items = 1, set()
                for a, v in enumerate(s.split(",")):
                    if codes[a] is None:
                        continue
                    v = v.strip().strip("'\"")
                    if v != "?":
                        items.add(base + codes[a][v])
                    base += len(codes[a])
                yield items


def main():
    out = []
    for name, (src, kind) in SOURCES.items():
        n = empty = 0
        with open(RAW / ("%s.txt" % name), "w") as fo:
            for u in records(src, kind):
                if not u:
                    empty += 1
                    continue
                fo.write(" ".join(map(str, sorted(u))) + "\n")
                n += 1
        msg = "%-14s from %-36s (%s) %8d tx | empty dropped %d" % (name, src.name, kind, n, empty)
        print(msg)
        out.append(msg)
    LOG.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
