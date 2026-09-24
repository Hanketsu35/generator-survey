# Second extension: five datasets chosen for memory disagreement

Written and committed before any full-benchmark run on these datasets.

## Datasets and how they were chosen

chicago, kddcup99, onlineretail, pamap, recordlink — the five of ten SPMF
candidates that met the screening rule fixed in
`tools/screen_memory_candidates.py` before screening (Apriori ≥ 1.5× and
≥ 10 MB above the lowest-memory miner at some level). Screening results:
`results/memory_screen.csv`. In every qualifying instance the lowest-memory
miner was Gr-growth (≈ 14 MB; Apriori 36–140 MB), confirmed independently
with GNU `time -v`, and all miners returned the same generator counts up to
the known empty-set convention.

**Selection bias, stated:** these datasets were chosen *because* the fixed
memory choice does badly on them. Beating that fixed choice here is expected
and is not evidence that the engine selects well in general. What these
datasets test is narrower: whether an engine whose training data says
"Apriori is the best single memory choice" (geometric-mean regret 1.445× over
53 training instances; Gr-growth 1.777×) recognises instances where it is
not.

## Run

`tools/bench_real_extra.py --datasets chicago kddcup99 onlineretail pamap
recordlink --out results/real_extra2_summary.csv --no-calibration
--cap-reachable`: difficulty levels by frequent-pair targets 10, 100, 1,000,
5,000, 20,000, each capped at 90% of the pairs that can reach support 10 (on
attribute data items of one attribute never co-occur); duplicate levels
dropped. All nine transactional miners, 3600 s cutoff, JVM default heap,
native address space capped at a quarter of RAM, corrected memory monitor,
2 workers.

## Model under test

The engine trained on `results/training_runs.csv` as committed before this
run (twelve datasets, none of these five). Fixed choices as before: memory
Apriori, runtime FP-growth (also the single best on the training table).

## Criteria

Scored as `tools/bench_status.py` scores: per instance and objective, cost of
the pick over the lowest cost among eligible implementations; memory only on
instances where every eligible implementation completed.

- **T1 safety** — the engine's pick violates the request on 0 instances.
- **T2 memory** — engine geometric-mean regret below the fixed choice's.
  (Expected to pass by construction of the dataset choice; reported, not
  claimed as a finding.)
- **T3 memory, absolute** — engine geometric-mean regret at most 1.25×.
  This is the informative one: near-best on the instances where the
  training-data single best is wrong.
- **T4 runtime** — engine geometric-mean regret at most 1.10×.

Also reported, not criteria: per-dataset regrets; instances inside vs
outside the training domain (`Recommender.outside_domain`); Gr-growth-always
as a reference line (it wins these datasets by construction).
