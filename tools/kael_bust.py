#!/usr/bin/env python3
"""Kael's bust and arms from Meshy (11/11/2026: docs/meshy/KAEL.md "Busto da Meshy"), cleaned before it goes on his
bones (Denis: "prima di mettere il busto sulle ossa di kael miglioriamolo al meglio"): Meshy's own paint in the bust
sheet's flat palette, piece by piece, and the skin's shadow (Denis chose "Ombre sulla pelle").

- Input: the decimated GLB (tools/mesh_prep/decimate_glb.py busto_k1.glb busto_k1_30k.glb 30000): its texture and UVs.
- Each texel's piece by Meshy's colour (skin, dark cloth, purple), smoothed on the surface (its thin dark strokes inside
  the skin are the skin's lines); its tone by Meshy's lightness: the cloth's darkest share black as the drawing's share
  (SHARE), the purple's darkest share its shadow, the skin's brown strokes its shadow or ink (SKIN_T).
  (Tried and left: the three views projected onto the model. They overlap it by 85-92% only: the skin's shadows came
  out in fragments and the borders frayed.)
- The tattoos (purple pieces whose rim is mostly skin): purple with a thin rim of its shadow, as the sheet draws them.
- The skin's shadow baked: light from above (SHADE: n . L minus the occlusion's weight), as much of it as the drawing
  shades (14%, fit on the three views: light from above and the hollows matched their shadows best), crumbs under
  SKIN_SMALL mm2 left out.
- Palette (PAL): measured on the three views sent to Meshy (docs/ref/personaggi/kael_busto_senza_code_*.png).
- The arms and the hands (Denis: "ok migliora i disegni sulle braccia e mani"; arms()):
  * cameras on the three views sent to Meshy (fit_cams: yaw, scale and place where the silhouettes overlap most, 85-92%),
    and per near arm and view a turn, scale and shift laying the model's upper-arm skin on the drawing's (fit_arms:
    84-88%; the far arms, half hidden behind the body, are not used); stored in docs/meshy/kael_bust_cams.json (--fit);
  * on the arms' skin seen by a view, the drawing's lines and shadows (its outline at the silhouette left out); the
    model's own tattoos stay (the drawing's fell beside them and broke them); Meshy's dark islands in the skin (cloth
    pieces under ISLE mm2 ringed by skin) skin first;
  * the right shoulder's tattoo the left one mirrored and laid on the right deltoid (ICP on the skin): Meshy had painted it
    in fragments; then the shoulders' leftover bits (under LEFT mm2) skin;
  * the hands (beyond the wrist cuffs, HAND_D): the fingers clean skin, the glove plum with its large shadows black, its
    edges smoothed, no purple past the cuff.
- The thumbs, the gloves and the black borders (Denis: "sistema i pollici che sono buggati e dipingi meglio i bordi neri delle
  dita e del resto"; finish()): the thumbs all skin from their base (THUMB: along the surface from each tip; Meshy had
  left glove across them and skin blobs on the palm beside them: the thumb looked cut in two); the glove's edge over the
  fingers Meshy's smoothed over GLOVE_R (it was frayed), between the thumb and the index the glove, the glove's black only
  in its large folds; on the shoulders the tattoos Meshy painted behind (dark purple with black edges) purple with a rim of
  its shadow, as the back sheet draws them, and its fragments there skin; then the black lines where the sheet draws
  them: between the skin and the cloth or the purple (the gloves' edges, the armholes, the collar), round the sash, the
  bracers' bands and the collar's trim, and between the sash's folds (not round the vest's stripes nor the tattoos; the
  fingers' own outlines are the outline's, as the game draws it).

usage: python3 tools/kael_bust.py IN_30k.glb OUT.glb [--png OUT.png] [--fit]   (--fit: measure the cameras again into CAMS)"""
import io, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
import glbio
import kael_flat as KF
from paint_views import texel_table

