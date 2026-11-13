# SAGGA SEQ 0.9 - Installazione

Ti servono tre file nei Download di Windows:

* `dinghy-sagga-0.9-src.tgz`: il sorgente del firmware;
* `sagga-0.9-pi.zip`: il bridge, il servizio e i plugin per il Raspberry Pi;
* questo foglio.

La 0.9 legge i progetti della 0.8: al primo avvio ritrovi l'ultimo slot salvato, e i file `.sgq` della 0.8 sul Pi si
caricano dalla libreria. Quando salvi, il progetto passa al formato 0.9 (`SGQ9`), che la 0.8 non legge più. Se pensi
di tornare alla 0.8, esporta prima i progetti sul Pi.

## 1. Compila in WSL

```sh
wsl -d Ubuntu2004
cd ~
cp /mnt/c/Users/user/Downloads/dinghy-sagga-0.9-src.tgz .
rm -rf dinghy-sagga-0.9
tar xzf dinghy-sagga-0.9-src.tgz
cd dinghy-sagga-0.9
sh tests/run_sagga_tests.sh
./build.sh --release 0.9
cp build/sagga-seq-0.9.fwsc /mnt/c/Users/user/Downloads/sagga-0.9.fwsc
cp tools/fm1_install.py /mnt/c/Users/user/Downloads/
```

I test devono finire tutti con `0 failures`. La riga `sagga plugins: skipped` va bene, perché serve una copia di
RaspiMIDIHub per quei test. `build.sh` deve dire `ok image` e non deve mostrare nessun `FAIL` su RAM e pool. Guarda anche la riga
`image ... B of ...`: la 0.9 è più grande della 0.8 (circa 20 KB di codice in più). Se supera lo slot, fermati e mandami
la riga.

## 2. Installa sull'FM-1

Collega l'FM-1 direttamente al PC e chiudi tutto ciò che può tenere occupata la porta MIDI (Ableton, il browser con
l'installer web, i MIDI monitor). Poi, in PowerShell:

```powershell
cd C:\Users\user\Downloads
py -3.12 .\fm1_install.py .\sagga-0.9.fwsc
```

Conferma con `y`. Dopo il riavvio lo schermo deve mostrare `SAGGA SEQ 0.9`.

## 3. Aggiorna il Raspberry Pi

Il bridge 0.9 serve per leggere i progetti `SGQ9` (la libreria rifiuterebbe i salvataggi nuovi) e per parlare con il
regista. Da PowerShell:

```powershell
cd C:\Users\user\Downloads
Expand-Archive .\sagga-0.9-pi.zip -DestinationPath . -Force
scp -r .\sagga-0.9-pi user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
rw
sudo systemctl stop sagga-grid-bridge
sudo mkdir -p /opt/sagga
sudo cp /tmp/sagga-0.9-pi/sagga_grid_bridge.py /tmp/sagga-0.9-pi/sagga-grid-bridge.service /opt/sagga/
sudo cp /opt/sagga/sagga-grid-bridge.service /etc/systemd/system/
sudo cp -r /tmp/sagga-0.9-pi/raspimidihub/sagga_remote /tmp/sagga-0.9-pi/raspimidihub/sagga_mutes /usr/lib/python3/dist-packages/raspimidihub/plugins/
sudo systemctl daemon-reload
sudo systemctl enable --now sagga-grid-bridge
sudo systemctl restart raspimidihub
ro
```

Il servizio è già scritto con `--model mini --frame`, quindi due Launchpad Mini rossi/verdi con quello sinistro ruotato
a cornice. Se le due metà risultano invertite, aggiungi `--swap` in fondo alla riga `ExecStart=` di
`/etc/systemd/system/sagga-grid-bridge.service`, poi esegui `sudo systemctl daemon-reload` e
`sudo systemctl restart sagga-grid-bridge` (tutto tra `rw` e `ro`).

