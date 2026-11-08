#!/usr/bin/env python3
"""Ren's new head (8/11/2026, Denis with his 3-view sheet docs/ref/personaggi/ren_testa_3viste.png: "fallo IDENTICO da
tripla A"): Meshy's multi-image bust made from that sheet (docs/meshy/REN.md, "Testa nuova") cut above the shoulders,
placed on the body's bind pose, skinned to the body's bones, the old head, neck and collar hidden.

usage: python3 tools/ren_head.py BUST.glb PACKAGE_DIR OUT_DIR [TEXTURE.jpg]
  BUST.glb     the bust, decimated (tools/mesh_prep/decimate_glb.py), with its texture
  PACKAGE_DIR  the body's tools/meshy_pack.py package (the skin weights are taken from it)
  TEXTURE.jpg  the bust's texture painted from the sheet (tools/paint_head.py); without it, Meshy's own
  writes OUT_DIR/<name>_head.json, .bin, .jpg (name = the package's): {v, verts, tris, pos, nor, uv: float32, jnt: uint8 x4,
  wgt: float32 x4, idx: uint16/32, hide: uint32 (the package's triangles it replaces), lb: float32 (the outline's
  extra push back per vertex, m: fringe_back); each [byte offset, count]}
  and OUT_DIR/<name>_fringe.json, .bin, .png: the face's locks drawn from the sheet (tools/ren_fringe.py)

Placing (BUSTS, measured on the bust, in its own units): its eyes' line and its chin on the drawing's (ren.png rows 168
and 238 through drawing_fit: the head as big as before, the sheet's proportions), its neck's axis on the body's (both fit
as circles to the skin around the neck, BUSTS neck and BODY_NECK). Cut: the bust's triangles under BUSTS cut (the
shoulders and the chest: the body's own stay) are left out. Skin, by what each vertex is in the bust's texture: the hair
(dark, not the shirt) and all above HEAD_JAW m but the collar's teal and trim (the face, the ears, the eyes: their
whites, skinned as the collar, stayed behind when the head turned, blank eyes) on the Head bone; the neck's skin from
the neck and the spine at its base to the Head at HEAD_JAW; the collar, its trim and the shirt as the body's nearest vertex that
is not its old head (Meshy skinned the old collar half to the Head: it turned with the head), without the Head; then
smoothed over its neighbours (HEAD_SMOOTH rounds, the head's own vertices kept). Hidden: the body's triangles all above
HIDE_Y (the old head and its hair, the neck, the collar's top).
"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meshy_pack import read_glb, acc, world_mats

# Per bust (its file's name without the extension), measured on its front view, in its own units: the eyes' line and
# the chin (y), the neck (the skin between these heights fits its axis), the cut (y: under it, the shoulders, left out)
# and its colours to the sheet's (palette: Meshy's main colours, k-means of its texture, each with the sheet's)
BUSTS = {'testa_v1_15k': {'eye': .195, 'chin': -.105, 'neck': (-.24, -.16), 'cut': -.43},
         'testa_v2_face': {'eye': .208, 'chin': -.125, 'neck': (-.26, -.16), 'cut': -.45, 'sockets': [(-.13, .2), (.133, .2)], 'bangs': True, 'palette': [
             ((68, 55, 69), (75, 64, 73)), ((47, 36, 47), (52, 43, 52)), ((53, 42, 55), (60, 50, 60)), ((101, 81, 88), (113, 94, 102)),   # hair
             ((250, 195, 156), (248, 184, 137)), ((203, 152, 120), (170, 112, 82)),   # skin, its shadow
             ((42, 91, 97), (57, 97, 102)), ((38, 72, 79), (45, 78, 84)), ((27, 64, 71), (33, 55, 60)), ((52, 62, 71), (40, 44, 50)),   # collar, shirt
             ((239, 219, 204), (206, 190, 162))]}}   # trim
DRAW_EYE, DRAW_CHIN = 168., 238.           # the drawing's rows (ren.png) of the eyes' line and the chin
BODY_NECK = (1.44, 1.47)                   # the body's neck: its skin between these heights fits its axis
HIDE_Y = 1.445                             # the body's triangles above it are hidden
BODY_X = .006                              # the body's middle (x)
HIDE_RAY, HIDE_NECK_R = .08, .075   # (and all of them that are skin, or within that of the neck's axis: the old neck)
HEAD_SMOOTH, HEAD_JAW, HEAD_TOP = 3, 1.515, 1.535   # (HEAD_TOP: above it all on the Head bone; the collar ends at 1.529)
COLLAR_STIFF = (1.46, 1.50, .8)   # see main(): the collar's top on the spine, not on the shoulders
# Meshy's colours to the sheet's (its texture a little lighter and greyer: pink skin, light shadows): each texel moves by
# the offsets of the palette colours near it (HEAD_SPREAD: how near, rgb), its shades within a colour kept
HEAD_PALETTE = [((68, 55, 70), (75, 64, 73)), ((52, 41, 53), (58, 48, 58)), ((100, 81, 90), (113, 94, 102)),   # hair, its dark, its light
                ((249, 190, 151), (248, 184, 137)), ((184, 140, 113), (162, 107, 78)), ((109, 59, 44), (101, 68, 50)),   # skin, its shadow, the darkest
                ((42, 87, 93), (57, 97, 102)), ((39, 35, 44), (30, 28, 34)), ((239, 219, 204), (206, 190, 162))]   # collar teal, dark cloth, trim
HEAD_SPREAD = 28.
TEMPLE = (.05, .095, 1.556, 1.581, -.004, .058)   # the temples (|x| from the middle in, out; y; z; m): see temples()
TEMPLE_SKIN, TEMPLE_SINK, TEMPLE_STRETCH = .5, .012, .5
TEMPLE_SMOOTH, TEMPLE_GROW, TEMPLE_RINGS = True, .008, 2   # see temple_smooth() (False: temple_locks(), the locks sunk)
TEMPLE_LINE = (.045, .1, 1.555, 1.62, -.03, .075, .1, .004)   # see main(): the temples' outline pushed back
CHEEKS = (.03, 1.525, 1.595, .015, 1.583, .07)   # see cheek_marks(): |x| over, y between, z over, the eyes' band (over y, within |x|)
EARS = (.045, .1, 1.545, 1.615, -.035, .03)   # see cheek_marks(): |x|, y, z ranges (m)
TEMPLE_SPOT = (-.078, -.052, 1.570, 1.592, -.012, .016)   # (x, y, z ranges, m) a brown spot on one temple: see temple_spot()
PLUG_LINE = .1                             # the outline of the plug under the face's holes (tools/ren_eyes.py): pushed back (m)
FRINGE_PAINT = (.0008, 120., (60, 50, 60))   # see fringe_paint(): in front of the face by (m), lighter than (mean rgb), the colour they take
FRINGE_NEAR, FRINGE_MAX = .01, .05
FRINGE = (.02, .008, .004, 3, .002)   # the hair over the face: its outline's push back (m), the face's reach around it, the depth slack (m), smoothing rounds, grid (m): see fringe_back()
HEAD_TEX = 2048   # the texture's size at most (px; 4096 looked the same at the viewer's nearest zoom and took 4 times the memory)


def circle(x, z):
    """Least-squares circle through the points (x, z): (centre x, centre z, radius)."""
    A = np.stack([x, z, np.ones_like(x)], 1); c = np.linalg.lstsq(A, -(x ** 2 + z ** 2), rcond=None)[0]
    xc, zc = -c[0] / 2, -c[1] / 2
    return xc, zc, float(np.sqrt(xc ** 2 + zc ** 2 - c[2]))


def skin_of(col):
    return (col[:, 0] > 120) & (col[:, 1] > 75) & (col[:, 0] - col[:, 2] > 40)


def _texels(uv, A, TS):
    """A triangle's texels (rows, cols as an (n, 2) array of col, row) with their 3D points. uv: its corners in texels."""
    lo = np.floor(uv.min(0)).astype(int); hi = np.ceil(uv.max(0)).astype(int)
    xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1)); px = np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)
    T = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T
    if abs(np.linalg.det(T)) < 1e-9: return np.zeros((0, 2), int), np.zeros((0, 3))
    b = np.linalg.solve(T, (px - uv[0]).T).T; w = np.c_[1 - b.sum(1), b]; ins = (w >= -1e-3).all(1)
    q = np.floor(px[ins]).astype(int); g = (q >= 0).all(1) & (q < TS).all(1)
    return q[g], (w[ins] @ A)[g]


