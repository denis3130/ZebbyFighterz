#!/usr/bin/env python3
"""Kael's own touches after tools/char_look.py (10/11/2026: the model Meshy made from Denis's drawing of him dressed,
docs/ref/personaggi/kael_nero.png), from looking at him in 3D from every side and close up (docs/meshy/CONTROLLI.md):

- the lock over his right eye lifted above the brow (as tools/mesh_prep/lift_bangs.py did for Ren's bangs): the drawing
  shows both eyes and one lock between them (BANGS: the hair in front of the face within x0..x1, from its root's
  height down to its tips, pressed up so the tips end at the brow; the lock between the eyes is outside x0..x1);
- the hair, the face's front and all the body in flat light (the look's per-vertex flat share): the toon light's bands
  on the many locks, over the face and on the vest were grey patches and soft smears; the paint has the drawings' shading;
- the paint cleaned (kael_painted.jpg, the look's paint): on the clothes (not the head), specks (small spots of
  another colour inside a patch of black or purple, not at its UV piece's edge, under SPECK texels) take their
  surroundings' colour; the purple in the drawing's two tones by its lightness smoothed over PURPLE_BLUR texels (the
  soft dark gradients at its edges were airbrush, not the drawing's flat colours) and the black's purple-tinted
  gradient texels in the drawing's black; the black in the drawing's two tones, its lit cloth and its folds (SUIT: Denis,
  10/11, "cambiare il colore del modello 3d di kael da troppo scuro a più come nelle foto": Meshy's black was nearly
  all under the drawing's lit tone), by the paint's lightness smoothed over SUIT_BLUR texels (no grain), lit where
  the drawing's share of it is (SUIT_LIT) on the front, the back and the sides alike (SUIT_BINS: Meshy's black is
  darker behind), no patch of a tone under SUIT_MIN texels, its edges softened;
  the hair in the head sheet's two tones (HAIR: its light and its lavender shadow, as much of it as the sheet has, by
  the paint's lightness smoothed: Meshy's hair was nearly white) and its outline thinner (HAIR_LINE: the sheet's locks'
  lines are thin), the jaw's outline bold as the head sheet's (JAW); no outline on the upper arms' small sharp ridges (FIN: Meshy's
  skin fins by the armholes; seen along the shoulder in the guard, their outline lay on the skin as black dashes); the earrings in the drawing's purple (EARRING: their light and purple texels under the lobes); the face's right half
  (his right, under the lifted lock: Meshy painted no eye there) the mirror image of its left half about the nose
  (FACE: on the face's surface, not the hair in front of it; faded in at the middle and where it turns away);
  between the UV pieces, the nearest piece's colour (no seams under filtering).

usage: python3 tools/kael_fix.py PACKAGE_DIR   (writes PACKAGE_DIR/kael_painted.jpg and the shape and the flat light
into PACKAGE_DIR/kael_look.json + .bin)"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
from ren_look import smooth_normals
from paint_views import texel_table
import glbio

BANGS = {'x': (-.068, -.012), 'top': 1.70, 'tips': 1.575, 'to': 1.632, 'front': (.002, .008)}   # m (see above)
FLAT_HAIR, FLAT_FACE, FLAT_FACE_N = 1., .75, (.15, .45)   # the flat share: the hair; the face's skin, by its normal's z
FLAT_BODY = 1.                             # and on all the body (11/11: on its front alone, as Ren's, the toon light's soft bands on the
                                           # vest's sides and back and on the shoulders were no sheet's flat colours; the paint has their shading)
SPECK, SKIN_KEEP, TINY = 60, 4, 20   # texels: a speck's size at most; how far from the skin a colour is the skin's own shading; a purple bit's
BLACK, BLACK_MED = (14, 13, 15), 5         # the drawing's black; the black's median (texels)
SUIT, SUIT_LIT, SUIT_BLUR, SUIT_MIN = ((14, 13, 15), (46, 45, 48)), .54, 3., 150   # kael_nero.png's black: folds, lit
SUIT_BINS = 6                              # the lit share the drawing's on the front, the back and between (by the normal)
HAIR, HAIR_LIT, HAIR_BLUR, HAIR_MIN = ((129, 111, 138), (225, 214, 224)), .6, 5., 120   # the head sheet's hair: shadow, light
HAIR_LINE = .5                             # the outline's width on the hair (its locks' lines thinner, as the sheet's)
HAIR_SKIN = .6                             # but not a light texel that much skin surrounds (1.5 cm): a stroke on the skin
JAW, JAW_LINE = (1.505, 1.535, .075), .7   # m: the jaw under the mouth (y from, to; |x| under); its outline's width
FIN = (.3, .3, -.2)                        # the upper arms' ridges: the shoulders' and arms' share over [0], the forearms' under [1],
                                           # convexity (the neighbours' mean under the tangent plane, per mean edge) under [2]
PURPLE, PURPLE_BLUR = ((96, 42, 136), (169, 84, 210)), 1.5   # the drawing's purple in shadow and in light
FACE = {'box': (-.085, .085, 1.545, 1.665), 'surf': .004, 'mid': (.002, .008), 'turn': (.10, .30), 'px': .0004}
EARRING = {'x': .052, 'y': (1.505, 1.585), 'z': -.012, 'ramp': ((70, 28, 104), (150, 70, 200), (214, 160, 240))}


def load(pkg):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2).astype(np.float64)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    lj = json.load(open(os.path.join(pkg, name + '_look.json'))); LB = open(os.path.join(pkg, name + '_look.bin'), 'rb').read()
    jn = np.frombuffer(LB, np.uint8, lj['skin'][0][1], lj['skin'][0][0]).reshape(-1, 4).astype(np.int64)
    wn = np.frombuffer(LB, np.float32, lj['skin'][1][1], lj['skin'][1][0]).reshape(-1, 4).astype(np.float64)
    return name, m, P, N, UV, I, jn, wn, lj, LB


def classes(c):
    """Per colour (n x 3): 0 black, 1 purple, 2 skin, 3 light (hair, whites), 4 other."""
    r, g, b = c[:, 0], c[:, 1], c[:, 2]; mx = c.max(1); mn = c.min(1); out = np.full(len(c), 4)
    out[(mx < 75) | ((mx < 110) & (mx - mn < 30))] = 0
    out[(b > g + 40) & (b > 90) & (r < b + 10) & (out != 0)] = 1
    out[(r > 140) & (r - b > 40) & (g > 80)] = 2
    out[(mn > 150) & (mx - mn < 70)] = 3
    return out


def face_depth(P, I, hw, x0, x1, y0, y1, n=72):
    """The face behind the hair seen from the front: on each front ray over x0..x1, y0..y1, the last hit in the front
    half of the head (z > .02). A function of points (n x 3) -> their face's z there (nan off the face)."""
    T = I[(hw[I] > .3).all(1)]
    X = np.linspace(x0, x1, n); Y = np.linspace(y1, y0, n); ZF = np.full((n, n), np.nan)
    for i, y in enumerate(Y):
        for k, r in enumerate(glbio.raycast_z(P, T, X, [y] * n)):
            rr = [h for h in r if h[0] > .02]
            if rr: ZF[i, k] = rr[-1][0]
    def zf(p):
        iy = np.clip(np.round((Y[0] - p[:, 1]) / (Y[0] - Y[-1]) * (n - 1)).astype(int), 0, n - 1)
        ix = np.clip(np.round((p[:, 0] - X[0]) / (X[-1] - X[0]) * (n - 1)).astype(int), 0, n - 1)
        out = ZF[iy, ix]; out[(p[:, 0] < x0) | (p[:, 0] > x1) | (p[:, 1] < y0) | (p[:, 1] > y1)] = np.nan
        return out
    return zf


