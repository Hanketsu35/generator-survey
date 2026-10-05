# peakrun

Exact peak memory of a child process: `peakrun OUTFILE CMD [ARGS...]` runs
CMD and writes its `ru_maxrss` (from `wait4`, in KiB) to OUTFILE. Every
benchmark and probe run in this repository goes through it
(`src/metrics.py`); see `results/peak_method_check.csv` for why polling is
not enough.

Build (Linux):

    gcc -O2 -static -o tools/peakrun/peakrun tools/peakrun/peakrun.c

Without the binary the harness warns and falls back to polled VmHWM.
