# Which datasets the cost models are fitted on (found 2026-11-11)

Since 7c34ac9 (2026-10-03, "Train on all 81 benchmarked datasets") the
engine has read `results/exact/training_all.csv`, which holds 81 datasets
and 3,284 runs. The cost models, however, are fitted on only **22** of them
(1,054 runs). `recommender/perfmodel.load_runs` joins the runs with the
meta-feature cache `recommender/data/metafeatures.json` by an inner join.
That cache covers only the configured datasets, so the 59 datasets added
later (the UCI and OpenML confirmation sets up to FRESH6, and the later SPMF
sets) are dropped without a message. Every version of the cache since that
commit has the same 22 training datasets. FGC-Stream's cost model was
therefore fitted on 7 datasets, not 57 as `INTERVAL_ALLDATA_POSTHOC.md`
states.

What is not affected:
- **Every pre-registered result** (FRESH7, FRESH8, BASELINE, BASELINE2,
  FRESH9) was scored with the engine as it actually ran, that is, with cost
  models on 22 datasets. The results describe that system.
- **The interval calibration.** The leave-one-dataset-out residuals were
  computed for runs on 75 datasets (`tools/interval_pool_all.py`,
  `tools/interval_pool_exact.py`, which compute each held-out dataset's
  features from its file); only the model producing them was fitted on 22.
- **The fix for FRESH6.** FGC-Stream's intervals were calibrated as their
  own group on those residuals. That, and not a larger training set, is what
  the runtime intervals of FRESH7 and FRESH8 rest on.

What was wrong: the descriptions "the engine trains on all 81 datasets"
(README, `recommender/README.md`, the manuscript). They are corrected. The
code is left as it is, because the confirmations tested it in this form;
fitting on all 81 would be a new configuration needing its own test.
`tools/review_learning_curve.py` reports, post hoc, what the selectors and
the recommender score on PRIMARY when fitted on all 81 datasets.
