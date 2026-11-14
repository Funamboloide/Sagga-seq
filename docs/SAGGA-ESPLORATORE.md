# L'esploratore: il firmware provato tutto, in pochi minuti

`tests/sagga_explore.py` fa al firmware quello che faresti tu provandolo, ma ogni gesto, in ogni situazione, e senza
stancarsi. Gira sul computer, senza l'FM-1: il firmware vero (lo stesso `firmware/src/dinghy.c` che va sull'FM-1) è
compilato per il PC con il simulatore (`tests/host.c`), che va circa 400 volte più veloce del tempo vero.

```sh
python3 tests/sagga_explore.py            # tutto: circa 3 minuti e mezzo
python3 tests/sagga_explore.py --veloce   # un minuto: le situazioni e i gesti principali (è nella suite dei test)
```

Alla fine scrive `build/explore/RAPPORTO.md` (cosa non va, e come rifarlo), `build/explore/EFFETTI.md` (per ogni gesto,
cosa cambia) e `build/explore/rapporto.json`.

## Come lavora

1. **Le situazioni.** Prepara la macchina in 12 modi: vuota ferma e in play, una band TECHNO in play, una HOUSE con
   l'armonia su LOCK, una AMAPIANO ferma, una progressione USER con FOLLOW RETRIG e 3+3+2, GENRE LIVE, VIAGGIO, PERF,
   note lunghe con un loop fra due step, il grid attaccato, e (0.12) una band JUNGLE con la traccia 1 in BREAK; 0.18: **il
   tablet e il grid insieme** (REMOTE 13 + 14, il grid, la band in play), con una e con due porte USB (con due i valori
   tornano al hub sulla porta 2).
2. **I gesti.** Quasi 5000: ogni bottone da solo e tenuto con un altro; ogni manopola su ogni pagina di HOME, GLO, SEQ,
   ENV, LFO, ARP e SAVE (le pagine della 0.12), con e senza SEL, avanti, indietro, e avanti-e-indietro; ogni tasto
   della tastiera da solo e con ogni modificatore (SEQ, HOME, FX, EDIT, ARP ... e **ogni gruppo + SEL: il PICK**); i gesti
   a due step (la nota lunga, e con SEL + FX il loop); i tasti tenuti della 0.12 (REC = TAKE, SEL + GLO = viaggio off, GLO +
   SEL + OCT); **le finestre** (un tocco su HOME, SEQ, EDIT, ENV, LFO, ARP o FX, poi un tasto, una manopola o una pagina,
   poi il tocco che chiude); il MASTER; i bottoni e i 128 pad del grid in ogni vista (FOLLOW compresa); 0.18: **i comandi
   del tablet** (SAGGA Live sul canale 12, TRACK sul canale 13: ogni manopola con un paio di valori, ogni interruttore
   acceso e spento, ogni tasto), solo nelle situazioni con il tablet. Nelle sessioni di quelle situazioni pannello, tablet
   e grid sono un terzo dei gesti ciascuno.
