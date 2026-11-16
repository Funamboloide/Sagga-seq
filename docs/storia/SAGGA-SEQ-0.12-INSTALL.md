# SAGGA SEQ 0.12 - Installazione

Ti servono due file nei Download di Windows (li fa `sh tools/make_release.sh 0.12`, e sono allegati al rilascio):

* `sagga-seq-0.12-source.zip`: il sorgente del firmware (e di tutto il resto);
* `sagga-hub-0.12.zip`: il bridge dei Launchpad (con i due colori nuovi), l'hub (pagina 8090), il convertitore, i
  **cinque plugin** (Remote, Mutes e i nuovi Motori, Break, Mod) e le librerie del Pi, per il Raspberry Pi.

**Il formato.** La 0.12 scrive e legge `SGQB` come la 0.11: gli slot dell'FM-1, i file `.sgq` sul Pi, gli snapshot e la
libreria del Pi si aprono come sono (le tracce hanno due campi nuovi per il BREAK, che partono dai valori di base). Un
progetto salvato dalla 0.12 si apre anche sulla 0.11 (che ignora quei due campi e il modo BREAK suona come FREE).

**La mappa dei tasti è cambiata**: VIAGGIO è GLO 3, l'armonia e le progressioni utente sono ARP 3-6, la pagina USB è
SAVE 3, i quattro gesti SEQ + SEL + tasto sono tasti **tenuti** (UNDO = REDO, COOK = COOK a caso, KIT = BAND, DICE =
DICE PROG), l'ottava live è GLO + SEL + OCT. **Un tocco su HOME, SEQ, EDIT, ENV, LFO, ARP o FX apre la finestra del
tasto** (come tenerlo premuto, finché non lo tocchi di nuovo); SEL + ARP è l'arpeggio on / off, SEL + FX il loop a due
step (erano i tocchi di ARP e FX). La tabella completa: `../SAGGA-SEQ.md`, "The FM-1 panel".

## 1. Compila in WSL

```sh
wsl -d Ubuntu2004
cd ~
rm -rf sagga-seq-0.12-source
unzip -q /mnt/c/Users/user/Downloads/sagga-seq-0.12-source.zip
cd sagga-seq-0.12-source
sh tests/run_sagga_tests.sh
./build.sh --release 0.12
cp build/sagga-seq-0.12.fwsc /mnt/c/Users/user/Downloads/sagga-0.12.fwsc
cp tools/fm1_install.py /mnt/c/Users/user/Downloads/
```

I test devono finire tutti con `0 failures` (`sagga plugins: ... (the hub's own host: skipped ...)` va bene). `build.sh`
deve dire `ok image` e nessun `FAIL`. Guarda le tre cifre della riga delle note:

* `pool ... B of 344064`: come la 0.11 (circa 320 KB): il progetto in memoria non cambia di dimensione;
* `RAM .data+.bss ... B of 98304`: circa 4 KB più della 0.11 (la memoria di TAKE: 96 note, il fuoco del PICK, il pattern
  sotto un chop tenuto);
* `image ... B of 581564`: circa 22 KB più della 0.11 (PICK, BREAK, le mappe, il canale 13, le finestre, la vista PICK del grid).

Le stime vengono dalla compilazione per il PC (non con la toolchain JieLi): se un numero supera il limite, o la build si
ferma, **fermati e mandami la riga**. L'identità del pacchetto è `FM-1_962`.

## 2. Installa sull'FM-1

Collega l'FM-1 direttamente al PC e chiudi tutto ciò che può tenere occupata la porta MIDI (Ableton, il browser con
l'installer web, i MIDI monitor). Poi, in PowerShell:

```powershell
cd C:\Users\user\Downloads
py -3.12 .\fm1_install.py .\sagga-0.12.fwsc
```

Conferma con `y`. Dopo il riavvio lo schermo deve mostrare `SAGGA SEQ 0.12`. Oppure dal Pi: carica il `.fwsc` nella
pagina dell'hub (`http://<ip del pi>:8090`) e premi *Installa*.

