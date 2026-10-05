# Verification batch A (transactional): full-text check against RULE.md

Date: 2026-10-05. Rule applied: `RULE.md`. The output must consist **only** of
minimal generators (each may be paired with its closure or support) and must
contain **all** generators that satisfy the stated condition, for at least one
parameter setting. Every decision below rests on a full text I downloaded and
read: the problem statement, the algorithm's output line and the
correctness theorem. Local copies are in the session scratchpad (`va/`).

How I read "pairing". I count an output of the form "closed itemset C with
the list of its generators" as generator–closure pairing. That form is allowed.
An output that also contains another pattern family (all frequent itemsets)
or derived objects (association-rule bases) breaks the word "only". Entries
that turn on this reading are marked **(borderline)**.

---

## 1. Pascal

- **Citation:** Y. Bastide, R. Taouil, N. Pasquier, G. Stumme, L. Lakhal. "Mining frequent patterns with counting inference". *SIGKDD Explorations* 2(2):66–75, 2000. DOI 10.1145/380995.381017.
- **Full text read:** https://hal.science/hal-00467750/document (HAL copy of the published version). The copy at https://www.kdd.org/exploration_files/bastide.pdf is the same paper, but its text layer is garbled.
- **Problem statement (Sec. 2, p. 67):** "The task of mining frequent patterns consists in determining all frequent patterns together with their supports for a given threshold minsup."
- **Output:** Algorithm 1, step 22: "return ∪k Fk". This is all frequent patterns. Each one carries a `key` flag and its support. Key patterns (generators) are the device used for counting inference (Sec. 3.1–3.2). They are not the result of the task.
- **Condition:** frequency (minsup).
- **Decision: EXCLUDE.** The clause is "generators are only an intermediate step". The stated output is the whole set of frequent itemsets. The key flags are a by-product, and the paper's task is frequent-pattern mining.
- **Implementation seen:** SPMF ships a "Pascal" (not re-checked here).

## 2. Prince

- **Citation:** T. Hamrouni, S. Ben Yahia, Y. Slimani. "Prince: An algorithm for generating rule bases without closure computations". *DaWaK 2005*, LNCS 3589, pp. 346–355. DOI 10.1007/11546849_34.
- **Full text of the DaWaK paper:** NOT reachable. The Springer copy is paywalled. HAL hal-00397430 has no file, and CiteSeerX is down.
- **Full text read instead (same authors, same algorithm):** T. Hamrouni, S. Ben Yahia, Y. Slimani. "Avoiding the itemset closure computation 'pitfall'". *CLA 2005*, CEUR-WS Vol-162, pp. 47–60, https://ceur-ws.org/Vol-162/paper5.pdf. Also seen: S. Ben Yahia, HDR thesis 2009, arXiv:1911.00524, Sec. 3.3.2. It describes the same output.
- **Output statement (CLA 2005, Sec. 3, p. 50):** "It outputs the list of frequent closed itemsets and their associated minimal generators as well as the informative association rules formed by the couple (GB, RI)."
- **Correctness (CLA 2005, Theorem 1, p. 55):** "The Prince algorithm extracts all frequent minimal generators and derives all frequent closed itemsets and all valid informative association rules."
- **Output:** frequent closed itemsets with all their frequent minimal generators (the generator lattice), plus the generic rule bases (GB, RI) under minconf.
- **Condition:** frequency (minsup), plus minconf for the rules.
- **Decision: UNVERIFIED** for the DaWaK 2005 paper as cited. **(borderline)** If the CLA 2005 companion paper is accepted as the source, the strict reading gives **EXCLUDE**. All frequent generators are output and complete, paired with their closures, but the stated output also includes association-rule bases, so it is not "only" generators. Under a lenient reading (pairs plus derived rules), it would be INCLUDE.

## 3a. Gr-growth

- **Citations:**
  - H. Li, J. Li, L. Wong, M. Feng, Y.-P. Tan. "Relative risk and odds ratio: a data mining perspective". *PODS 2005* (page range not checked). I read the authors' "Corrected Version".
  - J. Li, H. Li, L. Wong, J. Pei, G. Dong. "Minimum description length principle: generators are preferable to closed patterns". *AAAI 2006*, pp. 409–414.
