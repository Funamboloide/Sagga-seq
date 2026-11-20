# SAGGA HUB: il Pi di SAGGA SEQ - la pagina (firmware, progetti, editor, aggiornamento, custode delle celle) su RaspiMIDIHub, il bridge del grid, e l'expander dell'FM-1 (moduli pronti + software)

Installare e aggiornare, in breve: `docs/INSTALLA.md` del repository (questo file è il dettaglio del Pi).

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
* **Avvia la prova** (tutte le sessioni - 31 dalla 0.31, circa ventisei minuti - o 4): serve SAGGA SEQ 0.20.3 sull'FM-1, fermo. La
  pagina chiede di premere SEL sull'FM-1 (0.20.4: il bridge resta acceso finché non dici sì, così lo schermo
  mostra la domanda; se nessuno risponde la domanda torna, fino a tre volte); poi l'FM-1 si riavvia nel suo test a ogni sessione (non toccarlo). Il Pi
  preme le pagine SAGGA dentro RaspiMIDIHub (con la sua API, come il tablet), fa girare il bridge del grid (il codice
  installato, con due Launchpad finti: il servizio del bridge è fermo durante la prova e riparte alla fine - **i
  Launchpad veri in quel tempo sono spenti (dalla 0.23.2; prima restavano accesi e fermi) e l'FM-1 dice GRID LOST: è
  giusto così**, tornano a fine prova) e il
  pannello dell'FM-1 con il test. Con **stacca i synth** (di solito sì) le celle fra l'FM-1 e tutto quello che non è
  una pagina SAGGA sono tolte dalla matrice per la prova: i synth tacciono e niente di estraneo entra nell'FM-1.
  Tornano alla fine; l'elenco sta in `/boot/firmware/sagga/banco/celle-staccate.json` finché non sono tornate, e se
  la prova si interrompe la pagina offre **Rimetti le celle** (la prova dopo le rimette anche da sola). Alla fine il
  progetto che l'FM-1 aveva in memoria torna dov'era (`IMPORTED`: SAVE per tenerlo).
* Nella tendina, al posto del banco, **l'FM-1 completo** (`fm1_piano.json`, 36 sessioni dalla 0.31 - con le cose della 0.28, della 0.29, della 0.30 e della 0.31 -, mezz'ora abbondante): le sessioni
  dell'esploratore dal PC (ogni situazione dell'FM-1, 60 gesti, il tablet e il grid come eventi del test), dal Pi,
  senza PC. Il resto uguale: SEL, le celle dei synth staccate, il progetto che torna in memoria.
* **I conti** (0.23.1, con SAGGA SEQ 0.23.1 sull'FM-1): l'FM-1 conta quello che manda sull'USB, porta per porta e
  tipo per tipo (tick del clock, note, note-off, CC, il resto, i byte). Il Pi glielo chiede prima di ogni sessione e
  dopo, quando l'FM-1 è fermo e zitto, e lo confronta con quello che ha sentito lui e con quello che ha ricevuto il
  suo driver USB (`/proc/asound/cardN/midi0`). Se i numeri sono uguali non dice niente. Se un messaggio manca, la riga
  della sessione nel log dice `CONTI:` con quanti, di che tipo e **dove si sono persi**: dentro l'FM-1 (i suoi stessi
  conti non tornano, o dice di averne scartati), fra l'FM-1 e il Pi (al driver mancano dei byte), o nel Pi dopo il
  driver (il driver li ha tutti, il programma no). Con ogni sessione restano nella raccolta anche le righe del kernel
  sull'USB di quei secondi. La prova dura una ventina di secondi in più.
* Il log sotto i bottoni; alla fine **raccolta-banco-...json**, **RAPPORTO-BANCO-...md** e il log si scaricano dalla
  pagina. Stanno in `/run/sagga-banco` e anche sulla SD (`/boot/firmware/sagga/banco`, le ultime tre prove). La
  raccolta si confronta con il simulatore: `python3 tests/sagga_explore.py --banco raccolta-banco-....json`.

