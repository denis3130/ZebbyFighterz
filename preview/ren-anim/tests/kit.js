// Ren's kit page (mods/kit.js), checked:  node tests/kit.js <page.html>
// 1. Live: every play runs with the page's own loop on a phone-landscape screen, the speeds and the background switched
//    while it plays; no page error allowed; the drawn frames per second.
// 2. Frame by frame (VW.tick, then three more quarter frames drawn in between), in the game's world (the fight line
//    along x): each foot's contact point (its toe tip when the heel is up, else its ball) and how far it moves between
//    two drawn frames while it is on the floor (slide, mm), how high a foot goes while it steps, the legs' extension
//    (hip to ankle over the leg's length), the arms' deepest point inside the chest, the largest jolt (a change of
//    speed between two quarter frames, mm) of the hips, hands, feet and head, and, on the palm's active frames, where
//    its striking point is from the fighter (mm along the line, height).
// Prints one JSON object; exits 1 on a page error.
const {open} = require('./lib');
(async () => {
  const {browser, page, errors} = await open(process.argv[2], {w: 844, h: 390, dpr: 1});
  const click = id => page.evaluate(id => document.getElementById(id).click(), id);
  for (const id of ['play0', 'play1', 's4', 'play2', 's2', 'kitBg', 'play1', 's1', 'kitBg', 'play0']) { await click(id); await page.waitForTimeout(900); }
  await page.keyboard.press('ArrowRight'); await page.keyboard.press(' '); await page.keyboard.press('n');
  await page.waitForTimeout(600);
  const live = await page.evaluate(() => ({fps: VW.fps, act: VW.F.act, overflowX: document.documentElement.scrollWidth > innerWidth}));
  await page.evaluate(() => { VW.speed = 0; VW.spin = false; VW.acc = 0; });
  const r = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, md = X.mdData('ren'), B = n => it.bones.find(b => b.name === n);
    const P = n => B(n).getWorldPosition(new T.Vector3()), Q = n => B(n).getWorldQuaternion(new T.Quaternion());
    // the shoes' toe tips in the feet's own frames, the legs' lengths (rest pose)
    X.mdApply(it, X.mdRest(md)); it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
    const rest = {}, pos = md.geo.attributes.position;
    for (const s of ['Left', 'Right']) {
      const q = Q(s + 'Foot').invert(), ank = P(s + 'Foot'), ball = P(s + 'ToeBase'), f = ball.clone().sub(ank).setY(0).normalize();
      let far = 0;
      for (let i = 0; i < pos.count; i++) { const x = pos.getX(i); if (pos.getY(i) > .07 || (x > 0) !== (s === 'Left')) continue; far = Math.max(far, (x - ball.x) * f.x + (pos.getZ(i) - ball.z) * f.z); }
      rest[s] = {ball: ball.y, tip: new T.Vector3(ball.x + f.x * far, 0, ball.z + f.z * far).sub(ank).applyQuaternion(q),
        len: P(s + 'UpLeg').distanceTo(P(s + 'Leg')) + P(s + 'Leg').distanceTo(P(s + 'Foot'))};
    }
    const limb = md.meta.limbs[X.CFG.moves.palm.limb], out = {};
    const JOLT = ['Hips', 'Head', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot', 'LeftLeg', 'RightLeg', 'LeftForeArm', 'RightForeArm'];
    for (let i = 0; i < X.VW_PLAYS.length; i++) {
      document.getElementById('play' + i).click();
      const o = out[X.VW_PLAYS[i][0]] = {frames: 0, slide: {}, lift: {}, ext: {max: 0, at: ''}, chest: {max: 0, at: ''}, jolt: {}, strike: []};
      let wraps = 0, last = VW.step, prev = null, trail = [];
      for (let t = 0; t < 2000 && wraps < 1; t++) {
        VW.tick(1); if (VW.step < last) wraps++; last = VW.step;
        if (wraps) break;
        o.frames++;
        for (const k of [0, .25, .5, .75]) {
          if (k) X.rnSync(it, 0, X.rnDrawState(k));
          it.root.updateMatrixWorld(true);
          const F = X.rnDrawState(k).sides[0].team[0], tag = F.act + ' f' + F.af.toFixed(2), cur = {};
          for (const s of ['Left', 'Right']) {
            const ank = P(s + 'Foot'), ball = P(s + 'ToeBase'), R = rest[s], tip = R.tip.clone().applyQuaternion(Q(s + 'Foot')).add(ank);
            const h = Math.min(ball.y - R.ball, tip.y), onTip = tip.y < ball.y - R.ball - .002, pt = onTip ? tip : ball;
            const ext = P(s + 'UpLeg').distanceTo(ank) / R.len;
            if (ext > o.ext.max) { o.ext.max = +ext.toFixed(3); o.ext.at = s[0] + ' ' + tag; }
            if (h < .004) {   // on the floor
              cur[s] = {x: pt.x, z: pt.z, onTip};
              if (prev && prev[s] && prev[s].onTip === onTip) {
                const sl = Math.hypot(pt.x - prev[s].x, pt.z - prev[s].z) * 1000, d = o.slide[s[0]] || (o.slide[s[0]] = {max: 0, at: ''});
                if (sl > d.max) { d.max = +sl.toFixed(1); d.at = tag; }
              }
            } else { const d = o.lift[s[0]] || (o.lift[s[0]] = {max: 0, at: ''}); if (h * 1000 > d.max) { d.max = +(h * 1000).toFixed(0); d.at = tag; } }
          }
          // the arms into the chest (overlap.js's measure)
          const sp = B('Spine01'), inv = sp.matrixWorld.clone().invert(), lo = P('Spine02').applyMatrix4(inv).y - .05, hi = P('neck').applyMatrix4(inv).y;
          for (const s of ['Right', 'Left']) {
            const E = P(s + 'ForeArm'), H = P(s + 'Hand'), tp = new T.Vector3(0, .09, 0).applyMatrix4(B(s + 'Hand').matrixWorld);
            for (const pt of [E, E.clone().lerp(H, .33), E.clone().lerp(H, .66), H, H.clone().lerp(tp, .5)]) {
              const l = pt.clone().applyMatrix4(inv); if (l.y < lo || l.y > hi) continue;
              const rz = l.z > 0 ? .13 : .15, kk = Math.hypot(l.x / (.16 + .04), l.z / (rz + .04));
              if (kk < 1) { const dp = (1 - kk) * 100 * Math.min(.2, rz + .04); if (dp > o.chest.max) { o.chest.max = +dp.toFixed(1); o.chest.at = s[0] + ' ' + tag; } }
            }
          }
          trail.push({tag, p: JOLT.map(n => P(n))});
          if (trail.length > 3) trail.shift();
          if (trail.length === 3) JOLT.forEach((n, j) => {
            const a = trail[0].p[j], b = trail[1].p[j], c = trail[2].p[j], jl = c.clone().sub(b).sub(b.clone().sub(a)).length() * 1000, d = o.jolt[n] || (o.jolt[n] = {max: 0, at: ''});
            if (jl > d.max) { d.max = +jl.toFixed(1); d.at = trail[1].tag; }
          });
          if (F.act === 'palm' && k === 0 && F.af >= 9 && F.af <= 13) {
            const pt = new T.Vector3().fromArray(limb.p).applyMatrix4(B(limb.b).matrixWorld);
            o.strike.push({f: F.af, x: Math.round(pt.x * 1000 - F.x), y: Math.round(pt.y * 1000)});
          }
          prev = cur;
        }
      }
    }
    return out;
  });
  console.log(JSON.stringify({errors, live, ...r}, null, 1));
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})();
