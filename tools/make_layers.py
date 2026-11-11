#!/usr/bin/env python3
"""Cuts the painted arena (docs/ref/sfondo-cascata.png) into the far layers of the 3D arena (needs Pillow, numpy).

usage: python3 tools/make_layers.py

  assets/arena/cascata_sky.jpg      sky and clouds (the cliffs filled in from the sky), widened and taller
  assets/arena/cascata_cliffs.jpg   cliffs, waterfall and the mist below them; column, banner, lantern, front grass
                                    and floor taken out (they are 3D now) and filled in from around them
  assets/arena/cascata_cliffs_aw.png the cliffs' alpha (red; 0 = sky) and where the water flows (green, as
                                    cascata_mask.png), in the cliffs layer's pixels
  assets/arena/cascata_mist.png     a soft mist band (alpha in the red channel), coloured in the shader
  assets/arena/cascata_layers.json  where the original painting sits in each layer (uv, v from the bottom)
Each layer is the painting widened by PAD_X of its width on both sides (mirrored), the sky PAD_TOP taller (a deeper
blue upwards) and the cliffs PAD_BOTTOM deeper (the mist goes on down): the 3D camera sees more than the flat
backdrop did. build.py embeds every file under assets/ in the page as a data URI.
"""
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'docs', 'ref', 'sfondo-cascata.png')
OUT = os.path.join(ROOT, 'assets', 'arena')
W0, H0 = 1672, 941
PAD_X, PAD_TOP, PAD_BOTTOM = .25, .3, .45
SEAM = 140   # px of crossfade where the painting's far edge wraps round
CLIFFS_W, SKY_W, QUALITY, MAX_KB = 2048, 1024, 82, 700
FLOOR_Y = 725   # the painted floor starts here (the terrace is 3D now)
# Foreground taken out (painting px): the column with its banner (filled mirrored), the lantern and the front grass
# (filled smooth: they stand in the mist).
COLUMN = [(0, 0), (178, 0), (178, 160), (205, 205), (250, 330), (300, 470), (335, 560), (345, 725), (0, 725)]
CUT = [[(1490, 500), (1662, 500), (1668, 725), (1486, 725)],
       [(1350, 640), (1672, 630), (1672, 725), (1350, 725)],
       [(0, 560), (360, 560), (360, 725), (0, 725)],
       # two painted leaves next to the right cliff (the colour test misses them)
       [(1498, 448), (1545, 448), (1545, 485), (1498, 485)], [(1240, 665), (1290, 665), (1290, 695), (1240, 695)]]
# The sky line (painting px, x rising): left hill, the trees left of the crest, the crest with its temple, right cliff.
SKY = [(0, 175), (170, 165), (230, 148), (280, 130), (330, 110), (370, 85), (400, 68), (440, 58), (480, 62), (520, 78),
       (560, 105), (590, 118), (640, 150), (690, 175), (740, 195), (790, 220), (840, 240), (880, 251), (1000, 250),
       (1150, 245), (1168, 238), (1172, 222), (1192, 214), (1212, 222), (1216, 238), (1245, 234), (1265, 210),
       (1290, 195), (1320, 180), (1350, 160), (1380, 130), (1410, 115), (1440, 110), (1480, 120), (1520, 135),
       (1560, 150), (1600, 165), (1640, 175), (1672, 180)]
# The waterfall (as tools/make_assets.py): the sky line never goes below its crest; its mask fades from FOAM_Y down.
WATER = [(672, 254), (1242, 247), (1240, 420), (1185, 470), (1165, 560), (1160, 640), (1080, 672), (820, 672),
         (705, 640), (676, 560)]
FOAM_Y, FOAM_H, FOAM_MIN = 590, 82, .4
MIST_ROWS = (600, 700)


