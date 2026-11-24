#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The VARIAZIONI patches (make_bus.py) built for the Cortex-M4 and linked the way the Patcher links a patch: clang
against the Ksoloti firmware's headers (a checkout of github.com/ksoloti/ksoloti), ld.lld with the firmware's own
ramlink_ksoloti.ld, the firmware's functions and data as addresses. It says what each patch takes of the board's
memories (SRAM1 44 kB: the code; SRAM3 64 kB: the code that runs seldom, beside an effect; CCM: the variables;
SDRAM 32 MB: the buffers) and fails if one does not fit. The Patcher compiles with GCC 9: its sizes differ some.

    KSOLOTI=/path/to/ksoloti [KOBJ=/path/to/ksoloti-objects] python3 tools/gills/armcheck/check_bus.py [--fx X.axp ...]

Without --fx: the effect patches in tools/gills/effetti/.

KOBJ: the Gills' objects (knobs, buttons, screen, LEDs) with their own code; without it, small stand-ins.
With --fx it also builds the effect patch as it is: clang makes bigger code than GCC (here the effect patches alone
measure more than 44 kB), so beside an effect the test is that the patch with the variations takes no more of SRAM1
than the effect alone, which runs on the Gills; alone, that it fits.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GILLS = os.path.dirname(HERE)

WRAP = r'''/* what the Patcher puts around a patch's objects (Patch.java GenerateCode3), the part that matters here */
#define MIDICHANNEL 0
#define HT_SDRAM __attribute__ ((section (".sdram")))
int32buffer AudioInputLeft, AudioInputRight, AudioOutputLeft, AudioOutputRight;
#include "%(cpp)s"
static rootc root;
void PatchProcess(int32_t *inbuf, int32_t *outbuf) {
    for (uint32_t i = 0; i < BUFSIZE; i++) {
        AudioInputLeft[i] = inbuf[i << 1] >> 4; AudioInputRight[i] = inbuf[(i << 1) + 1] >> 4;
        AudioOutputLeft[i] = 0; AudioOutputRight[i] = 0;
    }
    root.dsp();
    for (uint32_t i = 0; i < BUFSIZE; i++) {
        outbuf[i << 1] = __SSAT(AudioOutputLeft[i], 28) << 4;
        outbuf[(i << 1) + 1] = __SSAT(AudioOutputRight[i], 28) << 4;
    }
}
void PatchMidiInHandler(midi_device_t dev, uint8_t port, uint8_t status, uint8_t data1, uint8_t data2) {
    root.MidiInHandler(dev, port, status, data1, data2);
}
typedef void (*funcpp_ptr)(void);
extern funcpp_ptr __ctor_array_start, __ctor_array_end;
extern uint32_t _pbss_start, _pbss_end;
extern char _sdram_dyn_start, _sdram_dyn_end;
void xpatch_init2(uint32_t fwid) {
    (void)fwid;
    for (volatile uint32_t *p = &_pbss_start; p < &_pbss_end; p++) *p = 0;
    for (funcpp_ptr *f = &__ctor_array_start; f < &__ctor_array_end; f++) (*f)();
    sdram_init(&_sdram_dyn_start, &_sdram_dyn_end);
    root.Init();
    patchMeta.fptr_MidiInHandler = PatchMidiInHandler;
    patchMeta.fptr_dsp_process = PatchProcess;
}
extern "C" __attribute__((section(".boot"))) void xpatch_init(uint32_t fwid) { xpatch_init2(fwid); }
'''

REGIONS = {'SRAM1': 0xB000, 'SRAM3': 0x10000, 'CCMSRAM': 0xC800, 'SDRAM': 0x2000000}


