MICROCOSMO per norns (shield XL compreso)
========================================
Granulare / micro-loop / glitch / multidelay in stile Hologram Microcosm. Traduzione del
patch "microcosm" per Ksoloti Gills: 11 effetti x 4 varianti, HOLD, filtro, SPACE
(riverbero 4 modi), looper di frase da 60 s con overdub, undo, reverse e velocita'.

INSTALLAZIONE
 1. Copia la cartella "microcosmo" in ~/dust/code/
 2. SYSTEM > RESTART (l'engine SuperCollider e' nuovo)
 3. SELECT > microcosmo
 Lo script spegne monitor diretto, riverbero e compressore di norns e li rimette come
 prima quando cambi script. Usa circa 55 MB di RAM (non in tempo reale) per storia, delay e looper.

CONTROLLI
 E1 preset (44, nell'ordine del pedale: MOSAIC SEQ GLIDE | BLOCKS INTERRUPT ARP |
    HAZE TUNNEL STRUM | PATTERN WARP)     K1+E1 pagina
 E2 / E3 i due valori della pagina         K1 tenuto (un attimo) = i due valori sotto
   1 SOUND        ACTIVITY  REPEATS       | K1: MOD DEPTH  MOD RATE
   2 COLORE       SHAPE     FILTER        | K1: RESONANCE  REVERB plate (A room, B dark, C hall, D ambient)
   3 MIX          MIX       SPACE         | K1: FX VOLUME (meta' = unity)  LOOPER ONLY
   4 TIME / LOOP  TIME      LOOP LEVEL    | K1: LOOP SPEED  LOOP FADE (5 ms - 10 s)
   5 OPZIONI      REVERSE FX  LOOPER PRE/POST | K1: TIME MODE (SUBDIV/TEMPO)  HOLD toggle/momentaneo
   6 LOOPER       LOOP REV  FADE (in+out, solo in, solo out) | K1: QUANTIZE  BURST
 K2     HOLD (freeze dell'effetto). Non funziona mentre il looper registra o suona:
        far partire il looper lo spegne (come sul pedale). Con il loop in STOP torna.
 K3     LOOP REC > PLAY > DUB        tenuto 1 s: UNDO dell'overdub
        con BURST: loop a strato unico, registra finche' tieni premuto e suona quando
        lasci; se c'e' gia' un loop premere lo cancella e ne registra subito uno nuovo
 K1+K2  TAP TEMPO                    tenuto 1 s: BYPASS con code
 K1+K3  LOOP STOP / PLAY             tenuto 1 s: ERASE
 K1 da solo con un tocco breve apre il menu di norns: per i comandi K1+ tienilo un attimo.
 Tutto e' anche in PARAMETERS (e mappabile a CC con PARAMETERS > MAP).

 REVERSE FX: grani e loop dell'effetto suonano al contrario (anche il loro inviluppo);
   se un grano non e' ancora registrato tutto viene preso un po' piu' indietro nel tempo.
   PATTERN e WARP diventano reverse delay (pezzi lunghi quanto il ritardo). Il looper ha
   il suo reverse separato (LOOP REV).
 QUANTIZE: l'inizio della registrazione riallinea la griglia ritmica dell'effetto; alla
   chiusura la durata va alla semiminima piu' vicina; se arrotonda per eccesso continua a
   registrare fino a li' (lo schermo dice ancora REC).
 FADE: dove agisce LOOP FADE (in = ripartenza da STOP, out = STOP); altrove 5 ms.
 LOOPER ONLY: gli effetti tacciono; modulazione di pitch (MOD DEPTH/RATE), FILTER, MIX e
   SPACE restano attivi sul segnale.
 INTERRUPT: con MIX al 100% il dry sparisce del tutto (tra un glitch e l'altro silenzio).
 ACTIVITY = densita'/complessita', REPEATS = durata/frequenza/feedback.
 SHAPE ha quattro posizioni come sul pedale: SQUARE piatto, RAMP sale (swell), TRIANGLE
   sale e scende, SAW attacco e discesa (pluck). E' la forma di ogni grano o di ogni giro
   di un micro loop; con RAMP, TRIANGLE e SAW muove anche un passa-basso leggero (aperto
   in cima, piu' scuro dove il volume e' basso).
   GLIDE: e' la figura del glissato (scivola-si ferma-torna, sale, sale e scende, scende).
   TUNNEL: il micro loop dura 1/32 del tempo (20-250 ms), SHAPE da' la forma a ogni giro.
   PATTERN e WARP: e' il profilo di volume dei tap (leggera discesa, crescendo, centrali davanti,
   calando). HAZE: con TRIANGLE i grani hanno la campana di Hann.
 Dal manuale e dal tutorial (revisione 2): SEQ B rimbalza tra velocita' normale e meta' e
   ACTIVITY decide ogni quanto (battuta ... sedicesimo); SEQ C: ACTIVITY aggiunge strati (1-3);
   GLIDE con SQUARE scivola e si ferma invece di saltare; GLIDE B scende dal doppio alla meta';
   HAZE A: campioni "stirati", i grani
   ripercorrono gli ultimi istanti a meta' velocita'. Multidelay: con SQUARE i tap calano un poco
   uno dopo l'altro (un delay normale) e il primo tap esce a destra, come nel tutorial.
 FILTER tutto aperto = bypass, tutto chiuso = effetto muto.
 TIME in SUBDIV: 1/4, 1/2, TAP, 2x, 4x, 8x del tempo; in TEMPO: 40-240 BPM.

EFFETTI
 MICRO LOOP: MOSAIC, SEQ, GLIDE      GLITCH: BLOCKS, INTERRUPT, ARP
 GRANULES: HAZE, TUNNEL, STRUM       MULTIDELAY: PATTERN, WARP

SCHERMO
 riga 1 preset e famiglia (o BYPASS, LOOP ONLY, REVERSE)   riga 2 tempo, CLK se il clock e' MIDI, SUBDIV/TEMPO
 righe 3-5 pagina e valori             riga 6 AUX/INS, looper PRE/PST, stato, durata,
                                       H = hold, R = reverse, CLIP = ingresso troppo alto

INGRESSO / ROUTING (PARAMETERS > INGRESSO / USCITA)
 ingresso mono L (default) / stereo / L+R      uscita stereo / mono
 routing  insert (default): MIX e' un vero dry/wet: a zero solo dry, a meta' dry ed effetto
          pieni, a 100 solo effetto. Per un bus (mandata e ritorno) tieni MIX a 100.
          aux: solo per mandata e ritorno: il dry diretto non esce mai, MIX e' il livello del
          ritorno e a MIX 0 il dry entra solo nel riverbero SPACE. INTERRUPT in aux aggiunge
          solo i glitch. Era il default fino alla revisione 2.
 Aux bilanciato (TRS) in un ingresso stereo: sul destro arriva il segnale invertito,
 quindi usa ingresso = mono L.
 BYPASS CON CODE: l'ingresso dell'effetto si chiude in 10 ms, code, ripetizioni e riverbero
 sfumano. Il dry resta dove lo mette MIX (pieno fino a meta', niente a 100: su un bus il
 bypass e' silenzio). In aux non esce altro. HOLD continua a suonare.

TEMPO E CLOCK
 Da dove arriva il tempo (PARAMETERS > CLOCK > source):
   midi  clock MIDI dalla porta TRS dello shield o da una porta USB. "midi clock in"
         = all (tutte) oppure la sola porta che vuoi; sullo schermo CLK.
   link  Ableton Link sulla rete: cavo Ethernet del Raspberry Pi (o Wi-Fi) nella stessa
         rete del computer o delle app con Link. Sullo schermo LINK e il numero di peer
         collegati (LINK0 = nessuno: controlla cavo e rete). Per START e STOP accendi
         "link start/stop sync" su norns e nel DAW; "link quantum" = battiti per battuta.
   Il TAP non cambia mai il tempo di un clock esterno (ne' quello della sessione Link).
 Il tempo segue il clock e la griglia ritmica (SEQ, STRUM, INTERRUPT, ARP) si riallinea a ogni
 battuta (con Link sulla battuta della sessione, insieme agli altri peer); START
 riparte dal battere. In SUBDIV il pot TIME sceglie la suddivisione; in TEMPO comanda il
 pot finche' non fai TAP o arriva START. Con il clock interno il TAP cambia il tempo di norns.

MIDI  (PARAMETERS > MIDI: porta e canale, omni o 1-16)
 CC DA PALCO (valore >= 64 = on)
 CC64 HOLD (sustain: finche' premi)   CC80 BYPASS con code (pedale in toggle)
 CC81 LOOP REC > PLAY > DUB   CC83 LOOP STOP/PLAY   CC84 LOOP ERASE   CC82 TAP
      (con BURST: CC81 127 = premi, 0 = lasci)
 CC85 REVERSE FX (>= 64 on, < 64 off)   CC86 UNDO
 CC DEL PEDALE (stessi numeri del Microcosm; convivono con quelli sopra)
 Manopole 0-127: CC6 ACTIVITY, CC8 FILTER, CC9 MIX, CC11 REPEATS, CC12 SPACE, CC13 LOOP
   LEVEL, CC14 MOD RATE, CC15 RESONANCE, CC16 FX VOLUME, CC17 e CC18 LOOP SPEED, CC19 MOD
   DEPTH, CC21 LOOP FADE
 CC5 suddivisione 0-5 (1/4, 1/2, TAP, 2x, 4x, 8x)   CC10 TIME = tempo 40-240 BPM (solo
   con il clock interno)
 CC7 SHAPE: 0-31 SQUARE, 32-63 RAMP, 64-95 TRIANGLE, 96-127 SAW
 CC20 REVERB: quattro fasce, A B C D
 CC23 loop reverse, CC24 looper PRE, CC25 looper only, CC26 burst, CC27 quantize (>= 64 on)
 CC28 record (su un loop esistente ne parte uno nuovo), CC29 play, CC30 overdub, CC31 stop,
   CC34 erase, CC35 undo
 CC47 REVERSE FX, CC48 HOLD (>= 64 on)   CC93 TAP   CC102 0-63 BYPASS, 64-127 attivo
 Attenzione: CC7 e CC10 sono anche volume e pan di tastiere e DAW: usa un canale dedicato.
 PROGRAM CHANGE come nella tabella del pedale:
   1-4 ARP  5-8 INTERRUPT  9-12 BLOCKS  13-16 GLIDE  17-20 SEQ  21-24 MOSAIC
   25-28 HAZE  29-32 TUNNEL  33-36 STRUM  37-40 PATTERN  41-44 WARP
   es. 26 = HAZE B. 0 e 45-60 (preset utente del pedale) non fanno nulla. Se il tuo
   controller manda un numero in meno, aggiungi 1. (Prima erano 0-43 in un altro ordine.)
 Salva le impostazioni con PARAMETERS > PSET: all'avvio torna l'ultimo PSET.

COME FUNZIONA (e differenze dal Gills)
 - L'engine scrive sempre gli ultimi 10.9 s dell'ingresso; le "voci" ne suonano dei pezzi.
   Il sequencer che decide quando e cosa suonare gira in sclang ogni 64 campioni e ogni voce
   parte con un pacchetto a tempo: il ritmo e' preciso al campione, con 30 ms di anticipo
   fisso (le voci suonano comunque audio gia' passato).
 - Looper in PRE fx: l'overdub registra solo l'ingresso (ora anche sul Gills).
 - MOD DEPTH agisce anche sulle voci gia' partite.

ALGORITMI DALLA COMUNITA' (open source, licenza MIT, riscritti per questo engine)
 - SPACE: plate "figure eight" di Griesinger/Dattorro come nel riverbero di Mutable
   Instruments Rings (c) 2014 Emilie Gillet. Modi dal piu' corto al piu' lungo: A 0.8 s,
   B 1.8 s (scuro), C 4.2 s, D 12 s. Stesse misure del Gills.
 - ECO DI SPACE (nostra lettura del manuale: SPACE "mescola riverbero e delay"): un
   ping-pong accanto al plate, che finisce anche dentro il plate. Tempi per modo: A 3/32
   e 1/16, B 1/8 e 3/16 (scuro), C 3/16 e 1/4, D 3/8 e 1/2, piegati di un'ottava se
   uscirebbero da 30 ms - 1.3 s. Seguono il tempo di norns; PARAMETERS > SUONO >
   space echo = libero li tiene come a 120 BPM, spento toglie l'eco (solo riverbero,
   allo stesso volume). SPACE suona forte come prima.
 - HAZE: la campana di Hann dei grani (SHAPE = TRIANGLE) viene dalle finestre dei grani
   di Mutable Instruments Clouds.

STATO DEL LAVORO
 Non provato su norns ne' dentro SuperCollider. Controllato: lo script Lua gira su una
 simulazione delle API di norns (preset, pagine, tasti con tenuto, looper, tap, clock,
 MIDI, PSET, schermo); l'engine passa un controllo statico contro la libreria di
 SuperCollider (classi, metodi, argomenti, precedenze, controlli dei SynthDef). Al primo
 avvio guarda Maiden: se l'engine non compila, l'errore e' li'. Se il sequencer incontra un
 errore lo scrive in Maiden ("Microcosmo scheduler: ...") e continua.