- **Full texts read:**
  - PODS (corrected): http://web.archive.org/web/20180614120212id_/http://web.mit.edu:80/mfeng/www/papers/sub-217-li.pdf (archived author copy).
  - AAAI: https://www.aaai.org/Papers/AAAI/2006/AAAI06-065.pdf
- **Output statement:**
  - PODS, Fig. 5: "Output: The generators of F(ms, D) and their support levels."
  - PODS, Theorem 3.2: "Gr-growth is sound and complete for producing the generators of F(ms, D) and their support…"
  - AAAI, Algorithm 2 (p. 411): "Output: The complete set of frequent generators."
- **Output:** frequent generators only, each with its support (in the PODS paper, split into Dpos and Dneg supports).
- **Condition:** frequency (ms).
- **Decision: INCLUDE.** The output is only generators, complete, and the paper proves it.
- **Implementation:** the original binaries and sources are in this repo under `external_algos/Gr_growth/`.

## 3b. GC-growth

- **Citation and full text:** the PODS 2005 paper above (corrected version), Sec. 3.2 and Fig. 6.
- **Output statement:**
  - Fig. 6: "Output: The generators and closed patterns of F(ms, D), as well as and their support levels."
  - Step 16: "output R[C], C, S^pos[C], and S^neg[C]". Here R[C] is the set of generators of closed pattern C.
  - Theorem 3.4: "GC-growth is sound and complete for producing the generators and closed patterns of F(ms, D) and their support levels simultaneously."
- **Output:** for every frequent equivalence class, the closed pattern together with all of its generators and its supports. Every closed pattern in the output has R[C] ≠ ∅ (step 15). This is generator–closure pairing.
- **Condition:** frequency.
- **Decision: INCLUDE** (pairing allowed). The output is all frequent generators, each paired with its closure and support.

## 4. Zart

- **Citation:** L. Szathmary, A. Napoli, S. O. Kuznetsov. "ZART: A multifunctional itemset mining algorithm". *CLA 2007*, CEUR-WS Vol-331.
- **Full text read:** https://ceur-ws.org/Vol-331/Szathmary.pdf
- **Output statements:**
  - Sec. 4, end of the running example: "the algorithm stops, all FIs and all FCIs with their generators are determined, as shown in Table 4 (right)."
  - Table 4 caption, two output columns: "All frequent itemsets (∪i Fi)" and "All frequent closed itemsets with their generators (∪i Zi)".
  - Abstract: "identify frequent closed itemsets and associate generators to their closures."
- **Output:** (a) all frequent itemsets, each with support and key/closed flags, and (b) every frequent closed itemset with the list of its frequent generators. Part (b) is complete: Properties 4–5 and the Find-Generators procedure.
- **Condition:** frequency.
- **Decision: EXCLUDE (borderline).** The clause is "output only minimal generators". Zart's stated output also includes every frequent itemset (Table 4, left). Part (b) alone would qualify as generator–closure pairing. If the survey accepts "generators + closures as one component of a larger output", Zart becomes INCLUDE.
- **Implementation seen:** Coron and SPMF both have "Zart" (not re-checked).

## 5a. Talky-G

- **Citation:** L. Szathmary, P. Valtchev, A. Napoli, R. Godin. "Efficient vertical mining of frequent closures and generators". *IDA 2009*, LNCS 5772, pp. 393–404. DOI 10.1007/978-3-642-03915-7_34.
- **Full text read:** https://inria.hal.science/inria-00618805/document. The text layer is font-garbled, so I read pages 2–8 as rendered images.
- **Supporting full text:**
  - L. Szathmary et al. "A fast compound algorithm for mining generators, closed itemsets, and computing links between equivalence classes". *Annals of Math. and AI* 70, 2014. DOI 10.1007/s10472-013-9372-8. https://inria.hal.science/hal-01101140/document
  - INRIA RR-6657 (2008), https://inria.hal.science/inria-00322798/document
