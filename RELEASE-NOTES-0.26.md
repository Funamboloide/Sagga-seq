# SAGGA SEQ 0.26 - Note di rilascio

Dalla lista che ti avevo scritto dopo la 0.25 hai scelto sette cose. **Sono dentro tutte e sette**, più il controllo
tecnico delle versioni 0.23-0.25.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.26.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.26.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati tutti e due. I progetti di prima si aprono come sono, e suonano come prima.

## Le sette cose

| cosa avevi chiesto | adesso |
| --- | --- |
| **metronomo e conteggio** | SAVE ha una pagina nuova, la 5: **THE CLICK**. Il click batte sui tempi del metro; prima di registrare può contare una o due battute |
| **accordi dal vivo dalla tastiera** | KEYBOARD (SAVE 4 K2) ha due modi nuovi, **CHORDS**: l'accordo che suoni diventa l'armonia di tutta la band |
| **il metro che cambia con la scena** | GLO 4 K3, **SCENE METRE**: ogni scena si ricorda il suo metro e lo riporta. Anche nella song |
| **accordi che si muovono poco** | FOLLOW ha un modo nuovo, **SMOOTH**: da un accordo all'altro le note comuni restano ferme, le altre vanno alla nota più vicina |
| **pedale, rotella, bend, aftertouch attraverso l'FM-1** | passano e arrivano al synth della traccia che stai suonando. Con REC acceso vengono anche registrati |
| **ritmi nati in sette e in cinque** | i motori THEORY scrivono la parte **dentro la battuta** del metro: un 7/8 non è più un 4/4 a cui manca un pezzo |
| **la risposta fatta di note** | il basso riprende le note della melodia; la melodia, subito dopo un accordo, suona note di quell'accordo |

## 1. Il metronomo e il conteggio

**SAVE pagina 5, THE CLICK** (tieni SAVE e vai alla quinta pagina con OCT+):

| manopola | cosa fa |
| --- | --- |
| **K1 CLICK** | OFF, REC (solo mentre registri), PLAY (ogni volta che suona) |
| **K2 COUNT IN** | OFF, 1 BAR, 2 BARS: quante battute conta prima di registrare |
| **K3 CLICK OUT** | FM-1 (il suono dell'FM-1) oppure un canale MIDI: il click diventa una nota su quel canale |
| **K4 LEVEL** | il volume, da 1 a 10. Con SEL tenuto: la nota MIDI del click |

* Il click batte **sui tempi del metro**: in 7/8 (2+2+3) senti tre colpi per battuta, non quattro. Il primo colpo
  della battuta è più acuto e più forte.
* **Il conteggio**: con REC acceso e COUNT IN su 1 o 2, premi PLAY. L'FM-1 conta (lo schermo dice `COUNT IN 1.1`,
  `1.2`...; il LED di PLAY lampeggia) e poi parte. Se premi PLAY durante il conteggio, si ferma (`COUNT IN STOPPED`).
  Il conteggio c'è solo quando è l'FM-1 a dare il tempo.
* All'inizio il click è **spento**: lo accendi tu.

## 2. Gli accordi dal vivo

**SAVE 4 K2, KEYBOARD**, adesso ha cinque posizioni: OFF, TRANSPOSE, TRANS <C3 (sono le due di prima, con un nome
più chiaro: si chiamavano ALL e SPLIT C3), e le nuove **CHORDS** e **CHORD <C3**.

* **CHORDS**: suoni un accordo sulla tastiera (due note o più) e quello diventa **l'accordo dell'armonia**. Tutte le
  tracce con FOLLOW ci vanno subito, come quando la progressione cambia accordo. Lo schermo dice quale ha capito:
  `CHORD IV (THE KEYBOARD'S)`.
* **CHORD <C3**: lo stesso, ma solo con i tasti sotto il Do centrale. Sopra suoni normalmente: mano sinistra gli
  accordi, mano destra la melodia.
* L'accordo **resta** quando alzi le mani, fino al prossimo. Funziona anche con HARMONY spenta.
* Per tornare alla progressione: rimetti KEYBOARD su un altro modo.

