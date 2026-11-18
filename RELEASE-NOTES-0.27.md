# SAGGA SEQ 0.27 - Note di rilascio

Dopo la 0.26 ti avevo dato la mappa dei generatori, con quattro proposte. Le hai volute tutte e quattro, e mi hai detto
di correggere l'arpeggio. **Sono dentro tutte e cinque.**

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.27.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.27.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |
| la mappa dei generatori, con quello che è cambiato | `MAPPA-GENERATORI.md` |

Vanno installati tutti e due. I progetti di prima si aprono come sono, e suonano come prima.

## Le cinque cose

| cosa avevi chiesto | adesso |
| --- | --- |
| **correggi l'arpeggio** | senza tonalità, ogni parte dei motori parte dalla fondamentale del progetto: l'arpeggio della BAND non suona più una quinta sopra |
| **un profilo che nasconde** | SAVE + K4 ora va FULL, **SEMPLICE**, PALCO. SEMPLICE nasconde le pagine SEQ 2 e SEQ 3 finché non suonano |
| **RANDOM come un dado** | RANDOM aspetta come un dado: con OCT+ lo tieni, con OCT- torni indietro, con ALG rivedi i tiri |
| **DRIFT dentro EVOLVE** | EVOLVE ha una manopola nuova, **RETURN**: 100 resta vicino al pattern di partenza, 0 è DRIFT, in mezzo torna un po' |
| **lo schermo dice chi sta agendo** | DENSITY, CHANCE, ENERGIA, THIN e SWELL dicono su cosa lavorano: questa traccia, o tutto il set |

## 1. L'arpeggio senza tonalità

