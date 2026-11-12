# Voidrise Fighters — istruzioni per Claude

Rispondi sempre a Denis **in italiano**, con messaggi brevi e chiari (spesso usa il telefono).

- Picchiaduro anime 2.5D originale in **Three.js r128**, JavaScript vanilla. PC, telefono (**solo orizzontale**) e controller. Obiettivo: Steam e store dei telefoni.
- Design approvato: `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md`. Riferimento visivo: `docs/ref/riferimento-stile.png`.
- Logica di combattimento deterministica a 60 passi fissi (serve per l'online futuro); la grafica legge lo stato e non lo cambia.
- Tutti i numeri di bilanciamento in `src/a0_cfg.js` (oggetto `CFG`).

## Struttura, build e test
- `src/` contiene i moduli, uniti da `mk.sh` (ordine dei file in `FILES`) tramite `build.py` in `game_w.html` (versione di test, con `window.__VF`) e in `index.html` (versione giocabile, un solo file con le immagini incorporate).
- Build: `bash mk.sh` (deve stampare `SYNTAX_OK`).
- Test: `python3 tests/run.py tests/<file>.test.js [--viewport WxH] [--touch] [--mobile] [--seed N]`. File: smoke sim attack guard round input touch render fighter3d feel hud menu orient perf model arena (l'arena 3D: anche con `--viewport 844x390` e `1280x720`). L'elenco completo dei comandi è in `docs/HANDOFF.md`, "Build e test".
  - Servono `pip install playwright` e un browser Chromium (il runner usa Chrome o Chromium di sistema se c'è).
  - `three.min.js` (r128) è nel repository: i test lo usano al posto del CDN.
- Leggi per primo `docs/HANDOFF.md`: stato, decisioni e prossimo passo.
- Arene 3D: `src/d_arena.js`, `CFG.arenas`, strati da `tools/make_layers.py` (dai livelli di Denis in `docs/ref/cascata_livelli/`: 4 cielo, 3 montagna, 2 cascata, 1b nebbia, 1 colline, 0 pavimento), inquadrature `tools/arena_shots.py`, tempi `tools/frame_ms.py` (vedi `docs/HANDOFF.md`, "Arene 3D").
- Lottatori Meshy: `docs/meshy/REN.md` (task, crediti, come rifare il pacchetto `assets/ren/` con `tools/meshy_pack.py`); disegno e pose in `src/e_model.js`, tabella azione → clip in `CFG.clips`. Foglio delle pose: `python3 tools/pose_sheet.py out.png`.
- Meshy, animazioni: `is_free` del catalogo non vale per la API, ogni azione costa 3 crediti.

## Pubblicare
- Pagina giocabile (pagina Claude "Voidrise Fighters"): https://claude.ai/artifact/RdQfJDspYWN6SFx5BoMhCY — si continua a pubblicare lì
- Lancia `bash mk.sh`, poi pubblica `index.html` con lo strumento Artifact (un solo file, icona `game`) su quell'URL.
- Anteprima 3D di Ren (pagina a parte, senza giocare): https://claude.ai/artifact/V3vLHuaZbf47o3DYo65jZC — pubblica `viewer.html` (creato da `mk.sh`, non nel repository) su quell'URL. Prova: `python3 tests/viewer_check.py`. La pittura dal disegno (`tools/paint_from_drawing.py` → `viewer_assets/ren/ren_painted.jpg`) e tutto il look di Ren (`CFG.looks.ren`) dal 10/11 sono anche nel gioco e nell'app: `mk.sh` mette `viewer_assets` in `index.html` (circa 10 MB).
- Anteprima 3D di Kael (Meshy dal disegno vestito `kael_nero.png`, ossa delle dita, animazioni di Ren, pulizia di `tools/kael_fix.py`): https://claude.ai/artifact/3ZbpwhocWKAGHNhFBuA9Hy — pubblica `viewer_kael.html` (creato da `mk.sh` con `wip_assets/kael`, non nel repository) su quell'URL. Prova: `python3 tests/viewer_check.py --page=viewer_kael.html`. Kael di Meshy: `docs/meshy/KAEL.md`.
- Anteprima dell'arena (l'arena da sola, telecamera libera, senza lottatori): https://claude.ai/artifact/9i779EszTGaKUBTJu2bTYh — pubblica `arena.html` (creato da `mk.sh`, non nel repository) su quell'URL. Pagina di prova dell'arena nel gioco (finché Denis non approva): https://claude.ai/artifact/K5Y9HZWitGtRqt5yM9PTSB.
- Prima di pubblicare: tutti i test verdi e nessun errore nella console.
- Il ramo `tappa1-basi` si unisce a `main` solo dopo la prova di Denis.
- Versione "app" per il telefono: `play/` (creata da `mk.sh` con `tools/make_play.py`: pagina intera con three.js dentro, manifest, icona di Ren, service worker per giocare offline). La serve GitHub Pages: https://denis3130.github.io/ZebbyFighterz/play/ (GitHub Pages pubblica il ramo `gh-pages`: per aggiornare l'app, dopo `bash mk.sh` e il commit, `git push origin <ramo>:gh-pages`). Si installa da Safari/Chrome con "Aggiungi alla schermata Home". Prova: `python3 tests/play_check.py`.

## Regole di lavoro di Denis
- Giochi completi e curati: niente emoji al posto della grafica, niente combattimenti fatti solo di numeri.
- Tappe piccole e verificabili: dopo ogni tappa una versione giocabile.
- Ogni funzione va su touch, mouse e tastiera, e controller.
- Game feel: hitstop, lampo, leggero tremolio, colpiti che si schiacciano, contatori che rimbalzano, pulsanti che si schiacciano.
- Gli effetti non allungano le lotte: misura prima e dopo. Misura gli FPS prima e dopo (obiettivo 60 su telefono medio).
- Contenuti originali: ispirati al genere, senza copiare nomi, personaggi o grafica di altri giochi.
- Meshy: prima di spendere crediti mostra a Denis saldo e costo stimato, e procedi solo con il suo ok.
- Prima di mostrare a Denis una versione di un personaggio, guardala tu in 3D da ogni lato, da vicino e in tutte le mosse con `docs/meshy/CONTROLLI.md` (cose storte, sfumate, colori che sbordano, contorni sbagliati) e correggi tutto quello che trovi: non contare su di lui per trovare gli errori. Non cambiare la forma del corpo senza chiederglielo. Per Kael e ogni nuovo lottatore (Denis, 10/11: "guarda bene il modello 3d di ren, scannerizzalo in 3d e rifai le stesse cose su kael"): metti Ren (già approvato) accanto al nuovo, con le stesse inquadrature e mosse, e rifai sul nuovo tutto quello che è stato fatto su Ren (elenco in `docs/meshy/CONTROLLI.md`). Ogni volta che sembra andare bene, confronta il modello sia con i fogli del personaggio dalla stessa inquadratura (`tools/sheet_scan.py`) sia con Ren in 3D (Denis, 10/11: "così capisci dove c'è l'errore ed evito di dirtelo io").
- Niente nuove versioni di un personaggio né cambi di forma senza il permesso di Denis (10/11, dopo il viso di Kael versione 7: "non rifarlo senza il mio permesso"): prima gli mandi le immagini del cambio e aspetti il suo ok, poi pubblichi.
- Consegna: 2-3 righe su cosa è cambiato, FPS e come provarlo; idee "per dopo" annotate senza costruirle; chiudi con un solo passo successivo concreto.
