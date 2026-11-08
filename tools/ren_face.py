#!/usr/bin/env python3
"""Ren's face painted from his sheet (8/11/2026, Denis after the version 31: "alcune parti del viso sono ancora fatte
male"): called by tools/ren_head.py, after tools/ren_fringe.py (its registration of the sheet's front view on the head).

Meshy's face paint is its own reading of the sheet: a thin spindle down the middle of the nose (the sheet: a line down
the nose's left side and its shadow), light scratches and dark specks on the cheeks, stray lines around the mouth.
Here every texel of the face (its triangles that are not hair) gets:
  - seen from the front (its point the frontmost of the face there, within VIS m) and facing it (the face's normal,
    from its smoothed depth, n_z over FRONT[0], full over FRONT[1]): the sheet's front view at its point (sheet_face:
    its features; the hair over the face, its shadows and the outlines of the face, the ears and the neck as plain skin:
    tools/ren_fringe.py draws the locks, the outline the face's edges);
  - elsewhere (the cheeks' sides, from the eyes to the ears, in front of EAR_Z): Meshy's paint without its marks (light
    grey scratches, purple specks, black streaks: each takes its nearest unmarked texel's colour);
  - between the two, both mixed.
The sheet's features kept as they are drawn (sheet_face; EYES, NOSE, MOUTH: boxes in the head's frame; the brows over
the eyes); elsewhere its skin, flat. Not on the neck (under the jaw's edge seen from the front: its depth drops by
JAW_DZ): Meshy's shading kept there.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

from ren_fringe import front_view, texels, SHEET, SHEET_FRONT, PX, X0, X1, Y0, Y1, BODY_X

FRONT = (.25, .45)            # the front weight's ramp over the face's normal z
VIS = .0015                   # a texel within that of the frontmost face surface (m) is seen from the front
FACE_Y = (1.497, 1.66)        # the face's triangles: their middle between these heights (m)
EAR_Z = .022                  # the cheeks' cleanup: in front of this (m; the ears are behind it)
BROW_Y = 1.6                  # above: the forehead (the locks' shadows kept)
EYES = (-.07, .08, 1.575, 1.605)                       # the sheet's features, boxes in the head's frame (x0, x1, y0, y1, m):
EYE_UP, EYE_WING = .0035, .0035                        # (around each eye: how far over it, how far out of its outer corner)
NOSE = (-.018, .022, 1.538, 1.577)                      # (under the locks' tips)
MOUTH = (-.026, .038, 1.526, 1.543)                     # (not the chin's outline under it)
FOREHEAD_X = .035                                       # the forehead's shadows: this far from the middle (the new locks')
JAW_DZ = .006                                           # the jaw's edge seen from the front: the depth drops by more than that
SKIN = (249, 182, 134)        # the sheet's skin (its median): the face's plain colour


def classes(w):
    """The sheet's colour classes (an h x w x 3 float image): skin, its shadow (brown), black, white, hair (purple)."""
    wi = w.astype(int); r, g, b = wi[..., 0], wi[..., 1], wi[..., 2]; lum = w.mean(2); sat = w.max(2) - w.min(2)
    skin = (r > 140) & (r - b > 55); brown = (r > 60) & (r - b > 25) & ~skin
    black = lum < 50; white = (w.min(2) > 185) & (sat < 35)
    purple = (lum >= 38) & (lum < 120) & ~skin & ~brown & (r - g >= 3) & (b - g >= 2) & (sat < 60)   # (the hair: dark, a little purple; not the eyes' greys)
    return skin, brown, black, white, purple


