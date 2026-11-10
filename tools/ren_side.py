"""The sides of the new head clean around the ears, on the temples, on the neck and on the cheeks (9-10/11/2026).
Denis's detail sheet (docs/ref/personaggi/ren_testa_dettagli.png, "togli tutto il necessario affinché sembri real come
l'immagine") gave the ear: seen, small as Meshy's ("ok l'orecchio ci sta", prova 1). Then: "fai meglio i capelli attorno
alle orecchie e sul collo, e quelli sulle guance; gli altri capelli non toccarli"; and on 10/11 two photos with the
circled parts left: the ear, around it, the temple to the eye's corner, the neck behind the ear.

Meshy's head is one shell: on the sides its outer surface is the hair, with no scalp under it, and loose flaps of hair
hang over the face's and the neck's skin (the ragged strands, the "spikes"); cut, they opened holes. Here, per side, in
a window (SIDE_WIN: z from, to; y from, to) seen along x (a picture SIDE_PX m per px: the outermost surface's colour and
depth, the innermost's depth), its parts SIDE_CORE changed fully, fading over SIDE_BAND m:
- a clean design: Meshy's hair outline cleaned as a drawing is (the dark joined to the hair above, SIDE_TOP_PX; strands
  thinner than 2 * SIDE_OPEN px off, SIDE_OPEN[1] in front of SIDE_TEMPLE_Z, the temple's, their tips put back as clean
  points, SIDE_TIP; gaps narrower than 2 * SIDE_CLOSE px shut, specks under SIDE_SPECK px gone, holes in the hair up to
  SIDE_HOLE px filled, pieces cut off from it under SIDE_BIG px out, the edge smoothed); the ear the sheet's drawing and
  SIDE_EAR_PAD m of skin around it (and the sheet's skin within SIDE_NEAR_EAR of it); in it the hair in its own colours
  (the nearest hair's where it was not), the skin in its own tone around (its marks left out), an ink line SIDE_INK[0]
  m wide along the hair's edge (not along the ear: its drawing has its own);
- the surface: the skin's (the skin seen where the shell has one layer, carried harmonic under the rest) SIDE_SKIN_UP
  m over it where the design has skin, the ear's bump too (prova 1's ear: the drawing on the side of the head); the
  hair under a cone from its edge (no higher over the skin than SIDE_CONE[0] m plus SIDE_CONE[1] m per m, a soft
  minimum of SIDE_CONE[2] m; never raised: its relief kept under it), within SIDE_DEEP m of its edge brought onto the
  smoothed surface; a point raised no more than SIDE_RAISE m (deeper: left, hidden); a flap's underside SIDE_INSINK m
  under its top (no flicker between them); flaps of hair over the skin (SIDE_FLAP[1] m over it where the design has
  skin) moved down within SIDE_FLAP[0] too, wherever the window ends; never the head's bottom edge (SIDE_EDGE_STEPS
  steps around it: the collar's skirt hangs from it), the collar, nor anything under SIDE_FLOOR m; the outline of all
  that pushed back SIDE_LINE m;
- the paint: every triangle there, its texels from the design along x (the same on every layer: the gaps between the
  locks and the skin under them alike), the triangles moved over SIDE_MOVED m painted fully, the walls (their normal's
  share along x under SIDE_WALL) without lines; the texels standing SIDE_LIFT m over the skin after the moves (a lock
  not pressed down: seen from the front) in the hair's colours, not the design's skin; not the face's front (normal's
  share along z over SIDE_FRONT, unless moved).
- the eyes kept: their triangles (whites or iris in their texels, the iris's only within SIDE_EYE_NEAR m of the whites:
  the temple's shaded skin has its colours; SIDE_EYE_RINGS rings around), a box (SIDE_EYE_BOX)
  and SIDE_EYE_GUARD m around their whites neither moved nor painted;
- on the temple to the eye's corner (SIDE_TEMPLE, as ren_head.TEMPLE_LINE, but for the points as they are after the
  moves and further out: its locks came from outside that box) the outline pushed back SIDE_TEMPLE[3] m (inside the head
  the locks' edges seen from three quarters drew black hooks; the silhouette keeps its line), and the locks there
  standing out over the skin in the hair's colours even in front of the window's parts (their light undersides, seen
  from the front: streaks), facing the front or not (the face's front, lying on the skin, stays).
The temple's locks (10/11 night, Denis: "le ciocche ... falle meglio che puoi"; they hung there as a fringe of thin
spikes and needles, the black triangle):
- the eyes' guard no longer takes the temple: the iris's colours, sought for the eyes' triangles, are also the temple's
  shaded skin (SIDE_EYE_NEAR above); held there, neither moved nor painted, with its neighbours (SIDE_EYE_RINGS) it
  stopped the whole temple's locks from coming down;
- no triangle stretched: a point goes in no more than SIDE_STRETCH m per m of mesh from the points that go less or stay
  (a lock's tip pressed beside its root left where it was drew a needle across the temple), the welded copies together;
- on the temple a lower cone (SIDE_TEMPLE_CONE: its slope there), and its edge redrawn (SIDE_TEMPLE_EDGE: opened wider,
  its tips put back as points; blended into the rest by the signed distance over the box's ramp): no drips, no hooks;
- there the hair one tone (SIDE_TEMPLE_TONE: its colours blurred): Meshy's strokes, painted along x on the locks pressed
  near the edge, read from three quarters as spikes and light streaks;
- the locks moved near the eyes painted (their guard's most, not its least: half in, half out of the eyes' box they had
  been moved but kept Meshy's streaks), and the temple's skin under the design's hair painted facing the front too;
- a painted triangle's texels within SIDE_EDGE_PX of its edges painted too (between the two pieces of a seam neither had
  them: dotted light lines along the locks).
sides() also returns the texels it painted: the neck's marks (ren_head.py, NECK_CLEAN) leave them as they are.

usage (prototyping on a head already made): python3 tools/ren_side.py HEAD_DIR [DEBUG.npz]"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
SIDE_SHEET = ('docs/ref/personaggi/ren_testa_dettagli.png', (1028, 0, 1536, 490))   # (the sheet, its profile panel: x0, y0, x1, y1 px)
SIDE_EAR = (273, 263, 317, 347)          # the ear in the panel (x0, y0, x1, y1 px)
SIDE_EAR_M = (-.008, 1.590, .042)        # where the drawn ear goes on the model: its centre (z, y m) and height (m): Meshy's
SIDE_WIN = (-.090, .095, 1.490, 1.675)   # the window: z from, to; y from, to (m)
SIDE_CORE = [(-.078, .014, 1.528, 1.660), (.014, .072, 1.572, 1.650)]   # its parts changed fully (z0, z1, y0, y1)
SIDE_BAND = .004                         # m: their edges' fade (a gaussian)
SIDE_PX = .00025                         # the side picture's m per px
SIDE_OPEN, SIDE_CLOSE, SIDE_TEMPLE_Z = (7, 12), 4, .012   # px; px; m (see above)
SIDE_TIP = (10, .35, 8)                  # tips put back: at least [0] px long, their base's half width up to [1] of their length, [2] px apart
SIDE_SPECK, SIDE_HOLE, SIDE_BIG = 160, 2500, 4000   # px (see above)
SIDE_SOFT_EDGE = 1.5                     # px: the cleaned outline smoothed (a gaussian, cut at its half)
SIDE_TOP_PX = 12                         # px: the hair is the dark joined to the window's top rows
SIDE_EAR_PAD, SIDE_NEAR_EAR = .0005, .006   # m (see above)
SIDE_EAR_LINE = (1.1, 2.0)               # the sheet's px: the ear's outline line's width; its mask softened (see sheet_ear())
SIDE_INK = (.0007, .00015)               # m: the ink line's width, its edges' softness
SIDE_SKIN_UP, SIDE_RAISE, SIDE_INSINK = .0006, .001, .0012   # m (see above)
SIDE_CONE, SIDE_DEEP = (.001, 1.2, .002), .004   # see above
SIDE_TEMPLE_CONE = ((.004, .016, .062, .078), (1.640, 1.655), .35)   # the temple's: z ramps (in from, full from, full to, out at), y (full under, none over), its slope (m per m)
SIDE_FLAP = ((-.090, .076, 1.520, 1.675), .003)   # see above
SIDE_FLOOR, SIDE_EDGE_STEPS = 1.515, 3   # see above
SIDE_MOVED, SIDE_WALL, SIDE_LIFT, SIDE_FRONT = .001, (.2, .45), .002, .6   # see above
SIDE_EYE_BOX = (.055, 1.570, 1.615, .058, .003)   # the eyes: z over [0], y between [1] and [2], under [3] m from the middle; its margin [4]
SIDE_EYE_RINGS, SIDE_EYE_GUARD = 2, (.004, .008, .003, .006)   # m from the whites: no paint within [0], fully from [1]; no move: [2], [3]
SIDE_EYE_NEAR = .008                     # m: the iris's colours count as the eye's within this of a white triangle
SIDE_LINE, SIDE_GROW = .03, 2.5          # m; px of the painted triangles' texels around them, in the texture's gaps
SIDE_EDGE_PX = .7                        # px: a painted triangle's texels within this of its edges painted too
SIDE_STRETCH = .8                        # see above: m a point may go in per m of mesh from its neighbours
SIDE_TEMPLE = ((.045, .13), (1.555, 1.665), (-.03, .085), .1, .004)   # see above: |x| from the middle, y, z (m); the push (m), its ramp (m)
SIDE_TEMPLE_EDGE = ((.012, .062, 1.550, 1.640), .002, 16, (16, .2, 16))   # the temple's edge redrawn: z, y box (its ramp, m); the opening (px), the tips (as SIDE_TIP)
SIDE_TEMPLE_TONE = 14, (.012, .080, 1.550, 1.640)   # px: the hair's colours blurred (one tone: Meshy's strokes, seen on the locks pressed, drew spikes) on z, y (m; to the eye's lock)
X0 = .006                                # the head's middle (x, m)
INK = np.array([22., 20, 26]); HAIR = np.array([[22., 20, 26], [58, 48, 58], [75, 64, 73], [113, 94, 102]])   # (ren_hair.HAIR_TONES)
SHADE = np.array([.82, .74, .72])        # (ren_hair.SKIN_SHADE)
ss = lambda e0, e1, x: (lambda t: t * t * (3 - 2 * t))(np.clip((x - e0) / (e1 - e0), 0, 1))


# --- the sheet's ear (as prova 1 drew it) ---

def sheet_classes():
    """The profile panel's pixels: 0 background, 1 skin, 2 skin's shadow (the ear's hollow), 3 ink, 4 hair dark, 5 hair
    colour, 6 hair light."""
    root = os.path.join(HERE, '..'); x0, y0, x1, y1 = SIDE_SHEET[1]
    P = np.asarray(Image.open(os.path.join(root, SIDE_SHEET[0])).convert('RGB')).astype(int)[y0:y1, x0:x1]
    r, g, b = P[..., 0], P[..., 1], P[..., 2]; m = P.mean(2)
    k = np.zeros(P.shape[:2], np.uint8)
    k[(m < 110)] = 4
    k[(m < 110) & (m >= 52) & (r - g < 30)] = 5
    k[(m >= 80) & (m < 150) & (r - g < 40) & (b > g)] = 6
    k[(r > 140) & (r <= 215) & (r - b > 50) & (g < 145)] = 2
    k[(r > 215) & (r - b > 60) & (g > 140)] = 1
    k[(np.abs(r - g) < 12) & (np.abs(g - b) < 14) & (r > 190)] = 0
    nearskin = ndimage.binary_dilation((k == 1) | (k == 2), iterations=2)
    k[(m < 40) & nearskin] = 3
    return k


def sheet_ear(skin_rgb):
    """The panel's ear (a soft mask, float: over .5 the ear), its skin (mask) and its drawing in the head's colours (float
    (h, w, 3))."""
    k = sheet_classes()
    sk = (k == 1) | (k == 2); sk = ndimage.binary_closing(sk, iterations=2) | sk
    ex0, ey0, ex1, ey1 = SIDE_EAR
    ear = np.zeros_like(sk); ear[ey0 - 2:ey1 + 3, ex0 - 3:ex1 + 3] = (sk | (k == 3))[ey0 - 2:ey1 + 3, ex0 - 3:ex1 + 3]
    lab, n = ndimage.label(ear); cy, cx = (ey0 + ey1) // 2, (ex0 + ex1) // 2
    ear = lab == lab[cy, cx] if lab[cy, cx] else ear
    ear = ndimage.binary_fill_holes(ear)
    # (its outline smooth: the mask softened, SIDE_EAR_LINE[1] px; its drawing the sheet's own colours in the head's skin,
    # each channel scaled by the head's skin over the sheet's: its lines and shades as crisp as the sheet's, not classes
    # (their anti-aliased edges, taken for the hair's colours, beaded the outline); a line SIDE_EAR_LINE[0] px wide along
    # its free edge, inside it (10/11, Denis: "migliora leggermente i contorni dell'orecchio"); not where it joins the face)
    earf = ndimage.gaussian_filter(ear.astype(float), SIDE_EAR_LINE[1])
    root = os.path.join(HERE, '..'); x0, y0, x1, y1 = SIDE_SHEET[1]
    P = np.asarray(Image.open(os.path.join(root, SIDE_SHEET[0])).convert('RGB')).astype(float)[y0:y1, x0:x1]
    s_skin = np.median(P[ey0:ey1, ex0:ex1][k[ey0:ey1, ex0:ex1] == 1], 0)
    img = np.clip(np.asarray(skin_rgb, float) * P / s_skin, 0, 255)
    ins = ndimage.distance_transform_edt(earf > .5) - .5
    ring = ~(earf > .5) & ndimage.binary_dilation(earf > .5, iterations=2)   # (outside, along the outline: where the sheet has
    attached = ndimage.binary_dilation(ring & ((k == 1) | (k == 2)), iterations=3)   # skin there, the ear joins the face: no line)
    ink = (1 - ss(SIDE_EAR_LINE[0] - .5, SIDE_EAR_LINE[0] + .5, ins)) * ~attached
    img = img * (1 - ink[..., None]) + INK * ink[..., None]
    return earf, sk | ((k == 3) & ndimage.binary_dilation(sk, iterations=2)), img


def to_panel(z, y):
    """Model (z, y) -> panel (x, y) px (the ear on the model's)."""
    s = SIDE_EAR_M[2] / (SIDE_EAR[3] - SIDE_EAR[1]); cx, cy = (SIDE_EAR[0] + SIDE_EAR[2]) / 2, (SIDE_EAR[1] + SIDE_EAR[3]) / 2
    return cx + (SIDE_EAR_M[0] - z) / s, cy + (SIDE_EAR_M[1] - y) / s


# --- the side picture ---

def grid():
    """The window's picture: its size and model (z, y) -> px (u, v) and back."""
    z0, z1, y0, y1 = SIDE_WIN
    W, H = int((z1 - z0) / SIDE_PX), int((y1 - y0) / SIDE_PX)
    return W, H, (lambda z, y: ((z - z0) / SIDE_PX, (y1 - y) / SIDE_PX)), (lambda u, v: (u * SIDE_PX + z0, y1 - v * SIDE_PX))


def raster(Q, UV, I, tex, sg, tris):
    """The window seen from side sg along x: per px the outermost surface (its depth |x - X0|, triangle, colour) and the
    innermost (its depth)."""
    W, H, to_g, _ = grid(); TS = tex.shape[0]
    amax = np.full((H, W), -9.); amin = np.full((H, W), 9.); tid = np.full((H, W), -1, np.int64); col = np.zeros((H, W, 3))
    for k in tris:
        v = Q[I[k]]; a = sg * (v[:, 0] - X0); us, vs = to_g(v[:, 2], v[:, 1])
        xa, xb = int(max(np.floor(us.min()), 0)), int(min(np.ceil(us.max()) + 1, W)); ya, yb = int(max(np.floor(vs.min()), 0)), int(min(np.ceil(vs.max()) + 1, H))
        if xa >= xb or ya >= yb: continue
        den = (us[1] - us[0]) * (vs[2] - vs[0]) - (us[2] - us[0]) * (vs[1] - vs[0])
        if abs(den) < 1e-12: continue
        gx, gy = np.meshgrid(np.arange(xa, xb) + .5, np.arange(ya, yb) + .5)
        l1 = ((gx - us[0]) * (vs[2] - vs[0]) - (us[2] - us[0]) * (gy - vs[0])) / den; l2 = ((us[1] - us[0]) * (gy - vs[0]) - (gx - us[0]) * (vs[1] - vs[0])) / den; l0 = 1 - l1 - l2
        ins = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
        if not ins.any(): continue
        depth = l0 * a[0] + l1 * a[1] + l2 * a[2]
        sub = amax[ya:yb, xa:xb]; up = ins & (depth > sub)
        if up.any():
            uv = l0[..., None] * UV[I[k, 0]] + l1[..., None] * UV[I[k, 1]] + l2[..., None] * UV[I[k, 2]]
            tx = np.clip((uv[..., 0] * TS).astype(int), 0, TS - 1); ty = np.clip((uv[..., 1] * TS).astype(int), 0, TS - 1)
            sub[up] = depth[up]; tid[ya:yb, xa:xb][up] = k; col[ya:yb, xa:xb][up] = tex[ty, tx][up]
        sub = amin[ya:yb, xa:xb]; dn = ins & (depth < sub); sub[dn] = depth[dn]
    return amax, amin, tid, col


def is_hair(c):
    """The hair's colours (its dark purple tones and the ink; not the skin's browns, the collar's teal or its cream)."""
    c = np.asarray(c, float); r, g, b = c[..., 0], c[..., 1], c[..., 2]
    return (c.mean(-1) < 128) & (np.abs(r - b) < 32) & (r >= g - 8)


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r


def tips(H, O, tip=SIDE_TIP):
    """Pointed triangles from O's edge out to the tips of H the opening cut (see SIDE_TIP)."""
    lmin, wfrac, supp = tip
    R = H & ~O
    dO, ind = ndimage.distance_transform_edt(~O, return_indices=True)
    d = np.where(R, dO, 0)
    pk = np.argwhere((d == ndimage.maximum_filter(d, footprint=disk(supp))) & (d >= lmin))
    lab, n = ndimage.label(R, structure=np.ones((3, 3)))
    att = np.zeros(n + 1, bool); att[np.unique(lab[ndimage.binary_dilation(O, structure=np.ones((3, 3))) & R])] = True; att[0] = False
    out = Image.new('L', (H.shape[1], H.shape[0]), 0); dr = ImageDraw.Draw(out); nt = 0
    yy_, xx_ = np.mgrid[:H.shape[0], :H.shape[1]]
    for (y, x) in pk:
        if not att[lab[y, x]]: continue
        L = d[y, x]; cy, cx = ind[0][y, x], ind[1][y, x]
        dv = np.array([x - cx, y - cy], float); dv /= max(np.linalg.norm(dv), 1e-9); pv = np.array([-dv[1], dv[0]])
        y0_, y1_, x0_, x1_ = max(cy - int(L) - 2, 0), cy + int(L) + 3, max(cx - int(L) - 2, 0), cx + int(L) + 3
        sel = (lab[y0_:y1_, x0_:x1_] == lab[y, x]) & (dO[y0_:y1_, x0_:x1_] < 4)
        if sel.any():
            pr = (xx_[y0_:y1_, x0_:x1_][sel] - cx) * pv[0] + (yy_[y0_:y1_, x0_:x1_][sel] - cy) * pv[1]; wd = max(pr.max() - pr.min(), 2) / 2
        else: wd = 2
        w = min(wfrac * L, wd + 1); b0 = np.array([cx, cy], float) - dv * 3
        dr.polygon([tuple(b0 + pv * w), tuple(b0 - pv * w), (x + .5, y + .5)], fill=255); nt += 1
    return np.asarray(out) > 0, nt


def clean(H, r_open):
    """H (the hair seen) cleaned (see above): strands thinner than 2 * r_open px off."""
    O = ndimage.binary_opening(H, structure=disk(r_open))
    T, nt = tips(H, O)
    C = O | (T & ndimage.binary_dilation(H, structure=disk(2)))
    C = ndimage.binary_closing(C, structure=disk(SIDE_CLOSE))
    lab, n = ndimage.label(C); sz = np.bincount(lab.ravel()); sz[0] = 0; C = (sz >= SIDE_SPECK)[lab] & (lab > 0)
    lab, n = ndimage.label(~C); sz = np.bincount(lab.ravel()); C |= (sz < SIDE_SPECK)[lab] & (lab > 0)
    return ndimage.gaussian_filter(C.astype(float), SIDE_SOFT_EDGE) > .5, nt


def harmonic(val, known, step=4):
    """val where known, harmonic elsewhere (solved on a grid step times coarser, back up bilinear)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    H, W = val.shape; h, w = H // step, W // step
    vk = val[:h * step, :w * step].reshape(h, step, w, step); kk = known[:h * step, :w * step].reshape(h, step, w, step)
    cnt = kk.sum((1, 3)); K = cnt > 0; V = np.where(K, (vk * kk).sum((1, 3)) / np.maximum(cnt, 1), 0)
    n = h * w; idx = np.arange(n).reshape(h, w); rows, cols, data = [], [], []
    ys, xs = np.mgrid[:h, :w]
    for (dy, dx) in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        y2, x2 = ys + dy, xs + dx; ok = (y2 >= 0) & (y2 < h) & (x2 >= 0) & (x2 < w)
        a, c = idx[ys[ok], xs[ok]], idx[y2[ok], x2[ok]]
        rows += [a, a]; cols += [a, c]; data += [np.ones(len(a)), -np.ones(len(a))]
    A = coo_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    kf = K.ravel(); D = coo_matrix((np.ones(kf.sum()), (np.nonzero(kf)[0], np.nonzero(kf)[0])), shape=(n, n)).tocsr()
    b = np.zeros(n); b[kf] = V.ravel()[kf]
    sol = spsolve((A.multiply((~kf)[:, None]).tocsr() + D).tocsc(), b).reshape(h, w)
    yy, xx = np.mgrid[:H, :W]
    return bilinear(sol[..., None], np.clip((xx.ravel() + .5) / step - .5, 0, w - 1), np.clip((yy.ravel() + .5) / step - .5, 0, h - 1))[:, 0].reshape(H, W)


def laplace_fill(val, known, iters=400):
    """val where known, smoothly carried into the rest (Jacobi rounds of the neighbours' mean, from a nearest fill)."""
    if not known.any(): return val
    _, ind = ndimage.distance_transform_edt(~known, return_indices=True); v = val[ind[0], ind[1]].copy()
    k = np.array([[0, .25, 0], [.25, 0, .25], [0, .25, 0]])
    for _ in range(iters):
        v = np.where(known, val, ndimage.convolve(v, k, mode='nearest'))
    return v


def texels_wide(uv, A, TS, covered, grow=SIDE_GROW):
    """A triangle's texels ((n, 2) col, row) and their 3D points, and around it up to grow px out into the texture's gaps
    (texels no triangle covers, their points extrapolated): painted too, the texture's filtering there takes the
    triangle's colour, not a neighbour's (light seams along the pieces' edges)."""
    lo = np.floor(uv.min(0) - grow).astype(int); hi = np.ceil(uv.max(0) + grow).astype(int)
    xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1)); px = np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)
    T = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T
    if abs(np.linalg.det(T)) < 1e-9: return np.zeros((0, 2), int), np.zeros((0, 3))
    b = np.linalg.solve(T, (px - uv[0]).T).T; w = np.c_[1 - b.sum(1), b]
    G = np.linalg.inv(T); gn = np.r_[np.linalg.norm(G.sum(0)), np.linalg.norm(G[0]), np.linalg.norm(G[1])]
    out = (-w / np.maximum(gn, 1e-12)).max(1)
    q = np.floor(px).astype(int); g = (q >= 0).all(1) & (q < TS).all(1)
    ins = (out < SIDE_EDGE_PX) & g   # (and the texels on its edges: between two pieces of a seam, neither had them)
    ring = (out > 0) & (out < grow) & g
    ring[ring] = ~covered[q[ring, 1], q[ring, 0]]
    keep = ins | ring
    return q[keep], (w[keep] @ A)


