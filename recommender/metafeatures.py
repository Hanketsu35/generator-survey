"""Cheap dataset meta-features for Layer 3.

Rice's algorithm-selection framework needs a feature map from problem
instances to a space in which algorithm performance is predictable.  The
constraint here is that computing the features must be much cheaper than
running the miner -- otherwise the recommender costs more than the guess it
saves.  Every feature below is obtained in a single streaming pass with no
itemset enumeration whatsoever.

The features are deliberately structural (size, density, skew) rather than
pattern-based: a pattern-based feature such as "number of closed itemsets at
sigma" would be a miniature instance of the problem we are trying to avoid
solving.
"""
import json
import math
import os
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE = os.path.join(_HERE, "data", "metafeatures.json")

FEATURE_NAMES = (
    "log_n_tx",
    "log_n_items",
    "avg_len",
    "max_len",
    "len_cv",          # coefficient of variation of transaction length
    "density",         # avg_len / n_items
    "log_density",
    "sup_gini",        # skew of the item-support distribution
    "sup_entropy",     # normalised Shannon entropy of item supports
    "max_sup_ratio",   # support of the most frequent item / |D|
)


def _gini(values):
    s = sorted(values)
    n = len(s)
    tot = sum(s)
    if n == 0 or tot == 0:
        return 0.0
    cum = sum((2 * i - n + 1) * v for i, v in enumerate(s))
    return cum / (n * tot)


def _entropy(counts):
    tot = sum(counts)
    if tot <= 0 or len(counts) <= 1:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / tot
            h -= p * math.log(p)
    return h / math.log(len(counts))


def _iter_records(path, data_type):
    """Yield the set of distinct items of each record.

    Handles the three SPMF layouts the benchmark uses:
      transactional : whitespace-separated item ids
      sequential    : itemsets delimited by -1, sequence terminated by -2
      utility       : 'items : total : per-item utilities'
    """
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("@"):
                continue
            if data_type == "utility":
                parts = line.split(":")
                toks = parts[0].split()
            elif data_type == "sequential":
                toks = [t for t in line.split() if t not in ("-1", "-2")]
            else:
                toks = line.split()
            if toks:
                yield toks


_EXTRACTED = {}


def extract(path, data_type="transactional"):
    """Single-pass meta-feature extraction.  Returns a dict (a copy).

    Memoised on (path, size, mtime, data_type): the chat asks for the same
    file's features on every turn, and a pass over chicago takes 1.7 s.
    """
    try:
        st = os.stat(path)
        key = (os.path.abspath(path), st.st_size, st.st_mtime_ns, data_type)
    except OSError:
        key = None
    if key is not None and key in _EXTRACTED:
        return dict(_EXTRACTED[key])
    out = _extract(path, data_type)
    if key is not None:
        if len(_EXTRACTED) > 64:
            _EXTRACTED.clear()
        _EXTRACTED[key] = dict(out)
    return out


def _extract(path, data_type="transactional"):
    """Single-pass meta-feature extraction.  Returns a dict."""
    counts = Counter()
    n = 0
    tot_len = 0
    sq_len = 0
    max_len = 0
    for toks in _iter_records(path, data_type):
        items = set(toks)
        k = len(items)
        n += 1
        tot_len += k
        sq_len += k * k
        if k > max_len:
            max_len = k
        counts.update(items)

    if n == 0:
        raise ValueError("no records parsed from %s" % path)

    m = max(len(counts), 1)
    avg = tot_len / n
    var = max(sq_len / n - avg * avg, 0.0)
    density = avg / m
    sup = list(counts.values())

    return {
        "n_tx": n,
        "n_items": m,
        "log_n_tx": math.log10(n),
        "log_n_items": math.log10(m),
        "avg_len": avg,
        "max_len": float(max_len),
        "len_cv": (math.sqrt(var) / avg) if avg else 0.0,
        "density": density,
        "log_density": math.log10(max(density, 1e-9)),
        "sup_gini": _gini(sup),
        "sup_entropy": _entropy(sup),
        "max_sup_ratio": max(sup) / n,
    }


def vector(feats):
    """Ordered numeric vector in FEATURE_NAMES order."""
    return [float(feats[k]) for k in FEATURE_NAMES]


# ----------------------------------------------------------------------
# Cache, so that a recommendation for a named benchmark dataset works even
# when the raw data is not present on the machine.
# ----------------------------------------------------------------------
def load_cache():
    if os.path.exists(_CACHE):
        with open(_CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(cache):
    with open(_CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, sort_keys=True)


DATASET_TYPES = {
    "chess": "transactional", "connect": "transactional",
    "mushroom": "transactional", "pumsb": "transactional",
    "accidents": "transactional", "retail": "transactional",
    "t10i4d100k": "transactional",
    "bible": "sequential", "leviathan": "sequential", "sign": "sequential",
    "chainstore": "utility", "foodmart": "utility",
}

RAW_DIR = os.path.join(os.path.dirname(_HERE), "datasets", "raw")
UTIL_DIR = os.path.join(os.path.dirname(_HERE), "datasets", "spmf_format")
SYN_DIR = os.path.join(os.path.dirname(_HERE), "datasets", "synthetic")

#: Synthetic datasets are named by their generating parameters (see synth.py),
#: so they are recognised by prefix rather than listed in DATASET_TYPES. They
#: are always transactional.
SYN_PREFIX = "syn_"


def is_synthetic(name):
    return str(name).startswith(SYN_PREFIX)


def dataset_path(name):
    if is_synthetic(name):
        return os.path.join(SYN_DIR, "%s.txt" % name)
    t = DATASET_TYPES.get(name, "transactional")
    if t == "utility":
        p = os.path.join(UTIL_DIR, "%s_utility_fixed.txt" % name)
        if os.path.exists(p):
            return p
    return os.path.join(RAW_DIR, "%s.txt" % name)


def data_type(name):
    """Input format of a dataset by name; synthetic ones are transactional."""
    if is_synthetic(name):
        return "transactional"
    return DATASET_TYPES.get(name, "transactional")


def for_dataset(name, use_cache=True):
    """Meta-features of a named benchmark dataset, cached on first use."""
    cache = load_cache() if use_cache else {}
    if name in cache:
        return cache[name]
    feats = extract(dataset_path(name), data_type(name))
    cache[name] = feats
    save_cache(cache)
    return feats


def build_cache(names=None):
    """Recompute the cache for every benchmark dataset present on disk."""
    names = names or list(DATASET_TYPES)
    cache = load_cache()
    for nm in names:
        p = dataset_path(nm)
        if not os.path.exists(p):
            continue
        cache[nm] = extract(p, data_type(nm))
    save_cache(cache)
    return cache


if __name__ == "__main__":
    c = build_cache()
    hdr = ["dataset"] + list(FEATURE_NAMES)
    print("  ".join("%-13s" % h for h in hdr))
    for nm in sorted(c):
        row = ["%-13s" % nm] + ["%-13.4f" % c[nm][k] for k in FEATURE_NAMES]
        print("  ".join(row))