def sheet_face(K, U0, V0):
    """The sheet's front view as the face's paint, in its own pixels: its plain skin and its features kept (the eyes:
    whites, irises, lids, the lashes' wings at the outer corners; each brow: the thick black stroke over its eye, not the
    hair's; the nose's line and shadow; the mouth and the lip's shadow; the upper lids' shading; the new locks' shadows on
    the forehead), all else (the hair over the face and its shadows, the face's, ears' and neck's outlines, the side
    locks' shadows) the sheet's skin. Returns (image h x w x 3 float, the kept mask); its pixels map to the head's frame
    as u = (x - X0) / K + U0, v = (Y1 - y) / K + V0."""
    w = np.asarray(Image.open(SHEET).convert('RGB').crop(SHEET_FRONT)).astype(float); H, W = w.shape[:2]
    skin, brown, black, white, purple = classes(w)
    vv, uu = np.mgrid[0:H, 0:W]; X = X0 + (uu + .5 - U0) * K; Y = Y1 - (vv + .5 - V0) * K
    box = lambda b: (X > b[0]) & (X < b[1]) & (Y > b[2]) & (Y < b[3])
    px = lambda d: max(1, int(round(d / K)))
    near_p = ndimage.distance_transform_edt(~purple) * K <= .001
    plain = np.sqrt(((w - np.array(SKIN)) ** 2).sum(2)) < 30          # (the skin's own colour)
    shade = (skin | brown) & ~plain & (w.mean(2) < np.mean(SKIN) - 8)   # (its shadows: darker than it)
    keep = plain.copy()
    wb = white & box(EYES); lab, n = ndimage.label(ndimage.binary_closing(wb, iterations=2))
    for L in np.argsort(-ndimage.sum(wb, lab, range(1, n + 1)))[:2] + 1:
        ys, xs = np.nonzero(lab == L); eye = np.zeros((H, W), bool)
        for y in range(ys.min(), ys.max() + 1):   # (filled between its whites, by rows and by columns: the iris too)
            r = xs[ys == y]
            if len(r): eye[y, r.min():r.max() + 1] = True
        for x in range(xs.min(), xs.max() + 1):
            r = ys[xs == x]
            if len(r): eye[r.min():r.max() + 1, x] = True
        eye = ndimage.binary_fill_holes(ndimage.binary_closing(eye, iterations=px(.0015)))
        ex0, ex1, ey1 = X[eye].min(), X[eye].max(), Y[eye].max(); out = -1 if (ex0 + ex1) / 2 < BODY_X else 1   # (its outer side)
        ym = Y[eye].mean(); inx = (X > ex0 - .0005) & (X < ex1 + .0005)
        # all that is drawn around it (not the plain skin, not the hair): over it the lid's grey shadow, the thick lash
        # line, the lid's shading up to EYE_UP; under it the lower lid's line; out of its outer corner the lashes' wing;
        # not past its inner corner (the locks' tips hang there)
        xin = (X - (ex0 if out > 0 else ex1)) * out > -.0005; xout = (X - (ex1 if out > 0 else ex0)) * out < EYE_WING
        zone = np.where(Y > ym, ndimage.binary_dilation(eye, iterations=px(EYE_UP)), ndimage.binary_dilation(eye, iterations=px(.0013))) & xin & xout
        keep |= (eye & ~purple) | (zone & ~plain & ~purple)
        # its brow: the biggest thick black stroke (not the hair's) over it
        reg = (X > ex0 - .008) & (X < ex1 + .008) & (Y > ey1 + .001) & (Y < ey1 + .016)
        thick = ndimage.binary_opening(black & reg & ~near_p & ~zone, iterations=2); lab3, n3 = ndimage.label(thick)
        if n3:
            brow = lab3 == np.argmax(ndimage.sum(thick, lab3, range(1, n3 + 1))) + 1
            keep |= ndimage.binary_dilation(brow, iterations=3) & black & ~near_p & reg
    keep |= (black | shade) & box(NOSE) & ~near_p                                         # the nose's line, its shadow, the nostril
    lab, n = ndimage.label(black); mb = black & box(MOUTH)                                   # the mouth, the lip's shadow: not the
    big = np.isin(lab, np.unique(lab[black & ~box(MOUTH) & ndimage.binary_dilation(box(MOUTH), iterations=2)]))   # chin's outline (it runs on out of the box)
    keep |= (mb & ~big) | (shade & box(MOUTH))
    keep |= shade & (np.abs(X - BODY_X) < FOREHEAD_X) & (Y > BROW_Y) & ~near_p            # the new locks' shadows on the forehead
    out = w.copy(); out[~keep | plain] = SKIN   # (the plain skin flat: no stray tones along the outlines)
    return out, keep