## 3. Il metro che cambia con la scena

**GLO 4 K3, SCENE METRE**: OFF oppure BRING IT.

* Con BRING IT ogni scena che **salvi** si ricorda il metro in cui la salvi (lo schermo dice `SCENE STORED 2 IN 7/8`).
* Quando la **richiami**, porta il suo metro: da fermo subito, mentre suona alla fine della battuta.
* **Nella song** funziona da solo: strofa in 4/4, ritornello in 7/8. Anche se parti da metà song, l'FM-1 sa in che
  battuta è.
* Una scena salvata con SCENE METRE spento lascia il metro com'è.

## 4. Gli accordi che si muovono poco

**ARP 4 K1, FOLLOW MODE**, dopo MELODY c'è **SMOOTH**.

Con gli altri modi un accordo si sposta tutto insieme, come una mano che scivola sulla tastiera. Con SMOOTH fa come
un tastierista: **le note che i due accordi hanno in comune restano ferme**, le altre vanno alla nota più vicina.
Do-Mi-Sol che va sul Fa diventa Do-Fa-La, non Fa-La-Do un'ottava sopra.

I PAD e i PIANO fatti da BEAT, BAND e dai dadi nascono già in SMOOTH.

## 5. Pedale, rotelle e aftertouch

Fino alla 0.25 una tastiera collegata all'FM-1 perdeva tutto tranne le note. Adesso:

* **Passano**: il pedale, la rotella del pitch, la rotella di modulazione, l'aftertouch (anche quello tasto per
  tasto) e tutti gli altri controlli vanno al synth della traccia che stai suonando. Serve REC acceso, oppure
  MIDI IN su ALWAYS (SAVE 4 K4), come per le note.
* **Vengono registrati** (REC acceso, mentre suona, su una traccia a step):
  * le rotelle e l'aftertouch finiscono in una **LANE** della traccia. Se la traccia ne ha già una per quel
    controllo usa quella, altrimenti ne prende una libera. Lo schermo lo dice: `LANE 6 RECORDS THE PITCH WHEEL`.
  * **il pedale** non diventa una lane: le note suonate col pedale giù vengono registrate **lunghe quanto suonano**.
    Risuonate non hanno bisogno del pedale.
* Niente resta appeso: se cambi traccia o premi STOP, il pedale viene rilasciato e la rotella torna al centro sul
  canale dov'erano.

## 6. I ritmi nati in sette e in cinque

Nella 0.25 i motori THEORY scrivevano sempre in 4/4 e poi adattavano: un 7/8 era un 4/4 con un pezzo tagliato.

Adesso scrivono **dentro la battuta**. Ogni passo della battuta sa che posto ha nel metro, e il ritmo nasce lì:

* in 7/8 la cassa della techno batte **su ogni tempo della battuta**, e il clap risponde sui tempi dopo il primo;
* in 5/4 i cinque tempi sono cinque tempi veri, ognuno con le sue scelte: nessuno è la copia di un altro;
* un metro dispari si può sentire in due modi (in 7/8: il tempo lungo come un tempo solo, oppure spezzato). Ogni
  band ne ha uno, deciso dal suo seme, uguale per tutte le sue parti;
* se il metro non ha un passo per il colpo su cui una parte è costruita (il rullante della dubstep sul tre, in una
  battuta di tre tempi), il colpo va sul tempo più vicino: **una parte non perde mai la sua spina dorsale**;
* l'ENERGIA riempie e svuota come sempre, senza spostare quello che c'è.

Cosa succede ai pattern che hai già:

* **in 4/4 non cambia niente**: i motori fanno esattamente le stesse parti della 0.25;
* un pattern fatto dalla 0.25 resta com'è. Se **cambi il metro**, viene rifatto dentro la battuta nuova; se torni in
  4/4, ritrovi quello di prima, nota per nota.

## 7. La risposta fatta di note

Nella 0.25 le parti si rispondevano solo nel ritmo: una suonava dove l'altra taceva. Adesso si rispondono anche
con le note.

