# Voidrise Fighters · Interfaccia U1 «Dal titolo alla lotta» · Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** il percorso completo intro → titolo → (nome) → menu principale → Gioca → Versus locale / Allenamento → personaggi → arena → VS → **lotta vera** → risultati, nello stile tripla A dei riferimenti `docs/ref/ui/`, a strati animati, su touch, mouse, tastiera e controller.

**Architecture:** file nuovi `src/u*.js` (salvataggio, navigazione, componenti, strati, schermate, ponte) uniti da `mk.sh` al gioco esistente, a partire dal ramo `tappa2-ren-meshy`. I menu sono HTML + CSS sopra il canvas; il motore 3D resta solo per la lotta. La simulazione non viene toccata, tranne due opzioni nuove della partita (round e tempo) salvate nello stato. La grafica dei lottatori segue i personaggi scelti.

**Tech Stack:** JavaScript vanilla ES2019, Three.js r128 (già nel gioco), CSS, Python 3 + Pillow per le immagini, Python 3 + Playwright (Chromium headless) per i test, come il resto del progetto.

**Spec:** `docs/superpowers/specs/2026-11-11-voidrise-interfaccia-design.md` (con la spec della Tappa 1 per la lotta).

## Global Constraints

- Tutti i testi in italiano. Nomi: «VOIDRISE», «Ren», «Kael», «Astra», «Raigon».
- «Niente schermate solo decorative»: ogni pulsante fa qualcosa oppure è **dichiarato** «In arrivo» (lucchetto o avviso). Mai simulare come funzionante ciò che non c'è.
- «Ogni funzione va su touch, mouse e tastiera, e controller». Touch e pulsanti a schermo si attivano al **rilascio** del dito (come `mnTap` oggi).
- «Logica di combattimento deterministica»: nei file `c*_*.js` niente DOM, `Math.random`, `Date`. I file `u*` leggono lo stato della lotta e non lo cambiano (tranne l'avversario del manichino in pausa, come oggi).
- Tutti i numeri dell'interfaccia in `CFG.ui` e `CFG.prog` (file `src/a1_ui_cfg.js`, oggetto `CFG`).
- Telefono solo in orizzontale; zone sicure con `env(safe-area-inset-*)`; pulsanti toccabili di almeno 44 px.
- Immagini dell'interfaccia dentro la pagina: al massimo **3 MB** in tutto (base64); `index.html` sotto i 16 MB.
- Nei menu la lotta 3D non si disegna (gli strati la coprono): niente costo inutile sul telefono.
- Gli effetti non allungano le lotte e gli FPS si misurano prima e dopo (obiettivo 60 su telefono medio).
- Lavoro sul ramo `claude/cool-fermi-fkx4iq`. Non si toccano `gh-pages` né la pagina Claude del gioco: si pubblica una pagina a parte «Voidrise · Interfaccia».

## Review Focus

1. Doppio tocco veloce su un pulsante mentre parte la transizione: atteso un solo cambio di schermata. Test in Task 3 `double tap navigates once`.
2. Memoria del telefono piena o bloccata (`localStorage` che lancia errori): il gioco va avanti, un avviso una volta sola. Test in Task 2 `storage that throws: playable, one toast`.
3. L'app va in background durante il VS: la lotta non parte di nascosto e al ritorno non «salta in avanti». Test in Task 10 `hidden during VS: the fight waits`.
4. Controller staccato nei menu: nessun errore, il fuoco resta dov'è, tastiera e touch continuano. Test in Task 3 `pad unplugged in the menus`.
5. Telefono girato in verticale mentre si scrive il nome: compare «Gira il telefono»; tornati in orizzontale il testo scritto c'è ancora. Test in Task 7 `rotate while typing keeps the name`.

---

## Mappa dei file

| File | Responsabilità | Task |
|---|---|---|
| `src/a1_ui_cfg.js` | `CFG.ui`, `CFG.prog` | 1 |
| `build.py` | `.webp` tra le immagini; `<!--include:FILE-->` nella testa incolla `src/FILE` | 1 |
| `src/u_style.css` | stile dell'interfaccia (colori, caratteri, componenti, schermate, transizioni) | 1, 4-11 |
| `src/u0_save.js` | salvataggio versionato e migrazione da `voidrise.prefs` | 2 |
| `src/u7_prog.js` | XP della partita, livello profilo, statistiche (parte U1) | 2 |
| `src/u1_nav.js` | schermate, pila, fuoco 2D, input dei menu, `uiTap` | 3 |
| `src/u2_comp.js` | componenti riusabili, avvisi, conferma | 4 |
| `tools/make_ui_assets.py`, `assets/ui/*.webp` | immagini segnaposto a strati | 5 |
| `src/u3_layers.js` | scena a strati, parallasse, particelle, qualità | 5 |
| `src/u4_intro.js` | intro, titolo, nome | 6, 7 |
| `src/u5_play.js` | menu principale, Gioca, impostazioni Versus, personaggi, arena, VS, risultati | 8-11 |
| `src/u9_bridge.js` | ponte verso la lotta, `uiEvents` | 10 |
| `src/c1_sim.js` | opzioni `rounds` e `timeS` nello stato | 8 |
| `src/d_render.js`, `src/g_hud.js` | lottatori e ritratti secondo i personaggi scelti | 10 |
| `src/h_menu.js` | pausa, orientamento, FPS, visibilità sul nuovo sistema; via titolo e fine partita vecchi | 3, 10, 11 |
| `src/head.html` | font, include dello stile, radice `#ui` ripulita | 1, 3 |
| `src/z_main.js` | boot verso l'intro, `uiFrame` nel ciclo, `uiEvents` nel passo, `__VF` | 1, 3, 5, 10 |
| `mk.sh` | `FILES` con i file nuovi | 1 |
| `tests/ui_*.test.js`, `tests/lib.js`, `tests/menu.test.js`, `tests/orient.test.js` | prove | tutti |
| `docs/HANDOFF-UI.md`, `CLAUDE.md` | stato, comandi, link della pagina | 12 |

Ordine di `FILES`: `a0_cfg.js a1_ui_cfg.js c1_sim.js c2_moves.js c3_dummy.js b_input.js d_render.js e_poses.js e_fighter3d.js e_model.js f_fx.js g_hud.js u0_save.js u7_prog.js u1_nav.js u2_comp.js u3_layers.js u4_intro.js u5_play.js u9_bridge.js h_menu.js z_main.js` (i file non ancora creati entrano nel task che li crea).

## Valori di partenza

```js
// src/a1_ui_cfg.js
Object.assign(CFG, {
  ui: {
    t: {go: 420, stagger: 40, toast: 2400, bump: 220, tapGuard: 350},   // ms: transizione, ritardo a cascata, avviso, rimbalzo, doppio tocco ignorato
    repeat: [350, 130],                                                   // controller tenuto nei menu: primo ripeti, poi ogni
    intro: {len: 7000, firstSkipAfter: 0},                                // intro 7 s; «Salta» subito
    vs: {minMs: 2500, tapAfterMs: 600},
    par: {sky: .12, ruins: .35, fog: .6, hero: 1, step: 28},             // parallasse: fattore per strato, px per passo di navigazione
    q: {lowCores: 4, lowMem: 3, parts: {bassa: 0, media: 36, alta: 80}},
    name: {min: 3, max: 16, re: "^[A-Za-z0-9À-ÖØ-öø-ÿ _-]+$", pool: ['Lama', 'Brace', 'Vento', 'Corvo', 'Ombra', 'Falco', 'Tuono', 'Cenere']},
    chars: {
      ren:    {name: 'Ren',    pot: 4, vel: 3, dif: 2, hue: '#2f8f86'},
      kael:   {name: 'Kael',   pot: 3, vel: 4, dif: 3, hue: '#8f6ad8'},
      astra:  {name: 'Astra',  lock: 'Pass gratuito · livello 50'},
      raigon: {name: 'Raigon', lock: 'Pass Premium · livello 50'},
    },
    roster: ['ren', 'kael', 'astra', 'raigon', null, null, null, null, null, null, null, null],   // null = «In arrivo»
    arenas: [{id: 'cascata', name: 'La Grande Cascata', ok: true}, {id: 'rovine', name: "Rovine dell'acquedotto"},
             {id: 'montagne', name: 'Montagne'}, {id: 'tetti', name: 'Tetti della città'}, {id: 'foresta', name: 'Foresta'}, {id: 'deserto', name: 'Deserto'}],
    lines: {'ren>kael': ['Non mi tirerò indietro.', 'Allora dimostralo.'], 'kael>ren': ['Sei ancora in piedi?', 'Abbastanza per batterti.']},
    vsOpts: {rounds: [1, 3, 5], r: 1, time: [60, 90, 99, 0], tm: 2},   // indici dei valori iniziali (3 round, 99 s); tempo 0 = ∞
  },
  prog: {xp: {played: 60, win: 40, round: 10}, levelXp: 1000},
});
```

## Interfacce condivise

- `SV` (oggetto salvato, chiave `voidrise.save`, `v:1`): `{v, name, introSeen, xp, lastChar, stats:{played, won, lost, draw, rounds, hits, maxCombo, timeS, byChar:{<char>:{played, won}}}, settings:{quality:'auto'|'bassa'|'media'|'alta', fpsCap:60, showFps:false}}`.
- Schermata: `navRegister({id, build(root), enter(params, isBack), leave(), back(), tab(d), scene})` → la radice è `<section class="usc" id="sc-<id>">` dentro `#uiScreens`. `back()` che restituisce `false` blocca il ritorno. `scene` = nome della scena a strati.
- `NAV = {cur, stack:[{id, params, focus}], screens, focus, dev:'kb'|'touch'|'pad', padIx, pad:[], tapEnd, busyUntil}`.
- Elementi con il fuoco: qualunque elemento con `data-focus` visibile nella schermata (o nella finestra sopra). Conferma = `el.uiAct(dev)`.
- Partita: `bridgeStart({mode:'versus'|'training', chars:[c0,c1], arena, rounds, timeS, dev})`; risultato `bridgeResult(S) -> {mode, chars, winner, wins:[a,b], rounds, hits:[a,b], maxCombo:[a,b], timeS}`.
- `startMatch(mode, {seed, dummy, chars, rounds, timeS})`: i valori mancanti come oggi (`['ren','kael']`, `CFG.round`).
- `G.state` resta `'title'` in tutti i menu (intro compresa), `'fight'`, `'pause'`, `'end'` (risultati): il runner dei test attende ancora `'title'`.
- `window.__VF` aggiunge: `UI` (= `{NAV, SV, LY, INTRO, UIB}`), `navRegister, navGo, navBack, navReset, navReplace, navMove, navPress, navTab, navFocus, navPadPoll, uiFrame, saveDefaults, saveLoad, saveWrite, progMatchXp, progAddXp, progLevel, progRecord, cBtn, cItem, cCard, cTabs, cStepper, cChip, uiToast, uiConfirm, layersSet, layersShift, layersFrame, layersQuality, introAt, introSkip, bridgePreload, bridgeStart, bridgeResult, renderCast, F3D_BY`.
- I test che aspettano una `Promise` (caricamento del VS, finestra di conferma) restituiscono una `Promise`: `T.run` la attende (Task 4). Tra due microtask il ciclo `requestAnimationFrame` non gira, quindi le prove restano deterministiche.

---

### Task 1: Base: ramo, build, stile e configurazione

**Files:**
- Branch: `git merge origin/tappa2-ren-meshy` in `claude/cool-fermi-fkx4iq` (nessun conflitto atteso: qui ci sono solo documenti)
- Create: `src/a1_ui_cfg.js` (valori sopra), `src/u_style.css` (solo le variabili per ora), `tests/ui_base.test.js`
- Modify: `build.py` (`.webp` in `MIME`; nella testa ogni `<!--include:NOME-->` diventa `<style>` + `src/NOME` + `</style>`), `src/head.html` (font e include), `mk.sh` (`a1_ui_cfg.js` in `FILES`)

**Interfaces:**
- Produces: `CFG.ui`, `CFG.prog`; variabili CSS `--u-bg:#14121b --u-panel:rgba(20,17,28,.74) --u-line:rgba(216,166,87,.38) --u-gold:#d8a657 --u-gold2:#f3d6a0 --u-orange:#f08a32 --u-ink:#efe8dc --u-dim:#a59db3 --u-violet:#8f6ad8 --u-teal:#2f8f86 --u-red:#d4513f`; caratteri `--u-display:'Cinzel',Georgia,serif` (logo, titoli, numeri) e `--u-serif:'Cormorant Garamond',Georgia,serif` (voci, sottotitoli, corsivo).

- [ ] **Step 1: prima misura e test di partenza** — `bash mk.sh` deve stampare `SYNTAX_OK`; lancia la serie completa di `docs/HANDOFF.md` («Build e test») e annota in `docs/HANDOFF-UI.md` (nuovo) quanti test passano. Misura il costo per fotogramma nei menu oggi: `python3 tests/run.py tests/perf.test.js --viewport 844x390` (righe `INFO`) e annota.
- [ ] **Step 2: test** — `tests/ui_base.test.js`:
```js
T.test('ui config is in CFG', () => { T.eq(__VF.CFG.ui.roster.length, 12); T.eq(__VF.CFG.ui.arenas[0].id, 'cascata'); T.eq(__VF.CFG.prog.levelXp, 1000); });
T.test('ui style is in the page', () => { T.eq(getComputedStyle(document.documentElement).getPropertyValue('--u-gold').trim(), '#d8a657'); });
T.test('webp assets are embedded as data URIs', () => { const k = Object.keys(__VF.ASSETS).find(k => k.endsWith('.webp')); T.ok(k, 'no webp'); T.ok(__VF.ASSETS[k].startsWith('data:image/webp;base64,')); });
```
Per il terzo test serve un `.webp` in `assets/ui/`: per ora `assets/ui/probe.webp` (1×1, fatto con Pillow), tolto nel Task 5.
- [ ] **Step 3: verifica che fallisca** — `bash mk.sh && python3 tests/run.py tests/ui_base.test.js` → FAIL.
- [ ] **Step 4: implementazione** — come in Files. Google Fonts: aggiungi `family=Cinzel:wght@500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600` al link esistente.
- [ ] **Step 5: verifica** — `bash mk.sh && python3 tests/run.py tests/ui_base.test.js && python3 tests/run.py tests/smoke.test.js` → tutti PASS.
- [ ] **Step 6: commit** — `git add -A && git commit -m "Interfaccia U1: base, stile e configurazione"`

### Task 2: Salvataggio, XP e statistiche

**Files:**
- Create: `src/u0_save.js`, `src/u7_prog.js`, `tests/ui_save.test.js`
- Modify: `mk.sh`, `src/z_main.js` (`__VF`)

**Interfaces:**
- Produces:
  - `saveDefaults() -> SV`; `saveLoad() -> SV` (riempie `SV`; dati assenti, rotti o di un'altra versione → valori iniziali; se c'è `voidrise.prefs` con `fps:true` porta `settings.showFps = true`); `saveWrite() -> boolean` (in `try`; al primo fallimento della sessione `uiToast('Impossibile salvare i progressi su questo dispositivo', 'err')` se `uiToast` esiste).
  - `progLevel(xp) -> {lvl, into, need}` con `lvl = 1 + floor(xp / levelXp)`.
  - `progMatchXp(r) -> {xp, parts:[{label, xp}]}`: `played` sempre, `win` se `r.winner === 0`, `round` per ogni round vinto dal lato 0; etichette «Incontro giocato», «Vittoria», «Round vinti ×N».
  - `progAddXp(sv, xp) -> {before, after}` (livelli prima e dopo).
  - `progRecord(sv, r)`: aggiorna `stats` per il lato 0 (il G1): played, won/lost/draw, rounds, hits, maxCombo, timeS, byChar.
  - Allenamento: niente XP né statistiche (`progMatchXp` non viene chiamata).

- [ ] **Step 1: test** — `tests/ui_save.test.js`:
```js
const K = 'voidrise.save';
T.test('defaults when nothing is saved', () => { localStorage.removeItem(K); const s = __VF.saveLoad(); T.eq(s.v, 1); T.eq(s.xp, 0); T.eq(s.name, null); T.eq(s.settings.quality, 'auto'); });
T.test('round trip', () => { const s = __VF.saveLoad(); s.name = 'Lama'; s.xp = 1500; T.ok(__VF.saveWrite()); T.eq(__VF.saveLoad().name, 'Lama'); T.eq(__VF.saveLoad().xp, 1500); });
T.test('broken or old data: defaults', () => { localStorage.setItem(K, '{rotto'); T.eq(__VF.saveLoad().xp, 0); localStorage.setItem(K, JSON.stringify({v: 99, xp: 5})); T.eq(__VF.saveLoad().xp, 0); });
T.test('old FPS preference is carried over', () => { localStorage.removeItem(K); localStorage.setItem('voidrise.prefs', JSON.stringify({v: 1, fps: true})); T.eq(__VF.saveLoad().settings.showFps, true); localStorage.removeItem('voidrise.prefs'); });
T.test('storage that throws: playable, one toast', () => { const own = Object.getOwnPropertyDescriptor(window, 'localStorage'); let n = 0; const t = window.uiToast; window.uiToast = () => n++;
  Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('denied', 'SecurityError'); }, configurable: true});
  try { T.eq(__VF.saveLoad().xp, 0); T.eq(__VF.saveWrite(), false); T.eq(__VF.saveWrite(), false); T.eq(n <= 1, true); }
  finally { if (own) Object.defineProperty(window, 'localStorage', own); else delete window.localStorage; window.uiToast = t; } });
T.test('levels from XP', () => { T.eq(__VF.progLevel(0).lvl, 1); T.eq(__VF.progLevel(999).lvl, 1); T.eq(__VF.progLevel(1000).lvl, 2); T.eq(__VF.progLevel(1250).into, 250); });
T.test('match XP: played + win + rounds', () => { const r = {mode: 'versus', chars: ['ren', 'kael'], winner: 0, wins: [2, 1], hits: [20, 9], maxCombo: [5, 3], timeS: 120};
  const x = __VF.progMatchXp(r); T.eq(x.xp, 60 + 40 + 20); T.eq(x.parts.length, 3); T.eq(__VF.progMatchXp(Object.assign({}, r, {winner: 1, wins: [0, 2]})).xp, 60); });
T.test('record: stats of G1 and level up', () => { const s = __VF.saveDefaults(); s.xp = 950; const r = {mode: 'versus', chars: ['kael', 'ren'], winner: 0, wins: [2, 0], hits: [14, 3], maxCombo: [6, 2], timeS: 80};
  __VF.progRecord(s, r); const up = __VF.progAddXp(s, __VF.progMatchXp(r).xp); T.eq(s.stats.won, 1); T.eq(s.stats.byChar.kael.won, 1); T.eq(s.stats.maxCombo, 6); T.eq(up.before, 1); T.eq(up.after, 2); });
```
- [ ] **Step 2: verifica che fallisca** — `bash mk.sh && python3 tests/run.py tests/ui_save.test.js` → FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces; `saveLoad` unisce ai valori iniziali in profondità, così le chiavi aggiunte dopo hanno un valore.
- [ ] **Step 4: verifica** — stesso comando → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: salvataggio, XP e statistiche"` (con `git add` dei file nuovi)

### Task 3: Navigazione unica (tastiera, mouse, touch, controller) e pausa portata

**Files:**
- Create: `src/u1_nav.js`, `tests/ui_nav.test.js`
- Modify: `src/h_menu.js` (via `MN_SCREENS`, `showScreen`, `mnFocus`, `mnButtons`, `menuMove`, i tasti dei menu in `menuInit` e il polling dei menu in `menuPad`; resta: `menu`, `menuSync`, orientamento, FPS, visibilità, controller staccato, schermo intero; `mnTap` diventa `uiTap` in `u1_nav.js`), `src/head.html` (in `#ui` via `#title`, `#pause`, `#end`; nuovo `<div id="uiScreens">`, `<div id="uiOver">` per finestre e avvisi, `<div id="uiBlade">`), `src/z_main.js`, `tests/menu.test.js`, `tests/lib.js`

**Interfaces:**
- Consumes: `SV`, `inputMaskHeld()`, `inputPadList()`, `menu`, `G`.
- Produces: `navRegister(def)`, `navGo(id, params)`, `navBack()`, `navReplace(id, params)`, `navReset(id, params)` (svuota la pila), `navMove('up'|'down'|'left'|'right')`, `navPress(dev)`, `navTab(-1|1)`, `navPadPoll(now)`, `navFocus(el)`, `uiTap(el, fn)`.
  - Fuoco 2D: tra gli elementi `data-focus` visibili, il più vicino nella direzione (distanza lungo la direzione + 2 × distanza di lato, tra i centri); nessuno → il fuoco resta. Un contenitore `data-wrap` fa il giro (ultimo → primo) sulla sua colonna o riga.
  - Il fuoco ha la classe `f`; il mouse che passa sopra sposta il fuoco; il tocco no (solo al rilascio: fuoco + conferma).
  - Tasti: frecce e WASD muovono; Invio, Spazio, J confermano; Esc e Backspace (non dentro un campo di testo) tornano indietro; Q/E e PagSu/PagGiù = `navTab`. Controller: croce e levetta (ripetizione `CFG.ui.repeat`), A conferma, B indietro, LB/RB `navTab`, Start in lotta = pausa (come oggi).
  - Ogni pressione aggiorna `NAV.dev` (`'kb'`, `'touch'`, `'pad'`) e `NAV.padIx`; il dispositivo passa a `bridgeStart` («chi conferma è G1»).
  - `navGo` è sincrono (la schermata nuova ha `on` subito); la transizione è solo CSS: classe `go` rimessa su `#uiBlade` e `--i` sugli elementi per la cascata. Per `CFG.ui.t.tapGuard` ms dopo un cambio di schermata le conferme col **puntatore** (tocco e clic) sono ignorate (doppio tocco, doppio clic); tastiera e controller no.
  - `navBack()` sulla prima schermata della pila non fa nulla.
- Pausa nel nuovo sistema: schermata `pause` con «Riprendi», «Ricomincia», «Avversario: Fermo/Casuale» (solo allenamento), «FPS: Sì/No», «Abbandona» (conferma, poi menu principale). `menu.pause()` → `G.state='pause'` e `navGo('pause')`; `menu.resume()` → toglie la schermata. `menu.toTitle()` → `navReset('menu')` (il titolo con «Tocca per iniziare» solo all'avvio).

- [ ] **Step 1: test** — `tests/ui_nav.test.js` (registra 3 schermate di prova con pulsanti `data-focus` in griglia 2×2, poi le toglie):
```js
T.test('go, back and the focus returns where it was', () => { __VF.navReset('tA'); keyTap('ArrowRight'); T.eq(focused(), 'A2'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'tB'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'tA'); T.eq(focused(), 'A2'); });
T.test('2D focus picks the nearest in the direction and stops at the edge', () => { __VF.navReset('tA'); keyTap('ArrowDown'); T.eq(focused(), 'A3'); keyTap('ArrowDown'); T.eq(focused(), 'A3'); keyTap('ArrowRight'); T.eq(focused(), 'A4'); });
T.test('data-wrap wraps', () => { __VF.navReset('tC'); keyTap('ArrowUp'); T.eq(focused(), 'C3'); });
T.test('mouse hover focuses, click confirms', () => { __VF.navReset('tA'); hover('A4'); T.eq(focused(), 'A4'); uiClick('A4'); T.eq(__VF.UI.NAV.cur, 'tB'); });
T.test('touch confirms on release only', () => { __VF.navReset('tA'); const b = byText('A2'); ptr(b, 'pointerdown', 7); T.eq(__VF.UI.NAV.cur, 'tA'); ptr(b, 'pointerup', 7); T.eq(__VF.UI.NAV.cur, 'tB'); T.eq(__VF.UI.NAV.dev, 'touch'); });
T.test('double tap navigates once', () => { const g = __VF.CFG.ui.t.tapGuard; __VF.CFG.ui.t.tapGuard = 350; try { __VF.navReset('tA'); const n = __VF.UI.NAV.stack.length; tapEl(byText('A2'), 8); tapEl(byText('B1'), 9); T.eq(__VF.UI.NAV.stack.length, n + 1); } finally { __VF.CFG.ui.t.tapGuard = g; } });
T.test('pad: d-pad moves, A confirms, B goes back, the pad is the device', () => { __VF.navReset('tA'); padsAt([{buttons: {15: 1}}]); padTick(); padsAt([{}]); padTick(); T.eq(focused(), 'A2');
  padsAt([{buttons: {0: 1}}]); padTick(); T.eq(__VF.UI.NAV.cur, 'tB'); T.eq(__VF.UI.NAV.dev, 'pad'); padsAt([{}]); padTick(); padsAt([{buttons: {1: 1}}]); padTick(); T.eq(__VF.UI.NAV.cur, 'tA'); fakePads([]); padTick(); });
T.test('pad unplugged in the menus', () => { __VF.navReset('tA'); padsAt([{}]); padTick(); fakePads([]); window.dispatchEvent(new Event('gamepaddisconnected')); padTick(); keyTap('ArrowRight'); T.eq(focused(), 'A2'); T.eq(__VF.G.state, 'title'); });
T.test('Q/E and LB/RB call the screen tab()', () => { __VF.navReset('tB'); keyTap('KeyE'); T.eq(window.__tabs, 1); padsAt([{buttons: {4: 1}}]); padTick(); T.eq(window.__tabs, 0); fakePads([]); padTick(); });
T.test('back on the first screen does nothing', () => { __VF.navReset('tA'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'tA'); });
```
In `tests/lib.js` metti `__VF.CFG.ui.t.tapGuard = 0` appena caricato (le prove cliccano di fila; solo `double tap navigates once` la riaccende) e aggiungi: `keyTap(code)` (key + keyUp), `focused()` (testo dell'elemento col fuoco), `byText(t)` (elemento `data-focus` visibile che contiene `t`; se in `#uiOver` c'è una finestra aperta cerca prima lì), `uiClick(t)` (click su `byText(t)`), `hover(t)` (`pointermove` del mouse). Riscrivi `tests/menu.test.js` sul nuovo sistema con gli stessi intenti (pausa e ripresa con Esc, Start e ⏸; la pausa ferma la sim; avversario in allenamento; scheda nascosta senza recupero; ricomincia; controller staccato in lotta; ciclo a passi fissi; tasto di conferma tenuto che non attacca; FPS Sì/No ricordato) usando `__VF.bridgeStart` al posto del titolo vecchio (fino al Task 10: `__VF.startMatch`).
- [ ] **Step 2: verifica che fallisca** — `bash mk.sh && python3 tests/run.py tests/ui_nav.test.js` → FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces. Schermate di prova registrate solo dal test (`__VF.navRegister`).
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/ui_nav.test.js && python3 tests/run.py tests/menu.test.js && python3 tests/run.py tests/touch.test.js --viewport 844x390 --touch --mobile` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: navigazione unica e pausa nel nuovo sistema"`

### Task 4: Componenti

**Files:**
- Create: `src/u2_comp.js`, `tests/ui_comp.test.js`
- Modify: `src/u_style.css`, `mk.sh`

**Interfaces:**
- Consumes: `uiTap`, `navFocus`, `NAV`.
- Produces (ognuno restituisce l'elemento; quelli con `act` hanno `data-focus` e `el.uiAct(dev)`):
  - `cLogo(size:'s'|'l')` — «VOIDRISE» in Cinzel spaziato con la falce dorata sottile dietro la «O».
  - `cHead(title, sub)` — barra arancione verticale, titolo, sottotitolo corsivo, linea sfumata sotto.
  - `cBtn({label, act, kind:'main'|'line'|'small', icon, locked, note})` — parallelogramma (`skewX(-18deg)`), bordo oro sottile, fondo scuro; `main` con pennellata arancione in basso a destra; fuoco = bordo oro chiaro, bagliore, lama di luce che scorre una volta; premuto = `scale(.95)`. `locked` = lucchetto, testo attenuato, conferma → `uiToast(note || 'In arrivo', 'soon')`.
  - `cItem({label, act, locked, note})` — voce di menu testuale (corsivo grande): col fuoco cresce, diventa oro chiaro, barra arancione a sinistra e pennellata dietro.
  - `cCard({label, img, act, locked, note, badge})` — immagine, etichetta corsiva in basso, cornice oro; col fuoco cornice arancione e leggero zoom dell'immagine.
  - `cTabs(labels, i, onPick)`, `cStepper({label, values, i, fmt, onChange})` (‹ valore ›; sinistra/destra col fuoco cambiano il valore), `cStatBar(label, n, max)` (tacche), `cProgress(frac)`, `cChip()` (avatar, nome, «Liv. N»), `cBack()` («‹ Indietro» in alto a sinistra, chiama `navBack`).
  - `uiToast(text, kind:'info'|'soon'|'err')` — riquadro `#uiToast` in alto al centro, sparisce dopo `CFG.ui.t.toast`; uno alla volta (il nuovo sostituisce il vecchio).
  - `uiConfirm({title, text, yes, no}) -> Promise<boolean>` — finestra in `#uiOver`; il fuoco resta dentro la finestra; Esc/B = no; al termine il fuoco torna dove era.

- [ ] **Step 1: test** — `tests/ui_comp.test.js` (monta i componenti in una schermata di prova):
```js
T.test('locked button: no action, a «In arrivo» toast', () => { let n = 0; mount([__VF.cBtn({label: 'Online', act: () => n++, locked: true})]); uiClick('Online'); T.eq(n, 0); T.ok(vis('uiToast')); T.ok(txt('uiToast').includes('In arrivo')); });
T.test('button act gets the device', () => { let d; mount([__VF.cBtn({label: 'Vai', act: dev => d = dev})]); keyTap('Enter'); T.eq(d, 'kb'); });
T.test('stepper changes with left/right while focused', () => { let v; mount([__VF.cStepper({label: 'Round', values: [1, 3, 5], i: 1, onChange: x => v = x})]); keyTap('ArrowRight'); T.eq(v, 5); keyTap('ArrowRight'); T.eq(v, 5); T.ok(txt('sc-uiMount').includes('5')); });
T.test('confirm: focus trapped, Esc says no, focus restored', () => { mount([__VF.cBtn({label: 'Abbandona', act: () => {}}), __VF.cBtn({label: 'Altro', act: () => {}})]); keyTap('ArrowDown'); let r = null;
  __VF.uiConfirm({title: 'Abbandonare?', text: 'La partita andrà persa.', yes: 'Abbandona', no: 'Annulla'}).then(x => r = x); keyTap('ArrowUp'); T.ok(focused() === 'Annulla' || focused() === 'Abbandona');
  keyTap('Escape'); return Promise.resolve().then(() => { T.eq(r, false); T.eq(focused(), 'Altro'); }); });
T.test('tabs call onPick and tab() moves them', () => { let p = -1; mount([__VF.cTabs(['Audio', 'Grafica'], 0, i => p = i)]); keyTap('KeyE'); T.eq(p, 1); });
T.test('chip shows name and level', () => { __VF.UI.SV.name = 'Lama'; __VF.UI.SV.xp = 3100; mount([__VF.cChip()]); T.ok(txt('sc-uiMount').includes('Lama')); T.ok(txt('sc-uiMount').includes('Liv. 4')); });
```
`mount(list)` (in `tests/lib.js`) registra e apre la schermata di prova `uiMount` (radice `#sc-uiMount`) con gli elementi dati. Il test asincrono: `T.run` attende una `Promise` restituita da un test (aggiungi `await` in `T.run` solo per i test che la restituiscono; gli altri restano sincroni).
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — DOM creato in JS; tutto lo stile in `u_style.css`. Animazioni solo con `transform` e `opacity`.
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/ui_comp.test.js` → PASS. Poi una pagina di prova dei componenti: `__VF.navReset('uiMount')` con un pulsante per tipo, screenshot a 844×390 (`deviceScaleFactor` 1) e confronto a occhio con `docs/ref/ui/01-*.png` e `03-*.png` (pulsanti «Conferma», «Riprendi», carte, linguette): correggi spessori, inclinazione e colori finché sono vicini.
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: componenti"`

### Task 5: Immagini segnaposto e scena a strati

**Files:**
- Create: `tools/make_ui_assets.py`, `assets/ui/*.webp` (via `probe.webp`), `src/u3_layers.js`, `tests/ui_layers.test.js`, `tests/ui_perf.test.js`
- Modify: `src/u_style.css`, `src/head.html` (`<div id="uiLayers">` sotto `#uiScreens`), `src/z_main.js` (`tick`: con `G.state` `'title'` o `'end'` chiama `uiFrame(now)` e non `renderFrame`), `src/u1_nav.js` (aggancio agli strati), `mk.sh`

**Interfaces:**
- `tools/make_ui_assets.py` (Pillow, WebP qualità 82) scrive in `assets/ui/`:
  - `sky.webp` 1280×720: cielo al tramonto disegnato (sfumatura viola → arancione all'orizzonte, sole, 3 fasce di nuvole scure);
  - `ruins.webp` 1600×900 con trasparenza: `docs/ref/sfondo-rovine.png` senza il cielo (pixel azzurri sopra la linea delle rovine resi trasparenti, bordo sfumato 3 px), portato al tramonto (moltiplica viola `#5a4a78`, luce arancione dal basso al centro, contrasto ridotto);
  - `fog1.webp`, `fog2.webp` 1600×300: fasce di nebbia (rumore sfocato, alfa 0-0.55);
  - `ren_full.webp`, `kael_full.webp` (altezza 900): da `docs/ref/personaggi/ren.png` e `kael.png`, sfondo grigio tolto (distanza dal colore dei 4 angoli < 26 → trasparente, bordo sfumato 2 px);
  - `face_ren.webp`, `face_kael.webp` 256×256 (testa dalle schede), `face_astra.webp`, `face_raigon.webp` 256×256 (da `docs/ref/ui/04-*.png`, riquadro del pass), `silhouette.webp` 256×256 (sagoma di `ren_full` riempita `#1c1826` con bordo `#3a3248`);
  - `arena_cascata.webp`, `arena_rovine.webp` 640×360 (dagli sfondi), `arena_montagne/tetti/foresta/deserto.webp` 320×180 (dalle miniature di `docs/ref/ui/01-*.png`);
  - `intro_clash.webp` 1280×720 (riquadro dello scontro in `docs/ref/ui/00-*.png`, senza la scritta «Salta»: ritaglio sopra).
  - Stampa le dimensioni in KB; fallisce se il totale supera 2,2 MB (il base64 resta sotto 3 MB).
- `navGo`/`navBack`/`navReset` chiamano `layersSet(def.scene, …)` della schermata nuova e `layersShift(+1)` andando avanti, `layersShift(-1)` tornando indietro: gli strati scivolano a velocità diverse a ogni cambio.
- `LY = {scene, parts:[], q, settle()}`: `parts` = particelle vive; `settle()` porta subito la parallasse alla posizione finale (per i test).
- `layersInit()`; `layersSet(scene, o)` con `scene` tra `'menu' | 'title' | 'select' | 'vs' | 'results' | 'off'`, `o = {hero:'ren'|'kael', rival, arena}`: sceglie quali strati mostrare e dove stanno i personaggi; `layersShift(dir)` (parallasse a ogni cambio di schermata: `-1`/`+1`); `layersFrame(now)` (particelle su un `<canvas id="uiParts">` 2D, braci arancioni che salgono, numero da `CFG.ui.q.parts`); `layersQuality(q)` (`'bassa'` toglie nebbia animata, respiro e particelle); `uiFrame(now)` = `layersFrame` + aggiornamenti dei menu.
- Animazioni CSS: nuvole che scorrono (120 s), nebbia (40 s e 65 s in versi opposti), stendardi assenti nei segnaposto, respiro dei personaggi (`scale` 1→1,012 in 4 s), luce di bordo (`drop-shadow` arancione per Ren, viola per Kael, che pulsa).
- Qualità `'auto'` al primo avvio: `'media'` se `navigator.hardwareConcurrency <= 4` o `navigator.deviceMemory <= 3`, altrimenti `'alta'`; salvata in `SV.settings.quality`.
- `#uiLayers` nascosto (`display:none`) quando `G.state` è `'fight'` o `'pause'`: le animazioni CSS si fermano e non costano nulla in lotta. Con `G.state` `'title'` o `'end'` (menu e risultati, coperti dagli strati) `tick` non chiama `renderFrame`.

- [ ] **Step 1: immagini** — `python3 tools/make_ui_assets.py` → elenco con i KB e totale ≤ 2,2 MB. Guarda ogni immagine (Read) e controlla: personaggi senza alone grigio, rovine senza cielo azzurro rimasto.
- [ ] **Step 2: test** — `tests/ui_layers.test.js`:
```js
T.test('menu scene shows sky, ruins, fog and the hero', () => { __VF.layersSet('menu', {hero: 'ren'}); for (const id of ['lySky', 'lyRuins', 'lyFog1', 'lyHero']) T.ok(vis(id), id); });
T.test('a shift moves the far layers less than the near ones', () => { __VF.layersSet('menu', {hero: 'ren'}); const x = id => new DOMMatrix(getComputedStyle($(id)).transform).e; const a = [x('lySky'), x('lyHero')]; __VF.layersShift(1); __VF.UI.LY.settle(); T.ok(Math.abs(x('lySky') - a[0]) < Math.abs(x('lyHero') - a[1])); });
T.test('quality bassa: no particles, no fog animation', () => { __VF.layersQuality('bassa'); __VF.layersFrame(performance.now()); T.eq(__VF.UI.LY.parts.length, 0); T.eq(getComputedStyle($('lyFog1')).animationName, 'none'); __VF.layersQuality('alta'); });
T.test('hidden during a fight, back in the menus', () => { __VF.startMatch('training', {seed: 1}); T.ok(!vis('uiLayers')); __VF.menu.toTitle(); T.ok(vis('uiLayers')); });
T.test('UI images stay under 3 MB in the page', () => { const n = Object.entries(__VF.ASSETS).filter(([k]) => k.startsWith('ui/') && k.endsWith('.webp')).reduce((a, [, v]) => a + v.length, 0); T.info('ui images ' + (n / 1e6).toFixed(2) + ' MB'); T.ok(n < 3e6); });
T.test('menus do not draw the 3D scene', () => { __VF.menu.toTitle(); const n = __VF.renderer.info.render.frame; __VF.tick(performance.now()); T.eq(__VF.renderer.info.render.frame, n); });
```
`tests/ui_perf.test.js`: con `T.info`, ms medi di `__VF.tick` su 300 chiamate nei menu (qualità alta e bassa) e in lotta.
- [ ] **Step 3: verifica che fallisca** — FAIL.
- [ ] **Step 4: implementazione** — come nelle Interfaces; togli `assets/ui/probe.webp` e aggiorna il test del Task 1 su `ui/sky.webp`.
- [ ] **Step 5: verifica** — `bash mk.sh && python3 tests/run.py tests/ui_layers.test.js && python3 tests/run.py tests/ui_perf.test.js --viewport 844x390` → PASS; annota i ms in `docs/HANDOFF-UI.md` (prima: valori del Task 1). Screenshot della scena `menu` a 844×390: confronto con `docs/ref/ui/00-*.png` (riquadro 3).
- [ ] **Step 6: commit** — `git add -A && git commit -m "Interfaccia U1: immagini segnaposto e scena a strati animata"`

### Task 6: Intro

**Files:**
- Create: `src/u4_intro.js`, `tests/ui_intro.test.js`
- Modify: `src/u_style.css`, `src/z_main.js` (`boot`: dopo `renderInit` `G.state='title'` e `navReset('intro')`), `mk.sh`

**Interfaces:**
- `INTRO = {t0, playing}`; `introAt(ms)` mette la scena nello stato del tempo `ms` (pura funzione del tempo: classi e variabili CSS), `introSkip()`, schermata `intro` (con `cBtn` «Salta» in basso a destra). Alla fine (`CFG.ui.intro.len`) o a «Salta» → `navReset('title')`; `SV.introSeen = true`.
- Inquadrature (ms): 0-600 nero con braci; 600-2000 Ren entra da sinistra (`ren_full`, da fuori schermo a 30% con linee di velocità e polvere); 2000-3200 Kael entra da destra; 3200-3700 stretta: zoom 1→1,25 su tutti e due; 3700 **impatto**: lampo bianco 120 ms, anello d'urto che si allarga, tremolio 400 ms, sassi; 3700-5000 rallentatore su `intro_clash` con polvere; 5000-5600 bianco; 5600-7000 il logo si forma (lettere che appaiono con la falce dorata che taglia) → titolo.
- Dalla seconda volta (`SV.introSeen`) anche un tocco ovunque, un tasto o A saltano.

- [ ] **Step 1: test** — `tests/ui_intro.test.js`:
```js
T.test('boot shows the intro first', () => { T.eq(__VF.UI.NAV.cur, 'intro'); T.eq(__VF.G.state, 'title'); });
T.test('shots in order', () => { __VF.introAt(1000); T.ok($('sc-intro').classList.contains('s-ren')); __VF.introAt(3800); T.ok($('sc-intro').classList.contains('s-impact')); __VF.introAt(6000); T.ok($('sc-intro').classList.contains('s-logo')); });
T.test('the end goes to the title and remembers it', () => { __VF.introAt(__VF.CFG.ui.intro.len + 1); T.eq(__VF.UI.NAV.cur, 'title'); T.eq(__VF.UI.SV.introSeen, true); });
T.test('Salta skips', () => { __VF.navReset('intro'); uiClick('Salta'); T.eq(__VF.UI.NAV.cur, 'title'); });
T.test('first time: a tap elsewhere does not skip; later it does', () => { __VF.UI.SV.introSeen = false; __VF.navReset('intro'); tapEl($('sc-intro'), 3); T.eq(__VF.UI.NAV.cur, 'intro');
  __VF.UI.SV.introSeen = true; __VF.navReset('intro'); tapEl($('sc-intro'), 4); T.eq(__VF.UI.NAV.cur, 'title'); });
T.test('the intro never touches the fight state', () => { __VF.navReset('intro'); __VF.introAt(4000); T.eq(__VF.G.S, null); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — un solo `introAt(ms)` chiamato da `uiFrame` con `now - INTRO.t0`; la scheda nascosta ferma il tempo dell'intro (riparte da dov'era).
- [ ] **Step 4: verifica** — PASS. Registra un video della intro con Playwright (`record_video_dir`, 844×390) e guardane 8 fotogrammi (uno per inquadratura): ritmo, impatto leggibile, logo pulito. Annota gli ms per fotogramma durante l'impatto (`ui_perf`).
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: intro con lo scontro di Ren e Kael"`

### Task 7: Titolo e nome

**Files:**
- Modify: `src/u4_intro.js`, `src/u_style.css`
- Create: `tests/ui_title.test.js`

**Interfaces:**
- Schermata `title`: logo grande al centro, Ren e Kael di profilo ai lati, rovine e tramonto, «Tocca per iniziare» che pulsa. La scritta segue `NAV.dev` (o il tipo di schermo all'avvio): `'touch'` → «Tocca per iniziare», `'kb'` → «Premi un tasto», `'pad'` → «Premi A». Qualunque tocco, tasto o pulsante del controller → schermo intero e blocco orizzontale (come `mnFullscreen`, solo al tocco) → se `SV.name` è vuoto `navGo('name')`, altrimenti `navReset('menu')`.
- Schermata `name`: `cHead('Come ti chiami?', 'Il nome compare nel profilo e nei risultati.')`, campo di testo (etichetta visibile «Nome»), nome proposto già scritto (`pool` + due cifre), errore sotto il campo che si aggiorna mentre scrivi, «Conferma» attivo solo se il nome è valido; griglia di lettere per il controller (A-Z, 0-9, spazio, ⌫, «Fatto»), che appare quando l'ultimo dispositivo è il controller. Conferma → `SV.name`, `saveWrite()`, `navReset('menu')`.
- Errori (testo esatto): «Usa almeno 3 caratteri», «Al massimo 16 caratteri», «Solo lettere, numeri, spazi, - e _».

- [ ] **Step 1: test** — `tests/ui_title.test.js`:
```js
T.test('prompt follows the device', () => { __VF.navReset('title'); __VF.UI.NAV.dev = 'pad'; __VF.navReset('title'); T.ok(txt('sc-title').includes('Premi A')); __VF.UI.NAV.dev = 'kb'; __VF.navReset('title'); T.ok(txt('sc-title').includes('Premi un tasto')); });
T.test('first launch asks the name', () => { __VF.UI.SV.name = null; __VF.navReset('title'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'name'); T.ok($('uName').value.length >= 3); });
T.test('name errors and confirm', () => { const f = $('uName'); type(f, 'ab'); T.eq(txt('uNameErr'), 'Usa almeno 3 caratteri'); T.ok(byText('Conferma').classList.contains('off'));
  type(f, 'Lama#1'); T.eq(txt('uNameErr'), 'Solo lettere, numeri, spazi, - e _'); type(f, 'x'.repeat(17)); T.eq(txt('uNameErr'), 'Al massimo 16 caratteri');
  type(f, 'Lama Nera'); T.eq(txt('uNameErr'), ''); uiClick('Conferma'); T.eq(__VF.UI.SV.name, 'Lama Nera'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('named player goes straight to the menu', () => { __VF.navReset('title'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('controller letter grid', () => { __VF.UI.SV.name = null; __VF.navReset('title'); padsAt([{buttons: {0: 1}}]); padTick(); padsAt([{}]); padTick(); T.eq(__VF.UI.NAV.cur, 'name'); T.ok(vis('uKeys')); fakePads([]); padTick(); });
T.test('Backspace inside the field deletes, it does not go back', () => { const f = $('uName'); type(f, 'Lama'); f.focus(); key('Backspace'); keyUp('Backspace'); T.eq(__VF.UI.NAV.cur, 'name'); });
```
`type(el, text)` (in `tests/lib.js`) mette il valore e lancia `input`. Il test di orientamento va in `tests/orient.test.js` (`--viewport 390x844 --touch --mobile`):
```js
T.test('rotate while typing keeps the name', () => { setViewport(844, 390); window.dispatchEvent(new Event('resize')); __VF.UI.SV.name = null; __VF.navReset('name'); type($('uName'), 'Brace');
  setViewport(390, 844); window.dispatchEvent(new Event('resize')); T.ok(vis('rotate')); setViewport(844, 390); window.dispatchEvent(new Event('resize')); T.ok(!vis('rotate')); T.eq($('uName').value, 'Brace'); T.eq(__VF.UI.NAV.cur, 'name'); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces.
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/ui_title.test.js && python3 tests/run.py tests/orient.test.js --viewport 390x844 --touch --mobile` → PASS. Screenshot del titolo e del nome a 844×390, confronto con `docs/ref/ui/00-*.png` (riquadro 2).
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: titolo e nome del giocatore"`

### Task 8: Menu principale, Gioca e impostazioni del Versus (round e tempo nella partita)

**Files:**
- Create: `src/u5_play.js`, `tests/ui_menu.test.js`
- Modify: `src/c1_sim.js` (`simCreate` legge `o.rounds` e `o.timeS`), `src/z_main.js` (`startMatch` li passa), `src/u_style.css`, `mk.sh`, `tests/round.test.js` (2 prove)

**Interfaces:**
- Sim: `simCreate({..., rounds, timeS})` salva `S.need = (rounds ? (rounds + 1) / 2 : CFG.round.wins)` e `S.timeS = (timeS === undefined ? CFG.round.timerS : timeS)`. Il timer di ogni round = `S.timeS * 60`, oppure `-1` se `S.timeS === 0` o in allenamento; la partita finisce a `S.need` round vinti (al posto di `CFG.round.wins`). Valori interi: niente cambia nel determinismo.
- Schermata `menu`: a sinistra `cLogo('s')` e le voci `cItem` «Gioca», «Allenamento», «Profilo», «Pass stagionale», «Impostazioni» (`data-wrap`); in alto a destra `cChip()`; a destra l'eroe (`SV.lastChar` o Ren) e il rivale sfumato dietro (`layersSet('menu', {hero, rival})`). «Profilo», «Pass stagionale», «Impostazioni»: `locked`, nota «In arrivo nella prossima versione».
  - Col fuoco su «Gioca» appaiono sotto le carte `cCard` «Arcade» (bloccata: «Arcade in arrivo»), «Online» (bloccata: «Modalità online in arrivo») e la voce «Versus locale». Destra/giù dal menu entra nelle carte.
- «Versus locale» → schermata `vsopts`: `cHead('Versus locale', 'Scontro tra due giocatori sullo stesso dispositivo.')`, `cStepper` «Round» (1, 3, 5) e «Tempo» (60, 90, 99, ∞), Ren a sinistra («Giocatore 1») e Kael a destra («Giocatore 2»), `cBtn` main «Combatti» → `navGo('select', {mode:'versus', rounds, timeS, step:0})`. I valori scelti restano per la sessione.
- «Allenamento» → `navGo('select', {mode:'training', step:0})`.

- [ ] **Step 1: test** — `tests/ui_menu.test.js` e 2 prove in `tests/round.test.js`:
```js
// ui_menu.test.js
T.test('main menu items and chip', () => { __VF.UI.SV.name = 'Lama'; __VF.navReset('menu'); for (const t of ['Gioca', 'Allenamento', 'Profilo', 'Pass stagionale', 'Impostazioni']) T.ok(byText(t), t); T.ok(txt('sc-menu').includes('Lama')); });
T.test('locked entries say so and do nothing', () => { __VF.navReset('menu'); uiClick('Profilo'); T.eq(__VF.UI.NAV.cur, 'menu'); T.ok(txt('uiToast').includes('In arrivo')); uiClick('Online'); T.ok(txt('uiToast').includes('online in arrivo')); });
T.test('keyboard: Gioca → cards → Versus locale → options', () => { __VF.navReset('menu'); T.eq(focused(), 'Gioca'); keyTap('ArrowRight'); keyTap('ArrowDown'); T.ok(['Arcade', 'Online', 'Versus locale'].includes(focused()));
  __VF.navReset('menu'); uiClick('Versus locale'); T.eq(__VF.UI.NAV.cur, 'vsopts'); });
T.test('versus options: rounds and time', () => { __VF.navReset('vsopts'); T.ok(txt('sc-vsopts').includes('3')); T.ok(txt('sc-vsopts').includes('99'));
  navFocusText('Round'); keyTap('ArrowRight'); navFocusText('Tempo'); keyTap('ArrowRight'); T.ok(txt('sc-vsopts').includes('∞')); uiClick('Combatti'); const p = __VF.UI.NAV.stack.at(-1).params; T.eq(p.rounds, 5); T.eq(p.timeS, 0); });
T.test('menu back from options returns to the menu with Gioca focused', () => { __VF.navReset('menu'); uiClick('Versus locale'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'menu'); });
// round.test.js
T.test('rounds option: 1 round wins the match', () => { const S = N({rounds: 1}); T.eq(S.need, 1); F(S, 1).hp = 1; /* un colpo che va a segno */ near(S); T.feed(S, 1, B.P, 0); T.feed(S, 400, 0, 0); T.eq(S.phase, 'end'); T.eq(S.winner, 0); });
T.test('time option: 0 = no timer, 60 = 3600 frames', () => { T.eq(N({timeS: 0}).timer, -1); T.eq(N({timeS: 60}).timer, 3600); T.eq(N({}).timer, __VF.CFG.round.timerS * 60); });
```
`navFocusText(t)` (in `tests/lib.js`) = `__VF.navFocus(byText(t))`.
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces.
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/ui_menu.test.js && python3 tests/run.py tests/round.test.js && python3 tests/run.py tests/sim.test.js` → PASS. Screenshot del menu (fuoco su «Gioca» con le carte) e di «Versus locale» a 844×390 e 1280×720, confronto con `docs/ref/ui/00-*.png` (riquadro 3) e `01-*.png` (riquadro 4).
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: menu principale, Gioca, round e tempo del Versus"`

### Task 9: Selezione dei personaggi

**Files:**
- Modify: `src/u5_play.js`, `src/u_style.css`
- Create: `tests/ui_select.test.js`

**Interfaces:**
- Schermata `select` (`params = {mode, rounds, timeS, step, picks:[]}`): titolo in alto «Scegli il combattente» (in Versus «Giocatore 1» / «Giocatore 2» sotto), griglia 2×6 in basso da `CFG.ui.roster` (`face_*`, `silhouette` per `null`, lucchetto per `lock`), a sinistra il personaggio col fuoco a figura intera con respiro, nome grande corsivo e `cStatBar` Potenza / Velocità / Difficoltà (max 5); in Versus a destra la scelta del G1 già fatta (o vuota mentre sceglie il G1).
- Il fuoco sulla griglia cambia subito il personaggio grande (con un piccolo ingresso laterale). Conferma:
  - Ren o Kael: allenamento → `navGo('arena', {mode, chars:[c, rivale]})` (rivale = l'altro dei due); Versus step 0 → `navGo('select', {…, step:1, picks:[c]})`; Versus step 1 → `navGo('arena', {…, chars:[picks[0], c]})`.
  - Lo stesso personaggio del G1 per il G2: `uiToast('Scontro speculare in arrivo: scegli un altro combattente', 'soon')`.
  - Astra / Raigon: `uiToast('Si sblocca con il ' + lock, 'soon')` (es. «Si sblocca con il Pass gratuito · livello 50»).
  - Sagome: `uiToast('Nuovo combattente in arrivo', 'soon')`.
- Indietro dallo step 1 torna allo step 0 con il fuoco sulla scelta di prima.

- [ ] **Step 1: test** — `tests/ui_select.test.js`:
```js
T.test('grid: 12 slots, 2 playable, 2 pass locks, 8 coming', () => { __VF.navGo('select', {mode: 'versus', step: 0, picks: []}); T.eq(document.querySelectorAll('#sc-select .uSlot').length, 12);
  T.eq(document.querySelectorAll('#sc-select .uSlot.lock').length, 2); T.eq(document.querySelectorAll('#sc-select .uSlot.soon').length, 8); });
T.test('focus shows the fighter and stats', () => { navFocusSlot(1); T.ok(txt('uSelName').includes('Kael')); T.eq(document.querySelectorAll('#uSelStats .on').length, 3 + 4 + 3); });
T.test('Astra explains how to unlock', () => { navFocusSlot(2); keyTap('Enter'); T.ok(txt('uiToast').includes('Pass gratuito · livello 50')); T.eq(__VF.UI.NAV.cur, 'select'); });
T.test('versus: G1 then G2, no mirror', () => { navFocusSlot(0); keyTap('Enter'); T.eq(__VF.UI.NAV.stack.at(-1).params.step, 1); navFocusSlot(0); keyTap('Enter'); T.ok(txt('uiToast').includes('Scontro speculare in arrivo'));
  navFocusSlot(1); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'arena'); T.eq(JSON.stringify(__VF.UI.NAV.stack.at(-1).params.chars), '["ren","kael"]'); });
T.test('back from G2 returns to G1 with the focus on the first pick', () => { keyTap('Escape'); keyTap('Escape'); T.eq(__VF.UI.NAV.stack.at(-1).params.step, 0); T.eq(focusedSlot(), 0); });
T.test('training: one pick, the rival is the other fighter', () => { __VF.navGo('select', {mode: 'training', step: 0, picks: []}); navFocusSlot(1); keyTap('Enter'); T.eq(JSON.stringify(__VF.UI.NAV.stack.at(-1).params.chars), '["kael","ren"]'); });
```
`navFocusSlot(i)`, `focusedSlot()` in `tests/lib.js`.
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces.
- [ ] **Step 4: verifica** — PASS. Screenshot a 844×390, 640×360 e 1280×720; confronto con `docs/ref/ui/00-*.png` (riquadro 4). La griglia non copre il volto del personaggio grande; nessun testo tagliato.
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: selezione dei personaggi"`

### Task 10: Arena, VS, ponte verso la lotta vera

**Files:**
- Create: `src/u9_bridge.js`, `tests/ui_flow.test.js`
- Modify: `src/u5_play.js`, `src/u_style.css`, `src/d_render.js` (`rdFightersBuild` costruisce un lottatore per personaggio in `F3D_BY`; nuovo `renderCast(chars)`), `src/z_main.js` (`startMatch` chiama `renderCast`; `stepGame` chiama `uiEvents(S)`), `src/g_hud.js` (ritratti e nomi dal personaggio di ogni lato), `src/h_menu.js` (fine partita → risultati, Task 11), `mk.sh`

**Interfaces:**
- `renderCast(chars)`: `F3D[0] = F3D_BY[chars[0]]`, `F3D[1] = F3D_BY[chars[1]]`; i lottatori non in campo nascosti. Il resto del disegno continua a usare `F3D[side]`.
- Schermata `arena`: `cHead('Scegli l\'arena', 'Seleziona il luogo dello scontro.')`, l'arena col fuoco riempie lo sfondo (`layersSet('select', {arena})`, zoom lento), fila di `cCard` da `CFG.ui.arenas` (`arena_<id>`; non `ok` → bloccata, «Arena in arrivo»), `cBtn` main «Conferma» → `navGo('vs', params + {arena})`. In allenamento si salta il VS: «Conferma» → caricamento breve → lotta.
- Schermata `vs`: i due volti grandi (`ren_full`/`kael_full` ritagliati al busto) entrano dai lati, «VS» oro che si forma con una lama di luce, nomi e una battuta ciascuno (`CFG.ui.lines[c0 + '>' + c1]`, se manca nessuna battuta), «Caricamento…» con `cProgress` che segue `bridgePreload(arena)`. Pronto e passati `CFG.ui.vs.minMs` → `bridgeStart`. Dopo `CFG.ui.vs.tapAfterMs` un tocco o un tasto, a caricamento finito, parte subito. Il tempo del VS conta solo con la scheda visibile. Se `bridgePreload` fallisce: «Impossibile caricare l'arena» con «Riprova» e «Indietro».
- `bridgePreload(arena) -> Promise` (oggi la Cascata è già pronta dopo `renderInit`: si risolve subito); `bridgeStart({mode, chars, arena, rounds, timeS, dev})` → `inputAssign(mode, dev)`, `inputMaskHeld()`, `startMatch(mode, {seed, dummy:'fermo', chars, rounds, timeS})`, `SV.lastChar = chars[0]`, schermate dei menu tolte. `uiEvents(S)` conta in `UIB` i colpi (`hit` per lato) e la combo massima (dal `combo` del difensore). `bridgeResult(S)` come in «Interfacce condivise».

- [ ] **Step 1: test** — `tests/ui_flow.test.js` (percorso con la tastiera; con `CFG.ui.vs.minMs = 0` per non aspettare):
```js
T.test('versus from the menu to the real fight', () => { __VF.CFG.ui.vs.minMs = 0; __VF.UI.SV.name = 'Lama'; __VF.navReset('menu'); uiClick('Versus locale'); uiClick('Combatti');
  navFocusSlot(1); keyTap('Enter'); navFocusSlot(0); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'arena'); uiClick('Conferma'); T.eq(__VF.UI.NAV.cur, 'vs');
  T.ok(txt('sc-vs').includes('Kael') && txt('sc-vs').includes('Ren'));
  return Promise.resolve().then(() => { later(700, () => __VF.uiFrame(performance.now())); T.eq(__VF.G.state, 'fight');
    T.eq(__VF.fighterOf(__VF.G.S, 0).char, 'kael'); T.eq(__VF.F3D[0], __VF.F3D_BY.kael); T.eq(txt('name0'), 'KAEL'); }); });
T.test('locked arena does not start', () => { __VF.navGo('arena', {mode: 'versus', chars: ['ren', 'kael']}); uiClick('Foresta'); T.ok(txt('uiToast').includes('in arrivo')); T.eq(__VF.UI.NAV.cur, 'arena'); });
T.test('preload error: retry and back', () => { window.bridgePreloadFail = true; __VF.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata'});
  return Promise.resolve().then(() => Promise.resolve()).then(() => { T.ok(txt('sc-vs').includes("Impossibile caricare l'arena")); window.bridgePreloadFail = false; uiClick('Riprova'); }); });
T.test('hidden during VS: the fight waits', () => { __VF.CFG.ui.vs.minMs = 2500; __VF.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata'});
  Object.defineProperty(document, 'hidden', {value: true, configurable: true}); document.dispatchEvent(new Event('visibilitychange')); later(5000, () => __VF.uiFrame(performance.now())); T.eq(__VF.G.state, 'title');
  Object.defineProperty(document, 'hidden', {value: false, configurable: true}); document.dispatchEvent(new Event('visibilitychange')); __VF.uiFrame(performance.now()); T.eq(__VF.G.state, 'title', 'the VS time restarts from where it was'); __VF.CFG.ui.vs.minMs = 0; });
T.test('training goes straight to the fight with the chosen fighter', () => { __VF.navReset('menu'); uiClick('Allenamento'); navFocusSlot(1); keyTap('Enter'); uiClick('Conferma');
  return Promise.resolve().then(() => { later(1000, () => __VF.uiFrame(performance.now())); T.eq(__VF.G.mode, 'training'); T.eq(__VF.fighterOf(__VF.G.S, 0).char, 'kael'); }); });
T.test('rendering the swapped cast does not change the sim', () => { __VF.startMatch('versus', {seed: 3, chars: ['kael', 'ren']}); const h = __VF.simHash(__VF.G.S); __VF.renderFrame(__VF.G.S, performance.now()); T.eq(__VF.simHash(__VF.G.S), h); });
T.test('uiEvents counts hits and the best combo', () => { comboG(3); const r = __VF.bridgeResult(__VF.G.S); T.ok(r.hits[0] >= 3); T.ok(r.maxCombo[0] >= 3); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces. Il test d'errore usa `window.bridgePreloadFail` (solo `game_w.html` lo legge).
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/ui_flow.test.js` e poi `render fighter3d feel hud model` (`python3 tests/run.py tests/$f.test.js`, `model` con `--viewport 844x390 --touch --mobile`) → tutti PASS. Screenshot di arena e VS a 844×390; confronto con `docs/ref/ui/01-*.png` (riquadri 1 e 2). Una partita vera Kael (G1) contro Ren a 844×390: guarda che lottatori, ritratti e nomi siano giusti.
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: arena, VS e ponte verso la lotta vera"`

### Task 11: Risultati e ritorno al menu

**Files:**
- Modify: `src/u5_play.js`, `src/h_menu.js` (`menuCheckEnd` → `G.state='end'`, `navGo('results', bridgeResult(S))`; guardia `CFG.menu.endGuardMs` sulla schermata), `src/u_style.css`
- Create: `tests/ui_results.test.js`

**Interfaces:**
- Schermata `results` (`params` = risultato): il vincitore grande a sinistra (`ren_full`/`kael_full`, posa con luce di bordo), titolo «Vittoria» con alloro oro (se ha vinto il G1), «Sconfitta» (G1 ha perso; in Versus «Vince G2 · <Nome>»), «Pareggio»; punteggio «2 – 1» tra i due volti; in Versus il titolo è «Vince G1 · <Nome>» / «Vince G2 · <Nome>».
- In Versus: `progRecord(SV, r)`, XP con `progMatchXp(r)`: ogni voce entra a cascata con il suo «+N XP», il totale sale con un contatore che rimbalza, poi la barra del livello si riempie; se il livello sale: «Livello N!» con un piccolo lampo. `saveWrite()`.
- Pulsanti: «Rivincita» (stessi personaggi, arena, round, tempo → `bridgeStart` diretto), «Cambia personaggio» (`navGo('select', {mode, rounds, timeS, step:0, picks:[]})`, la pila torna sopra il menu), «Menu principale» (`navReset('menu')`). Esc / B = «Menu principale».
- In allenamento la lotta non finisce: la fine partita non arriva (come oggi); «Abbandona» in pausa porta al menu.

- [ ] **Step 1: test** — `tests/ui_results.test.js`:
```js
T.test('win: title, score, XP and save', () => { __VF.UI.SV.xp = 950; __VF.bridgeStart({mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); __VF.G.S.wins = [2, 1]; endMatch(0);
  T.eq(__VF.UI.NAV.cur, 'results'); T.ok(txt('sc-results').includes('Vince G1')); T.ok(txt('sc-results').includes('2 – 1')); T.eq(__VF.UI.SV.xp, 950 + 60 + 40 + 20); T.ok(txt('sc-results').includes('Livello 2!')); T.eq(JSON.parse(localStorage.getItem('voidrise.save')).xp, 1070); });
T.test('confirm is ignored for a moment', () => { keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'results'); });
T.test('rematch keeps fighters and options', () => { later(__VF.CFG.menu.endGuardMs + 50, () => uiClick('Rivincita')); T.eq(__VF.G.state, 'fight'); T.eq(__VF.fighterOf(__VF.G.S, 0).char, 'ren'); });
T.test('change fighter goes to the select screen', () => { endMatch(1); later(__VF.CFG.menu.endGuardMs + 50, () => uiClick('Cambia personaggio')); T.eq(__VF.UI.NAV.cur, 'select'); T.eq(__VF.G.state, 'title'); keyTap('Escape'); T.ok(['vsopts', 'menu'].includes(__VF.UI.NAV.cur)); });
T.test('draw', () => { __VF.bridgeStart({mode: 'versus', chars: ['kael', 'ren'], arena: 'cascata', dev: 'kb'}); endMatch(2); T.ok(txt('sc-results').includes('Pareggio')); });
T.test('back = main menu', () => { later(__VF.CFG.menu.endGuardMs + 50, () => __VF.navBack()); T.eq(__VF.UI.NAV.cur, 'menu'); T.eq(__VF.G.S, null); });
T.test('abandon from pause asks, then goes to the menu', () => { __VF.bridgeStart({mode: 'training', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); __VF.menu.pause(); uiClick('Abbandona'); T.ok(vis('uiOver')); uiClick('Abbandona'); return Promise.resolve().then(() => { T.eq(__VF.UI.NAV.cur, 'menu'); }); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — come nelle Interfaces.
- [ ] **Step 4: verifica** — PASS. Screenshot dei risultati a 844×390; confronto con `docs/ref/ui/03-*.png` (riquadro 4).
- [ ] **Step 5: commit** — `git commit -am "Interfaccia U1: risultati, XP e rivincita"`

### Task 12: Prove su tutti gli schermi, misure, documenti e pubblicazione

**Files:**
- Create: `tests/ui_layout.test.js`, `tests/ui_touch.test.js`, `docs/HANDOFF-UI.md` (completato)
- Modify: `CLAUDE.md` (una riga: «Interfaccia: leggi `docs/HANDOFF-UI.md`» e il link della pagina), `tests/smoke.test.js` (`boots to title` diventa `boots to the intro`)

- [ ] **Step 1: test** — `tests/ui_layout.test.js` (lanciato a 640×360, 844×390, 1280×720, 1920×1080) e `tests/ui_touch.test.js` (`--viewport 844x390 --touch --mobile`):
```js
// ui_layout.test.js: per ogni schermata del percorso
const SCREENS = [['title'], ['name'], ['menu'], ['vsopts'], ['select', {mode: 'versus', step: 0, picks: []}], ['arena', {mode: 'versus', chars: ['ren', 'kael']}], ['vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata'}], ['results', {mode: 'versus', chars: ['ren', 'kael'], winner: 0, wins: [2, 1], hits: [9, 4], maxCombo: [4, 2], timeS: 90}]];
for (const [id, p] of SCREENS) T.test('layout ' + id, () => { __VF.CFG.ui.vs.minMs = 1e9; __VF.navReset(id, p); const root = $('sc-' + id);
  for (const el of root.querySelectorAll('[data-focus]')) { if (el.offsetParent === null) continue; const r = el.getBoundingClientRect();
    T.ok(r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight, id + ': ' + el.textContent.trim() + ' off screen'); T.ok(Math.min(r.width, r.height) >= 44 || el.classList.contains('uSlot'), id + ': ' + el.textContent.trim() + ' too small'); }
  T.ok(document.scrollingElement.scrollWidth <= innerWidth, 'no horizontal scroll'); T.ok(noOverflow(root), id + ': text clipped'); });
// ui_touch.test.js
T.test('the whole path by touch', () => { __VF.CFG.ui.vs.minMs = 0; __VF.UI.SV.name = null; __VF.navReset('title'); tapEl($('sc-title'), 1); T.eq(__VF.UI.NAV.cur, 'name'); tapEl(byText('Conferma'), 2);
  tapEl(byText('Versus locale'), 3); tapEl(byText('Combatti'), 4); tapEl(slot(0), 5); tapEl(slot(1), 6); tapEl(byText('Conferma'), 7);
  return Promise.resolve().then(() => { later(1000, () => __VF.uiFrame(performance.now())); T.eq(__VF.G.state, 'fight'); T.ok(vis('tP')); }); });
```
`noOverflow(root)` (in `tests/lib.js`): nessun elemento di testo con `scrollWidth > clientWidth + 1`. `slot(i)` = `i`-esimo `.uSlot`.
- [ ] **Step 2: tutti i test** — devono passare tutti, con 0 errori:
```bash
bash mk.sh
for f in smoke sim attack guard round input render fighter3d feel hud menu perf model ui_base ui_save ui_nav ui_comp ui_layers ui_intro ui_title ui_menu ui_select ui_flow ui_results; do python3 tests/run.py tests/$f.test.js || break; done
for v in 640x360 844x390 1280x720 1920x1080; do python3 tests/run.py tests/ui_layout.test.js --viewport $v || break; done
python3 tests/run.py tests/ui_touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/orient.test.js --viewport 390x844 --touch --mobile
python3 tests/run.py tests/model.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/ui_perf.test.js --viewport 844x390
python3 tests/play_check.py
```
- [ ] **Step 3: prova a mano** — Playwright a 844×390 con il touch (tocchi veri via CDP) e a 1280×720 con tastiera e controller finto: intro intera, nome, menu, Versus Kael contro Ren fino ai risultati, rivincita, cambia personaggio, allenamento, pausa, abbandona. Console senza errori. Screenshot per Denis a `deviceScaleFactor` 2: intro (impatto), titolo, menu, personaggi, arena, VS, lotta, risultati.
- [ ] **Step 4: misure** — `ui_perf` (ms nei menu alta/bassa, durante l'intro, in lotta) contro i valori del Task 1; peso di `index.html` (deve restare < 16 MB). Tutto in `docs/HANDOFF-UI.md` con: stato, comandi, interfacce, scelte di Denis, segnaposto da sostituire (elenco dei file di `assets/ui/` con misure), idee «per dopo» della spec.
- [ ] **Step 5: pubblicazione** — nuova pagina Claude «Voidrise · Interfaccia» con `index.html` (icona `game`); link in `CLAUDE.md` e `docs/HANDOFF-UI.md`.
- [ ] **Step 6: commit e push** — `git add -A && git commit -m "Interfaccia U1: prove, misure, documenti e pubblicazione" && git push -u origin claude/cool-fermi-fkx4iq`.
