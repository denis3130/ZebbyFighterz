// tests/lib.js — tiny in-page test API. Tests in one file run in order and share page state.
window.T = (() => {
  const tests = [];
  class Fail extends Error {}
  const fmt = v => { try { const s = JSON.stringify(v); return s === undefined ? String(v) : s; } catch (_) { return String(v); } };
  const pre = msg => (msg ? msg + ': ' : '');
  return {
    test(name, fn) { tests.push({name, fn}); },
    eq(a, b, msg) { if (a !== b) throw new Fail(pre(msg) + 'expected ' + fmt(b) + ', got ' + fmt(a)); },
    ok(v, msg) { if (!v) throw new Fail(msg || 'expected truthy, got ' + fmt(v)); },
    near(a, b, eps, msg) { if (!(Math.abs(a - b) <= eps)) throw new Fail(pre(msg) + 'expected ' + b + ' ±' + eps + ', got ' + a); },
    // printed by run.py as "INFO msg"
    info(msg) { (window.TINFO = window.TINFO || []).push(String(msg)); },
    // runs simStep n times with the given inputs (a: player 0, b: player 1)
    feed(S, n, a = 0, b = 0) { for (let i = 0; i < n; i++) __VF.simStep(S, a, b); },
    // deterministic Math.random (mulberry32): a failing run can be replayed with the same seed (run.py --seed N)
    seed(s) { let a = s >>> 0; Math.random = () => { a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; },
    SEED: 1,
    // synchronous on purpose: no await between tests, so the real-time frame loop never runs in between
    async run() {
      this.seed(this.SEED);
      const out = [];
      for (const t of tests) {
        // a test may return a Promise (a dialog's answer): awaited here; it settles in microtasks, so no frame runs in between
        try { const r = t.fn(); if (r && typeof r.then === 'function') await r; out.push({name: t.name, ok: true}); }
        catch (e) { out.push({name: t.name, ok: false, msg: e instanceof Fail ? e.message : String(e && e.stack || e)}); }
      }
      return out;
    },
  };
})();

// Shared helpers of the fight-logic suites (sim, attack, guard, round): B = buttons,
// N(opts) = new versus sim (seed 1, Ren vs Kael, opts override) with the 100-frame intro already played (no input) and
// the frame counter back at 0, so a test counts its own frames; F(S, i) = active fighter of side i.
const B = __VF.BTN;
function N(opts) {
  const S = __VF.simCreate(Object.assign({seed: 1, mode: 'versus', chars: ['ren', 'kael']}, opts));
  T.feed(S, __VF.CFG.round.intro, 0, 0); S.frame = 0;
  return S;
}
function fight(opts) { return N(opts); }
function trainingFight() { return N({mode: 'training', dummy: 'fermo'}); }
function F(S, i) { return __VF.fighterOf(S, i); }
// near(S) = the fighters 700 mm apart (x -350 / +350), in range of the light attacks.
function near(S) { F(S, 0).x = -350; F(S, 1).x = 350; }
// comboPPPH(S) = P tapped three times, each tap in the chain window of the move before (it lands during that move's
// hitstop and waits in the buffer), then P held 12 frames for the heavy: p1 p2 p3 hp, damage 30+35+45+72.
function comboPPPH(S) {
  for (let i = 0; i < 3; i++) {
    T.feed(S, 1, B.P, 0); T.feed(S, 1, 0, 0);
    for (let j = 0; j < 30 && !S.ev.some(e => e.t === 'hit'); j++) T.feed(S, 1, 0, 0);
  }
  T.feed(S, 12, B.P, 0); T.feed(S, 40, 0, 0);
}

// Input helpers (Task 6). key/keyUp/keyUpAll = keyboard events on window; fakePads(list) replaces navigator.getGamepads
// (each entry in the compact form {buttons:{2:1}, axes:[-.9,0]}; [] = no pads); pd/pm/pu/fire = PointerEvents on an element.
const _held = new Set();
function key(code) { _held.add(code); window.dispatchEvent(new KeyboardEvent('keydown', {code, bubbles: true, cancelable: true})); }
function keyUp(code) { _held.delete(code); window.dispatchEvent(new KeyboardEvent('keyup', {code, bubbles: true, cancelable: true})); }
function keyUpAll() { for (const c of [..._held]) keyUp(c); }
const _realPads = navigator.getGamepads ? navigator.getGamepads.bind(navigator) : null;
function fakePads(list) {
  if (!list.length) { Object.defineProperty(navigator, 'getGamepads', {value: () => [], configurable: true}); return; }
  const pads = list.map(p => {
    const buttons = Array.from({length: 17}, (_, i) => ({pressed: !!(p.buttons && p.buttons[i]), value: p.buttons && p.buttons[i] ? 1 : 0}));
    const a = p.axes || [], axes = [a[0] || 0, a[1] || 0, a[2] || 0, a[3] || 0];
    return {connected: true, buttons, axes};
  });
  Object.defineProperty(navigator, 'getGamepads', {value: () => pads, configurable: true});
}
function $(id) { return document.getElementById(id); }
function vis(id) {
  const e = $(id); if (!e) return false;
  const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
  return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden';
}
function txt(id) { return $(id) ? $(id).textContent.trim() : ''; }
function fire(id, type, x, y, pointerId) {
  $(id).dispatchEvent(new PointerEvent(type, {pointerId: pointerId === undefined ? 1 : pointerId, clientX: x, clientY: y,
    bubbles: true, cancelable: true, pointerType: 'touch', isPrimary: true}));
}
function pd(id, x, y, pointerId) { fire(id, 'pointerdown', x, y, pointerId); }
function pm(id, x, y, pointerId) { fire(id, 'pointermove', x, y, pointerId); }
function pu(id, x, y, pointerId) { fire(id, 'pointerup', x, y, pointerId); }
// Final fix wave. ptr(el, type, pointerId, dx, dy) = a touch PointerEvent on element el at its centre (+dx, +dy px);
// tapEl(el, pointerId) = a touch tap (down + up at the centre) on el, with no click (as Chrome does while another
// finger is down); mid(el) = el's centre [x, y].
function mid(el) { const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }
function ptr(el, type, pointerId, dx, dy) { const [x, y] = mid(el);
  el.dispatchEvent(new PointerEvent(type, {pointerId, clientX: x + (dx || 0), clientY: y + (dy || 0), bubbles: true, cancelable: true, pointerType: 'touch', isPrimary: false})); }
function tapEl(el, pointerId) { ptr(el, 'pointerdown', pointerId); ptr(el, 'pointerup', pointerId); }
// skipIntro = play the 100-frame intro of __VF.G.S; nearG = the two fighters of __VF.G.S at -350 / +350.
function skipIntro() { __VF.frame(__VF.CFG.round.intro); }
function nearG() { const S = __VF.G.S; __VF.fighterOf(S, 0).x = -350; __VF.fighterOf(S, 1).x = 350; }

// Render helpers (Task 7). pxAt(t, u, v) = draw __VF.G.S at time t ms, then read at once (same JS turn, before the
// browser presents the frame) the pixel at u, v (0..1, v from the top) -> [r, g, b, a]; diff/sum = over RGB;
// setViewport(w, h) = fake innerWidth/innerHeight (dispatch 'resize' after it).
function pxAt(t, u, v) {
  __VF.renderFrame(__VF.G.S, t);
  const gl = __VF.renderer.getContext(), w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
  const x = Math.min(w - 1, Math.floor(u * w)), y = Math.min(h - 1, Math.floor(v * h)), p = new Uint8Array(4);
  gl.readPixels(x, h - 1 - y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p);
  return [p[0], p[1], p[2], p[3]];
}
function diff(a, b) { return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]); }
function sum(p) { return p[0] + p[1] + p[2]; }
function setViewport(w, h) {
  Object.defineProperty(window, 'innerWidth', {value: w, configurable: true});
  Object.defineProperty(window, 'innerHeight', {value: h, configurable: true});
}

