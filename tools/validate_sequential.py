"""Sirali (sequential) jeneratör ciktilarini BAGIMSIZ bir oracle ile dogrular.

Islemsel aile icin yapilan dogrulamanin sirali aileye tasinmis hali.  Amac,
VGEN'in FEAT/FSGP'den DAHA AZ desen dondurmesi bulgusunu karara baglamak:
    - FEAT/FSGP fazla mi uretiyor (jeneratör olmayanlari da yaziyor), yoksa
    - VGEN eksik mi birakiyor (gercek jeneratörleri atliyor)?

Olcut (FEAT/FSGP/VGEN makalelerinin verdigi tanim):
    Bir S sirali deseni JENERATÖRDUR  <=>  hicbir OZ ALT-DIZISI S ile ayni
    destege sahip degildir.

Destek anti-monoton oldugundan (bir ogeyi silmek destegi azaltamaz) ve her oz
alt-dizi tek tek oge silmeleriyle elde edilebildiginden, yalnizca BIREBIR
alt-dizileri (tek bir oge silinmis hali) kontrol etmek YETERLIDIR -- islemsel
oracle ile ayni argüman.

Destekler, alt-dizi icerme testi ile dogrudan veri tabanindan hesaplanir;
oracle test edilen hicbir madenciye dayanmaz.

Kullanim:
    python tools/validate_sequential.py sign 0.04
"""
import os
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)


def parse_db(path):
    """SPMF dizi veri tabanini okur -> [[frozenset, ...], ...]."""
    seqs = []
    for line in open(path, encoding="utf-8"):
        toks = line.split()
        if not toks:
            continue
        seq, cur = [], []
        for t in toks:
            if t == "-1":
                if cur:
                    seq.append(frozenset(cur))
                cur = []
            elif t == "-2":
                break
            else:
                cur.append(t)
        if cur:
            seq.append(frozenset(cur))
        if seq:
            seqs.append(seq)
    return seqs


def parse_patterns(path):
    """SPMF cikti satirlarini ayristirir -> [(itemset, ...), ...] (tuple of frozenset)."""
    out = []
    for line in open(path, encoding="utf-8"):
        head = line.split("#SUP:")[0].split()
        pat, cur = [], []
        for t in head:
            if t == "-1":
                if cur:
                    pat.append(frozenset(cur))
                cur = []
            else:
                cur.append(t)
        if cur:
            pat.append(frozenset(cur))
        out.append(tuple(pat))
    return out


def contains(seq, pat):
    """pat, seq'in bir alt-dizisi mi?  Acgozlu eslestirme dogrudur:
    her desen ogesini mumkun olan EN ERKEN konumda eslestirmek optimaldir."""
    i = 0
    for itemset in seq:
        if pat[i] <= itemset:
            i += 1
            if i == len(pat):
                return True
    return False


class Oracle:
    def __init__(self, seqs):
        self.seqs = seqs
        self.n = len(seqs)
        # oge -> o ogeyi iceren dizilerin bitmask'i (aday elemeye yarar)
        self.bits = {}
        for idx, seq in enumerate(seqs):
            for itemset in seq:
                for it in itemset:
                    self.bits[it] = self.bits.get(it, 0) | (1 << idx)
        self.cache = {}

    def support(self, pat):
        if not pat:
            return self.n
        key = pat
        if key in self.cache:
            return self.cache[key]
        mask = None
        for itemset in pat:
            for it in itemset:
                b = self.bits.get(it, 0)
                mask = b if mask is None else (mask & b)
        cnt = 0
        idx = 0
        m = mask or 0
        while m:
            if m & 1:
                if contains(self.seqs[idx], pat):
                    cnt += 1
            m >>= 1
            idx += 1
        self.cache[key] = cnt
        return cnt

    def immediate_subsequences(self, pat):
        """Tek bir oge silinerek elde edilen tum birebir alt-diziler."""
        seen = set()
        for i, itemset in enumerate(pat):
            for it in itemset:
                rest = itemset - {it}
                if rest:
                    sub = pat[:i] + (rest,) + pat[i + 1:]
                else:
                    sub = pat[:i] + pat[i + 1:]
                if sub not in seen:
                    seen.add(sub)
                    yield sub

    def is_generator(self, pat):
        if not pat:
            return True
        s = self.support(pat)
        for sub in self.immediate_subsequences(pat):
            if self.support(sub) == s:
                return False
        return True


def run(algo, db, out, thresh):
    subprocess.run(
        ["java", "-jar", "spmf/spmf.jar", "run", algo, db, out, str(thresh)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    return parse_patterns(out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    dataset, thresh = sys.argv[1], sys.argv[2]
    db = "datasets/raw/%s.txt" % dataset
    tmp = Path("results/seqval")
    tmp.mkdir(parents=True, exist_ok=True)

    pats = {}
    for algo in ("FEAT", "FSGP", "VGEN"):
        pats[algo] = set(run(algo, db, str(tmp / ("%s_%s_%s.txt" % (algo, dataset, thresh))), thresh))

    seqs = parse_db(db)
    orc = Oracle(seqs)
    print("database : %s (%d sequences)   minsup=%s" % (dataset, len(seqs), thresh))
    for a in ("FEAT", "FSGP", "VGEN"):
        print("  %-5s returned %d patterns" % (a, len(pats[a])))

    feat, vgen = pats["FEAT"], pats["VGEN"]
    print("  FEAT == FSGP as sets: %s" % (feat == pats["FSGP"]))

    only_feat = feat - vgen
    only_vgen = vgen - feat
    print("")
    print("SET DIFFERENCE")
    print("  in FEAT/FSGP but not VGEN : %d" % len(only_feat))
    print("  in VGEN but not FEAT/FSGP : %d" % len(only_vgen))

    def audit(name, patterns):
        bad = [p for p in patterns if p and not orc.is_generator(p)]
        print("  %-28s : %d of %d FAIL the generator criterion"
              % (name, len(bad), len(patterns)))
        return bad

    print("")
    print("ORACLE VERDICT")
    bad_feat = audit("all FEAT/FSGP patterns", feat)
    bad_vgen = audit("all VGEN patterns", vgen)
    bad_only_feat = audit("FEAT-only patterns", only_feat)
    if only_vgen:
        audit("VGEN-only patterns", only_vgen)

    print("")
    if only_feat and not bad_only_feat:
        print("  => VGEN is INCOMPLETE: every one of the %d patterns it omits" % len(only_feat))
        print("     is a genuine sequential generator.")
    elif bad_only_feat and len(bad_only_feat) == len(only_feat):
        print("  => FEAT/FSGP OVER-PRODUCE: all %d extra patterns fail the criterion."
              % len(only_feat))
    elif only_feat:
        print("  => MIXED: %d of %d FEAT-only patterns are genuine generators."
              % (len(only_feat) - len(bad_only_feat), len(only_feat)))
    for p in list(only_feat)[:3]:
        print("     example omitted by VGEN:",
              " -1 ".join(" ".join(sorted(s)) for s in p),
              "supp", orc.support(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
