# L'esploratore: il firmware provato tutto, in pochi minuti

`tests/sagga_explore.py` fa al firmware quello che faresti tu provandolo, ma ogni gesto, in ogni situazione, e senza
stancarsi. Gira sul computer, senza l'FM-1: il firmware vero (lo stesso `firmware/src/dinghy.c` che va sull'FM-1) è
compilato per il PC con il simulatore (`tests/host.c`), che va circa 400 volte più veloce del tempo vero.

```sh
python3 tests/sagga_explore.py            # tutto: circa 3 minuti e mezzo
python3 tests/sagga_explore.py --veloce   # un minuto: le situazioni e i gesti principali (è nella suite dei test)
```

Alla fine scrive `build/explore/RAPPORTO.md` (cosa non va, e come rifarlo), `build/explore/EFFETTI.md` (per ogni gesto,
cosa cambia) e `build/explore/rapporto.json`.

## Come lavora

1. **Le situazioni.** Prepara la macchina in 29 modi (erano 12 nella 0.12, 23 nella 0.24, 28 nella 0.26): vuota ferma e in play, una band TECHNO in play, una HOUSE con
   l'armonia su LOCK, una BALANI ferma (0.29; prima era AMAPIANO), una progressione USER con FOLLOW RETRIG e 3+3+2, GENRE LIVE, VIAGGIO, PERF,
   note lunghe con un loop fra due step, il grid attaccato, e (0.12) una band JUNGLE con la traccia 1 in BREAK; 0.13 e 0.20: tre con le cose nuove di allora (CHAIN LIST e MOTION, gli LFO, i MIDI FX in catena); 0.18: **il
   tablet e il grid insieme** (REMOTE 13 + 14, il grid, la band in play), con una e con due porte USB (con due i valori
   tornano al hub sulla porta 2). 0.23: **cinque con i motori THEORY**: una band TECHNO; una REGGAETON
   (regole scritte a mano dalla 0.29) con GENRE LIVE; SOURCE FREE (nessun genere) con pattern di quattro battute, ferma; una GQOM
   (0.29; prima era AMAPIANO) con il tablet e il grid; una HOUSE sulle MOSSE, dove RISER, DROP e l'energia riempiono e svuotano quello che i motori hanno fatto.
   0.24: **una con le lunghezze**: una band TECHNO con la traccia 1 da 32 step (la seconda battuta sono le copie del
   pattern) e la traccia 8 da 19 (tre copie: il polimetro), sulle MOSSE con le mosse **alla battuta**: così una mossa
   chiesta (LONGER e SHORTER comprese) è già successa quando la sonda guarda, due battute dopo. Nelle altre situazioni
   le mosse aspettano la fine della frase, 16 battute, e la sonda le vede solo in coda. E ogni situazione che nel nome
   promette una lunghezza viene controllata prima di cominciare: la 0.24, alla prima stesura, aveva lasciato "pattern
   di quattro battute" a esplorare tracce da una battuta sola (SAVE 2 K4 non era più LIBRARY LENGTH), e niente lo
   diceva.
   0.25: **quattro con le cose nuove**. **Il 7/8** (una battuta di 14 step, 2+2+3): una band TECHNO dei motori fatta in
   quel metro, la traccia 2 da 28 step (due battute) e la traccia 8 da 19 (la polimetria), le mosse alla battuta.
   **Il 5/4** (20 step): la band HOUSE della libreria, l'armonia accesa (un accordo ogni 20 step), la traccia 1 da 40.
   **I poliritmi**: la traccia 3 a 1/4 5:4 con un loop di cinque step, la traccia 5 a 1/16 7:4, un TURING lungo quanto
   la traccia che gira. **La melodia**: la band FREE dei motori, una progressione USER che cambia accordo dentro la
   battuta (3+3+2), il LEAD sulla traccia 8 in MELODY e selezionato, così le manopole della traccia girano sulla
   melodia. E il controllo "una situazione è quello che dice" adesso guarda anche altri valori promessi dal nome: la
   quarta situazione parte solo se la traccia 8 è davvero in MELODY con FOLLOW acceso, e l'armonia accesa e non su LOCK.
   0.26: **una con le cose nuove**. Una battuta di 20 step (5/4), una band FREE dei motori **nata in cinque**, con le
   risposte fatte di note; le scene portano il metro (GLO 4 K3); il CLICK acceso mentre suona, come nota sul canale
   MIDI 10 (SAVE 5); KEYBOARD su CHORDS (SAVE 4). Il nome della situazione promette che il LEAD e il BASS sono pattern
   fatti nel modo nuovo (`thv` 3), e viene controllato prima di cominciare.
   0.27: **una con le cose nuove**. Una band dei motori in un progetto **senza tonalità** (dove l'arpeggio andava una
   quinta sopra), EVOLVE acceso sul banco ogni 16 battute con **RETURN 50**, il profilo **SEMPLICE** (le pagine SEQ 2 e
   SEQ 3 si vedono solo mentre suonano: qui SEQ 3 c'è, EVOLVE è acceso), in play. Il nome promette il profilo, EVOLVE
   e il RETURN, e viene controllato prima di cominciare.
   0.28: **una con le cose nuove**. Le tracce sono dodici: una band TECHNO, la **traccia 12** scelta (la banca 9-12, che
   ne ha quattro), un **accordo di sei note** sul suo primo passo (SEL + sei tasti), i **lock delle lane 7 e 8** (ENV 7
   e 8), in play. Il nome promette la traccia scelta, le sei note e i lock: la sonda ha due valori nuovi per traccia,
   `poly` (quante note ha il passo scritto più pieno del pattern) e `lx` (i passi con un lock sulle lane 7 o 8), e
   viene controllata prima di cominciare. ENV ha otto pagine: l'esploratore gira le manopole anche sulle lane 7 e 8.
2. **I gesti.** Più di 5000 (0.23: 5416 con il grid e il tablet, 2901 senza): ogni bottone da solo e tenuto con un altro; ogni manopola su ogni pagina di HOME, GLO, SEQ,
   ENV, LFO, ARP e SAVE (le pagine della 0.12), con e senza SEL, avanti, indietro, e avanti-e-indietro; ogni tasto
   della tastiera da solo e con ogni modificatore (SEQ, HOME, FX, EDIT, ARP ... e **ogni gruppo + SEL: il PICK**); i gesti
   a due step (la nota lunga, e con SEL + FX il loop); i tasti tenuti della 0.12 (REC = TAKE, SEL + GLO = viaggio off, GLO +
   SEL + OCT); **le finestre** (un tocco su HOME, SEQ, EDIT, ENV, LFO, ARP o FX, poi un tasto, una manopola o una pagina,
   poi il tocco che chiude); il MASTER; i bottoni e i 128 pad del grid in ogni vista (FOLLOW compresa); 0.18: **i comandi
   del tablet** (SAGGA Live sul canale 12, TRACK sul canale 13: ogni manopola con un paio di valori, ogni interruttore
   acceso e spento, ogni tasto), solo nelle situazioni con il tablet. Nelle sessioni di quelle situazioni pannello, tablet
   e grid sono un terzo dei gesti ciascuno.
3. **Una copia per gesto.** Il simulatore prepara la situazione una volta, poi si copia (`fork`) per ogni gesto:
   ogni copia parte dalla stessa identica macchina, fa il suo gesto e guarda tutto lo stato (ogni impostazione di ogni
   traccia, l'armonia, la tonalità, i canali, i pattern ...) subito dopo, dopo due battute e dopo lo STOP. Una copia
   che non fa niente dice cosa cambia da solo con il tempo (gli accordi che girano, i dadi di EVOLVE ...): l'effetto
   di un gesto è la differenza con lei.
4. **Le coppie.** Poi 400 coppie di gesti per situazione: il secondo misurato contro il primo da solo. Così si vede,
   per esempio, se dopo aver caricato una band sfogliare i generi cambia gli accordi.
5. **Le sessioni.** Poi 200 sessioni di 60 gesti a caso. Se una rompe una regola, l'esploratore la riprova togliendo
   un gesto alla volta finché resta solo quello che basta a farlo succedere: il rapporto dà quella sequenza corta.

## Le regole

| regola | cosa non deve succedere |
| --- | --- |
| SFOGLIARE | sfogliare (pagine, cursore, traccia, genere, parte e variazione della libreria) che cambia la musica o l'armonia |
| ARMONIA | l'armonia che cambia senza che tu la tocchi (ARP 3-6, DICE PROG; erano SEQ 4 e 8 fino alla 0.11) o carichi qualcosa di un genere |
| LOCK | con l'armonia su LOCK, qualcosa che non sia ARP 3-6 o DICE PROG che la cambia |
| CANALE | il canale MIDI di una traccia cambiato da chi non deve (BAND, un dado, una manopola qualunque) |
| NOTE SCRITTE | BAND o KIT che cambiano la nota di una traccia dove hai scritto qualcosa |
| FASE | due battute dopo un gesto, una traccia che non è dove la battuta dice |
| COPIE | 0.24: due battute dopo un gesto (e alla fine), le copie di un pattern fuori posto: nel pattern che suona devono essere la fine del loop, ognuna uguale allo step del pattern che ripete; dopo il loop, in ogni pattern della traccia, solo il segno di dove il pattern finisce (uno step in pausa). Non guardata su una traccia TAPE, né mentre un loop fra due step o un LOOP del viaggio tiene la lunghezza |
| NOTE APPESE | dopo lo STOP, una nota accesa e mai spenta |
| CLOCK | il clock MIDI che salta (tanti tick quanti ne vuole il tempo) |
| MIDI | byte MIDI non validi |
| MORTO | il firmware che si pianta, o (con i sanitizer) un errore di memoria |
| RITORNO | una manopola girata di uno e poi indietro che non rimette la musica dov'era (da guardare) |
| MOTORI | 0.23: da fermo, un pattern fatto dai motori THEORY che non è all'ENERGIA della macchina, o di cui i motori ricordano uno stile che non esiste. 0.25: o che non è nel METRO della macchina (i motori lo rifanno quando il metro cambia); uno cambiato a mano resta nel suo metro, e lì l'energia non lo tocca. Dalla 0.25 la regola guarda anche la fine di ogni sessione |

Le regole sono scritte in fondo al file, una funzione ciascuna, con le eccezioni volute (`HARM_OK`, `CH_OK`,
`ACCETTATI`): aggiungerne una è qualche riga. Con i sanitizer trova anche gli errori di memoria:

```sh
SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -g" python3 tests/sagga_explore.py
```

## Per guardare un caso da vicino

```sh
python3 tests/sagga_explore.py --solo "TECHNO band in play" --gesto "SEQ 1 PRESETS +1" --vedi
```

stampa lo stato prima e ogni campo che il gesto cambia (dopo, dopo due battute, da fermo) e quante note sono uscite.

## Per cercare più a fondo

Le sessioni a caso sono quelle che trovano le cose rare (due o tre gesti che da soli non fanno niente). Con un altro
seme sono altre sessioni; più lunghe ne contengono di più:

```sh
python3 tests/sagga_explore.py --sessioni 2000 --lunghe 150 --seme 58
```

Quattrocento sessioni da 60 gesti girano in circa 30 secondi.

## Cosa ha trovato

* **Sulla 0.10** (`SAGGA_EXPLORE_ROOT` = un albero 0.10): in 19 secondi, `SEQ + PRESETS` che cambia il genere da cui
  vengono gli accordi, cioè il problema delle tue note; e una traccia fuori fase dopo aver cambiato direzione (FWD,
  REV) mentre suona, che nessuno aveva notato.
* **Sulla 0.11**, da soli e in coppia: tre tracce fuori fase, corrette: dopo un cambio di direzione, dopo essere
  passata da TAPE e tornata, dopo un UNDO che rimette l'inizio del loop (`t011_in_time_after`).
* **Sulla 0.11**, nelle sessioni lunghe (cose che nessun gesto da solo fa): un dado rimesso com'era dopo una lunghezza
  cambiata in battuta, o sopra una traccia in TAPE; un loop di VIAGGIO lasciato a mano (in una sessione di 47 gesti che
  non si lascia accorciare: conta quando arriva ogni gesto); STOP dentro un DJ LOOP e poi CONTINUE; una cosa cambiata
  da fermo (la direzione, un dado rimesso) e poi CONTINUE (2 gesti: HOME 2 K1, SEL + PLAY); un RELOAD di una traccia a
  cui VIAGGIO aveva cambiato il loop (3 gesti: salva, HOME 8 ALG, SEL + SAVE). Corrette tutte; ognuna è una sessione di
  `t011_explorer_sessions`, che la rifà a ogni giro dei test.

* **Sulla 0.23**, in una sessione delle situazioni nuove con i motori: uno **snapshot** richiamato dopo aver cambiato
  la DIREZIONE di una traccia la lasciava uno step fuori dalla battuta (3 gesti: SAVE + SEL + nero 1, HOME 2 K1, SAVE +
  nero 1). Non c'entrano i motori: succedeva in ogni situazione, dalla 0.11. Corretto; è il test
  `t023_snapshot_direction`. La regola MOTORI è stata provata rompendo apposta il servizio dei motori in una copia del
  firmware: 17 errori sulle MOSSE, zero sul firmware vero.
  Il giro completo della 0.23, a errore corretto: 73.819 gesti da soli in 22 situazioni, 8.797 coppie, 200 sessioni
  da 60 gesti, nessun errore; la suite di nuovo con AddressSanitizer e UndefinedBehaviorSanitizer, nessun errore.

* **Sulla 0.24** (la lunghezza è della traccia, le copie): la regola nuova **COPIE** e una situazione nuova, con le
  copie nel loop e le mosse alla battuta. Il giro completo: 76.720 gesti da soli in 23 situazioni, 9.197 coppie, 200
  sessioni da 60 gesti, nessun errore, nemmeno di COPIE; in più 200 sessioni tutte nella situazione nuova, nessun
  errore. La regola è stata provata rompendo apposta il servizio delle copie in una copia del firmware: 150 sessioni
  corte, 5 errori COPIE (il primo: `copie fuori posto dopo due battute: T1 (dal gesto 34 ...)`), zero sul firmware
  vero; nella situazione nuova, con la stessa rottura, bastano i gesti da soli: 73 errori COPIE. La situazione nuova, al primo giro, ha fatto vedere due cose che le regole non conoscevano, tutte e due il
  firmware come deve essere: sulle MOSSE **K3 è il genere**, una mossa, e l'armonia lo segue (finché le mosse
  aspettavano la fine della frase nessuna sonda lo vedeva arrivare: adesso ARMONIA lo sa); e l'**inizio del loop**
  spostato e rimesso lascia le copie come step (è fra i "Visti e voluti" del rapporto). Un limite da sapere: un
  errore che vuole tre gesti precisi di fila (uno snapshot salvato, una lunghezza cambiata, lo snapshot richiamato)
  l'esploratore lo trova solo se il caso glieli mette in fila; per quelli ci sono le prove fisse del simulatore
  (`t024_copies`), che lo rifanno a ogni giro.

* **Il banco della 0.23 sull'FM-1 vero** (i file datati 26 ottobre 2026 dall'orologio del Pi, che era indietro: il
  banco, 4 sessioni; l'FM-1 completo, 28): i motori
  THEORY sull'FM-1 fanno le stesse parti del simulatore (le otto sessioni con i motori, uguali sonda per sonda), e
  nelle 28 sessioni le note sono le stesse, 28.068. Il rapporto segnava
  cinque cose; guardate una per una, quattro erano tempo o la prova stessa: un dado dal grid preso 1 ms dopo, il
  saluto del bridge mandato dopo la fine della sessione, il tasto di un loop letto 6 ms dopo a 300 BPM, un THROW
  girato 9 ms dopo. La quinta era vera: **sei messaggi che l'FM-1 aveva mandato e il Pi non aveva sentito** (in s014
  tre tick del clock, in s015 un tick e due note-off nello stesso istante), e una di queste due sessioni il rapporto
  non la segnava nemmeno. Da lì viene la 0.23.1 del confronto: le due prove nuove sul tempo, la regola PERSI, e i
  CONTI, con cui l'FM-1 dice quello che ha mandato e la prova dopo dirà da che lato un messaggio si perde. Rifatto
  sulle stesse due raccolte: il banco 0 errori; l'FM-1 completo 2 errori, i due PERSI.

