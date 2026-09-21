"""Kalan uc implementasyonu dogrular: GHUI-Miner, HUCI-Miner-Gen., FGC-Stream.

Bu ucunun hedefi HUG-Miner'inkinden farkli oldugu icin tek bir olcut yeterli
degil.  Semantigi VARSAYMAK yerine, her cikti icin birden fazla aday olcut
olculur ve hangisinin ciktiyla BIREBIR ortustugu raporlanir.  Boylece
implementasyonun gercekte hangi aileyi urettigi deneysel olarak belirlenir.

Olculen olcutler (X bir kume, theta esik):
    minimal      : X destek-minimal bir jeneratör mu (dikey bitset oracle)
    u(X)>=theta  : X'in kendi faydasi esigi asiyor mu
    u(cl(X))>=t  : X'in KAPANISI'nin faydasi esigi asiyor mu
                   (bir destek-denklik sinifinda faydalar kume buyudukce
                    artar -- destekleyen islemler ayni, ogeler eklenir --
                    bu yuzden sinifta bir HUI varsa kapanis da HUI'dir)

FGC-Stream icin ayri bir yol izlenir: harness onu pencere boyutu = |D| ile
calistirdigi icin (src/harness.py, exe_type 'fgcstream') kayan pencere tum veri
tabanini kapsar ve cikti siradan frequent minimal jeneratörlere denk gelmelidir.
Dolayisiyla ISLEMSEL oracle dogrudan uygulanabilir.

Kullanim:
    python tools/validate_remaining.py hui  foodmart 20
    python tools/validate_remaining.py fgc  mushroom 0.4
"""
import os
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)


# --------------------------------------------------------------------------
# Ortak: dikey bitset destek oracle'i
# --------------------------------------------------------------------------
class ItemsetOracle:
    def __init__(self, transactions):
        self.txs = transactions          # [{item: utility}] veya [set]
        self.n = len(transactions)
        self.bits = {}
        for i, tx in enumerate(transactions):
            for it in tx:
                self.bits[it] = self.bits.get(it, 0) | (1 << i)

    def mask(self, items):
        m = None
        for it in items:
            b = self.bits.get(it, 0)
            m = b if m is None else (m & b)
        return (1 << self.n) - 1 if m is None else m

    def support(self, items):
        return bin(self.mask(items)).count("1")

    def is_minimal(self, items):
        if not items:
            return True
        s = self.support(items)
        for x in items:
            if self.support(items - {x}) == s:
                return False
        return True

    @staticmethod
    def _set_bits(m):
        """Kurulu bitlerin indekslerini verir.

        Naif `while m: ... m >>= 1` yaklasimi her adimda n-bitlik yeni bir
        buyuk tamsayi urettigi icin cagri basina O(n^2)'dir ve buyuk
        konfigurasyonlarda (or. chess) pratikte bitmiyor.  Dusuk biti
        `m & -m` ile ayiklamak maliyeti O(popcount)'a indirir.
        """
        while m:
            b = m & -m
            yield b.bit_length() - 1
            m ^= b

    def closure(self, items):
        """X'i iceren tum islemlerin kesisimi = cl(X)."""
        m = self.mask(items)
        if m == 0:
            return frozenset(items)
        cl = None
        for idx in self._set_bits(m):
            keys = set(self.txs[idx])
            cl = keys if cl is None else (cl & keys)
            if cl is not None and not cl:
                break
        return frozenset(cl or items)

    def utility(self, items):
        total = 0
        for idx in self._set_bits(self.mask(items)):
            tx = self.txs[idx]
            total += sum(tx.get(it, 0) for it in items)
        return total


def load_utility_db(path):
    txs = []
    for line in open(path, encoding="utf-8"):
        parts = line.strip().split(":")
        if len(parts) < 3:
            continue
        items, utils = parts[0].split(), parts[2].split()
        if len(items) != len(utils):
            continue
        tx = {}
        for it, u in zip(items, utils):
            try:
                tx[it] = tx.get(it, 0) + int(u)
            except ValueError:
                pass
        txs.append(tx)
    return txs


def load_plain_db(path):
    txs = []
    for line in open(path, encoding="utf-8"):
        t = line.split()
        if t:
            txs.append({x: 0 for x in t})
    return txs


