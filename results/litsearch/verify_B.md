# Verification batch B: newer transactional candidates

Rule applied: `results/litsearch/RULE.md` (2026-10-05). Each decision rests on the
full text, and when no full text was reachable the entry is marked UNVERIFIED.
"Not reachable" means no open copy was found via OpenAlex, Crossref, J-STAGE,
author or institutional pages, CiteSeerX, or web search. ResearchGate and
Academia.edu returned HTTP 403, and no paywall bypass was used.

Full texts were saved and read from the session scratchpad (`dpminer.pdf`, `ssmg.pdf`,
`n_NehmeICFCA2005.pdf`, `cgt.pdf`, `jsai.pdf`).

---

## 1. Nehmé, Valtchev, Rouane, Godin (2005): IncA-Gen / Magalice-A

- **Citation:** K. Nehmé, P. Valtchev, M. H. Rouane, R. Godin, "On Computing the Minimal
  Generator Family for Concept Lattices and Icebergs", ICFCA 2005, LNCS 3403, pp. 192-207,
  doi 10.1007/978-3-540-32262-7_13.
- **Full text read:** http://www.info2.uqam.ca/~godin_r/Articles/NehmeICFCA2005.pdf (author copy
  with the LNAI 3403 page header). An identical copy is at
  http://archive.dimacs.rutgers.edu/Workshops/WGOrder/Slides/valtchev1.pdf.
- **Output definition (Def. 1, p. 195):** "gen(Y′, Y) = {G ⊆ Y | G′ = Y′ and ∀ F ⊂ G, F′ ⊃ Y′}".
  Algorithm statement (Sec. 4, p. 199): "an algorithmic procedure ... that updates both the
  lattice and the mingen sets of the lattice concepts upon the insertion of a new attribute
  into the context."
- **Input → output:** The input is a formal context K = (O, A, I), a binary table, so it is a
  database. Attributes are inserted one at a time, and the paper runs this "in a batch mode"
  as an "iceberg-plus-mingen constructor" (Sec. 1, p. 193). The output is the concept lattice,
  or the iceberg lattice L^α in Sec. 5, where every concept carries its complete mingen set
  gen(c). Exactness rests on Properties 1-5 and Corollaries 1-2 (Sec. 3, pp. 196-199). In
  particular, Property 5 states that gen₂(c) is *exactly* min(∪ gen₁(ĉ)) × {a} for new concepts.
- **Condition:** None (the full lattice), or frequency (the iceberg variant, Sec. 5, with
  Compute-F-Classes).
