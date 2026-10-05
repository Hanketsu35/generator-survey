# Verification batch D: sequential generators (full-text check against RULE.md)

Date: 2026-10-05. Rule: `results/litsearch/RULE.md`. For sequences, a generator is a
sequential pattern with no proper subsequence (possibly non-contiguous embedding) of
equal support.

How I looked for full texts: OpenAlex (`/works/doi:...?select=locations`), Semantic Scholar
`openAccessPdf`, Unpaywall, author pages (philippe-fournier-viger.com, mysmu.edu,
comp.nus.edu.sg/~wongls, fit.hcmus.edu.vn/~lhbac), and web search. ScienceDirect, IOS Press,
academia.edu and ResearchGate all returned bot or CAPTCHA pages (HTTP 403, "Are you a robot",
"Just a moment..."). I did not try to get past them. Springer, IEEE, Inderscience, ACM and
Ingenta (ASP) copies are paywalled, and OpenAlex lists no other open-access location for them.

---

## 1. FEAT: INCLUDE

- **Citation:** C. Gao, J. Wang, Y. He, L. Zhou. "Efficient mining of frequent sequence
  generators." WWW 2008 (poster), pp. 1051–1052. doi:10.1145/1367497.1367651
- **Full text read:** https://www.philippe-fournier-viger.com/spmf/FEAT_2008.pdf (2 pages)
- **Quote (§2.1 Problem Formulation, p. 1):** "Sp is called a sequence generator iff ∄Sp′
  such that Sp′ < Sp (i.e., Sp contains Sp′) and sup(Sp) = sup(Sp′) … the task of frequent
  sequence generator mining is to mine the complete set of sequence generators which are
  frequent in database SDB."
- **Input / output:** a sequence database of single-item sequences and min_sup. The output
  is the set FGS of all frequent sequence generators.
- **Condition:** frequency. "<" means proper subsequence, so a non-contiguous embedding
  ("S(i) = e1…ei−1 ei+1…en"). Theorem 3: S is a generator iff no single-item deletion S(i)
  has the same support.
- **Decision:** **INCLUDE.** The problem statement asks for exactly the complete set of
  frequent generators.
- **Implementation:** SPMF ("the FEAT algorithm (Gao et al., 2008)").

## 2. FSGP: UNVERIFIED

- **Citation:** S. Yi, T. Zhao, Y. Zhang, S. Ma, Z. Che. "An effective algorithm for mining
  sequential generators." Procedia Engineering 15 (2011) 3653–3657.
  doi:10.1016/j.proeng.2011.08.684
- **Full text:** the paper is gold open access (CC BY-NC-ND), but every copy I could find is
  on sciencedirect.com, which returned a CAPTCHA or HTTP 403 page. The Wayback Machine has no
  snapshot, and the ResearchGate copy is behind a bot check.
- **Decision:** **UNVERIFIED.** It is not counted. Someone with a browser should read it
  directly; it is likely to be an INCLUDE.
- **Implementation:** SPMF lists "the FSGP algorithm (Yi et al., 2011)".

## 3. VGEN: INCLUDE

- **Citation:** P. Fournier-Viger, A. Gomariz, M. Šebek, M. Hlosta. "VGEN: fast vertical
  mining of sequential generator patterns." DaWaK 2014, LNCS 8646, pp. 476–488.
  doi:10.1007/978-3-319-10160-6_42
- **Full text read:**
  https://www.philippe-fournier-viger.com/spmf/2014_VGEN_sequential_pattern_generator_mining.pdf
- **Quote (§2, Definition 7, PDF p. 4):** "A sequential pattern sa is said to be a generator
  if there is no other sequential pattern sb, such that sb ⊑ sa, and their supports are
  equal. … The problem of mining … (generator) sequential patterns is to discover the set
  of … (generator) sequential patterns."
- **More text:** §3 says the search procedure is "adapted to discover only generator
  patterns … The result is the VGEN algorithm, which returns the set of generator patterns",
  and §1 says "VGEN can capture the complete set of sequential generators".
- **Input / output:** a sequence database of itemset-sequences and minsup. The output is all
  frequent sequential generators with their supports. The empty sequence ⟨⟩ seeds Z.
- **Condition:** frequency. ⊑ is containment by a non-contiguous embedding (Definition 2).
- **Decision:** **INCLUDE.**
- **Implementation:** SPMF (VGEN).

## 4a. FGenSM: UNVERIFIED

- **Citation:** B. Le, H. Duong, T. Truong, P. Fournier-Viger. "FCloSM, FGenSM: two efficient
  algorithms for mining frequent closed and generator sequences using the local pruning
  strategy." Knowledge and Information Systems 53(1) (2017) 71–107.
  doi:10.1007/s10115-017-1032-6
- **Full text:** paywalled at Springer. ResearchGate returned "Temporarily Unavailable". There
  is no copy on Fournier-Viger's site or the first author's page (fit.hcmus.edu.vn/~lhbac),
  and OpenAlex shows no open-access location.
- **Decision:** **UNVERIFIED.** It is not counted.

