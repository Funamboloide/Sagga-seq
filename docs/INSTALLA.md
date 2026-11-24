# SAGGA SEQ - Installare e aggiornare

SAGGA SEQ è fatto di tre pezzi, e si installa con **due file**:

| il pezzo | il file | dove va |
| --- | --- | --- |
| **l'FM-1** (il sequencer, e il cervello del grid) | `sagga-X.fwsc` | nell'FM-1, dalla pagina del Pi |
| **il Pi** (la pagina, l'editor, la libreria, le pagine SAGGA di RaspiMIDIHub, il custode delle celle) | `sagga-hub-X.zip` | nel Pi |
| **il grid** (i due Launchpad) | lo stesso `sagga-hub-X.zip`: il bridge dei Launchpad è lì dentro | nel Pi |

I due file vanno **della stessa versione**, con una eccezione: **la 0.32.2 e la 0.32.3 sono solo del Pi** (e la 0.32.4 e la
0.32.5 solo degli effetti del live: FIGO, SCENA, le VARIAZIONI della Gills). L'FM-1 resta
alla 0.32.1 (`sagga-0.32.1.fwsc`, quello che hai già dentro) e sul Pi va `sagga-hub-0.32.3.zip`. Il manuale d'uso è il documento
"SAGGA SEQ 0.32 — Il manuale" (vale per la 0.32.1); il riferimento
completo di ogni comando è [SAGGA-SEQ.md](SAGGA-SEQ.md); il grid è in [SAGGA-GRID.md](SAGGA-GRID.md); la pagina del Pi
in `tools/hub/LEGGIMI.md` (nello zip: `LEGGIMI.md`).

## Aggiornare (il caso normale)

Il tablet o il telefono sulla rete del Pi (`RaspiMIDIHub-XXXX`), la pagina `http://192.168.4.1:8090` (l'indirizzo del
Pi, porta 8090). Non mentre suoni: l'FM-1 si riavvia, e si riavvia anche RaspiMIDIHub.

1. **Il Pi**: **AGGIORNA IL PI**, scegli `sagga-hub-X.zip`, **Aggiorna il Pi**, conferma. La pagina sparisce per qualche
   secondo e torna con `SAGGA HUB X` in alto e il registro dell'installazione sotto il bottone, che finisce con
   `exit 0`.
2. **L'FM-1**: fermo (non in PLAY), collegato al Pi. **FIRMWARE**: carica `sagga-X.fwsc`, **Installa**. Non staccare il
   cavo. L'FM-1 si riavvia e lo schermo dice `SAGGA SEQ X` per tre secondi.
3. **Guarda** la sezione **LE CELLE DELL'FM-1**: dice se il Pi ha dovuto rimettere dei collegamenti fra l'FM-1 e le
   pagine dopo il riavvio (RaspiMIDIHub 6 li perde quando un dispositivo manca mentre salva: il Pi li rimette da solo).

I progetti negli slot dell'FM-1 e nella libreria del Pi restano. Il formato dei progetti è `SGQB` dalla 0.10. Si
possono saltare le versioni (dalla 0.27 alla 0.32 in un colpo, per esempio): valgono tutte le note qui sotto.
**Dalla 0.28** le tracce sono dodici: un progetto di prima si apre con le sue prime dodici tracce. Se torni alla 0.27,
apre i progetti della 0.28, senza le note 5-6 e le lane 7-8.
**Dalla 0.29** i generi sono 22: un progetto di prima si apre con ogni genere dove è andato (AMAPIANO come REGGAETON,
BASSLINE come UK GARAGE, GRIME come DUBSTEP, AFRO HOUSE come GQOM). Se torni alla 0.28, apre i progetti della 0.29:
BALANI come AFRO HOUSE, il BALAFON come un LEAD, PROG 7 e 8 come PROG 1, senza ROLL e ACCENT; le scale, i groove e le
forme d'accordo nuove tornano a quelle di partenza. Sul Pi i pattern e le progressioni che avevi salvato nei generi
tolti passano nei generi dove sono andati.
**Dalla 0.30** le scene sono 32, le snapshot 16, la song ha 128 entrate e le TAPE 3072 eventi: i progetti di prima si
aprono come erano. Se torni alla 0.29, apre i progetti della 0.30 con le prime 16 scene, 8 snapshot, 64 entrate e 1536
eventi. All'accensione l'FM-1 rimette anche i mute e la scena del progetto salvato (fino alla 0.29 solo il LOAD lo
faceva).
**Dalla 0.31** i tasti che erano delle tracce 13-16 sono i quattro gruppi (batteria, bassi, melodiche, tutte) e un LFO
può muovere un gruppo: i progetti di prima si aprono come erano. Se torni alla 0.30, apre i progetti della 0.31; un LFO
messo su un gruppo lo trova spento, sulla traccia 1.
**Dalla 0.32** i tasti e i pad che non facevano niente hanno un lavoro, e la manopola MASTER può muovere l'ENERGIA: i
progetti di prima si aprono come erano. Se torni alla 0.31, apre i progetti della 0.32; la manopola messa sull'ENERGIA
la trova sul TEMPO. La libreria del Pi mostra sul grid fino a 112 file (erano 64): aggiorna il Pi insieme all'FM-1.
**Dalla 0.32.1** la pagina SAGGA Remote arriva alle 32 scene e alle 16 snapshot (le manopole SCENES e SNAPS): mandano
numeri che solo l'FM-1 0.32.1 capisce, quindi aggiorna tutti e due. I progetti non cambiano.
**La 0.32.2 è solo del Pi**: fai solo il passo 1 (`sagga-hub-0.32.2.zip`); l'FM-1 non si tocca. Il bridge del grid si
ferma sempre quando deve (una prova del banco poteva lasciarlo fermo, con il grid spento fino al riavvio del Pi), la
domanda `PC TEST? SEL = YES` della prova resta sullo schermo, e le prove non lasciano più un progetto in più nella
libreria. Durante questo aggiornamento il Pi può metterci fino a un quarto di minuto in più: sta fermando il bridge
vecchio.
**La 0.32.3 è solo del Pi** anche lei: fai solo il passo 1 (`sagga-hub-0.32.3.zip`). Porta **DA ABLETON** sulla pagina:
i clip MIDI esportati da Ableton diventano un progetto a passi, ogni parte sul canale della sua macchina. Controlla la
tabella dei canali in quella sezione la prima volta (deve essere come la matrice di RaspiMIDIHub).
**La 0.32.4 non tocca né l'FM-1 né il Pi**: cambiano solo gli effetti del live. Su norns copia il nuovo `figo.lua`
(`tools/norns/figo/README.md`), sulla Gills carica `scena_aux.axp` se la usi su un bus o `scena.axp` in insert
(`tools/gills/LEGGIMI.md`).
**La 0.32.5 è solo della Gills**: FIGO e SCENA insieme (VARIAZIONI). Sul bus carica la patch del tuo effetto con le
variazioni (`microcosm_figo_scena.axp` o `chroma_console_figo_scena.axp`, fatte da `tools/gills/make_bus.py` dalle tue
patch), o `figo_scena_aux.axp` da sola. La prima volta con **Live**, guardando il carico DSP; poi **Upload to Internal
Flash** (`tools/gills/LEGGIMI.md`). L'FM-1, il Pi e norns restano come sono.

## La prima volta sul Pi

Serve RaspiMIDIHub già installato e funzionante, e una volta sola un terminale sul Pi (SSH: dal PC, o da un tablet
Android con Termux, quello di GitHub, `pkg install openssh`). Da lì in poi il Pi si aggiorna dalla sua pagina.

```sh
scp sagga-hub-X.zip user@192.168.4.1:/tmp/
ssh user@192.168.4.1
cd /tmp && unzip -o sagga-hub-X.zip && cd sagga-hub-X
sudo sh install_hub.sh --no-pc
```

* `--no-pc` è per un Pi qualunque. Senza `--no-pc` lo script prepara anche la porta PC dell'expander (un RP2040-Zero
  sulla UART: spegne il Bluetooth e la console seriale, vuole un riavvio): solo se quel pezzo c'è (`LEGGIMI.md`).
