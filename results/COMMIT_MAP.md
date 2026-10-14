# Commit map

The history has been rewritten twice. Before the first public push, commit
messages were edited. On 2026-10-05, the manuscripts, drafts, notes and logs
were removed from every commit and the result was force-pushed. Each rewrite
changed the commit hashes but not the dates, the order, or the content of any
file that is still tracked. The references in the protocols, results and
scripts now name the current hashes. This table maps the hashes they named
before the second rewrite, for anyone holding an older copy.

| Date | Before | Now | Commit |
|---|---|---|---|
| 2026-09-23 | `325800a` | `3882ae1` | Freeze the Layer 1 configuration before scoring the test split |
| 2026-09-24 | `594fd7a` | `831646d` | Stream every output counter; keep a failed program's last message |
| 2026-09-24 | `ededb6a` | `c80f65d` | Pre-register the second extension: five datasets chosen for memory disagreement |
| 2026-09-29 | `1d1811f` | `11e1a48` | Pre-register a confirmation of the memory probe on five unseen datasets |
| 2026-09-29 | `5f2467a` | `3cdbf91` | Train the engine on every dataset measured on this machine |
| 2026-09-29 | `ced9dc7` | `57a6441` | Document the probe: literature, method, pre-registered result, decision |
| 2026-09-30 | `3db7c8e` | `70294c5` | Pre-register conformal prediction intervals for cost estimates |
| 2026-09-30 | `4ea63c4` | `01c01df` | Pre-register a hard-threshold confirmation of the memory probe on four unseen datasets |
| 2026-09-30 | `4eb8f25` | `bc67b9a` | Show 90% prediction intervals; rank probed memory by the interval's upper end |
| 2026-09-30 | `a1d9867` | `cfeeb9a` | Pre-register a fresh confirmation of the shipped memory ranking on eight newly downloaded datasets |
| 2026-10-01 | `2ff1a5b` | `db36d0e` | Demote a probed miner that lags in its probe; pre-register its test on three new UCI datasets |
| 2026-10-01 | `7664db1` | `1db85d4` | Extrapolate Gr-growth's memory as a fixed map plus a power law; pre-register its test on four large UCI datasets |
| 2026-10-02 | `4a2560d` | `08d9ecf` | Pre-register a targeted test of the progress rule on instances where a probed miner lags |
| 2026-10-02 | `861fd9a` | `f810d69` | Show 95% intervals calibrated over datasets (CDF pooling); pre-register their test on ten new UCI datasets |
| 2026-10-03 | `114debe` | `dda968a` | Pre-register a sixth fresh confirmation: median-centred, class-split runtime intervals on thirteen new datasets |
| 2026-10-03 | `4191068` | `9b7b61f` | Pre-register a fifth fresh confirmation: guaranteed intervals on exact memory, twelve new datasets |
| 2026-10-03 | `a46c8b8` | `d0fa21f` | Pre-register a seventh fresh confirmation on 24 OpenML-CC18 datasets selected by rule |
| 2026-10-04 | `2218f2b` | `7c9eed2` | Add ISAC and AutoFolio selectors; fix the baseline comparison's plan before computing it |
| 2026-10-04 | `e918d4e` | `ad2b085` | Pre-register an eighth fresh confirmation: the sampled probe interval on eight large OpenML datasets |
| 2026-10-05 | `03c6bfc` | `a2443d1` | Pre-register testing the progress rule on the instances where it acted after it was frozen |
| 2026-10-05 | `2008a17` | `2ae3765` | Pre-register two baselines that separate the recommender from measuring: probe-argmin and selectors given the probe |
| 2026-10-05 | `2ef6ff6` | `3ad27a7` | Pre-register rebuilding the ranking quantiles on exact memory |
| 2026-10-05 | `59500fb` | `4c56655` | Rank on quantiles from the exact pools; no pick changes on any of 335 test instances |
