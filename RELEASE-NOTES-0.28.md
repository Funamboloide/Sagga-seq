# SAGGA SEQ 0.28 - Note di rilascio

Mi avevi detto: "non mi servono più di 12 tracce". E delle cose da fare con lo spazio liberato: "il punto 2 è
succoso". **Eccolo**: le tracce sono dodici, e con la memoria che lasciano un passo tiene **accordi di sei note** e ogni
traccia ha **otto lane CC**.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.28.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.28.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due**: anche il Pi cambia (l'editor e le pagine SAGGA vedono dodici tracce, sei note, otto
lane).

## Le tre cose

| cosa | fino alla 0.27 | adesso |
| --- | --- | --- |
| **le tracce** | 16 | **12** (i canali MIDI restano 16) |
| **le note di un passo** | fino a 4 | **fino a 6** |
| **le lane CC di una traccia** | 6 | **8** |

## 1. Dodici tracce

* Le tracce sono 12. I **canali MIDI restano 16**: ogni traccia può andare su qualunque canale, come prima.
* **HOME + bianco 1-12** sceglie la traccia. I bianchi **13-16 per ora non fanno niente**: decidiamo poi cosa metterci.
* I neri, senza niente tenuto: **1-8** le tracce della banca, **9** l'altra banca. Le banche sono **1-8 e 9-12**: la
  seconda ne ha quattro, e lì i neri 5-8 non fanno niente.
* **GLO + bianco 1-12**: i mute.
* **DICE ALL** tira le otto tracce dalla parte di quella scelta: 1-8, oppure 5-12.
* **Il grid**: i pad e i bottoni delle tracce 13-16 sono spenti. Nella banca 9-12 le viste PERF, DRUM ed EUCLID hanno
  quattro righe.
* **Sul Pi**: SAGGA Live, Motori, Mutes e BeatStep mostrano dodici tracce. Un comando per le tracce 13-16 che arriva da
  un altro controller non fa niente.

## 2. Accordi di sei note

* Un passo tiene fino a **6 note**.
* **SEL + tasti**: premi i tasti uno dopo l'altro, vicini (entro mezzo secondo): fino a sei note. Al settimo lo schermo
  dice `CHORD FULL (6 NOTES)`.
* Anche **MIDI REC** (da una tastiera), **il grid** (SHIFT + i pad delle note) e **l'editor del Pi** scrivono sei note.
* **EDIT + SEL + K1-K4** cambiano le note 1-4, come prima. Le note 5 e 6 le vedi sulla riga, per esempio
  `EDIT+SEL STEP 1  5 G4 6 A4`. Per cambiarle, suona di nuovo l'accordo, o usa l'editor.
* L'arpeggio, lo strum e il voicing lavorano su tutte e sei. Da un passo suonano al massimo sei note, anche con un
  accordo (CHORD) sopra.

## 3. Otto lane CC

