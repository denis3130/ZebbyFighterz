#!/usr/bin/env python3
"""Kael's new head (10/11/2026, Denis: "se facessimo kael a pezzi su meshy? cioe prima testa e capelli e poi busto e
braccia ed infine gambe e piedi?"): Meshy's multi-image bust from his four head images (docs/ref/personaggi/
kael_testa_fronte, _profilo_dx, _dietro, _profilo_sx.png; docs/meshy/KAEL.md, "Testa da Meshy"), decimated
(tools/mesh_prep/decimate_glb.py: the face and the collar denser), placed on Kael's bind pose, skinned to his bones,
his own head and his collar's top hidden, coloured as his head images.

- Where (BUST: measured on the bust's front and side views, in its own units; DRAW: kael_nero.png, the full drawing the
  body was made from, through its scan camera docs/meshy/kael_scan.json): its eyes' line and chin on the drawing's (the
  head as big as drawn: its hair's top and width come out as drawn too), its neck's axis on the body's collar's (x, z).
- What is taken: all of it above CUT_Y (its bottom's cap left out). Its collar (the images': high, its purple trim just
  under the chin, open in front) widened to the size of Kael's at each height and side, his own above HIDE_COLLAR hidden
  under it (it rose 2-4 cm over the new jaw, its purple rim across it, and with the old head hidden it was a thin
  broken shell).
- Skin: the Head bone for the face, the hair, the ears and the earrings; the neck and the nape from the collar's top
  shares (COLLAR_TOP) to the Head up to the jaw in front and NAPE_Y behind; the collar as his collar's nearest point at
  its bottom, stiff higher up (COLLAR_STIFF: the shoulders' share to the spine), at its top COLLAR_TOP's shares of the
  Head and the neck, smoothed over its neighbours.
- Kael's own head hidden: his triangles on the Head bone (their share over HIDE_W).
- Colours (his head images'): the hair in their two lavenders (light and shadow, by the paint's lightness, the shadow
  HAIR_SHADOW of it) with its black lines; the skin's main tone and its shadow moved to theirs (SKIN); the light marks
  Meshy left on the face's skin (the nose's sheen) painted as skin. Light: flat (the texture's own colour), the
  collar's as his collar's there; the hair's and the earrings' outline thinner, pushed back behind the face where the
  locks hang over it.

usage: python3 tools/kael_head.py BUST.glb   (writes wip_assets/kael/kael_head.json, .bin, .png and removes the
kael_fringe.* of the earlier proposal, tools/kael_ren_head.py: this head draws its own locks; Kael's look needs head:true
in CFG.looks.kael)"""
import io, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
import glbio
from paint_views import texel_table
from kael_ren_head import lum_split
from cel_light import contact, occlusion

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
KAEL_PKG = os.path.join(ROOT, 'wip_assets/kael')
# the bust (its own units): the eyes' line (y), the chin (y), the neck's axis (x, z: its skin's circle under the jaw),
# the ear lobes (y: the earrings hang under it), the earrings' boxes (x, y, z ranges)
BUST = {'eyes': -.09, 'chin': -.59, 'neck': (.078, -.010), 'lobe': -.25,
        'ears': (((-.37, -.22), (-.58, -.21), (-.12, .22)), ((.36, .51), (-.58, -.21), (-.12, .22)))}
DRAW = {'eyes': 152., 'chin': 220., 's': 831.682, 'by': 1478.11}   # kael_nero.png's rows; its scan camera (px per m, feet)
BODY_NECK = (.0085, -.005)   # m: the body's collar's top ring's centre (x, z; fit over 1.50-1.52 m)
CUT_Y, JAW_Y, NAPE_Y = 1.464, 1.512, 1.545   # m: under CUT_Y the bust is left out (its bottom's cap); above JAW_Y in
                             # front, NAPE_Y behind, all on the Head
HIDE_W = .9                  # Kael's triangles on his Head bone, their share over this: hidden
# the collar (see main): the bust's (its cloth up to COLLAR_GAP m over its trim's top at each side) widened to his
# (within COLLAR_R m of the neck's axis; per COLLAR_DY m and COLLAR_BIN degrees around it; fit up to COLLAR_FIT m),
# COLLAR_OUT m outside it; his own above HIDE_COLLAR m hidden; NECK_Y: the neck's skin turns toward the Head from there
COLLAR_R, COLLAR_BIN, COLLAR_DY, COLLAR_GAP, COLLAR_FIT, COLLAR_OUT, HIDE_COLLAR, NECK_Y = .1, 15, .004, .002, 1.50, .0015, 1.483, 1.50
COLLAR_GROW, COLLAR_RINGS, COLLAR_F = .006, 3, (.8, 1.9)   # (see main: its cloth's neighbours; its widening's range)
COLLAR_STIFF, COLLAR_TOP, COLLAR_SMOOTH = (1.465, 1.495, .9), (1.475, .5), 4   # (see main: its skin)
COLLAR_Y = 1.545             # m: the bust's collar skinned as his collar's nearest point under this (his old rim's too)
HAIR = ((227, 214, 229), (143, 125, 158))   # the images' hair: light, shadow (k-means of their hair's pixels)
HAIR_SHADOW, HAIR_BLUR, HAIR_LINE = .52, 2., 70   # the shadow's share of the texels (.52: about .38 of what shows, as on the images); its smoothing (texels); its lines: darker (kept)
SKIN = [((253, 192, 152), (248, 187, 143)), ((209, 158, 130), (178, 124, 96))]   # Meshy's skin, its shadow -> the images'
SKIN_SPREAD = 30.
# the images' drawn shading (tools/cel_light.py; Denis, 10/11: "rendi il modello 3d identico"; tools/kael_light.py
# measured that no one light gives it: they shade the skin in a thin band under the locks over it, on the nose's side, in
# the ears and under the jaw, the hair under the locks over it and on their undersides): L toward the light (x his
# left, y up, z his front); the skin in shadow under a lock within skin[0] m, more than skin[1] m out of it, in the face's
# own shadow from L under the chin (up to neck m above it: the jaw's on the neck) and turned from L under skin[2]; the
# hair under other locks (hair[0], [1] as the skin's), turned from Lh (a light from above: a front light put the whole
# back of the head in shadow, the images draw it lit from every side) under hair[2], and where Meshy's own is darkest (the share hair[3]); their edges smoothed
# over blur texels (skin, hair). None: the texture's own shading.
PAD_KEEP = 6                       # texels: see the texture's padding in main()
STUMP = (10, .007, (.02, .05), -.015, .02, .04, 6, (.003, .008), .004, .8, .005)   # see cheek_stumps()
SHADE = {'L': (0., .5, .87), 'Lh': (0., 1., .2), 'skin': (.006, .0015, -.15), 'neck': .004, 'hair': (.005, .004, -.2, .13), 'blur': (.8, 2.5)}
# the head painted from Denis's six head images (10/11/2026, Denis: "l'hai migliorato ma troppo poco"): their cameras
# (cams: tools/kael_hair_fit.py, fit on the face's skin), each of the hair's texels from the views that see it and draw
# hair there (see paint(); ink: the images' lines, darker than this); not the face, the earrings and the collar (ours).
# None: the colours above alone
PAINT = {'cams': 'docs/meshy/kael_head_cams.json', 'seen': .002, 'min': .3, 'pow': 16., 'line': 3, 'ink': 90, 'line_min': .4}
# the face (tools/kael_fringe.py): painted from the images, Meshy's locks over it out, the front image's bangs a sheet in
# front of it; FACE_MID: the face's middle (x, m)
PRESS_SIDES = False              # (FACE 'paint': the temples pressed, see tools/kael_fringe.py press; tried: the front image's locks by the eyes went too)
SIDES = True                     # (FACE 'paint': Meshy's locks over the temples hidden when seen from the side, the sides painted from the side images: tools/kael_fringe.py side_hide)
FACE, FACE_MID = 'paint', .0076   # ('sheet': Meshy's locks over the face out, the front image's bangs a sheet; 'paint': Meshy's locks
                                  # over the eyes and the forehead out, the front image's bangs painted on the forehead; 'all': and all of the
                                  # circled area, hair or skin, from the images that see it; 'skin': only the face painted)
HAIR_BACK = .012             # m: with PAINT, the hair's outline this far back (hidden behind the locks near it: Meshy's
                             # tufts' black edges drew a tangle the images do not have; the mane's outer edge keeps it)
