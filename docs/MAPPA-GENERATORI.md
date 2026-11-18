# SAGGA SEQ 0.26 - La mappa dei generatori

Mi avevi scritto: *troppe strade per la stessa cosa*. RANDOM, i dadi, COOK, EVOLVE, DRIFT, EUCLID, i quattro algoritmi,
i motori e le mosse fanno cose che si sovrappongono.

Questa è la mappa. **Non ho unito né nascosto niente**: qui c'è cosa fa ogni strada, dove due strade fanno la stessa
cosa, e cosa ti propongo. Scegli tu. Qualunque cosa scegli, i progetti salvati e i gesti che usi restano.

I numeri di oggi: 43 pagine di manopole (HOME 8, SEQ 8, ENV 6, LFO 6, ARP 6, SAVE 5, GLO 4) e circa 3.000 gesti
diversi sul pannello.

## In una riga

Tutti i generatori rispondono a una di **tre domande**:

| la domanda | chi risponde |
| --- | --- |
| **1. Fammi un pattern** (da zero) | BEAT, KIT, BAND, i DADI, RANDOM, i motori THEORY |
| **2. Cambia il pattern che c'è** (lo riscrive) | COOK, EVOLVE, DRIFT, RANDOM, la VARIAZIONE dei motori |
| **3. Muovilo mentre suona** (non lo riscrive) | EUCLID LIVE, i quattro algoritmi, i MIDI FX, l'ENERGIA, le MOSSE |

La confusione nasce perché ogni domanda ha più risposte, messe in posti diversi.

## Chi fa cosa

