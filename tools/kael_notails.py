#!/usr/bin/env python3
"""Kael's bust sheet without the sash's two hanging tails, for Meshy (11/11/2026, Denis: "creami il modello in 3d su
meshy ... se ti conviene creare quella fascia viola tu senza meshy dimmelo, che voglio che si animi come quelle arancioni
di ren"; then "togli meglio" and "annerisci leggermente la tuta"). The tails become ribbons in code, as Ren's; the knot
at the waist stays. Per panel of docs/ref/personaggi/kael_busto_3viste.png (P, measured on the sheet): the tails' area
(E) erased; the vest's part of it (V, its bottom along the sheet's own hem) plum with the sheet's jagged black shadows
(F) and its outline (L); the rest the sheet's background. Then the suit a little darker (DARK) and each panel cut out
alone on a square of the background (BOX: the other figures' hands cleared), 1024 px.

usage: python3 tools/kael_notails.py [OUT_DIR]   (writes OUT_DIR/kael_busto_senza_code_{destra,fronte,sinistra}.png and
OUT_DIR/kael_busto_senza_code.png, the whole sheet; default docs/ref/personaggi)"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'docs', 'ref', 'personaggi', 'kael_busto_3viste.png')
BG, PLUM, SHADOW, INK = (211, 211, 213), (76, 57, 86), (28, 23, 31), (20, 18, 23)
S = 4   # supersampling
P = {   # erase area, the vest's part of it, black shadows inside the vest (jagged, as the sheet's folds), outlines
 'fronte': dict(
   E=[(918, 493), (946, 487), (992, 491), (1004, 500), (1052, 622), (1052, 712), (1030, 802), (1008, 802), (990, 750), (930, 712), (930, 669), (889, 617), (905, 545)],
   V=[(918, 493), (946, 487), (992, 491), (1004, 503), (1046, 624), (953, 668), (925, 643), (900, 646), (887, 617), (903, 545)],
   F=[[(918, 494), (1002, 500), (990, 512), (975, 560), (965, 520), (950, 578), (940, 522), (928, 550), (922, 510)],
      [(1004, 503), (1046, 624), (1039, 630), (1018, 582), (1022, 618), (1008, 562), (1003, 525)],
      [(975, 657), (962, 600), (992, 649)], [(1010, 642), (1000, 588), (1026, 634)]],
   L=[[(918, 493), (946, 487), (992, 491), (1004, 503)], [(1004, 503), (1046, 624), (953, 668), (925, 643), (904, 646)]],
   ),
 'destra': dict(
   E=[(366, 493), (386, 485), (403, 489), (412, 520), (426, 600), (444, 700), (436, 792), (424, 792), (406, 772), (360, 707), (360, 663), (338, 613), (352, 545)],
   V=[(366, 493), (386, 486), (402, 490), (400, 560), (395, 620), (392, 645), (376, 668), (360, 646), (347, 648), (336, 613), (350, 545)],
   F=[[(367, 494), (402, 491), (398, 505), (390, 545), (384, 515), (376, 562), (370, 520)],
      [(402, 491), (400, 560), (395, 620), (392, 645), (386, 640), (392, 580), (396, 520)], [(371, 660), (376, 605), (384, 650)]],
   L=[[(366, 493), (386, 486), (402, 490)], [(402, 490), (400, 560), (395, 620), (392, 645), (376, 668), (360, 646), (343, 649)]],
   ),
 'sinistra': dict(
   E=[(1468, 495), (1500, 485), (1545, 489), (1562, 492), (1586, 515), (1594, 578), (1616, 640), (1602, 710), (1582, 802), (1566, 802), (1544, 750), (1480, 710), (1480, 669), (1436, 617), (1454, 545)],
   V=[(1468, 495), (1500, 486), (1545, 490), (1560, 495), (1576, 518), (1586, 580), (1607, 640), (1497, 670), (1470, 645), (1455, 648), (1434, 617), (1452, 545)],
   F=[[(1469, 496), (1560, 496), (1548, 512), (1530, 566), (1520, 520), (1505, 582), (1495, 522), (1482, 552), (1475, 510)],
      [(1560, 496), (1576, 518), (1586, 580), (1607, 640), (1598, 646), (1574, 586), (1578, 622), (1562, 562), (1557, 520)],
      [(1526, 662), (1513, 604), (1542, 657)], [(1568, 651), (1558, 600), (1583, 645)]],
   L=[[(1468, 495), (1500, 486), (1545, 490), (1560, 495)], [(1560, 495), (1576, 518), (1586, 580), (1607, 640), (1497, 670), (1470, 645), (1450, 648)]],
   ),
}
DARK = (.15, 130., 20., 45.)   # the suit a little darker (Denis, 11/11: "annerisci leggermente la tuta"): by [0], its colours under [1] in their
                               # largest channel (faded over [2]), not the purples (blue over green by [3] or more) nor the skin
BOX = {'destra': (0, 60, 560, 800), 'fronte': (540, 60, 1220, 800), 'sinistra': (1215, 60, 1774, 800)}
LW = 3.6

def edit(im, p):
    x0 = min(x for x, _ in p['E']) - 12; y0 = min(y for _, y in p['E']) - 12; x1 = max(x for x, _ in p['E']) + 12; y1 = max(y for _, y in p['E']) + 12
    w, h = x1 - x0, y1 - y0; sc = lambda pts: [((x - x0) * S, (y - y0) * S) for x, y in pts]
    patch = im.crop((x0, y0, x1, y1)).resize((w * S, h * S), Image.NEAREST); d = ImageDraw.Draw(patch)
    d.polygon(sc(p['E']), fill=BG); d.polygon(sc(p['V']), fill=PLUM)   # (V's left chain just outside E's: no light band between)
    for f in p['F'] + p.get('X', []): d.polygon(sc(f), fill=SHADOW)
    if 'D' in p: d.line(sc(p['D']), fill=SHADOW, width=int(6 * S), joint='curve')
    if 'D2' in p: d.line(sc(p['D2']), fill=SHADOW, width=int(5 * S))   # (the tails' left edge, with its light rim: the vest's shadow there)
    for l in p['L']:
        pts = sc(l); d.line(pts, fill=INK, width=int(LW * S), joint='curve')
        for q in pts: r = LW * S / 2; d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=INK)
    patch = patch.resize((w, h), Image.LANCZOS)
    m = Image.new('L', (w * S, h * S), 0); ImageDraw.Draw(m).polygon(sc(p['E']), fill=255)
    m = m.resize((w, h), Image.LANCZOS).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(.8))
    im.paste(patch, (x0, y0), m)

def alone(im, box, size=1024, margin=.06):
    c = np.asarray(im.crop(box)).astype(int); fg = np.abs(c - np.array(BG)).max(2) > 14
    lab, n = ndimage.label(ndimage.binary_closing(fg, iterations=2)); big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    keep = ndimage.binary_dilation(lab == big, iterations=2); c[~keep] = BG
    ys, xs = np.nonzero(lab == big); c = c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    side = int(max(c.shape[:2]) * (1 + 2 * margin)); out = np.zeros((side, side, 3), np.uint8); out[:] = BG
    oy, ox = (side - c.shape[0]) // 2, (side - c.shape[1]) // 2; out[oy:oy + c.shape[0], ox:ox + c.shape[1]] = c
    return Image.fromarray(out).resize((size, size), Image.LANCZOS), int((~keep).sum() - (~fg).sum())

if __name__ == '__main__':
    im = Image.open(SRC).convert('RGB')
    for k, p in P.items(): edit(im, p)
    a = np.asarray(im).astype(np.float64); mx = a.max(2); w = np.clip((DARK[1] - mx) / DARK[2], 0, 1) * ((a[..., 2] - a[..., 1]) < DARK[3]) * (a[..., 0] < 140)
    im = Image.fromarray(np.clip(a * (1 - DARK[0] * w[..., None]), 0, 255).round().astype(np.uint8))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs', 'ref', 'personaggi')
    im.save(os.path.join(out, 'kael_busto_senza_code.png'))
    for k, b in BOX.items():
        a, _ = alone(im, b); a.save(os.path.join(out, 'kael_busto_senza_code_%s.png' % k)); print('written', os.path.join(out, 'kael_busto_senza_code_%s.png' % k))
