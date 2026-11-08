"""Merge the database exports of the multi-database search and remove duplicates.

    python tools/merge_db.py               # the main query
    python tools/merge_db.py --supplement  # the supplementary query of 2026-11-09

Sources (results/litsearch/):
  hits.csv, hits_addendum.csv     OpenAlex, 2026-10-05 and 2026-10-20 (tools/litsearch.py)
  db/wos_2026-11-08.txt           Web of Science Core Collection, tab-delimited full record
  db/scopus_2026-11-09.csv        Scopus CSV export
  db/ieee_xplore_2026-11-08.csv   IEEE Xplore CSV export
  db/acm_dl_2026-11-08.json       ACM Guide to Computing Literature, read from the result pages

The OpenAlex hits carry no abstract, and the ACM records carry a title cut at
the first colon and a shortened abstract. Both are completed from OpenAlex by
id or DOI; the answers are cached in db/openalex_meta.json so that a rerun
needs no network.

Two records are the same work when they share a DOI, or when their
normalised titles are equal and they do not carry two different DOIs.
Output: db/merged.csv, one row per work, with the databases that returned it.

The supplementary query (hits_supplement.csv and the db/*_supp_* files) is
merged the same way into db/merged_supp.csv. A work that is already in
merged.csv keeps its R number; a new work gets an S number. merged.csv is not
changed, so the screening decisions in screening.csv stay attached.
"""
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

LIT = Path(__file__).resolve().parent.parent / "results" / "litsearch"
DB = LIT / "db"
CACHE = DB / "openalex_meta.json"
csv.field_size_limit(sys.maxsize)
ORDER = ["OpenAlex", "WoS", "Scopus", "IEEE", "ACM"]


def ndoi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", d)
    return d if d.startswith("10.") else ""


def ntitle(t):
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"[^a-z0-9]", "", t)


def rec(src, sid, title, year, venue, doi, abstract, typ):
    y = re.search(r"\d{4}", str(year or ""))
    return {"src": src, "sid": sid, "title": " ".join((title or "").split()),
            "year": int(y.group()) if y else None, "venue": (venue or "").strip(),
            "doi": ndoi(doi), "abstract": " ".join((abstract or "").split()),
            "type": (typ or "").strip()}


def inverted(ix):
    if not ix:
        return ""
    pos = sorted((p, w) for w, ps in ix.items() for p in ps)
    return " ".join(w for _, w in pos)


def openalex(keys, field):
    """Look up works by OpenAlex id or DOI, 50 per request; cache by key."""
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [k for k in keys if k and f"{field}:{k}" not in cache]
    for i in range(0, len(todo), 50):
        part = todo[i:i + 50]
        url = ("https://api.openalex.org/works?per-page=50&filter=%s:%s&select=id,doi,"
               "title,publication_year,abstract_inverted_index,primary_location,type"
               % (field, urllib.parse.quote("|".join(part), safe="|/:")))
        with urllib.request.urlopen(url, timeout=60) as r:
            res = json.load(r)["results"]
        for k in part:
            cache.setdefault(f"{field}:{k}", None)
        for w in res:
            hit = {"title": w.get("title"), "year": w.get("publication_year"),
                   "doi": ndoi(w.get("doi")), "type": w.get("type"),
                   "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                   "abstract": inverted(w.get("abstract_inverted_index"))}
            if field == "openalex":
                cache[f"openalex:{w['id'].rsplit('/', 1)[-1]}"] = hit
            else:
                cache[f"doi:{hit['doi']}"] = hit
        CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True))
        time.sleep(0.3)
    return cache


MAIN = {"openalex": ("hits.csv", "hits_addendum.csv"), "wos": "wos_2026-11-08.txt",
        "scopus": "scopus_2026-11-09.csv", "ieee": "ieee_xplore_2026-11-08.csv",
        "acm": "acm_dl_2026-11-08.json"}
SUPP = {"openalex": ("hits_supplement.csv",), "wos": "wos_supp_2026-11-09.txt",
        "scopus": "scopus_supp_2026-11-09.csv", "ieee": "ieee_xplore_supp_2026-11-09.csv",
        "acm": "acm_dl_supp_2026-11-09.json"}


