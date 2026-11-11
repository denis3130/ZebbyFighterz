#!/usr/bin/env python3
"""The near 3D pieces' paint, taken from the painted arena (docs/ref/sfondo-cascata.png) (needs Pillow, numpy).

usage: python3 tools/make_props.py [--preview OUTDIR]

  assets/arena/cascata_floor.jpg   the painted floor seen from above: every texel is the painting's colour where the
                                   start camera sees that point of the floor (so in the game, at the start camera, the
                                   floor looks exactly like the painting, and it stays on the floor when the camera
                                   moves); where the painting does not show the floor (past the screen, under the
                                   column, the lantern and the grass) it is filled from the painted slabs, mirrored
  assets/arena/cascata_floor.json  the texture's world rect (x0, z0, x1, z1, metres) and the floor's back edge z
  assets/arena/cascata_props.jpg   the painted props side by side: the column (under its banner rebuilt from its
                                   own stone), the banner, the lantern, the rock, grass and ivy tufts
  assets/arena/cascata_props_a.png their alpha (the painted outlines: the lantern's windows see through)
  assets/arena/cascata_props.json  for each: its box in the painting (px, y down) and its rect in the atlas (uv, v up);
                                   the banner's left and right edges (painting px, top to bottom)
The camera and placement numbers below must match CFG.cam and CFG.arenas.cascata.ref (src/a0_cfg.js); the test
'floor paint matches the painting' checks it. build.py embeds every file under assets/ in the page.
"""
import argparse
import json
import math
import os
import sys
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_layers as ML  # noqa: E402  (painting size, polygons, mirror_fill, poly_alpha)

ROOT = ML.ROOT
OUT = ML.OUT
W0, H0 = ML.W0, ML.H0
# CFG.cam and CFG.arenas.cascata.ref
FOV, DIST0, FOOT_SCREEN = 30, 6.5, .86
REF_W, REF_H, FOOT_ROW, COVER = 844, 390, .83, 1.1
# The painted floor: its top runs from FLOOR_TOP (its back edge) to FLOOR_BOTTOM (below that the painting shows its
# front face); the floor texture covers x X0..X1, z Z0..Z1 (metres) at TEX px.
FLOOR_TOP, FLOOR_BOTTOM = 725, 888
X0, X1, Z1 = -8., 8., 4.2
TEX = (4096, 512)
QUALITY = 86
RECT, BLEND = (-2.75, 2.75, -1.85, 1.55), 12   # metres x0, x1, z0, z1 all painted; texels of the fade
# Not floor, though below its back edge: the column's foot with its ivy, bottom left.
FLOOR_CUT = [[(0, 712), (135, 712), (118, 760), (60, 790), (0, 800)]]


def ref_place():
    """arRefPlace in src/d_arena.js: the flat backdrop's placement on the ref screen at the start camera."""
    gy = FOOT_SCREEN * REF_H
    s = max(max(REF_W / W0, REF_H / H0) * COVER, REF_W / W0, gy / (FOOT_ROW * H0), (REF_H - gy) / ((1 - FOOT_ROW) * H0))
    su, sv = REF_W / (W0 * s), REF_H / (H0 * s)
    return .5 - su / 2, 1 - FOOT_ROW - (REF_H - gy) / (H0 * s), su, sv


def to_painting(x, y, z):
    """World point(s) (metres) -> painting px (X, Y down), through the start camera on the ref screen."""
    px, py, su, sv = ref_place()
    t = math.tan(math.radians(FOV / 2)); asp = REF_W / REF_H
    cy = DIST0 * (FOOT_SCREEN - .5) * 2 * t
    L = DIST0 - z
    sx = (x / (L * t * asp) + 1) / 2
    sy = ((y - cy) / (L * t) + 1) / 2
    return (px + sx * su) * W0, (1 - (py + sy * sv)) * H0


def floor_back_z():
    """The z (metres) where the painting's floor ends: its row FLOOR_TOP at the start camera."""
    lo, hi = -10., 0.
    for _ in range(60):
        mid = (lo + hi) / 2
        _, Y = to_painting(0., 0., mid)
        lo, hi = (mid, hi) if Y < FLOOR_TOP else (lo, mid)
    return (lo + hi) / 2


