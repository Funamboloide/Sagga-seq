# SAGGA SEQ 0.20.2 - Note di rilascio

**Cambia solo il Pi**, di nuovo: l'installazione del hub (`install_hub.sh`). Il firmware dell'FM-1 resta la 0.20.

## Cosa non andava

A metà installazione lo script riavviava RaspiMIDIHub, per caricare le pagine SAGGA nuove. Ripartendo, RaspiMIDIHub
rimette in sola lettura il disco del Pi: le righe dopo non potevano più scrivere (`install: cannot remove
'/etc/systemd/system/sagga-fw.service': Read-only file system`) e lo script si fermava. Il riavvio può anche far
cadere per qualche secondo il suo WiFi, e con il WiFi cadeva la sessione SSH.

## Cosa cambia

* **RaspiMIDIHub si riavvia per ultimo**, dopo che tutto è scritto e il disco è tornato in sola lettura.
* **Prima di scrivere i servizi lo script rende di nuovo scrivibile il disco**, se qualcos'altro l'ha richiuso.
* **L'installazione va avanti anche se il WiFi cade.** `sudo sh install_hub.sh --no-pc` parte in un servizio a parte
  e il terminale segue solo il suo registro. Se la connessione salta, l'installazione finisce lo stesso: riconnettiti
  e leggi `/run/sagga-install.log` (l'ultima riga dice `SAGGA_INSTALL_EXIT=0` se è andata).
* **La pagina del Pi** (AGGIORNA IL PI) lo lancia nello stesso modo.

Provato sul computer con systemctl, mount e systemd-run finti: un'installazione completa, una con la sessione uccisa a
metà (finisce lo stesso), una che fallisce (il codice d'errore torna indietro).
