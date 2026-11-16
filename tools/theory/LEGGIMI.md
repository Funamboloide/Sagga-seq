# SAGGA SEQ 0.23 - gli strumenti dei motori THEORY

I motori THEORY sono **nel firmware** dalla 0.23: sull'FM-1 si accendono da SEQ pagina 8, K1 (SOURCE THEORY: le regole del genere; SOURCE FREE: le regole di nessun genere). Cosa
sono, come si usano e cosa fa ognuno è scritto in `docs/TEORIA.md`; le regole dei 21 generi contati dalla libreria in
`docs/TEORIA-GENERI.md`.

Qui ci sono gli strumenti che girano sul computer. Non servono per suonare.

| il file | cosa fa |
| --- | --- |
| `gen_rules.py` | **conta la libreria** e scrive le regole dei 21 generi che non ne hanno di scritte a mano: `firmware/src/sagga_theory_data.h` (per il firmware) e `docs/TEORIA-GENERI.md` (da leggere). `--check`: dice se i due file sono quelli che la libreria dà (lo fa la suite dei test). Se cambi la libreria, rilancialo. |
| `libdump.c` | la libreria del firmware come testo, per `gen_rules.py` (lo compila lui). |
| `sagga_theory.c` | i motori dalla riga di comando: una band o una parte come testo, nella notazione della libreria. `--rules`: tutte le tabelle. |
| `compare.py` | i motori **contro la libreria**, genere per genere e parte per parte: quanti colpi, dove cadono, quanto dista una battuta fatta dalla più vicina scritta. |
| `regole.py` | scrive in italiano le regole fatte a mano (TECHNO, HOUSE, DRUM+BASS, DUBSTEP, FREE) dentro `docs/TEORIA.md`. `--check`: come sopra. |
| `render.py` | per **ascoltare senza l'FM-1**: per uno stile e un seme fa un progetto `.sgq`, un file MIDI (General MIDI) e un testo, otto scene. |

```sh
cc -std=c11 -O2 -Ifirmware/src tools/theory/sagga_theory.c firmware/src/sagga_seq_core.c firmware/src/sagga_beats.c -o build/sagga_theory
build/sagga_theory REGGAETON 6                       # STILE SEME [VARIAZIONE QUANTO ENERGIA LUNGHEZZA] [PARTE ...]
build/sagga_theory "UK GARAGE" 1 2 60 80 64 BASS VOX # la variazione 2 al 60 %, energia 80, quattro battute
python3 tools/theory/compare.py 100 TRANCE AMAPIANO  # 100 semi, due generi
python3 tools/theory/render.py build/teoria --styles all --seeds 1
```

## I file che fa `render.py`

Una cartella per stile. Di ogni progetto tre file:

| il file | cos'è |
| --- | --- |
| `.mid` | le otto scene suonate dal simulatore, una dopo l'altra, con un marcatore a ogni scena. La batteria sul canale 10, un suono per ogni parte melodica. I suoni del General MIDI sono quelli che sono: ascolta **le note e il ritmo**. |
| `.sgq` | lo stesso progetto per l'FM-1 (0.23): PROGETTI sulla pagina del Pi, Carica, poi Manda all'FM-1. |
| `.txt` | le parti scritte come nella libreria (`X x o g . -`, le note in esadecimale), scena per scena. |

Le otto scene: 1 la band del seme a energia 60; 2 e 3 una variazione piccola (25 %) e una grande (60 %); 4 e 5 la
stessa band a energia 25 e 95; 6, 7, 8 altre tre band dello stesso stile, sulle progressioni USER 2, 3, 4.

Sull'FM-1 l'energia è quella della macchina: le scene 1, 4 e 5 lì suonano uguali, all'energia del momento. Le tre
energie sono per il file MIDI.
