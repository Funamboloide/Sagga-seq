# SAGGA SEQ 0.32.4 - Note di rilascio (solo FIGO e SCENA)

Questa versione cambia solo i due effetti del live: **FIGO** su norns e **SCENA** sulla Gills. Meno latenza dove si può
togliere, e niente più effetto phaser quando stanno su un bus del mixer.

**L'FM-1 e il Pi non cambiano.** L'FM-1 resta alla 0.32.1, il Pi alla 0.32.3: lì non c'è niente da aggiornare.

| il pezzo | il file |
| --- | --- |
| norns | `tools/norns/figo/figo.lua` (FIGO 0.2) |
| la Gills, su un bus | `tools/gills/scena_aux.axp` |
| la Gills, in insert | `tools/gills/scena.axp` |
| l'FM-1 e il Pi | niente da fare |

## Da dove veniva la latenza

* **FIGO** leggeva il nastro 8 ms dietro la testina che registra. Con i circa 11 ms di norns (convertitori e JACK, che
  nessuno script può togliere), il pulito usciva circa 19 ms dopo.
* **SCENA** non aggiunge niente: al centro esce lo stesso campione che entra. Restano solo i circa 1-2 ms della scheda.
* **Su un bus** il pulito che esce anche dal ritorno si somma all'originale sul mixer qualche millisecondo dopo. È quello
  che si sente come phaser, o come flam sui colpi.

## FIGO 0.2

* **Il pulito legge mezzo millisecondo dietro la testina** invece di 8. In ogni blocco softcut registra prima di leggere,
  e scrive 8 campioni dietro la testina: per leggere solo quello che è già scritto bastano 10 campioni (0,2 ms). L'ho
  visto nel codice di softcut, quello che norns compila. In insert il pulito esce così circa 11 ms dopo invece di 19.
* **PARAMETERS > routing**: **insert** (come prima) o **aux (mandata)** per un bus. In aux il pulito non esce mai:
  sul ritorno ci sono solo gli interventi e la memoria, e quando non succede niente il ritorno è muto. GATE in aux non
  c'è, perché non avrebbe un pulito da tagliare.
* **In aux gli interventi arrivano in tempo.** FIGO fa partire quello che suona prima di quanto il suono impiega ad
  andare a norns e tornare. È l'**anticipo**, 11 ms (PARAMETERS > anticipo). Può farlo perché quello che ripete è già sul
  nastro. Le ripetizioni, i roll, INDIETRO, la memoria e l'eco cadono così sulla griglia del pulito al mixer. Le
  ripetizioni si sentono dalla prima ripetizione, perché il primo pezzo è il pulito, già sul mixer.
* **Si sente come prima, solo meno in ritardo.** Gli interventi partono 7,5 ms prima del battito, quindi vedono il nastro
  8 ms dietro la testina, come nella 0.1. E un salto ha finito la sua dissolvenza prima dell'attacco del colpo.
* **Tre errori della 0.1 corretti**, trovati dalle nuove prove:
  * il **ROLL** con glitch alto superava la testina che registra per circa 0,3 secondi a roll, e suonava il nastro di 5
    minuti prima (o silenzio nei primi 5 minuti). La rampa di velocità di softcut sale subito, non piano come pensava il
    vecchio modello. Adesso l'intonazione sale dalla seconda metà del roll, quando legge solo quello che è registrato;
  * la **MEMORIA** a doppia velocità, partita da una sola battuta fa e lunga 8 battiti, faceva lo stesso. Adesso va a
    doppia solo se resta dietro;
  * uno **START** di SAGGA durante un intervento lo teneva aperto finché norns non tornava a contare fin lì (norns
    rimette il conto dei battiti a zero). Con uno START al battito 80 erano 42 secondi senza altri interventi, e in
    insert l'ultimo pezzo restava in loop. Adesso FIGO conta i battiti per conto suo e non torna mai indietro.
* **L'eco della memoria** parte da softcut stesso, al campione, h dopo il pulito. Prima partiva da quando il clock
  svegliava lo script, fino a qualche millisecondo dopo.
* **Le impostazioni**: la latenza ha un nome nuovo, *latenza (dietro la testina)*, 0,5 ms. Gli 8 ms salvati dalla 0.1 non
  tornano. Sono nuovi *routing* (insert) e *anticipo (aux)* (11 ms).

**Tarare l'anticipo** (una volta, poi resta salvato):

1. Metti routing = insert e FIGO a 0.
2. Registra dalla USB del 12MTK il canale di un suono secco (la cassa) e il ritorno di norns.
3. In Ableton misura di quanti ms il colpo del ritorno arriva dopo: quello è l'anticipo.
4. Rimetti routing = aux.

A orecchio: in aux, con una cassa dritta sul bus, FIGO 100 e carattere 0, muovi l'anticipo finché i colpi ripetuti non si
fondono con quelli del mixer.

## SCENA

* **`scena_aux.axp`, per il bus**: il pulito non esce mai. Escono:
  * il fruscio;
  * l'eco e il riverbero;
  * i loop di ROLL, FREEZE e dei fill, dalla loro prima ripetizione (FREEZE subito).

  Filtro e crush lavorano su quello che va nell'eco e nel riverbero, e sui loop: il pulito sul mixer resta com'è. Al
  centro il ritorno è muto, e lo schermo scrive MANDATA al posto di PULITO.
* **`scena.axp`, in insert**: non cambia niente. Il loop di prova di 16 battute esce identico a prima, campione per
  campione.
* Le due patch sono la stessa. Cambia l'attributo **routing** dell'oggetto `scena`, che si può cambiare anche nel
  Patcher.

## Installare

* **norns**: copia il nuovo `figo.lua` come la prima volta (`tools/norns/figo/README.md`). Poi PARAMETERS > routing = aux
  (mandata), e tara l'anticipo.
* **Gills**: apri `scena_aux.axp` nel Ksoloti Patcher, **Live**, guarda il carico DSP, poi **Upload to internal flash**
  (`tools/gills/LEGGIMI.md`).

Nel piano per il live il firmware si blocca domenica 13 dicembre: questi due file arrivano prima, c'è tempo per provarli
sul rig.

## Come è stato provato

* **FIGO**: `texlua tools/norns/test_figo.lua`, 129 controlli, con un modello di softcut rifatto dal suo codice:
  * le voci fatte in ordine a ogni blocco, la testina che scrive 8 campioni dietro e la lettura che ne guarda 2 avanti;
  * la dissolvenza di ogni salto e di ogni giro del loop, con la testina vecchia che continua mentre sfuma. Un salto
    chiesto intanto aspetta, e un punto del loop lo cancella;
  * le rampe a un polo.

  Niente di quello che si sente suona nastro non registrato, in insert e in aux, da 90 a 174 BPM, con il messaggio della
  posizione di norns in ritardo da 0 a 9 ms. In aux, con un giro di 11 ms, le ripetizioni cadono a pezzi interi dopo il
  pulito al mixer entro 0,6 ms. Uno START nel mezzo di un intervento non lo blocca più. Ho rotto apposta 26 pezzi del
  nuovo codice, uno alla volta: le prove se ne accorgono ogni volta.
* **SCENA**: `tools/gills/test_scena.cpp`, 58 controlli, 21 nuovi per aux. Le due patch compilano per il Cortex-M4 contro
  gli header del firmware Ksoloti: circa 15 kB di codice su 44.
* **Niente è stato provato su un norns o su una Gills veri.** La prima volta ascolta i livelli, guarda il carico DSP
  della Gills, e su norns tara l'anticipo.
