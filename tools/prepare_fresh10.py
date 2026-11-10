"""Download and convert the datasets of FRESH10 (results/FRESH10_PROTOCOL.md).

    python tools/prepare_fresh10.py --download
    <python with pyarrow> tools/prepare_fresh10.py --to-csv
    python tools/prepare_fresh10.py

The procedure of tools/prepare_fresh9.py, applied to
results/fresh10_selection.json (the next 12 datasets after FRESH9's under
the same rule); counts go to results/fresh10_prepare.txt.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "tools"))
import prepare_fresh9 as P9                                # noqa: E402

P9.SEL = _ROOT / "results" / "fresh10_selection.json"
P9.LOG = _ROOT / "results" / "fresh10_prepare.txt"

if __name__ == "__main__":
    sys.exit(P9.main())
