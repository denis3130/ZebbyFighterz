# Voidrise Fighters · Tappa 1 "Basi del combattimento" · Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** un picchiaduro 1 contro 1 giocabile (allenamento contro un manichino e 2 giocatori in locale) nell'arena "La Grande Cascata", con due lottatori provvisori in cel-shading, comandi su touch, tastiera e controller, pubblicato come pagina Claude.

**Architecture:** moduli JavaScript vanilla in `src/` uniti da `mk.sh` + `build.py` in un solo HTML, come Stormblade. La **simulazione** (`c1_sim.js`, `c2_moves.js`, `c3_dummy.js`) è pura e deterministica: interi in millimetri e fotogrammi, nessun THREE, DOM, `Math.random` o orologio. Avanza a passi fissi di 1/60 s con un intero di tasti per giocatore. **Grafica, HUD e menu** leggono lo stato e non lo cambiano mai.

**Tech Stack:** Three.js r128 (cdnjs nella pagina pubblicata, copia locale `three.min.js` nei test), JavaScript ES2019 senza bundler, Python 3 + Pillow per le immagini, Python 3 + Playwright con Chromium headless e SwiftShader per i test.

**Spec:** `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md`. Immagini in `docs/ref/`.

## Global Constraints

- "Three.js r128, JavaScript vanilla, moduli in `src/` uniti in un solo HTML". Nessuna libreria in più. Unici file esterni: three r128 da cdnjs e Google Fonts.
- "Logica (simulazione): passo fisso a 60 al secondo, solo numeri interi o arrotondati in modo stabile, nessun `Math.random` libero (generatore con seme), nessun uso del tempo reale." Nei file `c*_*.js`: niente `THREE`, `document`, `window`, `Math.random`, `Date`, `performance`, `Math.sin/cos/sqrt`. Posizioni in mm, velocità in mm/fotogramma, tempi in fotogrammi.
- "La grafica legge lo stato della logica e lo disegna … Non cambia mai lo stato."
- Ogni numero di bilanciamento sta in `CFG` (`src/a0_cfg.js`). I valori di questo piano sono quelli di partenza.
- Tutti i testi dell'interfaccia sono in italiano. Nomi: "VOIDRISE FIGHTERS", "REN", "KAEL".
- "Ogni funzione va su touch, mouse e tastiera, e controller."
- "Telefono (solo orizzontale) … Se il telefono è in verticale, schermata 'gira il telefono'."
- "obiettivo 60 [FPS] su telefono di fascia media"; gli effetti non allungano le lotte: si misura prima e dopo.
- "Prima di pubblicare: tutti i test verdi e nessun errore nella console."
- Pronto per il 3v3: ogni lato è `{team:[F], cur:0}`; tutto il codice passa da `fighterOf(s, side)` e mai da `team[0]`.
- Guardia, chiarimento della spec: `mid` si para in piedi e accovacciati; `low` solo accovacciati; `high` (gli attacchi in salto) solo in piedi.
- Controller, chiarimento della spec ("il primo controller va al G1 se non c'è tastiera in uso"): chi conferma "2 Giocatori" nel menu diventa G1 con quel dispositivo. Se conferma con la tastiera, il controller 1 va al G2.
- Si lavora sul ramo `tappa1-basi`; si unisce a `main` solo a tappa finita e rivista da Denis.

## Review Focus

1. Telefono: l'app va in background (notifica, cambio app) e poi torna. Atteso: la partita è in pausa e non "salta in avanti". Test in Task 11 `hidden tab pauses and does not catch up`.
2. Il pollice scivola fuori da un tasto touch, o il browser annulla il tocco (`pointercancel`). Atteso: il tasto si rilascia, niente colpo forte "incastrato". Test in Task 6 `pointercancel releases a held button`.
3. Telefono girato o finestra ridimensionata durante la lotta. Atteso: piedi ancora sul pavimento dipinto, HUD al suo posto. Test in Task 7 `resize keeps feet on the painted floor`.
4. Doppio K.O. (i due colpi arrivano nello stesso fotogramma). Atteso: round pari, nessun blocco. Test in Task 5 `double KO is a draw round`.
5. Controller staccato durante una partita a 2. Atteso: pausa, nessun errore, il gioco riprende con tastiera o touch. Test in Task 11 `pad disconnect pauses`.

---

## Mappa dei file

| File | Responsabilità | Task |
|---|---|---|
| `mk.sh`, `build.py` | build: unisce `src/head.html` e i `.js` di `FILES`, incorpora `assets/` come data URI (`ASSETS`), scrive `game_w.html` (test, con `window.__VF`) e `index.html` (pubblicata, senza `__VF`), controlla la sintassi con `node --check` | 1 |
| `three.min.js` | r128, copiato da Storm-Blade, usato solo dai test | 1 |
| `tests/run.py`, `tests/lib.js` | runner Playwright e API `T`, adattati da Storm-Blade | 1 |
| `src/head.html` | titolo, font, CSS, DOM di HUD, menu e tasti touch | 1, 6, 10, 11 |
| `src/a0_cfg.js` | `CFG`, ogni numero | 1-11 |
| `src/c1_sim.js` | `BTN`, stato, generatore, passo, fisica, contatti, round | 2, 3, 4, 5 |
| `src/c2_moves.js` | lettura dei comandi (tocco/tenuto, catene, buffer) e macchina a stati delle mosse | 2, 3, 4 |
| `src/c3_dummy.js` | manichino dell'allenamento (`dummyInput`) | 5 |
| `src/b_input.js` | tastiera (2 set), controller, touch → intero di tasti per giocatore | 6 |
| `tools/make_assets.py`, `assets/` | fondale JPG, maschera dell'acqua, ritratti | 7 |
| `src/d_render.js` | renderer, telecamera, fondale con acqua che scorre, foglie, ombre | 7 |
| `src/e_fighter3d.js` | lottatori provvisori: scheletro, toon, contorno, pose | 8 |
| `src/f_fx.js` | scintille, lampo, schiacciamento, tremolio, carica, proiettili, K.O. | 9 |
| `src/g_hud.js` | barre, ritratti, timer, round vinti, combo, energia, scritte | 10 |
| `src/h_menu.js` | titolo, pausa, fine partita, navigazione, "gira il telefono", schermo intero | 11 |
| `src/z_main.js` | `boot()`, ciclo a passo fisso, `G`, `window.__VF` | 1, 5, 11 |
| `docs/HANDOFF.md` | stato del lavoro, comandi, decisioni | 12 |

Ordine di `FILES` in `mk.sh`: `a0_cfg.js c1_sim.js c2_moves.js c3_dummy.js b_input.js d_render.js e_fighter3d.js f_fx.js g_hud.js h_menu.js z_main.js`. I file non ancora creati si aggiungono a `FILES` nel task che li crea.

## Valori di partenza (`CFG`)

Unità: mm, mm/fotogramma, fotogrammi (60 = 1 s); in `fx`, `cam` e `arena` metri e millisecondi (solo grafica).

```js
const CFG={
  ver:1,
  stage:{half:6000, startX:1200, maxSep:5500},
  body:{push:260, hurt:250, head:150, headH:300, h:1800, hCrouch:1050, hAir:1500, passY:1000, hp:1000, meterMax:3000},   // chi è in aria sopra passY non spinge e non è spinto
  walk:{f:75, b:58},
  jump:{squat:4, v:147, g:7, vxF:62, vxB:-52, superV:180, land:2, landAtk:5},
  dash:{f:{n:18, v0:170, v1:40}, b:{n:20, v0:150, v1:30}, tap:10},
  input:{hold:12, chargeShow:4, both:3, buffer:8},
  phys:{pushFric:2},
  combo:{scaleFrom:3, scaleStep:10, minScale:30, decayFrom:6, decay:1, minStun:6, juggleMax:6, lift:60},
  stop:{light:6, mid:8, heavy:11, spec:8, thr:10, ko:40, blockLight:5, blockHeavy:8},
  meter:{hit:1, block:.5, taken:.5},
  knock:{ground:36, getup:16, roll:22, rollDist:1300},
  thr:{range:900, s:4, a:2, whiff:24, anim:40, hitF:30, dmg:120, vx:60, vy:60},
  spec:{spawn:14, rec:30, speed:120, box:150, dmg:70, hs:20, bs:16, chip:8, x:500, y:1100},
  round:{intro:100, timerS:99, end:150, wins:2},
  training:{refill:60},
  dummy:{min:30, max:60},
  moves:{ /* tabella "Mosse" qui sotto */ },
  loop:{maxSteps:4},
  cam:{fov:30, dist0:6.5, distMax:9.6, footScreen:.86, marginX:1.0, marginTop:.35, smooth:.15, xMax:3.0},
  arena:{footRow:.86, cover:1.25, parX:.012, zoomPar:.3, contrast:.9, lift:.03, flow:.35, streak:.22, wobble:.002, leaves:10},
  fx:{on:true, flashMs:60, squashMs:110, squash:[1.1,.9], shakeHeavy:[.06,180], shakeKO:[.12,400], spark:{light:.35, heavy:.6, block:.3}},
  hud:{chipDelay:30, chipRate:.8, comboHide:60},
};
```

### Mosse (`CFG.moves`)

