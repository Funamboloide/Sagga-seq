# SAGGA SEQ 0.21 - Note di rilascio

**La 0.20.9 riletta da capo a fondo: un FM-1, un Pi (con il grid dentro), il manuale.** Nessuna funzione nuova da
imparare; il formato dei progetti resta `SGQB`. Si installa al posto della 0.20.9 (non serve passarci).

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.21.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, **il bridge del grid** | `sagga-hub-0.21.zip` |
| come si installa e si aggiorna, in un foglio solo | `INSTALLA.md` |
| il manuale | "SAGGA SEQ 0.21 - Manuale d'uso" (il documento di sempre, aggiornato) |

## Cosa ho trovato

### Un errore vero nell'FM-1: una riga dello schermo scriveva oltre la sua memoria

La quinta riga dello schermo, quella che dice cosa sta succedendo (`DICE? +KEEP -BACK`, `EVOLVE`, `SONG`, `TEMP`,
`LOOP`, `STOP@BAR`, `RESTART`, `TR>`, `MACRO`, `MOTION`, `MORPH`, `LEARN`, `RELOAD`, `MUTES WAIT`, `ECHO ALL`,
`STEP LOOP`, `TOOL WAITS`, `EVERY`, `SNAP`, `CAPTURE`, l'accordo), veniva composta in 64 caratteri di memoria senza
niente che la fermasse. Lo schermo ne mostra 31, e finché le scritte accese insieme erano poche non succedeva nulla. Ma
sette o otto insieme passano i 64: un dado in attesa, TEMP tenuto, un LOOP, RESTART, un macro mosso, MORPH, ECHO ALL.
Da lì l'FM-1 scriveva nella memoria accanto: quello che capita dopo non si può prevedere (un blocco, un riavvio, niente).
È il genere di momento che succede dal vivo, non a casa.

L'ha trovato la prova a caso con il controllo della memoria acceso (una volta su cinquecento); poi l'ho rifatto apposta
con sette comandi delle pagine, e la 0.20.9 nel simulatore muore. Adesso le righe dello schermo si scrivono in una
memoria che taglia da sola alla fine, come i messaggi facevano già dalla 0.7. La riga resta di 31 caratteri: con tante
scritte insieme vedi le prime.

### Le pagine del tablet

* **Un valore mosso dal tablet tornava "appena mosso" 65 secondi dopo**, per 0,4 secondi (il contatore di quel momento
  ha 16 bit di millisecondi e fa il giro): un cambio fatto sul pannello in quell'istante arrivava alla pagina in
  ritardo. Adesso i contatori vengono tenuti giovani.
* **SAGGA Break segue la traccia del tablet** come le altre pagine: SWAP, ROLLS e SLICES tornano dall'FM-1 (canale 13,
  CC 73-75) quando cambi TRACK o li giri sull'FM-1. Era l'unica pagina con le manopole ferme.

### Il Pi

* **Una pagina SAGGA nuova si collega da sola.** Quando aggiungi una pagina in RaspiMIDIHub (o tutte, la prima volta),
  il custode delle celle mette le sue due celle: il suo OUT verso la porta 2 dell'FM-1, la porta 2 verso il suo IN (per
  SAGGA BeatStep solo l'OUT). Lo fa una volta per pagina, con USB PORTS 2 sull'FM-1; se poi togli una cella a mano,
  resta tolta. Sulla pagina del Pi: `pagina nuova, collegata`. Prima andava fatto a mano, due celle per pagina.

### Piccole cose

* TOOLS WHEN: un valore fuori scala (un progetto rovinato) avrebbe diviso per zero; adesso aspetta la battuta.
* Testi e commenti rimasti indietro: i generi sono 25 (dicevano 24 in tre posti), i MIDI FX del tablet sono 0-9.
* Tre cose inutili tolte dal codice (un valore scritto due volte, una scelta con due rami uguali, import non usati).

## Cosa non ho trovato

