# SAGGA M8 LINK 0.6 - due Brick, ognuna con il suo M8, come strumenti MIDI per il Raspberry

```
M8 --USB--> Brick A (porta in ALTO) ... Brick A (USB-C in BASSO) --USB--> hub alimentato --> Raspberry Pi
M8 --USB--> Brick B (porta in ALTO) ... Brick B (USB-C in BASSO) --USB--> hub alimentato --> Raspberry Pi
```

Novità della 0.6: se esci da m8c e ci rientri, KNULLI torna a EmulationStation e stacca la porta USB della Brick:
il Pi perdeva l'M8 finché non rilanciavi il link. Ora il link la riattacca da solo entro due secondi (un cane da
guardia nel servizio; una porta che KNULLI ha dato ad altro, per esempio ADB acceso, la lascia stare). Sul Pi non
cambia niente. Per aggiornare una Brick: copia il nuovo `sagga_m8` come sotto e `knulli-services restart sagga_m8`.

Novità della 0.5: ogni Brick ha un nome, A o B. Il Pi le distingue da quello: in RaspiMIDIHub compaiono come
"SAGGA M8 A" e "SAGGA M8 B" (modo native) oppure come due schede virtuali, SAGGAM8A e SAGGAM8B (modo ffs).
Una Brick con la 0.4 senza nome vale come A.

Lo script sceglie da solo uno dei due modi:

- **native**: se il kernel della Brick ha la funzione USB-MIDI (f_midi), il Pi vede un normale strumento USB-MIDI.
  Sul Pi non serve installare niente.
- **ffs**: se il kernel non ce l'ha (con KNULLI e kernel 4.9.191 è il caso più probabile), sul Pi gira
  `sagga_m8_host.py`, che dà a ogni Brick la sua scheda MIDI virtuale.

## Su ogni Brick

Nelle impostazioni di KNULLI metti la modalità USB su off (niente ADB). Il comando dei servizi è `knulli-services`
su Scarab, `batocera-services` su Gladiator II: nei comandi qui sotto usa quello della tua versione. Dal PC, nella
cartella dello zip estratto:

```powershell
scp .\sagga-m8-link\brick\sagga_m8 .\sagga-m8-link\brick\sagga_m8_ffs.py .\sagga-m8-link\brick\sagga_m8_diag.sh root@IP-BRICK:/tmp/
ssh root@IP-BRICK
```

Sulla Brick (sulla seconda Brick scrivi `name B` invece di `name A`):

```sh
knulli-services stop sagga_m8 2>/dev/null
knulli-services disable sagga_m8 2>/dev/null
mkdir -p /userdata/system/services
cp /tmp/sagga_m8 /tmp/sagga_m8_ffs.py /tmp/sagga_m8_diag.sh /userdata/system/services/
chmod +x /userdata/system/services/sagga_m8 /userdata/system/services/sagga_m8_ffs.py
sh /userdata/system/services/sagga_m8 name A
sh /userdata/system/services/sagga_m8_diag.sh
knulli-services start sagga_m8
knulli-services status sagga_m8
knulli-services enable sagga_m8
```

`start` dice quale modo ha scelto: `native USB-MIDI` oppure `vendor link`. Se su questa Brick c'era la 0.3 di ChatGPT,
i primi due comandi la fermano e la tolgono dall'avvio; i file nuovi la sostituiscono. Con la modalità USB su off
KNULLI non crea nessun gadget USB: lo crea il link, e lo toglie quando lo fermi.

## Sul Pi (solo se almeno una Brick dice "vendor link")

Dal PC:

```powershell
scp .\sagga-m8-link\pi\sagga_m8_host.py .\sagga-m8-link\pi\sagga-m8-link.service user@IP-PI:/tmp/
ssh user@IP-PI
```

Sul Pi:

```sh
rw
sudo systemctl disable --now sagga-m8-link 2>/dev/null
sudo rm -rf /opt/sagga-m8-link
sudo apt install python3-usb
sudo mkdir -p /opt/sagga
sudo cp /tmp/sagga_m8_host.py /opt/sagga/
sudo cp /tmp/sagga-m8-link.service /etc/systemd/system/
sudo modprobe -r snd-virmidi 2>/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now sagga-m8-link
sudo systemctl restart raspimidihub
ro
python3 /opt/sagga/sagga_m8_host.py --list
journalctl -u sagga-m8-link -e
```

`--list` deve mostrare le due Brick con il loro nome e la loro scheda; il log deve dire `Brick A connected` e
`Brick B connected`. `rm -rf /opt/sagga-m8-link` toglie la 0.3 di ChatGPT dal Pi, se c'era.

Per installare `python3-usb` il Pi deve avere internet: un cavo Ethernet verso il router, oppure in RaspiMIDIHub
Settings > Connectivity > WiFi mode "WiFi for updates".

## Il cavo e la corrente

La USB-C in basso di ogni Brick va a un **hub alimentato**, non al Pi: la Brick si ricarica da quella porta. L'M8 va
nella porta in alto.

## Se una Brick non compare

- `knulli-services status sagga_m8` sulla Brick: nome, modo, M8 presente, ultime righe del log.
- "the USB port is in use by KNULLI": la modalità USB di KNULLI non è su off.
- Sul Pi "two Bricks are both called A": su una delle due `sh /userdata/system/services/sagga_m8 name B`, poi
  `knulli-services stop sagga_m8` e `knulli-services start sagga_m8`.
- Sul Pi "no virtual card SAGGAM8B": `sudo modprobe -r snd-virmidi`, poi `sudo systemctl restart sagga-m8-link`.
