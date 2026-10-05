# Semantics-Aware Algorithm Recommendation for Minimal-Generator Mining

A three-layer recommender built on the 667-run benchmark and the output-correctness
audit in the parent repository.

## Where it stands (read this first)

Five more real datasets were benchmarked (bms1, bms2, c20d10k, kosarak,
c73d10k; 216 runs), and every completed run under 30 s — 714 of them — was
re-measured after the memory monitor turned out not to measure short runs at
all. Full account: `results/REMEASURE_RESULTS.md`.

- **Layer 2 is unaffected.** Its claims are measured against an oracle, not a
  cost model, and they are the contribution that stands.
- **The pre-registered test on the new datasets failed on cost**: S1 safety
  PASS (0 of 38, but performance-first also 0 of 38), S2 memory FAIL (1.637×
  vs fixed 1.446×), S3 runtime FAIL (1.142×, bar 1.10). These stand as
  recorded.
- **The ground truth could not have passed them.** Native runs under 0.1 s
  were read once, at spawn — apriori on mushroom 0.5 recorded at 0.02 MB,
  3.7–4.2 MB when measured. The old machine's own best, scored on the new
  one, gave memory regret 4.95×. After re-measurement the repeatability floor
  is 1.055× (memory) and 1.048× (runtime).
- **Held out one at a time over twelve datasets, the engine ties the fixed
  choice**: memory 1.452× vs 1.445× (ratio 1.006, 5–95% 0.964–1.039), runtime
  1.240× vs 1.226× (1.014, 0.950–1.087). That is after a fix to how crashes
  enter the runtime model, chosen after seeing the result; before it, runtime
  was 1.707× vs 1.226×.
- **Learned selectors still beat the fixed choice on the memory slice** of the
  selector benchmark after re-measurement (headroom 3.642× → 2.18×; best
  nPAR10 0.180 on seven datasets, 0.559 on twelve), but *which* selector is
  best changed with every change of data, as it did before. See *Selector
  results after re-measurement* below.
- **The engine now trains on the re-measured table by default**
  (`results/training_runs.csv`, 883 runs, 12 transactional datasets);
  published experiments keep reading `results/summary.csv` and reproduce.
  The engine also says when a request lies outside the data it learned from.

- **Memory requests are now answered partly by measurement.** On a memory
  request for a transactional file, the four native miners are run briefly on
  samples of the user's own file and their cost is extrapolated to full size
  (`probe.py`). Leave-one-dataset-out over 17 datasets: memory regret 1.073x
  against the model's 1.282x (pre-registered P1 passed, with an extrapolation
  form amended after one smoke-test instance; see `literature/NOTES.md` §10).
  On runtime the probe's own time dominates millisecond-scale runs (6.29x vs
  1.19x, P3 failed), so runtime stays with the model.

- **The probe held up on unseen data, but it did not win there.** First
  confirmation, 5 unseen datasets (`results/CONFIRM_RESULTS.md`):
  non-inferior (1.023x vs 1.000x). The engine was already perfect where every
  miner finished, so superiority failed as the protocol expected. Probe
  accuracy and budget answers replicate. Hard thresholds, 4 more unseen
  datasets (`results/HARD_RESULTS.md`): superiority failed (2.154x vs
  2.172x); budget answers were 100% vs 62%. The probe's two losses came from
  the decision rule, which set a measurement against an optimistic model
  guess.
- *(Superseded by the exact-memory, dataset-level intervals below.)*
  **Cost estimates now come with calibrated 90% prediction intervals**
  (`intervals.py`, `results/INTERVAL_RESULTS.md`). The band shown before was
  a bootstrap of the forest mean, and it covered 5% of runs on unseen data.
  Split-conformal intervals from leave-one-dataset-out residuals cover 88%
  (memory) and 89% (runtime). They are honest about the model: 22x wide on
  memory, against 1.1x for a probe measurement. The probe's runtime interval
  undercovered (83%) and is not shown.
- **With a probe, memory is ranked at the interval's upper end.** This was
  found after the hard-threshold test and has not been confirmed. On all 125
  instances seen, regret is 1.062x against 1.101x for the point rule and
  1.222x for the engine (`results/DECISION_RULE_POSTHOC.md`).

- **The probe now uses everything it sees.**
  - A miner stopped in its probe has already used a known amount of memory,
    and that is a lower bound on its peak.
  - The probe's measured scale on the file corrects the model's estimates
    for the miners it does not run.
  - The four miners run concurrently (worst case 68 s, was 249 s).
  - This is post hoc, on seen data (`results/DECISION_RULE_POSTHOC.md`).
    Over 125 instances, regret is 1.042x with no failed pick; the engine
    gives 1.222x. On every hard instance the pick is the lowest-memory
    miner that completed.

- **The fresh confirmation of that ranking was mixed** (`results/FRESH_RESULTS.md`:
  8 datasets downloaded for it, 33 instances).
  - Where the probe measured the user's file directly (29 instances, 7
    datasets), the shipped ranking had regret 1.002x against the engine's
    1.152x.
  - On the one large dataset it had to sample (uscensus), it lost: 2.336x
    against 1.000x. Ranking by lower bounds picked a slow allocator that did
    not finish, and the affine extrapolation overestimated Gr-growth 2.8x.
  - Superiority over the engine failed (P = 0.60), and so did "no more
    failed picks". The model's 90% memory interval covered 79% there. The
    probe's interval covered 91%.
  - Nothing was re-tuned on this result. When no probed miner finishes, the
    engine now says so, and says that the ranking is then weak.

