#!/usr/bin/env python3
"""Cuts the painted arena (docs/ref/sfondo-cascata.png) into the far depth planes of the 3D arena, like an anime
multiplane camera (needs Pillow, numpy).

usage: python3 tools/make_layers.py [--preview OUTDIR]

  assets/arena/cascata_atlas.jpg    every plane's colours, packed side by side
  assets/arena/cascata_atlas_m.png  the same layout: red = the plane's alpha, green = where the water flows
  assets/arena/cascata_mist.png     a soft mist band (alpha in red), coloured in the shader
  assets/arena/cascata_layers.json  the planes (near to far): name, box (painting px: x0, y0, x1, y1, y down; may
                                    reach past the painting) and strips (f = the strip in the plane's uv, uv = in the
                                    atlas: u0, v0, u1, v1, v up), mist colour
The planes, nearest first (their depths are in CFG.arenas.cascata.layers): LF the dark forest low on the left, FL and
FR the near cliffs (the orange wall on the left, the sunlit trees on the right), UL and UR the high cliffs behind
them, falls (the waterfall with its crest, temple and wooded bank), haze (the far hazy hills and the mist; it fills
everything below the sky line that no plane covers, and goes on below the painted floor and past both edges), sky.
At the start camera they add up to the painting exactly: where a plane shows, it has the painting's colours. Where a
nearer plane hides it, each plane goes on (its polygon reaches in behind the nearer one) and is filled from itself,
mirrored across its edge (rock goes on as rock, water as water), so a camera move uncovers more of it, never a hole
or a copy of the nearer plane. The column with its banner, the lantern, the front grass, the painted floor and the
yellow leaves painted in the mist are 3D now (or gone): every plane fills them in. build.py embeds every file under
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

# The planes, nearest first, traced by hand on the painting (painting px). poly = where the plane is: what shows of
# it plus how far it goes on behind the nearer planes (never into what a farther plane shows). fade = soft edges
# where the plane dissolves into the mist: ('below', line, px) fades out over px above the line, ('left', x, px)
# fades in from x. scale = atlas pixels per painting pixel. pad = px it goes on past the painting's right edge
# (mirrored, fading out).
FL_CROWN = [(330, 347), (350, 340), (363, 330), (383, 317), (403, 303), (420, 300), (440, 300), (450, 287), (463, 270),
            (473, 263), (493, 250), (503, 243), (513, 232), (523, 220), (547, 213), (570, 210), (583, 200), (597, 192),
            (617, 190), (630, 200), (650, 213), (663, 232), (672, 254)]
FR_CROWN = [(1236, 410), (1241, 403), (1248, 392), (1258, 382), (1272, 372), (1286, 361), (1293, 347), (1307, 330),
            (1324, 326), (1345, 323), (1355, 311), (1369, 299), (1383, 295), (1397, 302), (1414, 316), (1428, 326),
            (1446, 333), (1463, 333), (1473, 319), (1494, 314), (1515, 306), (1533, 307), (1546, 316), (1560, 333),
            (1581, 344), (1600, 352)]
FR_FALLS_EDGE = [(1232, 441), (1194, 465), (1180, 493), (1166, 530), (1147, 558), (1124, 582), (1096, 605), (1058, 634),
                 (1030, 652)]
FR_MIST_EDGE = [(1030, 672), (1058, 668), (1100, 645), (1147, 626), (1194, 607), (1241, 584), (1312, 560), (1359, 551),
                (1406, 523), (1452, 504), (1546, 490), (1642, 443)]
LF_TOP = [(300, 470), (321, 452), (330, 427), (370, 432), (410, 432), (432, 430), (459, 434), (477, 445), (499, 463),
          (522, 472), (544, 490), (566, 494), (589, 512), (607, 530), (629, 538), (658, 552), (686, 567), (711, 586),
          (735, 620), (750, 660)]
LF_BOTTOM = [(290, 565), (330, 578), (400, 590), (480, 594), (560, 602), (640, 627), (700, 657), (752, 664)]
BOTTOM = 820   # px: every plane goes down solid to here, below the painted floor line: the terrace hides its base
PAD_SEAM = 70  # px: past the right edge a plane goes on with its own painting from further in, crossfaded over this
# Left of the left mountains, where the sun's glow was: the left mountains once more (as built here, hidden parts
# included), flipped, FAR_SCALE times their size, their right edge at FAR_RIGHT and their base at BOTTOM, a little
# paler (FAR_TINT of the horizon's blue): another mountain, further away, solid.
FAR_SRC, FAR_TINT, FAR_PAD = (196, 40, 650), .14, 520
FAR_SCALE, FAR_PEAK = .83, (120, 190)   # its size, and where its peak is (painting px)
FAR_SLOPE = .9   # px down per px out: its sides
FAR_HAZE = 640   # row of the haze's top on the far left
# Every mountain is one solid piece: its painted outline where it shows, and wherever it is hidden (behind a nearer
# plane, or below the painted floor) it goes on as itself (mirrored from its own painting), down to BOTTOM. No fades:
# no fog cutting the mountains. Only where two planes meet inside the painted mist at their feet the seam is soft.
PLANES = [
    {'name': 'LF', 'scale': .9, 'clone': [(230, 0), (460, 0), (230, -60), (460, -60)], 'nofringe': True,
     'poly': LF_TOP + [(752, 690), (748, BOTTOM), (20, BOTTOM), (40, 640), (95, 585), (150, 540), (205, 505),
                       (255, 486), (288, 474)],
     'bumps': [('top', 20, 292, 16)],
     'fade': [('right', [(752, 640), (752, 690), (748, BOTTOM)], 30, 640, 20)]},
    {'name': 'FL', 'scale': .9, 'clone': [(80, 0), (160, 0), (80, -60), (160, -120)], 'nofringe': True,
     'poly': FL_CROWN + [(672, 288), (677, 336), (679, 384), (677, 432), (672, 480),
                                                    (672, 520), (668, 560), (668, BOTTOM), (240, BOTTOM), (250, 560),
                                                    (262, 505), (272, 462), (284, 420), (296, 360), (318, 344)],
     'bumps': [('left', 360, BOTTOM, 14)]},
    {'name': 'FR', 'scale': .9, 'pad': 340,
     'poly': FR_CROWN + [(1625, 395), (1642, 443), (W0, 440), (W0, BOTTOM), (1000, BOTTOM), (1012, 720), (1030, 652)] +
             FR_FALLS_EDGE[::-1][1:],
     'fade': [('left', [(1030, 650), (1012, 720), (1000, BOTTOM)], 30, 650, 20)]},
    {'name': 'UL', 'scale': .9, 'clone': [(0, -110), (0, -220), (-60, -110), (-60, -220), (0, -330)], 'nofringe': True,
     # its hidden right side stays left of where the orange cliff's edge goes when the camera goes right: there the
     # water shows, never a strip of this cliff
     'poly': [(200, 30), (645, 30), (640, 143), (655, 200), (665, 232), (668, 250), (660, 280), (640, 310), (618, 340),
              (612, 400), (606, BOTTOM), (318, BOTTOM), (328, 400), (345, 355), (330, 347), (345, 330), (335, 300), (320, 277), (313, 247),
              (310, 217), (287, 207), (267, 197), (233, 187), (215, 157), (200, 150)]},
    {'name': 'UR', 'scale': .9, 'pad': 300, 'clone': [(0, -110), (0, -220), (60, -110), (0, -330)],
     'poly': [(1245, 30), (W0, 30), (W0, BOTTOM), (1245, BOTTOM), (1236, 410), (1235, 357), (1240, 300), (1244, 245),
              (1247, 215)]},
    {'name': 'falls', 'scale': 1., 'water': True,
     # the water goes on behind the cliffs (further than they ever slide), solid, down to BOTTOM
     'poly': [(500, 160), (640, 143), (640, 30), (1245, 30), (1245, 236), (1415, 242), (1400, 420), (1352, 441),
              (1314, 465), (1300, 493), (1286, 530), (1267, 558), (1244, 582), (1216, 605), (1178, 634), (1150, 652),
              (1120, BOTTOM), (550, BOTTOM), (552, 300), (545, 160)]},
]
# The haze plane's own top: its hills against the sky on the left, then low behind the nearer planes (it is only
# seen where they do not cover it, and when they move it is what shows behind them, rather than the sky).
HAZE_TOP = [(0, 172), (215, 157), (260, 178), (300, 205), (345, 240), (420, 300), (500, 350), (580, 410), (660, 470),
            (760, 500), (900, 510), (1050, 500), (1150, 485), (1250, 470), (1350, 440), (1450, 400), (1530, 370),
            (1580, 335), (1625, 300), (W0, 285)]   # (on the right, up behind the forest's misty foot)
HAZE_SCALE, SKY_SCALE = .42, .32
GLOW_X = (250, 470)  # px: left of these the sun's glow in the sky and the haze turns to the cool sky and mist
HAZE_SOFT = 70   # px: the haze's top fades into the sky over this


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
    sky_y = line_y(SKY, np.arange(W0))
    S = np.clip(ys - sky_y[None, :] + .75, 0, 1.5) / 1.5                 # below the sky line, 1.5 px soft edge
    leaves = painted_leaves(rgb)
    unknown = poly_alpha(CUT, W0, H0) > .01
    unknown |= leaves | (ys >= FLOOR_Y)

    # Each plane's alpha, and what shows of it (its weight in the painting at the start camera).
    cover = np.zeros((H0, W0))
    for P in PLANES:
        a = poly_alpha([P['poly']], W0, H0) * S
        for kind, where, px, *rng in P.get('fade', ()):
            if kind == 'below':          # fades out over px above the line (only right of rng[0], ramped over rng[1];
                                         # a negative ramp: only left of rng[0])
                f = np.clip((line_y(where, np.arange(W0))[None, :] - ys) / px, 0, 1)
                if rng:
                    k = np.clip((xs - rng[0]) / rng[1], 0, 1)
                    f = 1 - k * (1 - f)
                a *= f
            else:                        # fades in from a vertical (x) or slanted ([(x, y), ...]) line on its left
                xl = where if np.isscalar(where) else np.interp(ys, [p[1] for p in where], [p[0] for p in where])
                f = np.clip(((xs - xl) if kind == 'left' else (xl - xs)) / px, 0, 1)   # 'right': out towards it
                if rng:                  # only below row rng[0], ramped over rng[1]
                    k = np.clip((ys - rng[0]) / rng[1], 0, 1)
                    f = 1 - k * (1 - f)
                a *= f
        for kind, lo, hi, amp in P.get('bumps', ()):   # an invented edge: tree crowns, not a polygon line
            if kind == 'top':                          # the top edge of columns lo..hi
                cols = np.arange(lo, hi)
                top = np.where((a[:, cols] > .5).any(0), (a[:, cols] > .5).argmax(0), H0)
                b = amp * (np.abs(np.sin(cols / 13.)) * .7 + np.abs(np.sin(cols / 5.7 + 1.3)) * .3)
                a[:, cols] *= np.clip(ys[:, cols] - (top + b)[None, :] + 1, 0, 1)
            else:                                      # the left edge of rows lo..hi
                rws = np.arange(lo, hi)
                left = np.where((a[rws] > .5).any(1), (a[rws] > .5).argmax(1), W0)
                b = amp * (np.abs(np.sin(rws / 12.)) * .7 + np.abs(np.sin(rws / 5.1 + .7)) * .3)
                a[rws] *= np.clip(xs[rws] - (left + b)[:, None] + 1, 0, 1)
        P['cov'] = cover.copy()
        P['a'] = a
        P['w'] = a * (1 - cover)
        cover = cover + P['w']
    # its top is soft (mist rising into the sky), so when the planes in front move it never shows a line; on the
    # far left (the sun's glow, a beam of light) it is the right side's, mirrored
    wl = glow_weight(xs)
    top = line_y(HAZE_TOP, np.arange(W0))
    top = top * (1 - wl[0]) + FAR_HAZE * wl[0]      # (on the far left low: the far mountain's foot in the mist)
    hz = np.clip((ys - top[None, :]) / HAZE_SOFT + .5, 0, 1) * S
    rest = (S > .99) & (1 - cover > .01)       # shows, no plane above has it (not the sky line's soft edge: the sky's)
    # the thin slivers of it (gaps of a few px between two planes' outlines) go to the plane beside them: in the
    # haze they would float in the air as dark ticks when the planes move
    big = np.asarray(Image.fromarray(np.uint8(rest) * 255).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(13)), bool)
    sliver = rest & ~big
    if sliver.any():
        nearw = np.stack([blur(P['w'], 4) for P in PLANES])
        best = nearw.argmax(0)
        cov = np.zeros((H0, W0))
        for i, P in enumerate(PLANES):
            # (as opaque as the plane is around it: where its outline is soft the sliver is soft too, no lone dot)
            P['a'] = np.where(sliver & (best == i) & (nearw[i] > .02), np.maximum(P['a'], np.minimum(1, blur(P['a'], 4) * 1.6)), P['a'])
            P['cov'] = cov.copy()
            P['w'] = P['a'] * (1 - cov)
            cov = cov + P['w']
        cover = cov
        rest = (S > .99) & (1 - cover > .01)
    # what is left of it that is only a thin fringe along the planes' soft outlines stays out of the haze too (the
    # haze widens what it takes by a few px: a fringe would become a floating speck)
    rest &= np.asarray(Image.fromarray(np.uint8(rest) * 255).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(13)), bool)
    print('slivers given to the planes beside them: %d px' % sliver.sum())
    rest &= wl < .5                            # (not the glow: there the sky and the far mountains instead)
    rest &= ys >= top[None, :] - 10            # (nor above the haze's own top: a patch there would float in the air)
    hz = np.maximum(hz, blur(np.asarray(Image.fromarray(np.uint8(rest) * 255).filter(ImageFilter.MaxFilter(7)), np.float64) / 255, 1) * S)
    hz_w = hz * (1 - cover)
    print('painting covered by the planes and the haze: %.4f (sky %.4f)' % ((cover + hz_w).mean(), (1 - cover - hz_w).mean()))

    islands = []
    # Near planes: the painting where they show, mirrored across their edges where they are hidden.
    for P in PLANES:
        nz = np.nonzero(P['a'] > .003)
        y0, y1 = max(0, nz[0].min() - 3), min(H0, nz[0].max() + 4)
        x0, x1 = max(0, nz[1].min() - 3), min(W0, nz[1].max() + 4)
        # its colours come only from where it is fully itself (on its soft edges the painting mixes in what is
        # behind: that fringe would travel with the plane as a light or dark thread); the edges take them from inside
        # (and nothing nearer over it: under a nearer plane's soft edge the painting mixes that plane in, a ghost)
        known = (P['w'][y0:y1, x0:x1] > .02) & (P['a'][y0:y1, x0:x1] > .97) & (P['cov'][y0:y1, x0:x1] < .1) & \
            ~unknown[y0:y1, x0:x1]
        if P.get('nofringe'):   # not the halo next to the column (its light and the glow): taken from further in
            known &= ~(np.asarray(Image.fromarray(np.uint8(poly_alpha([CUT[0]], x1 - x0, y1 - y0, x0, y0) > .3) * 255)
                                  .filter(ImageFilter.MaxFilter(41)), np.float64) > 0)
        col = mirror_fill(rgb[y0:y1, x0:x1], known)
        cutr = unknown[y0:y1, x0:x1] & (np.arange(y0, y1)[:, None] < FLOOR_Y)
        if P.get('clone'):   # its hidden parts: more of itself, copied (rock as rock, forest along its slope)
            need = (P['a'][y0:y1, x0:x1] > .003) & ~known
            cl, got = clone_fill(rgb[y0:y1, x0:x1], known, need, P['clone'])
            col = np.where(got[..., None], cl, col)
            cutr &= ~got
        # where the painting had the props that are 3D now (lantern, grass) or the painted leaves, in the mist: the
        # mist goes on, smooth
        if cutr.any():
            sm = push_pull(rgb[y0:y1, x0:x1], known)
            sm = np.asarray(Image.fromarray(np.uint8(np.clip(sm, 0, 255))).filter(ImageFilter.GaussianBlur(4)), np.float64)
            col = np.where(cutr[..., None], sm, col)
        al = P['a'][y0:y1, x0:x1]
        water = None
        if P.get('water'):
            foam = np.array([1 if y < FOAM_Y else max(FOAM_MIN, 1 - (y - FOAM_Y) / FOAM_H * .6) for y in range(y0, y1)])
            water = blur(poly_alpha([WATER] + WATER_HIDDEN, x1 - x0, y1 - y0, x0, y0) * foam[:, None], 5)
        if P.get('pad'):   # past the right edge: more of itself, solid: its own painting from further in (a mirror
            pad = P['pad']  # only where it starts, crossfaded, so no mirrored shapes)
            assert col.shape[1] >= pad + 2
            w = np.clip(np.arange(pad) / PAD_SEAM, 0, 1)
            b0 = max(0, col.shape[1] - 2 * pad)
            def ext(a):
                mir, blk = a[:, -2:-pad - 2:-1], a[:, b0:b0 + pad]
                ww = w.reshape((1, pad) + (1,) * (a.ndim - 2))
                return mir * (1 - ww) + blk * ww
            col = np.concatenate([col, ext(col)], 1)
            al = np.concatenate([al, ext(al)], 1)
            x1 += pad
        islands.append({'name': P['name'], 'box': [x0, y0, x1, y1], 'rgb': col, 'm': al, 'water': water, 'scale': P['scale']})

    # The far mountain on the left: the left mountains as built (LF over FL over UL, hidden parts included), flipped.
    fx0, fy0, fx1 = FAR_SRC
    can, ca = np.zeros((BOTTOM - fy0, fx1 - fx0, 3)), np.zeros((BOTTOM - fy0, fx1 - fx0))
    for name in ('UL', 'FL', 'LF'):
        it = next(i for i in islands if i['name'] == name)
        bx0, by0, bx1, by1 = it['box']
        ox0, oy0, ox1, oy1 = max(bx0, fx0), max(by0, fy0), min(bx1, fx1), min(by1, BOTTOM)
        if ox1 <= ox0 or oy1 <= oy0:
            continue
        m = it['m'][oy0 - by0:oy1 - by0, ox0 - bx0:ox1 - bx0]
        sl = (slice(oy0 - fy0, oy1 - fy0), slice(ox0 - fx0, ox1 - fx0))
        can[sl] = can[sl] * (1 - m[..., None]) + it['rgb'][oy0 - by0:oy1 - by0, ox0 - bx0:ox1 - bx0] * m[..., None]
        ca[sl] = ca[sl] + (1 - ca[sl]) * m
    first = np.where((ca > .5).any(0), (ca > .5).argmax(0), ca.shape[0])   # its outline: the first solid row per column
    # widened on both sides with more of itself, then its sides slope down to its foot (a mountain, not a block)
    known_c = ca > .97
    hh, ww = ca.shape
    can = np.concatenate([np.zeros((hh, FAR_PAD, 3)), can, np.zeros((hh, FAR_PAD, 3))], 1)
    kn = np.concatenate([np.zeros((hh, FAR_PAD), bool), known_c, np.zeros((hh, FAR_PAD), bool)], 1)
    side = np.zeros(kn.shape, bool); side[:, :FAR_PAD] = True; side[:, -FAR_PAD:] = True
    for sgn, part in ((1, np.s_[:, :FAR_PAD]), (-1, np.s_[:, -FAR_PAD:])):
        need = np.zeros(kn.shape, bool); need[part] = True
        cl, got = clone_fill(can, kn, need, [(sgn * d, 0) for d in (FAR_PAD, FAR_PAD // 2, 3 * FAR_PAD // 2)])
        can = np.where(got[..., None], cl, can)
    first = np.concatenate([np.full(FAR_PAD, hh), first, np.full(FAR_PAD, hh)])
    ca = np.concatenate([np.zeros((hh, FAR_PAD)), ca, np.zeros((hh, FAR_PAD))], 1)
    # its outline without narrow notches (where its source had gaps between planes): the upper envelope
    env = first.astype(np.float64)
    for _ in range(2):
        env = np.minimum(env, np.array([env[max(0, i - 40):i + 41].min() + 0 for i in range(len(env))]) + 30)
    first = np.minimum(first, env).astype(int)
    cx, peak = np.argmin(first), first.min()
    xs_ = np.arange(ca.shape[1])
    ridge = np.maximum(np.where(side[0], 0, first), peak + FAR_SLOPE * np.abs(xs_ - cx) - FAR_SLOPE * 60)
    ridge = np.convolve(np.pad(ridge, 15, mode='edge'), np.ones(31) / 31, mode='same')[15:-15]
    ridge = ridge + np.where(side[0] | (ridge > first + 2), 7 * np.sin(xs_ / 23.) + 4 * np.sin(xs_ / 9.7 + 1), 0)   # uneven
    rows = np.arange(ca.shape[0])[:, None]
    solid = rows >= ridge[None, :]
    can = mirror_fill(can, ((ca > .97) | side) & solid & (can.sum(2) > 0))
    ca = np.clip(rows - ridge[None, :] + 1, 0, 1)
    can, ca = can[:, ::-1], ca[:, ::-1]
    horizon = rgb[150:170, 900:1100].reshape(-1, 3).mean(0)
    can = can * (1 - FAR_TINT) + horizon * FAR_TINT
    k, (pkx, pky) = FAR_SCALE, FAR_PEAK
    cpx = can.shape[1] - 1 - cx                          # the peak's column after the flip
    w, h = round(can.shape[1] * k), round(can.shape[0] * k)
    # placed so its peak is at FAR_PEAK; its base goes on down to BOTTOM or below
    bx0 = round(pkx - cpx * k); by0 = round(pky - peak * k)
    fc, fa = resized(can, w, h), resized(ca, w, h)
    if by0 + h < BOTTOM:
        ext = BOTTOM - by0 - h
        fc = np.concatenate([fc, np.repeat(fc[-1:], ext, 0)], 0); fa = np.concatenate([fa, np.repeat(fa[-1:], ext, 0)], 0)
        h += ext
    # further from the peak, hazier (aerial perspective: its sides fade towards the horizon's blue)
    d = np.clip(np.abs(np.arange(w) - cpx * k) / (w / 2), 0, 1)[None, :, None]
    fc = fc * (1 - .35 * d) + horizon * .35 * d
    islands.append({'name': 'far', 'box': [bx0, by0, bx0 + w, by0 + h], 'rgb': fc, 'm': fa, 'water': None, 'scale': .6})

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
