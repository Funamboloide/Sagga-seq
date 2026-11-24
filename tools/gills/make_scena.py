#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""SCENA for the Ksoloti Gills: writes the patch (scena.axp) from the engine (scena_engine.h) and the board glue
(scena_platform.h): one embedded object with the whole effect, the stereo audio in and out, the Gills screen.

    python3 tools/gills/make_scena.py [OUT.axp] [--cpp TEST.cpp]

It writes two patches, the same but for the object's attribute `routing`: OUT.axp (insert, the dry passes) and, next
to it, OUT_aux.axp (aux, for a mixer's send and return: no dry out). In the Patcher the attribute can be changed on
either. --cpp also writes the C++ the Ksoloti Patcher generates for the object (a class with Init, dsp,
MidiInHandler), to compile it against the firmware's headers (tests/run_sagga_tests.sh does it with clang when the
headers are there).
"""
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
OBJ_UUID = 'b7a1c0de-5ce9-4a00-8000-000000005ce9'        # fixed: the patch is the same file every time it is made

INLETS = [('frac32buffer', 'inl', 'left in'), ('frac32buffer', 'inr', 'right in')]
OUTLETS = [('frac32buffer', 'outl', 'left out'), ('frac32buffer', 'outr', 'right out'),
           ('charptr32', 'l1', 'screen line 1'), ('charptr32', 'l2', 'screen line 2'),
           ('charptr32', 'l3', 'screen line 3'), ('charptr32', 'l4', 'screen line 4')]

INIT = '''static int16_t sc_el[SC_ECHO_N] __attribute__ ((section (".sdram")));
static int16_t sc_er[SC_ECHO_N] __attribute__ ((section (".sdram")));
static int16_t sc_rl[SC_ROLL_N] __attribute__ ((section (".sdram")));
static int16_t sc_rr[SC_ROLL_N] __attribute__ ((section (".sdram")));
static float sc_rv[SC_RV_TOTAL] __attribute__ ((section (".sdram")));
hw_setup();
sc_init(sc_el, sc_er, sc_rl, sc_rr, sc_rv);
routing = attr_routing;
sc_rt = (uint32_t)(attr_anticipo * 48.f + 0.5f);'''

KRATE = '''sc_block(inlet_inl, inlet_inr, outlet_outl, outlet_outr);
outlet_l1 = line[0];
outlet_l2 = line[1];
outlet_l3 = line[2];
outlet_l4 = line[3];'''

MIDI = 'sc_midi(status, data1, data2);'

NOTES = '''<html><h3>SCENA</h3>
Un effetto in insert sul loop: <b>una manopola</b> (SCENA) dal break-down (a sinistra) al pulito (al centro) al
build-up (a destra), come le Scene FX del Pioneer RMX-1000. Le altre nove dicono fin dove arriva ogni parte, come una
scena dell'Octatrack: le imposti a casa. MOTO lo fa muovere da solo, a tempo.
<br><br><b>Manopole</b>
<br>1 SCENA: sinistra break-down, centro pulito (bit per bit), destra build-up
<br>2 MOTO: quanto si muove da solo (respiro del filtro e dell'eco, fill a fine battuta e a fine frase)
<br>3 ECO: il tempo dell'eco, 1/16 1/8 1/8. 1/4 1/4. 1/2 1 BAR (dal clock MIDI o dal TAP)
<br>4 FEEDBACK: quanto suona l'eco agli estremi
<br>5 FILTRO: fin dove va il filtro (destra: passa-alto fino a 2.5 kHz, sinistra: passa-basso fino a 220 Hz)
<br>6 RISON: la risonanza (cresce con la scena)
<br>7 RUMORE: il fruscio che sale nel build-up
<br>8 CRUSH: bit e campioni in meno nel break-down
<br>9 RIVERB: il riverbero sotto il break-down
<br>10 RITORNI: il volume di eco e riverbero
<br><br><b>Tasti</b>
<br>S1 ROLL (tenuto): dal prossimo sedicesimo ripete 1/8 (MOTO oltre meta': 1/16); nel build-up si accorcia a ogni battito
<br>S2 FREEZE: dal prossimo battito ripete il battito appena passato, finche' non lo premi di nuovo
<br>S3 RELEASE: pulito subito, l'eco si spegne da sola; torna quando SCENA ripassa dal centro
<br>S4 TAP: il tempo, se non arriva il clock MIDI
<br><br><b>MIDI</b> (qualsiasi canale): clock, start, stop; CC 20 SCENA, CC 21 MOTO, CC 22 ROLL, CC 23 FREEZE, CC 24 RELEASE.
La manopola si riprende il controllo appena la muovi.
<br><br>LED 3: blu build-up, rosso break-down. LED 4: blu il battito, rosso ROLL / FREEZE (lampeggia: RELEASE).
<br><br><b>routing</b> (l'attributo dell'oggetto scena, nel Patcher; poi di nuovo Upload):
<br>insert: in serie, il pulito passa (al centro bit per bit). La latenza e' solo quella della scheda, circa 1-2 ms.
<br>aux (scena_aux.axp): per mandata e ritorno del mixer. Il pulito non esce mai (e' gia' sul mixer: una sua copia
in ritardo di 1-2 ms farebbe un effetto phaser). Escono il rumore, l'eco e il riverbero, e i loop di ROLL, FREEZE e
dei fill dalla loro prima ripetizione (il primo passaggio e' il pulito). Filtro e crush agiscono su quello che va
nell'eco e nel riverbero, e sui loop; il pulito sul mixer resta com'e'. Al centro il ritorno e' muto: sul display
MANDATA al posto di PULITO.
<br>anticipo (attributo, solo in aux): i loop ripetono 1.5 ms prima, quanto il suono impiega ad andare dalla Gills al
mixer e a tornare: cosi' cadono sulla griglia del pulito al mixer. Se le ripetizioni di una cassa dritta fanno flam o
effetto phaser, prova un altro valore.'''


def read(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


def declaration():
    return read('scena_platform.h') + '\n' + read('scena_engine.h')


def cdata(s):
    assert ']]>' not in s
    return '<![CDATA[' + s + ']]>'


ROUTINGS = ('insert', 'aux')
# aux: the way to the mixer and back (the Gills' converters and buffers): the loops repeat that early
ANTICIPI = [('1.5 ms', '1.5f'), ('0 ms', '0.0f'), ('0.5 ms', '0.5f'), ('1.0 ms', '1.0f'), ('2.0 ms', '2.0f'),
            ('2.5 ms', '2.5f'), ('3.0 ms', '3.0f')]


def axp(routing='insert'):
    assert routing in ROUTINGS
    decl = declaration()
    io = []
    io.append('      <inlets>')
    for t, n, d in INLETS:
        io.append('         <%s name="%s" description="%s"/>' % (t, n, d))
    io.append('      </inlets>')
    io.append('      <outlets>')
    for t, n, d in OUTLETS:
        io.append('         <%s name="%s" description="%s"/>' % (t, n, d))
    io.append('      </outlets>')
    o = []
    o.append('<patch-1.0 appVersion="1.0.12">')
    o.append('   <comment type="patch/comment" x="14" y="14" text="%s"/>' % escape(
        '<html><b>SCENA</b> - una manopola, dal break-down al build-up. Le istruzioni: Patch &gt; Notes.', {'"': '&quot;'}))
    o.append('   <obj type="audio/in stereo" uuid="99848ad6d90a8e615e83b2e619cfc806f28e7281" name="audio_in" x="14" y="70">')
    o.append('      <params/>\n      <attribs/>\n   </obj>')
    o.append('   <patchobj type="patch/object" uuid="%s" name="scena" x="168" y="70">' % OBJ_UUID)
    o.append('      <params/>')
    o.append('      <attribs>')
    o.append('         <combo attributeName="routing" selection="%s"/>' % routing)
    o.append('         <combo attributeName="anticipo" selection="%s"/>' % ANTICIPI[0][0])
    o.append('      </attribs>')
    o.append('      <object id="patch/object" uuid="%s">' % OBJ_UUID)
    o.append('         <sDescription>SCENA: one knob from break-down to build-up (Pioneer RMX-1000 Scene FX, Octatrack scenes)</sDescription>')
    o.append('         <author>SAGGA</author>')
    o.append('         <license>GPL</license>')
    o.extend('   ' + x for x in io)
    o.append('         <displays/>\n         <params/>')
    o.append('         <attribs>')
    o.append('            <combo name="routing" description="insert: the dry passes; aux: send and return, no dry out">')
    o.append('               <MenuEntries>')
    for r in ROUTINGS:
        o.append('                  <string>%s</string>' % r)
    o.append('               </MenuEntries>')
    o.append('               <CEntries>')
    for i in range(len(ROUTINGS)):
        o.append('                  <string>%d</string>' % i)
    o.append('               </CEntries>')
    o.append('            </combo>')
    o.append('            <combo name="anticipo" description="aux: the way to the mixer and back; the loops repeat that early">')
    o.append('               <MenuEntries>')
    for m, _ in ANTICIPI:
        o.append('                  <string>%s</string>' % m)
    o.append('               </MenuEntries>')
    o.append('               <CEntries>')
    for _, v in ANTICIPI:
        o.append('                  <string>%s</string>' % v)
    o.append('               </CEntries>')
    o.append('            </combo>')
    o.append('         </attribs>')
    o.append('         <includes/>')
    o.append('         <code.declaration>%s</code.declaration>' % cdata(decl))
    o.append('         <code.init>%s</code.init>' % cdata(INIT))
    o.append('         <code.krate>%s</code.krate>' % cdata(KRATE))
    o.append('         <code.midihandler>%s</code.midihandler>' % cdata(MIDI))
    o.append('      </object>')
    o.append('   </patchobj>')
    o.append('   <obj type="audio/out stereo" uuid="a1ca7a567f535acc21055669829101d3ee7f0189" name="audio_out" x="336" y="70">')
    o.append('      <params/>\n      <attribs/>\n   </obj>')
    o.append('   <obj type="ksoloti/gills/display" uuid="0c083e83-0280-4cf2-b747-8a00859bb904" name="display" x="336" y="168">')
    o.append('      <params/>')
    o.append('      <attribs>')
    o.append('         <combo attributeName="useScope" selection="off"/>')
    o.append('         <objref attributeName="scope" obj=""/>')
    o.append('         <combo attributeName="narrowFont" selection="off"/>')
    o.append('      </attribs>')
    o.append('   </obj>')
    nets = [(('audio_in', 'left'), ('scena', 'inl')), (('audio_in', 'right'), ('scena', 'inr')),
            (('scena', 'outl'), ('audio_out', 'left')), (('scena', 'outr'), ('audio_out', 'right')),
            (('scena', 'l1'), ('display', 'line1')), (('scena', 'l2'), ('display', 'line2')),
            (('scena', 'l3'), ('display', 'line3')), (('scena', 'l4'), ('display', 'line4'))]
    o.append('   <nets>')
    for (so, sp), (do, dp) in nets:
        o.append('      <net>\n         <source obj="%s" outlet="%s"/>\n         <dest obj="%s" inlet="%s"/>\n      </net>' % (so, sp, do, dp))
    o.append('   </nets>')
    o.append('   <settings>\n      <subpatchmode>no</subpatchmode>\n      <MidiChannel>1</MidiChannel>\n      <NPresets>8</NPresets>')
    o.append('      <NPresetEntries>32</NPresetEntries>\n      <NModulationSources>8</NModulationSources>')
    o.append('      <NModulationTargetsPerSource>8</NModulationTargetsPerSource>\n   </settings>')
    o.append('   <notes>%s</notes>' % cdata(NOTES))
    o.append('   <windowPos>\n      <x>40</x>\n      <y>40</y>\n      <width>900</width>\n      <height>600</height>\n   </windowPos>')
    o.append('</patch-1.0>')
    return '\n'.join(o) + '\n'


def patcher_cpp(routing='insert'):
    """the class the Ksoloti Patcher writes for the object (AxoObjectInstance.GenerateClass); the Patcher puts each
    attribute's C value in place of attr_<name> everywhere in the code"""
    args = ['const int32buffer inlet_inl', 'const int32buffer inlet_inr', 'int32buffer &outlet_outl',
            'int32buffer &outlet_outr', 'char* &outlet_l1', 'char* &outlet_l2', 'char* &outlet_l3', 'char* &outlet_l4']
    return '''/* the Patcher's shape for the SCENA object (make_scena.py --cpp) */
class rootc;
class instanceSCENA {
    public: // v1
        rootc *parent;
%s
        public: void Init(rootc *_parent) {
            parent = _parent;
%s
        }
        public: void Dispose() {
        }
        public: void dsp(%s) {
%s
        }
        void MidiInHandler(midi_device_t dev, uint8_t port, uint8_t status, uint8_t data1, uint8_t data2) {
%s
        }
};
static instanceSCENA scena_i;
static int32buffer t_in_l, t_in_r, t_out_l, t_out_r;
static char *t_l1, *t_l2, *t_l3, *t_l4;
extern "C" void scena_entry(void) {
    scena_i.Init(0);
    scena_i.dsp(t_in_l, t_in_r, t_out_l, t_out_r, t_l1, t_l2, t_l3, t_l4);
    scena_i.MidiInHandler(MIDI_DEVICE_DIN, 0, 0xF8, 0, 0);
}
''' % (declaration(), INIT.replace('attr_routing', str(ROUTINGS.index(routing))).replace('attr_anticipo', ANTICIPI[0][1]),
       ', '.join(args), KRATE, MIDI)


def main(argv):
    out = os.path.join(HERE, 'scena.axp')
    cpp = None
    rest = list(argv)
    while rest:
        a = rest.pop(0)
        if a == '--cpp':
            cpp = rest.pop(0)
        else:
            out = a
    with open(out, 'w') as f:
        f.write(axp('insert'))
    print('wrote %s' % out)
    root, ext = os.path.splitext(out)
    out_aux = root + '_aux' + (ext or '.axp')
    with open(out_aux, 'w') as f:
        f.write(axp('aux'))
    print('wrote %s' % out_aux)
    if cpp:
        with open(cpp, 'w') as f:
            f.write(patcher_cpp())
        print('wrote %s' % cpp)
        croot, cext = os.path.splitext(cpp)
        with open(croot + '_aux' + (cext or '.cpp'), 'w') as f:
            f.write(patcher_cpp('aux'))
        print('wrote %s' % (croot + '_aux' + (cext or '.cpp')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
