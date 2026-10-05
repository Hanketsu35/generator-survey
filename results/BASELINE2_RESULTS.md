# Is the memory gain just from measuring? Results

Protocol: `BASELINE2_PROTOCOL.md` (2008a17). Script
`tools/baseline2_comparison.py --af-wallclock 1800`. Rows in
`baseline2_rows.csv`, output in `baseline2_output.txt`, log in
`baseline2.log`. Training with probe features: 531 rows, 59 instances,
15 datasets.

## Memory regret (geometric mean, failed pick = 10)

| method | PRIMARY (119 inst., 32 datasets) | all (335 inst., 90 datasets) |
|---|---|---|
| recommender, probe | 1.030x [1.006-1.062], 0 failed | 1.018x [1.006-1.033], 0 failed |
| probe-argmin | 1.029x [1.005-1.061], 0 failed | 1.025x [1.009-1.044], 1 failed |
| ISAC + probe features | 1.078x [1.031-1.132], 1 failed | 1.066x, 1 failed |
| regression + probe features | 1.096x | 1.105x |
| AutoFolio + probe features | 1.098x | 1.120x |
| SUNNY + probe features | 1.142x | 1.167x |
| pairwise + probe features | 1.145x, 1 failed | 1.110x, 2 failed |

## Registered criteria

| criterion | result |
|---|---|
| B1: recommender <= 1.02 x probe-argmin (PRIMARY) | **PASS**: ratio 1.001 [1.000-1.002]; the same pick on 99.2% of instances |
| B2: recommender better than the best probe-feature selector, P >= 0.95 (PRIMARY) | **PASS**: against ISAC + probe, ratio 0.955 [0.918-0.986], P = 0.9995 |

## What it means (as the protocol fixed in advance)

- **B1 passes.** The gain comes from the probe's measurement. On the
  ranking, the recommender is reading the probe: it picks what probe-argmin
  picks on all but one PRIMARY instance. It loses nothing by also carrying
  the semantic filter, the model for the JVM miners and the intervals. On
  all 335 instances it has one failed pick fewer than probe-argmin. The
  paper says this plainly, and does not attribute the memory gain to the
  ranking model.
- **B2 passes.** Given the same measurements as features, learned selectors
  do worse than reading the measurement directly (1.066-1.167x). With 59
  training instances, a learned mapping from probe values to the best miner
  is noisier than the identity.

## AutoFolio seeds (gap G5)

`tools/autofolio_seeds.py`; the rule, fixed before running, was to report the
mean and the range.

| seed | PRIMARY | all |
|---|---|---|
| 12345 (published run) | 1.137x | 1.133x |
| 1 | 1.145x, 1 failed | 1.109x, 2 failed |
| 2 | 1.137x, 1 failed | 1.133x, 3 failed |
| **mean (range)** | **1.140x (1.137-1.145)** | **1.125x (1.109-1.133)** |

The comparison with AutoFolio does not depend on its seed.
