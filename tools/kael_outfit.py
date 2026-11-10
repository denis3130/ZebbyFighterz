#!/usr/bin/env python3
"""Kael's clothes on his own body (10/11/2026; Denis sent the body without hair or clothes, then the sheets of the rest:
docs/ref/personaggi/kael_testa_3viste.png, kael_busto_3viste.png, kael_gambe_3viste.png, kael_retro.png; the whole
front, kael.png, lies exactly on kael_base.png, the drawing Meshy made the body from). The clothes that follow the body
are the body's own surface moved out to the drawing's outline and painted from the sheets: no second layer that a
kick could push the body through. Each garment, in the bind pose (metres; the character's right is -x):

- the top: the torso between the sash's band and the collar, not the arms (sleeveless: BARE_ARM of an arm bone's
  weight and more is bare), TOP_OFF out along the normal and smoothed (TOP_SMOOTH: cloth, not the abs under it);
- the collar: the neck from COLLAR_Y[0] to [1], a cylinder around the neck COLLAR_OFF outside its widest;
- the band: the sash's turns around the waist (BAND_Y), BAND_OFF out from the spine, smoothed;
- the trousers: from the band down to the cuffs (CUFF_Y), out from the legs by the drawing's outline (PANTS: per
  height, the outer, inner and front/back offsets, measured on kael.png), smoothed (no knees, no calves);
- the boots: below the cuffs, BOOT_SHAFT out from the shin, BOOT_STRAP on the strap (STRAP_Y), the foot BOOT_FOOT out
  along the normal (not the sole) and smoothed (no toes), never under the floor;
- the forearm guards: from GUARD_T[0] of the way from the elbow to the wrist, GUARD_OFF out from the forearm, the
  rims (GUARD_RIM) GUARD_RIM_OFF;
- the gloves: the hand (its own bone's weight over GLOVE_W, not the fingers'), GLOVE_OFF out along the normal.
Between garments the surface steps (the cuffs, the collar's top, the band's edges, the guards' rims): each is smoothed
alone, its edge kept. The collar's skin: the neck's and the spine's only (not the head's: it does not turn with him).
MOVE = False since Denis saw it (10/11/2026: "perché l'hai ingrossato così tanto? il modello iniziale la forma andava
benissimo"): the body keeps Meshy's shape and the clothes are its paint only; the garments' shapes above still decide
where each garment is (the paint's materials) and fit the back sheet (its baggy outline).

usage: python3 tools/kael_outfit.py PACKAGE_DIR   (after tools/char_look.py: writes the look's shape into
PACKAGE_DIR/kael_look.json + .bin, and PACKAGE_DIR/kael_painted.jpg)"""
import json, os, sys
import numpy as np
from scipy.sparse import coo_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ren_look import qm, smooth_normals

BAND_Y = (1.12, 1.22)
CUFF_Y = .27
STRAP_Y = (.09, .145)
COLLAR_Y = (1.555, 1.606)
BARE_ARM = .45
TOP_OFF, TOP_SMOOTH = .005, 16
COLLAR_OFF = .008
BAND_OFF, BAND_SMOOTH = .018, 6
# the trousers' outline (kael.png on the model, the right leg: the left one is under the sash's tails): height (m),
# offsets out from the leg (m): outer side, inner side, front and back
PANTS = [(1.12, .022, .012, .018), (.95, .030, .010, .025), (.80, .050, .015, .040), (.70, .055, .018, .045),
         (.60, .055, .028, .045), (.45, .047, .032, .042), (.35, .045, .025, .038), (.29, .035, .018, .030),
         (.27, .020, .010, .016)]
PANTS_SMOOTH = 24
BOOT_SHAFT, BOOT_STRAP, BOOT_FOOT, BOOT_SMOOTH = .012, .020, .010, 12
GUARD_T, GUARD_RIM, GUARD_OFF, GUARD_RIM_OFF = (.32, 1.), ((.32, .40), (.86, .97)), .008, .013
GLOVE_W, GLOVE_OFF = .5, .002
RELABEL_ROUNDS = 3
MOVE = False   # (see above: the body's own shape, the clothes painted on it)
# garment labels (also the paint's materials)
SKIN, TOP, COLLAR, BAND, PANTS_, BOOT, GUARD, GLOVE = range(8)
NAMES = ['skin', 'top', 'collar', 'band', 'trousers', 'boots', 'guards', 'gloves']