* Lo script deve dire `sagga_sgqmid built`, `sagga_sgqjson built` e `the SAGGA pages installed in ...`. La prima volta
  gli serve internet per quattro pacchetti Python (il tethering del telefono basta); se dice `apt failed` ma le righe
  `built` ci sono, quei pacchetti c'erano già.
* Alla fine RaspiMIDIHub si riavvia (il suo WiFi può cadere per qualche secondo: l'installazione finisce lo stesso, il
  registro è in `/run/sagga-install.log`).

Poi, nell'interfaccia di RaspiMIDIHub: **aggiungi le pagine SAGGA che vuoi** (SAGGA Live, Remote, Mutes, Motori, Break,
Mod; SAGGA BeatStep se hai una BeatStep Pro). **I collegamenti fra le pagine e l'FM-1 li mette il Pi**: qualche secondo
dopo che hai aggiunto una pagina (con l'FM-1 acceso e USB PORTS 2), **LE CELLE DELL'FM-1** dice `pagina nuova,
collegata`: il suo OUT verso la porta 2 dell'FM-1 (`Felucca MIDI 2`), la porta 2 verso il suo IN. Lo fa una volta per
pagina: se poi togli una cella a mano, resta tolta. A mano restano i synth (l'uscita `Felucca MIDI 1` verso ognuno) e,
per SAGGA BeatStep, la BeatStep Pro verso il suo IN.

## La prima volta sull'FM-1

Come un aggiornamento: dalla pagina del Pi, **FIRMWARE**, carica `sagga-X.fwsc`, **Installa**. Oppure dal computer, con
il cavo nell'FM-1: `py fm1_install.py sagga-X.fwsc` (Windows) o `python3 fm1_install.py sagga-X.fwsc`. L'installatore
controlla il pacchetto prima di scrivere: un file danneggiato, o che non è per l'FM-1, viene rifiutato e la memoria non
si tocca.

Dopo il primo avvio, due impostazioni (tieni SAVE):

* **SAVE 3 K1 = USB PORTS 2**, poi **SEL + K1 due volte** (riconnette senza staccare il cavo): la porta 1 porta i synth,
  la porta 2 il grid, le pagine e il Pi. Serve per il grid, per le pagine e per l'editor.
* **SAVE 1 K2 = REMOTE 13 + 14**: le pagine SAGGA parlano sui canali 12, 13 e 14 della porta 2.

## Il grid

Due Launchpad nelle USB del Pi: il bridge (`sagga-grid-bridge`, installato con lo zip) li trova da solo, li mette uno
accanto all'altro (16 x 8) e li collega alla porta 2 dell'FM-1. Niente da collegare nella matrice di RaspiMIDIHub: i
Launchpad parlano solo con il bridge. Quali Launchpad, come si accendono, tutte le viste: [SAGGA-GRID.md](SAGGA-GRID.md).
Se l'FM-1 o un Launchpad non c'è, il bridge aspetta in silenzio e riparte da solo quando torna. Se i Launchpad sono
spenti, il bridge è fermo: succede durante la prova del banco (alla fine riparte) e quando spegni il Pi.

## Controllare che sia tutto a posto

1. Lo schermo dell'FM-1 all'accensione: `SAGGA SEQ X`. La pagina del Pi in alto: `SAGGA HUB X`. Lo stesso numero.
2. PLAY: la prima riga dice `RUN 128`. Un bianco: uno step acceso, il synth sul canale della traccia suona.
3. Una pagina SAGGA sul tablet (per esempio SAGGA Live): gira TRACK, lo schermo dell'FM-1 dice `TAB T..`; gira una
   manopola sull'FM-1 (PERF, K4: QUANTISE), sulla pagina SAGGA Remote si muove da sola.
4. I Launchpad si accendono e la griglia mostra la traccia selezionata sull'FM-1.
5. Se vuoi una prova completa: sulla pagina del Pi, **ESPLORATORE DEL BANCO** (`SAGGA-ESPLORATORE.md`): il Pi suona
   l'FM-1, le pagine e il grid per una mezz'ora e confronta tutto con il simulatore.

## Se qualcosa non va

* La pagina del Pi non si apre: sei sulla rete del Pi? L'indirizzo è quello del Pi, porta 8090.
* `AGGIORNA IL PI` rifiuta lo zip: dice perché (deve essere un `sagga-hub-X.zip`, non il sorgente).
* Le pagine non comandano l'FM-1, o l'FM-1 non muove le pagine: **LE CELLE DELL'FM-1** sulla pagina del Pi dice quali
  collegamenti ci sono e quali ha rimesso; sull'FM-1 controlla USB PORTS 2 e REMOTE 13 + 14.
* Il grid non si accende, o fa cose strane: sulla pagina del Pi premi **Controlla la matrice** (qualche secondo). Il
  suo file dice anche cosa ha detto il bridge: le porte che ha preso, se aspetta l'FM-1, perché si è fermato. Dalla
  0.32.2, se il bridge è fermo lo fa ripartire, e lo dice: non serve riavviare il Pi.
* Un'installazione dell'FM-1 interrotta (il cavo staccato, il Pi spento): l'FM-1 resta in modalità di aggiornamento
  finché non è finita. Ricollega il cavo e premi di nuovo **Installa**: riprende da capo e finisce.
* L'FM-1 non parte più: spegnilo, tieni **OCT-** mentre lo accendi. È il soccorso USB: prende sempre un firmware nuovo
  (dalla pagina del Pi o da `fm1_install.py`).

## Compilare da sé

Il firmware si compila su GitHub a ogni push (Actions, "build firmware"); il pacchetto finisce nel ramo `pacchetti`
con `fm1_install.py`. Lo zip del Pi e il sorgente: `sh tools/make_release.sh X`. I test, tutti, su un computer senza
FM-1: `sh tests/run_sagga_tests.sh`.

Le versioni passate, con le loro note e i loro fogli di installazione: [storia/](storia/).
