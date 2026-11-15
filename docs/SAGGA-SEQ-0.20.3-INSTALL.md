# SAGGA SEQ 0.20.3 - Installazione

L'esploratore del banco (`RELEASE-NOTES-0.20.3.md`). Cambiano il Pi e l'FM-1.

## 1. Il Pi

PC o tablet sulla rete del Pi (`RaspiMIDIHub-XXXX`), apri `http://192.168.4.1:8090`. In **AGGIORNA IL PI** scegli
`sagga-hub-0.20.3.zip` e premi **Aggiorna il Pi**. Il log finisce con `exit 0` e in alto compare `SAGGA HUB 0.20.3`.
Alla fine il WiFi del Pi può sparire per qualche secondo: se il PC non si ricollega da solo, ricollegalo tu.

## 2. L'FM-1

Il firmware `sagga-0.20.3.fwsc` lo costruisce GitHub: lo trovi nel ramo `pacchetti` del repository
(`github.com/Funamboloide/Sagga-seq/tree/pacchetti`, il file `sagga-0.20.3.fwsc`, poi **Download raw file**).

FM-1 collegato al Pi e fermo, sulla pagina del Pi: **FIRMWARE**, carica `sagga-0.20.3.fwsc`, **Installa**. Dopo il
riavvio lo schermo dice `SAGGA SEQ 0.20.3`.

## 3. Prima della prova

* Sull'FM-1 conviene **USB PORTS 2** (SAVE tenuto, OCT+ fino a `SAVE 3 SYSTEM`, K1 su 2, poi SEL + K1 due volte:
  si ricollega): il grid e le pagine sulla porta 2, i synth sulla 1. Con una porta sola la prova va lo stesso, e il
  controllo della matrice lo dice.
* Nel hub le sei pagine SAGGA aggiunte (Remote, Mutes, Motori, Break, Mod, Live), ognuna con le sue due celle: la
  pagina verso la porta 2 dell'FM-1, la porta 2 verso la pagina. Una pagina che non c'è viene provata lo stesso, con
  i suoi comandi mandati diretti.
* I Launchpad possono restare collegati: durante la prova il bridge vero è fermo e il Pi usa due Launchpad finti.

## 4. La prova

1. Sulla pagina del Pi, **ESPLORATORE DEL BANCO**, premi **Controlla la matrice**: in un secondo dice cosa c'è e cosa
   manca. Se c'è un **ERRORE** sistemalo nella matrice (Save Config) e ricontrolla.
2. Premi **Avvia la prova** (la prima volta va bene **4 sessioni**, cinque minuti). Quando la pagina dice **Sull'FM-1:
   premi SEL**, premi SEL sull'FM-1 entro 20 secondi.
3. Da lì non toccare l'FM-1: si riavvia a ogni sessione, un tasto premuto ferma tutto. I synth tacciono (le loro celle
   sono staccate), il grid resta spento.
4. Alla fine la pagina dice **finito**. Sull'FM-1 c'è `IMPORTED: SAVE TO KEEP IT`: il tuo progetto è tornato in
   memoria, tocca SAVE due volte se vuoi tenerlo nello slot. Le celle dei synth sono tornate nella matrice.
5. Scarica dalla pagina **raccolta-banco-...json** e **RAPPORTO-BANCO-...md** e mandameli.

## 5. L'FM-1 completo

Come la prova del banco, ma nella tendina scegli **l'FM-1 completo: ogni situazione** (tutte le sessioni: mezz'ora
circa). Sono le sessioni dell'esploratore che facevi dal PC: ogni situazione dell'FM-1, 60 gesti a sessione. Anche qui
SEL quando la pagina lo chiede, poi non toccare l'FM-1; alla fine scarica la raccolta e mandamela.

Chiudere la pagina non ferma la prova: va avanti da sola. Se invece il Pi si spegne a metà, alla riaccensione la
pagina mostra **Rimetti le celle**: premilo (con l'FM-1 e i synth collegati) e le celle dei synth tornano.
