# SAGGA SEQ 0.23.2 - Note di rilascio

Ho riletto tutto quello che gira sul Pi, e il grid, come avevi chiesto. E ho sistemato la manopola A del tablet su
CELL. Le due cose più importanti che sono uscite:

1. **alcune abitudini di SAGGA sul Pi disturbavano la musica** (note tagliate, un buco ogni tanto);
2. **il vecchio piano roll rovinava i progetti** quando premevi Salva. L'ho tolto: c'è la scheda Tape dell'editor.

Si installa al posto della 0.23.1. Lo stesso formato dei progetti (`SGQB`).

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.23.2.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.23.2.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Quasi tutto è nel Pi. Nell'FM-1 cambia solo la manopola A del tablet.

## Il Pi non disturba più la musica

RaspiMIDIHub ha un'abitudine: **ogni volta che sul Pi un programma apre o chiude una porta MIDI, rifà tutta la sua
matrice**. Chiude le note che stanno suonando, stacca tutti i collegamenti, guarda i dispositivi e ricollega. Per un
momento (un decimo di secondo, anche di più) dall'FM-1 ai synth non passa niente. L'ho letto nel suo codice: lo fa
per i dispositivi che attacchi e stacchi, ma lo fa anche per un programma qualunque. E un programma che chiede
l'elenco delle porte MIDI ne apre e ne chiude due.

Quattro cose di SAGGA lo facevano mentre suonavi (la quarta solo se usi le patch degli snapshot):

| cosa | prima | adesso |
| --- | --- | --- |
| **la pagina del Pi** (porta 8090) chiede all'FM-1 chi è, per scriverlo in alto | la prima volta che la aprivi, e poi **ogni dieci minuti** finché restava aperta | solo quando l'FM-1 è appena tornato (acceso, riavviato, aggiornato). Aprire la pagina non chiede più niente |
| **il bridge del grid senza i due Launchpad** guarda se sono arrivati | **ogni 3 secondi** | solo quando un dispositivo arriva o se ne va |
| **il bridge del grid senza l'FM-1** | finiva e ripartiva **ogni 2 secondi** | aspetta fermo |
| **le patch dei synth negli snapshot** (solo se hai scritto `patches.json`) | **a ogni snapshot** che tornava, il bridge apriva e chiudeva la porta di ogni synth | le porte dei synth le apre quando parte, e le tiene |

Se ti è capitato di sentire una nota tagliata o un buco ogni tanto, con la pagina del Pi aperta, con un Launchpad
staccato, o quando richiamavi uno snapshot con le patch, poteva essere questo. Adesso, mentre suoni, niente di SAGGA
apre o chiude porte sul Pi.