* **Il basso sotto la melodia**: fuori dai tempi, dove la melodia tace e ha appena suonato, il basso riprende la
  nota che la melodia aveva un ottavo o un quarto prima. Sui tempi resta sulle sue note: lì è il fondamento.
  Quanto spesso dipende dallo stile: un basso melodico (house, garage) lo fa spesso, un basso tutto di toniche
  (trance) quasi mai. **Ogni genere resta se stesso.**
* **La melodia sopra gli accordi**: subito dopo un accordo, dove gli accordi tacciono, la melodia suona una nota di
  quell'accordo: la terza, poi la quinta, poi la settima. Quando la progressione si sposta, FOLLOW MELODY porta
  quella nota sull'accordo che sta suonando.
* Vale per i pattern **fatti nuovi con la 0.26** (BEAT, BAND, i dadi, un seme nuovo). Quelli della 0.25 continuano
  a rispondersi solo nel ritmo, così i tuoi progetti suonano come prima.

## Il controllo tecnico

Mi avevi detto "assolutamente sì". Ho misurato quanta parte del programma viene davvero eseguita dalle prove:
fra il 95 e il 99% del firmware, secondo la parte. Le righe mai eseguite le ho guardate una per una.

* **Un errore trovato e corretto**: in una tonalità minore l'accordo di nona sul secondo grado veniva scritto, nei
  file per il Pi, come un semplice diminuito.
* **Un falso allarme dell'esploratore corretto**: sulla pagina delle MOSSE la manopola ALG sceglie *quando* parte una
  mossa. L'esploratore la prendeva per un cambio di pagina e segnalava un errore che non c'era.
* **Il piano di prova per l'FM-1 vero** (quello nello zip del Pi) lasciava fuori le situazioni più nuove: il numero
  era scritto a mano. Adesso le prende tutte.
* **La memoria di lavoro**: i motori nuovi ne usano di più. Ho misurato il caso peggiore: circa un terzo di quella
  che l'FM-1 ha. C'è margine.
* L'analizzatore del compilatore su tutto il firmware: quattro avvisi, guardati uno per uno. Nessuno è un errore vero.
* Ho aggiunto le prove per le parti nuove e per quelle che nessuna prova toccava.

## Come è stato provato

| la prova | quanto |
| --- | --- |
| il cuore del sequencer | 30.938.169 controlli, 0 errori |
| i motori THEORY, in 4/4 e in altre 18 battute (7/8, 5/4, 5/8, 9/8, 11/8, 7/4...) | 215.628.289 controlli, 0 errori |
| i motori della 0.25, confrontati uno a uno | 1.213.056 parti: identiche |
| il simulatore (il firmware vero che gira sul computer) | 1.478 controlli, 0 errori |
| l'esploratore: ogni gesto del pannello, in 28 situazioni | 94.367 gesti da soli, 11.197 coppie di gesti, 200 sessioni a caso: 0 errori |
| l'editor del Pi | 245 controlli, 0 errori |
| il bridge del grid, la pagina del Pi, le pagine SAGGA | 325 + 176 + 80 controlli, 0 errori |
| gli errori di memoria (gesti a caso, con i rilevatori accesi) | 26 giri, 0 errori |
| 19 errori messi apposta nel programma | le prove li trovano tutti e 19 |

**Non ho un FM-1 in mano**: tutto questo è provato sul simulatore, non sullo strumento vero.

## Installare

Come sempre: prima il Pi (`sagga-hub-0.26.zip`), poi l'FM-1 (`sagga-0.26.fwsc`). I passi sono in `INSTALLA.md`.

## Cosa provare per primo

1. **Il click**: SAVE 5, K1 su PLAY, premi PLAY. Se non senti niente, vedi "Da sapere" qui sotto.
2. **Una band in 7/8**: GLO 4 K1 fino a 14, SEQ 8 K1 su THEORY, poi BAND. Ascolta la cassa: batte sui tempi del
   sette, non su quelli di un 4/4 tagliato.
