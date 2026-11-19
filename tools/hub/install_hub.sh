#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# SAGGA HUB on a RaspiMIDIHub (any Pi): the grid bridge, the M8 link, the firmware library and, if a RP2040-Zero is
# wired to the UART, the PC port. Run from the folder of the unpacked zip, on the Pi:
#     sudo sh install_hub.sh            # the expander: everything, and the UART for the RP2040 (Bluetooth off)
#     sudo sh install_hub.sh --no-pc    # a home Pi without the RP2040: no UART changes, no PC port service
# Idempotent: run it again after an update. The root file system is made writable while it runs (rw / ro).
# 0.20.1: from then on the hub page (port 8090, AGGIORNA IL PI) runs it by itself on an uploaded sagga-hub-X.zip.
# 0.20.2: it runs in a systemd unit of its own and this terminal only follows its log: when RaspiMIDIHub restarts
# (at the very end now) its WiFi can drop for a moment, and with it the SSH session; the install goes on.
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PC=1; [ "$1" = "--no-pc" ] && PC=0
HERE=$(cd "$(dirname "$0")" && pwd)
if [ -z "$SAGGA_DETACHED" ] && [ -d /run/systemd/system ] && command -v systemd-run >/dev/null 2>&1; then
    LOG=/run/sagga-install.log
    UNIT=sagga-install-$(date +%s)
    : > "$LOG"
    if systemd-run --unit="$UNIT" --collect --quiet --setenv=SAGGA_DETACHED=1 /bin/sh -c \
        'sh "$0" "$@" >>/run/sagga-install.log 2>&1; echo "SAGGA_INSTALL_EXIT=$?" >>/run/sagga-install.log' \
        "$HERE/install_hub.sh" "$@"; then
        echo "installing in the background ($UNIT): if the WiFi drops, reconnect and read $LOG"
        tail -n +1 -f "$LOG" &
        TP=$!
        while ! grep -q '^SAGGA_INSTALL_EXIT=' "$LOG"; do sleep 1; done
        sleep 1
        kill "$TP" 2>/dev/null || true
        RC=$(sed -n 's/^SAGGA_INSTALL_EXIT=//p' "$LOG" | tail -n 1)
        exit "${RC:-1}"
    fi
    echo "systemd-run failed: installing here (keep the WiFi up)"
fi
RW=0; ROOT_RO=0
# RaspiMIDIHub's rw / ro are often shell aliases of the user, not commands sudo can see: then the root is remounted here
if command -v rw >/dev/null 2>&1; then rw; RW=1
elif grep -q " / [^ ]* ro[ ,]" /proc/mounts; then ROOT_RO=1; mount -o remount,rw /; fi
# 0.20.2: and again before every write to it: something else (RaspiMIDIHub) may have put it back read-only
# 0.23.2: really before every block of writes - apt and the two compilers take a minute on a small Pi, and what
# followed them wrote to the root unchecked: a root gone read-only meanwhile ended the install half way
rwroot() { if grep -q " / [^ ]* ro[ ,]" /proc/mounts; then mount -o remount,rw / && ROOT_RO=1; fi; }
apt-get install -y --no-install-recommends python3-mido python3-rtmidi python3-serial python3-usb gcc libc6-dev >/dev/null || \
    echo "apt failed: is the Pi on the internet? (USB tethering from the phone does it)"
rwroot
install -d /opt/sagga/hub
# 0.20.1: the hub's version (the zip's folder, sagga-hub-X): the page shows it at the top
case "$(basename "$HERE")" in sagga-hub-*) basename "$HERE" | sed 's/^sagga-hub-//' > /opt/sagga/hub/VERSION ;; esac
install -m 755 "$HERE/sagga_grid_bridge.py" "$HERE/fm1_install.py" /opt/sagga/
[ -f "$HERE/patches.json" ] && install -m 644 "$HERE/patches.json" /opt/sagga/ || true
install -m 755 "$HERE/sagga_m8_host.py" /opt/sagga/
install -m 755 "$HERE/hub/sagga_pc_host.py" "$HERE/hub/sagga_fw.py" "$HERE/hub/usbmidi_pkt.py" /opt/sagga/hub/
install -m 644 "$HERE/hub/sagga_patterns.py" "$HERE/hub/sagga_progs.py" "$HERE/hub/sagga_slicer.py" "$HERE/hub/sagga_editor.py" "$HERE/hub/editor.html" "$HERE/hub/sagga_celle.py" /opt/sagga/hub/
rm -f /opt/sagga/hub/roll.html                                 # 0.23.2: the piano roll of 0.11 is gone (the editor's Tape tab)
for f in sagga_banco.py sagga_testport.py sagga_hw_test.py sagga_hw_explore.py banco_piano.json fm1_piano.json; do   # 0.20.3: the banco's explorer
    [ -f "$HERE/hub/$f" ] && install -m 644 "$HERE/hub/$f" /opt/sagga/hub/ || true