* Ogni traccia ha **8 lane** (prima 6). Sulla pagina **ENV**, OCT+ va fino a `LANE 8/8`.
* In un progetto nuovo: **lane 7 = CC 73** (l'attacco), **lane 8 = CC 72** (il rilascio). Si cambiano come le altre
  (ENV K2, o il LEARN).
* Le scene, gli snapshot, il grid (la vista CC: pad 1-8) e il LEARN tengono tutte e otto. Al nono CC il LEARN dice
  `NO FREE LANE FOR CC ...`.
* Le manopole LANE della pagina SAGGA Mod sul Pi restano sulle lane 1-6.

## 4. I progetti

* **I progetti di prima si aprono**, con le loro prime dodici tracce. Le tracce 13-16 restano fuori (mi avevi detto
  che non ne hai). Un LFO, un MOD o un TRIG che puntava su una di quelle si ferma.
* **Tornare alla 0.27** si può: la 0.27 apre i progetti della 0.28, ma senza le note 5-6 e le lane 7-8.
* Un **file MIDI** caricato sul Pi: i canali 1-12 diventano le tracce 1-12; le note dei canali 13-16 restano fuori.

## Come è stato provato

| la prova | quanto |
| --- | --- |
| le prove nuove, delle tre cose | 8 controlli nel simulatore (il pannello: le banche, le sei note, le lane 7 e 8, e tutto dopo uno spegnimento), più quelle del cuore, dell'editor del Pi, del convertitore MIDI e delle pagine SAGGA: 0 errori |
| la 0.27 vera (presa da git) con i progetti della 0.28, e il contrario | 60 progetti 0.28 → 0.27 → 0.28 uguali; 20 progetti della 0.27 con tutte e sedici le tracce: le prime dodici come erano |
| 10 errori messi apposta nelle parti nuove, uno alla volta | le prove li trovano tutti e 10 |
| il cuore del sequencer | 30.968.676 controlli, 0 errori |
| i motori THEORY | 215.628.289 controlli, 0 errori |
| il simulatore (il firmware vero che gira sul computer) | XXX_SIM controlli, 0 errori |
| l'esploratore: ogni gesto del pannello, in 30 situazioni (una nuova: la traccia 12, sei note, le lane 7 e 8) | 102.073 gesti da soli, 11.995 coppie di gesti, 200 sessioni a caso: 0 errori (al primo giro una coppia segnata: il genere delle MOSSE che arriva prima perché ALG porta le mosse alla battuta; è il firmware come deve essere) |
| l'editor del Pi | 265 controlli, 0 errori |
| il bridge del grid, la pagina del Pi, le pagine SAGGA | 325 + 176 + 83 controlli, 0 errori |
| gli errori di memoria (gesti a caso, con i rilevatori accesi) | 26 giri: al primo, **un errore della 0.28 stessa** (sotto); corretto, 0 errori; anche tutte le prove del simulatore con i rilevatori: 0 errori |

**L'errore trovato dai rilevatori**: in HOME e in PERF la striscia in fondo allo schermo ha sedici celle, e la 0.28
disegnava le celle 13-16 come se fossero tracce, leggendo oltre le dodici. Sul simulatore senza rilevatori non si
vedeva niente. Adesso le celle 13-16 sono spente. Anche i bottoni delle tracce 13-16 sul grid (banca 9-12) sono spenti.
E un errore del Pi, trovato scrivendo le prove: un file MIDI con note sui canali 13-16 avrebbe scritto oltre le dodici
tracce. Adesso quelle note restano fuori.

**Non ho un FM-1 in mano**: tutto questo è provato sul simulatore, non sullo strumento vero.

## Installare

Come sempre: prima il Pi (`sagga-hub-0.28.zip`), poi l'FM-1 (`sagga-0.28.fwsc`). I passi sono in `INSTALLA.md`.
Sullo schermo, dopo l'aggiornamento: `SAGGA SEQ 0.28` per tre secondi.

## Cosa provare per primo

1. **Sei note**: tieni SEL, premi sei tasti uno dopo l'altro (veloce), lascia. PLAY: un accordo di sei note.
2. **Le lane 7 e 8**: ENV, OCT+ fino a `LANE 7/8`, gira K1 sul passo: sul synth si muove il CC 73 (l'attacco), su quel
   passo.
3. **La banca 9-12**: nero 9 (l'altra banca), poi i neri 1-4: le tracce 9-12.
4. **Un progetto vecchio**: caricalo (SAVE + PRESETS, lo slot) e guarda che le prime dodici tracce siano come prima.

## Da sapere

* I bianchi 13-16 di HOME sono liberi: quando vuoi, decidiamo cosa metterci.
* Le note 5 e 6 non hanno una manopola: le scrivi suonando (SEL + tasti, MIDI REC, il grid) o dall'editor.
* Nella pagina SAGGA Mod mancano le lane 7 e 8 (le manopole sono sei).

## La dimensione

XXX_DIMENSIONE