def bilinear(img, x, y):
    """img (h, w, ...) at float px x, y (clamped)."""
    h, w = img.shape[:2]; x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int); fx, fy = x - x0, y - y0
    if img.ndim == 3: fx, fy = fx[:, None], fy[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def welded(Q, I):
    """The welded points (copies at one place, as one): (first copy, each point's weld) and the welded edges."""
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    T = weld[I]; return first, weld, np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)


def eyes(Q, UV, I, tex):
    """The eyes kept (see above): per point the share it may be moved and painted (0 to 1), the eyes' triangles."""
    TS = tex.shape[0]; first, weld, E = welded(Q, I)
    vc = tex[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)]
    C = Q[I].mean(1); bw = np.array([[1 / 3, 1 / 3, 1 / 3], [.6, .2, .2], [.2, .6, .2], [.2, .2, .6]])
    U = np.einsum('kb,tbc->tkc', bw, UV[I]) * TS; ct = tex[np.clip(U[..., 1].astype(int), 0, TS - 1), np.clip(U[..., 0].astype(int), 0, TS - 1)]
    m, st = ct.mean(-1), ct.max(-1) - ct.min(-1)
    white, iris = (m > 200) & (st < 45), (ct[..., 0] > 110) & (ct[..., 0] < 215) & (ct[..., 2] < 95) & (m < 150) & (st > 70)
    base = (C[:, 2] > .045) & (C[:, 1] > 1.565) & (C[:, 1] < 1.625); wt = base & white.any(1)
    near = cKDTree(C[wt]).query(C)[0] < SIDE_EYE_NEAR if wt.any() else np.zeros(len(C), bool)   # (the temple's shaded skin
    eye_t = wt | (base & iris.any(1) & near)                                                  # has the iris's colours)
    for _ in range(SIDE_EYE_RINGS):
        vw = np.zeros(len(first), bool); vw[weld[I[eye_t]].ravel()] = True; eye_t = vw[weld[I]].any(1)
    eye_v = np.zeros(len(Q), bool); eye_v[I[eye_t].ravel()] = True
    wh = (vc.mean(1) > 215) & (vc.max(1) - vc.min(1) < 45) & (Q[:, 1] > 1.57) & (Q[:, 1] < 1.62) & (Q[:, 2] > .05)
    d = cKDTree(Q[wh]).query(Q)[0] if wh.any() else np.full(len(Q), 9.)
    ez, ey0, ey1, ea, em = SIDE_EYE_BOX
    box = ss(ez - em, ez, Q[:, 2]) * ss(ey0 - em, ey0, Q[:, 1]) * (1 - ss(ey1, ey1 + em, Q[:, 1])) * (1 - ss(ea, ea + em, np.abs(Q[:, 0] - X0)))
    keep = (1 - box) * ~eye_v
    g = SIDE_EYE_GUARD
    return ss(g[0], g[1], d) * keep, ss(g[2], g[3], d) * keep, eye_t


