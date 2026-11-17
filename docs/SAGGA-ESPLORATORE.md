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
   tornano al hub sulla porta 2). 0.23: **cinque con i motori THEORY**: una band TECHNO; una REGGAETON
   (regole contate) con GENRE LIVE; SOURCE FREE (nessun genere) con pattern di quattro battute, ferma; una AMAPIANO con il tablet e il
   grid; una HOUSE sulle MOSSE, dove RISER, DROP e l'energia riempiono e svuotano quello che i motori hanno fatto.
2. **I gesti.** Più di 5000 (0.23: 5416 con il grid e il tablet, 2901 senza): ogni bottone da solo e tenuto con un altro; ogni manopola su ogni pagina di HOME, GLO, SEQ,
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
| MOTORI | 0.23: da fermo, un pattern fatto dai motori THEORY che non è all'ENERGIA della macchina, o di cui i motori ricordano uno stile che non esiste |

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

* **Sulla 0.23**, in una sessione delle situazioni nuove con i motori: uno **snapshot** richiamato dopo aver cambiato
  la DIREZIONE di una traccia la lasciava uno step fuori dalla battuta (3 gesti: SAVE + SEL + nero 1, HOME 2 K1, SAVE +
  nero 1). Non c'entrano i motori: succedeva in ogni situazione, dalla 0.11. Corretto; è il test
  `t023_snapshot_direction`. La regola MOTORI è stata provata rompendo apposta il servizio dei motori in una copia del
  firmware: 17 errori sulle MOSSE, zero sul firmware vero.
  Il giro completo della 0.23, a errore corretto: 73.819 gesti da soli in 22 situazioni, 8.797 coppie, 200 sessioni
  da 60 gesti, nessun errore; la suite di nuovo con AddressSanitizer e UndefinedBehaviorSanitizer, nessun errore.

* **Il banco della 0.23 sull'FM-1 vero** (26 ottobre 2026: il banco, 4 sessioni; l'FM-1 completo, 28): i motori
  THEORY sull'FM-1 fanno le stesse parti del simulatore (le otto sessioni con i motori, uguali sonda per sonda), e
  nelle 28 sessioni le note sono le stesse, 28.068. Il rapporto segnava
  cinque cose; guardate una per una, quattro erano tempo o la prova stessa: un dado dal grid preso 1 ms dopo, il
  saluto del bridge mandato dopo la fine della sessione, il tasto di un loop letto 6 ms dopo a 300 BPM, un THROW
  girato 9 ms dopo. La quinta era vera: **sei messaggi che l'FM-1 aveva mandato e il Pi non aveva sentito** (in s014
  tre tick del clock, in s015 un tick e due note-off nello stesso istante), e una di queste due sessioni il rapporto
  non la segnava nemmeno. Da lì viene la 0.23.1 del confronto: le due prove nuove sul tempo, la regola PERSI, e i
  CONTI, con cui l'FM-1 dice quello che ha mandato e la prova dopo dirà da che lato un messaggio si perde. Rifatto
  sulle stesse due raccolte: il banco 0 errori; l'FM-1 completo 2 errori, i due PERSI.

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
grid ogni 1,5 s). `--hw-tablet N` aggiunge N sessioni con il tablet e il grid; un piano con eventi MIDI vuole sull'FM-1
la versione con cui è fatto, la 0.20 o più recente (il programma di Windows lo controlla). Ogni sessione parte da un riavvio dell'FM-1 nel test: nessun progetto, nessuno slot letto
o scritto, come il simulatore appena acceso. L'FM-1 dice dove ha preso ogni evento: il suo millisecondo e il suo tick di
clock. Il confronto rifà la sessione nel simulatore con ogni evento esattamente lì (fra gli stessi due tick), quindi le
due macchine devono essere uguali sonda per sonda, anche se il PC o l'FM-1 sono arrivati in ritardo. Il rapporto
(`build/explore/RAPPORTO-HW.md`) dice:

| regola | cosa |
| --- | --- |
| SIMULATORE | l'FM-1 diverso dal simulatore, dalla sonda dove comincia: il campo, i due valori, gli ultimi gesti |
| MORTO | il firmware piantato (vettore e PC del crash), un riavvio da solo, l'FM-1 che non risponde più |
| FASE, NOTE APPESE | le stesse regole, sui dati dell'FM-1 |
| PERSI | 0.23.1: un tick, una nota o un note-off che il simulatore manda e il computer non ha sentito dall'FM-1, **uno per uno, con il momento**. Le due liste sono messe una accanto all'altra, tipo per tipo e nota per nota; un messaggio arrivato in ritardo e quello che lo raggiunge si cancellano. Fino alla 0.23 le note si contavano dai note-on e i tick con due di margine: un note-off perso non si vedeva |
| CONTI | 0.23.1, con SAGGA SEQ 0.23.1 sull'FM-1: quello che l'FM-1 **dice di aver mandato** (lo conta lui, per porta e per tipo, e tiene i conti della sua coda USB) contro quello che il computer ha sentito e quello che ha ricevuto il suo driver USB. Dice dove un messaggio si è perso: dentro l'FM-1, per strada, o nel computer |
| NOTE, CLOCK | le note e i tick che escono dall'USB contro quelli del simulatore: nessuno perso per strada (0.18: non le luci del grid sul canale 16, ne' gli interruttori degli LFO che tornano al tablet, note 100-115 sul canale 13) |
| CICLO | il ciclo principale fermo più di 60 ms |
| TEMPO | visto, non un errore: una sonda presa sul tick in cui comincia uno step (gli step soli, di uno, e di nuovo uguali entro tre sonde; con loro il pattern che una coda cambia alla fine del loop), un messaggio che su una macchina è appena scaduto, o un gesto che l'FM-1 ha letto pochi ms dopo: il confronto prova a spostare gli eventi di quel gesto di 1-15 ms e se con uno spostamento il simulatore fa la stessa cosa lo tiene e va avanti (REC e TAKE scrivono le note al millisecondo). 0.23.1, due prove in più quando quelle non bastano: i messaggi che l'FM-1 ha **sentito dalle porte** prima di quella sonda (un pad del grid, un comando di una pagina) presi 1-3 ms prima o dopo; e **un solo evento di uno dei cinque gesti prima**, fino a 20 ms dopo, perché quello che un gesto mette in moto a volte si vede solo più tardi (il tasto di un loop tenuto a cavallo di un tick a 300 BPM, un THROW che finisce di scivolare una battuta dopo). Se una prova toglie una parte delle differenze senza farne di nuove, la tiene e cerca il resto da capo |

Le note e il clock si contano solo fin dove il PC ha ascoltato (chiude le porte quando riavvia l'FM-1 per la sessione dopo).
La prima volta sull'FM-1 vero (9 novembre 2026, 0.12): 20 sessioni, 0 errori; 19 di TEMPO, uno solo di un tasto letto 2 ms dopo.

`--hw-prova` fa tutto con il simulatore al posto dell'FM-1, con il costo dello schermo acceso (gli eventi arrivano in
ritardo come sul vero): deve dire che è tutto uguale, ed è nella suite dei test.

## Il banco: l'FM-1, il Pi e il grid insieme (0.20.3)

