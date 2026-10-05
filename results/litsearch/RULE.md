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
   output we verified. FSGP's and FGC-Stream's papers are paywalled, but
   their released implementations were checked against the oracles of
   Section 4.3 of the paper: every output pattern is a generator, and
   their sets agree with the other implementations'. Verifying the output
   is stronger evidence than reading a problem statement.
3. **Peer review is required** (criterion I3 of the first screening, left
   out of this file by mistake). An algorithm that satisfies the rule but
   appeared only in a non-refereed venue is recorded and not counted.
