# SAGGA SEQ 0.16 - Note di rilascio

Cinque cose:

0. **il MERENGUE**, il 25° genere della libreria;
1. **i pattern dei generi entrano con il loro GROOVE**, non solo con lo swing;
2. **gli algoritmi si preparano prima di partire**: K1 sceglie (READY), K2-K4 impostano, SEQ + bianco 6 accende con
   quei valori (EUCLID compreso); lo stesso per l'ARMONIA (K2 prepara, K1 accende), EXPO (K1-K3 preparano, K4 accende)
   e i MIDI FX (K1 prepara, SEQ + bianco 6 accende, ognuno con i suoi valori);
3. **armonia FREE** (ARP 4 K2): accordi slegati dal genere, ARP 3 K2 su tutte le 150 progressioni;
4. **EDIT + ARP copia la progressione** che suona in uno slot USER, da modificare su ARP 5 / 6.

Il formato resta `SGQB` (i campi del groove ci sono dalla 0.15, FREE usa un byte libero di `sq_gen_t`); il Pi non cambia.

## Il merengue, il 25° genere

SEQ + PRESETS fino all'ultimo (24 scatti da TECHNO): `MERENGUE`, 128-156 BPM, tonalità maggiori (MAJOR, MIXOLYDIAN,
MINOR), dritto (swing 50). La band (BAND, nove parti):

| traccia | parte | cosa suona |
| --- | --- | --- |
| T1 | KICK | la cassa su ogni battito, come l'orquesta e il merengue de calle |
| T2 | SNARE | il bordo della tambora sul «e» del 2 e del 4 |
| T3 | HAT | la güira: un ottavo e due sedicesimi a battito, «cha chi-ki» (nota 69, cabasa) |
| T4 | PERC | la tambora: lo schiaffo e il rullo che porta alla battuta (nota 66) |
| T5 | CONGA | le conga |
| T6 | BASS | il basso che anticipa il battito, fondamentale e quinta |
| T7 | PIANO | il montuno in levare |
| T8 | LEAD | il riff di sax o fisarmonica |
| T9 | VOX | il coro |

Le progressioni: I-V7, I-IV-V7-I, I-vi-ii-V7, I-IV-I-V7, I-ii-V7-I, vi-IV-V7-I. Il GROOVE: güira e shaker PUSH 30 (un
filo avanti), la tambora HUMAN 40, il bordo HUMAN 30, il resto dritto. In VIAGGIO, dopo la cassa, entrano prima la güira e la tambora;
il vicino è la BATIDA. I chop del BREAK: STRAIGHT, SHUFFLE, REPEAT, END ROLL. Sul grid è nella terza pagina dei generi
(PAGE viola). Un progetto con il merengue aperto da una 0.15 trova TECHNO al suo posto.

## Gli algoritmi: prima li prepari, poi li accendi

Fino alla 0.15 K1 su SEQ 2 faceva partire subito l'algoritmo con i valori di default, e la prima girata delle manopole
di EUCLID accendeva EUCLID LIVE: dal vivo la traccia saltava prima che tu potessi impostarla. Adesso:

* **SEQ 2, K1**: l'algoritmo diventa **READY** sullo slot (schermo `ALGO 1 READY` / `TURING`, sulla griglia il pad
  arancione). Non suona ancora niente.
* **K2-K4**: i suoi valori (mutazione, lunghezza, regola, celle, densità ...), sempre senza farlo partire.
* **SEQ + bianco 6** (su SEQ 2): parte **con quei valori** (`T1 ALGO 1: TURING STARTS`). Da lì K2-K4 lo cambiano mentre
  suona, come prima.
* **SEQ + bianco 6 di nuovo**: si ferma (`TURING STOPS (READY AGAIN)`), i valori restano; il prossimo SEQ + bianco 6 lo
  riaccende uguale.
* **Mentre uno suona**, K1 su un altro lo prepara e K2-K4 impostano quello; il primo continua finché SEQ + bianco 6 non
  li scambia. K1 di nuovo su quello che suona: le manopole tornano a lui. K1 su OFF: SEQ + bianco 6 lo ferma.
* Ogni algoritmo di ogni slot ricorda i suoi valori finché l'FM-1 è acceso (il progetto salva quello che suona).
* **EUCLID**: con EUCLID LIVE spento le manopole di SEQ 1 lo preparano (`EUCLID READY T1: 5/16 ROT 2 SEQ + WHITE 6
  STARTS IT`), SEQ + bianco 6 lo accende (sullo scope, come prima); acceso, le manopole lo cambiano dal vivo.
* SEQ + bianco 6 resta EUCLID LIVE su tutte le pagine SEQ tranne SEQ 2, dove accende / spegne l'algoritmo dello slot.
* **Griglia**, vista TRACK 3: un tocco sull'algoritmo lo prepara (arancione), il secondo lo accende (bianco), un tocco
  su quello che suona lo ferma; le righe 4-5 impostano quello READY. Vista EUCLID: impulsi e rotazione di una riga con
  EUCLID LIVE spento si preparano, il pad 1 la accende.

