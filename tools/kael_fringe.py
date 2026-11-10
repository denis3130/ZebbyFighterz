#!/usr/bin/env python3
"""Kael's face from Denis's head images (11/11/2026 night, Denis circling the face in every view: "voglio che le parti
che ho cerchiato siano perfettamente identiche alle immagini sue. faccia occhi e naso sopratutto, le orecchie vanno
bene ma per favore usa tutte le tue risorse per copiarle al meglio come hai fatto con ren"), called by tools/kael_head.py
on the head it builds (FACE there):

- 'paint' (used): Meshy's locks in front of the eyes and the forehead (seen from the front camera, hair in front of the
  face's skin by more than DROP_DZ m, under the forehead's top, within PAINT_SIDE m of the face's middle) left out, with
  the pieces of hair this leaves floating; the face's skin painted from the images (each texel from the views that see
  it and draw the face there: the image's skin with what it holds, its eyes, brows, nose, mouth, lines and shadows; not
  its hair), weighted by how much it faces each (to the power POW); the features (FEAT: the eyes, the nose, the mouth,
  the brows, the chin) from the front image alone (two images' eyes over each other doubled them); the front image's
  bangs painted on the forehead's skin where the model shows it from the front.
- 'sheet' (tried): the front image's bangs a sheet in front of the face (from the side: streaks and pieces).
- 'all' (tried): all of the circled area (AREA), hair or skin, from the image that sees each point best, the face first
  around the eyes (EYE_BAND, FACE_PRIO): the hair came out in specks (each point from another image).
- 'skin' (tried): only the face painted, Meshy's locks kept (they hang over the eyes); lift() (tried: the bangs are one
  surface with the forehead, lifted they tore it into strips); carve() with the profiles (CARVE_VIEWS, tried: behind a
  lock taken out there is another, holes and pieces over the eye).

face(...) paints in place and returns (the head's triangles kept, the sheet or None)."""
import json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from cel_light import view_depth

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DROP_DZ, DROP_TOP = .0015, .006   # m: in front of the skin by more than; the forehead's top (its highest skin) plus
EAR = (.057, .03)                 # m: the ears (|x - the face's middle| over [0], z under [1]): not painted
POW, MIN_FACING, SEEN = 16., .2, .002
FEAT = (.042, .006, .03, .3, .004)   # the features: |x - middle| under [0], from [1] under the chin to [2] over the eyes, facing the front camera over [3]; [4]: the edge's blend (m)
UNDER = (178, 124, 96)
GAP, TUCK, ROOTS, GRID, STEEP = .0025, .0015, 24, 6, .006
VOTE = (.25, 1, 40, .12)          # see carve(): facing the view over [0]; at least [1] votes; floating pieces under [2] triangles; the skin within [3] m behind (from the side the bangs' ends stand 2-11 cm in front of the brow)
CARVE_VIEWS, CARVE_Z = (), .01   # (and only in front of z over CARVE_Z m: not the sideburns over the ears)   # the views carve() asks ('paint': the temples and the eyes' outer corners from the side)
LIFT = (.066, .006, .010)         # see lift() (tried, not used: the bangs are one surface with the forehead, lifted they tore it into strips): within [0] m of the face's middle; columns of [1] m; ending [2] m above the eyes' line
EYE_BAND, FACE_PRIO = (.022, .05), 30.   # paint_all: from [0] m under the eyes' line to [1] over it (the brows, the temples), the face drawn by any image first
AREA = (.075, .01, .012, -.005)   # the circled area (paint_all): |x - middle| under [0], from [1] under the chin to [2] over the forehead's top, z over [3] (m)
PAINT_SIDE, BANGS_FACING, BANGS_LOW = .046, .45, .012   # 'paint' (see face()): Meshy's locks out within [0] m of the middle; the bangs
                                  # painted where the skin faces the front over [1], down to [2] m under the eyes' line
