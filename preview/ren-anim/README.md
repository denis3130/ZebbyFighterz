# Anteprima "Ren animazioni nuove"

Pagina di prova per le animazioni di Ren (solo grafica: i tempi del combattimento non cambiano).

- `base/viewer_code.html`: il codice dell'anteprima 3D originale di Ren, senza la riga delle immagini incorporate.
- `scaffold.js`: i punti di aggancio (nuove/vecchie, opzioni, tastiera e controller, disegno tra due fotogrammi).
- `mods/body.js`: lo stile di ogni mossa e la fisica del corpo (piedi fissati sulla punta, tallone che si alza e
  ruota, gambe mai stirate, ginocchia sopra i piedi, peso ed equilibrio, colpo sempre dentro la sua zona, allungo).
- `mods/trail.js`: la scia, solo sui colpi forti, curva e sempre dietro al corpo.
- `mods/fx.js`: il manichino, il fermo-immagine, lampo, scintilla, tremolio, il colpo energetico.
- `mods/hair.js`: i capelli che seguono la testa con un piccolo ritardo.
- `mods/body_v1.js`: il primo tentativo, tenuto solo come confronto.

## Costruire

    python3 build.py --assets ASSETS.js --out pagina.html --mods body.js,trail.js,fx.js,hair.js

`ASSETS.js` è la riga `const ASSETS={...};` della pagina pubblicata (circa 9,7 MB, non sta nel repository).

## Prove

    node tests/check.js pagina.html    # errori, precisione dei colpi, costo per fotogramma (vecchie e nuove)
    node tests/legs.js pagina.html     # gambe stirate, piedi sollevati, sprofondati, storti, che scivolano
    node tests/smoke.js pagina.html    # tutte le mosse e i tasti in tempo reale, formato telefono
    node tests/sheet.js pagina.html cartella --plays 2,3 --yaws 65,245   # tavole di controllo delle mosse
