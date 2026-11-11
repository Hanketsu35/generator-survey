# Inclusion rule for the survey (agreed 2026-10-05)

An algorithm is counted **if and only if** its paper's own problem statement
says that its output consists **only of minimal generators** and contains
**all** minimal generators that satisfy the algorithm's stated condition,
for at least one parameter setting.

## Definitions

A **minimal generator** (also called a generator, key set, key pattern or
0-free set) is a pattern none of whose proper sub-patterns has the same
support. The relation is set inclusion for itemsets and subsequence for
sequences. Two facts follow from this definition.

- **Minimal rare itemsets are generators.** Every proper subset of a minimal
  rare itemset is frequent, so its support is strictly larger.
- **δ-free sets with δ = 0 are generators.** So are disjunction-free,
  k-free and similar sets, which form subfamilies of the generators.

## Conditions that are allowed

The stated condition may be any of these: frequency, rarity (minimal rare
itemsets), a utility condition on the generator or on its closure, a
sliding window or stream, or an extra freeness condition (disjunction-free,
k-free, succinct systems).

The output may pair each generator with its closure or support.

## Excluded

- Generators are only an intermediate step and are not output, as in
  A-Close or an algorithm that outputs only closed itemsets.
- The input is not a database: the algorithm post-processes a given family
  of closed itemsets or high-utility itemsets.
- The method is heuristic or approximate, so the enumeration is not exact.
- The pattern language differs: negated items, iterative patterns, or
  contiguous (substring) patterns. The data model may also differ:
  uncertain data, numerical pattern structures, or multi-relational data.
- "Minimality" is defined on something other than support, for example
  utility-minimal itemsets. HUCI-Miner-Generators is excluded on this
  ground: our oracle audit found 0 of its 2,002 outputs support-minimal.

## Evidence standard

- The decision rests on the **full text**: the problem definition, the
  output of the algorithm, and the theorem that proves it correct or
  complete.
- Each decision records a short verbatim quote and its location.
- Without the full text, the algorithm is **UNVERIFIED** and is not counted.
- Abstracts and titles are not enough. Third-party descriptions are not
  enough either.

## Amendments after the first verification pass (2026-10-05)

Each amendment is written down with its reason. The authors are told of
each one.

1. **"Only" is changed to "as an identified part".** The agreed criterion
   was that an algorithm counts if it finds generators. Read literally,
   "only minimal generators" removed Pascal, Zart and Prince, whose output
   also contains the frequent itemsets, the closures or the rule bases.
   The rule now reads: the complete set of generators that satisfy the
   condition must be an identified part of the output. Additional output
   is allowed. Generators used internally and not output still exclude an
   algorithm, as for TITANIC and A-Close.
2. **Our own oracle audit counts as evidence of what an implementation
   outputs.** This applies only to executable implementations whose
   output we verified. FGC-Stream's paper is paywalled (FSGP's, first thought
   paywalled, is open access and was read in the second pass), but
   their released implementations were checked against the oracles of
   Section 4.3 of the paper: every output pattern is a generator, and
   their sets agree with the other implementations'. Verifying the output
   is stronger evidence than reading a problem statement.
3. **Peer review is required** (criterion I3 of the first screening, left
   out of this file by mistake). An algorithm that satisfies the rule but
   appeared only in a non-refereed venue is recorded and not counted.

## Amendments of 2026-11-09

4. **Scope: itemsets and sequences.** The survey covers generators over
   transaction and sequence databases, with the utility, rarity and stream
   conditions above. Structured pattern languages (subgraphs, subtrees) are
   out of scope. Each had one counted algorithm (Fogger for graphs, RTGener
   for rooted trees), neither executable, and a family of one cannot be
   compared with the others. Both are recorded in `VERIFIED.md` and not
   counted.
5. **CMG (in CONCISE, SCRS Proceedings 2021) is counted.** It meets the
   rule; the publisher's page does not describe the review process, and the
   authors decided to treat the proceedings as refereed.

## Amendments of 2026-11-10

6. **Google Scholar as a further source.** Eight queries on the names of the
   database query, run with Publish or Perish; the first 200 results of each
   are screened on title and snippet (`db/scholar_screening.csv`), and the
   candidates are decided on their full texts like the others
   (`db/FULLTEXT_SCHOLAR.md`).
7. **Post-filters are not algorithms (EC6).** An option that mines all
   frequent itemsets with an existing miner and then removes the
   non-generators (Borgelt's programs, the arules generator target) is a
   reduction of a given representation, not a generator-mining algorithm.
   This writes down how the Borgelt programs were already treated.

## Amendment of 2026-11-11

8. **Families of fewer than five algorithms are not counted (EC7).** On the
   advisor's request the survey keeps the families that can be compared as
   families. High-utility generators (HUG-Miner, GHUI-Miner, HUGN: three
   algorithms) join subgraph and subtree generators (one each, am. 4) as
   recorded, not counted. IC1 no longer names utilities. The counts become
   47 counted and 13 executable (34 up to 2015, 11 executable; 13 since
   2016, 2 executable). HUG-Miner and GHUI-Miner stay in the benchmark and
   the output audit, since SPMF ships them next to HUCI-Miner-Generators and
   the recommender must keep a high-utility request away from the latter.
