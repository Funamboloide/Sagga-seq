# SAGGA HUB 0.1.1 (0.13: il BREAK IN SLICE; 0.14: l'editor dei progetti; 0.15: nome, Tape, segui e ascolta; 0.20.1: si aggiorna dalla sua pagina): la libreria firmware e i progetti su RaspiMIDIHub; l'expander dell'FM-1 (moduli pronti + software)

È un'aggiunta a RaspiMIDIHub, su qualunque Pi: la pagina web con i firmware dell'FM-1 (li carichi, li installi) e i
progetti esportati dal grid, il bridge dei Launchpad, l'M8 link e, volendo, una porta USB-MIDI verso il computer.
Si usa in due modi:

- **sul Pi 4 di casa, subito**: `sudo sh install_hub.sh --no-pc`. Nessun pezzo da comprare; la pagina è
  all'indirizzo del Pi, porta 8090. È tutto quello che serve finché si suona in casa.
- **come expander**: un Pi 3B sotto l'FM-1 che fa da hub a batteria: ospita i Launchpad e l'FM-1, porta il MIDI
  fuori su TRS, si presenta a un computer come interfaccia MIDI. Niente PCB: moduli che si comprano, un vassoio
  stampato (`case/sagga-hub-case.scad`), e lo stesso software (`sudo sh install_hub.sh`, con la porta PC).
  A casa l'expander si attacca al Pi 4 dalla sua porta PC e compare nella matrice come "SAGGA HUB 1/2".

## I pezzi (solo per l'expander)

| cosa | modello | note |
| --- | --- | --- |
| il cervello | **Raspberry Pi 3B** (quello liberato dal passaggio di RaspiMIDIHub al Pi 4) | 4 USB-A sue: FM-1, 2 Launchpad, MICROMIDITRS. Lo Zero 2 W è introvabile nel 2026; se ricompare (19,50 €) si scambia con la stessa SD, più il Waveshare USB HUB HAT (B) |
| MIDI TRS | **Denki Oto MICROMIDITRS-USB v2** (TRS OUT tipo A, TRS IN auto-sensing A/B, USB-C) | in una USB-A dell'hub con un cavo A→C corto; l'hub guadagna anche un MIDI IN TRS |
| porta PC | **Waveshare RP2040-Zero** | tre fili all'header del Pi (sotto), firmware `rp2040/` |
| batteria | powerbank piatto 10.000 mAh, uscita 5 V 3 A, **ricarica pass-through**, **modalità bassa corrente** | senza quelle due cose si spegne da solo o non carica mentre suona; con il 3B circa 4-6 ore |
| all'FM-1 | cavo USB-A → USB-C **con spina C ad angolo retto**, 25 cm | dall'hub alla presa dell'FM-1 |
| al Pi | cavo USB-A → micro-USB, 20-30 cm | dalla powerbank alla presa PWR del 3B |
| alla MICROMIDITRS | cavo USB-A → USB-C, 15-20 cm | |
| microSD | SanDisk 32 GB | RaspiMIDIHub + tutto questo |

## Installare il software (sul Pi, da SSH, una volta)

1. RaspiMIDIHub installato e funzionante (immagine o `install.sh` su Pi OS Lite).
2. Copia questo zip sul Pi (`scp sagga-hub-0.1.1.zip user@<ip del pi>:/tmp/`), poi:
   ```sh
   cd /tmp && unzip -o sagga-hub-0.1.1.zip && cd sagga-hub-0.1.1
   sudo sh install_hub.sh --no-pc     # il Pi 4 di casa, senza RP2040
   sudo sh install_hub.sh             # l'expander: anche la porta PC, poi: sudo reboot
   ```
   Lo script installa bridge dei Launchpad, M8 link, libreria firmware e, senza `--no-pc`, la porta PC con la
   UART per il RP2040 (console seriale spenta, Bluetooth spento: per questo serve il reboot). Serve internet la
   prima volta per i pacchetti Python (`python3-mido python3-rtmidi python3-serial python3-usb`): il tethering
   del telefono basta. Si può rilanciare dopo un aggiornamento: non rompe nulla.
