# SAGGA SEQ 0.23 - i motori THEORY, genere per genere

Questo foglio lo scrive `tools/theory/gen_rules.py` **contando la libreria dell'FM-1**: non si corregge a mano (la
suite dei test controlla che sia quello che la libreria dà). Dice cosa suonano i motori nei 16 generi le cui regole
sono contate. TECHNO, HOUSE, DUBSTEP, REGGAETON, DRUM+BASS e BALANI hanno regole scritte a mano: sono in
`TEORIA.md`, che spiega anche cosa sono i motori e come si usano.

## Come si legge

Una riga è una **famiglia**: un modo di suonare quella parte in quel genere (un hat in ottavi, un hat in levare). Il
seme ne sceglie una; la percentuale dice quanto spesso.

* **base**: quello che la famiglia suona anche con l'energia a zero.
* **pieno**: quello che suona sempre da energia 25 in su.
* **in più**: i sedicesimi che l'energia aggiunge. Una cifra per sedicesimo, da `1` (raro) a `f` (quasi sempre): a
  energia 50 un sedicesimo segnato `d` c'è una volta su due, a 100 quasi sempre.
* Due righe nella stessa casella: la prima è la battuta, la seconda la sua **risposta** (le battute 2 e 4).
* L'ultima colonna: *chiusura* = l'ultima battuta del pattern si riempie verso l'uno; *rullate* = certi colpi
  diventano rullate; *mai sul kick*, *con il kick* = la parte guarda il kick che suona.

`X` accento, `x` colpo, `o` piano, `g` ghost, `.` niente. Sedici caratteri sono una battuta.

Le **note** sono quelle che la libreria usa in quella parte: i motori le scelgono nelle stesse proporzioni, ma mettono
la fondamentale sull'uno e l'ottava dopo una fondamentale come fa un bassista.

## HARDTECHNO

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 2 · 58 % | `X.......X.......` | `X...X...X...X...` | `.........44..4f4` |  |
|  | 2 di 2 · 42 % | `X...X...X...X...`<br>`X...X...X...X...` | `X..xX...X..xX..x`<br>`X..xX...X..xX...` | `.55....a..5.....`<br>`.55....a......af` | rullate |
| RUMBLE | 1 di 4 · 50 % | `.x.x.x.x.x.x.x.x` | `.xxx.xxx.xxx.xxx` | `....4...4.......` | mai sul kick |
|  | 2 di 4 · 25 % | `..x...x...x...x.` | `..xx..xx..xx..xx` | `.1...1...1...1..` | mai sul kick |
|  | 3 di 4 · 17 % | `...x...x...x...x` | `.x.x.x.x.x.x.x.x` | `..1...d...1...1.` | mai sul kick |
|  | 4 di 4 · 8 % | `......x.......x.` | `..x...x...x...x.` | `.1.1.1.1.1.1.1.1` | mai sul kick |
| CLAP | 1 di 2 · 92 % | `....X.......X..x` | `....X.......X..x` | `..3....a36...33.` | rullate |
|  | 2 di 2 · 8 % | `........X.......` | `........X.......` | `................` |  |
| HAT | 1 di 4 · 50 % | `..x...x...x...x.`<br>`..x...x...x...x.` | `..xx..xx..xx..xx`<br>`..xx..xx..xxxxxx` | `1...1...14..94..`<br>`1...1d..1.......` |  |
|  | 2 di 4 · 33 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...1.1.6.1.1.6.6` | rullate |
|  | 3 di 4 · 8 % | `..X.......X.....` | `..X...X...X...X.` | `1..111.11..111.1` |  |
|  | 4 di 4 · 8 % | `x.x.x.x.x.x.x.x.`<br>`..xx..xx..xxxxxx` | `xxxxxxxxxxxxxxxx`<br>`xxxxxxxxxxxxxxxx` | `................`<br>`................` |  |
| OPEN HAT | la sola | `......x.......x.` | `..x...x...x...x.` | `.5.........5...5` | rullate |
| RIDE | 1 di 3 · 33 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...1.1.1.1.1...1` |  |
|  | 2 di 3 · 33 % | `x.o.x.o.x.o.x.o.` | `x.oxx.oxx.oxx.ox` | `.....1...d......` | rullate |
|  | 3 di 3 · 33 % | `......x.......x.` | `..x...x...x...x.` | `1..11d.111.11..1` | rullate |
| PERC | 1 di 4 · 42 % | `......x.......x.` | `..x...x...x...x.` | `1a.1.5.5.1.511.5` | chiusura |
|  | 2 di 4 · 33 % | `...x..........xx` | `...x...x...x..xx` | `111..11..61.16..` | chiusura, rullate |
|  | 3 di 4 · 17 % | `...x..x........x` | `x..x..x..x..x..x` | `.11..d.1..11..1.` | chiusura, rullate |
|  | 4 di 4 · 8 % | `...x...x...x...x` | `.x.x.x.x.x.x.x.x` | `..1...1...1...1.` | chiusura |
| STAB | 1 di 4 · 33 % | `........x.......` | `........x.......` | `d.d1.11...111.d.` |  |
|  | 2 di 4 · 33 % | `x.....x.....x...` | `x.....x.....x...` | `..1d....1.1...1.` |  |
|  | 3 di 4 · 17 % | `...x.......x....` | `...x.......x....` | `1.....1.1.......` |  |
|  | 4 di 4 · 17 % | `..x..x....x.....` | `..x..x....x.....` | `1.......1...1...` |  |
| LEAD | 1 di 4 · 33 % | `X.....x.x.......` | `X.xx.xx.x.xx.xx.` | `.1..1..1.1..1..d` |  |
|  | 2 di 4 · 33 % | `x.....x.x.......` | `x.....x.x.......` | `.11dd1.1.1111111` |  |
|  | 3 di 4 · 17 % | `x.xx.xx.x.xx.xx.` | `xxxxxxxxxxxxxxxx` | `................` |  |
|  | 4 di 4 · 17 % | `x.xx....x.x.....` | `x.xx.x.xx.x.x.x.` | `....1.1....1.1.1` |  |

**Le note.** RUMBLE: fondamentale 97 %. STAB: triadi 65 %, accordi di settima 18 %, quinte vuote 18 %. LEAD: un motivo - fa un arco 50 %, scende 17 %, sale 17 %, alterna due note 17 %; scala pentatonica 65 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 60 %, quinta 30 %, terza 10 %.

**La progressione.** due accordi 60 %, un accordo 18 %, quattro accordi 18 %, tre accordi 4 %; ogni accordo dura 2 battute 60 %, 1 battuta 18 %, 4 battute 18 %, 8 battute 4 %; parte da casa 95 volte su 100; la fondamentale si muove di un grado sotto 42 %, un grado sopra 29 %, una terza sotto 17 %, una terza sopra 4 %, una quarta sopra 4 %, una quinta sopra 4 %; colori: triade 83 %, sus2 9 %. Le scale del genere: PHRYG, MINOR, LOCRIAN.