def load(files=MAIN):
    out = []
    for name in files["openalex"]:
        with open(LIT / name, newline="") as fh:
            for r in csv.DictReader(fh):
                out.append(rec("OpenAlex", r["id"].rsplit("/", 1)[-1], r["title"], r["year"],
                               r["venue"], r["doi"], "", r["type"]))
    with open(DB / files["wos"], encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
            out.append(rec("WoS", r["UT"], r["TI"], r["PY"] or r["EA"], r["SO"], r["DI"],
                           r["AB"], r["DT"]))
    with open(DB / files["scopus"], encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ab = "" if r["Abstract"].startswith("[No abstract") else r["Abstract"]
            out.append(rec("Scopus", r["EID"], r["Title"], r["Year"], r["Source title"],
                           r["DOI"], ab, r["Document Type"]))
    with open(DB / files["ieee"], encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            out.append(rec("IEEE", r["DOI"] or r["PDF Link"], r["Document Title"],
                           r["Publication Year"], r["Publication Title"], r["DOI"],
                           r["Abstract"], r.get("Document Identifier", "")))
    for r in json.loads((DB / files["acm"]).read_text()):
        venue = re.sub(r"https?://doi\.org/\S*$", "", r.get("venue") or "")
        out.append(rec("ACM", r["doi"], r["title"], r.get("date"), venue, r["doi"],
                       r.get("abstract", "").rstrip("…"), r.get("type")))
    return out


def complete(recs):
    oa = openalex([r["sid"] for r in recs if r["src"] == "OpenAlex"], "openalex")
    oa = openalex([r["doi"] for r in recs if r["src"] == "ACM"], "doi")
    for r in recs:
        if r["src"] == "OpenAlex":
            hit = oa.get(f"openalex:{r['sid']}")
            if hit:
                r["abstract"] = hit["abstract"] or ""
        elif r["src"] == "ACM":
            hit = oa.get(f"doi:{r['doi']}")
            if hit and hit["title"]:
                r["title"] = " ".join(hit["title"].split())
                if hit["abstract"]:
                    r["abstract"] = hit["abstract"]
                r["year"] = hit["year"] or r["year"]


def cluster(recs):
    groups = []                      # each: {"dois": set, "titles": set, "recs": list}
    by_doi, by_title = {}, {}
    for r in recs:
        nt = ntitle(r["title"])
        g = by_doi.get(r["doi"]) if r["doi"] else None
        if g is None and len(nt) >= 20:
            cand = by_title.get(nt)
            if cand is not None and (not r["doi"] or not cand["dois"] or r["doi"] in cand["dois"]):
                g = cand
        if g is None:
            g = {"dois": set(), "titles": set(), "recs": []}
            groups.append(g)
        g["recs"].append(r)
        if r["doi"]:
            g["dois"].add(r["doi"])
            by_doi[r["doi"]] = g
        if len(nt) >= 20:
            g["titles"].add(nt)
            by_title.setdefault(nt, g)
    return groups


def pick(g, key):
    """Prefer the value from the richest source: Scopus, WoS, IEEE, OpenAlex, ACM."""
    pref = ["Scopus", "WoS", "IEEE", "OpenAlex", "ACM"]
    vals = sorted((pref.index(r["src"]), r[key]) for r in g["recs"] if r[key])
    if key == "abstract":
        vals = sorted(((-len(v), 0), v) for _, v in vals)
    return vals[0][1] if vals else ""


def supplement():
    """Merge the supplementary query and match its works against merged.csv."""
    recs = load(SUPP)
    complete(recs)
    groups = cluster(recs)
    with open(DB / "merged.csv", newline="") as fh:
        old = list(csv.DictReader(fh))
    by_doi = {d: r["rid"] for r in old for d in r["doi"].split(";") if d}
    by_title = {ntitle(r["title"]): r["rid"] for r in old if len(ntitle(r["title"])) >= 20}
    rows = []
    for g in groups:
        rid = next((by_doi[d] for d in sorted(g["dois"]) if d in by_doi), None)
        if rid is None:
            rid = next((by_title[t] for t in sorted(g["titles"]) if t in by_title), None)
        srcs = sorted({r["src"] for r in g["recs"]}, key=ORDER.index)
        rows.append({"rid": rid or "", "year": pick(g, "year"), "title": pick(g, "title"),
                     "venue": pick(g, "venue"), "type": pick(g, "type"),
                     "doi": ";".join(sorted(g["dois"])), "sources": ";".join(srcs),
                     "n_records": len(g["recs"]), "abstract": pick(g, "abstract"),
                     "ids": ";".join(f"{r['src']}:{r['sid']}" for r in g["recs"])})
    new = sorted((r for r in rows if not r["rid"]), key=lambda r: (r["year"] or 0, ntitle(r["title"])))
    for i, r in enumerate(new, 1):
        r["rid"] = "S%04d" % i
    rows.sort(key=lambda r: (r["rid"][0] == "R", r["rid"]))
    with open(DB / "merged_supp.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n = {s: sum(r["src"] == s for r in recs) for s in ORDER}
    print("records per source:", n, "total", len(recs))
    print("unique works:", len(rows), " duplicates removed:", len(recs) - len(rows))
    print("already in merged.csv:", len(rows) - len(new), " new works:", len(new))
    only = {s: sum(r["sources"] == s for r in new) for s in ORDER}
    print("new works found by one source only:", only)
    print("new works without abstract:", sum(not r["abstract"] for r in new))


def main():
    recs = load()
    complete(recs)
    groups = cluster(recs)
    rows = []
    for i, g in enumerate(sorted(groups, key=lambda g: (pick(g, "year") or 0, ntitle(pick(g, "title")))), 1):
        srcs = sorted({r["src"] for r in g["recs"]}, key=ORDER.index)
        rows.append({"rid": "R%04d" % i, "year": pick(g, "year"), "title": pick(g, "title"),
                     "venue": pick(g, "venue"), "type": pick(g, "type"),
                     "doi": ";".join(sorted(g["dois"])), "sources": ";".join(srcs),
                     "n_records": len(g["recs"]), "abstract": pick(g, "abstract"),
                     "ids": ";".join(f"{r['src']}:{r['sid']}" for r in g["recs"])})
    with open(DB / "merged.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n = {s: sum(r["src"] == s for r in recs) for s in ORDER}
    print("records per source:", n, "total", len(recs))
    print("unique works:", len(rows), " duplicates removed:", len(recs) - len(rows))
    only = {s: sum(r["sources"] == s for r in rows) for s in ORDER}
    print("found by one source only:", only)
    print("no abstract:", sum(not r["abstract"] for r in rows))


if __name__ == "__main__":
    supplement() if "--supplement" in sys.argv[1:] else main()
