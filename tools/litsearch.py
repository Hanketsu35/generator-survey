"""Systematic search for minimal-generator algorithms (Supplementary Section S3).

    python tools/litsearch.py              # the registered search
    python tools/litsearch.py --addendum   # the addendum of 2026-10-20

OpenAlex (title and abstract search), run 2026-10-05. The queries cover the
names the same object has carried: minimal generators, generators of closed
itemsets, free sets / free itemsets, key patterns / key itemsets, sequential
and utility generators, generators in graphs and streams. Every hit is kept
in results/litsearch/hits.csv for screening (results/litsearch/SCREENING.md).

The addendum adds the terms the registered queries lacked: minimal rare
itemsets are also called minimal(ly) infrequent itemsets or minimal rare
(infrequent) patterns, and a review of the survey found a rare-itemset
miner (IFP_min) published under such a name only. Its hits, minus those already in hits.csv, go to hits_addendum.csv.
"""
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "results" / "litsearch"
QUERIES = [
    '"minimal generator" itemset',
    '"minimal generators" itemsets',
    '"minimal generators" mining',
    'generators "closed itemsets"',
    'generators "closed patterns"',
    '"sequential generator"',
    '"sequential generators"',
    '"generator patterns"',
    '"free itemsets"',
    '"free sets" frequency',
    '"key patterns" mining',
    '"key itemsets"',
    '"utility" generators itemsets',
    'generators "closed graph"',
    '"generators" "data streams" closed',
    '"minimal rare itemsets"',
    '"disjunction-free"',
]
ADDENDUM = [
    '"minimal infrequent"',
    '"minimally infrequent"',
    '"minimal rare itemset"',
    '"minimal rare pattern"',
    '"minimal rare patterns"',
    '"minimal infrequent pattern"',
]


def fetch(q):
    out, cursor = [], "*"
    while cursor and len(out) < 600:
        url = ("https://api.openalex.org/works?filter=title_and_abstract.search:%s"
               "&per-page=200&cursor=%s&select=id,doi,title,publication_year,"
               "primary_location,type" % (urllib.parse.quote(q), cursor))
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
        out += d["results"]
        cursor = d["meta"].get("next_cursor")
        if not d["results"]:
            break
        time.sleep(0.3)
    return out


def main(addendum=False):
    OUT.mkdir(parents=True, exist_ok=True)
    seen = {}
    log = []
    known = set()
    if addendum:
        with open(OUT / "hits.csv", newline="") as fh:
            known = {r["id"] for r in csv.DictReader(fh)}
    for q in (ADDENDUM if addendum else QUERIES):
        res = fetch(q)
        log.append("%-40s %d" % (q, len(res)))
        for w in res:
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
            k = w["id"]
            if k in known:
                continue
            if k not in seen:
                seen[k] = {"id": k, "doi": w.get("doi") or "", "year": w.get("publication_year"),
                           "title": (w.get("title") or "").replace("\n", " "), "venue": src,
                           "type": w.get("type"), "queries": q}
            else:
                seen[k]["queries"] += " | " + q
    name = "hits_addendum.csv" if addendum else "hits.csv"
    with open(OUT / name, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["year", "title", "venue", "type", "doi", "id", "queries"])
        wr.writeheader()
        for r in sorted(seen.values(), key=lambda r: (r["year"] or 0, r["title"])):
            wr.writerow(r)
    qname = "queries_addendum.txt" if addendum else "queries.txt"
    (OUT / qname).write_text("\n".join(log) + "\nunique, not in hits.csv: %d\n" % len(seen)
                             if addendum else "\n".join(log) + "\nunique: %d\n" % len(seen))
    print("\n".join(log), "\nunique:", len(seen))


if __name__ == "__main__":
    import sys
    main(addendum="--addendum" in sys.argv[1:])