* **Il banco della 0.24 sull'FM-1 vero** (17 novembre 2026; i file portano la data del 26 ottobre, quella
  dell'orologio del Pi): il banco, 21 sessioni, e l'FM-1 completo, 28. **Zero errori in tutte e 49 le sessioni**, niente
  da guardare, 47 note di TEMPO (sonde prese sul confine di uno step, tasti letti qualche millisecondo dopo: gli stessi
  casi della prova della 0.23). Il codice nuovo ha girato davvero sull'FM-1: nei messaggi si leggono `LENGTH 32: THE 16
  STEPS REPEAT`, `THE COPIES ARE YOUR STEPS NOW`, `LENGTH n AT THE BAR`. I sei messaggi persi della 0.23 non si sono
  ripetuti: PERSI 0, e l'FM-1 dice di aver mandato 402.973 messaggi senza scartarne uno (la causa di allora resta
  sconosciuta). Due cose sono venute fuori da quella prova. **LONGER e SHORTER non sono capitati in nessuna delle 49
  sessioni**: restano da provare a mano sull'FM-1. E durante l'installazione del firmware il bridge del grid si era
  attaccato al programma di caricamento ("Felucca Update") e gli mandava il suo saluto ogni secondo: non ha fatto
  danni, ed è corretto nella 0.25.

* **Sulla 0.25** (il metro, i poliritmi, i motori che si ascoltano, la melodia che conosce l'accordo): quattro
  situazioni nuove (sopra), e il controllo che una situazione sia quello che il suo nome dice guarda anche altri
  valori (`want`: l'armonia accesa e non su LOCK, la traccia 8 in MELODY). Il giro completo: **89.842 gesti da soli in
  27 situazioni, 10.796 coppie, 200 sessioni da 60 gesti, nessun errore, niente da guardare**. Al primo giro c'era una
  cosa da guardare, e si è vista perché la situazione della melodia lascia selezionata la traccia 8 e non la 1: la nota
  di uno step girata e rimessa (EDIT, SEL + K1) lascia la penna su quella nota. È il firmware come deve essere (la penna
  è l'ultima nota scritta): adesso è fra i "Visti e voluti", solo per quel campo. La regola **MOTORI** adesso
  guarda anche il metro, e la fine di ogni sessione: provata rompendo apposta il servizio che rifà i pattern dei motori
  nel metro nuovo, nella situazione del 7/8 ha dato 14 errori (le manopole di GLO 4, e sei sessioni ridotte a due
  gesti: `T1: fatto nel metro 21, la macchina e' nel metro 24`), zero sul firmware vero. Un limite da sapere: se al
  cambio di metro le tracce non ripartissero insieme dalla battuta nuova, l'esploratore **non** lo vedrebbe. La sua
  regola FASE misura ogni traccia contro il suo punto di partenza, non contro la battuta, e una traccia può stare
  fuori dalla battuta anche per scelta (RETRIG, un pattern che entra al BEAT). Quel caso lo guardano le prove fisse
  (`t025_metre`: rotto apposta, tre prove falliscono).
  Le prove fisse della 0.25 (`t025_*`, 68 controlli nel simulatore, più quelle del cuore e dei motori) sono state
  provate rompendo il firmware in dodici punti, uno alla volta: tutte e dodici le rotture trovate. Le prove del
  simulatore di nuovo con AddressSanitizer e UndefinedBehaviorSanitizer: nessun errore.