def load(pkg):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2).astype(np.float64)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    bones = m['bones']; G = [None] * len(bones)
    for i, b in enumerate(bones):
        Mi = np.eye(4); Mi[:3, :3] = qm(b['q']); Mi[:3, 3] = b['t']; G[i] = Mi if b['p'] < 0 else G[b['p']] @ Mi
    lj = json.load(open(os.path.join(pkg, name + '_look.json'))); LB = open(os.path.join(pkg, name + '_look.bin'), 'rb').read()
    jn = np.frombuffer(LB, np.uint8, lj['skin'][0][1], lj['skin'][0][0]).reshape(-1, 4).astype(np.int64)
    wn = np.frombuffer(LB, np.float32, lj['skin'][1][1], lj['skin'][1][0]).reshape(-1, 4).astype(np.float64)
    return name, m, P, N, UV, I, bones, np.array([g[:3, 3] for g in G]), jn, wn, lj, LB


def weld_graph(P, I):
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    weld = weld.ravel(); nw = len(first); T = weld[I]
    E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr()
    return first, weld, A


def on_polyline(p, pts):
    """Per point of p the nearest point on the polyline pts: (that point, the share along it of its segment, the segment)."""
    best = np.full(len(p), np.inf); out = np.zeros_like(p); tt = np.zeros(len(p)); seg = np.zeros(len(p), int)
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]; d = b - a; t = np.clip(((p - a) @ d) / (d @ d), 0, 1); q = a + t[:, None] * d
        dist = np.linalg.norm(p - q, axis=1); u = dist < best
        best[u] = dist[u]; out[u] = q[u]; tt[u] = t[u]; seg[u] = k
    return out, tt, seg


def smooth_in(X, A, sel, fixed, n, lam=.5, mu=-.53):
    """Taubin smoothing of X (welded, n x k) n rounds over the vertices sel, their neighbours in sel only; fixed stay."""
    S = A.multiply(sel[:, None]).multiply(sel[None, :]).tocsr(); deg = np.asarray(S.sum(1)).ravel()
    move = sel & ~fixed & (deg > 0); X = X.copy()
    for k in range(2 * n):
        avg = (S @ X) / np.maximum(deg, 1)[:, None]; f = lam if k % 2 == 0 else mu
        X[move] = X[move] + f * (avg[move] - X[move])
    return X


def profile(y):
    """The trousers' offsets at height y (outer, inner, front/back), linear between PANTS' rows."""
    ys = np.array([r[0] for r in PANTS])[::-1]; vals = np.array([r[1:] for r in PANTS])[::-1]
    return np.stack([np.interp(y, ys, vals[:, k]) for k in range(3)], 1)


