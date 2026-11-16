# SAGGA SEQ 0.20 - Installazione

Nove MIDI FX nell'ordine che scegli, gli inviluppi, la MOD MATRIX, la BeatStep Pro (`RELEASE-NOTES-0.20.md`). Il formato
resta `SGQB`: slot e progetti si aprono come sono.

## 1. Il Pi (cambia: l'editor, il convertitore, i plugin)

**Dal tablet Android, sulla rete del Pi (192.168.4.1).** Serve Termux, scaricato da GitHub
(`github.com/termux/termux-app/releases`, il file che finisce con `universal.apk`), non dal Play Store.

A casa, con internet, una volta sola:

```sh
pkg update
pkg install openssh
termux-setup-storage
```

Poi il tablet sulla rete `RaspiMIDIHub-XXXX` del Pi, e in Termux:

```sh
scp ~/storage/downloads/sagga-hub-0.20.zip user@192.168.4.1:/tmp/
ssh user@192.168.4.1
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.20.zip && cd sagga-hub-0.20
sudo sh install_hub.sh --no-pc
exit
```

Lo script deve dire `sagga_sgqmid built`, `sagga_sgqjson built` e `the SAGGA pages installed in ...`. Un
`apt failed: is the Pi on the internet?` sulla rete del Pi non è un problema se le due righe `built` ci sono. (Dal PC:
gli stessi comandi da PowerShell.)

## 2. L'FM-1

FM-1 collegato al Pi e fermo, pagina `http://192.168.4.1:8090`, carica `sagga-0.20.fwsc`, **Installa**. Dopo il
riavvio lo schermo dice `SAGGA SEQ 0.20`.

## 3. Prova

1. Una traccia con i 16 step accesi (C4) su un synth, PLAY.
2. **Tocca HOME**, OCT fino a `HOME 6/8 MIDI FX`. **K1** su `GLITCH`, **K2** a 100 %, **K3** `STUTTER`. **Tocca HOME**,
   **tocca SEQ**, **bianco 6** (non sulla pagina `SEQ 2/7`): ogni step si spezza in quattro. **Tocca SEQ**.
3. Di nuovo in HOME 6: **K1** su `RANDOM`, SEQ + bianco 6: `T1 MIDI FX RANDOM STARTS: RND+GLIT`. Le note si spostano in
   chiave. Ora **K1** su `GLITCH` e **SEL + K1** a sinistra di quattro scatti: `T1 ORDER GLIT>RND`. Adesso RANDOM sposta
   anche i pezzi, ognuno per conto suo.
4. **K1** su `OFF`, SEQ + bianco 6: si fermano tutti.
5. **L'inviluppo**: **LFO + bianco 1** (l'LFO 1 acceso), pagina 1 **K1** `ENV`, **K3** DEPTH 127, **K4** CENTER 0;
   pagina 3 **K4** `T1`; pagina 5 **K2** DECAY `1/8`. Sul synth il CC 74 (il filtro) si apre a ogni nota e si richiude.
6. **La MOD MATRIX**: pagina 6, **K2** `CC IN`, **K3** `VEL T`, **K4** 100 %. **LFO + REC** e muovi una manopola di una
   tastiera sul MIDI IN: `MOD 1 SOURCE = CC ..`. Quella manopola ora decide la velocity della traccia 1.
7. **La BeatStep Pro** (se l'hai): nel hub aggiungi **SAGGA BeatStep**, la BeatStep Pro verso il suo IN, il suo OUT verso
   la porta 2 dell'FM-1, **Save Config**. Sul plugin **LEARN**, gira le 16 manopole (la riga in alto da sinistra, poi
   quella in basso), tocca i 16 pad: il contatore arriva a 32. La prima manopola ora cambia la TRACK del tablet, i pad
   sono i 16 MUTE.
8. Salva (tocca SAVE due volte), spegni e riaccendi: la catena, l'ordine, l'inviluppo e la MOD MATRIX ci sono ancora.
