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
from it or None, the hair's triangles that are part of the face or None, the texels side_paint painted by the eyes' outer
corners where the front image had painted nothing or None)."""
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
JAW_UNDER = (.01, -.4)             # see feat_zone(): under the chin plus [0] m, the texels facing down (normal's y under [1]) are not the front image's
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
HIDE_ORDER = ('profilo_dx', '34_dx', '34_sx', 'profilo_sx')   # (the side images, his right's then his left's; the head's aHide has one value per side: HIDE_VIEWS)
HIDE = (2, 5, .05, 22., (.03, .075), 40, .04, -.02, .006)   # see side_hide(): the drawing's skin eroded [0] px; up to [1] layers; the skin behind within [2] m;
                                  # from [3] degrees around the head; y from the chin minus [4][0] to the eyes plus [4][1] (m); pieces under [5]
                                  # triangles; no holes: a surface behind each within [6] m; the camera's half of the head: depth over [7] m;
                                  # a hair triangle over a gap of the face within [8] m of it: part of the face, painted as its skin
SIDE_PAINT = (24., 10., (.03, .075), 105., 15.)   # see side_paint(): from [0] degrees around the head, fading in over [1]; y from the chin minus [2][0] to
                                  # the eyes plus [2][1] (m); up to [3] degrees, behind the ear, fading out over [4]
EAR_BOX = (.057, .035, (1.545, 1.625))   # the ear (see side_hide's standing): |x - middle| over [0], |z| under [1], y in [2] (m)
SIDE_POW, SIDE_FACING = 24., (.05, .35)  # side_paint's weights: how much the texel faces each image, to this power; seen by it facing it over [0], the skin's triangles over [1]
SIDE_LINE = (90, .12)             # side_paint: a line (darker than [0]) from an image only as it faces the texel more than the other by [1]
SKIN_FILL = (.075, .0, .01, 1.58, .012, .035)   # see skin_fill(): the front ([0], [1], [2]); all round the neck under [3] m; the jaw's shadow under the chin plus [4];
# within [5] m under the forehead's top only the triangles with a corner skin's
JEWEL = (30, 300, (110, 220), (20, 95, 1100), 110, 5, 60, 9)   # see jewel_mask()
LINE_RULE = (90, .5, 8)           # the images' dark lines (under [0]) on the skin, but the front image's: only from an image the texel faces over
                                  # [1]; not within [2] px of the figure's edge (its outer line: on the neck's side it was black blobs from behind)
NECK_FACING = .35                 # the neck (under the chin or behind the ears' plane): only from an image it faces over this
UNDER_EAR = (.03, (1.545, 1.578), .003)   # under and behind the ears (|x - middle| over [0], y in [1], z under [2]; the skin's triangles): no dark
                                  # lines (the profile's lobe is bigger than the model's: its outline fell on the neck, a black arc from behind)
NECK_LOW = 1.522                  # the neck's skin under this (m, just over the collar's rim): no dark line from the images (their collar's rim)
NECK_SKIN = 1.545                 # side_paint: the neck's skin under this (m) takes the images' skin alone, not their hair nor its outlines
BEHIND_EAR = 92.                  # side_paint: the hair's triangles further round the head than this (degrees) take no skin from the images
LOCK_LINE = (5, 120, 6)           # see lock_lines()
SCRAP = (40, .0025, .075)         # see face(): the hair's scraps lying on the face
FREE_LOCK = (.006, 60, .5, .02)   # see free_locks()
HIDE_WHOLE = 1 / 3                # see side_hide(): a lock hanging before the face is hidden whole from its side if over this share of its area is
HIDE_IN = (.2, 80., 4)            # see side_hide(): the inner walls behind the hidden locks
EYE_KEEP = .004                   # see face(): the eyes and the brows as painted before the side images, and this far around them (m): never the side images'
HIDE_FOOT = (3, 70.)              # see side_hide(): the hidden locks' feet: this many rings of triangles next to them, not further round the head than [1] degrees
CUT = (.001, .0009, 120.)          # see side_paint(): the lock's fill reaching the eyes' kept zone (within [0] m) with no outline, its texels joined within [1] m, pieces up to [2] mm2
LOCK_FILL = 110                   # see face(): the hair's fill colours (not its lines) are lighter than this


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


def jewel_mask(D, F, boxes, is_skin, is_hair, is_purple):
    """The earrings an image draws (boxes: where the model's earrings fall in it, px): the crystal (the purple pieces
    over JEWEL[1] px that touch a box grown JEWEL[0] px, no wider than JEWEL[2][0] px nor taller than JEWEL[2][1]: not
    the collar's trim), the bead and the hook over it (the silver pieces in the column over the crystal's top, JEWEL[3]
    px wide and tall, clear of its sides and under JEWEL[3][2] px: not the hair behind; one after the other, each within
    8 px of the last) and their outlines (the dark, silver and purple within JEWEL[5] px). The drawn earrings are wider
    than the model's and a little off: painted on the skin they were a second earring on the neck, a purple and black
    ladder beside the crystal, a lavender bead on the lobe."""
    H, W = F.shape; J = np.zeros((H, W), bool); L = D.mean(2)
    pur = is_purple(D) & F; silver = is_hair(D) & ~is_skin(D) & F; dark = (L < JEWEL[4]) & F
    gem = pur & (D[..., 2] - D[..., 1] > JEWEL[6])   # (the crystal's purples: not the hair's deep shadows, purple too behind the ears)
    lab, _ = ndimage.label(gem); objs = ndimage.find_objects(lab)
    for (x0, y0, x1, y1) in boxes:
        m = JEWEL[0]; win = np.zeros((H, W), bool); win[max(0, y0 - m):min(H, y1 + m), max(0, x0 - m):min(W, x1 + m)] = True
        ids = np.unique(lab[win]); ids = [k for k in ids[ids > 0] if (lab == k).sum() > JEWEL[1] and objs[k - 1][1].stop - objs[k - 1][1].start < JEWEL[2][0]
                                          and objs[k - 1][0].stop - objs[k - 1][0].start < JEWEL[2][1]]
        if not ids: continue
        cry = np.isin(lab, ids); ys_, xs_ = np.nonzero(cry); cy0 = ys_.min(); ax = int(round(xs_[ys_ < cy0 + 6].mean()))   # (its top: the column the hook hangs in)
        bx0, bx1 = max(0, ax - JEWEL[3][0]), min(W, ax + JEWEL[3][0] + 1); band = np.zeros((H, W), bool); band[max(0, cy0 - JEWEL[3][1]):cy0 + 6, bx0:bx1] = True
        ls, n = ndimage.label(silver & band); acc = cry.copy()
        left = [k + 1 for k, sl in enumerate(ndimage.find_objects(ls)) if sl[1].start > bx0 and sl[1].stop < bx1 and (ls == k + 1).sum() < JEWEL[3][2]]
        for _ in range(4):
            near = ndimage.binary_dilation(acc, iterations=8); add = [k for k in left if (near & (ls == k)).any()]
            if not add: break
            acc |= np.isin(ls, add); left = [k for k in left if k not in add]
        J |= ndimage.binary_dilation(acc, iterations=JEWEL[5]) & (dark | silver | pur)
        J |= ndimage.binary_dilation(acc, iterations=JEWEL[7])   # (and their outline's soft rim, brown on the skin: left out, it was a dotted diamond round the crystal)
    return J


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
    # (not the jaw's underside: the front image's line under the chin, painted there, was a second black bar over the jaw's wedge from the side)
    z = z * np.where(p[:, 1] < chin_m + JAW_UNDER[0], sm(JAW_UNDER[1] - .2, JAW_UNDER[1], n[:, 1]), 1.)
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


def corner_pieces(Q, I, sel):
    """Of the triangles sel: those not in the largest piece joined edge to edge (what hangs from the rest by a corner
    alone, or by nothing)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    _, w = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); w = w.ravel(); t = np.nonzero(sel)[0]; out = np.zeros(len(I), bool)
    if not len(t): return out
    T = w[I[t]]; e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); e.sort(1); key = e[:, 0] * (int(w.max()) + 1) + e[:, 1]; tri = np.tile(np.arange(len(t)), 3)
    o = np.argsort(key, kind='stable'); key, tri = key[o], tri[o]; same = key[1:] == key[:-1]
    _, comp = connected_components(coo_matrix((np.ones(int(same.sum()), np.int8), (tri[:-1][same], tri[1:][same])), shape=(len(t), len(t))), directed=False)
    out[t[comp != np.bincount(comp).argmax()]] = True
    return out


