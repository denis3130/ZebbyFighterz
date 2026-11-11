#!/usr/bin/env python3
"""Builds the far depth planes of the 3D arena from Denis's layers of the painting (docs/ref/cascata_livelli,
11/11/2026), like an anime multiplane camera, and paints on what they do not show (Pillow, numpy; tools/synth.py).

usage: python3 tools/make_layers.py [--preview OUTDIR]

  assets/arena/cascata_atlas.jpg    every plane's colours, packed in strips
  assets/arena/cascata_atlas_m.png  the same layout: red = the plane's alpha, green = where the water flows
  assets/arena/cascata_mist.png     a soft mist band (alpha in red; for drifting mist banks, none at the moment)
  assets/arena/cascata_layers.json  the planes (name, box in painting px, strips with their opaque cores), the mist
                                    colour, and the sky dome's colours by elevation
Denis's layers, far to near (Denis: "dal più lontano al più vicino", parallax "delicata", least on 3): 3 = the sky,
the two big mountains (the sun's on the left, the temple's on the right) and the misty valley = the plane `far`
(with `farL` and `farR` past the painting's sides); 2 = the waterfall with its rock sides = `falls` (its water and
spray flow in the shader, not the rock); 1 = the two low hills in front of it with their mist = `hillsL`, `hillsR`;
0 = the floor with the column and the lantern = the 3D floor and props (tools/make_props.py), fixed with the
fighters. At the start camera the planes add up to Denis's composition. Where the free camera of the arena preview
looks past the painting the planes go on as before (Denis: "lasciali come sono"): the hills and the big mountains as
more of themselves (guided image quilting, tools/synth.py: blocks of their own painting along a new ridge going down
into the mist), the mist band at their feet (`base`, from the painting), the sky (`sky`, from the painting) and around
everything a sky dome (src/d_arena.js) with the sky's colours by elevation and the valley's mist below the horizon.
Nothing is mirrored or repeated whole. build.py embeds every file under assets/ in the page as a data URI.
"""
import argparse
import json
import math
import os
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'docs', 'ref', 'sfondo-cascata.png')
OUT = os.path.join(ROOT, 'assets', 'arena')
W0, H0 = 1672, 941
ATLAS_W, QUALITY, MAX_KB, STRIP, CORE = 2048, 84, 1700, 160, 64
FLOOR_Y = 725                                 # the painted floor starts here (the terrace is 3D now)
# Foreground taken out (painting px): the column with its banner, the lantern, the front grass (all 3D now).
CUT = [[(0, 0), (178, 0), (178, 160), (205, 205), (250, 330), (300, 470), (335, 560), (345, 725), (0, 725)],
       [(1490, 480), (1672, 480), (1672, 725), (1486, 725)],
       [(1350, 640), (1672, 630), (1672, 725), (1350, 725)],
       [(0, 560), (360, 560), (360, 725), (0, 725)],
       # two painted leaves next to the right cliff (the colour test misses them)
       [(1498, 448), (1545, 448), (1545, 485), (1498, 485)], [(1240, 665), (1290, 665), (1290, 695), (1240, 695)]]
# The sky line (painting px, x rising), traced by hand: the outlines are refined from the painting (`matte`).
SKY = [(0, 175), (170, 165), (230, 148), (280, 130), (330, 110), (370, 85), (400, 68), (440, 58), (480, 62), (520, 78),
       (560, 105), (590, 118), (640, 150), (690, 175), (740, 195), (790, 220), (840, 240), (880, 251), (1000, 250),
       (1150, 245), (1168, 238), (1172, 222), (1192, 214), (1212, 222), (1216, 238), (1245, 234), (1265, 210),
       (1290, 195), (1320, 180), (1350, 160), (1380, 130), (1410, 115), (1440, 110), (1480, 120), (1520, 135),
       (1560, 150), (1600, 165), (1640, 175), (1672, 180)]
FOAM_Y, FOAM_H, FOAM_MIN = 590, 82, .4   # the water's flow fades from FOAM_Y down into the spray (to FOAM_MIN)
MIST_ROWS = (600, 700)
DEPTH = {'base': -8, 'hillsL': -17, 'hillsR': -17, 'falls': -34, 'far': -90, 'farL': -90, 'farR': -90,
         'sky': -300}   # = CFG.arenas.cascata.layers
# the start camera (CFG.cam, CFG.arenas.cascata.ref): for the sky dome's colours by elevation
FOV, DIST0, FOOT_SCREEN = 30, 6.5, .86
REF_W, REF_H, FOOT_ROW, COVER = 844, 390, .83, 1.1

BOT = 1000      # the hills and the waterfall go down to here (under the floor's edge: mist)
END_FADE = 260  # px: the far end of what goes on past the painting dissolves into the mist over this
# Denis's layers (docs/ref/cascata_livelli), drawn on the painting's canvas at 1674 x 940 (scaled to W0 x H0; the
# points below are in the painting's px).
LAYERS = os.path.join(ROOT, 'docs', 'ref', 'cascata_livelli')
LAYER_FILES = {'far': 'livello3_cielo_montagne.png', 'falls': 'livello2_cascata.png', 'hills': 'livello1_colline.png'}
# 3, far: the sky line over the big mountains and the valley's far hills (traced by hand); its canvas is as wide as the
# sky's; inside the painting its sky fades into the sky plane over FAR_FADE px at its sides and FAR_TOP_FADE at its
# top; past the painting the valley goes on and the mountains go down into it (FAR_DOWN_*), their blocks from FAR_SRC.
FAR_SKY = [(0, 232), (100, 214), (175, 180), (230, 150), (290, 128), (330, 105), (380, 85), (420, 70), (450, 62),
           (490, 68), (520, 80), (560, 100), (600, 125), (630, 140), (660, 160), (700, 175), (740, 195), (770, 210),
           (800, 225), (840, 240), (900, 255), (950, 263), (1000, 268), (1060, 262), (1100, 248), (1150, 240),
           (1240, 214), (1270, 190), (1300, 175), (1350, 150), (1400, 122), (1440, 110), (1480, 112), (1520, 125),
           (1560, 140), (1600, 150), (1640, 165), (1672, 175)]
FAR_X, FAR_BOT = (-1506, 3178), 1100
FAR_VALLEY = (292, 345)     # rows: past the painting the valley's top melts into the sky between these
FAR_DOWN_L = [(-420, 420), (-300, 372), (-180, 322), (-80, 280)]   # the big mountains going down into the valley
FAR_DOWN_R = [(1760, 205), (1860, 250), (1960, 302), (2060, 352), (2180, 405)]   # past the sides (steep: no strip)
FAR_FADE, FAR_TOP_FADE = 150, 120
FAR_SRC = [(130, 840, 60, 930), (1240, 1672, 105, 930)]
# 1, hills: each low hill goes on outwards down into the mist (its new ridge), on its canvas (x from, to), its blocks
# from its own painting (x0, x1, y0, y1); its bottom edge (row 720, cut straight) is pulled down under the floor.
HILLS = {'hillsL': {'X': (-1500, 1000), 'region': [(-1500, -20), (836, -20), (836, 700), (1000, 700), (1000, BOT),
                                                   (-1500, BOT)], 'side': -1, 'gap': (836, 1000),
                    'out': [(-1500, 780), (-1200, 720), (-900, 655), (-600, 590), (-350, 520), (-150, 468)],
                    'src': (0, 834, 380, 718), 'seed': 3},
         'hillsR': {'X': (820, 3170), 'region': [(984, -20), (3170, -20), (3170, BOT), (820, BOT), (820, 700),
                                                  (984, 700)], 'side': 1, 'gap': (984, 820),
                    'out': [(1800, 332), (1950, 372), (2150, 432), (2400, 512), (2700, 600), (3000, 690), (3170, 740)],
                    'src': (988, 1672, 250, 718), 'seed': 7}}
HILLS_SMEAR = (712, 732)   # (rows: from its bottom edge to just under the floor's edge)
MIST_LEVEL = {'hillsL': 590, 'hillsR': 560, 'far': 300}   # row where each one's foot starts to sink into its mist
# 2, falls: the rock on its two sides (the water flows everywhere else) and its canvas.
FALLS_ROCK = [[(413, 472), (428, 380), (448, 330), (474, 290), (508, 262), (560, 247), (610, 254), (616, 300),
               (612, 400), (608, 470), (560, 522), (478, 522)],
              [(1271, 229), (1300, 221), (1340, 224), (1372, 231), (1356, 260), (1331, 300), (1311, 340), (1291, 372),
               (1274, 330), (1271, 280)]]