## DUB TECHNO

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 2 · 83 % | `X.......X.......`<br>`X.......X.......` | `X...X...X...X...`<br>`X.......X...X..x` | `...3.3.5.3.f...5`<br>`..3.a5.3........` | rullate |
|  | 2 di 2 · 17 % | `X.......X.......` | `X.......X.......` | `..d.............` |  |
| RIM | 1 di 4 · 50 % | `............x...` | `............x...` | `....9.9..9.....4` | rullate |
|  | 2 di 4 · 25 % | `.............x..` | `.............x..` | `.......9...f....` | rullate |
|  | 3 di 4 · 17 % | `...x..........x.` | `...x..........x.` | `......dd...d....` |  |
|  | 4 di 4 · 8 % | `.............x..` | `..x..x....x..x..` | `................` |  |
| HAT | 1 di 4 · 42 % | `..x...x...x...x.` | `..x..ox...x..ox.` | `.5.5...f...5...1` | chiusura, rullate |
|  | 2 di 4 · 33 % | `......x.......x.` | `..x...x...x...x.` | `.6.1.1.1...6.6.d` | chiusura |
|  | 3 di 4 · 17 % | `..x...X...x...x.` | `..xo..Xo..xo..xx` | `.....1.......1..` | chiusura, rullate |
|  | 4 di 4 · 8 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...1.1.1...1.1.1` | chiusura |
| SHAKER | 1 di 2 · 83 % | `..x...x...x...x.` | `xoxo.oxoxoxo.oxo` | `....a.......a...` |  |
|  | 2 di 2 · 17 % | `......o.......o.` | `..o...o...o...o.` | `11.111.111.111.1` |  |
| PERC | 1 di 4 · 33 % | `...o.......o....`<br>`...o.....o.o....` | `...o...o...o...o`<br>`...o...o.o.o...o` | `.11..11..d1..11.`<br>`.11..11...1..1d.` |  |
|  | 2 di 4 · 33 % | `......x.......x.` | `......x.......x.` | `.111.1.1.11d.1.1` | rullate |
|  | 3 di 4 · 17 % | `..o.......o.....` | `..o.......o.....` | `...1..11.1.1..11` |  |
|  | 4 di 4 · 17 % | `.g.......g......` | `.g...g...g...g..` | `...1..11...1..11` |  |
| BASS | 1 di 3 · 50 % | `x.......x.......` | `x..x....x..x....` | `..1...1...1.441.` |  |
|  | 2 di 3 · 33 % | `......x.......x.` | `..x...x...x...x.` | `16.1....1..1....` |  |
|  | 3 di 3 · 17 % | `X.....x.x.......` | `X.....x.x.......` | `..11.....d11..1.` |  |
| CHORD | 1 di 2 · 58 % | `...x.......x....` | `...x.......x....` | `.44..1...41..1..` |  |
|  | 2 di 2 · 42 % | `..x.......x.....` | `..x..x....x..x..` | `...1..5....5....` |  |
| PAD | la sola | `x...............` | `x...............` | `......4.4.......` |  |
| ARP | 1 di 2 · 67 % | `......x.......x.` | `..x...x...x...x.` | `1..616.11..61...` |  |
|  | 2 di 2 · 33 % | `x.......x.......` | `x...x...x...x...` | `..11.11d..11..1.` |  |

**Le note.** BASS: fondamentale 86 %, terza 10 %. CHORD: accordi di settima 85 %, triadi 15 %. PAD: accordi di settima 90 %, triadi 10 %; tenuti. ARP: le note dell'accordo in fila, con la settima.

**La progressione.** due accordi 60 %, un accordo 18 %, quattro accordi 18 %, tre accordi 4 %; ogni accordo dura 2 battute 60 %, 1 battuta 18 %, 4 battute 18 %, 8 battute 4 %; parte da casa 82 volte su 100; la fondamentale si muove di un grado sotto 29 %, un grado sopra 17 %, una quarta sopra 17 %, una quinta sopra 17 %, una terza sotto 17 %, una terza sopra 4 %; colori: settima 49 %, nona 22 %, triade 9 %, sus4 9 %, sesta 9 %. Le scale del genere: MINOR, DORIAN, PHRYG.

## UK GARAGE

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 3 · 67 % | `X.........X.....`<br>`X.........X.....` | `X.........X.....`<br>`X.........X.....` | `.....2.3.2..a...`<br>`.3.5.3.f.2.....6` | chiusura |
|  | 2 di 3 · 25 % | `X.......X...X...` | `X.......X...X...` | `....f..9.......9` | chiusura |
|  | 3 di 3 · 8 % | `X.........X.....`<br>`X.......X...X...` | `X...X..x..X.X...`<br>`X...X...X..xX.x.` | `................`<br>`................` | chiusura |
| SNARE | 1 di 3 · 50 % | `....X.......X..g` | `....X.......X..g` | `...6...6.6......` |  |
|  | 2 di 3 · 33 % | `....X.......X...` | `....X......gX.g.` | `.6........6....6` |  |
|  | 3 di 3 · 17 % | `....X...g...X...` | `....X...g...X...` | `.........d...d..` |  |
| HAT | 1 di 4 · 55 % | `..x...x...x...x.`<br>`..x...x...x...x.` | `.xx..xx..xx..xx.`<br>`.xx..xx..xx.xxxx` | `...91..11..41..1`<br>`...41..d...1....` |  |
|  | 2 di 4 · 18 % | `..x...x...x...x.` | `..x.x.xx..x.x.xx` | `.d.1.1...1.1.1..` | rullate |
|  | 3 di 4 · 18 % | `..x...x...x...x.`<br>`..x...x...x...x.` | `..xx.xxx.xxx.xxx`<br>`.xxx.xxx.xxx.xxx` | `.d..1...d...1...`<br>`....1.......1...` | rullate |
|  | 4 di 4 · 9 % | `......x.......x.` | `..x...x...x...x.` | `.1.111.1.1.111.1` |  |
| OPEN HAT | la sola | `......x.......x.` | `..X...x...X...x.` | `.............6.6` |  |
| SHAKER | 1 di 2 · 50 % | `..x...x...x...x.` | `xoxo.oxoxoxo.oxo` | `....f.......f...` |  |
|  | 2 di 2 · 50 % | `......o.......o.` | `..o...o...o...o.` | `11.111.111.911.f` |  |
| PERC | 1 di 4 · 30 % | `..x.....x.x.....` | `..x.....x.x.....` | `1..11.19.9.91.11` | chiusura |
|  | 2 di 4 · 30 % | `x.....g.x.g.....` | `x...x.g.x.g.x.g.` | `..f9...9.1.1...1` | chiusura |
|  | 3 di 4 · 20 % | `...x..X....x....` | `...x..X....x....` | `1.1.1..1111.1.d1` | chiusura |
|  | 4 di 4 · 20 % | `......x..x....x.` | `......x..x....x.` | `1.111..11.111..d` | chiusura, rullate |
| BASS | 1 di 3 · 83 % | `x.........x.....` | `x..x..x...x.....` | `.11.13.311..ad1.` |  |
|  | 2 di 3 · 8 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...1.........1..` |  |
|  | 3 di 3 · 8 % | `x.....x.x...x...` | `xx..x.x.xx..x.x.` | `...1......1..1..` |  |
| SUB | 1 di 2 · 67 % | `x.......x.......` | `x.......x.......` | `....d.1...16d..1` | con il kick |
|  | 2 di 2 · 33 % | `x.....x...x.....` | `x.....x...x.....` | `....1...1..11..d` | con il kick |
| CHORD | 1 di 2 · 50 % | `..x....x..X.....` | `..x....x..X.....` | `1..41.........1.` |  |
|  | 2 di 2 · 50 % | `X.........x.....` | `X...x.....x...x.` | `..1....1........` |  |
| STAB | 1 di 4 · 33 % | `..x..X....x.....` | `..x..X....x.....` | `1......d....1.1.` |  |
|  | 2 di 4 · 33 % | `x.....x.........` | `x.....x.........` | `..1d......d1d.1.` |  |
|  | 3 di 4 · 17 % | `..x.......x.....` | `..x...x...x...x.` | `1...............` |  |
|  | 4 di 4 · 17 % | `...x.......x....` | `...x.......x....` | `1....11.........` |  |
| VOX | 1 di 2 · 67 % | `........x.x.....` | `........x.x.....` | `d.1d1.......116.` |  |
|  | 2 di 2 · 33 % | `..x.x.......x...` | `..x.x.......x...` | `1..1....1.1..d1.` |  |
| ARP | 1 di 3 · 50 % | `xx.xx.xx.xx.xx.x` | `xxxxxxxxxxxxxxxx` | `................` |  |
|  | 2 di 3 · 33 % | `..X...x...x...x.` | `x.X.x.x.x.x.x.x.` | `.1.1.1.1.1.1.1.1` |  |
|  | 3 di 3 · 17 % | `xx..x.x...x.x...` | `xx.xx.xx.xx.xx.x` | `..1..1..1..1..1.` |  |

**Le note.** BASS: fondamentale 44 %, ottava 17 %, quarta 16 %, quinta 14 %, terza 9 %. SUB: fondamentale 74 %, quinta 11 %, settima 11 %, terza 5 %; note tenute. CHORD: accordi di settima 95 %, triadi 5 %. STAB: triadi 65 %, accordi di settima 35 %. VOX: un motivo - scende 50 %, sale 17 %, fa un arco 17 %, alterna due note 17 %; scala pentatonica 90 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su quinta 46 %, fondamentale 31 %, terza 23 %. ARP: le note dell'accordo in fila (fondamentale, terza, quinta, ottava).

**La progressione.** quattro accordi 60 %, due accordi 32 %, un accordo 4 %, tre accordi 4 %; ogni accordo dura 1 battuta 74 %, 2 battute 18 %, 4 battute 4 %, 8 battute 4 %; parte da casa 70 volte su 100; la fondamentale si muove di una quarta sopra 38 %, un grado sopra 17 %, una quinta sopra 17 %, una terza sopra 9 %, una terza sotto 9 %, un grado sotto 9 %; colori: settima 47 %, nona 38 %, triade 6 %, sus4 6 %; gli accordi entrano spesso un sedicesimo prima. Le scale del genere: MINOR, DORIAN, MAJOR.