SHEEN = 205                  # on the face's skin (its own triangles, under the eyes): texels lighter than this (the skin's 190): Meshy's sheen
# the outline (per vertex: its width's share, aLine; its extra push back, m, aBack): the earrings' thin, the hair's
# HAIR_LINE_W (its many thin locks drew black ribbons at the head's full width); the locks over the face (in front of its
# skin seen from the front, within FRINGE[1] m of it, depth slack FRINGE[2]) pushed back FRINGE[0] m behind it, as Ren's
# (tools/ren_head.py fringe_back): their outline showed as thick black bands over the face; smoothed over FRINGE[3] rounds
EAR_LINE, HAIR_LINE_W = .3, .4
# the earrings (the drawing's, kael_testa_fronte.png): EAR_RINGS rings of the bead and hook around the crystal; its purples
# from the highlight to the darkest (EAR_TONES) by its facets' light from EAR_LIGHT (over EAR_STEPS, dark to light); the
# bead's and the hook's silver, lit and shaded
EAR_RINGS, EAR_LIGHT, EAR_STEPS = 4, (-.35, .6, .7), (-.1, .35, .8)
EAR_HANG = (.1, .02)   # (see main: the earrings' pieces; bust units, .1 = 16 mm)
EAR_AXIS = (.037, .08, .12)   # (see main: the hook's own pieces within [0] of the earring's axis, taken over its top [1], from [2] under its top; bust units)
EAR_APEX = (.015, .009, .003, .004)   # (see main: the crystal's point: within [0] m over the earring's widest, the last height narrower than [2] before it is [3] wide again, the bead; [1] not used)
SHELF_TOP = .0015            # (m: the shelf's dark up to this over the collar's rim)
COLLAR_SHELF = (25, 20, 36)  # (see main: the triangles between the neck and the collar's rim, in the collar's dark lining)
GREY = (16, 80, .03)         # (see main: Meshy's greys on the hair's triangles: channels within [0] of each other, lighter than [1]; as the painted hair within [2] m)
FLAT = True                  # (the texture in the drawings' flat colours at the end, the lines kept over them: tools/kael_flat.py)
HAIR_FILL = (.008, 30)       # (see main: the hair no image paints takes the nearest painted hair's fill, within [0] m; fill: lighter than the ink plus [1])
EAR_TONES = ((232, 164, 245), (156, 75, 198), (107, 50, 143), (76, 36, 109))
EAR_SILVER = ((204, 182, 218), (146, 124, 162))   # (the drawn link and bead: lit, shade; medians over the crystals in the profile images)
FRINGE = (.02, .008, .004, 3, .002)
HEAD_TEX = 2048


def cheek_stumps(Q, I, skin, mid, eye_m, chin_m, T, uv):
    """The stumps of the locks left out on the cheeks (tools/kael_fringe.py face(): its scraps kept as part of the face, the lock's
    root standing up to 4 mm off the cheek, some of its triangles turned inward) and the holes in the skin under them: from his right,
    the stump's sides were back faces, their outline's shell two black specks on the cheek, and the hole showed the inside of the head
    (Denis's screenshot of 11/11). A hole (welded open edges' loop) of at most STUMP[0] edges and STUMP[1] m across, on the cheeks'
    front (|x - middle| in STUMP[2], y under the eyes plus STUMP[3], over the chin plus STUMP[4], z over STUMP[5]) with at least
    STUMP[6] all-skin triangles around it (STUMP[7] m away: the cheek's surface, its normal): within STUMP[8] m of it the triangles
    turned from the cheek by more than acos(STUMP[9]) go, and what they leave open is capped with a fan of new triangles on one texel
    of the cheek's flat skin (uv; T the texture), the outline within STUMP[10] m the cheek's own. Returns (the triangles kept, the
    caps as (rim vertices, centre, normal), the vertices whose outline is reset, the caps' uv) or None."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    _, wv = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel(); P = np.zeros((wv.max() + 1, 3)); P[wv] = Q
    C = Q[I].mean(1); fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); ar = .5 * np.linalg.norm(fn, axis=1); fn /= np.maximum(2 * ar[:, None], 1e-12)
    def loops(T_):
        E = np.sort(np.stack([wv[I[T_][:, [0, 1]]], wv[I[T_][:, [1, 2]]], wv[I[T_][:, [2, 0]]]], 1).reshape(-1, 2), 1)
        u, c = np.unique(E, axis=0, return_counts=True); op = u[c == 1]
        if not len(op): return op, np.zeros(0, np.int64)
        ov = np.unique(op); ix = np.full(wv.max() + 1, -1); ix[ov] = np.arange(len(ov))
        _, lab = connected_components(coo_matrix((np.ones(len(op)), (ix[op[:, 0]], ix[op[:, 1]])), shape=(len(ov), len(ov))), directed=False)
        return op, lab[ix[op[:, 0]]]
    sk = np.nonzero(skin[I].all(1))[0]; op, el = loops(np.arange(len(I))); keep = np.ones(len(I), bool); holes = []
    for l in np.unique(el):
        e = op[el == l]; vs = np.unique(e); c0 = P[vs].mean(0); ext = np.ptp(P[vs], axis=0).max(); dx = abs(c0[0] - mid)
        if not (len(e) <= STUMP[0] and ext <= STUMP[1] and STUMP[2][0] < dx < STUMP[2][1] and c0[1] < eye_m + STUMP[3] and c0[1] > chin_m + STUMP[4] and c0[2] > STUMP[5]): continue
        d = np.linalg.norm(C[sk] - c0, axis=1); ring = sk[(d > STUMP[7][0]) & (d < STUMP[7][1])]
        if len(ring) < STUMP[6]: continue
        nrm = (fn[ring] * ar[ring, None]).sum(0); nrm /= np.linalg.norm(nrm)
        near = np.nonzero(np.linalg.norm(C - c0, axis=1) < STUMP[8])[0]; st = near[fn[near] @ nrm < STUMP[9]]; keep[st] = False; holes.append((c0, nrm))
        print('cheek: a hole of %d edges at %+.1f mm from the middle, %.1f mm under the eyes: %d triangles of a stump round it out (%.1f mm2)' % (
            len(e), 1e3 * (c0[0] - mid), 1e3 * (eye_m - c0[1]), len(st), 1e6 * ar[st].sum()))
    if not holes: return None
    op2, el2 = loops(np.nonzero(keep)[0]); caps = []; reset = np.zeros(len(Q), bool)
    for c0, nrm in holes:
        reset |= np.linalg.norm(Q - c0, axis=1) < STUMP[10]
        for l in np.unique(el2):
            e = op2[el2 == l]; vs = np.unique(e)
            if np.linalg.norm(P[vs].mean(0) - c0) > 2 * STUMP[8] or len(e) > 3 * STUMP[0]: continue
            nb = {}
            for a, b in e: nb.setdefault(a, []).append(b); nb.setdefault(b, []).append(a)
            if any(len(v) != 2 for v in nb.values()): print('cheek: a loop there not simple, left open'); continue
            ring_ = [e[0][0], nb[e[0][0]][0]]
            while True:
                nx = [v for v in nb[ring_[-1]] if v != ring_[-2]][0]
                if nx == ring_[0]: break
                ring_.append(nx)
            caps.append((ring_, P[ring_].mean(0), nrm)); print('cheek: its hole capped, %d edges' % len(e))
    # (the caps' texel: of the flat skin, in the middle of a cheek triangle near the first hole, 5 x 5 texels of skin round it)
    TS = T.shape[0]; skin_c = np.array([247, 188, 146]); c0 = holes[0][0]; uv0 = None
    for t in sk[np.argsort(np.linalg.norm(C[sk] - c0, axis=1))][:400]:
        u_ = uv[I[t]].mean(0); r, c = int(u_[1] * TS), int(u_[0] * TS)
        if 2 <= r < TS - 2 and 2 <= c < TS - 2 and np.abs(T[r - 2:r + 3, c - 2:c + 3] - skin_c).max() <= 2: uv0 = u_; break
    assert uv0 is not None, 'no flat skin texel near the cheek\'s hole'
    return keep, [([np.nonzero(wv == w)[0][np.argmax(skin[wv == w])] for w in r], c, n) for r, c, n in caps], reset, uv0


def face_back(Q, I, skin, hair):
    """Per vertex: the outline's extra push back (m) of the hair over the face (FRINGE), smoothed over its neighbours."""
    t = I[skin[I].all(1)]; g = FRINGE[4]
    lo = Q[skin][:, :2].min(0) - .02; hi = Q[skin][:, :2].max(0) + .02; n = np.ceil((hi - lo) / g).astype(int) + 1
    Z = np.full(n, -np.inf)
    ij = np.floor((Q[:, :2] - lo) / g).astype(int)
    for k in range(3):   # (the skin's points and its triangles' middles: the face's front-most depth per cell)
        pts = Q[t[:, k]] * .5 + Q[t].mean(1) * .5
        c = np.clip(np.floor((pts[:, :2] - lo) / g).astype(int), 0, n - 1); np.maximum.at(Z, (c[:, 0], c[:, 1]), pts[:, 2])
    c = np.clip(ij[skin], 0, n - 1); np.maximum.at(Z, (c[:, 0], c[:, 1]), Q[skin, 2])
    have = np.isfinite(Z); have = ndimage.binary_closing(have, iterations=2) & ndimage.binary_fill_holes(have)
    near = ndimage.binary_dilation(have, iterations=max(1, int(round(FRINGE[1] / g))))
    _, (ix, iy) = ndimage.distance_transform_edt(~np.isfinite(Z), return_indices=True); Zf = ndimage.grey_dilation(Z[ix, iy], size=3)
    inb = (ij >= 0).all(1) & (ij < n).all(1); c = np.clip(ij, 0, n - 1)
    over = hair & inb & near[c[:, 0], c[:, 1]] & (Q[:, 2] > Zf[c[:, 0], c[:, 1]] - FRINGE[2])
    lb = np.where(over, FRINGE[0], 0.)
    _, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); weld = weld.ravel()
    T = weld[I]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    from scipy.sparse import csr_matrix
    nw = weld.max() + 1; A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw))
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1); lw = np.zeros(nw); np.maximum.at(lw, weld, lb)
    for _ in range(FRINGE[3]): lw = np.maximum(lw, .5 * lw + .5 * (A @ lw) / deg)
    return lw[weld], int(over.sum())