3. Nella matrice di RaspiMIDIHub compaiono **SAGGAM8A / B** (le Brick) e, con la porta PC, **SAGGAPC1 / SAGGAPC2**
   (il computer): collega `Felucca MIDI 1 → SAGGAPC1` e `SAGGAPC1 → Felucca MIDI 1` e il computer vede l'FM-1
   come "SAGGA HUB 1".
4. La **libreria firmware**: `http://<ip del pi>:8090` (sull'expander `192.168.4.1`, dal telefono sul suo WiFi).
   Carichi i `.fwsc`, vedi quale firmware ha l'FM-1 collegato, premi *Installa*. Non spegnere durante la
   scrittura; se salta, ricollega e installa di nuovo: finisce il lavoro. *Elimina* (0.20.1) toglie un `.fwsc` dalla
   libreria del Pi (il firmware dell'FM-1 non cambia). I progetti esportati dal grid sono nella
   stessa pagina, da scaricare, **anche come `.mid`** (0.11: ogni progetto ha il suo link .mid). Dalla stessa pagina
   carichi un `.sgq` (torna nella libreria) o un **file MIDI**: diventa un progetto di tracce TAPE (un canale = una
   traccia, fino a 16 battute e 1536 note), da caricare sull'FM-1 dal grid (LIB) come gli altri. Tutto sta in
   `/boot/firmware/sagga/` (la partizione FAT: la SD letta da un computer li mostra come file normali).

## AGGIORNA IL PI (0.20.1)

Dalla 0.20.1 il Pi si aggiorna dalla stessa pagina (porta 8090), senza SSH: nella sezione **AGGIORNA IL PI** scegli
uno zip `sagga-hub-X.zip` e premi *Aggiorna il Pi*. La pagina lo controlla (una cartella sola `sagga-hub-X`, nessun
percorso che ne esce, nessun collegamento, dentro `install_hub.sh` e la pagina, e la pagina nuova deve essere Python
valido e sapersi aggiornare: uno zip più vecchio della 0.20.1 si installa solo da SSH), lo apre in `/run/sagga-update` e lancia `install_hub.sh` per conto suo, con `systemd-run` (lo script riavvia
la pagina stessa). Con `--no-pc`, a meno che la porta PC sia accesa su quel Pi. La pagina sparisce per qualche secondo
e torna con la versione nuova in alto (`SAGGA HUB 0.20.1`) e il log dell'installazione sotto il bottone; se qualcosa
non va il log dice dove (`exit N`). Non parte mentre l'FM-1 si sta installando, e l'FM-1 non si installa mentre il Pi
si aggiorna. Si riavvia anche RaspiMIDIHub: non farlo mentre suoni.

Lo può fare chi è sulla rete del Pi, come può installare un firmware: la password del WiFi è la chiave. La prima
volta (per avere questa pagina) si passa ancora da SSH.

Dalla 0.20.2 `install_hub.sh` gira in un servizio a parte anche da SSH: se il WiFi del Pi cade (succede quando
RaspiMIDIHub riparte, adesso alla fine) l'installazione finisce lo stesso. Il registro è in `/run/sagga-install.log`.

## ESPLORATORE DEL BANCO (0.20.3)

L'FM-1, il Pi e il grid provati insieme, per le strade vere (`docs/SAGGA-ESPLORATORE.md`, "Il banco"). Sulla pagina
(porta 8090):

* **Controlla la matrice**: le celle che servono (ogni pagina SAGGA verso la porta 2 dell'FM-1 e ritorno), quelle che
  non devono esserci (un Launchpad nella matrice, la porta 2 dell'FM-1 verso un synth), il Default routing, i servizi.
  Non cambia niente.
* **Avvia la prova** (tutte le sessioni, una ventina di minuti, o 4): serve SAGGA SEQ 0.20.3 sull'FM-1, fermo. La
  pagina chiede di premere SEL sull'FM-1 (0.20.4: il bridge resta acceso finché non dici sì, così lo schermo
  mostra la domanda; se nessuno risponde la domanda torna, fino a tre volte); poi l'FM-1 si riavvia nel suo test a ogni sessione (non toccarlo). Il Pi
  preme le pagine SAGGA dentro RaspiMIDIHub (con la sua API, come il tablet), fa girare il bridge del grid (il codice
  installato, con due Launchpad finti: il servizio del bridge è fermo durante la prova e riparte alla fine) e il
  pannello dell'FM-1 con il test. Con **stacca i synth** (di solito sì) le celle fra l'FM-1 e tutto quello che non è
  una pagina SAGGA sono tolte dalla matrice per la prova: i synth tacciono e niente di estraneo entra nell'FM-1.
  Tornano alla fine; l'elenco sta in `/boot/firmware/sagga/banco/celle-staccate.json` finché non sono tornate, e se
  la prova si interrompe la pagina offre **Rimetti le celle** (la prova dopo le rimette anche da sola). Alla fine il
  progetto che l'FM-1 aveva in memoria torna dov'era (`IMPORTED`: SAVE per tenerlo).
* Nella tendina, al posto del banco, **l'FM-1 completo** (`fm1_piano.json`, 28 sessioni, mezz'ora circa): le sessioni
  dell'esploratore dal PC (ogni situazione dell'FM-1, 60 gesti, il tablet e il grid come eventi del test), dal Pi,
  senza PC. Il resto uguale: SEL, le celle dei synth staccate, il progetto che torna in memoria.
* Il log sotto i bottoni; alla fine **raccolta-banco-...json**, **RAPPORTO-BANCO-...md** e il log si scaricano dalla
  pagina. Stanno in `/run/sagga-banco` e anche sulla SD (`/boot/firmware/sagga/banco`, le ultime tre prove). La
  raccolta si confronta con il simulatore: `python3 tests/sagga_explore.py --banco raccolta-banco-....json`.

La prova gira in un servizio a parte (`systemd-run`, come l'aggiornamento): se la pagina si riavvia va avanti. Mentre
gira l'FM-1 non si installa, il Pi non si aggiorna e l'editor non parla con l'FM-1. Da SSH:
`sudo python3 /opt/sagga/hub/sagga_banco.py [--piano /opt/sagga/hub/fm1_piano.json] [--solo-matrice] [--sessioni 4]
[--non-staccare] [--rimetti]`.

## L'EDITOR DEI PROGETTI (0.14)

Nella pagina (porta 8090), accanto a ogni progetto della libreria, **editor**: tutto il progetto su telefono o PC -
le 16 tracce con i loro step, lo step con note, velocity, gate, condizioni, ratchet, TIE, SLIDE e lock, le impostazioni
di ogni traccia, le lane disegnate col dito, le scene, la song, le catene, gli LFO, la chiave e il resto del progetto.
**Salva** lo riscrive nella libreria (la versione prima resta in `versioni/`, si ripristina dalla pagina); **Manda
all'FM-1** lo carica sull'FM-1 fermo (SAVE sull'FM-1 lo tiene). Sotto la lista dei progetti: **Nuovo** (un progetto
vuoto con il nome che scrivi) e **Ricevi dall'FM-1** (quello che l'FM-1 ha adesso). I progetti li legge e li scrive
`sagga_sgqjson`, compilato sul Pi dallo stesso codice del firmware: l'editor non può fare un progetto che l'FM-1 non
prende. Con il bridge del grid acceso l'hub chiede a lui (ha la porta dell'FM-1, file in `/run/sagga`); senza, usa
`sagga_grid_bridge.py --export / --import`.

