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
(dark, not the shirt), the face and the ears (skin above HEAD_JAW m) on the Head bone; the neck's skin from the neck
and the spine at its base to the Head at HEAD_JAW; the collar, its trim and the shirt as the body's nearest vertex that
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
         'testa_v2_15k': {'eye': .208, 'chin': -.125, 'neck': (-.26, -.16), 'cut': -.45, 'palette': [
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
    head = (dark & ~shirt) | (skin & (Q[:, 1] >= HEAD_JAW))
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
    im = Image.fromarray(np.clip(flat.reshape(t.shape), 0, 255).round().astype(np.uint8))
    im.save(os.path.join(out, name + '_head.jpg'), quality=88, optimize=True)
    main_b = np.bincount(top[:, 0], minlength=nb)
    print('head: %d verts, %d tris (of %d; under the cut left out), from y %.3f to %.3f m; the body\'s triangles hidden: %d of %d; main bones %s' % (
        nv, len(Iq), len(Ib), Q[:, 1].min(), Q[:, 1].max(), len(hide), len(I), {bones[i]: int(c) for i, c in enumerate(main_b) if c}))


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5): sys.exit(__doc__)
    main(*sys.argv[1:])
