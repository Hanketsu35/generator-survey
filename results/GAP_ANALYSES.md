# Further views of the baseline comparison (gaps G2-G4)

Script `tools/gap_stats.py`; output `gap_stats_output.txt`. These are not
new tests. They look at `baseline_rows.csv` and the stored probes in more
ways, after `BASELINE_RESULTS.md`, and they are reported whatever they show.

## G3: regret in megabytes (memory, pick's peak minus the best eligible peak)

| | PRIMARY median | PRIMARY mean | > 10 MB | > 100 MB | all: mean | all: > 10 MB |
|---|---|---|---|---|---|---|
| recommender, probe | 0.0 MB | 65.2 MB | 4.2% | 2.5% | 28.6 MB | 2.4% |
| AutoFolio | 0.0 | 45.9 | 14.4% | 6.8% | 54.8 | 11.4% |
| ISAC | 0.0 | 45.0 | 13.6% | 6.8% | 32.2 | 9.1% |
| SUNNY | 0.0 | 22.8 | 24.6% | 5.9% | 47.3 | 20.7% |
| pairwise | 0.0 | 42.3 | 16.2% | 2.6% | 32.0 | 11.6% |
| recommender, no probe | 10.6 | 51.3 | 54.2% | 6.8% | 59.1 | 39.0% |
| SBS | 10.8 | 81.8 | 69.7% | 6.7% | 72.4 | 64.8% |

(failed picks excluded from the megabytes, counted in `gap_stats_output.txt`)

**Reading.** The recommender misses by more than 10 MB far less often than
any selector (4.2% vs 13.6-24.6% on PRIMARY). On PRIMARY its *mean* miss is
larger than AutoFolio's, ISAC's and SUNNY's. A few large instances cause
this: there, an extrapolation error of a few percent is tens of megabytes.
The ratio and the megabytes answer different questions, and the paper
reports both.

## G2: the probe's time

| | PRIMARY | all |
|---|---|---|
| probe wall time, median / 90% / max | 0.14 / 1.2 / 67.5 s | 0.16 / 1.9 / 68.0 s |
| runtime of the recommended run, median | 0.03 s | 0.03 s |
| the probe already produced the output (direct, measured) | 68.9% | 72.5% |
| extra time beyond the run, median / 90% | 0.10 / 0.9 s | 0.11 / 1.4 s |
| extra time longer than the run itself | 85.7% | 81.8% |
| on runs of >= 10 s: extra / run, median | 0.64 (5 runs) | 0.32 (18 runs) |

**Reading.** In absolute terms the probe costs about a tenth of a second
typically and about a minute at most. Most mining runs here are shorter
still, so the probe usually takes longer than the run it informs. It pays
when memory is the constraint, not time: the user asked for the
lowest-memory miner, and a second of probing is the price of a
measurement. It is not a way to save time, and the paper does not
present it as one.

## G4: conventional tests (memory)

Wilcoxon signed-rank tests on per-dataset mean log regret, recommender
with probe against each method, Holm-corrected. On PRIMARY (32 datasets)
every comparison is significant at 0.05: against AutoFolio, 11 datasets
better, 5 worse, 16 tied, Holm p = 0.034; against ISAC 9/4/19, p = 0.034.
On all 90 datasets every Holm p is below 0.001.

The Friedman test rejects equal ranks (PRIMARY chi2 = 172.6, p = 1.8e-32).
The average ranks on PRIMARY are: recommender 3.22, AutoFolio 3.81,
ISAC 3.89, pairwise 4.14, regression 4.20, SUNNY 4.78, the recommender
without probe 6.66, SBS 7.38, survival 7.42, random 9.50. The Nemenyi
critical difference (alpha = 0.05, k = 10) is 2.39 on PRIMARY and 1.43 on
all 90 datasets.

**Reading.** The paired tests favour the recommender over every method.
The Nemenyi post hoc test, which is much more conservative with ten methods,
does not separate it from the five learned selectors on PRIMARY
(differences 0.59-1.56 < 2.39). On all 90 datasets it separates it from
SUNNY and everything below (1.67 >= 1.43), but not from AutoFolio, ISAC,
pairwise or regression (0.62-0.88). Both results are stated in the paper.
