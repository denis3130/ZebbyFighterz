#!/usr/bin/env python3
"""Kael's arms painted from Denis's drawings (10/11/2026; Denis: "il colore della tuta e tatuaggi rimane nero e i guanti
pure non toccarli, ma tutto il resto cerca di farlo identico come nelle foto, soprattutto viso e capelli e braccia"), as
Ren's body was painted from his (tools/paint_from_drawing.py, tools/paint_views.py): the arms' skin and their tattoos
from the front drawing (kael_nero.png), the back sheet (kael_retro.png) and the bust sheet's three-quarter panels
(kael_busto_3viste.png: each the outer side of the arm nearer to it), in flat light there (the look's flat share: the
drawings' own shading, as Ren's FLAT_BODY).

- The cameras: the front's and the back's from the scan (docs/meshy/kael_scan.json, tools/sheet_scan.py); a
  three-quarter panel's turned by SIDE_YAW (the scan of its near arm's outline peaks there, flatly), its scale and place
  those of its near arm. Meshy's arms are not quite where the drawings have them: each arm's skin as a view sees it is
  fitted to the drawing's (FIT: a turn about its middle, a scale and a shift, the most overlap of the two, the lines
  and tattoos inside them counted in), and its texels take the drawing's colour where that puts them.
- The arms' skin: the texels of the shoulders, upper arms and elbows (their bones' share over ARM_W; not the hands)
  painted skin (with its lines), and the dark ones among them that skin surrounds (Meshy's tattoo strokes: in a
  HOLE-wide neighbourhood, at least HOLE_SKIN of it skin, on the upper arm, not the forearm's bracer; or in the
  texture a bit under SPECK texels with at least SPECK_SKIN of skin around it: Meshy's dashes by the bracers' bands);
  not the vest's sides under the arms, nor the bracers, nor the gloves. All of it painted anew: Meshy's sketchy strokes
  go. The other dark bits on the shoulders and upper arms (Meshy painted the collar's point and black strokes on the
  right shoulder's skin): skin where a drawing facing them well has its arm there, if under CAND_MAX texels with at
  least CAND_SKIN of skin around them (not the vest, nor the black on the collar's point, which lies over that shoulder
  on the arm's bones; nothing purple: the point's own colour).
- A drawing's colour: inside its arm (its skin with the lines and tattoos inside it, CLOSE) as drawn; outside it (the
  arm's outline, the vest beyond: where Meshy's arm is a little bigger) the nearest of its arm's colours from EDGE_IN
  inside it (not the edge's soft blend into the outline: brown smears at the elbows). The back and the bust sheets'
  tattoos are purple: black (TATTOO) as on the front, their soft edges too.
- The views on a texel: the one it faces most (SHARP: a narrow change from one to the next, no double lines), only
  where that view sees it (the triangle in front at its pixel, or one sharing a corner with it, by its place: the UV
  pieces' seams split the vertices, and the seams kept Meshy's paint in thin light lines); by how much it faces it
  (FACE) over the drawings' skin in light (BASE: where no view paints, the shoulders' tops, under the arms).

usage: python3 tools/kael_arms.py PACKAGE_DIR [DEBUG_DIR]   (after tools/kael_fix.py: paints PACKAGE_DIR/kael_painted.jpg
over in place and sets the arms' flat light in PACKAGE_DIR/kael_look.bin; DEBUG_DIR: each view's fit, the model's arm
outline in red on the drawing before it and in green after)"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage, sparse
from scipy.fft import rfft2, irfft2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kael_fix import load, classes
from paint_views import texel_table, seen_ids
import sheet_scan

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REF = os.path.join(ROOT, 'docs', 'ref', 'personaggi')
SIDE_YAW, SIDE_S = 30., 800.   # deg (the bust's three-quarter panels); px/m, a first guess of their scale
# (name, sheet, the arms it paints, yaw (None: the scan's camera, of the sheet's panel PANEL[name], default its first), the x range of its near
# arm's skin (px), purple tattoos). The front: the bust sheet's front panel (11/11: Denis's body sheets, purple tattoos; it was kael_nero.png's,
# black ones)
VIEWS = (('front', 'kael_busto_3viste.png', ('Left', 'Right'), None, None, True),
         ('back', 'kael_retro.png', ('Left', 'Right'), None, None, True),
         ('his right side', 'kael_busto_3viste.png', ('Right',), -SIDE_YAW, (0, 300), True),
         ('his left side', 'kael_busto_3viste.png', ('Left',), SIDE_YAW, (1474, 1774), True))
PANEL = {'front': 1}
ARM_W, HAND_W = .5, .2
HOLE, HOLE_CELL, HOLE_SKIN = .02, .004, .6   # m: the neighbourhood, its cells; the share of skin in it
SPECK, SPECK_SKIN = 400, .7                   # texels: a small bit in the texture; the share of skin around it
CAND_MAX, CAND_SKIN = 3000, .4               # texels: the biggest dark bit on the shoulders a drawing may paint skin;
                                              # the share of skin around it at least
EDGE_IN = 3                                   # px: a drawing's arm's colours outside it from this far inside it
CLOSE = 7                                     # px: the drawing's lines and tattoos inside its skin (a closing)
FIT = {'turn': (-12., 12., 1.), 'scale': (.85, 1.15, .02), 'shift': 40, 'fine': (1., .25, .02, .005)}   # deg, x, px
FACE, FLAT, SHARP = (.3, .6), (.1, .45), 40.  # n . d: the paint's weight; the flat light's (as Ren's FLAT_BODY)
TAT_VIEW = (.05,)                             # see the shoulders' tattoos in main()
BASE = (246., 187., 146.)                     # the drawings' skin in light
TATTOO, TATTOO_EDGE = None, 2                 # the tattoos' colour (None: as the sheets draw them, purple with their black outline; it was
                                              # kael_nero.png's black, (14, 13, 15)); px of soft edge around the purple ones


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def disk(r):
    a = np.arange(-r, r + 1); return np.add.outer(a * a, a * a) <= r * r


def warp(M, th, sc, c):
    """M (rows v, cols u) moved by q = c + sc R(th) (p - c) (p, q, c in u, v): M on q's grid."""
    co, si = np.cos(th), np.sin(th)
    Rvu = (np.array([[co, si], [-si, co]]) / sc)[::-1, ::-1]   # (p - c = R(-th) (q - c) / sc, in v, u order)
    cvu = np.array([c[1], c[0]])
    return ndimage.affine_transform(M.astype(np.float32), Rvu, offset=cvu - Rvu @ cvu, order=1) > .5