* **Sulla 0.26** (il click, gli accordi dal vivo, il metro delle scene, SMOOTH, il pedale e le rotelle, i motori nella
  battuta, le risposte con le note): una situazione nuova (sopra), e SAVE ha una pagina in più da sfogliare. Il giro
  completo: **94.367 gesti da soli in 28 situazioni, 11.197 coppie, 200 sessioni da 60 gesti, nessun errore, niente da
  guardare**. Un falso allarme del giro della 0.25 è stato capito e tolto: nelle coppie, dopo un gesto che apre le
  MOSSE, la manopola ALG non sfoglia niente: sceglie *quando* parte una mossa in coda (PHRASE, BAR, BEAT). L'esploratore
  la trattava come "sfogliare" e segnalava che la musica era cambiata; adesso lì è un comando. Il piano per l'FM-1 vero
  che va nello zip del Pi prende **ogni** situazione una volta (il numero era scritto a mano, 24, e le ultime
  situazioni della 0.25 ne restavano fuori): 27 sessioni più 4 con il tablet. Il banco: 26.
  Le prove fisse della 0.26 (`t026_*`, 83 controlli nel simulatore, più quelle del cuore e dei motori) sono state
  provate rompendo il firmware in diciannove punti, uno alla volta: tutte e diciannove le rotture trovate. Le stesse
  prove con AddressSanitizer e UndefinedBehaviorSanitizer: nessun errore. L'analizzatore statico di clang su tutto il
  firmware: quattro avvisi, nessuno vero (li ho guardati uno per uno).

