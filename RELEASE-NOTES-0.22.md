# SAGGA SEQ 0.22 - Note di rilascio

**Lo scavo fino alla prima versione.** Questa volta ho guardato dove i test non arrivavano (l'USB vero, l'attesa dello
schermo, i contatori che fanno il giro, le righe del firmware che nessun test eseguiva), gli strumenti che provano
tutto il resto, e come FM-1, Pi e grid spendono il loro tempo. Nessuna funzione nuova, lo stesso formato dei progetti
(`SGQB`). Si installa al posto della 0.21.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.22.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid | `sagga-hub-0.22.zip` |
| come si installa e si aggiorna | `INSTALLA.md` (invariato) |

## L'FM-1

### Le note aspettavano lo schermo

Un pezzo di schermo (una riga: 5 ms di pixel; una cella grande: 8) parte da solo verso il pannello, ma il pezzo dopo
lo aspettava, e con lui tutto il giro principale: il clock e le note che cadevano in quel tempo partivano in ritardo.
Succede ogni volta che lo schermo cambia mentre suoni, cioè ogni volta che giri una manopola.

Misurato nel simulatore, con il costo vero del pannello: una band in play e quattro manopole girate, **79 note su 130
partivano da 1 a 8 ms in ritardo**; girando il tempo a 300 BPM i tick del clock, che dovrebbero stare a 8,3 ms l'uno
dall'altro, stavano fra 3 e 14. Adesso il giro comincia un pezzo di schermo solo quando il pannello ha finito quello
prima: **da 0 a 2 ms**, tick fra 7 e 10. Lo schermo si aggiorna alla stessa velocità di prima.

### Una raffica di messaggi poteva perdersi

L'uscita USB aveva una coda di 64 messaggi. Quello che un giro mandava oltre il posto libero veniva buttato, e l'FM-1
lo contava soltanto (`DROPPED` sulla pagina USB). Un dado sui CC manda sei lane per sedici tracce in un colpo; nella
prova a caso tre tasti insieme hanno fatto 68 Control Change in un giro, e quattro sono spariti: quattro synth con il
suono sbagliato. Con le note va peggio: una nota spenta che si perde resta appesa.

Nessun test poteva vederlo: **il simulatore non aveva la coda** (mandava sempre tutto). Adesso ce l'ha, uguale a
quella dell'FM-1, e la prova a caso gira con quella. La coda è di 256; le luci del grid, le lane, gli LFO e i valori
per il tablet continuano a vedere solo i primi 64 posti, così la musica non fa mai la fila dietro di loro.

### Il grid mostra una vista in un decimo di secondo

Le luci partivano 8 ogni 20 ms: una vista nuova, con una band (84-130 luci), ci metteva da 230 a 350 ms a comparire.
Adesso 24 ogni 20 ms: **da 90 a 110 ms**. Il posto che le luci lasciano alle note è lo stesso di prima.

### L'effetto GATE non allungava le note

Fra i MIDI FX, GATE offre una durata FISSA da 1/32 a 2 battute e un fattore da x1/4 a x4. Qualunque cosa chiedessi,
**una nota non passava mai il suo step**: lo step dopo della traccia la chiudeva. FISSA 1/4 dava un sedicesimo, x2
pure. Era così dalla 0.20, e l'unico test che c'era provava FISSA 1/32.

Adesso una nota che GATE allunga oltre lo step dura quello che dice: FISSA 1/8 due step, 1/4 quattro; x2 e x4 di una
nota all'80 % 1,6 e 3,2 step. Si sovrappone alle note che vengono dopo (su un synth mono: legato), e se la stessa nota
torna prima che finisca, quella vecchia si chiude in quel momento. UMANA da sola resta com'era: non porta mai una nota
oltre il suo step.

### Un TIE verso la stessa nota lasciava 15 millisecondi

Una nota legata (TIE) tiene 15 ms dentro lo step dopo, per far scivolare un synth mono. Se lo step dopo aveva **la
stessa nota**, la fine di quella legata arrivava 15 ms dopo l'attacco della nuova e la spegneva: della seconda nota
restava un clic. Era così dalla 0.10. Adesso la nota legata si chiude nel momento in cui comincia la nuova, che dura
il suo gate.

### Altro

* L'interrupt dell'audio azzerava, scalava con MASTER e spostava un buffer di silenzio ogni 5,8 ms (SAGGA SEQ non
  suona): adesso lo conferma e basta.
* Due funzioni che nessuno chiamava, tolte.

## Il Pi

