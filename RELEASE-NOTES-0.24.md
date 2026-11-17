# SAGGA SEQ 0.24 - Note di rilascio

Mi avevi chiesto se la questione della lunghezza dei pattern si poteva risolvere, e se aveva senso. **Sì, tutte e sei
le cose che hai scritto sono fattibili, e le ho fatte.** Guardando il codice ho anche trovato due errori veri, vecchi
dalla 0.11, che sono esattamente quello che sentivi ("il tempo si incasina").

L'idea della 0.24 in una riga: **la lunghezza è della traccia, e la decidi solo tu. I pattern si adattano a lei.**

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.24.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.24.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati tutti e due. I progetti di prima si aprono come sono.

## Le tue domande, una per una

| cosa chiedevi | la risposta |
| --- | --- |
| cambiare lunghezza durante un live senza che il tempo si incasini | fatto: il cambio aspetta la battuta e la traccia atterra sullo step giusto **già sulla battuta** (prima no: vedi sotto) |
| allungo di 3 step (polimetria), poi arrivo a 32: rientra nei binari? | **adesso sì, sempre.** Prima no: restava sfalsata di 3 step per sempre. Era un errore |
| se allungo e non ho scritto niente oltre, l'FM-1 copia il pattern da solo | fatto. Le chiamo **copie** |
| ma devo poter aggiungere anche step silenziosi | fatto come dicevi tu: scrivi solo l'ultimo step (il 64) e la traccia allungata resta in silenzio fino a lì |
| carico un pattern da 16 su una traccia da 32: deve restare 32 | fatto: resta 32, il pattern c'è due volte. Su una traccia da 17: i 16 step e poi di nuovo il primo |
| allungare tutte le tracce insieme, nelle mosse | fatto: **LONGER** e **SHORTER** |
| dice, cook, turing, motori: ragionano in 16 o capiscono la lunghezza? | dipende dal motore: c'è la tabella più sotto. RANDOM, i dadi e COOK adesso fanno una **frase** lunga quanto la traccia, non il doppio della stessa battuta |

## Cosa non andava (i due errori)

Ho rifatto nel simulatore il tuo caso: una melodia di 16 step che suona, la porti a 19 (aspetta la battuta), poi a 32.

**Errore 1: lo step sulla battuta era quello sbagliato.** Quando la lunghezza cambiava sulla battuta, la traccia veniva
rimessa a posto un attimo *dopo*: lo step che suonava proprio sulla battuta era ancora quello del giro vecchio. Nel
tuo caso, sulla battuta in cui arrivava il 32 suonava lo step 11.

**Errore 2: il 32 non era il pattern due volte.** Quando allungavi, l'FM-1 ricopiava "la lunghezza che c'era quando hai
cominciato a girare la manopola". Passando da 19, ricopiava i 19: la seconda battuta diventava 1 2 3 e poi 1 2 3 ...
13. Tre step fuori, per sempre: non rientrava più.

| | prima (0.23.2) | adesso (0.24) |
| --- | --- | --- |
| battuta 2 e 3, a 19 step | la polimetria giusta | uguale: la polimetria giusta |
| lo step sulla battuta in cui arriva il 32 | lo step 11 | lo step 1 |
| le battute dopo, a 32 step | 1...16, poi 1 2 3 1 2 ... 13 (sfalsata) | 1...16, 1...16: di nuovo sui binari |

Lo schermo adesso te lo dice: `LENGTH 32: THE 16 STEPS REPEAT`.

## Le copie

Quando una traccia è più lunga del suo pattern, negli step in più il pattern **gira di nuovo**. Quegli step sono le sue
**copie**.

* **Seguono il pattern.** Cambi uno step del pattern (da un tasto, dal grid, dal tablet, con un tool) e la sua copia
  cambia con lui, subito.
* **Finché non ne tocchi una.** Appena scrivi su una copia (la accendi, la spegni, le cambi nota), tutte le copie
  diventano **step tuoi**: da lì in poi il pattern è lungo quanto la traccia e ogni step è indipendente. Lo schermo
  dice `THE COPIES ARE YOUR STEPS NOW`.
* **Si vedono.** Sul grid le copie che suonano hanno un colore loro: un **verde-azzurro spento**. Gli step tuoi restano
  verdi come sempre.
