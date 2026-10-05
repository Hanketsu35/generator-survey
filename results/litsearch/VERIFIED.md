# Full-text verification: consolidated result (both passes)

Rule: `RULE.md`, including its amendments. The second pass read 18 papers
that the authors fetched through institutional access: `verify2_T.md`,
`verify2_S.md` and `verify2_U.md`. The PDFs are kept locally and are not
committed. First-pass evidence, with verbatim quotes and the URL read: `verify_A.md` (transactional classics),
`verify_B.md` (newer transactional), `verify_C.md` (subfamilies, rare,
stream), `verify_D.md` (sequential), `verify_E.md` (utility, graph).
Amendment 1 is "an identified part of the output"; amendment 2 is "our
oracle audit counts as evidence"; amendment 3 is peer review.

## Counted (verified): 35

| family | algorithm | evidence | executable |
|---|---|---|---|
| transactional | Pascal | audit of the SPMF implementation (am. 2); key patterns flagged in the paper's output (am. 1) | S |
| transactional | Prince | CLA 2005 paper, same authors and algorithm: closed itemsets with their minimal generators, plus rule bases (am. 1) | – |
| transactional | Gr-growth | AAAI'06 Alg. 2 "Output: the complete set of frequent generators"; PODS'05 Thm 3.2 | C |
| transactional | GC-growth | PODS'05 Thm 3.4: closed patterns with all their generators | – |
| transactional | Zart | frequent itemsets plus closed itemsets with their generators (am. 1); audited | S |
| transactional | Talky-G (with its diffset variant) | IDA'09 §3.2 "the IT-tree contains all FGs"; audited | S |
| transactional | Touch | IDA'09 §4: closed itemsets with all their generators | – |
| transactional | DefMe | PAKDD'14 §2.2, §5: minimal patterns = free itemsets (generators); audited | S |
| transactional | MINEX (δ-free sets, δ = 0) | DMKD'03, output FreqFree(r,σ,δ), complete by Thm 4 | – |
| transactional | free itemsets under constraints (Boulicaut, Jeudy) | IDEAS'01 Thm 3 | – |
| transactional | HLinEx, disjunction-free sets (Bykowski, Rigotti) | Information Systems 2003 version: frequent disjunction-free sets plus border (am. 1) | – |
| transactional | IncA-Gen / Magalice-A (Nehmé et al.) | ICFCA'05 Def. 1, Props 1–5: all generators of each concept; lattice order as extra output (am. 1) | – |
| transactional | DPMiner | KDD'07, Corollary 1: closed patterns with all their generators | – |
| transactional | CGT | FutureRFID'14: all frequent generators with closure and support | – |
| transactional | SSMG-Miner (succinct systems) | DASFAA'05: an exact succinct system of minimal generators (a subfamily) | – |
| sequential | FEAT | WWW'08 §2.1 "complete set of sequence generators which are frequent"; audited | S |
| sequential | FSGP | Procedia Eng.'11 Def. 1 "find all the set of frequent sequential generator patterns" (open access); audited | S |
| sequential | VGEN | DaWaK'14 Def. 7, §3; audited | S |
| sequential | GenMiner | SDM'08 §6–7 "mines a full set of generators" | – |
| high-utility | HUG-Miner | ADMA'14 §2.3: support-minimal generators that are high-utility; audited | S |
| high-utility | GHUI-Miner | ADMA'14 Alg. 1: generators of classes holding a HUI; it also reads the CHUIs mined from the same database; audited | S |
| graph | Fogger | EDBT'09 §2.1: complete set of frequent connected subgraph generators | – |
| rare | AprioriRare | ICTAI'07, Prop. 1: minimal rare itemsets are generators; audited | S |
| rare | MRG-Exp | ICTAI'07 "Output: FGs plus mRGs" | – |
| rare | MINIT | DMIN'07: all minimal infrequent itemsets | – |
| rare | Walky-G | CLA'12: all minimal rare itemsets plus frequent generators | – |
| rare | SAMRIC (k = 1) | IJCAI'23: k = 1 is exactly the minimal rare itemsets, enumerated exactly | – |
| transactional | MG-CHARM | CIE39'09 Alg. 1: all frequent closed itemsets and their minimal generators (Lemma 2). Caveat: GENCLOSE (p. 68) shows that its union step can produce non-generators. Not executable, so not audited | – |
| transactional | GENCLOSE | EAAI'14 §3.3 "all and only the generators", Theorems 1–2 | – |
| transactional | GrAFCI+ | KAIS'21 Alg. 1 output FG and FC; Corollary 4.4 (am. 1) | – |
| sequential | FGenSM | KAIS'17 p. 88 "complete set of frequent generator sequences"; Def. 3 | – |
| sequential | FGenCloSM | EAAI'18 p. 203: closed and generator sets (am. 1) | – |
| sequential | MaxGenCloSM | EAAI'18 p. 202: maximal, closed and generator sets (am. 1) | – |
| stream | StreamGen | CIKM'09 §3 "the complete set of frequent itemset generators" over the window; Thms 6–13 | – |
| stream | FGC-Stream | audit of the released implementation (am. 2); 1,246 checks | C |