La prova gira in un servizio a parte (`systemd-run`, come l'aggiornamento): se la pagina si riavvia va avanti. Mentre
gira l'FM-1 non si installa, il Pi non si aggiorna e l'editor non parla con l'FM-1. Da SSH:
`sudo python3 /opt/sagga/hub/sagga_banco.py [--piano /opt/sagga/hub/fm1_piano.json] [--solo-matrice] [--sessioni 4]
[--non-staccare] [--rimetti]`.

## LE CELLE DELL'FM-1 (0.20.9)

RaspiMIDIHub 6 perde le celle di un dispositivo che non c'è: il suo salvataggio automatico (ogni 15-30 secondi quando
qualcosa cambia, e le pagine SAGGA cambiano sempre) scrive solo le celle dei dispositivi presenti, e se in quel secondo
l'FM-1 si riavvia o è spento le sue celle spariscono. La pagina del Pi ha un **custode** (`sagga_celle.py`): finché
l'FM-1 c'è ricorda le sue celle (le pagine, i synth, i filtri e le mappature) in `/boot/firmware/sagga/celle-fm1.json`;
quando l'FM-1 (o l'altro capo di una cella) se ne va e torna - il suo numero USB cambia ogni volta - aspetta 5 secondi
che RaspiMIDIHub faccia il suo e rimette quelle che mancano. Una cella tolta con l'FM-1 acceso resta tolta; con l'FM-1
spento torna. **Una pagina SAGGA nuova viene collegata da sola** (0.21): quando la aggiungi in RaspiMIDIHub, o tutte
la prima volta, il custode mette le sue due celle (il suo OUT verso la porta 2 dell'FM-1, la porta 2 verso il suo IN;
per SAGGA BeatStep solo l'OUT), una volta sola, con USB PORTS 2 sull'FM-1: se poi le togli a mano restano tolte. Sulla
pagina, **LE CELLE DELL'FM-1** dice cosa ha rimesso; durante la prova del banco aspetta. Per spegnerlo:
`--senza-custode` in `sagga-fw.service`.

Il banco, dalla 0.20.9, fa lo stesso a ogni riavvio dell'FM-1; se l'FM-1 non risponde per 12 secondi lo fa ritrovare
all'USB; scrive nel log le righe del kernel e i contatori dell'FM-1; e se l'FM-1 non torna mette il progetto di prima
della prova nella libreria (`prima-del-banco-<data>.sgq`: PROGETTI, editor, Manda all'FM-1).

## IL PI NON DISTURBA LA MUSICA (0.23.2)

RaspiMIDIHub rifà tutta la sua matrice ogni volta che sul Pi un programma apre o chiude una porta MIDI (per ALSA: un
client che arriva o se ne va). Chiude le note che stanno suonando, stacca ogni collegamento, guarda i dispositivi e
ricollega: per un momento niente passa. E un programma che chiede l'elenco delle porte MIDI ne apre e chiude due.
Fino alla 0.23.1 tre cose di SAGGA lo facevano anche mentre suonavi:

* **la pagina del Pi** chiedeva all'FM-1 chi è (per scrivere `FM-1_973` in alto) la prima volta che la aprivi, e poi
  ogni dieci minuti finché restava aperta: ogni volta una mezza dozzina di client. Adesso lo chiede un pezzo del
  servizio per conto suo, **solo quando l'FM-1 è appena tornato** (acceso, riavviato, aggiornato: lo vede dal suo
  numero USB, senza aprire niente). Aprire la pagina non chiede più niente a nessuno. Un FM-1 che c'è e non risponde
  ancora viene richiamato dopo 6, 20 e 60 secondi, poi basta;
* **il bridge senza i due Launchpad** guardava le porte ogni 3 secondi, per vedere se erano arrivati: la matrice
  rifatta ogni 3 secondi. Adesso guarda `/proc` (non apre niente) e chiede le porte solo quando un dispositivo è
  arrivato o se n'è andato;
* **il bridge senza l'FM-1** finiva, e il servizio lo faceva ripartire ogni 2 secondi, ogni volta con uno sguardo alle
  porte. Adesso aspetta lì, fermo (`no FM-1 ...: the bridge waits for it`).

E una quarta, solo per chi tiene le patch dei synth con gli snapshot (`patches.json`): a ogni snapshot che tornava con
le sue patch il bridge apriva e chiudeva la porta di ogni synth, in mezzo alla musica. Adesso le porte dei synth le
apre quando parte (o quando attacchi il synth) e le tiene aperte.

In più il bridge **si accorge di un FM-1 che si riavvia in mezzo secondo**. Guardava i client ALSA una volta al
secondo, per numero e nome; l'FM-1 torna in 0,44 secondi con lo stesso numero e lo stesso nome (lo dice il log della
tua prova): il bridge restava lì collegato a niente, il grid morto finché qualcosa non lo faceva ripartire. Adesso
guarda anche i suoi collegamenti (`/proc/asound/seq/clients` li elenca porta per porta) e riparte se non ci sono più.
E un bridge che viene fermato (lo fa la prova del banco, e lo spegnimento del Pi) **spegne i Launchpad** e avvisa
l'FM-1: prima il grid restava acceso e fermo, e sembrava vivo.

