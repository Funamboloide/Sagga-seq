# SAGGA SEQ 0.12 - Note di rilascio

La 0.12 è fatta delle richieste sulla 0.11: le note lunghe e il legato che si devono vedere; le idee di Skiff (il
firmware live per l'FM-1) che valeva la pena rubare; studio e VIAGGIO che non devono essere compartimenti stagni; le
pagine distribuite meglio fra i tasti; **le finestre: un tocco al posto del tasto tenuto**; scegliere con i tasti e
non solo con le manopole; il BREAK, gli slice di un break di batteria per la jungle e non solo; e tre pagine nuove
per il RaspiMIDIHub. Il formato resta **`SGQB`**: i progetti, gli snapshot e la libreria del Pi della 0.11 si aprono
come sono (i campi nuovi delle tracce, le impostazioni del BREAK, partono dai loro valori di base). La mappa dei tasti
cambia: è la tabella in `docs/SAGGA-SEQ.md`.

## Le finestre: un tocco al posto del tasto tenuto

* **Un tocco su HOME, SEQ, EDIT, ENV, LFO, ARP o FX apre la finestra del tasto** (premuto e lasciato entro 0,6 s senza
  fare altro): da lì in poi è *come se lo tenessi premuto*: le manopole e lo schermo sono i suoi, **i tasti sono i suoi**
  (SEQ: i TOOLS e i dadi; LFO: gli LFO; HOME: le tracce; EDIT ed ENV: il cursore e gli strumenti dello step; ARP: la
  tastiera suona la traccia; FX: gli effetti e i loop), **OCT- / OCT+ sfogliano le sue pagine**, **SEL + tasto è il PICK**.
  Lo stesso tasto toccato di nuovo la chiude; un altro tasto-finestra apre la sua al posto; un tasto **tenuto davvero**
  vince sempre e, lasciato, la finestra resta. Il pulsante della finestra aperta è acceso pieno; la mappa dei suoi
  tasti compare dopo mezzo secondo e resta quattro secondi.
* **GLO è già una finestra: il PERF** (il tocco di sempre; chiude le altre). Novità: in PERF **OCT- / OCT+ sfogliano le
  tre pagine di GLO** (LIVE, TRACK LIVE, VIAGGIO); MUTE / SOLO dei bianchi è passato a **SEL + OCT- / OCT+**.
* **SAVE non ha finestra**: il tocco salva (due volte), tenuto = le sue pagine, come prima.
* I due vecchi tocchi sono sotto SEL: **SEL + ARP** = arpeggio on / off; **SEL + FX** = il prossimo gesto a due step è
  un LOOP. ARP da solo apre la sua finestra (la tastiera suona la traccia finché non la chiudi), FX la sua.

## Le pagine: il tasto dice di cosa si parla

* **HOME 7** (la traccia: TRACK, PLAY, KEY, MODE, LOOPS, MIDI FX, TIMING), **GLO 3** (il live: LIVE, TRACK LIVE,
  **VIAGGIO**, che era HOME 8), **SEQ 7** (il ritmo e i generatori: EUCLID, ALGORITHM, EVOLVE, EXPO, EXPO 2, TOOLS,
  **BREAK**), **ARP 6** (le note, gli accordi, **l'armonia e le progressioni utente**, che erano SEQ 4 e SEQ 8: ARP, CHORD,
  HARMONY, HARMONY 2, USER PROG, USER PROG 2), EDIT (lo step; **SEL + manopole: le sue quattro note**), ENV 6, LFO 3, FX
  (**SEL + manopole: i THROWS**), **SAVE 3** (SYSTEM: le porte USB, le luci dei tasti).
* **GLO + OCT** gira le pagine di GLO; l'ottava live della traccia è **GLO + SEL + OCT- / OCT+**. In PERF (GLO toccato) le
  manopole seguono la pagina mostrata e **SEL + manopole è TRACK LIVE** come nella 0.11. La pagina USB (era HOME + SEL)
  è SAVE 3: la riconnessione è **SEL + K1 due volte**.
* I secondi significati dei tasti di SEQ si **tengono**: UNDO tenuto 0,6 s = REDO, COOK tenuto = il COOK a caso, KIT
  (nero 7) tenuto = BAND, DICE SEQ (nero 1) tenuto = DICE PROG. Il tocco agisce quando lasci il tasto. Così SEQ + SEL
  + tasto è libero per il PICK.
* **ARP + SAVE** manda la progressione al Pi (era SEQ + SAVE su SEQ 4 / 8); SEQ + SAVE manda sempre il pattern.

## PICK: scegliere con i tasti

**Tasto del gruppo + SEL + un tasto della tastiera = il valore della manopola a fuoco** della pagina mostrata. A fuoco
è l'ultima manopola girata su quella pagina (K1 all'inizio); lo schermo la segna con `>` davanti all'etichetta (`>-`
quando i tasti non possono impostarla: un valore continuo come una velocity resta alla manopola); **nero 11** passa il
fuoco alla manopola dopo. I tasti che valgono qualcosa sono accesi, quello del valore attuale lampeggia. La manopola
viene girata della differenza, così messaggi, limiti e battute attese sono gli stessi di quando la giri a mano.

