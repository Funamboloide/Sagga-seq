# SAGGA SEQ 0.20.7 - Note di rilascio

**Cambia solo l'FM-1.** Il Pi resta alla 0.20.6.

## Cosa non andava

Con la 0.20.6 l'FM-1 rimandava QUANTISE alla pagina SAGGA Remote sul canale 12 CC 34, ma solo con REMOTE 13 + 14 (SAVE +
K2). Con REMOTE 14, l'impostazione di partenza dell'FM-1 (solo SAGGA Remote), non lo mandava mai: la pagina comandava
l'FM-1, ma non lo seguiva.

## Cosa cambia

QUANTISE torna alla pagina con REMOTE 14 e con REMOTE 13 + 14. Gli altri tre (SWING della pagina Live, il pattern della
traccia 6, la lane 1) sono delle pagine sui canali 12 e 13 e restano con REMOTE 13 + 14.

Provato nel simulatore con REMOTE 14 e con REMOTE 13 + 14: QUANTISE girato sul pannello (PERF, K4) torna sul canale 12
CC 34; con REMOTE 14 sul canale 12 non va nient'altro.

## Installare

FM-1 fermo, collegato al Pi: sulla pagina del Pi, **FIRMWARE**, carica `sagga-0.20.7.fwsc`, **Installa**. Dopo il
riavvio lo schermo dice `SAGGA SEQ 0.20.7`. Poi tocca una cella qualsiasi della pagina SAGGA Remote (l'FM-1 manda i
valori al hub solo dopo che una pagina gli ha parlato) e gira QUANTISE sull'FM-1 (PERF, K4): la pagina lo segue.
