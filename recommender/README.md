# Semantics-Aware Algorithm Recommendation for Minimal-Generator Mining

A three-layer recommender built on the 667-run benchmark and the output-correctness
audit in the parent repository.

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
| specification violated by performance-first selection | **193 / 830 (23.3%)** |
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

| objective | best selector | nPAR10 | band | P(beats SBS) |
|---|---|---|---|---|
| memory, **static** | pairwise ranking | **0.445** | 0.094–0.962 | **0.96** |
| memory, landmarks | survival (exp. runtime) | 0.922 | 0.773–1.084 | 0.80 |
| runtime, static | survival (risk-averse) | 0.913 | 0.766–1.000 | 0.91 |
| runtime, **landmarks** | pairwise ranking | **0.688** | 0.411–0.884 | **1.00** |

On memory the landmarks actively hurt — every band then spans 1.0. On runtime
they are decisive. The explanation is coherent: landmarks describe what makes an
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
| memory, SPMF only | 1.016× | pairwise ranking, 0.745 |
| rare/stream (46.8% censored) | 1.251× | pairwise ranking, **0.000** |
| **memory, all 9** | **3.660×** | **pairwise ranking, 0.445** |

On the one slice with real headroom, every learned selector beats the fixed
choice and the ordering is the one the literature predicts —
**ranking > survival > regression > fixed**:

Every number below carries a **cluster bootstrap over held-out datasets** —
whole datasets resampled, not configurations, because configurations of one
dataset are not independent and that dependence is exactly what the effective
instance count measures. An instance-level bootstrap would report intervals
several times too narrow. nPAR10 is recomputed inside each resample, its
denominator being estimated from the same data.

| selector | nPAR10 | 5–95% band | P(beats SBS) | top-1 |
|---|---|---|---|---|
| pairwise ranking | **0.445** | **0.094–0.962** | **0.96** | 45.0% |
| survival (risk-averse) | 0.869 | 0.507–1.034 | 0.88 | 35.0% |
| survival (expected runtime / PAR10) | 0.893 | 0.612–1.034 | 0.88 | 32.5% |
| regression (the original Layer 3) | 0.916 | 0.443–1.194 | 0.65 | 10.0% |
| **SUNNY** (k-NN, k=16) | 0.987 | 0.911–1.087 | 0.67 | 37.5% |
| SBS (fixed choice) | 1.000 | — | — | 27.5% |
| **random pick** | 11.824 | 6.262–30.582 | 0.00 | 7.5% |

Only the pairwise ranker's band excludes 1.0. For every other selector,
"beats the fixed choice" is not supported by the data, and saying so is the
difference between a result and a ranking of point estimates.

The two bracketing baselines are there because they change how the rest reads.
**SUNNY** is the most-cited k-NN selector in the field and fits nothing; it
barely clears the fixed choice (0.987 here, 0.993 on runtime), which is
independent evidence that the weakness lies in the features rather than in the
model class. **Random** scores 11.8, establishing that "beats the single best
fixed choice" is a demanding bar on this portfolio and not a trivial one — a
reader seeing 0.445 has no way to know that otherwise.

Three things this says, none of them flattering to a naive reading:

1. **Where runtime is the objective there is nothing to win.** Headroom is
   1.011×, and on the dedicated-miner portfolio Gr-growth wins every single
   configuration. The portfolio lacks the complementarity that makes algorithm
   selection pay in SAT — a property of the benchmark, not of any model.
2. **Absolute magnitudes stay modest** even in the good slice: 18.4 MB down to
   11.0 MB. The 55% gap closure is a relative claim and should be stated as one.
3. **Top-1 accuracy and cost disagree.** On an earlier run the pairwise ranker
   had the best accuracy and the worst cost: one catastrophic pick outweighs
   many small wins when the loss is asymmetric. Judge selectors on cost.

See `literature/NOTES.md`, including a mistake of ours that a 10× penalty on
peak memory manufactured an apparent 4.35× headroom where the clean subset
shows 1.016×.

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
set. That means the set is saturated and was written by the same author as the
rules: there is no headroom for an LLM to demonstrate value. An independently
authored query set, containing genuinely ambiguous requests, is a prerequisite
before Layer 1 can be claimed as a contribution rather than an interface.

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
| `engine.py` | orchestration and report formatting |
| `cli.py` | command line |
| `nl.py` | Layer 1 extractors + evaluation |
| `data/nl_queries.json` | Layer 1 ground truth |
| `synth.py` | controlled instance generation |
| `evaluate.py` | E1–E4 |
| `out/` | generated results (gitignored) |

## Reproducing

Requires the parent repository's `results/summary.csv` and `datasets/raw/`.
No network access, no API key (unless `--llm` is used for Layer 1).

```bash
python -m recommender.metafeatures   # rebuild the meta-feature cache
python -m recommender.evaluate       # E1-E4
python -m recommender.nl --eval      # Layer 1
```