// Feel helpers (Task 9). scripted(i) = a fixed, deterministic input for frame i (player 0): walks in, taps a chain, holds
// P for a heavy, throws the Special, jumps and kicks, backs off; repeats every 200 frames.
function scripted(i) {
  const k = i % 200;
  if (k < 20) return B.R;
  if (k === 20 || k === 30 || k === 40) return B.P;
  if (k >= 55 && k < 70) return B.P;
  if (k === 90) return B.S;
  if (k >= 110 && k < 114) return B.U | B.R;
  if (k === 125 || k === 130) return B.K;
  if (k >= 150 && k < 160) return B.L;
  return 0;
}
// hitOnce(move) = one hit of `move` (default 'p1'; 'hp' = P held) through the real sim: the earlier effects expire first
// (the fx clock jumps 1 s ahead), then a fresh versus match, the fighters close, P tapped or held until the hit event.
// Every sim step gets fxEvents; the frame is drawn at the hit's time. Returns that time (ms of the fx clock).
function hitOnce(move) {
  move = move || 'p1';
  const V = __VF, S0 = V.FX.now;
  V.fxUpdate(S0 + 1000);
  V.startMatch('versus', {seed: 1}); skipIntro(); nearG();
  const S = V.G.S;
  let t = V.FX.now + 100;
  for (let i = 0; i < 60; i++) {
    const held = move === 'hp' ? i < 12 : i === 0;
    V.simStep(S, held ? B.P : 0, 0);
    V.fxEvents(S, t);
    if (S.ev.some(e => e.t === 'hit')) { V.renderFrame(S, t); return t; }
    t += 16;
  }
  throw new Error('no hit from ' + move);
}