## 3. Aggiorna il Raspberry Pi

Il bridge 0.12 ha i due colori nuovi del grid (TAIL e TIE: le note lunghe come blocchi; il bridge vecchio al loro posto
mostra DIM e basta), e lo zip porta i tre plugin nuovi. Da PowerShell:

```powershell
cd C:\Users\user\Downloads
scp .\sagga-hub-0.12.zip user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.12.zip && cd sagga-hub-0.12
sudo sh install_hub.sh --no-pc        # il Pi 4 di casa; sull'expander con il RP2040: senza --no-pc, poi sudo reboot
```

Lo script è lo stesso della 0.11 e si può rilanciare: rimette il bridge, l'hub, i plugin (anche i tre nuovi), l'M8
link, ricompila `sagga_sgqmid` (deve dire `sagga_sgqmid built`); le librerie già tue in `/boot/firmware/sagga/` non le
tocca. Poi nell'interfaccia del RaspiMIDIHub: aggiungi **SAGGA Motori**, **SAGGA Break** e **SAGGA Mod** (stanno con i
controller), collega l'OUT di ciascuno all'FM-1 nella matrice (con USB PORTS 2: alla porta 2) e salva la configurazione.
Sull'FM-1 serve **SAVE K2 = REMOTE 13 + 14** (il profilo PALCO lo mette da solo).

Per controllare: `journalctl -u sagga-grid-bridge -e` (`bridge running`) e la pagina `http://<ip del pi>:8090`, che deve
mostrare il firmware collegato come `FM-1_962`.

Se usi lo Zynthian invece del Pi: `SAGGA-GRID-ZYNTHIAN.md` nello zip, stessi passi con i file nuovi.

## 4. Le patch dei synth, le due porte USB

Come prima: `patches.json` in `/boot/firmware/sagga/` per PATCHES. Le due porte USB sono su **SAVE 3** (SAVE tenuto, OCT+
due volte): K1 su `2`, poi **SEL + K1 due volte** per riconnettere. Entrambe le impostazioni sopravvivono all'aggiornamento.

## 5. Primo controllo

1. All'accensione lo schermo dice `SAGGA SEQ 0.12`. Gli slot della 0.11 si caricano (HOME + SAVE due volte).
2. **SEQ tenuto, nero 7 tenuto 0,6 s** (BAND): `TECHNO BAND #1: ...`. **PLAY**. **Tocca SEQ** e lascialo: la pagina
   `SEQ 1/7 EUCLID` resta sullo schermo, il pulsante SEQ è acceso pieno (la finestra); dopo mezzo secondo le due righe
   dei messaggi mostrano la mappa dei suoi tasti. **OCT+** sfoglia le pagine, i tasti bianchi sono i TOOLS; **tocca SEQ**
   di nuovo: gli step tornano.
3. **Tocca HOME** (la finestra). Gira **K2** di uno scatto (il fuoco va su LENGTH: `> LENGTH` sullo schermo), poi **SEL +
   bianco 8**: la lunghezza diventa 32 (alla battuta); **SEL + nero 11**: il fuoco passa a K3 (`> STEP`); **SEL + bianco
   3**: la divisione diventa la terza. Con SEL tenuto i tasti validi sono accesi e quello del valore lampeggia. Tocca
   HOME per chiudere (la stessa cosa funziona tenendo HOME invece di toccarlo).
4. Tieni il bianco 3 e premi il bianco 6 (`NOTE 3-6: 4 STEPS`): sullo schermo le quattro celle sono un blocco unico, sulla
   tastiera i tasti 4-6 sono in glow; sul grid le tre celle sono verde scuro.
5. **Tocca ARP**: la tastiera suona la traccia senza registrare (la finestra di ARP: il pulsante acceso). **REC tenuto
   0,6 s** dopo aver suonato qualche nota: `TAKE: N NOTES INTO T1`, le note sono nel pattern; UNDO le toglie. Tocca ARP
   per chiudere. **SEL + ARP** (un tocco): l'arpeggio on / off.
