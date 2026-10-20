# Search addendum (2026-10-20)

## Why

A review of the survey found that the registered queries (`queries.txt`)
have no term for the names under which minimal rare itemsets are also
published: *minimal(ly) infrequent itemsets* and *minimal rare
(infrequent) patterns*. One rare-itemset miner, IFP_min, appears under such
a name only. The rule (`RULE.md`) is unchanged; only the queries are added.

## Search

`python tools/litsearch.py --addendum`, OpenAlex title and abstract,
2026-10-20. Six queries (`queries_addendum.txt`); 55 works not already in
`hits.csv` (`hits_addendum.csv`).

## Screening on title, venue and abstract

Set aside under the rule's exclusions:

- other data models: XML structures (2004, 2008); multi-dimensional
  intervals (2006, 2018); partially ordered data (2010, 2014, 2021, 2022);
  uncertain data (MiFI-Outlier 2019, Information Sciences 2021, Computer
  Journal 2021);
- weighted support: infrequent weighted itemsets (2014, 2015, 2016, 2025)
  and the weighted-stream miner of China Communications 2019;
- hypergraph dualization and complexity results without a mining
  algorithm: generation of weighted transversals (2000), dualization in
  products of lattices (2002), dual-bounded hypergraphs (2002),
  irredundant dualization (2003), monotone duality in logspace (2013),
  dualization over distributive lattices (2022);
- not itemset mining: inverse frequent itemset mining (2013), logical
  analysis of data (2023, 2025), and five works from other fields;
- a thesis (declarative itemset mining, 2020), whose algorithm is CP4MII
  below.

## Decided on the full text

| work | decision | evidence |
|---|---|---|
| IFP_min, Gupta, Mittal, Bhattacharya, COMAD 2011 (arXiv:1207.4958) | **count**, rare, 2011 | Def. 1 (minimally infrequent: infrequent, all proper subsets frequent); Algorithm IFP_min, "Output: Minimally infrequent itemsets (MIIs) in db(T)"; Sect. 5.2 "Completeness and Soundness": "it returns all minimally infrequent itemsets and all itemsets returned by it are minimally infrequent". Input: a transaction database. |
| CP4MII, Belaid, Bessiere, Lazaar, IJCAI 2019 | **count**, rare, 2019 | Def. 2 (MII); Theorem 1: "The set of solutions to MODEL(D,s,b) corresponds to the set of MFIs if b = true, the set of MIIs otherwise." Code: gite.lirmm.fr/belaid/cp4borders (Scala, OscaR). |
| MIMDS_1/2, Zhou and Pi, IAJIT 18(6) 2021 | **count** on its own claim, stream (sliding window), 2021 | Eq. (4) (minimal infrequent pattern in the window); Algorithm 1 "Output: MP // minimal infrequent patterns"; Sect. 4: "the MDO algorithm can find all the minimal infrequent patterns". No proof; counted on its claim, as MG-CHARM. |
| MRPM, Li and Cai, ITC 51(2) 2022 | **count**, stream (sliding window), 2022 | Def. 3 (MRP: a rare pattern all of whose subsets are frequent); Algorithm 1 "Output: MRPs". |
| Kyiv, Demchuk and Leith, arXiv:1403.6985 (2014) | meets the rule, **not refereed** | "a new algorithm, called Kyiv, for finding all minimal attribute combinations occurring with less than a specified frequency"; no refereed version found (CrossRef). |
| Murakami and Uno, DAM 2014 | **exclude**: input is a hypergraph (complements of maximal frequent itemsets), not a database | Sect. on instances: "the dual of the set of the complements of maximal frequent itemsets is the set of minimal infrequent itemsets". |
| Boros, Gurvich, Khachiyan, Makino, STACS 2002 / AMAI 2003 | **exclude**: a complexity result, no mining algorithm | decided on DIMACS TR 2000-37 (same authors, same result): Corollary 1 obtains the minimal t-infrequent sets by reduction to hypergraph dualization (Fredman–Khachiyan). |

## Not yet decided: full text behind a paywall

- Loo, Yip, Kao, Cheung, DEXA 2000 (10.1007/3-540-44469-6_66)
- Eisenschmidt and Haus, Discrete Applied Mathematics 2012 (10.1016/j.dam.2012.03.013)
- Hemalatha, Vaidehi, Lakshmi, ESWA 2015 (10.1016/j.eswa.2014.09.053)
- minimal rare pattern outlier detection for data streams with anti-monotonic constraints, LNCS 2020 (10.1007/978-3-030-62974-8_16)
- Bitwise vertical mining of minimal rare patterns, LNCS 2023 (10.1007/978-3-031-39831-5_13)
- CORI (SPMF), Bouasker and Ben Yahia, found in SPMF's list during the review

The IJAERD 2016 paper "Minimally infrequent itemset mining using
pattern-growth paradigm" repeats the IFP_min title and is to be checked as
a version of it.