SIDE = .058                       # m: the sheet not further than this from the face's middle (the temples' locks stay Meshy's)


def drawing(view):
    D = np.asarray(Image.open(os.path.join(ROOT, 'docs/ref/personaggi/kael_testa_%s.png' % view)).convert('RGB')).astype(np.float64)
    bg = np.median(D[5:40, 5:40].reshape(-1, 3), 0)
    F = ndimage.binary_fill_holes(ndimage.binary_opening(np.abs(D - bg).sum(2) > 30, iterations=1))
    return D, F


def face_mask(D, F, is_skin, is_hair):
    """The image's face: its skin and what is joined to it that is not hair (the eyes, the nose, the mouth, the lines),
    the piece with the most skin (not the ears)."""
    sk = is_skin(D) & F; hr = is_hair(D) & ~sk & F
    lab, n = ndimage.label((sk | (F & ~hr)) & F)
    if n == 0: return np.zeros_like(F)
    cnt = ndimage.sum(sk, lab, range(1, n + 1))
    return lab == 1 + int(np.argmax(cnt))


def lift(Q, N, I, vc, hair_v, is_skin, cam, mid, eye_m):
    """Meshy's locks over the face lifted to end above the brows, as in the images (they hang over the eyes; the images
    show the eyes under the bangs): seen from the front camera, the hair in front of the face's skin (by more than
    DROP_DZ, within LIFT[0] m of the face's middle), under the hairline (the face's topmost skin over that column), is
    pressed up toward the hairline so its lowest point (over LIFT[1] m columns) ends LIFT[2] m above the eyes' line,
    keeping its distance from the skin; its normals renewed. Q, N in place; returns how many points moved."""
    th = np.radians(cam['yaw']); fwd = np.array([np.sin(th), 0, np.cos(th)])
    D, F = drawing('fronte'); H, W = F.shape
    skin_t = is_skin(vc)[I].all(1); Zs, proj = view_depth(Q, I[skin_t], cam, W, H)
    have = np.isfinite(Zs); top_v = np.where(have.any(0), np.argmax(have, 0), H)   # (per column: the face's topmost skin pixel)
    _, first, inv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    X = Q[first].copy(); hw = np.zeros(len(first), bool); np.logical_or.at(hw, inv, hair_v)
    sk = np.zeros(len(first), bool); np.logical_or.at(sk, inv, ~hair_v); hw &= ~sk   # (points shared with the skin: held)
    u, v, d = proj(X); ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
    zs = np.where(have[vi, ui], Zs[vi, ui], -np.inf)
    y_h = (cam['by'] - top_v[ui]) / cam['s']
    cand = hw & np.isfinite(zs) & (d > zs + DROP_DZ) & (X[:, 1] < y_h) & (np.abs(X[:, 0] - mid) < LIFT[0])
    y_b = eye_m + LIFT[2]
    # (per column band: the lowest candidate)
    band = np.floor((X[:, 0] - mid) / LIFT[1]).astype(int); y_low = {}
    for b_ in np.unique(band[cand]): y_low[b_] = X[cand & (band == b_), 1].min()
    yl = np.array([y_low.get(b_, np.inf) for b_ in band])
    k = np.nonzero(cand & (yl < y_b) & (y_h > y_b + .005))[0]
    y_new = y_h[k] - (y_h[k] - X[k, 1]) * (y_h[k] - y_b) / np.maximum(y_h[k] - yl[k], 1e-6)
    off = d[k] - zs[k]   # (its distance in front of the skin, kept)
    Xn = X[k].copy(); Xn[:, 1] = y_new
    u2, v2, d2 = proj(Xn); ui2, vi2 = np.clip(np.round(u2).astype(int), 0, W - 1), np.clip(np.round(v2).astype(int), 0, H - 1)
    zs2 = np.where(have[vi2, ui2], Zs[vi2, ui2], zs[k]); Xn += fwd[None] * ((zs2 + off) - d2)[:, None]
    X[k] = Xn
    # (normals: the moved surface's, area weighted)
    Tw = inv[I]; fn = np.cross(X[Tw[:, 1]] - X[Tw[:, 0]], X[Tw[:, 2]] - X[Tw[:, 0]]); acc = np.zeros_like(X)
    for c in range(3): np.add.at(acc, Tw[:, c], fn)
    Nw = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    moved = np.zeros(len(first), bool); moved[k] = True; aff = np.zeros(len(first), bool); aff[Tw[moved[Tw].any(1)].ravel()] = True
    Q[:] = X[inv]; sel = aff[inv]; N[sel] = Nw[inv[sel]]
    print('face: %d points of Meshy\'s locks over the face pressed up to end %.0f mm above the eyes (up to %.1f mm)' % (
        len(k), 1000 * LIFT[2], 1000 * (np.abs(y_new - (Q[first][k, 1] if False else y_new)).max() if len(k) else 0)))
    return len(k)