## 4b. FCloSM: UNVERIFIED

- **Citation:** same paper as 4a.
- **Full text:** same as 4a, so it could not be read. Going by the title, FCloSM mines closed
  sequences, which would be an EXCLUDE (generators not output). Under the evidence standard
  this cannot be confirmed without the full text.
- **Decision:** **UNVERIFIED.** It is not counted either way.

## 5. GenMiner: INCLUDE. GenMiner-EQ: EXCLUDE

- **Citation:** D. Lo, S.-C. Khoo, J. Li. "Mining and ranking generators of sequential
  patterns." SIAM SDM 2008, pp. 553–564. doi:10.1137/1.9781611972788.51
- **Full text read:** http://www.mysmu.edu/faculty/davidlo/papers/sdm08.pdf (13 pages)
- **Quote (§3 Preliminaries, PDF p. 2):** "A frequent pattern P is a generator if there
  exists no sub-sequence of P having the same support as P."
- **Quote (§6.4 / §7, PDF p. 6):** "a set of candidate generators, which is a super-set of
  all generators … we need to eliminate members of the candidate set that are not
  generators." and "The algorithm described in Section 6 mines a full set of generators."
  Figure 4: "Outputs: Gen: The set of mined generators".
- **Input / output:** a sequence database of single-item sequences and min_sup. The output
  is all frequent sequential generators: PSL building, then S-Gen superset generation, then
  final filtering.
- **Condition:** frequency, with subsequence containment ⊑ (non-contiguous).
- **Decision:**
  - **GenMiner: INCLUDE.**
  - **GenMiner-EQ: EXCLUDE.** It outputs only the highest-ranked generator of each
    equivalence class, not all generators (§7, "returning one generator per equivalence
    class"), so it fails the "all minimal generators" requirement.

## 6. Iterative generators (Lo, Li, Wong, Khoo): EXCLUDE

- **Citation:** D. Lo, J. Li, L. Wong, S.-C. Khoo. "Mining iterative generators and
  representative rules for software specification discovery." IEEE TKDE 23(2) (2011)
  282–296. doi:10.1109/TKDE.2010.24
- **Full text read:** https://www.comp.nus.edu.sg/~wongls/psZ/davidlo-tkde09.pdf (14 pages;
  the authors' accepted version on Limsoon Wong's page)
- **Quote (§3.3, Definition 3.6, p. 5):** "A frequent pattern P is a generator if there
  exists no subsequence Q s.t.: 1. P and Q have the same support 2. Inst(P)≈Inst(Q)".
- **How support is defined (§3.2):** "The support of a pattern … is the number of its
  instances in DB. Repeated occurrences of a pattern within a sequence are taken into
  consideration". An instance is a QRE match with exclusion constraints (Definition 3.2).
- **Problem (§3.3):** "Given a sequence database, find a set of frequent iterative
  generators."
- **Decision:** **EXCLUDE (pattern language differs: iterative patterns).** The rule names
  this case explicitly. Support counts instances, not sequences. Patterns carry QRE
  exclusion constraints. Generator-hood also requires instance correspondence (≈).

## 7. IncGen (He, Wang, Zhou): UNVERIFIED

- **Citation:** Y. He, J. Wang, L. Zhou. "Efficient incremental mining of frequent sequence
  generators." DASFAA 2011, LNCS 6587, pp. 168–182 (approx.). doi:10.1007/978-3-642-20149-3_14
- **Full text:** paywalled at Springer. Semantic Scholar marks it CLOSED and OpenAlex shows no
  open-access location. ResearchGate is behind a bot check.
- **Decision:** **UNVERIFIED.** It is not counted.

## 8. SeqGen (Yi et al.): UNVERIFIED

- **Citation:** S. Yi et al. "SeqGen: mining sequential generator patterns from sequence
  databases." Advanced Science Letters 11(1) (2012). doi:10.1166/asl.2012.3008
- **Full text:** paywalled (American Scientific Publishers / Ingenta), with no open-access copy
  found.
- **Decision:** **UNVERIFIED.** It is not counted.

## 9. MSGPs (ACIIDS 2012) and the IJISTA 2014 paper: UNVERIFIED

- **Citations:** T.-T. Pham, J. Luo, T.-P. Hong, B. Vo. "MSGPs: a novel algorithm for mining
  sequential generator patterns." ICCCI 2012 (LNCS 7654), pp. 393–401.
  doi:10.1007/978-3-642-34707-8_40. Also T.-T. Pham, J. Luo, T.-P. Hong. "An efficient
  algorithm for mining sequential generator pattern using prefix trees and hash tables."
  IJISTA 13(3/4) 2014. doi:10.1504/IJISTA.2014.065151
  - Note: DBLP lists the 2012 MSGPs paper under ICCCI (conf/iccci/PhamLHV12), not ACIIDS.
- **Full text:** both paywalled (Springer and Inderscience). Semantic Scholar marks both
  CLOSED, and OpenAlex shows no open-access location.
- **Same algorithm?** This cannot be decided without the texts.
- **Decision:** **UNVERIFIED** for both. Neither is counted.

