#!/usr/bin/env python3
"""Kael's hands and wrists remade (17/11/2026; docs/superpowers/specs/2026-11-17-kael-mani-polso-design.md): the pieces
tools/kael_bust_attach.py writes beside his bust, as parts of his package (src/e_model.js mdPartData).

- crop_paint: Ren's paint cut out round his hands, pixel for pixel (no resampling: the hands keep his paint as on him).
- write_part: a part's json and bin (and its texture), in the bust's format."""
import json, os
import numpy as np


def crop_paint(img, uv, pad=4):
    """img (PIL) cropped to the pixels uv (n, 2) cover, pad pixels more on each side; uv remapped into the crop.
    The crop starts on whole pixels, so every texel keeps its colour and its place among its neighbours."""
    w, h = img.size; x, y = uv[:, 0] * w, uv[:, 1] * h
    x0, y0 = max(0, int(np.floor(x.min())) - pad), max(0, int(np.floor(y.min())) - pad)
    x1, y1 = min(w, int(np.ceil(x.max())) + pad), min(h, int(np.ceil(y.max())) + pad)
    return img.crop((x0, y0, x1, y1)), np.c_[(x - x0) / (x1 - x0), (y - y0) / (y1 - y0)]


def write_part(folder, name, arrays, extra=None, img=None, fmt='jpg'):
    """<folder>/<name>.json|.bin (and .jpg or .png): arrays in order, each as [byte offset, count] in the bin (4-byte
    aligned); 'idx' as uint16 under 65536 vertices, else uint32; 'jnt' as uint8; 'hide' an empty uint32 block unless
    given (mdPartData reads it); extra merged into the json."""
    pad = lambda b: b + b'\0' * (-len(b) % 4)
    n = len(arrays['pos']); blob = b''; jo = {'v': 1, 'verts': int(n), 'tris': int(len(arrays['idx']))}
    arrays = dict(arrays); arrays.setdefault('hide', np.zeros(0, np.uint32))
    for k, a in arrays.items():
        a = np.asarray(a)
        if k == 'idx': a = a.astype(np.uint16 if n < 65536 else np.uint32)
        elif k == 'jnt': a = a.astype(np.uint8)
        elif k in ('hide',): a = a.astype(np.uint32)
        elif k in ('near',): a = a.astype(np.int32)
        else: a = a.astype(np.float32)
        blob = pad(blob); jo[k] = [len(blob), int(a.size)]; blob += np.ascontiguousarray(a).tobytes()
    jo.update(extra or {})
    open(os.path.join(folder, name + '.bin'), 'wb').write(pad(blob))
    json.dump(jo, open(os.path.join(folder, name + '.json'), 'w'), separators=(',', ':'))
    if img is not None:
        if fmt == 'png': img.save(os.path.join(folder, name + '.png'), optimize=True)
        else: img.convert('RGB').save(os.path.join(folder, name + '.jpg'), quality=95)


def clip_iso(P, N, W, D, I):
    """The triangles I cut along D = 0, the part with D <= 0 kept (Sutherland-Hodgman on each triangle, fanned back into
    triangles in the same winding). A cut vertex is shared by the triangles on its edge; its position, normal (unit),
    weights (rows of W, dense) and D (0) interpolated along the edge. Returns P, N, W, D, I with the unused vertices dropped."""
    P, N, W, D = (np.asarray(a, float) for a in (P, N, W, D)); out_v = [P], [N], [W], [D]
    n = [len(P)]; cut = {}

    def at(a, b):
        k = (min(a, b), max(a, b))
        if k not in cut:
            t = D[a] / (D[a] - D[b]); nv = N[a] + (N[b] - N[a]) * t
            out_v[0].append((P[a] + (P[b] - P[a]) * t)[None]); out_v[1].append((nv / max(np.linalg.norm(nv), 1e-12))[None])
            out_v[2].append((W[a] + (W[b] - W[a]) * t)[None]); out_v[3].append(np.zeros(1))
            cut[k] = n[0]; n[0] += 1
        return cut[k]

    tris = []
    for t in I:
        ins = D[t] <= 0
        if ins.all(): tris.append(t); continue
        if not ins.any(): continue
        poly = []
        for k in range(3):
            a, b = t[k], t[(k + 1) % 3]
            if D[a] <= 0: poly.append(a)
            if (D[a] <= 0) != (D[b] <= 0): poly.append(at(a, b))
        tris += [(poly[0], poly[k], poly[k + 1]) for k in range(1, len(poly) - 1)]
    P2, N2, W2, D2 = (np.concatenate(o) for o in out_v); I2 = np.array(tris, np.int64).reshape(-1, 3)
    used = np.unique(I2); mp = -np.ones(len(P2), np.int64); mp[used] = np.arange(len(used))
    return P2[used], N2[used], W2[used], D2[used], mp[I2]