def _in_temple(p):
    x0, x1, y0, y1, z0, z1 = TEMPLE; ax = np.abs(p[:, 0] - BODY_X)
    return (ax > x0) & (ax < x1) & (p[:, 1] > y0) & (p[:, 1] < y1) & (p[:, 2] > z0) & (p[:, 2] < z1)


def _skin_px(t):
    return (t[..., 0] > 200) & (t[..., 0] - t[..., 2] > 70) & (t[..., 1] > 140)


def temple_locks(Q, UV, I, tex):
    """Meshy laid the sheet's sideburns flat on the temples (thin locks from the eyes to the ears, dark: from the side a
    bruise; the sheet has skin there): the triangles with their middle within TEMPLE whose texels are mostly not skin
    (under TEMPLE_SKIN) sink TEMPLE_SINK m toward the head's axis, under the face's skin (their corners on the face's own
    triangles stay: no dents). Moves Q in place; returns how many points."""
    TS = tex.shape[0]; sk = _skin_px(tex); C = Q[I].mean(1); A = Q[I]
    lock = np.zeros(len(I), bool); face = np.zeros(len(I), bool)
    for k in np.nonzero(_in_temple(C) | _in_temple(A[:, 0]) | _in_temple(A[:, 1]) | _in_temple(A[:, 2]))[0]:
        q, _ = _texels(UV[I[k]] * TS, A[k], TS)
        if not len(q): continue
        f = sk[q[:, 1], q[:, 0]].mean(); face[k] = f >= TEMPLE_SKIN; lock[k] = (f < TEMPLE_SKIN) and _in_temple(C[k:k + 1])[0]
    key = np.round(Q / 1e-6).astype(np.int64); _, weld = np.unique(key, axis=0, return_inverse=True); weld = weld.ravel()
    on_face = np.zeros(weld.max() + 1, bool); on_face[weld[I[face].ravel()]] = True
    mv = np.zeros(weld.max() + 1, bool); mv[weld[I[lock].ravel()]] = True; mv &= ~on_face
    v = mv[weld] & _in_temple(Q)
    d = Q[v][:, [0, 2]] - np.array([BODY_X, 0.]); d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    Q[v, 0] -= d[:, 0] * TEMPLE_SINK; Q[v, 2] -= d[:, 1] * TEMPLE_SINK
    return int(v.sum()), int(lock.sum())


