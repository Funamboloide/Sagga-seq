# SAGGA SEQ 0.18 - Installazione

Il firmware: il tablet ha una traccia sua, SAGGA Live (canale 12), l'FM-1 rimanda i valori alle pagine del hub, il
grid segue l'FM-1 (FOLLOW), ARP RATE 1/2 e 1/4 (`RELEASE-NOTES-0.18.md`). Il formato resta `SGQB`, slot e progetti si
aprono come sono.

* **Il Pi** (questa volta cambia): metti `sagga-hub-0.18.zip` come scritto in `SAGGA-SEQ-0.15-INSTALL.md` (passo 1,
  con il nome nuovo dello zip). `install_hub.sh` copia anche la pagina nuova, **SAGGA Live**, e la SAGGA Mod
  aggiornata, poi riavvia il hub.
* **Il hub, una volta**: nell'interfaccia web aggiungi **SAGGA Live** (fra i controller). Nella matrice: il suo OUT
  verso la porta 2 dell'FM-1 ("Felucca MIDI 2"), come le altre; poi **la porta 2 dell'FM-1 verso l'IN di ogni pagina
  SAGGA** (Remote, Mutes, Motori, Break, Mod, Live): sono i valori che tornano. Save Config. Sull'FM-1: SAVE K2 =
  REMOTE 13 + 14, USB PORTS 2 (SAVE 3 K1, poi SEL + K1 due volte).
* **L'FM-1**: FM-1 collegato al Pi e fermo, pagina `http://10.249.215.136:8090`, carica `sagga-0.18.fwsc`, **Installa**.
  Dopo il riavvio lo schermo dice `SAGGA SEQ 0.18`. (Dal PC: `py .\fm1_install.py .\sagga-0.18.fwsc`.)

## Prova

1. SEQ + nero 7 tenuto (BAND), PLAY. Sull'FM-1 resta sulla traccia 1.
2. **Il tablet**: apri SAGGA Live, **TRACK** su T5. Gira **ARP** su UP e **RATE** su 1/4: la traccia 5 arpeggia una
   nota ogni quarto, lo schermo dell'FM-1 dice `TAB T5: ...`, e l'FM-1 è ancora sulla traccia 1.
3. **I valori che tornano**: sull'FM-1 vai sulla traccia 5 (nero 5), ARP tenuto, gira K1: la manopola ARP sul tablet si
   muove. Fai un mute dal pannello (PERF, un bianco): il MUTE corrispondente su SAGGA Live si accende.
4. **MIDI FX dal tablet**: MIDI FX su ECHO (`TAB T5 MIDI FX ECHO READY: GO`), **FX GO**: l'eco parte; FX GO di nuovo:
   si ferma.
5. **Il grid**: SHIFT + STEP due volte (`FOLLOW: THE GRID GOES WITH THE FM-1`, SHIFT azzurro). Apri la finestra HOME
   sull'FM-1 (un tocco su HOME): il grid mostra le quattro manopole; la riga 6 è la LENGTH di tutte le tracce. Tocca
   un pad della riga 6: quella traccia prende la lunghezza della traccia dell'FM-1. Chiudi la finestra (HOME di nuovo):
   il grid torna agli step. Tocca GLO: il grid va su PERF.
6. **ARP lento sull'FM-1**: ARP tenuto, K3 tutto a sinistra: `ARP RATE 1/4: A NOTE EVERY 4 STEPS`.
