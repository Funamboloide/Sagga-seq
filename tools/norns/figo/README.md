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
* **Dove metterlo**, PARAMETERS > **routing**:
  * **insert**: in serie su tutto il loop, il suono passa tutto da norns. Il pulito esce da FIGO.
  * **aux (mandata)**: su un bus del mixer, in mandata e ritorno. È il caso del tuo rig. Il pulito è già sul mixer,
    quindi FIGO non lo fa uscire mai: sul ritorno ci sono solo gli interventi e la memoria, e quando non succede niente
    il ritorno è muto. Se il pulito uscisse anche dal ritorno, qualche millisecondo dopo l'originale, i due insieme
    farebbero un effetto phaser.
* **I livelli**: FIGO spegne il monitor di norns da solo (il pulito passa da softcut, o in aux dal mixer) e lo rimette
  com'era quando chiudi lo script. In LEVELS il **softcut** deve essere a 0 dB.

## La latenza

* **norns**: quello che entra esce circa **11 ms** dopo. Sono i convertitori e JACK: 3 blocchi da 128 campioni, più
  uno perché softcut è un programma a parte da quello che mischia ingresso e uscita. È una stima dal codice e dalla
  configurazione di norns, non una misura, e uno script non la può togliere.
* **FIGO**: prima (0.1) ci aggiungeva **8 ms**, perché il pulito leggeva il nastro 8 ms dietro la testina che registra.
  Adesso legge **mezzo millisecondo** dietro (PARAMETERS > **latenza**): softcut, in ogni blocco, scrive l'ingresso
  prima di leggerlo, e scrive 8 campioni dietro la testina, quindi bastano 10 campioni (0,2 ms). In insert il totale
  scende così da circa 19 a circa 11 ms.
* **Su un bus (aux)** FIGO fa di più: fa partire tutto quello che suona prima, di quanto il suono impiega ad andare a
  norns e tornare al mixer (PARAMETERS > **anticipo**, 11 ms). Può farlo perché quello che ripete è già sul nastro.
  Così le ripetizioni, i roll, l'indietro, la memoria e l'eco cadono **sulla griglia del pulito al mixer**, non 11 ms
  dopo.

**Tarare l'anticipo** (una volta, poi resta salvato). A misura: routing = **insert** e FIGO a 0, registra dalla USB del
12MTK il canale del suono pulito (per esempio la cassa) e il ritorno di norns, e in Ableton misura di quanti ms il colpo
del ritorno arriva dopo quello del canale: quello è l'anticipo. Poi rimetti routing = **aux**. A orecchio: routing =
aux, una cassa dritta sul bus, FIGO 100 e carattere 0 (ripetizioni lunghe); muovi l'anticipo finché i colpi ripetuti
non si fondono con quelli del mixer, senza flam.

## I comandi

| | |
| --- | --- |
| **E2 FIGO** | quanto interviene. 10-30: qualche fill a fine frase. 50: qualcosa in ogni frase. 100: sempre |
| **E3 CARATTERE** | da **dub** (ripetizioni lunghe, reverse a mezza velocità, ottava sotto, tape stop, eco lanciate) a **glitch** (1/16 e 1/32, roll che sale, sedicesimi rimescolati, gate, ottava sopra) |
| **E1 MEMORIA** | una battuta di 1, 2, 4 o 8 battute fa che torna sotto, filtrata e con i lati scambiati, o un'eco lanciata a fine frase. Funziona anche con FIGO a zero |
| **K2 HOLD** | dal prossimo battito ripete il battito appena passato; con FIGO alto lo varia da solo (più corto, al contrario, a doppia o mezza velocità). K2 di nuovo: torna il loop |
| **K3 PULITO** | sul prossimo battito esce con un tape stop (dub) o un backspin (glitch), poi solo il pulito (in aux: silenzio). K3 di nuovo: riparte |

Lo schermo mostra FIGO (con **AUX** accanto, in aux), il cursore dub-glitch, MEMORIA, il tempo, la frase un battito per
casella e, in grande, l'intervento in corso.

**Dal controller**: ogni valore si può mappare su una manopola MIDI (PARAMETERS > MAP): per esempio FIGO su una
manopola di SAGGA Live o della BeatStep Pro.

## Gli interventi

