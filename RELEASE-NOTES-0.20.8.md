# SAGGA SEQ 0.20.8 - Note di rilascio

**Cambia solo l'FM-1.** Il Pi resta alla 0.20.6.

## Cosa non andava

L'FM-1 rimandava i suoi valori alle pagine del hub solo dopo che una pagina gli aveva mandato un comando (da quando si
era acceso). Se dopo l'accensione giravi prima l'FM-1, SAGGA Remote non si muoveva finché non toccavi la pagina.

## Cosa cambia

Basta che dal Pi arrivi qualcosa sulla porta 2: il bridge del grid manda un segnale di vita ogni secondo (anche senza
Launchpad). Quindi le pagine seguono l'FM-1 da subito, senza toccarle prima. Con una porta USB sola non cambia niente
(non torna niente al hub, come prima).

Provato nel simulatore: finché sulla porta 2 non arriva niente l'FM-1 non manda niente; arrivato solo il segnale di
vita del bridge, QUANTISE girato sul pannello torna alla pagina senza che nessuna pagina sia stata toccata.

## Installare

FM-1 fermo, collegato al Pi: sulla pagina del Pi, **FIRMWARE**, carica `sagga-0.20.8.fwsc`, **Installa**. Dopo il
riavvio lo schermo dice `SAGGA SEQ 0.20.8`. Gira QUANTISE sull'FM-1 (PERF, K4) senza toccare prima la pagina: SAGGA
Remote lo segue.