- **Output statements (IDA 2009):**
  - p. 2: "Additionally, Talky-G is a stand-alone algorithm for extracting FGs."
  - Sec. 3.1, p. 5: "our Talky-G algorithm uses this traversal to find the set of frequent generators."
  - Sec. 3.2, p. 6: "At the end, the IT-tree contains all FGs."
  - Algorithm 3 returns "a frequent generator or null".
  - AMAI 2014, Sec. 4.1.3: "Talky-G concentrates on frequent generators only so that at the end all FGs are comprised in the IT-tree."
- **Output:** all frequent generators, each with support. Algorithm 1 inserts 1-itemsets only if supp < |O|, so full-support items are not generators.
- **Condition:** frequency.
- **Decision: INCLUDE.**

## 5b. Talky-G-Diffset

- **Sources read:** IDA 2009 (above), RR-6657 and AMAI 2014.
- **Finding:** no paper defines a separate algorithm called "Talky-G-Diffset". Here is what the papers say about diffsets:
  - RR-6657, Sec. 2: "Diffsets can be used for Eclat, Charm, and Talky-G resulting in dEclat, dCharm, and dTalky-G … we have not used diffsets in our implementations yet."
  - AMAI 2014, Sec. 4.1.1: "we used this optimization technique in our algorithm Snow-Touch".
  - AMAI 2014, Sec. 6: "The diffset optimization technique [21] was activated".
- **Output:** the same as Talky-G. The diffset is only a tidset-encoding optimization.
- **Decision: INCLUDE as an implementation variant of Talky-G**, not as a separately published algorithm. The survey should not count it as an extra paper.

## 5c. Touch

- **Citation and full text:** IDA 2009 above, Sec. 4 (p. 8). There is a longer version in RR-6657.
- **Output statements:**
  - Sec. 4: "The algorithm has three steps: (1) extracting FCIs, (2) extracting FGs, and (3) associating FGs to their FCIs."
  - Fig. 3 caption: "Bottom: output of Touch on dataset D". This is a table with columns "FCI (supp) | FGs".
  - Abstract: "uses … Charm, to extract FCIs and a novel one, Talky-G, to extract FGs. The respective outputs are matched in a post-processing step."
- **Output:** every frequent closed itemset with its support and the list of all its frequent generators.
- **Condition:** frequency.
- **Decision: INCLUDE** (generator–closure pairing). The full Talky-G output is part of it.

## 6. DefMe (DeFMe)

- **Citation:** A. Soulet, F. Rioult. "Efficiently depth-first minimal pattern mining". *PAKDD 2014*, LNCS 8443, pp. 28–39. DOI 10.1007/978-3-319-06608-0_3.
- **Full text read:** https://hal.science/hal-01021412/document
- **Problem statement (end of Sec. 2.2):** "Given a minimizable set system S = ⟨(F, E), G, cov, φ⟩, the minimal pattern mining problem consists in enumerating all the minimal patterns for S."
- **Minimal pattern (Def. 4):** "X is minimal … iff X ∈ F and for every generalization Y ∈ G such that Y ⊂ X, cov(Y) ≠ cov(X)."
- **Itemset case (Sec. 5):** "the system S_I = ⟨(2^I, I), 2^I, cov_I, Id⟩ is minimizable and M(S_I) corresponds exactly to the free itemsets (or generators)."
- **Algorithm 1:** "Output: polynomially incrementally outputs the minimal patterns". Line 2 prints X only when X passes the minimality test. Line 4 restricts the search to Xe ∈ F, so frequency enters through F (Sec. 4.1, Table 1 uses minsup).
- **Correctness:** Theorems 1–4. Theorems 3–4 state "M(S) is enumerable" with polynomial space and polynomial delay.
- **Output:** minimal patterns only. For itemsets these are exactly the generators; equal cover is the same as equal support for nested itemsets.
- **Condition:** membership in F (frequent itemsets in the experiments; F = 2^I gives all generators).
- **Decision: INCLUDE.** The itemset instance outputs only the free itemsets (generators), and all of them. The same paper also covers the essential-itemset and minimal-string instances. Those use another cover or another pattern language, so they are out of scope, but the itemset instance qualifies on its own.

## 7. GrAFCI+