def sides(Q, N, UV, I, lb, tex, skin_rgb, debug=None):
    """Q, N, UV, I, lb: the head (positions, normals, uvs, triangles, outline push); tex: its texture (painted in place).
    Moves Q, N, lb in place; returns per side the points moved, the texels painted (count) and their mask (TS, TS)."""
    skin_rgb = np.asarray(skin_rgb, float); TS = tex.shape[0]
    W, H, to_g, from_g = grid()
    gu, gv = np.meshgrid(np.arange(W) + .5, np.arange(H) + .5); gz, gy = from_g(gu, gv)
    core = np.zeros((H, W))
    for z0, z1, y0, y1 in SIDE_CORE: core[(gz >= z0) & (gz <= z1) & (gy >= y0) & (gy <= y1)] = 1
    wg = ss(.02, .98, ndimage.gaussian_filter(core, SIDE_BAND / SIDE_PX))
    ear_p, sheet_skin, ear_img = sheet_ear(skin_rgb)
    pu, pv = to_panel(gz, gy); iu, iv = np.round(pu).astype(int), np.round(pv).astype(int)
    inp = (iu >= 0) & (iu < ear_p.shape[1]) & (iv >= 0) & (iv < ear_p.shape[0])
    ear_g = bilinear(ear_p, pu.ravel(), pv.ravel()).reshape(H, W) > .5   # (the soft mask sampled: a smooth outline)
    near_g = np.zeros((H, W), bool); near_g[inp] = sheet_skin[iv[inp], iu[inp]]
    d_ear = ndimage.distance_transform_edt(~ear_g) * SIDE_PX
    keep_skin = (d_ear < SIDE_EAR_PAD) | (near_g & (d_ear < SIDE_NEAR_EAR))
    ear_c = bilinear(ear_img, pu.ravel(), pv.ravel()).reshape(H, W, 3); ear_f = ndimage.gaussian_filter(keep_skin.astype(float), 2)
    vc = tex[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)]
    r_, g_, b_ = vc[:, 0], vc[:, 1], vc[:, 2]
    collar = ((g_ > r_ + 5) | ((vc.mean(1) > 165) & (r_ - b_ < 60) & (np.abs(r_ - g_) < 30))) & (Q[:, 1] < 1.555)   # (its teal and cream; higher up, the eyes' light greys)
    tri_ok = ~collar[I].all(1)
    near_collar = np.zeros(len(Q), bool); near_collar[I[collar[I].sum(1) >= 2].ravel()] = True
    first, weld, E = welded(Q, I)
    ue, cnt = np.unique(E, axis=0, return_counts=True); ne = np.zeros(len(first), bool); ne[ue[cnt == 1].ravel()] = True
    ne &= Q[first, 1] < 1.53   # (the head's bottom edge only: the hair's flaps' edges move)
    for _ in range(SIDE_EDGE_STEPS):
        gr = ne.copy(); gr[E[:, 0][ne[E[:, 1]]]] = True; gr[E[:, 1][ne[E[:, 0]]]] = True; ne = gr
    near_edge = ne[weld]
    eg, egm, eye_t = eyes(Q, UV, I, tex)
    z0, z1, y0, y1 = SIDE_WIN
    def side_tris(sg):
        C3 = Q[I].mean(1)
        return np.nonzero(tri_ok & (C3[:, 2] > z0) & (C3[:, 2] < z1) & (C3[:, 1] > y0) & (C3[:, 1] < y1) & (sg * (C3[:, 0] - X0) > .012))[0]
    Q0 = Q.copy(); design = {}; out = {}
    newa = np.zeros(len(Q)); moved = np.zeros(len(Q), bool); win_w = np.zeros(len(Q))
    for sg in (1, -1):
        amax, amin, tid, col = raster(Q, UV, I, tex, sg, side_tris(sg))
        on = amax > -9; H0 = on & is_hair(col)
        # the design (see above)
        lab, n = ndimage.label(H0); top = np.unique(lab[:SIDE_TOP_PX]); H0 = np.isin(lab, top[top > 0])
        C = np.where(gz < SIDE_TEMPLE_Z, clean(H0, SIDE_OPEN[0])[0], clean(H0, SIDE_OPEN[1])[0])
        M = np.where(wg > .02, C, H0) & on
        lab, n = ndimage.label(~M); sz = np.bincount(lab.ravel()); touch = np.zeros(n + 1, bool); touch[np.unique(lab[keep_skin])] = True
        M |= (sz < SIDE_HOLE)[lab] & ~touch[lab] & (lab > 0)
        M &= ~keep_skin
        lab, n = ndimage.label(M); sz = np.bincount(lab.ravel()); top = np.zeros(n + 1, bool); top[np.unique(lab[:SIDE_TOP_PX])] = True
        M &= (top | (sz >= SIDE_BIG))[lab] & (lab > 0)
        (ez0, ez1, ey0_, ey1_), er, eo, etip = SIDE_TEMPLE_EDGE   # (the temple's edge redrawn: see above)
        O = ndimage.binary_opening(M, structure=disk(eo)); Tt = tips(M, O, etip)[0]
        Ct = ndimage.gaussian_filter((O | (Tt & ndimage.binary_dilation(M, structure=disk(2)))).astype(float), SIDE_SOFT_EDGE) > .5
        tz = ss(ez0 - er, ez0, gz) * (1 - ss(ez1, ez1 + er, gz)) * ss(ey0_ - er, ey0_, gy) * (1 - ss(ey1_, ey1_ + er, gy))
        sdist = lambda A: ndimage.distance_transform_edt(A) - ndimage.distance_transform_edt(~A)
        M = ((tz * sdist(Ct) + (1 - tz) * sdist(M)) > 0) & on & ~keep_skin
        sd = (ndimage.distance_transform_edt(M) - ndimage.distance_transform_edt(~M)) * SIDE_PX   # (+ in the hair, m)
        _, ind = ndimage.distance_transform_edt(~H0, return_indices=True); hair_c = col[ind[0], ind[1]]
        clean_sk = on & ~is_hair(col) & (col[..., 0] > 200) & (col[..., 0] - col[..., 2] > 80) & (col.mean(-1) > 160)
        sk_map = np.stack([ndimage.gaussian_filter(laplace_fill(col[..., c], clean_sk, 150), 6) for c in range(3)], -1) if clean_sk.any() else np.broadcast_to(skin_rgb, col.shape).copy()
        hair_t = np.stack([ndimage.gaussian_filter(hair_c[..., c], SIDE_TEMPLE_TONE[0]) for c in range(3)], -1)   # (the temple's: one tone)
        (oz0, oz1, oy0, oy1) = SIDE_TEMPLE_TONE[1]
        tt = ndimage.gaussian_filter(((gz > oz0) & (gz < oz1) & (gy > oy0) & (gy < oy1)).astype(float), .004 / SIDE_PX)[..., None]; hair_c = hair_c * (1 - tt) + hair_t * tt
        img = np.where(M[..., None], hair_c, sk_map)
        flat = np.stack([ndimage.gaussian_filter(img[..., c], 1.5) for c in range(3)], -1)   # (for the walls: no lines)
        ink = ss(-SIDE_INK[1], SIDE_INK[1], sd) * (1 - ss(SIDE_INK[0] - SIDE_INK[1], SIDE_INK[0] + SIDE_INK[1], sd)) * ss(.0008, .0016, d_ear)
        img = img * (1 - ink[..., None]) + INK * ink[..., None]
        img = np.where(ear_g[..., None], ear_c, img)
        img = np.stack([ndimage.gaussian_filter(img[..., c], .6) for c in range(3)], -1)
        # the surface (see above)
        known = on & ~is_hair(col) & (col[..., 0] > 150) & (col[..., 0] - col[..., 2] > 55) & (amax - amin < .003) & (d_ear > .003)
        h_skin = ndimage.gaussian_filter(harmonic(np.where(known, amax, 0), known), 8)
        _, ind2 = ndimage.distance_transform_edt(~on, return_indices=True)
        h_out = ndimage.gaussian_filter(ndimage.median_filter(amax[ind2[0], ind2[1]], 7), 8)
        (cz0, cz1, cz2, cz3), (cy0, cy1), cs = SIDE_TEMPLE_CONE
        tw = ss(cz0, cz1, gz) * (1 - ss(cz2, cz3, gz)) * (1 - ss(cy0, cy1, gy)); slope = SIDE_CONE[1] + (cs - SIDE_CONE[1]) * tw
        cap = SIDE_CONE[0] + slope * np.maximum(sd, 0)
        h = ndimage.gaussian_filter(h_skin + SIDE_SKIN_UP + np.where(M, np.clip(h_out - h_skin - SIDE_SKIN_UP, 0, cap), 0), 4)
        design[sg] = (img, flat, h_skin, hair_c, sd)
        a = sg * (Q[:, 0] - X0); u, v = to_g(Q[:, 2], Q[:, 1])
        ing = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1) & (a > .012) & ~near_collar & ~near_edge & (Q[:, 1] > SIDE_FLOOR)
        k = np.nonzero(ing)[0]; uk, vk = u[k], v[k]; ak = a[k]
        wv = bilinear(wg, uk, vk) * egm[k]; hv = bilinear(h, uk, vk); sdk = bilinear(sd, uk, vk); sk_k = bilinear(h_skin, uk, vk) + SIDE_SKIN_UP
        (fz0, fz1, fy0, fy1), fh = SIDE_FLAP
        flap = (Q[k, 2] > fz0) & (Q[k, 2] < fz1) & (Q[k, 1] > fy0) & (Q[k, 1] < fy1) & (sdk < 0) & (ak - sk_k + SIDE_SKIN_UP > fh)
        wv = np.where(flap, np.maximum(wv, egm[k]), wv)
        hgt = ak - sk_k; capk = SIDE_CONE[0] + bilinear(slope, uk, vk) * np.maximum(sdk, 0)
        soft = -SIDE_CONE[2] * np.logaddexp(-hgt / SIDE_CONE[2], -capk / SIDE_CONE[2])
        hv = np.where(sdk > SIDE_DEEP, sk_k + np.minimum(soft, hgt), hv)
        win_w[k] = np.maximum(win_w[k], wv)
        hv = hv - SIDE_INSINK * (sg * N[k, 0] < -.2)
        sel = (wv > 1e-3) & (hv - ak < np.where(sdk > 0, 0, SIDE_RAISE)); k, wv, hv, ak = k[sel], wv[sel], hv[sel], ak[sel]
        newa[k] = ak + wv * (hv - ak); moved[k] = True
        out[sg] = int((np.abs(wv * (hv - ak)) > 2e-4).sum())
        if debug is not None: debug[sg] = dict(H0=H0, M=M, sd=sd, amax=amax, amin=amin, col=col, h=h, h_skin=h_skin, img=img, wg=wg)
    # (no triangle stretched: a point goes in no more than SIDE_STRETCH m per m of mesh from those that go less, or stay:
    # pressed alone, a lock's tip beside its unmoved root drew a long needle across the temple; the welded copies of a
    # point together)
    inward = np.zeros(len(Q))
    for sg in (1, -1):
        m = moved & (sg * (Q[:, 0] - X0) > .012); inward[m] = sg * (Q[m, 0] - X0) - newa[m]
    T = np.zeros(len(first)); np.maximum.at(T, weld, np.maximum(inward, 0))
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    Lw = np.linalg.norm(Q[first][E[:, 0]] - Q[first][E[:, 1]], axis=1) * SIDE_STRETCH + 1e-9
    nw = len(first); src = np.arange(nw)
    G = coo_matrix((np.r_[Lw, Lw, T + 1e-9], (np.r_[E[:, 0], E[:, 1], np.full(nw, nw)], np.r_[E[:, 1], E[:, 0], src])), shape=(nw + 1, nw + 1)).tocsr()
    lim = dijkstra(G, indices=nw)[:nw]
    for sg in (1, -1):
        m = moved & (sg * (Q[:, 0] - X0) > .012)
        go = np.where(inward[m] > 0, np.minimum(inward[m], lim[weld[m]]), inward[m])   # (the small raises as they are)
        Q[m, 0] = X0 + sg * (sg * (Q[m, 0] - X0) - go)
    Wq = np.zeros((len(first), 3)); Wn = np.zeros(len(first)); np.add.at(Wq, weld[moved], Q[moved]); np.add.at(Wn, weld[moved], 1)
    wm = Wn > 0; Wq[wm] /= Wn[wm, None]; sel = wm[weld]; Q[sel] = Wq[weld[sel]]
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); Nw = np.zeros((len(first), 3))
    for c in range(3): np.add.at(Nw, weld[I[:, c]], fn)
    Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12); N[sel] = Nw[weld[sel]]
    lb[:] = np.maximum(lb, SIDE_LINE * ss(.3, .7, win_w))
    (tx0, tx1), (ty0, ty1), (tz0, tz1), tpush, tramp = SIDE_TEMPLE; ax = np.abs(Q[:, 0] - X0)
    inside = np.minimum.reduce([ax - tx0, tx1 - ax, Q[:, 1] - ty0, ty1 - Q[:, 1], Q[:, 2] - tz0, tz1 - Q[:, 2]])
    temple_v = inside > 0; lb[:] = np.maximum(lb, tpush * np.clip(inside / tramp, 0, 1))
    # the paint (see above)
    cov = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(cov)
    for tr_ in UV[I] * TS: dr.polygon([tuple(v) for v in tr_], fill=255)
    covered = np.asarray(cov) > 0; painted = np.zeros((TS, TS), bool); n_px = 0
    fnu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    tmoved = np.abs(Q[:, 0] - Q0[:, 0])[I].max(1) > SIDE_MOVED
    for sg in (1, -1):
        img, flat, hsk, hcol, sdd = design[sg]
        a0 = sg * (Q0[:, 0] - X0); u0, v0 = to_g(Q0[:, 2], Q0[:, 1]); okg = (u0 >= 0) & (u0 < W - 1) & (v0 >= 0) & (v0 < H - 1)
        blade = np.zeros(len(Q), bool); blade[okg] = a0[okg] - bilinear(hsk, u0[okg], v0[okg]) > SIDE_LIFT
        for t in side_tris(sg):
            if eye_t[t]: continue
            a3 = sg * (Q[I[t], 0] - X0); u3, v3 = to_g(Q[I[t], 2], Q[I[t], 1])
            lifted = temple_v[I[t]].all() and (a3 - bilinear(hsk, u3, v3) > SIDE_LIFT).all()   # (a lock on the temple, standing out)
            tin = ((Q[I[t], 2] > ez0) & (Q[I[t], 2] < ez1) & (Q[I[t], 1] > ey0_) & (Q[I[t], 1] < ey1_)).all() and (bilinear(sdd, u3, v3) > .0005).all()
            if fnu[t, 2] > SIDE_FRONT and not tmoved[t] and not lifted and not tin: continue   # (the temple's skin under its hair: painted)
            fw = ss(SIDE_WALL[0], SIDE_WALL[1], abs(fnu[t, 0]))
            q, P3 = texels_wide(UV[I[t]] * TS, Q[I[t]], TS, covered)
            if not len(q): continue
            u, v = to_g(P3[:, 2], P3[:, 1]); ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
            q, u, v, P3 = q[ok], u[ok], v[ok], P3[ok]
            if not len(q): continue
            up = (sg * (P3[:, 0] - X0) - bilinear(hsk, u, v) > SIDE_LIFT) & (bilinear(ear_f, u, v) < .5)
            w = np.maximum(bilinear(wg, u, v), 1. if tmoved[t] else 0.)
            if lifted: w = np.where(up, 1., w)   # (the temple's locks standing out: hair, in front of the window's parts too)
            w = w * (eg[I[t]].max() if tmoved[t] and blade[I[t]].all() else eg[I[t]].min()); sel = w > 1e-3   # (a lock moved near the eye:
                                                                                            # painted, not left in Meshy's streaks)
            if not sel.any(): continue
            q, u, v, w, P3, up = q[sel], u[sel], v[sel], w[sel], P3[sel], up[sel]
            c0 = tex[q[:, 1], q[:, 0]]; d = bilinear(img, u, v) * fw + bilinear(flat, u, v) * (1 - fw)
            if up.any(): d[up] = bilinear(hcol, u[up], v[up])
            tex[q[:, 1], q[:, 0]] = c0 * (1 - w[:, None]) + d * w[:, None]
            painted[q[w > .5, 1], q[w > .5, 0]] = True; n_px += int((w > .5).sum())
    return out, n_px, painted


