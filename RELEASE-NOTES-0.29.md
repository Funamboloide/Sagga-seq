# SAGGA SEQ 0.29 - Note di rilascio

Mi avevi detto: "ci sono dei generi che non hanno senso nella loro specificità o vaghezza", e cosa farne: l'amapiano
dentro il reggaeton, il bassline fra UK garage e i generi bass, il meglio del grime nel dubstep, via l'afro house (con
le sue percussioni in gqom e batida), e un genere nuovo, il balani. Poi, con lo spazio liberato: "8 progressioni e
THEORY a mano" e "Più effetti, accordi, scale". **Eccoli**: i generi sono **22**, c'è il **BALANI** con il suo
**BALAFON**, ogni genere ha **otto progressioni**, REGGAETON e BALANI hanno le regole THEORY **scritte a mano**, e ci
sono **due effetti MIDI, cinque scale, tre groove e quattro forme d'accordo** in più.

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.29.fwsc` |
| il Pi: le pagine dei pattern e delle progressioni, l'editor, le pagine SAGGA, il bridge del grid | `sagga-hub-0.29.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due, insieme**: l'FM-1 0.28 ha 25 generi, il Pi 0.29 ne mostra 22, e i numeri non
tornerebbero.

## 1. I generi: da 25 a 22

| il genere di prima | dove è andato | cosa ha portato |
| --- | --- | --- |
| AMAPIANO | REGGAETON | il log drum, gli shaker in sedicesimi, i rim, gli accordi di settima del piano. Il tempo del REGGAETON adesso è **90-112** |
| BASSLINE | UK GARAGE | i bassi che saltano d'ottava, il sub, gli stab d'organo, la cassa in quattro dello speed garage |
| GRIME | DUBSTEP | i lead a onda quadra, gli stab d'archi, le casse spezzate, i bassi sul secondo grado abbassato |
| AFRO HOUSE | GQOM e BATIDA | le congas a domanda e risposta, gli shaker, i tom, i rim, le percussioni |

* **BALANI** è nuovo: la musica del balafon delle feste di strada di Bamako, veloce (**160-180 BPM**). La cassa in
  quattro, il clap sul 2 e sul 4, il 3-3-2 del djembe sulla conga e sulla percussione, lo shaker in sedicesimi, i tom
  che rullano, le grida dell'MC e il **BALAFON**.
* I pattern dei generi tolti stanno **dopo** quelli del genere che li ha presi: la prima variazione resta la più tipica
  del genere, e COOK ci arriva camminando.
* L'ordine: TECHNO, HARDTECHNO, DUB TECHNO, HOUSE, UK GARAGE, UK FUNKY, DUBSTEP, JUNGLE, REGGAETON, BATIDA, GQOM,
  EXPERIMENT, ELECTRO, DRUM+BASS, BALANI, FOOTWORK, TRANCE, UK DRILL, HARDCORE, PHONK, BAILE FUNK, MERENGUE. Sul grid la
  vista BEAT ha di nuovo due pagine di generi (12 + 10).

## 2. I progetti di prima

* **Si aprono come erano**, con ogni genere dove è andato: GRIME come DUBSTEP, BASSLINE come UK GARAGE, AFRO HOUSE come
  GQOM, AMAPIANO come REGGAETON. Vale dovunque è scritto un genere: quello del progetto, dell'armonia, del VIAGGIO, il
  pattern di una traccia, un pattern dei motori, uno snapshot.
* **Sul Pi**, i pattern e le progressioni che **tu** avevi salvato in quei quattro generi passano in fondo al genere
  che li ha presi, la prima volta che il hub parte. Il file vecchio resta com'era, non si cancella niente.
* **Se torni alla 0.28**, apre i progetti della 0.29: BALANI come AFRO HOUSE, il BALAFON come un LEAD, PROG 7 e 8 come
  PROG 1, senza ROLL e ACCENT; le scale, i groove e le forme nuove tornano a quelle di partenza. Se poi la 0.28 lo
  salva di nuovo, la 0.29 lo riapre con quello che la 0.28 ha tenuto (il BALANI diventa GQOM).

## 3. Il BALAFON

* È una parte (e un ruolo) a sé: una melodia **battuta**, note corte, dal Do centrale. Con l'armonia segue gli accordi
  come una melodia, come un LEAD o un VOX.
