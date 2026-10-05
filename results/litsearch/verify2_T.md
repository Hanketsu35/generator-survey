# Full-text verification, batch T (2026-10-05)

Rule applied: `RULE.md`, including Amendments 1-3 (generators need only be an
identified part of the output; peer review required). All PDFs were read with
`pdftotext` (with `-layout` and, for the two-column IEEE files whose layout text
was garbled, also without it). Quotes are short and verbatim, with location.

---

## 1. MG-CHARM

- **Citation:** B. Vo, B. Le, "Fast algorithm for mining minimal generators of
  frequent closed itemsets and their applications," Proc. 39th Int. Conf. on
  Computers & Industrial Engineering (CIE39), IEEE, 2009, pp. 1407-1411.
- **File:** `Fast_algorithm_for_mining_minimal_generators_of_frequent_closed_itemsets_and_their_applications.pdf`
  (the copy `Fast_algorithm_for_mining_minimal_generators_of_fr.pdf` was not
  re-read separately).
- **Quote (Sec. 3.1, Algorithm 1, p. 1409):** "Input: The database D and support
  threshold minSup / Output: all FCI satisfy minSup and their mG".
  Definition (Sec. 2.3, p. 1408): X' in G(X) "is a minimal generator if it has no
  subset in G(X)", where a generator satisfies X' ⊆ X and σ(X) = σ(X').
- **Input:** transaction database + minSup.
- **Output:** all frequent closed itemsets, each with its set of minimal generators.
- **Condition:** frequency (generators of frequent closed itemsets = frequent generators).
- **Support-minimal?** Yes by definition (no proper subset with equal support);
  completeness claimed in Lemma 2 (Sec. 3.2), minimality of joined generators in
  Lemma 1(5.2).
- **Caveat (not decisive under the rule):** Lemma 1(5) forms generators of
  Xi ∪ Xj as pairwise unions of mGs without a subset-support check. GENCLOSE's
  authors (EAAI 2014, p. 68) show that a union of two generators need not be a
  generator (eb ∪ eh = ebh, not a generator) and cite MG-CHARM as using such
  joins. A correctness audit of an MG-CHARM implementation against the oracles
  would be worthwhile.
- **Peer review:** IEEE conference proceedings (CIE39).
- **Decision: INCLUDE.**

## 2. GENCLOSE

- **Citation:** A. Tran, T. Truong, B. Le, "Simultaneous mining of frequent
  closed itemsets and their generators: Foundation and algorithm," Engineering
  Applications of Artificial Intelligence 36 (2014) 64-80,
  doi:10.1016/j.engappai.2014.07.004.
- **File:** `1-s2.0-S0952197614001717-main.pdf`
- **Quote (Sec. 1, p. 65):** "given a transaction database and a minimum support
  threshold, the task is to find all frequent closed itemsets together with
  their generators." Sec. 3.3 (p. 73), "Correctness and completeness": "it
  correctly lists all and only the generators."