def paint(out, Q, I, ys, xs, ks, pos, nor, sel):
    """The texels sel (of the texel table ys, xs, ks, pos, nor) painted from the images (PAINT): each from the views that
    see it (the head's front-most surface there, within PAINT['seen'] m; facing the camera over PAINT['min']; on the
    image's figure, its outer line left out), weighted by how much it faces each (to the power PAINT['pow']: nearly the
    best view alone, no doubled lines). Returns how many and which."""
    from cel_light import view_depth
    cams = json.load(open(os.path.join(ROOT, PAINT['cams'])))
    idx = np.nonzero(sel)[0]; acc = np.zeros((len(idx), 3)); wsum = np.zeros(len(idx))
    from kael_fringe import drawing
    for view, cam in cams.items():
        D, F = drawing(view); H, W = D.shape[:2]   # (the front one with the locks over its left eye cut short: kael_fringe.front_edit)
        F = ndimage.binary_erosion(F, iterations=PAINT['line'])
        Z, proj = view_depth(Q, I, cam, W, H); u, v, dep = proj(pos[idx])
        ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
        th = np.radians(cam['yaw']); facing = nor[idx] @ np.array([np.sin(th), 0, np.cos(th)])
        px = D[vi, ui]; Lp = px.mean(1)
        hair_px = (is_hair(px) | (Lp < PAINT['ink'])) & ~is_skin(px) & ~is_purple(px)   # (the image's hair there, or its lines: not its skin)
        # (nor the line where its hair ends on its skin: the model's tips over the neck are longer than the drawn ones, the drawn
        # tip's outline was stamped across them and the lock went on under it, pale: a lock ending twice)
        near_skin = ndimage.binary_dilation(is_skin(D) & F, iterations=3); hair_px &= ~((Lp < PAINT['ink']) & near_skin[vi, ui])
        hair_px &= ~((Lp < PAINT['ink']) & (facing < PAINT['line_min']))   # (nor a line from an image the texel barely faces: stretched along the lock, it was dashes, comb teeth and hatching)
        vis = (dep >= Z[vi, ui] - PAINT['seen']) & (facing > PAINT['min']) & (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1) & F[vi, ui] & hair_px
        x0, y0 = np.clip(np.floor(u).astype(int), 0, W - 2), np.clip(np.floor(v).astype(int), 0, H - 2); fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        col = (D[y0, x0] * (1 - fx) + D[y0, x0 + 1] * fx) * (1 - fy) + (D[y0 + 1, x0] * (1 - fx) + D[y0 + 1, x0 + 1] * fx) * fy
        w = np.where(vis, np.maximum(facing, 0) ** PAINT['pow'], 0.)
        acc += w[:, None] * col; wsum += w
    ok = wsum > 0
    out[ys[idx[ok]], xs[idx[ok]]] = acc[ok] / wsum[ok, None]
    return int(ok.sum()), idx[ok]


def placement():
    """The bust's placement on the body (body = bust * s + off, m) and the eyes' and the chin's heights there."""
    eye_m, chin_m = (DRAW['by'] - DRAW['eyes']) / DRAW['s'], (DRAW['by'] - DRAW['chin']) / DRAW['s']
    s = (eye_m - chin_m) / (BUST['eyes'] - BUST['chin'])
    off = np.array([BODY_NECK[0] - s * BUST['neck'][0], eye_m - s * BUST['eyes'], BODY_NECK[1] - s * BUST['neck'][1]])
    return s, off, eye_m, chin_m


def is_skin(c):
    return (c[..., 0] - c[..., 2] > 50) & (c[..., 0] > 120)


def is_hair(c):
    L = c.mean(-1); sat = c.max(-1) - c.min(-1)
    return (c[..., 2] >= c[..., 1]) & (c[..., 0] >= c[..., 1] - 5) & (L > 80) & (sat < 50)   # (greyish: the collar's trim is purple, sat 70-95)


def is_purple(c):
    return (c[..., 2] > c[..., 1] + 40) & (c[..., 0] > c[..., 1] + 20)


def is_cloth(c):
    return (c.max(-1) < 90) | is_purple(c)


