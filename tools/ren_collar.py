#!/usr/bin/env python3
"""The new head's collar joined to the body's vest (8/11/2026, Denis: "il suo vestito da dietro il collo si stacca"):
called by tools/ren_head.py on the head it builds.

The bust Meshy made from the head's sheet is cut above the shoulders: its collar's bottom edge stands off the body's
vest (9 mm on average), and the body's triangles under the new head are hidden (ren_head.py, hide): from above and
behind, between the two, one saw into the body (a black hole under the collar's back), and the collar's jagged bottom
band, in the head's own teal, sat on the vest in another. Here:
  - a skirt: from each point of the head's bottom edge (the boundary of the head mesh under SKIRT_Y m) to the nearest
    point of the body's kept surface, SKIRT_IN m under it (where the vest is there, it hides the skirt; where there is a
    gap, the skirt fills it), in one flat colour (SKIRT_RGB: the vest's back as the body's toon light shows it, the head's
    light being flat) from a block of the texture outside every piece; skinned at the top as the edge, at the bottom as
    the body's nearest vertex; its outline pushed back (SKIRT_LINE);
  - the head's texels within BAND_D of the vest (under SKIRT_Y + .01 m) take the body's own paint at the nearest point
    (the drawing's, OUT_DIR/<name>_painted.jpg): the collar's bottom band is the vest's colour, its jagged edge gone.
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

SKIRT_Y, SKIRT_IN, SKIRT_MAX, SKIRT_LINE = 1.50, .0015, .04, .1
SKIRT_RGB = (56, 90, 92)
BAND_D = .010
NECK_AXIS = (.006, -.01)   # (x, z) of the neck's axis: the skirt faces away from it
SAMPLE = .0015             # the body's surface sampled every that many m (the nearest points)


def _texels(uv, A, TS):
    """A triangle's texels (n x 2: col, row) and their 3D points (uv: its corners in texels; A: its corners)."""
    lo = np.floor(uv.min(0)).astype(int); hi = np.ceil(uv.max(0)).astype(int)
    xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1)); px = np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)
    T = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T
    if abs(np.linalg.det(T)) < 1e-9: return np.zeros((0, 2), int), np.zeros((0, 3))
    b = np.linalg.solve(T, (px - uv[0]).T).T; w = np.c_[1 - b.sum(1), b]; ins = (w >= -1e-3).all(1)
    q = np.floor(px[ins]).astype(int); g = (q >= 0).all(1) & (q < TS).all(1)
    return q[g], (w[ins] @ A)[g]


