#!/usr/bin/env python3
"""Ren's chest in the vest's front opening drawn as in the sheet (9/11/2026, Denis: "migliora ancora la parte del
petto"). Meshy painted it in soft brown smudges (the collarbones' notch like a bat, the breastbone a smear, the tracing's
dashes) with a soft dark shadow along the shirt's V on one side; the sheet (docs/ref/personaggi/ren.png, from the front)
has flat skin, thin ink lines (the collarbones, the breastbone), two clean shadow shapes under the notch, and the V's
edges inked sharp.

chest(img, ys, xs, pos, nor, sheet) paints img (h x w x 3, float, the body's texture) in place; ys, xs, pos, nor: its
texel table (tools/paint_views.texel_table). Called by tools/paint_meshy.py, after the tracing.
- the V: its two edges straight lines on the front (x as a function of the height, fitted to the extent of Meshy's light
  skin between the heights CHEST_FIT), from where they meet up to CHEST_TOP m;
- inside it, and in the skin above it up to CHEST_Y[1] (the head's neck starts there), flat skin (the median of its light
  skin) with the sheet's lines and shadow shapes, mapped from the sheet's V (SHEET_V: its bottom and its edges at the
  height SHEET_V[1][1], in the sheet's pixels; the sheet's collarbones' line, SHEET_CLAV, at CHEST_CLAV m on the model)
  onto the model's;
- on the shirt's side of the V's edges, ink CHEST_INK m wide, then the shirt up to CHEST_BAND m (Meshy's soft shadow
  there in the colour of the nearest shirt beyond it);
- never the vest's teal.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHEST_CX, CHEST_X, CHEST_Y = .005, .095, (1.30, 1.448)   # the region (m): the front, around x = CHEST_CX, between those heights
CHEST_FIT, CHEST_TOP = (1.335, 1.425), 1.434
CHEST_INK, CHEST_BAND = .0016, .006
CHEST_CLAV = 1.438
CHEST_SHEET = {'ren': 'docs/ref/personaggi/ren.png'}   # (the sheet from the front, from the repository's root, per package)
SHEET_BOX = (440, 240, 600, 420)   # the sheet's chest (pixels: x0, y0, x1, y1)
SHEET_V, SHEET_CLAV = ((505., 372.5), (457., 300.), (558., 300.)), 284.
SHEET_EDGE = 2.5   # the sheet's own V edges (their ink: drawn from the model's V) left out of its lines: that near them, px


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


SHEET_UP = 4   # (the sheet's chest upsampled that many times, smooth, before its lines and shapes are cut out: no stair steps)


def sheet_masks(sheet):
    """The sheet's chest: (lines, shadows) as float masks over SHEET_BOX upsampled SHEET_UP times, its skin's and its
    shadows' median colours."""
    x0, y0, x1, y1 = SHEET_BOX; U = SHEET_UP
    im = Image.open(sheet).convert('RGB').crop((x0, y0, x1, y1))
    c = np.asarray(im.resize(((x1 - x0) * U, (y1 - y0) * U), Image.BICUBIC)).astype(np.float64)
    r, b = c[..., 0], c[..., 2]; lum = c.mean(2)
    skin = (r > 200) & (r - b > 60) & (c[..., 1] > 140)
    shadow = (r > 130) & (r - b > 50) & (lum < 175) & (lum > 95) & ~skin
    dark = lum < 90
    # the V's inside (and the band of the collarbones' line above it): its lines are the thin dark strokes there, not the
    # shirt; the V's own edges left out
    (bx, by), (lx, ly), (rx, ry) = SHEET_V
    gy, gx = (np.mgrid[0:(y1 - y0) * U, 0:(x1 - x0) * U].astype(np.float64) + .5) / U
    gy += y0; gx += x0
    def side(ax, ay, cx_, cy_):   # signed distance (px) from the line a-c, positive toward the V's inside
        nx, ny = cy_ - ay, -(cx_ - ax); n = np.hypot(nx, ny); d = ((gx - ax) * nx + (gy - ay) * ny) / n
        return d if ((bx + lx + rx) / 3 - ax) * nx + ((by + ly + ry) / 3 - ay) * ny > 0 else -d
    dl, dr = side(bx, by, lx, ly), side(bx, by, rx, ry)
    inside = (np.minimum(dl, dr) > SHEET_EDGE) & (gy > SHEET_CLAV - 4)
    top = (gy < ly - 6) & (gy > SHEET_CLAV - 4) & (gx > lx + 2) & (gx < rx - 2)   # (the collarbones' line: across the V's top; not the neck's lines above)
    disk = np.hypot(*np.mgrid[-2 * U:2 * U + 1, -2 * U:2 * U + 1]) <= 2 * U + .01
    thin = dark & ~ndimage.binary_opening(dark, structure=disk)
    lines = ndimage.gaussian_filter((thin & (inside | top)).astype(np.float64), U * .4)   # (about a texel of the model wide: its antialiasing)
    shad = ndimage.gaussian_filter((shadow & (inside | top)).astype(np.float64), U * .4)
    return lines, shad, np.median(c[skin], 0), np.median(c[shadow & (inside | top)], 0)