- **Gr-growth's memory extrapolation was fixed and confirmed on new data**
  (`results/FRESH2_RESULTS.md`; 4 large UCI datasets downloaded for the
  test, 15 instances). The probe now models Gr-growth as its fixed hash map
  (13.8 MiB, from the source) plus a sublinear tree. All four registered
  criteria passed:
  - Gr-growth's median memory error fell from 0.084 to 0.054 (log10);
  - the ranking went from 1.422x to 1.359x;
  - it beat the engine (1.514x, P = 0.998);
  - the probe's interval covered 89%.

  Two instances remain where every rule picks a miner that does not finish:
  completion, not memory, is now the weak point.

- **On three more new datasets** (`results/FRESH3_RESULTS.md`), the
  probe-backed ranking matched the lowest-memory miner on 12 of 13
  instances: 1.001x, against the engine's 2.029x (P = 0.959). Twelve of the
  13 were sampled. The rule that demotes a miner lagging in its probe
  (`PROGRESS_DEMOTE`, found post hoc, `results/PROGRESS_POSTHOC.md`) had
  nothing to act on there. A targeted screen (`results/LAG_RESULTS.md`)
  over 9 lower thresholds of 13 datasets found no instance where a miner
  lags either: such instances are rare. Its condition did occur on 5
  instances of FRESH5–FRESH8, after the rule was frozen
  (`results/LAG2_RESULTS.md`). There it changed 3 picks: 1 better and 2
  worse (1.779x vs 1.615x without it). That is below the protocol's
  minimum of 4 changed picks, so it is no verdict. Over everything, the
  rule has got 4 picks right and 4 wrong. It stays on as an unconfirmed
  heuristic for a rare case.

  Over the three fresh confirmations the probe-backed ranking was below the
  engine every time: 1.110x vs 1.132x, 1.359x vs 1.514x, 1.001x vs 2.029x.

- **Memory is now measured exactly, and the intervals carry a dataset-level
  guarantee.**
  - Polled VmHWM could not measure runs of a few milliseconds, and read
    end-of-run peaks 6-7% low (`results/peak_method_check.csv`).
  - Every run now goes through `tools/peakrun` (`ru_maxrss` via `wait4`).
    Every table was re-measured: 1,999 runs, JVM runs as the median of
    three, since their peak varies by itself by up to 24%. The paper was
    updated to match.
  - Intervals are calibrated over 39-50 datasets by subsampling (Dunn,
    Wasserman & Ramdas 2023): 90% for the probe, 95% for the model. On
    twelve new datasets (`results/FRESH5_RESULTS.md`) the memory intervals
    met their guarantees: probe 0.908 at x1.1 wide, model 0.950 at x800.
    The runtime interval fell short (0.923 against 0.95).

- **Every interval the engine shows now meets its guarantee on unseen data**
  (`results/FRESH7_RESULTS.md`: 24 OpenML-CC18 datasets, selected by rule).
  - The engine trains on all 81 benchmarked datasets.
  - Runtime is reported as the typical (median) value, which is 3-5x more
    accurate than the mean it replaced.
  - Intervals are calibrated over datasets by subsampling, FGC-Stream on
    its own.
  - Measured coverage: probe memory 0.954 at 95% (x1.15 wide), model memory
    0.991 and model runtime 0.980 at 95%. The model's intervals are very
    wide, which is what it knows about a new dataset.
  - Path: FRESH4 -> FRESH7 (`RUNTIME_INTERVAL_POSTHOC.md`,
    `INTERVAL_ALLDATA_POSTHOC.md`). The probe's sampled interval, which
    FRESH7 could test on one dataset only, met its 90% guarantee on eight
    large OpenML datasets (0.954, x3 wide; `results/FRESH8_RESULTS.md`).

- **Audit before writing up** (2026-10-05). The engine now:
  - shows the typical (median) runtime in its table and budget checks, not
    the restricted mean, which a small chance of a timeout inflates;
  - shows no interval for implementations outside the calibration (the
    sequential, utility and rare-pattern miners), with a note saying why;
  - probes on any request with a memory BUDGET and uses only the probe's
    memory figures there;
  - warns when `tools/peakrun` is not built, instead of measuring
    differently in silence;
  - ranks on quantiles from the exact pools too. The ranking's own 90%
    quantiles had still come from the 794 polled runs. Rebuilt on the exact
    pools, they changed no pick on any of 335 test instances
    (`results/RANKQ_RESULTS.md`).

Sections below that report numbers on `results/summary.csv` are kept as they
were measured; where re-measurement changes a conclusion, the section says so.

## The thesis

Every published algorithm-selection framework — Rice's formulation, empirical
hardness models, AutoML portfolio methods — assumes the candidate algorithms are
semantically interchangeable, and selects among them on a performance metric.

**In generator mining that assumption is false, and this repository measures how
false.** Of 17 executable implementations:

| implementation | what the audit found |
|---|---|
| HUCI-Miner-Generators | returns **0 / 2002** support-minimal patterns — a different family entirely, despite the name |
| Gr-growth (`k ≥ 2`) | an **undocumented parameter** silently switches to the disjunction-free family; 40% of the output, faster for exactly that reason |
| Talky-G, Talky-G-diffset | return **non-minimal itemsets on 7 of 57** configurations, up to 13.8% of the output |
| VGEN vs FEAT/FSGP | disagree on **3802 patterns** at one configuration — a threshold-rounding convention, not an algorithmic difference |
| Talky-G (empty set) | emits the empty set **iff the dataset has no full-support item** — an input-dependent convention |

A recommender that optimises runtime over this candidate set returns implementations
that silently answer a different question. So Layer 2 runs *first*.

## Layers

```
  natural language
        │  Layer 1  nl.py           rule baseline + optional LLM adapter
        ▼
    MiningTask                      spec.py   formal, checkable
        │  Layer 2  capabilities.py HARD semantic filter, oracle-backed
        ▼
   eligible set
        │  Layer 3  perfmodel.py    runtime / memory / completion prediction
        ▼
  ranked recommendation + explanation + refusals with evidence
```

Layer 2 is a knowledge base and a constraint check, not a learned model: every
claim is traceable to an oracle measurement recorded in `data/capabilities.json`.

## Quick start

```bash
python -m recommender.cli --dataset mushroom --threshold 0.05
python -m recommender.cli --ask "minimal generators at 30% support, memory is tight under 512 MB" --dataset chess
python -m recommender.cli --dataset foodmart --data-type utility --family high_utility_generator --threshold 50
python -m recommender.cli --data-path mydata.txt --threshold 0.1 --json
```

Explicit flags always override anything `--ask` parses out of the text.

The engine learns from `results/training_runs.csv` when it exists (build it
with `python tools/build_training_table.py`), otherwise from
`results/summary.csv`. The fitted model is cached per table content in `out/`.

### Chat interface

```bash
ollama serve &                       # optional: without it, rules + template text
python -m recommender.chat           # then open http://127.0.0.1:8765
```

Drop a CSV (baskets, order/item pairs, or 0/1 columns — `ingest.py` decides
which and says how it read the file) or an SPMF file, and ask in Turkish or
English; a TR/EN switch sets the language of every reply. Everything stays on
the machine. The model reads the question and phrases the answer; the decision
is the engine's, unchanged. Its explanation is discarded for the template if it
names an implementation it was not shown, writes a number it was not given, or
leaves out an over-budget caveat. A reason invented without a name or number
still passes, and the page says "checked", not "verified".

Two limits the interface surfaced, both now in the engine: when a file lies
outside the size/shape range an implementation's costs were learned on
(`Recommender.outside_domain`), its predicted time and memory are marked as
extrapolations and not quoted — a 400-record file got 1007 s for Zart, whose
fastest recorded run is 0.45 s; and budgets stated in the first message are
read (they were silently dropped).

## Experiments

```bash
python -m recommender.evaluate      # E1-E4, writes out/experiments.{txt,json}
python -m recommender.nl --eval     # Layer 1 accuracy, per field
```

### E1 — the oracle gap (negative result)

A *perfect* per-instance selector beats "always run the single best implementation"
by **7.7%** in geometric mean (1.011× on PAR10 mean). Performance prediction cannot
carry this paper. It is reported so the contribution is not oversold.

The objectives do conflict, however, which is what keeps Layer 3 worth having:
FP-growth is best on runtime (1.08×) but 1.84× on memory; Apriori is best on memory
(1.38×) but 2.46× on runtime.

### E2 — semantic error rate (headline)

830 queries = 83 configurations × 5 requirement profiles × 2 objectives. The
baseline selector is given the **true measured** runtime and memory of every
implementation — a perfect performance oracle, strictly stronger than anything
learnable — and picks the cheapest implementation that accepts the input format.

| | |
|---|---|
| specification violated by performance-first selection | **188 / 830 (22.7%)** (re-run on exact memory, `results/e2_exact_output.txt`; 193 when first run) |
| violated by semantics-first selection | 0 (by construction) |
| price of correctness (compliant vs non-compliant pick) | 1.87× geometric mean |
| queries admitting **no** compliant implementation | 30 (3.6%) |

By profile: floor boundary 58.4%, ceil boundary 41.6%, default 5.4%. By objective:
runtime 21.4%, memory 25.1%.

Failure modes: 88 wrong-boundary picks, 60 opposite-boundary picks, 30 picks of
Arima (rare itemsets, not generators), 15 picks of HUCI-Miner-Generators
(utility-minimal, not support-minimal).

### Selector comparison — normalized PAR10 (leave-one-dataset-out)

```bash
python -m recommender.bench_selectors --category 1
```

Reported in **nPAR10**, the algorithm-selection standard: 0 = oracle-perfect,
1 = no better than always running the single best algorithm, > 1 = actively
worse than not selecting at all.

### Instance space — where each miner actually wins

```bash
python -m recommender.instance_space                      # runtime, PLS
python -m recommender.instance_space --objective memory
```