def temple_smooth(Q, UV, I, tex):
    """The temples' skin made one smooth surface (8/11, Denis: "di lato il viso si deforma, deve essere omogeneo"): the
    locks Meshy laid flat on the temples (as temple_locks() finds them) and the points around them within TEMPLE_ZONE
    (TEMPLE grown by TEMPLE_GROW m; not the eyes) are placed by a bi-harmonic fill over the mesh from the points around
    them, which stay: no dents, no folds (sunk under the skin, as before, they left long folded triangles: bumps and
    notches on the face's outline from three quarters). Moves Q in place; returns (points moved, lock triangles)."""
    TS = tex.shape[0]; sk = _skin_px(tex); C = Q[I].mean(1); A = Q[I]
    lock = np.zeros(len(I), bool); face = np.zeros(len(I), bool)
    for k in np.nonzero(_in_temple(C) | _in_temple(A[:, 0]) | _in_temple(A[:, 1]) | _in_temple(A[:, 2]))[0]:
        q, _ = _texels(UV[I[k]] * TS, A[k], TS)
        if not len(q): continue
        f = sk[q[:, 1], q[:, 0]].mean(); face[k] = f >= TEMPLE_SKIN; lock[k] = (f < TEMPLE_SKIN) and _in_temple(C[k:k + 1])[0]
    key = np.round(Q / 1e-6).astype(np.int64); _, first, weld = np.unique(key, axis=0, return_index=True, return_inverse=True); weld = weld.ravel(); nw = len(first)
    T = weld[I]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    from scipy.sparse import csr_matrix, identity
    from scipy.sparse.linalg import spsolve
    Adj = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw))
    deg = np.asarray(Adj.sum(1)).ravel()
    # the free points: the locks' and, around them, those in the grown zone (not the eyes': their whites and lashes)
    W = Q[first]; g = TEMPLE_GROW; x0, x1, y0, y1, z0, z1 = TEMPLE; axw = np.abs(W[:, 0] - BODY_X)
    zone = (axw > x0 - g) & (axw < x1 + g) & (W[:, 1] > y0 - g) & (W[:, 1] < y1 + g) & (W[:, 2] > z0 - g) & (W[:, 2] < z1 + g)
    cw = tex[np.clip((UV[first, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[first, 0] * TS).astype(int), 0, TS - 1)].astype(int)
    eye = (cw.min(1) > 175) | ((cw.mean(1) < 60) & (W[:, 1] > 1.582))
    free = np.zeros(nw, bool); free[np.unique(T[lock])] = True
    for _ in range(TEMPLE_RINGS): free |= (Adj @ free.astype(float) > 0) & zone
    free &= zone & ~eye
    # bi-harmonic: L^2 x = 0 on the free points (L: the uniform graph Laplacian), the others fixed
    L = (csr_matrix((deg, (np.arange(nw), np.arange(nw))), shape=(nw, nw)) - Adj).tocsr(); M = (L @ L).tocsr()
    f = np.nonzero(free)[0]; c = np.nonzero(~free)[0]
    if not len(f): return 0, int(lock.sum())
    Mff = M[f][:, f].tocsc(); Mfc = M[f][:, c]
    Xf = np.stack([spsolve(Mff, -(Mfc @ W[c, k])) for k in range(3)], 1)
    W2 = W.copy(); W2[f] = Xf; Q[:] = W2[weld]
    return int(len(f)), int(lock.sum())


def temples(t, Q, UV, I):
    """The texels whose 3D point is within TEMPLE and that are not skin take the skin's colour (the face is flat: one
    colour, the median of its skin texels there): what is left of the sideburns' paint (see temple_locks). Returns how many."""
    TS = t.shape[0]; A = Q[I]; C = A.mean(1); x0, x1, y0, y1, z0, z1 = TEMPLE
    ac = np.abs(C[:, 0] - BODY_X); near = (ac > x0 - .012) & (ac < x1 + .012) & (C[:, 1] > y0 - .012) & (C[:, 1] < y1 + .012) & (C[:, 2] > z0 - .012) & (C[:, 2] < z1 + .012)
    box = np.zeros(t.shape[:2], bool)
    for k in np.nonzero(near)[0]:
        q, p3 = _texels(UV[I[k]] * TS, A[k], TS); q = q[_in_temple(p3)]; box[q[:, 1], q[:, 0]] = True
    sk = _skin_px(t); good = box & sk; bad = box & ~sk
    if not good.any(): return 0
    skin = np.median(t[good], 0); t[bad] = skin
    # the sunk locks' triangles stretched over the temple (under TEMPLE_STRETCH texels per mm2: their few texels' stripes
    # spread over 3-16 mm2 each, brown and white streaks by the eye's outer corner) all skin, with the texels around them
    # in the texture that no other triangle covers (the filtering reaches them)
    from PIL import ImageDraw
    from scipy import ndimage
    a3 = np.linalg.norm(np.cross(A[:, 1] - A[:, 0], A[:, 2] - A[:, 0]), axis=1) / 2 * 1e6
    uv = UV[I] * TS; auv = np.abs((uv[:, 1, 0] - uv[:, 0, 0]) * (uv[:, 2, 1] - uv[:, 0, 1]) - (uv[:, 1, 1] - uv[:, 0, 1]) * (uv[:, 2, 0] - uv[:, 0, 0])) / 2
    st = near & (auv < TEMPLE_STRETCH * a3)
    if st.any():
        ms, mo = Image.new('L', (TS, TS), 0), Image.new('L', (TS, TS), 0); ds, do = ImageDraw.Draw(ms), ImageDraw.Draw(mo)
        for k in np.nonzero(st)[0]: ds.polygon([tuple(v) for v in uv[k]], fill=255)
        for k in np.nonzero(~st)[0]: do.polygon([tuple(v) for v in uv[k]], fill=255)
        ms, mo = np.asarray(ms) > 0, np.asarray(mo) > 0
        paint = ndimage.binary_dilation(ms, iterations=2) & ~(mo & ~ms)
        t[paint] = skin
    return int(bad.sum()), int(st.sum())


def temple_spot(t, Q, UV, I):
    """A brown oval spot Meshy painted on one temple only (the -x one, at the hairline): its texels in TEMPLE_SPOT that are
    brown, light or dark (the skin's shadow and the spot's core; not the hair, the brows or the lines: purple or black) take the skin's colour. Returns how many."""
    TS = t.shape[0]; A = Q[I]; C = A.mean(1); lo = np.array(TEMPLE_SPOT[0::2]); hi = np.array(TEMPLE_SPOT[1::2])
    near = ((C > lo - .012) & (C < hi + .012)).all(1); box = np.zeros(t.shape[:2], bool)
    for k in np.nonzero(near)[0]:
        q, p3 = _texels(UV[I[k]] * TS, A[k], TS); q = q[((p3 > lo) & (p3 < hi)).all(1)]; box[q[:, 1], q[:, 0]] = True
    sk = _skin_px(t); r, g, b = t[..., 0], t[..., 1], t[..., 2]
    brown = (r > 60) & (r - b > 12) & ~sk   # (the hair's purples and the black lines have r - b under 12)
    good = box & sk; bad = box & brown
    if not good.any(): return 0
    t[bad] = np.median(t[good], 0)
    return int(bad.sum())


def fringe_back(Q, N, I, skin, dark, ax):
    """The hair over the face (the fringe, the locks at the temples) with its outline pushed FRINGE[0] m further back
    (Denis, 8/11: "i capelli sulla faccia" were still badly made: there its outline, 4 mm wide and only 6 mm back for the
    jaw's line over the neck, came out of the locks' creases and between them and the skin as black splinters around
    the eyes and brows; the sheet's locks are clean). Seen from the front, the face is its skin above the jaw facing
    forward on a FRINGE[4] m grid (its frontmost depth per cell), widened FRINGE[1] m; the hair (dark) in it, in front of
    the face or within FRINGE[2] m of it, gets the push, smoothed over FRINGE[3] rounds of neighbours. The locks' outline
    still shows against what is further back (the background, at the head's sides). The same for the hair on the face's
    sides (FRINGE_NEAR). Returns the push per vertex (m) and
    the face's depth grid (for fringe_paint)."""
    from scipy import ndimage
    fr, wide, slack, rounds, g = FRINGE
    face = skin & (Q[:, 1] > HEAD_JAW) & (N[:, 2] > .2)
    lo = Q[:, :2].min(0) - .02; ij = np.floor((Q[:, :2] - lo) / g).astype(int); shp = tuple(ij.max(0) + 2)
    zf = np.full(shp, -9.); np.maximum.at(zf, (ij[face, 0], ij[face, 1]), Q[face, 2])
    k = int(round(wide / g)); z1 = ndimage.grey_dilation(zf, size=(3, 3)); zf = ndimage.grey_dilation(zf, size=(2 * k + 1, 2 * k + 1))
    zf = np.where(z1 > -9, z1, zf)   # (the face's own depth where it is, its widened edge only around it: by the nose, the nose's height did not count)
    front = dark & (zf[ij[:, 0], ij[:, 1]] > -9) & (Q[:, 2] > zf[ij[:, 0], ij[:, 1]] - slack)
    # (and the locks on the face's sides, the sideburns over the cheeks and the temples, seen from three quarters: the
    # hair within FRINGE_NEAR m of the skin above the jaw in front of the neck's axis, outside it: its outline made black
    # splinters on the cheeks there)
    from scipy.spatial import cKDTree
    fs = np.nonzero(skin & (Q[:, 1] > HEAD_JAW) & (Q[:, 2] > ax[1]))[0]; hv = np.nonzero(dark)[0]
    d, nn = cKDTree(Q[fs]).query(Q[hv], distance_upper_bound=FRINGE_NEAR); ok = np.isfinite(d)
    side = np.zeros(len(Q), bool); hv, nn = hv[ok], fs[nn[ok]]
    side[hv[((Q[hv] - Q[nn]) * N[nn]).sum(1) > -slack]] = True
    # the push: FRINGE[0], or more for the locks standing further off the face (a lock 3 cm in front of the forehead kept
    # its outline over it), up to FRINGE_MAX m
    dz = np.where(front, Q[:, 2] - zf[ij[:, 0], ij[:, 1]], 0.)
    w = np.where(front | side, np.clip(dz + fr / 2, fr, FRINGE_MAX), 0.)
    key = np.round(Q / 1e-6).astype(np.int64); _, weld = np.unique(key, axis=0, return_inverse=True); weld = weld.ravel(); nw = weld.max() + 1
    T = weld[I]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    ww = np.zeros(nw); np.maximum.at(ww, weld, w); deg = np.bincount(E.ravel(), minlength=nw).astype(float)
    for _ in range(rounds):
        acc = np.zeros(nw); np.add.at(acc, E[:, 0], ww[E[:, 1]]); np.add.at(acc, E[:, 1], ww[E[:, 0]])
        ww = np.maximum(ww, .5 * ww + .5 * acc / np.maximum(deg, 1))
    return ww[weld], (zf, lo, g)


def fringe_paint(t, Q, UV, I, lb, grid):
    """Meshy painted what the sheet shows behind the locks over the face on the locks themselves: the eye's white and
    the skin as white and grey splinters at their tips in front of the eyes, a skin speck at the tip between them. On
    the locks (two corners or more fringe hair, lb, and their middle more than FRINGE_PAINT[0] m in front of the face) the
    texels lighter than FRINGE_PAINT[1] (mean rgb) take the hair's dark colour (FRINGE_PAINT[2]). Returns how many."""
    zf, lo, g = grid; dz, light, col = FRINGE_PAINT
    TS = t.shape[0]; A = Q[I]; C = A.mean(1)
    ij = np.clip(np.floor((C[:, :2] - lo) / g).astype(int), 0, np.array(zf.shape) - 1)
    zc = zf[ij[:, 0], ij[:, 1]]
    lock = ((lb[I] > .5 * FRINGE[0]).sum(1) >= 2) & (zc > -9) & (C[:, 2] > zc + dz)
    n = 0
    for k in np.nonzero(lock)[0]:
        q, _ = _texels(UV[I[k]] * TS, A[k], TS)
        if not len(q): continue
        v = t[q[:, 1], q[:, 0]]; m = v.mean(1) > light
        if m.any(): t[q[m, 1], q[m, 0]] = col; n += int(m.sum())
    return n


def cheek_marks(t, Q, UV, I):
    """Meshy's marks on the cheeks' sides and the ears (light grey scratches, purple and black specks and strokes: the
    sheet has clean skin there, the ears' brown shadow inside): on the skin's triangles (two corners or more) in CHEEKS
    (|x| from the middle over CHEEKS[0], y between CHEEKS[1] and [2], z over [3], m; not the eyes: under the eyes' band
    or outside it) and in EARS (|x|, y, z ranges: behind the eyes), those texels take the colour of the nearest unmarked
    skin texel. Returns how many."""
    from scipy import ndimage
    TS = t.shape[0]; A = Q[I]; C = A.mean(1); ax0, y0, y1, z0, eye_y, eye_x = CHEEKS
    c = np.clip(t[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)], 0, 255)
    sk3 = _skin_px(c[None])[0][I].sum(1) >= 2
    ac = np.abs(C[:, 0] - BODY_X)
    sel = sk3 & (ac > ax0) & (C[:, 1] > y0) & (C[:, 1] < y1) & (C[:, 2] > z0) & ~((C[:, 1] > eye_y) & (ac < eye_x))
    ex0, ex1, ey0, ey1, ez0, ez1 = EARS   # (and the ears and the sideburns' skin, behind the eyes)
    sel |= sk3 & (ac > ex0) & (ac < ex1) & (C[:, 1] > ey0) & (C[:, 1] < ey1) & (C[:, 2] > ez0) & (C[:, 2] < ez1)
    mask = np.zeros(t.shape[:2], bool)
    for k in np.nonzero(sel)[0]:
        q, _ = _texels(UV[I[k]] * TS, A[k], TS); mask[q[:, 1], q[:, 0]] = True
    v = np.clip(t, 0, 255); lum = v.mean(2); r, g, b = v[..., 0], v[..., 1], v[..., 2]
    bad = mask & (((lum > 140) & (r - b < 60)) | ((lum > 160) & (g - b < 35)) | ((lum < 150) & (b >= g - 2)) | (lum < 70))   # (light grey or pink, purple, black)
    good = mask & ~bad
    if not bad.any() or not good.any(): return 0
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True); t[bad] = t[iy[bad], ix[bad]]
    return int(bad.sum())


