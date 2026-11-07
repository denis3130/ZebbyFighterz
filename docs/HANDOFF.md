# Passaggio di consegne — aggiornato il 7 novembre 2026

- **Registro dell'esecuzione**: `docs/superpowers/plans/2026-11-06-voidrise-tappa1-basi.ledger.md` (ogni decisione presa, con il suo costo, e i punti minori rimandati).

## Dove siamo
- **Tappa 2a "Ren di Meshy in gioco" (7/11/2026)**, ramo `tappa2-ren-meshy` (parte da `tappa1-basi`): il lato 0 (Ren) è il modello Meshy con scheletro e 25 animazioni Meshy; Kael resta il lottatore provvisorio. Piano: `docs/superpowers/plans/2026-11-07-voidrise-tappa2a-ren-meshy.md`, registro con tutte le decisioni: `...-ren-meshy.ledger.md`. Task Meshy, crediti (135 spesi, saldo 1225) e come rifare il pacchetto: `docs/meshy/REN.md`.
  - Come funziona: `tools/meshy_pack.py` → `assets/ren/` (json + bin + jpg, dentro `index.html`, che ora pesa 4,5 MB); `src/e_model.js` disegna lo `SkinnedMesh` toon con contorno e calcola la posa con `mdPoseOf(F, S)`, funzione pura dello stato; la tabella azione → clip è `CFG.clips`. Il colpo cade nel fotogramma attivo della logica (tempo trovato al caricamento); camminate sulla distanza del piede a terra (niente scivolate); calcio basso con IK.
  - Denis non è contento della faccia (capelli meno a punte del disegno): "teniamolo così per ora".
- **Tappa 1 "Basi del combattimento" finita** (Task 1-12 del piano `docs/superpowers/plans/2026-11-06-voidrise-tappa1-basi.md`), sul ramo `tappa1-basi`, più le correzioni della revisione finale (vedi sotto). **Non è ancora unita a `main`**: si unisce solo dopo la prova di Denis.
- Che cosa c'è: allenamento contro un manichino (fermo o casuale), 2 giocatori in locale, arena "La Grande Cascata", due lottatori provvisori (Ren e Kael, cel-shading) con la stessa tabella di mosse, comandi su touch, tastiera (2 set) e controller, HUD, menu, pausa, fine partita, "gira il telefono".
- Pagina giocabile: vedi `CLAUDE.md` ("Pubblicare").
- Design: `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md`. Riferimento visivo: `docs/ref/riferimento-stile.png`.

