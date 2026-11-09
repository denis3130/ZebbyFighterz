#!/usr/bin/env python3
"""The sides and the back of Ren's new head drawn clean (9/11/2026, Denis on two close-ups of the temples, the ears and
the nape: "capelli ed orecchie non sono uniformi"): Meshy painted them in soft blotches (the ears a sketch of brown
strokes, white and black specks, a light streak behind the eyes, the hair's highlights blurred, skin showing between the
locks); the sheets (docs/ref/personaggi/ren_testa_3viste.png) have flat colours with crisp shapes: the hair in its dark,
its colour and its light, the skin flat with the ears' and the neck's shadows as clean shapes, the scalp between the
locks in the hair's dark.

head_sides(t, Q, N, UV, I, skin_rgb) paints t (the head's texture, h x w x 3 float) in place, on the triangles I of the
head (positions Q, normals N, uvs UV) in SIDES (not the face: the face, approved, is not touched), called by
tools/ren_head.py once the face and the eyes are drawn:
- each texel is hair or skin: its colour's (hair: dark and greyish; skin: light and warm; others: unknown), averaged on
  the model around it (a gaussian of SIDES_SMOOTH[0] m, on the same surface: normals within SIDES_SAME), cut at its half;
- the skin under a lock on the cranium (above SCALP[3] m; along its normal a hair triangle within SCALP[0] m, its weight
  exp(-d / SCALP[1]) over SCALP[2]): the scalp, in the hair's dark;
- the hair: its brightness averaged the same way (SIDES_SMOOTH[1] m) and cut into the palette's three tones (HAIR_TONES:
  dark, colour, light at the thresholds HAIR_CUTS), the darkest cores in ink;
- the skin: flat (skin_rgb), its marks crisp: their darkness (from the skin's down to SKIN_MARK[0] of its brightness)
  averaged (SIDES_SMOOTH[2] m) and cut at [1], in the sheets' shadow tone (SKIN_SHADE of the skin), the darkest cores
  ([2]) toward the ink; under the locks the hair's shadow in the same tone (SHADOW: as in the sheets, a band under the
  hair at the temples, the ears and the nape);
- the thin pieces (the locks, their undersides painted in skin and pink by Meshy: light slivers between the locks) in
  the hair's colours (THIN).
fill_holes(...) closes the head's small holes on the sides and the back (HOLES).
"""
import numpy as np
from scipy.spatial import cKDTree

# where (the head's own axis, x and z; from the front, degrees: fully from [2], none under [3]; heights, m, fading over [6])
SIDES = (.006, -.005, 62., 52., 1.452, 1.665, .012)
SIDES_SMOOTH, SIDES_SAME, SIDES_K = (.0012, .0008, .0007), .6, 40
SCALP = (.015, .005, .35, 1.625)   # ([3]: only above that height, m: the cranium; under it the skin under the locks is in their shadow)
SHADOW, SHADOW_L = (.04, .001, .0012), np.array([0., .75, .65]) / np.hypot(.75, .65)
THIN, EAR_BOX = .009, (.045, .105, 1.545, 1.615, -.04, .03)   # (the thin pieces: see head_sides; the ears: |x| from the axis, y, z, m)
HAIR_TONES = np.array([[22., 20, 26], [58, 48, 58], [75, 64, 73], [113, 94, 102]])   # ink, dark, colour, light
HAIR_CUTS = (34., 62., 90.)   # (brightness: ink | dark | colour | light)
SKIN_MARK, SKIN_SHADE = (.6, .45, .8), np.array([.82, .74, .72])
INK = np.array([22., 20, 26])


