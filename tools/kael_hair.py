#!/usr/bin/env python3
"""Kael's hair and earrings, made in code (10/11/2026, from Denis's sheets: kael.png, kael_retro.png and
kael_testa_3viste.png): white, wild, in pointed locks with black outlines; purple diamond earrings. A part of the look
(ASSETS 'kael/kael_hair.json|bin|png', e_model mdPartData), all on the Head bone, toon lit in its palette's colours.

- The cap: the scalp above the hairline (HAIRLINE: per direction around the head, the height it starts at) moved out
  CAP_OFF along its normal: no bald scalp between the locks.
- The locks (LOCKS, around the head's centre C: azimuth 0 in front, +90 his left; elevation; m): each a lens-shaped
  blade along a cubic curve from its root on the cap (as a tangent along the scalp toward its tip) to its tip,
  tapering to a point (width W[0] at the root, thickness W[1]). A lock marked 'sil' reaches the drawing's outline seen
  from the front (kael.png's figure along its direction from C, less SIL_IN): the drawn spikes.
- Its colours along each lock: the palette's root lilac to its tip's white (PALETTE); the outline LINE (width and push
  back, m: thinner than the body's, the locks' own edges show over each other).
- The earrings: a long purple octahedron under each earlobe (EARRING).

usage: python3 tools/kael_hair.py PACKAGE_DIR   (writes PACKAGE_DIR/kael_hair.json, .bin, .png)"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kael_outfit import load, REF
from ren_look import drawing_fit
from paint_views import sheet

C = np.array([.006, 1.718, -.007])
CAP_OFF = .010
# the hair's mass: the scalp moved out by this much (m) by elevation (deg), less within MASS_EDGE m (in height) of the
# hairline (to CAP_OFF there), and smoothed round (MASS_SMOOTH rounds)
MASS = [(-20, .030), (10, .062), (40, .060), (70, .036), (90, .028)]
MASS_EDGE, MASS_SMOOTH = .03, 20
# the hairline: (azimuth deg, the height where the hair starts, m): in front at the brows' top (the bangs cover the
# forehead), down to the ears' tops at the sides, behind them lower, to the nape at the back
HAIRLINE = [(0, 1.768), (15, 1.752), (35, 1.738), (60, 1.725), (80, 1.712), (100, 1.705), (125, 1.66), (155, 1.625), (180, 1.62)]
LINE = (.004, .0025)
EDGE_LINE = .07   # the share of a lock's half width, at each edge, drawn black (its own contour, as the drawing's locks)
PALETTE = [(150, 136, 168), (196, 186, 212), (226, 220, 234), (240, 238, 245)]   # root lilac .. tip white
SIL_IN = .004
SEG, SIDES = 12, 6
TAPER_AT = .5   # a lock is its full width this far along, then tapers to its point
# locks: (root azimuth, root elevation, tip azimuth, tip elevation, tip distance from C (m), 'sil' (to the drawing's
# outline) or '+d' (d m off the hair's mass there), half width, half thickness, hug (the share of its way it lies on the
# mass before it stands off), curl (deg: its last third turned up, + , or down, -)). As the drawing has them:
LOCKS = []
def both(*ls):
    for l in ls: LOCKS.extend([l, (-l[0], l[1], -l[2]) + tuple(l[3:])])
# the outline's spikes: one lock each, found on the drawings (spikes(): kael.png from the front, kael_retro.png from
# behind), its root up its way toward the part (front) or the crown (behind)
TIP_DEPTH = {'front': .020, 'back': -.045}   # m from C along z: where a drawn spike's tip is
TIP_ROOT = {'front': (5, 72), 'back': (180, 72)}   # the direction the spikes' locks come from
TIP_ROOT_SHARE, TIP_HUG = .55, .25
SPIKE_WIN, SPIKE_RISE = 6, 4
# layers from the crown down, each lock's tip lifting off over the layer under it (the drawing's many outlined points)
def layer(n, az0, el0, el1, off, w, hug, curl, skip=(), twist=0):
    for k in range(n):
        a = ((az0 + 360. * k / n + 180) % 360) - 180
        if any(lo <= a <= hi for lo, hi in skip): continue
        LOCKS.append((a, el0, a + twist * np.sign(a), el1, off, w, .007, hug, curl))
layer(8, 22, 86, 52, '+.030', .040, .45, 14)
layer(11, 0, 66, 18, '+.034', .040, .50, 10, skip=((-30, 30),), twist=8)
layer(11, 16, 42, -18, '+.030', .036, .55, -6, skip=((-58, 58),), twist=10)
layer(8, 180, 18, -52, '+.020', .032, .60, -10, skip=((-112, 112),))
# the bangs: two curtains from the part (a little to his left) down over the forehead and out to the temples, one long
# lock between the eyes, a shorter one under each curtain (each through a direction at its middle)
for k, (az, el, mid, tip) in enumerate([((10, 64), None, (16, 10), (34, 2)), ((12, 62), None, (24, 8), (48, -2)), ((14, 60), None, (34, 10), (60, 4)),
                                          ((0, 64), None, (-8, 10), (-26, 2)), ((-2, 62), None, (-18, 8), (-40, -2)), ((-4, 60), None, (-28, 10), (-54, 4))]):
    LOCKS.append((az[0], az[1], tip[0], tip[1], '+.010', .022, .006, .62, -12, mid))
LOCKS += [(5, 62, -3, -12, '+.008', .014, .005, .70, -8, (2, 14))]   # (the long one between the eyes)
# beside the face, in front of the ears: down to the cheekbones
both((52, 40, 60, -24, '+.012', .016, .005, .80, -8), (66, 36, 74, -30, '+.012', .015, .005, .82, -8))
EARRING = {'top': .008, 'len': .036, 'wide': .0095, 'col': (140, 80, 200), 'lobes': [(.074, 1.660, -.018), (-.071, 1.672, -.022)]}


def unit(v): return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def spikes(D, fig, c, s, below=.035):
    """The drawing's hair (its lavender white and lilac, with its black lines) above c's height + below m: the tips of
    its outline seen from c (px): (angle from up, clockwise on the image; radius px; width px) at each local maximum
    within SPIKE_WIN degrees standing SPIKE_RISE px above its neighbours."""
    R, G, B = D[..., 0], D[..., 1], D[..., 2]
    light = fig & (D.min(2) > 120) & (B >= R - 12) & (np.ptp(D, 2) < 70)   # (in the figure: not the sheet's grey)
    rows = np.zeros(D.shape[:2], bool); rows[:int(c[1] + below * s)] = True
    hair = ndimage.binary_closing(light & rows, iterations=3)
    lab, n = ndimage.label(hair); hair = lab == (np.argmax(ndimage.sum(hair, lab, range(1, n + 1))) + 1)
    hair = ndimage.binary_dilation(hair, iterations=2)   # (its black outline)
    ys, xs = np.nonzero(hair); ang = (np.degrees(np.arctan2(xs - c[0], -(ys - c[1]))) % 360).astype(int)
    prof = np.zeros(360); np.maximum.at(prof, ang, np.hypot(xs - c[0], ys - c[1]))
    prof = ndimage.uniform_filter1d(prof, 3, mode='wrap'); out = []
    for a in range(360):
        if prof[a] <= 0: continue
        win = prof[[(a + k) % 360 for k in range(-SPIKE_WIN, SPIKE_WIN + 1)]]
        if prof[a] == win.max() and prof[a] - win.min() > SPIKE_RISE:
            w = 1
            while w < 15 and prof[(a - w) % 360] > prof[a] - 12 and prof[(a + w) % 360] > prof[a] - 12: w += 1
            out.append((a, float(prof[a]), float(2 * prof[a] * np.sin(np.radians(w)))))
    return out



def sph(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)])


def scalp_radius(H, d):
    """The scalp's distance from C toward d: the head's vertices within 8 degrees of d, their farthest."""
    v = H - C; r = np.linalg.norm(v, axis=1); c = (v @ d) / r
    near = c > np.cos(np.radians(8))
    return r[near].max() if near.any() else r.max()


def outline_dist(mask, s, cx, by, d):
    """kael.png's figure from C along d seen from the front: how far (m, in that 2D direction) its outline is."""
    u0, v0 = cx + s * C[0], by - s * C[1]; dd = np.array([d[0], -d[1]]); n = np.linalg.norm(dd)
    if n < 1e-6: return None
    dd /= n; H, Wd = mask.shape; last = 0
    for k in range(1, 400):   # (the farthest figure pixel along the ray: past the gaps between the spikes)
        u, v = int(round(u0 + dd[0] * k)), int(round(v0 + dd[1] * k))
        if not (0 <= u < Wd and 0 <= v < H): break
        if mask[v, u]: last = k
        elif k - last > 40: break
    return last / s


