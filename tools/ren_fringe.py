#!/usr/bin/env python3
"""Ren's face locks drawn from his sheet (8/11/2026, Denis: "i capelli sulla faccia" still badly made, "quelli sopra
sono perfetti"; then "è fatto meglio ma non abbastanza"): called by tools/ren_head.py, on the head it builds.

Meshy's fringe over the forehead is a mass of soft locks: from the front their shapes are not the sheet's, and their
outline (pushed back to stop it splintering between them and the skin, fringe_back in ren_head.py) is gone. Here:
  - the sheet's front view (docs/ref/personaggi/ren_testa_3viste.png, its middle panel) is registered on the head seen
    from the front (orthographic): its eyes, nose and mouth matched to the head's by normalized cross-correlation
    (register: scale and offset);
  - Meshy's fringe under the hairline (an arc, HAIRLINE) over the face's front (FRONT_NZ; between two of the sheet's
    lines near SIDE_X each side, so the temples' locks stay Meshy's: from the side they cover the eyes' corners) is
    removed, the eyes kept;
  - the forehead under it is painted from the sheet (its skin and its shadows; under the sheet's hair, skin);
  - the sheet's locks there (its hair over the face: its purple and the black lines along it, not the brows nor the
    eyes) become one mesh: a pillow (LOCK_TH thick at most, thinner at the edges: from the side a solid lock, its edge
    the sheet's line) hanging from the crown's front edge (tucked TUCK behind it) down to GAP in front of the face at the
    brows (BROW_Y) and below, its texture the sheet's front view, its alpha the locks' shape.
Writes OUT_DIR/<name>_fringe.json, .bin, .png ({v, verts, tris, pos, uv: float32, idx: uint16/32; each [byte offset,
count]}; all on the Head bone, e_model.js mdFringeData); returns the head's triangles kept and paints the forehead in
its texture (in place).
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, signal

SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'ref', 'personaggi', 'ren_testa_3viste.png')
SHEET_FRONT = (591, 0, 1183, 887)        # the sheet's front view (px box)
PX, X0, X1, Y0, Y1 = .00025, -.12, .12, 1.45, 1.70   # the front frame: m per px, its window (m)
REG = ((-.05, .05), (1.535, 1.607), np.arange(2.0, 2.5, .02))   # register: the template (x, y m: eyes to mouth), the scales tried
FRONT_NZ = .6                             # the face's front: its normal's z at least (from its smoothed depth)
SIDE_X, SIDE_W = .045, .008               # the sides' limits: the sheet's darkest line within SIDE_W of SIDE_X (m from the middle)
BODY_X = .006                             # the face's middle (x)
HAIRLINE = (1.650, 8.3, 1.60)             # the arc y = a - b x^2 (m), at least c: above it Meshy's crown stays
DROP_DZ, DROP_Y = .0015, 1.57             # Meshy's fringe: in front of the face by more than that, above that
GAP, TUCK, BROW_Y, HANG = .0025, .0015, 1.598, 1.6   # the locks' depth (see above); HANG: their curve's power
LOCK_TH, LOCK_EDGE, LOCK_BACK, GRID = .0018, .0015, .4, 8   # the pillow: thickness, its ramp from the edge (m), its back's share; mesh grid (px)
CUT_MIN = 2500                            # pieces of the locks the sides' limits cut off, smaller than that (px): left out


def texels(uv, A, TS):
    """A triangle's texels (n x 2: col, row) and their 3D points. uv: its corners in texels; A: its corners (3 x 3)."""
    lo = np.floor(uv.min(0)).astype(int); hi = np.ceil(uv.max(0)).astype(int)
    xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1)); px = np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)
    T = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T
    if abs(np.linalg.det(T)) < 1e-9: return np.zeros((0, 2), int), np.zeros((0, 3))
    b = np.linalg.solve(T, (px - uv[0]).T).T; w = np.c_[1 - b.sum(1), b]; ins = (w >= -1e-3).all(1)
    q = np.floor(px[ins]).astype(int); g = (q >= 0).all(1) & (q < TS).all(1)
    return q[g], (w[ins] @ A)[g]


