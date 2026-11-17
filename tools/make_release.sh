#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# The release files of SAGGA SEQ, from a clean checkout (no toolchain needed; the firmware itself is built with
# build.sh on a machine that has it):
#     sh tools/make_release.sh 0.10 [OUT_DIR]
# writes OUT_DIR (default build/release):
#     sagga-seq-X.Y-source.zip     the repository (what git tracks), for ./build.sh --release X.Y on WSL
#     sagga-hub-X.Y.zip            the Raspberry Pi side: install_hub.sh and everything it installs (the grid bridge,
#                                  the hub page, the .sgq <-> .mid converter's sources, the M8 link, the plugins)
#     INSTALLA.md                  the installation sheet (Italian: docs/INSTALLA.md, the one of today's set),
#     RELEASE-NOTES-X.Y.md         and the release notes (the root's; a past version's: docs/storia/)
set -e
VER=${1:?version, e.g. 0.10}
cd "$(dirname "$0")/.."
OUT=${2:-build/release}
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# 1. the source: a git archive when this is a checkout, else the tree without build output
SRC="sagga-seq-$VER-source"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git archive --format=tar --prefix="$SRC/" HEAD | (cd "$T" && tar xf -)
    # files added but not yet committed still belong in the source (a release is cut before the commit sometimes)
    git ls-files --others --exclude-standard | grep -v '^\.claude/' | while read -r f; do
        [ -f "$f" ] && mkdir -p "$T/$SRC/$(dirname "$f")" && cp "$f" "$T/$SRC/$f"
    done
else
    mkdir -p "$T/$SRC"
    tar --exclude=./build --exclude=./.git --exclude=./.claude --exclude='__pycache__' -cf - . | (cd "$T/$SRC" && tar xf -)
fi
find "$T/$SRC" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
(cd "$T" && rm -f "$OUT/$SRC.zip" && zip -qr "$OUT/$SRC.zip" "$SRC")

# 2. the Pi: the layout install_hub.sh reads (tools/hub/install_hub.sh: $HERE/...)
HUB="sagga-hub-$VER"
H="$T/$HUB"
mkdir -p "$H/hub" "$H/sgqmid" "$H/raspimidihub" "$H/rp2040"
cp tools/hub/install_hub.sh tools/hub/LEGGIMI.md "$H/"
cp tools/hub/sagga_fw.py tools/hub/sagga_pc_host.py tools/hub/usbmidi_pkt.py tools/hub/sagga_patterns.py tools/hub/sagga_progs.py tools/hub/sagga_slicer.py \
   tools/hub/sagga_editor.py tools/hub/editor.html tools/hub/sagga_celle.py tools/hub/sagga-fw.service tools/hub/sagga-pc-link.service tools/hub/sagga-virmidi.service "$H/hub/"
cp tools/hub/sagga_banco.py tools/hwtest/sagga_testport.py tools/hwtest/sagga_hw_test.py tools/hwtest/sagga_hw_explore.py "$H/hub/"   # 0.20.3: the banco's explorer
python3 tests/sagga_explore.py --banco-piano "$H/hub/banco_piano.json"            # ... and its plan (made now, from the explorer)
python3 tests/sagga_explore.py --hw-piano "$H/hub/fm1_piano.json" --sessioni 24 --hw-tablet 4   # ... and the whole FM-1's (every situation)
mkdir -p "$H/hub/patterns" && cp tools/hub/patterns/*.txt "$H/hub/patterns/"      # 0.11: the stock patterns of the genres
mkdir -p "$H/hub/progressions" && cp tools/hub/progressions/*.txt "$H/hub/progressions/"   # 0.11: the stock progressions of the genres
cp -r tools/hub/rp2040/. "$H/rp2040/"
cp -r tools/hub/case "$H/case"
cp tools/sagga_grid_bridge.py tools/fm1_install.py "$H/"
cp tools/sagga-grid-bridge.service tools/sagga-grid-bridge-zynthian.service tools/patches.example.json "$H/"
cp tools/m8link/pi/sagga_m8_host.py tools/m8link/pi/sagga-m8-link.service "$H/"
cp -r tools/raspimidihub/. "$H/raspimidihub/"
cp tools/sgqmid/sagga_sgqmid.c tools/sgqmid/sagga_sgqjson.c firmware/src/sagga_seq_core.c firmware/src/sagga_seq_core.h firmware/src/sagga_beats.c \
   firmware/src/sagga_beats.h firmware/src/sagga_beats_data.h firmware/src/sagga_setgenre_data.h firmware/src/sagga_devices.h "$H/sgqmid/"
cp docs/SAGGA-GRID.md docs/SAGGA-GRID-ZYNTHIAN.md docs/INSTALLA.md "$H/"
find "$H" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
(cd "$T" && rm -f "$OUT/$HUB.zip" && zip -qr "$OUT/$HUB.zip" "$HUB")

# 3. the sheets
cp docs/INSTALLA.md "$OUT/"
for n in "RELEASE-NOTES-$VER.md" "docs/storia/RELEASE-NOTES-$VER.md"; do [ -f "$n" ] && cp "$n" "$OUT/" && break; done || true

# the converter must build from the zip's own files (the Pi does exactly this)
cc -std=c11 -O2 -I"$H/sgqmid" "$H/sgqmid/sagga_sgqmid.c" "$H/sgqmid/sagga_seq_core.c" "$H/sgqmid/sagga_beats.c" -o "$T/sagga_sgqmid"
cc -std=c11 -O2 -I"$H/sgqmid" "$H/sgqmid/sagga_sgqjson.c" "$H/sgqmid/sagga_seq_core.c" "$H/sgqmid/sagga_beats.c" -o "$T/sagga_sgqjson"   # 0.14
ls -la "$OUT"
