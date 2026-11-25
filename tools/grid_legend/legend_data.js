// SAGGA GRID: what every button and pad does (from docs/SAGGA-GRID.md, section 3, SAGGA SEQ 0.32.1).
// Rows and columns count from 1 (row 1 on top, column 1 on the left). segs: [first column, last column, text].

const TITLE = "SAGGA GRID · cosa fa ogni tasto";
const SUBTITLE = "Due Launchpad Mini affiancati nella formazione da grid (--frame): il sinistro girato di un quarto, " +
  "i 32 tasti tondi intorno ai 16 × 8 pad. SAGGA SEQ 0.32.1.";

const TOP_BUTTONS = [
  {id: 0, title: "PLAY / STOP", shift: "CONTINUE: riparte da dove si era fermato"},
  {id: 1, title: "REC: arma la registrazione", shift: "vista PROJ; in PROJ: LIB"},
  {id: 2, title: "FILL, finché lo tieni", shift: "l'altro banco di tracce: 1–8 / 9–12"},
  {id: 3, title: "UNDO / REDO dell'ultimo strumento", sub: "con un dado in attesa: BACK", shift: "vista FX"},
  {id: 4, title: "vista STEP → DRUM", shift: "vista CC → FOLLOW"},
  {id: 5, title: "vista PERF → SONG → MOSSE → REGIA", shift: "vista LFO"},
  {id: 6, title: "vista TRACK → TRACK 2 → TRACK 3", shift: "vista BEAT → EUCLID"},
  {id: 7, title: "SHIFT: tienilo premuto", sub: "due tocchi veloci: resta premuto (giallo)"},
];

const GROUP_BUTTONS = {
  tracks: {title: "8–15 · le tracce 1–8 del banco",
           text: "Banco 2 (blu): 8–11 sono le tracce 9–12, 12–15 i loro mute (verde suona, rosso muto, " +
                 "lampeggia: aspetta, giallo: solo).",
           shift: "il solo di quella traccia"},
  patterns: {title: "16–23 · i pattern 1–8",
             text: "della traccia selezionata: il nuovo parte alla fine del giro della traccia, e lampeggia " +
                   "finché aspetta.",
             shift: "copia lì il pattern che suona (UNDO lo toglie)"},
  scenes: {title: "24–31 · le scene 1–8",
           text: "del banco dove sta il cursore delle scene (1–8, 9–16, 17–24, 25–32): la scena parte alla " +
                 "battuta dopo.",
           shift: "salva lì la scena"},
};

const NAV = [
  [["4"], "STEP → DRUM", ["SHIFT", "4"], "CC → FOLLOW"],
  [["5"], "PERF → SONG → MOSSE → REGIA*", ["SHIFT", "5"], "LFO"],
  [["6"], "TRACK → TRACK 2 → TRACK 3", ["SHIFT", "6"], "BEAT → EUCLID"],
  [["SHIFT", "3"], "FX", ["SHIFT", "1"], "PROJ → LIB"],
];

const NOTES = [
  {h: "I gruppi", t: "Dove una riga sono le 12 tracce, i pad 13–16 sono i gruppi: 13 DRUMS (le batterie), 14 BASS (i bassi), " +
                     "15 MELODIC (il resto), 16 ALL (tutte). Un pad fa a tutto il gruppo quello che la riga fa a una traccia."},
  {h: "SHIFT", t: "Tienilo, e i tasti che hanno un secondo lavoro diventano arancio. Due tocchi veloci: " +
                  "resta premuto, per usare il grid con una mano; un altro tocco lo lascia."},
  {h: "In coda", t: "Pattern e scene partono al loro momento e lampeggiano finché aspettano. Da fermo " +
                    "cambiano subito."},
  {h: "La vista", t: "L'FM-1 scrive la vista aperta in fondo allo schermo: G:STEP, G:PERF, G:MOSSE…"},
];

