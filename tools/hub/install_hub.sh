#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# SAGGA HUB on a RaspiMIDIHub (any Pi): the grid bridge, the M8 link, the firmware library and, if a RP2040-Zero is
# wired to the UART, the PC port. Run from the folder of the unpacked zip, on the Pi:
#     sudo sh install_hub.sh            # the expander: everything, and the UART for the RP2040 (Bluetooth off)
#     sudo sh install_hub.sh --no-pc    # a home Pi without the RP2040: no UART changes, no PC port service
# Idempotent: run it again after an update. The root file system is made writable while it runs (rw / ro).
# 0.20.1: from then on the hub page (port 8090, AGGIORNA IL PI) runs it by itself on an uploaded sagga-hub-X.zip.
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PC=1; [ "$1" = "--no-pc" ] && PC=0
HERE=$(cd "$(dirname "$0")" && pwd)
RW=0; ROOT_RO=0
# RaspiMIDIHub's rw / ro are often shell aliases of the user, not commands sudo can see: then the root is remounted here
if command -v rw >/dev/null 2>&1; then rw; RW=1
elif grep -q " / [^ ]* ro[ ,]" /proc/mounts; then ROOT_RO=1; mount -o remount,rw /; fi
apt-get install -y --no-install-recommends python3-mido python3-rtmidi python3-serial python3-usb gcc libc6-dev >/dev/null || \
    echo "apt failed: is the Pi on the internet? (USB tethering from the phone does it)"
install -d /opt/sagga/hub
# 0.20.1: the hub's version (the zip's folder, sagga-hub-X): the page shows it at the top
case "$(basename "$HERE")" in sagga-hub-*) basename "$HERE" | sed 's/^sagga-hub-//' > /opt/sagga/hub/VERSION ;; esac
install -m 755 "$HERE/sagga_grid_bridge.py" "$HERE/fm1_install.py" /opt/sagga/
[ -f "$HERE/patches.json" ] && install -m 644 "$HERE/patches.json" /opt/sagga/ || true
install -m 755 "$HERE/sagga_m8_host.py" /opt/sagga/
install -m 755 "$HERE/hub/sagga_pc_host.py" "$HERE/hub/sagga_fw.py" "$HERE/hub/usbmidi_pkt.py" /opt/sagga/hub/
install -m 644 "$HERE/hub/roll.html" "$HERE/hub/sagga_patterns.py" "$HERE/hub/sagga_progs.py" "$HERE/hub/sagga_slicer.py" "$HERE/hub/sagga_editor.py" "$HERE/hub/editor.html" /opt/sagga/hub/
mkdir -p /opt/sagga/hub/patterns && install -m 644 "$HERE/hub/patterns/"*.txt /opt/sagga/hub/patterns/   # 0.11: the stock patterns (a genre's file is copied to the projects folder when it changes)
mkdir -p /opt/sagga/hub/progressions && install -m 644 "$HERE/hub/progressions/"*.txt /opt/sagga/hub/progressions/   # 0.11: the stock progressions (the same way)
# 0.11: the .sgq <-> .mid converter, built here from the firmware's own core
if [ -d "$HERE/sgqmid" ] && command -v cc >/dev/null 2>&1; then
    cc -std=c11 -O2 -I"$HERE/sgqmid" "$HERE/sgqmid/sagga_sgqmid.c" "$HERE/sgqmid/sagga_seq_core.c" "$HERE/sgqmid/sagga_beats.c" -o /opt/sagga/hub/sagga_sgqmid \
        && echo "sagga_sgqmid built" || echo "sagga_sgqmid did not build: the page works without .mid"
    # 0.14: the web editor's converter (.sgq <-> what the page edits), from the same core
    cc -std=c11 -O2 -I"$HERE/sgqmid" "$HERE/sgqmid/sagga_sgqjson.c" "$HERE/sgqmid/sagga_seq_core.c" "$HERE/sgqmid/sagga_beats.c" -o /opt/sagga/hub/sagga_sgqjson \
        && echo "sagga_sgqjson built" || echo "sagga_sgqjson did not build: the page's editor will say so"