def shape(P, N, I, bones, J, jn, wn, drawn=None):
    """The clothed shape: (new positions, per vertex its garment, the collar's vertices). drawn (welded positions and
    normals -> per vertex +1 drawn skin, -1 drawn cloth, 0 unknown): where skin and cloth meet, as the drawing has it
    (relabel())."""
    idx = {b['n']: i for i, b in enumerate(bones)}; nb = len(bones)
    wsum = lambda names: sum(((jn == idx[n]) * wn).sum(1) for n in names)
    fing = ((jn >= nb) * wn).sum(1)
    armw = wsum(['LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm', 'LeftHand', 'RightHand']) + fing
    first, weld, A = weld_graph(P, I); nw = len(first); Pw = P[first]; Nw = N[first]; y = Pw[:, 1]
    mx = lambda x: (lambda o: (np.maximum.at(o, weld, x), o)[1])(np.zeros(nw))   # (per welded vertex, the most over its copies)
    armw_, fore_, hand_, fing_, head_ = (mx(x) for x in (armw, wsum(['LeftForeArm', 'RightForeArm']), wsum(['LeftHand', 'RightHand']), fing, wsum(['Head'])))
    # --- the directions each garment moves out along ---
    spine = J[[idx['Hips'], idx['Spine02'], idx['Spine01'], idx['Spine'], idx['neck']]]; spine = np.vstack([spine[0] - [0, .3, 0], spine])
    ax, _, _ = on_polyline(Pw, spine); rad = Pw - ax; rad[:, 1] = 0; rhat = rad / np.maximum(np.linalg.norm(rad, axis=1), 1e-9)[:, None]
    nax, _, _ = on_polyline(Pw, J[[idx['neck'], idx['Head']]]); nrad = Pw - nax; nrad[:, 1] = 0; nr = np.linalg.norm(nrad, axis=1)
    nhat = nrad / np.maximum(nr, 1e-9)[:, None]
    legdir = np.zeros((nw, 3)); legmag = np.zeros(nw); shin = np.zeros((nw, 3)); side_of = np.zeros(nw, int)
    for s, sg in (('Left', 1), ('Right', -1)):
        pts = J[[idx[s + 'UpLeg'], idx[s + 'Leg'], idx[s + 'Foot']]]; pts = np.vstack([pts[0] + [0, .25, 0], pts])
        q, t, seg = on_polyline(Pw, pts); r = Pw - q; dd = pts[np.minimum(seg + 1, len(pts) - 1)] - pts[seg]; dd /= np.linalg.norm(dd, axis=1, keepdims=True)
        r = r - (r * dd).sum(1, keepdims=True) * dd; rh = r / np.maximum(np.linalg.norm(r, axis=1), 1e-9)[:, None]
        blend = np.clip((y - .90) / .12, 0, 1)[:, None]   # (above the hip joint the pelvis is one: out from the spine there)
        dirn = rh * (1 - blend) + rhat * blend; dirn /= np.maximum(np.linalg.norm(dirn, axis=1, keepdims=True), 1e-9)
        ox = dirn @ np.array([sg, 0, 0.]); oz = dirn[:, 2]; pr = profile(y)
        on = (Pw[:, 0] * sg) > 0
        legdir[on] = dirn[on]; legmag[on] = (np.where(ox > 0, pr[:, 0], pr[:, 1]) * ox ** 2 + pr[:, 2] * oz ** 2)[on]; shin[on] = rh[on]; side_of[on] = sg
    armdir = np.zeros((nw, 3)); armt = np.zeros(nw)
    for s, sg in (('Left', 1), ('Right', -1)):
        e, w = J[idx[s + 'ForeArm']], J[idx[s + 'Hand']]
        q, t, _ = on_polyline(Pw, np.array([e, w])); r = Pw - q; d = (w - e) / np.linalg.norm(w - e); r -= (r @ d)[:, None] * d
        on = (Pw[:, 0] * sg) > 0; armdir[on] = (r / np.maximum(np.linalg.norm(r, axis=1), 1e-9)[:, None])[on]; armt[on] = t[on]
    # --- the garments ---
    lab = np.full(nw, SKIN)
    torso = (armw_ < BARE_ARM) & (y > BAND_Y[0]) & (y < COLLAR_Y[1]) & (head_ < .5)
    band = torso & (y <= BAND_Y[1]); lab[band] = BAND
    collar = (armw_ < BARE_ARM) & (y >= COLLAR_Y[0]) & (y < COLLAR_Y[1]) & (nr < .075)   # (the head's weight too: the neck under the jaw)
    lab[torso & ~band & ~collar & (y < COLLAR_Y[0] + .01)] = TOP; lab[collar] = COLLAR
    legs = (armw_ < .5) & (y < BAND_Y[0]); lab[legs & (y >= CUFF_Y)] = PANTS_; lab[legs & (y < CUFF_Y)] = BOOT
    arms = armw_ >= .5
    lab[arms & (fore_ >= .3) & (armt >= GUARD_T[0]) & (hand_ < .5) & (fing_ < .3)] = GUARD
    lab[arms & (hand_ >= GLOVE_W) & (fing_ < .5) & (lab != GUARD)] = GLOVE
    if drawn is not None: lab = relabel(lab, drawn(Pw, Nw), A, y, armw_, fore_, hand_, fing_, head_)
    # --- out: each garment along its direction ---
    D = np.zeros((nw, 3)); g = lambda k: lab == k
    D[g(BAND)] = rhat[g(BAND)] * BAND_OFF
    D[g(TOP)] = Nw[g(TOP)] * TOP_OFF
    c = g(COLLAR)
    if c.any():   # (vertical walls: per 15 degrees around the neck, its widest above the collar's middle, and out)
        ang = (np.degrees(np.arctan2(nrad[:, 0], nrad[:, 2])) % 360) / 15; up = c & (y > (COLLAR_Y[0] + COLLAR_Y[1]) / 2)
        R = np.array([nr[up & (np.abs((ang - k + 12) % 24 - 12) <= 1)].max() if (up & (np.abs((ang - k + 12) % 24 - 12) <= 1)).any() else 0 for k in range(24)])
        R = np.where(R > 0, R, R[R > 0].mean()) + COLLAR_OFF
        a0 = np.floor(ang).astype(int) % 24; fr = ang - np.floor(ang); Rv = R[a0] * (1 - fr) + R[(a0 + 1) % 24] * fr
        D[c] = nhat[c] * np.maximum(Rv[c] - nr[c], 0)[:, None]
    D[g(PANTS_)] = legdir[g(PANTS_)] * legmag[g(PANTS_), None]
    b = g(BOOT); foot = b & (y < STRAP_Y[0]); shaft = b & ~foot; strap = shaft & (y <= STRAP_Y[1])
    D[shaft] = shin[shaft] * np.where(strap[shaft], BOOT_STRAP, BOOT_SHAFT)[:, None]
    D[foot] = Nw[foot] * (BOOT_FOOT * (Nw[foot, 1] >= -.4))[:, None]
    rim = np.zeros(nw, bool)
    for a, bb in GUARD_RIM: rim |= (armt >= a) & (armt <= bb)
    gu = g(GUARD); D[gu] = armdir[gu] * np.where(rim[gu], GUARD_RIM_OFF, GUARD_OFF)[:, None]
    D[g(GLOVE)] = Nw[g(GLOVE)] * GLOVE_OFF
    # --- the new surface: each garment smoothed alone, its edges kept ---
    Q = Pw + D; Ac = A.tocoo(); edge = np.zeros(nw, bool); diff = lab[Ac.row] != lab[Ac.col]; edge[Ac.row[diff]] = True
    for k, n in ((TOP, TOP_SMOOTH), (BAND, BAND_SMOOTH), (PANTS_, PANTS_SMOOTH), (BOOT, BOOT_SMOOTH)):
        Q = smooth_in(Q, A, lab == k, edge, n)
    Q[:, 1] = np.maximum(Q[:, 1], np.minimum(Pw[:, 1], 0))   # (never under the floor)
    for k in range(len(NAMES)): print('  %s: %d vertices, moved out %.1f mm at most' % (NAMES[k], (lab == k).sum(), 1000 * np.linalg.norm(Q - Pw, axis=1)[lab == k].max() if (lab == k).any() else 0))
    return Q[weld], lab[weld], (lab == COLLAR)[weld]


