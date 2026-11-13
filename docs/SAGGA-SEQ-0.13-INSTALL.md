# SAGGA SEQ 0.13 - Installazione

Ti servono due file nei Download di Windows (li fa `sh tools/make_release.sh 0.13`, e sono allegati al rilascio):

* `sagga-seq-0.13-source.zip`: il sorgente del firmware (e di tutto il resto);
* `sagga-hub-0.13.zip`: il bridge dei Launchpad, l'hub (pagina 8090, **con il BREAK IN SLICE**), il convertitore, i
  cinque plugin (**SAGGA Mod con le terzine**) e le librerie del Pi, per il Raspberry Pi.

**Il formato.** La 0.13 scrive e legge `SGQB` come la 0.12: gli slot dell'FM-1, i file `.sgq` sul Pi, gli snapshot e la
libreria del Pi si aprono come sono. Le cose nuove (RATE SEQ, TRIG, CHAIN LIST, MOTION, KEYBOARD, MIDI IN) stanno in un
blocco in coda al progetto, scritto solo se ne usi qualcuna: un progetto della 0.13 si apre anche sulla 0.12, che salta
il blocco.

**La mappa dei tasti è la stessa della 0.12**, con le aggiunte: LFO ha 4 pagine (la 4 è RATE SEQ, la 3 ha TRIG su K4),
HOME ne ha 8 (la 8 è la CHAIN LIST; HOME 7 K2 è OFF / P1+2 / LIST), SAVE ne ha 4 (la 4 è LIVE IN: MOTION, KEYBOARD, KEYB
CH, MIDI IN), EDIT + nero 7 è lo SLIDE, ARP + nero 1-4 su una traccia DRUM in play è il NOTE REPEAT. La tabella completa:
`docs/SAGGA-SEQ.md`, "The FM-1 panel" e "What is new in 0.13".

## 1. Compila in WSL

```sh
wsl -d Ubuntu2004
cd ~
rm -rf sagga-seq-0.13-source
unzip -q /mnt/c/Users/user/Downloads/sagga-seq-0.13-source.zip
cd sagga-seq-0.13-source
sh tests/run_sagga_tests.sh
./build.sh --release 0.13
cp build/sagga-seq-0.13.fwsc /mnt/c/Users/user/Downloads/sagga-0.13.fwsc
cp tools/fm1_install.py /mnt/c/Users/user/Downloads/
```

I test devono finire tutti con `0 failures` (`sagga plugins: ... (the hub's own host: skipped ...)` va bene; c'è una riga
nuova, `sagga slicer: ... 0 failures`). `build.sh` deve dire `ok image` e nessun `FAIL`. Le tre cifre della riga delle
note, rispetto alla 0.12 (`image 352180`, `RAM 63152`, `pool 321576`):

* `pool ... B of 344064`: circa 800 byte in più (il blocco nuovo del progetto: 780 byte), quindi intorno a 322 400;
* `RAM .data+.bss ... B of 98304`: qualche centinaio di byte in più (i colpi dei TRIG, la catena che suona, lo SLIDE);
* `image ... B of 581564`: circa 8-12 KB in più.

Le stime vengono dalla compilazione per il PC: se un numero supera il limite, o la build si ferma, **fermati e mandami
la riga**. L'identità del pacchetto è `FM-1_963`.

## 2. Installa sull'FM-1

Collega l'FM-1 direttamente al PC e chiudi tutto ciò che può tenere occupata la porta MIDI (Ableton, il browser con
l'installer web, i MIDI monitor). Poi, in PowerShell:

```powershell
cd C:\Users\user\Downloads
py -3.12 .\fm1_install.py .\sagga-0.13.fwsc
```

Conferma con `y`. Dopo il riavvio lo schermo deve mostrare `SAGGA SEQ 0.13`. Oppure dal Pi: carica il `.fwsc` nella
pagina dell'hub (`http://<ip del pi>:8090`) e premi *Installa*.

## 3. Aggiorna il Raspberry Pi

Serve per il BREAK IN SLICE e per le terzine di SAGGA Mod (il bridge e gli altri plugin non cambiano). Da PowerShell:

```powershell
cd C:\Users\user\Downloads
scp .\sagga-hub-0.13.zip user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.13.zip && cd sagga-hub-0.13
sudo sh install_hub.sh --no-pc        # il Pi 4 di casa; sull'expander con il RP2040: senza --no-pc, poi sudo reboot
```

Lo script è lo stesso e si può rilanciare: rimette il bridge, l'hub (con `sagga_slicer.py`), i plugin, l'M8 link,
ricompila `sagga_sgqmid` (deve dire `sagga_sgqmid built`); le librerie già tue in `/boot/firmware/sagga/` non le tocca.
SAGGA Mod si aggiorna da solo al riavvio del RaspiMIDIHub (resta al suo posto nella matrice).

Per controllare: la pagina `http://<ip del pi>:8090` deve mostrare il firmware collegato come `FM-1_963` e la sezione
**BREAK IN SLICE**.

## 4. Primo controllo