* **Valgono per tutti e 8 i pattern della traccia**, non solo per quello che sta suonando (prima solo quello).
* **Contano sempre dal pattern.** 16, poi 19, poi 23, poi 32, in qualunque ordine: a 32 sono sempre i 16 step due volte.

## Accorciare e tornare indietro

Accorci una traccia da 16 a 12 per fare polimetria. Il pattern **resta intero**: i 4 step che non suonano aspettano
dopo la fine del loop (sul grid li vedi blu, come sempre).

* Torni a 16: riavrai il pattern **com'era**, anche se il suo ultimo quarto era silenzio. Prima no: in quel silenzio
  l'FM-1 ricopiava i primi 4 step, e il pattern tornava diverso.
* Da 12 vai a 32: è il pattern da 16 **due volte**. Di nuovo sui binari.

## Il silenzio, quando lo vuoi

Quello che scrivi **dopo** la fine del loop fa parte del pattern. È la tua idea, e funziona così:

* **Scrivi solo lo step 64** mentre la traccia gira sui suoi 16. Poi allunga: a 40, a 64, dove vuoi. Niente viene
  copiato, la traccia resta in silenzio fino allo step 64.
* **Arrivato a 64, spegni lo step 64** prima che il cursore ci arrivi: hai 64 step, 16 di note e 48 di silenzio.
* **Scrivi una seconda battuta** mentre la prima gira (per esempio dal grid), poi porta la traccia a 64: sono le tue
  **due battute, due volte**. Il pattern adesso è di 32 step, e sono quei 32 che girano.

## Caricare un pattern non cambia più la lunghezza

BEAT, KIT, BAND, i dadi, le proposte del viaggio, GENRE LIVE, i pattern del Pi, i motori THEORY: **nessuno tocca più la
lunghezza della traccia**. Prima ogni pattern caricato la riportava a 16.

| la traccia è lunga | carichi un pattern da 16 | cosa suona |
| --- | --- | --- |
| 32 | resta 32 | il pattern due volte (la seconda sono copie) |
| 17 | resta 17 | i 16 step, poi di nuovo il primo |
| 64 | resta 64 | il pattern quattro volte |
| 12 | resta 12 | i primi 12 step; gli altri 4 aspettano, e tornano se allunghi |

**SAVE pagina 2, K4** si chiamava LIBRARY LEN (16 / 32 / 64). Adesso è **LONG PATTERNS** e ha due posizioni:

* **COPY** (è così da nuovo): un pattern di una battuta, su una traccia più lunga, si ripete uguale. È quello che
  chiedevi.
* **PHRASE**: invece di ripetersi, nell'ultima battuta arriva la variazione successiva con il fill del genere. È la
  "forma lunga" che c'era dalla 0.10.

I pattern che la libreria ha già scritti su due o quattro battute arrivano interi in tutti e due i modi, se la traccia
è lunga abbastanza.

Un'eccezione sola: un pattern che non sta in una battuta (il bembé, 12 step; un pattern del Pi da 12 o da 24) porta
la traccia alla sua lunghezza. Ripeterlo dentro 16 step lo romperebbe.

## Allungare e accorciare tutte le tracce: LONGER e SHORTER

Sono due mosse nuove, sulle **MOSSE** (SEL + GLO):

* **SEL + nero 6** (il tasto di DOUBLE): **LONGER**. Ogni traccia diventa lunga il doppio.
* **SEL + nero 5** (il tasto di HALF): **SHORTER**. Ogni traccia diventa lunga la metà.

Senza SEL quei due tasti restano HALF e DOUBLE (la velocità). Sul grid, nella vista VIAGGIO: **SHIFT** + gli stessi
pad.

* Mentre suoni vanno in coda come le altre mosse e arrivano a fine frase (o con NOW alla battuta). Da fermo: subito.
* **SHORTER dopo LONGER ti ridà tutto com'era**, step per step. Vale anche al contrario.
* Una traccia che non può (il doppio passerebbe i 64 step; un numero dispari di step non ha metà) **resta com'è**, e
  lo schermo le conta: `LONGER: 12 TRACKS TWICE AS LONG, 4 STAY`.
* Due tracce da 12 e da 16 diventano 24 e 32: la polimetria fra loro resta la stessa.

