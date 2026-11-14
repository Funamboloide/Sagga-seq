# SAGGA SEQ 0.16 - Note di rilascio

Una cosa sola: **i pattern dei generi entrano con il loro GROOVE**, non solo con lo swing. Il formato resta `SGQB`
(i campi del groove ci sono dalla 0.15); il Pi non cambia.

## Cosa fa

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

* `sagga_beats.c`: `sq_genre_groove(genere, parte)` (la tabella, nove gruppi di parti per 24 generi); `sagga_gen.c`: il
  pattern caricato e DICE GROOVE la usano; VIAGGIO e le variazioni del Pi passano dalla stessa strada.
* Test: il core (la tabella: valori nei limiti, i casi della documentazione), il simulatore (la BAND di UK GARAGE, HOUSE,
  TRANCE con i loro groove; DICE GROOVE; un groove a mano sostituito dal pattern; in UK garage batteria e basso si
  incontrano sui sedicesimi pari).
