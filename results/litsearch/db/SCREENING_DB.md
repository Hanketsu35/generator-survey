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

Six of the 41 algorithms counted at the time (before the full-text step
below and the scope change) have no record in any of the five sources:

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

Counted per algorithm, after the scope change of 2026-11-09 (`../RULE.md`
am. 4, which removes Fogger): the database search retrieves the paper on
which the decision was made for 44 of the 48 counted algorithms. The four
others are Pascal, GC-growth, and AprioriRare and MRG-Exp, which share the
ICTAI 2007 paper; the 2010 version of that paper is retrieved (R0584). All
four came from the original survey's list. (An earlier count here, "38 of
41", counted the ICTAI paper as one item and included Fogger.)

## Candidates over the whole survey (for the PRISMA flow)

| | candidates |
|---|---|
| first pass, OpenAlex and other methods (`../VERIFIED.md`, `../ADDENDUM.md`) | 85 |
| new from the five-database search (29 works in `FULLTEXT_DB.md`, less Gr-growth, Kryszkiewicz 2004 and Kryszkiewicz & Gajek 2002, decided before) | 26 |
| **total decided on the full text** | **111** |
| new from Google Scholar (`FULLTEXT_SCHOLAR.md`: 14 works, less Soulet & Rioult 2016 and Phan-Luong's one-phase method, already candidates) | 12 |
| **total with Google Scholar** | **123** |

Outcome before Google Scholar: 48 counted, 2 meet the rule but are out of
scope (Fogger, RTGener), 36 excluded, 2 not refereed, 23 not reachable.
With Google Scholar and the full texts read in the browser on 2026-11-10:
50 counted (CDP+I; the closed keys base of Phan Luong 2002, formerly not
reachable), 43 excluded (Huấn 2020, Hanusse & Maabout 2011, Troiano et al.
2009, Duong et al. 2024: IC2; Bouasker et al. 2015: EC4; Cordero et al.
2022: EC2; arules generator target: EC6), 2 out of scope, 2 not refereed,
26 not reachable (22 earlier, 4 from Scholar).

Google Scholar (2026-11-10, Publish or Perish, 8 queries, first 200 results
each; two queries returned 50 and 138): 1,388 records, 1,218 unique, 250
already among the database works, 968 screened on title and snippet
(`scholar_screening.csv`). It retrieves the deciding papers of Pascal, of
AprioriRare with MRG-Exp, and of CDP+I, which no database returned (the
databases retrieve 45 of the 50 counted algorithms' deciding papers); GC-growth remains the
one counted algorithm found only through references.

Eight candidates have no record in any of the five databases and came
from the original survey's list or from the references of included
papers: Pascal, GC-growth, the three algorithms of the ICTAI 2007 paper
(AprioriRare, MRG-Exp, Arima), TITANIC, CORI and MC-FHAUIM. Four of them
are counted. The other 103 candidates are all retrieved.

## Totals over both queries

| step | main | supplement | total |
|---|---|---|---|
| records identified | 2,779 | 1,118 | 3,897 |
| duplicates removed | 932 | 534 + 108 already in main | 1,574 |
| works screened | 1,847 | 476 | 2,323 |
| excluded on title and abstract | 1,704 | 469 | 2,173 |
| decided before (K) | 112 | 3 | 115 |
| to the full text (FT) | 31 | 4 | 35 |

## Full text

The 35 records coded FT are decided in `FULLTEXT_DB.md`: eight new works
are counted (GenAll, GBorder2, FTMiner, FFIP, DeFFeD, HUGN, MRP-TBMiner,
CMG), one meets the rule but mines trees and is out of scope (RTGener),
ten are excluded, two were decided before, and eight could not be read.

## Files not redistributed

The exports themselves (`wos_*.txt`, `scopus_*.csv`, `ieee_xplore_*.csv`,
`acm_dl_*.json`, and the Publish or Perish files `scholar_q*.csv`) and the
merged tables with their abstracts are not in the repository: the providers'
terms restrict redistribution. They are kept by the authors in `db/raw/`. The
repository keeps, for every work, its record identifier, title, venue, DOI,
the sources that returned it and its screening code (`merged*.csv`,
`screening*.csv`, `scholar_screening.csv`), so each decision can be checked
and each query rerun.
