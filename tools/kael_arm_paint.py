#!/usr/bin/env python3
"""Kael's Meshy forearms painted as the sheet draws them (19/11/2026, Denis on the forearms from Meshy: "passaci col disegno
rendila più simile a quella di Ren, intendo le dita ecc, e fixa dove è fatta male"; docs/meshy/KAEL.md, "Avambracci da
Meshy"). Meshy's paint: soft colours with jagged edges between them (the bands' rims, the glove's edge), the fingers plain,
their creases barely hinted. Here, per texel (its point on the model: tools/paint_views.py texel_table):

- the colours flat, the bust's palette (tools/kael_bust_attach.py): each texel the class its neighbours within CLEAN m on
  the model mostly have (skin, the glove's and bracer's plum, the bands' purple), so the edges between them are smooth;
- the ink of the sheet: a line INK_W m wide along every edge between the classes (the glove's edge, the bands' rims);
- the fingers drawn as Ren's: dark lines where the skin folds or another part of it lies close in front (between the
  fingers, in the fist the fingers against the palm and the thumb over them: a ball CREASE m wide resting on the skin there
  holds other skin), and Meshy's own faint lines (its nails, its joints: skin LINE_DARK darker than the skin round it).

Sizes in metres on Kael (the model's units times UNIT: its hand's scale on him, tools/kael_bust_attach.py arm_parts).

usage: python3 tools/kael_arm_paint.py IN.glb OUT.png [DEBUG.png [FULL.glb]]   (FULL: the model before its lightening, for its valleys)"""
import io, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
import glbio
from paint_views import texel_table

UNIT = .19                       # m per model unit on Kael's hands (about: 0.15-0.17 m per unit, the hand 1.14 times)
CLEAN, INK_W, CREASE = .0028, .0011, .0028   # m: the classes' vote's reach; the ink lines' width; the crease ball's diameter
FACING = .3                      # the creases: the skin in the ball facing the texel's (normals over 107 degrees apart)
VALLEY = 400.                     # the full model's valleys drawn: deeper than this (1/m: a crease's mean curvature)
JOINTS, JOINT_W, JOINT_STEP, JOINT_MIN, JOINT_THUMB = (), .0013, .0012, .02, .028   # the fingers' joints (off: tried (.42, .72), the distance from the glove's edge drew a loop on the thumb, none on the fingers): at these shares of their length from the glove, so wide (m); the texels thinned to so far apart (m); a finger at least so much of the skin; under so long (m) a thumb (one joint)
LINE_DARK = 22                   # Meshy's lines on the skin: so much darker (0-255) than the skin round them
SKIN, PLUM, PURPLE = 0, 1, 2
PAL = {SKIN: (250, 191, 151), PLUM: (65, 49, 74), PURPLE: (166, 92, 203)}   # the bust's palette (tools/kael_bust_attach.py)
INK, CREASE_C = (9, 6, 9), (88, 42, 34)   # the ink; the skin's lines (Ren's: a dark brown, not black, inside the skin)


def classes(c):
    """per colour (n, 3) 0-255 its class: skin, purple, else plum"""
    skin = (c[:, 0] > 150) & (c[:, 0] - c[:, 2] > 35)
    pur = ~skin & (c[:, 2] > 120) & (c[:, 2] - c[:, 1] > 50)
    return np.where(skin, SKIN, np.where(pur, PURPLE, PLUM))


def valleys(glb):
    """per vertex of the full Meshy model (before its lightening: its creases a millimetre wide) how deep a valley it sits
    in: the mean of its neighbours past it along its normal, over the square of their mean distance (1/units)"""
    m = glbio.read(glb); P, I = m['pos'].astype(float), m['idx'].astype(np.int64)
    key = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True)[1].ravel()   # (welded: Meshy's seams)
    n = key.max() + 1; Q = np.zeros((n, 3)); np.add.at(Q, key, P); Q /= np.bincount(key, minlength=n)[:, None]
    E = key[np.r_[I[:, [0, 1]], I[:, [1, 2]], I[:, [2, 0]]]]; E = np.unique(np.sort(E, 1), axis=0); E = E[E[:, 0] != E[:, 1]]
    deg = np.bincount(E.ravel(), minlength=n).astype(float); S_ = np.zeros((n, 3)); np.add.at(S_, E[:, 0], Q[E[:, 1]]); np.add.at(S_, E[:, 1], Q[E[:, 0]])
    ln = np.zeros(n); l = np.linalg.norm(Q[E[:, 0]] - Q[E[:, 1]], axis=1); np.add.at(ln, E[:, 0], l); np.add.at(ln, E[:, 1], l); ln /= np.maximum(deg, 1)
    Nv = np.zeros((n, 3)); f = key[I]; fn = np.cross(Q[f[:, 1]] - Q[f[:, 0]], Q[f[:, 2]] - Q[f[:, 0]])
    for k in range(3): np.add.at(Nv, f[:, k], fn)
    Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-12)
    v = ((S_ / np.maximum(deg, 1)[:, None] - Q) * Nv).sum(1) / np.maximum(ln, 1e-9) ** 2
    return Q, Nv, v


