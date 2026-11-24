#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""VARIAZIONI for the Ksoloti Gills: FIGO and SCENA in one object (var_engine.h, with figo_engine.h and
scena_engine.h), alone or beside an effect.

    python3 tools/gills/make_bus.py [--fx EFFECT.axp ...] [--out DIR] [--cpp]

It always writes figo_scena.axp (insert) and figo_scena_aux.axp (aux, for a mixer's send and return): FIGO and SCENA
alone, the Gills' knobs and buttons theirs. With --fx it reads an effect patch for the Gills (the Microcosm or the
Chroma Console one: a `panel` object reads the knobs, the effect object makes the sound) and writes, next to it or in
DIR, <name>_figo_scena.axp: the same patch with the variations added, for a bus (the effect and the variations in
aux). The panel gets an inlet `page`: while the variations' page is on it leaves the knobs and the buttons alone, and
when you come back every knob takes its value back when it passes it. The effect patches are not in this repository:
pass yours. --cpp also writes, next to each patch, the C++ the Ksoloti Patcher would make of it (all its objects, the
nets, the root), for the checks in tests/run_sagga_tests.sh: with -DHOST_TEST it runs on a computer with the Gills'
knobs, buttons, screen and LEDs faked; for the Cortex-M4, tools/gills/armcheck/check_bus.sh.
"""
import os
import re
import sys
import copy
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
VAR_UUID = 'b7a1c0de-5ce9-4a00-8000-00000000f160'

# what does not run sample by sample is made small; beside an effect all of the variations' code goes to the Gills'
# second RAM (SRAM3, 64 kB): with it the patch takes less of the first one (44 kB) than the effect alone did
# one section a function (.sram3.text.N, N from __COUNTER__): with GCC, inline and not inline functions in one named
# section are a "section type conflict"; the linker script takes .sram3.* into SRAM3
S3 = ('#ifndef S3_SECT\n#define S3_STR2(x) #x\n#define S3_STR(x) S3_STR2(x)\n'
      '#define S3_SECT(kind) section(".sram3." kind "." S3_STR(__COUNTER__))\n#endif\n')
SMALL = ('#ifdef __clang__\n#define VR_SMALL __attribute__((noinline, minsize%s))\n'
         '#else\n#define VR_SMALL __attribute__((noinline, optimize("Os")%s))\n#endif')
SRAM3 = ', S3_SECT("text")'
MC_COLD_SRAM3 = (S3 + '#undef MC_COLD\n#ifdef __clang__\n#define MC_COLD __attribute__((noinline, minsize, S3_SECT("text")))\n'
                 '#else\n#define MC_COLD __attribute__((noinline, optimize("Os"), S3_SECT("text")))\n#endif\n')

INLETS = ([('frac32buffer', 'inl', 'in left (the send)'), ('frac32buffer', 'inr', 'in right'),
           ('frac32buffer', 'fxl', "the effect's out, left"), ('frac32buffer', 'fxr', "the effect's out, right")]
          + [('frac32.positive', 'p%d' % i, 'pot %d' % i) for i in range(1, 11)]
          + [('bool32', 'b%d' % i, 'button %d' % i) for i in range(1, 5)]
          + [('int32', 'enc', 'encoder'), ('bool32', 'esw', 'encoder switch')]
          + [('charptr32', 'pl%d' % i, "the panel's screen line %d" % i) for i in range(1, 5)]
          + [('frac32.positive', 'pled' + n, "the panel's LED " + n) for n in ('1', '2', '3b', '3r', '4b', '4r')])
OUTLETS = ([('frac32buffer', 'outl', 'out left'), ('frac32buffer', 'outr', 'out right'),
            ('bool32', 'page', "the variations' page is on (to the panel)")]
           + [('charptr32', 'l%d' % i, 'screen line %d' % i) for i in range(1, 5)]
           + [('frac32.positive', 'led' + n, 'LED ' + n) for n in ('1', '2', '3b', '3r', '4b', '4r')])
LED_NAMES = ('1', '2', '3b', '3r', '4b', '4r')
LED_SEL = {'1': '1', '2': '2', '3b': '3 blue', '3r': '3 red', '4b': '4 blue', '4r': '4 red'}

ATTRS = [
    ('routing', 'insert: in -> FIGO -> SCENA (beside an effect: after it); aux: send and return, no dry out',
     [('insert', '0'), ('aux', '1')]),
    ('ingresso', 'stereo, or mono L (the left in on both sides)', [('stereo', '0'), ('mono L', '1')]),
    ('frase', 'FIGO: the phrase, in beats', [('16', '16'), ('8', '8'), ('32', '32')]),
    ('uscita', 'FIGO: the way out (PULITO)', [('auto', '0'), ('tape stop', '1'), ('backspin', '2'), ('secca', '3')]),
    ('anticipo', 'aux: the way to the mixer and back, ms (SHIFT+encoder on the page changes it)',
     [('1.5 ms', '1.5f'), ('0 ms', '0.0f'), ('0.5 ms', '0.5f'), ('1.0 ms', '1.0f'), ('2.0 ms', '2.0f'),
      ('2.5 ms', '2.5f'), ('3.0 ms', '3.0f')]),
]

INIT = '''static int16_t vr_el[SC_ECHO_N] __attribute__ ((section (".sdram")));
static int16_t vr_er[SC_ECHO_N] __attribute__ ((section (".sdram")));
static int16_t vr_rl[SC_ROLL_N] __attribute__ ((section (".sdram")));
static int16_t vr_rr[SC_ROLL_N] __attribute__ ((section (".sdram")));
static float vr_rv[SC_RV_TOTAL] __attribute__ ((section (".sdram")));
static uint32_t vr_tape[FG_N] __attribute__ ((section (".sdram")));
sc_init(vr_el, vr_er, vr_rl, vr_rr, vr_rv);
fg_init(vr_tape);
vr_init(attr_routing, attr_ingresso, attr_anticipo, attr_frase, attr_uscita);'''

KRATE = '''{
    int32_t pots[10] = {inlet_p1, inlet_p2, inlet_p3, inlet_p4, inlet_p5, inlet_p6, inlet_p7, inlet_p8, inlet_p9, inlet_p10};
    bool bs[4] = {inlet_b1 != 0, inlet_b2 != 0, inlet_b3 != 0, inlet_b4 != 0};
    char *pl[4] = {(char *)inlet_pl1, (char *)inlet_pl2, (char *)inlet_pl3, (char *)inlet_pl4};
    int32_t pled[6] = {inlet_pled1, inlet_pled2, inlet_pled3b, inlet_pled3r, inlet_pled4b, inlet_pled4r};
    char *ln[4];
    int32_t led[6];
    vr_block(inlet_inl, inlet_inr, inlet_fxl, inlet_fxr, outlet_outl, outlet_outr, pots, bs, inlet_enc, inlet_esw != 0,
             pl, pled, ln, led);
    outlet_page = vr_page ? (1 << 27) : 0;
    outlet_l1 = ln[0]; outlet_l2 = ln[1]; outlet_l3 = ln[2]; outlet_l4 = ln[3];
    outlet_led1 = led[0]; outlet_led2 = led[1]; outlet_led3b = led[2]; outlet_led3r = led[3];
    outlet_led4b = led[4]; outlet_led4r = led[5];
}'''

MIDI = 'vr_midi(status, data1, data2);'

NOTES_VAR = '''VARIAZIONI: FIGO + SCENA
========================
Le variazioni di FIGO (ripetizioni, roll, reverse, ottave, tape stop, shuffle, gate, indietro, memoria) e di SCENA
(build-up, break-down, roll, freeze) sullo stesso suono.

LA PAGINA%(page)s
MANOPOLE: 1 SCENA (sinistra break-down, centro pulito, destra build-up), 2 FIGO (quanto interviene), 3 CARATTERE
  (da dub a glitch), 4 MEMORIA, 5 MOTO (SCENA si muove da sola), 6 ECO, 7 FEEDBACK, 8 FILTRO, 9 RIVERB, 10 RITORNI.
  Con SHIFT (encoder tenuto): 6 RISON, 7 RUMORE, 8 CRUSH, 9 LIV.MEMORIA, 10 LIVELLO (degli interventi di FIGO).
  Pick-up: una manopola riprende il suo valore quando ci passa sopra ("~" e "o" sullo schermo finche' non lo aggancia).
PULSANTI: 1 ROLL (tenuto), 2 FREEZE, 3 PULITO (FIGO esce a tempo e SCENA torna pulita; di nuovo: FIGO riparte),
  4 HOLD (ripete il battito appena passato; di nuovo: torna il loop).
  SHIFT+1: la frase di FIGO parte da qui. SHIFT+4: TAP (se non arriva il clock MIDI).
  SHIFT+encoder: l'anticipo in aux (la strada fino al mixer e ritorno), un decimo di millisecondo a scatto.
SCHERMO: riga 1 FIGO, CARATTERE, MEMORIA e INS/AUX; riga 2 SCENA; riga 3 il tempo e la frase; riga 4 l'intervento
  di FIGO e la MEMORIA. Quando giri una manopola le righe 3-4 mostrano il suo valore.
LED (sulla pagina): 1 il battito, 2 FIGO interviene (tenue: la memoria), 3 blu build-up / rosso break-down,
  4 blu HOLD o un loop di SCENA, rosso SHIFT (lampeggia: PULITO o RELEASE).

MIDI (qualsiasi canale, da qualsiasi pagina): CC 110 SCENA, 111 MOTO, 112 ROLL (tenuto), 113 FREEZE, 114 RELEASE,
  115 FIGO, 116 CARATTERE, 117 MEMORIA, 118 HOLD, 119 PULITO.%(cc)s Clock, START e STOP: il tempo.

IL SUONO (attributo routing dell'oggetto "variazioni", nel Patcher):
  aux: per mandata e ritorno del mixer. Escono %(aux)s: niente pulito (e' gia' sul mixer). Quando non succede niente le
       variazioni non danno niente.
  insert: in serie, %(ins)s. Quando non succede niente il suono passa identico, bit per bit.
  Gli altri attributi: ingresso (stereo o mono L), frase (16, 8 o 32 battiti), uscita (il modo di uscire di PULITO:
  auto, tape stop, backspin, secca), anticipo (in aux: di quanto le ripetizioni partono prima, 1.5 ms).
  In aux le ripetizioni partono l'anticipo prima: cosi' cadono sulla griglia del pulito al mixer. Per tararlo: una
  cassa dritta, FIGO 100, CARATTERE 0, e gira SHIFT+encoder finche' le ripetizioni non si fondono con i colpi.
'''

PAGE_ALONE = ': le manopole e i pulsanti sono delle variazioni.'
PAGE_FX = ''' (una pressione lunga dell'encoder):
  Le manopole e i pulsanti sono di %(fx)s o delle variazioni. Tieni premuto l'encoder per un secondo senza
  toccare altro e lascia: passi all'altra pagina (lo schermo, tenendolo, scrive LASCIA: ...). Tornando su %(fx)s
  ogni manopola riprende il suo valore quando ci passa sopra: niente salta. %(fx)s intanto continua a suonare, e
  il MIDI e il clock gli arrivano sempre.'''


def read(name):
    with open(os.path.join(HERE, name)) as f:
        return f.read()


def cdata(s):
    assert ']]>' not in s
    return '<![CDATA[' + s + ']]>'


def var_declaration(alone, fx_name='EFFETTO', echo_bits=18, tape_bits=21):
    """the variations object's code: the knobs' platform is in var_engine.h; cold code in SRAM3 beside an effect"""
    d = []
    if not alone:
        d.append(S3 + SMALL % (SRAM3, SRAM3))
        for m in ('SC', 'FG', 'VR'):
            d += ['#define %s_HOT __attribute__((S3_SECT("text")))' % m,
                  '#define %s_FN __attribute__((S3_SECT("text")))' % m,
                  '#define %s_RO __attribute__((S3_SECT("rodata")))' % m]
    else:
        d.append(SMALL % ('', ''))
        d.append('#define VR_ALONE')
    d += ['#define SC_COLD VR_SMALL', '#define FG_COLD VR_SMALL', '#define VR_COLD VR_SMALL']
    d += ['#define SC_ECHO_BITS %d' % echo_bits, '#define FG_BITS %d' % tape_bits, '#define VR_FX_NAME "%s"' % fx_name]
    d.append(read('scena_engine.h'))
    d.append(read('figo_engine.h'))
    d.append(read('var_engine.h'))
    d += ['#undef %s_%s' % (m, k) for m in ('SC', 'FG', 'VR') for k in ('COLD', 'HOT', 'FN', 'RO')]
    d += ['#undef VR_SMALL', '#undef SC_ECHO_BITS', '#undef FG_BITS', '#undef VR_FX_NAME', '#undef VR_ALONE', '']
    return '\n'.join(d)


def var_object(name, x, y, alone, routing, fx_name='EFFETTO', echo_bits=18, tape_bits=21, effect_desc=None):
    """the <patchobj> of the variations object, as an ElementTree element"""
    po = ET.Element('patchobj', {'type': 'patch/object', 'uuid': VAR_UUID, 'name': name, 'x': str(x), 'y': str(y)})
    ET.SubElement(po, 'params')
    at = ET.SubElement(po, 'attribs')
    sel = {'routing': routing}
    for an, _, entries in ATTRS:
        ET.SubElement(at, 'combo', {'attributeName': an, 'selection': sel.get(an, entries[0][0])})
    o = ET.SubElement(po, 'object', {'id': 'patch/object', 'uuid': VAR_UUID})
    ET.SubElement(o, 'sDescription').text = ('VARIAZIONI: FIGO and SCENA, the variations on the loop'
                                            + ('' if alone else ' beside ' + (effect_desc or 'an effect')))
    ET.SubElement(o, 'author').text = 'SAGGA'
    ET.SubElement(o, 'license').text = 'GPL'
    il = ET.SubElement(o, 'inlets')
    for t, n, d in INLETS:
        ET.SubElement(il, t, {'name': n, 'description': d})
    ol = ET.SubElement(o, 'outlets')
    for t, n, d in OUTLETS:
        ET.SubElement(ol, t, {'name': n, 'description': d})
    ET.SubElement(o, 'displays')
    ET.SubElement(o, 'params')
    oa = ET.SubElement(o, 'attribs')
    for an, desc, entries in ATTRS:
        c = ET.SubElement(oa, 'combo', {'name': an, 'description': desc})
        me = ET.SubElement(c, 'MenuEntries')
        for m, _ in entries:
            ET.SubElement(me, 'string').text = m
        ce = ET.SubElement(c, 'CEntries')
        for _, v in entries:
            ET.SubElement(ce, 'string').text = v
    ET.SubElement(o, 'includes')
    for tag, text in (('code.declaration', var_declaration(alone, fx_name, echo_bits, tape_bits)),
                      ('code.init', INIT), ('code.krate', KRATE), ('code.midihandler', MIDI)):
        ET.SubElement(o, tag).text = text
    return po


# --------------------------------------------------------------------------------------------- writing .axp
def serialize(root):
    """the patch as the Patcher writes it: code in CDATA"""
    out = []

    def attrs(e):
        return ''.join(' %s="%s"' % (k, escape(v, {'"': '&quot;'})) for k, v in e.attrib.items())

    def walk(e, ind):
        pad = '   ' * ind
        if e.tag.startswith('code.') or e.tag == 'notes':
            out.append('%s<%s%s>%s</%s>' % (pad, e.tag, attrs(e), cdata(e.text or ''), e.tag))
            return
        kids = list(e)
        text = (e.text or '').strip()
        if not kids and not text:
            out.append('%s<%s%s/>' % (pad, e.tag, attrs(e)))
            return
        if not kids:
            out.append('%s<%s%s>%s</%s>' % (pad, e.tag, attrs(e), escape(text), e.tag))
            return
        out.append('%s<%s%s>' % (pad, e.tag, attrs(e)))
        for k in kids:
            walk(k, ind + 1)
        out.append('%s</%s>' % (pad, e.tag))
    walk(root, 0)
    return '\n'.join(out) + '\n'


def net(src, dsts):
    n = ET.Element('net')
    ET.SubElement(n, 'source', {'obj': src[0], 'outlet': src[1]})
    for d in dsts:
        ET.SubElement(n, 'dest', {'obj': d[0], 'inlet': d[1]})
    return n


def gills_obj(kind, name, x, y, attr=None):
    """a Gills hardware object (the ksoloti-objects library), as the effect patches have them"""
    types = {
        'pot': ('ksoloti/gills/pot p', '1c0c845ed2d7e06ae5f377ba13d9d09f4747ac89', [('combo', 'pot')]),
        'button': ('ksoloti/gills/button', '07be7a50-1051-436a-92aa-03e2fb9b1229', [('combo', 'button')]),
        'led': ('ksoloti/gills/led pwm', 'e6534d2d-0815-4b4a-8351-99987f214822', [('combo', 'led')]),
    }
    t, uuid, al = types[kind]
    o = ET.Element('obj', {'type': t, 'uuid': uuid, 'name': name, 'x': str(x), 'y': str(y)})
    ET.SubElement(o, 'params')
    a = ET.SubElement(o, 'attribs')
    for tag, an in al:
        ET.SubElement(a, tag, {'attributeName': an, 'selection': attr})
    return o


def alone_patch(routing):
    """FIGO + SCENA alone: the knobs, the buttons, the encoder, the screen and the LEDs, the audio"""
    root = ET.Element('patch-1.0', {'appVersion': '1.0.12'})
    ET.SubElement(root, 'comment', {'type': 'patch/comment', 'x': '14', 'y': '10',
                                    'text': 'VARIAZIONI - FIGO + SCENA. Le istruzioni: Patch > Notes.'})
    for i in range(10):
        root.append(gills_obj('pot', 'pot_%d' % (i + 1), 20 + 120 * (i % 8), 40 + 60 * (i // 8), str(i + 1)))
    for k in range(4):
        root.append(gills_obj('button', 'button_%d' % (k + 1), 260 + 120 * k, 100, str(k + 1)))
    enc = ET.SubElement(root, 'obj', {'type': 'ksoloti/gills/encoder', 'uuid': '8d8c7129-cce1-491f-98b4-6ecb6355cfee',
                                      'name': 'encoder_1', 'x': '740', 'y': '100'})
    ET.SubElement(enc, 'params')
    ea = ET.SubElement(enc, 'attribs')
    ET.SubElement(ea, 'spinner', {'attributeName': 'min', 'value': '-65536'})
    ET.SubElement(ea, 'spinner', {'attributeName': 'max', 'value': '65535'})
    ai = ET.SubElement(root, 'obj', {'type': 'audio/in stereo', 'uuid': '99848ad6d90a8e615e83b2e619cfc806f28e7281',
                                     'name': 'audio_in', 'x': '900', 'y': '100'})
    ET.SubElement(ai, 'params'); ET.SubElement(ai, 'attribs')
    root.append(var_object('variazioni', 330, 160, True, routing))
    disp = ET.SubElement(root, 'obj', {'type': 'ksoloti/gills/display', 'uuid': '0c083e83-0280-4cf2-b747-8a00859bb904',
                                       'name': 'oled', 'x': '640', 'y': '160'})
    ET.SubElement(disp, 'params')
    da = ET.SubElement(disp, 'attribs')
    ET.SubElement(da, 'combo', {'attributeName': 'useScope', 'selection': 'off'})
    ET.SubElement(da, 'objref', {'attributeName': 'scope', 'obj': ''})
    ET.SubElement(da, 'combo', {'attributeName': 'narrowFont', 'selection': 'on'})
    for j, n in enumerate(LED_NAMES):
        root.append(gills_obj('led', 'led_' + n, 640, 320 + 50 * j, LED_SEL[n]))
    ao = ET.SubElement(root, 'obj', {'type': 'audio/out stereo', 'uuid': 'a1ca7a567f535acc21055669829101d3ee7f0189',
                                     'name': 'audio_out', 'x': '640', 'y': '640'})
    ET.SubElement(ao, 'params'); ET.SubElement(ao, 'attribs')
    nets = ET.SubElement(root, 'nets')
    for i in range(10):
        nets.append(net(('pot_%d' % (i + 1), 'out'), [('variazioni', 'p%d' % (i + 1))]))
    for k in range(4):
        nets.append(net(('button_%d' % (k + 1), 'out'), [('variazioni', 'b%d' % (k + 1))]))
    nets.append(net(('encoder_1', 'out'), [('variazioni', 'enc')]))
    nets.append(net(('encoder_1', 'sw'), [('variazioni', 'esw')]))
    nets.append(net(('audio_in', 'left'), [('variazioni', 'inl')]))
    nets.append(net(('audio_in', 'right'), [('variazioni', 'inr')]))
    nets.append(net(('variazioni', 'outl'), [('audio_out', 'left')]))
    nets.append(net(('variazioni', 'outr'), [('audio_out', 'right')]))
    for i in range(1, 5):
        nets.append(net(('variazioni', 'l%d' % i), [('oled', 'line%d' % i)]))
    for n in LED_NAMES:
        nets.append(net(('variazioni', 'led' + n), [('led_' + n, 'in')]))
    s = ET.SubElement(root, 'settings')
    ET.SubElement(s, 'subpatchmode').text = 'no'
    notes = NOTES_VAR % {'page': PAGE_ALONE, 'cc': ' Anche i CC 20-24 di SCENA (20 SCENA, 21 MOTO, 22 ROLL, 23 FREEZE, 24 RELEASE).',
                         'aux': "gli interventi di FIGO, la memoria, il fruscio, l'eco, il riverbero e i loop di SCENA",
                         'ins': "l'ingresso passa da FIGO e poi da SCENA"}
    ET.SubElement(root, 'notes').text = notes
    wp = ET.SubElement(root, 'windowPos')
    for k, v in (('x', '40'), ('y', '40'), ('width', '1100'), ('height', '760')):
        ET.SubElement(wp, k).text = v
    return root


# --------------------------------------------------------------------------------- beside an effect: the merge
PANEL_DECL_ADD = {
    'microcosm': r'''
/* ---- the variations' page (VARIAZIONI beside this effect): while it is on the knobs and the buttons are theirs ---- */
bool pgWas;
/* the page is on: MIDI, the clock and the screen go on, the knobs and the buttons are left alone */
MC_COLD void pgFrozen(int32_t enc) {
    ticks++;
    midiTick();
    tapTick++;
    if (tapTick > 100000) tapTick = 100000;
    if (loopActive()) holdSt = false;
    subZone = zoneOf(prim[5], 6, subZone);
    rvZone = zoneOf(prim[9], 4, rvZone);
    lsZone = zoneOf(sec[5], 5, lsZone);
    shZone = zoneOf(prim[2], 4, shZone);
    knobBpm = bpmOf(prim[5]);
    if (popT > 0) popT--;
    encLast = enc;
    shift = false;
}
/* back: every knob takes its value back when it passes it (pick-up); the buttons and the encoder switch start from
   where they are (no press, no long press, no REVERSE) */
MC_COLD void pgResume(const int32_t *pot, const bool *b, bool esw) {
    for (int i = 0; i < UI_NP; i++) {
        float raw = (float)pot[i] * (1.0f / 134217728.0f);
        raw = raw < 0.0f ? 0.0f : (raw > 1.0f ? 1.0f : raw);
        pv[i] = pLast[i] = pShow[i] = raw;
        float d = raw - prim[i];
        pickP[i] = (d > 0.015f || d < -0.015f) ? 1 : 0;
        if (hasSec(i)) pickS[i] = 1;
    }
    for (int k = 0; k < 4; k++) { uint8_t r = b[k] ? 1 : 0; bRaw[k] = bSt[k] = r; bCnt[k] = 12; bHeld[k] = 0; bLong[k] = 1; }
    bRaw[4] = bSt[4] = esw ? 1 : 0; bCnt[4] = 12; bHeld[4] = 2000; shUsed = true;
}
''',
    'chroma': r'''
/* ---- the variations' page (VARIAZIONI beside this effect): while it is on the knobs and the buttons are theirs ---- */
bool pgWas;
/* the page is on: MIDI, the clock, the gestures and the screen go on, the knobs and the buttons are left alone */
MC_COLD void pgFrozen(int32_t enc, int32_t cs) {
    ticks++;
    midiTick(cs);
    tapTick++;
    if (tapTick > 100000) tapTick = 100000;
    fstyleZ = zoneOf(sec[9], 3, fstyleZ);
    rdivZ = zoneOf(prim[2], 8, rdivZ);
    tdivZ = zoneOf(prim[4], 8, tdivZ);
    gestureTick();
    if (popT > 0) popT--;
    encLast = enc;
    shift = false;
}
/* back: every knob takes its value back when it passes it (pick-up), a gesture goes on until its knob is moved from
   here; the buttons and the encoder switch start from where they are */
MC_COLD void pgResume(const int32_t *pot, const bool *b, bool esw) {
    for (int i = 0; i < UI_NP; i++) {
        float raw = (float)pot[i] * (1.0f / 134217728.0f);
        raw = raw < 0.0f ? 0.0f : (raw > 1.0f ? 1.0f : raw);
        pv[i] = pLast[i] = pShow[i] = raw;
        float d = raw - prim[i];
        pickP[i] = (d > 0.015f || d < -0.015f) ? 1 : 0;
        if (hasSec(i)) pickS[i] = 1;
    }
    for (int k = 0; k < 8; k++) gStop[k] = pv[k];
    for (int k = 0; k < 4; k++) { uint8_t r = b[k] ? 1 : 0; bRaw[k] = bSt[k] = r; bCnt[k] = 12; bHeld[k] = 0; bLong[k] = 1; bShf[k] = 0; }
    bRaw[4] = bSt[4] = esw ? 1 : 0; bCnt[4] = 12; bHeld[4] = 0;
}
''',
}
PANEL_KRATE = {
    'microcosm': ('    uiTick(pots, bs, inlet_enc, inlet_esw);\n',
                  '    if (inlet_page) pgFrozen(inlet_enc);\n'
                  '    else { if (pgWas) pgResume(pots, bs, inlet_esw); uiTick(pots, bs, inlet_enc, inlet_esw); }\n'
                  '    pgWas = inlet_page != 0;\n'),
    'chroma': ('    uiTick(pots, bs, inlet_enc, inlet_esw, inlet_cstate);\n',
               '    if (inlet_page) pgFrozen(inlet_enc, inlet_cstate);\n'
               '    else { if (pgWas) pgResume(pots, bs, inlet_esw); uiTick(pots, bs, inlet_enc, inlet_esw, inlet_cstate); }\n'
               '    pgWas = inlet_page != 0;\n'),
}
# the effects: what they are called, the object that makes the sound, the SDRAM they leave free
EFFECTS = {
    'microcosm': {'name': 'MICROCOSM', 'dsp': 'microcosm', 'echo_bits': 17, 'tape_bits': 20, 'routing': 'aux',
                  'desc': 'Microcosm'},
    'chroma': {'name': 'CHROMA', 'dsp': 'chroma', 'echo_bits': 18, 'tape_bits': 21, 'routing': 'aux',
               'desc': 'Chroma Console'},
}


def const_tables(code):
    """`static const char *x[N] = {` -> `static const char *const x[N] = {`: read-only, with the code"""
    return re.sub(r'static const char \*(\w+)\[', r'static const char *const \1[', code)


def once(s, a, b, what):
    if s.count(a) != 1:
        raise SystemExit('make_bus: %s: expected once, found %d times: %r' % (what, s.count(a), a[:60]))
    return s.replace(a, b)


def which_effect(root):
    names = [po.get('name') for po in root.findall('patchobj')]
    for k, e in EFFECTS.items():
        if e['dsp'] in names and 'panel' in names:
            return k
    raise SystemExit('make_bus: not a Microcosm or Chroma patch for the Gills (no panel + microcosm/chroma objects)')


def merge(fx_path):
    root = ET.parse(fx_path).getroot()
    kind = which_effect(root)
    E = EFFECTS[kind]
    objs = {o.get('name'): o for o in list(root.findall('obj')) + list(root.findall('patchobj'))}
    # the panel: an inlet `page`, frozen while it is on, pick-up when it goes off; its cold code in SRAM3
    panel = objs['panel'].find('object')
    ET.SubElement(panel.find('inlets'), 'bool32', {'name': 'page', 'description': "the variations' page is on"})
    decl = panel.find('code.declaration')
    decl.text = MC_COLD_SRAM3 + const_tables(decl.text) + PANEL_DECL_ADD[kind] + '#undef MC_COLD\n'
    kr = panel.find('code.krate')
    a, b = PANEL_KRATE[kind]
    kr.text = once(kr.text, a, b, 'panel k-rate')
    ini = panel.find('code.init')
    ini.text = (ini.text or '') + '\npgWas = false;\n'
    # the effect: in aux for the bus
    dsp = objs[E['dsp']]
    for c in dsp.find('attribs'):
        if c.get('attributeName') == 'routing':
            c.set('selection', E['routing'])
    # room for the variations: the screen, the LEDs and the out to the right
    for n, o in objs.items():
        if n == 'oled' or n.startswith('led_') or n == 'audio_out':
            o.set('x', str(int(o.get('x')) + 310))
    var = var_object('variazioni', 640, 160, False, 'aux', E['name'], E['echo_bits'], E['tape_bits'], E['desc'])
    # (in the patch file after the effect: the Patcher's order goes by position anyway)
    kids = list(root)
    root.insert(kids.index(dsp) + 1, var)
    # the nets
    nets = root.find('nets')
    for n in list(nets):
        s = n.find('source')
        so, sp = s.get('obj'), s.get('outlet')
        dests = n.findall('dest')
        if so.startswith('pot_') or so.startswith('button_') or so == 'encoder_1':
            for d in dests:
                if d.get('obj') == 'panel':
                    ET.SubElement(n, 'dest', {'obj': 'variazioni', 'inlet': d.get('inlet')})
        elif so == 'audio_in':
            ET.SubElement(n, 'dest', {'obj': 'variazioni', 'inlet': 'inl' if sp == 'left' else 'inr'})
        elif so == E['dsp'] and sp in ('outL', 'outR'):
            for d in dests:
                n.remove(d)
            ET.SubElement(n, 'dest', {'obj': 'variazioni', 'inlet': 'fxl' if sp == 'outL' else 'fxr'})
        elif so == 'panel' and re.match(r'l[1-4]$', sp):
            for d in dests:
                n.remove(d)
            ET.SubElement(n, 'dest', {'obj': 'variazioni', 'inlet': 'p' + sp})
        elif so == 'panel' and sp.startswith('led'):
            for d in dests:
                n.remove(d)
            ET.SubElement(n, 'dest', {'obj': 'variazioni', 'inlet': 'p' + sp})
    nets.append(net(('variazioni', 'outl'), [('audio_out', 'left')]))
    nets.append(net(('variazioni', 'outr'), [('audio_out', 'right')]))
    nets.append(net(('variazioni', 'page'), [('panel', 'page')]))
    for i in range(1, 5):
        nets.append(net(('variazioni', 'l%d' % i), [('oled', 'line%d' % i)]))
    for nm in LED_NAMES:
        nets.append(net(('variazioni', 'led' + nm), [('led_' + nm, 'in')]))
    # the notes: the variations first
    notes = root.find('notes')
    fxn = E['desc']
    head = NOTES_VAR % {'page': PAGE_FX % {'fx': fxn}, 'cc': ' (I CC 20-24 restano di %s.)' % fxn,
                        'aux': ("l'effetto di %s, gli interventi di FIGO, la memoria, il fruscio, l'eco, il riverbero "
                                "e i loop di SCENA, ognuno dalla mandata" % fxn),
                        'ins': "%s, poi FIGO, poi SCENA (anche %s va messo in insert: il suo attributo routing)" % (fxn, fxn)}
    if notes is None:
        notes = ET.SubElement(root, 'notes')
    notes.text = head + '\n\n' + (notes.text or '')
    root.find('comment').set('text', '%s + VARIAZIONI (FIGO + SCENA) per un bus. Le istruzioni: Patch > Notes.' % fxn)
    return kind, root


# ------------------------------------------------------------------------------- the Patcher's C++ of a patch
def ctype(t, inlet):
    if t == 'frac32buffer':
        return 'const int32buffer' if inlet else 'int32buffer &'
    if t == 'charptr32':
        return 'const char*' if inlet else 'char* &'
    return 'const int32_t' if inlet else 'int32_t &'


def default_of(t):
    return {'frac32buffer': 'ZEROBUFFER', 'charptr32': '0'}.get(t, 'UNCONNECTED_INPUT')


def sink_of(t):
    return {'frac32buffer': 'UNCONNECTED_OUTPUT_BUFFER', 'charptr32': 'UNCONNECTED_CHARPTR'}.get(t, 'UNCONNECTED_OUTPUT')


def net_ctype(t):
    return {'frac32buffer': 'int32buffer', 'charptr32': 'char*'}.get(t, 'int32_t')


def patcher_cpp(root, objdefs):
    """the patch as C++, the way the Patcher writes it (one class an object, the nets, rootc's dsp and MIDI). objdefs:
    name -> (inlets, outlets, attrs {name: C value}, code {section: text}) for the objects that are not embedded"""
    insts = []
    for e in root:
        if e.tag in ('obj', 'patchobj'):
            insts.append(e)
    # the Patcher sorts by position: y, then x
    insts.sort(key=lambda e: (int(e.get('y')), int(e.get('x'))))
    nets = root.find('nets')
    src_of = {}        # (obj, inlet) -> net index
    out_of = {}        # (obj, outlet) -> net index
    net_types = []
    for i, n in enumerate(nets):
        s = n.find('source')
        out_of[(s.get('obj'), s.get('outlet'))] = i
        for d in n.findall('dest'):
            src_of[(d.get('obj'), d.get('inlet'))] = i
        net_types.append(None)
    classes, calls, members, midis = [], [], [], []
    for e in insts:
        name = e.get('name')
        if e.tag == 'patchobj':
            o = e.find('object')
            inl = [(c.tag, c.get('name')) for c in o.find('inlets')]
            outl = [(c.tag, c.get('name')) for c in o.find('outlets')]
            code = {c.tag: (c.text or '') for c in o if c.tag.startswith('code.')}
            attrs = {}
            defs = {}
            for c in o.find('attribs'):
                defs[c.get('name')] = dict(zip([s.text for s in c.findall('./MenuEntries/string')],
                                               [s.text for s in c.findall('./CEntries/string')]))
            for c in e.find('attribs'):
                an = c.get('attributeName')
                attrs[an] = defs[an][c.get('selection')]
        else:
            inl, outl, attrs, code = objdefs(e)
        for k, (t, nn) in enumerate(outl):
            i = out_of.get((name, nn))
            if i is not None:
                net_types[i] = t
        cn = 'objectinstance_' + name
        body = []
        decl = code.get('code.declaration', '')
        args = ['%s inlet_%s' % (ctype(t, True), nn) for t, nn in inl] + \
               ['%soutlet_%s' % (ctype(t, False), nn) for t, nn in outl]
        txt = ('class %s {\n  public: // v1\n  rootc *parent;\n%s\n  public: void Init(rootc *_parent) {\n  parent = _parent;\n%s\n  }\n'
               '  public: void Dispose() {\n%s\n  }\n  public: void dsp(%s) {\n%s\n  }\n') % (
            cn, decl, code.get('code.init', ''), code.get('code.dispose', ''), ', '.join(args), code.get('code.krate', ''))
        if code.get('code.srate'):
            txt = txt[:-4] + '\n  uint32_t buffer_index;\n  for (buffer_index = 0; buffer_index < BUFSIZE; buffer_index++) {\n%s\n  }\n  }\n' % code['code.srate']
        if code.get('code.midihandler'):
            txt += '  void MidiInHandler(midi_device_t dev, uint8_t port, uint8_t status, uint8_t data1, uint8_t data2) {\n%s\n  }\n' % code['code.midihandler']
            midis.append('    %s_i.MidiInHandler(dev, port, status, data1, data2);' % cn)
        txt += '};\n'
        for an, av in sorted(attrs.items(), key=lambda kv: -len(kv[0])):
            txt = re.sub(r'\battr_%s\b' % re.escape(an), av, txt)
        classes.append(txt)
        members.append('  %s %s_i;' % (cn, cn))
        cargs = []
        for t, nn in inl:
            i = src_of.get((name, nn))
            cargs.append('net%d' % i if i is not None else default_of(t))
        for t, nn in outl:
            i = out_of.get((name, nn))
            cargs.append('net%d' % i if i is not None else sink_of(t))
        calls.append('    %s_i.dsp(%s);' % (cn, ', '.join(cargs)))
    netdecl = ['  %s net%d;' % (net_ctype(t or 'int32'), i) for i, t in enumerate(net_types)]
    # the buffers in the SDRAM: HT_SDRAM, the attribute on the board, nothing on a computer
    classes = [re.sub(r'__attribute__\s*\(\(\s*section\s*\(\s*"\.sdram"\s*\)\s*\)\)', 'HT_SDRAM', c) for c in classes]
    out = ['/* the Patcher\'s C++ of this patch (make_bus.py --cpp), for the checks */',
           'class rootc;']
    out += classes
    out.append('class rootc {\n  public:')
    out += members
    out += netdecl
    out.append('  int32_t UNCONNECTED_OUTPUT;\n  char *UNCONNECTED_CHARPTR;\n  int32buffer UNCONNECTED_OUTPUT_BUFFER;')
    out.append('  void Init() {')
    out += ['    %s_i.Init(this);' % m.split()[0] for m in members]
    out.append('  }\n  void dsp() {\n    static const int32_t UNCONNECTED_INPUT = 0;\n    static const int32buffer ZEROBUFFER = {0};')
    out += calls
    out.append('  }\n  void MidiInHandler(midi_device_t dev, uint8_t port, uint8_t status, uint8_t data1, uint8_t data2) {')
    out += midis
    out.append('  }\n};')
    return '\n'.join(out) + '\n'


def main(argv):
    out_dir = None
    fxs = []
    cpp = False
    rest = list(argv)
    while rest:
        a = rest.pop(0)
        if a == '--fx':
            fxs.append(rest.pop(0))
        elif a == '--out':
            out_dir = rest.pop(0)
        elif a == '--cpp':
            cpp = True
        else:
            raise SystemExit(__doc__)
    od = out_dir or HERE
    os.makedirs(od, exist_ok=True)
    written = []
    for routing, fn in (('insert', 'figo_scena.axp'), ('aux', 'figo_scena_aux.axp')):
        p = os.path.join(od, fn)
        with open(p, 'w') as f:
            f.write(serialize(alone_patch(routing)))
        written.append(p)
    alone_fx = []
    for fx in fxs:
        kind, root = merge(fx)
        base = os.path.splitext(os.path.basename(fx))[0]
        base = re.sub(r'_gills$', '', base)
        p = os.path.join(out_dir or os.path.dirname(os.path.abspath(fx)), base + '_figo_scena.axp')
        with open(p, 'w') as f:
            f.write(serialize(root))
        written.append(p)
        # the effect as it is, with the routing the merged patch gives it: for the test that compares the two
        er = ET.parse(fx).getroot()
        for po in er.findall('patchobj'):
            if po.get('name') == EFFECTS[kind]['dsp']:
                for c in po.find('attribs'):
                    if c.get('attributeName') == 'routing':
                        c.set('selection', EFFECTS[kind]['routing'])
        alone_fx.append((os.path.join(os.path.dirname(p), base + '_effect.cpp'), er))
    if cpp:
        import gills_objects
        for p in written:
            root = ET.parse(p).getroot()
            with open(os.path.splitext(p)[0] + '.cpp', 'w') as f:
                f.write(patcher_cpp(root, gills_objects.objdef))
        for p, er in alone_fx:
            with open(p, 'w') as f:
                f.write(patcher_cpp(er, gills_objects.objdef))
    for p in written:
        print('wrote %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