def fit(Mm, Dm, c):
    """The turn (rad), scale and shift (u, v px) that put the model's mask Mm the most over the drawing's Dm, and that
    overlap (intersection over union)."""
    S = FIT['shift']; ys, xs = np.nonzero(Mm | Dm)
    y0, y1, x0, x1 = max(ys.min() - S - 10, 0), ys.max() + S + 11, max(xs.min() - S - 10, 0), xs.max() + S + 11
    Mw, Dw = Mm[y0:y1, x0:x1], Dm[y0:y1, x0:x1].astype(np.float64); cw = (c[0] - x0, c[1] - y0)
    FD = rfft2(Dw); nD = Dw.sum(); best = (-1,)

    def score(th, sc):
        W = warp(Mw, th, sc, cw).astype(np.float64); nW = W.sum()
        cor = irfft2(FD * np.conj(rfft2(W)), s=Dw.shape)   # cor[t] = sum_q D(q) W(q - t)
        cor = np.roll(np.roll(cor, S, 0), S, 1)[:2 * S + 1, :2 * S + 1]
        iou = cor / np.maximum(nW + nD - cor, 1)
        k = np.unravel_index(np.argmax(iou), iou.shape); return iou[k], (k[1] - S, k[0] - S)

    for th in np.radians(np.arange(FIT['turn'][0], FIT['turn'][1] + 1e-9, FIT['turn'][2])):
        for sc in np.arange(FIT['scale'][0], FIT['scale'][1] + 1e-9, FIT['scale'][2]):
            iou, t = score(th, sc)
            if iou > best[0]: best = (iou, th, sc, t)
    dt, st, ds, ss = FIT['fine']; th0, sc0 = best[1], best[2]
    for th in th0 + np.radians(np.arange(-dt, dt + 1e-9, st)):
        for sc in sc0 + np.arange(-ds, ds + 1e-9, ss):
            iou, t = score(th, sc)
            if iou > best[0]: best = (iou, th, sc, t)
    return best[1], best[2], best[3], best[0]


