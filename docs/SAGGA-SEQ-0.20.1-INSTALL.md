# SAGGA SEQ 0.20.1 - Installazione

Cambia solo il Pi: **Elimina** per i firmware della libreria e **AGGIORNA IL PI**, gli zip del hub caricati dalla
pagina (`RELEASE-NOTES-0.20.1.md`). L'FM-1 resta alla 0.20: non serve reinstallarlo.

## 1. L'ultima volta da Termux

Come per la 0.20 (`docs/SAGGA-SEQ-0.20-INSTALL.md`): il tablet sulla rete `RaspiMIDIHub-XXXX`, e in Termux

```sh
scp ~/storage/downloads/sagga-hub-0.20.1.zip user@192.168.4.1:/tmp/
ssh user@192.168.4.1
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.20.1.zip && cd sagga-hub-0.20.1
sudo sh install_hub.sh --no-pc
exit
```

## 2. Prova

1. Pagina `http://192.168.4.1:8090`: in alto c'è `SAGGA HUB 0.20.1`.
2. **Elimina** accanto a un firmware vecchio (per esempio `sagga-0.19.fwsc`), conferma: sparisce dalla lista.
3. **AGGIORNA IL PI**: scegli di nuovo `sagga-hub-0.20.1.zip` (dai Download del tablet), **Aggiorna il Pi**, conferma.
   Lo stato dice `aggiornamento 0.20.1 in corso`; la pagina sparisce per qualche secondo (`il Pi non risponde`) e
   torna con `aggiornato a 0.20.1` e il log sotto, che finisce con `exit 0`.
4. Prova uno zip sbagliato, per esempio `sagga-seq-0.20-source.zip`: la pagina dice `la cartella si chiama
   sagga-seq-0.20-source: serve sagga-hub-X` e non fa niente.

Da qui in poi: quando ti preparo un `sagga-hub-X.zip`, lo scarichi sul tablet e lo carichi da **AGGIORNA IL PI**.
Niente Termux.