FALLS_X = (300, 1460)
# The mist at the mountains' feet, in front of all of them: the painting's own rows BASE_ROWS, its waterfall foam taken
# out (FOAM_CUT: it is the waterfall's own, behind); cloud tops at BASE_TOP (lower under the waterfall), BASE_RAMP px
# from clear to solid; it goes on sideways over BASE_X (quilted from itself) and fades out at its ends.
BASE_ROWS, BASE_TOP, BASE_TOP_FALLS, BASE_RAMP = (540, 760), 712, 716, 50   # (its top at the floor's edge since
# Denis's layers: in the painting their own mist; the band is for what the free camera sees past and under them)
BASE_X, BASE_BOT = (-5500, 7150), 1150
FOAM_CUT = [(680, 560), (1215, 560), (1215, 760), (680, 760)]
SKY_SCALE, MTN_SCALE, FALLS_SCALE, BASE_SCALE, FAR_SCALE, FAR_OUT_SCALE = .32, .85, .9, .5, .75, .4
GLOW_X = (250, 470)  # px: left of these the sun's glow was in the sky: more of its clouds painted on there
# The sky's canvas (painting px): as far as the preview's free camera can look (about 60 degrees to each side and 40
# up at its widest), its clouds fading into the sky dome over SKY_FADE px at the sides and top, and from SKY_FOOT[0]
# to SKY_FOOT[1] at its foot (below, the dome's horizon mist).
SKY_X, SKY_TOP, SKY_FOOT, SKY_FADE = (-1506, 3178), -620, (400, 470), 200
DEEP = np.array([.149, .408, .839])   # the deep blue high up (the painting's darkest sky, top right)
SKY_BAND = 120       # px: the painted clouds thin out over this towards the painting's top and sides
# Whole clouds of the painting (painting px boxes: wisps, streaks, the small cumulus left of the waterfall's crest),
# scattered over the sky past the painting (a few, each flipped or not and at its own size): its clouds there too.
SKY_SPRITES = [(590, 25, 830, 118), (650, 125, 880, 248), (995, 72, 1185, 148), (860, 112, 1000, 155)]
SKY_SPRITE_P = [.25, .35, .25, .15]   # how often each
SKY_STAMPS = 24      # how many


