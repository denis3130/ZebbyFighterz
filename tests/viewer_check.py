#!/usr/bin/env python3
"""Check of a character viewer (viewer.html, viewer_kael.html, built by mk.sh): it boots with its character on the stage,
every play button and option works, the picture is not empty and the console stays clean. Phone landscape and portrait
sizes, touch. Ren's page: his whole look (new head, its locks, the sash out of the body, both paints); Kael's: his fists on
his own finger bones, the outline's widths, his clothes (the body's shape moved, tools/kael_outfit.py), both paints.

usage: python3 tests/viewer_check.py [OUT_DIR] [--page=viewer_kael.html]   (OUT_DIR: also save a screenshot per size)
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
  const rib = []; it.body.traverse(o => { if (o.isSkinnedMesh && o.geometry !== g && o !== it.head && o !== it.fringe && o.material.isMeshToonMaterial) rib.push(o); });   /* the tails (not the new head, nor its locks from the sheet) */
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


# Kael's gloves (17/11): a shell over Ren's hands, its rings at the wrists. skinP: a part vertex's (or a point near it,
# with the vertex's skin) place in the world, as the GPU skins it (SkinnedMesh.boneTransform, for any bind point)
GEAR = """async () => { const it = VW.it, r = {};
  const plum = async (hide) => { await new Promise(f => setTimeout(f, 150)); it.root.updateMatrixWorld(true);   // (plum pixels round the left fist)
    const c = document.getElementById('view'), bone = n => it.bones.find(o => o.name === n) || it.fingers.find(o => o.name === n);
    const v = bone('LeftHand').getWorldPosition(new THREE.Vector3()).lerp(bone('LeftHandMiddle1').getWorldPosition(new THREE.Vector3()), .7).project(VW.camera);
    const x = (v.x + 1) / 2 * c.width, y = (1 - v.y) / 2 * c.height, g = document.createElement('canvas'); g.width = g.height = 80;
    const ctx = g.getContext('2d'); ctx.drawImage(c, x - 40, y - 40, 80, 80, 0, 0, 80, 80); const d = ctx.getImageData(0, 0, 80, 80).data; let k = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 0 && d[i + 2] > d[i] && d[i] > d[i + 1] && d[i + 2] - d[i + 1] > 12 && d[i + 2] < 160) k++; return k; };
  if (it.arms) {   // Meshy's forearms (19/11): textured, flashed when hit, the fist or the open hand as the moves ask, the wrists straight
    // in the fists (the hand's line, wrist to the middle finger's first joint, on the forearm's), drawn mirrored too
    const W = o => o.getWorldPosition(new THREE.Vector3()), bone = n => it.bones.find(o => o.name === n) || it.fingers.find(o => o.name === n);
    r.arms = it.arms.every(m => !!m[0].material.map && m[1].isSkinnedMesh);
    r.flash = [it.mats.armFist, it.mats.armOpen].every(m => !!m && it.arms.some(a => a[0].material === m));
    VW.speed = 0; let bend = 0;
    for (const [b, n] of [[0, 40], [2, 7], [2, 12], [3, 30]]) { document.getElementById('play' + b).click(); VW.tick(n); it.root.updateMatrixWorld(true);
      for (const sd of ['Left', 'Right']) { const E = W(bone(sd + 'ForeArm')), H = W(bone(sd + 'Hand')), M = W(bone(sd + 'HandMiddle1'));
        bend = Math.max(bend, THREE.MathUtils.radToDeg(H.clone().sub(E).angleTo(M.clone().sub(H)))); } }
    r.straight = bend < 3; r.straightPx = +bend.toFixed(2);
    document.getElementById('play0').click(); VW.tick(40); const fist = it.arms[0][0].visible && !it.arms[1][0].visible;
    document.getElementById('play6').click(); VW.tick(20); const open = !it.arms[0][0].visible && it.arms[1][0].visible;
    r.swap = fist && open;
    document.getElementById('play0').click(); VW.tick(40); VW.spin = false; VW.yaw = .55; VW.zoom = .45; it.root.scale.x = -1;
    const withA = await plum(); it.arms.forEach(m => { m[0].material.visible = false; }); const without = await plum(); it.arms.forEach(m => { m[0].material.visible = true; });
    r.mirror = withA - without > 30; r.mirrorPx = withA - without;
    it.root.scale.x = 1; VW.zoom = 1; VW.speed = 1;
    return r;
  }
  r.gloves = !!it.gloves && !!it.gloves.geometry.attributes.color && !!it.gloves.geometry.attributes.aGlove;
  r.flash = !!it.hands && !!it.gloves && [it.hands.material, it.gloves.material].every(m => Object.values(it.mats).includes(m));
  if (!r.gloves) return r;
  const M = new THREE.Matrix4(), T = new THREE.Vector3();
  const skinP = (m, i, p) => { const g = m.geometry, si = g.attributes.skinIndex, sw = g.attributes.skinWeight, v = p.clone().applyMatrix4(m.bindMatrix), o = new THREE.Vector3();
    for (let k = 0; k < 4; k++) { const w = sw.array[i * 4 + k]; if (!w) continue; const b = si.array[i * 4 + k];   /* (r128: no getComponent) */
      M.multiplyMatrices(m.skeleton.bones[b].matrixWorld, m.skeleton.boneInverses[b]); o.addScaledVector(T.copy(v).applyMatrix4(M), w); }
    return o.applyMatrix4(m.bindMatrixInverse).applyMatrix4(m.matrixWorld); };
  const P = (a, i) => new THREE.Vector3().fromBufferAttribute(a, i);
  const G = it.gloves, H = it.hands, gp = G.geometry.attributes.position, gd = G.geometry.attributes.aGlove, hp = H.geometry.attributes.position;
  // the shell inside the glove (over 3 mm from its edge), 300 of its vertices, each with its skin's nearest vertex
  const pj0 = G.userData.part || {}, flared = q => (pj0.rings || []).some(g => { const c = new THREE.Vector3(...g.c), ax = new THREE.Vector3(...g.ax), d = q.clone().sub(c), t = d.dot(ax);
    return t < g.h / 2 + .025 && d.addScaledVector(ax, -t).length() < .1; });   // (by the rings the glove and the skin flare out to them together)
  const inner = []; for (let i = 0; i < gp.count; i++) if (gd.getX(i) < -.003 && !flared(P(gp, i))) inner.push(i);
  const pick = inner.filter((_, k) => k % Math.max(1, Math.floor(inner.length / 300)) === 0).map(i => { const q = P(gp, i); let best = 1e9, j = -1;
    for (let k = 0; k < hp.count; k++) { const d = q.distanceToSquared(P(hp, k)); if (d < best) { best = d; j = k; } } return [i, j]; });
  VW.speed = 0; let ok = 0, n = 0;
  for (let b = 0; b < 10; b++) { document.getElementById('play' + b).click();
    for (let f = 0; f < 60; f += 6) { VW.tick(6); it.root.updateMatrixWorld(true);
      for (const [i, j] of pick) {   // (the shell moves with the skin under it: its rest offset from that skin, carried by the skin's
        // own motion, still at least half there; a shell sinking into the skin, or left behind, falls under it)
        const o0 = P(gp, i).sub(P(hp, j)), Hs = skinP(H, j, P(hp, j)), o1 = skinP(H, j, P(hp, j).add(o0)).sub(Hs), S = skinP(G, i, P(gp, i));
        n++; if (S.sub(Hs).dot(o1.normalize()) > .5 * o0.length()) ok++; } } }
  r.shell = ok / n > .99; r.shellShare = ok / n;
  // the wrists' rings cover their joins in every move: what was inside a ring at rest (the cuff's end, the hand's start) stays
  // on the inner side of the ring's outer wall (its nearest vertex there, along that vertex's normal)
  const pj = G.userData.part; r.ring = false;
  if (pj && pj.rings && it.bust) {
    const Bm = it.bust, bp = Bm.geometry.attributes.position, gn = G.geometry.attributes.normal; let rok = 0, rn = 0;
    for (let b = 0; b < 10; b++) { document.getElementById('play' + b).click();
      for (let f = 0; f < 60; f += 6) { VW.tick(6); it.root.updateMatrixWorld(true);
        for (const g of pj.rings) {
          const R = []; for (let i = g.outer[0]; i < g.outer[0] + g.outer[1]; i += 3) { const p0 = P(gp, i), q = skinP(G, i, p0); R.push([q, skinP(G, i, p0.clone().addScaledVector(P(gn, i), .001)).sub(q).normalize()]); }
          const ins = g.inBust.filter((_, k) => k % 4 === 0).map(i => skinP(Bm, i, P(bp, i))).concat(g.inHands.map(i => skinP(H, i, P(hp, i))));
          for (const V of ins) { let best = 1e9, nr = null; for (const [q, nq] of R) { const d = V.distanceToSquared(q); if (d < best) { best = d; nr = [q, nq]; } }
            rn++; if (V.clone().sub(nr[0]).dot(nr[1]) < 0) rok++; } } } }
    r.ring = rok / rn > .995; r.ringShare = rok / rn;
  }
  // mirrored (the fighter on the right): the glove still drawn (pixels it adds round the fist)
  document.getElementById('play0').click(); VW.tick(40); VW.spin = false; VW.yaw = .55; VW.zoom = .45; it.root.scale.x = -1;
  const withG = await plum(); G.visible = false; const without = await plum(); G.visible = true;
  r.mirror = withG - without > 30; r.mirrorPx = withG - without;
  it.root.scale.x = 1; VW.zoom = 1; VW.speed = 1;
  return r; }"""
REN_ONLY = ('spikes', 'head', 'fringe', 'flat', 'ribbons', 'calm', 'swings', 'finite')   # (the look's parts only Ren has)
KAEL_ONLY = ('hands', 'flash', 'gloves', 'shell', 'ring', 'mirror', 'arms', 'straight', 'swap', 'outfit')   # (Kael's: his hands Ren's as their own part, his gloves and wrists' rings, 17/11; or Meshy's forearms, 19/11)


async def main(out_dir, page='viewer.html'):
    ren = page == 'viewer.html'; name = 'REN' if ren else os.path.splitext(page)[0].split('_')[-1].upper()
    page_file = os.path.join(tempfile.mkdtemp(), page)
    open(page_file, 'w', encoding='utf-8').write(WRAP % open(os.path.join(ROOT, page), encoding='utf-8').read())
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
            # its name; the paint buttons (both have the drawing painted on them: Ren since 7/11, Kael's clothes since
            # 10/11), each paint its own picture
            if not (await pg.inner_text('#name')).startswith(name) or not (await pg.title()).endswith(name.capitalize()): errs.append('not %s\'s page' % name)
            if not await pg.is_visible('#paint'): errs.append('paint buttons hidden')
            if await pg.evaluate("VW.tex.meshy.image.src === VW.tex.draw.image.src"): errs.append('paints the same')
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
              document.getElementById('play0').click(); VW.tick(12);   /* (game frames, not the clock: the same on a slow machine) */
              const sashBones = it.sash ? it.sash.ribbons.reduce((n, q) => n + q.bones.length, 0) : 0;
              r.fists = !!it.fingers && it.fingers.length === 30 && it.mesh.skeleton.bones.length === it.bones.length + 30 + sashBones && it.curl === 1
                && it.fingers.every((o, i) => Math.abs(o.quaternion.dot(it.fist[i])) > .9999);
              it.root.updateMatrixWorld(true);   // a real fist: the four curled fingers end level (hand frame, within 2 mm; the fist's own frame where the model gives one, it.fistFrame: Kael's bust's hands)
              r.level = ['Left', 'Right'].every(h => { const H = it.bones.find(b => b.name === h + 'Hand'), fq = it.fistFrame ? it.fistFrame[h].clone().invert() : new THREE.Quaternion();
                const y = ['Index', 'Middle', 'Ring', 'Pinky'].map(f => Math.min(...[2, 3].map(k => H.worldToLocal(it.fingers.find(o => o.name === h + 'Hand' + f + k).getWorldPosition(new THREE.Vector3())).applyQuaternion(fq).y)));
                return Math.max(...y) - Math.min(...y) < .002; });
              document.getElementById('play6').click(); VW.tick(12);
              r.open = it.curl === 0 && it.fingers.every(o => Math.abs(o.quaternion.w) > .9999);
              r.spikes = it.joints.head.children.some(g => g.isGroup && g.children.length >= 8) || !!it.head;   // (the new head has its own hair)
              r.head = !!it.head && it.head.isSkinnedMesh && it.head.geometry.index.count > 30000;   // the new head (the viewer turns it on)
              r.fringe = !!it.fringe && it.fringe.isSkinnedMesh && it.fringe.geometry.index.count > 6000 && it.fringe.material.alphaTest > 0;   // its locks from the sheet (over 2000 triangles)
              r.line = !!it.mesh.geometry.attributes.aLine; r.flat = !!it.mesh.geometry.attributes.aFlat;
              // (Kael: Ren's hands as their own part on the same skeleton (Ren's are 1305 triangles), flashing with the body: f_fx lights every material of it.mats)
              r.hands = (!!it.hands && it.hands.isSkinnedMesh && it.hands.skeleton === it.mesh.skeleton && it.hands.geometry.index.count / 3 > 1000)
                || (!!it.arms && it.arms.length === 2 && it.arms.every(m => m[0].isSkinnedMesh && m[0].skeleton === it.mesh.skeleton && m[0].geometry.index.count / 3 > 1000));   // (or Meshy's forearms, 19/11)
              // (Kael's clothes from Meshy, 19/11: their own skinned mesh on his skeleton, all of his own body's triangles hidden)
              r.outfit = !!it.bust && it.bust.isSkinnedMesh && it.bust.skeleton === it.mesh.skeleton && it.bust.geometry.index.count / 3 > 10000 && it.mesh.geometry.index.count === 0;
              r.flash = !!it.hands && Object.values(it.mats).includes(it.hands.material);
              return r; }""")
            # the sash: two ribbons on chains of bones; calm in the guard, swinging after a jump, never NaN
            sash = await pg.evaluate("""async () => { const it = VW.it, sa = it.sash, r = {};
              if (!sa) return {ribbons: false};
              const tip = () => sa.ribbons.map(q => q.P[q.P.length - 1].clone()), off = () => Math.max(...sa.ribbons.map(q => q.P[q.P.length - 1].distanceTo(q.T[q.T.length - 1])));
              VW.speed = 0; document.getElementById('play0').click(); sa.F = null; VW.tick(100);   // the guard, still (game frames, not the clock; the sash anew: it kept the swing of the checks before)
              const a = tip(); VW.tick(12); const b = tip(); VW.speed = 1;
              r.ribbons = sa.ribbons.length === 2 && sa.ribbons.every(q => q.bones.length >= 4);
              r.calm = a.every((p, i) => p.distanceTo(b[i]) < .02);
              document.getElementById('play5').click(); let most = 0;
              for (let k = 0; k < 12; k++) { await new Promise(f => setTimeout(f, 80)); most = Math.max(most, off()); }
              r.swings = most > .03 && most < 1;   // moves, without flying off (it is .5 m long)
              r.finite = sa.ribbons.every(q => q.P.every(p => Number.isFinite(p.x + p.y + p.z)));
              return r; }""")
            look.update(sash)
            if not ren: look.update(await pg.evaluate(GEAR))
            look = {k: v for k, v in look.items() if k not in (KAEL_ONLY if ren else REN_ONLY)}
            if not all(v for k, v in look.items() if not k.endswith(('Share', 'Px'))): errs.append('look ' + str(look))
            if w > h and ren:   # once: the sash out of the body in every play button's moves
                ins = await pg.evaluate(INSIDE, [list(SASH_OUT), 180, 3]); slf = ins.pop('self')
                over = {k: v for k, v in ins.items() if v[0] > SASH_OUT[int(k)]}
                if slf != [4, 0] or over: errs.append('sash inside the body %s (self-test %s)' % ({k: [round(v[0], 3), round(v[1], 3)] for k, v in over.items()}, slf))
                print('  sash inside the body, per button (share, deepest m):', {k: [round(v[0], 3), round(v[1], 3)] for k, v in ins.items()})
            ok = n == 10 and drawn > 200 and not errs
            failed += not ok
            print(('PASS' if ok else 'FAIL') + ' %s %dx%d: %d play buttons, %d drawn pixels of 4096 in the middle%s' % (page, w, h, n, drawn, (', ' + ' | '.join(errs[:3])) if errs else ''))
            if out_dir: await pg.screenshot(path=os.path.join(out_dir, '%s_%dx%d.png' % (os.path.splitext(page)[0], w, h)))
            await ctx.close()
        await b.close()
    print('%d failed (viewer_check)' % failed)
    return failed


if __name__ == '__main__':
    pages = [a[len('--page='):] for a in sys.argv[1:] if a.startswith('--page=')]; rest = [a for a in sys.argv[1:] if not a.startswith('--page=')]
    sys.exit(1 if asyncio.run(main(rest[0] if rest else None, *pages[:1])) else 0)
