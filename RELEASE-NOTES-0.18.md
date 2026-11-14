# SAGGA SEQ 0.18 - Note di rilascio

**Tre cervelli, un set solo.** L'FM-1, il tablet (le pagine del RaspiMIDIHub) e il grid adesso lavorano insieme ma
ognuno per conto suo: con una mano sull'FM-1, con l'altra sul tablet, e il grid che fa altro ancora, senza restare
legati a una pagina dell'FM-1.

0. **il tablet ha una traccia sua**: quello che mandano le pagine del Pi agisce sulla traccia del tablet (TRACK), non su
   quella dell'FM-1; lo schermo dell'FM-1 lo dice (`TAB T5: LFO ON`);
1. **SAGGA Live**, una pagina nuova per il tablet (canale 12): tutto della traccia del tablet a portata di mano -
   pattern, lunghezza, ottava, swing, groove, ARP, accordo, MIDI FX, algoritmo, euclid, COOK, BEAT, proposte, dadi,
   UNDO, e i 16 mute;
2. **l'FM-1 rimanda i valori al tablet**: giri una manopola sull'FM-1 e la manopola sul tablet si muove; un mute fatto
   sul pannello si accende su SAGGA Live;
3. **il grid segue l'FM-1** (FOLLOW, era PICK): la vista va con la pagina aperta sull'FM-1, e le righe 5-8 mostrano la
   stessa manopola su tutte le 16 tracce (un tocco: quella traccia prende il valore);
4. **ARP RATE 1/2 e 1/4**: una nota ogni 2 o 4 step, per stendere un accordo su 16 step e più.

Il formato resta `SGQB`. **Il Pi cambia**: c'è una pagina nuova (SAGGA Live) e SAGGA Mod è aggiornata; nella matrice del
hub va aggiunto un collegamento (la porta 2 dell'FM-1 verso le pagine SAGGA). Vedi `docs/SAGGA-SEQ-0.18-INSTALL.md`.

## La traccia del tablet

Fino alla 0.17 il tablet agiva sulla traccia selezionata sull'FM-1: se cambiavi traccia sul pannello, cambiava anche
quella del tablet. Adesso il tablet ha **la sua traccia, il suo LFO e il suo cursore**:

* **TRACK** (canale 13 CC 112: su SAGGA Live, Motori e Mod) sceglie la traccia del tablet. L'FM-1 resta sulla sua.
* I pad di SAGGA Break e dei canali 13, le lane di SAGGA Mod, TAKE, MODE, il BREAK, l'LFO scelto su Mod: tutto sulla
  traccia del tablet.
* Lo schermo dell'FM-1 segna quello che arriva dal tablet: `TAB T5: LFO ON`, `TAB T3 MIDI FX ECHO READY: GO`. (Il GO del
  tablet è il SEQ + bianco 6 del pannello.)
* COOK, BEAT, DADI e UNDO dal tablet lavorano **solo sulla sua traccia**, qualunque sia lo SCOPE, e subito (senza il
  WHEN).

## SAGGA Live (canale 12)

Una pagina di 4 colonne per 13 righe:

| riga | | | | |
|---|---|---|---|---|
| 1 | TRACK | MODE | MUTE | SOLO |
| 2 | PATTERN (al QUANTISE) | LENGTH (alla battuta) | OCTAVE | RETRIG |
| 3 | SWING | GROOVE | GROOVE AMT | FOLLOW |
| 4 | ARP | OCTAVES | RATE (1/4, 1/2, ROLL, 1-4) | RUN |
| 5 | CHORD (32 forme) | MIDI FX (READY) | FX AMOUNT | FX GO |
| 6 | ALGO (READY) | A | B | C |
| 7 | ALGO GO | PULSES | ROTATION | EUCLID (acceso / spento) |
| 8 | COOK | BEAT | PROPOSAL | QUEUE (la proposta in coda) |
| 9 | DICE | KEEP | BACK | UNDO |
| 10-13 | MUTE 1-16 | | | |

MIDI FX e ALGO funzionano come sull'FM-1: la manopola mette pronto (READY) l'effetto o l'algoritmo, con A B C o FX
AMOUNT lo imposti, GO lo fa partire (di nuovo GO: si ferma). A, B, C vanno da 0 a 127 su tutto il campo
dell'algoritmo (TURING: mutazione, lunghezza, mosse; CELL: regola, celle, ogni quanto; ACCENT: quale, quanto, inizio;
DENSITY: densità, ghost); lo schermo dell'FM-1 dice il valore vero (`TAB T5: TURING MUTATION 40`).

