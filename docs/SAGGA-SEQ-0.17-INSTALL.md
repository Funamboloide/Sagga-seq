# SAGGA SEQ 0.17 - Installazione

Il firmware: VIAGGIO non è più una modalità. Il viaggio gira sempre, le MOSSE sono la pagina 3 di PERF (SEL + GLO), le
proposte si fanno con SEQ + BEAT tenuto, SAVE + bianco 16 registra sempre il set (`RELEASE-NOTES-0.17.md`). Il formato
resta `SGQB`, slot e progetti si aprono come sono.

* **Il Pi**: metti `sagga-hub-0.17.zip` come scritto in `SAGGA-SEQ-0.15-INSTALL.md` (passo 1, con il nome nuovo dello
  zip). Rispetto alla 0.16 non cambia niente: se hai già la 0.16 sul Pi puoi lasciarla.
* **L'FM-1**: FM-1 collegato al Pi e fermo, pagina `http://10.249.215.136:8090`, carica `sagga-0.17.fwsc`, **Installa**.
  Dopo il riavvio lo schermo dice `SAGGA SEQ 0.17`. (Dal PC: `py .\fm1_install.py .\sagga-0.17.fwsc`.)

## Prova

1. Scrivi due tracce a mano (o SEQ + nero 7 tenuto: BAND). GLO tenuto, OCT+ fino alla pagina 3, K2 tutto a sinistra:
   la frase è di 4 battute. PLAY: suona tutto come scritto, energia 50.
2. **SEL + GLO**: lo schermo dice `PERF 3/3 MOSSE  AT PHRASE`. **Nero 2** (BREAK): alla fine della frase una battuta
   con la sola traccia selezionata, poi tutto torna.
3. **Nero 1** (FILL), poi **nero 10**: `CANCELLED FILL`, la coda è vuota.
4. **Nero 7** (THIN): alla fine della frase escono due tracce, sfumando; **nero 8** (SWELL): rientrano.
5. **Nero 9** (INDIETRO): alla fine della frase torna quella prima.
6. **K1** a destra: l'energia sale battuta per battuta fino alla fine della frase (velocity, filtro, ghost note).
7. **SEL + GLO** di nuovo: sei nello studio, il viaggio continua sotto.
8. **Proposta**: seleziona la traccia della cassa, SEQ tenuto, **BEAT (bianco 10) tenuto** finché lo schermo dice
   `PROPOSAL KICK #1 IN P2: PRESETS QUEUES IT`: la cassa che suona non cambia. Lascia SEQ, gira **PRESETS** di uno:
   `T1 PROPOSAL P2 QUEUED`, alla fine del loop entra la cassa nuova.
9. **Il set**: dopo qualche frase, **SAVE + bianco 16**: `JOURNEY SAVED: n SCENES AND THE SONG`. HOME + GLO: la song
   rifà quello che hai suonato.
