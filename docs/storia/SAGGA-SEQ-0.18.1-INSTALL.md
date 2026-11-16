# SAGGA SEQ 0.18.1 - Installazione

La 0.18 con il test dal PC che fa anche da tablet e da grid (`RELEASE-NOTES-0.18.1.md`). Sul pannello, sul tablet e sul
grid è la 0.18 (`SAGGA-SEQ-0.18-INSTALL.md`: le pagine del hub, la matrice, la prova in sei punti).

* **Il Pi**: se hai già messo la 0.18 non serve niente. Altrimenti `sagga-hub-0.18.1.zip` come la 0.18.
* **L'FM-1**: FM-1 collegato al Pi e fermo, pagina `http://10.249.215.136:8090`, carica `sagga-0.18.1.fwsc`,
  **Installa**. Dopo il riavvio lo schermo dice `SAGGA SEQ 0.18.1`. (Dal PC: `py .\fm1_install.py .\sagga-0.18.1.fwsc`.)

## L'esploratore sull'FM-1

1. Scompatta `sagga-esploratore-0.18.1.zip` in una cartella di Windows (per esempio nei Download).
2. FM-1 con la 0.18.1, **fermo**, collegato **direttamente al PC** con il cavo USB (non al Pi); niente sulla presa MIDI
   IN; Ableton e tutto quello che usa le porte MIDI chiusi.
3. In PowerShell, nella cartella:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_hw_explore.ps1
   ```
   La prima volta installa `mido` e `python-rtmidi` (serve Python 3.9+ e internet). Sullo schermo dell'FM-1:
   `PC TEST? SEL = YES, ANOTHER KEY = NO`: **premi SEL**. Da lì non toccarlo: per ogni sessione si riavvia nel test e
   suona da solo, una riga per sessione (`ok`, o cosa ha visto). Sono 25 sessioni, circa mezz'ora.
4. Alla fine l'FM-1 si riavvia normale e il tuo progetto torna in memoria (`IMPORTED: SAVE TO KEEP IT`: SAVE se vuoi
   tenerlo). Nella cartella c'è `raccolta-<data>.json`: mandamelo, faccio io il confronto con il simulatore.

Durante il test l'FM-1 non legge e non scrive nessuno slot; il progetto che avevi resta sul PC (`backup-<data>.sgq`) e
torna alla fine. Una mano su un tasto o una manopola lo ferma subito. Se il PC si ferma a metà, spegni e riaccendi
l'FM-1: il test vive solo nella RAM.
