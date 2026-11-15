# SAGGA SEQ 0.20.9 - Note di rilascio

**Cambiano il Pi (soprattutto) e, di poco, l'FM-1 (solo il suo test).** Il formato dei progetti resta `SGQB`.

## Cosa hanno trovato le prove della 0.20.8

* **L'FM-1 completo, 28 sessioni**: l'FM-1 fa quello che fa il simulatore. L'unico errore (s006) era del confronto: una
  sonda caduta sul confine di uno step (l'FM-1 l'ha letta un tick di clock prima) lo faceva sembrare diverso, e da lì in
  poi tutte (le sonde arrivano ogni 700 ms, sei step: se una cade sul confine, cadono tutte). Adesso il confronto guarda
  anche il tick di ogni sonda: un tick di differenza, poi di nuovo uguali, è TEMPO. Un tick perso per sempre resta un
  errore.
* **s027 e s028, VALORI**: non era l'FM-1 e non erano le pagine. **RaspiMIDIHub 6 perde le celle di un dispositivo che
  non c'è**: il suo salvataggio automatico (ogni 15-30 secondi quando qualcosa è cambiato, e le pagine SAGGA cambiano
  sempre, seguono l'FM-1) scrive solo le celle dei dispositivi presenti. Se in quel secondo l'FM-1 si sta riavviando, o è
  spento, le sue celle spariscono anche dalla memoria di RaspiMIDIHub, e quando l'FM-1 torna non le rimette. Nella prova
  è successo al 27° riavvio; nell'uso normale può succedere quando spegni l'FM-1 poco dopo averlo usato.
* **Il banco fermo al 4° riavvio**: l'FM-1 non ha risposto per 40 secondi, con le porte lì. Dai log non si capisce se
  l'FM-1 era sordo o il Pi non l'aveva visto andare e tornare. E il tuo progetto non è tornato in memoria.

## Il Pi: il custode delle celle dell'FM-1

Il Pi ricorda le celle dell'FM-1 (con le pagine, con i synth, con i loro filtri e le mappature) finché l'FM-1 c'è. Quando
l'FM-1 se ne va e torna (spento, riavviato, aggiornato: lo dice il suo numero USB, che cambia ogni volta), o quando se ne
va e torna l'altro capo di una cella, aspetta che RaspiMIDIHub faccia il suo (5 secondi) e rimette quelle che mancano,
come erano. Sulla pagina del Pi, **LE CELLE DELL'FM-1**, dice cosa ha rimesso e quando.

* Una cella che togli **con l'FM-1 acceso** resta tolta: il custode la dimentica. Con l'FM-1 spento, invece, torna.
* La prima volta parte dalle celle che servono alle pagine SAGGA (ogni pagina verso la porta 2 dell'FM-1, la porta 2
  verso ogni pagina): **quelle che la prova della 0.20.8 ti ha fatto perdere tornano da sole** appena aggiorni il Pi.
* I Launchpad non hanno celle (parlano solo con il bridge): mai rimesse.
* Il ricordo sta in `/boot/firmware/sagga/celle-fm1.json`, anche dopo un riavvio del Pi.

## Il banco: i riavvii

* Dopo ogni riavvio dell'FM-1 il banco controlla che le sue celle siano tornate e rimette quelle che RaspiMIDIHub ha
  perso, prima della sessione: VALORI torna a dire qualcosa. Il rapporto dice quante ne ha rimesse.
* Se l'FM-1 non risponde per 12 secondi dopo un riavvio, il Pi lo fa ritrovare all'USB (un reset della sua porta,
  come staccato e riattaccato), poi aspetta altri 30 secondi.
* Nel log, a ogni riavvio, le righe del kernel sull'USB e i contatori dell'FM-1 (quanti HELLO ha sentito dal suo avvio,
  quante risposte non sono partite, quando il Pi l'ha configurato, quanto è rimasto fermo il suo giro principale): se
  succede di nuovo, si capisce da che parte.
* Se l'FM-1 non torna più, il progetto che aveva in memoria prima della prova va nella libreria del Pi, come
  `prima-del-banco-<data>.sgq`: **PROGETTI**, editor, **Manda all'FM-1**.

## Le pagine del hub

* **SAGGA Mod**: il PANIC del hub non spegne più l'LFO (LFO ON è uno stato dell'FM-1, come i mute di SAGGA Live: dalla
  0.18 la pagina lo segue, non lo comanda a vuoto).
* I testi di Motori, Mod, Break e Remote dicono "la traccia del tablet" dove dicevano "la traccia selezionata": dalla
  0.18 le pagine lavorano sulla traccia scelta con TRACK, non su quella dell'FM-1.

## L'FM-1: i contatori del test

Il test dell'FM-1 risponde a una domanda nuova (DIAG) con 19 numeri dal suo avvio: i HELLO e i messaggi del test
arrivati, le risposte che l'USB non ha potuto mandare, quando è partito il giro principale e quanto è rimasto fermo al
massimo, i reset del bus e le configurazioni del Pi (e a che ms), i pacchetti arrivati, trattenuti e mandati, i pezzi di
SysEx persi. Fuori dal test non cambia niente.

## Provato

* Il confronto: tre sonde con gli step e il tick uno avanti, poi un pattern diverso: l'errore è il pattern, alla sua
  sonda; gli step e il tick uno avanti fino alla fine: errore. Le 28 sessioni della 0.20.8 di nuovo: s006 è TEMPO.
* Il custode contro un RaspiMIDIHub finto che perde le celle come il vero: l'FM-1 riavviato (tutte e 6 tornano, il filtro
  e la mappatura del synth compresi), spento a lungo, un synth staccato e tornato su un altro numero, una cella tolta a
  mano (resta tolta), RaspiMIDIHub che si riavvia, il Pi che si riavvia (il ricordo dalla SD), la prima volta (le celle
  delle pagine dalla regola), il numero USB che non si legge (la cella torna, non si dimentica).
* Il banco con un RaspiMIDIHub che perde le celle a ogni riavvio: le rimette, le pagine funzionano, i valori tornano;
  con un FM-1 sordo dopo il secondo riavvio: ritrovato all'USB, la prova va avanti; con un FM-1 che non torna: il
  progetto nella libreria.
* La DIAG nel simulatore.
* Le pagine nel vero host dei plugin di RaspiMIDIHub (con un suo checkout): 96 controlli, compresi i quattro CC di
  ritorno della 0.20.6. Questa parte dei test non girava più da quando esiste il finto hub dei test: sistemata.

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.20.9.zip`. Dopo l'aggiornamento guarda **LE CELLE
   DELL'FM-1**: se la prova della 0.20.8 aveva fatto perdere le celle delle pagine, dice che le ha rimesse.
2. **L'FM-1**: FM-1 fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.20.9.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.20.9`.
3. Se vuoi, rifai le due prove (il banco e l'FM-1 completo) e mandami le raccolte e i log.

## Da sapere: RaspiMIDIHub

Il difetto è di RaspiMIDIHub (6.0.0): il suo salvataggio (`snapshot`) dovrebbe tenere le celle dei dispositivi che in
quel momento non ci sono. Vale per ogni dispositivo, non solo per l'FM-1: un synth staccato durante un salvataggio
automatico torna senza le sue celle. Il custode del Pi lo copre per l'FM-1; per gli altri, conviene segnalarlo a chi fa
RaspiMIDIHub.