Dal PC il tablet e il grid sono finti: il PC manda i loro messaggi come eventi del test. Il **banco** gira sul Pi e
passa per le strade vere: le sei pagine SAGGA premute dentro RaspiMIDIHub con la sua API (il comando esce dalla pagina e
arriva all'FM-1 dalla matrice), il bridge del grid vero con due Launchpad finti, il pannello e le sonde con il test
dell'FM-1. Si lancia dalla pagina del Pi (**ESPLORATORE DEL BANCO**, `tools/hub/LEGGIMI.md`).

```sh
python3 tests/sagga_explore.py --banco-piano tools/hub/banco_piano.json    # il piano (make_release lo mette nello zip)
#   ... sul Pi: la pagina del hub, Avvia la prova ...
python3 tests/sagga_explore.py --banco raccolta-banco-<data>.json         # -> build/explore/RAPPORTO-BANCO.md
```

Il piano: 20 sessioni da 40 gesti nelle situazioni con il tablet e il grid (REMOTE 13 + 14 e il grid attaccato, poi
ognuna delle situazioni dell'FM-1); un gesto su due è una cella di una pagina (ogni cella di ogni pagina almeno una
volta nel giro), gli altri il pannello e il grid. Dalla 0.20.3 l'FM-1, se il test glielo chiede, ascolta le sue porte e
dice ogni messaggio che ha sentito, dove (il millisecondo, il tick del clock, la porta): il confronto rifà la sessione
con quei messaggi negli stessi punti, come gli eventi del test. In più del rapporto dal PC:

| regola | cosa |
| --- | --- |
| MATRICE | le celle che servono (ogni pagina verso la porta 2, la porta 2 verso le pagine) e quelle che non devono esserci |
| PAGINE | un comando che il Pi ha dato a una pagina e che l'FM-1 non ha mai sentito (la cella nella matrice?); una pagina che non risponde all'API; una cella con il CC cambiato da te (visto) |
| GRID | un messaggio del bridge che l'FM-1 non ha mai sentito |
| PONTE | un pad o un bottone che il bridge ha tradotto male |
| LUCI | le luci del bridge diverse da quelle che l'FM-1 aveva mandato; da guardare: le luci ferme dell'FM-1 diverse da quelle del simulatore |
| VALORI | un valore che l'FM-1 rimanda e che la cella della pagina non segue |
| SENTITI | l'FM-1 che non ascolta (firmware vecchio), pezzi di quello che ha sentito persi per strada, messaggi da un altro dispositivo |
| CELLE | 0.20.9: le celle dell'FM-1 che RaspiMIDIHub ha perso in un riavvio (il suo salvataggio automatico mentre l'FM-1 non c'era) e che il Pi ha rimesso (visto), o che non sono tornate (errore: allora VALORI è da guardare) |

Dalla 0.20.9, a ogni riavvio dell'FM-1, il programma del Pi: controlla che le celle dell'FM-1 siano tornate e rimette
quelle che RaspiMIDIHub ha perso; se l'FM-1 non risponde per 12 secondi lo fa ritrovare all'USB (un reset della sua
porta, come staccato e riattaccato) e aspetta altri 30 secondi; scrive nel log le righe del kernel sull'USB e i contatori
dell'FM-1 (il test risponde alla DIAG: i HELLO che ha sentito dal suo avvio, le risposte non partite, quando il Pi l'ha
configurato, quanto è rimasto fermo il suo giro principale), per capire da che parte stava un FM-1 che non rispondeva; e se l'FM-1 non torna, mette il progetto che aveva in memoria nella libreria del Pi
(`prima-del-banco-<data>.sgq`). Nel confronto una sonda letta un tick di clock prima o dopo, sul confine di uno step, è
TEMPO anche quando quelle dopo cadono sul confine come lei (le sonde vengono ogni 700 ms, sei step).

Dalla stessa pagina c'è anche **l'FM-1 completo**: il piano dell'esploratore dal PC (`--hw-piano`, 24 sessioni più 4
con il tablet e il grid; make_release lo mette nello zip come `hub/fm1_piano.json`) fatto girare dal Pi con lo stesso
programma, senza Windows. La raccolta si confronta con `--banco` come quella del banco.

`--banco-prova` fa tutto con il simulatore al posto dell'FM-1 (il bridge vero, i ritardi del Pi a caso) e deve dire
che è tutto uguale; poi perde i comandi delle pagine, e un pezzo di quello che l'FM-1 ha sentito, e deve trovarli. È
nella suite dei test, con `tests/sagga_banco_tests.py` (il programma del Pi contro un FM-1 e un RaspiMIDIHub finti).

## Cosa non vede
* Il suono e lo schermo: guarda lo stato e il MIDI, non come è disegnata una pagina.
* Le cose che succedono più in là di due battute (una mossa di VIAGGIO in coda per la fine della frase).
* Se una cosa è bella: dice cosa cambia e cosa rompe una regola. Se un effetto è giusto lo decidi tu, guardando la
  mappa degli effetti.
