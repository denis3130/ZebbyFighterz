#!/usr/bin/env python3
"""Kael's face painted from Denis's head sheet (10/11/2026; Denis: "la faccia fa ancora schifo", "no per la testa fai tu
niente meshy"; docs/ref/personaggi/kael_testa_3viste.png: his right side, front, his left side), on Meshy's head as it
is (its shape untouched), in flat light (the sheet's own shading, as Ren's head).

- The face: the head's texels on its surface seen from the front (kael_fix.face_depth: the face behind the hair), from
  the collar up (FACE_Y), its skin, its lines, the whites of its eyes (light texels near the eyes only: elsewhere a
  light texel on the face is a lock of hair lying on it); and the rest of the head's skin (the jaw's underside, the
  neck, the face's sides, under the locks) with the dark strokes it surrounds (HOLE; small pieces, HOLE_MAX: not the
  collar's black by the neck) and Meshy's warm brown strokes; never the collar (COLLAR_Y: its purple, its lavender
  highlights, its black), whatever its texels' bones
  and highlights on it (WARM: the hair's lavender and white are cool); not the hair, the earrings, the collar.
- Each panel's camera: orthographic, turned by a yaw (the one whose view of the face's landmarks, its eyes, nose tip,
  mouth and chin, MODEL, best matches the panel's, MARKS: a scale and a shift across, YAW_RANGE), and from the model's
  landmarks to the panel's: across by that scale and shift, down piecewise through the eyes, the nose, the mouth and
  the chin (the sheet's face is longer below the mouth than Meshy's: its features land on the model's), then a
  thin-plate spline exact at the landmarks (in three quarters the sheet's nose stands out more than Meshy's), held to
  the first map ANCHOR px around.
- A panel's colour: inside its face (the skin with the lines, eyes and shadows inside it; not the locks of hair lying
  over it with their outlines, LOCK_EDGE, nor the ears and earrings) as drawn, its skin's shadows only by the nose and
  the mouth and under the chin (KEEP_SHADE: the others are the drawn locks' shadows, the locks elsewhere on the model;
  as Ren's face, clean skin with the drawing's features); his right half above the nose the mirror image of his left
  half (MIRROR: the front panel draws a lock over his right brow and eye); outside it the nearest of its face's colours
  from EDGE_IN inside it.
- Sharp (CEL): the drawing's face in its own flat colours (CEL_PAL, its dark lines its black), each texel the colour of
  its nearest pixel (the drawing resampled to the texture had soft, blurred eyes and brows).
- The views on a texel: the one it faces most (SHARP; the front's lead FRONT_BIAS: the three quarters panels only on the
  face's sides), where it sees it; by how much it faces it (FACE) over the drawing's skin in light (BASE). Only the
  PANELS paint (now the front: the three quarters ones, fitted and mapped all the same, put their cheeks' shadows
  elsewhere than the front's, in stripes where they met; the face's sides are the skin in light, as Ren's).
- The jaw's black V line (JAW_V), as the drawings': along the jaw's lower edge seen from the front, on the face's front
  surface (the 3D outline is pushed behind the body and draws no inner lines). (Painting the jaw's underside black
  instead read as a goatee.)
- The collar's specks (COLLAR_SPECK: Meshy's skin-coloured bits on its purple and black by the neck) in its colours.
- The whole face flat lit (its shading is the sheet's), but the jaw's underside and the neck under it (UNDER): in the
  toon light's shadow, as Ren's, the jaw's line over them reads as the jaw.

usage: python3 tools/kael_face.py PACKAGE_DIR [DEBUG_DIR]   (after tools/kael_fix.py: paints PACKAGE_DIR/kael_painted.jpg
over in place, the face's flat light into PACKAGE_DIR/kael_look.bin; DEBUG_DIR: each panel with the model's landmarks
mapped onto it, and the yaw search)"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, sparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
from kael_fix import load, classes, face_depth
from paint_views import texel_table, seen_ids
import sheet_scan

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SHEET = os.path.join(ROOT, 'docs', 'ref', 'personaggi', 'kael_testa_3viste.png')
# the sheet's landmarks (px): his right eye's and his left eye's irises, the nose's tip, the mouth's middle, the chin
MARKS = {'his left side': {'eyes': ((320., 255.), (388.3, 246.7)), 'nose': (318., 295.), 'mouth': (360., 321.7), 'chin': (346.7, 363.3)},
         'front': {'eyes': ((1072.4, 252.5), (1161.2, 252.6)), 'nose': (1115., 299.), 'mouth': (1118., 322.), 'chin': (1118., 366.)},
         'his right side': {'eyes': ((1860., 240.), (1927.7, 249.)), 'nose': (1930., 285.), 'mouth': (1895., 316.7), 'chin': (1913.3, 360.)}}
YAW_RANGE = {'his left side': (15., 50.), 'front': (-6., 6.), 'his right side': (-50., -15.)}   # deg (+: his left side seen)
# the model's (m, the bind pose with the look's shape; z: its front-most surface there)
MODEL = {'eyes': ((-.0294, 1.5946), (.0385, 1.5947)), 'nose': (.004, 1.560), 'mouth': (.004, 1.543), 'chin': (.006, 1.5225)}
FACE_BOX, FACE_Y, SURF, EYE_R = (-.09, .09, 1.47, 1.72), 1.508, .004, .013   # m: the raycast's box; the collar's top; on the surface; an eye's white
HOLE, HOLE_CELL, HOLE_SKIN = .015, .003, .6   # m: a dark texel's neighbourhood, its cells; the share of skin in it
HOLE_MAX = 1500                               # texels: a dark stroke's piece at most (the collar's black is bigger)
COLLAR_Y = 1.53                               # m: under this, purple and big black pieces are the collar's, never the face's
NECK = (1.545, .055, .015, 400)               # the neck's sides (y under, z under, |x| over, m): dark pieces touching its skin,
                                              # under this many texels, are Meshy's strokes: skin
COLLAR_SPECK = 400                            # texels: a speck of another colour on the collar at most (it takes the collar's)
WARM = 25                                     # red over blue: a warm colour (skin's), not the hair's
LIGHT_SKIN = .6                               # a light texel that much skin surrounds: Meshy's light strokes, not a lock
CHIN_LIGHT = (1.54, .075)                      # m: under the mouth (y under, |x| under) no hair: its light texels are skin's
EYE_ZONE = (.022, .010, .024)                 # m: around an iris (|dx| under, dy from -, to +: the brow): the face's light texels
CEL, CEL_LINE = True, 70                     # the drawing's face in its flat colours; its lines (lightness under) black
CEL_PAL = ((14, 12, 12), (248, 186, 140), (248, 200, 154), (166, 112, 82), (240, 240, 242), (170, 100, 190),
           (128, 72, 156), (60, 30, 80), (108, 84, 108), (226, 212, 226), (130, 112, 138))   # (the head sheet's)
CEL_KEEP = 4                                  # (CEL_PAL's white: the irises' highlights, never a speck)
CONTOUR = 7                                   # px: the drawn face's outline at its edge (left to the 3D outline)
UNDER = (-.1, 1.56, .2, .002)                 # under the jaw's line seen from the front (to this over it, m; facing down: n.y under;
                                              # y under): toon light, not flat (n.z: unused)
NOSE_KEEP = (9, 30, 7)                        # px around the drawn nose's tip (|dx| under; up to, down to): its shadow kept, a band
                                              # along it (Meshy's nose is flatter: the drawn shadow beside it fell on the cheek)
NOSE_SIDE = (.35, .022, .035)                 # the nose's sides (|n.x| over; |dx| under, up to dy over the tip, m): no shadow
JAW_PAINT = False                             # the jaw's line painted (off: the outline draws it, kael_fix HEAD_BACK; painted, a
                                              # black stripe down the cheek seen from the side)
JAW_V, JAW_BLACK = (.005, .002, .045, 1.56, .075), (14., 13., 15.)   # m: the jaw's line (its height, its columns' width, the
                                              # face's front: z over, y under, |x| under); its black
                                              # (as kael_fix's HAIR_SKIN: the hair is the rest)
FRONT_BIAS = .2                               # n . d: the front panel's lead (it paints the face until it turns ~35 deg)
LOCK_EDGE, EYE_KEEP = 5, 22.                  # px: a lock over the drawn face left out with this much around it (its
                                              # outline); but not within this of an eye
SHADE_L, KEEP_SHADE = 165, (26., 16.)         # the drawn skin's shadow (lightness under); px around the nose, the mouth kept
MIRROR, NOSE_STRIP = ('front',), 16          # the panels whose right half above the nose is their left half's mirror
                                              # (but px by the nose, below the eyes, as drawn: its shadow)
PANELS = ('front',)                           # the panels that paint (the three quarters ones shade the cheeks otherwise:
                                              # their shadows fall elsewhere than the front's, in stripes where they meet)
FACE, SHARP, CLOSE, EDGE_IN, ANCHOR = (.3, .6), 40., 6, 3, 110.


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def disk(r):
    a = np.arange(-r, r + 1); return np.add.outer(a * a, a * a) <= r * r


def marks3d(P, I, hw, skin_tri=None):
    """The model's landmarks in 3D: MODEL's x, y and the front-most face surface's z there."""
    import glbio
    zf = face_depth(P, I, hw, *FACE_BOX, 120)
    pts = [MODEL['eyes'][0], MODEL['eyes'][1], MODEL['nose'], MODEL['mouth'], MODEL['chin']]
    T = I[(hw[I] > .3).all(1)]; out = []
    cx_, cy = pts[4]   # (the chin: the skin's lowest point in front there, wherever the shape put it; not the collar)
    Ts = I[(hw[I] > .3).all(1) & (skin_tri if skin_tri is not None else True)]
    for y in np.arange(cy + .01, cy - .03, -.0005):
        if any(h[0] > JAW_V[2] for h in glbio.raycast_z(P, Ts, [cx_], [y])[0]): pts[4] = (cx_, y)
        elif y < cy: break
    for k, (x, y) in enumerate(pts):   # (the nose's tip and the chin: the front-most hit; the eyes and the mouth: the face
        hits = [h[0] for h in glbio.raycast_z(P, T, [x], [y])[0] if h[0] > .02]   # behind the hair)
        out.append((x, y, max(hits) if k in (2, 4) and hits else float(zf(np.array([[x, y, 0.]]))[0])))
    return np.array(out)


