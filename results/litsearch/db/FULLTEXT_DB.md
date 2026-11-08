# Full text of the multi-database candidates (2026-11-09)

The 35 records sent to the full text by the title and abstract screening
(`screening.csv`, `screening_supp.csv`, code FT) were read against
`../RULE.md` and its amendments. Records that are versions of one work are
decided together. Full texts were read through the institution's access in
the browser or from open copies; the PDFs are kept locally and not committed.

| records | work | decision | evidence |
|---|---|---|---|
| R0344, S0089 | GenAll, Ben Tekaya, Ben Yahia, Slimani; CLA 2005 and ARIMA 4 (2005) (10.46298/arima.1835) | COUNT, transactional, 2005 | ARIMA p.176: "Générateur minimal : ... correspond aux bloqueurs minimaux associés à la famille de ses faces"; Algorithm 1 "Entrée: Le contexte d'extraction K / Sortie: L'arbre lexicographique de F, ImmSucc, liste-gen": every formal concept with the list of its minimal generators. Input: a formal context (a transaction database). No support threshold: all concepts. |
| S0229 | DeFFeD, Holat, Plantevit, Raïssi, Tomeh, Charnois, Crémilleux; ICDM 2014 (10.1109/ICDM.2014.154; HAL hal-01100929) | COUNT, sequential, 2014 | Def. 2.5: s is δ-free if for all s' ≺ s, Support(s') > Support(s) + δ; §II-C: "Sequence generators [24], [25] are a particular case of δ-free sequence (i.e., δ = 0)"; "To discover the complete set of frequent δ-free sequential patterns ... DeFFeD must be launched as follows". Input: a sequence database. No proof of completeness beyond the pruning properties 2.9-2.11; no code found yet. |
| R0327 | GBorder2, Xu and Xie, PKDD 2005, LNAI 3721 pp. 701–708 (10.1007/11564126_75) | COUNT on its own claim, transactional (incremental), 2005 | §2: "An itemset is a generator if none of its proper subsets has the same support as it has ... the set of frequent generators by FG"; "The generators representation consists of two components: (a) FG enriched by the support value for each itemset X∈FG; (b) GB−"; GBorder2 maintains this representation as transactions are added and removed. Input: a transaction database and its updates. No proof. |
| S0099 | FTMiner, Hébert and Crémilleux, DS 2005, LNAI 3735 pp. 124–136 (10.1007/11563983_12) | COUNT, transactional, 2005 | Def. 2: X is δ-free if for all X1 ⊂ X, |g(X)| + δ < |g(X1)|; §2.1: "When δ = 0, X is called a 0-free set or a free set"; Theorem 2: "The algorithm FTMiner extracts all the γ-frequent and δ-free patterns from the database r", with proofs of correctness and completeness. |
| R0775 | RTGener, Yi, Xu, Peng, Xiong, Wang, Ma; CyberC 2013 (10.1109/CyberC.2013.29) | COUNT on its own claim, tree (rooted ordered subtrees), 2013 | Problem statement (§III-B): "Given a rooted tree database, RTD; a minimum support threshold, min_sup; we are required to find all frequent rooted tree generators in RTD"; Fig. 4 "Output: a set of all frequent rooted tree generators, GS"; Lemma 1: "t must not be a generator if support of t is equal to the support of t'" (t' a size-1 subtree). Def. 4 speaks of "minimum size" patterns of the class, but the test is support-minimality against immediate subtrees. No proof of completeness; no code. |
| R0557 | FFIP, Zhang, Lu, Zhou, APCIP 2009 (10.1109/APCIP.2009.93) | COUNT on its own claim, transactional, 2009 | Def. 1 (δ-free-set, Boulicaut et al.); Algorithm 2 "Input: r a binary database over a set of items R, σ and δ two thresholds. Output: FreqFreePart(r, σ, δ)", the frequent δ-free sets found by partitioning the database; δ = 0 gives the frequent free sets (generators). No proof; no code. |
| R1157 | MRP-TBMiner, minimal rare pattern mining for satellite telemetry data streams, Chinese Journal of Computers 42(6), 2019 (10.11897/SP.J.1016.2019.01351; open PDF at cjc.ict.ac.cn) | COUNT on its own claim, stream (sliding window), 2019 | Def. 5: a rare pattern all of whose subsets are frequent is a minimal rare pattern (MP), Eq. 6; abstract: the algorithm finds all minimal rare patterns in the window ("挖掘出全部的最小稀有模式"). Rare means support below the frequent threshold and at least a noise threshold; with the noise threshold at its lowest the set is the minimal rare itemsets. No proof; no code. |
| R0967 | HUGN, Ren, Yan, Gao, Wang, He, IJICIC 12(4) (2016) 1115–1128 (open PDF at ijicic.org) | COUNT on its own claim, high-utility (negative utilities), 2016 | Def. 2.8: "An itemset X is a generator iff there is no itemset Y such that Y ⊂ X and sup(X) = sup(Y)"; Def. 2.9: a high utility generator is a generator whose utility is at least minutil (the HUG-Miner definition); §3: "the HUGN algorithm is designed to mine high utility generators". No proof; no code. |
| R1261 | CMG (in CONCISE), Parfait and André, SCRS Conference Proceedings on Intelligent Systems (2021) 15–36 (10.52458/978-93-91842-08-6-2) | MEETS THE RULE; refereeing of the venue not established, so not counted for now | §3.1: CMG "takes as input a database and a minimum support minsup. It returns the frequent closed, maximal and their generators"; Algorithm 1 "Ensure: ⟨Closed, Maximal, Generator, Supp⟩". The publisher's page states no review process. |
| R1199, R1209, R1357 | GDPM, Makhalova, Buzmakov, Kuznetsov, Napoli; arXiv 2020, CEUR 2020, IJAR 2022 | EXCLUDE: not the complete set of generators | arXiv v3 §5.1: GDPM "returns the computed closure levels and, optionally, one passkey per closed itemset"; a passkey is a minimum-cardinality key (Def. 2). |
| R0266 | Calders and Goethals, minimal k-free representations, PKDD 2003 (10.1007/978-3-540-39804-2_9) | EXCLUDE: no generator-mining algorithm | Abstract: "we present a unifying framework encapsulating most known concise representations"; the new representations S_k(G) are compared by size (Sect. 5); no algorithm whose output is the generators. |
| R0351 | Frambourg, Valtchev, Godin, merge-based computation of minimal generators, ICCS 2005, LNAI 3596 pp. 181–194 (10.1007/11524564_12) | EXCLUDE: the input is not a database | §4.1: the procedure merges two concept lattices L1 and L2 of subcontexts; "mingens already exist" in L1 and the mingens of the new concepts are computed during the merge ("preliminary experimental results"). |
| R0403, R0500 | Hamrouni, Ben Yahia, Mephu Nguifo, succinct system of minimal generators, CLA 2006 and LNAI 4923 (2008) pp. 80–95 (10.1007/978-3-540-78921-5_5) | EXCLUDE: no mining algorithm | New definitions of the SSMG and Prop. 9 ("an exact representation of the MG set"); §5 compares the number of succinct and of all frequent MGs; no algorithm is given. |
| R0411 | DSFS_Miner, Hamrouni, Valtchev, Ben Yahia, Mephu Nguifo, ICFCA 2007, LNAI 4390 pp. 130–150 (10.1007/978-3-540-70901-5_9) | EXCLUDE: a different family | Def. 11 and §6: DSFS_Miner returns FDSFS_K, the representative MGs together with non-MG elements of their negative border ("eac ... is not a MG ... It will then be retained as an element of the representation"); the generators are not output as an identified set. |
| R1224 | Iwanuma, Yajima, Yamamoto, negative rules over minimal generators, IEEE BigData 2020 (10.1109/BigData50022.2020.9377846) | EXCLUDE: the output is negative association rules | Abstract: "we study an efficient mining algorithm of negative rules over minimal generators ... We show a new top-down algorithm for mining a consistent and non-redundant set of negative association rules"; the generators index a suffix tree and are not the output. |
| R0405 | Shi, Hua, Zhang, the canonical basis of implicational system, ICMLC 2006 (10.1109/ICMLC.2006.258563) | EXCLUDE: generators are an intermediate step | Def. 5 defines (minimal) generators, and Algorithm 1 builds the generator levels G_i; Algorithm 2 then keeps "Answer ← ∪{p ∈ G | ∄p' ∈ G, φ(p) = φ(p')}" to obtain the closed itemsets, from which the pseudo-closed sets and the canonical basis are computed (§4). The output is the canonical basis. |
| R0472 | Szathmary, Valtchev, Napoli, Godin, constructing iceberg lattices from frequent closures using generators, DS 2008 (10.1007/978-3-540-88411-8_15; HAL inria-00331524) | EXCLUDE: the input is not a database | Abstract: "The goal is to extract the precedence relation from a more common mining output, i.e. closures and generators ... the new algorithm fits an arbitrary FCI/FG-miner." |
| R0310 | Kryszkiewicz, SAC 2004 | K: already excluded (VERIFIED.md, "reduces an already computed representation") | — |
| R0368, R0459 | Liu, Li, Wong, generators and a positive border; 2006 and KAIS 17 (2008) 35–56 (10.1007/s10115-007-0111-5) | K: this is GrGrowth, already counted as Gr-growth | Abstract: "We develop an efficient algorithm, called GrGrowth, to mine generators and positive borders". |
| S0262 | Soulet and Rioult, exact and approximate minimal pattern mining, 2017 (10.1007/978-3-319-45763-5_4) | NOT REACHED: an extended version of DefMe (counted); not in the subscription, and the HAL record (hal-01411167) has no file | — |
| R0499 | Hamrouni, Ben Yahia, Mephu Nguifo, succinct minimal generators, IJFCS 19 (2008) (10.1142/S0129054108005681) | NOT REACHED: the publisher page did not open and the HAL records have no file; the CLA 2006 version (R0403/R0500) gives no mining algorithm | — |
| R0714 | genMG, multiobjective non-redundant rules in streams, 2012 (10.1007/978-3-642-29350-4_9) | NOT REACHED: not in the subscription | — |
| R0892 | Finding minimal rare itemsets with an extended version of the Apriori algorithm, ICAI 2014 (10.14794/icai.9.2014.1.85) | NOT REACHED: the proceedings server does not answer (2026-11-09) | — |
| R0325, R0347, R0536 | HOPE-II (Computer Engineering and Science 2005), IHPD (Computer Engineering 2005), NIUA (Journal of Tangshan College 2009) | NOT REACHED: Chinese journals without an open copy | — |
| R0248, R0249 | Kryszkiewicz and Gajek, ISMIS 2002 | UNVERIFIED (unchanged): not in the institution's subscription (Springer "Access this chapter", 2026-11-09) | — |
| R0546, R0810 | Lo, Khoo, Wong, non-redundant sequential rules, Information Systems 2009; Pham et al., EAAI 2014 | PENDING: ScienceDirect shows a robot check that has to be passed by a person | — |

## Summary

| decision | works | records |
|---|---|---|
| counted | 8: GenAll, GBorder2, FTMiner, FFIP, RTGener, DeFFeD, HUGN, MRP-TBMiner | 9 |
| meets the rule, venue's refereeing not established | 1: CMG (CONCISE) | 1 |
| excluded | 8 | 11 |
| already decided (Gr-growth; Kryszkiewicz 2004) | 2 | 3 |
| unverified, not reached or pending | 10 | 11 |
| **total** | **29** | **35** |

R0248/R0249 (Kryszkiewicz and Gajek 2002) were already listed as unverified
in `../VERIFIED.md` and stay so.

Not reached: S0262 (extended DefMe), R0499 (succinct minimal generators,
IJFCS), R0714 (genMG), R0892 (ICAI 2014), and the three Chinese-language
journal papers R0325, R0347, R0536. Pending: R0546 and R0810, whose
ScienceDirect pages ask for a robot check that has to be passed by a person.

RTGener mines rooted ordered trees, a structured family like Fogger's
graphs; the survey has no tree family yet.
