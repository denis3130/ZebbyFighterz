# Anteprima "Ren animazioni nuove"

Pagina di prova per le animazioni di Ren (solo grafica: i tempi del combattimento non cambiano).

- `base/viewer_code.html`: il codice dell'anteprima 3D originale di Ren, senza la riga delle immagini incorporate.
- `scaffold.js`: i punti di aggancio (nuove/vecchie, opzioni, tastiera e controller, disegno tra due fotogrammi).
- `mods/body.js`: lo stile di ogni mossa e la fisica del corpo (piedi fissati sulla punta, tallone che si alza e
  ruota, gambe mai stirate, ginocchia sopra i piedi, peso ed equilibrio, colpo sempre dentro la sua zona, allungo).
- `mods/style.js`: lo stile di Ren fatto a mano: guardia "acqua che scorre" a mani aperte con piccoli cerchi,
  guardia tenuta in camminata, gesto da fermo (scioglie il collo). Braccia con cinematica inversa.
- `mods/trail.js`: la scia, solo sui colpi forti, curva e sempre dietro al corpo.
- `mods/fx.js`: il manichino, il fermo-immagine, lampo, scintilla, tremolio, il colpo energetico.
- `mods/hair.js`: i capelli che seguono la testa con un piccolo ritardo.
- `mods/extra.js`: altre animazioni: calcio rotante e spazzata (clip di Meshy non ancora usate), caduta da KO,
  colpi in volo, combo, vittoria.
- `mods/swag.js`: entrata (si scioglie, poi scatta in guardia con un anello d'acqua a terra) e provocazione
  ("no-no" col dito), fatte a mano posa per posa.
- `mods/kit.js`: le tecniche di Ren dalle quattro tavole di Denis (12/11/2026), prima tappa: guardia elastica,
  passo radente, palmo a scatto. Tutte partono e tornano alla stessa guardia (quella della tavola: tre quarti,
  gambe larghe e basse, mano avanti aperta, mano dietro sullo stomaco). Piedi messi a mano (quello in appoggio non si
  muove), tempi e numeri tutti proposte (il progetto non li definisce ancora). Pagina a parte, senza effetti.
- `mods/body_v1.js`: il primo tentativo, tenuto solo come confronto.

## Costruire

    python3 build.py --assets ASSETS.js --out pagina.html --mods body.js,style.js,trail.js,fx.js,hair.js,extra.js,swag.js

`ASSETS.js` è la riga `const ASSETS={...};` della pagina pubblicata (circa 9,7 MB, non sta nel repository).

La pagina delle tecniche (vista laterale del gioco, velocità vera, pavimento a quadretti di 25 cm):

    python3 build.py --assets ASSETS.js --out tecniche.html --mods body.js,style.js,hair.js,kit.js \
      --title "Tecniche di Ren" --subtitle "Guardia, passo radente, palmo · vista laterale, senza effetti"

## Prove

    node tests/check.js pagina.html    # errori, precisione dei colpi, costo per fotogramma (vecchie e nuove)
    node tests/legs.js pagina.html     # gambe stirate, piedi sollevati, sprofondati, storti, che scivolano
    node tests/smoke.js pagina.html    # tutte le mosse e i tasti in tempo reale, formato telefono
    node tests/sheet.js pagina.html cartella --plays 2,3 --yaws 65,245   # tavole di controllo delle mosse
    node tests/kit.js tecniche.html    # tecniche: piedi in appoggio fermi, gambe mai tirate, braccia fuori dal petto,
                                       # nessuno scatto tra quarti di fotogramma, dove arriva il palmo
