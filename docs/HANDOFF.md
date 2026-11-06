# Passaggio di consegne — aggiornato il 6 novembre 2026

## Dove siamo
- **Tappa 1 "Basi del combattimento" finita** (Task 1-12 del piano `docs/superpowers/plans/2026-11-06-voidrise-tappa1-basi.md`), sul ramo `tappa1-basi`. **Non è ancora unita a `main`**: si unisce solo dopo la prova di Denis.
- Che cosa c'è: allenamento contro un manichino (fermo o casuale), 2 giocatori in locale, arena "La Grande Cascata", due lottatori provvisori (Ren e Kael, cel-shading) con la stessa tabella di mosse, comandi su touch, tastiera (2 set) e controller, HUD, menu, pausa, fine partita, "gira il telefono".
- Pagina giocabile: vedi `CLAUDE.md` ("Pubblicare").
- Design: `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md`. Riferimento visivo: `docs/ref/riferimento-stile.png`.

## Build e test
```
bash mk.sh                      # scrive game_w.html (test, con window.__VF) e index.html (pubblicata); stampa SYNTAX_OK
for f in smoke sim attack guard round input render fighter3d feel hud menu perf; do python3 tests/run.py tests/$f.test.js || break; done
python3 tests/run.py tests/render.test.js --viewport 844x390
python3 tests/run.py tests/hud.test.js --viewport 844x390
python3 tests/run.py tests/hud.test.js --viewport 1280x720
python3 tests/run.py tests/touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/orient.test.js --viewport 390x844 --touch --mobile
```
- Opzioni di `run.py`: `--viewport WxH`, `--touch`, `--mobile`, `--seed N` (un fallimento si ripete con lo stesso seme).
- Servono `pip install playwright` e Chromium (il runner usa Chrome/Chromium di sistema se c'è). `three.min.js` (r128) è nel repository e i test lo usano al posto del CDN.
- `run.py` fallisce anche sugli errori della console (tranne "Failed to load resource": i font bloccati).
- Stato dei test al 6/11/2026: tutti verdi, 0 errori.

## Architettura in poche righe
- `src/` è unito da `mk.sh` (ordine in `FILES`) tramite `build.py`; le immagini di `assets/` entrano come data URI, quindi `index.html` è un solo file.
- **Simulazione** (`c1_sim.js`, `c2_moves.js`, `c3_dummy.js`): pura e deterministica. Passo fisso a 60 al secondo, interi in mm e fotogrammi, generatore con seme, niente THREE, DOM, `Math.random`, `Date`, `Math.sin/cos/sqrt`. Serve così per l'online futuro.
- **Grafica, effetti e HUD** (`d_render.js`, `e_fighter3d.js`, `f_fx.js`, `g_hud.js`) leggono lo stato e non lo cambiano mai. Test: "render does not change the sim".
- **Un solo `stepGame()`** in `z_main.js`: legge i comandi, fa `simStep`, passa gli eventi a fx e HUD. Lo usano sia `frame(n)` (test) sia il ciclo in tempo reale (`tick`).
- Ogni lato è `{team:[F], cur:0}` (pronto per il 3v3): il codice passa da `fighterOf(S, side)`, mai da `team[0]`.
- Tutti i numeri di bilanciamento sono in `src/a0_cfg.js` (`CFG`). Le mosse sono in `CFG.moves`.
- `window.__VF` esiste solo in `game_w.html`; `index.html` non lo ha (c'è un test).

## Interfacce chiave
- `BTN = {U:1, D:2, L:4, R:8, P:16, K:32, S:64, DASH:128, GUARD:256}`: un intero di tasti per giocatore, direzioni assolute.
- `simCreate({seed, mode:'versus'|'training', chars, dummy:'fermo'|'casuale'})`, `simStep(S, in0, in1)`, `simClone(S)`, `simHash(S)`, `fighterOf(S, side)`, `dummyInput(S, side)`.
- `S.ev`: eventi del fotogramma (`hit block whiff charge heavyFire thr proj projHit projBlock projClash jump land dash knock ko timeup round fight win draw`), con coordinate in mm: li consumano fx e HUD.
- `G = {state:'title'|'fight'|'pause'|'end', mode, S, acc, last}`; `startMatch(mode, {seed, dummy})`.
- Test: `__VF.frame(n)` fa n passi, un disegno e l'aggiornamento dell'HUD; `__VF.CFG.stop` contiene le classi di hitstop. Gli aiuti dei test (`N`, `fight`, `F`, `scripted`, `key`, `fakePads`, `pd/pm/pu`...) sono in `tests/lib.js`.
- Input: `src/b_input.js` (tastiera: WASD+JKL e frecce+tastierino; controller; touch) -> intero di tasti. Chi conferma "2 Giocatori" diventa G1 con quel dispositivo.

## Valori misurati (6/11/2026, Chromium headless con SwiftShader, `tests/perf.test.js`)
- Logica: **0,0022 ms per fotogramma** (limite del test 0,3 ms).
- Disegno + logica: **1,96 ms per fotogramma** in headless (solo di riferimento: non è un telefono).
- Durata del round con la sequenza di prova: **709 fotogrammi con hitstop, 709 senza** (fotogrammi congelati 141 contro 0). Il KO cade sullo stesso fotogramma perché la sequenza è fissa e il tempo guadagnato dal congelamento coincide con il ritmo delle catene; l'hitstop non allunga il round.
- **FPS sul telefono: ancora da misurare** con `?fps=1` (mostra `#fps`). Obiettivo 60 su un telefono di fascia media.

## Prova a mano (6/11/2026, Playwright)
- 844x390 touch: allenamento, passi con la levetta, pugni, calci, forte, salto, speciale, guardia, scatto, pausa dal pulsante, avversario su CASUALE, ripresa. 1280x720 tastiera: partita a 2 fino a "VINCE REN!" (per far prima la vita di Kael è stata messa a 60 con `__VF.G.S`), poi RIVINCITA. Console senza errori.

## Note per Denis / per dopo
Cose notate nelle revisioni; non costruirle finché Denis non lo chiede.
- La catena p1 → p2 → p3 → forte arriva a segno solo a distanza ravvicinata.
- Dopo il super salto l'attaccante supera l'avversario colpito in aria.
- Ogni salto allontana la telecamera: il fondale "respira".
- I lottatori scivolano sulle giunture delle lastre dipinte mentre la telecamera si sposta.
- Il limite di copertura ferma lo zoom del fondale in cima ai salti sul 16:9.
- Gli FPS sul telefono vanno misurati con `?fps=1`.
- I modelli Meshy di Ren e Kael sono la Tappa 2: prima mostra a Denis saldo e costo stimato, poi procedi solo con il suo ok. `docs/meshy/` non esiste ancora per questo gioco.

## Prossimo passo
Denis prova la pagina sul telefono e con il controller e dice se la Tappa 1 si unisce a `main`. Poi si scrive il piano della Tappa 2 (un piano alla volta), a partire dai modelli Meshy di Ren e Kael.