TS = 2048                              # the texture's size
SC = .443                              # m per unit of Meshy's GLB (the bust, collar's top to hem, about 0.75 m)
PAL = dict(plum=(65, 49, 74), black=(26, 21, 27), skin=(250, 191, 151), skinS=(164, 112, 85), purple=(166, 92, 203), purpleS=(108, 63, 138), ink=(9, 6, 9))
SHARE = dict(black=.37, purpleS=.21)   # the drawing's: black of the cloth, the shadow of the purple
SKIN_T = (120, 182)                    # Meshy's skin lightness: under [0] ink, under [1] the skin's shadow (its brown strokes only)
SKIN_SMALL = 15.                       # mm2: the skin's shadow pieces under this: skin
SHADE = (0., 60., 1., .144)            # the skin's shadow: light from azimuth [0], elevation [1] (degrees), occlusion's weight [2], its share [3]
AO_DIRS, AO_RES, AO_EPS = 96, 700, .025   # the occlusion: directions, depth maps' size, self-test (GLB units)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
VIEWS = {k: os.path.join(ROOT, 'docs', 'ref', 'personaggi', 'kael_busto_senza_code_%s.png' % k) for k in ('fronte', 'destra', 'sinistra')}
CAMS = os.path.join(ROOT, 'docs', 'meshy', 'kael_bust_cams.json')
YAWS = {'fronte': (-15, 15), 'destra': (-75, -20), 'sinistra': (20, 75)}   # fit_cams: the yaws tried per view
BG = (211, 211, 213)
NEAR_ARMS = (('fronte', -1), ('fronte', 1), ('destra', -1), ('sinistra', 1))   # (view, side): the arms the drawings paint (+1 his left)
FACE_MIN, VIEW_W, VIS_EPS, EDGE = .3, {'fronte': 1., 'destra': .85, 'sinistra': .85}, .012, 5
ISLE, LEFT, HAND_D, GLOVE_SMALL = 400., 60., .925, 25.
ZONE = ((.28, .55), (.38, .78))   # the shoulders: |x|, y (GLB units)
THUMB = (.095, ((-.94, -.585, .035), (.933, -.588, .033)))   # the thumbs: skin within [0] (GLB units, along the surface) of their tips (his right, his left)
LINE, LINE_FOLD, SASH, COLLAR_Y = .003, .0018, (-.32, -.10, .40), .70   # the borders' half widths (GLB units: 1.3 and 0.8 mm); the sash (y from, to, |x| under); the collar's trim over
GLOVE_R, THUMB_WEB, SAMPLE = .027, .12, .04   # the glove's edge: smoothed over [0]; between the thumb and the index (within [1] of its tip) the glove; [2] of the texels sampled
GLOVE_BLACK, EDGE_CLEAR = 15., .008            # the glove's black: pieces over this (mm2) and none within [1] of its edge over the fingers
BACK_BITS, TAT_MAX, TAT_RIM, TAT_PUR = 200., 2500., .55, .15   # the shoulders: fragments behind under [0] mm2 skin; tattoo pieces under [1] mm2, over [2] of their rim skin, over [3] of them purple


def occlusion(P, N, I):
    """Per vertex: the share of AO_DIRS directions (weighted by the normal) from which it is seen."""
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9); Q = P - (P.min(0) + P.max(0)) / 2; R = np.linalg.norm(Q, axis=1).max() * 1.02; S = AO_RES
    i = np.arange(AO_DIRS) + .5; phi = np.arccos(1 - 2 * i / AO_DIRS); th = np.pi * (1 + 5 ** .5) * i
    D = np.c_[np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)]; vis = np.zeros(len(P)); ws = np.zeros(len(P))
    for dv in D:
        up = np.array([0, 1, 0]) if abs(dv[1]) < .9 else np.array([1, 0, 0]); ex = np.cross(up, dv); ex /= np.linalg.norm(ex); ey = np.cross(dv, ex)
        u = (Q @ ex / R * .5 + .5) * (S - 1); v = (Q @ ey / R * -.5 + .5) * (S - 1); z = Q @ dv
        im = Image.new('F', (S, S), -1e9); dr = ImageDraw.Draw(im)
        for t in np.argsort(z[I].mean(1)): a, b, c = I[t]; dr.polygon([(u[a], v[a]), (u[b], v[b]), (u[c], v[c])], fill=float(z[I[t]].mean()))
        Z = np.asarray(im)[np.clip(np.round(v).astype(int), 0, S - 1), np.clip(np.round(u).astype(int), 0, S - 1)]
        w = np.clip(N @ dv, 0, 1); vis += w * (z >= Z - AO_EPS); ws += w
    return vis / np.maximum(ws, 1e-9)


def _ids(P, I, cam):
    """The triangle drawn at each pixel of a view (orthographic camera cam: yaw, s, cx, by, W, H), and the vertices' place and depth."""
    t = np.radians(cam['yaw']); uv = np.c_[cam['cx'] + cam['s'] * (P[:, 0] * np.cos(t) - P[:, 2] * np.sin(t)), cam['by'] - cam['s'] * P[:, 1]]
    dv = P[:, 0] * np.sin(t) + P[:, 2] * np.cos(t); im = Image.new('I', (cam['W'], cam['H']), -1); dr = ImageDraw.Draw(im)
    for q in np.argsort(dv[I].mean(1)): a, b, c = I[q]; dr.polygon([(uv[a, 0], uv[a, 1]), (uv[b, 0], uv[b, 1]), (uv[c, 0], uv[c, 1])], fill=int(q))
    return np.asarray(im), uv, dv