def lift_bangs(P, I, hw, col):
    """The lock over his right eye pressed up (see BANGS): the new positions."""
    x0, x1 = BANGS['x']; top, tips, to = BANGS['top'], BANGS['tips'], BANGS['to']
    zf = face_depth(P, I, hw, x0 - .03, x1 + .03, tips - .02, top + .01, 60)(P)
    sm = lambda e0, e1, v: (lambda t: t * t * (3 - 2 * t))(np.clip((v - e0) / (e1 - e0), 0, 1))
    w = sm(x0 - .015, x0, P[:, 0]) * (1 - sm(x1, x1 + .008, P[:, 0])) * np.where(np.isnan(zf), 0, sm(*BANGS['front'], P[:, 2] - np.nan_to_num(zf, nan=9)))
    w *= (P[:, 1] < top) & (P[:, 1] > tips - .03) & (hw > .3) & (classes(col) != 2)
    _, inv = np.unique(np.round(P * 1e6).astype(np.int64), axis=0, return_inverse=True); inv = inv.ravel()
    wm = np.zeros(inv.max() + 1); np.maximum.at(wm, inv, w); w = wm[inv]   # (copies of a position move together)
    k = (top - to) / (top - tips); ynew = top - (top - np.maximum(P[:, 1], tips - .03)) * k
    Q = P.copy(); Q[:, 1] += w * (ynew - P[:, 1])
    print('bangs: %d vertices lifted, %.1f cm at most' % ((w > .01).sum(), 100 * (w * (ynew - P[:, 1])).max()))
    return Q


