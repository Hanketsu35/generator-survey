# Second extension: results

Protocol: `EXTENSION2_PROTOCOL.md` (committed before the run). 171 runs,
19 instances (5 datasets × 3–5 levels), 9.9 h; 16 timeouts; 4 errors, all
memory exhaustion (Borgelt "not enough memory", Gr-growth `std::bad_alloc`).
Scorer output: `extension2_status.txt` (`tools/bench_status2.py`).

## Pre-registered criteria

| criterion | result | |
|---|---|---|
| T1 safety | 0 of 32 picks violate the request | PASS |
| T2 memory, engine vs fixed (Apriori) | 2.579× vs 5.365× | PASS — expected by dataset choice |
| T3 memory, absolute ≤ 1.25× | 2.579× | **FAIL** |
| T4 runtime ≤ 1.10× | 1.428× (fixed FP-growth 1.503×) | **FAIL** |

Reference, not a criterion: always running Gr-growth scores 1.000× on memory
and 1.012× on runtime here.

Per dataset (engine memory / runtime regret): chicago 4.248 / 2.748,
kddcup99 1.000 / 1.567, onlineretail 1.362 / 1.107, pamap 9.873 / 1.273,
recordlink 2.279 / 1.171. Outside the training domain 3.111× / 1.794×,
inside 2.196× / 1.286×.

**Reading.** The engine does not generalise the regularity these datasets
share. Trained on twelve datasets where Apriori is the best single memory
choice, it picks Eclat on pamap and Apriori on part of chicago, where
Gr-growth uses a tenth of the memory. This is the performance layer's
limitation seen from a new angle, not a new failure mode: the regularity is
visible in the raw numbers and not in the features the model generalises
from.

## The benchmark finding, independent of the recommender

Peak memory, completed runs, range over the calibrated levels:

| dataset | tx | items | Gr-growth | Apriori / Eclat / FP-growth | SPMF miners (DefMe, Pascal, Zart, Talky-G ×2) |
|---|---|---|---|---|---|
| chicago | 2,662,309 | 35 | 14–16 MB | 133 MB | 393–1,931 MB |
| kddcup99 | 1,000,000 | 135 | 14 MB | 110–113 MB | 593–1,564 MB |
| onlineretail | 540,455 | 2,603 | 14–15 MB | 36–38 MB | 283–2,247 MB |
| recordlink | 574,913 | 27 | 14 MB | 47–57 MB | 271–849 MB |
| pamap | 1,000,000 | 82 | 14 MB (1,034 MB at the hardest level) | 140–1,957 MB | 655–1,880 MB |

Gr-growth is not slower for it: its median runtime relative to FP-growth per
dataset is 0.38–1.01×. Mechanism: Gr-growth streams the file and keeps a
prefix tree of the frequent items only; the Borgelt miners hold every
transaction; the SPMF miners run in a JVM that grows its heap towards the
default ceiling before collecting. On data with many transactions and few
distinct items the tree stays tiny, and the gap is widest there. Measured
independently with GNU `time -v` on two instances (pamap, chicago): 14.3–14.5
MB against 133–140 MB, matching the monitor. Generator counts agree across
all miners up to the known empty-set convention.

Datasets screened and not qualifying (all miners within ~1.3× or < 10 MB):
chainstore (FIM version), fruithut, instacart (train), skin, t20i6d100k.
