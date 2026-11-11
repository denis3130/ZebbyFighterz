#!/usr/bin/env python3
"""Cuts the painted arena (docs/ref/sfondo-cascata.png) into the far depth planes of the 3D arena, like an anime
multiplane camera (needs Pillow, numpy).

usage: python3 tools/make_layers.py [--preview OUTDIR]

  assets/arena/cascata_atlas.jpg    every plane's colours, packed in strips
  assets/arena/cascata_atlas_m.png  the same layout: red = the plane's alpha, green = where the water flows
  assets/arena/cascata_mist.png     a soft mist band (alpha in red; drifting mist banks, none at the moment)
  assets/arena/cascata_layers.json  the planes: name, box (painting px: x0, y0, x1, y1, y down; may reach past the
                                    painting), strips (f = the strip in the plane's uv, uv = in the atlas: u0, v0, u1,
                                    v1, v up) with their opaque cores, mist colour
The planes (their depths are in CFG.arenas.cascata.layers): base = the painted mist at the mountains' feet, one band in
front of all of them; L and R = the two mountains, left and right of the waterfall, each one whole piece exactly as
painted (nothing inside a mountain is ever uncovered, so nothing in them is invented); falls = the waterfall, which
goes on behind them (copied from itself sideways: water, crest and bank); far = pale mountains in the haze past
their outer slopes; haze = the far mist; sky. At the start camera they add up to the painting: where a plane shows,
it has the painting's colours. The column with its banner, the lantern, the front grass, the painted floor and the
yellow leaves painted in the mist are 3D now (or gone): the planes fill them in. build.py embeds every file under
assets/ in the page as a data URI.
"""
import argparse
import json
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'docs', 'ref', 'sfondo-cascata.png')
OUT = os.path.join(ROOT, 'assets', 'arena')
W0, H0 = 1672, 941
PAD_X, PAD_TOP, PAD_BOTTOM = .25, .3, .45     # the sky and the haze reach this far past the painting
SEAM = 140                                    # px of crossfade where the sky's far edge wraps round
ATLAS_W, QUALITY, MAX_KB, STRIP, CORE = 2048, 84, 900, 160, 64
FLOOR_Y = 725                                 # the painted floor starts here (the terrace is 3D now)
# Foreground taken out (painting px): the column with its banner, the lantern, the front grass (all 3D now).
CUT = [[(0, 0), (178, 0), (178, 160), (205, 205), (250, 330), (300, 470), (335, 560), (345, 725), (0, 725)],
       [(1490, 500), (1662, 500), (1668, 725), (1486, 725)],
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
# The waterfall (as tools/make_assets.py) and its mask's fade towards the foam.
WATER = [(672, 254), (1242, 247), (1240, 420), (1185, 470), (1165, 560), (1160, 640), (1080, 672), (820, 672),
         (705, 640), (676, 560)]
FOAM_Y, FOAM_H, FOAM_MIN = 590, 82, .4
# where the water goes on behind the cliffs on both sides (seen when they slide): it flows there too
WATER_HIDDEN = [[(540, 256), (690, 256), (690, 560), (705, 640), (540, 640)],
                [(1225, 247), (1430, 247), (1430, 640), (1160, 640), (1165, 560), (1185, 470), (1225, 430)]]
MIST_ROWS = (600, 700)

# The planes, traced by hand on the painting (painting px; x may go past the painting's edges).
FL_CROWN = [(330, 347), (350, 340), (363, 330), (383, 317), (403, 303), (420, 300), (440, 300), (450, 287), (463, 270),
            (473, 263), (493, 250), (503, 243), (513, 232), (523, 220), (547, 213), (570, 210), (583, 200), (597, 192),
            (617, 190), (630, 200), (650, 213), (663, 232), (672, 254)]
FR_FALLS_EDGE = [(1232, 441), (1194, 465), (1180, 493), (1166, 530), (1147, 558), (1124, 582), (1096, 605), (1058, 634),
                 (1030, 652)]
LF_TOP = [(300, 470), (321, 452), (330, 427), (370, 432), (410, 432), (432, 430), (459, 434), (477, 445), (499, 463),
          (522, 472), (544, 490), (566, 494), (589, 512), (607, 530), (629, 538), (658, 552), (686, 567), (711, 586),
          (735, 620), (750, 660)]
BOTTOM = 820   # px: every plane goes down solid to here, below the painted floor line: the terrace hides its base
EXT = 430      # px: how far the two mountains (and the sky line) go on past each side of the painting
# The sky line past the painting: on the left, where the column and the sun's glow were, the left mountain's shoulder
# goes down into the mist; on the right the right mountain goes on and down.
SKY_LEFT = [(-EXT, 700), (-320, 640), (-220, 560), (-120, 470), (-30, 385), (40, 320), (100, 262), (150, 212),
            (195, 170)]
SKY_RIGHT = [(1730, 215), (1800, 265), (1880, 330), (1960, 410), (2040, 500), (W0 + EXT, 570)]
SKY_EXT = SKY_LEFT + SKY[2:] + SKY_RIGHT
# The mountains are two whole pieces, exactly as painted, each at one depth: L everything left of the waterfall (the
# high cliff, the orange cliff, the dark forest at their foot, the shoulder on the far left), R everything right of
# it. Nothing inside a mountain is ever uncovered, so nothing in them is invented: only where the painting had the
# column (L's left part, mirrored from L) and past the painting's edges (each mountain mirrored at the edge). The
# waterfall behind them goes on (as water) further than they ever slide. smooth = the props' holes in it (lantern,
# grass, leaves: all in the mist) are filled smooth, not mirrored. scale = atlas pixels per painting pixel.
PLANES = [
    # L ends on the left a little right of where the painted column stood (its light, the glow, stays out), its edge
    # there a line of tree crowns (bumps: rows from, to, depth px); past it, far mountains and the sky
    {'name': 'L', 'scale': .9, 'bumps': (150, 760, 20), 'polys': [
        [(200, 0), (645, 0), (640, 143), (655, 200), (665, 232), (668, 250), (672, 254), (672, 288), (677, 336),
         (679, 384), (677, 432), (672, 480), (672, 520), (668, 560), (668, BOTTOM), (372, BOTTOM), (370, 725),
         (360, 560), (325, 470), (275, 330), (230, 205), (203, 160)],
        LF_TOP + [(752, 690), (748, BOTTOM), (372, BOTTOM)]]},
    {'name': 'R', 'scale': .9, 'smooth': True, 'polys': [
        [(1247, 0), (W0 + EXT, 0), (W0 + EXT, BOTTOM), (1000, BOTTOM), (1012, 720)] + FR_FALLS_EDGE[::-1] +
        [(1236, 410), (1235, 357), (1240, 300), (1244, 245), (1247, 215)]]},
    # the waterfall behind the mountains: more of itself copied sideways from its middle (water, the crest's row),
    # never a mirror (blocks) nor its temple again: (dx, from x, to x) for the hidden pixels in that range
    # (its own top: the painted sky line over the crest, and behind the mountains its bank and crest going on, so
    # what a mountain uncovers is bank, crest and water, never what was sky above them)
    {'name': 'falls', 'scale': 1., 'water': True, 'smooth': True,
     'top': [(450, 215), (520, 196), (590, 178), (640, 150)] + [p for p in SKY if 640 < p[0] < 1245] +
            [(1245, 236), (1272, 249), (1430, 251)],
     # (offsets, x from, x to, row from, row to): above its crest the bank is copied along its slope, below the crest
     # the water straight across (the crest stays level)
     'clone': [([(60, 0), (130, 0), (200, 0)], 0, 740, 0, 247), ([(270, 0), (200, 0), (340, 0)], 0, 740, 247, H0),
               ([(-270, 0), (-200, 0), (-340, 0), (-130, 0)], 1180, W0, 0, H0)],
     'fringe': 13, 'noclone': [(1150, 195), (1235, 195), (1235, 256), (1150, 256)],
     'polys': [
        [(500, 160), (640, 143), (640, 30), (1245, 30), (1245, 236), (1415, 242), (1400, 420), (1352, 441),
         (1314, 465), (1300, 493), (1286, 530), (1267, 558), (1244, 582), (1216, 605), (1178, 634), (1150, 652),
         (1120, BOTTOM), (550, BOTTOM), (552, 300), (545, 160)]]},
]
# The mist at the mountains' feet, as painted, in one band in front of all of them (they sink into it together, so
# their feet never slide apart): the painting's rows from BASE_ROWS[0] down, the waterfall's foam taken out (it is
# the waterfall's own, behind), cloud tops at BASE_TOP (lower under the waterfall: its foam shows above), BASE_RAMP
# px from clear to solid.
BASE_ROWS, BASE_TOP, BASE_TOP_FALLS, BASE_RAMP, BASE_PAD = (540, 760), 612, 668, 50, 760
FOAM_CUT = [(680, 560), (1215, 560), (1215, 760), (680, 760)]
# Far mountains, pale in the haze, past the two mountains' outer slopes: (peak x, peak row) each, their sides slope
# FAR_SLOPE px down per px out; FAR_HAZE = how much of the horizon's haze is in their colour (top, bottom).
FAR_PEAKS = [(-470, 300), (-170, 250), (120, 300), (1700, 300), (1960, 235), (2230, 290)]
FAR_SLOPE, FAR_HAZE_MIX, FAR_BOX = .75, (.5, .8), (-760, 140, 2470, BOTTOM)
# The haze plane's own top: its hills against the sky on the left, then low behind the nearer planes.
HAZE_TOP = [(0, 172), (215, 157), (260, 178), (300, 205), (345, 240), (420, 300), (500, 350), (580, 410), (660, 470),
            (760, 500), (900, 510), (1050, 500), (1150, 485), (1250, 470), (1350, 440), (1450, 400), (1530, 370),
            (1580, 335), (1625, 300), (W0, 285)]
HAZE_SCALE, SKY_SCALE = .42, .32
GLOW_X = (250, 470)  # px: left of these the sun's glow in the sky and the haze turns to the cool sky and mist
HAZE_SOFT = 70   # px: the haze's top fades into the sky over this
FAR_HAZE = 640   # row of the haze's top on the far left


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
    up = np.asarray(Image.fromarray(np.uint8(np.clip(small, 0, 255)).squeeze()).resize((W2, H2), Image.BILINEAR), np.float64)
    up = up.reshape(H2, W2, -1)[:h, :wd]
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


def clone_fill(img, known, need, offsets):
    """Fills img where need is set with its own texture copied from where known is set, at the first of offsets
    ((dx, dy) px: the source is (x + dx, y + dy)) that lands on a known pixel: the mountain goes on as more of itself
    (a slope copied along the slope, rock from above), not a smear or a mirror. Returns (img, filled)."""
    H, W = known.shape
    out, done = img.copy(), np.zeros_like(known)
    ys, xs = np.nonzero(need)
    for dx, dy in offsets:
        todo = ~done[ys, xs]
        if not todo.any():
            break
        y, x = ys[todo], xs[todo]
        sy, sx = y + dy, x + dx
        ok = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
        ok[ok] = known[sy[ok], sx[ok]]
        out[y[ok], x[ok]] = img[sy[ok], sx[ok]]
        done[y[ok], x[ok]] = True
    return out, done


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


def wrap_widen(a, top):
    """The sky widened by PAD_X of the painting's width on both sides with its far edge (crossfaded over SEAM px), plus
    `top` empty rows."""
    px = round(W0 * PAD_X)
    left, right = a[:, -px - SEAM:].copy(), a[:, :px + SEAM].copy()
    w = np.linspace(0, 1, SEAM)[None, :, None]
    mid = a.copy()
    mid[:, :SEAM] = left[:, -SEAM:] * (1 - w) + a[:, :SEAM] * w
    mid[:, -SEAM:] = a[:, -SEAM:] * (1 - w) + right[:, :SEAM] * w
    a = np.concatenate([left[:, :px], mid, right[:, SEAM:SEAM + px]], 1)
    return np.concatenate([np.zeros((top,) + a.shape[1:]), a], 0)


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


def main(preview):
    os.makedirs(OUT, exist_ok=True)
    rgb = np.asarray(Image.open(SRC).convert('RGB'), np.float64)
    assert rgb.shape[:2] == (H0, W0), rgb.shape
    ys, xs = np.mgrid[0:H0, 0:W0]
    sky_y = line_y(SKY_EXT, np.arange(W0))
    S = np.clip(ys - sky_y[None, :] + .75, 0, 1.5) / 1.5                 # below the sky line, 1.5 px soft edge
    Wp = W0 + 2 * EXT                                                    # the canvas past both edges
    SP = np.clip(np.arange(H0)[:, None] - line_y(SKY_EXT, np.arange(Wp) - EXT)[None, :] + .75, 0, 1.5) / 1.5
    leaves = painted_leaves(rgb)
    unknown = poly_alpha(CUT, W0, H0) > .01
    unknown |= leaves | (ys >= FLOOR_Y)

    # Each plane's alpha (on the wide canvas: the two mountains go on past the edges), and what shows of it in the
    # painting (its weight at the start camera).
    cover = np.zeros((H0, W0))
    for P in PLANES:
        if P.get('top'):     # its own top line instead of the sky line
            tl = line_y(P['top'], np.arange(Wp) - EXT)
            P['aP'] = poly_alpha(P['polys'], Wp, H0, -EXT) * (np.clip(np.arange(H0)[:, None] - tl[None, :] + .75, 0, 1.5) / 1.5)
        else:
            P['aP'] = poly_alpha(P['polys'], Wp, H0, -EXT) * SP
        if P.get('bumps'):   # its left edge between these rows: tree crowns, not a polygon line
            lo, hi, amp = P['bumps']
            rws = np.arange(lo, min(hi, H0))
            aw = P['aP'][rws] > .5
            left = np.where(aw.any(1), aw.argmax(1), Wp)
            b = amp * (np.abs(np.sin(rws / 15.)) * .65 + np.abs(np.sin(rws / 6.3 + .7)) * .35)
            P['aP'][rws] *= np.clip(np.arange(Wp)[None, :] - (left + b)[:, None] + 1, 0, 1)
        a = P['aP'][:, EXT:EXT + W0]
        P['cov'], P['a'], P['w'] = cover.copy(), a, a * (1 - cover)
        cover = cover + P['w']
    # the haze: its top soft (mist rising into the sky); on the far left low, the far mountains' feet in the mist
    wl = glow_weight(xs)
    top = line_y(HAZE_TOP, np.arange(W0))
    top = top * (1 - wl[0]) + FAR_HAZE * wl[0]
    hz = np.clip((ys - top[None, :]) / HAZE_SOFT + .5, 0, 1) * S
    rest = (S > .99) & (1 - cover > .01)
    rest &= np.asarray(Image.fromarray(np.uint8(rest) * 255).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(13)), bool)
    rest &= (wl < .5) & (ys >= top[None, :] - 10)
    hz = np.maximum(hz, blur(np.asarray(Image.fromarray(np.uint8(rest) * 255).filter(ImageFilter.MaxFilter(7)), np.float64) / 255, 1) * S)
    hz_w = hz * (1 - cover)
    print('painting covered by the planes and the haze: %.4f (sky %.4f)' % ((cover + hz_w).mean(), (1 - cover - hz_w).mean()))

    islands = []
    # The mountains and the waterfall: the painting where they show; where the painting had the props (the column
    # on L, mirrored from L; the lantern, the grass and the leaves in the mist, smooth) and where a nearer one hides
    # them (the waterfall behind the mountains: water, mirrored), filled from themselves; past the painting's edges,
    # each mirrored at the edge.
    for P in PLANES:
        nz = np.nonzero(P['aP'] > .003)
        y0, y1 = max(0, nz[0].min() - 3), min(H0, nz[0].max() + 4)
        X0, X1 = max(0, nz[1].min() - 3), min(Wp, nz[1].max() + 4)          # on the wide canvas
        x0, x1 = max(X0 - EXT, 0), min(X1 - EXT, W0)                         # inside the painting
        known = (P['w'][y0:y1, x0:x1] > .02) & (P['a'][y0:y1, x0:x1] > .97) & (P['cov'][y0:y1, x0:x1] < .1) & \
            ~unknown[y0:y1, x0:x1]
        col = mirror_fill(rgb[y0:y1, x0:x1], known)
        cutr = unknown[y0:y1, x0:x1] & (np.arange(y0, y1)[:, None] < FLOOR_Y)
        if P.get('smooth') and cutr.any():
            sm = push_pull(rgb[y0:y1, x0:x1], known)
            sm = np.asarray(Image.fromarray(np.uint8(np.clip(sm, 0, 255))).filter(ImageFilter.GaussianBlur(4)), np.float64)
            col = np.where(cutr[..., None], sm, col)
        if P.get('clone'):   # copied from its own painting (its small holes, already filled, count as painted)
            vis = (P['w'][y0:y1, x0:x1] > .02) & (P['cov'][y0:y1, x0:x1] < .1) & (P['a'][y0:y1, x0:x1] > .97)
            if P.get('fringe'):   # not the painted shadow along the mountains' edges: copied water there too
                k = 2 * P['fringe'] + 1
                nearc = np.asarray(Image.fromarray(np.uint8(np.clip(P['cov'][y0:y1, x0:x1], 0, 1) * 255))
                                   .filter(ImageFilter.MaxFilter(k)), np.float64) / 255
                vis &= nearc < .1
                known = known & (nearc < .1)
            src = known | (vis & cutr)
            if P.get('noclone'):
                src &= ~(poly_alpha([P['noclone']], x1 - x0, y1 - y0, x0, y0) > .01)
            colx, rowy = np.arange(x0, x1)[None, :], np.arange(y0, y1)[:, None]
            # near the painted part the copy fades in over the mirrored edge (no step in shade where they meet)
            vy, vx = nearest_known(vis)
            dist = np.hypot((vy - rowy).astype(np.float64), (vx - colx + x0 - x0).astype(np.float64) - 0)
            dist = np.hypot((vy - np.arange(y1 - y0)[:, None]).astype(np.float64), (vx - np.arange(x1 - x0)[None, :]).astype(np.float64))
            wfade = np.clip(dist / 40., 0, 1)[..., None]
            for offs, xa, xb, ya, yb in P['clone']:
                need = ~vis & (P['aP'][y0:y1, EXT + x0:EXT + x1] > .003) & (colx >= xa) & (colx < xb) & \
                    (rowy >= ya) & (rowy < yb)
                srcr = src & (rowy >= ya) & (rowy < yb)        # (each band from its own rows: bank from bank, water from water)
                cl, got = clone_fill(col, srcr, need, offs)
                cl = np.asarray(Image.fromarray(np.uint8(np.clip(cl, 0, 255))).filter(ImageFilter.GaussianBlur(1.2)), np.float64)
                col = np.where(got[..., None], col * (1 - wfade) + cl * wfade, col)
        left, right = EXT + x0 - X0, X1 - (EXT + x1)
        if left > 0:
            col = np.concatenate([col[:, left:0:-1], col], 1)
        if right > 0:
            col = np.concatenate([col, col[:, -2:-right - 2:-1]], 1)
        al = P['aP'][y0:y1, X0:X1]
        water = None
        if P.get('water'):
            foam = np.array([1 if y < FOAM_Y else max(FOAM_MIN, 1 - (y - FOAM_Y) / FOAM_H * .6) for y in range(y0, y1)])
            water = blur(poly_alpha([WATER] + WATER_HIDDEN, X1 - X0, y1 - y0, X0 - EXT, y0) * foam[:, None], 5)
        islands.append({'name': P['name'], 'box': [X0 - EXT, y0, X1 - EXT, y1], 'rgb': col, 'm': al, 'water': water,
                        'scale': P['scale']})

    # The mist at the mountains' feet, in front of all of them: the painting's own, its waterfall foam taken out.
    b0, b1 = BASE_ROWS
    band = rgb[b0:b1].copy()
    bk = ~(unknown[b0:b1] | (poly_alpha([FOAM_CUT], W0, b1 - b0, 0, b0) > .01))
    band = push_pull(band, bk)
    band = np.where(bk[..., None], band, np.asarray(Image.fromarray(np.uint8(np.clip(band, 0, 255))).filter(ImageFilter.GaussianBlur(6)), np.float64))
    mrow = np.asarray(Image.fromarray(np.uint8(band[FLOOR_Y - b0 - 30:FLOOR_Y - b0].mean(0)[None])).filter(ImageFilter.BoxBlur(60)), np.float64)[0]
    band[FLOOR_Y - b0:] = mrow[None]
    k = np.linspace(0, 1, 40)[:, None, None]                                  # into the solid mist above the floor line
    band[FLOOR_Y - b0 - 40:FLOOR_Y - b0] = band[FLOOR_Y - b0 - 40:FLOOR_Y - b0] * (1 - k) + mrow[None] * k
    band = np.concatenate([band, np.repeat(band[-1:], BOTTOM + 40 - b1, 0)], 0)
    band = np.pad(band, ((0, 0), (BASE_PAD, BASE_PAD), (0, 0)), mode='reflect')
    bx = np.arange(band.shape[1]) - BASE_PAD
    under = np.clip(1 - np.abs(bx - 945) / 330, 0, 1)                         # under the waterfall the tops sit lower
    tops = BASE_TOP + (BASE_TOP_FALLS - BASE_TOP) * np.minimum(1, under * 1.6) + \
        9 * np.sin(bx / 31.) + 6 * np.sin(bx / 13.7 + 1.1) + 4 * np.sin(bx / 6.1 + 2.3)
    f = np.clip((np.arange(b0, BOTTOM + 40)[:, None] - tops[None, :]) / BASE_RAMP, 0, 1)
    islands.append({'name': 'base', 'box': [-BASE_PAD, b0, W0 + BASE_PAD, BOTTOM + 40], 'rgb': band,
                    'm': f * f * (3 - 2 * f), 'water': None, 'scale': .5})

    # Far mountains past the two mountains' outer slopes: pale shapes in the haze, solid.
    fx0, fy0, fx1, fy1 = FAR_BOX
    fxs, fys = np.arange(fx0, fx1), np.arange(fy0, fy1)
    ridge = np.min([py + FAR_SLOPE * np.abs(fxs - px) for px, py in FAR_PEAKS], 0)
    ridge += 6 * np.sin(fxs / 17.) + 4 * np.sin(fxs / 7.3 + .8) + 3 * np.sin(fxs / 3.1 + 2)   # a ragged forest edge
    fa = np.clip(fys[:, None] - ridge[None, :] + 1, 0, 1)
    rock = rgb[300:520, 1280:1600].reshape(-1, 3).mean(0)                     # the mountains' own colour
    horizon = rgb[150:170, 900:1100].reshape(-1, 3).mean(0)
    mist = rgb[600:700, 560:680].reshape(-1, 3).mean(0)
    depth = np.clip((fys[:, None] - ridge[None, :]) / 260, 0, 1)[..., None]  # from its ridge down into the mist
    mix = FAR_HAZE_MIX[0] + (FAR_HAZE_MIX[1] - FAR_HAZE_MIX[0]) * depth
    rnd = np.random.RandomState(3)
    tex = np.asarray(Image.fromarray(np.uint8(rnd.rand(fy1 - fy0, fx1 - fx0) * 255)).filter(ImageFilter.GaussianBlur(5)), np.float64) / 255
    shade = (.86 + .28 * tex)[..., None] * (1 - .12 * np.clip((fxs[None, :] % 160 - 80) / 80., -1, 1)[..., None] * 0)
    fc = (rock * shade) * (1 - mix) + (horizon * (1 - depth) + mist * depth) * mix
    islands.append({'name': 'far', 'box': [fx0, fy0, fx1, fy1], 'rgb': fc, 'm': fa, 'water': None, 'scale': .4})

    # Haze: the painting where it shows, smoothly filled elsewhere; below the painted floor the mist goes on down
    # (the mean of rows 690-720 per column, paler further down); past both edges it is mirrored.
    # (its colours only where nothing nearer is over it: under the mountains' soft feet the painting has their
    # ghosts, which would stay behind in the mist when they move)
    near = np.asarray(Image.fromarray(np.uint8(np.clip(cover, 0, 1) * 255)).filter(ImageFilter.MaxFilter(17)), np.float64) / 255
    known = (hz_w > .02) & (near < .1) & ~unknown      # (and not right at a plane's edge: its fringe is dark forest)
    # (where it shows only through gaps, the painting itself, much blurred: the mountains' blues, not a flat grey)
    rgb_b = np.asarray(Image.fromarray(np.uint8(rgb)).filter(ImageFilter.GaussianBlur(40)), np.float64)
    haze = push_pull(np.where(known[..., None], rgb, rgb_b), known | (S > .99))
    haze = np.where(known[..., None], rgb, np.asarray(Image.fromarray(np.uint8(np.clip(haze, 0, 255))).filter(ImageFilter.GaussianBlur(2)), np.float64))
    # the sun's glow on the far left (a beam of light down through the mist): the right side's mist, mirrored
    wx = glow_weight(xs)[..., None]
    far = np.asarray(Image.fromarray(np.uint8(np.clip(haze[:, ::-1], 0, 255))).filter(ImageFilter.GaussianBlur(7)), np.float64)
    haze = haze * (1 - wx) + far * wx           # (softened: far mist has no detail, and no stray dark fringe)
    # behind the column and its banner (the far left, seen when the camera goes left): the hill, the trees and the
    # mist just right of it go on, sharp (not the smooth fill)
    # (from anything painted there, cliff and trees included: so far back they read as one more hill)
    # (the left mountain itself, smaller and hazier, as farther mountains: see the copies after widening)
    bot, px = round(H0 * PAD_BOTTOM), round(W0 * PAD_X)
    mist_row = np.asarray(Image.fromarray(np.uint8(haze[690:720].mean(0)[None])).filter(ImageFilter.BoxBlur(40)), np.float64)[0]
    BLEND = 60
    w = np.linspace(0, 1, BLEND)[:, None, None]
    haze[FLOOR_Y:] = mist_row[None]
    haze[FLOOR_Y - BLEND:FLOOR_Y] = haze[FLOOR_Y - BLEND:FLOOR_Y] * (1 - w) + mist_row[None] * w
    pale = np.array([235., 245., 252.])
    k = np.linspace(0, 1, bot)[:, None, None]
    haze = np.concatenate([haze, mist_row[None] * (1 - .6 * k) + pale * .6 * k], 0)
    hal = np.concatenate([np.where(ys >= FLOOR_Y - 2, 1., hz), np.ones((bot, W0))], 0)
    # past both edges it is mirrored (soft haze: nothing sharp to repeat)
    haze = np.pad(haze, ((0, 0), (px, px), (0, 0)), mode='reflect')
    hal = np.pad(hal, ((0, 0), (px, px)), mode='reflect')
    islands.append({'name': 'haze', 'box': [-px, 0, W0 + px, H0 + bot], 'rgb': haze, 'm': hal, 'water': None, 'scale': HAZE_SCALE})

    # Sky: the rest filled in from the sky; wrapped round past both edges; on top a deeper blue.
    is_sky = (ys < sky_y[None, :] - 3) & ~unknown
    sky = push_pull(rgb, is_sky)
    sky = np.where(is_sky[..., None], rgb, np.asarray(Image.fromarray(np.uint8(np.clip(sky, 0, 255))).filter(ImageFilter.GaussianBlur(2)), np.float64))
    # the sun's glow on the far left: the right side's sky and clouds, mirrored
    wx = glow_weight(xs)[..., None]
    sky = sky * (1 - wx) + sky[:, ::-1] * wx
    top = round(H0 * PAD_TOP)
    sk = wrap_widen(sky, top)
    first = np.asarray(Image.fromarray(np.uint8(sk[top:top + 12].mean(0)[None])).filter(ImageFilter.BoxBlur(150)), np.float64)[0]
    deep = np.array([38., 104., 214.])
    k = np.linspace(1, 0, top)[:, None, None]
    sk[:top] = first[None] * (1 - k) + deep * k
    # The haze is opaque below its own top: the sky is never seen lower than that (plus a margin for the parallax),
    # so the sky plane stops there and the GPU does not draw it under everything.
    sky_bottom = BOTTOM
    sk = sk[:top + sky_bottom]
    islands.append({'name': 'sky', 'box': [-px, -top, W0 + px, sky_bottom], 'rgb': sk, 'm': np.ones(sk.shape[:2]), 'water': None, 'scale': SKY_SCALE})

    # Atlas.
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

    meta = {'atlas': [ATLAS_W, int(AH)], 'planes': [{'name': it['name'], 'box': [int(v) for v in it['box']],
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
