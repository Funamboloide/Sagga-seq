#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# 0.31: a 0.30 firmware opens a project saved by 0.31 (an LFO on a GROUP of tracks: on T1 and off, the rest as it was),
# and 0.31 one saved by 0.30 - and a project without a group's LFO is saved by both byte for byte (tests/sagga_compat30.c).
# 0.30's core is taken from git as it was released (commit 8b717ff); without that history here (a shallow clone, GitHub's
# build): skipped.
set -e
cd "$(dirname "$0")/.."
REF=8b717ff
if ! git cat-file -e "$REF^{commit}" 2>/dev/null; then echo "compat 0.30: skipped (0.30 is not in the git history here)"; exit 0; fi
D=build/compat30
rm -rf "$D"; mkdir -p "$D/src30" "$D/img"
for f in sagga_seq_core.c sagga_seq_core.h sagga_img27.h sagga_beats.c sagga_beats.h sagga_beats_data.h sagga_setgenre_data.h sagga_devices.h; do
    git show "$REF:firmware/src/$f" > "$D/src30/$f"
done
cc -std=c11 -O1 -w -Ifirmware/src tests/sagga_compat30.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o "$D/now"
cc -std=c11 -O1 -w -I"$D/src30" -DOLD30 tests/sagga_compat30.c "$D/src30/sagga_seq_core.c" "$D/src30/sagga_beats.c" -o "$D/old"
"$D/now" write "$D/img"
"$D/old" relay "$D/img"
"$D/now" check "$D/img"
