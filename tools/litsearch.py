"""Systematic search for minimal-generator algorithms (gap G8, kbs/GAPS.md).

    python tools/litsearch.py

OpenAlex (title and abstract search), run 2026-10-05. The queries cover the
names the same object has carried: minimal generators, generators of closed
itemsets, free sets / free itemsets, key patterns / key itemsets, sequential
and utility generators, generators in graphs and streams. Every hit is kept
in results/litsearch/hits.csv for screening (results/litsearch/SCREENING.md).
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seen = {}
    log = []
    for q in QUERIES:
        res = fetch(q)
        log.append("%-40s %d" % (q, len(res)))
        for w in res:
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
            k = w["id"]
            if k not in seen:
                seen[k] = {"id": k, "doi": w.get("doi") or "", "year": w.get("publication_year"),
                           "title": (w.get("title") or "").replace("\n", " "), "venue": src,
                           "type": w.get("type"), "queries": q}
            else:
                seen[k]["queries"] += " | " + q
    with open(OUT / "hits.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["year", "title", "venue", "type", "doi", "id", "queries"])
        wr.writeheader()
        for r in sorted(seen.values(), key=lambda r: (r["year"] or 0, r["title"])):
            wr.writerow(r)
    (OUT / "queries.txt").write_text("\n".join(log) + "\nunique: %d\n" % len(seen))
    print("\n".join(log), "\nunique:", len(seen))


if __name__ == "__main__":
    main()