const SECTIONS = [
  {title: "Tasto 4 · i passi", views: [
    {key: "STEP", open: "tasto 4", what: "la traccia selezionata", groups: [
      {r: [1, 4], segs: [[1, 16, "i 64 passi, 16 per riga. Tocco: acceso / spento. Tienine uno e premi un altro: " +
        "una nota lunga fra i due. Tieni mezzo secondo: lo selezioni senza cambiarlo. SHIFT + pad: il pattern " +
        "finisce lì"]]},
      {r: [5, 5], segs: [[1, 16, "la velocity del passo selezionato, 16 livelli"]]},
      {r: [6, 6], segs: [[1, 16, "la probabilità, dal 6 al 100 %. SHIFT: la condizione (1:2, 2:4, FILL, !FILL, " +
        "FIRST, PRE…)"]]},
      {r: [7, 7], segs: [[1, 8, "ratchet 1–8"], [9, 16, "gate 12–100 %"]], note: "SHIFT: 15 PLAIN, 16 TIE (legato)"},
      {r: [8, 8], segs: [[1, 16, "le note: cromatiche da C3, o la scala della traccia (le toniche bianche). " +
        "SHIFT + tocco: aggiungi o togli una nota, accordi fino a 4"]]},
    ], foot: "Su una traccia BREAK i passi sono le fette, e la riga 8 sono le 16 fette."},
    {key: "DRUM", open: "tasto 4, di nuovo", what: "le otto tracce del banco, una per riga", groups: [
      {r: [1, 4], segs: [[1, 16, "una traccia per riga (banco 1: le tracce 1–4; banco 2: 9–12). Tocco: il passo " +
        "acceso / spento, e suona la sua nota. Tieni mezzo secondo: selezioni traccia e passo"]]},
      {r: [5, 8], bank2: true, segs: [[1, 16, "la forza dei passi delle tracce 9–12 (la riga 5 sotto la 1…): " +
        "NORMAL → ACCENT → GHOST"]], lead: "banco 1: le tracce 5–8, come sopra. Banco 2:"},
    ], foot: "SHIFT + pad 1–4: la pagina di 16 passi. SHIFT + un altro pad: la traccia di quella riga."},
    {key: "CC", open: "SHIFT + tasto 4", what: "le corsie CC della traccia selezionata", groups: [
      {r: [1, 4], segs: [[1, 16, "una barra per passo: il valore che la corsia blocca lì (in alto 127, poi 80, 48, " +
        "16). Tocco: blocca quel valore; di nuovo in cima: niente blocco"]]},
      {r: [5, 5], segs: [[1, 8, "la corsia 1–8"], [9, 12, "la pagina dei passi 1–4"], [13, 13, "COPY: copia la corsia"],
        [14, 14, "PASTE: la incolla"], [15, 15, "la corsia in tutti i pattern"], [16, 16, "cancella la corsia"]]},
      {r: [6, 6], segs: [[1, 16, "il numero CC: 1, 5, 7, 10, 11, 12, 13, 64, 71–75, 91, 93, 94. SHIFT + pad: " +
        "LEARN (muovi una manopola del synth)"]]},
      {r: [7, 7], segs: [[1, 16, "il valore base 0–127, dove torna dopo un blocco"]]},
      {r: [8, 8], segs: [[1, 1, "corsia spenta"], [2, 2, "niente base"],
        [3, 6, "il modo: NORMAL, SLIDE, TRIGLESS, NRPN"],
        [7, 15, "rampa su, rampa giù, su e giù, a caso, capovolta, un passo prima, un passo dopo, smussata, a metà " +
          "verso la base"], [16, 16, "cancella la pagina"]]},
    ]},
    {key: "FOLLOW", open: "SHIFT + tasto 4, di nuovo", what: "il grid va con la pagina dell'FM-1", groups: [
      {r: [1, 4], segs: [[1, 16, "K1–K4 della pagina aperta sull'FM-1, una manopola per riga: il pad del valore " +
        "di adesso è bianco"]]},
      {r: [5, 8], segs: [[1, 12, "K1–K4 su tutte le tracce (pad 1 = traccia 1). Tocco: quella traccia prende il " +
        "valore. SHIFT + tocco: l'FM-1 va su quella traccia"], [13, 16, "i gruppi"]]},
    ], foot: "Mentre il grid segue, SHIFT è ciano. Una vista scelta a mano lo ferma; SHIFT + 4 due volte lo fa ripartire."},
  ]},
  {title: "Tasto 5 · il live", views: [
    {key: "PERF", open: "tasto 5", what: "le otto tracce del banco, una per riga", groups: [
      {r: [1, 4], lead: "una traccia per riga (banco 2: le tracce 9–12)",
       segs: [[1, 1, "mute"], [2, 2, "solo"], [3, 10, "pattern 1–8"], [11, 11, "RETRIG: riparte dal primo passo"],
         [12, 12, "KILL finché tieni (SHIFT: resta)"], [13, 16, "dove è la testina; tocco: seleziona la traccia"]]},
      {r: [5, 5], bank2: true, segs: [[1, 16, "le scene 1–16: tocco, la scena alla QUANTISE; SHIFT + tocco: salva"]],
       lead: "banco 1: le tracce 5–8, come sopra. Banco 2:"},
      {r: [6, 6], bank2: true, segs: [[1, 16, "le scene 17–32, uguale"]]},
      {r: [7, 7], bank2: true, segs: [[1, 16, "gli snapshot 1–16: tocco, lo richiami; SHIFT + tocco: salva"]]},
      {r: [8, 8], bank2: true, segs: [[1, 12, "i mute delle tracce 1–12 (SHIFT: solo)"],
        [13, 16, "i gruppi: DRUMS, BASS, MELODIC, ALL"]]},
    ]},
    {key: "SONG", open: "tasto 5, di nuovo", what: "la canzone: le scene in fila", groups: [
      {r: [1, 1], segs: [[1, 16, "16 voci della canzone: tocco, la modifichi (quella dopo l'ultima: una nuova). " +
        "SHIFT + tocco: la canzone salta lì"]]},
      {r: [2, 2], segs: [[1, 16, "la scena della voce, 1–16 (SHIFT: 17–32)"]]},
      {r: [3, 3], segs: [[1, 16, "la sua durata: 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 48, 64 battute"]]},
      {r: [4, 4], segs: [[1, 1, "SONG on / off"], [2, 2, "LOOP"], [3, 3, "inserisci una copia"], [4, 4, "cancella"],
        [5, 6, "un posto prima / dopo"], [7, 8, "il suo tempo / nessuno"], [9, 9, "SONG TEMPO"],
        [10, 11, "battute ÷ 2 / × 2"], [12, 12, "SAVE THE SET"], [13, 14, "pagina indietro / avanti"],
        [15, 15, "la voce libera dopo l'ultima"], [16, 16, "dall'inizio, adesso (SHIFT: cancella la canzone)"]]},
      {r: [5, 8], segs: [[1, 16, "la canzone battuta per battuta (64 dalla prima voce della pagina), un colore per " +
        "voce, rosso la battuta che suona. Tocco: la canzone salta lì"]]},
    ]},
    {key: "MOSSE", open: "tasto 5, una terza volta", what: "il viaggio: le mosse a fine frase", groups: [
      {r: [1, 1], segs: [[1, 16, "le battute della frase, rossa quella che suona. Un pad qualsiasi: NOW"]]},
      {r: [2, 2], segs: [[1, 12, "le 12 tracce e il loro stato (vuota, proposta, dentro, fuori). Tocco: una " +
        "proposta; tieni: il dado; SHIFT + tocco: il ruolo"], [13, 16, "il dado per un gruppo"]]},
      {r: [3, 3], segs: [[1, 12, "la coda: tocco, la traccia entra o esce al confine"],
        [13, 16, "un gruppo dentro / fuori"]]},
      {r: [4, 4], segs: [[1, 11, "le mosse: FILL, BREAK, RISER, DROP, HALF, DOUBLE, THIN, SWELL, SWAP, LOOP, NOW"],
        [12, 14, "la frase di 4, 8, 16 battute"], [15, 15, "INDIETRO"], [16, 16, "annulla l'ultima"]],
       note: "SHIFT: BREAK di tutto, LOOP di 4 battute; SHIFT + HALF / DOUBLE: SHORTER / LONGER, ogni traccia lunga la metà / il doppio"},
      {r: [5, 5], segs: [[1, 16, "l'energia, da 0 a 100"]]},
      {r: [6, 6], segs: [[1, 8, "i pattern della traccia: tocco, SWAP o dentro al confine"],
        [9, 11, "MOVES AT: frase, battuta, battito"], [12, 13, "genere − / +"], [14, 15, "tonalità − / +"],
        [16, 16, "il dado"]]},
      {r: [7, 7], segs: [[1, 8, "le progressioni del genere"], [9, 12, "le tue"], [13, 13, "DICE / PI"],
        [14, 16, "HARMONY, LOCK, battute per accordo (suonando: l'accordo)"]]},
      {r: [8, 8], segs: [[1, 16, "le frasi passate: il 16 è questa, il 15 una indietro… Tocco: INDIETRO fin lì"]]},
    ]},
    {key: "REGIA", open: "tasto 5, una quarta volta", what: "solo quando il regista del Pi ha parlato", groups: [
      {r: [1, 1], segs: [[1, 16, "le 16 regole del regista: spenta, accesa, rossa mentre passa. Tocco: la accendi " +
        "o la spegni"]]},
      {r: [2, 8], segs: [[1, 16, "come le righe 2–8 di MOSSE: tracce, coda, mosse, energia, pattern, " +
        "progressioni, frasi passate"]]},
    ]},
    {key: "LFO", open: "SHIFT + tasto 5", what: "i 16 LFO", groups: [
      {r: [1, 1], segs: [[1, 16, "i 16 LFO: tocco, lo selezioni; di nuovo, acceso / spento"]]},
      {r: [2, 2], segs: [[1, 8, "la forma: seno, triangolo, rampa su, rampa giù, quadra, S&H, random morbido, decay"],
        [9, 14, "dove va: CC, velocity, gate, probabilità, timing, swing"], [15, 15, "retrigger"],
        [16, 16, "inverti"]]},
      {r: [3, 3], segs: [[1, 16, "la velocità: da 16 battute a 1/32"]]},
      {r: [4, 4], segs: [[1, 16, "la profondità"]]},
      {r: [5, 5], segs: [[1, 16, "il centro"]]},
      {r: [6, 6], segs: [[1, 16, "la fase"]]},
      {r: [7, 7], segs: [[1, 12, "il bersaglio: il canale MIDI (un LFO di CC) o la traccia 1–12"],
        [13, 16, "un gruppo"]]},
      {r: [8, 8], segs: [[1, 16, "il numero CC (SHIFT + pad: LEARN)"]]},
    ]},
  ]},
  {title: "Tasto 6 · la traccia e i generatori", views: [
    {key: "TRACK", open: "tasto 6", what: "la traccia selezionata", groups: [
      {r: [1, 1], segs: [[1, 16, "16 strumenti: CLEAR, REVERSE, SHIFT <, SHIFT >, RANDOM, EUCLID LIVE, WRITE LIVE, " +
        "UNDO, COOK, BEAT, PROG, COPY, PASTE, DOUBLE, INVERT, HUMANIZE"]]},
      {r: [2, 2], segs: [[1, 13, "l'arpeggio: BLOCK, UP, DOWN, UP-DN, DN-UP, UP&DN, CONV, DIV, RND, WALK, PLAYED, " +
        "THUMB, PINKY"], [14, 16, "ottave 1–3"]]},
      {r: [3, 3], segs: [[1, 8, "swing 50–75 %"], [9, 12, "direzione: avanti, indietro, ping-pong, a caso"],
        [13, 16, "trasporto −12, −1, +1, +12 (SHIFT: a 0)"]]},
      {r: [4, 4], segs: [[1, 13, "la divisione, da 1/1 a 1/32T"], [14, 14, "FREE / IN KEY / DRUM / BREAK"],
        [15, 16, "poliritmi: 5 o 7 nel tempo di 4"]]},
      {r: [5, 5], segs: [[1, 16, "la lunghezza 4, 8 … 64 (SHIFT: l'inizio del loop)"]]},
      {r: [6, 6], segs: [[1, 8, "humanize del tempo 0–50 %"], [9, 16, "humanize della velocity 0–50"]]},
      {r: [7, 7], segs: [[1, 15, "velocity −63 … +63 (il pad 8: 0)"], [16, 16, "tutte le tracce a 0 (due volte)"]]},
      {r: [8, 8], segs: [[1, 15, "il nudge del passo selezionato, −50 … +50 % (a sinistra: prima)"],
        [16, 16, "tutti i passi sulla griglia"]]},
    ]},
    {key: "TRACK 2", open: "tasto 6, di nuovo", what: "i loop dei parametri, i programmi", groups: [
      {r: [1, 1], segs: [[1, 16, "il loop delle note: 1–16 passi (SHIFT: 17–32); di nuovo: torna al loop della " +
        "traccia"]]},
      {r: [2, 2], segs: [[1, 16, "il loop delle velocity"]]},
      {r: [3, 3], segs: [[1, 16, "il loop dei gate"]]},
      {r: [4, 4], segs: [[1, 16, "il Program Change del canale nella scena della riga 5: 1–16 (SHIFT: 17–32); di " +
        "nuovo: nessuno. Parte subito"]]},
      {r: [5, 5], segs: [[1, 8, "quale scena, 1–8 del banco"], [9, 12, "il banco: 1–8, 9–16, 17–24, 25–32"],
        [13, 13, "i programmi di questa scena in tutte"], [14, 14, "questa scena senza programmi"],
        [15, 15, "il programma di questo canale in tutte le scene"], [16, 16, "manda adesso i programmi della scena"]]},
      {r: [6, 8], segs: [[1, 16, "i tre loop: rosso il passo che suonano. Tocco: quel loop riparte da lì"]]},
    ]},
    {key: "TRACK 3", open: "tasto 6, una terza volta", what: "accordi, effetti MIDI, algoritmi", groups: [
      {r: [1, 1], segs: [[1, 5, "il voicing: CLOSE, INV 1, INV 2, DROP 2, OPEN"], [6, 16, "lo strum, −50 … +50 % " +
        "(il pad 11: 0)"]]},
      {r: [2, 2], segs: [[1, 5, "gli effetti MIDI: OFF, HARM, OCTAVE, ECHO, VEL CURVE"], [6, 16, "la quantità −5 … +5"]],
       note: "SHIFT + 2–8: CHANCE, RANDOM, NOTE FILTER, GATE, GLITCH, ROLL, ACCENT"},
      {r: [3, 3], segs: [[1, 8, "il tempo dell'ECHO, 1/32 … 1/4"], [9, 16, "quanto tiene l'ECHO / la velocity della " +
        "voce HARM"]]},
      {r: [4, 4], segs: [[1, 5, "l'algoritmo: OFF, TURING, CELL, ACCENT, DENSITY"], [6, 6, "FOLLOW"],
        [7, 7, "EUCLID LIVE"], [8, 8, "lo slot 1–4"], [9, 16, "C: ritmo / note di TURING, CELL ogni 1 / 2 / 4 " +
          "battute, offset di ACCENT"]]},
      {r: [5, 5], segs: [[1, 16, "A: la mutazione di TURING, la regola di CELL, lo stile di ACCENT, DENSITY"]]},
      {r: [6, 6], segs: [[1, 16, "B: la lunghezza di TURING (16: come la traccia), le celle di CELL, la quantità di " +
        "ACCENT, la velocity dei ghost di DENSITY"]]},
      {r: [7, 7], segs: [[1, 16, "il gate lungo del passo selezionato: da 1,5 a 64 passi"]]},
      {r: [8, 8], segs: [[1, 16, "il canale MIDI 1–16"]]},
    ]},
    {key: "BEAT", open: "SHIFT + tasto 6", what: "libreria, generatori, dadi, EVOLVE", groups: [
      {r: [1, 1], segs: [[1, 12, "il genere (due pagine; nella seconda: 11 a caso, 12 la SOURCE)"], [13, 13, "PAGE"],
        [14, 14, "LOAD"], [15, 15, "KIT (SHIFT: BAND)"], [16, 16, "DICE ALL"]]},
      {r: [2, 2], segs: [[1, 9, "le parti del genere: la sua band, PROG, KIT"],
        [10, 15, "l'ambito: traccia, banco, tutte, batterie, melodiche, CUSTOM"], [16, 16, "WRITE LIVE"]]},
      {r: [3, 3], segs: [[1, 6, "le progressioni 1–6"], [7, 7, "HARMONY"], [8, 8, "battute per accordo"],
        [9, 9, "FOLLOW"], [10, 10, "pagina"], [11, 16, "le variazioni (con THEORY e FREE: i semi)"]]},
      {r: [4, 4], segs: [[1, 5, "DICE: SEQ, CC, LFO, GROOVE, ALL"], [6, 6, "KEEP"], [7, 7, "BACK"],
        [9, 14, "cosa cambia: ritmo, +note, +CC, +note+CC, +CC+LFO, tutto"], [15, 16, "il tiro prima / dopo"]]},
      {r: [5, 5], segs: [[1, 16, "EUCLID: gli impulsi 1–16 (con CUSTOM: le tracce dell'ambito, 13–16 i gruppi)"]],
       note: "SHIFT: le righe 5–6 mostrano cosa porterebbe LOAD"},
      {r: [6, 6], segs: [[1, 16, "EUCLID: la rotazione 0–15"]]},
      {r: [7, 7], segs: [[1, 8, "densità a caso 10–90 %"], [9, 16, "HEAT 5–90 %"]]},
      {r: [8, 8], segs: [[1, 1, "EVOLVE"], [2, 2, "FREEZE"], [3, 3, "REVERT"], [4, 4, "DRIFT"],
        [5, 9, "ogni 1, 2, 4, 8, 16 battute"], [10, 16, "quanto, 5–80 %"]]},
    ]},
    {key: "EUCLID", open: "SHIFT + tasto 6, di nuovo", what: "otto ritmi euclidei, uno per traccia", groups: [
      {r: [1, 4], lead: "una traccia per riga", segs: [[1, 1, "EUCLID LIVE on / off"],
        [2, 16, "gli impulsi 1–15 (SHIFT: la rotazione 0–14)"]]},
      {r: [5, 8], bank2: true, lead: "banco 1: le tracce 5–8, come sopra. Banco 2, sotto le tracce 9–12:",
       segs: [[1, 1, "la FAMILY: EUCLID, TRESILLO, NUMERIC"], [2, 16, "la ROTATION 0–14"]]},
    ], foot: "Suonano sopra quello che è scritto; WRITE LIVE li scrive nei pattern."},
  ]},
  {title: "SHIFT + 3, SHIFT + 1 · effetti, progetto, file", views: [
    {key: "FX", open: "SHIFT + tasto 3", what: "gli effetti dal vivo", groups: [
      {r: [1, 1], segs: [[1, 16, "16 effetti finché li tieni (SHIFT + pad: restano): FILL, stutter 2 / 4 / 8, half " +
        "time, double time, reverse, freeze, random, ottava su, ottava giù, quinta, velocity al massimo, staccato, " +
        "legato, kill all"]]},
      {r: [2, 2], segs: [[1, 12, "LOOP / REPEAT da 1/32 a 4 battute, poi le terzine"], [13, 13, "1/16 puntato"],
        [14, 14, "ECHO su ogni traccia"], [15, 15, "1/8 puntato"], [16, 16, "EXIT"]],
       note: "tocco: un LOOP che resta; tieni: REPEAT, e quando lasci ogni traccia è dove sarebbe stata"},
      {r: [3, 3], segs: [[1, 16, "TRANSPOSE della tonalità, −7 … +8 semitoni (il pad 8: 0), alla QUANTISE"]]},
      {r: [4, 4], segs: [[1, 12, "le tracce che prendono LOOP e REPEAT (nessuna accesa: tutte)"],
        [13, 16, "un gruppo"]]},
      {r: [5, 5], segs: [[1, 16, "MORPH: dalla scena che suona (1) a MORPH TO (16)"]]},
      {r: [6, 6], segs: [[1, 12, "KILL della traccia finché tieni (SHIFT: resta)"],
        [13, 16, "KILL di un gruppo (16: tutte tranne la selezionata)"]]},
      {r: [7, 7], segs: [[1, 8, "MORPH TO: la scena 1–8"], [9, 15, "QUANTISE: AUTO, NOW, BEAT, BAR, 2, 4, 8 BARS"],
        [16, 16, "MUTE QUEUE"]]},
      {r: [8, 8], segs: [[1, 1, "TEMP"], [2, 2, "RELOAD"], [3, 3, "RESTART"], [4, 4, "STOP a fine battuta"],
        [5, 12, "SNAPSHOT 1–8 o 9–16 (SHIFT: salva)"], [13, 13, "CC CAPTURE"], [14, 14, "SEND"],
        [15, 15, "PATCHES del Pi"], [16, 16, "PANIC"]]},
    ]},
    {key: "PROJ", open: "SHIFT + tasto 1", what: "tonalità, slot, tempo", groups: [
      {r: [1, 1], segs: [[1, 12, "la tonica, da C a B"], [13, 14, "una quinta giù / su"], [15, 15, "la relativa"],
        [16, 16, "la parallela"]]},
      {r: [2, 2], segs: [[1, 16, "la scala: cromatica, maggiore, minore, i modi, minore armonica e melodica, " +
        "pentatoniche, blues, esatonale, frigia dominante, hirajoshi (SHIFT + 1–5: altre cinque)"]]},
      {r: [3, 3], segs: [[1, 15, "lo spostamento, −24 … +24 semitoni"], [16, 16, "THE KEY BEFORE: la tonalità di prima"]]},
      {r: [4, 4], segs: [[1, 12, "il modo delle tracce 1–12: FREE, IN KEY, DRUM"], [13, 13, "ogni traccia sul suo " +
        "canale"], [14, 14, "le batterie sul canale 10"], [15, 16, "il canale della traccia − / +"]]},
      {r: [5, 5], segs: [[1, 4, "la manopola MASTER: TEMPO, MORPH, FILTER, ENERGY"], [5, 5, "il remoto"],
        [6, 13, "SONG TEMPO, MIDI IN PLAYS, LONG PATTERNS, CLICK, COUNT IN, MUTE QUEUE, SCENE METRE, PROFILE"],
        [14, 14, "BAKE della tonalità"], [15, 15, "tutte seguono la tonalità, non le batterie"],
        [16, 16, "nessuna la segue"]]},
      {r: [6, 6], segs: [[1, 8, "lo slot 1–8"], [9, 9, "SAVE"], [10, 10, "LOAD"], [11, 11, "CLEAR"],
        [12, 12, "EXPORT al Pi"], [13, 14, "il file prima / dopo"], [15, 15, "SAVE OVER sul Pi"],
        [16, 16, "NEW PROJECT"]], note: "SAVE, LOAD, CLEAR, SAVE OVER e NEW PROJECT vogliono due tocchi"},
      {r: [7, 7], segs: [[1, 4, "il tempo −10, −1, +1, +10"], [5, 5, "TAP"], [6, 6, "REC quantizzato / libero"],
        [7, 7, "clock master / slave"], [8, 8, "il tempo ÷ 2"], [9, 9, "unmute di tutto"], [10, 10, "il tempo × 2"],
        [11, 16, "90, 100, 120, 128, 140, 174"]]},
      {r: [8, 8], segs: [[1, 16, "salta alla battuta 1–16"]]},
    ]},
    {key: "LIB", open: "SHIFT + tasto 1, di nuovo", what: "i progetti salvati sul Pi", groups: [
      {r: [1, 7], segs: [[1, 16, "i file, fino a 112, in ordine di nome: tocco, lo scegli; di nuovo, lo carichi " +
        "(suonando: allo STOP)"]]},
      {r: [8, 8], segs: [[1, 2, "PREVIOUS / NEXT: il file prima / dopo"], [3, 3, "FIRST: il primo file"], [4, 4, "REFRESH"],
        [5, 5, "AS SAVED: com'era salvato sul Pi (due volte)"], [6, 6, "il pattern della traccia al Pi"], [7, 7, "la progressione al Pi"],
        [8, 8, "SAVE AS A NEW FILE"], [9, 9, "SAVE OVER (due volte)"], [10, 15, "gli ultimi caricati"], [16, 16, "LOAD"]]},
    ]},
  ]},
];

