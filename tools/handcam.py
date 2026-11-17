#!/usr/bin/env python3
"""Kael's hands and wrists beside Ren's (17/11/2026, Denis: "a me non piacciono soprattutto le mani", "ora il polso";
docs/superpowers/specs/2026-11-17-kael-mani-polso-design.md): the same close-ups of both characters' viewer pages, from
the same 8 sides, and how far apart their skin's colour is.

- Poses: 'pugno' (the guard's fist: button 0, 40 game frames), 'aperta' (the open hand: every skinned mesh in its rest
  pose), 'polso_guardia' (the wrist in the guard), 'polso_pugno' (the wrist mid-punch: button 2, 7 frames).
- Camera: 30 degrees, from 8 sides 45 degrees apart (pitch .2 rad), looking at the hand (from its wrist bone 70% of the
  way to its middle finger's first joint) or at the wrist bone; the stage hidden, a neutral grey behind.
- Skin: the pixels whose colour is skin-like (CIE Lab: hue 20-75 degrees, chroma 12-50, lightness over 30); per sheet the
  CIE76 difference of Kael's mean skin colour and Ren's.
- Out: OUT/<pose>_<Left|Right>.png (8 views; Kael above, Ren below) and one line per sheet:
  '<pose>_<side> skin dE 12.3 (kael L 61 a 18 b 30, ren L 74 a 16 b 27)'.

usage: python3 tools/handcam.py OUT [--page=viewer_kael.html] [--ref=viewer.html]"""
import asyncio, io, os, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
from viewer_check import WRAP, ARGS, CHROME, route, ROOT
from playwright.async_api import async_playwright

SIZE, THUMB = 600, 300
POSES = (('pugno', 'hand', .45), ('polso_guardia', 'wrist', .42), ('polso_pugno', 'wrist', .42), ('aperta', 'hand', .5))
YAWS = [k * np.pi / 4 for k in range(8)]
PITCH = .2

SHOT = """async ([side, aim, dist, yaw, pitch]) => {
  const it = VW.it, c = VW.camera, bone = n => { let b = null; it.root.traverse(o => { if (o.isBone && o.name === n) b = o; }); return b; };
  it.root.updateMatrixWorld(true);
  const m = bone(side + 'Hand').getWorldPosition(new THREE.Vector3());
  if (aim === 'hand') m.lerp(bone(side + 'HandMiddle1').getWorldPosition(new THREE.Vector3()), .7);
  c.position.set(m.x + dist * Math.sin(yaw) * Math.cos(pitch), m.y + dist * Math.sin(pitch), m.z + dist * Math.cos(yaw) * Math.cos(pitch));
  c.lookAt(m); c.clearViewOffset(); c.fov = 30; c.aspect = 1; c.updateProjectionMatrix();
  VW.renderer.render(VW.scene, c); }"""


async def shots(b, page):
    """{(pose, side): [8 RGB arrays]} of the page's character"""
    pf = os.path.join(tempfile.mkdtemp(), page)
    open(pf, 'w', encoding='utf-8').write(WRAP % open(os.path.join(ROOT, page), encoding='utf-8').read())
    ctx = await b.new_context(viewport={'width': SIZE, 'height': SIZE}); pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.route('**/*', route); await pg.goto('file://' + pf)
    await pg.wait_for_function("document.getElementById('now') && document.getElementById('now').textContent.length > 0", timeout=60000)
    await pg.wait_for_timeout(500)   # (the textures decoded)
    await pg.evaluate("""() => { window.requestAnimationFrame = () => 0; VW.speed = 0; VW.spin = false;
      for (const id of ['top', 'bottom']) document.getElementById(id).style.display = 'none';   /* (the canvas is in #stage: opaque grey below) */
      VW.renderer.setClearColor(0x808080, 1); VW.renderer.setSize(innerWidth, innerHeight, false);
      VW.it.root.position.set(0, 0, 0); VW.it.root.rotation.y = 0; }""")
    out = {}
    for pose, aim, dist in POSES:
        if pose == 'aperta': await pg.evaluate("VW.it.root.traverse(o => { if (o.isSkinnedMesh) o.skeleton.pose(); })")
        else: await pg.evaluate("([b, n]) => { document.getElementById('play' + b).click(); VW.tick(n); }", [2, 7] if pose == 'polso_pugno' else [0, 40])
        for side in ('Left', 'Right'):
            ims = []
            await pg.evaluate(SHOT, [side, aim, dist, YAWS[0], PITCH]); await pg.screenshot()   # (once unseen: the first shot after a pose showed the frame before it)
            for yaw in YAWS:
                await pg.evaluate(SHOT, [side, aim, dist, yaw, PITCH])
                ims.append(np.asarray(Image.open(io.BytesIO(await pg.screenshot())).convert('RGB')))
            out[pose, side] = ims
    await ctx.close()
    if errs: sys.exit('%s: %s' % (page, errs))
    return out


def lab(rgb):
    c = rgb.reshape(-1, 3) / 255.
    c = np.where(c > .04045, ((c + .055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[.4124, .3576, .1805], [.2126, .7152, .0722], [.0193, .1192, .9505]]).T / [.95047, 1., 1.08883]
    f = np.where(xyz > .008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.c_[116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])]


def skin(ims):
    """the mean Lab colour of the skin-like pixels of the images, and their count"""
    L = lab(np.concatenate([i.reshape(-1, 3) for i in ims]))
    h = np.degrees(np.arctan2(L[:, 2], L[:, 1])); ch = np.hypot(L[:, 1], L[:, 2])
    m = (h > 20) & (h < 75) & (ch > 12) & (ch < 50) & (L[:, 0] > 30)
    return (L[m].mean(0) if m.any() else np.full(3, np.nan)), int(m.sum())


async def main(out, page, ref):
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=ARGS)
        K = await shots(b, page); R = await shots(b, ref)
        await b.close()
    for key in K:
        sheet = Image.new('RGB', (THUMB * len(YAWS), 2 * THUMB + 10), (255, 255, 255))
        for row, S in enumerate((K, R)):
            for i, im in enumerate(S[key]): sheet.paste(Image.fromarray(im).resize((THUMB, THUMB), Image.LANCZOS), (THUMB * i, row * (THUMB + 10)))
        name = '%s_%s' % key; sheet.save(os.path.join(out, name + '.png'))
        (k, nk), (r, nr) = skin(K[key]), skin(R[key])
        print('%s skin dE %.1f (kael L %.0f a %.0f b %.0f, %d px; ren L %.0f a %.0f b %.0f, %d px)' % (name, np.linalg.norm(k - r), *k, nk, *r, nr))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    if len(args) != 1: sys.exit(__doc__)
    asyncio.run(main(args[0], opt.get('page', 'viewer_kael.html'), opt.get('ref', 'viewer.html')))