* Nella band del BALANI sta dove c'era il LEAD.
* Con THEORY suona il suo **ostinato**: sedicesimi, le due mani a turno, sulla pentatonica; oppure le sue figure sui
  tempi. Mai una nota tenuta.

## 4. Otto progressioni per genere

* Le sei di prima restano dove erano (un progetto tiene la sua progressione per numero), più **due nuove**: quelle del
  bassline in UK GARAGE, del grime in DUBSTEP, dell'amapiano in REGGAETON, dell'afro house in GQOM e BATIDA, del genere
  stesso negli altri.
* **ARP pagina 3, K2** (l'armonia): PROG 1-8, USER 1-4, DICE/PI.
* **Il grid**, vista VIAGGIO, riga 7: pad 1-8 le progressioni del genere, 9-12 le tue, 13 DICE/PI, 14-16 l'accordo che
  suona, a turno (bianco: il primo della progressione). La riga 3 della vista BEAT resta su PROG 1-6.
* **SAGGA Mod**: PROGRESSION va da PROG 1 a PROG 8, poi USER 1-4 e DICE/PI.

## 5. THEORY: REGGAETON e BALANI scritti a mano

Prima le loro regole erano contate dalla libreria. Adesso sono scritte a mano, come quelle di TECHNO, HOUSE, DUBSTEP e
DRUM+BASS.

* **REGGAETON**: il **dembow** a ogni energia - la cassa sui quattro tempi, il rullante su `...x..x....x..x.`. A
  energia bassa resta il dembow con l'ossatura del resto; il resto entra con l'energia (a 100 hat, shaker, rim, congas
  e timbale hanno più del doppio dei colpi che a 0). Il log drum scivola fra le note, il basso e il lead vanno in
  3+3+2, quattro accordi, uno a battuta.
* **BALANI**: il clap sul 2 e sul 4, il 3-3-2 del djembe, il balafon in sedicesimi sulla pentatonica, uno o due
  accordi.
* A energia 50 somigliano alla libreria: delle loro 21 parti, **19** cadono dove cade la libreria. Le due lontane sono
  gli shaker: nella libreria suonano quasi tutti i sedicesimi, e lì il confronto dice poco.
* **Gli altri generi**: i 17 che non sono cambiati (e FREE) fanno quello che facevano, colpo per colpo. UK GARAGE,
  BATIDA e GQOM hanno regole contate nuove, perché la loro libreria è cambiata. Le regole contate imparano dalle prime
  sei progressioni: le due nuove restano fuori, così i generi di prima suonano come prima.
* Tutte le regole, in italiano: `docs/TEORIA.md` (quelle a mano) e `docs/TEORIA-GENERI.md` (le 16 contate).

## 6. Più cose da suonare

| cosa | fino alla 0.28 | adesso |
| --- | --- | --- |
| **gli effetti MIDI** | 9 | **11**: ROLL e ACCENT |
| **le scale** | 16 | **21** |
| **i groove** | 10 | **13** |
| **le forme d'accordo** | 32 | **36** |

* **ROLL**: ogni nota diventa **2-6 colpi** dentro il suo passo, con la velocity uguale, che sale o che scende, e una
  probabilità (K2 i colpi, K3 la velocity, K4 quanto spesso). Gli hat della trap.
* **ACCENT**: ogni **2-8 passi** (K3), da un passo tuo (K4), più forte (K2 fino a +60; sotto lo 0, più piano). Fa il
  tre-contro-quattro. Nell'ORDER della catena ACCENT viene dopo VEL CURVE, ROLL prima di ECHO.
* Si mettono nella catena come gli altri: HOME pagina 6, K1 sull'effetto, **SEQ + bianco 6**. Sul grid: SHIFT + i pad
  7 e 8 della seconda riga, nella vista TRACK 3.
* **Le scale**: HUNGARIAN MINOR, DOUBLE HARMONIC, LYDIAN DOMINANT, MAJOR BLUES, IN SEN. Sul grid, vista PROJ: SHIFT +
  riga 2, pad 1-5.
* **I groove**: MALI (i sedicesimi del djembe, che pendono verso tre per tempo), DEMBOW (i due colpi del rullante
  sull'ultimo sedicesimo, in ritardo e forti), BROKEN (il broken beat: la "e" in anticipo, l'ultimo sedicesimo in
  ritardo).
* **Le forme d'accordo**: 7#9, 7B9, MAJ7#11, QUARTAL. Per il CHORD di una traccia e nelle tue progressioni.
* **Sul Pi**: SAGGA Live ha i groove, le forme e gli effetti nuovi; la BeatStep arriva fin lì con le sue manopole;
  l'editor dei progetti ha ROLL e ACCENT nella catena.

## Due errori corretti

* **La parte di BEAT oltre la sedicesima della lista** (un LEAD, un VOX, un LOG DRUM ...): dopo uno spegnimento tornava
  KICK. Adesso resta quella.
* **La progressione dei dadi nel VIAGGIO** (DICE/PI: il pad 13 della riga 7 del grid, o PRESETS): lo schermo le dava il
  nome della tua prima progressione (`USER PROG ...`). Adesso dice `DICE/PI` con i suoi accordi. C'era da quando
  esiste lo slot del Pi.

## Come è stato provato

| la prova | quanto |
| --- | --- |
| le prove nuove | i progetti fra 0.28 e 0.29 nei due versi (la 0.28 vera, presa dalla storia del codice), un progetto della 0.28 in ognuno dei suoi 25 generi e con le sue 11 progressioni; il balafon, le otto progressioni, ROLL e ACCENT, le scale, i groove e le forme salvati e riaperti; le regole a mano di REGGAETON e BALANI su 150 semi a ogni energia; la riga 7 del grid; i nomi nuovi sulle pagine del Pi: 0 errori |
| i progetti fra le versioni | 40 progetti della 0.29 aperti dalla 0.28 e ripresi, 60 + 20 con la 0.27: 0 diversi |
| 13 errori rimessi apposta, uno alla volta (AMAPIANO aperto come BATIDA, un progetto con il BALANI salvato senza il pezzo nuovo, il 7B9 con la nona giusta, IN SEN con la sesta maggiore, ROLL al posto sbagliato nella catena di un progetto 0.28, i colpi di ROLL troppo larghi, ACCENT un passo in ritardo, il rullante del REGGAETON senza il dembow, il pad 13 chiamato USER 1, il pad 13 che non fa niente, SAGGA Mod senza PROG 8, il Pi che lascia le tue progressioni nei generi tolti, la catena dell'editor a dieci effetti) | le prove li trovano tutti e 13 (l'ultimo dopo una prova nuova: prima scappava) |
| il cuore del sequencer | 44.556.406 controlli, 0 errori |
| i motori THEORY | 200.798.646 controlli (150 semi per ognuno dei 23 stili, in 4/4 e in altri 19 metri), 0 errori |
| il simulatore (il firmware vero che gira sul computer) | 1.551 controlli, 0 errori; 26 giri di gesti a caso con i rilevatori degli errori di memoria: 0 errori |
| l'esploratore: ogni gesto del pannello, del grid e della pagina, in 30 situazioni (fra queste una BALANI ferma e una GQOM con tablet e grid) | 102.082 gesti da soli, 11.995 coppie di gesti, 200 sessioni a caso: 0 errori |
| l'editor del Pi, il bridge del grid, la pagina del Pi, le pagine SAGGA, il banco, il custode delle celle | 266 + 326 + 179 + 94 + 76 + 49 controlli, 0 errori |

**Non ho un FM-1 in mano**: tutto questo è provato sul simulatore, non sullo strumento vero.

## Installare

Come sempre: prima il Pi (`sagga-hub-0.29.zip`), poi l'FM-1 (`sagga-0.29.fwsc`). I passi sono in `INSTALLA.md`. Sullo
schermo, dopo l'aggiornamento: `SAGGA SEQ 0.29` per tre secondi.

## Cosa provare per primo

1. **Il BALANI**: tieni SEQ e gira PRESETS fino a `BALANI`. Poi tieni SEQ e il **nero 7** per mezzo secondo (BAND): la
   band intera, con il balafon.
2. **ROLL su un hat**: sulla traccia dell'hat tieni HOME, OCT+ fino alla pagina 6 (MIDI FX), K1 su `ROLL`, poi **SEQ +
   bianco 6**. K2 i colpi, K3 `RISING`.
3. **Il dembow che si riempie**: SEQ pagina 8, K1 su `THEORY`; il genere REGGAETON; BAND. Poi GLO pagina 3 (le
   MOSSE), K1: l'energia. Da 0 a 100 la batteria si riempie, e il rullante del dembow non si muove.

## La prossima

Come avevi scelto per la RAM: **32 scene e song da 128**, **16 snapshot**, **TAPE doppia e UNDO a 32**.
