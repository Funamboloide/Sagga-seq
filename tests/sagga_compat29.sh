#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# 0.30: a 0.29 firmware opens a project saved by 0.30 (its first 16 scenes, 8 snapshots, 64 song entries, 1536 tape
# events), and 0.30 one saved by 0.29 - and a project with nothing 0.29 lacks is saved by both byte for byte
# (tests/sagga_compat29.c). 0.29's core is taken from git as it was released (commit f06d097); without that history here
# (a shallow clone, GitHub's build): skipped.
set -e
cd "$(dirname "$0")/.."
REF=f06d097
if ! git cat-file -e "$REF^{commit}" 2>/dev/null; then echo "compat 0.29: skipped (0.29 is not in the git history here)"; exit 0; fi
D=build/compat29
rm -rf "$D"; mkdir -p "$D/src29" "$D/img"
for f in sagga_seq_core.c sagga_seq_core.h sagga_img27.h sagga_beats.c sagga_beats.h sagga_beats_data.h sagga_setgenre_data.h sagga_devices.h; do
    git show "$REF:firmware/src/$f" > "$D/src29/$f"
done
cc -std=c11 -O1 -w -Ifirmware/src -Itests tests/sagga_compat29.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o "$D/now"
cc -std=c11 -O1 -w -I"$D/src29" -DOLD29 tests/sagga_compat29.c "$D/src29/sagga_seq_core.c" "$D/src29/sagga_beats.c" -o "$D/old"
"$D/now" write "$D/img"
"$D/old" relay "$D/img"
"$D/now" check "$D/img"