## UK FUNKY

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 3 · 58 % | `X.....X...X.....` | `X..x..X...X..x..` | `.4...4........4.` |  |
|  | 2 di 3 · 25 % | `X..x....X.......`<br>`X.....X...x.....` | `X..x...xX..x...x`<br>`X..x..X...x..x..` | `.....9..........`<br>`.......f......9.` |  |
|  | 3 di 3 · 17 % | `X...X...........` | `X...X....x..X...` | `.......d........` |  |
| SNARE | 1 di 3 · 50 % | `....X.......X...` | `....X..x.x..X...` | `...5.5.....a..5.` |  |
|  | 2 di 3 · 33 % | `......x.......x.` | `......x.......x.` | `.6......d......6` | rullate |
|  | 3 di 3 · 17 % | `...X..x.....x...` | `...X..x.....x...` | `..d.............` |  |
| HAT | 1 di 4 · 33 % | `......X.......x.` | `..x...X...x...x.` | `11.111..16.611.6` | chiusura |
|  | 2 di 4 · 25 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `.1.9.9...1.1.1..` | chiusura, rullate |
|  | 3 di 4 · 25 % | `..x...x...x...x.` | `x.xx.xx.x.xx.xx.` | `.f..1..9.1..1...` | chiusura |
|  | 4 di 4 · 17 % | `x.x.x.x.x.x.x.x.` | `xxx.xxx.xxx.xxx.` | `...d.......1....` | chiusura, rullate |
| RIM | 1 di 3 · 50 % | `...x..........x.` | `...x..........x.` | `......f9...f....` | rullate |
|  | 2 di 3 · 33 % | `......x.....x...` | `......x.....x...` | `...........d....` | rullate |
|  | 3 di 3 · 17 % | `..x.......x.....` | `..x..x....x..x..` | `................` |  |
| CONGA | 1 di 4 · 42 % | `...x..x.......x.` | `...x..x....x.xx.` | `151.15.5151.1..1` | chiusura, rullate |
|  | 2 di 4 · 25 % | `..o.......o...x.` | `..o.x..x..o...x.` | `1..1..1.1..1f1.9` | chiusura, rullate |
|  | 3 di 4 · 17 % | `x..x..x.........` | `x..x..x...x.x..x` | `..1.1..1d..1.11.` | chiusura |
|  | 4 di 4 · 17 % | `x..x..x.......x.` | `x.xx..x.x.xx..x.` | `....1..1....11.1` | chiusura |
| PERC | 1 di 4 · 33 % | `......X...x.x...` | `x..x..X...x.x...` | `.16.11.611...116` |  |
|  | 2 di 4 · 25 % | `x.........x.x...`<br>`x.x.......x.x...` | `x.x..x.x..x.x...`<br>`x.x..x.x..x.x..x` | `.1.11.1.1....1.f`<br>`.1.19.1.1..9.f..` |  |
|  | 3 di 4 · 25 % | `..x.x.....x.....` | `..x.x...x.x..x..` | `19.9.111....1..1` | rullate |
|  | 4 di 4 · 17 % | `....X.x.....x...` | `.x..X.x..x..x.x.` | `1.11.1.11.d..1.1` |  |
| TOM | 1 di 3 · 67 % | `..............xx`<br>`..............xx` | `..............xx`<br>`..............xx` | `1.....d...16d1..`<br>`6.....d...16d1..` | rullate |
|  | 2 di 3 · 17 % | `..........x..x..` | `..........x..x..` | `1.....1.....1.11` |  |
|  | 3 di 3 · 17 % | `x.....x.....x...` | `x.....x.....x...` | `..............11` |  |
| BASS | 1 di 3 · 42 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1..1..1.....1.` |  |
|  | 2 di 3 · 33 % | `x.....x.........` | `x.....x.x.....x.` | `..1661...61..1..` |  |
|  | 3 di 3 · 25 % | `..........x..x..` | `..x..x....x..x..` | `19.9..1.1.....1.` |  |
| CHORD | 1 di 2 · 83 % | `..x..x....x.....` | `..x..x....x.....` | `33.1....1..36...` |  |
|  | 2 di 2 · 17 % | `x.......x.......` | `x..x....x..x....` | `..1..1....1.....` |  |
| LEAD | 1 di 4 · 50 % | `x.....x.x.......` | `x.....x.x.......` | `..1f91.1..11111.` |  |
|  | 2 di 4 · 17 % | `x.....x.x.......` | `x.xx.xx.x.xx.xx.` | `....1.......1...` |  |
|  | 3 di 4 · 17 % | `x.xx....x.x.....` | `x.xx.x.xx.x.x.x.` | `....1.1.........` |  |
|  | 4 di 4 · 17 % | `x.....x.x.......` | `x.x.x.x.x.x.x.x.` | `...1.1..........` |  |

**Le note.** BASS: fondamentale 36 %, quinta 24 %, quarta 17 %, terza 14 %, ottava 9 %. CHORD: accordi di settima 88 %, triadi 12 %. LEAD: un motivo - fa un arco 48 %, sale 31 %, scende 16 %, alterna due note 5 %; scala pentatonica 90 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 35 %, quinta 35 %, terza 29 %.

**La progressione.** due accordi 60 %, un accordo 18 %, quattro accordi 18 %, tre accordi 4 %; ogni accordo dura 2 battute 46 %, 1 battuta 32 %, 4 battute 18 %, 8 battute 4 %; parte da casa 70 volte su 100; la fondamentale si muove di un grado sopra 26 %, una quarta sopra 26 %, una quinta sopra 15 %, una terza sotto 15 %, un grado sotto 15 %, una terza sopra 3 %; colori: settima 76 %, nona 16 %; gli accordi entrano spesso un ottavo prima. Le scale del genere: MINOR, DORIAN, PHRYG.

## JUNGLE

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | la sola | `X.........x.....`<br>`X.........X.....` | `X.........x.....`<br>`X.........X.....` | `.2b.....12..2..1`<br>`..81..3....2f4..` | chiusura |
| SNARE | 1 di 2 · 58 % | `....X.......X..x`<br>`....X....g..X...` | `....X.......X..x`<br>`....X..x.g..X.g.` | `.....5..........`<br>`.a.5.55........5` |  |
|  | 2 di 2 · 42 % | `....X.......X...`<br>`....X....g..X...` | `....X..g.g..X...`<br>`g...X..g.g..X...` | `.5............5a`<br>`......5........a` |  |
| HAT | 1 di 3 · 67 % | `..x.......x.....`<br>`..x...x...x...x.` | `..x...x...x...x.`<br>`..x...x...x.xxxx` | `11.311.111.116.3`<br>`11.113.313.3....` | rullate |
|  | 2 di 3 · 25 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `.9.9.......9.1.1` | rullate |
|  | 3 di 3 · 8 % | `x.x.x.x.x.x.x.x.` | `xxxxxxxxxxxxxxxx` | `................` |  |
| RIDE | 1 di 3 · 33 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...1.1.1...1...1` |  |
|  | 2 di 3 · 33 % | `x.o.x.o.x.o.x.o.` | `x.oxx.oxx.oxx.ox` | `.....d..........` | rullate |
|  | 3 di 3 · 33 % | `......x.......x.` | `..x...x...x...x.` | `1..11d.11..11..1` | rullate |
| PERC | 1 di 4 · 33 % | `......x.......x.` | `..x...x...x...x.` | `11.16..1.1.61d.1` | chiusura |
|  | 2 di 4 · 33 % | `....g....g..g...` | `.g..g..g.g..g..g` | `1.11..1.6.61.61.` | chiusura |
|  | 3 di 4 · 25 % | `...x..x.....x...` | `x..x..x..x..x..x` | `.91.1..9..1..11.` | chiusura, rullate |
|  | 4 di 4 · 8 % | `...x.......x....` | `...x.......x....` | `111.1.11.11.1111` | chiusura |
| SUB | la sola | `x...............` | `x...............` | `......f.2.b.....` | con il kick |
| BASS | 1 di 2 · 75 % | `x.......x.......` | `x.......x.......` | `..3e..1...c36...` |  |
|  | 2 di 2 · 25 % | `x.....X...x.....` | `x.....X...x.....` | `...1....1.......` |  |
| PAD | la sola | `x...............` | `x...............` | `......2.d..2....` |  |
| VOX | 1 di 3 · 50 % | `x.......x.x.....` | `x.......x.x.....` | `..111..9...91.1.` |  |
|  | 2 di 3 · 33 % | `..x.x.......x...` | `..x.x.......x...` | `1..1...11.11..d.` |  |
|  | 3 di 3 · 17 % | `...x......x.....` | `...x......x.....` | `1.1.1...1...1...` |  |
| ARP | 1 di 2 · 50 % | `x...x...x...x...` | `x.x.x.x.x.x.x.x.` | `.1.1.1.1.1.1.1.9` |  |
|  | 2 di 2 · 50 % | `x.x.x.x.x.x.x.x.` | `xxxxxxxxxxxxxxxx` | `................` |  |

**Le note.** SUB: fondamentale 59 %, terza 15 %, quarta 11 %, ottava 7 %, settima 7 %; note tenute. BASS: fondamentale 63 %, terza 17 %, ottava 10 %, quarta 10 %. PAD: accordi di settima 73 %, triadi 27 %; tenuti. VOX: un motivo - scende 50 %, sale 17 %, fa un arco 17 %, alterna due note 17 %; scala pentatonica 90 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su quinta 40 %, terza 33 %, fondamentale 27 %. ARP: le note dell'accordo in fila (fondamentale, terza, quinta, ottava).

**La progressione.** due accordi 46 %, quattro accordi 32 %, un accordo 18 %, tre accordi 4 %; ogni accordo dura 2 battute 46 %, 1 battuta 32 %, 4 battute 18 %, 8 battute 4 %; parte da casa 70 volte su 100; la fondamentale si muove di una quarta sopra 34 %, un grado sopra 23 %, un grado sotto 23 %, una terza sotto 13 %, una terza sopra 3 %, una quinta sopra 3 %; colori: settima 55 %, nona 32 %, triade 8 %. Le scale del genere: MINOR, DORIAN, PHRYG.

## BATIDA

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 3 · 75 % | `X.......X.......`<br>`X.....X.X.......` | `X.....X.X..x....`<br>`X..x..X.X..x..x.` | `...6.....3...f93`<br>`.....6....3..f.c` |  |
|  | 2 di 3 · 17 % | `X...X.......X...` | `X...X..x..X.X...` | `.............d..` |  |
|  | 3 di 3 · 8 % | `X.....X...X.....` | `X..x..X...X..x..` | `................` |  |
| SNARE | 1 di 3 · 83 % | `....X.......X.x.` | `....X.......X.x.` | `.......a.d...6.3` |  |
|  | 2 di 3 · 8 % | `....X.......X...` | `....Xg......Xg..` | `................` |  |
|  | 3 di 3 · 8 % | `...x....X..x....` | `...x....X..x....` | `................` |  |
| HAT | 1 di 4 · 36 % | `..x.....x.x.....` | `..x.x...x.x...x.` | `11.6.111.6.116..` | chiusura |
|  | 2 di 4 · 27 % | `..xx..x...xx..x.` | `x.xx.xx.x.xx.xx.` | `.9..1..9....1...` | chiusura, rullate |
|  | 3 di 4 · 18 % | `..x.......x...x.` | `..xx..x...xx..x.` | `1...1d..1...11..` | chiusura, rullate |
|  | 4 di 4 · 18 % | `..x.x...x.x...x.` | `x.x.x.x.x.x.x.x.` | `...1.d.....1.1..` | chiusura, rullate |
| SHAKER | 1 di 2 · 83 % | `xo..x.x.x.x.x.x.` | `xo.oxoxoxoxoxoxo` | `..f.............` |  |
|  | 2 di 2 · 17 % | `......o.......o.` | `..o...o...o...o.` | `11.111.111.111.1` |  |
| CONGA | 1 di 4 · 40 % | `x.....x.x.x.....` | `x.xx..x.x.xx..x.` | `....1..6....16.1` | chiusura, rullate |
|  | 2 di 4 · 30 % | `....x..x..o.....` | `....x..x..o.x.x.` | `1.f1..9.1..1.1..` | chiusura |
|  | 3 di 4 · 20 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1.1..11..11.1d` | chiusura, rullate |
|  | 4 di 4 · 10 % | `x.....x.o.x.....` | `x..x..x.o.x.x..o` | `..1.1..1...1.11.` | chiusura |
| PERC | 1 di 4 · 50 % | `....x..x.....x..`<br>`....x..x.x...x..` | `.x..x..x..x..x.x`<br>`.x..x..x.x.x.x.x` | `1.41.11.1f.41.4.`<br>`1.11.11.1...1.9.` |  |
|  | 2 di 4 · 17 % | `x........x....x.` | `x..x..x..x..x.x.` | `.11.11.1..11.d.1` | rullate |
|  | 3 di 4 · 17 % | `x......x.X....x.` | `x.x..x.x.X..x.x.` | `.1..1.....1d.1.1` |  |
|  | 4 di 4 · 17 % | `........x..X..x.` | `..x..x..x..X..x.` | `11..1..1.11.11.d` |  |
| RIM | 1 di 4 · 33 % | `...x..........x.` | `...x..........x.` | `......dd...d....` |  |
|  | 2 di 4 · 33 % | `......x.....x...` | `......x.....x...` | `.........d......` | rullate |
|  | 3 di 4 · 17 % | `...x..x.........` | `...x..x....x...x` | `................` |  |
|  | 4 di 4 · 17 % | `..x.......x.....` | `..x..x....x..x..` | `................` |  |
| TOM | 1 di 3 · 67 % | `......x.......x.`<br>`......x.......xx` | `......x.......x.`<br>`......x.......xx` | `1........61.61.d`<br>`6........61.61..` |  |
|  | 2 di 3 · 17 % | `x.....x.....x...` | `x.....x.....x...` | `..............11` |  |
|  | 3 di 3 · 17 % | `..........x..x..` | `..........x..x..` | `1.....1.....1.11` |  |
| BASS | 1 di 3 · 42 % | `x.....x.......x.` | `x.x...x.x.x...x.` | `...1.......1.5.5` |  |
|  | 2 di 3 · 33 % | `X.....x.x.......` | `X..x..x.x..x..x.` | `.66..6....1..1..` |  |
|  | 3 di 3 · 25 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1.....1..1..1.` |  |
| CHORD | 1 di 2 · 75 % | `..x.....x.....x.` | `..x..x..x..x..x.` | `1..1..1...3....3` |  |
|  | 2 di 2 · 25 % | `x..x..x.........` | `x..x..x.........` | `..1..1..1..1..1.` |  |
| LEAD | 1 di 4 · 50 % | `x.....x.x.......` | `x.....x.x.......` | `..1f91.1..11111.` |  |
|  | 2 di 4 · 17 % | `x.....x.x.......` | `x.xx.xx.x.xx.xx.` | `....1.......1...` |  |
|  | 3 di 4 · 17 % | `x.xx....x.x.....` | `x.xx.x.xx.x.x.x.` | `....1.1.........` |  |
|  | 4 di 4 · 17 % | `x.....x.x.......` | `x.x.x.x.x.x.x.x.` | `...1.1..........` |  |