| | cosa fa |
| --- | --- |
| 1/4, 1/8, 1/16, 1/32 | il pezzo che parte sul battito suona una volta, poi si ripete fino alla fine dell'intervento |
| ROLL | 1/4, poi 1/8, 1/16, 1/32: un build-up; con glitch alto sale anche di intonazione, nella seconda metà |
| REVERSE | gli ultimi battiti al contrario (dub: a mezza velocità) |
| OTTAVA - / OTTAVA + | il nastro a mezza velocità / l'ultimo mezzo battito a doppia velocità |
| TAPE STOP | il nastro rallenta fino a fermarsi, solo a fine battuta o a fine frase |
| SHUFFLE | i sedicesimi dell'ultima battuta, in un ordine nuovo |
| GATE | il loop tagliato a sedicesimi (non in aux: lì non c'è un pulito da tagliare) |
| INDIETRO | quello che suonava 1, 2 o 4 battute fa, a tempo, al posto del loop |

Un intervento dura mezzo battito, uno o due battiti e non passa mai la fine della frase: il primo battito della frase
nuova arriva pulito. In aux suonano sopra il pulito invece che al suo posto; le ripetizioni si sentono dalla prima
ripetizione (il primo pezzo è il pulito, già sul mixer), e REVERSE, OTTAVA - e TAPE STOP entrano dopo qualche
millisecondo, quando suonano quello che è già sul nastro.

Gli interventi partono 7,5 ms prima del battito: così vedono il nastro 8 ms dietro la testina, come nella 0.1, e un
salto ha finito la sua dissolvenza prima dell'attacco del colpo. Si sente tutto uguale a prima, solo meno in ritardo.

## Il menu (PARAMETERS)

FIGO, carattere e memoria (come le manopole); **frase** 8, 16 o 32 battiti; **allinea**; **uscita (K3)**: auto, tape
stop, backspin o secca; **routing** insert o aux (mandata); **ingresso** stereo o mono (L); **livello** di quello che
esce da A; **livello memoria**; **latenza (dietro la testina)**: 0,5 ms (da 0,3 a 30); **anticipo (aux)**: 11 ms (da 0
a 40). Le impostazioni restano per la volta dopo. La latenza ha un nome nuovo: gli 8 ms salvati dalla 0.1 non tornano.

## Prove

`tools/norns/test_figo.lua` (`texlua tools/norns/test_figo.lua`) fa girare lo script con un norns finto e un modello di
softcut fatto come il suo codice (softcut-lib, quello che norns compila): le voci fatte in ordine a ogni blocco, la
testina che scrive 8 campioni dietro la sua posizione e la lettura che ne guarda 2 avanti, la dissolvenza di ogni salto
e di ogni giro del loop (la testina vecchia continua dov'era mentre sfuma; un salto chiesto durante una dissolvenza
aspetta la sua fine, e un punto del loop impostato intanto lo cancella), le rampe di velocità e di volume a un polo.
Controlla, millisecondo per millisecondo, quale momento dell'ingresso stai sentendo e se è già sul nastro:

* a FIGO 0 il pulito è sempre mezzo millisecondo dietro la testina, niente altro;
* niente di quello che senti suona nastro non ancora registrato, in dub, in glitch, a 90, 120, 128 e 174 BPM, con il
  messaggio della posizione di norns in ritardo di 0, 2 o 9 ms;
* gli interventi dub e glitch fanno quello che dicono, uno alla volta, mai oltre la fine della frase, ognuno 7,5 ms
  prima del suo battito, e dopo ognuno il pulito torna;
* le ripetizioni sono pezzi interi dopo il pulito, entro 0,4 ms;
* più FIGO dà più interventi, soprattutto a fine frase;
* MEMORIA rimette battute intere a tempo, l'eco si spegne;
* HOLD e PULITO funzionano;
* uno START di SAGGA durante un intervento (norns rimette il conto dei battiti a zero): FIGO va avanti, nessun
  intervento dura più dei suoi 2 battiti, in insert e in aux;
* le scelte a caso che tengono lontane le testine, provate ventimila volte: la MEMORIA a doppia solo se resta dietro,
  i sedicesimi al contrario di SHUFFLE solo da quello che è già registrato;
* in aux: a FIGO 0 il ritorno è muto, il pulito non esce mai, A si sente solo durante un intervento, niente GATE né
  ripetizioni senza un pezzo dopo il primo; al mixer (con un giro di 11 ms) le ripetizioni cadono a pezzi interi dopo
  il pulito, entro 0,6 ms, i roll entro 3,5 ms, la memoria a battute intere, HOLD a battiti interi; da aux a insert
  torna il pulito, da insert ad aux sparisce;
* il cambio di tempo, le frasi da 8 e da 32, il mono, la latenza e il giro completo del nastro di 300 secondi vanno.

Le nuove prove hanno trovato tre errori della 0.1, corretti qui:

* il **ROLL** con glitch alto alzava la velocità troppo presto. La rampa di softcut sale subito (non in modo lineare,
  come pensava il vecchio modello), e la testina che legge superava quella che registra per circa 0,3 secondi a roll:
  suonava il nastro di 5 minuti prima, o silenzio nei primi 5 minuti. Adesso sale dalla seconda metà del roll, quando
  legge solo quello che è già registrato;
* la **MEMORIA** a doppia velocità, partita da una sola battuta fa e lunga 8 battiti, faceva lo stesso. Adesso va a
  doppia solo se resta dietro;
* uno **START** di SAGGA durante un intervento lo teneva aperto finché norns non tornava a contare fin lì: con un START
  al battito 80, 42 secondi senza altri interventi, e in insert l'ultimo pezzo in loop. Adesso FIGO conta i battiti per
  conto suo e non torna mai indietro.

Non è ancora girato su un norns vero: la prima volta ascolta i livelli, e su un bus tara l'anticipo.
