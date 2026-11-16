# SAGGA SEQ 0.20.4 - Note di rilascio

**Cambia solo il Pi**: l'esploratore del banco. Il firmware dell'FM-1 resta la 0.20.3.

## Cosa non andava

La prova fermava il bridge del grid prima di chiedere il permesso all'FM-1. Senza il bridge l'FM-1 lascia andare il
grid e scrive `GRID DETACHED`: quella scritta copriva la domanda `PC TEST? SEL = YES`. Sull'FM-1 non si vedeva che
bisognava premere SEL, dopo 20 secondi l'FM-1 rispondeva "nessuna risposta" e la prova finiva lì (il banco e l'FM-1
completo, tutti e due).

## Cosa cambia

* **Il bridge si ferma solo dopo il sì.** Mentre l'FM-1 chiede, il grid resta attaccato e sullo schermo c'è la
  domanda. Dopo il sì l'FM-1 scrive `GRID DETACHED` per un attimo: è giusto, si riavvia nel test subito dopo.
* **Se nessuno risponde, la domanda torna**: fino a tre volte (un minuto in tutto). Il log lo dice.
* Se alla fine nessuno ha detto sì, il bridge e la matrice restano come erano (prima il bridge veniva fermato e
  riacceso per niente).

Provato con l'FM-1 finto: la domanda fatta con il bridge ancora acceso, la seconda domanda quando nessuno ha
risposto alla prima, e nessuna prova (né bridge fermato né celle staccate) dopo tre domande senza risposta.