- **Decision: INCLUDE.** The input is a database, and the output is the complete family of
  minimal generators, each attached to its closure (concept intent), with or without a
  frequency threshold. **Caveat for the caller:** the output also contains the lattice
  precedence (Hasse) relation between concepts ("our algorithm produces the lattice precedence
  relation beside concepts and mingen", p. 193). The extra item is an order on the closures,
  not additional patterns. If the rule's "only of minimal generators" is read to forbid any
  extra structure, this entry would flip to EXCLUDE.
- **Implementation:** The paper says IncA-Gen is in the Galicia platform (Java), and that a
  stand-alone version named Magalice-A exists (Sec. 6).

## 2. DPMiner: Li, Liu, Wong (KDD 2007)

- **Citation:** J. Li, G. Liu, L. Wong, "Mining statistically important equivalence classes and
  delta-discriminative emerging patterns", KDD 2007, pp. 430-439, doi 10.1145/1281192.1281240.
- **Full text read:** https://www.comp.nus.edu.sg/~wongls/psZ/guimei-kdd07.pdf (10 pp., author copy).
- **Problem statement / output (Sec. 2, p. 2):** "Problem 1 can be solved by mining the generators
  and closed patterns of frequent equivalence classes, and their associated class label
  distribution information." Sec. 3, Step 5: "output significant equivalence classes as [G_X, X]
  ... and G_X is the corresponding set of generators."
- **Input → output:** The input is a transaction database (k class-labelled datasets) and a
  support threshold ms. Step 2 mines *all* frequent closed patterns and their generator sets:
  "Mine frequent closed patterns and generators to concisely represent all frequent equivalence
  classes of D". The completeness claim reads "The completeness of the algorithm is guaranteed
  at Step 2 by Corollary 1". The output is a set of equivalence classes [G, C], meaning each
  frequent closed pattern with its full generator set, plus class-label counts. Generator
  minimality is checked exactly against the immediate subsets stored in a hash table
  (Sec. 4.1.2).
- **Condition:** Frequency, plus an optional statistical-significance threshold on the class.
  With a threshold that accepts every class, the output is all frequent generators grouped with
  their closures. Problem 2 instead outputs only non-redundant δ-discriminative classes, a
  restriction the allowed-condition list does not cover. The decision rests on Problem 1.
- **Decision: INCLUDE.** The input is a database, and the output is all frequent generators
  paired with their closures, which the rule allows. The stated threshold is frequency, and at
  least one parameter setting gives the complete family.
- **Implementation:** Not checked. DPMiner binaries have historically come from G. Liu's NUS
  pages.

## 3. MG-CHARM: Vo, Le (CIE39 2009)

- **Citation:** B. Vo, B. Le, "Fast algorithm for mining minimal generators of frequent closed
  itemsets and their applications", 39th Int. Conf. on Computers & Industrial Engineering (CIE39),
  2009, pp. 1407-1411, doi 10.1109/iccie.2009.5223846.
- **Full text read:** None. OpenAlex lists the work as closed with no repository copy, the
  ResearchGate entry 224584556 returned 403, and IEEE Xplore is paywalled.
- **Decision: UNVERIFIED.** The title suggests generators of frequent closed itemsets mined
  together with the closed itemsets. That would likely be an INCLUDE, but only if the paper
  does not post-process a given closed-itemset family. This cannot be decided without the text.

## 4. GENCLOSE: Tran, Truong, Le (EAAI 2014; ACIIDS-type chapter 2013)

- **Citations:** A. Tran, T. Truong, B. Le, "Simultaneous mining of frequent closed itemsets and
  their generators: Foundation and algorithm", Engineering Applications of AI 36 (2014) 64-80,
  doi 10.1016/j.engappai.2014.07.004. Also "An Approach for Mining Concurrently Closed Itemsets
  and Generators", in Advanced Computational Methods for Knowledge Engineering, Springer AISC
  479, 2013, doi 10.1007/978-3-319-00293-4_27.
- **Full text read:** None. Both are closed according to OpenAlex. ResearchGate 264561134 and
  Academia.edu 86781169 returned 403 or a Cloudflare challenge, and ScienceDirect and
  SpringerLink are paywalled.
- **Decision: UNVERIFIED.** It is likely an INCLUDE, as a level-wise miner of frequent
  generators together with closed itemsets, but this is not confirmed from the text.

## 5. CGT: Szathmáry, Ispány (FutureRFID 2014)

- **Citation:** L. Szathmary, M. Ispány, "CGT: a vertical miner for frequent equivalence classes
  of itemsets", Proc. 1st Int. Conf. and Exhibition on Future RFID Technologies, Eger, 2014,
  pp. 161-169, doi 10.17048/FutureRFID.1.2014.161.
- **Full text read:** https://publikacio.uni-eszterhazy.hu/29/1/FutureRFID.1.2014.161.pdf (publisher OA repository).
- **Output definition (Abstract, p. 161):** "a vertical, depth-first algorithm that outputs
  frequent generators (FGs) and their associated frequent closed itemsets (FCIs)." Sec. 3.5,
  p. 165: "CGT groups generators to their closure, thus the output of CGT is the list of
  frequent equivalence classes".
- **Input → output:** The input is a transaction dataset and min_supp. CGT traverses all
  frequent itemsets with Talky's reverse pre-order, so every subset of X is processed before
  X. A new frequent itemset becomes a generator when no generator in the row with the same
  tidset is a proper subset of it (Case 2, p. 166). The output is a hash table of rows, each
  holding a tidset, the generators, the closure and the support. The "eq. class members" field
  is "optional ... in the implementation it can be omitted" (p. 166). The paper gives no formal
  theorem; completeness is argued from the fact that CGT enumerates all frequent itemsets.
- **Condition:** Frequency.
- **Decision: INCLUDE.** The input is a database, and the output is all frequent generators
  paired with their closure and support. The optional non-generator member list can be turned
  off, and the rule needs only one setting that gives the complete family.
- **Implementation:** Java (java.util.HashMap) per footnote 2. No link was found in the paper.

## 6. Nabeshima, Iwanuma (JSAI 2020)

- **Citation:** T. Nabeshima (鍋島崇宏), K. Iwanuma (岩沼宏治), "極小生成子とその閉包アイテム集合のペアの高速列挙法
  / Fast Enumeration of Pairs of Minimal Generators and Their Closure Itemsets", Proc. 34th Annual
  Conf. of JSAI (JSAI2020), paper 2N4-OS-17a-04, 4 pp., doi 10.11517/pjsai.JSAI2020.0_2N4OS17a04.
  The second author is Koji Iwanuma; the brief listed only Nabeshima.
- **Full text read:**
  https://www.jstage.jst.go.jp/article/pjsai/JSAI2020/0/JSAI2020_2N4OS17a04/_pdf/-char/ja
  (Japanese). The PDF text layer is garbled, so the pages were rendered to images and read
  visually.
- **Output definition (Algorithm 2, p. 4):** "Input: トランザクションデータベース T = {t1,…,tm}, 最小支持度 ms /
  Output: T 上の，飽和集合 C とその極小生成子 M のペア ⟨C, M⟩ の集合 PAIRS". In English, the output is
  the set PAIRS of pairs ⟨closed itemset C, its minimal generator M⟩ on T. Sec. 1 says:
  "まずデータベースから直接極小生成子を求めると同時に，その閉包アイテム集合を高速に求めて". This means the
  algorithm mines minimal generators directly from the database. It does not start from
  enumerated closed itemsets, unlike the group's earlier bottom-up method [2].
- **Input → output:** The input is a transaction database and a minimum support ms. The
  algorithm runs a depth-first search over a suffix tree that contains frequent minimal
  generators only. Each node is tested exactly with CheckMinimalGenerator (Algorithm 1, using
  Theorem 2 with frq(P\{i}) > frq(P)). Recursion requires sup(P ∪ {e}) ≥ ms. Each generator's
  closure is computed through Theorem 3, clo(P) = P ∪ CI_P. Sec. 4.3, "閉包の列挙の完全性保証"
  (completeness guarantee of closure enumeration), fixes a completeness bug by ordering items
  by descending frequency. No formal proof of completeness for the whole output is given. The
  paper reports that the run on webdocs at ms = 0.10 was killed for lack of memory (Table 8).
- **Condition:** Frequency.
- **Decision: INCLUDE under the rule as written.** The input is a database, and the output is
  all frequent minimal generators, each paired with its closure. **Peer review:** the paper
  itself says nothing about review. JSAI annual-conference papers are short papers submitted
  without refereeing. Consistent with that, Iwanuma's researchmap lists the group's earlier
  JSAI annual-conference paper (2017) *without* the 査読有り (refereed) flag, while the
  IEEE papers carry the flag. Treat this paper as **not peer reviewed**. If the survey requires
  peer review, it drops out on that ground, not under RULE.md.

## 7. Iwanuma, Yajima, Yamamoto (IEEE CSDE 2021)

- **Citation:** K. Iwanuma, K. Yajima, Y. Yamamoto, "Enumerating Minimal Generators from Closed
  Itemsets – Toward Effective Compression of Negative Association Rules", IEEE CSDE 2021,
  doi 10.1109/csde53843.2021.9718380. researchmap marks it 査読有り (refereed).
- **Full text read:** None. OpenAlex lists it as closed, and no copy was found on IEEE
  Xplore (paywalled), researchmap, or the Yamamoto lab page.
- **Decision: UNVERIFIED.** It cannot be counted. A non-decisive hint comes from the same group's
  JSAI 2020 paper (item 6, Sec. 1 and Sec. 3), which describes their predecessor method [2] as
  searching "予め列挙された飽和集合それぞれについて，その極小生成子" (the minimal generators of each
  closed itemset enumerated in advance). That suggests the post-processing exclusion
  ("input is not a database"), which matches the title. This is not decided, because the full
  text was not read.

## 8. Yajima, Iwanuma, Yamamoto (IIAI-AAI 2022)

- **Citation:** K. Yajima, K. Iwanuma, Y. Yamamoto, "A Bottom-Up Enumeration Algorithm of Minimal
  Generators without Support Counting for Compressing Negative Association Rules", 12th IIAI-AAI
  2022, doi 10.1109/iiaiaai55812.2022.00135.
- **Full text read:** None. The paper is closed, with IEEE Xplore 9894557 paywalled.
- **Decision: UNVERIFIED.** Related Japanese SIG reports by the same authors are titled "飽和集合上の
  極小生成子抽出アルゴリズム" (minimal generators *on closed itemsets*, SIG-FPAI-108, 2019). Those
  titles hint at post-processing of closed itemsets, but this was not verified from the text.

## 9. Mochizuki, Iwanuma (IIAI-AAI 2024)

- **Citation:** S. Mochizuki, K. Iwanuma, "A Space-Saving Algorithm for Enumerating Minimal
  Generators in Negative Rule Mining", 16th IIAI-AAI 2024, pp. 689-692,
  doi 10.1109/iiai-aai63651.2024.00139.
- **Full text read:** None. The paper is closed, and the conference program only lists the
  title.
- **Decision: UNVERIFIED.**

## 10. Phan Luong (DaWaK 2002)

- **Citation:** V. Phan Luong, "The Closed Keys Base of Frequent Itemsets", DaWaK 2002, LNCS 2454,
  pp. 181-190, doi 10.1007/3-540-46145-0_18.
- **Full text read:** None. The paper is closed (SpringerLink paywall), with no repository copy
  in OpenAlex and none found on the web. A companion paper exists: "A Method for Computing
  Frequent Key and Closed Itemsets in One Phase", BDA 2002 (dblp conf/bda/Luong02). It may be
  the algorithmic one, but it was also not reachable.
- **Decision: UNVERIFIED.** Whether this paper is an algorithm or only a representation or rule
  base cannot be settled without the text.

## 11. SSMG-Miner: Dong, Jiang, Pei, Li, Wong (DASFAA 2005)

- **Citation:** G. Dong, C. Jiang, J. Pei, J. Li, L. Wong, "Mining Succinct Systems of Minimal
  Generators of Formal Concepts", DASFAA 2005, LNCS 3453, pp. 175-187, doi 10.1007/11408079_17.
- **Full text read:** https://www.cs.sfu.ca/~jpei/publications/ssmg-dasfaa05.pdf (author copy).
- **Problem definition (Sec. 2.2, p. 180):** "Given a transaction database TDB and a support
  threshold min_sup, the problem of mining the succinct system of minimal generators is to find
  a succinct system of minimal generators for all formal concepts C = (X, D) that sup(X) ≥ min_sup."
  Definition 3 (p. 179): "A succinct system of minimal generators ... consists of, for each formal
  concept C = (X, D), a representative minimal generator and a set of canonical minimal generators."
- **Input → output:** The input is a transaction database and min_sup. The output, from Fig. 4
  (SSMG-Miner), is "Succinct system of minimal generators for formal concepts in TDB". It is
  stored as tuples (MinList : Max, Count), so each concept's retained minimal generators come
  with the closed itemset and support. Non-minimal local generators are removed exactly in
  Sec. 3.4, and so are "clutters", meaning generators that contain a non-representative
  generator of a more general concept. Every output pattern is a true minimal generator, and the
  SSMG is a well-defined subfamily from which all minimal generators can be rebuilt. The SSMG
  is not unique, but all SSMGs have the same size (p. 180).
- **Condition:** Frequency plus succinctness. RULE.md explicitly allows "succinct systems" as a
  freeness-type subfamily condition.
- **Decision: INCLUDE.** The input is a database, and the output is an exact subfamily of
  minimal generators (the succinct system) paired with closures and support. No formal
  completeness theorem is given; correctness is argued through Lemmas 1-2 and Sec. 3.4.

## 12. Zhao, Chen, Tian (IEEE ICEICT 2023)

- **Citation:** L. Zhao, C. Chen, W. Tian, "Mining Frequent Closed Itemsets and Generators Over
  Uncertain Data", 6th IEEE ICEICT 2023, pp. 453-458, doi 10.1109/iceict57916.2023.10245860.
- **Full text read:** None. The paper is closed, with IEEE Xplore 10245860 paywalled.
- **Decision: UNVERIFIED.** It is not counted either way. If the text confirms the title's data
  model, it would be EXCLUDED under "data model differs: uncertain data". The search-snippet
  description also suggests a two-step method that first mines all probabilistic frequent
  itemsets. That snippet is third-party and is not used for the decision.

---

## Summary

| # | Algorithm | Decision | One-line reason |
|---|-----------|----------|-----------------|
| 1 | IncA-Gen / Magalice-A (Nehmé et al., ICFCA 2005) | INCLUDE (caveat) | Input is a context; outputs the exact complete mingen set of every (frequent) concept, attached to its intent; also outputs the lattice order (flip to EXCLUDE if extra structure is disallowed) |
| 2 | DPMiner (Li, Liu, Wong, KDD 2007) | INCLUDE | From a database, outputs all frequent equivalence classes [G, C] (all frequent generators with closures); the significance filter is optional |
| 3 | MG-CHARM (Vo, Le, CIE39 2009) | UNVERIFIED | No open full text (IEEE paywall; ResearchGate 403) |
| 4 | GENCLOSE (Tran, Truong, Le, EAAI 2014 / 2013) | UNVERIFIED | No open full text (Elsevier and Springer paywalls; ResearchGate and Academia 403) |
| 5 | CGT (Szathmáry, Ispány, FutureRFID 2014) | INCLUDE | OA full text: from a dataset, outputs all frequent generators grouped with closure and support (member list optional) |
| 6 | Nabeshima & Iwanuma (JSAI 2020) | INCLUDE (not peer reviewed) | Algorithm 2: input database T and ms, output all ⟨closure, minimal generator⟩ pairs; JSAI annual-conference paper, unrefereed |
| 7 | Iwanuma, Yajima, Yamamoto (CSDE 2021) | UNVERIFIED | No full text; title and the group's JSAI 2020 description suggest post-processing of closed itemsets (would be EXCLUDE) |
| 8 | Yajima, Iwanuma, Yamamoto (IIAI-AAI 2022) | UNVERIFIED | No full text (IEEE paywall) |
| 9 | Mochizuki, Iwanuma (IIAI-AAI 2024) | UNVERIFIED | No full text (IEEE paywall) |
| 10 | Closed Keys Base (Phan Luong, DaWaK 2002) | UNVERIFIED | No full text (Springer paywall); algorithm vs. rule base undecided |
| 11 | SSMG-Miner (Dong et al., DASFAA 2005) | INCLUDE | From a TDB, outputs an exact succinct system of minimal generators (a subfamily the rule allows) with closure and support |
| 12 | Zhao, Chen, Tian (ICEICT 2023) | UNVERIFIED | No full text; would be EXCLUDED (uncertain data model) if the text confirms the title |
