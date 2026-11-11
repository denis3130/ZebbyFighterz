// Menus and the game cycle around the fight: title, pause, end screen, navigation (keyboard, controller, touch, mouse),
// "gira il telefono", full screen, auto-pause and the FPS counter (pause menu "FPS: SÌ / NO", or ?fps=1). Reads the sim,
// never changes it (except the training dummy's mode, chosen in the pause menu).
// One screen at a time inside #ui; one focused button per screen (class 'f', orange like the reference).
const MN = {scr: null, focus: {}, rot: false, endAt: 0, ptype: 'mouse', pad: [], tapEnd: 0, fps: {on: false, t: 0, frames: 0, sim: 0, steps: 0, draw: 0}};
const MN_SCREENS = ['title', 'pause', 'end'];
const MN_REPEAT = [350, 130];   // controller direction held: ms before the first repeat, ms between repeats
const MN_TAP = {slop: 12, ms: 700};   // a tap may end this many px off its button; the click after it is dropped this many ms
// Preferences kept on this device (localStorage, versioned; storage that is missing or throws, as in a sandboxed frame,
// only means they are not kept): fps = the FPS counter is on.
const MN_PREFS = {key: 'voidrise.prefs', v: 1};

function mnEl(id) { return document.getElementById(id); }
function mnTouchDevice() { return (window.matchMedia && matchMedia('(pointer:coarse)').matches) || navigator.maxTouchPoints > 0; }
function mnButtons(id) { return [...mnEl(id).querySelectorAll('.mb')].filter(b => !b.hidden); }
function mnEndGuard() { return MN.scr === 'end' && performance.now() - MN.endAt < CFG.menu.endGuardMs; }
function mnSeed() { return (Math.random() * 1e9) | 0; }

