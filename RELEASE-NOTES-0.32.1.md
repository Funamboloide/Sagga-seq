# SAGGA SEQ 0.32.1 - Note di rilascio

Mi hai mandato i log della 0.32 sull'FM-1 vero e mi hai chiesto di ricontrollare, con un modello più forte, tutto quello
che è stato fatto dalla 0.27 in poi: l'FM-1, il Pi e il bridge. **I log dicono che l'FM-1 fa quello che deve.** Rileggendo
il codice ho trovato **un errore vero**, che c'era dalla 0.29 (la sezione 2), e sei cose più piccole: non tornavano
con quello che avevi chiesto, o potevano far danno (le sezioni 3, 4 e 5). Sono tutte sistemate.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.32.1.fwsc` |
| il Pi: la pagina SAGGA Remote nuova, il banco (e tutto il resto, come sempre) | `sagga-hub-0.32.1.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due, insieme**: le manopole nuove di SAGGA Remote mandano numeri che solo l'FM-1 0.32.1
capisce. I progetti non cambiano.

## 1. I tuoi log: l'FM-1 vero con la 0.32

Hai fatto girare tutti e due i piani: il banco (32 sessioni) e l'FM-1 completo (37). **In tutte e 69 le sessioni l'FM-1
fa esattamente quello che fa il simulatore**, comprese quelle con le cose della 0.28, 0.29, 0.30, 0.31 e 0.32.

Il rapporto segnava quattro cose. Le ho guardate una per una: **nessuna è un errore dell'FM-1, tutte e quattro erano
dello strumento che confronta**. Adesso non le segna più.

| cosa segnava | cos'era davvero |
| --- | --- |
| **s024**: l'FM-1 diverso dal simulatore (i mute) | La sonda è caduta proprio sulla battuta dove entrava una scena in coda. L'FM-1 l'ha letta un attimo prima (un tick di clock), il simulatore un attimo dopo. È una questione di tempo, non di comportamento. |
| **b012**: una nota persa | Per far tornare una sonda il confronto aveva spostato i tasti di 2 millisecondi, e così il simulatore suonava una nota in più. Con i tempi veri dell'FM-1 quella nota non la suona nemmeno il simulatore. Niente di perso. |
| **b030**: due celle delle pagine non seguono l'FM-1 | Un pad del grid aveva spento il REMOTE. Da lì l'FM-1 non ascolta più le pagine, com'è giusto. |
| **b032**: una cella non segue (il SEED) | Il SEED vale solo per i pattern fatti dai motori. Quel pattern non lo era, quindi l'FM-1 non aveva niente da mostrare. |

Con lo strumento corretto, le tue due raccolte danno **0 errori**.

Una cosa resta, e non è nuova: in 7 riavvii su 32 l'FM-1 ci ha messo più di 12 secondi a farsi ritrovare dal Pi sull'USB.
Il Pi lo recupera da solo (lo fa dalla 0.20.9) e la prova va avanti, ma dura qualche minuto in più. Senza un FM-1 in
mano non posso provare una correzione lì, quindi non l'ho toccato.

## 2. Un errore vero, dalla 0.29: quattro forme di accordo

Con la 0.29 avevi chiesto più accordi, e sono arrivate quattro forme nuove: **7#9, 7B9, MAJ7#11 e QUARTAL**. Su una
traccia (ARP 2, CHORD) funzionano dalla 0.29. In una **progressione USER** no: lì K4 (ARP 5) sceglie la forma di ogni
accordo, e l'FM-1 scrive sullo schermo il nome dell'accordo. La tabella dei nomi era rimasta a 32 righe; le forme sono
36. Appena K4 arrivava a una delle quattro nuove, l'FM-1 cercava un nome che non c'era.

Cosa succede sull'FM-1 vero non lo so, perché non ne ho uno: nel simulatore il programma si ferma in quel punto.
Sull'FM-1 mi aspetto lo schermo rosso `SAGGA SEQ CRASH` e il riavvio, oppure lettere a caso al posto del nome. Lo stesso
valeva per ARP 3 (l'accordo che suona) con una progressione così, anche arrivata dal Pi. Dalla 0.29 alla 0.32.

Adesso le quattro forme hanno il loro nome: `I7#9`, `I7b9`, `Imaj7#11`, `Iq4`. Un progetto salvato con una di queste
forme in una progressione USER, con la 0.32.1 si apre e si suona come gli altri.

**Perché nessuna prova l'aveva visto.** Per arrivarci bisogna girare K4 fino in fondo alla lista. Le prove e
l'esploratore giravano ogni manopola di uno scatto in su e uno in giù. Ho cambiato due cose, perché un errore così non
passi più:

* **Il compilatore conta la tabella.** Se manca un nome, il firmware non si costruisce. Ho fatto contare nello stesso
  modo tutte le 244 tabelle del firmware che hanno una misura: le altre 243 sono giuste. Questo controllo adesso gira
  con i test, a ogni versione.
* **L'esploratore gira ogni manopola tutta su e tutta giù**, in ogni pagina e in ogni situazione (1050 gesti in più per
  situazione). Con il firmware della 0.32 trova questo errore subito. Dove c'è il tablet manda anche ogni controller
  dei canali del remoto al valore più alto (359 gesti in più).