### Lo stesso altrove

* **ARMONIA**: spenta, ARP 3 K2 sceglie la progressione e la mette READY (`READY TECHNO i-VII-VI-VII: K1 ON`), K1 la
  accende. Fino alla 0.15 girare K2 accendeva l'armonia.
* **EXPO** (SEQ 4): con SHAPE su OFF, K1-K3 la preparano (`EXPO READY: K4 SHAPE STARTS IT`), K4 la accende con quei
  valori. Fino alla 0.15 il primo tocco la accendeva su RAMP.
* **MIDI FX** (HOME 6): K1 mette l'effetto READY (`T1 MIDI FX ECHO READY: SEQ + WHITE 6`; quello che suona continua),
  K2-K4 ne impostano i valori, **SEQ + bianco 6** lo accende (con un MIDI FX READY sulla traccia selezionata quel tasto
  accende lui e non EUCLID; HOME + bianco 6 resta la traccia 6). K1 su OFF e poi SEQ + bianco 6: si spegne. Ogni effetto
  ricorda i suoi valori su quella traccia (i default solo la prima volta). Griglia, TRACK 3 riga 2: un tocco READY
  (arancione), il secondo lo accende. Fino alla 0.15 K1 lo accendeva subito, ogni volta con i default.
* **ARP e CHORD** andavano già bene: ottave, RATE, RUN, voicing e strum sono della traccia e restano quando cambi modo o
  forma (impostali col modo su BLOCK o la forma su OFF, poi scegli). Anche gli LFO, EVOLVE e la quantità del GROOVE.

## Armonia FREE e copia della progressione

* **ARP 4 K2**, uno a sinistra del primo genere: **FREE**. Gli accordi non sono di nessun genere: ARP 3 K2 scorre tutte
  le 150 progressioni della libreria (`TECHNO 1` .. `MERENGUE 6`), poi le USER e DICE/PI; con un MOOD (ARP 4 K3) solo
  quelle di quel mood. Un pattern caricato, BAND, GENRE LIVE, il genere di VIAGGIO non spostano più l'armonia. K2 a
  destra: di nuovo i generi. Si salva col progetto.
* **EDIT + ARP**: la progressione che suona (della libreria, USER, del Pi) viene scritta in uno slot USER, accordo per
  accordo con le sue forme: quello mostrato su ARP 5 se non è quello che suona, altrimenti il primo vuoto (`COPIED TO
  USER 2: ARP 5 TO CHANGE IT`). Suona subito dalla copia (uguale) e la cambi su ARP 5 / ARP 6. Sopra uno slot pieno
  chiede conferma (`COPY OVER USER 1: EDIT+ARP AGAIN`, entro 3 s).
* **FOLLOW** non sposta le note nel tempo: cambia solo l'altezza (in gradi della scala), il ritmo resta quello scritto.
  Solo RETRIG e LEGATO agiscono su una nota tenuta attraverso un cambio d'accordo. Per un pad che segue il ritmo
  armonico: una nota lunga (gate lungo o TIE) con FOLLOW RETRIG.

## I groove dei generi

Un pattern della libreria (BEAT, BAND, KIT, GENRE LIVE, le proposte di VIAGGIO, le variazioni del Pi) portava solo lo
swing del genere. Adesso porta anche il **GROOVE della sua parte**, con lo swing che ci va insieme:

* **hat, shaker, percussioni** portano il groove del genere;
* **la cassa** resta l'àncora, dritta sullo swing del genere;
* **basso e accordi** tengono lo swing del genere (qualche genere: un HUMAN o un LAID BACK leggero).

Dove un template porta già lo shuffle (GARAGE, SAMBA) la batteria sta dritta sotto (swing 50) e basso e accordi prendono
lo swing che gli corrisponde: GARAGE 100 % vale circa uno swing 63, al 60 % circa 58. Così le parti si incontrano: in UK
garage ogni nota su un sedicesimo pari arriva fra il 18 e il 34 % di uno step in ritardo, batteria e basso insieme (il
simulatore lo misura).

**DICE GROOVE** (SEQ + nero 4) tiene il template di ogni parte e muove di poco la quantità (± 20 %) e lo swing. Un
groove o uno swing messi a mano vengono sostituiti dal prossimo pattern caricato su quella traccia, come succedeva già
per lo swing: dopo li giri tu per il tuo feel.

## Le dosi, genere per genere