def slerp(a, b, t):
    om = np.arccos(np.clip(a @ b, -1, 1))
    if om < 1e-6: return np.tile(a, (len(t), 1))
    return (np.sin((1 - t) * om)[:, None] * a + np.sin(t * om)[:, None] * b) / np.sin(om)


def lock_mesh(H, dr, dt, R1, w, h, hug, curl, dm=None):
    """One lock: its path from the root's direction dr to the tip's dt around C, lying on the hair's mass (H: its
    radius toward a direction) for its first hug of the way, then standing off to R1 at the tip; its last third turned by curl
    degrees (up +); a flat lens tapering to a point. (vertices, triangles outward, each vertex's share along it)"""
    ts = np.linspace(0, 1, SEG + 1)
    if dm is None: dirs = slerp(dr, dt, ts)
    else:   # (through dm at its middle: the bangs down over the forehead, then to the temple)
        dirs = np.vstack([slerp(dr, dm, np.array([t * 2]))[0] if t <= .5 else slerp(dm, dt, np.array([t * 2 - 1]))[0] for t in ts])
    rs = np.array([H(d) for d in dirs]) + h * .6
    off = np.clip((ts - hug) / max(1 - hug, 1e-3), 0, 1); off = off * off * (3 - 2 * off)
    rad = rs + (R1 - rs[-1]) * off
    pts = C + dirs * rad[:, None]
    if curl:   # (the end turned about the axis across its way: its tip up or down)
        k0 = int(SEG * .66); ax = unit(np.cross(pts[-1] - pts[k0], [0, 1, 0]) + 1e-9)
        if np.linalg.norm(np.cross(pts[-1] - pts[k0], [0, 1, 0])) < 1e-6: ax = np.array([1., 0, 0])
        a = np.radians(curl) * np.clip((ts - ts[k0]) / (1 - ts[k0]), 0, 1) ** 1.5
        for k in range(k0 + 1, SEG + 1):
            v = pts[k] - pts[k0]; c, s_ = np.cos(a[k]), np.sin(a[k])
            pts[k] = pts[k0] + v * c + np.cross(ax, v) * s_ + ax * (ax @ v) * (1 - c)
    tan = unit(np.gradient(pts, axis=0))
    ring = np.array([(1, 0), (.5, 1), (-.5, 1), (-1, 0), (-.5, -1), (.5, -1)])
    V = []; along = []; across = []
    for k, t in enumerate(ts[:-1]):
        o = unit(pts[k] - C); o = unit(o - (o @ tan[k]) * tan[k]); b = np.cross(tan[k], o)
        taper = (1 if t < TAPER_AT else (1 - (t - TAPER_AT) / (1 - TAPER_AT)) ** .9) * (.8 + .2 * np.clip(t / .12, 0, 1))   # (full to TAPER_AT, then to its point; a little narrower at the root)
        for a_, c_ in ring: V.append(pts[k] + b * a_ * w * taper + o * c_ * h * taper); across.append(.5 * (1 - abs(a_)))
        along += [t] * SIDES
    V.append(pts[-1]); along.append(1.); across.append(0.)
    T = []
    for k in range(SEG - 1):
        for j in range(SIDES):
            a, b = k * SIDES + j, k * SIDES + (j + 1) % SIDES; c, e = a + SIDES, b + SIDES
            T += [(a, e, b), (a, c, e)]
    tipv = SEG * SIDES; last = (SEG - 1) * SIDES
    for j in range(SIDES): T.append((last + j, tipv, last + (j + 1) % SIDES))
    for j in range(1, SIDES - 1): T.append((0, j, j + 1))   # (its root's end, inside the cap)
    V = np.array(V); T = np.array(T)
    vol = np.einsum('ij,ij->i', V[T[:, 0]], np.cross(V[T[:, 1]], V[T[:, 2]])).sum()
    if vol < 0: T = T[:, ::-1]   # (outward: the outline's shell goes out)
    return V, T, np.array(along), np.array(across)