**Le note.** BASS: fondamentale 41 %, terza 18 %, quarta 18 %, quinta 16 %, ottava 7 %. CHORD: triadi 91 %, accordi di settima 9 %. LEAD: un motivo - fa un arco 48 %, sale 31 %, scende 16 %, alterna due note 5 %; scala pentatonica 65 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 46 %, quinta 38 %, terza 15 %.

**La progressione.** quattro accordi 88 %, un accordo 4 %, due accordi 4 %, tre accordi 4 %; ogni accordo dura 1 battuta 88 %, 2 battute 4 %, 4 battute 4 %, 8 battute 4 %; parte da casa 70 volte su 100; la fondamentale si muove di un grado sopra 23 %, una terza sotto 23 %, una quarta sopra 18 %, una quinta sopra 18 %, un grado sotto 18 %; colori: triade 94 %. Le scale del genere: MINOR, MAJOR, DORIAN.

## GQOM

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 3 · 42 % | `X.....X.....x...` | `X.....X.....x...` | `...a....a.5.....` |  |
|  | 2 di 3 · 33 % | `X.....X.........`<br>`X.....X.....X...` | `X.....X...X..X..`<br>`X.....X.....X.X.` | `...6.......d....`<br>`..666...........` |  |
|  | 3 di 3 · 25 % | `X.....X..x......` | `X.....X..x......` | `..........99....` |  |
| SNARE | 1 di 3 · 42 % | `........x.......` | `........x.......` | `.....5...55..5..` |  |
|  | 2 di 3 · 33 % | `....X..X....x...` | `....X..X....x...` | `.9.......9......` | rullate |
|  | 3 di 3 · 25 % | `......x.......x.` | `......x.......x.` | `.....9.......9..` | rullate |
| HAT | 1 di 4 · 33 % | `......x.......x.` | `..x...x...x...x.` | `1..161.116.116..` | chiusura |
|  | 2 di 4 · 25 % | `..x.......x.....` | `..x..x....x..x..` | `1..11.991..1..1.` | chiusura, rullate |
|  | 3 di 4 · 25 % | `..x..x....x..x..` | `x.xx.x..x.xx.x..` | `.9..1.1..9....1.` | chiusura, rullate |
|  | 4 di 4 · 17 % | `x.......x.......` | `x...x...x...x...` | `..11.11d..11.11.` | chiusura, rullate |
| SHAKER | 1 di 2 · 83 % | `..x...x...x...x.` | `xoxoxoxoxoxo.oxo` | `............f...` |  |
|  | 2 di 2 · 17 % | `......o.......o.` | `..o...o...o...o.` | `11.111.111.111.1` |  |
| PERC | 1 di 4 · 45 % | `...x..x.....x...` | `...x..x.....x...` | `511.15..1155.151` | rullate |
|  | 2 di 4 · 18 % | `..........x.x...`<br>`...x......x.x...` | `...xx.....x.x...`<br>`...xx.....x.x..x` | `1.1..11......1..`<br>`111..1d......1d.` |  |
|  | 3 di 4 · 18 % | `x.......x.x.....`<br>`x.......x.x.x...` | `x.x..x..x.x..x..`<br>`x.x..x..x.x.xx.x` | `...11.1.....1...`<br>`.d.11.1.......d.` |  |
|  | 4 di 4 · 18 % | `.....x.......x..` | `.x...x...x...x..` | `1.111.1...1.1.1d` | rullate |
| CONGA | 1 di 4 · 33 % | `x..x..x.........`<br>`x..x..x.o.......` | `x..x..x...x.x..x`<br>`x..x..x.o.x.x..o` | `..1.1..1d..1.11.`<br>`..1.1..1...1.1d.` |  |
|  | 2 di 4 · 33 % | `...x..x.......x.` | `...x..x....x.xx.` | `1.1.1..11.1.1..d` | rullate |
|  | 3 di 4 · 17 % | `x..x..x.......x.` | `x.ox..x.x.ox..x.` | `............11.1` |  |
|  | 4 di 4 · 17 % | `..........o.x.x.` | `..o.x..x..o.x.x.` | `1..1..1.1..1.1.1` |  |
| TOM | 1 di 4 · 50 % | `............x.xx` | `............x.xx` | `1..1..1...19.9..` | rullate |
|  | 2 di 4 · 20 % | `..........x..x..` | `..........x..x..` | `1.d..d1.....1.11` |  |
|  | 3 di 4 · 20 % | `x.....x.....x...`<br>`x...........x...` | `x.....x.....x...`<br>`x...........x...` | `..........1..111`<br>`....d.d...d..111` |  |
|  | 4 di 4 · 10 % | `..........x..x..` | `x..x..x...x..x..` | `............1.11` |  |
| BASS | la sola | `x.....x.....x...` | `x.....x.....x...` | `...a.3.3.......3` |  |
| PAD | la sola | `x...............` | `x...............` | `......9.4.......` |  |
| VOX | 1 di 3 · 50 % | `................` | `................` | `1.1f1.9.11f.1...` |  |
|  | 2 di 3 · 33 % | `X.......x.x.....` | `X.......x.x.....` | `..111.1..d..1...` |  |
|  | 3 di 3 · 17 % | `..x.x.......x...` | `..x.x.......x...` | `1..1....1.1.....` |  |
| ARP | 1 di 2 · 50 % | `x.....x.....x...` | `x..x..x..x..x..x` | `..9..9.......1..` |  |
|  | 2 di 2 · 50 % | `x.....x.....x...` | `x.....x.....x...` | `..11.1...1...d.1` |  |

**Le note.** BASS: fondamentale 70 %, seconda 14 %, terza 9 %, quinta 5 %. PAD: accordi di settima 60 %, triadi 40 %; tenuti. VOX: un motivo - scende 38 %, alterna due note 38 %, fa un arco 19 %, sale 5 %; scala pentatonica 90 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su quinta 46 %, fondamentale 38 %, terza 15 %. ARP: le note dell'accordo in fila (fondamentale, terza, quinta, ottava).

**La progressione.** due accordi 74 %, un accordo 18 %, tre accordi 4 %, quattro accordi 4 %; ogni accordo dura 2 battute 74 %, 4 battute 18 %, 1 battuta 4 %, 8 battute 4 %; parte da casa 95 volte su 100; la fondamentale si muove di un grado sopra 22 %, una quarta sopra 22 %, una terza sotto 22 %, un grado sotto 22 %, una terza sopra 5 %, una quinta sopra 5 %; colori: triade 80 %, sus4 10 %. Le scale del genere: MINOR, PHRYG, H.MINOR.

