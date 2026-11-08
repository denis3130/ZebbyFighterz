#!/usr/bin/env python3
"""Ren's new head (8/11/2026, Denis with his 3-view sheet docs/ref/personaggi/ren_testa_3viste.png: "fallo IDENTICO da
tripla A"): Meshy's multi-image bust made from that sheet (docs/meshy/REN.md, "Testa nuova") cut above the shoulders,
placed on the body's bind pose, skinned to the body's bones, the old head, neck and collar hidden.

usage: python3 tools/ren_head.py BUST.glb PACKAGE_DIR OUT_DIR [TEXTURE.jpg]
  BUST.glb     the bust, decimated (tools/mesh_prep/decimate_glb.py), with its texture
  PACKAGE_DIR  the body's tools/meshy_pack.py package (the skin weights are taken from it)
  TEXTURE.jpg  the bust's texture painted from the sheet (tools/paint_head.py); without it, Meshy's own
  writes OUT_DIR/<name>_head.json, .bin, .jpg (name = the package's): {v, verts, tris, pos, nor, uv: float32, jnt: uint8 x4,
  wgt: float32 x4, idx: uint16/32, hide: uint32 (the package's triangles it replaces); each [byte offset, count]}

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
HEAD_SMOOTH, HEAD_JAW = 3, 1.515
# Meshy's colours to the sheet's (its texture a little lighter and greyer: pink skin, light shadows): each texel moves by
# the offsets of the palette colours near it (HEAD_SPREAD: how near, rgb), its shades within a colour kept
HEAD_PALETTE = [((68, 55, 70), (75, 64, 73)), ((52, 41, 53), (58, 48, 58)), ((100, 81, 90), (113, 94, 102)),   # hair, its dark, its light
                ((249, 190, 151), (248, 184, 137)), ((184, 140, 113), (162, 107, 78)), ((109, 59, 44), (101, 68, 50)),   # skin, its shadow, the darkest
                ((42, 87, 93), (57, 97, 102)), ((39, 35, 44), (30, 28, 34)), ((239, 219, 204), (206, 190, 162))]   # collar teal, dark cloth, trim
HEAD_SPREAD = 28.
HEAD_TEX = 4096   # the texture's size at most (px)


def circle(x, z):
    """Least-squares circle through the points (x, z): (centre x, centre z, radius)."""
    A = np.stack([x, z, np.ones_like(x)], 1); c = np.linalg.lstsq(A, -(x ** 2 + z ** 2), rcond=None)[0]
    xc, zc = -c[0] / 2, -c[1] / 2
    return xc, zc, float(np.sqrt(xc ** 2 + zc ** 2 - c[2]))


def skin_of(col):
    return (col[:, 0] > 120) & (col[:, 1] > 75) & (col[:, 0] - col[:, 2] > 40)


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
    print('skin: head %d, neck %d, collar and shirt %d vertices' % (head.sum(), neck.sum(), rest.sum()))
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel(); nw = len(first)
    T = weld[Iq]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    from scipy.sparse import csr_matrix
    A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)); deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)
    Ww = np.zeros((nw, nb)); np.add.at(Ww, weld, Wf); Ww /= np.bincount(weld, minlength=nw)[:, None]
    hw_ = np.zeros(nw, bool); hw_[weld[head]] = True
    for _ in range(HEAD_SMOOTH): Ww = np.where(hw_[:, None], Ww, .5 * Ww + .5 * (A @ Ww) / deg[:, None])
    Wv = Ww[weld]; top = np.argsort(-Wv, 1)[:, :4]; tw = np.take_along_axis(Wv, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-12)
    # hidden: the body's triangles all above HIDE_Y
    hide = np.nonzero((P[I, 1] > HIDE_Y).all(1))[0].astype(np.uint32)
    blob = bytearray()
    def put(arr):
        while len(blob) % 4: blob.append(0)
        o = len(blob); blob.extend(np.ascontiguousarray(arr).tobytes()); return [o, int(arr.size)]
    nv = len(Q)
    head = {'v': 1, 'verts': nv, 'tris': len(Iq), 'scale': round(s, 5), 'pos': put(Q.astype(np.float32)), 'nor': put(Nq.astype(np.float32)), 'uv': put(UVq.astype(np.float32)),
            'jnt': put(top.astype(np.uint8)), 'wgt': put(tw.astype(np.float32)), 'idx': put(Iq.astype(np.uint32 if nv > 65535 else np.uint16)), 'hide': put(hide)}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_head.bin'), 'wb').write(bytes(blob))
    json.dump(head, open(os.path.join(out, name + '_head.json'), 'w'), separators=(',', ':'))
    im = Image.open(texture).convert('RGB') if texture else texb
    pal = bp.get('palette', HEAD_PALETTE); t = np.asarray(im).astype(np.float64); src = np.array([a for a, _ in pal], float); dst = np.array([b for _, b in pal], float)
    flat = t.reshape(-1, 3); d2 = ((flat[:, None, :] - src[None]) ** 2).sum(2); w = np.exp(-d2 / (2 * HEAD_SPREAD ** 2)); ws = w.sum(1, keepdims=True)
    flat = flat + (w @ (dst - src)) / np.maximum(ws, 1e-9) * np.clip(ws, 0, 1)   # (far from every palette colour: unchanged)
    t = np.clip(flat.reshape(t.shape), 0, 255)
    # the texels between the UV pieces take their nearest piece's colour (the texture's filtering, at a distance, pulled
    # Meshy's packing colours into the pieces' edges: specks and lines along the seams)
    from PIL import ImageDraw
    from scipy import ndimage
    TS = t.shape[0]; mimg = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(mimg)
    for tri in UVq[Iq] * TS: dr.polygon([tuple(v) for v in tri], fill=255)
    inside = ndimage.binary_dilation(np.asarray(mimg) > 0, iterations=2)
    _, (gy, gx) = ndimage.distance_transform_edt(~inside, return_indices=True); t = t[gy, gx]
    print('texture: %d%% of its texels in the head\'s pieces, the rest padded' % round(100 * inside.mean()))
    im = Image.fromarray(t.round().astype(np.uint8))
    if max(im.size) > HEAD_TEX: im = im.resize((HEAD_TEX, HEAD_TEX), Image.LANCZOS)
    im.save(os.path.join(out, name + '_head.jpg'), quality=88, optimize=True)
    main_b = np.bincount(top[:, 0], minlength=nb)
    print('head: %d verts, %d tris (of %d; under the cut left out), from y %.3f to %.3f m; the body\'s triangles hidden: %d of %d; main bones %s' % (
        nv, len(Iq), len(Ib), Q[:, 1].min(), Q[:, 1].max(), len(hide), len(I), {bones[i]: int(c) for i, c in enumerate(main_b) if c}))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
