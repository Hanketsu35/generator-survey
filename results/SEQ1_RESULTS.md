# SEQ1: results

The protocol is `SEQ1_PROTOCOL.md`, in its amended form (9ff3669).

The truth runs are in `seq1_summary.csv`. All 48 ran: 43 completed, 2 timed
out (FEAT on FIFA at the two lowest thresholds) and 3 ran out of JVM heap
(FEAT and FSGP on MSNBC at 0.097; FSGP on FIFA at 0.091). Scores are in
`seq1_eval_output.txt` and `seq1_eval_rows.csv`.

## Result: S1 and S2 pass, but only against a weak bar

| criterion | recommender | single best (SBS) | failed picks | outcome |
|---|---|---|---|---|
| S1 (primary), runtime | 2.102x | 2.102x | 3 vs 3 | PASS (<=) |
| S2, memory | 2.012x | 2.278x | 3 vs 4 | PASS |

- **S3 (reported):** on 32 of 64 floor or ceiling requests (50.0%), the
  cheapest completed miner keeps the wrong threshold side. FEAT and FSGP
  keep the floor and VGEN the ceiling.

## Reading (not a test)

**On runtime the recommender makes the same pick as SBS on every instance.**
The cost models were fitted on three sequential datasets (bible, leviathan,
sign), and they do not tell these files apart. Regret reaches 24x on MSNBC
at 0.30, where VGEN is far faster than the pick. On several FIFA instances
the recommender's memory picks are 1.6–2.0x worse than SBS, although its
geometric mean is lower.

The family filter matters as much on sequential data as on transactional
data. The two halves of the system therefore fare differently:

- **The semantic half transfers.** Half of the requests that fix a side
  would be violated by a cost-only pick.
- **The cost half does not.** It needs more sequential training data
  before its ranking is worth more than the single best implementation.
