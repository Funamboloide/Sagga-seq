#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# 0.32: a 0.31 firmware opens a project saved by 0.32 (the MASTER knob on the ENERGY: on the TEMPO, the rest as it was),
# and 0.32 one saved by 0.31 - and a project without the ENERGY is saved by both byte for byte (tests/sagga_compat31.c).
# 0.31's core is taken from git as it was released (commit 7d7583a); without that history here (a shallow clone, GitHub's
# build): skipped.
set -e
cd "$(dirname "$0")/.."
REF=7d7583a
if ! git cat-file -e "$REF^{commit}" 2>/dev/null; then echo "compat 0.31: skipped (0.31 is not in the git history here)"; exit 0; fi
D=build/compat31
rm -rf "$D"; mkdir -p "$D/src31" "$D/img"
for f in sagga_seq_core.c sagga_seq_core.h sagga_img27.h sagga_beats.c sagga_beats.h sagga_beats_data.h sagga_setgenre_data.h sagga_devices.h; do
    git show "$REF:firmware/src/$f" > "$D/src31/$f"
done
cc -std=c11 -O1 -w -Ifirmware/src tests/sagga_compat31.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o "$D/now"
cc -std=c11 -O1 -w -I"$D/src31" -DOLD31 tests/sagga_compat31.c "$D/src31/sagga_seq_core.c" "$D/src31/sagga_beats.c" -o "$D/old"
"$D/now" write "$D/img"
"$D/old" relay "$D/img"
"$D/now" check "$D/img"