* **Sulla 0.27** (il profilo SEMPLICE, RANDOM come un dado, il RETURN di EVOLVE, chi sta agendo, l'arpeggio senza
  tonalità): una situazione nuova (sopra). Il primo giro completo ha trovato **un errore vecchio**, della 0.24, in una
  sessione della HOUSE dei motori sulle MOSSE, ridotta a tre gesti: la traccia uno step più corta del suo pattern
  (HOME 1 K2 -1: il pattern aspetta intero dopo il loop, con il segno della sua fine), la finestra EDIT e OCT+ (il
  cursore sul segno), ENV 5 K1 -1. Due battute dopo le copie erano fuori posto (regola COPIE). ENV K1 girato verso il
  basso su un passo senza lock non scriveva niente, ma segnava il passo come scritto: il segno non era più un segno, e
  un passo così, acceso dopo con un tasto, suonava la nota 60 e non la penna della traccia (su una cassa, un altro
  suono). Corretto: sono i test `t027_mark` (il simulatore) e `test_v027_mark` (il cuore). La stessa sequenza con un
  lock vero (ENV 5 K1 +1) o con EDIT K1 sul segno falliva sulla 0.26 e passa sulla 0.27. Il giro completo, a errore
  corretto: **97.380 gesti da soli in 29 situazioni, 11.597 coppie, 200 sessioni da 60 gesti, nessun errore, niente
  da guardare**. Le prove fisse della 0.27 (`t027_*`, 32 controlli nel simulatore, più quelle del cuore e
  dell'editor) sono state provate rompendo il firmware in ventitré punti, uno alla volta: tutte e ventitré le rotture
  trovate. Le stesse prove con AddressSanitizer e UndefinedBehaviorSanitizer: nessun errore. Il piano del banco: 27
  sessioni.

* **Sulla 0.28** (dodici tracce, accordi di sei note, otto lane): una situazione nuova (sopra), e ENV ha otto pagine.
  La fuzz con i rilevatori (UndefinedBehaviorSanitizer) ha trovato subito **un errore della 0.28 stessa**: in HOME e in
  PERF la striscia dello schermo disegnava le celle 13-16 come tracce, leggendo oltre le dodici (senza i rilevatori non
  si vedeva). Corretto: le celle 13-16 sono spente, e lo guarda il test `t028_panel`. Il primo giro completo ha segnato
  una coppia sulle MOSSE (ARMONIA: GLO 3 SEL + K3, poi ALG): il genere chiesto con K3 aspetta la fine della frase, ALG
  porta le mosse alla battuta e il genere, con l'armonia che lo segue, arriva dentro le due battute della sonda. Il
  cambio è di K3, una mossa: è fra i "Visti e voluti". E i due valori nuovi della sonda, `poly` e `lx`, vedono lo step
  che una manopola ha scritto e riscritto (SET, un lock al valore di prima): come gli hash, RITORNO non li guarda. Il
  giro completo: **102.073 gesti da soli in 30 situazioni, 11.995 coppie, 200 sessioni da 60 gesti, nessun errore,
  niente da guardare**. Le prove fisse della 0.28 (`t028_panel` nel simulatore, `test_v028_image` nel cuore, la 0.27
  vera presa da git in `tests/sagga_compat27.sh`, l'editor, il convertitore MIDI, le pagine SAGGA) sono state provate
  rompendo il firmware e il Pi in dieci punti, uno alla volta: tutte e dieci le rotture trovate. Il piano del banco: 28
  sessioni; l'FM-1 completo: 33.

* **Il banco della 0.27 sull'FM-1 vero** (19 novembre 2026; i file portano la data del 26 ottobre, quella dell'orologio
  del Pi): il banco, 27 sessioni, e l'FM-1 completo, 32. Nessun blocco, nessuna nota appesa, nessun messaggio perso
  dall'FM-1, il clock giusto. Al primo confronto 6 cose diverse dal simulatore e un comando di una pagina mai arrivato;
  guardate una per una, **nessuna era un errore del firmware**:
  * s021 e b020: la sonda letta un tick di clock prima dal FM-1, proprio sul tick che cambia qualcosa (il pattern che
    una coda cambia sulla battuta; il THROW FILTER che scivola: -10 e -9). Alla sonda dopo, uguali.
  * b027: il dado della pagina Motori. L'FM-1 prende un messaggio dall'USB e lo lavora nel suo giro del ciclo, fino a
    8-9 ms dopo (il simulatore: 1 ms); con il messaggio spostato così, il simulatore tira lo stesso dado.
  * b024: la traccia 5 in 7:4 dentro un loop DJ di un 16esimo, uno step indietro per cinque sonde di fila: il passo di
    un poliritmo comincia fra due tick, e l'FM-1 lo fa al suo giro, pochi ms dopo. Poi di nuovo uguali.
  * b007: due note del simulatore 23 e 30 ms dopo l'ultimo messaggio che il Pi ha sentito (aveva chiuso le porte): il
    bordo della finestra.
  * b022: il tasto PROPOSAL della pagina Live manda 127 e 0 nello stesso istante; l'FM-1 ha sentito il 127, lo 0 si è
    perso per strada (8 coppie su 9 della sessione sono arrivate intere). L'FM-1 agisce alla pressione: non ha fatto
    niente di meno.
  Il confronto ora riconosce questi casi, e le prove del confronto controllano che resti un errore quello che
  non torna uguale. Sulle stesse due raccolte: **il banco 0 errori, 1 da guardare (il rilascio di PROPOSAL); l'FM-1
  completo 0 errori**. Restano da capire i riavvii lenti: 6 volte su 59 l'FM-1 non ha risposto entro 12 secondi dopo il
  riavvio fra due sessioni, e il Pi l'ha fatto ritrovare all'USB; alla fine il kernel del Pi ha scritto degli errori
  USB (`urb status -32`). È sempre tornato, e il firmware non si è mai piantato.

Il modo di lavorare è quello: l'esploratore trova una sequenza corta, la sequenza diventa un test, il test fallisce
sul firmware vecchio e passa su quello corretto.

## Sull'FM-1 vero

Il simulatore ha il codice dell'FM-1 ma non il suo compilatore (un errore come quello del flag DENSITY della 0.11 si
vedeva solo ottimizzando), né i suoi tempi (lo schermo che si disegna, l'USB). Per questo la 0.11 ha il **test dal PC**
(`firmware/src/sagga_test.c`): con il tuo sì (SEL sull'FM-1) il PC preme i tasti, gira le manopole e suona la tastiera
dell'FM-1 vero, e l'FM-1 gli manda tutto il suo stato, la stessa sonda del simulatore.

```sh
python3 tests/sagga_explore.py --hw-piano /mnt/c/Users/user/Downloads/sagga-esploratore    # il piano, i file per Windows
#   ... su Windows: run_hw_explore.ps1 (tools/hwtest/LEGGIMI.md): l'FM-1 fa le sessioni, il PC tiene tutto ...
python3 tests/sagga_explore.py --hw /mnt/c/Users/user/Downloads/sagga-esploratore/raccolta-<data>.json
```

Il piano sono le sessioni a caso dell'esploratore (una situazione, 60 gesti, una sonda dopo ognuno), con quello che una
mano fa sul pannello e (0.18) il MIDI che entra: i comandi del tablet e i pad e i bottoni del grid, che il PC manda come
eventi del test e l'FM-1 prende come se arrivassero dalla porta del remoto (il PC al posto del Pi; il keep-alive del
grid ogni 1,5 s). `--hw-tablet N` aggiunge N sessioni con il tablet e il grid; un piano con eventi MIDI vuole sull'FM-1
la versione con cui è fatto, la 0.20 o più recente (il programma di Windows lo controlla). Ogni sessione parte da un riavvio dell'FM-1 nel test: nessun progetto, nessuno slot letto
o scritto, come il simulatore appena acceso. L'FM-1 dice dove ha preso ogni evento: il suo millisecondo e il suo tick di
clock. Il confronto rifà la sessione nel simulatore con ogni evento esattamente lì (fra gli stessi due tick), quindi le
due macchine devono essere uguali sonda per sonda, anche se il PC o l'FM-1 sono arrivati in ritardo. Il rapporto
(`build/explore/RAPPORTO-HW.md`) dice:

| regola | cosa |
| --- | --- |
| SIMULATORE | l'FM-1 diverso dal simulatore, dalla sonda dove comincia: il campo, i due valori, gli ultimi gesti |
| MORTO | il firmware piantato (vettore e PC del crash), un riavvio da solo, l'FM-1 che non risponde più |
| FASE, NOTE APPESE, COPIE (0.24) | le stesse regole, sui dati dell'FM-1 |
| PERSI | 0.23.1: un tick, una nota o un note-off che il simulatore manda e il computer non ha sentito dall'FM-1, **uno per uno, con il momento**. Le due liste sono messe una accanto all'altra, tipo per tipo e nota per nota; un messaggio arrivato in ritardo e quello che lo raggiunge si cancellano. Fino alla 0.23 le note si contavano dai note-on e i tick con due di margine: un note-off perso non si vedeva |
| CONTI | 0.23.1, con SAGGA SEQ 0.23.1 sull'FM-1: quello che l'FM-1 **dice di aver mandato** (lo conta lui, per porta e per tipo, e tiene i conti della sua coda USB) contro quello che il computer ha sentito e quello che ha ricevuto il suo driver USB. Dice dove un messaggio si è perso: dentro l'FM-1, per strada, o nel computer |
| NOTE, CLOCK | le note e i tick che escono dall'USB contro quelli del simulatore: nessuno perso per strada (0.18: non le luci del grid sul canale 16, ne' gli interruttori degli LFO che tornano al tablet, note 100-115 sul canale 13) |
| CICLO | il ciclo principale fermo più di 60 ms |
| TEMPO | visto, non un errore: una sonda presa sul tick in cui comincia uno step (gli step soli, di uno, e di nuovo uguali entro tre sonde; con loro il pattern che una coda cambia alla fine del loop), un messaggio che su una macchina è appena scaduto, o un gesto che l'FM-1 ha letto pochi ms dopo: il confronto prova a spostare gli eventi di quel gesto di 1-15 ms e se con uno spostamento il simulatore fa la stessa cosa lo tiene e va avanti (REC e TAKE scrivono le note al millisecondo). 0.23.1, due prove in più quando quelle non bastano: i messaggi che l'FM-1 ha **sentito dalle porte** prima di quella sonda (un pad del grid, un comando di una pagina) presi 1-3 ms prima o dopo; e **un solo evento di uno dei cinque gesti prima**, fino a 20 ms dopo, perché quello che un gesto mette in moto a volte si vede solo più tardi (il tasto di un loop tenuto a cavallo di un tick a 300 BPM, un THROW che finisce di scivolare una battuta dopo). Se una prova toglie una parte delle differenze senza farne di nuove, la tiene e cerca il resto da capo. Dal banco della 0.27: una sonda letta un tick di clock prima o dopo, **qualunque cosa mostri**, se alla sonda dopo è di nuovo uguale (il tick che cambia il pattern sulla battuta, un THROW che scivola); il passo di un **poliritmo** uno step avanti o indietro anche per più sonde di fila, se torna uguale mentre suona (l'FM-1 lo fa al suo giro del ciclo); i messaggi sentiti dalle porte spostati **fino a 9 ms** (l'FM-1 li lavora nel suo giro, fino a 8-9 ms dopo averli presi) |

