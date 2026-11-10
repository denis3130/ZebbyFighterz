#!/usr/bin/env python3
"""Kael's head: Ren's (10/11/2026, Denis: "prendi solo la testa di ren e mettila a kael poi falla nel suo stile", "non è
il problema il mento ma tutta la faccia"): Ren's new head (viewer_assets/ren/ren_head.*, tools/ren_head.py: Meshy's bust
from Ren's head sheet, approved by Denis) and its face's locks (ren_fringe.*) moved onto Kael's skeleton (the same 24
bones in the same order), coloured as Kael (his head sheet, docs/ref/personaggi/kael_testa_3viste.png).

- What is taken: the head's hair, face, ears, eyes and neck: not Ren's collar, its trim, his shirt and vest (Kael keeps
  his own high collar): the triangles on the Head and the neck bones (their share over KEEP_W) whose paint is not the
  collar's teal, the trim's cream (under TRIM_Y: above it the light texels are the eyes' whites) nor the cloth's dark.
- Where: each vertex from Ren's bind pose to Kael's by its bones (v' = sum w Mk Mr^-1 v: the head on Kael's neck as on
  Ren's), then scaled about Kael's Head bone by SCALE (Kael's head as big as Ren's on his body: 1) and moved by SHIFT.
- Kael's own head hidden (the head's hide): his triangles on the Head bone (their head share over HIDE_W): his face,
  hair, ears, earrings; his collar (half on the Head) stays.
- Colours (Kael's head sheet; the skin as it is: Ren's and Kael's sheets have the same skin): the hair in the sheet's
  two lavender tones (HAIR: light and shadow, the shadow HAIR_SHADOW of it, by the paint's lightness smoothed over
  HAIR_BLUR texels), its black lines black; the irises purple (IRIS: Ren's brown irises, their shading kept along the
  sheet's purples), the eyes' boxes as tools/ren_eyes.py's. The face's locks (the fringe's png) as the hair.
- The head's per-vertex flat light and outline push back (flat, lb) as Ren's; no lining nor noline (Ren's body's).

usage: python3 tools/kael_ren_head.py   (writes wip_assets/kael/kael_head.json, .bin, .jpg and kael_fringe.json, .bin,
.png; Kael's look then needs head:true in CFG.looks.kael)"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paint_views import texel_table

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REN_PKG, REN_HEAD, KAEL_PKG = (os.path.join(ROOT, p) for p in ('assets/ren', 'viewer_assets/ren', 'wip_assets/kael'))
KEEP_W, TRIM_Y, CLOTH_W = .5, 1.555, .5    # the head and the neck's share; the trim's height (m, Ren); the cloth: dark under the head
SCALE, SHIFT = 1., (0., 0., 0.)            # about Kael's Head bone; m, after the eyes' alignment
KAEL_EYES = (.0046, 1.5946)                # m: Kael's own eyes' middle (x, y; tools/kael_face.py MODEL)
HIDE_W = .9                                # Kael's triangles on his Head bone, their share over this: hidden
COLLAR_Y, KAEL_AXIS, OLD_EAR = 1.545, .004, (.045, 1.525)   # but his collar's (under COLLAR_Y, m); not his old earrings
                                           # (|x - his face's middle| over, y over)
HAIR, HAIR_SHADOW, HAIR_BLUR, HAIR_LINE = ((225, 214, 224), (129, 111, 138)), .4, 4., 42   # the sheet's hair; its lines (lightness under)
LINE_PX = 3                                # a dark stroke up to this many texels from its edge: a line (black); deeper in: shadow
IRIS = ((60, 30, 80), (128, 72, 156), (176, 108, 200))   # the sheet's iris: dark ring, mid, light
IRIS_AT, IRIS_R, IRIS_DARK = ((-.023, 1.5916), (.0378, 1.5926)), .0052, 32   # Ren's irises' centres and radius (m); his
                                           # lids' and pupils' black (lightness under) kept
SKIN_SHARE = .45                           # a dark texel with that much skin around it (1.5 cm) is the face's (brows, lashes): not hair
# the earrings (the head sheet's, m): the lobe beyond the face's middle by 'out', its height and depth (Ren's space); the hook
# (above, below the lobe, half width), the bead (its centre under the lobe, radius), the crystal (its top, middle, tip under
# the lobe; its half width, half depth), its sides; the light on its facets; EAR_COLS: light, mid, dark facet, bead, hook,
# sparkle; EAR_LINE: their outline's width (a share of the head's)
EAR = {'out': .06, 'y': (1.55, 1.60), 'z': .0, 'hook': (.001, .013, .0007), 'bead': (.016, .0032), 'gem': (.020, .033, .060, .0080, .0050),
       'sides': 6, 'light': np.array([-.55, .45, .7]) / np.linalg.norm([-.55, .45, .7])}
EAR_COLS = ((196, 140, 226), (150, 72, 196), (84, 36, 124), (124, 58, 168), (214, 214, 226), (252, 250, 255))
EAR_LINE = .3


def bones_world(pkg_json):
    out = []
    for b in pkg_json['bones']:
        x, y, z, w = b['q']
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        L = np.eye(4); L[:3, :3] = R; L[:3, 3] = b['t']
        out.append(L if b['p'] < 0 else out[b['p']] @ L)
    return np.array(out)


def read_head(d, name):
    j = json.load(open(os.path.join(d, name + '.json'))); B = open(os.path.join(d, name + '.bin'), 'rb').read()
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    return j, B, f


def lum_split(img, mask, share, blur):
    """The mask's texels: True where in the lighter (1 - share) of their lightness, smoothed over blur (no grain)."""
    L = img.mean(2); Ls = ndimage.gaussian_filter(np.where(mask, L, 0), blur) / np.maximum(ndimage.gaussian_filter(mask.astype(float), blur), 1e-6)
    lit = mask & (Ls > np.percentile(Ls[mask], 100 * share))
    for tone in (True, False):   # (no small patches of either)
        lab, n = ndimage.label(mask & (lit == tone)); sz = np.bincount(lab.ravel()); small = sz < 60; small[0] = False
        lit[small[lab]] = not tone
    return lit