3. **Una copia per gesto.** Il simulatore prepara la situazione una volta, poi si copia (`fork`) per ogni gesto:
   ogni copia parte dalla stessa identica macchina, fa il suo gesto e guarda tutto lo stato (ogni impostazione di ogni
   traccia, l'armonia, la tonalità, i canali, i pattern ...) subito dopo, dopo due battute e dopo lo STOP. Una copia
   che non fa niente dice cosa cambia da solo con il tempo (gli accordi che girano, i dadi di EVOLVE ...): l'effetto
   di un gesto è la differenza con lei.
4. **Le coppie.** Poi 400 coppie di gesti per situazione: il secondo misurato contro il primo da solo. Così si vede,
   per esempio, se dopo aver caricato una band sfogliare i generi cambia gli accordi.
5. **Le sessioni.** Poi 200 sessioni di 60 gesti a caso. Se una rompe una regola, l'esploratore la riprova togliendo
   un gesto alla volta finché resta solo quello che basta a farlo succedere: il rapporto dà quella sequenza corta.

## Le regole

| regola | cosa non deve succedere |
| --- | --- |
| SFOGLIARE | sfogliare (pagine, cursore, traccia, genere, parte e variazione della libreria) che cambia la musica o l'armonia |
| ARMONIA | l'armonia che cambia senza che tu la tocchi (ARP 3-6, DICE PROG; erano SEQ 4 e 8 fino alla 0.11) o carichi qualcosa di un genere |
| LOCK | con l'armonia su LOCK, qualcosa che non sia ARP 3-6 o DICE PROG che la cambia |
| CANALE | il canale MIDI di una traccia cambiato da chi non deve (BAND, un dado, una manopola qualunque) |
| NOTE SCRITTE | BAND o KIT che cambiano la nota di una traccia dove hai scritto qualcosa |
| FASE | due battute dopo un gesto, una traccia che non è dove la battuta dice |
| NOTE APPESE | dopo lo STOP, una nota accesa e mai spenta |
| CLOCK | il clock MIDI che salta (tanti tick quanti ne vuole il tempo) |
| MIDI | byte MIDI non validi |
| MORTO | il firmware che si pianta, o (con i sanitizer) un errore di memoria |
| RITORNO | una manopola girata di uno e poi indietro che non rimette la musica dov'era (da guardare) |

Le regole sono scritte in fondo al file, una funzione ciascuna, con le eccezioni volute (`HARM_OK`, `CH_OK`,
`ACCETTATI`): aggiungerne una è qualche riga. Con i sanitizer trova anche gli errori di memoria:

```sh
SAGGA_SIM_CFLAGS="-fsanitize=address,undefined -g" python3 tests/sagga_explore.py
```

## Per guardare un caso da vicino

```sh
python3 tests/sagga_explore.py --solo "TECHNO band in play" --gesto "SEQ 1 PRESETS +1" --vedi
```

stampa lo stato prima e ogni campo che il gesto cambia (dopo, dopo due battute, da fermo) e quante note sono uscite.

## Per cercare più a fondo

Le sessioni a caso sono quelle che trovano le cose rare (due o tre gesti che da soli non fanno niente). Con un altro
seme sono altre sessioni; più lunghe ne contengono di più:

```sh
python3 tests/sagga_explore.py --sessioni 2000 --lunghe 150 --seme 58
```

Quattrocento sessioni da 60 gesti girano in circa 30 secondi.

## Cosa ha trovato

* **Sulla 0.10** (`SAGGA_EXPLORE_ROOT` = un albero 0.10): in 19 secondi, `SEQ + PRESETS` che cambia il genere da cui
  vengono gli accordi, cioè il problema delle tue note; e una traccia fuori fase dopo aver cambiato direzione (FWD,
  REV) mentre suona, che nessuno aveva notato.
* **Sulla 0.11**, da soli e in coppia: tre tracce fuori fase, corrette: dopo un cambio di direzione, dopo essere
  passata da TAPE e tornata, dopo un UNDO che rimette l'inizio del loop (`t011_in_time_after`).
* **Sulla 0.11**, nelle sessioni lunghe (cose che nessun gesto da solo fa): un dado rimesso com'era dopo una lunghezza
  cambiata in battuta, o sopra una traccia in TAPE; un loop di VIAGGIO lasciato a mano (in una sessione di 47 gesti che
  non si lascia accorciare: conta quando arriva ogni gesto); STOP dentro un DJ LOOP e poi CONTINUE; una cosa cambiata
  da fermo (la direzione, un dado rimesso) e poi CONTINUE (2 gesti: HOME 2 K1, SEL + PLAY); un RELOAD di una traccia a
  cui VIAGGIO aveva cambiato il loop (3 gesti: salva, HOME 8 ALG, SEL + SAVE). Corrette tutte; ognuna è una sessione di
  `t011_explorer_sessions`, che la rifà a ogni giro dei test.

Il modo di lavorare è quello: l'esploratore trova una sequenza corta, la sequenza diventa un test, il test fallisce
sul firmware vecchio e passa su quello corretto.

## Sull'FM-1 vero

Il simulatore ha il codice dell'FM-1 ma non il suo compilatore (un errore come quello del flag DENSITY della 0.11 si
vedeva solo ottimizzando), né i suoi tempi (lo schermo che si disegna, l'USB). Per questo la 0.11 ha il **test dal PC**
(`firmware/src/sagga_test.c`): con il tuo sì (SEL sull'FM-1) il PC preme i tasti, gira le manopole e suona la tastiera
dell'FM-1 vero, e l'FM-1 gli manda tutto il suo stato, la stessa sonda del simulatore.

```sh
python3 tests/sagga_explore.py --hw-piano /mnt/c/Users/user/Downloads/sagga-esploratore    # il piano, i file per Windows
#   ... su Windows: run_hw_explore.ps1 (tools/hwtest/LEGGIMI.md): l'FM-1 fa le sessioni, il PC tiene tutto ...
python3 tests/sagga_explore.py --hw /mnt/c/Users/user/Downloads/sagga-esploratore/raccolta-<data>.json
```

Il piano sono le sessioni a caso dell'esploratore (una situazione, 60 gesti, una sonda dopo ognuno), con quello che una
mano fa sul pannello e (0.18) il MIDI che entra: i comandi del tablet e i pad e i bottoni del grid, che il PC manda come
eventi del test e l'FM-1 prende come se arrivassero dalla porta del remoto (il PC al posto del Pi; il keep-alive del
grid ogni 1,5 s). `--hw-tablet N` aggiunge N sessioni con il tablet e il grid; un piano con eventi MIDI vuole la 0.18
sull'FM-1 (il programma di Windows lo controlla). Ogni sessione parte da un riavvio dell'FM-1 nel test: nessun progetto, nessuno slot letto
o scritto, come il simulatore appena acceso. L'FM-1 dice dove ha preso ogni evento: il suo millisecondo e il suo tick di
clock. Il confronto rifà la sessione nel simulatore con ogni evento esattamente lì (fra gli stessi due tick), quindi le
due macchine devono essere uguali sonda per sonda, anche se il PC o l'FM-1 sono arrivati in ritardo. Il rapporto
(`build/explore/RAPPORTO-HW.md`) dice:

| regola | cosa |
| --- | --- |
| SIMULATORE | l'FM-1 diverso dal simulatore, dalla sonda dove comincia: il campo, i due valori, gli ultimi gesti |
| MORTO | il firmware piantato (vettore e PC del crash), un riavvio da solo, l'FM-1 che non risponde più |
| FASE, NOTE APPESE | le stesse regole, sui dati dell'FM-1 |
| NOTE, CLOCK | le note e i tick che escono dall'USB contro quelli del simulatore: nessuno perso per strada (0.18: non le luci del grid sul canale 16, ne' gli interruttori degli LFO che tornano al tablet, note 100-115 sul canale 13) |
| CICLO | il ciclo principale fermo più di 60 ms |
| TEMPO | visto, non un errore: una sonda presa sul tick in cui comincia uno step (gli step soli, di uno, e di nuovo uguali entro tre sonde; con loro il pattern che una coda cambia alla fine del loop), un messaggio che su una macchina è appena scaduto, o un gesto che l'FM-1 ha letto pochi ms dopo: il confronto prova a spostare gli eventi di quel gesto di 1-15 ms e se con uno spostamento il simulatore fa la stessa cosa lo tiene e va avanti (REC e TAKE scrivono le note al millisecondo) |

Le note e il clock si contano solo fin dove il PC ha ascoltato (chiude le porte quando riavvia l'FM-1 per la sessione dopo).
La prima volta sull'FM-1 vero (9 novembre 2026, 0.12): 20 sessioni, 0 errori; 19 di TEMPO, uno solo di un tasto letto 2 ms dopo.

`--hw-prova` fa tutto con il simulatore al posto dell'FM-1, con il costo dello schermo acceso (gli eventi arrivano in
ritardo come sul vero): deve dire che è tutto uguale, ed è nella suite dei test.

## Cosa non vede
* Il suono e lo schermo: guarda lo stato e il MIDI, non come è disegnata una pagina.
* Le cose che succedono più in là di due battute (una mossa di VIAGGIO in coda per la fine della frase).
* Se una cosa è bella: dice cosa cambia e cosa rompe una regola. Se un effetto è giusto lo decidi tu, guardando la
  mappa degli effetti.
