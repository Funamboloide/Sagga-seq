# SAGGA SEQ 0.11 - Note di rilascio

La 0.11 è fatta delle annotazioni sulla 0.10, una per una: l'armonia che cambiava mentre sfogliavi i generi, le
lunghezze che saltavano, un algoritmo solo per traccia, una band di sette parti uguale per tutti i generi, sei
variazioni messe a caso, le progressioni solo sui gradi della scala, e un sequencer che ragionava a step singoli.
Il formato diventa **`SGQB`**, e questa volta **la 0.11 legge i progetti della 0.10** (`SGQA`): si aprono con le cose
nuove spente. Un progetto salvato dalla 0.11 non si apre sulla 0.10.

## L'armonia ha un genere suo

* Sfogliare i generi (SEQ + PRESETS, la vista BEAT) **non cambia più gli accordi**. La progressione viene dal genere
  dell'armonia, che segue quello della macchina solo quando di quel genere carichi davvero qualcosa: BEAT, KIT, BAND,
  PROG, GENRE LIVE che ricarica, VIAGGIO, uno snapshot.
* **HARMONY OFF / ON / LOCK** (SEQ 4 K1): con LOCK l'armonia resta dove l'hai messa qualunque cosa carichi, e i dadi non
  scelgono la progressione. **SEL + K2** su SEQ 4 sceglie a mano il genere dell'armonia.

## Le lunghezze cambiano in battuta

* Giri la lunghezza di una traccia mentre suona (HOME 1 K2, la riga LEN del grid): aspetta la battuta (`LENGTH 32 AT
  THE BAR`, la cella lo dice), poi la traccia riparte allineata.
* **Allungando, gli step nuovi si riempiono con il loop che c'era**: da 16 a 32 i sedici ripetuti, da 16 a 64 quattro
  volte. Accorciando e riallungando tornano gli step che erano scritti, intatti.
* Un pattern della libreria, o uno snapshot con un altro loop, caricati mentre suona atterrano **in fase** con la
  battuta, non sullo step 1 fuori tempo.

## Quattro algoritmi per traccia

* SEQ 2 mostra lo **slot** (`ALGO 1` .. `ALGO 4`): **SEL + K1** lo sceglie, K1 il suo algoritmo, K2-K4 i parametri.
* Suonano in ordine, a ogni step: un algoritmo di ritmo (TURING, CELL) sostituisce i colpi venuti prima, DENSITY li
  sfoltisce o li riempie, gli ACCENT si sommano. Un TURING sul ritmo e un DENSITY dopo: il ritmo cambia e poi si
  dirada. WRITE LIVE scrive tutto negli step e tiene gli ACCENT.
* Sul grid, vista TRACK 3: la riga dell'algoritmo lavora sullo slot mostrato, il pad 8 passa al successivo.

## Una band per ogni genere

* Ogni genere ha la sua **formazione, da 8 a 11 parti**: TECHNO cassa, clap, hat, open hat, ride, perc, rumble, basso,
  stab, pad; HOUSE cassa, clap, hat, open hat, shaker, perc, basso, piano, pad, vox; AMAPIANO cassa, clap, shaker, hat,
  rim, perc, log drum, basso, piano, pad, vox; DUB TECHNO cassa, rim, hat, shaker, perc, basso, accordi, pad ... (tutte
  in `tools/beat_parts.py`, modificabili).
* **25 ruoli** (HOME 4 K2): i sette della 0.10 più CLAP, OPEN HAT, RIDE, SHAKER, CONGA, TOM, RIM, CRASH, COWBELL,
  RUMBLE, SUB, LOG DRUM, STAB, PAD, PIANO, LEAD, VOX. Ognuno appartiene a una famiglia (cassa, rullante, hat, perc,
  basso, accordi, arp): COOK, i dadi e VIAGGIO li trattano come la famiglia.
* **BAND** (SEQ + SEL + nero 7) mette la formazione sulle tracce a cui hai dato quei ruoli, poi sulle tracce libere
  (prima le vuote). **Non tocca mai il canale** di una traccia, e cambia la nota solo su una traccia dove non è scritto
  niente e la nota è quella di partenza: le tracce che hai preparato tu restano tue. KIT fa lo stesso con le sole
  percussioni del genere.
