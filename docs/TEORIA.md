# SAGGA SEQ 0.26 - i motori THEORY

Questo foglio spiega i motori THEORY: cosa sono, come si usano, cosa fa ognuno e perché, e a quali strumenti che
esistono già somigliano. In fondo ci sono i dettagli, per chi li vuole.

Le regole dei 21 generi contati dalla libreria sono in un foglio a parte: `TEORIA-GENERI.md`.

I motori sono nati nella 0.23. Dalla **0.25** le parti **si ascoltano fra loro**, la melodia **conosce l'accordo**, e i
motori lavorano in **qualunque metro** (7/8, 5/4, 6/8...). Sono i punti 9, 10 e 11 più sotto. Dalla **0.26** scrivono
la parte **dentro la battuta** del metro, e una risposta **ha le note**: sono i punti 11 e 12.

## In breve

Fino alla 0.22 una parte si **carica**: per ogni genere e per ogni parte la libreria ha fino a dodici pattern scritti, e
BEAT, KIT e BAND ne prendono uno.

Dalla 0.23 puoi scegliere, con la manopola **SOURCE** (SEQ pagina 8, K1). Ha tre posizioni:

* **LIBRARY**: tutto è come prima, le parti si caricano.
* **THEORY**: la parte non viene caricata. Viene **fatta sul momento**, dalle regole del **genere** e da un numero, il
  **SEME**.
* **FREE**: come THEORY, ma con le regole di **nessun genere**, qualunque genere sia scelto sull'FM-1. È il modo
  libero dei motori (vedi "Liberi dal genere", più sotto).

Poi:

* Lo stesso seme dà sempre la stessa band. Un altro seme, un'altra band dello stesso genere. I semi sono 999.
* Vale per tutti i **25 generi** dell'FM-1, e per **FREE** (nessun genere).
* I motori fanno la batteria, i bassi, gli accordi, gli arpeggi, i motivi (LEAD, VOX) e le progressioni.
* Quello che esce è un pattern come gli altri: lo modifichi, lo salvi, lo metti nelle scene. In più l'FM-1 ricorda da
  quale seme l'ha fatto, e per questo può **riempirlo e svuotarlo con l'ENERGIA** e portarlo a una **variazione**.

Puoi passare da una sorgente all'altra quando vuoi, anche suonando: quello che c'è sulle tracce resta.

## Come si usa

| cosa vuoi | cosa fai |
| --- | --- |
| accendere i motori | **SEQ pagina 8** (THEORY), **K1**: un passo, SOURCE THEORY (le regole del genere). Un altro passo, SOURCE FREE (nessun genere). Indietro: LIBRARY. |
| una band intera | **BAND** (SEQ + nero 7 tenuto), come sempre. La band è fatta dal seme scritto in NEXT SEED. Ancora BAND: il seme dopo, un'altra band. |
| solo la batteria | **KIT** (SEQ + nero 7). |
| la parte di una traccia | **BEAT** (SEQ + bianco 10). Ancora BEAT: il seme dopo. |
| scegliere il seme | **SEQ 8 K2** (NEXT SEED, da 1 a 999), oppure **SEQ + ALG**, che con la libreria sceglie la variazione. |
| un'altra parte sulla traccia, subito | **SEQ 8 K3** (TRACK SEED): giri, e il pattern diventa quello dell'altro seme. |
| la stessa parte, un po' diversa | **COOK** (SEQ + bianco 9): cammina verso la variazione dopo dello stesso seme. Quanto cambia lo dice **HEAT**. Con **SEQ 8 K4** (VARIATION) ci vai diretto. |
| che cambi da sola | **EVERY** + COOK, come con la libreria. |
| più piena, più vuota | l'**ENERGIA** della macchina: GLO 3 K1, la riga dell'energia sul grid, RISER e DROP, il tablet. |
| semi a caso | **DICE SEQ**: OCT+ tiene, OCT- rimette com'era. |
| una progressione nuova | **DICE PROG**: è fatta con le regole del genere e va nello slot del dado. |
| cambiare genere tenendo la band | **GENRE LIVE**: le parti vengono rifatte nel genere nuovo, dallo stesso seme. |
| una melodia che resta al suo posto e segue gli accordi | È già così per i **LEAD** e i **VOX** fatti dai motori (0.25): la traccia ha FOLLOW su **MELODY** (ARP 4 K1). Su un lead di un progetto vecchio: gira ARP 4 K1 fino a MELODY. |
| un altro metro | **GLO 4** (0.25): K1 la battuta in step, K2 come si divide. I pattern dei motori vengono rifatti nel metro nuovo. |
| nessun genere | **SEQ 8 K1 su FREE**: BAND dà una band di otto parti fatta solo con il metro, e BEAT, KIT, i dadi e DICE PROG lavorano senza genere. Vedi "Liberi dal genere". |
| parti di quattro battute | **La lunghezza della traccia** (dalla 0.24): portala a 64 **prima** di fare la parte (HOME, K2; o per tutte le tracce la mossa LONGER, SEL + nero 6 nelle MOSSE, due volte). Con 16 step la parte è una battuta, con 32 due (la seconda risponde alla prima), con 64 quattro, e l'ultima ha la chiusura. Una parte già fatta su 16 step, se allunghi la traccia dopo, si ripete uguale (le copie): per le risposte e la chiusura rifalla. (Fino alla 0.23 lo decideva SAVE 2 K4, LIBRARY LENGTH.) |

Sul **grid**, nella vista BEAT, la terza riga: i pad da 11 a 16 scelgono il seme fra sei, il pad 10 passa ai sei dopo.
Con SHIFT tenuto vedi il pattern che quel seme darebbe.

Sul **tablet**, nella pagina SAGGA Live, c'è una riga nuova: SOURCE (LIBRARY, THEORY, FREE), NEXT SEED, SEED,
VARIATION. BEAT, COOK e DICE della pagina usano i motori quando SOURCE è su THEORY o su FREE.

Nell'**editor del Pi** le tracce il cui pattern è fatto dai motori hanno un segno con il seme (◆8). Se lì svuoti o
sposti un pattern, i motori lo dimenticano: da quel momento è un pattern scritto a mano.

Tre cose da sapere:

* L'energia **aggiunge soltanto**: salendo, i colpi che c'erano restano dove sono e le note tengono la loro altezza.
* Uno step che scrivi a mano in un pattern dei motori **resta**, anche quando l'energia cambia. Fanno eccezione le
  parti che seguono la cassa: il RUMBLE (TECHNO, HARDTECHNO) e il SUB (DRUM+BASS, DUBSTEP, JUNGLE, GRIME, BASSLINE,
  FOOTWORK, PHONK, UK DRILL, BAILE FUNK). Quelle, quando l'energia cambia, vengono rifatte tutte intorno alla cassa, e
  lo step scritto a mano si perde. Se ci tieni, incolla il pattern su se stesso (non è più dei motori) o scrivilo
  dopo aver scelto l'energia.
* Se incolli, raddoppi o svuoti un pattern, non è più dei motori: l'energia non lo tocca più. BEAT ne fa uno nuovo.

## Liberi dal genere (FREE)

I motori hanno un modo **libero dal genere**. In questo modo non guardano quale genere è scelto: usano regole che
vengono solo dal metro. Una cassa sta sui tempi, un rullante cerca il 2 e il 4, un hat sta sugli ottavi o sui
sedicesimi, un basso parte dall'uno.

Ci si arriva in tre modi. Il primo è quello diretto.

| cosa giri | cosa diventa libero |
| --- | --- |
| **SEQ 8 K1: SOURCE FREE** | **I motori**, sempre. Il genere dell'FM-1 resta scelto e vale per tutto il resto: l'armonia e le tracce già caricate dalla libreria. |
| **SEQ 6 K4: GENRE FREE**, con SOURCE THEORY | **Tutta la macchina**: i generatori ignorano il genere, e i motori con loro. |
| **ARP 4 K2: HARMONY FREE**, con SOURCE THEORY | **Solo le progressioni**: DICE PROG ne fa una di nessun genere. Le parti restano del genere. |

Cosa cambia in FREE:

* **BAND** dà sempre otto parti: KICK, SNARE, HAT, PERC, BASS, CHORD, ARP, LEAD. **KIT** dà le prime quattro.
* **BEAT** su una traccia fa la parte scelta, con le regole di nessun genere. Su più tracce insieme (lo scope su BANK
  o ALL) dà a ognuna la parte del suo **ruolo**: FREE ha una regola per ogni ruolo. Un CLAP si comporta da rullante,
  un RUMBLE da basso, un PAD da accordi, un VOX da motivo.
* Le parti non prendono lo swing e il GROOVE di un genere. Il tempo resta quello che hai.
* **DICE PROG** usa qualunque scala e qualunque movimento della tonalità.
* L'**ENERGIA**, **COOK**, il seme e la variazione funzionano come sempre.
* Con SOURCE FREE un **cambio di genere non tocca i pattern dei motori**, nemmeno con GENRE LIVE: restano come sono.
  Le tracce caricate dalla libreria seguono il genere come sempre, dalla libreria. (Con SOURCE THEORY e GENRE LIVE i
  pattern dei motori vengono rifatti nel genere nuovo.)
* Ogni pattern **ricorda come è stato fatto**. Uno fatto in FREE resta di nessun genere anche se poi torni su THEORY:
  l'energia e COOK lo trattano da FREE finché non lo rifai con BEAT.

Sullo schermo la casella SOURCE dice FREE, e la riga sotto dice cosa farà BEAT, per esempio `FREE KICK SEED 4`. Con
SOURCE THEORY e GENRE FREE la casella dice THEORY e la riga sotto dice FREE.

## I motori, uno per uno

### 1. Il ritmo

**Cosa fa.** Decide su quali sedicesimi c'è un colpo, e quanto forte. Ogni parte ha una o più **famiglie**: modi di
suonarla tipici del genere. Un hat può essere in ottavi, in levare, in sedicesimi; il seme sceglie quale. Di ogni
famiglia c'è una parte che **c'è sempre** (le quattro casse della techno, il rullante del dembow) e una parte che
**può esserci**: per ogni altro sedicesimo c'è un peso, che dice quanto spesso lì cade un colpo.

**Perché.** Un genere si riconosce da quello che c'è sempre. Il resto è quello che cambia da un brano all'altro. Tenere
le due cose separate vuol dire che ogni band è diversa ma resta nel genere.

**A cosa somiglia.** A *Grids* di Mutable Instruments, che ha una mappa di pattern di batteria ricavata da loop veri e
per ogni canale decide i colpi confrontando un livello con una soglia. E a *GESMI* (Eigenfeldt e Pasquier), che ha
contato su cento brani quante volte ogni sedicesimo ha un colpo e da lì genera: è il modo in cui sono nate le regole di
21 generi su 25 (vedi più sotto).

