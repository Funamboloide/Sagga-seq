# SAGGA SEQ 0.30 - Note di rilascio

Per la RAM avevi scelto: **"32 scene e song da 128"**, **"16 snapshot"**, **"TAPE doppia e UNDO a 32"**. **Eccoli**:
le scene sono **32**, le snapshot **16**, la song ha **128 entrate**, le TAPE tengono **3072 eventi** e UNDO torna
indietro di **32 righe**. E il nome **VIAGGIO** non c'è più da nessuna parte: la vista del grid si chiama **MOSSE**, come
la pagina dell'FM-1.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.30.fwsc` |
| il Pi: l'editor, le pagine SAGGA, il bridge del grid, il banco | `sagga-hub-0.30.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due, insieme**. Si possono saltare le versioni: dalla 0.27 alla 0.30 in un colpo va bene
(qui sotto, in fondo, cosa hanno portato la 0.28 e la 0.29).

## 1. Le scene: 32

* In PERF (tocca GLO) **PRESETS** porta il cursore delle scene da 1 a 32. Lo schermo dice `PERF SCENE 17`.
* **I neri 1-8 sono le otto scene del gruppo dove sta il cursore**: 1-8, 9-16, 17-24, 25-32. Con il cursore sulla 17,
  il nero 1 è la scena 17 e il nero 8 la 24.
* Come prima: il nero richiama la scena, **SEL + nero** la salva, **HOME + nero** la mette in fondo alla song.
* **Sul grid**: i bottoni delle scene seguono lo stesso gruppo. Nella vista **SONG** la riga 2 è scene 1-16, **con
  SHIFT 17-32** (se la scena dell'entrata sta nell'altra metà, il suo pad è blu). Nella vista **TRACK 2** la riga 5
  sono le scene del gruppo (il pad 16 manda i program della scena scelta, come prima). Nella vista **FX** la riga 7
  (MORPH TO) sono le scene del gruppo.
* **Il remoto** (canale 14): CC 28 / 29 la scena prima / dopo arrivano a tutte e 32; CC 40-47 restano le scene 1-8;
  **CC 2 (MORPH TO)**: da 0 a 31 è quella scena (da 32 in su: il valore diviso 4).

## 2. Le snapshot: 16

* **Tieni SAVE e premi il bianco 9 o il bianco 10**: le snapshot 1-8 o 9-16. Mentre tieni SAVE, il bianco del gruppo è
  acceso.
* Poi, come prima: **SAVE + nero 1-8** richiama, **SAVE + SEL + nero 1-8** salva, nel gruppo scelto.
* Una snapshot salvata o richiamata porta il gruppo con sé.
* **Sul grid**, vista FX, riga 8: i pad 5-12 sono le otto del gruppo; **SHIFT + pad 13** passa all'altro gruppo (con
  SHIFT tenuto il pad 13 è giallo per 1-8, blu per 9-16).
* Il remoto resta sulle snapshot 1-8 (CC 106-113 e 12-19).

## 3. La song: 128 entrate

* HOME + nero in PERF aggiunge un'entrata, fino a 128. Dopo la 128: `SONG FULL (128)`.
* Sul grid, vista SONG: otto pagine da 16 (riga 4, pad 13 e 14). Le righe 5-8, la song battuta per battuta, partono
  **dalla prima entrata della pagina**: anche le entrate dopo la 64 si vedono e si toccano (fino alla 0.29 le righe
  mostravano solo le prime 64 battute).

## 4. TAPE e UNDO

* Le TAPE delle dodici tracce insieme tengono **3072 eventi** (erano 1536). Dopo: `TAPE FULL`.
* **UNDO** torna indietro sulle ultime **32 righe** cambiate (erano 16): una modifica di una riga, 32 modifiche
  indietro.

## 5. VIAGGIO diventa MOSSE

Solo il nome: niente si è spostato.

* Il grid: il bottone PERF fa PERF, SONG, **MOSSE**.
* SAVE + bianco 16: `SAVE THE SET`, e poi `SET SAVED: 5 SCENES AND THE SONG` (erano JOURNEY). Il set suonato può
  diventare fino a **32 scene** (erano 16).
* SAVE + K2: `REMOTE ON CH 14 + PAGES ON CH 13`.
* Le pagine **SAGGA Mod** e **SAGGA Remote** (0.30) dicono MOSSE.

## 6. Un errore corretto

* **All'accensione** l'FM-1 caricava l'ultimo slot ma lasciava fuori i suoi **mute** e il **cursore delle scene**
  (tutte le tracce accese, scena 1); il LOAD (HOME + SAVE due volte) invece li rimetteva. Adesso li rimette anche
  l'accensione. Era così dalla 0.9. L'ho trovato scrivendo la prova delle 32 scene.

## 7. I progetti

* **I progetti di prima si aprono come erano.**
* Un progetto della 0.30 si salva come la 0.29, più un pezzo nuovo per quello che la 0.29 non ha: le scene 17-32 (con i
  loro metri), le entrate 65-128, le snapshot 9-16, gli eventi delle TAPE dopo il 1536.
* **Se torni alla 0.29**, apre i progetti della 0.30 con le prime 16 scene, 8 snapshot, 64 entrate e 1536 eventi.
* Uno slot resta di 32 KB. Un progetto pienissimo di tutto (TAPE lunghe, 16 snapshot, 32 scene) potrebbe non starci:
  l'FM-1 dice `TOO BIG FOR A SLOT` e lascia lo slot com'era. Per avere un'idea: una band intera con 16 snapshot sono
  7 KB.
* **Sul Pi** l'editor dei progetti ha le 32 scene, le 128 entrate e le 16 snapshot.

## 8. Se arrivi dalla 0.27

