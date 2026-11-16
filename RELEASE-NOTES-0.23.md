# SAGGA SEQ 0.23 - Note di rilascio

**I motori THEORY.** Fino alla 0.22 una parte si caricava dalla libreria. Dalla 0.23 puoi anche farla **fare** all'FM-1:
dalle regole del genere e da un numero, il **seme**. Vale per tutti i 25 generi. E c'è il modo **libero dal genere**
(FREE): i motori lavorano con le regole di nessun genere. Se non accendi i motori, l'FM-1 è la 0.22 com'era. Lo stesso
formato dei progetti (`SGQB`). Si installa al posto della 0.22.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.23.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid | `sagga-hub-0.23.zip` |
| come si installa e si aggiorna | `INSTALLA.md` (invariato) |

Cosa sono i motori e cosa fa ognuno è spiegato per intero in `docs/TEORIA.md`. Qui c'è l'essenziale.

## Come si usa

1. **SEQ pagina 8** (THEORY), **K1**: un passo, SOURCE **THEORY** (le regole del genere). Un altro passo, SOURCE
   **FREE** (le regole di nessun genere).
2. **BAND** (SEQ + nero 7 tenuto): una band intera, fatta dal seme. Ancora BAND: il seme dopo, un'altra band.
3. Gira l'**ENERGIA** (GLO 3 K1, o la riga dell'energia sul grid): la band si riempie e si svuota.
4. **COOK** (SEQ + bianco 9) su una traccia: la stessa parte, un po' diversa. Ancora COOK: ancora un po'.

| cosa vuoi | cosa fai |
| --- | --- |
| tornare alla libreria | SEQ 8 K1: SOURCE LIBRARY. Quello che c'è sulle tracce resta |
| solo la batteria, o una parte sola | KIT (SEQ + nero 7), BEAT (SEQ + bianco 10), come sempre |
| scegliere il seme | SEQ 8 K2 (NEXT SEED, da 1 a 999), oppure SEQ + ALG |
| un'altra parte su una traccia, subito | SEQ 8 K3 (TRACK SEED) |
| andare dritto a una variazione | SEQ 8 K4 (VARIATION). Quanto cambia lo dice HEAT |
| semi a caso | DICE SEQ. OCT+ tiene, OCT- rimette com'era |
| una progressione fatta dal genere | DICE PROG |
| cambiare genere tenendo la band | GENRE LIVE: le parti sono rifatte nel genere nuovo, dallo stesso seme |
| nessun genere | SEQ 8 K1 su **FREE**. Vedi qui sotto |
| parti di quattro battute | SAVE 2 K4, LIBRARY LENGTH 64 (un progetto nuovo parte da 16: una battuta) |

Tre cose da sapere mentre suoni:

* L'energia **aggiunge soltanto**. Salendo, i colpi che c'erano restano dove sono e le note tengono la loro altezza.
* Uno step che scrivi a mano in un pattern dei motori **resta**, anche quando l'energia cambia.
* Se incolli, raddoppi o svuoti un pattern, non è più dei motori: l'energia non lo tocca più. BEAT ne fa uno nuovo.

## Liberi dal genere (FREE)

I motori hanno un modo in cui **non guardano il genere**. Usano regole che vengono solo dal metro: una cassa sta sui
tempi, un rullante cerca il 2 e il 4, un hat sta sugli ottavi o sui sedicesimi, un basso parte dall'uno.

| cosa giri | cosa diventa libero |
| --- | --- |
| **SEQ 8 K1: SOURCE FREE** | i motori, sempre, qualunque genere sia scelto. È la via diretta |
| SEQ 6 K4: GENRE FREE, con SOURCE THEORY | tutta la macchina, e i motori con lei |
| ARP 4 K2: HARMONY FREE, con SOURCE THEORY | solo le progressioni di DICE PROG |

* **BAND** dà otto parti: KICK, SNARE, HAT, PERC, BASS, CHORD, ARP, LEAD. **KIT** le prime quattro.
* **BEAT** su più tracce insieme (lo scope su BANK o ALL) dà a ognuna la parte del suo ruolo: FREE ha una regola per
  ogni ruolo.
* Niente swing e niente GROOVE di un genere. Il tempo resta quello che hai.
* L'energia, COOK, il seme e la variazione funzionano come sempre.
* Con SOURCE FREE un cambio di genere **non tocca** i pattern dei motori, nemmeno con GENRE LIVE. Le tracce caricate
  dalla libreria seguono il genere come sempre.

## I motori, e a cosa somigliano

