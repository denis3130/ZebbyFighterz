// Sanity check of a built page, both animations (old = original, new = the layer):
//   node tests/check.js <page.html>
// - no page error, no NaN in any bone, every play runs 2 cycles;
// - hit accuracy: at each move's active frames the hitting limb's distance (mm) outside the move's box, facing right,
//   as the game places the model (mdMeasure's convention): new must not be worse than old by more than 30 mm;
// - cost: ms per frame of the pose pipeline (VW.tick), old and new.
// Prints one JSON object; exit code 1 when a check fails.
const {open, freeze} = require('./lib');
(async () => {
  const {browser, page, errors} = await open(process.argv[2]);
  await freeze(page);
  const r = await page.evaluate(() => {
    const X = window.__X, CFG = X.CFG, T = X.THREE, out = {modes: {}}, v = new T.Vector3();
    const dummyOff = () => { if (VW.RN && VW.RN.opt && VW.RN.opt.dummy) document.getElementById('opt_dummy').click(); };
    for (const mode of ['old', 'new']) {
      document.getElementById(mode === 'old' ? 'aOld' : 'aNew').click(); dummyOff();
      const box = {}; let nan = 0, frames = 0, t0 = 0, ms = 0;
      for (let i = 0; i < X.VW_PLAYS.length; i++) {
        document.getElementById('play' + i).click();
        let wraps = 0, last = VW.step;
        for (let t = 0; t < 4000 && wraps < 2; t++) {
          t0 = performance.now(); VW.tick(1); ms += performance.now() - t0; frames++;
          if (VW.step < last) wraps++; last = VW.step;
          for (const b of VW.it.bones) if (!(b.quaternion.x === b.quaternion.x) || !(b.position.y === b.position.y)) nan++;
          const F = VW.F, m = CFG.moves[F.act];
          if (m && F.af > m.s && F.af <= m.s + m.a) {
            const e = CFG.clips[F.act] || {}, limb = e.limb || (e.up && e.up.limb) || m.limb, k = m.box, it = VW.it;
            const keep = [it.root.position.clone(), it.root.rotation.y, it.body.scale.x];
            it.root.position.set(0, 0, 0); it.root.rotation.y = X.F3_YAW; it.body.scale.x = it.scale; it.root.updateMatrixWorld(true);
            it.limbs[limb].getWorldPosition(v);
            const x = v.x * 1000, y = v.y * 1000, d = Math.hypot(Math.max(k[0] - x, 0, x - k[1]), Math.max(k[2] - y, 0, y - k[3]));
            box[F.act] = Math.max(box[F.act] || 0, Math.round(d));
            it.root.position.copy(keep[0]); it.root.rotation.y = keep[1]; it.body.scale.x = keep[2];
          }
        }
      }
      out.modes[mode] = {frames, nan, msPerFrame: +(ms / frames).toFixed(3), box};
    }
    document.getElementById('aNew').click();
    return out;
  });
  const fail = [];
  if (errors.length) fail.push('page errors: ' + errors.slice(0, 3).join(' | '));
  for (const m of ['old', 'new']) if (r.modes[m].nan) fail.push(m + ': NaN in bones');
  for (const id in r.modes.old.box) if ((r.modes.new.box[id] || 0) > r.modes.old.box[id] + 30) fail.push(`hit accuracy ${id}: limb ${r.modes.new.box[id]} mm outside its box (old ${r.modes.old.box[id]})`);
  r.fail = fail;
  console.log(JSON.stringify(r));
  await browser.close();
  process.exit(fail.length ? 1 : 0);
})();