def drawing(sheet, purple):
    """A sheet: its colours, its skin's classes, its tattoos (purple ones: the purple that skin surrounds; not the
    sash, the bracers, the collar's point) and its arms (the skin with the lines and the tattoos inside it)."""
    D = np.asarray(Image.open(os.path.join(REF, sheet)).convert('RGB')).astype(np.float64)
    dc = sheet_scan.classes(D); sk = dc == 1; tat = np.zeros_like(sk)
    if purple:
        lab, n = ndimage.label(dc == 4); keep = np.zeros(n + 1, bool)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            y0, y1 = max(sl[0].start - 6, 0), sl[0].stop + 6; x0, x1 = max(sl[1].start - 6, 0), sl[1].stop + 6
            me = lab[y0:y1, x0:x1] == i; ring = ndimage.binary_dilation(me, iterations=4) & ~me
            keep[i] = me.sum() > 30 and sk[y0:y1, x0:x1][ring].mean() > .6
        tat = keep[lab]
    dreg = ndimage.binary_fill_holes(ndimage.binary_closing(sk | tat, structure=disk(CLOSE)))
    return D, dc, tat, dreg


def main(pkg, debug=None):
    name, m, P, N, UV, I, jn, wn, lj, LB = load(pkg)
    if 'move' not in lj or 'nor' not in lj: sys.exit('run tools/kael_fix.py first')
    mv = lj['move']; mi = np.frombuffer(LB, np.uint16, mv['idx'][1], mv['idx'][0]).astype(np.int64)
    P[mi] = np.frombuffer(LB, np.float32, mv['pos'][1], mv['pos'][0]).reshape(-1, 3)
    NL = np.frombuffer(LB, np.float32, lj['nor'][1], lj['nor'][0]).reshape(-1, 3).astype(np.float64)   # (the light's)
    flat = np.frombuffer(LB, np.float32, lj['flat'][1], lj['flat'][0]).astype(np.float64).copy()
    bi = {b['n']: i for i, b in enumerate(m['bones'])}; nb = len(m['bones'])
    bw = lambda *ns: sum(((jn == bi[n]) * wn).sum(1) for n in ns)
    hand = bw('LeftHand', 'RightHand') + ((jn >= nb) * wn).sum(1)
    side = {s: bw(s + 'Shoulder', s + 'Arm', s + 'ForeArm') for s in ('Left', 'Right')}
    upper, fore = bw('LeftShoulder', 'LeftArm', 'RightShoulder', 'RightArm'), bw('LeftForeArm', 'RightForeArm')
    tp = os.path.join(pkg, name + '_painted.jpg')
    T = np.asarray(Image.open(tp).convert('RGB')).astype(np.float64); TS = T.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(P, NL, UV, I, TS)
    at = lambda w: (w[I[ks]] * bary).sum(1)
    hd, up, fo = at(hand), at(upper), at(fore); sd = {s: at(w) for s, w in side.items()}
    arm = ((sd['Left'] + sd['Right']) > ARM_W) & (hd < HAND_W)
    cl = classes(T[ys, xs])
    # the arms' skin, and the dark texels it surrounds (Meshy's tattoo strokes)
    skinish = arm & np.isin(cl, (2, 3, 4))
    g = np.floor(pos / HOLE_CELL).astype(np.int64); g -= g[arm].min(0); shp = tuple(g[arm].max(0) + 1)
    Sk = np.zeros(shp, np.float32); Al = np.zeros(shp, np.float32)
    np.add.at(Sk, tuple(g[skinish].T), 1); np.add.at(Al, tuple(g[arm].T), 1)
    k = int(round(HOLE / HOLE_CELL)) | 1
    Sk = ndimage.uniform_filter(Sk, k); Al = ndimage.uniform_filter(Al, k)
    gi = tuple(np.clip(g, 0, np.array(shp) - 1).T)
    share = np.where(arm, Sk[gi] / np.maximum(Al[gi], 1e-6), 0)
    hole = arm & np.isin(cl, (0, 1)) & (share > HOLE_SKIN) & (up > fo)   # (dark or purple: Meshy's purple tattoo strokes too, which stayed
    # beside the drawn bolt in pieces; 11/11)
    # (and in the texture, the small dark or purple bits that skin surrounds: Meshy's dashes by the bracers' bands)
    A2 = np.zeros((TS, TS), bool); A2[ys, xs] = arm; K2 = np.zeros((TS, TS), bool); K2[ys, xs] = skinish | hole
    lab, n = ndimage.label(A2 & ~K2); sz = np.bincount(lab.ravel()); small = np.zeros(n + 1, bool)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sz[i] > SPECK: continue
        y0, y1 = max(sl[0].start - 3, 0), sl[0].stop + 3; x0, x1 = max(sl[1].start - 3, 0), sl[1].stop + 3
        me = lab[y0:y1, x0:x1] == i; ring = ndimage.binary_dilation(me, iterations=2) & ~me & A2[y0:y1, x0:x1]
        small[i] = ring.any() and K2[y0:y1, x0:x1][ring].mean() > SPECK_SKIN
    hole |= small[lab[ys, xs]] & arm
    reg = skinish | hole
    # (the dark paint left on the shoulders and upper arms: skin too where a drawing facing it says so; not the purple:
    # the collar's point lies over the right shoulder, on the arm's bones)
    cand = arm & ~reg & (cl == 0) & (up > fo)
    C2 = np.zeros((TS, TS), bool); C2[ys, xs] = cand; lab, n = ndimage.label(C2)   # (only small bits by the skin: not
    sz = np.bincount(lab.ravel()); okc = np.zeros(n + 1, bool); RG = np.zeros((TS, TS), bool); RG[ys, xs] = reg   # the vest,
    CV = np.zeros((TS, TS), bool); CV[ys, xs] = True                                 # nor the collar's point's black)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sz[i] >= CAND_MAX: continue
        y0, y1 = max(sl[0].start - 3, 0), sl[0].stop + 3; x0, x1 = max(sl[1].start - 3, 0), sl[1].stop + 3
        me = lab[y0:y1, x0:x1] == i; ring = ndimage.binary_dilation(me, iterations=2) & ~me & CV[y0:y1, x0:x1]
        okc[i] = ring.any() and RG[y0:y1, x0:x1][ring].mean() >= CAND_SKIN
    cand &= okc[lab[ys, xs]]
    R = np.nonzero(reg | cand)[0]; isreg = reg[R]
    print('the arms\' skin: %d texels (%d of them dark strokes inside it); %d more dark ones to ask the drawings about' % (
        int(reg.sum()), int(hole.sum()), int(cand.sum())))
    nt = len(I); cnt = np.bincount(ks, minlength=nt); rcnt = np.bincount(ks[reg], minlength=nt)
    tri_reg = rcnt > .5 * np.maximum(cnt, 1)
    tri_side = {s: side[s][I].mean(1) > ARM_W for s in side}
    _, wid = np.unique(np.round(P * 1e5).astype(np.int64), axis=0, return_inverse=True); wid = wid.ravel()
    inc = sparse.csr_matrix((np.ones(I.size), (np.repeat(np.arange(nt), 3), wid[I].ravel())), shape=(nt, wid.max() + 1))
    adj = (inc @ inc.T).tocsr()   # (triangles sharing a corner, by its place: the UV pieces' seams split the vertices)
    scan = json.load(open(os.path.join(ROOT, 'docs', 'meshy', 'kael_scan.json')))
    sheets = {}; tat_dec = np.zeros(len(R), bool)
    Sc = np.full((len(VIEWS), len(R)), -np.inf); Co = np.zeros((len(VIEWS), len(R), 3)); dirs = []
    for vi, (vname, sheet, arms, yaw, near, purple) in enumerate(VIEWS):
        if sheet not in sheets: sheets[sheet] = drawing(sheet, purple)
        D, dc, tat, dreg = sheets[sheet]; H, W = D.shape[:2]
        sp = scan[sheet][PANEL.get(vname, 0)]; yaw = sp['yaw'] if yaw is None else yaw; t = np.radians(yaw)
        r, d = np.array([np.cos(t), 0, -np.sin(t)]), np.array([np.sin(t), 0, np.cos(t)]); dirs.append((d, arms))
        dbg = D.copy() if debug else None
        for s in arms:
            def model_mask(cam):
                u, v = cam[1] + cam[0] * (P @ r), cam[2] - cam[0] * P[:, 1]
                seen = seen_ids(P, I, np.ones(nt, bool), u, v, P @ d, H, W)
                Mm = (seen >= 0) & tri_reg[np.maximum(seen, 0)] & tri_side[s][np.maximum(seen, 0)]
                Mm = ndimage.binary_fill_holes(ndimage.binary_closing(Mm, structure=disk(CLOSE)))
                lab, n = ndimage.label(Mm); return seen, lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
            lab, n = ndimage.label(dreg)
            if near is None:   # (the scan's camera; its arm: the drawing's piece the model's arm is most over)
                cam = (sp['s'], sp['cx'], sp['by']); seen, Mm = model_mask(cam)
                ov = np.bincount(lab[ndimage.binary_dilation(Mm, iterations=30)], minlength=n + 1); ov[0] = 0
                Dm = lab == int(np.argmax(ov))
            else:              # (a three-quarter panel: its near arm, the biggest piece of skin there; the camera on it)
                sz = np.bincount(lab.ravel()); cxs = ndimage.mean(np.arange(W)[None, :].repeat(H, 0), lab, range(n + 1))
                ok = [i for i in range(1, n + 1) if sz[i] > 3000 and near[0] <= cxs[i] <= near[1]]
                Dm = lab == max(ok, key=lambda i: sz[i]); dy, dx = np.nonzero(Dm)
                av = np.unique(I[tri_reg & tri_side[s]])
                cam = (SIDE_S, (dx.min() + dx.max()) / 2 - SIDE_S * (P[av] @ r).mean(), (dy.min() + dy.max()) / 2 + SIDE_S * P[av, 1].mean())
                for _ in range(2):   # (its scale: the arm's height; its place: the arm's middle)
                    seen, Mm = model_mask(cam); my, mx = np.nonzero(Mm)
                    kk = (dy.max() - dy.min()) / max(my.max() - my.min(), 1)
                    mc, dcn = ((mx.min() + mx.max()) / 2, (my.min() + my.max()) / 2), ((dx.min() + dx.max()) / 2, (dy.min() + dy.max()) / 2)
                    cam = (cam[0] * kk, dcn[0] + kk * (cam[1] - mc[0]), dcn[1] + kk * (cam[2] - mc[1]))
                seen, Mm = model_mask(cam)
            my, mx = np.nonzero(Mm); cm = (mx.mean(), my.mean())
            th, sc, (tu, tv), iou = fit(Mm, Dm, cm)
            print('%s, his %s arm: turned %.2f deg, scale %.3f, moved (%d, %d) px; overlap %.0f%% (%.0f%% before)' % (
                vname, s.lower(), np.degrees(th), sc, tu, tv, 100 * iou, 100 * (Mm & Dm).sum() / (Mm | Dm).sum()))
            # the drawing's colour there: as drawn inside its arm, the nearest of its arm's colours outside it
            Dc = D.copy()
            if purple and TATTOO is not None:   # (its tattoos black, their soft edges too)
                tb = ndimage.binary_dilation(tat & Dm, iterations=TATTOO_EDGE) & Dm & (dc != 1)
                Dc[tb | (tat & Dm)] = TATTOO
            tz = ndimage.binary_dilation(tat & Dm, iterations=TATTOO_EDGE + 2)   # (the tattoo with its outline)
            if purple and near is None: Dc[tz & Dm] = BASE   # (the shoulders' tattoos from their three-quarter panel alone: below)
            Din = ndimage.binary_erosion(Dm, iterations=EDGE_IN)   # (not its edge's soft blend into the outline)
            _, (iy, ix) = ndimage.distance_transform_edt(~Din, return_indices=True); Dc = np.where(Dm[..., None], Dc, Dc[iy, ix])
            # the texels of this arm this view sees, facing it
            pr = pos[R]; pu = cam[1] + cam[0] * (pr @ r); pv = cam[2] - cam[0] * pr[:, 1]
            inside = (pu >= 0) & (pu < W - 1) & (pv >= 0) & (pv < H - 1)
            pui, pvi = np.clip(pu.round().astype(int), 0, W - 1), np.clip(pv.round().astype(int), 0, H - 1)
            kr = ks[R]; fid = seen[pvi, pui]; vis = (fid == kr) & inside; o = np.nonzero(~vis & (fid >= 0) & inside)[0]
            vis[o] = np.asarray(adj[kr[o], fid[o]]).ravel() > 0
            face = nor[R] @ d
            sel = (sd[s][R] > ARM_W) & vis & (face > FACE[0]) & (isreg | (face > FACE[1]))
            co, si = np.cos(th), np.sin(th); du, dv = pu[sel] - cm[0], pv[sel] - cm[1]
            qu = cm[0] + tu + sc * (co * du - si * dv); qv = cm[1] + tv + sc * (si * du + co * dv)
            ins = Din[np.clip(qv.round().astype(int), 0, H - 1), np.clip(qu.round().astype(int), 0, W - 1)]
            keep = isreg[sel] | ins; idx = np.nonzero(sel)[0]; sel[idx[~keep]] = False; qu, qv = qu[keep], qv[keep]   # (inside its arm)
            x0 = np.clip(np.floor(qu).astype(int), 0, W - 2); y0 = np.clip(np.floor(qv).astype(int), 0, H - 2)
            fx = np.clip(qu - x0, 0, 1)[:, None]; fy = np.clip(qv - y0, 0, 1)[:, None]
            Co[vi, sel] = (Dc[y0, x0] * (1 - fx) * (1 - fy) + Dc[y0, x0 + 1] * fx * (1 - fy) + Dc[y0 + 1, x0] * (1 - fx) * fy + Dc[y0 + 1, x0 + 1] * fx * fy)
            Sc[vi, sel] = face[sel]
            if purple and near is not None and tz.any():   # (the tattoo as a decal from this panel, where it draws it: every texel of this arm
                # it sees there, also at a slant (facing it over TAT_VIEW[0]), takes it over every other view; drawn by the front and the back
                # views too, the bolts met off by a few px: in pieces with black strokes; Denis, 11/11)
                st = (sd[s][R] > ARM_W) & vis & (face > TAT_VIEW[0]) & (up[R] > fo[R])
                du, dv = pu[st] - cm[0], pv[st] - cm[1]
                qu2 = cm[0] + tu + sc * (co * du - si * dv); qv2 = cm[1] + tv + sc * (si * du + co * dv)
                xi, yi = np.clip(qu2.round().astype(int), 0, W - 1), np.clip(qv2.round().astype(int), 0, H - 1)
                inn = tz[yi, xi]; ti = np.nonzero(st)[0][inn]
                x0 = np.clip(np.floor(qu2[inn]).astype(int), 0, W - 2); y0 = np.clip(np.floor(qv2[inn]).astype(int), 0, H - 2)
                fx = np.clip(qu2[inn] - x0, 0, 1)[:, None]; fy = np.clip(qv2[inn] - y0, 0, 1)[:, None]
                Co[vi, ti] = (D[y0, x0] * (1 - fx) * (1 - fy) + D[y0, x0 + 1] * fx * (1 - fy) + D[y0 + 1, x0] * (1 - fx) * fy + D[y0 + 1, x0 + 1] * fx * fy)
                Sc[vi, ti] = 10.; tat_dec[ti] = True
                print('  the tattoo: %d texels' % len(ti))
            print('  %d texels it sees (%d facing it well)' % (int(sel.sum()), int((face[sel] > FACE[1]).sum())))
            if debug:
                e = Mm & ~ndimage.binary_erosion(Mm, iterations=2); dbg[e] = (255, 0, 0)
                Wm = np.roll(np.roll(warp(Mm, th, sc, cm), tv, 0), tu, 1)
                e = Wm & ~ndimage.binary_erosion(Wm, iterations=2); dbg[e] = (0, 220, 0)
        if debug:
            os.makedirs(debug, exist_ok=True)
            Image.fromarray(dbg.astype(np.uint8)).save(os.path.join(debug, 'arms_%s.png' % vname.replace(' ', '_')))
    # (the shoulders' tattoos from one view: the three-quarter panel of their side, where they are drawn whole, wherever it sees the shoulder
    # and the upper arm well (TAT_VIEW: facing it over [0], the upper arm's bones over the forearm's). Chosen with the front and the back by
    # how much they faced, the front's bolt and the side's met off by a few px: the tattoo in pieces with black strokes; Denis, 11/11)
    for vi in range(len(VIEWS)):   # (the decal's texels: that view alone)
        own = Sc[vi] >= 10.
        Sc[:, own] = np.where(np.arange(len(VIEWS))[:, None] == vi, Sc[:, own], -np.inf)
    # each texel: the view it faces most (a narrow change to the next), over the skin in light where none faces it
    smax = Sc.max(0); seen_any = np.isfinite(smax)
    w = np.where(np.isfinite(Sc), np.exp(SHARP * (Sc - np.where(seen_any, smax, 0))), 0)
    col = (w[..., None] * Co).sum(0) / np.maximum(w.sum(0), 1e-12)[:, None]
    wt = np.where(seen_any, smooth(*FACE, np.where(seen_any, smax, 0)), 0)[:, None]
    new = np.array(BASE) * (1 - wt) + col * wt; put = isreg | seen_any   # (the asked ones: where a drawing said skin)
    out = T.copy(); out[ys[R[put]], xs[R[put]]] = new[put]
    print('%d of the dark ones on the shoulders and upper arms painted skin as the drawings have it' % int((~isreg & seen_any).sum()))
    cov = np.zeros((TS, TS), bool); cov[ys, xs] = True   # (between the UV pieces: the nearest piece's colour)
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(tp, quality=90, optimize=True)
    # the flat light: on the arms' skin where it faces a view (the drawings' shading painted there)
    vreg = np.zeros(len(P)); vc = np.zeros(len(P))
    np.add.at(vreg, I.ravel(), np.repeat(tri_reg.astype(float), 3)); np.add.at(vc, I.ravel(), 1)
    vin = (vreg / np.maximum(vc, 1) > .5) & ((side['Left'] + side['Right']) > ARM_W) & (hand < HAND_W)
    fl = np.zeros(len(P))
    for d, arms in dirs:
        for s in arms: fl = np.where(side[s] > ARM_W, np.maximum(fl, smooth(*FLAT, NL @ d)), fl)
    new = np.where(vin, np.maximum(flat, fl), flat)
    blob = bytearray(LB); of = lj['flat'][0]; blob[of:of + 4 * len(P)] = new.astype(np.float32).tobytes()
    open(os.path.join(pkg, name + '_look.bin'), 'wb').write(bytes(blob))
    print('paint: %d texels of the arms\' skin (%d from a drawing, %d facing one well); flat light on %d arm vertices' % (
        int(put.sum()), int((wt[put, 0] > 0).sum()), int((wt[put, 0] > .5).sum()), int((vin & (fl > .5)).sum())))


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3): sys.exit(__doc__)
    main(*sys.argv[1:])
