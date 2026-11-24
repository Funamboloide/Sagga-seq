# SCENA e VARIAZIONI per la Ksoloti Gills

In questa cartella:

* **SCENA** (`scena.axp`, `scena_aux.axp`): una manopola dal break-down al build-up. È la prima parte qui sotto.
* **VARIAZIONI** (`figo_scena.axp`, `figo_scena_aux.axp`): FIGO e SCENA insieme in un solo oggetto, da sole sulla
  Gills; e accanto a **Microcosm** e **Chroma Console** (`microcosm_figo_scena.axp`, `chroma_console_figo_scena.axp`).
  È la seconda parte.
* **Gli effetti da soli** (`effetti/microcosm_gills.axp`, `effetti/chroma_console_gills.axp`): Microcosm e Chroma
  Console per la Gills, come li usavi prima. Le loro versioni per norns, con Caramello, sono in `tools/norns/effetti/`.

# SCENA - una manopola dal break-down al build-up

Una patch per la Ksoloti Gills da mettere in insert sul loop (`scena.axp`) o su un bus del mixer, in mandata e
ritorno (`scena_aux.axp`). **SCENA** (manopola 1) è la manopola da suonare:

* **al centro**: pulito, bit per bit;
* **a destra**: il build-up, come le Scene FX del Pioneer RMX-1000. Il passa-alto sale, entra un fruscio che cresce,
  l'eco si apre con ripetizioni sempre più sottili;
* **a sinistra**: il break-down. Il passa-basso scende, i campioni si sbriciolano, l'eco si scurisce, sotto si apre un
  riverbero.