def parse_itemsets(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        head = line.split("#")[0].split()
        out.append(frozenset(head))
    return out


def run_spmf(algo, db, out, param):
    subprocess.run(["java", "-jar", "spmf/spmf.jar", "run", algo, db, out, str(param)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return parse_itemsets(out)


# --------------------------------------------------------------------------
def audit_hui(dataset, theta):
    db = "datasets/spmf_format/%s_utility_fixed.txt" % dataset
    txs = load_utility_db(db)
    orc = ItemsetOracle(txs)
    tmp = Path("results/valremain")
    tmp.mkdir(parents=True, exist_ok=True)

    print("database: %s (%d transactions)  min_utility=%d" % (dataset, orc.n, theta))
    for algo, name in (("GHUI-Miner", "GHUI_Miner"),
                       ("HUCI_Miner_Generators", "HUCI_Miner_Generators")):
        pats = [p for p in run_spmf(algo, db, str(tmp / ("%s_%s_%s.txt" % (name, dataset, theta))), theta) if p]
        if not pats:
            print("\n%-22s : no output" % algo)
            continue
        n_min = sum(1 for p in pats if orc.is_minimal(p))
        n_uself = sum(1 for p in pats if orc.utility(p) >= theta)
        n_ucl = sum(1 for p in pats if orc.utility(orc.closure(p)) >= theta)
        print("\n%-22s : %d patterns" % (algo, len(pats)))
        print("   support-minimal        : %d / %d %s"
              % (n_min, len(pats), "(ALL)" if n_min == len(pats) else "<-- violations"))
        print("   u(X)      >= threshold : %d / %d" % (n_uself, len(pats)))
        print("   u(cl(X))  >= threshold : %d / %d %s"
              % (n_ucl, len(pats), "(ALL)" if n_ucl == len(pats) else ""))


def audit_fgc(dataset, minsup):
    """FGC-Stream: pencere = |D| oldugu icin islemsel oracle dogrudan gecerli."""
    import math
    db = "datasets/raw/%s.txt" % dataset
    txs = load_plain_db(db)
    orc = ItemsetOracle(txs)
    exe = "external_algos/FGC_Stream/FGC-Stream/FGC_Stream_release.exe"
    if not Path(exe).exists():
        print("FGC-Stream binary not present at %s" % exe)
        return
    tmp = Path("results/valremain")
    tmp.mkdir(parents=True, exist_ok=True)
    out = str(tmp / ("FGC_%s_%s.txt" % (dataset, minsup)))
    abs_sup = int(math.ceil(float(minsup) * orc.n))
    # Windows'ta goreli ileri-bolu yollu exe cagrisi CreateProcess'te
    # bulunamiyor; mutlak yola cevir.
    exe_abs = os.path.abspath(exe)
    subprocess.run([exe_abs, os.path.abspath(db), str(abs_sup), "0",
                    os.path.abspath(out), str(orc.n)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    # Format: 's=<destek> fermeture : <kapanis> generateurs : <g1>  <g2>'
    # Jeneratörler CIFT bosluk ile ayrilir; her biri bosluklu bir kume.
    classes = []
    for line in open(out, encoding="utf-8", errors="ignore"):
        if "generateurs :" not in line or "fermeture :" not in line:
            continue
        sup_part, rest = line.split("fermeture :", 1)
        clo_part, gen_part = rest.split("generateurs :", 1)
        try:
            s = int(sup_part.strip().lstrip("s="))
        except ValueError:
            continue
        closure = frozenset(clo_part.split())
        gens = [frozenset(g.split()) for g in gen_part.rstrip("\n").split("  ") if g.strip()]
        if not gens:
            gens = [frozenset()]          # bos kume jeneratörü
        classes.append((s, closure, gens))

    total_gens = sum(len(g) for _, _, g in classes)
    print("database: %s (%d transactions)  minsup=%s -> abs %d"
          % (dataset, orc.n, minsup, abs_sup))
    print("FGC-Stream            : %d classes, %d generators" % (len(classes), total_gens))
    if not classes:
        return

    bad_min, bad_sup, bad_clo, below = [], [], [], []
    for s, closure, gens in classes:
        if orc.closure(closure) != closure or orc.support(closure) != s:
            bad_clo.append(closure)
        for g in gens:
            gs = orc.support(g)
            if gs != s:
                bad_sup.append(g)
            if g and not orc.is_minimal(g):
                bad_min.append(g)
            if gs < abs_sup:
                below.append((g, gs))
    print("   generators support-minimal : %d / %d %s"
          % (total_gens - len(bad_min), total_gens,
             "(ALL)" if not bad_min else "<-- VIOLATIONS"))
    print("   generator support == class : %d / %d %s"
          % (total_gens - len(bad_sup), total_gens,
             "(ALL)" if not bad_sup else "<-- mismatches"))
    print("   reported closures correct  : %d / %d %s"
          % (len(classes) - len(bad_clo), len(classes),
             "(ALL)" if not bad_clo else "<-- VIOLATIONS"))
    print("   generators below abs thr.  : %d  (boundary convention if >0)" % len(below))
    if below:
        sups = sorted({s for _, s in below})
        print("      their supports: %s   (threshold %d)" % (sups[:6], abs_sup))


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    mode, dataset, param = sys.argv[1], sys.argv[2], sys.argv[3]
    if mode == "hui":
        audit_hui(dataset, int(param))
    elif mode == "fgc":
        audit_fgc(dataset, param)
    else:
        print("mode must be 'hui' or 'fgc'")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