0.15: nella scheda **Progetto** il **NOME** del progetto (fino a 16 caratteri: l'FM-1 lo mostra con SAVE + PRESETS e
quando carica uno slot; **Nuovo** lo prende dal nome del file). La scheda **Tape** è il piano roll delle tracce TAPE:
tocchi il vuoto e c'è una nota da un sedicesimo, la trascini per spostarla, dal bordo destro la allunghi, Canc la toglie;
battute e quantize del loop sulla stessa riga. Nella scheda **Traccia** il **GROOVE** (il template e quanto). In alto:
**segui l'FM-1** (mentre suona, lo step di ogni traccia ha una cornice bianca, il Tape una linea che corre) e
**ascolta** (lo step che accendi, la nota del roll che tocchi la suona l'FM-1 su quella traccia; nello step c'è anche
**♪ ascolta**). Segui e ascolta passano dal bridge del grid: deve essere acceso, con l'FM-1 collegato. Dalla 0.15 il
bridge gira anche senza i Launchpad (per la libreria e l'editor) e riparte da solo, col grid, quando li attacchi.

## BREAK IN SLICE (0.13)

Nella stessa pagina (porta 8090) la sezione **BREAK IN SLICE**: carichi un loop di batteria in WAV (PCM 8, 16, 24, 32 bit
o float 32, mono o stereo, fino a 64 secondi), scegli 8, 16 o 32 slice e premi *Taglia*: il Pi trova dove comincia il
break (il silenzio prima va via), quante battute sono e il tempo (una potenza di due di battute fra 90 e 180 BPM; se è
un break lento o veloce scrivi tu BPM o battute), taglia sulla griglia dei sedicesimi e sposta ogni taglio sul colpo
vicino, a un passaggio per lo zero, con una dissolvenza di 3 ms in coda. Torna uno zip:

- `01.wav` .. `16.wav`: le slice, nel formato del file (l'8 bit diventa 16);
- `<nome>-loop.wav`: il loop dal primo colpo, con un cue su ogni slice (i campionatori che leggono i cue lo affettano da soli);
- `<nome>.sfz`: le slice sulle note dalla prima in su (C1 = 36, o quella che scrivi), una alla volta: la nuova taglia
  quella che suona. sfizz (lo Zynthian), Sforzando e gli altri lettori SFZ lo caricano così com'è;
- `LEGGIMI.txt`: tempo, battute, dove comincia ogni slice e cosa impostare sull'FM-1 (una traccia BREAK, la sua PEN = la
  prima nota, SEQ 7 SLICES).

Lo stesso da un terminale, anche sul PC: `python3 sagga_slicer.py amen.wav --slices 16 [--bpm 136] [--pen 36]`.

## Il RP2040-Zero (porta PC, solo per l'expander o se vuoi collegare un computer al Pi 4 senza passare dall'FM-1)

Firmware in `rp2040/`: si compila su WSL con il Pico SDK (`rp2040/README.md`, cinque comandi) e si copia il `.uf2`
sulla schedina tenendo premuto BOOT. Fili: GP0 → pin 10 del Pi, GP1 → pin 8, GND → pin 6 (stessi pin su 3B e Zero;
l'installatore spegne il Bluetooth, che sul 3B usa quella UART). Il LED: verde quando
arriva dal computer, blu dal Pi, rosso se la UART trabocca.

## Il vassoio

`case/sagga-hub-case.scad`: in testa al file ci sono le misure da sostituire (l'FM-1, la powerbank, la MICROMIDITRS,
la posizione della USB-C dell'FM-1). Il 3B poggia su quattro perni nei suoi fori M2.5, con le USB-A verso la parete
sinistra: lì una finestra per i cavi dei Launchpad, e nell'incavo davanti alle porte si infilano anche i cavi interni.
Sul retro: USB-C del RP2040 (porta PC), i due jack TRS. Sulla parete della powerbank (`pb_wall`): la finestra della
sua presa di ricarica, così si carica senza aprire nulla, e il foro del pulsante. L'FM-1 appoggia sopra e chiude il
vassoio; la spina ad angolo scende dentro da una fessura nel bordo. Se i moduli chiedono più spazio dell'impronta
dell'FM-1 il vassoio cresce da solo (lo dice la console di OpenSCAD).

## Cosa non c'è (ancora)

L'audio: l'FM-1 manda il suo audio via USB al Pi, quindi registrarlo si può; l'ingresso audio analogico e l'audio
dell'FM-1 verso il computer no. La porta PC porta MIDI, non audio.

## Test

`python3 tests/sagga_hub_tests.py` nel repository: pacchetti USB-MIDI e SLIP (anche contro il C del RP2040), il link
della porta PC su una pseudo-seriale, la pagina dei firmware con un installatore finto, l'aggiornamento del Pi, la
sezione del banco. `python3 tests/sagga_banco_tests.py`: il programma del banco contro un FM-1, un RaspiMIDIHub e un
systemctl finti.
