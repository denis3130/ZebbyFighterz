// The game cycle around the fight, on the interface navigation (u1_nav.js): pause, end of a match, "gira il telefono",
// full screen, auto-pause and the FPS counter (pause menu "FPS: Sì / No", or ?fps=1). Reads the sim, never changes it
// (except the training dummy's mode, chosen in the pause menu).
// Until the real main menu and results screens (Interface U1 Tasks 8 and 11), 'menu' is the old title's two choices and
// 'results' the old end screen, ported to the new navigation.
const MN = {rot: false, fps: {on: false, t: 0, frames: 0, sim: 0, steps: 0, draw: 0}};

function mnEl(id) { return document.getElementById(id); }
function mnTouchDevice() { return (window.matchMedia && matchMedia('(pointer:coarse)').matches) || navigator.maxTouchPoints > 0; }
function mnSeed() { return (Math.random() * 1e9) | 0; }
// A plain interface button (styled by u_style.css): label, data-act, optional id.
function mnBtn(label, act, id) { return '<div class="ub" data-focus role="button" data-act="' + act + '"' + (id ? ' id="' + id + '"' : '') + '><span' + (id ? ' id="' + id.replace(/^b/, '').toLowerCase() + 'Tx"' : '') + '>' + label + '</span></div>'; }
function mnActs(r, fn) { r.querySelectorAll('[data-act]').forEach(b => { b.uiAct = dev => fn(b.dataset.act, dev); }); }

