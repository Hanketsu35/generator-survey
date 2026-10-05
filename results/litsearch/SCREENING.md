# Systematic search for minimal-generator algorithms: screening (gap G8)

Search: `tools/litsearch.py`, run on OpenAlex (title and abstract) on
2026-10-05. There were 17 queries covering the names the object has carried:
minimal generators, generators of closed itemsets or patterns, free sets and
free itemsets, key patterns and key itemsets, sequential and utility
generators, generators in graphs and streams, minimal rare itemsets, and
disjunction-free sets. The queries returned 546 unique works
(`hits.csv`, `queries.txt`). A title filter kept the 160 that concern
mining. Each of those was screened on title, venue and abstract
(`candidates.json`). Four works were added by snowballing from the
references of included papers; these are marked [s].

DBLP's API was not usable (it serves a bot challenge), so OpenAlex is the
only index searched. Google Scholar was not searched.

## Inclusion criteria (as the original survey applied them, now written down)

- **I1.** The work proposes an algorithm, not only a representation, a
  base of rules, an application or a theorem.
- **I2.** The algorithm enumerates exactly the inclusion-minimal members of
  support-equivalence classes (minimal generators, key sets, 0-free sets).
  This covers itemsets, sequences, utility-constrained itemsets, graphs and
  streams. It also covers the minimal rare itemsets, the generators'
  counterpart on the negative border, as in the original 25.
- **I3.** It appeared in a peer-reviewed computer-science venue, or in a
  technical report of an included line of work.
- Conference and journal versions of the same algorithm count once.

## Exclusions

- **E1.** Strict subfamilies: disjunction-free, k-free, rule-free sets, and
  succinct systems of minimal generators.
- **E2.** Disjunctive (OR) generators.
- **E3.** Generators used only as an intermediate result (A-Close, Close).
- **E4.** Heuristic or approximate enumeration.
- **E5.** Other data models: numerical pattern structures, uncertain data,
  multi-relational data.
- **E6.** No algorithm: bases, rules, applications, interestingness, theory.
- **E7.** A venue outside computer science.

## Included: new (not among the original 25)

| family | algorithm | year | venue | executable? |
|---|---|---|---|---|
| transactional | TITANIC [s] (Stumme et al.) | 2002 | Data Knowl. Eng. | no (Coron link dead) |
| transactional | free itemsets under constraints (Boulicaut, Jeudy) | 2001 | IDEAS | no |
| transactional | MINEX, 0-free sets [s] (Boulicaut, Bykowski, Rigotti) | 2003 | Data Min. Knowl. Discov. | no |
| transactional | minimal generator family for concept lattices (Nehme et al.) | 2005 | ICFCA, LNCS | no |
| transactional | GC-growth [s] (Li, Li, Wong et al.) | 2005 | PODS | no |
| transactional | DPMiner (Li, Liu, Wong) | 2007 | KDD | no |
| transactional | MG-CHARM (Vo, Le) | 2009 | CIE39 | no |
| transactional | GENCLOSE (Tran, Truong, Le) | 2013/2014 | EAAI | no |
| transactional | CGT (Szathmary, Ispány) | 2014 | Future RFID Technologies | no |
| transactional | MG enumeration from closed itemsets (Iwanuma et al.) | 2021 | IEEE CSDE | no |
| transactional | bottom-up MG enumeration (Yajima et al.) | 2022 | IIAI-AAI | no |
| transactional | space-saving MG enumeration (Mochizuki, Iwanuma) | 2024 | IIAI-AAI | no |
| sequential | GenMiner (Lo, Khoo, Li) | 2008 | SDM | no |
| sequential | iterative generators (Lo et al.) | 2011 | TKDE | no |
| sequential | incremental sequence generators (He, Wang, Zhou) | 2011 | DASFAA, LNCS | no |
| sequential | SeqGen (Yi et al.) | 2012 | Adv. Sci. Lett. | no |
| sequential | MSGPs (Pham et al.) | 2012/2014 | ACIIDS / IJISTA | no |
| sequential | CloGen (Pham, Luo, Vo) | 2013 | IJIIDS | no |
| sequential | MSGP-PreTree (Pham) | 2015 | Fundam. Inform. | no |
| sequential | contiguous sequential generators (Zhang et al.) | 2016 | IEEE/ACM TCBB | no |
| sequential | FGenCloSM (Duong, Truong, Le) | 2018 | EAAI | no |
| high-utility | CHUIs and generators from a lattice (Mai, Nguyen) | 2017 | J. Inf. Telecommun. | no |
| high-utility | closed and generator HUIs (Merugula, Rao) | 2020 | Int. J. Knowl.-Based Intell. Eng. Syst. | no |
| rare/stream | StreamGen (Gao, Wang) | 2009 | CIKM | no |
| rare/stream | sequential generators over stream windows (Yi et al.) | 2012 | Adv. Sci. Lett. | no |
| rare/stream | Walky-G (Szathmary et al.) | 2012 | CLA | no (Coron link dead) |
| rare/stream | k-minimal rare itemsets (Hidouri et al.) | 2023 | IJCAI | no |

