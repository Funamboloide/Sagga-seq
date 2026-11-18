# SAGGA SEQ 0.27 - La mappa dei generatori

Mi avevi scritto: *troppe strade per la stessa cosa*. RANDOM, i dadi, COOK, EVOLVE, DRIFT, EUCLID, i quattro algoritmi,
i motori e le mosse fanno cose che si sovrappongono.

Questa è la mappa: cosa fa ogni strada, dove due strade fanno la stessa cosa, e cosa è cambiato. Nella 0.26 ti avevo
fatto quattro proposte; le hai volute tutte e quattro e sono nella 0.27 (sotto, [Cosa è cambiato in 0.27](#cosa-è-cambiato-in-027)).
Non è stato tolto niente: i progetti salvati e i gesti che usi restano.

I numeri: 43 pagine di manopole (HOME 8, SEQ 8, ENV 6, LFO 6, ARP 6, SAVE 5, GLO 4) e circa 3.000 gesti diversi sul
pannello. Nel profilo SEMPLICE le pagine sono 41: SEQ 2 e SEQ 3 restano nascoste finché non suonano.

## In una riga

Tutti i generatori rispondono a una di **tre domande**:

| la domanda | chi risponde |
| --- | --- |
| **1. Fammi un pattern** (da zero) | BEAT, KIT, BAND, i DADI (RANDOM compreso), i motori THEORY |
| **2. Cambia il pattern che c'è** (lo riscrive) | COOK, EVOLVE (DRIFT è EVOLVE senza ritorno), la VARIAZIONE dei motori |
| **3. Muovilo mentre suona** (non lo riscrive) | EUCLID LIVE, i quattro algoritmi, i MIDI FX, l'ENERGIA, le MOSSE |

La confusione nasceva perché ogni domanda ha più risposte, messe in posti diversi. Dalla 0.27 due coppie sono unite
(RANDOM con i dadi, DRIFT con EVOLVE) e lo schermo dice su cosa lavora chi rende la musica più piena o più vuota.

## Chi fa cosa

| il generatore | dove sta | cosa fa | riscrive il pattern? | si torna indietro? |
| --- | --- | --- | --- | --- |
| **BEAT** | SEQ + bianco 10 | una parte del genere sulla traccia: dalla libreria, o fatta dai motori | sì | UNDO |
| **KIT**, **BAND** | SEQ + nero 7 (tenuto: BAND) | la batteria, o tutta la band, in un colpo | sì | UNDO |
| **PROPOSTA** | SEQ + BEAT tenuto | una parte in un pattern libero, da ascoltare prima di tenerla | sì, in un pattern vuoto | la scarti |
| **DADI** (SEQ, CC, LFO, GROOVE, ALL, PROG) | SEQ + neri 1-5 | tirano un pattern nuovo sulle tracce dello SCOPE; ricordano 16 tiri | sì | OCT- o UNDO; ALG rivede i tiri |
| **RANDOM** | SEQ + bianco 5 | una battuta a caso e la sua frase (A A' A B), secondo il ruolo e la tonalità, sulle tracce dello SCOPE. **Dalla 0.27 è un tiro di dado** | sì | OCT- o UNDO; ALG rivede i tiri |
| **COOK** | SEQ + bianco 9 | un tocco: qualche passo verso la variazione dopo. Tenuto: cucina a caso, battuta per battuta | sì, pochi passi alla volta | UNDO |
| **EVOLVE** | SEQ + nero 9, pagina SEQ 3 | COOK da solo, ogni 1-16 battute. **RETURN** (SEQ 3, SEL + K2) dice quanto torna al pattern di partenza: 100 resta vicino, 0 si allontana | sì | REVERT (nero 11), FREEZE lo ferma |
| **DRIFT** | SEQ + nero 8 | **dalla 0.27 è una scorciatoia**: EVOLVE con RETURN a 0; premuto di nuovo, il RETURN di prima | sì | REVERT |
| **VARIAZIONE** dei motori | SEQ 8 K4 | salta subito alla variazione N dello stesso seme | sì | UNDO, o rigiri K4 |
| **SEME** dei motori | SEQ 8 K3 | un'altra parte, da un altro seme | sì | UNDO, o rigiri K3 |
| **EUCLID LIVE** (EUCLID, TRESILLO, NUMERIC) | pagina SEQ 1, parte con SEQ + bianco 6 | un ritmo sopra il pattern: colpi distribuiti, o uno dei sedici ritmi | no (WRITE LIVE lo scrive) | lo spegni |
| **TURING** | pagina SEQ 2 | un giro di colpi che muta piano; può muovere il ritmo, le note o tutti e due | no (WRITE LIVE) | lo spegni |
| **CELL** | pagina SEQ 2 | un ritmo che cambia a ogni generazione, con una regola | no (WRITE LIVE) | lo spegni |
| **ACCENT** | pagina SEQ 2 | accenti sopra il pattern: sul tempo, sul levare, 3+3+2, a caso | no | lo spegni |
| **DENSITY** | pagina SEQ 2 | toglie o lascia colpi: più pieno, più vuoto. Lo schermo: `THIS TRACK ONLY` | no | lo spegni |
| **MIDI FX** (CHANCE, RANDOM NOTE, GLITCH...) | pagina HOME 6 | cambiano le note mentre escono. CHANCE, sullo schermo: `THIS TRACK ONLY` | no | li spegni |
| **ENERGIA** | GLO 3 K1, le mosse | muove tutto il set, e riempie e svuota i pattern fatti dai motori. Lo schermo: `THE WHOLE SET + 4 ENGINE PARTS` | sì, solo i passi che cambiano | riabbassi l'energia |
| **MOSSE** (FILL, BREAK, RISER, DROP, THIN, SWELL...) | PERF pagina 3 | muovono tutto il set a fine frase. THIN e SWELL, sullo schermo: `THE WHOLE SET` | alcune sì | INDIETRO |

## Dove due strade fanno la stessa cosa

| | le strade | sono davvero uguali? |
| --- | --- | --- |
| **A** | **RANDOM** e **DADO SEQ** con il genere su FREE | **Sì.** Il dado, senza genere, fa "una battuta a caso e la sua frase": è RANDOM. **0.27: unite**, RANDOM ora è un tiro e ricorda i tiri come il dado |
| **B** | **COOK tenuto** e **EVOLVE** | **Quasi.** EVOLVE è COOK a caso fatto da solo ogni N battute. Stesse regole |
| **C** | **EVOLVE** e **DRIFT** | **Quasi.** Stessa cosa, con o senza il ritorno al punto di partenza. **0.27: unite**, DRIFT è EVOLVE con RETURN a 0 |
| **D** | **COOK** (un tocco) e **VARIAZIONE** (SEQ 8 K4) | **Stessa meta, passo diverso.** COOK ci cammina, K4 ci salta |
| **E** | **BEAT** con i motori, **SEME** (SEQ 8 K3), **DADO SEQ** con i motori | **Quasi.** Tutti e tre danno "un'altra parte da un altro seme". BEAT prende il seme dopo, K3 lo scegli tu, il dado lo tira |
| **F** | **DENSITY**, **ENERGIA**, **THIN / SWELL**, **CHANCE** | **Stesso effetto, quattro mani.** Tutti fanno "più pieno / più vuoto": su una traccia (DENSITY, CHANCE), sui pattern dei motori (ENERGIA), su tutto il set (THIN, SWELL). **0.27: lo schermo dice su cosa lavora ognuna** |
| **G** | **TURING sulle note**, **RANDOM NOTE**, **COOK** sulle note | **Simili.** Tutti muovono le note dentro la tonalità; TURING con memoria, RANDOM NOTE senza, COOK riscrivendo |
| **H** | **EUCLID** come strumento e **EUCLID LIVE** | **Stessa idea, due momenti.** Uno scrive subito, l'altro suona sopra finché non lo scrivi |
| **I** | **FILL** (mossa), la **chiusura** dei motori, **LONG PATTERNS su PHRASE** | **Simili.** Tre modi di chiudere una frase |

## Cosa è cambiato in 0.27

Le quattro proposte della 0.26, fatte. Per ognuna: cosa fa, e cosa resta.

### 1. Il profilo SEMPLICE

SAVE + K4 ora va **FULL, SEMPLICE, PALCO**. SEMPLICE è FULL, ma nasconde le pagine dei generatori "da laboratorio":
SEQ 2 (i quattro algoritmi) e SEQ 3 (EVOLVE). Con SEQ + OCT- / OCT+ le salti.

**Non spegne niente**: un algoritmo sulla traccia scelta fa tornare SEQ 2, EVOLVE acceso fa tornare SEQ 3. Lo schermo,
quando lo scegli: `PROFILE SEMPLICE: SEQ 2 AND 3 HIDDEN WHILE OFF`. In FULL ritrovi tutto, com'era.

Cosa resta: tutto. I progetti non cambiano, i gesti nemmeno. PALCO ora è a due scatti di K4 invece di uno.

### 2. RANDOM è un tiro di dado

Stesso gesto (SEQ + bianco 5), stessa musica, sulle tracce dello SCOPE. Ma ora aspetta come un dado:
`RANDOM: OCT+ KEEP, OCT- BACK`. Con OCT+ lo tieni, con OCT- (o UNDO) torni a com'era prima, con ALG rivedi i tiri
(fino a 16, insieme agli altri dadi). Premuto di nuovo, è un altro tiro.

Cosa resta: il gesto, e quello che fa. Se RANDOM lo ripete EVERY (SEQ 6), cambia subito, come prima.

### 3. DRIFT dentro EVOLVE: RETURN

Sulla pagina SEQ 3, **SEL + K2** è **RETURN** (il ritorno), da 0 a 100 %: prima di ogni cambio, quanta parte del
pattern di partenza torna.

* **100** (l'EVOLVE di prima): ogni cambio parte dal pattern di partenza, e gli resta vicino.
* **0**: ogni cambio parte dall'ultimo, e si allontana senza tornare. È DRIFT.
* **in mezzo**: torna quella parte dei passi (e degli LFO); il resto continua a girare. Un EVOLVE "al guinzaglio".

Lo schermo: `EVOLVE RETURN 40%: PART OF THE WAY BACK`. Il tasto DRIFT (SEQ + nero 8) resta come scorciatoia: porta
RETURN a 0 (`DRIFT: EVOLVE WANDERS AWAY`) e, premuto di nuovo, lo rimette com'era
(`NO DRIFT: EVOLVE STAYS NEAR THE SEED`).

Cosa resta: un progetto con DRIFT acceso si apre con RETURN a 0 e suona uguale.

### 4. Lo schermo dice chi sta agendo

Non ho unito le quattro mani del "più pieno, più vuoto": lavorano su cose diverse. Ora ognuna dice su cosa lavora.

| la mano | dove | lo schermo |
| --- | --- | --- |
| DENSITY | SEQ 2 | `T3 DENSITY 60%: THIS TRACK ONLY` |
| CHANCE | HOME 6 | `T3 CHANCE 40%: THIS TRACK ONLY` |
| ENERGIA | GLO 3 K1 | `ENERGY 70: THE WHOLE SET + 4 ENGINE PARTS` (tutto il set, e quante parti dei motori riempie e svuota) |
| THIN, SWELL | le MOSSE | `QUEUED: THIN - THE WHOLE SET, 2 TRACKS OUT`, `QUEUED: SWELL - THE WHOLE SET, 2 TRACKS IN` |

### E una correzione: l'arpeggio senza tonalità

In un progetto senza tonalità (scala CHROMA, com'è un progetto nuovo) l'arpeggio della BAND suonava una quinta sopra
le altre parti. Ora una parte scritta senza tonalità su una traccia nuova (BAND, BEAT dei motori, una proposta) parte
dalla fondamentale del progetto (Do, in un progetto nuovo), nel suo registro. Con una tonalità non cambia niente, e quello che è già
scritto resta com'è.

### Cose che restano come sono

* **COOK e VARIAZIONE** (D): camminare e saltare sono due gesti musicali diversi.
* **BEAT, SEME, DADO** (E): sono lo stesso motore con tre maniglie, ma ognuna serve in un momento diverso.
* **EUCLID e EUCLID LIVE** (H): scrivere subito e provare prima sono due modi di lavorare.
* **TURING, RANDOM NOTE, COOK** (G): suonano diversi.

## Voglio... uso...

| voglio | uso | perché questa |
| --- | --- | --- |
| partire da zero con una band | **BAND** (SEQ + nero 7 tenuto) | una band intera nel genere, in un gesto |
| una parte nuova su una traccia | **BEAT** (SEQ + bianco 10) | la parte giusta per il ruolo della traccia |
| un'altra idea, subito | **DADO SEQ** (SEQ + nero 1), o **RANDOM** (SEQ + bianco 5) | tiri, ascolti, e torni indietro se non ti piace |
| la stessa parte, un po' diversa | **COOK** (SEQ + bianco 9), più tocchi | cambia pochi passi alla volta: ti fermi quando va bene |
| che cambi da sola nel tempo | **EVOLVE** (SEQ + nero 9) | cucina ogni N battute; RETURN alto: resta vicina all'originale |
| che cambi da sola e vada lontano | **EVOLVE** con RETURN a 0 (o il tasto **DRIFT**) | non torna indietro: REVERT se vuoi tornare |
| un ritmo "matematico" sopra il mio | **EUCLID LIVE** (SEQ 1, poi SEQ + bianco 6) | non tocca il pattern finché non lo scrivi |
| più pieno o più vuoto, dal vivo | **ENERGIA** (GLO 3 K1) con i motori; altrimenti **THIN / SWELL** | lavorano su tutto il set, a tempo |
| una chiusura a fine frase | **FILL** (le MOSSE) | arriva a fine frase da sola |
| tornare a com'era | **UNDO** (SEQ + bianco 8), o **REVERT** dopo EVOLVE | |
| meno pagine sul pannello | il profilo **SEMPLICE** (SAVE + K4) | le pagine da laboratorio spariscono finché non le usi |

## Se qualcosa non torna

Le proposte sono fatte, ma provate solo nel simulatore, non su un FM-1 vero. Se suonandole qualcosa non va (le pagine
che SEMPLICE nasconde, il passo di RETURN, una riga dello schermo) dimmelo: si cambia nella versione dopo.