* **Il Pi chiedeva all'FM-1 chi era ogni 5 secondi**, per tutto il tempo che la pagina del Pi restava aperta: ogni
  volta partiva un Python, nasceva un client ALSA (e RaspiMIDIHub riesamina tutti i dispositivi a ogni client che
  compare) e arrivava un SysEx all'FM-1. Dodici volte al minuto, anche in mezzo a un set. Adesso lo chiede quando i
  client ALSA cambiano (l'FM-1 arriva, se ne va, si riavvia).
* **Il bridge del grid** mandava a ogni Launchpad un messaggio per ogni luce (13 byte l'una); adesso prende tutte
  quelle che arrivano insieme e ne fa uno solo. Quando non succede niente si sveglia 50 volte al secondo invece di 200.

## Gli strumenti di prova

* **L'esploratore esplorava un progetto vuoto.** La sua "band" era il gesto della 0.11 (SEQ + SEL + nero 7), che dalla
  0.12 fa un'altra cosa: **quattordici situazioni su diciassette**, nel simulatore e nei piani per l'FM-1 e per il
  banco, non avevano nessuna band. E nel simulatore il suo grid se ne andava dopo 3,5 secondi, perché nessuno gli
  mandava il segnale di vita. Anche le prove che hai fatto tu sull'FM-1 e sul banco hanno girato senza band: quello
  che hanno trovato è giusto, ma hanno suonato molto meno di quello che credevamo.
  Con le band vere e il grid che resta: 55.829 gesti in 17 situazioni, 6.799 coppie, 200 sessioni, **nessun errore**.
  Una situazione "con la band" che non ce l'ha adesso è un errore lei stessa.
* **Nessun test passava i 66 secondi.** I contatori dell'FM-1 fanno il giro ogni 179 secondi e, i microsecondi, a 71,6
  minuti (in passato lì il clock si era già fermato una volta). Sei situazioni lasciate in play per 76 minuti, due
  per 150: il clock mai in ritardo, la band uguale dal primo all'ultimo minuto, niente appeso. Una è un test fisso.
* **Cosa i test non eseguivano mai.** Ho misurato riga per riga (gcov) quanto firmware fanno girare tutti i test
  insieme: il 97 % (di 13.223 righe, 347 non le esegue nessuno). Quello che resta fuori l'ho letto e, dove si poteva
  suonare, provato a mano: la vista del grid di una traccia TAPE, sei destinazioni e tre sorgenti della MOD MATRIX, i
  ritmi dell'armonia 3+5, 3+1 e 2 BARS, le condizioni 1:4, 4:4 e NOT FILL, le durate di GATE. Fanno tutte quello che
  dice il manuale tranne GATE (sopra). Adesso hanno un test fisso (30 controlli), e l'esploratore tocca anche i 128
  pad della vista VIAGGIO del grid.

## Cosa ho guardato e lasciato com'è

* **Il salvataggio dei progetti** (nove aree per otto slot, l'intestazione scritta per ultima, la cancellazione in
  sottofondo solo da fermo): è fatto bene, uno spegnimento a metà non rovina niente e la memoria non si consuma.
* **Il tempo di calcolo dell'FM-1** non è un limite: tutto il giro principale è leggero. I ritardi venivano dalle
  attese (lo schermo, la coda), non dai conti.
* **I SysEx in arrivo** hanno un posto solo: un secondo SysEx che arriva mentre il primo aspetta il giro principale
  viene scartato. Chi li manda (il bridge, il banco, l'aggiornamento) aspetta la risposta o riprova, e toccare quella
  parte vuol dire toccare l'aggiornamento del firmware senza poterlo provare su un FM-1: l'ho lasciata.
* **Il bridge e la pagina del Pi si parlano con dei file** in `/run/sagga`, guardati 50 volte al secondo. Costa poco
  (misurato: quasi tutto il tempo va nel risveglio, non nei file) e funziona; rifarlo con un socket sarebbe più
  pulito ma non cambia niente che si senta.

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.22.zip`. In alto deve dire `SAGGA HUB 0.22`.
2. **L'FM-1**: fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.22.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.22`.

## Da sapere

* **Niente di questo ha ancora girato su un FM-1 vero.** Tre correzioni dell'FM-1 toccano l'hardware: la coda USB
  (più lunga), lo schermo (il giro guarda se il pannello ha finito, con lo stesso segnale che prima aspettava) e
  l'interrupt dell'audio. Sono piccole e le ho lette contro il codice della piattaforma, ma i numeri qui sopra sono
  del simulatore. Se dopo l'aggiornamento lo schermo si comporta in modo strano o l'FM-1 non parte, torna alla 0.21
  (stessa pagina, FIRMWARE) e dimmelo; se non parte proprio, OCT- tenuto all'accensione apre il soccorso USB.
  GATE e TIE invece sono conti del sequencer: lì il simulatore e l'FM-1 fanno la stessa cosa.
* **Se un progetto usa GATE** (HOME 6, i MIDI FX) con FISSA da 1/8 in su o con un fattore sopra x1, adesso suona
  diverso: le note durano quello che c'è scritto e si sovrappongono. Se ti eri abituato a com'era, FISSA 1/16 è la
  nota lunga uno step.
* **Rifai le due prove** (l'FM-1 completo e il banco) quando hai tempo: sono le prime con le band vere. I piani nuovi
  sono nello zip del Pi.
* L'FM-1 sordo dopo un riavvio e RaspiMIDIHub che perde le celle: come nelle note della 0.21.
