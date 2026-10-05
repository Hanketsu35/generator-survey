# Verification batch C: generator subfamilies, rare and stream (2026-10-05)

Rule applied: `results/litsearch/RULE.md`. A decision is made only when the full text was read.
Search routes tried for every paper: OpenAlex (`best_oa_location`, all `locations`), Semantic
Scholar API (mostly HTTP 429), WebSearch, publisher PDF links (ACM DL is behind a Cloudflare
challenge, and the IEEE, Springer and Elsevier copies are paywalled), CEUR-WS, HAL, arXiv API,
author pages, and Wayback CDX listings of author pages. No paywall was bypassed.
Downloaded texts are in the session scratchpad under `C/`.

---

## 1. Bykowski & Rigotti, disjunction-free sets (PODS 2001)

- **Citation:** A. Bykowski, C. Rigotti. "A condensed representation to find frequent patterns."
  PODS 2001, pp. 267-273. doi:10.1145/375551.375604.
- **Full text read:** No copy of the PODS paper was reachable. The ACM PDF returns a Cloudflare
  challenge or 403. OpenAlex lists only the DOI and CiteSeerX 10.1.1.25.5127, and CiteSeerX
  refused the connection and has no Wayback snapshot. Rigotti's archived home page
  (liris.cnrs.fr/~crigotti/_downloads/) has no pods01 file.
- **Related full text that was read (not the paper under decision):** the journal extension,
  A. Bykowski, C. Rigotti, "DBC: a condensed representation of frequent patterns for efficient
  mining", Information Systems 28 (2003). Author copy:
  https://web.archive.org/web/2010id_/http://liris.cnrs.fr/~crigotti/_downloads/is03.pdf .
  It says "This paper is a major extension of [17]" (Sec. 1), where [17] is the PODS'01 paper.
  - Def. 5 (Sec. 3): "a rule of the form Y ⇒ A ∨ A is a particular case of simple disjunctive
    rule". So every disjunction-free set is a generator, because Y ⇒ A means supp(Y) = supp(Y∪A).
  - Algorithm 4 (HLinEx), Sec. 6.1.1: "Output: FreqDFree(r, σ) and frequent itemsets of the
    negative border." Algorithm 5 (VLinEx) is the depth-first variant.
  - The negative-border part contains sets that are not generators. Example 4 gives
    {A,B} ⇒ C ∨ C, so {A,B,C} is in FreqBd− but {A,B} has the same support.
- **Decision: UNVERIFIED** (PODS 2001 full text not reachable). If the journal version is taken
  as evidence, HLinEx/VLinEx would be **EXCLUDE**, because the output (the DBC) also contains
  non-generator border sets, so it does not consist "only of minimal generators". Note that the
  algorithm is HLinEx, not "HLinHex".

## 2. Kryszkiewicz: disjunction-free generators (ICDM 2001), generalized disjunction-free generators (PAKDD 2002, with Gajek), k-disjunction-free borders (SAC 2004)

- **Citations:** M. Kryszkiewicz, "Concise representation of frequent patterns based on
  disjunction-free generators", ICDM 2001, pp. 305-312, doi:10.1109/ICDM.2001.989533.
  M. Kryszkiewicz, M. Gajek, "Concise representation of frequent patterns based on generalized
  disjunction-free generators", PAKDD 2002, LNCS 2336, pp. 159-171, doi:10.1007/3-540-47887-6_15.
  M. Kryszkiewicz, "Reducing borders of k-disjunction free representations of frequent patterns",
  SAC 2004, doi:10.1145/967900.968017.
- **Full text read:** none. OpenAlex marks all three as closed with no repository copy. IEEE,
  Springer and ACM are paywalled or Cloudflare-blocked, and ResearchGate returns 403. No
  author-page copy was found (Wayback CDX for ii.pw.edu.pl/~mkr has no PDFs).
- **Decision: UNVERIFIED** (all three). The questions of whether each paper proposes an
  algorithm and whether negated items are used cannot be settled without the texts.

## 3. Rule-free sets: RFS-Miner (Zhao, Lu, Wang, Yin, ICMLC 2003/2004) and HOPE-III (Lu, Computer Engineering and Science 2005)

- **Citations:** "Using rule-free sets to find frequent itemsets", Proc. ICMLC 2003 (IEEE),
  doi:10.1109/ICMLC.2003.1264434. "An optimized algorithm for mining frequent rule-free sets",
  Computer Engineering & Science, 2005 (no DOI found).
