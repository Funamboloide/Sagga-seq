# SPDX-License-Identifier: GPL-3.0-only
"""The objects of a Gills patch that are not embedded in it (the Gills' knobs, buttons, encoder, LEDs and screen from
the ksoloti-objects library, the audio in and out), for make_bus.py --cpp: their inlets, outlets, attribute values and
code, the way the Ksoloti Patcher puts them in a patch's C++.

The code is two: with HOST_TEST defined, stand-ins that read and write the host test's arrays (host_pot, host_btn,
host_enc, host_esw, host_line, host_led); else the objects' own code, read from a checkout of ksoloti-objects
(KOBJ=/path/to/ksoloti-objects, for the Cortex-M4 check: what the patch costs), or, without one, small stand-ins.
"""
import os
import re
import xml.etree.ElementTree as ET

KOBJ = os.environ.get('KOBJ')


def _axo(rel):
    if not KOBJ:
        return None
    p = os.path.join(KOBJ, 'objects', rel)
    if not os.path.exists(p):
        return None
    return list(ET.parse(p).getroot())[0]


def _code(o):
    return {c.tag: (c.text or '') for c in o if c.tag.startswith('code.')}


def _sel(e):
    return {c.get('attributeName'): (c.get('selection') if c.get('selection') is not None else c.get('value'))
            for c in e.find('attribs')}


def _cvals(o, sel):
    """the C values of the attributes selected, from the object's definition"""
    out = {}
    for c in o.find('attribs'):
        an = c.get('name')
        if c.tag == 'combo':
            me = [s.text for s in c.findall('./MenuEntries/string')]
            ce = [s.text for s in c.findall('./CEntries/string')]
            m = dict(zip(me, ce))
            out[an] = m.get(sel.get(an), ce[0] if ce else '0')
        elif c.tag == 'spinner':
            out[an] = sel.get(an, '0')
        else:
            out[an] = '0'
    return out


POT_CH = {str(i + 1): c for i, c in enumerate([0, 1, 2, 3, 6, 7, 8, 9, 11, 12])}
LED_IX = {'1': 0, '2': 1, '3 blue': 2, '3 red': 3, '4 blue': 4, '4 red': 5}


def _host(kind, sel):
    """a stand-in: the same inlets and outlets, the host's arrays"""
    if kind == 'pot':
        return {'code.krate': 'outlet_out = host_pot[%d];' % (int(sel['pot']) - 1)}
    if kind == 'button':
        return {'code.krate': 'outlet_out = host_btn[%d] ? (1 << 27) : 0;' % (int(sel['button']) - 1)}
    if kind == 'encoder':
        return {'code.krate': 'outlet_out = host_enc; outlet_sw = host_esw ? (1 << 27) : 0;'}
    if kind == 'led':
        return {'code.krate': 'host_led[%d] = inlet_in;' % LED_IX[sel['led']]}
    if kind == 'display':
        return {'code.krate': 'host_line[0] = inlet_line1; host_line[1] = inlet_line2; host_line[2] = inlet_line3; '
                              'host_line[3] = inlet_line4;'}
    if kind == 'in':
        return {'code.krate': 'for (int j = 0; j < BUFSIZE; j++) { outlet_left[j] = AudioInputLeft[j]; '
                              'outlet_right[j] = AudioInputRight[j]; }'}
    if kind == 'out':
        return {'code.krate': 'for (int j = 0; j < BUFSIZE; j++) { AudioOutputLeft[j] += inlet_left[j]; '
                              'AudioOutputRight[j] += inlet_right[j]; }'}
    raise KeyError(kind)


SHAPES = {
    'ksoloti/gills/pot p': ('pot', 'ksoloti/gills/pot p.axo', [], [('frac32.positive', 'out')]),
    'ksoloti/gills/button': ('button', 'ksoloti/gills/button.axo', [], [('bool32', 'out')]),
    'ksoloti/gills/encoder': ('encoder', 'ksoloti/gills/encoder.axo', [('int32', 'set')],
                              [('int32', 'out'), ('bool32', 'sw')]),
    'ksoloti/gills/led pwm': ('led', 'ksoloti/gills/led pwm.axo', [('frac32.positive', 'in')], []),
    'ksoloti/gills/display': ('display', 'ksoloti/gills/display.axo',
                              [('charptr32', 'line1'), ('charptr32', 'line2'), ('charptr32', 'line3'),
                               ('charptr32', 'line4'), ('int32', 'mode'), ('bool32', 'disable')], []),
    'audio/in stereo': ('in', None, [], [('frac32buffer', 'left'), ('frac32buffer', 'right')]),
    'audio/out stereo': ('out', None, [('frac32buffer', 'left'), ('frac32buffer', 'right')], []),
}


def objdef(e):
    """(inlets, outlets, {attr: C value}, {code section: text}) of a non-embedded object; the code has a HOST_TEST
    branch and the board's own"""
    t = e.get('type')
    kind, rel, inl, outl = SHAPES[t]
    sel = _sel(e)
    host = _host(kind, sel)
    o = _axo(rel) if rel else None
    if o is not None:
        board = _code(o)
        attrs = _cvals(o, sel)
        attrs['parent'] = 'objectinstance_' + e.get('name')
        if kind == 'display':
            attrs['scope'] = '0'
            inc = o.find('includes')
            hdr = ''
            if inc is not None:
                for c in inc:
                    p = os.path.join(KOBJ, 'objects', os.path.dirname(rel), c.text.strip().lstrip('./'))
                    if os.path.exists(p):
                        with open(p) as f:
                            hdr += f.read() + '\n'
            board['code.declaration'] = hdr + board.get('code.declaration', '')
        if kind == 'encoder':
            board['code.declaration'] = 'int32_t disp_value; int32_t disp_switch;\n' + board.get('code.declaration', '')
    else:
        board = dict(host)
        if kind == 'pot':
            board = {'code.krate': 'outlet_out = adcvalues[%d] << 15;' % POT_CH[sel['pot']]}
        attrs = {}
    code = {}
    for sec in set(host) | set(board):
        h, b = host.get(sec, ''), board.get(sec, '')
        if h == b:
            code[sec] = h
        else:
            code[sec] = '#ifdef HOST_TEST\n%s\n#else\n%s\n#endif\n' % (h, b)
    return inl, outl, attrs, code