- **Citation:** M. Ledmi, S. Zidat, A. Hamdi-Cherif. "GrAFCI+ A fast generator-based algorithm for mining frequent closed itemsets". *Knowledge and Information Systems* 63(7):1873–1908, 2021. DOI 10.1007/s10115-021-01575-3.
- **Full text:** NOT reachable.
  - OpenAlex and Unpaywall report it as closed (no repository copy).
  - The Univ. Batna 2 page has only metadata.
  - I found no arXiv or HAL preprint.
- **Decision: UNVERIFIED.** The title and abstract suggest that generators are a means to closed itemsets, but RULE.md does not allow a decision from those.

## 8. TITANIC

- **Citation:** G. Stumme, R. Taouil, Y. Bastide, N. Pasquier, L. Lakhal. "Computing iceberg concept lattices with TITANIC". *Data & Knowledge Engineering* 42(2):189–222, 2002. DOI 10.1016/S0169-023X(02)00057-5.
- **Full text read:** https://hal.science/hal-00578830/document (published version).
- **Problem statement (Sec. 4, p. 201):** "Problem. Let h be a closure operator on a finite set M, and let s be a compatible weight function. Determine the closure system H_h related to the closure operator h by using the weight function s."
- **Output:**
  - Algorithm 1, step 14 (p. 205): "return ∪ {X.closure | X ∈ K_i}". Only the closures of the key sets are returned.
  - Iceberg variant (Sec. 7, p. 212): "Algorithm 5, step 14: The algorithm returns only frequent intents, i.e. only closures of frequent key sets."
  - Key sets (Def. 8: "key set (or minimal generator)") are computed level by level (K_k) as the search frontier and the place where closures are computed. They are not in the returned result.
- **Condition:** frequency, i.e. a weight threshold (iceberg).
- **Decision: EXCLUDE.** The clause is "generators are only an intermediate step and are not output". The output is closed sets (intents) only.

## 9. MINEX / δ-free sets

- **Citation:** J.-F. Boulicaut, A. Bykowski, C. Rigotti. "Free-Sets: a condensed representation of Boolean data for the approximation of frequency queries". *Data Mining and Knowledge Discovery* 7(1):5–22, 2003. DOI 10.1023/A:1021571501451.
- **Full text read:** https://perso.liris.cnrs.fr/jean-francois.boulicaut/dami_2003.pdf (author's copy of the published version; HAL hal-01503814 has no file). I did not read the PKDD 2000 conference version.
- **Definitions:**
  - Def. 6 (p. 9): a δ-strong rule X ⇒ Y satisfies "Sup(r, X) − Sup(r, X ∪ Y) ≤ δ".
  - Def. 7: "X ⊆ R is a δ-free-set w.r.t. r if and only if there is no δ-strong rule based on X in r."
  - Def. 9 (p. 11): "FreqFree(r, σ, δ) = Freq(r, σ) ∩ Free(r, δ)".
- **Output:**
  - Sec. 4 (p. 12): "an algorithm, called MINEX, that generates all frequent free-sets. For clarity, we omit the fact that it outputs their supports as well."
  - Algorithm 1: "Output: FreqFree(r, σ, δ)".
  - Theorem 4 (Correctness): "Algorithm MINEX computes the sets of all σ-frequent δ-free-sets."
- **δ = 0:** a 0-strong rule means Sup(X) = Sup(X ∪ Y), so a 0-free set has no proper subset with the same support. That is exactly a generator, as stated in RULE.md. The paper itself (Sec. 6, p. 21) says closed itemsets are "strongly related to the notion of 0-free-sets (δ-free-sets with δ = 0)". For δ > 0, the *representation* approximates supports, but the enumeration of δ-free sets is still exact.
- **Condition:** frequency (σ) and δ-freeness.
- **Decision: INCLUDE.** At δ = 0 the output is exactly the frequent generators with their supports, and it is complete (Theorem 4).

## 10. Boulicaut & Jeudy, constrained free-set mining