* SEQ + SELECT scorre le parti del genere, PROG e KIT; sul grid la riga 2 della vista BEAT, a pagine se sono più di nove.

## 12 variazioni in ordine, e COOK che cammina

* **12 variazioni per le parti principali, 6 per le altre**, in ordine di somiglianza: la prima è la più tipica del
  genere, ogni successiva la più vicina alla precedente, la densità che sale, le stranezze in fondo. Sul grid: la riga 3
  della vista BEAT, pad 10 la pagina (1-6 / 7-12).
* **COOK su una traccia della libreria cammina verso la variazione successiva**: a ogni pressione cambia tanti step
  quanto dice HEAT (prima i sedicesimi deboli, il primo della battuta per ultimo; gli step bloccati restano):
  `COOK KICK #3: 2 TO GO`, poi `REACHED`, poi verso la seguente. **SEQ + SEL + COOK** (grid: SHIFT + COOK) è il COOK
  casuale di prima. Su una traccia scritta a mano COOK fa quello che faceva.

## Il Pi tiene altre variazioni

* Con il bridge nuovo, **SEQ + ALG oltre l'ultima variazione** continua in quelle del Pi (`#13/12+PI`), BEAT la carica.
* **SEQ + SAVE** manda il loop della traccia selezionata al Pi come nuova variazione della sua parte, nel genere della
  macchina (`ON THE PI: TECHNO KICK #25`).
* Il Pi parte con le 12 / 6 variazioni successive di ogni parte di ogni genere. La pagina dell'hub (porta 8090), sezione
  **PATTERN SUL PI**, le mostra genere per genere e ne cancella una. I file sono testo, uno per genere, in
  `/boot/firmware/sagga/patterns/` (`KICK	X...X...X..xX...	-`).

## Note con la loro durata

* La libreria non è più fatta di note da uno step: un pad tiene la battuta, un basso suona fino al colpo dopo, gli stab
  hanno la loro coda (il `-` nei pattern tiene la nota).
* RANDOM, EUCLID e i dadi danno alle note melodiche una durata secondo il ruolo; una traccia melodica il cui ritmo è
  fatto da un algoritmo tiene ogni nota fino al colpo successivo dell'algoritmo.
* **Tieni uno step e premi un secondo step: la nota dura fra i due** (contati tutti e due: dal 3 al 6 sono quattro
  step; `NOTE 3-6: 4 STEPS`). Sul pannello e sul grid. Il metodo di prima (EDIT, K1 il gate fino a 64 step) resta.
* **FX toccato da solo e poi lo stesso gesto: il loop fra i due step** della 0.10 (EXIT lo toglie). FX premuto insieme
  a un tasto, un bottone o una manopola non conta come tocco.

## Le progressioni

* **Ogni accordo può avere qualunque fondamentale**, le 12 sopra la tonica (SEQ 8 K3: I, bII, II, bIII, III, IV, #IV, V,
  bVI, VI, bVII, VII): il bVII e il bVI del minore epico, il bII di quello scuro. **K4 la forma**: l'accordo della
  scala su quella nota con un colore (TRIAD, 7, 9, SUS4, SUS2, 6), oppure una delle forme di CHORD (MAJ, MIN, MAJ7, MIN9,
  9SUS4, DIM7, M7B5 ...). I progetti 0.10 restano come erano (per grado).
* **SEL + K3: la durata dell'accordo in sedicesimi** (1-64), **SEL + K4: il PUSH** (0-4 sedicesimi in anticipo: l'accordo
  house che arriva prima della battuta). SEL + K2 scrive negli accordi le durate di un ritmo. Cinque slot: USER 1-4 e
  **DICE/PI**.
