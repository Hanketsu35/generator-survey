# Second fresh confirmation: results

Protocol: `FRESH2_PROTOCOL.md` (41579ee). Truth: `fresh2_summary.csv`
(180 runs, 5.1 h: 52 timeouts at 600 s, 11 errors). Probes:
`probe_fresh2.jsonl`. Output: `fresh2_eval_output.txt`; rows:
`fresh2_eval_rows.csv`, `fresh2_gr_accuracy.csv`.

## Registered result: all four criteria pass

| criterion | result |
|---|---|
| G1: Gr-growth memory, median abs log10 error, 11 clean sampled instances | **PASS**: affine 0.084, new 0.054 |
| G2: C2 (new form) <= C1 (affine) | **PASS**: 1.359x vs 1.422x |
| G3: C2 below the engine, P >= 0.95 | **PASS**: 1.359x vs 1.514x, ratio 0.898 (5-95% 0.767-0.992), P = 0.998 |
| G4: probe memory interval coverage >= 0.85 | **PASS**: 0.891 (n = 55) |

## What changed in the picks

On covertype and poker the affine line put Gr-growth at 103-193 MB, and the
ranking chose Apriori. Gr-growth was the lowest in truth (44-171 MB). The
new form put it at 65-138 MB, and the ranking chose it. That is 6
instances, with C1 at 1.01-1.28x and C2 at 1.00x each.

The new form still errs:
- it overestimates covertype by 0.16-0.18 (log10);
- it now underestimates poker at the lowest sigma, by 0.15.

Its errors are smaller than the affine line's on 8 of the 11 clean
instances, and equal on the other 3.

## Where all three rules fail

On census_kdd at 0.0151 and diabetes130 at 0.213, the engine and both forms
pick Apriori, which did not finish in 600 s. Each counts as 10, and they
make up all the failed picks: A 2, C1 2, C2 2. The memory estimate is not
the problem: on diabetes130 Apriori's was 361 MB, and Apriori had reached
316 MB when stopped. The problem is completion. A probed miner's
completion probability is set to 1, though the probe saw the warning:
Apriori did not finish its 40,000-transaction sample within 20 s, while the
others finished it in seconds. Using the probe's runtime evidence for
completion is the next thing to change, and needs its own test.
