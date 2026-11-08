#!/usr/bin/env python3
"""Paints Ren's new head (the Meshy bust, tools/ren_head.py) from Denis's 3-view sheet (8/11/2026).

usage: python3 tools/paint_head.py BUST.glb SHEET.png OUT.jpg [DEBUG_DIR]
  BUST.glb  the decimated bust (its UVs and Meshy's texture)
  SHEET.png docs/ref/personaggi/ren_testa_3viste.png: three panels side by side (DESTRA, FRONTE, SINISTRA), labels under
  writes OUT.jpg: the bust's texture, each texel from the sheet's views where it is seen

Each panel is a view of the bust: an orthographic camera turned by a yaw around the vertical (VIEWS: the yaw's search
range), its scale and offset; all four fit by the most overlap of the bust's silhouette with the panel's drawing. A
texel takes the colour of the views that see it (the bust's front-most surface there), each weighted by how much it
faces that view (VIEW_POW: sharper toward the best one; turned away less than VIEW_MIN, none: the drawing's contour
lines stretched over a surface seen edge-on); where no view sees it (the back of the head, under the hair, under the
collar) the colour of the nearest texel in space that one sees, of the same part (hair, skin or cloth in Meshy's
texture). The sheet's background never: a texel landing on it takes the nearest drawn pixel.
"""
import io, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

VIEWS = {'destra': (-60., -15.), 'fronte': (-6., 6.), 'sinistra': (15., 60.)}   # yaw search ranges (degrees)
PANEL_H = 815                                # the panels' drawing height (the labels under it left out)
VIEW_POW, VIEW_MIN = 4., .15


def load_bust(path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from meshy_pack import read_glb, acc, world_mats
    j, BIN = read_glb(path); G, _ = world_mats(j)
    ni = next(i for i, nd in enumerate(j['nodes']) if 'mesh' in nd); M = G[ni]
    pr = j['meshes'][j['nodes'][ni]['mesh']]['primitives'][0]; at = pr['attributes']
    P = acc(j, BIN, at['POSITION']).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    UV = acc(j, BIN, at['TEXCOORD_0']).astype(np.float64); I = acc(j, BIN, pr['indices']).reshape(-1, 3).astype(np.int64)
    img = j['images'][0]; bv = j['bufferViews'][img['bufferView']]
    tex = Image.open(io.BytesIO(BIN[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']])).convert('RGB')
    return P, UV, I, tex


def rot(yaw):
    a = np.radians(yaw); c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def raster_ids(X, Y, Z, I, W, H):
    """Front-most triangle id (-1 none) and depth per pixel for the projected vertices (X, Y pixels, Z depth: larger nearer)."""
    Zb = np.full((H, W), -np.inf); T = np.full((H, W), -1, np.int64)
    A, B_ = X[I], Y[I]
    for k in range(len(I)):
        x, y = A[k], B_[k]
        lx, hx = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), W - 1)); ly, hy = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), H - 1))
        if hx < lx or hy < ly: continue
        dd = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(dd) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(lx, hx + 1) + .5, np.arange(ly, hy + 1) + .5)
        u = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / dd; v = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / dd; w = 1 - u - v
        ins = (u >= -1e-3) & (v >= -1e-3) & (w >= -1e-3); zz = u * Z[I[k, 0]] + v * Z[I[k, 1]] + w * Z[I[k, 2]]
        iy, ix = (gy - .5).astype(int), (gx - .5).astype(int); up = ins & (zz > Zb[iy, ix])
        Zb[iy[up], ix[up]] = zz[up]; T[iy[up], ix[up]] = k
    return T, Zb


