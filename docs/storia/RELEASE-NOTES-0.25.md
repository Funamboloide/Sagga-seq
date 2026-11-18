# SAGGA SEQ 0.25 - Note di rilascio

Mi avevi chiesto se al sequencer mancava altro. Ti avevo scritto una lista di sei cose, e mi hai detto "fai tutto".
**Sono fatte tutte e sei.**

| il pezzo | il file |
| --- | --- |
| l'FM-1 (e il cervello del grid) | `sagga-0.25.fwsc` |
| il Pi: la pagina, l'editor, le pagine SAGGA, il custode, il bridge del grid, la prova al banco | `sagga-hub-0.25.zip` |
| come si installa e si aggiorna | `INSTALLA.md` |

Vanno installati tutti e due. I progetti di prima si aprono come sono, e suonano come prima.

## Le sei cose

| cosa mancava | adesso |
| --- | --- |
| **il metro**: la battuta era sempre di 16 step | la battuta può avere **da 3 a 32 step**, divisi in tempi come vuoi: 7/8, 5/4, 6/8, 9/8... (GLO pagina 4). Tutto quello che aspetta "la battuta" aspetta questa |
| **i poliritmi veri**: 5 o 7 colpi nello spazio di 4 | sei valori nuovi dello step (HOME 1 K3, dopo 1/32T): cinque o sette step nel tempo di quattro |
| **TURING e NUMERIC** ragionavano in 16 | TURING può essere **lungo quanto la traccia**; NUMERIC si adatta alla battuta |
| **i motori non si ascoltavano** | il lead risponde agli accordi, le percussioni al rullante, il basso lascia spazio al lead |
| **la melodia non conosceva l'accordo** | FOLLOW ha un modo nuovo, **MELODY**: la melodia resta dov'è e le note importanti vanno sull'accordo |
| **LONGER e SHORTER dal tablet** | due tasti nuovi nella pagina SAGGA Live |

In più due correzioni sul Pi: il grid non parla più all'FM-1 mentre lo aggiorni, e l'editor mostra le copie subito.

## 1. Il metro

Fino alla 0.24 una battuta era 16 sedicesimi, sempre. Potevi fare una traccia da 14 step, ma l'FM-1 continuava a
contare le battute in 16: i cambi di pattern, gli accordi, le mosse cadevano ogni 16 step.

Adesso la battuta la decidi tu, in **GLO pagina 4, THE METRE** (in PERF è la quarta pagina):

| manopola | cosa fa |
| --- | --- |
| **K1 BAR** | quanti step ha la battuta, da 3 a 32. 16 è il 4/4 di sempre, 14 il 7/8, 20 il 5/4, 12 il 3/4 o il 6/8, 18 il 9/8 |
| **K2 BEATS** | come si divide in tempi. 14 step: 2+2+3, 2+3+2 oppure 3+2+2. 16 step: 4/4, oppure 3+3+2, 3+2+3, 2+3+3 |

Le altre due caselle ti dicono il nome del metro (7/8) e dove sei (battuta.step).

* **Da fermo** il cambio è immediato. **Mentre suona** aspetta la fine della battuta (lo schermo dice
  `BAR 14: 7/8 2+2+3 AT THE BAR`), e tutte le tracce ripartono insieme da lì.
* **Le tracce lunghe un numero di battute seguono**: una traccia da 16 diventa da 14, una da 32 diventa da 28. Lo
  schermo dice quante: `BAR 14: 7/8 2+2+3, 16 TRACKS FOLLOW`. I pattern **non vengono riscritti**: se torni a 16, li
  ritrovi interi.
* **Una traccia di un'altra lunghezza resta com'è.** Una traccia da 19 contro una battuta da 14 è la tua polimetria.
* **Tutto quello che aspetta la battuta aspetta questa**: un cambio di lunghezza, un pattern in coda, QUANTISE, WHEN
  ed EVERY, le MOSSE e la loro frase, la song, GENRE LIVE, lo STOP a fine battuta.
