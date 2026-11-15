# SAGGA SEQ 0.20.2 - Installazione

Cambia solo l'installazione del hub (`RELEASE-NOTES-0.20.2.md`). L'FM-1 resta alla 0.20.

## Se l'installazione della 0.20.1 si è fermata su `Read-only file system`

I file nuovi erano già tutti copiati: si era fermata solo dopo, sui servizi, che non sono cambiati.

1. Nella sessione SSH ancora aperta: `sudo reboot`.
2. Dopo un minuto ricollegati al WiFi del Pi e apri `http://192.168.4.1:8090`: in alto c'è `SAGGA HUB 0.20.1`.
3. In **AGGIORNA IL PI** scegli `sagga-hub-0.20.2.zip` e premi **Aggiorna il Pi**. Il log finisce con `exit 0` e in
   alto compare `SAGGA HUB 0.20.2`. Alla fine il WiFi del Pi può sparire per qualche secondo: se il PC non si
   ricollega da solo, ricollegalo tu.

## Da PowerShell o Termux, se preferisci

```sh
scp sagga-hub-0.20.2.zip user@192.168.4.1:/tmp/
ssh user@192.168.4.1
cd /tmp && unzip -o sagga-hub-0.20.2.zip && cd sagga-hub-0.20.2
sudo sh install_hub.sh --no-pc
```

Se il WiFi cade durante l'installazione, lei va avanti. Riconnettiti, `ssh user@192.168.4.1` e
`cat /run/sagga-install.log`: l'ultima riga è `SAGGA_INSTALL_EXIT=0` quando ha finito bene.
