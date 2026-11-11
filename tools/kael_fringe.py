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

With 'paint' and SIDES (tools/kael_head.py; Denis, 11/11 night, circling the temples, the cheeks and his right eye): the
images do not agree (the front one draws locks beside the eyes, the side ones the temple and the cheek bare there), so
Meshy's locks a side image does not draw are hidden only as the head is seen from there (side_hide; the package's hv,
src/e_model.js mdHeadHide), the skin under them painted from the side images (side_paint, skin_fill), and the front
image's two locks over his right eye cut short, their tips above the brow (front_edit).

face(...) paints in place and returns (the head's triangles kept, the sheet or None, per side image the triangles hidden
from it or None)."""
import json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from cel_light import view_depth, zbuffer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DROP_DZ, DROP_TOP = .0015, .006   # m: in front of the skin by more than; the forehead's top (its highest skin) plus
EAR = (.057, .03)                 # m: the ears (|x - the face's middle| over [0], z under [1]): not painted
POW, MIN_FACING, SEEN = 16., .2, .002
FEAT = (.042, .006, .03, .3, .004)   # the features: |x - middle| under [0], from [1] under the chin to [2] over the eyes, facing the front camera over [3]; [4]: the edge's blend (m)
FEAT_FRONT = (.7, .02, .03)       # the cheeks (|x - middle| from [1] to [2] m and further): facing the front camera over [0] (turned to the side,
                                  # the front image's lines there, a little off, came out as marks on the cheek from the 3/4)
EYE_ZONE = (.056, .024, .006)     # and around the eyes the front image's alone up to [0] m from the middle (their outer corners; the 3/4 images'
                                  # locks across them came through), [1] m around the eyes' line plus [2]
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
PRESS = (3, .0012, 40, 1.5)       # see press(): the skull's grid (px); the pressed hair over it (m); its fade into the drawing's hair (px); the skull's smoothing (cells)
PRESS_WIN = (30., 10., .02, .06, 0.)   # see press(): around the head from the face's front over [0] degrees (fading in over [1]), y from the chin
                                  # minus [2] to the eyes plus [3] (m, fading over a cm); the angle's centre z [4] (m)
PRESS_FAR = (.025, .035)          # see press(): the hair standing further off the skull than this (m, fading out): kept (the mane's side spikes)
PRESS_NEED = (2, 3, 90)           # see press(): the front image's hair kept, grown over [0] rings of neighbours, smoothed over [1]; its lines darker than [2]
# the sides seen from the side (side_hide, side_paint; used): per side, its images (the profile, the 3/4)
HIDE_VIEWS = {'dx': ('profilo_dx', '34_dx'), 'sx': ('profilo_sx', '34_sx')}
HIDE_ORDER = ('profilo_dx', '34_dx', '34_sx', 'profilo_sx')   # (the head's aHide: x, y, z, w)
HIDE = (2, 5, .05, 22., (.03, .075), 40, .04, -.02, .006)   # see side_hide(): the drawing's skin eroded [0] px; up to [1] layers; the skin behind within [2] m;
                                  # from [3] degrees around the head; y from the chin minus [4][0] to the eyes plus [4][1] (m); pieces under [5]
                                  # triangles; no holes: a surface behind each within [6] m; the camera's half of the head: depth over [7] m;
                                  # a hair triangle over a gap of the face within [8] m of it: part of the face, painted as its skin
SIDE_PAINT = (24., 10., (.03, .075))   # see side_paint(): from [0] degrees around the head, fading in over [1]; y from the chin minus [2][0] to the eyes plus [2][1] (m)
SIDE_POW, SIDE_FACING = 24., .05  # side_paint's weights: how much the texel faces each image, to this power; seen by it facing it over
SIDE_LINE = (90, .12)             # side_paint: a line (darker than [0]) from an image only as it faces the texel more than the other by [1]
SKIN_FILL = (.075, .0, .01)       # see skin_fill()
LOCK_LINE = (5, 120, 6)           # see lock_lines()


# the front image's two locks over its left eye (Kael's right) cut short, their tips above the brow (Denis, 10/11 night,
# circling them: "quella ciocca davanti l'occhio rimpiccioliscila mettila davanti con la punta della ciocca sopra al
# sopracciglio", "accorciare o semplicemente rimuovere senza lasciare tracce"); see front_edit()
FRONT_EDIT = dict(xm=705.25, xn=690, box=(515, 520, 770, 730), locks=(((650, 600), 588, (652, 626)), ((585, 590), 578, (586, 604))),
                  line=3.2, dark=(25, 22, 30))


def front_edit(D):
    """The front image with the locks over its left eye cut short (FRONT_EDIT['locks']: a pixel in each, the row it is
    cut at, its new tip): below the cut each ends in a point (the triangle from its two edges at the cut to the tip, its
    two sides drawn as the drawing's lines, line px, dark); what they covered (the eye, the brow, the skin between them)
    from the other eye mirrored (about xm, the irises' middle: they are at 587.8 and 822.7, both at y 664.3), by the
    nose (right of xn, not symmetric) the lit skin's colour, flat as drawn."""
    E = FRONT_EDIT; H, W = D.shape[:2]; xm, xn = E['xm'], E['xn']
    from kael_head import is_hair as _is_hair, is_skin as _is_skin
    xs = np.arange(W); xr = 2 * xm - xs; x0 = np.clip(np.floor(xr).astype(int), 0, W - 2); fx = np.clip(xr - x0, 0, 1)
    Mi = D[:, x0] * (1 - fx)[None, :, None] + D[:, x0 + 1] * fx[None, :, None]
    light = _is_hair(D) & ~_is_skin(D) & (D.mean(2) > 150)
    b = E['box']; inbox = np.zeros((H, W), bool); inbox[b[1]:b[3], b[0]:b[2]] = True
    lab, _ = ndimage.label(light & inbox); Y, X = np.mgrid[0:H, 0:W]
    old = np.zeros((H, W), bool); keep = np.zeros((H, W), bool); above = np.zeros((H, W), bool); edges = []
    for (sx, sy), cut, (tx, ty) in E['locks']:
        m = lab == lab[sy, sx]
        full = m | (ndimage.binary_dilation(m, iterations=6) & (D.mean(2) < 150) & inbox)   # (with its outline)
        row = np.nonzero(m[cut])[0]; xl, xr_ = row.min() - 1, row.max() + 1
        im = Image.new('L', (W, H), 0); ImageDraw.Draw(im).polygon([(xl, cut), (xr_, cut), (tx, ty)], fill=255)
        old |= full & (Y > cut); keep |= (np.asarray(im) > 0) & full; above |= full & (Y <= cut)
        edges += [((xl, cut), (tx, ty)), ((xr_, cut), (tx, ty))]
    top = min(c for _, c, _ in E['locks'])
    R = ndimage.binary_dilation(old, iterations=2) & ~keep & ~above & (Y > top)
    lit = _is_skin(D) & (D.mean(2) > 175); lit_c = np.median(D[700:770, 720:790][lit[700:770, 720:790]], 0)
    wm = np.clip((xn - X) / 12., 0, 1)
    hairy = _is_hair(Mi) & ~_is_skin(Mi) & (Mi.mean(2) > 150)
    fill = np.where((hairy & R)[..., None], lit_c, Mi * wm[..., None] + lit_c * (1 - wm[..., None]))
    Rf = np.clip(ndimage.gaussian_filter(R.astype(float), 1.) * 1.5, 0, 1) * ~keep
    out = D * (1 - Rf[..., None]) + fill * Rf[..., None]
    dist = np.full((H, W), np.inf)
    for (a, b_) in edges:
        a, b_ = np.array(a, float), np.array(b_, float); ab = b_ - a; t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        dist = np.minimum(dist, np.hypot(X - (a[0] + t * ab[0]), Y - (a[1] + t * ab[1])))
    al = np.clip(E['line'] / 2 + .5 - dist, 0, 1) * (Y >= top - 2)
    return out * (1 - al[..., None]) + np.array(E['dark'], float) * al[..., None]


_DRAWN = {}


def drawing(view):
    """Denis's head image of view (the front one edited, front_edit) and its figure (not the background)."""
    if view not in _DRAWN:
        D = np.asarray(Image.open(os.path.join(ROOT, 'docs/ref/personaggi/kael_testa_%s.png' % view)).convert('RGB')).astype(np.float64)
        if view == 'fronte' and FRONT_EDIT: D = front_edit(D)
        bg = np.median(D[5:40, 5:40].reshape(-1, 3), 0)
        F = ndimage.binary_fill_holes(ndimage.binary_opening(np.abs(D - bg).sum(2) > 30, iterations=1))
        _DRAWN[view] = (D, F)
    D, F = _DRAWN[view]
    return D.copy(), F.copy()


def face_mask(D, F, is_skin, is_hair):
    """The image's face: its skin and what is joined to it that is not hair (the eyes, the nose, the mouth, the lines),
    the piece with the most skin (not the ears)."""
    sk = is_skin(D) & F; hr = is_hair(D) & ~sk & F
    lab, n = ndimage.label((sk | (F & ~hr)) & F)
    if n == 0: return np.zeros_like(F)
    cnt = ndimage.sum(sk, lab, range(1, n + 1))
    return lab == 1 + int(np.argmax(cnt))


def skin_face(D, F, is_skin):
    """The image's face from its skin alone: the skin with the thin lines and the features it closes around (the eyes, the
    brows, the mouth), the piece with the most of it (face_mask also takes the lines joined to it: in the hair they make
    one net reaching the whole mane)."""
    sk = is_skin(D) & F
    sk = ndimage.binary_fill_holes(ndimage.binary_closing(sk, iterations=2)) & F
    lab, n = ndimage.label(sk)
    if n == 0: return sk
    return lab == 1 + int(np.argmax(ndimage.sum(sk, lab, range(1, n + 1))))


def lock_lines(D, F, is_skin, is_hair):
    """The image's locks' outlines: its dark pixels (under LOCK_LINE[1]) within LOCK_LINE[0] px of its hair's fill (its
    lavenders, light and shadow: purple in them, LOCK_LINE[2]; not the eyes' whites, which have none)."""
    fill = is_hair(D) & ~is_skin(D) & F & (D.mean(2) > 100) & (np.minimum(D[..., 0], D[..., 2]) - D[..., 1] > LOCK_LINE[2])
    return ndimage.binary_dilation(fill, iterations=LOCK_LINE[0]) & (D.mean(2) < LOCK_LINE[1]) & F


def skin_all(D, F, is_skin, least=60):
    """The image's skin, all of it (the face, the temples between the locks, the ears; pieces under least px left out),
    with the thin lines and the features it closes around."""
    sk = is_skin(D) & F
    sk = ndimage.binary_fill_holes(ndimage.binary_closing(sk, iterations=2)) & F
    lab, n = ndimage.label(sk)
    if n == 0: return sk
    big = np.nonzero(ndimage.sum(sk, lab, range(1, n + 1)) >= least)[0] + 1
    return np.isin(lab, big)


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


def harmonic(Z, known, inside, iters=600):
    """Z's unknown cells inside the window filled by the Laplace equation (the known cells fixed): a smooth surface under
    the hair carried from the skin around it."""
    out = np.where(known, Z, np.nan); m = np.nanmean(out[known]) if known.any() else 0.
    cur = np.where(known, Z, m)
    free_ = inside & ~known
    for _ in range(iters):
        nb = (np.roll(cur, 1, 0) + np.roll(cur, -1, 0) + np.roll(cur, 1, 1) + np.roll(cur, -1, 1)) / 4
        cur = np.where(free_, nb, cur)
    return cur


def press(Q, N, I, vc, hair_v, cams, mid, eye_m, chin_m, is_skin, is_hair):
    """The temples and the cheeks between the eyes and the ears clean as in the profiles (Denis, 11/11 night, circling them
    in every view): Meshy's head is one shell, on the sides its outer surface is the hair (no scalp under it: taken out,
    its locks opened holes). Per side, seen from its profile's camera: the skull under the hair (the front-most skin seen
    there, carried under the rest by harmonic(), on a grid of PRESS[0] px, smoothed over PRESS[3] cells) and the hair's
    points over it pressed down onto it, PRESS[1] m over it: all of them where the profile draws the face (its skin, not
    its hair), fading out over PRESS[2] px into the drawing's hair (its locks' ends lie on the head, rising into the
    mass; the first try faded inside the face and left the locks' ends standing, in pieces); only on the head's side
    (PRESS_WIN: around it from the face's front over [0] degrees, fading in over [1]; from the chin minus [2] to the eyes
    plus [3] m): not the face's front, where the front image draws the locks by the eyes. The pressed points take the
    skull's normal (a lock's two faces pressed together had opposite ones: the painting left the one turned away
    unpainted, in specks, and the outline drew black shards along them). Q, N in place; returns the pressed share per
    vertex (0 to 1: the outline's width goes with it, the painting takes the profiles' drawing where it is over .05)."""
    _, first, inv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    X = Q[first].copy(); hw = np.zeros(len(first), bool); np.logical_or.at(hw, inv, hair_v)
    wv = np.zeros(len(first)); nv = np.zeros((len(first), 3))
    skin_t = is_skin(vc)[I].all(1); moved_total = []
    sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - a) / (b - a), 0, 1))
    az = np.degrees(np.arctan2(X[:, 0] - mid, X[:, 2] - PRESS_WIN[4]))
    yw = sm(chin_m - PRESS_WIN[2] - .01, chin_m - PRESS_WIN[2], X[:, 1]) * (1 - sm(eye_m + PRESS_WIN[3], eye_m + PRESS_WIN[3] + .01, X[:, 1]))
    # (what the front image needs: its hair where the model's front-most surface is, by the eyes the locks it draws
    # over their outer corners; grown and smoothed over the mesh, a lock kept whole)
    from scipy.sparse import csr_matrix
    Tw = inv[I]; E = np.unique(np.sort(np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]), 1), axis=0); nw = len(first)
    A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)); deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)
    fr = cams['fronte']; Df, Ff = drawing('fronte'); Hf, Wf = Ff.shape; FMf = skin_face(Df, Ff, is_skin)
    Zf, pjf = view_depth(Q, I, fr, Wf, Hf); uf, vf, df = pjf(X)
    uif, vif = np.clip(np.round(uf).astype(int), 0, Wf - 1), np.clip(np.round(vf).astype(int), 0, Hf - 1); pxf = Df[vif, uif]
    need = hw & (df >= Zf[vif, uif] - SEEN) & Ff[vif, uif] & ~FMf[vif, uif] & (is_hair(pxf) | (pxf.mean(1) < PRESS_NEED[2]))
    need_s = need.astype(float)
    for _ in range(PRESS_NEED[0]): need_s = np.maximum(need_s, (A @ need_s > 0).astype(float))
    for _ in range(PRESS_NEED[1]): need_s = .5 * need_s + .5 * (A @ need_s) / deg
    for view, sign in (('profilo_dx', -1), ('profilo_sx', 1)):
        cam = cams[view]; D, F = drawing(view); H, W = F.shape
        th = np.radians(cam['yaw']); fwd = np.array([np.sin(th), 0, np.cos(th)]); right = np.array([np.cos(th), 0, -np.sin(th)]); up = np.array([0., 1., 0.])
        Za, proj = view_depth(Q, I, cam, W, H); Zs, _ = view_depth(Q, I[skin_t], cam, W, H)
        g = PRESS[0]; Hg, Wg = (H + g - 1) // g, (W + g - 1) // g
        pad = lambda A, fill: np.pad(A, ((0, Hg * g - H), (0, Wg * g - W)), constant_values=fill)
        za = pad(np.where(np.isfinite(Za), Za, np.nan), np.nan).reshape(Hg, g, Wg, g); zs = pad(np.where(np.isfinite(Zs), Zs, np.nan), np.nan).reshape(Hg, g, Wg, g)
        with np.errstate(all='ignore'):
            za_g = np.nanmax(za, axis=(1, 3)); zs_g = np.nanmax(zs, axis=(1, 3))
        known = np.isfinite(zs_g) & np.isfinite(za_g) & (zs_g >= za_g - .0015)   # (the skin is the front-most there)
        inside = np.isfinite(za_g)
        skull = harmonic(np.where(known, zs_g, 0.), known, inside)
        if PRESS[3]:   # (smoothed: Meshy's skin between its locks is uneven)
            m_ = ndimage.gaussian_filter(inside.astype(float), PRESS[3]); skull = np.where(inside, ndimage.gaussian_filter(np.where(inside, skull, 0.), PRESS[3]) / np.maximum(m_, 1e-6), skull)
        # (its normal: the depth d over the image's a = (u - cx) / s, b = (by - v) / s is P = right a + up b + fwd d, whose
        # normal is fwd - d_a right - d_b up, d_a = s d_u, d_b = -s d_v)
        du = np.gradient(skull, axis=1) / g; dv = np.gradient(skull, axis=0) / g
        ng = fwd[None, None] - (cam['s'] * du)[..., None] * right[None, None] + (cam['s'] * dv)[..., None] * up[None, None]
        ng /= np.linalg.norm(ng, axis=2, keepdims=True)
        FM = skin_face(D, F, is_skin); dist = ndimage.distance_transform_edt(~FM)   # (px out of the drawing's face, into its hair)
        u, v, d = proj(X); ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
        gi, gj = np.clip(vi // g, 0, Hg - 1), np.clip(ui // g, 0, Wg - 1)
        target = skull[gi, gj] + PRESS[1]
        w = (sm(PRESS_WIN[0], PRESS_WIN[0] + PRESS_WIN[1], az * sign) * yw * (1 - sm(0, PRESS[2], dist[vi, ui])) * inside[gi, gj]
             * (1 - need_s) * (1 - sm(PRESS_FAR[0], PRESS_FAR[1], d - skull[gi, gj])))
        k = np.nonzero(hw & (d > target) & (w > 1e-3))[0]
        delta = (target[k] - d[k]) * w[k]
        X[k] += fwd[None] * delta[:, None]
        nv[k] = ng[gi[k], gj[k]]; wv[k] = np.maximum(wv[k], w[k])
        moved_total.append((view, int((np.abs(delta) > 1e-4).sum()), float(np.abs(delta).max()) if len(k) else 0.))
    # (normals: the pressed points' toward the skull's, by how much they were pressed)
    fn = np.cross(X[Tw[:, 1]] - X[Tw[:, 0]], X[Tw[:, 2]] - X[Tw[:, 0]]); acc = np.zeros_like(X)
    for c in range(3): np.add.at(acc, Tw[:, c], fn)
    Nw = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    pk = wv > 1e-3; aff = np.zeros(len(first), bool); aff[Tw[pk[Tw].any(1)].ravel()] = True
    Nn = np.where(pk[:, None], (1 - wv[:, None]) * Nw + wv[:, None] * nv, Nw); Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)
    Q[:] = X[inv]; sel = aff[inv]; N[sel] = Nn[inv[sel]]
    print('face: the temples and the cheeks pressed onto the skull as the profiles draw them: %s (the front image\'s hair kept: %d points)' % (
        ', '.join('%s %d points (up to %.1f mm)' % (v_, n_, 1000 * m_) for v_, n_, m_ in moved_total), int(need.sum())))
    return wv[inv]


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