def paint(pkg, name, Q, N, UV, I, hw, zfun):
    T0 = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(np.float64); TS = T0.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(Q, N, UV, I, TS)
    th = (hw[I[ks]] * bary).sum(1)
    out = T0.copy(); cov = np.zeros((TS, TS), bool); cov[ys, xs] = True
    cl = np.full((TS, TS), -1); cl[ys, xs] = classes(T0[ys, xs])
    cloth = np.zeros((TS, TS), bool); cloth[ys, xs] = th < .5
    # specks: small spots inside a patch of black or purple (not at their UV piece's edge) take its colour
    edge = cov & ~ndimage.binary_erosion(cov, iterations=2)
    n_sp = 0
    for c in (0, 1):
        other = cloth & (cl != c) & (cl != 2)
        lab, n = ndimage.label(other); sz = np.bincount(lab.ravel()); touch = np.zeros(n + 1, bool); np.logical_or.at(touch, lab[edge], True)
        small = (sz < SPECK) & ~touch; small[0] = False
        sp = small[lab] & cloth
        if not sp.any(): continue
        ring = ndimage.binary_dilation(sp, iterations=2) & ~sp & (cl == c) & cov
        _, (iy, ix) = ndimage.distance_transform_edt(~ring, return_indices=True)
        out[sp] = out[iy[sp], ix[sp]]; cl[sp] = c; n_sp += int(sp.sum())
    # on the clothes the drawing has only black, purple and skin: any light or other colour there (away from the skin:
    # not its shading) takes the nearest of those (the white triangles and scratches Meshy left)
    skin = cov & (cl == 2); near_skin = ndimage.binary_dilation(skin, iterations=SKIN_KEEP)
    bad = cloth & np.isin(cl, (3, 4)) & ~near_skin; good = cov & np.isin(cl, (0, 1)) & ~near_skin
    if bad.any():
        _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
        out[bad] = out[iy[bad], ix[bad]]; cl[bad] = cl[iy[bad], ix[bad]]; n_sp += int(bad.sum())
    # tiny purple bits on the black (under TINY texels, even at their UV piece's edge): black
    lab, n = ndimage.label(cloth & (cl == 1)); sz = np.bincount(lab.ravel()); tiny = (sz < TINY); tiny[0] = False
    tp = tiny[lab]
    if tp.any(): out[tp] = BLACK; cl[tp] = 0; n_sp += int(tp.sum())
    # the black's dotted seams (grey dots in rows, Meshy's): inside the black, its median over BLACK_MED texels
    blk = cloth & (cl == 0); inner = ndimage.binary_erosion(blk, structure=np.ones((BLACK_MED, BLACK_MED)))
    med = np.stack([ndimage.median_filter(out[..., k], size=BLACK_MED) for k in range(3)], -1); out[inner] = med[inner]
    # the purple in the drawing's two tones by its lightness smoothed (no grain); the black's purple-tinted texels black
    pu = cloth & (cl == 1); L = out.mean(2)
    Ls = ndimage.gaussian_filter(np.where(pu, L, 0), PURPLE_BLUR) / np.maximum(ndimage.gaussian_filter(pu.astype(float), PURPLE_BLUR), 1e-6)
    t0, t1 = np.array(PURPLE, float); split = (t0.mean() + t1.mean()) / 2
    out[pu] = np.where((Ls[pu] > split)[:, None], t1, t0)
    bk = cloth & (cl == 0) & (out[..., 2] - out[..., 1] > 14)
    out[bk] = BLACK
    # the black in the drawing's two tones (its lit cloth where the paint is lightest, as much of it as the drawing has)
    blk = cloth & (cl == 0); L = out.mean(2)
    Ls = ndimage.gaussian_filter(np.where(blk, L, 0), SUIT_BLUR) / np.maximum(ndimage.gaussian_filter(blk.astype(float), SUIT_BLUR), 1e-6)
    nz = np.zeros((TS, TS)); nz[ys, xs] = nor[:, 2]   # (the split by the way the cloth faces: Meshy's black is darker behind)
    edges = np.linspace(-1, 1, SUIT_BINS + 1); mids = (edges[:-1] + edges[1:]) / 2
    ts_ = [np.percentile(Ls[blk & (nz >= a) & (nz < b)], 100 * (1 - SUIT_LIT)) if (blk & (nz >= a) & (nz < b)).sum() > 500 else np.nan for a, b in zip(edges[:-1], edges[1:])]
    ok = ~np.isnan(ts_); thr = np.interp(nz, mids[ok], np.array(ts_)[ok])
    lit = blk & (Ls > thr)
    for tone in (True, False):   # (no small patches of either)
        lab, n = ndimage.label(blk & (lit == tone)); sz = np.bincount(lab.ravel()); small = sz < SUIT_MIN; small[0] = False
        lit[small[lab]] = not tone
    w = ndimage.gaussian_filter(lit.astype(float), .7) / np.maximum(ndimage.gaussian_filter(blk.astype(float), .7), 1e-6)
    t0, t1 = (np.array(c, float) for c in SUIT); out[blk] = t0 + (t1 - t0) * np.clip(w[blk], 0, 1)[:, None]
    # the hair in the sheet's two tones (kael_testa_3viste.png: its light and its lavender shadow, about 40% of it), by the
    # paint's lightness smoothed over HAIR_BLUR texels (Meshy's darker inner layers and gaps between the locks)
    ch = classes(T0[ys, xs]); cool = T0[ys, xs, 0] - T0[ys, xs, 2] <= 25   # (the hair's light and its lavender: not warm)
    hd = th > .5; g = np.floor(pos / .003).astype(np.int64); g -= g[hd].min(0); shp = tuple(g[hd].max(0) + 1)
    Sk = np.zeros(shp, np.float32); Al = np.zeros(shp, np.float32)   # (the share of skin around: a light stroke on the
    np.add.at(Sk, tuple(g[hd & (ch == 2)].T), 1); np.add.at(Al, tuple(g[hd].T), 1)   # skin is not a lock of hair)
    Sk = ndimage.uniform_filter(Sk, 5); Al = ndimage.uniform_filter(Al, 5); gi = tuple(np.clip(g, 0, np.array(shp) - 1).T)
    share = np.where(hd, Sk[gi] / np.maximum(Al[gi], 1e-6), 0)
    hm = np.zeros((TS, TS), bool); hm[ys, xs] = hd & cool & ((ch == 3) | ((ch == 4) & (T0[ys, xs].mean(1) > 90))) & (share < HAIR_SKIN)
    L0 = T0.mean(2); Lh = ndimage.gaussian_filter(np.where(hm, L0, 0), HAIR_BLUR) / np.maximum(ndimage.gaussian_filter(hm.astype(float), HAIR_BLUR), 1e-6)
    hl = hm & (Lh > np.percentile(Lh[hm], 100 * (1 - HAIR_LIT)))
    for tone in (True, False):
        lab, n = ndimage.label(hm & (hl == tone)); sz = np.bincount(lab.ravel()); small = sz < HAIR_MIN; small[0] = False; hl[small[lab]] = not tone
    w = ndimage.gaussian_filter(hl.astype(float), .7) / np.maximum(ndimage.gaussian_filter(hm.astype(float), .7), 1e-6)
    h0, h1 = (np.array(c, float) for c in HAIR); out[hm] = h0 + (h1 - h0) * np.clip(w[hm], 0, 1)[:, None]
    # the earrings: the drawing's purple, its light and shadow from the paint's
    c0 = classes(T0[ys, xs])
    e = (th > .5) & (np.abs(pos[:, 0]) > EARRING['x']) & (pos[:, 1] > EARRING['y'][0]) & (pos[:, 1] < EARRING['y'][1]) & (pos[:, 2] > EARRING['z'])
    e &= (c0 == 1) | (c0 == 3) | ((c0 == 4) & (T0[ys, xs].mean(1) > 120))
    if e.any():
        Le = T0[ys[e], xs[e]].mean(1); r0, r1, r2 = (np.array(v, float) for v in EARRING['ramp'])
        t = np.clip((Le - Le.min()) / max(np.ptp(Le), 1), 0, 1)[:, None]
        out[ys[e], xs[e]] = np.where(t < .5, r0 + (r1 - r0) * (t / .5), r1 + (r2 - r1) * ((t - .5) / .5))
    # the face's right half: the mirror image of its left half about the nose, on the face's surface
    x0, x1, y0, y1 = FACE['box']; zf = zfun(pos)
    onf = (th > .5) & ~np.isnan(zf) & (np.abs(pos[:, 2] - np.nan_to_num(zf, nan=-9)) < FACE['surf']) & (nor[:, 2] > FACE['turn'][0])
    nose = onf & (np.abs(pos[:, 1] - 1.58) < .02); xc = float(pos[nose][np.argmax(pos[nose, 2]), 0]) if nose.any() else 0.
    src = onf & (pos[:, 0] > xc); px = FACE['px']; W, H = int((x1 - x0) / px) + 1, int((y1 - y0) / px) + 1
    gu = np.clip(((pos[:, 0] - x0) / px).round().astype(int), 0, W - 1); gv = np.clip(((y1 - pos[:, 1]) / px).round().astype(int), 0, H - 1)
    img = np.zeros((H, W, 3)); zb = np.full((H, W), -9.); o = np.argsort(pos[src, 2])
    si = np.nonzero(src)[0][o]; zb[gv[si], gu[si]] = pos[si, 2]; img[gv[si], gu[si]] = out[ys[si], xs[si]]
    have = zb > -9; _, (iy, ix) = ndimage.distance_transform_edt(~have, return_indices=True); img = img[iy, ix]
    tgt = onf & (pos[:, 0] < xc)
    mu = np.clip(((2 * xc - pos[tgt, 0]) - x0) / px, 0, W - 1).round().astype(int); mv = gv[tgt]
    sm = lambda e0, e1, v: (lambda t: t * t * (3 - 2 * t))(np.clip((v - e0) / (e1 - e0), 0, 1))
    w = (sm(*FACE['mid'], xc - pos[tgt, 0]) * sm(*FACE['turn'], nor[tgt, 2]))[:, None]
    ti = np.nonzero(tgt)[0]; out[ys[ti], xs[ti]] = out[ys[ti], xs[ti]] * (1 - w) + img[mv, mu] * w
    n_face = int(tgt.sum()); q = pu
    # between the UV pieces: the nearest piece's colour
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(os.path.join(pkg, name + '_painted.jpg'), quality=90, optimize=True)
    print('paint: %d texels of specks; %d purple texels in the drawing\'s tones, %d black ones; %d earring texels; the face\'s right half from its left (%d texels, the nose at x %.3f)' % (n_sp, int(q.sum()), int(bk.sum()), int(e.sum()), n_face, xc))