// HUD helpers (Task 10). startFight = a versus match (seed 1) past the intro; comboG(n) (n <= 4) = side 0 lands an n-hit combo
// on side 1 in __VF.G.S, tapping through __VF.frame (the input override) until the defender's combo counter reaches n, then
// lets go (the defender is still in hitstun); barScale(id) = the element's current scaleX from its transform.
function startFight() { __VF.startMatch('versus', {seed: 1}); skipIntro(); }
function comboG(n) {
  startFight(); nearG();
  const S = __VF.G.S, IN = __VF.IN, taps = [B.P, B.K, B.P, B.P];   // chain p1 k1 p2 p3 (taps only, no heavy)
  // one tap per hit still to come, each tapped as soon as the one before has landed (it waits in the input buffer and
  // chains), so no buffered tap lands an extra hit after the n-th
  let t = 0;
  for (let i = 0; i < 400 && F(S, 1).combo < n; i++) {
    let p = 0;
    if (t === 0 || (F(S, 1).combo === t && t < n)) { p = taps[t++]; nearG(); }   // pushback would otherwise carry the defender out of reach
    IN.override[0] = p; __VF.frame(1);
  }
  IN.override[0] = null;
  if (F(S, 1).combo < n) throw new Error('combo of ' + n + ' not reached');
}
function barScale(id) {
  const m = new DOMMatrix(getComputedStyle($(id)).transform);
  return m.a;
}

// Menu helpers (Task 11). padTick() = run the menu's controller polling once (the real loop does it every frame);
// endMatch(winner) = drive the running match to phase 'end' with that winner (0, 1 or 2 = draw) and let the loop react once.
function padTick() { __VF.menuPad(); }
function endMatch(winner) {
  const S = __VF.G.S;
  S.phase = 'end'; S.winner = winner;
  __VF.tick(performance.now());
}

