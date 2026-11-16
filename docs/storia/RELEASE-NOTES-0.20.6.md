# SAGGA SEQ 0.20.6 - Note di rilascio

Cambiano **l'FM-1** (i valori che rimanda al hub) e **il Pi** (le pagine SAGGA e l'esploratore del banco). Il formato
dei progetti resta `SGQB`.

## QUANTISE e SWING tornano sulle pagine

Le prime prove del banco hanno trovato che due valori che l'FM-1 rimanda al hub non arrivavano mai alle pagine:
QUANTISE (SAGGA Remote) e SWING (SAGGA Live). Erano tutti e due sul CC 6. RaspiMIDIHub 6 fa girare le sue pagine in MIDI
2.0 quando il Pi lo sa fare, e in MIDI 2.0 il CC 6 (e il 38, e i 98-101) non sono più dei CC qualsiasi: sono i pezzi di
un RPN / NRPN, e il Pi se li tiene. Lo stesso valeva per il pattern della traccia 6 (CC 38, SAGGA Motori) e la lane 1
(CC 101, SAGGA Mod).

Adesso l'FM-1 rimanda quei quattro sul **canale 12, CC 33-36**, e le pagine li prendono lì. Nell'altro senso non cambia
niente: le pagine, la BeatStep e qualsiasi controller continuano a mandare il CC 6, il 38 e il 101 come prima. Se hai
cambiato il CC di una di quelle celle, segue il tuo.

Servono tutti e due: il firmware 0.20.6 sull'FM-1 e il Pi 0.20.6 (le pagine nuove si installano con lui).

## Il banco non si ferma più alla terza sessione

La prima prova del banco si era fermata dopo due sessioni: "error creating ALSA sequencer client object". A ogni
riavvio dell'FM-1 il programma del Pi riapriva le porte e lasciava indietro quelle vecchie (su Linux ogni porta aperta
è un "client" di ALSA, e una porta chiusa non lo libera finché il programma non lo butta via). Dopo un po' ALSA non ne
aveva più. Adesso ogni porta chiusa libera il suo client.

## Provato

* Nel simulatore: SWING, QUANTISE, il pattern della traccia 6 e la lane 1 tornano sul canale 12 CC 33-36 e mai più sui
  vecchi numeri; quello che il tablet ha appena mosso non torna indietro mentre la mano è lì; i vecchi numeri, in
  entrata, fanno quello che facevano.
* Le pagine con il loro codice e con quello vero di RaspiMIDIHub: il canale 12 CC 33-36 diventa il valore della cella
  giusta, il loro CC di sempre funziona ancora, e premere la cella manda ancora il CC di sempre.
* Il programma del banco con un python-rtmidi finto che conta i client: dopo quattro sessioni e i loro riavvii non ne
  resta nessuno (prima: 36, e sul Pi di più, finché ALSA non ne dava più).