def includes(K):
    inc = ['-I%s/firmware' % K, '-I%s/firmware/mutable_instruments' % K, '-I%s/chibios' % K,
           '-I%s/CMSIS/Core/Include' % K, '-I%s/CMSIS/DSP/Include' % K]
    for d in ('os/hal/include', 'os/hal/osal/rt', 'os/rt/include', 'os/rt/ports/ARMCMx', 'os/rt/ports/ARMCMx/compilers/GCC',
              'os/common/ports/ARMCMx/compilers/GCC', 'os/common/ports/ARMCMx/devices/STM32F4xx', 'os/ext/CMSIS/include',
              'os/ext/CMSIS/ST/STM32F4xx', 'os/hal/ports/common/ARMCMx', 'os/hal/ports/STM32/STM32F4xx', 'os/various',
              'os/various/fatfs_bindings', 'ext/fatfs/src'):
        inc.append('-I%s/chibios/%s' % (K, d))
    for l in ('ADCv2', 'CANv1', 'DACv1', 'DMAv2', 'EXTIv1', 'GPIOv2', 'I2Cv1', 'MACv1', 'OTGv1', 'RTCv2', 'SDIOv1',
              'SPIv1', 'TIMv1', 'USARTv1', 'xWDGv1'):
        inc.append('-I%s/chibios/os/hal/ports/STM32/LLD/%s' % (K, l))
    inc.append('-I%s/firmware/STM32F4xx_HAL_Driver/Inc' % K)
    return inc


def build(cpp, K, tmp, link=True):
    name = os.path.splitext(os.path.basename(cpp))[0]
    w = os.path.join(tmp, name + '_patch.cpp')
    with open(w, 'w') as f:
        f.write(WRAP % {'cpp': cpp})
    o = os.path.join(tmp, name + '.o')
    cmd = ['clang++', '--target=thumbv7em-none-eabihf', '-mcpu=cortex-m4', '-mfpu=fpv4-sp-d16', '-mfloat-abi=hard',
           '-std=c++11', '-O3', '-ffast-math', '-fno-math-errno', '-fno-rtti', '-fno-exceptions', '-ffunction-sections',
           '-fdata-sections', '-fno-common', '-fno-threadsafe-statics', '-fno-use-cxa-atexit', '-DBOARD_KSOLOTI_CORE',
           '-DARM_MATH_CM4', '-DCORTEX_USE_FPU=TRUE', '-DTHUMB', '-DTHUMB_NO_INTERWORKING', '-DTHUMB_PRESENT',
           '-D__FPU_PRESENT', '-Werror=return-type', '-Wno-everything', '-isystem', os.path.join(HERE, 'libc')] + \
        includes(K) + ['-include', os.path.join(HERE, 'xpatch_lite.h'), '-c', w, '-o', o]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-4000:])
        raise SystemExit('%s: does not compile for the Cortex-M4' % name)
    und = subprocess.run(['llvm-nm', '--undefined-only', o], capture_output=True, text=True).stdout.split()
    und = [u for u in und if u not in ('U',)]
    if not link:
        return sizes_of(o, False), sorted(set(u for u in und if not u.startswith('_')))
    defs = []
    for k, u in enumerate(sorted(set(und))):
        if u in ('_pbss_start', '_pbss_end', '__ctor_array_start', '__ctor_array_end', '_sdram_dyn_start',
                 '_sdram_dyn_end', '_sram3_start', '_sram3_end'):
            continue
        defs.append('--defsym=%s=0x%08x' % (u, 0x08010000 + 16 * k))
    elf = os.path.join(tmp, name + '.elf')
    r = subprocess.run(['ld.lld', '-T', os.path.join(K, 'firmware', 'ramlink_ksoloti.ld'), '--gc-sections', o, '-o', elf]
                       + defs, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-4000:])
        raise SystemExit('%s: does not link (a memory overflows?)' % name)
    return sizes_of(elf, True), sorted(set(u for u in und if not u.startswith('_')))


