# SAGGA SEQ: il test sull'FM-1 vero (da Windows, via USB)

Un programma che, con l'FM-1 collegato al PC, fa sull'hardware quello che il simulatore fa qui: manda un progetto di
prova, lo fa suonare dal telecomando MIDI, ascolta note e clock e li confronta con quello che il firmware **deve**
mandare (calcolato dallo stesso firmware nel simulatore). Alla fine rimette a posto il tuo progetto.

## Come si lancia

1. FM-1 acceso, SAGGA SEQ in esecuzione, **fermo** (non in PLAY), collegato al PC via USB. Chiudi Ableton e tutto
   quello che usa le porte MIDI dell'FM-1: su Windows una porta MIDI la apre un programma solo.
2. Scompatta lo zip, apri PowerShell nella cartella e:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_hw_test.ps1
   ```
   La prima volta installa `mido` e `python-rtmidi` (serve Python 3.9+ e internet). Poi parte, chiede conferma, e in
   un minuto scarso stampa PASS / FAIL riga per riga. Opzioni: `--bars 8` (più battute nel test di PLAY),
   `--port Felucca` (se trova altre porte), `--yes` (non chiede).
3. Se qualcosa è FAIL: mandami il file `hwtest-<data>.log` della cartella. Dentro c'è ogni byte che l'FM-1 ha
   mandato, con i tempi: da lì capisco cosa ha fatto il firmware.

## Cosa controlla

| passo | che cosa |
| --- | --- |
| identità | l'handshake dell'updater: modello e versione |
| EXPORT | il progetto in memoria esce via SysEx, immagine SGQB (0.11; SGQA per la 0.10) con CRC giusto; viene salvato in `backup-<data>.sgq` |
| IMPORT | `hwtest.sgq` entra (un chunk alla volta, ogni chunk confermato), riesce identico |
| PLAY (telecomando CC 20, canale 14) | MIDI Start, clock a 128 BPM ±1 %, jitter, 96 clock a battuta, **ogni nota** delle prime due battute sui canali 1-3 (altezza, velocity, tempo entro 25 ms), la traccia 3 in EXPO RAMP con gli intervalli che si accorciano, ogni note-on ha il suo note-off, niente dopo STOP |
| MUTE | traccia 1 muta dal telecomando (CC 48) a metà della battuta 2 e di nuovo attiva a metà della 4: il canale 1 tace nella battuta 3 |
| TEMPO | +8 e -8 dal telecomando (CC 31 / 30): il clock va a 136 e torna a 128 |
| BUSY | un EXPORT mentre suona viene rifiutato con lo stato giusto |
| RESTORE | il backup torna in memoria. Sul display: `IMPORTED: SAVE TO KEEP IT`. È il tuo progetto come lo avevi; il programma **non scrive mai la flash** dell'FM-1: se vuoi tenere qualcosa, SAVE lo fai tu |

Il progetto di prova (`hwtest.sgq`, fatto col simulatore da `make_assets.py`): traccia 1 cassa sui quarti (nota 60),
traccia 2 quattro note (C D E G) sui primi quattro step, traccia 3 uno step con EXPO RAMP (8 colpi a battuta, curva
+4), traccia 4 una **traccia TAPE** di una battuta con due note suonate dentro, 128 BPM, clock master. Con un
firmware senza EXPO e TAPE (0.9) tutto passa tranne i canali 3 e 4: è il modo per vedere che versione c'è davvero
sopra.

## Cosa non può controllare

Lo schermo. I tasti fisici li preme l'esploratore (sotto): questo test guarda il MIDI, quello tutto il resto.

## L'esploratore sull'FM-1 (0.11)

L'esploratore (`tests/sagga_explore.py`, `docs/SAGGA-ESPLORATORE.md`) fa le sue sessioni a caso anche sull'FM-1 vero:
il PC preme i tasti, gira le manopole e suona la tastiera ai tempi di un piano (0.18: e fa da tablet e da grid, mandando i
loro comandi come se arrivassero dal Pi), e dopo ogni gesto l'FM-1 manda tutto il suo stato. Poi in WSL ogni sessione viene rifatta nel simulatore, ogni evento nel punto esatto in cui l'FM-1 l'ha preso
(il suo millisecondo e il suo tick di clock): le due macchine devono essere uguali sonda per sonda. Quello che differisce
è l'hardware (il compilatore, i tempi), non il piano.

1. In WSL, il piano e i file per Windows in una cartella dei Download:
   ```sh
   python3 tests/sagga_explore.py --hw-piano /mnt/c/Users/user/Downloads/sagga-esploratore
   ```
   (20 sessioni da 60 gesti, circa 20 minuti; `--sessioni 3` per una prova corta, `--seme N` per altre sessioni;
   `--hw-tablet N`: N sessioni in più con il tablet e il grid, dalla 0.18.1).
2. FM-1 acceso con la 0.11 o più recente (un piano con il tablet e il grid vuole la versione con cui è fatto, la 0.19: il programma lo controlla),
   **fermo**, collegato direttamente al PC; niente sulla presa MIDI IN; Ableton chiuso. In
   PowerShell, nella cartella:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_hw_explore.ps1
   ```
   Sullo schermo dell'FM-1: `PC TEST? SEL = YES, ANOTHER KEY = NO`: **premi SEL**. Da lì non toccarlo: per ogni
   sessione si riavvia nel test (`PC TEST: A HAND ON A KEY STOPS IT`) e suona da solo. Ogni sessione scrive una riga
   (`ok`, oppure cosa ha visto subito: FASE, NOTE APPESE, un errore).
3. Alla fine l'FM-1 si riavvia normale e il tuo progetto torna in memoria (`IMPORTED: SAVE TO KEEP IT`). Poi in WSL:
   ```sh
   python3 tests/sagga_explore.py --hw /mnt/c/Users/user/Downloads/sagga-esploratore/raccolta-<data>.json
   ```
   scrive `build/explore/RAPPORTO-HW.md`. Mandami quello, o la raccolta.

**Sicuro.** Durante il test l'FM-1 non legge e non scrive nessuno slot e nessuna impostazione: il blocco è nel punto più
basso, dove la flash viene scritta (`fl_app_lock`), e in più il salvataggio è spento (`PC TEST: SLOTS OFF`). Il
progetto che avevi in memoria resta sul PC (`backup-<data>.sgq`) e torna alla fine. Una mano su qualunque tasto o
manopola ferma il test subito, e il PC rimette a posto. Se il PC si ferma a metà, spegni e riaccendi l'FM-1: il test
vive solo nella RAM, alla riaccensione è sparito.

## File

`sagga_hw_test.py` il programma; `fm1_install.py` (l'handshake e il formato 7 bit, condivisi con l'installatore);
`hwtest.sgq`, `hwtest_expected.json` il riferimento; `run_hw_test.ps1` il lancio da PowerShell. Nel repository anche
`make_assets.py` (rigenera il riferimento) e `tests/sagga_hwtest_tests.py` (il programma contro un FM-1 finto).
L'esploratore: `sagga_hw_explore.py` e `run_hw_explore.ps1` (su Windows), `sagga_testport.py` (il SysEx del test,
anche per WSL); `firmware/src/sagga_test.c` il lato dell'FM-1; `tests/sagga_explore_hw.py` il piano e il confronto;
`tests/sagga_hw_explore_tests.py` il programma contro un FM-1 finto.