* **Quando cambiano gli accordi** (SEQ 4, SEL + K4 RHYTHM): BARS (ogni tante battute, K3, come prima), **GENRE** (quello
  del genere: house e garage spingono di un sedicesimo, reggaeton e dancehall 3+3+2), PUSH 16TH, PUSH 8TH, **3+3+2**
  (6, 6 e 4 sedicesimi: tre accordi a battuta), TWO A BAR, 3+5, 3+1, 2 BARS. I cambi restano al loro posto nella
  battuta: un ritmo di 2 o 3 durate si stende sugli accordi finché i due giri tornano insieme (3+3+2 su quattro accordi:
  quattro battute). L'armonia cambia su qualunque sedicesimo.
* **FOLLOW: HOLD, RETRIG, LEGATO** (SEQ 4, SEL + K1, per la traccia selezionata): una nota tenuta attraverso un cambio
  d'accordo resta sul suo (HOLD, come prima), viene ribattuta sul nuovo (RETRIG) o ci scivola (LEGATO: le note nuove
  partono prima che le vecchie finiscano, quelle in comune continuano; un synth mono fa il glide).

## I mood

* **Dieci mood**: SAD, MELANCHOLY, SATISFYING, ENERGETIC, EUPHORIC, EPIC, DREAMY, DARK, TENSE, SUSPENDED. Ogni
  progressione ne ha uno: quello che le dai tu (SEQ 8, SEL + K1) o quello che la macchina indovina da com'è fatta
  (accordi minori, il bVI e il bVII presi in prestito, la cadenza V-I, settime e none, i sus, il tritono, quanto corre).
* **MOOD** (SEQ 4, SEL + K3) filtra K2: passa solo per le progressioni di quel mood (`NO MORE EPIC` quando finiscono).
* **DICE PROG** (SEQ + SEL + nero 1): una progressione nuova del mood scelto nello slot DICE/PI, e suona subito.

## Il Pi tiene le progressioni

* Con il bridge nuovo, **SEQ 4 K2 oltre l'ultima progressione dell'FM-1** continua in quelle del Pi: del genere
  dell'armonia e del MOOD, **prima le più simili a quella che suonava** (`PI EPIC 3/8: i-bVI-bVII-i`). Ognuna entra in
  DICE/PI e suona; K2 indietro oltre la prima torna dov'eri.
* **SEQ + SAVE su SEQ 4** manda al Pi la progressione che suona, **su SEQ 8** quella che stai scrivendo, con il suo mood.
* Il Pi parte con **701 progressioni**, un file per genere, divise per mood e colorate come il genere le vuole (settime
  e none minori nella dub techno, settime nella house, maj7 e min9 nell'amapiano, add9 nella trance, quinte vuote nella
  hard techno). La pagina dell'hub, sezione **PROGRESSIONI SUL PI**, le mostra per genere e per mood, ne cancella una e
  ne aggiunge una scritta a mano: `i bVI bVII i`, `ii7:8 V7:8 Imaj7^1` (`:8` la durata in sedicesimi, `^1` il push).

## Corretto

* Su alcune build (-O2) uno slot DENSITY leggeva un valore che VIAGGIO non aveva scritto: uno step con una condizione
  (1:2, FILL) poteva suonare lo stesso, a velocità 1. Trovato con valgrind, ora ha un test.

