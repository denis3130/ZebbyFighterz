// Contact sheets: for each act of the chosen plays, one PNG with a row per camera angle and a column per key frame.
//   node tests/sheet.js <page.html> <outDir> [--plays 2,3] [--acts hp,hk] [--yaws 65,0,155,245] [--old] [--scene]
//                       [--cell 360x420] [--zoom 1] [--frames N] [--nodummy]
// --old draws the original animation; --scene keeps the waterfall (default: a plain backdrop with a floor grid, so
// feet and silhouettes read); yaws in degrees (65 = the game's view of a fighter facing right, 0 = from the front).
const {open, freeze, drawn} = require('./lib');
const fs = require('fs'), path = require('path'), {execFileSync} = require('child_process');

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : (process.argv[i + 1] === undefined || process.argv[i + 1].startsWith('--') ? true : process.argv[i + 1]); };
(async () => {
  const html = process.argv[2], out = process.argv[3];
  if (!html || !out) { console.error('usage: node sheet.js <page.html> <outDir> [options]'); process.exit(2); }
  const [cw, ch] = String(arg('cell', '360x420')).split('x').map(Number), yaws = String(arg('yaws', '65,0,155,245')).split(',').map(Number);
  const plays = arg('plays', null), acts = arg('acts', null), old = !!arg('old', false), nF = +arg('frames', 8);
  fs.mkdirSync(out, {recursive: true});
  const {browser, page, errors} = await open(html, {w: cw, h: ch});
  await freeze(page);
  await page.evaluate(([old, scene, zoom, nodummy]) => {
    document.getElementById('top').style.display = 'none';
    document.getElementById('bottom').style.cssText = 'position:fixed;top:100%;bottom:auto;visibility:hidden';   // (vwResize fits the view above it)
    if (!scene) {
      document.getElementById('stage').style.backgroundImage = 'none'; document.getElementById('stage').style.background = '#8d94a3';
      const T = window.__X ? window.__X.THREE : window.THREE, g = new T.GridHelper(6, 24, 0x30343c, 0x6f7684); g.position.y = .001; VW.scene.add(g);
    }
    if (nodummy && VW.RN && 'dummy' in VW.RN.opt) document.getElementById('opt_dummy').click();
    document.getElementById(old ? 'aOld' : 'aNew').click();
    VW.zoom = zoom; dispatchEvent(new Event('resize'));
  }, [old, !!arg('scene', false), +arg('zoom', 1), !!arg('nodummy', false)]);
  const nPlays = await page.evaluate(() => document.querySelectorAll('#moves button').length);
  const manifest = [];
  for (let pi = 0; pi < nPlays; pi++) {
    if (plays && !String(plays).split(',').map(Number).includes(pi)) continue;
    // the play's timeline: one cycle of (tick, step, act, af, hitting)
    const tl = await page.evaluate(pi => {
      document.getElementById('play' + pi).click();
      const a = []; let last = VW.step, wraps = 0;
      for (let t = 0; t < 2000; t++) {
        if (VW.step < last) wraps++; last = VW.step; if (wraps) break;
        const m = __X.CFG.moves[VW.F.act];
        a.push({t, step: VW.step, act: VW.F.act, name: VW.name, af: VW.F.af, hit: !!(m && VW.F.af > m.s && VW.F.af <= m.s + m.a), m: m ? [m.s, m.a, m.r === 'land' ? 8 : m.r] : null});
        VW.tick(1);
      }
      return a;
    }, pi);
    const steps = [...new Set(tl.map(x => x.step))];
    for (const st of steps) {
      const fr = tl.filter(x => x.step === st), act = fr[0].act, label = (fr[0].name || act);
      if (acts && !String(acts).split(',').includes(act)) continue;
      let pick;
      if (fr[0].m) {
        const [s, a, r] = fr[0].m, want = [0, Math.round(s * .35), Math.round(s * .7), s, s + 1, s + a, s + a + Math.round(r * .25), s + a + Math.round(r * .6), s + a + r];
        pick = [...new Set(want)].map(af => fr.find(x => x.af === af)).filter(Boolean);
      } else {
        const n = Math.min(nF, fr.length); pick = [];
        for (let k = 0; k < n; k++) pick.push(fr[Math.round(k * (fr.length - 1) / Math.max(1, n - 1))]);
        pick = [...new Set(pick)];
      }
      const cells = [];
      await page.evaluate(pi => { document.getElementById('play' + pi).click(); }, pi);
      let at = 0;
      for (const f of pick) {
        await page.evaluate(n => VW.tick(n), f.t - at); at = f.t;
        for (const yaw of yaws) {
          await page.evaluate(y => { VW.yaw = y * Math.PI / 180; }, yaw);
          await drawn(page);
          const file = path.join(out, `_c_${pi}_${st}_${f.t}_${yaw}.png`);
          await page.screenshot({path: file});
          cells.push({file, yaw, af: f.af, hit: f.hit});
        }
      }
      manifest.push({out: path.join(out, `${pi}_${st}_${act}${old ? '_old' : ''}.png`), title: `${label} (${act})${old ? ' — ORIGINAL' : ''}`, yaws, cols: pick.map(f => `f${f.af}${f.hit ? ' HIT' : ''}`), cells, cw, ch});
    }
  }
  await browser.close();
  const mf = path.join(out, '_manifest.json');
  fs.writeFileSync(mf, JSON.stringify(manifest));
  execFileSync('python3', [path.join(__dirname, 'compose.py'), mf], {stdio: 'inherit'});
  for (const m of manifest) for (const c of m.cells) fs.unlinkSync(c.file);
  fs.unlinkSync(mf);
  console.log(JSON.stringify({sheets: manifest.map(m => m.out), errors}));
})();
