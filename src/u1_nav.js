// One navigation for every interface screen (spec 2026-11-11-voidrise-interfaccia-design.md §6): a stack of screens,
// one focused element, the same rules on keyboard, mouse, touch and controller. Confirming calls el.uiAct(device, target):
// target = the part of the element that was tapped or clicked (a stepper's arrow), undefined from keyboard and controller.
// A screen is {id, build(root), enter(params, isBack), leave(), back(), tab(d), onFocus(el), guardMs}: its root
// <section class="usc" id="sc-<id>"> is made the first time it is shown. Focusable = any visible [data-focus] element of
// the screen (or of the dialog open in #uiOver). Confirming an element calls el.uiAct(device) or goes to data-go.
// back() returning false keeps the screen (it handled Esc / B itself); guardMs = confirm and back ignored that long after
// the screen appears (the end of a match, so a mashing player does not skip it). any(device) = a screen that reacts to
// any key, any controller button or a tap anywhere outside its buttons (the intro, the title): true = handled.
const NAV = {cur: null, stack: [], screens: {}, focus: null, dev: 'kb', padIx: null, pad: [], down: null, tapEnd: 0, busyUntil: 0, shownAt: 0};
const NAV_TAP = {slop: 12, ms: 700};   // a tap may end this many px off its element; the click a tap may still produce is dropped this long
const NAV_KEYS = {ArrowUp: 'up', KeyW: 'up', ArrowDown: 'down', KeyS: 'down', ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right'};
const NAV_VEC = {up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0]};

function navRegister(def) { NAV.screens[def.id] = def; return def; }
function navRootOf(def) {
  if (!def.root) {
    const r = document.createElement('section');
    r.className = 'usc'; r.id = 'sc-' + def.id;
    document.getElementById('uiScreens').appendChild(r);
    def.root = r;
    if (def.build) def.build(r);
  }
  return def.root;
}
const navDef = () => (NAV.cur ? NAV.screens[NAV.cur] : null);
// The device that confirmed, in the form inputAssign takes: 'kb' (keyboard and mouse), 'touch' or {pad: i}.
function navDevice() { return NAV.dev === 'pad' ? {pad: NAV.padIx || 0} : NAV.dev; }
function navSetDev(d) {
  if (d && typeof d === 'object') { NAV.dev = 'pad'; NAV.padIx = d.pad; }
  else if (d === 'touch' || d === 'kb' || d === 'pad') NAV.dev = d;
}
function navVisible(e) { return e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; }
function navScope() {
  const o = document.getElementById('uiOver');
  if (o && o.firstElementChild) return o;
  const d = navDef();
  return d ? d.root : null;
}
function navItems() { const s = navScope(); return s ? [...s.querySelectorAll('[data-focus]')].filter(navVisible) : []; }
const navIsField = el => !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA');
function navFocus(el) {
  if (NAV.focus === el) return;
  if (NAV.focus) { NAV.focus.classList.remove('f'); if (navIsField(NAV.focus) && document.activeElement === NAV.focus) NAV.focus.blur(); }   // leaving a text field closes its keyboard
  NAV.focus = el || null;
  if (!el) return;
  el.classList.add('f');
  if (navIsField(el) && NAV.dev === 'kb' && document.activeElement !== el) { try { el.focus({preventScroll: true}); } catch (_) {} }   // typing goes to it
  const d = navDef();
  if (d && d.onFocus) d.onFocus(el);
}
const navGuarded = () => { const d = navDef(); return !!(d && d.guardMs && performance.now() - NAV.shownAt < d.guardMs); };