- **Full text read:** none. The IEEE copy is paywalled and OpenAlex and Semantic Scholar mark it
  closed. No open copy of the Chinese journal paper was found.
- **Decision: UNVERIFIED** (both). Whether rule-free sets are generators cannot be confirmed from
  the paper's own definition.

## 4. Szathmary, Napoli, Valtchev, "Towards rare itemset mining", ICTAI 2007

- **Citation:** L. Szathmary, A. Napoli, P. Valtchev. "Towards Rare Itemset Mining." ICTAI 2007,
  pp. 305-312, doi:10.1109/ICTAI.2007.30.
- **Full text read:** https://inria.hal.science/inria-00189424v1/file/szathmary-ictai07.pdf (HAL).
- **Definitions (Sec. 3):** "Definition 2 An itemset is a minimal rare itemset (mRI) if it is
  rare but all its proper subsets are frequent." "Definition 3 An itemset X is a (minimal or key)
  generator if it has no proper subset with the same support". "Proposition 1 All minimal rare
  itemsets are generators."

### 4a. Apriori-Rare
- **Quote (Sec. 4.1):** "Apriori-Rare is a slightly modified version of Apriori that stores the
  mRIs. Thus, whenever an i candidate survives the frequent i − 1 subset test, but proves to be
  rare, it is kept as an mRI." Sec. 4 also says: "Both algorithms described here produce the mRIs."
- **Output:** all minimal rare itemsets for min_supp. It enumerates all frequent itemsets
  internally, but the paper states its product as the mRIs.
- **All generators?** Yes, by Proposition 1. The search is exact and levelwise (Mannila-Toivonen
  negative border).
- **Decision: INCLUDE** (condition: rarity / minimal rare itemsets).

### 4b. MRG-Exp
- **Quote (Algorithm MRG-Exp box, Sec. 4.2):** "Description: finding minimal rare generators
  efficiently / Input: dataset plus min supp / Output: FGs plus mRGs".
- **Output:** all frequent generators and all minimal rare generators (= mRIs).
- **All generators?** Yes. Candidates whose i-subsets are not all frequent generators are pruned,
  and "If both values are different then the candidate is a true generator. Moreover, depending
  on its support, it is either a frequent generator or a minimal rare one, i.e., an mRI."
  Completeness follows from Property 1 (generators form a downset) and Proposition 2
  (generator iff supp ≠ min of immediate subsets).
- **Decision: INCLUDE** (frequent generators plus minimal rare itemsets, exact).

### 4c. Arima
- **Quote (Algorithm Arima box, Sec. 5):** "restoring all (non-zero) rare itemsets from mRIs /
  … / Output: all (non-zero) rare itemsets plus mZGs".
- **Output:** all non-zero rare itemsets plus the minimal zero generators. Most rare itemsets are
  not generators.
- **Decision: EXCLUDE.** The output does not consist only of minimal generators; the mRIs are
  only its input.

- **Implementation seen:** Coron platform (Java), used in the paper's experiments. SPMF also
  hosts a copy of the paper (philippe-fournier-viger.com/spmf/apriorirare.pdf).

## 5. MINIT, Haglin & Manning, DMIN 2007

- **Citation:** D. J. Haglin, A. M. Manning. "On Minimal Infrequent Itemset Mining." Proc. DMIN
  2007 (CSREA Press).
- **Full text read:** author copy http://mavdisk.mnsu.edu/haglin/papers/minit.pdf, retrieved via
  https://web.archive.org/web/20100612203350id_/http://mavdisk.mnsu.edu/haglin/papers/minit.pdf
  (PDF created April 2007). The Semantic Scholar PDF (pdfs.semanticscholar.org/4f4d/…) turned
  out to be the authors' talk slides, so it was not used for the decision.
- **Quote (Sec. I):** "τ-infrequent if |D(I)| < τ … minimal τ-infrequent if it is τ-infrequent
  and all of its proper subsets are τ-frequent". Algorithm 1 MINIT: "Returns: A listing of all
  MIIs for dataset D with cardinality less than maxc". Sec. III: "setting maxc to L will find
  all MIIs."