In un progetto **senza tonalità** (la scala CHROMA, com'è un progetto nuovo) una parte prendeva come fondamentale la
nota da cui parte. Per l'arpeggio quella nota era un Sol: l'arpeggio della BAND, della libreria e dei motori, suonava
una quinta sopra il basso e gli accordi.

Adesso una parte scritta senza tonalità su una traccia nuova (con BAND, con BEAT dei motori, o una proposta delle
MOSSE) parte dalla **fondamentale del progetto** (il Do, in un progetto nuovo), nel suo registro. Basso, accordi e
arpeggio suonano nello stesso accordo.

Con una tonalità non cambia niente: era già giusto.

## 2. Il profilo SEMPLICE

**SAVE + K4** sceglie il profilo. Ora sono tre, in quest'ordine: **FULL, SEMPLICE, PALCO**.

* **SEMPLICE** è FULL, ma nasconde le pagine dei generatori "da laboratorio": **SEQ 2** (i quattro algoritmi) e **SEQ 3**
  (EVOLVE). Tenendo SEQ, OCT- e OCT+ le saltano.
* **Non spegne niente.** Se sulla traccia scelta c'è un algoritmo, SEQ 2 c'è. Se EVOLVE è acceso, SEQ 3 c'è.
* Lo schermo, quando lo scegli: `PROFILE SEMPLICE: SEQ 2 AND 3 HIDDEN WHILE OFF`.
* **PALCO** è come prima, ma ora è a due scatti di K4 invece di uno.

Il profilo sta nelle impostazioni dell'FM-1, non nel progetto: alla riaccensione lo ritrovi.

## 3. RANDOM è un tiro di dado

Stesso gesto (**SEQ + bianco 5**), stessa musica (una battuta a caso e la sua frase), sulle tracce dello SCOPE. Ma ora
aspetta come un dado:

* lo schermo dice `RANDOM: OCT+ KEEP, OCT- BACK`;
* **OCT+** lo tieni; **OCT-** (o UNDO) torni a com'era prima del primo tiro;
* **ALG** rivede i tiri, fino a 16, insieme a quelli degli altri dadi (`RANDOM 2/2 ALG`);
* premuto di nuovo, è un altro tiro.

Se RANDOM lo ripete **EVERY** (la pagina SEQ 6), cambia subito, come prima: nessun dado resta ad aspettare.

## 4. RETURN: DRIFT dentro EVOLVE

Sulla pagina **SEQ 3** (EVOLVE), **SEL + K2** è **RETURN**, il ritorno, da 0 a 100 %. Prima di ogni cambio di
EVOLVE, dice quanta parte del pattern di partenza torna:

| RETURN | cosa fa | lo schermo |
| --- | --- | --- |
| **100** | ogni cambio parte dal pattern di partenza: EVOLVE gli resta vicino. È l'EVOLVE di sempre | `FROM THE SEED EVERY TIME` |
| **in mezzo** | torna quella parte dei passi (e degli LFO), il resto continua ad andare: un EVOLVE "al guinzaglio" | `PART OF THE WAY BACK` |
| **0** | ogni cambio parte dall'ultimo, e va lontano senza tornare. È DRIFT | `DRIFT, NO WAY BACK` |

Il tasto **DRIFT** (SEQ + nero 8) resta, come scorciatoia: porta RETURN a 0 (`DRIFT: EVOLVE WANDERS AWAY`) e, premuto
di nuovo, lo rimette dov'era (`NO DRIFT: EVOLVE RETURN 50%`, o `NO DRIFT: EVOLVE STAYS NEAR THE SEED` se era 100).
Il messaggio di EVOLVE dice il RETURN quando non è 100: `EVOLVE 30% EVERY 4 RETURN 50%`, o `... DRIFT` a 0.

Un progetto di prima con DRIFT acceso si apre con RETURN 0, e suona uguale.

## 5. Lo schermo dice chi sta agendo

Le quattro mani del "più pieno, più vuoto" restano quattro, perché lavorano su cose diverse. Adesso ognuna lo dice:

| la mano | dove | lo schermo |
| --- | --- | --- |
| DENSITY | SEQ 2 | `T3 DENSITY 60%: THIS TRACK ONLY` |
| CHANCE | HOME 6 | `T3 CHANCE 40%: THIS TRACK ONLY` |
| l'ENERGIA | GLO 3 K1 | `ENERGY 70: THE WHOLE SET + 4 ENGINE PARTS`: tutto il set, e quante parti dei motori riempie e svuota |
| THIN, SWELL | le MOSSE | `QUEUED: THIN - THE WHOLE SET, 2 TRACKS OUT`, `QUEUED: SWELL - THE WHOLE SET, 2 TRACKS IN` |

## Come è stato provato

{{PROVE}}

**Non ho un FM-1 in mano**: tutto questo è provato sul simulatore, non sullo strumento vero.

## Installare

Come sempre: prima il Pi (`sagga-hub-0.27.zip`), poi l'FM-1 (`sagga-0.27.fwsc`). I passi sono in `INSTALLA.md`.
Sullo schermo, dopo l'aggiornamento: `SAGGA SEQ 0.27` per tre secondi.

## Cosa provare per primo

1. **L'arpeggio**: un progetto nuovo, il genere TRANCE (SEQ + PRESETS), poi BAND (SEQ + nero 7 tenuto). Basso,
   accordi e arpeggio nello stesso accordo. Anche con i motori (SEQ 8 K1 su THEORY).
2. **RANDOM**: SEQ + bianco 5, ascolta; ancora SEQ + bianco 5; gira ALG per tornare al primo tiro; OCT+ per tenerlo.
3. **RETURN**: accendi EVOLVE (SEQ + nero 9), vai su SEQ 3, tieni SEL e gira K2 fino a 50. Ascolta per qualche
   battuta: cambia, ma non si perde.
4. **SEMPLICE**: SAVE + K4 di uno scatto. Con SEQ tenuto, OCT+ salta da SEQ 1 a SEQ 4.

## Da sapere

* **Le band già fatte senza tonalità** restano come sono: i pattern scritti non cambiano. Per metterle a posto scegli
  una tonalità (HOME 3: K2 la fondamentale, K3 la scala) e rifai BAND.
* **Tornare alla 0.26**: un FM-1 con la 0.26 apre i progetti della 0.27. Il RETURN diventa DRIFT acceso (sotto il
  50 %) o spento (dal 50 % in su). Il profilo SEMPLICE, la 0.26 non lo conosce: torna FULL.
* **In SEMPLICE**, per usare un algoritmo o EVOLVE la prima volta: EVOLVE si accende con SEQ + nero 9 da qualunque
  pagina, e allora SEQ 3 compare. Per un algoritmo torna un momento a FULL: quando la traccia ne ha uno, SEQ 2 resta
  visibile anche in SEMPLICE.
* **Il click dell'FM-1** (della 0.26) va ancora provato sullo strumento. Se non lo senti, CLICK OUT su un canale MIDI
  funziona di sicuro.

## La dimensione

{{DIMENSIONE}}