| la manopola è | i tasti |
| --- | --- |
| una lista (un modo, una scala, una forma, un genere, un chop ...) | bianchi 1-16 = voci 1-16, neri 1-10 = voci 17-26 |
| un conteggio (pulsazioni, colpi, una traccia, una scena, un pattern) | bianchi 1-16, neri 17-26 |
| una lunghezza in step (LENGTH, un loop, i sedicesimi di un accordo) | bianchi 4, 8, 12 .. 64; neri 3 5 6 7 9 10 11 13 14 15 (le polimetrie) |
| una fondamentale (la KEY, la chiave di VIAGGIO, la radice di un accordo) | il tasto è la nota: da F3 a G5, cromatico |
| semitoni o gradi (TRANSPOSE, SHIFT, una CURVE) | F4 = 0, F3 = -12, G5 = +14 |
| una percentuale (heat, density, un gate, l'energia ...) | bianchi 1-10 = 10 .. 100 %, neri 1-10 = 5, 15 .. 95 % |
| una nota (EDIT + SEL: le quattro note dello step, quella a fuoco) | il tasto è la nota, con l'ottava della tastiera (SEL + OCT); gate e condizione restano alle manopole di EDIT |
| un numero di CC (di una lane, di un LFO) | 26 CC comuni: MOD, BREATH, PORTA, VOL, PAN, EXPR, 12, 13, RES, REL, ATT, CUTOFF, DEC, 76-78 sui bianchi; SUSTAIN, PORTA ON, REV, CHO, GP 1-4, BEND, AFTERTOUCH sui neri |

**La mappa dei tasti sullo schermo**: tieni un gruppo (anche FX, SAVE, SEL) mezzo secondo senza fare altro e le due
righe dei messaggi dicono cosa fanno i suoi tasti bianchi e neri, e cosa fa SEL + tasto per la manopola a fuoco.

**Il PICK dal grid**: la vista **PICK** (SHIFT + STEP due volte: CC, poi PICK) mostra le quattro manopole della finestra
aperta sull'FM-1 (quella di PERF se è acceso, HOME se non c'è nulla), una per riga: i pad 1-16 delle righe 1-4 sono i
tasti bianchi del PICK (voci 1-16, lunghezze 4..64, le note ...), i pad 1-10 delle righe 5-8 i suoi tasti neri 1-10; il pad
del valore attuale è bianco, una manopola che i tasti non possono impostare è una riga spenta; un pad imposta la
manopola (e la mette a fuoco).

## Le note lunghe e il legato come un blocco

