// The pose page (mods/posa.js: ready positions, buttons only), checked:  node tests/posa.js <page.html> [shot.png]
// On a phone held sideways (844x390, touch) with a stand-in for the page's database (window.claude.use('db'), in
// memory, holding one document of the first version, which must not be listed): no page error, nothing wider than
// the screen, the panel whole without scrolling, Ren inside the space it leaves him; each row's buttons (the pose
// takes the choice, the button shows it, the body moves), the hands' buttons going round, a new pose, playing, undo,
// the guard, deleting, the keys, a controller (a stand-in for navigator.getGamepads); the saved document (format 2),
// and the page opened again from it. The preview (Anteprima), with three of Claude's animations added: it opens on
// it, playing; next and previous by touch, keys and controller, round at the ends; the pause holds the frame; the
// list opens on it; Modifica and back; a change to one of Claude's goes to Denis's own copy (the original stays); a
// copy of one of Claude's left on the device does not go over the original. Then every combination of choices solved once (no NaN, no arm inside the chest,
// no hand in the head, no standing leg past the solver's stretch, no foot under the floor), every change of one row
// eased frame by frame (no joint jumping in the middle of it), and the time the pose takes (ms) against the guard's.
// Prints one JSON object; exits 1 on a page error or a failed check.
const {open} = require('./lib');
const FAKE_DB = `(() => {
  const old = {v: 1, name: 'Prova vecchia', updated: 1, poses: [{b: {}, h: {}, L: {}, R: {}, fL: {}, fR: {}}]};
  const store = window.__store = JSON.parse(sessionStorage.getItem('fakeStore') || JSON.stringify({vecchia: old})), subs = [];
  const snap = () => { const docs = Object.entries(store).sort((a, b) => (b[1].updated || 0) - (a[1].updated || 0))
    .map(([id, d]) => ({id, exists: true, data: () => d, metadata: {fromCache: false, hasPendingWrites: false}}));
    return {docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: {fromCache: false, hasPendingWrites: false}}; };
  let n = +(sessionStorage.getItem('fakeN') || 0);   // (new ids: never one already there, page after page)
  const col = {orderBy: () => col, limit: () => col,
    onSnapshot: (next) => { subs.push(next); setTimeout(() => next(snap()), 300); return () => {}; },
    doc: id => { if (!id) { id = 'gen' + (++n); sessionStorage.setItem('fakeN', String(n)); } return {id, set: async d => { window.__writes = (window.__writes || 0) + 1; store[id] = JSON.parse(JSON.stringify(d));
      sessionStorage.setItem('fakeStore', JSON.stringify(store)); subs.forEach(f => f(snap())); }}; }};
  window.claude = {use: async name => name === 'db' ? {collection: () => col} : null};
})();`;
(async () => {
  const shot = process.argv[3];
  const {browser, page, errors} = await open(process.argv[2], {w: 844, h: 390, dpr: 1, mobile: true, init: FAKE_DB, settle: 1500});
  const fails = [], ok = (c, what) => { if (!c) fails.push(what); }, r = {};
  const S = () => page.evaluate(() => ({P: JSON.parse(JSON.stringify(VW.PZ.poses[VW.PZ.cur])), n: VW.PZ.poses.length, cur: VW.PZ.cur, play: !!VW.PZ.play,
    title: document.querySelector('#name small').textContent, st: document.getElementById('pzSt').textContent}));
  const bones = () => page.evaluate(() => ['LeftHand', 'RightHand', 'LeftFoot', 'RightFoot', 'Head'].map(n => VW.it.bones.find(b => b.name === n).getWorldPosition(new THREE.Vector3()).toArray()));
  const moved = (a, b) => Math.max(...a.map((p, i) => Math.hypot(p[0] - b[i][0], p[1] - b[i][1], p[2] - b[i][2])));
  const settle = (ms = 400) => page.waitForTimeout(ms);
  await settle(600);
  // layout: the panel whole, Ren in the space left of it and under the title
  r.lay = await page.evaluate(() => {
    const P = document.getElementById('pzP'), pr = P.getBoundingClientRect(), tb = document.getElementById('name').getBoundingClientRect().bottom, cam = VW.camera;
    VW.it.root.updateMatrixWorld(true);
    const scr = n => { const v = VW.it.bones.find(b => b.name === n).getWorldPosition(new THREE.Vector3()).project(cam); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; };
    const pts = ['Head', 'LeftHand', 'RightHand', 'LeftToeBase', 'RightToeBase'].map(scr);
    return {overflowX: document.documentElement.scrollWidth > innerWidth, panelScroll: P.scrollHeight - P.clientHeight, panelLeft: Math.round(pr.left), titleBottom: Math.round(tb),
      inside: pts.every(([x, y]) => x > 4 && x < pr.left - 4 && y > tb - 30 && y < innerHeight - 4), head: pts[0].map(Math.round), feet: [pts[3], pts[4]].map(p => p.map(Math.round))};
  });
  ok(!r.lay.overflowX, 'overflow'); ok(r.lay.panelScroll <= 1, 'panel scrolls: ' + r.lay.panelScroll); ok(r.lay.inside, 'Ren outside his space');
  if (shot) await page.screenshot({path: shot});
  // every row's buttons, by touch
  r.rows = {};
  for (const key of ['bA', 'bD', 'gA', 'gD', 'busto', 'alt', 'passo']) {
    const vals = await page.evaluate(k => VW.pz.rows.find(x => x.key === k).vals.map(v => v[0]), key), first = await page.evaluate(k => VW.PZ.poses[VW.PZ.cur][k], key);
    for (const v of vals.filter(x => x !== first).concat(first)) {
      const b0 = await bones();
      await page.tap(`#pzP .pzR[aria-label="${await page.evaluate(k => VW.pz.rows.find(x => x.key === k).label, key)}"] button[data-v="${v}"]`);
      await settle(key === 'passo' ? 1000 : 400);
      const s = await S(), pressed = await page.evaluate(([k, v]) => { const row = [...document.querySelectorAll('#pzP .pzR')].find(x => x.getAttribute('aria-label') === VW.pz.rows.find(y => y.key === k).label);
        return [...row.querySelectorAll('button[aria-pressed="true"]')].map(b => b.dataset.v); }, [key, v]);
      const m = moved(b0, await bones());
      r.rows[key + ':' + v] = Math.round(m * 100);
      ok(s.P[key] === v && pressed.length === 1 && pressed[0] === v && m > .02, 'row ' + key + ' ' + v);
    }
  }
  // the hands go round
  for (const k of ['mA', 'mD']) {
    const seen = [];
    for (let i = 0; i < 3; i++) { await page.tap('#pz_' + k); await settle(150); seen.push((await S()).P[k]); }
    r[k] = seen; ok(new Set(seen).size === 3 && seen[2] === (k === 'mA' ? 'pugno' : 'socchiusa'), 'hand ' + k);
  }
  // a new pose, a change, playing, stop
  await page.tap('#pzAdd'); await settle();
  { const s = await S(); ok(s.n === 2 && s.cur === 1, 'add'); }
  await page.tap('#pzP .pzR[aria-label="Braccio avanti"] button[data-v="avanti"]'); await page.tap('#pz_mA'); await page.tap('#pz_mA'); await settle();
  await page.tap('#pzPlay'); await settle(200);
  { const s = await S(); r.playTitle = s.title; ok(s.play && /Riproduzione/.test(s.title), 'play'); }
  const wr = [];
  for (let i = 0; i < 22; i++) { wr.push((await bones())[0]); await page.waitForTimeout(100); }
  r.playMoves = Math.round(Math.max(...wr.map(p => Math.hypot(p[0] - wr[0][0], p[1] - wr[0][1], p[2] - wr[0][2]))) * 1000);
  ok(r.playMoves > 100, 'playing moves: ' + r.playMoves);
  await page.tap('#pzPlay'); await settle();
  { const s = await S(); ok(!s.play, 'stop'); }
  // undo, the guard, delete
  { const s0 = await S(); await page.tap('#pzUndo'); await settle(); const s1 = await S(); ok(JSON.stringify(s0.P) !== JSON.stringify(s1.P), 'undo');
    await page.tap('#pzGuard'); await settle(); const s2 = await S(); ok(s2.P.bA === 'guardia' && s2.P.mA === 'pugno' && s2.P.gA === 'terra', 'guard');
    await page.tap('#pzDel'); await settle(); const s3 = await S(); ok(s3.n === 1, 'delete'); }
  // keys: up to the first row (the lead arm: the keys start from the row last touched), right to its next position,
  // down to the rear arm, right; Ctrl+Z twice
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  { const s0 = await S();
    for (let i = 0; i < 7; i++) await page.keyboard.press('ArrowUp');
    const row0 = await page.evaluate(() => VW.PZ.row);
    for (let i = 0; i < row0; i++) await page.keyboard.press('ArrowUp');
    await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowRight'); await settle(200);
    const s1 = await S(); r.keys = {row: await page.evaluate(() => VW.PZ.row), bA: [s0.P.bA, s1.P.bA], bD: [s0.P.bD, s1.P.bD]};
    ok(r.keys.row === 1 && s1.P.bA !== s0.P.bA && s1.P.bD !== s0.P.bD, 'keys');
    await page.keyboard.press('Control+z'); await page.keyboard.press('Control+z'); await settle(200);
    const s2 = await S(); ok(s2.P.bA === s0.P.bA && s2.P.bD === s0.P.bD, 'ctrl+z'); }
  // a controller: down (from the rear arm to the hands' row), right (the rear hand goes round), A (a new pose)
  await page.evaluate(() => { const pad = {buttons: Array.from({length: 17}, () => ({pressed: false})), axes: [0, 0, 0, 0]}; window.__pad = pad; navigator.getGamepads = () => [pad]; });
  { const s0 = await S(), press = async i => { await page.evaluate(i => { __pad.buttons[i].pressed = true; }, i); await page.waitForTimeout(120); await page.evaluate(i => { __pad.buttons[i].pressed = false; }, i); await page.waitForTimeout(120); };
    await press(13); await press(15); await press(0); await settle(200);
    const s1 = await S(); r.pad = {mD: [s0.P.mD, s1.P.mD], n: [s0.n, s1.n]}; ok(s1.P.mD !== s0.P.mD && s1.n === s0.n + 1, 'controller'); }
  // the notes and the save
  await page.tap('#pzNb'); await page.fill('#pzName', 'Prova'); await page.fill('#pzNote', 'dalla 1 alla 2 veloce'); await page.tap('#pzClose');
  await page.waitForTimeout(1600);
  r.saved = await page.evaluate(() => ({writes: window.__writes || 0, docs: Object.entries(window.__store).map(([id, d]) => ({id, v: d.v, name: d.name, poses: d.poses.length, first: d.poses[0]})), list: VW.PZ.list.map(a => a.name)}));
  ok(r.saved.docs.some(d => d.v === 2 && d.name === 'Prova' && d.poses === 2) && !r.saved.list.includes('Prova vecchia'), 'saved');
  // time: the pose (ms per frame) against the kit's guard
  r.ms = await page.evaluate(() => {
    const X = window.__X, md = X.mdData('ren'), F = Object.assign({}, VW.F), S = {frame: 0, sides: [{team: [F], cur: 0}]};
    const t = act => { F.act = act; F.af = 50; for (let i = 0; i < 20; i++) X.RN.pure(md, F, S); const t0 = performance.now(); for (let i = 0; i < 200; i++) { F.af = 50 + i * .1; X.RN.pure(md, F, S); } return +((performance.now() - t0) / 200).toFixed(3); };
    return {posa: t('posa'), idle: t('idle')};
  });
  r.fps = await page.evaluate(() => VW.fps);
  // opened again
  await page.reload(); await page.waitForFunction(() => window.VW && VW.PZ && VW.pz, null, {timeout: 60000}); await page.waitForTimeout(1200);
  r.reopen = await page.evaluate(() => ({name: VW.PZ.name, n: VW.PZ.poses.length, st: document.getElementById('pzSt').textContent}));
  ok(r.reopen.name === 'Prova' && r.reopen.n === 2, 'reopen');
  // the preview (Anteprima): three of Claude's animations in the database (on every load from here: storage written
  // just before a reload can be lost), a first visit on this device (window.name: what the next load is for)
  await page.addInitScript(() => {
    const G = {bA: 'guardia', mA: 'pugno', bD: 'guardia', mD: 'socchiusa', gA: 'terra', gD: 'terra', busto: 'dritto', alt: 'normale', passo: 'qui', note: ''};
    const P = ch => Object.assign({}, G, ch, {t: 10}), a = (name, cat, ord, poses) => ({v: 2, name, cat, ord, note: name + ', di Claude', updated: 100 + ord, poses: [G].concat(poses)});
    const add = {'c-uno': a('Uno', 'Colpi', 1, [P({bA: 'avanti'}), P({})]), 'c-due': a('Due', 'Colpi', 2, [P({bD: 'avanti', mD: 'pugno'}), P({})]),
      'c-tre': a('Tre', 'Calci', 3, [P({gA: 'ginocchio'}), P({gA: 'calcio'}), P({})])};
    for (const [id, d] of Object.entries(add)) if (!window.__store[id]) window.__store[id] = d;
    if (window.name === 'nuovo') localStorage.removeItem('pose-ren-v2');
    if (window.name === 'copia') {   // (one of Claude's changed on this device and never saved: two poses gone)
      const d = JSON.parse(JSON.stringify(window.__store['c-tre'])); d.poses.splice(1, 2); d.updated = Date.now() + 1e7;
      localStorage.setItem('pose-ren-v2', JSON.stringify({id: 'c-tre', doc: d}));
    }
    window.name = '';
  });
  const reload = async name => { await page.evaluate(n => { window.name = n; }, name || ''); await page.reload(); await page.waitForFunction(() => window.VW && VW.PZ && VW.pz, null, {timeout: 60000}); await page.waitForTimeout(1200); };
  await reload('nuovo');
  const W = () => page.evaluate(() => { const vis = id => getComputedStyle(document.getElementById(id)).display !== 'none';
    return {watch: VW.PZ.watch, id: VW.PZ.id, play: !!VW.PZ.play, held: !!(VW.PZ.play && VW.PZ.play.paused !== undefined), panel: vis('pzW'), editor: vis('pzP'), list: !document.getElementById('pzA').hidden,
      wc: document.getElementById('pzWc').textContent, wn: document.getElementById('pzWn').textContent}; });
  r.watch = {start: await W()};
  r.watch.lay = await page.evaluate(() => {
    const pr = document.getElementById('pzW').getBoundingClientRect(), tb = document.getElementById('name').getBoundingClientRect().bottom, cam = VW.camera;
    VW.it.root.updateMatrixWorld(true);
    const scr = n => { const v = VW.it.bones.find(b => b.name === n).getWorldPosition(new THREE.Vector3()).project(cam); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; };
    const pts = ['Head', 'LeftHand', 'RightHand', 'LeftToeBase', 'RightToeBase'].map(scr), W = document.getElementById('pzW');
    return {inside: pts.every(([x, y]) => x > 4 && x < pr.left - 4 && y > tb - 30 && y < innerHeight - 4), panelLeft: Math.round(pr.left), scroll: W.scrollHeight - W.clientHeight,
      targets: ['pzNext', 'pzPrev', 'pzPause', 'pzList', 'pzEdit'].map(id => Math.round(document.getElementById(id).getBoundingClientRect().height))};
  });
  { const w = r.watch.start, L = r.watch.lay;
    ok(w.watch && w.panel && !w.editor && w.id === 'c-uno' && w.play && w.wc === 'Colpi · 1 di 2' && w.wn === 'Uno', 'the preview opens, playing the first of Claude\'s');
    ok(L.inside && L.scroll <= 1 && Math.min(...L.targets) >= 44, 'the preview\'s layout: ' + JSON.stringify(L)); }
  const order = await page.evaluate(() => [null, 'Colpi', 'Calci'].flatMap(c => VW.PZ.list.filter(a => a.cat === c)).map(a => a.id)), seq = [];
  const step = async f => { await f(); await settle(450); const w = await W(); seq.push(w.id); ok(w.watch && w.play, 'playing after a change of animation'); };
  for (let i = 0; i < 3; i++) await step(() => page.tap('#pzNext'));   // (Due, Tre, round to Denis's own)
  await step(() => page.tap('#pzPrev'));
  await step(() => page.keyboard.press('ArrowLeft')); await step(() => page.keyboard.press('ArrowRight'));
  await page.evaluate(() => { const pad = {buttons: Array.from({length: 17}, () => ({pressed: false})), axes: [0, 0, 0, 0]}; window.__pad = pad; navigator.getGamepads = () => [pad]; });
  const press = async i => { await page.evaluate(i => { __pad.buttons[i].pressed = true; }, i); await page.waitForTimeout(120); await page.evaluate(i => { __pad.buttons[i].pressed = false; }, i); await page.waitForTimeout(120); };
  await step(() => press(14)); await step(() => press(5)); await step(() => press(4));
  r.watch.seq = seq;
  { const at = i => order[(i + 4 * order.length) % order.length], u = order.indexOf('c-uno');
    ok(JSON.stringify(seq) === JSON.stringify([at(u + 1), at(u + 2), at(u + 3), at(u + 2), at(u + 1), at(u + 2), at(u + 1), at(u + 2), at(u + 1)]), 'next and previous: ' + seq.join(' ')); }
  // the pause holds the frame (touch, the space bar, the controller's A), and lets it go on
  { const held = async (f, on) => { await f(); await settle(250); const w = await W(), b0 = await bones(); await page.waitForTimeout(500); const m = moved(b0, await bones()); return w.held === on && (on ? m < .002 : true); };
    ok(await held(() => page.tap('#pzPause'), true), 'pause by touch'); ok(await held(() => page.tap('#pzPause'), false), 'on again by touch');
    ok(await held(() => page.keyboard.press(' '), true), 'pause by the space bar'); ok(await held(() => press(0), false), 'on again by the controller');
    const w0 = [], at = await W(); for (let i = 0; i < 22; i++) { w0.push((await bones())[1]); await page.waitForTimeout(100); }   // (a whole loop)
    ok(at.play && !at.held && Math.max(...w0.map(p => Math.hypot(p[0] - w0[0][0], p[1] - w0[0][1], p[2] - w0[0][2]))) > .02, 'playing on after the pause'); }
  // the list: opens on the preview, playing the one tapped
  await page.tap('#pzList'); await settle(400);
  { const w = await W(); ok(w.list, 'the list opens'); }
  await page.tap('#pzA .pzAr button[data-id="c-uno"]'); await settle(500);
  { const w = await W(); r.watch.list = w; ok(w.id === 'c-uno' && w.play && w.watch && !w.list, 'the list opens an animation on the preview'); }
  // Modifica, and back with the editor's Anteprima, the M key, the controller's Start
  const orig = await page.evaluate(() => JSON.stringify(window.__store['c-uno']));
  await page.tap('#pzEdit'); await settle(400);
  { const w = await W(); ok(!w.watch && w.editor && !w.panel && !w.play, 'Modifica opens the editor'); }
  await page.tap('#pzWb'); await settle(400);
  { const w = await W(); ok(w.watch && w.panel && w.play, 'Anteprima from the editor'); }
  await page.keyboard.press('m'); await settle(300);
  { const w = await W(); ok(!w.watch, 'M: the editor'); }
  await press(9); await settle(300);
  { const w = await W(); ok(w.watch, 'Start: the preview'); }
  await page.keyboard.press('m'); await settle(300);
  // a change to one of Claude's: Denis's own copy takes it, the original stays as it was
  await page.tap('#pzP .pzR[aria-label="Braccio dietro"] button[data-v="alto"]'); await page.waitForTimeout(1600);
  r.watch.fork = await page.evaluate(() => ({id: VW.PZ.id, name: VW.PZ.name, cat: VW.PZ.cat, copies: Object.entries(window.__store).filter(([, d]) => d.name === 'Uno (mia)').map(([id, d]) => ({id, cat: d.cat || null, bD: d.poses[0].bD}))}));
  { const f = r.watch.fork, now = await page.evaluate(() => JSON.stringify(window.__store['c-uno']));
    ok(now === orig && f.copies.length === 1 && f.id === f.copies[0].id && f.copies[0].cat === null && f.copies[0].bD === 'alto' && f.name === 'Uno (mia)', 'a change to one of Claude\'s goes to a copy'); }
  // a copy of one of Claude's left on this device (two poses gone, never saved): the original opens again, untouched
  const tre = await page.evaluate(() => JSON.stringify(window.__store['c-tre']));
  await reload('copia');
  r.watch.restored = await page.evaluate(() => ({id: VW.PZ.id, n: VW.PZ.poses.length, watch: VW.PZ.watch, play: !!VW.PZ.play}));
  { const x = r.watch.restored, now = await page.evaluate(() => JSON.stringify(window.__store['c-tre']));
    ok(x.id === 'c-tre' && x.n === 4 && x.watch && x.play && now === tre, 'the original opens again over a copy left on the device'); }
  await page.keyboard.press('m'); await settle(300);
  // every combination, solved once
  r.all = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), PZ = VW.PZ, B = n => it.bones.find(b => b.name === n), P = n => B(n).getWorldPosition(new T.Vector3());
    const F = Object.assign({}, VW.F, {act: 'posa', af: 1000}), S = {frame: 1000, sides: [{team: [F], cur: 0}]};
    X.mdApply(it, X.mdRest(md)); it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
    const len = {}; for (const s of ['Left', 'Right']) len[s] = P(s + 'UpLeg').distanceTo(P(s + 'Leg')) + P(s + 'Leg').distanceTo(P(s + 'Foot'));
    const row = k => VW.pz.rows.find(x => x.key === k).vals.map(v => v[0]), hands = VW.pz.hands.map(h => h[0]);
    const keys = ['bA', 'mA', 'bD', 'mD', 'gA', 'gD', 'busto', 'alt'], dom = [row('bA'), hands, row('bD'), hands, row('gA'), row('gD'), row('busto'), row('alt')];   // (the place: a translation, left out)
    const w = {chest: 0, head: 9, ext: 0, floor: 0, nan: 0, n: 0}, idx = keys.map(() => 0);
    for (;;) {
      const c = {note: '', passo: 'qui'}; keys.forEach((k, i) => { c[k] = dom[i][idx[i]]; });
      PZ.poses = [c]; PZ.cur = 0; PZ.D = null; PZ.tr = null; PZ.ver++; F.af++; S.frame++;
      const p = X.RN.pure(md, F, S);
      if (p.q.some(x => !isFinite(x)) || p.h.some(x => !isFinite(x))) w.nan++;
      X.mdApply(it, p); it.root.updateMatrixWorld(true);
      const sp = B('Spine01'), inv = sp.matrixWorld.clone().invert(), lo = P('Spine02').applyMatrix4(inv).y - .05, hi = P('neck').applyMatrix4(inv).y;
      for (const s of ['Right', 'Left']) {
        const E = P(s + 'ForeArm'), H = P(s + 'Hand'), tp = new T.Vector3(0, .09, 0).applyMatrix4(B(s + 'Hand').matrixWorld);
        for (const pt of [E, E.clone().lerp(H, .5), H, H.clone().lerp(tp, .5)]) {
          const l = pt.clone().applyMatrix4(inv); if (l.y < lo || l.y > hi) continue;
          const rz = l.z > 0 ? .13 : .15, kk = Math.hypot(l.x / .2, l.z / (rz + .04));
          if (kk < 1) w.chest = Math.max(w.chest, (1 - kk) * 100 * Math.min(.2, rz + .04));
        }
        w.head = Math.min(w.head, H.clone().lerp(tp, .5).distanceTo(P('Head').addScaledVector(new T.Vector3(0, 1, 0), .1)));
      }
      for (const [s, g] of [['Left', 'gA'], ['Right', 'gD']]) {
        if (c[g] === 'terra') w.ext = Math.max(w.ext, P(s + 'UpLeg').distanceTo(P(s + 'Foot')) / len[s]);
        w.floor = Math.max(w.floor, -Math.min(P(s + 'ToeBase').y, P(s + 'Foot').y - .06));
      }
      w.n++;
      let i = 0; while (i < keys.length && ++idx[i] >= dom[i].length) { idx[i] = 0; i++; }
      if (i === keys.length) break;
    }
    for (const k of ['chest', 'head', 'ext', 'floor']) w[k] = +w[k].toFixed(3);
    return w;
  });
  ok(!r.all.nan && r.all.chest < .5 && r.all.head > .08 && r.all.ext <= .966 && r.all.floor < .005, 'combinations');
  // the guard's ankles and hip joints that a foot swinging under the hips goes round (posa.js PZ_LEG): still the page's
  r.leg = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), PZ = VW.PZ, P = n => it.bones.find(b => b.name === n).getWorldPosition(new T.Vector3());
    const F = Object.assign({}, VW.F, {act: 'posa', af: 3000}), S = {frame: 3000, sides: [{team: [F], cur: 0}]};
    PZ.poses = [Object.assign({}, VW.pz.guard, {note: ''})]; PZ.cur = 0; PZ.D = null; PZ.tr = null; PZ.ver++;
    X.mdApply(it, X.RN.pure(md, F, S)); it.root.position.set(0, 0, 0); it.root.rotation.set(0, 0, 0); it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
    const line = new T.Vector3(Math.cos(X.F3_YAW), 0, Math.sin(X.F3_YAW));
    let off = 0;
    for (const [s, n] of [['L', 'Left'], ['R', 'Right']]) {
      const a = P(n + 'Foot'), h = P(n + 'UpLeg'), G = VW.pz.leg[s];
      off = Math.max(off, Math.abs(a.dot(line) - G.ax), Math.abs(a.y - G.ay), Math.abs(h.dot(line) - G.hx), Math.abs(h.y - G.hy));
    }
    return {off: +(off * 1000).toFixed(1)};
  });
  ok(r.leg.off < 5, 'the guard moved: PZ_LEG off by ' + r.leg.off + ' mm');
  // every change of one row, eased: no joint jumps in the middle (its largest step against its mean over the change)
  r.ease = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), PZ = VW.PZ, G = VW.pz.guard, B = n => it.bones.find(b => b.name === n);
    const F = Object.assign({}, VW.F, {act: 'posa', af: 5000}), S = {frame: 5000, sides: [{team: [F], cur: 0}]}, n = PZ.ease;
    const J = ['LeftForeArm', 'LeftHand', 'RightForeArm', 'RightHand', 'LeftLeg', 'LeftFoot', 'RightLeg', 'RightFoot', 'Head'];
    const pos = () => { X.mdApply(it, X.RN.pure(md, F, S)); it.root.updateMatrixWorld(true); return J.map(j => B(j).getWorldPosition(new T.Vector3())); };
    const hands = VW.pz.hands.map(h => h[0]), changes = [], A = VW.pz.rows.find(x => x.key === 'bA').vals.map(v => v[0]).flatMap(v => hands.map(h => [v, h]));
    for (const [pk, hk] of [['bA', 'mA'], ['bD', 'mD']]) for (const a of A) for (const b of A) if (a.join() !== b.join()) changes.push([{[pk]: a[0], [hk]: a[1]}, {[pk]: b[0], [hk]: b[1]}]);
    for (const k of ['gA', 'gD', 'busto', 'alt']) { const vs = VW.pz.rows.find(x => x.key === k).vals.map(v => v[0]); for (const a of vs) for (const b of vs) if (a !== b) changes.push([{[k]: a}, {[k]: b}]); }
    let worst = {ratio: 0, step: 0, at: ''};
    for (const [a, b] of changes) {
      PZ.poses = [Object.assign({}, G, a, {note: ''})]; PZ.cur = 0; PZ.D = null; PZ.tr = null; PZ.ver++; F.af++; S.frame++;
      let prev = pos();
      PZ.poses[0] = Object.assign({}, G, b, {note: ''}); PZ.ver++;
      const steps = J.map(() => []);
      for (let f = 0; f < n; f++) { F.af++; S.frame++; const cur = pos(); cur.forEach((p, j) => steps[j].push(p.distanceTo(prev[j]))); prev = cur; }
      // (a jump: a step larger than 1.5 cm and three times the steps on either side of it; a fast middle is no jump)
      steps.forEach((st, j) => st.forEach((x, i) => {
        if (i === 0 || i === st.length - 1 || x < .015) return;
        const ratio = x / Math.max(st[i - 1], st[i + 1], 1e-6);
        if (ratio > worst.ratio) worst = {ratio: +ratio.toFixed(2), step: +(x * 100).toFixed(1), at: JSON.stringify(a) + ' > ' + JSON.stringify(b) + ' ' + J[j]};
      }));
    }
    return {n: changes.length, worst};
  });
  ok(r.ease.worst.ratio < 3, 'a joint jumps: ' + r.ease.worst.at);
  console.log(JSON.stringify({errors, fails, ...r}, null, 1));
  await browser.close();
  process.exit(errors.length || fails.length ? 1 : 0);
})();
