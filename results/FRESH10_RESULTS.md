# FRESH10: results

Protocol: `FRESH10_PROTOCOL.md` (d949ec7). The truth runs are in
`fresh10_summary.csv`: 210 runs in 11.1 h, of which 58 timed out and 30
ended with errors (most of them out of memory under the cap). Scores are in
`fresh10_eval_output.txt` and `fresh10_eval_rows.csv`. The frozen files
matched the protocol commit.

## Results

- **H1 (primary): PASS.** With its probe, the recommender picked the best
  implementation on every one of the 19 scorable instances (regret
  1.000x), with no failed pick (probe-argmin: 0). Seventeen of these were
  sampled probes. On the same instances, the heaviest completed alternative
  needed 13.3 times the best peak in the median (271 times at most). A
  median of 3 of the 10 implementations did not complete, and the slowest
  completed run took 72 s in the median.
- **H2: FAIL.** With cost models fitted on 81 datasets, memory regret
  without a probe was 1.396x, against 1.337x for the deployed models fitted
  on 22.
- **H3: FAIL.** On runtime the 81-dataset models scored 1.562x, against
  1.281x.
- **Intervals of the deployed engine: all pass.**

  | interval | coverage | lowest dataset | bar |
  |---|---|---|---|
  | Y1, sampled probe | 0.938 | 0.75 | 0.90 |
  | Y2, model runtime | 0.989 | — | 0.95 |
  | Y3, model memory | 1.000 | — | 0.95 |
  | Y4, measured probe (3 datasets) | 1.000 | — | 0.95 |

## Consequence (as the protocol fixes it)

H2 and H3 failed, so the engine keeps its cost models fitted on 22 datasets.
The post hoc gain on PRIMARY (`review_learning_curve_output.txt`) did not
hold on new hard instances.