Le altre nove manopole dicono **fin dove arriva** ogni parte agli estremi, come una scena dell'Octatrack: le imposti
una volta, a casa. **MOTO** fa muovere tutto da solo, a tempo: il filtro e l'eco respirano a ogni battito, e a fine
battuta e a fine frase arrivano dei fill (un roll, un'eco lanciata, un tuffo del filtro). MOTO lavora solo quando SCENA
non è al centro: al centro resta tutto pulito.

## In insert o su un bus

La latenza di SCENA è solo quella della scheda: circa 1-2 ms (stima), dai convertitori e dai blocchi da 16 campioni.
L'effetto non aggiunge niente: al centro esce lo stesso campione che entra, nello stesso blocco.

* **`scena.axp`, insert**: in serie su una parte o su tutto il loop. 1-2 ms in ritardo non si sentono.
* **`scena_aux.axp`, aux**: per mandata e ritorno del mixer (il caso del tuo rig). Qui il pulito **non esce mai**: è
  già sul mixer, e una sua copia in ritardo di 1-2 ms sommata all'originale taglia delle frequenze come un phaser
  (è la "latenza" che si sente su un bus). Escono solo:
  * il fruscio del build-up;
  * l'eco e il riverbero;
  * i loop di ROLL, FREEZE e dei fill, dalla loro **prima ripetizione** (il primo passaggio è il pulito, che è già
    sul mixer). FREEZE ripete il battito appena passato, quindi si sente subito.

  Filtro e crush lavorano su quello che va nell'eco e nel riverbero, e sui loop: il pulito sul mixer resta com'è.
  Il ritorno al centro è muto, e lo schermo scrive **MANDATA** al posto di PULITO. Mandata dal mixer prima o dopo il
  fader, come preferisci; il ritorno al livello che ti serve (RITORNI regola eco e riverbero).

  **anticipo** (un attributo dell'oggetto, di partenza 1,5 ms): quello che esce dalla Gills arriva al mixer un po' dopo
  il pulito, per la strada fino alla Gills e ritorno. In aux i loop di ROLL e FREEZE partono quell'anticipo prima, così
  le ripetizioni cadono sulla griglia del pulito. Si sceglie nel Patcher, sull'oggetto: 0, 0,5, 1, 1,5, 2, 2,5 o 3 ms.
  In insert non cambia niente.

Le due patch sono la stessa: cambia solo l'attributo **routing** dell'oggetto `scena` (insert o aux). Si può
cambiare anche nel Patcher, sull'oggetto, prima di **Live** o dell'**Upload**.

## Le manopole

| | | |
| --- | --- | --- |
| 1 | **SCENA** | sinistra break-down, centro pulito, destra build-up |
| 2 | **MOTO** | quanto si muove da solo |
| 3 | **ECO** | il tempo dell'eco: 1/16, 1/8, 1/8., 1/4, 1/4., 1/2, 1 battuta (dal clock MIDI o dal TAP) |
| 4 | **FEEDBACK** | quanto continua l'eco agli estremi |
| 5 | **FILTRO** | fin dove va il filtro: a destra un passa-alto fino a 2,5 kHz, a sinistra un passa-basso fino a 220 Hz |
| 6 | **RISON** | la risonanza; cresce con la scena |
| 7 | **RUMORE** | il fruscio del build-up |
| 8 | **CRUSH** | bit e campioni in meno nel break-down |
| 9 | **RIVERB** | il riverbero del break-down |
| 10 | **RITORNI** | il volume di eco e riverbero |

## I tasti

| | | |
| --- | --- | --- |
| S1 | **ROLL** (tenuto) | dal prossimo sedicesimo ripete 1/8 (1/16 con MOTO oltre metà); nel build-up si accorcia a ogni battito: 1/16, poi 1/32. Lo lasci e torna il loop |
| S2 | **FREEZE** | dal prossimo battito ripete il battito appena passato, finché non lo premi di nuovo; con MOTO lo varia da solo (più corto, al contrario) |
| S3 | **RELEASE** | pulito subito, l'eco si spegne da sola. SCENA torna a contare quando la riporti al centro |
| S4 | **TAP** | il tempo, se non arriva il clock MIDI |

**LED 3**: blu nel build-up, rosso nel break-down, più forte quanto più giri. **LED 4**: blu sul battito, rosso con ROLL
o FREEZE (lampeggia dopo RELEASE). **Lo schermo**: la scena (PULITO, o MANDATA in aux; BUILD 40, BREAK 70, RELEASE), il tempo e da dove
arriva (MIDI, TAP, INT), l'ultima manopola che hai mosso (o la posizione nella frase), ROLL, FREEZE o il fill in corso.

## MIDI

Su qualsiasi canale arrivano il clock, START e STOP: con START la frase riparte dal primo battito. E cinque CC:
**20** SCENA, **21** MOTO, **22** ROLL (da 64 in su tenuto), **23** FREEZE, **24** RELEASE. La manopola si riprende il
controllo appena la muovi. Il clock arriva dal MIDI IN DIN della Gills; con il cavo USB al Pi la Gills dovrebbe
comparire anche nella matrice di RaspiMIDIHub.

## Caricarla sulla Gills

1. Sul computer apri `scena.axp` (insert) o `scena_aux.axp` (bus) con il **Ksoloti Patcher**. La patch usa solo gli
   oggetti di base (`audio/in stereo`,
   `audio/out stereo`) e lo schermo della Gills (`ksoloti/gills/display`, nella libreria `ksoloti-objects` che il
   Patcher scarica da solo).
2. Gills collegata via USB, **Live**: la patch si compila sul computer e parte. In basso nella finestra guarda il
   **carico DSP**: è previsto sotto la metà.
3. Per averla a ogni accensione, senza computer: **Upload to internal flash** (menu **Board** della finestra della
   patch).
4. Le istruzioni sono anche dentro la patch: **Patch > Notes**.

Tutto l'effetto sta in un solo oggetto, scritto in C++. Il codice è in `scena_engine.h` (l'effetto) e
`scena_platform.h` (manopole, tasti e LED della Gills); `make_scena.py` rifà `scena.axp` e `scena_aux.axp` da questi
due file.

## Prove

* `tools/gills/test_scena.cpp`: l'effetto sul computer, con manopole e tasti finti. Controlla che:
  * al centro esca esattamente quello che entra;
  * i filtri tagliano davvero, e arrivano il fruscio, il crush e la coda del riverbero;
  * l'eco va a tempo con il clock e si spegne;
  * RELEASE lascia suonare la coda;
  * il clock MIDI dà il tempo giusto, e così il TAP;
  * ROLL e FREEZE ripetono il pezzo giusto e poi lasciano tornare il pulito;
  * i fill di MOTO cadono solo a fine battuta o a fine frase, e mai al centro;
  * il CC 20 e la manopola si passano il controllo;
  * con tutto al massimo e rumore bianco in ingresso non esplode;
  * in insert esce, campione per campione, quello che usciva prima di aux (il loop di prova di 16 battute è identico);
  * in aux al centro esce silenzio esatto, qualsiasi cosa entri; nel build-up senza eco esce solo il fruscio, uguale
    con due ingressi diversi; un colpo non esce, la sua eco un battito dopo sì; ROLL tace nel primo passaggio e poi
    ripete il pezzo passato (non il pulito di adesso); FREEZE ripete il battito; il filtro del break-down taglia
    anche il loop; con tutto al massimo non esplode.

  `build/test_scena --render demo.wav` fa un loop di 16 battute con la manopola mossa a mano.
* `tools/gills/armcheck/check_arm.sh` (con `KSOLOTI=` una copia del repository di Ksoloti) compila le due patch per
  il Cortex-M4 contro gli header veri del firmware. Ne escono circa 15 kB di codice, contro i 44 disponibili.

Non è ancora girata su una Gills vera: la prima volta usa Live e guarda il carico DSP (in aux fa un filtro in più,
per i loop).

# VARIAZIONI - FIGO e SCENA insieme

Le variazioni di **FIGO** (le stesse di FIGO su norns: ripetizioni da 1/4 a 1/32, ROLL, REVERSE, OTTAVA - e +, TAPE
STOP, SHUFFLE, GATE, INDIETRO, e sotto MEMORIA ed ECO) e quelle di **SCENA**, sullo stesso suono e a tempo con lo
stesso clock. Qui FIGO lavora campione per campione: niente softcut, niente attese. Ogni salto è una dissolvenza di
2 ms che finisce dove va, così l'attacco di un colpo non si perde mai; e FIGO decide un battito prima.

Due modi di usarle:

* **Da sole**: `figo_scena.axp` (insert) e `figo_scena_aux.axp` (aux, mandata e ritorno). Le manopole e i pulsanti
  sono delle variazioni.
* **Microcosm + FIGO + SCENA** e **Chroma Console + FIGO + SCENA**, per un bus del mixer: l'effetto e le variazioni
  nella stessa Gills, sulla stessa mandata. Il ritorno è l'effetto più le variazioni: `microcosm_figo_scena.axp` e
  `chroma_console_figo_scena.axp`. L'effetto resta com'era: quando le variazioni non fanno niente, dal ritorno esce
  l'effetto bit per bit.

  Queste due patch le fa `make_bus.py` dagli effetti di `effetti/`. Se cambi un effetto (o ne aggiungi uno con il suo
  `panel`), rifalle:

      python3 tools/gills/make_bus.py

  Con `--fx tua_patch.axp` lavora su un'altra patch e scrive la versione con le variazioni accanto a lei.

## Le due pagine (con un effetto)

Le manopole e i pulsanti della Gills sono dell'effetto o delle variazioni. **Tieni premuto l'encoder per un secondo
senza toccare altro, e lascia**: passi all'altra pagina. Mentre lo tieni, l'ultima riga dello schermo scrive
`LASCIA: VARIAZIONI` (o `LASCIA: MICROCOSM`, `LASCIA: CHROMA`). Se intanto giri una manopola o premi un tasto,
la pressione resta dell'effetto (SHIFT; sul Microcosm un tocco breve da solo è REVERSE).

Tornando su una pagina, **ogni manopola riprende il suo valore quando ci passa sopra** (pick-up): niente salta. Sulla
pagina delle variazioni lo schermo mostra `~` e `o` finché la manopola non aggancia. L'effetto intanto continua a
suonare, e il MIDI e il clock gli arrivano sempre.

## Le manopole e i pulsanti delle variazioni

| | | con SHIFT (encoder tenuto) |
| --- | --- | --- |
| 1 | **SCENA** (sinistra break-down, centro pulito, destra build-up) | |
| 2 | **FIGO**: quanto interviene | |
| 3 | **CARATTERE**: da dub (ripetizioni lunghe, reverse a metà velocità, ottava sotto, tape stop, eco) a glitch (1/16 e 1/32, roll che salgono, shuffle, gate, ottava sopra) | |
| 4 | **MEMORIA**: torna una battuta di qualche battuta fa, sotto | |
| 5 | **MOTO** (SCENA si muove da sola) | |
| 6 | **ECO** | **RISON** |
| 7 | **FEEDBACK** | **RUMORE** |
| 8 | **FILTRO** | **CRUSH** |
| 9 | **RIVERB** | **LIV.MEMORIA** |
| 10 | **RITORNI** | **LIVELLO** degli interventi di FIGO |

| | | con SHIFT |
| --- | --- | --- |
| 1 | **ROLL** di SCENA (tenuto) | la frase di FIGO parte da qui |
| 2 | **FREEZE** di SCENA | |
| 3 | **PULITO**: FIGO esce a tempo (tape stop, backspin o secco) e SCENA torna pulita; di nuovo: FIGO riparte | |
| 4 | **HOLD**: ripete il battito appena passato (con FIGO alto lo varia da solo); di nuovo: torna il loop | **TAP** |
| encoder | | **anticipo** in aux, un decimo di millisecondo a scatto |

**Lo schermo**: riga 1 FIGO, CARATTERE, MEMORIA e INS o AUX; riga 2 SCENA; riga 3 il tempo e la frase; riga 4
l'intervento di FIGO (con INDIETRO quante battute indietro) e MEMORIA o ECO. Quando giri una manopola, le righe 3 e 4
mostrano il suo valore. **I LED**: 1 il battito; 2 FIGO interviene (tenue: la memoria); 3 blu build-up, rosso
break-down; 4 blu HOLD o un loop di SCENA, rosso SHIFT (lampeggia con PULITO o RELEASE).

## MIDI

Su qualsiasi canale e da qualsiasi pagina: **CC 110** SCENA, **111** MOTO, **112** ROLL (da 64 in su tenuto), **113**
FREEZE, **114** RELEASE, **115** FIGO, **116** CARATTERE, **117** MEMORIA, **118** HOLD, **119** PULITO. Così dal
controller puoi lanciare le variazioni anche quando la Gills mostra l'effetto. I CC 20-24 restano dell'effetto
(Microcosm e Chroma li usano); da sole, le variazioni rispondono anche ai CC 20-24 di SCENA. Clock, START e STOP danno
il tempo: START fa ripartire la frase, ma non interrompe quello che FIGO sta facendo.

## Insert o aux, e gli attributi

Sull'oggetto `variazioni`, nel Patcher, prima di Live o dell'Upload:

* **routing**: *insert* (in serie: l'ingresso, o l'effetto, passa da FIGO e poi da SCENA) o *aux* (mandata e ritorno:
  escono solo gli interventi, niente pulito, che è già sul mixer; quando non succede niente, esce silenzio). Le
  patch con Microcosm e Chroma sono in aux. In aux FIGO non usa GATE (taglierebbe un pulito che non passa da qui) né
  le ripetizioni troppo corte per ripetersi (la loro prima fetta è il pulito, che in aux non esce).
* **ingresso**: stereo, o mono L (il sinistro su tutti e due i lati).
* **frase**: 16, 8 o 32 battiti, la frase di FIGO (più interventi verso la fine).
* **uscita**: come esce FIGO con PULITO: auto, tape stop, backspin, secca.
* **anticipo**: in aux le ripetizioni partono questo tempo prima (di partenza 1,5 ms), per cadere sulla griglia del
  pulito al mixer. Si cambia anche dalla Gills: SHIFT + encoder. Per tararlo: una cassa dritta, FIGO 100, CARATTERE 0,
  e gira finché le ripetizioni non si fondono con i colpi.

## La memoria

| | nastro di FIGO | eco più lunga di SCENA |
| --- | --- | --- |
| da sole, e con Chroma Console | 43,7 s | 5,4 s |
| con Microcosm | 21,8 s | 2,7 s (una battuta intera fino a 88 BPM) |

Il Microcosm usa già quasi tutta la memoria grande della scheda: con lui il nastro è la metà. INDIETRO e MEMORIA
arrivano fino a 4 e 8 battute fa finché il nastro le tiene; se no prendono meno battute.

Con un effetto il codice non sta tutto nei 44 kB della memoria del codice: la parte delle variazioni che non gira a ogni
campione va nella **seconda RAM** della scheda (SRAM3, 64 kB; ne usa circa 32). Il Patcher e il firmware di Ksoloti la
sanno usare: nel loro codice (quello di luglio 2026, con cui ho compilato e collegato queste patch) la seconda parte si
carica con **Live**, si salva con **Upload to Internal Flash** (all'accensione il firmware la rimette in RAM) e si legge
dalla scheda SD. Non ho potuto controllare da quale versione pubblicata c'è. Con un Patcher più vecchio la patch con
l'effetto dovrebbe fermarsi alla compilazione, con un errore di memoria piena: aggiorna Patcher e firmware, insieme.
Le patch da sole (`figo_scena.axp`, `figo_scena_aux.axp`) non la usano.

## Prove

* `tools/gills/test_variazioni.cpp`: le variazioni sul computer, da sole e accanto a un effetto finto, con manopole,
  tasti e MIDI finti. L'ingresso dice a ogni campione quando è entrato, così ogni campione d'uscita dice da dove viene.
  Controlla, tra l'altro, che:
  * quando non fanno niente esca, in insert, esattamente quello che entra; in aux silenzio esatto;
  * ogni ripetizione sia intera dal primo campione, e il pulito torni dopo;
  * in aux tutto arrivi l'anticipo prima, e non esca mai il pulito;
  * REVERSE, OTTAVA, TAPE STOP, SHUFFLE, GATE, INDIETRO, ROLL, HOLD e MEMORIA suonino quello che devono, e non leggano
    mai il nastro dove non è ancora scritto;
  * FIGO misuri il battito giusto, e INDIETRO cada sul battito vero anche se il tempo si sposta;
  * con un seno in ingresso e FIGO e MEMORIA a 100 non ci sia mai un click (anche quando un salto arriva durante
    un'altra dissolvenza, o un evento parte proprio dove finisce il precedente);
  * la pagina, il pick-up, SHIFT, i CC 110-119 e lo schermo facciano quello che dicono;
  * con tutto al massimo e rumore bianco non esploda.

      c++ -std=c++14 -O2 -Itools/gills tools/gills/test_variazioni.cpp -o build/test_variazioni && build/test_variazioni

* `tools/gills/test_bus.cpp`: le patch con Microcosm e Chroma, come le compila il Patcher, accanto all'effetto da solo.
  Controlla che con le variazioni ferme il suono sia identico, bit per bit (anche girando manopole e premendo tasti
  sull'effetto); che la pagina delle variazioni non muova l'effetto; che tornando le manopole riprendano i loro valori;
  che il CC 115 lanci FIGO anche dalla pagina dell'effetto; che un GESTURE del Chroma continui. `make_bus.py --cpp`
  scrive il C++ da provare; `tests/run_sagga_tests.sh` lo fa ogni volta.
* `tools/gills/armcheck/check_bus.py` (con `KSOLOTI=` una copia del repository di Ksoloti, e se c'è `KOBJ=` una di
  ksoloti-objects) compila e collega le patch per il Cortex-M4 con il linker del firmware, e dice quanta memoria
  prende ciascuna. Lo fa con clang, non con il GCC del Patcher: le misure sono indicative. La prova è che accanto a un
  effetto la memoria del codice non cresca rispetto all'effetto da solo.

Non sono ancora girate su una Gills vera. La prima volta usa Live e guarda il **carico DSP** in basso nella finestra:
non l'ho potuto misurare, e con l'effetto accanto è la cosa da guardare per prima.