* **Schermo**: una nota di N step è un blocco unico: la cella piena, le celle coperte e gli spazi fra loro riempiti in un
  verde più scuro; 1,5 step: mezza cella in più; TIE salda la cella alla successiva. Uno step acceso sotto una coda
  resta acceso.
* **Tastiera**: lo step pieno acceso, i tasti coperti in **glow** (il livello basso dei LED, mai usato finora da SAGGA);
  sotto EDIT ed ENV uguale, con il cursore che lampeggia.
* **Grid**: le celle coperte hanno il ruolo nuovo **TAIL** (verde scuro), lo step legato **TIE** (verde chiaro). Il bridge
  ha i due colori: va rimesso sul Pi (il vecchio bridge mostra DIM al loro posto).

## Studio e VIAGGIO: due strade, una traccia

* **SEL + GLO, un tocco**: la tastiera passa fra quella di VIAGGIO (tracce e mosse) e quella dello studio (gli step)
  **senza fermare il viaggio**: frasi, coda ed energia continuano. La prima volta accende il viaggio. **SEL + GLO tenuto
  0,6 s**: il viaggio si spegne (lo schermo: `VIAGGIO OFF`).
* Una traccia che scrivi, muti o svuoti a mano mentre il viaggio va **prende lo stato giusto da sola** (IN, OUT,
  EMPTY; PROPOSED se il pattern che suona è vuoto ma altri no): THIN, SWELL, l'energia e le proposte la vedono. Una
  traccia fatta in VIAGGIO è un pattern normale: in studio si edita come le altre, mentre il viaggio va.
* **GLO tenuto + tasti = i tasti di PERF** (mute, scene) in qualunque modo, anche in VIAGGIO e nello studio.

## BREAK: gli slice di un break

Un campionatore (M8, Digitakt, Simpler ...) ha il break tagliato in slice su note consecutive, dalla nota PEN della
traccia (SEL + K4). Una traccia in modo **BREAK** (HOME 4 K1: FREE / IN KEY / DRUM / TAPE / BREAK; nel grid il pad 14
della riga 4 di TRACK) suona slice: ogni step ne è uno (il numero nella cella NOTE e nella cella SLICE della pagina
STEP; la nota = PEN + slice - 1), gate = quanto dura, ratchet = roll, nudge, chance e condizioni come sempre; la lane
BEND è il pitch dello slice. La chiave non la tocca.

* **SEQ 7 BREAK**: K1 **CHOP**, la libreria dei riordini scritta sopra il loop, **sedici, uno per tasto bianco**: 1 STRAIGHT
  (gli slice in fila), 2 END ROLL (gli ultimi due step rullano), 3 RUSH (due corse verso i rullanti), 4 REPEAT (la prima
  metà due volte), 5 DOUBLE (uno slice sì e uno no, due volte), 6 HALF (ogni slice tenuto due step), 7 BACKWARDS, 8 GHOST
  (pause fra i colpi), 9 LOW (solo le casse), 10 HIGH (senza casse), 11 SHUFFLE (le coppie scambiate), 12 THINK, 13 APACHE
  (i primi due slice di nuovo sul tre), 14 SNARES (il rullante dappertutto), 15 TRIPLE (terzine contro il quattro), 16
  BUILD (ogni slice quattro volte); UNDO lo toglie. K2 **ROLLS** (quanti step rulla il dado), K3 **SWAP** (quanta parte della
  battuta il dado rimescola), K4 **SLICES** (8, 16, 32).
* **Il dado** (SEQ + nero 1, RANDOM) tiene la spina dorsale: slice 1 sul battere di uno e tre, slice 5 su due e quattro
  (con 16 slice: cassa e rullante), rimescola il resto e rulla; HEAT (SEQ 1 K4) dice quanto.
