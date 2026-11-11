// Interface U1, Task 3: one navigation for every screen (keyboard, mouse, touch, controller). Three test screens:
// tA = a 2x2 grid (every button opens tB), tB = two buttons (open tC) and a tab handler, tC = a wrapping column.
const testScreen = (id, html, extra) => __VF.navRegister(Object.assign({id, build(r) { r.innerHTML = html; }}, extra || {}));
const cell = (t, go) => '<div class="ub" data-focus ' + (go ? 'data-go="' + go + '"' : '') + ' style="width:120px;height:48px">' + t + '</div>';
testScreen('tA', '<div style="display:grid;grid-template-columns:120px 120px;gap:24px;padding:40px">' + ['A1', 'A2', 'A3', 'A4'].map(t => cell(t, 'tB')).join('') + '</div>');
testScreen('tB', '<div style="display:flex;gap:24px;padding:40px">' + cell('B1', 'tC') + cell('B2', 'tC') + '</div>', {tab(d) { window.__tabs = (window.__tabs | 0) + d; }});
testScreen('tC', '<div data-wrap style="display:flex;flex-direction:column;gap:16px;padding:40px">' + cell('C1') + cell('C2') + cell('C3') + '</div>');

T.test('go, back and the focus returns where it was', () => { __VF.navReset('tA'); keyTap('ArrowRight'); T.eq(focused(), 'A2'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'tB'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'tA'); T.eq(focused(), 'A2'); });
T.test('2D focus picks the nearest in the direction and stops at the edge', () => { __VF.navReset('tA'); keyTap('ArrowDown'); T.eq(focused(), 'A3'); keyTap('ArrowDown'); T.eq(focused(), 'A3'); keyTap('ArrowRight'); T.eq(focused(), 'A4'); });
T.test('WASD moves too', () => { __VF.navReset('tA'); keyTap('KeyD'); T.eq(focused(), 'A2'); keyTap('KeyS'); T.eq(focused(), 'A4'); });
T.test('data-wrap wraps', () => { __VF.navReset('tC'); keyTap('ArrowUp'); T.eq(focused(), 'C3'); keyTap('ArrowDown'); T.eq(focused(), 'C1'); });
T.test('mouse hover focuses, click confirms', () => { __VF.navReset('tA'); hover('A4'); T.eq(focused(), 'A4'); uiClick('A4'); T.eq(__VF.UI.NAV.cur, 'tB'); });
T.test('touch confirms on release only', () => { __VF.navReset('tA'); const b = byText('A2'); ptr(b, 'pointerdown', 7); T.eq(__VF.UI.NAV.cur, 'tA'); ptr(b, 'pointerup', 7); T.eq(__VF.UI.NAV.cur, 'tB'); T.eq(__VF.UI.NAV.dev, 'touch'); });
T.test('a finger that slides off the button does not confirm', () => { __VF.navReset('tA'); const b = byText('A2'); ptr(b, 'pointerdown', 6); ptr(b, 'pointerup', 6, 200, 0); T.eq(__VF.UI.NAV.cur, 'tA'); });
T.test('double tap navigates once', () => { const g = __VF.CFG.ui.t.tapGuard; __VF.CFG.ui.t.tapGuard = 350; try { __VF.navReset('tA'); const n = __VF.UI.NAV.stack.length; later(400, () => { tapEl(byText('A2'), 8); tapEl(byText('B1'), 9); }); T.eq(__VF.UI.NAV.stack.length, n + 1); T.eq(__VF.UI.NAV.cur, 'tB'); } finally { __VF.CFG.ui.t.tapGuard = g; } });
T.test('pad: d-pad moves, A confirms, B goes back, the pad is the device', () => { __VF.navReset('tA'); padsAt([{buttons: {15: 1}}]); padTick(); padsAt([{}]); padTick(); T.eq(focused(), 'A2');
  padsAt([{buttons: {0: 1}}]); padTick(); T.eq(__VF.UI.NAV.cur, 'tB'); T.eq(__VF.UI.NAV.dev, 'pad'); padsAt([{}]); padTick(); padsAt([{buttons: {1: 1}}]); padTick(); T.eq(__VF.UI.NAV.cur, 'tA'); fakePads([]); padTick(); });
T.test('pad unplugged in the menus', () => { __VF.navReset('tA'); padsAt([{}]); padTick(); fakePads([]); window.dispatchEvent(new Event('gamepaddisconnected')); padTick(); keyTap('ArrowRight'); T.eq(focused(), 'A2'); T.eq(__VF.G.state, 'title'); });
T.test('Q/E and LB/RB call the screen tab()', () => { __VF.navReset('tB'); keyTap('KeyE'); T.eq(window.__tabs, 1); padsAt([{buttons: {4: 1}}]); padTick(); T.eq(window.__tabs, 0); fakePads([]); padTick(); });
T.test('back on the first screen does nothing', () => { __VF.navReset('tA'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'tA'); });
T.test('one screen at a time', () => { __VF.navReset('tA'); __VF.navGo('tB'); T.ok(vis('sc-tB')); T.ok(!vis('sc-tA')); });
