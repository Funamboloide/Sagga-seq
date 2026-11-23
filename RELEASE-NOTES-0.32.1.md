# SAGGA SEQ 0.32.1 - Note di rilascio

Mi hai mandato i log della 0.32 sull'FM-1 vero e mi hai chiesto di ricontrollare, con un modello più forte, tutto quello
che è stato fatto dalla 0.27 in poi: l'FM-1, il Pi e il bridge. **I log dicono che l'FM-1 fa quello che deve.** Rileggendo
il codice non ho trovato errori gravi; ho trovato quattro cose che non tornavano con quello che avevi chiesto, o che
potevano far danno, e le ho sistemate.

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

## 2. Il tablet arriva alle 32 scene e alle 16 snapshot

Con la 0.30 avevi chiesto 32 scene e 16 snapshot. Sull'FM-1 e sul grid c'erano; **la pagina SAGGA Remote era rimasta a
8 scene e 8 snapshot**. Adesso:

* **SCENES** (una manopola nuova, sotto i bottoni delle scene): sceglie quali otto scene sono i bottoni SCENE 1-8.
  Va su 1-8, 9-16, 17-24, 25-32. Con SCENES su 9-16, SCENE 3 è la scena 11 (lo schermo dell'FM-1 dice il numero vero).
* **SNAPS** (in fondo alla pagina): sceglie quali otto snapshot sono SNAP 1-8 e STORE 1-8. Va su 1-8 o 9-16.
* **MORPH TO** arriva alla scena 32 (si fermava alla 8), e segue l'FM-1 anche oltre la 8.

Le due manopole sono del tablet, come la sua traccia: i tasti dell'FM-1 e il grid tengono i loro gruppi di otto. Servono
REMOTE 13 + 14 sull'FM-1 (SAVE + K2), come per le altre pagine.

## 3. I pad che cambiano tutto in un colpo adesso chiedono prima

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

## 4. Due cose piccole

* **LFO + nero 11** (l'LFO da capo, due volte): se fra il primo e il secondo tocco sceglievi un altro LFO, azzerava
  quello nuovo senza chiedere. Adesso chiede di nuovo, per quello.
* **La mappa dei tasti** (un bottone tenuto mezzo secondo): HOME e GLO non dicevano i lavori che la 0.31 aveva dato ai
  bianchi 13-16. Adesso sì: `W TRK 13-16 STEP PG` (HOME: la pagina degli step), `W MUTE 13-16 GROUPS` (GLO: i gruppi).

## Cosa ho riletto

Tutto il codice cambiato dalla 0.26 alla 0.32: i tasti e le manopole del pannello, il grid, le MOSSE, il remoto, il
tablet, il salvataggio, le sei pagine SAGGA del Pi, l'editor dei progetti, il bridge del grid, l'installatore. Ho
cercato in particolare i resti dei numeri vecchi (16 tracce, 8 scene, 4 note, 6 lane, 25 generi) e i messaggi con i nomi
vecchi (VIAGGIO): non ce ne sono. Le guardie delle dodici tracce sono a posto dappertutto.

## Come è stato provato

PROVE_QUI

## Installare

Come sempre: prima il Pi (`sagga-hub-0.32.1.zip`), poi l'FM-1 (`sagga-0.32.1.fwsc`). I passi sono in `INSTALLA.md`.
Sullo schermo, dopo l'aggiornamento: `SAGGA SEQ 0.32.1` per tre secondi.

Dopo l'aggiornamento del Pi, la pagina SAGGA Remote ha una riga in più: le due manopole nuove compaiono da sole.

## La dimensione

DIMENSIONE