def _smooth3(x, a, b):
    u = np.clip((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u)


def surface_mean(pos, nor, val, sigma, mask_src=None, k=SIDES_K):
    """val (n, or n x c) averaged around each point on the model: a gaussian of sigma m over its k nearest within 3
    sigma whose normals are within SIDES_SAME (the same surface: not a lock over the skin under it); mask_src: only those
    points as sources (the others' val unused)."""
    src = np.arange(len(pos)) if mask_src is None else np.nonzero(mask_src)[0]
    v = val[src]; tree = cKDTree(pos[src]); out = np.zeros(val.shape, float); wsum = np.zeros(len(pos))
    for s in range(0, len(pos), 60000):
        p = pos[s:s + 60000]; dd, jj = tree.query(p, k=min(k, len(src)), distance_upper_bound=3 * sigma)
        ok = np.isfinite(dd); jj = np.where(ok, jj, 0)
        ok &= (nor[s:s + 60000][:, None, :] * nor[src][jj]).sum(2) > SIDES_SAME
        w = np.exp(-.5 * (np.where(ok, dd, 0) / sigma) ** 2) * ok; ws = w.sum(1)
        if v.ndim == 1: out[s:s + 60000] = (w * v[jj]).sum(1) / np.maximum(ws, 1e-12)
        else: out[s:s + 60000] = (w[..., None] * v[jj]).sum(1) / np.maximum(ws, 1e-12)[:, None]
        wsum[s:s + 60000] = ws
    return out, wsum


def _ray_hits(O, D, A, B, C, maxd):
    """Rays O + t D against the triangles (A, B, C): per ray the nearest t in (1e-4, maxd), or inf."""
    out = np.full(len(O), np.inf); e1, e2 = B - A, C - A
    for s in range(0, len(O), 256):
        o, d = O[s:s + 256, None, :], D[s:s + 256, None, :]
        p = np.cross(d, e2[None]); det = (e1[None] * p).sum(2); ok = np.abs(det) > 1e-12; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        tv = o - A[None]; u = (tv * p).sum(2) * inv; q = np.cross(tv, e1[None]); v = (d * q).sum(2) * inv; tt = (e2[None] * q).sum(2) * inv
        out[s:s + 256] = np.where(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (tt > 1e-4) & (tt < maxd), tt, np.inf).min(1)
    return out


def _classes(c):
    """Per texel colour: 1 hair (dark, greyish purple), 0 skin (light, warm), .5 neither."""
    lum = c.mean(1); r, g, b = c[:, 0], c[:, 1], c[:, 2]
    hair = (lum < 135) & (r - b < 30) & (r - g < 40)
    skin = (r > 150) & (r - b > 45)
    return np.where(hair, 1., np.where(skin, 0., .5))


def head_sides(t, Q, N, UV, I, skin_rgb=None, debug=None, posterize=True):
    from paint_views import texel_table
    TS = t.shape[0]; C = Q[I].mean(1)
    x0, z0, ph1, ph0, y0, y1, fy = SIDES
    phi = lambda P: np.degrees(np.abs(np.arctan2(P[:, 0] - x0, P[:, 2] - z0)))
    tri = np.nonzero((phi(C) > ph0 - 3) & (C[:, 1] > y0 - .005) & (C[:, 1] < y1 + fy + .005))[0]
    ys, xs, ks, bary, pos, nor = texel_table(Q, N, UV, I[tri], TS)
    w_reg = _smooth3(phi(pos), ph0, ph1) * _smooth3(pos[:, 1], y0 - .001, y0 + .004) * (1 - _smooth3(pos[:, 1], y1, y1 + fy))
    sel = w_reg > 0; ys, xs, ks, bary, pos, nor, w_reg = ys[sel], xs[sel], ks[sel], bary[sel], pos[sel], nor[sel], w_reg[sel]
    c0 = t[ys, xs].copy(); lum = c0.mean(1)
    if skin_rgb is None:   # (the skin's colour: its texels' there, the light ones)
        sk0 = (_classes(c0) == 0) & (lum > np.percentile(lum[_classes(c0) == 0], 40)) if (_classes(c0) == 0).sum() > 100 else _classes(c0) == 0
        skin_rgb = np.median(c0[sk0], 0) if sk0.sum() > 10 else np.array([248., 177, 125])
    skin_rgb = np.asarray(skin_rgb, float)
    vr = np.unique(I[tri]); tree_all = cKDTree(C)
    # the thin pieces (the locks, their undersides painted in skin and pink by Meshy): per vertex, into the surface (along
    # -normal), another surface within THIN m; not in the ears (EAR_BOX: thin there too)
    A, B, Cc = Q[I[:, 0]], Q[I[:, 1]], Q[I[:, 2]]; thick = np.full(len(Q), np.inf)
    for s in range(0, len(vr), 1500):
        vv = vr[s:s + 1500]; near = tree_all.query_ball_point(Q[vv], THIN + .01)
        cand = np.unique(np.concatenate([np.array(n, int) for n in near if len(n)] or [np.zeros(0, int)]))
        if len(cand): thick[vv] = _ray_hits(Q[vv] - N[vv] * 1e-4, -N[vv], A[cand], B[cand], Cc[cand], THIN)
    thin_v = np.isfinite(thick).astype(float); thin = (thin_v[I[tri][ks]] * bary).sum(1) > .5
    ax_ = np.abs(pos[:, 0] - x0); e = EAR_BOX
    in_ear = (ax_ > e[0]) & (ax_ < e[1]) & (pos[:, 1] > e[2]) & (pos[:, 1] < e[3]) & (pos[:, 2] > e[4]) & (pos[:, 2] < e[5])
    # hair or skin: the colour's class, the thin pieces hair, averaged on the model around each texel
    cls = _classes(c0); cls = np.where(thin & ~in_ear, 1., cls)
    hs, _ = surface_mean(pos, nor, cls, SIDES_SMOOTH[0])
    is_hair = _smooth3(hs, .45, .55)
    # the scalp under the locks: per vertex, along its normal, a hair triangle near
    tc = t[np.clip((UV[I, 1].mean(1) * TS).astype(int), 0, TS - 1), np.clip((UV[I, 0].mean(1) * TS).astype(int), 0, TS - 1)]
    hair_t = np.nonzero(_classes(tc) == 1)[0]; hitd = np.full(len(Q), np.inf)
    if len(hair_t):
        Ah, Bh, Ch = Q[I[hair_t, 0]], Q[I[hair_t, 1]], Q[I[hair_t, 2]]; tree = cKDTree(C[hair_t])
        for s in range(0, len(vr), 1500):
            vv = vr[s:s + 1500]; near = tree.query_ball_point(Q[vv], SCALP[0] + .01)
            cand = np.unique(np.concatenate([np.array(n, int) for n in near if len(n)] or [np.zeros(0, int)]))
            if len(cand): hitd[vv] = _ray_hits(Q[vv] + N[vv] * 1e-4, N[vv], Ah[cand], Bh[cand], Ch[cand], SCALP[0])
    cv = np.where(np.isfinite(hitd), np.exp(-hitd / SCALP[1]), 0.); cov = (cv[I[tri][ks]] * bary).sum(1)
    scalp = (1 - is_hair) * _smooth3(cov, SCALP[2] - .03, SCALP[2] + .03) * ~in_ear * _smooth3(pos[:, 1], SCALP[3] - .006, SCALP[3] + .006)
    # the hair's shadow on the skin under it (the sheets: a band of the skin's shadow tone under the locks, at the temples,
    # the ears and the nape): rays toward the light (SHADOW_L) from the skin, sampled every SHADOW[1] m, against the hair;
    # averaged on the model (a gaussian of SHADOW[2] m) and cut at its half
    k_sh = np.zeros(len(ys))
    skin_s = np.nonzero((is_hair < .5) & (nor @ SHADOW_L > .05))[0]
    if len(skin_s) and len(hair_t):
        key = np.floor(pos[skin_s] / SHADOW[1]).astype(np.int64); _, first_s = np.unique(key, axis=0, return_index=True); smp = skin_s[first_s]
        Ah, Bh, Ch = Q[I[hair_t, 0]], Q[I[hair_t, 1]], Q[I[hair_t, 2]]; treeh = cKDTree(C[hair_t]); hit_s = np.zeros(len(smp))
        for s0 in range(0, len(smp), 400):
            ss = smp[s0:s0 + 400]; mid = pos[ss] + SHADOW_L * SHADOW[0] / 2
            near = treeh.query_ball_point(mid, SHADOW[0] / 2 + .012)
            cand = np.unique(np.concatenate([np.array(n, int) for n in near if len(n)] or [np.zeros(0, int)]))
            if len(cand): hit_s[s0:s0 + 400] = np.isfinite(_ray_hits(pos[ss] + nor[ss] * 3e-4, np.repeat(SHADOW_L[None], len(ss), 0), Ah[cand], Bh[cand], Ch[cand], SHADOW[0]))
        tree_s = cKDTree(pos[smp]); dd, jj = tree_s.query(pos, k=12, distance_upper_bound=3 * SHADOW[2]); okk = np.isfinite(dd); jj = np.where(okk, jj, 0)
        okk &= (nor[:, None, :] * nor[smp][jj]).sum(2) > SIDES_SAME
        gw = np.exp(-.5 * (np.where(okk, dd, 0) / SHADOW[2]) ** 2) * okk; sv = (gw * hit_s[jj]).sum(1) / np.maximum(gw.sum(1), 1e-9)
        k_sh = _smooth3(sv, .42, .58) * (gw.sum(1) > 1e-6) * (1 - is_hair)
    # the hair: its own colours where they are the hair's (dark, greyish), the others (skin, pink, white, brown on the
    # locks) the nearest of those on the same surface; then its brightness averaged and cut into the palette's tones
    good = (cls == 1) & ~thin | ((cls == 1) & thin)
    good &= _classes(c0) == 1
    hair_c = c0.copy()
    bad = (hs > .5) & ~good
    if bad.any() and good.any():
        tg = cKDTree(pos[good]); dd, jj = tg.query(pos[bad], k=8)
        same = (nor[bad][:, None, :] * nor[good][jj]).sum(2) > SIDES_SAME
        wgt = np.where(same, 1., .05) / np.maximum(dd, 1e-5); hair_c[bad] = (wgt[..., None] * c0[good][jj]).sum(1) / wgt.sum(1)[:, None]
    if posterize:
        lh, _ = surface_mean(pos, nor, hair_c.mean(1), SIDES_SMOOTH[1], mask_src=hs > .5)
        k_ink, k_dark, k_light = _smooth3(lh, HAIR_CUTS[0] - 3, HAIR_CUTS[0] + 3), _smooth3(lh, HAIR_CUTS[1] - 3, HAIR_CUTS[1] + 3), _smooth3(lh, HAIR_CUTS[2] - 3, HAIR_CUTS[2] + 3)
        hair_rgb = HAIR_TONES[0][None] * (1 - k_ink[:, None]) + HAIR_TONES[1][None] * k_ink[:, None]
        hair_rgb = hair_rgb * (1 - k_dark[:, None]) + HAIR_TONES[2][None] * k_dark[:, None]
        hair_rgb = hair_rgb * (1 - k_light[:, None]) + HAIR_TONES[3][None] * k_light[:, None]
    else:
        hair_rgb = hair_c; k_dark = k_light = np.zeros(len(ys))
    # the skin: flat, its marks crisp (their darkness averaged on the skin only)
    Ls = skin_rgb.mean(); dk = np.clip((Ls - lum) / (Ls * (1 - SKIN_MARK[0])), 0, 1)
    sk = (hs <= .5)
    ds, _ = surface_mean(pos, nor, dk, SIDES_SMOOTH[2], mask_src=sk)
    am, core = _smooth3(ds, SKIN_MARK[1] - .04, SKIN_MARK[1] + .04), _smooth3(ds, SKIN_MARK[2] - .05, SKIN_MARK[2] + .05)
    am = np.maximum(am, k_sh)   # (the hair's shadow and the marks: one tone)
    skin_px = skin_rgb[None] * (1 - am[:, None]) + (skin_rgb * SKIN_SHADE)[None] * am[:, None]
    skin_px = skin_px * (1 - .5 * core[:, None]) + INK[None] * .5 * core[:, None]
    # together: skin, the scalp under the locks in the hair's dark, the hair
    new = skin_px * (1 - scalp[:, None]) + HAIR_TONES[1][None] * scalp[:, None]
    new = new * (1 - is_hair[:, None]) + hair_rgb * is_hair[:, None]
    t[ys, xs] = c0 * (1 - w_reg[:, None]) + new * w_reg[:, None]
    if debug is not None: debug.update(ys=ys, xs=xs, pos=pos, hs=hs, cov=cov, scalp=scalp, ds=ds, w=w_reg, thin=thin, in_ear=in_ear, k_sh=k_sh)
    print('head sides: skin %s' % np.round(skin_rgb).astype(int).tolist())
    print('head sides: %d texels redrawn (%d hair, %d of them thin pieces or specks not in its colours; %d scalp under the '
          'locks in its dark; %d skin: %d in its marks\' or the hair\'s shadow, %d of them the hair\'s)' % (len(ys), int((is_hair > .5).sum()), int(bad.sum()),
                                                                     int((scalp > .5).sum()), int((is_hair <= .5).sum()), int(((is_hair <= .5) & (am > .5)).sum()), int((k_sh > .5).sum())))
    return skin_rgb


# the head's small holes on its sides and back (9/11/2026: at the temples, between the locks, Meshy's mesh and the cuts
# left holes up to a few cm long; through them, the head's inside and the outline's black showed as specks and dashes):
# the boundary loops (and loops touching at a point) of at most HOLES[0] edges and HOLES[1] m long, their centre in SIDES (from HOLES[2] degrees), closed
# by a fan from their centre in a flat colour (the hair's dark or the skin, by the colour around them)
HOLES = (16, .12, 38.)


def fill_holes(Q, N, UV, I, J, W, lb, tex, taken, skin_rgb):
    """Q, N, UV, I, J, W, lb: the head (positions, normals, uvs, triangles, skin joints and weights, outline push); tex:
    its texture (to tell the colour around each hole); taken: blocks of the texture already used [(row, col, half)].
    Returns (Q, N, UV, I, J, W, lb with the fans added, the flat blocks [(row, col, half, rgb)])."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from ren_collar import free_blocks
    TS = tex.shape[0]
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    T = weld[I]; E = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
    Eu, cnt = np.unique(E, axis=0, return_counts=True); bd = Eu[cnt == 1]
    if not len(bd): return Q, N, UV, I, J, W, lb, []
    nw = len(first); lab = connected_components(coo_matrix((np.ones(len(bd)), (bd[:, 0], bd[:, 1])), shape=(nw, nw)), directed=False)[1]
    le = lab[bd[:, 0]]; Pw = Q[first]; x0, z0, _, _, y0, y1, _ = SIDES
    loops = []
    for l in np.unique(le):
        e = bd[le == l]; vs = np.unique(e)
        if len(e) > HOLES[0]: continue   # (loops touching at a point too: one fan over them)
        L = np.linalg.norm(Pw[e[:, 0]] - Pw[e[:, 1]], axis=1).sum(); c = Pw[vs].mean(0)
        ph = np.degrees(np.abs(np.arctan2(c[0] - x0, c[2] - z0)))
        if L <= HOLES[1] and ph >= HOLES[2] and y0 < c[1] < y1 + .04: loops.append(e)
    if not loops: return Q, N, UV, I, J, W, lb, []
    # the orientation of each boundary edge as a triangle has it (the fan's triangles run the other way)
    dirE = {}
    for tri in T:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])): dirE[(a, b)] = True
    (r0, c0, b0), (r1, c1, b1) = free_blocks(UV, I, TS, 2, half=10, taken=taken)
    uv_hair, uv_skin = np.array([(c0 + .5) / TS, (r0 + .5) / TS]), np.array([(c1 + .5) / TS, (r1 + .5) / TS])
    # (a vertex of the head at each welded point: its skin and normal)
    rep = first
    newP, newN, newUV, newJ, newW, newT = [], [], [], [], [], []
    n0 = len(Q); nadd = 0; n_tri = 0
    for e in loops:
        vs = np.unique(e); col = tex[np.clip((UV[rep[vs], 1] * TS).astype(int), 0, TS - 1), np.clip((UV[rep[vs], 0] * TS).astype(int), 0, TS - 1)]
        hair = (col.mean(1) < 135).mean() > .5
        uvf = uv_hair if hair else uv_skin
        # the fan: the loop's points copied (in the flat colour), its centre
        idx = {}
        for v in vs:
            idx[v] = n0 + nadd; nadd += 1; newP.append(Pw[v]); newN.append(N[rep[v]]); newUV.append(uvf); newJ.append(J[rep[v]]); newW.append(W[rep[v]])
        cen = n0 + nadd; nadd += 1; newP.append(Pw[vs].mean(0)); nn = N[rep[vs]].mean(0); newN.append(nn / max(np.linalg.norm(nn), 1e-9)); newUV.append(uvf)
        acc = {}
        for v in vs:
            for k in range(4): acc[J[rep[v], k]] = acc.get(J[rep[v], k], 0) + W[rep[v], k] / len(vs)
        top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; jj = [k for k, _ in top4] + [0] * (4 - len(top4)); ww = np.array([w for _, w in top4] + [0] * (4 - len(top4)))
        newJ.append(np.array(jj, J.dtype)); newW.append((ww / max(ww.sum(), 1e-9)).astype(W.dtype))
        for a, b in e:
            if (a, b) in dirE: newT.append((idx[b], idx[a], cen))   # (the edge a->b is a triangle's: the fan's runs b->a)
            else: newT.append((idx[a], idx[b], cen))
            n_tri += 1
    Q2 = np.r_[Q, np.array(newP)]; N2 = np.r_[N, np.array(newN)]; UV2 = np.r_[UV, np.array(newUV)]
    J2 = np.r_[J, np.array(newJ, J.dtype)]; W2 = np.r_[W, np.array(newW, W.dtype)]; lb2 = np.r_[lb, np.zeros(nadd, lb.dtype)]
    I2 = np.r_[I, np.array(newT, I.dtype)]
    print('head: %d small holes on its sides and back closed (%d triangles)' % (len(loops), n_tri))
    return Q2, N2, UV2, I2, J2, W2, lb2, [(r0, c0, b0, HAIR_TONES[1]), (r1, c1, b1, np.array(skin_rgb, float))]
