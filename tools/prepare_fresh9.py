"""Download and convert the datasets of the ninth fresh confirmation.

    python tools/prepare_fresh9.py --download          # OpenML parquet files
    <python with pyarrow> tools/prepare_fresh9.py --to-csv
    python tools/prepare_fresh9.py                     # transactions

Datasets: results/fresh9_selection.json (tools/select_fresh9.py). OpenML's
ARFF server delivered about 50 KB/s on 2026-11-09, so the files are taken from
OpenML's parquet copies (the dataset description's parquet_url), which hold
the same attributes. --to-csv writes each one as a CSV of strings (a missing
value is empty); it needs pyarrow, which the project environment does not
have, and was run in a separate environment. The conversion is then the rule
of FRESH4-8 for CSV sources: read every value as a string,
tools/prepare_fresh4.convert. Files are kept in
datasets/candidates/openml_fresh9/. Names are prefixed "oml_". Counts go to
results/fresh9_prepare.txt.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))

SRC = _ROOT / "datasets" / "candidates" / "openml_fresh9"
RAW = _ROOT / "datasets" / "raw"
SEL = _ROOT / "results" / "fresh9_selection.json"
LOG = _ROOT / "results" / "fresh9_prepare.txt"


def safe(name):
    return "oml_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def download(sel):
    SRC.mkdir(parents=True, exist_ok=True)
    hdr = {"User-Agent": "generator-survey benchmark"}
    for did, name, _n, _f, _fid in sel:
        p = SRC / ("%s.pq" % name)
        if p.exists() and p.stat().st_size > 0:
            continue
        with urllib.request.urlopen(urllib.request.Request(
                "https://www.openml.org/api/v1/json/data/%d" % did, headers=hdr), timeout=120) as r:
            url = json.load(r)["data_set_description"]["parquet_url"]
        print("download", did, name, url, flush=True)
        tmp = p.with_suffix(".part")
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=600) as r, \
                open(tmp, "wb") as fo:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                fo.write(b)
        tmp.rename(p)


def to_csv(sel):
    for _did, name, _n, _f, _fid in sel:
        c = SRC / ("%s.csv.gz" % name)
        if c.exists() or not (SRC / ("%s.pq" % name)).exists():
            continue
        d = pd.read_parquet(SRC / ("%s.pq" % name))
        d.astype(object).where(d.notna(), None).to_csv(c, index=False, na_rep="")
        print("csv", name, d.shape, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--to-csv", action="store_true")
    args = ap.parse_args(argv)
    sel = json.load(open(SEL))
    if args.download:
        download(sel)
        return 0
    if args.to_csv:
        to_csv(sel)
        return 0
    from prepare_fresh4 import convert
    out = []
    for _did, name, _n, _f, _fid in sel:
        d = pd.read_csv(SRC / ("%s.csv.gz" % name), dtype=str, keep_default_na=False)
        d = d.replace({"": None}).dropna(how="all")
        m, n_items = convert(d)
        del d
        n = 0
        with open(RAW / ("%s.txt" % safe(name)), "w") as fo:
            for row in m.itertuples(index=False):
                u = sorted({int(x) for x in row if x is not None and x == x})
                if u:
                    fo.write(" ".join(map(str, u)) + "\n")
                    n += 1
        msg = "%-40s %8d tx  %7d items  %3d columns" % (safe(name), n, n_items, m.shape[1])
        print(msg, flush=True)
        out.append(msg)
    LOG.write_text("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