* **Gli accordi cambiano ogni battuta del metro.** In 7/8 un accordo dura 14 step.
* **La libreria e i motori fanno i pattern nel metro.** Una cassa in quattro, in 7/8 2+2+3, diventa una cassa sui
  tre tempi. I pattern dei motori, quando cambi metro, vengono rifatti da soli nel metro nuovo.
* **GROOVE, ACCENT, DENSITY, COOK** sanno dove sono i tempi del metro.
* Nell'**editor del Pi** il metro è nella scheda Progetto, e ogni riga di step ha i segni dei tempi. Un **file MIDI**
  esce con il metro giusto.

## 2. I poliritmi veri

Lo step di una traccia (HOME 1 K3) arrivava fino a 1/32T. Girando ancora trovi sei valori nuovi:

| valore | cosa vuol dire |
| --- | --- |
| 1/16 5:4 | **cinque** step nel tempo di quattro sedicesimi (un quarto) |
| 1/8 5:4 | cinque step nel tempo di quattro ottavi (mezza battuta) |
| 1/4 5:4 | cinque step nel tempo di quattro quarti (una battuta di 4/4) |
| 1/16 7:4, 1/8 7:4, 1/4 7:4 | lo stesso con **sette** |

L'esempio più semplice: una traccia con 5 step a 1/4 5:4 e la cassa in quattro. Senti **cinque contro quattro**, e le
due tracce si ritrovano insieme a ogni battuta, per sempre.

Il clock MIDI ha 24 scatti per quarto, e un quinto di quarto sono 4,8 scatti: non cade su uno scatto. L'FM-1 suona
ognuno di questi step **al suo momento esatto, fra uno scatto e l'altro**. Per questo i cinque colpi sono uguali fra
loro e la traccia non scivola mai.

Sul **grid**, vista TRACK, riga 4: il pad 15 è il cinque, il pad 16 il sette. Premuto ancora, passa al valore dopo.
Swing, GROOVE, ratchet e arpeggio funzionano come su ogni altro step.

## 3. TURING lungo quanto la traccia, NUMERIC nella battuta

**TURING.** La sua frase era lunga al massimo 16 step e girava dentro la traccia. Adesso la manopola della lunghezza
(SEQ 2, K3) dopo il 16 ha **TRACK**: la frase è lunga quanto la traccia, fino a 64 step. Se allunghi o accorci la
traccia, la frase la segue. Sul grid: vista TRACK 3, riga 6, pad 16.

**NUMERIC.** I suoi sedici ritmi sono scritti su 16 step. Su una traccia più corta suonava solo l'inizio del ritmo.
Adesso il ritmo viene **adattato agli step che ha**: ogni colpo va al suo posto in proporzione. Vale per la battuta
del metro (14 step in 7/8) e per un loop più corto di una battuta. Su 16 step suona come prima.

Una cosa che cambia anche in 4/4: una traccia NUMERIC **più corta di 16 step** adesso suona il ritmo adattato, non il
suo inizio tagliato. Se avevi un pezzo così, suonerà diverso.

## 4. Le parti si ascoltano

Fino alla 0.24 i motori facevano ogni parte da sola. Solo la cassa veniva guardata (il rumble la evita, il sub la
cerca). Adesso una parte nasce **insieme alla parte a cui risponde**:

| questa parte | risponde a |
| --- | --- |
| LEAD, VOX, ARP | gli accordi |
| le percussioni (PERC, CONGA, TOM, COWBELL) | il rullante |
| i bassi (BASS, SUB, RUMBLE, LOG DRUM) | il lead |

Dove l'altra parte attacca, questa tace più spesso. Subito dopo, suona più spesso. Così il lead suona nei vuoti degli
accordi e il basso lascia spazio sotto il lead.

Misurato su 60 semi per ognuno dei 26 stili: sugli attacchi dell'altra parte i colpi calano di un quarto (dal 23 al
28 % in meno), subito dopo crescono (dal 14 al 18 % in più).