def sizes_of(f, linked):
    """what the sections of an object (or of the linked patch, by address) take of each memory"""
    out = subprocess.run(['llvm-readelf', '-S', '-W', f], capture_output=True, text=True).stdout
    used = {k: 0 for k in REGIONS}
    for line in out.splitlines():
        m = re.match(r'\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+[0-9a-f]+\s+([0-9a-f]+)\s+\S+\s+(\S*)', line)
        if not m:
            continue
        sec, typ, addr, size, flg = m.group(1), m.group(2), int(m.group(3), 16), int(m.group(4), 16), m.group(5)
        if 'A' not in flg or size == 0 or sec.startswith('.rel'):
            continue
        if not linked:
            k = ('SRAM3' if sec.startswith('.sram3') else 'SDRAM' if sec.startswith('.sdram') else
                 'CCMSRAM' if sec.startswith('.bss') else 'SRAM1')
            used[k] += size
            continue
        if 0x00011000 <= addr < 0x0001C000:
            used['SRAM1'] += size
        elif 0x20020000 <= addr < 0x20030000:
            used['SRAM3'] += size
        elif 0x10000000 <= addr < 0x1000C800:
            used['CCMSRAM'] += size
        elif 0xC0000000 <= addr < 0xC2000000:
            used['SDRAM'] += size
    return used


def main(argv):
    K = os.environ.get('KSOLOTI')
    if not K:
        raise SystemExit(__doc__)
    fxs = []
    rest = list(argv)
    while rest:
        a = rest.pop(0)
        if a == '--fx':
            fxs.append(rest.pop(0))
    if not fxs:
        ed = os.path.join(GILLS, 'effetti')
        fxs = sorted(os.path.join(ed, f) for f in os.listdir(ed) if f.endswith('_gills.axp')) if os.path.isdir(ed) else []
    tmp = tempfile.mkdtemp()
    cmd = [sys.executable, os.path.join(GILLS, 'make_bus.py'), '--out', tmp, '--cpp']
    for fx in fxs:
        cmd += ['--fx', fx]
    subprocess.run(cmd, check=True, capture_output=True)
    fail = False
    orig = {}
    for fx in fxs:                                 # the effect alone (make_bus.py wrote it, with the same routing)
        base = re.sub(r'_gills$', '', os.path.splitext(os.path.basename(fx))[0])
        orig[base + '_figo_scena'] = build(os.path.join(tmp, base + '_effect.cpp'), K, tmp, link=False)[0]
    for fn in sorted(os.listdir(tmp)):
        if not fn.endswith('.cpp') or fn.endswith('_patch.cpp') or fn.endswith('_effect.cpp'):
            continue
        name = os.path.splitext(fn)[0]
        base = orig.get(name)
        if base is None:
            used, und = build(os.path.join(tmp, fn), K, tmp)
        else:
            used, und = build(os.path.join(tmp, fn), K, tmp, link=False)
            try:                                   # and linked, when clang's code fits: the second RAM, the calls
                build(os.path.join(tmp, fn), K, tmp)
                elf = os.path.join(tmp, name + '.elf')
                syms = subprocess.run(['llvm-nm', elf], capture_output=True, text=True).stdout
                thunks = len([l for l in syms.splitlines() if 'Thunk' in l or 'veneer' in l])
                print('   linked with ramlink_ksoloti.ld: the second RAM\'s code at 0x20020000, %d long calls between'
                      ' the two' % thunks)
            except SystemExit:
                print('   (clang\'s code does not fit to link it: the test is the one against the effect alone)')
        line = '%s arm:' % name
        for k in ('SRAM1', 'SRAM3', 'CCMSRAM', 'SDRAM'):
            cap = REGIONS[k]
            line += ' %s %.1f of %.0f kB,' % (k, used[k] / 1024.0, cap / 1024.0) if k != 'SDRAM' else \
                ' SDRAM %.2f of %.0f MB' % (used[k] / 1048576.0, cap / 1048576.0)
            if k == 'SRAM1' and base is not None:
                line += ' (the effect alone %.1f kB)' % (base['SRAM1'] / 1024.0)
                if used[k] > base['SRAM1']:
                    fail = True
                    line += ' (FAIL: more than the effect alone)'
            elif used[k] > cap:
                fail = True
                line += ' (FAIL: too big)'
        print(line)
        print('   needs from the firmware: ' + ' '.join(und))
    if not os.environ.get('KOBJ'):
        print('   (no KOBJ: the Gills objects are stand-ins, the real ones take some kB more)')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
