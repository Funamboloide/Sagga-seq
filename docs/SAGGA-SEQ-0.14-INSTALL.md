# SAGGA SEQ 0.14 - Installazione

Ti servono due file nei Download di Windows (li fa `sh tools/make_release.sh 0.14`, e sono allegati al rilascio):

* `sagga-seq-0.14-source.zip`: il sorgente del firmware (e di tutto il resto);
* `sagga-hub-0.14.zip`: il bridge dei Launchpad, l'hub (pagina 8090, **con l'editor dei progetti** e il BREAK IN SLICE), i
  convertitori, i cinque plugin e le librerie del Pi, per il Raspberry Pi.

**Il formato.** La 0.14 scrive e legge `SGQB` come la 0.12 e la 0.13: slot, file `.sgq`, snapshot e libreria del Pi si
aprono così come sono.

**Cosa cambia.** Sull'FM-1 solo una cosa: caricare uno slot vuoto (HOME + SAVE due volte) dà un **progetto nuovo**. Sul
Pi c'è l'**editor dei progetti** nella pagina dell'hub. La tabella completa è in `docs/SAGGA-SEQ.md`, "What is new in
0.14".

## 1. Compila in WSL

```sh
wsl -d Ubuntu2004
cd ~
rm -rf sagga-seq-0.14-source
unzip -q /mnt/c/Users/user/Downloads/sagga-seq-0.14-source.zip
cd sagga-seq-0.14-source
sh tests/run_sagga_tests.sh
./build.sh --release 0.14
cp build/sagga-seq-0.14.fwsc /mnt/c/Users/user/Downloads/sagga-0.14.fwsc
cp tools/fm1_install.py /mnt/c/Users/user/Downloads/
```

I test devono finire tutti con `0 failures`. Ci sono due righe nuove: `sagga editor: ... 0 failures` e, senza
playwright in WSL, la pagina dell'editor saltata. `build.sh` deve dire `ok image`. Rispetto alla 0.13 (`image 361096`,
`RAM 63376`, `pool 322356`) le tre cifre devono restare quasi uguali: qualche decina di byte di codice in più, RAM e pool
uguali. L'identità del pacchetto è `FM-1_964`.

## 2. Installa sull'FM-1

Collega l'FM-1 direttamente al PC e chiudi tutto ciò che può tenere occupata la porta MIDI (Ableton, il browser con
l'installer web, i MIDI monitor). Poi, in PowerShell:

```powershell
cd C:\Users\user\Downloads
py -3.12 .\fm1_install.py .\sagga-0.14.fwsc
```

Conferma con `y`. Dopo il riavvio lo schermo deve mostrare `SAGGA SEQ 0.14`. Oppure dal Pi: carica il `.fwsc` nella
pagina dell'hub (`http://<ip del pi>:8090`) e premi *Installa*.

## 3. Aggiorna il Raspberry Pi

Serve per l'editor (il bridge, l'hub e il convertitore nuovo). Da PowerShell:

```powershell
cd C:\Users\user\Downloads
scp .\sagga-hub-0.14.zip user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.14.zip && cd sagga-hub-0.14
sudo sh install_hub.sh --no-pc        # il Pi 4 di casa; sull'expander con il RP2040: senza --no-pc, poi sudo reboot
```

Lo script deve dire `sagga_sgqmid built` **e** `sagga_sgqjson built`. Riavvia da solo hub e bridge; le tue librerie in
`/boot/firmware/sagga/` non le tocca.

## 4. Primo controllo

1. All'accensione lo schermo dice `SAGGA SEQ 0.14`; i tuoi slot si caricano come prima.
2. **Progetto nuovo:** SAVE tenuto + PRESETS su uno slot che dice `EMPTY`, lascia SAVE. HOME + SAVE: `LOAD SLOT n EMPTY:
   AGAIN = NEW PROJECT`; HOME + SAVE di nuovo: `NEW PROJECT: SAVE PUTS IT IN SLOT n`. PLAY: silenzio. Scrivi due step,
   SAVE due volte: è nello slot.
3. **L'editor:** `http://<ip del pi>:8090`, sotto PROGETTI scrivi un nome e premi **Ricevi dall'FM-1** (FM-1 fermo): si
   apre l'editor con il tuo progetto. Nella scheda Tracce tocca qualche step, cambia una velocity, **Salva**.
4. **Manda all'FM-1:** dall'editor, a FM-1 fermo. PLAY sull'FM-1: ci sono gli step di prima. SAVE sull'FM-1 se vuoi
   tenerlo nello slot.
5. **Versioni:** il menu "versioni" ha quella di prima del salvataggio; **Ripristina** la riporta.
6. Dal telefono, stessa pagina: la scheda **Lane** si disegna col dito.

Poi il test hardware (`tools/hwtest`: `run_hw_test.ps1` da PowerShell, con l'FM-1 direttamente sul PC) per il
controllo completo del timing: deve dire `0 failures`.

## 5. L'esploratore sull'FM-1

Come per la 0.12 (`tools/hwtest/LEGGIMI.md`): il PC preme i tasti dell'FM-1 per venti minuti e poi confronta tutto con
il simulatore. In WSL:

```sh
cd ~/sagga-seq-0.14-source
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

Le note di rilascio (`RELEASE-NOTES-0.14.md`) elencano tutto il nuovo; il riferimento completo è `docs/SAGGA-SEQ.md`.
