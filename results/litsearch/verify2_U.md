# Full-text verification, batch U (2026-10-05)

Rule: RULE.md including Amendments 1-3. Text extracted with `pdftotext -layout`.
Files are in `Fetched_pdfs/`. Quotes are short and verbatim. Page numbers are the printed journal or proceedings page numbers.

---

## 1. MRI-CE

- **Citation:** W. Song, Z. Sun, P. Fournier-Viger, Y. Wu, "MRI-CE: Minimal rare itemset discovery using the cross-entropy method", *Information Sciences* 665 (2024) 120392.
- **File read:** `1-s2.0-S0020025524003050-main.pdf` (full text, 1243 lines)
- **Quotes:**
  - Abstract, p. 1: "we can attempt to mine minimal rare itemsets (MRIs) and use heuristic methods to mine approximate results instead of exact results."
  - Sec. 5.4.3 (Accuracy), p. 16: "Heuristic-based itemset mining algorithms do not guarantee that all target itemsets will be discovered within a certain number of iterations".
  - Accuracy is measured as the share of the exact set that MRI-CE finds, against MRG-Exp (Sec. 5.4.3).
- **Input:** a transaction database.
- **Output:** a subset of the minimal rare itemsets, found by cross-entropy sampling. The set is not guaranteed to be complete.
- **Condition:** rarity (minimal rare itemsets).
- **Support-minimal guaranteed?** Yes, for each itemset it outputs: the progressive check confirms that every subset is frequent. The set as a whole is not guaranteed to be complete.
- **Decision: EXCLUDE.** Clause: "The method is heuristic or approximate, so the enumeration is not exact."

## 2. FCGHUI-Miner / FGHUI-Miner (Tran, Duong, Truong, Le)

- **Citation:** T. Tran, H. Duong, T. Truong, B. Le, "Efficient mining of concise and informative representations of frequent high utility itemsets", *Engineering Applications of Artificial Intelligence* 126 (2023) 107111.
- **File read:** `1-s2.0-S0952197623012952-main.pdf` (full text)
- **Quotes:**
  - Definition 10(a), Sec. 3, p. 4: "A is called a frequent generator of HUIs (FGHUI) if there exists no FHUI that is a proper sub-itemset of A and has the same support."
  - Problem statement, Sec. 3.1, p. 5: "discover both sets FCHUI of all FCHUIs and FGHUI of all FGHUIs, as well as find the FGHUI set solely."
- **Input:** a quantitative transaction database.
- **Output:** FGHUI, alone (FGHUI-Miner) or with FCHUI (FCGHUI-Miner). Theorem 1 states that the set is complete.
- **Condition:** frequent and high utility (u >= mu, supp >= ms).
- **Support-minimal guaranteed?** **No.** The definition is relative: minimality is checked only against subsets that are themselves FHUIs. The paper defines the support-minimal set separately as FHUGI = FHUI ∩ GI (Def. 10(b)) and rejects it, noting FHUGI ⊆ FGHUI and FHUGI ≠ FGHUI (Sec. 3.1(iii)). Example 3 (p. 5) gives FGHUI = {ac, ab} while GI = {a, b, c}. Here ac has support 1, the same as c, so ac is not a generator.
- **Decision: EXCLUDE.** Clause: minimality is not defined on support alone. It is relative to the FHUI family, so outputs are not guaranteed support-minimal. This is the same ground as HUCI-Miner-Generators.

## 3. Gen-FHUOIM

- **Citation:** H. Duong, T. Truong, "An Efficient Algorithm for Mining Frequent High Utility Occupancy Generators", in *Proc. 9th Int. Conf. on Cloud Computing and Internet of Things (CCIOT 2024)*, Hanoi, ACM, 2024, pp. 101-109 (doi 10.1145/3704304.3704318).
- **File read:** `3704304.3704318.pdf` (full text)
- **Quotes:**
  - Definition 6, Sec. 2, p. 103: "A is said to be a generator of FHUOI (GFHUOI) if there is not any FHUOI being a proper subset of A and sharing identical support."
  - Problem statement, p. 104: "the aim of the problem in the current study is to mine the GFHUOI set of all GFHUOIs."