Le note intere sono in `docs/storia/RELEASE-NOTES-0.28.md` e `RELEASE-NOTES-0.29.md`. In breve:

* **0.28**: le tracce sono **12** (i neri 1-8 e il nero 9 per la banca 9-12); un passo tiene **6 note** (SEL + sei
  tasti); le lane CC sono **8** (ENV pagine 7 e 8). Un progetto della 0.27 si apre con le sue prime dodici tracce.
* **0.29**: i generi sono **22** (AMAPIANO dentro REGGAETON, BASSLINE dentro UK GARAGE, GRIME dentro DUBSTEP, AFRO
  HOUSE in GQOM e BATIDA) e c'è il **BALANI** con il suo **BALAFON**; ogni genere ha **8 progressioni**; REGGAETON e
  BALANI hanno le regole THEORY scritte a mano; in più gli effetti **ROLL** e **ACCENT**, **5 scale**, **3 groove**,
  **4 forme d'accordo**.
* Il manuale nuovo, "SAGGA SEQ 0.30 — Il manuale", spiega tutto da capo, con le cose nuove dentro le lezioni.

## 9. L'esploratore

L'esploratore prova ogni gesto in ogni situazione. Ha due situazioni nuove, così le cose della 0.28, 0.29 e 0.30 sono
dentro anche il piano per l'FM-1 vero (`fm1_piano.json`):

* **0.29**: una band BALANI dei motori (con il balafon), la scala HUNGARIAN MINOR, PROG 7, il groove MALI, ROLL e
  ACCENT in catena sulla traccia 3, in play.
* **0.30**: le scene 17 e 32 salvate, una song di 70 entrate che suona dalla 65, le snapshot 9 e 16, il tablet e il
  grid, in play.
* E nei gesti: SHIFT + i pad della riga 2 delle viste PROJ (le scale nuove) e SONG (le scene 17-32), SHIFT + la riga 8
  della vista FX (le snapshot 9-16), e sul tablet i valori nuovi di GROOVE, MIDI FX e CHORD.
* La situazione della 0.28 (12 tracce, accordi di 6, lane 7-8) c'era già.

## Come è stato provato

Non ho un FM-1 in mano: la 0.30 è provata nel simulatore (lo stesso codice del firmware, sul computer), con i test e
con l'esploratore.

| la prova | il risultato |
| --- | --- |
| il cuore: progetti, immagini, song, TAPE | 44.562.587 controlli, 0 errori |
| la 0.30 contro la 0.29 vera, presa da git | 40 progetti 0.30 → 0.29 → 0.30 giusti; 40 salvati uguali byte per byte da tutte e due; quelli della 0.29 come erano |
| i motori THEORY | 200.798.646 controlli, 0 errori |
| il simulatore del pannello e del grid | 1584 controlli, 0 errori, con le prove nuove delle scene, delle snapshot, della song, di UNDO e delle TAPE |
| l'editor dei progetti sul Pi | 267 controlli, 0 errori |
| le pagine SAGGA, il bridge del grid, il hub | 94, 326 e 179 controlli, 0 errori |
| la fuzz con AddressSanitizer e UndefinedBehaviorSanitizer | 26 giri, 0 errori |
| l'esploratore, il giro completo | 110.996 gesti da soli in 32 situazioni, 12.794 coppie, 200 sessioni da 60 gesti: 0 errori, niente da guardare |
| il banco, con il simulatore al posto dell'FM-1 | 0 errori; e trova le rotture preparate apposta (i comandi persi, un FM-1 sordo) |
| tredici rotture fatte apposta nel firmware e nell'editor | trovate tutte e tredici |

**Sull'FM-1 vero** la 0.30 non è ancora passata. La provi con il banco, dalla pagina del Pi (porta 8090): **Avvia la
prova** (30 sessioni, circa venticinque minuti) e, nella tendina, **l'FM-1 completo** (35 sessioni, con le cose della
0.28, della 0.29 e della 0.30: mezz'ora abbondante). Se qualcosa non torna, la raccolta si confronta con il
simulatore: `python3 tests/sagga_explore.py --banco raccolta-banco-....json` (`docs/SAGGA-ESPLORATORE.md`).


## Installare

Come sempre: prima il Pi (`sagga-hub-0.30.zip`), poi l'FM-1 (`sagga-0.30.fwsc`). I passi sono in `INSTALLA.md`. Sullo
schermo, dopo l'aggiornamento: `SAGGA SEQ 0.30` per tre secondi.

## Cosa provare per primo

1. **La scena 17**: tocca GLO (PERF), gira PRESETS finché lo schermo dice `PERF SCENE 17`, poi **SEL + nero 1**: la
   scena 17 è salvata. Il nero 1 la richiama.
2. **La snapshot 9**: tieni SAVE, premi il **bianco 10** (si accende), poi SEL + nero 1: la snapshot 9. Lascia tutto,
   cambia qualcosa, e tieni SAVE + nero 1: torna.
3. **Una song lunga**: in PERF tieni HOME e premi i neri a turno: ogni pressione è un'entrata. Sul grid, vista SONG
   (PERF due volte), le pagine con i pad 13 e 14 della riga 4.

## La dimensione

Il firmware cresce di 3.612 byte: 478.124 su 581.564 (la 0.29: 474.512). La RAM fissa sale di 17.120 byte: 84.704
su 98.304 (la 0.29: 67.584). Ci è passata soprattutto la memoria dei dadi (quello che OCT- rimette a posto), per
lasciare il posto grande al progetto: 341.164 su 344.064 byte (la 0.29: 311.308), con le 32 scene, la song da 128, le
16 snapshot, le TAPE doppie e le 32 righe di UNDO. Restano 2.900 byte liberi.
