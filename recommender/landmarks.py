"""Threshold-dependent landmark features for Layer 3.

``metafeatures.py`` describes the *dataset*. Ten of its eleven columns are
constant within a dataset, so the only thing that distinguishes two
configurations of the same dataset is ``log_thr``. Instance space analysis
measured the consequence: 95.6% of positional variance lies between datasets,
the configurations land in vertical stripes, and the effective instance count
is 7 rather than 58. Anything learned across that plane is fitted to seven
points.

Worse, ``log_thr`` is *not comparable across datasets*. The benchmark grid runs
retail at sigma = 0.0005 and pumsb at sigma = 0.95; sigma = 0.3 is trivial on
mushroom and near the hardest point of accidents. A model given raw log_thr has
to recover that interaction from seven datasets.

The meta-learning answer is **landmarking** (Pfahringer et al., 2000): describe
the instance by the behaviour of a cheap surrogate rather than by static
structure alone. The surrogate used here is the **exact level-2 statistics of
the mining problem itself**, which is the right choice for two reasons.

*   It is genuinely cheap, and cheap for a specific reason: every feature below
    is read off the item-support vector and the item co-occurrence matrix
    ``C = B^T B``. Both are computed **once per dataset**, and every threshold
    on the grid is then a thresholding of the same two arrays. Cost is one pass
    plus one matrix product, independent of how many thresholds are asked for.

*   It is not a miniature instance of the problem being avoided. Level 2 is
    where the generator property first becomes observable -- a pair {i,j} is a
    generator iff sup(ij) < min(sup(i), sup(j)) -- so the counts below measure
    closure collapse directly, while enumerating nothing beyond pairs.

The features split into three groups:

  scale-free threshold   where sigma falls in *this dataset's* support
                         distribution, instead of on an absolute axis
  level-1 landmarks      the frequent-item sub-problem the miner traverses
  level-2 landmarks      frequent pairs, generator pairs, and closure collapse

``n_gen2_frac`` and ``collapse_frac`` are the two that carry generator-specific
information: they say how much of the level-2 lattice survives minimality, and
hence how much pruning the miner gets for free.
"""
import json
import math
import os

import numpy as np

from . import metafeatures as mf

_HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE = os.path.join(_HERE, "data", "landmarks.json")

#: Feature names, in the order ``vector()`` emits them.
LANDMARK_NAMES = (
    # --- scale-free threshold ------------------------------------------
    "thr_pctile",        # fraction of items whose support is below sigma
    "log_thr_rel",       # log10(sigma / support of the most frequent item)
    "log_thr_abs",       # log10(absolute minimum support count)
    # --- level-1 -------------------------------------------------------
    "log_n_freq1",       # log10(1 + number of frequent items)
    "frac_freq1",        # frequent items / all items
    "freq_sup_mass",     # share of total item-support carried by frequent items
    "boundary_frac",     # items with support in [sigma, 2*sigma): the pruning zone
    "avg_len_freq",      # mean transaction length after infrequent items are dropped
    "density_freq",      # avg_len_freq / n_freq1
    # --- level-2 -------------------------------------------------------
    "log_n_freq2",       # log10(1 + number of frequent pairs)
    "pair_density",      # frequent pairs / all pairs of frequent items
    "n_gen2_frac",       # frequent pairs that are GENERATORS / frequent pairs
    "collapse_frac",     # frequent pairs equal in support to a singleton subset
    "log_lattice_ratio", # log10((1 + n_freq2) / (1 + n_freq1)): branching factor
)

#: Datasets wider than this use a sparse co-occurrence product; narrower ones a
#: chunked dense one. Dense is far faster when it fits, and ``sum_t |t|^2`` --
#: the nonzero count of the sparse product -- explodes on wide dense data.
_DENSE_MAX_ITEMS = 4000
_CHUNK = 20000


# ----------------------------------------------------------------------
# One pass + one matrix product per dataset
# ----------------------------------------------------------------------
def _load_matrix(path, data_type):
    """Read the file once into (indptr, indices, n_tx, item_ids).

    Items are remapped to dense column indices so that the co-occurrence
    product is over observed items only -- SPMF item ids are not contiguous
    and retail's go far above its distinct-item count.
    """
    indptr = [0]
    indices = []
    remap = {}
    n = 0
    for toks in mf._iter_records(path, data_type):
        seen = set()
        for t in toks:
            j = remap.get(t)
            if j is None:
                j = len(remap)
                remap[t] = j
            seen.add(j)
        indices.extend(sorted(seen))
        indptr.append(len(indices))
        n += 1
    if n == 0:
        raise ValueError("no records parsed from %s" % path)
    return (np.asarray(indptr, dtype=np.int64),
            np.asarray(indices, dtype=np.int32), n, len(remap))