Projects the instances into a plane where performance varies smoothly (partial
least squares, because PCA never sees performance) and draws each algorithm's
**footprint**: the region where it is within 20% of best.

| | |
|---|---|
| performance variance the plane explains | **0.233** (PCA: 0.115) |
| Eclat / FP-growth footprint area | 1.000 / 0.966 — good *everywhere* |
| Gr-growth footprint | area 0.075, **purity 1.00** — the only real niche |
| algorithms good on zero instances | **5 of 9** |
| coverage | 16 of 36 grid cells (runtime), 11 of 36 (memory) |
| **effective instance count** | **7.3, not 58** |

That last row is the important one. Ten of the eleven features are properties
of the *dataset*; only the threshold varies within one, so the configurations
land in vertical stripes and **95.6% of positional variance lies between
datasets**. Anything learned across the plane has an effective sample size of
seven. It is also why the plane explains only 23% of performance variation —
the root cause of every weak selector number above is the features, not the
model class.

Figures: `plots/instance_space_{runtime,memory}_{pls,pca}.pdf`.

`effective instance count` is computed, not asserted: it is the cluster-sampling
design effect `n / (1 + (m̄−1)·ICC)` with the between-dataset share read as an
intra-cluster correlation. At ICC = 1 it returns the number of datasets, at
ICC = 0 the number of configurations. On the static feature set it gives 7.3,
which reproduces the figure previously quoted as "7".

### Threshold-dependent landmarks — the fix for the feature set, and its limit

```bash
python -m recommender.feature_ablation
python -m recommender.bench_selectors --objective memory --features landmarks
```

The diagnosis above names the features as the root cause, so `landmarks.py`
addresses them. Ten of the eleven static features are dataset constants, and the
one that is not — `log_thr` — is *not comparable across datasets*: the grid runs
retail at σ = 0.0005 and pumsb at 0.95, and σ = 0.3 is trivial on mushroom while
near the hardest point of accidents.

Following landmarking (Pfahringer et al., ICML 2000), 14 features describe the
instance by the **exact level-2 statistics of the mining problem**. Both arrays
they are read from — the item-support vector and the co-occurrence matrix
`C = BᵀB` — are computed **once per dataset**, so every threshold is a
thresholding of the same two arrays: **4.5 s for all 58 configurations**,
independent of how many thresholds are asked for. Level 2 is chosen because it is
where the generator property first becomes observable — `{i,j}` is a generator
iff `sup(ij) < min(sup(i), sup(j))` — so closure collapse is measured directly
while nothing beyond pairs is enumerated.

| | static | landmarks |
|---|---|---|
| performance variance the plane explains | 0.233 | **0.517** |
| between-dataset share | 95.6% | 62.2% |
| effective instances | 7.3 | **10.5** |
| LOO-dataset-out MAE vs constant baseline | 0.685 vs 0.660 — **loses** | **0.587 — wins** |

**Doubling the explained variance buys three more effective instances, not 51.**
And the per-fold picture refuses to confirm the pooled gain: landmarks win on
2 of 7 folds, with a paired bootstrap of −0.098 and a 95% CI of −0.363…+0.126.
At seven folds nothing reaches significance — which is the same small-meta-sample
problem, reappearing as the reason it cannot be shown to be solved.

**The gain is objective-specific, so the feature set is a flag, not a default:**

Shown for pairwise ranking, the selector that the training jackknife below
finds stable; "best selector per slice" is itself unstable at this sample size.

| objective | features | nPAR10 | band | P(beats SBS) |
|---|---|---|---|---|
| memory | **static** | **0.429** | 0.075–0.948 | **0.98** |
| memory | landmarks | 0.820 | 0.745–1.003 | 0.95 |
| runtime | static | 1.116 | 1.006–1.460 | 0.01 |
| runtime | **landmarks** | **0.688** | 0.411–0.884 | **1.00** |

On memory the landmarks hurt — the band stops excluding 1.0. On runtime they
are decisive, turning a selector that loses to the fixed choice into one that
beats it in every bootstrap resample. The explanation is coherent: landmarks describe what makes an
*instance* expensive in time, namely the size of the frequent sub-problem,
whereas what makes an *implementation* memory-hungry is its data structure — JVM
around 500 MB against native C around 40 MB — which the threshold barely moves.

### Statistical significance and practical magnitude are different claims

| slice | oracle gap | best selector saves |
|---|---|---|
| runtime | **9.9 ms** | 3.1 ms |
| memory | 13.3 MB | 7.4 MB |

The runtime result is statistically robust (P = 1.00) and economically trivial;
both are true. Any claim from this benchmark must print the absolute figure next
to the ratio, or "closes 31% of the gap" will be read as something it is not.

### Equivalence tiers — the recommender says when it cannot tell

The ranking used to read 1-2-3 over candidates whose predicted costs differed
by hundredths of a second, which asserts a preference the data does not
support. Each survival tree yields its own value of the decision rule, so
resampling those per-tree values bootstraps the ensemble mean and gives a
5-95% band at no extra fitting cost. Candidates whose bands overlap share a
**tier**, and within a tier the order carries no information:

```
tier implementation              runtime_s  memory_MB  P(fin)   PAR10_cost
1    Gr-growth                        8.54      151.0    100%          8.5
     FP-growth (Borgelt, -tg)         6.11      225.5    100%          6.1

2    Eclat (Borgelt, -tg)             7.18      274.6    100%          7.2

  Tier 1 contains 2 implementations whose predicted cost bands overlap.
  The data does not support preferring one over another here.

RECOMMENDED: Gr-growth  (tied with 1 other)
   predicted cost 2.700, 5-95% band 2.444..2.934
```

The band is computed on the **composite score**, not on runtime alone — a first
version tiered on the runtime band while ranking by the balanced score, which
put Gr-growth in tier 1 and a *cheaper* FP-growth in tier 2. Relative widths of
whichever bands feed the objective are propagated with that objective's
exponent (`balanced` takes a square root, so it halves the relative width).

**First, measure whether there is anything to select between**
(`python -m recommender.complementarity`). Headroom is SBS/VBS — how much a
*perfect* selector could win over the best fixed choice:

| slice | headroom | best learned selector |
|---|---|---|
| runtime, dedicated miners | **1.000×** | — Gr-growth wins 58 of 58 |
| runtime, all 9 | 1.011× | none beats the fixed choice |
| memory, SPMF only | 1.016× | none beats the fixed choice — the oracle gap is 2.8 MB |
| rare/stream (46.8% censored) | 1.251× | pairwise ranking, **0.000** |
| **memory, all 9** | **3.642×** (2.18× re-measured) | **every learned selector; pairwise ranking the most stable** |

Every number below carries a **cluster bootstrap over held-out datasets** —
whole datasets resampled, not configurations, because configurations of one
dataset are not independent and that dependence is exactly what the effective
instance count measures. An instance-level bootstrap would report intervals
several times too narrow. nPAR10 is recomputed inside each resample, its
denominator being estimated from the same data.

Memory objective, full portfolio, the 39 configurations where every candidate
completed:

| selector | nPAR10 | 5–95% band | P(beats SBS) | top-1 |
|---|---|---|---|---|
| regression (the original Layer 3) | 0.352 | 0.022–0.939 | 1.00 | 28.2% |
| pairwise ranking | **0.429** | **0.075–0.948** | **0.98** | 48.7% |
| survival (expected runtime / PAR10) | 0.575 | 0.107–0.987 | 0.96 | 56.4% |
| survival (risk-averse) | 0.610 | 0.152–1.107 | 0.90 | 17.9% |
| **SUNNY** (k-NN, k=16) | 0.981 | 0.902–1.054 | 0.74 | 38.5% |
| SBS (fixed choice) | 1.000 | — | — | 28.2% |
| **random pick** | 12.005 | 6.331–32.909 | 0.00 | 7.7% |

**Read the order of these rows as carrying no information.** This table used
to show pairwise ranking first and regression last, and was presented as "the
ordering the literature predicts: ranking > survival > regression > fixed".
Then one run in `results/summary.csv` turned out to be a silent crash recorded
as a success (see *Data repair* below). Removing that single configuration
moved regression from 0.916 to 0.352 — from worst learned selector to best.

So the stability was measured. A **training jackknife** removes each of the 39
configurations from the data in turn — train and test — refits every selector
and re-evaluates:

| selector | nPAR10 range over 39 refits | median | best in | beats SBS in |
|---|---|---|---|---|
| **pairwise ranking** | **0.143 – 0.480** | 0.429 | **30 / 39** | 39 / 39 |
| regression | 0.009 – 0.853 | 0.484 | 8 / 39 | 39 / 39 |
| survival (risk-averse) | 0.110 – 0.921 | 0.600 | 1 / 39 | 39 / 39 |
| survival (expected runtime) | 0.487 – 0.861 | 0.576 | 0 / 39 | 39 / 39 |
| SUNNY | 0.726 – 0.992 | 0.981 | 0 / 39 | 39 / 39 |

The 39 refits produce **11 distinct orders**. What survives:

- **Every learned selector beats the fixed choice, in all 39.** That is robust.
- **Pairwise ranking is the one to use** — not because it always wins, but
  because it is never bad: the narrowest range by far, and best in 30 of 39.
  Regression's 0.352 above is a favourable draw from a range that reaches 0.853.
- **That verdict holds within one training regime, and the regime matters
  more.** Every selector above is trained on the clean subset only. The engine
  (`engine_memory_eval.py`) is trained on every completed run, and pairwise
  ranking trained the same way moves its median from 0.869 to 0.248 on that
  script's anchors. There, pairwise ranking wins typically (24 of 39 refits)
  and the engine's regression has the better worst case (0.600 against 0.898).
  Neither dominates, so the engine is left as it is — measured, not assumed.
- **No ordering among the selectors is a property of this benchmark.**
  Dropping the jackknife only on the *test* side leaves the order unchanged in
  39 of 39; the instability is entirely in what the selectors *learn* from
  roughly 33 training configurations per fold. That is the effective instance
  count of 7.3 showing up as fragility rather than as a wide interval.

The two bracketing baselines change how the rest reads. **SUNNY** is the
most-cited k-NN selector in the field and fits nothing; it barely clears the
fixed choice (0.981 here, 0.993 on runtime), independent evidence that the
weakness lies in the features rather than the model class. **Random** scores
12.0, establishing that "beats the single best fixed choice" is a demanding bar
on this portfolio — a reader seeing 0.429 has no way to know that otherwise.