## EXPERIMENT

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 4 · 75 % | `X.....X..X......`<br>`x.....X.........` | `X..x..X..X.x....`<br>`x..x..X.....x...` | `.............3.3`<br>`.........3.....3` | rullate |
|  | 2 di 4 · 8 % | `X..x.......x....` | `X..x.x...x.x..x.` | `................` |  |
|  | 3 di 4 · 8 % | `X..........x....` | `X.......x..x.x..` | `................` |  |
|  | 4 di 4 · 8 % | `X.........x.....` | `X....x....x....x` | `................` |  |
| SNARE | 1 di 4 · 42 % | `......x.....x..x` | `......x.....x..x` | `.5.....5...5..f.` |  |
|  | 2 di 4 · 25 % | `.....g..X.....g.` | `..g..g..X..g..g.` | `......99........` |  |
|  | 3 di 4 · 17 % | `.....x....X.....` | `.....x....X.....` | `d...............` |  |
|  | 4 di 4 · 17 % | `...x.....x....x.` | `...x.....x....x.` | `......d.........` | rullate |
| HAT | 1 di 4 · 33 % | `x...x..x..x.x...` | `xxx.xx.x..xxx.x.` | `...1..1.16...6.6` | chiusura, rullate |
|  | 2 di 4 · 33 % | `x.........x.x...` | `x..x..x...x.x...` | `.d6.11.611.6.11.` | chiusura, rullate |
|  | 3 di 4 · 17 % | `x.x....x.X.x....` | `x.xx.x.xxX.x.xx.` | `.1..1.1...1.d...` | chiusura |
|  | 4 di 4 · 17 % | `x...x..x........` | `x...x..x.x...x..` | `.111.11...1d1.1.` | chiusura, rullate |
| PERC | 1 di 4 · 33 % | `x..............x` | `x....x....x....x` | `.1111.1116.61d1.` | rullate |
|  | 2 di 4 · 33 % | `x...........x..x`<br>`....x.....x.x..x` | `x..x..x..x..x..x`<br>`.x..x..x..x.x.xx` | `..1..6..1.16.1..`<br>`1.16.6..16.6.1..` | rullate |
|  | 3 di 4 · 25 % | `..x.....x.......`<br>`..x.....x.......` | `..x.....x...x..x`<br>`..x.....x...x..x` | `1..1.11..191.9..`<br>`11..11.1..91.91.` |  |
|  | 4 di 4 · 8 % | `.x.x......x.....` | `.x.x...x..xx....` | `1.1.111.11..1111` |  |
| TOM | 1 di 4 · 33 % | `............x.xx` | `............x.xx` | `1....11..d11.1..` | rullate |
|  | 2 di 4 · 33 % | `......x.......x.`<br>`x.............x.` | `......x.......x.`<br>`x.....x.......xx` | `1....d...11.11.1`<br>`.........11d11..` |  |
|  | 3 di 4 · 17 % | `..........x..x..` | `..........x..x..` | `1.....1.....1.11` |  |
|  | 4 di 4 · 17 % | `x.....x.....x...` | `x.....x.....x...` | `..............11` |  |
| BASS | 1 di 3 · 42 % | `x...x...x.......` | `xx..x...x.x..x..` | `..5...15...11...` |  |
|  | 2 di 3 · 33 % | `x.....x....x....` | `x.....x....x....` | `.1..16.11.1.11..` |  |
|  | 3 di 3 · 25 % | `x...x.....x.....` | `x...x..x..x.x...` | `.1....1.1..1.199` |  |
| PAD | 1 di 2 · 67 % | `x...............` | `x...............` | `....1.3.6.61..1.` |  |
|  | 2 di 2 · 33 % | `x.....X....x....` | `x.....X....x....` | `....6...1.....6.` |  |
| ARP | 1 di 2 · 50 % | `x.x.xx.x.xx.x.x.` | `xxxxxxxxxxxxxxxx` | `................` |  |
|  | 2 di 2 · 50 % | `x.x.x....x..x...` | `x.x.xx.x.xx.x.x.` | `.1.4..1.1..1.1.1` |  |

**Le note.** BASS: fondamentale 26 %, quarta 23 %, seconda 19 %, terza 15 %, settima 15 %, quinta 3 %. PAD: triadi 50 %, accordi di settima 37 %, quinte vuote 13 %. ARP: le note dell'accordo in fila (fondamentale, terza, quinta, ottava).

**La progressione.** due accordi 46 %, quattro accordi 46 %, un accordo 4 %, tre accordi 4 %; ogni accordo dura 1 battuta 46 %, 2 battute 46 %, 4 battute 4 %, 8 battute 4 %; parte da casa 82 volte su 100; la fondamentale si muove di una terza sopra 41 %, un grado sotto 26 %, una quinta sopra 18 %, un grado sopra 10 %; colori: settima 27 %, nona 22 %, sus4 17 %, sus2 17 %, sesta 12 %, triade 7 %. Le scale del genere: WHOLE, HIRAJO, LOCRIAN.

## ELECTRO

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 2 · 67 % | `X.....x...X.....`<br>`X.....X.........` | `X.....x...X.....`<br>`X.....X.........` | `...6...3.....f33`<br>`...6.3..f.6...f.` | rullate |
|  | 2 di 2 · 33 % | `X.....X.........` | `X.....X.x.....x.` | `..........666...` |  |
| SNARE | 1 di 3 · 67 % | `....X.......X...` | `....X.......X...` | `.....6.33....33d` |  |
|  | 2 di 3 · 25 % | `....X.......X.g.` | `....X.......X.g.` | `......f....f...9` |  |
|  | 3 di 3 · 8 % | `....X.......X.g.` | `....X..g....Xgg.` | `................` |  |
| CLAP | la sola | `....X.......X...` | `....X.......X...` | `.......9......44` |  |
| HAT | 1 di 4 · 33 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `.1.1.6.6.1.6...1` | chiusura, rullate |
|  | 2 di 4 · 33 % | `x.x.x.x.X.x.x.x.` | `x.xxx.xxX.xxx.xx` | `.d...1...6......` | chiusura |
|  | 3 di 4 · 25 % | `..x.......X.....` | `..x...x...X...x.` | `19.11..91..11..1` | chiusura |
|  | 4 di 4 · 8 % | `x.xxx.xxx.xxx.xx` | `xxxxxxxxxxxxxxxx` | `................` | chiusura |
| OPEN HAT | la sola | `......x.......x.` | `......x.......x.` | `..d..4...4d....4` | rullate |
| COWBELL | 1 di 4 · 40 % | `..x.......x.....` | `..x...x...x...x.` | `1..111.11...d1.1` |  |
|  | 2 di 4 · 20 % | `..x.......x...x.` | `..x.x..x..x...x.` | `1.....1.....11..` |  |
|  | 3 di 4 · 20 % | `..x.x.........x.` | `..x.x...x...x.x.` | `1.....11..1..1..` |  |
|  | 4 di 4 · 20 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1.1..1....1.1.` |  |
| BASS | 1 di 3 · 58 % | `X.....x...x.....` | `X.....x...x.....` | `.4.1.4..1..1.44.` |  |
|  | 2 di 3 · 33 % | `x.....x.x.......` | `x..x..x.x..x....` | `..........1...1.` |  |
|  | 3 di 3 · 8 % | `x.....x...x.....` | `x.x...x.x.x...x.` | `...1.......1....` |  |
| STAB | 1 di 3 · 67 % | `x...........x...` | `x...........x...` | `..11d1d...6.....` |  |
|  | 2 di 3 · 17 % | `...x.......x....` | `...x.......x....` | `1.....1.........` |  |
|  | 3 di 3 · 17 % | `..x..x....x.....` | `..x..x....x.....` | `1...........1...` |  |
| ARP | 1 di 2 · 83 % | `x...x...x...x...` | `x.x.x.x.x.x.x.x.` | `.1.1.1.1.1.3.1.1` |  |
|  | 2 di 2 · 17 % | `x.X.x.x.x.x.x.x.` | `xxXxxxxxxxxxxxxx` | `................` |  |
| PERC | 1 di 4 · 33 % | `.x...x......x...`<br>`.....x......x.x.` | `.x...x......x...`<br>`.x...x...x..x.x.` | `1.11..1d1d1...1.`<br>`1.11..1.1.1.....` |  |
|  | 2 di 4 · 33 % | `......x.......x.` | `......x.......x.` | `1111.d.1111.1...` | rullate |
|  | 3 di 4 · 17 % | `..x.....x...x...` | `..x.....x...x...` | `.1...11..1....1.` |  |
|  | 4 di 4 · 17 % | `x.....x.........` | `x..x..x...x.....` | `.1...1...1..1.1.` |  |

**Le note.** BASS: fondamentale 45 %, ottava 31 %, quarta 10 %, quinta 8 %, terza 4 %. STAB: triadi 71 %, accordi di settima 29 %. ARP: le note dell'accordo in fila (fondamentale, terza, quinta, ottava).

**La progressione.** due accordi 60 %, un accordo 18 %, quattro accordi 18 %, tre accordi 4 %; ogni accordo dura 2 battute 60 %, 1 battuta 18 %, 4 battute 18 %, 8 battute 4 %; parte da casa 95 volte su 100; la fondamentale si muove di una quarta sopra 29 %, un grado sotto 29 %, una terza sopra 17 %, una terza sotto 17 %, un grado sopra 4 %, una quinta sopra 4 %; colori: triade 70 %, settima 16 %, sus4 9 %. Le scale del genere: MINOR, PHRYG, DORIAN.

## FOOTWORK

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 2 · 75 % | `X.........X.....`<br>`X.........X.X...` | `X..X......X..X..`<br>`X..X..X...X.X...` | `..3...6........6`<br>`.......3.3.3.6f.` |  |
|  | 2 di 2 · 25 % | `X...........X...` | `X.....X..x..X...` | `...f...........f` |  |
| SNARE | 1 di 2 · 58 % | `....x.......X..x` | `....x.......X..x` | `..4..4..44.4....` | rullate |
|  | 2 di 2 · 42 % | `........X.......` | `........X.......` | `....5......a.5f5` | rullate |
| CLAP | 1 di 2 · 83 % | `....X.......X...` | `....X.......X...` | `.......5......55` |  |
|  | 2 di 2 · 17 % | `......x.......x.` | `...x..x....x..x.` | `................` |  |
| HAT | 1 di 4 · 33 % | `..x...x...x.....` | `..x...x...x..gx.` | `11.11..616..1..1` | chiusura |
|  | 2 di 4 · 33 % | `x.....x.....x...` | `x..x..x..x..x..x` | `.61.1..d1.1..61.` | chiusura, rullate |
|  | 3 di 4 · 25 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...9...1.1.9.1.1` | chiusura, rullate |
|  | 4 di 4 · 8 % | `x.x.x.x.x.x.x.x.` | `xxx.xxx.xxx.xxx.` | `...1...1.......1` | chiusura |
| PERC | 1 di 4 · 33 % | `x.....x........x` | `x..x..x..x..x..x` | `.61.1..11.16.61.` |  |
|  | 2 di 4 · 25 % | `x.....x...x.....`<br>`x.....x...x.x...` | `x.x...x.x.x...x.`<br>`x.x...x.x.x.xx.x` | `.1.11..1.1.919.1`<br>`.9.11..1.1....9.` |  |
|  | 3 di 4 · 25 % | `.......x..x..x..` | `.x..x..x..x..x..` | `1.11.91.11.91.11` | rullate |
|  | 4 di 4 · 17 % | `..........x....x` | `..x....x..x....x` | `11.11.1.11.11d1.` | rullate |
| TOM | 1 di 4 · 33 % | `..............x.`<br>`..............xx` | `..............x.`<br>`..............xx` | `1.11.1d.1111d1.d`<br>`d.11.1d.1111d1..` |  |
|  | 2 di 4 · 33 % | `x.....x.....x...` | `x.....x.....x...` | `..1d.1..1d11.11d` |  |
|  | 3 di 4 · 17 % | `..x.....x.....x.` | `..x..x..x..x..x.` | `1.....1.....1..1` |  |
|  | 4 di 4 · 17 % | `..........x..x..` | `..........x..x..` | `1.....1.....1.11` |  |
| SUB | 1 di 3 · 42 % | `x...............` | `x.....x..x..x...` | `...1......1..5..` | con il kick |
|  | 2 di 3 · 33 % | `x...............` | `x..x......x..x..` | `......6..1..1...` | con il kick |
|  | 3 di 3 · 25 % | `x...............` | `x...............` | `...1..9.919.11..` | con il kick |
| CHORD | 1 di 2 · 67 % | `x.........x.....` | `x.........x.....` | `.1.3..1......33.` |  |
|  | 2 di 2 · 33 % | `x..X..X.........` | `x..X..X.........` | `.6........1.....` |  |
| VOX | 1 di 3 · 33 % | `x..x..x.........` | `x..x..x..x..x..x` | `..1.1...1.1.....` |  |
|  | 2 di 3 · 33 % | `...x......X.....` | `...x......X.....` | `6.1.1.1.d6..1..1` |  |
|  | 3 di 3 · 33 % | `..X.x.......x...` | `..X.x.......x...` | `1..1..1.111...66` |  |