* **COOK cammina fra i chop del genere** della libreria (SEQ + PRESETS), quelli che gli appartengono, nel suo ordine:
  JUNGLE ha STRAIGHT, THINK, APACHE, SHUFFLE, SNARES, TRIPLE, END ROLL; TECHNO STRAIGHT, GHOST, HALF, LOW, END ROLL;
  FOOTWORK TRIPLE, RUSH, REPEAT, DOUBLE, SNARES, BUILD; e così gli altri ventuno (`sagga_seq_core.c`, `BRK_GENRE`). Lo
  schermo dice `END ROLL (JUNGLE 7/7)`; COOK tenuto ne pesca uno a caso.
* **ARP (tenuto, o la sua finestra): i bianchi 1-16 sono i chop, dal vivo.** Un tocco scrive il chop e resta (come la
  manopola); un tasto **tenuto** più di 0,6 s suona il suo chop finché lo tieni e **al rilascio torna il pattern di prima**
  (un altro bianco nel frattempo: il suo chop, sotto lo stesso pattern); il chop scritto lampeggia sui tasti. I neri:
  1 ROLL (l'ultimo slice suonato su questa traccia, o lo step che suona, ripetuto a ogni step finché tieni, in tempo con
  lo swing; ogni ripetizione dura mezzo step), 2 ROLL 1/32, 3 HALF (ogni slice due step), 4 DOUBLE, 5 BACKWARDS, 6 DICE,
  7 RESET (1..16), 8 / 9 il chop dopo / prima.
* **Gli slice si suonano con REC** (senza ARP): i bianchi 1-16, i neri 17-27 (un break da 32), scritti mentre suoni (TAKE
  se li ricorda); e dai pad del Pi (SAGGA Break) e dalla riga delle note del grid. Su qualunque altra traccia **ARP +
  tasti suona la traccia** senza registrare (le note, i colpi di una batteria).
* Uno step con **STEP LOCK** (EDIT + nero 1) resta com'è attraverso i chop, il dado e le mosse.
* Nel grid la riga delle note della vista STEP sono i 16 slice. Dal Pi: la pagina **SAGGA Break**.

## Da Skiff

* **TAKE** (REC tenuto 0,6 s): quello che hai suonato sulla tastiera, o che è entrato via MIDI, **nell'ultimo giro della
  traccia selezionata** finisce nel suo pattern, con REC o senza (l'FM-1 ricorda sempre le ultime 96 note, con il tick
  in cui sono iniziate e finite): quantizzato allo step (REC QUANTISED) o con il nudge (REC FREE), il gate lungo quanto
  hai tenuto la nota, la velocity suonata; un accordo su uno step aggiunge le sue note. UNDO lo toglie.
* **THROWS** (FX + SEL + K1..K4): i quattro macro INTENSITY, GATE, SWING, FILTER lanciati: da quando lasci la manopola
  tornano a 0 da soli in una battuta. FX + manopola da sola: il macro resta, come sempre.

## Il Pi: canale 13 e tre pagine nuove

Con REMOTE 13 + 14 (SAVE K2), il canale 13 risponde ai **CC dal 33 in su** oltre a quelli di VIAGGIO: 33-48 il pattern
della traccia 1-16, 49-64 la sua lunghezza, 65-75 le mosse e le impostazioni del BREAK, **76-91 i 16 slice come pad**,
92-97 un LFO (quale, SHAPE, RATE, DEPTH, DEST, on/off), 101-106 la base delle lane 1-6 della traccia selezionata, 107
TAKE, 108-111 i THROWS, 112 la traccia selezionata, 113 il suo modo, 114 ENERGY, 115 GENRE, 116 KEY, 117 la
progressione, 118 HARMONY. **Le note sul canale 13** suonano la traccia selezionata come i tasti con ARP tenuto (su un
BREAK le note 36-51 sono gli slice 1-16); **le note 100-115 accendono (note on) e spengono (note off) gli LFO 1-16**:
i sedici interruttori di SAGGA Mod, tutti sotto mano.