def feat_zone(p, n, fwd, mid, eye_m, chin_m):
    """Per point (p, its normal n; fwd: the front camera's): the share painted from the front image alone (the features,
    FEAT; around the eyes, EYE_ZONE), 0 to 1."""
    sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - a) / (b - a), 0, 1))
    ax, nf = np.abs(p[:, 0] - mid), n @ fwd
    ft = FEAT[3] + (FEAT_FRONT[0] - FEAT[3]) * sm(FEAT_FRONT[1], FEAT_FRONT[2], ax)   # (the nose, the mouth and the chin's middle from facing the front over FEAT[3], as the eyes)
    z = (sm(FEAT[0], FEAT[0] - FEAT[4], ax) * sm(chin_m - FEAT[1] - FEAT[4], chin_m - FEAT[1], p[:, 1]) * sm(eye_m + FEAT[2], eye_m + FEAT[2] - FEAT[4], p[:, 1])
         * sm(ft - .1, ft, nf))
    ze = sm(EYE_ZONE[0], EYE_ZONE[0] - FEAT[4], ax) * sm(EYE_ZONE[1], EYE_ZONE[1] - FEAT[4], np.abs(p[:, 1] - eye_m - EYE_ZONE[2])) * sm(FEAT[3] - .1, FEAT[3], nf)
    return np.maximum(z, ze)


