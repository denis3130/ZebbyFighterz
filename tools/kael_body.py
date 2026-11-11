#!/usr/bin/env python3
"""Kael's body painted from Denis's three body sheets, as his head from his six head images (11/11/2026; Denis, sending
kael_busto_3viste.png, kael_gambe_3viste.png and kael_retro.png again: "ok ora migliorami il corpo come hai fatto per il
viso deve essere identico", and choosing to keep the model's shapes and repaint it: "Solo ridipingere, gratis").

- The views: the bust sheet's three panels (his right three quarters, front, his left three quarters), the legs sheet's
  three and the back sheet; their cameras the scan's (tools/sheet_scan.py, docs/meshy/kael_body_cams.json: yaw, scale,
  place), the model in its bind pose with the look's shape.
- Each texel of the body (not the triangles the new head hides, tools/kael_head.py) from the view that faces it most
  (the sharpest choice, no blend: no doubled lines), where that view sees it (the triangle in front there, SEEN) and its
  pixel is inside the drawn figure (not its outline: OUTLINE px from the background). The arms' skin and the hands are
  not repainted (tools/kael_arms.py fitted them arm by arm; Meshy's arms are not quite where the drawings have them): on
  them only the tattoos are the drawings' purple.
- Where no view paints (the sides between the views, under the arms, inside the legs), the colours already there in the
  drawings' palette: the suit's lit black to the drawings' dark plum, its folds to their black, the tattoos to purple.
- Then the drawings' flat colours (PAL): each texel one of them, with its black lines over it all or none (no soft
  ramps), the specks under SPECK mm2 as what is around them.

usage: python3 tools/kael_body.py PACKAGE_DIR [DEBUG_DIR]   (after tools/kael_arms.py: reads PACKAGE_DIR/kael_painted.jpg,
writes PACKAGE_DIR/kael_painted.png, which the pages take in its place; DEBUG_DIR: the view that painted each texel)"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kael_fix import load
from paint_views import texel_table
from cel_light import view_depth
import sheet_scan

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REF = os.path.join(ROOT, 'docs', 'ref', 'personaggi')
CAMS = os.path.join(ROOT, 'docs', 'meshy', 'kael_body_cams.json')
# the drawings' flat colours (measured on the three sheets, 11/11): the suit's plum and its black shadows, the purple in light
# and in shadow, the skin and its shadow, the lines' black
PAL = {'plum': (76, 58, 84), 'black': (28, 24, 30), 'purple': (166, 90, 202), 'purpleS': (84, 44, 112),
       'skin': (247, 188, 146), 'skinS': (172, 116, 90)}
INKC = (10, 9, 11)
SEEN, OUTLINE, FACING, POW = .004, 3, .25, 8.   # m: in front at its pixel; px of the figure's rim left out; the least facing; its weight's power
USE = {'retro': 'all', 'gambe_fronte': 'shaft', 'gambe_dx': 'shaft', 'gambe_sx': 'shaft'}   # the views that paint, and what (see main)
SHAFT = (.195, .285)                             # m: the boots' shafts (bind pose's height), between their purple strap and the trousers' cuff
ARM_SKIN = .45                                  # the arms' (shoulders' to hands') share of a texel's bones over this: its skin not repainted
RECOLOUR = {(46, 45, 48): 'plum', (14, 13, 15): 'black'}   # tools/kael_fix.py's suit tones (lit, folds) -> the drawings'
TAT = (.006, .5, 1, 20, .25)                   # see the tattoos in main(): rim (m), its skin share, edge (texels); the least piece (texels), its inside's share
UPPER, BACK_FACING = .3, .5                    # the shoulders' and upper arms' bones' share; the back sheet: the least facing
SPECK, INK_MIN = (6., 1.), .5                  # mm2: specks of a colour (cloth, lines) taken by what is around them; ink all or none


def nearest(c, cols):
    """Per colour the index of the nearest flat colour (rgb distance)."""
    d = ((c[:, None, :] - cols[None]) ** 2).sum(2); return d.argmin(1), np.sqrt(d.min(1))


def main(pkg, debug=None):
    name, m, P, N, UV, I, jn, wn, lj, LB = load(pkg)
    if 'move' in lj:
        mv = lj['move']; mi = np.frombuffer(LB, np.uint16, mv['idx'][1], mv['idx'][0]).astype(np.int64)
        P[mi] = np.frombuffer(LB, np.float32, mv['pos'][1], mv['pos'][0]).reshape(-1, 3)
    drawn = np.ones(len(I), bool)
    hp = os.path.join(pkg, name + '_head.json')
    if os.path.exists(hp):   # (the triangles the new head hides: not drawn)
        hj = json.load(open(hp)); HB = open(os.path.join(pkg, name + '_head.bin'), 'rb').read()
        drawn[np.frombuffer(HB, np.uint32, hj['hide'][1], hj['hide'][0]).astype(np.int64)] = False
    tp = os.path.join(pkg, name + '_painted.jpg')
    T = np.asarray(Image.open(tp).convert('RGB')).astype(np.float64); TS = T.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, TS)
    use = drawn[ks]; print('body: %d texels, %d on the drawn triangles' % (len(ks), int(use.sum())))
    bi = {b['n']: i for i, b in enumerate(m['bones'])}; nb = len(m['bones'])
    bw = lambda *ns: sum(((jn == bi[n]) * wn).sum(1) for n in ns if n in bi)
    arm_v = bw('LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand') + ((jn >= nb) * wn).sum(1)
    arm = (arm_v[I[ks]] * bary).sum(1) > ARM_SKIN
    cols = np.array(list(PAL.values()), np.float64); names = list(PAL)
    c0 = T[ys, xs]
    # 1. the colours already there in the drawings' palette (see RECOLOUR; the purples to theirs; Meshy's skin as it is)
    out = T.copy(); cur = c0.copy()
    src = np.array(list(RECOLOUR), float); dst = np.array([PAL[v] for v in RECOLOUR.values()], float)
    cl = sheet_scan.classes(c0)
    dark = cl == 3
    if dark.any():
        j, _ = nearest(c0[dark], src); cur[dark] = dst[j]
    pur = cl == 4
    if pur.any():
        L = c0[pur].mean(1); cur[pur] = np.where((L > 105)[:, None], np.array(PAL['purple'], float), np.array(PAL['purpleS'], float))
    # 2. the views
    cams = json.load(open(CAMS)); best = np.full(len(ks), -1.); got = np.zeros((len(ks), 3)); who = np.full(len(ks), -1)
    idx = np.nonzero(use)[0]; p, n = pos[idx], nor[idx]
    # (only some views paint. Projected, the front's and the three quarters' drawings were smeared purple strokes and doubled shadows: Meshy's
    # shapes are not quite theirs (the sash's knot, the hem, the folds), the overlaps of the silhouettes 62-78%. The back sheet overlaps
    # the model's back by 85%: it paints all it sees well (the back's shadows, the trousers' stripes, the tattoos and the bracers from
    # behind). The legs' views paint the boots' shafts alone (SHAFT), their dark colours only: Meshy painted the shafts all black)
    upper = (bw('LeftShoulder', 'LeftArm', 'RightShoulder', 'RightArm')[I[ks]] * bary).sum(1) > UPPER
    only = os.environ.get('KAEL_BODY_VIEWS')   # (to try a subset: names, comma separated; empty: none)
    shaft = (pos[idx, 1] > SHAFT[0]) & (pos[idx, 1] < SHAFT[1])
    for vi, (key, cam) in enumerate(cams['views'].items()):
        if only is not None and key not in only.split(','): continue
        if only is None and key not in USE: continue
        D = np.asarray(Image.open(os.path.join(REF, cam['sheet'])).convert('RGB')).astype(np.float64); H, W = D.shape[:2]
        bx = cam['box']; F = np.zeros((H, W), bool)   # (the figure: not the background, as tools/sheet_scan.py finds it)
        bg = np.median(np.concatenate([D[:8].reshape(-1, 3), D[-8:].reshape(-1, 3), D[:, :8].reshape(-1, 3), D[:, -8:].reshape(-1, 3)]), 0)
        fig = ndimage.binary_opening(np.abs(D - bg).sum(2) > sheet_scan.BG_TOL, iterations=1)
        F[bx[1]:bx[3], bx[0]:bx[2]] = fig[bx[1]:bx[3], bx[0]:bx[2]]
        F = ndimage.binary_erosion(ndimage.binary_fill_holes(F), iterations=OUTLINE)
        Z, pj = view_depth(P, I[drawn], cam, W, H); u, v, dep = pj(p)
        ui, vi_ = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
        t = np.radians(cam['yaw']); facing = n @ np.array([np.sin(t), 0, np.cos(t)])
        ok = (dep >= Z[vi_, ui] - SEEN) & (facing > FACING) & (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1) & F[vi_, ui]
        x0, y0 = np.clip(np.floor(u).astype(int), 0, W - 2), np.clip(np.floor(v).astype(int), 0, H - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        col = (D[y0, x0] * (1 - fx) + D[y0, x0 + 1] * fx) * (1 - fy) + (D[y0 + 1, x0] * (1 - fx) + D[y0 + 1, x0 + 1] * fx) * fy
        if USE.get(key) == 'shaft': ok &= shaft & (sheet_scan.classes(col) == 3)
        else: ok &= (facing > BACK_FACING) & ~upper[idx]   # (the back, seen well; not the shoulders and the upper arms: there the
        # sheet's tattoos and the vest's edge fell at a slant, purple smears on the deltoid from the side)
        w = np.where(ok, facing ** POW, -1.); bet = w > best[idx]
        best[idx[bet]] = w[bet]; got[idx[bet]] = col[bet]; who[idx[bet]] = vi
        print('view %-14s (%s, yaw %+.0f): sees %d texels, paints %d so far' % (key, cam['sheet'], cam['yaw'], int(ok.sum()), int((who == vi).sum())))
    painted = (who >= 0) & ~(arm & (sheet_scan.classes(got) == 1))   # (not the arms' skin: kael_arms)
    painted &= ~(arm & (sheet_scan.classes(got) == 3) & (sheet_scan.classes(c0) == 1))   # (nor the drawing's dark over the arms' skin: misplaced lines)
    cur[painted] = got[painted]
    # (the arms' tattoos: purple, as the sheets draw them (tools/kael_arms.py painted them in kael_nero.png's black). In the texture, the dark
    # pieces of the shoulders' and the upper arms' texels whose rim (TAT[0] texels) is skin's for at least TAT[1] of it: their inside purple,
    # their edge (TAT[2] texels) the purple's shadow)
    # (the rim in 3D, TAT[0] m round the piece: in the texture a piece's neighbours may be another piece of the atlas, the arm's skin next to
    # the back's cloth, which turned the back's shadows purple)
    UP = np.zeros((TS, TS), bool); UP[ys[use & upper], xs[use & upper]] = True
    CL = np.zeros((TS, TS), np.uint8); CL[ys, xs] = sheet_scan.classes(cur); RI = -np.ones((TS, TS), np.int64); RI[ys, xs] = np.arange(len(ks))
    lab, nl = ndimage.label(UP & (CL == 3), structure=np.ones((3, 3)))
    ui_ = np.nonzero(use & upper)[0]; tr = cKDTree(pos[ui_]); skin_u = sheet_scan.classes(cur[ui_]) == 1
    tat = np.zeros((TS, TS), bool); nt = 0
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        me = lab[sl] == i
        if me.sum() < TAT[3] or ndimage.binary_erosion(me).sum() < TAT[4] * me.sum(): continue   # (not the muscles' thin lines: no inside)
        rows = RI[sl][me]; near = np.unique(np.concatenate(tr.query_ball_point(pos[rows][::max(1, len(rows) // 200)], TAT[0])))
        near = near[~np.isin(ui_[near], rows)]
        if len(near) and skin_u[near].mean() >= TAT[1]: tat[sl] |= me; nt += 1
    edge = tat & ~ndimage.binary_erosion(tat, iterations=TAT[2])
    tt = tat[ys, xs] & use; cur[tt] = PAL['purple']; te = edge[ys, xs] & use; cur[te] = PAL['purpleS']
    print('body: %d pieces of the arms\' tattoos (%d texels) to the drawings\' purple' % (nt, int(tt.sum())))
    print('body: %d texels painted from the views, %d recoloured to the palette' % (int(painted.sum()), int((use & ~painted).sum())))
    # 3. the flat colours
    k, dist = nearest(cur, cols); a_ = np.zeros(len(ks))
    ink = (cur.mean(1) < 22) & (dist > 12)
    newc = cols[k]; newc[ink] = INKC
    out[ys[use], xs[use]] = newc[use]
    cov = np.zeros((TS, TS), bool); cov[ys[use], xs[use]] = True
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    op = os.path.join(pkg, name + '_painted.png')
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(op, optimize=True)
    print('written', op, os.path.getsize(op), 'bytes')
    if debug:
        os.makedirs(debug, exist_ok=True); dbg = np.zeros((TS, TS, 3), np.uint8)
        pc = np.array([(230, 60, 60), (60, 200, 60), (60, 90, 230), (230, 200, 40), (200, 60, 200), (60, 200, 200), (240, 140, 40)], np.uint8)
        dbg[ys[who >= 0], xs[who >= 0]] = pc[who[who >= 0] % len(pc)]
        Image.fromarray(dbg).save(os.path.join(debug, 'views.png'))


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