def relabel(lab, ds, A, y, armw_, fore_, hand_, fing_, head_):
    """Where skin and cloth meet, as drawn: in each zone where they do (the armholes, the guards' tops, the gloves'
    edges) a vertex drawn skin is skin, one drawn cloth is that zone's garment; then RELABEL_ROUNDS of
    each zone's vertices taking their neighbours' majority (the drawing's lines and purple say neither)."""
    zones = [(TOP, (y > 1.25) & (y < COLLAR_Y[0] + .01) & (armw_ < .95) & (head_ < .5)),
             (GUARD, (fore_ >= .3) & (hand_ < .6) & (fing_ < .3)),
             (GLOVE, (hand_ >= .3) & (fing_ < .7))]   # (not the collar: its top is level, and behind it the drawing has hair)
    lab = lab.copy(); Ac = A.tocoo(); n0 = (lab == SKIN).sum()
    for g, z in zones:
        z = z & np.isin(lab, (SKIN, g))
        lab[z & (ds > 0)] = SKIN; lab[z & (ds < 0)] = g
        for _ in range(RELABEL_ROUNDS):
            on = (lab == g).astype(float); cnt = np.bincount(Ac.row, on[Ac.col], len(lab)) + on; tot = np.bincount(Ac.row, minlength=len(lab)) + 1
            maj = cnt / tot; lab[z & (maj > .5)] = g; lab[z & (maj < .5)] = SKIN
    print('  the drawing\'s skin and cloth: %+d skin vertices' % ((lab == SKIN).sum() - n0))
    return lab