done
mkdir -p /opt/sagga/hub/patterns && install -m 644 "$HERE/hub/patterns/"*.txt /opt/sagga/hub/patterns/   # 0.11: the stock patterns (a genre's file is copied to the projects folder when it changes)
mkdir -p /opt/sagga/hub/progressions && install -m 644 "$HERE/hub/progressions/"*.txt /opt/sagga/hub/progressions/   # 0.11: the stock progressions (the same way)
# 0.29: the four genres that left, as 0.28 gave them (the hub moves the patterns you kept in them to where they went)
for d in patterns progressions; do
    if [ -d "$HERE/hub/$d/retired" ]; then mkdir -p "/opt/sagga/hub/$d/retired" && install -m 644 "$HERE/hub/$d/retired/"*.txt "/opt/sagga/hub/$d/retired/"; fi
    for g in AMAPIANO BASSLINE GRIME AFROHOUSE; do rm -f "/opt/sagga/hub/$d/$g.txt"; done   # (0.28's stock of them: no genre now)
done
# 0.11: the .sgq <-> .mid converter, built here from the firmware's own core
if [ -d "$HERE/sgqmid" ] && command -v cc >/dev/null 2>&1; then
    rwroot
    cc -std=c11 -O2 -I"$HERE/sgqmid" "$HERE/sgqmid/sagga_sgqmid.c" "$HERE/sgqmid/sagga_seq_core.c" "$HERE/sgqmid/sagga_beats.c" -o /opt/sagga/hub/sagga_sgqmid \
        && echo "sagga_sgqmid built" || echo "sagga_sgqmid did not build: the page works without .mid"
    # 0.14: the web editor's converter (.sgq <-> what the page edits), from the same core
    rwroot
    cc -std=c11 -O2 -I"$HERE/sgqmid" "$HERE/sgqmid/sagga_sgqjson.c" "$HERE/sgqmid/sagga_seq_core.c" "$HERE/sgqmid/sagga_beats.c" -o /opt/sagga/hub/sagga_sgqjson \
        && echo "sagga_sgqjson built" || echo "sagga_sgqjson did not build: the page's editor will say so"
fi
# 0.12: the SAGGA pages of RaspiMIDIHub's web interface (Remote, Mutes, Motori, Break, Mod), when the hub is on this Pi
PLUG=$(python3 -c "import raspimidihub, os; print(os.path.join(os.path.dirname(raspimidihub.__file__), 'plugins'))" 2>/dev/null || true)
if [ -n "$PLUG" ] && [ -d "$PLUG" ] && [ -d "$HERE/raspimidihub" ]; then
    rwroot
    for d in "$HERE"/raspimidihub/sagga_*/; do rm -rf "$PLUG/$(basename "$d")"; cp -r "$d" "$PLUG/"; done
    RMH_RESTART=1                                   # 0.20.2: at the very end (it puts the root back read-only)
    echo "the SAGGA pages installed in $PLUG (add them in the hub's interface, OUT to the FM-1)"
else
    echo "RaspiMIDIHub's plugins folder not found: copy the raspimidihub/sagga_* folders by hand (raspimidihub/README.md)"
fi
rwroot
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
rwroot
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
if [ "$RMH_RESTART" = 1 ]; then
    echo "RaspiMIDIHub restarts for the new SAGGA pages (its WiFi may drop for a few seconds)"
    sleep 1
    systemctl restart raspimidihub 2>/dev/null || true
fi
