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
        try { t.fn(); out.push({name: t.name, ok: true}); }
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