**0.25: mentre aggiorni l'FM-1 il Pi lo lascia in pace.** Durante un aggiornamento l'FM-1 è un altro dispositivo,
"Felucca Update": il suo programma di caricamento. Fino alla 0.24 il bridge e il custode delle celle lo prendevano per
l'FM-1: il bridge si attaccava e gli mandava il suo saluto ogni secondo per tutta l'installazione (si vede nel log di
un'installazione vera). Adesso il caricatore non è l'FM-1: il bridge aspetta (`no FM-1 ...: the bridge waits for it`)
e torna quando l'FM-1 riparte con il firmware nuovo.

Quello che resta: quando attacchi o stacchi un dispositivo USB (un Launchpad, un synth, l'FM-1), RaspiMIDIHub rifà la
matrice, e il bridge riparte. È di RaspiMIDIHub, e succede in un momento in cui hai le mani sui cavi.

**Come sta il bridge.** *Controlla la matrice* (qualche secondo) e la prova del banco scrivono nel loro file anche le
ultime righe del bridge: le porte che ha preso, se aspetta l'FM-1, se gira senza i Launchpad, perché si è fermato. Alla
fine della prova, anche quello che dice quando riparte. Se il grid fa qualcosa di strano, quel file dice cosa.

**L'orologio del Pi.** Un Pi non ha orologio: senza internet resta indietro (i file della prova del 17 novembre 2026
portano la data del 26 ottobre), e dopo uno spegnimento può ripartire da un'ora già passata. I file della prova e le
versioni dell'editor prendono il nome dall'ora, e venivano ordinati per nome: una versione salvata "adesso" poteva
contare come la più vecchia ed essere buttata. Dalla 0.23.2 il nome di una versione è sempre dopo quello della più nuova che c'è, e della
prova appena fatta i file sulla SD restano sempre (con le due più nuove delle altre). Le date che leggi restano quelle
dell'orologio del Pi: sbagliate, ma in ordine.

## L'EDITOR DEI PROGETTI (0.14)

Nella pagina (porta 8090), accanto a ogni progetto della libreria, **editor**: tutto il progetto su telefono o PC -
le tracce con i loro step (0.28: dodici), lo step con note (fino a sei), velocity, gate, condizioni, ratchet, TIE, SLIDE e lock, le impostazioni
di ogni traccia, le lane disegnate col dito, le scene, la song, le catene, gli LFO, la chiave e il resto del progetto.
**Salva** lo riscrive nella libreria (la versione prima resta in `versioni/`, si ripristina dalla pagina); **Manda
all'FM-1** lo carica sull'FM-1 fermo (SAVE sull'FM-1 lo tiene). Sotto la lista dei progetti: **Nuovo** (un progetto
vuoto con il nome che scrivi) e **Ricevi dall'FM-1** (quello che l'FM-1 ha adesso). I progetti li legge e li scrive
`sagga_sgqjson`, compilato sul Pi dallo stesso codice del firmware: l'editor non può fare un progetto che l'FM-1 non
prende. Con il bridge del grid acceso l'hub chiede a lui (ha la porta dell'FM-1, file in `/run/sagga`); senza, usa
`sagga_grid_bridge.py --export / --import`.

