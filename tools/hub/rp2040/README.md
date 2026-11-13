# SAGGA HUB PC port (RP2040-Zero)

The firmware of the small board on the hub's "PC" USB-C socket: a two-port USB-MIDI interface for the computer,
a UART to the Pi (see `sagga_pc.c`). Flashing: hold BOOT on the RP2040-Zero, plug it into the computer, copy
`sagga_pc.uf2` onto the `RPI-RP2` drive that appears.

## Build (Linux, WSL)

```sh
sudo apt install cmake gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib build-essential git
git clone --depth 1 --branch 2.1.1 https://github.com/raspberrypi/pico-sdk.git ~/pico-sdk
(cd ~/pico-sdk && git submodule update --init lib/tinyusb)
export PICO_SDK_PATH=~/pico-sdk
cp ~/pico-sdk/external/pico_sdk_import.cmake .
mkdir -p build && cd build && cmake .. && make -j4
# -> build/sagga_pc.uf2
```

`slip_midi.h` is shared with the host test: `cc -std=c11 -Wall -Wextra -Werror test_slip_midi.c -o t && ./t`.

## Wiring to the Pi (three jumper wires on the Pi's header)

| RP2040-Zero | Pi Zero 2 W header |
| --- | --- |
| GP0 (TX) | pin 10, GPIO15 (RXD) |
| GP1 (RX) | pin 8, GPIO14 (TXD) |
| GND | pin 6 |

The RP2040-Zero is powered by the computer (or the charger) on its own USB-C; it must share ground with the Pi
(the GND wire). Both run at 3.3 V on the UART: no level shifting.
