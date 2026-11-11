#!/usr/bin/env python3
"""The three views of a 3-view head sheet (right, front, left) as Meshy's multi-image-to-3d inputs (10/11/2026, Kael's
new head, as Ren's: docs/meshy/REN.md "Testa nuova", its second try, the views cropped to the head and the collar):
each panel cut to a square from the hair's top to a little under the chin (UNDER_CHIN of the head's height: the
collar), centred on the face, 1024 px; under the chin only the collar kept (the figure's columns within COLLAR of the
face's centre, the shoulders and the flap left out, the sheet's background there); with --black, the cloth's dark
purple as Denis wants the suit (black: his front drawing's two blacks, BLACK) and the purple on the skin (the tattoos)
black too.

usage: python3 tools/head_views.py SHEET.png OUT_DIR NAME [--black]   (writes OUT_DIR/NAME_destra.png, _fronte, _sinistra)"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheet_scan import panels, classes

UNDER_CHIN, COLLAR = .26, .34   # (shares of the head's height: hair's top to chin)
BLACK = ((46, 45, 48), (14, 13, 15), 52)   # the suit's black and its folds' (kael_nero.png), the split (the sheet's lightness)


def main(sheet, out, name, black=False):
    D = np.asarray(Image.open(sheet).convert('RGB')).astype(np.float64)
    lab, bg, boxes = panels(D); cl_all = classes(D)
    for view, (x0, y0, x1, y1, ids) in zip(('destra', 'fronte', 'sinistra'), boxes):
        fig = np.isin(lab, ids); sk = fig & (cl_all == 1)
        ys = np.nonzero(fig[:, x0:x1].any(1))[0]; top = ys.min()
        fy, fx = np.nonzero(sk[top:top + int(.62 * (ys.max() - top)), x0:x1]); cx = x0 + fx.mean(); chin = top + fy.max()
        hh = chin - top; side = int(hh * (1 + UNDER_CHIN)) + 20; c0 = int(cx - side / 2); r0 = top - 15
        P = D.copy()
        if black:   # the cloth's dark purple black (not the hair: above the chin), the tattoos black
            low = np.zeros(D.shape[:2], bool); low[chin - 8:] = True
            r, g, b = D[..., 0], D[..., 1], D[..., 2]; L = D.mean(2)
            cloth = fig & low & (cl_all != 1) & (D.max(2) < 140) & (b > r - 5) & ~((b > g + 40) & (b > 100) & (D.max(2) > 140))
            P[cloth] = np.where((L[cloth] > BLACK[2])[:, None], BLACK[0], BLACK[1])
            tat = fig & low & (cl_all == 4) & ndimage.binary_dilation(sk, iterations=6)
            tat &= ~ndimage.binary_dilation(cloth, iterations=2)
            P[tat] = BLACK[1]
        keep = fig.copy()   # under the chin, only the collar
        rows = np.arange(D.shape[0])[:, None] > chin + 6; cols = np.abs(np.arange(D.shape[1])[None, :] - cx) > COLLAR * hh
        keep &= ~(rows & cols)
        lab_k, n = ndimage.label(keep); sz = ndimage.sum(keep, lab_k, range(1, n + 1)); keep = lab_k == (np.argmax(sz) + 1)
        P[~keep] = bg
        pad = 200; Pp = np.empty((P.shape[0] + 2 * pad, P.shape[1] + 2 * pad, 3)); Pp[:] = bg; Pp[pad:-pad, pad:-pad] = P   # (the sheet's background past its edges)
        im = Image.fromarray(np.clip(Pp, 0, 255).astype(np.uint8)).crop((c0 + pad, r0 + pad, c0 + pad + side, r0 + pad + side)).resize((1024, 1024), Image.LANCZOS)
        im.save(os.path.join(out, '%s_%s.png' % (name, view)))
        print('%s: face centre x %d, hair top %d, chin %d, square %d px' % (view, cx, top, chin, side))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:4], black='--black' in sys.argv)
