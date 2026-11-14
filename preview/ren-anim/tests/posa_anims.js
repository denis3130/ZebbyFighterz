// Ren's animations (data/animazioni.json), each played in the pose page through its whole loop, a quarter frame at a
// time:  node tests/posa_anims.js <page.html> [animazioni.json] [only-this-key]
// For each: a foot on the floor never slides (its contact point: the toe tip when the heel is up, else the ball; mm
// between two samples while it stays down), no foot under the floor, no arm inside the chest (the kit test's measure),
// no hand in the head, a standing leg never past the solver's stretch, no joint jumping (a step between two samples
// more than 1.5 cm and three times the steps before and after it), no NaN, the two legs never into each other (their
// bones' lines, thighs from a little under the hip, shins and feet, never closer than LIM.legs cm: a leg is about 15
// thick).
// Prints one line per animation and the worst of all; exits 1 on a page error or a failed limit.
const {open} = require('./lib');
const fs = require('fs'), path = require('path');
const LIM = {slide: +(process.env.SLIDE || 2), floor: 5, chest: .5, head: .08, ext: .97, legs: +(process.env.LEGS || 12)};   // (SLIDE=mm: a stricter look)
(async () => {
  const file = process.argv[3] || path.join(__dirname, '..', 'data', 'animazioni.json'), only = process.argv[4];
  const docs = JSON.parse(fs.readFileSync(file, 'utf8')).filter(d => !only || d.id === only || d.id === 'c-' + only);
  const {browser, page, errors} = await open(process.argv[2], {w: 844, h: 390, dpr: 1, settle: 1200});
  const res = [];
  for (const d of docs) {
    const r = await page.evaluate(([id, doc, LIM]) => {
      const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), PZ = VW.PZ, B = n => it.bones.find(b => b.name === n);
      const P = n => B(n).getWorldPosition(new T.Vector3()), Q = n => B(n).getWorldQuaternion(new T.Quaternion());
      // the shoes' toe tips in the feet's own frames, the legs' lengths, the ball's rest height (rest pose)
      if (!window.__rest) {
        X.mdApply(it, X.mdRest(md)); it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
        const rest = {}, pos = md.geo.attributes.position;
        for (const s of ['Left', 'Right']) {
          const q = Q(s + 'Foot').invert(), ank = P(s + 'Foot'), ball = P(s + 'ToeBase'), f = ball.clone().sub(ank).setY(0).normalize();
          let far = 0;
          for (let i = 0; i < pos.count; i++) { const x = pos.getX(i); if (pos.getY(i) > .07 || (x > 0) !== (s === 'Left')) continue; far = Math.max(far, (x - ball.x) * f.x + (pos.getZ(i) - ball.z) * f.z); }
          rest[s] = {ball: ball.y, tip: new T.Vector3(ball.x + f.x * far, 0, ball.z + f.z * far).sub(ank).applyQuaternion(q),
            len: P(s + 'UpLeg').distanceTo(P(s + 'Leg')) + P(s + 'Leg').distanceTo(P(s + 'Foot'))};
        }
        window.__rest = rest;
      }
      const rest = window.__rest;
      VW.pz.load(id, doc);
      PZ.play = {f0: 0, at: {a: 0, b: 1, back: false}}; PZ.ver++;
      const L = VW.pz.timeline(), F = Object.assign({}, VW.F, {act: 'posa', af: 0, air: false}), S = {frame: 0, sides: [{team: [F], cur: 0}]};
      const J = ['LeftHand', 'RightHand', 'LeftForeArm', 'RightForeArm', 'LeftFoot', 'RightFoot', 'LeftLeg', 'RightLeg', 'Head', 'Hips'];
      const o = {len: L.len, low: 9, lowAt: '', slide: 0, slideAt: '', floor: 0, floorAt: '', chest: 0, chestAt: '', head: 9, headAt: '', ext: 0, extAt: '', nan: 0, jumps: [], legs: 99, legsAt: ''};
      const seg = (p1, p2, q1, q2) => {   // (the closest two segments come)
        const d1 = p2.clone().sub(p1), d2 = q2.clone().sub(q1), r = p1.clone().sub(q1), a = d1.dot(d1), e = d2.dot(d2), f = d2.dot(r), c = d1.dot(r), b = d1.dot(d2), den = a * e - b * b;
        let s = den > 1e-9 ? Math.max(0, Math.min(1, (b * f - c * e) / den)) : 0, t = (b * s + f) / e;
        if (t < 0) { t = 0; s = Math.max(0, Math.min(1, -c / a)); } else if (t > 1) { t = 1; s = Math.max(0, Math.min(1, (b - c) / a)); }
        return p1.clone().addScaledVector(d1, s).distanceTo(q1.clone().addScaledVector(d2, t));
      };
      const legParts = s => { const h = P(s + 'UpLeg'), k = P(s + 'Leg'), a = P(s + 'Foot'), t = P(s + 'ToeBase'); return [['coscia', h.lerp(k, .3), k], ['stinco', k, a], ['piede', a, t]]; };
      let prev = null, trail = [], tag0 = () => '';
      for (let t = 0; t <= L.len; t += .25) {
        tag0 = () => 'f' + t.toFixed(2);
        F.af = t; S.frame = t;
        const p = X.RN.pure(md, F, S);
        if (p.q.some(x => !isFinite(x)) || p.h.some(x => !isFinite(x))) { o.nan++; continue; }
        X.mdApply(it, p); it.root.rotation.set(0, 0, 0);
        const xf = VW.pz.rootOf(p); it.root.quaternion.copy(xf.q); it.root.position.copy(xf.t).multiplyScalar(it.scale);   // (the whole body's turn and flip)
        it.root.updateMatrixWorld(true);
        const low = Math.min(...['Head', 'Hips', 'LeftHand', 'RightHand'].map(n => P(n).y));
        if (low < o.low) { o.low = +low.toFixed(3); o.lowAt = tag0(); }
        const at = PZ.play.at, tag = 'f' + t.toFixed(2) + ' ' + (at.back ? 'ritorno' : (at.a + 1) + '>' + (at.b + 1)), cur = {};
        for (const s of ['Left', 'Right']) {
          const ank = P(s + 'Foot'), ball = P(s + 'ToeBase'), R = rest[s], tip = R.tip.clone().applyQuaternion(Q(s + 'Foot')).add(ank);
          const h = Math.min(ball.y - R.ball, tip.y), onTip = tip.y < ball.y - R.ball - .002, pt = onTip ? tip : ball;
          if (-h * 1000 > o.floor) { o.floor = +(-h * 1000).toFixed(1); o.floorAt = s[0] + ' ' + tag; }
          if (h < .004) {   // on the floor
            cur[s] = {x: pt.x, z: pt.z, onTip};
            if (prev && prev[s] && prev[s].onTip === onTip) {
              const sl = Math.hypot(pt.x - prev[s].x, pt.z - prev[s].z) * 1000;
              if (sl > o.slide) { o.slide = +sl.toFixed(1); o.slideAt = s[0] + ' ' + tag; }
            }
            const ext = P(s + 'UpLeg').distanceTo(ank) / R.len;
            if (ext > o.ext) { o.ext = +ext.toFixed(3); o.extAt = s[0] + ' ' + tag; }
          }
        }
        prev = cur;
        // the arms in the chest; the hands near the head
        const sp = B('Spine01'), inv = sp.matrixWorld.clone().invert(), lo = P('Spine02').applyMatrix4(inv).y - .05, hi = P('neck').applyMatrix4(inv).y;
        for (const s of ['Right', 'Left']) {
          const E = P(s + 'ForeArm'), H = P(s + 'Hand'), tp = new T.Vector3(0, .09, 0).applyMatrix4(B(s + 'Hand').matrixWorld);
          for (const pt of [E, E.clone().lerp(H, .5), H, H.clone().lerp(tp, .5)]) {
            const l = pt.clone().applyMatrix4(inv); if (l.y < lo || l.y > hi) continue;
            const rz = l.z > 0 ? .13 : .15, kk = Math.hypot(l.x / .2, l.z / (rz + .04));
            if (kk < 1) { const dp = (1 - kk) * 100 * Math.min(.2, rz + .04); if (dp > o.chest) { o.chest = +dp.toFixed(1); o.chestAt = s[0] + ' ' + tag; } }
          }
          const hd = H.clone().lerp(tp, .5).distanceTo(P('Head').addScaledVector(new T.Vector3(0, 1, 0), .1));
          if (hd < o.head) { o.head = +hd.toFixed(3); o.headAt = s[0] + ' ' + tag; }
        }
        // the legs: never into each other
        { const Lp = legParts('Left'), Rp = legParts('Right');
          for (const l of Lp) for (const q of Rp) { const d = seg(l[1], l[2], q[1], q[2]) * 100; if (d < o.legs) { o.legs = +d.toFixed(1); o.legsAt = 'sx ' + l[0] + '/dx ' + q[0] + ' ' + tag; } } }
        // jumps: a step much larger than the steps on either side of it
        trail.push({tag, p: J.map(n => P(n))});
        if (trail.length > 4) trail.shift();
        if (trail.length === 4) J.forEach((n, j) => {
          const st = [1, 2, 3].map(i => trail[i].p[j].distanceTo(trail[i - 1].p[j]));
          if (st[1] > .015 && st[1] > 3 * Math.max(st[0], st[2])) o.jumps.push(n + ' ' + (st[1] * 100).toFixed(1) + 'cm ' + trail[2].tag);
        });
      }
      return o;
    }, [d.id, d.doc, LIM]);
    const bad = [];
    if (r.nan) bad.push('NaN');
    if (r.slide > LIM.slide) bad.push('scivola ' + r.slide + 'mm ' + r.slideAt);
    if (r.floor > LIM.floor) bad.push('sotto il pavimento ' + r.floor + 'mm ' + r.floorAt);
    if (r.chest > LIM.chest) bad.push('braccio nel petto ' + r.chest + 'cm ' + r.chestAt);
    if (r.head < LIM.head) bad.push('mano nel viso ' + r.head + ' ' + r.headAt);
    if (r.ext > LIM.ext) bad.push('gamba tirata ' + r.ext + ' ' + r.extAt);
    if (r.low < .05) bad.push('testa, mani o bacino a terra ' + r.low + ' ' + r.lowAt);
    if (r.legs < LIM.legs) bad.push('gambe una dentro l\'altra ' + r.legs + 'cm ' + r.legsAt);
    if (r.jumps.length) bad.push('scatti: ' + r.jumps.slice(0, 3).join('; ') + (r.jumps.length > 3 ? ' (+' + (r.jumps.length - 3) + ')' : ''));
    res.push({id: d.id, name: d.doc.name, bad, r});
    console.log((bad.length ? 'NO ' : 'ok ') + d.id.padEnd(26) + ' ' + (r.len / 60).toFixed(1) + 's  slide ' + r.slide + '  chest ' + r.chest + '  head ' + r.head + '  ext ' + r.ext + '  legs ' + r.legs + (bad.length ? '\n     ' + bad.join('\n     ') : ''));
  }
  const worst = k => res.reduce((m, x) => (k === 'head' || k === 'legs' ? x.r[k] < m.r[k] : x.r[k] > m.r[k]) ? x : m, res[0]);
  console.log(JSON.stringify({errors, n: res.length, failed: res.filter(x => x.bad.length).map(x => x.id),
    worst: Object.fromEntries(['slide', 'floor', 'chest', 'head', 'ext', 'legs'].map(k => [k, [worst(k).r[k], worst(k).id]]))}));
  await browser.close();
  process.exit(errors.length || res.some(x => x.bad.length) ? 1 : 0);
})();