0.23, i motori THEORY: una traccia il cui pattern è **fatto dai motori** ha accanto al nome un segno con il seme
(`◆8`: seme 8), e in alto leggi `sorgente THEORY (prossimo seme N)`, oppure `sorgente FREE` quando i motori sono
liberi dal genere (SEQ 8 K1 su FREE). Il fumetto del segno dice se il pattern è di nessun genere. L'editor tiene quello che i motori sanno di ogni
pattern (da quale seme, a che variazione): un passo che cambi resta, e l'ENERGIA dell'FM-1 continua a riempire e
svuotare il resto (non in un RUMBLE o in un SUB che segue la cassa: quelli, quando l'energia cambia, vengono rifatti
interi). Se **svuoti** o **sposti** un pattern, i motori lo dimenticano: è un pattern scritto a mano.
**Copia in...** su un altro pattern della stessa traccia porta con sé il seme; su un'altra traccia no.

**0.24, le copie.** Sull'FM-1 la lunghezza è della traccia: quando una traccia è più lunga del suo pattern, negli step
in più il pattern gira di nuovo. Quegli step sono le sue **copie**, e l'editor le mostra in **verde-azzurro** (gli step
scritti da te restano verdi). Se ne selezioni una, sotto leggi di quale step è la copia.
Quando premi **Salva** il Pi rimette tutto a posto come farebbe l'FM-1 (lo fa `sagga_sgqjson`, con lo stesso codice
del firmware):

* cambi uno **step del pattern**: le sue copie cambiano con lui;
* cambi una **copia**: tutte le copie di quel pattern diventano step tuoi (il pattern è lungo quanto la traccia);
* **allunghi la traccia** (scheda Traccia, *lunghezza*): il pattern gira nei nuovi step, in tutti e 8 i pattern della
  traccia. Se dopo la fine del loop avevi scritto qualcosa, vale quello che hai scritto e non si copia niente;
* **accorci la traccia**: il pattern resta intero dopo il loop e torna com'era quando la riallunghi.

**0.25:** le copie nuove le vedi **subito**, mentre scrivi il numero della lunghezza, prima del Salva (fino alla 0.24
solo dopo). La pagina fa il conto come lo fa l'FM-1: quello che vedi prima del Salva è quello che trovi dopo.
Uno step copiato o incollato, o un pattern copiato su un altro, arriva sempre come step tuo, mai come copia.

