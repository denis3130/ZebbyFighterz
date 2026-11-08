#!/usr/bin/env python3
"""Ren's eyes and the skin around them redrawn clean (8/11/2026, Denis: "rifai il viso senza i capelli che coprono e
aggiungili successivamente, così gli occhi vengono fatti da dio come le dita", then "fai da solo ... senza meshy"):
called by tools/ren_head.py after tools/ren_fringe.py, on the head it builds.

Meshy painted the eyes under the sheet's hair: the -x eye cut by a seam of its texture (half its white grey), its lashes
notched, its highlights mirrored; the brows' inner ends and the nose's bridge smudged with the locks' tips; small pieces
of locks floating in front of the eye (the fringe taken out around them) and a hole between the brows (the back of the
head's hair seen through it). Here, on the face seen from the front (orthographic, BAND, sampled smoothly):
  - the pieces of the head not joined to it (ISLAND_MAX triangles at most) out;
  - the holes (the back of the head seen through the face) and the hair's purple painted on the face: skin, harmonic;
  - the -x eye and brow: the +x ones mirrored (the axis from the eyes' own match), feathered at the box's edges (BOX);
  - the highlights: the +x eye's moved (not mirrored) onto the -x eye (the sheet: both at the iris' upper left);
  - the bridge between the brows down to the nose's line (BRIDGE): plain skin (harmonic, the brows not bleeding in);
    the dark specks around the eyes too;
  - written back into the texture: each texel of the face's triangles in the region (not the hair in front of the face,
    not the back of the head), the band averaged over the texel's footprint, feathered at the region's edge;
  - a plug where the face has a hole: a small grid of skin PLUG_BACK behind the face around it (its outline pushed
    back by the caller).
"""
import os, sys
import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.linalg import spsolve
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ren_fringe import texels

BAND = (-.076, .088, 1.566, 1.622, .00008)   # the band from the front: x0, x1, y0, y1 (m), m per px
ISLAND_MAX = 30                             # the head's pieces not joined to it with that many triangles at most: out
FRONT_DZ, BACK_DZ, HOLE_DZ, RIM_DZ = .003, .012, .006, .008   # the face's triangles: within these in front of / behind its smoothed
                                            # depth (farther in front: hair; behind: the back of the head); a hole: the
                                            # surface seen that far behind; on the bridge, in front up to RIM_DZ
BOX = (.0084, .064, 1.5765, 1.6195, .0006)  # each eye's box: |x - axis| from, to; y from, to (m); its feathering
MIRROR = ((-.07, -.012), (.002, .011), 12)  # the axis' match: the -x eye's columns (m); the axis searched in (m); dy (px)
IRIS = ((.0168, .0488), (1.5852, 1.602))    # the +x iris searched in: x - axis, y (m)
BRIDGE = (.0105, 1.5715, .0068, .0013, 1.5785)   # |x - axis| under, y over; the brows' ends kept beyond; the nose's line kept
                                            # within (its x found) under that y
UNDER = (.019, 1.584)                       # and under the eyes' inner corners: |x - axis| under, y under (the locks' tips there)
FEATHER = .0005                             # the region's edge (m)
PLUG_BACK, PLUG_GRID, PLUG_MIN, PLUG_DZ = .0004, .001, 50, .05   # the plug: behind the face (m); its grid (m); holes from that
                                            # many px, where the surface seen is that far behind (the back of the head)


def islands(Q, I, n_max=ISLAND_MAX):
    """Which triangles to keep: those of the pieces (joined by shared positions) with more than n_max triangles."""
    key = np.round(Q / 1e-5).astype(np.int64); _, weld = np.unique(key, axis=0, return_inverse=True); weld = weld.ravel()
    nt = len(I); A = sparse.csr_matrix((np.ones(3 * nt), (np.repeat(np.arange(nt), 3), weld[I].ravel())), shape=(nt, weld.max() + 1))
    n, lab = sparse.csgraph.connected_components(A @ A.T, directed=False)
    return np.bincount(lab, minlength=n)[lab] > n_max