def surface_dist(Q, P, I, r=.012):
    """each point's distance to the surface (P, I): the nearest point of the triangles with a corner within r of it"""
    from scipy.spatial import cKDTree
    tri_of = [[] for _ in range(len(P))]
    for k, t in enumerate(I):
        for v in t: tri_of[v].append(k)
    tree = cKDTree(P); out = np.full(len(Q), np.inf)
    for i, q in enumerate(Q):
        ks = np.unique([k for v in tree.query_ball_point(q, r) for k in tri_of[v]]).astype(np.int64)
        if not len(ks): continue
        A, B, C = P[I[ks, 0]], P[I[ks, 1]], P[I[ks, 2]]; out[i] = np.linalg.norm(closest_on_tris(q, A, B, C) - q, axis=1).min()
    return out


def closest_on_tris(q, A, B, C):
    """the point of each triangle (A, B, C: (n, 3)) nearest q (Ericson, Real-Time Collision Detection 5.1.5)"""
    ab, ac, ap = B - A, C - A, q - A; d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = q - B; d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1); cp = q - C; d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    den = np.where(np.abs(va + vb + vc) < 1e-30, 1e-30, va + vb + vc); v, w = vb / den, vc / den
    out = A + ab * v[:, None] + ac * w[:, None]   # (inside the face)
    sd = lambda a, b: np.where(np.abs(a - b) < 1e-30, 1e-30, a - b)
    e_bc = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0); out[e_bc] = (B + (C - B) * (((d4 - d3) / sd(d4 - d3 + d5, d6))[:, None]))[e_bc]
    e_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0); out[e_ac] = (A + ac * ((d2 / sd(d2, d6))[:, None]))[e_ac]
    e_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0); out[e_ab] = (A + ab * ((d1 / sd(d1, d3))[:, None]))[e_ab]
    c_c = (d6 >= 0) & (d5 <= d6); out[c_c] = C[c_c]
    c_b = (d3 >= 0) & (d4 <= d3); out[c_b] = B[c_b]
    c_a = (d1 <= 0) & (d2 <= 0); out[c_a] = A[c_a]
    return out


