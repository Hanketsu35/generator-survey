# Full-text decisions on the Google Scholar candidates

Google Scholar searched with Publish or Perish on 2026-11-10, 200 results per
query. Records: `scholar_*_2026-11-10.csv`. Title screening:
`scholar_screening.csv` (`tools/scholar_screen.py`). Criteria: `../RULE.md` and
the paper's IC/EC table.

## Decided

| Work | Decision | Basis |
|---|---|---|
| Koçak, Akgün, Guns, Miguel, ECAI 2020 (10.3233/FAIA200110), "Exploiting incomparability in solution dominance" (CDP+I); preprint arXiv:1910.00505 (ModRef 2019) | **COUNT** (transactional; also mines minimal rare itemsets). **Executable**: ESSENCE models and scripts released (github.com/stacs-cp/ECAI2020-CDP, tag 1.0; Zenodo 10.5281/zenodo.3675340), run with the open Conjure/Savile Row/solver toolchain | Read from the released models, `models/gen_fis.essence`: the dominance constraint `(fromSolution(freq_items[1]) subsetEq freq_items[1]) -> (freq_items[2] < fromSolution(freq_items[2]))` with search ascending in itemset size keeps a frequent itemset only if every earlier solution contained in it has strictly larger support. That is the complete set of support-minimal frequent generators, the empty set included (IC2, IC3). `models/min_rare_fis.essence`: support below the threshold and no earlier solution contained in it, which gives the minimal rare itemsets. Exact constraint solving; refereed (ECAI). The ECAI PDF was not reachable (IOS landing page; St Andrews portal 403); the decision rests on the arXiv preprint, which states the same definition ("a frequent itemset which does not have any frequent subsets with the same support"), and on the released models |
| Huấn, JST Univ. Danang 18(5.2), 2020, "High-performance algorithm in mining generators of closed frequent itemsets" (SEQ-GCFI, MCP-GCFI) | EXCLUDE, IC2 | Definition 4 calls every proper subset of a closed itemset with the same support a generator, and Table 4 lists (V,3) together with (VO,3) and (VR,3): non-minimal sets are output |
| Ledmi, Souidi, Hahsler, Ledmi, Kara-Mohamed, IJDMMM 15(2) 2023, "frequent generator itemsets in arules package" | EXCLUDE, EC6: a post-filter of a frequent-itemset miner (a reduction of a given representation), like the Borgelt programs | arules 1.7-2 (2021) NEWS: "The C APRIORI implementation can now mine frequent generator itemsets". The code (`src/istree.c`, `ist_filter`, mode `IST_GENTOR`) marks, after Apriori, every frequent itemset with a subset of equal support. It keeps the ceiling side (`s_min = ceil(tacnt*supp)`). Recorded as a further post-filtering implementation (R) |
| Phan-Luong, "A method for computing frequent key and closed itemsets in one phase" (long version of DaWaK 2002, "The closed keys base of frequent itemsets", R0246) | **COUNT** (transactional), formerly not reachable | Full text from ResearchGate (`papers/ft/scholar/phanluong2002_onephase.pdf`): a key itemset has no strictly included itemset with the same closure; FClosedKeys returns all frequent (key, closure, support) triples, Theorem 2 (correctness and completeness). The refereed venue is the DaWaK 2002 paper on the same representation and algorithm |
| Hanusse & Maabout, CIKM 2011, "A parallel algorithm for computing borders" | EXCLUDE, IC2 | ACM full text (browser, institutional access): the procedure outputs "The MFI set B" (positive border); the negative border appears only in related work |
| Troiano, Scibelli, Birtolo, ISDA 2009, "A fast algorithm for mining rare itemsets" (Rarity) | EXCLUDE, IC2 | IEEE full text: "a list R containing all resulting rare itemsets"; all rare itemsets are output |
| Bouasker, Hamrouni, Ben Yahia, IDA 2015, rare correlated patterns | EXCLUDE, EC4 (on the abstract) | Representations of rare patterns correlated by the bond measure, built on the classes of a closure operator "dedicated to the bond measure"; the companion CORI is excluded the same way. No subscription to the full text |
| Cordero, Enciso, Mora, Ojeda-Aciego et al. 2022, "Interactive search by using minimal generators" | EXCLUDE, EC2 (on the abstract) | Minimal generators computed from a set of implications in formal concept analysis, by a lazy interactive search |
| Duong, Pham, Truong, Fournier-Viger, Applied Intelligence 2024 | EXCLUDE, IC2 | Full text: MaxCloFHUOIM and CloFHUOIM mine closed and maximal FHUOIs, no generators |
| Szathmary et al., ICTAI 2007, "Towards rare itemset mining" | K (AprioriRare, MRG-Exp, counted) | Retrieved by Scholar, not by the five databases |
| Bastide et al., SIGKDD Explorations 2000, "Mining frequent patterns with counting inference" | K (Pascal, counted) | Retrieved by Scholar, not by the five databases |
| Szathmary et al., CLA 2008 / IDA 2009 | K (Touch, Talky-G, counted) | |
| Demchuk & Leith, CoRR 2014 | K (Kyiv, recorded as not refereed) | |