Le pagine (`tools/raspimidihub`, gratis come le altre): **SAGGA Motori** (le sedici tracce, una riga ciascuna: MUTE,
PATTERN, LENGTH, RETRIG, KILL; sotto la traccia selezionata, il suo MODE, DICE, UNDO, KEEP), **SAGGA Break** (sedici pad
slice, ROLL, ROLL/2, HALF, DOUBLE, BACKWARDS, DICE, RESET, TAKE, CHOP (i sedici), ROLLS, SWAP, SLICES), **SAGGA Mod** (un
LFO alla volta con le sue manopole, **i sedici interruttori L1-L16**, le sei lane, i quattro THROWS che tornano al centro
da soli, ENERGY, GENRE, KEY, PROGRESSION, HARMONY). SAGGA Remote ha TAKE. Vanno copiate sul Pi con le altre
(`tools/raspimidihub/README.md`).

## Il resto

* HOME 4 K1 si chiama MODE (era THIS TRACK); la pagina SYSTEM (SAVE 3) mostra le porte USB, la riconnessione senza
  staccare il cavo (SEL + K1 due volte) e le luci dei tasti; nel grid il pad del modo (TRACK, riga 4, pad 14) gira
  anche su BREAK.
* Le note che entrano via MIDI finiscono nella memoria di TAKE come quelle dei tasti.
* Dalla revisione prima di uscire: TAKE mette le note dove le metterebbe REC (lo step che suonava; nella seconda metà,
  quello dopo) e dimentica il giro precedente allo STOP; le note MIDI in entrata finiscono nella sua memoria anche senza
  REC; il ROLL ricorda lo slice per traccia, si ferma anche se la traccia cambia mentre il Pi lo tiene, e ogni colpo ha
  un gate; SEL + GLO con un tasto, una manopola o OCT nel mezzo non cambia pannello né spegne il viaggio; PERF + SEL
  mostra TRACK LIVE mentre le manopole lo fanno; ENERGY e PHRASE dai tasti vanno sul valore giusto; due tasti di SEQ
  tenuti insieme: il primo vale come tocco; le impostazioni BREAK di un progetto 0.11 partono dai valori di base
  (`sq_brk_half` prendeva anche le velocity sbagliate).
* L'esploratore conosce la mappa nuova (le pagine, i gruppi + SEL, i tasti tenuti, GLO + SEL + OCT, **le finestre**: un
  tocco, un tasto o una manopola o una pagina, un tocco), una situazione in più (una band JUNGLE con la traccia 1 in
  BREAK) e tre eccezioni spiegate (CHAIN, il pattern in coda su un loop di due step, il genere di VIAGGIO che porta con
  sé quello dell'armonia; il pad della riga 1 della vista PICK, che è il canale di HOME 1). Il passaggio lungo: 34 112 gesti
  da soli, 1 440 coppie, 30 sessioni, 0 errori. **Sull'FM-1 vero** (`tools/hwtest`): 20 sessioni da 60 gesti, nessun
  crash, ciclo massimo 10 ms, e l'FM-1 fa quello che fa il simulatore sonda per sonda. Le uniche differenze erano di tempo
  (una sonda sul tick in cui comincia uno step, un messaggio al suo ultimo millisecondo, un tasto letto 2 ms dopo): il
  confronto ora le riconosce (regola TEMPO), e le note e il clock si contano solo fin dove il PC ha ascoltato.
* I test: 870 controlli nel simulatore (anche con ASan e UBSan), 890 mila nel core, il bridge, i plugin (con una
  controfigura dell'API del hub quando non c'è un checkout di RaspiMIDIHub), il runner di Windows contro l'FM-1 finto.

## Cosa non c'è (ancora)

* Una finestra per SAVE e per SEL: SAVE si tiene (il tocco salva), SEL resta un modificatore (il suo tocco è libero).
* Il PICK del grid imposta la manopola della pagina mostrata: le altre pagine si cambiano dall'FM-1 (OCT nella finestra).