def shell(P, N, D, I, t=.002, wall=.0015, skin=None, most=.0015):
    """The glove as a real piece: the surface (P, N, D, I: the hand's skin inside the glove, cut along its edge) pushed t
    along its faces' normals (averaged over coincident vertices, so the shell has no cracks where the skin's are split), and
    along the edge (its vertices with D = 0) a strip from the shell down to wall below it: the glove's thickness, in ink.
    With skin (P, I: the whole hands' surface) the shell is pushed further where a bump of the skin round it comes nearer
    than t (Ren's skin by the wrist has 1 mm bumps), at most by most, the extra push spread over its neighbours.
    Returns P, N, D, I, ink (1 on the strip's lower vertices) and src (each vertex's surface vertex)."""
    # (pushed along the surface's own normals: the faces' (area-weighted) over coincident vertices, not the light's normals,
    # smoothed on Ren's low hands: along those the shell came within 0.3 mm of the faces round it)
    key = np.round(np.asarray(P) / 1e-6).astype(np.int64); _, grp = np.unique(key, axis=0, return_inverse=True); grp = grp.ravel()
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    Na = np.zeros((grp.max() + 1, 3)); np.add.at(Na, grp[I].ravel(), np.repeat(fn, 3, axis=0)); Na = Na[grp]
    Na /= np.maximum(np.linalg.norm(Na, axis=1, keepdims=True), 1e-12)
    if (Na * N).sum() < 0: Na = -Na   # (the faces wound the other way: outward as the given normals)
    extra = np.zeros(len(P))
    if skin is not None:   # (pushed out until the skin round it is t away, then the push spread: each vertex at least the
        # mean of its neighbours', three times, so the shell has no dents)
        # (per position, not per vertex: the skin's vertices split where its paint is, and pushed apart they left cracks)
        ng = grp.max() + 1; first = np.zeros(ng, np.int64); first[grp[::-1]] = np.arange(len(P))[::-1]; eg = np.zeros(ng)
        for _ in range(6):
            need = np.zeros(ng); np.maximum.at(need, grp, np.maximum(0., t - surface_dist(P + (t + eg[grp])[:, None] * Na, *skin)))
            if need.max() < 2e-5: break
            eg = np.minimum(eg + need * 1.2, most)   # (at most so much more: where a fold of the skin rises over it, pushing on chased it)
        E0 = np.unique(np.sort(grp[np.concatenate([I[:, [0, 1]], I[:, [1, 2]], I[:, [2, 0]]])], 1), axis=0); E0 = E0[E0[:, 0] != E0[:, 1]]
        E0 = np.concatenate([E0, E0[:, ::-1]])
        for _ in range(3):
            acc = np.zeros(ng); cnt = np.zeros(ng); np.add.at(acc, E0[:, 0], eg[E0[:, 1]]); np.add.at(cnt, E0[:, 0], 1)
            eg = np.maximum(eg, acc / np.maximum(cnt, 1))
        extra = eg[grp]
    S = P + (t + extra)[:, None] * Na
    # (the edge: the cut's edges, both ends on D = 0, used by one triangle)
    E = np.concatenate([I[:, [0, 1]], I[:, [1, 2]], I[:, [2, 0]]]); ks = np.sort(grp[E], 1)
    _, inv, cnt = np.unique(ks, axis=0, return_inverse=True, return_counts=True)
    edge = E[(cnt[inv.ravel()] == 1) & (np.abs(D[E]).max(1) < 1e-9)]
    ev = np.unique(edge); low = {v: len(P) + k for k, v in enumerate(ev)}
    Pw = P[ev] + (t + extra[ev] - wall)[:, None] * Na[ev]
    quads = [(a, b, low[b]) for a, b in edge] + [(a, low[b], low[a]) for a, b in edge]
    P_ = np.concatenate([S, Pw]); N_ = np.concatenate([Na, Na[ev]]); D_ = np.concatenate([D, D[ev]])
    I_ = np.concatenate([I, np.array(quads, np.int64).reshape(-1, 3)]); ink = np.r_[np.zeros(len(P)), np.ones(len(ev))]
    return P_, N_, D_, I_, ink, np.r_[np.arange(len(P)), ev]


def glove_edge(P, H, K, palm, T2, T3, r_thumb, back=.012, palm_m=.004, thumb=.004, soft=.006):
    """The half glove's edge drawn as the sheet draws it (19/11/2026, Denis: "la mano è troppo storta ancora"): the edge the
    texture painted, folded over the knuckles in the fist, came out in teeth. Per point of a hand P (n, 3), in its rest pose,
    the signed distance (m; the glove under 0, the skin over it) to:
    - a line across the hand before its knuckles: along the hand's axis (the wrist H to the knuckles' mean, K (4, 3): the
      index, middle, ring and little fingers' first joints, in that order) `back` m before the knuckles' line on its back,
      `palm_m` on its palm (`palm`: the unit vector to the palm), blended over `soft` m across the hand's middle;
    - and the thumb free from `thumb` m before its second joint T2 (toward T3), within r_thumb m of its axis."""
    a = K.mean(0) - H; a /= np.linalg.norm(a)
    b = (K[0] - K[3]) - ((K[0] - K[3]) @ a) * a; b /= np.linalg.norm(b)
    pm = palm - (palm @ a) * a - (palm @ b) * b; pm /= np.linalg.norm(pm)
    R = P - H; t, s, h = R @ a, R @ b, R @ pm
    tk, sk = (K - H) @ a, (K - H) @ b; o = np.argsort(sk)
    w = np.clip((h / soft + 1) / 2, 0, 1); w = w * w * (3 - 2 * w)   # (0 on the back, 1 on the palm)
    d_hand = t - (np.interp(s, sk[o], tk[o]) - (back + (palm_m - back) * w))
    ax = (T3 - T2) / np.linalg.norm(T3 - T2); u = (P - T2) @ ax
    rad = np.linalg.norm((P - T2) - np.outer(u, ax), axis=1)
    return np.maximum(d_hand, np.minimum(u + thumb, r_thumb - rad))