### 2. L'energia

**Cosa fa.** Riempie una parte o la svuota. A energia zero resta lo **scheletro**: per un hat in ottavi, il levare;
per la cassa in quattro del reggaeton o della trance, i colpi sull'1 e sul 3 (in TECHNO e HOUSE, scritti a mano, la
cassa resta in quattro a qualunque energia). Da 25 c'è il pattern intero. Salendo ancora entrano i colpi in più, prima
i più probabili. A 50 una parte somiglia a quelle della libreria; a 100 è molto piena.

**Perché.** In un live l'energia è il gesto più usato. Se svuotando una parte i colpi sparissero a caso, il genere
sparirebbe con loro. Qui spariscono per ultimi quelli che contano di più: gli accenti, e quello che la libreria stessa
tiene nelle sue versioni più vuote.

**A cosa somiglia.** Alla manopola FILL di *Grids* (più giri, più colpi, e gli accenti stanno sui colpi che contano) e
a *Complexity* e *Intensity* dei Session Players di Logic Pro.

### 3. Le linee: BASS, SUB, RUMBLE, LOG DRUM

**Cosa fa.** Prima il ritmo, come sopra. Poi per ogni colpo sceglie una nota dell'accordo. Sull'uno quasi sempre la
fondamentale. Sugli altri tempi fondamentale, quinta o ottava. Fuori dai tempi può rispondere con l'ottava, ripetere
la nota del tempo, o prendere una nota sua. Quali note usa, e quanto spesso, dipende dal genere: un basso trance è
quasi solo fondamentale e ottava, un basso UK garage usa anche la terza e la quarta. Il rumble non suona mai dove
suona la cassa, e guarda la cassa **vera** della band, quella che sta suonando. Il sub le sta vicino.

**Perché.** Un basso non è una melodia libera: sta sotto l'accordo e tiene insieme cassa e armonia. Le regole sono
quelle di un bassista: fondamentale sul battere, ottave per muoversi, poche note di passaggio.

**A cosa somiglia.** Ai bassisti dei Session Players di Logic Pro, che seguono la traccia degli accordi e possono
agganciarsi al ritmo di un'altra traccia. E alla matrice di GESMI, che per il basso conta insieme quando cade una nota
e quale nota è.

### 4. Gli accordi: CHORD, STAB, PAD, PIANO

**Cosa fa.** Il ritmo, poi il tipo di accordo: triade, accordo di settima, quinta vuota. L'accordo è scritto sulla
tonica. Lo sposta l'**ARMONIA**, che lo porta sul grado della progressione e gli dà il colore (settima, nona, sus).

**Perché.** Così una parte di accordi fatta dai motori segue qualunque progressione, anche una scritta da te o una
presa dal Pi, come fa una parte della libreria.

**A cosa somiglia.** All'*NDLR* di Conductive Labs: pad, drone e motivi seguono tutti la stessa tonalità e lo stesso
accordo, deciso in un posto solo.

### 5. I motivi: LEAD, VOX

**Cosa fa.** Il ritmo, poi una **forma**: il motivo scende, sale, fa un arco, oppure alterna due note. Si muove su una
scala di cinque note (la pentatonica) o di sette. Sui tempi tende a una nota dell'accordo. Su quattro battute la forma
è domanda e risposta: la seconda battuta risponde e resta aperta, la quarta torna a casa.

**Perché.** Un motivo si ricorda per la forma, non per le singole note. Una forma semplice, ripetuta con una risposta,
suona come una frase. Note a caso nella scala no.

**A cosa somiglia.** Al *T-1* di Torso Electronics, dove una frase è una forma (rampa, triangolo, onda) più
un'ampiezza. E ai motivi dell'NDLR.

### 6. L'arpeggio: ARP

**Cosa fa.** Il ritmo, poi le note dell'accordo in fila: su, giù, su e giù, bassa-alta, oppure un ordine suo che si
ripete. Nei generi dove gli arpeggi della libreria hanno la settima, la usa.

### 7. Le progressioni

**Cosa fa.** DICE PROG, con SOURCE su THEORY o su FREE, non pesca una progressione della libreria: ne fa una. Decide quanti accordi
(da uno a quattro), quanto dura ognuno, e dove va la fondamentale. Non usa mai un accordo diminuito o aumentato. La
tonica c'è sempre, e l'ultimo accordo è uno che riporta a casa. I colori ci sono solo dove la tonalità li fa suonare.

**Perché.** Ogni genere muove gli accordi a modo suo. La techno sta ferma su uno o due accordi. La house sale di
quarta. Il reggaeton ha quasi sempre quattro accordi di una battuta. Sono proporzioni: i motori le rispettano.

### 8. Seme e variazione

**Cosa fa.** Ogni scelta dei motori è un numero che esce dal seme, dalla parte e dal **posto nella battuta**. Per questo
lo stesso seme ridà la stessa band. Una **variazione** rifà solo una quota delle scelte, quella che dice HEAT. Fino al
40 % cambiano i dettagli. Oltre, cominciano a cambiare anche le scelte grosse, come la forma di un motivo. La famiglia
resta sempre quella del seme: un hat in levare non diventa un hat in sedicesimi con COOK. Per quello c'è un altro seme.

**Perché.** Con i numeri legati al posto, una variazione piccola resta piccola: cambia due colpi, non tutto il pattern.
E l'energia può aggiungere una nota senza spostare le altre.

**A cosa somiglia.** Alla *Turing Machine* di Music Thing Modular: una manopola che va da "sempre uguale" a "sempre
diverso", e in mezzo cambia una nota ogni tanto.

### 9. L'ascolto fra le parti (0.25)

**Cosa fa.** Fino alla 0.24 ogni parte nasceva da sola. Solo la cassa veniva guardata: il rumble la evita, il sub la
cerca. Dalla 0.25 una parte nasce **insieme alla parte a cui risponde**:

| questa parte | risponde a |
| --- | --- |
| LEAD, VOX, ARP | gli **accordi** (la prima traccia con il ruolo CHORD, STAB, PAD o PIANO) |
| PERC, CONGA, TOM, COWBELL | il **rullante** (la prima traccia con il ruolo SNARE, CLAP o RIM) |
| BASS, SUB, RUMBLE, LOG DRUM | il **lead** (la prima traccia con il ruolo LEAD, VOX o ARP) |
| cassa, rullante e clap, hat, shaker, ride, crash, accordi | nessuno: sono come nella 0.24 |

L'altra traccia deve andare a sedicesimi (non a terzine o in un poliritmo), e non essere un TAPE o un BREAK.

Rispondere vuol dire due cose. **Dove l'altra parte attacca**, questa tace due volte su tre (i colpi che il genere
vuole sempre restano). **Subito dopo un attacco** dell'altra, un colpo di questa è più probabile. Così il lead non
copre gli accordi e suona nei loro vuoti, e il basso lascia spazio sotto il lead.

Funziona in qualunque ordine fai le parti. Se rifai gli accordi (BEAT, un altro seme, il dado, UNDO), dopo un attimo
il lead e l'arpeggio vengono **rifatti da soli**, dal loro stesso seme, per rispondere agli accordi nuovi. L'altra
parte può anche essere un pattern della libreria o uno scritto da te: i motori leggono i suoi step.

**Perché.** In una band vera nessuno suona da solo. Due parti che attaccano sempre insieme si coprono; due parti che
si alternano si sentono tutte e due. È la differenza fra otto loop messi uno sull'altro e un arrangiamento.

**A cosa somiglia.** Al bassista dei Session Players di Logic Pro, che può seguire il ritmo di un'altra traccia. E al
vecchio trucco del "call and response": una parte chiama, l'altra risponde nei vuoti.

**Quanto.** Misurato su 60 semi per ognuno dei 26 stili:

| | colpi sugli attacchi dell'altra | colpi subito dopo | colpi in tutto |
| --- | --- | --- | --- |
| lead, voci, arpeggi con gli accordi | 23 % in meno | 14 % in più | quasi uguali |
| percussioni con il rullante | 28 % in meno | 18 % in più | uguali |
| bassi con il lead | 28 % in meno | 15 % in più | 10 % in meno |

Tre cose da sapere:

* Una parte risponde a **una sola** altra parte, e solo con il **ritmo**. Le note non cambiano.
* Quando la parte a cui risponde viene rifatta, anche lei viene rifatta **intera**: uno step scritto a mano lì sopra si
  perde. Se ci tieni, incolla il pattern su se stesso (non è più dei motori).
* L'altra parte viene ascoltata a energia media. Così muovere l'ENERGIA non rifà tutte le risposte a ogni passo.

### 10. La melodia e l'accordo (0.25)

**Cosa fa.** Un motivo è scritto sull'accordo di tonica. Fino alla 0.24 lo spostava FOLLOW, tutto intero, a ogni
accordo: lo stesso disegno una terza sotto, una quarta sopra. Va bene per un riff di basso. Una melodia vera non fa
così.

Dalla 0.25 FOLLOW ha un quarto modo, **MELODY** (ARP 4 K1, dopo LEGATO), e i LEAD e i VOX fatti da BEAT, BAND, i dadi
e i motori lo ricevono da soli:

* la melodia **resta dove è scritta**, non salta con gli accordi;
* le sue **note forti** vanno alla **nota più vicina dell'accordo che suona**. Sono forti le note su un tempo della
  battuta e le note più lunghe di uno step. Se due note dell'accordo sono alla stessa distanza, vince quella sotto;
* le **note corte fra i tempi** restano come sono scritte: sono note di passaggio, nella scala;
* una **nota tenuta** mentre l'accordo cambia scivola alla nota più vicina dell'accordo nuovo (come LEGATO). Se è già
  una nota dell'accordo nuovo, continua.

Un esempio in LA minore, con gli accordi Am, F, C, G. Il motivo ha LA, DO, MI sui tempi. Su Am resta LA DO MI. Su F
(FA LA DO) diventa LA DO **FA**. Su C (DO MI SOL) diventa **SOL** DO MI. Su G (SOL SI RE) diventa **SOL SI RE**. Ogni
nota si è mossa di un tono al massimo: la linea è la stessa, e sta sempre dentro l'accordo.

**Perché.** È quello che fa chi canta o suona un tema sopra un giro di accordi: tiene la linea e appoggia le note
importanti su quelle dell'accordo. Le note corte in mezzo possono essere fuori dall'accordo, perché passano.

**A cosa somiglia.** Alla "chord track" di Logic Pro e di Cubase, che porta le note di una melodia sulle note
dell'accordo più vicine. E ai motivi dell'NDLR, che cambiano note con l'accordo senza cambiare registro.