def poly_alpha(polys, w, h, ox=0, oy=0):
    """Antialiased coverage (0..1) of polygons (painting px) on a w x h canvas whose top left is painting (ox, oy)."""
    k = 4
    m = Image.new('L', (w * k, h * k), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon([((x - ox) * k, (y - oy) * k) for x, y in p], fill=255)
    return np.asarray(m.resize((w, h), Image.BOX), np.float64) / 255


def line_y(line, xs):
    lx, ly = zip(*line)
    return np.interp(xs, lx, ly)


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
    up = np.stack([np.asarray(Image.fromarray(small[..., i].astype(np.float32), 'F').resize((W2, H2), Image.BILINEAR),
                              np.float64) for i in range(small.shape[2])], 2)[:h, :wd]
    return np.where(known[..., None], img, up)


def shifted(a, dy, dx, fill):
    """a moved so that out[y, x] = a[y + dy, x + dx] (fill where that is outside)."""
    H, W = a.shape
    out = np.full_like(a, fill)
    ys, ye = max(0, -dy), H - max(0, dy)
    xs, xe = max(0, -dx), W - max(0, dx)
    if ys < ye and xs < xe:
        out[ys:ye, xs:xe] = a[ys + dy:ye + dy, xs + dx:xe + dx]
    return out


def nearest_known(known):
    """Jump flooding: for every pixel, the coordinates of (nearly) the nearest known pixel (-1 if none)."""
    H, W = known.shape
    Y, X = np.mgrid[0:H, 0:W]
    sy = np.where(known, Y, -1).astype(np.int32); sx = np.where(known, X, -1).astype(np.int32)
    big = np.int64(1) << 40
    d = np.where(known, 0, big).astype(np.int64)
    step = 1 << max(0, int(np.ceil(np.log2(max(H, W)))) - 1)
    steps = []
    while step >= 1:
        steps.append(step); step //= 2
    for step in steps + [1]:
        for dy in (-step, 0, step):
            for dx in (-step, 0, step):
                if not dy and not dx:
                    continue
                ny, nx = shifted(sy, dy, dx, -1), shifted(sx, dy, dx, -1)
                nd = np.where(ny >= 0, (ny - Y).astype(np.int64) ** 2 + (nx - X).astype(np.int64) ** 2, big)
                b = nd < d
                sy[b] = ny[b]; sx[b] = nx[b]; d[b] = nd[b]
    return sy, sx


def mirror_fill(img, known):
    """Fills the unknown pixels of img from the known ones, mirrored across the nearest edge of the known region (the
    texture goes on: rock as rock, water as water); where the mirror lands on unknown pixels too, the nearest known
    one; then softened a little (only the filled pixels)."""
    H, W = known.shape
    sy, sx = nearest_known(known)
    Y, X = np.mgrid[0:H, 0:W]
    ry, rx = 2 * sy - Y, 2 * sx - X
    ok = (sy >= 0) & (ry >= 0) & (ry < H) & (rx >= 0) & (rx < W)
    ok[ok] = known[ry[ok], rx[ok]]
    srcy = np.where(ok, ry, np.maximum(sy, 0)); srcx = np.where(ok, rx, np.maximum(sx, 0))
    out = np.where(known[..., None], img, img[srcy, srcx])
    soft = np.asarray(Image.fromarray(np.uint8(np.clip(out, 0, 255))).filter(ImageFilter.GaussianBlur(1.2)), np.float64)
    return np.where(known[..., None], img, soft)


def glow_weight(xs):
    """1 left of GLOW_X[0], 0 right of GLOW_X[1]: where the sun's glow is turned to the cool sky and mist."""
    f = np.clip((GLOW_X[1] - xs) / (GLOW_X[1] - GLOW_X[0]), 0, 1)
    return f * f * (3 - 2 * f)


def blur(a, r):
    return np.asarray(Image.fromarray(np.uint8(np.clip(a * 255, 0, 255))).filter(ImageFilter.GaussianBlur(r)), np.float64) / 255


def painted_leaves(rgb):
    """The yellow leaves painted in the mist (they would hang still beside the 3D ones): yellow pixels whose
    surroundings are mostly blue, grown by 4 px."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    yellow = (r > 170) & (g > 150) & (b < 140) & (r > b + 60)
    blue = (b > r + 40).astype(np.uint8) * 255
    around = np.asarray(Image.fromarray(blue).filter(ImageFilter.BoxBlur(14)), np.float64) / 255
    m = (yellow & (around > .6)).astype(np.uint8) * 255
    return np.asarray(Image.fromarray(m).filter(ImageFilter.MaxFilter(9)), bool)


def pack(islands):
    """Shelf-packs the islands (each {'rgb', 'm'} at atlas scale) into ATLAS_W columns, 4 px apart: sets 'at' =
    (x, y) and returns the atlas height."""
    x = y = shelf = 0
    for it in sorted(islands, key=lambda i: -i['rgb'].shape[0]):
        h, w = it['rgb'].shape[:2]
        if x + w > ATLAS_W:
            x, y, shelf = 0, y + shelf + 4, 0
        it['at'] = (x, y)
        x += w + 4; shelf = max(shelf, h)
    return (y + shelf + 3) // 4 * 4


def resized(a, w, h):
    if a.ndim == 2:
        return np.asarray(Image.fromarray(np.uint8(np.clip(a * 255, 0, 255))).resize((w, h), Image.LANCZOS), np.float64) / 255
    return np.asarray(Image.fromarray(np.uint8(np.clip(a, 0, 255))).resize((w, h), Image.LANCZOS), np.float64)


def box(a, r):
    """Mean over the (2r + 1)^2 box around each pixel (integral images; a: H, W or H, W, C)."""
    if a.ndim == 2:
        return box(a[..., None], r)[..., 0]
    H, W, C = a.shape
    I = np.zeros((H + 1, W + 1, C), np.float64); I[1:, 1:] = a.cumsum(0).cumsum(1)
    y0 = np.clip(np.arange(H) - r, 0, H); y1 = np.clip(np.arange(H) + r + 1, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W); x1 = np.clip(np.arange(W) + r + 1, 0, W)
    S = I[y1][:, x1] - I[y0][:, x1] - I[y1][:, x0] + I[y0][:, x0]
    return (S / ((y1 - y0)[:, None] * (x1 - x0)[None, :])[..., None]).astype(np.float32)


def dist_to(mask):
    """Distance (px) from every pixel to the nearest pixel of mask."""
    sy, sx = nearest_known(mask)
    H, W = mask.shape
    return np.hypot(sy - np.arange(H)[:, None], sx - np.arange(W)[None, :]).astype(np.float32)


def matte(rgb, inside, real_out, band=26, r=22):
    """The alpha of the region `inside` (a traced polygon) with its outline taken from the painting: within `band` px of
    the traced line, each pixel is unmixed between the region's local colour and the outside's local colour (means
    over (2r + 1)^2 of the pixels well inside and well outside), where the outside is real painting (real_out);
    where the two are too alike, the traced line stands. rgb in 0..1."""
    d_in, d_out = dist_to(~inside), dist_to(inside)
    coreA = inside & (d_in > band)
    coreB = ~inside & (d_out > band) & real_out
    def lmean(m):
        w = m.astype(np.float32)
        out = box(rgb * w[..., None], r) / np.maximum(box(w, r), 1e-6)[..., None]
        return push_pull(out * 255, box(w, r) > 1e-3) / 255
    CA, CB = lmean(coreA), lmean(coreB)
    dv = CA - CB
    a = np.clip(((rgb - CB) * dv).sum(2) / np.maximum((dv * dv).sum(2), 1e-4), 0, 1)
    conf = np.clip((dv * dv).sum(2) / .02, 0, 1)
    a = a * conf + inside * (1 - conf)
    bandm = ~coreA & ~(~inside & (d_out > band))
    bandm &= dist_to(~inside & real_out) < band + 2          # (only where the outside next to it is real painting)
    alpha = np.where(bandm, a, inside.astype(np.float32))
    am = np.asarray(Image.fromarray(np.uint8(alpha * 255)).filter(ImageFilter.MedianFilter(3)), np.float32) / 255
    return np.where(bandm, am, alpha)


def gblur(a, r):
    """About a Gaussian blur of sigma r (three box passes) of a float image (H, W or H, W, C), any range."""
    k = max(1, round(r))
    return box(box(box(a, k), k), k).astype(np.float64)


def low_pass(img, known, r):
    """The smooth (low-frequency) part of img where known: a normalized Gaussian blur (unknown pixels count for
    nothing), filled smoothly where nothing known is near."""
    w = known.astype(np.float64)
    num, den = gblur(img * w[..., None], r), gblur(w, r)
    out = num / np.maximum(den, 1e-6)[..., None]
    return push_pull(out, den > .05)


def spread(field, at, fall):
    """field (H, W, C) known at the pixels `at`, spread smoothly everywhere (push_pull) and fading out to 0 over `fall`
    px away from them."""
    f = push_pull(np.where(at[..., None], field, 0), at)
    d = np.clip(1 - dist_to(at) / fall, 0, 1)
    return f * (d * d * (3 - 2 * d))[..., None]


def membrane(cv, known, syn, fall=140, r=8, solid=.9):
    """The painted-on pixels' light matched to the painting's along their seam (a membrane, as in seamless cloning):
    on the seam, the difference between the painting's local mean colour and the painted-on one's, spread smoothly
    into the painted-on part and fading out over `fall` px. cv: premultiplied colour (channels 0-2) and alpha (3)."""
    a = cv[..., 3]
    col = np.where(a[..., None] > 1e-3, cv[..., :3] / np.maximum(a, 1e-3)[..., None], 0)
    K = (known & (a > solid)).astype(np.float32)
    S = (syn & (a > solid)).astype(np.float32)
    bK, bS = box(K, r), box(S, r)
    mk = box(col * K[..., None], r) / np.maximum(bK, 1e-6)[..., None]
    ms = box(col * S[..., None], r) / np.maximum(bS, 1e-6)[..., None]
    seam = (S > 0) & (bK > .15) & (bS > .15) & (dist_to(known) < 4)
    if not seam.any():
        return cv
    D = spread(mk - ms, seam, fall)
    out = cv.copy()
    out[..., :3] = np.where(syn[..., None], np.clip(col + D, 0, 1) * a[..., None], cv[..., :3])
    return out


def vnoise(h, w, cell, seed):
    """Smooth value noise in 0..1, features about `cell` px."""
    rng = np.random.RandomState(seed)
    gh, gw = h // cell + 3, w // cell + 3
    im = Image.fromarray(np.uint8(rng.rand(gh, gw) * 255)).resize((gw * cell, gh * cell), Image.BICUBIC)
    return np.asarray(im, np.float32)[:h, :w] / 255


def foliage(rgb):
    """Where the painting has foliage (green or yellow) rather than rock, mist or sky: 0..1, softened."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return box(((g >= b) & (g >= .8 * r)).astype(np.float32), 7)


def undulate(xs, seed):
    """A ridge's own shape on top of its traced line: shoulders and dips (px)."""
    p = seed * 1.7
    return 24 * np.sin(xs / 140. + .7 + p) + 11 * np.sin(xs / 61. + 2.1 + p) + 5 * np.sin(xs / 23. + .4 + p)


def unpremultiply(pm, a, solid=.6):
    """Colours (0..1) from premultiplied ones; where a plane is nearly transparent, its nearest solid colour."""
    a3 = a[..., None]
    col = np.where(a3 > 1e-3, pm / np.maximum(a3, 1e-3), 0)
    return mirror_fill(col * 255, a > solid) / 255


def soften_seam(cv, known, syn, r=5, width=10):
    """Softens the seam where painted pixels meet painted-on ones (both sides, `width` px)."""
    seam = np.where(known, dist_to(syn), dist_to(known)) < width
    sm = np.stack([box(cv[..., i], r) for i in range(cv.shape[2])], 2)
    w = seam[..., None] * .8
    return cv * (1 - w) + sm * w


def ref_place():
    """arRefPlace in src/d_arena.js: the flat backdrop's placement on the ref screen at the start camera."""
    gy = FOOT_SCREEN * REF_H
    s = max(max(REF_W / W0, REF_H / H0) * COVER, REF_W / W0, gy / (FOOT_ROW * H0), (REF_H - gy) / ((1 - FOOT_ROW) * H0))
    su, sv = REF_W / (W0 * s), REF_H / (H0 * s)
    return .5 - su / 2, 1 - FOOT_ROW - (REF_H - gy) / (H0 * s), su, sv


def src_tile(rgb, a, kn, sky_y, fol, box_):
    """A source for the quilting: premultiplied colours + alpha, where whole blocks may come from, and its guides."""
    x0, x1, y0, y1 = box_
    rows = np.arange(y0, y1)[:, None]
    depth = rows - sky_y[None, x0:x1]
    g = np.stack([np.clip(depth / 50., -1.5, 7), np.broadcast_to(np.minimum(rows, 540) / 150., depth.shape),
                  fol[y0:y1, x0:x1] * 2.], 2).astype(np.float32)
    c = np.concatenate([(rgb * a[..., None])[y0:y1, x0:x1], a[y0:y1, x0:x1, None]], 2).astype(np.float32)
    return c, kn[y0:y1, x0:x1], g


def side_by_side(tiles, gap=80):
    """Source tiles joined left to right, an unusable gap between them (no block spans two)."""
    h = max(t[0].shape[0] for t in tiles)
    cs, vs, gs = [], [], []
    for c, v, g in tiles:
        p = h - c.shape[0]
        cs += [np.pad(c, ((0, p), (0, 0), (0, 0))), np.zeros((h, gap, c.shape[2]), np.float32)]
        vs += [np.pad(v, ((0, p), (0, 0))), np.zeros((h, gap), bool)]
        gs += [np.pad(g, ((0, p), (0, 0), (0, 0))), np.zeros((h, gap, g.shape[2]), np.float32)]
    return np.concatenate(cs[:-1], 1), np.concatenate(vs[:-1], 1), np.concatenate(gs[:-1], 1)


def build_mountain(name, rgb, a, inside, kn, sky_y, fol, X, ridge_pts, painted, outer, source, seed, log):
    """One mountain on its canvas (painting x X[0]..X[1], rows 0..BOT): its painting where kept (kn), the rest of its
    region painted on along its ridge (quilted from `source`), its foot sunk into its mist, its far end faded."""
    x0, x1 = X
    Wc, Hc, ox = x1 - x0, BOT, -x0
    px0, px1 = max(0, x0), min(W0, x1)
    cv = np.zeros((Hc, Wc, 4), np.float32)
    known = np.zeros((Hc, Wc), bool)
    known[:H0, px0 + ox:px1 + ox] = kn[:, px0:px1]
    cv[:H0, px0 + ox:px1 + ox, :3] = (rgb * a[..., None])[:, px0:px1]
    cv[:H0, px0 + ox:px1 + ox, 3] = a[:, px0:px1]
    cv[~known] = 0
    cx = np.arange(Wc) - ox
    ridge = np.interp(cx, *zip(*ridge_pts))
    ramp = np.clip((painted[0] - cx) / 120., 0, 1) + np.clip((cx - painted[1]) / 120., 0, 1)   # outside the painting
    ridge = ridge + undulate(cx, seed) * np.clip(ramp, 0, 1)
    rows = np.arange(Hc)[:, None]
    depth = rows - ridge[None, :]
    region = poly_alpha([inside], Wc, Hc, x0, 0) > .5
    target = region & (depth >= -25) & ~known
    # guides: depth below the ridge, height, forest-or-rock (in the new parts: forest along the ridge, patches below)
    fol_c = np.zeros((Hc, Wc), np.float32); fol_c[:H0, px0 + ox:px1 + ox] = fol[:, px0:px1]
    nz = .6 * vnoise(Hc, Wc, 90, seed) + .4 * vnoise(Hc, Wc, 37, seed + 1)
    fol_t = np.maximum(np.clip(1 - depth / 70., 0, 1), np.clip((nz - .45) / .12, 0, 1) * (1 - .5 * np.clip((depth - 60) / 260., 0, 1)))
    g = np.stack([np.clip(depth / 50., -1.5, 7), np.broadcast_to(np.minimum(rows, 540) / 150., (Hc, Wc)),
                  np.where(known, fol_c, fol_t) * 2.], 2).astype(np.float32)
    filled = known.copy()
    t0 = time.time()
    n = synth.quilt(cv, filled, known, target, g, *source, block=72, overlap=24, n_cand=1500, w_guide=4., tol=.1,
                    seed=seed, sub=3)
    log('  %s: %d blocks painted on (%.0f s)' % (name, n, time.time() - t0))
    # its foot sinks into its mist: the painting's mist colours, rising to a wavy level, with soft wisps
    syn = ~known & filled
    m_hi, m_lo = MISTS[name]
    lvl = MIST_LEVEL[name] + 25 * np.sin(cx / 170. + 1.2 + seed) + 12 * np.sin(cx / 53. + .3 + seed)
    wisp = vnoise(Hc, Wc, 45, seed + 4) * .65 + vnoise(Hc, Wc, 17, seed + 5) * .35
    t_ = np.clip((rows - lvl[None, :] + (wisp - .5) * 110) / 150., 0, 1)
    mo = t_ * t_ * (3 - 2 * t_) * .92
    mcol = (m_hi[None, None] * (1 - t_[..., None]) + m_lo[None, None] * t_[..., None]) * (.94 + .12 * wisp[..., None])
    a3 = cv[..., 3:4]
    col = np.where(a3 > 1e-3, cv[..., :3] / np.maximum(a3, 1e-3), 0)
    mixed = col * (1 - mo[..., None]) + mcol * mo[..., None]
    cv[..., :3] = np.where((syn & (depth >= 40))[..., None], mixed * a3, cv[..., :3])
    cv = membrane(cv, known, syn)        # no step of light where the painting meets the painted-on part
    cv = soften_seam(cv, known, syn)
    # the far end dissolves into the mist
    end = np.clip((np.minimum(cx - x0, x1 - cx) if outer == 0 else (cx - x0) if outer < 0 else (x1 - cx)) / END_FADE, 0, 1)
    cv *= (end * end * (3 - 2 * end))[None, :, None]
    al = cv[..., 3]
    rows_on = np.nonzero((al > .003).any(1))[0]
    y0 = max(0, rows_on.min() - 2)
    col = unpremultiply(cv[..., :3], al)
    return {'name': name, 'box': [x0, y0, x1, Hc], 'rgb': col[y0:] * 255, 'm': al[y0:], 'water': None,
            'scale': MTN_SCALE}


MISTS = {}


def load_layers():
    """Denis's layers on the painting's canvas (W0 x H0): far (RGB, 0..1), falls and hills (RGBA, 0..1)."""
    out = {}
    for k, f in LAYER_FILES.items():
        im = Image.open(os.path.join(LAYERS, f)).convert('RGBA').resize((W0, H0), Image.LANCZOS)
        L = np.asarray(im, np.float32) / 255
        L[..., 3] = np.clip((L[..., 3] - .03) / .94, 0, 1)   # (Denis's files stop at 250-254 where they are solid,
        # and have a faint haze of 1-6 alpha around the pieces)
        out[k] = L
    h = out['hills']                                     # the right hill reaches the painting's right edge
    h[:, W0 - 3:] = h[:, W0 - 4:W0 - 3]
    return out


def smear_down(rgba, y0, y1):
    """Its bottom edge pulled down from row y0 to y1: each row keeps at least the row above (colour and alpha), so no
    gap shows between it and what is in front (the floor's edge)."""
    L = rgba.copy()
    for y in range(y0, y1):
        up, cur = L[y - 1], L[y]
        a_up, a_cur = up[:, 3:4], cur[:, 3:4]
        a_new = np.maximum(a_cur, a_up)
        L[y, :, :3] = (cur[:, :3] * a_cur + up[:, :3] * np.clip(a_new - a_cur, 0, 1)) / np.maximum(a_new, 1e-6)
        L[y, :, 3:4] = a_new
    return L


def top_edge(alpha, thr=.5, none=720):
    """Per column, the first row where alpha passes thr (none where it never does)."""
    on = alpha > thr
    return np.where(on.any(0), on.argmax(0), none).astype(np.float64)


def build_hills(L1, log):
    """Layer 1, the two low hills in front of the waterfall: as Denis drew them inside the painting (their bottom
    pulled under the floor's edge), each going on outwards and down into the mist (quilted from its own painting)."""
    L1 = smear_down(L1, *HILLS_SMEAR)
    rgb, a = L1[..., :3], L1[..., 3]
    ys, xs = np.mgrid[0:H0, 0:W0]
    top = top_edge(a)
    fol = foliage(rgb)
    MISTS['hillsL'] = MISTS['hillsR'] = (
        rgb[575:620][a[575:620] > .95].mean(0), rgb[680:715][a[680:715] > .95].mean(0))
    out = []
    for name, h in HILLS.items():
        x0, x1, y0, y1 = h['src']
        kn = ys < HILLS_SMEAR[1]                      # the painting's canvas, down to its pulled bottom: as drawn
        valid = kn & (ys >= top[None, :] - 40) & (ys < 718) & (a > .02) | (kn & (ys >= top[None, :] - 40) & (ys < top[None, :]))
        src = side_by_side([src_tile(rgb, a, valid, top, fol, (x0, x1, y0, y1))])
        xs_in = np.arange(max(0, h['X'][0]), min(W0, h['X'][1]))
        inner = [(int(x), float(top[x])) for x in xs_in[::8] if (x < 834 if h['side'] < 0 else x > 988)]
        ridge = sorted(h['out'] + inner)
        it = build_mountain(name, rgb, a, h['region'], kn, top, fol, h['X'], ridge, (0, W0), h['side'], src,
                            h['seed'], log)
        # under the waterfall the two hills' mists overlap, each fading out (no straight edge under the gap)
        g0, g1 = h['gap']
        cxs = np.arange(it['box'][0], it['box'][2])
        f = np.clip((g1 - cxs) / (g1 - g0), 0, 1)
        f = np.where((cxs - g0) * np.sign(g1 - g0) > 0, f * f * (3 - 2 * f), 1.)
        it['m'] = it['m'] * f[None, :]
        out.append(it)
    return out


def extend_band(rgb, known, X, R, seed, log, name):
    """A band of the painting (rgb 0..1, its known pixels) over painting x X[0]..X[1], rows R[0]..R[1], at full size
    (0..1): the painting where known (blending in over 12 px), elsewhere (built at half size) its brush strokes
    quilted from its own (the guide = the row) on its light going on smoothly as its mean per row (no stripes)."""
    x0, x1 = X
    r0, r1 = R
    H2, W2 = H0 // 2, W0 // 2
    kf = known[:H2 * 2, :W2 * 2]
    cs = (rgb[:H2 * 2, :W2 * 2] * kf[..., None]).reshape(H2, 2, W2, 2, 3).sum((1, 3))
    ks = kf.reshape(H2, 2, W2, 2).sum((1, 3))
    h2, w2, o2, q2 = (r1 - r0) // 2, (x1 - x0) // 2, -x0 // 2, r0 // 2
    rows = max(0, min(H2 - q2, h2))
    kn = np.zeros((h2, w2), bool); kn[:rows, o2:o2 + W2] = (ks >= 4)[q2:q2 + rows]
    col = np.zeros((h2, w2, 3)); col[:rows, o2:o2 + W2] = (cs / np.maximum(ks, 1)[..., None])[q2:q2 + rows]
    n_r = kn.sum(1)
    okr = np.nonzero(n_r >= 40)[0]
    rr = np.arange(h2)
    prof = np.stack([np.interp(rr, okr, ((col * kn[..., None]).sum(1)[okr, c] / n_r[okr])) for c in range(3)], 1)
    gk = np.exp(-.5 * (np.arange(-24, 25) / 8.) ** 2); gk /= gk.sum()
    prof = np.stack([np.convolve(np.pad(prof[:, c], 24, mode='edge'), gk, 'valid') for c in range(3)], 1)
    nz = vnoise(h2, w2, 110, seed)[..., None]
    lo = prof[:, None] * (1 + .05 * (nz - .5)) + spread(low_pass(col, kn, 10) - prof[:, None], kn, 260)
    det = np.where(kn[..., None], col - lo, 0).astype(np.float32)
    g = (np.clip(rr, okr.min(), okr.max()) / 12.)[:, None, None] * np.ones((1, w2, 1))
    g = g.astype(np.float32)
    filled = kn.copy()
    t0 = time.time()
    n = synth.quilt(det, filled, kn, ~kn, g, det[:, o2:o2 + W2].copy(), kn[:, o2:o2 + W2].copy(),
                    g[:, o2:o2 + W2].copy(), block=40, overlap=14, n_cand=1200, w_guide=3., tol=.12, seed=seed, sub=2)
    log('  %s: %d blocks painted on (%.0f s)' % (name, n, time.time() - t0))
    det = np.where(kn[..., None], det, gblur(det, 2) * .8)
    wide = resized(np.clip((lo + det) * 255, 0, 255), x1 - x0, r1 - r0) / 255
    mid = wide[:, -x0:-x0 + W0]
    rows_f = min(H0, r1) - r0
    kb = known[r0:r0 + rows_f]
    k_ = (np.clip(dist_to(~kb) / 12., 0, 1) if (~kb).any() else np.ones(kb.shape))[..., None]
    mid[:rows_f] = rgb[r0:r0 + rows_f] * k_ + mid[:rows_f] * (1 - k_)
    return wide


def build_far(L3, log):
    """Layer 3, the sky with the two big mountains and the misty valley: as Denis drew it inside the painting (its sky
    fading into the sky plane towards the painting's sides and top). Past the painting (only the preview's free camera
    sees it): the valley goes on (its brush strokes quilted, its light smooth; its top melting into the sky) and the
    two big mountains go down into it (quilted from their own painting). Three islands: the painting's part at
    FAR_SCALE, the parts past its sides at FAR_OUT_SCALE."""
    rgb = L3[..., :3].astype(np.float64)
    ys, xs = np.mgrid[0:H0, 0:W0]
    sky = line_y(FAR_SKY, np.arange(W0))
    ground = np.clip((ys - sky[None, :] + 3) / 6., 0, 1)                # 1 under the sky line, soft
    edge = np.clip(np.minimum(xs, W0 - 1 - xs) / FAR_FADE, 0, 1) * np.clip(ys / FAR_TOP_FADE, 0, 1)
    edge = edge * edge * (3 - 2 * edge)
    a = np.maximum(ground, edge)                                        # its sky fades out only near the edges
    X0, X1 = FAR_X
    Wc, Hc, ox = X1 - X0, FAR_BOT, -X0
    cv = np.zeros((Hc, Wc, 4))
    # the valley all round (rows FAR_VALLEY[0] down), its top melting into the sky past the painting
    v0, v1 = FAR_VALLEY
    band = extend_band(rgb, ys >= v0, FAR_X, (v0, Hc), 13, log, 'far valley')
    t = np.clip((np.arange(v0, Hc) - v0) / (v1 - v0), 0, 1)[:, None]
    va = t * t * (3 - 2 * t) * np.ones((1, Wc))
    cv[v0:, :, :3] = band * va[..., None]
    cv[v0:, :, 3] = va
    # the big mountains going down into it past the painting's sides
    fol = foliage(rgb)
    MISTS['far'] = (rgb[300:360].reshape(-1, 3).mean(0), rgb[620:720].reshape(-1, 3).mean(0))
    tiles = [side_by_side([src_tile(rgb, ground, (ys >= sky[None, :] - 30) & (ys < H0 - 8), sky, fol, b)])
             for b in FAR_SRC]                                          # (blocks of ground, see-through above it)
    global BOT
    bot, BOT = BOT, FAR_BOT
    try:
        for (mx0, mx1), out_pts, side, seed, src in (((-800, 260), FAR_DOWN_L, -1, 11, tiles[0]),
                                                     ((W0 - 260, 2400), FAR_DOWN_R, 1, 12, tiles[1])):
            inner = [p for p in FAR_SKY if mx0 <= p[0] <= mx1]
            region = [(mx0, -20), (mx1, -20), (mx1, Hc), (mx0, Hc)]
            it = build_mountain('far', rgb, ground, region, np.ones((H0, W0), bool), sky, fol, (mx0, mx1),
                                sorted(out_pts + inner), (0, W0), side, src, seed, log)
            # over the valley, only past the painting
            bx0, by0, bx1, by1 = it['box']
            m_ = it['m'] * ((np.arange(bx0, bx1) < 0) | (np.arange(bx0, bx1) >= W0))[None, :]
            c0 = bx0 + ox
            seg = cv[by0:by1, c0:c0 + (bx1 - bx0)]
            seg[..., :3] = it['rgb'] / 255 * m_[..., None] + seg[..., :3] * (1 - m_[..., None])
            seg[..., 3] = m_ + seg[..., 3] * (1 - m_)
    finally:
        BOT = bot
    # the painting itself (its sky fading out towards its sides and top)
    cv[:H0, ox:ox + W0, :3] = rgb * a[..., None]
    cv[:H0, ox:ox + W0, 3] = a
    # past its far ends it dissolves
    e_ = np.clip(np.minimum(np.arange(Wc), Wc - 1 - np.arange(Wc)) / END_FADE, 0, 1)
    cv *= (e_ * e_ * (3 - 2 * e_))[None, :, None]
    al = cv[..., 3]
    rows_on = np.nonzero((al > .003).any(1))[0]
    y0 = max(0, rows_on.min() - 2)
    col = unpremultiply(cv[..., :3], al) * 255
    parts = []
    for name, (p0, p1), sc in (('farL', (X0, 0), FAR_OUT_SCALE), ('far', (0, W0), FAR_SCALE),
                               ('farR', (W0, X1), FAR_OUT_SCALE)):
        c0, c1 = p0 + ox, p1 + ox
        parts.append({'name': name, 'box': [p0, y0, p1, Hc], 'rgb': col[y0:, c0:c1], 'm': al[y0:, c0:c1],
                      'water': None, 'scale': sc})
    return parts


def build_layer_falls(L2, log):
    """Layer 2, the waterfall with its rock sides, as Denis drew it: its bottom pulled under the floor's edge and below
    that dissolving into the mist; the water (not the rock) marked for the shader to make it flow, less in the spray."""
    L2 = smear_down(L2, *HILLS_SMEAR)
    x0, x1 = FALLS_X
    Hc, Wc = BOT, x1 - x0
    rock = blur(poly_alpha(FALLS_ROCK, W0, H0), 2)
    foam = np.array([1 if y < FOAM_Y else max(FOAM_MIN, 1 - (y - FOAM_Y) / FOAM_H * .6) for y in range(H0)])
    water = np.clip(L2[..., 3] - rock, 0, 1) * foam[:, None]
    cv = np.zeros((Hc, Wc, 5), np.float32)
    cv[:H0, :, :3] = (L2[..., :3] * L2[..., 3:4])[:, x0:x1]
    cv[:H0, :, 3] = L2[:, x0:x1, 3]
    cv[:H0, :, 4] = (water * L2[..., 3])[:, x0:x1]
    filled = np.zeros((Hc, Wc), bool); filled[:HILLS_SMEAR[1]] = True
    rows = np.arange(Hc)[:, None]
    sm = push_pull(cv.astype(np.float64), filled & (cv[..., 3] > .5))
    fade = np.clip(1 - (rows - HILLS_SMEAR[1]) / 90., 0, 1)
    fade = (fade * fade * (3 - 2 * fade)).astype(np.float32)
    low = ~filled
    cv = np.where(low[..., None], sm * fade[..., None] * (cv[HILLS_SMEAR[1] - 1, :, 3] > .5)[None, :, None], cv)
    al = cv[..., 3]
    rows_on = np.nonzero((al > .003).any(1))[0]
    y0 = max(0, rows_on.min() - 2)
    col = unpremultiply(cv[..., :3], al)
    w = np.clip(cv[..., 4] / np.maximum(al, 1e-3), 0, 1) * (al > .01)
    log('  falls: Denis\'s layer 2, %d x %d' % (Wc, Hc - y0))
    return {'name': 'falls', 'box': [x0, y0, x1, Hc], 'rgb': col[y0:] * 255, 'm': al[y0:], 'water': w[y0:],
            'scale': FALLS_SCALE}


def main(preview):
    t_all = time.time()
    log = print
    os.makedirs(OUT, exist_ok=True)
    rgb8 = np.asarray(Image.open(SRC).convert('RGB'), np.float64)
    assert rgb8.shape[:2] == (H0, W0), rgb8.shape
    ys, xs = np.mgrid[0:H0, 0:W0]
    sky_y = line_y(SKY, np.arange(W0))
    leaves = painted_leaves(rgb8)
    unknown = (poly_alpha(CUT, W0, H0) > .01) | leaves | (ys >= FLOOR_Y)
    lay = load_layers()
    islands = build_hills(lay['hills'], log)
    islands.append(build_layer_falls(lay['falls'], log))
    islands += build_far(lay['far'], log)
    islands.append(build_base(rgb8, unknown, log))
    islands.append(build_sky(rgb8, unknown, sky_y, ys, xs, log))
    dome = dome_colours(islands[-1], mist_profile(lay['far'][..., :3].astype(np.float64) * 255))
    write_atlas(islands, rgb8, dome, preview)
    log('done in %.0f s' % (time.time() - t_all))


def build_base(rgb8, unknown, log):
    """The mist at the mountains' feet, in front of all of them: the painting's own (its waterfall foam, the column,
    the lantern and the grass taken out) and, at half size, the rest of it all round: sideways and down below the floor
    its brush strokes quilted from its own, its light going on smoothly as its mean per row (no stripes); cloud tops
    on it."""
    b0, b1 = BASE_ROWS
    x0, x1 = BASE_X
    rgb = rgb8 / 255
    bk = ~(unknown | (poly_alpha([FOAM_CUT], W0, H0) > .01))
    bk[:b0] = False; bk[b1:] = False
    # the painting's band at half size (known pixels only), on the half-size canvas
    H2, W2 = H0 // 2, W0 // 2
    kf = bk[:H2 * 2, :W2 * 2]
    cs = (rgb[:H2 * 2, :W2 * 2] * kf[..., None]).reshape(H2, 2, W2, 2, 3).sum((1, 3))
    ks = kf.reshape(H2, 2, W2, 2).sum((1, 3))
    h2, w2, o2, r2 = (BASE_BOT - b0) // 2, (x1 - x0) // 2, -x0 // 2, b0 // 2
    rows = min(H2 - r2, h2)
    known = np.zeros((h2, w2), bool); known[:rows, o2:o2 + W2] = (ks >= 4)[r2:r2 + rows]
    col = np.zeros((h2, w2, 3)); col[:rows, o2:o2 + W2] = (cs / np.maximum(ks, 1)[..., None])[r2:r2 + rows]
    # its light: the mean per row (smooth down the rows, the last one below), its own near the painting
    n_r = known.sum(1)
    okr = np.nonzero(n_r >= 40)[0]
    rr = np.arange(h2)
    prof = np.stack([np.interp(rr, okr, ((col * known[..., None]).sum(1)[okr, c] / n_r[okr])) for c in range(3)], 1)
    gk = np.exp(-.5 * (np.arange(-24, 25) / 8.) ** 2); gk /= gk.sum()
    prof = np.stack([np.convolve(np.pad(prof[:, c], 24, mode='edge'), gk, 'valid') for c in range(3)], 1)
    nz = vnoise(h2, w2, 110, 21)[..., None]
    lo = prof[:, None] * (1 + .06 * (nz - .5)) + spread(low_pass(col, known, 10) - prof[:, None], known, 260)
    det = np.where(known[..., None], col - lo, 0).astype(np.float32)
    # its brush strokes all round, from its own (the guide = the row, below the floor the lowest painted rows')
    g = (np.clip(rr, okr.min(), okr.max()) / 12.)[:, None, None] * np.ones((1, w2, 1))
    g = g.astype(np.float32)
    sv = known[:, o2:o2 + W2].copy()
    filled = known.copy()
    t0 = time.time()
    n = synth.quilt(det, filled, known, ~known, g, det[:, o2:o2 + W2].copy(), sv, g[:, o2:o2 + W2].copy(),
                    block=40, overlap=14, n_cand=1200, w_guide=3., tol=.12, seed=9, sub=2)
    log('  base: %d blocks painted on (%.0f s)' % (n, time.time() - t0))
    det = np.where(known[..., None], det, gblur(det, 2) * .8)   # mist is soft: no block edges in the new parts
    wide = resized(np.clip((lo + det) * 255, 0, 255), x1 - x0, BASE_BOT - b0)
    # the painting itself at full size where it is known, blending into the new parts over 12 px
    mid = wide[:, -x0:-x0 + W0]
    kb = bk[b0:H0]
    ks_ = np.clip(dist_to(~kb) / 12., 0, 1)[..., None]
    mid[:H0 - b0] = rgb8[b0:] * ks_ + mid[:H0 - b0] * (1 - ks_)
    bx = np.arange(x0, x1)
    under = np.clip(1 - np.abs(bx - 945) / 330, 0, 1)            # under the waterfall the tops sit lower
    tops = BASE_TOP + (BASE_TOP_FALLS - BASE_TOP) * np.minimum(1, under * 1.6) + \
        30 * (vnoise(1, x1 - x0, 80, 31)[0] - .5) + 12 * (vnoise(1, x1 - x0, 27, 32)[0] - .5)   # puffs, not teeth
    f = np.clip((np.arange(b0, BASE_BOT)[:, None] - tops[None, :]) / BASE_RAMP, 0, 1)
    end = np.clip(np.minimum(bx - x0, x1 - bx) / 400., 0, 1)
    m = f * f * (3 - 2 * f) * (end * end * (3 - 2 * end))[None, :]
    return {'name': 'base', 'box': [x0, b0, x1, BASE_BOT], 'rgb': wide, 'm': m, 'water': None, 'scale': BASE_SCALE}


def build_sky(rgb8, unknown, sky_y, ys, xs, log):
    """The sky as far as the free camera looks (SKY_X, from SKY_TOP down to SKY_FOOT), at half size: the painting's sky
    in the middle (its sun's glow on the left taken out); its light (the low frequencies) going on smoothly as its
    mean per row, deeper blue higher up (DEEP); its clouds (the detail) quilted all round from its own, the guide =
    the row (no mirror, no copy wrapped round); fading into the sky dome at its sides, top and foot."""
    rgb = rgb8 / 255
    known_f = (ys < sky_y[None, :] - 14) & ~unknown & (glow_weight(xs) < .15)
    H2, W2 = H0 // 2, W0 // 2                                  # the painting at half size, known pixels only
    kf = known_f[:H2 * 2, :W2 * 2]
    cs = (rgb[:H2 * 2, :W2 * 2] * kf[..., None]).reshape(H2, 2, W2, 2, 3).sum((1, 3))
    ks = kf.reshape(H2, 2, W2, 2).sum((1, 3))
    kh = ks >= 4
    colh = cs / np.maximum(ks, 1)[..., None]
    X0, X1 = SKY_X
    ox, oy = -X0 // 2, -SKY_TOP // 2                           # canvas px of the painting's (0, 0)
    Wc, Hc = (X1 - X0) // 2, (SKY_FOOT[1] - SKY_TOP) // 2
    rp = min(H2, Hc - oy)
    kn = np.zeros((Hc, Wc), bool); kn[oy:oy + rp, ox:ox + W2] = kh[:rp]
    col = np.zeros((Hc, Wc, 3)); col[oy:oy + rp, ox:ox + W2] = colh[:rp]
    # its light: the mean per row (rows with enough sky), deeper blue above the painting, the last one below
    n_r = kn.sum(1)
    ok = n_r >= 20
    prof = np.zeros((Hc, 3))
    prof[ok] = (col * kn[..., None]).sum(1)[ok] / n_r[ok, None]
    r_ok = np.nonzero(ok)[0]
    r0, r1 = r_ok.min(), r_ok.max()
    rr = np.arange(Hc)
    gk = np.exp(-.5 * (np.arange(-36, 37) / 12.) ** 2); gk /= gk.sum()
    for c in range(3):
        prof[:, c] = np.interp(rr, r_ok, prof[r_ok, c])
        prof[:, c] = np.convolve(np.pad(prof[:, c], 36, mode='edge'), gk, 'valid')   # no stripes along the rows
    k = np.clip((r0 - rr) / max(1, r0), 0, 1)[:, None]          # above the painting: towards the deep blue
    k = k * k * (3 - 2 * k)
    prof = prof * (1 - k) + DEEP[None] * k
    lo_k = low_pass(col, kn, 12)
    lo = prof[:, None] + spread(lo_k - prof[:, None], kn, 150)
    det = np.where(kn[..., None], col - lo, 0).astype(np.float32)
    # its clouds thin out towards the painting's top and sides and where the glow was (none of that is ever seen
    # by the game's camera, only by the preview's free one): no cloud cut by a straight edge
    cx_p = (np.arange(Wc) - ox) * 2
    frame = ((rr - oy >= 0) & (rr - oy < H2))[:, None] & ((cx_p >= 0) & (cx_p < W0))[None, :]
    sky_h = np.interp(np.clip(cx_p, 0, W0 - 1), np.arange(W0), sky_y) / 2 + oy
    hole = frame & ~kn & (rr[:, None] < sky_h[None, :] - 7) & (cx_p[None, :] < GLOW_X[1] + 60)
    band = SKY_BAND / 2
    t_ = np.clip(dist_to(~frame | hole) / band, 0, 1)
    det = det * (t_ * t_ * (3 - 2 * t_))[..., None]
    sky = lo + det
    # whole clouds scattered past it: each sprite's colours over the sky's light, by how much it stands out
    rng = np.random.RandomState(5)
    lum = lambda a_: a_ @ np.array([.3, .59, .11])
    placed, tries = [], 0
    clear = ~frame | ((rr[:, None] - oy) * 2 < 170) & ~(kn & (t_ > .5))   # never where the game's camera looks
    while len(placed) < SKY_STAMPS and tries < 4000:
        tries += 1
        k_ = rng.choice(len(SKY_SPRITES), p=SKY_SPRITE_P)
        bx0, by0, bx1, by1 = [v // 2 for v in SKY_SPRITES[k_]]
        sc = rng.uniform(1.1, 2.1)
        w_, h_ = round((bx1 - bx0) * sc * rng.uniform(.8, 1.45)), round((by1 - by0) * sc)
        X = rng.randint(0, Wc - w_); Y = rng.randint(0, max(1, (300 - SKY_TOP) // 2 - h_))
        if not clear[Y:Y + h_, X:X + w_].all():
            continue
        if any(X < p[0] + p[2] + 40 and p[0] < X + w_ + 40 and Y < p[1] + p[3] + 30 and p[1] < Y + h_ + 30 for p in placed):
            continue
        src = colh[by0:by1, bx0:bx1]
        a_ = np.clip(lum(src - lo[oy + by0:oy + by1, ox + bx0:ox + bx1]) / .2, 0, 1)
        a_ *= np.clip((src[..., 2] / np.maximum(src[..., 1], 1e-3) - .55) / .15, 0, 1)   # not a sunlit tree top
        dr = np.clip((dist_to(~kh[by0:by1, bx0:bx1]) - 2) / 12., 0, 1)   # sky only: fading out above a ridge's edge
        a_ = gblur(a_ * a_ * (3 - 2 * a_), 1.5) * dr * dr * (3 - 2 * dr)
        ex, ey = np.arange(bx1 - bx0), np.arange(by1 - by0)
        e = np.minimum(np.minimum(ex, ex[::-1])[None, :], np.minimum(ey, ey[::-1])[:, None])
        a_ = a_ * np.clip(e / 10., 0, 1)
        if rng.rand() < .5:
            src, a_ = src[:, ::-1], a_[:, ::-1]
        S_ = resized(src * 255, w_, h_) / 255
        A_ = resized(a_, w_, h_)[..., None]
        sky[Y:Y + h_, X:X + w_] = sky[Y:Y + h_, X:X + w_] * (1 - A_) + S_ * A_
        placed.append((X, Y, w_, h_))
    log('  sky: %d clouds scattered' % len(placed))
    sky = np.clip(sky, 0, 1)
    # into the dome: its sides and top over SKY_FADE px, its foot from SKY_FOOT[0] to SKY_FOOT[1]
    f2 = SKY_FADE / 2
    fx = np.clip(np.minimum(np.arange(Wc), Wc - 1 - np.arange(Wc)) / f2, 0, 1)
    fy = np.clip(rr / f2, 0, 1) * np.clip((SKY_FOOT[1] - (rr * 2 + SKY_TOP)) / (SKY_FOOT[1] - SKY_FOOT[0]), 0, 1)
    m = fy[:, None] * fx[None, :]
    m = m * m * (3 - 2 * m)
    return {'name': 'sky', 'box': [X0, SKY_TOP, X1, SKY_FOOT[1]], 'rgb': sky * 255, 'm': m, 'water': None,
            'scale': SKY_SCALE * 2}


def mist_profile(rgb8):
    """The painting's distant mist, row by row (rows 400 down): the mean of its light, low-saturation blue pixels."""
    c = rgb8 / 255
    mx, mn = c.max(2), c.min(2)
    mist = (mx > .55) & (mx - mn < .45) & (c[..., 2] >= c[..., 0]) & (np.arange(H0)[:, None] >= 400) & \
        (np.arange(H0)[:, None] < FLOOR_Y)
    prof = np.full((H0 + 400, 3), np.nan)
    for r in range(400, FLOOR_Y):
        if mist[r].sum() > 40:
            prof[r] = c[r][mist[r]].mean(0)
    rows = np.arange(H0 + 400)
    ok = ~np.isnan(prof[:, 0])
    return np.stack([np.interp(rows, rows[ok], prof[ok, i]) for i in range(3)], 1)


def dome_colours(sky, mist, n=64, e0=-.7, e1=1., h0=430, h1=500):
    """The sky dome's colour for each elevation (radians) from e0 to e1: what the painting shows at that elevation from
    the start camera (a row of the painting is one elevation, whatever the depth): the sky's mean colour on that row
    above row h0, the distant mist below row h1, blended between."""
    px, py, su, sv = ref_place()
    t = math.tan(math.radians(FOV / 2))
    out = []
    for e in np.linspace(e0, e1, n):
        row = H0 * (1 - (py + sv * (math.tan(e) / t + 1) / 2))
        r = int(np.clip(round((row - sky['box'][1]) * sky['rgb'].shape[0] / (sky['box'][3] - sky['box'][1])), 0,
                        sky['rgb'].shape[0] - 1))
        cs = sky['rgb'][r].mean(0) / 255
        cm = mist[int(np.clip(round(row), 0, len(mist) - 1))]
        k = float(np.clip((row - h0) / (h1 - h0), 0, 1))
        out.append([round(float(v), 4) for v in cs * (1 - k) + cm * k])
    return {'e0': e0, 'e1': e1, 'colors': out}


def write_atlas(islands, rgb, dome, preview):
    """Packs the planes into the atlas (strips with their opaque cores) and writes the files."""
    for it in islands:
        h, w = it['rgb'].shape[:2]
        W, H = max(8, round(w * it['scale'])), max(8, round(h * it['scale']))
        it['rgb'], it['m'] = resized(it['rgb'], W, H), resized(it['m'], W, H)
        if it['water'] is not None:
            it['water'] = resized(it['water'], W, H)
    # Strips: every plane but the falls (its water reads up and down) and the sky (opaque) is cut into vertical strips
    # STRIP px wide, each cropped to its own rows: the shader then reads only where a plane really is, not the sky
    # or the mist that its rectangle also holds.
    strips = []
    for it in islands:
        h, w = it['rgb'].shape[:2]
        cuts = [(0, w)] if it['name'] in ('falls', 'sky') else [(x, min(w, x + STRIP)) for x in range(0, w, STRIP)]
        for x0, x1 in cuts:
            rows = np.nonzero((it['m'][:, x0:x1] > .003).any(1))[0]
            if not len(rows):
                continue
            y0, y1 = max(0, rows.min() - 2), min(h, rows.max() + 3)
            # cores: per CORE px wide column of the strip, the longest run of rows where it is fully opaque (inset by
            # 2 px): drawn first, opaque, near to far, so the GPU skips everything they hide
            cores = []
            for cx0 in range(x0, x1, CORE):
                cx1 = min(x1, cx0 + CORE)
                full = (it['m'][:, cx0:cx1] >= .996).all(1)
                best, run = (0, 0), None
                for yy in range(h + 1):
                    if yy < h and full[yy]:
                        run = yy if run is None else run
                    elif run is not None:
                        if yy - run > best[1] - best[0]:
                            best = (run, yy)
                        run = None
                ry0, ry1 = best[0] + 2, best[1] - 2
                if ry1 - ry0 >= 8 and cx1 - cx0 >= 8:
                    cores.append([cx0 + (2 if cx0 > x0 else 0), ry0, cx1 - (2 if cx1 < x1 else 0), ry1])
            strips.append({'name': it['name'], 'rgb': it['rgb'][y0:y1, x0:x1], 'm': it['m'][y0:y1, x0:x1],
                           'water': None if it['water'] is None else it['water'][y0:y1, x0:x1],
                           'f': [round(x0 / w, 6), round(1 - y1 / h, 6), round(x1 / w, 6), round(1 - y0 / h, 6)],
                           'px': (x0, y0, x1, y1), 'iw': w, 'ih': h, 'cores': cores})
    AH = pack(strips)
    col = np.zeros((AH, ATLAS_W, 3)); msk = np.zeros((AH, ATLAS_W, 3))
    for it in strips:
        (x, y), (h, w) = it['at'], it['rgb'].shape[:2]
        # each island 2 px wider all round (its own edge pixels), so bilinear reads never mix two islands
        pr = np.pad(it['rgb'], ((2, 2), (2, 2), (0, 0)), mode='edge')
        X0, Y0 = x - 2, y - 2
        sx, sy = max(0, -X0), max(0, -Y0)
        ex, ey = min(ATLAS_W, X0 + pr.shape[1]), min(AH, Y0 + pr.shape[0])
        col[Y0 + sy:ey, X0 + sx:ex] = pr[sy:ey - Y0, sx:ex - X0]
        mm = np.zeros((h, w, 3)); mm[..., 0] = it['m'] * 255
        if it['water'] is not None:
            mm[..., 1] = it['water'] * 255
        pm_ = np.pad(mm, ((2, 2), (2, 2), (0, 0)), mode='edge')   # the same 2 px of its own edge as the colours
        msk[Y0 + sy:ey, X0 + sx:ex] = pm_[sy:ey - Y0, sx:ex - X0]
        it['uv'] = [round(x / ATLAS_W, 6), round(1 - (y + h) / AH, 6), round((x + w) / ATLAS_W, 6), round(1 - y / AH, 6)]
        # each core in the plane's uv (f) and in the atlas (uv)
        sx0, sy0 = it['px'][0], it['px'][1]
        it['coreq'] = [{'f': [round(c[0] / it['iw'], 6), round(1 - c[3] / it['ih'], 6), round(c[2] / it['iw'], 6), round(1 - c[1] / it['ih'], 6)],
                        'uv': [round((x + c[0] - sx0) / ATLAS_W, 6), round(1 - (y + c[3] - sy0) / AH, 6),
                               round((x + c[2] - sx0) / ATLAS_W, 6), round(1 - (y + c[1] - sy0) / AH, 6)]} for c in it['cores']]
    pc = os.path.join(OUT, 'cascata_atlas.jpg'); pm = os.path.join(OUT, 'cascata_atlas_m.png')
    Image.fromarray(np.uint8(np.clip(col, 0, 255))).save(pc, 'JPEG', quality=QUALITY, optimize=True)
    Image.fromarray(np.uint8(np.clip(msk, 0, 255))).save(pm, 'PNG', optimize=True)

    # Mist: soft value noise band, alpha in red (the colour comes from the shader: the painting's mist tone).
    rnd = np.random.RandomState(7)
    n = np.zeros((256, 1024))
    for cells, amp in ((4, .5), (9, .3), (20, .2)):
        g = rnd.rand(cells + 1, cells * 4 + 1)
        g[:, -1] = g[:, 0]                       # repeats in u
        n += amp * np.asarray(Image.fromarray(np.uint8(g * 255)).resize((1024, 256), Image.BICUBIC), np.float64) / 255
    v = np.linspace(0, 1, 256)[:, None]           # 0 = top of the band
    band = np.clip(n * 1.4 - .35, 0, 1) * np.sin(np.pi * v) ** 1.5 * np.clip(v * 1.6, 0, 1)
    pmist = os.path.join(OUT, 'cascata_mist.png')
    Image.fromarray(np.uint8(band * 255)).save(pmist, 'PNG', optimize=True)
    mist_col = rgb[MIST_ROWS[0]:MIST_ROWS[1], 560:680].reshape(-1, 3).mean(0)

    meta = {'atlas': [ATLAS_W, int(AH)], 'dome': dome, 'planes': [{'name': it['name'], 'box': [int(v) for v in it['box']],
                                                    'strips': [{'f': st['f'], 'uv': st['uv'], 'cores': st['coreq']} for st in strips if st['name'] == it['name']]}
                                                   for it in islands],
            'mistColor': [round(c / 255, 3) for c in mist_col]}
    with open(os.path.join(OUT, 'cascata_layers.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    for old in ('cascata_sky.jpg', 'cascata_cliffs.jpg', 'cascata_cliffs_aw.png'):
        if os.path.exists(os.path.join(OUT, old)):
            os.remove(os.path.join(OUT, old))
    total = 0
    for p in (pc, pm, pmist):
        kb = os.path.getsize(p) / 1024; total += kb
        im = Image.open(p)
        print('%-34s %4dx%-4d %-3s %6.1f KB' % (os.path.relpath(p, ROOT), im.size[0], im.size[1], im.mode, kb))
    for it in islands:
        n = [st for st in strips if st['name'] == it['name']]
        core = sum((c[2] - c[0]) * (c[3] - c[1]) for st in n for c in st['cores'])
        print('  %-6s box %-26s %2d strips, %d atlas px, %d%% in cores' % (it['name'], [int(v) for v in it['box']], len(n), sum(st['rgb'].shape[0] * st['rgb'].shape[1] for st in n), 100 * core / max(1, sum(st['rgb'].shape[0] * st['rgb'].shape[1] for st in n))))
    print('total %.0f KB' % total)
    assert total <= MAX_KB, 'layers are %.0f KB' % total

    if preview:   # every plane on its own over magenta, and the start-camera sum (it must look like the painting)
        os.makedirs(preview, exist_ok=True)
        for it in islands:
            m = it['m'][..., None]
            Image.fromarray(np.uint8(it['rgb'] * m + np.array([255, 0, 255]) * (1 - m))).save(os.path.join(preview, 'plane_%s.png' % it['name']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview')
    main(ap.parse_args().preview)