def bilinear(img, X, Y):
    h, w = img.shape[:2]
    X = np.clip(X, 0, w - 1.001); Y = np.clip(Y, 0, h - 1.001)
    x0, y0 = np.floor(X).astype(int), np.floor(Y).astype(int)
    fx, fy = (X - x0)[..., None], (Y - y0)[..., None]
    a, b = img[y0, x0], img[y0, x0 + 1]
    c, d = img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def floor(rgb, unknown):
    zb = floor_back_z()
    W, H = TEX
    xs = X0 + (np.arange(W) + .5) / W * (X1 - X0)
    zs = Z1 + (np.arange(H) + .5) / H * (zb - Z1)            # row 0 = the front (z = Z1), last row = the back edge
    XX, ZZ = np.meshgrid(xs, zs)
    PX, PY = to_painting(XX, 0., ZZ)
    inside = (PX >= 0) & (PX < W0 - 1) & (PY >= FLOOR_TOP) & (PY < FLOOR_BOTTOM - 1)
    ok = inside.copy()
    ok[inside] = ~unknown[np.clip(PY[inside].astype(int), 0, H0 - 1), np.clip(PX[inside].astype(int), 0, W0 - 1)]
    col = np.zeros((H, W, 3))
    col[ok] = bilinear(rgb, PX[ok], PY[ok])
    print('floor: back edge z %.3f m, %.1f%% of the texture painted' % (zb, 100 * ok.mean()))
    # Past the painted part: the largest fully painted rectangle (RECT, metres) mirrored over and over (the warm left
    # goes on warm, the shaded right shaded); the painted part fades into it over BLEND texels.
    rx0, rx1, rz0, rz1 = RECT
    def mirror(v, a, b):
        w = b - a; k = np.mod(v - a, 2 * w)
        return a + np.where(k < w, k, 2 * w - k)
    MX, MZ = mirror(XX, rx0, rx1), mirror(ZZ, min(rz0, zb), rz1)
    ci = np.clip(np.round((MX - X0) / (X1 - X0) * W - .5).astype(int), 0, W - 1)
    ri = np.clip(np.round((MZ - Z1) / (zb - Z1) * H - .5).astype(int), 0, H - 1)
    rep = col[ri, ci]
    assert ok[ri, ci].mean() > .99, 'RECT is not all painted'
    soft = np.asarray(Image.fromarray(np.uint8(ok) * 255).filter(ImageFilter.MinFilter(2 * BLEND + 1))
                      .filter(ImageFilter.GaussianBlur(BLEND / 2)), np.float64)[..., None] / 255
    col = col * soft + rep * (1 - soft)
    p = os.path.join(OUT, 'cascata_floor.jpg')
    Image.fromarray(np.uint8(np.clip(col, 0, 255))).save(p, 'JPEG', quality=QUALITY, optimize=True)
    return p, {'rect': [X0, Z1, X1, round(zb, 4)], 'back': round(zb, 4)}


# The props in the painting (px). Their 3D shapes are built in src/d_arena.js and take these colours as seen from the
# start camera (each vertex painted with the painting's pixel there), cut by these outlines.
COLUMN = [(20, 45), (62, 40), (85, 55), (110, 72), (140, 88), (165, 100), (169, 140), (152, 160), (130, 166), (130, 700),
          (0, 712), (0, 560), (14, 520), (18, 152), (41, 145), (41, 57)]
POLE = [(45, 148), (60, 146), (200, 205), (199, 222), (185, 222), (45, 168)]
BANNER_L = [(95, 178), (99, 260), (104, 330), (113, 378), (133, 420), (158, 455), (186, 482), (205, 500)]
BANNER_R = [(186, 212), (191, 262), (201, 302), (216, 342), (241, 386), (269, 430), (296, 480), (324, 545)]
BANNER_BOX = (85, 165, 335, 552)
LANTERN = [(1572, 527), (1604, 527), (1606, 556), (1652, 572), (1660, 588), (1626, 596), (1626, 636), (1636, 640),
           (1636, 652), (1631, 654), (1633, 705), (1540, 705), (1542, 654), (1536, 650), (1537, 636), (1550, 634),
           (1550, 597), (1515, 592), (1517, 576), (1568, 556)]
ROCK = [(143, 627), (200, 627), (230, 648), (241, 700), (98, 706), (96, 674), (118, 650)]
TUFTS = {'grass_l': (236, 640, 362, 724), 'grass_m': (1488, 638, 1548, 724), 'grass_r': (1612, 630, 1672, 724),
         'ivy': (0, 590, 134, 724)}