fi
# 0.12: the SAGGA pages of RaspiMIDIHub's web interface (Remote, Mutes, Motori, Break, Mod), when the hub is on this Pi
PLUG=$(python3 -c "import raspimidihub, os; print(os.path.join(os.path.dirname(raspimidihub.__file__), 'plugins'))" 2>/dev/null || true)
if [ -n "$PLUG" ] && [ -d "$PLUG" ] && [ -d "$HERE/raspimidihub" ]; then
    for d in "$HERE"/raspimidihub/sagga_*/; do rm -rf "$PLUG/$(basename "$d")"; cp -r "$d" "$PLUG/"; done
    systemctl restart raspimidihub 2>/dev/null || true
    echo "the SAGGA pages installed in $PLUG (add them in the hub's interface, OUT to the FM-1)"
else
    echo "RaspiMIDIHub's plugins folder not found: copy the raspimidihub/sagga_* folders by hand (raspimidihub/README.md)"
fi
install -m 644 "$HERE/hub/sagga-virmidi.service" "$HERE/hub/sagga-pc-link.service" "$HERE/hub/sagga-fw.service" /etc/systemd/system/
install -m 644 "$HERE/sagga-grid-bridge.service" "$HERE/sagga-m8-link.service" /etc/systemd/system/
# the M8 link loads the cards through sagga-virmidi now (one modprobe with all four cards)
M8=/etc/systemd/system/sagga-m8-link.service
sed -i '/^ExecStartPre=.*modprobe snd-virmidi/d' "$M8"
grep -q '^Requires=sagga-virmidi.service' "$M8" || sed -i '/^\[Unit\]/a Requires=sagga-virmidi.service' "$M8"
grep -q '^After=sagga-virmidi.service' "$M8" || sed -i '/^\[Unit\]/a After=sagga-virmidi.service' "$M8"
# the boot partition: the projects and firmware folders live there (read-only on RaspiMIDIHub: remount for a moment)
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
BOOT=$(dirname "$CFG"); BOOT_RO=0
grep -q " $BOOT [^ ]* ro[ ,]" /proc/mounts && { BOOT_RO=1; mount -o remount,rw "$BOOT"; }
install -d "$BOOT/sagga/firmware"
if [ $PC = 1 ]; then
    # the UART for the PC port: the PL011 on GPIO 14/15, no serial console, Bluetooth off
    grep -q '^enable_uart=1' "$CFG" || echo 'enable_uart=1' >> "$CFG"
    grep -q '^dtoverlay=disable-bt' "$CFG" || echo 'dtoverlay=disable-bt' >> "$CFG"
    CMD=/boot/firmware/cmdline.txt; [ -f "$CMD" ] || CMD=/boot/cmdline.txt
    sed -i 's/console=serial0,115200 //; s/console=ttyAMA0,115200 //' "$CMD"
fi
sync; [ $BOOT_RO = 1 ] && mount -o remount,ro "$BOOT" || true
systemctl daemon-reload
if [ $PC = 1 ]; then
    systemctl disable --now hciuart 2>/dev/null || true
    systemctl disable --now serial-getty@ttyAMA0 serial-getty@serial0 2>/dev/null || true
    systemctl enable sagga-virmidi sagga-grid-bridge sagga-m8-link sagga-pc-link sagga-fw
    systemctl restart sagga-virmidi sagga-grid-bridge sagga-m8-link sagga-pc-link sagga-fw
else
    systemctl disable --now sagga-pc-link 2>/dev/null || true
    systemctl enable sagga-virmidi sagga-grid-bridge sagga-m8-link sagga-fw
    systemctl restart sagga-virmidi sagga-grid-bridge sagga-m8-link sagga-fw
fi
[ $RW = 1 ] && ro || true
[ $ROOT_RO = 1 ] && { sync; mount -o remount,ro / || echo "the root stays writable until the next reboot"; } || true
IP=$(hostname -I 2>/dev/null | cut -d' ' -f1); [ -n "$IP" ] || IP=192.168.4.1
echo "SAGGA HUB installed. Firmware library and projects: http://$IP:8090"
if [ $PC = 1 ]; then echo "Reboot once (the UART settings). The matrix shows SAGGAPC1/2 (the computer) and SAGGAM8A/B (the Bricks)."
else echo "No PC port (--no-pc). The matrix shows SAGGAM8A/B (the Bricks); the bridge waits for the Launchpads."; fi
