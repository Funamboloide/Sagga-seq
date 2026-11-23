# SAGGA SEQ 0.32.2 - Note di rilascio (solo il Pi)

Mi hai mandato i log della 0.32.1 sull'FM-1 vero. **L'FM-1 è a posto: in tutte e 71 le sessioni fa esattamente quello
che fa il simulatore.** Gli stessi log mostrano però tre cose che non andavano **sul Pi**, e una ti ha lasciato con il
grid spento finché non hai riavviato il Pi. Sono sistemate tutte e tre.

**Il firmware dell'FM-1 non cambia.** Resta la 0.32.1 che hai dentro, quella che ha appena passato le prove. Si
aggiorna solo il Pi.

| il pezzo | il file |
| --- | --- |
| l'FM-1 | niente da fare: resta `sagga-0.32.1.fwsc` |
| il Pi (la pagina, il banco, il bridge del grid) | `sagga-hub-0.32.2.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

## 1. I tuoi log: l'FM-1 vero con la 0.32.1

Hai fatto girare tutti e due i piani: il banco (33 sessioni) e l'FM-1 completo (38). **In tutte e 71 l'FM-1 fa quello
che fa il simulatore**, con dentro le correzioni della 0.32.1: i nomi delle quattro forme d'accordo, le banche del
tablet, i pad che chiedono due volte.

Il rapporto segnava due cose, una per raccolta. Le ho guardate: **nessuna è un errore dell'FM-1, erano tutte e due una
questione di tempo**, e lo strumento che confronta adesso lo capisce da solo.

| cosa segnava | cos'era davvero |
| --- | --- |
| **s024**: un accordo diverso (`iv9` invece di `i7`) | La sonda è caduta nel millisecondo in cui l'accordo cambiava. L'FM-1 l'ha letta un attimo prima di fare quel tick di clock. |
| **b014**: un THROW sul FILTER a 27 invece di 26 | Lo stesso: il valore stava scendendo, e la sonda è caduta un attimo prima del passo successivo. |

Perché succede: l'FM-1 fa il lavoro di ogni millisecondo dentro il giro del suo programma, che con lo schermo dura fino
a 9 millisecondi (lo dice lui stesso in ogni sonda). Una sonda può cadere lì in mezzo. Il simulatore invece fa tutto
al millisecondo esatto. Ho fatto rileggere quelle due sonde al simulatore 6 e 5 millisecondi prima: **identiche**.

Adesso il confronto fa questa prova da solo: se una sonda è diversa la rilegge fino a 13 millisecondi prima (il ritardo
che l'FM-1 dichiara, più 4). Se così torna uguale è tempo, e il rapporto dice quale sonda e di quanto. Una sonda che per
tornare uguale andrebbe letta 300 millisecondi prima resta un errore: c'è una prova che lo controlla.

Con questa regola le tue due raccolte danno **0 errori, niente da guardare**. I rapporti rifatti sono fra i file.

Due cose viste, già note, che non sono errori:

* in 9 riavvii su 33 e in 8 su 38 l'FM-1 ha risposto dopo i 12 secondi, e il Pi lo ha fatto ritrovare all'USB. È come
  prima. Dal software non si può fare di più: allunga solo la prova di qualche minuto;
* in un riavvio RaspiMIDIHub ha perso 15 collegamenti dell'FM-1, e il Pi li ha rimessi da solo.

## 2. Il grid spento fino al riavvio del Pi

**Cosa è successo.** Dopo il banco hai fatto partire l'FM-1 completo. Hai premuto SEL, il banco ha fermato il bridge
del grid come fa sempre... e il bridge non ha finito. Il banco ha aspettato 20 secondi e si è fermato con un errore di
Python (0 sessioni). Il sistema ha aspettato 90 secondi, ha ucciso il bridge e lo ha lasciato "failed": da lì il grid è
rimasto spento. *Controlla la matrice* diceva solo `il servizio sagga-grid-bridge e' failed`. Hai riavviato il Pi, e la
prova dopo è andata.

**Perché.** La libreria MIDI che usa il bridge (python-rtmidi) ha un difetto nel modo di chiudere una porta
d'ingresso: se un messaggio arriva proprio mentre la porta si chiude, la chiusura aspetta il filo che ascolta la porta,
e quel filo aspetta la chiusura. Per sempre. Il registro del sistema lo mostra: quando ha ucciso il bridge erano
rimasti solo il programma e un filo. Lo stesso blocco aveva già fermato la prima prova dal tuo PC, tempo fa; allora
avevo sistemato gli strumenti della prova, ma **il bridge no**. È capitato una volta su cinque perché serve un messaggio
dell'FM-1 in quei pochi millisecondi.

**Cosa cambia.**

1. **Il bridge, quando gli dici di fermarsi, saluta e se ne va.** Spegne i Launchpad, avvisa l'FM-1, e il programma
   finisce lì, in un decimo di secondo. Non chiude più le porte una per una: le chiude il sistema, che non aspetta
   nessuno. Vale anche quando spegni il Pi.
2. **Se anche il saluto si piantasse**, dopo 8 secondi il bridge finisce da solo e scrive nel suo registro dov'era
   fermo. E il sistema adesso gli dà 15 secondi, non 90.
