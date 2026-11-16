# SAGGA SEQ 0.15 - Installazione

Il firmware lo compila GitHub (il tuo repository `Funamboloide/Sagga-seq`, azione *build firmware*): niente WSL. Ti
servono due file:

* `sagga-0.15.fwsc`: il firmware (dalla pagina dell'azione su GitHub, o dal ramo `pacchetti` del repository);
* `sagga-hub-0.15.zip`: il bridge dei Launchpad, l'hub (pagina 8090, **con l'editor nuovo**) e il convertitore, per il
  Raspberry Pi.

**Il formato.** `SGQB` come prima: slot, file `.sgq`, snapshot e libreria del Pi si aprono così come sono. Un progetto
salvato dalla 0.15 si apre anche con la 0.14 (senza nome e senza groove).

**Cosa cambia.** Sull'FM-1: SAVE + REC svuota uno slot, il nome del progetto con SAVE tenuto e al caricamento, il GROOVE
in HOME 7 K3 / K4. Sul Pi: nell'editor il nome, la scheda Tape, segui l'FM-1, ascolta. Tutto in `RELEASE-NOTES-0.15.md`.

## 1. Aggiorna prima il Raspberry Pi

L'editor nuovo e il bridge nuovo servono per "segui" e "ascolta". Da PowerShell:

```powershell
cd $HOME\Downloads
scp .\sagga-hub-0.15.zip user@10.249.215.136:/tmp/
ssh user@10.249.215.136
```

Sul Pi:

```sh
cd /tmp && unzip -o sagga-hub-0.15.zip && cd sagga-hub-0.15
sudo sh install_hub.sh --no-pc
```

Lo script deve dire `sagga_sgqmid built` **e** `sagga_sgqjson built`. Riavvia da solo hub e bridge; le tue librerie in
`/boot/firmware/sagga/` non le tocca.

## 2. Installa il firmware sull'FM-1 dal Pi

1. FM-1 collegato al Pi, fermo.
2. Apri `http://10.249.215.136:8090`, carica `sagga-0.15.fwsc`, premi **Installa**. Non staccare niente durante la
   scrittura; se salta, ricollega e installa di nuovo.
3. Dopo il riavvio lo schermo dice `SAGGA SEQ 0.15`; i tuoi slot si caricano come prima.

(Con l'FM-1 sul PC va anche `py .\fm1_install.py .\sagga-0.15.fwsc` in PowerShell.)

## 3. Primo controllo

1. **Il nome:** nell'editor apri un progetto, scheda **Progetto**, scrivi un nome in **NOME**, **Salva**, **Manda
   all'FM-1**. Sull'FM-1 SAVE due volte (lo salva nello slot scelto). Tieni SAVE: le righe in basso dicono `SLOT n:` col
   nome e `NOW:` col nome.
2. **Svuotare:** SAVE + PRESETS su uno slot che non ti serve; SAVE + REC: `CLEAR SLOT ...: SAVE+REC AGAIN`; ancora SAVE +
   REC: `SLOT n CLEARED`. Tieni SAVE: `SLOT n: EMPTY`.
3. **GROOVE:** una traccia con sedici step accesi, HOME 7 (HOME + OCT+), K3 su GARAGE: lo shuffle; K4 per quanto.
4. **Segui:** nell'editor spunta **segui l'FM-1**, PLAY sull'FM-1: la cornice bianca corre sugli step.
5. **Ascolta:** spunta **ascolta** e accendi uno step: lo senti dal synth di quella traccia.
6. **Tape:** scheda **Tape**, una traccia (se non è TAPE, scheda Traccia: modo TAPE), tocca il roll: nascono note;
   trascinale; **Salva**, **Manda all'FM-1**, PLAY.

Se qualcosa non torna mandami una foto dello schermo dell'FM-1 o il messaggio dell'editor.
