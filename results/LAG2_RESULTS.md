# The progress rule where it acted after it was frozen: results

Protocol: `LAG2_PROTOCOL.md` (03c6bfc). Script `tools/lag2_eval.py`; rows in
`lag2_rows.csv`; output in `lag2_output.txt`. Run after the ranking
quantiles were adopted (`RANKQ_RESULTS.md`, 59500fb).

## Result: underpowered, no pass or fail

In A (FRESH5–FRESH8) a native miner lagged in the probe on 5 instances. The
rule changed the pick on 3 of them, fewer than the 4 the protocol requires,
so it gives no verdict. Both engines gave identical picks.

| group | n | D (rule on) | S (rule off) | changed | D better / worse |
|---|---|---|---|---|---|
| A, primary | 5 | 1.779x, 0 failed | 1.615x, 0 failed | 3 | 1 / 2 |
| B, secondary | 6 | 1.000x, 0 failed | 1.468x, 1 failed | 1 | 1 / 0 |

Changed picks:

| group | instance | probe | rule on | rule off |
|---|---|---|---|---|
| A | hypothyroid 0.0076 | direct, Apriori did not finish | Gr-growth 1.48 | Apriori 1.00 |
| A | phishingwebsites 0.141 | direct, Apriori did not finish | Gr-growth 1.20 | Apriori 1.00 |
| A | satimage 0.049 | direct, only Gr-growth finished | Gr-growth 2.26 | Apriori 2.47 |
| B | uscensus 0.054 | sampled, only Gr-growth finished a run | Gr-growth 1.00 | Apriori, failed (10) |

## Deviation from the protocol

B's four training instances (bms1, chess, connect, pamap) had no truth in
the test tables the script reads, and are left out. The rule was found on
those same instances in `PROGRESS_POSTHOC.md`, so they are not independent
of it in any case.

## Reading (not a test)

The record of the rule now stands at 4 picks it got right and 4 it got
wrong. The seen data gave 2 and 2 (`PROGRESS_POSTHOC.md`), and these data
give 2 and 2.

Split by probe mode, the eight lean one way, with an exception on each
side. This was seen after the fact.

| probe | rule right | rule wrong |
|---|---|---|
| direct (60 s on the full file) | satimage (2.26 vs 2.47) | hypothyroid, phishing, chess |
| sampled | census_kdd, diabetes130, uscensus (each a failure avoided) | pamap |

- In a direct probe, a miner that missed 60 s mostly still finished within
  the cutoff, and with the least memory.
- In a sampled probe, a miner that lagged mostly failed in the truth too.

A rule restricted to sampled probes would be a new rule, found on these same
data. It would need its own pre-registered test before it could be adopted.

## Decision (as the protocol fixes it)

The rule stays on, still unconfirmed. The README says so, and also records
that on the instances where it acted after it was frozen, it was worse more
often than better.
