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
- `mods/posa.js` (dopo `kit.js`): "Pose di Ren" (13-14/11/2026), le pose chiave a tasti con cui Denis mostra le
  animazioni che ha in mente. Per braccio avanti e dietro Guardia / Avanti / Alto / Viso / Gomito / Basso, per ogni mano
  Pugno / Socchiusa / Aperta, per gamba avanti e dietro A terra / Ginocchio / Calcio / Alto / Basso / Dietro, Busto Dritto / Avanti /
  Indietro, Altezza Normale / Basso / Alto, Passo Indietro / Qui / Avanti / 2 avanti. Il resto del corpo segue da solo
  (un braccio dritto o un gomito porta dentro la spalla, un calcio inclina indietro e alza sulla gamba d'appoggio, il
  cui piede sale sulla punta e gira; due piedi in aria fanno un salto; i passi sono veri: un piede e poi l'altro,
  ciascuno alzato, nessuno striscia; un piede che si stacca sale prima di andare avanti e atterra per ultimo; gli occhi
  restano sull'avversario). Ren a sinistra, i tasti a destra; "Animazioni" apre l'elenco a gruppi (un tocco: si apre e
  parte). Ogni posa può avere i suoi tempi (t fotogrammi per arrivarci, h ferma, e: snap o out), altrimenti 24
  fotogrammi. Tocco, mouse, tastiera, controller. Salvataggio nel database della pagina (raccolta `animazioni`,
  formato 2: le scelte per nome, con la legenda dentro) e sul dispositivo. La spinta che tiene le braccia fuori dal
  busto, in questa pagina, sfuma oltre i bordi del busto (`RS.torso.soft`, style.js): un braccio che entra nella fascia
  del petto non scatta. Oltre i tasti, per le mosse speciali di Claude (14/11): tutto il corpo che gira su se stesso
  (sul piede che resta a terra, sulla punta) o fa la capriola (sul bacino, in aria), salti più alti, un posto in metri,
  lo scatto radente, e gli effetti all'arrivo di una posa (impatto, impatto forte con lampo e tremolio, energia tra le
  mani, onda di energia in avanti, scia dell'arto). Solo grafica, calcolati dal tempo di riproduzione: un'animazione
  è uguale ogni volta. Il ginocchio di una gamba in aria si piega sempre dal suo lato naturale (la linea della gamba
  girata di un quarto in avanti: giù -> avanti, avanti -> su, indietro -> giù), anche quando la gamba passa da davanti
  a dietro, e un piede che passa da davanti a dietro il bacino gira sotto di esso ad arco; il tallone d'appoggio
  vicino alla gamba tesa sale piano (`RB.softHeel`, body.js); un braccio quasi teso ci arriva morbido; la fascia
  segue il corpo girato e capovolto.
  La pagina si apre sull'Anteprima (14/11, Denis: "faccio successivo e mi parte l'animazione successiva"): Ren in
  grande e a destra il gruppo, il nome e la descrizione dell'animazione, «Successiva» e «Precedente» (frecce sinistra
  e destra; croce o dorsali del controller), Pausa (ferma il fotogramma: spazio, A), Elenco (L, X), Modifica (M, Y o
  Start: l'editor a tasti, che ha «Anteprima» per tornare). Le animazioni di Claude non si cambiano per sbaglio: la
  prima modifica a una crea una copia tua in «Le tue» («… (mia)»), l'originale resta; una copia rimasta su un
  dispositivo e mai salvata non va mai sopra l'originale del database (si riapre quello).
  I calci (14/11, Denis: "la gamba destra oltrepassa quella sinistra"): nei calci con la gamba dietro l'anca destra
  viene avanti (prima girava al contrario), il piede sinistro d'appoggio gira la punta in fuori e il suo ginocchio
  resta fuori dalla strada; il piede che calcia sta sul suo lato, sotto la sua anca (la guardia di profilo tiene il
  piede dietro un po' a sinistra di quello davanti: in aria il destro si sposta solo quando è dietro il bacino, il
  sinistro solo quando è davanti); la gamba si piega mentre passa sotto il bacino (il calcio si richiama prima di
  tornare giù); il ginocchio in aria punta un po' in fuori. Le due gambe non si attraversano mai.
- `data/animazioni.py`: le animazioni fatte da Claude (14/11/2026, richieste di Denis: "almeno 50, fatte bene", poi
  "tante combo [...] combo speciali, mosse speciali"): 103 in sei gruppi (Colpi 15, Calci 17, Combinazioni 30,
  Difese 11, Movimenti 12, Speciali 18), ognuna con i suoi tempi e una nota per posa. Le mosse speciali: calcio
  girato, calcio tornado, capriola d'ascia, mille palmi, onda del vuoto, pugno fantasma, ascesa, martello del cielo,
  pugno rotante, danza del vuoto, capriola di vittoria e il Colpo Voidrise (la mossa finale). Ogni colpo "snap" ha il
  suo impatto (l'ultimo di una combinazione è forte), i calci la loro scia.
  Scrive `data/animazioni.json` (i documenti come li salva la pagina, id `c-<nome>`), che va nel database della
  pagina.
- `mods/body_v1.js`: il primo tentativo, tenuto solo come confronto.

## Costruire

    python3 build.py --assets ASSETS.js --out pagina.html --mods body.js,style.js,trail.js,fx.js,hair.js,extra.js,swag.js

`ASSETS.js` è la riga `const ASSETS={...};` della pagina pubblicata (circa 9,7 MB, non sta nel repository).

La pagina delle tecniche (vista laterale del gioco, velocità vera, pavimento a quadretti di 25 cm):

    python3 build.py --assets ASSETS.js --out tecniche.html --mods body.js,style.js,hair.js,kit.js \
      --title "Tecniche di Ren" --subtitle "Le sette tecniche delle tavole · vista laterale, senza effetti"

L'editor di pose (da pubblicare con il database: `capabilities: {db: {}}`):

    python3 build.py --assets ASSETS.js --out pose.html --mods body.js,style.js,hair.js,kit.js,posa.js \
      --title "Pose di Ren" --subtitle "Pose pronte"

## Prove

    node tests/check.js pagina.html    # errori, precisione dei colpi, costo per fotogramma (vecchie e nuove)
    node tests/legs.js pagina.html     # gambe stirate, piedi sollevati, sprofondati, storti, che scivolano
    node tests/smoke.js pagina.html    # tutte le mosse e i tasti in tempo reale, formato telefono
    node tests/sheet.js pagina.html cartella --plays 2,3 --yaws 65,245   # tavole di controllo delle mosse
    node tests/kit.js tecniche.html    # tecniche: piedi in appoggio fermi, gambe mai tirate, braccia fuori dal petto,
                                       # nessuno scatto tra quarti di fotogramma, dove arriva il palmo
    node tests/posa.js pose.html       # pose a tasti su telefono (tocco), con un database finto: ogni tasto,
                                       # pose, riproduci, annulla, tastiera, controller, salvataggio e riapertura;
                                       # l'Anteprima (successiva e precedente con tocco, tasti, controller; pausa;
                                       # elenco; la copia quando si modifica un'animazione di Claude; l'originale
                                       # che si riapre sopra una copia rimasta sul dispositivo);
                                       # tutte le 46.656 combinazioni (braccia fuori dal petto, piedi sopra il
                                       # pavimento, gambe non tirate) e ogni cambio senza scatti; costo per fotogramma
    python3 data/animazioni.py         # le animazioni di Claude -> data/animazioni.json
    node tests/posa_anims.js pose.html # ogni animazione, un quarto di fotogramma alla volta: piedi a terra fermi,
                                       # niente sotto il pavimento, braccia fuori dal petto e dal viso, gambe
                                       # d'appoggio non tirate, nessuna articolazione che salta, le due gambe mai
                                       # una dentro l'altra (almeno 12 cm tra le loro linee; SLIDE=1: più severo)
