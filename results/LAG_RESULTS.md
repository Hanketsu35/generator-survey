# Targeted confirmation of the progress rule: results

Protocol: `LAG_PROTOCOL.md` (78067cc). Screen: `probe_lag.jsonl`; the selection is `lag_instances.csv`, which is empty.

## Result: underpowered, no pass or fail

The grid gave 9 instances. The other targets were dropped by the minimum
absolute support of 10 or the reachable-pairs cap, or coincided with sigmas
already in a truth table. On none of the 9 did the native miners' probe
progress differ:
- on 7, all four finished every probe run;
- on 2 (uscensus 0.0000518, fifa_set 0.0015 and 0.00057), all four timed
  out in the 60 s direct run.

No instance qualified, so no truth was run. Fewer than 4 instances
qualified, and the protocol reports that as underpowered.

## What this says about the rule

A miner that lags while the others finish is rare. Across everything
probed so far it has occurred on 6 instances:
- training: bms1, chess, connect and pamap, always Apriori;
- fresh2: census_kdd and diabetes130, the two instances that motivated the
  rule.

Where it occurs the rule decides the pick, and on the seen data it decided
it right 2 times and wrong 2 times; the fifth and sixth were unchanged
(`PROGRESS_POSTHOC.md`). Two fresh tests, 13 and 9 instances, found no case
to test it on.

The rule stays on, as an untested heuristic for a rare case. The README and
the engine's comment say so. It cannot affect an instance where no miner
lags, which is every instance in all three fresh confirmations.
