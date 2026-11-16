# SAGGA SEQ 0.18.1 - Note di rilascio

Una correzione piccola sotto il cofano, per provare la 0.18 sull'FM-1 vero: **l'esploratore dal PC adesso fa anche da
tablet e da grid**. Sul pannello, sul tablet e sul grid non cambia niente rispetto alla 0.18.

* **Il test dal PC manda anche il MIDI** (`firmware/src/sagga_test.c`, un evento nuovo): i comandi delle pagine del hub
  (SAGGA Live sul canale 12, TRACK sul canale 13) e i pad e i bottoni del grid arrivano all'FM-1 come se venissero dal
  Pi, sulla porta del remoto. Così le sessioni dell'esploratore provano sull'hardware anche la traccia del tablet, i
  valori che tornano (con USB PORTS 2), FOLLOW e la copia sulle 16 tracce.
* **Dove l'FM-1 prende un evento** lo dice con il tick di clock di prima dell'evento, non di dopo: un salto del grid a
  una battuta (vista PROJ, riga 8) sposta il clock, e il confronto con il simulatore vedeva un CLOCK diverso che non
  c'era.
* La sonda dice anche il grid in FOLLOW, la traccia del tablet e se il tablet ha parlato.
* Il programma di Windows controlla la versione: un piano con il tablet e il grid su un FM-1 più vecchio della 0.18.1
  non parte (non tocca niente).
* L'esploratore nel simulatore ha due situazioni nuove (tablet e grid con una e con due porte USB) e i comandi del
  tablet fra i gesti: 0 errori. Le note 100-115 sul canale 13 che tornano al tablet (gli interruttori degli LFO) e le
  luci del grid non sono "note appese".

Il formato resta `SGQB`; il Pi è quello della 0.18 (`sagga-hub-0.18.1.zip` è lo stesso, con il nome nuovo).
