// The game cycle around the fight, on the interface navigation (u1_nav.js): pause, end of a match, "gira il telefono",
// full screen, auto-pause and the FPS counter (pause menu "FPS: Sì / No", or ?fps=1). Reads the sim, never changes it
// (except the training dummy's mode, chosen in the pause menu).
const MN = {rot: false, fps: {on: false, t: 0, frames: 0, sim: 0, steps: 0, draw: 0}};

function mnEl(id) { return document.getElementById(id); }
function mnTouchDevice() { return (window.matchMedia && matchMedia('(pointer:coarse)').matches) || navigator.maxTouchPoints > 0; }
function mnSeed() { return (Math.random() * 1e9) | 0; }
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
  mnEl('uiLayers').classList.toggle('off', st === 'fight' || st === 'pause');   // the layered scene only behind the menus
  mnEl('hud').style.visibility = st === 'fight' ? '' : 'hidden';   // (the pause screen covers the fight, as in the reference)
  mnEl('tPause').classList.toggle('on', st === 'fight' && !MN.rot);
  mnEl('rotate').classList.toggle('on', MN.rot);
  touchShow(st === 'fight' && !MN.rot);
}
const menu = {
  pause() { if (G.state !== 'fight') return; G.state = 'pause'; navReset('pause'); menuSync(); },
  resume() { if (G.state !== 'pause' || MN.rot) return; inputMaskHeld(); G.state = 'fight'; G.last = null; menuSync(); },
  restart() { if (!G.S) return; inputMaskHeld(); startMatch(G.mode, Object.assign({}, G.opts, {seed: mnSeed(), dummy: G.S.dummy})); },
  toTitle() { G.state = 'title'; G.S = null; navReset('menu'); menuSync(); },
};
// The match is over (the sim reached phase 'end'): the results (u5_play.js).
function menuCheckEnd() {
  const S = G.S; if (G.state !== 'fight' || !S || S.phase !== 'end') return;
  G.state = 'end'; navReset('results', bridgeResult(S)); menuSync();
}
// Phones: full screen and landscape lock on the first tap of a menu button (unsupported on iOS: ignored).
function mnFullscreen() {
  const lock = () => { try { const p = screen.orientation && screen.orientation.lock && screen.orientation.lock('landscape'); if (p && p.catch) p.catch(() => {}); } catch (_) {} };
  try { const el = document.documentElement, r = el.requestFullscreen && el.requestFullscreen(); if (r && r.then) r.then(lock, lock); else lock(); } catch (_) { lock(); }
}
// A match from the menus: whoever confirms is G1 (dev); opts = {rounds, timeS, chars} from the versus options.
function mnStart(mode, dev, opts) {
  inputAssign(mode, dev);
  inputMaskHeld();
  startMatch(mode, Object.assign({seed: mnSeed(), dummy: 'fermo'}, opts));
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
// Builds a column of components into r: [cBtn options...], each with act0 = its action name (data-act).
function mnColumn(r, head, btns, fn) {
  r.appendChild(head);
  const col = uiEl('div', 'ucol');
  col.setAttribute('data-wrap', '');
  for (const o of btns) col.appendChild(cBtn(Object.assign({act: dev => fn(o.act0, dev)}, o)));
  r.appendChild(col);
}
function menuScreens() {
  navRegister({id: 'pause', build(r) {
    mnColumn(r, cHead('Pausa'), [{label: 'Riprendi', act0: 'resume'}, {label: 'Ricomincia', act0: 'restart'},
      {label: 'Avversario: Fermo', act0: 'opp', id: 'bOpp', txId: 'oppTx'}, {label: 'FPS: No', act0: 'fps', id: 'bFps', txId: 'fpsTx'}, {label: 'Abbandona', act0: 'quit'}], a => {
      if (a === 'resume') menu.resume();
      else if (a === 'restart') menu.restart();
      else if (a === 'opp') { G.S.dummy = G.S.dummy === 'casuale' ? 'fermo' : 'casuale'; mnPauseRefresh(); }
      else if (a === 'fps') mnFpsSet(!MN.fps.on, true);
      else if (a === 'quit') uiConfirm({title: 'Abbandonare la partita?', text: 'Tornerai al menu principale.', yes: 'Abbandona', no: 'Annulla'}).then(ok => { if (ok) menu.toTitle(); });
    });
  }, enter() { mnPauseRefresh(); }, back() { menu.resume(); return false; }});
  navRootOf(NAV.screens.pause);   // built now: the FPS label and the opponent button exist from the start   // built now: the FPS label and the opponent button exist from the start
}
function menuInit() {
  navInit();
  layersInit();
  menuScreens();
  introScreens();
  playScreens();
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