def cel(D, M):
    """The drawing's face (D, inside the mask M) in its own flat colours (CEL_PAL: its skin in light and in shadow, its
    black lines, the eyes' whites, the irises' purples and their dark ring, the brows', the hair's over the face): each
    pixel the nearest of them, its dark ones (CEL_LINE) black; then each pixel unlike most of its 8 neighbours their
    colour (specks). The edges sharp. D outside M as it is."""
    pal = np.array(CEL_PAL, float); px = D[M]; L = px.mean(1)
    lab = ((px[:, None, :] - pal[None]) ** 2).sum(2).argmin(1); lab[L < CEL_LINE] = 0   # (CEL_PAL[0]: the black)
    key = np.full(D.shape[:2], -1); key[M] = lab
    best = np.zeros(D.shape[:2]); arg = key.copy()
    for k in range(len(pal)):
        c = ndimage.uniform_filter((key == k).astype(float), 3)
        up = c > best; best[up] = c[up]; arg[up] = k
    lone = M & (best * 9 >= 5) & (arg != key) & (key != CEL_KEEP); key[lone] = arg[lone]   # (not the irises' highlights)
    O = D.copy(); O[M] = pal[key[M]]
    return O


def mapping(src, dst):
    """From the model's projected landmarks (5 x 2: eyes, nose, mouth, chin) to the panel's: x by a scale and a shift (least
    squares over all five), y piecewise linear through the eyes' middle, the nose, the mouth and the chin. -> f(u, v), residual."""
    A = np.stack([src[:, 0], np.ones(5)], 1); (a, b), *_ = np.linalg.lstsq(A, dst[:, 0], rcond=None)
    res = np.sqrt(np.mean((A @ [a, b] - dst[:, 0]) ** 2))
    ys = np.array([src[:2, 1].mean(), src[2, 1], src[3, 1], src[4, 1]]); yd = np.array([dst[:2, 1].mean(), dst[2, 1], dst[3, 1], dst[4, 1]])
    o = np.argsort(ys); ys, yd = ys[o], yd[o]
    def f(u, v):
        q = np.interp(v, ys, yd)
        lo, hi = v < ys[0], v > ys[-1]   # (beyond: the end segments' slopes)
        q[lo] = yd[0] + (v[lo] - ys[0]) * (yd[1] - yd[0]) / (ys[1] - ys[0])
        q[hi] = yd[-1] + (v[hi] - ys[-1]) * (yd[-1] - yd[-2]) / (ys[-1] - ys[-2])
        return a * u + b, q
    return f, res, (a, b)