Quello che resta: quando attacchi o stacchi un dispositivo USB (un Launchpad, un synth, l'FM-1), RaspiMIDIHub rifà la
matrice. È suo, non di SAGGA.

## Il grid

* **Si accorge di un FM-1 che si riavvia.** Il bridge guardava una volta al secondo se l'FM-1 c'era ancora. Nel log
  della tua prova l'FM-1 si riavvia e torna in **0,44 secondi**, con lo stesso nome: il bridge poteva non accorgersene,
  e restava collegato a niente. Il grid era morto finché qualcosa non faceva ripartire il bridge. Adesso il bridge
  guarda anche i suoi collegamenti, e se non ci sono più riparte da solo.
* **Un bridge fermo spegne i Launchpad.** Durante la prova al banco il Pi ferma il bridge. Prima i Launchpad restavano
  accesi e fermi (me l'avevi chiesto: sembravano vivi). Adesso si spengono, e l'FM-1 dice `GRID LOST`. A fine prova si
  riaccendono. Lo stesso quando spegni il Pi.
* Una luce di un tipo che il bridge non conosce (un firmware più nuovo del Pi) si vede fioca, non spenta.

Il resto del grid l'ho riletto e non l'ho toccato: il bridge, il suo modo di parlare con l'FM-1, le viste. Sui tuoi
due Launchpad Mini rossi e verdi i 18 tipi di luce stanno in 16 colori: bianco, giallo e "in attesa" sono lo stesso
ambra (quello in attesa lampeggia). È un limite dei Launchpad.

## Il tablet: la manopola A su CELL

Sulla pagina SAGGA Live, la manopola A di CELL sceglie la regola. Arrivava a una regola su due, e **mancavano proprio
quelle da cui partire**: 170 e 240 (il ritmo scivola), 204 (resta), 184, 150. Adesso **la regola è il doppio della
manopola**: 85 è la 170, 102 è la 204, 120 è la 240. Dal tablet arrivi a tutte le regole pari, cioè a tutte quelle
della tabella tranne la 51 e la 105 (pannello o grid). Lo schermo dell'FM-1 dice sempre cosa fa la regola.

## L'orologio del Pi

Il Pi non ha un orologio: senza internet resta indietro. I file della tua prova del 17 novembre portano la data del
26 ottobre. Non rompe niente, ma due cose prendevano il nome dall'ora e venivano ordinate per nome:

* **le versioni dell'editor** (quando salvi un progetto, quello di prima resta in `versioni/`, le ultime 20): con
  l'orologio che torna indietro, una versione salvata adesso poteva contare come la più vecchia ed essere buttata.
  Adesso il nome di una versione viene sempre dopo quello della più nuova che c'è;
* **i file della prova al banco sulla SD** (le ultime tre prove): quella appena fatta poteva essere cancellata subito.
  Adesso resta sempre.

Le date che leggi restano quelle dell'orologio del Pi: sbagliate, ma in ordine.

## Il vecchio piano roll: tolto

Nella pagina del Pi, accanto a ogni progetto, c'erano due link: **editor** e **piano roll**. Il piano roll era la
pagina vecchia, della 0.11, di prima dell'editor. Rileggendola ho visto che il suo **Salva** non rimetteva il progetto
com'era. L'ho provato con il suo stesso codice: bastava aprirla e premere Salva, senza toccare niente.

| il progetto | cosa succedeva al Salva |
| --- | --- |
| una traccia TAPE su un canale MIDI diverso dal suo numero (la traccia 4 sul canale 10) | le note andavano sulla **traccia 10**, che diventava una traccia TAPE (i suoi step restavano scritti, ma non suonavano più). La traccia 4 restava com'era: quello che avevi cambiato era perso |
| una traccia TAPE con la trasposizione (+12) | le note tornavano scritte già trasposte, e la trasposizione restava: suonava un'ottava più su di prima |
| un loop TAPE di una battuta | tornava di quattro battute, con le note ripetute quattro volte. Una nota che cambiavi restava quella di prima nelle altre tre |

Con le tracce TAPE sul loro canale, senza trasposizione e lunghe tutte uguali (da quattro battute in su) non
succedeva niente: le prove di allora usavano un progetto così, e non l'avevano visto.

La scheda **Tape** dell'editor (c'è dalla 0.15) fa le stesse cose: tocchi il vuoto e c'è una nota, la trascini, la
allunghi, Canc la toglie. E scrive le note così come l'FM-1 le tiene, traccia per traccia: in quei tre casi il
progetto torna giusto (c'è una prova nuova che lo controlla). Quindi il link *piano roll* non c'è più. Un vecchio
indirizzo `/roll/...` apre l'editor sulla scheda Tape.

Se hai usato il piano roll vecchio e ti sei trovato una traccia cambiata senza motivo, era questo. Sulla SD, nella
cartella `sagga`, accanto al progetto c'è un file `.bak`: è il progetto com'era prima dell'ultimo Salva del piano
roll. Se ti serve riprenderlo, dimmelo.

## Cose più piccole

* **BREAK IN SLICE.** Se scrivevi un BPM troppo lento per il file (100 per un break a 136), o troppe battute, tornava
  uno zip con le ultime slice **vuote**: tasti che non suonano niente, e nessun avviso. Adesso la pagina dice cosa non
  torna: `a 100 BPM 1 battuta dura 2.40 s, ma il file dal primo colpo dura 1.76 s (che per 1 battuta sono 136.0 BPM)`.
  Se lasci vuoti BPM e battute, li trova il Pi come prima.
* **Il file della prova dice come sta il bridge.** *Controlla la matrice* e la prova del banco scrivono nel loro file
  anche le ultime righe del bridge del grid: le porte che ha preso, se aspetta l'FM-1, perché si è fermato. Il bridge
  è la parte che è cambiata di più e non ha mai girato sul tuo Pi: se il grid fa qualcosa di strano, premi *Controlla
  la matrice* e mandami il file.
* La pagina del Pi **rifiuta le richieste che arrivano da un altro sito**. Una pagina web aperta su un telefono della
  stessa rete poteva, in teoria, caricare un file come firmware e chiederne l'installazione.
* `install_hub.sh` controlla che il disco sia scrivibile prima di ogni blocco di scritture. Se RaspiMIDIHub lo
  richiudeva a metà, l'aggiornamento si fermava a metà.
* Nell'editor, il fumetto di un pattern fatto dai motori diceva "i passi che scrivi tu restano". Adesso dice anche
  l'eccezione: non in un RUMBLE o in un SUB che segue la cassa.
* Il messaggio della prova diceva `GRID DETACHED`; l'FM-1 scrive `GRID LOST`.

## Letto e trovato a posto

Le sette pagine SAGGA del tablet (provate anche dentro il vero RaspiMIDIHub: 99 controlli). Il custode delle celle. Il
programma della prova al banco, e come rimette a posto tutto alla fine. L'editor: il programma sul Pi e tutto il
codice della sua pagina. La libreria dei progetti. I pattern e le progressioni del Pi (rispondono all'FM-1 in meno di
un millisecondo). L'M8 link e la porta PC. L'installatore del firmware. Tre strumenti automatici sul codice del Pi e
sulle pagine web: nessun errore vero.

I due programmi che trasformano i progetti (verso l'editor, e verso i file MIDI) li ho anche messi alla prova con
più di 1.500 file rotti e modifiche a caso, sotto il controllore della memoria: nessun errore. Il lettore dei file
MIDI ha avuto un ritocco di sicurezza (un file tagliato a metà di una nota veniva letto qualche byte oltre la sua
fine: senza danno, ma non si fa).

## I 6 messaggi persi della prova

Restano da spiegare. Due cose in più le so adesso. Il tuo Pi è un Pi 4 o 5 (lo dice il log): la sua USB è buona, non è
quella dei Pi vecchi che perdono note. E il rifacimento della matrice di RaspiMIDIHub **non** c'entra con quei 6: la
prova ascolta l'FM-1 per conto suo, senza passare dalla matrice. Lo diranno i conti della 0.23.1 alla prossima prova.

## Come è stato provato

Nel simulatore e con dispositivi finti (un ALSA finto, un RaspiMIDIHub finto, Launchpad finti). **Niente di questo ha
girato sul tuo Pi.**

* **Il bridge del grid**: 321 controlli (la 0.23.1: 279). I nuovi contano gli sguardi alle porte: senza l'FM-1 il
  bridge legge `/proc` quaranta volte e guarda le porte due volte in tutto; senza i Launchpad le guarda una volta sola
  finché niente cambia; con le patch degli snapshot, tre snapshot richiamati mentre suona non aprono e non chiudono
  niente. Poi: l'FM-1 rifatto con lo stesso numero (il collegamento sparito viene visto), il bridge fermato dal
  servizio (i Launchpad spenti, l'FM-1 avvisato), la luce sconosciuta.
* **La pagina del Pi**: 177 controlli (162). Chiede all'FM-1 chi è solo quando l'FM-1 cambia; una richiesta da un altro
  sito è rifiutata; il vecchio piano roll: un link vecchio apre l'editor, un Salva è rifiutato e il progetto non viene
  toccato.
* **L'editor**: 180 controlli (166), con la pagina aperta in un browser vero. I nuovi: le versioni con l'orologio che
  torna indietro, e i tre casi che il vecchio piano roll sbagliava, giusti dalla scheda Tape.
* **Lo slicer**: 48 controlli (33). **La prova al banco**: 76 (69). **Le pagine SAGGA dentro il vero RaspiMIDIHub**:
  99, come prima.
* **L'FM-1**: 1.274 controlli con i tasti e le manopole (1.269): i 5 nuovi sono la manopola A del tablet su CELL. Il
  cuore del firmware (2.306.210 controlli) e i motori (36.252.432) passano come nella 0.23.1.
* **L'esploratore completo**: 73.819 gesti da soli in 22 situazioni, 8.797 coppie di gesti, 200 sessioni a caso da 60
  gesti: **0 errori**.
* **La memoria**: la suite intera rifatta con i controlli della memoria (AddressSanitizer e
  UndefinedBehaviorSanitizer): i 1.274 controlli dell'FM-1, 26 prove a caso, l'esploratore veloce. Nessun errore.
* **I test che controllano i test**. Ho rimesso apposta le cose vecchie, una alla volta, per vedere se i test nuovi se
  ne accorgono: la vecchia mappa della manopola A, lo sguardo alle porte ogni 3 secondi, la domanda ogni dieci minuti,
  le porte dei synth aperte a ogni snapshot (9 controlli falliscono), lo slicer senza il controllo nuovo (4
  falliscono). Se ne accorgono tutti. Il vecchio piano roll l'ho fatto girare con il suo stesso codice sui tre casi,
  per vedere il danno prima di toglierlo.
* **GitHub** ha compilato il pacchetto (`FM-1_973`) e rifatto i 2.306.210 controlli del cuore del firmware.
* **Cosa non è stato provato**: il Pi vero, RaspiMIDIHub vero in funzione, i Launchpad veri, un FM-1 vero.

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.23.2.zip`. In alto deve dire `SAGGA HUB 0.23.2`.
2. **L'FM-1**: fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.23.2.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.23.2`.

## Da sapere

* **Niente di questo ha girato su un Pi vero.** La parte più cambiata è il bridge del grid. Dopo l'aggiornamento del
  Pi i Launchpad devono riaccendersi entro una decina di secondi. Se non succede, o se il grid fa qualcosa di strano:
  premi **Controlla la matrice** sulla pagina del Pi e mandami il file. Adesso dentro ci sono le righe del bridge.
* **Durante la prova al banco i Launchpad si spengono** e l'FM-1 dice `GRID LOST`. È giusto: si riaccendono alla fine.
* **Il piano roll non c'è più**: le tracce TAPE si scrivono nell'editor, scheda **Tape**.
* **I 6 messaggi persi**: rifai la prova al banco con l'FM-1 e il Pi tutti e due alla 0.23.2 e mandami il file. I
  conti diranno dove si perdono.
* **Attaccare o staccare un cavo USB mentre suoni** fa ancora rifare la matrice a RaspiMIDIHub (una nota tagliata, un
  attimo di buco). È suo. Meglio farlo fra un pezzo e l'altro.
* **I progetti** si aprono come sono. Nell'FM-1 cambia solo la manopola A del tablet su una traccia CELL: la stessa
  posizione della manopola adesso dà un'altra regola (il doppio del numero).
* **Il firmware** cresce di 32 byte: 443.944 su 581.564 (la 0.23.1: 443.912). La RAM è la stessa: 68.816 byte su
  98.304. Lo dice la compilazione di GitHub.