// Shows the stack's top entry (null: no screen, e.g. during a fight). isBack: coming back to it (its focus returns).
function navShow(entry, isBack) {
  const old = navDef();
  if (old) { old.root.classList.remove('on', 'in'); if (old.leave) old.leave(); }
  navFocus(null);
  NAV.cur = null;
  if (!entry) return;
  const def = NAV.screens[entry.id];
  if (!def) throw new Error('unknown screen ' + entry.id);
  const r = navRootOf(def);
  NAV.cur = entry.id;
  if (def.scene && typeof layersSet === 'function') layersSet(def.scene, def.layers ? def.layers(entry.params) : {});   // the layered scene behind this screen
  if (def.enter) def.enter(entry.params, !!isBack);
  r.classList.add('on');
  const items = navItems();
  items.forEach((e, i) => e.style.setProperty('--i', i));   // the cascade: each element enters a little after the one before
  r.classList.remove('in'); void r.offsetWidth; r.classList.add('in');
  const back = isBack && entry.focus !== null ? items[Math.min(entry.focus, items.length - 1)] : null;
  navFocus(back || items.find(e => e.hasAttribute('data-first')) || items[0] || null);
  NAV.shownAt = performance.now(); NAV.busyUntil = NAV.shownAt + CFG.ui.t.tapGuard;
  const b = document.getElementById('uiBlade');
  if (b) { b.classList.remove('go', 'back'); void b.offsetWidth; b.classList.add(isBack ? 'back' : 'go'); }
}
function navSaveFocus() { const top = NAV.stack[NAV.stack.length - 1]; if (top) top.focus = Math.max(0, navItems().indexOf(NAV.focus)); }
function navGo(id, params) { navSaveFocus(); NAV.stack.push({id, params: params || {}, focus: null}); navShow(NAV.stack[NAV.stack.length - 1], false); layersShift(1); }
function navReplace(id, params) { NAV.stack.pop(); NAV.stack.push({id, params: params || {}, focus: null}); navShow(NAV.stack[NAV.stack.length - 1], false); }
function navReset(id, params) { NAV.stack = [{id, params: params || {}, focus: null}]; layersDepth(0); navShow(NAV.stack[0], false); }
function navClear() { NAV.stack = []; navShow(null); }
function navBack() {
  const dlg = document.getElementById('uiDlg');
  if (dlg && dlg.uiBack) { dlg.uiBack(); return; }   // an open dialog answers «no» first
  const d = navDef();
  if (!d || navGuarded()) return;
  if (d.back && d.back() === false) return;
  if (NAV.stack.length <= 1) return;
  NAV.stack.pop();
  navShow(NAV.stack[NAV.stack.length - 1], true);
  layersShift(-1);
}

// Focus moves to the nearest element in the direction (distance along it + 2 x distance across, between centres); none
// there: inside a [data-wrap] box it wraps to the far end, else it stays. A focused element may take the direction
// itself first (el.uiDir(dir) returning true: a stepper changes its value with left/right).
function navCentre(e) { const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }
function navBest(f, items, dir, ahead) {
  const [x0, y0] = navCentre(f), v = NAV_VEC[dir];
  let best = null, bs = Infinity;
  for (const e of items) {
    if (e === f) continue;
    const [x, y] = navCentre(e), dx = x - x0, dy = y - y0, along = dx * v[0] + dy * v[1], across = Math.abs(dx * v[1] + dy * v[0]);
    if (ahead && along <= 1) continue;
    const s = along + 2 * across;
    if (s < bs) { bs = s; best = e; }
  }
  return best;
}
function navMove(dir) {
  const f = NAV.focus;
  if (f && f.uiDir && f.uiDir(dir)) return;
  const items = navItems();
  if (!items.length) return;
  if (!f || !items.includes(f)) { navFocus(items[0]); return; }
  let n = navBest(f, items, dir, true);
  if (!n) {
    const box = f.closest('[data-wrap]');
    if (box) n = navBest(f, items.filter(e => box.contains(e)), dir, false);   // (the most negative "along" = the far end)
  }
  if (n) navFocus(n);
}
// Confirm the focused element (keyboard, controller; a pointer confirms through navPointerAct).
function navPress(dev) {
  navSetDev(dev);
  if (navGuarded()) return;
  const el = NAV.focus;
  if (el && navItems().includes(el)) navAct(el);
}
function navAct(el, target) {
  if (el.uiAct) el.uiAct(navDevice(), target);
  else if (el.dataset.go) navGo(el.dataset.go);
}
function navTab(d) {
  const def = navDef();
  if (!def) return;
  if (def.tab) { def.tab(d); return; }
  const t = navScope() && navScope().querySelector('[data-tabs]');
  if (t && t.uiTab) t.uiTab(d);
}
// A pointer confirm: only an element of the screen in front (not one under an open dialog), and not in the first
// CFG.ui.t.tapGuard ms of a screen (a double tap would confirm on the next screen too).
function navPointerAct(el, dev, target) {
  if (MN.rot || !navItems().includes(el)) return;
  navSetDev(dev);
  if (navIsField(el)) { navFocus(el); return; }   // a tap on a text field is for typing in it, not a confirm
  if (performance.now() < NAV.busyUntil || navGuarded()) return;
  navFocus(el); navAct(el, target);
}