def poly_mask(polys, size):
    m = Image.new('L', size, 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon(p, fill=255)
    return np.asarray(m) > 127


def push_pull(img, known):
    """Fills the unknown pixels of img (H, W, C float) from the known ones: a pyramid of weighted means, each level
    filling the holes of the one above (smooth fill, no streaks)."""
    w = known.astype(np.float64)
    if min(img.shape[:2]) <= 2 or w.all():
        if w.any() and not w.all():
            img = img.copy(); img[~known] = (img * w[..., None]).sum((0, 1)) / w.sum()
        return img
    h, wd = img.shape[:2]
    H2, W2 = (h + 1) // 2 * 2, (wd + 1) // 2 * 2
    pi = np.zeros((H2, W2, img.shape[2])); pi[:h, :wd] = img * w[..., None]
    pw = np.zeros((H2, W2)); pw[:h, :wd] = w
    si = pi.reshape(H2 // 2, 2, W2 // 2, 2, -1).sum((1, 3)); sw = pw.reshape(H2 // 2, 2, W2 // 2, 2).sum((1, 3))
    small = np.where(sw[..., None] > 0, si / np.maximum(sw, 1e-9)[..., None], 0)
    small = push_pull(small, sw > 0)
    up = np.asarray(Image.fromarray(np.uint8(np.clip(small, 0, 255))).resize((W2, H2), Image.BILINEAR), np.float64)
    up = up.reshape(H2, W2, -1)[:h, :wd]
    return np.where(known[..., None], img, up)


def sky_line():
    """The sky line traced by hand on the painting (SKY), per column: the cliffs and the waterfall's crest are below."""
    xs, ys = zip(*SKY)
    return np.interp(np.arange(W0), xs, ys)


def painted_leaves(rgb):
    """The yellow leaves painted in the mist (they would hang still beside the 3D ones): yellow pixels whose
    surroundings are mostly blue, grown by 4 px."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    yellow = (r > 170) & (g > 150) & (b < 140) & (r > b + 60)
    blue = (b > r + 40).astype(np.uint8) * 255
    around = np.asarray(Image.fromarray(blue).filter(ImageFilter.BoxBlur(14)), np.float64) / 255
    m = (yellow & (around > .6)).astype(np.uint8) * 255
    return np.asarray(Image.fromarray(m).filter(ImageFilter.MaxFilter(9)), bool)


def mirror_fill(rgb, poly):
    """Fills poly (the column and its banner, at the left edge) row by row with the picture just right of it, mirrored
    about the poly's right edge (cliff and foliage go on behind it, no blur), then softens a 6 px seam."""
    m = poly_mask([poly], (W0, H0))
    out = rgb.copy()
    for y in range(H0):
        xs = np.nonzero(m[y])[0]
        if not len(xs):
            continue
        e = xs.max() + 1
        src = np.clip(2 * e - xs, 0, W0 - 1)
        out[y, xs] = rgb[y, src]
    seam = np.asarray(Image.fromarray(np.uint8(m) * 255).filter(ImageFilter.MaxFilter(13)), bool) & \
        ~np.asarray(Image.fromarray(np.uint8(m) * 255).filter(ImageFilter.MinFilter(13)), bool)
    soft = np.asarray(Image.fromarray(np.uint8(out)).filter(ImageFilter.GaussianBlur(2)), np.float64)
    return np.where(seam[..., None], soft, out)


def widen(a, top, bottom):
    """a (H, W, C) widened by PAD_X of its width on both sides with the far edge of the painting (the right cliff goes
    on left of the left one, and back), crossfaded over SEAM px so no edge or mirror shows; plus `top` and `bottom`
    empty rows."""
    px = round(W0 * PAD_X)
    left, right = a[:, -px - SEAM:].copy(), a[:, :px + SEAM].copy()
    w = np.linspace(0, 1, SEAM)[None, :, None]
    mid = a.copy()
    mid[:, :SEAM] = left[:, -SEAM:] * (1 - w) + a[:, :SEAM] * w            # wrapped right edge fades into the left edge
    mid[:, -SEAM:] = a[:, -SEAM:] * (1 - w) + right[:, :SEAM] * w           # ... and the left edge into the right one
    a = np.concatenate([left[:, :px], mid, right[:, SEAM:SEAM + px]], 1)
    return np.concatenate([np.zeros((top,) + a.shape[1:]), a, np.zeros((bottom,) + a.shape[1:])], 0)


def save(arr, name, width, mode='RGB'):
    im = Image.fromarray(np.uint8(np.clip(arr, 0, 255)).squeeze(), mode)
    im = im.resize((width, round(im.size[1] * width / im.size[0])), Image.LANCZOS)
    p = os.path.join(OUT, name)
    if name.endswith('.jpg'):
        im.save(p, 'JPEG', quality=QUALITY, optimize=True)
    else:
        im.save(p, 'PNG', optimize=True)
    return p, im.size


def uv_box(top, bottom):
    """Where the original painting sits in a layer widened by PAD_X and by top/bottom rows (v from the bottom)."""
    px, w, h = round(W0 * PAD_X), W0 + 2 * round(W0 * PAD_X), H0 + top + bottom
    return {'u0': px / w, 'u1': (px + W0) / w, 'v0': bottom / h, 'v1': (bottom + H0) / h}


def main():
    os.makedirs(OUT, exist_ok=True)
    rgb = np.asarray(Image.open(SRC).convert('RGB'), np.float64)
    assert rgb.shape[:2] == (H0, W0), rgb.shape
    rgb = mirror_fill(rgb, COLUMN)
    line = sky_line()
    ys = np.arange(H0)[:, None]
    alpha = np.clip(ys - line[None, :] + .75, 0, 1.5) / 1.5       # 1.5 px soft edge at the sky line
    leaves = painted_leaves(rgb)
    print('painted leaves: %d px' % leaves.sum())
    cut = poly_mask(CUT, (W0, H0)) | (ys >= FLOOR_Y).repeat(W0, 1) | leaves
    is_cliff = (alpha > .5) & ~cut
    is_sky = ys < line[None, :] - 3

    # Cliffs: the cut-out parts filled from the cliffs around them, softened; alpha 1 there (the cliff goes on behind).
    cliffs = push_pull(rgb, is_cliff)
    soft = np.asarray(Image.fromarray(np.uint8(cliffs)).filter(ImageFilter.GaussianBlur(3)), np.float64)
    cliffs = np.where(cut[..., None] & ~leaves[..., None], soft, cliffs)
    alpha = np.where(cut & (ys >= line[None, :]), 1., alpha)
    # Below the floor line the mist goes on down: the mean of rows 690-720 per column, paler further down.
    bot = round(H0 * PAD_BOTTOM)
    mist_row = np.asarray(Image.fromarray(np.uint8(cliffs[690:720].mean(0)[None])).filter(ImageFilter.BoxBlur(40)), np.float64)[0]
    cl = widen(cliffs, 0, bot); al = widen(alpha[..., None], 0, bot)
    pale = np.array([235., 245., 252.])
    k = np.linspace(0, 1, bot)[:, None, None]
    cl[H0:] = widen(mist_row[None], 0, 0) * (1 - .6 * k) + pale * .6 * k
    cl[FLOOR_Y:H0] = widen(np.repeat(mist_row[None], H0 - FLOOR_Y, 0), 0, 0)
    al[H0:] = 1
    # The painting's mist blends into the extension over BLEND rows above the floor line (no seam there).
    BLEND = 60
    w = np.linspace(0, 1, BLEND)[:, None, None]
    cl[FLOOR_Y - BLEND:FLOOR_Y] = cl[FLOOR_Y - BLEND:FLOOR_Y] * (1 - w) + cl[FLOOR_Y:FLOOR_Y + 1] * w
    p1, s1 = save(cl, 'cascata_cliffs.jpg', CLIFFS_W)

    # Water mask in the cliffs layer.
    m = Image.new('L', (W0, H0), 0)
    ImageDraw.Draw(m).polygon(WATER, fill=255)
    foam = np.array([1 if y < FOAM_Y else max(FOAM_MIN, 1 - (y - FOAM_Y) / FOAM_H * .6) for y in range(H0)])
    wm = np.asarray(m, np.float64) * foam[:, None]
    wm = np.asarray(Image.fromarray(np.uint8(wm)).filter(ImageFilter.GaussianBlur(5)), np.float64)
    wm = widen(wm[..., None], 0, bot)
    px = round(W0 * PAD_X)
    wm[:, :px] = 0; wm[:, px + W0:] = 0          # no mirrored waterfall
    # alpha in red, water in green: one texture read in the shader
    aw = np.concatenate([al * 255, wm, np.zeros_like(wm)], 2)
    p2, _ = save(aw, 'cascata_cliffs_aw.png', CLIFFS_W)
    p3 = p2

    # Sky: the cliffs filled in from the sky; on top a deeper blue.
    sky = push_pull(rgb, is_sky)
    sky = np.asarray(Image.fromarray(np.uint8(sky)).filter(ImageFilter.GaussianBlur(2)), np.float64)
    sky = np.where(is_sky[..., None], rgb, sky)
    top = round(H0 * PAD_TOP)
    sk = widen(sky, top, 0)
    first = np.asarray(Image.fromarray(np.uint8(sk[top:top + 12].mean(0)[None])).filter(ImageFilter.BoxBlur(150)), np.float64)[0]
    deep = np.array([38., 104., 214.])
    k = np.linspace(1, 0, top)[:, None, None]
    sk[:top] = first[None] * (1 - k) + deep * k
    p4, _ = save(sk, 'cascata_sky.jpg', SKY_W)

    # Mist: soft value noise band, alpha in red (the colour comes from the shader: the painting's mist tone).
    rnd = np.random.RandomState(7)
    n = np.zeros((256, 1024))
    for cells, amp in ((4, .5), (9, .3), (20, .2)):
        g = rnd.rand(cells + 1, cells * 4 + 1)
        g[:, -1] = g[:, 0]                       # repeats in u
        n += amp * np.asarray(Image.fromarray(np.uint8(g * 255)).resize((1024, 256), Image.BICUBIC), np.float64) / 255
    v = np.linspace(0, 1, 256)[:, None]           # 0 = top of the band
    band = np.clip(n * 1.4 - .35, 0, 1) * np.sin(np.pi * v) ** 1.5 * np.clip(v * 1.6, 0, 1)
    p5, _ = save(band[..., None] * 255, 'cascata_mist.png', 1024, 'L')
    mist_col = rgb[MIST_ROWS[0]:MIST_ROWS[1], 560:680].reshape(-1, 3).mean(0)

    meta = {'sky': uv_box(top, 0), 'cliffs': uv_box(0, bot), 'mistColor': [round(c / 255, 3) for c in mist_col]}
    with open(os.path.join(OUT, 'cascata_layers.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    total = 0
    for p in (p1, p2, p4, p5):
        kb = os.path.getsize(p) / 1024; total += kb
        im = Image.open(p)
        print('%-34s %4dx%-4d %-2s %6.1f KB' % (os.path.relpath(p, ROOT), im.size[0], im.size[1], im.mode, kb))
    print('total %.0f KB' % total, json.dumps(meta))
    assert total <= MAX_KB, 'layers are %.0f KB' % total


if __name__ == '__main__':
    main()
