# SAGGA SEQ 0.9 - Note di rilascio

La 0.9 legge i progetti della 0.8 (`SGQ8`) e salva nel formato nuovo (`SGQ9`). Della 0.8 non è stato tolto niente.

## Nuovo

* **VIAGGIO** (SEL + PERF). Il set suonato come un viaggio fatto di frasi.
  * **La frase**: dura 16 battute (oppure 8 o 4, da HOME 6/6 K2). Quello che chiedi si mette in **coda** e succede
    tutto insieme alla fine della frase. Intanto le mani restano libere per preparare la frase successiva.
  * **Le tracce** (tasti bianchi): un tap su una traccia vuota crea una **proposta** presa dalla libreria del genere.
    Se tieni premuto, tira i dadi. **SEL + tasto** fa entrare la traccia alla fine della frase, oppure la fa uscire
    con una dissolvenza. Un tap su una traccia che suona non la zittisce mai.
  * **Le mosse** (tasti neri): FILL, BREAK, RISER, DROP, HALF, DOUBLE, THIN, SWELL, SWAP, LOOP e NOW.
    * LOOP registra una frase suonata a mano.
    * NOW esegue la coda alla battuta dopo; da fermo la esegue subito.
  * **OCT−** torna alla frase prima. **OCT+** annulla l'ultima mossa.
  * **ENERGIA** (K1, da 0 a 100) muove insieme velocity, filtro, gate, densità, profondità degli LFO e colore degli
    accordi. Scivola fino al nuovo valore nel corso della frase.
  * **Cinque generi del set**: LOFI DEEP, DUB TECHNO, HARDTECHNO, DUBSTEP, JUNGLE DNB. Ognuno ha la sua scala dei ruoli.
    I generi bass hanno anche le percussioni AFRO/LATIN: tresillo, son clave, rumba, cascara, bossa, cinquillo e
    bembé.
  * **SEL + PLAY** da fermo è il SEME: tira a sorte genere, tonalità e tempo.
  * **SAVE + bianco 16** (SALVA VIAGGIO): la scia delle frasi diventa scene e canzone.
* **Profili** (SAVE + K4): **FULL** fa tutto come la 0.8. **PALCO** è per suonare:
  * VIAGGIO è acceso dall'accensione;
  * il pannello non modifica gli step;
  * HOME mostra solo le pagine KEY e VIAGGIO;
  * il remote è su 13 + 14.

  Il profilo resta salvato nell'FM-1.
* **Remote sul canale 13** (SAVE + K2: OFF, CH 14, 13 + 14). Porta i comandi del VIAGGIO: CC 1-16 tracce, 17-27
  mosse, 28 indietro, 29 annulla. Sul canale 14, il CC 3 è l'energia.
* **Il regista** (SysEx 50-55). Un programma sul Pi segue il set: battuta, scena, tonalità, accordo, frase, energia.
  Può anche scrivere una frase su una traccia alla battuta successiva. Il grid ha la vista REGIA per le sue regole.
* **16 scene, canzone di 64 voci.**
  * Sul pannello, PERF + PRESETS sposta il cursore delle scene da 1 a 16; i tasti neri vanno al banco del cursore.
  * La vista SONG del grid sfoglia le voci a pagine di 16 (riga 4, pad 13/14).
* **Il salvataggio ricorda cosa suonava.** All'accensione tornano il pattern di ogni traccia, i mute e la scena.
* **Grid**: vista VIAGGIO (PERF → SONG → VIAGGIO); vista REGIA dopo VIAGGIO, quando un regista ha parlato. Il pad del
  remote nella vista PROJ ha tre stati.

## Corretto

* Con due porte USB, i CC degli LFO, i Program Change delle scene e il MIDI LEARN arrivavano solo ai canali 1-14.
* Un mute di gruppo (scena tutto acceso, solo questa, inverti) lasciava indietro dei mute in coda.
* Un LEARN in attesa sopravviveva al caricamento di un progetto.
* Uno STOP esterno veniva gestito due volte.
* Uno snapshot che cambiava pattern teneva lo step già deciso per il pattern vecchio.

## Trovati dai test e dalla revisione della 0.9, corretti prima del rilascio

* Una proposta su una traccia vuota suonava un C4 invece della cassa.
* INDIETRO tornava alla frase appena finita invece di quella prima; con NOW andava una frase troppo indietro.
* Dopo un RISER la frase successiva partiva dal picco invece che dall'energia scelta.
* HALF e DOUBLE spostavano le tracce fuori dalla griglia per tutto il set, e un salvataggio durante la frase li
  rendeva permanenti. Ora passano dallo stesso meccanismo degli effetti HALF / DOUBLE e non toccano il progetto.
* Un BREAK dentro un BREAK lasciava tutto muto; una traccia che entrava durante un BREAK suonava nel silenzio.
* Spegnere VIAGGIO a metà frase lasciava attivi HALF, BREAK, la dissolvenza e la registrazione LOOP.
* Il LOOP: poteva cancellare il pattern che suonava; cambiava per sempre lunghezza e divisione della traccia (ora
  tornano quando la traccia lascia il loop e si rimettono quando ci torna); un loop in cui non hai suonato niente
  viene dimenticato; su una traccia DRUM tutti i tasti bianchi suonano quel tamburo; la tastiera esterna registra
  sulla traccia del loop.
* Il FILL chiesto nell'ultima battuta andava perso; il FILL ora aggiunge colpi fantasma su tutte le tracce (i
  pattern della libreria non hanno condizioni FILL).
* Le proposte diventavano "dentro" dopo PERF e ritorno, o dopo un caricamento.
* Le risposte del regista (RISPOSTA, TOCCATA, REGIA TASTO) si perdevano se la coda USB era piena.
* Il profilo PALCO non bloccava le manopole di SEQ / EDIT / ENV.
* SALVA VIAGGIO contava le battute con la lunghezza di frase attuale anche per le frasi vecchie.

## Cosa provare per primo

1. **SEL + PERF**. Fai tap sul bianco 1: compare la proposta di cassa. Poi **SEL + bianco 1**, **nero 11 (NOW)**,
   **PLAY**: la cassa suona.
2. HOME 6/6 K2 su 4 battute. **SEL + bianco 2**: il rullante entra alla fine della frase.
3. **K1** a 100: senti l'energia salire battuta dopo battuta. Poi **nero 7 (THIN)** e **nero 8 (SWELL)**.
4. **OCT−**: alla fine della frase torni a quella prima.
5. **SAVE + bianco 16**, poi salva il progetto: il viaggio è diventato una canzone.

## Test

Il codice vero del firmware gira in un simulatore: 515 controlli. Ci sono anche il core (687.065 controlli), il bridge
(246), il fuzz con AddressSanitizer e i descrittori USB. Tutto senza errori. Sull'FM-1 vero la 0.9 non è ancora
stata provata: è il prossimo passo.
