# SAGGA SEQ 0.32.6 - Note di rilascio (l'FM-1 e il Pi: il DELAY negativo, la nota M8)

Questa versione cambia **l'FM-1 e il Pi**. Aggiorna tutti e due, prima il Pi e poi l'FM-1 (`docs/INSTALLA.md`).
I progetti non cambiano: quelli di prima si aprono come sono, e la 0.32.1 apre quelli della 0.32.6.

| il pezzo | il file |
| --- | --- |
| l'FM-1 | `sagga-0.32.6.fwsc` |
| il Pi | `sagga-hub-0.32.6.zip` |
| norns, la Gills | niente da fare |

## L'FM-1: un passo in anticipo al cambio di scena

**Cosa non andava.** Un passo che parte prima del suo posto (un **DELAY** negativo, un **NUDGE** negativo, lo
humanize, il GROOVE o un LFO che lo spinge avanti) l'FM-1 lo decide un passo prima, e lo manda prima che arrivi la
battuta. Fino alla 0.32.5 questa decisione non sapeva cosa portava la battuta. Così, al cambio di scena:

* la prima nota partiva **prima del Program Change** della scena: suonava con lo strumento vecchio;
* partiva **dal pattern di prima**, e il primo passo del pattern nuovo non suonava;
* una traccia che la scena **accende** perdeva il suo primo passo;
* una traccia che la scena **spegne** suonava ancora il suo primo passo.

Lo stesso con la song, con un mute che aspetta la battuta, con un pattern in coda e con RESTART. Per questo il
manuale diceva di usare solo DELAY positivi.

**Adesso.** Quando decide il passo, l'FM-1 guarda cosa porta la battuta: l'entrata dopo della song, la scena in coda,
i mute, i pattern e il RESTART che aspettano quel momento. Il passo parte come la battuta lo vuole: dal pattern della
scena, con il **Program Change della scena subito prima**, sul suo canale. Una traccia che la scena accende suona il
suo primo passo, in anticipo come deve; una traccia che la scena spegne tace. Con QUANTISE BAR, dove la scena fa
ripartire la traccia dal suo primo passo, parte quel passo, una volta sola (la 0.32.5 ne mandava due: quello vecchio
in anticipo e quello nuovo sulla battuta).

**Quando non si può sapere prima.** Se la scena porta **un'altra tonalità** (per una traccia IN KEY), **un altro
metro**, o se aspettano una **SNAPSHOT**, il **TRANSPOSE** della tonalità, **STOP** alla battuta o una lunghezza
nuova, quel passo si decide al suo posto e suona **sulla griglia**, senza anticipo, quella volta sola. Meglio pochi
millisecondi tardi che la nota sbagliata.

**Un secondo sguardo, al momento di partire.** Fra quando il passo è deciso e quando parte passa al massimo un
passo. Se in mezzo cambia qualcosa (una scena messa in coda all'ultimo momento, una scena con QUANTISE NOW, un mute, il
passo riscritto), al momento di partire l'FM-1 lo decide di nuovo, come stanno le cose, e parte lo stesso in anticipo.

**Mai due note per un passo.** Un passo già partito resta: si ferma solo se, quando arriva il suo posto, la traccia è
muta. Se invece era stato deciso muto e al suo posto deve suonare (una traccia che VIAGGIO accende, un pattern che
EVOLVE cambia sulla battuta), suona lì, sulla griglia.

**Quindi da qui i DELAY negativi si possono usare.** Se una macchina è lenta, puoi darle un DELAY negativo invece di
ritardare tutte le altre. Funziona anche il contrario, come prima.

Le tracce a polimetro (cinque o sette contro quattro) non guardano la battuta in anticipo: hanno solo gli altri due
sguardi.

## Il Pi: la nota M8 in DA ABLETON

L'M8 suona un campione alla sua altezza vera sulla nota che chiama **C-4**. Le batterie del Drum Rack arrivano con
le loro note (36 la cassa, 38 il rullante, 42 l'hat) e sull'M8 suonano più alte o più basse. Prima andavano
sistemate a mano, con il TRANSPOSE di ogni traccia.

* Nella sezione **DA ABLETON** c'è la casella **nota M8 (N)**. Scrivi il numero della tua nota (la prova per trovarla
  è nel manuale, «La nota giusta»); accanto la pagina dice come la chiama l'FM-1 (48 è C3). Poi **Salva canali e
  nota**.
* Da lì ogni parte di batteria che va a un M8 (canali 1-7 e 13-16) arriva su N: la sua nota più usata diventa N, le
  altre si spostano con lei della stessa distanza, come farebbe il TRANSPOSE. La **PEN** della traccia è N, così
  anche i passi nuovi che scrivi sull'FM-1 suonano giusti.
* Una parte di batteria su un canale che non va a un M8 (per esempio la PERC sul 12, lo Zynthian) resta com'è, e il
  rapporto lo dice.
* Casella vuota: le note restano quelle del clip, come prima. Il rapporto ti ricorda la casella.
* La tabella delle parti adesso dice la **macchina del canale** che scrivi: 1-3 l'M8 1, 4-7 e 13-16 l'M8 2, 8-11 il
  MicroDexed, 12 lo Zynthian.
* Da un terminale: `python3 sagga_ableton.py ... --nota-m8 48`.
* Il `LEGGIMI.md` del Pi corregge quello che diceva la 0.32.3: sull'M8 **TRANSP OFF** non fa suonare uguali tutte le
  note che arrivano (toglie solo le trasposizioni dell'M8 stesso). Per questo serve la nota M8.

## Cosa non è provato

Niente di questa versione è stato provato sull'FM-1 vero, sugli M8 o sul Pi vero. È provato nel simulatore, che fa
girare il codice dell'FM-1 stesso, e con la pagina del Pi in un browser vero (Chromium) sul computer:

* un test nuovo del simulatore (`t0326_early_bound`) prova la scena in coda, la song, QUANTISE BAR, il mute che
  aspetta, la scena che spegne, l'altra tonalità, una scena NOW prima e dopo la partenza del passo, una scena messa in
  coda all'ultimo momento, con il DELAY e con il NUDGE;
* i test di DA ABLETON provano la nota M8 nel convertitore, nella pagina e nel browser.

Prima del live del 29 dicembre prova sull'FM-1 vero un cambio di scena con un DELAY negativo su una traccia, e
ascolta la batteria di una palette sugli M8 con la tua N.

## La dimensione

Il firmware cresce di 2.192 byte: 501.516 su 581.564 (la 0.32.1: 499.324). La RAM fissa cresce di 288 byte:
85.280 su 98.304 (la 0.32.1: 84.992): è quello che ogni traccia ricorda del passo deciso in anticipo. Lo spazio
grande, dove sta il progetto, non cambia: 341.980 su 344.064 byte.
