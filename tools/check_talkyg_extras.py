"""Talky-G returns 149 itemsets at mushroom/minsup=0.2 that DefMe, Pascal and
all three Borgelt miners do not. Test those extras against the definition of a
minimal generator: X is minimal iff no proper subset of X has supp = supp(X).
(Anti-monotonicity => checking immediate subsets is sufficient.)
"""
import os, itertools

ROOT = r"D:\Doktora\Dersler\CENG643\TermProject"
TMP = os.path.join(os.environ["CLAUDE_JOB_DIR"], "tmp", "val")
DATA = os.path.join(ROOT, "datasets", "raw", "mushroom.txt")


def parse_spmf(path, only_gen=False):
    s = set()
    for line in open(path, encoding="utf-8", errors="ignore"):
        if "#SUP:" not in line:
            continue
        if only_gen and "IS_GENERATOR: true" not in line:
            continue
        it = line.split("#SUP:")[0].strip()
        s.add(frozenset(it.split()) if it else frozenset())
    return s


def parse_borgelt(path):
    s = set()
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        it = line.split("(")[0].strip()
        s.add(frozenset(it.split()) if it else frozenset())
    return s


bits, n = {}, 0
for line in open(DATA, encoding="utf-8", errors="ignore"):
    if not line.strip():
        continue
    for it in line.split():
        bits[it] = bits.get(it, 0) | (1 << n)
    n += 1


def sup(items):
    m = None
    for it in items:
        b = bits.get(it, 0)
        m = b if m is None else (m & b)
        if m == 0:
            return 0
    return bin(m).count("1") if m is not None else n


tg = parse_spmf(os.path.join(TMP, "TalkyG_mushroom_0.2.txt"))
bo = parse_borgelt(os.path.join(TMP, "Borgelt-fpgrowth_mushroom_0.2.txt"))
tg.discard(frozenset()); bo.discard(frozenset())

extra = tg - bo
print("Talky-G sets: %d | Borgelt sets: %d | Talky-G extras: %d"
      % (len(tg), len(bo), len(extra)))

viol = nonviol = 0
examples = []
for its in extra:
    s = sup(its)
    hit = None
    for sub in itertools.combinations(sorted(its), len(its) - 1):
        if sup(sub) == s:
            hit = sub
            break
    if hit is not None:
        viol += 1
        if len(examples) < 5:
            examples.append((sorted(its), s, list(hit)))
    else:
        nonviol += 1

print("\nOf Talky-G's %d extra sets:" % len(extra))
print("  NOT minimal generators (a proper subset has equal support): %d" % viol)
print("  genuinely minimal                                        : %d" % nonviol)
print("\nexamples (itemset, support, equal-support proper subset):")
for its, s, sub in examples:
    print("   %-28s sup=%-6d subset %s has the same support"
          % (" ".join(its), s, " ".join(sub)))

# sanity: are Borgelt's sets a strict subset of Talky-G's?
print("\nBorgelt sets missing from Talky-G: %d" % len(bo - tg))
