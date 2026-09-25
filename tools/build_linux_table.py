"""The published table, every row measured on this machine: results/summary_linux.csv.

    python tools/build_linux_table.py

Each of the 667 configurations of results/summary.csv, with its runtime,
peak memory, generator count, timeout flag and error taken from:

  results/remeasured.csv          short completed runs, 3 repeats, median
                                  (valid rows only: all repeats ran, count
                                  equal to the recorded one)
  results/published_linux_rerun.csv  everything else, one run each

A configuration found in neither is reported and the build fails: the point
of this table is that no row is a Windows number.

The generator count is the recorded one wherever the rerun completed and
agreed with it (remeasure/rerun compare it); where the outcome changed --
a Windows timeout that completes here, a crash that no longer crashes -- the
new count is used and the row is listed.
"""
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))
os.chdir(_ROOT)

import remeasure_eval as E                               # noqa: E402

RERUN = _ROOT / "results" / "published_linux_rerun.csv"
OUT = _ROOT / "results" / "summary_linux.csv"


def _k(a, d, p):
    return (a, d, round(float(p), 9))


def build():
    summ = pd.read_csv(E.SUMMARY, dtype={"generator_count": str})
    _all, rem = E.valid_remeasured()
    rem = rem[rem.source == "summary"]
    rr = pd.read_csv(RERUN, dtype={"generator_count": str, "generator_count_recorded": str})
    by_rem = {_k(a, d, p): r for a, d, p, r in
              zip(rem.algorithm, rem.dataset, rem.param_value, rem.itertuples())}
    by_rr = {_k(a, d, p): r for a, d, p, r in
             zip(rr.algorithm, rr.dataset, rr.param_value, rr.itertuples())}
    out, missing, changed = [], [], []
    for r in summ.itertuples(index=False):
        k = _k(r.algorithm, r.dataset, r.param_value)
        row = r._asdict()
        if k in by_rem:
            x = by_rem[k]
            row.update(runtime_s=x.runtime_s, peak_memory_mb=x.peak_memory_mb,
                       source="remeasured")
        elif k in by_rr:
            x = by_rr[k]
            was = ("timeout" if str(r.timed_out).lower() == "true"
                   else "error" if pd.notna(r.error) else "ok")
            now = "timeout" if x.timed_out else ("error" if isinstance(x.error, str) and x.error
                                                  else "ok")
            row.update(runtime_s=x.runtime_s, peak_memory_mb=x.peak_memory_mb,
                       timed_out=bool(x.timed_out),
                       error=x.error if now == "error" else None,
                       generator_count=(x.generator_count if now == "ok" else None),
                       source="rerun")
            if was != now or x.count_matches is False:
                changed.append((r.algorithm, r.dataset, r.param_value, was, now,
                                r.generator_count, x.generator_count))
        else:
            missing.append(k)
            continue
        row["machine"] = "Linux x86_64"
        out.append(row)
    if missing:
        print("MISSING %d configurations -- not built:" % len(missing))
        for k in missing[:20]:
            print("   ", k)
        return None
    df = pd.DataFrame(out)
    df.to_csv(OUT, index=False)
    print("-> %s: %d rows (%d re-measured, %d re-run)"
          % (OUT.relative_to(_ROOT), len(df), (df.source == "remeasured").sum(),
             (df.source == "rerun").sum()))
    if changed:
        print("outcome changed on this machine (%d):" % len(changed))
        for c in changed:
            print("   %-22s %-11s %-8s %-7s -> %-7s  count %s -> %s" % c)
    return df


if __name__ == "__main__":
    sys.exit(0 if build() is not None else 1)