def _cooccurrence(indptr, indices, n_tx, n_items):
    """Upper-triangular item co-occurrence counts and item supports.

    Returns ``(sup, pair_i, pair_j, pair_c)`` where the pair arrays list only
    co-occurring pairs (count > 0) with ``i < j``.
    """
    sup = np.bincount(indices, minlength=n_items).astype(np.int64)

    if n_items <= _DENSE_MAX_ITEMS:
        C = np.zeros((n_items, n_items), dtype=np.float64)
        for start in range(0, n_tx, _CHUNK):
            stop = min(start + _CHUNK, n_tx)
            rows = stop - start
            B = np.zeros((rows, n_items), dtype=np.float32)
            lo, hi = indptr[start], indptr[stop]
            seg = indices[lo:hi]
            # Row index of every nonzero in this chunk.
            counts = np.diff(indptr[start:stop + 1])
            rr = np.repeat(np.arange(rows, dtype=np.int64), counts)
            B[rr, seg] = 1.0
            C += (B.T @ B).astype(np.float64)
        iu = np.triu_indices(n_items, k=1)
        c = C[iu]
        keep = c > 0
        return sup, iu[0][keep], iu[1][keep], c[keep].astype(np.int64)

    from scipy import sparse
    data = np.ones(indices.size, dtype=np.float32)
    B = sparse.csr_matrix((data, indices, indptr), shape=(n_tx, n_items))
    C = (B.T @ B).tocoo()
    keep = C.row < C.col
    return (sup, C.row[keep].astype(np.int64), C.col[keep].astype(np.int64),
            np.rint(C.data[keep]).astype(np.int64))


class DatasetProbe:
    """Per-dataset arrays from which any threshold's landmarks are read off.

    Built once; ``at(sigma)`` is then pure array arithmetic. This is what keeps
    the features cheap enough to be worth computing at recommendation time.
    """

    def __init__(self, sup, pair_i, pair_j, pair_c, n_tx, n_items,
                 tx_len_sq_sum=None):
        self.sup = sup
        self.pair_i = pair_i
        self.pair_j = pair_j
        self.pair_c = pair_c
        self.n_tx = int(n_tx)
        self.n_items = int(n_items)
        self.total_sup = float(sup.sum())
        self.max_sup = int(sup.max()) if sup.size else 0
        # Support of the smaller singleton in each pair: the minimality test.
        self._pair_min_sup = np.minimum(sup[pair_i], sup[pair_j])

    # ------------------------------------------------------------------
    @classmethod
    def build(cls, path, data_type="transactional"):
        indptr, indices, n_tx, n_items = _load_matrix(path, data_type)
        sup, pi, pj, pc = _cooccurrence(indptr, indices, n_tx, n_items)
        probe = cls(sup, pi, pj, pc, n_tx, n_items)
        # Retained so avg_len_freq can be computed per threshold.
        probe._indptr, probe._indices = indptr, indices
        return probe

    # ------------------------------------------------------------------
    def at(self, sigma):
        """Landmark features at relative support ``sigma`` in (0, 1]."""
        n = self.n_tx
        minsup = max(sigma * n, 1.0)

        freq = self.sup >= minsup
        n_freq1 = int(freq.sum())
        frac_freq1 = n_freq1 / max(self.n_items, 1)
        freq_mass = float(self.sup[freq].sum()) / max(self.total_sup, 1.0)
        boundary = int(((self.sup >= minsup) & (self.sup < 2 * minsup)).sum())

        # Mean transaction length once infrequent items are dropped -- the
        # length the miner actually traverses, not the length on disk.
        if n_freq1 == 0:
            avg_len_freq = 0.0
        else:
            keep = freq[self._indices]
            # Number of surviving items per transaction, summed.
            avg_len_freq = float(keep.sum()) / n

        # --- level 2 ---------------------------------------------------
        pf = self.pair_c >= minsup
        n_freq2 = int(pf.sum())
        max_pairs = n_freq1 * (n_freq1 - 1) / 2.0
        pair_density = n_freq2 / max_pairs if max_pairs > 0 else 0.0

        if n_freq2 > 0:
            # {i,j} is a generator iff its support is strictly below that of
            # both singletons, i.e. below the smaller of the two.
            strictly_below = self.pair_c[pf] < self._pair_min_sup[pf]
            n_gen2 = int(strictly_below.sum())
            n_gen2_frac = n_gen2 / n_freq2
            collapse_frac = 1.0 - n_gen2_frac
        else:
            n_gen2_frac = 0.0
            collapse_frac = 0.0

        return {
            "thr_pctile": float((self.sup < minsup).mean()) if self.sup.size else 0.0,
            "log_thr_rel": math.log10(max(minsup, 1.0) / max(self.max_sup, 1)),
            "log_thr_abs": math.log10(max(minsup, 1.0)),
            "log_n_freq1": math.log10(1.0 + n_freq1),
            "frac_freq1": frac_freq1,
            "freq_sup_mass": freq_mass,
            "boundary_frac": boundary / max(self.n_items, 1),
            "avg_len_freq": avg_len_freq,
            "density_freq": avg_len_freq / n_freq1 if n_freq1 else 0.0,
            "log_n_freq2": math.log10(1.0 + n_freq2),
            "pair_density": pair_density,
            "n_gen2_frac": n_gen2_frac,
            "collapse_frac": collapse_frac,
            "log_lattice_ratio": math.log10((1.0 + n_freq2) / (1.0 + n_freq1)),
        }