* Funziona **in qualunque ordine** fai le parti.
* Se **rifai gli accordi** (BEAT, un altro seme, il dado, UNDO), dopo un attimo il lead e l'arpeggio vengono rifatti
  da soli per rispondere agli accordi nuovi. Restano le stesse parti, dello stesso seme.
* La cassa, il rullante, gli hat e gli accordi non rispondono a nessuno: sono identici alla 0.24.
* L'altra parte può essere anche un pattern della libreria o uno scritto da te.

## 5. La melodia conosce l'accordo

Con FOLLOW una traccia segue gli accordi: tutto il pattern viene spostato sull'accordo che suona. Per un basso va
bene. Per una melodia no: lo stesso disegno salta su e giù a ogni accordo.

FOLLOW adesso ha un quarto modo, **MELODY** (ARP pagina 4, K1, dopo LEGATO):

* la melodia **resta dove l'hai scritta**;
* le **note forti** vanno alla **nota più vicina dell'accordo che suona**. Sono forti le note sui tempi della battuta
  e le note più lunghe di uno step;
* le **note corte fra i tempi** restano come sono: sono note di passaggio;
* una **nota tenuta** mentre l'accordo cambia scivola alla nota più vicina dell'accordo nuovo.

Un esempio in LA minore con gli accordi Am, F, C, G. La melodia ha LA, DO, MI sui tempi:

| accordo | la melodia suona |
| --- | --- |
| Am | LA DO MI |
| F | LA DO **FA** |
| C | **SOL** DO MI |
| G | **SOL SI RE** |

Ogni nota si sposta di un tono al massimo. Con il FOLLOW di prima tutta la melodia saltava di una terza o di una
quarta.

**I LEAD e i VOX fatti da BEAT, BAND, i dadi e i motori prendono MELODY da soli.** Se poi sulla stessa traccia metti
un basso o degli accordi, torna il FOLLOW normale. Un lead **fatto prima della 0.25** resta com'era: gira ARP 4 K1
fino a MELODY, oppure rifallo con BEAT.

Puoi usarlo anche su una melodia scritta da te: accendi FOLLOW e scegli MELODY.

## 6. LONGER e SHORTER dal tablet

Nella pagina **SAGGA Live** ci sono due tasti nuovi, SHORTER e LONGER. Fanno quello che fanno le mosse sull'FM-1:
tutte le tracce lunghe la metà, o il doppio. Mentre suona il cambio arriva alla battuta dopo; da fermo è immediato.
Uno annulla l'altro.

## Le due correzioni sul Pi

**Il grid non parla all'FM-1 mentre lo aggiorni.** Durante un aggiornamento l'FM-1 diventa un altro dispositivo, che
si chiama "Felucca Update". Il bridge del grid lo prendeva per l'FM-1 e gli mandava un messaggio al secondo per tutta
l'installazione. L'ho visto nel log di una tua installazione. Non ha fatto danni, ma non doveva succedere. Adesso il
bridge aspetta, e torna quando l'FM-1 riparte.

**L'editor mostra le copie subito.** Quando nell'editor del Pi allunghi una traccia, le copie del pattern le vedevi
solo dopo il Salva. Adesso le vedi mentre scrivi il numero.

## Come è stato provato

Tutto nel **simulatore**: è il firmware vero, compilato per il computer. Non su un FM-1 vero, perché non ne ho uno.
Il simulatore controlla la logica, i tempi e il MIDI che esce. Non può dire come suona: quello lo senti tu.

