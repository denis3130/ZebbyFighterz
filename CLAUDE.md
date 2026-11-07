# Voidrise Fighters — istruzioni per Claude

Rispondi sempre a Denis **in italiano**, con messaggi brevi e chiari (spesso usa il telefono).

- Picchiaduro anime 2.5D originale in **Three.js r128**, JavaScript vanilla. PC, telefono (**solo orizzontale**) e controller. Obiettivo: Steam e store dei telefoni.
- Design approvato: `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md`. Riferimento visivo: `docs/ref/riferimento-stile.png`.
- Logica di combattimento deterministica a 60 passi fissi (serve per l'online futuro); la grafica legge lo stato e non lo cambia.
- Tutti i numeri di bilanciamento in `src/a0_cfg.js` (oggetto `CFG`).

## Struttura, build e test
- `src/` contiene i moduli, uniti da `mk.sh` (ordine dei file in `FILES`) tramite `build.py` in `game_w.html` (versione di test, con `window.__VF`) e in `index.html` (versione giocabile, un solo file con le immagini incorporate).
- Build: `bash mk.sh` (deve stampare `SYNTAX_OK`).
- Test: `python3 tests/run.py tests/<file>.test.js [--viewport WxH] [--touch] [--mobile] [--seed N]`. File: smoke sim attack guard round input touch render fighter3d feel hud menu orient perf. L'elenco completo dei comandi è in `docs/HANDOFF.md`, "Build e test".
  - Servono `pip install playwright` e un browser Chromium (il runner usa Chrome o Chromium di sistema se c'è).
  - `three.min.js` (r128) è nel repository: i test lo usano al posto del CDN.
- Leggi per primo `docs/HANDOFF.md`: stato, decisioni e prossimo passo.

## Pubblicare
- Pagina giocabile (pagina Claude "Voidrise Fighters"): https://claude.ai/artifact/RdQfJDspYWN6SFx5BoMhCY — si continua a pubblicare lì
- Lancia `bash mk.sh`, poi pubblica `index.html` con lo strumento Artifact (un solo file, icona `game`) su quell'URL.
- Prima di pubblicare: tutti i test verdi e nessun errore nella console.
- Il ramo `tappa1-basi` si unisce a `main` solo dopo la prova di Denis.
- Versione "app" per il telefono: `play/` (creata da `mk.sh` con `tools/make_play.py`: pagina intera con three.js dentro, manifest, icona di Ren, service worker per giocare offline). La serve GitHub Pages: https://denis3130.github.io/ZebbyFighterz/play/ (Pages va attivato da Denis in Settings → Pages, ramo `tappa1-basi`, cartella `/ (root)`; da questa sessione non si può). Si installa da Safari/Chrome con "Aggiungi alla schermata Home". Prova: `python3 tests/play_check.py`.

## Regole di lavoro di Denis
- Giochi completi e curati: niente emoji al posto della grafica, niente combattimenti fatti solo di numeri.
- Tappe piccole e verificabili: dopo ogni tappa una versione giocabile.
- Ogni funzione va su touch, mouse e tastiera, e controller.
- Game feel: hitstop, lampo, leggero tremolio, colpiti che si schiacciano, contatori che rimbalzano, pulsanti che si schiacciano.
- Gli effetti non allungano le lotte: misura prima e dopo. Misura gli FPS prima e dopo (obiettivo 60 su telefono medio).
- Contenuti originali: ispirati al genere, senza copiare nomi, personaggi o grafica di altri giochi.
- Meshy: prima di spendere crediti mostra a Denis saldo e costo stimato, e procedi solo con il suo ok.
- Consegna: 2-3 righe su cosa è cambiato, FPS e come provarlo; idee "per dopo" annotate senza costruirle; chiudi con un solo passo successivo concreto.