**Le note.** SUB: fondamentale 43 %, quarta 23 %, quinta 18 %, terza 11 %, ottava 5 %. CHORD: accordi di settima 56 %, triadi 44 %. VOX: un motivo - scende 32 %, fa un arco 32 %, alterna due note 32 %, sale 5 %; scala pentatonica 92 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su quinta 43 %, fondamentale 36 %, terza 21 %.

**La progressione.** due accordi 60 %, un accordo 18 %, quattro accordi 18 %, tre accordi 4 %; ogni accordo dura 2 battute 60 %, 1 battuta 18 %, 4 battute 18 %, 8 battute 4 %; parte da casa 82 volte su 100; la fondamentale si muove di un grado sopra 42 %, una terza sotto 29 %, una quarta sopra 17 %, una terza sopra 4 %, una quinta sopra 4 %, un grado sotto 4 %; colori: settima 63 %, nona 22 %, sus4 9 %. Le scale del genere: MINOR, DORIAN, PENT.-.

## TRANCE

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | la sola | `X.......X.......`<br>`X.......X...X...` | `X...X...X...X...`<br>`X...X...X...X..x` | `..2..2...2.f..26`<br>`...2.....4....f.` | rullate |
| CLAP | 1 di 2 · 67 % | `....X.......X..x` | `....X.......X..x` | `.5.....5.....55.` | rullate |
|  | 2 di 2 · 33 % | `............x...` | `............x...` | `.........666....` |  |
| HAT | 1 di 4 · 42 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `.5.5...5.1.5.1.1` | chiusura, rullate |
|  | 2 di 4 · 33 % | `..x...x...x...x.` | `..xx..xx..xx..xx` | `16..1...16..16..` | chiusura, rullate |
|  | 3 di 4 · 17 % | `..x.......X.....` | `..x...x...X...x.` | `11.11..11..11d.1` | chiusura |
|  | 4 di 4 · 8 % | `o.X.o.X.o.X.o.X.` | `oxXxoxXxoxXxoxXx` | `................` | chiusura |
| OPEN HAT | 1 di 2 · 83 % | `......x.......x.` | `..x...x...x...x.` | `...5.3.3.3.1.3.5` |  |
|  | 2 di 2 · 17 % | `......x.......x.` | `......x.......x.` | `..1.......1d....` | rullate |
| RIDE | 1 di 3 · 50 % | `x.o.x.o.x.o.x.o.` | `x.oxx.oxx.oxx.ox` | `.9...9..........` | rullate |
|  | 2 di 3 · 33 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `.1.1.1.1...1...1` |  |
|  | 3 di 3 · 17 % | `......x.......x.` | `..x...x...x...x.` | `1..11..11..11..1` |  |
| PERC | 1 di 3 · 50 % | `................` | `................` | `1..1..f11.f1.1f1` |  |
|  | 2 di 3 · 33 % | `x.......x.......`<br>`x.............xx` | `x.......x.......`<br>`x.............xx` | `...1..1d..11..1.`<br>`...1..1...11.d..` |  |
|  | 3 di 3 · 17 % | `...x.......x....` | `...x.......x....` | `1.....1.1.1...11` |  |
| BASS | 1 di 3 · 42 % | `..x...x...x...x.` | `.xx..xx..xx..xx.` | `...1...1...1...1` |  |
|  | 2 di 3 · 33 % | `.xx..xx..xx..xx.` | `.xxx.xxX.xxx.xxx` | `................` |  |
|  | 3 di 3 · 25 % | `......x.......X.` | `..x...x...x...X.` | `.1.1.1.1.1.1.1.1` |  |
| PAD | la sola | `x...............` | `x...............` | `......4.d.2.....` |  |
| ARP | 1 di 2 · 67 % | `x..xx...x...x.X.` | `x.xxx.xxx.xxx.Xx` | `.1...1...1...3..` |  |
|  | 2 di 2 · 33 % | `x.xxx.xxx.xxx.xx` | `xxxxxxxxxxxxxxxx` | `................` |  |
| LEAD | 1 di 4 · 33 % | `x.......x...x...` | `x.xx.x.xx.x.x.x.` | `......6....1.6.6` |  |
|  | 2 di 4 · 33 % | `x.......x.......` | `x..x..x.x.......` | `..1.61.1..161161` |  |
|  | 3 di 4 · 17 % | `x..x..x.x.......` | `x.xx.xx.x.xx.x.x` | `.......1....1.d.` |  |
|  | 4 di 4 · 17 % | `x.......x...x...` | `x.......x...x...` | `..11.111..11.111` |  |

**Le note.** BASS: fondamentale 75 %, ottava 11 %, quarta 7 %, quinta 5 %. PAD: triadi 70 %, accordi di settima 30 %; tenuti. ARP: le note dell'accordo in fila (fondamentale, terza, quinta, ottava). LEAD: un motivo - fa un arco 55 %, scende 24 %, sale 16 %, alterna due note 5 %; scala pentatonica 92 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 35 %, quinta 35 %, terza 29 %.

**La progressione.** quattro accordi 88 %, un accordo 4 %, due accordi 4 %, tre accordi 4 %; ogni accordo dura 1 battuta 60 %, 2 battute 32 %, 4 battute 4 %, 8 battute 4 %; parte da casa 70 volte su 100; la fondamentale si muove di un grado sopra 24 %, una quinta sopra 24 %, una terza sotto 19 %, un grado sotto 19 %, una terza sopra 7 %, una quarta sopra 7 %; colori: triade 90 %, sus4 5 %. Le scale del genere: MINOR, H.MINOR, PHRYG.

## UK DRILL

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | la sola | `X......x..x.....`<br>`X.........x.....` | `X......x..x.....`<br>`X.........x.....` | `..6..1...1...1..`<br>`..1.1..c.3...3.5` | chiusura |
| SNARE | la sola | `........X.....X.`<br>`........X.....X.` | `........X.....X.`<br>`........X.....X.` | `.....26...69...4`<br>`......f4..26.2.6` | rullate |
| HAT | la sola | `..x...x...x...x.`<br>`..x...x...x...x.` | `x.x.x.x.x.x.x.x.`<br>`x.x.x.x.x.x.x.x.` | `...2.2...6...4..`<br>`...2.4.2.2...6.b` | rullate |
| PERC | 1 di 4 · 33 % | `..x.....x.....x.` | `..x.....x.....x.` | `...1..11...d.1..` | chiusura, rullate |
|  | 2 di 4 · 33 % | `.......x.....X..` | `.......x.....X..` | `..11..1.1..d..1.` | chiusura |
|  | 3 di 4 · 17 % | `......x.......x.` | `......x.......x.` | `..1....11..1.1..` | chiusura |
|  | 4 di 4 · 17 % | `...x.......x....` | `...x.......x....` | `..1....11....11.` | chiusura |
| RIM | 1 di 4 · 50 % | `......x.........` | `......x.........` | `...9........9.f.` |  |
|  | 2 di 4 · 17 % | `...x......x.....` | `...x......x.....` | `................` |  |
|  | 3 di 4 · 17 % | `...x..........x.` | `...x...x...x..x.` | `................` |  |
|  | 4 di 4 · 17 % | `..x.......x.....` | `..x..x....x..x..` | `................` |  |
| SUB | la sola | `X...............` | `X...............` | `......2d2.f.....` | con il kick |
| PAD | la sola | `x...............` | `x...............` | `......2.b.....9.` |  |
| LEAD | 1 di 4 · 50 % | `x..x..x.x.......` | `x..x..x.x..x..x.` | `..1.11.1..1.1...` |  |
|  | 2 di 4 · 17 % | `x...x.x.x.......` | `x.x.x.x.x.x.x.x.` | `...1.......1....` |  |
|  | 3 di 4 · 17 % | `x..x....x...x.x.` | `x.xx.x.xx.x.x.x.` | `....1.1....1....` |  |
|  | 4 di 4 · 17 % | `x.......x.......` | `x...x.x.x.......` | `..11......111.1.` |  |
| VOX | 1 di 3 · 67 % | `...x......x.....` | `...x......x.....` | `1.1.1..61...d...` |  |
|  | 2 di 3 · 17 % | `x.......x.x.....` | `x.......x.x.....` | `...1........1...` |  |
|  | 3 di 3 · 17 % | `..x.x.......x...` | `..x.x.......x...` | `...1......1.....` |  |

