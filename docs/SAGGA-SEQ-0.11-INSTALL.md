# SAGGA SEQ 0.11 - Installazione

Ti servono due file nei Download di Windows (li fa `sh tools/make_release.sh 0.11`, e sono allegati al rilascio):

* `sagga-seq-0.11-source.zip`: il sorgente del firmware (e di tutto il resto);
* `sagga-hub-0.11.zip`: il bridge dei Launchpad, l'hub (pagina 8090), il convertitore, i plugin, e le librerie nuove
  del Pi (le variazioni in più e le progressioni) per il Raspberry Pi.

**Se hai già installato la 0.11 di prima** (quella senza il test dal PC): rifai solo i punti 1 e 2, l'FM-1. Il Pi non
cambia: il bridge, l'hub e le librerie sono gli stessi.

**Il formato.** La 0.11 scrive `SGQB` e **legge ancora i progetti 0.10** (`SGQA`): gli slot dell'FM-1 e i file `.sgq`
sul Pi si aprono, con le cose nuove spente (un solo slot di algoritmo per traccia, l'armonia nel genere del progetto,
FOLLOW su HOLD, le progressioni utente come erano). Un progetto salvato dalla 0.11 non si apre più sulla 0.10: se
pensi di tornare indietro, esporta prima i progetti che ti servono (vista PROJ, EXPORT).

## 1. Compila in WSL

```sh
wsl -d Ubuntu2004
cd ~
rm -rf sagga-seq-0.11-source
unzip -q /mnt/c/Users/user/Downloads/sagga-seq-0.11-source.zip
cd sagga-seq-0.11-source
sh tests/run_sagga_tests.sh
./build.sh --release 0.11
cp build/sagga-seq-0.11.fwsc /mnt/c/Users/user/Downloads/sagga-0.11.fwsc
cp tools/fm1_install.py /mnt/c/Users/user/Downloads/
```

I test devono finire tutti con `0 failures` (`sagga plugins: skipped` va bene). `build.sh` deve dire `ok image` e nessun
`FAIL`. Guarda le tre cifre della riga delle note:

* `pool ... B of 344064`: la 0.11 usa circa 320 KB (la 0.10 circa 318: le tracce e le progressioni sono più grandi);
* `RAM .data+.bss ... B of 98304`: circa 30 KB più della 0.10 (25 KB sono il test dal PC: le sonde, gli eventi), ben
  sotto il limite;
* `image ... B of 581564`: la libreria nuova (2304 variazioni in 44 KB) e il codice dell'armonia fanno crescere
  l'immagine di circa 85 KB rispetto alla 0.10, più circa 5 KB del test dal PC.

Le stime vengono da una compilazione di prova fatta qui (non con la toolchain JieLi): se un numero supera il limite, o
la build si ferma, **fermati e mandami la riga**. L'identità del pacchetto è `FM-1_961`.

## 2. Installa sull'FM-1

Collega l'FM-1 direttamente al PC e chiudi tutto ciò che può tenere occupata la porta MIDI (Ableton, il browser con
l'installer web, i MIDI monitor). Poi, in PowerShell:

```powershell
cd C:\Users\user\Downloads
py -3.12 .\fm1_install.py .\sagga-0.11.fwsc
```

Conferma con `y`. Dopo il riavvio lo schermo deve mostrare `SAGGA SEQ 0.11`. Oppure dal Pi: carica il `.fwsc` nella
pagina dell'hub (`http://<ip del pi>:8090`) e premi *Installa*.

## 3. Aggiorna il Raspberry Pi

Il bridge 0.11 serve per i progetti `SGQB`, per le **variazioni in più** e le **progressioni** che il Pi tiene per
l'FM-1 (senza il bridge nuovo l'FM-1 si ferma alle sue), e il convertitore `.mid` va ricompilato con il core nuovo.
Da PowerShell:

```powershell
cd C:\Users\user\Downloads
scp .\sagga-hub-0.11.zip user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.11.zip && cd sagga-hub-0.11
sudo sh install_hub.sh --no-pc        # il Pi 4 di casa; sull'expander con il RP2040: senza --no-pc, poi sudo reboot
```

