# SAGGA SEQ 0.12 - il disegno (prima del codice)

Le richieste: le note lunghe e il legato visibili (schermo, LED, grid); le idee di Skiff; studio e VIAGGIO sulla
stessa traccia, live; le pagine distribuite meglio; scegliere con i tasti e non solo con le manopole; il BREAK (gli
slice di un break di batteria); i controller del RaspiMIDIHub; altro che vale la pena.

## 1. Le pagine: il tasto dice di cosa si parla, le pagine vanno dal comune al raro

| tasto tenuto | pagine (OCT- / OCT+) | prima |
|---|---|---|
| HOME (la traccia) | 1 TRACK, 2 PLAY, 3 KEY, 4 MODE, 5 LOOPS, 6 MIDI FX, 7 TIMING | 8 (la 8 era VIAGGIO) |
| GLO (il live) | 1 LIVE (MORPH, MORPH TO, TRANSPOSE, QUANTISE), 2 TRACK LIVE (PATTERN, LENGTH, SCALE, MUTE QUEUE), 3 VIAGGIO (ENERGY, PHRASE, GENRE, KEY) | 1 (+SEL) |
| SEQ (il ritmo, i generatori) | 1 EUCLID, 2 ALGORITHM, 3 EVOLVE, 4 EXPO, 5 EXPO 2, 6 TOOLS, 7 BREAK | 8 (4 e 8 erano l'armonia) |
| ARP (le note, gli accordi, l'armonia) | 1 ARP, 2 CHORD, 3 HARMONY, 4 HARMONY 2 (FOLLOW, GENRE, MOOD, RHYTHM), 5 USER PROG, 6 USER PROG 2 (MOOD, LENGTHS, LENGTH, PUSH) | 2 |
| EDIT (lo step) | 1 GATE, CONDITION, NUDGE, RAMP; 2 NOTES (le quattro note dello step) | 1 |
| ENV (le lane) | 6, una lane a pagina | 6 |
| LFO | 3 | 3 |
| FX | 1 MACROS, 2 THROWS (gli stessi quattro, ma tornano a 0 da soli in una battuta) | 1 |
| SAVE | 1, 2 come prima, 3 SYSTEM (USB PORTS, BUTTON LIGHTS) | 2 (+ la pagina USB su HOME + SEL) |
| SEL, niente | 1 | 1 |

Cosa si sposta: GLO + OCT ora gira le pagine di GLO; l'ottava live della traccia e' **GLO + SEL + OCT- / OCT+**. La
pagina USB (era HOME + SEL tenuti) e' SAVE 3; la riconnessione: **SEL + K1** su SAVE 3. **SEL + K1..K4** sulle
vecchie pagine SEQ 4 e SEQ 8 non servono piu': sono pagine vere (ARP 4, ARP 6). I quattro gesti SEQ + SEL + tasto
diventano **tenere il tasto**: UNDO tenuto = REDO, COOK tenuto = COOK a caso, KIT tenuto = BAND, DICE SEQ tenuto =
DICE PROG (nel grid restano con SHIFT).

## 2. Scegliere con i tasti: PICK

**Tasto del gruppo + SEL + un tasto della tastiera = il valore di una manopola della pagina mostrata.** Quale
manopola: quella **a fuoco**, cioe' l'ultima girata su quella pagina (ricordata per pagina; all'inizio K1); lo
schermo la segna con `>` davanti all'etichetta. **Nero 11** (con gruppo + SEL) passa il fuoco alla manopola dopo.

* i bianchi 1-16 sono i valori 1-16 della lista, i neri 1-10 i valori 17-26;
* una lunghezza (1-64 step: LENGTH, HITS, CELLS, PULSES): i bianchi sono 4, 8, 12 .. 64, i neri 2, 6, 10 .. 38;
* una fondamentale (ROOT, la KEY di VIAGGIO): la tastiera e' cromatica, da F3 (F) a G5;
* un valore con segno in semitoni o passi (TRANSPOSE, SHIFT, HARM): F4 = 0, cromatico (F3 = -12, G5 = +14);
* le note dello step (EDIT 2): la tastiera suona la nota, con l'ottava di SEL + OCT;
* una manopola continua (velocity, un valore CC, una percentuale fine) non si sceglie con i tasti: lo schermo dice `-`.

Quando un gruppo e' tenuto e non succede nulla per mezzo secondo, lo schermo mostra **la mappa dei tasti** di
quel gruppo (bianchi, neri, SEL + tasti: il fuoco) al posto delle righe di messaggio.

## 3. Le note lunghe e il legato

* **Schermo**: una nota di N step e' un blocco continuo: la cella dello step pieno, le celle coperte e gli spazi fra
  loro riempiti in un verde piu' scuro; 1.5 step: mezza cella in piu'. TIE: il blocco si salda alla cella dopo (lo
  spazio fra le due e' pieno). Uno step acceso sotto una nota lunga resta acceso sopra la coda.
* **LED della tastiera**: lo step pieno acceso, i tasti coperti in **glow** (il livello basso dei LED, prima mai usato
  da SAGGA); sotto EDIT / ENV uguale, con il cursore che lampeggia.
* **Grid**: le celle coperte con il ruolo nuovo **16 TAIL** (verde scuro), il TIE con **17 TIE**; il bridge ha i due
  colori nuovi (va rimesso sul Pi).

## 4. Studio e VIAGGIO: due strade, una traccia

* **SEL + GLO (tocco)**: il pannello passa fra le tastiere di VIAGGIO e dello studio (gli step) **senza fermare il
  viaggio**: le frasi, la coda e l'energia continuano. La prima volta accende il viaggio.
* **SEL + GLO tenuto (0.6 s)**: il viaggio si spegne (la coda svuotata, l'energia neutra).
* Una traccia scritta in studio mentre il viaggio va entra nello stato giusto da sola (IN se suona, OUT se e' muta,
  EMPTY se la svuoti): THIN, SWELL, l'energia, le proposte la vedono. Una traccia fatta in VIAGGIO (una proposta
  entrata, un LOOP) e' un pattern normale: in studio si edita come le altre, mentre il viaggio va.
* In VIAGGIO il tasto della traccia selezionata suona i suoi step come prima; per editare: SEL + GLO, oppure EDIT /
  ENV + tasti (gia' cosi').

## 5. BREAK: gli slice di un break

Un campionatore (M8, Digitakt, Simpler ...) ha un break tagliato in 16 slice su 16 note consecutive. Una traccia in
modo **BREAK** (HOME 4 K1: FREE / IN KEY / DRUM / TAPE / BREAK) manda quelle note: ogni step e' uno **slice**
(1-16, il numero nella cella NOTE), la nota = la nota PEN della traccia + slice - 1; gate = quanto dura, ratchet =
roll dello slice, nudge, chance, condizioni come sempre; la lane BEND = il pitch dello slice.

* **SEQ 7 BREAK**: K1 **CHOP** (la libreria dei riordini: STRAIGHT 1..16, TWO-STEP, AMEN ROLL, HALF, DOUBLE, BACKWARDS,
  SNARE RUSH, GHOST, LOW (solo colpi bassi), HIGH, SHUFFLE 1-4 ...), K2 **ROLL** (quanti step hanno un roll, 0-8), K3
  **SWAP** (la quantita' di slice spostati dal dado, 0-100 %), K4 **SLICES** (8, 16, 32: quanti ne ha il break).
  Il dado (SEQ + nero 1 su una traccia BREAK) rimescola tenendo la spina dorsale: cassa sul battere (slice 1 e 9),
  rullante su 2 e 4 (slice 5 e 13), gli altri a caso; HEAT dice quanto.
* **ARP tenuto + bianchi 1-16**: gli slice suonano dal vivo (e con REC si scrivono); su una traccia qualunque ARP +
  tasti = la tastiera suona la traccia (note, batteria) senza registrare. **ARP + neri** su una traccia BREAK: 1 ROLL
  (lo slice tenuto in roll), 2 HALF, 3 DOUBLE, 4 BACKWARDS, 5 DICE, 6 RESET (1..16), 7 STUTTER (lo step che suona
  ripetuto finche' tieni).
* Grid: nella vista STEP di una traccia BREAK la riga 8 sono i 16 slice.
* I generi JUNGLE, DRUM+BASS, FOOTWORK, HARDCORE hanno chop propri nella libreria; COOK su una traccia BREAK cammina
  fra i chop del genere.

## 6. Da Skiff

* **THROWS** (FX 2): i quattro macro che tornano a 0 da soli, in una battuta, da quando li lasci.
* **TAKE** (REC tenuto 0.6 s): quello che hai suonato sulla tastiera nell'ultimo giro della traccia, anche senza REC,
  finisce nella traccia (la memoria delle ultime 4 battute di tasti c'e' sempre).
* **La mappa dei tasti sullo schermo** quando tieni un gruppo (punto 2).
* **Il legato e le note lunghe disegnati come barre continue** (punto 3).

## 7. I controller del RaspiMIDIHub (pagine web, gratis)

Comandi nuovi sul canale 13 (CC 33 in su): per traccia il pattern (33-48, il valore e' il pattern), la lunghezza
(49-64), BREAK (65 ROLL, 66 HALF, 67 DOUBLE, 68 BACKWARDS, 69 DICE, 70 RESET, 71 STUTTER, 72 CHOP, 73 SWAP %), le
note sul canale 13 = gli slice / i tasti della traccia selezionata; LFO: 80-95 on/off, 96 SHAPE, 97 RATE, 98
DEPTH, 99 DEST del LFO scelto (100); le lane: 101-106 la base delle lane 1-6 della traccia selezionata; 107 TAKE;
108-111 THROWS.

* **SAGGA Motori**: 16 tracce: mute, solo, pattern 1-8, lunghezza, retrig, kill, la traccia selezionata.
* **SAGGA Break**: 16 pad slice, ROLL HALF DOUBLE BACK DICE RESET STUTTER, CHOP e SWAP.
* **SAGGA Mod**: 16 LFO on/off, il LFO scelto (shape, rate, depth, dest), le sei lane della traccia (base), i throws.
* SAGGA Remote: + TAKE.

## 8. Com'è andata (dopo il codice)

Quasi tutto come sopra. Le differenze, perché il codice le ha chieste:

* **EDIT** non ha una pagina 2: le quattro note dello step sono **EDIT + SEL + K1..K4** (e SEL + tasto le scrive come
  prima); EDIT + SEL + tasto è il PICK della pagina (il gate, la condizione). Lo stesso per **FX**: i THROWS sono FX + SEL
  + manopole, non una pagina 2 (FX + SEL + neri restano i loop sulla traccia).
* **ARP + neri** su una traccia BREAK: 1 ROLL, 2 ROLL 1/32, 3 HALF, 4 DOUBLE, 5 BACKWARDS, 6 DICE, 7 RESET, 8 / 9 il chop
  dopo / prima (lo STUTTER del disegno è il ROLL: lo step che suona, o l'ultimo slice suonato a mano, ripetuto sul tempo
  degli step, con lo swing).
* I **chop sono sedici**, uno per tasto bianco (SHUFFLE B è uscito): così **ARP + bianco N = chop N dal vivo** (un
  tocco resta, tenuto suona finché tieni e poi torna il pattern di prima); gli slice si suonano con REC, dai pad del Pi
  e dal grid. I **chop dei generi** ci sono: ogni genere ha la sua lista (`BRK_GENRE` in `sagga_seq_core.c`) e COOK la
  percorre; COOK tenuto ne pesca uno a caso.
* La **riconnessione USB** è SEL + K1 due volte su SAVE 3 (HOME + SEL + OCT+ non esiste più).
* La **tastiera di PERF** è anche **GLO tenuto + tasti**, in ogni modo: così dallo studio o da VIAGGIO si muta al volo
  senza passare da PERF.
* Il **canale 13**: i 16 slice come pad sono **CC 76-91** (il hub manda solo CC dalle celle), un LFO alla volta con le
  manopole (92 quale, 93-97 shape, rate, depth, dest, on/off) e **i sedici interruttori come note 100-115** (il plugin
  SAGGA Mod le manda da solo: `send_note_on` / `send_note_off` di PluginBase, dato che i CC liberi del canale erano
  cinque); le note 36-51 fanno lo stesso dei pad. La mappa completa è in `../SAGGA-SEQ.md`.
* Le lunghezze dai tasti: i bianchi 4, 8 .. 64, i **neri 3 5 6 7 9 10 11 13 14 15** (le polimetrie, non 2, 6 .. 38).
* Le percentuali dai tasti: bianchi 1-10 = 10..100 %, neri = 5, 15 .. 95 %.
* I quattro gesti SEQ + SEL + tasto sono **tasti tenuti 0,6 s**; il tocco agisce quando lasci il tasto.
* **EDIT + SEL + tasto** imposta la nota dello step a fuoco (NOTE 1-4, quello che lo schermo mostra con SEL tenuto), non il
  gate: gate e condizione restano alle manopole.
* **Le finestre** (chieste dopo il primo giro): un tocco su HOME, SEQ, EDIT, ENV, LFO, ARP o FX tiene il tasto "premuto"
  finché non lo tocchi di nuovo o apri un'altra finestra: manopole, schermo, tasti, OCT per le pagine, SEL + tasto per
  il PICK, tutto come tenuto; un tasto tenuto davvero vince. GLO era già così (PERF); in PERF OCT sfoglia le pagine di
  GLO e SEL + OCT fa MUTE / SOLO. SAVE non ha finestra (il tocco salva). I due tocchi che c'erano sono andati sotto SEL
  (SEL + ARP l'arpeggio, SEL + FX il loop a due step). Nel codice è una maschera "tenuto effettivo" (`eff_held`) al posto
  di quella fisica dove il tasto decide il livello (tasti, manopole, OCT, schermo, LED, PICK, mappe), mentre le combo
  fra pulsanti (HOME + PLAY, SEQ + SAVE ...) restano fisiche.
* Il **PICK dal grid**: la vista PICK (CC di nuovo) con le quattro manopole della finestra aperta, una per riga, i pad
  come i tasti bianchi (righe 1-4) e neri (5-8) del PICK.
