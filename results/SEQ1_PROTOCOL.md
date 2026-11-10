# SEQ1: the recommender on sequential data it has not seen

Written and committed before any miner ran on these instances. The
thresholds (`results/seq1_instances.csv`) were computed from item supports
only.

## Why

Every confirmation so far has been transactional. The recommender also
serves sequential requests (FEAT, FSGP, VGEN), with cost models fitted on
three sequential datasets (bible, leviathan, sign), and no confirmation
covers that family. Reviewers asked for one family besides the
transactional one, end to end.

## Data and runs

- **Datasets:** MSNBC, FIFA and BIKE in SPMF sequence format
  (`datasets/candidates/`, copied to `datasets/raw/*_seq.txt`). None has
  been used as sequential data before.
- **Thresholds:** the sigma at which 5, 10, 15, 20, 30, 60 and 100 single
  items are frequent, with an absolute support of at least 10 and duplicates
  dropped, placed at s - 0.25. This gives 16 instances.
- **Runs:** FEAT, FSGP and VGEN on every instance, with a 600 s cutoff and
  the JVM default heap. Runs go one at a time, and each starts only when
  10 GB are free (`tools/seq1_eval.py --run`, `results/seq1_summary.csv`).
- **Recommender:** the deployed engine, with the default sequential request
  (sequential generators, any threshold side). There is no probe, because
  the sequential miners are JVM programs.

## Criteria

Geometric-mean regret against the cheapest completed miner; a failed pick
counts as 10. The single best (SBS) is the miner with the lowest
geometric-mean cost on the sequential training runs.

- **S1 (primary):** runtime. Recommender regret <= SBS regret.
- **S2:** memory. Recommender regret <= SBS regret.
- **S3 (reported only):** the share of floor and ceiling requests on which
  the cheapest completed miner keeps the wrong threshold side. The
  recommender excludes these miners by construction.

No interval criterion: the sequential intervals are not calibrated and are
not shown (Section 5.4 of the paper).

## Frozen

`recommender/engine.py`, `recommender/capabilities.py`,
`recommender/perfmodel.py`, `recommender/survival.py`,
`results/exact/training_all.csv`, `tools/seq1_eval.py`.