def green(rgb):
    """Alpha of grass and ivy against the blue mist and sky: how much greener or yellower than blue."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return np.clip((np.maximum(g, r * .9) - b - 6) / 30, 0, 1)


def props(rgb):
    """Each prop's colours (edge colours spread outward: no background at its outline) and alpha, cropped."""
    out = {}
    def crop(box, a, fill_known=None):
        x0, y0, x1, y1 = box
        c, m = rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]
        k = (m > .6) if fill_known is None else fill_known[y0:y1, x0:x1]
        return ML.mirror_fill(c, k), m
    # the column: under the banner and the pole, its own stone mirrored in
    col_a = ML.poly_alpha([COLUMN], W0, H0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = (r > 110) & (r > g * 1.3) & (r > b * 1.3)
    cover = (np.asarray(Image.fromarray(np.uint8(red) * 255).filter(ImageFilter.MaxFilter(5)), np.float64) > 0) | \
        (ML.poly_alpha([POLE], W0, H0) > .1)
    out['column'] = crop((0, 30, 175, 720), col_a, (col_a > .6) & ~cover)
    # the banner: its red cloth (its tears see through), in the box around it
    ban = ML.poly_alpha([BANNER_L + BANNER_R[::-1]], W0, H0) > .01
    ban_a = np.where(ban, np.clip((r - np.maximum(g, b) * 1.15 - 10) / 30, 0, 1), 0)
    ban_a = np.asarray(Image.fromarray(np.uint8(ban_a * 255)).filter(ImageFilter.GaussianBlur(.7)), np.float64) / 255
    out['banner'] = crop(BANNER_BOX, ban_a)
    lan_a = ML.poly_alpha([LANTERN], W0, H0)
    win = (b > r + 25) & (b > 150)                                    # the windows: the sky through them
    lan_a = lan_a * (1 - win)
    out['lantern'] = crop((1505, 520, 1668, 712), lan_a)
    out['rock'] = crop((90, 620, 248, 712), ML.poly_alpha([ROCK], W0, H0))
    out['pole'] = crop((40, 140, 205, 228), ML.poly_alpha([POLE], W0, H0))
    gr = green(rgb)
    for k, box in TUFTS.items():
        c, m = crop(box, gr)
        w = m.shape[1]   # the tufts fade out at their left and right ends (a hedge of them has no straight cut)
        fade = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w * .22), 0, 1)
        out[k] = (c, m * (fade * fade * (3 - 2 * fade))[None, :])
    return out


def pack_props(items):
    order = sorted(items, key=lambda k: -items[k][0].shape[0])
    W, x, y, shelf, at = 1024, 0, 0, 0, {}
    for k in order:
        h, w = items[k][0].shape[:2]
        if x + w > W:
            x, y, shelf = 0, y + shelf + 4, 0
        at[k] = (x, y); x += w + 4; shelf = max(shelf, h)
    H = (y + shelf + 3) // 4 * 4
    col, alp = np.zeros((H, W, 3)), np.zeros((H, W))
    uv = {}
    for k, (c, a) in items.items():
        (x, y), (h, w) = at[k], c.shape[:2]
        col[y:y + h, x:x + w] = c; alp[y:y + h, x:x + w] = a
        uv[k] = [round(x / W, 6), round(1 - (y + h) / H, 6), round((x + w) / W, 6), round(1 - y / H, 6)]
    return col, alp, uv


def main(preview):
    rgb = np.asarray(Image.open(ML.SRC).convert('RGB'), np.float64)
    unknown = ML.poly_alpha(ML.CUT + FLOOR_CUT, W0, H0) > .01
    pf, meta = floor(rgb, unknown)
    with open(os.path.join(OUT, 'cascata_floor.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print('%s %.0f KB' % (os.path.relpath(pf, ROOT), os.path.getsize(pf) / 1024), meta)
    items = props(rgb)
    col, alp, uv = pack_props(items)
    pc, pa = os.path.join(OUT, 'cascata_props.jpg'), os.path.join(OUT, 'cascata_props_a.png')
    Image.fromarray(np.uint8(np.clip(col, 0, 255))).save(pc, 'JPEG', quality=QUALITY, optimize=True)
    Image.fromarray(np.uint8(np.clip(alp * 255, 0, 255))).save(pa, 'PNG', optimize=True)
    boxes = {'column': (0, 30, 175, 720), 'banner': BANNER_BOX, 'lantern': (1505, 520, 1668, 712), 'rock': (90, 620, 248, 712),
             'pole': (40, 140, 205, 228)}
    boxes.update(TUFTS)
    pm = {k: {'box': list(boxes[k]), 'uv': uv[k]} for k in items}
    pm['banner_edges'] = {'left': BANNER_L, 'right': BANNER_R}
    pm['pole_ends'] = [[52, 156], [195, 213]]
    with open(os.path.join(OUT, 'cascata_props.json'), 'w') as f:
        json.dump(pm, f, indent=1)
    print('props: %s %.0f KB + %.0f KB alpha, %dx%d' % (os.path.relpath(pc, ROOT), os.path.getsize(pc) / 1024,
                                                      os.path.getsize(pa) / 1024, col.shape[1], col.shape[0]))
    if preview:
        os.makedirs(preview, exist_ok=True)
        Image.open(pf).resize((2048, 256)).save(os.path.join(preview, 'floor.png'))
        a = alp[..., None]
        Image.fromarray(np.uint8(col * a + np.array([255, 0, 255]) * (1 - a))).save(os.path.join(preview, 'props.png'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview')
    main(ap.parse_args().preview)