**Le note.** SUB: fondamentale 52 %, seconda 15 %, terza 12 %, sesta 9 %, ottava 6 %, quinta 3 %, quarta 3 %. PAD: triadi 50 %, accordi di settima 50 %; tenuti. LEAD: un motivo - fa un arco 63 %, scende 16 %, sale 16 %, alterna due note 5 %; scala pentatonica 52 volte su 100, altrimenti tutte e sette le note; fino a 10 semitoni sopra la fondamentale; poggia su fondamentale 38 %, terza 38 %, quinta 25 %. VOX: un motivo - scende 73 %, alterna due note 18 %, sale 5 %, fa un arco 5 %; scala pentatonica 90 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su quinta 50 %, fondamentale 25 %, terza 25 %.

**La progressione.** quattro accordi 46 %, due accordi 32 %, un accordo 18 %, tre accordi 4 %; ogni accordo dura 1 battuta 46 %, 2 battute 32 %, 4 battute 18 %, 8 battute 4 %; parte da casa 82 volte su 100; la fondamentale si muove di un grado sopra 28 %, una terza sotto 28 %, una quinta sopra 19 %, una quarta sopra 11 %, un grado sotto 11 %, una terza sopra 3 %; colori: triade 92 %. Le scale del genere: MINOR, PHRYG, H.MINOR.

## HARDCORE

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 2 · 92 % | `X.......X.......`<br>`....X.......X...` | `X...X...X...X...`<br>`X...X...X...X...` | `.7...1...7.....1`<br>`.964.272..9..2f2` | chiusura, rullate |
|  | 2 di 2 · 8 % | `X...X...X...X...` | `X.x.X.x.X.x.X.x.` | `................` | chiusura |
| CLAP | la sola | `....X.......X...`<br>`....X.......X...` | `....X.......X...`<br>`....X.......X...` | `...2.2.d.2...42f`<br>`...2.2.d.2...64f` | rullate |
| HAT | 1 di 2 · 83 % | `......x.......x.`<br>`......x.......x.` | `..x...x...x...x.`<br>`..x...x...x...x.` | `15.335.31..513..`<br>`1...1..31..1ff.f` |  |
|  | 2 di 2 · 17 % | `..x...x...X...x.` | `x.x.x.x.x.X.x.x.` | `...........d.1.1` |  |
| OPEN HAT | la sola | `......x.......x.` | `......x.......x.` | `..d4......d....9` | rullate |
| PERC | 1 di 4 · 33 % | `..x.x...x.......` | `..x.x...x.x...x.` | `11.1..11.1..1d.1` | chiusura, rullate |
|  | 2 di 4 · 33 % | `x...........x..x` | `x..x..x..x..x..x` | `.d1.1..11.1..11.` | chiusura, rullate |
|  | 3 di 4 · 17 % | `x.......x.......` | `x.......x.......` | `..111.1..11.1.11` | chiusura |
|  | 4 di 4 · 17 % | `....x.......x...` | `....x..x....x..x` | `1.11..1.111...1.` | chiusura |
| STAB | 1 di 4 · 33 % | `x.....x.....x...` | `x.....x.....x...` | `.611.1..1.61.11.` |  |
|  | 2 di 4 · 33 % | `...X.......x....` | `...X.......x....` | `161.611.1.1.161.` |  |
|  | 3 di 4 · 17 % | `X.......x.....x.` | `X.......x.....x.` | `...1..1...11d...` |  |
|  | 4 di 4 · 17 % | `..x..x....x.....` | `..x..x....x.....` | `1..1..1....11d..` |  |
| LEAD | 1 di 4 · 42 % | `x.......x.......` | `x..x..x.x.......` | `..1.55.1.1111511` |  |
|  | 2 di 4 · 33 % | `x...x...x...x...` | `x.x.x.x.x.x.x.x.` | `...1.1.1.6.1.6.6` |  |
|  | 3 di 4 · 17 % | `x.xx.x.xx.x.x.x.` | `x.xxxxxxxxxxxxxx` | `.d..............` |  |
|  | 4 di 4 · 8 % | `x.x.....x.x.x...` | `x.xx.x.xx.x.x.x.` | `....1.1..1...1.1` |  |
| PAD | la sola | `x...............` | `x...............` | `......9.4.......` |  |
| BASS | 1 di 2 · 83 % | `x.......x.......` | `x...x...x...x...` | `..1...15..1...15` |  |
|  | 2 di 2 · 17 % | `x...x...x...x...` | `x.x.x.x.x.x.x.x.` | `................` |  |

**Le note.** STAB: triadi 54 %, quinte vuote 26 %, accordi di settima 21 %. LEAD: un motivo - fa un arco 48 %, sale 40 %, scende 8 %, alterna due note 5 %; scala pentatonica 51 volte su 100, altrimenti tutte e sette le note; fino a 13 semitoni sopra la fondamentale; poggia su fondamentale 55 %, quinta 27 %, terza 18 %. PAD: accordi di settima 80 %, triadi 20 %; tenuti. BASS: fondamentale 90 %, seconda 7 %, quarta 3 %.

**La progressione.** due accordi 46 %, quattro accordi 32 %, un accordo 18 %, tre accordi 4 %; ogni accordo dura 2 battute 46 %, 1 battuta 32 %, 4 battute 18 %, 8 battute 4 %; parte da casa 95 volte su 100; la fondamentale si muove di un grado sotto 44 %, un grado sopra 34 %, una terza sotto 13 %, una terza sopra 3 %, una quarta sopra 3 %, una quinta sopra 3 %; colori: triade 85 %, sus2 8 %. Le scale del genere: PHRYG, MINOR, H.MINOR.

## PHONK

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | la sola | `X.........X.X...`<br>`X.........X.....` | `X.........X.X...`<br>`X.........X.....` | `..11.....1.2...4`<br>`..1..1f4.1.52...` | chiusura |
| SNARE | la sola | `........X.......`<br>`........X.....x.` | `........X.......`<br>`........X.....x.` | `.2.2.....b44..4.`<br>`.2.222...4.222.f` | rullate |
| HAT | 1 di 3 · 83 % | `x...x...x...x...`<br>`x...x...x...x...` | `x.x.x.x.x.x.x.x.`<br>`x.x.x.x.x.x.x.x.` | `.5.1.1.5.1.3.1.3`<br>`.5.1.1.8.1.5.3.f` | rullate |
|  | 2 di 3 · 8 % | `x.x.x...x...x...` | `x.xgx.x.xgx.x.x.` | `.1.....1...1...1` |  |
|  | 3 di 3 · 8 % | `x.xxx.x.xxx.x.x.` | `xxxxxxxxxxxxxxxx` | `................` |  |
| COWBELL | 1 di 4 · 40 % | `x.....x.........` | `x..x..x...x.....` | `..1.11..1..1dd1.` |  |
|  | 2 di 4 · 20 % | `x.....x.x.......` | `x..x..x.x..x..x.` | `..1.......1.11..` |  |
|  | 3 di 4 · 20 % | `..x.......x.....` | `..x...x...x...x.` | `1..1....1...11..` |  |
|  | 4 di 4 · 20 % | `..x.....x.....x.` | `..x.x...x...x.x.` | `1..1..1...1..1..` |  |
| PERC | 1 di 3 · 67 % | `......x.......x.` | `......x.......x.` | `1.61.6.61.61.1..` | chiusura |
|  | 2 di 3 · 17 % | `..x.....x..x....` | `..x.....x..x....` | `......1...1...1.` | chiusura |
|  | 3 di 3 · 17 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1...........1.` | chiusura |
| SUB | 1 di 2 · 58 % | `X.....x...X.....` | `X.....x...X.....` | `.4......1..441..` | con il kick |
|  | 2 di 2 · 42 % | `x.......x.......` | `x.......x.......` | `......1..5a.1a..` | con il kick |
| LEAD | 1 di 3 · 67 % | `x.....x.x.......` | `x.....x.x.......` | `..1f61.1..1a1.a.` |  |
|  | 2 di 3 · 25 % | `x..x....x...x.x.` | `x.xx.x.xx.x.x.x.` | `....1.9....9....` |  |
|  | 3 di 3 · 8 % | `x.....x.x.......` | `x.x.x.x.x.x.x.x.` | `...1.1.1...1....` |  |
| PAD | la sola | `x...............` | `x...............` | `......4.9.......` |  |
| VOX | 1 di 2 · 67 % | `....x.......x...` | `....x.......x...` | `6.61....161.....` |  |
|  | 2 di 2 · 33 % | `..........x.....` | `..........x.....` | `d.1d1...d1..1...` |  |

**Le note.** SUB: fondamentale 68 %, quinta 8 %, seconda 8 %, ottava 5 %, terza 5 %, settima 5 %. LEAD: un motivo - fa un arco 55 %, scende 24 %, sale 16 %, alterna due note 5 %; scala pentatonica 66 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 50 %, quinta 25 %, terza 25 %. PAD: accordi di settima 70 %, triadi 30 %; tenuti. VOX: un motivo - scende 45 %, alterna due note 45 %, sale 5 %, fa un arco 5 %; scala pentatonica 90 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 55 %, quinta 36 %, terza 9 %.

**La progressione.** due accordi 60 %, un accordo 18 %, quattro accordi 18 %, tre accordi 4 %; ogni accordo dura 2 battute 60 %, 1 battuta 18 %, 4 battute 18 %, 8 battute 4 %; parte da casa 95 volte su 100; la fondamentale si muove di un grado sotto 29 %, un grado sopra 17 %, una quarta sopra 17 %, una quinta sopra 17 %, una terza sotto 17 %, una terza sopra 4 %; colori: triade 83 %, settima 9 %. Le scale del genere: PHRYG, MINOR, H.MINOR.

## BAILE FUNK

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 3 · 75 % | `X.....X.X.......`<br>`X.....X.........` | `X..X..X.X..X..X.`<br>`X..X..X...X.....` | `....1.....3.3..4`<br>`.6..13.1f..39f..` | chiusura |
|  | 2 di 3 · 17 % | `X.....X.X.......` | `X..X..X.X..X..X.` | `...............d` | chiusura |
|  | 3 di 3 · 8 % | `X..X..X.........` | `X..X..X...X..X..` | `................` | chiusura |
| SNARE | 1 di 2 · 92 % | `....X.......X...`<br>`....X.......X..x` | `....X.......X...`<br>`....X.......X..x` | `.2.2.2.2.....229`<br>`.222..52.2...2e.` | rullate |
|  | 2 di 2 · 8 % | `....X.......X...` | `..x.X.....x.X...` | `................` |  |
| HAT | 1 di 4 · 42 % | `..x.......x.....` | `..x...x...x...x.` | `15.111.11..115.5` | rullate |
|  | 2 di 4 · 42 % | `..x...x...x...x.`<br>`..x...x...x...x.` | `x.xx.xx.x.xx.xx.`<br>`x.xx.xx.x.xxxxxx` | `.f..1..a....1..1`<br>`.5..1...........` |  |
|  | 3 di 4 · 8 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `.1.1.1.1...1.1.1` |  |
|  | 4 di 4 · 8 % | `x.xx.xx.x.xx.xx.`<br>`x.xx.xx.x.xxxxxx` | `xxxxxxxxxxxxxxxx`<br>`xxxxxxxxxxxxxxxx` | `................`<br>`................` |  |
| PERC | 1 di 3 · 58 % | `.......x..x..x..`<br>`..x....x..x..x..` | `..x..x.x..x..x.x`<br>`..x..x.x..x..xxx` | `...1..4..1.14.4.`<br>`.4.4..7..1.1f...` |  |
|  | 2 di 3 · 33 % | `...x...x.....x..` | `...x...x.x.g.x..` | `..1..61...1.1.16` |  |
|  | 3 di 3 · 8 % | `x.............x.` | `x.....x.x.....x.` | `..11.1.1.11111.1` |  |
| CONGA | 1 di 4 · 25 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1....11..11.11` | chiusura |
|  | 2 di 4 · 25 % | `x.....x.o.x.....` | `x..x..x.o.x.x..o` | `..1....1...1.11.` | chiusura |
|  | 3 di 4 · 25 % | `x.....x.x.o.....` | `x.ox..x.x.ox..x.` | `.......1....11.1` | chiusura |
|  | 4 di 4 · 25 % | `...x..x.......x.` | `...x..x....x.xx.` | `1.1....11.1.1..1` | chiusura |
| TOM | 1 di 4 · 40 % | `..........x..x..` | `..........x..x..` | `d..d..d.11.11.11` | chiusura |
|  | 2 di 4 · 20 % | `x.....x.....x...` | `x.....x.....x...` | `...1......1..11.` | chiusura |
|  | 3 di 4 · 20 % | `......x..x....x.` | `......x..x....x.` | `1..1......1.11..` | chiusura |
|  | 4 di 4 · 20 % | `x.....x.......x.` | `x..x..x.x..x..x.` | `..........1.11..` | chiusura |
| SUB | 1 di 3 · 58 % | `x...............` | `x.....x.x.....x.` | `.447......1b.4..` | con il kick |
|  | 2 di 3 · 25 % | `x.....x...x.....` | `x..x..x...x..x..` | `........1..1..1.` | con il kick |
|  | 3 di 3 · 17 % | `x...............` | `x...............` | `...1..1.d.11.11.` | con il kick |
| VOX | 1 di 4 · 42 % | `..x.x.......x...` | `..x.x.......x...` | `1..1..1.1.11..1.` |  |
|  | 2 di 4 · 25 % | `...x......x.....` | `...x......x.....` | `1.1.19..1...1...` |  |
|  | 3 di 4 · 17 % | `x..x....X.......` | `x..x..x.X..x..x.` | `..1.1.....1.1...` |  |
|  | 4 di 4 · 17 % | `X.......x.x.....` | `X.......x.x.....` | `..111.......1...` |  |
| STAB | 1 di 4 · 33 % | `x.......x.......` | `x.......x.......` | `..1d.11...1d1...` |  |
|  | 2 di 4 · 33 % | `...X.......x....` | `...X.......x....` | `1d...11.1.......` |  |
|  | 3 di 4 · 17 % | `x.....x.....x...` | `x.....x.....x...` | `...1....1.......` |  |
|  | 4 di 4 · 17 % | `..x..x....x.....` | `..x..x....x.....` | `1.......1.......` |  |