Ho cercato con tutto quello che c'è, e tolto l'errore dello schermo il resto ha tenuto:

* il simulatore con il controllo della memoria (ASan e UBSan): i 1093 controlli, i 9340 gesti dell'esploratore in 5
  situazioni, il banco di prova;
* più di 1100 prove a caso da un minuto con il controllo della memoria, più di 300 delle quali con le pagine del tablet
  (canali 12 e 13, i pad, USB PORTS 2); più di 20.000 messaggi SysEx sbagliati apposta, di ogni tipo che l'FM-1
  conosce: nessun altro errore;
* 180 progetti con i byte cambiati a caso, mandati all'FM-1 come li manda il Pi (ne ha accettati 121), suonati e
  guardati su ogni pagina del pannello e del grid: quello che l'FM-1 accetta, lo regge;
* tre analizzatori del codice (gcc, clang, clang-tidy) e ruff sui programmi del Pi: niente di vero.

## I test, perché la prossima volta lo trovino prima

* La prova a caso gira **sempre con il controllo della memoria**, suona anche le pagine del tablet, parte una volta su
  otto da un progetto rovinato, e rifà ogni volta il caso che ha trovato l'errore.
* La suite **fallisce quando un test fallisce**: prima finiva sempre bene (guardava solo l'ultima riga di ogni test).
* I due programmi dell'FM-1 (quello vero e il caricatore degli aggiornamenti) vengono controllati prima di mandarli a
  GitHub: la prima 0.20.9 non si compilava, e me ne sono accorto solo lì.

## I documenti

* **Un foglio solo per installare e aggiornare**: `docs/INSTALLA.md` (i due file, il caso normale, la prima volta sul
  Pi e sull'FM-1, il grid, come controllare, cosa fare se non va). Prima erano diciannove fogli, uno per versione, che si
  rimandavano l'uno all'altro.
* Le note e i fogli delle versioni passate (0.8 - 0.20.9) sono in `docs/storia/`; il riferimento in inglese
  (`docs/SAGGA-SEQ.md`) non comincia più con 800 righe di storia.
* **Il manuale** (0.21): il capitolo 2 con i file giusti, l'aggiornamento dalla pagina del Pi e `--no-pc` (senza, lo
  script spegne il Bluetooth: è per l'expander); le pagine LFO sono 6, non 4; i MIDI FX salvati sono nove, non quattro;
  i valori tornano al tablet da soli (non "dopo il primo comando"); le pagine nuove collegate dal Pi; SAGGA Break che
  segue; cosa fare se le pagine smettono di comandare dopo un riavvio.

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.21.zip`. In alto deve dire `SAGGA HUB 0.21`.
2. **L'FM-1**: fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.21.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.21`.
3. Guarda **LE CELLE DELL'FM-1**: se la prova della 0.20.8 aveva fatto perdere le celle delle pagine, dice che le ha
   rimesse.

## Da sapere

* **Il custode delle celle non ha ancora girato sul tuo Pi** (è nato con la 0.20.9, ieri sera): è provato contro un
  RaspiMIDIHub finto che perde le celle come il vero. La prima volta guarda cosa dice la sua sezione; per spegnerlo,
  `--senza-custode` in `sagga-fw.service`.
* **L'FM-1 sordo dopo un riavvio** (il banco della 0.20.8 fermo al quarto): la causa non la so ancora. Dalla 0.20.9 il
  banco lo fa ritrovare all'USB e scrive nel log le righe del kernel e i contatori dell'FM-1: alla prossima prova si
  capisce da che parte sta.
* **RaspiMIDIHub 6 perde le celle di un dispositivo assente** durante il suo salvataggio automatico: il difetto è suo,
  e vale per ogni dispositivo, non solo per l'FM-1. Conviene segnalarlo a chi lo fa.
* Il riferimento in inglese porta ancora, riga per riga, i segni delle versioni (`0.16: ...; 0.19: ...`): è giusto ma
  faticoso. Il manuale in italiano è quello pulito.