def fit_cams(P, I):
    """Per view: the yaw, scale and place where the model's silhouette overlaps the drawing's most."""
    def mask(uv, W, H):
        im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
        for a, b, c in I: dr.polygon([tuple(uv[a]), tuple(uv[b]), tuple(uv[c])], fill=1)
        return np.asarray(im).astype(bool)
    def proj(yaw, s, cx, by):
        t = np.radians(yaw); return np.c_[cx + s * (P[:, 0] * np.cos(t) - P[:, 2] * np.sin(t)), by - s * P[:, 1]]
    cams = {}
    for k, (y0, y1) in YAWS.items():
        A = np.asarray(Image.open(VIEWS[k]).convert('RGB')).astype(int); F = np.abs(A - BG).max(2) > 14; H, W = F.shape
        ys, xs = np.nonzero(F); fb = (xs.min(), ys.min(), xs.max(), ys.max())
        def place(yaw):
            u = proj(yaw, 1, 0, 0); s = (fb[3] - fb[1]) / np.ptp(u[:, 1]); u = u * s
            return s, (fb[0] + fb[2]) / 2 - (u[:, 0].min() + u[:, 0].max()) / 2, fb[1] - u[:, 1].min()
        def iou(yaw, s, cx, by): M = mask(proj(yaw, s, cx, by), W, H); return (M & F).sum() / (M | F).sum()
        best = None
        for yaw in range(y0, y1 + 1, 5):
            s, cx, by = place(yaw); v = iou(yaw, s, cx, by)
            if best is None or v > best[0]: best = (v, yaw, s, cx, by)
        v, yaw, s, cx, by = best
        for step in (2, 1, .5):
            for _ in range(3):
                for cand in ((yaw + step, s, cx, by), (yaw - step, s, cx, by), (yaw, s * (1 + .005 * step), cx, by), (yaw, s * (1 - .005 * step), cx, by),
                             (yaw, s, cx + 2 * step, by), (yaw, s, cx - 2 * step, by), (yaw, s, cx, by + 2 * step), (yaw, s, cx, by - 2 * step)):
                    vv = iou(*cand)
                    if vv > v: v, (yaw, s, cx, by) = vv, cand
        cams[k] = dict(yaw=float(yaw), s=float(s), cx=float(cx), by=float(by), iou=float(v), W=W, H=H)
        print('camera %-8s yaw %+.1f, overlap %.0f%%' % (k, yaw, 100 * v))
    return cams


def fit_arms(P, I, ks, mat, tat, cams):
    """Per arm and view: the turn, scale and shift (pixels, about the model arm's centre) laying the model's upper-arm skin on the drawing's."""
    sk_t = np.bincount(ks, weights=((mat == 0) | tat).astype(float), minlength=len(I)) > .5 * np.bincount(ks, minlength=len(I))
    C = P[I].mean(1); side = np.sign(C[:, 0]); arm_t = sk_t & (np.abs(C[:, 0]) > .25)
    def warp(M, a, k, tx, ty, cx, cy):
        ys, xs = np.nonzero(M); ca, sa = np.cos(np.radians(a)), np.sin(np.radians(a))
        X = k * (ca * (xs - cx) - sa * (ys - cy)) + cx + tx; Y = k * (sa * (xs - cx) + ca * (ys - cy)) + cy + ty
        out = np.zeros_like(M); ok = (X >= 0) & (X < M.shape[1] - 1) & (Y >= 0) & (Y < M.shape[0] - 1)
        out[np.round(Y[ok]).astype(int), np.round(X[ok]).astype(int)] = True
        return ndimage.binary_closing(out, iterations=1)
    res = {}
    for k, cam in cams.items():
        A = np.asarray(Image.open(VIEWS[k]).convert('RGB')).astype(int); r, g, b = A[..., 0], A[..., 1], A[..., 2]
        S = ((r > 140) & (r - b > 40)) | ((r > 120) & (r - b > 50) & (g > 80)); ID = _ids(P, I, cam)[0]
        for sd in (-1, 1):
            Mm = (ID >= 0) & arm_t[np.maximum(ID, 0)] & (side[np.maximum(ID, 0)] == sd); lab, n = ndimage.label(Mm)
            if n == 0: continue
            Mm = lab == np.argmax(np.bincount(lab.ravel())[1:]) + 1
            if Mm.sum() < 3000: continue
            lb, nb = ndimage.label(S); ov = np.bincount(lb[Mm], minlength=nb + 1); ov[0] = 0; dm = lb == ov.argmax()
            yc, xc = np.argwhere(Mm).mean(0); yd, xd = np.argwhere(dm).mean(0)
            def iou(p): w = warp(Mm, p[0], p[1], p[2], p[3], xc, yc); return (w & dm).sum() / (w | dm).sum()
            best = (iou((0, 1, xd - xc, yd - yc)), (0., 1., xd - xc, yd - yc))
            for step in (4., 2., 1., .5):
                imp = True
                while imp:
                    imp = False; p = best[1]
                    for dp in ((step, 0, 0, 0), (-step, 0, 0, 0), (0, .01 * step, 0, 0), (0, -.01 * step, 0, 0), (0, 0, 2 * step, 0), (0, 0, -2 * step, 0), (0, 0, 0, 2 * step), (0, 0, 0, -2 * step)):
                        q = tuple(np.add(p, dp)); v = iou(q)
                        if v > best[0] + 1e-4: best = (v, q); imp = True
            a, kk, tx, ty = best[1]; res['%s %+d' % (k, sd)] = dict(view=k, side=sd, a=float(a), k=float(kk), tx=float(tx), ty=float(ty), cx=float(xc), cy=float(yc), iou=float(best[0]))
            print('arm %-8s %s: overlap %.0f%%' % (k, 'his left ' if sd > 0 else 'his right', 100 * best[0]))
    return res