Vale per qualunque traccia, non solo per quelle dei motori: metti FOLLOW e MELODY su una melodia scritta da te.
Un accordo (uno step con due note o più) su una traccia MELODY si sposta come sempre.

### 11. Il metro (0.25), e la battuta (0.26)

**Cosa fa.** La battuta dell'FM-1 può avere **da 3 a 32 step**, divisi in tempi come vuoi (GLO 4): 7/8 come 2+2+3,
5/4, 6/8, 9/8. Dalla 0.26 i motori scrivono la parte **dentro quella battuta**.

Come: ogni passo della battuta **sta per** un sedicesimo di una battuta in 4/4, e le regole dello stile (quanto pesa un
sedicesimo, cosa c'è sempre, cosa non c'è mai) vengono lette lì. Ma ogni scelta porta il nome del posto vero del
passo: così due tempi della battuta non sono mai la copia uno dell'altro.

* La battuta ha **due metà**, divise al tempo più vicino al centro. La prima metà sta per i tempi 1 e 2 (l'uno e la sua
  risposta), la seconda per i tempi 3 e 4.
* Dentro una metà i tempi sono, a turno, "il primo" e "la risposta". Un 5/4 è UNO due due | TRE quattro.
* Un metro dispari si può **sentire in due modi**. Il 7/8 come 2+2+3: il tempo lungo è un tempo solo (UNO due TRE-e),
  oppure è spezzato (UNO due TRE-quattro). Ogni band ne ha uno, scelto dal suo seme, uguale per tutte le sue parti.
* Una battuta di **due tempi** è mezza battuta: due di loro fanno UNO due | TRE quattro. Una di un tempo solo è un
  quarto di battuta.
* **La spina dorsale non si perde.** Una battuta di tre tempi sta per tre dei quattro tempi: può non avere un passo
  per il colpo su cui una parte è costruita (il rullante della dubstep sul tre). Allora lo porta il passo più vicino
  con lo stesso posto nel tempo: il rullante finisce sull'ultimo tempo della battuta.
* **L'energia aggiunge soltanto**, anche qui: quello che una parte ha a energia zero resta sotto a ogni energia.
* La lunghezza è di una, due o quattro **battute del metro** (quante ne ha la traccia), non più di 64 step.

In 4/4 non cambia niente: un passo sta per se stesso, e i motori fanno le parti della 0.25, identiche.