def convexity(P, I):
    """Per vertex (welded): its neighbours' mean over the tangent plane, per its mean edge (negative: a ridge, positive: a pit)."""
    from scipy.sparse import coo_matrix
    _, wv = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel(); nw = wv.max() + 1
    W = wv[I]; E = np.unique(np.sort(np.concatenate([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]), 1), axis=0)
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr()
    Pw = np.zeros((nw, 3)); Pw[wv] = P
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]]); Nw = np.zeros((nw, 3)); np.add.at(Nw, W.ravel(), np.repeat(fn, 3, 0))
    Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12)
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1); el = np.linalg.norm(Pw[E[:, 0]] - Pw[E[:, 1]], axis=1)
    se = np.zeros(nw); np.add.at(se, E[:, 0], el); np.add.at(se, E[:, 1], el)
    return ((((A @ Pw) / deg[:, None] - Pw) * Nw).sum(1) / np.maximum(se / deg, 1e-9))[wv]


def main(pkg):
    name, m, P, N, UV, I, jn, wn, lj, LB = load(pkg)
    if 'move' in lj: sys.exit('the look already has a shape: run tools/char_look.py first')
    idx = {b['n']: i for i, b in enumerate(m['bones'])}; nb = len(m['bones'])
    hw = ((jn == idx['Head']) * wn).sum(1)
    tex = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(np.float64); ts = tex.shape[0]
    col = tex[np.clip((UV[:, 1] * ts).astype(int), 0, ts - 1), np.clip((UV[:, 0] * ts).astype(int), 0, ts - 1)]
    Q = lift_bangs(P, I, hw, col)
    cv = classes(col)
    hand = sum(((jn == idx[s + 'Hand']) * wn).sum(1) for s in ('Left', 'Right')) + ((jn >= nb) * wn).sum(1)
    nsm = smooth_normals(Q, I, np.clip(hand / .5, 0, 1))
    sm = lambda e0, e1, v: (lambda t: t * t * (3 - 2 * t))(np.clip((v - e0) / (e1 - e0), 0, 1))
    flat = np.zeros(len(P)); flat[(hw > .3) & (cv == 3)] = FLAT_HAIR
    face = (hw > .5) & (cv == 2) & (P[:, 1] > 1.52)
    flat[face] = np.maximum(flat[face], FLAT_FACE * sm(*FLAT_FACE_N, nsm[face, 2]))
    body = hw < .3; flat[body] = FLAT_BODY
    print('flat light: %d hair vertices, %d of the face, %d of the body' % ((flat[(cv == 3)] > 0).sum(), (flat[face] > 0).sum(), (flat[body] > .5).sum()))
    paint(pkg, name, Q, nsm.astype(np.float64), UV, I, hw, face_depth(Q, I, hw, *FACE['box']))
    # the look: its line and skin as they are; the light's normals on the new shape, the flat share, the moved vertices
    f32 = lambda a: np.frombuffer(LB, np.float32, a[1], a[0])
    pad = lambda b: b + b'\0' * (-len(b) % 4)
    line = f32(lj['line']).copy(); line[(hw > .3) & (cv == 3)] *= HAIR_LINE   # (the hair's outline thinner)
    jaw = (hw > .5) & (cv == 2) & (Q[:, 1] > JAW[0]) & (Q[:, 1] < JAW[1]) & (np.abs(Q[:, 0]) < JAW[2])   # (the jaw's line
    line[jaw] = np.maximum(line[jaw], JAW_LINE)                                                     # bold, as drawn)
    up_arm = sum(((jn == idx[s + b]) * wn).sum(1) for s in ('Left', 'Right') for b in ('Shoulder', 'Arm'))
    fore = sum(((jn == idx[s + 'ForeArm']) * wn).sum(1) for s in ('Left', 'Right'))
    fin = (up_arm > FIN[0]) & (fore < FIN[1]) & (convexity(P, I) < FIN[2]); line[fin] = 0
    print('outline: none on %d vertices of the upper arms\' ridges' % int(fin.sum()))
    look = dict(lj); blob = line.astype(np.float32).tobytes(); look['line'] = [0, int(lj['line'][1])]
    oj = len(blob); blob += jn.astype(np.uint8).tobytes(); blob = pad(blob); ow = len(blob); blob += wn.astype(np.float32).tobytes()
    look['skin'] = [[oj, int(jn.size)], [ow, int(wn.size)]]
    of = len(blob); blob += flat.astype(np.float32).tobytes(); look['flat'] = [of, int(flat.size)]
    on = len(blob); blob += nsm.astype(np.float32).tobytes(); look['nor'] = [on, int(nsm.size)]
    moved = np.nonzero(np.linalg.norm(Q - P, axis=1) > 1e-6)[0].astype(np.uint16)
    mi = len(blob); blob += moved.tobytes(); blob = pad(blob)
    mp = len(blob); blob += Q[moved].astype(np.float32).tobytes(); mn = len(blob); blob += nsm[moved].astype(np.float32).tobytes()
    look['move'] = {'idx': [mi, int(moved.size)], 'pos': [mp, int(moved.size * 3)], 'nor': [mn, int(moved.size * 3)]}
    open(os.path.join(pkg, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(pkg, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look %d B: %d vertices moved' % (len(blob), moved.size))


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
