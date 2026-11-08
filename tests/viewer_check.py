#!/usr/bin/env python3
"""Check of the character viewer (viewer.html, built by mk.sh): it boots with Ren on the stage, every play button and
option works, the picture is not empty and the console stays clean. Phone landscape and portrait sizes, touch.

usage: python3 tests/viewer_check.py [OUT_DIR]   (OUT_DIR: also save a screenshot per size)
"""
import asyncio, os, sys, tempfile
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox']
CHROME = next((c for c in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/opt/pw-browsers/chromium') if os.path.isfile(c)), None)
# the published page gets this skeleton from the artifact host
WRAP = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light}body{margin:0;font:14px/1.4 system-ui,sans-serif}[hidden]{display:none!important}</style></head><body>%s</body></html>')


# The sash out of the body (Denis: "la fascia non entri nei vestiti/corpo"): every 3rd of 180 frames of each play button
# (started from a still guard), more than 5 mm in (less is a touch, under the outlines),
# the sash's vertices below the band against the body as drawn (skinned on the CPU), inside = winding number > 0 by signed
# ray crossings on 3 of 4 axis rays (the mesh's parts overlap). Returns the self-test (the hips' joint inside: 4 votes, a
# point 1 m in front: 0) and per button [share of points inside, deepest (m, along the rays)].
INSIDE = """async ([plays, frames, every]) => {
  const it = VW.it, mesh = it.mesh, g = mesh.geometry, I = g.index.array, nt = I.length / 3, CELL = .02, v = new THREE.Vector3();
  const rib = []; it.body.traverse(o => { if (o.isSkinnedMesh && o.geometry !== g && o !== it.head && o.material.isMeshToonMaterial) rib.push(o); });   /* the tails (not the new head) */
  const X = new Float32Array(g.attributes.position.count * 3);
  const skin = (m, out) => { const p = m.geometry.attributes.position; for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); m.boneTransform(i, v); v.applyMatrix4(m.matrixWorld); out[i * 3] = v.x; out[i * 3 + 1] = v.y; out[i * 3 + 2] = v.z; } return out; };
  const grid = (a, b) => { const G = new Map();
    for (let t = 0; t < nt; t++) { let l0 = 1e9, h0 = -1e9, l1 = 1e9, h1 = -1e9;
      for (let k = 0; k < 3; k++) { const i = I[t * 3 + k] * 3; l0 = Math.min(l0, X[i + a]); h0 = Math.max(h0, X[i + a]); l1 = Math.min(l1, X[i + b]); h1 = Math.max(h1, X[i + b]); }
      for (let c0 = Math.floor(l0 / CELL); c0 <= Math.floor(h0 / CELL); c0++) for (let c1 = Math.floor(l1 / CELL); c1 <= Math.floor(h1 / CELL); c1++) {
        const key = c0 * 100003 + c1; let l = G.get(key); if (!l) G.set(key, l = []); l.push(t); } }
    return G; };
  const cross = (G, a, b, c, p) => { const l = G.get(Math.floor(p[a] / CELL) * 100003 + Math.floor(p[b] / CELL)); let wp = 0, wm = 0, dp = 1e9, dm = 1e9;
    if (l) for (const t of l) { const i0 = I[t * 3] * 3, i1 = I[t * 3 + 1] * 3, i2 = I[t * 3 + 2] * 3;
      const ax = X[i0 + a], ay = X[i0 + b], bx = X[i1 + a], by = X[i1 + b], cx = X[i2 + a], cy = X[i2 + b], d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
      if (Math.abs(d) < 1e-14) continue;
      const u = ((by - cy) * (p[a] - cx) + (cx - bx) * (p[b] - cy)) / d, w = ((cy - ay) * (p[a] - cx) + (ax - cx) * (p[b] - cy)) / d, z = 1 - u - w;
      if (u < 0 || w < 0 || z < 0) continue;
      const h = u * X[i0 + c] + w * X[i1 + c] + z * X[i2 + c], e1 = [0, 1, 2].map(k => X[i1 + k] - X[i0 + k]), e2 = [0, 1, 2].map(k => X[i2 + k] - X[i0 + k]);
      const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]][c];
      if (h > p[c]) { wp += n > 0 ? 1 : -1; dp = Math.min(dp, h - p[c]); } else { wm += n < 0 ? 1 : -1; dm = Math.min(dm, p[c] - h); } }
    return [wp, wm, dp, dm]; };
  const vote = (Gz, Gx, p) => { const z = cross(Gz, 0, 1, 2, p), x = cross(Gx, 1, 2, 0, p); return [[z[0], z[1], x[0], x[1]].filter(w => w > 0).length, Math.min(z[2], z[3], x[2], x[3])]; };
  VW.speed = 0; VW.spin = false; it.root.updateMatrixWorld(true); skin(mesh, X);
  const hip = it.bones[0].getWorldPosition(new THREE.Vector3()).toArray(), Gz0 = grid(0, 1), Gx0 = grid(1, 2);
  const out = {self: [vote(Gz0, Gx0, hip)[0], vote(Gz0, Gx0, [hip[0], hip[1], hip[2] + 1])[0]]};
  for (const k of plays) {   // each from a still guard (a button pressed mid-air drops the fighter to the floor at once)
    document.getElementById('play0').click(); VW.tick(20); it.sash.F = null; VW.tick(60);   // the guard's pose settled, the sash anew
    document.getElementById('play' + k).click(); let bad = 0, pts = 0, deep = 0;
    for (let f = 0; f < frames; f++) {
      VW.tick(1); if (f % every) continue;
      it.root.updateMatrixWorld(true); skin(mesh, X); const Gz = grid(0, 1), Gx = grid(1, 2);
      for (const r of rib) { const R = skin(r, new Float32Array(r.geometry.attributes.position.count * 3));
        for (let i = (it.sash.ribbons[rib.indexOf(r)].tuckRows + 2) * 4; i < R.length / 3; i++) { /* not the part under the band */ const [vt, d] = vote(Gz, Gx, [R[i * 3], R[i * 3 + 1], R[i * 3 + 2]]); pts++; if (vt >= 3 && d > .005) { bad++; deep = Math.max(deep, d); } } } }
    out[k] = [bad / pts, deep]; }
  VW.speed = 1; return out; }"""
SASH_OUT = {0: .01, 1: .01, 2: .01, 3: .025, 4: .05, 5: .01, 6: .01, 7: .015, 8: .015, 9: .04}   # most shares inside allowed per
# button (7/11/2026, light tails on the band's skin, the worst of 5 starting moments: guard .1%, walk 0, punches .1%,
# kicks .6%, crouch 2.6%, jump .1%, special 0, throw 0, hit 0, down 2.2%; before, with the legs as thin capsules: 8
# to 38%). Crouching and lying, the top of the sash is pressed between the thighs and the belly, hidden in the fold.


async def route(r):
    u = r.request.url
    if 'three.min.js' in u: await r.fulfill(path=os.path.join(ROOT, 'three.min.js'), content_type='application/javascript')
    elif u.startswith('file://'): await r.continue_()
    else: await r.abort()


async def main(out_dir):
    page_file = os.path.join(tempfile.mkdtemp(), 'viewer.html')
    open(page_file, 'w', encoding='utf-8').write(WRAP % open(os.path.join(ROOT, 'viewer.html'), encoding='utf-8').read())
    failed = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=ARGS)
        for w, h in ((844, 390), (390, 844)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
            pg.on('console', lambda m: errs.append('CONSOLE ' + m.text) if m.type in ('error', 'warning') and 'Failed to load resource' not in m.text else None)
            await pg.route('**/*', route); await pg.goto('file://' + page_file)
            await pg.wait_for_function("document.getElementById('now') && document.getElementById('now').textContent.length > 0", timeout=60000)
            n = await pg.evaluate("document.querySelectorAll('#moves button').length")
            for i in range(n):
                await pg.click('#play%d' % i); await pg.wait_for_timeout(250)
            for bid in ('pMeshy', 'lFlat', 's4', 'spin', 'pDraw', 'lToon', 's1', 'spin'):
                await pg.click('#' + bid)
            await pg.click('#play2'); await pg.wait_for_timeout(700)
            # the canvas shows the fighter: some pixels are not transparent in the middle of the picture
            drawn = await pg.evaluate("""() => { const c = document.getElementById('view'), g = document.createElement('canvas'); g.width = 64; g.height = 64;
              const x = g.getContext('2d'); x.drawImage(c, c.width * .35, c.height * .2, c.width * .3, c.height * .6, 0, 0, 64, 64);
              const d = x.getImageData(0, 0, 64, 64).data; let k = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) k++; return k; }""")
            # the proposal's look: fists in the guard (the fingers curled on their own bones, in the skeleton), open hands
            # in the special, spikes on the head, thin face outline
            look = await pg.evaluate("""async () => { const it = VW.it, r = {};
              document.getElementById('play0').click(); await new Promise(f => setTimeout(f, 300));
              const sashBones = it.sash ? it.sash.ribbons.reduce((n, q) => n + q.bones.length, 0) : 0;
              r.fists = !!it.fingers && it.fingers.length === 30 && it.mesh.skeleton.bones.length === it.bones.length + 30 + sashBones && it.curl === 1
                && it.fingers.every((o, i) => Math.abs(o.quaternion.dot(it.fist[i])) > .9999);
              it.root.updateMatrixWorld(true);   // a real fist: the four curled fingers end level (hand frame, within 2 mm)
              r.level = ['Left', 'Right'].every(h => { const H = it.bones.find(b => b.name === h + 'Hand');
                const y = ['Index', 'Middle', 'Ring', 'Pinky'].map(f => Math.min(...[2, 3].map(k => H.worldToLocal(it.fingers.find(o => o.name === h + 'Hand' + f + k).getWorldPosition(new THREE.Vector3())).y)));
                return Math.max(...y) - Math.min(...y) < .002; });
              document.getElementById('play6').click(); await new Promise(f => setTimeout(f, 300));
              r.open = it.curl === 0 && it.fingers.every(o => Math.abs(o.quaternion.w) > .9999);
              r.spikes = it.joints.head.children.some(g => g.isGroup && g.children.length >= 8) || !!it.head;   // (the new head has its own hair)
              r.head = !!it.head && it.head.isSkinnedMesh && it.head.geometry.index.count > 30000;   // the new head (the viewer turns it on)
              r.line = !!it.mesh.geometry.attributes.aLine && !!it.mesh.geometry.attributes.aFlat; return r; }""")
            # the sash: two ribbons on chains of bones; calm in the guard, swinging after a jump, never NaN
            sash = await pg.evaluate("""async () => { const it = VW.it, sa = it.sash, r = {};
              if (!sa) return {ribbons: false};
              const tip = () => sa.ribbons.map(q => q.P[q.P.length - 1].clone()), off = () => Math.max(...sa.ribbons.map(q => q.P[q.P.length - 1].distanceTo(q.T[q.T.length - 1])));
              VW.speed = 0; document.getElementById('play0').click(); VW.tick(100);   // the guard, still (game frames, not the clock)
              const a = tip(); VW.tick(12); const b = tip(); VW.speed = 1;
              r.ribbons = sa.ribbons.length === 2 && sa.ribbons.every(q => q.bones.length >= 4);
              r.calm = a.every((p, i) => p.distanceTo(b[i]) < .02);
              document.getElementById('play5').click(); let most = 0;
              for (let k = 0; k < 12; k++) { await new Promise(f => setTimeout(f, 80)); most = Math.max(most, off()); }
              r.swings = most > .03 && most < 1;   // moves, without flying off (it is .5 m long)
              r.finite = sa.ribbons.every(q => q.P.every(p => Number.isFinite(p.x + p.y + p.z)));
              return r; }""")
            look.update(sash)
            if not all(look.values()): errs.append('look ' + str(look))
            if w > h:   # once: the sash out of the body in every play button's moves
                ins = await pg.evaluate(INSIDE, [list(SASH_OUT), 180, 3]); slf = ins.pop('self')
                over = {k: v for k, v in ins.items() if v[0] > SASH_OUT[int(k)]}
                if slf != [4, 0] or over: errs.append('sash inside the body %s (self-test %s)' % ({k: [round(v[0], 3), round(v[1], 3)] for k, v in over.items()}, slf))
                print('  sash inside the body, per button (share, deepest m):', {k: [round(v[0], 3), round(v[1], 3)] for k, v in ins.items()})
            ok = n == 10 and drawn > 200 and not errs
            failed += not ok
            print(('PASS' if ok else 'FAIL') + ' viewer %dx%d: %d play buttons, %d drawn pixels of 4096 in the middle%s' % (w, h, n, drawn, (', ' + ' | '.join(errs[:3])) if errs else ''))
            if out_dir: await pg.screenshot(path=os.path.join(out_dir, 'viewer_%dx%d.png' % (w, h)))
            await ctx.close()
        await b.close()
    print('%d failed (viewer_check)' % failed)
    return failed


if __name__ == '__main__':
    sys.exit(1 if asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None)) else 0)
