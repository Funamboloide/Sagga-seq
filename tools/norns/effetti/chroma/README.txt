CHROMA per norns (shield XL compreso)
====================================
Multieffetto in stile Hologram Chroma Console. Traduzione del patch "chroma" per Ksoloti Gills.
4 moduli in serie, 5 effetti ciascuno, ordine modificabile:
 CHARACTER : DRIVE, SWEETEN, FUZZ, HOWL, SWELL
 MOVEMENT  : DOUBLER, VIBRATO, PHASER, TREMOLO, PITCH
 DIFFUSION : CASCADE, REELS, SPACE, COLLAGE, REVERSE
 TEXTURE   : FILTER, SQUASH, CASSETTE, BROKEN, INTERFERENCE
CAPTURE (looper/sustainer 30 s), GESTURE (registra i movimenti dei controlli), TAP e clock.

INSTALLAZIONE
 1. Copia la cartella "chroma" in ~/dust/code/
 2. SYSTEM > RESTART (l'engine SuperCollider e' nuovo)
 3. SELECT > chroma
 Lo script spegne monitor diretto, riverbero e compressore di norns (il dry, se serve,
 lo gestisce l'engine) e li rimette come prima quando cambi script.

CONTROLLI
 E1 pagina   E2 / E3 valori   K1 tenuto (un attimo) = i due valori sotto
   1 CHARACTER  AMOUNT  TILT    | K1: VOL  SENS (guadagno d'ingresso, soglia di SWELL)
   2 MOVEMENT   AMOUNT  RATE    | K1: VOL  DRIFT (di MOVEMENT)
   3 DIFFUSION  AMOUNT  TIME    | K1: VOL  DRIFT (di DIFFUSION: sono due, come sul pedale)
   4 TEXTURE    AMOUNT  STYLE   | K1: VOL  (STYLE = LOW-PASS / TILT / HIGH-PASS per FILTER,
                                             nell'ordine del pedale; all'avvio LOW-PASS)
   5 PERF       MIX     OUTPUT  | K1: ORDINE della catena  CAPTURE pre/post
 Pagine modulo: K2 effetto successivo (K1+K2 precedente), K3 bypass del modulo
                (nome in minuscolo nella riga in alto).
 Pagina PERF:   K2 CAPTURE: tieni premuto per registrare, rilascia per suonare
                (meno di 1 s = SUSTAIN pad, altrimenti LOOP, 30 s al massimo).
                Mentre suona: tieni premuto = quello vecchio sfuma e registri subito
                di nuovo; un tocco breve (meno di 0.25 s) = ferma e cancella.
                K3 BYPASS con code: l'ingresso si chiude in 10 ms, code e riverberi sfumano.
                K1+K2 GESTURE: tocco = inizia/ferma la registrazione di TILT, i quattro
                AMOUNT, RATE, TIME e MIX; tenuto 1 s = cancella. Muovere un controllo
                registrato ne cancella il gesto. La velocita' del gesto segue il tempo
                (a meta' tempo va a meta' velocita').
 Da tutte le pagine: K1+K3 TAP TEMPO; tenuto 1 s = TEMPO OFF (RATE e TIME tornano liberi).
 K1 da solo con un tocco breve apre il menu di norns: per la seconda riga tienilo un attimo.
 Tutto e' anche in PARAMETERS (e mappabile a CC con PARAMETERS > MAP).

 RATE: velocita' di VIBRATO/PHASER/TREMOLO; con PITCH e' continuo da un'ottava sotto a
       un'ottava sopra (niente shift in una piccola zona attorno al centro);
       con DOUBLER da raddoppio stretto (8 ms) a slapback (128 ms).
 AMOUNT: TREMOLO da shimmer morbido a chop a onda quadra; PITCH, SPACE e REVERSE dry/wet
       (tutto aperto = 100% wet); PHASER intensita' e stadi (2-12).
 DRIFT di MOVEMENT: DOUBLER salti d'intonazione casuali e momentanei; VIBRATO, PHASER e
       TREMOLO l'onda passa da sinusoide a casuale (VIBRATO allarga i due lati); PITCH
       lo-fi (fino a 6 kHz di campionamento) e stonato.
 DRIFT di DIFFUSION: CASCADE ondeggia e le ripetizioni si consumano; REELS wow e flutter;
       SPACE chorus sulla coda; COLLAGE alcuni grani a velocita' doppia o dimezzata;
       REVERSE ondeggia l'intonazione.
 TIME: tempo di CASCADE/REELS; grana di COLLAGE (muovendola i pezzi scivolano e
       l'intonazione si piega); velocita' e intonazione di REVERSE (meta', normale al
       centro, doppia); tipo di stanza di SPACE (ROOM, HALL, CATHEDRAL, HUGE).
 TILT con DRIVE agisce anche prima della saturazione (scuro = distorcono di piu' i bassi).
 FILTER: LOW-PASS e HIGH-PASS non fanno nulla con AMOUNT a zero e filtrano di piu' salendo, come
sul pedale (il LOW-PASS a fondo corsa chiude quasi tutto). In stile TILT: a sinistra taglia gli
acuti, a destra i bassi, al centro niente. Un PSET salvato prima ha lo stile con un altro numero.

SCHERMO
 riga 1  la catena nell'ordine (DRIV>DUBL>CASC>FILT), il modulo della pagina in chiaro,
         AUX, INS o MIX a destra
 riga 2  tempo (BPM o CLK), capture (REC, LOOP, SUS), gesture, BYPASS, CLIP (ingresso alto)
 riga 3  modulo ed effetto
 sotto   i due valori della pagina

INGRESSO / ROUTING (PARAMETERS > INGRESSO / USCITA)
 ingresso: mono L (default) / stereo / L+R      uscita: stereo / mono
 routing:  mix (default)  MIX e' un vero dry/wet: a zero solo dry, a meta' dry ed effetto
             pieni, a 100 solo effetto (per un bus tieni MIX a 100). La catena da' solo la
             parte effettata: DOUBLER, PHASER, PITCH e tutta la DIFFUSION danno solo l'effetto;
             CHARACTER, TEXTURE, VIBRATO e TREMOLO lavorano su quello che ricevono. Il dry di
             MIX e' sempre il segnale pulito. Con tutti i moduli in bypass resta solo il dry.
           insert  il pedale vero, moduli in serie: il diretto attraversa doubler, delay e
             riverbero; MIX sfuma tra ingresso e catena. Per l'uso in serie.
           aux     solo mandata e ritorno: come mix, ma il dry non esce mai e MIX e' il
             livello del ritorno. Era il default fino alla revisione 2.
 Aux bilanciato (TRS) in un ingresso stereo: sul destro arriva il segnale invertito,
 quindi usa ingresso = mono L.

TEMPO E CLOCK
 Da dove arriva il tempo (PARAMETERS > CLOCK > source):
   midi  clock MIDI dalla porta TRS dello shield o da una porta USB. "midi clock in"
         = all (tutte) oppure la sola porta che vuoi; sullo schermo CLK.
   link  Ableton Link sulla rete: cavo Ethernet del Raspberry Pi (o Wi-Fi) nella stessa
         rete del computer o delle app con Link. Sullo schermo LINK e il numero di peer
         collegati (LINK0 = nessuno: controlla cavo e rete). Per START e STOP accendi
         "link start/stop sync" su norns e nel DAW; "link quantum" = battiti per battuta.
   Il TAP non cambia mai il tempo di un clock esterno (ne' quello della sessione Link).
 Quando il tempo arriva da fuori (midi, link o crow), quando arriva START o quando fai TAP,
 RATE e TIME seguono il tempo con le suddivisioni:
   TIME  1/16 1/8T 1/8 1/8. 1/4 1/4. 1/2 1/2.        (a meta' corsa = 1/4)
   RATE  4 BAR 2 BAR 1 BAR 1/2 1/4 1/8 1/8T 1/16     (a meta' corsa = 1/4)
 L'LFO di MOVEMENT si aggancia alla battuta (il TREMOLO e' al massimo sul battere,
 in poche battute e senza salti). Con il clock interno il TAP cambia il tempo di norns.
 PARAMETERS > CATENA E LIVE > rate/time per tornare liberi.

MIDI  (PARAMETERS > MIDI: porta, canale omni o 1-16, mappa MIDI)
 Lo script risponde alla tabella CC del pedale originale. Tre CC (64, 80, 82) coincidono
 con quelli "da palco": PARAMETERS > MIDI > mappa MIDI decide chi vince.
   live (default): CC64 CAPTURE, CC80 BYPASS con code, CC82 TAP (come prima)
   pedale:         CC64 TILT, CC80 GESTURE, CC82 CAPTURE (come sul pedale)
 CC DEL PEDALE
 CC64 TILT (solo mappa pedale), CC65 CHARACTER AMOUNT, CC66 RATE, CC67 MOVEMENT AMOUNT,
   CC68 TIME, CC69 DIFFUSION AMOUNT, CC70 MIX, CC71 TEXTURE AMOUNT, CC72 SENS,
   CC73/75/77/79 VOL dei quattro moduli, CC74 DRIFT di MOVEMENT, CC76 DRIFT di DIFFUSION,
   CC78 OUTPUT
 CC16/17/18/19 effetto di CHARACTER/MOVEMENT/DIFFUSION/TEXTURE: 0-21 = 1o, 22-43 = 2o,
   44-65 = 3o, 66-87 = 4o, 88-109 = 5o, 110-127 = modulo spento
 CC80 GESTURE (64-127 registra, 0-63 suona; solo mappa pedale), CC81 ferma e cancella
 CC82 CAPTURE (88-127 registra, 44-87 suona, 0-43 ferma e cancella; solo mappa pedale)
 CC83 CAPTURE PRE (>= 64)   CC84 FILTER STYLE (0-43 LOW-PASS, 44-87 TILT, 88-127 HIGH-PASS)
 CC91 0-63 BYPASS, 64-127 attivo   CC93 TAP   CC103-106 bypass dei moduli (0-63 bypass)
 CC IN PIU' (non sul pedale)
 CC20/21/22/23 effetto di CHARACTER/MOVEMENT/DIFFUSION/TEXTURE
      0-25 = 1o, 26-51 = 2o, 52-76 = 3o, 77-102 = 4o, 103-127 = 5o
 CC24/25/26/27 bypass del modulo    CC28 ordine dei moduli (0 = C>M>D>T)
 Una "scena" per brano = un preset del controller che manda questi CC insieme.
 Salva le impostazioni con PARAMETERS > PSET: all'avvio torna l'ultimo PSET.

DIFFERENZE DAL GILLS
 - PHASER senza feedback: SuperCollider senza plugin non ha il feedback di un campione
   (con il feedback a blocchi suonerebbe come un flanger). Le tacche sono le stesse.
 - PITCH usa il pitch shifter di SuperCollider (finestra di 43 ms). Sul Gills le due
   testine si danno il cambio dove il suono si ripete (note tenute piu' pulite); qui
   resta quello granulare di SuperCollider.
 - SWELL: una nota nuova sopra una che suona ancora non fa piu' "click".
 - Gli effetti a ritardo hanno lo stesso tempo e lo stesso feedback del Gills: il giro di
   feedback passa per un blocco di SuperCollider ma la lettura e' anticipata dello stesso
   tanto, quindi le ripetizioni restano esattamente a tempo.

ALGORITMI DALLA COMUNITA' (open source, licenza MIT, riscritti per questo engine)
 - SPACE: plate "figure eight" di Griesinger/Dattorro come nel riverbero di Mutable
   Instruments Rings (c) 2014 Emilie Gillet. TIME sceglie la stanza (0.5, 1.5, 3, 6, 15 s)
   e la stanza scivola senza salti; DRIFT aggiunge chorus alla coda.
 - REELS, CASSETTE, BROKEN: pezzi di nastro di Airwindows (Chris Johnson): wow e flutter
   come in Flutter/ToTape (la velocita' cambia a caso a ogni ciclo e la profondita' la
   segue: nessuna oscillazione uguale alla precedente), "soften" di ToTape (gli acuti
   forti si schiacciano), clip a seno di Tape/ToTape; in CASSETTE anche l'head bump
   (circa +3 dB intorno a 70 Hz a fondo corsa). In REELS il nastro lavora su ogni
   ripetizione. Stessi volumi di prima.

STATO DEL LAVORO
 Non provato su norns ne' dentro SuperCollider. Controllato: lo script Lua gira su una
 simulazione delle API di norns (pagine, tasti, capture, gesture, tap, clock, MIDI, PSET,
 schermo); l'engine passa un controllo statico contro la libreria di SuperCollider (classi,
 metodi, argomenti, precedenze). Al primo avvio guarda Maiden: se l'engine non compila
 l'errore e' li'.
