// The way into a match (spec §3): main menu, the «Gioca» block, the local versus options, the fighter select, the arena,
// the VS screen (the bridge to the fight is u9_bridge.js), the results. Locked entries say what is still to come.
const VSOPT = {r: null, tm: null};   // the versus options chosen in this session (indexes into CFG.ui.vsOpts)

function playScreens() {
  // --- Main menu: entries on the left, the «Gioca» block under them (Arcade, Online, Versus locale), the player's chip
  // top right, the last fighter used large on the right with the rival behind (the layered scene).
  navRegister({id: 'menu', scene: 'menu', layers: () => ({hero: (SV && SV.lastChar) || 'ren'}),
    build(r) {
      const soon = 'In arrivo nella prossima versione';
      const top = uiEl('div', 'mmTop');   // the logo in its own row (on short screens the menu is a wrapping row: the logo keeps its own width)
      top.appendChild(cLogo('s'));
      r.appendChild(top);
      const list = uiEl('div', 'mmList');
      list.setAttribute('data-wrap', '');
      const vs = cItem({label: 'Versus locale', act0: 'vs', act: () => navGo('vsopts')});
      vs.classList.add('mmVs');
      list.append(cItem({label: 'Gioca', act0: 'play', act: () => navFocus(vs)}),
        cItem({label: 'Allenamento', act0: 'train', act: dev => { if (dev === 'touch') mnFullscreen(); navGo('select', {mode: 'training', step: 0, picks: []}); }}),
        cItem({label: 'Profilo', act0: 'profile', act: () => navGo('profile')}), cItem({label: 'Pass stagionale', locked: true, note: soon}), cItem({label: 'Impostazioni', act0: 'settings', act: () => navGo('settings')}));
      const cards = uiEl('div', 'mmCards');
      cards.append(cCard({label: 'Arcade', img: ASSETS['ui/card_arcade.webp'], locked: true, note: 'Arcade in arrivo'}),
        cCard({label: 'Online', img: ASSETS['ui/card_online.webp'], locked: true, note: 'Modalità online in arrivo'}));
      const play = uiEl('div', 'mmPlay');
      play.append(cards, vs);
      const chip = uiEl('div', 'mmChip');
      r.append(list, play, chip);
    },
    enter() { const c = this.root.querySelector('.mmChip'); c.innerHTML = ''; c.appendChild(cChip()); },
    back() { return false; }});
  // --- Local versus: rounds and time, Ren for player 1 on the left and Kael for player 2 on the right, «Combatti».
  navRegister({id: 'vsopts', scene: 'versus', layers: () => ({hero: 'ren', rival: 'kael'}),
    build(r) {
      const O = CFG.ui.vsOpts;
      if (VSOPT.r === null) { VSOPT.r = O.r; VSOPT.tm = O.tm; }
      r.appendChild(cBack());
      const head = cHead('Versus locale', 'Scontro tra due giocatori sullo stesso dispositivo.');
      const mid = uiEl('div', 'voMid');
      mid.append(cStepper({label: 'Round', values: O.rounds, i: VSOPT.r, onChange: v => { VSOPT.r = O.rounds.indexOf(v); }}),
        cStepper({label: 'Tempo', values: O.time, i: VSOPT.tm, fmt: v => (v ? String(v) : '∞'), onChange: v => { VSOPT.tm = O.time.indexOf(v); }}));
      const tags = uiEl('div', 'voTags', '<span class="voTag">Giocatore 1</span><span class="voTag">Giocatore 2</span>');
      const go = cBtn({label: 'Combatti', kind: 'main', act0: 'fight', act: dev => {
        if (dev === 'touch') mnFullscreen();
        navGo('select', {mode: 'versus', rounds: O.rounds[VSOPT.r], timeS: O.time[VSOPT.tm], step: 0, picks: []});
      }});
      go.querySelector('.ub').setAttribute('data-first', '');
      r.append(head, mid, tags, go);
    }});
  selScreen();
  arenaScreen();
  resultsScreen();
}

