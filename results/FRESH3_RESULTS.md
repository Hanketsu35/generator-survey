# Third fresh confirmation: results

Protocol: `FRESH3_PROTOCOL.md` (2ff1a5b). Truth: `fresh3_summary.csv`
(130 runs, 1.9 h: 17 timeouts at 600 s, no errors). Probes:
`probe_fresh3.jsonl`. Output: `fresh3_eval_output.txt`; rows:
`fresh3_eval_rows.csv`.

## Registered result

| criterion | result |
|---|---|
| P1: D <= S, failed D <= S | PASS, but **trivially**: 0 picks changed |
| P2: D below the engine, P >= 0.95 | **PASS**: 1.001x vs 2.029x, ratio 0.493 (5-95% 0.349-0.791), P = 0.959 |
| P3: probe memory interval coverage >= 0.85 | **PASS**: 0.923 (n = 52) |

The progress rule is **not confirmed and not refuted**. No probed miner
lagged on any of the 13 instances, since all four finished every probe run,
so D and S made the same pick everywhere. The protocol said in advance that
this outcome would say nothing about the rule. Its support remains the post
hoc analysis (`PROGRESS_POSTHOC.md`): two failed picks turned into the best,
two picks made worse.

## What the test does show

The probe-backed ranking, with or without the flag, matched the
lowest-memory miner on 12 of 13 instances; the 13th came within 2%. The
engine alone picked Gr-growth everywhere:
- 1.21-2.18x on dota2;
- 3.67-3.89x on miniboone, where Apriori used 64-72 MB and Gr-growth about
  240;
- right on power.

Twelve of the 13 instances were sampled, not measured, so this is the
sampled path, the one that lost on uscensus in `FRESH_RESULTS.md`, now with
Gr-growth's corrected form. It held here.