- **Input:** a quantitative transaction database.
- **Output:** GFHUOI.
- **Condition:** frequent and high utility occupancy (occ >= muo, supp >= ms).
- **Support-minimal guaranteed?** **No.** The definition is relative, since minimality is checked only against FHUOI subsets. The paper itself notes that GFHUOI differs from the support-minimal FHUOGI = FHUOI ∩ GI (p. 103-104). In Example 4 (p. 104), ae is called a GFHUOI, yet Example 2 shows ρ(a) = ρ(ae), so a is a proper subset with equal support.
- **Peer review:** ACM proceedings of an international conference. This question is moot here.
- **Decision: EXCLUDE.** Clause: minimality is relative to FHUOIs, not support-minimal.

## 4. CG-FHAUI

- **Citation:** H. Duong, T. Truong, B. Le, P. Fournier-Viger, "CG-FHAUI: an efficient algorithm for simultaneously mining succinct pattern sets of frequent high average utility itemsets", *Knowledge and Information Systems* 66 (2024) 5239-5280.
- **File read:** `s10115-024-02121-7.pdf` (full text)
- **Quotes:**
  - Definition 9(a), p. 5249: "A is referred to as a generator of FHAUIs (GFHAUI) if there exists no FHAUI that is a proper subset of A and shares the same support."
  - Problem statement, p. 5250: "the paper aims to simultaneously discover both the CFHAUI set of all CFHAUIs and the GFHAUI set of all GFHAUIs."
- **Input:** a quantitative transaction database.
- **Output:** CFHAUI and GFHAUI.
- **Condition:** frequent and high average utility (au >= mu, supp >= ms).
- **Support-minimal guaranteed?** **No.** The definition is relative to the FHAUI family. The paper names the support-minimal set FHAUGI = FGI ∩ FHAUI and calls it "lossy", saying it "should not be used" (Discussion (c), p. 5250). In its worked example, B = ad is in GFHAUI even though supp(d) = supp(ad) = 1.
- **Decision: EXCLUDE.** Clause: minimality is relative to FHAUIs, not support-minimal.

## 5. MC-FHAUIM / C-FHAUIM

- **Citation:** T. Tran, H. Duong, T. Truong, B. Le, "Efficient mining of compact high average utility patterns using the tightest weak lower bound", *Applied Intelligence* 56 (2026) 180.
- **File read:** `s10489-026-07130-3.pdf` (full text)
- **Quote:** Problem statement, Sec. 3, p. 8: "the tasks of closed and/or maximal frequent high average utility itemset mining (CFHAUIM, MFHAUIM) involve identifying the sets CFHAUI and/or MFHAUI."
- **Input:** a quantitative transaction database.
- **Output:** closed FHAUIs and maximal FHAUIs only. The algorithm returns "CFHAUI and MFHAUI sets as its output (line 9)". GFHAUI appears only in related work and in the CG-FHAUI baseline.
- **Condition:** frequent and high average utility.
- **Support-minimal guaranteed?** Not applicable, since the algorithm outputs no generators.
- **Decision: EXCLUDE.** Clause: generators are not output. The output consists of closed and maximal itemsets only.

---

## Summary

| Algorithm | Decision | Reason |
|---|---|---|
| MRI-CE (Inf. Sci. 2024) | EXCLUDE (heuristic) | Cross-entropy heuristic. Its authors say it mines "approximate results instead of exact results", so completeness is not guaranteed. |
| FCGHUI-Miner / FGHUI-Miner (EAAI 2023) | EXCLUDE (minimality not on support) | FGHUI is relative: minimality is checked only against FHUI subsets. The paper shows FGHUI ≠ FHUI ∩ GI (Example 3: ac is output, but supp(c) = supp(ac)). |
| Gen-FHUOIM (CCIOT 2024) | EXCLUDE (minimality not on support) | GFHUOI is relative: minimality is checked only against FHUOI subsets. In Example 4, ae is output although ρ(a) = ρ(ae). |
| CG-FHAUI (KAIS 2024) | EXCLUDE (minimality not on support) | GFHAUI is relative: minimality is checked only against FHAUI subsets. In the paper's example, ad is output although supp(d) = supp(ad). |
| MC-FHAUIM / C-FHAUIM (Appl. Intell. 2026) | EXCLUDE (no generators output) | It outputs only closed and maximal FHAUIs. |