def drawn_split(P_fit, views, forced=()):
    """A function of (welded positions, normals) -> per vertex +1 where the drawing seen from the side it faces most
    (front or back, facing it by .3 and more, and in front there) is skin, -1 cloth (dark), 0 neither (lines, purple,
    background) or not seen; forced: per view, polygons (px) whose vote is cloth (under the shoulder's flap: the top).
    views: [(drawing, u(X), v(X), depth(X), facing(N))]."""
    from PIL import Image, ImageDraw
    def f(Pw, Nw):
        out = np.zeros(len(Pw)); best = np.full(len(Pw), .3)
        for k, (D, u_of, v_of, depth_of, face_of) in enumerate(views):
            H, Wd = D.shape[:2]; fc = face_of(Nw); u = u_of(Pw); v = v_of(Pw); dep = depth_of(Pw)
            fm = Image.new('L', (Wd, H), 0)
            for poly in (forced[k] if k < len(forced) else ()): ImageDraw.Draw(fm).polygon(poly, fill=255)
            fm = np.asarray(fm) > 0
            zimg = np.full((H, Wd), -1e9); ui = np.clip(u.round().astype(int), 0, Wd - 1); vi = np.clip(v.round().astype(int), 0, H - 1)
            np.maximum.at(zimg, (vi, ui), dep)
            from scipy import ndimage
            zimg = ndimage.maximum_filter(zimg, 3)   # (the surface in front, a little wide)
            seen = dep > zimg[vi, ui] - .012
            c = D[vi, ui]; r, g_, b = c[:, 0], c[:, 1], c[:, 2]; lum = c.mean(1)
            skin = (r > 140) & (r - b > 45) & (g_ > 80)
            cloth = ~skin & (lum < 120) & (lum > 50) & ~((b > 140) & (b - g_ > 55))
            use = seen & (fc > best); best[use] = fc[use]
            out[use] = np.where(fm[vi, ui][use], -1, np.where(skin[use], 1, np.where(cloth[use], -1, 0)))
        return out
    return f


def collar_skin(jn, wn, collar, bones):
    """The collar's vertices skinned to the neck and the spine only (their head's share moved to the neck)."""
    idx = {b['n']: i for i, b in enumerate(bones)}; jn = jn.copy(); wn = wn.copy()
    for v in np.nonzero(collar)[0]:
        h = jn[v] == idx['Head']
        if not (h & (wn[v] > 0)).any(): continue
        add = wn[v][h].sum(); wn[v][h] = 0; nk = jn[v] == idx['neck']
        if nk.any(): wn[v][np.argmax(nk)] += add
        else: k = int(np.argmin(wn[v])); jn[v][k] = idx['neck']; wn[v][k] = add
    return jn, wn


