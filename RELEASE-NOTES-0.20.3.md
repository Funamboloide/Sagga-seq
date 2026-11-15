# SAGGA SEQ 0.20.3 - Note di rilascio

**L'esploratore del banco**: l'FM-1, il Pi e il grid provati insieme, per le strade vere. Cambiano il Pi (la pagina
del hub) e, di poco, l'FM-1 (il suo test). Il formato dei progetti resta `SGQB`.

## Perché

L'esploratore dell'FM-1 (dal PC, `tools/hwtest`) preme i tasti dell'FM-1 e fa anche da tablet e da grid, ma con
messaggi suoi, dentro il test: non passa mai dal Pi. Le pagine SAGGA dentro RaspiMIDIHub, la matrice, il bridge del
grid non li aveva mai provati nessuno insieme all'FM-1.

## L'esploratore del banco

Sulla pagina del Pi (`http://192.168.4.1:8090`), **ESPLORATORE DEL BANCO**:

* **Controlla la matrice**: le celle che servono (ogni pagina SAGGA verso la porta 2 dell'FM-1, la porta 2 verso le
  pagine) e quelle che non devono esserci (un Launchpad nella matrice, la porta 2 dell'FM-1 verso un synth), il
  Default routing, i servizi. Non tocca niente.
* **Avvia la prova**: 20 sessioni (o 4, per provare), una ventina di minuti. L'FM-1 chiede il permesso (SEL), salva
  il progetto che ha in memoria e si riavvia nel suo test a ogni sessione. Il Pi:
  * preme le sei pagine SAGGA (Remote, Mutes, Motori, Break, Mod, Live) **dentro RaspiMIDIHub**, con la sua API, come
    quando tocchi il tablet: il comando esce dalla pagina e arriva all'FM-1 dalla matrice. Nel giro ogni cella di ogni
    pagina viene premuta almeno una volta;
  * fa girare **il bridge del grid vero** con due Launchpad finti: i pad e i bottoni entrano nel bridge, il bridge parla
    con l'FM-1, le luci che l'FM-1 rimanda arrivano al bridge (il servizio del bridge resta fermo durante la prova);
  * preme il pannello dell'FM-1 e legge tutto il suo stato dopo ogni gesto, con il test dell'FM-1.
  Durante la prova **le celle fra l'FM-1 e i synth sono staccate**: i synth tacciono, e niente di estraneo entra
  nell'FM-1. Tornano alla fine; se la prova si interrompe (corrente, riavvio) tornano alla prova dopo, o con
  **Rimetti le celle**. Alla fine il tuo progetto torna in memoria (sull'FM-1 `IMPORTED`: SAVE per tenerlo).
* Dopo ogni sessione il Pi controlla da solo: ogni comando delle pagine e ogni messaggio del bridge è arrivato
  all'FM-1? Il bridge ha tradotto ogni pad giusto? Le luci sono quelle che l'FM-1 ha mandato? I valori che l'FM-1
  rimanda sono tornati sulle pagine? Se hai cambiato il CC di una cella, la prova usa il tuo.
* Il log si vede sulla pagina mentre va; alla fine **raccolta-banco-...json** e **RAPPORTO-BANCO-...md** si scaricano
  dalla pagina (restano anche sulla SD, le ultime tre prove). La raccolta va confrontata con il simulatore
  (`python3 tests/sagga_explore.py --banco raccolta-banco-....json`): mandamela.

## L'FM-1: il test ascolta le porte

Fino alla 0.20 l'FM-1, nel suo test, ignorava tutto il MIDI che arrivava dalle porte (per rifare ogni sessione
uguale). Dalla 0.20.3, se il Pi lo chiede, lo suona e dice al Pi ogni messaggio che ha sentito e dove (il suo
millisecondo, il tick del clock, la porta): il simulatore rifà la sessione con quei messaggi negli stessi punti. Fuori
dal test non cambia niente. Il PC (`tools/hwtest`) continua come prima.

## Provato

* Il simulatore al posto dell'FM-1, il bridge vero, i ritardi del Pi a caso: 20 sessioni da 40 gesti, tutte uguali;
  con i comandi delle pagine persi dal hub, o con un pezzo di quello che l'FM-1 ha sentito perso per strada, il
  confronto lo trova.
* Il test dell'FM-1 nel simulatore: senza la richiesta non sente niente, come prima; con la richiesta sente tutto,
  in ordine, al millisecondo, e la sessione rifatta con quei messaggi è la stessa macchina, luci del grid comprese.
* Il programma del Pi contro un FM-1 finto, un RaspiMIDIHub finto e un systemctl finto: le celle staccate e rimesse
  (anche dopo un'interruzione), le pagine premute dal hub, una cella con il CC cambiato, una pagina che manca, il
  bridge fermato e riacceso, un FM-1 con il firmware vecchio (si ferma senza toccare niente).
* La pagina: la prova parte in un servizio a parte (se la pagina si riavvia, la prova va avanti), durante la prova
  l'FM-1 non si installa e l'editor non lo tocca, i file si scaricano.

Non è ancora girato sul banco vero: è la prima volta.
