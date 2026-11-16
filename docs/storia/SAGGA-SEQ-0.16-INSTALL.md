# SAGGA SEQ 0.16 - Installazione

Il firmware: il MERENGUE come 25° genere, i pattern dei generi entrano con il loro GROOVE, gli algoritmi si preparano prima di partire,
l'armonia FREE, EDIT + ARP copia la progressione (`RELEASE-NOTES-0.16.md`). Il formato resta `SGQB`, slot e progetti si
aprono come sono.

* **Il Pi**: metti `sagga-hub-0.16.zip` come scritto in `SAGGA-SEQ-0.15-INSTALL.md` (passo 1, con il nome nuovo dello
  zip): porta i pattern e le progressioni del merengue e il genere nuovo nella pagina SAGGA Mod. Senza, l'FM-1 funziona
  lo stesso, il Pi non ha le variazioni del merengue oltre le 12 dell'FM-1.
* **L'FM-1**: FM-1 collegato al Pi e fermo, pagina `http://10.249.215.136:8090`, carica `sagga-0.16.fwsc`, **Installa**.
  Dopo il riavvio lo schermo dice `SAGGA SEQ 0.16`. (Dal PC: `py .\fm1_install.py .\sagga-0.16.fwsc`.)

## Prova

1. SEQ + PRESETS su **UK GARAGE**, poi **BAND** (SEQ + nero 7 tenuto). Seleziona la traccia dell'hat, HOME pagina 7: `GROOVE
   GARAGE 100%`; HOME pagina 2: swing 50. La traccia del basso: GROOVE OFF, swing 63.
2. PLAY: lo shuffle del 2-step su tutta la band, la cassa e il basso insieme agli hat.
3. **DICE GROOVE** (SEQ + nero 4): il feel si muove di poco, il template resta.
4. **Algoritmo preparato**: SEQ tenuto, OCT+ a SEQ 2. K1 su DENSITY (`ALGO 1 READY`), K2 tutto a sinistra (0 %): suona
   ancora tutto. SEQ + bianco 6: la traccia tace subito (DENSITY parte a 0, non a 100). SEQ + bianco 6 di nuovo: torna.
5. **FREE**: ARP 4 K2 tutto a sinistra (`FREE`), poi ARP 3 K2: le progressioni di tutti i generi. Carica un pattern di
   un altro genere: gli accordi non cambiano.
6. **Copia**: con una progressione che suona, EDIT + ARP: `COPIED TO USER 1`. Su ARP 5 cambia un accordo.
7. **Armonia preparata**: ARP 3 K1 su OFF, K2 su un'altra progressione (`READY ...: K1 ON`): gli accordi non cambiano.
   K1 su ON: parte quella scelta.
8. **MIDI FX preparato**: HOME 6, K1 su ECHO (`T1 MIDI FX ECHO READY`), K2 su 4 ripetizioni: ancora niente eco. SEQ +
   bianco 6: l'eco parte con 4 ripetizioni.
9. **Merengue**: HOME 3 la chiave in C maggiore, SEQ + PRESETS fino a `MERENGUE`, SEQ + nero 7 tenuto (BAND):
   `MERENGUE BAND #1: 9 TRACKS`. PLAY: la cassa in quattro, la güira «cha chi-ki», la tambora, il basso che anticipa.
