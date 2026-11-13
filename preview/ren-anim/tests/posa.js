// The pose editor (mods/posa.js), checked:  node tests/posa.js <page.html> [shot.png]
// On a phone held sideways (844x390, touch) with a stand-in for the page's database (window.claude.use('db'), in
// memory): no page error, nothing wider than the screen, every handle on the picture; then each part dragged (the
// mouse, and one drag by touch) and where its handle ends against where the pointer went (a part within reach follows
// the pointer: the head's look and the elbow's way included, which checks their signs); the part's buttons, the
// poses' row, playing, undo, the keys, a controller (a stand-in for navigator.getGamepads); the saved document, and
// the page opened again from it; the time the act's pose takes (ms per frame) against the kit's guard.
// Prints one JSON object; exits 1 on a page error or a failed check.
const {open, drawn} = require('./lib');
const FAKE_DB = `(() => {
  const store = window.__store = JSON.parse(sessionStorage.getItem('fakeStore') || '{}'), subs = [];
  const snap = () => { const docs = Object.entries(store).sort((a, b) => (b[1].updated || 0) - (a[1].updated || 0))
    .map(([id, d]) => ({id, exists: true, data: () => d, metadata: {fromCache: false, hasPendingWrites: false}}));
    return {docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: {fromCache: false, hasPendingWrites: false}}; };
  let n = 0;
  const col = {orderBy: () => col, limit: () => col,
    onSnapshot: (next) => { subs.push(next); setTimeout(() => next(snap()), 300); return () => {}; },
    doc: id => { id = id || 'gen' + (++n); return {id, set: async d => { window.__writes = (window.__writes || 0) + 1; store[id] = JSON.parse(JSON.stringify(d));
      sessionStorage.setItem('fakeStore', JSON.stringify(store)); subs.forEach(f => f(snap())); }}; }};
  window.claude = {use: async name => name === 'db' ? {collection: () => col} : null};
})();`;
(async () => {
  const shot = process.argv[3];
  const {browser, page, errors} = await open(process.argv[2], {w: 844, h: 390, dpr: 1, mobile: true, init: FAKE_DB, settle: 1500});
  const fails = [], ok = (c, what) => { if (!c) fails.push(what); };
  const S = () => page.evaluate(() => ({P: JSON.parse(JSON.stringify(VW.PZ.poses[VW.PZ.cur])), n: VW.PZ.poses.length, cur: VW.PZ.cur, sel: VW.PZ.sel, scr: JSON.parse(JSON.stringify(VW.PZ.scr)),
    st: document.getElementById('pzSt').textContent, title: document.querySelector('#name small').textContent, play: !!VW.PZ.play}));
  const settle = () => page.waitForTimeout(250);
  await page.waitForTimeout(600);
  // layout
  const lay = await page.evaluate(() => {
    const b = document.getElementById('bottom').getBoundingClientRect(), t = document.getElementById('pzTop').getBoundingClientRect(), vis = [];
    for (const [id, q] of Object.entries(VW.PZ.scr)) vis.push(q.x > 10 && q.x < innerWidth - 10 && q.y > 10 && q.y < b.top - 4 ? 1 : id);
    return {overflowX: document.documentElement.scrollWidth > innerWidth, bottomTop: Math.round(b.top), topBottom: Math.round(t.bottom), hidden: vis.filter(x => x !== 1),
      hint: getComputedStyle(document.getElementById('hint')).display, rows: [...document.querySelectorAll('#bottom .row.pz')].map(r => Math.round(r.getBoundingClientRect().height))};
  });
  ok(!lay.overflowX, 'overflow'); ok(!lay.hidden.length, 'handles off the picture: ' + lay.hidden);
  if (shot) await page.screenshot({path: shot});
  // drags (mouse): part, by (dx, dy) px; where its handle ends
  const drag = async (id, dx, dy, steps = 8) => {
    const s0 = await S(), q = s0.scr[id];
    await page.mouse.move(q.x, q.y); await page.mouse.down();
    for (let i = 1; i <= steps; i++) await page.mouse.move(q.x + dx * i / steps, q.y + dy * i / steps);
    await page.mouse.up(); await settle();
    const s1 = await S(), e = s1.scr[id];
    return {sel: s1.sel, P0: s0.P, P1: s1.P, miss: Math.round(Math.hypot(e.x - q.x - dx, e.y - q.y - dy))};
  };
  const r = {};
  r.hL = await drag('hL', -40, -30); ok(r.hL.sel === 'hL' && r.hL.miss <= 4, 'hand L: ' + r.hL.miss);
  r.hLfar = await drag('hL', 120, 0);   // (beyond the arm's reach: the wrist stops at it)
  ok(Math.hypot(...r.hLfar.P1.L.p) <= .45, 'hand L reach');
  r.hR = await drag('hR', 20, -30); ok(r.hR.miss <= 4, 'hand R: ' + r.hR.miss);
  r.eL = await drag('eL', 0, -25); ok(JSON.stringify(r.eL.P0.L.e) !== JSON.stringify(r.eL.P1.L.e), 'elbow L');
  // the elbow's way is kept across the arm (a hint, not a point): moving the hand afterwards turns no elbow over
  r.eHint = await page.evaluate(() => { const P = VW.PZ.poses[VW.PZ.cur].L, k = VW.PZ.fk, q = k.qC.clone(), e = new THREE.Vector3().fromArray(P.e).applyQuaternion(q);
    const ax = k.w.L.clone().sub(k.sh.L).normalize(); return +Math.abs(e.dot(ax)).toFixed(3); });
  ok(r.eHint < .05, 'elbow hint across the arm: ' + r.eHint);
  r.fL = await drag('fL', 25, -60); ok(r.fL.P1.fL.up > .2 && r.fL.miss <= 6, 'foot L: ' + r.fL.miss);
  r.fR = await drag('fR', 20, 0); ok(r.fR.P1.fR.up === 0 && r.fR.P1.fR.x > .05 && r.fR.miss <= 4, 'foot R: ' + r.fR.miss);
  r.fRfar = await drag('fR', -150, 0);   // (beyond the leg's reach: the ankle stops at it)
  r.legR = await page.evaluate(() => { const k = VW.PZ.fk; return +(k.ank.R.distanceTo(k.hip.R) / k.leg.R).toFixed(3); });
  ok(r.legR <= .97, 'foot R reach: ' + r.legR);
  r.hips = await drag('hips', 0, 15); ok(r.hips.P1.b.dip > .05 && r.hips.miss <= 4, 'hips: ' + r.hips.miss);
  // the chest turns about the pelvis: its handle on the pointer's way from the pelvis (it cannot stretch toward it)
  { const s0 = await S(), q = s0.scr.chest, h = s0.scr.hips;
    r.chest = await drag('chest', 25, 0);
    const e = (await S()).scr.chest, hy = h.y + 0, ang = (a, b) => Math.atan2(b.x - a.x, a.y - b.y) * 180 / Math.PI;
    r.chestAng = Math.round(Math.abs(ang({x: h.x, y: hy}, e) - ang({x: h.x, y: hy}, {x: q.x + 25, y: q.y})));
    ok(r.chest.P1.b.leanL > 5 && r.chestAng <= 6, 'chest: ' + r.chestAng); }
  r.head = await drag('head', 0, -25); ok(r.head.P1.h.nod < -3 && r.head.miss <= 8, 'head nod: ' + r.head.miss);
  r.all = await drag('all', 40, 0); ok(Math.abs((r.all.P1.b.lx - r.all.P0.b.lx) - (r.all.P1.fL.x - r.all.P0.fL.x)) < .002 && r.all.P1.b.lx > r.all.P0.b.lx + .1, 'all');
  // the head's turn, in the front view: drag its look sideways
  await page.click('#pzTools .opt button:nth-of-type(3)'); await settle();
  r.headYaw = await drag('head', 30, 0);   // (the look's point is held 30 cm from the face: it follows the pointer's way, not all of it)
  ok(Math.abs(r.headYaw.P1.h.yaw - r.headYaw.P0.h.yaw) > 5 && r.headYaw.miss <= 15, 'head yaw: ' + r.headYaw.miss);
  await page.click('#pzTools .opt button:nth-of-type(1)'); await settle();
  // a drag by touch (CDP touch events) on the right hand
  {
    const s0 = await S(), q = s0.scr.hR, cdp = await page.context().newCDPSession(page), T = (type, x, y) => cdp.send('Input.dispatchTouchEvent', {type, touchPoints: type === 'touchEnd' ? [] : [{x, y}]});
    await T('touchStart', q.x, q.y); for (let i = 1; i <= 6; i++) await T('touchMove', q.x - 3 * i, q.y + 2 * i); await T('touchEnd'); await settle();
    const s1 = await S(), e = s1.scr.hR; r.touch = {miss: Math.round(Math.hypot(e.x - q.x + 18, e.y - q.y - 12)), moved: JSON.stringify(s0.P.R.p) !== JSON.stringify(s1.P.R.p), yaw: await page.evaluate(() => VW.yaw)};
    ok(r.touch.moved && r.touch.miss <= 4, 'touch drag: ' + r.touch.miss);
  }
  // the part's buttons (the right hand selected): open, palm up, wrist back
  for (const t of ['Aperta', 'Su', 'Indietro']) await page.click('#pzPart button:has-text("' + t + '")');
  await settle();
  { const s = await S(); r.btn = s.P.R; ok(s.P.R.k === 0 && s.P.R.roll === 180 && s.P.R.wrist === 70, 'hand buttons'); }
  // undo: the three buttons back
  for (let i = 0; i < 3; i++) await page.click('#pzUndo');
  await settle();
  { const s = await S(); ok(s.P.R.k === .55 && s.P.R.wrist !== 70, 'undo'); }
  // the poses' row: a new pose, then playing, then stop
  await page.click('#pzAdd'); await settle();
  { const s = await S(); ok(s.n === 2 && s.cur === 1, 'add pose'); }
  await drag('hL', -40, 30);
  await page.click('#pzPlay'); await page.waitForTimeout(200);
  { const s = await S(); r.playTitle = s.title; ok(s.play && /Riproduzione/.test(s.title), 'play'); }
  // playing: the lead wrist goes between its two poses (sampled for 2.2 s: one loop is 1.7 s at the game's speed)
  const wr = [];
  for (let i = 0; i < 22; i++) { wr.push(await page.evaluate(() => VW.it.bones.find(x => x.name === 'LeftHand').getWorldPosition(new THREE.Vector3()).toArray())); await page.waitForTimeout(100); }
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  r.playMoves = Math.round(Math.max(...wr.map(p => dist(p, wr[0]))) * 1000);
  ok(r.playMoves > 50, 'playing moves: ' + r.playMoves);
  await page.click('#pzPlay'); await settle();
  { const s = await S(); ok(!s.play, 'stop'); }
  // keys: Tab to the next part, arrows move it, Ctrl+Z
  await page.click('#pzChips button:nth-child(1)'); await page.focus('body').catch(() => {}); await page.evaluate(() => document.activeElement && document.activeElement.blur());
  { const s0 = await S(); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); await page.keyboard.press('ArrowUp'); await page.keyboard.press('ArrowUp'); await settle();
    const s1 = await S(); r.keys = {sel: [s0.sel, s1.sel]}; ok(s1.sel !== s0.sel && JSON.stringify(s1.P) !== JSON.stringify(s0.P), 'keys');
    await page.keyboard.press('Control+z'); await settle(); const s2 = await S(); ok(JSON.stringify(s2.P) !== JSON.stringify(s1.P), 'ctrl+z'); }
  // a controller: the right shoulder to the next part, the left stick up for half a second, the A button
  await page.evaluate(() => {
    const pad = {buttons: Array.from({length: 17}, () => ({pressed: false})), axes: [0, 0, 0, 0]};
    window.__pad = pad; navigator.getGamepads = () => [pad];
  });
  { const s0 = await S();
    await page.evaluate(() => { __pad.buttons[5].pressed = true; }); await page.waitForTimeout(120); await page.evaluate(() => { __pad.buttons[5].pressed = false; __pad.axes[1] = -1; });
    await page.waitForTimeout(500); await page.evaluate(() => { __pad.axes[1] = 0; __pad.buttons[0].pressed = true; }); await page.waitForTimeout(120);
    await page.evaluate(() => { __pad.buttons[0].pressed = false; }); await settle();
    const s1 = await S(); r.pad = {sel: [s0.sel, s1.sel]}; ok(s1.sel !== s0.sel && JSON.stringify(s1.P) !== JSON.stringify(s0.P), 'controller'); }
  // the notes, then the save: what the database holds
  await page.click('#pzNb'); await page.fill('#pzName', 'Prova'); await page.fill('#pzNote', 'dalla 1 alla 2 veloce'); await page.click('#pzClose');
  await page.waitForTimeout(1600);
  const saved = await page.evaluate(() => ({writes: window.__writes || 0, docs: Object.entries(window.__store).map(([id, d]) => ({id, name: d.name, note: d.note, poses: d.poses.length, v: d.v}))}));
  r.saved = saved; ok(saved.docs.length === 1 && saved.docs[0].name === 'Prova' && saved.docs[0].poses === 2 && saved.writes < 25, 'saved');
  // time: the act's pose against the kit's guard (ms per frame, the pose only)
  r.ms = await page.evaluate(() => {
    const X = window.__X, md = X.mdData('ren'), F = Object.assign({}, VW.F), S = {frame: 0, sides: [{team: [F], cur: 0}]};
    const t = act => { F.act = act; F.af = 50; for (let i = 0; i < 20; i++) X.RN.pure(md, F, S); const t0 = performance.now(); for (let i = 0; i < 200; i++) { F.af = 50 + i * .1; X.RN.pure(md, F, S); } return +((performance.now() - t0) / 200).toFixed(3); };
    return {posa: t('posa'), idle: t('idle')};
  });
  r.fps = await page.evaluate(() => VW.fps);
  // opened again: the saved animation comes back
  await page.reload(); await page.waitForFunction(() => window.VW && VW.PZ && VW.PZ.guard, null, {timeout: 60000}); await page.waitForTimeout(1200);
  r.reopen = await page.evaluate(() => ({name: VW.PZ.name, n: VW.PZ.poses.length, st: document.getElementById('pzSt').textContent}));
  ok(r.reopen.name === 'Prova' && r.reopen.n === 2, 'reopen');
  console.log(JSON.stringify({errors, fails, lay, ...r, hL: r.hL.miss, hR: r.hR.miss, fL: r.fL.miss, fR: r.fR.miss, hips: r.hips.miss, chest: r.chest.miss, head: r.head.miss, headYaw: r.headYaw.miss, eL: r.eL.P1.L.e, all: r.all.miss}, null, 1));
  await browser.close();
  process.exit(errors.length || fails.length ? 1 : 0);
})();