def front_view(P, UV, I, tex, N):
    """Orthographic front view of the triangles I (looking down -z): rgb, depth (z, -inf where empty), normal z, the
    triangle seen (index into I, -1 where empty)."""
    W = int(round((X1 - X0) / PX)); H = int(round((Y1 - Y0) / PX)); TS = tex.shape[0]
    rgb = np.zeros((H, W, 3), np.uint8); zb = np.full((H, W), -np.inf); nzb = np.zeros((H, W)); tb = np.full((H, W), -1, np.int64)
    A = P[I]; X = (A[:, :, 0] - X0) / PX; Y = (Y1 - A[:, :, 1]) / PX
    for k in range(len(I)):
        xs, ys = X[k], Y[k]; lx, hx = int(np.floor(xs.min())), int(np.ceil(xs.max())); ly, hy = int(np.floor(ys.min())), int(np.ceil(ys.max()))
        if hx < 0 or hy < 0 or lx >= W or ly >= H: continue
        lx, ly, hx, hy = max(lx, 0), max(ly, 0), min(hx, W - 1), min(hy, H - 1)
        gx, gy = np.meshgrid(np.arange(lx, hx + 1) + .5, np.arange(ly, hy + 1) + .5)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12: continue
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        w2 = 1 - w0 - w1; m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any(): continue
        z = w0 * A[k, 0, 2] + w1 * A[k, 1, 2] + w2 * A[k, 2, 2]
        iy, ix, zz = gy[m].astype(int), gx[m].astype(int), z[m]; near = zz > zb[iy, ix]
        if not near.any(): continue
        iy, ix, zz = iy[near], ix[near], zz[near]; ww = np.stack([w0[m][near], w1[m][near], w2[m][near]], 1)
        uv = ww @ UV[I[k]]; tu = np.clip((uv[:, 0] * TS).astype(int), 0, TS - 1); tv = np.clip((uv[:, 1] * TS).astype(int), 0, TS - 1)
        zb[iy, ix] = zz; rgb[iy, ix] = tex[tv, tu]; tb[iy, ix] = k; nzb[iy, ix] = ww @ N[I[k], 2]
    return rgb, zb, nzb, tb


def register(head_rgb, sheet):
    """The sheet's front view on the head's front view: (m per sheet px, sheet column at X0, sheet row at Y1), from the
    best match of the head's eyes-to-mouth (darkness, normalized cross-correlation) over the scales REG[2]."""
    (xa, xb), (ya, yb), scales = REG
    img = 255 - np.asarray(Image.fromarray(sheet).convert('L')).astype(float); g = Image.fromarray(head_rgb).convert('L'); best = None
    for k in scales:
        m = np.asarray(g.resize((int(round(g.width / k)), int(round(g.height / k))), Image.LANCZOS)).astype(float)
        r0, r1 = int((Y1 - yb) / PX / k), int((Y1 - ya) / PX / k); c0, c1 = int((xa - X0) / PX / k), int((xb - X0) / PX / k)
        t = 255 - m[r0:r1, c0:c1]; t = t - t.mean(); n = t.size; ones = np.ones_like(t)
        c = signal.fftconvolve(img, t[::-1, ::-1], mode='valid'); s1 = signal.fftconvolve(img, ones, mode='valid'); s2 = signal.fftconvolve(img ** 2, ones, mode='valid')
        ncc = c / (np.sqrt((t ** 2).sum()) * np.sqrt(np.maximum(s2 - s1 ** 2 / n, 1e-9))); j = np.unravel_index(np.argmax(ncc), ncc.shape)
        if best is None or ncc[j] > best[0]: best = (float(ncc[j]), k, j[1] - c0, j[0] - r0)
    return best


