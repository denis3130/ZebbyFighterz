// The pose page (mods/posa.js: ready positions, buttons only), checked:  node tests/posa.js <page.html> [shot.png]
// On a phone held sideways (844x390, touch) with a stand-in for the page's database (window.claude.use('db'), in
// memory, holding one document of the first version, which must not be listed): no page error, nothing wider than
// the screen, the panel whole without scrolling, Ren inside the space it leaves him; each row's buttons (the pose
// takes the choice, the button shows it, the body moves), the hands' buttons going round, a new pose, playing, undo,
// the guard, deleting, the keys, a controller (a stand-in for navigator.getGamepads); the saved document (format 2),
// and the page opened again from it. Then every combination of choices solved once (no NaN, no arm inside the chest,
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
  for (const key of ['bA', 'bD', 'gA', 'gD', 'busto', 'alt']) {
    const vals = await page.evaluate(k => VW.pz.rows.find(x => x.key === k).vals.map(v => v[0]), key);
    for (const v of vals.slice(1).concat(vals[0])) {
      const b0 = await bones();
      await page.tap(`#pzP .pzR[aria-label="${await page.evaluate(k => VW.pz.rows.find(x => x.key === k).label, key)}"] button[data-v="${v}"]`);
      await settle();
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
  // every combination, solved once
  r.all = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), PZ = VW.PZ, B = n => it.bones.find(b => b.name === n), P = n => B(n).getWorldPosition(new T.Vector3());
    const F = Object.assign({}, VW.F, {act: 'posa', af: 1000}), S = {frame: 1000, sides: [{team: [F], cur: 0}]};
    X.mdApply(it, X.mdRest(md)); it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
    const len = {}; for (const s of ['Left', 'Right']) len[s] = P(s + 'UpLeg').distanceTo(P(s + 'Leg')) + P(s + 'Leg').distanceTo(P(s + 'Foot'));
    const row = k => VW.pz.rows.find(x => x.key === k).vals.map(v => v[0]), hands = VW.pz.hands.map(h => h[0]);
    const keys = ['bA', 'mA', 'bD', 'mD', 'gA', 'gD', 'busto', 'alt'], dom = [row('bA'), hands, row('bD'), hands, row('gA'), row('gD'), row('busto'), row('alt')];
    const w = {chest: 0, head: 9, ext: 0, floor: 0, nan: 0, n: 0}, idx = keys.map(() => 0);
    for (;;) {
      const c = {note: ''}; keys.forEach((k, i) => { c[k] = dom[i][idx[i]]; });
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
  // every change of one row, eased: no joint jumps in the middle (its largest step against its mean over the change)
  r.ease = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), PZ = VW.PZ, G = VW.pz.guard, B = n => it.bones.find(b => b.name === n);
    const F = Object.assign({}, VW.F, {act: 'posa', af: 5000}), S = {frame: 5000, sides: [{team: [F], cur: 0}]}, n = PZ.ease;
    const J = ['LeftForeArm', 'LeftHand', 'RightForeArm', 'RightHand', 'LeftLeg', 'LeftFoot', 'RightLeg', 'RightFoot', 'Head'];
    const pos = () => { X.mdApply(it, X.RN.pure(md, F, S)); it.root.updateMatrixWorld(true); return J.map(j => B(j).getWorldPosition(new T.Vector3())); };
    const hands = VW.pz.hands.map(h => h[0]), changes = [], A = ['guardia', 'avanti', 'alto', 'viso'].flatMap(v => hands.map(h => [v, h]));
    for (const [pk, hk] of [['bA', 'mA'], ['bD', 'mD']]) for (const a of A) for (const b of A) if (a.join() !== b.join()) changes.push([{[pk]: a[0], [hk]: a[1]}, {[pk]: b[0], [hk]: b[1]}]);
    for (const k of ['gA', 'gD', 'busto', 'alt']) { const vs = VW.pz.rows.find(x => x.key === k).vals.map(v => v[0]); for (const a of vs) for (const b of vs) if (a !== b) changes.push([{[k]: a}, {[k]: b}]); }
    let worst = {ratio: 0, step: 0, at: ''};
    for (const [a, b] of changes) {
      PZ.poses = [Object.assign({}, G, a, {note: ''})]; PZ.cur = 0; PZ.D = null; PZ.tr = null; PZ.ver++; F.af++; S.frame++;
      let prev = pos();
      PZ.poses[0] = Object.assign({}, G, b, {note: ''}); PZ.ver++;
      const steps = J.map(() => []);
      for (let f = 0; f < n; f++) { F.af++; S.frame++; const cur = pos(); cur.forEach((p, j) => steps[j].push(p.distanceTo(prev[j]))); prev = cur; }
      steps.forEach((st, j) => {
        const tot = st.reduce((x, y) => x + y, 0), mx = Math.max(...st), ratio = mx / (tot / st.length);
        if (mx > .03 && ratio > worst.ratio) worst = {ratio: +ratio.toFixed(2), step: +(mx * 100).toFixed(1), at: JSON.stringify(a) + ' > ' + JSON.stringify(b) + ' ' + J[j]};
      });
    }
    return {n: changes.length, worst};
  });
  ok(r.ease.worst.ratio < 3, 'a joint jumps: ' + r.ease.worst.at);   // (an even ease: 1.5; a jump: much more)
  console.log(JSON.stringify({errors, fails, ...r}, null, 1));
  await browser.close();
  process.exit(errors.length || fails.length ? 1 : 0);
})();
