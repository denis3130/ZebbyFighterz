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
