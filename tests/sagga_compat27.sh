#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# 0.28: a 0.27 firmware opens a project saved by 0.28, and 0.28 one saved again by 0.27 (tests/sagga_compat27.c).
# 0.27's core is taken from git as it was released (commit 732ee36); without that history here (a shallow clone,
# GitHub's build): skipped.
set -e
cd "$(dirname "$0")/.."
REF=732ee36
if ! git cat-file -e "$REF^{commit}" 2>/dev/null; then echo "compat 0.27: skipped (0.27 is not in the git history here)"; exit 0; fi
D=build/compat27
rm -rf "$D"; mkdir -p "$D/src27" "$D/img"
for f in sagga_seq_core.c sagga_seq_core.h sagga_beats.c sagga_beats.h sagga_beats_data.h sagga_setgenre_data.h sagga_devices.h; do
    git show "$REF:firmware/src/$f" > "$D/src27/$f"
done
cc -std=c11 -O1 -w -Ifirmware/src tests/sagga_compat27.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o "$D/now"
cc -std=c11 -O1 -w -I"$D/src27" -DOLD27 tests/sagga_compat27.c "$D/src27/sagga_seq_core.c" "$D/src27/sagga_beats.c" -o "$D/old"
"$D/now" write "$D/img"
"$D/old" relay "$D/img"
"$D/now" check "$D/img"