Se cambi metro, i pattern dei motori vengono **rifatti dentro la battuta nuova**, dal loro seme, uno alla volta (prima
la parte a cui un'altra risponde, poi quella che risponde). Se torni al metro di prima ritrovi il pattern di prima.
Un pattern dei motori che hai cambiato a mano resta com'è, nel suo metro: finché la battuta è un'altra, nemmeno
l'ENERGIA lo tocca.

**I pattern della 0.25.** Quello che i motori ricordano di un pattern dice come è stato fatto. Un pattern della 0.25
viene rifatto come lo faceva la 0.25 (l'energia, una variazione, un altro genere): così un progetto vecchio suona
come prima. Solo il cambio di metro lo porta dentro la battuta, e in 4/4 torna quello che era.

**Perché.** Un genere si riconosce da cosa cade sui tempi e da cosa cade fra i tempi. Stendere un 4/4 su sette (la
0.25) teneva la cassa sui tempi, ma il risultato era un 4/4 a cui mancava un pezzo. Dando a ogni passo il suo posto,
la cassa della techno batte su ogni tempo del sette e il levare resta levare.

**Il limite.** I motori conoscono i generi in 4/4 e li portano negli altri metri. Un aksak bulgaro o un 5/4 jazz
veri hanno accenti loro, che nessuna regola qui dentro conosce.

### 12. La risposta ha le note (0.26)

**Cosa fa.** Nella 0.25 una parte rispondeva a un'altra solo nel ritmo. Adesso anche con le note.

* **Il basso sotto la melodia** (o sotto l'arpeggio). Fuori dai tempi, dove la melodia non attacca e ha appena
  suonato, il basso prende la nota che la melodia aveva **un ottavo o un quarto prima** (lo decide il seme della
  band); se lì non c'era niente, l'ultima nota della melodia nel giro di un tempo. Sui tempi il basso resta sulle sue
  note: lì è il fondamento.
* **Quanto spesso lo decide lo stile.** Più il basso di quello stile usa di suo quella nota (la terza, la settima, la
  quarta...), più volentieri la prende: al massimo sette volte su dieci. Una nota che il basso di quello stile non
  suona mai, non la prende. Il basso della trance, tutto toniche, resta tutto toniche; quello della garage canta.
  Mai la settima maggiore: un basso suona la sesta al suo posto.
* **La melodia sopra gli accordi.** Sui sedicesimi subito dopo un accordo, dove gli accordi tacciono, la melodia
  suona una nota dell'accordo: sul primo sedicesimo la terza, sul secondo la quinta, sul terzo la settima (l'ottava
  se l'accordo non ha settima). Sei volte su dieci. La fine della frase resta com'era: torna a casa.
* **Quando gli accordi si spostano**, FOLLOW MELODY tratta quella nota come una nota forte: la porta sulla nota più
  vicina dell'accordo che sta suonando. Così la risposta è una nota dell'accordo sotto ogni accordo, non solo sul primo.
* **La parte a cui si risponde viene sentita com'è davvero**: fatta a metà energia, e insieme alla parte a cui
  risponde lei. Il basso sente la melodia che sente gli accordi.

Il ritmo non cambia: le note cambiano solo dove la parte suonava già. E una nota resta la stessa a ogni energia.

**Sotto un arpeggio** il basso prende note dell'accordo che l'arpeggio sta girando. A metà energia sono proprio le
note appena suonate; a un'altra energia l'arpeggio cambia ordine, e la nota è dell'accordo ma non sempre quella.

**Sugli altri accordi** il basso sposta la nota presa insieme all'accordo, come fa con tutte le sue note: riprende
il disegno della melodia, portato sull'accordo.

**Vale per i pattern fatti nuovi** con la 0.26 (BEAT, BAND, i dadi, un seme nuovo). Un pattern della 0.25 continua a
rispondere solo nel ritmo, anche dopo un cambio di metro.

**Perché.** In una band vera il bassista riprende la coda della frase del solista, e il solista dopo un accordo ne
suona le note. È il modo più semplice di far sentire che due parti parlano fra loro.

## Da dove vengono le regole

* **TECHNO, HOUSE, DRUM AND BASS, DUBSTEP**: scritte a mano, da quello che si legge su come si costruiscono questi
  generi (le fonti sono in fondo) e controllate sulla libreria. Sono più sotto in questo foglio.
* **Gli altri 21 generi**: **contate dalla tua libreria**. Un programma (`tools/theory/gen_rules.py`) legge tutti i
  pattern di un genere, mette insieme quelli che sono lo stesso pattern con altri dettagli (una famiglia), e conta. Quello
  che quasi tutti suonano diventa "c'è sempre". Quello che suonano alcuni diventa un peso. Dai pattern di due e quattro
  battute impara cosa fa la seconda battuta. Dalle note impara quali usa un basso e come si muove un motivo. Dalle sei
  progressioni del genere impara come si muovono gli accordi. Le trovi in `TEORIA-GENERI.md`.
* **FREE**: scritto a mano. Usa solo il metro: una cassa sta sui tempi, un rullante sul 2 e sul 4, un hat sugli ottavi.

Se cambi la libreria, le regole contate si possono rifare con un comando.

## Quanto somigliano alla libreria

Misurato dal programma `tools/theory/compare.py`, 60 semi per genere, energia 50:

* su 229 parti, **218** cadono dove cade la libreria: gli stessi sedicesimi, con frequenze simili;
* in media una battuta fatta dai motori è a **mezzo sedicesimo** dalla battuta scritta più vicina, e **due battute su
  tre** sono battute che la libreria ha già, colpo per colpo (sette su dieci nei 21 generi contati, quattro su dieci
  nei quattro scritti a mano);
* delle 11 parti lontane, 9 sono nei quattro generi scritti a mano, dove alcune parti sono volute diverse (la
  percussione tre-contro-quattro della techno non è nella libreria);
* le note dei bassi hanno le stesse proporzioni della libreria. I motivi usano le stesse note ma più terze e meno
  quarte.

Detto chiaro: a energia 50, nei generi contati, i motori stanno **molto vicini alla libreria**. Il nuovo viene da come
le battute si combinano fra le parti, dalle note (che non sono quelle scritte), dall'energia e dalle variazioni.

E i controlli sul motore (43 milioni, su 150 semi per ognuno dei 26 stili): una parte non è mai vuota; salendo di
energia nessun colpo si perde; una nota che resta tiene la sua altezza (ne cambiano 7 su diecimila, le ultime di un
motivo); quello che **ogni** pattern della libreria suona, i motori lo suonano sempre. Dalla 0.25 anche: una parte che
risponde a un'altra non è mai vuota, non perde colpi salendo di energia, e resta uguale se non risponde a nessuno.

## Cosa non sanno fare

* **Una parte ascolta una sola altra parte.** Il lead ascolta gli accordi ma non il basso. Dalla 0.26 la risposta ha
  le note, ma è una risposta corta: una nota ripresa, non una frase intera completata.
* **Conoscono i generi in 4/4.** In un altro metro la parte nasce dentro la battuta (0.26), ma con le regole che il
  genere ha in quattro. Le terzine ci sono solo come rullata. Lo swing e il GROOVE sono quelli che l'FM-1 dà al
  genere.
* **Una frase è di due battute.** Con quattro battute la terza ripete la prima e la quarta risponde come la seconda, con
  la chiusura. I break lunghi quattro battute della jungle diventano frasi di due.
* **Un motivo è una voce sola.** Dalla 0.25 conosce l'accordo (FOLLOW MELODY), ma solo con le note forti: una nota
  corta fra i tempi resta quella scritta, e sopra un accordo preso da fuori scala può stridere per un sedicesimo.
* **Le regole contate vengono dalla libreria**: un genere suona come la sua libreria, non meglio.
* **Il seme arriva a 128 dal tablet** (una manopola MIDI ha 128 valori). Dall'FM-1 arrivi a 999.

## Cosa non è stato provato

Tutto questo gira nel **simulatore**, che è il firmware stesso compilato per il computer. Non su un FM-1 vero: non ne
ho uno. Il simulatore controlla la logica, i tempi e il MIDI che esce. Non può dire **come suona**: se un genere non ti
convince, dimmi quale parte, e si corregge la regola.

## I dettagli: come nasce una parte

### Il seme

Ogni scelta è un numero da 0 a 255 fatto dal seme, dalla parte e dal nome della scelta ("la cassa, il sedicesimo 11").
Niente dipende da cosa è stato fatto prima: per questo lo stesso seme ridà la stessa band, e una variazione cambia solo
le scelte che rifà.

Una parte dura una, due o quattro battute: quelle che la traccia ha quando la parte viene fatta (16, 32 o 64 step;
fino alla 0.23 lo decideva LIBRARY LENGTH). Su una traccia di un'altra lunghezza la parte è fatta su 16, 32 o 64
step, la misura più grande che ci sta (16 su una traccia da 19, 32 su una da 48), e il resto sono le sue copie; su una
traccia più corta di 16 è fatta su 16 e ne suona l'inizio. Le battute 1 e 3 sono la stessa battuta; la 2 e la 4
rifanno una quota delle scelte (la **risposta** alla prima); l'ultima ha la **chiusura** del genere.

### Il ritmo

Una battuta è sedici sedicesimi. Nei blocchi li leggi così, come nella libreria: `X` accento, `x` colpo, `o` piano,
`g` ghost, `.` niente.

* **sempre**: i colpi che ci sono a qualunque energia e in qualunque variazione (le quattro casse della techno).
* **mai**: i sedicesimi dove quella parte non suona (il rumble sulla cassa).
* **pesi**: per ogni altro sedicesimo, quanto è probabile un colpo, da `1` a `f` (15); `.` è zero. Un colpo c'è con
  probabilità *peso / 15 × densità*; la **densità** va dal primo numero (energia 0) al secondo (energia 100). Un peso
  da `c` in su è un accento; fino al peso scritto accanto il colpo è piano o ghost.
* **classi**: i quattro tempi, le quattro `e`, i quattro `&`, le quattro `a` possono entrare tutti insieme, con una
  scelta sola. È quello che rende regolare un hat o uno shaker invece che sparso. La percentuale è a energia 100.
  "Manca" è la probabilità che un colpo della classe venga lasciato fuori.
* **ciclo**: un colpo ogni tre sedicesimi che gira sopra le stanghette (tre contro quattro).
* **con la cassa**: una parte può non suonare mai dove suona la cassa della stessa band, o cercarla.
* **mai due vicini**: fra due colpi su sedicesimi attaccati resta quello che entra a un'energia più bassa.

Una parte non è mai vuota: se a quell'energia non le toccherebbe niente, ha il colpo che entrerebbe per primo.

Le **regole contate** (i 21 generi di `TEORIA-GENERI.md`) usano gli stessi pesi, e in più:

* **famiglie**: più regole per la stessa parte; il seme ne sceglie una, secondo quante variazioni della libreria le
  somigliano;
* **due battute**: una famiglia può avere una regola per le battute 1 e 3 e una per le battute 2 e 4;
* **base e pieno**: di quello che c'è sempre, una parte c'è a qualunque energia e il resto entra a energia 25;
* **i livelli per posto**: accento, colpo, piano o ghost li decide il sedicesimo, come li scrive la libreria lì;
* **le rullate per posto**: dove la libreria rulla (l'hat della drill), un colpo può essere una rullata.

### La linea (BASS, SUB, RUMBLE)

Prima il ritmo, poi una nota dell'accordo per ogni colpo, **secondo il posto nella battuta**. Ogni tempo ha la sua
nota: sull'uno la fondamentale, sugli altri tempi quasi sempre fondamentale, quinta o ottava. Una nota fuori dal tempo
risponde alla nota del suo tempo: l'ottava se quella è la fondamentale (il basso a ottave della house), oppure la
ripete, oppure è una nota sua. Nell'ultimo ottavo del pattern può esserci una nota che riporta a casa (la settima, la
quinta, la seconda, la quarta). La settima maggiore sotto un accordo viene sostituita dalla sesta.

### Gli accordi (STAB, PAD, PIANO)

Il ritmo, poi il tipo di accordo: la **triade** della tonalità (`m` o `M`), il suo accordo di **settima** (`n`, `N` o
`7`), la **quinta vuota** (`5`). L'accordo è scritto sulla tonica: è l'ARMONIA che lo sposta sul grado che suona e gli
dà il colore della progressione (la settima, la nona, la sesta, le sospensioni).

Nessuna parte scrive un `sus4`: l'ARMONIA sposta un accordo scritto per gradi della scala, e su un grado di ogni scala
la quarta non è giusta (il VI di una tonalità minore). Gli accordi sospesi sono colori della progressione, che sa su
che grado si trova.

### Il motivo (LEAD, VOX)

* **La scala su cui si muove**: la pentatonica della tonalità (minore: fondamentale, terza, quarta, quinta, settima;
  maggiore: fondamentale, seconda, terza, quinta, sesta), oppure tutte e sette le note.
* **Il profilo** della battuta: scende, sale, fa un arco, oppure alterna due note. Parte da una nota dell'accordo (la
  fondamentale più spesso, poi la quinta, poi la terza).
* **Ogni nota** sta sul profilo, o un gradino più in là (una nota di volta), ogni tanto due (un salto), oppure ripete
  la nota del suo tempo. Sui tempi è quasi sempre una nota dell'accordo, sull'uno sempre.
* **La forma** è `a a' a b`: la battuta 2 comincia come la 1, risponde un gradino sopra o sotto e chiude **aperta**,
  sulla quinta; la 4 ha un altro profilo e torna **a casa**, sulla fondamentale o sulla sua ottava.

Anche qui una nota ha la sua altezza dal posto che occupa: l'energia aggiunge note, le altre restano dove sono.

### L'arpeggio (ARP)

Le note dell'accordo in un ordine, una per colpo: su, giù, su e giù, bassa-alta-bassa-alta, oppure un ordine suo che
si ripete a ogni battuta. In TECHNO sono quattro (triade e ottava) con un accento ogni tre note, tre contro quattro.
Negli altri generi quattro o cinque: con la settima dove gli arpeggi della libreria di quel genere ce l'hanno.

### La progressione

* **La scala e la tonica** le sceglie il seme, fra quelle che lo stile usa.
* **Quanti accordi** (da uno a quattro) e **quanto dura** ognuno. Il giro intero sta in sedici battute.
* **Le fondamentali si muovono per gradi della scala**, con i pesi dello stile (una quarta sopra nella house, un grado
  sotto o il secondo abbassato nella techno, verso il sesto e il settimo abbassati nella drum and bass).
* **Mai un accordo diminuito o aumentato** (il II di una tonalità minore, il VII di una maggiore, il III di una
  minore armonica).
* **Casa c'è sempre**: quasi sempre è il primo accordo; se la progressione parte da un altro, casa arriva alla fine.
* **L'ultimo** di tre o quattro accordi è uno che riporta a casa.
* **I colori** (settima, nona, sus4, sus2, sesta) solo dove la tonalità li fa suonare: una nona o un sus2 vogliono una
  seconda maggiore sopra la fondamentale (non quella abbassata di una tonica frigia), un sus4 una quarta giusta, una
  sesta una sesta maggiore, e niente settima maggiore su un accordo minore.
* **L'anticipo**: gli accordi possono entrare un sedicesimo o un ottavo prima della battuta (la house).

Lo stesso seme in due stili dà la stessa tonica (la scala la sceglie ogni stile fra le sue).

### ENERGIA e VARIAZIONE, misurate

Su 150 semi per stile, 26 stili, tutte le parti, otto livelli di energia (`tests/sagga_theory_tests.c`, 36 milioni di
controlli):

* salendo di energia **nessun colpo si perde** (il rumble a parte, dove entra una cassa: sulla cassa non suona mai);
* una nota che resta **tiene la sua altezza**: su quattro milioni ne cambiano tremila, e sono le note che chiudono un
  motivo (l'ultima cambia quando l'energia ne aggiunge una dopo);
* una variazione dello 0 % non cambia niente; del 10, 25, 50, 75, 100 % cambia in media **3, 6, 12, 18, 22** step su
  cento (gli altri sono pause in tutte e due, o colpi che ci sono "sempre");
* quale **famiglia** segue una parte lo decide il seme, e nessuna variazione lo cambia.

## Le regole scritte a mano

I blocchi "le regole" non sono scritti a mano: escono dalle tabelle del motore (`firmware/src/sagga_theory.c`) e un
test controlla che siano uguali. Quello che leggi è quello che suona.

### TECHNO (131 BPM)

La cassa in quattro, sempre, con l'accento; attorno i ghost che la fanno rotolare, soprattutto sull'ultimo sedicesimo
della battuta e su quello prima del 4. Il clap sul 4 sempre e sul 2 quasi sempre, con i ghost vicini. L'hat sul levare,
sempre; i sedicesimi gli entrano a classi intere con l'energia. L'open hat sul levare del 2 e del 4, il ride in ottavi.
La percussione: pochi colpi sparsi, oppure un ciclo di tre sedicesimi sopra le stanghette. Il **rumble** occupa i tre
sedicesimi fra una cassa e l'altra e sulla cassa non suona mai. Il basso sta sul levare e poi si riempie; quasi solo
fondamentale e ottava. Lo stab: uno, due, tre colpi a battuta, singoli sedicesimi fuori dal battere. Il pad sull'uno,
tenuto. L'arpeggio in ottavi, con un accento ogni tre note.

L'armonia si muove poco: **un accordo solo** quattro volte su dieci, altrimenti due (quattro ogni tanto), per lo più
di quattro battute l'uno. Le scale sono la minore, la frigia (per il secondo grado abbassato) e la dorica; le
fondamentali scendono di un grado o di una terza, o salgono di un grado. Triadi, poche settime.

<!-- regole TECHNO -->
```text
KICK
    sempre   X...X...X...X...
    pesi     ...3.1.2.125.146   densità 0-78 %   fino a peso 3: 'o'
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

CLAP
    sempre   ............X...
    pesi     .1..d112.21..453   densità 47-100 %   fino a peso 5: 'g'
    battute 2 e 4: 30 % delle scelte rifatte
    chiusura un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi

HAT
    sempre   ..x...x...x...x.
    classi   tempi 23 % 'x'   e 27 % 'o'   a 59 % 'x'   a energia 0 il 31 % di queste
             un colpo della classe manca: 10 %
    battute 2 e 4: 20 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)

OPEN HAT
    pesi     .262.2d1.26..1b2   densità 63-100 %   fino a peso 2: 'g'
    battute 2 e 4: 15 % delle scelte rifatte

RIDE
    classi   tempi 92 % 'x'   e 12 % 'o'   & 98 % 'x'   a 27 % 'o'   a energia 0 il 67 % di queste
             un colpo della classe manca: 6 %
    battute 2 e 4: 10 % delle scelte rifatte

PERC
    pesi     14143286.3253636   densità 27-78 %   fino a peso 3: 'g'
    ciclo    un colpo ogni 3 sedicesimi, oltre le stanghette (40 % dei semi); sotto energia 40 uno ogni 6
    battute 2 e 4: 30 % delle scelte rifatte
    chiusura la seconda metà si riempie

RUMBLE
    mai      x...x...x...x...   e mai dove suona il kick
    classi   e 66 % 'o'   & 96 % 'x'   a 98 % 'x'   a energia 0 il 78 % di queste
             un colpo della classe manca: 5 %
    battute 2 e 4: 15 % delle scelte rifatte
    note     fondamentale 88 %, quinta 4 %, ottava 3 %, terza 3 %, settima 2 %, seconda 2 %
             sull'uno la fondamentale 86 %
             nell'ultimo ottavo una nota che riporta a casa 12 %

BASS
    sempre   ..x...x...x...x.
    classi   tempi 43 % 'x'   e 43 % 'x'   a 78 % 'x'   a energia 0 il 51 % di queste
             un colpo della classe manca: 5 %
    battute 2 e 4: 20 % delle scelte rifatte
    note     fondamentale 70 %, quinta 8 %, ottava 14 %, terza 3 %, settima 3 %, quarta 2 %
             sull'uno la fondamentale 92 %   sui tempi fondamentale, quinta o ottava 78 %
             fuori dai tempi: l'ottava della fondamentale del tempo 35 % (entro 3 sedicesimi), la nota del tempo 23 %
             nell'ultimo ottavo una nota che riporta a casa 43 %

STAB
    pesi     4..a..a3..2a55.3   densità 31-82 %
    battute 2 e 4: 40 % delle scelte rifatte
    accordi  triade 60 %, settima 30 %, quinta vuota 10 %   lo stesso tipo per tutto il pattern 90 %   tenuti 0 %

PAD
    sempre   x...............
    pesi     .....12171......   densità 43-94 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 30 % delle scelte rifatte
    accordi  triade 45 %, settima 55 %   lo stesso tipo per tutto il pattern 78 %   tenuti sempre

ARP
    sempre   x.x.x.x.x.x.x.x.
    classi   e 23 % 'x'   a 23 % 'x'   (insieme)   a energia 0 il 24 % di queste
             un colpo della classe manca: 5 %
    battute 2 e 4: 15 % delle scelte rifatte

LA PROGRESSIONE
    scala          minore 45 %, dorica 15 %, frigia 40 %
    accordi        uno 40 %, due 40 %, tre 5 %, quattro 15 %
    durata         1 battuta 5 %, 2 battute 25 %, 4 battute 45 %, 8 battute 25 %
    parte da casa  95 %
    la fondamentale si muove di  un grado sopra 25 %, una terza sopra 4 %, una quarta sopra 8 %, una quinta sopra 7 %, una terza sotto 25 %, un grado sotto 30 %
    l'ultimo di tre o quattro    II 25 %, III 5 %, IV 10 %, V 10 %, VI 25 %, VII 25 %
    colori         triade 60 %, settima 25 %, sus4 5 %, sus2 10 %   lo stesso per tutti 80 %
    entra          sulla battuta 95 %, un sedicesimo prima 5 %
```
<!-- /regole -->

### HOUSE (124 BPM)

La cassa in quattro e il clap sul 2 e sul 4, sempre. L'hat sul levare, e i tempi gli entrano come classe (ottavi);
l'open hat sul levare del 2 e del 4; lo shaker sul levare e poi in sedicesimi, tutti insieme. Il **basso** ha tre
famiglie: sul levare, il riff 3+3+2, quello sincopato; è un basso a ottave (dopo la fondamentale di un tempo, quasi una
volta su due viene la sua ottava). Il **piano** ha tre famiglie di stab: il 3+3+2, il levare, gli anticipi; quasi
sempre accordi di settima. La voce: due, tre, quattro note a battuta sui levare, sulla pentatonica, quasi solo note
dell'accordo.

L'armonia cammina: **quattro accordi** una volta su due, altrimenti due, di una o due battute. Minore e dorica, a volte
maggiore o misolidia. Le fondamentali salgono di una quarta, o scendono di una terza o di un grado. Settime e none. Una
volta su due gli accordi entrano **in anticipo**, di un sedicesimo o di un ottavo.

<!-- regole HOUSE -->
```text
KICK
    sempre   X...X...X...X...
    pesi     ...3.1.2..23.155   densità 0-78 %   fino a peso 3: 'o'
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

CLAP
    sempre   ....X.......X...
    pesi     .121..14.332.253   densità 16-86 %   tutti 'g'
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi

HAT
    sempre   ..x...x...x...x.
    classi   tempi 47 % 'x'   e 12 % 'o'   a 31 % 'o'   a energia 0 il 35 % di queste
             un colpo della classe manca: 8 %
    battute 2 e 4: 20 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)

OPEN HAT
    pesi     .451.3e2..51.2d2   densità 69-100 %   fino a peso 4: 'g'
    battute 2 e 4: 15 % delle scelte rifatte

SHAKER
    sempre   ..x...x...x...x.
    classi   tempi 59 % 'x'   e 59 % 'o'   a 59 % 'o'   (insieme)   a energia 0 il 24 % di queste
             un colpo della classe manca: 6 %
    battute 2 e 4: 15 % delle scelte rifatte

PERC
    pesi     ..82.2c1..4331b1   densità 47-94 %   fino a peso 2: 'o'
    battute 2 e 4: 55 % delle scelte rifatte
    chiusura la seconda metà si riempie

BASS
  una famiglia (35 % dei semi)
    sempre   ..x...x...x...x.
    pesi     ...23..1...33..2   densità 16-63 %
    battute 2 e 4: 25 % delle scelte rifatte
  una famiglia (35 % dei semi)
    sempre   x..x..x.x..x..x.
    pesi     .......1.2..2..2   densità 0-59 %
    battute 2 e 4: 25 % delle scelte rifatte
  una famiglia (30 % dei semi)
    sempre   ..x.....x.....x.
    pesi     3..4925..2367..2   densità 39-90 %
    battute 2 e 4: 30 % delle scelte rifatte
    note     fondamentale 50 %, quinta 13 %, ottava 22 %, terza 6 %, settima 6 %, quarta 3 %
             sull'uno la fondamentale 84 %   sui tempi fondamentale, quinta o ottava 74 %
             fuori dai tempi: l'ottava della fondamentale del tempo 43 % (entro 4 sedicesimi), la nota del tempo 12 %
             nell'ultimo ottavo una nota che riporta a casa 47 %   tenute 23 % (al massimo 1 sedicesimo)

PIANO
  una famiglia (40 % dei semi)
    sempre   x..x..x.x..x..x.
    pesi     ..........2....2   densità 0-47 %   tutti 'o'
    battute 2 e 4: 20 % delle scelte rifatte
  una famiglia (30 % dei semi)
    sempre   ..x...x...x...x.
    pesi     ...1...3...5.2.2   densità 24-78 %   tutti 'o'
    battute 2 e 4: 25 % delle scelte rifatte
  una famiglia (30 % dei semi)
    sempre   ..x..x.x..x..x.x
    pesi     ........45.5....   densità 24-78 %   tutti 'o'
    battute 2 e 4: 20 % delle scelte rifatte
    accordi  triade 10 %, settima 90 %   lo stesso tipo per tutto il pattern 84 %   tenuti 59 % (al massimo 1 sedicesimo)

PAD
    sempre   x...............
    pesi     ......7.3.....3.   densità 31-78 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 25 % delle scelte rifatte
    accordi  triade 25 %, settima 75 %   lo stesso tipo per tutto il pattern 78 %   tenuti sempre

VOX
    pesi     ..9422.2..9.8.3.   densità 59-100 %   fino a peso 2: 'o'
    battute 2 e 4: 50 % delle scelte rifatte
    motivo   scala: pentatonica 90 %, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale
             poggia su: la fondamentale 33 %, la quinta 50 %, la terza 17 %
             profilo: scende 25 %, sale 10 %, arco 20 %, due note alternate 45 %   ampiezza 1-2 gradini
             ripete la nota del suo tempo 43 %   un gradino fuori posto 20 %   un salto di due 4 %
             nota dell'accordo: sull'uno sempre, sui tempi 86 %, fuori dai tempi 66 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 59 %   tenute 23 %

ARP
  una famiglia (50 % dei semi)
    sempre   x.x.x.x.x.x.x.x.
    battute 2 e 4: 15 % delle scelte rifatte
  una famiglia (50 % dei semi)
    classi   tempi sempre 'x'   e sempre 'x'   & sempre 'x'   a sempre 'x'
             un colpo della classe manca: 4 %
    battute 2 e 4: 15 % delle scelte rifatte

LA PROGRESSIONE
    scala          minore 45 %, dorica 35 %, maggiore 12 %, misolidia 8 %
    accordi        uno 5 %, due 35 %, tre 10 %, quattro 50 %
    durata         1 battuta 45 %, 2 battute 45 %, 4 battute 10 %
    parte da casa  85 %
    la fondamentale si muove di  un grado sopra 7 %, una terza sopra 13 %, una quarta sopra 28 %, una quinta sopra 11 %, una terza sotto 20 %, un grado sotto 20 %
    l'ultimo di tre o quattro    II 3 %, III 10 %, IV 22 %, V 25 %, VI 15 %, VII 25 %
    colori         triade 8 %, settima 50 %, nona 27 %, sus4 8 %, sus2 3 %, sesta 4 %   lo stesso per tutti 60 %
    entra          sulla battuta 50 %, un sedicesimo prima 25 %, un ottavo prima 25 %
```
<!-- /regole -->

### DRUM AND BASS (173 BPM)

Il **two-step**: la cassa sull'uno e sul levare del 3 (i sedicesimi 1 e 11), il rullante sul 2 e sul 4 (5 e 13). In
mezzo i ghost del rullante; nell'ultima battuta l'ultimo rullante arriva un ottavo in ritardo, oppure lo seguono due
colpi rapidi. L'hat in ottavi (i sedicesimi a classi), il ride sui tempi o sui levare, lo shaker in sedicesimi, la
percussione di soli ghost oppure un ciclo di tre. Il **sub** parte con la cassa e tiene: i suoi colpi cadono dove cade
la cassa. Il basso ha poche note, sull'uno e a metà battuta. I pad lunghi. Il lead ha due ritmi: il 3+3+2
(`x..x..x.x`) oppure gli ottavi; quasi sempre sulla pentatonica.

L'armonia: **due o quattro accordi**, di due battute (o quattro). Quasi sempre in minore; le fondamentali vanno verso
il sesto e il settimo grado. Settime e none.

<!-- regole DNB -->
```text
KICK
    sempre   X.........x.....
    pesi     ..22...12..35113   densità 12-67 %   fino a peso 2: 'o'
    battute 2 e 4: 45 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

SNARE
    sempre   ....X.......X...
    pesi     .323.3.924.9.425   densità 35-90 %   tutti 'g'
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura l'ultimo rullante un ottavo in ritardo, oppure due colpi rapidi dopo di lui

HAT
    sempre   x.x.x.x.x.x.x.x.
    classi   e 16 % 'o'   a 51 % 'x'   a energia 0 il 24 % di queste
             un colpo della classe manca: 9 %
    battute 2 e 4: 20 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)

RIDE
  una famiglia (60 % dei semi)
    sempre   x...x...x...x...
    classi   & 70 % 'o'   a 59 % 'x'   a energia 0 il 43 % di queste
             un colpo della classe manca: 6 %
    battute 2 e 4: 15 % delle scelte rifatte
  una famiglia (40 % dei semi)
    sempre   ..x...x...x...x.
    pesi     ...3...3...4...2   densità 16-63 %   tutti 'o'
    battute 2 e 4: 15 % delle scelte rifatte

SHAKER
    classi   tempi sempre 'x'   e sempre 'o'   & sempre 'x'   a sempre 'o'
             un colpo della classe manca: 21 %
    battute 2 e 4: 15 % delle scelte rifatte

PERC
  una famiglia (65 % dei semi)
    pesi     29.39.415446.212   densità 43-96 %   tutti 'g'
    battute 2 e 4: 35 % delle scelte rifatte
  una famiglia (35 % dei semi)
    pesi     ..........3....3   densità 16-63 %   tutti 'o'
    ciclo    un colpo ogni 3 sedicesimi, oltre le stanghette (100 % dei semi); sotto energia 40 uno ogni 6
    battute 2 e 4: 20 % delle scelte rifatte

SUB
    sempre   X...............
    pesi     ......3.31b...7.   densità 59-100 %
    più probabile dove suona il kick (+5)   mai due colpi su sedicesimi vicini   battute 2 e 4: 30 % delle scelte rifatte
    note     fondamentale 60 %, quinta 14 %, ottava 8 %, terza 9 %, settima 6 %, quarta 3 %
             sull'uno la fondamentale 96 %   sui tempi fondamentale, quinta o ottava 59 %
             fuori dai tempi: la nota del tempo 16 %
             nell'ultimo ottavo una nota che riporta a casa 31 %   tenute sempre, fino a 3 sedicesimi di pausa prima della nota dopo

BASS
    sempre   X...............
    pesi     ...1.132a.32..52   densità 47-94 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 35 % delle scelte rifatte
    note     fondamentale 66 %, quinta 12 %, ottava 3 %, terza 10 %, settima 6 %, quarta 3 %
             sull'uno la fondamentale 92 %   sui tempi fondamentale, quinta o ottava 66 %
             fuori dai tempi: la nota del tempo 23 %
             nell'ultimo ottavo una nota che riporta a casa 23 %   tenute 35 % (al massimo 3 sedicesimi)

PAD
    sempre   x...............
    pesi     ..1...539.1....1   densità 47-94 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 30 % delle scelte rifatte
    accordi  triade 35 %, settima 65 %   lo stesso tipo per tutto il pattern 74 %   tenuti sempre

LEAD
  una famiglia (55 % dei semi)
    sempre   x..x..x.x.......
    pesi     .......2....2323   densità 12-63 %   tutti 'o'
    battute 2 e 4: 35 % delle scelte rifatte
  una famiglia (45 % dei semi)
    sempre   x.x.x.x.x.x.x.x.
    pesi     ...3...3.3.3...3   densità 0-55 %   tutti 'o'
    battute 2 e 4: 25 % delle scelte rifatte
    motivo   scala: pentatonica 74 %, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale
             poggia su: la fondamentale 40 %, la quinta 33 %, la terza 27 %
             profilo: scende 40 %, sale 15 %, arco 30 %, due note alternate 15 %   ampiezza 2-4 gradini
             ripete la nota del suo tempo 23 %   un gradino fuori posto 23 %   un salto di due 8 %
             nota dell'accordo: sull'uno sempre, sui tempi 78 %, fuori dai tempi 20 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 74 %   tenute 66 %

LA PROGRESSIONE
    scala          minore 70 %, dorica 15 %, frigia 10 %, minore armonica 5 %
    accordi        uno 10 %, due 40 %, tre 5 %, quattro 45 %
    durata         1 battuta 5 %, 2 battute 55 %, 4 battute 35 %, 8 battute 5 %
    parte da casa  90 %
    la fondamentale si muove di  un grado sopra 5 %, una terza sopra 17 %, una quarta sopra 15 %, una quinta sopra 10 %, una terza sotto 29 %, un grado sotto 24 %
    l'ultimo di tre o quattro    II 3 %, III 12 %, IV 18 %, V 15 %, VI 25 %, VII 27 %
    colori         triade 15 %, settima 45 %, nona 25 %, sus4 3 %, sus2 10 %, sesta 2 %   lo stesso per tutti 55 %
    entra          sulla battuta 85 %, un ottavo prima 15 %
```
<!-- /regole -->

### DUBSTEP (140 BPM)

Il **mezzo tempo**: la cassa sull'uno, il rullante sul 3 (il sedicesimo 9), mai sul 2 e sul 4. Le frasi sono di due
battute: la 2 e la 4 rifanno più della metà delle scelte. Gli hat sono radi (sul 2 e sul 4) oppure in ottavi; le
chiusure sono due sedicesimi o una rullata in tre. Il **sub** sta sull'uno e tiene note lunghe. Il basso ha colpi con
le rullate (due, tre o quattro in un sedicesimo): è il wobble scritto come nota ribattuta, come lo scrive la libreria.
Il lead: poche note lunghe, che scendono, sulla pentatonica.

L'armonia è quasi ferma: **un accordo solo** una volta su due, altrimenti due, lunghi. Minore, frigia, minore armonica;
triadi.

<!-- regole DUBSTEP -->
```text
KICK
    sempre   X...............
    pesi     .11..15331612.13   densità 27-82 %   fino a peso 3: 'o'
    battute 2 e 4: 60 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

SNARE
    sempre   ........X.......
    pesi     1211.133..21.314   densità 24-75 %   tutti 'g'
    battute 2 e 4: 60 % delle scelte rifatte
    chiusura due sedicesimi, o una rullata in tre, prima dell'uno (da energia 25)

HAT
  una famiglia (75 % dei semi)
    sempre   ....x.......x...
    pesi     1.41.1412242.175   densità 12-59 %   fino a peso 1: 'o'
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura due sedicesimi, o una rullata in tre, prima dell'uno (da energia 25)
  una famiglia (25 % dei semi)
    sempre   x.x.x.x.x.x.x.x.
    classi   e 12 % 'o'   a 23 % 'o'   a energia 0 il 24 % di queste
             un colpo della classe manca: 10 %
    battute 2 e 4: 30 % delle scelte rifatte
    chiusura due sedicesimi, o una rullata in tre, prima dell'uno (da energia 25)

PERC
    pesi     ...73141..86.243   densità 39-92 %   fino a peso 2: 'o'
    battute 2 e 4: 50 % delle scelte rifatte

SUB
    sempre   X...............
    pesi     ......8.6.a.5...   densità 47-90 %
    più probabile dove suona il kick (+5)   mai due colpi su sedicesimi vicini   battute 2 e 4: 45 % delle scelte rifatte
    note     fondamentale 55 %, quinta 12 %, ottava 15 %, terza 6 %, settima 7 %, seconda 5 %
             sull'uno la fondamentale 98 %   sui tempi fondamentale, quinta o ottava 66 %
             fuori dai tempi: l'ottava della fondamentale del tempo 16 % (entro 6 sedicesimi), la nota del tempo 12 %
             nell'ultimo ottavo una nota che riporta a casa 35 %   tenute sempre, fino a 2 sedicesimi di pausa prima della nota dopo

BASS
    sempre   x...............
    pesi     .1.8..51b1..b221   densità 63-100 %   fino a peso 2: 'o'
    battute 2 e 4: 40 % delle scelte rifatte
    note     fondamentale 68 %, quinta 8 %, ottava 12 %, terza 4 %, settima 2 %, quarta 6 %
             sull'uno la fondamentale 94 %   sui tempi fondamentale, quinta o ottava 74 %
             fuori dai tempi: l'ottava della fondamentale del tempo 23 % (entro 6 sedicesimi), la nota del tempo 27 %
             nell'ultimo ottavo una nota che riporta a casa 16 %   rullate (2, 3 o 4 in un sedicesimo) 47 %

PAD
    sempre   x...............
    pesi     ......1.31......   densità 16-55 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 50 % delle scelte rifatte
    accordi  triade 60 %, settima 40 %   lo stesso tipo per tutto il pattern 86 %   tenuti sempre

LEAD
  una famiglia (55 % dei semi)
    sempre   x...x.x.x.......
    pesi     ............2.23   densità 8-59 %   tutti 'o'
    battute 2 e 4: 40 % delle scelte rifatte
  una famiglia (45 % dei semi)
    sempre   x...............
    pesi     ..7936a3a37.9.64   densità 59-100 %   fino a peso 3: 'o'
    battute 2 e 4: 35 % delle scelte rifatte
    motivo   scala: pentatonica 70 %, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale
             poggia su: la fondamentale 35 %, la quinta 35 %, la terza 29 %
             profilo: scende 45 %, sale 10 %, arco 25 %, due note alternate 20 %   ampiezza 2-4 gradini
             ripete la nota del suo tempo 35 %   un gradino fuori posto 20 %   un salto di due 6 %
             nota dell'accordo: sull'uno sempre, sui tempi 78 %, fuori dai tempi 27 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 78 %   tenute 78 %

LA PROGRESSIONE
    scala          minore 55 %, frigia 35 %, minore armonica 10 %
    accordi        uno 45 %, due 40 %, tre 5 %, quattro 10 %
    durata         1 battuta 5 %, 2 battute 35 %, 4 battute 45 %, 8 battute 15 %
    parte da casa  97 %
    la fondamentale si muove di  un grado sopra 21 %, una terza sopra 6 %, una quarta sopra 10 %, una quinta sopra 8 %, una terza sotto 29 %, un grado sotto 27 %
    l'ultimo di tre o quattro    II 20 %, III 8 %, IV 10 %, V 12 %, VI 25 %, VII 25 %
    colori         triade 65 %, settima 20 %, nona 3 %, sus4 2 %, sus2 10 %   lo stesso per tutti 80 %
    entra          sulla battuta 100 %
```
<!-- /regole -->

### REGGAETON (101 BPM)

Il **dembow**: la cassa in quattro, sempre; il rullante su `...x..x....x..x.` a ogni energia, con gli accenti
sull'ultimo sedicesimo dell'1 e del 3 (oppure, una famiglia su quattro, sui due colpi dopo). L'hat in ottavi, e i
sedicesimi entrano con l'energia; lo shaker in sedicesimi (quello dell'amapiano); il rim con i primi due colpi del
rullante, oppure sulle "e"; le congas sul tresillo (3+3+2); un timbale ogni tanto. Il basso sta con la cassa e prende
i levare del tresillo (sull'ultimo sedicesimo dell'1 e del 3); il **log drum** dell'amapiano scivola fra le note,
mai due colpi vicini. Gli accordi sul tresillo, il lead in 3+3+2.

L'armonia: **quattro accordi**, uno a battuta, quasi sempre (i VI III VII); le fondamentali scendono di una terza o
salgono di una quinta o di una quarta. In minore; triadi, qualche settima e qualche nona (l'amapiano).

<!-- regole REGGAETON -->
```text
KICK
    sempre   X...X...X...X...
    pesi     ...2...1..13..22   densità 8-63 %   tutti 'o'
    battute 2 e 4: 30 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

SNARE
  una famiglia (75 % dei semi)
    sempre   ...X..x....X..x.
    pesi     ..3....5.23....6   densità 16-75 %   fino a peso 3: 'g'
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi
  una famiglia (25 % dei semi)
    sempre   ...x..X....x..X.
    pesi     ..3..2....35...4   densità 12-71 %   fino a peso 3: 'g'
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi

HAT
  una famiglia (60 % dei semi)
    sempre   ..x...x...x...x.
    classi   tempi 78 % 'x'   e 20 % 'o'   a 55 % 'o'   a energia 0 il 16 % di queste
             un colpo della classe manca: 8 %
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)
  una famiglia (40 % dei semi)
    sempre   ..x...x...x...x.
    pesi     .......4.......5   densità 12-67 %   tutti 'o'
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)

SHAKER
    classi   tempi 86 % 'x'   e 62 % 'o'   & sempre 'x'   a 78 % 'o'   (insieme)   a energia 0 il 12 % di queste
             un colpo della classe manca: 16 %
    battute 2 e 4: 15 % delle scelte rifatte

RIM
  una famiglia (60 % dei semi)
    pesi     ...c..c...54..6.   densità 20-86 %
    battute 2 e 4: 30 % delle scelte rifatte
  una famiglia (40 % dei semi)
    pesi     ..c..3....c..34.   densità 16-82 %   fino a peso 3: 'o'
    battute 2 e 4: 30 % delle scelte rifatte

CONGA
  una famiglia (60 % dei semi)
    sempre   x...............
    pesi     ...9..c.7..8..9.   densità 16-90 %
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura la seconda metà si riempie
  una famiglia (40 % dei semi)
    sempre   ...X............
    pesi     ..4.3.a....7.78.   densità 16-86 %   fino a peso 3: 'o'
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura la seconda metà si riempie

PERC
    pesi     ...2..9...3.3.91   densità 16-86 %   fino a peso 3: 'o'
    battute 2 e 4: 30 % delle scelte rifatte
    chiusura la seconda metà si riempie

BASS
  una famiglia (65 % dei semi)
    sempre   X...............
    pesi     ...a..3.f..a..32   densità 16-86 %
    più probabile dove suona il kick (+5)   battute 2 e 4: 30 % delle scelte rifatte
  una famiglia (35 % dei semi)
    sempre   X...............
    pesi     ......9.f.....9.   densità 16-82 %
    più probabile dove suona il kick (+5)   battute 2 e 4: 30 % delle scelte rifatte
    note     fondamentale 65 %, quinta 14 %, ottava 12 %, terza 6 %, settima 3 %
             sull'uno la fondamentale 94 %   sui tempi fondamentale, quinta o ottava 78 %
             fuori dai tempi: l'ottava della fondamentale del tempo 23 % (entro 3 sedicesimi), la nota del tempo 27 %
             nell'ultimo ottavo una nota che riporta a casa 35 %   tenute 23 % (al massimo 3 sedicesimi)

LOG DRUM
    sempre   X...............
    pesi     ...5..5...9..9.2   densità 20-90 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 40 % delle scelte rifatte
    note     fondamentale 45 %, quinta 18 %, ottava 14 %, terza 12 %, settima 6 %, quarta 3 %, seconda 2 %
             sull'uno la fondamentale 86 %   sui tempi fondamentale, quinta o ottava 59 %
             fuori dai tempi: l'ottava della fondamentale del tempo 31 % (entro 3 sedicesimi), la nota del tempo 8 %
             nell'ultimo ottavo una nota che riporta a casa 43 %   tenute 47 % (al massimo 4 sedicesimi), fino a 1 sedicesimo di pausa prima della nota dopo

CHORD
  una famiglia (60 % dei semi)
    sempre   x...............
    pesi     ...9..9.6..8..8.   densità 16-82 %
    battute 2 e 4: 30 % delle scelte rifatte
  una famiglia (40 % dei semi)
    sempre   x...............
    pesi     ......9...9.....   densità 12-67 %
    mai due colpi su sedicesimi vicini   battute 2 e 4: 30 % delle scelte rifatte
    accordi  triade 70 %, settima 30 %   lo stesso tipo per tutto il pattern 86 %   tenuti 23 %

LEAD
  una famiglia (55 % dei semi)
    sempre   x...............
    pesi     ...c..c...7..7.3   densità 12-75 %   tutti 'o'
    battute 2 e 4: 35 % delle scelte rifatte
  una famiglia (45 % dei semi)
    sempre   x...............
    pesi     ..7...8...7...8.   densità 16-82 %   tutti 'o'
    battute 2 e 4: 35 % delle scelte rifatte
    motivo   scala: pentatonica 78 %, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale
             poggia su: la fondamentale 40 %, la quinta 33 %, la terza 27 %
             profilo: scende 35 %, sale 15 %, arco 30 %, due note alternate 20 %   ampiezza 2-4 gradini
             ripete la nota del suo tempo 31 %   un gradino fuori posto 20 %   un salto di due 6 %
             nota dell'accordo: sull'uno sempre, sui tempi 82 %, fuori dai tempi 27 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 74 %   tenute 31 %

LA PROGRESSIONE
    scala          minore 65 %, dorica 15 %, frigia 5 %, maggiore 5 %, minore armonica 10 %
    accordi        uno 5 %, due 20 %, tre 5 %, quattro 70 %
    durata         1 battuta 75 %, 2 battute 25 %
    parte da casa  85 %
    la fondamentale si muove di  un grado sopra 5 %, una terza sopra 5 %, una quarta sopra 20 %, una quinta sopra 30 %, una terza sotto 25 %, un grado sotto 15 %
    l'ultimo di tre o quattro    II 5 %, III 10 %, IV 15 %, V 15 %, VI 25 %, VII 30 %
    colori         triade 70 %, settima 18 %, nona 8 %, sus2 4 %   lo stesso per tutti 75 %
    entra          sulla battuta 85 %, un sedicesimo prima 15 %
```
<!-- /regole -->

### BALANI (170 BPM)

La musica del **balafon** delle feste di strada di Bamako, veloce. La cassa in quattro, il clap sul 2 e sul 4 con i
suoi ghost in fondo alla battuta. L'hat sui levare o in ottavi, lo shaker in sedicesimi con un buco su una "e" ogni
tanto. Il 3-3-2 del djembe sulla percussione e sulla conga bassa; i tom che rullano verso la frase dopo. Il basso
sull'1 e sul 3, oppure sul tresillo. Il **BALAFON**: l'ostinato in sedicesimi, le due mani a turno (due note che si
alternano, sulla pentatonica), oppure le sue figure sui tempi; le note sono battute, mai tenute. Le grida dell'MC. Gli
accordi (se li chiedi: la band non li ha) sui levare.

L'armonia: **un accordo solo, o due** (I - V, I - IV), di due o quattro battute; la fondamentale sale di una quarta o
di una quinta. Maggiore o misolidia; triadi.

<!-- regole BALANI -->
```text
KICK
    sempre   X...X...X...X...
    pesi     ......3....4..23   densità 8-67 %   fino a peso 3: 'o'
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

CLAP
    sempre   ....X.......X...
    pesi     .......5.....236   densità 16-78 %   tutti 'g'
    battute 2 e 4: 30 % delle scelte rifatte
    chiusura un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi

HAT
  una famiglia (55 % dei semi)
    sempre   ..x...x...x...x.
    classi   tempi 35 % 'x'   e 23 % 'o'   a 78 % 'x'   a energia 0 il 31 % di queste
             un colpo della classe manca: 8 %
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)
  una famiglia (45 % dei semi)
    sempre   x.x.x.x.x.x.x.x.
    classi   e 20 % 'o'   a 90 % 'x'   a energia 0 il 47 % di queste
             un colpo della classe manca: 8 %
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)

SHAKER
    classi   tempi sempre 'x'   e 43 % 'o'   & sempre 'x'   a sempre 'o'   (insieme)   a energia 0 il 63 % di queste
             un colpo della classe manca: 12 %
    battute 2 e 4: 15 % delle scelte rifatte

PERC
    pesi     ..8..8.7..8..8.7   densità 27-90 %
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura la seconda metà si riempie

CONGA
  una famiglia (60 % dei semi)
    sempre   X...............
    pesi     ..89..8.8.89..8.   densità 24-86 %
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura la seconda metà si riempie
  una famiglia (40 % dei semi)
    sempre   X...............
    pesi     ...9..9...8..9..   densità 20-78 %
    battute 2 e 4: 35 % delle scelte rifatte
    chiusura la seconda metà si riempie

TOM
    pesi     ......6.....4477   densità 12-63 %
    battute 2 e 4: 50 % delle scelte rifatte
    chiusura la seconda metà si riempie

BASS
  una famiglia (70 % dei semi)
    sempre   X.......x.......
    pesi     ...4..6...4...6.   densità 24-82 %
    più probabile dove suona il kick (+5)   battute 2 e 4: 35 % delle scelte rifatte
  una famiglia (30 % dei semi)
    sempre   X...............
    pesi     ...9..9...8..9..   densità 24-82 %
    battute 2 e 4: 35 % delle scelte rifatte
    note     fondamentale 60 %, quinta 20 %, ottava 10 %, terza 5 %, quarta 5 %
             sull'uno la fondamentale 94 %   sui tempi fondamentale, quinta o ottava 78 %
             fuori dai tempi: l'ottava della fondamentale del tempo 20 % (entro 3 sedicesimi), la nota del tempo 23 %
             nell'ultimo ottavo una nota che riporta a casa 35 %   tenute 16 % (al massimo 2 sedicesimi)

BALAFON
  una famiglia (70 % dei semi)
    classi   tempi sempre 'x'   e 78 % 'o'   & sempre 'x'   a sempre 'o'   a energia 0 il 71 % di queste
             un colpo della classe manca: 12 %
    battute 2 e 4: 25 % delle scelte rifatte
  una famiglia (30 % dei semi)
    sempre   x.x.x...........
    pesi     ......7.9.8.9.76   densità 24-86 %   tutti 'o'
    battute 2 e 4: 30 % delle scelte rifatte
    motivo   scala: pentatonica 94 %, altrimenti tutte e sette le note; fino a 15 semitoni sopra la fondamentale
             poggia su: la fondamentale 40 %, la quinta 33 %, la terza 27 %
             profilo: scende 15 %, sale 15 %, arco 20 %, due note alternate 50 %   ampiezza 3-5 gradini
             ripete la nota del suo tempo 12 %   un gradino fuori posto 23 %   un salto di due 10 %
             nota dell'accordo: sull'uno sempre, sui tempi 78 %, fuori dai tempi 35 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 59 %   tenute 0 %

VOX
    sempre   x...............
    pesi     ...4......7.....   densità 16-67 %
    battute 2 e 4: 40 % delle scelte rifatte
    motivo   scala: pentatonica 86 %, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale
             poggia su: la fondamentale 40 %, la quinta 40 %, la terza 20 %
             profilo: scende 40 %, sale 10 %, arco 20 %, due note alternate 30 %   ampiezza 1-2 gradini
             ripete la nota del suo tempo 47 %   un gradino fuori posto 16 %   un salto di due 2 %
             nota dell'accordo: sull'uno sempre, sui tempi 86 %, fuori dai tempi 59 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 59 %   tenute 47 %

CHORD
    sempre   ..x...x...x...x.
    battute 2 e 4: 30 % delle scelte rifatte
    accordi  triade 90 %, settima 5 %, quinta vuota 5 %   lo stesso tipo per tutto il pattern 90 %   tenuti 0 %

LA PROGRESSIONE
    scala          maggiore 65 %, misolidia 35 %
    accordi        uno 40 %, due 45 %, tre 5 %, quattro 10 %
    durata         1 battuta 5 %, 2 battute 35 %, 4 battute 45 %, 8 battute 15 %
    parte da casa  95 %
    la fondamentale si muove di  un grado sopra 5 %, una terza sopra 5 %, una quarta sopra 40 %, una quinta sopra 35 %, una terza sotto 10 %, un grado sotto 5 %
    l'ultimo di tre o quattro    II 5 %, III 5 %, IV 35 %, V 40 %, VI 15 %
    colori         triade 85 %, settima 5 %, sus4 5 %, sus2 5 %   lo stesso per tutti 90 %
    entra          sulla battuta 100 %
```
<!-- /regole -->

### FREE

Nessun genere. Una cassa che sta sull'uno e si appoggia ai tempi, un rullante che cerca il 2 e il 4, un hat a classi
(tempi, levare, sedicesimi), una percussione fuori dai tempi con il suo ciclo, un basso che parte dall'uno, accordi,
un arpeggio, un motivo. Niente swing e niente GROOVE di un genere. La progressione usa qualunque scala e qualunque
movimento della tonalità. Sull'FM-1 il tempo resta quello che hai (i programmi per ascoltare al computer usano 120
BPM). Si usa con SOURCE FREE (SEQ 8 K1), o con GENRE FREE: vedi "Liberi dal genere", più sopra.

Una parte che uno stile non ha (un rullante in TECHNO, un lead in HOUSE) viene fatta con le regole che lo stile ha per
la sua famiglia, e se non ne ha con quelle di FREE.

<!-- regole FREE -->
```text
KICK
    sempre   X...............
    pesi     .1329132a1339143   densità 16-86 %   fino a peso 3: 'o'
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura levare del kick sull'ultimo sedicesimo (da energia 25; da 75 anche il penultimo)

SNARE
    pesi     1122b1233223b233   densità 31-90 %   fino a peso 3: 'g'
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura un ghost, un colpo e un accento che rulla sugli ultimi tre sedicesimi

HAT
    classi   tempi 59 % 'x'   e 20 % 'o'   & 78 % 'x'   a 35 % 'o'   a energia 0 il 39 % di queste
             un colpo della classe manca: 12 %
    battute 2 e 4: 25 % delle scelte rifatte
    chiusura gli ultimi due sedicesimi pieni (da energia 30; da 60 l'ultimo rulla)

PERC
    pesi     2435246524353555   densità 16-67 %   fino a peso 3: 'o'
    ciclo    un colpo ogni 3 sedicesimi, oltre le stanghette (33 % dei semi); sotto energia 40 uno ogni 6
    battute 2 e 4: 40 % delle scelte rifatte
    chiusura la seconda metà si riempie

BASS
    sempre   x...............
    pesi     .264626372546273   densità 24-86 %
    battute 2 e 4: 35 % delle scelte rifatte
    note     fondamentale 40 %, quinta 15 %, ottava 12 %, terza 10 %, settima 8 %, quarta 6 %, seconda 5 %, sesta 4 %
             sull'uno la fondamentale 70 %   sui tempi fondamentale, quinta o ottava 55 %
             fuori dai tempi: l'ottava della fondamentale del tempo 16 % (entro 2 sedicesimi), la nota del tempo 12 %
             nell'ultimo ottavo una nota che riporta a casa 27 %   tenute 31 % (al massimo 2 sedicesimi)

CHORD
    sempre   x...............
    pesi     ..33415261334242   densità 12-63 %
    battute 2 e 4: 35 % delle scelte rifatte
    accordi  triade 50 %, settima 40 %, quinta vuota 10 %   lo stesso tipo per tutto il pattern 59 %   tenuti 47 % (al massimo 2 sedicesimi)

ARP
    pesi     8264726482647364   densità 24-90 %   fino a peso 3: 'o'
    battute 2 e 4: 35 % delle scelte rifatte

LEAD
    sempre   x...............
    pesi     .156517271545253   densità 35-94 %   fino a peso 1: 'o'
    battute 2 e 4: 35 % delle scelte rifatte
    motivo   scala: pentatonica 43 %, altrimenti tutte e sette le note; fino a 15 semitoni sopra la fondamentale
             poggia su: la fondamentale 50 %, la quinta 33 %, la terza 17 %
             profilo: scende 25 %, sale 25 %, arco 30 %, due note alternate 20 %   ampiezza 2-5 gradini
             ripete la nota del suo tempo 20 %   un gradino fuori posto 27 %   un salto di due 12 %
             nota dell'accordo: sull'uno sempre, sui tempi 62 %, fuori dai tempi 16 %
             la battuta 2 chiude aperta (sulla quinta) e l'ultima a casa 51 %   tenute 31 %

LA PROGRESSIONE
    scala          minore 25 %, dorica 15 %, frigia 15 %, maggiore 25 %, misolidia 10 %, minore armonica 10 %
    accordi        uno 10 %, due 30 %, tre 20 %, quattro 40 %
    durata         1 battuta 30 %, 2 battute 40 %, 4 battute 25 %, 8 battute 5 %
    parte da casa  70 %
    la fondamentale si muove di  un grado sopra 17 %, una terza sopra 17 %, una quarta sopra 17 %, una quinta sopra 17 %, una terza sotto 16 %, un grado sotto 16 %
    l'ultimo di tre o quattro    II 16 %, III 16 %, IV 16 %, V 16 %, VI 17 %, VII 17 %
    colori         triade 30 %, settima 25 %, nona 15 %, sus4 10 %, sus2 10 %, sesta 10 %   lo stesso per tutti 30 %
    entra          sulla battuta 70 %, un sedicesimo prima 15 %, un ottavo prima 15 %
```
<!-- /regole -->

## Gli strumenti

```sh
# una band, o una parte, come testo: STILE SEME [VARIAZIONE QUANTO ENERGIA LUNGHEZZA] [PARTE ...]
cc -std=c11 -O2 -Ifirmware/src tools/theory/sagga_theory.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o build/sagga_theory
build/sagga_theory REGGAETON 6                  # lo stile: il nome di un genere dell'FM-1, il suo numero, o FREE
build/sagga_theory "UK GARAGE" 1 2 60 80 64 BASS VOX   # la variazione 2 al 60 %, energia 80, quattro battute

python3 tools/theory/gen_rules.py               # rifà le regole contate dalla libreria (e TEORIA-GENERI.md)
python3 tools/theory/compare.py 100 TRANCE      # i motori contro la libreria, parte per parte
python3 tools/theory/regole.py --write docs/TEORIA.md   # i blocchi "le regole" di questo foglio
python3 tools/theory/render.py build/teoria --styles all --seeds 1   # un MIDI e un progetto per genere, da ascoltare
sh tests/run_sagga_tests.sh                     # tutti i test
```

## Fonti

I modelli:

* [Mutable Instruments Grids, il manuale](https://pichenette.readthedocs.io/en/latest/modules/grids/manual/)
* [Generative Electronica Research Project (GERP, GESMI)](https://metacreation.net/generative-electronica-research-project/) e
  [Eigenfeldt, Pasquier: Considering Vertical and Horizontal Context in Corpus-based Generative Electronic Dance Music](https://econtact.ca/14_4/eigenfeldt_generativeelectronica.html)
* [Sioros, Guedes: kin.rhythmicator (NIME 2011)](https://nime.org/proc/sioros2011)
* [Sound On Sound: i Session Players di Logic Pro](https://www.soundonsound.com/techniques/logic-pro-synth-bass-session-player)
* [Torso Electronics T-1, il manuale](https://manuals.online/torso-electronics/recording-equipment/t-1/user-manual/11d0p)
* [Conductive Labs NDLR, una recensione](https://synthandsoftware.com/2020/08/conductive-labs-ndlr-review/)
* [Sound On Sound: Music Thing Modular Turing Machine](https://www.soundonsound.com/reviews/music-thing-modular-turing-machine-mkii)

I generi scritti a mano:

* [Attack Magazine, Beat Dissected: Rolling Techno](https://www.attackmagazine.com/technique/beat-dissected/rolling-techno/)
* [Attack Magazine, The Theory of Techno: Parallel Chord Stabs](https://www.attackmagazine.com/technique/tutorials/the-theory-of-techno-parallel-chord-stabs/)
* [Attack Magazine, Passing Notes: Deep House Chords](https://www.attackmagazine.com/technique/passing-notes/passing-notes-deep-house-chords/)
* [Attack Magazine, Beat Dissected: Raw Drum & Bass](https://www.attackmagazine.com/technique/beat-dissected/raw-drum-bass/)
* [MusicRadar, How to program 6 different jungle and drum 'n' bass grooves](https://www.musicradar.com/how-to/how-to-program-6-different-jungle-and-drum-n-bass-grooves)
* [Sound On Sound, Dubstep Drums](https://www.soundonsound.com/techniques/dubstep-drums)
* La libreria di SAGGA SEQ: `tools/hub/patterns/`.