| il motore | cosa fa | perché così | a cosa somiglia |
| --- | --- | --- | --- |
| **il ritmo** | sceglie una *famiglia* (un hat in ottavi, in levare, in sedicesimi), tiene quello che c'è sempre e aggiunge il resto secondo dei pesi | un genere si riconosce da quello che c'è sempre | Grids di Mutable Instruments; GESMI |
| **l'energia** | svuotando lascia per ultimi i colpi che contano: gli accenti, e quello che la libreria tiene nelle sue versioni vuote | se i colpi sparissero a caso sparirebbe il genere | la manopola FILL di Grids; Complexity e Intensity di Logic |
| **le linee** (BASS, SUB, RUMBLE, LOG DRUM) | fondamentale sull'uno, ottave per muoversi, le note che quel genere usa. Il rumble evita la cassa che sta suonando, il sub la cerca | un basso sta sotto l'accordo e lega cassa e armonia | i bassisti dei Session Players di Logic Pro |
| **gli accordi** | il ritmo e il tipo di accordo; lo sposta l'ARMONIA | così segue qualunque progressione, anche la tua | l'NDLR di Conductive Labs |
| **i motivi** (LEAD, VOX) | una forma (scende, sale, arco, due note) su una scala di cinque o sette note, con domanda e risposta | un motivo si ricorda per la forma | il T-1 di Torso Electronics |
| **l'arpeggio** (ARP) | il ritmo, poi le note dell'accordo in fila: su, giù, su e giù, o un ordine suo che si ripete | un arpeggio è l'accordo suonato una nota alla volta | |
| **le progressioni** | quanti accordi, quanto durano, dove va la fondamentale; mai un accordo diminuito o aumentato | ogni genere muove gli accordi a modo suo | |
| **seme e variazione** | ogni scelta è legata al posto nella battuta: una variazione piccola resta piccola | così l'energia può aggiungere senza spostare | la Turing Machine di Music Thing |

## Tutti i 25 generi

* **TECHNO, HOUSE, DRUM+BASS, DUBSTEP**: regole scritte a mano, da quello che si legge su come si fanno questi generi.
* **Gli altri 21**: regole **contate dalla tua libreria**. Un programma legge tutti i pattern di un genere, mette insieme
  quelli che si somigliano e conta: quello che quasi tutti suonano c'è sempre, quello che suonano alcuni ha un peso. Le
  trovi scritte, genere per genere, in `docs/TEORIA-GENERI.md`.
* **FREE**: scritto a mano, solo il metro.

Quanto somigliano alla libreria, misurato (energia 50, 60 semi per genere): su 229 parti, 218 cadono dove cade la
libreria, e **due battute su tre sono battute che la libreria ha già**, colpo per colpo. Detto chiaro: nei generi
contati i motori stanno molto vicini alla libreria. Il nuovo viene da come le battute si combinano fra le parti, dalle
note (che non sono quelle scritte), dall'energia e dalle variazioni. Un genere suona come la sua libreria, non meglio.

## Il Pi e il grid

* **Il grid.** Nella vista BEAT, la terza riga: con SOURCE su THEORY o FREE i pad da 11 a 16 scelgono il seme fra sei, il pad 10
  passa ai sei dopo. Con SHIFT vedi il pattern che quel seme darebbe. Il programma sul Pi che parla con i Launchpad non
  è cambiato: le luci le decide l'FM-1.
* **Il tablet.** La pagina SAGGA Live ha una riga nuova: SOURCE (LIBRARY, THEORY, FREE), NEXT SEED, SEED, VARIATION
  (canale 12, CC 56-59), e l'FM-1 le rimanda i suoi valori. BEAT, COOK e DICE della pagina usano i motori quando
  SOURCE è su THEORY o su FREE. Dal tablet i semi arrivano a 128, dall'FM-1 a 999.
* **L'editor dei progetti.** Tiene quello che i motori sanno di ogni pattern. Una traccia il cui pattern è dei motori
  ha un segno con il seme (`◆8`). Se lì svuoti o sposti un pattern, i motori lo dimenticano. In alto dice la sorgente
  del progetto: THEORY o FREE.
* **Aggiorna anche il Pi.** Con il Pi alla 0.22 e l'FM-1 alla 0.23 tutto funziona, ma l'editor vecchio, quando salva
  un progetto, butta via i semi: i pattern restano, l'energia non li muove più.

## Un errore vecchio, trovato dall'esploratore

Richiamare uno **snapshot** rimetteva una traccia a tempo se le cambiava la lunghezza, l'inizio o la divisione. Non se
le cambiava la **direzione**: con una traccia su BACKWARD, uno snapshot salvato con FORWARD la lasciava uno step fuori
dalla battuta fino allo STOP dopo. Era così dalla 0.11. L'ha trovato una sessione a caso dell'esploratore (tre gesti:
SAVE + SEL + nero 1, HOME 2 K1, SAVE + nero 1). Corretto, ed è un test.

## Come è stato provato

@@PROVE@@

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.23.zip`. In alto deve dire `SAGGA HUB 0.23`.
2. **L'FM-1**: fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.23.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.23`.

## Da sapere

* **Niente di questo ha girato su un FM-1 vero.** Tutto è provato nel simulatore, che è il firmware stesso compilato
  per il computer: la logica, i tempi, il MIDI che esce. Il firmware cresce di circa 45 KB e ci sta con margine, ma è
  la compilazione di GitHub a dirlo, e l'FM-1 a confermarlo.
* **Come suona lo dicono le tue orecchie.** I test dicono che i motori stanno nel genere e non si rompono. Se una parte
  di un genere non ti convince, dimmi quale: le regole contate si rifanno, quelle a mano si correggono.
* **I progetti di prima** si aprono come sono, con SOURCE LIBRARY. Un progetto fatto con la 0.23, caricato su una 0.22,
  suona: i pattern ci sono, i semi vengono ignorati.
* **Cosa i motori non sanno fare**: le parti non si ascoltano fra loro (a parte la cassa); solo sedicesimi in quattro
  quarti, le terzine solo come rullata; una frase è di due battute; un motivo è una voce sola.
* Se cambi la libreria dei pattern, le regole dei 21 generi contati si rifanno con `python3 tools/theory/gen_rules.py`
  e una compilazione nuova.
