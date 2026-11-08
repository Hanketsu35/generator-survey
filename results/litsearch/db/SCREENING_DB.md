# Multi-database search: merge and title/abstract screening

## Sources

One Boolean query, the union of the 23 OpenAlex queries (`../queries.txt`,
`../queries_addendum.txt`), run on title, abstract and keywords:

```
("minimal generator*" AND (itemset* OR mining))
OR (generator* AND ("closed itemset*" OR "closed pattern*" OR "closed graph*"))
OR "sequential generator*" OR "generator pattern*" OR "free itemset*"
OR ("free set*" AND frequen*) OR ("key pattern*" AND mining) OR "key itemset*"
OR (utility AND generator* AND itemset*) OR (generator* AND "data stream*" AND closed)
OR "minimal rare itemset*" OR "disjunction-free" OR "minimal infrequent"
OR "minimally infrequent" OR "minimal rare pattern*"
```

| source | field syntax | date | records | file |
|---|---|---|---|---|
| OpenAlex | 23 title/abstract queries | 2026-10-05, 2026-10-20 | 601 | `../hits.csv`, `../hits_addendum.csv` |
| Web of Science Core Collection | `TS=(...)` | 2026-11-08 | 550 | `wos_2026-11-08.txt` |
| Scopus | `TITLE-ABS-KEY(...)` | 2026-11-09 | 571 | `scopus_2026-11-09.csv` |
| IEEE Xplore | All Metadata, Boolean | 2026-11-08 | 938 | `ieee_xplore_2026-11-08.csv` |
| ACM Guide to Computing Literature | Title, Abstract, Keyword | 2026-11-08 | 119 | `acm_dl_2026-11-08.json` |
| **total** | | | **2,779** | |

The ACM records were read from the result pages, not exported. Their titles
stop at the first colon, so `tools/merge_db.py` completes title and abstract
from OpenAlex by DOI. It also adds the OpenAlex abstracts, which the hit lists
lack. The answers are cached in `openalex_meta.json`.

## Duplicates

Two records are the same work when they share a DOI, or when their
normalised titles agree and they carry no two different DOIs
(`tools/merge_db.py`). 932 duplicates were removed. That leaves 1,847 works
(`merged.csv`).

Some works were returned by one source only: IEEE Xplore 837, OpenAlex 215,
WoS 178, Scopus 92 and ACM 35. IEEE's All Metadata field also matches index
terms, and most of its single-source records are electrical generators and
test-pattern generators.

## Screening on title and abstract

Every work has a recorded decision in `screening.csv`. The codes are:

| code | meaning | works |
|---|---|---|
| X1 | outside pattern mining (power engineering, circuit test, neuroscience, logic, ...) | 1,459 |
| X2 | pattern mining, but another pattern class (closed, maximal, utility, contrast, ...) | 68 |
| X3 | no mining algorithm: survey, theory, rule base, measure, application | 101 |
| X4 | another data model or pattern language: negation, disjunction, uncertain, weighted, numerical, XML, data cubes, partial orders | 38 |
| X5 | not a refereed computer-science publication: front matter, thesis, report, non-CS venue | 36 |
| X6 | sampling or heuristic, not an exact enumeration | 2 |
| K | already decided in the OpenAlex search (`../VERIFIED.md`, `../ADDENDUM.md`) | 112 |
| FT | new candidate, to be decided on the full text | 31 |
| | **total** | **1,847** |

The 1,291 works that mention no mining term in title or abstract were
screened on the title. Eight of them were moved to the abstract screen
because their titles were close to the topic. The codes follow the exclusions
of `../RULE.md`.

## Validation against the counted algorithms

Six of the 41 counted algorithms have no record in any of the five sources:

| work | likely reason |
|---|---|
| Pascal (SIGKDD Explorations 2000) | "key patterns" is not in the indexed metadata, or the venue is not indexed |
| GC-growth (PODS 2005) | the abstract speaks of equivalence classes, relative risk and odds ratio |
| DefMe (PAKDD 2014) | "minimal patterns" and "free" are not query terms |
| FEAT (WWW 2008) | "sequence generators", while the query has "sequential generator*" |
| Fogger (EDBT 2009) | "graph generators", while the query has generator* with "closed graph*" |
| ICTAI 2007 (AprioriRare, MRG-Exp) | not found; its 2010 version is (R0584) |

