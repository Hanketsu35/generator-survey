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
generator*"; a supplementary query is still to be run.
