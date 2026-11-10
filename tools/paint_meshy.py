#!/usr/bin/env python3
"""Ren's body in Meshy's own paint with the drawings' lines traced lightly over it (8/11/2026, Denis: "il modello di
meshy senza i tuoi disegni è molto più pulito nei vestiti ed il resto del corpo ... rifarlo disegnato come meshy ma con
leggeri calchi"); the head (tools/ren_head.py) is not touched.

usage: python3 tools/paint_meshy.py PACKAGE_DIR DRAWN.jpg OUT.jpg
  PACKAGE_DIR  the tools/meshy_pack.py package: its texture is the base
  DRAWN.jpg    the drawings painted on the model (tools/paint_from_drawing.py, then tools/paint_views.py): only their
               thin dark lines are taken
  OUT.jpg      the look's paint (viewer_assets/ren/ren_painted.jpg)

- the old tails' paint: Meshy painted the sash's tails on the trousers and the vest's flaps under them too (orange specks
  and streaks under the band, where the tails hung; the tails' own shapes are hidden, tools/ren_head.py): those texels
  (orange or its brown mixes, under the band, not on the arms nor on the tails' hidden shapes) take the colour of the
  nearest texel (on the model, in 3D) that is not, softened among themselves; within TAIL_NEAR of the tails' hidden
  shapes (the clothes they covered, painted in greys and tans by Meshy: grey shards along the vest's edge once the tails
  were gone, 9/11/2026, Denis: "ce ancora un pezzo di fascia rimuovilo") every colour but the vest's teal and the
  trousers' purple, in one of the two: the one most of the nearest texels are;
- the borders between the parts clean (clean_borders; 9/11/2026, Denis: "dove si sovrappongono i colori"): Meshy's brush
  left each part's colour in ragged teeth, specks and mixes over the next one (the sash's orange on the vest, the skin
  into the wristbands, the vest's green into the skin at the armholes), and along the texture's seams the zigzag of the
  triangles; each texel near a border takes the colour of the part the model has there, smoothed on the model itself;
  in the armholes (ARMHOLE) the skin wins over the vest's half-green fold above the deltoids;
- the collar's lining in one cream (LINING_*), the vest's armholes edged in ink (ARM_LINE; not its specks, ARM_SPECK,
  nor around the skin's specks left in the teal, ARM_PALE), as in the drawings;
- the tracing: the drawings' dark lines (darker than TRACE_LUM, thinner than about 2 TRACE_W + 1 texels: not the big
  black shapes of the folds; in pieces of TRACE_MIN texels or more and TRACE_LEN long: lines, not specks nor dashes) over
  Meshy's paint in TRACE_INK,
  TRACE_ALPHA opaque; not on the hands (drawn spread differently) nor on the head;
- the chest in the vest's front opening drawn as in the sheet: flat skin, the sheet's lines, the V's edges inked
  (tools/ren_chest.py);
- the texels between the pieces take their nearest piece's colour (as the other paints).
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paint_views import load, texel_table
from ren_look import sash_tails, SASH_BAND, TAILS_TOUCH, TAILS_STUB

TRACE_LUM, TRACE_W, TRACE_ALPHA, TRACE_INK, TRACE_MIN = 50., 2, .6, np.array([22., 20, 26]), 30
TRACE_LEN = .03   # a traced piece on the vest or the sash this long (m, on the model) or more: a line; shorter, a dash (9/11: scratches on the vest's shoulders)
# Denis's close-up of the shoulder (9/11/2026: "devi assolutamente aggiustare tutto quello che c'è nell'immagine"):
# LINING_*: the collar's light lining (the light part above LINING_Y m, off the arms, within LINING_X m of the middle) in
# one cream, the sheets' (Meshy's was white with grey streaks, like metal); ARM_LINE: the vest's armholes edged in the
# drawings' ink, this wide (m) on the vest's side of its border with the skin (the light's angular patches there:
# ren_look.smooth_normals; Meshy's shading smoothed in the texture too took the muscles' own strokes away: not done)
LINING_RGB, LINING_Y, LINING_X = np.array([206., 190, 162]), 1.36, .2
ARM_LINE = .0035
ARM_SPECK = 10   # its pieces in the texture of fewer texels: left out (9/11, Denis's side view in guard: black dots by the line)
ARM_PALE = (12, .6)   # see main(): the pale specks by the armholes (texels, share of teal around them)
TAIL_LOW, FILL_K = .12, 48   # the old tails' paint: from this height (m) up to the band; its fill: the median of that many texels
UNDER_TAILS = (.02, .032, 8, .0025, .8)   # see under_tails()
VEST_HEM = (.5, 5., .03, .03)   # see under_tails()
OFF_TAILS = (.045, 40., 4.)   # see under_tails()
HEM = (.82, .93, 140., 70., .015)   # see under_tails()
MAROON = (.045, 18., 130., .012)   # see under_tails()
TAIL_NEAR = .02   # the clothes under the old tails: this near (m) their hidden shapes, every colour but the vest's and the trousers'
# the borders between the clothes, the skin and the sash clean (9/11/2026, Denis: "dove si sovrappongono i colori"): see
# clean_borders. BORDER_SIGMA (m), BORDER_STEP (texels), BORDER_NN: the parts' shares around each texel, a gaussian of
# that width over a sample every that many texels, its that many nearest; BORDER_NEAR: another part with that share or
# more is a border near; BORDER_K: the colour of a texel redone is the median of that many of its part's nearest texels
# away from the borders; BORDER_MIX: a texel whose hue (its colour over its brightness) has moved [0] or more of the way
# from its part's toward the other part's there, within [1] of the line between the two, is a mix of the two (redone;
# 9/11, Denis: "quella macchia verde del vestito che sfiora il braccio colorandolo": the vest's grey-green at the
# shoulders' tops, half skin), if brighter than [2] (darker, the hue is noise); BORDER_SPECK: a speck of one part inside
# another, up to that many texels (redone)
BORDER_SIGMA, BORDER_STEP, BORDER_NN, BORDER_NEAR, BORDER_K, BORDER_MIX, BORDER_SPECK = .004, 2, 32, .12, 24, (.2, .03, 40.), 60
# the armholes (9/11/2026, Denis: "quella macchia verde del vestito che sfiora il braccio colorandolo", circled on the top
# of the shoulder seen from the side): the fold under the vest's edge, between it and the deltoid, Meshy painted half green
# half skin; the arm wins there, as in the sheets (the vest's green ends at its edge's dark line): texels of the arms'
# weight ARMHOLE[0] to [1], above ARMHOLE[2] m, in a mix of the vest's and the skin's hue (BORDER_MIX's test, from the
# skin's side: at least ARMHOLE[3] of the way to the vest's) take the skin's colour
ARMHOLE = (.1, .75, 1.25, .1, 12)   # ([4]: then the specks left there, up to that many texels, inside the skin: skin too)
TEAL_, SKIN_, LIGHT_, DARK_, ORANGE_, MIXED_ = range(6)
DEBUG = {}   # (clean_borders' inner values, for tests)


def orangeish(c):
    """Orange and its browns, light or dark (n x 3): warm (red over blue and green) and strongly so for their
    brightness (not the trousers' purple grey, nor the boots' beige trim, nor the wraps' warm white)."""
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    return (r > 20) & (r - b > 16) & (r - g > 10) & ((r - b) > .25 * r)


def teal(c):
    """The vest's teal, light or dark (n x 3): green and blue over red, and clearly so for its brightness (not the
    light blue greys Meshy left under the tails)."""
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    return (g - r > np.maximum(8, .2 * g)) & (b - r > 0)


def purple(c):
    """The trousers' dark purple grey (n x 3): dark, red and blue not under green."""
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    return (c.mean(1) < 95) & (r >= g - 2) & (b >= g - 4) & ~orangeish(c)


def parts(c):
    """The part each colour belongs to (n x 3): the vest's teal (its shadows too), the skin (its shadows too), light (the
    wraps and their grey folds, the trims), dark (the trousers' purple grey, the undershirt, the boots, the wristbands,
    lines), the sash's orange, or a mix of none."""
    r, g, b = c[:, 0], c[:, 1], c[:, 2]; lum = c.mean(1); mx, mn = c.max(1), c.min(1)
    k = np.full(len(c), MIXED_)
    k[(r > 100) & (b > .36 * r) & (b < .8 * r) & (g > .5 * r) & (g < .9 * r) & (r - b > 30)] = SKIN_
    k[(mn > 120) & (mx - mn < 50)] = LIGHT_
    k[(lum < 75) & (np.abs(r - b) < 45) & (g <= np.maximum(r, b) + 6)] = DARK_
    k[(r > 120) & (b < .32 * r) & (g > .3 * r) & (g < .75 * r)] = ORANGE_
    k[(g - r > np.maximum(6, .15 * g)) & (b - r > .1 * (r + g + b)) & (lum > 12)] = TEAL_   # (the vest's grey-greens half skin are mixes)
    return k


def clean_borders(img, ys, xs, pos, nor, armhole=None):
    """The borders between the parts (parts()) clean, as drawn: Meshy painted them with a brush, ragged, each part's
    colour in teeth and specks over the other's and mixes of the two between, and along the texture's seams its pieces
    meet in the triangles' zigzag. On the model (in 3D, across the seams): each part's share around every texel (its
    texels, without the thin lines and specks: opened in the texture; a sample every BORDER_STEP texels, weighted by a
    gaussian of BORDER_SIGMA m and by facing the same way) gives the texel its part, the one with the most; where another
    part has BORDER_NEAR of it or more (a border near), a texel painted in that part's colour or in a mix of the two
    (BORDER_MIX: by hue, so a part's own shading stays) takes its own part's colour; so does a speck (up to BORDER_SPECK
    texels) of a part inside another's; dark lines are kept. The new colours: the median of the BORDER_K nearest texels of the part (in 3D) away from the
    borders, softened among themselves. img (h x w x 3 float) is changed in place; returns the texels redone (a mask over
    ys, xs)."""
    TS = img.shape[0]; c = img[ys, xs]; k = parts(c)
    cls = np.full((TS, TS), -1); cls[ys, xs] = k
    big = np.full((TS, TS), -1)
    for p_ in range(5):
        r_ = 2 if p_ == DARK_ else 1
        disk = np.hypot(*np.mgrid[-r_:r_ + 1, -r_:r_ + 1]) <= r_ + .01
        big[ndimage.binary_opening(cls == p_, structure=disk)] = p_
    kb = big[ys, xs]
    smp = np.nonzero((kb >= 0) & (ys % BORDER_STEP == 0) & (xs % BORDER_STEP == 0))[0]
    tree = cKDTree(pos[smp]); F = np.zeros((len(k), 5))
    for i0 in range(0, len(k), 200000):
        q = slice(i0, min(i0 + 200000, len(k)))
        d, j = tree.query(pos[q], k=BORDER_NN, distance_upper_bound=3 * BORDER_SIGMA)
        ok = np.isfinite(d); j = np.where(ok, j, 0)
        w = np.exp(-.5 * (np.where(ok, d, 0) / BORDER_SIGMA) ** 2) * ok * np.clip((nor[smp][j] * nor[q][:, None, :]).sum(2), 0, 1)
        for p_ in range(5): F[q, p_] = (w * (kb[smp][j] == p_)).sum(1)
    tot = F.sum(1); F /= np.maximum(tot, 1e-9)[:, None]
    has = tot > 1e-6
    order = np.argsort(-F, 1); s_ = np.where(has, order[:, 0], -1); o_ = order[:, 1]
    f2 = np.take_along_axis(F, o_[:, None], 1)[:, 0]
    near = has & (f2 >= BORDER_NEAR)
    speck = np.zeros(len(k), bool)
    for p_ in (TEAL_, SKIN_, LIGHT_, ORANGE_):
        lb, nb = ndimage.label(cls == p_, structure=np.ones((3, 3)))
        if not nb: continue
        sz = np.bincount(lb.ravel())[lb[ys, xs]]
        speck |= (k == p_) & (sz <= BORDER_SPECK) & has & (s_ != p_)
    pure = has & (k == s_) & (F.max(1) > .97)
    src = {p_: np.nonzero(pure & (k == p_))[0] for p_ in range(5)}
    trees = {p_: cKDTree(pos[v]) for p_, v in src.items() if len(v) >= BORDER_K}
    def median_of(p_, q):
        _, j = trees[p_].query(pos[q], k=BORDER_K); return np.median(c[src[p_][j]], axis=1)
    redo = np.zeros(len(k), bool); new = c.copy()
    a = (near & (k == o_) & (k != s_)) | speck   # (another part's colour near its border; a speck)
    # a mix of the two parts near their border (in hue): not the dark lines (but the dark part's own fringe)
    mix = near & ~a & ((k != DARK_) | (s_ == DARK_) | (o_ == DARK_)) & (c.mean(1) > BORDER_MIX[2])
    hue = lambda x: x / np.maximum(x.sum(1, keepdims=True), 1e-9)
    for p_ in range(5):
        if p_ not in trees: continue
        q = np.nonzero((a | mix) & (s_ == p_))[0]
        if not len(q): continue
        own = median_of(p_, q); keep_q = np.ones(len(q), bool); mq = mix[q]
        for o2 in range(5):
            sel = mq & (o_[q] == o2)
            if not sel.any(): continue
            if o2 not in trees: keep_q[sel] = False; continue
            ho, hx, ht = hue(own[sel]), hue(c[q[sel]]), hue(median_of(o2, q[sel])); e = ht - ho
            t = ((hx - ho) * e).sum(1) / np.maximum((e * e).sum(1), 1e-12)
            dl = np.linalg.norm(hx - (ho + np.clip(t, 0, 1)[:, None] * e), axis=1)
            keep_q[np.nonzero(sel)[0][(t < BORDER_MIX[0]) | (dl > BORDER_MIX[1])]] = False
        q = q[keep_q]; new[q] = own[keep_q]; redo[q] = True
    # the armholes: the mixes of the vest and the skin take the skin's colour (armhole: a mask over the texels, ARMHOLE)
    n_arm = 0
    if armhole is not None and SKIN_ in trees and TEAL_ in trees:
        q = np.nonzero(armhole & (k != DARK_) & (k != SKIN_) & (k != TEAL_) & (c.mean(1) > BORDER_MIX[2]))[0]
        if len(q):
            sk, ve = median_of(SKIN_, q), median_of(TEAL_, q); hs, hv, hx = hue(sk), hue(ve), hue(c[q]); e = hv - hs
            t = ((hx - hs) * e).sum(1) / np.maximum((e * e).sum(1), 1e-12); dl = np.linalg.norm(hx - (hs + np.clip(t, 0, 1)[:, None] * e), axis=1)
            ok = (t >= ARMHOLE[3]) & (t <= 1.1) & (dl <= 2 * BORDER_MIX[1]); q = q[ok]; new[q] = sk[ok]; redo[q] = True; n_arm = len(q)
        # the specks left there (the vest's teal and dark dots in a row along the fold), inside the skin: skin
        kk = parts(new); m = np.zeros((TS, TS), bool); m[ys, xs] = armhole & (kk != SKIN_)
        sk_img = np.zeros((TS, TS), bool); sk_img[ys, xs] = kk == SKIN_
        lb, nb = ndimage.label(m, structure=np.ones((3, 3)))
        if nb:
            sz = np.bincount(lb.ravel()); ring = ndimage.binary_dilation(m, iterations=2) & ~m
            rl = ndimage.maximum_filter(np.where(m, lb, 0), size=5)   # (each ring texel: the speck next to it)
            rs = np.bincount(rl[ring], weights=sk_img[ring].astype(float), minlength=nb + 1) / np.maximum(np.bincount(rl[ring], minlength=nb + 1), 1)
            small = (sz <= ARMHOLE[4]) & (rs >= .7); small[0] = False
            q = np.nonzero(small[lb[ys, xs]])[0]
            if len(q): new[q] = median_of(SKIN_, q); redo[q] = True; n_arm += len(q)
    acc = np.zeros((TS, TS, 3)); cnt = np.zeros((TS, TS)); acc[ys[redo], xs[redo]] = new[redo]; cnt[ys[redo], xs[redo]] = 1
    sm = np.stack([ndimage.gaussian_filter(acc[..., i], 1.) for i in range(3)], -1) / np.maximum(ndimage.gaussian_filter(cnt, 1.), 1e-6)[..., None]
    img[ys[redo], xs[redo]] = sm[ys[redo], xs[redo]]
    DEBUG.update(k=k, s=s_, o=o_, f2=f2, near=near, a=a, mix=mix, redo=redo, F=F, has=has)
    names = ['vest', 'skin', 'light', 'dark', 'orange']
    print('borders: %d texels redone (%d of another part near its border, %d mixes, %d specks, %d in the armholes); by part: %s' % (
        int(redo.sum()), int((redo & a & ~speck).sum()), int((redo & mix).sum()), int((redo & speck).sum()), n_arm,
        ', '.join('%s %d' % (names[p_], int((redo & (s_ == p_)).sum())) for p_ in range(5))))
    return redo


def harmonic_fill(img, ys, xs, pos, nor, U, K):
    """The texels U (indices into the texel table) filled smooth from the texels K: harmonic, each the mean of its
    UNDER_TAILS[2] nearest within UNDER_TAILS[3] m on the same surface (normals within UNDER_TAILS[4]); with a light pull
    to K's median (pieces not reaching K take it)."""
    from scipy.sparse import coo_matrix, diags
    from scipy.sparse.linalg import spsolve
    if not len(U) or not len(K): return 0
    c = img[ys, xs]; A_ = np.r_[U, K]; dd, jj = cKDTree(pos[A_]).query(pos[U], k=UNDER_TAILS[2] + 1, distance_upper_bound=UNDER_TAILS[3])
    ok = np.isfinite(dd) & (jj < len(A_)); jj = np.where(ok, jj, 0)
    ok &= (jj != np.arange(len(U))[:, None]) & ((nor[U][:, None, :] * nor[A_][jj]).sum(2) > UNDER_TAILS[4])
    rows = np.repeat(np.arange(len(U)), jj.shape[1])[ok.ravel()]; cols = jj.ravel()[ok.ravel()]
    Wm = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(U), len(A_))).tocsr(); WU, WK = Wm[:, :len(U)], Wm[:, len(U):]
    Lm = (diags(ok.sum(1) + 1e-3) - WU).tocsc(); xK = c[K]; base = np.median(xK, 0)
    for ch in range(3): img[ys[U], xs[U], ch] = np.clip(spsolve(Lm, WK @ xK[:, ch] + 1e-3 * base[ch]), 0, 255)
    return len(U)


