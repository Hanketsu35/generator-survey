#!/usr/bin/env bash
# Fetch and build the native programs that this repository does not carry:
# Christian Borgelt's Apriori, Eclat and FP-growth, and FGC-Stream.
# They are third-party code; the versions below are the ones the paper
# measured. Run from the repository root:  bash tools/fetch_native.sh
#
# Borgelt (https://borgelt.net): apriori 6.31, eclat 5.24, fpgrowth 6.21, all
# dated 2022.11.22. The tarballs are checked against the SHA-256 sums of the
# files that were built for the paper; a mismatch means the upstream release
# changed, and the script stops rather than build another version.
#
# FGC-Stream (https://github.com/Louis-Romain-Roux/FGC-Stream), commit
# 2ebf751 (2020-11-15). GCC needs one line the MSVC-only source lacks
# (tools/patches/fgc_stream_gcc.patch adds `template<>` to an explicit
# specialisation) and <cstdint>, which is injected rather than edited in.
set -euo pipefail

ROOT=$(pwd)
[ -f "$ROOT/src/config.py" ] || { echo "run from the repository root" >&2; exit 1; }

declare -A SHA=(
  [apriori]=711fd38fd9b3df58198040a9530c34f3661bbb179c044d401a2a23928136fa33
  [eclat]=8a4f61d6ad237bbe668aac0f62c95394bfe7e026eca961ce86a3f41b5b38ed78
  [fpgrowth]=2eeb0ef26d53872e40f8f4d7699e742534b11e68cbf779d496c1d2693e0898f0
)
FGC_URL=https://github.com/Louis-Romain-Roux/FGC-Stream
FGC_COMMIT=2ebf751dffeffe96aa339ce33c77d0338cad9269

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# --- Borgelt -------------------------------------------------------------
mkdir -p "$ROOT/external_algos/borgelt"
for p in apriori eclat fpgrowth; do
  curl -fsSL -o "$work/$p.tar.gz" "https://borgelt.net/src/$p.tar.gz"
  echo "${SHA[$p]}  $work/$p.tar.gz" | sha256sum -c --quiet - \
    || { echo "$p.tar.gz differs from the measured release" >&2; exit 1; }
  tar xzf "$work/$p.tar.gz" -C "$work"
  make -s -C "$work/$p/src" "$p" >/dev/null 2>&1
  cp "$work/$p/src/$p" "$ROOT/external_algos/borgelt/$p"
  "$ROOT/external_algos/borgelt/$p" 2>&1 | grep -m1 version || true
done

# --- FGC-Stream ----------------------------------------------------------
fgc="$ROOT/external_algos/FGC_Stream"
[ -d "$fgc/.git" ] || git clone -q "$FGC_URL" "$fgc"
git -C "$fgc" checkout -q "$FGC_COMMIT"
if git -C "$fgc" apply --check "$ROOT/tools/patches/fgc_stream_gcc.patch" 2>/dev/null; then
  git -C "$fgc" apply "$ROOT/tools/patches/fgc_stream_gcc.patch"
fi
(cd "$fgc/FGC-Stream" && g++ -O2 -std=c++17 -include cstdint -o FGC_Stream_release *.cpp)
echo "FGC-Stream built at commit ${FGC_COMMIT:0:7}"