3. **Gli accordi dal vivo**: SAVE 4 K2 su CHORDS, fai partire una band, suona accordi sulla tastiera.
4. **SMOOTH**: su una traccia di accordi, ARP 4 K1 su SMOOTH, e accendi l'armonia.
5. **Il pedale**: REC acceso, suona tenendo il pedale, riascolta: le note sono lunghe come le hai suonate.

## Da sapere

* **Il suono del click dell'FM-1 va provato sullo strumento.** Usa l'uscita audio dell'FM-1, che il sequencer teneva
  spenta dalla 0.22. Se non lo senti o disturba, metti CLICK OUT su un canale MIDI: il click diventa una nota (di
  solito la 75, una clave) che puoi mandare a un synth o a una drum machine. Questo modo funziona di sicuro.
* **Il pedale è registrato come lunghezza delle note**, non come pedale: nel pattern non trovi "pedale giù".
* **Su una traccia TAPE** le rotelle passano e si sentono, ma non vengono registrate: un tape tiene solo le note.
* **Le band fatte con la 0.25 in un metro dispari** restano come sono. Se cambi metro e poi torni, rinascono nel
  modo nuovo (dentro la battuta), quindi non sono più identiche a prima.
* **Tornare alla 0.25**: un FM-1 con la 0.25 apre i progetti della 0.26, ma prende per "scritti a mano" i pattern
  fatti nel modo nuovo (non li riempie più con l'energia) e dimentica le impostazioni del click.
* **Sotto un arpeggio** il basso riprende le note dell'accordo che l'arpeggio sta girando, non sempre la nota esatta
  appena suonata: un arpeggio cambia ordine con l'energia.
* **Una cosa vecchia che ho visto adesso** (c'è almeno dalla 0.23, non l'ho toccata): in un progetto **senza
  tonalità** (scala CHROMATIC, com'è un progetto nuovo) l'arpeggio di una BAND viene scritto una quinta sopra le altre
  parti. Se scegli una tonalità (HOME 3: K2 la tonica, K3 la scala) è giusto. Si può correggere nella prossima
  versione: dimmi se lo vuoi.

## La mappa dei generatori

Mi avevi chiesto di occuparmi delle "troppe strade per la stessa cosa". **La mappa è fatta**: è il file
`MAPPA-GENERATORI.md` che ti consegno insieme agli altri. Dice cosa fa ogni generatore, dove due strade fanno la stessa
cosa (ne ho trovate nove), e ti propone quattro cose da unire o nascondere.

**Non ho unito né nascosto niente**: sono scelte tue. Dimmi quali proposte vuoi e le faccio nella prossima versione.
In fondo alla mappa c'è una tabella "Voglio... uso..." che vale già oggi.

## Cosa manca ancora

* **Il manuale riscritto da capo** "com'è adesso": non è fatto. Il manuale è **aggiornato** alla 0.26 (le sette cose
  nuove sono nei loro capitoli, le tabelle e i nomi dei file sono a posto), ma non è riscritto. Nella guida di
  riferimento in inglese i capitoli "cosa c'è di nuovo" delle versioni vecchie sono passati nella storia.
* **Il nome del manuale** nell'elenco dei tuoi documenti dice ancora 0.25: da qui non riesco a cambiarlo, lo puoi
  rinominare tu. Dentro, il titolo è già 0.26.
* **Il controllo tecnico**: fatta la parte più importante (quanto è provato, le righe mai eseguite, gli errori
  trovati, le prove rotte apposta, i controlli sul codice del Pi: nessun errore vero). Mancano alcune prove su parti
  vecchie che nessuna prova tocca (la song con il tempo per riga, due motivi dell'OCTAVE, l'LFO su CHANCE e SWING).
* **I tempi sullo strumento**: rifare una parte costa, sul computer, circa una volta e mezza la 0.25 in 4/4 e il
  doppio in un metro dispari. Sull'FM-1 va misurato.

## La dimensione

Il firmware cresce di 17.288 byte: 476.948 su 581.564 (la 0.25: 459.660). La RAM cresce di 320 byte: 72.096 su
98.304 (la 0.25: 71.776). C'è posto per tutti e due: restano libere più di 100.000 byte di firmware. Le misure sono
della build di GitHub.
