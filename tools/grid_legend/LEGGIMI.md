# La legenda del grid

`docs/SAGGA-GRID-LEGENDA.pdf`: 19 pagine A4 orizzontali, da sfogliare o da stampare.

* **Pagina 1**: i due Launchpad nella formazione da grid (`--frame`, il sinistro girato), con il nome di ogni tasto e
  la sua freccia; al posto dei pad, la mappa di quale tasto apre quale vista. Toccando il nome di una vista si va
  alla sua pagina.
* **Pagina 2**: i 32 tasti tondi, da soli e con SHIFT, con un disegnino che dice dove sono.
* **Pagine 3-19**: una vista per pagina: il grid grande, una freccia per ogni riga di pad, i colori che dicono quali
  pad fanno cosa, e in alto cosa premere per arrivarci. "↩ la mappa", in fondo, torna alla pagina 1.

`docs/grid-legenda.png` è la pagina 1, per il manuale (`docs/SAGGA-GRID.md`, sezione 3).

## I file

| file | cosa |
| --- | --- |
| `legend_data.js` | tutto il testo, preso dalla sezione 3 di `docs/SAGGA-GRID.md`: quando una vista cambia, si cambia qui |
| `legenda.html` | disegna le pagine: una `section` di 1122 x 793 px è una pagina A4 |
| `render.py` | fa il PDF e il PNG |

## Rifarla

```sh
python3 tools/grid_legend/render.py
```

Serve Playwright con il suo Chromium (`pip install playwright`, `python3 -m playwright install chromium`) e il font
Inter. Se le etichette di una vista non stanno nella pagina, `legenda.html` rimpicciolisce il testo di quella vista
fino a 11,5 px.

I nomi in maiuscolo sono quelli dell'FM-1 e del manuale (CONTINUE, DRUMS, SAVE OVER...); il resto è in italiano. I
colori dei pad raggruppano le funzioni: non sono quelli dei LED.
