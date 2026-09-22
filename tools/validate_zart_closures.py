"""Does Zart emit correct generator -> closure pairs?

Why this exists. Asked for exact association rules, the recommender found one
eligible implementation in the capability base -- FGC-Stream, a Windows-only
binary the repository cannot redistribute -- and so, on Linux, none it could
run. Zart plausibly fills that gap: SPMF documents it as producing closed
itemsets together with their generators, and its report prints exactly that.
But the audit only ever validated Zart's GENERATORS, so the capability base
records it as ``minimal_generator`` and nothing more. Crediting it with
``generator_closure_pairs`` on the strength of its documentation would repeat
the error this repository exists to measure -- HUCI-Miner-Generators is also
documented as producing generators, and returns 0 of 2002.

So it is measured. For each configuration, against the vertical bitset oracle
of ``validate_remaining.py``:

  closed      every reported closure C satisfies cl(C) == C
  support     the #SUP printed for C equals its true support
  subset      every generator G of C satisfies G <= C
  class       cl(G) == C -- the generator really belongs to that class. This
              is stronger than the support equality the FGC-Stream audit
              checks: two different classes can share a support value.
  minimal     every non-empty G is support-minimal
  complete    the union of all reported generators equals DefMe's generator
              set, DefMe being the validated reference

Completeness has to respect a convention difference measured by the audit:
DefMe keeps itemsets whose support equals floor(sigma*|D|), Zart requires
ceil(sigma*|D|). The two differ only when sigma*|D| is not an integer, and then
only by DefMe's generators whose support is exactly the floor. Those are removed
from the reference using the oracle's own support, so the comparison is exact at
any sigma rather than only at thresholds that happen to be integral.

If closed, class and complete all hold, every frequent closed itemset appears
with its complete generator list: each closed set has at least one generator,
so the closures of a complete generator set are the complete closed sets.

    python tools/validate_zart_closures.py mushroom 0.3
    python tools/validate_zart_closures.py --all
"""
import math
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))
from validate_remaining import ItemsetOracle, load_plain_db  # noqa: E402

OUT = _ROOT / "results" / "valzart"


class FastOracle(ItemsetOracle):
    """The same oracle with a closure that scales to connect and pumsb.

    ``ItemsetOracle.closure`` intersects the item sets of every transaction
    containing X. On connect at sigma = 0.9 that is some 60,000 Python set
    intersections per generator, and the first run of this audit spent over ten
    minutes on one configuration. The closure has an equivalent form over the
    bitmasks the oracle already holds:

        cl(X) = { i : cover(X) is a subset of cover(i) }
              = { i : bits[i] & mask(X) == mask(X) }

    one big-integer AND per item. Being a rewrite of the oracle, it is not
    trusted on that argument: ``crosscheck`` compares it with the original on
    every closure of a real configuration before any audit runs, and the audit
    refuses to start if a single one differs.
    """

    def closure(self, items):
        m = self.mask(items)
        if m == 0:
            return frozenset(items)
        return frozenset(i for i, b in self.bits.items() if (b & m) == m)


def crosscheck(dataset="mushroom", sigma=0.3):
    """Fast closure == original closure on every class of a real run."""
    db = _ROOT / "datasets" / "raw" / ("%s.txt" % dataset)
    txs = load_plain_db(str(db))
    slow, fast = ItemsetOracle(txs), FastOracle(txs)
    OUT.mkdir(parents=True, exist_ok=True)
    z_out = OUT / "crosscheck_zart.txt"
    run_spmf("Zart", db, z_out, sigma)
    checked = mismatched = 0
    for c, _s, gens in parse_zart(z_out):
        for x in [c] + list(gens):
            checked += 1
            if slow.closure(x) != fast.closure(x):
                mismatched += 1
    z_out.unlink()
    return checked, mismatched

#: Configurations chosen to be feasible for Zart, which has the lowest
#: completion rate of the transactional family (69.0%), and to include both a
#: threshold where floor and ceil differ and one where they coincide.
CONFIGS = [
    ("mushroom", 0.5), ("mushroom", 0.3), ("mushroom", 0.2),
    ("chess", 0.9), ("chess", 0.8),
    ("connect", 0.95), ("connect", 0.9),
    ("pumsb", 0.95),
    ("t10i4d100k", 0.02),
]


