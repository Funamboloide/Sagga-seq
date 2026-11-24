CARAMELLO per norns (shield XL compreso)
=======================================
Autotune da pulitissimo a hyperpop / 100 gecs. Traduzione del patch "autotune" per Ksoloti Gills.
Rilevamento del pitch (Pitch di SuperCollider) + pitch shift PSOLA con formanti indipendenti.

INSTALLAZIONE
 1. Copia la cartella "caramello" in ~/dust/code/ (via SMB "dust", sftp o Maiden).
 2. SYSTEM > RESTART (serve perche' l'engine SuperCollider e' nuovo).
 3. SELECT > caramello.
 Lo script spegne il monitor diretto di norns, il riverbero e il compressore di sistema
 (il dry passa gia' dentro l'engine) e li rimette come prima quando cambi script.
 Se apri MIX e alzi "monitor" mentre gira senti la voce raddoppiata.

INGRESSI
 Gli ingressi dello shield XL sono di linea: per un microfono serve un preamp
 (o la mandata di un canale del mixer).
 PARAMETERS > INGRESSO / USCITA > ingresso:
   mono L           una voce nel jack IN sinistro
   L+R              una voce, somma dei due ingressi
   stereo (2 voci)  due cantanti indipendenti: IN L -> OUT L, IN R -> OUT R
 uscita: stereo (default) / mono (L+R su tutte e due le uscite; con 2 voci: A + B)
 latenza: live (default) / studio (granuli piu' vecchi di 16 ms, piu' morbido)

CONTROLLI
 E1 pagina   E2 / E3 i due valori della pagina   K1 tenuto (un attimo) = i due valori sotto
   1 TUNE     RETUNE  AMOUNT    | K1: KEY (tonalita')  SCALE
   2 PITCH    PITCH   FORMANT   | K1: FINE  VIBRATO
   3 SUGAR    SUGAR   DRIVE     | K1: WIDTH  TONE
   4 HARMONY  HARMONY TIPO      | K1: CRUSH  GATE
   5 SPACE    SPACE   MIX       | K1: SIZE  OUTPUT (meta' = unity)
 K2 FREEZE (tocco = on/off, tenuto = finche' premi)     K3 BYPASS
 K1+K2 NIGHTCORE (le formanti seguono il pitch)         K1+K3 note MIDI on/off
 K1 da solo con un tocco breve apre il menu di norns (normale su norns): per la seconda
 riga tienilo premuto un attimo, poi gira o premi.
 Tutti i parametri sono anche in PARAMETERS e si possono mappare a CC con PARAMETERS > MAP.

 Scale: CHROMATIC MAJOR MINOR MAJ-PENTA MIN-PENTA BLUES HARM-MINOR DORIAN MIXOLYDIAN
 Armonie: OTTAVA SU, OTTAVA GIU, QUINTA SU, QUINTA GIU, QUARTA SU, TERZA SU, TERZA GIU,
   SESTA SU, POWER (5a+8a), TRIADE, TRIADE+8a, GECS STACK (8a sotto, 5a, 8a sopra),
   OTTAVE (sotto+sopra), SUS (4a+5a). Terze, seste e triadi seguono la scala.
 RICETTE (PARAMETERS > RICETTE, scegli e "carica la ricetta"):
   pulito naturale, hard tune, caramello gecs, nightcore, robot

SCHERMO
 riga 1  tonalita', scala e flag (BYP FRZ NC MIDI H0 CLIP = ingresso troppo alto)
 riga 2  nota cantata e cent dal target  > nota in uscita
 riga 3  accordatore (tacca al centro = intonato, piena entro 15 cent)
 sotto   pagina e i due valori
 Con 2 voci: A e B affiancati, due accordatori.

MIDI  (PARAMETERS > MIDI: porta e canale, omni o 1-16)
 Note tenute: l'ultima diventa la nota da cantare (nell'ottava piu' vicina alla voce),
 le altre dell'accordo diventano le armonie. Con 2 voci cantano tutte e due la nota tenuta.
 CC64 (sustain) FREEZE finche' premi   CC80 BYPASS   CC81 ARMONIE OFF   (>= 64 = on)
 PROGRAM CHANGE = tonalita' + scala:  PC = 12 x scala + tonalita'
   0-11 MAJOR  12-23 MINOR  24-35 CHROMATIC  36-47 MAJ-PENTA  48-59 MIN-PENTA
   60-71 BLUES  72-83 HARM-MINOR  84-95 DORIAN  96-107 MIXOLYDIAN
   es. PC 0 = C maggiore, PC 7 = G maggiore, PC 21 = A minore
   (se il controller conta da 1 a 128 aggiungi 1)

LIVE
 Latenza in live: circa 1-2 periodi della nota cantata (circa 3 ms sul La4, 7 ms sul La3)
 piu' la latenza audio di norns (alcuni millisecondi). In live il dry non e' allineato al
 wet: tieni MIX al 100%.
 Salva il tuo setup con PARAMETERS > PSET: all'avvio lo script ricarica l'ultimo PSET.
 All'accensione norns riapre da solo l'ultimo script usato.

DIFFERENZE DAL GILLS
 - Rilevamento: Pitch di SuperCollider al posto di YIN. Le marche PSOLA sono agganciate
   alla forma d'onda (passaggi per lo zero della fondamentale), come nel Gills.
 - Niente LED: lo stato e' sull'OLED. Niente soft takeover: gli encoder sono relativi.
 - Pitch fino a +-24 semitoni (sul Gills +-12).

STATO DEL LAVORO
 Non provato su norns ne' dentro SuperCollider (qui non avevo ne' l'uno ne' l'altro).
 Controllato: la parte Lua gira su una simulazione delle API di norns (pagine, tasti, MIDI,
 PSET, schermo); l'engine passa un controllo statico contro la libreria di SuperCollider;
 l'algoritmo dell'engine (marche, scelta dei granuli, GrainBuf) e' stato rifatto in Python
 su un cantante sintetico: hard tune 95.6% dei frame entro 5 cent (mediana 0.7 cent),
 ottava su/giu', formanti, nightcore e doppie entro 1-2 cent di mediana, nessuna lettura
 oltre l'ingresso. Al primo avvio guarda Maiden: se l'engine non compila l'errore e' li'.
