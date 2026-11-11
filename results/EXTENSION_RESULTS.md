# EXTENSION: results

The first extension round (5 SPMF datasets) predates the protocol files used
from REMEASURE on; its criteria are the success metrics printed by
`tools/bench_status.py` and also recorded in `REMEASURE_RESULTS.md` §1.
This file was written on 2026-11-11 from a re-run of that scorer on the
stored runs, so that every round of Table 5 has a results file.

| criterion | value | outcome |
|---|---|---|
| S1 safety: recommender violates the request | 0 of 38 picks | PASS |
| S2 memory: regret below the fixed choice | 1.637× against 1.446× (14 instances, 5 datasets) | FAIL |
| S3 runtime: regret at most 1.10 | 1.142× (24 instances, 5 datasets) | FAIL |

Total: 1 passed, 2 failed (Table 5).