if __name__ == '__main__':
    d = sys.argv[1]
    h = json.load(open(os.path.join(d, 'ren_head.json'))); B = bytearray(open(os.path.join(d, 'ren_head.bin'), 'rb').read())
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    Q = f(h['pos']).reshape(-1, 3).astype(float); N = f(h['nor']).reshape(-1, 3).astype(float); UV = f(h['uv']).reshape(-1, 2).astype(float)
    I = f(h['idx'], np.uint32 if h['verts'] > 65535 else np.uint16).reshape(-1, 3).astype(np.int64); lb = f(h['lb']).astype(float).copy()
    tex = np.asarray(Image.open(os.path.join(d, 'ren_head.jpg')).convert('RGB')).astype(float).copy()
    TS = tex.shape[0]; vc = tex[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)]
    sk = (vc[:, 0] > 230) & (vc[:, 0] - vc[:, 2] > 90) & (np.abs(Q[:, 0] - X0) > .04) & (Q[:, 1] > 1.5)
    skin_rgb = np.median(vc[sk], 0); print('side skin', skin_rgb)
    dbg = {} if len(sys.argv) > 2 else None
    out, n, painted = sides(Q, N, UV, I, lb, tex, skin_rgb, debug=dbg)
    print('sides: points moved per side', out, '; texels painted', n)
    if dbg is not None: np.savez_compressed(sys.argv[2], **{'%s_%d' % (k, s): v for s in dbg for k, v in dbg[s].items()})
    def put(key, arr):
        o, cnt = h[key]; B[o:o + 4 * cnt] = np.ascontiguousarray(arr, np.float32).tobytes()
    put('pos', Q.ravel()); put('nor', N.ravel()); put('lb', lb)
    open(os.path.join(d, 'ren_head.bin'), 'wb').write(bytes(B))
    Image.fromarray(np.clip(tex, 0, 255).round().astype(np.uint8)).save(os.path.join(d, 'ren_head.jpg'), quality=88, optimize=True)