def vector(feats):
    """Ordered numeric vector in LANDMARK_NAMES order."""
    return [float(feats[k]) for k in LANDMARK_NAMES]


# ----------------------------------------------------------------------
# Cache, keyed "dataset@sigma", so a machine without datasets/ still works
# ----------------------------------------------------------------------
def _key(dataset, sigma):
    return "%s@%.10g" % (dataset, sigma)


def load_cache():
    if os.path.exists(_CACHE):
        with open(_CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(cache):
    with open(_CACHE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, sort_keys=True)


def for_config(dataset, sigma, cache=None, probe_cache=None):
    """Landmarks of one (dataset, sigma) configuration, cached on first use."""
    cache = load_cache() if cache is None else cache
    k = _key(dataset, sigma)
    if k in cache:
        return cache[k]
    probes = {} if probe_cache is None else probe_cache
    if dataset not in probes:
        probes[dataset] = DatasetProbe.build(
            mf.dataset_path(dataset), mf.data_type(dataset))
    feats = probes[dataset].at(sigma)
    cache[k] = feats
    if probe_cache is None:
        save_cache(cache)
    return feats


def build_cache(grid, verbose=True):
    """Compute landmarks for ``{dataset: [sigma, ...]}``, one probe per dataset."""
    import time
    cache = load_cache()
    for dataset, sigmas in sorted(grid.items()):
        path = mf.dataset_path(dataset)
        if not os.path.exists(path):
            if verbose:
                print("  skip %-14s (no data on disk)" % dataset)
            continue
        todo = [s for s in sigmas if _key(dataset, s) not in cache]
        if not todo:
            continue
        t0 = time.time()
        probe = DatasetProbe.build(
            path, mf.data_type(dataset))
        t_probe = time.time() - t0
        for s in sigmas:
            cache[_key(dataset, s)] = probe.at(s)
        if verbose:
            print("  %-14s %6d tx x %6d items | probe %6.2fs | %d thresholds"
                  % (dataset, probe.n_tx, probe.n_items, t_probe, len(sigmas)))
        save_cache(cache)
    return cache


def grid_from_summary(path=None, categories=(1,)):
    """The (dataset, threshold) grid actually present in the benchmark."""
    import pandas as pd
    path = path or os.path.join(os.path.dirname(_HERE), "results", "summary.csv")
    df = pd.read_csv(path)
    df = df[df.category.isin(categories)]
    return {d: sorted(g.param_value.unique())
            for d, g in df.groupby("dataset")}


if __name__ == "__main__":
    grid = grid_from_summary()
    print("Building landmark cache for %d datasets" % len(grid))
    c = build_cache(grid)
    print("\ncached configurations: %d" % len(c))
    hdr = ["configuration"] + list(LANDMARK_NAMES)
    print("  ".join("%-16s" % h for h in hdr))
    for k in sorted(c):
        print("  ".join(["%-16s" % k] + ["%-16.4f" % c[k][f] for f in LANDMARK_NAMES]))