def joints(pos, nor, skin, cut, glove, mode, u):
    """the fingers' joints drawn as Ren's (19/11): per finger (a piece of skin on its own once the lines between the
    fingers cut it, JOINT_MIN of the skin's texels at least) the distance along it from the glove's edge (Dijkstra over
    the texels thinned to JOINT_STEP m, their neighbours within 2.5 steps); across it a line JOINT_W wide at JOINTS of its
    length (its last for the thumb, the shortest), all round it. Returns the texels on them."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components, dijkstra
    on = np.nonzero(skin & ~cut)[0]; step = JOINT_STEP * u
    key = np.floor(pos[on] / step).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    sp = on[first]; tr = cKDTree(pos[sp]); pairs = tr.query_pairs(2.5 * step, output_type='ndarray')
    w = np.linalg.norm(pos[sp[pairs[:, 0]]] - pos[sp[pairs[:, 1]]], axis=1)
    G = coo_matrix((w, (pairs[:, 0], pairs[:, 1])), shape=(len(sp), len(sp))).tocsr()
    nc, lab = connected_components(G, directed=False)
    gd, _ = cKDTree(pos[glove]).query(pos[sp]); src = np.nonzero(gd < 2 * step)[0]
    out = np.zeros(len(pos), bool); n_f = 0; c0 = pos[skin].mean(0)
    sizes = np.bincount(lab, minlength=nc)
    if (sizes > JOINT_MIN * len(sp)).sum() < 4:   # (the fingers not apart: no joints rather than wrong ones)
        print('joints: the fingers are not apart (%d pieces): none drawn' % int((sizes > JOINT_MIN * len(sp)).sum())); return out
    for c in np.nonzero(sizes > JOINT_MIN * len(sp))[0]:
        mem = lab == c; s_ = src[mem[src]]
        if not len(s_): continue
        d = dijkstra(G, directed=False, indices=s_, min_only=True); d = np.where(mem, d, np.inf); L = d[mem].max()
        if not np.isfinite(L) or L < 3 * step: continue
        n_f += 1
        # (the texels of this finger: their thinned point's distance)
        # (each texel's distance smooth: the mean of its 6 nearest thinned points', by their nearness; the nearest alone
        # made the lines dashes a step long)
        mi = np.nonzero(mem & np.isfinite(d))[0]; tt = on[mem[lab[inv]] & np.isfinite(d[inv])]
        dq, iq = cKDTree(pos[sp[mi]]).query(pos[tt], 6); wq = 1 / np.maximum(dq, .2 * step) ** 2; dd = (d[mi][iq] * wq).sum(1) / wq.sum(1)
        back = np.ones(len(tt), bool)   # (both sides: the joints' creases go round the finger, as Ren's)
        fr = JOINTS if L > JOINT_THUMB * u else JOINTS[-1:]
        for f in fr:
            out[tt[back & (np.abs(dd - f * L) < JOINT_W / 2 * u)]] = True
    print('joints: %d fingers, %d texels' % (n_f, int(out.sum())))
    return out


def main(src, out, debug=None, full=None):
    m = glbio.read(src); P, N, UV, I = m['pos'].astype(float), m['nor'].astype(float), m['uv'].astype(float), m['idx'].astype(np.int64)
    T = np.asarray(Image.open(io.BytesIO(m['img'])).convert('RGB')).astype(int); S = T.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, S)
    col = T[ys, xs]; cl = classes(col); tree = cKDTree(pos); u = 1 / UNIT
    def near(k, f):   # (per texel f of its k nearest texels on the model (their indices, distances), in blocks: the memory)
        out = []
        for a in range(0, len(pos), 200000):
            d, q = tree.query(pos[a:a + 200000], k, workers=-1); out.append(f(q, d))
        return np.concatenate(out)
    # (the classes cleaned: each texel the class most of its neighbours within CLEAN on the model have, twice: islands of a
    # few texels go)
    cl2 = cl.copy()
    for _ in range(3):
        def vote(q, d, c_=cl2): v = np.stack([((c_[q] == c) & (d < CLEAN * u)).sum(1) for c in range(3)], 1); return v.argmax(1)
        cl2 = near(48, vote)
    print('classes cleaned: %d of %d texels changed (skin %d, plum %d, purple %d)' % (int((cl2 != cl).sum()), len(cl), *np.bincount(cl2, minlength=3)))
    out_c = np.array([PAL[c] for c in cl2], float)
    # (the ink along the edges between the classes: a texel of another class within INK_W/2)
    ink = near(16, lambda q, d: ((cl2[q] != cl2[q[:, :1]]) & (d < INK_W / 2 * u)).any(1))
    # (the skin's creases: a ball of CREASE diameter resting on the skin at the texel holds skin facing it (finger against
    # finger, a finger's bones folded on each other), not merely the skin of a hollow)
    sk = np.nonzero(cl2 == SKIN)[0]; r = CREASE / 2 * u; crease = np.zeros(len(pos), bool); skin_ = cl2 == SKIN
    for a in range(0, len(sk), 40000):
        b = sk[a:a + 40000]; L_ = tree.query_ball_point(pos[b] + nor[b] * r * 1.02, r * .95, workers=-1)
        crease[b] = [len(q) > 2 and ((nor[q] @ nor[i] < -FACING) & skin_[q]).sum() > 2 for i, q in zip(b, L_)]
    # (Meshy's own faint lines on the skin: LINE_DARK darker than the skin round them on the model (its 64 nearest texels);
    # kept only where they make lines, not dots: over a third of their neighbours as dark)
    L = col.sum(1) / 3.; Lsk = np.where(cl2 == SKIN, L, np.nan)
    faint = near(64, lambda q, d: (np.nanmedian(Lsk[q], 1) - L[q[:, 0]]) > LINE_DARK) & (cl2 == SKIN)
    faint &= near(16, lambda q, d: faint[q].mean(1) > .35)
    # (the valleys of the full model's skin: its folds between the fingers' bones, the knuckles' creases; a texel the valley of
    # the full model's vertex nearest it, facing the same way)
    valley = np.zeros(len(pos), bool)
    if full:
        Q, Nq, v = valleys(full); fq = cKDTree(Q)
        dq, iq = [], []
        for a in range(0, len(pos), 200000):
            d_, q_ = fq.query(pos[a:a + 200000], 4, workers=-1); dq.append(d_); iq.append(q_)
        dq, iq = np.concatenate(dq), np.concatenate(iq)
        ok = (np.einsum('nkj,nj->nk', Nq[iq], nor) > .5); vv = np.where(ok, v[iq], 0).max(1)
        valley = (cl2 == SKIN) & (vv > VALLEY * UNIT)
        valley &= near(16, lambda q, d: valley[q].mean(1) > .3)
        print('valleys: %d texels (the full model\'s %d vertices, %.0f%% of its skin\'s over %.0f /m)' % (int(valley.sum()), len(Q), 100 * valley.sum() / max(1, (cl2 == SKIN).sum()), VALLEY))
    jt = joints(pos, nor, cl2 == SKIN, crease | ink | valley, cl2 == PLUM, 'fist' if 'pugno' in os.path.basename(src) else 'open', u) if JOINTS else np.zeros(len(pos), bool)
    lines = (crease | faint | valley | jt) & ~ink
    out_c[lines] = CREASE_C; out_c[ink] = INK
    print('ink: %d texels on the edges; skin lines: %d (creases %d, Meshy\'s %d)' % (int(ink.sum()), int(lines.sum()), int(crease.sum()), int(faint.sum())))
    O = T.astype(float).copy(); O[ys, xs] = out_c
    # (the texels outside the triangles: their nearest painted one's colour, so the filtering at the seams stays clean)
    filled = np.zeros((S, S), bool); filled[ys, xs] = True
    _, (iy, ix) = ndimage.distance_transform_edt(~filled, return_indices=True); O = O[iy, ix]
    Image.fromarray(O.clip(0, 255).astype(np.uint8)).save(out)
    print('written: %s (%dx%d)' % (out, S, S))
    if debug:
        D = np.full((S, S, 3), 128, np.uint8); D[ys, xs] = np.array([PAL[c] for c in cl2]); D[ys[crease], xs[crease]] = (255, 0, 0); D[ys[faint], xs[faint]] = (0, 200, 0); D[ys[valley], xs[valley]] = (0, 0, 255); D[ys[jt], xs[jt]] = (255, 255, 0); D[ys[ink], xs[ink]] = 0
        Image.fromarray(D).save(debug)


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
