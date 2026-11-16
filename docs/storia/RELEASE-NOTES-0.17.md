# SAGGA SEQ 0.17 - Note di rilascio

Una cosa sola, ma grossa: **VIAGGIO non è più una modalità**. Fino alla 0.16 era una tastiera a parte (SEL + GLO), dove
gli stessi tasti facevano altro, e il viaggio partiva solo quando lo accendevi. Adesso è dentro ogni set:

0. **il viaggio gira sempre**: frasi, coda, energia e traccia (il "trail") ci sono da quando premi PLAY; a energia 50,
   con niente in coda, non cambia niente: la musica suona come l'hai scritta;
1. **le MOSSE sono la pagina 3 di PERF** (GLO 3): i neri sono FILL, BREAK, RISER, DROP, HALF, DOUBLE, THIN, SWELL,
   INDIETRO, ANNULLA, NOW, e succedono **alla fine della frase**, da sole. **SEL + GLO** apre PERF su quella pagina;
2. **le proposte si fanno in SEQ**: **SEQ + BEAT tenuto** mette la variazione su un pattern libero, **PRESETS** la manda
   in coda;
3. **il set si registra sempre**: **SAVE + bianco 16** trasforma quello che hai suonato in scene e song, in qualunque
   modo tu l'abbia suonato.

Il formato resta `SGQB`; il Pi non cambia (stesso zip della 0.16, con il nome nuovo).

## Perché

FX e MOSSE adesso sono due cose diverse e chiare:

* **FX**: succede **adesso**, finché tieni il tasto (LOOP, REPEAT, gli effetti, i macro);
* **MOSSE**: succede **alla fine della frase**, da sola (o alla battuta, o al quarto: MOVES AT).

Le tracce dentro e fuori le fai con i mute di PERF (con MUTE QUEUE e QUANTISE aspettano la battuta o la frase), il genere
e la tonalità con K3 / K4 della pagina MOSSE, le proposte in SEQ. Sparisce una tastiera intera e il manuale si accorcia
di un capitolo.

## Le MOSSE: PERF pagina 3

Ci arrivi con **SEL + GLO** (apre PERF direttamente sulla pagina 3; SEL + GLO di nuovo: torni allo studio), con GLO +
OCT+ fino alla pagina 3, oppure tenendo GLO sulla pagina 3 da qualunque modo. Lo schermo: `PERF 3/3 MOSSE  AT PHRASE`,
le celle ENERGY, PHRASE BAR (la battuta della frase), GENRE, KEY (con `>` quando uno è in coda), sotto la coda.

| nero | mossa | alla fine della frase |
|---|---|---|
| 1 | FILL | l'ultima battuta riempie (le condizioni FILL dei passi, ghost note su tutte le tracce); chiesto nell'ultima battuta: subito |
| 2 | BREAK | 1 battuta con la sola traccia selezionata; con SEL: 2 battute di silenzio, poi tutto torna |
| 3 | RISER | le ultime 4 battute di una frase da 8 o 16 salgono a energia 100 |
| 4 | DROP | un fill nell'ultima battuta, poi tutte le tracce con note dentro ed energia 100 |
| 5 / 6 | HALF / DOUBLE | tutto a metà / al doppio per una frase |
| 7 | THIN | fuori le due tracce più alte nella scala del genere (mai l'ultima), sfumando |
| 8 | SWELL | dentro due tracce, le più vicine all'energia |
| 9 | **INDIETRO** | torna la frase prima (pattern, mute, tonalità, genere, progressione, energia); era OCT- |
| 10 | **ANNULLA** | toglie l'ultima mossa in coda; era OCT+ |
| 11 | NOW | la coda alla prossima battuta invece che alla fine della frase (fermo: subito) |

I neri accesi sono le mosse in coda (il 10: c'è qualcosa da annullare; l'11 lampeggia mentre NOW aspetta la battuta).
I bianchi restano i mute di PERF (SEL + bianco: solo). Le manopole:

* **K1** l'energia (0-100, 50 neutro), **K2** la frase (4, 8, 16 battute), **K3** il genere, **K4** la tonalità (in coda
  mentre suona, subito da fermo);
* **ALG: MOVES AT** (alla frase, a ogni battuta, a ogni quarto; era K2 nella modalità VIAGGIO);
* **PRESETS: la progressione** (in coda). Con l'ARMONIA spenta la mette READY (`READY ...: ARP 3 K1 ON`), come ARP 3 K2
  dalla 0.16: non la accende più da sola. Anche la mossa PROG, quando arriva, lascia l'armonia come l'hai lasciata tu;
* SEL + ALG il tempo; **SEL + PLAY** da fermo: il SEED (genere, tonalità e tempo a caso).

Sulle pagine 1 e 2 di PERF i neri restano le scene, come sempre. Con HOME tenuto i neri restano la song.

## Il viaggio gira sempre

