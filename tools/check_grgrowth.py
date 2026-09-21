"""Gr-growth ciktisini bagimsiz olarak dogrular.

Gozlem: mushroom/0.2'de Gr-growth 683 kume dondururken DefMe/Pascal/Borgelt
1703-1704 bildiriyor ve Gr-growth ciktisi 4-boyutlu kumelerde bitiyor.
Bu, ya (a) sayim fonksiyonunun hatali olmasi, ya (b) Gr-growth'un ciktisini
kirpmasi anlamina gelir.  Ikisinin ayrimi makale icin kritik: Gr-growth
"en hizli" olarak sunuluyor, ama eksik cikti veriyorsa karsilastirma gecersiz.

Test: her Gr-growth kumesi gercekten minimal jeneratör mu (SAGLAMLIK) ve
referans kumesinin tamami uretiliyor mu (TAMLIK)?  Destekler dikey bitset
ile bagimsiz hesaplanir.
"""
import sys
from pathlib import Path

ROOT = Path(r"D:\Doktora\Dersler\CENG643\TermProject")


def build_bitsets(path):
    items, n = {}, 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            toks = line.split()
            if not toks:
                continue
            for t in toks:
                items[t] = items.get(t, 0) | (1 << n)
            n += 1
    return items, n


def support(itemset, items):
    bs = None
    for it in itemset:
        b = items.get(it, 0)
        bs = b if bs is None else bs & b
        if bs == 0:
            return 0
    return bin(bs).count("1") if bs is not None else 0


def parse_grgrowth(path):
    """format: <size> <item>... <support>"""
    out = set()
    for line in open(path, encoding="utf-8", errors="ignore"):
        t = line.split()
        if not t:
            continue
        k = int(t[0])
        out.add(frozenset(t[1:1 + k]))
    return out


def parse_spmf(path, only_gen=False):
    out = set()
    for line in open(path, encoding="utf-8", errors="ignore"):
        if "#SUP:" not in line:
            continue
        if only_gen and "IS_GENERATOR: true" not in line:
            continue
        it = line.split("#SUP:")[0].strip()
        out.add(frozenset(it.split()) if it else frozenset())
    return out


def main():
    data = ROOT / "datasets/raw/mushroom.txt"
    gr = parse_grgrowth(ROOT / "results/raw/out_Gr_growth_mushroom_0_2.txt")
    ref_path = ROOT / "results/raw/out_DefMe_mushroom_0_2.txt"
    if not ref_path.exists():
        print("reference output missing: %s" % ref_path); return
    ref = parse_spmf(ref_path)

    items, n = build_bitsets(data)
    print("transactions: %d   minsup 0.2 -> abs %d" % (n, round(0.2 * n)))
    print("Gr-growth sets: %d | DefMe sets: %d" % (len(gr), len(ref)))

    gr_ne = {s for s in gr if s}
    ref_ne = {s for s in ref if s}
    print("\n(excluding the empty set)")
    print("  Gr-growth      : %d" % len(gr_ne))
    print("  DefMe          : %d" % len(ref_ne))
    print("  Gr-growth \ DefMe (spurious): %d" % len(gr_ne - ref_ne))
    print("  DefMe \ Gr-growth (MISSED)  : %d" % len(ref_ne - gr_ne))
    print("  is Gr-growth a subset of DefMe? %s" % (gr_ne <= ref_ne))

    sizes = {}
    for s in ref_ne:
        sizes[len(s)] = sizes.get(len(s), 0) + 1
    gsz = {}
    for s in gr_ne:
        gsz[len(s)] = gsz.get(len(s), 0) + 1
    print("\n  size : DefMe : Gr-growth")
    for k in sorted(sizes):
        print("   %2d  : %5d : %5d" % (k, sizes[k], gsz.get(k, 0)))

    # saglamlik: her Gr-growth kumesi gercekten minimal jeneratör mu?
    bad = 0
    for s in list(gr_ne)[:2000]:
        sup = support(s, items)
        for it in s:
            if support(s - {it}, items) == sup:
                bad += 1
                break
    print("\n  definition violations among Gr-growth sets: %d" % bad)


if __name__ == "__main__":
    main()
