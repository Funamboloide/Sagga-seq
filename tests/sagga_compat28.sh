#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# 0.29: a 0.28 firmware opens a project saved by 0.29 (BALANI as AFRO HOUSE), and 0.29 one saved by 0.28 - its 25 genres
# each where it went (tests/sagga_compat28.c). 0.28's core is taken from git as it was released (commit 311e494);
# without that history here (a shallow clone, GitHub's build): skipped.
set -e
cd "$(dirname "$0")/.."
REF=311e494
if ! git cat-file -e "$REF^{commit}" 2>/dev/null; then echo "compat 0.28: skipped (0.28 is not in the git history here)"; exit 0; fi
D=build/compat28
rm -rf "$D"; mkdir -p "$D/src28" "$D/img"
for f in sagga_seq_core.c sagga_seq_core.h sagga_img27.h sagga_beats.c sagga_beats.h sagga_beats_data.h sagga_setgenre_data.h sagga_devices.h; do
    git show "$REF:firmware/src/$f" > "$D/src28/$f"
done
cc -std=c11 -O1 -w -Ifirmware/src tests/sagga_compat28.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o "$D/now"
cc -std=c11 -O1 -w -I"$D/src28" -DOLD28 tests/sagga_compat28.c "$D/src28/sagga_seq_core.c" "$D/src28/sagga_beats.c" -o "$D/old"
"$D/now" write "$D/img"
"$D/old" relay "$D/img"
"$D/now" check "$D/img"