def load_bust(path):
    j, BIN = read_glb(path); G, _ = world_mats(j)
    ni = next(i for i, nd in enumerate(j['nodes']) if 'mesh' in nd); M = G[ni]
    pr = j['meshes'][j['nodes'][ni]['mesh']]['primitives'][0]; at = pr['attributes']
    P = acc(j, BIN, at['POSITION']).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    N = acc(j, BIN, at['NORMAL']).astype(np.float64) @ np.linalg.inv(M[:3, :3]); N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    UV = acc(j, BIN, at['TEXCOORD_0']).astype(np.float64); I = acc(j, BIN, pr['indices']).reshape(-1, 3).astype(np.int64)
    img = j['images'][0]; bv = j['bufferViews'][img['bufferView']]
    import io
    tex = Image.open(io.BytesIO(BIN[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']])).convert('RGB')
    return P, N, UV, I, tex


def load_package(pkg):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2)
    J = f(me['jnt'], np.uint8).reshape(-1, 4).astype(np.int64); W = f(me['wgt']).reshape(-1, 4).astype(np.float64)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    tex = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(int); ts = tex.shape[0]
    col = tex[np.clip((UV[:, 1] * ts).astype(int), 0, ts - 1), np.clip((UV[:, 0] * ts).astype(int), 0, ts - 1)]
    return name, m, P, J, W, I, col


# The eyes flush with the face (Meshy sank them 1 cm into sockets under a ledge, the upper lid: seen from below or the side
# the ledge hid the iris and left the white, a blank stare): around each eye (BUSTS sockets, an ellipse of SOCKET_R half
# axes in bust units) the face's points move along z only (seen from the front nothing changes) onto a smooth fit of the
# face's skin around them (SOCKET_FIT: the box it is fit over; a cubic in x, y; the sockets and the nose left out), fully
# inside SOCKET_CORE of the ellipse, fading to nothing at its edge (the upper lid's ledge, its lines darker than
# SOCKET_LASH, pushed back onto it too). Not the hair's locks in front of the face (more than SOCKET_HAIR in front of the
# fit, purple). Their normals: the new surface's.
SOCKET_R, SOCKET_CORE, SOCKET_FIT, SOCKET_HAIR, SOCKET_LASH = (.1, .056), .65, (.27, (.04, .36)), .012, 36


def flatten_eyes(P, N, I, col, eyes):
    """The bust's points and normals with its eyes flush with the face (see SOCKET_*); P, N: bust units."""
    if not eyes: return P, N
    X = lambda p: np.stack([np.ones(len(p)), p[:, 0], p[:, 1], p[:, 0] ** 2, p[:, 0] * p[:, 1], p[:, 1] ** 2, p[:, 0] ** 3, p[:, 0] ** 2 * p[:, 1], p[:, 0] * p[:, 1] ** 2, p[:, 1] ** 3], 1)
    ell = np.min([((P[:, 0] - ex) / SOCKET_R[0]) ** 2 + ((P[:, 1] - ey) / SOCKET_R[1]) ** 2 for ex, ey in eyes], 0)
    skin = skin_of(col) & (col[:, 0] - col[:, 1] > 40)
    box = (np.abs(P[:, 0]) < SOCKET_FIT[0]) & (P[:, 1] > SOCKET_FIT[1][0]) & (P[:, 1] < SOCKET_FIT[1][1]) & (N[:, 2] > .2) & (P[:, 2] > 0)
    nose = (np.abs(P[:, 0]) < .045) & (P[:, 1] < min(ey for _, ey in eyes) - .02)
    use = box & skin & (ell > 1.3) & ~nose
    for _ in range(5):
        c = np.linalg.lstsq(X(P[use]), P[use, 2], rcond=None)[0]; r = P[:, 2] - X(P) @ c; use = use & (np.abs(r) < .02)
    fit = X(P) @ c; w = np.clip((1 - np.sqrt(ell)) / (1 - SOCKET_CORE), 0, 1); w = w * w * (3 - 2 * w)
    lash = col.mean(1) < SOCKET_LASH   # (the lids' lines and lashes, near black: on the face's ledge, flattened too; the hair is purple)
    mv = (w > 0) & ((P[:, 2] < fit + SOCKET_HAIR) | (lash & (P[:, 2] < fit + .08))) & (P[:, 2] > fit - .08)
    Q = P.copy(); Q[mv, 2] += w[mv] * (fit[mv] - P[mv, 2])
    # normals: the moved surface's (area weighted, over the copies of a point along the texture's seams)
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    T = weld[I]; Pw = Q[first]; fn = np.cross(Pw[T[:, 1]] - Pw[T[:, 0]], Pw[T[:, 2]] - Pw[T[:, 0]]); acc = np.zeros((len(first), 3))
    for k in range(3): np.add.at(acc, T[:, k], fn)
    nn = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    aff = np.zeros(len(first), bool); aff[T[(mv[I]).any(1)].ravel()] = True
    N2 = N.copy(); sel = aff[weld]; N2[sel] = nn[weld[sel]]
    d = (Q - P)[mv, 2]
    print('eyes flush: %d points moved forward up to %.3f (mean %.3f) bust units, %d normals renewed; the fit\'s rms %.4f over %d skin points' % (
        int(mv.sum()), d.max(), d.mean(), int(sel.sum()), np.sqrt((r[use] ** 2).mean()), int(use.sum())))
    return Q, N2


# The bangs close to the face (Meshy hung them 1-3 cm in front of it: with the head bent forward in the guard, or seen
# from a little above, they covered the eyes; on the sheet the eyes are clear): the hair's points in front of the face
# (BANGS_BOX: |x| and the y range, bust units) come toward its surface along z only (seen from the front nothing
# changes), to BANGS_KEEP of their distance from it (never nearer than BANGS_MIN), fully under BANGS_Y[0], not at all
# above BANGS_Y[1]. The face's surface: the front-most skin seen from the front (a grid of BANGS_CELL).
BANGS_BOX, BANGS_Y, BANGS_KEEP, BANGS_MIN, BANGS_CELL = (.27, (.08, .34)), (.25, .31), .35, .006, .004


def bangs_back(P, N, I, col):
    """The bust's points and normals with its bangs close to the face (see BANGS_*); P, N: bust units."""
    from scipy import ndimage
    skin = skin_of(col) & (col[:, 0] - col[:, 1] > 40)
    t = I[skin[I].all(1)]
    x0, x1, y0, y1 = -BANGS_BOX[0] - .05, BANGS_BOX[0] + .05, BANGS_BOX[1][0] - .05, BANGS_BOX[1][1] + .05
    nx, ny = int((x1 - x0) / BANGS_CELL) + 1, int((y1 - y0) / BANGS_CELL) + 1; Z = np.full((nx, ny), -np.inf)
    for a, b, c in P[t]:
        lo = np.maximum(np.floor((np.minimum(np.minimum(a, b), c)[:2] - [x0, y0]) / BANGS_CELL).astype(int), 0); hi = np.minimum(np.ceil((np.maximum(np.maximum(a, b), c)[:2] - [x0, y0]) / BANGS_CELL).astype(int), [nx - 1, ny - 1])
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if (hi < lo).any() or abs(d) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1), indexing='ij'); X = x0 + gx * BANGS_CELL; Y = y0 + gy * BANGS_CELL
        u = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d; v = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d; w = 1 - u - v
        zz = u * a[2] + v * b[2] + w * c[2]; up = (u >= -.02) & (v >= -.02) & (w >= -.02) & (zz > Z[gx, gy]); Z[gx[up], gy[up]] = zz[up]
    have = np.isfinite(Z)
    if not have.any(): return P, N
    _, (ix, iy) = ndimage.distance_transform_edt(~have, return_indices=True); Z = ndimage.gaussian_filter(Z[ix, iy], 1.)
    zf = Z[np.clip(((P[:, 0] - x0) / BANGS_CELL).round().astype(int), 0, nx - 1), np.clip(((P[:, 1] - y0) / BANGS_CELL).round().astype(int), 0, ny - 1)]
    hair = ~skin & (col.mean(1) < 130) & ~((col[:, 1] > col[:, 0] + 8) & (col[:, 2] > col[:, 0] + 8))
    inb = (np.abs(P[:, 0]) < BANGS_BOX[0]) & (P[:, 1] > BANGS_BOX[1][0]) & (P[:, 1] < BANGS_BOX[1][1])
    gap = P[:, 2] - zf; mv = hair & inb & (gap > BANGS_MIN) & (gap < .2)
    wy = np.clip((BANGS_Y[1] - P[:, 1]) / (BANGS_Y[1] - BANGS_Y[0]), 0, 1); wy = wy * wy * (3 - 2 * wy)
    k = 1 - wy * (1 - BANGS_KEEP)
    Q = P.copy(); Q[mv, 2] = zf[mv] + np.maximum(gap[mv] * k[mv], np.minimum(gap[mv], BANGS_MIN))
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    T = weld[I]; Pw = Q[first]; fn = np.cross(Pw[T[:, 1]] - Pw[T[:, 0]], Pw[T[:, 2]] - Pw[T[:, 0]]); acc = np.zeros((len(first), 3))
    for j in range(3): np.add.at(acc, T[:, j], fn)
    nn = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    aff = np.zeros(len(first), bool); aff[T[(mv[I]).any(1)].ravel()] = True
    N2 = N.copy(); sel = aff[weld]; N2[sel] = nn[weld[sel]]
    print('bangs: %d hair points in front of the face brought closer (from %.3f to %.3f bust units in front on average)' % (int(mv.sum()), gap[mv].mean(), (Q[mv, 2] - zf[mv]).mean()))
    return Q, N2


