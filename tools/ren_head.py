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
TAILS_PIECE, TAILS_Y = 200, (.5, 1.1)   # see main(): the old tails' floating pieces (triangles), where (y, m)
HEAD_SMOOTH, HEAD_JAW, HEAD_TOP = 3, 1.515, 1.535   # (HEAD_TOP: above it all on the Head bone; the collar ends at 1.529)
COLLAR_STIFF = (1.46, 1.50, .8)   # see main(): the collar's top on the spine, not on the shoulders
# the collar's back wall pushed back (9/11/2026, Denis: "vestito crea sta specie di gobba sulla schiena sotto al colletto"): the
# bust's collar met the vest at its base (1.44-1.46 m) but stood 3 cm further in above it, and in the guard (the spine bent
# forward) the vest's back rose behind it as a hump; as in the sheets (ren_retro.png) it stands on the back: the collar's
# vertices (not the head's nor the neck's) from COLLAR_FLARE[0] m up (all of it from [1]) and behind the neck (z under [2],
# all of it under [3]) go back [4] m, their normals turned with them
COLLAR_FLARE = (1.455, 1.475, -.04, -.08, .03)
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
CHIN_LINE = (0, .045, 1.497, 1.527, .035, .095, .006, .004)   # see main(): the chin's lower part's outline pushed back (as TEMPLE_LINE; [0] unused)
LAPEL_TOPS = (38., 52., 1.432, .105, .15)   # see main()
LAPEL_LINING = (20., 70., 1.33, .16)   # see main(): |angle from the front| between [0] and [1] degrees, above [2] m, within [3] m of the neck's axis
LAPEL_NOLINE = (30., 60., 1.40, .09, .15)   # see main(): as LAPEL_TOPS
BODY_HOLES = (40, 1.04, .03)   # see body_holes()
CHEEKS = (.03, 1.525, 1.595, .015, 1.583, .07)   # see cheek_marks(): |x| over, y between, z over, the eyes' band (over y, within |x|)
EARS = (.045, .1, 1.545, 1.615, -.035, .03)   # see cheek_marks(): |x|, y, z ranges (m)
TEMPLE_SPOT = (-.078, -.052, 1.570, 1.592, -.012, .016)   # (x, y, z ranges, m) a brown spot on one temple: see temple_spot()
PLUG_LINE = .1                             # the outline of the plug under the face's holes (tools/ren_eyes.py): pushed back (m)
FRINGE_PAINT = (.0008, 120., (60, 50, 60))   # see fringe_paint(): in front of the face by (m), lighter than (mean rgb), the colour they take
FRINGE_NEAR, FRINGE_MAX = .01, .05
FRINGE = (.02, .008, .004, 3, .002)   # the hair over the face: its outline's push back (m), the face's reach around it, the depth slack (m), smoothing rounds, grid (m): see fringe_back()
# the neck's marks clean: see main() (9/11/2026, "sistemi i colori dentro al colletto sul collo")
NECK_CLEAN, NECK_SHADE = (1.53, .62, .0007, .062, 1.40), np.array([.82, .74, .72])
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