def run_spmf(algo, db, out, sigma, timeout=1800):
    subprocess.run(["java", "-jar", str(_ROOT / "spmf" / "spmf.jar"), "run", algo,
                    str(db), str(out), str(sigma)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=False, timeout=timeout)


def _items(tokens):
    """A parsed itemset; SPMF prints the empty generator as EMPTYSET."""
    toks = [t for t in tokens if t != "EMPTYSET"]
    return frozenset(toks)


def parse_zart(path):
    """[(closure, printed support, [generators])] from Zart's first section."""
    classes = []
    state, closure, sup, gens = None, None, None, []
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if line.startswith("======="):
                if "frequent itemsets" in line:
                    break                     # second section: not pairs
                continue
            if line.startswith("CLOSED"):
                if closure is not None:
                    classes.append((closure, sup, gens))
                state, closure, sup, gens = "closed", None, None, []
                continue
            if line.startswith("GENERATOR"):
                state = "gens"
                continue
            if not line:
                continue
            if state == "closed":
                head, _, tail = line.partition("#SUP:")
                closure = _items(head.split())
                sup = int(tail.strip())
            elif state == "gens":
                gens.append(_items(line.split()))
    if closure is not None:
        classes.append((closure, sup, gens))
    return classes


def parse_generators(path):
    out = set()
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            if line:
                out.add(_items(line.split("#")[0].split()))
    return out


def audit(dataset, sigma):
    db = _ROOT / "datasets" / "raw" / ("%s.txt" % dataset)
    txs = load_plain_db(str(db))
    orc = FastOracle(txs)
    n = orc.n
    t = sigma * n
    ceil_t, floor_t = int(math.ceil(t)), int(math.floor(t))

    OUT.mkdir(parents=True, exist_ok=True)
    z_out = OUT / ("zart_%s_%s.txt" % (dataset, sigma))
    d_out = OUT / ("defme_%s_%s.txt" % (dataset, sigma))
    t0 = time.time()
    run_spmf("Zart", db, z_out, sigma)
    run_spmf("DefMe", db, d_out, sigma)
    classes = parse_zart(z_out)
    reference = parse_generators(d_out)
    # Align DefMe's floor convention to Zart's ceil convention.
    if ceil_t != floor_t:
        reference = {g for g in reference if orc.support(g) >= ceil_t}

    bad = {"closed": 0, "support": 0, "subset": 0, "class": 0, "minimal": 0}
    zart_gens = set()
    n_gens = 0
    for c, s, gens in classes:
        if orc.closure(c) != c:
            bad["closed"] += 1
        if orc.support(c) != s:
            bad["support"] += 1
        for g in gens:
            n_gens += 1
            zart_gens.add(g)
            if not g <= c:
                bad["subset"] += 1
            if orc.closure(g) != c:
                bad["class"] += 1
            if g and not orc.is_minimal(set(g)):
                bad["minimal"] += 1
    missing = reference - zart_gens
    extra = zart_gens - reference
    ok = all(v == 0 for v in bad.values()) and not missing and not extra and classes
    for p in (z_out, d_out):
        try:
            p.unlink()
        except OSError:
            pass
    return {"dataset": dataset, "sigma": sigma, "n": n, "classes": len(classes),
            "generators": n_gens, "bad": bad, "missing": len(missing),
            "extra": len(extra), "boundary_differs": ceil_t != floor_t,
            "ok": bool(ok), "secs": time.time() - t0}


def main(argv):
    configs = CONFIGS if (not argv or argv[0] == "--all") else [(argv[0], float(argv[1]))]
    checked, bad = crosscheck()
    print("fast closure vs original oracle: %d closures compared, %d differ%s"
          % (checked, bad, "" if bad else "  -> using the fast closure"))
    if bad:
        print("REFUSING to audit with a closure that disagrees with the oracle.")
        return 1
    print()
    print("%-11s %6s %8s %8s  %-7s %-7s %-6s %-5s %-7s %8s %6s  %s"
          % ("dataset", "sigma", "classes", "gens", "closed", "support", "subset",
             "class", "minimal", "missing", "extra", "verdict"))
    print("-" * 104)
    results = []
    for ds, sg in configs:
        try:
            r = audit(ds, sg)
        except subprocess.TimeoutExpired:
            print("%-11s %6s  timed out" % (ds, sg))
            continue
        results.append(r)
        b = r["bad"]
        print("%-11s %6s %8d %8d  %-7d %-7d %-6d %-5d %-7d %8d %6d  %s%s"
              % (ds, sg, r["classes"], r["generators"], b["closed"], b["support"],
                 b["subset"], b["class"], b["minimal"], r["missing"], r["extra"],
                 "PASS" if r["ok"] else "FAIL",
                 "  (floor != ceil)" if r["boundary_differs"] else ""))
    if results:
        n_ok = sum(r["ok"] for r in results)
        print()
        print("%d of %d configurations pass every check (%d classes, %d generators)"
              % (n_ok, len(results), sum(r["classes"] for r in results),
                 sum(r["generators"] for r in results)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
