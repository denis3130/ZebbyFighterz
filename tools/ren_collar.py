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
    (the drawing's, OUT_DIR/<name>_painted.jpg): the collar's bottom band is the vest's colour, its jagged edge gone;
  - collar_shell (9/11/2026, Denis: "tutto il colletto bro"): the bust's collar (lumpy, painted in facets, its bottom cut
    in spikes) and the body's old collar's walls beside it (two collars one through the other) replaced by a clean one
    made here around the neck, in the sheets' flat colours (SHELL_*, PAINT_*, OLD_*).
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
# the new collar's flat colours, as the sheets draw it (ren_retro.png, ren_busto_3viste.png, ren_testa_3viste.png): the
# vest's teal outside (PAINT_TEAL), in shade inside (PAINT_INSIDE), a cream trim (paint_meshy.LINING_RGB) on its top and fronts
PAINT_TEAL, PAINT_INSIDE = np.array([44., 91, 98]), np.array([30., 64, 70])
# the new collar (9/11/2026, "tutto il colletto bro": the bust's collar, lumpy and cut in spikes at its bottom, and the body's
# old collar's walls beside it, two collars one through the other): a clean one made here around the neck's axis (NECK_AXIS),
# as the sheets draw it, open in front between +-SHELL_PHI degrees from the front; SHELL_COLS columns around it; its top
# the bust's collar's (a high percentile of its heights within SHELL_WIN degrees), its outer side the bust's collar's
# outermost (a high percentile of its radii within SHELL_WIN degrees and SHELL_DY m, from SHELL_DATA_Y m up, the
# spikes under it left out) pushed SHELL_OUT m out, both smoothed (SHELL_SMOOTH: columns, rows); SHELL_THICK m thick; from
# SHELL_BASE m (in the body) up; in flat colours: teal outside, its shade inside, cream on the top (SHELL_TRIM: the band
# outside and inside, m) and on the front edges
SHELL_PHI, SHELL_COLS, SHELL_ROWS, SHELL_WIN, SHELL_DY, SHELL_DATA_Y = 41., 92, 10, 7., .005, 1.445
SHELL_SMOOTH, SHELL_OUT, SHELL_THICK, SHELL_BASE, SHELL_TRIM = (3., 2.), .002, .005, 1.418, (.003, .006)
# its base flared out over the shoulders (SHELL_FLARE: under that height, m, that much m out per m down), and the body's old
# collar walls in it or near it hidden (ren_head.py: the body's triangles not skin from OLD_WALL[0] m up, within the
# collar's wall widened OLD_WALL[1] m outside and [2] m inside: in the moves, skinned to the shoulders, they came through it)
SHELL_FLARE, OLD_WALL = (1.465, .8), (1.455, .02, .03)
SHELL_FLARE_W, SHELL_NSMOOTH = .006, 6   # (the flare's knee rounded over that much m; the normals smoothed that many rounds)
# the floor inside it, from its inner side in to the neck (the bust's neck skin there, SHELL_NECK_IN m in), at SHELL_FLOOR m: the
# bust's neck under it left out (ren_head.py), its edge was jagged
SHELL_FLOOR, SHELL_NECK_IN = 1.452, .003
SHELL_SKIN = (.015, .045)   # its skin: the bust's collar's around each point (a gaussian of [0] m, those within [1] m)
# (9/11/2026, Denis's close-up of the chest: "migliora tutto": green shards at the base of the neck, through the collar's
# front opening): the skirt in the neck's skin within SKIRT_SKIN degrees of the front (it showed teal at the neck's sides),
# the floor in skin within FLOOR_SKIN degrees (the trapezius between the neck and the collar), the head's neck texels
# that kept the bust's teal in skin (ren_head.py), and the body's old pieces poking up through the floor hidden (OLD_IN: from
# that much m under the floor, that much m into the collar's inner side)
SKIRT_SKIN, FLOOR_SKIN, OLD_IN = 100., 75., (.012, .004)
NECK_KEEP_R = .058   # (ren_head.py: the bust's triangles within that of the neck's axis, above the floor, are the neck's: kept)
# (ren_head.py) the neck's skin shifted to the body's lit chest's from SKIN_TO_CHEST[0] m above the floor down to it (the
# head's flat skin is darker: a straight seam where the neck, the floor and the skirt met the chest), the chest's skin taken
# from the body's paint in front, from SKIN_TO_CHEST[1] m up to the floor; the skirt and the floor in front in it
SKIN_TO_CHEST = (.035, 1.40)
OLD_TOP = (1.465, .22)   # (and all of the body's not skin above that height, m, within that of the neck's axis: the old collar's tips)
# (9/11/2026, Denis from behind: "il vestito da dietro sotto al colletto è staccato, riattaccalo e fallo meno grosso da
# dietro") the collar's back stood 4-5 cm off the neck (the bust's, pushed back 3 cm by ren_head.COLLAR_FLARE against the
# hump): pulled in SHELL_BACK[0] m at its top, within SHELL_BACK[1] degrees of the back (cos^2), from none at its base up
# to all at [2] of its height; its top there lowered [3] m. Its outside lit as the body (ren_head.py: the toon light where
# the body's is, by its normal; flat in front): in its flat light it was another teal than the vest's, the vest's jagged
# top edge drawn over it
SHELL_BACK = (.026, 85., .5, .008)
# (9/11/2026, Denis on a side view in guard: the collar's lower part, in the body, came out over the vest: with the arms up
# the vest's shoulders and chest move in, the collar's base, skinned as the bust's collar, stayed out; its jagged edge
# showed on the vest, its outline across the lapels) its points skinned as the vest's nearest (a gaussian of SHELL_BODY[2]
# m over the 16 nearest of the vest's kept points) under SHELL_BODY[0] m, as the bust's collar above [1] m, between them
# blended (smoothstep)
SHELL_BODY = (1.452, 1.49, .012)
# (and the gap between it and the vest's cut rim, 2 to 4 cm wide at the back since the collar is narrower there: from the
# side, a black notch where it met the vest) its wall flares out to the rim: SHELL_RIM: the rim's points within [0] degrees
# of each column, above [1] m, [2] to [3] m from the neck's axis; past it by [4] m up to its height, back to its own over
# [6] m above it; not within [5] degrees of its front edges
SHELL_RIM = (6., 1.43, .06, .2, .003, 12., .015)
SHELL_LINE = (1.462, 1.478)
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