def texels_wide(uv, A, TS, ring=1.5):
    """A triangle's texels as texels() (ren_fringe.py), and those within ring texels outside it (the pieces' edges: a
    texel half covered by its triangle, its centre out, kept its old colour and the filtering drew it as a line along the
    seam): (inside: cols/rows, 3D points), (ring: the same, the points extrapolated on its plane)."""
    lo = np.floor(uv.min(0) - ring).astype(int); hi = np.ceil(uv.max(0) + ring).astype(int)
    xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1)); px = np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)
    T = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T; det = np.linalg.det(T)
    empty = (np.zeros((0, 2), int), np.zeros((0, 3)))
    if abs(det) < 1e-9: return empty, empty
    b = np.linalg.solve(T, (px - uv[0]).T).T; w = np.c_[1 - b.sum(1), b]
    edge = np.linalg.norm(uv[[1, 2, 0]] - uv[[2, 0, 1]], axis=1); h = abs(det) / np.maximum(edge, 1e-9)   # (each corner's altitude)
    ins = (w >= -1e-3).all(1); near = ((w * h) >= -ring).all(1) & ~ins
    out = []
    for m in (ins, near):
        q = np.floor(px[m]).astype(int); g = (q >= 0).all(1) & (q < TS).all(1); out.append((q[g], (w[m] @ A)[g]))
    return out[0], out[1]


def render_uv(P, UV, I, x0, x1, y0, y1, px):
    """Orthographic front view of the triangles I (looking down -z): per pixel its uv (barycentric), depth (-inf where
    empty) and triangle (index into I, -1 where empty)."""
    W = int(round((x1 - x0) / px)); H = int(round((y1 - y0) / px))
    uvb = np.zeros((H, W, 2)); zb = np.full((H, W), -np.inf); tb = np.full((H, W), -1, np.int64)
    A = P[I]; X = (A[:, :, 0] - x0) / px; Y = (y1 - A[:, :, 1]) / px
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
        zb[iy, ix] = zz; uvb[iy, ix] = ww @ UV[I[k]]; tb[iy, ix] = k
    return uvb, zb, tb


def padded(tex, UV, I):
    """The texture with the texels outside the triangles' pieces taking their nearest piece's colour (sampled smoothly
    near a seam, a piece's edge would pull in the packing's colours)."""
    TS = tex.shape[0]; m = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(m)
    for tri in UV[I] * TS: dr.polygon([tuple(v) for v in tri], fill=255)
    inside = ndimage.binary_dilation(np.asarray(m) > 0, iterations=1)
    gy, gx = ndimage.distance_transform_edt(~inside, return_distances=False, return_indices=True)
    return tex[gy, gx]


def sample(tex, uv):
    """The texture at uv (h x w x 2), cubic spline."""
    TS = tex.shape[0]; r = uv[..., 1] * TS - .5; c = uv[..., 0] * TS - .5
    return np.stack([ndimage.map_coordinates(tex[..., m].astype(float), [r, c], order=3, mode='nearest') for m in range(3)], -1).clip(0, 255)


def harmonic(f, unk):
    """f with its unknown pixels (unk) the smoothest field matching the known ones at their border (Laplace)."""
    h, w = unk.shape; n = int(unk.sum())
    if n == 0: return f
    idx = -np.ones((h, w), int); idx[unk] = np.arange(n); ys, xs = np.nonzero(unk)
    rows, cols = [], []; b = np.zeros((n, f.shape[2])); deg = np.zeros(n)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        y2, x2 = ys + dy, xs + dx; ins = (y2 >= 0) & (y2 < h) & (x2 >= 0) & (x2 < w); k = np.nonzero(ins)[0]; deg[k] += 1
        nb = idx[y2[k], x2[k]]; u = nb >= 0; rows.append(k[u]); cols.append(nb[u]); kk = k[~u]; b[kk] += f[y2[kk], x2[kk]]
    rows, cols = np.concatenate(rows), np.concatenate(cols)
    A = sparse.csc_matrix((np.r_[-np.ones(len(rows)), deg], (np.r_[rows, np.arange(n)], np.r_[cols, np.arange(n)])), shape=(n, n))
    out = f.copy(); sol = spsolve(A, b); out[ys, xs] = sol.reshape(n, -1); return out


