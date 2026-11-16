# SAGGA SEQ 0.13 - Note di rilascio

La 0.13 è la lista delle otto cose "aggiungibili" della 0.12, tutte: l'LFO che cambia velocità mentre suona, il
sidechain fatto dalla cassa, il NOTE REPEAT sulle tracce di batteria, la tastiera esterna che traspone, i movimenti delle
macro registrati nel loop, lo SLIDE per step (l'808, la 303), le catene di pattern lunghe, e sul Pi il taglio di un break
in slice. Il formato resta **`SGQB`**: le impostazioni nuove stanno in un blocco in coda al progetto, scritto solo
quando qualcosa non è al suo valore di base. **La 0.12 apre un progetto della 0.13** (salta il blocco: niente CHAIN
LIST, RATE SEQ, MOTION) e la 0.13 apre i progetti della 0.12 così come sono. Gli snapshot non portano le cose nuove.

## LFO: RATE SEQ, le terzine, TRIG

* **LFO pagina 4, RATE SEQ**: K1 **STEPS** (OFF, da 2 a 8 velocità), K2 **EVERY** (BEAT, 2 BEATS, BAR, 2 BARS: quanto dura
  ognuna), K3 **POSITION** (quale delle velocità imposta la manopola sotto), K4 la sua **RATE** (`(RATE)` fra parentesi:
  suona ancora quella dell'LFO). Ogni velocità fa partire il suo ciclo dove comincia il suo tempo: 1 BAR, 1/8, 1/4T,
  1/16 è il wobble che cambia passo sulla battuta. PICK anche qui (LFO + SEL + bianco 3: 3 velocità; bianco 1: OFF).
* **Le terzine**: dopo 1/32 la RATE continua con **1/4T, 1/8T, 1/16T, 1/32T** (pagina 1 K2, la RATE SEQ, SAGGA Mod).
  Il DICE LFO resta sulle sedici dritte.
* **TRIG** (pagina 3 K4): CLOCK come sempre, oppure **T1-T16**: ogni colpo di quella traccia fa ripartire il ciclo
  dell'LFO, che a fine ciclo resta fermo fino al colpo dopo. **DECAY + INVERT su un volume** (un LFO su CC 7 o 11 del
  canale di un pad) = il pad che si abbassa sotto la cassa: il "pompare" della house e della bass music, fatto dalla
  traccia della cassa (una traccia muta non lo fa partire). Prima del primo colpo l'LFO aspetta a fine ciclo.

## NOTE REPEAT sulle tracce DRUM

ARP tenuto (o la sua finestra), un bianco tenuto (il suo strumento) e **nero 1-4 tenuto**: lo strumento di nuovo ogni
**1/16, 1/32, 1/32T, 1/8** finché tieni, a tempo con gli step della traccia (con il suo swing). Con REC acceso le
ripetizioni si scrivono (1/32 e 1/32T come RATCHET 2 e 3 sullo step). In play, su una traccia di batteria, i neri 1-4 sono
accesi e quello tenuto lampeggia; la mappa di ARP lo dice (`W PLAY  B1-4 REPEAT`). Sulle tracce melodiche ARP + tasti
suonano come prima; sul BREAK i neri restano le sue mosse.

## La tastiera esterna e il MIDI IN: SAVE pagina 4 LIVE IN

* **K2 KEYBOARD**: OFF; **ALL**: ogni nota che arriva dal MIDI IN traspone la tonalità (il TRANSPOSE di GLO 1 K3) da -5 a
  +6, contato dalla tonalità com'era prima di ogni trasposizione (in DO: RE = +2, SI = -1, DO = di nuovo 0); **SPLIT C3**:
  le note sotto il C3 traspongono, da C3 in su sono note. Aspetta il momento del QUANTISE come la manopola (da fermo:
  subito). Le note che traspongono non suonano e non si registrano.
* **K3 KEYB CH**: ANY o 1-16, il canale su cui manda la tastiera (le note degli altri canali restano note).
* **K4 MIDI IN**: REC ONLY (come prima: le note che entrano suonano la traccia selezionata con REC acceso) o **ALWAYS**: la
  suonano sempre (un controller di pad: le sue batterie), REC o no; REC le registra comunque, TAKE se le ricorda sempre.

## MOTION: i movimenti delle macro nel loop

**SAVE 4 K1**: OFF, 1, 2 o 4 BATTUTE. Con **REC acceso**, quello che fai alle quattro macro (FX + K1-K4, un THROW che
torna indietro, i fader del remote) si scrive nel loop, un sedicesimo per cella, e poi suona da solo: il FILTER che si
apre sull'ultimo quarto di ogni battuta, l'INTENSITY che respira. Mentre giri una manopola, e per 0,3 s dopo, vince la
mano; senza REC non si scrive niente. **FX + OCT-** (MACROS 0) cancella anche la motion (`MACROS 0, THE MOTION WIPED`).
Lo schermo di FX e la riga 5 dicono MOTION / MOTION REC. Si salva con il progetto; OFF la tiene (torna a suonare
rimettendo le battute).

## SLIDE per step

**EDIT + nero 7**: come il TIE la nota tiene fino allo step dopo, e **la nota dopo scivola al suo posto**: l'interruttore
del portamento del canale (CC 65) va a 127 subito prima di lei e torna a 0 prima della prima nota dopo che non scivola
(e allo STOP, al PANIC). Il tempo dello scivolo lo decide il synth (la sua manopola di portamento / glide: un basso 808,
una 303, un mono in legato). TIE (nero 6) e SLIDE (nero 7) sono l'uno o l'altro; i neri 5-7 di EDIT sono accesi sullo
step che ha PLAIN, TIE, SLIDE; lo schermo dice SLIDE, la striscia e il grid lo mostrano come un TIE. Non sulle tracce
DRUM e BREAK (`SLIDE: A MELODIC TRACK'S STEP`).

## CHAIN LIST: le catene lunghe

**HOME 7 K2** ora è **OFF / P1+2 / LIST** (P1+2: la coppia della 0.10, K2 +1 come prima). **HOME 8 CHAIN LIST** (pagina
nuova): K1 **LENGTH** 1-8 voci, K2 **ENTRY** (quale voce impostano le manopole sotto), K3 il suo **PATTERN** 1-8, K4 quante
**TIMES** 1-8 suona. La traccia suona la lista, ogni pattern alla fine del loop di quello prima (`HOME 8/8  1>2X2 3`:
la lista, `>` la voce sotto le manopole, `*` quella che suona). **PLAY riparte dalla voce 1.** Un pattern scelto a mano
(PRESETS, una scena, il remote) suona come sempre al suo momento: se è nella lista la lista prosegue da lì, se non c'è la
lista si spegne (`T1 CHAIN LIST OFF: P5 IS NOT IN IT`). Anche il PICK (HOME + SEL + tasto) imposta le quattro manopole.

## Il Pi: BREAK IN SLICE

Nella pagina dell'hub (porta 8090) la sezione **BREAK IN SLICE**: un loop di batteria in WAV entra, uno zip esce - le
slice `01.wav` .. (8, 16 o 32, nel formato del file), il loop con un cue su ogni slice, un **.sfz** con le slice sulle
note dalla prima in su (C1 = 36 se non dici altro), una alla volta (sfizz sullo Zynthian, Sforzando: lo carichi così
com'è), e `LEGGIMI.txt` con il tempo trovato, le battute e cosa impostare sull'FM-1 (traccia BREAK, PEN = la prima nota,
SEQ 7 SLICES). Il Pi trova dove comincia il break, quante battute sono e il tempo (una potenza di due di battute fra 90 e
180 BPM, oppure BPM / battute che scrivi tu), taglia sulla griglia dei sedicesimi e sposta ogni taglio sul colpo vicino,
a un passaggio per lo zero. Da terminale: `python3 sagga_slicer.py amen.wav --slices 16`. Solo libreria standard di
Python: niente da installare sul Pi.

**SAGGA Mod**: la RATE ha le quattro terzine (venti velocità, come l'FM-1).

## Sotto il cofano

* Il blocco nuovo del progetto (`sq_ext_t`, 780 byte): i RATE SEQ e i TRIG dei sedici LFO, le CHAIN LIST delle sedici
  tracce, la MOTION (64 celle per macro), le impostazioni di SAVE 4. I test del core ne controllano i valori di base, il
  viaggio andata e ritorno, un blocco sconosciuto saltato, i valori fuori misura rimessi a posto.
* I pattern della CHAIN LIST cambiano alla fine del loop come la coppia della 0.10; il TRIG prende il colpo dove parte
  la nota (anche i ratchet, una traccia muta no).
* Test nuovi nel simulatore: 0.13 LFO (RATE SEQ, terzine, TRIG, PICK), NOTE REPEAT (le quattro velocità, REC, una traccia
  melodica), KEYBOARD e MIDI IN (ALL, SPLIT, il canale, in play al QUANTISE, REC ONLY / ALWAYS), MOTION (scritta, suonata,
  senza REC, cancellata, lo schermo), SLIDE (CC 65 prima della nota, il legato, lo STOP, TIE o SLIDE, la batteria), CHAIN
  LIST (la lista, a mano dentro e fuori, il salvataggio). `tests/sagga_slicer_tests.py`: break sintetici con i colpi dove
  li mettiamo noi, il tempo, l'inizio, i tagli sui colpi, lo zip, i formati, gli errori, il modulo della pagina.
* L'esploratore ha due situazioni nuove (CHAIN LIST + MOTION + KEYBOARD + SLIDE in play; RATE SEQ + TRIG) e conosce le
  pagine nuove (HOME 8, LFO 4, SAVE 4).

Il riferimento completo è `../SAGGA-SEQ.md` ("What is new in 0.13" e le tabelle); l'installazione
`SAGGA-SEQ-0.13-INSTALL.md`.
