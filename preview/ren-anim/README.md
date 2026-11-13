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
- `mods/kit.js`: le tecniche di Ren dalle quattro tavole di Denis (12/11/2026): guardia elastica, passo radente,
  palmo a scatto, gomito spezzaguardia, deviazione circolare, calcio a frusta, passo spezzato, e la camminata in
  guardia avanti e indietro (senza tavola, nel suo stile: passi bassi che non incrociano i piedi, guidata dalla
  distanza percorsa, quindi senza piedi che scivolano a qualsiasi velocità). Tutte partono e tornano
  alla stessa guardia (tre quarti, gambe larghe e basse, braccio avanti dritto a pugno chiuso, mano dietro socchiusa
  sullo stomaco). Ogni mossa è una tabella (tempi, corpo, piedi, braccia, mani) letta dalle stesse poche funzioni.
  Piedi messi a mano (quello in appoggio non si muove), tempi e numeri tutti proposte (il progetto non li definisce
  ancora). Pagina a parte, senza effetti.
- `mods/posa.js` (dopo `kit.js`): "Pose di Ren" (13/11/2026), l'editor di pose chiave chiesto da Denis per mostrare
  le animazioni che ha in mente. Lo stesso Ren e la stessa guardia del kit; punti da trascinare su testa (dove
  guarda), busto, bacino, mani, gomiti, piedi e tutto il corpo (si muovono nel piano di fronte alla camera: si gira
  la vista per spostarli in profondità); per mano e piede i pulsanti di forma, palmo, polso, tallone e punta. Pose
  numerate, "Riproduci" le mostra in fila a velocità fissa (24 fotogrammi da una all'altra), Annulla, note per
  Claude. Funziona con tocco, mouse, tastiera e controller. Le pose si salvano da sole nel database della pagina
  (raccolta `animazioni`, un documento per animazione, con la legenda dei numeri dentro) e su questo dispositivo.
  Ogni posa è sopra la guardia base: corpo, testa, mani (polso e gomito nel riferimento del busto), piedi.
- `mods/body_v1.js`: il primo tentativo, tenuto solo come confronto.

## Costruire

    python3 build.py --assets ASSETS.js --out pagina.html --mods body.js,style.js,trail.js,fx.js,hair.js,extra.js,swag.js

`ASSETS.js` è la riga `const ASSETS={...};` della pagina pubblicata (circa 9,7 MB, non sta nel repository).

La pagina delle tecniche (vista laterale del gioco, velocità vera, pavimento a quadretti di 25 cm):

    python3 build.py --assets ASSETS.js --out tecniche.html --mods body.js,style.js,hair.js,kit.js \
      --title "Tecniche di Ren" --subtitle "Le sette tecniche delle tavole · vista laterale, senza effetti"

L'editor di pose (da pubblicare con il database: `capabilities: {db: {}}`):

    python3 build.py --assets ASSETS.js --out pose.html --mods body.js,style.js,hair.js,kit.js,posa.js \
      --title "Pose di Ren" --subtitle "Editor di pose"

## Prove

    node tests/check.js pagina.html    # errori, precisione dei colpi, costo per fotogramma (vecchie e nuove)
    node tests/legs.js pagina.html     # gambe stirate, piedi sollevati, sprofondati, storti, che scivolano
    node tests/smoke.js pagina.html    # tutte le mosse e i tasti in tempo reale, formato telefono
    node tests/sheet.js pagina.html cartella --plays 2,3 --yaws 65,245   # tavole di controllo delle mosse
    node tests/kit.js tecniche.html    # tecniche: piedi in appoggio fermi, gambe mai tirate, braccia fuori dal petto,
                                       # nessuno scatto tra quarti di fotogramma, dove arriva il palmo
    node tests/posa.js pose.html       # editor di pose su telefono (tocco), con un database finto: ogni parte
                                       # trascinata segue il dito, pulsanti, pose, riproduci, annulla, tastiera,
                                       # controller, salvataggio e riapertura, costo per fotogramma