- **Input:** transaction database + minsupp.
- **Output:** all frequent closed itemsets with all their generators (lattice LCG).
- **Condition:** frequency.
- **Support-minimal?** Yes. Generator defined (Sec. 2, p. 66) as G with
  h(G) = h(A) and h(G') ⊂ h(G) for every nonempty proper subset G'; Consequence 2
  shows equivalence with the support-based definition. Exactness by Theorem 1
  (necessary and sufficient condition) and Theorem 2.
- **Peer review:** Elsevier journal.
- **Decision: INCLUDE.**

## 3. Iwanuma, Yajima, Yamamoto (CSDE 2021)

- **Citation:** K. Iwanuma, K. Yajima, Y. Yamamoto, "Enumerating Minimal
  Generators from Closed Itemsets – Toward Effective Compression of Negative
  Association Rules," 2021 IEEE Asia-Pacific Conf. on Computer Science and Data
  Engineering (CSDE), doi:10.1109/CSDE53843.2021.9718380.
- **File:** `Enumerating_Minimal_Generators_from_Closed_Itemsets__Toward_Effective_Compression_of_Negative_Association_Rules.pdf`
- **Quote (Sec. III-B):** "we assume that we use a state-of-the-art tool for
  enumerating all closed itemsets such as LCM [7]. In this paper, we restrict the
  focus of our research to an algorithm that extracts all minimal generators from
  given closed itemsets." Algorithm 1 (and Algorithm 3): "Input: CIS is a family
  of pairs ⟨Xi, fi⟩ ... each Xi is a closed itemset".
- **Input:** a given family of closed itemsets with supports (Algorithms 1-2 also
  use a vertical database for support counting; Algorithm 3 uses none).
- **Output:** all pairs ⟨Mj, i⟩ with Mj a minimal generator of closed Xi
  (MCR(D, msP): closed X with sup ≥ msP).
- **Condition:** frequency of the closure (msP).
- **Support-minimal?** Yes (standard definition). Patterns are positive itemsets;
  negation only appears in the downstream application.
- **Decision: EXCLUDE** - input clause: post-processes a given family of closed
  itemsets (the paper's stated scope).

## 4. Yajima, Iwanuma, Yamamoto (IIAI-AAI 2022)

- **Citation:** K. Yajima, K. Iwanuma, Y. Yamamoto, "A Bottom-Up Enumeration
  Algorithm of Minimal Generators without Support Counting for Compressing
  Negative Association Rules," 12th IIAI Int. Congress on Advanced Applied
  Informatics (IIAI-AAI), IEEE, 2022, pp. 665-?, doi:10.1109/IIAIAAI55812.2022.00135.
- **File:** `A_Bottom-Up_Enumeration_Algorithm_of_Minimal_Generators_without_Support_Counting_for_Compressing_Negative_Association_Rules.pdf`
- **Quote (Abstract / Algorithm 1, Sec. III):** "a bottom-up efficient algorithms
  for enumerating minimal generators from given closed itemsets." Algorithm 1:
  "Input: CIS is a family of pairs ⟨Xk, fk⟩ ... each Xk is a closed itemset".
- **Input:** a given family of closed itemsets with supports (no database access).
- **Output:** all pairs ⟨Mj, i⟩, Mj a minimal generator of Xi, for every Xi in CIS.
- **Condition:** whatever family of closed itemsets is supplied.
- **Support-minimal?** Yes (standard definition).
- **Decision: EXCLUDE** - input clause: input is a pre-mined family of closed itemsets.

## 5. Mochizuki, Iwanuma (IIAI-AAI 2024)

- **Citation:** S. Mochizuki, K. Iwanuma, "A Space-Saving Algorithm for
  Enumerating Minimal Generators in Negative Rule Mining," 16th IIAI Int.
  Congress on Advanced Applied Informatics (IIAI-AAI), IEEE, 2024, p. 689ff,
  doi:10.1109/IIAI-AAI63651.2024.00139.
- **File:** `A_Space-Saving_Algorithm_for_Enumerating_Minimal_Generators_in_Negative_Rule_Mining.pdf`
- **Quote (Abstract):** "we propose a method of enumerating minimal generators
  from a closed item set using a bucket-type membership table in a vertical
  format, instead of a hash table." The generator test (Theorem 1, Corollary 1,
  Sec. III) decides generatorhood from the membership table of closed itemsets.
- **Input:** the closed itemsets (as a CID membership table); same pipeline as
  [6] = item 3 ("first extract all frequent closed sets from D", Sec. II).
- **Output:** pairs ⟨closed X, minimal generator Y⟩.
- **Condition:** frequency of the closure.
- **Support-minimal?** Yes (standard definition).
- **Decision: EXCLUDE** - input clause: post-processes given closed itemsets.

## 6. Zhao, Chen, Tian (ICEICT 2023)

- **Citation:** L. Zhao, C. Chen, (Tian), "Mining Frequent Closed Itemsets and
  Generators over Uncertain Data," 2023 IEEE 6th Int. Conf. on Electronic
  Information and Communication Technology (ICEICT),
  doi:10.1109/ICEICT57916.2023.10245860.
- **File:** `Mining_Frequent_Closed_Itemsets_and_Generators_Over_Uncertain_Data.pdf`
- **Quote (Sec. III, Definition 10):** "Given an uncertain dataset UTD, for a
  probabilistic frequent item set X, X is called frequent generator if there is
  no direct true subset Y of X such that PrF(X) = PrF(Y)."
- **Input:** uncertain (probabilistic) transaction database; two steps: mine all
  probabilistic frequent itemsets, then extract closed itemsets and generators.
- **Output:** probabilistic frequent closed itemsets and generators.
- **Condition:** frequent probability ≥ threshold.
- **Support-minimal?** No: minimality is on frequent probability, not support, and
  only immediate subsets are compared.
- **Decision: EXCLUDE** - data-model clause (uncertain data); also minimality
  not defined on support.

## 7. GrAFCI+

- **Citation:** M. Ledmi, S. Zidat, A. Hamdi-Cherif, "GrAFCI+ A fast
  generator-based algorithm for mining frequent closed itemsets," Knowledge and
  Information Systems 63 (2021) 1873-1908, doi:10.1007/s10115-021-01575-3.
- **File:** `s10115-021-01575-3.pdf`
- **Quote (Algorithm 1, p. 1887):** "Output: FG and FC are respectively the sets
  of frequent generators and closed itemsets". Corollary 4.4 (Sec. 4.4.5,
  Completeness): "We want to prove that GrAFCI+ produces all FCIs and all FGIs
  and nothing else."