Executable among the counted: Pascal, Gr-growth, Zart, Talky-G (and its
diffset variant), DefMe, FEAT, FSGP, VGEN, HUG-Miner, GHUI-Miner,
AprioriRare and FGC-Stream. That makes **12 algorithms** and 13
implementations.

## Excluded (verified): 21

| algorithm | reason |
|---|---|
| TITANIC | returns only the closures; key sets are intermediate |
| Arima | outputs all rare itemsets, mostly non-generators |
| HUCI-Miner-Generators | its "generator" is minimal among high-utility subsets, not support-minimal (Def. 13); confirmed by our audit (0 of 2,002) |
| GFHUOI-Miner (2025), CGFHUOI-Miner (2025) | minimality relative to frequent high-utility-occupancy subsets only; outputs need not be support-minimal |
| LHUCI-Miner (Mai, Nguyen 2017) | its input is a set of HUIs, not a database |
| iterative generators (Lo et al. 2011) | a different pattern language |
| GenMiner-EQ | only the top-ranked generator of each class |
| Iwanuma et al. 2021; Yajima et al. 2022; Mochizuki & Iwanuma 2024 | input is a family of closed itemsets, not a database |
| Zhao et al. 2023 | uncertain data; generators defined by frequent probability |
| Kryszkiewicz 2004 | reduces an already computed representation; no generator-mining algorithm |
| MRI-CE | heuristic: "does not guarantee that all target itemsets will be discovered" |
| Tran et al. 2023; Gen-FHUOIM 2024; CG-FHAUI 2024 | relative definition: minimality only against frequent high-utility subsets; their own examples output non-support-minimal patterns |
| MC-FHAUIM 2026 | outputs only closed and maximal patterns |
| FCloSM | closed sequences only |
| FMaxSM | maximal sequences only |
| ConSgen | contiguous (substring) pattern language |

## Recorded, not counted (venue)

- Nabeshima & Iwanuma, JSAI 2020: it meets the rule, but JSAI annual
  conference papers are not refereed (amendment 3).

## Unverified (no full text reachable, even with institutional access): 14

Not counted. Phan Luong 2002; Kryszkiewicz 2001; Kryszkiewicz & Gajek 2002;
RFS-Miner; HOPE-III; NOV-mGCFSI; IncGen (He et al. 2011); SeqGen; MSGPs
(2012/2014); CloGen; MSGP-PreTree; StreamSeqGen; MFG-HUI; Merugula & Rao
2020.

The same authors' later papers suggest that MFG-HUI uses the relative
utility definition and would be excluded. NOV-mGCFSI was in the original
survey.

## Final counts

| family | counted | executable |
|---|---|---|
| transactional | 18 | 5 (Pascal, Gr-growth, Zart, Talky-G, DefMe) |
| sequential | 7 | 3 (FEAT, FSGP, VGEN) |
| high-utility | 2 | 2 (HUG-Miner, GHUI-Miner) |
| graph | 1 | 0 |
| rare | 5 | 1 (AprioriRare) |
| stream | 2 | 1 (FGC-Stream) |
| **total** | **35** | **12 (34.3%)** |

By era (first publication):

| era | counted | executable |
|---|---|---|
| up to 2015 | 29 | 11 (37.9%) |
| since 2016 | 6 | 1 (16.7%) |

## What changed against the original survey's 25

- **Out:** Arima (replaced by AprioriRare, which is what SPMF runs),
  HUCI-Miner-Generators, Gen-FHUOIM and CG-FHAUI (not support-minimal
  generators), and FCloSM (closed only).
- **Unverified:** MFG-HUI and NOV-mGCFSI.
- **Kept and verified in the second pass:** GrAFCI+ and FGenSM.
- **Counted once:** Talky-G-Diffset is counted with Talky-G; it has no
  separate paper.
- **Kept and verified:** Pascal, Prince, Gr-growth, Zart, Talky-G, Touch,
  DefMe, FEAT, FSGP, VGEN, HUG-Miner, GHUI-Miner, Fogger, MINIT and
  FGC-Stream.
