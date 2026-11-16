# SAGGA SEQ 0.19 - Installazione

I quattro MIDI FX in catena sulla stessa traccia (`RELEASE-NOTES-0.19.md`). Il formato resta `SGQB`: slot e progetti si
aprono come sono, il MIDI FX che avevano diventa la catena.

* **Il Pi** (questa volta cambia, per l'editor): metti `sagga-hub-0.19.zip` come scritto in `SAGGA-SEQ-0.15-INSTALL.md`
  (passo 1, con il nome nuovo dello zip). `install_hub.sh` copia l'editor e il convertitore nuovi, poi riavvia il hub.
  La matrice e le pagine SAGGA restano come le hai.
* **L'FM-1**: FM-1 collegato al Pi e fermo, pagina `http://10.249.215.136:8090`, carica `sagga-0.19.fwsc`, **Installa**.
  Dopo il riavvio lo schermo dice `SAGGA SEQ 0.19`. (Dal PC: `py .\fm1_install.py .\sagga-0.19.fwsc`.)

## Prova

1. Una traccia con qualche step acceso su un synth, PLAY.
2. **Tocca HOME**, OCT fino a `HOME 6/8 MIDI FX`. **K1** su `ECHO`: `T1 MIDI FX ECHO READY: SEQ + WHITE 6`. **Tocca
   HOME**, **tocca SEQ**, **bianco 6** (non sulla pagina `SEQ 2/7`): l'eco parte. **Tocca SEQ**.
3. Di nuovo in HOME 6: **K1** su `HARM`, poi SEQ + bianco 6: `T1 MIDI FX HARM STARTS: HARM+ECHO`. Senti la seconda voce,
   e l'eco ripete tutte e due.
4. **K1** su `OCTAVE`, SEQ + bianco 6: `HOME 6/8 FX OCT+HARM+ECHO`. Ogni due step la nota sale d'ottava, e la voce con
   lei.
5. **K1** di nuovo su `ECHO`: `T1 MIDI FX ECHO PLAYS: SEQ + WHITE 6 TAKES IT OUT`. SEQ + bianco 6: l'eco esce, il resto
   continua.
6. **K1** su `OFF`, SEQ + bianco 6: si fermano tutti.
7. **Il tablet** (SAGGA Live, TRACK su un'altra traccia): MIDI FX su ECHO, **FX GO**; MIDI FX su HARM, **FX GO**: sullo
   schermo dell'FM-1 `TAB T..: MIDI FX HARM STARTS: HARM+ECHO`. FX GO di nuovo: HARM esce.
8. Salva (tocca SAVE due volte), spegni e riaccendi: la catena c'è ancora, ogni effetto con i suoi valori.