def place(Pb, colb, P, col, fit, HEAD_EYE, HEAD_CHIN, HEAD_NECK):
    """The bust's points in the body's bind space (metres): (scale, a function of bust points)."""
    s_d, cx, by = fit
    eye_m, chin_m = (by - DRAW_EYE) / s_d, (by - DRAW_CHIN) / s_d
    s = (eye_m - chin_m) / (HEAD_EYE - HEAD_CHIN)
    nb = skin_of(colb) & (Pb[:, 1] > HEAD_NECK[0]) & (Pb[:, 1] < HEAD_NECK[1]) & (np.abs(Pb[:, 0]) < .3)
    bx, bz, br = circle(Pb[nb, 0], Pb[nb, 2])
    no = skin_of(col) & (P[:, 1] > BODY_NECK[0]) & (P[:, 1] < BODY_NECK[1]) & (np.abs(P[:, 0]) < .08)
    ox, oz, orr = circle(P[no, 0], P[no, 2])
    print('placing: scale %.4f m per unit; the bust\'s neck (%.3f, %.3f) r %.3f -> the body\'s (%.4f, %.4f) r %.4f (the bust\'s %.4f m)' % (s, bx, bz, br, ox, oz, orr, br * s))
    T = np.array([ox - s * bx, eye_m - s * HEAD_EYE, oz - s * bz])
    return s, lambda q: q * s + T


