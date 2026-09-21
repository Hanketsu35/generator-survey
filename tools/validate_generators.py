"""Verify Borgelt apriori/eclat/fpgrowth '-tg' mine MINIMAL GENERATORS.

Two independent tests.

(1) Exact set equality against SPMF reference generator miners
    (Talky-G, DefMe, and Pascal filtered to '#IS_GENERATOR: true').
    Cardinality agreement is weak evidence; we compare the itemsets themselves.

(2) Direct definition check.  X is a minimal generator iff no proper subset of
    X has the same support.  Support is anti-monotone, so if any proper subset
    matches supp(X) then some IMMEDIATE subset (size |X|-1) does too.  Checking
    immediate subsets is therefore sufficient and costs |X| probes per set.
    Supports are computed with vertical bitsets (Python ints).
"""
import os, subprocess, sys, itertools

ROOT = r"D:\Doktora\Dersler\CENG643\TermProject"
JAR = os.path.join(ROOT, "spmf", "spmf.jar")
BORG = os.path.join(ROOT, "external_algos", "borgelt")
TMP = os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "val")
os.makedirs(TMP, exist_ok=True)


def run_spmf(algo, data, out, pct):
    subprocess.run(["java", "-jar", JAR, "run", algo, data, out, "%g%%" % (pct * 100)],
                   capture_output=True, timeout=2400)


def run_borgelt(exe, data, out, pct):
    subprocess.run([os.path.join(BORG, exe), "-tg", "-s%g" % (pct * 100), data, out],
                   capture_output=True, timeout=2400)


def parse_spmf(path, only_generators=False):
    s = set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "#SUP:" not in line:
                continue
            if only_generators and "IS_GENERATOR: true" not in line:
                continue
            it = line.split("#SUP:")[0].strip()
            s.add(frozenset(it.split()) if it else frozenset())
    return s


def parse_borgelt(path):
    s = set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            it = line.split("(")[0].strip()
            s.add(frozenset(it.split()) if it else frozenset())
    return s


def build_bitsets(path):
    """item -> bitset of transaction ids"""
    bits, n = {}, 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            for it in line.split():
                bits[it] = bits.get(it, 0) | (1 << n)
            n += 1
    return bits, n


def sup(bits, items):
    m = None
    for it in items:
        b = bits.get(it, 0)
        m = b if m is None else (m & b)
        if m == 0:
            return 0
    return bin(m).count("1") if m is not None else 0


CASES = [("mushroom", 0.4), ("mushroom", 0.2), ("chess", 0.7)]

for ds, pct in CASES:
    data = os.path.join(ROOT, "datasets", "raw", "%s.txt" % ds)
    print("=" * 74)
    print("%s   minsup=%g" % (ds, pct))
    sets = {}
    for algo in ("TalkyG", "DefMe", "Pascal"):
        o = os.path.join(TMP, "%s_%s_%g.txt" % (algo, ds, pct))
        if not os.path.exists(o):
            run_spmf(algo, data, o, pct)
        sets[algo] = parse_spmf(o, only_generators=(algo == "Pascal"))
    for exe, name in (("apriori.exe", "Borgelt-apriori"),
                      ("eclat.exe", "Borgelt-eclat"),
                      ("fpgrowth.exe", "Borgelt-fpgrowth")):
        o = os.path.join(TMP, "%s_%s_%g.txt" % (name, ds, pct))
        if not os.path.exists(o):
            run_borgelt(exe, data, o, pct)
        sets[name] = parse_borgelt(o)

    for k in sets:                      # DefMe alone emits the empty set
        sets[k].discard(frozenset())

    ref = sets["TalkyG"]
    print("  (1) exact set equality vs Talky-G")
    for k, v in sets.items():
        if v == ref:
            print("      %-18s n=%-7d IDENTICAL" % (k, len(v)))
        else:
            print("      %-18s n=%-7d DIFFERS (+%d / -%d)"
                  % (k, len(v), len(v - ref), len(ref - v)))

    print("  (2) minimality by definition (immediate subsets)")
    bits, ntx = build_bitsets(data)
    for name in ("Borgelt-apriori", "Borgelt-eclat", "Borgelt-fpgrowth"):
        cand = [c for c in sets[name] if len(c) >= 2]
        viol = 0
        for its in cand:
            s = sup(bits, its)
            for sub in itertools.combinations(its, len(its) - 1):
                if sup(bits, sub) == s:
                    viol += 1
                    break
        print("      %-18s %d sets checked, %d violations" % (name, len(cand), viol))