def fringe(Q, N, UV, I, tex, name, out):
    """See above. Q, N, UV, I: the head (its vertices, normals, uvs, triangles); tex: its texture (h x w x 3, float or
    uint8; the forehead painted in place). Returns the triangles kept."""
    P = Q.astype(float); UV = UV.astype(float); I = np.asarray(I).astype(np.int64); TS = tex.shape[0]
    t8 = np.clip(tex, 0, 255).astype(np.uint8)
    c = t8[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)].astype(int)
    skinv = (c[:, 0] > 140) & (c[:, 0] - c[:, 2] > 55); skin_t = skinv[I].all(1)
    mc = c.mean(1); hairv = (mc >= 38) & (mc < 110) & (c[:, 0] >= c[:, 1] + 4) & (c[:, 2] >= c[:, 1] + 2) & (c[:, 0] - c[:, 2] < 25)   # (the purple hair; not the black lashes and lines)
    # the sheet on the head's front
    sheet = np.asarray(Image.open(SHEET).convert('RGB').crop(SHEET_FRONT))
    rgb_all, _, _, _ = front_view(P, UV, I, t8, N)
    score, k, U0, V0 = register(rgb_all, sheet); K = PX * k
    print('fringe: the sheet on the head\'s front: %.3f mm per px of the sheet, match %.2f' % (1000 * K, score))
    # the face from the front: its skin's depth (filled, smoothed), its front (the normal from that depth), the region
    _, z_s, _, _ = front_view(P, UV, I[skin_t], t8, N)
    H, W = z_s.shape; ii, jj = np.mgrid[0:H, 0:W]; X = X0 + (jj + .5) * PX; Y = Y1 - (ii + .5) * PX
    face = np.isfinite(z_s) & (Y > 1.52)
    _, (gy, gx) = ndimage.distance_transform_edt(~face, return_indices=True); zfill = z_s[gy, gx]; zsm = ndimage.gaussian_filter(zfill, 6)
    zone = ndimage.binary_fill_holes(ndimage.binary_closing(face, iterations=6)) & (Y > 1.52)
    for i in range(H):   # (row by row from its left edge to its right: the eyes and the brows are not skin)
        js = np.nonzero(face[i])[0]
        if len(js) > 1 and Y[i, 0] > 1.52: zone[i, js.min():js.max() + 1] = True
    dzy, dzx = np.gradient(ndimage.gaussian_filter(zfill, 10), PX); front = zone & (1 / np.sqrt(1 + dzx ** 2 + dzy ** 2) > FRONT_NZ)
    cols = front.any(0); D = front.copy(); topc = np.where(cols, front.argmax(0), H)
    for j in np.nonzero(cols)[0]: D[max(topc[j] - int(.03 / PX), 0):topc[j], j] = True
    D = ndimage.binary_closing(D, iterations=3)
    # the sheet over the frame, its colours' classes
    u = (X - X0) / K + U0 - .5; v = (Y1 - Y) / K + V0 - .5; fs = sheet.astype(float)
    w = np.stack([ndimage.map_coordinates(fs[..., m], [v, u], order=3, cval=0) for m in range(3)], 2).clip(0, 255)
    wi = w.astype(int); r, g, b = wi[..., 0], wi[..., 1], wi[..., 2]; lum = w.mean(2); sat = w.max(2) - w.min(2)
    skin_s = (r > 140) & (r - b > 55); black_s = lum < 50; brown_s = (r > 60) & (r - b > 25) & ~skin_s
    white_s = (w.min(2) > 185) & (sat < 35)
    purple_s = (lum >= 38) & (lum < 175) & ~skin_s & ~brown_s & (b >= g - 4) & (r >= g - 4) & (sat < 60)
    # the sides' limits: the sheet's darkest column near SIDE_X each side, per row, smoothed
    def side(x):
        j0, j1 = int((x - SIDE_W - X0) / PX), int((x + SIDE_W - X0) / PX)
        jm = j0 + np.argmin(ndimage.gaussian_filter(lum, 1.)[:, j0:j1], 1)
        return ndimage.gaussian_filter1d(ndimage.median_filter(jm.astype(float), 15), 3)
    bl, br = side(BODY_X - SIDE_X), side(BODY_X + SIDE_X); inside = (jj > bl[:, None]) & (jj < br[:, None])
    front &= inside; D &= inside
    # Meshy's fringe under the hairline, over the region, in front of the face (the eyes kept)
    jx = np.arange(W); ycut = np.maximum(HAIRLINE[0] - HAIRLINE[1] * (X0 + (jx + .5) * PX) ** 2, HAIRLINE[2])
    C = P[I].mean(1); cj = ((C[:, 0] - X0) / PX).astype(int); ci = ((Y1 - C[:, 1]) / PX).astype(int)
    ok = (ci >= 0) & (ci < H) & (cj >= 0) & (cj < W); Dd = ndimage.binary_dilation(D, iterations=8)
    over = np.zeros(len(I), bool); over[ok] = Dd[ci[ok], cj[ok]]
    dz = np.full(len(I), -9.); dz[ok] = C[ok, 2] - zsm[ci[ok], cj[ok]]; ye = np.zeros(len(I)); ye[ok] = ycut[cj[ok]]
    drop = over & (C[:, 1] < ye) & (C[:, 1] > DROP_Y) & (dz > DROP_DZ) & ((hairv[I].sum(1) >= 2) | ((dz > .004) & ~skinv[I].all(1) & (C[:, 1] > BROW_Y + .006)))
    keep = ~drop
    rgb_r, z_r, _, t_r = front_view(P, UV, I[keep], t8, N)
    # the crown's front just above the hairline: the locks' roots tuck behind it
    zedge = np.full(W, np.nan)
    for j in np.nonzero(cols)[0]:
        i0 = int((Y1 - ycut[j]) / PX) - int(.002 / PX); seg = z_r[max(i0 - 12, 0):i0 + 1, j]; seg = seg[np.isfinite(seg)]
        if len(seg): zedge[j] = seg.max()
    okz = np.isfinite(zedge); zedge = ndimage.gaussian_filter1d(np.interp(jx, jx[okz], zedge[okz]), 8)
    # the sheet's brows (its thick black in their band, the two biggest)
    band = (Y > 1.594) & (Y < 1.62) & (np.abs(X) < .07)
    thick = ndimage.binary_opening(black_s & band, iterations=3); lab, n = ndimage.label(thick)
    brows = np.isin(lab, np.argsort(-ndimage.sum(thick, lab, range(1, n + 1)))[:2] + 1); brows = ndimage.binary_dilation(brows, iterations=2) & black_s
    browtop = np.array([np.nonzero(brows[:, j])[0].min() if brows[:, j].any() else int((Y1 - BROW_Y) / PX) for j in range(W)])
    # the locks: above the brows all that is not skin, its shadow or white; below them, the purple and the lines along
    # it (within .8 mm); not the eyes (the lids and their grey shading); the pieces the sides' limits cut off left out
    above = (ii < browtop[None, :]) & (Y > BROW_Y - .004)
    near_p = ndimage.distance_transform_edt(~purple_s) * PX <= .0008
    L = ((above & ~skin_s & ~brown_s & ~white_s & ~brows) | purple_s | (black_s & near_p & ~brows)) & D & (Y <= ycut[None, :] + .004) & (Y >= 1.565)
    L = ndimage.binary_closing(ndimage.binary_opening(L, iterations=1), iterations=1)
    eyes = ndimage.binary_fill_holes(ndimage.binary_dilation(white_s & (Y > 1.582) & (Y < 1.604), iterations=6))
    L &= ~(eyes & ~purple_s) & ~ndimage.binary_dilation(white_s, iterations=1)
    lab, n = ndimage.label(L); sz = ndimage.sum(L, lab, range(1, n + 1))
    touch = ndimage.sum(((np.abs(jj - bl[:, None]) < 3) | (np.abs(jj - br[:, None]) < 3)) & L, lab, range(1, n + 1)) > 0
    L = np.isin(lab, np.nonzero((sz >= 80) & ~(touch & (sz < CUT_MIN)))[0] + 1)
    # their depth: from the crown's edge (TUCK behind it) down to GAP in front of the face at the brows (and below;
    # where the hairline comes down to the brows, at the sides, close to the face all along)
    tt = np.where(ycut[None, :] > BROW_Y + .008, np.clip((Y - BROW_Y) / np.maximum(ycut[None, :] - BROW_Y, 1e-4), 0, 1), 0.)
    zl = zsm + GAP + (np.maximum((zedge - TUCK)[None, :] - zsm, GAP) - GAP) * tt ** HANG
    # the mesh: a grid over the locks (widened), front and back (the pillow), the texture's box
    area = ndimage.binary_dilation(L, iterations=6); rows, cl = np.nonzero(area)
    gi = np.arange(rows.min() - rows.min() % GRID, rows.max() + 1 + GRID, GRID); gj = np.arange(cl.min() - cl.min() % GRID, cl.max() + 1 + GRID, GRID)
    GI, GJ = np.meshgrid(gi, gj, indexing='ij'); ins = area[np.clip(GI, 0, H - 1), np.clip(GJ, 0, W - 1)]
    vid = -np.ones(GI.shape, int); quads = []; nv = 0
    for a_ in range(GI.shape[0] - 1):
        for b_ in range(GI.shape[1] - 1):
            q = [(a_, b_), (a_ + 1, b_), (a_ + 1, b_ + 1), (a_, b_ + 1)]
            if not any(ins[p] for p in q): continue
            for p in q:
                if vid[p] < 0: vid[p] = nv; nv += 1
            A_, B_, C_, D_ = [vid[p] for p in q]; quads += [(A_, B_, C_), (A_, C_, D_)]
    hh = LOCK_TH * np.sqrt(np.clip(ndimage.distance_transform_edt(L) * PX / LOCK_EDGE, 0, 1))
    tr0, tc0, TH, TW = gi[0], gj[0], gi[-1] - gi[0] + 1, gj[-1] - gj[0] + 1
    pos = np.zeros((2 * nv, 3)); uvs = np.zeros((2 * nv, 2))
    for (p, q), kk in np.ndenumerate(vid):
        if kk < 0: continue
        i_, j_ = min(max(GI[p, q], 0), H - 1), min(max(GJ[p, q], 0), W - 1); x, y = X0 + (GJ[p, q] + .5) * PX, Y1 - (GI[p, q] + .5) * PX
        pos[kk] = (x, y, zl[i_, j_] + hh[i_, j_]); pos[nv + kk] = (x, y, zl[i_, j_] - LOCK_BACK * hh[i_, j_])
        uvs[kk] = uvs[nv + kk] = ((GJ[p, q] - tc0 + .5) / TW, (GI[p, q] - tr0 + .5) / TH)
    quads = np.array(quads, np.int64); idx = np.concatenate([quads, quads[:, ::-1] + nv]); nv *= 2
    pad = lambda arr: np.pad(arr, ((0, max(0, tr0 + TH - H)), (0, max(0, tc0 + TW - W))) + ((0, 0),) * (arr.ndim - 2), mode='edge')[tr0:tr0 + TH, tc0:tc0 + TW]
    lk = pad(L); _, (py, px) = ndimage.distance_transform_edt(~lk, return_indices=True)
    rgba = np.dstack([pad(w)[py, px], ndimage.gaussian_filter(lk.astype(float), .7) * 255]).clip(0, 255).astype(np.uint8)
    os.makedirs(out, exist_ok=True); Image.fromarray(rgba, 'RGBA').save(os.path.join(out, name + '_fringe.png'), optimize=True)
    blob = bytearray()
    def put(arr):
        while len(blob) % 4: blob.append(0)
        o = len(blob); blob.extend(np.ascontiguousarray(arr).tobytes()); return [o, int(arr.size)]
    js = {'v': 1, 'verts': int(nv), 'tris': len(idx), 'pos': put(pos.astype(np.float32)), 'uv': put(uvs.astype(np.float32)), 'idx': put(idx.astype(np.uint16 if nv < 65536 else np.uint32))}
    open(os.path.join(out, name + '_fringe.bin'), 'wb').write(bytes(blob)); json.dump(js, open(os.path.join(out, name + '_fringe.json'), 'w'), separators=(',', ':'))
    # the forehead under the old fringe (seen from the front, over the region, under the hairline, above the head's own
    # brows, on the face): the sheet's skin there, its shadows kept; under the sheet's hair, the skin's colour
    skin_col = np.median(w[skin_s & front & (Y > 1.615)], 0)
    mdk = (rgb_r.astype(int).mean(2) < 60) & (Y > 1.594) & (Y < 1.62) & (np.abs(X) < .07) & np.isfinite(z_r) & (z_r < zsm + .002)
    mth = ndimage.binary_opening(mdk, iterations=3); lab, n = ndimage.label(mth)
    mbrows = np.isin(lab, np.argsort(-ndimage.sum(mth, lab, range(1, n + 1)))[:2] + 1) if n else mth
    btm = np.array([np.nonzero(mbrows[:, j])[0].min() if mbrows[:, j].any() else int((Y1 - BROW_Y) / PX) for j in range(W)])
    kept = np.nonzero(keep)[0]; n_t = n_px = 0
    for kk in np.unique(t_r[t_r >= 0]):
        k_ = kept[kk]
        if not ok[k_] or not D[ci[k_], cj[k_]] or C[k_, 1] >= ycut[cj[k_]] + .004 or C[k_, 1] <= Y1 - (btm[cj[k_]] - 2) * PX or dz[k_] > .004: continue
        q, p3 = texels(UV[I[k_]] * TS, P[I[k_]], TS)
        if not len(q): continue
        sc = np.stack([ndimage.map_coordinates(fs[..., m], [(Y1 - p3[:, 1]) / K + V0 - .5, (p3[:, 0] - X0) / K + U0 - .5], order=1) for m in range(3)], 1)
        isk = (sc[:, 0] > 60) & (sc[:, 0] - sc[:, 2] > 25)
        tex[q[:, 1], q[:, 0]] = np.where(isk[:, None], sc, skin_col); n_t += 1; n_px += len(q)
    print('fringe: Meshy\'s fringe over the forehead removed (%d triangles), the forehead painted from the sheet (%d triangles), '
          'the sheet\'s locks: %d verts, %d tris, texture %dx%d' % (int(drop.sum()), n_t, nv, len(idx), TW, TH))
    return I[keep]
