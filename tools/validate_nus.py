"""Audit GC-growth and DPMiner (DPM-delta) against independent oracles.

    python tools/validate_nus.py [--configs mushroom:0.4,chess:0.7,...]

Both programs write a generator file (<base>.key: length, items, support per
line), a closed-pattern file (<base>.closed) and the generator--closure
pairs (<base>.pair). For every configuration:

  soundness    each generator's support is recomputed with vertical bitsets
               and every immediate subset is checked to have a larger
               support (a generator has no proper subset of equal support,
               and support is anti-monotone, so immediate subsets suffice);
               each pair's closure is checked to be the closure of its
               generator;
  completeness the generator set is compared, as a set, with the generators
               of Borgelt's Eclat (-tg) at the same absolute threshold,
               minus the empty set.

DPM-delta needs class labels: each transaction is given the single label 0
(items shifted by one so that no item collides with it), with one class and
the delta of the run. Its output is the generators of the delta-
discriminative equivalence classes that have no delta-discriminative
sub-pattern, never the whole family; with one class every class is delta-
discriminative, so it returns the frequent single items with their
closures. Writes results/validate_nus.txt.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

from src.datasets import get_dataset_path                 # noqa: E402

GC = _ROOT / "external_algos" / "GC_growth" / "GcGrowth"
DPM = _ROOT / "external_algos" / "DPMiner" / "DPM-delta"
ECLAT = _ROOT / "external_algos" / "borgelt" / "eclat"
OUT = _ROOT / "results" / "validate_nus.txt"
DEFAULT = ("mushroom:0.05,mushroom:0.1,mushroom:0.2,mushroom:0.3,mushroom:0.4,mushroom:0.5,"
           "chess:0.5,chess:0.6,chess:0.7,connect:0.7,connect:0.8,connect:0.9,"
           "retail:0.001,retail:0.002,t10i4d100k:0.002,t10i4d100k:0.005,"
           "pumsb:0.8,pumsb:0.9,accidents:0.5,accidents:0.7")


def read_db(path):
    rows = [line.split() for line in open(path) if line.split()]
    bits = {}
    for t, row in enumerate(rows):
        for it in row:
            bits[it] = bits.get(it, 0) | (1 << t)
    return rows, bits


def support(itemset, bits, n):
    b = (1 << n) - 1
    for it in itemset:
        b &= bits.get(it, 0)
        if not b:
            return 0
    return bin(b).count("1")


def closure(itemset, bits, n):
    """Items present in every transaction that contains the itemset."""
    b = (1 << n) - 1
    for it in itemset:
        b &= bits.get(it, 0)
    if not b:
        return None
    return frozenset(it for it, v in bits.items() if v & b == b)


def parse(path, shift=0):
    """-> [(itemset, support or None)]; DPM-delta's .key has no support."""
    out = []
    for line in open(path):
        t = line.split()
        if not t:
            continue
        k = int(t[0])
        items = frozenset(str(int(x) - shift) for x in t[1:1 + k] if int(x) >= shift)
        out.append((items, int(t[1 + k]) if len(t) > 1 + k else None))
    return out


def eclat_generators(data, abs_sup, work):
    out = os.path.join(work, "eclat.txt")
    subprocess.run([str(ECLAT), "-tg", "-s-%d" % abs_sup, data, out], capture_output=True)
    gens = set()
    for line in open(out):
        body = line.split("(")[0].split()
        gens.add(frozenset(body))
    return gens


def run(prog, data, abs_sup, work, delta):
    base = os.path.join(work, "out")
    if prog == "GC-growth":
        subprocess.run([str(GC), data, str(abs_sup), base], capture_output=True)
        shift = 0
    else:
        lab = os.path.join(work, "labelled.txt")
        with open(data) as src, open(lab, "w") as dst:
            for line in src:
                t = line.split()
                if t:
                    dst.write("0 " + " ".join(str(int(x) + 1) for x in t) + "\n")
        subprocess.run([str(DPM), lab, "1", str(abs_sup), str(delta), base], capture_output=True)
        shift = 1
    keys, closed = parse(base + ".key", shift), parse(base + ".closed", shift)
    pairs = [tuple(map(int, l.split())) for l in open(base + ".pair") if l.split()]
    sup = {g: closed[c][1] for g, c in pairs}
    keys = [(k, s if s is not None else sup.get(i)) for i, (k, s) in enumerate(keys)]
    return keys, closed, pairs


def audit(prog, ds, sigma, delta=0):
    data = str(get_dataset_path(ds))
    rows, bits = read_db(data)
    n = len(rows)
    abs_sup = max(1, int(round(sigma * n)))
    with tempfile.TemporaryDirectory() as work:
        keys, closed, pairs = run(prog, data, abs_sup, work, delta)
        ref = eclat_generators(data, abs_sup, work)
    bad_sup = bad_min = bad_clo = 0
    for items, sup in keys:
        s = support(items, bits, n)
        if s != sup or s < abs_sup:
            bad_sup += 1
            continue
        if items and any(support(items - {i}, bits, n) == s for i in items):
            bad_min += 1
    for gi, ci in pairs:
        g, c = keys[gi][0], closed[ci][0]
        if g and closure(g, bits, n) != c:
            bad_clo += 1
    got = {k for k, _ in keys if k}
    return {"n": n, "abs": abs_sup, "generators": len(got), "eclat": len(ref),
            "missing": len(ref - got), "extra": len(got - ref), "bad_support": bad_sup,
            "not_minimal": bad_min, "bad_closure": bad_clo,
            "empty_set": any(not k for k, _ in keys)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=DEFAULT)
    ap.add_argument("--programs", default="GC-growth,DPMiner")
    ap.add_argument("--delta", type=int, default=0)
    a = ap.parse_args(argv)
    lines = []
    for prog in a.programs.split(","):
        for c in a.configs.split(","):
            ds, s = c.split(":")
            r = audit(prog, ds, float(s), a.delta)
            line = ("%-9s %-11s %-6s abs %-7d gens %8d eclat %8d missing %6d extra %6d "
                    "bad_support %d not_minimal %d bad_closure %d empty_set %s"
                    % (prog, ds, s, r["abs"], r["generators"], r["eclat"], r["missing"],
                       r["extra"], r["bad_support"], r["not_minimal"], r["bad_closure"],
                       r["empty_set"]))
            print(line, flush=True)
            lines.append(line)
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
