#!/usr/bin/env python3
"""The 3D scan of a fighter against Denis's sheets (10/11/2026, Denis: "non puoi scannerizzarlo in 3d così capisci
meglio dove sbagliavi prima su ren?"): for each panel of a sheet (one figure each: a 3-view sheet's right, front and
left, or a single view), the camera that shows the model as the panel shows it, the model drawn from there by its
viewer page (its look: paint, toon light, outline) and the two side by side and over each other, so that every
difference in shape, lines and colours is in sight.

- The model: its bind pose (the drawings' A-pose), with the look's shape (look.move) and its new head if the package's
  folder has one (<name>_head.*, tools/kael_head.py: in place of the triangles it hides).
- The camera: orthographic, the model turned by a yaw about the vertical (+: its face toward the viewer's left, its left
  side seen), its x' = p . (cos t, 0, -sin t) at u = cx + s x', its y at v = by - s y. Yaw, scale and offset: the ones
  where the model seen so overlaps the panel's figure most, the sum of the overlaps (intersection over union) of the
  silhouettes and of each material (skin, hair, dark cloth, purple: the model's from its paint, the drawing's from its
  colours; the face's skin and the hair's mass tell which way the head is turned).
- A part (--part, --rows): the 3-view head sheet draws the head turned and the shoulders not; there only the model's
  head is matched, to the figure's rows down to the chin. Cut (--cut): a bust cut off at the bottom, a torso at both
  ends: the model's rows past the figure's are left out.
- The outputs: OUT_<k>.png per panel (the panel, the whole model from that camera, and the model with the drawing's dark
  lines in red over it) and OUT.json (the cameras and their overlaps).

usage: python3 tools/sheet_scan.py PAGE.html PACKAGE_DIR SHEET.png OUT [--yaw=a:b,...] [--part=y0:y1] [--rows=f0:f1]
                                   [--cut=top,bottom] [--res=N]
  --yaw   one range per panel (degrees, panels from the left), default -75:75 each
  --part  only the model's triangles between these heights (m, bind pose)
  --rows  only the panel figure's rows from f0 to f1 of its height (0 its top, 1 its bottom); --cut=bottom implied
  --res   the render's size, in panel pixels (default 2)"""
import asyncio, base64, io, json, os, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.fft import rfft2, irfft2
WORKERS = os.cpu_count() or 1

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BG_TOL, LINE_LUM = 30, 70
MATS = ('skin', 'hair', 'dark', 'purple')   # (and 'other': in the silhouette only)


def classes(c):
    """Per colour (... x 3): 1 skin, 2 hair (light, low saturation), 3 dark (black, the drawings' dark purple cloth),
    4 purple, 5 other."""
    r, g, b = c[..., 0], c[..., 1], c[..., 2]; mx = c.max(-1); mn = c.min(-1); out = np.full(c.shape[:-1], 5, np.uint8)
    out[(mx < 95) | ((mx < 125) & (mx - mn < 45))] = 3
    out[(b > g + 40) & (b > 100) & (r < b + 30) & (out != 3)] = 4
    out[(r > 150) & (g > 95) & (r - b > 40)] = 1
    out[(mn > 150) & (mx - mn < 70)] = 2
    return out