// --- Fighter select (params {mode, rounds, timeS, step, picks}): a 2x6 grid of slanted portraits; the focused fighter
// large on the side that is choosing (G1 left, G2 right) with name and stats; the other side shows the pick already made
// (G1's, while G2 chooses) or the fighter waiting. Confirm a playable fighter to go on; a locked or coming one says why.
// Same fighter on both sides: «In arrivo» (it needs a second copy of the model and an alternate colour).
const SEL = {p: null, at: {l: -1e9, r: -1e9}};
function selImg(c) {
  if (!c) return ASSETS['ui/silhouette.webp'];
  return ASSETS['ui/' + c + '_full.webp'] || ASSETS['ui/face_' + c + '.webp'] || ASSETS['ui/silhouette.webp'];
}
function selInfo(box, c, tag) {
  const C = c && CFG.ui.chars[c];
  box.innerHTML = '';
  box.appendChild(uiEl('div', 'selTag', uiEsc(tag)));
  const name = uiEl('div', 'selName', C ? uiEsc(C.name) : '');
  box.appendChild(name);
  const st = uiEl('div', 'selStats');
  if (C && C.pot) st.append(cStatBar('Potenza', C.pot, 5), cStatBar('Velocità', C.vel, 5), cStatBar('Difficoltà', C.dif, 5));
  else if (C && C.lock) st.appendChild(uiEl('div', 'selLock', UI_ICON.lock + '<span>' + uiEsc(C.lock) + '</span>'));
  else if (!C && tag) st.appendChild(uiEl('div', 'selLock', '<span>In attesa</span>'));   // (the side waiting for its choice)
  box.appendChild(st);
  return {name, st};
}
function selFig(el, c, ghost) {
  el.style.backgroundImage = 'url(' + selImg(c) + ')';
  el.className = 'selFig ' + el.dataset.side + (ghost ? ' ghost' : '') + (c && CFG.ui.chars[c] && CFG.ui.chars[c].lock ? ' locked' : '') + (c ? '' : ' none');
  el.dataset.c = c || '';
  el.classList.remove('in'); void el.offsetWidth; el.classList.add('in');
  const aura = el.previousElementSibling;   // the light behind the figure takes its colour and flashes (selLife)
  if (aura && aura.classList.contains('selAura')) { aura.dataset.c = c && !(CFG.ui.chars[c] && CFG.ui.chars[c].lock) ? c : ''; aura.dataset.ghost = ghost ? '1' : ''; }
  SEL.at[el.dataset.side] = performance.now();
}
// The select's life: each figure breathes, the light behind it breathes and flashes as the figure changes.
function selLife(r, now) {
  for (const s of ['l', 'r']) {
    const f = r.querySelector('.selFig.' + s), a = f.previousElementSibling, k = Math.max(0, 1 - (now - SEL.at[s]) / 520);
    f.style.scale = (1 + .007 * (1 - Math.cos(now / 760 + (s === 'r' ? 1.7 : 0)))).toFixed(4);
    a.style.opacity = a.dataset.c ? ((a.dataset.ghost ? .35 : .75) + .15 * Math.sin(now / 640 + (s === 'r' ? 2 : 0)) + .6 * k * k).toFixed(3) : '0';
    a.style.scale = (1 + .12 * k).toFixed(3);
  }
}
function selPick(i) {
  const p = SEL.p, c = CFG.ui.roster[i];
  if (!c) { uiToast('Nuovo combattente in arrivo', 'soon'); return; }
  const C = CFG.ui.chars[c];
  if (C.lock) { uiToast('Si sblocca con il ' + C.lock, 'soon'); return; }
  if (p.mode === 'versus' && p.step === 1 && p.picks[0] === c) { uiToast('Scontro speculare in arrivo: scegli un altro combattente', 'soon'); return; }
  const base = {mode: p.mode, rounds: p.rounds, timeS: p.timeS};
  if (p.mode === 'versus' && p.step === 0) { navGo('select', Object.assign(base, {step: 1, picks: [c]})); return; }
  const chars = p.mode === 'versus' ? [p.picks[0], c] : [c, c === 'ren' ? 'kael' : 'ren'];
  navGo('arena', Object.assign(base, {chars}));
}
function selScreen() {
  navRegister({id: 'select', scene: 'select', layers: () => ({}),
    build(r) {
      r.appendChild(cBack());
      r.appendChild(uiEl('div', 'selTitle', '<i></i><b>Scegli il combattente</b><i></i>'));
      r.appendChild(uiEl('div', 'selWho'));
      for (const side of ['l', 'r']) { const f = uiEl('i', 'selFig ' + side); f.dataset.side = side; r.appendChild(uiEl('i', 'selAura ' + side)); r.appendChild(f); r.appendChild(uiEl('div', 'selInfo ' + side)); }
      const grid = uiEl('div', 'selGrid');
      CFG.ui.roster.forEach((c, i) => {
        const C = c && CFG.ui.chars[c];
        const sl = uiEl('div', 'uSlot' + (!c ? ' soon' : C.lock ? ' lock' : ''), '<i style="background-image:url(' + (c ? (ASSETS['ui/face_' + c + '.webp'] || '') : ASSETS['ui/silhouette.webp']) + ')"></i>' + (C && C.lock ? UI_ICON.lock : ''));
        sl.dataset.i = i;
        uiFocusable(sl, () => selPick(i));
        grid.appendChild(sl);
      });
      r.appendChild(grid);
      const ok = cBtn({label: 'Conferma', kind: 'main', act: () => selPick(SEL.cur || 0)});
      ok.classList.add('selOk');
      r.appendChild(ok);
    },
    enter(p) {
      SEL.p = p; const r = this.root, vs = p.mode === 'versus', side = vs && p.step === 1 ? 'r' : 'l', other = side === 'l' ? 'r' : 'l';
      r.querySelector('.selWho').textContent = vs ? (p.step ? 'Giocatore 2' : 'Giocatore 1') : 'Allenamento';
      // the side that is not choosing: G1's pick (versus, step 1), or who waits (versus step 0: player 2; training: the dummy)
      const oc = vs ? (p.step ? p.picks[0] : null) : null;
      selInfo(r.querySelector('.selInfo.' + other), oc, vs ? (p.step ? 'Giocatore 1' : 'Giocatore 2') : 'Avversario');
      selFig(r.querySelector('.selFig.' + other), oc, true);
      SEL.side = side;
      r.querySelectorAll('.uSlot').forEach(s => s.classList.toggle('pick', vs && p.step === 1 && CFG.ui.roster[+s.dataset.i] === p.picks[0]));
      // the focus starts on the last fighter used (or, for G2, the other one)
      const want = vs && p.step ? (p.picks[0] === 'ren' ? 'kael' : 'ren') : (SV && SV.lastChar) || 'ren';
      const first = r.querySelector('.uSlot[data-i="' + Math.max(0, CFG.ui.roster.indexOf(want)) + '"]');
      r.querySelectorAll('[data-first]').forEach(e => e.removeAttribute('data-first'));
      first.setAttribute('data-first', '');
      SEL.cur = null;
    },
    onFocus(el) {
      if (!el.classList.contains('uSlot')) return;
      const i = +el.dataset.i, c = CFG.ui.roster[i], r = this.root;
      if (SEL.cur === i) return;
      SEL.cur = i;
      const box = r.querySelector('.selInfo.' + SEL.side), p = SEL.p;
      r.querySelectorAll('#uSelName,#uSelStats').forEach(e => e.removeAttribute('id'));
      const info = selInfo(box, c, p.mode === 'versus' ? (p.step ? 'Giocatore 2' : 'Giocatore 1') : 'Allenamento');
      info.name.id = 'uSelName'; info.st.id = 'uSelStats';
      selFig(r.querySelector('.selFig.' + SEL.side), c, false);
    },
    frame(now) { if (LY.q !== 'bassa') selLife(this.root, now); }});
}

