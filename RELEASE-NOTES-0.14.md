# SAGGA SEQ 0.14 - Note di rilascio

Due cose: un **progetto nuovo** dal pannello e l'**editor dei progetti** nel browser, sul Pi. Il formato resta `SGQB`,
la memoria dell'FM-1 non cresce: il firmware cambia di poche righe, il resto è tutto sul Pi.

## Un progetto nuovo

Scegli uno slot vuoto (SAVE + PRESETS: lo schermo dice `EMPTY`) e caricalo come gli altri, **HOME + SAVE due volte**:
la prima volta `LOAD SLOT 7 EMPTY: AGAIN = NEW PROJECT`, la seconda `NEW PROJECT: SAVE PUTS IT IN SLOT 7`. È tutto al
valore di base: tempo, tracce, chiave, scene, song, LFO. **SAVE** lo scrive in quello slot. Gli altri slot non si
toccano; RELOAD non ha niente a cui tornare finché non lo salvi.

## L'editor dei progetti (pagina 8090)

Accanto a ogni progetto della libreria c'è **editor**. Sotto la lista: **Nuovo** (un progetto vuoto con il nome che
scrivi) e **Ricevi dall'FM-1** (il progetto che l'FM-1 ha adesso, da fermo). Le schede:

| scheda | cosa |
|---|---|
| Tracce | le 16 tracce, i 64 step di un pattern; un tocco accende o spegne (con la nota PEN della traccia) o solo seleziona; sotto lo step: quattro note, velocity, gate, chance, ratchet, condizione, nudge, ramp, TIE, SLIDE, PLAIN, LOCK, le sei lane; copia, incolla, svuota |
| Traccia | tutte le impostazioni delle pagine HOME (modo, canale, ruolo, PEN, lunghezza, divisione, swing, accordi, arpeggio, MIDI FX, EUCLID, le lunghezze per parametro); copia il pattern su un'altra traccia o un altro pattern, svuotalo, ruotalo |
| Lane | i lock di una lane disegnati col dito o col mouse; il CC della lane, il valore base, lo scivolo, NRPN |
| Scene | per ogni scena: i pattern, i mute, i program change per canale, la chiave |
| Song | le voci (scena, battute, tempo); aggiungi, sposta, togli |
| Catene | OFF, P1+2 o una LISTA per traccia |
| LFO | i 16 LFO con RATE SEQ e TRIG |
| Progetto | tempo, clock, i 16 slot della chiave, QUANTISE, MORPH, le macro, CC LEAD, LIVE IN, i synth dei canali |

**Salva** riscrive il progetto nella libreria; la versione di prima resta in `versioni/` e si ripristina dalla pagina.
Se il file è cambiato nel frattempo (salvato dall'FM-1 o da un'altra pagina) il salvataggio viene rifiutato. **Manda
all'FM-1** carica il progetto sull'FM-1 fermo; SAVE sull'FM-1 lo tiene. **Annulla** o Ctrl+Z, Ctrl+S per salvare.

La pagina non costruisce mai un progetto da sola. Il Pi compila `sagga_sgqjson` dallo **stesso codice del firmware**:
legge il progetto come lo legge l'FM-1 e scrive le modifiche passando per lo stesso controllo dei valori dell'FM-1.
L'editor quindi non può fare un progetto che l'FM-1 non prende: un valore fuori misura viene rimesso a posto, e la
pagina dice quanti. Le tracce TAPE restano del piano roll; snapshot e VIAGGIO l'editor non li tocca.

Con il bridge del grid acceso, l'hub chiede a lui di mandare e ricevere, perché ha già la porta dell'FM-1 (un file in
`/run/sagga`); senza bridge usa `sagga_grid_bridge.py --export / --import`. Un progetto ricevuto entra prima in un file
a parte e prende il nome solo se si rilegge come progetto.

## Sotto il cofano

* `tools/sgqmid/sagga_sgqjson.c` (read, apply, new); `tools/hub/sagga_editor.py`, `tools/hub/editor.html`; il bridge
  ha la classe `Control` per le richieste dell'hub.
* `tests/sagga_editor_tests.py`: il convertitore (lettura, modifiche, valori corretti dal firmware, errori che non
  scrivono niente, lo step scritto che il core suona), l'editor (salvataggi, conflitti, versioni, nomi), le liste della
  pagina confrontate con quelle del pannello, l'FM-1 dentro e fuori attraverso un bridge vero con un FM-1 finto
  (occupato, un progetto rotto), la pagina in un browser senza schermo. Il simulatore prova il progetto nuovo dallo slot
  vuoto.
* Il confronto dell'esploratore con l'FM-1 ha le due regole di tempo trovate nella prima raccolta della 0.13.