// Activation of a button outside the screens (fn) — the pause button over the fight: touch and pen on pointerup, when
// the press began on el and ends on it or within NAV_TAP.slop px (Chrome makes no click for a tap while another finger
// is down, e.g. the thumb on the stick); a mouse or programmatic click through click. The click a tap may still produce is
// dropped (pointerType touch or pen, or within NAV_TAP.ms of a tap: it would land on whatever is under the finger now).
function uiTap(el, fn) {
  let id = null;
  el.addEventListener('pointerdown', e => { if (e.pointerType !== 'mouse') id = e.pointerId; });
  el.addEventListener('pointercancel', e => { if (e.pointerId === id) id = null; });
  el.addEventListener('pointerup', e => {
    if (e.pointerId !== id) return;
    id = null;
    if (!navNear(el, e)) return;
    NAV.tapEnd = performance.now() + NAV_TAP.ms; fn('touch');
  });
  el.addEventListener('click', e => {
    e.preventDefault();
    if (e.pointerType === 'touch' || e.pointerType === 'pen' || performance.now() < NAV.tapEnd) { NAV.tapEnd = 0; return; }
    fn('kb');
  });
}
function navNear(el, e) {
  const r = el.getBoundingClientRect(), m = NAV_TAP.slop;
  return e.clientX >= r.left - m && e.clientX <= r.right + m && e.clientY >= r.top - m && e.clientY <= r.bottom + m;
}
// The same rules for every focusable element of a box (the screens, the dialogs), delegated: one press at a time.
function navPointers(box) {
  box.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') return;
    const el = e.target.closest && e.target.closest('[data-focus]');
    NAV.down = el ? {id: e.pointerId, el, t: e.target} : null;
  });
  box.addEventListener('pointercancel', e => { if (NAV.down && NAV.down.id === e.pointerId) NAV.down = null; });
  box.addEventListener('pointerup', e => {
    const d = NAV.down;
    if (!d || d.id !== e.pointerId) {   // a tap outside any button: the screen's any(), if it has one
      const def = navDef();
      if (def && def.any && !MN.rot && def.root.contains(e.target) && !(e.target.closest && e.target.closest('[data-focus]'))) { const dv = e.pointerType === 'mouse' ? 'kb' : 'touch'; navSetDev(dv); def.any(dv); }
      return;
    }
    NAV.down = null;
    if (!navNear(d.el, e)) return;
    NAV.tapEnd = performance.now() + NAV_TAP.ms;
    navPointerAct(d.el, 'touch', d.t);
  });
  box.addEventListener('click', e => {
    const el = e.target.closest && e.target.closest('[data-focus]');
    if (!el) return;
    e.preventDefault();
    if (e.pointerType === 'touch' || e.pointerType === 'pen' || performance.now() < NAV.tapEnd) { NAV.tapEnd = 0; return; }
    navPointerAct(el, 'kb', e.target);
  });
  box.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    const el = e.target.closest && e.target.closest('[data-focus]');
    if (el && navItems().includes(el)) { NAV.dev = 'kb'; navFocus(el); }
  });
}
// Keyboard: arrows and WASD move, Enter / Space / J confirm, Esc (and Backspace outside a text field) go back, Q / E and
// PageUp / PageDown switch tabs. In a text field the letters, Space and left / right belong to the field.
function navKey(e) {
  const c = e.code, typing = navIsField(document.activeElement);
  if (c === 'Escape' || (c === 'Backspace' && !typing)) { if (!e.repeat) menuBack(); e.preventDefault(); return; }
  if (G.state === 'fight' || !NAV.cur || MN.rot) return;
  NAV.dev = 'kb';
  const def = navDef();
  if (def.any && !typing && !e.repeat && def.any('kb')) { e.preventDefault(); return; }
  if (typing && c !== 'ArrowUp' && c !== 'ArrowDown' && c !== 'Enter') return;
  const mv = NAV_KEYS[c];
  if (mv) { navMove(mv); e.preventDefault(); }
  else if (c === 'Enter' || c === 'Space' || c === 'KeyJ') { if (!e.repeat) navPress('kb'); e.preventDefault(); }
  else if (c === 'KeyQ' || c === 'PageUp') { navTab(-1); e.preventDefault(); }
  else if (c === 'KeyE' || c === 'PageDown') { navTab(1); e.preventDefault(); }
}
// Controller, once per frame: Start pauses and resumes a fight; in the menus the d-pad or left stick moves (one step per
// press, repeating while held), A confirms, B goes back, LB / RB switch tabs. Presses are edges against the previous poll.
function navPadPoll(now) {
  const l = inputPadList();
  for (let i = 0; i < Math.max(l.length, NAV.pad.length); i++) {
    const g = l[i];
    if (!g || g.connected === false) { NAV.pad[i] = null; continue; }
    const p = NAV.pad[i] || (NAV.pad[i] = {b: {}, dir: null, at: 0});
    const down = n => !!(g.buttons[n] && (g.buttons[n].pressed || g.buttons[n].value > .5));
    const edge = n => { const d = down(n), e = d && !p.b[n]; p.b[n] = d; return e; };
    const a = edge(0), b = edge(1), lb = edge(4), rb = edge(5), start = edge(9), xy = edge(2) | edge(3) | edge(8), ax = g.axes[0] || 0, ay = g.axes[1] || 0;
    const dir = down(12) || ay < -.5 ? 'up' : down(13) || ay > .5 ? 'down' : down(14) || ax < -.5 ? 'left' : down(15) || ax > .5 ? 'right' : null;
    const def = (G.state === 'title' || G.state === 'end') && !MN.rot ? navDef() : null;
    if (def && def.any && (a || b || lb || rb || start || xy)) { NAV.dev = 'pad'; NAV.padIx = i; if (def.any('pad')) { p.dir = dir; continue; } }
    if (start) { if (G.state === 'fight') menu.pause(); else if (G.state === 'pause') menu.resume(); p.dir = dir; continue; }
    if (G.state === 'fight' || !NAV.cur || MN.rot) { p.dir = dir; continue; }
    if (a || b || lb || rb || (dir && dir !== p.dir)) { NAV.dev = 'pad'; NAV.padIx = i; }
    if (dir && (dir !== p.dir || now >= p.at)) { navMove(dir); p.at = now + CFG.ui.repeat[dir === p.dir ? 1 : 0]; }
    p.dir = dir;
    if (a) navPress({pad: i}); else if (b) menuBack(); else if (lb) navTab(-1); else if (rb) navTab(1);
  }
}
function navInit() {
  NAV.dev = mnTouchDevice() ? 'touch' : 'kb';   // the title's prompt before any input
  navPointers(document.getElementById('uiScreens'));
  navPointers(document.getElementById('uiOver'));
  window.addEventListener('keydown', navKey);
}