* Trovati dall'esploratore (sotto): una traccia restava fuori fase con la battuta, mentre suona, dopo
  * un cambio di direzione (FWD, REV: c'era già nella 0.10);
  * essere passata da TAPE e tornata;
  * un UNDO che rimetteva l'inizio o la lunghezza del loop;
  * un dado rimesso com'era (SEQ 7) dopo una lunghezza cambiata in battuta, o sopra una traccia passata in TAPE;
  * un loop di VIAGGIO lasciato a mano (la traccia tornava alle sue impostazioni senza tornare a tempo);
  * STOP dentro un DJ LOOP e poi CONTINUE;
  * una cosa cambiata da fermo (la direzione, un dado rimesso) e poi CONTINUE (SEL + PLAY): ora CONTINUE riparte dove
    il clock dice, anche da slave (0xFB);
  * un RELOAD (SEL + SAVE) di una traccia a cui VIAGGIO aveva cambiato il loop; e, per lo stesso motivo, la fine di
    TEMP.

  Ora in tutti questi casi la traccia torna dove la battuta dice (una funzione sola, `track_cfg_back`, per ogni volta
  che le impostazioni di una traccia vengono rimesse); ognuno ha un test (`t011_in_time_after`,
  `t011_explorer_sessions`, che rifà le sessioni dell'esploratore che li hanno trovati).

## L'esploratore

`tests/sagga_explore.py` prova il firmware come lo proveresti tu, ma tutto: in 11 situazioni (vuoto, band in play,
armonia su LOCK, progressione USER, GENRE LIVE, VIAGGIO, PERF, loop, grid ...) fa ognuno dei suoi oltre 4000 gesti
(ogni bottone, ogni manopola su ogni pagina con e senza SEL, ogni tasto con ogni modificatore, i pad del grid in ogni
vista), poi coppie di gesti e sessioni lunghe a caso, e dice cosa cambia e quali regole si rompono: sfogliare che
cambia l'armonia, un canale cambiato da chi non deve, una traccia fuori fase, note appese, il clock che salta. Gira
nel simulatore, in circa tre minuti e mezzo (un minuto con `--veloce`, che è nella suite dei test). Sulla 0.10 trova in
19 secondi il problema dell'armonia che cambiava sfogliando i generi. Come si usa e come si legge:
`docs/SAGGA-ESPLORATORE.md`.

**Anche sull'FM-1 vero.** La 0.11 ha il test dal PC (`firmware/src/sagga_test.c`): con il tuo sì sull'FM-1 (SEL) il PC
preme i tasti, gira le manopole e suona la tastiera ai tempi delle sessioni dell'esploratore, e l'FM-1 manda dopo ogni
gesto tutto il suo stato e dove ha preso ogni evento (il suo millisecondo, il suo tick di clock). In WSL ogni sessione
viene rifatta nel simulatore con ogni evento esattamente lì: quello che differisce è l'hardware (il compilatore, i
tempi), e il rapporto lo dice sonda per sonda; in più le regole sui dati dell'FM-1 (FASE, note appese, note o tick persi
sull'USB, il firmware che si pianta, il ciclo che si ferma). Ogni sessione parte da un riavvio nel test: niente progetto,
nessuno slot letto o scritto (il blocco è dove la flash si scrive), il progetto in memoria salvato sul PC e rimesso alla
fine; una mano su un tasto ferma tutto. Come si fa: `tools/hwtest/LEGGIMI.md`, punto 6 del foglio d'installazione.

## Compatibilità

* `SGQB` è `SGQA` con le tracce da 96 byte (i quattro slot, il modo di FOLLOW), cinque progressioni utente da 52 byte
  (fondamentale, forma, durata, push, mood) e i generatori da 32 (genere e LOCK dell'armonia, RHYTHM, MOOD). Il bridge,
  l'hub, il convertitore `.mid` e il test hardware leggono tutti e due.
* SysEx nuovi 60-65 (le variazioni del Pi), 66-6B (le progressioni) e 70-73 (il test dal PC): in `docs/SAGGA-SEQ.md`.

## I test

core 888.724 controlli, simulatore 768 (tra cui: le lunghezze in battuta, l'armonia che non segue lo sfoglio, i quattro
slot, la band con i ruoli e i canali tenuti, il cammino di COOK, le note tenute, il gesto dei due step, le variazioni e
le progressioni del Pi in tutte e due le direzioni, PUSH, 3+3+2, RETRIG e LEGATO, il filtro dei mood, DICE PROG), bridge
271, hub 80, fuzz 24, l'esploratore (22.656 gesti da soli, 4.397 coppie, 200 sessioni; e, mentre si correggeva, più di
20.000 sessioni a caso con altri semi), il test dal PC (il simulatore al posto dell'FM-1, con lo schermo che costa: ogni
sessione rifatta uguale; il programma di Windows contro un FM-1 finto che perde pezzi per strada, 15), tutti a 0. Il
simulatore gira anche sotto AddressSanitizer, UBSan e valgrind.

Le formazioni dei generi sono state riviste anche su fonti di produzione: Attack Magazine ("Dark techno rumble",
"Deep afro house") e beatstorapon ("How to make an amapiano beat").