def under_ears(p, mid):
    """Per point: under and behind an ear (UNDER_EAR)."""
    return (np.abs(p[:, 0] - mid) > UNDER_EAR[0]) & (p[:, 1] > UNDER_EAR[1][0]) & (p[:, 1] < UNDER_EAR[1][1]) & (p[:, 2] < UNDER_EAR[2])


def free_locks(Q, I, hair_v, cams, mid, side=None):
    """Meshy's locks hanging before the face: the hair's pieces (two corners hair or more, welded, FREE_LOCK[1]
    triangles or more) standing over FREE_LOCK[0] m before the face's layer seen from the front camera. Returns, per
    triangle, whether it is of one hanging free, then its piece (-1: none; side_hide() hides a piece from its side whole
    or not at all). Hanging free: less than FREE_LOCK[2] of its area within side (PAINT_SIDE) of the face's middle (the others
    are the bangs face() leaves out, painted on the forehead) and in the median over FREE_LOCK[3] m off the head seen
    from both of its side's images too (the big one before his left brow; not the temples' locks lying on the head).
    Those are kept whole and unpainted: face() cut this one lengthwise at PAINT_SIDE (its inner wall out: an open
    shell, the outline's black along the cut, its inside seen from his right), the left images' under-hair lines were
    painted across it (bars) and their skin on it (patches)."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    side = PAINT_SIDE if side is None else side
    C = Q[I].mean(1); nh = hair_v[I].sum(1); x = C[:, 0] - mid
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); ar = .5 * np.linalg.norm(fn, axis=1); fn /= np.maximum(2 * ar[:, None], 1e-12)
    def off(view, sel, without=None):   # (per triangle: how far before the furthest layer turned to this camera, of the triangles sel)
        cam = cams[view]; F = drawing(view)[1]; H, W = F.shape
        _, pj = view_depth(Q, I[:1], cam, W, H); u, v, d = pj(C); uq, vq, dq = pj(Q)
        t = np.radians(cam['yaw']); turned = (fn @ np.array([np.sin(t), 0, np.cos(t)]) > .2) & sel(d)
        if without is not None: turned[without] = False
        Zs = -zbuffer(uq, vq, -dq, I[turned], W, H)
        return d - Zs[np.clip(np.round(v).astype(int), 0, H - 1), np.clip(np.round(u).astype(int), 0, W - 1)]
    s = off('fronte', lambda d: C[:, 2] > .02); s = np.where(np.isfinite(s), s, 0.)
    idx = np.nonzero((nh >= 2) & (s > FREE_LOCK[0]))[0]; free = np.zeros(len(I), bool); piece = np.full(len(I), -1)
    if not len(idx): return free, piece
    _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel()
    A = csr_matrix((np.ones(3 * len(idx)), (np.repeat(np.arange(len(idx)), 3), wv[I[idx]].ravel())), shape=(len(idx), wv.max() + 1))
    n, lab = connected_components(A @ A.T, directed=False)
    for k in range(n):
        t = idx[lab == k]
        if len(t) < FREE_LOCK[1]: continue
        piece[t] = k
        if ar[t][np.abs(x[t]) < side].sum() >= FREE_LOCK[2] * ar[t].sum(): continue
        med = []
        for view in HIDE_VIEWS['dx' if x[t].mean() < 0 else 'sx']:
            so = off(view, lambda d: d > HIDE[7], without=t)[t]; so = so[np.isfinite(so)]
            med.append(np.median(so) if len(so) else np.inf)
        if min(med) > FREE_LOCK[3]: free[t] = True
        print('face: a lock of %d triangles before the face, %.0f..%.0f mm from its middle, %.0f mm off the head from its side: %s' % (
            len(t), 1e3 * x[t].min(), 1e3 * x[t].max(), 1e3 * min(med), 'hanging free, kept whole' if free[t[0]] else 'on the temple'))
    return free, piece


def side_hide(Q, I, keep, vc, hair_v, cams, mid, eye_m, chin_m, is_skin, ear_v=None, free=None, piece=None):
    """Meshy's locks over the temples and the cheeks that the side images (the profile and the 3/4 of each side,
    HIDE_VIEWS) do not draw: hidden when the head is seen from that side (src/e_model.js mdHeadHide, the head's aHide),
    kept from the front, where the front image draws them by the eyes (Denis, 11/11 night, circling both: the images do
    not agree on them; pressed onto the head for the side, they went from the front too). Per image, layer by layer
    (up to HIDE[1]): the hair triangles seen from it in front of the skin (within HIDE[2] m behind) where it draws the
    face (skin_face, eroded HIDE[0] px; the middle and two corners), on its side of the head (HIDE[3] degrees around it
    from the face's front, y from the chin minus HIDE[4][0] to the eyes plus HIDE[4][1]); then the hair's pieces this
    leaves under HIDE[5] triangles next to them. One set per side, the two images' together (each its own, the game
    swapped them at the angle between the two, -47 degrees, which lies between his guard and his block: a lock by his
    eye flicked on every block and blinked walking back), and the locks hanging before the face (piece, free_locks())
    whole or not at all: all of one if over HIDE_WHOLE of its area is hidden (cut where the image stops drawing skin
    behind it, a lock was a torn stump over the eye, a band cut square over the brow, and sawn off from behind). Under
    them is Meshy's skin (the temples' scalp: no holes), painted from the image that sees it by side_paint(). Whole
    triangles (their corners split from the rest's in the package: hidden by shares, the skin next to them was cut
    too, the back of the head seen through). Returns {view: the triangles hidden from it (over I; its side's set)},
    {view: the locks standing over the head (seen from any camera, hidden or not; the same for every view)} and the
    hair triangles that are part of the face (over its gaps)."""
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    nh = hair_v[I].sum(1); hair_t = nh >= 2   # (the locks: two corners hair or more)
    C = Q[I].mean(1); az = np.degrees(np.arctan2(C[:, 0] - mid, C[:, 2] - PRESS_WIN[4]))
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); ar = .5 * np.linalg.norm(fn, axis=1); fn /= np.maximum(2 * ar[:, None], 1e-12)
    ywin = (C[:, 1] > chin_m - HIDE[4][0]) & (C[:, 1] < eye_m + HIDE[4][1])
    _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel()
    res, lock, force = {}, {}, np.zeros(len(I), bool)
    not_ear = ~ear_v[I].any(1) if ear_v is not None else np.ones(len(I), bool)   # (not the earrings: their hooks are hair's colour)
    ns = is_skin(vc)[I].sum(1)
    def layer(cam, W, H):   # (per triangle: the layer furthest back of those turned to this camera lies behind it, within HIDE[2] m)
        _, pj = view_depth(Q, I[:1], cam, W, H); _, _, d_ = pj(C); uq_, vq_, dq_ = pj(Q); u_, v_, _ = pj(C)
        tv_ = np.radians(cam['yaw']); turned_ = (fn @ np.array([np.sin(tv_), 0, np.cos(tv_)]) > .2) & (d_ > HIDE[7])
        Zs_ = -zbuffer(uq_, vq_, -dq_, I[keep & turned_], W, H); zs_ = Zs_[np.clip(np.round(v_).astype(int), 0, H - 1), np.clip(np.round(u_).astype(int), 0, W - 1)]
        return np.isfinite(zs_) & (zs_ < d_ - DROP_DZ) & (zs_ > d_ - HIDE[2])
    def no_holes(hid, cam, W, H, proj, d, zs, turned, only=None):   # (from this image, behind all of each hidden triangle another surface within HIDE[6] m; else
        # it stays, and lying on the face (within HIDE[8] m of it) it is part of it: Meshy's skin has gaps under some of its locks)
        for _ in range(4):
            Zb, _ = view_depth(Q, I[keep & ~hid], cam, W, H); hk = np.nonzero(hid if only is None else hid & only)[0]
            g = hk[covers_gap(Q, I, hk, Zb, proj)]
            if not len(g): break
            hid[g] = False; force[g[(d[g] - zs[g] < HIDE[8]) & turned[g]]] = True   # (turned to the camera: a lock's inner side painted as skin was a skin-coloured wedge in the hair)
    Ff = drawing('fronte')[1]; stand = layer(cams['fronte'], Ff.shape[1], Ff.shape[0])   # (from the front too: the locks hanging before the face)
    for side, sign in (('dx', -1), ('sx', 1)):
        cand = keep & hair_t & ywin & (az * sign > HIDE[3]) & not_ear
        both = np.zeros(len(I), bool); seen = {}; on_skin = np.zeros(len(I), bool)
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
            zk = (-zbuffer(uq, vq, -dq, I[keep & turned & (ns == 3)], W, H))[vi, ui]; on_skin |= np.isfinite(zk) & (zk < d - DROP_DZ) & (zk > d - HIDE[2])   # (over the skin's own triangles)
            for _ in range(HIDE[1]):
                Z, _ = view_depth(Q, I[keep & ~hid], cam, W, H)
                c = cand & ~hid & (d >= Z[vi, ui] - SEEN) & over & behind
                if not c.any(): break
                hid |= c
            no_holes(hid, cam, W, H, proj, d, zs, turned, only=None if piece is None else piece < 0)   # (the locks before the face: decided whole, below)
            both |= hid; stand |= behind; seen[view] = (cam, W, H, proj, d, zs, turned)
        n0 = int(both.sum()); whole = np.zeros(len(I), bool); shown = np.zeros(len(I), bool)
        if piece is not None:   # (the locks hanging before the face on this side: whole or not at all)
            for k in np.unique(piece[(piece >= 0) & keep & not_ear & (((C[:, 0] - mid) * sign) > 0)]):
                t = (piece == k) & keep & not_ear
                if ((C[t, 0] - mid) * sign).mean() <= 0: both &= ~t; shown |= t; continue   # (the other side's lock: whole)
                share = ar[t & both].sum() / ar[t].sum()
                if share > HIDE_WHOLE: both |= t; whole |= t
                else: both &= ~t; shown |= t
                print('face: the lock of %d triangles before the face on his %s: %.0f%% of it where the images draw the face, %s' % (
                    int(t.sum()), 'right' if side == 'dx' else 'left', 100 * share, 'hidden whole from that side' if share > HIDE_WHOLE else 'shown whole'))
        n1 = int(both.sum())
        for _ in range(HIDE_FOOT[0]):   # (and the hidden locks' feet: the hair's triangles next to them lying over the skin seen from one of this
            # side's images, in front of the ear. Where the image draws a brow's end or a line there, not skin, they stayed: lavender
            # flecks on the temple by the brow)
            hv = np.zeros(wv.max() + 1, bool); hv[wv[I[both]].ravel()] = True
            foot = cand & on_skin & ~both & ~shown & (az * sign < HIDE_FOOT[1]) & hv[wv[I]].any(1)
            if not foot.any(): break
            both |= foot
        print('face: %d triangles of the hidden locks\' feet on his %s' % (int(both.sum()) - n1, 'right' if side == 'dx' else 'left'))
        # (no holes from either image, the feet too; not the whole locks: they hang before the face, and where one is seen beyond the
        # face's edge nothing is behind it, which is no hole)
        for view in HIDE_VIEWS[side]: no_holes(both, *seen[view], only=~whole)
        loose = np.zeros(len(I), bool)
        for hairs in (True, False):   # (the pieces this leaves: the hair's small ones touching what is hidden, then whatever is left hanging in
            # the air, any colour: Meshy's dark lines along a hidden lock were specks beside the head)
            rest = np.nonzero(keep & ~both & not_ear & (hair_t if hairs else True))[0]
            if not len(rest): continue
            A = csr_matrix((np.ones(3 * len(rest)), (np.repeat(np.arange(len(rest)), 3), wv[I[rest]].ravel())), shape=(len(rest), wv.max() + 1))
            _, lab = connected_components(A @ A.T, directed=False); sz = np.bincount(lab)
            hv = np.zeros(wv.max() + 1, bool); hv[wv[I[both]].ravel()] = True
            touch = np.zeros(lab.max() + 1, bool); np.logical_or.at(touch, lab, hv[wv[I[rest]]].any(1))
            sm_ = rest[(sz[lab] < HIDE[5]) & touch[lab]]; both[sm_] = True; loose[sm_] = True
        print('face: %d triangles in small pieces left by the hidden locks on his %s: hidden with them' % (int(loose.sum()), 'right' if side == 'dx' else 'left'))
        for view in HIDE_VIEWS[side]:   # (of those, the ones lying on the face over a gap of its skin stay, part of it; the others hang in the air:
            # nothing behind them is no hole)
            cam, W, H, proj, d, zs, turned = seen[view]
            no_holes(both, cam, W, H, proj, d, zs, turned, only=loose & np.isfinite(zs) & (d - zs < HIDE[8]))
        # (and the inner walls this opens: behind a hidden lock are the insides of the locks next to it, turned away from the camera,
        # grey-lavender blocks on the temple. The hair's triangles turned away from both of this side's cameras (by over HIDE_IN[0]),
        # in front of the ear (HIDE_IN[1] degrees), that one of the two now sees (the front-most there): hidden too, layer by layer
        # (HIDE_IN[2]), unless nothing is behind them (no_holes))
        dirs = [np.array([np.sin(np.radians(cams[v_]['yaw'])), 0, np.cos(np.radians(cams[v_]['yaw']))]) for v_ in HIDE_VIEWS[side]]
        inner_c = keep & hair_t & not_ear & ywin & (az * sign > HIDE[3]) & (az * sign < HIDE_IN[1]) & np.all([fn @ dv < -HIDE_IN[0] for dv in dirs], 0)
        inner = np.zeros(len(I), bool)
        for _ in range(HIDE_IN[2]):
            new = np.zeros(len(I), bool)
            for view in HIDE_VIEWS[side]:
                cam, W, H, proj, d, zs, _t = seen[view]
                Z, _ = view_depth(Q, I[keep & ~both], cam, W, H); u, v, _ = proj(C)
                new |= inner_c & ~both & (d >= Z[np.clip(np.round(v).astype(int), 0, H - 1), np.clip(np.round(u).astype(int), 0, W - 1)] - SEEN)
            if not new.any(): break
            both |= new; inner |= new
            for view in HIDE_VIEWS[side]: no_holes(both, *seen[view], only=inner)
            inner &= both
        print('face: %d triangles of inner walls seen through the hidden locks on his %s: hidden with them' % (int(inner.sum()), 'right' if side == 'dx' else 'left'))
        loose = corner_pieces(Q, I, keep & ~both) & hair_t & not_ear & ~force   # (and what the hidden set leaves hanging by a corner alone: a flag of 5 cm2 beside his right temple)
        both |= loose; print('face: %d triangles hanging by a corner once the locks on his %s are hidden: hidden with them' % (int(loose.sum()), 'right' if side == 'dx' else 'left'))
        for view in HIDE_VIEWS[side]: res[view] = both
        stand |= both
        print('face: from his %s side, %d of Meshy\'s triangles over the temple and the cheek hidden (%d where its images draw the face; whole locks and small pieces with them)' % (
            'right' if side == 'dx' else 'left', int(both.sum()), n0))
    # the locks standing over the head, seen from any of the five cameras (the same for every view: a lock before the face
    # is beyond its edge from the side, nothing behind it there, and took the side image's skin, a skin-coloured patch on
    # it from the other side): the hair's triangles and, but on the ears (EAR_BOX: their shadows are not skin's colour
    # either), those neither hair's nor skin's (the dark lines Meshy painted between its locks)
    ear = (np.abs(C[:, 0] - mid) > EAR_BOX[0]) & (np.abs(C[:, 2]) < EAR_BOX[1]) & (C[:, 1] > EAR_BOX[2][0]) & (C[:, 1] < EAR_BOX[2][1])
    standing = keep & stand & ~force & ((nh >= 2) | (ns < 2)) & ~(ear & ((ns >= 1) | (nh < 2)))   # (the ears' greyish shadows read as hair: with a corner skin's, the ear's own)
    if ear_v is not None:
        for view in res: assert not (res[view] & ear_v[I].any(1)).any(), 'an earring triangle hidden from ' + view
    if free is not None: standing |= free & keep
    for view in res: lock[view] = standing
    print('face: %d hair triangles over gaps of the face\'s skin, lying on it: part of the face; %d triangles of locks standing over the head' % (int(force.sum()), int(standing.sum())))
    return res, lock, force


def hide_shares(Q, I, keep, hid):
    """Per vertex: the share (by area) of its kept triangles that hid holds, alike over its copies along the texture's
    seams. Not used: hidden by shares, the skin next to the locks was cut too (side_hide(): whole triangles)."""
    _, wld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wld = wld.ravel()
    ar = .5 * np.linalg.norm(np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]), axis=1) * keep
    tot = np.zeros(wld.max() + 1); np.add.at(tot, wld[I].ravel(), np.repeat(ar, 3))
    hs = np.zeros(wld.max() + 1); np.add.at(hs, wld[I].ravel(), np.repeat(ar * (hid & keep), 3))
    return (hs / np.maximum(tot, 1e-12))[wld]


def side_paint(out, Q, I, keep, hide, locks, is_skin, ys, xs, ks, pos, nor, ear_v, collar_v, cams, mid, eye_m, chin_m, done=None, jm=None, skin_tri=None, is_hair=None, hair_tri=None, free=None, is_purple=None, keep_zone=None, front_done=None, skin2_tri=None):
    """The head's sides as their images draw them, seen from that side (Meshy's locks there hidden, side_hide): each
    texel on the side (SIDE_PAINT: from [0] degrees around the head, fading in over [1], to [3] behind the ear, fading
    out over [4]: further round it painted the profiles' neck on the hair behind the ears and their edge-on streaks on
    the nape; y from the chin minus [2][0] to the eyes plus [2][1]; not the earrings, the collar, the features the front
    image draws) from the side's
    images that see it then (the profile, the 3/4), all of their drawing (the skin, its lines and shading, the locks
    they draw over the temple; not their skin on a lock standing over the face, locks), weighted by how much it faces
    each (to the power SIDE_POW); blended over what was painted at the fade. Returns how many texels, and which of
    them lie by the eyes' outer corners where no image had painted (below)."""
    sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - a) / (b - a), 0, 1))
    th = np.radians(cams['fronte']['yaw']); fwd_f = np.array([np.sin(th), 0, np.cos(th)])
    az = np.degrees(np.arctan2(pos[:, 0] - mid, pos[:, 2] - PRESS_WIN[4]))
    yw = sm(chin_m - SIDE_PAINT[2][0] - .01, chin_m - SIDE_PAINT[2][0], pos[:, 1]) * (1 - sm(eye_m + SIDE_PAINT[2][1], eye_m + SIDE_PAINT[2][1] + .01, pos[:, 1]))
    zone = feat_zone(pos, nor, fwd_f, mid, eye_m, chin_m)
    # (by the eyes' outer corners (EYE_ZONE, beyond the features' FEAT[0]) the front image has the say, but there it sees the locks standing
    # before the temple, not the temple, and paints nothing. The temple kept Meshy's skin with the shadow of those locks, hidden from the
    # side, or the 3/4 image's shadow alone where that draws skin and the profile a lock: a brown patch between the ear and the eye, the tip
    # of a drawn lock under it (Denis, 11/11, circling it on the preview). What the front image did not paint there is the side images' as
    # the rest of the temple; not the eyes and the brows themselves (keep_zone), which stay as they were)
    loose = np.zeros(len(ks), bool)
    if front_done is not None and keep_zone is not None:
        loose = ~front_done & ~keep_zone & (zone > 0) & (np.abs(pos[:, 0] - mid) > FEAT[0]); zone = np.where(loose, 0., zone)
    li = np.nonzero(loose)[0]; prev_c = out[ys[li], xs[li]].copy(); prev_d = done[li].copy() if done is not None else None
    base = yw * (1 - zone) * ~ear_v[I[ks]].any(1) * ~collar_v[I[ks]].any(1) * keep[ks]   # (the ears too: as the side images draw them, the hair over them)
    if free is not None: base = base * ~free[ks]   # (not the locks hanging free before the face: no image draws them where they are)
    total = 0; got_loose = np.zeros(len(ks), bool)
    for side, sign in (('dx', -1), ('sx', 1)):
        wwin = base * sm(SIDE_PAINT[0], SIDE_PAINT[0] + SIDE_PAINT[1], az * sign) * (1 - sm(SIDE_PAINT[3], SIDE_PAINT[3] + SIDE_PAINT[4], az * sign))
        sel = np.nonzero(wwin > 1e-3)[0]
        if not len(sel): continue
        p, n = pos[sel], nor[sel]; acc = np.zeros((len(sel), 3)); wsum = np.zeros(len(sel))
        samples = []
        sk3 = skin_tri[ks[sel]] if skin_tri is not None else np.zeros(len(sel), bool); u_ear = under_ears(p, mid) & sk3; n_skin = sk3 & (p[:, 1] < NECK_SKIN)
        h_back = (hair_tri[ks[sel]] if hair_tri is not None else np.zeros(len(sel), bool)) & (az[sel] * sign > BEHIND_EAR)   # (the hair behind the ear: see below)
        in_ear = (np.abs(p[:, 0] - mid) > EAR_BOX[0]) & (np.abs(p[:, 2]) < EAR_BOX[1]) & (p[:, 1] > EAR_BOX[2][0]) & (p[:, 1] < EAR_BOX[2][1])
        for view in HIDE_VIEWS[side]:   # (each image the head as seen from it: what it hides left out, what that shows painted from it)
            cam = cams[view]; D, F = drawing(view); H, W = F.shape
            LL = lock_lines(D, F, is_skin, is_hair) if is_hair is not None else None
            Z, pj = view_depth(Q, I[keep & ~hide[view]], cam, W, H); u, v, dep = pj(p)
            ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
            t = np.radians(cam['yaw']); facing = n @ np.array([np.sin(t), 0, np.cos(t)])
            vis = (dep >= Z[vi, ui] - SEEN) & (facing > np.where(sk3, SIDE_FACING[1], SIDE_FACING[0])) & (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1) & F[vi, ui] & ~hide[view][ks[sel]]
            if jm is not None: vis &= ~jm[view][vi, ui]   # (not the earrings it draws: jewel_mask)
            x0, y0 = np.clip(np.floor(u).astype(int), 0, W - 2), np.clip(np.floor(v).astype(int), 0, H - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
            col = (D[y0, x0] * (1 - fx) + D[y0, x0 + 1] * fx) * (1 - fy) + (D[y0 + 1, x0] * (1 - fx) + D[y0 + 1, x0 + 1] * fx) * fy
            vis &= ~(locks[view][ks[sel]] & is_skin(col))   # (a lock standing over the head keeps its hair's paint where the image draws
            # skin: painted as skin, it was skin-coloured pieces before the face from the other side)
            dk = col.mean(1) < LINE_RULE[0]
            vis &= ~(dk & ((facing < LINE_RULE[1]) | u_ear))   # (a dark line only from an image the texel faces; none under and behind the ears)
            if is_purple is not None: vis &= ~(sk3 & (is_purple(col) | ((p[:, 1] < NECK_LOW) & dk)))   # (nor the collar the images draw higher than the model's: face())
            if is_hair is not None: vis &= ~(u_ear & is_hair(col) & ~is_skin(col))   # (nor the hair the profile draws lower than the model's: a lavender blade on the neck behind the lobe)
            vis &= ~(h_back & is_skin(col))   # (the hair behind the ear turns to the front: the 3/4 image won there and draws its ear and cheek on it, a skin-coloured wedge behind the ear)
            if LL is not None: vis &= ~(n_skin & ((is_hair(col) & ~is_skin(col)) | LL[vi, ui]))   # (the neck's skin: not the mane's tips the profile draws lower than the model's, loose black ticks on bare neck)
            samples.append((np.where(vis, facing, -1.), col))
        if len(samples) > 1:   # (the ears from their profile alone where it sees them, the 3/4 where it does not: the two drawn ears do not fall
            # on the same place of the model's, mixed they were two brown blobs and a smeared line inside the ear)
            f0, c0 = samples[0]; f1, c1 = samples[1]; samples[1] = (np.where(in_ear & (f0 > -1), -1., f1), c1)
        for i_, (fc, col) in enumerate(samples):   # (a dark line only from the image that sees the texel clearly best: the other's
            # view of it, a little off, drew the profile's lines across the 3/4's cheek)
            other = np.max([f_ for j_, (f_, _) in enumerate(samples) if j_ != i_], axis=0) if len(samples) > 1 else np.full(len(fc), -1.)
            w = np.where(fc > -1, np.maximum(fc, 0) ** SIDE_POW, 0.)
            dark = col.mean(1) < SIDE_LINE[0]
            w = np.where(dark & (other > -1), w * sm(0, SIDE_LINE[1], fc - other), w)
            acc += w[:, None] * col; wsum += w
        ok = wsum > 0; k = sel[ok]; a = wwin[k][:, None]; got = acc[ok] / wsum[ok, None]
        if is_hair is not None:   # (a lock the image draws on the skin, where the side's zone fades into the front image's (by the eye's
            # corner): all of it or none. Blended, its edge there was a pale smear on the temple)
            lockc = sk3[ok] & is_hair(got) & ~is_skin(got); a = np.where(lockc[:, None], (a >= .5).astype(float), a)
        out[ys[k], xs[k]] = out[ys[k], xs[k]] * (1 - a) + got * a
        if done is not None: done[k] = True
        total += int(ok.sum()); got_loose[k] = loose[k]
    cut = 0
    if len(li) and keep_zone is not None and skin2_tri is not None and is_hair is not None:   # (the lock's fill reaching the kept zone with no outline
        # between: the drawn lock goes on over the eye's corner, where the kept zone stops it, cut on a straight line. Its piece of fill on the
        # skin's triangles that touches the zone goes back to what it was; the lock ends on its own outline)
        from scipy.spatial import cKDTree
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        gi = np.nonzero(got_loose)[0]; cg = out[ys[gi], xs[gi]]
        cand = gi[skin2_tri[ks[gi]] & is_hair(cg) & ~is_skin(cg) & (cg.mean(1) > LOCK_FILL)]
        if len(cand):
            kz = np.nonzero(keep_zone)[0]; dd, _ = cKDTree(pos[kz]).query(pos[cand], distance_upper_bound=CUT[0]); seed = np.isfinite(dd)
            pr = cKDTree(pos[cand]).query_pairs(CUT[1], output_type='ndarray')
            _, lab = connected_components(coo_matrix((np.ones(len(pr), np.int8), (pr[:, 0], pr[:, 1])), shape=(len(cand), len(cand))).tocsr(), directed=False)
            tri_a = .5 * np.linalg.norm(np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]), axis=1) * 1e6; cnt = np.bincount(ks, minlength=len(I))
            ta = tri_a[ks[cand]] / np.maximum(cnt[ks[cand]], 1); area = np.bincount(lab, weights=ta); hit = np.zeros(lab.max() + 1, bool); np.logical_or.at(hit, lab, seed)
            back = hit[lab] & (area[lab] <= CUT[2]); pos_in = np.searchsorted(li, cand[back])
            out[ys[cand[back]], xs[cand[back]]] = prev_c[pos_in]
            if done is not None: done[cand[back]] = prev_d[pos_in]
            got_loose[cand[back]] = False; cut = int(back.sum())
            print('face: the drawn locks\' fill cut on the eyes\' kept zone: %d pieces put back (%d texels, %s mm2), %d left (over %.0f mm2)' % (
                int((hit & (area <= CUT[2])).sum()), cut, ', '.join('%.0f' % a_ for a_ in area[hit & (area <= CUT[2])]), int((hit & (area > CUT[2])).sum()), CUT[2]))
    gl = np.nonzero(got_loose)[0]
    print('face: %d texels of the temples and the cheeks painted from the side images (as seen from the side; %d by the eyes\' corners no image had painted)' % (total, len(gl)))
    return total, (got_loose, prev_c[np.searchsorted(li, gl)] if len(gl) else np.zeros((0, 3)))