* La frase conta da PLAY (16 battute di default), la coda gira alla fine, il trail tiene le ultime 128 frasi.
* Energia 50 = niente: velocity, filtro, gate, densità come scritti, gli LFO al 100 % (con VIAGGIO acceso fino alla 0.16
  a energia 50 gli LFO erano al 75 %; sotto 50 adesso sono più leggeri, fino al 50 % a energia 0).
* Gli stati delle tracce (VUOTA, PROPOSTA, DENTRO, FUORI) seguono le tue mani a ogni fine frase: un mute in PERF, una
  scena, un pattern cambiato. THIN, SWELL e il trail vedono la musica com'è.
* "Nessun silenzio per sbaglio" (una traccia tenuta quando le mosse non ne lasciano nessuna) vale solo per il silenzio
  fatto dalle mosse: un silenzio fatto da te resta.
* **PALCO** (SAVE + K4) parte sulle MOSSE; lì SEQ non fa più uscire da PERF (PALCO non ha SEQ).

## Le proposte in SEQ

* **SEQ + BEAT (bianco 10) tenuto 0,6 s**: quello che BEAT scriverebbe (genere, parte e variazione di SEQ) va in un
  pattern **libero** della traccia selezionata; il pattern che suona non si tocca. Lo schermo: `PROPOSAL KICK #1 IN P2:
  PRESETS QUEUES IT`. Tenuto di nuovo: la variazione dopo, nel pattern libero dopo.
* **PRESETS** (senza niente tenuto): la prima girata mette in coda la proposta (`T1 PROPOSAL P2 QUEUED`); entra al
  QUANTISE con le sue impostazioni (lunghezza, divisione, swing, groove). Le girate dopo scorrono i pattern come sempre.
* **BEAT toccato** scrive sul pattern che suona, come prima; adesso agisce quando lasci il tasto (come UNDO e COOK).
* Una proposta non prende mai un pattern scritto a mano: se non c'è un pattern vuoto sostituisce la proposta più
  vecchia, altrimenti `NO FREE PATTERN ON THIS TRACK FOR A PROPOSAL`. UNDO la toglie.

## Il set si registra sempre

**SAVE + bianco 16** prende le frasi suonate (le corse di frasi uguali) e ne fa le scene 1.. e la song, che le suona per
quante battute sono durate. Funziona sempre, anche se le MOSSE non le hai mai aperte. Poi salva il progetto come al
solito.

## Griglia e remoto

La vista VIAGGIO del grid e il remoto sul canale 13 funzionano come prima (tracce, proposte, dadi, SWAP, LOOP, la
coda, l'energia, il trail); non accendono più niente. Il tasto PERF del grid apre sempre prima PERF (fino alla 0.16, con
VIAGGIO acceso, apriva VIAGGIO). SWAP e LOOP restano sulla vista VIAGGIO e sui CC 25 / 26 del canale 13.

## Progetti

* Un progetto salvato con VIAGGIO spento suona come prima (la sua energia torna a 50).
* Uno salvato con VIAGGIO acceso tiene energia, frase e stati delle tracce.
* Un progetto della 0.17 aperto su una 0.16 parte con VIAGGIO acceso.

## Sotto il cofano

* `sagga_seq_core.c`: `sq_viaggio_default` / `sq_viaggio_sanitize` con il viaggio sempre acceso (spento nel progetto:
  energia 50); `sq_energy_map`: gli LFO al 100 % da 50 in su.
* `sagga_viaggio.c`: via `vg_mode` / `vg_mode_set` / la tastiera VIAGGIO; `vg_move_black` (i neri delle MOSSE),
  `vg_mosse_open`, `vg_panel_toggle` (SEL + GLO), `vg_pattern_in` (una proposta che entra porta le sue impostazioni,
  chiamato dal QUANTISE, dalla fine del loop e da PRESETS), `vg_prop_queue` (PRESETS), `beat_propose` (SEQ + BEAT
  tenuto); gli stati risincronizzati a ogni fine frase, con i mute "veri" (non quelli di un BREAK).
* `dinghy.c`: `perf_black` sulla pagina 3 manda alle MOSSE; ALG e PRESETS della pagina 3; via il blocco manopole e OCT
  della modalità VIAGGIO e SEL + GLO tenuto; `sagga_ui.c`: la schermata MOSSE; `sagga_pick.c`: BEAT fra i tasti SEQ che
  si possono tenere, le mappe dei tasti.
* Test: il core (un progetto con VIAGGIO spento, il progetto nuovo, gli LFO), il simulatore (i test di VIAGGIO riscritti
  sulle MOSSE, il grid e il remoto; `t017_mosse`: il viaggio senza aprire niente, BREAK con GLO tenuto, SAVE + bianco
  16, le pagine; `t017_proposal`: la proposta, la seconda, PRESETS, BEAT toccato), l'esploratore (la situazione MOSSE).
