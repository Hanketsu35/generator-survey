# New datasets and re-measurement: results

Protocol: `REMEASURE_PROTOCOL.md` (committed before these numbers existed).
Raw output: `remeasure_eval_output.txt` (as the protocol ran),
`remeasure_eval_output_crashfix.txt` (after the post-hoc model fix below).

## 1. Pre-registered (stand as recorded)

Trained on the 7 published datasets, scored on 5 new ones (bms1, bms2,
c20d10k, kosarak, c73d10k), 216 runs + 72 calibration runs, 14.8 h.

| criterion | result | |
|---|---|---|
| S1 safety | 0 of 38 violations | PASS — but performance-first also 0 of 38: not a test of safety |
| S2 memory | engine 1.637×, fixed (Apriori) 1.446× | FAIL |
| S3 runtime | engine 1.142×, bar 1.10 (fixed FP-growth 1.152×) | FAIL |

All 33 errors are memory exhaustion under the equal ~7.8 GB budget:
20 Talky-G Java heap, Borgelt exit 1 "not enough memory" and Gr-growth
signal 6 `std::bad_alloc`, the last two reproduced under a small cap.

## 2. Why: the ground truth could not separate choices

Short native runs were read once, at spawn (0.1 s RSS poll; runs of 10–15 ms).
apriori on mushroom 0.5: recorded 0.02 MB, measures 3.68–4.19 MB in 30/30
repeats with the corrected monitor (VmHWM, 1 ms at start, sampling on the
calling thread). The old machine's own measured best, scored on this machine:
memory 4.95×, runtime 1.106× — the recorded truth fails S2's comparison and
S3's bar itself.

## 3. Protocol analyses

**M0.** 714 runs re-measured (3 repeats each), 713 usable. Native runs
recorded under 0.1 s were under-measured 3.25× (extension) and 3.82×
(training table) in geometric mean, up to 1423×. Median repeat spread
1.010× — condition (< 1.25×) met.

**M1.** Repeatability floor after re-measurement: runtime 1.048×, memory
1.055× (recorded, cross-machine: 1.106×, 4.95×).

**M2.** Same model, re-measured costs: memory 2.060× vs fixed 1.295×;
runtime 1.064× vs 1.088×. The model's memory knowledge was learned from
floor readings.

**M3.** Retrained on re-measured labels: memory **1.214× vs fixed 1.295×**;
runtime **1.079×** (fixed 1.088×). 14 and 24 instances over 5 datasets.

**M4.** Twelve datasets, leave one out, as the protocol ran it:
memory engine 1.424× vs fixed 1.445× (ratio 0.987, 5–95% 0.950–1.022,
P(better) 0.72); runtime engine **1.707×** vs fixed 1.226× (ratio 1.344,
1.021–2.047, P(better) 0.03). The loss is connect (12.7×) and accidents
(4.6×): DefMe chosen at 74 s where FP-growth takes 0.7 s.

## 4. Post-hoc: diagnosis and fix (chosen after seeing M4)

Same 7 original held-out datasets, re-measured truth, three training sets:

| training data | memory (fixed 1.502×) | runtime (fixed 1.289×) |
|---|---|---|
| recorded labels | 1.807× | 1.284× |
| re-measured labels | 1.555× | 1.314× |
| re-measured + 5 new datasets | 1.450× | 2.018× |
| … without the new datasets' crash rows | 1.489× | 1.269× |
| … without c73d10k instead | 1.430× | 2.299× |

Cause: memory-exhaustion crashes entered the runtime survival model as
censored ("longer than 300 s"). Fix: censor timeouts only; crashes train the
completion classifier. M4 with the fix:

- memory: engine 1.452× vs fixed 1.445× — ratio 1.006, 5–95% 0.964–1.039, P(better) 0.40
- runtime: engine 1.240× vs fixed 1.226× — ratio 1.014, 5–95% 0.950–1.087, P(better) 0.37

## 5. What this says

- On twelve datasets, held out one at a time, **the engine ties the single
  best fixed choice on both objectives**. It does not beat it. Earlier
  claims of an advantage were made on measurements that could not support
  them.
- Clean labels help memory selection substantially (1.807× → 1.555× → 1.450×
  on the seven original datasets), and on the five new datasets the retrained
  model beats the fixed choice on memory (1.214× vs 1.295×) — few instances,
  post-hoc.
- Two silent crashes have now been found in the published table (Zart
  connect 0.8; HUCI-Miner-Generators chainstore 5000), both repaired with
  their evidence. Both hid behind an exit status the harness trusted.
- Layer 2's value is unaffected by any of this: it is measured against an
  oracle, not a cost model.