Le note e il clock si contano solo fin dove il PC ha ascoltato (chiude le porte quando riavvia l'FM-1 per la sessione dopo);
dal banco della 0.27: se le note non tornano, si contano di nuovo senza gli ultimi 40 ms, il bordo di quella finestra.
La prima volta sull'FM-1 vero (9 novembre 2026, 0.12): 20 sessioni, 0 errori; 19 di TEMPO, uno solo di un tasto letto 2 ms dopo.

`--hw-prova` fa tutto con il simulatore al posto dell'FM-1, con il costo dello schermo acceso (gli eventi arrivano in
ritardo come sul vero): deve dire che è tutto uguale, ed è nella suite dei test.

## Il banco: l'FM-1, il Pi e il grid insieme (0.20.3)

Dal PC il tablet e il grid sono finti: il PC manda i loro messaggi come eventi del test. Il **banco** gira sul Pi e
passa per le strade vere: le sei pagine SAGGA premute dentro RaspiMIDIHub con la sua API (il comando esce dalla pagina e
arriva all'FM-1 dalla matrice), il bridge del grid vero con due Launchpad finti, il pannello e le sonde con il test
dell'FM-1. Si lancia dalla pagina del Pi (**ESPLORATORE DEL BANCO**, `tools/hub/LEGGIMI.md`).

```sh
python3 tests/sagga_explore.py --banco-piano tools/hub/banco_piano.json    # il piano (make_release lo mette nello zip)
#   ... sul Pi: la pagina del hub, Avvia la prova ...
python3 tests/sagga_explore.py --banco raccolta-banco-<data>.json         # -> build/explore/RAPPORTO-BANCO.md
```

Il piano: una sessione da 40 gesti per ogni situazione con il tablet e il grid (REMOTE 13 + 14 e il grid attaccato,
poi ognuna delle situazioni dell'FM-1: 28 dalla 0.28, 27 nella 0.27, erano 26 nella 0.26, 25 nella 0.25, 21 nella 0.24 e 20 prima); un gesto su due è una cella di una pagina (ogni cella di ogni pagina almeno una
volta nel giro), gli altri il pannello e il grid. Dalla 0.20.3 l'FM-1, se il test glielo chiede, ascolta le sue porte e
dice ogni messaggio che ha sentito, dove (il millisecondo, il tick del clock, la porta): il confronto rifà la sessione
con quei messaggi negli stessi punti, come gli eventi del test. In più del rapporto dal PC:

| regola | cosa |
| --- | --- |
| MATRICE | le celle che servono (ogni pagina verso la porta 2, la porta 2 verso le pagine) e quelle che non devono esserci |
| PAGINE | un comando che il Pi ha dato a una pagina e che l'FM-1 non ha mai sentito (la cella nella matrice?); una pagina che non risponde all'API; una cella con il CC cambiato da te (visto). Dal banco della 0.27: il rilascio di un tasto (lo 0 dopo il 127) perso per strada, con la pressione arrivata, è da guardare e non un errore: l'FM-1 agisce alla pressione |
| GRID | un messaggio del bridge che l'FM-1 non ha mai sentito |
| PONTE | un pad o un bottone che il bridge ha tradotto male |
| LUCI | le luci del bridge diverse da quelle che l'FM-1 aveva mandato; da guardare: le luci ferme dell'FM-1 diverse da quelle del simulatore |
| VALORI | un valore che l'FM-1 rimanda e che la cella della pagina non segue |
| SENTITI | l'FM-1 che non ascolta (firmware vecchio), pezzi di quello che ha sentito persi per strada, messaggi da un altro dispositivo |
| CELLE | 0.20.9: le celle dell'FM-1 che RaspiMIDIHub ha perso in un riavvio (il suo salvataggio automatico mentre l'FM-1 non c'era) e che il Pi ha rimesso (visto), o che non sono tornate (errore: allora VALORI è da guardare) |

Dalla 0.20.9, a ogni riavvio dell'FM-1, il programma del Pi: controlla che le celle dell'FM-1 siano tornate e rimette
quelle che RaspiMIDIHub ha perso; se l'FM-1 non risponde per 12 secondi lo fa ritrovare all'USB (un reset della sua
porta, come staccato e riattaccato) e aspetta altri 30 secondi; scrive nel log le righe del kernel sull'USB e i contatori
dell'FM-1 (il test risponde alla DIAG: i HELLO che ha sentito dal suo avvio, le risposte non partite, quando il Pi l'ha
configurato, quanto è rimasto fermo il suo giro principale), per capire da che parte stava un FM-1 che non rispondeva; e se l'FM-1 non torna, mette il progetto che aveva in memoria nella libreria del Pi
(`prima-del-banco-<data>.sgq`). Nel confronto una sonda letta un tick di clock prima o dopo, sul confine di uno step, è
TEMPO anche quando quelle dopo cadono sul confine come lei (le sonde vengono ogni 700 ms, sei step).

Dalla stessa pagina c'è anche **l'FM-1 completo**: il piano dell'esploratore dal PC (`--hw-piano`, 24 sessioni più 4
con il tablet e il grid; make_release lo mette nello zip come `hub/fm1_piano.json`) fatto girare dal Pi con lo stesso
programma, senza Windows. La raccolta si confronta con `--banco` come quella del banco.

`--banco-prova` fa tutto con il simulatore al posto dell'FM-1 (il bridge vero, i ritardi del Pi a caso) e deve dire
che è tutto uguale; poi perde i comandi delle pagine, e un pezzo di quello che l'FM-1 ha sentito, e deve trovarli. È
nella suite dei test, con `tests/sagga_banco_tests.py` (il programma del Pi contro un FM-1 e un RaspiMIDIHub finti).

## Cosa non vede
* Il suono e lo schermo: guarda lo stato e il MIDI, non come è disegnata una pagina.
* Le cose che succedono più in là di due battute (una mossa di VIAGGIO in coda per la fine della frase).
* Se una cosa è bella: dice cosa cambia e cosa rompe una regola. Se un effetto è giusto lo decidi tu, guardando la
  mappa degli effetti.