def collar_join(Q, N, UV, I, J, W, lb, tex, PB, IB, UVB, JB, WB, keep, paint, skin_rgb=None):
    """See above. Q, N, UV, I, J, W, lb: the head (vertices, normals, uvs, triangles, skin joints and weights, outline
    push); tex: its texture (h x w x 3 float, painted in place: the band); PB, IB, UVB, JB, WB: the body's package
    (positions, triangles, uvs, skin); keep: the body's triangles kept (not hidden); paint: the body's paint (h x w x 3) or
    None; skin_rgb: the neck's skin (the skirt's colour in front). Returns (Q, N, UV, I, J, W, lb with the skirt added, the
    flat blocks: [(row, col, half size, rgb)] to paint in the texture once it is padded)."""
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
    (rs, cs, bs), = free_blocks(UV, I, TS, 1, half=12, taken=((int(r0), int(c0), blk),))   # (and one for the skin: the skirt in front)
    uv_skin = np.array([(cs + .5) / TS, (rs + .5) / TS])
    n0, nb, rep = len(Q), len(bv), first[bv]
    # (in the front's opening, between the new collar's sides, the skirt joins the neck's skin to the chest's: in the skin's
    # own colour, its edge's; elsewhere, in the collar, the flat colour)
    phb = np.degrees(np.arctan2(Q[rep, 0] - NECK_AXIS[0], Q[rep, 2] - NECK_AXIS[1])); front = np.abs(phb) < SKIRT_SKIN
    uvs = np.where(front[:, None], uv_skin[None, :], uv_flat[None, :])   # (the neck's edge's own uvs fell on the bust's teal there)
    Q2 = np.r_[Q, Q[rep], pts[j] - fn[tri[j]] * SKIRT_IN]; N2 = np.r_[N, N[rep], fn[tri[j]]]; UV2 = np.r_[UV, uvs, uvs]
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
        PS = paint.shape[0]; C = Q[I].mean(1)
        # (not on the neck itself, within NECK_KEEP_R of its axis: it took the old body's blurry neck marks there, 9/11)
        cand = np.nonzero((C[:, 1] < SKIRT_Y + .01) & (np.hypot(C[:, 0] - NECK_AXIS[0], C[:, 2] - NECK_AXIS[1]) > NECK_KEEP_R))[0]
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
    return Q2, N2, UV2, I2, J2, W2, lb2, [(int(r0), int(c0), blk, np.array(SKIRT_RGB, float)), (rs, cs, bs, np.array(skin_rgb if skin_rgb is not None else SKIRT_RGB, float))]


