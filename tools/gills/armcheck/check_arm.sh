#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# SCENA compiled the way the Ksoloti Patcher compiles it, but with clang, against the Ksoloti firmware's own headers
# (a checkout of github.com/ksoloti/ksoloti): it catches a name that does not exist on the board, a type that does
# not fit, code that grows too big. libc/ holds the few C headers the firmware's headers include (no newlib here).
#     KSOLOTI=/path/to/ksoloti sh tools/gills/armcheck/check_arm.sh
set -e
K=${KSOLOTI:?KSOLOTI=/path/to/a/ksoloti/checkout}
HERE=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
python3 "$HERE/../make_scena.py" "$T/scena.axp" --cpp "$T/scena.cpp" >/dev/null
INC="-I$K/firmware -I$K/firmware/mutable_instruments -I$K/chibios -I$K/CMSIS/Core/Include -I$K/CMSIS/DSP/Include"
for d in os/hal/include os/hal/osal/rt os/rt/include os/rt/ports/ARMCMx os/rt/ports/ARMCMx/compilers/GCC \
         os/common/ports/ARMCMx/compilers/GCC os/common/ports/ARMCMx/devices/STM32F4xx os/ext/CMSIS/include \
         os/ext/CMSIS/ST/STM32F4xx os/hal/ports/common/ARMCMx os/hal/ports/STM32/STM32F4xx os/various \
         os/various/fatfs_bindings ext/fatfs/src; do INC="$INC -I$K/chibios/$d"; done
for l in ADCv2 CANv1 DACv1 DMAv2 EXTIv1 GPIOv2 I2Cv1 MACv1 OTGv1 RTCv2 SDIOv1 SPIv1 TIMv1 USARTv1 xWDGv1; do
    INC="$INC -I$K/chibios/os/hal/ports/STM32/LLD/$l"; done
INC="$INC -I$K/firmware/STM32F4xx_HAL_Driver/Inc"
clang++ --target=thumbv7em-none-eabihf -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard -std=c++11 -O3 \
    -ffast-math -fno-math-errno -fno-rtti -fno-exceptions -DBOARD_KSOLOTI_CORE -DARM_MATH_CM4 -DCORTEX_USE_FPU=TRUE \
    -DTHUMB -DTHUMB_NO_INTERWORKING -DTHUMB_PRESENT -D__FPU_PRESENT -Werror=return-type -Wno-everything \
    -isystem "$HERE/libc" $INC -include "$HERE/xpatch_lite.h" -c "$T/scena.cpp" -o "$T/scena.o"
TEXT=$(llvm-size "$T/scena.o" | awk 'NR==2{print $1}')
UNDEF=$(llvm-nm --undefined-only "$T/scena.o" | awk '{print $2}' | tr '\n' ' ')
echo "scena arm: compiles for the Cortex-M4 against the firmware headers, code $TEXT bytes, needs: $UNDEF"
[ "$TEXT" -lt 40000 ] || { echo "scena arm: FAIL, the code is too big for the patch's 44 kB"; exit 1; }
for s in $UNDEF; do
    case "$s" in adcvalues|_pal_lld_setgroupmode|memset|memcpy|__aeabi_*) ;; *) echo "scena arm: FAIL, needs $s"; exit 1;; esac
done
