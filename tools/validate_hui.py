"""Yuksek-fayda (high-utility) jeneratör ciktilarini BAGIMSIZ bir oracle ile dogrular.

Islemsel aile icin yapilan dogrulamanin (bkz. makale, sec:validation) yuksek-fayda
ailesine tasinmis hali.  Iki bagimsiz olcut hesaplanir:

  1) DESTEK-MINIMALLIGI  -- bir X kumesi jeneratördür ancak ve ancak hicbir oz
     alt kumesi ayni destege sahip degilse.  Destek anti-monoton oldugundan
     yalnizca |X| adet BIREBIR alt kumeyi kontrol etmek yeterlidir (islemsel
     oracle ile ayni argüman).  Destekler dikey bitset ile tam olarak hesaplanir.

  2) FAYDA  -- X'in faydasi, X'i iceren her islemde X'in ogelerinin
     (miktar x dis fayda) toplamlarinin islemler uzerindeki toplamidir.
     SPMF fayda dosyasi formati:  <ogeler> : <islem toplam faydasi> : <oge faydalari>

HUG-Miner semantigi: "high utility generator" = hem destek-minimal hem de
fayda >= esik olan kume.  Bu betik yalnizca HUG-Miner'i dogrular; GHUI-Miner
FARKLI bir hedefi (yuksek-faydali kumelerin jeneratörleri) oldugu icin ayni
olcute tabi degildir ve rapor edilmez.

Kullanim:
    python tools/validate_hui.py foodmart 100
"""
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)


def load_utility_db(path):
    """SPMF fayda dosyasini okur -> (islem listesi, oge->bitset, islem sayisi).

    Her islem: {oge: fayda} sozlugu.
    """
    txs = []
    bits = {}
    n = 0
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(":")
        if len(parts) < 3:
            continue
        items = parts[0].split()
        utils = parts[2].split()
        if len(items) != len(utils):
            continue
        tx = {}
        for it, u in zip(items, utils):
            try:
                tx[it] = tx.get(it, 0) + int(u)
            except ValueError:
                tx[it] = tx.get(it, 0)
        txs.append(tx)
        for it in tx:
            bits[it] = bits.get(it, 0) | (1 << n)
        n += 1
    return txs, bits, n


def parse_output(path):
    """SPMF cikti satirlarini ayristirir: '<ogeler> #SUP: s #UTIL: u'."""
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        head = line.split("#SUP:")[0].split()
        if head:
            out.append(frozenset(head))
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    dataset, thresh = sys.argv[1], int(sys.argv[2])

    db = "datasets/spmf_format/%s_utility_fixed.txt" % dataset
    out_file = "results/validate_hui_%s_%s.txt" % (dataset, thresh)

    import subprocess
    subprocess.run(
        ["java", "-jar", "spmf/spmf.jar", "run", "HUG-Miner", db, out_file, str(thresh)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )

    txs, bits, n = load_utility_db(db)
    patterns = parse_output(out_file)
    print("database      : %s  (%d transactions, %d items)" % (dataset, n, len(bits)))
    print("min_utility   : %d" % thresh)
    print("patterns      : %d" % len(patterns))

    def support_mask(items):
        m = None
        for it in items:
            b = bits.get(it, 0)
            m = b if m is None else (m & b)
        return m if m is not None else (1 << n) - 1

    def popcount(m):
        return bin(m).count("1")

    def utility(items):
        """X'i iceren islemlerde X'in ogelerinin fayda toplami."""
        m = support_mask(items)
        total = 0
        idx = 0
        mm = m
        while mm:
            if mm & 1:
                tx = txs[idx]
                total += sum(tx.get(it, 0) for it in items)
            mm >>= 1
            idx += 1
        return total

    not_minimal = []
    below_thresh = []
    for g in patterns:
        if not g:
            continue
        s = popcount(support_mask(g))
        for x in g:                       # birebir alt kumeler yeterli
            if popcount(support_mask(g - {x})) == s:
                not_minimal.append(g)
                break
        if utility(g) < thresh:
            below_thresh.append(g)

    print("")
    print("VIOLATIONS")
    print("  not support-minimal : %d" % len(not_minimal))
    print("  utility < threshold : %d" % len(below_thresh))
    if not not_minimal and not below_thresh:
        print("  -> SOUND: every returned pattern is a minimal generator")
        print("            and meets the utility threshold.")
    else:
        for g in (not_minimal[:3] + below_thresh[:3]):
            print("   example:", sorted(g, key=lambda z: int(z) if z.isdigit() else 0),
                  "supp", popcount(support_mask(g)), "util", utility(g))
    return 0


if __name__ == "__main__":
    sys.exit(main())