def v_lines(pos, nor, light):
    """The V's edges: (aL, bL, aR, bR), x = a + b y on the front, fitted to the light skin's extent per height."""
    hs, xl, xr = [], [], []
    for y in np.arange(CHEST_FIT[0], CHEST_FIT[1] + 1e-9, .0025):
        m = light & (np.abs(pos[:, 1] - y) < .00125)
        if m.sum() < 4: continue
        x = pos[m, 0]; hs.append(y); xl.append(np.percentile(x, 1)); xr.append(np.percentile(x, 99))
    hs = np.array(hs); A = np.stack([np.ones_like(hs), hs], 1)
    (aL, bL), (aR, bR) = np.linalg.lstsq(A, np.array(xl), rcond=None)[0], np.linalg.lstsq(A, np.array(xr), rcond=None)[0]
    return aL, bL, aR, bR


def chest(img, ys, xs, pos, nor, sheet, ink=np.array([22., 20, 26])):
    from paint_meshy import parts, TEAL_, SKIN_
    c0 = img[ys, xs].copy(); k = parts(c0)
    reg = (np.abs(pos[:, 0] - CHEST_CX) < CHEST_X) & (pos[:, 1] > CHEST_Y[0]) & (pos[:, 1] < CHEST_Y[1]) & (nor[:, 2] > .2)
    light = reg & (c0[:, 0] > 200) & (c0[:, 0] - c0[:, 2] > 60)
    aL, bL, aR, bR = v_lines(pos, nor, light)
    yb = (aR - aL) / (bL - bR); xb = aL + bL * yb   # (where they meet: the V's bottom)
    x, y = pos[:, 0], pos[:, 1]
    dl = (x - (aL + bL * y)) / np.hypot(1, bL); dr = ((aR + bR * y) - x) / np.hypot(1, bR); d = np.minimum(dl, dr)
    band = reg & (y <= CHEST_TOP) & (y > yb - CHEST_BAND) & (k != TEAL_)
    inside = band & (d > 0)
    above = reg & (y > CHEST_TOP) & (k == SKIN_)
    edge = band & (d <= 0) & (d > -CHEST_INK)
    shirt = band & (d <= -CHEST_INK) & (d > -CHEST_BAND)
    skin_rgb = np.median(c0[light & (d > 0)], 0)
    # the sheet mapped: its V's bottom and its edges at SHEET_V[1][1] onto the model's, at the height where the sheet's
    # collarbones' line falls on CHEST_CLAV
    lines, shad, sk_d, sh_d = sheet_masks(sheet)
    (sbx, sby), (slx, sly), (srx, sry) = SHEET_V
    hv = yb + (sby - sly) / (sby - SHEET_CLAV) * (CHEST_CLAV - yb)
    M = np.array([[xb, yb, 1], [aL + bL * hv, hv, 1], [aR + bR * hv, hv, 1]])
    S = np.array([[sbx, sby], [slx, sly], [srx, sry]])
    Af = np.linalg.solve(M, S)   # (model x, y, 1) -> sheet (u, v)
    paint = inside | above
    uv = np.c_[x[paint], y[paint], np.ones(paint.sum())] @ Af
    x0, y0 = SHEET_BOX[:2]
    co = [(uv[:, 1] - y0) * SHEET_UP - .5, (uv[:, 0] - x0) * SHEET_UP - .5]
    a_ln = _smooth(ndimage.map_coordinates(lines, co, order=1, mode='constant'), .2, .6)
    a_sh = _smooth(ndimage.map_coordinates(shad, co, order=1, mode='constant'), .25, .6)
    sh_rgb = skin_rgb * sh_d / sk_d
    col = skin_rgb[None, :] * (1 - a_sh[:, None]) + sh_rgb[None, :] * a_sh[:, None]
    col = col * (1 - a_ln[:, None]) + ink[None, :] * a_ln[:, None]
    img[ys[paint], xs[paint]] = col
    img[ys[edge], xs[edge]] = ink
    far = band & (d <= -CHEST_BAND) & (d > -3 * CHEST_BAND) & (k != SKIN_)   # (the shirt beyond the band: its own colours)
    if far.any() and shirt.any():
        _, j = cKDTree(pos[far]).query(pos[shirt]); img[ys[shirt], xs[shirt]] = c0[far][j]
    print('chest: V from %.3f m (x %.3f) up, edges x = %.3f %+.2f y and %.3f %+.2f y; %d texels of skin redrawn with the '
          'sheet\'s lines (%d in ink, %d in shadow), %d of ink on its edges, %d of the shirt along them' % (
              yb, xb, aL, bL, aR, bR, int(paint.sum()), int((a_ln > .5).sum()), int((a_sh > .5).sum()), int(edge.sum()), int(shirt.sum())))
    return dict(V=(aL, bL, aR, bR, xb, yb), skin=skin_rgb, A=Af)


if __name__ == '__main__':   # preview: python3 tools/ren_chest.py PACKAGE_DIR IN.jpg SHEET.png OUT.jpg (only the chest's triangles)
    from paint_views import load, texel_table
    pkg, src, sheet, out = sys.argv[1:5]
    name, P, N, UV, I, *_ = load(pkg)
    T = np.asarray(Image.open(src).convert('RGB')).astype(np.float64); TS = T.shape[0]
    C = P[I].mean(1); sel = np.nonzero((C[:, 1] > CHEST_Y[0] - .02) & (C[:, 1] < CHEST_Y[1] + .02) & (np.abs(C[:, 0] - CHEST_CX) < CHEST_X + .02) & (C[:, 2] > -.03))[0]
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I[sel], TS)
    chest(T, ys, xs, pos, nor, sheet)
    Image.fromarray(np.clip(T, 0, 255).round().astype(np.uint8)).save(out, quality=92)
