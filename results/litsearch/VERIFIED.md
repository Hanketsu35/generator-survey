# Full-text verification: consolidated result (both passes)

Rule: `RULE.md`, including its amendments. The second pass read 18 papers
that the authors fetched through institutional access: `verify2_T.md`,
`verify2_S.md` and `verify2_U.md`. The PDFs are kept locally and are not
committed. First-pass evidence, with verbatim quotes and the URL read: `verify_A.md` (transactional classics),
`verify_B.md` (newer transactional), `verify_C.md` (subfamilies, rare,
stream), `verify_D.md` (sequential), `verify_E.md` (utility, graph).
Amendments 4 (scope: itemsets and sequences) and 5 (CMG's venue) of
2026-11-09 are in `RULE.md`.
The candidates of the second search (minimal infrequent and minimal rare
terms) are decided in `ADDENDUM.md`, and those of the multi-database search
of 2026-11-09 in `db/FULLTEXT_DB.md`; both are merged into the counts below.
Amendment 1 is "an identified part of the output"; amendment 2 is "our
oracle audit counts as evidence"; amendment 3 is peer review.

## Counted (verified): 50

| family | algorithm | evidence | executable |
|---|---|---|---|
| transactional | Pascal | audit of the SPMF implementation (am. 2); key patterns flagged in the paper's output (am. 1) | S |
| transactional | Prince | CLA 2005 paper, same authors and algorithm: closed itemsets with their minimal generators, plus rule bases (am. 1) | – |
| transactional | Gr-growth | AAAI'06 Alg. 2 "Output: the complete set of frequent generators"; PODS'05 Thm 3.2 | C |
| transactional | GC-growth | PODS'05 Thm 3.4: closed patterns with all their generators; program found later, audited (`results/validate_nus.txt`) | C |
| transactional | Zart | frequent itemsets plus closed itemsets with their generators (am. 1); audited | S |
| transactional | Talky-G (with its diffset variant) | IDA'09 §3.2 "the IT-tree contains all FGs"; audited | S |
| transactional | Touch | IDA'09 §4: closed itemsets with all their generators | – |
| transactional | DefMe | PAKDD'14 §2.2, §5: minimal patterns = free itemsets (generators); audited | S |
| transactional | MINEX (δ-free sets, δ = 0) | DMKD'03, output FreqFree(r,σ,δ), complete by Thm 4 | – |
| transactional | free itemsets under constraints (Boulicaut, Jeudy) | IDEAS'01 Thm 3 | – |
| transactional | HLinEx, disjunction-free sets (Bykowski, Rigotti) | Information Systems 2003 version: frequent disjunction-free sets plus border (am. 1) | – |
| transactional | IncA-Gen / Magalice-A (Nehmé et al.) | ICFCA'05 Def. 1, Props 1–5: all generators of each concept; lattice order as extra output (am. 1) | – |
| transactional | DPMiner | KDD'07, Corollary 1: closed patterns with all their generators. The released program (DPM-delta, found later) returns only the delta-discriminative classes (`results/validate_nus.txt`) | C (subfamily) |
| transactional | CGT | FutureRFID'14: all frequent generators with closure and support | – |
| transactional | SSMG-Miner (succinct systems) | DASFAA'05: an exact succinct system of minimal generators (a subfamily) | – |
| sequential | FEAT | WWW'08 §2.1 "complete set of sequence generators which are frequent"; audited | S |
| sequential | FSGP | Procedia Eng.'11 Def. 1 "find all the set of frequent sequential generator patterns" (open access); audited | S |
| sequential | VGEN | DaWaK'14 Def. 7, §3; audited | S |
| sequential | GenMiner | SDM'08 §6–7 "mines a full set of generators" | – |
| high-utility | HUG-Miner | ADMA'14 §2.3: support-minimal generators that are high-utility; audited | S |
| high-utility | GHUI-Miner | ADMA'14 Alg. 1: generators of classes holding a HUI; it also reads the CHUIs mined from the same database; audited | S |
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
| rare | IFP_min | COMAD'11 Def. 1, Sect. 5.2 completeness and soundness (`ADDENDUM.md`) | – |
| rare | CP4MII | IJCAI'19 Thm 1 (`ADDENDUM.md`); source public, does not build | – |
| rare | RP-VIPER | DaWaK'23 Alg. 1 "Output: List of all minimal rare patterns"; on its claim (`ADDENDUM.md`) | – |
| stream | MIP-DS | ESWA'15 Def. 3, Sect. 4.1 "generates all possible minimal infrequent patterns"; on its claim (`ADDENDUM.md`) | – |
| stream | MIMDS_1/2 | IAJIT'21 Alg. 1 "Output: MP"; on its claim (`ADDENDUM.md`) | – |
| stream | MRPM | ITC'22 Def. 3, Alg. 1 "Output: MRPs" (`ADDENDUM.md`) | – |
| transactional | GenAll | ARIMA'05 Alg. 1: every concept with its list of minimal generators (`db/FULLTEXT_DB.md`) | – |
| transactional | GBorder2 | PKDD'05 §2: maintains FG with supports and its negative border as the database changes; on its claim (`db/FULLTEXT_DB.md`) | – |
| transactional | FTMiner (δ-free, δ = 0) | DS'05 Thm 2: all γ-frequent δ-free patterns (`db/FULLTEXT_DB.md`) | – |
| transactional | FFIP (δ-free, δ = 0) | APCIP'09 Alg. 2 "Output: FreqFreePart(r, σ, δ)"; on its claim (`db/FULLTEXT_DB.md`) | – |
| sequential | DeFFeD (δ-free sequences, δ = 0) | ICDM'14 Def. 2.5, §II-C "the complete set of frequent δ-free sequential patterns" (`db/FULLTEXT_DB.md`) | – |
| high-utility | HUGN | IJICIC'16 Defs 2.8–2.9: support-minimal generators that are high-utility; on its claim (`db/FULLTEXT_DB.md`) | – |
| transactional | CMG (in CONCISE) | SCRS'21 §3.1, Alg. 1 "Ensure: ⟨Closed, Maximal, Generator, Supp⟩" (am. 1); venue counted as refereed (`RULE.md` am. 5) | – |
| stream | MRP-TBMiner | Chinese J. Computers'19 Def. 5: all minimal rare patterns of the window; on its claim (`db/FULLTEXT_DB.md`) | – |
| transactional | Closed keys (FClosedKeys; Phan Luong) | DaWaK'02 "The closed keys base of frequent itemsets" (R0246); decided on the long version "A method for computing frequent key and closed itemsets in one phase" (ResearchGate full text, 2026-11-10, `papers/ft/scholar/`): key itemset = no strictly included itemset with the same closure; Algorithm FClosedKeys returns all frequent (key, closure, support) triples, Theorem 2 (correct and complete) | – |
| transactional | CDP+I (constraint dominance programming; also minimal rare itemsets) | ECAI'20 (Koçak, Akgün, Guns, Miguel), found by Google Scholar; decided on the arXiv preprint and the released ESSENCE models `gen_fis.essence`, `min_rare_fis.essence` (`db/FULLTEXT_SCHOLAR.md`) | M |

Executable among the counted: Pascal, Gr-growth, Zart, Talky-G (and its
diffset variant), DefMe, FEAT, FSGP, VGEN, HUG-Miner, GHUI-Miner,
AprioriRare and FGC-Stream: **12 algorithms** and 13 implementations,
the benchmark's. The programs of GC-growth and DPMiner were found later
(audited; GC-growth benchmarked separately, `results/gcgrowth_summary.csv`),
which makes **14 executable algorithms**. CDP+I, found by the Google Scholar
search (2026-11-10), releases its constraint models and scripts
(github.com/stacs-cp/ECAI2020-CDP, Zenodo 10.5281/zenodo.3675340): **15**.

## Excluded (verified): 26 (21 here, 5 in `ADDENDUM.md`)

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
- Kyiv (Demchuk & Leith), arXiv:1403.6985: meets the rule, no refereed
  version (`ADDENDUM.md`).

## Recorded, not counted (scope: structured patterns, `RULE.md` am. 4)

- Fogger, EDBT 2009: complete set of frequent connected subgraph
  generators (`verify_E.md`). Not executable.
- RTGener, CyberC 2013: all frequent rooted tree generators, on its claim
  (`db/FULLTEXT_DB.md`). Not executable.

## Unverified (no full text reachable, even with institutional access): 15

The multi-database search adds candidates that could not be read yet; they
are listed in `db/FULLTEXT_DB.md` and are not counted.

Not counted. Kryszkiewicz 2001; Kryszkiewicz & Gajek 2002;
RFS-Miner; HOPE-III; NOV-mGCFSI; IncGen (He et al. 2011); SeqGen; MSGPs
(2012/2014); CloGen; MSGP-PreTree; StreamSeqGen; MFG-HUI; Merugula & Rao
2020; from the second search, Loo et al. (DEXA 2000) and AMCMRP-Outlier
(ISC 2020).

The same authors' later papers suggest that MFG-HUI uses the relative
utility definition and would be excluded. NOV-mGCFSI was in the original
survey.

## Final counts

| family | counted | executable |
|---|---|---|
| transactional | 25 | 8 (Pascal, Gr-growth, GC-growth, Zart, DPMiner (subfamily), Talky-G, DefMe, CDP+I) |
| sequential | 8 | 3 (FEAT, FSGP, VGEN) |
| rare | 8 | 1 (AprioriRare) |
| stream | 6 | 1 (FGC-Stream) |
| **total** | **47** | **13 (27.7%)** |

High-utility (3 counted before, 2 executable: HUG-Miner, GHUI-Miner) is
recorded, not counted, since 2026-11-11 (`RULE.md` am. 8).

By era (first publication):

| era | counted | executable |
|---|---|---|
| up to 2015 | 34 | 11 (32.4%) |
| since 2016 | 13 | 2 (15.4%) |

## What changed against the original survey's 25

- **Out:** Arima (replaced by AprioriRare, which is what SPMF runs),
  HUCI-Miner-Generators, Gen-FHUOIM and CG-FHAUI (not support-minimal
  generators), and FCloSM (closed only).
- **Unverified:** MFG-HUI and NOV-mGCFSI.
- **Kept and verified in the second pass:** GrAFCI+ and FGenSM.
- **Counted once:** Talky-G-Diffset is counted with Talky-G; it has no
  separate paper.
- **Kept and verified:** Pascal, Prince, Gr-growth, Zart, Talky-G, Touch,
  DefMe, FEAT, FSGP, VGEN, HUG-Miner, GHUI-Miner, MINIT and
  FGC-Stream.
- **Out of scope since 2026-11-09:** Fogger (graph), `RULE.md` am. 4.