def fill(f, unk, k=4):
    """harmonic() on a k times coarser grid, then exactly within 3k px of the known pixels (fast on big regions)."""
    h, w = unk.shape; H2, W2 = -(-h // k), -(-w // k)
    pad = lambda a: np.pad(a, ((0, H2 * k - h), (0, W2 * k - w)) + ((0, 0),) * (a.ndim - 2), mode='edge')
    fu, kn = pad(f), ~pad(unk); kc = kn.reshape(H2, k, W2, k).sum((1, 3))
    fc = (fu * kn[..., None]).reshape(H2, k, W2, k, -1).sum((1, 3)) / np.maximum(kc, 1)[..., None]
    fc = harmonic(fc, kc == 0)
    up = np.stack([ndimage.zoom(fc[..., m], k, order=1)[:h, :w] for m in range(f.shape[2])], -1)
    g = np.where(unk[..., None], up, f)
    return harmonic(g, unk & (ndimage.distance_transform_edt(unk) <= 3 * k))


def classes(img):
    """lum, the skin (with its light shadows), the hair's purple, the dark lines, the whites."""
    lum = img.mean(2); r, g, b = img[..., 0], img[..., 1], img[..., 2]; sat = img.max(2) - img.min(2)
    skin = (r > 150) & (r - b > 60) & (lum > 140)
    purple = (lum >= 30) & (lum < 130) & (r >= g + 2) & (b >= g) & (r - b < 30)
    return lum, skin, purple, lum < 80, (img.min(2) > 175) & (sat < 50)


def eyes(Q, N, UV, I, tex):
    """See above. Q, N, UV: the head's vertices, normals, uvs; I: its triangles; tex: its texture (h x w x 3 float,
    painted in place). Returns (the triangles kept, the plug: {pos, nor, uv, src: the vertex each copies its skin from,
    tri: its triangles over its own vertices} or None)."""
    P = Q.astype(float); UV = UV.astype(float); I = np.asarray(I).astype(np.int64)
    keep = islands(P, I); I = I[keep]
    print('eyes: %d triangles of pieces not joined to the head out' % int((~keep).sum()))
    x0, x1, y0, y1, R = BAND; TS = tex.shape[0]
    uvb, zb, tb = render_uv(P, UV, I, x0, x1, y0, y1, R); H, W = zb.shape
    X = x0 + (np.arange(W) + .5) * R; Y = y1 - (np.arange(H) + .5) * R; XX, YY = np.meshgrid(X, Y); jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    ok = np.isfinite(zb); img0 = sample(padded(tex, UV, I), uvb); img0[~ok] = 0; img = img0.copy()
    lum, skin, purple, dark, white = classes(img)
    # the face's smoothed depth (from its skin), the holes (nothing, or the back of the head) and the hair in front
    _, (gy, gx) = ndimage.distance_transform_edt(~(ok & skin), return_indices=True); zs = ndimage.gaussian_filter(zb[gy, gx], .002 / R)
    hole = ~ok | (zb < zs - HOLE_DZ); front = ok & (zb > zs + FRONT_DZ)
    img = fill(img, hole | (purple & ~dark & ~front))
    lum, skin, purple, dark, white = classes(img)
    # the mirror's axis: the -x eye against the +x one mirrored (dark and white, normalized cross-correlation)
    (la, lb_), (ma, mb), dmax = MIRROR; rows_e = (Y > 1.578) & (Y < 1.618)
    L0, L1 = int((la - x0) / R), int((lb_ - x0) / R); feat = np.concatenate([dark[rows_e][:, L0:L1], white[rows_e][:, L0:L1]], 1).astype(float).ravel()
    best = None
    for xm in range(int((ma - x0) / R), int((mb - x0) / R) + 1):
        jr = 2 * xm - np.arange(L0, L1)
        if jr.min() < 0 or jr.max() >= W: continue
        for dy in range(-dmax, dmax + 1, 2):
            rr = np.clip(np.nonzero(rows_e)[0] + dy, 0, H - 1)
            g2 = np.concatenate([dark[rr][:, jr], white[rr][:, jr]], 1).astype(float).ravel()
            sc = ((feat - feat.mean()) * (g2 - g2.mean())).mean() / (feat.std() * g2.std() + 1e-9)
            if best is None or sc > best[0]: best = (sc, xm, dy)
    sc, xm, dy = best; XMID = x0 + (xm + .5) * R
    print('eyes: the mirror\'s axis at x %.4f m, the -x eye %.2f mm lower, match %.2f' % (XMID, -dy * R * 1000, sc))
    # the -x box: the +x mirrored (not where the +x side has hair in front: the temples' locks stay theirs)
    jr = np.clip(2 * xm - np.arange(W), 0, W - 1); rr = np.clip(np.arange(H) + dy, 0, H - 1)
    mir = img[rr][:, jr]; mhair = (front | purple)[rr][:, jr]
    b0, b1, by0, by1, bf = BOX; ax_ = XX - XMID
    boxL = (ax_ < -b0) & (ax_ > -b1) & (YY > by0) & (YY < by1); boxR = (ax_ > b0) & (ax_ < b1) & (YY > by0) & (YY < by1)
    al = ndimage.gaussian_filter((boxL & ~ndimage.binary_dilation(mhair, iterations=3)).astype(float), bf / R)[..., None]
    img = img * (1 - al) + mir * al
    lum, skin, purple, dark, white = classes(img); r, g, b = img[..., 0], img[..., 1], img[..., 2]
    # the irises (the +x one; the -x is its mirror) and the highlights: the -x eye's out (harmonic over them and their
    # soft edge), the +x eye's copied there, moved
    (ia, ib), (iya, iyb) = IRIS; srch = (ax_ > ia) & (ax_ < ib) & (YY > iya) & (YY < iyb)
    iris = srch & (r - b > 45) & (lum < 170) & (lum > 40) & ~skin
    m = ndimage.binary_opening(iris, iterations=3); lab, n = ndimage.label(m)
    k = np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1; ys, xs = np.nonzero(ndimage.binary_fill_holes(lab == k))
    rad = (xs.max() - xs.min()) / 2; cxR = (xs.min() + xs.max()) / 2; cy = ys.max() - rad; cxL = 2 * xm - cxR; cyL = cy - dy
    wh = img.min(2) > 195
    def blobs(cx, cy_):
        lab2, n2 = ndimage.label(wh & (np.hypot(jj - cx, ii - cy_) < rad * 1.08)); sz = ndimage.sum(wh, lab2, range(1, n2 + 1))
        return np.isin(lab2, np.nonzero(sz < 2500)[0] + 1)
    hR, hL = blobs(cxR, cy), blobs(cxL, cyL)
    hz = ndimage.binary_dilation(hL, iterations=9); a0, a1, c0, c1 = int(cyL - 1.3 * rad), int(cyL + 1.3 * rad), int(cxL - 1.3 * rad), int(cxL + 1.3 * rad)
    img[a0:a1, c0:c1] = harmonic(img[a0:a1, c0:c1].copy(), hz[a0:a1, c0:c1])
    sx, sy = int(round(cxR - cxL)), int(round(cy - cyL)); hRd = ndimage.binary_dilation(hR, iterations=2); ys, xs = np.nonzero(hRd)
    img[ys - sy, xs - sx] = img[ys, xs]
    print('eyes: irises %.1f mm across, their centres %.1f mm apart; highlights: %d px out of the -x iris, %d copied from the +x one' % (
        2 * rad * R * 1000, (cxR - cxL) * R * 1000, int(hL.sum()), int(hRd.sum())))
    lum, skin, purple, dark, white = classes(img)
    # the bridge and the specks: harmonic skin (the solve sees light skin where the brows and the eyes touch it; they
    # are put back after); the nose's line (its x: the darkest under the bridge) and the brows' ends kept
    bw, bya, bkeep, nw, nya = BRIDGE
    lab, n = ndimage.label(dark & (boxL | boxR)); sz = ndimage.sum(dark, lab, range(1, n + 1)); big = np.isin(lab, np.nonzero(sz > (.001 / R) ** 2 * 3)[0] + 1)
    nose = (np.abs(ax_) < .004) & (YY > bya - .005) & (YY < bya + .005) & dark
    xn = XX[nose].mean() if nose.any() else XMID
    bridge = ((np.abs(ax_) < bw) | ((np.abs(ax_) < UNDER[0]) & (YY < UNDER[1]))) & (YY > bya) & ~((np.abs(XX - xn) < nw) & (YY < nya))
    irises = (np.hypot(jj - cxR, ii - cy) < rad * 1.1) | (np.hypot(jj - cxL, ii - cyL) < rad * 1.1)
    sat = img.max(2) - img.min(2); eyein = ((img.min(2) > 150) & (sat < 70)) | irises
    lab, n = ndimage.label(eyein); eyein = np.isin(lab, np.nonzero(ndimage.sum(eyein, lab, range(1, n + 1)) > (.001 / R) ** 2)[0] + 1)
    keepf = ndimage.binary_dilation((big & ~(bridge & (np.abs(ax_) < bkeep))) | eyein | (dark & (np.abs(XX - xn) < nw) & (YY < nya)), iterations=1)
    speck = dark & (boxL | boxR) & ~big & ~irises
    unk = (bridge | ndimage.binary_dilation(speck, iterations=4)) & ~keepf
    light = skin & (lum > 172)
    ring = ndimage.binary_dilation(bridge, iterations=int(.0015 / R)) & ~bridge & ~light & ~keepf
    unk |= ring
    SK = np.median(img[light & ndimage.binary_dilation(bridge, iterations=int(.003 / R)) & ~bridge], 0)
    tmp = img.copy(); tmp[keepf & ndimage.binary_dilation(unk, iterations=3)] = SK
    out = fill(tmp, unk); out[~unk] = img[~unk]
    print('eyes: the bridge and %d px of specks as skin (%s), the nose\'s line at x %.4f m kept' % (int(speck.sum()), SK.astype(int), xn))
    # written back: the region (the boxes and the bridge), feathered
    alpha = np.clip(ndimage.gaussian_filter((boxL | boxR | bridge).astype(float), FEATHER / R), 0, 1)
    fin = img0 * (1 - alpha[..., None]) + out * alpha[..., None]
    C = P[I].mean(1); cj = ((C[:, 0] - x0) / R).astype(int); ci = ((y1 - C[:, 1]) / R).astype(int)
    inb = (cj >= 0) & (cj < W) & (ci >= 0) & (ci < H); cand = np.nonzero(inb)[0]
    cand = cand[alpha[ci[cand], cj[cand]] > 0]; dz = C[cand, 2] - zs[ci[cand], cj[cand]]
    # (on the bridge only the fringe is hair, and the holes' rims bulge out: in front up to RIM_DZ there)
    cand = cand[((dz < FRONT_DZ) | ((dz < RIM_DZ) & bridge[ci[cand], cj[cand]])) & (dz > -BACK_DZ)]
    blur = {}; n_tx = 0; src = tex.copy(); jobs = []
    for k in cand:
        A = P[I[k]]; e1, e2 = A[1, :2] - A[0, :2], A[2, :2] - A[0, :2]; fa = abs(e1[0] * e2[1] - e1[1] * e2[0]) / 2 / R ** 2
        u = UV[I[k]] * TS; f1, f2 = u[1] - u[0], u[2] - u[0]; ta = abs(f1[0] * f2[1] - f1[1] * f2[0]) / 2
        s = round(np.clip(.45 * np.sqrt(fa / max(ta, 1e-9)), .5, 6.) * 2) / 2   # (the texel's footprint in band px)
        if s not in blur: blur[s] = np.stack([ndimage.gaussian_filter(fin[..., c], s) for c in range(3)], -1)
        jobs.append((s, texels_wide(u, A, TS)))
    for part in (1, 0):   # (the rings first: a texel inside a triangle takes that triangle's colour)
        for s, tx in jobs:
            q, p3 = tx[part]
            if not len(q): continue
            j = (p3[:, 0] - x0) / R - .5; i = (y1 - p3[:, 1]) / R - .5
            v = (j >= 0) & (j < W - 1) & (i >= 0) & (i < H - 1)
            iq, jq = np.clip(np.round(i).astype(int), 0, H - 1), np.clip(np.round(j).astype(int), 0, W - 1)
            v &= p3[:, 2] > zs[iq, jq] - BACK_DZ   # (all its texels: the pieces of the locks sunk through the face take its colours)
            if not v.any(): continue
            col = np.stack([ndimage.map_coordinates(blur[s][..., c], [i[v], j[v]], order=1) for c in range(3)], 1)
            a_ = ndimage.map_coordinates(alpha, [i[v], j[v]], order=1)[:, None]; qq = q[v]
            tex[qq[:, 1], qq[:, 0]] = src[qq[:, 1], qq[:, 0]] * (1 - a_) + col * a_; n_tx += len(qq) * (part == 0)
    print('eyes: %d triangles of the face repainted (%d texels)' % (len(cand), n_tx))
    # the plug: under each hole of the face in the region (the back of the head seen through it)
    holes = (~ok | (zb < zs - PLUG_DZ)) & (alpha > .5); lab, n = ndimage.label(holes); sz = ndimage.sum(holes, lab, range(1, n + 1))
    holes = np.isin(lab, np.nonzero(sz >= PLUG_MIN)[0] + 1)
    for k in np.nonzero(sz >= PLUG_MIN)[0]:
        ys, xs = np.nonzero(lab == k + 1)
        dd = (zs - np.where(np.isfinite(zb), zb, -1.))[ys, xs]
        print('eyes: a hole of %.1f mm2 at x %.4f..%.4f, y %.4f..%.4f m, seen behind by %.0f mm (median)' % (len(ys) * R * R * 1e6, X[xs.min()], X[xs.max()], Y[ys.max()], Y[ys.min()], 1000 * np.median(dd)))
    if not holes.any(): return I, None
    face = ok & ~hole & ~front; zf = harmonic(np.where(face, zb, 0)[..., None], ~face & ndimage.binary_dilation(holes, iterations=int(.005 / R)))[..., 0]
    area = ndimage.binary_dilation(holes, iterations=int(.002 / R)); st = max(1, int(round(PLUG_GRID / R)))
    gi = np.arange(0, H, st); gj = np.arange(0, W, st); GI, GJ = np.meshgrid(gi, gj, indexing='ij'); ins = area[GI, GJ]
    vid = -np.ones(GI.shape, int); tris = []; nv = 0
    for a_ in range(GI.shape[0] - 1):
        for b_ in range(GI.shape[1] - 1):
            cell = [(a_, b_), (a_ + 1, b_), (a_ + 1, b_ + 1), (a_, b_ + 1)]
            if not all(ins[c] for c in cell): continue
            for c in cell:
                if vid[c] < 0: vid[c] = nv; nv += 1
            A_, B_, C_, D_ = [vid[c] for c in cell]; tris += [(A_, B_, C_), (A_, C_, D_)]   # (facing +z)
    if not tris: return I, None
    pos = np.zeros((nv, 3)); nor = np.zeros((nv, 3)); gzy, gzx = np.gradient(ndimage.gaussian_filter(zf, 4), R)
    for (p, q_), kk in np.ndenumerate(vid):
        if kk < 0: continue
        i_, j_ = GI[p, q_], GJ[p, q_]; pos[kk] = (X[j_], Y[i_], zf[i_, j_] - PLUG_BACK)
        nn = np.array([-gzx[i_, j_], gzy[i_, j_], 1.]); nor[kk] = nn / np.linalg.norm(nn)
    # its colour: the skin repainted at the hole's middle (the uv of the biggest face triangle of the bridge there)
    hy, hx = [int(v) for v in ndimage.center_of_mass(holes)]; near = (np.hypot(jj - hx, ii - hy) < .004 / R) & face & (out.mean(2) > 150) & bridge
    tk = np.unique(tb[near]); tk = tk[tk >= 0]
    uarea = lambda t: abs(np.cross(np.r_[UV[I[t]][1] - UV[I[t]][0], 0], np.r_[UV[I[t]][2] - UV[I[t]][0], 0])[2])
    tbest = max(tk, key=uarea) if len(tk) else int(tb[hy, hx]); uv0 = UV[I[tbest]].mean(0)
    from scipy.spatial import cKDTree
    _, srcv = cKDTree(P).query(pos)
    print('eyes: a plug of %d triangles under %d px of holes in the face' % (len(tris), int(holes.sum())))
    return I, {'pos': pos, 'nor': nor, 'uv': np.tile(uv0, (nv, 1)), 'src': srcv, 'tri': np.array(tris, np.int64)}


if __name__ == '__main__':
    # a try on a built head (OUT_DIR of tools/ren_head.py): python3 tools/ren_eyes.py IN_DIR OUT_DIR (the texture and the
    # geometry rewritten there)
    import json, shutil
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    m = json.load(open(os.path.join(src_dir, 'ren_head.json'))); B = open(os.path.join(src_dir, 'ren_head.bin'), 'rb').read()
    get = lambda k, dt, w: np.frombuffer(B, dt, m[k][1], m[k][0]).reshape(-1, w).copy() if w > 1 else np.frombuffer(B, dt, m[k][1], m[k][0]).copy()
    it = np.uint32 if m['verts'] > 65535 else np.uint16
    Qh, Nh, UVh = get('pos', np.float32, 3), get('nor', np.float32, 3), get('uv', np.float32, 2)
    Ih = get('idx', it, 3); jnt, wgt, lb = get('jnt', np.uint8, 4), get('wgt', np.float32, 4), get('lb', np.float32, 1)
    t = np.asarray(Image.open(os.path.join(src_dir, 'ren_head.jpg')).convert('RGB')).astype(np.float64)
    Ik, plug = eyes(Qh, Nh, UVh, Ih, t)
    if plug is not None:
        n0 = len(Qh); Qh = np.r_[Qh, plug['pos']]; Nh = np.r_[Nh, plug['nor']]; UVh = np.r_[UVh, plug['uv']]
        jnt = np.r_[jnt, jnt[plug['src']]]; wgt = np.r_[wgt, wgt[plug['src']]]; lb = np.r_[lb, np.full(len(plug['pos']), .1)]; Ik = np.r_[Ik, plug['tri'] + n0]
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(src_dir):
        if not f.startswith('ren_head'): shutil.copy(os.path.join(src_dir, f), out_dir)
    blob = bytearray(); nv = len(Qh)
    def put(arr):
        while len(blob) % 4: blob.append(0)
        o = len(blob); blob.extend(np.ascontiguousarray(arr).tobytes()); return [o, int(arr.size)]
    head = {'v': 1, 'verts': nv, 'tris': len(Ik), 'scale': m['scale'], 'pos': put(Qh.astype(np.float32)), 'nor': put(Nh.astype(np.float32)), 'uv': put(UVh.astype(np.float32)),
            'jnt': put(jnt.astype(np.uint8)), 'wgt': put(wgt.astype(np.float32)), 'idx': put(Ik.astype(np.uint32 if nv > 65535 else np.uint16)),
            'hide': put(np.frombuffer(B, np.uint32, m['hide'][1], m['hide'][0])), 'lb': put(lb.astype(np.float32))}
    open(os.path.join(out_dir, 'ren_head.bin'), 'wb').write(bytes(blob)); json.dump(head, open(os.path.join(out_dir, 'ren_head.json'), 'w'), separators=(',', ':'))
    t = padded(t, UVh, Ik)   # (as tools/ren_head.py does before saving)
    Image.fromarray(t.clip(0, 255).round().astype(np.uint8)).save(os.path.join(out_dir, 'ren_head.jpg'), quality=88, optimize=True)
