# Fresh confirmation: results

Protocol: `FRESH_PROTOCOL.md` (d75b069). Truth: `fresh_summary.csv`
(370 runs, 5.7 h: 49 timeouts at 600 s, 32 errors). Probes:
`probe_fresh.jsonl`, run one instance at a time after the benchmark.
Output: `fresh_eval_output.txt`; rows: `fresh_eval_rows.csv`. That gives
33 instances on 8 datasets; 4 instances had no completed eligible miner.

## Registered result

| | A engine | B registered probe rule | C as shipped |
|---|---|---|---|
| memory regret (geo-mean) | 1.132x | 1.152x | 1.110x |
| failed picks | 0 | 2 | 1 |

| criterion | result |
|---|---|
| F1: C below A, P >= 0.95 | **FAIL** (ratio 0.978, 5-95% 0.815-1.229, P = 0.60) |
| F2: C <= 1.02 x B | PASS (1.110 vs 1.175) |
| F3: C fails no more often than A or B | **FAIL** (C 1, A 0, B 2) |
| F4: model memory interval covers >= 0.85 | **FAIL** (0.785; per dataset min 0.54) |
| F4: probe memory interval covers >= 0.85 | PASS (0.911) |

## Where C gained and where it lost

On seven datasets C is at or below A: 1.000 everywhere except microblog at
1.012. It corrects the engine where the engine's estimates are wrong on a
directly measured file:
- t25i10d10k: A 1.376, C 1.000;
- msnbc: A 1.685, C 1.000;
- ecommerce: A 1.061, C 1.000;
- microblog: A 1.132, C 1.012.

On microblog at 0.032 the registered rule B picked FGC-Stream, which failed,
while C picked the best miner. There the probe's scale did what it was
added for.

All of C's loss is on **uscensus**, the only dataset that the probe sampled
rather than measured (1,000,000 transactions). C scores 2.336 against A's
1.000:

- **sigma 0.054.** No native miner finished its 20 s run on a sample, so
  every native entered the ranking through its lower bound. Apriori's bound
  was the lowest (613 MB) because it **allocates slowly**, and it was picked.
  In the truth run it did not finish in 600 s: a failed pick. A lower bound
  says how much memory a miner had taken so far, not whether it will finish.
  The rule that fixed mooc_set post hoc does the opposite here.
- **sigma 0.257.** The affine extrapolation put Gr-growth at 221 MB. The
  truth was 79 MB: its tree of frequent items grows sublinearly in n, and a
  per-transaction slope taken from 10,000 to 40,000 transactions
  overshoots. Apriori was picked (2.98x). The engine picked Gr-growth on both
  instances.

The model's memory interval undercovered on unseen data this time (0.785;
0.881 on the eight datasets of the interval test). The probe's interval
held (0.911).

## What this means

- The probe helps where it **measures** the user's file (every dataset
  except uscensus): 29 instances, no loss against the engine, several large
  gains.
- Where it can only **sample**, two things failed on the first large
  dataset that had not been seen: ranking by lower bounds, and affine
  extrapolation for Gr-growth. They are not fixed here. Any fix chosen now
  would be fitted to this result.
- The 90% interval of the model is not reliably 90% on new data; 79-88%
  across the two unseen sets.
