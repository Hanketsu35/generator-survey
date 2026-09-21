"""Arima (AprioriRare) ciktisini BAGIMSIZ bir maksimum-destek oracle'i ile dogrular.

Bu, denetimdeki son bosluktu: calistirilan diger her implementasyon bir
oracle'a karsi kontrol edilmisti, Arima edilmemisti.  Arima'nin hedefi
digerlerinden farkli oldugu icin islemsel jeneratör oracle'i dogrudan
uygulanamaz -- ayri bir olcut gerekir.

Olcut (Szathmary vd. 2007, "Towards Rare Itemset Mining"):
    X bir MINIMAL NADIR KUME (mRI) dir  <=>
        (i)  X nadirdir            : supp(X) <  abs_esik
        (ii) her OZ ALT KUMESI sik : supp(Y) >= abs_esik,  her Y subset X

Destek anti-monoton oldugundan (ii) icin yalnizca BIREBIR alt kumeleri
(tek oge silinmis, |X|-1 boyutlu) kontrol etmek YETERLIDIR: |Y| < |X|-1 olan
her Y, bir birebir alt kume Z'nin altkumesidir, dolayisiyla
supp(Y) >= supp(Z) >= abs_esik.  Ayni argüman islemsel ve sirali oracle'larda
da kullanildi -- 2^|X| yerine |X| sorgu.

TAMLIK (completeness) de kontrol edilir, yalnizca saglamlik degil.  Her mRI'nin
tum birebir alt kumeleri sik oldugundan, her mRI  F + {i}  bicimindedir
(F sik).  Bu yuzden aday kume:
        {tek ogeler}  ∪  {F ∪ {i} : F sik, i ∉ F}
ve GERCEK mRI kumesi bu adaylardan olcutu saglayanlardir.  Sik kumeler
Borgelt'in fpgrowth'u ile MUTLAK esikte (-s-<n>) bir alt esik kullanilarak
uretilir, boylece sonuc kendi oracle'imizin sik kumelerinin USTKUMESI olur;
sik/nadir karari her zaman oracle'a gore verilir, Borgelt'in sinir
konvansiyonuna gore degil.

Kullanim:
    python tools/validate_rare.py mushroom 0.3
    python tools/validate_rare.py retail 0.1 --no-completeness
"""
import argparse
import math
import os
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)

SPMF = "spmf/spmf.jar"
FPGROWTH = "external_algos/borgelt/fpgrowth.exe"
TMP = Path("results/rareval")

#: |sik kumeler| x |ogeler| bu degeri asarsa tamlik kontrolu atlanir.
CANDIDATE_CAP = 8_000_000


class RareOracle:
    """Dikey bitset destek oracle'i -- test edilen hicbir madenciye dayanmaz."""

    def __init__(self, transactions):
        self.n = len(transactions)
        # `bits[it] |= 1 << i` in a loop allocates a fresh n-bit integer on every
        # set bit, so building the masks that way is O(n^2) and does not finish
        # on the larger datasets (accidents has 340k transactions).  Collect the
        # transaction ids first and pack each mask once through a bytearray.
        tids = {}
        for i, tx in enumerate(transactions):
            for it in tx:
                tids.setdefault(it, []).append(i)
        nbytes = (self.n + 7) // 8
        self.bits = {}
        for it, ids in tids.items():
            ba = bytearray(nbytes)
            for t in ids:
                ba[t >> 3] |= 1 << (t & 7)
            self.bits[it] = int.from_bytes(bytes(ba), "little")
        self.items = sorted(self.bits)
        self._cache = {}

    def support(self, items):
        key = frozenset(items)
        if key in self._cache:
            return self._cache[key]
        m = None
        for it in key:
            b = self.bits.get(it, 0)
            m = b if m is None else (m & b)
        s = self.n if m is None else bin(m).count("1")
        self._cache[key] = s
        return s

    def immediate_subsets(self, items):
        for x in items:
            yield frozenset(items) - {x}

    def is_minimal_rare(self, items, abs_thr):
        """(rare?, all immediate subsets frequent?)"""
        rare = self.support(items) < abs_thr
        allfreq = all(self.support(y) >= abs_thr
                      for y in self.immediate_subsets(items))
        return rare, allfreq


