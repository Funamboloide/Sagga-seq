# SAGGA SEQ 0.31 - Note di rilascio

**I tasti che non facevano niente adesso lavorano.** Dalla 0.28 le tracce sono dodici, e tutto quello che c'era per le
tracce 13-16 - sul pannello, sul grid, sul remoto - era rimasto spento. Adesso quei tasti sono **i gruppi**, e nella
banca 9-12 i tasti e le righe che erano delle tracce 13-16 fanno le cose che servono lì: i **mute** delle tracce 9-12,
le **scene** e le **snapshot** sul grid, la **forza degli step**, la **rotazione** dell'euclideo.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.31.fwsc` |
| il Pi: l'editor, le pagine SAGGA, il bridge del grid, il banco | `sagga-hub-0.31.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due, insieme**. Si possono saltare le versioni: dalla 0.27 alla 0.31 in un colpo va bene
(qui sotto, in fondo, cosa hanno portato la 0.28, la 0.29 e la 0.30).

## 1. I gruppi

Dove una fila di tasti o di pad è le dodici tracce (il primo è la traccia 1), **i quattro dopo sono i gruppi**:

| tasto / pad | il gruppo | cosa c'è dentro | sul grid |
| --- | --- | --- | --- |
| 13 | **DRUMS**, la batteria | le tracce in modo DRUM (come lo SCOPE DRUMS) | arancio |
| 14 | **BASS**, i bassi | le altre con il ruolo BASS, SUB, RUMBLE o LOG DRUM | blu |
| 15 | **MELODIC**, le melodiche | tutte le altre | ciano |
| 16 | **ALL**, tutte | ogni traccia | bianco |

Un tocco fa a tutto il gruppo quello che la fila fa a una traccia. Il gruppo è quello di adesso: una traccia che
diventa DRUM è con la batteria dal passo dopo. Un gruppo senza tracce lo dice (`NO DRUM TRACK`, `NO BASS TRACK (A BASS
OR SUB ROLE)`, `NO MELODIC TRACK`) e sul grid il suo pad è spento.

## 2. Sul pannello dell'FM-1

