# SAGGA SEQ 0.23 - i motori THEORY

Questo foglio spiega i motori THEORY: cosa sono, come si usano, cosa fa ognuno e perché, e a quali strumenti che
esistono già somigliano. In fondo ci sono i dettagli, per chi li vuole.

Le regole dei 21 generi contati dalla libreria sono in un foglio a parte: `TEORIA-GENERI.md`.

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
| nessun genere | **SEQ 8 K1 su FREE**: BAND dà una band di otto parti fatta solo con il metro, e BEAT, KIT, i dadi e DICE PROG lavorano senza genere. Vedi "Liberi dal genere". |
| parti di quattro battute | **SAVE 2 K4**, LIBRARY LENGTH 64. Con 16 la parte è una battuta, con 32 due (la seconda risponde alla prima), con 64 quattro, e l'ultima ha la chiusura. |

Sul **grid**, nella vista BEAT, la terza riga: i pad da 11 a 16 scelgono il seme fra sei, il pad 10 passa ai sei dopo.
Con SHIFT tenuto vedi il pattern che quel seme darebbe.

Sul **tablet**, nella pagina SAGGA Live, c'è una riga nuova: SOURCE (LIBRARY, THEORY, FREE), NEXT SEED, SEED,
VARIATION. BEAT, COOK e DICE della pagina usano i motori quando SOURCE è su THEORY o su FREE.

Nell'**editor del Pi** le tracce il cui pattern è fatto dai motori hanno un segno con il seme (◆8). Se lì svuoti o
sposti un pattern, i motori lo dimenticano: da quel momento è un pattern scritto a mano.

Tre cose da sapere:

* L'energia **aggiunge soltanto**: salendo, i colpi che c'erano restano dove sono e le note tengono la loro altezza.
* Uno step che scrivi a mano in un pattern dei motori **resta**, anche quando l'energia cambia.
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

E i controlli sul motore (36 milioni, su 150 semi per ognuno dei 26 stili): una parte non è mai vuota; salendo di
energia nessun colpo si perde; una nota che resta tiene la sua altezza (ne cambiano 7 su diecimila, le ultime di un
motivo); quello che **ogni** pattern della libreria suona, i motori lo suonano sempre.

## Cosa non sanno fare

* **Le parti non si ascoltano fra loro**, a parte la cassa: il rumble la evita, il sub la cerca. Il basso non lascia
  spazio al lead, non c'è botta e risposta fra due parti.
* **Solo sedicesimi in quattro quarti.** Le terzine ci sono solo come rullata. Lo swing e il GROOVE sono quelli che
  l'FM-1 dà al genere.
* **Una frase è di due battute.** Con quattro battute la terza ripete la prima e la quarta risponde come la seconda, con
  la chiusura. I break lunghi quattro battute della jungle diventano frasi di due.
* **Un motivo è una voce sola** e non sa quale accordo sta suonando: lo sposta FOLLOW.
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

Una parte dura una, due o quattro battute (LIBRARY LENGTH). Le battute 1 e 3 sono la stessa battuta; la 2 e la 4
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
