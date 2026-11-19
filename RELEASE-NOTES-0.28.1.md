# SAGGA SEQ 0.28.1 - Note di rilascio

Mi avevi chiesto: "Aggiorna la pagina sagga mod". **Eccola**: le lane sono otto, e SHAPE e DEST arrivano dove arriva
l'FM-1. Strada facendo sono saltati fuori due errori, corretti anche quelli.

| il pezzo | il file |
| --- | --- |
| l'FM-1 | `sagga-0.28.1.fwsc` |
| il Pi: la pagina SAGGA Mod nuova (e tutto il resto, come sempre) | `sagga-hub-0.28.1.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati **tutti e due**: le manopole LANE 7 e 8 mandano dei numeri che solo l'FM-1 0.28.1 capisce.

## La pagina SAGGA Mod

| cosa | fino alla 0.28 | adesso |
| --- | --- | --- |
| **le manopole LANE** | 1-6 | **1-8** |
| **SHAPE** | fino a DECAY | **fino a ENV** (l'inviluppo) |
| **DEST** | fino a SWING | **fino a MOD ONLY** (una sorgente per la MOD MATRIX: non manda niente) |

* **LANE 7 e LANE 8** muovono la base delle lane 7 e 8 della traccia del tablet (quella che scegli con TRACK su SAGGA
  Live o Motori), e la mandano subito al synth. In un progetto nuovo la lane 7 è il CC 73 (l'attacco) e la lane 8 il
  CC 72 (il rilascio).
* **Tornano indietro**: se giri la base della lane 7 o 8 sull'FM-1 (ENV, la pagina della lane, K3), la manopola della
  pagina la segue. Come le altre.
* **SHAPE e DEST** sull'FM-1 avevano ENV e MOD ONLY dalla 0.20, la pagina no. Se l'LFO del tablet era su ENV o MOD ONLY,
  la manopola riceveva un valore fuori dalla sua scala. Adesso li ha tutti, con gli stessi nomi dello schermo.
  L'FM-1 adesso prende MOD ONLY anche dalla pagina (prima il CC 96 si fermava a SWING).
* La pagina ha **una riga in più**: le otto lane occupano le righe 3-6, poi i THROWS, poi ENERGY / GENRE / KEY /
  PROGRESSION, e in fondo i sedici interruttori L1-L16.

**I numeri, per chi collega altro**: le lane 1-6 restano sul canale 13, CC 101-106. Le lane 7 e 8 sono sul **canale 12,
CC 62 e 63**. Sul canale 13 restava un solo numero libero che torna indietro alle pagine (il 119): i 98-100 il Pi se li
tiene, come succedeva al 101 della lane 1 (vedi la 0.20.6). Il canale 12 è comunque "la traccia del tablet", come le
lane.

## Due errori corretti

1. **Un LFO che cambia destinazione.** Un LFO su CC con il canale 13-16, passato a VEL, GATE, CHANCE, TIMING o SWING
   (che vogliono una traccia): lo schermo diceva `TRACK 16` e l'LFO muoveva la traccia 1, perché le tracce sono dodici.
   Adesso diventa la **traccia 12**, l'ultima che c'è. Vale dal pannello, dal grid e dalla pagina. Sul grid, nella vista
   LFO, la riga delle tracce si accende solo per 1-12, e i pad 13-16 non fanno niente.
2. **Una PROPOSAL che entra fuori tempo.** Una traccia con il loop che parte più avanti (HOME + ALG: START 2) e una
   proposta in attesa: quando la proposta entra rimette lo START sul passo 1, e la traccia restava un passo (o un
   pezzetto di passo) fuori dalla battuta. Adesso va dove dice la battuta. L'ha trovato l'esploratore; c'era già nella
   0.27.

## Come è stato provato

| la prova | quanto |
| --- | --- |
| le prove nuove | 10 controlli nel simulatore (le lane 7 e 8 dalla pagina al synth e indietro, MOD ONLY, il bersaglio dell'LFO dalla pagina e dal grid; la proposta che entra in tempo, guardata ogni 10 ms per una battuta, con QUANTISE AUTO e NOW) e 7 nelle prove delle pagine (SHAPE e DEST con i nomi dell'FM-1, le otto lane, ogni manopola che torna indietro): 0 errori |
| 8 errori rimessi apposta, uno alla volta (ENV che manca, la lane 8 che non torna, MOD ONLY rifiutato, il CC 62 ignorato, il bersaglio fuori dalle tracce, il pad 14 del grid, la proposta fuori tempo, la proposta rimessa in fila a metà del tick) | le prove li trovano tutti e 8 |
| il cuore del sequencer | 30.968.676 controlli, 0 errori |
| i motori THEORY | 215.628.289 controlli, 0 errori |
| il simulatore (il firmware vero che gira sul computer) | 1.541 controlli, 0 errori; 26 giri di gesti a caso con i rilevatori degli errori di memoria: 0 errori |
| l'esploratore: ogni gesto del pannello, del grid e della pagina, in 30 situazioni | 102.082 gesti da soli, 11.995 coppie di gesti, 200 sessioni a caso: 0 errori (al primo giro, con il tablet: la proposta fuori tempo, sopra; corretta) |
| l'editor del Pi, il bridge del grid, la pagina del Pi, le pagine SAGGA, il banco | 265 + 325 + 176 + 90 + 76 controlli, 0 errori |

**Non ho un FM-1 in mano**: tutto questo è provato sul simulatore, non sullo strumento vero.

## Installare

Come sempre: prima il Pi (`sagga-hub-0.28.1.zip`), poi l'FM-1 (`sagga-0.28.1.fwsc`). I passi sono in `INSTALLA.md`.
Sullo schermo, dopo l'aggiornamento: `SAGGA SEQ 0.28.1` per tre secondi. I progetti non cambiano: quelli della 0.28 si
aprono come sono.

## Cosa provare per primo

1. **LANE 7**: sulla pagina SAGGA Mod muovi LANE 7. Sul synth della traccia del tablet si muove il CC 73.
2. **Il ritorno**: sull'FM-1 tieni ENV, OCT+ fino a `LANE 8/8`, gira K3. La manopola LANE 8 della pagina la segue.
3. **MOD ONLY**: sulla pagina porta DEST in fondo. Sull'FM-1, LFO pagina 2: `DESTINATION MOD ONLY`.

## Da sapere

* Con l'FM-1 ancora sulla 0.28, LANE 7 e LANE 8 non fanno niente (il resto della pagina sì).
* Se avevi cambiato a mano il CC di qualche cella della pagina Mod, resta come l'avevi messo: le celle nuove sono solo
  LANE 7 e LANE 8.