`s` = fotogrammi di avvio (il primo fotogramma attivo è `s+1`), `a` = attivi, `r` = recupero (`land` = fino all'atterraggio, poi `jump.landAtk`). Zona = `[x0,x1,y0,y1]` in mm: x in avanti dal centro del lottatore, y dal suolo (in aria dai piedi). `push` = velocità di spinta del colpito, che cala di `phys.pushFric`. `stop` = classe di hitstop. Catene: `tapP`/`tapK` = mossa per un tocco di P/K nella finestra di cancellazione, `heavy` = `true` (ogni forte della posizione attuale) o un elenco, `spec` = cancellabile nello Speciale, `jc` = salto alto annulla il recupero (solo se ha colpito). Arto = la parte del modello che deve stare nella zona (Task 8).

| id | posizione | comando | s | a | r | danno | stun colpito | stun parata | altezza | zona | push | stop | catene | arto | effetto |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p1 | piedi | P tocco | 4 | 2 | 7 | 30 | 14 | 10 | mid | 200,700,900,1550 | 24 | light | tapP p2, tapK k1, heavy, spec | handL | |
| p2 | piedi | P tocco in catena | 5 | 3 | 9 | 35 | 15 | 11 | mid | 200,760,900,1550 | 24 | light | tapP p3, tapK k1, heavy, spec | handR | |
| p3 | piedi | P tocco in catena | 7 | 3 | 14 | 50 | 18 | 12 | mid | 200,780,900,1500 | 35 | mid | heavy, spec | handL | |
| k1 | piedi | K tocco | 6 | 3 | 10 | 40 | 15 | 11 | mid | 200,820,700,1100 | 24 | light | tapP p2, tapK k2, heavy, spec | footL | |
| k2 | piedi | K tocco in catena | 8 | 3 | 15 | 55 | 18 | 12 | mid | 250,900,1100,1500 | 30 | mid | heavy, spec | footR | |
| hp | piedi | P tenuto | 12 | 4 | 18 | 90 | 22 | 15 | mid | 250,900,900,1550 | 40 | heavy | heavy [chk], spec | handR | |
| hk | piedi | K tenuto | 14 | 4 | 20 | 100 | — | 16 | mid | 300,1000,1000,1600 | — | heavy | spec | footR | a terra: vx 70, vy 70 |
| cp | basso | P tocco | 5 | 2 | 8 | 25 | 13 | 10 | mid | 200,700,700,1000 | 22 | light | tapP p2, tapK ck, heavy, spec | handR | |
| ck | basso | K tocco | 6 | 3 | 10 | 30 | 14 | 10 | low | 250,900,0,300 | 24 | light | heavy, spec | footL | |
| chp | basso | P tenuto | 9 | 4 | 20 | 80 | 20 | 14 | mid | 150,650,1300,2100 | 30 | heavy | spec | handR | su chi è in aria: a terra, vx 30, vy 50 |
| chk | basso | K tenuto | 11 | 4 | 22 | 70 | — | 14 | mid | 200,700,800,1900 | — | heavy | spec, jc | footR | lancio: in aria, vy 160, vx 10 |
| jp | aria | P tocco | 5 | 4 | land | 40 | 15 | 10 | high | 150,600,300,900 | 20 | light | tapK jk, heavy | handR | |
| jk | aria | K tocco | 6 | 5 | land | 45 | 16 | 11 | high | 150,700,-300,500 | 20 | light | heavy | footR | |
| jhp | aria | P tenuto | 10 | 4 | land | 75 | 20 | 13 | high | 150,700,0,800 | 20 | heavy | — | handR | su chi è in aria: schiacciata, vy −120, poi a terra |
| jhk | aria | K tenuto | 11 | 5 | land | 80 | 21 | 14 | high | 150,800,-400,400 | 20 | heavy | — | footR | |

Lo Speciale (`spec`) e la presa (`thr`) hanno i loro valori in `CFG.spec` e `CFG.thr`. Nella Tappa 1 Ren e Kael usano la stessa tabella.

## Interfacce condivise (riferimento per tutti i task)

```js
BTN = {U:1, D:2, L:4, R:8, P:16, K:32, S:64, DASH:128, GUARD:256}   // direzioni assolute, in c1_sim.js
simCreate({seed, mode:'versus'|'training', chars:['ren','kael'], dummy:'fermo'|'casuale'}) -> S
simStep(S, in0, in1) -> void     // un fotogramma; svuota e riempie S.ev
simClone(S) -> S                 // copia profonda (JSON)
simHash(S) -> string             // FNV-1a di JSON.stringify(S) senza S.ev
fighterOf(S, side) -> F          // S.sides[side].team[S.sides[side].cur]
dummyInput(S, side) -> int       // manichino, usa solo S.rng
```

- `S = {frame, rng, mode, phase:'intro'|'fight'|'ko'|'timeup'|'end', pf, round, timer, wins:[0,0], winner, stop, sides:[{team:[F],cur:0},{…}], proj:[], ev:[], dummy, dum:[{act,left},{act,left}]}`. `timer` è in fotogrammi (−1 in allenamento); `winner` vale −1 finché la partita non è finita, poi 0, 1 o 2 (pareggio).
- `F = {side, char, x, y, vx, vy, face:1|-1, hp, meter, act, af, air, stun, combo, comboDmg, juggle, hit:0|1|2, inv, hold:[p,k], prev, tap:{dir,f}, buf:{cmd,left}, sj, land}`.
  - `act`: `idle walkF walkB crouch jumpSquat air dashF dashB guard guardC block hitStun juggle knock getup rollF rollB thr thrWhiff thrown landing ko win intro` più gli id delle mosse e `spec`.
  - `hit`: la mossa in corso ha già toccato (1 colpito, 2 parato).
- Eventi in `S.ev`: `{t, side, x, y, move, dmg, heavy}`, con `t` tra `hit block whiff charge heavyFire thr proj projHit projBlock projClash jump land dash knock ko timeup round fight win draw`. Le coordinate sono in mm, nel punto di contatto (centro della sovrapposizione tra zona che colpisce e corpo).
- `G = {state:'title'|'fight'|'pause'|'end', mode, S, acc, last}` in `z_main.js`. `startMatch(mode, {seed, dummy})`.
- `window.__VF` (solo in `game_w.html`): `{G, CFG, BTN, simCreate, simStep, simClone, simHash, fighterOf, dummyInput, startMatch, frame(n), IN, renderer, camera, cam, toScreen, limbWorld, ARENA, F3D, FX, HUD, menu, tick}`. Ogni task aggiunge le sue voci.

---

### Task 1: Scheletro del progetto, build e runner dei test

**Files:**
- Create: `mk.sh`, `build.py`, `three.min.js` (copia di `/home/user/Storm-Blade/three.min.js`), `src/head.html`, `src/a0_cfg.js`, `src/z_main.js`, `tests/run.py`, `tests/lib.js`, `tests/smoke.test.js`, `.gitignore` (`g.js`)
- Branch: `git checkout -b tappa1-basi`

**Interfaces:**
- Produces: `bash mk.sh` → `game_w.html` + `index.html` + `SYNTAX_OK`. `ASSETS` = oggetto `{'arena/cascata.jpg':'data:image/jpeg;base64,…', …}` con ogni file sotto `assets/` (vuoto finché il Task 7 non ne aggiunge). `boot()` porta `G.state` a `'title'`. Runner: `python3 tests/run.py tests/X.test.js [--viewport WxH] [--touch] [--mobile] [--seed N]`. `T.info(msg)` stampa `INFO msg`. `T.feed(S, n, a, b)` esegue `simStep` n volte.

- [ ] **Step 1: test di fumo** — `tests/smoke.test.js`:
```js
T.test('boots to title', () => T.eq(__VF.G.state, 'title'));
T.test('index has no test API', () => T.ok(!/window\.__VF=/.test(TINDEX), 'index.html contiene __VF'));
T.test('assets object exists', () => T.eq(typeof __VF.ASSETS, 'object'));
```
`run.py` definisce `window.TINDEX` con il testo di `index.html` prima del test.
- [ ] **Step 2: verifica che fallisca** — `python3 tests/run.py tests/smoke.test.js` → errore: `game_w.html` non esiste.
- [ ] **Step 3: implementazione**
  - `build.py out wrap files…`: come Storm-Blade, senza GLTFLoader. Prima del codice inserisce `const ASSETS={…};` letto da `assets/**/*.jpg|png`.
  - `mk.sh`: cd nella cartella; `FILES`; `game_w.html`; `index.html`, a cui toglie il tratto da `window.__VF={` fino a `\nboot();` escluso; poi `node --check`.
  - `run.py`: copia di Storm-Blade, con questi cambi: attende `window.__VF && __VF.G.state==='title'`; niente `INIT` per localStorage; `chrome_path()` controlla anche `/opt/pw-browsers/chromium`; niente `--http` e `--data`; inietta `TINDEX`; stampa le righe `INFO`.
  - `lib.js`: `T` di Storm-Blade, con `info` e `feed` e senza `newGame`, `clearEnemies` e `key`.
  - `head.html`: `<title>Voidrise Fighters</title>`, Google Fonts "Bebas Neue" e "Barlow Condensed" (600 e 700 corsivo), variabili CSS `--orange:#ff7a1a --yellow:#ffc83a --cyan:#35d8ff --violet:#9b5fe0 --ink:#f4f1ea --dark:#14121c`, `#app` > `#game` (canvas) e `#hud`, `#ui`.
  - `z_main.js`: `G`, `boot()` che mette `G.state='title'`, `window.__VF={G, CFG, ASSETS};\nboot();`.
  - Se Playwright per Python manca: `pip install playwright` (il browser c'è già in `/opt/pw-browsers/chromium`).
- [ ] **Step 4: verifica** — `bash mk.sh && python3 tests/run.py tests/smoke.test.js` → `3 passed, 0 failed, 0 errors`.
- [ ] **Step 5: commit** — `git add -A && git commit -m "Tappa 1: scheletro, build e runner dei test"`

### Task 2: Simulazione: stato, movimento e determinismo

**Files:**
- Create: `src/c1_sim.js`, `src/c2_moves.js`, `tests/sim.test.js`
- Modify: `src/a0_cfg.js` (sezioni `stage body walk jump dash input phys`), `mk.sh` (`FILES`), `src/z_main.js` (esporta le funzioni della sim)

**Interfaces:**
- Produces: `BTN`, `simCreate`, `simStep`, `simClone`, `simHash`, `fighterOf` (vedi "Interfacce condivise"). In `c2_moves.js`: `readCommand(S, F, bits) -> cmd|null` (cmd tra `jump dashF dashB walkF walkB crouch guard guardC` e, dal Task 3, le mosse) e `setAct(F, act)` (azzera `af` e `hit`). Il primo fotogramma di un'azione ha `af = 1`: i fotogrammi attivi di una mossa sono `af` da `s+1` a `s+a`. In questo task `phase` parte da `'fight'`: le fasi arrivano nel Task 5.

- [ ] **Step 1: test** — `tests/sim.test.js` (helper: `const B=__VF.BTN, N=()=>__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), F=(S,i)=>__VF.fighterOf(S,i)`):
```js
T.test('start positions', () => { const S=N(); T.eq(F(S,0).x,-1200); T.eq(F(S,1).x,1200); T.eq(F(S,0).face,1); T.eq(F(S,1).face,-1); });
T.test('walk forward 20f', () => { const S=N(); T.feed(S,20,B.R,0); T.eq(F(S,0).x,-1200+75*20); });
T.test('walk back is slower', () => { const S=N(); T.feed(S,30,B.L,0); T.eq(F(S,0).x,-1200-58*30); });
T.test('neutral jump lands after squat + airtime', () => { const S=N(); T.feed(S,1,B.U,0); let n=1; while(F(S,0).act!=='idle'&&n<200){T.feed(S,1,0,0);n++;}
  T.ok(n>=4+40&&n<=4+44+2, 'frames '+n); T.eq(F(S,0).y,0); });
T.test('jump apex about 1.55 m', () => { const S=N(); let top=0; T.feed(S,1,B.U,0); for(let i=0;i<60;i++){T.feed(S,1,0,0);top=Math.max(top,F(S,0).y);} T.near(top,1550,80); });
T.test('dash forward by button and by double tap', () => { const a=N(); T.feed(a,1,B.DASH,0); T.eq(F(a,0).act,'dashF');
  const b=N(); T.feed(b,1,B.R,0); T.feed(b,2,0,0); T.feed(b,1,B.R,0); T.eq(F(b,0).act,'dashF'); });
T.test('back + dash = back dash', () => { const S=N(); T.feed(S,1,B.L|B.DASH,0); T.eq(F(S,0).act,'dashB'); });
T.test('fighters never overlap and stay inside walls', () => { const S=N(); T.feed(S,200,B.R,B.L); T.ok(F(S,1).x-F(S,0).x>=2*260); const W=N(); T.feed(W,400,B.L,B.L); T.eq(F(W,0).x,-6000+260); T.eq(F(W,1).x,-6000+3*260); });
T.test('max separation', () => { const S=N(); T.feed(S,300,B.L,B.R); T.ok(F(S,1).x-F(S,0).x<=5500); });
T.test('sides switch when jumping over', () => { const S=N(); F(S,1).x=0; T.feed(S,1,0,B.U|B.L); T.feed(S,80,0,B.L); T.ok(F(S,1).x<F(S,0).x); T.feed(S,5,0,0); T.eq(F(S,0).face,-1); T.eq(F(S,1).face,1); });
T.test('determinism: same inputs same hash', () => { const run=()=>{const S=N(); let r=7; for(let i=0;i<900;i++){r=(r*1103515245+12345)>>>0; T.feed(S,1,r>>>16&511,r>>>7&511);} return __VF.simHash(S);}; T.eq(run(),run()); });
T.test('clone then continue gives the same hash', () => { const A=N(); T.feed(A,120,B.R,B.L|B.U); const C=__VF.simClone(A); T.feed(A,200,B.U|B.R,B.D); T.feed(C,200,B.U|B.R,B.D); T.eq(__VF.simHash(A),__VF.simHash(C)); });
T.test('sim is pure: no Math.random, no clock', () => { const mr=Math.random, pn=performance.now, dn=Date.now; Math.random=()=>{throw Error('Math.random');}; performance.now=()=>{throw Error('clock');}; Date.now=performance.now;
  try{ const S=N(); T.feed(S,300,B.R|B.P,B.L|B.K); } finally { Math.random=mr; performance.now=pn; Date.now=dn; } });
T.test('left+right is neutral', () => { const S=N(); T.feed(S,30,B.L|B.R,0); T.eq(F(S,0).x,-1200); });
```
- [ ] **Step 2: verifica che fallisca** — `bash mk.sh && python3 tests/run.py tests/sim.test.js` → FAIL: `__VF.simCreate` non definita.
- [ ] **Step 3: implementazione**
  - `c1_sim.js`: `simStep` esegue, in quest'ordine: input (fronti di pressione, contatori `hold`, doppio tocco, SOCD: L+R = nessuna direzione orizzontale, U+D = nessuna verticale) → comando (`readCommand`) → fisica (velocità, gravità `jump.g`, atterraggio a y=0) → pushbox (separazione a metà; non vale se uno dei due è in aria sopra `body.passY`, così si può saltare oltre l'avversario; muri a ±`stage.half − body.push`; distanza massima `maxSep`) → verso (il `face` si aggiorna solo da `idle`, `walk*`, `crouch`, `guard*`) → `frame++`.
  - Il generatore è mulberry32 su `S.rng` (intero). Velocità del dash: interpolazione intera da `v0` a `v1` lungo `n` fotogrammi. Salto con direzione: L/R al momento della fine dello `squat`, in avanti/indietro rispetto a `face`.
  - `simHash` è FNV-1a a 32 bit in esadecimale, calcolato su `JSON.stringify` dello stato senza `ev`.
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/sim.test.js` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: simulazione deterministica e movimento"` (con i file nuovi aggiunti)

### Task 3: Attacchi: tocco e tenuto, colpi, combo, lancio

**Files:**
- Modify: `src/a0_cfg.js` (`moves combo stop meter knock`), `src/c1_sim.js` (contatti, danni, hitstop, stun, giocoleria, a terra e rialzo), `src/c2_moves.js` (comandi d'attacco, catene, buffer)
- Create: `tests/attack.test.js`

**Interfaces:**
- Consumes: Task 2.
- Produces: `scaleFor(n)`, `moveBox(F, m) -> {x0,x1,y0,y1}|null` in coordinate assolute (mm) se `F` è nei fotogrammi attivi di `m`; `hurtBoxes(F) -> [corpo, testa]` (spec: "zone che possono essere colpite (corpo, testa)"): corpo ±`body.hurt` da 0 ad altezza − `headH`, testa ±`body.head` da lì all'altezza (`h`, `hCrouch` o `hAir` dai piedi). `canBeHit(F)`, `hitstunFor(base, n)`. Usate dal Task 8 per il test degli arti.

- [ ] **Step 1: test** — `tests/attack.test.js` (stessi helper; `near(S)` mette i lottatori a 700 mm: `F(S,0).x=-350; F(S,1).x=350`):
```js
T.test('tap P releases a light punch', () => { const S=N(); T.feed(S,3,B.P,0); T.eq(F(S,0).act,'idle'); T.feed(S,1,0,0); T.eq(F(S,0).act,'p1'); });
T.test('hold P 12 frames fires the heavy punch at the 12th', () => { const S=N(); T.feed(S,11,B.P,0); T.ok(F(S,0).act!=='hp'); T.feed(S,1,B.P,0); T.eq(F(S,0).act,'hp'); T.feed(S,5,0,0); T.eq(F(S,0).act,'hp','releasing after the heavy does nothing'); });
T.test('charge event from the 4th held frame', () => { const S=N(); T.feed(S,3,B.P,0); T.ok(!S.ev.some(e=>e.t==='charge')); T.feed(S,1,B.P,0); T.ok(S.ev.some(e=>e.t==='charge')); });
T.test('crouch versions and air versions', () => { const S=N(); T.feed(S,2,B.D|B.K,0); T.feed(S,1,B.D,0); T.eq(F(S,0).act,'ck'); const A=N(); T.feed(A,1,B.U,0); T.feed(A,8,0,0); T.feed(A,1,B.P,0); T.feed(A,1,0,0); T.eq(F(A,0).act,'jp'); });
T.test('p1 hits: damage, hitstun, hitstop', () => { const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,1,0,0); T.feed(S,4,0,0); const h=S.ev.find(e=>e.t==='hit'); T.ok(h,'no hit on frame 5'); T.eq(F(S,1).hp,970); T.eq(S.stop,6); T.eq(F(S,1).act,'hitStun'); });
T.test('P,P,P chain is p1 p2 p3', () => { const S=N(); near(S); const seq=[]; for(let i=0;i<60;i++){ T.feed(S,1,(i%6===0)?B.P:0,0); const a=F(S,0).act; if(seq[seq.length-1]!==a&&/^p\d$/.test(a))seq.push(a);} T.eq(seq.slice(0,3).join(),'p1,p2,p3'); });
T.test('chain only on contact', () => { const S=N(); let saw=false; for(let i=0;i<40;i++){ T.feed(S,1,(i%3===0)?B.P:0,0); if(F(S,0).act==='p2')saw=true; } T.ok(!saw, 'whiffed p1 must not chain'); });
T.test('damage scaling from the 3rd hit, floor 30%', () => { const S=N(); near(S); comboPPPH(S); T.eq(1000-F(S,1).hp, 30+35+45+72); T.eq(__VF.scaleFor(12),30); });
T.test('hitstun decays from the 6th hit', () => { T.eq(__VF.hitstunFor(14,6),13); T.eq(__VF.hitstunFor(14,5),14); T.eq(__VF.hitstunFor(14,40),6); });
T.test('no infinite: mashing P and K in the corner ends before 20 hits', () => { const S=N(); F(S,1).x=5700; F(S,0).x=5000; let max=0; for(let i=0;i<600;i++){ T.feed(S,1,[B.P,0,B.K,0,B.D|B.P,0][i%6],0); max=Math.max(max,F(S,1).combo);} T.ok(max<20,'combo '+max); });
T.test('launcher then super jump chase and air hit', () => { const S=N(); near(S); T.feed(S,12,B.D|B.K,0); let n=0; while(!S.ev.some(e=>e.t==='hit')&&n<20){T.feed(S,1,B.D,0);n++;}
  T.eq(F(S,1).act,'juggle'); T.feed(S,1,B.U|B.R,0); T.feed(S,16,B.R,0); T.ok(F(S,0).sj,'super jump (buffered through the hitstop)');
  let pressed=false; for(let i=0;i<60&&F(S,1).combo<2;i++){ const go=!pressed&&Math.abs(F(S,0).y-F(S,1).y)<300; T.feed(S,1,go?B.P:0,0); if(go){pressed=true; T.feed(S,1,0,0);} } T.ok(F(S,1).combo>=2,'air hit'); });
T.test('juggle limit makes the opponent invulnerable until landing', () => { const S=N(); const f=F(S,1); f.act='juggle'; f.air=true; f.y=800; f.juggle=6; T.eq(__VF.canBeHit(f),false); });
T.test('hk knocks down, then getup is invulnerable', () => { const S=N(); near(S); T.feed(S,14,B.K,0); T.feed(S,30,0,0); T.eq(F(S,1).act,'knock'); T.ok(F(S,1).inv>0); });
T.test('holding back on the ground rolls', () => { const S=N(); near(S); T.feed(S,14,B.K,0); let saw=false; for(let i=0;i<150&&!saw;i++){ T.feed(S,1,0,B.R); saw=F(S,1).act==='rollB'; } T.ok(saw); });
T.test('trade: both hit on the same frame', () => { const S=N(); near(S); T.feed(S,1,B.P,B.P); T.feed(S,5,0,0); T.ok(F(S,0).hp<1000&&F(S,1).hp<1000); });
T.test('meter: hit gives attacker dmg, defender half', () => { const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,6,0,0); T.eq(F(S,0).meter,30); T.eq(F(S,1).meter,15); });
```
`comboPPPH(S)` (in `tests/lib.js`) preme P,P,P nelle finestre di catena e poi tiene P 12 fotogrammi. Danni attesi: 30, 35, 50×0,9=45, 90×0,8=72.
- [ ] **Step 2: verifica che fallisca** — `python3 tests/run.py tests/attack.test.js` → FAIL.
- [ ] **Step 3: implementazione**
  - Regole del comando, in ordine, quando il lottatore può agire o la finestra di cancellazione è aperta:
    1. P e K premuti entro `input.both` fotogrammi → presa (Task 4). I due rilasci successivi non contano.
    2. S → speciale (Task 4).
    3. Rilascio di P o K con `hold < input.hold` → colpo normale. In catena vale `tapP`/`tapK` della mossa in corso; altrimenti, in base alla posizione: `p1`/`k1`, `cp`/`ck` se c'è D, `jp`/`jk` in aria.
    4. `hold` che arriva a `input.hold` → colpo forte: `hp hk`, `chp chk`, `jhp jhk`. Evento `heavyFire`.
    5. Scatto (tasto o doppio tocco entro `dash.tap`).
    6. U → salto (alto se `jc` è aperto).
    7. GUARD → `guard`/`guardC`.
    8. D → `crouch`; L/R → camminata.
  - I comandi arrivati quando non si può agire restano in `buf` per `input.buffer` fotogrammi.
  - Finestra di cancellazione: dal fotogramma del contatto (`hit>0`) alla fine del recupero.
  - Contatti a fine passo: per ogni lottatore nei fotogrammi attivi con `hit===0`, la `moveBox` contro le `hurtBoxes` dell'altro, se `canBeHit` (non `inv`, non `knock`/`getup`/`roll*`, giocoleria sotto il limite). I due lottatori si controllano nello stesso passo (scambio di colpi).
  - Danno: `floor(dmg * scaleFor(n) / 100)` con `scaleFor(n) = max(minScale, 100 - scaleStep*max(0, n-scaleFrom+1))` e `n` = numero del colpo nella combo (1°, 2° pieni, 3° 90%, 4° 80% … minimo 30%). `hitstunFor(base, n) = max(minStun, base - decay*max(0, n-decayFrom+1))`.
  - Hitstop: `S.stop = CFG.stop[classe]`. Mentre `stop>0` si aggiornano solo `hold`, `prev` e `buf`, e il buffer non scade (così un tocco durante l'hitstop di un forte, 11 fotogrammi, non va perso).
  - In aria colpito → `juggle`: `vy = max(vy, move.vy ?? combo.lift)`, `juggle++`. Atterraggio da `juggle` → `knock`.
  - `knock` dura `knock.ground` fotogrammi, poi `getup` (`knock.getup`) oppure `rollF`/`rollB` se si tiene una direzione (`knock.roll` fotogrammi, `rollDist` mm). Sempre invulnerabile.
  - `combo` e `comboDmg` del colpito si azzerano quando esce da `hitStun`, `juggle`, `knock`.
  - `__VF` espone anche `hitstunFor`, `scaleFor`, `canBeHit`, `moveBox`, `hurtBoxes`.
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/attack.test.js && python3 tests/run.py tests/sim.test.js` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: attacchi, catene, danno che cala, lancio"`

### Task 4: Guardia, presa e colpo energetico

**Files:**
- Modify: `src/c1_sim.js`, `src/c2_moves.js`, `src/a0_cfg.js` (`thr spec`)
- Create: `tests/guard.test.js`

**Interfaces:**
- Consumes: Task 3.
- Produces: `S.proj` = `[{side, x, y, vx, live}]` (al massimo uno per lato); `isBlocking(F, height) -> bool`.

- [ ] **Step 1: test** — `tests/guard.test.js`:
```js
T.test('back-hold blocks a mid, no damage, blockstun', () => { const S=N(); near(S); T.feed(S,1,B.P,B.R); T.feed(S,6,0,B.R); T.eq(F(S,1).hp,1000); T.eq(F(S,1).act,'block'); T.ok(S.ev.some(e=>e.t==='block')); });
T.test('guard button blocks without walking', () => { const S=N(); near(S); const x=F(S,1).x; T.feed(S,1,B.P,B.GUARD); T.feed(S,6,0,B.GUARD); T.eq(F(S,1).hp,1000); T.eq(F(S,1).x>=x,true); });
T.test('standing guard does not block a low', () => { const S=N(); near(S); T.feed(S,1,B.D|B.K,B.GUARD); T.feed(S,8,B.D,B.GUARD); T.eq(F(S,1).hp,970); });
T.test('crouch guard blocks low and mid', () => { for(const m of [[B.D|B.K,B.D],[B.D|B.P,B.D]]){ const S=N(); near(S); T.feed(S,1,m[0],B.D|B.GUARD); T.feed(S,8,m[1],B.D|B.GUARD); T.eq(F(S,1).hp,1000); } });
T.test('crouch guard does not block a jump attack', () => { const S=N(); F(S,1).x=0; T.feed(S,2,0,B.D|B.GUARD); const a=F(S,0); Object.assign(a,{x:-500,y:400,air:true,vy:-20,act:'jk',af:6,hit:0}); T.feed(S,2,0,B.D|B.GUARD); T.eq(F(S,1).hp,955); });
T.test('throw beats guard', () => { const S=N(); near(S); T.feed(S,1,B.P|B.K,B.GUARD); T.feed(S,40,0,B.GUARD); T.eq(F(S,1).hp,880); T.eq(F(S,1).act,'knock'); });
T.test('throw out of range whiffs', () => { const S=N(); T.feed(S,1,B.P|B.K,0); T.eq(F(S,0).act,'thr'); T.feed(S,6,0,0); T.eq(F(S,0).act,'thrWhiff'); });
T.test('throw cannot grab an airborne opponent', () => { const S=N(); near(S); T.feed(S,1,0,B.U); T.feed(S,6,0,0); T.feed(S,1,B.P|B.K,0); T.feed(S,10,0,0); T.eq(F(S,1).hp,1000); });
T.test('special spawns one projectile at frame 14, one at a time', () => { const S=N(); T.feed(S,1,B.S,0); T.feed(S,12,0,0); T.eq(S.proj.length,0); T.feed(S,1,0,0); T.eq(S.proj.length,1); F(S,0).act='idle'; T.feed(S,1,B.S,0); T.ok(F(S,0).act!=='spec','S with a projectile alive does nothing'); });
T.test('projectile hit and chip on block', () => { const a=N(); T.feed(a,1,B.S,0); T.feed(a,60,0,0); T.eq(F(a,1).hp,930); const b=N(); T.feed(b,1,B.S,B.R); T.feed(b,60,0,B.R); T.eq(F(b,1).hp,992); });
T.test('projectiles clash', () => { const S=N(); T.feed(S,1,B.S,B.S); let saw=false; for(let i=0;i<60;i++){ T.feed(S,1,0,0); saw=saw||S.ev.some(e=>e.t==='projClash'); } T.ok(saw); T.eq(S.proj.length,0); T.eq(F(S,0).hp,1000); T.eq(F(S,1).hp,1000); });
```
- [ ] **Step 2: verifica che fallisca** — `python3 tests/run.py tests/guard.test.js` → FAIL.
- [ ] **Step 3: implementazione**
  - Si para quando, nel momento del contatto, il colpito è in `idle walkB crouch guard guardC block` e tiene GUARD o "indietro" rispetto all'avversario. In piedi senza D si parano `mid` e `high`; accovacciati (D) si parano `mid` e `low`. Lo `stun` di parata è `bs`, la spinta è `push` (all'attaccante se il colpito è al muro). Lo Speciale toglie `spec.chip` anche in parata.
  - Presa: P+K avvia sempre `thr` (avvio `thr.s`, attivi `thr.a`). Prende se, nei fotogrammi attivi, la distanza tra i centri è al massimo `thr.range` e il bersaglio è a terra, non in `stun` e non `inv`; altrimenti, finiti gli attivi, `thrWhiff`. Se prende: `thr.anim` fotogrammi, danno `thr.dmg` al fotogramma `thr.hitF`, poi il bersaglio va in `knock` con `thr.vx`, `thr.vy`.
  - Proiettile: nasce a `x + face*spec.x`, `y = spec.y`, con velocità `face*spec.speed` e scatola di ±`spec.box`. Sparisce oltre `stage.half+1000` o al contatto. Due proiettili che si toccano spariscono entrambi.
- [ ] **Step 4: verifica** — `guard`, `attack`, `sim` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: guardia alta e bassa, presa, colpo energetico"`

### Task 5: Round, partita, allenamento e manichino

**Files:**
- Create: `src/c3_dummy.js`, `tests/round.test.js`
- Modify: `src/c1_sim.js` (fasi), `src/a0_cfg.js` (`round training dummy`), `src/z_main.js` (`startMatch`, `G.S`), `mk.sh`

**Interfaces:**
- Consumes: Task 2-4.
- Produces: `frame(n)` in `z_main.js` (n passi di gioco: tasti da `inputRead` se esiste, altrimenti 0; eventi a `fxEvents`/`hudEvents` se esistono; poi un `renderFrame` se esiste). Fasi `intro → fight → ko|timeup → (intro del round dopo | end)`; si passa a `fight` alla fine del 100° passo dell'intro. Eventi `round` (inizio intro, con `S.round`), `fight`, `ko`, `timeup`, `win`, `draw`. `dummyInput(S, side)`. `startMatch(mode, {seed, dummy})` crea `G.S` e mette `G.state='fight'`.

- [ ] **Step 1: test** — `tests/round.test.js`:
```js
T.test('intro ignores inputs for 100 frames', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); T.eq(S.phase,'intro'); T.feed(S,99,B.R,0); T.eq(F(S,0).x,-1200); T.feed(S,1,0,0); T.eq(S.phase,'fight'); });
T.test('timer counts 99 s only in fight', () => { const S=fight(); T.eq(S.timer,99*60); T.feed(S,60,0,0); T.eq(S.timer,98*60); });
T.test('KO ends the round and the winner gets a win', () => { const S=fight(); F(S,1).hp=20; near(S); T.feed(S,1,B.P,0); T.feed(S,6,0,0); T.eq(S.phase,'ko'); T.feed(S,150,0,0); T.eq(S.wins[0],1); T.eq(S.round,2); T.eq(S.phase,'intro'); T.eq(F(S,1).hp,1000); });
T.test('time up: more health wins', () => { const S=fight(); F(S,0).hp=500; S.timer=1; T.feed(S,1,0,0); T.eq(S.phase,'timeup'); T.feed(S,150,0,0); T.eq(S.wins[1],1); });
T.test('double KO is a draw round', () => { const S=fight(); F(S,0).hp=10; F(S,1).hp=10; near(S); T.feed(S,1,B.P,B.P); T.feed(S,200,0,0); T.eq(S.wins[0],1); T.eq(S.wins[1],1); T.ok(['intro','fight'].includes(S.phase)); });
T.test('best of 3: 2 wins end the match', () => { const S=fight(); S.wins=[1,0]; F(S,1).hp=1; near(S); T.feed(S,1,B.P,0); T.feed(S,200,0,0); T.eq(S.phase,'end'); T.eq(S.winner,0); });
T.test('2-2 after draws is a draw match', () => { const S=fight(); S.wins=[1,1]; F(S,0).hp=1; F(S,1).hp=1; near(S); T.feed(S,1,B.P,B.P); T.feed(S,200,0,0); T.eq(S.winner,2); });
T.test('training: no timer, health refills 60 frames after the combo', () => { const S=__VF.simCreate({seed:1,mode:'training',chars:['ren','kael'],dummy:'fermo'}); T.feed(S,100,0,0); T.eq(S.timer,-1); near(S); T.feed(S,1,B.P,0); T.feed(S,30,0,0); T.ok(F(S,1).hp<1000); T.feed(S,60,0,0); T.eq(F(S,1).hp,1000); });
T.test('training: health never below 1', () => { const S=trainingFight(); F(S,1).hp=5; near(S); T.feed(S,1,B.P,0); T.feed(S,6,0,0); T.eq(F(S,1).hp,1); T.ok(S.phase==='fight'); });
T.test('dummy fermo sends nothing', () => { const S=trainingFight(); T.eq(__VF.dummyInput(S,1),0); });
T.test('dummy casuale is deterministic and moves', () => { const run=()=>{const S=__VF.simCreate({seed:5,mode:'training',chars:['ren','kael'],dummy:'casuale'}); for(let i=0;i<600;i++) __VF.simStep(S,0,__VF.dummyInput(S,1)); return S;};
  const a=run(), b=run(); T.eq(__VF.simHash(a),__VF.simHash(b)); T.ok(F(a,1).x!==1200,'it moved'); });
```
`fight()` e `trainingFight()` (in `tests/lib.js`) creano la sim e fanno passare l'intro.
- [ ] **Step 2: verifica che fallisca** — `python3 tests/run.py tests/round.test.js` → FAIL.
- [ ] **Step 3: implementazione**
  - `simCreate` parte in `intro`, con `round:1` e `timer` pari a `timerS*60` (−1 in allenamento). Il timer scende solo in `fight`, anche durante l'hitstop.
  - K.O.: hp ≤ 0 → `ko` con `S.stop = stop.ko`. Dopo `round.end` fotogrammi: chi ha più hp prende un round; con parità (doppio K.O. o tempo con hp uguali) lo prendono entrambi.
  - Con `wins[i] >= round.wins` → `end` e `winner` (2 se entrambi). Altrimenti nuovo round: posizioni e hp di partenza, energia tenuta.
  - In allenamento: niente `ko`, hp minimo 1, ricarica a `body.hp` quando il colpito non è in combo da `training.refill` fotogrammi.
  - Manichino `casuale`: ogni `dummy.min..max` fotogrammi (da `S.rng`) sceglie con lo stesso peso tra fermo, avanti, indietro, basso, salto e guardia (indietro tenuto). Lo stato è in `S.dum[side]`.
- [ ] **Step 4: verifica** — `round`, `guard`, `attack`, `sim` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: round, partita al meglio di 3, allenamento con manichino"`

### Task 6: Comandi: tastiera, controller e touch

**Files:**
- Create: `src/b_input.js`, `tests/input.test.js`, `tests/touch.test.js`
- Modify: `src/head.html` (DOM e CSS dei tasti touch), `src/z_main.js` (ogni passo legge `inputRead`), `mk.sh`

**Interfaces:**
- Produces: `inputInit()`, `inputRead(p) -> int`, `inputAssign(mode, chooser)` con `chooser` = `'kb'|'touch'|{pad:i}`, `IN = {override:[null,null], keys:Set, pads:[], touchBits:0, assign}`. Se `IN.override[p]` non è `null`, `inputRead` restituisce quel valore (serve ai test).
  - Tastiera G1: `KeyW KeyS KeyA KeyD` + `KeyJ` P, `KeyK` K, `KeyL` S, `KeyU` DASH, `KeyI` GUARD.
  - Tastiera G2: frecce + `Numpad1` P, `Numpad2` K, `Numpad3` S, `Numpad4` DASH, `Numpad5` GUARD.
  - In allenamento tutti e due i set vanno al G1.
  - Controller (Gamepad API, mappa standard): P = 2, K = 0, S = 1, DASH = 5, GUARD = 4, croce 12-15, levetta sinistra con zona morta .45.
  - Assegnazione: `IN.assign = [{kb:[0,1]|[0]|[1], pad:i|null, touch:bool}, {…}]`. In allenamento G1 = tutti e due i set, il primo controller e il touch. In 2 giocatori G1 = il `chooser` più il set 1 (e il touch), G2 = il set 2 e il primo controller non preso.
- DOM touch (solo con `pointer:coarse`): `#touch` con `#stickZone` (40% sinistro, levetta che nasce dove appoggi il dito, raggio 56 px, `#stickKnob`) e i tasti `#tP` `#tK` `#tS` (tondi, grandi) e `#tDash` `#tGuard` (a pillola, sotto), come nel riferimento. Icone SVG (pugno, stivale, fiamma, figura che corre, scudo) con le scritte PUGNO, CALCIO, SPEC, SCATTO, GUARDIA. Classe `.down` mentre premuto, con `scale(.9)`.
- Levetta: U se `ny < -.45`, D se `ny > .45`, L se `nx < -.45`, R se `nx > .45` (normalizzati sul raggio).

- [ ] **Step 1: test** — `tests/input.test.js` (viewport di default) e `tests/touch.test.js` (`--viewport 844x390 --touch --mobile`):
```js
// input.test.js
T.test('keyboard G1 and G2 at the same time (versus)', () => { __VF.inputAssign('versus','kb'); key('KeyD'); key('KeyJ'); key('ArrowLeft'); key('Numpad2');
  T.eq(__VF.inputRead(0), B.R|B.P); T.eq(__VF.inputRead(1), B.L|B.K); keyUpAll(); });
T.test('training: arrows also drive G1', () => { __VF.inputAssign('training','kb'); key('ArrowUp'); T.eq(__VF.inputRead(0)&B.U, B.U); keyUpAll(); });
T.test('gamepad mapping', () => { fakePads([{buttons:{2:1,5:1}, axes:[-.9,0]}]); __VF.inputAssign('training','kb'); T.eq(__VF.inputRead(0), B.P|B.DASH|B.L); fakePads([]); });
T.test('chooser pad becomes G1, keyboard set 2 is G2', () => { fakePads([{},{buttons:{0:1}}]); __VF.inputAssign('versus',{pad:1}); T.eq(__VF.inputRead(0)&B.K, B.K); T.eq(__VF.inputRead(1)&B.K, 0); fakePads([]); });
T.test('chooser keyboard: pad 0 goes to G2', () => { fakePads([{buttons:{1:1}}]); __VF.inputAssign('versus','kb'); T.eq(__VF.inputRead(1)&B.S, B.S); T.eq(__VF.inputRead(0)&B.S, 0); fakePads([]); });
T.test('keys are released on window blur', () => { key('KeyJ'); window.dispatchEvent(new Event('blur')); T.eq(__VF.inputRead(0)&B.P, 0); });
// touch.test.js
T.test('touch controls are shown', () => { for(const id of ['tP','tK','tS','tDash','tGuard','stickZone']) T.ok(vis(id), id); });
T.test('stick right and up', () => { pd('stickZone',100,250,1); pm('stickZone',160,200,1); T.eq(__VF.inputRead(0)&(B.R|B.U), B.R|B.U); pu('stickZone',160,200,1); T.eq(__VF.inputRead(0),0); });
T.test('button press shows .down and sets the bit', () => { pd('tP',0,0,2); T.ok($('tP').classList.contains('down')); T.eq(__VF.inputRead(0)&B.P, B.P); pu('tP',0,0,2); T.ok(!$('tP').classList.contains('down')); });
T.test('pointercancel releases a held button', () => { pd('tK',0,0,3); fire('tK','pointercancel',0,0,3); T.eq(__VF.inputRead(0)&B.K, 0); T.ok(!$('tK').classList.contains('down')); });
T.test('P and K pressed together throw (touch)', () => { __VF.startMatch('training',{seed:1,dummy:'fermo'}); skipIntro(); nearG(); pd('tP',0,0,4); pd('tK',0,0,5); __VF.frame(1); pu('tP',0,0,4); pu('tK',0,0,5); __VF.frame(45); T.eq(F(__VF.G.S,1).hp,880); });
T.test('buttons fit inside a 390 px tall screen', () => { for(const id of ['tP','tK','tS','tDash','tGuard']){ const r=$(id).getBoundingClientRect(); T.ok(r.bottom<=390&&r.right<=844&&r.width>=48, id); } });
```
`key`, `keyUpAll`, `fakePads` (sostituisce `navigator.getGamepads`), `pd/pm/pu/fire` (PointerEvent sull'elemento, con `pointerId`), `vis`, `skipIntro`, `nearG` vanno in `tests/lib.js`.
- [ ] **Step 2: verifica che fallisca** — `python3 tests/run.py tests/input.test.js` → FAIL.
- [ ] **Step 3: implementazione** — Ascoltatori `keydown`/`keyup` su `window` (con `preventDefault` sui tasti di gioco), `blur` che svuota `keys`, Pointer Events con `setPointerCapture` sui tasti e sulla levetta, `pointerup` e `pointercancel` che rilasciano. `inputRead` unisce i dispositivi del giocatore con un OR e lascia lo SOCD alla sim.
- [ ] **Step 4: verifica** — `python3 tests/run.py tests/input.test.js && python3 tests/run.py tests/touch.test.js --viewport 844x390 --touch --mobile` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: comandi da tastiera, controller e touch"`

### Task 7: Arena "La Grande Cascata": fondale, acqua che scorre, telecamera

**Files:**
- Create: `tools/make_assets.py`, `assets/arena/cascata.jpg`, `assets/arena/cascata_mask.png`, `assets/ui/ren_face.jpg`, `assets/ui/kael_face.jpg`, `src/d_render.js`, `tests/render.test.js`
- Modify: `src/z_main.js` (`boot` aspetta le texture prima del titolo; `G.state==='fight'` disegna ogni rAF), `mk.sh`

**Interfaces:**
- Produces: `renderInit() -> Promise`, `renderFrame(S, nowMs)` (mette `uTime = nowMs/1000`), `renderResize()`, `cam = {x, y, dist}` in metri, `toScreen(xm, ym, zm) -> {x, y}` in px, `ARENA = {mat (ShaderMaterial del fondale), leaves (Group), footRowY() -> px}`, `scene`, `camera`, `renderer`. Il mondo 3D è in metri: `x = F.x/1000`, `y = F.y/1000`, `z = 0` (lato 0 a +0,05, lato 1 a −0,05).

- [ ] **Step 1: immagini** — `tools/make_assets.py` (Pillow), da `docs/ref/`:
  - `sfondo-cascata.png` → `assets/arena/cascata.jpg` (1672×941, qualità 82, al massimo 600 KB).
  - Maschera dell'acqua: poligono in pixel dell'immagine `[(672,254),(1242,247),(1240,420),(1185,470),(1165,560),(1160,640),(1080,672),(820,672),(705,640),(676,560)]`, riempito a 255. Dalla riga 590 in giù va moltiplicato per `max(.4, 1-(y-590)/82*.6)` (schiuma più calma), poi sfocatura gaussiana 5 px, poi ridotto a 836×471 in scala di grigi → `cascata_mask.png`.
  - Ritratti 160×160: `ren.png` ritaglio `(392,40,632,280)`, `kael.png` ritaglio `(392,70,632,310)` → JPG qualità 85.
  - Lancia `python3 tools/make_assets.py`, poi guarda i file prodotti: la maschera deve coprire solo la cascata e i ritratti mostrare la faccia intera.
- [ ] **Step 2: test** — `tests/render.test.js` (default 640×360; il file va lanciato anche con `--viewport 844x390`):
```js
T.test('water flows: waterfall pixels change, rock does not', () => { __VF.startMatch('versus',{seed:1}); __VF.ARENA.leaves.visible=false; const a=pxAt(0,.55,.3), s=pxAt(0,.3,.05), b=pxAt(500,.55,.3), s2=pxAt(500,.3,.05);
  T.ok(diff(a,b)>6,'water still'); T.ok(diff(s,s2)<=2,'static area moved'); __VF.ARENA.leaves.visible=true; });
T.test('feet stand on the painted floor', () => { const g=__VF.toScreen(__VF.cam.x,0,0).y; T.near(g/innerHeight, .86, .02); T.near(__VF.ARENA.footRowY(), g, innerHeight*.02); });
T.test('camera keeps both fighters in view at max separation', () => { const S=__VF.G.S; F(S,0).x=-2750; F(S,1).x=2750; for(let i=0;i<60;i++) __VF.renderFrame(S,i*16);
  for(const i of [0,1]){ const p=__VF.toScreen(F(S,i).x/1000,.9,0); T.ok(p.x>0&&p.x<innerWidth,'side '+i); } });
T.test('camera fits a super jump and the floor stays aligned', () => { const S=__VF.G.S; F(S,0).y=2314; for(let i=0;i<60;i++) __VF.renderFrame(S,i*16);
  T.ok(__VF.toScreen(F(S,0).x/1000,(2314+1800)/1000,0).y>0,'head off screen'); T.near(__VF.ARENA.footRowY(), __VF.toScreen(__VF.cam.x,0,0).y, innerHeight*.02); });
T.test('backdrop covers the whole screen', () => { for(const [u,v] of [[0,0],[1,0],[0,1],[1,1]]){ const p=pxAt(0,u,v); T.ok(p[3]===255 && sum(p)>30, u+','+v); } });
T.test('render does not change the sim', () => { const h=__VF.simHash(__VF.G.S); __VF.renderFrame(__VF.G.S,0); T.eq(__VF.simHash(__VF.G.S),h); });
T.test('resize keeps feet on the painted floor', () => { setViewport(740,360); window.dispatchEvent(new Event('resize')); __VF.renderFrame(__VF.G.S,0); T.near(__VF.ARENA.footRowY(), __VF.toScreen(__VF.cam.x,0,0).y, innerHeight*.02); });
```
`pxAt(t,u,v)` chiama `renderFrame(G.S, t)` e legge subito il pixel con `gl.readPixels`, nello stesso turno JS (u,v da 0 a 1, v dall'alto). `diff` e `sum` sono sui canali RGB. `setViewport` cambia `innerWidth`/`innerHeight` con `defineProperty`.
- [ ] **Step 3: verifica che fallisca** — FAIL: `__VF.ARENA` non definito.
- [ ] **Step 4: implementazione `src/d_render.js`**
  - `WebGLRenderer` con `antialias:false`, `pixelRatio min(devicePixelRatio, 2)` e `autoClear=false`.
  - Il fondale è un rettangolo a tutto schermo con una camera ortografica, disegnato prima della scena 3D (`depthWrite:false`).
  - Copertura: scala = `max(W/imgW, H/imgH) * arena.cover`, moltiplicata per `(dist0/dist)^zoomPar`. La riga `footRow` dell'immagine va messa alla y di schermo di `toScreen(cam.x,0,0)`, che vale `footScreen` dell'altezza; lo zoom ha il centro su quel punto. Spostamento orizzontale: `-cam.x * parX` larghezze d'immagine.
  - Shader del fondale:
    - colore = `(c - .5) * contrast + .5 + lift`;
    - con `m` = maschera: `uv' = uv + vec2(0, sin(uv.x*90. + uTime*3.) * wobble * m)`;
    - strisce = rumore a valori 2D su `(uv.x*140., uv.y*6. + uTime*flow*6.)`;
    - `col += m * (strisce - .5) * streak`.
  - Telecamera: `fov` verticale 30°, guardando lungo −z senza inclinazione. `cam.y = dist * (footScreen - .5) * 2 * tan(fov/2)`, così il suolo è sempre all'86% dell'altezza. `dist` è il massimo tra `dist0`, la distanza che contiene i due lottatori con `marginX` (in base all'aspetto dello schermo) e quella che contiene la testa più alta con `marginTop`, al massimo `distMax`. `cam.x` = punto medio, limitato a ±`xMax`. Avvicinamento con `smooth` per fotogramma.
  - Foglie: `arena.leaves` sprite (texture a foglia disegnata su canvas, giallo-verde), da sinistra a destra con oscillazione; metà a z +1,5 e metà a z −2. Usano un generatore della sola grafica.
  - Ombre: disco con sfumatura radiale nera al 45%, a y = 0,005, che si rimpicciolisce con l'altezza del lottatore.
  - `uTime` avanza con il tempo reale solo in `fight` e in `title`.
- [ ] **Step 5: verifica** — `python3 tests/run.py tests/render.test.js` e `--viewport 844x390` → tutti PASS. Salva uno screenshot a 844×390 nella scratchpad e guardalo: cascata che si muove, pavimento al suo posto.
- [ ] **Step 6: commit** — `git add -A && git commit -m "Tappa 1: arena La Grande Cascata con acqua che scorre e telecamera"`

### Task 8: Lottatori provvisori in cel-shading e pose

**Files:**
- Create: `src/e_fighter3d.js`, `tests/fighter3d.test.js`
- Modify: `src/d_render.js` (crea e aggiorna `F3D`), `mk.sh`

**Interfaces:**
- Consumes: `moveBox`, `hurtBoxes` (Task 3), `scene` (Task 7).
- Produces: `F3D = [{root, joints, limbs:{handL,handR,footL,footR}, mats}]`, `fighterBuild(char) -> F3D item`, `poseOf(F, S) -> {joint:[x,y,z] gradi, …}` (pura, dipende solo da `act`, `af`, `x`, `hold`), `limbWorld(side, limb) -> THREE.Vector3` in metri.

- [ ] **Step 1: test** — `tests/fighter3d.test.js`:
```js
T.test('every limb is inside its hitbox on the active frames', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,0); f.x=0; f.face=1;
  for(const [id,m] of Object.entries(__VF.CFG.moves)){ f.air=id[0]==='j'; f.y=f.air?900:0; f.act=id; f.af=m.s+1+Math.floor(m.a/2); __VF.renderFrame(S,0);
    const p=__VF.limbWorld(0,m.limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' '+m.limb+' at '+[p.x,p.y]); } });
T.test('facing left mirrors the limbs', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,0); f.x=0; f.face=-1; f.act='p1'; f.af=5; __VF.renderFrame(S,0); T.ok(__VF.limbWorld(0,'handL').x<-.2); });
T.test('fighters have an outline and toon shading', () => { const it=__VF.F3D[0]; let toon=0, out=0; it.root.traverse(o=>{ if(o.material&&o.material.isMeshToonMaterial)toon++; if(o.material&&o.material.side===THREE.BackSide)out++; }); T.ok(toon>10&&out>10); });
T.test('ren and kael colours differ', () => { T.ok(__VF.F3D[0].mats.main.color.getHex()!==__VF.F3D[1].mats.main.color.getHex()); });
T.test('pose is a pure function', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const a=JSON.stringify(__VF.poseOf(F(S,0),S)), b=JSON.stringify(__VF.poseOf(F(S,0),S)); T.eq(a,b); });
T.test('feet touch the ground when idle', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0); T.near(__VF.limbWorld(0,'footL').y,.05,.06); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL: `__VF.limbWorld` non definita.
- [ ] **Step 3: implementazione**
  - Scheletro di `THREE.Group`:
    - bacino → schiena → petto → collo → testa;
    - petto → spalla L/R → gomito → polso (pugno = sfera);
    - bacino → anca L/R → ginocchio → caviglia (stivale = box).
  - Proporzioni anime con altezza 1,8 m, costruite con `CylinderGeometry` e `SphereGeometry` (r128 non ha `CapsuleGeometry`). Pantaloni larghi: cilindri più larghi al ginocchio. Capelli: coni.
  - Colori di Ren: pelle `#e8b48a`, capelli `#2a2230`, gilet `#2f6f6e`, maglia `#3a3040`, fascia `#f07a22`, pantaloni `#3b3340`, bende `#e9e2d6`, stivali `#2f6f6e`/`#1b1b1f`.
  - Colori di Kael: capelli `#ece8f4`, abito `#3a2d4a`, accenti e fascia `#9b5fe0`, guanti `#2a2233`, pelle `#e8b48a`.
  - Materiali: `MeshToonMaterial` con `gradientMap` a 3 livelli (DataTexture 3×1, valori 90/170/255, `NearestFilter`). Contorno: per ogni mesh una copia con `ShaderMaterial` `BackSide` che sposta i vertici lungo la normale di 0,018 m, colore `#0b0a10`. Una luce direzionale da in alto a sinistra, come il sole del fondale, più una luce emisferica.
  - Pose in gradi per articolazione, per ogni `act`. Nelle mosse: guardia → caricamento (fine dell'avvio) → colpo disteso (fotogrammi attivi) → ritorno in guardia (fine del recupero), con `smoothstep` in base a `af`. Camminata a ciclo sulla distanza percorsa. Guardia con respiro: seno di `S.frame`.
  - Verso: `root.rotation.y = face * 90°`, più 25° verso la telecamera.
- [ ] **Step 4: verifica** — `fighter3d`, `render` → tutti PASS. Screenshot a 844×390 di p1, hk, chk, guardia bassa e salto: le pose devono leggersi come pugno, calcio e così via.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: lottatori provvisori in cel-shading con pose"`

### Task 9: Effetti e game feel

**Files:**
- Create: `src/f_fx.js`, `tests/feel.test.js`
- Modify: `src/d_render.js` (chiama `fxUpdate`), `src/a0_cfg.js` (`fx`), `mk.sh`

**Interfaces:**
- Consumes: eventi `S.ev` (Task 3-5), `F3D` (Task 8).
- Produces: `fxEvents(S, nowMs)`, chiamata una volta per passo di sim con gli eventi di quel passo, e `fxUpdate(nowMs)` per ogni rAF. `FX = {sparks:[], shake:{amp,until}, flash:[ms0,ms1], squash:[ms0,ms1], screenFlash, projColor(char) -> THREE.Color}` (`projColor` dà il colore del nucleo).
- Effetti:
  - **Scintilla**: sprite additivi al punto di contatto, giallo-bianco; più grande sui forti; azzurro-bianco piccolo in parata.
  - **Lampo bianco** sul colpito (`emissive` per `flashMs`).
  - **Schiacciamento** del colpito (`squash` per `squashMs`).
  - **Tremolio** della telecamera solo sui forti (`shakeHeavy`) e al K.O. (`shakeKO`).
  - **Carica**: alone pulsante sulla mano o sul piede mentre `hold >= chargeShow`, che cresce fino al colpo forte; lampo del corpo su `heavyFire`.
  - **Proiettile**: sfera luminosa con scia. Ren: nucleo `#ffffff`, alone `#bff3ff`, più bianco dell'acqua (spec). Kael: nucleo `#ffffff`, alone `#c9a2ff`.
  - **K.O.**: lampo bianco di tutto lo schermo per 120 ms.

- [ ] **Step 1: test** — `tests/feel.test.js`:
```js
T.test('hit makes spark, flash and squash', () => { hitOnce(); T.ok(__VF.FX.sparks.length>0); T.ok(__VF.FX.flash[1]>0); T.ok(__VF.FX.squash[1]>0); });
T.test('light hit does not shake, heavy does', () => { hitOnce('p1'); T.eq(__VF.FX.shake.amp,0); hitOnce('hp'); T.near(__VF.FX.shake.amp,.06,.001); });
T.test('effects do not change the fight', () => { const run=on=>{ __VF.CFG.fx.on=on; const S=__VF.simCreate({seed:3,mode:'versus',chars:['ren','kael']}); for(let i=0;i<1200;i++){ __VF.simStep(S, scripted(i), __VF.dummyInput(S,1)); __VF.fxEvents(S,i*16); } return __VF.simHash(S); };
  T.eq(run(true), run(false)); __VF.CFG.fx.on=true; });
T.test('effects are pooled: no new objects after warm-up', () => { for(let i=0;i<30;i++) hitOnce(); const n=__VF.scene.children.length; for(let i=0;i<30;i++) hitOnce(); T.eq(__VF.scene.children.length,n); });
T.test('ren projectile core is whiter than the water', () => { const c=__VF.FX.projColor('ren'); T.ok(c.r+c.g+c.b>2.7); });
```
`hitOnce(move)` e `scripted(i)` stanno in `tests/lib.js`. `scripted(i)` è una sequenza fissa di tasti che ripete combo, salti e speciali.
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — Gli effetti usano solo il tempo della grafica. Scintille, aloni e scie stanno in pool creati in `renderInit`. Il tremolio sposta la telecamera solo nel disegno: `cam` resta quello calcolato, così il test del pavimento continua a valere.
- [ ] **Step 4: verifica** — `feel`, `render`, `fighter3d` → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: game feel — hitstop, scintille, lampo, schiacciamento, tremolio, carica"`

### Task 10: HUD

**Files:**
- Create: `src/g_hud.js`, `tests/hud.test.js`
- Modify: `src/head.html` (DOM e CSS del HUD), `src/z_main.js`, `mk.sh`

**Interfaces:**
- Consumes: `S`, eventi, `ASSETS['ui/ren_face.jpg']`, `ASSETS['ui/kael_face.jpg']`.
- Produces: `hudInit()`, `hudUpdate(S)` (ogni rAF: disegna), `hudEvents(S)` (ogni passo di sim: combo e parte persa della vita, così i tempi sono in fotogrammi). `HUD = {chip:[a,b]}` (frazione della barra).
- DOM: `#face0/#face1`, `#name0/#name1`, `#hpFill0/1`, `#hpChip0/1`, `#timer`, `#wins0/#wins1` (2 rombi ciascuno), `#combo0/#combo1` (numero + "COLPI"), `#meter0/#meter1` (3 segmenti), `#lvl0/#lvl1`, `#banner`.
- Stile del riferimento:
  - barre della vita gialle (`--yellow`) e oblique (`skewX(-20deg)`), con la parte persa rossa che cala piano: aspetta `hud.chipDelay` fotogrammi dalla fine della combo, poi scende di `hud.chipRate` barre al secondo;
  - ritratti in cornici a punta;
  - timer grande al centro (Bebas Neue) in un riquadro a punta, "∞" in allenamento;
  - energia azzurra (`--cyan`) a segmenti con il livello accanto.
- Scritte di `#banner`: "ROUND N" per tutta l'intro, "COMBATTI!" per 40 fotogrammi dall'evento `fight`, "K.O.", "TEMPO!", "VINCE REN!" / "VINCE KAEL!", "PAREGGIO". Ognuna entra con un'animazione una volta sola.

- [ ] **Step 1: test** — `tests/hud.test.js` (anche con `--viewport 844x390`):
```js
T.test('health bar follows hp', () => { startFight(); F(__VF.G.S,1).hp=500; __VF.hudUpdate(__VF.G.S); T.near(barScale('hpFill1'),.5,.01); });
T.test('chip waits for the combo to end, then drains', () => { comboG(1); __VF.hudUpdate(__VF.G.S); T.near(barScale('hpChip1'),1,.01); __VF.frame(70); T.ok(barScale('hpChip1')<1); __VF.frame(120); T.near(barScale('hpChip1'),barScale('hpFill1'),.01); });
T.test('combo counter shows from 2 hits and bumps once per hit', () => { comboG(2); T.eq(txt('combo0').trim().startsWith('2'),true); T.ok($('combo0').classList.contains('bump')); });
T.test('combo counter hides 60 frames after the combo', () => { comboG(2); __VF.frame(80); T.ok(!vis('combo0')); });
T.test('timer shows seconds, ∞ in training', () => { startFight(); T.eq(txt('timer'),'99'); __VF.startMatch('training',{seed:1,dummy:'fermo'}); __VF.frame(110); T.eq(txt('timer'),'∞'); });
T.test('round banners', () => { __VF.startMatch('versus',{seed:1}); __VF.frame(2); T.eq(txt('banner'),'ROUND 1'); __VF.frame(99); T.eq(txt('banner'),'COMBATTI!'); });
T.test('portraits and names', () => { T.eq(txt('name0'),'REN'); T.eq(txt('name1'),'KAEL'); T.ok($('face0').style.backgroundImage.includes('data:image/jpeg')); });
T.test('HUD fits a 360 px tall screen and does not cover the fighters', () => { const t=$('timer').getBoundingClientRect(); T.ok(t.bottom < innerHeight*.25); for(const id of ['meter0','meter1']) T.ok($(id).getBoundingClientRect().bottom<=innerHeight); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — `hudUpdate` cambia il DOM solo quando un valore cambia (testo, `transform: scaleX`). Le animazioni sono classi CSS rimesse con un reflow (`void el.offsetWidth`). Le zone sicure usano `env(safe-area-inset-*)`.
- [ ] **Step 4: verifica** — `hud` in 640×360 e 844×390 → tutti PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: HUD con barre, timer, combo ed energia"`

### Task 11: Menu, pausa, fine partita, orientamento e ciclo di gioco

**Files:**
- Create: `src/h_menu.js`, `tests/menu.test.js`, `tests/orient.test.js`
- Modify: `src/head.html` (`#title #pause #end #rotate #tPause #fps`), `src/z_main.js` (ciclo completo), `mk.sh`

**Interfaces:**
- Consumes: `startMatch`, `inputAssign`, `IN`, `renderFrame`, `hudUpdate`, `fxEvents`.
- Produces:
  - `menu = {pause(), resume(), restart(), toTitle()}`, `showScreen(id|null)`, `menuMove(dir)`, `menuPress(device)`, `menuBack()` e `tick(nowMs)`, il ciclo: accumulatore di 1000/60 ms, al massimo `loop.maxSteps` passi per tick, poi `renderFrame` e `hudUpdate`.
  - Schermate:
    - `#title`: logo "VOIDRISE / FIGHTERS" in CSS (Bebas Neue, corsivo, taglio arancione) sul fondale sfocato, con i pulsanti obliqui "1 GIOCATORE · ALLENAMENTO" e "2 GIOCATORI";
    - `#pause`: "RIPRENDI", "RICOMINCIA", "AVVERSARIO: FERMO/CASUALE" (solo in allenamento), "TORNA AL MENU";
    - `#end`: "VINCE REN!" / "VINCE KAEL!" / "PAREGGIO", con "RIVINCITA" e "MENU";
    - `#rotate`: icona SVG di un telefono che gira e il testo "Gira il telefono in orizzontale".
  - Pausa: Esc, Start (pulsante 9) o il tasto `#tPause` (sotto il timer, visibile sempre e cliccabile col mouse).
  - Navigazione: frecce e WASD, Invio, Spazio o J per confermare, Esc per tornare indietro; croce o levetta, A (0) e B (1) dal controller; tocco e clic.
  - `menuPress` riceve il dispositivo che ha confermato e lo passa a `inputAssign` ("chi sceglie è G1").
  - Al primo tocco di un pulsante del titolo: schermo intero e `screen.orientation.lock('landscape')`, dentro `try`, come `lockLandscape` di Storm-Blade.
  - Con `?fps=1` nell'indirizzo `#fps` mostra ogni 500 ms gli FPS, i ms della sim e i ms del disegno.

- [ ] **Step 1: test** — `tests/menu.test.js` (default) e `tests/orient.test.js` (`--viewport 390x844 --touch --mobile`):
```js
// menu.test.js
T.test('title → training with keyboard', () => { key('Enter'); keyUp('Enter'); T.eq(__VF.G.state,'fight'); T.eq(__VF.G.mode,'training'); });
T.test('Esc pauses, Esc resumes', () => { key('Escape'); keyUp('Escape'); T.eq(__VF.G.state,'pause'); key('Escape'); keyUp('Escape'); T.eq(__VF.G.state,'fight'); });
T.test('pause stops the sim', () => { __VF.menu.pause(); const f=__VF.G.S.frame; __VF.tick(performance.now()+500); T.eq(__VF.G.S.frame,f); __VF.menu.resume(); });
T.test('opponent toggle in training', () => { __VF.menu.pause(); clickText('AVVERSARIO'); T.eq(__VF.G.S.dummy,'casuale'); __VF.menu.resume(); });
T.test('gamepad navigates the title and becomes G1', () => { __VF.menu.toTitle(); fakePads([{buttons:{13:1}}]); padTick(); fakePads([{buttons:{0:1}}]); padTick(); fakePads([]); padTick(); T.eq(__VF.G.mode,'versus'); T.eq(__VF.IN.assign[0].pad,0); });
T.test('match end screen and rematch', () => { endMatch(0); T.eq(__VF.G.state,'end'); T.eq(txt('endTitle'),'VINCE REN!'); clickText('RIVINCITA'); T.eq(__VF.G.state,'fight'); });
T.test('mouse click on pause button', () => { $('tPause').click(); T.eq(__VF.G.state,'pause'); __VF.menu.resume(); });
T.test('hidden tab pauses and does not catch up', () => { Object.defineProperty(document,'hidden',{value:true,configurable:true}); document.dispatchEvent(new Event('visibilitychange'));
  T.eq(__VF.G.state,'pause'); Object.defineProperty(document,'hidden',{value:false,configurable:true}); __VF.menu.resume(); const f=__VF.G.S.frame; __VF.tick(performance.now()+5000); T.ok(__VF.G.S.frame-f<=4); });
T.test('restart resets the match', () => { __VF.startMatch('versus',{seed:1}); __VF.frame(200); __VF.menu.pause(); clickText('RICOMINCIA'); T.eq(__VF.G.state,'fight'); T.eq(__VF.G.S.frame,0); });
T.test('pad disconnect pauses', () => { __VF.startMatch('versus',{seed:1}); fakePads([{}]); __VF.inputAssign('versus',{pad:0}); __VF.menu.resume(); window.dispatchEvent(new Event('gamepaddisconnected')); T.eq(__VF.G.state,'pause'); fakePads([]); });
// orient.test.js
T.test('portrait shows the rotate screen and pauses a fight', () => { T.ok(vis('rotate')); __VF.startMatch('training',{seed:1,dummy:'fermo'}); window.dispatchEvent(new Event('resize')); T.eq(__VF.G.state,'pause'); });
T.test('landscape hides it', () => { setViewport(844,390); window.dispatchEvent(new Event('resize')); T.ok(!vis('rotate')); });
```
- [ ] **Step 2: verifica che fallisca** — FAIL.
- [ ] **Step 3: implementazione** — In `#app` è visibile una sola schermata alla volta. Il controller nei menu si legge con fronti di pressione (un passo per pressione). `visibilitychange` con `hidden` → pausa e `G.last = null`, così al ritorno non si recupera il tempo perso. `gamepaddisconnected` di un controller assegnato durante `fight` → pausa.
- [ ] **Step 4: verifica** — `menu` e `orient` (`--viewport 390x844 --touch --mobile`) → tutti PASS. Poi tutti i test (comandi in "Tutti i test" nel Task 12).
- [ ] **Step 5: commit** — `git commit -am "Tappa 1: menu, pausa, fine partita, orientamento"`

### Task 12: Misure, documenti e pubblicazione

**Files:**
- Create: `tests/perf.test.js`, `docs/HANDOFF.md`
- Modify: `CLAUDE.md` (link della pagina pubblicata e comandi)

- [ ] **Step 1: test di misura** — `tests/perf.test.js`:
```js
T.test('sim step under 0.3 ms', () => { const S=__VF.simCreate({seed:2,mode:'versus',chars:['ren','kael']}); const t=performance.now(); for(let i=0;i<6000;i++) __VF.simStep(S,scripted(i),__VF.dummyInput(S,1)); const ms=(performance.now()-t)/6000; T.info('sim ms/frame '+ms.toFixed(4)); T.ok(ms<.3); });
T.test('render ms per frame (headless, reference only)', () => { __VF.startMatch('versus',{seed:2}); const t=performance.now(); for(let i=0;i<300;i++){ __VF.frame(1); } T.info('render+sim ms/frame '+((performance.now()-t)/300).toFixed(2)); });
T.test('round length with and without hitstop', () => { const len=stop=>{ const k=JSON.stringify(__VF.CFG.stop); if(!stop) for(const c in __VF.CFG.stop) __VF.CFG.stop[c]=0; const S=fight(); let n=0; while(S.phase==='fight'&&n<99*60){ __VF.simStep(S,scripted(n),0); n++; } Object.assign(__VF.CFG.stop,JSON.parse(k)); return n; };
  T.info('frames to KO: hitstop '+len(true)+', no hitstop '+len(false)); });
```
- [ ] **Step 2: tutti i test** — devono passare tutti, con 0 errori:
```bash
bash mk.sh
for f in smoke sim attack guard round input render fighter3d feel hud menu perf; do python3 tests/run.py tests/$f.test.js || break; done
python3 tests/run.py tests/render.test.js --viewport 844x390
python3 tests/run.py tests/hud.test.js --viewport 844x390
python3 tests/run.py tests/touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/orient.test.js --viewport 390x844 --touch --mobile
```
- [ ] **Step 3: prova a mano nel browser** — Playwright a 844×390 con il touch, poi a 1280×720 con la tastiera. Una partita a 2 completa fino a "VINCE …", un allenamento con il manichino casuale e una pausa. Console senza errori. Screenshot di titolo, lotta, colpo forte e fine partita da mostrare a Denis.
- [ ] **Step 4: documenti** — `docs/HANDOFF.md` in italiano: stato, comandi di build e test, interfacce chiave, valori misurati (ms della sim, durata del round con e senza hitstop), idee "per dopo". In `CLAUDE.md` vanno i comandi di test e, dopo la pubblicazione, il link della pagina.
- [ ] **Step 5: pubblicazione** — Nuova pagina Claude "Voidrise Fighters" con `index.html` (le immagini sono già dentro). Un solo file; icona `game`. Annota l'URL in `CLAUDE.md`.
- [ ] **Step 6: commit e push** — `git add -A && git commit -m "Tappa 1: misure, documenti, pubblicazione" && git push -u origin tappa1-basi`. Si unisce a `main` solo dopo la prova di Denis.
