# Confirmation on hard thresholds: results

Protocol: `HARD_PROTOCOL.md` (420e79a). Truth: `hard_summary.csv` (72 runs,
2.5 h: 24 timeouts at 600 s, 12 errors). Probes: `probe_points_hard.csv`.
Output: `hard_eval_output.txt`.

## Registered result

| | affine = log-log (every probe was a direct measurement) |
|---|---|
| memory regret, 6 instances / 3 datasets: engine | 2.172x |
| probe | 2.154x |
| H1 superiority | FAIL (ratio 0.992, 5-95% 0.604-1.629, P = 0.64) |
| H2 non-inferiority | PASS |
| H3 accuracy | not applicable: no sampled instance |
| H4 budget answers correct | PASS: 1.000 vs 0.620 |

eshop_set dropped out: on both of its levels no miner completed within
600 s, so there is no lowest memory to compare against.

## Per instance

| instance | best | engine | probe |
|---|---|---|---|
| liquor 0.000225 | Apriori 21.8 MB | Gr-growth 1.43x | Apriori 1.00x |
| liquor 0.000954 | Apriori 11.8 MB | Gr-growth 2.38x | Apriori 1.00x |
| sign 0.0408 | Eclat 5.8 MB | Apriori 1.77x | Eclat 1.00x |
| sign 0.0503 | Apriori 4.4 MB | Apriori 1.00x | Apriori 1.00x |
| mooc 0.000821 | Gr-growth 523 MB | Apriori 1.74x | **Pascal, failed (10x)** |
| mooc 0.000300 | Gr-growth 2987 MB | **Apriori, failed (10x)** | **Apriori, failed (10x)** |

The probe matched the lowest memory on 4 of 6 instances, and the engine on
1. On mooc the probe's two failures undo its lead. Both come from the
decision rule, not from the probe's measurements:

- **mooc 0.000821.** The probe measured all four native miners on the
  full file (512-972 MB). The rule compared those measurements against the
  model's estimate for Pascal (252 MB) and picked Pascal, which timed out.
  The model's estimate was a guess 22x wide (see `INTERVAL_RESULTS.md`),
  set against a measurement.
- **mooc 0.000300.** No native miner finished its 60 s probe. The rule fell
  back to the model's estimates (30-43 MB; the truth was 2987 MB for the
  only native miner that completed), and so picked Apriori, which then ran
  out of its memory cap. That every native miner timed out in the probe was
  itself evidence that this instance is heavy, and the rule threw it away.

Also: on these instances a direct probe took up to 249 s (four 60 s
timeouts), which is not the "seconds" the chat promises.

## Not tested

With the pick restricted to miners that completed, the probe's regret is
1.000x against the engine's 1.480x.