def arms(P, I, ys, xs, ks, pos, nor, mat, lab, tat, area, cams, fits, names, cols, ix, jw, okw, ok):
    """The arms' skin from the drawings, the right tattoo mirrored from the left, the shoulders' leftovers, the hands (see the docstring)."""
    from scipy.spatial import cKDTree
    j = jw[:, :KF.KNN - 1]; lab = lab.copy(); mat = mat.copy()
    sk_t = np.bincount(ks, weights=((mat == 0) | tat).astype(float), minlength=len(I)) > .5 * np.bincount(ks, minlength=len(I))
    arm_t = sk_t & (np.abs(P[I].mean(1)[:, 0]) > .25)
    # (Meshy's dark islands in the arms' skin)
    comp = KF._comps(mat, j, ok); nc = comp.max() + 1; ca = np.bincount(comp, weights=area, minlength=nc)
    diff = ok & (comp[j] != comp[:, None]); rr = np.repeat(np.arange(len(mat)), j.shape[1])[diff.ravel()]; qq = j[diff]
    rs = np.bincount(comp[rr], weights=((mat[qq] == 0) | tat[qq]).astype(float), minlength=nc); rn = np.bincount(comp[rr], minlength=nc)
    cm = np.zeros(nc, np.int64); cm[comp] = mat; ax = np.zeros(nc); np.maximum.at(ax, comp, np.abs(pos[:, 0]))
    isl_c = (cm == 1) & (ca < ISLE) & (rs > .6 * np.maximum(rn, 1)) & (ax > .25); isl = isl_c[comp]; mat[isl] = 0; lab[isl] = ix['skin']
    arm_x = arm_t[ks] & ((mat == 0) | tat); sd_x = np.sign(pos[:, 0])
    best = np.full(len(ks), -1.); newl = np.full(len(ks), -1)
    for k, cam in cams.items():
        A = np.asarray(Image.open(VIEWS[k]).convert('RGB')).astype(float)
        bg = np.abs(A - BG).max(2) <= 14; near_bg = ndimage.binary_dilation(bg, iterations=EDGE)
        dc = np.abs(A[..., None, :] - cols[None, None]).max(3).argmin(2); dc[dc == ix['black']] = ix['ink']; dc[near_bg & (dc == ix['ink'])] = -2; dc[bg] = -1
        t = np.radians(cam['yaw']); W, H = cam['W'], cam['H']; ID, uv, dv = _ids(P, I, cam)
        tp = np.c_[cam['cx'] + cam['s'] * (pos[:, 0] * np.cos(t) - pos[:, 2] * np.sin(t)), cam['by'] - cam['s'] * pos[:, 1]]; td = pos[:, 0] * np.sin(t) + pos[:, 2] * np.cos(t)
        px = np.clip(np.round(tp[:, 0]).astype(int), 0, W - 1); py = np.clip(np.round(tp[:, 1]).astype(int), 0, H - 1); fid = ID[py, px]; okp = fid >= 0
        fd = np.full(len(ks), -1e9); f = fid[okp]; Pa, Pb, Pc = uv[I[f, 0]], uv[I[f, 1]], uv[I[f, 2]]; Pp = tp[okp]
        v0 = Pb - Pa; v1 = Pc - Pa; v2 = Pp - Pa; d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01; den[np.abs(den) < 1e-12] = 1e-12; b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den
        fd[okp] = (1 - b1 - b2) * dv[I[f, 0]] + b1 * dv[I[f, 1]] + b2 * dv[I[f, 2]]
        vis = okp & ((fid == ks) | (td >= fd - VIS_EPS)); facing = nor @ np.array([np.sin(t), 0, np.cos(t)])
        for sd in (-1, 1):
            if (k, sd) not in NEAR_ARMS: continue
            F = fits['%s %+d' % (k, sd)]; c_, s_ = np.cos(np.radians(F['a'])), np.sin(np.radians(F['a']))
            sel = arm_x & (sd_x == sd) & vis & (facing > FACE_MIN)
            X = F['k'] * (c_ * (tp[:, 0] - F['cx']) - s_ * (tp[:, 1] - F['cy'])) + F['cx'] + F['tx']; Y = F['k'] * (s_ * (tp[:, 0] - F['cx']) + c_ * (tp[:, 1] - F['cy'])) + F['cy'] + F['ty']
            c = dc[np.clip(np.round(Y).astype(int), 0, H - 1), np.clip(np.round(X).astype(int), 0, W - 1)]
            good = sel & ~tat & np.isin(c, [ix['skin'], ix['skinS'], ix['ink'], ix['purple'], ix['purpleS'], -2])
            c = np.where((c == -2) | (c == ix['purple']) | (c == ix['purpleS']), ix['skin'], c)
            w = np.where(good, facing ** 2 * VIEW_W[k], -1.); bet = w > best; best[bet] = w[bet]; newl[bet] = c[bet]
    got = newl >= 0; lab[got] = newl[got]
    keep = ~arm_x; lab = KF._mode(lab, j, ok, len(names), keep=keep | (lab == ix['ink']))
    KF._small(lab, j, ok, area, np.where(arm_x, np.where(lab == ix['ink'], .8, 4.), 0.), keep)
    print('arms: %d texels from the drawings, %d of dark islands in the skin' % (int(got.sum()), int(isl.sum())))
    # (the right tattoo: the left one mirrored and laid on the right deltoid)
    zone = lambda sd: (np.sign(pos[:, 0]) == sd) & (np.abs(pos[:, 0]) > ZONE[0][0]) & (np.abs(pos[:, 0]) < ZONE[0][1]) & (pos[:, 1] > ZONE[1][0]) & (pos[:, 1] < ZONE[1][1])
    src = np.nonzero(zone(1) & ((mat == 0) | tat))[0]; dst = np.nonzero(zone(-1) & (mat == 0) & ~tat)[0]
    S = pos[src] * [-1, 1, 1]; Sn = nor[src] * [-1, 1, 1]; Rm = np.eye(3); tv = np.zeros(3); D = pos[dst][::4]; tree = cKDTree(D)
    for _ in range(40):
        X = S[::6] @ Rm.T + tv; dd, nn = tree.query(X); kp = dd < np.quantile(dd, .8)
        A_, B_ = X[kp], D[nn[kp]]; ma, mb = A_.mean(0), B_.mean(0); U, _, Vt = np.linalg.svd((A_ - ma).T @ (B_ - mb)); Ri = (U @ Vt).T
        if np.linalg.det(Ri) < 0: Vt[-1] *= -1; Ri = (U @ Vt).T
        Rm = Ri @ Rm; tv = Ri @ tv + (mb - Ri @ ma)
    Sa = S @ Rm.T + tv; San = Sn @ Rm.T; cand = np.nonzero(zone(-1))[0]; dd, nn = cKDTree(Sa).query(pos[cand]); agree = (nor[cand] * San[nn]).sum(1) > .5
    src_edge = tat[src] & (lab[src] == ix['purpleS']); old_t = np.nonzero(tat & (np.sign(pos[:, 0]) == -1))[0]
    dot_ = cKDTree(pos[old_t]).query(pos[cand])[0] if len(old_t) else np.full(len(cand), 9.)
    may = ((mat[cand] == 0) | tat[cand] | ((mat[cand] == 1) & (dot_ < .035))) & (dd < .012) & agree
    m_t = tat[src][nn]; c_ = cand[may]; new = np.where(m_t[may], np.where(src_edge[nn][may], ix['purpleS'], ix['purple']), -1)
    was = tat[c_] | (mat[c_] == 1); lab[c_[new >= 0]] = new[new >= 0]; lab[c_[(new < 0) & was]] = ix['skin']
    print('right tattoo: the left one mirrored (mean gap %.4f), %d texels' % (dd[may].mean() if may.any() else 0, int((new >= 0).sum())))
    # (the shoulders' leftovers)
    skz = (zone(-1) | zone(1)) & ((mat == 0) | tat | (lab == ix['skin']))
    comp2 = KF._comps(lab, j, ok); ca2 = np.bincount(comp2, weights=area); nc2 = len(ca2); inz = np.zeros(nc2); np.add.at(inz, comp2, skz.astype(float)); cnt2 = np.bincount(comp2, minlength=nc2)
    lc = np.zeros(nc2, np.int64); lc[comp2] = lab
    bad = (ca2 < LEFT) & (inz > .5 * cnt2) & np.isin(lc, [ix['purple'], ix['purpleS'], ix['black'], ix['plum'], ix['ink']]); fix = bad[comp2] & skz; lab[fix] = ix['skin']
    # (the hands)
    hand = np.abs(pos[:, 0]) * .8 - pos[:, 1] * .6 > HAND_D; hd = np.abs(pos[:, 0]) * .8 - pos[:, 1] * .6
    m2 = mat.copy(); isk = np.isin(lab, [ix['skin'], ix['skinS'], ix['ink']]); m2[hand & isk] = 0; m2[hand & ~isk & (m2 == 0)] = 1
    for _ in range(4): m2 = np.where(hand, KF._mode(m2, jw, okw, 3), m2)
    KF._small(m2, j, ok, area, np.where(hand, 30., 0.), ~hand); m2[hand & (m2 == 2) & (hd > HAND_D + .02)] = 1
    fing = hand & (m2 == 0); glv = hand & (m2 == 1); cuff = hand & (m2 == 2); lab[fing] = ix['skin']
    gl = lab.copy(); gl[glv & ~np.isin(lab, [ix['black'], ix['plum']])] = ix['plum']; KF._small(gl, j, ok, area, np.where(glv, GLOVE_SMALL, 0.), ~glv)
    for _ in range(3): gl = np.where(glv, KF._mode(gl, jw, okw, len(names)), gl)
    lab[glv] = gl[glv]; lab[cuff & ~np.isin(lab, [ix['purple'], ix['purpleS']])] = ix['purple']
    print('shoulders: %d leftover bits to skin; hands: %d texels of fingers, %d of glove' % (int(bad.sum()), int(fing.sum()), int(glv.sum())))
    return lab