def carve(Q, I, hair_v, is_skin, is_hair, cams, mid, chin_m, top, skin_all=None):
    """Meshy's hair triangles in front of the face that the images do not draw: per view that sees one (the front-most
    there, facing it over VOTE[0]) with the face's skin behind it (by more than DROP_DZ), a vote for the face if the
    image draws its face there, for the hair if it draws hair; out where the face's votes are more (and at least
    VOTE[1]), then the hair's pieces this leaves under VOTE[2] triangles out too."""
    C = Q[I].mean(1); fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    hair_t = hair_v[I].any(1) & (C[:, 1] < top) & (C[:, 1] > chin_m - .01) & (np.abs(C[:, 0] - mid) < .075) & (C[:, 2] > CARVE_Z)
    vf = np.zeros(len(I), int); vh = np.zeros(len(I), int)
    for view, cam in cams.items():
        D, F = drawing(view); H, W = F.shape
        FM = ndimage.binary_erosion(face_mask(D, F, is_skin, is_hair), iterations=2); HM = F & ~ndimage.binary_dilation(FM, iterations=2)
        Z, pj = view_depth(Q, I, cam, W, H); Zs_, _ = view_depth(Q, I[skin_all], cam, W, H)
        u, v, d = pj(C); ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
        t = np.radians(cam['yaw']); facing = np.abs(fn @ np.array([np.sin(t), 0, np.cos(t)]))
        behind = np.isfinite(Zs_[vi, ui]) & (d > Zs_[vi, ui] + DROP_DZ) & (d - Zs_[vi, ui] < VOTE[3])   # (the face's skin just behind it)
        seen = hair_t & behind & (d >= Z[vi, ui] - SEEN) & (facing > VOTE[0]) & (u >= 0) & (u < W) & (v >= 0) & (v < H)
        vf += seen & FM[vi, ui]; vh += seen & HM[vi, ui]
    out = hair_t & (vf > vh) & (vf >= VOTE[1])
    # (the pieces of hair this leaves floating)
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel()
    rest = np.nonzero(~out)[0]
    A = csr_matrix((np.ones(3 * len(rest)), (np.repeat(np.arange(len(rest)), 3), wv[I[rest]].ravel())), shape=(len(rest), wv.max() + 1))
    _, lab = connected_components(A @ A.T, directed=False); sz = np.bincount(lab)
    small = rest[(sz[lab] < VOTE[2])]
    out[small] = True
    print('face: %d of Meshy\'s hair triangles over the face the images draw as face left out (%d of their floating pieces)' % (int(out.sum()) - len(small), len(small)))
    return out