3. **Il banco non si fida più.** Se il bridge non si ferma lo fa chiudere dal sistema, lo dice nel log e va avanti con
   la prova. Niente più errore di Python. Alla fine lo fa ripartire **sempre**, e se non riparte lo scrive, con cosa
   premere.
4. ***Controlla la matrice* adesso lo ripara.** Se trova il bridge fermo quando dovrebbe girare, lo fa ripartire e lo
   dice: `Il bridge del grid era fermo (failed): l'ho fatto ripartire, il grid torna.` Non serve riavviare il Pi.

## 3. La domanda "premi SEL" che spariva

Guardando i log ho visto una cosa che si ripete **in tutte e cinque le prove** (e nelle due della 0.32): la prima
richiesta di premere SEL va a vuoto (`nessun tasto premuto in 20 secondi`), e il sì arriva solo alla seconda. Non eri
tu a essere lento.

Prima della prova il banco chiede all'FM-1 il progetto che ha in memoria, per rimetterglielo alla fine. Il bridge
sentiva passare quel progetto, lo salvava anche lui nella libreria e rispondeva all'FM-1 `SAVED ON THE PI`. Quella
scritta arrivava un secondo dopo la domanda `PC TEST? SEL = YES` e la copriva. Poi lo schermo tornava normale: la
domanda c'era ancora, ma non si vedeva più.

L'ho rifatto nel simulatore con il firmware 0.32.1: con quella risposta la domanda sparisce dopo un secondo; senza,
resta sullo schermo per tutti i venti secondi.

**Adesso** il banco avvisa il bridge prima di chiedere il progetto, e il bridge quella copia la lascia passare: niente
scritta, la domanda resta. **Dovresti poter premere SEL alla prima richiesta**, e ogni prova parte venti secondi prima.

## 4. Un progetto in più nella libreria a ogni prova

È la stessa causa della sezione 3: il bridge salvava nella libreria la copia del progetto che il banco chiede. **Ogni
prova lasciava un file in più** (`sagga-009.sgq` ... `sagga-013.sgq` sono delle ultime cinque prove; le prove di prima
ne hanno lasciati altri). Adesso non succede più.

Il SAVE dal grid, l'EXPORT dai tasti dell'FM-1 e l'editor della pagina salvano come prima.

I file già lasciati restano dove sono: non so distinguerli con certezza dai tuoi, quindi non li tocco. Sono copie del
progetto che l'FM-1 aveva in memoria quel giorno. Se vuoi toglierli: la SD nel PC, cartella `sagga`. La pagina del Pi
non ha un bottone per cancellare un progetto.

## 5. Due cose più piccole

* **L'installatore e il test dell'FM-1** chiudono le porte MIDI nello stesso modo sicuro. Lì il blocco non si è mai
  visto, ma il difetto della libreria è lo stesso.
* **`sagga_grid_bridge.py --export`** lanciato a mano mentre il servizio gira non lascia più due file (uno suo, uno del
  servizio).

## Come è stato provato

**Sul Pi vero non ho potuto provare niente**: qui non ci sono né porte MIDI né il sistema che fa partire i servizi.
L'FM-1 vero non c'entra: il suo firmware non è cambiato. Quello che ho potuto fare:

| la prova | il risultato |
| --- | --- |
| le tue due raccolte dell'FM-1 vero (0.32.1), con il confronto nuovo | 0 errori tutte e due, niente da guardare |
| il blocco rifatto in piccolo: quaranta righe di C con la stessa forma della libreria MIDI | la chiusura di prima, con un messaggio in arrivo, **non torna mai**; le tre chiusure nuove (bridge, installatore, test) tornano sempre, anche con un messaggio ogni decimo di millisecondo |
| il bridge vero fatto partire con porte finte che non finiscono mai di chiudersi | fermato, saluta ed esce in un decimo di secondo senza toccarle; con le chiusure di prima non esce mai |
| un saluto che non finisce mai | il bridge esce da solo dopo il suo tempo e dice dov'era fermo |
| il banco con un bridge che non si ferma, uno che non riparte, uno trovato fermo | la prova va avanti, il bridge riparte, tutto detto nel log; nessun errore di Python |
| la domanda sullo schermo, nel simulatore con il firmware 0.32.1 | coperta dopo un secondo con la risposta del bridge; resta venti secondi senza |
| il progetto chiesto da un altro programma | il bridge non lo salva e non risponde; il SAVE del grid e l'editor salvano come prima |
PROVE_QUI

## Installare

Solo il Pi: sulla pagina, **AGGIORNA IL PI**, `sagga-hub-0.32.2.zip`. L'FM-1 non si tocca.

Questa volta l'aggiornamento può metterci fino a un quarto di minuto in più: sta fermando il bridge vecchio, che ha
ancora il difetto.

## Cosa guardare la prima volta

* **Avvia la prova**: la domanda `PC TEST? SEL = YES` deve restare sullo schermo dell'FM-1. Premi SEL alla prima
  richiesta.
* Nel log della prova, dopo il sì: `il bridge del grid e' fermo per la prova` deve arrivare subito, e alla fine
  `il bridge del grid riparte`.
* Nella libreria non deve comparire un `sagga-NNN.sgq` nuovo dopo la prova.
* Se mai il grid resta spento: **Controlla la matrice**.