All six entered the survey through the original survey's list, not through a
search. The query misses the forms "sequence generator*" and "graph
generator*", and "minimal patterns" for DefMe. The supplementary query below
was written for these gaps.

## Supplementary query (2026-11-09)

```
("sequence generator*" AND (frequent OR mining))
OR ("graph generator*" AND (frequent OR mining)) OR "subgraph generator*"
OR ("tree generator*" AND (frequent OR mining))
OR ("free pattern*" AND (mining OR frequent))
OR ("minimal pattern*" AND (mining OR frequent) AND (free OR generator* OR closed))
OR ("equivalence class*" AND ("closed pattern*" OR "closed itemset*"))
OR ("minimal generator*" AND (lattice* OR closure* OR pattern*))
OR "delta-free" OR "δ-free"
```

It was run with the same field syntax on the same five sources. OpenAlex has
no truncation, so there it ran as 15 queries with singular and plural forms
(`tools/litsearch.py --supplement`, `../queries_supplement.txt`).

| source | records | file |
|---|---|---|
| OpenAlex | 364 | `../hits_supplement.csv` |
| Web of Science Core Collection | 235 | `wos_supp_2026-11-09.txt` |
| Scopus | 318 | `scopus_supp_2026-11-09.csv` |
| IEEE Xplore | 118 | `ieee_xplore_supp_2026-11-09.csv` |
| ACM Guide to Computing Literature | 83 | `acm_dl_supp_2026-11-09.json` |
| **total** | **1,118** | |

ACM did not let the result page be saved this time. The DOI, year and
document type of each record were read from the page; titles and abstracts
come from OpenAlex by DOI, as before. For the 17 ACM-only DOIs (prefix
10.5555), which OpenAlex does not hold, the title and venue were read from
the page.

`tools/merge_db.py --supplement` removes duplicates the same way and writes
`merged_supp.csv`. The 1,118 records are 584 works. 108 of them are already
in `merged.csv` and keep their R number and their decision. The other 476 are
new and numbered S0001 to S0476. Their decisions are in `screening_supp.csv`:

| code | works |
|---|---|
| X1 outside pattern mining | 392 |
| X2 another pattern class | 28 |
| X3 no mining algorithm | 23 |
| X4 another data model or pattern language | 18 |
| X5 not a refereed CS publication | 8 |
| K already decided (FEAT, Fogger, DefMe) | 3 |
| FT full text needed | 4 |
| **total** | **476** |

Most of X1 are random-graph generators, pseudo-random sequence generators,
δ-free graphs in combinatorics, the δ phase of alloys, δ-free ATPase, and
minimal generators of ideals in commutative algebra. The four new candidates
are S0089 (concept lattice and minimal generators, ARIMA 2005), S0099
(frequent δ-free patterns in large databases, DS 2005), S0229 (δ-free
sequential patterns, ICDM 2014) and S0262 (exact and approximate minimal
pattern mining, 2017, an extended version of DefMe).

### Validation after the supplement

| work | main query | supplement |
|---|---|---|
| FEAT (WWW 2008) | no | yes (S0123) |
| Fogger (EDBT 2009) | no | yes (S0145) |
| DefMe (PAKDD 2014) | no | yes (S0224) |
| Pascal (SIGKDD Explorations 2000) | no | no |
| GC-growth (PODS 2005) | no | no |
| ICTAI 2007 (AprioriRare, MRG-Exp) | no | no |

38 of the 41 counted algorithms are now retrieved by the database search.
The remaining three come from the original survey's list. Their papers are
not indexed under any of the terms; GC-growth's journal version (KDD 2007,
R0435) is retrieved, as is the 2010 version of the ICTAI paper (R0584).

## Totals over both queries

| step | main | supplement | total |
|---|---|---|---|
| records identified | 2,779 | 1,118 | 3,897 |
| duplicates removed | 932 | 534 + 108 already in main | 1,574 |
| works screened | 1,847 | 476 | 2,323 |
| excluded on title and abstract | 1,704 | 469 | 2,173 |
| decided before (K) | 112 | 3 | 115 |
| to the full text (FT) | 31 | 4 | 35 |
