# SAGGA SEQ 0.10 - Installazione

Ti servono due file nei Download di Windows (li fa `sh tools/make_release.sh 0.10`, e sono allegati al rilascio):

* `sagga-seq-0.10-source.zip`: il sorgente del firmware (e di tutto il resto);
* `sagga-hub-0.10.zip`: il bridge dei Launchpad, l'hub (pagina 8090), il convertitore, i plugin per il Raspberry Pi.

**Attenzione al formato.** La 0.10 scrive e legge solo `SGQA`: **non carica i progetti della 0.9** (né gli slot
nell'FM-1 né i file `.sgq` sul Pi). All'accensione gli slot vecchi risultano vuoti; i file 0.9 sul Pi restano dove
sono ma la libreria li rifiuta. Se un progetto 0.9 ti serve ancora, esportalo prima (vista PROJ, EXPORT) e tienilo
per un firmware 0.9. I progetti si rifanno in fretta: BAND (SEQ + SEL + nero 7) mette giù un genere intero.

## 1. Compila in WSL

```sh
wsl -d Ubuntu2004
cd ~
rm -rf sagga-seq-0.10-source
unzip -q /mnt/c/Users/user/Downloads/sagga-seq-0.10-source.zip
cd sagga-seq-0.10-source
sh tests/run_sagga_tests.sh
./build.sh --release 0.10
cp build/sagga-seq-0.10.fwsc /mnt/c/Users/user/Downloads/sagga-0.10.fwsc
cp tools/fm1_install.py /mnt/c/Users/user/Downloads/
```

I test devono finire tutti con `0 failures` (`sagga plugins: skipped` va bene: serve una copia di RaspiMIDIHub per
quelli). `build.sh` deve dire `ok image` e nessun `FAIL` su RAM e pool. Guarda la riga `pool ... B of 344064`: la 0.10
usa circa 318 KB (il progetto è più grande: sei lane, sedici tonalità). Se un numero supera il limite, fermati e
mandami la riga. L'identità del pacchetto è `FM-1_960`.

## 2. Installa sull'FM-1

Collega l'FM-1 direttamente al PC e chiudi tutto ciò che può tenere occupata la porta MIDI (Ableton, il browser con
l'installer web, i MIDI monitor). Poi, in PowerShell:

```powershell
cd C:\Users\user\Downloads
py -3.12 .\fm1_install.py .\sagga-0.10.fwsc
```

Conferma con `y`. Dopo il riavvio lo schermo deve mostrare `SAGGA SEQ 0.10`. Oppure dal Pi: carica il `.fwsc` nella
pagina dell'hub (`http://<ip del pi>:8090`) e premi *Installa*.

## 3. Aggiorna il Raspberry Pi

Il bridge e l'hub 0.10 servono per i progetti `SGQA` (quelli vecchi rifiuterebbero i salvataggi nuovi) e per il
convertitore `.mid`, che va ricompilato con il core nuovo. Da PowerShell:

```powershell
cd C:\Users\user\Downloads
scp .\sagga-hub-0.10.zip user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.10.zip && cd sagga-hub-0.10
sudo sh install_hub.sh --no-pc        # il Pi 4 di casa; sull'expander con il RP2040: senza --no-pc, poi sudo reboot
```

Lo script è lo stesso della 0.9 e si può rilanciare: rimette il bridge (`/opt/sagga/sagga_grid_bridge.py`), l'hub,
i plugin SAGGA Remote e SAGGA Mutes, l'M8 link, e ricompila `sagga_sgqmid` dai sorgenti nello zip (deve dire
`sagga_sgqmid built`). Serve internet solo la prima volta (i pacchetti Python e `gcc`).

Per controllare: `journalctl -u sagga-grid-bridge -e` (le porte dei due Launchpad, quella dell'FM-1, `bridge
running`) e la pagina `http://<ip del pi>:8090`, che deve mostrare il firmware collegato come `FM-1_960`.

Se usi lo Zynthian invece del Pi: `SAGGA-GRID-ZYNTHIAN.md` nello zip, stessi passi della 0.9 con i file nuovi.

## 4. Le patch dei synth, le due porte USB

Come nella 0.9: `patches.json` in `/boot/firmware/sagga/` per PATCHES; HOME + SEL, K1 su `2`, OCT+ due volte per le
due porte USB (i canali 15 e 16 alle tracce). Entrambe le impostazioni sopravvivono all'aggiornamento.

## 5. Primo controllo

1. All'accensione lo schermo dice `SAGGA SEQ 0.10`. Gli slot sono vuoti (il formato è nuovo).
2. **SEQ + SEL + nero 7** (BAND): lo schermo dice `TECHNO BAND #1: 8 TRACKS`. **PLAY**: suona una band di otto tracce
   sui canali 1-8. SEQ + PRESETS cambia genere: con SEQ 7 K4 su `LIVE`, alla battuta dopo la band è del genere nuovo.
3. HOME, OCT+ fino a `HOME 1/8`, **K2** a 8 e poi di nuovo a 16: la cassa non si sposta rispetto alla battuta.
4. **FX + HOME**: PANIC, tutto tace e la musica riprende. Di nuovo entro due secondi: si ferma.
5. ENV: la pagina della lane 1; **OCT+**: la lane 2. SAVE + OCT+: la seconda pagina di SAVE (CC LEAD, SONG TEMPO,
   DEVICE, LIBRARY).
6. **SEL + PERF**: VIAGGIO. K3 su `BASS`, tap sul bianco 1: `T1 BASS P2 SEL+KEY: IN`; tieni il bianco 1 mezzo secondo
   due volte, poi ALG: `T1 BASS P3 (2/3)`.
7. Sul Pi, dalla pagina 8090, EXPORT dal grid (vista PROJ) e il file compare nella libreria; il link `.mid` funziona.

Poi il test hardware (`tools/hwtest`: `run_hw_test.ps1` da PowerShell, con l'FM-1 direttamente sul PC) per il
controllo completo del timing: deve dire `0 failures`.

Le note di rilascio (`RELEASE-NOTES-0.10.md`) elencano tutto il nuovo; il riferimento completo è `docs/SAGGA-SEQ.md`;
il manuale 0.10 (in italiano) è il documento che accompagna il rilascio.