| la prova | il risultato |
| --- | --- |
| **la suite intera**, sul codice finale | tutta verde |
| le prove del cuore del firmware | 29,8 milioni di controlli, 0 errori |
| le prove dei motori THEORY (150 semi per ognuno dei 26 stili) | 42,8 milioni di controlli, 0 errori |
| le prove del simulatore | 1395 controlli, 0 errori (68 sono nuovi, per le cose della 0.25) |
| le prove dell'editor e del convertitore del Pi | 238 controlli, 0 errori |
| **l'esploratore completo**: 27 situazioni (4 nuove: il 7/8, il 5/4, i poliritmi, la melodia) | 89.842 gesti da soli, 10.796 coppie di gesti, 200 sessioni da 60 gesti: **0 errori, niente da guardare** |
| le prove del simulatore con i **controlli di memoria** (ASan e UBSan) | 0 errori |
| il piano per l'FM-1 vero (28 sessioni) e quello del banco (28 sessioni), contro il simulatore | 0 errori, niente da guardare |

Due inciampi da dirti. Sono del computer su cui faccio le prove, non del firmware:

* in un giro la prova del programma di test per il PC è fallita una volta. È una prova a tempo vero contro un FM-1
  finto (non usa il firmware). Rifatta 14 volte, da sola e sotto carico, è sempre passata;
* nel giro dopo **il disco si è riempito**. Uno strumento del repository che non c'entra con l'FM-1 (strati) lasciava
  un file audio nei file temporanei a ogni prova: in due settimane di prove erano 24 GB. L'ho corretto (adesso li
  toglie), ho liberato il disco e ho rifatto la suite da capo: tutta verde.

**Rotture fatte apposta.** Una prova che non fallisce mai non prova niente. Ho rotto il firmware in dodici punti, uno
alla volta, per vedere se le prove se ne accorgono. Se ne sono accorte tutte e dodici:

| cosa ho rotto | chi se n'è accorto |
| --- | --- |
| al cambio di metro le tracce non ripartono insieme | 3 prove del metro (l'esploratore no: vedi sotto) |
| i pattern dei motori non vengono rifatti nel metro nuovo | 2 prove, e l'esploratore: 14 errori nella situazione del 7/8 |
| il TURING non segue la lunghezza della traccia | 2 prove |
| un poliritmo viene rimesso a tempo come una traccia normale | 3 prove |
| NUMERIC lascia due colpi attaccati | 2 prove |
| l'FM-1 non dice ai motori qual è la parte a cui rispondere | 1 prova |
| nei motori nessuna parte tace dove l'altra attacca | 3 prove dei motori |
| le risposte non vengono rifatte quando rifai gli accordi | 1 prova |
| nessuna nota della melodia è "forte" | 2 prove |
| una nota tenuta non si sposta al cambio di accordo | 1 prova |
| fra due note ugualmente vicine vince quella sopra | 6 prove |
| un lead fatto da BEAT non prende MELODY | 2 prove |

Ho rotto apposta anche una situazione dell'esploratore (le ho fatto promettere una cosa non vera): l'esploratore l'ha
rifiutata prima di cominciare.

**L'esploratore ha una regola in più.** La regola MOTORI adesso controlla anche il metro: da fermo, ogni pattern dei
motori deve essere nel metro della macchina (a meno che tu non l'abbia cambiato a mano). E la guarda anche alla fine
di ogni sessione. Un limite onesto: se al cambio di metro le tracce non ripartissero insieme, l'esploratore non se ne
accorgerebbe. Quel caso lo guardano le prove fisse, e se ne accorgono.

Al primo giro l'esploratore aveva trovato **una cosa da guardare**, e l'ho guardata: girare la nota di uno step e
rimetterla com'era lascia la "penna" (la nota che prende il prossimo step che accendi) su quella nota. È giusto così,
è come funziona la penna dalla 0.8. Adesso l'esploratore lo sa, e nel giro finale non c'è niente da guardare.

**Cosa non è stato provato**

* Niente di tutto questo su un FM-1 vero.
* Come suonano i motori che si ascoltano e la melodia in MELODY. I numeri dicono che fanno quello che devono; se
  musicalmente non ti convincono, dimmi cosa senti e si cambia la regola.
* LONGER e SHORTER dal tablet vero (dal tablet finto sì).

## Installare

Come le altre volte, tutti e due i pezzi: `INSTALLA.md` ha i passi. Sull'FM-1 lo schermo dice `SAGGA SEQ 0.25` per tre
secondi all'accensione.

## Cosa provare per primo

1. **Il 7/8.** Fai una band (SEQ + nero 7 tenuto). Da fermo, GLO pagina 4, gira K1 di due scatti indietro: `BAR 14`.
   Premi PLAY.
2. **Cinque contro quattro.** Su una traccia melodica: lunghezza 5 (HOME 1 K2), poi HOME 1 K3 in avanti finché leggi
   `1/4 5:4` (è il primo valore dopo 1/32T). Accendi i cinque step. Con la cassa in quattro sotto.
3. **La melodia.** SOURCE su FREE (SEQ 8 K1, due scatti), poi BAND: l'armonia si accende da sola. La traccia 8 è il
   lead, già su MELODY: ascoltala, poi gira ARP 4 K1 indietro fino a HOLD e senti la differenza.
4. **TURING sulla traccia.** Una traccia da 32 con qualche step acceso. SEQ 2: K1 su TURING, K3 tutto avanti fino a
   `TRACK`, poi SEQ + bianco 6 per farlo partire.
5. **LONGER / SHORTER sull'FM-1 vero.** Questa è la prova che manca ancora dalla 0.24: sulle MOSSE (SEL + GLO),
   SEL + nero 6 e SEL + nero 5, mentre suona.

## Da sapere

**Del metro**

* Il metro è **uno solo per tutto il progetto**.
* Una traccia lunga **esattamente una battuta** segue la battuta in tutti e due i versi: se in 4/4 avevi una traccia
  da 14, porti la battuta a 14 e poi di nuovo a 16, la traccia diventa da 16.
* La casella BEATS mostra 9 caratteri. Una divisione lunga la leggi intera nella riga sotto.
* Dal **tablet** la battuta non si cambia.
* I motori scrivono in quattro tempi, e il pattern viene steso sulla battuta. Un 7/8 dei motori è un 4/4 adattato, non
  un ritmo pensato in sette.
* Un pattern dei motori che hai **cambiato a mano** non viene rifatto quando cambi metro: resta nel suo metro, e
  finché la battuta è un'altra nemmeno l'ENERGIA lo tocca. (Le parti che rispondono a un'altra parte o seguono la
  cassa vengono rifatte comunque.)

**Dei poliritmi**

* Ci sono solo il cinque e il sette contro quattro.
* Su una traccia in poliritmo le durate di EXPO (BEAT, BAR...) non sono giuste.

**Delle parti che si ascoltano**

* Una parte ascolta **una sola** altra parte, e solo il suo ritmo.
* Quando la parte a cui risponde viene rifatta, anche lei viene rifatta intera: uno step scritto a mano lì sopra si
  perde.

**Della melodia**

* Una nota corta fra i tempi resta quella scritta. Sopra un accordo fuori scala può stridere per un sedicesimo.

**Con una 0.24**

Un progetto della 0.25 aperto da una 0.24 suona in 4/4, un poliritmo diventa 1/16, un TURING su TRACK diventa da 16,
una traccia MELODY torna su HOLD. Il resto è uguale.

**Ancora aperto dalle versioni prima**

* **LONGER e SHORTER non sono mai stati provati su un FM-1 vero** (punto 5 qui sopra).
* I sei messaggi persi nella prova al banco della 0.23: la causa non è ancora nota. Nelle prove dopo non è più successo.
* Ogni prova al banco lascia sul Pi un file `backup-*.sgq`: puoi cancellarli.

**La dimensione**

Il firmware cresce di 11.044 byte: 459.660 su 581.564 (la 0.24: 448.616). La RAM cresce di 960 byte: 71.776 su 98.304
(la 0.24: 70.816). C'è posto per tutti e due. Le misure sono della build di GitHub.
