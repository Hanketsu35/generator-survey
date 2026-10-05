# Full-text verification, batch E (high-utility and graph generators)

Rule applied: `RULE.md` (2026-10-05). For utility mining, an algorithm counts only if
its output is **support-minimal** generators (no proper subset, among *all* itemsets,
with equal support) under a utility condition on the generator or on its closure, mined
from a database, exactly and completely. A "generator" defined as minimal only among
the high-utility (or frequent-high-utility) itemsets is not a support-minimal generator:
an itemset can have a proper subset with the same support that fails the utility test,
and it is then output although it is not a minimal generator. This is the ground on
which RULE.md already excludes HUCI-Miner-Generators.

Verified 2026-10-05. Local copies of the full texts read are in the session scratchpad
(`.../scratchpad/E/`). Paywalled publisher pages gave the abstract only and were not used
for decisions.

---

## 1a. HUG-Miner

- **Citation.** P. Fournier-Viger, C.-W. Wu, V. S. Tseng. Novel concise representations
  of high utility itemsets using generator patterns. ADMA 2014, LNCS 8933, pp. 30-43.
  doi:10.1007/978-3-319-14717-8_3.
- **Full text read.** https://www.philippe-fournier-viger.com/ADMA2014_GHUIMiner_Generators_of_high_utility_itemsets.pdf
  (author copy, 14 pp., same pagination as LNCS). An extended 26-page author version is
  at https://www.philippe-fournier-viger.com/ADMA2014_generator_high_utility_itemsets.pdf.
- **Generator definition (Sect. 2.2, p. 34).** "an itemset X is a generator (a.k.a key
  pattern or minimal pattern) iff there is no itemset Y such that Y ⊂ X and sup(X) = sup(Y)"
  (support-based, over all itemsets).
- **Output definition (Sect. 2.3, p. 35).** "We use the term High Utility Generator
  (HUGs) to refer to those that are HUIs". HUG-Miner (Sect. 3, p. 40) is "a variation of
  GHUI-Miner named HUG-Miner to mine only HUGs".
- **Input / output.** Input: transaction database with utilities, minutil. Output: all
  generators X (support-minimal) with u(X) ≥ minutil.
- **Condition.** Utility condition on the generator itself.
- **Completeness.** Sect. 3, p. 39: "it can be easily seen that this main procedure is
  correct and complete for finding GHUIs" (proof not given; claim stated).
- **Decision: INCLUDE.** Output is exactly the support-minimal generators that are HUIs;
  allowed condition "utility condition on the generator".
- **Implementation.** SPMF, "HUG-Miner" (https://www.philippe-fournier-viger.com/spmf/HUG-Miner.php,
  "This is the original implementation of HUG-Miner").

## 1b. GHUI-Miner

- **Citation.** Same paper as 1a.
- **Full text read.** Same URL as 1a.
- **Output definition (Sect. 2.3, p. 35).** "some equivalence classes contain at least one
  HUI. We name generators appearing in these equivalence classes Generators of High
  Utility Itemsets (GHUIs)."
- **Input / output (Algorithm 1, p. 37).** "input: D: a transaction database, minutil
  ..., CHUIs: the set of CHUIs; output: the set of GHUIs". The CHUIs "need to be first
  mined using an algorithm for mining CHUIs (CHUD [14] in our implementation)" (p. 37).
  GHUI-Miner then scans D, builds utility-lists and enumerates generator patterns in D;
  the CHUIs are used only for pruning and closure look-up.
- **Condition.** Utility condition on the closure (the generator's equivalence class
  contains a HUI, i.e. its closure is a CHUI, Property 7).
- **Decision: INCLUDE** (allowed condition "utility condition ... on its closure").
  *Caveat for the caller:* the algorithm takes the CHUI family as an extra input. It is
  not a post-processor of that family (it mines generators from D itself, and the
  CHUIs come from D by CHUD in the same pipeline), so I did not apply the
  "input is not a database" exclusion. If the survey reads that clause strictly as
  "any given family of closed itemsets as input", flip this to EXCLUDE.
- **Implementation.** SPMF "GHUI-Miner" (spmf/GHUIMiner.php).

## 2. HUCI-Miner (generators)

- **Citations.** (a) J. Sahoo, A. K. Das, A. Goswami. An algorithm for mining high
  utility closed itemsets and generators. arXiv:1410.2988, 2014. (b) Same authors, An
  efficient approach for mining association rules from high utility itemsets. Expert
  Systems with Applications 42(13), 2015 (journal version; not open access, not read).
