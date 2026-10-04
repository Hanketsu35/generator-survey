# Baseline comparison: results

Protocol: `BASELINE_PROTOCOL.md` (b17ef35). Script:
`tools/baseline_comparison.py`. Rows: `baseline_rows.csv`; full output:
`baseline_output.txt` (`baseline_output_noaf.txt` is the dry run without
AutoFolio, identical otherwise).

Every method is trained on `results/exact/training_runs.csv` (22 datasets)
and chooses among the same semantically eligible implementations. Regret is
the geometric mean against the best completed eligible implementation; a
failed pick counts as 10. Bands are 5-95% cluster bootstrap over datasets.

## Memory objective

| method | primary: FRESH7+8, 32 datasets | all test sets, 90 datasets |
|---|---|---|
| **recommender, with probe** | **1.030x [1.005-1.064]**, 0 failed | **1.018x [1.006-1.031]**, 0 failed |
| ISAC | 1.132x [1.050-1.230] | 1.121x [1.076-1.170] |
| AutoFolio (SMAC, 1,800 s) | 1.137x [1.059-1.233] | 1.133x [1.072-1.208] |
| pairwise ranking (SATzilla-11 style) | 1.181x | 1.155x |
| per-algorithm regression (EPM) | 1.225x | 1.163x |
| SUNNY (k = 16) | 1.357x | 1.344x |
| recommender, no probe | 2.023x | 1.739x |
| survival (Run2Survive) | 2.641x | 2.349x |
| SBS | 2.682x | 2.653x |
| random | 5.182x | 4.934x |

Paired cluster bootstrap on the primary subset:
- probe vs ISAC: ratio 0.915 [0.839-0.974], P(probe better) = 0.9998;
- probe vs AutoFolio: ratio 0.911 [0.836-0.971], P = 0.9998.

On all 90 datasets the ratios are 0.909 and 0.900, P = 1.000.

## Runtime objective (no probe: it does not pay on runtime)

| method | primary, 32 datasets | all, 90 datasets |
|---|---|---|
| pairwise ranking | 1.205x [1.105-1.332] | 1.221x |
| recommender (model) | 1.220x [1.119-1.351] | 1.280x |
| SUNNY | 1.239x | 1.256x |
| regression | 1.261x | 1.277x |
| SBS | 1.262x | 1.368x |
| AutoFolio | 1.286x | 1.277x |
| ISAC | 1.315x | 1.232x |
| survival | 1.317x | 1.417x |
| random | 4.977x | 5.125x |

The recommender's runtime choice is level with the learned selectors, all
within overlapping bands. Runtime headroom over SBS is small on this
portfolio: SBS is 1.26-1.37x.

## Semantics: unrestricted selectors

Allowed every implementation that ran, the learned selectors almost never
picked one Layer 2 rejects:
- 0% for all of them on memory;
- up to 1.7% (survival) on runtime;
- random picks one 21-25% of the time.

The unsound implementations in this portfolio (Talky-G and its diffset
variant) are rarely the cheapest, so here a performance-driven selector
avoids them by accident. Layer 2's value lies where this comparison does not
reach: a wrong pattern family (HUCI-Miner), a configuration trap
(Gr-growth's k), boundary and empty-set conventions, and the other mining
categories. That is measured separately (experiment E2), not here.

## Reading

- **Memory.** The recommender's advantage on memory comes from the probe.
  It beats AutoFolio and every other standard selector by about 9-10% in
  geometric-mean regret, with no failed pick. Without the probe its model is
  worse than the learned selectors.
- **Runtime.** It is level with them.
