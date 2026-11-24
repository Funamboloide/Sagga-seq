# SAGGA SEQ 0.32.5 - Note di rilascio (solo la Gills: VARIAZIONI)

Questa versione cambia solo la **Gills**. FIGO e SCENA stanno insieme in un solo oggetto, anche accanto a **Microcosm**
e a **Chroma Console**: così dal bus lanci le variazioni sopra l'effetto.

**L'FM-1, il Pi e norns non cambiano.** L'FM-1 resta alla 0.32.1, il Pi alla 0.32.3, FIGO su norns alla 0.2 (quella
della 0.32.4).

| il pezzo | il file |
| --- | --- |
| la Gills con Microcosm, su un bus | `tools/gills/microcosm_figo_scena.axp` |
| la Gills con Chroma Console, su un bus | `tools/gills/chroma_console_figo_scena.axp` |
| la Gills da sola, su un bus | `tools/gills/figo_scena_aux.axp` |
| la Gills da sola, in insert | `tools/gills/figo_scena.axp` |
| SCENA da sola | `tools/gills/scena_aux.axp`, `tools/gills/scena.axp` (rifatte: un click tolto, l'anticipo) |
| l'FM-1, il Pi, norns | niente da fare |

Le due patch con l'effetto le fa `tools/gills/make_bus.py` dalle patch di Microcosm e Chroma per la Gills, che adesso
sono anche loro nel repository (`tools/gills/effetti/`), con le versioni per norns di Microcosmo, Chroma e Caramello
(`tools/norns/effetti/`).

**I numeri delle versioni** sono quelli del repository: salgono a ogni rilascio, anche quando cambia solo un effetto.
Le patch della Gills e gli script di norns funzionano con qualsiasi versione dell'FM-1 e del Pi.

## VARIAZIONI

* **FIGO rifatto per la Gills, in C++.** È la stessa macchina di FIGO su norns: un intervento a battito, deciso un
  battito prima; da dub a glitch con CARATTERE; MEMORIA ed ECO sotto. Qui lavora campione per campione: niente
  softcut, niente attese. Ogni salto è una dissolvenza di 2 ms che finisce dove va, così l'attacco di un colpo non si
  perde mai.
* **SCENA nello stesso oggetto**, a tempo con lo stesso clock: le manopole di SCENA restano quelle di sempre.
* **Con un effetto, due pagine.** Le manopole e i pulsanti sono dell'effetto o delle variazioni. **L'encoder tenuto
  un secondo senza toccare altro, e lasciato**, passa all'altra pagina. Tornando, ogni manopola riprende il suo valore
  quando ci passa sopra: niente salta. L'effetto intanto suona, e il MIDI e il clock gli arrivano sempre (anche un
  GESTURE del Chroma continua).
* **Dal MIDI, da qualsiasi pagina: i CC 110-119.** 110 SCENA, 111 MOTO, 112 ROLL, 113 FREEZE, 114 RELEASE, 115 FIGO,
  116 CARATTERE, 117 MEMORIA, 118 HOLD, 119 PULITO.
* **Due cose diverse da quello che ti avevo detto:**
  * i CC sono **110-119**, non 20-24: i 20-24 li usano già Microcosm e Chroma. Le patch da sole rispondono anche ai
    20-24 di SCENA;
  * la pagina cambia con l'encoder **tenuto un secondo e lasciato**, non con una pressione: la pressione è già dello
    SHIFT dell'effetto, e sul Microcosm un tocco breve da solo è REVERSE.
* **Le due patch con l'effetto sono in aux** (mandata e ritorno): dal ritorno escono l'effetto e gli interventi, mai
  il pulito. Quando le variazioni non fanno niente, esce l'effetto bit per bit, come senza.
* **La memoria**: il nastro di FIGO è di 43,7 s da solo e con Chroma, di 21,8 s con Microcosm (il Microcosm usa già
  quasi tutta la memoria grande della scheda). Con Microcosm l'eco più lunga di SCENA è 2,7 s: una battuta intera fino a
  88 BPM.