6. **SEL + GLO** (tocco): VIAGGIO parte. Di nuovo **SEL + GLO**: `STUDIO: THE JOURNEY GOES ON`, la tastiera torna agli step
   mentre la frase continua; **SEL + GLO tenuto**: `VIAGGIO OFF`.
7. HOME 4, **K1 su BREAK** (o HOME + SEL + bianco 5). Dai alla traccia il canale di un campionatore con un break sulle
   note da C4 in su. **SEQ 7, K1**: `BREAK T1: END ROLL`, i 16 step sono gli slice 1-16. **SEQ + nero 1**: il dado tiene
   cassa e rullante sui battere. **Tocca ARP**: **bianco 5** toccato = `DOUBLE` (resta), **bianco 6 tenuto** = `HALF` finché
   lo tieni e poi `BACK`; **nero 3**: HALF; **nero 1 tenuto**: il roll. **SEQ + bianco 9** (COOK): `GHOST (TECHNO 2/5)`, i
   chop del genere. Con **REC** acceso e la finestra chiusa i bianchi suonano gli slice.
8. **FX + SEL + K1** girata e lasciata: INTENSITY sale e torna a 0 da sola in una battuta (la cella lo mostra).
9. **ARP 3** (ARP tenuto, OCT+ due volte): l'armonia; **ARP + SEL + bianco 3**: `LOCK`. **ARP + SAVE** manda la
   progressione al Pi.
10. Dal Pi, con SAGGA Break aperto sul telefono e l'OUT collegato all'FM-1: i pad suonano gli slice della traccia
    selezionata; CHOP cambia il riordino; SAGGA Mod: un THROW lanciato torna al centro, **L3** accende l'LFO 3 (sull'FM-1,
    tocca LFO: il bianco 3 è acceso). Sul grid: **SHIFT + STEP due volte** (PICK) con una finestra aperta sull'FM-1: le
    quattro righe sono le sue manopole, il pad bianco il valore attuale.

Poi il test hardware (`tools/hwtest`: `run_hw_test.ps1` da PowerShell, con l'FM-1 direttamente sul PC) per il
controllo completo del timing: deve dire `0 failures`.

## 6. L'esploratore sull'FM-1

L'abbiamo fatto girare sull'FM-1 il 9 novembre (20 sessioni, 0 errori). Per rifarlo dopo un aggiornamento: il PC preme i
tasti dell'FM-1 per venti minuti e poi confronta tutto con il simulatore (`tools/hwtest/LEGGIMI.md`):

```sh
cd ~/sagga-seq-0.12-source
python3 tests/sagga_explore.py --hw-piano /mnt/c/Users/user/Downloads/sagga-esploratore
```

FM-1 fermo, collegato al PC, niente sulla presa MIDI IN, Ableton chiuso. In PowerShell:

```powershell
cd C:\Users\user\Downloads\sagga-esploratore
powershell -ExecutionPolicy Bypass -File .\run_hw_explore.ps1
```

Sull'FM-1 compare `PC TEST? SEL = YES`: premi **SEL**, poi non toccarlo (una mano lo ferma). Alla fine il tuo progetto
torna in memoria. Di nuovo in WSL:

```sh
python3 tests/sagga_explore.py --hw "$(ls -t /mnt/c/Users/user/Downloads/sagga-esploratore/raccolta-*.json | head -1)"
```

e mandami `build/explore/RAPPORTO-HW.md` (o la raccolta).

Le note di rilascio (`RELEASE-NOTES-0.12.md`) elencano tutto il nuovo; il riferimento completo è `../SAGGA-SEQ.md`;
il disegno da cui è partita la 0.12 è `SAGGA-SEQ-0.12-DISEGNO.md` (con, in fondo, cosa è stato fatto diversamente).