1. All'accensione lo schermo dice `SAGGA SEQ 0.13`. Gli slot della 0.12 si caricano (HOME + SAVE due volte).
2. **SEQ + nero 7 tenuto** (BAND): `TECHNO BAND #1: ...`. **PLAY**.
3. **Il sidechain.** Tocca **LFO**, **bianco 2** (LFO 2 acceso). Pagina 1: **K1 su DECAY** (sette scatti). Pagina 2: K1 CC,
   K2 il canale di un pad, K3 CC 7 (o 11). Pagina 3: **K3 INVERT ON**, **K4 su T1** (`TRIG: T1 HITS START IT`): il pad si
   abbassa a ogni cassa della traccia 1 e risale. Pagina 1 K2: la RATE decide quanto dura (1/4 BAR: un quarto).
4. **RATE SEQ.** Pagina 4: **K1 su 2** (STEPS 2), K4 la velocità della posizione 1; **K3 +1** (POSITION 2/2), K4 un'altra
   (anche 1/8T, dopo 1/32): l'LFO cambia velocità a ogni battito. Tocca LFO per chiudere.
5. **NOTE REPEAT.** Seleziona la traccia della cassa o degli hat (una traccia DRUM della band). Tieni **ARP**, tieni il
   **bianco 1**, tieni il **nero 1**: lo strumento ogni sedicesimo; **nero 2**: 1/32; **nero 3**: 1/32T; **nero 4**: 1/8.
   Lasci: smette. Con **REC** acceso si scrive.
6. **SLIDE.** Una traccia melodica (il basso della band), il canale di un mono con il portamento a metà. **Tocca EDIT**,
   **bianco** di uno step acceso, **nero 7**: `SLIDE: GLIDES INTO THE NEXT NOTE (CC 65)` (il nero 7 si accende). La nota
   dopo scivola; quella dopo ancora no. Tocca EDIT per chiudere.
7. **CHAIN LIST.** HOME 7 (HOME tenuto, OCT+ sei volte), **K2 +2**: `CHAIN LIST: HOME 8 WRITES IT`. **OCT+**: HOME 8, `HOME
   8/8  >1 2 3 ...`. K1 la lunghezza, K2 la voce, K3 il pattern, K4 quante volte. **PLAY** da fermo: parte dalla voce 1.
8. **MOTION.** SAVE tenuto, OCT+ tre volte (SAVE 4/4 LIVE IN): **K1 su 1 BAR** (girare le manopole di SAVE non salva).
   **REC**, poi **FX + K4** a metà battuta su e giù: il FILTER. **REC** di nuovo: la battuta dopo il filtro si muove da
   solo come l'hai mosso. **FX + OCT-**: `MACROS 0, THE MOTION WIPED`.
9. **La tastiera.** Una tastiera MIDI sul MIDI IN (o dal PC sulla porta 1). SAVE 4 **K2 su ALL**: un RE suonato = `TRANSPOSE
   2` alla battuta (le tracce IN KEY si spostano), un DO lo riporta a 0. **SPLIT C3**: sotto il C3 traspone, sopra suona
   (con **K4 MIDI IN su ALWAYS** suona la traccia selezionata anche senza REC). K3: il canale della tastiera.
10. **Il Pi.** `http://<ip del pi>:8090`, **BREAK IN SLICE**: carica un break in WAV, 16 slice, *Taglia*: scarichi lo zip.
    Sullo Zynthian (o un altro lettore SFZ) carica il `.sfz`; sull'FM-1 una traccia **BREAK** (HOME 4 K1) sul canale di
    quel campionatore, la sua PEN sulla nota che dice `LEGGIMI.txt` (C1 = 36 se non l'hai cambiata), **SEQ 7 K4** sulle
    slice scelte, il tempo che dice il LEGGIMI. SAGGA Mod: la RATE arriva a 1/32T.

Poi il test hardware (`tools/hwtest`: `run_hw_test.ps1` da PowerShell, con l'FM-1 direttamente sul PC) per il
controllo completo del timing: deve dire `0 failures`.

## 5. L'esploratore sull'FM-1

Come per la 0.12 (`tools/hwtest/LEGGIMI.md`): il PC preme i tasti dell'FM-1 per venti minuti e poi confronta tutto con
il simulatore. In WSL:

```sh
cd ~/sagga-seq-0.13-source
python3 tests/sagga_explore.py --hw-piano /mnt/c/Users/user/Downloads/sagga-esploratore
```

FM-1 fermo, collegato al PC, niente sulla presa MIDI IN, Ableton chiuso. In PowerShell:

```powershell
cd C:\Users\user\Downloads\sagga-esploratore
powershell -ExecutionPolicy Bypass -File .\run_hw_explore.ps1
```

Sull'FM-1 compare `PC TEST? SEL = YES`: premi **SEL**, poi non toccarlo. Alla fine il tuo progetto torna in memoria. Di
nuovo in WSL:

```sh
python3 tests/sagga_explore.py --hw "$(ls -t /mnt/c/Users/user/Downloads/sagga-esploratore/raccolta-*.json | head -1)"
```

e mandami `build/explore/RAPPORTO-HW.md` (o la raccolta).

Le note di rilascio (`RELEASE-NOTES-0.13.md`) elencano tutto il nuovo; il riferimento completo è `docs/SAGGA-SEQ.md`.
