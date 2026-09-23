"""Turn the file a user actually has into the layout the miners read.

Every miner in the portfolio reads SPMF's format: one transaction per line,
items as whitespace-separated integers. Nobody arrives with that. They arrive
with a CSV, and in one of three shapes:

``basket``   one transaction per line, items separated by a delimiter
             milk,bread,eggs
             bread,butter
``long``     one (transaction, item) pair per line, usually with a header
             order_id,product
             17,milk
             17,bread
``onehot``   a header of item names and one 0/1 row per transaction
             milk,bread,eggs
             1,1,0

The shape is decided from the file itself and reported back in plain words,
because a misread file would be mined and recommended on without error: a long
file read as baskets turns every row into a two-item "transaction". Saying how
the file was read is the only way the user can catch that.

Only transactional data comes through this path. Sequences and utilities have
richer structure than a CSV shape can signal reliably, so those must already be
in SPMF's format -- which ``ask.sniff_format`` recognises -- and a CSV that
looks like either is refused rather than guessed at.
"""
import csv
import io
import re
from collections import OrderedDict

MIN_TRANSACTIONS = 10
MIN_ITEMS = 2
_TRUE = {"1", "1.0", "true", "yes", "y", "t", "x"}
_FALSE = {"0", "0.0", "false", "no", "n", "f", ""}


class IngestError(ValueError):
    """The file could not be read as transactional data; the message says why."""


def _is_spmf(lines):
    """Whitespace-separated integers (SPMF), including sequence/utility forms."""
    seen = 0
    for s in lines:
        s = s.strip()
        if not s or s[0] in "#@%":
            continue
        toks = s.replace(":", " ").split()
        if not all(re.fullmatch(r"-?\d+", t) for t in toks):
            return False
        seen += 1
    return seen > 0


def _delimiter(lines):
    counts = {d: sum(l.count(d) for l in lines) for d in (",", ";", "\t", "|")}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else None


def _looks_numeric(tok):
    try:
        float(tok)
        return True
    except ValueError:
        return False


def _header_likely(rows):
    """First row names columns if it is non-numeric while the rest are numeric."""
    if len(rows) < 2:
        return False
    first = rows[0]
    if any(_looks_numeric(c) for c in first if c.strip()):
        return False
    body = [c for r in rows[1:20] for c in r if c.strip()]
    return bool(body) and sum(_looks_numeric(c) for c in body) / len(body) > 0.8


def read_transactions(path, sample_lines=400):
    """-> (transactions as lists of item names, shape, explanation).

    Raises IngestError with a message meant for the user when the shape cannot
    be decided or the result is too small to mine.
    """
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        text = fh.read()
    head = text.splitlines()[:sample_lines]
    if _is_spmf(head):
        return None, "spmf", "already in SPMF format (integer item ids)"
    delim = _delimiter(head)
    if delim is None:
        # One token per line is a single-item "transaction" list; with spaces
        # it could be baskets separated by whitespace.
        rows = [l.split() for l in text.splitlines() if l.strip()]
        shape, how = "basket", "one transaction per line, items separated by spaces"
        tx = [r for r in rows]
        return _finish(tx, shape, how)

    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    rows = [[c.strip() for c in r] for r in rows if any(c.strip() for c in r)]
    if not rows:
        raise IngestError("the file is empty")
    dname = {",": "commas", ";": "semicolons", "\t": "tabs", "|": "pipes"}[delim]
    widths = {len(r) for r in rows[:sample_lines]}

    # onehot: a header of names, then rows of 0/1 of the same width
    if len(widths) == 1 and len(rows[0]) >= 2:
        body = [c.lower() for r in rows[1:sample_lines] for c in r]
        if body and all(c in _TRUE | _FALSE for c in body) and not _looks_numeric(rows[0][0]):
            names = rows[0]
            tx = [[names[j] for j, c in enumerate(r) if c.lower() in _TRUE]
                  for r in rows[1:]]
            return _finish(tx, "onehot",
                           "a header of %d item names and one 0/1 row per "
                           "transaction, separated by %s" % (len(names), dname))

    # long: exactly two columns and the first column repeats
    if widths == {2}:
        start = 1 if not _looks_numeric(rows[0][0]) and rows[0][0].lower() in (
            "id", "tid", "transaction", "transaction_id", "order", "order_id",
            "invoice", "invoice_id", "basket", "basket_id", "session", "session_id",
            "user", "user_id", "customer", "customer_id") else 0
        firsts = [r[0] for r in rows[start:]]
        if len(set(firsts)) < 0.9 * len(firsts):
            groups = OrderedDict()
            for tid, item in rows[start:]:
                if item:
                    groups.setdefault(tid, []).append(item)
            return _finish(list(groups.values()), "long",
                           "one (transaction, item) pair per line, grouped by the "
                           "first column%s" % (", header skipped" if start else ""))

    # basket: variable-length rows of item tokens
    start = 0
    if _header_likely(rows):
        start = 1
    tx = [[c for c in r if c] for r in rows[start:]]
    return _finish(tx, "basket",
                   "one transaction per line, items separated by %s" % dname)


def _finish(tx, shape, how):
    tx = [t for t in tx if t]
    items = {i for t in tx for i in t}
    if len(tx) < MIN_TRANSACTIONS:
        raise IngestError("only %d transactions were found; at least %d are needed "
                          "to mine patterns" % (len(tx), MIN_TRANSACTIONS))
    if len(items) < MIN_ITEMS:
        raise IngestError("only %d distinct item was found" % len(items))
    return tx, shape, how


def to_spmf(path, out_path):
    """Convert `path` if needed. -> dict(path, shape, how, item_names)

    ``item_names`` maps the integer ids written to the file back to the user's
    names, so a report can speak in them; None when the input was already SPMF.
    """
    tx, shape, how = read_transactions(path)
    if shape == "spmf":
        return {"path": path, "shape": shape, "how": how, "item_names": None}
    # Ids by descending frequency, so the most common item is 1 -- purely for
    # readability of the written file; no miner depends on the numbering.
    freq = {}
    for t in tx:
        for i in set(t):
            freq[i] = freq.get(i, 0) + 1
    ids = {name: k + 1 for k, name in enumerate(sorted(freq, key=lambda n: (-freq[n], n)))}
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        for t in tx:
            fh.write(" ".join(str(i) for i in sorted({ids[x] for x in t})))
            fh.write("\n")
    return {"path": out_path, "shape": shape, "how": how,
            "item_names": {v: k for k, v in ids.items()},
            "n_transactions": len(tx), "n_items": len(ids)}