| genere | hat / ride | shaker | percussioni (rim, conga, tom) | cassa / rullante | basso e accordi |
|---|---|---|---|---|---|
| TECHNO | HOUSE 40 | HUMAN 30 | HUMAN 30 | dritti | dritti |
| HARDTECHNO | PUSH 30 | PUSH 30 | PUSH 30 | dritti | dritti |
| DUB TECHNO (54) | HOUSE 50 | HOUSE 50 | HUMAN 40 | dritti | accordi LAID BACK 30 |
| HOUSE (54) | HOUSE 100 | HOUSE 100 | HOUSE 60 | dritti | HUMAN 30 |
| UK GARAGE | GARAGE 100, swing 50 | GARAGE 100, swing 50 | GARAGE 100, swing 50 | GARAGE 100, swing 50 | swing 63 |
| UK FUNKY (56) | GARAGE 50, swing 50 | AFRO 80 | AFRO 80 | rullante AFRO 40 | accordi HUMAN 30 |
| GRIME | TRAP 50 | TRAP 40 | HUMAN 30 | dritti | dritti |
| DUBSTEP (52) | LAID BACK 40 | LAID BACK 40 | LAID BACK 40 | dritti (il rullante a metà tempo sulla griglia) | dritti |
| JUNGLE | PUSH 50 | PUSH 50 | HUMAN 50 | cassa HUMAN 30, rullante HUMAN 60 | accordi HUMAN 30 |
| BASSLINE | GARAGE 60, swing 50 | GARAGE 60, swing 50 | GARAGE 60, swing 50 | dritti (56) | swing 58 |
| REGGAETON | TRAP 40 | AFRO 50 | AFRO 60 | rullante AFRO 60 (il dembow) | dritti |
| BATIDA (52) | AFRO 60 | AFRO 80 | AFRO 100 | rullante AFRO 40 | dritti |
| GQOM (54) | AFRO 50 | AFRO 60 | AFRO 80 | dritti | dritti |
| EXPERIMENT | DILLA 60 | DILLA 60 | DILLA 60 | cassa HUMAN 30, rullante DILLA 40 | HUMAN 50 |
| ELECTRO | TRAP 40 | TRAP 30 | HUMAN 20 | dritti | dritti |
| DRUM+BASS | PUSH 40 | PUSH 40 | HUMAN 30 | dritti | accordi HUMAN 30 |
| AFRO HOUSE (54) | HOUSE 70 | AFRO 100 | AFRO 100 | dritti | HUMAN 30 |
| AMAPIANO (58) | AFRO 60 | AFRO 80 | AFRO 80 | dritti | log drum dritto, accordi LAID BACK 40 |
| FOOTWORK | TRAP 60 | TRAP 40 | HUMAN 30 | dritti | dritti |
| TRANCE | dritto | dritto | dritto | dritti | dritti |
| UK DRILL (54) | TRAP 100 | TRAP 60 | TRAP 60 | dritti | dritti |
| HARDCORE | PUSH 40 | PUSH 40 | PUSH 30 | dritti | dritti |
| PHONK (52) | TRAP 80 | TRAP 50 | HUMAN 20 (il cowbell) | dritti | accordi LAID BACK 30 |
| BAILE FUNK (54) | SAMBA 80, swing 50 | SAMBA 100, swing 50 | SAMBA 100, swing 50 | rullante AFRO 50 | dritti |

Fra parentesi lo swing del genere, che hanno tutte le parti dove non è detto altro; senza parentesi: 50. L'open hat
segue l'hat con un po' meno; arp, lead e voci seguono gli accordi. La tabella completa, parte per parte, è in
`docs/SAGGA-SEQ.md`.

## Sotto il cofano

* il merengue: `tools/gen_beats.py` (i pattern), `tools/beat_parts.py` (la band, conga e coro), `tools/gen_progs.py` (le
  progressioni del Pi), `SQ_GENRES` 25, la riga del GROOVE, i chop del BREAK, i file del Pi (`patterns/MERENGUE.txt`,
  `progressions/MERENGUE.txt`), la pagina SAGGA Mod.
* `sagga_beats.c`: `sq_genre_groove(genere, parte)` (la tabella, nove gruppi di parti per 25 generi); `sagga_gen.c`: il
  pattern caricato e DICE GROOVE la usano; VIAGGIO e le variazioni del Pi passano dalla stessa strada.
* `sagga_gen.c`: `algo_choose` / `algo_go` / `algo_pad`, i valori pronti per slot e per algoritmo (`algo_mem`, in RAM),
  `euclid_touch` che prepara invece di accendere; `harm_prog_set` che non accende più l'armonia (e `harm_say`: con FREE
  un messaggio lungo poteva uscire dai 64 byte del buffer); EXPO senza accensione automatica; `mfx_choose` / `mfx_go` / `mfx_pad` (dinghy.c); `harm_genre_turn` / `harm_free_turn` (FREE); `dinghy.c`: `prog_copy`.
* Test: il core (la tabella: valori nei limiti, i casi della documentazione), il simulatore (la BAND di UK GARAGE, HOUSE,
  TRANCE con i loro groove; DICE GROOVE; un groove a mano sostituito dal pattern; in UK garage batteria e basso si
  incontrano sui sedicesimi pari; DENSITY 0 READY che non suona finché SEQ + bianco 6 non lo accende, poi a 0 e non a
  100; CELL preparato mentre suona DENSITY e scambiato; stop e ripartenza con gli stessi valori; EUCLID READY; i pad
  della griglia; FREE con 150 progressioni e MOOD; la copia che suona uguale all'originale). I test che accendevano un
  algoritmo con K1 o EUCLID con le manopole ora premono anche SEQ + bianco 6.