def recolor_hair(img, mask):
    """img's hair texels (mask) in the sheet's two tones by their lightness, their black lines black, edges soft."""
    L = img.mean(2); dark = mask & (L < HAIR_LINE)
    line = dark & (ndimage.distance_transform_edt(dark) <= LINE_PX)   # (thin: a line; thick: the lock's shadow)
    line = dark & ndimage.binary_dilation(line & ~ndimage.binary_erosion(dark, iterations=LINE_PX), iterations=1)
    body = mask & ~line
    lit = lum_split(img, body, HAIR_SHADOW, HAIR_BLUR)
    w = ndimage.gaussian_filter(lit.astype(float), .7) / np.maximum(ndimage.gaussian_filter(body.astype(float), .7), 1e-6)
    h0, h1 = (np.array(c, float) for c in (HAIR[1], HAIR[0]))
    out = img.copy(); out[body] = h0 + (h1 - h0) * np.clip(w[body], 0, 1)[:, None]
    return out


def earrings(Q, out, ys, xs, posr, tc, Dh, UV, It, TS, hb, shift):
    """The two earrings (EAR: the sheet's, its sizes in m): vertices, normals, uvs (each triangle on one flat colour of a
    patch painted in the texture's free space) per triangle, three each. The lobes: the -x ear's lowest skin texel beyond
    the face (Ren's space, through the Head bone's move), the +x one its mirror image about the face's middle (the irises')."""
    skin = (tc[:, 0] > 140) & (tc[:, 0] - tc[:, 2] > 35)
    ax = (IRIS_AT[0][0] + IRIS_AT[1][0]) / 2
    ear = skin & (posr[:, 0] < ax - EAR['out']) & (posr[:, 1] > EAR['y'][0]) & (posr[:, 1] < EAR['y'][1]) & (np.abs(posr[:, 2] - EAR['z']) < .03)
    if not ear.any(): print('earrings: no ear found'); return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 2)), None
    lr = posr[ear][np.argmin(posr[ear, 1])]
    lobes = [lr, np.array([2 * ax - lr[0], lr[1], lr[2]])]
    lobes = [hb + ((Dh @ np.r_[l, 1.])[:3] - hb) * SCALE + shift for l in lobes]
    # the patch: a free square of the texture (no UV piece within 6 texels), painted in EAR_COLS
    cov = np.zeros((TS, TS), bool); cov[ys, xs] = True; free = ~ndimage.binary_dilation(cov, iterations=6)
    k = 16 * len(EAR_COLS); fr = ndimage.minimum_filter(free.astype(np.uint8), size=k + 8)
    cy, cx = np.argwhere(fr > 0)[0] + (k + 8) // 2 - k // 2
    uvc = []
    for i, c in enumerate(EAR_COLS):
        y0, x0 = cy, cx + 16 * i; out[y0:y0 + 16, x0:x0 + 16] = c; uvc.append(((x0 + 8) / TS, (y0 + 8) / TS))
    tris = []   # (each: 3 points, a colour index)
    for L in lobes:
        h0, h1, hw = L + [0, EAR['hook'][0], 0], L - [0, EAR['hook'][1], 0], EAR['hook'][2]   # the hook: a thin square bar
        box = [h0 + [dx, 0, dz] for dx, dz in ((-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw))] + [h1 + [dx, 0, dz] for dx, dz in ((-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw))]
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
            tris += [((box[a], box[b], box[b + 4]), 4), ((box[a], box[b + 4], box[a + 4]), 4)]
        bc, br = L - [0, EAR['bead'][0], 0], EAR['bead'][1]   # the bead: an octahedron
        oc = [bc + v for v in (np.array([br, 0, 0]), np.array([0, 0, br]), np.array([-br, 0, 0]), np.array([0, 0, -br]))]
        for i in range(4):
            tris += [((bc + [0, br, 0], oc[(i + 1) % 4], oc[i]), 3), ((bc - [0, br, 0], oc[i], oc[(i + 1) % 4]), 3)]
        top, eq, bot = L - [0, EAR['gem'][0], 0], L - [0, EAR['gem'][1], 0], L - [0, EAR['gem'][2], 0]   # the crystal: a bicone
        ring = [eq + [EAR['gem'][3] * np.cos(a), 0, EAR['gem'][4] * np.sin(a)] for a in np.arange(EAR['sides']) * 2 * np.pi / EAR['sides']]
        for i in range(EAR['sides']):
            a, b = ring[i], ring[(i + 1) % EAR['sides']]
            for tri in ((top, b, a), (bot, a, b)):
                n = np.cross(tri[1] - tri[0], tri[2] - tri[0]); n /= np.linalg.norm(n) + 1e-12
                lit = n @ EAR['light']
                ci = 0 if lit > .35 else (1 if lit > -.15 else 2)
                if i == 1 and tri[0] is top: ci = 5   # (the sparkle: a facet in white, as the sheet's)
                tris.append((tri, ci))
    V, Nv, U = [], [], []
    for tri, ci in tris:
        a, b, c = (np.asarray(t, float) for t in tri)
        n = np.cross(b - a, c - a); n /= np.linalg.norm(n) + 1e-12
        V += [a, b, c]; Nv += [n, n, n]; U += [uvc[ci]] * 3
    print('earrings: lobes at %s, %s; %d triangles' % (np.round(lobes[0], 3).tolist(), np.round(lobes[1], 3).tolist(), len(tris)))
    return np.array(V), np.array(Nv), np.array(U), uvc