def under_tails(img, ys, xs, pos, nor, tp, region):
    """(9/11/2026, Denis: "rimuovi le parti rimanenti della fascia vecchia", with a photo of the vest under the knot) where
    the old tails lay on the clothes, Meshy's paint under them filled in patches (the median of the nearest texels) and the
    drawings' lines traced over them (the tails' own outlines, on the vest): blotches and ghost lines along the tails' path.
    The texels of region within UNDER_TAILS[0] m of the tails' shapes (tp: points on them) are filled smooth from the
    clean ones around them (from there to [1] m; not ink; harmonic_fill: the vest's flaps from the vest, the trousers from
    the trousers). And the vest's hem: Meshy's light trim on its bottom edge (HEM: its light texels, brighter than [2] and
    less saturated than [3], between [0] and [1] m), not in the sheets, filled from the vest around it ([4] m)."""
    d = np.full(len(pos), np.inf); d[region] = cKDTree(tp).query(pos[region], distance_upper_bound=UNDER_TAILS[1])[0]
    c = img[ys, xs]
    U = np.nonzero(region & (d < UNDER_TAILS[0]))[0]; K = np.nonzero(region & (d >= UNDER_TAILS[0]) & (d < UNDER_TAILS[1]) & (c.mean(1) > 40))[0]
    K = K[~orangeish(c[K])]   # (not the band's orange: under the knot it made the fill a muddy yellow green streak, 9/11 Denis)
    # (under the vest's hem, VEST_HEM, from the trousers' texels only: on the right thigh, 20 cm under the hem, the fill took
    # the vest's teal from texels around, a teal patch seen from behind, 9/11 Denis. The hem: per VEST_HEM[1] degrees around
    # the body, the vest's teal's lowest heights (its [3] quantile, above [0] m: not the boots); under it by [2] m: trousers)
    vt = region & teal(c) & (pos[:, 1] > VEST_HEM[0]); vt[U] = False
    ang = np.floor((np.degrees(np.arctan2(pos[:, 0], pos[:, 2])) + 180) / VEST_HEM[1]).astype(int); nbins = int(np.ceil(360 / VEST_HEM[1])) + 1
    hem = np.full(nbins, np.inf)
    for bi in np.unique(ang[vt]): hem[bi] = np.quantile(pos[vt & (ang == bi), 1], VEST_HEM[3])
    hem = np.minimum(hem, np.minimum(np.roll(hem, 1), np.roll(hem, -1)))
    low_ = pos[U, 1] < hem[ang[U]] - VEST_HEM[2]
    n = harmonic_fill(img, ys, xs, pos, nor, U[~low_], K) + harmonic_fill(img, ys, xs, pos, nor, U[low_], K[~teal(c[K])])
    print('under the old tails: %d texels under the vest\'s hem filled from the trousers alone' % int(low_.sum()))
    # (and farther, to OFF_TAILS[0] m: Meshy's paint by the tails' path not the vest's teal nor the trousers' purple, brighter
    # than [1] (not ink), or teal with green over blue by [2] (olive): a pale yellow green streak along the vest's slit by the
    # knot, seen from behind, 9/11 Denis), filled from the teal and the purple around them
    c = img[ys, xs]; d3 = np.full(len(pos), np.inf); d3[region] = cKDTree(tp).query(pos[region], distance_upper_bound=OFF_TAILS[0] + .015)[0]
    off = region & (d3 < OFF_TAILS[0]) & ((~teal(c) & ~purple(c) & (c.mean(1) > OFF_TAILS[1])) | (teal(c) & (c[:, 1] - c[:, 2] > OFF_TAILS[2]))); off[U] = False   # (and the teal gone olive)
    Ko = np.nonzero(region & (d3 < OFF_TAILS[0] + .015) & ~off & (teal(c) | purple(c)))[0]
    print('near the old tails: %d texels neither the vest\'s nor the trousers\' colour filled from them' % harmonic_fill(img, ys, xs, pos, nor, np.nonzero(off)[0], Ko))
    print('under the old tails: %d texels filled smooth from the clothes around them (within %.0f mm of their shapes)' % (n, 1000 * UNDER_TAILS[0]))
    c = img[ys, xs]; inr = (pos[:, 1] > HEM[0]) & (pos[:, 1] < HEM[1]) & region
    lt = inr & (c.mean(1) > HEM[2]) & (c.max(1) - c.min(1) < HEM[3])
    if lt.any():
        dl = cKDTree(pos[lt]).query(pos[inr & ~lt], distance_upper_bound=HEM[4])[0]
        Kh = np.nonzero(inr & ~lt)[0][np.isfinite(dl) & (c[inr & ~lt].mean(1) > 40)]
        print('the vest\'s hem: %d texels of its light trim filled from the vest around them' % harmonic_fill(img, ys, xs, pos, nor, np.nonzero(lt)[0], Kh))
    # (and the dark red flecks left near the tails' path, on surfaces farther than UNDER_TAILS[0]: within MAROON[0] m of
    # the tails, red over green by [1] and over blue, darker than [2]; filled from their surroundings, [3] m)
    c = img[ys, xs]; d2 = np.full(len(pos), np.inf); d2[region] = cKDTree(tp).query(pos[region], distance_upper_bound=MAROON[0])[0]; near2 = region & (d2 < MAROON[0])
    mr = near2 & (c[:, 0] - c[:, 1] > MAROON[1]) & (c[:, 0] > c[:, 2]) & (c.mean(1) < MAROON[2])
    if mr.any():
        dm = cKDTree(pos[mr]).query(pos[near2 & ~mr], distance_upper_bound=MAROON[3])[0]
        Km = np.nonzero(near2 & ~mr)[0][np.isfinite(dm) & (c[near2 & ~mr].mean(1) > 40)]
        print('near the old tails: %d dark red texels filled from around them' % harmonic_fill(img, ys, xs, pos, nor, np.nonzero(mr)[0], Km))


