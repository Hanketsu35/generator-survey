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
| Szathmary et al., ICTAI 2007, "Towards rare itemset mining" | K (AprioriRare, MRG-Exp, counted) | Retrieved by Scholar, not by the five databases |
| Bastide et al., SIGKDD Explorations 2000, "Mining frequent patterns with counting inference" | K (Pascal, counted) | Retrieved by Scholar, not by the five databases |
| Szathmary et al., CLA 2008 / IDA 2009 | K (Touch, Talky-G, counted) | |
| Demchuk & Leith, CoRR 2014 | K (Kyiv, recorded as not refereed) | |

## Not reachable (counted as such; 10 works)

Automated access refused (ACM, IEEE, SAGE, Springer, ResearchGate,
academia.edu, neliti). Soulet & Rioult 2016 was already a candidate and
stays unreachable.


Minimal generators of closed rare itemsets with item weights (Huấn, Univ.
Danang JST; neliti refuses automated access); lattice-based generator mining
(Chi, academia.edu); Vo & Nguyen 2017 chapter; Phan-Luong, frequent key and
closed itemsets in one phase; Le 2007, minimal infrequent itemsets on a
cluster; Hanusse & Maabout, CIKM 2011, parallel borders; Soulet & Rioult 2016
(extended DefMe, listed as unreachable); Bouasker et al., IDA 2015, rare
correlated patterns; Troiano et al., ISDA 2009, Rarity; Cordero et al. 2022,
minimal generators in FCA; Duong, Pham, Truong, Fournier-Viger, Applied
Intelligence 2024, concise representations of frequent high-utility
occupancy patterns (the same group's Gen-FHUOIM is EC4).