const FOOT = "Dal manuale docs/SAGGA-GRID.md. Il disegno è uno schema: qui i colori dei pad raggruppano le funzioni, " +
  "non sono quelli dei LED.";

// how a view opens: [button, with SHIFT, how many presses]
const KEYS = {"STEP": [4, 0, 1], "DRUM": [4, 0, 2], "CC": [4, 1, 1], "FOLLOW": [4, 1, 2], "PERF": [5, 0, 1],
  "SONG": [5, 0, 2], "MOSSE": [5, 0, 3], "REGIA": [5, 0, 4], "LFO": [5, 1, 1], "TRACK": [6, 0, 1], "TRACK 2": [6, 0, 2],
  "TRACK 3": [6, 0, 3], "BEAT": [6, 1, 1], "EUCLID": [6, 1, 2], "FX": [3, 1, 1], "PROJ": [1, 1, 1], "LIB": [1, 1, 2]};

// the PDF's page of the buttons: [ids, name, alone, with SHIFT]
const BUTTON_TABLE = [
  [[0], "0 · PLAY", "PLAY / STOP", "CONTINUE: riparte da dove si era fermato"],
  [[1], "1 · REC", "arma la registrazione", "vista PROJ; in PROJ: LIB"],
  [[2], "2 · FILL", "FILL, finché lo tieni", "l'altro banco di tracce: 1–8 / 9–12"],
  [[3], "3 · UNDO", "UNDO / REDO dell'ultimo strumento (con un dado in attesa: BACK)", "vista FX"],
  [[4], "4 · STEP", "vista STEP; di nuovo: DRUM", "vista CC; di nuovo: FOLLOW"],
  [[5], "5 · PERF", "vista PERF; di nuovo: SONG, poi MOSSE, poi REGIA", "vista LFO"],
  [[6], "6 · TRACK", "vista TRACK; di nuovo: TRACK 2, poi TRACK 3", "vista BEAT; di nuovo: EUCLID"],
  [[7], "7 · SHIFT", "tienilo, e ogni tasto fa il suo secondo lavoro: quelli che ne hanno uno diventano arancio. " +
    "Due tocchi veloci: resta premuto (giallo), per il grid con una mano", ""],
  [[8, 9, 10, 11, 12, 13, 14, 15], "8–15 · tracce", "la traccia 1–8 del banco. Banco 2 (blu): 8–11 sono le tracce " +
    "9–12, 12–15 i loro mute (verde suona, rosso muto, lampeggia: aspetta, giallo: solo)", "il solo di quella traccia"],
  [[16, 17, 18, 19, 20, 21, 22, 23], "16–23 · pattern", "il pattern 1–8 della traccia selezionata: parte alla fine " +
    "del giro della traccia, e lampeggia finché aspetta", "copia lì il pattern che suona (UNDO lo toglie)"],
  [[24, 25, 26, 27, 28, 29, 30, 31], "24–31 · scene", "la scena 1–8 del banco del cursore (1–8, 9–16, 17–24, " +
    "25–32): parte alla battuta dopo", "salva lì la scena"],
];

const SHORT_NAMES = ["PLAY", "REC", "FILL", "UNDO", "STEP", "PERF", "TRACK", "SHIFT"];