def main(bust, pkg, out, texture=None):
    Pb, Nb, UVb, Ib, texb = load_bust(bust)
    tb = np.asarray(texb).astype(int); th = tb.shape[0]
    colb = tb[np.clip((UVb[:, 1] * th).astype(int), 0, th - 1), np.clip((UVb[:, 0] * th).astype(int), 0, th - 1)]
    name, m, P, J, W, I, col = load_package(pkg)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ren_look import drawing_fit
    from scipy import ndimage
    D = np.asarray(Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'ref', 'personaggi', 'ren.png')).convert('RGB')).astype(np.float64)
    bg = D[5:40, 5:40].reshape(-1, 3).mean(0); mask = ndimage.binary_opening(np.abs(D - bg).sum(2) > 30, iterations=1)
    fit = drawing_fit(P, mask)[1:]
    bp = BUSTS[os.path.splitext(os.path.basename(bust))[0]]; HEAD_CUT = bp['cut']
    Pb, Nb = flatten_eyes(Pb, Nb, Ib, colb, bp.get('sockets'))
    if bp.get('bangs'): Pb, Nb = bangs_back(Pb, Nb, Ib, colb)
    s, tr = place(Pb, colb, P, col, fit, bp['eye'], bp['chin'], bp['neck'])
    # the cut: the bust's triangles above HEAD_CUT (all three corners)
    keep = (Pb[Ib, 1] > HEAD_CUT).all(1)
    # (and the bust's shirt's corners over the chest's top, under the collarbones: dark points through the body's skin)
    Cb = tr(Pb[Ib].mean(1)); cb = colb[Ib].mean(1)
    corner = (Cb[:, 1] < HIDE_Y + .01) & (np.abs(Cb[:, 0] - BODY_X) < .08) & (Cb[:, 2] > -.01) & (cb.mean(1) < 100) & ~((cb[:, 1] > cb[:, 0] + 8) & (cb[:, 2] > cb[:, 0] + 8))
    print('the bust\'s shirt corners over the chest left out: %d triangles' % int((keep & corner).sum()))
    keep &= ~corner; It = Ib[keep]
    used = np.unique(It); remap = np.full(len(Pb), -1); remap[used] = np.arange(len(used))
    Q = tr(Pb[used]); Nq = Nb[used]; UVq = UVb[used]; Iq = remap[It]
    # skin, by part (see above)
    from scipy.spatial import cKDTree
    bones = [b['n'] for b in m['bones']]; nb = len(bones); hb, nk, sp = bones.index('Head'), bones.index('neck'), bones.index('Spine')
    c = colb[used]; lum = c.mean(1)
    skin = skin_of(c) & (c[:, 0] - c[:, 1] > 40); teal = (c[:, 1] > c[:, 0] + 10) & (c[:, 2] > c[:, 0] + 10); dark = (lum < 110) & ~teal
    ax = circle(*Q[(Q[:, 1] > BODY_NECK[0]) & (Q[:, 1] < HEAD_JAW) & skin][:, [0, 2]].T)   # (the new neck's axis)
    shirt = dark & (Q[:, 1] < HEAD_JAW - .015) & (Q[:, 2] > ax[1])
    trim = (c.min(1) > 140) & (c[:, 0] - c[:, 2] > 15) & (c[:, 0] - c[:, 2] < 60) & ~skin
    head = (dark & ~shirt) | ((Q[:, 1] >= HEAD_JAW) & ~teal & ~trim)   # (above the jaw all of it: the eyes' whites and irises too)
    head |= Q[:, 1] >= HEAD_TOP   # (above the collar's top all of it, whatever its colour: hair and face in light or teal-ish
    # tints, taken for the collar's trim or teal, had a quarter of their weight on the spine and the shoulders and came off
    # the head when it turned, up to 7 cm on the ground)
    print('above the jaw left to the collar (its teal and trim): %d vertices' % int(((Q[:, 1] >= HEAD_JAW) & ~head).sum()))
    neck = skin & ~head
    rest = ~head & ~neck   # the collar, its trim, the shirt
    Wf = np.zeros((len(Q), nb)); Wf[head, hb] = 1
    t = np.clip((Q[neck, 1] - HIDE_Y) / (HEAD_JAW - HIDE_Y), 0, 1)
    Wf[neck, hb] = t; Wf[neck, nk] = (1 - t) * .7 + t * 0; Wf[neck, sp] = (1 - t) * .3
    Wf[neck] /= Wf[neck].sum(1, keepdims=True)
    hw = ((J == hb) * W).sum(1); body = np.nonzero(hw < .3)[0]
    _, near = cKDTree(P[body]).query(Q[rest]); near = body[near]
    for k in range(4): np.add.at(Wf, (np.nonzero(rest)[0], J[near, k]), W[near, k] * (J[near, k] != hb))
    Wf[rest] /= np.maximum(Wf[rest].sum(1, keepdims=True), 1e-12)
    # the collar stands up stiff: from COLLAR_STIFF[0] to [1] m up its share of the shoulders' and arms' weights goes to
    # the top of the spine, up to COLLAR_STIFF[2] (on the shoulders, the nearest body vertex's, its back tore into shards
    # when the arms went up: each half followed its own shoulder)
    y0, y1, f = COLLAR_STIFF; sh = [bones.index(n) for n in ('LeftShoulder', 'RightShoulder', 'LeftArm', 'RightArm')]
    k = np.nonzero(rest)[0]; mv = np.clip((Q[k, 1] - y0) / (y1 - y0), 0, 1) * f
    take = Wf[np.ix_(k, sh)] * mv[:, None]; Wf[np.ix_(k, sh)] -= take; Wf[k, sp] += take.sum(1)
    print('collar: %d vertices stiffer (their shoulders\' weight to the spine, up to %d%%)' % (int((mv > 0).sum()), round(100 * f)))
    print('skin: head %d, neck %d, collar and shirt %d vertices' % (head.sum(), neck.sum(), rest.sum()))
    if TEMPLE_SMOOTH: print('temples: %d points around %d locks laid flat placed smooth (bi-harmonic)' % temple_smooth(Q, UVq, Iq, tb))
    else: print('temples: %d points of %d locks laid flat sunk under the skin' % temple_locks(Q, UVq, Iq, tb))
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel(); nw = len(first)
    T = weld[Iq]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    from scipy.sparse import csr_matrix
    A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)); deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)
    Ww = np.zeros((nw, nb)); np.add.at(Ww, weld, Wf); Ww /= np.bincount(weld, minlength=nw)[:, None]
    hw_ = np.zeros(nw, bool); hw_[weld[head]] = True
    for _ in range(HEAD_SMOOTH): Ww = np.where(hw_[:, None], Ww, .5 * Ww + .5 * (A @ Ww) / deg[:, None])
    Wv = Ww[weld]; top = np.argsort(-Wv, 1)[:, :4]; tw = np.take_along_axis(Wv, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-12)
    # hidden: the body's triangles all above HIDE_Y that the new head covers: its old head (the Head bone's), and the rest
    # (the old collar, the vest's top, the neck) where a ray out of the triangle along its normal meets the new head within
    # HIDE_RAY m (the shoulders' tops it does not cover stay: hidden, their holes showed the outline's black inside)
    up = (P[I, 1] > HIDE_Y).all(1); hw3 = ((J == hb) * W).sum(1)[I].mean(1)
    no = skin_of(col) & (P[:, 1] > BODY_NECK[0]) & (P[:, 1] < BODY_NECK[1]) & (np.abs(P[:, 0]) < .08); circle_body = circle(P[no, 0], P[no, 2])
    cand = np.nonzero(up & (hw3 < .5))[0]
    A0 = Q[Iq[:, 0]]; E1 = Q[Iq[:, 1]] - A0; E2 = Q[Iq[:, 2]] - A0
    cen = P[I[cand]].mean(1); fnb = np.cross(P[I[cand, 1]] - P[I[cand, 0]], P[I[cand, 2]] - P[I[cand, 0]]); fnb /= np.maximum(np.linalg.norm(fnb, axis=1, keepdims=True), 1e-12)
    covered = np.zeros(len(cand), bool)
    for k in range(len(cand)):   # (Moller-Trumbore against all the head's triangles)
        o, d = cen[k] + fnb[k] * 1e-4, fnb[k]; pv = np.cross(d, E2); det = (E1 * pv).sum(1); ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0); tv = o - A0; u = (tv * pv).sum(1) * inv; qv = np.cross(tv, E1); v = (qv @ d) * inv; t = (qv * E2).sum(1) * inv
        covered[k] = (ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0) & (t < HIDE_RAY)).any()
    tcol = col[I[cand]].mean(1); old_neck = skin_of(tcol) | (np.hypot(cen[:, 0] - BODY_X, cen[:, 2] - circle_body[1]) < HIDE_NECK_R)   # (the old neck: the new one replaces it)
    covered |= old_neck
    old_collar = tips = np.zeros(len(cand), bool)   # (hiding more of the old collar opened holes into the outline's black)
    # (the old collar below HIDE_Y stays: the vest over the chest is the same piece, hidden it left holes)
    hide = np.sort(np.concatenate([np.nonzero(up & (hw3 >= .5))[0], cand[covered]])).astype(np.uint32)
    print('hidden: %d of the old head, %d of %d others under the new head or of the old collar (%d of it, %d by its pulled points; %d kept: not covered)' % (
        int((up & (hw3 >= .5)).sum()), int(covered.sum()), len(cand), int(old_collar.sum()), int(tips.sum()), int((~covered).sum())))
    blob = bytearray()
    def put(arr):
        while len(blob) % 4: blob.append(0)
        o = len(blob); blob.extend(np.ascontiguousarray(arr).tobytes()); return [o, int(arr.size)]
    lb, grid = fringe_back(Q, Nq, Iq, skin, dark, ax)
    # the temples and the ears' tops: the outline further back too (TEMPLE_LINE: |x| from the middle, y, z ranges, m; the push,
    # m; its ramp at the edges, m): under the sideburns and the sunk locks the surface folds and faces down, its outline
    # showed through the skin as black splinters by the eyes' outer corners and over the cheeks at the ears
    x0_, x1_, y0_, y1_, z0_, z1_, push_, ramp_ = TEMPLE_LINE; ax_ = np.abs(Q[:, 0] - BODY_X)
    inside_ = np.minimum.reduce([ax_ - x0_, x1_ - ax_, Q[:, 1] - y0_, y1_ - Q[:, 1], Q[:, 2] - z0_, z1_ - Q[:, 2]])
    lb_line = np.maximum(lb, push_ * np.clip(inside_ / ramp_, 0, 1))   # (the outline's only: lb itself says which is hair over the face)
    print('temples: %d vertices with their outline %.0f mm back' % (int((inside_ > 0).sum()), 1000 * push_))
    print('fringe: %d vertices of the hair over the face, their outline %.0f to %.0f mm further back' % (int((lb > .5 * FRINGE[0]).sum()), 1000 * FRINGE[0], 1000 * lb.max()))
    im = Image.open(texture).convert('RGB') if texture else texb
    pal = bp.get('palette', HEAD_PALETTE); t = np.asarray(im).astype(np.float64); src = np.array([a for a, _ in pal], float); dst = np.array([b for _, b in pal], float)
    flat = t.reshape(-1, 3); d2 = ((flat[:, None, :] - src[None]) ** 2).sum(2); w = np.exp(-d2 / (2 * HEAD_SPREAD ** 2)); ws = w.sum(1, keepdims=True)
    flat = flat + (w @ (dst - src)) / np.maximum(ws, 1e-9) * np.clip(ws, 0, 1)   # (far from every palette colour: unchanged)
    t = np.clip(flat.reshape(t.shape), 0, 255)
    # (before the temples': there the locks sunk under the skin, painted as skin, must stay so: dark, they showed through it)
    print('fringe: %d light texels on the locks over the face painted as hair' % fringe_paint(t, Q, UVq, Iq, lb, grid))
    print('temples: %d texels of Meshy\'s sideburns painted as skin, %d of their stretched triangles all skin' % temples(t, Q, UVq, Iq))
    print('temple spot: %d brown texels painted as skin' % temple_spot(t, Q, UVq, Iq))
    print('cheeks: %d texels of Meshy\'s marks painted as the skin around them' % cheek_marks(t, Q, UVq, Iq))
    # the face's locks from the sheet (tools/ren_fringe.py): Meshy's fringe over the forehead out, the sheet's locks in
    from ren_fringe import fringe as sheet_fringe
    Ik = sheet_fringe(Q, Nq, UVq, Iq, t, name, out)
    # the eyes and the skin around them redrawn clean (tools/ren_eyes.py): the -x eye and brow from the +x ones, the
    # bridge plain skin, the pieces floating off the head out, a plug of skin under the face's holes (its outline back)
    from ren_eyes import eyes as clean_eyes
    Ik, plug = clean_eyes(Q, Nq, UVq, Ik, t)
    if plug is not None:
        n0 = len(Q); Q = np.r_[Q, plug['pos']]; Nq = np.r_[Nq, plug['nor']]; UVq = np.r_[UVq, plug['uv']]
        top = np.r_[top, top[plug['src']]]; tw = np.r_[tw, tw[plug['src']]]
        lb_line = np.r_[lb_line, np.full(len(plug['pos']), PLUG_LINE)]; Ik = np.r_[Ik, plug['tri'] + n0]
    nv = len(Q)
    head = {'v': 1, 'verts': nv, 'tris': len(Ik), 'scale': round(s, 5), 'pos': put(Q.astype(np.float32)), 'nor': put(Nq.astype(np.float32)), 'uv': put(UVq.astype(np.float32)),
            'jnt': put(top.astype(np.uint8)), 'wgt': put(tw.astype(np.float32)), 'idx': put(Ik.astype(np.uint32 if nv > 65535 else np.uint16)), 'hide': put(hide), 'lb': put(lb_line.astype(np.float32))}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_head.bin'), 'wb').write(bytes(blob))
    json.dump(head, open(os.path.join(out, name + '_head.json'), 'w'), separators=(',', ':'))
    # the texels between the UV pieces take their nearest piece's colour (the texture's filtering, at a distance, pulled
    # Meshy's packing colours into the pieces' edges: specks and lines along the seams)
    from PIL import ImageDraw
    from scipy import ndimage
    TS = t.shape[0]; mimg = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(mimg)
    for tri in UVq[Ik] * TS: dr.polygon([tuple(v) for v in tri], fill=255)
    inside = ndimage.binary_dilation(np.asarray(mimg) > 0, iterations=2)
    _, (gy, gx) = ndimage.distance_transform_edt(~inside, return_indices=True); t = t[gy, gx]
    print('texture: %d%% of its texels in the head\'s pieces, the rest padded' % round(100 * inside.mean()))
    im = Image.fromarray(t.round().astype(np.uint8))
    if max(im.size) > HEAD_TEX: im = im.resize((HEAD_TEX, HEAD_TEX), Image.LANCZOS)
    im.save(os.path.join(out, name + '_head.jpg'), quality=88, optimize=True)
    main_b = np.bincount(top[:, 0], minlength=nb)
    print('head: %d verts, %d tris (of %d; under the cut left out), from y %.3f to %.3f m; the body\'s triangles hidden: %d of %d; main bones %s' % (
        nv, len(Ik), len(Ib), Q[:, 1].min(), Q[:, 1].max(), len(hide), len(I), {bones[i]: int(c) for i, c in enumerate(main_b) if c}))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