* **PERF, i bianchi 13-16** (GLO tenuto, PERF acceso, la pagina delle MOSSE): un tocco e il gruppo **tace** se
  qualcosa di suo suona, se no **torna** (`DRUMS MUTED`, `DRUMS PLAY`; con MUTE QUEUE alla battuta, come i mute). Il
  **bianco 16** riaccende tutto: niente mute, niente solo (`ALL TRACKS AUDIBLE`). **Con SEL** (o con i bianchi sul solo,
  SEL + OCT+) è il **solo del gruppo**: acceso per tutto il gruppo, o spento se l'aveva già tutto (`SOLO: BASS`, `SOLO
  OFF: BASS`); SEL + bianco 16 toglie ogni solo (`NO SOLO`). Le luci: acceso mentre qualcosa del gruppo suona (il 16:
  mentre suona tutto), lampeggia mentre un mute aspetta.
* **La banca 9-12** (il nero 9): **i neri 5-8 sono i mute delle tracce 9-12** (`T9 MUTED`, `T9 PLAYS`; acceso: muta;
  lampeggia: aspetta il QUANTISE). I neri 1-4 scelgono le tracce 9-12, come prima.
* **HOME + bianco 13-16: la pagina di step** 1-16, 17-32, 33-48, 49-64 (`STEPS 17-32`; il cursore sul primo step della
  pagina; acceso: la pagina che vedi). È quello che OCT- e OCT+ fanno una pagina alla volta.
* **Un LFO su un gruppo**: sulla pagina 2 degli LFO, **K2** (TRACK) dopo T12 va su **DRUMS, BASS, MELODIC, ALL** (per
  tutte le destinazioni tranne CC, dove K2 è il canale). L'LFO muove quel parametro di ogni traccia del gruppo. La cella
  dice il nome del gruppo; con PICK (LFO + SEL) sono i bianchi 13-16.

## 3. Il remoto (canale 14) e la pagina SAGGA Mutes

I CC delle tracce 13-16 sono i gruppi:

* **CC 60-63**: il mute di un gruppo (il 63: tutto acceso, ALL ON).
* **CC 76-79**: il **KILL** di un gruppo finché è premuto (il 79: **tutte tranne la traccia del tablet**, quella che
  sceglie TRACK su SAGGA Live o Motori).
* **CC 102-105**: il **RETRIG** di un gruppo (ogni sua traccia riparte dal primo step al suo step dopo; da fermo:
  `PLAY FIRST`).

Sulla pagina **SAGGA Mutes** del tablet, sotto i dodici MUTE, KILL e RETRIG, c'è una riga con i quattro gruppi: MUTE
DRUMS, MUTE BASS, MUTE MELODIC, ALL ON; KILL DRUMS, KILL BASS, KILL MELODIC, KILL ALL BUT T; RETRIG DRUMS, RETRIG BASS,
RETRIG MELODIC, RETRIG ALL.

## 4. Sul grid

* **I bottoni traccia 12-15 nella banca 9-12** (quelli delle tracce 13-16): i **mute delle tracce 9-12** (con SHIFT: il
  solo). Verde suona, rosso muto, lampeggia aspetta, giallo solo.
* **PERF nella banca 9-12, righe 5-8**: la riga 5 sono le scene 1-16 e la riga 6 le scene 17-32 (un tocco la porta, al
  QUANTISE; SHIFT + tocco la salva); la riga 7 le 16 snapshot (un tocco la richiama, SHIFT + tocco la salva); la riga 8
  i mute delle dodici tracce (SHIFT: il solo) e, sui pad 13-16, i gruppi.
* **DRUM nella banca 9-12, righe 5-8**: **la forza degli step** delle tracce 9-12, sotto le loro righe. Un tocco:
  NORMALE, ACCENTO, GHOST, NORMALE (velocity 100, 124, 45: le tre della libreria; `T9 STEP 5: ACCENT`); uno step
  spento si accende, ACCENTO. SHIFT + pad: quella traccia.
* **EUCLID nella banca 9-12, righe 5-8**: sotto le tracce 9-12, il pad 1 è la **famiglia** (EUCLID ciano, TRESILLO
  arancio, NUMERIC viola: come SEQ 1 K3) e i pad 2-16 la **rotazione** 0-14, senza SHIFT.
* **I pad 13-16 dei gruppi** dove una riga è le dodici tracce:
  * **FX** riga 4: un gruppo dentro o fuori da quello che LOOP e REPEAT prendono (`LOOP / REPEAT WITHOUT DRUMS`; il 16:
    tutte); riga 6: il **KILL** di un gruppo finché lo tieni, con SHIFT resta (`KILL BASS (STAYS)`; il 16: tutte tranne
    la traccia scelta).
  * **MOSSE** riga 2: i **dadi** per ogni traccia del gruppo (`THE DICE: MELODIC, 4 TRACKS`); riga 3: il gruppo **IN /
    OUT** al confine (fuori se qualcosa è dentro, se no dentro; il 16: tutte quelle che hanno note).
  * **FOLLOW** righe 5-8: il valore di quella manopola a tutto il gruppo (`MELODIC: LENGTH AS T1`).
  * **BEAT** riga 5, con lo SCOPE CUSTOM: un gruppo dentro o fuori dallo scope (`SCOPE + DRUMS`).
  * **LFO** riga 7: l'LFO su un gruppo (`LFO ON DRUMS`; bianco quello scelto).
* **PROJ riga 4, pad 13-16: i canali MIDI**. Il 13: ogni traccia sul canale del suo numero (T1 sul 1 ... T12 sul 12);
  il 14: le tracce DRUM sul canale 10 (il General MIDI); il 15 e il 16: il canale della traccia scelta - e + (come la
  riga 8 di TRACK 3). Una traccia che cambia canale chiude prima le sue note.
* **BEAT, pagina 2 dei generi** (riga 1): il **pad 11** un genere **a caso** (un altro), il **pad 12 la SOURCE**:
  LIBRARY, THEORY (ciano), FREE (viola), come SEQ 8 K1.

## 5. Due errori corretti

L'ho visto guardando tutti i pad del grid:

* **BEAT, riga 3**: dalla 0.29 (otto progressioni a genere) i pad 7 e 8 facevano le progressioni 7 e 8, e così erano
  spariti **HARMONY acceso / spento** (pad 7) e **le battute di un accordo** (pad 8). Adesso sono tornati; i pad 1-6
  sono le progressioni 1-6 (la 7 e la 8 sono nella vista MOSSE e su SEQ 4 K2, come le note della 0.29 dicevano).
* **CC, riga 5**: dalla 0.28 i pad delle lane 7 e 8 erano disegnati spenti, come quando le lane erano sei. Funzionavano,
  ma non si vedevano. Adesso sono accesi come gli altri.

## 6. I progetti

* **I progetti di prima si aprono come erano.**
* Nel progetto non cambia niente, tranne una cosa: un LFO può avere per traccia un gruppo (16-19).
* **Se torni alla 0.30**, apre i progetti della 0.31; un LFO messo su un gruppo lo trova **spento, sulla traccia 1**
  (un LFO MOD ONLY resta acceso).
* **Sul Pi** l'editor dei progetti, negli LFO, ha "traccia o gruppo": le dodici tracce e i quattro gruppi.

## 7. Se arrivi dalla 0.27

Le note intere sono in `docs/storia/` (`RELEASE-NOTES-0.28.md`, `0.29.md`, `0.30.md`). In breve:

* **0.28**: le tracce sono **12**; un passo tiene **6 note**; le lane CC sono **8**.
* **0.29**: i generi sono **22**, con il **BALANI** e il suo **BALAFON**; **8 progressioni** a genere; **ROLL** e
  **ACCENT**, **5 scale**, **3 groove**, **4 forme d'accordo**.
* **0.30**: **32 scene**, **16 snapshot**, la song di **128 entrate**, le TAPE di **3072 eventi**, UNDO a **32 righe**;
  VIAGGIO si chiama MOSSE dappertutto; l'accensione rimette i mute e la scena.
* Il manuale, "SAGGA SEQ 0.31 — Il manuale", ha le cose nuove: i gruppi nella lezione 10 e nella Parte terza.

## 8. L'esploratore

L'esploratore prova ogni gesto in ogni situazione. Ha una situazione nuova, così le cose della 0.31 sono anche nel
piano per l'FM-1 vero (`fm1_piano.json`) e nel banco:

* **0.31**: una band TECHNO, la traccia 10 scelta (la banca 9-12), la T9 muta dal bottone 12 del grid, un LFO VEL sul
  gruppo BASS, LOOP e REPEAT senza la batteria, il tablet e il grid, in play. Prima di cominciare la sonda controlla la
  traccia, il mute, l'LFO e il LOOP.
* Nei gesti: il bottone traccia 6 del grid (nella banca 9-12 il mute di T10), con e senza SHIFT; SHIFT + i pad delle
  righe 5-8 di DRUM e della riga 6 di FX.
* PROJ riga 4, pad 13-16 può cambiare i canali delle tracce: la regola CANALE lo sa.

PROVE_QUI

## Installare

Come sempre: prima il Pi (`sagga-hub-0.31.zip`), poi l'FM-1 (`sagga-0.31.fwsc`). I passi sono in `INSTALLA.md`. Sullo
schermo, dopo l'aggiornamento: `SAGGA SEQ 0.31` per tre secondi.

## Cosa provare per primo

1. **La batteria che tace**: una band (SEQ + nero 7 tenuto), PLAY, tocca GLO (PERF), poi il **bianco 13**: la batteria
   tace; ancora: torna. **SEL + bianco 13**: restano solo i tamburi; **SEL + bianco 16**: tutto di nuovo.
2. **I mute di 9-12**: il nero 9 (la banca 9-12), poi i **neri 5-8**: le tracce 9-12 tacciono e tornano.
3. **Un LFO sui bassi**: tieni LFO, OCT+ fino alla pagina 2, K1 su VEL, **K2 oltre T12 fino a BASS**; pagina 3, K1 ON.
   Il basso e il rumble respirano insieme.