def collar_top(pts, agg, empty):
    """Per COLLAR_BIN degrees around the neck's axis (BODY_NECK): agg of the points' heights there (empty bins from their
    neighbours, then smoothed: [1, 2, 1])."""
    nbin = 360 // COLLAR_BIN; ph = np.degrees(np.arctan2(pts[:, 0] - BODY_NECK[0], pts[:, 2] - BODY_NECK[1]))
    b = ((ph + 180) // COLLAR_BIN).astype(int) % nbin; v = np.full(nbin, np.nan)
    for k in range(nbin):
        if (b == k).any(): v[k] = agg(pts[b == k, 1])
    if np.isnan(v).all(): return np.full(nbin, empty)
    ok = np.nonzero(~np.isnan(v))[0]; v = np.interp(np.arange(nbin), ok, v[ok], period=nbin)
    return (np.roll(v, 1) + 2 * v + np.roll(v, -1)) / 4


def radius_grid(pts, y0, y1):
    """The points' outer radius around the neck's axis per COLLAR_DY m (from y0 to y1) and COLLAR_BIN degrees (empty
    cells from their neighbours around, then up and down)."""
    nbin = 360 // COLLAR_BIN; ny = int(np.ceil((y1 - y0) / COLLAR_DY))
    r = np.hypot(pts[:, 0] - BODY_NECK[0], pts[:, 2] - BODY_NECK[1]); ph = np.degrees(np.arctan2(pts[:, 0] - BODY_NECK[0], pts[:, 2] - BODY_NECK[1]))
    iy = np.clip(((pts[:, 1] - y0) / COLLAR_DY).astype(int), 0, ny - 1); ib = ((ph + 180) // COLLAR_BIN).astype(int) % nbin
    G = np.full((ny, nbin), np.nan)
    for a, b, v in zip(iy, ib, r):
        if not v <= G[a, b]: G[a, b] = v
    for a in range(ny):
        ok = np.nonzero(~np.isnan(G[a]))[0]
        if len(ok): G[a] = np.interp(np.arange(nbin), ok, G[a, ok], period=nbin)
    for b in range(nbin):
        ok = np.nonzero(~np.isnan(G[:, b]))[0]
        if len(ok): G[:, b] = np.interp(np.arange(ny), ok, G[ok, b])
    G = np.where(np.isnan(G), np.nanmean(G), G)
    return (np.roll(G, 1, 1) + 2 * G + np.roll(G, -1, 1)) / 4


def radius_at(G, y0, y, ph):
    """G (radius_grid) at heights y and angles ph (degrees): bilinear, around the axis periodic."""
    ny, nbin = G.shape; fy = np.clip((np.asarray(y) - y0) / COLLAR_DY - .5, 0, ny - 1); fb = (np.asarray(ph) + 180) / COLLAR_BIN - .5
    a = np.floor(fy).astype(int); a1 = np.minimum(a + 1, ny - 1); ty = fy - a
    b = np.floor(fb).astype(int); tb = fb - b; b0 = b % nbin; b1 = (b + 1) % nbin
    return (G[a, b0] * (1 - tb) + G[a, b1] * tb) * (1 - ty) + (G[a1, b0] * (1 - tb) + G[a1, b1] * tb) * ty


def at_angle(v, ph):
    """v (per bin, collar_top) at the angles ph (degrees), linearly between the bins' middles."""
    nbin = len(v); x = (np.asarray(ph) + 180) / COLLAR_BIN - .5
    return np.interp(x, np.arange(nbin), v, period=nbin)


def main(bust):
    m = glbio.read(bust); Pb, Nb, UVb, Ib = m['pos'], m['nor'], m['uv'], m['idx']
    tex = Image.open(io.BytesIO(m['img'])).convert('RGB')
    if tex.size[0] > HEAD_TEX: tex = tex.resize((HEAD_TEX, HEAD_TEX), Image.LANCZOS)
    T = np.asarray(tex).astype(np.float64); TS = T.shape[0]
    # where: the eyes and the chin on the drawing's, the neck on the body's
    s, off, eye_m, chin_m = placement()
    P = Pb * s + off
    print('placed: %.4f m per unit; eyes at %.4f m, chin %.4f m; from y %.3f to %.3f m' % (s, eye_m, chin_m, P[:, 1].min(), P[:, 1].max()))
    # each vertex's paint
    vc = T[np.clip((UVb[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UVb[:, 0] * TS).astype(int), 0, TS - 1)]
    tc = T[np.clip((UVb[Ib][:, :, 1].mean(1) * TS).astype(int), 0, TS - 1), np.clip((UVb[Ib][:, :, 0].mean(1) * TS).astype(int), 0, TS - 1)]
    C = Pb[Ib].mean(1)
    ear_t = np.zeros(len(Ib), bool)
    for (x0, x1), (y0, y1), (z0, z1) in BUST['ears']:
        ear_t |= (C[:, 0] > x0) & (C[:, 0] < x1) & (C[:, 1] > y0) & (C[:, 1] < y1) & (C[:, 2] > z0) & (C[:, 2] < z1)
    Ct = P[Ib].mean(1)
    # (the bust's collar's top at each side: its trim's highest point, body space; see collar_top)
    ear_vb = np.zeros(len(P), bool); ear_vb[Ib[ear_t].ravel()] = True
    trim = is_purple(vc) & (P[:, 1] < JAW_Y + .02) & ~ear_vb
    top_b = collar_top(P[trim], np.max, P[:, 1].min())
    ph_v = np.degrees(np.arctan2(P[:, 0] - BODY_NECK[0], P[:, 2] - BODY_NECK[1]))
    collar_vb = is_cloth(vc) & ~ear_vb & ((P[:, 1] < JAW_Y) | (P[:, 1] < at_angle(top_b, ph_v) + COLLAR_GAP))
    # (and the cloth next to it, COLLAR_RINGS rings of neighbours, up to COLLAR_GROW m over its top (not by the chin, in
    # front, above the jaw): its trim's upper edge, left at the bust's width, cut dark teeth into the trim)
    _, wb_ = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True); wb_ = wb_.ravel(); TW_ = wb_[Ib]
    grow_ok = is_cloth(vc) & ~ear_vb & (P[:, 1] < at_angle(top_b, ph_v) + COLLAR_GROW) & ((np.abs(ph_v) > 25) | (P[:, 1] < JAW_Y))
    for _ in range(COLLAR_RINGS):
        cw = np.zeros(wb_.max() + 1, bool); cw[wb_[collar_vb]] = True
        nbr = np.zeros_like(cw); nbr[TW_[cw[TW_].any(1)].ravel()] = True
        collar_vb |= grow_ok & nbr[wb_]
    # (the earrings themselves: in their boxes the crystal, purple, and its dark lines, then the bead and the hook under
    # the lobe, EAR_RINGS rings of the non-skin next to them; the boxes' skin and hair stay skin and hair: as earrings
    # they kept Meshy's colours, the hair by the ears whitish)
    jewel = ear_t & (is_purple(tc) | (tc.max(1) < 70)); grow_e = ear_t & ~is_skin(tc) & (C[:, 1] < BUST['lobe'])
    for _ in range(EAR_RINGS):
        cw = np.zeros(wb_.max() + 1, bool); cw[TW_[jewel].ravel()] = True
        jewel |= grow_e & cw[TW_].any(1)
    # (only what hangs from the lobe: the pieces reaching EAR_HANG[0] under it, the crystal's, and of them what is under the
    # lobe plus EAR_HANG[1] (bust units). The ears' own dark lines in the boxes were taken for earrings: painted silver, a
    # lavender patch in the ear, and with their neighbours left out of the painting from the images)
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    jk = np.nonzero(jewel)[0]
    Aj = csr_matrix((np.ones(3 * len(jk)), (np.repeat(np.arange(len(jk)), 3), TW_[jk].ravel())), shape=(len(jk), wb_.max() + 1))
    _, labj = connected_components(Aj @ Aj.T, directed=False); lowj = np.full(labj.max() + 1, np.inf); np.minimum.at(lowj, labj, C[jk, 1])
    hang = (lowj[labj] < BUST['lobe'] - EAR_HANG[0]) & (Pb[Ib[jk], 1].max(1) < BUST['lobe'] + EAR_HANG[1])
    print('earrings: %d triangles (%d more in their boxes were the ears\' lines or loose pieces: left to the head)' % (int(hang.sum()), int((~hang).sum())))
    jewel[:] = False; jewel[jk[hang]] = True
    # (and the hook's own pieces: the triangles not skin's within EAR_AXIS[0] of each earring's axis (its top EAR_AXIS[1]'s), from
    # EAR_AXIS[2] under its top to the lobe: hair's colour, they were left to the head, painted from the images, black too, and one
    # hidden with the locks from the 3/4, coming and going as the camera turned)
    n_hook = 0
    for sgn in (-1, 1):
        sj = jewel & ((C[:, 0] - BUST['neck'][0]) * sgn > 0)
        if not sj.any(): continue
        vj = np.unique(Ib[sj]); ty = Pb[vj, 1].max(); up = vj[Pb[vj, 1] > ty - EAR_AXIS[1]]; ax, az_ = Pb[up, 0].mean(), Pb[up, 2].mean()
        near = ((np.hypot(C[:, 0] - ax, C[:, 2] - az_) < EAR_AXIS[0]) & (C[:, 1] > ty - EAR_AXIS[2]) & (Pb[Ib, 1].max(1) < BUST['lobe'] + EAR_HANG[1])
                & ~is_skin(tc) & ~jewel & ((C[:, 0] - BUST['neck'][0]) * sgn > 0))
        n_hook += int(near.sum()); jewel |= near
    print('earrings: %d more triangles by their hooks\' axes' % n_hook)
    ear_t = jewel
    keep = (P[Ib, 1] > CUT_Y).all(1)
    It = Ib[keep]; used = np.unique(It); remap = -np.ones(len(P), np.int64); remap[used] = np.arange(len(used))
    It = remap[It]; Q, Nq, UV, vc, collar_v = P[used], Nb[used].copy(), UVb[used], vc[used], collar_vb[used]
    ear_v = np.zeros(len(Q), bool); ear_v[It[ear_t[keep]].ravel()] = True
    print('taken: %d of %d triangles (%d under the cut); its collar %d vertices' % (len(It), len(Ib), int((~keep).sum()), int(collar_v.sum())))
    # skin
    K = json.load(open(os.path.join(KAEL_PKG, 'kael.json'))); KB = open(os.path.join(KAEL_PKG, 'kael.bin'), 'rb').read(); me = K['mesh']
    kf = lambda a, dt=np.float32: np.frombuffer(KB, dt, a[1], a[0])
    names = [b['n'] for b in K['bones']]; nb = len(names); hb = names.index('Head')
    KP = kf(me['pos']).reshape(-1, 3).astype(np.float64); KUV = kf(me['uv']).reshape(-1, 2)
    KJ = kf(me['jnt'], np.uint8).reshape(-1, 4).astype(np.int64); KW = kf(me['wgt']).reshape(-1, 4).astype(np.float64)
    KI = kf(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    KT = np.asarray(Image.open(os.path.join(KAEL_PKG, 'kael_painted.jpg')).convert('RGB')).astype(np.float64); KTS = KT.shape[0]
    kvc = KT[np.clip((KUV[:, 1] * KTS).astype(int), 0, KTS - 1), np.clip((KUV[:, 0] * KTS).astype(int), 0, KTS - 1)]
    kr = np.hypot(KP[:, 0] - BODY_NECK[0], KP[:, 2] - BODY_NECK[1])
    khw = (KW * (KJ == hb)).sum(1); hid = khw[KI].mean(1) > HIDE_W
    # the bust's collar on Kael's (as wide as his at each height and side, COLLAR_OUT m outside it): its points pushed
    # out from the neck's axis by his collar's outer radius over the bust's there (both per COLLAR_DY m and COLLAR_BIN
    # degrees; above COLLAR_FIT his as at COLLAR_FIT: higher up his rim was the old head's); his collar above HIDE_COLLAR
    # hidden under it (its top was 2-4 cm over the new jaw, its rim across it, and with the old head hidden a thin
    # broken shell), the bust's own collar (as drawn: its top just under the chin, its purple trim) in its place
    kvis = np.ones(len(KI), bool); kvis[hid] = False; kvv = np.zeros(len(KP), bool); kvv[KI[kvis].ravel()] = True
    kcl = kvv & is_cloth(kvc) & (kr < COLLAR_R) & (KP[:, 1] > CUT_Y - .02) & (KP[:, 1] < COLLAR_FIT + COLLAR_DY)
    R_k = radius_grid(KP[kcl], CUT_Y - .02, COLLAR_FIT + COLLAR_DY)
    R_b = radius_grid(Q[collar_v], CUT_Y - .02, COLLAR_FIT + .03)
    qy = Q[collar_v, 1]; qph = np.degrees(np.arctan2(Q[collar_v, 0] - BODY_NECK[0], Q[collar_v, 2] - BODY_NECK[1]))
    fk = (radius_at(R_k, CUT_Y - .02, np.minimum(qy, COLLAR_FIT), qph) + COLLAR_OUT) / np.maximum(radius_at(R_b, CUT_Y - .02, np.minimum(qy, COLLAR_FIT + .03), qph), 1e-4)
    fk = np.clip(fk, *COLLAR_F)   # (its points deep inside, in front's opening: no further out than the rest)
    cv = np.nonzero(collar_v)[0]; ctr = np.array([BODY_NECK[0], BODY_NECK[1]])
    Q[np.ix_(cv, [0, 2])] = ctr + (Q[np.ix_(cv, [0, 2])] - ctr) * fk[:, None]
    hide_c = np.nonzero(kvis & (KP[KI].mean(1)[:, 1] > HIDE_COLLAR) & (np.hypot(KP[KI].mean(1)[:, 0] - BODY_NECK[0], KP[KI].mean(1)[:, 2] - BODY_NECK[1]) < COLLAR_R + .03))[0]
    print('collar: the bust\'s %d points widened to his collar (x %.2f to %.2f), %d of his triangles above %.3f m hidden under it' % (
        len(cv), fk.min(), fk.max(), len(hide_c), HIDE_COLLAR))
    hair_v = is_hair(vc) & ~is_skin(vc)
    # (the neck, up to the jaw in front and to NAPE_Y behind: there the nape's hair and skin joined the collar's top,
    # and stretched over it when the head tipped back in the high kick)
    sm3 = lambda x: (lambda u: u * u * (3 - 2 * u))(np.clip(x, 0, 1))
    ph_q = np.abs(np.degrees(np.arctan2(Q[:, 0] - BODY_NECK[0], Q[:, 2] - BODY_NECK[1])))
    y_hi = JAW_Y + (NAPE_Y - JAW_Y) * sm3((ph_q - 60) / 90)
    low = (Q[:, 1] < y_hi) & ~collar_v & ~ear_v
    head = ~low & ~collar_v
    Wf = np.zeros((len(Q), nb)); Wf[head, hb] = 1
    neck = np.nonzero(low)[0]
    if len(neck):   # (the neck's skin: as the collar's top (COLLAR_TOP), toward the Head from NECK_Y up to the jaw; on his
        # nearest points it took his old collar's shoulders and stretched over the collar in the high kick)
        t = sm3((Q[neck, 1] - NECK_Y) / (y_hi[neck] - NECK_Y))
        Wf[neck, hb] = COLLAR_TOP[1] + (1 - COLLAR_TOP[1]) * t; Wf[neck, names.index('neck')] = (1 - COLLAR_TOP[1]) * (1 - t)
    if len(cv):   # (the collar: as his collar's nearest point, his old rim's too: it turned with the head as Meshy rigged it)
        reg = np.nonzero(is_cloth(kvc) & (kr < COLLAR_R + .02) & (KP[:, 1] > CUT_Y - .03) & (KP[:, 1] < COLLAR_Y))[0]
        _, near = cKDTree(KP[reg]).query(Q[cv]); near = reg[near]
        Wc = np.zeros((len(cv), nb))
        for k in range(4): np.add.at(Wc, (np.arange(len(cv)), KJ[near, k]), KW[near, k])
        # (stiff: from COLLAR_STIFF[0] m up its shoulders' and arms' share to the spine, up to COLLAR_STIFF[2] at [1]; then
        # toward COLLAR_TOP's shares of the Head and the neck at its top, from COLLAR_TOP[0] m: on his nearest points alone
        # its top edge took the old rim's head share here and the shoulders' there, and tore into teeth in the throw and
        # the high kick)
        sh = [names.index(n) for n in ('LeftShoulder', 'RightShoulder', 'LeftArm', 'RightArm')]; sp, nk = names.index('Spine'), names.index('neck')
        yq = Q[cv, 1]; u = sm3((yq - COLLAR_STIFF[0]) / (COLLAR_STIFF[1] - COLLAR_STIFF[0])) * COLLAR_STIFF[2]
        take = Wc[:, sh] * u[:, None]; Wc[:, sh] -= take; Wc[:, sp] += take.sum(1)
        ytop = at_angle(top_b, np.degrees(np.arctan2(Q[cv, 0] - BODY_NECK[0], Q[cv, 2] - BODY_NECK[1])))
        tt = sm3((yq - COLLAR_TOP[0]) / np.maximum(ytop - COLLAR_TOP[0], 1e-3))
        Wt = np.zeros_like(Wc); Wt[:, hb] = COLLAR_TOP[1]; Wt[:, nk] = 1 - COLLAR_TOP[1]
        Wf[cv] = Wc * (1 - tt[:, None]) + Wt * tt[:, None]
        LJ = json.load(open(os.path.join(KAEL_PKG, 'kael_look.json'))); LBb = open(os.path.join(KAEL_PKG, 'kael_look.bin'), 'rb').read()
        flat_c = np.frombuffer(LBb, np.float32, LJ['flat'][1], LJ['flat'][0])[near] if 'flat' in LJ else np.zeros(len(cv))   # (lit as his collar there)
    # (the copies of a vertex along the texture's seams: one weight)
    _, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_inverse=True); weld = weld.ravel()
    Ww = np.zeros((weld.max() + 1, nb)); np.add.at(Ww, weld, Wf); Ww /= np.bincount(weld)[:, None]
    if len(cv):   # (and the collar's smoothed over its neighbours, COLLAR_SMOOTH rounds: the rest kept)
        from scipy.sparse import csr_matrix
        TW = weld[It]; E = np.unique(np.sort(np.concatenate([TW[:, [0, 1]], TW[:, [1, 2]], TW[:, [2, 0]]]), 1), axis=0); nw = weld.max() + 1
        A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)); deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)
        cw = np.zeros(nw, bool); cw[weld[cv]] = True
        for _ in range(COLLAR_SMOOTH): Ww = np.where(cw[:, None], .5 * Ww + .5 * (A @ Ww) / deg[:, None], Ww)
    Wf = Ww[weld]
    top = np.argsort(-Wf, 1)[:, :4]; tw = np.take_along_axis(Wf, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-12)
    print('skin: %d on the Head (%d earrings), %d of the neck and the nape toward it (%d of them hair), %d of the collar' % (int(head.sum()), int(ear_v.sum()), len(neck), int(hair_v[neck].sum()), len(cv)))
    press_w = None
    if FACE == 'paint' and PRESS_SIDES:   # (the temples and the cheeks pressed onto the skull as the profiles draw them: tools/kael_fringe.py press)
        from kael_fringe import press
        press_w = press(Q, Nq, It, vc, hair_v, json.load(open(os.path.join(ROOT, PAINT['cams']))), FACE_MID, eye_m, chin_m, is_skin, is_hair)
    # Kael's own head hidden, and his collar's top (above)
    hide = np.unique(np.r_[np.nonzero(hid)[0], hide_c]).astype(np.uint32)
    print('Kael\'s head: %d triangles hidden (%d of his old head, %d of his collar\'s top)' % (len(hide), int(hid.sum()), len(hide_c)))
    # colours
    ys, xs, ks, bary, pos, nor = texel_table(Q, Nq, UV, It, TS)
    tcx = T[ys, xs]; out = T.copy()
    # (the skin: its main tone and its shadow to the images', each texel by the offsets of those near it)
    src = np.array([a for a, _ in SKIN], float); dst = np.array([b for _, b in SKIN], float)
    sk = is_skin(tcx); x = tcx[sk]; d2 = ((x[:, None, :] - src[None]) ** 2).sum(2); w = np.exp(-d2 / (2 * SKIN_SPREAD ** 2)); ws = w.sum(1, keepdims=True)
    out[ys[sk], xs[sk]] = np.clip(x + (w @ (dst - src)) / np.maximum(ws, 1e-9) * np.clip(ws, 0, 1), 0, 255)
    # (the face's light marks: as the skin around them)
    face = (pos[:, 2] > BODY_NECK[1] + .06) & (np.abs(pos[:, 0] - BODY_NECK[0]) < .05) & (pos[:, 1] > JAW_Y) & (pos[:, 1] < eye_m - .012)
    skin_tri = is_skin(vc)[It].all(1)   # (on the skin's own triangles: not the locks hanging over it, lavender as the sheen)
    sheen = face & skin_tri[ks] & (tcx.mean(1) > SHEEN)
    if sheen.any() and (face & sk).any():
        fs = np.nonzero(face & sk)[0]; _, j = cKDTree(pos[fs]).query(pos[sheen]); out[ys[sheen], xs[sheen]] = out[ys[fs[j]], xs[fs[j]]]
    # (the hair: two lavenders by its lightness, its thin dark lines black-ish, the eyes' whites not hair)
    eyes_box = (np.abs(pos[:, 0] - BODY_NECK[0]) < .045) & (np.abs(pos[:, 1] - eye_m) < .012) & (pos[:, 2] > BODY_NECK[1] + .05)
    HM = np.zeros((TS, TS), bool); HM[ys, xs] = is_hair(tcx) & ~sk & ~eyes_box & ~ear_v[It[ks]].any(1) & ~collar_v[It[ks]].any(1) & ~sheen
    L = T.mean(2); darkl = np.zeros((TS, TS), bool); darkl[ys, xs] = (L[ys, xs] < HAIR_LINE)
    body = HM & ~darkl
    lit = lum_split(T, body, HAIR_SHADOW, HAIR_BLUR)
    wl = ndimage.gaussian_filter(lit.astype(float), .7) / np.maximum(ndimage.gaussian_filter(body.astype(float), .7), 1e-6)
    h0, h1 = (np.array(c, float) for c in (HAIR[1], HAIR[0]))
    out[body] = h0 + (h1 - h0) * np.clip(wl[body], 0, 1)[:, None]
    print('colours: %d skin texels to the images\' tones, %d of the face\'s sheen as skin, %d hair texels in two lavenders (%d lit)' % (
        int(sk.sum()), int(sheen.sum()), int(body.sum()), int((lit & body).sum())))
    if SHADE:   # the images' drawn shading (tools/cel_light.py), see SHADE
        def smooth(sel, idx, sigma):   # (a mask over the texels idx, smoothed in the texture: no stairs at its edges)
            Sm = np.zeros((TS, TS)); Mm = np.zeros((TS, TS)); Sm[ys[idx], xs[idx]] = sel; Mm[ys[idx], xs[idx]] = 1
            return (ndimage.gaussian_filter(Sm, sigma) / np.maximum(ndimage.gaussian_filter(Mm, sigma), 1e-6))[ys[idx], xs[idx]] > .5
        Lv = np.array(SHADE['L'], float); Lv /= np.linalg.norm(Lv)
        hair_t = np.nonzero(body[ys, xs])[0]; casters = pos[hair_t][::4]; tree = cKDTree(casters)
        skin_t = np.nonzero(sk & ~eyes_box & ~ear_v[It[ks]].any(1) & ~collar_v[It[ks]].any(1))[0]
        R, FR, TERM = SHADE['skin']
        under = contact(pos[skin_t], nor[skin_t], casters, R, FR, up=(0., 1., 0.), tree=tree)   # (under the locks)
        jaw = occlusion(Q, It[is_skin(vc)[It].all(1)], pos[skin_t], Lv) & (pos[skin_t, 1] < chin_m + SHADE['neck'])   # (the jaw's shadow on the neck: only there, the nose's on the cheek was a long dark wedge)
        away = nor[skin_t] @ Lv < TERM
        ss = smooth(under | jaw | away, skin_t, SHADE['blur'][0])
        lit_tone = out[ys[skin_t], xs[skin_t]].mean(1) > np.mean(SKIN[1][1]) + 8   # (Meshy's own skin shadows stay as they are: not twice)
        k = skin_t[ss & lit_tone]; out[ys[k], xs[k]] = out[ys[k], xs[k]] * (np.array(SKIN[1][1], float) / np.array(SKIN[0][1], float))
        R, FR, TERM, DR = SHADE['hair']
        hc = contact(pos[hair_t], nor[hair_t], casters, R, FR, tree=tree)   # (under other locks)
        Lh = np.array(SHADE['Lh'], float); Lh /= np.linalg.norm(Lh)
        ha = nor[hair_t] @ Lh < TERM   # (their undersides: by a light from above, the same from every side, as the images)
        Dk = np.zeros((TS, TS), bool); Dk[body] = ~lum_split(T, body, DR, HAIR_BLUR)[body]   # (Meshy's darkest: the images' deep shadows)
        hs = smooth(hc | ha | Dk[ys[hair_t], xs[hair_t]], hair_t, SHADE['blur'][1])
        out[ys[hair_t], xs[hair_t]] = np.array(HAIR[0], float); out[ys[hair_t[hs]], xs[hair_t[hs]]] = np.array(HAIR[1], float)
        print('shade: skin %d texels in shadow (%d under the locks, %d the face\'s own, %d turned away); hair %.0f%% in shadow' % (
            len(k), int(under.sum()), int(jaw.sum()), int(away.sum()), 100 * hs.mean()))
    free_t = piece_t = None
    if PAINT:   # the head painted from Denis's six head images, see PAINT
        hair_x = body[ys, xs] & ~ear_v[It[ks]].any(1) & ~collar_v[It[ks]].any(1)
        if FACE == 'paint' and SIDES:   # (not the locks hanging free before the face: no image draws them where they are, kael_fringe.free_locks())
            from kael_fringe import free_locks
            free_t, piece_t = free_locks(Q, It, hair_v, json.load(open(os.path.join(ROOT, PAINT['cams']))), FACE_MID); hair_x &= ~free_t[ks]
        n_p, got = paint(out, Q, It, ys, xs, ks, pos, nor, hair_x)   # (the hair: on the face the image's bangs fell on the model's skin)
        # (the hair no image paints, a third of the nape's: the model's tips hang lower than the drawn ones and the images draw the neck
        # there, the locks' flanks face no image. It kept the two flat tones by the geometry, their borders along the triangles' edges,
        # pale ends under the drawn tips. Now each takes the nearest painted hair's fill colour, within HAIR_FILL[0] m; else the shadow's)
        painted = np.zeros(len(ys), bool); painted[got] = True; unp = np.nonzero(hair_x & ~painted)[0]
        fill = got[out[ys[got], xs[got]].mean(1) > PAINT['ink'] + HAIR_FILL[1]]
        if len(unp) and len(fill):
            dd, jj = cKDTree(pos[fill]).query(pos[unp], distance_upper_bound=HAIR_FILL[0]); nr = np.isfinite(dd)
            out[ys[unp[nr]], xs[unp[nr]]] = out[ys[fill[jj[nr]]], xs[fill[jj[nr]]]]; out[ys[unp[~nr]], xs[unp[~nr]]] = np.array(HAIR[1], float)
            print('hair: %d texels no image paints as the nearest painted hair (%d too far: the shadow\'s lavender)' % (int(nr.sum()), int((~nr).sum())))
        # (and Meshy's neutral greys left on the hair's triangles, neither hair's colour nor a line: the locks' inner sides no image sees,
        # flat grey polygons among the lavender. As the nearest painted fill, else the shadow's)
        cg = out[ys, xs]; grey = (hair_v[It[ks]].sum(1) >= 2) & ~hair_x & ~painted & ~ear_v[It[ks]].any(1) & ~collar_v[It[ks]].any(1) & ~is_skin(cg) & (np.ptp(cg, axis=1) < GREY[0]) & (cg.mean(1) > GREY[1])
        if free_t is not None: grey &= ~free_t[ks]
        gi = np.nonzero(grey)[0]
        if len(gi) and len(fill):
            dd, jj = cKDTree(pos[fill]).query(pos[gi], distance_upper_bound=GREY[2]); nr = np.isfinite(dd)
            out[ys[gi[nr]], xs[gi[nr]]] = out[ys[fill[jj[nr]]], xs[fill[jj[nr]]]]; out[ys[gi[~nr]], xs[gi[~nr]]] = np.array(HAIR[1], float)
            print('hair: %d grey texels on the hair\'s triangles as the nearest painted hair' % len(gi))
        print('painted from the images: %d texels (%.0f%% of the head\'s)' % (n_p, 100 * n_p / len(ys)))
    keep_t, card, sides_t, face_t, temple_x = np.ones(len(It), bool), None, None, None, None
    if FACE:   # the face from the images, Meshy's locks over it out, the front image's bangs a sheet (tools/kael_fringe.py)
        from kael_fringe import face as face_paint
        cams_ = json.load(open(os.path.join(ROOT, PAINT['cams'])))
        keep_t, card, sides_t, face_t, temple_x = face_paint(out, Q, Nq, UV, It, ys, xs, ks, pos, nor, vc, hair_v, ear_v, collar_v, FACE_MID, eye_m, chin_m, cams_, is_skin, is_hair, sheet=FACE == 'sheet', paint_bangs=FACE in ('paint', 'all'), paint_all=FACE == 'all', pressed=None if press_w is None else press_w > .05, sides=FACE == 'paint' and SIDES, bary=bary, free=free_t, piece=piece_t)
    # the earrings in the drawing's purples (EAR_TONES: by how much each facet faces EAR_LIGHT), the bead and the hook in
    # its silver (EAR_SILVER: lit, shaded); their lines black
    # the shelf between the neck and the collar's rim: the bust's collar is pushed out to Kael's, the neck's skin is not, and the
    # triangles joining them (one or two corners the collar's) lie nearly flat between them. No step paints them (each leaves the
    # collar's out): they kept Meshy's blend of skin and cloth, skin's shards through the collar's black line from behind, a streaked
    # shelf with lavender spikes as the head tips (Denis, 11/11, circling the nape: the lavender bit by the collar). Now the collar's
    # dark lining, and their corners not the collar's without outline (it drew black teeth through them)
    # (up to the collar's rim only (its own corners' top plus SHELF_TOP): where a shelf triangle's skin corner stands higher up the nape, the part
    # over the rim is the neck's skin; all of it dark, it was a black triangle standing on the nape over the rim's centre)
    sh_t = collar_v[It].any(1) & ~collar_v[It].all(1); rim_y = np.where(collar_v[It], Q[It][:, :, 1], -1e9).max(1)
    k = np.nonzero(sh_t[ks] & (pos[:, 1] < rim_y[ks] + SHELF_TOP))[0]; out[ys[k], xs[k]] = np.array(COLLAR_SHELF, float)
    shelf_v = np.zeros(len(Q), bool); shelf_v[It[sh_t].ravel()] = True; shelf_v &= ~collar_v
    print('collar: %d triangles between the neck and its rim in its lining\'s colour (%d texels), %d of their corners without outline' % (int(sh_t.sum()), len(k), int(shelf_v.sum())))
    jt = np.nonzero(ear_v[It[ks]].all(1))[0]
    if len(jt):
        fn = np.cross(Q[It[:, 1]] - Q[It[:, 0]], Q[It[:, 2]] - Q[It[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
        # (each earring by its own side's light, from the front and from behind: with one light for both, his left one was dark
        # seen from his left and both flat dark from behind; Denis's back image draws them as from the front)
        el = np.array(EAR_LIGHT, float); el /= np.linalg.norm(el); sg = np.where(pos[jt, 0] > FACE_MID, -1., 1.)
        nx = fn[ks[jt], 0] * sg; lt = nx * el[0] + fn[ks[jt], 1] * el[1] + np.abs(fn[ks[jt], 2]) * el[2]; cj = T[ys[jt], xs[jt]]
        # (the bead and the hook by their height, over the crystal's top: by Meshy's colours the bead was the crystal's purple with
        # black crumbs. The crystal's top, per earring: EAR_APEX)
        hook = np.zeros(len(jt), bool)
        for sgn in (-1, 1):
            ev = ear_v & ((Q[:, 0] - FACE_MID) * sgn > 0)
            if not ev.any(): continue
            ey = Q[ev, 1]; hs = np.arange(ey.min(), ey.max() + 1e-9, .001); wd = np.full(len(hs), np.nan)
            for a, h in enumerate(hs):
                m_ = ev & (np.abs(Q[:, 1] - h) < .0015)
                if m_.sum() > 1: wd[a] = max(np.ptp(Q[m_, 0]), np.ptp(Q[m_, 2]))
            a = int(np.nanargmax(wd)); b = min(len(hs), a + int(EAR_APEX[0] * 1000) + 1); apex, thin = ey.max(), False
            for c in range(a + 1, b):   # (its vertices are few, rings at its widest and at its point: up from its widest, past its point (thin), to where the bead widens)
                if np.isnan(wd[c]): continue
                if wd[c] < EAR_APEX[2]: thin = True; apex = hs[c]
                elif thin and wd[c] >= EAR_APEX[3]: break
            hook |= ((pos[jt, 0] - FACE_MID) * sgn > 0) & (pos[jt, 1] > apex)
            print('earring %s: the crystal up to %.4f m (its widest %.1f mm), the bead and the hook over it' % ('left' if sgn > 0 else 'right', apex, 1000 * np.nanmax(wd)))
        pur = is_purple(cj) & (cj.max(1) >= 70) & ~hook; sil = (~is_purple(cj) & (cj.max(1) >= 70)) | hook
        tone = np.digitize(lt, EAR_STEPS)   # (0 darkest .. 3 highlight)
        tones = np.array(EAR_TONES, float)[::-1]
        out[ys[jt[pur]], xs[jt[pur]]] = tones[tone[pur]]
        out[ys[jt[sil]], xs[jt[sil]]] = np.where((lt[sil] > 0)[:, None], np.array(EAR_SILVER[0], float), np.array(EAR_SILVER[1], float))
        print('earrings: %d crystal texels in the drawing\'s four purples, %d of the bead and the hook silver' % (int(pur.sum()), int(sil.sum())))
    if temple_x is not None:   # (the texels side_paint painted by the eyes' corners (kael_fringe.face's temple): those that would be in the eyes' and
        # brows' mask without that paint go back to what they were, and stay out of the new paint's set; nothing of that mask changes)
        import kael_flat
        tl, tprev = temple_x; tl = tl.copy(); gi = np.nonzero(tl)[0]
        if len(gi):
            cc = out[ys, xs].astype(np.float32); cc[gi] = tprev; kk = np.nonzero(keep_t[ks])[0]; m_ = np.zeros(len(ks), bool)
            m_[kk] = kael_flat.eyes_mask(pos[kk].astype(np.float64), nor[kk].astype(np.float32), cc[kk], (is_skin(vc)[It].sum(1) >= 2)[ks[kk]], FACE_MID, eye_m)
            back = gi[m_[gi]]; out[ys[back], xs[back]] = cc[back]; tl[back] = False
            print('face: %d texels of the temples\' new paint inside the eyes\' and brows\' mask as it was without it: put back' % len(back))
        temple_x = tl
    if os.environ.get('KAEL_FLAT_DUMP'):   # (the state before the flat colours' pass, to work on that pass alone: tools/kael_flat.py's own main)
        np.savez(os.environ['KAEL_FLAT_DUMP'], out=out.astype(np.float32), It=It, ys=ys, xs=xs, ks=ks, pos=pos.astype(np.float32), nor=nor.astype(np.float32), hair_v=hair_v, skin_v=is_skin(vc),
                 ear_v=ear_v, collar_v=collar_v, keep_t=keep_t, mid=FACE_MID, eye_m=eye_m, chin_m=chin_m, free_t=free_t if free_t is not None else np.zeros(len(It), bool), Q=Q,
                 face_t=face_t if face_t is not None else np.zeros(len(It), bool), not_eye=temple_x if temple_x is not None else np.zeros(len(ks), bool))
    fixed_x = None
    if FLAT:   # (the drawings' flat colours, the eyes and the brows left as painted: tools/kael_flat.py)
        import kael_flat
        kael_flat.prepare(Q, It); fl_ = kael_flat.flatten(out, It, ys, xs, ks, pos, nor, hair_v, is_skin(vc), ear_v, collar_v, keep_t, FACE_MID, eye_m, chin_m, face_t=face_t, not_eye=temple_x)
        fixed_x = fl_[2][fl_[3]]   # (the eyes', the brows' and the earrings' texels, left as painted)
    # (the texels no drawn triangle holds as the nearest drawn one's. Those of the triangles left out too (Meshy's locks over the face): they kept
    # their hair's paint, and the drawn triangles next to them in the texture picked it up along their edges, lavender and black dots on the
    # cheek under a lock's tip; Denis's screenshot of 11/11. Not within PAD_KEEP texels of the eyes', the brows' and the earrings': there
    # every texel stays as it was, nothing of theirs changes, "occhi e sopracciglia non si toccano")
    cov = np.zeros((TS, TS), bool); kt = keep_t[ks]; cov[ys[kt], xs[kt]] = True
    if fixed_x is not None and len(fixed_x):
        fm = np.zeros((TS, TS), bool); fm[ys[fixed_x], xs[fixed_x]] = True; allc = np.zeros((TS, TS), bool); allc[ys, xs] = True
        cov |= allc & ndimage.binary_dilation(fm, iterations=PAD_KEEP)
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    # (lossless: a JPEG smears every border between two flat colours, and halves the colours' resolution)
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(os.path.join(KAEL_PKG, 'kael_head.png'), optimize=True)
    if os.path.exists(os.path.join(KAEL_PKG, 'kael_head.jpg')): os.remove(os.path.join(KAEL_PKG, 'kael_head.jpg'))   # (the earlier builds': the pages would carry both)
    # the package (as tools/ren_head.py's)
    It = It[keep_t]   # (without Meshy's locks over the face, FACE)
    src = np.arange(len(Q)); hmask = None
    if sides_t:   # (Meshy's locks hidden from his right side and from his left: their triangles' corners split from the rest's, each copy with the side(s) it is hidden from; src/e_model.js mdHeadHide)
        from kael_fringe import HIDE_VIEWS
        tm = np.zeros(len(It), np.int64)
        for b_, side in enumerate(('dx', 'sx')):
            assert all((sides_t[v_] == sides_t[HIDE_VIEWS[side][0]]).all() for v_ in HIDE_VIEWS[side])   # (one set per side: kael_fringe.side_hide)
            tm |= sides_t[HIDE_VIEWS[side][0]][keep_t].astype(np.int64) << b_
        pair = It.astype(np.int64) * 4 + tm[:, None]; up, inv_ = np.unique(pair.ravel(), return_inverse=True)
        src = up // 4; hmask = up % 4; It = inv_.reshape(-1, 3)
        print('hidden from his right side %d triangles, from his left %d; %d corners split from their neighbours\' (%d vertices in use)' % (
            int((tm & 1).sum()), int((tm >> 1 & 1).sum()), len(src) - len(np.unique(src)), len(src)))
    scrap_v = np.zeros(len(Q), bool)
    if face_t is not None and face_t.any():   # (the vertices all of whose kept hair triangles are the face's: tools/kael_fringe.py face(), its scraps and gap covers)
        Io = src[It]; ft = face_t[keep_t]; hk = hair_v[Io].sum(1) >= 2; other = np.zeros(len(Q), bool); other[Io[hk & ~ft].ravel()] = True   # (Io: It's corners before the split)
        scrap_v[Io[ft].ravel()] = True; scrap_v &= ~other
    Q, Nq, UV, top, tw, ear_v, hair_v, collar_v, vc = Q[src], Nq[src], UV[src], top[src], tw[src], ear_v[src], hair_v[src], collar_v[src], vc[src]
    shelf_v, scrap_v = shelf_v[src], scrap_v[src]
    if press_w is not None: press_w = press_w[src]
    # (the hair's outline: its vertices and those of the dark lines Meshy painted between its locks, neither hair's colour nor skin's:
    # at the full width and not pushed back, their outline was black shards along the locks, over the brow from the side)
    hairish = hair_v | (~is_skin(vc) & ~ear_v & ~collar_v & (Q[:, 1] > JAW_Y))
    hairish &= ~scrap_v   # (the hair's scraps lying on the face, painted as its skin: no hair's rim round them)
    line_w = np.where(ear_v, EAR_LINE, np.where(hairish, HAIR_LINE_W, 1.))
    line_w[shelf_v] = 0.
    if press_w is not None: line_w = line_w * (1 - np.clip(press_w, 0, 1)) ** 2   # (the pressed temples: their lines the profiles' own, painted)
    lb, n_over = face_back(Q, It, is_skin(vc) & ~hair_v & (Q[:, 1] > JAW_Y), hair_v)
    if PAINT: lb = np.maximum(lb, np.where(hairish, HAIR_BACK, 0.))   # (the hair's outline pushed back: only the mane's outer edge drawn, the lines inside it the images')
    lb = np.where(scrap_v, 0., lb)
    lb = np.where(ear_v, 0., lb)   # (the earrings' outline not pushed back: the hook, hair's colour, was pushed behind the head with the fringe, a pale strip with no contour)
    print('outline: the hair\'s %.2f of the width, the earrings\' %.2f; %d hair vertices over the face pushed back %.0f mm (%d with the smoothing)' % (
        HAIR_LINE_W, EAR_LINE, n_over, 1000 * FRINGE[0], int((lb > 0).sum())))
    n_add = 0
    if STUMP and FACE:   # (the stumps of the locks left out on the cheeks, and the holes under them: cheek_stumps())
        cs = cheek_stumps(Q, It, is_skin(vc), FACE_MID, eye_m, chin_m, np.clip(out, 0, 255).round(), UV)
        if cs is not None:
            keep_c, caps, reset, uv0 = cs; line_w = line_w.copy(); lb = lb.copy(); line_w[reset] = 1.; lb[reset] = 0.
            nv, nt, nn = [], [], []
            for rim, cen, nrm in caps:   # (their own vertices: the rim's places and skinning, the cheek's normal, on the one texel; full outline, never hidden)
                base = len(Q) + len(nv); nv += [(Q[v], v) for v in rim] + [(cen, rim[0])]; nn += [nrm] * (len(rim) + 1); cen_i = base + len(rim)
                for a in range(len(rim)):
                    t = [cen_i, base + a, base + (a + 1) % len(rim)]; pa = [cen, Q[rim[a]], Q[rim[(a + 1) % len(rim)]]]
                    nt.append(t if np.cross(pa[1] - pa[0], pa[2] - pa[0]) @ nrm > 0 else [t[0], t[2], t[1]])
            if nv:
                n_add = len(nv); sv = np.array([v for _, v in nv]); nrm_ = np.array(nn)
                Q = np.concatenate([Q, np.array([p for p, _ in nv])]); Nq = np.concatenate([Nq, nrm_]); UV = np.concatenate([UV, np.tile(uv0, (n_add, 1))])
                top = np.concatenate([top, top[sv]]); tw = np.concatenate([tw, tw[sv]]); line_w = np.concatenate([line_w, np.ones(n_add)]); lb = np.concatenate([lb, np.zeros(n_add)])
                if hmask is not None: hmask = np.concatenate([hmask, np.zeros(n_add, hmask.dtype)])
            It = np.concatenate([It[keep_c], np.array(nt, It.dtype).reshape(-1, 3)])
            print('cheek: %d triangles out, %d in, %d vertices added, the outline reset on %d' % (int((~keep_c).sum()), len(nt), n_add, int(reset.sum())))
    pad = lambda bts: bts + b'\0' * (-len(bts) % 4)
    blob = b''; jo = {'v': 1, 'verts': int(len(Q)), 'tris': int(len(It)), 'scale': round(float(s), 5)}
    def put(key, arr):
        nonlocal blob
        blob = pad(blob); jo[key] = [len(blob), int(arr.size)]; blob += np.ascontiguousarray(arr).tobytes()
    put('pos', Q.astype(np.float32)); put('nor', Nq.astype(np.float32)); put('uv', UV.astype(np.float32))
    put('jnt', top.astype(np.uint8)); put('wgt', tw.astype(np.float32))
    put('idx', It.astype(np.uint16 if len(Q) < 65536 else np.uint32)); put('hide', hide)
    flat_v = np.ones(int(src.max()) + 1)
    if len(cv): flat_v[cv] = flat_c
    flat_v = np.concatenate([flat_v[src], np.ones(n_add)])
    put('lb', lb.astype(np.float32)); put('flat', flat_v.astype(np.float32)); put('line', line_w.astype(np.float32))
    if hmask is not None:   # (hidden from his right side, from his left: src/e_model.js mdHeadHide, by the camera's angle around the head, switching midway between the front image's and each 3/4's)
        cams_ = json.load(open(os.path.join(ROOT, PAINT['cams'])))
        put('hv', np.stack([(hmask >> b_ & 1) for b_ in range(2)], 1).astype(np.float32))
        from kael_fringe import PRESS_WIN
        jo['hideAz'] = [round(float(FACE_MID), 5), PRESS_WIN[4], (cams_['34_dx']['yaw'] + cams_['fronte']['yaw']) / 2, (cams_['fronte']['yaw'] + cams_['34_sx']['yaw']) / 2]
    open(os.path.join(KAEL_PKG, 'kael_head.bin'), 'wb').write(pad(blob)); json.dump(jo, open(os.path.join(KAEL_PKG, 'kael_head.json'), 'w'), separators=(',', ':'))
    for ext in ('json', 'bin', 'png'):
        fp = os.path.join(KAEL_PKG, 'kael_fringe.' + ext)
        if os.path.exists(fp): os.remove(fp)
    if card is not None:   # the bangs' sheet (src/e_model.js mdFringeData: on the Head bone)
        sp, suv, stri, rgba = card; blob = b''; jo = {'v': 1, 'verts': int(len(sp)), 'tris': int(len(stri))}
        put('pos', sp.astype(np.float32)); put('uv', suv.astype(np.float32)); put('idx', stri.astype(np.uint16 if len(sp) < 65536 else np.uint32))
        open(os.path.join(KAEL_PKG, 'kael_fringe.bin'), 'wb').write(pad(blob)); json.dump(jo, open(os.path.join(KAEL_PKG, 'kael_fringe.json'), 'w'), separators=(',', ':'))
        Image.fromarray(rgba, 'RGBA').save(os.path.join(KAEL_PKG, 'kael_fringe.png'), optimize=True)
    print('written: kael_head (%d vertices, %d triangles); bones %s' % (len(Q), len(It), {names[i]: int(c) for i, c in enumerate(np.bincount(top[:, 0], minlength=nb)) if c}))


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
