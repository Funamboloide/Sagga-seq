# FIGO - rende figo il noioso (norns)

Uno script per norns (lo shieldXL va benissimo) che prende un loop dall'ingresso e lo varia **da solo, a tempo**,
mentre tu prepari altro sul sequencer. Tu giri una manopola: **FIGO**. A zero il loop passa pulito; salendo, la
macchina decide lei, battito per battito, se e come intervenire. Gli interventi cadono soprattutto dove li metterebbe
un DJ: a fine battuta e, ancora di più, a fine frase. Sul primo battito della battuta succede poco.

Ispirato alla manopola RAND del Red Panda Tensor, alla memoria del Chase Bliss Habit, al Beat Repeat di Ableton e alle
Release FX del Pioneer RMX-1000. Usa solo softcut (il registratore a nastro che norns ha già dentro): niente engine,
gira anche su un Pi 3B+.

## Installare (dal tablet, con Termux)

norns e il tablet sulla stessa rete (per esempio la rete del Pi, `RaspiMIDIHub-XXXX`). L'indirizzo di norns è in
**SYSTEM > WIFI**. In Termux, con `figo.lua` in Download:

```sh
ssh we@<ip di norns> mkdir -p /home/we/dust/code/figo
scp ~/storage/downloads/figo.lua we@<ip di norns>:/home/we/dust/code/figo/
```

La password di norns, se non l'hai cambiata, è `sleep`. Poi su norns: **SELECT > figo**. (Senza Termux: apri
`http://<ip di norns>` nel browser, è maiden; crea uno script nuovo che si chiami `figo` e incolla il file.)

## Prima di suonare

* **Il clock**: PARAMETERS > CLOCK > **source = midi**, sulla porta MIDI dove arriva SAGGA. Con START di SAGGA la
  frase riparte dal primo battito (se non combacia: PARAMETERS > **allinea: la frase parte ora**, sul primo battito).
* **Dove metterlo**: in insert su tutto il loop (il suono passa tutto da norns). Il pulito esce con circa 10 ms di
  ritardo (la latenza di softcut): non mischiarlo con il suono originale in parallelo, farebbe un effetto phaser.
* **I livelli**: FIGO spegne il monitor di norns da solo (il pulito passa da softcut) e lo rimette com'era quando
  chiudi lo script. In LEVELS il **softcut** deve essere a 0 dB.

## I comandi

| | |
| --- | --- |
| **E2 FIGO** | quanto interviene. 10-30: qualche fill a fine frase. 50: qualcosa in ogni frase. 100: sempre |
| **E3 CARATTERE** | da **dub** (ripetizioni lunghe, reverse a mezza velocità, ottava sotto, tape stop, eco lanciate) a **glitch** (1/16 e 1/32, roll che sale, sedicesimi rimescolati, gate, ottava sopra) |
| **E1 MEMORIA** | una battuta di 1, 2, 4 o 8 battute fa che torna sotto, filtrata e con i lati scambiati, o un'eco lanciata a fine frase. Funziona anche con FIGO a zero |
| **K2 HOLD** | dal prossimo battito ripete il battito appena passato; con FIGO alto lo varia da solo (più corto, al contrario, a doppia o mezza velocità). K2 di nuovo: torna il loop |
| **K3 PULITO** | sul prossimo battito esce con un tape stop (dub) o un backspin (glitch), poi solo il pulito. K3 di nuovo: riparte |

Lo schermo mostra FIGO, il cursore dub-glitch, MEMORIA, il tempo, la frase un battito per casella e, in grande,
l'intervento in corso.

**Dal controller**: ogni valore si può mappare su una manopola MIDI (PARAMETERS > MAP): per esempio FIGO su una
manopola di SAGGA Live o della BeatStep Pro.

## Gli interventi

| | cosa fa |
| --- | --- |
| 1/4, 1/8, 1/16, 1/32 | il pezzo che parte sul battito suona una volta, poi si ripete fino alla fine dell'intervento |
| ROLL | 1/4, poi 1/8, 1/16, 1/32: un build-up; con glitch alto sale anche di intonazione |
| REVERSE | gli ultimi battiti al contrario (dub: a mezza velocità) |
| OTTAVA - / OTTAVA + | il nastro a mezza velocità / l'ultimo mezzo battito a doppia velocità |
| TAPE STOP | il nastro rallenta fino a fermarsi, solo a fine battuta o a fine frase |
| SHUFFLE | i sedicesimi dell'ultima battuta, in un ordine nuovo |
| GATE | il loop tagliato a sedicesimi |
| INDIETRO | quello che suonava 1, 2 o 4 battute fa, a tempo, al posto del loop |

Un intervento dura mezzo battito, uno o due battiti e non passa mai la fine della frase: il primo battito della frase
nuova arriva pulito.

## Il menu (PARAMETERS)

FIGO, carattere e memoria (come le manopole); **frase** 8, 16 o 32 battiti; **allinea**; **uscita (K3)**: auto, tape
stop, backspin o secca; **ingresso** stereo o mono (L); **livello** del pulito; **livello memoria**; **latenza** del
pulito (8 ms; più alta se senti scatti). Le impostazioni restano per la volta dopo.

## Prove

`tools/norns/test_figo.lua` (`texlua tools/norns/test_figo.lua`) fa girare lo script con un norns finto e un modello di
softcut (le sei voci, i loop, le velocità, i salti, il nastro che ricorda quando ha registrato ogni pezzo). Controlla,
millisecondo per millisecondo, quale momento dell'ingresso stai sentendo:

* a FIGO 0 il pulito è sempre 8 ms dietro, niente altro;
* gli interventi dub e glitch fanno quello che dicono;
* un intervento alla volta, mai oltre la fine della frase, e dopo ognuno il pulito torna;
* più FIGO dà più interventi, soprattutto a fine frase;
* MEMORIA rimette battute intere a tempo, l'eco si spegne;
* HOLD e PULITO funzionano;
* il cambio di tempo, le frasi da 8 e da 32, il mono, la latenza e il giro completo del nastro di 300 secondi vanno.

Non è ancora girato su un norns vero: la prima volta ascolta i livelli e la latenza.
