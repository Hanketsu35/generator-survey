# Eighth fresh confirmation: the probe's sampled interval, on large data

Written and committed before any miner or probe ran on these datasets.

## Why

`FRESH7_RESULTS.md` confirmed every interval the engine shows, except the
probe's interval for SAMPLED values (90%). FRESH7 had one dataset large
enough for the probe to sample (numerai), below the three the protocol
required. The configuration is unchanged since FRESH7; this tests that one
interval, with the others checked again.

## Data: selection rule, fixed here

OpenML, every active dataset with 80,000-1,500,000 instances and 3-40
features (API listing, 2026-10-04: 561). The rule:
1. **Format.** Dense ARFF only.
2. **Synthetic generators out:** BNG (Bayesian-network samples of small UCI
   sets), RandomRBF, Hyperplane, SEA, LED, Stylized, mlr, and similar.
3. **Used or related out:** poker, covertype, census, adult, bank, skin,
   SUSY, HIGGS, MiniBooNE, diabetes, electricity, chess, connect, kosarak,
   retail, accidents, pamap, recordlink, chicago, mushroom, instacart,
   numerai, letter, pendigits, satimage, jungle, airlines.
4. **Families.** One per family (name prefix, letters and digits only),
   the lowest data id.
5. **Count.** The first 8 by data id.

The result (`fresh8_selection.json`): Click_prediction_small, ldpa,
spoken-arabic-digit, walking-activity, creditcard, SensorDataResource,
COMET_MC_SAMPLE, fars. A first pass of rule 4 split spoken-arabic-digit from
SpokenArabicDigit, the same source; this was corrected before any file was
read. Selection used metadata only.

Converted by the rule of FRESH4-7 (`tools/prepare_fresh8.py`,
`fresh8_prepare.txt`). SensorDataResource has a per-row identifier column,
which the rule turns into 127,704 items that are never frequent; it is left
as the rule gives it.

That gives 31 instances, 100,968-1,496,391 transactions each, so the probe
samples at every level. Ten implementations, 600 s cutoff
(`tools/bench_real_extra.py ... --out results/fresh8_summary.csv`).

## Frozen

As FRESH7 (this commit): `engine.py`, `probe.py`, `intervals.py`,
`data/intervals.json`, `perfmodel.py`, `survival.py`,
`results/exact/training_all.csv`.

## Criteria (mean per-dataset coverage; each bar is the guarantee)

- **Y1 (primary):** probe memory interval, sampled (90%): >= 0.90.
- **Y2:** model runtime interval (95%): >= 0.95.
- **Y3:** model memory interval (95%): >= 0.95.
- **Y4:** probe memory interval, measured (95%): >= 0.95, only if at least 3
  datasets have measured values (here a probe measures only when every
  sample size would exceed half the file); otherwise reported only.
