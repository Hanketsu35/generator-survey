"""Select the datasets of the ninth fresh confirmation (results/FRESH9_PROTOCOL.md).

    python tools/select_fresh9.py

Applies the selection rule of results/FRESH8_PROTOCOL.md to the OpenML
listing saved in datasets/candidates/openml_fresh9/ (API, 2026-11-09:
every active dataset with 80,000-1,500,000 instances and 3-40 features),
and continues the ordering by data id after FRESH8's eight. Metadata only:
no data file is read. Writes results/fresh9_candidates.json (the whole
ordered list, FRESH8's eight marked) and results/fresh9_selection.json.
"""
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
LISTING = _ROOT / "datasets" / "candidates" / "openml_fresh9" / "openml_listing_2026-11-09.json"

# Rule 2 of FRESH8: synthetic generators.
SYNTHETIC = ("bng", "randomrbf", "hyperplane", "sea", "led", "stylized", "mlr",
             "agrawal", "stagger", "waveform", "friedman", "rbf", "mixed",
             "sine", "synthetic", "simulated", "artificial", "generated")
# Rule 3 of FRESH8: used before or related (as written there).
USED = ("poker", "covertype", "census", "adult", "bank", "skin", "susy", "higgs",
        "miniboone", "diabetes", "electricity", "chess", "connect", "kosarak",
        "retail", "accidents", "pamap", "recordlink", "chicago", "mushroom",
        "instacart", "numerai", "letter", "pendigits", "satimage", "jungle", "airlines")
N_SELECT = 24


def family(name):
    """Rule 4: the name prefix of letters and digits (up to the first other
    character), lower-cased; a prefix that starts another one, or is started
    by it, is the same family (spoken-arabic-digit and SpokenArabicDigit)."""
    return re.match(r"[a-z0-9]*", name.lower()).group(0) or name.lower()


def q(d, k):
    for x in d.get("quality", []):
        if x["name"] == k:
            return float(x["value"])
    return None


def main():
    data = json.load(open(LISTING))["data"]["dataset"]
    prev = json.load(open(_ROOT / "results" / "fresh8_selection.json"))
    prev_ids = {p[0] for p in prev}
    rows, seen = [], set()
    for d in sorted(data, key=lambda x: x["did"]):
        name, low = d["name"], d["name"].lower()
        if d.get("format", "").upper() != "ARFF":
            continue                                        # rule 1: dense ARFF only
        if any(low.startswith(s) or ("(" in low and s in low) for s in SYNTHETIC):
            continue                                        # rule 2
        if any(u in low for u in USED):
            continue                                        # rule 3
        fam = family(name)
        if any(fam.startswith(f) or f.startswith(fam) for f in seen):
            continue                                        # rule 4: one per family, lowest id
        seen.add(fam)
        rows.append([d["did"], name, int(q(d, "NumberOfInstances")), int(q(d, "NumberOfFeatures")),
                     d["file_id"], d["did"] in prev_ids])
    (_ROOT / "results" / "fresh9_candidates.json").write_text(json.dumps(rows, indent=1))
    first8 = [r[1] for r in rows[:8]]
    print("first 8 under the rule:", first8)
    print("FRESH8's 8 all among the first %d" % max(i + 1 for i, r in enumerate(rows) if r[5]))
    new = [r[:5] for r in rows if not r[5] and r[0] > max(prev_ids)][:N_SELECT]
    (_ROOT / "results" / "fresh9_selection.json").write_text(json.dumps(new, indent=1))
    for r in new:
        print(r)
    print(len(rows), "eligible;", len(new), "selected")


if __name__ == "__main__":
    sys.exit(main())