def near_index(P_shell, P_hands):
    """for each point (the shell's surface before its push) the nearest vertex of the hands"""
    from scipy.spatial import cKDTree
    return cKDTree(P_hands).query(P_shell)[1]


def ring_frame(P, c, ax, ref, n_th):
    """P in a ring's frame: along its axis from its middle, the radius, the angle's bin (n_th round)"""
    d = P - c; t = d @ ax; rad = d - np.outer(t, ax); side = np.cross(ax, ref)
    th = np.arctan2(rad @ side, rad @ ref)
    return t, np.linalg.norm(rad, axis=1), np.round(th / (2 * np.pi) * n_th).astype(int) % n_th


def cuff_band(X, pur, sel, E, H, step=.005):
    """The bracer's purple cuff band by the wrist: along the forearm (E elbow, H wrist) the 5 mm slices of sel's vertices
    over half purple, the run of them nearest the wrist. Returns its middle, the axis (toward the hand) and its height."""
    ax = (H - E) / np.linalg.norm(H - E); L = np.linalg.norm(H - E); t = (X - E) @ ax
    r = np.linalg.norm((X - E) - np.outer(t, ax), axis=1); s = sel & (r < .09)
    ts = np.arange(L - .10, L + .03, step)
    fr = np.array([pur[s & (t >= a) & (t < a + step)].mean() if (s & (t >= a) & (t < a + step)).sum() > 5 else 0. for a in ts])
    on = fr > .5
    if not on.any(): raise ValueError('no cuff band by the wrist')
    k1 = np.nonzero(on)[0].max(); k0 = k1
    while k0 > 0 and on[k0 - 1]: k0 -= 1
    t0, t1 = ts[k0], ts[k1] + step
    return E + ax * (t0 + t1) / 2, ax, t1 - t0


def ring_radius(Pn, c, ax, ref, h, clear=.003, n_th=48, pad=.004):
    """per angle bin the ring's radius: the points (Pn) within its height (and pad more) at their 95th percentile, empty
    bins filled round the circle, smoothed over 7 bins, at most 1.2 times the median, plus clear"""
    t, r, k = ring_frame(Pn, c, ax, ref, n_th); m = np.abs(t) <= h / 2 + pad
    rb = np.array([np.percentile(r[m & (k == b)], 95) if (m & (k == b)).sum() >= 3 else np.nan for b in range(n_th)])
    ok = ~np.isnan(rb); idx = np.arange(n_th)
    rb = np.interp(idx, np.r_[idx[ok] - n_th, idx[ok], idx[ok] + n_th], np.tile(rb[ok], 3))
    rb = np.convolve(np.r_[rb[-3:], rb, rb[:3]], np.ones(7) / 7, 'valid')
    return np.minimum(rb, 1.2 * np.median(rb)) + clear


