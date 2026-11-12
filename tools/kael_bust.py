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
  * Kael's own hands (beyond the wrist cuffs, HAND_D; since 11/11 only what the cut leaves of them, Ren's below): the
    fingers clean skin, the glove plum with its large shadows black, its edges smoothed, no purple past the cuff.
- The arms' muscles traced (muscle_lines): thin ink lines in the middle of the valleys between the muscles, as the sheet
  traces them (Denis, 12/11: "ricalca anche i muscoli delle braccia").
- Ren's hands in place of Kael's (Denis, 11/11: "ora rendi quelle mani simili come quelli di ren"; ren_hands()): Kael's
  hand cut past his cuff, Ren's (assets/ren, past his wrist band) laid on it by a similarity fit on the wrist and the five
  tips, its wrist blended onto the cut and the two rings zipped (the seam's triangles turned as their neighbours), the
  wrist then as wide as the cuff's band (WRIST: 32%, fading over the palm's base; the sheet's glove leaves the cuff that wide); a new
  UV atlas (xatlas, unwrap()). On them Ren's paint: his skin and his lines (the skin's shadow where his paint is darker
  than REN_LINE, softened a little; bits under REN_SMALL mm2 left out), and the sheet's fingerless glove (glove_of(),
  glove_texels()): plain plum over the palm up to a straight edge GLOVE_M under the fingers' webs (the webs found where
  the fingers part going down from the tips), on the back of the hand DORSAL nearer the wrist (Denis, 11/11, on the fists:
  "sono deformi": the edge lay on the knuckles' fold and broke into a crown of points in the fist; now the knuckles are bare), the thumb bare with its base as in Ren's fist (THUMB_W: where his skin moves with the thumb's bones; from a ring at its web, THUMB_RING, its skin cut by the glove along its stretched base read as a blade in the fist), the edge
  smoothed; under the cuffs, where Kael's hand was, Meshy's black and small purple islands the glove's plum.
- The gloves and the black borders (Denis: "sistema i pollici che sono buggati e dipingi meglio i bordi neri delle
  dita e del resto"; finish()): what is left of Kael's own hands the glove's plum; on the shoulders the tattoos Meshy
  painted behind (dark purple with black edges) purple with a rim of its shadow, as the back sheet draws them, and its
  fragments there skin; then the black lines where the sheet draws
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
REN = os.path.join(ROOT, 'assets', 'ren', 'ren.json'), os.path.join(ROOT, 'viewer_assets', 'ren', 'ren_painted.jpg')   # Ren's package and paint
KAEL_TIPS = {-1: ((-.941, -.57, .004), ((-.739, -.847, .057), (-.829, -.84, .059), (-.653, -.797, .075), (-.892, -.788, .084))),
             1: ((.933, -.588, .033), ((.823, -.84, .085), (.734, -.841, .073), (.654, -.795, .076), (.885, -.785, .092)))}   # per hand (-1 his right): the thumb's and the fingers' tips (GLB units)
WRIST = (0., .05, .07)   # the glove's wrist pushed out by [0] from the seam, fading from [1] over [2] past the cut (GLB units)
CUT_K, CUT_R, BLEND, GAP = .015, .022, .05, .006   # the cut: Kael's past his cuff's edge (GLB units), Ren's past his hand bone (m); the wrist's blend; the seam's width
MUSCLE = (20, 6, .008, .002)   # the arms' muscles' lines (muscle_lines): the smoothing for the valleys, for their middle; the thresholds
FINGER_LINE = (.985, 2., 0.)   # the fingers' lines (finger_lines): the sides' ink over [0], their shadow over [1] (2: none); the joints' creases within [2] GLB units (0: none, they read as dashes across the fingers)
THUMB_RING = float(os.environ.get('KAEL_THUMB_RING', 0.))   # GLB units: the thumb bare from a ring square to it so far past its web (the sheet's glove: the thumb out of it where it leaves the palm; Denis, 12/11: "il pollice è ancora fatto male": bare along the surface from its tip up to its web, its outer side's skin ran on down its base, in the fist a long blade)
REN_PAINT = int(os.environ.get('KAEL_REN_PAINT', 1))   # the hands' skin in Ren's own paint (1) or the palette's flat skin with lines (0)
THUMB_W = float(os.environ.get('KAEL_THUMB_W', .5))   # the thumb bare with its base as in Ren's fist: where his skin follows the thumb's bones by more than this (0: from the ring, THUMB_RING)
THUMB_W_VSMOOTH = int(os.environ.get('KAEL_THUMB_W_VSMOOTH', 4))   # rounds of smoothing of those weights over the mesh before the cut
THUMB_W_SMOOTH = int(os.environ.get('KAEL_THUMB_W_SMOOTH', 0))   # and over the texels (tried 60: the teeth stayed; 200: the glove took most of the thumb)
THUMB_SPAN = float(os.environ.get('KAEL_THUMB_SPAN', .03))   # GLB units: the thumb's skin along the surface from its tip up to its web and this much more (where the ring is nearer, the ring its edge)
DORSAL = (.035, .025)   # the glove's edge on the back of the hand this much nearer the wrist (GLB units, 1.5 cm), blended over the hand's half thickness [1]
GLOVE_M, THUMB_M, SMOOTH, REN_LINE, REN_SMALL, GLOVE_SMOOTH = .02, .005, 30, (110, 110), 5., 4   # Ren's hands: the glove's edge under the webs, the thumb bare up to [1] short of its web; the distance's smoothing; his lines: ink, shadow under these lightnesses (the same: no painted shadow, the game's light draws it; Ren's painted wrinkles were brown blotches on the fists), their bits under [4] mm2 skin; the glove's edge smoothed [5] times (the glove plain plum: the light's black on it came out in blotches)
CLOTH = (48, 33, 59)                              # the glove's colour as Meshy's dark cloth (then it is the vest's plum)
LINE, LINE_FOLD, SASH, COLLAR_Y = .003, .0018, (-.32, -.10, .40), .70   # the borders' half widths (GLB units: 1.3 and 0.8 mm); the sash (y from, to, |x| under); the collar's trim over
GLOVE_BLACK, EDGE_CLEAR, UNDER_CUFF = 15., .008, .045           # the glove's black: pieces over this (mm2) and none within [1] of its edge over the fingers
BACK_BITS, TAT_MAX, TAT_RIM, TAT_PUR = 200., 2500., .55, .15   # the shoulders: fragments behind under [0] mm2 skin; tattoo pieces under [1] mm2, over [2] of their rim skin, over [3] of them purple


def _weld(P):
    _, wv = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True); return wv.ravel()


def _graph(P, I):
    from scipy.sparse import coo_matrix
    wv = _weld(P); nw = wv.max() + 1; Pw = np.zeros((nw, 3)); Pw[wv] = P; W = wv[I]
    E = np.unique(np.sort(np.concatenate([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]), 1), axis=0); w = np.linalg.norm(Pw[E[:, 0]] - Pw[E[:, 1]], axis=1)
    return wv, Pw, W, E, coo_matrix((np.r_[w, w], (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr()


def _loops(Tri, wv):
    """The boundary loops of a triangle set (welded ids, in order)."""
    W = wv[Tri]; E = np.concatenate([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]])
    _, inv, c = np.unique(np.sort(E, 1), axis=0, return_inverse=True, return_counts=True); nxt = {}
    for a, b in E[c[inv.ravel()] == 1]: nxt.setdefault(a, []).append(b)
    seen, out = set(), []
    for a0 in list(nxt):
        if a0 in seen: continue
        lp = [a0]; seen.add(a0); cur = a0
        while True:
            nb = [x for x in nxt.get(cur, []) if x not in seen]
            if not nb: break
            cur = nb[0]; lp.append(cur); seen.add(cur)
        out.append(lp)
    return out


def ren_hands(P, N, UV, I, cloth_v):
    """Ren's hands in place of Kael's (Denis, 11/11: "ora rendi quelle mani simili come quelli di ren"): Kael's hand past CUT_K
    beyond his cuff out (its part joined to the fingertips); Ren's hand past CUT_R beyond his hand bone (his wrist band left
    out) placed on Kael's by a similarity (rotation, scale, shift) fit on the wrist's centre (weight 4), the thumb's and the four
    fingers' tips; its wrist blended (over BLEND) onto a ring GAP past Kael's cut, the two rings zipped. Returns the new positions,
    normals, triangles, per vertex the source UV and whether it is Ren's, per triangle its source (0 Kael's paint, 1 Ren's, 2 the
    seam), and per hand the cut's ring, Ren's thumb tip."""
    import json as _j
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra, connected_components
    rj = _j.load(open(REN[0])); RB = open(REN[0][:-4] + 'bin', 'rb').read(); rm = rj['mesh']
    rf = lambda a, dt=np.float32: np.frombuffer(RB, dt, a[1], a[0])
    RP = rf(rm['pos']).reshape(-1, 3).astype(float); RUV = rf(rm['uv']).reshape(-1, 2).astype(float)
    RI = rf(rm['idx'], np.uint16 if rm['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    def qm(q):
        x, y, z, w = q; return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    Wm = {}
    for i, bn in enumerate(rj['bones']):
        M = np.eye(4); M[:3, :3] = qm(bn['q']); M[:3, 3] = bn['t']; Wm[i] = (Wm[bn['p']] @ M) if bn['p'] >= 0 else M
    rn = [bn['n'] for bn in rj['bones']]
    kwv, kPw, kW, kE, kG = _graph(P, I); rwv, rPw, rW, rE, rG = _graph(RP, RI)
    hdw = np.abs(kPw[:, 0]) * .8 - kPw[:, 1] * .6; kcl = np.zeros(len(kPw), bool); kcl[kwv[cloth_v[0]]] = True; kpu = np.zeros(len(kPw), bool); kpu[kwv[cloth_v[1]]] = True
    keep = np.ones(len(I), bool); hands = []
    for sd, side in ((-1, 'Right'), (1, 'Left')):
        s_ = np.sign(kPw[:, 0]) == sd
        cuff = s_ & kpu & (hdw > .80) & (hdw < .97); glove = s_ & kcl & (hdw > .88)
        ci = np.nonzero(cuff)[0]; dd, _ = cKDTree(kPw[glove]).query(kPw[ci], distance_upper_bound=.01); edge = ci[np.isfinite(dd)]
        Hc = kPw[s_ & (hdw > .97)].mean(0); e_c = kPw[edge].mean(0)
        _, _, Vt = np.linalg.svd(kPw[edge] - e_c, full_matrices=False); ax = Vt[2] * np.sign(Vt[2] @ (Hc - e_c))
        tK = (kPw - e_c) @ ax; cut = np.percentile(tK[edge], 90) + CUT_K; c0 = e_c + ax * cut
        cand = s_ & (tK > cut); idx = np.nonzero(cand)[0]; mp = -np.ones(len(kPw), int); mp[idx] = np.arange(len(idx)); e_ = kE[cand[kE[:, 0]] & cand[kE[:, 1]]]
        _, lab = connected_components(coo_matrix((np.ones(len(e_)), (mp[e_[:, 0]], mp[e_[:, 1]])), shape=(len(idx), len(idx))), directed=False)
        tipv = np.argmin(np.linalg.norm(kPw - np.array(KAEL_TIPS[sd][1][0]), axis=1)); hv = np.zeros(len(kPw), bool); hv[idx[lab == lab[mp[tipv]]]] = True
        keep &= ~hv[kW].any(1)
        # Ren's hand
        hb = Wm[rn.index(side + 'Hand')][:3, 3]; fa = Wm[rn.index(side + 'ForeArm')][:3, 3]; rax = (hb - fa) / np.linalg.norm(hb - fa)
        tR = (rPw - hb) @ rax; rR = np.linalg.norm((rPw - hb) - np.outer(tR, rax), axis=1)
        hR = (tR > CUT_R) & (rR < .12) & (np.sign(rPw[:, 0]) == sd); triR = np.nonzero(hR[rW].all(1))[0]
        vs = np.unique(rW[triR]); mp = -np.ones(len(rPw), int); mp[vs] = np.arange(len(vs)); e_ = rE[np.isin(rE[:, 0], vs) & np.isin(rE[:, 1], vs)]
        _, lab = connected_components(coo_matrix((np.ones(len(e_)), (mp[e_[:, 0]], mp[e_[:, 1]])), shape=(len(vs), len(vs))), directed=False)
        inb = np.zeros(len(rPw), bool); inb[vs[lab == np.argmax(np.bincount(lab))]] = True; triR = triR[inb[rW[triR]].all(1)]
        ringR = np.array(max(_loops(RI[triR], rwv), key=len)); reg = np.zeros(len(rPw), bool); reg[np.unique(rW[triR])] = True
        dist = dijkstra(rG, indices=ringR, min_only=True); nb = [[] for _ in range(len(rPw))]; Gc = rG.tocoo()
        for a, b in zip(Gc.row, Gc.col): nb[a].append(b)
        cands = []
        for v in np.nonzero(reg & np.isfinite(dist))[0]:
            rg_ = {v}; fr = {v}
            for _ in range(3): fr = {u for x in fr for u in nb[x]} - rg_; rg_ |= fr
            if dist[v] >= max(dist[u] for u in rg_ if np.isfinite(dist[u])): cands.append(v)
        cands = sorted(cands, key=lambda v: -dist[v]); tips = []
        for v in cands:
            if all(np.linalg.norm(rPw[v] - rPw[t_]) > .075 * dist[cands[0]] for t_ in tips): tips.append(v)
            if len(tips) == 5: break
        th = min(tips, key=lambda v: dist[v]); fing = sorted([v for v in tips if v != th], key=lambda v: np.linalg.norm(rPw[v] - rPw[th]))
        srcL = np.array([rPw[ringR].mean(0), rPw[th]] + [rPw[v] for v in fing])
        thK = np.array(KAEL_TIPS[sd][0]); fK = sorted(KAEL_TIPS[sd][1], key=lambda q: np.linalg.norm(np.array(q) - thK))
        dstL = np.array([c0, thK] + [np.array(q) for q in fK]); wts = np.array([4., 1, 1, 1, 1, 1])
        mu_s = (wts[:, None] * srcL).sum(0) / wts.sum(); mu_d = (wts[:, None] * dstL).sum(0) / wts.sum()
        Xs = (srcL - mu_s) * np.sqrt(wts)[:, None]; Xd = (dstL - mu_d) * np.sqrt(wts)[:, None]
        U, S_, Vt2 = np.linalg.svd(Xs.T @ Xd); D_ = np.eye(3); D_[2, 2] = np.sign(np.linalg.det(Vt2.T @ U.T)); R = Vt2.T @ D_ @ U.T
        sc = (S_ * np.diag(D_)).sum() / (Xs ** 2).sum(); tf = lambda X, sc=sc, mu_s=mu_s, R=R, mu_d=mu_d: sc * (X - mu_s) @ R.T + mu_d
        sim = dict(sc=sc, mu_s=mu_s, R=R, mu_d=mu_d)
        hands.append(dict(sd=sd, side=side, c0=c0, ax=ax, triR=triR, ringR=ringR, tf=tf, sim=sim, thumb=tf(rPw[th])[None][0], tips=tf(rPw[[th] + fing]), err=np.linalg.norm(tf(srcL) - dstL, axis=1)))
        print("hands: %s: Ren's scaled %.2f, landmarks off by %s (GLB units); Kael's hand out: %d vertices" % (side, sc, np.round(hands[-1]['err'], 3), int(hv.sum())))
    Ik = I[keep]; lpsK = _loops(Ik, kwv)
    rep = {}
    for t_ in Ik:
        for x in t_: rep.setdefault(kwv[x], x)
    Ps, Ns, UVs, Ts, Ss, Rs = [P], [N], [UV], [Ik], [np.zeros(len(Ik), np.int8)], [np.zeros(len(P), bool)]; off = len(P)
    Ids = [np.full(len(P), -1)]
    for h in hands:
        c0, ax = h['c0'], h['ax']; lk = min(lpsK, key=lambda l: np.linalg.norm(kPw[l].mean(0) - c0)); h['ring'] = kPw[lk]
        u = np.cross(ax, [0, 0, 1.]); u /= np.linalg.norm(u); v = np.cross(ax, u); ang = lambda X: np.arctan2((X - c0) @ v, (X - c0) @ u)
        aK = ang(kPw[lk]); o = np.argsort(aK); aKs, pKs = aK[o], kPw[lk][o]
        per = lambda a, xs_, ys_: np.column_stack([np.interp(a, np.r_[xs_ - 2 * np.pi, xs_, xs_ + 2 * np.pi], np.r_[ys_[:, k], ys_[:, k], ys_[:, k]]) for k in range(3)])
        vs = np.unique(RI[h['triR']]); Q = h['tf'](RP[vs]); mpR = -np.ones(len(RP), int); mpR[vs] = np.arange(len(vs))
        rr0 = h['tf'](rPw[h['ringR']]); aR = ang(rr0); dR = per(aR, aKs, pKs) + ax * GAP - rr0; oR = np.argsort(aR)
        t0 = ((rr0 - c0) @ ax).mean(); w = np.clip(1 - ((Q - c0) @ ax - t0) / BLEND, 0, 1); w = w * w * (3 - 2 * w)
        Q = Q + per(ang(Q), aR[oR], dR[oR]) * w[:, None]
        for k_, wvid in enumerate(h['ringR']): Q[rwv[vs] == wvid] = rr0[k_] + dR[k_]
        # (the glove's wrist as wide as the sheet draws it under the cuff (Denis, 11/11: the fists "sono da migliorare nettamente
        # guarda le sue immagini di riferimento"): Ren's wrist was 70-75% of the cuff's band, the sheet's nearly all of it: pushed out
        # from the axis by WRIST[0] from just past the seam, fading to nothing over the palm's base)
        tq = (Q - c0) @ ax; rad = (Q - c0) - np.outer(tq, ax); sm = lambda x: (lambda u: u * u * (3 - 2 * u))(np.clip(x, 0, 1))
        kq = 1 + WRIST[0] * sm((tq - GAP - .002) / .01) * (1 - sm((tq - WRIST[1]) / WRIST[2]))
        Q = c0 + np.outer(tq, ax) + rad * kq[:, None]
        Ps.append(Q); Ns.append(np.zeros_like(Q)); UVs.append(RUV[vs]); Ts.append(mpR[RI[h['triR']]] + off); Ss.append(np.ones(len(h['triR']), np.int8)); Rs.append(np.ones(len(Q), bool))
        Ids.append(vs)
        kA = [rep[w_] for w_ in lk]; rA = [int(np.nonzero(rwv[vs] == wvid)[0][0]) + off for wvid in h['ringR']]
        def order(ids, a):
            i0 = int(np.argmin(a)); ids = ids[i0:] + ids[:i0]; a = np.r_[a[i0:], a[:i0]]; un = np.unwrap(a)
            if un[-1] < un[0]: ids = [ids[0]] + ids[1:][::-1]; un = np.unwrap(np.r_[a[0], a[1:][::-1]])
            return ids, un - un[0]
        kI, kU = order(kA, ang(kPw[lk])); rI_, rU = order(rA, aR); rU = rU + (aR[np.argmin(aR)] - aK[np.argmin(aK)]) * 0
        allp = lambda i: P[i] if i < len(P) else Q[i - off]
        kUe = np.r_[kU, 2 * np.pi]; rUe = np.r_[rU, 2 * np.pi]; tris = []; i = j = 0; nk, nr = len(kI), len(rI_)
        while i < nk or j < nr:
            if j >= nr or (i < nk and kUe[i + 1] <= rUe[j + 1]): tris.append([kI[i], kI[(i + 1) % nk], rI_[j % nr]]); i += 1
            else: tris.append([kI[i % nk], rI_[(j + 1) % nr], rI_[j]]); j += 1
        tris = np.array(tris)
        for t_ in tris:
            a_, b_, c_ = (allp(x) for x in t_); cen = (a_ + b_ + c_) / 3; rad = (cen - c0) - ((cen - c0) @ ax) * ax
            if np.cross(b_ - a_, c_ - a_) @ rad < 0: t_[1], t_[2] = t_[2], t_[1]
        Ts.append(tris); Ss.append(np.full(len(tris), 2, np.int8)); off += len(Q)
    P2 = np.concatenate(Ps); I2 = np.concatenate(Ts); src = np.concatenate(Ss); isR = np.concatenate(Rs)
    # (the seam's triangles turned as their neighbours: each shared edge run the other way)
    wz = _weld(P2)
    for _ in range(20):
        Wd = wz[I2]; E_ = np.concatenate([Wd[:, [0, 1]], Wd[:, [1, 2]], Wd[:, [2, 0]]]); tri = np.tile(np.arange(len(I2)), 3)
        key = E_[:, 0] * (wz.max() + 1) + E_[:, 1]; rkey = E_[:, 1] * (wz.max() + 1) + E_[:, 0]
        uk, cnt = np.unique(key, return_counts=True); dup = cnt[np.searchsorted(uk, key)] > 1; opp = np.isin(rkey, uk)
        bad = np.bincount(tri, weights=dup.astype(float), minlength=len(I2)); good = np.bincount(tri, weights=(opp & ~dup).astype(float), minlength=len(I2))
        flip = (src == 2) & (bad > good)
        if not flip.any(): break
        I2[flip] = I2[flip][:, [0, 2, 1]]
    print('seam: %d edges still run the same way' % int(dup.sum() // 2))
    wv2 = _weld(P2); fn = np.cross(P2[I2[:, 1]] - P2[I2[:, 0]], P2[I2[:, 2]] - P2[I2[:, 0]]); Nw = np.zeros((wv2.max() + 1, 3)); np.add.at(Nw, wv2[I2].ravel(), np.repeat(fn, 3, 0))
    Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12); N2 = np.concatenate(Ns); ch = isR.copy(); ch[I2[src == 2].ravel()] = True; N2[ch] = Nw[wv2[ch]]
    used = np.unique(I2); mp = -np.ones(len(P2), int); mp[used] = np.arange(len(used))
    for h in hands: h['rid'] = np.concatenate(Ids)[used]   # (each vertex's in Ren's package, -1 Kael's: tools/kael_bust_attach.py)
    return P2[used], N2[used], mp[I2], np.concatenate(UVs)[used], isR[used], src, hands


def muscle_lines(P, I, ks, bary):
    """The arms' muscles traced as the sheet traces them (Denis, 12/11: "ricalca anche i muscoli delle braccia"): per texel how
    far its surface lies under the surface smoothed MUSCLE[0] times along the normal (h: the valleys between the muscles), and
    how much more than around it (h minus h smoothed MUSCLE[1] times: the valley's middle). Lines where h is over MUSCLE[2]
    and that over MUSCLE[3] (GLB units)."""
    from scipy.sparse import coo_matrix
    wv, Pw, W, E, _ = _graph(P, I); nw = len(Pw)
    fn = np.cross(Pw[W[:, 1]] - Pw[W[:, 0]], Pw[W[:, 2]] - Pw[W[:, 0]]); Nw = np.zeros((nw, 3)); np.add.at(Nw, W.ravel(), np.repeat(fn, 3, 0)); Nw /= np.linalg.norm(Nw, axis=1, keepdims=True) + 1e-12
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr(); deg = np.asarray(A.sum(1)).ravel()
    def sm(X, n):
        for _ in range(n): X = .5 * X + .5 * (A @ X) / (deg[:, None] if X.ndim > 1 else deg)
        return X
    h = sm(((sm(Pw.copy(), MUSCLE[0]) - Pw) * Nw).sum(1), 2); hr = h - sm(h, MUSCLE[1])
    ht = (h[wv][I[ks]] * bary).sum(1); hrt = (hr[wv][I[ks]] * bary).sum(1)
    return (ht > MUSCLE[2]) & (hrt > MUSCLE[3])


def finger_lines(pos, nor, sel, hands):
    """The fingers drawn as the sheet draws them (Denis, 12/11: "disegna meglio le dita delle mani"): per texel of sel (Ren's
    hands' skin) its finger (the nearest of Ren's finger bones' chains, laid as his hand: tf), and on it a line along each side
    (FINGER_LINE[0]: where the surface turns square to the hand's width, |n . side| over it: ink; over [1]: the skin's shadow)
    where the fingers press together in a fist, and at the two joints a short crease (within [2] of the joint along the
    finger, on the back the skin's shadow, on the palm ink). Returns (ink, shadow) masks."""
    import kael_bust_attach as KA
    R = KA.package(KA.REN[0]); L, _, _ = KA.look(KA.REN[1], len(R['P'])); names = R['names']; fq = {f['n']: f['fist'] for f in L['fingers']}
    ink = np.zeros(len(pos), bool); sh = np.zeros(len(pos), bool)
    for h in hands:
        side = h['side']; sd = h['sd']; fw = KA.fingers_world(L['fingers'], names, R['Wm']); Rr = R['Wm'][names.index(side + 'Hand')][:3, :3]
        on = sel & (np.sign(pos[:, 0]) == sd); idx = np.nonzero(on)[0]
        if not len(idx): continue
        best = np.full(len(idx), 9.); seg = np.zeros((len(idx), 3)); dors = np.zeros((len(idx), 3)); tj = np.zeros(len(idx)); jl = np.zeros(len(idx))
        for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
            j = [fw[side + 'Hand' + f + str(k)] for k in (1, 2, 3)]; j.append(j[2] + (j[2] - j[1]) * .9)   # (the tip: the last bone's length on)
            q = KA.qm(fq[side + 'Hand' + f + '1']); d0 = (j[1] - j[0]) / np.linalg.norm(j[1] - j[0]); cu = Rr @ q @ Rr.T @ d0; dv = -(cu - (cu @ d0) * d0)
            Jb = h['tf'](np.array(j)); dvb = h['sim']['R'] @ dv
            for k in range(3):
                a, b = Jb[k], Jb[k + 1]; ab = b - a; L2 = ab @ ab; t = np.clip(((pos[idx] - a) @ ab) / L2, 0, 1); d = np.linalg.norm(pos[idx] - (a + np.outer(t, ab)), axis=1)
                if f != 'Thumb' and k == 0: d = d + .004 * (t < .15)   # (the knuckles belong to the hand's back, not to a finger's side)
                m = d < best; best[m] = d[m]; seg[m] = ab / np.sqrt(L2); dors[m] = dvb / np.linalg.norm(dvb)
                tl = np.minimum(t * np.sqrt(L2), (1 - t) * np.sqrt(L2))   # (along the bone, to its nearer joint)
                tj[m] = np.where(k == 0, (1 - t[m]) * np.sqrt(L2), np.where(k == 2, t[m] * np.sqrt(L2), tl[m])); jl[m] = (k > 0) | (t[m] > .5)
        n = nor[idx]; lat = np.cross(seg, dors); lat /= np.maximum(np.linalg.norm(lat, axis=1, keepdims=True), 1e-9)
        c = np.abs((n * lat).sum(1)); onf = best < .05
        ink[idx[onf & (c > FINGER_LINE[0])]] = True; sh[idx[onf & (c > FINGER_LINE[1]) & (c <= FINGER_LINE[0])]] = True
        crease = onf & jl.astype(bool) & (tj < FINGER_LINE[2]) & (c < .6); back = (n * dors).sum(1) > 0
        sh[idx[crease & back]] = True; ink[idx[crease & ~back]] = True
    return ink, sh


def ren_dorsal(side):
    """The back of Ren's hand (his package's space): opposite to where his index, middle and ring fingers curl in his fists."""
    import kael_bust_attach as KA
    R = KA.package(KA.REN[0]); L, _, _ = KA.look(KA.REN[1], len(R['P'])); names = R['names']
    Rr = R['Wm'][names.index(side + 'Hand')][:3, :3]; fw = KA.fingers_world(L['fingers'], names, R['Wm']); fq = {f['n']: f['fist'] for f in L['fingers']}
    v = np.zeros(3)
    for f in ('Index', 'Middle', 'Ring'):
        a, b = fw[side + 'Hand' + f + '1'], fw[side + 'Hand' + f + '2']; dr = (b - a) / np.linalg.norm(b - a)
        q = KA.qm(fq[side + 'Hand' + f + '1']); curled = Rr @ q @ Rr.T @ dr; v += curled - (curled @ dr) * dr
    return -v / np.linalg.norm(v)


def glove_of(P, I, isR, src_t, hands):
    """The fingerless glove on Ren's hands as the sheet draws it: the palm up to a straight edge GLOVE_M under the fingers'
    webs, the fingers and the thumb bare from their base. The webs: where the fingers part, on the distance from the cut along
    the surface (smoothed SMOOTH times) going down from the tips (each web the vertex where two fingers' pieces meet); the
    edge's plane through the three webs, square to the hand. Returns per hand the plane, the thumb's tip and its web (then
    glove_texels per texel)."""
    from scipy.sparse.csgraph import dijkstra
    wv, Pw, W, E, G = _graph(P, I); rv = np.zeros(len(Pw), bool); rv[wv[isR]] = True
    ring = np.unique(W[src_t == 2]); ring = ring[~rv[ring]]; dg = dijkstra(G, indices=ring, min_only=True, limit=2.); dg[~np.isfinite(dg)] = 0
    ip, ic = G.indptr, G.indices; nbm = [ic[ip[v]:ip[v + 1]] for v in range(len(Pw))]
    out = []
    import kael_bust_attach as KA
    R = KA.package(KA.REN[0]); RL, _, _ = KA.look(KA.REN[1], len(R['P'])); fw = KA.fingers_world(RL['fingers'], R['names'], R['Wm'])
    deg = np.diff(ip).astype(float); free = rv.copy(); free[ring] = False
    for _ in range(SMOOTH):
        avg = np.add.reduceat(dg[ic], ip[:-1]) / np.maximum(deg, 1); dg = np.where(free, avg, dg)
    for h in hands:
        vs = np.nonzero(rv & (np.sign(Pw[:, 0]) == h['sd']))[0]; tips = [vs[np.argmin(np.linalg.norm(Pw[vs] - t, axis=1))] for t in h['tips']]
        par = {}; tipset = {}
        def root(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        webs = {}
        for v in vs[np.argsort(-dg[vs])]:
            par[v] = v; tipset[v] = {k for k, t in enumerate(tips) if t == v}
            for u in nbm[v]:
                if u not in par: continue
                a_, b_ = root(u), root(v)
                if a_ == b_: continue
                for x in tipset[a_]:
                    for y in tipset[b_]:
                        webs.setdefault((min(x, y), max(x, y)), v)
                par[a_] = b_; tipset[b_] |= tipset.pop(a_)
        wf = [webs[(k, k + 1)] for k in (1, 2, 3)]; wt = webs[(0, 1)] if (0, 1) in webs else min((webs[k] for k in webs if 0 in k), key=lambda v: -dg[v])
        c = Pw[wf].mean(0); _, _, Vt = np.linalg.svd(Pw[wf] - c); ln = Vt[0]
        hx = Pw[tips[2]] - h['c0']; n = hx - (hx @ ln) * ln; n /= np.linalg.norm(n)
        # (the back of the hand: away from where the fingers curl in Ren's fists, in this space; the glove's edge there DORSAL
        # nearer the wrist: on the knuckles' fold it bent over the joints and broke into a crown of points in the fist)
        dv = h['sim']['R'] @ ren_dorsal(h['side']); dv -= (dv @ n) * n; dv /= np.linalg.norm(dv)
        # (the thumb's bones, Ren's laid on this hand: its edge a ring square to it, as the sheet's glove (the thumb out of it
        # where it leaves the palm, its base gloved))
        tj = h['tf'](np.array([fw[h['side'] + 'HandThumb%d' % k] for k in (1, 2, 3)]))
        out.append(dict(sd=h['sd'], c=c, n=n, d=dv, tip=Pw[tips[0]], web=Pw[wt], thumb=tj))
        ax_ = (tj[1] - tj[0]) / np.linalg.norm(tj[1] - tj[0])
        print("glove: %s thumb: its web %.2f of its first bone's length past that bone's joint" % (h['side'], ((Pw[wt] - tj[0]) @ ax_) / np.linalg.norm(tj[1] - tj[0])))
        print("glove: %s hand: webs at %s along the surface, the thumb's at %.3f" % (h['side'], np.round(dg[wf], 3), dg[wt]))
    return out


def glove_texels(pos, newh, planes, jw, okw, thumbw=None):
    """Per texel: the glove: under its hand's plane, but the thumb bare up to its web (along the surface from its tip, on
    the texels' own graph: its base a clean ring round it)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    g = np.zeros(len(pos), bool); r = np.repeat(np.arange(len(pos)), jw.shape[1])[okw.ravel()]; c = jw[okw]
    G = coo_matrix((np.linalg.norm(pos[r] - pos[c], axis=1) + 1e-9, (r, c)), shape=(len(pos), len(pos))).tocsr(); tree = cKDTree(pos)
    for q in planes:
        sel = newh & (np.sign(pos[:, 0]) == q['sd']); src = np.intersect1d(tree.query_ball_point(q['tip'], .006), np.nonzero(sel)[0])
        d = dijkstra(G, indices=src, min_only=True, limit=.4); L = d[tree.query(q['web'])[1]] - THUMB_M
        sm = lambda x: (lambda u: u * u * (3 - 2 * u))(np.clip(x, 0, 1))
        back = sm(.5 + ((pos[sel] - q['c']) @ q['d']) / (2 * DORSAL[1]))   # (0 on the palm's surface, 1 on the back's)
        tj = q['thumb']; ax = (tj[1] - tj[0]) / np.linalg.norm(tj[1] - tj[0]); ring = q['web'] + THUMB_RING * ax
        bare = (d[sel] < L + THUMB_SPAN) & ((pos[sel] - ring) @ ax > 0)   # (the ring its edge: along the surface only so far past the web, the index finger's skin not)
        if THUMB_W > 0: bare = thumbw[sel] > THUMB_W   # (Ren's fist: the thumb bare with its base, where his skin moves with the thumb's bones)
        g[sel] = ((pos[sel] - q['c']) @ q['n'] + GLOVE_M + DORSAL[0] * back < 0) & ~bare
        print('glove: the thumb bare up to %.3f from its tip, from a ring %.3f past its web (%d texels of its base gloved by the ring)' % (L, THUMB_RING, int(((d[sel] < L + THUMB_SPAN) & ~bare).sum())))
    return g


def unwrap(P, I):
    """A new UV atlas (xatlas: Kael's and Ren's pieces in one texture). Returns the vertices' map, the triangles, the UVs."""
    import xatlas
    at = xatlas.Atlas(); at.add_mesh(P.astype(np.float32), I.astype(np.uint32))
    po = xatlas.PackOptions(); po.resolution = TS; po.padding = 4; po.bilinear = True; po.blockAlign = True
    at.generate(xatlas.ChartOptions(), po); vm, idx, uv = at[0]
    print('atlas: %d charts, %.0f%% used' % (at.chart_count, 100 * at.utilization))
    return vm.astype(np.int64), idx.astype(np.int64), uv.astype(np.float64)


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


def arms(P, I, ys, xs, ks, pos, nor, mat, lab, tat, area, cams, fits, names, cols, ix, jw, okw, ok, newh):
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
    isl_c = (cm == 1) & (ca < ISLE) & (rs > .6 * np.maximum(rn, 1)) & (ax > .25); isl = isl_c[comp] & ~newh; mat[isl] = 0; lab[isl] = ix['skin']
    arm_x = arm_t[ks] & ((mat == 0) | tat) & ~newh; sd_x = np.sign(pos[:, 0])
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
    hd = np.abs(pos[:, 0]) * .8 - pos[:, 1] * .6; hand = (hd > HAND_D) & ~newh   # (Ren's hands: as main() painted them)
    m2 = mat.copy(); isk = np.isin(lab, [ix['skin'], ix['skinS'], ix['ink']]); m2[hand & isk] = 0; m2[hand & ~isk & (m2 == 0)] = 1
    for _ in range(4): m2 = np.where(hand, KF._mode(m2, jw, okw, 3), m2)
    KF._small(m2, j, ok, area, np.where(hand, 30., 0.), ~hand); m2[hand & (m2 == 2) & (hd > HAND_D + .02)] = 1
    fing = hand & (m2 == 0); glv = hand & (m2 == 1); cuff = hand & (m2 == 2); lab[fing] = ix['skin']
    gl = lab.copy(); gl[glv & ~np.isin(lab, [ix['black'], ix['plum']])] = ix['plum']; KF._small(gl, j, ok, area, np.where(glv, GLOVE_SMALL, 0.), ~glv)
    for _ in range(3): gl = np.where(glv, KF._mode(gl, jw, okw, len(names)), gl)
    lab[glv] = gl[glv]; lab[cuff & ~np.isin(lab, [ix['purple'], ix['purpleS']])] = ix['purple']
    print('shoulders: %d leftover bits to skin; hands: %d texels of fingers, %d of glove' % (int(bad.sum()), int(fing.sum()), int(glv.sum())))
    return lab


def finish(P, I, ks, bary, pos, nor, lab, tat, area, names, ix, jw, okw, ok, newh, rings=()):
    """What is left of Kael's hands, the shoulders' tattoos behind and the black borders (see the docstring)."""
    lab = lab.copy(); tat = tat.copy(); j = jw[:, :KF.KNN - 1]
    hd = np.abs(pos[:, 0]) * .8 - pos[:, 1] * .6; hand = hd > .925
    # 1. the hands: Ren's (ren_hands; newh, their texels): their skin and lines as Ren's paint, the glove as painted there; what
    # is left of Kael's own past his cuff the glove's plum
    hand = hand & ~newh
    lab[hand & ~np.isin(lab, [ix['plum'], ix['black'], ix['purple'], ix['purpleS']])] = ix['plum']
    glove = newh & np.isin(lab, [ix['plum'], ix['black']]); fingers = newh & np.isin(lab, [ix['skin'], ix['skinS'], ix['ink']]); thumb = np.zeros(len(lab), bool)
    # (under the cuffs, where Kael's hand was: Meshy's black and its small purple islands there the glove's plum; the cuff's hem
    # then gets its clean black line with the borders)
    if len(rings):
        uc = ~newh & (cKDTree(np.concatenate(rings)).query(pos, distance_upper_bound=UNDER_CUFF)[0] < UNDER_CUFF)
        pc = KF._comps(lab, j, ok); pa = np.bincount(pc, weights=area); pl = np.zeros(len(pa), np.int64); pl[pc] = lab
        isle = (pa < 200.)[pc] & np.isin(lab, [ix['purple'], ix['purpleS']]) & uc
        lab[isle | (uc & np.isin(lab, [ix['black'], ix['ink']]))] = ix['plum']
        print('under the cuffs: %d texels of purple islands and black to plum' % int((isle | uc).sum()))
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
    samp = lambda A, uv: A[np.clip((uv[:, 1] * A.shape[0]).astype(int), 0, A.shape[0] - 1), np.clip((uv[:, 0] * A.shape[1]).astype(int), 0, A.shape[1] - 1)]
    vc = samp(T, UV); vsk = (vc[:, 0] > 150) & (vc[:, 0] - vc[:, 2] > 35); vpu = (vc[:, 2] > 95) & (vc[:, 2] - vc[:, 1] > 55) & ~vsk
    P, N, I, SU, isR, src_t, hands = ren_hands(P, N, UV, I, (np.nonzero(~vsk & ~vpu)[0], np.nonzero(vpu)[0]))
    rid = hands[0]['rid']
    vm, I, UV = unwrap(P, I); P, N, SU, isR, rid = P[vm], N[vm], SU[vm], isR[vm], rid[vm]
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, TS); nor = nor / np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    # (each texel's source paint: Kael's by Meshy, Ren's on his hands, the seam the glove's)
    suv = (SU[I[ks]] * bary[:, :, None]).sum(1); s_ = src_t[ks]; newh = s_ >= 1
    TR = np.asarray(Image.open(REN[1]).convert('RGB')).astype(float)
    mey = np.zeros((len(ks), 3)); mey[s_ == 0] = samp(T, suv[s_ == 0]); mey[s_ == 1] = samp(TR, suv[s_ == 1]); mey[s_ == 2] = CLOTH
    # (the glove on Ren's hands: the palm up to under the knuckles, the fingers and the thumb bare)
    planes = glove_of(P, I, isR, src_t, hands)
    names = list(PAL); cols = np.array([PAL[k] for k in names], float); ix = {k: i for i, k in enumerate(names)}
    KF.prepare(P * SC, I); cnt = np.bincount(ks, minlength=len(I)).astype(float); area = KF.TRI_AREA[ks] * 1e6 / np.maximum(cnt[ks], 1)
    jw, okw, ok = KF._graph(pos * SC, nor.astype(np.float32), np.sqrt(area) * 1e-3); j = jw[:, :KF.KNN - 1]
    # (the thumb bare as in Ren's fist: where his skin moves with the thumb's bones by more than THUMB_W; Denis, 12/11:
    # "taglia i pugni di ren e attaccali a kael poi disegna i suoi guanti dove mancano")
    import kael_bust_attach as KA
    R_ = KA.package(KA.REN[0]); RL_, rsi_, rsw_ = KA.look(KA.REN[1], len(R_['P'])); an_ = R_['names'] + [f['n'] for f in RL_['fingers']]
    rth = (rsw_ * np.isin(rsi_, [k for k, n in enumerate(an_) if 'Thumb' in n])).sum(1)
    vt = np.where(rid >= 0, rth[np.maximum(rid, 0)], 0.)
    if THUMB_W_VSMOOTH:   # (smoothed over the surface first: on Ren's big triangles the weights' line broke into teeth)
        wv_, Pw_, W_, E_, G_ = _graph(P, I); vw = np.zeros(len(Pw_)); np.maximum.at(vw, wv_, vt); dg = np.bincount(E_.ravel(), minlength=len(Pw_)).astype(float)
        for _ in range(THUMB_W_VSMOOTH):
            acc = np.bincount(E_[:, 0], vw[E_[:, 1]], len(Pw_)) + np.bincount(E_[:, 1], vw[E_[:, 0]], len(Pw_)); vw = np.where(dg > 0, .5 * vw + .5 * acc / np.maximum(dg, 1), vw)
        vt = np.where(rid >= 0, vw[wv_], 0.)
    thumbw = (vt[I[ks]] * bary).sum(1)
    for _ in range(THUMB_W_SMOOTH): thumbw = np.where(newh, (np.where(okw, thumbw[jw], 0).sum(1) + thumbw) / (okw.sum(1) + 1), thumbw)   # (and over the texels)
    glove = glove_texels(pos, newh, planes, jw, okw, thumbw) | (s_ == 2)
    g2 = glove.astype(np.int64)
    for _ in range(GLOVE_SMOOTH): g2 = KF._mode(g2, jw, okw, 2, keep=~newh | (s_ == 2))
    glove = g2 == 1   # (the glove's edge smoothed on the surface)
    print("Ren's hands: %d texels, %d of them the glove" % (int(newh.sum()), int(glove.sum())))
    r, g, b = mey[:, 0], mey[:, 1], mey[:, 2]; L = mey.mean(1)
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
    sk3 = [ix['skin'], ix['skinS'], ix['ink']]; rh = newh & ~glove
    Lr = mey.mean(1)
    for _ in range(2): Lr = np.where(newh, (np.where(ok, Lr[j], 0).sum(1) + Lr) / (ok.sum(1) + 1), Lr)   # (his strokes a little softened: whole lines, not dashes)
    Lr = Lr[rh]; lab[rh] = np.where(Lr < REN_LINE[0], ix['ink'], np.where(Lr < REN_LINE[1], ix['skinS'], ix['skin'])); mat[rh] = 0; lab[glove] = ix['plum']; mat[glove] = 1; tat[newh] = False
    if not REN_PAINT:
        f_ink, f_sh = finger_lines(pos, nor, rh, hands); lab[rh & f_sh & (lab == ix['skin'])] = ix['skinS']; lab[rh & f_ink] = ix['ink']
    else: f_ink = f_sh = np.zeros(len(ks), bool)
    print('fingers: %d texels of their side lines and creases in ink, %d in the skin\'s shadow' % (int((rh & f_ink).sum()), int((rh & f_sh).sum())))
    print('pieces: skin %.1f%%, cloth %.1f%%, purple %.1f%%; tattoos: %d pieces' % (*(100 * np.bincount(mat, minlength=3) / len(mat)), int(tat_c.sum())))
    # the skin's shadow
    ao = occlusion(P, N, I)[cKDTree(P).query(pos)[1]]
    az, el = np.radians(SHADE[0]), np.radians(SHADE[1]); Lv = np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])
    sc = nor @ Lv - SHADE[2] * (1 - ao); sk = (mat == 0) & ~tat & ~newh; tau = np.quantile(sc[sk], SHADE[3])
    lab[sk & (lab == ix['skin']) & (sc < tau)] = ix['skinS']
    nl = len(names)
    for _ in range(5): lab = KF._mode(lab, jw, okw, nl, keep=(lab == ix['ink']) | tat | (mat != 0) | newh)
    for _ in range(2): lab = KF._mode(lab, j, ok, nl, keep=(lab == ix['ink']) | tat | newh)
    KF._small(lab, j, ok, area, np.where(newh, np.where(lab == ix['ink'], .3, np.where(glove, GLOVE_BLACK, np.where(lab == ix['skinS'], REN_SMALL, 1.))), np.where(lab == ix['ink'], 1.5, np.where(lab == ix['skinS'], SKIN_SMALL, 10.))), tat)
    print('  '.join('%s %.1f%%' % (n, 100 * (lab == i).mean()) for i, n in enumerate(names)))
    if fit or not os.path.exists(CAMS):
        cams = fit_cams(P, I); fits = fit_arms(P, I, ks, mat, tat, cams)
        json.dump({'_': 'tools/kael_bust.py --fit: the three views\' cameras (orthographic: u = cx + s (x cos yaw - z sin yaw), v = by - s y, GLB units) and per near arm a turn (a, degrees), scale (k) and shift (tx, ty px) about (cx, cy) laying its skin on the drawing\'s',
                   'cams': cams, 'arms': fits}, open(CAMS, 'w'), indent=1)
    cj = json.load(open(CAMS)); lab = arms(P, I, ys, xs, ks, pos, nor, mat, lab, tat, area, cj['cams'], cj['arms'], names, cols, ix, jw, okw, ok, newh)
    # (the arms' muscles traced: muscle_lines on the upper arms' and the elbows' skin, not the hands, the tattoos)
    armsk = (np.abs(pos[:, 0]) > .2) & (np.abs(pos[:, 0]) * .8 - pos[:, 1] * .6 < .80) & ~newh & ~tat & np.isin(lab, [ix['skin'], ix['skinS']])
    ml = armsk & muscle_lines(P, I, ks, bary); lab[ml] = ix['ink']
    print('arms: %d texels of the muscles\' lines' % int(ml.sum()))
    lab = finish(P, I, ks, bary, pos, nor, lab, tat, area, names, ix, jw, okw, ok, newh, [h['ring'] for h in hands])
    if os.environ.get('KAEL_BUST_DUMP'): np.savez(os.environ['KAEL_BUST_DUMP'], newh=newh, glove=glove, ys=ys, xs=xs, ks=ks, bary=bary, pos=pos, nor=nor, mat=mat, lab=lab, tat=tat, mey=mey, area=area)
    out = np.zeros((TS, TS, 3)); cov = np.zeros((TS, TS), bool); out[ys, xs] = cols[lab]; cov[ys, xs] = True
    if REN_PAINT:   # (the hands' skin in Ren's own paint: his hands, his fists, as he has them; Denis, 12/11: "non è la mano di ren quella su kael")
        rp = rh & (s_ == 1); out[ys[rp], xs[rp]] = mey[rp]
        print("hands: %d texels in Ren's paint" % int(rp.sum()))
    _, (iy, jx) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], jx[~cov]]
    im = Image.fromarray(out.round().astype(np.uint8)); bio = io.BytesIO(); im.save(bio, 'PNG', optimize=True)
    if png: im.save(png)
    glbio.write(dst, m, P, N, UV, I, img=bio.getvalue(), mime='image/png'); print('written', dst)
    # (beside it, for tools/kael_bust_attach.py: each vertex's in Ren's package (-1 Kael's), its place, and per hand the fit laying Ren's on it and its thumb's web)
    side = dst[:-4] + '_hands.npz'
    webs = {('Right' if q['sd'] < 0 else 'Left') + '_web': q['web'] for q in planes}   # (where each thumb leaves the palm: tools/kael_bust_attach.py THUMB_SCALE)
    np.savez(side, rid=rid, pos=P, **webs, **{'%s_%s' % (h['side'], k): np.asarray(v) for h in hands for k, v in h['sim'].items()})
    print('written', side)


if __name__ == '__main__':
    av = sys.argv[1:]; png = None; fit = '--fit' in av; av = [a for a in av if a != '--fit']
    if '--png' in av: k = av.index('--png'); png = av[k + 1]; av = av[:k] + av[k + 2:]
    if len(av) != 2: sys.exit(__doc__)
    main(av[0], av[1], png, fit)
