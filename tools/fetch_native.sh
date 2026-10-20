#!/usr/bin/env bash
# Fetch and build the native programs that this repository does not carry:
# Christian Borgelt's Apriori, Eclat and FP-growth, FGC-Stream, and the NUS
# programs GC-growth and DPMiner.
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
#
# GC-growth 2.0 and DPMiner (DPM-delta) 1.0 from the authors' project page
# (https://www.comp.nus.edu.sg/~wongls/projects/pattern-spaces/), SHA-256
# checked. GC-growth 2.1 only adds Windows DLLs to 2.0. Both are 32-bit
# Windows sources; three edits make them correct on 64-bit Linux without
# changing what they compute: pointers are compared as uintptr_t instead of
# unsigned int (the change the authors made themselves in Gr-growth), file
# names may exceed 100 characters, and the MSVC-only <crtdbg.h> is replaced
# by an empty header.
set -euo pipefail

ROOT=$(pwd)
[ -f "$ROOT/src/config.py" ] || { echo "run from the repository root" >&2; exit 1; }

declare -A SHA=(
  [GcGrowth-v2.zip]=3f92d88ac9c8d92196f56f71030d1ee6ecaa7ca4c6f6bd0e4d83d2fd1e9c98c6
  [dpm-v1.zip]=f232395119a3ebdaafbd1658998ca11612c8a0419fce94a8991aa0de9bcdd588
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

# --- GC-growth and DPMiner (NUS) -----------------------------------------
NUS=https://www.comp.nus.edu.sg/~wongls/projects/pattern-spaces
mkdir -p "$work/shim"
printf '#pragma once\n#define _CrtDumpMemoryLeaks() 0\n' > "$work/shim/crtdbg.h"
nus_build() {   # zip url, source dir in the zip, program name, target dir
  local zip=$1 url=$2 src=$3 prog=$4 dest=$5
  curl -fsSL -A Mozilla/5.0 -o "$work/$zip" "$url"
  echo "${SHA[$zip]}  $work/$zip" | sha256sum -c --quiet - \
    || { echo "$zip differs from the audited release" >&2; exit 1; }
  rm -rf "$work/nus" && mkdir "$work/nus" && unzip -q "$work/$zip" -d "$work/nus"
  local d="$work/nus/$src"
  sed -i 's/(unsigned int)\(p[a-z_]*\|gp[a-z_]*\)/(uintptr_t)\1/g' "$d/inline_routine.h"
  sed -i '1i #include <cstdint>' "$d/inline_routine.h"
  sed -i 's/#define MAX_FILENAME_LEN\t100/#define MAX_FILENAME_LEN\t4096/' "$d/Global.h"
  (cd "$d" && g++ -O2 -std=c++17 -w -I"$work/shim" -include cstring -o "$prog" *.cpp)
  mkdir -p "$ROOT/$dest" && cp "$d/$prog" "$ROOT/$dest/$prog"
  echo "$prog built from $zip"
}
nus_build GcGrowth-v2.zip "$NUS/gcgrowth-v2/GcGrowth-v2.zip" source GcGrowth external_algos/GC_growth
nus_build dpm-v1.zip "$NUS/dpm-v1/dpm-v1.zip" dpm-v1/DPM-delta DPM-delta external_algos/DPMiner