* **La seconda RAM.** Con un effetto il codice non sta nei 44 kB della memoria del codice: la parte delle variazioni che
  non gira a ogni campione va nella seconda RAM della scheda (64 kB, ne usa circa 32). Il codice di Ksoloti (quello di
  luglio 2026, con cui ho compilato queste patch) la carica con Live, la salva con Upload to Internal Flash e la
  rimette in RAM all'accensione. Non ho potuto controllare da quale versione pubblicata c'è: con un Patcher più vecchio
  la patch con l'effetto dovrebbe fermarsi alla compilazione, con un errore di memoria piena. Le patch da sole non la
  usano.

Tutto il resto (le manopole, i pulsanti, lo schermo, i LED, gli attributi) è in `tools/gills/LEGGIMI.md` e dentro ogni
patch (Patch > Notes).

## SCENA

* **Un click tolto.** Alla prima ripetizione di ROLL e FREEZE il loop saltava al suo inizio senza dissolvenza: un salto
  fino a 0,3 sul campione. Adesso ogni giro del loop, anche il primo, sfuma nel suo inizio.
* **L'anticipo, in aux.** ROLL e FREEZE partono quel tanto prima (1,5 ms di partenza, attributo `anticipo`), così le
  ripetizioni cadono sulla griglia del pulito al mixer. In insert non cambia niente.

## Come è stato provato

* **`tools/gills/test_variazioni.cpp`**, 178 controlli. L'ingresso dice a ogni campione quando è entrato, così ogni
  campione d'uscita dice da dove viene. Le nuove prove hanno trovato tre errori di FIGO, già corretti:
  * **un click quando un salto arriva durante un'altra dissolvenza** (succede spesso: una ripetizione che finisce
    proprio dove parte l'intervento dopo). Il secondo salto buttava via quello che stava ancora sfumando: un salto fino
    a 0,84. Adesso le due dissolvenze vanno avanti insieme. Con un seno in ingresso e FIGO e MEMORIA a 100, il passo più
    grande dell'uscita è 0,027: quello che il seno fa da solo;
  * **dopo un TAPE STOP** il nastro fermo tornava per un attimo a tutto volume, e un GATE subito dopo una ripetizione la
    lasciava suonare sotto;
  * **INDIETRO con il tempo che si sposta** (da 120 a 123 BPM in 16 battiti) cadeva a 1789 campioni dal battito vero.
    Adesso cerca i battiti veri: 4 campioni. Anche dopo uno START a metà battito cade su un battito che c'era.
* **`tools/gills/test_bus.cpp`**: le patch con Microcosm e Chroma come le compila il Patcher, accanto all'effetto da
  solo. Con le variazioni ferme il suono è identico bit per bit, anche girando manopole e premendo tasti; la pagina delle
  variazioni non muove l'effetto; tornando, le manopole riprendono i loro valori; il CC 115 lancia FIGO dalla pagina
  dell'effetto; il GESTURE del Chroma continua. 21 controlli con Microcosm, 25 con Chroma.
* **`tools/gills/armcheck/check_bus.py`**: le patch compilate per il Cortex-M4 e collegate con il linker del firmware.
  Con l'effetto la memoria del codice è 42,4 kB (Microcosm) e 42,8 kB (Chroma), meno dell'effetto da solo con lo stesso
  compilatore (46,8 e 47,1: clang fa codice più grande del GCC del Patcher); la seconda RAM 32,4 kB su 64. Le patch da
  sole: 34,4 kB.
* **Rotture apposta**: ho rotto apposta 53 pezzi del codice nuovo, uno alla volta. Le prove se ne accorgono in 48 casi
  (al primo giro ne sfuggivano 16: ho aggiunto le prove che mancavano); gli altri 5 non cambiano niente che si senta, per
  esempio un loop spostato di un campione, nel tempo e nel nastro insieme.
* **SCENA**: `tools/gills/test_scena.cpp`, 61 controlli (3 nuovi: nessun salto alla prima ripetizione; in aux ROLL e
  FREEZE con l'anticipo).
* **Niente è stato provato su una Gills vera.** La prima volta usa **Live**, non l'Upload: guarda il **carico DSP** in
  basso nella finestra del Patcher (non l'ho potuto misurare, e con l'effetto accanto è la cosa da guardare per prima),
  ascolta i livelli, e in aux tara l'anticipo (SHIFT + encoder). Poi **Upload to Internal Flash**.

Nel piano per il live il firmware si blocca domenica 13 dicembre: c'è tempo per provarle sul rig.