- **Output:** all minimal infrequent (minimal rare) itemsets, given maxc = L. The correctness
  properties are proved in Sec. IV (Theorems 2, 4 and 7, Lemmas 3 and 6).
- **All generators?** Yes. Every proper subset is frequent and so has strictly larger support
  (RULE.md, first fact).
- **Caveat:** the recursion works on the support sets D({i_j}). The paper does not discuss
  zero-support MIIs explicitly, and the authors' slides define infrequent as 0 < S(I) < τ, so in
  practice the output may be the non-zero mRIs. Under either reading it is a stated rarity
  condition.
- **Decision: INCLUDE** (minimal rare itemsets, exact; maxc = L).

## 6. Walky-G, Szathmary, Valtchev, Napoli, Godin, CLA 2012

- **Citation:** L. Szathmary, P. Valtchev, A. Napoli, R. Godin. "Efficient Vertical Mining of
  Minimal Rare Itemsets." CLA 2012, CEUR-WS Vol-972, pp. 269-280.
- **Full text read:** https://ceur-ws.org/Vol-972/paper23.pdf
- **Quote (Sec. 1):** "The main contribution of this paper is a new algorithm called Walky-G for
  mining minimal rare itemsets. The algorithm limits the traversal of the frequent zone to
  frequent generators only." Sec. 3: "When the algorithm stops, all frequent generators (and only
  frequent generators) are inserted in the IT-tree … all minimal rare itemsets have been found."
- **Output:** the mRIs (saveMri) and the frequent generators with their supports (saveFg,
  fgMap). Definitions 2 and 4 and Proposition 2 ("All minimal rare itemsets are generators [9]")
  are in Sec. 2.
- **All generators?** Yes. Caveat from Sec. 3: "Rare attributes with support 0 are not
  considered", so zero-support singletons are dropped.
- **Decision: INCLUDE** (minimal rare itemsets plus frequent generators, exact).
- **Implementation seen:** Coron (Java). SAMRIC (item 7) also uses Walky-G as a baseline.

## 7. Hidouri, Raddaoui, Jabbour, "Targeting Minimal Rare Itemsets from Transaction Databases", IJCAI 2023 (SAMRIC / k-MRI)

- **Citation:** A. Hidouri, B. Raddaoui, S. Jabbour. IJCAI 2023, pp. 2114-2121 (paper 235),
  doi:10.24963/ijcai.2023/235.
- **Full text read:** https://www.ijcai.org/proceedings/2023/0235.pdf
- **Quote (Def. 3, Sec. 3):** "X is called a k-minimal rare itemset (k-MRI, in short) if (i)
  ∀ Y ⊂ X s.t. |Y| ≤ k − 1, X \ Y is rare, and (ii) ∀Y ⊂ X s.t. |Y| ≥ k, X \ Y is frequent."
  "our model encompasses the minimal rare itemsets as a specific case by setting k to 1."
- **k = 1 check:** condition (i) only concerns Y = ∅ (X is rare). Condition (ii) requires every
  X \ Y with Y ≠ ∅, that is every proper subset, to be frequent. This is exactly Def. 1's minimal
  rare itemset, so 1-MRIs are mRIs and therefore generators. For k ≥ 2 a k-MRI has rare proper
  subsets that may have equal support, so it need not be a generator. One parameter setting is
  enough under the rule.
- **Exactness:** Sec. 3 says the encoding's models "correspond exactly to the set of k-minimal
  rare itemsets of D". Property 1 and Proposition 4 cover the encoding. Algorithm 1 (SAMRIC)
  enumerates all models with a modified MiniSAT. The splitting is disjoint and exhaustive
  (M(Φ) = ∪ M(Φ ∧ Γi)) and holds "without forgoing completeness" (Conclusion).
- **Decision: INCLUDE** (k = 1, SAMRIC: exact enumeration of the minimal rare itemsets).

## 8. MRI-CE, Song, Sun, Fournier-Viger, Wu, Information Sciences 665 (2024) 120392

- **Full text read:** none. The ScienceDirect copy is paywalled, OpenAlex marks it closed, and no
  author or repository copy was found. Only the abstract and an SPMF listing were seen, and
  neither is admissible.
- **Decision: UNVERIFIED.** The abstract describes a heuristic cross-entropy method, which would
  mean EXCLUDE (heuristic). That cannot be confirmed from the full text, and the algorithm is not
  counted either way.