Guardando lì vicino ho trovato un secondo errore, più piccolo e più vecchio. Nella pagina ARP 3 lo spazio per l'accordo
che suona teneva 11 caratteri. Un nome lungo con un posto a due cifre, per esempio `bVII9sus4 10`, scriveva un carattere
oltre. Di solito non fa niente, ma è un errore: adesso lo spazio basta per il nome più lungo.

## 3. Il tablet arriva alle 32 scene e alle 16 snapshot

Con la 0.30 avevi chiesto 32 scene e 16 snapshot. Sull'FM-1 e sul grid c'erano; **la pagina SAGGA Remote era rimasta a
8 scene e 8 snapshot**. Adesso:

* **SCENES** (una manopola nuova, sotto i bottoni delle scene): sceglie quali otto scene sono i bottoni SCENE 1-8.
  Va su 1-8, 9-16, 17-24, 25-32. Con SCENES su 9-16, SCENE 3 è la scena 11 (lo schermo dell'FM-1 dice il numero vero).
* **SNAPS** (in fondo alla pagina): sceglie quali otto snapshot sono SNAP 1-8 e STORE 1-8. Va su 1-8 o 9-16.
* **MORPH TO** arriva alla scena 32 (si fermava alla 8), e segue l'FM-1 anche oltre la 8.

Le due manopole sono del tablet, come la sua traccia: girarle non sposta niente sull'FM-1. Quando poi richiami una scena
o una snapshot, l'FM-1 ci va con il suo cursore, come quando lo fai dai suoi tasti. Servono REMOTE 13 + 14 sull'FM-1
(SAVE + K2), come per le altre pagine.

## 4. I pad che cambiano tutto in un colpo adesso chiedono prima

La 0.31 e la 0.32 avevano dato a qualche pad del grid un lavoro "di massa": un tocco solo, niente UNDO. Un dito sul pad
sbagliato, dal vivo, e tutte le tracce suonavano altri synth. Adesso **il primo tocco chiede, lo stesso pad entro tre
secondi lo fa** (come CLEAR e PROGETTO NUOVO):

| vista | pad | cosa fa |
| --- | --- | --- |
| PROJ, riga 4 | 13 | ogni traccia sul suo canale MIDI |
| PROJ, riga 4 | 14 | le batterie sul canale 10 |
| TRACK, riga 7 | 16 | la VEL OFFSET di tutte le tracce a 0 |
| TRACK 2, riga 5 | 13 | i programmi di una scena in tutte e 32 le scene |
| TRACK 2, riga 5 | 15 | il programma di un canale in tutte e 32 le scene |

Lo schermo lo dice: `EVERY TRACK ON ITS OWN CHANNEL? AGAIN: YES`.

## 5. Quattro cose piccole

* **LFO + nero 11** (l'LFO da capo, due volte): se fra il primo e il secondo tocco sceglievi un altro LFO, azzerava
  quello nuovo senza chiedere. Adesso chiede di nuovo, per quello.
* **La mappa dei tasti** (un bottone tenuto mezzo secondo): HOME e GLO non dicevano i lavori che la 0.31 aveva dato ai
  bianchi 13-16. Adesso sì: `W TRK 13-16 STEP PG` (HOME: la pagina degli step), `W MUTE 13-16 GROUPS` (GLO: i gruppi).
* **La song all'entrata 128** (l'editor dei progetti, sul Pi): la riga in alto, quella che segue la musica, smetteva
  di dire `song` quando la song arrivava alla sua ultima entrata possibile, la 128. Il numero che l'FM-1 mandava per
  quell'entrata era lo stesso di "nessuna song". Adesso l'FM-1 dice a parte se la song è accesa, e il Pi lo legge.
* **La chiave delle MOSSE** (GLO 3, K4): girata di più di due ottave in giù in un colpo solo, finiva su una nota che
  non esiste. Con le mani non ci si arriva, e dal tablet nemmeno: l'ha trovato l'esploratore con le manopole girate
  fino in fondo (sezione 2). Adesso gira intorno alle dodici note comunque la giri.

## Cosa ho riletto

Tutto il codice cambiato dalla 0.26 alla 0.32, riga per riga: i tasti e le manopole del pannello, il grid, le MOSSE, i
generatori, i motori THEORY, il formato dei progetti salvati, il remoto, il tablet, le sei pagine SAGGA del Pi, l'editor
dei progetti, il bridge del grid, l'installatore.

Ho cercato in particolare i resti dei numeri vecchi: 16 tracce, 8 scene, 8 snapshot, 4 note, 6 lane, 25 generi, 32
forme di accordo. Ne ho trovati due: le scene e le snapshot del tablet (sezione 3) e i nomi degli accordi (sezione 2).
Il secondo non l'ho trovato leggendo: l'ho trovato facendo contare al compilatore ogni tabella del firmware. Le guardie
delle dodici tracce sono a posto dappertutto, e sullo schermo non c'è più nessun messaggio con il nome vecchio
(VIAGGIO).

## Come è stato provato

PROVE_QUI

## Installare

Come sempre: prima il Pi (`sagga-hub-0.32.1.zip`), poi l'FM-1 (`sagga-0.32.1.fwsc`). I passi sono in `INSTALLA.md`.
Sullo schermo, dopo l'aggiornamento: `SAGGA SEQ 0.32.1` per tre secondi.

Dopo l'aggiornamento del Pi, la pagina SAGGA Remote ha una riga in più: le due manopole nuove compaiono da sole.

## La dimensione

DIMENSIONE
