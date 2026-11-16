#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# All SAGGA SEQ tests that run on a computer (no FM-1, no Launchpads, no toolchain needed): C compiler + Python 3.
#   sh tests/run_sagga_tests.sh            add  FUZZ=60  for more random runs, SANITIZE=1 for ASan + UBSan
set -e
cd "$(dirname "$0")/.."
mkdir -p build
# 0.20.9: step LABEL head|tail N COMMAND...: the command's output through head / tail, and its exit code kept: a test
# that fails, or does not even start, is said and makes the suite fail at the end (the pipes used to hide it: `python3
# x.py | tail -1` is tail's exit code, and the suite ended with 0 whatever had happened)
FAILED=""
step() {
    label=$1; how=$2; n=$3; shift 3
    if "$@" > build/step.out 2>&1; then rc=0; else rc=$?; fi
    if [ "$how" = head ]; then head -n "$n" build/step.out; else tail -n "$n" build/step.out; fi
    if [ "$rc" != 0 ]; then echo "FAIL: $label (exit $rc)"; FAILED="$FAILED [$label]"; fi
}
cc -std=c11 -Wall -Wextra -Werror -Ifirmware/src tests/sagga_core_tests.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o build/sagga_core_tests
step "core" tail 1 build/sagga_core_tests
# the JieLi library divides 64-bit numbers without a sign only (__udivdi3; no __divdi3 / __moddi3): no int64_t in the firmware
if grep -n '[^u]int64_t' firmware/src/*.c firmware/src/*.h firmware/hal/*.c firmware/hal/*.h 2>/dev/null | grep -v 'sagga_test.c'; then
    echo "firmware 64-bit: FAIL, a signed 64-bit number (the JieLi link has no __divdi3)"; exit 1
else echo "firmware 64-bit: no signed 64-bit numbers"; fi
# 0.20.9: the two builds of the FM-1 itself (the app without DINGHY_HOST, the update loader: both include usb.c) are
# compiled by GitHub only; here they must at least parse, with this computer's clang as a 32-bit bare-metal compiler
# (0.20.9's first push did not build: a line of usb.c the loader could not compile)
if command -v clang >/dev/null 2>&1 && echo 'int x;' | clang --target=armv7m-none-eabi -ffreestanding -fsyntax-only -x c - 2>/dev/null; then
    TF="--target=armv7m-none-eabi -ffreestanding -fsyntax-only -Os -fno-builtin -Wall -Wno-unused-function -Werror -Ifirmware/hal -Ifirmware/src"
    # shellcheck disable=SC2086
    if clang $TF firmware/loader/loader.c && clang $TF -Ifirmware/gen '-DFELUCCA_ID="FM-1_950"' '-DAPP_VER="0.0"' firmware/src/dinghy.c; then
        echo "firmware target builds: the app and the update loader parse (clang, no toolchain)"
    else echo "firmware target builds: FAIL"; exit 1; fi
else echo "firmware target builds: skipped (no clang with an ARM target)"; fi
cc -O2 -w -Ifirmware/src -Ifirmware/hal tests/usb_desc_test.c -o build/usb_desc_test
step "usb descriptors" tail 1 build/usb_desc_test
if python3 tools/gen_progs.py --check; then echo "gen_progs: the stock progressions are up to date"; else echo "FAIL: gen_progs"; FAILED="$FAILED [gen_progs]"; fi
step "bridge" tail 1 python3 tests/sagga_bridge_tests.py
step "plugins" tail 1 python3 tests/sagga_plugin_tests.py    # (RMH=<a RaspiMIDIHub checkout>: in the hub's own plugin host too)
step "m8 link" tail 1 python3 tools/m8link/test_link.py
step "hub" tail 1 python3 tests/sagga_hub_tests.py
step "hwtest" tail 1 python3 tests/sagga_hwtest_tests.py
step "sgqmid" tail 1 python3 tests/sagga_sgqmid_tests.py
step "roll" tail 1 python3 tests/sagga_roll_tests.py
step "slicer" tail 1 python3 tests/sagga_slicer_tests.py               # 0.13 a break into slices (the hub page)
step "editor" tail 1 python3 tests/sagga_editor_tests.py               # 0.14 the projects' web editor (converter, hub, bridge, page)
# the live effects of the set: FIGO on norns (a fake norns, softcut modelled), SCENA on the Ksoloti Gills
if command -v texlua >/dev/null 2>&1; then step "figo" tail 1 texlua tools/norns/test_figo.lua; else echo "figo: skipped (no texlua)"; fi
c++ -std=c++11 -O2 tools/gills/test_scena.cpp -o build/test_scena
step "scena" tail 1 build/test_scena
python3 tools/gills/make_scena.py build/scena.axp >/dev/null
if cmp -s build/scena.axp tools/gills/scena.axp; then echo "scena.axp: made from the engine, up to date"; else echo "scena.axp: FAIL, run python3 tools/gills/make_scena.py"; exit 1; fi
if [ -n "$KSOLOTI" ]; then sh tools/gills/armcheck/check_arm.sh; else echo "scena arm: skipped (KSOLOTI= a ksoloti checkout)"; fi
if python3 -c "import numpy, scipy" 2>/dev/null && command -v ffmpeg >/dev/null; then step "strati" tail 1 python3 tests/strati_tests.py; else echo "strati: skipped (needs numpy, scipy, ffmpeg)"; fi
if [ -n "$SANITIZE" ]; then export SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -fno-sanitize-recover=undefined -g"; fi
step "sim" tail 1 python3 tests/sagga_sim_tests.py
# 0.21: the fuzz with ASan + UBSan whenever this compiler has them (200 runs of it found a line of the screen written
# past its buffer: nothing a run without them can see)
if [ -z "$SAGGA_SIM_CFLAGS" ] && echo 'int main(void){return 0;}' | cc -fsanitize=address,undefined -x c - -o build/san_probe 2>/dev/null && build/san_probe; then
    step "fuzz" tail 3 env SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -fno-sanitize-recover=undefined -g" python3 tests/sagga_fuzz.py "${FUZZ:-24}"
else
    step "fuzz" tail 3 python3 tests/sagga_fuzz.py "${FUZZ:-24}"
fi
step "explore" head 12 python3 tests/sagga_explore.py --veloce          # 0.11 the explorer: every gesture, the rules (tutto: senza --veloce)
step "explore hw" head 8 python3 tests/sagga_explore.py --hw-prova      # 0.11 the explorer on the FM-1, with the simulator in its place
step "hw explore" tail 1 python3 tests/sagga_hw_explore_tests.py        # 0.11 the Windows runner, against a fake FM-1
step "banco prova" head 12 python3 tests/sagga_explore.py --banco-prova # 0.20.3 the banco (FM-1, Pi, grid), with the simulator as the FM-1
step "banco" tail 1 python3 tests/sagga_banco_tests.py                  # 0.20.3 the banco's runner on the Pi, a fake FM-1 and RaspiMIDIHub
step "celle" tail 1 python3 tests/sagga_celle_tests.py                  # 0.20.9 the keeper of the FM-1's cells (RaspiMIDIHub loses them)
if [ -n "$FAILED" ]; then echo "SAGGA TESTS: FAILED:$FAILED"; exit 1; fi
echo "SAGGA TESTS: all passed"
