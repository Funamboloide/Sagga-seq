# SAGGA SEQ 0.23.1 - Note di rilascio

Una versione piccola. Nasce dalla prova al banco della 0.23 e da due domande: "NUMERIC lavora nel modo giusto?" e
"come si usa CELL?". La risposta alla prima era no, ed è stato rifatto. CELL lavorava giusto ma era difficile da
usare, e adesso lo è meno. Si installa al posto della 0.23. Lo stesso formato dei progetti (`SGQB`).

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.23.1.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.23.1.zip` |
| come si installa e si aggiorna | `INSTALLA.md` (invariato) |

Servono tutti e due: l'FM-1 per NUMERIC e CELL, il Pi per i conti della prova al banco.

## NUMERIC: sedici ritmi

NUMERIC è la terza famiglia di EUCLID LIVE (SEQ pagina 1, K3). Fino alla 0.23 prendeva l'n-esimo numero primo e ne
suonava le cifre binarie. Su 16 step: con K1 a 2, 4 o 11 suonavano tutti gli step, a 1 uno sì e uno no, gli altri
valori davano da 7 a 14 colpi sparsi. Nessun ritmo che uno scriverebbe. Era copiato male dal modulo a cui si ispira
(il Numeric Repetitor): lì i "ritmi primi" sono ritmi scelti a mano, non numeri primi.

Adesso:

* **K1 sceglie uno di sedici ritmi base**, dal più dritto al più sincopato.
* **K2 lo sposta** di uno step alla volta, come nelle altre famiglie.
* **SEQ + bianco 6** lo fa partire e lo ferma, come sempre.

| K1 | il ritmo | la forma | |
| --- | --- | --- | --- |
| 1 | `x...x...x...x...` | 4-4-4-4 | cassa in quattro |
| 2 | `x...x...x.....x.` | 4-4-6-2 | l'ultimo colpo in ritardo |
| 3 | `x..x....x...x...` | 3-5-4-4 | |
| 4 | `x..x....x..x....` | 3-5-3-5 | |
| 5 | `x...x...x...x.x.` | 4-4-4-2-2 | quattro e una levata |
| 6 | `x..x..x.x...x...` | 3-3-2-4-4 | un tresillo, poi due colpi dritti |
| 7 | `x..x..x...x.x...` | 3-3-4-2-4 | clave son |
| 8 | `x..x...x..x.x...` | 3-4-3-2-4 | clave rumba |
| 9 | `x..x..x...x..x..` | 3-3-4-3-3 | bossa nova |
| 10 | `x.x.x...x.x.x...` | 2-2-4-2-2-4 | |
| 11 | `x..x..x.x...x.x.` | 3-3-2-4-2-2 | un tresillo, un colpo e una levata |
| 12 | `x..x..x.x..x..x.` | 3-3-2-3-3-2 | il tresillo due volte |
| 13 | `x..x..x..x..x.x.` | 3-3-3-3-2-2 | |
| 14 | `x.x.x.x.x.x.x...` | 2-2-2-2-2-2-4 | |
| 15 | `x.x.x.x.x.x..x..` | 2-2-2-2-2-3-3 | |
| 16 | `x..x.x.x..x.x.x.` | 3-2-2-3-2-2-2 | |

"La forma" sono gli step da un colpo al successivo: 3-3-2 è il tresillo. Ogni ritmo ha un colpo sul primo step, da 4 a
7 colpi, mai due attaccati. Su una traccia di 32 o 64 step i sedici step si ripetono. NUMERIC è fatto per tracce di 16
step: su una traccia più corta suona solo l'inizio del ritmo, e K1 arriva a tanti ritmi quanti sono gli step.

Lo schermo ti segue: la cella dice `NUMERIC READY 7 OF 16`, il messaggio dice la forma
(`NUMERIC LIVE T1: 7 = 3-3-4-2-4 ROT 2`). Girando K3 lo schermo dice cosa fanno K1 e K2 nella famiglia scelta, in
tutte e tre.

**Attenzione:** un progetto che suona un ritmo NUMERIC nella 0.23.1 suona diverso. Sceglilo di nuovo.

## CELL: torna al tuo ritmo, e lo schermo dice cosa fa la regola

CELL è l'algoritmo dopo TURING (SEQ pagina 2, K1). **Cosa fa:** prende il ritmo scritto sulla traccia e a ogni
battuta lo trasforma in una riga nuova, con una regola fissa. Per ogni step guarda lui e i suoi due vicini e decide se
nella riga dopo suona. Non c'è il caso: lo stesso ritmo con la stessa regola racconta sempre la stessa storia.

| manopola | cosa |
| --- | --- |
| K2 RULE | la regola, da 0 a 255 |
| K3 CELLS | quanto è lunga la riga: 16 = una battuta di sedicesimi. Con 8 la riga si ripete due volte nella battuta |
| K4 NEW ROW EVERY | ogni quanto arriva una riga nuova: 1, 2, 4 battute, o a ogni giro della traccia |

**A cosa serve:** a far cambiare da sola una parte (un hat, una percussione, uno stab) battuta dopo battuta, partendo
da quello che hai scritto tu. SEQ + bianco 6 lo fa partire; SEQ + bianco 7 (WRITE LIVE) scrive nel pattern la riga che
senti.

Due cose nuove:

1. **Una riga vuota torna al tuo ritmo.** Con più di cento regole, prima o poi la riga esce vuota. Fino alla 0.23
   ripartiva da un colpo solo a metà battuta, e il ritmo che avevi scritto non tornava più. Adesso riparte dal ritmo
   scritto. Così molte regole diventano una frase di qualche battuta che torna sempre a casa: la regola 90 su 16
   celle fa al massimo otto righe e poi di nuovo la tua.
2. **Lo schermo dice cosa fa la regola.** Le regole sono 256 numeri senza nome. Adesso, quando giri RULE o CELLS, lo
   schermo dice cosa farà quella regola con il ritmo di quella traccia:

   | lo schermo dice | vuol dire |
   | --- | --- |
   | `THE RHYTHM STAYS AS IT IS` | non cambia niente |
   | `SLIDES 1 STEP LATER EVERY ROW` | il ritmo scivola di uno step a ogni riga (`EARLIER`: all'indietro) |
   | `A LOOP OF 8 ROWS` | otto righe diverse, poi da capo |
   | `AFTER 4 ROWS A LOOP OF 4` | quattro righe che non tornano, poi un giro di quattro |
   | `AFTER 3 ROWS IT STAYS` | dopo tre righe si ferma su un ritmo |
   | `AFTER 1 ROW EVERY STEP PLAYS` | si riempie tutto |
   | `KEEPS CHANGING FOR A LONG TIME` | non si ripete per un bel po' |

   Se CELL sta suonando, la storia parte dalla riga che suona adesso. Se è READY, parte dal ritmo scritto.

**Regole da cui partire** (su 16 celle):

| regola | cosa fa |
| --- | --- |
| 204 | la riga resta com'è. Mentre CELL suona, ferma la riga di quella battuta |
| 170, 240 | il ritmo scivola uno step prima / uno step dopo a ogni riga |
| 184, 226 | scivola, e i colpi attaccati si allargano |
| 51 | scambia colpi e pause |
| 90, 150 | apre il ritmo e torna al tuo in 8 righe al massimo |
| 60, 102 | frasi più lunghe, fino a 16 righe |
| 54 | rado e fitto, a turno |
| 18, 22 | storie più rade |
| 110, 30 | storie lunghe; la 30 di solito non si ripete |

Quasi tutte le altre si fermano, riempiono tutto o non fanno niente: lo schermo te lo dice mentre giri.

**Sul grid** (TRACK 3, riga 5) i sedici pad delle regole adesso vanno dalla più calma alla più agitata: 204, 170, 240,
184, 51, 90, 150, 105, 60, 54, 18, 22, 126, 122, 110, 30. **Dal tablet** la manopola A arriva a una regola su due
(ha 128 posizioni per 256 regole): le regole 170, 240, 184, 204, 51 e 150 si scelgono dal pannello o dal grid. Dal
tablet le 171 e 241 scivolano anche loro, ma prima riempiono i buchi di tre step o più: scivola un ritmo più fitto del
tuo.

## La prova al banco conta i messaggi

Nei log della prova al banco che mi hai mandato (FM-1 alla 0.23; i file dicono 26 ottobre perché l'orologio del Pi è
indietro) c'era una cosa vera e non spiegata: **6 messaggi che l'FM-1 aveva mandato e il Pi non aveva sentito**, in 2
sessioni su 28 (quattro tick del clock e due note-off). Il resto tornava: i motori
sull'FM-1 vero suonano come nel simulatore, nota per nota. Ma da quei log non si poteva capire da che lato i 6
messaggi si erano persi. Adesso sì:

* **L'FM-1 conta quello che manda**, porta per porta e tipo per tipo, e tiene i conti della sua coda USB.
* **Il Pi glielo chiede** prima e dopo ogni sessione, e lo confronta con quello che ha sentito lui e con quello che ha
  ricevuto il suo driver USB.
* Se i numeri sono uguali non dice niente. Se manca qualcosa, la riga della sessione nel log dice `CONTI:` con quanti
  messaggi, di che tipo e **dove si sono persi**: dentro l'FM-1, fra l'FM-1 e il Pi, o nel Pi.

La prossima volta che fai la prova, se succede ancora, mandami il log: ci sarà scritto il lato.

Il rapporto che si fa dalla raccolta è più preciso. Dice i messaggi mancanti uno per uno, con il momento (`PERSI`). E
non segnala più come errori tre cose che erano solo questione di millisecondi. Rifatto sui tuoi due file:

* **Il banco** (4 sessioni): nessun errore. Prima ne segnava uno, un dado tirato dal grid che l'FM-1 aveva preso 1 ms
  dopo, e un "messaggio del bridge mai arrivato" che in realtà era partito dopo la fine della sessione.
* **L'FM-1 completo** (28 sessioni): 2 errori, e sono proprio i messaggi persi. Sessione s014: 3 tick del clock (a
  40,99, 41,11 e 42,97 secondi dall'inizio). Sessione s015: 1 tick e 2 note-off, tutti a 19,3 secondi. Le due
  differenze dal simulatore che segnava prima erano tasti letti dall'FM-1 da 6 a 9 ms dopo: con quei millisecondi il
  simulatore fa la stessa cosa.

Durante la prova **il grid vero resta acceso e fermo: è giusto così**. Il Pi spegne il programma che guida i due
Launchpad e ne usa due finti al suo interno, per premere ogni volta gli stessi pad. A fine prova tornano come prima.

## Corretto nei testi

Le note della 0.23 dicevano: "uno step scritto a mano in un pattern dei motori resta, anche quando l'energia cambia".
È vero per quasi tutte le parti. **Non per quelle che seguono la cassa**: il RUMBLE (TECHNO, HARDTECHNO) e il SUB
(DRUM+BASS, DUBSTEP, JUNGLE, GRIME, BASSLINE, FOOTWORK, PHONK, UK DRILL, BAILE FUNK). Quelle, quando l'energia
cambia, vengono rifatte tutte intorno alla cassa, e lo step scritto a mano si perde. Il firmware non è cambiato: è
cambiato il testo, in `TEORIA.md`, in `SAGGA-SEQ.md` e nel manuale.

## Come è stato provato

Nel simulatore, che è il firmware stesso compilato per il computer, e sui tuoi due file della prova al banco.

* **NUMERIC e CELL da soli**: 2.306.210 controlli sul cuore del firmware (la 0.23: 1.110.950). I sedici ritmi uno per
  uno. Per CELL: una riga nuova confrontata con la definizione, per tutte le 256 regole e tutte le larghezze da 3 a 64
  celle; la storia che lo schermo racconta confrontata con le righe contate una per una, per tutte le regole, su 9
  larghezze e 5 ritmi.
* **L'FM-1 intero**: 1.269 controlli fatti con i tasti e le manopole (la 0.23: 1.237). I 32 nuovi: NUMERIC dal
  pannello, CELL dal pannello, dal grid e dal tablet, i conti della prova.
* **L'esploratore completo**: 73.819 gesti da soli in 22 situazioni, 8.797 coppie di gesti, 200 sessioni a caso da 60
  gesti: **0 errori**.
* **La memoria**: la suite intera rifatta con i controlli della memoria (AddressSanitizer e
  UndefinedBehaviorSanitizer): i 1.269 controlli dell'FM-1, 26 prove a caso, l'esploratore veloce. Nessun errore.
* **I motori** non sono cambiati: i loro 36.252.432 controlli passano come nella 0.23.
* **La prova al banco senza FM-1**: un FM-1 finto che conta come quello vero. Quando gli faccio perdere due note per
  strada, il Pi lo dice e dice dove. In tutto 166 controlli sugli strumenti della prova, più 5 prove sul rapporto
  nuovo (i millisecondi e i messaggi persi).
* **I test che controllano i test**: la mia prima tabella dei sedici ritmi aveva due ritmi che erano un altro ritmo
  girato: il test nuovo li ha trovati, e li ho cambiati. Ho accorciato apposta la vista di CELL sulla storia: i test
  non se ne accorgevano, ho aggiunto due casi e adesso sì. Senza la ricerca nuova dei millisecondi, la prova del
  rapporto fallisce.
* **GitHub** ha compilato il pacchetto (`FM-1_973`) e rifatto i 2.306.210 controlli del cuore del firmware.
* **Cosa non è stato provato**: un FM-1 vero. NUMERIC, CELL e i contatori nuovi hanno girato solo nel simulatore.

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.23.1.zip`. In alto deve dire `SAGGA HUB 0.23.1`.
2. **L'FM-1**: fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.23.1.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.23.1`.

## Da sapere

* **Niente di questo ha girato su un FM-1 vero.** È provato nel simulatore: la logica, i tempi, il MIDI che esce.
  Il firmware cresce di 2,4 KB e ci sta con margine: 443.912 byte su 581.564 (la 0.23: 441.544), la RAM 68.816 byte
  su 98.304 (+80). Lo dice la compilazione di GitHub.
* **I progetti di prima** si aprono come sono. Cambia solo un ritmo NUMERIC che stava suonando: sceglilo di nuovo. Una
  traccia con CELL acceso suona uguale finché la riga non esce vuota; da lì torna al ritmo scritto, non più a un colpo
  solo.
* **I conti della prova** ci sono solo con l'FM-1 e il Pi tutti e due alla 0.23.1. Con un FM-1 alla 0.23 la prova
  gira come prima, senza conti.
* **Quando giri RULE o CELLS** l'FM-1 calcola la storia della regola per scriverla sullo schermo. Dovrebbe metterci
  pochi millisecondi, ma su un FM-1 vero non l'ho potuto misurare. Se girando quelle due manopole in play senti il
  tempo incerto, dimmelo.
