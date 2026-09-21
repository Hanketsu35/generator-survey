Diagnostic re-run of Arima's five OOM configurations with -Xmx12g.
See tools/rerun_arima_xmx.py and results/arima_xmx_diagnostic.csv.

Only Arima_chess_0.3.txt is present: it is the sole configuration that
completed (107.4 s, 8,173 MB, 180,161 generators).

The other four (chess 0.1, chess 0.2, connect 0.2, connect 0.3) again threw
java.lang.OutOfMemoryError at 11.1-11.8 GB. Their output files were TRUNCATED
at the point of abort and have been deleted: counting lines in a truncated
file yields a plausible-looking but invalid generator count, which is the
exact defect this audit fixed in src/metrics.py.