def ring(c, ax, ref, r_th, h, bulge=.002, lip=.004, n_h=7):
    """The ring round the wrist: an outer wall of n_h rows (radius r_th per angle, bulged by bulge at mid height) and at both
    ends a lip going in by lip (under the cuff's and the glove's surfaces: no gap shows). Returns P, N, I, D (the distance to
    the nearest rim along the axis, negative; 0 on the lips: their ink) and s (0 at the elbow's end, 1 at the hand's)."""
    n_th = len(r_th); th = np.arange(n_th) / n_th * 2 * np.pi; side = np.cross(ax, ref)
    U = np.cos(th)[:, None] * ref + np.sin(th)[:, None] * side   # (the radial directions)
    rows = []   # (radius per angle, t, normal kind)
    rows.append((r_th - lip, -h / 2, -1)); rows.append((r_th, -h / 2, -1))
    for k in range(n_h):
        a = k / (n_h - 1); rows.append((r_th + bulge * np.sin(np.pi * a), -h / 2 + a * h, 0))
    rows.append((r_th, h / 2, 1)); rows.append((r_th - lip, h / 2, 1))
    P, N, Dv, S = [], [], [], []
    for rr, t, kind in rows:
        P.append(c + t * ax + rr[:, None] * U); N.append(U if kind == 0 else np.tile(kind * ax, (n_th, 1)))
        Dv.append(np.full(n_th, 0. if kind else -min(t + h / 2, h / 2 - t))); S.append(np.full(n_th, (t + h / 2) / h))
    tris = []
    for a, b in ((0, 1), *((2 + k, 3 + k) for k in range(n_h - 1)), (n_h + 2, n_h + 3)):   # (the strips: bottom lip, wall, top lip)
        for j in range(n_th):
            j2 = (j + 1) % n_th; p, q, r_, s_ = a * n_th + j, a * n_th + j2, b * n_th + j2, b * n_th + j
            tris += [(p, q, r_), (p, r_, s_)]
    return np.concatenate(P), np.concatenate(N), np.array(tris, np.int64), np.concatenate(Dv), np.concatenate(S)


def flare(P, c, ax, ref, r_in, h, span=.025):
    """the glove's points by the ring on the hand's side brought out to its inside (r_in per angle, less 0.5 mm): fully within
    its height, fading over span past its edge (no neck between the glove and the ring)"""
    t, r, k = ring_frame(P, c, ax, ref, len(r_in))
    w = np.clip(1 - (t - h / 2) / span, 0, 1); w = w * w * (3 - 2 * w); w[t < -h / 2] = 0
    rr = r + np.maximum(0., r_in[k] - .0005 - r) * w
    rad = (P - c) - np.outer(t, ax); u = rad / np.maximum(r, 1e-9)[:, None]
    return c + np.outer(t, ax) + u * rr[:, None]


def skirt(P, D, I, c, ax, ref, r_in, h, sel, keep=.003):
    """The glove's open end by the wrist carried into its ring: its boundary that is not its edge over the fingers (there
    D = 0), among the vertices sel, each vertex given a twin inside the ring (keep within its edge along the axis, at its
    inside less 0.5 mm) and a strip between them. Returns the twins' P and normals (radial), the strip's triangles
    (indices after len(P)) and each twin's vertex."""
    key = np.round(P / 1e-6).astype(np.int64); _, grp = np.unique(key, axis=0, return_inverse=True); grp = grp.ravel()
    E = np.concatenate([I[:, [0, 1]], I[:, [1, 2]], I[:, [2, 0]]]); ks = np.sort(grp[E], 1)
    _, inv, cnt = np.unique(ks, axis=0, return_inverse=True, return_counts=True)
    E = E[(cnt[inv.ravel()] == 1) & (np.abs(D[E]) > 1e-9).any(1) & sel[E].all(1)]
    v = np.unique(E)
    if not len(v): return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3), np.int64), v
    t, r, k = ring_frame(P[v], c, ax, ref, len(r_in)); u = ((P[v] - c) - np.outer(t, ax)) / np.maximum(r, 1e-9)[:, None]
    Pt = c + np.outer(np.minimum(t, h / 2 - keep), ax) + u * (r_in[k] - .0005)[:, None]
    tw = {int(x): len(P) + i for i, x in enumerate(v)}
    tris = [(a, b, tw[b]) for a, b in E] + [(a, tw[b], tw[a]) for a, b in E]
    return Pt, u, np.array(tris, np.int64), v