// The pause screen's opponent button exists only in training; its label shows the current dummy.
function mnPauseRefresh() {
  mnEl('bOpp').hidden = G.mode !== 'training';
  mnEl('oppTx').textContent = 'AVVERSARIO: ' + (G.S && G.S.dummy === 'casuale' ? 'CASUALE' : 'FERMO');
}
function mnFocus(i) {
  const bs = mnButtons(MN.scr); if (!bs.length) return;
  i = Math.max(0, Math.min(bs.length - 1, i)); MN.focus[MN.scr] = i;
  mnEl(MN.scr).querySelectorAll('.mb').forEach(b => b.classList.toggle('f', b === bs[i]));
}
// id = 'title' | 'pause' | 'end' | null (no screen). A newly shown screen focuses its first button.
function showScreen(id) {
  MN.scr = id;
  for (const s of MN_SCREENS) mnEl(s).classList.toggle('on', s === id);
  if (id === 'pause') mnPauseRefresh();
  if (id) mnFocus(0);
}
// Puts everything on screen in line with G.state: the screen, the HUD (hidden on title and end), the pause button, the touch controls.
function menuSync() {
  const st = G.state, want = MN_SCREENS.includes(st) ? st : null;
  if (want !== MN.scr) showScreen(want);
  mnEl('hud').style.visibility = st === 'title' || st === 'end' ? 'hidden' : '';
  mnEl('tPause').classList.toggle('on', st === 'fight' && !MN.rot);
  mnEl('rotate').classList.toggle('on', MN.rot);
  touchShow(st === 'fight' && !MN.rot);
}
const menu = {
  pause() { if (G.state !== 'fight') return; G.state = 'pause'; menuSync(); },
  resume() { if (G.state !== 'pause' || MN.rot) return; inputMaskHeld(); G.state = 'fight'; G.last = null; menuSync(); },
  restart() { if (!G.S) return; inputMaskHeld(); startMatch(G.mode, {seed: mnSeed(), dummy: G.S.dummy}); },
  toTitle() { G.state = 'title'; G.S = null; menuSync(); },
};
// The match is over (the sim reached phase 'end'): the end screen with the winner.
function menuCheckEnd() {
  const S = G.S; if (G.state !== 'fight' || !S || S.phase !== 'end') return;
  mnEl('endTitle').textContent = S.winner === 2 ? 'PAREGGIO' : 'VINCE ' + fighterOf(S, S.winner).char.toUpperCase() + '!';
  G.state = 'end'; MN.endAt = performance.now(); menuSync();
}
function menuMove(dir) {
  if (!MN.scr || MN.rot) return;
  const bs = mnButtons(MN.scr), d = dir === 'up' || dir === 'left' || dir < 0 ? -1 : 1;
  mnFocus((MN.focus[MN.scr] + d + bs.length) % bs.length);
}
// Phones: full screen and landscape lock on the first tap of a title button (unsupported on iOS: ignored).
function mnFullscreen() {
  const lock = () => { try { const p = screen.orientation && screen.orientation.lock && screen.orientation.lock('landscape'); if (p && p.catch) p.catch(() => {}); } catch (_) {} };
  try { const el = document.documentElement, r = el.requestFullscreen && el.requestFullscreen(); if (r && r.then) r.then(lock, lock); else lock(); } catch (_) { lock(); }
}
function mnStart(mode, dev) {
  inputAssign(mode, dev);   // whoever confirms is G1
  inputMaskHeld();
  startMatch(mode, {seed: mnSeed(), dummy: 'fermo'});
}
// dev = the device that confirmed: 'kb' (keyboard and mouse), 'touch' or {pad:i}.
function menuPress(dev) {
  if (!MN.scr || MN.rot || mnEndGuard()) return;
  const b = mnButtons(MN.scr)[MN.focus[MN.scr]]; if (!b) return;
  dev = dev || 'kb';
  const act = b.dataset.act;
  if (MN.scr === 'title' && dev === 'touch') mnFullscreen();
  if (act === 'train') mnStart('training', dev);
  else if (act === 'vs') mnStart('versus', dev);
  else if (act === 'resume') menu.resume();
  else if (act === 'restart' || act === 'rematch') menu.restart();
  else if (act === 'opp') { G.S.dummy = G.S.dummy === 'casuale' ? 'fermo' : 'casuale'; mnPauseRefresh(); }
  else if (act === 'fps') mnFpsSet(!MN.fps.on, true);
  else if (act === 'menu') menu.toTitle();
}
// Esc / B: fight -> pause, pause -> resume, end -> title.
function menuBack() {
  if (MN.rot || mnEndGuard()) return;
  if (G.state === 'fight') menu.pause(); else if (G.state === 'pause') menu.resume(); else if (G.state === 'end') menu.toTitle();
}
// Controller, once per frame: Start pauses; in the menus the d-pad or left stick moves (one step per press, repeating
// while held), A confirms, B goes back. Presses are edges against the previous poll.
function menuPad() {
  const l = inputPadList(), now = performance.now();
  for (let i = 0; i < Math.max(l.length, MN.pad.length); i++) {
    const g = l[i];
    if (!g || g.connected === false) { MN.pad[i] = null; continue; }
    const p = MN.pad[i] || (MN.pad[i] = {b: {}, dir: 0, at: 0}), down = n => !!(g.buttons[n] && (g.buttons[n].pressed || g.buttons[n].value > .5));
    const edge = n => { const d = down(n), e = d && !p.b[n]; p.b[n] = d; return e; };
    const a = edge(0), b = edge(1), start = edge(9), ax = g.axes[0] || 0, ay = g.axes[1] || 0;
    const dir = down(12) || down(14) || ay < -.5 || ax < -.5 ? -1 : down(13) || down(15) || ay > .5 || ax > .5 ? 1 : 0;
    if (start) { if (G.state === 'fight') menu.pause(); else if (G.state === 'pause') menu.resume(); continue; }
    if (G.state === 'fight' || !MN.scr) { p.dir = dir; continue; }
    if (dir && (dir !== p.dir || now >= p.at)) { menuMove(dir); p.at = now + MN_REPEAT[dir === p.dir ? 1 : 0]; }
    p.dir = dir;
    if (a) menuPress({pad: i}); else if (b) menuBack();
  }
}
// "Gira il telefono": touch device held upright. A fight pauses; the menus are covered.
function menuOrient() {
  MN.rot = mnTouchDevice() && window.innerHeight > window.innerWidth;
  if (MN.rot && G.state === 'fight') G.state = 'pause';
  menuSync();
}
function mnPrefsLoad() { try { const p = JSON.parse(localStorage.getItem(MN_PREFS.key)); return p && p.v === MN_PREFS.v ? p : {}; } catch (_) { return {}; } }
function mnPrefsSave(p) { try { localStorage.setItem(MN_PREFS.key, JSON.stringify(Object.assign(mnPrefsLoad(), p, {v: MN_PREFS.v}))); } catch (_) {} }
// The FPS counter on or off (save = remember it on this device); the pause menu's label follows.
function mnFpsSet(on, save) {
  const f = MN.fps; f.on = on; f.t = f.frames = f.sim = f.steps = f.draw = 0;
  mnEl('fps').textContent = on ? 'FPS …' : '';
  mnEl('fps').classList.toggle('on', on);
  mnEl('fpsTx').textContent = 'FPS: ' + (on ? 'SÌ' : 'NO');
  if (save) mnPrefsSave({fps: on});
}
// At start: on with ?fps=1 in the address, else as last chosen on this device.
function menuFpsInit() { mnFpsSet(/[?&]fps=1\b/.test(location.search) || mnPrefsLoad().fps === true, false); }
// FPS, average sim ms per step and render ms per frame, refreshed every 500 ms.
function menuFps(now, simMs, steps, drawMs) {
  const f = MN.fps; if (!f.on) return;
  f.frames++; f.sim += simMs; f.steps += steps; f.draw += drawMs;
  if (!f.t) f.t = now;
  if (now - f.t < 500) return;
  mnEl('fps').textContent = 'FPS ' + Math.round(f.frames * 1000 / (now - f.t)) + ' · sim ' + (f.steps ? f.sim / f.steps : 0).toFixed(2) + ' ms · disegno ' + (f.draw / f.frames).toFixed(1) + ' ms';
  f.t = now; f.frames = f.sim = f.steps = f.draw = 0;
}
// Activation of an on-screen button (fn): touch and pen on pointerup, when the press began on el (pointerId) and ends on
// it or within MN_TAP.slop px (Chrome makes no click for a tap while another finger is down, e.g. the thumb on the
// stick); a mouse or a programmatic click through click. The click a tap may still produce is dropped, so nothing fires
// twice: a click with pointerType touch or pen, and the first click on any of these buttons within MN_TAP.ms of a tap
// (MN.tapEnd; the tap may have changed the screen, and that click lands on whatever is under the finger now).
function mnTap(el, fn) {
  let id = null;
  el.addEventListener('pointerdown', e => { if (e.pointerType !== 'mouse') id = e.pointerId; });
  el.addEventListener('pointercancel', e => { if (e.pointerId === id) id = null; });
  el.addEventListener('pointerup', e => {
    if (e.pointerId !== id) return;
    id = null;
    const r = el.getBoundingClientRect(), m = MN_TAP.slop;
    if (e.clientX < r.left - m || e.clientX > r.right + m || e.clientY < r.top - m || e.clientY > r.bottom + m) return;
    MN.tapEnd = performance.now() + MN_TAP.ms; fn();
  });
  el.addEventListener('click', e => {
    e.preventDefault();
    if (e.pointerType === 'touch' || e.pointerType === 'pen' || performance.now() < MN.tapEnd) { MN.tapEnd = 0; return; }
    fn();
  });
}
function menuInit() {
  const scr = document.querySelectorAll('.scr .mb');
  window.addEventListener('pointerdown', e => { MN.ptype = e.pointerType === 'touch' ? 'touch' : 'kb'; }, true);
  scr.forEach(b => {
    mnTap(b, () => { if (!MN.scr || MN.rot) return; mnFocus(mnButtons(MN.scr).indexOf(b)); menuPress(MN.ptype); });
    b.addEventListener('pointermove', e => { if (e.pointerType !== 'touch' && MN.scr) mnFocus(mnButtons(MN.scr).indexOf(b)); });
  });
  mnTap(mnEl('tPause'), menu.pause);
  window.addEventListener('keydown', e => {
    const c = e.code;
    if (c === 'Escape') { if (!e.repeat) menuBack(); e.preventDefault(); return; }
    if (G.state === 'fight' || !MN.scr) return;
    const mv = {ArrowUp: 'up', KeyW: 'up', ArrowLeft: 'left', KeyA: 'left', ArrowDown: 'down', KeyS: 'down', ArrowRight: 'right', KeyD: 'right'}[c];
    if (mv) { menuMove(mv); e.preventDefault(); }
    else if (c === 'Enter' || c === 'Space' || c === 'KeyJ') { if (!e.repeat) menuPress('kb'); e.preventDefault(); }
  });
  window.addEventListener('resize', menuOrient);
  window.addEventListener('orientationchange', menuOrient);
  document.addEventListener('visibilitychange', () => { if (document.hidden) { menu.pause(); G.last = null; } });
  window.addEventListener('gamepaddisconnected', e => {
    const i = e && e.gamepad ? e.gamepad.index : undefined;
    if (G.state === 'fight' && IN.assign && IN.assign.some(a => a.pad !== null && (i === undefined || a.pad === i))) menu.pause();
  });
  menuFpsInit();
}