def model(pkg):
    """The bind pose's positions (with the look's shape), the triangles and each triangle's material (its paint at its
    centre: the look's paint if there is one)."""
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2).astype(np.float64)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    lp = os.path.join(pkg, name + '_look.json')
    if os.path.exists(lp):
        lj = json.load(open(lp)); LB = open(os.path.join(pkg, name + '_look.bin'), 'rb').read()
        if 'move' in lj:
            mv = lj['move']; idx = np.frombuffer(LB, np.uint16, mv['idx'][1], mv['idx'][0]).astype(int)
            P[idx] = np.frombuffer(LB, np.float32, mv['pos'][1], mv['pos'][0]).reshape(-1, 3)
    tp = os.path.join(pkg, name + '_painted.jpg'); tp = tp if os.path.exists(tp) else os.path.join(pkg, name + '.jpg')
    T = np.asarray(Image.open(tp).convert('RGB')).astype(np.float64); ts = T.shape[0]
    uv = UV[I].mean(1); mat = classes(T[np.clip((uv[:, 1] * ts).astype(int), 0, ts - 1), np.clip((uv[:, 0] * ts).astype(int), 0, ts - 1)])
    hp = os.path.join(pkg, name + '_head.json')
    if os.path.exists(hp):   # (the new head in the package's folder, tools/kael_head.py: in place of the triangles it hides, as the viewer draws it)
        hj = json.load(open(hp)); HB = open(os.path.join(pkg, name + '_head.bin'), 'rb').read()
        hf = lambda a, dt=np.float32: np.frombuffer(HB, dt, a[1], a[0])
        HP = hf(hj['pos']).reshape(-1, 3).astype(np.float64); HUV = hf(hj['uv']).reshape(-1, 2).astype(np.float64)
        HI = hf(hj['idx'], np.uint16 if hj['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
        keep = np.ones(len(I), bool); keep[hf(hj['hide'], np.uint32).astype(np.int64)] = False
        HT = np.asarray(Image.open(os.path.join(pkg, name + '_head.jpg')).convert('RGB')).astype(np.float64); hs = HT.shape[0]
        huv = HUV[HI].mean(1); hmat = classes(HT[np.clip((huv[:, 1] * hs).astype(int), 0, hs - 1), np.clip((huv[:, 0] * hs).astype(int), 0, hs - 1)])
        I, mat = np.vstack([I[keep], HI + len(P)]), np.r_[mat[keep], hmat]; P = np.vstack([P, HP])
    return P, I, mat


def panels(D):
    """The sheet's figures: (their labels' image, the background colour, [x0, y0, x1, y1, [labels]] from the left; the
    captions and specks left out: pieces under 2% of the largest)."""
    bg = np.median(np.concatenate([D[:8].reshape(-1, 3), D[-8:].reshape(-1, 3), D[:, :8].reshape(-1, 3), D[:, -8:].reshape(-1, 3)]), 0)
    mask = ndimage.binary_opening(np.abs(D - bg).sum(2) > BG_TOL, iterations=1)
    lab, n = ndimage.label(mask); sz = ndimage.sum(mask, lab, range(1, n + 1)); objs = ndimage.find_objects(lab)
    boxes = sorted([[objs[k][1].start, objs[k][0].start, objs[k][1].stop, objs[k][0].stop, k + 1] for k in range(n) if sz[k] > .02 * sz.max()])
    merged = []   # (pieces of one figure that overlap in x: one panel)
    for b in boxes:
        if merged and b[0] < merged[-1][2] - 10:
            m_ = merged[-1]; m_[:4] = [min(m_[0], b[0]), min(m_[1], b[1]), max(m_[2], b[2]), max(m_[3], b[3])]; m_[4].append(b[4])
        else: merged.append(b[:4] + [[b[4]]])
    return lab, bg, merged


def raster(P, I, mat, yaw, S):
    """The model seen from yaw at S px/m, each pixel its front-most triangle's material (0: none): (image, x' min, y max)."""
    t = np.radians(yaw); x = P @ np.array([np.cos(t), 0, -np.sin(t)]); y = P[:, 1]; z = P @ np.array([np.sin(t), 0, np.cos(t)])
    u = (x - x.min()) * S + 2; v = (y.max() - y) * S + 2
    im = Image.new('L', (int(u.max()) + 4, int(v.max()) + 4), 0); dr = ImageDraw.Draw(im)
    for k in np.argsort(z[I].mean(1)):   # (far to near)
        a, b, c = I[k]; dr.polygon([(u[a], v[a]), (u[b], v[b]), (u[c], v[c])], fill=int(mat[k]))
    return np.asarray(im), x.min() - 2 / S, y.max() + 2 / S


def score(FFs, shape, Ms, rows, PH, PW):
    """The shift (dx, dy) of the model's masks Ms over the panel's (FFs: their transforms padded to PH x PW, shape their
    size; Fsum their areas) with the most summed IoU, the model's rows outside rows (the panel's frame) left out:
    (score, dx, dy, the IoUs there)."""
    (H, W), h, w = shape, Ms[0].shape[0], Ms[0].shape[1]
    dys = np.r_[np.arange(0, H), np.arange(-h + 1, 0)]; dxs = np.r_[np.arange(0, W), np.arange(-w + 1, 0)]
    lo = np.clip(rows[0] - dys, 0, h); hi = np.clip(rows[1] + 1 - dys, 0, h)
    tot = 0; ious = []
    for (FF, Fsum), M in zip(FFs, Ms):
        C = irfft2(FF * np.conj(rfft2(M.astype(np.float32), (PH, PW), workers=WORKERS)), (PH, PW), workers=WORKERS)
        C = np.concatenate([C[:H], C[PH - h + 1:]], 0); C = np.concatenate([C[:, :W], C[:, PW - w + 1:]], 1)
        cum = np.r_[0, np.cumsum(M.sum(1).astype(float))]; nM = cum[hi] - cum[lo]
        iou = C / np.maximum(Fsum + nM[:, None] - C, 1); ious.append(iou); tot = tot + iou
    k = np.unravel_index(np.argmax(tot), tot.shape)
    return float(tot[k]), int(dxs[k[1]]), int(dys[k[0]]), [float(i[k]) for i in ious]


def fit(P, I, mat, Fc, yaw_rng, rows, S_guess):
    """The camera of one panel: (score, yaw, s, cx, by, ious, channel names); a coarse search (6 degrees, scales of 7%,
    a third of the panel's pixels), then a fine one about its best (1 degree, 1%, every pixel). Fc: the panel's class
    image (0 off the figure), only the band of rows it uses (rows: that band's limits in its frame)."""
    chans = [Fc > 0] + [Fc == k + 1 for k in range(len(MATS))]
    use = [0] + [k + 1 for k in range(len(MATS)) if chans[k + 1].sum() > .02 * chans[0].sum()]
    def search(yaws, scales, step, S_r):
        best = None; Fd = [chans[c][::step, ::step] for c in use]; rd = (rows[0] // step, rows[1] // step)
        rs = [raster(P, I, mat, yaw, S_r) for yaw in yaws]
        hm = int(max(r[0].shape[0] for r in rs) * scales.max() / S_r / step) + 3; wm = int(max(r[0].shape[1] for r in rs) * scales.max() / S_r / step) + 3
        PH, PW = Fd[0].shape[0] + hm, Fd[0].shape[1] + wm
        FFs = [(rfft2(F.astype(np.float32), (PH, PW), workers=WORKERS), float(F.sum())) for F in Fd]
        for yaw, (M0, x0, y1) in zip(yaws, rs):
            for s in scales:
                k = s / S_r / step
                M = M0 if abs(k - 1) < 1e-9 else ndimage.zoom(M0, k, order=0)
                if M.shape[0] < 4 or M.shape[1] < 4: continue
                Ms = [(M > 0) if c == 0 else (M == c) for c in use]
                sc, dx, dy, ious = score(FFs, Fd[0].shape, Ms, rd, PH, PW)
                if best is None or sc > best[0]: best = (sc, float(yaw), float(s), step * dx - x0 * s, step * dy + y1 * s, ious)
        return best
    b = search(np.arange(yaw_rng[0], yaw_rng[1] + .1, 6.), S_guess * np.exp(np.linspace(-.6, .6, 18)), 3, 300.)
    b = search(np.arange(b[1] - 3, b[1] + 3.1, 1.), b[2] * np.exp(np.linspace(-.04, .04, 9)), 1, b[2])
    return b + (['silhouette'] + [MATS[c - 1] for c in use[1:]],)


JS = """([yaw, W, H, s, cx, by, bg]) => { const it = VW.it; VW.speed = 0; VW.spin = false;
  const sk = it.mesh.skeleton, Wb = sk.boneInverses.map(m => m.clone().invert());
  it.root.position.set(0, 0, 0); it.root.rotation.y = 0; it.body.scale.set(it.scale, it.scale, it.scale); it.root.updateMatrixWorld(true);
  const MW = it.mesh.matrixWorld.clone();
  sk.bones.forEach((b, i) => { const wi = MW.clone().multiply(Wb[i]); const loc = b.parent.matrixWorld.clone().invert().multiply(wi);
    loc.decompose(b.position, b.quaternion, new THREE.Vector3()); b.updateMatrixWorld(true); });
  it.root.rotation.y = -yaw * Math.PI / 180; it.root.updateMatrixWorld(true);
  const sc = it.scale, c = new THREE.OrthographicCamera((0 - cx) / s * sc, (W - cx) / s * sc, by / s * sc, (by - H) / s * sc, -10, 10);
  c.position.set(0, 0, 5); c.lookAt(0, 0, 0);
  const r = VW.renderer, size = new THREE.Vector2(); r.getSize(size); const old = r.getPixelRatio(); r.setPixelRatio(1); r.setSize(W, H, false);
  r.setClearColor(new THREE.Color(bg[0] / 255, bg[1] / 255, bg[2] / 255), 1); r.render(VW.scene, c); const url = r.domElement.toDataURL('image/png');
  r.setClearColor(0x000000, 0); r.setPixelRatio(old); r.setSize(size.x, size.y, false); return url; }"""
WRAP = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light}body{margin:0;font:14px/1.4 system-ui,sans-serif}[hidden]{display:none!important}</style></head><body>%s</body></html>')


async def render(page, cams):
    """The model drawn by its viewer page in the bind pose from each camera [yaw, W, H, s, cx, by, background]."""
    from playwright.async_api import async_playwright
    async def route(r):
        u = r.request.url
        if 'three.min.js' in u: await r.fulfill(path=os.path.join(ROOT, 'three.min.js'), content_type='application/javascript')
        elif u.startswith('file://'): await r.continue_()
        else: await r.abort()
    d = tempfile.mkdtemp(); f = os.path.join(d, 'v.html'); open(f, 'w').write(WRAP % open(page).read())
    async with async_playwright() as p:
        chrome = next((c for c in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/opt/pw-browsers/chromium') if os.path.isfile(c)), None)
        b = await p.chromium.launch(executable_path=chrome, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'])
        pg = await b.new_page(viewport={'width': 844, 'height': 390}); await pg.route('**/*', route)
        await pg.goto('file://' + f)
        await pg.wait_for_function("document.getElementById('now') && document.getElementById('now').textContent.length > 0", timeout=120000)
        await pg.wait_for_timeout(2500)
        out = []
        for c in cams:
            u = await pg.evaluate(JS, c)
            out.append(Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB'))
        await b.close()
    return out


def main(argv):
    page, pkg, sheet, out = argv[:4]; opts = dict(a[2:].split('=', 1) for a in argv[4:] if a.startswith('--') and '=' in a)
    cut = opts['cut'].split(',') if opts.get('cut') else []; res = float(opts.get('res', 2))
    P, I, mat = model(pkg)
    if 'part' in opts:
        y0, y1 = map(float, opts['part'].split(':')); keep = (P[I][:, :, 1] >= y0).all(1) & (P[I][:, :, 1] <= y1).all(1)
        Ip, matp = I[keep], mat[keep]
    else: Ip, matp = I, mat
    D = np.asarray(Image.open(sheet).convert('RGB')).astype(np.float64)
    lab, bg, boxes = panels(D)
    yaws = [tuple(map(float, r.split(':'))) for r in opts['yaw'].split(',')] if 'yaw' in opts else [(-75., 75.)] * len(boxes)
    cams, info = [], []
    Pp = P[np.unique(Ip)]; H_part = Pp[:, 1].max() - Pp[:, 1].min()
    for k, (x0, y0, x1, y1, ids) in enumerate(boxes):
        mx0, my0, mx1, my1 = max(0, x0 - 30), max(0, y0 - 30), min(D.shape[1], x1 + 30), min(D.shape[0], y1 + 30)
        fig = np.isin(lab[my0:my1, mx0:mx1], ids); Fc = np.where(fig, classes(D[my0:my1, mx0:mx1]), 0)
        fy = np.nonzero(fig.any(1))[0]; top, bot = fy.min(), fy.max(); rcut = cut
        if 'rows' in opts:   # (only that band of the figure; its bottom a cut)
            f0, f1 = map(float, opts['rows'].split(':')); r0, r1 = int(top + f0 * (bot - top)), int(top + f1 * (bot - top))
            Fc[:r0] = 0; Fc[r1 + 1:] = 0; top, bot = r0, r1; rcut = list(set(cut) | {'bottom'} | ({'top'} if f0 > 0 else set()))
        oy = max(0, top - 2) if 'top' in rcut or 'rows' in opts else 0; oe = min(Fc.shape[0], bot + 3) if 'bottom' in rcut else Fc.shape[0]
        rows = (top - oy if 'top' in rcut else -10 ** 6, bot - oy if 'bottom' in rcut else 10 ** 6)
        S_guess = (bot - top) / H_part
        sc, yaw, s, cx, by, ious, names = fit(P, Ip, matp, Fc[oy:oe], yaws[k], rows, S_guess); by += oy
        print('panel %d (%d..%d px): yaw %.0f, %.0f px/m; overlap %s' % (k, x0, x1, yaw, s, ', '.join('%s %.0f%%' % (n_, 100 * i) for n_, i in zip(names, ious))))
        info.append({'box': [mx0, my0, mx1, my1], 'yaw': yaw, 's': s, 'cx': cx + mx0, 'by': by + my0, 'iou': dict(zip(names, ious))})
        W, H = mx1 - mx0, my1 - my0
        cams.append([yaw, int(W * res), int(H * res), s * res, cx * res, by * res, [int(v) for v in bg]])
    ims = asyncio.run(render(page, cams))
    for k, (c, im) in enumerate(zip(info, ims)):
        mx0, my0, mx1, my1 = c['box']; pn = Image.fromarray(D[my0:my1, mx0:mx1].astype(np.uint8)).resize(im.size, Image.LANCZOS)
        A = np.asarray(pn).astype(float); R = np.asarray(im).astype(float)
        fig = np.asarray(Image.fromarray(np.isin(lab[my0:my1, mx0:mx1], boxes[k][4]).astype(np.uint8) * 255).resize(im.size, Image.NEAREST)) > 0
        ov = R * .75 + 255 * .25; ov[(A.mean(2) < LINE_LUM) & fig] = (230, 20, 20)
        o = Image.new('RGB', (im.size[0] * 3, im.size[1]), 'white'); o.paste(pn, (0, 0)); o.paste(im, (im.size[0], 0)); o.paste(Image.fromarray(ov.astype(np.uint8)), (2 * im.size[0], 0))
        o.save('%s_%d.png' % (out, k))
    json.dump(info, open(out + '.json', 'w'), indent=1)


if __name__ == '__main__':
    if len(sys.argv) < 5: sys.exit(__doc__)
    main(sys.argv[1:])
