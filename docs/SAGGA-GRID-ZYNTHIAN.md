# SAGGA sullo Zynthian: il palco minimale

Quattro cose: **FM-1**, i **due Launchpad**, lo **Zynthian** (suoni, bus, mix, master) e il **mixer**. Lo Zynthian fa anche
quello che sul tavolo grande fa RaspiMIDIHub: riceve l'FM-1, manda le note alle sue catene, e fa girare il bridge dei
Launchpad. Niente matrice MIDI, niente tablet: il profilo **PALCO** della 0.9 sull'FM-1 e il grid bastano.

Questo foglio è scritto prima di averlo provato su uno Zynthian vero: i punti segnati **(da verificare)** sono quelli
in cui la prima prova può chiedere un ritocco.

## 1. Il principio

L'FM-1 con **USB PORTS 2** (pagina USB: HOME + SEL, K1 su 2, OCT+ due volte) si presenta come due porte MIDI:

* **porta 1** (`Felucca MIDI 1`): le 16 tracce sui canali 1-16, il clock, il transport. Va alle catene dello Zynthian:
  ogni catena ascolta il suo canale MIDI;
* **porta 2** (`Felucca MIDI 2`): il grid, il remote, i SysEx. La prende il bridge, e lo Zynthian deve ignorarla.

I due Launchpad parlano **solo** con il bridge: anche loro vanno tolti dagli ingressi dello Zynthian, altrimenti i
loro pad diventano note nelle catene.

## 2. Il bridge sullo Zynthian

Da SSH (`root` / `opensynth`, oppure il terminale della webconf). Zynthian ha il filesystem scrivibile: niente `rw` e
`ro`.

```sh
apt update && apt install -y python3-mido python3-rtmidi
mkdir -p /zynthian/sagga/projects
# dallo zip sagga-0.9-pi (copiato prima in /tmp con scp):
cp /tmp/sagga-0.9-pi/sagga_grid_bridge.py /zynthian/sagga/
cp /tmp/sagga-0.9-pi/patches.example.json /zynthian/sagga/patches.json     # facoltativo: le patch degli snapshot
cp /tmp/sagga-0.9-pi/sagga-grid-bridge-zynthian.service /etc/systemd/system/sagga-grid-bridge.service
systemctl daemon-reload
systemctl enable --now sagga-grid-bridge
journalctl -u sagga-grid-bridge -e
```

Nel log devi vedere le porte dei due Launchpad, `Felucca MIDI 2` e `bridge running`. Se le due metà sono invertite,
`--swap` in fondo alla riga `ExecStart=` del servizio, poi `systemctl daemon-reload && systemctl restart sagga-grid-bridge`.

**(da verificare)** Il bridge apre le porte con ALSA (`mido` + `rtmidi`). Lo Zynthian le apre a sua volta per il suo
router MIDI; ALSA accetta più client sulla stessa porta, quindi devono convivere. Se il bridge dice che una porta è
occupata, dimmelo: si passa il bridge su JACK (`--backend` è una riga nel sorgente) e la cosa si chiude lì.

I progetti esportati finiscono in `/zynthian/sagga/projects` (la libreria del grid, vista LIB, li vede lì). Per
tenerli al sicuro: `scp root@zynthian.local:/zynthian/sagga/projects/*.sgq .` dal PC.

## 3. Cosa dire allo Zynthian

1. **Ingressi MIDI da ignorare**: nella lista dei dispositivi MIDI dello Zynthian (webconf → Interface → MIDI, oppure
   dall'interfaccia: Admin → MIDI options → MIDI input devices, a seconda della versione **(da verificare)** dove sta
   nella tua) togli la spunta a `Launchpad Mini` (tutti e due) e a `Felucca MIDI 2`. Resta `Felucca MIDI 1`.
2. **Clock**: Zynthian "MIDI clock in" da `Felucca MIDI 1`, così gli effetti a tempo (delay, LFO) seguono il tempo
   dell'FM-1. L'FM-1 resta master (HOME + PLAY: CLOCK MASTER).
3. **Una catena per traccia**: catena 1 ascolta il canale 1, catena 2 il canale 2, e così via. Sedici catene non ti
   servono: sei-otto sono già un set (cassa, rullante, hat, perc, basso, accordi, arp, pad). Le tracce dell'FM-1
   oltre quelle restano libere per i synth esterni, quando ci sono.
4. **Program Change per scena**: le catene dello Zynthian rispondono ai PC se nelle opzioni della catena il
   "Program change" è attivo: con HOME pagina 4 K4 ogni scena del SAGGA cambia preset sullo Zynthian.
5. I bus (NY sul kick + basso, sidechain, DUB, master) come nel foglio dello Zynthian: non cambia niente.

## 4. Il regista (facoltativo, dopo)

Il regista della 0.9 è un programma Python che parla con l'FM-1 via SysEx 50-55 sulla porta 2: sullo Zynthian gira
nello stesso posto del bridge (`import sagga_grid_bridge`, classe `Regista`). Non serve per suonare: è il passo dopo.

## 5. Sul palco

Ordine di accensione: Zynthian (da solo, aspetta lo schermo), poi i Launchpad e l'FM-1 (anche già attaccati: il
bridge li aspetta e riparte da solo), per ultimo il mixer e le casse. Sull'FM-1: SAVE + K4 su **PALCO** una volta
per tutte, resta nelle impostazioni. Da lì: SEL + PLAY per il seme, un tap sul bianco 1, e si parte.