**Le note.** SUB: fondamentale 67 %, quinta 10 %, settima 10 %, terza 8 %, quarta 4 %. VOX: un motivo - alterna due note 58 %, scende 17 %, fa un arco 17 %, sale 8 %; scala pentatonica 92 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 46 %, quinta 38 %, terza 15 %. STAB: triadi 76 %, accordi di settima 24 %.

**La progressione.** quattro accordi 46 %, due accordi 32 %, un accordo 18 %, tre accordi 4 %; ogni accordo dura 1 battuta 46 %, 2 battute 32 %, 4 battute 18 %, 8 battute 4 %; parte da casa 82 volte su 100; la fondamentale si muove di un grado sopra 45 %, una quarta sopra 19 %, un grado sotto 19 %, una terza sotto 11 %, una terza sopra 3 %, una quinta sopra 3 %; colori: triade 92 %. Le scale del genere: MINOR, PHRYG, H.MINOR.

## MERENGUE

| parte | famiglia | base | pieno | in più | |
| --- | --- | --- | --- | --- | --- |
| KICK | 1 di 2 · 92 % | `X.......X.......`<br>`X.......X.......` | `X...X...X...X...`<br>`X...X...X...X...` | `......2...5...5.`<br>`...5.....2e2.2f2` | rullate |
|  | 2 di 2 · 8 % | `X.......X.......` | `X.......X.......` | `................` |  |
| SNARE | la sola | `......x.......x.`<br>`......x.......x.` | `......x.......x.`<br>`......x.......x.` | `....4....42226.2`<br>`.2.42.....2.f4.f` | rullate |
| HAT | 1 di 2 · 75 % | `X.x.X.x.X.x.X.x.` | `X.xxX.xxX.xxX.xx` | `.3...3...6...c..` |  |
|  | 2 di 2 · 25 % | `..x...x...x...x.` | `x.x.x.x.x.x.x.x.` | `...1.9.1.9.1.1.1` |  |
| PERC | 1 di 3 · 50 % | `x.....x.x.....x.`<br>`x.....x.x.....x.` | `x..x.xx.x..x.xx.`<br>`x..x.xx.x....xx.` | `.11.1..4.41.1..4`<br>`.11.1..4.4ddf..f` | rullate |
|  | 2 di 3 · 25 % | `x.....x.x.....x.` | `x.xx..x.x.xx..x.` | `.9..19.1....11.1` | rullate |
|  | 3 di 3 · 25 % | `....x.......x.x.` | `....x..x....x.xx` | `1991.11.1.11.1..` | rullate |
| CONGA | 1 di 4 · 33 % | `..........o.x.x.` | `..o.x..x..o.x.x.` | `1..1.11.1..9.9..` | chiusura, rullate |
|  | 2 di 4 · 22 % | `...x..x....x.xx.` | `x..x.xx.x..x.xx.` | `.d1.1..1..1.1...` | chiusura, rullate |
|  | 3 di 4 · 22 % | `...x..x.......x.` | `...x..x....x.xx.` | `1.1.11.d1.1.1...` | chiusura, rullate |
|  | 4 di 4 · 22 % | `......x...x...x.` | `..x..xx...x..xx.` | `1..11..11d.11...` | chiusura, rullate |
| BASS | 1 di 2 · 58 % | `x.......x.......` | `x.....x.x.....x.` | `...717.....71..7` |  |
|  | 2 di 2 · 42 % | `x.......x.......` | `x...x...x...x...` | `...1.115...1..11` |  |
| PIANO | 1 di 4 · 42 % | `x..x..x.........` | `x..x..x.x..x..x.` | `..5..1.1..5..5.1` |  |
|  | 2 di 4 · 25 % | `x.....x...x.....` | `x..x..x...x..x..` | `..1..1.91..1..11` |  |
|  | 3 di 4 · 25 % | `..x.......x..x..` | `..x..x.x..x..x.x` | `1..1..1.1..1..1.` |  |
|  | 4 di 4 · 8 % | `......x.......x.` | `..x...x...x...x.` | `1..1.1.11..1.1.1` |  |
| LEAD | 1 di 4 · 42 % | `x.....x.x.......` | `x.x.x.xxx.x.x.xx` | `.5.5.1...1.5.5..` |  |
|  | 2 di 4 · 25 % | `x.x..x..x...x...` | `x.xx.x.xx.x.x.x.` | `....1.1..9.9...1` |  |
|  | 3 di 4 · 25 % | `x.....x.x.......` | `x.....x.x.......` | `..1f91.9..111.11` |  |
|  | 4 di 4 · 8 % | `x.x.x.xxx.x.x.xx` | `xxxxxxxxxxxxxxxx` | `................` |  |
| VOX | 1 di 3 · 50 % | `....x.......x...` | `....x.......x...` | `9.91....911.....` |  |
|  | 2 di 3 · 33 % | `...X......x.....` | `...X......x.....` | `1.1.1...1d..1...` |  |
|  | 3 di 3 · 17 % | `x.......x.x.....` | `x.......x.x.....` | `...11.......1...` |  |

**Le note.** BASS: fondamentale 53 %, quinta 42 %, ottava 4 %. PIANO: accordi di settima 73 %, triadi 27 %. LEAD: un motivo - fa un arco 71 %, sale 16 %, scende 8 %, alterna due note 5 %; scala pentatonica 51 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 40 %, quinta 40 %, terza 20 %. VOX: un motivo - scende 48 %, alterna due note 31 %, sale 16 %, fa un arco 5 %; scala pentatonica 65 volte su 100, altrimenti tutte e sette le note; fino a 12 semitoni sopra la fondamentale; poggia su fondamentale 43 %, quinta 43 %, terza 14 %.

**La progressione.** quattro accordi 74 %, due accordi 18 %, un accordo 4 %, tre accordi 4 %; ogni accordo dura 1 battuta 88 %, 2 battute 4 %, 4 battute 4 %, 8 battute 4 %; parte da casa 82 volte su 100; la fondamentale si muove di una quarta sopra 47 %, un grado sopra 19 %, una quinta sopra 19 %, una terza sotto 13 %; colori: triade 68 %, settima 26 %. Le scale del genere: MAJOR, MIXOLY, MINOR.