## 9. NOV-mGCFSI, Huan Phan et al., "A Novel Algorithm for Mining Minimal Generators of Closed Frequent Significance Itemsets"

- **Citation:** H. Phan et al., 2021, Lecture Notes on Data Engineering and Communications Technologies (Springer), pp. 1768-1779,
  doi:10.1007/978-3-030-70665-4_191.
- **Full text read:** none. The Springer copy is paywalled and OpenAlex marks it closed.
- **Decision: UNVERIFIED.** Whether "significance" minimality is support-minimality cannot be
  determined.

## 10. FGC-Stream, Martin, Valtchev, Roux, ICDM 2021; KAIS 2023 extension

- **Citations:** T. Martin, P. Valtchev, L.-R. Roux, "FGC-Stream: a novel joint miner for
  frequent generators and closed itemsets in data streams", ICDM 2021, doi:10.1109/ICDM51629.2021.00053.
  "Mining frequent generators and closures in data streams with FGC-Stream", Knowl. Inf. Syst.
  2023, doi:10.1007/s10115-023-01852-3. The task text named "Vuillemin, Lefèvre" as authors; the
  publisher metadata names Martin, Valtchev and Roux.
- **Full text read:** none. IEEE and Springer are paywalled, OpenAlex marks both closed,
  ResearchGate returns 403, and there is no arXiv or HAL copy. The UQAM Archipel list shows only
  Martin's 2017 master's thesis.
- **Decision: UNVERIFIED** (both).

## 11. StreamGen, Gao & Wang, CIKM 2009

- **Citation:** C. Gao, J. Wang. "Efficient itemset generator discovery over a stream sliding
  window." CIKM 2009, pp. 355-364, doi:10.1145/1645953.1646000.
- **Full text read:** none. ACM DL is Cloudflare-blocked, OpenAlex marks it closed, and Jianyong
  Wang's publication page lists the paper without a PDF link.
- **Decision: UNVERIFIED.**

---

## Summary table

| Algorithm | Decision | One-line reason |
|---|---|---|
| Bykowski & Rigotti, disjunction-free sets (PODS 2001; HLinEx) | UNVERIFIED | PODS full text unreachable. The IS 2003 journal version (read) outputs the DBC, which adds non-generator negative-border sets, so it would be EXCLUDE |
| Kryszkiewicz, disjunction-free generators (ICDM 2001) | UNVERIFIED | No full text reachable (IEEE paywall, no repository copy) |
| Kryszkiewicz & Gajek, generalized disjunction-free generators (PAKDD 2002) | UNVERIFIED | No full text reachable (Springer paywall) |
| Kryszkiewicz, k-disjunction-free borders (SAC 2004) | UNVERIFIED | No full text reachable (ACM blocked) |
| RFS-Miner (rule-free sets, ICMLC 2003) | UNVERIFIED | No full text reachable |
| HOPE-III (Comp. Eng. & Sci. 2005) | UNVERIFIED | No full text reachable |
| Apriori-Rare (ICTAI 2007) | INCLUDE | Outputs exactly the minimal rare itemsets, which Prop. 1 shows are generators |
| MRG-Exp (ICTAI 2007) | INCLUDE | "Output: FGs plus mRGs", an exact levelwise enumeration of generators |
| Arima (ICTAI 2007) | EXCLUDE | Outputs all non-zero rare itemsets plus mZGs, mostly non-generators |
| MINIT (DMIN 2007) | INCLUDE | Author copy read: returns all minimal τ-infrequent itemsets (maxc = L) with correctness properties proved |
| Walky-G (CLA 2012) | INCLUDE | Exact depth-first enumeration of all mRIs plus frequent generators |
| SAMRIC / k-MRI (IJCAI 2023) | INCLUDE | k = 1 gives exactly the mRIs, with exact and complete SAT model enumeration |
| MRI-CE (Inf. Sci. 2024) | UNVERIFIED | Paywalled. The abstract says heuristic, which would be EXCLUDE, but this was not checked in the full text |
| NOV-mGCFSI (LNDECT 2021) | UNVERIFIED | Paywalled, so the significance-based minimality notion cannot be checked |
| FGC-Stream (ICDM 2021 / KAIS 2023) | UNVERIFIED | Both full texts paywalled, with no open copy |
| StreamGen (CIKM 2009) | UNVERIFIED | ACM full text unreachable, with no open copy |