// --- Arena (params {mode, chars, rounds, timeS}): the arena with the focus fills the background; the cards of the coming
// arenas say so. «Conferma»: the VS in a versus, straight into the fight (after the loading) in training.
const AR_SEL = {cur: 'cascata'};   // the arena chosen on the arena screen (ARENA is the 3D arena of d_render.js)
function arenaGo(dev) {
  const p = NAV.stack[NAV.stack.length - 1].params, next = {mode: p.mode, chars: p.chars, rounds: p.rounds, timeS: p.timeS, arena: AR_SEL.cur, dev};
  if (p.mode === 'versus') { navGo('vs', next); return; }
  try { bridgeWarm(next.arena, next.chars); } catch (_) { uiToast("Impossibile caricare l'arena", 'err'); return; }   // training: no VS, straight in
  bridgeStart(next);
}
function arenaScreen() {
  navRegister({id: 'arena', scene: 'select', layers: () => ({}),
    build(r) {
      r.appendChild(cBack());
      r.appendChild(cHead("Scegli l'arena", 'Seleziona il luogo dello scontro.'));
      const cards = uiEl('div', 'arCards');
      for (const A of CFG.ui.arenas) {
        const img = A.ok ? '' : ASSETS['ui/arena_' + A.id + '.webp'];
        const c = cCard({label: A.name, img, locked: !A.ok, note: 'Arena in arrivo', act: dev => { AR_SEL.cur = A.id; arenaGo(dev); }});
        c.dataset.arena = A.id;
        if (A.ok) c.setAttribute('data-first', '');
        cards.appendChild(c);
      }
      r.appendChild(cards);
      const ok = cBtn({label: 'Conferma', kind: 'main', act0: 'go', act: dev => arenaGo(dev)});
      ok.classList.add('arOk');
      r.appendChild(ok);
    },
    enter() {
      const shot = bridgeArenaShot(), img = this.root.querySelector('.ucard[data-arena="cascata"] .ucardImg');   // the real arena, drawn by the game
      if (shot && img) img.style.backgroundImage = 'url(' + shot + ')';
    },
    onFocus(el) {
      const id = el.dataset.arena;
      if (!id) return;
      const A = CFG.ui.arenas.find(a => a.id === id);
      if (A.ok) AR_SEL.cur = id;
      const bg = el.querySelector('.ucardImg').style.backgroundImage.replace(/^url\(["']?|["']?\)$/g, '');
      layersSet('select', {arenaImg: bg});
    }});
  vsScreen();
}

// --- VS (params {mode, chars, arena, rounds, timeS, dev}): the two faces come in from the sides, the golden VS, a line each;
// «Caricamento…» follows the real loading. It stays CFG.ui.vs.minMs (its clock runs on shown frames only, so a hidden
// page does not start the fight); once loaded, a tap or a key after CFG.ui.vs.tapAfterMs starts at once. Loading
// failed: the reason, «Riprova» and «Indietro».
const VS = {t: 0, last: 0, ready: false, err: false, started: false, tok: 0, p: null, el: null, burst: false, settled: false};
// The VS's entrance (a pure function of the screen's clock t, ms): the two faces slam in from the sides, the VS mark
// crashes down on them with a flash, a shake and a burst of sparks, the names rise; then the faces push in slowly and the
// seam of light between them flickers. Driven from the frame, no CSS animation.
function vsLife(t) {
  if (t >= 1000) { if (VS.settled) return; VS.settled = true; t = 1000; } else VS.settled = false;   // after its entrance the VS stands still
  NAV.screens.vs.root.classList.toggle('settled', VS.settled);
  const E = VS.el, k = x => Math.max(0, Math.min(1, x)), back = x => 1 + 2.7 * Math.pow(x - 1, 3) + 1.7 * Math.pow(x - 1, 2);   // ease out with an overshoot
  const kl = k(t / 260), kr = k((t - 60) / 260), push = (1 + .02 * Math.sin(Math.PI * k((t - 390) / 500))).toFixed(4);   // the faces flinch as the mark crashes
  E.l.style.translate = (-26 * (1 - back(kl))).toFixed(2) + 'vw 0'; E.l.style.opacity = Math.min(1, kl * 3).toFixed(3); E.l.style.scale = push;
  E.r.style.translate = (26 * (1 - back(kr))).toFixed(2) + 'vw 0'; E.r.style.opacity = Math.min(1, kr * 3).toFixed(3); E.r.style.scale = push;
  const km = k((t - 220) / 170), hit = t - 390;
  E.mark.style.opacity = km > 0 ? '1' : '0';
  E.mark.style.scale = (1 + 2.2 * (1 - km * km)).toFixed(3);
  E.flash.style.opacity = hit >= 0 ? (.75 * (1 - k(hit / 240))).toFixed(3) : '0';
  const sh = hit >= 0 ? 14 * (1 - k(hit / 380)) : 0, e = Math.floor(t / 33);
  E.stage.style.translate = sh ? ((uiRand(e, 1) - .5) * sh).toFixed(1) + 'px ' + ((uiRand(e, 2) - .5) * sh).toFixed(1) + 'px' : '0px 0px';
  if (hit >= 0 && !VS.burst) { VS.burst = true; const b = E.mark.getBoundingClientRect(); layersBurst(b.left + b.width / 2, b.top + b.height / 2, 48, '#ffc46a', 1.4); }
  E.lines.style.opacity = (.75 * k(t / 120) * (1 - k((t - 380) / 520))).toFixed(3);
  E.lines.style.translate = (-(t * .8) % 90).toFixed(1) + 'px 0';
  E.seam.style.opacity = hit < 0 ? '0' : t < 1000 ? (.5 + .5 * uiRand(Math.floor(t / 70), 3)).toFixed(3) : '.85';
  const kn = k((t - 450) / 300);
  for (const s of E.sides) { s.style.opacity = kn.toFixed(3); s.style.translate = '0 ' + (16 * (1 - kn)).toFixed(1) + 'px'; }
}
function vsLoad() {
  const tok = ++VS.tok, r = NAV.screens.vs.root;
  VS.ready = VS.err = false;
  r.classList.remove('err');
  UIB.preload(VS.p.arena, VS.p.chars).then(() => { if (tok === VS.tok) VS.ready = true; },
    () => { if (tok !== VS.tok) return; VS.err = true; r.classList.add('err'); navFocus(r.querySelector('.vsErr .ub')); });
}
function vsStart() { if (VS.started) return; VS.started = true; bridgeStart(VS.p); }
function vsScreen() {
  navRegister({id: 'vs', scene: 'vs', layers: () => ({}),
    build(r) {
      r.innerHTML = '<div class="vsStage"><i class="vsLines"></i><i class="vsF l"></i><i class="vsF r"></i><div class="vsMark"><b>VS</b><i></i></div></div><i class="vsFlash"></i>' +
        '<div class="vsSide l"><b class="vsName"></b><i class="vsLine"></i></div><div class="vsSide r"><b class="vsName"></b><i class="vsLine"></i></div>' +
        '<div class="vsLoad"><span>Caricamento…</span></div><div class="vsErr"><b>Impossibile caricare l\'arena</b><div class="vsErrB"></div></div>';
      const bar = cProgress(0); bar.classList.add('vsBar'); r.querySelector('.vsLoad').appendChild(bar);
      r.querySelector('.vsErrB').append(cBtn({label: 'Riprova', act: () => vsLoad()}), cBtn({label: 'Indietro', act: () => navBack()}));
      const q = s => r.querySelector(s);
      VS.el = {stage: q('.vsStage'), lines: q('.vsLines'), l: q('.vsF.l'), r: q('.vsF.r'), mark: q('.vsMark'), seam: q('.vsMark i'), flash: q('.vsFlash'), sides: [...r.querySelectorAll('.vsSide')]};
    },
    enter(p) {
      VS.p = p; VS.t = 0; VS.last = 0; VS.started = false; VS.burst = false; VS.settled = false;
      const r = this.root, lines = CFG.ui.lines[p.chars[0] + '>' + p.chars[1]] || ['', ''];
      ['l', 'r'].forEach((s, i) => {
        const c = p.chars[i];
        const f = r.querySelector('.vsF.' + s), A = CFG.ui.art[c + '_vs'];
        f.style.backgroundImage = 'url(' + (ASSETS['ui/' + c + '_vs.webp'] || '') + ')';
        if (A) f.style.setProperty('--ax', (A[0] * A[1]).toFixed(4));
        r.querySelector('.vsSide.' + s + ' .vsName').textContent = CFG.ui.chars[c].name;
        r.querySelector('.vsSide.' + s + ' .vsLine').textContent = lines[i];
      });
      r.querySelector('.vsBar').uiSet(0);
      vsLife(0);
      vsLoad();
    },
    leave() { VS.tok++; },
    frame(now) {
      const dt = VS.last ? Math.min(100, now - VS.last) : 0, M = CFG.ui.vs.minMs;
      VS.last = now; VS.t += dt;
      vsLife(VS.t);
      if (VS.err) return;
      NAV.screens.vs.root.querySelector('.vsBar').uiSet(VS.ready ? Math.min(1, M ? VS.t / M : 1) : Math.min(.85, VS.t / Math.max(M, 1)));
      if (VS.ready && VS.t >= M) vsStart();
    },
    any() { if (!VS.ready || VS.err || VS.t < CFG.ui.vs.tapAfterMs) return false; vsStart(); return true; }});
}

// --- Results (params = bridgeResult: {mode, chars, winner, wins, rounds, hits, maxCombo, timeS}), as the reference: the
// winner large on the left, «Vittoria» between laurels (or «Pareggio»), who won, the score between the two faces, the XP
// of the match part by part with the total counted up and the level bar (G1 is the player of this device: statistics and
// XP are his, saved at once), then «Rivincita», «Cambia personaggio», «Menu principale». Esc / B = the menu.
const RS = {t: 0, last: 0, xp: 0, lv: null, done: false, burst: false};
// The results' entrance (pure function of the clock t, ms): «Vittoria» crashes in and glows, the laurels open out from
// it, a burst of gold (or of silver for a draw).
function rsLife(root, t) {
  const k = x => Math.max(0, Math.min(1, x)), kt = k(t / 320), e = 1 - Math.pow(1 - kt, 3), title = root.querySelector('.rsTitle');
  title.style.opacity = Math.min(1, kt * 2.5).toFixed(3);
  title.style.scale = (1 + .8 * (1 - e)).toFixed(3);
  const kl = k((t - 160) / 320), el = 1 - Math.pow(1 - kl, 3);
  root.querySelectorAll('.rsLaurel').forEach((l, i) => { l.style.opacity = kl.toFixed(3); l.style.translate = ((i ? -1 : 1) * 26 * (1 - el)).toFixed(1) + 'px 0'; });
  if (t >= 320 && !RS.burst) {
    RS.burst = true;
    const b = title.getBoundingClientRect(), draw = root.classList.contains('draw');
    layersBurst(b.left + b.width / 2, b.top + b.height / 2, 40, draw ? '#d8d4e8' : '#ffc46a', 1.2);
  }
}
const RS_LAUREL = '<svg class="rsLaurel" viewBox="0 0 40 80" aria-hidden="true"><path d="M31 77C11 62 6 36 19 5"/>' +
  [[12, 60, -40], [9, 47, -60], [10, 34, -75], [14, 22, -95], [19, 12, -110], [22, 66, 30], [17, 52, 15], [16, 39, 0], [19, 27, -20]].map(([x, y, a]) =>
    '<ellipse cx="' + x + '" cy="' + y + '" rx="6.5" ry="2.6" transform="rotate(' + a + ' ' + x + ' ' + y + ')"/>').join('') + '</svg>';
function resultsScreen() {
  navRegister({id: 'results', scene: 'results', guardMs: CFG.menu.endGuardMs,
    layers: r => ({hero: r.chars[r.winner === 1 ? 1 : 0], rival: null, pose: 'win'}),
    build(root) {
      root.innerHTML = '<div class="rsCol"><div class="rsHead">' + RS_LAUREL + '<b class="rsTitle"></b>' + RS_LAUREL + '</div><div class="rsWho"></div>' +
        '<div class="rsScore"><i class="rsFace l"></i><b class="rsNum"></b><i class="rsFace r"></i></div>' +
        '<div class="rsXp"><div class="rsParts"></div><div class="rsTot">+<span class="rsXpN">0</span> XP</div><div class="rsBar"></div><div class="rsLvl"></div></div></div><div class="rsBtns"></div>';
      root.querySelector('.rsBar').appendChild(cProgress(0));
      root.querySelector('.rsBtns').append(
        cBtn({label: 'Rivincita', act0: 'rematch', act: () => menu.restart()}),
        cBtn({label: 'Cambia personaggio', act0: 'change', act: () => {
          const p = {mode: G.mode, rounds: G.opts && G.opts.rounds, timeS: G.opts && G.opts.timeS, step: 0, picks: []};
          G.state = 'title'; G.S = null; navReset('menu'); navGo('select', p); menuSync();
        }}),
        cBtn({label: 'Menu principale', act0: 'menu', act: () => menu.toTitle()}));
    },
    enter(r) {
      const root = this.root, q = s => root.querySelector(s), N = c => CFG.ui.chars[c].name;
      q('.rsTitle').textContent = r.winner === 2 ? 'Pareggio' : 'Vittoria';
      q('.rsWho').textContent = r.winner === 2 ? '' : 'Vince G' + (r.winner + 1) + ' · ' + N(r.chars[r.winner]);
      q('.rsNum').textContent = r.wins[0] + ' – ' + r.wins[1];
      q('.rsFace.l').style.backgroundImage = 'url(' + uiFace(r.chars[0]) + ')';
      q('.rsFace.r').style.backgroundImage = 'url(' + uiFace(r.chars[1]) + ')';
      // the player's statistics and XP (a local versus: G1 is this device's player)
      const x = progMatchXp(r), before = progLevel(SV.xp);
      progRecord(SV, r);
      const up = progAddXp(SV, x.xp), after = progLevel(SV.xp);
      saveWrite();
      q('.rsParts').innerHTML = x.parts.map(p => '<div class="rsPart"><span>' + uiEsc(p.label) + '</span><b>+' + p.xp + ' XP</b></div>').join('');
      q('.rsLvl').textContent = up.after > up.before ? 'Livello ' + up.after + '!' : 'Livello ' + up.after;
      root.classList.toggle('lvup', up.after > up.before);
      root.classList.remove('done');
      RS.t = 0; RS.last = 0; RS.xp = x.xp; RS.done = false; RS.burst = false;
      root.classList.toggle('draw', r.winner === 2);
      rsLife(root, 0);
      RS.lv = {from: up.after > up.before ? 0 : before.into / before.need, to: after.into / after.need};
      q('.rsXpN').textContent = '0';
      q('.rsBar .uprog').uiSet(RS.lv.from);
    },
    // the total climbs from 0 in CFG.ui.t.go * 2 ms of shown frames, the level bar with it; then a bump (and «Livello N!»)
    frame(now) {
      if (RS.done) return;
      const dt = RS.last ? Math.min(100, now - RS.last) : 0;
      RS.last = now; RS.t += dt;
      const k = Math.min(1, RS.t / (CFG.ui.t.go * 2)), e = 1 - (1 - k) * (1 - k), root = this.root;
      rsLife(root, RS.t);
      root.querySelector('.rsXpN').textContent = String(Math.round(RS.xp * e));
      root.querySelector('.rsBar .uprog').uiSet(RS.lv.from + (RS.lv.to - RS.lv.from) * e);
      if (k >= 1 && RS.t >= 500) { RS.done = true; root.classList.add('done'); rsLife(root, 1e4); }
    },
    back() { menu.toTitle(); return false; }});
}