def finish(P, I, ks, bary, pos, nor, lab, tat, area, names, ix, jw, okw, ok):
    """The thumbs, the gloves' edges, the shoulders' tattoos behind and the black borders (see the docstring)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    lab = lab.copy(); tat = tat.copy(); j = jw[:, :KF.KNN - 1]
    hd = np.abs(pos[:, 0]) * .8 - pos[:, 1] * .6; hand = hd > .925
    # 1. the thumbs: geodesic distance from each tip on the welded mesh
    _, wv = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel(); nw = wv.max() + 1; Pw = np.zeros((nw, 3)); Pw[wv] = P
    W = wv[I]; E = np.unique(np.sort(np.concatenate([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]), 1), axis=0); w = np.linalg.norm(Pw[E[:, 0]] - Pw[E[:, 1]], axis=1)
    G = coo_matrix((np.r_[w, w], (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr()
    tips = [np.argmin(np.linalg.norm(Pw - np.array(t), axis=1)) for t in THUMB[1]]
    dtv = dijkstra(G, indices=tips, min_only=True, limit=.3); tri = W[ks]; dtx = (np.where(np.isfinite(dtv[tri]), dtv[tri], 9.) * bary).sum(1)
    thumb = hand & (dtx < THUMB[0])
    lab[thumb] = ix['skin']
    # (the glove's edge on the fingers: Meshy's, smoothed: each hand texel skin where over half of the surface within GLOVE_R
    # (same side) is skin, from SAMPLE of the texels; between the thumb and the index (within THUMB_WEB of the thumb's tip,
    # not the thumb) the glove; the thumbs skin)
    isk = np.isin(lab, [ix['skin'], ix['skinS'], ix['ink']])
    s0 = (hand & isk & (dtx > THUMB_WEB)) | thumb
    hi_ = np.nonzero(hand)[0]; rng = np.random.default_rng(0); smp = hi_[rng.random(len(hi_)) < SAMPLE]
    M = cKDTree(pos[smp]).sparse_distance_matrix(cKDTree(pos[smp]), GLOVE_R, output_type='coo_matrix')
    same = (nor[smp[M.row]] * nor[smp[M.col]]).sum(1) > .2
    fr = np.bincount(M.row[same], weights=s0[smp[M.col[same]]].astype(float), minlength=len(smp)) / np.maximum(np.bincount(M.row[same], minlength=len(smp)), 1)
    dd, nn = cKDTree(pos[smp]).query(pos[hi_], k=16); wgt = np.exp(-(dd / (.35 * GLOVE_R)) ** 2) + 1e-9; val = (fr[nn] * wgt).sum(1) / wgt.sum(1)   # (smooth: Gaussian over 16 samples)
    skin_h = np.zeros(len(lab), bool); skin_h[hi_] = val > .5; skin_h |= thumb; skin_h &= ~(hand & (dtx < THUMB_WEB) & ~thumb)
    # (the skin's specks on the glove and the glove's in the skin: pieces under 25 mm2 the other)
    sh_ = np.where(hand, skin_h.astype(int), 2); KF._small(sh_, j, ok, area, np.where(hand, 25., 0.), ~hand)
    for _ in range(2): sh_ = np.where(hand, KF._mode(sh_, j, ok, 3, keep=~hand), sh_)
    skin_h = hand & (sh_ == 1)
    fingers = hand & skin_h; glove = hand & ~skin_h
    stray = glove & isk
    lab[fingers] = ix['skin']; lab[stray] = ix['plum']
    lab[glove & ~np.isin(lab, [ix['plum'], ix['black'], ix['purple'], ix['purpleS']])] = ix['plum']
    # (purple bits on the hands past the cuffs, under 100 mm2: plum)
    pc = KF._comps(lab, j, ok); pa = np.bincount(pc, weights=area); pl = np.zeros(len(pa), np.int64); pl[pc] = lab
    pin = np.zeros(len(pa)); np.add.at(pin, pc, hand.astype(float)); pn = np.bincount(pc)
    pb = (pa < 100) & np.isin(pl, [ix['purple'], ix['purpleS']]) & (pin > .5 * pn); lab[pb[pc] & hand] = ix['plum']
    print('thumbs: %d texels skin; fingers %d; hands: %d stray skin texels and %d purple bits to the glove' % (int(thumb.sum()), int(fingers.sum()), int(stray.sum()), int((pb[pc] & hand).sum())))
    for _ in range(2): lab = np.where(glove, KF._mode(lab, jw, okw, len(names), keep=~glove), lab)
    # (the glove's black: its large folds only (pieces over GLOVE_BLACK mm2), none within EDGE_CLEAR of its edge over the fingers:
    # beside the edge's line it frayed it, and Meshy's dashes across the back are gone)
    gb = np.where(glove, np.where(lab == ix['black'], 1, 0), 2); KF._small(gb, j, ok, area, np.where(glove & (gb == 1), GLOVE_BLACK, 0.), ~glove)
    lab[glove & (gb == 0) & (lab == ix['black'])] = ix['plum']
    # (the shoulders' tattoos as Meshy painted them behind, dark purple with black edges: on the shoulders, the pieces of purple,
    # its shadow, black or ink lying in the skin (over TAT_RIM of their rim skin, under TAT_MAX mm2) are tattoos: purple, a rim of
    # its shadow, no ink (as the clean V in front)
    zoneS = (np.abs(pos[:, 0]) > .28) & (np.abs(pos[:, 0]) < .55) & (pos[:, 1] > .38) & (pos[:, 1] < .78)
    nonsk = zoneS & np.isin(lab, [ix['purple'], ix['purpleS'], ix['black'], ix['ink'], ix['plum']])
    tc = KF._comps(np.where(nonsk, 1, 0), j, ok); ta = np.bincount(tc, weights=area); ntc = len(ta)
    dif = ok & (tc[j] != tc[:, None]); r_ = np.repeat(np.arange(len(lab)), j.shape[1])[dif.ravel()]; q_ = j[dif]
    rsk = np.bincount(tc[r_], weights=np.isin(lab[q_], [ix['skin'], ix['skinS']]).astype(float), minlength=ntc); rnn = np.bincount(tc[r_], minlength=ntc)
    isn = np.zeros(ntc, bool); np.logical_or.at(isn, tc, nonsk)
    pur = np.bincount(tc, weights=(np.isin(lab, [ix['purple'], ix['purpleS']]) & nonsk).astype(float) * area, minlength=ntc)
    tt_c = isn & (ta > 20.) & (ta < TAT_MAX) & (rsk > TAT_RIM * np.maximum(rnn, 1)) & (pur > TAT_PUR * ta); tt2 = tt_c[tc] & nonsk   # (some purple in it: not a crease's shadow)
    rim2 = tt2 & np.where(ok, ~tt2[j], False).any(1)
    lab[tt2] = ix['purple']; lab[rim2] = ix['purpleS']; tat = tat | tt2
    print('shoulders: %d tattoo pieces (%d texels) as the sheet\'s, purple with its shadow\'s rim' % (int(tt_c.sum()), int(tt2.sum())))
    # (the shoulders' backs: Meshy's purple and black fragments there (pieces under BACK_BITS mm2 on the back-facing deltoid skin,
    # normal's z under -0.15) skin; the tattoo seen from behind is the clean V's outer side, as the back sheet draws it)
    backS = zoneS & (nor[:, 2] < -.15)
    pc2 = KF._comps(lab, j, ok); pa2 = np.bincount(pc2, weights=area); pl2 = np.zeros(len(pa2), np.int64); pl2[pc2] = lab
    inb = np.zeros(len(pa2)); np.add.at(inb, pc2, backS.astype(float)); pn2 = np.bincount(pc2)
    tat_any = np.zeros(len(pa2), bool); np.logical_or.at(tat_any, pc2, tat)
    frag = ~tat_any & (pa2 < BACK_BITS) & (inb > .5 * pn2) & np.isin(pl2, [ix['purple'], ix['purpleS'], ix['black'], ix['ink']])
    fx = frag[pc2] & zoneS; lab[fx] = ix['skin']; tat = tat & ~fx
    print('shoulders\' backs: %d fragments (%d texels) to skin' % (int(frag.sum()), int(fx.sum())))
    # 2. the black borders
    S_ = np.isin(lab, [ix['skin'], ix['skinS'], ix['ink']]) & ~tat
    C_ = np.isin(lab, [ix['plum'], ix['black']])
    U_ = np.isin(lab, [ix['purple'], ix['purpleS']]) & ~tat
    sash = (np.abs(pos[:, 0]) < SASH[2]) & (pos[:, 1] > SASH[0]) & (pos[:, 1] < SASH[1])
    cuffs = np.abs(pos[:, 0]) > .3; collar = (pos[:, 1] > COLLAR_Y) & (np.abs(pos[:, 0]) < .2)
    Ub = U_ & (sash | cuffs | collar)    # (the purple parts with their own outline: the sash, the bracers' bands, the collar's trim; not the vest's stripes)
    def near(a, b, r):
        """a's texels within r (GLB units) of a b texel on the same side of the surface."""
        ai, bi = np.nonzero(a)[0], np.nonzero(b)[0]
        if not len(ai) or not len(bi): return np.zeros(len(a), bool)
        dd, nn = cKDTree(pos[bi]).query(pos[ai], distance_upper_bound=r); okk = np.isfinite(dd)
        okk[okk] &= (nor[ai[okk]] * nor[bi[nn[okk]]]).sum(1) > .3
        out = np.zeros(len(a), bool); out[ai[okk]] = True; return out
    lab[near(glove & (lab == ix['black']), fingers | thumb, EDGE_CLEAR)] = ix['plum']
    C_ = np.isin(lab, [ix['plum'], ix['black']])
    ink = near(S_, C_ | U_, LINE) | near(C_ | U_, S_, LINE) | near(Ub, C_, LINE) | near(C_, Ub, LINE)
    fold = sash & (near(U_ & (lab == ix['purple']), lab == ix['purpleS'], LINE_FOLD))
    lab[ink | fold] = ix['ink']   # (between the fingers: the outline draws them; painted in the hollows they were black wedges)
    KF._small(lab, j, ok, area, np.where(lab == ix['ink'], .6, 0.), np.zeros(len(lab), bool))
    print('borders: %d texels of ink (%d on the sash\'s folds)' % (int((lab == ix['ink']).sum()), int(fold.sum())))
    return lab