- **Full text read.** https://arxiv.org/pdf/1410.2988 (18 pp.).
- **The paper's own definition of generator: relative to the HUI family, not
  support-minimal.** Sect. 4.1.1, p. 9, Definition 13: "An itemset X is a high utility
  generator, if it is a high utility itemset and there exists no proper high utility
  subset Z such that supp(Z) = supp(X)." Sect. 4.1.2, p. 9: "Throughout this paper we
  apply the second approach and after onwards we mean the generator means the high
  utility generator." The paper explicitly considers and rejects the support-minimal
  version (Definition 12, "no proper subset Z of X such that supp(Z) = supp(X). Moreover,
  X must satisfy the utility constraints").
  Theorem 4 (p. 10) gives AFE as a "generator" although its subset AE has the same
  support, so the paper itself acknowledges outputs that are not support-minimal.
- **Input / output.** Algorithm 1 (p. 10): "Input: HUI: {H1, ..., Hmax} ... Output: High
  utility closed itemsets with their generators"; line 2 calls FHM on D, and the
  generators are computed from the HUI set ("A post-processing algorithm, called the
  HUCI-Miner", abstract; "after extracting all high utility itemsets, the closure
  property is applied", p. 9).
- **Decision: EXCLUDE** on two clauses: (i) minimality is not support-minimality
  (Definition 13 is minimal only among HUIs); (ii) the generator step post-processes a
  given family of HUIs. Consistent with the oracle audit (0 of 2,002 outputs
  support-minimal). ESWA 2015 not read; the decision rests on the authors' arXiv text.

## 3. MFG-HUI

- **Citation.** H. Duong, T. Tran, T. Truong, B. Le. MFG-HUI: an efficient algorithm for
  mining frequent generators of high utility itemsets. IUKM 2023, LNCS 14376,
  pp. 279-290 (chapter 23). doi:10.1007/978-3-031-46781-3_23.
- **Full text.** Not reachable: Springer chapter is paywalled (only abstract/references
  shown), Semantic Scholar/OpenAlex list no OA copy, ResearchGate blocked by CAPTCHA.
- **Decision: UNVERIFIED.** (Abstract only: "frequent generators of high utility
  itemsets (FGHUIs)", "eliminate non-generator high utility branches". Not used for the
  decision. Note: the same group's later full texts, items 5 below, define the analogous
  "generator" relative to the FHUOI family, which would exclude it; this must be checked
  in the MFG-HUI text itself.)

## 4. CG-FHAUI

- **Citation.** H. Duong, T. Truong, B. Le, P. Fournier-Viger. CG-FHAUI: an efficient
  algorithm for simultaneously mining succinct pattern sets of frequent high average
  utility itemsets. Knowledge and Information Systems 66, 5239-5280, 2024.
  doi:10.1007/s10115-024-02121-7.
- **Full text.** Not reachable (Springer paywall; S2 status CLOSED; ResearchGate CAPTCHA).
- **Decision: UNVERIFIED.** Whether its "generators of FHAUIs (GFHAUIs)" are defined on
  support over all itemsets or only among FHAUIs could not be read.

## 5. Gen-FHUOIM and its 2025 journal versions

### 5a. Gen-FHUOIM (CCIOT 2024)

- **Citation.** H. Duong, T. Truong. An efficient algorithm for mining frequent high
  utility occupancy generators. Proc. 9th Int. Conf. on Cloud Computing and Internet of
  Things (CCIOT 2024). doi:10.1145/3704304.3704318.
- **Full text.** Not reachable (ACM DL 403/closed; S2 CLOSED; ResearchGate CAPTCHA).
- **Decision: UNVERIFIED.**

### 5b. GFHUOI-Miner (Dalat University Journal of Science 2025)

- **Citation.** Duong Van Hai, Hoang Minh Tien, Truong Chi Tin. Mining concise
  representations of frequent high-utility occupancy itemsets using generator patterns.
  Dalat University Journal of Science 15(3), 149-170, 2025.
  doi:10.37569/dalatuniversity.15.3.1373(2025).
- **Full text read.** https://tckh.dlu.edu.vn/index.php/tckhdhdl/article/download/1373/657 (22 pp., OA).
- **Definition (Def. 6, p. 153).** "A is called a generator of FHUOI (GFHUOI) if no
  FHUOI is a proper subset of A and none share identical support", i.e.
  GFHUOI = {A ∈ FHUOI | ∄B ∈ FHUOI: B ⊂ A ∧ supp(B) = supp(A)}.
- **Problem statement (p. 153-154).** "With a given QTDB D′ and two user-defined positive
  thresholds, muo and ms, the current study aims to mine the GFHUOI set of all GFHUOIs."
- **Why not support-minimal.** Minimality is checked only against subsets that are
  themselves FHUOIs; utility occupancy is not monotone in an equivalence class (the
  paper's own Example 3: bc is an FHUOI but b is not), so an output can have a non-FHUOI
  proper subset with the same support.
- **Decision: EXCLUDE** (minimality relative to the FHUOI family, not support-minimal;
  same ground as HUCI-Miner).

### 5c. CGFHUOI-Miner (MIC Journal on ICT Research 2025)

- **Citation.** T. Hoang, L. Huynh, H. Duong, T. Truong. Efficient mining of concise
  patterns for frequent high-utility occupancy itemsets using extended pruning
  strategies. Journal on Information Technologies & Communications (MIC), Vol. 2025,
  No. 2. doi:10.32913/mic-ict-research.v2025.n2.1360.
- **Full text read.** https://ictmag.ictvietnam.vn/ict/article/download/1360/642/ (OA PDF).
- **Definition (Def. 10, p. 113).** "X is referred to as a generator of frequent high
  utility occupancy itemset (GFHUOI) if no FHUOI exists as a proper sub-itemset of X
  with the same support." The paper cites Gen-FHUOIM [8] and GFHUOI-Miner [9] as mining
  this same GFHUOI set (p. 112).
- **Output.** CGFHUOI-Miner mines CFHUOIs and GFHUOIs together from the QTDB;
  MaxFHUOI-Miner mines maximal FHUOIs only.
- **Decision: EXCLUDE** (same relative definition as 5b).
- Note for 5a: this full text (by the same authors) states that Gen-FHUOIM mines the
  GFHUOI set of Def. 10, which would exclude it, but under the evidence standard 5a
  stays UNVERIFIED until its own text is read.

## 6. Mai and Nguyen 2017 (LHUCI-Miner)

- **Citation.** T. Mai, L. T. T. Nguyen. An efficient approach for mining closed high
  utility itemsets and generators. Journal of Information and Telecommunication 1(3),
  2017. doi:10.1080/24751839.2017.1347392 (gold OA, CC BY).
- **Full text read.** https://www.tandfonline.com/doi/full/10.1080/24751839.2017.1347392
  (HTML full text, retrieved through the r.jina.ai reader because the site's bot check
  blocks curl; the article is open access).
- **Definition (Definition 10).** "An itemset X is called a HUI generator or HUG or
  generator if it is a HUI and no any subset Z of X has supp(X) = supp(Z)."
- **Problem statement.** "Given a set of HUIs which are mined from transaction database D
  with a user-specified minimum utility threshold (min-util), the problem statement is
  to discover all CHUIs and their HUGs from HUIs." The HUIL lattice is built "from mined
  HUIs" (FHIM output) and IsGenerator flags are set only between HUI nodes.
- **Decision: EXCLUDE** (input is not a database: post-processes a given family of HUIs).

## 7. Merugula and Rao 2020

- **Citation.** S. Merugula, M. V. P. Chandra Sekhara Rao. An integrated approach for
  mining closed and generator high utility itemsets. Int. J. Knowledge-based and
  Intelligent Engineering Systems 24(1), 2020. doi:10.3233/KES-200026.
- **Full text.** Not reachable (IOS Press/SAGE paywall; no OA copy in S2/OpenAlex/CORE).
- **Decision: UNVERIFIED.**

## 8. Tran, Duong, Truong, Le 2023 (EAAI)

- **Citation.** T. Tran, H. Duong, T. Truong, B. Le. Efficient mining of concise and
  informative representations of frequent high utility itemsets. Engineering
  Applications of Artificial Intelligence 126, 107111, 2023.
  doi:10.1016/j.engappai.2023.107111.
- **Full text.** Not reachable (Elsevier paywall; S2 CLOSED; ResearchGate CAPTCHA).
  The search-result abstract mentions frequent generators of HUIs (FGHUIs), and the
  Dalat paper (5b, p. 150) cites it for "the generators of FHUIs", but neither is
  admissible evidence.
- **Decision: UNVERIFIED.**

## 9. Applied Intelligence 2026 (compact high average utility patterns)

- **Citation.** Tran, Duong, Truong, Le (DBLP journals/apin/TranDTL26). Efficient mining
  of compact high average utility patterns using the tightest weak lower bound. Applied
  Intelligence, 2026. doi:10.1007/s10489-026-07130-3.
- **Full text.** Not reachable (Springer paywall). The abstract names only "closed
  FHAUIs (CFHAUIs) ... and maximal FHAUIs (MFHAUIs)" and the algorithm MC-FHAUIM, so it
  probably mines no generators, but this is abstract-level only.
- **Decision: UNVERIFIED** (would be EXCLUDE if the full text confirms no generators).

## 10. FOGGER and other graph-generator miners

### 10a. FOGGER

- **Citation.** Z. Zeng, J. Wang, J. Zhang, L. Zhou. FOGGER: an algorithm for graph
  generator discovery. EDBT 2009, pp. 517-528. doi:10.1145/1516360.1516421.
- **Full text read.** https://openproceedings.org/2009/conf/edbt/ZengWZZ09.pdf
- **Definition (Sect. 2.1, p. 518).** "if ∄ p′′ ∈ [p] such that p′′ < p′, p′ is a minimal
  pattern in [p] and is called a generator", where [p] is the class of patterns with the
  same supporting graphs (same support set).
- **Problem statement (Sect. 2.1, p. 518).** "Given an input graph database D and a
  minimum support threshold min_sup, we study the problem of mining the complete set of
  graph generators which are frequent and also connected."
- **Output.** All frequent connected subgraph generators. Candidates that turn out to
  have a proper subgraph with the same support are removed from the result set R
  (Sect. 3.3.1, p. 521-522), so only generators are output; enumeration is exact
  (DFS-code tree, pruning only of branches with no generators).
- **Decision: INCLUDE**, with a note: RULE.md names the sub-pattern relation for itemsets
  and sequences only; FOGGER uses the subgraph relation, which fits the general
  definition ("a pattern none of whose proper sub-patterns has the same support") and is
  not in the excluded pattern languages. If the survey is restricted to itemsets and
  sequences, record it as out of scope rather than excluded.
- **Implementation.** None seen.

### 10b. Other graph candidates (not verified; reported for follow-up)

The FOGGER paper (Sect. 5, p. 526) says "no attention has been paid to the discovery of
frequent graph generators" before it. Searches (web, arXiv) found no later algorithm
whose stated output is graph generators. Related but likely non-qualifying candidates:

- **Minimal infrequent subgraphs (MIFS)** in incremental frequent subgraph mining
  (Abdelhamid et al., IncGM+, VLDB 2017; US patent 10409828). Minimal infrequent
  subgraphs are generators by the RULE.md argument, but there they appear to be an
  internal pruning structure, not the output, and support is the single-graph MNI
  measure. Not read; likely EXCLUDE (intermediate only).
- **Minimal distinguishing subgraph patterns**, MDGP-Mine (Zeng, Wang, Zhou et al.,
  "Efficient mining of minimal distinguishing subgraph patterns from graph databases",
  PAKDD 2008) and **minimal contrast subgraphs** (Ting and Bailey, SDM 2006, FOGGER
  ref. [20]). Minimality is on a contrast condition, not equal support. Not read;
  likely EXCLUDE.

---

## Summary

| Algorithm | Decision | One-line reason |
|---|---|---|
| HUG-Miner (Fournier-Viger et al., ADMA 2014) | INCLUDE | Outputs all support-minimal generators that are HUIs, mined from the database (Sect. 2.3, p. 35). |
| GHUI-Miner (same paper) | INCLUDE (caveat) | All support-minimal generators whose class/closure holds a HUI; mines D but also takes the CHUI set (from CHUD) as an extra input. |
| HUCI-Miner generators (Sahoo et al., arXiv 1410.2988 / ESWA 2015) | EXCLUDE | Def. 13: minimal only among HUI subsets, not support-minimal; post-processes FHM's HUIs. |
| MFG-HUI (Duong et al., IUKM 2023) | UNVERIFIED | No open full text. |
| CG-FHAUI (Duong et al., KAIS 2024) | UNVERIFIED | No open full text. |
| Gen-FHUOIM (Duong, Truong, CCIOT 2024) | UNVERIFIED | No open full text; later papers by the same authors say it mines the relative GFHUOI set. |
| GFHUOI-Miner (Dalat Univ. J. Sci. 2025) | EXCLUDE | Def. 6: minimal only among FHUOI subsets, so not support-minimal. |
| CGFHUOI-Miner (MIC J. ICT Research 2025) | EXCLUDE | Def. 10: same relative GFHUOI definition. |
| LHUCI-Miner (Mai, Nguyen, JIT 2017) | EXCLUDE | Problem input is "a set of HUIs"; it post-processes HUIs. |
| Merugula, Rao (KES 2020) | UNVERIFIED | No open full text. |
| Tran et al. (EAAI 2023) | UNVERIFIED | No open full text. |
| MC-FHAUIM (Applied Intelligence 2026) | UNVERIFIED | No open full text; abstract mentions only closed and maximal FHAUIs. |
| FOGGER (Zeng et al., EDBT 2009) | INCLUDE (scope note) | Complete set of frequent connected subgraph generators from a graph database; subgraph relation not named in RULE.md. |
| Other graph candidates (MIFS/IncGM+, MDGP-Mine, minimal contrast subgraphs) | not verified | Leads only; likely intermediate or contrast-minimal, so likely EXCLUDE. |