_BARY = 1 / 3 + .9 * (np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, .5, 0], [0, .5, .5], [.5, 0, .5], [1 / 3, 1 / 3, 1 / 3],
                                [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]]) - 1 / 3)


def covers_gap(Q, I, tris, Zb, proj):
    """Per triangle of tris: at one of its points (its corners, its edges' middles, inside it) the nearest of the other
    surfaces (their depth map Zb, from the camera of proj) is more than HIDE[6] m behind it: without it the inside of
    the head would show (nothing at all behind: the head's edge, no gap)."""
    if not len(tris): return np.zeros(0, bool)
    H, W = Zb.shape; P = np.einsum('sk,nkc->nsc', _BARY, Q[I[tris]]).reshape(-1, 3); u, v, d = proj(P)
    zb = Zb[np.clip(np.round(v).astype(int), 0, H - 1), np.clip(np.round(u).astype(int), 0, W - 1)]
    return (np.isfinite(zb) & (zb < d - HIDE[6])).reshape(len(tris), -1).any(1)


def side_hide(Q, I, keep, vc, hair_v, cams, mid, eye_m, chin_m, is_skin):
    """Meshy's locks over the temples and the cheeks that the side images (the profile and the 3/4 of each side,
    HIDE_VIEWS) do not draw: hidden when the head is seen from there (src/e_model.js mdHeadHide, the head's aHide), kept
    from the front, where the front image draws them by the eyes (Denis, 11/11 night, circling both: the images do not
    agree on them; pressed onto the head for the side, they went from the front too). Per image, its own (the profile
    and the 3/4 do not agree either: above the ear one draws hair, the other the temple's skin), layer by layer (up to
    HIDE[1]): the hair triangles seen from it in front of the skin (within HIDE[2] m behind) where it draws the face
    (skin_face, eroded HIDE[0] px; the middle and two corners), on its side of the head (HIDE[3] degrees around it from
    the face's front, y from the chin minus HIDE[4][0] to the eyes plus HIDE[4][1]); then the hair's pieces this leaves
    under HIDE[5] triangles next to them. Under them is Meshy's skin (the temples' scalp: no holes), painted from the
    image that sees it by side_paint(). Whole triangles (their corners split from the rest's in the package: hidden
    by shares, the skin next to them was cut too, the back of the head seen through). Returns {view: the triangles
    hidden from it (over I)}, {view: the locks standing over the face as seen from it, hidden or not} and the hair
    triangles that are part of the face (over its gaps)."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    nh = hair_v[I].sum(1); hair_t = nh >= 2   # (the locks: two corners hair or more)
    C = Q[I].mean(1); az = np.degrees(np.arctan2(C[:, 0] - mid, C[:, 2] - PRESS_WIN[4]))
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    ywin = (C[:, 1] > chin_m - HIDE[4][0]) & (C[:, 1] < eye_m + HIDE[4][1])
    _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel()
    res, lock, force = {}, {}, np.zeros(len(I), bool)
    for side, sign in (('dx', -1), ('sx', 1)):
        cand = keep & hair_t & ywin & (az * sign > HIDE[3])
        for view in HIDE_VIEWS[side]:
            hid = np.zeros(len(I), bool)
            cam = cams[view]; D, F = drawing(view); H, W = F.shape
            FM = ndimage.binary_erosion(skin_all(D, F, is_skin), iterations=HIDE[0])
            _, proj = view_depth(Q, I[:1], cam, W, H)
            u, v, d = proj(C); ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
            uq, vq, dq = proj(Q); uqi, vqi = np.clip(np.round(uq).astype(int), 0, W - 1), np.clip(np.round(vq).astype(int), 0, H - 1)
            over = FM[vi, ui] & (FM[vqi, uqi][I].sum(1) >= 1)
            # (the face behind them: the layer furthest back of those turned to this camera, on its half of the head; by Meshy's
            # colours the eyes' whites read as hair, and a lock before an eye had no skin behind it)
            tv = np.radians(cam['yaw']); turned = (fn @ np.array([np.sin(tv), 0, np.cos(tv)]) > .2) & (d > HIDE[7])
            Zs = -zbuffer(uq, vq, -dq, I[keep & turned], W, H)
            zs = Zs[vi, ui]; behind = np.isfinite(zs) & (zs < d - DROP_DZ) & (zs > d - HIDE[2])
            for _ in range(HIDE[1]):
                Z, _ = view_depth(Q, I[keep & ~hid], cam, W, H)
                c = cand & ~hid & (d >= Z[vi, ui] - SEEN) & over & behind
                if not c.any(): break
                hid |= c
            for _ in range(4):   # (no holes: from its image, behind all of each hidden triangle another surface within HIDE[6] m; else it
                # stays, and lying on the face (within HIDE[8] m of it) it is part of it: Meshy's skin has gaps under some of its locks)
                Zb, _ = view_depth(Q, I[keep & ~hid], cam, W, H); hk = np.nonzero(hid)[0]
                g = hk[covers_gap(Q, I, hk, Zb, proj)]
                if not len(g): break
                hid[g] = False; force[g[d[g] - zs[g] < HIDE[8]]] = True
            rest = np.nonzero(keep & hair_t & ~hid)[0]   # (the pieces left: small ones touching what is hidden)
            if len(rest):
                A = csr_matrix((np.ones(3 * len(rest)), (np.repeat(np.arange(len(rest)), 3), wv[I[rest]].ravel())), shape=(len(rest), wv.max() + 1))
                _, lab = connected_components(A @ A.T, directed=False); sz = np.bincount(lab)
                hv = np.zeros(wv.max() + 1, bool); hv[wv[I[hid]].ravel()] = True
                touch = np.zeros(lab.max() + 1, bool); np.logical_or.at(touch, lab, hv[wv[I[rest]]].any(1))
                small = rest[(sz[lab] < HIDE[5]) & touch[lab]]; hid[small] = True
                Zb, _ = view_depth(Q, I[keep & ~hid], cam, W, H); hid[small[covers_gap(Q, I, small, Zb, proj)]] = False
            res[view] = hid; lock[view] = keep & hair_t & behind
            print('face: from %s, %d of Meshy\'s triangles over the temple and the cheek hidden (its image draws the face there)' % (view, int(hid.sum())))
    for view in lock: lock[view] &= ~force
    print('face: %d hair triangles over gaps of the face\'s skin, lying on it: part of the face' % int(force.sum()))
    return res, lock, force


def hide_shares(Q, I, keep, hid):
    """Per vertex: the share (by area) of its kept triangles that hid holds, alike over its copies along the texture's
    seams (src/e_model.js leaves out what interpolates over a half: aHideR, aHideL)."""
    _, wld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wld = wld.ravel()
    ar = .5 * np.linalg.norm(np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]), axis=1) * keep
    tot = np.zeros(wld.max() + 1); np.add.at(tot, wld[I].ravel(), np.repeat(ar, 3))
    hs = np.zeros(wld.max() + 1); np.add.at(hs, wld[I].ravel(), np.repeat(ar * (hid & keep), 3))
    return (hs / np.maximum(tot, 1e-12))[wld]


def side_paint(out, Q, I, keep, hide, locks, is_skin, ys, xs, ks, pos, nor, ear_v, collar_v, cams, mid, eye_m, chin_m, done=None):
    """The head's sides as their images draw them, seen from that side (Meshy's locks there hidden, side_hide): each
    texel on the side (SIDE_PAINT: from [0] degrees around the head, fading in over [1]; y from the chin minus [2][0]
    to the eyes plus [2][1]; not the ears, the earrings, the collar, the features the front image draws) from the side's
    images that see it then (the profile, the 3/4), all of their drawing (the skin, its lines and shading, the locks
    they draw over the temple; not their skin on a lock standing over the face, locks), weighted by how much it faces
    each (to the power SIDE_POW); blended over what was painted at the fade. Returns how many texels."""
    sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - a) / (b - a), 0, 1))
    th = np.radians(cams['fronte']['yaw']); fwd_f = np.array([np.sin(th), 0, np.cos(th)])
    az = np.degrees(np.arctan2(pos[:, 0] - mid, pos[:, 2] - PRESS_WIN[4]))
    yw = sm(chin_m - SIDE_PAINT[2][0] - .01, chin_m - SIDE_PAINT[2][0], pos[:, 1]) * (1 - sm(eye_m + SIDE_PAINT[2][1], eye_m + SIDE_PAINT[2][1] + .01, pos[:, 1]))
    zone = feat_zone(pos, nor, fwd_f, mid, eye_m, chin_m)
    base = yw * (1 - zone) * ~ear_v[I[ks]].any(1) * ~collar_v[I[ks]].any(1) * keep[ks]   # (the ears too: as the side images draw them, the hair over them)
    total = 0
    for side, sign in (('dx', -1), ('sx', 1)):
        wwin = base * sm(SIDE_PAINT[0], SIDE_PAINT[0] + SIDE_PAINT[1], az * sign)
        sel = np.nonzero(wwin > 1e-3)[0]
        if not len(sel): continue
        p, n = pos[sel], nor[sel]; acc = np.zeros((len(sel), 3)); wsum = np.zeros(len(sel))
        samples = []
        for view in HIDE_VIEWS[side]:   # (each image the head as seen from it: what it hides left out, what that shows painted from it)
            cam = cams[view]; D, F = drawing(view); H, W = F.shape
            Z, pj = view_depth(Q, I[keep & ~hide[view]], cam, W, H); u, v, dep = pj(p)
            ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
            t = np.radians(cam['yaw']); facing = n @ np.array([np.sin(t), 0, np.cos(t)])
            vis = (dep >= Z[vi, ui] - SEEN) & (facing > SIDE_FACING) & (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1) & F[vi, ui] & ~hide[view][ks[sel]]
            x0, y0 = np.clip(np.floor(u).astype(int), 0, W - 2), np.clip(np.floor(v).astype(int), 0, H - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
            col = (D[y0, x0] * (1 - fx) + D[y0, x0 + 1] * fx) * (1 - fy) + (D[y0 + 1, x0] * (1 - fx) + D[y0 + 1, x0 + 1] * fx) * fy
            vis &= ~(locks[view][ks[sel]] & is_skin(col))   # (a lock standing over the face keeps its hair's paint where the image draws
            # skin: painted as skin, it was skin-coloured pieces before the face from the other side)
            samples.append((np.where(vis, facing, -1.), col))
        for i_, (fc, col) in enumerate(samples):   # (a dark line only from the image that sees the texel clearly best: the other's
            # view of it, a little off, drew the profile's lines across the 3/4's cheek)
            other = np.max([f_ for j_, (f_, _) in enumerate(samples) if j_ != i_], axis=0) if len(samples) > 1 else np.full(len(fc), -1.)
            w = np.where(fc > -1, np.maximum(fc, 0) ** SIDE_POW, 0.)
            dark = col.mean(1) < SIDE_LINE[0]
            w = np.where(dark & (other > -1), w * sm(0, SIDE_LINE[1], fc - other), w)
            acc += w[:, None] * col; wsum += w
        ok = wsum > 0; k = sel[ok]; a = wwin[k][:, None]
        out[ys[k], xs[k]] = out[ys[k], xs[k]] * (1 - a) + (acc[ok] / wsum[ok, None]) * a
        if done is not None: done[k] = True
        total += int(ok.sum())
    print('face: %d texels of the temples and the cheeks painted from the side images (as seen from the side)' % total)
    return total


def skin_fill(out, I, ys, xs, ks, pos, hair_v, ear_v, collar_v, done, keep, mid, chin_m, top, is_skin, force=None):
    """The face's skin left unpainted (no image sees it: slivers folded under their neighbours, the skin behind a lock)
    and still in Meshy's hair paint, lavender or dark (it showed from other sides as marks on the cheek): on the skin's
    triangles (at most one corner hair's) of the head's front half (SKIN_FILL: |x - middle| under [0], z over [1], from
    the chin minus [2] up), the texels not skin's colour take the nearest painted skin texel's. Returns how many."""
    from scipy.spatial import cKDTree
    c = out[ys, xs]; skin_now = is_skin(c)
    reg = (keep[ks] & (hair_v[I[ks]].sum(1) <= 1) & ~ear_v[I[ks]].any(1) & ~collar_v[I[ks]].any(1) & (np.abs(pos[:, 0] - mid) < SKIN_FILL[0])
           & (pos[:, 2] > SKIN_FILL[1]) & (pos[:, 1] > chin_m - SKIN_FILL[2]) & (pos[:, 1] < top))
    fz = force[ks] & keep[ks] if force is not None else np.zeros(len(ks), bool)   # (and the hair triangles that are part of the face, side_hide)
    todo = np.nonzero((reg | fz) & ~done & ~skin_now)[0]; src = np.nonzero(reg & done & skin_now & ~fz)[0]
    if len(todo) and len(src):
        _, j = cKDTree(pos[src]).query(pos[todo]); out[ys[todo], xs[todo]] = out[ys[src[j]], xs[src[j]]]
    print('face: %d texels of the skin no image sees, left in Meshy\'s hair paint, as the painted skin next to them' % len(todo))
    return len(todo)


def face(out, Q, N, UV, I, ys, xs, ks, pos, nor, vc, hair_v, ear_v, collar_v, mid, eye_m, chin_m, cams, is_skin, is_hair, sheet=True, paint_bangs=False, paint_all=False, pressed=None, sides=False, bary=None):
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
    Zface = None
    if paint_bangs:   # (and in front of the eyes and the brows. Their surface is not skin's colour (the skin alone let those locks through) and
        # their whites read as hair: the face is the layer furthest back of those turned to the front camera, the locks (two corners
        # hair or more) what is in front of it. Not further out by the eyes (tried, up to 5.8 cm: it cut the locks beside them
        # in two, their halves black shards from the other side; there the side images hide them, side_hide))
        fn_ = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); fn_ /= np.maximum(np.linalg.norm(fn_, axis=1, keepdims=True), 1e-12)
        ff = (fn_ @ fwd > .2) & (C[:, 2] > .02)
        Uq, Vq, Dq = proj(Q); Zface = -zbuffer(Uq, Vq, -Dq, I[ff], W, H)
        zf = Zface[vi, ui]
        over |= np.isfinite(zf) & (d > zf + DROP_DZ) & (hair_v[I].sum(1) >= 2) & (C[:, 1] < top) & (np.abs(C[:, 0] - mid) < side)
    part = np.zeros(len(I), bool)
    if paint_bangs:   # (no holes: Meshy's skin has gaps under some of its locks. Those lying on the face (within HIDE[8] m of it) that cover
        # one, seen from the front or a side image's camera, stay: part of the face, painted as its skin; the cheek's was a dark dot.
        # Under the eyes only: over them the bangs are painted on the forehead, the triangles kept there were skin's patches in the hair)
        near = over & np.isfinite(zf) & (d - zf < HIDE[8]) & (C[:, 1] < eye_m - BANGS_LOW)
        for view in ('fronte',) + HIDE_ORDER:
            Fv = drawing(view)[1]
            for _ in range(3):
                Zb, pj_ = view_depth(Q, I[~over], cams[view], Fv.shape[1], Fv.shape[0]); nk = np.nonzero(near & over)[0]
                g = nk[covers_gap(Q, I, nk, Zb, pj_)]
                if not len(g): break
                over[g] = False; part[g] = True
        print('face: %d of the triangles over the face kept: on it, over gaps of its skin' % int(part.sum()))
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
    hide, locks, force = side_hide(Q, I, keep, vc, hair_v, cams, mid, eye_m, chin_m, is_skin) if sides else (None, None, None)
    if hide is not None:
        for v_ in hide: hide[v_] &= ~part; locks[v_] &= ~part
        force |= part & keep
    # the face's texels: painted from the images
    Ik = I[keep]
    region = (np.abs(pos[:, 0] - mid) < AREA[0]) & (pos[:, 1] > chin_m - AREA[1]) & (pos[:, 1] < top + AREA[2]) & (pos[:, 2] > AREA[3])
    cls = (is_skin(out[ys, xs]) | skin_t[ks]) if not paint_all else region   # ('paint': all of the circled area, hair or skin, from the images)
    if pressed is not None: cls = cls | pressed[I[ks]].any(1)   # (the pressed temples: painted as the profiles draw them, hair or skin)
    if force is not None: cls = cls | force[ks]   # (the hair triangles that are part of the face: as its skin)
    if paint_bangs:   # (the features whatever their colour: under the left eye's locks, cut short, Meshy had painted them over the eye, white
        # and dark streaks across it; on the face's own layer: the locks left further in front took the eye's drawing, pieces of it before the eye from the side)
        ut, vt, dt = proj(pos); uti, vti = np.clip(np.round(ut).astype(int), 0, W - 1), np.clip(np.round(vt).astype(int), 0, H - 1)
        cls = cls | ((feat_zone(pos, nor, fwd, mid, eye_m, chin_m) > .5) & (dt < Zface[vti, uti] + 2 * DROP_DZ))
    sel = np.nonzero(keep[ks] & cls & ~ear_v[I[ks]].any(1) & ~collar_v[I[ks]].any(1)
                     & ~((np.abs(pos[:, 0] - mid) > EAR[0]) & (pos[:, 2] < EAR[1])) & (pos[:, 1] < top + (AREA[2] if paint_all else 0)))[0]
    p, n = pos[sel], nor[sel]
    pr_sel = pressed[I[ks[sel]]].any(1) if pressed is not None else np.zeros(len(sel), bool)
    sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - a) / (b - a), 0, 1))
    zone = feat_zone(p, n, fwd, mid, eye_m, chin_m)
    acc = np.zeros((len(sel), 3)); wsum = np.zeros(len(sel)); seen_any = np.zeros(len(sel), bool)
    for view, cam in cams.items():
        D, F = (Dfr, Ffr) if view == 'fronte' else drawing(view); Hv, Wv = F.shape
        FM = face_mask(D, F, is_skin, is_hair)
        if paint_bangs: FM = FM & ~lock_lines(D, F, is_skin, is_hair)   # (not the outlines of the locks it draws over the face: on the skin without
        # their lock, the front image's lock's tip was two dark strokes on the cheek from the 3/4)
        hv = hide[view] if hide is not None and view in hide else None   # (the side images: the head as seen from there)
        Z, pj = view_depth(Q, Ik if hv is None else I[keep & ~hv], cam, Wv, Hv); u, v, dep = pj(p)
        ui, vi = np.clip(np.round(u).astype(int), 0, Wv - 1), np.clip(np.round(v).astype(int), 0, Hv - 1)
        t = np.radians(cam['yaw']); facing = n @ np.array([np.sin(t), 0, np.cos(t)])
        vis = (dep >= Z[vi, ui] - SEEN) & (facing > MIN_FACING) & (u >= 0) & (u < Wv - 1) & (v >= 0) & (v < Hv - 1)
        if hv is not None: vis &= ~hv[ks[sel]]
        seen_any |= vis
        ok = vis & (F[vi, ui] if paint_all else FM[vi, ui])   # (all of the figure: its hair and its lines too)
        if pressed is not None: ok |= vis & F[vi, ui] & pr_sel   # (the pressed temples: all of the drawing there)
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
    done = np.zeros(len(ks), bool); done[sel[painted]] = True
    under = ~painted & seen_any & (n @ fwd > .3)   # (seen, but every image draws hair there: under the bangs)
    if sheet: out[ys[sel[under]], xs[sel[under]]] = UNDER   # (without the sheet: as it was, the skin with its shadows under Meshy's locks)
    print('face: %d texels painted from the images (%d of the features from the front one), %d under the bangs in the skin\'s shadow' % (
        int(painted.sum()), int((painted & (zone > .5)).sum()), int(under.sum())))
    if paint_bangs and not paint_all:   # the front image's bangs painted on the forehead's skin where the model shows it (from the front; paint_all does it with the others)
        FMf = face_mask(Dfr, Ffr, is_skin, is_hair) & ~lock_lines(Dfr, Ffr, is_skin, is_hair)   # (the bangs with their outlines)
        Z2, pj2 = view_depth(Q, Ik, fr, W, H); u, v, dep = pj2(p)
        ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
        seen = (dep >= Z2[vi, ui] - SEEN) & (n @ fwd > BANGS_FACING) & (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
        hair_px = Ffr[vi, ui] & ~FMf[vi, ui] & (p[:, 1] > eye_m - BANGS_LOW)
        k = seen & hair_px
        x0, y0 = np.clip(np.floor(u).astype(int), 0, W - 2), np.clip(np.floor(v).astype(int), 0, H - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        col = (Dfr[y0, x0] * (1 - fx) + Dfr[y0, x0 + 1] * fx) * (1 - fy) + (Dfr[y0 + 1, x0] * (1 - fx) + Dfr[y0 + 1, x0 + 1] * fx) * fy
        out[ys[sel[k]], xs[sel[k]]] = col[k]
        done[sel[k]] = True
        print('face: %d texels of the forehead painted with the front image\'s bangs' % int(k.sum()))
    if hide is not None:
        side_paint(out, Q, I, keep, hide, locks, is_skin, ys, xs, ks, pos, nor, ear_v, collar_v, cams, mid, eye_m, chin_m, done=done)
        skin_fill(out, I, ys, xs, ks, pos, hair_v, ear_v, collar_v, done, keep, mid, chin_m, top, is_skin, force)
    if not sheet: return keep, None, hide
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
    return keep, (sp, suv, np.array(tris, np.int64), rgba), hide