def collar_join(Q, N, UV, I, J, W, lb, tex, PB, IB, UVB, JB, WB, keep, paint):
    """See above. Q, N, UV, I, J, W, lb: the head (vertices, normals, uvs, triangles, skin joints and weights, outline
    push); tex: its texture (h x w x 3 float, painted in place: the band); PB, IB, UVB, JB, WB: the body's package
    (positions, triangles, uvs, skin); keep: the body's triangles kept (not hidden); paint: the body's paint (h x w x 3) or
    None. Returns (Q, N, UV, I, J, W, lb with the skirt added, the flat block: (row, col, half size) to paint SKIRT_RGB in
    the texture once it is padded)."""
    TS = tex.shape[0]; IK = IB[keep]; Cb = PB[IK].mean(1)
    near = IK[(Cb[:, 1] > SKIRT_Y - .14) & (Cb[:, 1] < SKIRT_Y + .06)]
    pts, tri, bar = [], [], []
    for k, t in enumerate(near):   # (the body's surface near the neck, sampled: points, their triangle, barycentrics)
        A = PB[t]; e = max(np.linalg.norm(A[1] - A[0]), np.linalg.norm(A[2] - A[0]), np.linalg.norm(A[2] - A[1])); n = max(2, int(e / SAMPLE))
        a, b = np.meshgrid(np.arange(n + 1), np.arange(n + 1)); m = a + b <= n; a, b = a[m], b[m]
        w = np.stack([a, b, n - a - b], 1) / n; pts.append(w @ A); tri.append(np.full(len(w), k)); bar.append(w)
    pts, tri, bar = np.concatenate(pts), np.concatenate(tri), np.concatenate(bar); tree = cKDTree(pts)
    fn = np.cross(PB[near[:, 1]] - PB[near[:, 0]], PB[near[:, 2]] - PB[near[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    ax = np.array([NECK_AXIS[0], 0, NECK_AXIS[1]]); ctr = PB[near].mean(1)
    s = np.sign(((ctr - ax)[:, [0, 2]] * fn[:, [0, 2]]).sum(1)); fn *= np.where(s == 0, 1, s)[:, None]   # (outward)
    # the head's bottom edge: the boundary of the welded mesh under SKIRT_Y
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    T = weld[I]; E = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
    Eu, cnt = np.unique(E, axis=0, return_counts=True); bnd = Eu[cnt == 1]; Wp = Q[first]
    bnd = bnd[(Wp[bnd[:, 0], 1] < SKIRT_Y) & (Wp[bnd[:, 1], 1] < SKIRT_Y)]
    bv = np.unique(bnd); d, j = tree.query(Wp[bv]); ok = d < SKIRT_MAX; vmap = {int(v): k for k, v in enumerate(bv)}
    bt = near[tri[j]]; nearest_v = bt[np.arange(len(bt)), np.argmax(bar[j], 1)]
    # the flat block: the middle of the texture's biggest square outside every piece
    mask = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(mask)
    for tr in UV[I] * TS: dr.polygon([tuple(v) for v in tr], fill=255)
    free = ~ndimage.binary_dilation(np.asarray(mask) > 0, iterations=6)
    dt = ndimage.distance_transform_cdt(free, metric='chessboard'); r0, c0 = np.unravel_index(np.argmax(dt), dt.shape); blk = int(min(dt[r0, c0] - 2, 24))
    uv_flat = np.array([(c0 + .5) / TS, (r0 + .5) / TS])
    n0, nb, rep = len(Q), len(bv), first[bv]
    Q2 = np.r_[Q, Q[rep], pts[j] - fn[tri[j]] * SKIRT_IN]; N2 = np.r_[N, N[rep], fn[tri[j]]]; UV2 = np.r_[UV, np.tile(uv_flat, (2 * nb, 1))]
    J2 = np.r_[J, J[rep], JB[nearest_v]]; W2 = np.r_[W, W[rep], WB[nearest_v]]; lb2 = np.r_[lb, np.full(2 * nb, SKIRT_LINE)]
    tris = []
    for a, b in bnd:
        if not (ok[vmap[a]] and ok[vmap[b]]): continue
        A_, B_, A2, B2 = n0 + vmap[a], n0 + vmap[b], n0 + nb + vmap[a], n0 + nb + vmap[b]
        nrm = np.cross(Q2[B_] - Q2[A_], Q2[A2] - Q2[A_]); c = (Q2[A_] + Q2[B_]) / 2
        if (nrm[[0, 2]] * (c - ax)[[0, 2]]).sum() < 0: A_, B_, A2, B2 = B_, A_, B2, A2   # (facing away from the neck's axis)
        tris += [(A_, B_, B2), (A_, B2, A2)]
    I2 = np.r_[I, np.array(tris, np.int64).reshape(-1, 3)]
    # the band: the head's texels on the vest take the vest's paint
    n_tx = 0
    if paint is not None:
        PS = paint.shape[0]; C = Q[I].mean(1); cand = np.nonzero(C[:, 1] < SKIRT_Y + .01)[0]
        dc, _ = tree.query(C[cand]); cand = cand[dc < 2 * BAND_D]
        for k in cand:
            q, p3 = _texels(UV[I[k]] * TS, Q[I[k]], TS)
            if not len(q): continue
            dd, jj = tree.query(p3); m = dd < BAND_D
            if not m.any(): continue
            t3 = near[tri[jj[m]]]; uvb = (UVB[t3] * bar[jj[m]][:, :, None]).sum(1)
            tex[q[m, 1], q[m, 0]] = paint[np.clip((uvb[:, 1] * PS).astype(int), 0, PS - 1), np.clip((uvb[:, 0] * PS).astype(int), 0, PS - 1)]; n_tx += int(m.sum())
    print('collar: a skirt of %d triangles from the head\'s bottom edge (%d points, %.0f mm from the vest on average) to the '
          'vest; %d texels of the collar\'s band on the vest in its paint' % (len(tris), nb, 1000 * d[ok].mean() if ok.any() else 0, n_tx))
    return Q2, N2, UV2, I2, J2, W2, lb2, (r0, c0, blk)


def load_body(pkg):
    """The body's package (tools/meshy_pack.py): positions, triangles, uvs, skin joints and weights."""
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    return (f(me['pos']).reshape(-1, 3).astype(np.float64), f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64),
            f(me['uv']).reshape(-1, 2).astype(np.float64), f(me['jnt'], np.uint8).reshape(-1, 4), f(me['wgt']).reshape(-1, 4))
