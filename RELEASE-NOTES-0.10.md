# SAGGA SEQ 0.10 - Note di rilascio

La 0.10 è la 0.9 riletta con un mese di note sul manuale: ventiquattro cose che non andavano, non si capivano o
mancavano, più quello che un sequencer da palco deve avere e la 0.9 non aveva (gli accordi da una nota, le lane che
scivolano, i tool che aspettano la battuta, la band in un colpo). Per farlo il formato del progetto riparte da capo:
la 0.10 scrive e legge **`SGQA`** e non legge i progetti della 0.9 (né il bridge, né l'hub, né il convertitore). Se
vuoi tenere un progetto 0.9, tienilo con un firmware 0.9: la 0.10 non lo converte.

## Il tempo: tutto atterra in battuta

* Cambi la **lunghezza** di una traccia (HOME 1 K2) o il suo passo e poi li rimetti: la traccia non resta spostata,
  suona lo step che il clock indica. Vale per **HALF, DOUBLE, REVERSE, FREEZE, RANDOM** quando li lasci, per la fine
  di un **LOOP** o di un **REPEAT**, e per il **loop fra due step**: la lunghezza che c'era prima è ricordata e **EXIT**
  (FX + nero 11) la rimette, in tempo. (0.9: le tracce proseguivano da dove erano rimaste, e il pattern restava fuori
  fase con la battuta.)
* **PANIC è FX + HOME**: sustain su, All Notes Off e All Sound Off su ogni canale, mandati a ritmo di quello che la USB
  accetta (prima una raffica che si perdeva); premuto di nuovo entro 2 secondi ferma anche il transport. Uno STOP
  normale manda All Notes Off e alza il sustain, e lascia le code dei synth.
* **ECHO ALL** (FX + OCT+): spento, cancella anche le ripetizioni che aspettavano.

## Un genere solo, e la band

* **Un genere per tutta la macchina** (SEQ + PRESETS, la vista BEAT, HOME 8 K3): la libreria, le progressioni
  dell'armonia e le proposte di VIAGGIO vengono tutte da lì. **24 generi**: via BREAKBEAT, TRAP, MINIMAL e LO-FI;
  dentro **UK DRILL**, **HARDCORE**, **PHONK** (half-time, gli 808 che scivolano, il riff di cowbell come ARP) e
  **BAILE FUNK** (il tamborzão in celle 3-3-2, l'atabaque fra i colpi). Drum and bass c'è dalla 0.8 (`DRUM+BASS`),
  con JUNGLE accanto. Ogni genere ha la sua scala dei ruoli per VIAGGIO (prima ne avevano solo cinque).
* **GENRE** (SEQ 7 K4): **FREE** (i generatori ignorano il genere: COOK e i dadi sono quelli nudi), **ON** (lo
  rispettano: è la base), **LIVE** (un cambio di genere ricarica, alla battuta dopo, ogni traccia venuta dalla
  libreria, stessa funzione e stessa variante: la band cambia colore sulla battuta).
* **BAND** (SEQ + SEL + nero 7; grid: SHIFT + pad KIT): tutto il genere in una pressione: KICK SNARE HAT PERC BASS
  CHORD ARP e PROG su otto tracce, ognuna sulla traccia che ha quel **ruolo**, altrimenti sulle otto del banco.
* **Libreria a 16, 32 o 64 step** (SAVE pagina 2 K4): i pattern più corti vengono piastrellati con le loro varianti e
  un fill nell'ultima battuta; i pattern lunghi della libreria entrano interi.
* **Ruolo per traccia** (HOME 4 K2; in VIAGGIO K3): nessuno, KICK, SNARE, HAT, PERC, BASS, CHORD, ARP. **COOK cucina
  per ruolo**: la cassa tiene i battere e prende levare, il rullante ghost e rullate, l'hat apre sul "e" e fa ratchet,
  il basso tiene la tonica sui battere e si muove per quinte e ottave, gli accordi cambiano ritmo e durata,
  l'arpeggio ordine e ottave. BAND e le proposte di VIAGGIO seguono il ruolo.

## Gli strumenti: quando

* **SEQ pagina 7 TOOLS**: K1 densità del RANDOM (era in SEQ 1), **K2 WHEN** (NOW, oppure alla prossima 1, 2, 4, 8, 16
  battute: uno strumento premuto mentre suona aspetta quella battuta, lo schermo dice `CLEAR IN 2 BARS`), **K3 EVERY**
  (OFF, 1 .. 32 battute: l'ultimo strumento usato si ripete ogni tante battute; COOK ogni 4 battute è un'evoluzione
  lenta che senti arrivare), K4 il modo GENRE.
* **Famiglie di ritmo** (SEQ 1 K3): EUCLID (le pulsazioni più sparse possibile: E(5,16) = `x..x..x..x..x...`),
  **TRESILLO** (celle 3-3-2, mezza battuta alla volta), **NUMERIC** (le cifre binarie dell'n-esimo numero primo: un
  ritmo né regolare né casuale). Stesse pulsazioni, un altro ritmo.
* **16 condizioni**: + 1:3, 2:3, 3:3, 1:8, FIRST (solo il primo giro dopo PLAY), **PRE** (solo dopo uno step della
  traccia che ha suonato: con la chance sullo step prima fa una coppia che vive insieme) e **!PRE**.
* **UNDO** torna indietro di più passi; REDO è SEQ + SEL + UNDO.

## Note, accordi, arpeggi

* **La penna**: SEL + K4 sceglie la nota prima. K1 su uno step spento ne cambia la nota (e la penna), la fa sentire in
  anteprima e **non accende lo step**; uno step che accendi prende la penna.
* **TIE** (EDIT + nero 6; grid SHIFT + riga 7 pad 16): la nota dello step tiene fino allo step dopo, legato (la nota
  successiva parte prima che questa finisca).
* **Gate fino a 64 step** anche dal grid (riga 7 di TRACK 3: 1,5, 2 .. 6, 8 .. 16, 20 .. 64; con SHIFT 17 .. 32).
* **CHORD** (HOME 4 K3; ARP pagina 2 K1): una nota scritta diventa un accordo **fino a sei note**, da **32 forme**:
  OCTAVE, POWER, 5-8, MAJOR, MINOR, DIM, AUG, SUS2, SUS4, MAJ6, MIN6, DOM7, MIN7, MAJ7, MINMAJ7, DIM7, M7B5, 7SUS4,
  ADD9, MINADD9, DOM9, MIN9, MAJ9, 9SUS4, 6/9, MIN6/9, MIN11, DOM13, SHELL7, MINSHELL, 1-3-5-8: gli accordi su cui
  vivono i generi della macchina (m7, m9 e 9sus4 di house e garage, gli stab techno, il maj7 dell'amapiano, l'add9
  della trance ...). Su una traccia IN KEY il modo **KEY** (ARP pagina 2 K2) decide come la forma incontra la scala:
  **DIATONIC** la costruisce sulla scala (la qualità segue il grado: MAJOR su Re in Do maggiore dà Re minore),
  **FREE** tiene la forma esatta (la qualità che hai chiesto, anche con note fuori chiave: Re maggiore in Do maggiore),
  **STRICT** tiene la forma e **spegne** le note che cadono fuori chiave (Re maggiore in Do maggiore suona Re e La).
  Una traccia FREE suona sempre la forma esatta. Uno step scritto a mano tiene quattro note; una forma ne suona sei,
  e arpeggio, strum e voicing lavorano su tutte e sei.
* **ARP ha due pagine**: pagina 1 modo, ottave, **RATE** (ROLL: l'accordo dentro lo step, come la 0.9; 1-4 note per
  step: l'arpeggio prosegue sugli step vuoti finché dura il gate dell'accordo), **RUN** (OFF; RETRIG: un accordo
  nuovo riparte dalla prima nota; HOLD: prosegue fino all'accordo dopo; HOLD+RT); pagina 2 (ARP + OCT+) CHORD: la
  forma, KEY, voicing, strum.
* **Transpose in chiave** (HOME 1 K4): su una traccia IN KEY conta **gradi della scala** (−24 .. +24), su una FREE
  semitoni. **OCTAVE** per traccia (HOME 2 K3; dal vivo: GLO tenuto + OCT− / OCT+). PERF K3 TRANSPOSE sposta la
  tonalità stessa (radice e spostamento insieme), così tutto quello che è in chiave si muove insieme.
* **Sedici tonalità** (HOME 3: K1 lo **SLOT** 1-16, K2 radice, K3 scala, K4 spostamento ±24). Una traccia suona nello
  slot corrente, oppure è **fissata** a uno slot (HOME 4 K4). Scene e snapshot riportano il loro slot. Le righe
  radice / scala / spostamento della vista PROJ del grid modificano lo slot corrente.
* **Progressioni tue** (SEQ pagina 8: quale delle 4, l'accordo 1-8, il suo grado i .. vii o `--` per finire lì, il
  colore): l'ARMONIA (SEQ 4 K2) suona 1-6 del genere oppure USER 1-4; VIAGGIO le raggiunge con PRESETS e dalla riga 7
  del grid.
* **FOLLOW** spiegato: scrivi la traccia **sulla tonica** (come se l'accordo fosse sempre il primo grado) e lei suona
  spostata sull'accordo che la progressione dice in quel momento, con il suo colore. HOME 2 K4, o SEQ 4 K4.

## Le CC lane

* **Sei lane, una per pagina** (ENV + OCT− / OCT+): K1 il valore bloccato sullo step (parte dalla base, o da 64),
  K2 il CC (SEL + K2 il MSB dell'NRPN), K3 la base, K4 il modo: NORMAL, **SLIDE** (il valore scivola da un lock al
  successivo, anche sugli step che tacciono), **TRIGLESS** (un lock viene mandato anche su uno step spento), **NRPN**
  (99 MSB, 98 LSB = il numero della lane, 6 il valore).
* **Registrare una lane**: con REC acceso, ENV tenuto e K1 che gira scrivono la manopola sugli step mentre passano.
* **CC LEAD** (SAVE pagina 2 K1): i lock escono fino a 30 ms prima delle note (per i synth che vogliono il filtro
  pronto prima della nota).
* **LEARN** (ENV + REC): prende il valore arrivato come base e, se il canale ha un **DEVICE** (SAVE pagina 2 K3:
  GENERIC, ELEKTRON), dice il nome del CC (`FILTER FREQ` invece di `CC 74`).

## Le macro

* **Si salvano con il progetto.** FX + OCT− le riporta a 0 (e con loro il MASTER se è su FILTER: lo 0.9 non lo
  faceva, e sembrava che il reset non funzionasse). **FX + ARP due volte: BAKE**: INTENSITY entra nelle velocity,
  GATE nei gate, SWING nello swing delle tracce, FILTER nella base della lane 1; poi le macro sono 0 e la musica è la
  stessa.

## La song

* **SONG TEMPO** (SAVE pagina 2 K2): ogni voce della song ricorda il BPM a cui l'hai aggiunta e lo rimette.

## VIAGGIO

* Funziona con **tutti e 24 i generi**; la scala dei ruoli è quella del genere della libreria.
* **Scegli tu** ruolo (K3) e canale (K4) di ogni traccia in modo VIAGGIO; sul grid SHIFT + pad della traccia cambia il
  ruolo. Le proposte seguono il ruolo; una traccia senza ruolo prende il primo libero della scala.
* **Le proposte**: un tap su una traccia vuota ne scrive una (`T1 KICK P2 SEL+KEY: IN`), un tap su una PROPOSTA la
  seleziona e dice cosa ha, tenuto tira i dadi, ALG le sfoglia (`T1 KICK P3 (2/3)`): fino a sette per traccia,
  ognuna con le sue impostazioni; piene, la più vecchia se ne va. (0.9: lo sfoglio non funzionava.)
* **MOVES AT** (K2): al confine della frase, **a ogni battuta** o **a ogni quarto**: decidi tu quando succedono le
  cose; la frase conta ancora per FILL, RISER, DROP e la scia.
* Un cambio di **GENERE** mentre suona aspetta il confine; RISER non inizia mai a metà.

## Il grid

* STEP: SHIFT + riga 6 le 16 condizioni; SHIFT + riga 7 pad 15 PLAIN, pad 16 TIE. TRACK 3 riga 7: i gate lunghi fino a
  64 step. VIAGGIO riga 2 con SHIFT: il ruolo della traccia; riga 7 le progressioni 1-10 (le tue in viola). BEAT: i 24
  generi in due pagine. SHIFT + KIT: BAND.

## Il formato, il Pi, gli strumenti

* `SGQA`: 16 tonalità, dispositivi per canale, 4 progressioni, tracce da 80 byte (lane, ruolo, accordo, ottava, slot,
  EXPO, TAPE), scene con lo slot, song con il tempo, macro, tape. Un progetto occupa circa 170 KB di RAM dell'FM-1
  (nel pool restano circa 26 KB liberi).
* Il bridge, l'hub (pagina 8090) e `sagga_sgqmid` accettano solo `SGQA`. L'hub ricompila il convertitore
  dall'installer (`install_hub.sh`), che va rilanciato dopo l'aggiornamento.
* `tools/make_release.sh X.Y` fa i due zip del rilascio (sorgente e Pi).
* L'identità del pacchetto: `FM-1_960` (0.9 era `FM-1_959`; `build.sh --release 0.10`).

## Dalla 0.10 pre-rilascio (già nel ramo)

* **EXPO** (SEQ 5-6): il ritmo di una traccia come curva esponenziale (RAMP, BOUNCE, SETTLE), con VEL GRACE e gli step
  PLAIN. **REC registra la durata**. **DELAY** per traccia (HOME 7 K1). **BEND e AFTERTOUCH** come lane o LFO.
  **CHAIN** (HOME 7 K2). **Tracce TAPE** (HOME 4 K1: il quarto modo) con TAPE BARS e TAPE QUANT (HOME 7 K3, K4) e il
  piano roll sul Pi; i progetti si scaricano come .mid e un .mid diventa tracce TAPE.

## Limiti

* Una lane SLIDE scivola uno step alla volta (un valore per step della traccia): va bene per un filtro, non per un
  pitch bend.
* Una nota TAPE suona nota, velocity e durata: niente condizioni, ratchet, lane o EXPO sul nastro.
* Il DELAY non si applica alle campate EXPO.
* La pagina del Pi modifica le tracce TAPE; le tracce step si modificano dal grid o dal pannello.

## Test

Simulatore 660 controlli (96 nuovi per la 0.10: atterraggi in tempo, PANIC, macro e BAKE, penna, TIE, accordi (32 forme, i tre modi KEY, sei voci), ARP
RATE / HOLD, transpose in chiave, ottava, condizioni, le sei lane in tutti i modi, registrazione, CC LEAD, LEARN con
i nomi, WHEN, EVERY, BAND, libreria a 32, GENRE LIVE / ON, COOK per ruolo, le famiglie, la progressione utente, gli
slot di tonalità, lo snapshot con lo slot, ECHO ALL, VIAGGIO con ruoli, canali, sfoglio, MOVES AT, tutti i generi),
core 697 mila, bridge 246, hub 46, convertitore 14, piano roll in Chromium, fuzz 24 run, test hardware simulato:
tutto verde al momento del rilascio. Sull'FM-1 vero la 0.10 va provata con `sagga-hwtest` subito dopo
l'installazione.
