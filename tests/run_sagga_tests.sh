#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# All SAGGA SEQ tests that run on a computer (no FM-1, no Launchpads, no toolchain needed): C compiler + Python 3.
#   sh tests/run_sagga_tests.sh            add  FUZZ=60  for more random runs, SANITIZE=1 for ASan + UBSan
set -e
cd "$(dirname "$0")/.."
mkdir -p build
cc -std=c11 -Wall -Wextra -Werror -Ifirmware/src tests/sagga_core_tests.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o build/sagga_core_tests
build/sagga_core_tests
# the JieLi library divides 64-bit numbers without a sign only (__udivdi3; no __divdi3 / __moddi3): no int64_t in the firmware
if grep -n '[^u]int64_t' firmware/src/*.c firmware/src/*.h firmware/hal/*.c firmware/hal/*.h 2>/dev/null | grep -v 'sagga_test.c'; then
    echo "firmware 64-bit: FAIL, a signed 64-bit number (the JieLi link has no __divdi3)"; exit 1
else echo "firmware 64-bit: no signed 64-bit numbers"; fi
cc -O2 -w -Ifirmware/src -Ifirmware/hal tests/usb_desc_test.c -o build/usb_desc_test && build/usb_desc_test
python3 tools/gen_progs.py --check && echo "gen_progs: the stock progressions are up to date"
python3 tests/sagga_bridge_tests.py | tail -1
python3 tests/sagga_plugin_tests.py | tail -1
python3 tools/m8link/test_link.py | tail -1
python3 tests/sagga_hub_tests.py | tail -1
python3 tests/sagga_hwtest_tests.py | tail -1
python3 tests/sagga_sgqmid_tests.py | tail -1
python3 tests/sagga_roll_tests.py | tail -1
python3 tests/sagga_slicer_tests.py | tail -1               # 0.13 a break into slices (the hub page)
python3 tests/sagga_editor_tests.py | tail -1               # 0.14 the projects' web editor (converter, hub, bridge, page)
# the live effects of the set: FIGO on norns (a fake norns, softcut modelled), SCENA on the Ksoloti Gills
if command -v texlua >/dev/null 2>&1; then texlua tools/norns/test_figo.lua | tail -1; else echo "figo: skipped (no texlua)"; fi
c++ -std=c++11 -O2 tools/gills/test_scena.cpp -o build/test_scena && build/test_scena | tail -1
python3 tools/gills/make_scena.py build/scena.axp >/dev/null
if cmp -s build/scena.axp tools/gills/scena.axp; then echo "scena.axp: made from the engine, up to date"; else echo "scena.axp: FAIL, run python3 tools/gills/make_scena.py"; exit 1; fi
if [ -n "$KSOLOTI" ]; then sh tools/gills/armcheck/check_arm.sh; else echo "scena arm: skipped (KSOLOTI= a ksoloti checkout)"; fi
if python3 -c "import numpy, scipy" 2>/dev/null && command -v ffmpeg >/dev/null; then python3 tests/strati_tests.py | tail -1; else echo "strati: skipped (needs numpy, scipy, ffmpeg)"; fi
if [ -n "$SANITIZE" ]; then export SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -fno-sanitize-recover=undefined -g"; fi
python3 tests/sagga_sim_tests.py | tail -1
python3 tests/sagga_fuzz.py "${FUZZ:-24}" | tail -3
python3 tests/sagga_explore.py --veloce | head -12          # 0.11 the explorer: every gesture, the rules (tutto: senza --veloce)
python3 tests/sagga_explore.py --hw-prova | head -8         # 0.11 the explorer on the FM-1, with the simulator in its place
python3 tests/sagga_hw_explore_tests.py | tail -1           # 0.11 the Windows runner, against a fake FM-1
python3 tests/sagga_explore.py --banco-prova | head -12     # 0.20.3 the banco (FM-1, Pi, grid), with the simulator as the FM-1
python3 tests/sagga_banco_tests.py | tail -1                # 0.20.3 the banco's runner on the Pi, a fake FM-1 and RaspiMIDIHub