// The pause screen's opponent button exists only in training; its label shows the current dummy.
function mnPauseRefresh() {
  const b = mnEl('bOpp'); if (!b) return;
  b.hidden = G.mode !== 'training';
  mnEl('oppTx').textContent = 'Avversario: ' + (G.S && G.S.dummy === 'casuale' ? 'Casuale' : 'Fermo');
}
// Puts the HUD, the pause button, the rotate screen and the touch controls in line with G.state. A fight has no menu screen.
function menuSync() {
  const st = G.state;
  if (st === 'fight' && NAV.cur) navClear();
  mnEl('hud').style.visibility = st === 'title' || st === 'end' ? 'hidden' : '';
  mnEl('tPause').classList.toggle('on', st === 'fight' && !MN.rot);
  mnEl('rotate').classList.toggle('on', MN.rot);
  touchShow(st === 'fight' && !MN.rot);
}
const menu = {
  pause() { if (G.state !== 'fight') return; G.state = 'pause'; navReset('pause'); menuSync(); },
  resume() { if (G.state !== 'pause' || MN.rot) return; inputMaskHeld(); G.state = 'fight'; G.last = null; menuSync(); },
  restart() { if (!G.S) return; inputMaskHeld(); startMatch(G.mode, {seed: mnSeed(), dummy: G.S.dummy}); },
  toTitle() { G.state = 'title'; G.S = null; navReset('menu'); menuSync(); },
};
// The match is over (the sim reached phase 'end'): the end screen with the winner.
function menuCheckEnd() {
  const S = G.S; if (G.state !== 'fight' || !S || S.phase !== 'end') return;
  const title = S.winner === 2 ? 'PAREGGIO' : 'VINCE ' + fighterOf(S, S.winner).char.toUpperCase() + '!';
  G.state = 'end'; navReset('results', {title}); menuSync();
}
// Phones: full screen and landscape lock on the first tap of a menu button (unsupported on iOS: ignored).
function mnFullscreen() {
  const lock = () => { try { const p = screen.orientation && screen.orientation.lock && screen.orientation.lock('landscape'); if (p && p.catch) p.catch(() => {}); } catch (_) {} };
  try { const el = document.documentElement, r = el.requestFullscreen && el.requestFullscreen(); if (r && r.then) r.then(lock, lock); else lock(); } catch (_) { lock(); }
}
function mnStart(mode, dev) {
  inputAssign(mode, dev);   // whoever confirms is G1
  inputMaskHeld();
  startMatch(mode, {seed: mnSeed(), dummy: 'fermo'});
}
// Kept names (the real loop and the tests call them): confirm, move, back, controller polling.
function menuPress(dev) { navPress(dev || 'kb'); }
function menuMove(dir) { navMove(dir === -1 ? 'up' : dir === 1 ? 'down' : dir); }
// Esc / B: a fight pauses; on a screen, that screen's back (the pause screen resumes, the end screen goes to the menu).
function menuBack() {
  if (MN.rot) return;
  if (G.state === 'fight') menu.pause(); else navBack();
}
function menuPad() { navPadPoll(performance.now()); }
// "Gira il telefono": touch device held upright. A fight pauses; the menus are covered.
function menuOrient() {
  MN.rot = mnTouchDevice() && window.innerHeight > window.innerWidth;
  if (MN.rot && G.state === 'fight') menu.pause();
  menuSync();
}
// The FPS counter on or off (save = remember it in the device save); the pause menu's label follows.
function mnFpsSet(on, save) {
  const f = MN.fps; f.on = on; f.t = f.frames = f.sim = f.steps = f.draw = 0;
  mnEl('fps').textContent = on ? 'FPS …' : '';
  mnEl('fps').classList.toggle('on', on);
  if (mnEl('fpsTx')) mnEl('fpsTx').textContent = 'FPS: ' + (on ? 'Sì' : 'No');
  if (save && SV) { SV.settings.showFps = on; saveWrite(); }
}
// At start: on with ?fps=1 in the address, else as last chosen on this device.
function menuFpsInit() { mnFpsSet(/[?&]fps=1\b/.test(location.search) || !!(SV && SV.settings.showFps), false); }
// FPS, average sim ms per step and render ms per frame, refreshed every 500 ms.
function menuFps(now, simMs, steps, drawMs) {
  const f = MN.fps; if (!f.on) return;
  f.frames++; f.sim += simMs; f.steps += steps; f.draw += drawMs;
  if (!f.t) f.t = now;
  if (now - f.t < 500) return;
  mnEl('fps').textContent = 'FPS ' + Math.round(f.frames * 1000 / (now - f.t)) + ' · sim ' + (f.steps ? f.sim / f.steps : 0).toFixed(2) + ' ms · disegno ' + (f.draw / f.frames).toFixed(1) + ' ms';
  f.t = now; f.frames = f.sim = f.steps = f.draw = 0;
}
function menuScreens() {
  navRegister({id: 'menu', build(r) {
    r.innerHTML = '<div class="logo"><div class="l1">VOIDRISE</div><div class="l2">FIGHTERS</div></div><div class="ucol" data-wrap>' +
      mnBtn('1 Giocatore · Allenamento', 'train') + mnBtn('2 Giocatori', 'vs') + '</div>';
    mnActs(r, (a, dev) => { if (dev === 'touch') mnFullscreen(); mnStart(a === 'train' ? 'training' : 'versus', dev); });
  }});
  navRegister({id: 'pause', build(r) {
    r.innerHTML = '<div class="mh">Pausa</div><div class="ucol" data-wrap>' + mnBtn('Riprendi', 'resume') + mnBtn('Ricomincia', 'restart') +
      mnBtn('Avversario: Fermo', 'opp', 'bOpp') + mnBtn('FPS: No', 'fps', 'bFps') + mnBtn('Abbandona', 'quit') + '</div>';
    mnActs(r, a => {
      if (a === 'resume') menu.resume();
      else if (a === 'restart') menu.restart();
      else if (a === 'opp') { G.S.dummy = G.S.dummy === 'casuale' ? 'fermo' : 'casuale'; mnPauseRefresh(); }
      else if (a === 'fps') mnFpsSet(!MN.fps.on, true);
      else if (a === 'quit') menu.toTitle();
    });
  }, enter() { mnPauseRefresh(); }, back() { menu.resume(); return false; }});
  navRegister({id: 'results', guardMs: CFG.menu.endGuardMs, build(r) {
    r.innerHTML = '<div class="mh" id="endTitle"></div><div class="ucol" data-wrap>' + mnBtn('Rivincita', 'rematch') + mnBtn('Menu', 'menu') + '</div>';
    mnActs(r, a => { if (a === 'rematch') menu.restart(); else menu.toTitle(); });
  }, enter(p) { mnEl('endTitle').textContent = p.title || ''; }, back() { menu.toTitle(); return false; }});
  for (const id of ['menu', 'pause', 'results']) navRootOf(NAV.screens[id]);   // built now: the FPS label and the opponent button exist from the start
}
function menuInit() {
  navInit();
  menuScreens();
  uiTap(mnEl('tPause'), menu.pause);
  window.addEventListener('resize', menuOrient);
  window.addEventListener('orientationchange', menuOrient);
  document.addEventListener('visibilitychange', () => { if (document.hidden) { menu.pause(); G.last = null; } });
  window.addEventListener('gamepaddisconnected', e => {
    const i = e && e.gamepad ? e.gamepad.index : undefined;
    if (G.state === 'fight' && IN.assign && IN.assign.some(a => a.pad !== null && (i === undefined || a.pad === i))) menu.pause();
  });
  menuFpsInit();
}