## 10. CloGen: UNVERIFIED

- **Citation:** T.-T. Pham, J. Luo, B. Vo. "An effective algorithm for mining closed
  sequential patterns and their minimal generators based on prefix trees." IJIIDS 7(4)
  (2013) 324–339. doi:10.1504/IJIIDS.2013.056314
- **Full text:** paywalled (Inderscience), with no open-access copy. ResearchGate is behind a
  bot check.
- **Decision:** **UNVERIFIED.** It is not counted. The title suggests it outputs both closed
  patterns and generators.

## 11. MSGP-PreTree: UNVERIFIED

- **Citation:** T.-T. Pham. "Efficiently mining sequential generator patterns using prefix
  trees." Fundamenta Informaticae 138(3) (2015). doi:10.3233/FI-2015-1217
- **Full text:** content.iospress.com returned a Cloudflare challenge, and no open-access
  copy was found.
- **Decision:** **UNVERIFIED.** It is not counted.

## 12. ConSgen (contiguous sequential generators): UNVERIFIED

- **Citation:** J. Zhang, Y. Wang, C. Zhang, Y. Shi. "Mining contiguous sequential generators
  in biological sequences." IEEE/ACM TCBB 13(5) (2016). doi:10.1109/TCBB.2015.2495132
- **Full text:** paywalled (IEEE). There is no PMC copy (PubMed 26529774 only) and no other
  open-access location.
- **Decision:** **UNVERIFIED.** It is not counted. If the full text confirms that patterns are
  contiguous substrings (the title says "contiguous"), the decision would be EXCLUDE (pattern
  language differs: contiguous). It is not counted under either outcome.

## 13. FGenCloSM, FMaxSM and MaxGenCloSM: UNVERIFIED

- **Citation:** H. Duong, T. Truong, B. Le. "Efficient algorithms for simultaneously mining
  concise representations of sequential patterns based on extended pruning conditions."
  Engineering Applications of Artificial Intelligence 67 (2018) 197–210.
  doi:10.1016/j.engappai.2017.09.024
- **Full text:** paywalled (ScienceDirect, which also showed a CAPTCHA). The academia.edu copy
  is behind a Cloudflare challenge.
- **Decision:** **UNVERIFIED** for all three. None is counted. FMaxSM mines maximal
  patterns, going by its name, so it would not be a generator miner in any case.

## 14. StreamSeqGen (Yi et al., stream sliding windows): UNVERIFIED

- **Citation:** S. Yi et al. "Efficient sequential generator discovery over stream sliding
  windows." Advanced Science Letters 11(1) (2012). doi:10.1166/asl.2012.3059
- **Full text:** paywalled (Ingenta / ASP), with no open-access copy.
- **Decision:** **UNVERIFIED.** It is not counted. The stream or sliding-window condition
  would be allowed by the rule if the full text confirmed exact, complete output.

---

## Summary

| Algorithm | Decision | One-line reason |
|---|---|---|
| FEAT (WWW 2008) | INCLUDE | §2.1 asks for "the complete set of sequence generators which are frequent"; subsequence-based. |
| FSGP (Proc. Eng. 2011) | UNVERIFIED | Open access, but ScienceDirect showed a CAPTCHA and no other copy was reachable. |
| VGEN (DaWaK 2014) | INCLUDE | Definition 7 and §3: returns the set of all frequent sequential generators (⊑, non-contiguous). |
| FGenSM (KAIS 2017) | UNVERIFIED | Paywalled; no open-access copy. |
| FCloSM (KAIS 2017) | UNVERIFIED | Paywalled; likely closed-only (would be EXCLUDE), but not confirmable. |
| GenMiner (SDM 2008) | INCLUDE | §6–7: "mines a full set of generators"; generator = no subsequence with equal support. |
| GenMiner-EQ (SDM 2008) | EXCLUDE | Outputs one top-ranked generator per equivalence class, not all generators. |
| Iterative generators (TKDE 2011) | EXCLUDE | Different pattern language: iterative (QRE) patterns, instance-count support, Inst≈ condition. |
| IncGen (DASFAA 2011) | UNVERIFIED | Paywalled; no open-access copy. |
| SeqGen (ASL 2012) | UNVERIFIED | Paywalled; no open-access copy. |
| MSGPs (ICCCI 2012) and IJISTA 2014 | UNVERIFIED | Paywalled; same algorithm or not cannot be decided. |
| CloGen (IJIIDS 2013) | UNVERIFIED | Paywalled; no open-access copy. |
| MSGP-PreTree (Fund. Inf. 2015) | UNVERIFIED | IOS Press challenge page; no open-access copy. |
| ConSgen, contiguous (TCBB 2016) | UNVERIFIED | Paywalled; would be EXCLUDE (contiguous) if confirmed. |
| FGenCloSM, FMaxSM, MaxGenCloSM (EAAI 2018) | UNVERIFIED | Paywalled; academia.edu copy behind a challenge page. |
| StreamSeqGen (ASL 2012) | UNVERIFIED | Paywalled; no open-access copy. |