## I motori e la lunghezza

Era la tua ultima domanda. Ecco cosa fa ognuno su una traccia da 32 o da 64 step.

| il motore | cosa fa su una traccia lunga | cambiato nella 0.24? |
| --- | --- | --- |
| **RANDOM** | una battuta a caso, poi la sua **frase**: su due battute domanda e risposta (A A'), su quattro A A' A B. A' è la stessa battuta con un altro finale. B è la "svolta": cambia di più. HEAT dice quanto | **sì**. Prima erano 32 o 64 step a caso, senza forma |
| **DICE** (libreria) | una variazione in forma di frase (nell'ultima battuta arriva quella dopo, con il fill), e ogni battuta ha una piccola mano diversa | **sì**. Prima riportava la traccia a 16 |
| **DICE** (GENRE FREE) | come RANDOM: una battuta e la sua frase | **sì** |
| **COOK** verso la variazione dopo | cammina verso la variazione scritta come frase lunga quanto la traccia | **sì**: non tocca più la lunghezza |
| **COOK** a caso | cucina ogni battuta per conto suo, con le regole del ruolo: le battute si allontanano piano | no, lo faceva già |
| **motori THEORY** | fanno le battute che la traccia ha: 16 step una battuta, 32 "a a'", 64 "a a' a b" con la svolta e il fill | **sì**: prima decideva LIBRARY LEN, adesso la traccia |
| **EVOLVE** | cucina tutto il loop: ogni battuta evolve a modo suo | no |
| **EUCLID** | i colpi sono sparsi su tutto il loop: 5 colpi su 32 step non sono 5 su 16 due volte | no, è già così |
| **TURING** | la sua frase è lunga quanto il suo registro (B: da 2 a 16 step) e gira dentro la traccia, qualunque lunghezza abbia | no |
| **CELL** | la sua riga è lunga B celle (da 4 a 64): metti B uguale alla lunghezza della traccia e hai una riga per giro | no |
| **NUMERIC** | un ritmo di una battuta, ripetuto | no |
| **ACCENT, DENSITY, ARP** | lavorano step per step: uguali su ogni lunghezza | no |
| **armonia, FOLLOW** | vanno a battute: una traccia da 64 step sente quattro battute di accordi | no |

In parole povere: **RANDOM, DICE, COOK e i motori THEORY adesso "traducono" quello che fanno sulla lunghezza della
traccia.** TURING e NUMERIC no: hanno una loro lunghezza per costruzione (il registro, il numero di 16 bit). Se vuoi
che anche loro si allunghino con la traccia dimmelo: si può fare, ma è un'altra cosa da disegnare.

## Il Pi e il grid

* **Il grid**: il colore nuovo delle copie (il verde-azzurro). Serve il bridge della 0.24, che è nello zip del Pi. Con
  un bridge vecchio le copie si vedono grigie.
* **L'editor del Pi** mostra le copie con lo stesso colore, e se ne selezioni una ti dice di quale step è la copia.
  Quando salvi, il Pi rimette tutto a posto come farebbe l'FM-1: se nell'editor allunghi una traccia, al Salva il
  pattern gira nei nuovi step; se cambi una copia, al Salva diventano step tuoi.
  Una cosa da sapere: nell'editor le copie nuove **compaiono dopo il Salva**, non mentre scrivi il numero.

## I progetti

* **Si aprono come sono.** Un progetto della 0.23 non ha copie: è tutto com'era.
* **Un progetto salvato con la 0.24 si apre anche con la 0.23**: le copie lì diventano step normali (suona uguale).
* **I pattern lunghi si salvano**, come prima: ogni pattern ha sempre 64 step di posto, a qualunque lunghezza.
* **Quanto pesano le copie.** La copia di una pausa non occupa niente. La copia di una nota occupa quanto una nota.
  Ho misurato: una band TECHNO di dieci tracce occupa 6.412 byte con le tracce da 16 step, 7.307 con le tracce da 64.
  Lo slot è di 32.768 byte, quindi c'è posto. Ma un progetto con tantissimi pattern pieni, tutti portati a 64, può
  non starci: l'FM-1 lo dice quando salvi (`TOO BIG FOR A SLOT`) e non rovina niente. In quel caso **SHORTER e poi
  salva**: le copie spariscono e il progetto torna piccolo.

## Cose più piccole

* Una mossa che ne cancella un'altra in coda adesso lo dice: `CANCELLED: LONGER` (anche `CANCELLED: HALF`). Prima
  diceva `QUEUED`, anche se la coda restava vuota.
* DOUBLE (SEQ + bianco 14) scrive il loop un'altra volta come **step tuoi**, non come copie: è fatto per cambiarli a
  mano.
* COPY e PASTE portano step, mai copie.
* Se sposti l'**inizio del loop** (HOME + ALG), le copie dei pattern di quella traccia diventano step: nessuna copia
  starebbe più al posto dello step che ripeteva.
* EVOLVE su una traccia con le copie le fa diventare step: ogni battuta evolve a modo suo.
* Una frase mandata dalla regia del Pi che cambia la lunghezza di una traccia adesso la rimette a tempo.
* Anche tutto il resto che cambia un loop sulla battuta (uno snapshot, un pattern con altre impostazioni) adesso
  atterra sulla battuta stessa, non un attimo dopo.
* L'esploratore ha una regola nuova, **COPIE**: dopo ogni gesto controlla che le copie siano a posto.

## Come è stato provato

Tutto nel simulatore: è lo stesso codice del firmware, compilato per il computer.

* **Il tuo caso** (16, poi 19 alla battuta, poi 32 alla battuta) adesso è una prova fissa: guarda lo step che suona su
  ogni battuta, e le rifà a ogni giro.
* **Prove nuove**: 52 controlli nel simulatore (le lunghezze, le copie, LONGER / SHORTER, i pattern caricati,
  i motori), 18 nell'editor del Pi, e le prove del cuore del firmware riscritte per le copie.
* **Tutta la suite**, nessun errore: 1.327 controlli nel simulatore dell'FM-1, 2.330.536 nel cuore del firmware,
  36.252.432 nei motori THEORY, 198 nell'editor del Pi, 322 nel bridge del grid, 177 nel hub, 76 nel banco, 51
  nell'esploratore per l'FM-1 vero, 48 nello slicer, 46 nelle celle, 14 nei file MIDI, 26 giri a caso con dati rotti.
* **L'esploratore**, giro completo, con la regola nuova COPIE: 76.720 gesti da soli in 23 situazioni, 9.197 coppie di
  gesti, 200 sessioni a caso da 60 gesti. Nessun errore.
* **Una situazione nuova nell'esploratore**, fatta per questa versione: una band con la traccia 1 da 32 (la seconda
  battuta sono le copie), la traccia 8 da 19, e le mosse che arrivano **alla battuta**. Serve perché nelle altre
  situazioni una mossa chiesta aspetta la fine della frase (16 battute) e lui, che guarda due battute dopo, la vedeva
  solo in coda: LONGER e SHORTER non succedevano mai davanti a lui. Lì dentro adesso succedono. Oltre al giro
  completo, 200 sessioni a caso da 60 gesti tutte in quella situazione: nessun errore.
* **Uno sbaglio mio, trovato all'ultimo controllo.** L'esploratore aveva una situazione "pattern di 4 battute" che
  le faceva con LIBRARY LEN. Tolto LIBRARY LEN, esplorava tracce da una battuta sola, con lo stesso nome, e niente lo
  diceva. Corretta (le tracce le allunga con LONGER), e adesso prima di cominciare l'esploratore controlla che ogni
  situazione abbia le lunghezze che il nome promette. Lo stesso valeva per una riga di `docs/TEORIA.md`, che spiegava
  ancora le parti di quattro battute con LIBRARY LENGTH: riscritta.
* **Rotture fatte apposta.** Ho rotto 17 cose, una alla volta, in una copia del firmware, per vedere se le prove se
  ne accorgono: tolto il riallineamento sulla battuta, rimesso l'errore dei 19 step, spento il servizio delle copie,
  tolto il segno di dove finisce un pattern, e così via. Se ne accorgono tutte e 17. Due all'inizio passavano (il
  dado e RANDOM che non facevano più la frase): ho stretto le prove finché non le hanno prese.