def main(src, dst, png=None, fit=False):
    m = glbio.read(src); P, N, UV, I = m['pos'], m['nor'], m['uv'], m['idx']
    T = np.asarray(Image.open(io.BytesIO(m['img'])).convert('RGB').resize((TS, TS), Image.LANCZOS)).astype(float)
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, TS); nor = nor / np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    names = list(PAL); cols = np.array([PAL[k] for k in names], float); ix = {k: i for i, k in enumerate(names)}
    KF.prepare(P * SC, I); cnt = np.bincount(ks, minlength=len(I)).astype(float); area = KF.TRI_AREA[ks] * 1e6 / np.maximum(cnt[ks], 1)
    jw, okw, ok = KF._graph(pos * SC, nor.astype(np.float32), np.sqrt(area) * 1e-3); j = jw[:, :KF.KNN - 1]
    mey = T[ys, xs]; r, g, b = mey[:, 0], mey[:, 1], mey[:, 2]; L = mey.mean(1)
    # the pieces: 0 skin, 1 dark cloth, 2 purple
    mat = np.ones(len(ks), np.int64); mat[(r > 150) & (r - b > 35)] = 0; mat[(b > 95) & (b - g > 55) & ~(mat == 0)] = 2
    lines = (mat == 1) & (KF._mode(mat, j, ok, 3, own=0) == 0); mat[lines] = 0
    for _ in range(2): mat = KF._mode(mat, jw, okw, 3, keep=lines)
    KF._small(mat, j, ok, area, np.full(len(ks), 30.), np.zeros(len(ks), bool))
    # the tones
    lab = np.zeros(len(ks), np.int64); brown = (r - b > 55) & (b - g < 40)
    s = mat == 0; lab[s] = np.where((L[s] < SKIN_T[0]) & brown[s], ix['ink'], np.where((L[s] < SKIN_T[1]) & brown[s], ix['skinS'], ix['skin']))
    s = mat == 1; lab[s] = np.where(L[s] < np.quantile(L[s], SHARE['black']), ix['black'], ix['plum'])
    s = mat == 2; lab[s] = np.where(L[s] < np.quantile(L[s], SHARE['purpleS']), ix['purpleS'], ix['purple'])
    # the tattoos
    comp = KF._comps(mat, j, ok); nc = comp.max() + 1
    diff = ok & (comp[j] != comp[:, None]); rr = np.repeat(np.arange(len(mat)), j.shape[1])[diff.ravel()]; qq = j[diff]
    rim_sk = np.bincount(comp[rr], weights=(mat[qq] == 0).astype(float), minlength=nc); rim_n = np.bincount(comp[rr], minlength=nc)
    cm = np.zeros(nc, np.int64); cm[comp] = mat; tat_c = (cm == 2) & (rim_sk > .6 * np.maximum(rim_n, 1)); tat = tat_c[comp]
    edge = tat & np.where(ok, mat[j] != 2, False).any(1); edge |= tat & np.where(ok, edge[j], False).any(1)
    lab[tat] = ix['purple']; lab[edge] = ix['purpleS']
    print('pieces: skin %.1f%%, cloth %.1f%%, purple %.1f%%; tattoos: %d pieces' % (*(100 * np.bincount(mat, minlength=3) / len(mat)), int(tat_c.sum())))
    # the skin's shadow
    ao = occlusion(P, N, I)[cKDTree(P).query(pos)[1]]
    az, el = np.radians(SHADE[0]), np.radians(SHADE[1]); Lv = np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])
    sc = nor @ Lv - SHADE[2] * (1 - ao); sk = (mat == 0) & ~tat; tau = np.quantile(sc[sk], SHADE[3])
    lab[sk & (lab == ix['skin']) & (sc < tau)] = ix['skinS']
    nl = len(names)
    for _ in range(5): lab = KF._mode(lab, jw, okw, nl, keep=(lab == ix['ink']) | tat | (mat != 0))
    for _ in range(2): lab = KF._mode(lab, j, ok, nl, keep=(lab == ix['ink']) | tat)
    KF._small(lab, j, ok, area, np.where(lab == ix['ink'], 1.5, np.where(lab == ix['skinS'], SKIN_SMALL, 10.)), tat)
    print('  '.join('%s %.1f%%' % (n, 100 * (lab == i).mean()) for i, n in enumerate(names)))
    if fit or not os.path.exists(CAMS):
        cams = fit_cams(P, I); fits = fit_arms(P, I, ks, mat, tat, cams)
        json.dump({'_': 'tools/kael_bust.py --fit: the three views\' cameras (orthographic: u = cx + s (x cos yaw - z sin yaw), v = by - s y, GLB units) and per near arm a turn (a, degrees), scale (k) and shift (tx, ty px) about (cx, cy) laying its skin on the drawing\'s',
                   'cams': cams, 'arms': fits}, open(CAMS, 'w'), indent=1)
    cj = json.load(open(CAMS)); lab = arms(P, I, ys, xs, ks, pos, nor, mat, lab, tat, area, cj['cams'], cj['arms'], names, cols, ix, jw, okw, ok)
    lab = finish(P, I, ks, bary, pos, nor, lab, tat, area, names, ix, jw, okw, ok)
    if os.environ.get('KAEL_BUST_DUMP'): np.savez(os.environ['KAEL_BUST_DUMP'], ys=ys, xs=xs, ks=ks, bary=bary, pos=pos, nor=nor, mat=mat, lab=lab, tat=tat, mey=mey, area=area)
    out = np.zeros((TS, TS, 3)); cov = np.zeros((TS, TS), bool); out[ys, xs] = cols[lab]; cov[ys, xs] = True
    _, (iy, jx) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], jx[~cov]]
    im = Image.fromarray(out.round().astype(np.uint8)); bio = io.BytesIO(); im.save(bio, 'PNG', optimize=True)
    if png: im.save(png)
    glbio.write(dst, m, P, N, UV, I, img=bio.getvalue(), mime='image/png'); print('written', dst)


if __name__ == '__main__':
    av = sys.argv[1:]; png = None; fit = '--fit' in av; av = [a for a in av if a != '--fit']
    if '--png' in av: k = av.index('--png'); png = av[k + 1]; av = av[:k] + av[k + 2:]
    if len(av) != 2: sys.exit(__doc__)
    main(av[0], av[1], png, fit)
