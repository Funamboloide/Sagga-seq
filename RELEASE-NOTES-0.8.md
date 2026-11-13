# SAGGA SEQ 0.8 - Note di rilascio

La 0.8 riparte dalla 0.7 e la rifà dove serviva: niente compatibilità con i progetti vecchi (formato `SGQ8`).

## Nuovo

* **Livello live per traccia.** EUCLID LIVE con pulse e rotazione proprie per ogni traccia: si sente subito, sopra il
  pattern scritto. Poi un ALGORITMO per traccia: TURING (ritmo, note o entrambi), CELL (automa cellulare, ogni 1/2/4
  battute o ogni giro), ACCENT, DENSITY (meno colpi, oppure ghost note in più). LED, schermo e grid mostrano quello che
  si sente; in ciano i colpi aggiunti dal livello live. **WRITE LIVE** (SEQ + bianco 7) scrive nel pattern quello che
  senti. Girare le manopole di un algoritmo non lo fa più ripartire.
* **ARMONIA.** Sei progressioni per genere, con colori: settima, nona, sus4, sus2, sesta. Le tracce con FOLLOW seguono
  l'accordo che suona e lo schermo ne mostra il nome. PROG scrive l'accordo di tonica e accende ARMONIA e FOLLOW.
* **SNAPSHOT (8).** Memorizzano lo stato live: pattern in riproduzione, mute/solo, macro, tonalità e TRANSPOSE,
  armonia, impostazioni delle tracce, LFO e, se vuoi, il tempo. Tornano al momento del QUANTISE. Con loro:
  * **CC CAPTURE** prende i valori CC che arrivano dai synth;
  * **SEND** li rimanda;
  * **PATCHES** fa conservare al Raspberry le patch SysEx dei synth e le rimanda quando lo snapshot torna.

  Si usano dal pannello (SAVE + neri), dal grid (vista FX, riga 8) e dal telefono (CC 106-119 e 12-19).
* **MIDI FX per traccia** (HOME pagina 5): HARM, OCTAVE, ECHO, VEL CURVE, con tempo e quanto si mantiene ogni
  ripetizione. **FX + OCT+** accende l'ECHO su tutte le tracce.
* **I dadi ricordano.** Fino a 16 lanci: con ALG ci si muove avanti e indietro, OCT+ tiene il lancio, OCT− rimette
  tutto com'era.
* **24 generi**: in più ELECTRO, BREAKBEAT, DRUM+BASS, TRAP, AFRO HOUSE, AMAPIANO, FOOTWORK, MINIMAL, TRANCE, LO-FI.
* **USB PORTS 2** (pagina USB): la porta 1 è per i synth, con 16 canali per le tracce; la porta 2 è per grid, remote
  e SysEx.
* **Grid**:
  * vista EUCLID (BEAT premuto di nuovo): otto tracce, ognuna con il suo euclideo;
  * vista TRACK 3 (TRACK 2 premuto di nuovo): voicing, strum, MIDI FX, algoritmo, gate lunghi, canale;
  * vista BEAT rifatta, con due pagine di generi;
  * vista FX con snapshot ed ECHO.
* **EDIT + nero 1: STEP LOCK.** EVOLVE e i dadi non toccano quello step.

## Manopole

Ogni valore torna esattamente a 0. I valori che si muovono a passi di 2, 4 o 5 restano sui multipli di quel passo, quindi
non capita più di finire su 3 o su −1. Girando veloce si va ×2 e poi ×4; il primo scatto dopo una pausa, e ogni
cambio di direzione, vale sempre un passo solo.

## Corretti (dalla revisione della 0.7)

1. STOP e PANIC cancellano anche le ripetizioni dell'echo e gli strum in attesa.
2. MUTE, KILL e i mute di scena tagliano subito anche le note lunghe.
3. Gli algoritmi live restano sulla loro traccia, anche se ne selezioni un'altra.
4. Strum ed echo non fanno più perdere note degli accordi. La coda degli ornamenti ha 128 posti e, quando è piena, cede
   per prima l'eco più debole.
5. EVOLVE usa la progressione solo se l'ARMONIA è accesa, e funziona su qualsiasi lunghezza di traccia.
6. TURING e CELL non ripartono più quando giri le loro manopole.
7. La manopola CELLS di CELL funziona.
8. EUCLID è davvero per traccia e LED e grid mostrano quello che si sente. SEQ + OCT± è tornato a cambiare pagina.
9. STACCATO è corto anche su ratchet e arpeggi (40 % di ogni colpo).
10. Le macro accelerano: non servono più 127 scatti.

Altre correzioni:
* un messaggio lungo sullo schermo poteva scrivere fuori dal suo spazio in memoria (trovato con AddressSanitizer);
* le ripetizioni negative dell'ECHO, le OCTAVE fino a ±8 ottave e l'ACCENT che ereditava l'algoritmo sono stati
  ripuliti;
* lo swing è mostrato come percentuale vera (50 % = dritto).

## Test

I test girano su computer, senza bisogno dell'FM-1:

| Cosa | Controlli |
|---|---|
| Nucleo | 686.617 |
| Simulatore, con il firmware vero | 433 |
| Descrittori USB | 31 |
| Bridge | 218 |
| Plugin di RaspiMIDIHub | 12 |
| Fuzz | 60 sequenze casuali |

Tutti passano, anche con AddressSanitizer e UBSan.

La 0.8 non è ancora stata provata su un FM-1 vero.