- **Citation:** J.-F. Boulicaut, B. Jeudy. "Mining free itemsets under constraints". *IDEAS 2001*, IEEE CS Press, pp. 322–329. DOI 10.1109/IDEAS.2001.938100.
- **Full text read:** https://perso.liris.cnrs.fr/jean-francois.boulicaut/ideas01.pdf. The math did not survive pdftotext, so I read pages 2, 4, 5 and 6 as rendered images.
- **Definitions:**
  - Def. 2 (p. 323): "the constrained itemset mining task is the computation of the collection of the itemsets that verify C (i.e., SAT_C) together with their frequencies."
  - Def. 6 (p. 326): "Free itemsets are itemsets that are not included in any closure of their proper sub-set."
  - Sec. 4.2: "The itemsets which verify this constraint are exactly the 0-free sets introduced in [6]."
- **Result:**
  - Theorem 3 (p. 327): "The set SAT_{C_am ∧ C_m} can be efficiently computed … using SAT_{C_Free∧C_m ∧ C_am ∧ C_m}, i.e., the output of the generic algorithm with the constraint C = C_Free∧C_m ∧ C_am ∧ C_m."
  - The generic algorithm's step 8 is "output ∪ L_i". Theorems 1–2 state that its generation and pruning are complete and correct.
- **Output:** the free itemsets (generators) that satisfy anti-monotone (for example frequency) and monotone constraints, with their frequencies. With C_m = true and C_am = C_freq, the output is exactly the frequent free sets. Sec. 4.4 extends this to δ-free sets.
- **Condition:** frequency plus user-defined anti-monotone and monotone constraints. Setting C_m = true gives the plain frequency condition. With a non-trivial C_m, "free" is checked only against subsets that satisfy C_m (C_Free∧C_m).
- **Note:** the experiments run on a database augmented with negated items. That is an application of the algorithm, not its pattern language.
- **Decision: INCLUDE**, by the "at least one parameter setting" clause (C_m = true, C_am = frequency). The output is then only 0-free sets (generators), and all of them.

---

## Summary

| Algorithm | Decision | One-line reason |
|---|---|---|
| Pascal | EXCLUDE | Task and output are all frequent patterns with supports (`return ∪Fk`). Key patterns are only flags and support-inference devices. |
| Prince | UNVERIFIED (borderline EXCLUDE) | DaWaK 2005 full text unreachable. The authors' CLA 2005 paper says the output is FCIs + their minimal generators + association-rule bases (GB, RI), so not "only" generators. |
| Gr-growth | INCLUDE | "Output: The complete set of frequent generators" (AAAI'06 Alg. 2). Sound and complete per PODS'05 Thm 3.2. |
| GC-growth | INCLUDE | Outputs each closed pattern with its full generator set R[C] and supports. Sound and complete per PODS'05 Thm 3.4 (pairing allowed). |
| Zart | EXCLUDE (borderline) | Output is all FIs *plus* FCIs with their generators (Table 4), so not only generators. The FCI+generator part alone would qualify. |
| Talky-G | INCLUDE | Stand-alone frequent-generator miner. "At the end, the IT-tree contains all FGs" (IDA'09 §3.2). |
| Talky-G-Diffset | INCLUDE as a Talky-G variant | Not a separately published algorithm. Diffsets are a tidset-encoding optimization (RR-6657, AMAI'14) with the same output as Talky-G. |
| Touch | INCLUDE | Outputs each FCI with all its FGs (IDA'09 §4, Fig. 3). Generator–closure pairing is allowed. |
| DefMe | INCLUDE | Enumerates all minimal patterns. The itemset instance M(S_I) "corresponds exactly to the free itemsets (or generators)" (PAKDD'14 §2.2, §5). |
| GrAFCI+ | UNVERIFIED | KAIS 2021 is closed access, with no open copy found. |
| TITANIC | EXCLUDE | Returns only closures of key sets ("returns only frequent intents", DKE'02 p. 212). Key sets are intermediate. |
| MINEX / δ-free sets | INCLUDE | "Output: FreqFree(r,σ,δ)", complete by Thm 4. δ = 0 gives exactly the frequent generators. |
| Boulicaut & Jeudy 2001 | INCLUDE | Generic levelwise algorithm outputs SAT of C_Free ∧ C_am ∧ C_m. With C_m = true and C_am = frequency this is exactly the frequent 0-free sets (Thm 3). |
