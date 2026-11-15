# SAGGA SEQ 0.20 - Note di rilascio

Tre cose nuove sull'FM-1 (cinque MIDI FX in più con l'ordine scelto da te, gli inviluppi, la MOD MATRIX) e una sul Pi:
la **BeatStep Pro** come manopole, pad e uscite CV.

## I MIDI FX: nove, nell'ordine che vuoi

HOME 6 K1 ora mostra nove effetti: OFF, HARM, OCTAVE, ECHO, VEL CURVE e i cinque nuovi. Entrano ed escono dalla catena
come quelli della 0.19 (K1 ne mostra uno, SEQ + bianco 6 lo aggiunge o lo toglie, K1 su OFF + SEQ + bianco 6 li ferma
tutti).

| effetto | K2 | K3 | K4 |
| --- | --- | --- | --- |
| **CHANCE** | quante note passano, 0-100 % | OGNI NOTA (ognuna il suo tiro) / OGNI STEP (un tiro per l'accordo) | - |
| **RANDOM** | quanto si spostano le note: ±0-7 gradi della chiave (FREE: ±12 semitoni) | quanto si sposta la velocity, ±0-64 | QUANTE note, 0-100 % |
| **NOTE FILTER** | la nota più bassa che passa | la più alta | UNA OGNI 1-8 (1: tutte) |
| **GATE** | la durata ×1/4 ×1/2 ×3/4 ×1 ×3/2 ×2 ×4 | FISSA: OFF, 1/32 .. 2 BARS (vince sul fattore) | UMANA: ±0-50 % a caso |
| **GLITCH** | QUANTI step, 0-100 % | MIX (uno qualsiasi), STUTTER (lo step a pezzi), RISE (pezzi che salgono la chiave), JUMP (un'ottava su o giù), CUT (un clic di nota) | PEZZI 1-8 |

* **SEL + K1 in HOME 6: l'ordine.** L'effetto mostrato suona prima (a sinistra) o dopo (a destra); lo schermo dice
  l'ordine di quelli che suonano, con lui (`T1 ORDER OCT>FILT>HARM`). L'ordine di base è NOTE FILTER, CHANCE, VEL
  CURVE, RANDOM, OCTAVE, HARM, GATE, GLITCH, ECHO: i quattro della 0.19 restano come erano. Ogni effetto lavora su quello
  che gli arriva: l'ECHO dopo HARM ripete anche la voce, HARM dopo l'ECHO dà una voce a ogni ripetizione, un FILTER dopo
  OCTAVE vede la nota già spostata.
* Il progetto salva i valori e l'ordine. Un progetto della 0.19 si apre con i nuovi ai valori di base; la 0.19 apre un
  progetto della 0.20 con i quattro che conosce.
* **Il tablet** (SAGGA Live): MIDI FX va da 0 a 9; FX AMOUNT dei nuovi copre tutto il loro campo. **Il grid** (TRACK 3,
  riga 2): SHIFT + pad 2-6 sono CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH. **L'editor del Pi**: la catena nell'ordine in
  cui suona, con le frecce per spostare un effetto.

## Gli inviluppi: un LFO a forma di ENV

LFO pagina 1 K1 ha una nona forma, **ENV**: l'LFO sale da CENTER di DEPTH (INVERT: scende) a ogni nota della sua
traccia **TRIG** (pagina 3 K4), resta su finché la nota è tenuta e poi torna giù. **LFO pagina 5 ENV**: K1 ATTACK, K2
DECAY, K3 SUSTAIN 0-100 %, K4 RELEASE, da 0 a 4 battute. Con TRIG sul clock riparte a ogni ciclo della sua RATE.

## La MOD MATRIX: LFO pagina 6 MOD

Otto slot: K1 lo SLOT, K2 la SORGENTE, K3 la DESTINAZIONE, K4 QUANTO (-100 .. +100 %); **SEL + K2 / SEL + K3**: quale
(quale LFO, macro, traccia, CC).

* Sorgenti: **LFO 1-16** (un LFO con destinazione **MOD ONLY**, la nuova ultima di pagina 2 K1, non manda niente: serve
  solo a modulare), **MACRO** INTENSITY / GATE / SWING / FILTER, **ENERGY** (quella delle MOSSE), **RANDOM** (un valore
  nuovo ogni sedicesimo), **VEL T1-T16** (l'ultima velocity di quella traccia), **CC IN** (un CC dal MIDI IN: LFO + REC
  sulla pagina 6 lo impara).
* Destinazioni: **DEPTH** e **CENTER** degli LFO; **VEL, GATE, CHANCE, TIMING, SWING** delle tracce; **FX T1-T16**: la
  profondità della catena di MIDI FX della traccia (-100 %: niente .. +100 %: il doppio).

## La BeatStep Pro

* **Le uscite CV e gate**: la BeatStep Pro converte il MIDI in CV. Nella matrice del hub `Felucca MIDI 1` verso la
  BeatStep Pro, solo canali 1, 2 e 10: il canale 1 esce dalle prese del suo sequencer 1 (pitch, gate, velocity), il 2
  dal sequencer 2, le note 36-43 del canale 10 dagli 8 gate della batteria.
* **Manopole e pad**: il nuovo plugin **SAGGA BeatStep** del hub. La BeatStep Pro in modo CONTROL verso il suo IN, il
  suo OUT verso la porta 2 dell'FM-1. **LEARN**: giri le 16 manopole una dopo l'altra, poi tocchi i 16 pad. Le manopole
  sono quelle di SAGGA Live sulla traccia del tablet; i pad sono i 16 MUTE, o le AZIONI (PLAY, FILL, FX GO, ALGO GO,
  COOK, BEAT, DICE, UNDO, PROPOSAL, QUEUE, KEEP, BACK, RETRIG, MUTE, EUCLID, ECHO ALL).

## I progetti

Il formato resta `SGQB`: i nuovi effetti, l'ordine, gli inviluppi e la MOD MATRIX stanno nel blocco di estensione. Un
progetto della 0.19 o di prima si apre come era.

**Il Pi cambia** (l'editor, il convertitore, SAGGA Live e il nuovo SAGGA BeatStep): `sagga-hub-0.20.zip`, vedi
`docs/SAGGA-SEQ-0.20-INSTALL.md`.

## Sotto il cofano

* `sagga_seq_core.c`: `sq_mfxd_t` (i nuovi cinque e l'ordine dei nove), `sq_lfoe_t` (l'inviluppo di ogni LFO),
  `sq_mod_t` (gli otto slot) in `sq_ext_t`, che passa da 1004 a 1508 byte; `sq_env_level`, `sq_mfx_order_move`.
* `dinghy.c`: `mfx_run`, la catena come una fila di eventi (ogni effetto li cambia, ne toglie o ne aggiunge; la nota
  esce, il resto va agli ornamenti); `mod_service` (la MOD MATRIX prima degli LFO); `env_out`.
* Test: il core, il simulatore (`t020_new_fx`, `t020_env_mod`), l'esploratore (una situazione nuova), l'editor, i
  plugin (anche dentro l'host vero di RaspiMIDIHub).