def skin_fill(out, I, ys, xs, ks, pos, hair_v, ear_v, collar_v, done, keep, mid, chin_m, top, is_skin, force=None, standing=None, skin_v=None):
    """The face's skin left unpainted (no image sees it: slivers folded under their neighbours, the skin behind a lock)
    and still in Meshy's hair paint, lavender or dark (it showed from other sides as marks on the cheek): on the skin's
    triangles (at most one corner hair's, not a lock standing over the head) of the head's front half (SKIN_FILL:
    |x - middle| under [0], z over [1], from the chin minus [2] up), the texels not skin's colour take the nearest
    painted skin texel's. Returns how many."""
    from scipy.spatial import cKDTree
    c = out[ys, xs]; skin_now = is_skin(c)
    base = keep[ks] & (hair_v[I[ks]].sum(1) <= 1) & ~ear_v[I[ks]].any(1) & ~collar_v[I[ks]].any(1)
    reg = base & (np.abs(pos[:, 0] - mid) < SKIN_FILL[0]) & (pos[:, 2] > SKIN_FILL[1]) & (pos[:, 1] > chin_m - SKIN_FILL[2]) & (pos[:, 1] < top)
    if skin_v is not None:   # (and all round the neck and under the ears, the triangles with two corners skin or more: Meshy's black wedges and
        # lavender patches no image sees, behind the earrings and under the tufts, were left on the skin there)
        reg |= base & (skin_v[I[ks]].sum(1) >= 2) & (pos[:, 1] < SKIN_FILL[3])
    if standing is not None: reg &= ~standing[ks]   # (not the locks standing over the head: their dark lines are not hair's colour either)
    if skin_v is not None:   # (nor Meshy's dark lines inside the hair, over the forehead's top: no corner hair's nor skin's, filled they were
        # skin-coloured slivers in the hair at the forelock's root)
        reg &= (skin_v[I[ks]].sum(1) >= 1) | (pos[:, 1] < top - SKIN_FILL[5])
    fz = force[ks] & keep[ks] & (pos[:, 2] > SKIN_FILL[1]) if force is not None else np.zeros(len(ks), bool)   # (and the hair triangles that are part of the face, side_hide; in front)
    if skin_v is not None:   # (under the jaw Meshy's black shadow stays: the drawn black wedge. Filled with skin it was eaten into teeth)
        jaw = (pos[:, 1] < chin_m + SKIN_FILL[4]) & (skin_v[I[ks]].sum(1) == 0); reg &= ~jaw; fz &= ~jaw
    todo = np.nonzero((reg | fz) & ~done & ~skin_now)[0]; src = np.nonzero(reg & done & skin_now & ~fz)[0]
    if len(todo) and len(src):
        _, j = cKDTree(pos[src]).query(pos[todo]); out[ys[todo], xs[todo]] = out[ys[src[j]], xs[src[j]]]
    print('face: %d texels of the skin no image sees, left in Meshy\'s hair paint, as the painted skin next to them' % len(todo))
    return len(todo)


