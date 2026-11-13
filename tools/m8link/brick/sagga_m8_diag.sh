#!/bin/sh
# SAGGA M8 LINK: what this Brick's kernel offers. Run as root on the Brick (with sagga_m8 stopped), send the output.
G=/sys/kernel/config/usb_gadget/g1
echo "== link"; grep -hE "^(NAME|MODE)=" /userdata/system/sagga_m8.conf 2>/dev/null; head -2 /userdata/system/services/sagga_m8 2>/dev/null | tail -1
echo "== kernel"; uname -r; cat /proc/version
echo "== config"; zcat /proc/config.gz 2>/dev/null | grep -E "^CONFIG_MODULES=|MODVERSIONS|MODULE_FORCE_LOAD|USB_F_MIDI|USB_CONFIGFS_F_MIDI|USB_MIDI_GADGET|USB_F_FS|SND_USB_AUDIO|SND_SEQUENCER=|SND_RAWMIDI="
echo "== modules dir"; ls /lib/modules/"$(uname -r)" 2>&1 | head
echo "== M8"; cat /proc/asound/cards; aconnect -l 2>/dev/null | head -20
echo "== gadget"; ls /sys/class/udc; echo "g1 UDC: [$(cat $G/UDC 2>/dev/null)]"; ls $G/functions $G/configs/b.1 2>&1
echo "== f_midi test"
if mkdir $G/functions/midi.test 2>/dev/null; then
    echo "MIDI-OK: native USB-MIDI possible"; ls $G/functions/midi.test; rmdir $G/functions/midi.test
else
    echo "NO-F_MIDI: the vendor link (ffs) is the way"
fi