Three things this says, none of them flattering to a naive reading:

1. **Where runtime is the objective there is nothing to win.** Headroom is
   1.011×, and on the dedicated-miner portfolio Gr-growth wins every single
   configuration. The portfolio lacks the complementarity that makes algorithm
   selection pay in SAT — a property of the benchmark, not of any model.
2. **Absolute magnitudes stay modest** even in the good slice: pairwise
   ranking takes the mean from 18.5 MB to 10.9 MB against an oracle of 5.1 MB.
   The gap closure is a relative claim and should be stated as one.
3. **Top-1 accuracy and cost disagree.** On an earlier run the pairwise ranker
   had the best accuracy and the worst cost: one catastrophic pick outweighs
   many small wins when the loss is asymmetric. Judge selectors on cost.

See `literature/NOTES.md`, including a mistake of ours that a 10× penalty on
peak memory manufactured an apparent 4.35× headroom where the clean subset
shows 1.016×.

### Selector results after re-measurement

The tables above were measured on `results/summary.csv`, where every native
run under 0.1 s had its peak memory read once, at spawn. Re-measured
(`tools/remeasure.py`, 3 repeats, median; repeat spread 1.01×), the same
comparison — memory, full portfolio, configurations where every candidate
completed, `python -m recommender.bench_selectors --objective memory --table …`:

| | recorded (7 datasets) | re-measured (7) | re-measured + extension (12) |
|---|---|---|---|
| configurations | 39 | 39 | 46 |
| headroom SBS/VBS | 3.642× | 2.181× | 2.166× |
| best learned selector | regression 0.352 | pairwise ranking **0.180** | survival (E[T]) 0.559 |
| pairwise ranking | 0.429 | 0.180 (0.088–0.294) | 0.608 (0.198–0.902) |
| regression | 0.352 | 0.791 | 0.706 |
| SUNNY | 0.981 | 0.859 | 0.864 |
| random | 12.0 | 15.7 | 30.6 |

- The memory headroom was inflated by the monitor, roughly by a third of its
  size, but most of it is real: 2.2× on clean measurements.
- **Every learned selector still beats the fixed choice on this slice**, on
  every table.
- **The winner changed with each table**, as the jackknife above predicted.
  Pairwise ranking is the one learned selector with P(beats SBS) ≥ 0.98 on all
  three; it stays the defensible default, for its worst case rather than its
  best.
- The engine's own leave-one-dataset-out test (`tools/remeasure_eval.py`, M4)
  measures something different — geometric-mean regret per instance against
  the pre-registered fixed choice, on every instance where the eligible
  miners completed — and there it ties the fixed choice (ratio 1.006). The two
  results are compatible: nPAR10 is a ratio of arithmetic means, dominated by
  the instances where memory is large, and that is where selection pays; the
  geometric mean weights every instance equally, and on most instances every
  choice is within a few megabytes.

### Data repair: a second silent crash, and one that exited 0

**HUCI-Miner (generators) on chainstore at min utility 5000** was recorded as
completed with 0 generators. SPMF had caught an `IndexOutOfBoundsException`,
printed "An error while trying to run the algorithm", and exited **0** — so
neither the exit-code check nor the OOM check could see it.
`src.metrics.spmf_error` now recognises the report, and `repair_summary.py`
checks for it. The repair also fixed the repair tool: it looked for
`…_5000_0.json` where the harness wrote `…_5000.json`, so no utility row had
ever been checked. One row changes; the neighbouring 1000 and 2000 rows are
genuine zeros.

### Data repair: a silent crash recorded as a success

`results/summary.csv` held one run that crashed and was recorded as completed:
**Zart on connect at minsup 0.8** ran 1741 s, exited with −1 (4294967295 as
Windows reports it), wrote no output, and entered the table as a success with 0
generators — where DefMe finds 15,108. The Layer 3 models trained on it as a
1741-second completed run.

`tools/repair_summary.py` exists for exactly this class of defect and missed
it, because it detected a crash only by `OutOfMemoryError` in the output, and
this process died without a word. It now also checks the exit code of the JSON
that produced each row — matched by timestamp, because `results/raw` also holds
superseded re-runs and matching on (algorithm, dataset, threshold) would blame a
row for an older run's crash. Exit codes that are a program's convention are
excluded, each confirmed in the program's own source: Gr-growth returns its
generator count (`return (int)gdtotal_generators;`), and Borgelt's 15 is
`E_NOITEMS`, "no (frequent) items found". Without those two rules the check
flags 79 rows, every one a correct run; with them it flags exactly one.

The table moves from 597 completed / 65 DNF / 5 crash to **596 / 65 / 6**, and
Zart's completion rate from 69.0% to 67.2%. The repair changes one line of the
file. E2 (193 of 830), complementarity and every runtime result are unchanged.
On memory, connect 0.8 leaves the clean subset (40 → 39 configurations, headroom
3.660× → 3.642×), and the selector ordering the section above describes did not
survive it — which is how its instability was found.

### E3 — does the performance model generalise? (negative result)

