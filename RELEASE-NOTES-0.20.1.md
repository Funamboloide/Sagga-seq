# SAGGA SEQ 0.20.1 - Note di rilascio

**Cambia solo il Pi.** Il firmware dell'FM-1 resta la 0.20 (`sagga-0.20.fwsc`, `FM-1_970`): non serve reinstallarlo.

## La pagina del hub (porta 8090)

* **Elimina**, accanto a ogni firmware della libreria: il `.fwsc` sparisce dal Pi (la partizione di boot, che è in
  sola lettura, si apre per quel momento, come per un upload). Il firmware che l'FM-1 ha adesso non cambia; quello che
  si sta installando non si cancella.
* **AGGIORNA IL PI**: carichi uno zip `sagga-hub-X.zip`, di quelli che ti preparo io, e il Pi si installa da solo.
  * Prima lo controlla: una cartella sola `sagga-hub-X`, nessun percorso che ne esce, nessun collegamento, dentro
    `install_hub.sh` e la pagina, e la pagina nuova deve essere Python valido (una pagina rotta si porterebbe via
    anche il prossimo aggiornamento). Uno zip sbagliato (il sorgente, un firmware, uno zip rifatto a mano) viene
    rifiutato con il motivo, e non parte niente. Anche uno zip del hub più vecchio della 0.20.1: la sua pagina non
    saprebbe più aggiornarsi, e il Pi tornerebbe solo da SSH (se lo vuoi davvero, da SSH si installa ancora).
  * Poi lo apre in `/run/sagga-update` e lancia `install_hub.sh` come faresti da SSH, ma per conto suo
    (`systemd-run`): lo script riavvia la pagina stessa, e senza quello si fermerebbe a metà.
  * `--no-pc` da solo, a meno che su quel Pi la porta PC (il RP2040) sia accesa.
  * La pagina sparisce per qualche secondo e torna con la versione in alto (`SAGGA HUB 0.20.1`) e il log
    dell'installazione sotto il bottone: `aggiornato a 0.20.1`, oppure `non riuscito (exit N)` e le righe che dicono
    dove.
  * Non parte mentre l'FM-1 si sta installando (il riavvio taglierebbe la scrittura), e l'FM-1 non si installa
    mentre il Pi si aggiorna. Si riavvia anche RaspiMIDIHub: non farlo mentre suoni.
* Chi è sulla rete del Pi lo può fare, come può già installare un firmware: la password del WiFi è la chiave. I due
  bottoni nuovi mandano un'intestazione che solo la pagina del hub mette, così un modulo di un altro sito non li può
  premere.

**La prima volta** (per avere questa pagina) si passa ancora da Termux / SSH: `docs/SAGGA-SEQ-0.20.1-INSTALL.md`. Da lì
in poi gli zip del hub si caricano dalla pagina.

## Sotto il cofano

* `tools/hub/sagga_fw.py`: `check_hub_zip`, `State.start_update` / `update_status` (il log e lo stato in
  `/run/sagga-update`, letti anche dalla pagina riavviata), `State.delete_package` (con `BootWriter`),
  `/api/update` e `/api/package/delete`; `X-Sagga-Hub`, l'intestazione della pagina.
* `tools/hub/install_hub.sh`: scrive la versione (`/opt/sagga/hub/VERSION`, dal nome della cartella dello zip).
* Test (`tests/sagga_hub_tests.py`): Elimina (anche sulla partizione in sola lettura), undici zip sbagliati
  rifiutati con il motivo (anche lo zip vero della 0.20), un aggiornamento con il suo log e la pulizia, uno fallito, `systemd-run`, la porta PC,
  la pagina riavviata che sa com'è andata, e lo zip vero di `make_release.sh` che la pagina accetta.
