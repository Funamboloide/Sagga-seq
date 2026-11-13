# Licensing

SAGGA SEQ is free software under the GNU General Public License, version 3 only (`GPL-3.0-only`, full text in
`LICENSE`). You may use, study, change and share it. If you give someone a firmware built from it, give them its
complete source under the same licence too.

## Who made what

| | |
| --- | --- |
| The platform: `firmware/hal/`, `firmware/loader/`, `crt0.S`, `app.ld`, `firmware/src/` (`usb.c`, `ota.c`, `recovery.c`, `lcd.c`, `gfx.c`, `libc.c`, `bootguard.h`, `uac_fir.h`), `tools/` (`build.py`, `fm1pkg_make.py`, `fm1_install.py`, `lz4blk.py`, `get_toolchain.sh`) | Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments ([Felucca](https://github.com/hugelton/Felucca)), with the changes of [SLOOP](https://github.com/isod89/sloop-fm1) (isod89) |
| The app template SAGGA SEQ grew from (`firmware/src/dinghy.c`, the wiring `platform.c`, the host mode `tests/host.c`, `docs/RULES.md`, `docs/MAKE-IT-YOURS.md`) | zvenson ([Dinghy](https://thefirmwarehub.com)) |
| SAGGA SEQ: the sequencer (`firmware/src/sagga_*.c`, `dinghy.c` as it is now), the MIDI and USB changes, the pattern library (`tools/gen_beats.py`), the Raspberry Pi bridge and plugins (`tools/sagga_grid_bridge.py`, `tools/raspimidihub/`), the M8 link (`tools/m8link/`), the tests and the SAGGA docs | Copyright (C) 2026 sagghino |

## Third-party material

| What | Licence | Where |
| --- | --- | --- |
| Terminus font 8x16 (ter-u16n), rendered into `firmware/gen/felucca_font.h` | SIL OFL 1.1 | `assets/fonts/Terminus-LICENSE.txt` |
| JieLi AC79 SDK: `uboot.boot`, `cfg_tool.bin`, `eq_cfg_hw.bin` are read from your SDK checkout at build time and placed in the package; no SDK files are in this tree | Apache-2.0 | <https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK> |
| The idea of one grid made of two Launchpads, and what it knows about the Launchpad Mini MK3 (`tools/sagga_grid_bridge.py`) | from [midigrid](https://github.com/jaggednz/midigrid), GPL-3.0 | no code copied |
| The plugins in `tools/raspimidihub/` run inside [RaspiMIDIHub](https://github.com/wamdam/raspimidihub) and use its plugin API | RaspiMIDIHub is GPL | not included here |

## Trademarks

"Felucca" and "Hügelton Instruments" are names of Hügelton Instruments; "M-VAVE" and "FM-1" belong to their owners;
"Launchpad" belongs to Focusrite / Novation; "M8" to Dirtywave. SAGGA SEQ is not made or endorsed by any of them.
