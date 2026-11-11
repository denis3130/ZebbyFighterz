// The way into a match (spec §3): main menu, the «Gioca» block, the local versus options, the fighter select, the arena.
// Later tasks add the VS screen and the results to this file. Locked entries say what is still to come.
const VSOPT = {r: null, tm: null};   // the versus options chosen in this session (indexes into CFG.ui.vsOpts)

function playScreens() {
  // --- Main menu: entries on the left, the «Gioca» block under them (Arcade, Online, Versus locale), the player's chip
  // top right, the last fighter used large on the right with the rival behind (the layered scene).
  navRegister({id: 'menu', scene: 'menu', layers: () => ({hero: (SV && SV.lastChar) || 'ren'}),
    build(r) {
      const soon = 'In arrivo nella prossima versione';
      r.appendChild(cLogo('s'));
      const list = uiEl('div', 'mmList');
      list.setAttribute('data-wrap', '');
      const vs = cItem({label: 'Versus locale', act0: 'vs', act: () => navGo('vsopts')});
      vs.classList.add('mmVs');
      list.append(cItem({label: 'Gioca', act0: 'play', act: () => navFocus(vs)}),
        cItem({label: 'Allenamento', act0: 'train', act: dev => { if (dev === 'touch') mnFullscreen(); navGo('select', {mode: 'training', step: 0, picks: []}); }}),
        cItem({label: 'Profilo', locked: true, note: soon}), cItem({label: 'Pass stagionale', locked: true, note: soon}), cItem({label: 'Impostazioni', locked: true, note: soon}));
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
}

// --- Fighter select (params {mode, rounds, timeS, step, picks}): a 2x6 grid of slanted portraits; the focused fighter
// large on the side that is choosing (G1 left, G2 right) with name and stats; the other side shows the pick already made
// (G1's, while G2 chooses) or the fighter waiting. Confirm a playable fighter to go on; a locked or coming one says why.
// Same fighter on both sides: «In arrivo» (it needs a second copy of the model and an alternate colour).
const SEL = {p: null};
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
      for (const side of ['l', 'r']) { const f = uiEl('i', 'selFig ' + side); f.dataset.side = side; r.appendChild(f); r.appendChild(uiEl('div', 'selInfo ' + side)); }
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
    }});
}

// --- Arena (params {mode, chars, rounds, timeS}). Until the full screen of Task 10: the one arena to play and «Conferma».
function arenaScreen() {
  navRegister({id: 'arena', scene: 'select', layers: () => ({}),
    build(r) {
      r.appendChild(cBack());
      r.appendChild(cHead("Scegli l'arena", 'Seleziona il luogo dello scontro.'));
      const cards = uiEl('div', 'arCards');
      cards.appendChild(cCard({label: 'La Grande Cascata', act: () => navFocus(r.querySelector('.arOk .ub'))}));
      r.appendChild(cards);
      const ok = cBtn({label: 'Conferma', kind: 'main', act0: 'go', act: dev => { const p = NAV.stack[NAV.stack.length - 1].params; mnStart(p.mode, dev, {chars: p.chars, rounds: p.rounds, timeS: p.timeS}); }});
      ok.classList.add('arOk');
      ok.querySelector('.ub').setAttribute('data-first', '');
      r.appendChild(ok);
    }});
}