## Build e test
```
bash mk.sh                      # scrive game_w.html (test, con window.__VF) e index.html (pubblicata); stampa SYNTAX_OK
for f in smoke sim attack guard round input render fighter3d feel hud menu perf model; do python3 tests/run.py tests/$f.test.js || break; done
python3 tests/run.py tests/render.test.js --viewport 844x390
python3 tests/run.py tests/hud.test.js --viewport 844x390
python3 tests/run.py tests/hud.test.js --viewport 1280x720
python3 tests/run.py tests/touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/orient.test.js --viewport 390x844 --touch --mobile
python3 tests/run.py tests/model.test.js --viewport 844x390 --touch --mobile
python3 tests/play_check.py
```
- Opzioni di `run.py`: `--viewport WxH`, `--touch`, `--mobile`, `--seed N` (un fallimento si ripete con lo stesso seme).
- Servono `pip install playwright` e Chromium (il runner usa Chrome/Chromium di sistema se c'è). `three.min.js` (r128) è nel repository e i test lo usano al posto del CDN.
- `run.py` fallisce anche sugli errori della console (tranne "Failed to load resource": i font bloccati).
- Stato dei test al 7/11/2026 (Tappa 2a, dopo la revisione finale): tutti verdi, 288 prove sui comandi qui sopra più `play_check`, 0 errori.

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
- Test: `__VF.frame(n)` fa n passi, un disegno e l'aggiornamento dell'HUD; `__VF.CFG.stop` contiene le classi di hitstop. Gli aiuti dei test (`N`, `fight`, `F`, `scripted`, `key`, `fakePads`, `padsAt`, `pd/pm/pu`, `ptr`, `tapEl`...) sono in `tests/lib.js`.
- Input: `src/b_input.js` (tastiera: WASD+JKL e frecce+tastierino; controller; touch) -> intero di tasti. Chi conferma "2 Giocatori" diventa G1 con quel dispositivo. In allenamento G1 usa entrambe le tastiere, il touch e un controller: quello che ha confermato, altrimenti il primo collegato (0 se non ce n'è nessuno). Tutte le letture dei controller passano da `inputPadList()`: se la pagina non può usare la Gamepad API (SecurityError) vale come "nessun controller".
- Touch: i pulsanti dei menu e ⏸ si attivano al **rilascio** del dito sul pulsante (`mnTap` in `h_menu.js`), così vanno anche con il pollice sulla levetta; il click che Chrome manda dopo un tocco viene ignorato. Un tasto di combattimento tenuto si rilascia se il dito scivola più di 16 px fuori (`IN_SLIDE`).
- Pausa: "FPS: SÌ / NO" mostra il contatore in basso al centro (anche `?fps=1`); la scelta resta nel dispositivo (`localStorage`, chiave `voidrise.prefs`, con versione, dentro try/catch).

## Valori misurati (6/11/2026, Chromium headless con SwiftShader, `tests/perf.test.js`, 844x390)
- Logica: **0,0018 ms per fotogramma** (limite del test 0,3 ms; prima delle correzioni finali 0,0020).
- Disegno + logica: **circa 2,2 ms per fotogramma** in headless (3 prove: 2,38 / 1,98 / 2,21; prima delle correzioni finali 2,43 / 2,25 / 2,03: nessuna differenza misurabile). Solo di riferimento: non è un telefono.
- Durata del round (sonda `tests/perf.test.js`: attaccante solo corpo a corpo, senza speciale né presa, contro un avversario fermo; 5 sfasamenti della sequenza, ognuno con e senza hitstop): **KO in media dopo 1040 fotogrammi con hitstop (734-1230) contro 988 senza (734-1143)**, cioè circa 52 fotogrammi (0,9 s) in più. L'hitstop congela in media il 14% dei fotogrammi. Il KO arriva in tutte e 10 le prove. Prima delle correzioni finali era 1070 contro 988: cambia solo perché p3 ora spinge meno (24 invece di 35) e la sequenza arriva a segno più spesso. Attenzione: è una sequenza a tempi fissi, non una partita vera, e con soli 5 sfasamenti la differenza varia molto da una prova all'altra; mostra l'ordine di grandezza, non una misura precisa. Una prima sonda con lo speciale dava 709 contro 709 solo perché il colpo finale era il proiettile lanciato a un fotogramma fisso: un caso fortuito, da non usare.
- **FPS sul telefono: ancora da misurare** da Denis: menu di pausa, "FPS: SÌ" (oppure `?fps=1`). Obiettivo 60 su un telefono di fascia media.

## Prova a mano (6/11/2026, Playwright)
- 844x390 touch: allenamento, passi con la levetta, pugni, calci, forte, salto, speciale, guardia, scatto, pausa dal pulsante, avversario su CASUALE, ripresa. 1280x720 tastiera: partita a 2 fino a "VINCE REN!" (per far prima la vita di Kael è stata messa a 60 con `__VF.G.S`), poi RIVINCITA. Console senza errori.
- Dopo le correzioni finali, 844x390 con tocchi veri (CDP): titolo con un dito appoggiato, ⏸ con il pollice sulla levetta, AVVERSARIO e RIPRENDI con il pollice giù, AVVERSARIO con un dito solo (cambia una volta sola), TORNA AL MENU (il click che segue non fa partire una partita), dito che scivola fuori da PUGNO (nessun forte). Controller: allenamento scelto con il secondo controller, che muove G1. Console senza errori.

## Correzioni della revisione finale (6/11/2026)
- Dopo "TEMPO!" (e dopo il K.O.) la lotta non si risolve più: niente comandi (il rilascio forzato di un tasto tenuto non è un tocco), contatti o proiettili nuovi; le azioni in corso finiscono senza colpire, quindi il round va a chi era avanti nel fotogramma di TEMPO!.
- Dopo un salto sopra l'avversario si atterra girati verso di lui: il colpo o lo scatto premuti durante l'atterraggio partono dalla parte giusta.
- Catena P,P,P e P tenuto: 4 colpi (182 danni) da 700 mm, fino a circa 790 mm (spinta di p3 da 35 a 24 in `CFG.moves`).
- Controller: lettura protetta (Gamepad API bloccata = nessun controller) e in allenamento il controller che conferma guida G1.
- Touch: menu e ⏸ al rilascio del dito (vanno con il pollice sulla levetta), il dito che scivola fuori da un tasto lo rilascia.
- HUD: il contatore delle combo si azzera all'inizio di un nuovo round. Il tremolio sposta anche il fondale dipinto (tutto lo schermo trema insieme).
- Pausa: "FPS: SÌ / NO".

## Versione "app" per il telefono (7/11/2026)
- `play/` è la versione da installare sul telefono: `tools/make_play.py` (lanciato da `mk.sh`) prende `index.html`, ci mette dentro three.js (niente CDN), le meta per la schermata Home, il manifest (schermo intero, orizzontale), le icone dal ritratto di Ren e `sw.js`, che salva la pagina e i font per giocare offline. Ogni build cambia il nome della cache, così il telefono prende la versione nuova.
- Indirizzo: https://denis3130.github.io/ZebbyFighterz/play/ — GitHub Pages pubblica il ramo `gh-pages` (creato il 7/11/2026 con `git push origin tappa1-basi:gh-pages`, che ha acceso Pages da solo). Per aggiornare l'app: `bash mk.sh`, commit, poi lo stesso push sul ramo `gh-pages`. Il file `.nojekyll` fa servire i file così come sono.
- Su iPhone: Safari → Condividi → "Aggiungi alla schermata Home". La pagina Claude invece resta dentro il sito di Claude (barra in alto) e da File l'html non gira.
- Prova: `python3 tests/play_check.py` (servita in http, senza CDN: manifest, service worker attivo, ricarica offline fino alla lotta).

## Misure Tappa 2a (7/11/2026, Chromium headless con SwiftShader, 844x390)
- Logica e durata del round invariate: KO dopo 1040,2 fotogrammi con hitstop, 988,0 senza (come prima).
- Disegno con sincronizzazione della GPU (`readPixels` a ogni fotogramma, 120 fotogrammi, allenamento con manichino casuale): **da circa 10 ms a circa 27 ms per fotogramma** (prima: commit 74128db, Ren provvisorio). Il Ren Meshy costa circa 9 ms per passaggio (modello e contorno, 30k triangoli con scheletro ciascuno) **nella grafica software**: su un telefono con GPU il costo dei vertici è molto minore, ma va misurato da Denis con "FPS: SÌ". Se scende sotto 60: alleggerire a ~20k triangoli (con i pesi copiati dal vertice più vicino) o un contorno più leggero.
- `tests/perf.test.js` (senza sincronizzazione) resta sui 0,6 ms per fotogramma: misura solo la CPU.

## Note per Denis / per dopo
- Revisione finale Tappa 2a (7/11): Ren a destra è specchiato (si vede di fronte su entrambi i lati); nei colpi a terra i piedi d'appoggio restano fermi (IK) e Ren non si stacca da terra; `hk` usa la clip del calcio alto (il calcio circolare Meshy a207 è girato e in salto, senza piedi a terra: per dopo un calcio circolare a terra). 288 prove verdi.
- Tappa 2a: capelli più a punte come nel disegno (Denis: "non mi piace ma teniamolo così"); rotolata vera (ora `rollF`/`rollB` usano la clip per rialzarsi mentre il corpo scivola); `chp` e `chk` si alzano (anti-aerei) anche se la hitbox resta bassa; la camminata gira circa 5 volte più veloce della clip perché la logica cammina a 4,5 m/s; posa di vittoria (la logica non la usa ancora); Kael di Meshy (modello + scheletro, le stesse animazioni con lo stesso scheletro).
Cose notate nelle revisioni; non costruirle finché Denis non lo chiede.
- Il forte dopo P,P,P combina solo se il quarto P viene premuto (e tenuto) già durante il p3 o al più 2 fotogrammi dopo il suo colpo: più tardi il colpito esce dallo stordimento prima che il forte parta (lo prende come primo colpo di una nuova combo). Dipende dai tempi di p3 e hp, non toccati.
- Con la telecamera molto lontana (16:9 alla massima distanza, super salto) il fondale ha poco margine su un lato: lì il tremolio del fondale è più corto verso quel lato.
- Dopo il super salto l'attaccante supera l'avversario colpito in aria.
- Ogni salto allontana la telecamera: il fondale "respira".
- I lottatori scivolano sulle giunture delle lastre dipinte mentre la telecamera si sposta.
- Il limite di copertura ferma lo zoom del fondale in cima ai salti sul 16:9.
- Gli FPS sul telefono vanno misurati dal menu di pausa ("FPS: SÌ").
- I modelli Meshy di Ren e Kael sono la Tappa 2: prima mostra a Denis saldo e costo stimato, poi procedi solo con il suo ok. `docs/meshy/` non esiste ancora per questo gioco.

## Anteprima 3D di Ren (7/11/2026)
- `viewer.html` (da `mk.sh`, con `src/viewer_head.html` + `src/v_viewer.js` e gli asset in `viewer_assets/`): Ren da solo sulla cascata, si gira col dito, pulsanti per ogni animazione (le stesse pose del gioco: `mdSync` su un lottatore finto), rallentatore, pittura "Disegno"/"Meshy", luce "3D"/"Piatta". Pubblicata su https://claude.ai/artifact/V3vLHuaZbf47o3DYo65jZC.
- Proposta in corso: Ren con il disegno di Denis dipinto sopra (proiezione frontale, `tools/paint_from_drawing.py`; il corpo combacia all'89% col disegno).
- Il "look" scelto da Denis (domande del 7/11: guardia "A pugile", pugni aperti solo nello speciale e nella presa, capelli a punte, faccia pulita; "prima nell'anteprima") è in `CFG.looks.ren`, spento nel gioco e acceso da `v_viewer.js`: guardia `a191` che respira, testa alzata di 12°, 11 punte di capelli dentro la sagoma del disegno, contorno sottile sul davanti della faccia e sulle dita. Dati: `python3 tools/ren_look.py assets/ren viewer_assets/ren docs/ref/personaggi/ren.png`.
- Pugni con le dita vere (7/11): Meshy dà uno scheletro senza dita, quindi `tools/ren_look.py` le trova sul mesh (i rami della distanza dal polso), mette 3 ossa per dito e pollice (Mixamo: `LeftHandIndex1`...) e i pesi della pelle; `modelBuild` le aggiunge allo scheletro, `mdSync` le chiude a pugno e le apre in 5 fotogrammi negli atti di `openHands`. Hanno preso il posto dei pugni modellati (blocchi + morph). Anteprima: render 84 → 79 ms per fotogramma in software (swiftshader), cioè un po' più leggera di prima.
- Il modello che Denis ha fatto sul sito meshy.ai (con le ossa delle dita) non si raggiunge dalla API: vedi `docs/meshy/REN.md`, "Dita".

## Prossimo passo
Denis guarda l'anteprima (pugni con le dita, guardia, capelli, faccia). Se gli piace: accendere `CFG.looks.ren` nel gioco (con i dati del look e la pittura dal disegno dentro `index.html`), ripubblicare gioco e app. Poi: Kael di Meshy (modello dal suo disegno + scheletro; le animazioni si riusano), mostrando prima saldo e costo.