def tps(src, dst):
    """A thin-plate spline from src (n x 2) to dst (n x 2): exact at its points. -> f(u, v) -> (x, y)."""
    n = len(src); U = lambda r2: np.where(r2 > 0, r2 * np.log(np.maximum(r2, 1e-12)) / 2, 0)   # (r^2 log r)
    A = np.zeros((n + 3, n + 3)); A[:n, :n] = U(((src[:, None] - src[None]) ** 2).sum(2))
    Pm = np.hstack([np.ones((n, 1)), src]); A[:n, n:] = Pm; A[n:, :n] = Pm.T
    b = np.zeros((n + 3, 2)); b[:n] = dst; c = np.linalg.solve(A, b); w, a = c[:n], c[n:]
    def f(u, v):
        p = np.stack([u, v], 1); q = U(((p[:, None] - src[None]) ** 2).sum(2)) @ w + a[0] + p @ a[1:]
        return q[:, 0], q[:, 1]
    return f


def main(pkg, debug=None):
    name, m, P, N, UV, I, jn, wn, lj, LB = load(pkg)
    if 'move' not in lj or 'nor' not in lj: sys.exit('run tools/kael_fix.py first')
    mv = lj['move']; mi = np.frombuffer(LB, np.uint16, mv['idx'][1], mv['idx'][0]).astype(np.int64)
    P[mi] = np.frombuffer(LB, np.float32, mv['pos'][1], mv['pos'][0]).reshape(-1, 3)
    NL = np.frombuffer(LB, np.float32, lj['nor'][1], lj['nor'][0]).reshape(-1, 3).astype(np.float64)
    flat = np.frombuffer(LB, np.float32, lj['flat'][1], lj['flat'][0]).astype(np.float64).copy()
    bi = {b['n']: i for i, b in enumerate(m['bones'])}; hw = ((jn == bi['Head']) * wn).sum(1)
    tp = os.path.join(pkg, name + '_painted.jpg')
    T = np.asarray(Image.open(tp).convert('RGB')).astype(np.float64); TS = T.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(P, NL, UV, I, TS)
    th = (hw[I[ks]] * bary).sum(1)
    zf = face_depth(P, I, hw, *FACE_BOX, 120)(pos)
    onf = (th > .5) & ~np.isnan(zf) & (np.abs(pos[:, 2] - np.nan_to_num(zf, nan=-9)) < SURF) & (pos[:, 1] > FACE_Y)
    uc = UV[I].mean(1); tcol = T[np.clip((uc[:, 1] * TS).astype(int), 0, TS - 1), np.clip((uc[:, 0] * TS).astype(int), 0, TS - 1)]
    cl = classes(T[ys, xs]); M3 = marks3d(P, I, hw, classes(tcol) == 2)
    near_eye = np.zeros(len(pos), bool)   # (the eyes and the brows above them: their light texels are the face's)
    for k in (0, 1):
        dx, dy = pos[:, 0] - M3[k, 0], pos[:, 1] - M3[k, 1]
        near_eye |= (np.abs(dx) < EYE_ZONE[0]) & (dy > -EYE_ZONE[1]) & (dy < EYE_ZONE[2])
    # and off that surface (the jaw's underside, the neck under it, the face's sides by the ears, the forehead under the
    # locks): the head's skin, and the dark texels skin surrounds (Meshy's strokes: in a HOLE-wide neighbourhood, at
    # least HOLE_SKIN of it skin); not the hair (light, or its lavender shading: not skin), the earrings, the collar
    head = (th > .5) & (pos[:, 1] > FACE_Y); sk = head & (cl == 2)
    g = np.floor(pos / HOLE_CELL).astype(np.int64); g -= g[head].min(0); shp = tuple(g[head].max(0) + 1)
    Sk = np.zeros(shp, np.float32); Al = np.zeros(shp, np.float32); np.add.at(Sk, tuple(g[sk].T), 1); np.add.at(Al, tuple(g[head].T), 1)
    kk = int(round(HOLE / HOLE_CELL)) | 1; Sk = ndimage.uniform_filter(Sk, kk); Al = ndimage.uniform_filter(Al, kk)
    gi = tuple(np.clip(g, 0, np.array(shp) - 1).T); share = np.where(head, Sk[gi] / np.maximum(Al[gi], 1e-6), 0)
    tc = T[ys, xs]; warm = tc[:, 0] - tc[:, 2] > WARM   # (Meshy's brown strokes and the skin's light: warm; the hair's lavender and white: not)
    DK = np.zeros((TS, TS), bool); DK[ys, xs] = head & (cl == 0); lab, n = ndimage.label(DK)   # (a dark stroke: a small piece;
    small = (np.bincount(lab.ravel()) < HOLE_MAX)[lab[ys, xs]]                                 # not the collar's black)
    reg = (onf & (np.isin(cl, (0, 2)) | ((cl == 4) & warm) | ((cl == 3) & near_eye))) | sk | (head & (cl == 0) & (share > HOLE_SKIN) & small) | (head & warm & ((cl == 4) | ((cl == 3) & (share > HOLE_SKIN)))) | (head & (cl == 3) & (share > LIGHT_SKIN)) | (head & (cl == 3) & (pos[:, 1] < CHIN_LIGHT[0]) & (np.abs(pos[:, 0]) < CHIN_LIGHT[1]))
    # (the neck's sides: Meshy's dark strokes on its skin, under the jaw; not the collar's black, a big piece)
    NK = np.zeros((TS, TS), bool); NK[ys, xs] = head & (cl == 0) & (pos[:, 1] < NECK[0]) & (pos[:, 2] < NECK[1]) & (np.abs(pos[:, 0]) > NECK[2])
    lab, n = ndimage.label(NK); szn = np.bincount(lab.ravel()); SKm = np.zeros((TS, TS), bool); SKm[ys, xs] = sk
    tch = np.zeros(n + 1, bool); np.logical_or.at(tch, lab[ndimage.binary_dilation(SKm, iterations=3) & NK], True)
    neck = ((szn < NECK[3]) & tch)[lab[ys, xs]] & (lab[ys, xs] > 0)
    reg |= neck
    collar = (pos[:, 1] < COLLAR_Y) & ((tc[:, 2] > tc[:, 1] + 30) | ((cl == 0) & ~small & ~neck))   # (its purple and its black)
    reg &= ~collar
    R = np.nonzero(reg)[0]
    print('the face: %d texels; the model\'s landmarks (m):' % len(R), np.round(M3, 4).tolist())
    nt = len(I)
    _, wid = np.unique(np.round(P * 1e5).astype(np.int64), axis=0, return_inverse=True); wid = wid.ravel()
    inc = sparse.csr_matrix((np.ones(I.size), (np.repeat(np.arange(nt), 3), wid[I].ravel())), shape=(nt, wid.max() + 1))
    adj = (inc @ inc.T).tocsr()
    D = np.asarray(Image.open(SHEET).convert('RGB')).astype(np.float64); H, W = D.shape[:2]
    dc = sheet_scan.classes(D)
    scan = json.load(open(os.path.join(ROOT, 'docs', 'meshy', 'kael_scan.json')))['kael_testa_3viste.png']
    Sc = np.full((3, len(R)), -np.inf); Co = np.zeros((3, len(R), 3)); dirs = []
    dbg = D.copy() if debug else None
    for vi, (vname, cam) in enumerate(zip(MARKS, scan)):
        mk = MARKS[vname]; dst = np.array([mk['eyes'][0], mk['eyes'][1], mk['nose'], mk['mouth'], mk['chin']])
        s, cx, by = cam['s'], cam['cx'], cam['by']
        best = None
        for yaw in np.arange(YAW_RANGE[vname][0], YAW_RANGE[vname][1] + 1e-9, .5):   # (the yaw whose landmarks fit best)
            t = np.radians(yaw); r = np.array([np.cos(t), 0, -np.sin(t)])
            src = np.stack([cx + s * (M3 @ r), by - s * M3[:, 1]], 1)
            f, res, ab = mapping(src, dst)
            if best is None or res < best[0]: best = (res, yaw, f, ab)
        res, yaw, f0, ab = best; t = np.radians(yaw)
        # then exact at the landmarks (a thin-plate spline through them and, ANCHOR px around, the piecewise map's points)
        src = np.stack([cx + s * (M3 @ np.array([np.cos(t), 0, -np.sin(t)])), by - s * M3[:, 1]], 1)
        an = src.mean(0) + ANCHOR * np.stack([np.cos(np.arange(8) * np.pi / 4), np.sin(np.arange(8) * np.pi / 4)], 1)
        f = tps(np.vstack([src, an]), np.vstack([dst, np.stack(f0(an[:, 0], an[:, 1]), 1)]))
        r, d = np.array([np.cos(t), 0, -np.sin(t)]), np.array([np.sin(t), 0, np.cos(t)]); dirs.append(d)
        print('%s: yaw %.1f deg, across x %.3f %+.1f px (landmarks off by %.1f px across)' % (vname, yaw, ab[0], ab[1], res))
        # the panel's face: its biggest skin piece by the landmarks, with what is inside it; the hair over it left out
        x0, y0, x1, y1 = cam['box']; Dv, dcv = D, dc
        if vname in MIRROR:   # (his right half above the nose: his left half's mirror image, clean of the locks drawn over it)
            xc = (dst[0][0] + dst[1][0]) / 2; ytop = int(dst[2][1] - 8); Dv = D.copy()
            cols = np.arange(x0, int(xc)); src_x = np.clip(np.round(2 * xc - cols).astype(int), 0, W - 1)
            wgt = np.clip((xc - cols) / 4., 0, 1)[None, :, None]   # (blended over the last 4 px by the middle)
            Dv[y0:ytop, x0:int(xc)] = D[y0:ytop][:, src_x] * wgt + D[y0:ytop, x0:int(xc)] * (1 - wgt)
            ey = int((dst[0][1] + dst[1][1]) / 2 + 12); nx = int(xc - NOSE_STRIP)   # (the nose's shadow down its side as drawn)
            Dv[ey:ytop, nx:int(xc) + 1] = D[ey:ytop, nx:int(xc) + 1]
            dcv = sheet_scan.classes(Dv)
        sk = (dcv == 1); sk[:, :x0] = False; sk[:, x1:] = False
        lab, n = ndimage.label(ndimage.binary_closing(sk, structure=disk(2)))
        mid = dst.mean(0).round().astype(int); ov = np.bincount(lab[mid[1] - 15:mid[1] + 15, mid[0] - 15:mid[0] + 15].ravel(), minlength=n + 1); ov[0] = 0
        face = ndimage.binary_fill_holes(ndimage.binary_closing(lab == np.argmax(ov), structure=disk(CLOSE)))
        ring = ndimage.binary_dilation(face, iterations=2) & ~face
        lab_all, _ = ndimage.label(dcv == 2); outside_ids = np.unique(lab_all[ring & (dcv == 2)]); outside_ids = outside_ids[outside_ids > 0]
        yy, xx = np.mgrid[0:H, 0:W]   # (the eyes are the face's: their whites can touch a lock, and then the face is open there)
        eyes = (np.hypot(xx - dst[0][0], yy - dst[0][1]) < EYE_KEEP) | (np.hypot(xx - dst[1][0], yy - dst[1][1]) < EYE_KEEP)
        face |= eyes
        locks = face & np.isin(lab_all, outside_ids) & ~eyes   # (light pixels joined to the hair outside the face: locks over it)
        Dm = face & ~(ndimage.binary_dilation(locks, iterations=LOCK_EDGE) & ~eyes)   # (with their outlines)
        # the skin's shadows: only the nose's, the lip's and the one under the chin (the others are the drawn locks' shadows,
        # and the locks are elsewhere on the model)
        Dk = Dv.copy(); light = np.median(Dv[(dcv == 1) & face & (Dv.mean(2) > 180)], 0)
        nz, mo, ch = dst[2], dst[3], dst[4]
        keep = ((np.abs(xx - nz[0]) < NOSE_KEEP[0]) & (yy > nz[1] - NOSE_KEEP[1]) & (yy < nz[1] + NOSE_KEEP[2])) | (np.hypot(xx - mo[0], yy - mo[1]) < KEEP_SHADE[1]) | (yy > ch[1] - 4)
        shade = face & (dcv == 1) & (Dv.mean(2) < SHADE_L) & ~keep; Dk[shade] = light
        # (the drawn face's own outline, its black at its edge: skin; the 3D outline draws it, at the model's edge)
        rim = Dm & (Dk.mean(2) < CEL_LINE + 30) & (ndimage.distance_transform_edt(Dm) < CONTOUR)
        Dk[rim] = light
        if CEL: Dk = cel(Dk, Dm)   # (the drawing's flat colours, its edges sharp: no blur from the resampling)
        Din = ndimage.binary_erosion(Dm, iterations=EDGE_IN)
        _, (iy, ix) = ndimage.distance_transform_edt(~Din, return_indices=True); Dc = np.where(Dm[..., None], Dk, Dk[iy, ix])
        # the face's texels this panel sees, facing it
        u, v = cx + s * (P @ r), by - s * P[:, 1]
        seen = seen_ids(P, I, np.ones(nt, bool), u, v, P @ d, H, W)
        pr = pos[R]; pu = cx + s * (pr @ r); pv = by - s * pr[:, 1]
        inside = (pu >= 0) & (pu < W - 1) & (pv >= 0) & (pv < H - 1)
        pui, pvi = np.clip(pu.round().astype(int), 0, W - 1), np.clip(pv.round().astype(int), 0, H - 1)
        kr = ks[R]; fid = seen[pvi, pui]; vis = (fid == kr) & inside; o = np.nonzero(~vis & (fid >= 0) & inside)[0]
        vis[o] = np.asarray(adj[kr[o], fid[o]]).ravel() > 0
        face_n = nor[R] @ d; sel = vis & (face_n > FACE[0])
        qu, qv = f(pu[sel], pv[sel])
        if CEL:   # (the nearest pixel: its flat colour)
            Co[vi, sel] = Dc[np.clip(np.round(qv).astype(int), 0, H - 1), np.clip(np.round(qu).astype(int), 0, W - 1)]
        else:
            x0_ = np.clip(np.floor(qu).astype(int), 0, W - 2); y0_ = np.clip(np.floor(qv).astype(int), 0, H - 2)
            fx = np.clip(qu - x0_, 0, 1)[:, None]; fy = np.clip(qv - y0_, 0, 1)[:, None]
            Co[vi, sel] = Dc[y0_, x0_] * (1 - fx) * (1 - fy) + Dc[y0_, x0_ + 1] * fx * (1 - fy) + Dc[y0_ + 1, x0_] * (1 - fx) * fy + Dc[y0_ + 1, x0_ + 1] * fx * fy
        Sc[vi, sel] = face_n[sel]
        print('  %d face texels it sees (%d facing it well); %d px of its face (%d of locks over it left out)' % (int(sel.sum()), int((face_n[sel] > FACE[1]).sum()), int(Dm.sum()), int(locks.sum())))
        if debug:
            e = Dm & ~ndimage.binary_erosion(Dm, iterations=2); dbg[e] = (0, 200, 0)
            src = np.stack([cx + s * (M3 @ r), by - s * M3[:, 1]], 1); q = np.stack(f(src[:, 0], src[:, 1]), 1)
            im = Image.fromarray(dbg.astype(np.uint8)); dr = ImageDraw.Draw(im)
            for (a_, b_), (c_, d_) in zip(dst, q):
                dr.ellipse([a_ - 4, b_ - 4, a_ + 4, b_ + 4], outline=(255, 0, 0), width=2); dr.ellipse([c_ - 2, d_ - 2, c_ + 2, d_ + 2], fill=(0, 0, 255))
            dbg = np.asarray(im).astype(np.float64)
    if debug:
        os.makedirs(debug, exist_ok=True); Image.fromarray(dbg.astype(np.uint8)).crop((0, 100, W, 450)).save(os.path.join(debug, 'face_marks.png'))
    BASE = np.median(D[(dc == 1) & (D.mean(2) > 170)], 0)   # (the drawing's skin in light)
    Sc[[k for k, v in enumerate(MARKS) if v not in PANELS]] = -np.inf   # (only the panels that paint)
    smax = Sc.max(0); seen_any = np.isfinite(smax)
    Sb = Sc + np.array([0., FRONT_BIAS, 0.])[:, None]; sbm = np.where(seen_any, Sb.max(0), 0)   # (the front first)
    w = np.where(np.isfinite(Sc), np.exp(SHARP * (Sb - sbm)), 0)
    col = (w[..., None] * Co).sum(0) / np.maximum(w.sum(0), 1e-12)[:, None]
    wt = np.where(seen_any, smooth(*FACE, np.where(seen_any, smax, 0)), 0)[:, None]
    new_ = BASE * (1 - wt) + col * wt
    # the jaw's black V line, as the drawings' (kael_nero.png, the head sheet): along the jaw's lower edge seen from the front,
    # JAW_V[0] high, on the face's front surface (the 3D outline is pushed behind the body: it draws no inner lines)
    pr = pos[R]; fr = (pr[:, 2] > JAW_V[2]) & (nor[R, 2] > -.2) & (pr[:, 1] < JAW_V[3]) & (np.abs(pr[:, 0]) < JAW_V[4])
    bins = np.floor((pr[:, 0] + .1) / JAW_V[1]).astype(int); edge = np.full(bins.max() + 2, np.inf)
    np.minimum.at(edge, bins[fr], pr[fr, 1]); ok = np.isfinite(edge)   # (per column, the face's lowest point in front)
    cx_ = (np.arange(len(edge)) + .5) * JAW_V[1] - .1
    edge_s = ndimage.median_filter(np.where(ok, edge, np.nan), 3)[ok] if ok.sum() > 3 else edge[ok]
    ej = np.interp(pr[:, 0], cx_[ok], edge_s)
    vline = fr & (pr[:, 1] < ej + JAW_V[0]) & JAW_PAINT
    new_[vline] = JAW_BLACK
    print('the jaw\'s line: %d texels; its lowest point at y %.4f' % (int(vline.sum()), float(np.nanmin(np.where(ok, edge, np.nan)))))
    # (the nose's sides in light: the drawing's shadow beside the nose, painted on its side, spread into a brown patch
    # in three quarters; the shadow under it stays)
    nz = (np.abs(pr[:, 0] - M3[2, 0]) < NOSE_SIDE[1]) & (pr[:, 1] > M3[2, 1] - .004) & (pr[:, 1] < M3[2, 1] + NOSE_SIDE[2]) & (np.abs(nor[R, 0]) > NOSE_SIDE[0])
    nzs = nz & (np.abs(new_ - np.array(CEL_PAL[3], float)).sum(1) < 40); new_[nzs] = BASE
    out = T.copy(); out[ys[R], xs[R]] = new_
    # the collar's specks (Meshy's skin-coloured bits on its purple and black, by the neck): its nearest colour
    oc = out[ys, xs]; low = (pos[:, 1] < COLLAR_Y) & (th > .3)
    colc = low & ((oc[:, 2] > oc[:, 1] + 30) | (oc.mean(1) < 60)); CC = np.zeros((TS, TS), bool); CC[ys, xs] = colc
    OT = np.zeros((TS, TS), bool); OT[ys, xs] = low & ~colc; lab, n = ndimage.label(OT); sz = np.bincount(lab.ravel())
    spk = np.zeros(n + 1, bool); CV = np.zeros((TS, TS), bool); CV[ys, xs] = True
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None or sz[i] > COLLAR_SPECK: continue
        y0, y1 = max(sl[0].start - 3, 0), sl[0].stop + 3; x0, x1 = max(sl[1].start - 3, 0), sl[1].stop + 3
        me = lab[y0:y1, x0:x1] == i; ring = ndimage.binary_dilation(me, iterations=2) & ~me & CV[y0:y1, x0:x1]
        spk[i] = ring.any() and CC[y0:y1, x0:x1][ring].mean() > .7
    SP = spk[lab] & OT
    if SP.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~CC, return_indices=True); out[SP] = out[iy[SP], ix[SP]]
    print('the collar: %d texels of specks in its colours' % int(SP.sum()))
    if debug:   # (the texture with the face's texels in the colour of the panel painting them: red, green, blue; white: none)
        vt = T.copy(); tint = np.array([[255, 0, 0], [0, 200, 0], [0, 80, 255]], float)
        vt[ys[R], xs[R]] = (w[..., None] * tint[:, None]).sum(0) / np.maximum(w.sum(0), 1e-12)[:, None] * wt + 255 * (1 - wt)
        Image.fromarray(np.clip(vt, 0, 255).astype(np.uint8)).save(os.path.join(debug, 'face_views.jpg'), quality=92)
    cov = np.zeros((TS, TS), bool); cov[ys, xs] = True
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(tp, quality=90, optimize=True)
    # the face all flat (its shading is the sheet's)
    vreg = np.zeros(len(P)); vc = np.zeros(len(P)); tri = np.bincount(ks[R], minlength=nt) > .5 * np.maximum(np.bincount(ks, minlength=nt), 1)
    np.add.at(vreg, I.ravel(), np.repeat(tri.astype(float), 3)); np.add.at(vc, I.ravel(), 1)
    vin = vreg / np.maximum(vc, 1) > .5
    ejv = np.interp(P[:, 0], cx_[ok], edge_s)   # (the jaw's edge seen from the front, at each vertex's x)
    under = (P[:, 1] < ejv + UNDER[3]) & (P[:, 1] < UNDER[1]) & (np.abs(P[:, 0]) < JAW_V[4]) & (hw > .3) & (NL[:, 1] < UNDER[0])   # (under the jaw's line: the jaw's underside and the neck under it, in the toon light: in
    new = np.where(vin & ~under, 1., np.where(under, 0., flat))   # its shadow, as Ren's, the jaw's line reads as the jaw)
    blob = bytearray(LB); of = lj['flat'][0]; blob[of:of + 4 * len(P)] = new.astype(np.float32).tobytes()
    open(os.path.join(pkg, name + '_look.bin'), 'wb').write(bytes(blob))
    print('paint: %d face texels (%d from the sheet, %d facing it well); the skin in light %s; flat light on %d face vertices' % (
        len(R), int((wt[:, 0] > 0).sum()), int((wt[:, 0] > .5).sum()), BASE.round().astype(int).tolist(), int(vin.sum())))


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3): sys.exit(__doc__)
    main(*sys.argv[1:])