def face(out, Q, N, UV, I, ys, xs, ks, pos, nor, vc, hair_v, ear_v, collar_v, mid, eye_m, chin_m, cams, is_skin, is_hair, sheet=True, paint_bangs=False, paint_all=False, pressed=None, sides=False, bary=None, free=None, piece=None):
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
    if paint_bangs:   # (and the hair's scraps left lying on the face: its pieces under SCRAP[0] triangles, all of them within SCRAP[1] m of the
        # face's layer, in its front. Part of the face, painted as its skin, without the hair's outline: under his right eye's outer
        # corner one was a dark dash with a grey smudge on the clean cheek)
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import connected_components
        _, wv_ = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv_ = wv_.ravel()
        ht = np.nonzero(~over & (hair_v[I].sum(1) >= 2))[0]
        A_ = csr_matrix((np.ones(3 * len(ht)), (np.repeat(np.arange(len(ht)), 3), wv_[I[ht]].ravel())), shape=(len(ht), wv_.max() + 1))
        _, lab_ = connected_components(A_ @ A_.T, directed=False); sz_ = np.bincount(lab_)
        on = np.isfinite(zf[ht]) & (d[ht] - zf[ht] < SCRAP[1]) & (np.abs(C[ht, 0] - mid) < SCRAP[2]) & (C[ht, 1] > chin_m) & (C[ht, 1] < top) & (C[ht, 2] > 0)
        off_ = np.zeros(lab_.max() + 1, bool); np.logical_or.at(off_, lab_, ~on)
        scr = ht[(sz_[lab_] < SCRAP[0]) & ~off_[lab_]]; part[scr] = True
        print('face: %d triangles of the hair\'s scraps lying on the face: part of it' % len(scr))
    if not sheet and not paint_bangs: over[:] = False   # ('skin': Meshy's locks kept)
    if paint_bangs and CARVE_VIEWS:   # (and in the profiles, Meshy's locks in front of the temple and the eye's outer corner where they draw the face)
        over |= carve(Q, I, hair_v, is_skin, is_hair, {k_: cams[k_] for k_ in CARVE_VIEWS}, mid, chin_m, top, skin_all=skin_t & ~over)
    if paint_bangs:   # (and the pieces of hair this leaves floating)
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import connected_components
        _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel(); rest = np.nonzero(~over)[0]
        A = csr_matrix((np.ones(3 * len(rest)), (np.repeat(np.arange(len(rest)), 3), wv[I[rest]].ravel())), shape=(len(rest), wv.max() + 1))
        _, lab = connected_components(A @ A.T, directed=False); sz = np.bincount(lab); over[rest[sz[lab] < VOTE[2]]] = True
    if free is not None: over &= ~free; part &= ~free   # (the locks hanging free before the face: whole, free_locks())
    if paint_bangs:   # (and what this leaves hanging by a corner: the stubs of the locks left out, a shard of 4 cm2 standing before the forehead's
        # top on his right, seen from every side; Denis, 11/11: "rimuovi se vedi le cose di troppo". Not what lies on the face, part of it)
        loose = corner_pieces(Q, I, ~over) & (hair_v[I].sum(1) >= 2) & ~part
        over |= loose; print('face: %d triangles of the hair hanging from the rest by a corner alone left out' % int(loose.sum()))
    keep = ~over
    print('face: %d of Meshy\'s triangles over the face left out (under %.3f m)' % (int(over.sum()), top))
    hide, locks, force = side_hide(Q, I, keep, vc, hair_v, cams, mid, eye_m, chin_m, is_skin, ear_v, free, piece) if sides else (None, None, None)
    JM, EDGE = {}, {}
    if paint_bangs:   # (per image: the earrings it draws, and its figure's outer LINE_RULE[2] px)
        from kael_head import is_purple
        for view, cam in cams.items():
            Dv, Fv = drawing(view); _, pjv = view_depth(Q, I[:1], cam, Fv.shape[1], Fv.shape[0]); boxes = []
            for sgn in (-1, 1):
                e = ear_v & ((Q[:, 0] - mid) * sgn > 0)
                if e.any(): ue, ve, _ = pjv(Q[e]); boxes.append((int(ue.min()), int(ve.min()), int(ue.max()) + 1, int(ve.max()) + 1))
            JM[view] = jewel_mask(Dv, Fv, boxes, is_skin, is_hair, is_purple); EDGE[view] = ndimage.distance_transform_edt(Fv) < LINE_RULE[2]
        print('face: the earrings the images draw, left out of the skin\'s painting: %s px' % ', '.join('%s %d' % (v_, int(m_.sum())) for v_, m_ in JM.items()))
    if hide is not None:
        for v_ in hide: hide[v_] &= ~part; locks[v_] &= ~part
        force |= part & keep
    elif paint_bangs: force = part & keep
    # the face's texels: painted from the images
    Ik = I[keep]
    region = (np.abs(pos[:, 0] - mid) < AREA[0]) & (pos[:, 1] > chin_m - AREA[1]) & (pos[:, 1] < top + AREA[2]) & (pos[:, 2] > AREA[3])
    cls = (is_skin(out[ys, xs]) | skin_t[ks]) if not paint_all else region   # ('paint': all of the circled area, hair or skin, from the images)
    if pressed is not None: cls = cls | pressed[I[ks]].any(1)   # (the pressed temples: painted as the profiles draw them, hair or skin)
    if force is not None: cls = cls | force[ks]   # (the hair triangles that are part of the face: as its skin)
    lock_t = None
    if locks is not None:   # (not the locks standing over the head, two corners hair or more: chosen by their colour, Meshy's skin-coloured texels
        # on them were painted as the face's skin, the last specks on the big forelock; filled as hair below)
        lock_t = next(iter(locks.values())) & (hair_v[I].sum(1) >= 2)
        if free is not None: lock_t = lock_t | (free & keep)
        cls = cls & ~lock_t[ks]
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
    acc = np.zeros((len(sel), 3)); wsum = np.zeros(len(sel)); seen_any = np.zeros(len(sel), bool); front_p = np.zeros(len(sel), bool)
    under_ear = under_ears(p, mid) & skin_t[ks[sel]]; neck = (p[:, 1] < chin_m) | (p[:, 2] < 0)
    for view, cam in cams.items():
        D, F = (Dfr, Ffr) if view == 'fronte' else drawing(view); Hv, Wv = F.shape
        FM = face_mask(D, F, is_skin, is_hair)
        if paint_bangs: FM = FM & ~lock_lines(D, F, is_skin, is_hair)   # (not the outlines of the locks it draws over the face: on the skin without
        # their lock, the front image's lock's tip was two dark strokes on the cheek from the 3/4)
        if paint_bangs and view == 'dietro': FM = ndimage.binary_erosion(is_skin(D) & F, iterations=2)   # (the nape has no drawn features: its skin alone,
        # not the rim between the drawn tips and the neck, pinkish slivers by the model's tips)
        if paint_bangs: FM = FM & ~JM[view]   # (nor the earrings it draws)
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
        if paint_bangs:   # (the images draw the collar higher on the neck than the model's: its purple trim and its black rim, painted on the neck's
            # skin, showed above the collar as the head tipped: a second trim line on the bare neck in the hit reaction)
            ok &= ~(skin_t[ks[sel]] & (is_purple(col) | ((p[:, 1] < NECK_LOW) & (col.mean(1) < LINE_RULE[0]))))
        if paint_bangs and view == 'fronte': ok &= ~((col.mean(1) < LINE_RULE[0]) & under_ear)   # (the front image's lines neither: a black arc on the neck behind the lobe)
        if paint_bangs and view != 'fronte':   # (LINE_RULE, UNDER_EAR, NECK_FACING)
            dk = col.mean(1) < LINE_RULE[0]
            ok &= ~(dk & ((facing < LINE_RULE[1]) | EDGE[view][vi, ui] | under_ear))
            ok &= ~(neck & (facing < NECK_FACING))
        w = np.where(ok, np.maximum(facing, 0) ** POW, 0.)
        if paint_all:   # (around the eyes the face first: where an image draws the face there, it wins over the hair the others draw)
            band = (p[:, 1] > eye_m - EYE_BAND[0]) & (p[:, 1] < eye_m + EYE_BAND[1])
            w = np.where(band & FM[vi, ui] & ok, w * FACE_PRIO + FACE_PRIO * 1e-9, w)
        w = w * zone if view == 'fronte' else w * (1 - zone)   # (the features: the front image's alone)
        if view == 'fronte': w = np.where(ok & (zone > 0), np.maximum(w, 1e-6 * zone), w); front_p = w > 0
        acc += w[:, None] * col; wsum += w
    painted = wsum > 0
    out[ys[sel[painted]], xs[sel[painted]]] = acc[painted] / wsum[painted, None]
    done = np.zeros(len(ks), bool); done[sel[painted]] = True
    fdone = np.zeros(len(ks), bool); fdone[sel[front_p]] = True   # (painted by the front image itself: side_paint)
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
        done[sel[k]] = True; fdone[sel[k]] = True
        print('face: %d texels of the forehead painted with the front image\'s bangs' % int(k.sum()))
    temple = None
    if hide is not None:
        import kael_flat   # (the eyes and the brows as its pass keeps them, EYE_KEEP around them)
        kk = np.nonzero(keep[ks])[0]; eyes_x = np.zeros(len(ks), bool)
        eyes_x[kk] = kael_flat.eyes_mask(pos[kk].astype(np.float64), nor[kk].astype(np.float32), out[ys[kk], xs[kk]].astype(np.float32), (is_skin(vc)[I].sum(1) >= 2)[ks[kk]], mid, eye_m, halo=EYE_KEEP)
        _, temple = side_paint(out, Q, I, keep, hide, locks, is_skin, ys, xs, ks, pos, nor, ear_v, collar_v, cams, mid, eye_m, chin_m, done=done, jm=JM, skin_tri=skin_t, is_hair=is_hair,
                               hair_tri=hair_v[I].sum(1) >= 2, free=free, is_purple=is_purple, keep_zone=eyes_x, front_done=fdone, skin2_tri=is_skin(vc)[I].sum(1) >= 2)
        skin_fill(out, I, ys, xs, ks, pos, hair_v, ear_v, collar_v, done, keep, mid, chin_m, top, is_skin, force, locks[HIDE_ORDER[0]], is_skin(vc))
    if lock_t is not None:   # (the skin's colour left on the standing locks, Meshy's own and the side images': as the nearest hair's, not its lines')
        from scipy.spatial import cKDTree
        lt = np.nonzero(lock_t[ks] & keep[ks] & ~ear_v[I[ks]].any(1) & ~collar_v[I[ks]].any(1))[0]; c_ = out[ys[lt], xs[lt]]
        bad = is_skin(c_) & ~done[lt]; src = lt[is_hair(c_) & ~is_skin(c_) & ~done[lt] & (c_.mean(1) > LOCK_FILL)]   # (not what the images painted there: the features' zone on the face's
        # own layer, the brow's ridge; filled, a block of the brow's lavender sat on top of his right brow)
        if bad.any() and len(src):
            _, j_ = cKDTree(pos[src]).query(pos[lt[bad]]); out[ys[lt[bad]], xs[lt[bad]]] = out[ys[src[j_]], xs[src[j_]]]
        print('face: %d skin-coloured texels on the locks standing over the head as the hair next to them' % int(bad.sum()))
    if not sheet: return keep, None, hide, force, temple
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
    return keep, (sp, suv, np.array(tris, np.int64), rgba), hide, force, temple
