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
- the tracing: the drawings' dark lines (darker than TRACE_LUM, thinner than about 2 TRACE_W + 1 texels: not the big
  black shapes of the folds; in pieces of TRACE_MIN texels or more: lines, not specks) over Meshy's paint in TRACE_INK,
  TRACE_ALPHA opaque; not on the hands (drawn spread differently) nor on the head;
- the texels between the pieces take their nearest piece's colour (as the other paints).
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paint_views import load, texel_table
from ren_look import sash_tails, SASH_BAND, TAILS_TOUCH

TRACE_LUM, TRACE_W, TRACE_ALPHA, TRACE_INK, TRACE_MIN = 50., 2, .6, np.array([22., 20, 26]), 30
TAIL_LOW, FILL_K = .12, 48   # the old tails' paint: from this height (m) up to the band; its fill: the median of that many texels
TAIL_NEAR = .02   # the clothes under the old tails: this near (m) their hidden shapes, every colour but the vest's and the trousers'
# the borders between the clothes, the skin and the sash clean (9/11/2026, Denis: "dove si sovrappongono i colori"): see
# clean_borders. BORDER_SIGMA (m), BORDER_STEP (texels), BORDER_NN: the parts' shares around each texel, a gaussian of
# that width over a sample every that many texels, its that many nearest; BORDER_NEAR: another part with that share or
# more is a border near; BORDER_K: the colour of a texel redone is the median of that many of its part's nearest texels
# away from the borders; BORDER_MIX: a texel of no part this near (rgb) the line between the colours of the two parts it
# lies between is their mix (redone); BORDER_SPECK: a speck of one part inside another, up to that many texels (redone)
BORDER_SIGMA, BORDER_STEP, BORDER_NN, BORDER_NEAR, BORDER_K, BORDER_MIX, BORDER_SPECK = .004, 2, 32, .12, 24, 45., 60
TEAL_, SKIN_, LIGHT_, DARK_, ORANGE_, MIXED_ = range(6)


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
    k[(g - r > np.maximum(6, .15 * g)) & (b - r > 0) & (lum > 12)] = TEAL_
    return k


def clean_borders(img, ys, xs, pos, nor):
    """The borders between the parts (parts()) clean, as drawn: Meshy painted them with a brush, ragged, each part's
    colour in teeth and specks over the other's and mixes of the two between, and along the texture's seams its pieces
    meet in the triangles' zigzag. On the model (in 3D, across the seams): each part's share around every texel (its
    texels, without the thin lines and specks: opened in the texture; a sample every BORDER_STEP texels, weighted by a
    gaussian of BORDER_SIGMA m and by facing the same way) gives the texel its part, the one with the most; where another
    part has BORDER_NEAR of it or more (a border near), a texel painted in that part's colour or in a mix of the two
    (BORDER_MIX) takes its own part's colour; so does a speck (up to BORDER_SPECK texels) of a part inside another's;
    dark lines are kept. The new colours: the median of the BORDER_K nearest texels of the part (in 3D) away from the
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
    mix = near & (k == MIXED_)
    for p_ in range(5):
        if p_ not in trees: continue
        q = np.nonzero((a | mix) & (s_ == p_))[0]
        if not len(q): continue
        own = median_of(p_, q); keep_q = np.ones(len(q), bool); mq = mix[q]
        for o2 in range(5):
            sel = mq & (o_[q] == o2)
            if not sel.any(): continue
            if o2 not in trees: keep_q[sel] = False; continue
            oth = median_of(o2, q[sel]); x = c[q[sel]]; e = oth - own[sel]
            t = np.clip(((x - own[sel]) * e).sum(1) / np.maximum((e * e).sum(1), 1e-9), 0, 1)
            dseg = np.linalg.norm(x - (own[sel] + t[:, None] * e), axis=1); keep_q[np.nonzero(sel)[0][dseg > BORDER_MIX]] = False
        q = q[keep_q]; new[q] = own[keep_q]; redo[q] = True
    acc = np.zeros((TS, TS, 3)); cnt = np.zeros((TS, TS)); acc[ys[redo], xs[redo]] = new[redo]; cnt[ys[redo], xs[redo]] = 1
    sm = np.stack([ndimage.gaussian_filter(acc[..., i], 1.) for i in range(3)], -1) / np.maximum(ndimage.gaussian_filter(cnt, 1.), 1e-6)[..., None]
    img[ys[redo], xs[redo]] = sm[ys[redo], xs[redo]]
    names = ['vest', 'skin', 'light', 'dark', 'orange']
    print('borders: %d texels redone (%d of another part near its border, %d mixes, %d specks); by part: %s' % (
        int(redo.sum()), int((redo & a & ~speck).sum()), int((redo & mix).sum()), int((redo & speck).sum()),
        ', '.join('%s %d' % (names[p_], int((redo & (s_ == p_)).sum())) for p_ in range(5))))
    return redo


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
    tail_t = tv[I].sum(1) >= TAILS_TOUCH; on_tail = tail_t[ks]
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
    redo = clean_borders(out_img, ys, xs, pos, nor)
    if os.environ.get('BORDER_DEBUG'): np.savez(os.environ['BORDER_DEBUG'], ys=ys[redo], xs=xs[redo])
    # the tracing: the drawings' thin dark lines
    inside = np.zeros((TS, TS), bool); inside[ys, xs] = True
    dark = (Dw.mean(2) < TRACE_LUM) & inside
    disk = np.hypot(*np.mgrid[-TRACE_W:TRACE_W + 1, -TRACE_W:TRACE_W + 1]) <= TRACE_W + .01
    thin = dark & ~ndimage.binary_opening(dark, structure=disk)
    lab, n = ndimage.label(thin, structure=np.ones((3, 3)))   # (lines, not specks: the pieces of TRACE_MIN texels or more)
    thin = np.isin(lab, np.nonzero(ndimage.sum(thin, lab, range(1, n + 1)) >= TRACE_MIN)[0] + 1)
    ok = np.zeros((TS, TS), bool); ok[ys, xs] = (hdw < .5) & (hw < .5) & ~on_tail
    a = np.clip(ndimage.gaussian_filter((thin & ok).astype(float), .6) * 1.6, 0, 1) * ok * TRACE_ALPHA
    out_img = out_img * (1 - a[..., None]) + TRACE_INK * a[..., None]
    print('tracing: %d texels of the drawings\' thin lines over Meshy\'s paint (%.0f%% opaque)' % (int((thin & ok).sum()), 100 * TRACE_ALPHA))
    # every texel outside the pieces (their centres, as the texel table has them) takes its nearest piece texel's colour:
    # around a thin piece the texels just outside it kept Meshy's old colours (the tails' orange next to a texel of the
    # trousers), and the filtering drew them in
    gy, gx = ndimage.distance_transform_edt(~inside, return_distances=False, return_indices=True); out_img = out_img[gy, gx]
    Image.fromarray(np.clip(out_img, 0, 255).round().astype(np.uint8)).save(out, quality=85, subsampling=0, optimize=True)   # (4:4:4: halved colour resolution bled the band's orange into the trousers at the pieces' borders)


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
