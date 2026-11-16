# SAGGA SEQ 0.15 - Note di rilascio

Cinque cose: **svuotare uno slot** dal pannello, il **nome del progetto**, il **GROOVE** per traccia, l'**editor che
segue la musica** (e la fa suonare all'FM-1) e le **tracce TAPE nell'editor**. Il formato resta `SGQB`: la 0.14 apre i
progetti della 0.15 (senza nome e senza groove), la 0.15 apre tutto quello di prima.

## Svuotare uno slot

Scegli lo slot (SAVE + PRESETS), poi **SAVE + REC**: `CLEAR SLOT 3 MIO PEZZO: SAVE+REC AGAIN`. Di nuovo entro tre
secondi: `SLOT 3 CLEARED: THE PROJECT YOU HAVE STAYS`. Lo slot è `EMPTY`, anche dopo averlo spento: ogni copia di quello
slot nella flash perde la sua intestazione. Il progetto che hai nell'FM-1 non si tocca; SAVE lo rimette in qualunque
slot. Solo da fermo (`CLEAR A SLOT: STOP FIRST`); uno slot già vuoto dice `NOTHING TO CLEAR`.

## Il nome del progetto

Fino a 16 caratteri: lettere, numeri, spazio e `- _ . + # & ! ' ( ) / :` (le lettere accentate perdono l'accento, il
resto diventa `_`). Lo scrivi nell'editor del Pi (scheda Progetto, **NOME**); **Nuovo** chiama il progetto come il file;
un file della libreria caricato dal grid (LIB) che non ha nome prende quello del file.

Sull'FM-1: **SAVE tenuto**, pagina 1, le righe 3 e 4 dicono `SLOT 3: MIO PEZZO` (o `NO NAME`, `EMPTY`) e `NOW:` col
nome del progetto che hai adesso. Mentre giri PRESETS il nome cambia con lo slot. Il caricamento chiede `LOAD SLOT 3
MIO PEZZO: HOME+SAVE AGAIN` e dice `LOADED SLOT 3: MIO PEZZO`. Lo slot tiene il nome nella sua intestazione, quindi lo
mostra senza leggere il progetto; uno slot salvato con la 0.14 non ha nome finché non lo salvi di nuovo. (Con SAVE
tenuto la pagina 1 mostra i nomi al posto della mappa dei tasti; la mappa è nelle pagine 2-4.)

## GROOVE

**HOME 7 K3 / K4** su una traccia che non è TAPE: un template e quanto, 0-100 %. Ogni template sposta ogni sedicesimo
della battuta un po' avanti o indietro (in % dello step, sopra al nudge dello step, allo swing e all'HUMAN) e lo fa più
forte o più piano:

| template | cosa fa |
|---|---|
| HOUSE | i sedicesimi appena in ritardo, l'ottavo in levare su |
| GARAGE | lo shuffle del 2-step |
| DILLA | ubriaco: mai due volte uguale |
| AFRO | 3 + 3 + 2, spinto |
| SAMBA | il secondo e il quarto sedicesimo in anticipo |
| LAID BACK | dietro al tempo |
| PUSH | davanti al tempo |
| HUMAN | i piccoli sbagli di chi suona |
| TRAP | stretto: lo fanno gli accenti |

Un template scelto a 0 % prende il 100 %. Su una traccia TAPE K3 / K4 restano TAPE BARS e TAPE QUANT. Con PICK (HOME +
SEL + un bianco) scegli il template coi tasti. Si salva col progetto.

## L'editor segue la musica e la fa suonare

In alto nell'editor:

* **segui l'FM-1**: mentre l'FM-1 suona, ogni traccia ha una cornice bianca sullo step su cui è (una traccia che suona un
  altro pattern dice `▶P3`), con tempo e scena; nella scheda Tape una linea corre sul loop.
* **ascolta**: lo step che accendi e la nota del roll che tocchi o sposti li suona l'FM-1 su quella traccia (il suo
  canale, la chiave, CHORD, il voicing; una nota TAPE come la suona il tape). Nello step c'è anche **♪ ascolta**.

Passano tutti e due dal bridge del grid (ha la porta dell'FM-1): deve essere acceso. Dalla 0.15 il bridge gira anche
senza i Launchpad (la libreria, l'editor) e quando li attacchi riparte da solo con il grid. L'FM-1 manda le posizioni solo
mentre il Pi le chiede, un sedicesimo alla volta, e mai aspettando la USB: un computer collegato non vede niente che non
abbia chiesto.

## Le tracce TAPE nell'editor

La scheda **Tape**: il piano roll del tape di una traccia (384 tick a quarto, il loop di TAPE battute). Tocchi il vuoto:
una nota da un sedicesimo; la trascini per spostarla (a sedicesimi con **griglia 1/16**, se no a passi di 12 tick); dal
bordo destro la allunghi; Canc toglie quella scelta; sotto, inizio, durata, nota e velocity della nota scelta. Battute e
quantize del loop sulla stessa riga. Si salva come il resto: versioni, controlli del firmware (una nota oltre la fine
del loop va via, e la pagina dice quante). Nella scheda Traccia una traccia TAPE ha TAPE battute e quantize, le altre il
GROOVE; nella scheda Tracce una traccia TAPE porta al suo roll.

## Corretto

* L'editor 0.14: il menu **modo** della scheda Traccia scriveva i bit sbagliati per TAPE e BREAK (metteva IN KEY +
  DRUM). Ora scrive quelli giusti.
* SAVE e REC premuti nello stesso giro del firmware (succede subito dopo STOP, mentre si cancella la flash) perdevano il
  SAVE + REC: il SAVE ora si legge per primo.

## Sotto il cofano

* `firmware/src/sagga_link.c` (nuovo): SysEx 30 (il Pi chiede le posizioni per 6 s), 31 (dove è ogni traccia, a ogni
  sedicesimo e a START / STOP), 32 (suona queste note su questa traccia). `sagga_store.c`: il nome nell'intestazione
  dello slot, SAVE + REC. `sagga_live3.c`: GROOVE. Il core: `sq_name_sanitize`, `sq_groove_*`, il blocco 1 del progetto
  da 796 byte (0.14: 780).
* `sagga_sgqjson`: il nome, il GROOVE, gli eventi TAPE (`tape T clear - 0`, `tape T,ON,DUR,NOTA add - VEL`) e il loop.
* Il bridge: `Control` chiede le posizioni mentre una pagina le vuole (`/run/sagga/pos-want`), le scrive in
  `pos.json`, manda le anteprime (`bridge-preview.json`). L'hub: `GET /api/pos`, `POST /api/fm1/preview`.
* Test: il core (nome, groove, un progetto 0.14), il simulatore (nomi, slot svuotati anche con due copie, groove,
  posizioni e anteprime lette dal bridge vero), l'editor (convertitore, hub, bridge, la pagina in un browser: nome,
  groove, una traccia TAPE scritta col mouse, segui, ascolta).