Total: 27 new. Years and venues as Crossref gives them (`bibmeta.json`). Merged as versions of algorithms already counted: Touch's
modular and compound versions (2011, AMAI 2013) into Touch; the 2010 rare
association rules paper into Arima/Walky-G; the 2025 journal versions into
Gen-FHUOIM.

**Arima and AprioriRare.** The original survey listed Arima (Szathmary et
al., ICTAI 2007) as executable through SPMF. The paper proposes three
algorithms. AprioriRare finds the minimal rare itemsets, MRG-Exp the minimal
rare generators, and Arima restores every rare itemset from them. SPMF 2.65
ships AprioriRare (and a TID variant), not Arima. The harness runs the SPMF
algorithm `AprioriRare` under the label "Arima" (`src/config.py`), and the
audit verified its output as the minimal rare itemsets. The executable,
benchmarked algorithm is therefore AprioriRare. The survey entry becomes
AprioriRare, with Arima and MRG-Exp named as its companions in the same
paper. This is a correction of a name, not a new algorithm.

**Executable.** No new algorithm has an
implementation in SPMF, on GitHub (searched by name), or on the authors'
pages found. The Coron platform, which implemented TITANIC, Touch and
Walky-G, has a download page whose archive returns 404 (checked
2026-10-05), and its source is not public.

## Excluded (examples, with the criterion)

| work | criterion |
|---|---|
| Bykowski & Rigotti 2001; Kryszkiewicz 2002–2006 (disjunction-free generators) | E1 |
| RFS-Miner 2004, HOPE-III 2005 (rule-free sets) | E1 |
| Dong et al. 2005 (succinct systems of minimal generators) | E1 |
| TitanicOR 2012; Disclose 2014 (disjunctive) | E2 |
| MRI-CE 2024 (cross-entropy, stochastic) | E4 (as in the original survey) |
| Kaytoue et al. 2010 (numerical pattern structures) | E5 |
| Zhao et al. 2023 (uncertain data) | E5 (as in the original survey) |
| multi-relational minimal generators 2012 | E5 |
| MinFHM 2016 (minimal high-utility itemsets, not generators) | I2 |
| non-redundant rule bases (2000–2021), classification with key itemsets | E6 |
| Srilatha & Chandra 2020 | E7 |

## Not decided (full text not reached; not counted)

- Nabeshima 2020, "Fast Enumeration of Pairs of Minimal Generators and Their
  Closure Itemsets" (JSAI annual conference). It is an algorithm for the
  object in scope, but peer review of the venue is unclear (I3).

- Phan Luong 2002, "The Closed Keys Base of Frequent Itemsets" (DaWaK):
  it may be a base of rules only.
- Tran et al. 2023 (EAAI 126), concise representations of frequent
  high-utility itemsets: the abstract was not available, and secondary
  descriptions disagree on whether it mines generators.
- "Efficient mining of compact high average utility patterns using the
  tightest weak lower bound" (Applied Intelligence 2026): possibly a
  successor of CG-FHAUI.

## Consequence for the survey

25 + 27 = 52 algorithms. 14 executable: 26.9%.

| era | surveyed | executable |
|---|---|---|
| up to 2015 | 17 + 19 = 36 | 13 (36.1%) |
| 2016 onwards | 8 + 8 = 16 | 1 (6.3%) |
