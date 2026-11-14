# SAGGA SEQ 0.19 - Note di rilascio

**I MIDI FX in catena.** Fino alla 0.18 una traccia aveva un MIDI FX alla volta. Adesso **i quattro possono suonare
insieme** sulla stessa traccia, sempre in quest'ordine:

1. **VEL CURVE**: la velocity (da qui partono tutti gli altri);
2. **OCTAVE**: la nota spostata d'ottava;
3. **HARM**: la seconda voce, costruita sulla nota che OCTAVE ha spostato;
4. **ECHO**: le ripetizioni della nota **e della seconda voce**.

## Sull'FM-1 (HOME 6)

* **K1 mostra uno dei quattro.** Se non suona è READY (`T1 MIDI FX HARM READY: SEQ + WHITE 6`): K2-K4 lo preparano,
  **SEQ + bianco 6 lo aggiunge alla catena** (`T1 MIDI FX HARM STARTS: HARM+ECHO`). Gli altri continuano a suonare.
* **Se suona**, sullo schermo c'è `MIDI FX ON`: K2-K4 lo cambiano dal vivo. SEQ + bianco 6 subito dopo che K1 l'ha
  trovato (`T1 MIDI FX ECHO PLAYS: SEQ + WHITE 6 TAKES IT OUT`) lo toglie dalla catena; dopo un giro di K2-K4 quel tasto
  torna all'EUCLID.
* **K1 su OFF, SEQ + bianco 6: si fermano tutti.**
* La riga del titolo dice la catena, nell'ordine in cui suona: `HOME 6/8 FX OCT+HARM+ECHO`.

## Cosa cambia anche

* **Ogni effetto ricorda i suoi valori nel progetto** (fino alla 0.18 si salvava solo quello che suonava; gli altri
  restavano finché l'FM-1 era acceso).
* **L'ECHO ripete anche la voce di HARM**, e così l'ECHO ALL (FX + OCT+) sulle tracce che non hanno un ECHO loro.
* **Uno snapshot non cambia i MIDI FX**: la catena è della traccia, non dello snapshot (fino alla 0.18 lo snapshot
  riportava il suo effetto).
* **Il tablet** (SAGGA Live): MIDI FX sceglie l'effetto, FX AMOUNT la sua quantità, **FX GO lo aggiunge alla catena
  della traccia del tablet; di nuovo: lo toglie**; su OFF li ferma tutti.
* **Il grid** (TRACK 3, riga 2): ogni effetto che suona è bianco; un tocco su uno che suona lo ferma, su un altro lo fa
  READY (arancione), di nuovo: parte. OFF due volte: si fermano tutti.
* **L'editor del Pi**: nella scheda Traccia, MIDI FX in catena, una casella per effetto e i suoi valori.

## E una catena sul hub

I plugin di RaspiMIDIHub (Velocity Equalizer, Chord Generator, Hold, MIDI Delay ...) si mettono in fila nella matrice
del hub, l'OUT di uno nell'IN del successivo, dopo la catena dell'FM-1. La ricetta è nel manuale (`docs/SAGGA-SEQ.md`,
"A chain on the hub too"): nella catena solo le note della traccia, i CC e il clock diretti al synth. I plugin nascono
con dei CC legati (MIDI Delay 74 / 75 / 76, Note Transpose 74, Scale Remapper 74): un CC legato non passa al synth.

## I progetti

Il formato resta `SGQB`: la catena sta nel blocco di estensione del progetto. Un progetto della 0.18 o di prima si
apre con il suo effetto come catena. Un progetto della 0.19 aperto da una 0.18 suona un effetto solo, il primo della
lista di K1 (HARM, OCTAVE, ECHO, VEL CURVE).

**Il Pi cambia** (l'editor e il convertitore dei progetti sanno della catena): `sagga-hub-0.19.zip`, vedi
`docs/SAGGA-SEQ-0.19-INSTALL.md`.

## Sotto il cofano

* `sagga_seq_core.c`: `sq_mfxc_t` in `sq_ext_t` (16 tracce, 13 byte l'una), `sq_mfx_mirror` (il `mfx` della traccia
  è il primo della catena), `sq_mfx_from_track` (un'immagine 0.18: il suo effetto come catena).
* `dinghy.c`: `mfx_sel` (l'effetto mostrato), `mfx_choose` / `mfx_go` (entra o esce), `mfx_extras` (HARM, poi ECHO
  della nota e della voce).
* Test: il core (la catena, un'immagine 0.18, sanitize), il simulatore (`t019_mfx_chain`: l'ordine, quello che si
  sente, un riavvio, uno snapshot, il tablet, il grid), l'editor (la catena in una patch).