Per controllare che funzioni: `journalctl -u sagga-grid-bridge -e`. Devi vedere le porte dei due Launchpad, la porta
dell'FM-1 e `bridge running`.

## 4. (Facoltativo) Le patch dei synth negli snapshot

Il bridge deve sapere quali synth chiamare. Copia l'esempio e modificalo con i tuoi synth:

```sh
sudo mount -o remount,rw /boot/firmware
sudo mkdir -p /boot/firmware/sagga
sudo cp /tmp/sagga-0.9-pi/patches.example.json /boot/firmware/sagga/patches.json
sudo nano /boot/firmware/sagga/patches.json
sudo mount -o remount,ro /boot/firmware
sudo systemctl restart sagga-grid-bridge
```

Per ogni synth servono tre campi:

* **`port`**: un pezzo del nome della sua porta MIDI. Per vedere i nomi: `python3 /opt/sagga/sagga_grid_bridge.py --list`.
* **`request`**: il messaggio SysEx con cui il synth manda la sua patch. Lo trovi nel manuale del synth, alla voce
  "MIDI implementation". Se non c'è, togli la riga: il bridge ascolta per 10 secondi e intanto tu fai "send patch" o
  "dump" dal synth.
* **`name`**: il nome con cui il file della patch viene salvato.

Il synth deve essere collegato al Pi. Il file si può modificare anche dal PC: è `sagga\patches.json` sulla partizione
piccola della scheda SD.

## 5. (Facoltativo) Due porte USB: tutti e 16 i canali per le tracce

Di base l'FM-1 ha una sola porta MIDI. In questo caso i canali 15 e 16 servono al grid, e le tracce usano i canali
1-14. Con due porte:

1. Sull'FM-1: tieni premuto **HOME + SEL** (la pagina USB), gira **K1** fino a `2` e premi **OCT+ due volte**.
   L'FM-1 si ricollega con due porte.
2. Il bridge prende da solo la porta 2: riavvialo con `sudo systemctl restart sagga-grid-bridge`, oppure aspetta che
   riparta da solo.
3. In RaspiMIDIHub, nella matrice, sono comparse **Felucca MIDI 1** e **Felucca MIDI 2**:
   * collega i synth alla **porta 1** (in entrambe le direzioni). Non serve più bloccare i canali 15 e 16;
   * collega i plugin **SAGGA Remote** e **SAGGA Mutes** alla **porta 2**;
   * premi Save Config.

La scelta resta salvata nell'FM-1. Per tornare a una porta sola: la stessa pagina, K1 su `1`, OCT+ due volte.

## 6. Primo controllo

1. Lo schermo, all'accensione, dice `SAGGA SEQ 0.9`, e il tuo ultimo progetto della 0.8 c'è ancora.
2. **SEL + PERF** (il tasto GLO): VIAGGIO. Tap sul **bianco 1**: lo schermo dice `T1 KICK P2 ...`. Poi **SEL + bianco
   1**, **nero 11 (NOW)**, **PLAY**: suona la cassa.
3. HOME, **OCT+** fino a `HOME 6/6 VIAGGIO`, **K2** due scatti indietro: frase di 4 battute. **SEL + bianco 2**: il
   rullante entra alla quarta battuta.
4. **K1** fino a 100: battuta dopo battuta suona più forte e più fitto. **OCT−**: alla fine della frase torna quella
   prima.
5. **SAVE + K4**: il profilo diventa `PALCO`. Prova SEQ + un tasto: lo schermo dice che non c'è in questo profilo.
   Ancora SAVE + K4: si torna a `FULL`.
6. Sul grid, **PERF** premuto tre volte: la vista VIAGGIO (pulsante nel colore accento).

Le note di rilascio (`RELEASE-NOTES-0.9.md`) elencano tutto il nuovo; il riferimento completo è `docs/SAGGA-SEQ.md`,
sezione VIAGGIO.