* **I controlli di memoria** (AddressSanitizer, UndefinedBehaviorSanitizer). La suite intera con i controlli accesi
  l'ho fatta prima delle ultime tre correzioni piccole al firmware: nessun errore. Dopo quelle, con i controlli
  accesi, ho rifatto le parti che toccano il codice nuovo: i 52 controlli nuovi, le prove del cuore, i 26 giri a caso,
  e l'esploratore nelle due situazioni delle lunghezze (in ognuna 2.901 gesti, 400 coppie, 200 sessioni). Nessun
  errore. La suite intera con i controlli, sul firmware finale, non l'ho rifatta.
* **Le pagine SAGGA dentro il RaspiMIDIHub vero** (il suo codice, sul computer; non un Pi): 99 controlli, nessun
  errore.
* **Su un FM-1 vero: niente.** Non ne ho uno. Vedi "Da sapere".

## Installare

1. **Il Pi**: sulla pagina del Pi, **AGGIORNA IL PI**, `sagga-hub-0.24.zip`. In alto deve dire `SAGGA HUB 0.24`.
2. **L'FM-1**: fermo, collegato al Pi: **FIRMWARE**, carica `sagga-0.24.fwsc`, **Installa**. Lo schermo dice
   `SAGGA SEQ 0.24`.