| il generatore | dove sta | cosa fa | riscrive il pattern? | si torna indietro? |
| --- | --- | --- | --- | --- |
| **BEAT** | SEQ + bianco 10 | una parte del genere sulla traccia: dalla libreria, o fatta dai motori | sì | UNDO |
| **KIT**, **BAND** | SEQ + nero 7 (tenuto: BAND) | la batteria, o tutta la band, in un colpo | sì | UNDO |
| **PROPOSTA** | SEQ + BEAT tenuto | una parte in un pattern libero, da ascoltare prima di tenerla | sì, in un pattern vuoto | la scarti |
| **DADI** (SEQ, CC, LFO, GROOVE, ALL, PROG) | SEQ + neri 1-5 | tirano un pattern nuovo sulle tracce dello SCOPE; ricordano 16 tiri | sì | OCT- o UNDO; ALG rivede i tiri |
| **RANDOM** | SEQ + bianco 5 | una battuta a caso e la sua frase (A A' A B), secondo il ruolo e la tonalità | sì | UNDO |
| **COOK** | SEQ + bianco 9 | un tocco: qualche passo verso la variazione dopo. Tenuto: cucina a caso, battuta per battuta | sì, pochi passi alla volta | UNDO |
| **EVOLVE** | SEQ + nero 9, pagina SEQ 3 | COOK da solo, ogni 1-16 battute, attorno al pattern di partenza | sì | REVERT (nero 11), FREEZE lo ferma |
| **DRIFT** | SEQ + nero 8 | come EVOLVE, ma si allontana senza tornare | sì | REVERT |
| **VARIAZIONE** dei motori | SEQ 8 K4 | salta subito alla variazione N dello stesso seme | sì | UNDO, o rigiri K4 |
| **SEME** dei motori | SEQ 8 K3 | un'altra parte, da un altro seme | sì | UNDO, o rigiri K3 |
| **EUCLID LIVE** (EUCLID, TRESILLO, NUMERIC) | pagina SEQ 1, parte con SEQ + bianco 6 | un ritmo sopra il pattern: colpi distribuiti, o uno dei sedici ritmi | no (WRITE LIVE lo scrive) | lo spegni |
| **TURING** | pagina SEQ 2 | un giro di colpi che muta piano; può muovere il ritmo, le note o tutti e due | no (WRITE LIVE) | lo spegni |
| **CELL** | pagina SEQ 2 | un ritmo che cambia a ogni generazione, con una regola | no (WRITE LIVE) | lo spegni |
| **ACCENT** | pagina SEQ 2 | accenti sopra il pattern: sul tempo, sul levare, 3+3+2, a caso | no | lo spegni |
| **DENSITY** | pagina SEQ 2 | toglie o lascia colpi: più pieno, più vuoto | no | lo spegni |
| **MIDI FX** (CHANCE, RANDOM NOTE, GLITCH...) | pagina HOME 6 | cambiano le note mentre escono | no | li spegni |
| **ENERGIA** | GLO 3 K1, le mosse | riempie e svuota i pattern fatti dai motori | sì, solo i passi che cambiano | riabbassi l'energia |
| **MOSSE** (FILL, BREAK, RISER, DROP, THIN, SWELL...) | PERF pagina 3 | muovono tutto il set a fine frase | alcune sì | INDIETRO |

## Dove due strade fanno la stessa cosa

| | le strade | sono davvero uguali? |
| --- | --- | --- |
| **A** | **RANDOM** e **DADO SEQ** con il genere su FREE | **Sì.** Il dado, senza genere, fa "una battuta a caso e la sua frase": è RANDOM. Cambia solo che il dado ricorda i tiri |
| **B** | **COOK tenuto** e **EVOLVE** | **Quasi.** EVOLVE è COOK a caso fatto da solo ogni N battute. Stesse regole |
| **C** | **EVOLVE** e **DRIFT** | **Quasi.** Stessa cosa, con o senza il ritorno al punto di partenza |
| **D** | **COOK** (un tocco) e **VARIAZIONE** (SEQ 8 K4) | **Stessa meta, passo diverso.** COOK ci cammina, K4 ci salta |
| **E** | **BEAT** con i motori, **SEME** (SEQ 8 K3), **DADO SEQ** con i motori | **Quasi.** Tutti e tre danno "un'altra parte da un altro seme". BEAT prende il seme dopo, K3 lo scegli tu, il dado lo tira |
| **F** | **DENSITY**, **ENERGIA**, **THIN / SWELL**, **CHANCE** | **Stesso effetto, quattro mani.** Tutti fanno "più pieno / più vuoto": su una traccia (DENSITY, CHANCE), sui pattern dei motori (ENERGIA), su tutto il set (THIN, SWELL) |
| **G** | **TURING sulle note**, **RANDOM NOTE**, **COOK** sulle note | **Simili.** Tutti muovono le note dentro la tonalità; TURING con memoria, RANDOM NOTE senza, COOK riscrivendo |
| **H** | **EUCLID** come strumento e **EUCLID LIVE** | **Stessa idea, due momenti.** Uno scrive subito, l'altro suona sopra finché non lo scrivi |
| **I** | **FILL** (mossa), la **chiusura** dei motori, **LONG PATTERNS su PHRASE** | **Simili.** Tre modi di chiudere una frase |

## Cosa ti propongo

Sono proposte. Nessuna è fatta. Per ognuna: cosa cambierebbe, e cosa resta.

### 1. Un profilo in più, che nasconde (la più utile)

Oggi SAVE + K4 sceglie fra FULL e PALCO. Aggiungerei un profilo in mezzo, per esempio **SEMPLICE**:

* mostra le strade principali: BEAT, BAND, i DADI, COOK, l'ENERGIA, le MOSSE;
* nasconde le pagine dei generatori "da laboratorio": SEQ 2 (i quattro algoritmi) e SEQ 3 (EVOLVE);
* **non spegne niente**: un generatore che sta suonando continua, e la sua pagina resta visibile finché è acceso;
* in FULL ritrovi tutto, com'è oggi.

Cosa resta: tutto. I progetti non cambiano, i gesti nemmeno. È solo quello che vedi.

### 2. RANDOM diventa un tiro di dado (unisce A)

RANDOM e il dado senza genere fanno la stessa cosa. Farei di RANDOM **un tiro**: stesso gesto (SEQ + bianco 5), ma
entra nella memoria dei dadi, così con ALG rivedi i tiri e con OCT- torni indietro.

Cosa resta: il gesto, e quello che fa. Guadagni la memoria dei tiri.

### 3. DRIFT dentro EVOLVE (unisce C)

Invece di due tasti, EVOLVE con una manopola in più: **RITORNO**. Al massimo è l'EVOLVE di oggi, a zero è DRIFT.

Cosa resta: il tasto DRIFT può restare come scorciatoia ("EVOLVE con ritorno a zero"). Un progetto con DRIFT acceso
suona uguale.

### 4. Una pagina sola per "più pieno, più vuoto" (chiarisce F)

Qui non unirei: le quattro mani lavorano su cose diverse. Farei dire allo schermo **chi sta agendo**: quando giri
l'ENERGIA, DENSITY o tocchi THIN, una riga dice su cosa lavora (questa traccia, i pattern dei motori, tutto il set).

### 5. Cose che lascerei come sono

* **COOK e VARIAZIONE** (D): camminare e saltare sono due gesti musicali diversi.
* **BEAT, SEME, DADO** (E): sono lo stesso motore con tre maniglie, ma ognuna serve in un momento diverso.
* **EUCLID e EUCLID LIVE** (H): scrivere subito e provare prima sono due modi di lavorare.
* **TURING, RANDOM NOTE, COOK** (G): suonano diversi.

## Voglio... uso...

Questa tabella vale già oggi, senza cambiare niente.

| voglio | uso | perché questa |
| --- | --- | --- |
| partire da zero con una band | **BAND** (SEQ + nero 7 tenuto) | una band intera nel genere, in un gesto |
| una parte nuova su una traccia | **BEAT** (SEQ + bianco 10) | la parte giusta per il ruolo della traccia |
| un'altra idea, subito | **DADO SEQ** (SEQ + nero 1) | tiri, ascolti, e torni indietro se non ti piace |
| la stessa parte, un po' diversa | **COOK** (SEQ + bianco 9), più tocchi | cambia pochi passi alla volta: ti fermi quando va bene |
| che cambi da sola nel tempo | **EVOLVE** (SEQ + nero 9) | cucina ogni N battute e resta vicina all'originale |
| un ritmo "matematico" sopra il mio | **EUCLID LIVE** (SEQ 1, poi SEQ + bianco 6) | non tocca il pattern finché non lo scrivi |
| più pieno o più vuoto, dal vivo | **ENERGIA** (GLO 3 K1) con i motori; altrimenti **THIN / SWELL** | lavorano su tutto il set, a tempo |
| una chiusura a fine frase | **FILL** (le MOSSE) | arriva a fine frase da sola |
| tornare a com'era | **UNDO** (SEQ + bianco 8), o **REVERT** dopo EVOLVE | |

## Cosa mi serve da te

Dimmi quali proposte vuoi (1, 2, 3, 4), anche solo una. Le faccio nella prossima versione, una alla volta, ognuna con
le sue prove. Se nessuna ti convince, la tabella "Voglio... uso..." entra nel manuale e ci fermiamo lì.
