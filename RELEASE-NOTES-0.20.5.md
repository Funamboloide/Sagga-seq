# SAGGA SEQ 0.20.5 - Note di rilascio

**Cambia solo il Pi**: l'esploratore del banco, dopo le prime prove sul banco vero. Il firmware dell'FM-1 resta la
0.20.3.

## Cosa hanno detto le prime prove

* **L'FM-1 è uguale al simulatore** in tutte le sessioni, del banco e dell'FM-1 completo. Le pagine, la matrice e il
  bridge funzionano: ogni comando delle pagine e del bridge è arrivato all'FM-1, il bridge ha tradotto ogni pad giusto.
* **Due valori che l'FM-1 rimanda non arrivano alle pagine**: QUANTISE (SAGGA Remote) e SWING (SAGGA Live). Sono
  tutti e due sul CC 6, e il CC 6 per il MIDI è il "Data Entry" degli RPN/NRPN: sulla strada dall'FM-1 alle pagine
  qualcosa nel Pi lo tiene per sé. Gli altri valori arrivano (MUTE, PATTERN, LENGTH, EUCLID, GENRE, PROG ...), e
  nell'altra direzione (dalla pagina all'FM-1) arriva anche il CC 6. Da sistemare spostando quei comandi su altri CC:
  serve un firmware nuovo, non è in questa versione.

## Cosa cambia

* **Le luci del grid e i valori per le pagine solo dalla porta 2 dell'FM-1.** Il programma del Pi li prendeva da
  tutte e due le porte: sulla porta 1, allo STOP, l'FM-1 manda ai synth il CC 64 (sustain) a 0 su ogni canale, e il
  programma lo scambiava per un valore della pagina Motori (l15 sul canale 13, CC 64). Era un falso allarme. Con due
  porte, sulla porta 1 il canale 16 è anche una traccia, non le luci del grid.
* **Se il programma del Pi si pianta, lo dice nel suo log** (quello che la pagina mostra e fa scaricare), invece di
  fermarsi in silenzio. Si scarica anche `banco.out`, quello che ha scritto il programma.

Il confronto con il simulatore (che faccio io) riconosce adesso anche un gesto di prima letto un millisecondo dopo che
si vede solo più avanti: il dado degli LFO pesca dagli stessi numeri a caso della musica.