## Cosa provare per primo

Cinque minuti, con una traccia sola che suona un pattern da 16:

1. **HOME, K2 a 19**, aspetta la battuta. Poi **a 32**. Devi sentire il pattern due volte, in fase con le altre tracce.
   Lo schermo: `LENGTH 32: THE 16 STEPS REPEAT`.
2. Sul grid: nella seconda riga gli step accesi sono verde-azzurri (sono le copie). **Spegni uno step della prima
   riga**: si spegne anche il suo gemello sotto. **Tocca un pad della seconda riga**: quelli accesi diventano tutti
   verdi, e lo schermo dice `THE COPIES ARE YOUR STEPS NOW`.
3. **K2 a 12, poi di nuovo a 16**: il pattern è tornato com'era.
4. Su una traccia da 32, **SEQ + bianco 10 (BEAT)**: la traccia resta 32.
5. **SEL + GLO** (le MOSSE), poi **SEL + nero 6**: lo schermo dice `QUEUED: LONGER` e tutte le tracce raddoppiano a
   fine frase (16 battute, se non hai cambiato la frase). Per non aspettare: **nero 11** (NOW) la fa alla prossima
   battuta; da fermo succede subito. **SEL + nero 5**: tornano com'erano.

## Da sapere

* **Niente di questo ha girato su un FM-1 vero.** È provato nel simulatore, che usa lo stesso codice. Se qualcosa non
  suona come è scritto qui, dimmi i gesti che hai fatto: lo rifaccio uguale nel simulatore.
* **La prova al banco**: rifalla con FM-1 e Pi tutti e due alla 0.24 e mandami il file. Serve per due cose: i **6
  messaggi persi** della prova della 0.23 (ancora aperti: i conti diranno da che lato si perdono), e la regola nuova
  COPIE, che gira anche sull'FM-1 vero. Per le lunghezze conta soprattutto **l'FM-1 completo** (28 sessioni): una è
  la situazione nuova, con le copie e le mosse alla battuta. Nel banco quella situazione è l'ultima delle 21 sessioni
  (erano 20): con "tutte le sessioni" la fa, con "4 sessioni" no.
* **La 0.23.1 e la 0.23.2 non le ho mai viste su hardware**: quello che c'era scritto nelle loro note (il Pi che non
  disturba la musica, il bridge che si accorge dell'FM-1 riavviato, NUMERIC, CELL) resta da confermare da te.
* **SAVE 2 K4 ha cambiato significato.** Un progetto vecchio con LIBRARY LEN a 16 si legge COPY, con 32 o 64 si legge
  PHRASE. Se usavi LIBRARY LEN 32 o 64 per avere pattern lunghi: adesso è la lunghezza della traccia che decide.
  Allunga la traccia, poi carica.
* **Un pattern caricato è fatto per la lunghezza che la traccia ha in quel momento.** Se carichi su una traccia da 16 e
  poi la porti a 32, hai il pattern due volte. Per avere una frase di due battute: prima porta la traccia a 32, poi
  carica (o tira il dado).
* **Il firmware**: le dimensioni le misura GitHub quando lo compila: le scrivo qui appena le ha.
