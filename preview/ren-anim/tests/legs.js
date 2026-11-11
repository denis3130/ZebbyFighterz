// Leg and foot physics of a built page, old (original) against new (the layer), over one cycle of every play:
//   node tests/legs.js <page.html>
// Per mode, the number of frames with each defect on a foot standing on the floor (its ball or toe tip lower than 6 cm), and the
// worst value: stretched (the leg straighter than 98.5% of its length), floating (the ball more than 15 mm above the
// floor), sunk (more than 12 mm under it), rolled (the sole tilted sideways by more than 12 degrees), knee (the knee
// more than 45 degrees off the foot's direction, on a bent leg), slide (the ball moving more than 6 mm in a frame, in
// the acts that stand still). Prints one JSON object.
const {open, freeze} = require('./lib');
(async () => {
  const {browser, page, errors} = await open(process.argv[2]);
  await freeze(page);
  const r = await page.evaluate(() => {
    const X = window.__X, T = X.THREE, it = VW.it, B = n => it.bones.find(b => b.name === n), out = {};
    const P = n => B(n).getWorldPosition(new T.Vector3()), Q = n => B(n).getWorldQuaternion(new T.Quaternion());
    const MOVING = {walkF: 1, walkB: 1, dashF: 1, dashB: 1, thr: 1, knock: 1, getup: 1, juggle: 1, air: 1, landing: 1, jumpSquat: 1};
    // rest frames of the feet: sole normal and toe direction in the foot's own frame
    const md = X.mdData('ren'); X.mdApply(it, X.mdRest(md)); it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
    const rest = {};
    const pos = md.geo.attributes.position;
    for (const s of ['Left', 'Right']) {
      const q = Q(s + 'Foot').invert(), ank = P(s + 'Foot'), ball = P(s + 'ToeBase'), f = ball.clone().sub(ank).setY(0).normalize();
      let far = 0;   // the toe tip: the farthest low vertex of this side along the foot
      for (let i = 0; i < pos.count; i++) { const x = pos.getX(i); if (pos.getY(i) > .07 || (x > 0) !== (s === 'Left')) continue; far = Math.max(far, (x - ball.x) * f.x + (pos.getZ(i) - ball.z) * f.z); }
      rest[s] = {up: new T.Vector3(0, 1, 0).applyQuaternion(q), ball: ball.y, tip: new T.Vector3(ball.x + f.x * far, 0, ball.z + f.z * far).sub(ank).applyQuaternion(q),
        len: P(s + 'UpLeg').distanceTo(P(s + 'Leg')) + P(s + 'Leg').distanceTo(P(s + 'Foot'))};
    }
    for (const mode of ['old', 'new']) {
      document.getElementById(mode === 'old' ? 'aOld' : 'aNew').click();
      if (VW.RN.opt && VW.RN.opt.dummy) document.getElementById('opt_dummy').click();
      const D = {}, add = (k, act, af, val) => { const d = D[k] || (D[k] = {frames: 0, worst: 0, at: '', acts: {}}); d.frames++; d.acts[act] = (d.acts[act] || 0) + 1; if (val > d.worst) { d.worst = +val.toFixed(3); d.at = act + ' f' + af; } };
      for (let i = 0; i < X.VW_PLAYS.length; i++) {
        document.getElementById('play' + i).click();
        let wraps = 0, last = VW.step, prev = null;
        for (let t = 0; t < (VW.plan.length > 1 ? 3000 : 300) && wraps < 1; t++) {
          VW.tick(1); if (VW.step < last) wraps++; last = VW.step;
          const F = VW.F, act = F.act, af = F.af;
          if (F.air || act === 'knock' || act === 'getup' || act === 'juggle') { prev = null; continue; }
          it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
          const cur = {act};
          for (const s of ['Left', 'Right']) {
            const hip = P(s + 'UpLeg'), knee = P(s + 'Leg'), ank = P(s + 'Foot'), ball = P(s + 'ToeBase'), R = rest[s];
            const tip = R.tip.clone().applyQuaternion(Q(s + 'Foot')).add(ank), h = Math.min(ball.y - R.ball, tip.y);   // the shoe's lowest point over the floor
            const onTip = tip.y < ball.y - R.ball, pt = onTip ? tip : ball;   // the point it stands on
            if (h > .06) continue;   // not standing on the floor
            cur[s] = {x: pt.x, z: pt.z, onTip};
            const ext = hip.distanceTo(ank) / R.len;
            if (ext > .985) add('stretched', act, af, ext);
            if (h > .015) add('floating', act, af, h * 1000);
            if (h < -.012) add('sunk', act, af, -h * 1000);
            const up = R.up.clone().applyQuaternion(Q(s + 'Foot')), fwd = ball.clone().sub(ank).setY(0).normalize(), lat = new T.Vector3().crossVectors(new T.Vector3(0, 1, 0), fwd);
            const roll = Math.abs(Math.asin(Math.max(-1, Math.min(1, up.dot(lat))))) * 180 / Math.PI;
            if (roll > 12) add('rolled', act, af, roll);
            if (ext < .96) {
              const d = ank.clone().sub(hip).normalize(), k = knee.clone().sub(hip); k.addScaledVector(d, -k.dot(d)); k.setY(0);
              if (k.length() > .03) { const a = Math.acos(Math.max(-1, Math.min(1, k.normalize().dot(fwd)))) * 180 / Math.PI; if (a > 45) add('knee', act, af, a); }
            }
            if (prev && prev.act === act && !MOVING[act] && prev[s] && prev[s].onTip === onTip) { const sl = Math.hypot(pt.x - prev[s].x, pt.z - prev[s].z) * 1000; if (sl > 6) add('slide', act, af, sl); }
          }
          prev = cur;
        }
      }
      out[mode] = D;
    }
    document.getElementById('aNew').click();
    return out;
  });
  console.log(JSON.stringify({errors, ...r}, null, 1));
  await browser.close();
})();