def loop_subdivide(P, I, attrs):
    """One round of Loop subdivision of the mesh (P, I): every triangle into four, the points moved by Loop's masks over
    the welded mesh (coincident vertices, split where the paint is, moved together), the open boundary kept where it is
    (its vertices still, its edges' new points halfway: the seam to the bust stays shut). attrs: per-vertex arrays (n, ...)
    interpolated halfway on each edge. Returns P, I and attrs for the new mesh."""
    P = np.asarray(P, float); n = len(P)
    key = np.round(P / 1e-6).astype(np.int64); _, grp = np.unique(key, axis=0, return_inverse=True); grp = grp.ravel(); ng = grp.max() + 1
    Pw = np.zeros((ng, 3)); np.add.at(Pw, grp, P); Pw /= np.bincount(grp, minlength=ng)[:, None]
    Iw = grp[I]; E = np.concatenate([Iw[:, [0, 1]], Iw[:, [1, 2]], Iw[:, [2, 0]]]); opp = np.concatenate([Iw[:, 2], Iw[:, 0], Iw[:, 1]])
    ks = np.sort(E, 1); uk, inv, cnt = np.unique(ks, axis=0, return_inverse=True, return_counts=True); inv = inv.ravel()
    osum = np.zeros((len(uk), 3)); np.add.at(osum, inv, Pw[opp]); bnd_e = cnt == 1
    # (the welded vertices: Loop's mask inside, still on the boundary)
    bv = np.zeros(ng, bool); bv[uk[bnd_e].ravel()] = True
    nb = np.zeros((ng, 3)); val = np.zeros(ng); np.add.at(nb, uk[:, 0], Pw[uk[:, 1]]); np.add.at(nb, uk[:, 1], Pw[uk[:, 0]])
    np.add.at(val, uk.ravel(), 1); val = np.maximum(val, 1)
    beta = (5 / 8 - (3 / 8 + np.cos(2 * np.pi / val) / 4) ** 2) / val
    Vn = np.where(bv[:, None], Pw, (1 - val * beta)[:, None] * Pw + beta[:, None] * nb)
    Em = np.where(bnd_e[:, None], (Pw[uk[:, 0]] + Pw[uk[:, 1]]) / 2, 3 / 8 * (Pw[uk[:, 0]] + Pw[uk[:, 1]]) + osum / 8)
    # (the new points per original vertex pair: the paint's split vertices keep their own attributes)
    Ei = np.concatenate([I[:, [0, 1]], I[:, [1, 2]], I[:, [2, 0]]]); eki = np.sort(Ei, 1)
    ui, inv_i = np.unique(eki, axis=0, return_inverse=True); inv_i = inv_i.ravel()
    wkey = np.sort(grp[ui], 1)
    lookup = {tuple(k): j for j, k in enumerate(uk)}; ew = np.array([lookup[tuple(k)] for k in wkey])
    P2 = np.r_[Vn[grp], Em[ew]]
    out = {k: np.r_[np.asarray(a), (np.asarray(a)[ui[:, 0]] + np.asarray(a)[ui[:, 1]]) / 2] for k, a in attrs.items()}
    m = n + inv_i.reshape(3, -1).T   # (the triangle's three edge points: ab, bc, ca)
    a, b, c = I[:, 0], I[:, 1], I[:, 2]; ab, bc, ca = m[:, 0], m[:, 1], m[:, 2]
    I2 = np.concatenate([np.c_[a, ab, ca], np.c_[ab, b, bc], np.c_[ca, bc, c], np.c_[ab, bc, ca]])
    return P2, I2, out


def vertex_normals(P, I):
    """smooth normals: the faces' (area-weighted) over coincident vertices"""
    key = np.round(P / 1e-6).astype(np.int64); _, grp = np.unique(key, axis=0, return_inverse=True); grp = grp.ravel()
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]]); N = np.zeros((grp.max() + 1, 3))
    np.add.at(N, grp[I].ravel(), np.repeat(fn, 3, axis=0)); N = N[grp]
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