Leave-one-**dataset**-out, seven folds. Leave-one-run-out would test on
near-duplicates and inflate everything.

| | |
|---|---|
| meta-feature model, MAE (log₁₀ s) | **1.422** (typical factor 26.4× off) |
| per-algorithm constant baseline | **0.689** (factor 4.89× off) |
| learned selector, geo-mean slowdown | 1.079× |
| always-single-best baseline | 1.112× |

With seven datasets each fold removes a seventh of the *feature space*, so the
model extrapolates rather than interpolates. This is why `synth.py` exists.

**Point prediction got worse when selection got better, and that is not a
contradiction.** This table used to read 0.727 against the 0.689 baseline — a
5% loss. It now reads 1.422, a 106% loss, and nothing regressed: the runtime
figure is no longer a regression estimate but `E[T]` read off the random survival
forest (NOTES §1). On an algorithm with heavy censoring, `E[T]` carries the
probability mass beyond the cutoff, so as a *point predictor of a completed run's
runtime* it is biased high by construction — while as an input to a *choice* it is
better, which is what the nPAR10 tables above measure.

That is the HARRIS argument appearing in our own numbers: accurate runtime
prediction is sufficient but not necessary for a correct ranking, and optimising
the ranking can cost accuracy. Any report of E3 must therefore say which quantity
it is scoring. The conclusion the negative result supports is unchanged, and
slightly stronger than before.

### E4 — is unsoundness predictable from meta-features?

Target: does Talky-G return non-minimal itemsets on this configuration?
57 configurations, 7 positive.

Pooled leave-one-dataset-out AUC is 0.771, significant under label permutation
(p = 0.012) — **and it must not be reported**. Decomposed:

| | |
|---|---|
| across datasets (*does this dataset carry the defect?*) | **0.417** — below chance |
| within datasets (*which threshold is affected?*) | 0.907 |

The model ranks T10I4D100K highest while that dataset has no defect at all. The
usable conclusion is the conservative one: **capability profiles must be measured
per implementation**, and a benchmark result on one dataset licenses no inference
about another. That is an argument for the audit.

### Layer 1

The rule-based baseline scores **100%** field-level exact match on the 28-query
set in `data/nl_queries.json`. That set speaks the field's vocabulary, so it is
saturated and cannot show whether a language model adds anything.

#### On questions a user without that vocabulary would ask

```bash
python -m recommender.nl_domain_eval                  # dev split
python -m recommender.nl_domain_eval --split test     # scored once
```

`data/nl_queries_domain.json`: 64 domain-phrased questions, half Turkish, every
word the rules key on banned and checked mechanically, split into dev and test,
with three goal-less questions per split -- one of them the literal *"which
algorithm should I use for this dataset?"*. Models run locally through Ollama.
The configuration was frozen in commit `ee34ecb` **before** the test split was
scored. Test split, 29 questions that state a goal:

| system | right | **silent error** | asked back | goal-less asked back |
|---|---|---|---|---|
| keyword rules | 27.6% | 72.4% | — | 0/3 |
| **type-default** (ignores the question) | 51.7% | 48.3% | — | 0/3 |
| qwen2.5-14b, prompt v1 | 82.8% | 17.2% | 0% | 0/3 |
| qwen2.5-14b, prompt v2 | **96.6%** | **3.4%** | 0% | 1/3 |
| qwen2.5-14b, v2 + type repair + self-consistency | 93.1% | 3.4% | 3.4% | **2/3** |

**Silent error** is the column that matters: a wrong family returned as if it
were right. Layer 2 cannot catch it, because Layer 2 guarantees that the output
matches the *specification*, not the user's *intent*. Asking back is unhelpful
but safe.

What the paired tests (exact McNemar) do and do not support:

- **The model beats the best no-model baseline: p = 0.004 on test**, p = 0.008
  on dev. This is the claim Layer 1 can now make.
- Prompt v2 over v1: it wins all 4 discordant test questions, consistent with
  dev, but **p = 0.125 — not significant at 29 questions.** Pooling with dev
  would reach p ≈ 0.04, and is not done, because dev was used to design v2.
- 7B against 14B, and self-consistency against none: not significant.

Three mechanisms, each aimed at a failure measured on dev:

- **Prompt v2** states each family by definition rather than by cue. v1 told
  the model to use `minimal_generator` for "minimal rules", which sent requests
  for rules to the one family that produces none — 14B did that on 4 of 5.
- **Type repair** reconciles the family with the data type measured from the
  file: on a sequence file, `minimal_generator` becomes `sequential_generator`,
  and any other inconsistency is sent back to the user.
- **Self-consistency** samples 7 readings, votes, and abstains below 5 of 7. It
  did **not** reduce silent errors on test — the remaining one is confident and
  wrong, and a vote cannot catch that. What it does is ask back on goal-less
  questions (1/3 → 2/3), at 6× the latency. It is a safety feature, not an
  accuracy feature, and it is on by default because a goal-less question is the
  scenario this entry point exists for.

**Residual failures, on every configuration:** a request for exact rules is
sometimes read as a request for identifying descriptions; and the 7B model
never asks back — it invents a goal on every goal-less question, on both
splits, which is why 14B is the default.