**0.25, il metro e il resto.** Nella scheda **Progetto** c'è il **METRO**: la *battuta* in step (da 3 a 32; 16 è il 4/4,
14 il 7/8, 20 il 5/4) e *i suoi tempi* (i modi in cui quella battuta si divide: 7/8 = 2+2+3, 2+3+2, 3+2+2). Quando
cambi la battuta, le tracce lunghe un numero di battute la seguono (16 → 14, 32 → 28), come sull'FM-1; i pattern
restano scritti come sono. Su ogni riga di step un segno mostra dove cominciano i tempi e le battute. In alto, accanto
al nome, leggi il metro quando non è 4/4. Nella scheda **Traccia** la lista dello *step* ha i sei **poliritmi** (1/4
5:4 ... 1/16 7:4: cinque o sette step nel tempo di quattro) e *FOLLOW: le note* ha il quarto modo, **MELODY** (una
melodia resta dove è scritta e le sue note forti vanno sull'accordo). Il TURING lungo quanto la traccia è B = 17.
Un file MIDI esce e rientra con il metro del progetto.

**0.26.** Nella scheda **Progetto** c'è **IL CLICK** (la pagina SAVE 5 dell'FM-1): CLICK (OFF, REC, PLAY), COUNT IN,
CLICK OUT (il suono dell'FM-1 o un canale MIDI), il livello, la nota, e *le scene portano il metro*. La lista
**KEYBOARD** ha i due modi nuovi, CHORDS e CHORD <C3 (gli accordi della tastiera sono l'armonia), e i nomi dell'FM-1
per i due di prima (TRANSPOSE, TRANS <C3). Nella scheda **Traccia**, *FOLLOW: le note* ha il quinto modo, **SMOOTH**
(gli accordi si muovono poco). Un pattern dei motori copiato su un altro pattern porta con sé anche il metro in cui è
stato fatto.

**0.27.** Il convertitore conosce il **RETURN** di EVOLVE (SEQ 3, SEL + K2 sull'FM-1): un progetto aperto e salvato
nell'editor lo tiene. L'editor non mostra EVOLVE, come prima. Il profilo SEMPLICE sta nelle impostazioni dell'FM-1,
non nel progetto: l'editor non lo vede.

**0.28.** Le tracce sono **dodici**, uno step ha fino a **sei note**, una traccia **otto lane**: l'editor li prende dal
progetto e li mostra tutti (nello step: nota 1-6, lane 1-8; nella scheda Lane: lane 1-8). Un progetto della 0.27 o di
prima si apre con le sue prime dodici tracce. Un file MIDI caricato nella pagina: i canali 1-12 diventano le tracce
1-12, le note dei canali 13-16 restano fuori. **ascolta** suona fino a sei note.

0.15: nella scheda **Progetto** il **NOME** del progetto (fino a 16 caratteri: l'FM-1 lo mostra con SAVE + PRESETS e
quando carica uno slot; **Nuovo** lo prende dal nome del file). La scheda **Tape** è il piano roll delle tracce TAPE:
tocchi il vuoto e c'è una nota da un sedicesimo, la trascini per spostarla, dal bordo destro la allunghi, Canc la toglie;
battute e quantize del loop sulla stessa riga. Nella scheda **Traccia** il **GROOVE** (il template e quanto). In alto:
**segui l'FM-1** (mentre suona, lo step di ogni traccia ha una cornice bianca, il Tape una linea che corre) e
**ascolta** (lo step che accendi, la nota del roll che tocchi la suona l'FM-1 su quella traccia; nello step c'è anche
**♪ ascolta**). Segui e ascolta passano dal bridge del grid: deve essere acceso, con l'FM-1 collegato. Dalla 0.15 il
bridge gira anche senza i Launchpad (per la libreria e l'editor) e riparte da solo, col grid, quando li attacchi.

**0.23.2: il vecchio piano roll non c'è più.** Accanto a ogni progetto c'era anche il link *piano roll* (la pagina
della 0.11). Il suo *Salva* passava da un file MIDI, e il progetto che tornava non era lo stesso: una traccia TAPE su
un canale MIDI diverso dal suo numero finiva sulla traccia con quel numero (che diventava una TAPE, svuotata, mentre
la traccia giusta restava com'era); una traccia TAPE trasposta veniva trasposta un'altra volta; un loop di una battuta
tornava di quattro, con le note ripetute (e una nota che cambiavi restava quella di prima nelle altre tre). Bastava
premere *Salva*, anche senza toccare niente. La scheda **Tape** dell'editor fa le stesse cose e scrive le note così
come l'FM-1 le tiene, traccia per traccia. Un vecchio indirizzo `/roll/...` apre l'editor sulla scheda Tape.

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

0.23.2: se scrivi un BPM troppo lento per il file, o troppe battute, il loop sarebbe più lungo del file. Prima
tornava uno zip con le ultime slice vuote (tasti che non suonano niente), senza una parola; adesso la pagina dice
quanto dura il file e a che tempo starebbe (`a 100 BPM 1 battuta dura 2.40 s, ma il file dal primo colpo dura 1.76 s
(che per 1 battuta sono 136.0 BPM)`). Anche le battute che danno un tempo impossibile vengono rifiutate.

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
systemctl finti. `python3 tests/sagga_celle_tests.py`: il custode delle celle contro un RaspiMIDIHub finto che le perde
come il vero.
