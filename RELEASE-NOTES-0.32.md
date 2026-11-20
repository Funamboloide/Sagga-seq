# SAGGA SEQ 0.32 - Note di rilascio

**I tasti che non facevano niente da sempre adesso lavorano.** La 0.31 aveva dato un lavoro ai tasti liberati dalle
dodici tracce e dai 22 generi. Ne restavano altri, spenti già da prima: con EDIT, ENV, LFO o SAVE tenuti certi tasti
non facevano niente, e sul grid c'erano pad spenti in quasi ogni vista. Adesso **ogni tasto con un bottone tenuto e
ogni pad del grid fa qualcosa**, quello che serve lì.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.32.fwsc` |
| il Pi: l'editor, le pagine SAGGA, il bridge del grid, il banco | `sagga-hub-0.32.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due, insieme**. Si possono saltare le versioni: dalla 0.27 alla 0.32 in un colpo va bene
(qui sotto, in fondo, cosa hanno portato la 0.28, la 0.29, la 0.30 e la 0.31).

## 1. Sul pannello dell'FM-1

* **EDIT + neri 8-11**, sullo step del cursore:
  * **nero 8, la FORZA**: NORMALE (velocity 100) → ACCENTO (124) → GHOST (45) → NORMALE. Uno step spento si accende,
    ACCENTO (`STEP 2: ACCENT`). Acceso su un accento.
  * **neri 9 e 10: lo step un posto prima / dopo** nel loop. Si scambia con quello accanto (sul primo step del loop il
    9 gira fino all'ultimo), il cursore va con lui, UNDO lo rimette (`STEP 1 TO 16`).
  * **nero 11, via gli extra**: la probabilità torna 100, la condizione ALL, niente nudge, un solo ratchet, niente
    rampa. Le note, la velocity e il gate restano. Acceso finché lo step ha uno di quegli extra.
* **ENV + neri 1-8: la lane** della pagina (come OCT- e OCT+; acceso: la lane che vedi, debole: le lane con un CC).
  **Nero 9 RAMPA SU, nero 10 RAMPA GIÙ**: i lock della lane salgono da 0 a 127 (o scendono) lungo il loop del pattern.
  **Nero 11: svuota la lane** nel loop (`LANE 3 CLEARED`; se non c'è niente: `LANE 3: NO LOCK IN THE LOOP`). UNDO le
  rimette.
* **LFO + neri 1-6: la pagina** dell'LFO (come OCT- e OCT+). **Nero 7 COPIA** l'LFO scelto (con il suo RATE SEQ, il
  TRIG e l'ENV), **nero 8 INCOLLA** sull'LFO scelto (`LFO PASTED 2`; acceso: ce n'è uno copiato). **Nero 9: tutti gli
  LFO spenti - ancora: si riaccendono quelli che erano accesi**. **Nero 10: il prossimo LFO libero** (il prossimo
  spento: per prepararne uno nuovo). **Nero 11: l'LFO da capo**, due volte entro 3 secondi (come in un progetto nuovo;
  lampeggia quando ha chiesto).
* **SAVE + bianchi 11-15, le cose del Pi**: **11 EXPORT** (il progetto al Pi, come il pad 12 di PROJ), **12 il pattern
  della traccia** al Pi (come SEQ + SAVE), **13 la progressione** (come ARP + SAVE), **14 e 15: la scaletta del Pi**, il
  file prima / dopo quello caricato. La prima volta lo nomina (`NEXT, AGAIN TO LOAD: 2 TWO`, il tasto lampeggia), la
  seconda entro 3 secondi lo carica (se suona: allo STOP). Deboli mentre tieni SAVE.
* **La manopola MASTER ha un quarto lavoro: l'ENERGIA** (SAVE + K1, o sul grid PROJ riga 5 pad 4). Muove l'energia
  delle MOSSE da 0 a 100 (`ENERGY 50: THE WHOLE SET`), come GLO 3 K1: se suona ci arriva scivolando.
* **La mappa dei tasti** (un bottone tenuto mezzo secondo): EDIT, ENV e LFO dicono i neri nuovi sulla seconda riga
  (`B8 FORCE 9/10 MOVE 11 EXTRAS`); con SEL tenuto quella riga dice quello che fa il PICK, come prima. SAVE (sulle
  pagine 2-5) dice `11-15 PI`.

## 2. Sul grid

* **TRACK**: riga 7 pad 16, **la VEL OFFSET di ogni traccia a 0**; riga 8 pad 16, **ogni step del pattern di nuovo
  sulla griglia** (niente nudge; UNDO). Arancio finché ce n'è uno.
* **CC**: riga 5, pad 13 **COPIA la lane** (i suoi lock nel pattern), 14 **INCOLLA** sulla lane che vedi (ciano: ce n'è
  una copiata), 15 **la lane in ogni pattern** della traccia. Riga 8: pad 3-6 **il modo della lane** (NORMAL, SLIDE,
  TRIGLESS, NRPN: come ENV K4; bianco quello acceso); pad 7-16 **gli attrezzi**, lungo il loop: RAMPA SU, RAMPA GIÙ, SU
  E GIÙ, A CASO, A TESTA IN GIÙ, UN PASSO PRIMA, UN PASSO DOPO (gira nel loop), AMMORBIDITA (ogni lock con i vicini), A
  METÀ VERSO LA BASE, SVUOTA LA PAGINA. UNDO le rimette tutte.
* **BEAT**: riga 4 pad 8, **DICE PROG** (come SEQ + nero 1 tenuto).
* **SONG**, riga 4: 5 e 6 l'entrata **un posto prima / dopo**, 7 **il suo tempo = il tempo di adesso**, 8 niente tempo
  suo, 9 **SONG TEMPO**, 10 e 11 le sue battute **a metà / il doppio**, 12 **SAVE THE SET**, 15 **l'entrata libera dopo
  l'ultima** (per aggiungerne una), 16 **la song dalla prima entrata** (SHIFT + 16 la svuota, come prima).
* **FX**, riga 2: pad 13 e 15, LOOP e REPEAT di **1/16 puntato** e **1/8 puntato**.
* **PROJ**:
  * riga 1, pad 13-16: la chiave **una quinta sotto**, **una quinta sopra**, **la relativa** (LA minore ↔ DO
    maggiore), **la parallela** (LA minore ↔ LA maggiore) - queste due di una chiave maggiore o minore;
  * riga 3 pad 16: **LA CHIAVE DI PRIMA** (avanti e indietro fra le ultime due);
  * riga 5: pad 4 la manopola MASTER sull'ENERGIA; pad 6-13 **gli interruttori del progetto**: SONG TEMPO, MIDI IN
    SUONA anche senza REC, LONG PATTERNS (frase / il pattern si ripete), il CLICK (spento, con REC, sempre), il COUNT
    IN (0, 1, 2 battute), MUTE QUEUE, SCENE METRE, il PROFILO (FULL, SEMPLICE, PALCO). Accesi quando sono accesi;
  * riga 6: pad 11 **svuota lo slot** (due volte), 13 e 14 **la scaletta del Pi** (il file prima / dopo), 15 **salva
    sopra il file** caricato dal Pi (due volte), 16 **un PROGETTO NUOVO** (due volte; gli slot restano come sono);
  * riga 7: pad 8 **il tempo a metà**, 10 **il doppio** (da 30 a 300), **11-16 il tempo 90, 100, 120, 128, 140, 174**
    (bianco quello di adesso).
* **TRACK 2**: riga 5 pad 9-12 **il banco di scene** dei pad 1-8 (1-8, 9-16, 17-24, 25-32), 13 **i programmi della
  scena in tutte le scene**, 14 **la scena senza programmi**, 15 **il programma di questo canale in tutte le scene**.
  Righe 6-8: **un tocco sposta la testina di quel loop** su quello step (`NOTE LOOP FROM STEP 3`).
* **LIB**: **112 file** nelle righe 1-7 (erano 64, righe 1-4). Riga 8: pad 3 **il PRIMO file**, 5 **il file caricato
  come è sul Pi** (due volte: quello che hai cambiato da allora va via), 6 e 7 **il pattern e la progressione al Pi**,
  **10-15 gli ultimi file caricati** (10 quello caricato, 11-15 i cinque prima, il più nuovo per primo; per nome: un
  tocco lo sceglie, ancora lo carica; uno che il Pi non ha più lo dice: `NOT ON THE PI NOW: ...`). Dopo un file caricato
  dalla riga 8, un tocco su un file prima lo sceglie.
* **MOSSE**: riga 4 pad 12-14 **la frase di 4, 8, 16 battute**; riga 6 pad 9-11 **MOVES AT** la frase / ogni battuta /
  ogni beat, 12 e 13 **il genere** - / +, 14 e 15 **la chiave** - / + (da fermo subito, in play in coda); riga 7 pad
  14-16 **HARMONY** acceso / spento, **LOCK**, **le battute di un accordo** (in play mostrano l'accordo, e lo fanno lo
  stesso).
* **REGIA**: le righe 2-8 sono **quelle delle MOSSE** (le regole del regista restano sulla riga 1).
* **FOLLOW**, righe 5-8 pad 11-16, su una manopola che non è di una traccia: dopo i neri dell'FM-1, **le voci 27-32** di
  una lista (le forme di un accordo di una USER PROG, ARP 5 K4: la 27 DOM9, la 28 MIN9) e **le lunghezze 17, 18, 19,
  21, 22, 23** (la lunghezza di un accordo, ARP 6 K3).

## 3. Un errore corretto

* **L'editor dei progetti sul Pi**, nella scheda Progetto: **MORPH verso la scena** offriva solo le scene 1-8 dalla
  0.30 (le scene sono 32). Adesso tutte e 32.

## 4. I progetti

* **I progetti di prima si aprono come erano.**
* Nel progetto non cambia niente, tranne una cosa: la manopola MASTER può essere sull'ENERGIA (il suo quarto lavoro).
* **Se torni alla 0.31**, apre i progetti della 0.32; la manopola messa sull'ENERGIA la trova sul TEMPO.
* **Sul Pi**: il bridge dà all'FM-1 fino a **112 file** (erano 64); l'editor ha l'ENERGIA nella manopola MASTER e le
  32 scene nel MORPH.

## 5. Se arrivi dalla 0.27

Le note intere sono in `docs/storia/` (`RELEASE-NOTES-0.28.md`, `0.29.md`, `0.30.md`, `0.31.md`). In breve:

* **0.28**: le tracce sono **12**; un passo tiene **6 note**; le lane CC sono **8**.
* **0.29**: i generi sono **22**, con il **BALANI** e il suo **BALAFON**; **8 progressioni** a genere; **ROLL** e
  **ACCENT**, **5 scale**, **3 groove**, **4 forme d'accordo**.
* **0.30**: **32 scene**, **16 snapshot**, la song di **128 entrate**, le TAPE di **3072 eventi**, UNDO a **32 righe**;
  VIAGGIO si chiama MOSSE dappertutto; l'accensione rimette i mute e la scena.
* **0.31**: i tasti delle tracce 13-16 sono **i gruppi** (batteria, bassi, melodiche, tutte); nella banca 9-12 i mute,
  la pagina di step, le scene e le snapshot sul grid; un LFO su un gruppo.
* Il manuale, "SAGGA SEQ 0.32 — Il manuale", ha le cose nuove.

## 6. L'esploratore

L'esploratore prova ogni gesto in ogni situazione. Ha una situazione nuova, così le cose della 0.32 sono anche nel
piano per l'FM-1 vero (`fm1_piano.json`) e nel banco:

* **0.32**: la manopola MASTER sull'ENERGIA, una band TECHNO, l'LFO 1 copiato e incollato sul 2, la lane 2 del grid in
  rampa e su SLIDE (e copiata), la frase di 8 battute e le MOSSE a ogni battuta, il tempo 140 e MUTE QUEUE dal grid, il
  tablet e il grid, in play. Prima di cominciare la sonda controlla il tempo e l'LFO.
* Nei gesti: tutti i pad della vista **LIB** (senza un Pi: chiede, e lo dice).

## Come è stato provato

PROVE_QUI

## I tasti che restano senza lavoro

TASTI_QUI

## Installare

Come sempre: prima il Pi (`sagga-hub-0.32.zip`), poi l'FM-1 (`sagga-0.32.fwsc`). I passi sono in `INSTALLA.md`. Sullo
schermo, dopo l'aggiornamento: `SAGGA SEQ 0.32` per tre secondi.

## Cosa provare per primo

1. **La forza di uno step**: tieni EDIT e tocca il **nero 8** sullo step del cursore: ACCENTO, GHOST, NORMALE. Con i
   **neri 9 e 10** lo step si sposta nel loop.
2. **Una rampa in un colpo**: tieni ENV, scegli la lane con un **nero 1-8**, poi il **nero 9**: la lane sale lungo il
   pattern; il **nero 11** la svuota.
3. **Un LFO doppio**: tieni LFO, **nero 7** (copia), il bianco di un altro LFO, **nero 8** (incolla).
4. **La scaletta senza grid**: con il Pi acceso, tieni SAVE e tocca due volte il **bianco 15**: il file dopo.

DIMENSIONE