**Residual threat to validity:** the questions and the prompt were written by
the same agent. The split, the keyword ban and the pre-test commit reduce that
bias; independently collected questions would remove it.

## Synthetic instances

`synth.py` implements an IBM Quest-style generator with controlled meta-features
(size, item count, transaction length, support skew, corruption), because E3 and
E4 both fail for lack of meta-instances.

```bash
python -m recommender.synth --grid --dry-run      # 162 datasets, ~346 MB, ~28 min
python -m recommender.synth --grid
```

**The evaluation protocol must always hold out a *real* dataset, never a synthetic
one**, or the accuracy is self-congratulatory. Synthetic instances fill the space
so a held-out real dataset is interpolated; they do not replace it.

### The sweep has now been run, and it did not work

```bash
python tools/sweep_synthetic.py --plan          # cost estimate, runs nothing
python tools/sweep_synthetic.py --workers 6     # 5771 runs, ~3.2 h
python -m recommender.synthetic_eval --objective memory --features static
python -m recommender.synthetic_eval --objective memory --dose
```

**5771 runs, 161 datasets, 642 instances, 2.9% censored, 0 errors**, thresholds
*calibrated per dataset* so instances are comparable: with item supports sorted
descending, `σ_k = sup_sorted[k−1]/n_tx` makes exactly k items frequent. Results
go to `results/synthetic_summary.csv` and never touch `results/summary.csv`.

It achieved precisely what it was built to achieve:

| | effective instances | plane R² |
|---|---|---|
| real only, static | **7.3** | 0.239 |
| real + synthetic, static | **172.8** | 0.350 |
| real + synthetic, landmarks | **219.1** | 0.537 |

And selection on a held-out **real** dataset got worse:

| objective | trained on real | + all synthetic |
|---|---|---|
| runtime | 0.887 s | 0.899 s |
| memory | **7.465 MB** | **11.261 MB** |

**Every diagnostic that identified the problem now says the problem is gone, and
the quantity those diagnostics exist to predict is worse.** The cause is specific
and measurable: the generator spans the *feature* space but induces a different
*ranking*. On runtime the tail order is reproduced exactly while the top three
are permuted — real FP-growth > Eclat > Gr-growth, synthetic Gr-growth >
FP-growth > Eclat — and the top is where selection happens. On memory 8 of 9
positions differ and Gr-growth falls from best to fourth.

Not a training-ratio effect, though 642 against 58 makes that the obvious
objection. With the selector **fixed in advance** and 8 random draws per dose:

| synthetic datasets | mean | draws beating real-only |
|---|---|---|
| 0 (baseline) | 7.465 MB | — |
| 7 (matched to the 7 real) | 8.177 | 4 / 8 |
| 14 | 9.835 | 3 / 8 |
| 20 | 10.900 | 2 / 8 |
| 50 / 100 / 157 | 12.1 – 12.4 | **0 / 8** |

Degradation is monotone and **no dose helps on average**, not even the matched
one. Which datasets are drawn matters more than how many — at a dose of 7 the
draws span 6.077 to 13.687 MB. Reweighting cannot repair a wrong ranking; at
best it recovers the real-only result by ignoring the synthetic data.

So **coverage of the meta-feature space is not coverage of the performance
space**, and filling the former is a remedy that measurably fails here. Anyone
proposing synthetic meta-instances should check the induced ranking first; it is
much cheaper than the sweep.

## Files

| file | role |
|---|---|
| `spec.py` | `MiningTask` — the formal specification |
| `capabilities.py` | Layer 2 filter, with per-rejection evidence |
| `data/capabilities.json` | the oracle-derived knowledge base (the core artifact) |
| `metafeatures.py` | single-pass structural features; `data/metafeatures.json` cache |
| `perfmodel.py` | Layer 3 predictors + Pareto front |
| `engine.py` | orchestration, report formatting, training-domain check (`outside_domain`) |
| `ingest.py` | CSV (basket / long / one-hot) → SPMF, with a plain-words account of how it was read |
| `chat.py`, `web/` | local bilingual chat interface |
| `cli.py` | command line |
| `nl.py` | Layer 1 extractors + evaluation |
| `data/nl_queries.json` | Layer 1 ground truth |
| `synth.py` | controlled instance generation |
| `evaluate.py` | E1–E4 |
| `out/` | generated results (gitignored) |
| `../tools/build_training_table.py` | builds `results/training_runs.csv`, the engine's default training table |
| `../tools/remeasure.py`, `remeasure_eval.py` | re-measurement of short runs, and the analyses fixed in `results/REMEASURE_PROTOCOL.md` |
| `../tools/bench_real_extra.py`, `bench_status.py` | the extension benchmark and its pre-registered criteria |

## Reproducing

Requires the parent repository's `results/summary.csv` and `datasets/raw/`;
the engine's default also reads `results/training_runs.csv`.
No network access, no API key (unless `--llm` is used for Layer 1).

```bash
python -m recommender.metafeatures   # rebuild the meta-feature cache
python -m recommender.evaluate       # E1-E4
python -m recommender.nl --eval      # Layer 1
python tools/remeasure_eval.py       # M0-M4 on the re-measured data
python tools/bench_status.py         # the pre-registered S1-S3
```