- **Input:** transaction database (conditional databases / Gr-tree) + minsup.
- **Output:** FC (frequent closed itemsets) and FG (frequent generators), both
  identified outputs; experiments report an FG column (Sec. 5).
- **Condition:** frequency.
- **Support-minimal?** Yes. Definition 3.4: a generator if "none of its subsets
  has a support equal to the support of x"; line 10 of Algorithm 1 checks all
  proper subsets. Empty set counted as a generator.
- **Key question answered:** generators are output, not only internal (Algorithm 1
  output and Corollaries 4.3-4.4).
- **Peer review:** Springer journal.
- **Decision: INCLUDE** (via Amendment 1: generators are an identified part of the output).

## 8. Kryszkiewicz (SAC 2004)

- **Citation:** M. Kryszkiewicz, "Reducing borders of k-disjunction free
  representations of frequent patterns," Proc. 2004 ACM Symposium on Applied
  Computing (SAC '04), pp. 559-563, doi:10.1145/967900.968017.
- **File:** `967900.968017.pdf`
- **Quote (Sec. 3.1, Problem Statement, p. 561):** "Our task is to find a minimal
  subset [of a border group] ... such that for every itemset X in [the _like
  group] we can determine if it belongs to [the group] or not". Conclusion: a
  "method of reducing borders of representations of frequent patterns".
- **Input:** an already computed k-disjunction-free representation (FDFree_k
  with supports and its border groups); no database mining step is proposed.
- **Output:** reduced border groups G' and a partition M' of FDFree_k
  (Unsplit, SIG sets) that allows reconstruction.
- **Condition:** n/a; experiments only for k = ∞.
- **Support-minimal?** FDFree_k ⊆ DFree_1 = generators (Sec. 2.4: "DFree1 equals
  all generators"), patterns are plain itemsets (disjunctions only appear in rules,
  no negated items). But the paper proposes no algorithm that enumerates FDFree_k;
  it reduces borders of a given representation.
- **Decision: EXCLUDE** - no algorithm enumerating generators from a database
  (generators are not produced by the proposed method; input is a pre-computed
  representation).

---

## Summary

| Algorithm | Decision | Reason |
|---|---|---|
| MG-CHARM (Vo & Le, CIE39 2009) | INCLUDE | Input database+minSup; output all FCIs with all their mGs (Alg. 1, Lemma 2); caveat: unchecked union joins, audit advised |
| GENCLOSE (Tran, Truong, Le, EAAI 2014) | INCLUDE | From database outputs all frequent closed itemsets with all generators; "all and only the generators" proved |
| Iwanuma, Yajima, Yamamoto (CSDE 2021) | EXCLUDE (input) | Input is a given family of closed itemsets (e.g. from LCM) |
| Yajima, Iwanuma, Yamamoto (IIAI-AAI 2022) | EXCLUDE (input) | Algorithm input is a family of closed itemsets, no database |
| Mochizuki, Iwanuma (IIAI-AAI 2024) | EXCLUDE (input) | Enumerates mGs from closed itemsets via a CID membership table |
| Zhao, Chen, Tian (ICEICT 2023) | EXCLUDE (data model) | Uncertain data; minimality on frequent probability, not support |
| GrAFCI+ (Ledmi et al., KAIS 2021) | INCLUDE | Alg. 1 outputs FG and FC; Cor. 4.4 claims all FGIs; generators are output, not only internal |
| Kryszkiewicz (SAC 2004) | EXCLUDE (no enumeration algorithm / input) | Border-reduction method on a given k-disjunction-free representation; does not enumerate generators |
