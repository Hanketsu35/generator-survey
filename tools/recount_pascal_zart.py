"""Recount generator cardinality for Pascal and Zart from retained SPMF outputs.

Pascal : SPMF emits every frequent itemset tagged '#IS_GENERATOR: true|false'.
         The generator count is the number of 'true' lines.
Zart   : SPMF emits a human-readable report of closed itemsets and, under each,
         its generators. Generators are the lines following a 'GENERATOR(S) :'
         marker, up to the next ' CLOSED :' marker.
"""
import os, re, glob, csv, json

RAW = r"D:\Doktora\Dersler\CENG643\TermProject\results\raw"


def count_pascal(path):
    n = 0
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'IS_GENERATOR: true' in line:
                n += 1
    return n


def count_zart(path):
    n = 0
    in_gen = False
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith('CLOSED'):
                in_gen = False
                continue
            if s.startswith('GENERATOR(S)'):
                in_gen = True
                continue
            if s.startswith('====='):
                in_gen = False
                continue
            if in_gen:
                n += 1
    return n


def raw_lines(path):
    n = 0
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.strip():
                n += 1
    return n


rows = []
for algo, fn in (("Pascal", count_pascal), ("Zart", count_zart)):
    for p in sorted(glob.glob(os.path.join(RAW, "out_%s_*.txt" % algo))):
        base = os.path.basename(p)[len("out_%s_" % algo):-4]
        # dataset_param  e.g. chess_0_2
        m = re.match(r"(.+)_(\d+_\d+)$", base)
        if not m:
            continue
        ds, pv = m.group(1), m.group(2).replace('_', '.')
        old = raw_lines(p)
        new = fn(p)
        rows.append((algo, ds, pv, old, new, os.path.getsize(p)))

print("%-7s %-12s %-6s %>12s %>12s %8s" .replace('>','')
      % ("algo", "dataset", "minsup", "recorded", "corrected", "ratio"))
for algo, ds, pv, old, new, sz in rows:
    r = ("%.2fx" % (old / new)) if new else "-"
    print("%-7s %-12s %-6s %12d %12d %8s" % (algo, ds, pv, old, new, r))

with open(os.environ['CLAUDE_JOB_DIR'] + r"\tmp\recount.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["algorithm", "dataset", "param_value", "recorded", "corrected"])
    for algo, ds, pv, old, new, sz in rows:
        w.writerow([algo, ds, pv, old, new])
print("\nwrote recount.csv (%d rows)" % len(rows))