def face(out, Q, N, UV, I, ys, xs, ks, pos, nor, vc, hair_v, ear_v, collar_v, mid, eye_m, chin_m, cams, is_skin, is_hair, sheet=True, paint_bangs=False, paint_all=False):
    cams = {k: v for k, v in cams.items()}; fr = cams['fronte']
    th = np.radians(fr['yaw']); right = np.array([np.cos(th), 0, -np.sin(th)]); fwd = np.array([np.sin(th), 0, np.cos(th)]); up = np.array([0., 1., 0.])
    Dfr, Ffr = drawing('fronte'); H, W = Ffr.shape
    skin_t = is_skin(vc)[I].all(1)
    Zs, proj = view_depth(Q, I[skin_t], fr, W, H)   # (the face's skin from the front)
    # Meshy's locks over the face: left out
    C = Q[I].mean(1); u, v, d = proj(C); ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
    front_skin = is_skin(vc) & (np.abs(Q[:, 0] - mid) < .03) & (Q[:, 2] > .03)
    top = Q[front_skin, 1].max() + DROP_TOP
    side = SIDE if sheet else PAINT_SIDE
    over = np.isfinite(Zs[vi, ui]) & (d > Zs[vi, ui] + DROP_DZ) & (C[:, 1] < top) & hair_v[I].any(1) & (np.abs(C[:, 0] - mid) < side)
    if not sheet and not paint_bangs: over[:] = False   # ('skin': Meshy's locks kept)
    if paint_bangs and CARVE_VIEWS:   # (and in the profiles, Meshy's locks in front of the temple and the eye's outer corner where they draw the face)
        over |= carve(Q, I, hair_v, is_skin, is_hair, {k_: cams[k_] for k_ in CARVE_VIEWS}, mid, chin_m, top, skin_all=skin_t & ~over)
    if paint_bangs:   # (and the pieces of hair this leaves floating)
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import connected_components
        _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel(); rest = np.nonzero(~over)[0]
        A = csr_matrix((np.ones(3 * len(rest)), (np.repeat(np.arange(len(rest)), 3), wv[I[rest]].ravel())), shape=(len(rest), wv.max() + 1))
        _, lab = connected_components(A @ A.T, directed=False); sz = np.bincount(lab); over[rest[sz[lab] < VOTE[2]]] = True
    keep = ~over
    print('face: %d of Meshy\'s triangles over the face left out (under %.3f m)' % (int(over.sum()), top))
    # the face's texels: painted from the images
    Ik = I[keep]
    region = (np.abs(pos[:, 0] - mid) < AREA[0]) & (pos[:, 1] > chin_m - AREA[1]) & (pos[:, 1] < top + AREA[2]) & (pos[:, 2] > AREA[3])
    cls = (is_skin(out[ys, xs]) | skin_t[ks]) if not paint_all else region   # ('paint': all of the circled area, hair or skin, from the images)
    sel = np.nonzero(keep[ks] & cls & ~ear_v[I[ks]].any(1) & ~collar_v[I[ks]].any(1)
                     & ~((np.abs(pos[:, 0] - mid) > EAR[0]) & (pos[:, 2] < EAR[1])) & (pos[:, 1] < top + (AREA[2] if paint_all else 0)))[0]
    p, n = pos[sel], nor[sel]
    sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - a) / (b - a), 0, 1))
    zone = (sm(FEAT[0], FEAT[0] - FEAT[4], np.abs(p[:, 0] - mid)) * sm(chin_m - FEAT[1] - FEAT[4], chin_m - FEAT[1], p[:, 1])
            * sm(eye_m + FEAT[2], eye_m + FEAT[2] - FEAT[4], p[:, 1]) * sm(FEAT[3] - .1, FEAT[3], n @ fwd))
    acc = np.zeros((len(sel), 3)); wsum = np.zeros(len(sel)); seen_any = np.zeros(len(sel), bool)
    for view, cam in cams.items():
        D, F = (Dfr, Ffr) if view == 'fronte' else drawing(view); Hv, Wv = F.shape
        FM = face_mask(D, F, is_skin, is_hair)
        Z, pj = view_depth(Q, Ik, cam, Wv, Hv); u, v, dep = pj(p)
        ui, vi = np.clip(np.round(u).astype(int), 0, Wv - 1), np.clip(np.round(v).astype(int), 0, Hv - 1)
        t = np.radians(cam['yaw']); facing = n @ np.array([np.sin(t), 0, np.cos(t)])
        vis = (dep >= Z[vi, ui] - SEEN) & (facing > MIN_FACING) & (u >= 0) & (u < Wv - 1) & (v >= 0) & (v < Hv - 1)
        seen_any |= vis
        ok = vis & (F[vi, ui] if paint_all else FM[vi, ui])   # (all of the figure: its hair and its lines too)
        x0, y0 = np.clip(np.floor(u).astype(int), 0, Wv - 2), np.clip(np.floor(v).astype(int), 0, Hv - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        col = (D[y0, x0] * (1 - fx) + D[y0, x0 + 1] * fx) * (1 - fy) + (D[y0 + 1, x0] * (1 - fx) + D[y0 + 1, x0 + 1] * fx) * fy
        w = np.where(ok, np.maximum(facing, 0) ** POW, 0.)
        if paint_all:   # (around the eyes the face first: where an image draws the face there, it wins over the hair the others draw)
            band = (p[:, 1] > eye_m - EYE_BAND[0]) & (p[:, 1] < eye_m + EYE_BAND[1])
            w = np.where(band & FM[vi, ui] & ok, w * FACE_PRIO + FACE_PRIO * 1e-9, w)
        w = w * zone if view == 'fronte' else w * (1 - zone)   # (the features: the front image's alone)
        if view == 'fronte': w = np.where(ok & (zone > 0), np.maximum(w, 1e-6 * zone), w)
        acc += w[:, None] * col; wsum += w
    painted = wsum > 0
    out[ys[sel[painted]], xs[sel[painted]]] = acc[painted] / wsum[painted, None]
    under = ~painted & seen_any & (n @ fwd > .3)   # (seen, but every image draws hair there: under the bangs)
    if sheet: out[ys[sel[under]], xs[sel[under]]] = UNDER   # (without the sheet: as it was, the skin with its shadows under Meshy's locks)
    print('face: %d texels painted from the images (%d of the features from the front one), %d under the bangs in the skin\'s shadow' % (
        int(painted.sum()), int((painted & (zone > .5)).sum()), int(under.sum())))
    if paint_bangs and not paint_all:   # the front image's bangs painted on the forehead's skin where the model shows it (from the front; paint_all does it with the others)
        FMf = face_mask(Dfr, Ffr, is_skin, is_hair)
        Z2, pj2 = view_depth(Q, Ik, fr, W, H); u, v, dep = pj2(p)
        ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
        seen = (dep >= Z2[vi, ui] - SEEN) & (n @ fwd > BANGS_FACING) & (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
        hair_px = Ffr[vi, ui] & ~FMf[vi, ui] & (p[:, 1] > eye_m - BANGS_LOW)
        k = seen & hair_px
        x0, y0 = np.clip(np.floor(u).astype(int), 0, W - 2), np.clip(np.floor(v).astype(int), 0, H - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        col = (Dfr[y0, x0] * (1 - fx) + Dfr[y0, x0 + 1] * fx) * (1 - fy) + (Dfr[y0 + 1, x0] * (1 - fx) + Dfr[y0 + 1, x0 + 1] * fx) * fy
        out[ys[sel[k]], xs[sel[k]]] = col[k]
        print('face: %d texels of the forehead painted with the front image\'s bangs' % int(k.sum()))
    if not sheet: return keep, None
    # the front image's bangs: a sheet in front of the face (its hair and the lines between its locks, over the face's skin)
    FMf = face_mask(Dfr, Ffr, is_skin, is_hair)
    Za, _ = view_depth(Q, Ik, fr, W, H)
    region = ndimage.binary_dilation(np.isfinite(Zs) & (Zs >= np.where(np.isfinite(Za), Za, -1e9) - .004), iterations=4)   # (where the face's skin is the front)
    ry = np.nonzero(region.any(1))[0]; rx = np.nonzero(region.any(0))[0]
    roots = np.zeros_like(region); roots[max(0, ry.min() - ROOTS):ry.min() + 1, rx.min():rx.max() + 1] = True
    bangs = (region | roots) & Ffr & ~FMf & ~is_skin(Dfr)
    bangs = ndimage.binary_opening(bangs, iterations=1)
    # (the sheet's points: a grid over them, each at the face's depth there plus GAP, or tucked behind the crown)
    bys, bxs = np.nonzero(bangs); x0, x1, y0, y1 = bxs.min() - GRID, bxs.max() + GRID, bys.min() - GRID, bys.max() + GRID
    gx = np.arange(x0, x1 + 1, GRID); gy = np.arange(y0, y1 + 1, GRID); GX, GY = np.meshgrid(gx, gy)
    gxi, gyi = np.clip(GX, 0, W - 1), np.clip(GY, 0, H - 1)
    zs = ndimage.grey_dilation(np.where(np.isfinite(Zs), Zs, -1e9), size=5)[gyi, gxi]; za = ndimage.grey_dilation(np.where(np.isfinite(Za), Za, -1e9), size=5)[gyi, gxi]
    on_skin = zs > -1e8; on_any = za > -1e8
    depth = np.where(on_skin & (zs >= za - .004), zs + GAP, za - TUCK)
    valid = on_any
    Pg = (right[None, None] * ((GX - fr['cx']) / fr['s'])[..., None] + up[None, None] * ((fr['by'] - GY) / fr['s'])[..., None] + fwd[None, None] * depth[..., None])
    valid &= np.abs(Pg[..., 0] - mid) < SIDE
    # cells: kept where they cover the bangs
    cov = ndimage.binary_dilation(bangs, iterations=GRID)
    tris = []; vid = -np.ones(GX.shape, int); verts = []
    for r in range(GX.shape[0] - 1):
        for c in range(GX.shape[1] - 1):
            cs = [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]
            if not all(valid[a] for a in cs): continue
            dz = [depth[a] for a in cs]
            if max(dz) - min(dz) > STEEP: continue   # (the face's sides seen edge-on: stretched cells, streaks from the side)
            cx_, cy_ = (GX[r, c] + GX[r, c + 1]) // 2, (GY[r, c] + GY[r + 1, c]) // 2
            if not cov[np.clip(cy_, 0, H - 1), np.clip(cx_, 0, W - 1)]: continue
            for a in cs:
                if vid[a] < 0: vid[a] = len(verts); verts.append(a)
            a, b, c2, d2 = (vid[q] for q in cs); tris += [(a, d2, b), (b, d2, c2)]   # (facing the camera)
    vr, vc_ = np.array([q[0] for q in verts]), np.array([q[1] for q in verts])
    sp = Pg[vr, vc_]; tw, th_ = x1 - x0, y1 - y0
    suv = np.c_[(GX[vr, vc_] - x0) / tw, (GY[vr, vc_] - y0) / th_]
    crop = Dfr[max(0, y0):y1, max(0, x0):x1]; pad = np.zeros((th_, tw, 3)); pad[max(0, y0) - y0:max(0, y0) - y0 + crop.shape[0], max(0, x0) - x0:max(0, x0) - x0 + crop.shape[1]] = crop
    al = np.zeros((th_, tw)); bm = bangs[max(0, y0):y1, max(0, x0):x1]; al[max(0, y0) - y0:max(0, y0) - y0 + bm.shape[0], max(0, x0) - x0:max(0, x0) - x0 + bm.shape[1]] = bm
    rgba = np.dstack([pad, al * 255]).clip(0, 255).astype(np.uint8)
    print('face: the front image\'s bangs a sheet of %d points, %d triangles (%d x %d px of it)' % (len(sp), len(tris), tw, th_))
    return keep, (sp, suv, np.array(tris, np.int64), rgba)
