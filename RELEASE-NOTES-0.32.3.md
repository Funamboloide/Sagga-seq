# SAGGA SEQ 0.32.3 - Note di rilascio (solo il Pi)

Una cosa nuova sulla pagina del Pi: **DA ABLETON**. I clip MIDI che esporti da Ableton diventano un progetto SAGGA **a
passi**, con ogni traccia già sul canale della macchina che la suona. Nel piano per il live era il passo più lungo
(il progetto SAGGA di ogni palette, un'ora e mezza): adesso i pattern li fa la pagina, e a te resta di controllarli e
aggiungere scene, LFO e lane. Conta mezz'ora per palette invece di un'ora e mezza.

**Il firmware dell'FM-1 non cambia.** Resta la 0.32.1 che hai dentro. Si aggiorna solo il Pi.

| il pezzo | il file |
| --- | --- |
| l'FM-1 | niente da fare: resta `sagga-0.32.1.fwsc` |
| il Pi (la pagina, il banco, il bridge del grid) | `sagga-hub-0.32.3.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

## DA ABLETON

1. **In Ableton**: tasto destro su un clip MIDI, **Export MIDI Clip**. Dai al file il nome `palette-parte-numero`: per
   esempio `A-basso-2.mid` è il basso, pattern 2.
2. **Sulla pagina del Pi**, sezione **DA ABLETON**: il nome del progetto, tutti i file insieme, **Fai il progetto**.
3. Torna un rapporto: dove è andato ogni clip, e cosa guardare. Da lì **Apri nell'editor**, poi **Manda all'FM-1**.

Le parti seguono il tuo set:

| tracce | le parti | la macchina |
| --- | --- | --- |
| 1-3 | cassa, basso, basso 2 | M8 1 |
| 4-7 | rullante, hat, perc, top | M8 2 |
| 8-11 | lead, accordi, pad, arp | MicroDexed |
| 12 | sample (intro, interludi) | Zynthian |

Il canale di ogni traccia è il suo numero (1-12). Se la tua matrice li vuole diversi, cambiali nella tabella della
sezione e premi **Salva i canali**: restano sul Pi. Le parole che riconosce, in italiano e in inglese, sono nella
pagina e in `LEGGIMI.md`.

**Cosa diventa un clip.**

- Ogni nota va sul sedicesimo più vicino. Quanto era spostata resta nel NUDGE del passo, così lo swing del clip resta.
- Un rullo (la stessa nota due volte in un sedicesimo) diventa un RATCHET; fino a sei note insieme, un accordo.
- Una nota che scivola nella successiva diventa un TIE (legato).
- 1, 2 o 4 battute sono un pattern; i clip più corti ricominciano da capo nella traccia, come le copie dell'FM-1.
- Da 5 a 8 battute: una coppia di pattern in CHAIN. L'unico clip lungo di una parte (fino a 16 battute): una traccia
  TAPE.
- Un clip di tutta la batteria (`drums`, `batteria`, `beat` nel nome) si divide da solo: cassa, rullante, hat, perc,
  piatti, ognuno sulla sua traccia.
- La scena N suona il clip N di ogni parte.

Non entrano i CC e il pitch bend dei clip: il rapporto lo dice. Rifare un progetto con lo stesso nome lascia il
vecchio fra le sue versioni.

Sugli M8: un campione di batteria con **TRANSP OFF** suona uguale con qualunque nota, quindi le note del Drum Rack
vanno bene come sono.

## Anche nella 0.32.3: il confronto dei tuoi log

Nell'ultima raccolta dal Pi vero c'era una sonda segnata (b031). Era di nuovo una questione di tempo: l'FM-1 aveva
tirato il dado un millisecondo prima di un tick di clock, e il messaggio è arrivato dopo il tick. Il confronto adesso
prova anche questo caso da solo: quella raccolta dà 0 errori, e le raccolte di prima danno gli stessi rapporti di prima.

## Come è stato provato

**Sul Pi vero e sull'FM-1 vero non ho provato niente.** Non ho nemmeno clip esportati dal tuo Ableton: li ho fatti
come li scrive Ableton (un file con la traccia del tempo e la traccia delle note, il nome del clip dentro).

| la prova | il risultato |
| --- | --- |
| il progetto suonato dal firmware vero, nel simulatore: otto parti per otto battute (swing, rullo, accordi, TAPE, CHAIN, il kit diviso) | 290 note su 290, ognuna sul suo canale, al massimo 0,9 ms dal clip |
| i file MIDI: i due formati, 96 e 480 tick, il running status, le note spente a velocity 0, i file rotti | letti; i rotti rifiutati con il motivo |
| le parti dai nomi, i passi, le copie, i canali salvati, le scene, i limiti | 82 controlli, 0 errori |
| la pagina in un browser vero, larga come un telefono | la tabella, il salvataggio dei canali, niente scroll di lato |
| la pagina del Pi e l'editor, le prove di sempre | 179 e 276 controlli, 0 errori |
| 23 rotture fatte apposta nel convertitore e nella pagina | trovate tutte. Al primo giro quattro erano passate: le prove erano deboli e le ho rinforzate |

Mandami due o tre clip veri esportati dal tuo Ableton: li faccio passare qui e controllo che escano come dentro
Ableton.

## Installare

Solo il Pi: sulla pagina, **AGGIORNA IL PI**, `sagga-hub-0.32.3.zip`. L'FM-1 non si tocca.

## La prima volta

* Guarda la tabella dei canali in **DA ABLETON**: deve corrispondere alla matrice di RaspiMIDIHub (quali canali vanno a
  M8 1, M8 2, MicroDexed, Zynthian). Se no, cambiala e **Salva i canali**.
* Prova con una palette sola: esporta i clip, **Fai il progetto**, leggi il rapporto, **Manda all'FM-1** e suona.