def body_holes(Q, N, UV, I, J, W, lb, TS, taken, PB, IB, UVB, JB, WB, NB, FB, keep, paint):
    """The body's holes (its kept triangles' open loops, BODY_HOLES: of at most [0] points, all under [1] m: where the old
    tails were hidden) closed by the head's triangles: the loop's points copied (skinned as the body's there, JB and WB,
    with its light's normals NB and flat share FB) and ear-clipped across, in a flat block of the head's texture each, in
    the body's paint around it (paint at the loop's uvs, the median); their outline pushed back BODY_HOLES[2] m. Returns
    (Q, N, UV, I, J, W, lb with them, the blocks [(row, col, half, rgb)], (the first new vertex, their flat shares) or None)."""
    from ren_collar import free_blocks
    _, first, weld = np.unique(np.round(PB / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    kt = IB[keep]; T = weld[kt]
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); key = np.sort(E, 1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True); bd = E[cnt[inv.ravel()] == 1]
    out_ = {}
    for a, b in bd: out_.setdefault(int(b), []).append(int(a))   # (each boundary edge a->b as its triangle has it; the fill runs b->a)
    rep = np.full(len(first), -1); rep[T.ravel()] = kt.ravel(); Pw = PB[first]
    # (the loops, walked edge by edge: where a loop touches itself at a point, cut there into simple ones)
    found = []
    for s0 in list(out_):
        while out_.get(s0):
            path, at = [s0], {s0: 0}; c = s0
            while out_.get(c):
                d = out_[c].pop()
                if d in at:
                    k = at[d]; found.append(path[k:])
                    for v in path[k + 1:]: del at[v]
                    path = path[:k + 1]
                else: at[d] = len(path); path.append(d)
                c = path[-1]
    loops = [lp for lp in found if 3 <= len(lp) <= BODY_HOLES[0] and Pw[lp, 1].max() < BODY_HOLES[1]]
    if not loops: return Q, N, UV, I, J, W, lb, [], None
    if NB is None:
        fn = np.cross(PB[IB[:, 1]] - PB[IB[:, 0]], PB[IB[:, 2]] - PB[IB[:, 0]]); NB = np.zeros_like(PB)
        for k in range(3): np.add.at(NB, IB[:, k], fn)
        NB = NB / np.maximum(np.linalg.norm(NB, axis=1, keepdims=True), 1e-12)
    blocks = free_blocks(UV, I, TS, len(loops), half=8, taken=taken); PS = paint.shape[0]
    n0 = len(Q); newP, newN, newUV, newJ, newW, newF, newT, out_blk = [], [], [], [], [], [], [], []
    for lp, (r0, c0, b0) in zip(loops, blocks):
        rv = rep[lp]; rgb = np.median(paint[np.clip((UVB[rv, 1] * PS).astype(int), 0, PS - 1), np.clip((UVB[rv, 0] * PS).astype(int), 0, PS - 1)], 0)
        out_blk.append((r0, c0, b0, rgb)); uvf = np.array([(c0 + .5) / TS, (r0 + .5) / TS]); base = n0 + len(newP)
        for v, r in zip(lp, rv):
            newP.append(Pw[v]); newN.append(NB[r]); newUV.append(uvf); newJ.append(JB[r]); newW.append(WB[r]); newF.append(FB[r] if FB is not None else 0.)
        # (ear clipping in the loop's best plane, its order the fill's winding; a fan from its first point if it fails)
        P = Pw[lp]; ctr = P.mean(0); _, _, vt = np.linalg.svd(P - ctr); q = (P - ctr) @ vt[:2].T
        cross = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        sg = np.sign(sum(cross(np.zeros(2), q[i], q[(i + 1) % len(q)]) for i in range(len(q)))) or 1.
        idx, tris = list(range(len(lp))), []
        while len(idx) > 3:
            for k in range(len(idx)):
                i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
                if cross(q[i0], q[i1], q[i2]) * sg <= 0: continue
                if any(cross(q[i0], q[i1], q[j]) * sg > 0 and cross(q[i1], q[i2], q[j]) * sg > 0 and cross(q[i2], q[i0], q[j]) * sg > 0 for j in idx if j not in (i0, i1, i2)): continue
                tris.append((i0, i1, i2)); idx.pop(k); break
            else:   # (no ear: the rest as a fan)
                tris += [(idx[0], idx[j], idx[j + 1]) for j in range(1, len(idx) - 2)]; idx = [idx[0], idx[-2], idx[-1]]
        tris.append(tuple(idx))
        # (each turned to face as the body's light normals there: the head draws both sides, its light by the side seen)
        for a, b, c in tris:
            fn_ = np.cross(P[b] - P[a], P[c] - P[a]); nn_ = NB[rv[a]] + NB[rv[b]] + NB[rv[c]]
            newT.append((base + a, base + b, base + c) if fn_ @ nn_ >= 0 else (base + a, base + c, base + b))
    na = len(newP)
    Q2 = np.r_[Q, np.array(newP)]; N2 = np.r_[N, np.array(newN)]; UV2 = np.r_[UV, np.array(newUV)]
    J2 = np.r_[J, np.array(newJ, J.dtype)]; W2 = np.r_[W, np.array(newW, W.dtype)]; lb2 = np.r_[lb, np.full(na, BODY_HOLES[2], lb.dtype)]
    I2 = np.r_[I, np.array(newT, I.dtype)]
    print('body: %d holes closed (%s points, %d triangles of the head\'s), in their paint %s' % (len(loops), [len(l) for l in loops], len(newT), [np.round(b_[3]).astype(int).tolist() for b_ in out_blk]))
    return Q2, N2, UV2, I2, J2, W2, lb2, out_blk, (n0, np.array(newF))


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
    # the collar's back wall pushed back (COLLAR_FLARE): z -= push f(y) g(z); the normals by the inverse transpose of the
    # displacement's gradient (only d z/d y and d z/d z: n' = (nx, ny - a nz / (1 + b), nz / (1 + b)))
    fy0, fy1, fz0, fz1, push = COLLAR_FLARE
    def _sm(e0, e1, x):
        u = np.clip((x - e0) / (e1 - e0), 0, 1); return u * u * (3 - 2 * u), np.where((u > 0) & (u < 1), 6 * u * (1 - u) / (e1 - e0), 0)
    fy, dfy = _sm(fy0, fy1, Q[:, 1]); gz, dgz = _sm(fz0, fz1, Q[:, 2])
    _, wq = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wq = wq.ravel()   # (the copies of a vertex
    on = (np.bincount(wq, rest.astype(float)) / np.bincount(wq))[wq]   # on the texture's seams move as one: the collar's share of them)
    a = -push * dfy * gz * on; b = -push * fy * dgz * on; Q[:, 2] -= push * fy * gz * on
    Nq = np.c_[Nq[:, 0], Nq[:, 1] - a * Nq[:, 2] / (1 + b), Nq[:, 2] / (1 + b)]; Nq /= np.maximum(np.linalg.norm(Nq, axis=1, keepdims=True), 1e-12)
    print('collar: %d vertices of its back wall pushed back (all %.0f mm: %d)' % (int((fy * gz * on > 0).sum()), 1000 * push, int((fy * gz * on > .999).sum())))
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
    # the sash's old tails (8/11, Denis: "rimuovere dal corpo la vecchia fascia ... le fasce che abbiamo sostituito con quelle
    # che si muovono"): Meshy's two tails hanging at the hips (ren_look.sash_tails: its orange under the band; the ribbons
    # of the look replace them), hidden too (every triangle with ren_look.TAILS_TOUCH of their vertices: the row that joined
    # them to the vest too, 9/11), with the pieces their removal leaves floating (under TAILS_PIECE triangles, their dark
    # edges); they lie on the trousers and the vest, which are whole under them (no holes)
    from ren_look import sash_tails, TAILS_TOUCH
    tv = np.zeros(len(P), bool)
    for tl in sash_tails(P, col, I): tv[tl] = True
    gone = tv[I].sum(1) >= TAILS_TOUCH; kept = np.ones(len(I), bool); kept[hide] = False; kept &= ~gone
    from scipy.sparse import csr_matrix as _csr
    from scipy.sparse.csgraph import connected_components as _cc
    _, wb = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True); wb = wb.ravel(); K = np.nonzero(kept)[0]
    Aw = _csr((np.ones(3 * len(K)), (np.repeat(np.arange(len(K)), 3), wb[I[K]].ravel())), shape=(len(K), wb.max() + 1))
    _, lab = _cc(Aw @ Aw.T, directed=False); szc = np.bincount(lab)
    Ck = P[I[K]].mean(1); bits = K[(szc[lab] < TAILS_PIECE) & (Ck[:, 1] > TAILS_Y[0]) & (Ck[:, 1] < TAILS_Y[1])]
    from ren_look import tail_stubs
    stubs = tail_stubs(P, col, I, tv)   # (and their tops under the band, 9/11: torn ends beside the ribbons)
    hide = np.unique(np.concatenate([hide, np.nonzero(gone)[0], bits, stubs])).astype(np.uint32)
    print('old sash tails: %d triangles hidden, %d of the pieces their removal left floating, %d of their tops under the band' % (int(gone.sum()), len(bits), len(stubs)))
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
    # and the chin's lower part (9/11/2026, Denis on a close-up in guard: "questo pezzo nero sulla faccia"): with the head
    # bent down in guard and seen from the front, the chin's bottom is near the line of sight and its small waves turn
    # some triangles away from the camera: their outline showed as a second black stroke beside the jaw line, on the
    # chin; pushed back (CHIN_LINE, as TEMPLE_LINE) it stays behind the chin's skin, the jaw line over the neck (3 cm
    # and more behind it) stays
    x0_, x1_, y0_, y1_, z0_, z1_, push_, ramp_ = CHIN_LINE
    inside_ = np.minimum.reduce([x1_ - ax_, Q[:, 1] - y0_, y1_ - Q[:, 1], Q[:, 2] - z0_, z1_ - Q[:, 2]])
    lb_line = np.maximum(lb_line, push_ * np.clip(inside_ / ramp_, 0, 1))
    print('chin: %d vertices with their outline %.0f mm back' % (int((inside_ > 0).sum()), 1000 * push_))
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
    # the sides and the back of the head drawn clean (tools/ren_hair.py): the hair in its tones, the thin locks Meshy
    # painted in skin in the hair's, the scalp between the locks in its dark, the skin flat with crisp marks; not the face
    from ren_hair import head_sides, fill_holes
    side_skin = head_sides(t, Q, Nq, UVq, Ik)
    # (and as Denis's detail sheet has them, tools/ren_side.py: the ears seen, the hair around them, the temples, the neck
    # and the cheeks clean)
    from ren_side import sides as sheet_sides
    side_out, side_px, side_painted = sheet_sides(Q, Nq, UVq, Ik, lb_line, t, side_skin)
    print('sides: around the ears, the temples, the neck and the cheeks: Meshy\'s locks cleaned, the flaps pressed onto the head (points moved per side %s); %d texels painted' % (side_out, side_px))
    # the collar joined to the vest (tools/ren_collar.py): a skirt from the head's bottom edge to the vest, the collar's band
    # on the vest in the vest's paint
    from ren_collar import collar_join, load_body, collar_shell, NECK_AXIS
    NECK_AXIS_X, NECK_AXIS_Z = NECK_AXIS
    # the new collar (ren_collar.collar_shell): made clean around the neck, in place of the bust's (its triangles left out:
    # the neck's bottom edge then joined to the vest by the skirt, a floor inside the collar)
    rest_all = np.zeros(len(Q), bool); rest_all[:len(rest)] = rest
    neck_all = np.zeros(len(Q), bool); neck_all[:len(neck)] = neck
    # the neck's skin (its texels by the floor, in front): the floor's colour there; and its texels that kept the bust's
    # teal (by the collar it lost) in the skin's colour around them
    from paint_views import texel_table
    from paint_meshy import parts, SKIN_, TEAL_, MIXED_, LIGHT_
    nk_t = np.nonzero(neck_all[Ik].sum(1) >= 2)[0]; TSq = t.shape[0]
    ysn, xsn, ksn, _, posn, norn = texel_table(Q, Nq, UVq, Ik[nk_t], TSq); cn = t[ysn, xsn]; kn = parts(cn)
    if os.environ.get('NECK_TEX'): np.savez(os.environ['NECK_TEX'], pos=posn, c=cn, ys=ysn, xs=xsn)
    skin_rgb = np.median(cn[(kn == SKIN_) & (posn[:, 1] < 1.47) & (posn[:, 2] > -.01)], 0) if ((kn == SKIN_) & (posn[:, 1] < 1.47)).sum() > 50 else np.median(cn[kn == SKIN_], 0)
    bad = (kn == TEAL_) | (kn == MIXED_) | (kn == LIGHT_)
    if bad.any() and (kn == SKIN_).any():
        sk_ = np.nonzero(kn == SKIN_)[0]; _, jn = cKDTree(posn[sk_]).query(posn[bad]); t[ysn[bad], xsn[bad]] = cn[sk_[jn]]
    print('neck: %d texels of the bust\'s teal and light in its skin; its skin %s' % (int(bad.sum()), np.round(skin_rgb).astype(int).tolist()))
    # the neck's marks clean (9/11/2026, Denis on a close-up of the neck inside the collar: "sistemi i colori dentro al
    # colletto sul collo"): Meshy's brown marks there (the neck's lines, the trapezius' shadows, the notch) blurry and
    # stair-stepped, with light patches and a grain over the skin. On the neck (the head's triangles within NECK_CLEAN[3] m
    # of its axis, between [4] and [0] m): the skin flat, the marks crisp: their darkness (from the skin's down to [1] of
    # its brightness) averaged on the model (a gaussian of [2] m) and cut at its half, in the sheets' shadow tone
    # (NECK_SHADE of the skin), their darkest cores toward the ink. Not the texels the sides drew nor their hair's (the
    # hair's tips over the neck, tools/ren_side.py; 9/11/2026: taken for marks, they came out brown smudges)
    Cn_ = Q[Ik].mean(1); rn_ = np.hypot(Cn_[:, 0] - NECK_AXIS_X, Cn_[:, 2] - NECK_AXIS_Z)
    tri_c = np.nonzero((rn_ < NECK_CLEAN[3]) & (Cn_[:, 1] < NECK_CLEAN[0]) & (Cn_[:, 1] > NECK_CLEAN[4]))[0]
    ysc, xsc, _, _, posc, _ = texel_table(Q, Nq, UVq, Ik[tri_c], TSq)
    if len(ysc):
        own = side_painted[ysc, xsc]
        ysc, xsc, posc = ysc[~own], xsc[~own], posc[~own]
    if len(ysc):
        c1 = t[ysc, xsc]; Ls = skin_rgb.mean(); dk = np.clip((Ls - c1.mean(1)) / (Ls * (1 - NECK_CLEAN[1])), 0, 1)
        dd, jj = cKDTree(posc).query(posc, k=48, distance_upper_bound=3 * NECK_CLEAN[2]); okk = np.isfinite(dd); jj = np.where(okk, jj, 0)
        gw = np.exp(-.5 * (np.where(okk, dd, 0) / NECK_CLEAN[2]) ** 2) * okk; ds = (gw * dk[jj]).sum(1) / np.maximum(gw.sum(1), 1e-9)
        sm3 = lambda a, b, x: (lambda u: u * u * (3 - 2 * u))(np.clip((x - a) / (b - a), 0, 1))
        am, core = sm3(.42, .52, ds), sm3(.8, .95, ds)
        new = skin_rgb[None, :] * (1 - am[:, None]) + (skin_rgb * NECK_SHADE)[None, :] * am[:, None]
        t[ysc, xsc] = new * (1 - .5 * core[:, None]) + np.array([22., 20, 26])[None, :] * .5 * core[:, None]
        print('neck: %d texels redrawn: flat skin, %d in the marks\' shadow tone, %d toward ink' % (len(ysc), int((am > .5).sum()), int((core > .5).sum())))
    # (and shifted to the body's lit chest's skin down to the floor: ren_collar.SKIN_TO_CHEST)
    from ren_collar import SHELL_FLOOR, SKIN_TO_CHEST
    PB_, IB_, UVB_, JB_, WB_ = load_body(pkg)
    NB_ = FB_ = None
    lp_ = os.path.join(out, name + '_look.json')
    if os.path.exists(lp_):   # (the look's skin of the body, as the viewer has it: tools/ren_look.py; and its light's normals and flat share)
        lj_ = json.load(open(lp_)); lb_ = open(os.path.join(out, name + '_look.bin'), 'rb').read()
        (oj_, nj_), (ow_, nw_) = lj_['skin']
        JB_ = np.frombuffer(lb_, np.uint8, nj_, oj_).reshape(-1, 4).astype(JB_.dtype); WB_ = np.frombuffer(lb_, np.float32, nw_, ow_).reshape(-1, 4).astype(WB_.dtype)
        if 'nor' in lj_: NB_ = np.frombuffer(lb_, np.float32, lj_['nor'][1], lj_['nor'][0]).reshape(-1, 3)
        if 'flat' in lj_: FB_ = np.frombuffer(lb_, np.float32, lj_['flat'][1], lj_['flat'][0])
    pp = os.path.join(out, name + '_painted.jpg'); paint_b = np.asarray(Image.open(pp).convert('RGB')).astype(np.float64) if os.path.exists(pp) else None
    if paint_b is not None:
        PSb = paint_b.shape[0]; cb_ = paint_b[np.clip((UVB_[:, 1] * PSb).astype(int), 0, PSb - 1), np.clip((UVB_[:, 0] * PSb).astype(int), 0, PSb - 1)]
        phb_ = np.degrees(np.arctan2(PB_[:, 0] - NECK_AXIS_X, PB_[:, 2] - NECK_AXIS_Z))
        mc = (PB_[:, 1] > SKIN_TO_CHEST[1]) & (PB_[:, 1] < SHELL_FLOOR) & (np.abs(phb_) < 35) & (parts(cb_) == SKIN_)
        if mc.sum() > 10:
            chest_rgb = np.median(cb_[mc], 0)
            w = np.clip(1 - (posn[:, 1] - SHELL_FLOOR) / SKIN_TO_CHEST[0], 0, 1); w = w * w * (3 - 2 * w)
            t[ysn, xsn] = np.clip(t[ysn, xsn] + w[:, None] * (chest_rgb - skin_rgb), 0, 255)
            print('neck: its skin shifted to the chest\'s %s from %d mm above the floor (%d texels, %d of the chest\'s vertices)' % (
                np.round(chest_rgb).astype(int).tolist(), round(1000 * SKIN_TO_CHEST[0]), int((w > 0).sum()), int(mc.sum())))
            skin_rgb = chest_rgb
    # the new collar's teal: the vest's own paint around it (lit as the body, ren_collar.SHELL_BACK: the same colour as the vest)
    teal_rgb = None
    if paint_b is not None:
        rv_ = np.hypot(PB_[:, 0] - NECK_AXIS_X, PB_[:, 2] - NECK_AXIS_Z); mt = (rv_ < .17) & (PB_[:, 1] > 1.38) & (PB_[:, 1] < 1.47) & (parts(cb_) == TEAL_)
        if mt.sum() > 10: teal_rgb = np.median(cb_[mt], 0); print('collar: the vest\'s teal around it %s (%d vertices)' % (np.round(teal_rgb).astype(int).tolist(), int(mt.sum())))
    SP, SN, SUV_unused, SJ, SW, STri, _, within, _, _ = collar_shell(Q, rest_all, top, tw, UVq, Ik, t.shape[0], (), neck_all, skin_rgb, teal_rgb)
    Cq_ = Q[Ik].mean(1); phq_ = np.degrees(np.arctan2(Cq_[:, 0] - NECK_AXIS_X, Cq_[:, 2] - NECK_AXIS_Z)) % 360
    from ren_collar import SHELL_PHI, SHELL_FLOOR, NECK_KEEP_R
    sides_ = (phq_ > SHELL_PHI + 3) & (phq_ < 360 - SHELL_PHI - 3)   # (in the front's opening only the collar's own: the neck's skin there meets the chest)
    rq_ = np.hypot(Cq_[:, 0] - NECK_AXIS_X, Cq_[:, 2] - NECK_AXIS_Z)
    on_neck = (rq_ < NECK_KEEP_R) & (Cq_[:, 1] > SHELL_FLOOR + .002)   # (the neck's own surface: its drawn lines, dark, were taken for the bust's shirt; left out they were holes)
    if os.environ.get('NECK_DEBUG'): np.save(os.environ['NECK_DEBUG'], np.nonzero(on_neck & (rest_all[Ik].sum(1) >= 1))[0])
    n_old = len(Ik); Ik = Ik[(np.where(sides_, rest_all[Ik].sum(1) < 1, rest_all[Ik].sum(1) < 2) | on_neck) & ~within(Cq_, 0, 0, floor=True)]   # (and the neck under its floor)
    from ren_collar import OLD_WALL, OLD_TOP
    kept_ = np.ones(len(I), bool); kept_[hide.astype(np.int64)] = False; Cb_ = P[I].mean(1); rb_ = np.hypot(Cb_[:, 0] - NECK_AXIS_X, Cb_[:, 2] - NECK_AXIS_Z)
    from ren_collar import OLD_IN
    walls = np.nonzero(kept_ & ~skin_of(col[I].mean(1)) & (((Cb_[:, 1] > OLD_WALL[0]) & within(Cb_, OLD_WALL[1], OLD_WALL[2])) | ((Cb_[:, 1] > OLD_TOP[0]) & (rb_ < OLD_TOP[1]))
                                                          | within(Cb_, OLD_IN[0], OLD_IN[1], floor='above')))[0]
    # (and the vest's lapels' top corners by the collar's front edges, LAPEL_TOPS: |angle from the front| between [0] and
    # [1] degrees, above [2] m, [3] to [4] m from the neck's axis: in guard the shoulders fold them up in front of the collar's
    # front edges, a dark wedge and crossed lines seen from the side; the collar's front edges stand over them)
    phb2_ = np.abs(np.degrees(np.arctan2(Cb_[:, 0] - NECK_AXIS_X, Cb_[:, 2] - NECK_AXIS_Z)))
    lap_ = np.nonzero(kept_ & ~skin_of(col[I].mean(1)) & (phb2_ > LAPEL_TOPS[0]) & (phb2_ < LAPEL_TOPS[1]) & (Cb_[:, 1] > LAPEL_TOPS[2]) & (rb_ > LAPEL_TOPS[3]) & (rb_ < LAPEL_TOPS[4]))[0]
    print('collar: %d of the vest\'s lapels\' top corners hidden' % len(lap_))
    hide = np.unique(np.concatenate([hide, walls, lap_])).astype(np.uint32)
    # (and the lapels' lining, LAPEL_LINING: the body's triangles there also drawn from behind, in their paint: in guard,
    # seen from the side into the vest's opening, their back faces were the outline's black triangles)
    kept2_ = np.ones(len(I), bool); kept2_[hide.astype(np.int64)] = False
    lining = np.nonzero(kept2_ & (phb2_ > LAPEL_LINING[0]) & (phb2_ < LAPEL_LINING[1]) & (Cb_[:, 1] > LAPEL_LINING[2]) & (rb_ < LAPEL_LINING[3]))[0].astype(np.uint32)
    print('collar: %d of the vest\'s lapels\' triangles lined (drawn from behind too)' % len(lining))
    # (and their folded corners, LAPEL_NOLINE (as LAPEL_TOPS), left out of the outline: pushed out past their lining, it drew
    # a black Z over the shirt seen from the side in guard; only pushed back, it slid aside as black dashes beside them)
    noline = lining[(phb2_[lining] > LAPEL_NOLINE[0]) & (phb2_[lining] < LAPEL_NOLINE[1]) & (Cb_[lining, 1] > LAPEL_NOLINE[2]) & (rb_[lining] > LAPEL_NOLINE[3]) & (rb_[lining] < LAPEL_NOLINE[4])].astype(np.uint32)
    print('collar: %d triangles of the lapels\' folded corners left out of the outline' % len(noline))
    print('collar: the bust\'s left out (%d triangles); a new one of %d triangles made around the neck; %d of the body\'s old collar walls hidden in it' % (n_old - len(Ik), len(STri), len(walls)))
    keep_b = np.ones(len(IB_), bool); keep_b[hide.astype(np.int64)] = False
    Q, Nq, UVq, Ik, top, tw, lb_line, flat_blk = collar_join(Q, Nq, UVq, Ik, top, tw, lb_line, t, PB_, IB_, UVB_, JB_, WB_, keep_b, paint_b, skin_rgb)
    # (and its small holes on the sides and the back closed, ren_hair.fill_holes: flat colours in their own blocks)
    Q, Nq, UVq, Ik, top, tw, lb_line, hole_blk = fill_holes(Q, Nq, UVq, Ik, top, tw, lb_line, t, [b_[:3] for b_ in flat_blk], side_skin)
    flat_blk = flat_blk + hole_blk
    # (and the body's holes, BODY_HOLES, left by hiding the old tails: a slit on the vest's front right and one on its left,
    # where the tails' roots were, and one on the right thigh; from behind in guard the vest's and the leg's insides showed
    # through them, a dark streak and a black triangle, 9/11 Denis: closed by the head's triangles. Those under the band,
    # under the ribbons' tops, left as they are)
    Q, Nq, UVq, Ik, top, tw, lb_line, bh_blk, bh_flat = body_holes(Q, Nq, UVq, Ik, top, tw, lb_line, t.shape[0], [b_[:3] for b_ in flat_blk],
                                                                    PB_, IB_, UVB_, JB_, WB_, NB_, FB_, keep_b, paint_b)
    flat_blk = flat_blk + bh_blk
    # (the new collar after the skirt: its flat colours in blocks of the texture outside every piece and the skirt's)
    SP, SN, SUV, SJ, SW, STri, shell_blk, _, SLB, SK = collar_shell(Q, np.r_[rest_all, np.zeros(len(Q) - len(rest_all), bool)], top, tw, UVq, Ik, t.shape[0], [b_[:3] for b_ in flat_blk], np.r_[neck_all, np.zeros(len(Q) - len(neck_all), bool)], skin_rgb, teal_rgb,
                                                                     body=(PB_, IB_[keep_b], JB_, WB_))
    n0 = len(Q); Q = np.r_[Q, SP]; Nq = np.r_[Nq, SN]; UVq = np.r_[UVq, SUV]; top = np.r_[top, SJ]; tw = np.r_[tw, SW]
    lb_line = np.r_[lb_line, SLB]; Ik = np.r_[Ik, STri + n0]
    nv = len(Q)
    # the light: flat (its texture's own colour, the sheet's shading) but on the new collar's outside and trim, lit as the
    # body is (ren_look: flat in front, FLAT_BODY by the normal, toon by the sides and the back): one teal with the vest's
    from ren_look import FLAT_BODY
    sm_ = lambda a, b, x: (lambda u: u * u * (3 - 2 * u))(np.clip((x - a) / (b - a), 0, 1))
    flat_v = np.ones(nv); lit = (SK == 0) | (SK == 2)
    flat_v[n0:][lit] = FLAT_BODY * sm_(.1, .45, SN[lit, 2])
    if bh_flat is not None: flat_v[bh_flat[0]:bh_flat[0] + len(bh_flat[1])] = bh_flat[1]   # (the body's holes' fans: lit as the body there)
    print('collar: %d of its vertices lit as the body (%d toon on the sides and the back)' % (int(lit.sum()), int((flat_v[n0:][lit] < .5).sum())))
    head = {'v': 1, 'verts': nv, 'tris': len(Ik), 'scale': round(s, 5), 'pos': put(Q.astype(np.float32)), 'nor': put(Nq.astype(np.float32)), 'uv': put(UVq.astype(np.float32)),
            'jnt': put(top.astype(np.uint8)), 'wgt': put(tw.astype(np.float32)), 'idx': put(Ik.astype(np.uint32 if nv > 65535 else np.uint16)), 'hide': put(hide), 'lining': put(lining), 'noline': put(noline), 'lb': put(lb_line.astype(np.float32)), 'flat': put(flat_v.astype(np.float32))}
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
    from ren_collar import SKIRT_RGB
    for r0, c0, blk, rgb in flat_blk: t[r0 - blk:r0 + blk + 1, c0 - blk:c0 + blk + 1] = rgb   # (the skirt's flat colours: after the padding)
    for r0, c0, blk, rgb in shell_blk: t[r0 - blk:r0 + blk + 1, c0 - blk:c0 + blk + 1] = rgb   # (the new collar's)
    im = Image.fromarray(t.round().astype(np.uint8))
    if max(im.size) > HEAD_TEX: im = im.resize((HEAD_TEX, HEAD_TEX), Image.LANCZOS)
    im.save(os.path.join(out, name + '_head.jpg'), quality=88, optimize=True)
    main_b = np.bincount(top[:, 0], minlength=nb)
    print('head: %d verts, %d tris (of %d; under the cut left out), from y %.3f to %.3f m; the body\'s triangles hidden: %d of %d; main bones %s' % (
        nv, len(Ik), len(Ib), Q[:, 1].min(), Q[:, 1].max(), len(hide), len(I), {bones[i]: int(c) for i, c in enumerate(main_b) if c}))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