def main():
    rj = json.load(open(os.path.join(REN_PKG, 'ren.json'))); kj = json.load(open(os.path.join(KAEL_PKG, 'kael.json')))
    assert [b['n'] for b in rj['bones']] == [b['n'] for b in kj['bones']], 'not the same skeleton'
    names = [b['n'] for b in kj['bones']]; Mr, Mk = bones_world(rj), bones_world(kj)
    hj, HB, f = read_head(REN_HEAD, 'ren_head')
    P = f(hj['pos']).reshape(-1, 3).astype(np.float64); N = f(hj['nor']).reshape(-1, 3).astype(np.float64)
    UV = f(hj['uv']).reshape(-1, 2).astype(np.float64); J = f(hj['jnt'], np.uint8).reshape(-1, 4).astype(np.int64)
    W = f(hj['wgt']).reshape(-1, 4).astype(np.float64); I = f(hj['idx'], np.uint16 if hj['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    LBk, FL = f(hj['lb']).astype(np.float64), f(hj['flat']).astype(np.float64)
    T = np.asarray(Image.open(os.path.join(REN_HEAD, 'ren_head.jpg')).convert('RGB')).astype(np.float64); TS = T.shape[0]
    # what is taken: the head and the neck, not the collar, its trim, the cloth
    hn = (W * np.isin(J, [names.index('Head'), names.index('neck')])).sum(1)
    uc = UV[I].mean(1); c = T[np.clip((uc[:, 1] * TS).astype(int), 0, TS - 1), np.clip((uc[:, 0] * TS).astype(int), 0, TS - 1)]
    teal = (c[:, 1] > c[:, 0] + 15) & (c[:, 2] > c[:, 0] + 15)
    trim = (c.min(1) > 150) & (c.max(1) - c.min(1) < 60) & (P[I][:, :, 1].mean(1) < TRIM_Y)
    tri_hn = hn[I].mean(1); keep = (tri_hn > KEEP_W) & ~teal & ~trim
    # (the cloth: the dark under the head's skin on the spine's bones)
    keep &= ~((c.mean(1) < 70) & (tri_hn < CLOTH_W + .3) & (P[I][:, :, 1].mean(1) < 1.47))
    lab = np.zeros(len(I), int)   # (only the head's piece: no stray bits of the collar)
    print('Ren\'s head: %d of %d triangles taken' % (int(keep.sum()), len(I)))
    It = I[keep]; used = np.unique(It); remap = -np.ones(len(P), np.int64); remap[used] = np.arange(len(used))
    It = remap[It]; P, N, UV, J, W, LBk, FL = P[used], N[used], UV[used], J[used], W[used], LBk[used], FL[used]
    # where: Ren's bind pose to Kael's, by the bones
    D = np.einsum('bij,bjk->bik', Mk, np.linalg.inv(Mr))   # per bone: Kael's world from Ren's
    ph = np.hstack([P, np.ones((len(P), 1))])
    Q = np.zeros_like(P); Nn = np.zeros_like(N)
    for k in range(4):
        Dk = D[J[:, k]]; Q += W[:, k:k + 1] * np.einsum('nij,nj->ni', Dk, ph)[:, :3]; Nn += W[:, k:k + 1] * np.einsum('nij,nj->ni', Dk[:, :3, :3], N)
    Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)
    hb = Mk[names.index('Head')][:3, 3]
    # (then the eyes' middle where Kael's own were, his face's middle on his body's: Ren's head bone is 1.6 cm to his other
    # side and his neck shorter; the chin then where kael_nero.png draws it)
    em = np.mean([(D[names.index('Head')] @ np.r_[x, y, .075, 1.])[:3] for x, y in IRIS_AT], 0)
    em = hb + (em - hb) * SCALE; shift = np.array([KAEL_EYES[0] - em[0], KAEL_EYES[1] - em[1], 0.]) + np.array(SHIFT)
    Q = hb + (Q - hb) * SCALE + shift
    print('moved by %s m (the eyes to Kael\'s)' % np.round(shift, 4).tolist())
    print('placed: y %.3f to %.3f, z %.3f to %.3f (Kael\'s Head bone at %s)' % (Q[:, 1].min(), Q[:, 1].max(), Q[:, 2].min(), Q[:, 2].max(), np.round(hb, 3).tolist()))
    # Kael's own head hidden
    K = json.load(open(os.path.join(KAEL_PKG, 'kael.json'))); KB = open(os.path.join(KAEL_PKG, 'kael.bin'), 'rb').read(); me = K['mesh']
    kf = lambda a, dt=np.float32: np.frombuffer(KB, dt, a[1], a[0])
    KI = kf(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    KJ = kf(me['jnt'], np.uint8).reshape(-1, 4); KW = kf(me['wgt']).reshape(-1, 4)
    khw = (KW * (KJ == names.index('Head'))).sum(1)
    hid = khw[KI].mean(1) > HIDE_W
    # (but his collar: its black and purple under COLLAR_Y, its pieces joined to it, not his old earrings beside the jaw)
    KP = kf(me['pos']).reshape(-1, 3).astype(np.float64); KUV = kf(me['uv']).reshape(-1, 2)
    KT = np.asarray(Image.open(os.path.join(KAEL_PKG, 'kael_painted.jpg')).convert('RGB')).astype(np.float64); KTS = KT.shape[0]
    kuc = KUV[KI].mean(1); kc = KT[np.clip((kuc[:, 1] * KTS).astype(int), 0, KTS - 1), np.clip((kuc[:, 0] * KTS).astype(int), 0, KTS - 1)]
    dark = kc.max(1) < 75; purple = (kc[:, 2] > kc[:, 1] + 40) & (kc[:, 2] > 90)
    kcen = KP[KI].mean(1)
    collar = hid & (dark | purple) & (kcen[:, 1] < COLLAR_Y) & ~((np.abs(kcen[:, 0] - KAEL_AXIS) > OLD_EAR[0]) & (kcen[:, 1] > OLD_EAR[1]))
    hide = np.nonzero(hid & ~collar)[0].astype(np.uint32)
    print('Kael\'s head: %d triangles hidden (%d of his collar kept)' % (len(hide), int(collar.sum())))
    # colours: the hair, the irises
    ys, xs, ks, bary, pos, nor = texel_table(Q, Nn, UV, It, TS)
    pos_r = None
    tc = T[ys, xs]; Lt = tc.mean(1)
    skin = (tc[:, 0] > 150) & (tc[:, 0] - tc[:, 2] > 40)
    g = np.floor(pos / .003).astype(np.int64); g -= g.min(0); shp = tuple(g.max(0) + 1)
    Sk = np.zeros(shp, np.float32); Al = np.zeros(shp, np.float32); np.add.at(Sk, tuple(g[skin].T), 1); np.add.at(Al, tuple(g.T), 1)
    Sk = ndimage.uniform_filter(Sk, 5); Al = ndimage.uniform_filter(Al, 5); share = Sk[tuple(g.T)] / np.maximum(Al[tuple(g.T)], 1e-6)
    darkish = (tc.max(1) - tc.min(1) < 60) & (Lt < 140) & ~skin
    hair_t = darkish & (share < SKIN_SHARE)
    HM = np.zeros((TS, TS), bool); HM[ys, xs] = hair_t
    out = recolor_hair(T, HM)
    # the irises: their discs (IRIS_AT, Ren's space; found on a front map of his eyes), not the whites nor the lids' black
    Pr = f(hj['pos']).reshape(-1, 3).astype(np.float64)[used]
    _, _, _, _, posr, _ = texel_table(Pr, N, UV, It, TS)
    iris = np.zeros(len(ys), bool)
    for (cx_, cy_) in IRIS_AT:
        iris |= (np.hypot(posr[:, 0] - cx_, posr[:, 1] - cy_) < IRIS_R) & (posr[:, 2] > .05)
    white = (tc.min(1) > 195) & (tc.max(1) - tc.min(1) < 45)
    iris &= ~white & (Lt > IRIS_DARK)
    if iris.any():
        t = np.clip((Lt[iris] - IRIS_DARK) / (175 - IRIS_DARK), 0, 1)[:, None]
        i0, i1, i2 = (np.array(v, float) for v in IRIS)
        out[ys[iris], xs[iris]] = np.where(t < .5, i0 + (i1 - i0) * (t / .5), i1 + (i2 - i1) * ((t - .5) / .5))
    print('colours: %d hair texels in Kael\'s two lavenders, %d iris texels purple' % (int(HM.sum()), int(iris.sum())))
    cov = np.zeros((TS, TS), bool); cov[ys, xs] = True
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    # the earrings (the sheet's: a silver hook from the lobe, a purple bead, a long purple crystal), on the Head bone
    hi = names.index('Head'); ev, en_, eu, ecol = earrings(Q, out, ys, xs, posr, tc, D[hi], UV, It, TS, hb, shift)
    ne = len(ev)
    if ne:
        Q = np.vstack([Q, ev]); Nn = np.vstack([Nn, en_]); UV = np.vstack([UV, eu])
        J = np.vstack([J, np.tile([hi, 0, 0, 0], (ne, 1))]); W = np.vstack([W, np.tile([1., 0, 0, 0], (ne, 1))])
        LBk = np.r_[LBk, np.zeros(ne)]; FL = np.r_[FL, np.ones(ne)]
        It = np.vstack([It, len(Q) - ne + np.arange(ne).reshape(-1, 3)])
    line = np.r_[np.ones(len(Q) - ne), np.full(ne, EAR_LINE)]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(os.path.join(KAEL_PKG, 'kael_head.jpg'), quality=92, optimize=True)
    # the package (as ren_head's)
    pad = lambda bts: bts + b'\0' * (-len(bts) % 4)
    blob = b''; jo = {'v': 1, 'verts': int(len(Q)), 'tris': int(len(It)), 'scale': hj.get('scale', 1.)}
    def put(key, arr):
        nonlocal blob
        blob = pad(blob); jo[key] = [len(blob), int(arr.size)]; blob += arr.tobytes()
    put('pos', Q.astype(np.float32)); put('nor', Nn.astype(np.float32)); put('uv', UV.astype(np.float32))
    put('jnt', J.astype(np.uint8)); put('wgt', W.astype(np.float32))
    put('idx', It.astype(np.uint16 if len(Q) < 65536 else np.uint32)); put('hide', hide)
    put('lb', LBk.astype(np.float32)); put('flat', FL.astype(np.float32)); put('line', line.astype(np.float32))
    open(os.path.join(KAEL_PKG, 'kael_head.bin'), 'wb').write(pad(blob)); json.dump(jo, open(os.path.join(KAEL_PKG, 'kael_head.json'), 'w'), separators=(',', ':'))
    # the face's locks: moved on the Head bone as the head, coloured as the hair
    fj, FB, ff = read_head(REN_HEAD, 'ren_fringe')
    FP = ff(fj['pos']).reshape(-1, 3).astype(np.float64); hi = names.index('Head')
    FPh = np.hstack([FP, np.ones((len(FP), 1))]); FQ = (D[hi] @ FPh.T).T[:, :3]; FQ = hb + (FQ - hb) * SCALE + shift
    blob = b''; jo = {'v': 1, 'verts': int(len(FQ)), 'tris': fj['tris'] if 'tris' in fj else int(fj['idx'][1] // 3)}
    put('pos', FQ.astype(np.float32)); put('uv', ff(fj['uv']).astype(np.float32))
    put('idx', ff(fj['idx'], np.uint16 if len(FQ) < 65536 else np.uint32).copy())
    open(os.path.join(KAEL_PKG, 'kael_fringe.bin'), 'wb').write(pad(blob)); json.dump(jo, open(os.path.join(KAEL_PKG, 'kael_fringe.json'), 'w'), separators=(',', ':'))
    F = np.asarray(Image.open(os.path.join(REN_HEAD, 'ren_fringe.png')).convert('RGBA')).astype(np.float64)
    fm = F[..., 3] > 127; Fo = F.copy(); Fo[..., :3] = recolor_hair(F[..., :3], fm & ((F[..., :3].max(2) - F[..., :3].min(2)) < 70))
    Image.fromarray(np.clip(Fo, 0, 255).round().astype(np.uint8), 'RGBA').save(os.path.join(KAEL_PKG, 'kael_fringe.png'), optimize=True)
    print('written: kael_head (%d vertices, %d triangles), kael_fringe (%d vertices)' % (len(Q), len(It), len(FQ)))


if __name__ == '__main__':
    main()