def free_blocks(UV, I, TS, n, half=16, taken=()):
    """n squares of the texture outside every piece (and outside taken: (row, col, half) squares), as far from the pieces
    as can be, at most half px from their centre to their side: [(row, col, half), ...]."""
    mask = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(mask)
    for tr in UV[I] * TS: dr.polygon([tuple(v) for v in tr], fill=255)
    used = np.asarray(mask) > 0
    for r0, c0, b in taken: used[max(r0 - b, 0):r0 + b + 1, max(c0 - b, 0):c0 + b + 1] = True
    out = []
    for _ in range(n):
        free = ~ndimage.binary_dilation(used, iterations=6)
        dt = ndimage.distance_transform_cdt(free, metric='chessboard'); r0, c0 = np.unravel_index(np.argmax(dt), dt.shape); b = int(min(dt[r0, c0] - 2, half))
        out.append((int(r0), int(c0), b)); used[max(r0 - b - 8, 0):r0 + b + 9, max(c0 - b - 8, 0):c0 + b + 9] = True
    return out


def collar_shell(Q, rest, top, tw, UV, I, TS, taken, neck=None, skin_rgb=None, teal_rgb=None, body=None):
    """A new collar (see SHELL_*), its shape from the bust's (rest: its collar's vertices): (positions, normals, uvs,
    skin joints, skin weights, triangles (from 0), the flat blocks [(row, col, half, rgb)] to paint, within(points,
    out_m, in_m): which points lie in its wall widened by those margins, the outline's push per vertex, the flat colour's
    kind per vertex: 0 teal, 1 inside, 2 cream, 3 skin). teal_rgb: the vest's paint (its teal outside, its shade inside)."""
    from paint_meshy import LINING_RGB
    ax = np.array([NECK_AXIS[0], NECK_AXIS[1]])
    phi = np.degrees(np.arctan2(Q[:, 0] - ax[0], Q[:, 2] - ax[1])) % 360; rad = np.hypot(Q[:, 0] - ax[0], Q[:, 2] - ax[1]); y = Q[:, 1]
    up = rest & (y > SHELL_DATA_Y)
    cols = np.linspace(SHELL_PHI, 360 - SHELL_PHI, SHELL_COLS); dphi = lambda a, b: (a - b + 180) % 360 - 180
    # the top line: per column a high percentile of the collar's heights around it, smoothed
    ytop = np.array([np.percentile(y[up & (np.abs(dphi(phi, c)) < SHELL_WIN)], 95) if (up & (np.abs(dphi(phi, c)) < SHELL_WIN)).sum() > 3 else np.nan for c in cols])
    ok = np.isfinite(ytop); ytop = np.interp(cols, cols[ok], ytop[ok]); ytop = ndimage.gaussian_filter1d(ytop, SHELL_SMOOTH[0], mode='nearest')
    # the outer radius: per column and height a high percentile of the collar's radii around it (its outer side), smoothed
    rows = np.linspace(0, 1, SHELL_ROWS); R = np.full((SHELL_COLS, SHELL_ROWS), np.nan)
    for i, c in enumerate(cols):
        near = up & (np.abs(dphi(phi, c)) < SHELL_WIN)
        for j, u in enumerate(rows):
            yy = SHELL_DATA_Y + u * (ytop[i] - SHELL_DATA_Y); m = near & (np.abs(y - yy) < SHELL_DY)
            if m.sum() > 2: R[i, j] = np.percentile(rad[m], 90)
    for i in range(SHELL_COLS):   # (missing heights: the nearest found)
        okj = np.isfinite(R[i])
        if okj.any(): R[i] = np.interp(rows, rows[okj], R[i, okj])
    for j in range(SHELL_ROWS):   # (missing columns: between their neighbours)
        oki = np.isfinite(R[:, j])
        if oki.any(): R[:, j] = np.interp(cols, cols[oki], R[oki, j])
    R = ndimage.gaussian_filter(R, SHELL_SMOOTH, mode='nearest') + SHELL_OUT
    # (9/11/2026, Denis from behind: "riattaccalo e fallo meno grosso da dietro") its back pulled in toward the neck
    # (SHELL_BACK: that much m at the top, within that many degrees of the back, none at its base: the base meets the vest)
    wb = np.cos(np.radians(90) * np.clip(np.abs(dphi(cols, 180)) / SHELL_BACK[1], 0, 1)) ** 2
    R = R - SHELL_BACK[0] * wb[:, None] * (lambda t: t * t * (3 - 2 * t))(np.clip(rows / SHELL_BACK[2], 0, 1))[None, :]
    ytop = ytop - SHELL_BACK[3] * wb
    teal = np.array(teal_rgb, float) if teal_rgb is not None else PAINT_TEAL
    blocks = free_blocks(UV, I, TS, 4, taken=taken); rgb = [teal, teal * PAINT_INSIDE / PAINT_TEAL, LINING_RGB, np.array(skin_rgb if skin_rgb is not None else PAINT_INSIDE, float)]
    uvb = [np.array([(c0 + .5) / TS, (r0 + .5) / TS]) for r0, c0, _ in blocks]
    P_, UV_, T_ = [], [], []
    LB_, K_ = [], []
    def grid(pts, kind, push=0.):   # pts: (nc, nr, 3) a quad grid; kind: its flat colour (0 teal, 1 inside, 2 cream, 3 skin); push: its outline's
        nc, nr = pts.shape[:2]; base = sum(len(p) for p in P_); P_.append(pts.reshape(-1, 3)); UV_.append(np.tile(uvb[kind], (nc * nr, 1))); LB_.append(np.full(nc * nr, push)); K_.append(np.full(nc * nr, kind))
        for a in range(nc - 1):
            for b in range(nr - 1):
                v00, v01, v10, v11 = base + a * nr + b, base + a * nr + b + 1, base + (a + 1) * nr + b, base + (a + 1) * nr + b + 1
                T_.extend([(v00, v10, v11), (v00, v11, v01)])
    th = np.radians(cols); dirs = np.stack([np.sin(th), np.cos(th)], 1)
    def ring(r, yv):   # (nc,) radii and heights -> (nc, 3) points
        return np.stack([ax[0] + dirs[:, 0] * r, yv, ax[1] + dirs[:, 1] * r], 1)
    # heights of the rows: from SHELL_BASE (in the body) up to the top; the data's radii below SHELL_DATA_Y held
    # the vest's cut rim around it (the body's kept triangles' open edges near the neck, ren_head.py's hiding): per column
    # its outermost point within SHELL_RIM[0] degrees (radius, height); the wall flares out to it (see SHELL_RIM)
    rim_r = np.full(SHELL_COLS, np.nan); rim_y = np.full(SHELL_COLS, np.nan)
    if body is not None:
        PBr, IBr = body[0], body[1]
        _, fr_, wr_ = np.unique(np.round(PBr / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); wr_ = wr_.ravel()
        Tr = wr_[IBr]; Er = np.sort(np.concatenate([Tr[:, [0, 1]], Tr[:, [1, 2]], Tr[:, [2, 0]]]), 1)
        Eu_, cnt_ = np.unique(Er, axis=0, return_counts=True); bd_ = Eu_[cnt_ == 1]; Pr = PBr[fr_]
        mr = (Pr[bd_[:, 0]] + Pr[bd_[:, 1]]) / 2; rr_ = np.hypot(mr[:, 0] - ax[0], mr[:, 2] - ax[1]); pr_ = np.degrees(np.arctan2(mr[:, 0] - ax[0], mr[:, 2] - ax[1])) % 360
        near_ = (mr[:, 1] > SHELL_RIM[1]) & (rr_ > SHELL_RIM[2]) & (rr_ < SHELL_RIM[3])
        for i, c in enumerate(cols):
            m_ = near_ & (np.abs(dphi(pr_, c)) < SHELL_RIM[0])
            if m_.any(): k_ = np.argmax(rr_[m_]); rim_r[i], rim_y[i] = rr_[m_][k_], mr[m_][k_, 1]
        # (not at its front edges: the vest's lapels there, cut far out on the chest, are not under it: SHELL_RIM[5] degrees)
        rim_r[np.abs(dphi(cols, 0)) < SHELL_PHI + SHELL_RIM[5]] = np.nan
        okr = np.isfinite(rim_r)
        if okr.any():
            rim_r = ndimage.gaussian_filter1d(np.where(okr, rim_r, np.interp(cols, cols[okr], rim_r[okr])), 1.5, mode='nearest') * np.where(okr, 1, np.nan)
            rim_y = np.where(okr, ndimage.gaussian_filter1d(np.where(okr, rim_y, np.interp(cols, cols[okr], rim_y[okr])), 1.5, mode='nearest'), np.nan)
        print('collar: the vest\'s cut rim under it at %d of its %d columns (%.0f to %.0f mm from the neck\'s axis)' % (int(okr.sum()), SHELL_COLS, 1000 * np.nanmin(rim_r) if okr.any() else 0, 1000 * np.nanmax(rim_r) if okr.any() else 0))
    def r_at(u_abs, ci=None):   # u_abs: heights (per column, or at columns ci) -> the outer radius there (flared at the base)
        ci = np.arange(SHELL_COLS) if ci is None else ci
        u = np.clip((u_abs - SHELL_DATA_Y) / np.maximum(ytop[ci] - SHELL_DATA_Y, 1e-6), 0, 1); jj = u * (SHELL_ROWS - 1); j0 = np.clip(np.floor(jj).astype(int), 0, SHELL_ROWS - 2); w = jj - j0
        r0 = R[ci, j0] * (1 - w) + R[ci, j0 + 1] * w + SHELL_FLARE[1] * SHELL_FLARE_W * np.logaddexp(0, (SHELL_FLARE[0] - u_abs) / SHELL_FLARE_W)   # (a smooth knee)
        rr0, ry0 = rim_r[ci], rim_y[ci]; okk = np.isfinite(rr0)
        if okk.any():   # (out to the rim and past it by SHELL_RIM[4] m, up to its height; above it back to its own over SHELL_RIM[6] m)
            v = np.clip((u_abs - np.where(okk, ry0, 0)) / SHELL_RIM[6], 0, 1); k = 1 - v * v * (3 - 2 * v)
            r0 = np.where(okk, r0 + np.maximum(0, np.where(okk, rr0, 0) + SHELL_RIM[4] - r0) * k, r0)
        return r0
    hs = lambda a, b, n: [a + (b - a) * k / (n - 1) for k in range(n)]
    ylo = np.full(SHELL_COLS, SHELL_BASE); yo1 = ytop - SHELL_TRIM[0]; yi1 = ytop - SHELL_TRIM[1]; yf = np.full(SHELL_COLS, SHELL_FLOOR)
    # outer: teal from the base to under the top's trim, then the trim; inner (THICK in, down to the floor): its shade, then
    # the trim; the floor: from the inner side in to the neck (its radius there: the bust's neck skin's), in the shade
    outer = np.stack([ring(r_at(yy), yy) for yy in hs(ylo, yo1, 12)], 1); outer_t = np.stack([ring(r_at(yy), yy) for yy in hs(yo1, ytop, 2)], 1)
    inner = np.stack([ring(r_at(yy) - SHELL_THICK, yy) for yy in hs(yf, yi1, 10)], 1); inner_t = np.stack([ring(r_at(yy) - SHELL_THICK, yy) for yy in hs(yi1, ytop, 2)], 1)
    # (the outer side's lower part, in and on the vest: its outline pushed back, SHELL_LINE: fully under [0] m, none from
    # [1]; it drew a black tooth into the vest where the wall came out of it, seen from the side)
    lo_push = lambda pts: SKIRT_LINE * (1 - (lambda u: u * u * (3 - 2 * u))(np.clip((pts[..., 1] - SHELL_LINE[0]) / (SHELL_LINE[1] - SHELL_LINE[0]), 0, 1))).reshape(-1)
    grid(outer, 0); LB_[-1] = lo_push(outer); grid(outer_t, 2); grid(inner[:, ::-1], 1); grid(inner_t[:, ::-1], 2)
    rim = np.stack([outer_t[:, -1], inner_t[:, -1]], 1); grid(rim, 2)   # (the top, outer to inner)
    bot = np.stack([inner[:, 0], outer[:, 0]], 1); grid(bot, 0, SKIRT_LINE)   # (the bottom: from the floor's edge down into the body)
    rneck = np.full(SHELL_COLS, np.nan)
    if neck is not None:
        nk = neck & (np.abs(y - SHELL_FLOOR) < .006)
        for i, c in enumerate(cols):
            m = nk & (np.abs(dphi(phi, c)) < SHELL_WIN)
            if m.sum() > 2: rneck[i] = np.percentile(rad[m], 30)
    okn = np.isfinite(rneck); rneck = np.interp(cols, cols[okn], rneck[okn]) if okn.any() else np.full(SHELL_COLS, .05)
    rneck = np.minimum(ndimage.gaussian_filter1d(rneck, SHELL_SMOOTH[0], mode='nearest') - SHELL_NECK_IN, r_at(yf) - SHELL_THICK - .002)
    floor = np.stack([ring(rneck, yf - .004), inner[:, 0]], 1)
    if os.environ.get('SHELL_DEBUG'): np.savez(os.environ['SHELL_DEBUG'], cols=cols, ytop=ytop, R=R, rneck=rneck)
    fr = np.abs(dphi(cols, 0)) < FLOOR_SKIN; k1 = int(np.argmin(fr)); k2 = SHELL_COLS - int(np.argmin(fr[::-1]))   # (the front columns: skin)
    if 0 < k1 < k2 < SHELL_COLS: grid(floor[:k1 + 1], 3, SKIRT_LINE); grid(floor[k1:k2], 1, SKIRT_LINE); grid(floor[k2 - 1:], 3, SKIRT_LINE)
    else: grid(floor, 1, SKIRT_LINE)   # (its outline pushed back: seen edge-on from the front it drew a black line across the chest)
    for e, flip in ((0, True), (SHELL_COLS - 1, False)):   # the front edges: outer to inner, base to top, in the trim
        col_o = np.r_[outer[e], outer_t[e, 1:]]; col_i = np.r_[inner[e], inner_t[e, 1:]]
        hy = np.linspace(0, 1, 14); yo = col_o[:, 1]; yi = col_i[:, 1]   # (both resampled on as many rows, by height)
        ys_ = SHELL_FLOOR + hy * (ytop[e] - SHELL_FLOOR); co = np.stack([np.interp(ys_, yo, col_o[:, k]) for k in range(3)], 1); ci_ = np.stack([np.interp(ys_, yi, col_i[:, k]) for k in range(3)], 1)
        g = np.stack([co, ci_], 0) if not flip else np.stack([ci_, co], 0); grid(g, 2)
        # (and under the floor, the outer side's front down to the base, teal: in the body)
        yb_ = np.linspace(SHELL_BASE, SHELL_FLOOR, 4); cb = np.stack([np.interp(yb_, yo, col_o[:, k]) for k in range(3)], 1); cbi = np.repeat(ci_[:1], 4, 0)
        g2 = np.stack([cb, cbi], 0) if not flip else np.stack([cbi, cb], 0); grid(g2, 0)
    P_ = np.concatenate(P_); UV_ = np.concatenate(UV_); T_ = np.array(T_, np.int64); LB_ = np.concatenate(LB_); K_ = np.concatenate(K_)
    # the triangles facing outward from the wall (the grids' winding: check against the centre of the wall)
    C = P_[T_].mean(1); fn = np.cross(P_[T_[:, 1]] - P_[T_[:, 0]], P_[T_[:, 2]] - P_[T_[:, 0]])
    # normals: per welded position, the area-weighted mean of its faces' (smooth, so the outline is whole)
    _, first, weld = np.unique(np.round(P_ / 1e-7).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    Nw = np.zeros((len(first), 3))
    for k in range(3): np.add.at(Nw, weld[T_[:, k]], fn)
    # (and smoothed over the welded mesh, SHELL_NSMOOTH rounds: its rows' small kinks drew the toon light's band edge as
    # dark dashes across its outside, seen from the side and the back)
    Tw = weld[T_]; nw = len(first); Ew = np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]])
    from scipy.sparse import coo_matrix
    Aw = coo_matrix((np.ones(2 * len(Ew)), (np.r_[Ew[:, 0], Ew[:, 1]], np.r_[Ew[:, 1], Ew[:, 0]])), shape=(nw, nw)).tocsr()
    Nn = Nw / np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12); deg_ = np.maximum(np.asarray(Aw.sum(1)).ravel(), 1)
    for _ in range(SHELL_NSMOOTH):
        Nn = .5 * Nn + .5 * (Aw @ Nn) / deg_[:, None]; Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)
    N_ = Nn[weld]
    # skin: the bust's collar's around each point (a gaussian of SHELL_SKIN[0] m over those within [1] m), the 4 most: smooth
    # (the nearest one's alone tore the collar into teeth in the moves: its neighbours on the body differ)
    src = np.nonzero(rest)[0]; nbn = int(top.max()) + 1; tree = cKDTree(Q[src])
    d, jj = tree.query(P_, k=64, distance_upper_bound=SHELL_SKIN[1]); ok = np.isfinite(d); jj = np.where(ok, jj, 0)
    wg = np.exp(-.5 * (np.where(ok, d, 0) / SHELL_SKIN[0]) ** 2) * ok
    acc = np.zeros((len(P_), nbn))
    for k in range(top.shape[1]): np.add.at(acc, (np.repeat(np.arange(len(P_)), jj.shape[1]), top[src][jj.ravel(), k]), (wg * tw[src][jj, k]).ravel())
    lone = wg.sum(1) < 1e-9
    if lone.any():   # (none near: the nearest one's)
        _, j1 = tree.query(P_[lone]); acc[np.nonzero(lone)[0][:, None], top[src][j1]] += tw[src][j1]
    acc /= np.maximum(acc.sum(1, keepdims=True), 1e-12)
    if body is not None:   # (its lower part skinned as the vest it sits in: see SHELL_BODY)
        PB, IBk, JB, WB = body; vb = np.unique(IBk); tb = cKDTree(PB[vb])
        db, jb = tb.query(P_, k=16); gb = np.exp(-.5 * (db / SHELL_BODY[2]) ** 2) + 1e-12
        accb = np.zeros((len(P_), max(nbn, int(JB.max()) + 1)))
        for k in range(4): np.add.at(accb, (np.repeat(np.arange(len(P_)), jb.shape[1]), JB[vb][jb.ravel(), k]), (gb * WB[vb][jb, k]).ravel())
        accb /= np.maximum(accb.sum(1, keepdims=True), 1e-12)
        if accb.shape[1] > acc.shape[1]: acc = np.pad(acc, ((0, 0), (0, accb.shape[1] - acc.shape[1])))
        u = np.clip((P_[:, 1] - SHELL_BODY[0]) / (SHELL_BODY[1] - SHELL_BODY[0]), 0, 1); bw = 1 - u * u * (3 - 2 * u)
        acc = acc * (1 - bw[:, None]) + accb[:, :acc.shape[1]] * bw[:, None]
        print('collar: its lower part skinned as the vest (%d of its %d points fully, %d partly)' % (int((bw > .999).sum()), len(P_), int(((bw > .001) & (bw <= .999)).sum())))
    J_ = np.argsort(-acc, 1)[:, :4]; W_ = np.take_along_axis(acc, J_, 1); W_ /= np.maximum(W_.sum(1, keepdims=True), 1e-12)
    def within(X, out_m, in_m, floor=False):   # X: points -> True where within the collar's wall widened by out_m outside and
        # in_m inside (floor: where under its floor, inside its inner side, by the angles it spans less 5 degrees)
        ph = np.degrees(np.arctan2(X[:, 0] - ax[0], X[:, 2] - ax[1])) % 360; rr = np.hypot(X[:, 0] - ax[0], X[:, 2] - ax[1])
        ci = np.clip(np.round((ph - SHELL_PHI) / (360 - 2 * SHELL_PHI) * (SHELL_COLS - 1)).astype(int), 0, SHELL_COLS - 1)
        if floor == 'above':   # (inside its inner side, from just under its floor up, within the angles it spans)
            return (ph >= SHELL_PHI - 2) & (ph <= 360 - SHELL_PHI + 2) & (X[:, 1] > SHELL_FLOOR - out_m) & (X[:, 1] <= ytop[ci]) & (rr < r_at(X[:, 1], ci) - SHELL_THICK + in_m)
        if floor:
            return (ph >= SHELL_PHI + 5) & (ph <= 360 - SHELL_PHI - 5) & (X[:, 1] < SHELL_FLOOR - .003) & (rr < r_at(np.full(len(X), SHELL_FLOOR), ci) - SHELL_THICK)
        on = (ph >= SHELL_PHI - 5) & (ph <= 360 - SHELL_PHI + 5) & (X[:, 1] >= SHELL_BASE) & (X[:, 1] <= ytop[ci] + .01)
        ro = r_at(X[:, 1], ci); return on & (rr < ro + out_m) & (rr > ro - SHELL_THICK - in_m)
    return P_, N_, UV_, J_.astype(top.dtype), W_.astype(tw.dtype), T_, [(r0, c0, b, rgb[k]) for k, (r0, c0, b) in enumerate(blocks)], within, LB_, K_


def load_body(pkg):
    """The body's package (tools/meshy_pack.py): positions, triangles, uvs, skin joints and weights."""
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    return (f(me['pos']).reshape(-1, 3).astype(np.float64), f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64),
            f(me['uv']).reshape(-1, 2).astype(np.float64), f(me['jnt'], np.uint8).reshape(-1, 4), f(me['wgt']).reshape(-1, 4))
