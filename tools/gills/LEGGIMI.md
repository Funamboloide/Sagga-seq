# SCENA - una manopola dal break-down al build-up (Ksoloti Gills)

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