def main(pkg, drawn, out):
    name, P, N, UV, I, HEADW, HANDW, FOREW, ARMW = load(pkg)
    T = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(np.float64); TS = T.shape[0]
    Dw = np.asarray(Image.open(drawn).convert('RGB')).astype(np.float64)
    if Dw.shape != T.shape: sys.exit('the drawn paint and the package\'s texture differ in size')
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, TS)
    at = lambda W_: (W_[I[ks]] * bary).sum(1)
    hw, hdw, aw = at(HEADW), at(HANDW), at(ARMW)
    # the old tails' shapes (hidden by ren_head.py): they give no colour, and take the clothes' too (their orange, though
    # hidden, bled along the seams into the trousers next to them in the texture: the filtering, the mipmaps)
    vcol = T[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)]
    tv = np.zeros(len(P), bool)
    for tl in sash_tails(P, vcol, I): tv[tl] = True
    tail_t = tv[I].sum(1) >= TAILS_TOUCH
    from ren_look import tail_stubs
    tail_t[tail_stubs(P, vcol, I, tv)] = True   # (their tops under the band: hidden too, tools/ren_head.py)
    on_tail = tail_t[ks]
    out_img = T.copy(); c0 = T[ys, xs]
    low = (pos[:, 1] < SASH_BAND) & (pos[:, 1] > TAIL_LOW) & (aw < .5) & (hw < .5)
    # the clothes under the tails (hidden by them in Meshy's model, painted in greys and tans there: grey shards along the
    # vest's edge once the tails were gone): near the tails' hidden shapes, every colour but the vest's and the trousers'
    tri_t = np.nonzero(tail_t)[0]; wq = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [4, 1, 1], [1, 4, 1], [1, 1, 4]], float)
    tp = np.einsum('kj,tjc->tkc', wq / wq.sum(1, keepdims=True), P[I[tri_t]]).reshape(-1, 3)
    near = np.zeros(len(pos), bool); near[low] = cKDTree(tp).query(pos[low])[0] < TAIL_NEAR
    is_teal, is_purple = teal(c0), purple(c0)
    bad = low & (orangeish(c0) | on_tail | (near & ~is_teal & ~is_purple))
    src = low & ~bad
    tree = cKDTree(pos[src]); _, j = tree.query(pos[bad], k=FILL_K)
    fill = np.median(c0[src][j], axis=1)   # (the median of the nearest clothes' texels: not one of Meshy's light streaks)
    # under the tails, one material's colour: the vest's or the trousers', whichever most of the nearest texels are (the
    # median of both together was a muddy grey)
    nb = near[bad]; cs = c0[src][j[nb]]; tq, pq = is_teal[src][j[nb]], is_purple[src][j[nb]]
    mem = np.where((tq.sum(1) >= pq.sum(1))[:, None], tq, pq); mem[~mem.any(1)] = True
    fill[nb] = np.nanmedian(np.where(mem[..., None], cs, np.nan), axis=1)
    print('under the old tails: %d texels not the vest\'s nor the trousers\' colour, in theirs' % int((near & bad & ~orangeish(c0) & ~on_tail).sum()))
    # (softened among themselves: the nearest colours make patches)
    acc = np.zeros((TS, TS, 3)); cnt = np.zeros((TS, TS)); acc[ys[bad], xs[bad]] = fill; cnt[ys[bad], xs[bad]] = 1
    sm = np.stack([ndimage.gaussian_filter(acc[..., k], 1.5) for k in range(3)], -1) / np.maximum(ndimage.gaussian_filter(cnt, 1.5), 1e-6)[..., None]
    out_img[ys[bad], xs[bad]] = sm[ys[bad], xs[bad]]
    print('old tails\' paint: %d texels under the band (orange or brown) in the colour of the clothes around them' % int(bad.sum()))
    # the borders between the parts clean (before the tracing: its lines stay as drawn)
    redo = clean_borders(out_img, ys, xs, pos, nor, (aw >= ARMHOLE[0]) & (aw <= ARMHOLE[1]) & (pos[:, 1] > ARMHOLE[2]) & (hw < .5))
    if os.environ.get('BORDER_DEBUG'): np.savez(os.environ['BORDER_DEBUG'], ys=ys[redo], xs=xs[redo])
    # the collar's lining in one cream; the armholes edged in ink
    k2 = parts(out_img[ys, xs])
    lin = (k2 == LIGHT_) & (pos[:, 1] > LINING_Y) & (aw < .3) & (np.abs(pos[:, 0]) < LINING_X) & (hw < .5)
    out_img[ys[lin], xs[lin]] = LINING_RGB
    arm = (aw >= .05) & (aw <= .85) & (pos[:, 1] > 1.2) & (hw < .5)
    # (the pale specks there, ARM_PALE: up to [0] texels of skin or light alone, the ring around them mostly the vest's
    # teal: in that teal before the ink, which ringed them as black eyelets on the armholes' line)
    cls_ = np.full((TS, TS), -1); cls_[ys, xs] = k2
    pale_ = np.zeros((TS, TS), bool); pale_[ys, xs] = arm & ((k2 == SKIN_) | (k2 == LIGHT_))
    lab_, n_ = ndimage.label(pale_, structure=np.ones((3, 3))); sz_ = np.bincount(lab_.ravel(), minlength=n_ + 1)
    small_ = np.where(pale_ & (sz_[lab_] <= ARM_PALE[0]), lab_, 0); grown_ = ndimage.grey_dilation(small_, size=(5, 5))
    ring_ = (grown_ > 0) & (small_ == 0) & (cls_ >= 0); tl_ = ring_ & ((cls_ == TEAL_) | (cls_ == MIXED_))
    share_ = np.bincount(grown_[ring_], minlength=n_ + 1); tn_ = np.bincount(grown_[tl_], minlength=n_ + 1)
    tc_ = np.stack([np.bincount(grown_[tl_], out_img[..., c][tl_], minlength=n_ + 1) for c in range(3)], 1) / np.maximum(tn_, 1)[:, None]
    ok_ = (tn_ >= ARM_PALE[1] * np.maximum(share_, 1)) & (tn_ > 0); ok_[0] = False
    sp_ = np.nonzero(ok_[small_[ys, xs]] & (small_[ys, xs] > 0))[0]
    out_img[ys[sp_], xs[sp_]] = tc_[small_[ys[sp_], xs[sp_]]]; k2[sp_] = TEAL_
    print('armholes: %d texels of skin or light specks in the vest\'s teal' % len(sp_))
    sk = arm & (k2 == SKIN_); te = np.nonzero(arm & ((k2 == TEAL_) | (k2 == MIXED_)))[0]
    ink = te[cKDTree(pos[sk]).query(pos[te])[0] < ARM_LINE] if sk.any() and len(te) else np.zeros(0, int)
    im_ = np.zeros((TS, TS), bool); im_[ys[ink], xs[ink]] = True   # (the few texels alone, on UV islands' borders, as dots)
    lab_, n_ = ndimage.label(im_, structure=np.ones((3, 3))); big_ = np.bincount(lab_.ravel(), minlength=n_ + 1) >= ARM_SPECK; big_[0] = False
    specks = ink[~big_[lab_[ys[ink], xs[ink]]]]; ink = ink[big_[lab_[ys[ink], xs[ink]]]]
    out_img[ys[ink], xs[ink]] = TRACE_INK
    print('collar: %d texels of its lining in cream; armholes: %d texels of ink along the vest\'s edge (%d in specks left out)' % (int(lin.sum()), len(ink), len(specks)))
    # the tracing: the drawings' thin dark lines
    inside = np.zeros((TS, TS), bool); inside[ys, xs] = True
    dark = (Dw.mean(2) < TRACE_LUM) & inside
    disk = np.hypot(*np.mgrid[-TRACE_W:TRACE_W + 1, -TRACE_W:TRACE_W + 1]) <= TRACE_W + .01
    thin = dark & ~ndimage.binary_opening(dark, structure=disk)
    lab, n = ndimage.label(thin, structure=np.ones((3, 3)))   # (lines, not specks: the pieces of TRACE_MIN texels or more, TRACE_LEN long)
    pid = lab[ys, xs]; on = pid > 0; cnt = np.bincount(pid[on], minlength=n + 1).astype(float)
    S1 = np.stack([np.bincount(pid[on], pos[on, i], minlength=n + 1) for i in range(3)], 1) / np.maximum(cnt, 1)[:, None]
    S2 = np.stack([np.bincount(pid[on], pos[on, i] * pos[on, j], minlength=n + 1) for i in range(3) for j in range(3)], 1).reshape(-1, 3, 3) / np.maximum(cnt, 1)[:, None, None]
    length = np.sqrt(12 * np.clip(np.linalg.eigvalsh(S2 - S1[:, :, None] * S1[:, None, :])[:, -1], 0, None))
    kt = parts(out_img[ys, xs]); cloth = np.bincount(pid[on], ((kt == TEAL_) | (kt == ORANGE_))[on].astype(float), minlength=n + 1) / np.maximum(cnt, 1)
    big = np.bincount(lab.ravel(), minlength=n + 1) >= TRACE_MIN
    # (and at the armholes, on the border between the vest and the arm, 9/11/2026: Denis on a side view in guard: the
    # drawings' thick armhole line, its thin ends traced, left black dashes with brown fringes along the armholes' top)
    at_arm = np.bincount(pid[on], arm[on].astype(float), minlength=n + 1) / np.maximum(cnt, 1)
    dash = big & ((cloth > .5) | (at_arm > .5)) & (length < TRACE_LEN)   # (on the vest and the sash only: the skin's muscle lines come in short pieces)
    good = big & ~dash; good[0] = False
    print('tracing: %d pieces of lines, %d dashes on the vest and the sash shorter than %.0f mm left out' % (int(good.sum()), int(dash[1:].sum()), 1000 * TRACE_LEN))
    thin = good[lab]
    ok = np.zeros((TS, TS), bool); ok[ys, xs] = (hdw < .5) & (hw < .5) & ~on_tail
    a = np.clip(ndimage.gaussian_filter((thin & ok).astype(float), .6) * 1.6, 0, 1) * ok * TRACE_ALPHA
    out_img = out_img * (1 - a[..., None]) + TRACE_INK * a[..., None]
    print('tracing: %d texels of the drawings\' thin lines over Meshy\'s paint (%.0f%% opaque)' % (int((thin & ok).sum()), 100 * TRACE_ALPHA))
    # the chest in the vest's opening drawn as in the sheet (tools/ren_chest.py)
    from ren_chest import chest, CHEST_SHEET
    sheet = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', CHEST_SHEET.get(name, ''))
    if name in CHEST_SHEET and os.path.exists(sheet): chest(out_img, ys, xs, pos, nor, sheet, TRACE_INK)
    # where the old tails lay (and their tops), the clothes under them filled smooth from the clean clothes around
    under_tails(out_img, ys, xs, pos, nor, tp, (pos[:, 1] < TAILS_STUB[1]) & (pos[:, 1] > TAIL_LOW) & (aw < .5) & (hw < .5) & (hdw < .5) & ~on_tail)
    # every texel outside the pieces (their centres, as the texel table has them) takes its nearest piece texel's colour:
    # around a thin piece the texels just outside it kept Meshy's old colours (the tails' orange next to a texel of the
    # trousers), and the filtering drew them in
    gy, gx = ndimage.distance_transform_edt(~inside, return_distances=False, return_indices=True); out_img = out_img[gy, gx]
    Image.fromarray(np.clip(out_img, 0, 255).round().astype(np.uint8)).save(out, quality=85, subsampling=0, optimize=True)   # (4:4:4: halved colour resolution bled the band's orange into the trousers at the pieces' borders)


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