def face_paint(t, Q, N, UV, I, reg):
    """See above. t: the head's texture (h x w x 3 float, painted in place); Q, N, UV, I: the head (its triangles kept);
    reg: (K, U0, V0), the sheet's front view on the head (tools/ren_fringe.py). Returns (texels from the sheet, cleaned)."""
    K, U0, V0 = reg; P = Q.astype(float); UV = UV.astype(float); I = np.asarray(I).astype(np.int64); TS = t.shape[0]
    t8 = np.clip(t, 0, 255).astype(np.uint8)
    c = t8[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)].astype(int)
    mc = c.mean(1); hairv = (mc >= 38) & (mc < 110) & (c[:, 0] >= c[:, 1] + 4) & (c[:, 2] >= c[:, 1] + 2) & (c[:, 0] - c[:, 2] < 25)
    teal = (c[:, 1] > c[:, 0] + 10) & (c[:, 2] > c[:, 0] + 10); trim = (c.min(1) > 140) & (c[:, 0] - c[:, 2] > 15) & (c[:, 0] - c[:, 2] < 60) & (c[:, 0] < 225)
    C = P[I].mean(1)
    face_t = (hairv[I].sum(1) < 2) & ~(teal[I].any(1)) & ~(trim[I].sum(1) >= 2) & (C[:, 1] > FACE_Y[0]) & (C[:, 1] < FACE_Y[1]) & (C[:, 2] > -.03)
    # the face from the front: its depth (the frontmost of the face's triangles), its normal z from that depth, smoothed
    _, z, _, _ = front_view(P, UV, I[face_t], t8, N)
    H, W = z.shape; ok = np.isfinite(z)
    _, (gy, gx) = ndimage.distance_transform_edt(~ok, return_indices=True); zf = z[gy, gx]
    dzy, dzx = np.gradient(ndimage.gaussian_filter(zf, 6), PX); nz = 1 / np.sqrt(1 + dzx ** 2 + dzy ** 2)
    # the jaw's edge seen from the front: per column, the first drop of the depth by more than JAW_DZ going down from
    # the mouth (the chin over the neck); under it the neck keeps Meshy's shading
    jaw = np.full(W, -np.inf); r0, r1 = int((Y1 - 1.56) / PX), int((Y1 - 1.48) / PX)
    for j in range(W):
        col = z[r0:r1, j]; d = col[:-1] - np.where(np.isfinite(col[1:]), col[1:], -1.)
        hit = np.nonzero(np.isfinite(col[:-1]) & (d > JAW_DZ))[0]
        if len(hit): jaw[j] = Y1 - (r0 + hit[0] + 1) * PX
    src, keep = sheet_face(K, U0, V0)
    def at(img, p):   # the frame's image at the points p (x, y)
        return ndimage.map_coordinates(img, [(Y1 - p[:, 1]) / PX - .5, (p[:, 0] - X0) / PX - .5], order=1, mode='nearest')
    def jaw_at(p): return jaw[np.clip(((p[:, 0] - X0) / PX).astype(int), 0, W - 1)]
    n_front = n_clean = 0
    for k in np.nonzero(face_t)[0]:
        q, p = texels(UV[I[k]] * TS, P[I[k]], TS)
        if not len(q): continue
        vis = (np.abs(p[:, 2] - at(zf, p)) < VIS) & (p[:, 1] > jaw_at(p) - .0005)
        wf = np.clip((at(nz, p) - FRONT[0]) / (FRONT[1] - FRONT[0]), 0, 1) * vis
        cur = t[q[:, 1], q[:, 0]].astype(float)
        if wf.any():
            u = (p[:, 0] - X0) / K + U0 - .5; v = (Y1 - p[:, 1]) / K + V0 - .5
            s = np.stack([ndimage.map_coordinates(src[..., m], [v, u], order=3, mode='nearest') for m in range(3)], 1).clip(0, 255)
            t[q[:, 1], q[:, 0]] = cur * (1 - wf[:, None]) + s * wf[:, None]; n_front += int((wf > 0).sum())
    # the cheeks' sides: Meshy's marks out (in front of the ears, the texels not fully from the sheet)
    mask = np.zeros(t.shape[:2], bool); side = np.zeros(t.shape[:2], bool)
    for k in np.nonzero(face_t & (C[:, 2] > EAR_Z))[0]:
        q, p = texels(UV[I[k]] * TS, P[I[k]], TS)
        if not len(q): continue
        vis = (np.abs(p[:, 2] - at(zf, p)) < VIS) & (p[:, 1] > jaw_at(p) - .0005); wf = np.clip((at(nz, p) - FRONT[0]) / (FRONT[1] - FRONT[0]), 0, 1) * vis
        mask[q[:, 1], q[:, 0]] = True; side[q[(wf < .999) & (p[:, 1] > jaw_at(p) + .002), 1], q[(wf < .999) & (p[:, 1] > jaw_at(p) + .002), 0]] = True
    ti = t.astype(int); r, g, b = ti[..., 0], ti[..., 1], ti[..., 2]; lum = t.mean(2)
    scratch = (lum > 185) & (r - b < 80)                      # (light grey: Meshy's highlights, the sheet's lines lost)
    speck = (b >= g - 2) & (lum < 150)                          # (purple: the hair's colour on the skin)
    streak = lum < 70                                           # (black)
    bad = side & (scratch | speck | streak)
    good = mask & ~bad
    if bad.any() and good.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True); t[bad] = t[iy[bad], ix[bad]]; n_clean = int(bad.sum())
    # the texels along the face's UV pieces' edges (touched by its triangles but no texel's middle in them: filtering
    # samples them at the seams, they kept Meshy's old colours, thin lines across the face) take their nearest painted
    # one's colour, if nearer the face's pieces than any other's
    from PIL import ImageDraw
    cover = np.zeros(t.shape[:2], bool)
    for k in np.nonzero(face_t)[0]:
        q, _ = texels(UV[I[k]] * TS, P[I[k]], TS); cover[q[:, 1], q[:, 0]] = True
    oth = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(oth)
    for tri in UV[I[~face_t]] * TS: dr.polygon([tuple(v) for v in tri], fill=255)
    other = np.asarray(oth) > 0
    d_face, (fy, fx) = ndimage.distance_transform_edt(~cover, return_indices=True); d_other = ndimage.distance_transform_edt(~other)
    stale = ~cover & (d_face <= 2.5) & (d_face < d_other)
    t[stale] = t[fy[stale], fx[stale]]
    return n_front, n_clean