def silhouette(P, I, yaw, k, ox, oy, W, H, step=4):
    """The bust's silhouette at a quarter of the panel's resolution (for the fit)."""
    Q = P @ rot(yaw).T; X = (ox + k * Q[:, 0]) / step; Y = (oy - k * Q[:, 1]) / step
    from PIL import ImageDraw
    im = Image.new('L', (W // step, H // step), 0); d = ImageDraw.Draw(im)
    for t in I: d.polygon([(X[a], Y[a]) for a in t], fill=255)
    return np.asarray(im) > 0


def fit_view(P, I, mask, yr):
    """Yaw, scale, offset of the camera that best overlaps the bust's silhouette with the drawn mask."""
    H, W = mask.shape; step = 4; ms = mask[::step, ::step][:H // step, :W // step]
    ys, xs = np.nonzero(mask); top, cxm = ys.min(), (xs.min() + xs.max()) / 2
    best = None
    def iou(p):
        sil = silhouette(P, I, *p, W, H, step); a = sil[:ms.shape[0], :ms.shape[1]]
        inter = (a & ms).sum(); return inter / max((a | ms).sum(), 1)
    for yaw in np.arange(yr[0], yr[1] + 1e-9, 5.):
        Q = P @ rot(yaw).T
        k0 = (H - top) / (Q[:, 1].max() - Q[:, 1].min()) * 1.0   # (first guess: the bust's height on the panel's)
        for ks in (.85, .95, 1.05, 1.15):
            k = k0 * ks; ox = cxm - k * (Q[:, 0].max() + Q[:, 0].min()) / 2; oy = top + k * Q[:, 1].max()
            p = (yaw, k, ox, oy); v = iou(p)
            if best is None or v > best[0]: best = (v, p)
    v, p = best; p = list(p); stepz = [2.5, .03 * p[1], 6., 6.]
    for it in range(40):   # coordinate descent
        improved = False
        for i in range(4):
            for sgn in (1, -1):
                q = list(p); q[i] += sgn * stepz[i]
                vq = iou(q)
                if vq > v: v, p, improved = vq, q, True
        if not improved:
            stepz = [s * .5 for s in stepz]
            if stepz[0] < .2: break
    return v, p


def main(bust, sheet, out, dbg=None):
    P, UV, I, tex0 = load_bust(bust)
    S = np.asarray(Image.open(sheet).convert('RGB')).astype(np.float64)
    bg = S[5:30, 5:30].reshape(-1, 3).mean(0); Wp = S.shape[1] // 3
    panels = {}
    for k, name in enumerate(('destra', 'fronte', 'sinistra')):
        img = S[:PANEL_H, k * Wp:(k + 1) * Wp]; mask = ndimage.binary_opening(np.abs(img - bg).sum(2) > 40, iterations=2)
        mask = ndimage.binary_fill_holes(mask)
        v, p = fit_view(P, I, mask, VIEWS[name])
        _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
        panels[name] = {'img': img, 'fill': img[iy, ix], 'mask': mask, 'p': p}
        print('%s: yaw %.1f, scale %.1f px per unit, offset (%.1f, %.1f); silhouette overlap %.3f' % (name, p[0], p[1], p[2], p[3], v))
    # texels: their triangle, barycentrics, position, normal (UV raster)
    T0 = np.asarray(tex0).astype(np.float64); TS = T0.shape[0]
    from PIL import ImageDraw
    uvimg = Image.new('RGB', (TS, TS), (0, 0, 0)); dr = ImageDraw.Draw(uvimg)
    for k, t in enumerate(I):
        c = k + 1; dr.polygon([(UV[q, 0] * TS, UV[q, 1] * TS) for q in t], fill=(c & 255, (c >> 8) & 255, (c >> 16) & 255))
    ua = np.asarray(uvimg).astype(np.int64); tid = ua[..., 0] + (ua[..., 1] << 8) + (ua[..., 2] << 16) - 1
    ys, xs = np.nonzero(tid >= 0); ks = tid[ys, xs]
    A = UV[I[ks, 0]] * TS; Bv = UV[I[ks, 1]] * TS; C = UV[I[ks, 2]] * TS; px = np.stack([xs + .5, ys + .5], 1)
    v0 = Bv - A; v1 = C - A; v2 = px - A
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01; den[np.abs(den) < 1e-12] = 1e-12
    bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
    bary = np.clip(np.stack([bu, bv, bw], 1), 0, 1); bary /= bary.sum(1, keepdims=True)
    pos = (P[I[ks]] * bary[..., None]).sum(1)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    nor = fn[ks]
    acc_c = np.zeros((len(ks), 3)); acc_w = np.zeros(len(ks))
    for name, pn in panels.items():
        yaw, k, ox, oy = pn['p']; R = rot(yaw); Q = P @ R.T; H, W = pn['mask'].shape
        X = ox + k * Q[:, 0]; Y = oy - k * Q[:, 1]
        Tv, _ = raster_ids(X, Y, Q[:, 2], I, W, H)
        q = pos @ R.T; tx = ox + k * q[:, 0]; ty = oy - k * q[:, 1]
        ix = np.clip(tx.astype(int), 0, W - 1); iy = np.clip(ty.astype(int), 0, H - 1)
        seen = Tv[iy, ix]; vis = seen == ks
        # neighbours of the texel's triangle count as seen too (a raster's pixel holds one triangle)
        ok = vis | (seen < 0)
        facing = (nor @ R.T)[:, 2]
        w = np.where(vis, np.clip((facing - VIEW_MIN) / (1 - VIEW_MIN), 0, 1) ** VIEW_POW, 0.)
        col = pn['fill'][iy, ix]
        acc_c += col * w[:, None]; acc_w += w
        print('%s: texels seen %d, weighted %d' % (name, int(vis.sum()), int((w > .05).sum())))
    painted = acc_w > 1e-4
    out_c = np.zeros((len(ks), 3)); out_c[painted] = acc_c[painted] / acc_w[painted, None]
    # the rest: the nearest painted texel in space of the same part
    c0 = T0[ys, xs]; lum = c0.mean(1)
    part = np.where((c0[:, 1] > c0[:, 0] + 8) & (c0[:, 2] > c0[:, 0] + 8), 2, np.where((c0[:, 0] > 120) & (c0[:, 0] - c0[:, 2] > 40) & (c0[:, 0] - c0[:, 1] > 30), 1, 0))
    from scipy.spatial import cKDTree
    for pt in (0, 1, 2):
        src = painted & (part == pt); dst = ~painted & (part == pt)
        if src.any() and dst.any():
            _, nn = cKDTree(pos[src]).query(pos[dst]); out_c[dst] = out_c[np.nonzero(src)[0][nn]]
        elif dst.any(): out_c[dst] = c0[dst]
    res = T0.copy(); res[ys, xs] = out_c
    # the gaps between the UV pieces: their nearest piece's colour
    have = np.zeros((TS, TS), bool); have[ys, xs] = True
    _, (gy, gx) = ndimage.distance_transform_edt(~have, return_indices=True); res = res[gy, gx]
    Image.fromarray(np.clip(res, 0, 255).astype(np.uint8)).save(out, quality=90, optimize=True)
    print('painted %d of %d texels from the views (%d filled from their nearest), %s' % (int(painted.sum()), len(ks), int((~painted).sum()), out))
    if dbg:
        os.makedirs(dbg, exist_ok=True)
        json.dump({n: pn['p'] for n, pn in panels.items()}, open(os.path.join(dbg, 'views.json'), 'w'))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