def save_look(pkg, name, lj, LB, Q, I, P, jn, wn, keep_w):
    """The look with the clothed shape: its normals smoothed on the new surface, the moved vertices (move: idx, pos, nor)
    and the skin."""
    f32 = lambda a: np.frombuffer(LB, np.float32, a[1], a[0])
    line = f32(lj['line']); flat = f32(lj['flat'])
    nsm = smooth_normals(Q, I, keep_w)
    moved = np.nonzero(np.linalg.norm(Q - P, axis=1) > 1e-6)[0].astype(np.uint16)
    blob = line.astype(np.float32).tobytes(); look = dict(lj); look['line'] = [0, int(line.size)]
    pad = lambda b: b + b'\0' * (-len(b) % 4)
    oj = len(blob); blob += jn.astype(np.uint8).tobytes(); blob = pad(blob); ow = len(blob); blob += wn.astype(np.float32).tobytes()
    look['skin'] = [[oj, int(jn.size)], [ow, int(wn.size)]]
    of = len(blob); blob += flat.astype(np.float32).tobytes(); look['flat'] = [of, int(flat.size)]
    on = len(blob); blob += nsm.astype(np.float32).tobytes(); look['nor'] = [on, int(nsm.size)]
    mi = len(blob); blob += moved.tobytes(); blob = pad(blob)
    mp = len(blob); blob += Q[moved].astype(np.float32).tobytes(); mn = len(blob); blob += nsm[moved].astype(np.float32).tobytes()
    if moved.size: look['move'] = {'idx': [mi, int(moved.size)], 'pos': [mp, int(moved.size * 3)], 'nor': [mn, int(moved.size * 3)]}
    open(os.path.join(pkg, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(pkg, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look %d B: %d vertices moved' % (len(blob), moved.size))
    return nsm


# --- the paint: the front and back sheets projected on the clothed shape ---
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'ref', 'personaggi')
FRONT_FACE, BACK_FACE = (.2, .5), (.2, .5)
# what hangs off the body in front of a garment (the sash's tails, the tunic's skirt, the shoulder's flap: pieces of
# their own, docs/meshy/KAEL.md): the drawing there is not that garment's paint. Per view (px of its sheet): the
# trousers only below PANTS_TOP (above it the tunic's skirt and the tails); the other pieces as polygons, each with the
# garments it hides.
PANTS_TOP = {'front': 940, 'back': 985}
HIDDEN = {'front': [([(548, 560), (900, 560), (900, 1012), (548, 1012)], (PANTS_,)),   # the tails, on the left leg
                    ([(254, 287), (300, 272), (379, 248), (445, 240), (445, 300), (387, 292), (325, 310), (300, 296)], (TOP, SKIN, COLLAR))],   # the flap
          'back': [([(372, 590), (425, 600), (335, 800), (272, 985), (222, 985), (252, 850), (325, 680)], (PANTS_,)),   # the tail
                   ([(600, 240), (700, 236), (790, 262), (880, 268), (805, 300), (700, 300), (600, 300)], (TOP, SKIN, COLLAR))]}   # the flap
# each garment's own colour where neither view sees it well (the sides): its well painted texels' median, not the
# drawing's black lines nor its purple
SOLE_Y, SOLE_COL = .024, (112, 76, 140)
BASE_FALLBACK = {TOP: (77, 60, 82), COLLAR: (40, 34, 44), BAND: (150, 90, 185), PANTS_: (77, 60, 82), BOOT: (70, 55, 76),
                 GUARD: (70, 55, 76), GLOVE: (78, 62, 85)}


def paint(pkg, name, P, Q, Nq, UV, I, lab, headw, armw, debug=None):
    """The texture: kael.png from the front (on the frame of kael_base.png, the drawing the body came from) and
    kael_retro.png from behind, projected on the clothed shape: each texel the views that see it, by how much it faces
    them; not the head (Meshy's face, the hair to come), not what hangs in front of a garment (HIDDEN). Where the views
    see a clothed texel little or not at all (its sides), its garment's own colour (BASE); a skin texel, Meshy's skin.
    (The 3/4 panels of the sheets are not used: drawn differently from any turn of the front, they did not fit.)"""
    from paint_views import texel_table, seen_ids, sheet, fit_back
    from ren_look import drawing_fit
    from PIL import Image, ImageDraw
    T0 = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(np.float64); TS = T0.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(Q, Nq, UV, I, TS)
    g = lab[I[ks]]; gt = np.where((g == g[:, :1]).all(1), g[:, 0], g[np.arange(len(g)), bary.argmax(1)])   # (each texel's garment)
    hw = (headw[I[ks]] * bary).sum(1)
    sm = lambda x, a, b: (lambda t: t * t * (3 - 2 * t))(np.clip((x - a) / (b - a), 0, 1))
    head = hw > .5
    C = np.zeros((len(ks), 3)); Wt = np.zeros(len(ks))
    def view(vname, D, Dfill, mask, u_of, v_of, depth, w0):
        """The view's colour at each texel and its weight: w0 where the texel is seen (its triangle, or one sharing a
        corner with it, in front at its pixel) and nothing hangs in front of its garment there."""
        H, Wd = mask.shape
        u = u_of(Q); v = v_of(Q); seen = seen_ids(Q, I, np.ones(len(I), bool), u, v, depth(Q), H, Wd)
        pu, pv = u_of(pos), v_of(pos); pui = np.clip(pu.round().astype(int), 0, Wd - 1); pvi = np.clip(pv.round().astype(int), 0, H - 1)
        fid = seen[pvi, pui]; vis = (fid == ks) & (pu >= 0) & (pu < Wd) & (pv >= 0) & (pv < H)
        near = ~vis & (fid >= 0)   # (a neighbour triangle in front: the same surface)
        if near.any():
            share = np.zeros(len(ks), bool); Ik = I[ks[near]]; If = I[fid[near]]
            share[np.nonzero(near)[0]] = (Ik[:, :, None] == If[:, None, :]).any((1, 2)); vis |= share
        off = (gt == PANTS_) & (pvi < PANTS_TOP[vname]); hid = np.zeros((H, Wd), bool)
        for poly, gs in HIDDEN[vname]:
            im = Image.new('L', (Wd, H), 0); ImageDraw.Draw(im).polygon(poly, fill=255); pm = np.asarray(im) > 0; hid |= pm
            off |= pm[pvi, pui] & np.isin(gt, gs)
        if debug:
            sil = seen >= 0; from scipy import ndimage as nd
            o = D.copy(); o[hid] = o[hid] * .5 + np.array([0, 255, 0]) * .5; o[PANTS_TOP[vname]] = (0, 0, 255)
            o[sil & ~nd.binary_erosion(sil, iterations=2)] = (255, 0, 0)
            Image.fromarray(o.astype(np.uint8)).save(os.path.join(debug, vname + '.png'))
        col = Dfill[pvi, pui]; light = (col.mean(1) > 120) & (np.ptp(col, 1) < 40)   # (the drawing's white gaps, its grey halo)
        return col, vis * w0 * ~off * ~light
    _, mb, _ = sheet(os.path.join(REF, 'kael_base.png'), None)
    _, s, cx, by = drawing_fit(P, mb)   # (the body as Meshy made it, on the drawing it made it from)
    D, mask, Dfill = sheet(os.path.join(REF, 'kael.png'), None)
    col, w = view('front', D, Dfill, mask, lambda X: cx + s * X[:, 0], lambda X: by - s * X[:, 1], lambda X: X[:, 2], sm(nor[:, 2], *FRONT_FACE) * ~head)
    C += col * w[:, None]; Wt += w
    print('  front (kael.png, %.0f px/m): %d texels (%d well)' % (s, (w > 0).sum(), (w > .5).sum()))
    D, mask, Dfill = sheet(os.path.join(REF, 'kael_retro.png'), None)
    sc, s2, cx2, by2 = fit_back(Q, mask)
    col, w = view('back', D, Dfill, mask, lambda X: cx2 - s2 * X[:, 0], lambda X: by2 - s2 * X[:, 1], lambda X: -X[:, 2], sm(-nor[:, 2], *BACK_FACE) * ~head)
    C += col * w[:, None]; Wt += w
    print('  back (kael_retro.png, %.1f%% inside, %.0f px/m): %d texels (%d well)' % (100 * sc, s2, (w > 0).sum(), (w > .5).sum()))
    mixed = C / np.maximum(Wt, 1e-9)[:, None]; a = np.clip(Wt, 0, 1)[:, None]
    base = T0[ys, xs].copy()
    for gg, fb in BASE_FALLBACK.items():
        own = (gt == gg) & (Wt > .9); c = mixed[own]
        c = c[(c.mean(1) > 50) & ~((c[:, 2] > 140) & (c[:, 2] - c[:, 1] > 55))] if gg != BAND else c
        bc = np.median(c, 0) if len(c) > 200 else np.array(fb, float)
        base[gt == gg] = bc
        print('  %s: its own colour %s; %d texels the views see little or not at all' % (NAMES[gg], bc.round().astype(int).tolist(), ((gt == gg) & (Wt < .5)).sum()))
    sole = (gt == BOOT) & (pos[:, 1] < SOLE_Y)   # (the soles in the drawing's purple, all around)
    mixed[sole] = SOLE_COL; a[sole] = 1
    out = T0.copy(); out[ys, xs] = mixed * a + base * (1 - a)
    # between the UV pieces (filtered, mipmapped) the nearest piece's colour, not Meshy's skin there
    from scipy import ndimage
    cov = np.zeros((TS, TS), bool); cov[ys, xs] = True
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(os.path.join(pkg, name + '_painted.jpg'), quality=88, optimize=True)


def main(pkg):
    from paint_views import sheet, fit_back
    from ren_look import drawing_fit
    name, m, P, N, UV, I, bones, J, jn, wn, lj, LB = load(pkg)
    if 'move' in lj: sys.exit('the look already has a shape: run tools/char_look.py first')
    # the front and back sheets on the model: kael.png as kael_base.png (the body Meshy made from it), kael_retro.png
    # on the clothed shape's silhouette (a first pass without the drawing's skin and cloth)
    _, mb, _ = sheet(os.path.join(REF, 'kael_base.png'), None); _, s, cx, by = drawing_fit(P, mb)
    Q0, _, _ = shape(P, N, I, bones, J, jn, wn)
    Db, mk, _ = sheet(os.path.join(REF, 'kael_retro.png'), None); _, s2, cx2, by2 = fit_back(Q0, mk)
    Df = np.asarray(__import__('PIL.Image', fromlist=['Image']).open(os.path.join(REF, 'kael.png')).convert('RGB')).astype(float)
    views = [(Df, lambda X: cx + s * X[:, 0], lambda X: by - s * X[:, 1], lambda X: X[:, 2], lambda Nn: Nn[:, 2]),
             (Db, lambda X: cx2 - s2 * X[:, 0], lambda X: by2 - s2 * X[:, 1], lambda X: -X[:, 2], lambda Nn: -Nn[:, 2])]
    flap = lambda v: [poly for poly, gs in HIDDEN[v] if TOP in gs]
    Q, lab, collar = shape(P, N, I, bones, J, jn, wn, drawn_split(P, views, (flap('front'), flap('back'))))
    if MOVE: jn2, wn2 = collar_skin(jn, wn, collar, bones)
    else: Q, jn2, wn2 = P.copy(), jn, wn   # (the garments' labels only: the body's own shape and skin)
    nb = len(bones); idx = {b['n']: i for i, b in enumerate(bones)}
    hw = sum(((jn == idx[s_ + 'Hand']) * wn).sum(1) for s_ in ('Left', 'Right')) + ((jn >= nb) * wn).sum(1)
    nsm = save_look(pkg, name, lj, LB, Q, I, P, jn2, wn2, np.clip(hw / .5, 0, 1))
    headw = ((jn == idx['Head']) * wn).sum(1)
    armw = sum(((jn == idx[s_ + b]) * wn).sum(1) for s_ in ('Left', 'Right') for b in ('Arm', 'ForeArm', 'Hand')) + ((jn >= nb) * wn).sum(1)
    dbg = os.environ.get('OUTFIT_DEBUG')
    if dbg: os.makedirs(dbg, exist_ok=True)
    paint(pkg, name, P, Q, nsm.astype(np.float64), UV, I, lab, headw, armw, dbg)


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