## Not reachable (4 works)

Read in the browser on 2026-11-10 where possible. Not obtained: Huấn,
minimal generators of closed rare itemsets with item weights (NOV-mGCRSI;
the Neliti PDF link returns 404; the same authors' significance itemsets
suggest EC4); Chi, lattice-based generator mining (academia.edu requires an
account); Vo & Nguyen 2017 chapter (no source located); Le 2007, minimal
infrequent itemsets on a cluster (no source located). Soulet & Rioult 2016
(extended DefMe; Springer abstract read, no subscription) stays among the
earlier unreachable candidates.

## Review check of 2026-11-11 (after the Deep Review of the manuscript)

**Re-check of the title rule.** All 589 Scholar works coded X2 by the title
rule of `tools/scholar_screen.py` were re-read by title one by one (the 354
X1 titles name no mining task). Five needed a closer look:

| Work | Decision | Basis |
|---|---|---|
| Szathmary et al., "Efficient vertical mining of frequent closed itemsets and generators" | already counted (Touch, Talky-G) | the ligature "ﬀ" had defeated the rule's prefix match |
| Liu, Li & Wong, SDM 2006, "Positive borders or negative borders" | already counted (Gr-growth) | the abstract names GrGrowth as its algorithm |
| Valtchev et al., JETAI 2002, "Generating frequent itemsets incrementally" | EXCLUDE, IC2 | abstract: incremental mining of frequent closed itemsets only |
| Calders & Goethals, PKDD 2002, "Mining all non-derivable frequent itemsets" (NDI) | EXCLUDE, IC2 | full text (arXiv cs/0206004), §5: the NDIs are a subset of ConFreqDFree, the frequent disjunction-free sets *with part of their border*; an NDI need not be free (a singleton contained in every transaction has bounds [0, |D|] and is non-derivable but not free), and the generators among the NDIs are not identified. Another condensed representation |
| Calders & Goethals, DMKD 2007, "Non-derivable itemset mining" (NDI, journal version; also dfNDI, SDM 2005) | EXCLUDE, IC2 | full text (Springer, institutional access): same output family; dfNDI mines the same NDI collection depth-first |

**Candidates from the references of MINIT and Kyiv.**

| Work | Decision | Basis |
|---|---|---|
| Manning & Haglin, ICDM 2005; Manning, Haglin & Keane, DMKD 16:165–196 (2008), SUDA2 | **COUNT** (rare, first published 2005). **Executable**: C++ in the R package sdcMicro (`suda2`) | full text (Springer, institutional access), §2: "an MSU is a unique itemset with no unique proper subsets … find all k-MSUs, 1 ≤ k ≤ maxk, where maxk ≤ C". With maxk = C this is the complete set of minimal rare itemsets of support 1 at minimum support 2 (IC2 for one parameter setting); exact recursive search; refereed |
| Elliot, Manning & Ford, IJUFKS 10(5):493–509 (2002), SUDA | not reachable | World Scientific page refused the full text; SUDA2's paper says SUDA "always conducts an exhaustive search for MSUs", which suggests COUNT, but the rule needs the paper |

Counts after this check: 127 candidates; 48 counted, 14 executable
(rare 9, 2 executable); not counted 79 (excluded 45, families of fewer than
five 5, not refereed 2, no full text 27).