def load_db(path):
    txs = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        t = line.split()
        if t:
            txs.append(set(t))
    return txs


def parse_spmf(path):
    """SPMF satirlari: 'i1 i2 ... #SUP: n'."""
    out = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        head = line.split("#SUP:")[0].split()
        if head:
            out.append(frozenset(head))
    return out


def run_arima(db, out, thr):
    subprocess.run(["java", "-jar", SPMF, "run", "AprioriRare", db, out, str(thr)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return parse_spmf(out)


def borgelt_frequent(db, abs_thr, out):
    """Mutlak esikte tum sik kumeler.  abs_thr-1 kullanilir: sonuc bizim
    esigimizdeki sik kumelerin USTKUMESI olsun, sinir farki bizi yanlis
    negatife dusurmesin."""
    exe = os.path.abspath(FPGROWTH)
    if not os.path.exists(exe):
        return None
    lo = max(int(abs_thr) - 1, 1)
    subprocess.run([exe, "-ts", "-s-%d" % lo, os.path.abspath(db),
                    os.path.abspath(out)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    # Borgelt exits 15 and writes NO output file when no item is frequent.
    # That is a legitimate result (every singleton is then rare), not an error.
    if not os.path.exists(out):
        return []
    sets = []
    for line in open(out, encoding="utf-8", errors="ignore"):
        head = line.split("(")[0].split()
        sets.append(frozenset(head))
    return sets


def infer_threshold(orc, pats, thr):
    """Mutlak esik konvansiyonu icin DENEYSEL kanit toplar.

    sigma*|D| nadiren tamsayidir; implementasyonlar floor/ceil arasinda
    ayrilir.  Onemli nokta: cikti cogu zaman iki adayi da AYIRT ETMEZ -- sinira
    tam oturan bir kume yoksa her ikisi de sifir ihlal verir.  Bu durumda
    konvansiyon 'belirlendi' diye raporlanamaz; iki aday da dondurulur ve
    dogrulama her ikisi altinda ayri ayri yurutulur.
    """
    raw = thr * orc.n
    cands = sorted({int(math.floor(raw)), int(math.ceil(raw))})
    viable = []
    for abs_thr in cands:
        bad = sum(1 for p in pats if not all(orc.is_minimal_rare(p, abs_thr)))
        viable.append((abs_thr, bad))
    best = min(b for _, b in viable)
    consistent = [a for a, b in viable if b == best]
    return consistent, viable, raw


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("threshold", type=float)
    ap.add_argument("--no-completeness", action="store_true")
    ap.add_argument("--cap", type=int, default=CANDIDATE_CAP)
    args = ap.parse_args()

    db = "datasets/raw/%s.txt" % args.dataset
    if not os.path.exists(db):
        print("no such dataset: %s" % db)
        return 1
    TMP.mkdir(parents=True, exist_ok=True)

    txs = load_db(db)
    orc = RareOracle(txs)
    out = str(TMP / ("Arima_%s_%s.txt" % (args.dataset, args.threshold)))
    pats = [p for p in run_arima(db, out, args.threshold) if p]

    print("database : %s (%d transactions, %d distinct items)"
          % (args.dataset, orc.n, len(orc.items)))
    print("maxsup   : %g" % args.threshold)
    if not pats:
        print("Arima returned no patterns.")
        return 0

    consistent, viable, raw = infer_threshold(orc, pats, args.threshold)
    sizes = {}
    for q in pats:
        sizes[len(q)] = sizes.get(len(q), 0) + 1
    print("sigma*|D| = %g   rounding candidates: %s"
          % (raw, ", ".join("%d (%d soundness violations)" % v for v in viable)))
    if len(consistent) > 1:
        print("NOTE: the output does not DISTINGUISH the two conventions -- no")
        print("      returned itemset sits on the boundary. The audit below is")
        print("      therefore run under BOTH, and only a verdict that holds")
        print("      under both is reported as established.")
    print("Arima returned %d itemsets, sizes %s" % (len(pats), dict(sorted(sizes.items()))))

    verdicts = []
    for abs_thr in consistent:
        print("")
        print("-" * 70)
        print("absolute threshold = %d  (frequent iff support >= %d)" % (abs_thr, abs_thr))
        print("-" * 70)
        verdicts.append(audit(orc, pats, abs_thr, db, args))

    print("")
    if all(v == "exact" for v in verdicts):
        print("OVERALL: sound and complete -- Arima's output is EXACTLY the minimal")
        print("rare itemset family%s."
              % (" under both rounding conventions" if len(consistent) > 1 else ""))
    elif all(v in ("exact", "sound") for v in verdicts):
        print("OVERALL: sound on every returned itemset; completeness not established.")
    else:
        print("OVERALL: VIOLATIONS FOUND -- see above.")
    return 0


def audit(orc, pats, abs_thr, db, args):
    """Returns 'exact' | 'sound' | 'violation' for one absolute threshold."""
    not_rare, not_minimal = [], []
    for q in pats:
        rare, allfreq = orc.is_minimal_rare(q, abs_thr)
        if not rare:
            not_rare.append(q)
        if not allfreq:
            not_minimal.append(q)
    print("SOUNDNESS  (every returned itemset must be a minimal rare itemset)")
    print("  rare, i.e. support < %-8d      : %d / %d %s"
          % (abs_thr, len(pats) - len(not_rare), len(pats),
             "(ALL)" if not not_rare else "<-- VIOLATIONS"))
    print("  all immediate subsets frequent     : %d / %d %s"
          % (len(pats) - len(not_minimal), len(pats),
             "(ALL)" if not not_minimal else "<-- VIOLATIONS"))
    for q in (not_rare + not_minimal)[:3]:
        print("     example: {%s} supp=%d" % (" ".join(sorted(q)), orc.support(q)))
    if not_rare or not_minimal:
        return "violation"

    if args.no_completeness:
        print("COMPLETENESS: skipped (--no-completeness)")
        return "sound"

    freq_out = str(TMP / ("FI_%s_%s_%d.txt" % (args.dataset, args.threshold, abs_thr)))
    freq = borgelt_frequent(db, abs_thr, freq_out)
    if freq is None:
        print("COMPLETENESS: skipped (Borgelt fpgrowth binary not present)")
        return "sound"

    # Test the cap on the RAW count first: re-checking 600k supports only to
    # then skip the pass wastes minutes on the dense low-threshold cases.
    n_cand = (len(freq) + 1) * len(orc.items)
    print("COMPLETENESS  (negative border: every mRI is F + {i} for some frequent F)")
    print("  frequent itemsets from the native miner   : %d" % len(freq))
    print("  candidate extensions to test              : ~%d" % n_cand)
    if n_cand > args.cap:
        print("  SKIPPED: exceeds the %d candidate cap. Soundness above still" % args.cap)
        print("  holds on all %d returned itemsets; completeness is unverified." % len(pats))
        return "sound"

    freq = [f for f in freq if f and orc.support(f) >= abs_thr]
    print("  frequent at the oracle threshold          : %d" % len(freq))

    truth = set()
    for it in orc.items:
        one = frozenset([it])
        if orc.support(one) < abs_thr:
            truth.add(one)
    seen = set()
    for f in freq:
        for it in orc.items:
            if it in f:
                continue
            cand = f | {it}
            if cand in seen:
                continue
            seen.add(cand)
            rare, allfreq = orc.is_minimal_rare(cand, abs_thr)
            if rare and allfreq:
                truth.add(cand)

    got = set(pats)
    missing, extra = truth - got, got - truth
    print("  true minimal rare itemsets (oracle)       : %d" % len(truth))
    print("  returned by Arima                         : %d" % len(got))
    print("  MISSING from Arima's output               : %d %s"
          % (len(missing), "" if missing else "(none)"))
    print("  returned but NOT minimal rare             : %d %s"
          % (len(extra), "" if extra else "(none)"))
    for q in list(missing)[:3]:
        print("     missing: {%s} supp=%d" % (" ".join(sorted(q)), orc.support(q)))
    for q in list(extra)[:3]:
        print("     extra  : {%s} supp=%d" % (" ".join(sorted(q)), orc.support(q)))
    return "exact" if not missing and not extra else "violation"


if __name__ == "__main__":
    sys.exit(main())