def vertex_normals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]); n = np.zeros_like(V)
    for k in range(3): np.add.at(n, T[:, k], fn)
    return unit(n)


def main(pkg):
    name, m, P, N, UV, I, bones, J, jn, wn, lj, LB = load(pkg)
    idx = {b['n']: i for i, b in enumerate(bones)}; hw = ((jn == idx['Head']) * wn).sum(1)
    H = P[hw > .5]
    _, mb, _ = sheet(os.path.join(REF, 'kael_base.png'), None); _, s, cx, by = drawing_fit(P, mb)
    _, mask, _ = sheet(os.path.join(REF, 'kael.png'), None)
    Vs, Ts, Cs, Xs = [], [], [], []; nv = 0
    # --- the cap: the scalp above the hairline, out along its normal ---
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    az = np.degrees(np.arctan2(P[:, 0] - C[0], P[:, 2] - C[2])); hl = np.interp(np.abs(az), [a for a, _ in HAIRLINE], [y for _, y in HAIRLINE])
    on = (hw > .5) & (P[:, 1] >= hl)
    tri = np.nonzero(on[I].all(1))[0]
    nsum = np.zeros((len(first), 3)); fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    for k in range(3): np.add.at(nsum, weld[I[:, k]], fn)
    nw = unit(nsum)
    used = np.unique(I[tri]); remap = -np.ones(len(P), int); remap[used] = np.arange(len(used))
    pc = P[used]; el = np.degrees(np.arcsin(np.clip((pc[:, 1] - C[1]) / np.linalg.norm(pc - C, axis=1), -1, 1)))
    edge = np.clip((pc[:, 1] - hl[used]) / MASS_EDGE, 0, 1); edge = edge * edge * (3 - 2 * edge)
    off = CAP_OFF + (np.interp(el, [e for e, _ in MASS], [o for _, o in MASS]) - CAP_OFF) * edge
    capV = pc + nw[weld[used]] * off[:, None]
    # smoothed round (welded across the texture's seams; its border kept)
    cw = weld[used]; uw, cinv = np.unique(cw, return_inverse=True); Xw = np.zeros((len(uw), 3)); np.add.at(Xw, cinv, capV); Xw /= np.bincount(cinv)[:, None]
    Tw = cinv[remap[I[tri]]]; E = np.unique(np.sort(np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]), 1), axis=0)
    from collections import Counter
    ecount = Counter(map(tuple, np.sort(np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]), 1)))
    border = np.zeros(len(uw), bool)
    for (a_, b_), c in ecount.items():
        if c == 1: border[a_] = border[b_] = True
    from scipy.sparse import coo_matrix
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(len(uw), len(uw))).tocsr(); deg = np.asarray(A.sum(1)).ravel()
    for k in range(2 * MASS_SMOOTH):
        f = .5 if k % 2 == 0 else -.53; avg = (A @ Xw) / np.maximum(deg, 1)[:, None]; Xw[~border] += f * (avg[~border] - Xw[~border])
    capV = Xw[cinv]
    Vs.append(capV); Ts.append(remap[I[tri]]); Cs.append(np.full(len(used), .35)); Xs.append(np.full(len(used), .4)); nv += len(used)
    print('mass: %d vertices, %d triangles, out %.0f to %.0f mm' % (len(used), len(tri), 1000 * off.min(), 1000 * off.max()))
    MV = capV - C; MR = np.linalg.norm(MV, axis=1); MD = MV / MR[:, None]
    def mass_r(d):   # (the mass's radius toward d; below the hairline, the scalp's and CAP_OFF)
        c = MD @ d; near = c > np.cos(np.radians(7))
        return MR[near].max() if near.any() else scalp_radius(H, d) + CAP_OFF
    # --- the locks ---
    # the drawn spikes: front (kael.png on kael_base.png's frame) and back (kael_retro.png on the clothed shape's)
    from paint_views import fit_back
    Db, mk, _ = sheet(os.path.join(REF, 'kael_retro.png'), None)
    mv = lj['move']; Q = P.copy(); Q[np.frombuffer(LB, np.uint16, mv['idx'][1], mv['idx'][0]).astype(int)] = np.frombuffer(LB, np.float32, mv['pos'][1], mv['pos'][0]).reshape(-1, 3)
    _, s2, cx2, by2 = fit_back(Q, mk)
    Df = np.asarray(Image.open(os.path.join(REF, 'kael.png')).convert('RGB')).astype(float)
    locks = list(LOCKS); nsp = 0
    for view, D, fig, ss, cc, flip in (('front', Df, mask, s, (cx + s * C[0], by - s * C[1]), 1), ('back', Db, mk, s2, (cx2 - s2 * C[0], by2 - s2 * C[1]), -1)):
        for a, r, wpx in spikes(D, fig, cc, ss):
            if 120 < a < 240: continue   # (not under the jaw)
            x = flip * np.sin(np.radians(a)) * r / ss; yv = np.cos(np.radians(a)) * r / ss
            tip = C + np.array([x, yv, TIP_DEPTH[view]]); d = tip - C; R1 = np.linalg.norm(d); dt = d / R1
            el1 = np.degrees(np.arcsin(dt[1])); az1 = np.degrees(np.arctan2(dt[0], dt[2]))
            dr = unit(slerp(sph(*TIP_ROOT[view]), dt, np.array([TIP_ROOT_SHARE]))[0])
            az0 = np.degrees(np.arctan2(dr[0], dr[2])); el0 = np.degrees(np.arcsin(dr[1]))
            hw_ = float(np.clip(wpx / ss * .7, .026, .048))
            locks.append((az0, el0, az1, el1, R1, hw_, .007, TIP_HUG, 0)); nsp += 1
    print('spikes from the drawings: %d' % nsp)
    for k, lk in enumerate(locks):
        a0, e0, a1, e1, R1, w, h, hug, curl = lk[:9]; dm = sph(*lk[9]) if len(lk) > 9 else None
        dr, dt = sph(a0, e0), sph(a1, e1)
        if R1 == 'sil':
            R = outline_dist(mask, s, cx, by, dt); proj = np.hypot(dt[0], dt[1])
            R1 = max((R - SIL_IN) / max(proj, .3), mass_r(dt) + .02) if R else .13
        elif isinstance(R1, str): R1 = mass_r(dt) + float(R1[1:])
        V, T, along, across = lock_mesh(mass_r, dr, dt, R1, w, h, hug, curl, dm)
        Vs.append(V); Ts.append(T + nv); Cs.append(.1 + .85 * along); Xs.append(across); nv += len(V)
    print('locks: %d' % len(locks))
    hairV = np.vstack(Vs); hairT = np.vstack(Ts); hairU = np.concatenate(Cs); hairX = np.concatenate(Xs)
    # --- the earrings: long octahedra under the lobes ---
    eV, eT = [], []
    for lobe in EARRING['lobes']:
        c = np.array(lobe) - [0, EARRING['top'] + EARRING['len'] / 2, 0]; L, W = EARRING['len'] / 2, EARRING['wide']
        base = len(hairV) + len(eV)
        eV += [c + [0, L, 0], c - [0, L, 0], c + [W, 0, 0], c + [0, 0, W], c - [W, 0, 0], c - [0, 0, W]]
        for q in range(4):
            a, b = 2 + q, 2 + (q + 1) % 4
            eT += [(base + 0, base + b, base + a), (base + 1, base + a, base + b)]   # (outward)
    allV = np.vstack([hairV, np.array(eV)]); allT = np.vstack([hairT, np.array(eT)])
    U = np.concatenate([hairU, np.full(len(eV), -1.)]); X = np.concatenate([hairX, np.full(len(eV), .4)])
    nor = vertex_normals(allV, allT)
    # palette: columns along a lock (its root's lilac to its tip's white; the last ones the earrings' purple), rows
    # across it (0 its edges, black over EDGE_LINE of its half width, .5 its middle)
    pal = np.array(PALETTE + [EARRING['col']], np.uint8)
    TW, TH = 64, 64; img = np.zeros((TH, TW, 3), np.uint8)
    for x in range(TW - 8):
        f = x / (TW - 9) * (len(PALETTE) - 1); i0 = int(f); fr = f - i0; i1 = min(i0 + 1, len(PALETTE) - 1)
        img[:, x] = np.round(pal[i0] * (1 - fr) + pal[i1] * fr)
    img[:, TW - 8:] = pal[-1]
    img[:max(1, int(round(EDGE_LINE * .25 * TH))), :TW - 8] = (20, 18, 24)   # (across runs 0 at the edge to .25 half way in)
    uvs = np.stack([np.where(U < 0, (TW - 4) / TW, U * (TW - 9) / TW + .5 / TW), X], 1)
    jnt = np.zeros((len(allV), 4), np.uint8); jnt[:, 0] = idx['Head']; wgt = np.zeros((len(allV), 4), np.float32); wgt[:, 0] = 1
    blob = b''; meta = {'verts': int(len(allV)), 'tris': int(len(allT)), 'line': list(LINE)}
    def put(key, arr):
        nonlocal blob
        blob += b'\0' * (-len(blob) % 4); meta[key] = [len(blob), int(arr.size)]; blob += arr.tobytes()
    put('pos', allV.astype(np.float32)); put('nor', nor.astype(np.float32)); put('uv', uvs.astype(np.float32))
    put('jnt', jnt); put('wgt', wgt); put('idx', allT.astype(np.uint16 if len(allV) < 65536 else np.uint32))
    open(os.path.join(pkg, name + '_hair.bin'), 'wb').write(blob)
    json.dump(meta, open(os.path.join(pkg, name + '_hair.json'), 'w'), separators=(',', ':'))
    Image.fromarray(img).save(os.path.join(pkg, name + '_hair.png'))
    print('hair: %d vertices, %d triangles, %d B' % (len(allV), len(allT), len(blob)))


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