Il PANIC del hub non tocca SAGGA Live (i suoi interruttori sono i mute dell'FM-1, non note da spegnere).

La mappa completa è in `docs/SAGGA-SEQ.md`, "Channel 12".

## I valori tornano al tablet

Con **USB PORTS 2**, appena il tablet ha mandato qualcosa, l'FM-1 manda sulla sua porta 2 i valori che le pagine
mostrano, quando cambiano (pochi messaggi per millisecondo, il clock e le note hanno sempre la precedenza) e piano piano
tutti di nuovo (uno ogni 40 ms: un hub riavviato o una pagina riaperta si rimettono in pari in pochi secondi).

* **SAGGA Live**: tutto (la traccia del tablet) e i 16 mute (quelli in coda con MUTE QUEUE compresi).
* **SAGGA Motori**: pattern (quello in coda, se c'è) e lunghezza (quella che aspetta la battuta) delle 16 tracce,
  TRACK, MODE.
* **SAGGA Mod**: l'LFO del tablet (quale, forma, rate, profondità, destinazione, acceso), le 6 lane della sua traccia,
  energia, genere, tonalità, progressione, armonia, e gli interruttori L1-L16.
* **SAGGA Remote**: MORPH, MORPH TO, EVOLVE AMT, HEAT, QUANTISE, i macro (anche mentre un THROW torna a 0), TRANSPOSE.

Un valore che stai muovendo sul tablet non viene toccato per 0,4 secondi (niente tira e molla con il dito); se l'FM-1
non l'ha preso così (una LENGTH oltre il pattern, un'OCTAVE su una traccia drum) dopo torna quello giusto.

Nella matrice del hub: **la porta 2 dell'FM-1 ("Felucca MIDI 2") verso l'IN di ogni pagina SAGGA**, oltre al loro OUT
verso l'FM-1 come prima. Con una porta USB sola non torna niente (la porta 1 va ai synth).

## Il grid segue l'FM-1 (FOLLOW)

SHIFT + STEP due volte (CC, poi **FOLLOW**; nella 0.12-0.17 si chiamava PICK). Da lì il grid **va con la pagina
dell'FM-1**, un quarto di secondo dopo che cambia:

| l'FM-1 | il grid |
|---|---|
| gli step (niente tenuto, nessuna finestra) | STEP |
| PERF | PERF; sulla pagina 3 (le MOSSE): VIAGGIO |
| LFO | LFO |
| FX | FX |
| ENV | CC (le lane) |
| EDIT | STEP |
| HOME, SEQ, ARP | FOLLOW: le quattro manopole della pagina |
| SAVE tenuto | resta com'è |

Sulla vista FOLLOW:

* **righe 1-4**: le quattro manopole della pagina, i loro valori sui pad (come PICK);
* **righe 5-8, novità**: se la manopola è di una traccia, **la stessa manopola su tutte le 16 tracce**: la traccia
  dell'FM-1 bianca, le tracce con il suo stesso valore accese, le altre spente. **Un tocco: quella traccia prende il
  valore** (`T3 LENGTH AS T1`; le lunghezze aspettano la battuta, i pattern il QUANTISE, come con la manopola).
  **SHIFT + un tocco: l'FM-1 va su quella traccia.** Se la manopola non è di una traccia (la tonalità, l'energia, il
  morph, gli LFO) lì restano i valori dei tasti neri come in PICK. Il canale MIDI e il PROGRAM di una scena non si
  copiano (sono dei synth).

Una vista scelta a mano con un tasto ferma FOLLOW; SHIFT + STEP due volte lo riaccende. Mentre segue, **SHIFT è
azzurro**.

## ARP RATE 1/2 e 1/4

ARP 1 K3 ha due posti nuovi **a sinistra di ROLL**: 1/2 (una nota ogni 2 step) e 1/4 (una nota ogni 4 step). L'ordine
della manopola: **1/4, 1/2, ROLL, 1, 2, 3, 4** (a sinistra più lento, a destra più veloce, come prima). Un accordo
tenuto per 16 step con RATE 1/4 fa quattro note, una per quarto; con RUN HOLD l'arpeggio va avanti fino all'accordo
dopo. Anche dal grid (PICK / FOLLOW), dal tablet (SAGGA Live, RATE) e dall'editor del Pi.

## Altro

* SAGGA Mod: GENRE arriva al 25° genere (MERENGUE).
* La documentazione: il Program Change per scena è su HOME pagina 5 K4 (non 4).

## Sotto il cofano

* `sagga_tablet.c` (nuovo): il canale 12 (`live12_cc`), i valori che tornano al hub (`fb_value`, `tab_fb_service`: una
  tabella di 116 voci, mandate quando cambiano, con una finestra di 0,4 s per quelle che il tablet ha appena mosso).
* `dinghy.c`: il fuoco del tablet (`tab_enter` / `tab_leave`: traccia, pagina, cursore, LFO, registrazione a step);
  `tab_takes` / `tab_cmd` per i canali 12-14; lo schermo `TAB ...` (e GO al posto di SEQ + WHITE 6); `SQ_ARP_PER_STEP` /
  `SQ_ARP_EVERY` (i RATE lenti: `arp_wait`).
* `sagga_grid.c`: la vista FOLLOW (`gr_follow_tick`, `gr_follow_view`, `gr_follow_copy`, la tabella `GR_PT` delle
  manopole che sono di una traccia).
* Il Pi: `tools/raspimidihub/sagga_live` (nuovo), `sagga_mod` (GENRE, gli interruttori L1-L16 seguono l'FM-1).
* Test: il simulatore (`t018_arp_slow`, `t018_tablet_track`, `t018_live_page`, `t018_live_sweep`, il test del grid
  FOLLOW), i plugin (con l'host vero del RaspiMIDIHub: i valori che tornano muovono le celle e non rimandano niente).