Lo script è lo stesso e si può rilanciare: rimette il bridge, l'hub, i plugin, l'M8 link, ricompila `sagga_sgqmid`
(deve dire `sagga_sgqmid built`) e copia in `/opt/sagga/hub/patterns/` e `/opt/sagga/hub/progressions/` le librerie
di partenza (un file per genere). La prima volta che un genere cambia (un SEQ + SAVE dall'FM-1, un'aggiunta o una
cancellazione dalla pagina) il suo file viene copiato accanto ai progetti, in `/boot/firmware/sagga/patterns/` e
`/boot/firmware/sagga/progressions/`, e da lì in poi è tuo: lo puoi aprire anche da Windows, sulla partizione FAT.

Per controllare: `journalctl -u sagga-grid-bridge -e` (le porte dei due Launchpad, quella dell'FM-1, `bridge
running`, nessun `sagga_patterns.py not found` o `sagga_progs.py not found`) e la pagina `http://<ip del pi>:8090`,
che deve mostrare il firmware collegato come `FM-1_961` e, in fondo, **PATTERN SUL PI** e **PROGRESSIONI SUL PI**.

Se usi lo Zynthian invece del Pi: `SAGGA-GRID-ZYNTHIAN.md` nello zip, stessi passi con i file nuovi.

## 4. Le patch dei synth, le due porte USB

Come prima: `patches.json` in `/boot/firmware/sagga/` per PATCHES; HOME + SEL, K1 su `2`, OCT+ due volte per le due
porte USB. Entrambe le impostazioni sopravvivono all'aggiornamento.

## 5. Primo controllo

1. All'accensione lo schermo dice `SAGGA SEQ 0.11`. Gli slot della 0.10 si caricano (HOME + SAVE due volte).
2. **SEQ + SEL + nero 7** (BAND): `TECHNO BAND #1: 10 TRACKS` (o quante tracce libere trova). **PLAY**. Ora
   **SEQ + PRESETS**: il genere cambia sullo schermo, gli accordi **no** (SEQ 4 mostra ancora `1 TECHNO`). Premi BEAT
   (SEQ + bianco 10) su una traccia: adesso l'armonia passa al genere nuovo.
3. SEQ 4, **K1 su LOCK**: carica qualcosa di un altro genere, l'armonia resta dov'è.
4. HOME 1, **K2** da 16 a 32 mentre suona: lo schermo dice `LENGTH 32 AT THE BAR`, alla battuta la traccia diventa di
   32 step e i 16 nuovi ripetono quello che c'era.
5. Tieni premuto il bianco 3 e premi il bianco 6: `NOTE 3-6: 4 STEPS`. Tocca **FX** da solo e rifai lo stesso gesto:
   ora è il loop fra i due step (EXIT lo toglie).
6. SEQ 2: **SEL + K1** passa allo slot `ALGO 2` (la cella lo mostra); K1 sceglie l'algoritmo del secondo slot.
7. SEQ 4 con **SEL**: K4 su `3+3+2`, K3 un **MOOD**, K1 il modo di FOLLOW (`RETRIG`, `LEGATO`). **SEQ + SEL + nero
   1**: `DICE PROG EPIC: i-bVI-bVII-i` (o simile), suona subito.
8. Con il bridge nuovo: SEQ 4, **K2** oltre l'ultima progressione: `PI EPIC 1/8: ...`. SEQ + ALG oltre la 12ª
   variazione: `#13/12+PI`, BEAT la carica. **SEQ + SAVE** manda la traccia al Pi (`ON THE PI: TECHNO KICK #...`); sulla
   pagina 8090 compare.

Poi il test hardware (`tools/hwtest`: `run_hw_test.ps1` da PowerShell, con l'FM-1 direttamente sul PC) per il
controllo completo del timing: deve dire `0 failures`.

## 6. L'esploratore sull'FM-1

Il PC preme i tasti dell'FM-1 per venti minuti e poi confronta tutto con il simulatore (`tools/hwtest/LEGGIMI.md`):

```sh
cd ~/sagga-seq-0.11-source
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

Le note di rilascio (`RELEASE-NOTES-0.11.md`) elencano tutto il nuovo; il riferimento completo è `docs/SAGGA-SEQ.md`;
il manuale (in italiano) è il documento che accompagna il rilascio.