// padsAt(list) = navigator.getGamepads returns list as it is (null entries = empty slots), each pad in fakePads' compact form.
function padsAt(list) {
  const pads = list.map(p => p && {connected: true, axes: [0, 0, 0, 0].map((v, i) => (p.axes && p.axes[i]) || 0),
    buttons: Array.from({length: 17}, (_, i) => ({pressed: !!(p.buttons && p.buttons[i]), value: p.buttons && p.buttons[i] ? 1 : 0}))});
  Object.defineProperty(navigator, 'getGamepads', {value: () => pads, configurable: true});
}

// later(ms, fn) = run fn with performance.now() ms ahead (tests are synchronous: this stands in for waiting).
function later(ms, fn) {
  const real = performance.now.bind(performance);
  performance.now = () => real() + ms;
  try { fn(); } finally { performance.now = real; }
}

// Interface helpers (U1). The pointer guard against double taps is off for the tests (they click one after another);
// 'double tap navigates once' turns it back on. keyTap(code) = key down and up; navEls() = the focusable elements on
// screen (inside an open dialog in #uiOver only, as the navigation does); byText(t) = the first of them whose text
// contains t; focused() = the text of the element with the focus; uiClick(t) = a click on byText(t) (mouse or
// programmatic, as a page click); hover(t) = the mouse moving over it.
if (__VF.CFG.ui) __VF.CFG.ui.t.tapGuard = 0;
function keyTap(code) { key(code); keyUp(code); }
function navEls() {
  const o = document.getElementById('uiOver'), box = o && o.firstElementChild ? o : document;
  return [...box.querySelectorAll('[data-focus]')].filter(e => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden');
}
function byText(t) { const e = navEls().find(e => e.textContent.includes(t)); if (!e) throw new Error('no focusable element with "' + t + '"'); return e; }
function focused() { const f = __VF.UI.NAV.focus; return f ? f.textContent.trim() : null; }
function uiClick(t) { byText(t).click(); }
function hover(t) { byText(t).dispatchEvent(new PointerEvent('pointermove', {bubbles: true, cancelable: true, pointerType: 'mouse', pointerId: 1})); }
// mount(list) = the test screen 'uiMount' (root #sc-uiMount) showing the given elements in a column, focus on the first.
function mount(list) {
  if (!__VF.UI.NAV.screens.uiMount) __VF.navRegister({id: 'uiMount', enter(p) { this.root.innerHTML = ''; const box = document.createElement('div');
    box.style.cssText = 'display:flex;flex-direction:column;gap:18px;align-items:flex-start'; p.list.forEach(e => box.appendChild(e)); this.root.appendChild(box); }});
  __VF.navReset('uiMount', {list});
}
// type(el, text) = set a text field's value as a person typing would leave it, then tell the page (input event).
function type(el, text) { el.value = text; el.dispatchEvent(new Event('input', {bubbles: true})); }
// navFocusText(t) = give the focus to the focusable element whose text contains t.
function navFocusText(t) { __VF.navFocus(byText(t)); }
// slot(i) = the i-th slot of the fighter select; navFocusSlot(i) = give it the focus; focusedSlot() = the index of the focused slot (-1 if none).
function slot(i) { return document.querySelectorAll('#sc-select .uSlot')[i]; }
function navFocusSlot(i) { __VF.navFocus(slot(i)); }
function focusedSlot() { return [...document.querySelectorAll('#sc-select .uSlot')].indexOf(__VF.UI.NAV.focus); }
// toArena(mode) = from the menu to the arena screen with the keyboard: training (Ren against Kael) or versus (G1 Ren,
// G2 Kael), so a test can do the last confirm (the one that starts the match) with the device it checks.
function toArena(mode) {
  __VF.menu.toTitle();
  if (mode === 'training') { uiClick('Allenamento'); keyTap('Enter'); }
  else { uiClick('Versus locale'); uiClick('Combatti'); keyTap('Enter'); keyTap('Enter'); }
  if (__VF.UI.NAV.cur !== 'arena') throw new Error('arena not reached: ' + __VF.UI.NAV.cur);
}
