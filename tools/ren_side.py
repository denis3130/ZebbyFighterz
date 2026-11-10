"""The sides of the new head clean around the ears, on the neck and on the cheeks (9-10/11/2026). Denis's detail sheet
(docs/ref/personaggi/ren_testa_dettagli.png, "togli tutto il necessario affinché sembri real come l'immagine") gave the
ear: seen, small as Meshy's ("ok l'orecchio ci sta", prova 1). Then: "fai meglio i capelli attorno alle orecchie e sul
collo, e quelli sulle guance; gli altri capelli non toccarli".

Meshy's head is one shell: on the sides its outer surface is the hair, with no scalp under it, and loose flaps of hair
hang over the face's and the neck's skin (the ragged strands). Cut, they opened holes. So:
- the hair is pressed onto the head as prova 1 did (press(): the sheet's profile, PRESS_WIN of its panel, its ear on
  Meshy's ear, tells where the side is skin; there the hair's points go to PRESS_SKIN_UP m over the skin under them (a ray
  along x; without skin under them, as their neighbours that have), and around it their height over it is no more than
  PRESS_CONE[0] m per m of distance from that skin (a slope), fading in front (PRESS_CONE[1..3]); none under
  PRESS_FLOOR m nor within PRESS_EDGE steps of the head's open edges; the outline of the moved points pushed back
  SIDE_LINE m);
- and painted along x with Meshy's own locks cleaned as a drawing is, in a window around the ear (SIDE_BOX, its edges
  fading over SIDE_EDGE m), seen from the side before the pressing (a picture SIDE_PX m per px, the outermost surface;
  the hair there is the dark joined to the hair above it, SIDE_TOP_PX: Meshy's dark marks on the neck are not hair):
  the hair's outline cleaned (strands thinner than 2 * SIDE_OPEN px off, their tips put back as clean points, SIDE_TIP;
  gaps narrower than 2 * SIDE_CLOSE px shut, specks and holes under SIDE_SPECK px gone, the edge smoothed); the ear the
  sheet's drawing and SIDE_EAR_PAD m of skin around it (and the sheet's skin within SIDE_NEAR_EAR of it); the skin plain
  (the skin's own tone around, its marks left out) where the hair went and SIDE_SKIN m around it, and from the hair's
  edge (the hair's shadows and specks there); the gaps between the locks in the hair's tone and an ink line SIDE_INK[0]
  m wide along the hair's edge, on the outermost surface only (the skin under a lock stays); the ear's drawing on the
  outermost surface facing the side (SIDE_EAR_FACE: its rim and what is behind it plain skin), no ink line along it (its
  drawing has its own); all of it only on the triangles facing the side (their normal's share along x over SIDE_FACE):
  the walls of the head's bumps keep their paint, not the side's stretched along them; but on the ear and the skin kept
  around it all of them (no hair's piece left on the ear).
sides() also returns the texels it painted and the hair's there: the neck's marks (ren_head.py, NECK_CLEAN) leave them
as they are.

usage (prototyping on a head already made): python3 tools/ren_side.py HEAD_DIR [DEBUG.npz]"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SIDE_SHEET = ('docs/ref/personaggi/ren_testa_dettagli.png', (1028, 0, 1536, 490))   # (the sheet, its profile panel: x0, y0, x1, y1 px)
SIDE_EAR = (273, 263, 317, 347)          # the ear in the panel (x0, y0, x1, y1 px)
SIDE_EAR_M = (-.008, 1.590, .042)        # where the drawn ear goes on the model: its centre (z, y m) and height (m): Meshy's
SIDE_BOX = (-.080, .042, 1.505, 1.640)   # the window: z from, to; y from, to (m: the collar under it)
SIDE_EDGE = .010                         # its edges (but the bottom: the collar) fade over this (m)
SIDE_PX = .00025                         # the side picture's m per px
SIDE_OPEN, SIDE_CLOSE = 7, 4             # px (see above)
SIDE_TIP = (10, .35, 8)                  # tips put back: at least [0] px long, their base's half width up to [1] of their length, [2] px apart
SIDE_SPECK = 160                         # px
SIDE_SOFT_EDGE = 1.5                     # px: the cleaned outline smoothed (a gaussian, cut at its half)
SIDE_EAR_PAD, SIDE_NEAR_EAR = .0005, .006   # m (see above)
PRESS_WIN, PRESS_DOWN = (190, 235, 345, 352), 1.46   # the panel's window (px); its skin row at the bottom carried down to this height (m)
PRESS_FLOOR, PRESS_EDGE = 1.52, 3        # m: no point under it moves (the neck in the collar: moved, its dark inside became the neck's marks);
                                         # nor any within this many steps of the head's open edges (its bottom: the collar's skirt hangs from it)
PRESS_SKIN_UP = .0015                    # m over the skin
PRESS_CONE = (1.2, .03, .05, .2, .002)   # the slope (m per m); its fade in front (z from, to: m) and the fade's rise; the soft minimum's width (m)
SIDE_EAR_FACE, SIDE_FACE = .3, (.15, .35)   # (see above: the normal's share along x)
SIDE_SKIN, SIDE_SPECKS = .003, .002       # m (see above); hair's colours left in the skin this near the hair painted skin
SIDE_TOP_PX = 12                         # px: the hair is the dark joined to the window's top rows
SIDE_INK = (.0007, .00015)               # m: the ink line's width, its edges' softness
SIDE_LINE, SIDE_GROW = .03, 2.5          # m; px of the painted triangles' texels around them, in the texture's gaps
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
    """The panel's ear (mask), its skin (mask) and its drawing in the head's colours (float (h, w, 3))."""
    k = sheet_classes()
    sk = (k == 1) | (k == 2); sk = ndimage.binary_closing(sk, iterations=2) | sk
    ex0, ey0, ex1, ey1 = SIDE_EAR
    ear = np.zeros_like(sk); ear[ey0 - 2:ey1 + 3, ex0 - 3:ex1 + 3] = (sk | (k == 3))[ey0 - 2:ey1 + 3, ex0 - 3:ex1 + 3]
    lab, n = ndimage.label(ear); cy, cx = (ey0 + ey1) // 2, (ex0 + ex1) // 2
    ear = lab == lab[cy, cx] if lab[cy, cx] else ear
    ear = ndimage.binary_fill_holes(ear)
    pal = np.array([HAIR[1], skin_rgb, np.asarray(skin_rgb) * SHADE, INK, HAIR[1], HAIR[2], HAIR[3]], float)
    img = np.stack([ndimage.gaussian_filter(pal[k][..., c], .8) for c in range(3)], -1)
    return ear, sk | ((k == 3) & ndimage.binary_dilation(sk, iterations=2)), img


def to_panel(z, y):
    """Model (z, y) -> panel (x, y) px (the ear on the model's)."""
    s = SIDE_EAR_M[2] / (SIDE_EAR[3] - SIDE_EAR[1]); cx, cy = (SIDE_EAR[0] + SIDE_EAR[2]) / 2, (SIDE_EAR[1] + SIDE_EAR[3]) / 2
    return cx + (SIDE_EAR_M[0] - z) / s, cy + (SIDE_EAR_M[1] - y) / s


# --- the side picture ---

def grid():
    """The window's picture: its size and model (z, y) -> px (u, v) and back."""
    z0, z1, y0, y1 = SIDE_BOX; m = .006
    W, H = int((z1 - z0 + 2 * m) / SIDE_PX), int((y1 - y0 + 2 * m) / SIDE_PX)
    return W, H, (lambda z, y: ((z - z0 + m) / SIDE_PX, (y1 + m - y) / SIDE_PX)), (lambda u, v: (u * SIDE_PX + z0 - m, y1 + m - v * SIDE_PX))


def weight(z, y):
    """1 in the window, fading to 0 over SIDE_EDGE at its front, back and top."""
    z0, z1, y0, y1 = SIDE_BOX
    return ss(z0, z0 + SIDE_EDGE, z) * (1 - ss(z1 - SIDE_EDGE, z1, z)) * (1 - ss(y1 - SIDE_EDGE, y1, y)) * (y > y0 - .004)


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


def tips(H, O):
    """Pointed triangles from O's edge out to the tips of H the opening cut (see SIDE_TIP)."""
    lmin, wfrac, supp = SIDE_TIP
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


def clean(H):
    """H (the hair seen) cleaned (see above)."""
    O = ndimage.binary_opening(H, structure=disk(SIDE_OPEN))
    T, nt = tips(H, O)
    C = O | (T & ndimage.binary_dilation(H, structure=disk(2)))
    C = ndimage.binary_closing(C, structure=disk(SIDE_CLOSE))
    lab, n = ndimage.label(C); sz = np.bincount(lab.ravel()); sz[0] = 0; C = (sz >= SIDE_SPECK)[lab] & (lab > 0)
    lab, n = ndimage.label(~C); sz = np.bincount(lab.ravel()); C |= (sz < SIDE_SPECK)[lab] & (lab > 0)
    return ndimage.gaussian_filter(C.astype(float), SIDE_SOFT_EDGE) > .5, nt


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
    ins = (w >= -1e-3).all(1) & g
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


def press(Q, N, UV, I, lb, tex):
    """The hair pressed onto the head as prova 1 did (see above). Moves Q, N, lb in place; returns per side the points
    moved, how many found skin under them, how many not."""
    from scipy.spatial import cKDTree
    k = sheet_classes(); H, Wd = k.shape; x0, y0, x1, y1 = PRESS_WIN
    sk = (k == 1) | (k == 2); sk = ndimage.binary_closing(sk, iterations=2) | sk
    skin = np.zeros_like(sk); skin[y0:y1, x0:x1] = (sk | ((k == 3) & ndimage.binary_dilation(sk, iterations=2)))[y0:y1, x0:x1]
    yd = int(np.ceil(to_panel(SIDE_EAR_M[0], PRESS_DOWN)[1])); ext = np.zeros((max(yd + 2, H), Wd), bool)
    ext[:H] = skin
    for yy in range(y1 - 1, yd + 1): ext[yy] = skin[y1 - 2]
    Hx = ext.shape[0]; d_out = ndimage.distance_transform_edt(~ext)
    TS = tex.shape[0]
    vc = tex[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)]
    skin_v = (vc[:, 0] > 150) & (vc[:, 0] - vc[:, 2] > 40)
    hair_v = ~skin_v & (vc.mean(1) < 130) & (vc[:, 0] >= vc[:, 1] - 4)   # (not the collar's teal nor its cream)
    _, first, weld = np.unique(np.round(Q / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    s = SIDE_EAR_M[2] / (SIDE_EAR[3] - SIDE_EAR[1]); cx, cy = (SIDE_EAR[0] + SIDE_EAR[2]) / 2, (SIDE_EAR[1] + SIDE_EAR[3]) / 2
    zb = SIDE_EAR_M[0] - (cx - x1) * s; yt = SIDE_EAR_M[1] + (cy - y0) * s
    moved = np.zeros(len(Q), bool); out = {}
    tri_skin = skin_v[I].sum(1) >= 2; Cq = Q[I].mean(1)
    # (the head's open edges, welded, and PRESS_EDGE steps around them)
    Tw = weld[I]; Ew = np.sort(np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]), 1)
    ue, cnt = np.unique(Ew, axis=0, return_counts=True); ne = np.zeros(len(first), bool); ne[ue[cnt == 1].ravel()] = True
    for _ in range(PRESS_EDGE):
        grow = ne.copy(); grow[Ew[:, 0][ne[Ew[:, 1]]]] = True; grow[Ew[:, 1][ne[Ew[:, 0]]]] = True; ne = grow
    near_edge = ne[weld]
    for sg in (1, -1):
        a = sg * (Q[:, 0] - X0)
        px, py = to_panel(Q[:, 2], Q[:, 1]); ix, iy = np.round(px).astype(int), np.round(py).astype(int)
        inw = (a > .025) & (ix >= 0) & (ix < Wd) & (iy >= 0) & (iy < Hx) & (Q[:, 2] < PRESS_CONE[2])
        dd = np.full(len(Q), np.inf); dd[inw] = d_out[iy[inw], ix[inw]]
        cap_all = PRESS_SKIN_UP + PRESS_CONE[0] * dd * s + PRESS_CONE[3] * ((Q[:, 2] - PRESS_CONE[1]) / (PRESS_CONE[2] - PRESS_CONE[1])).clip(0, None) ** 2
        cand = np.nonzero(inw & (cap_all < .05) & hair_v & (Q[:, 1] > PRESS_FLOOR) & ~near_edge)[0]
        # the skin under each: the nearest skin triangle on this side hit by a ray toward the middle (along x)
        st = np.nonzero(tri_skin & (sg * (Cq[:, 0] - X0) > .02) & (Cq[:, 2] < PRESS_CONE[2] + .03) & (Cq[:, 2] > zb - .08) & (Cq[:, 1] > PRESS_DOWN - .03) & (Cq[:, 1] < yt + .08))[0]
        A0 = Q[I[st, 0]]; E1 = Q[I[st, 1]] - A0; E2 = Q[I[st, 2]] - A0; dvec = np.array([-sg, 0., 0.])
        pv = np.cross(dvec, E2); det = (E1 * pv).sum(1); okd = np.abs(det) > 1e-14; inv = np.where(okd, 1 / np.where(okd, det, 1), 0)
        hit = np.full(len(Q), np.nan)
        for v in cand:
            tv = Q[v] - A0; u = (tv * pv).sum(1) * inv; qv = np.cross(tv, E1); w_ = (qv @ dvec) * inv; tt = (qv * E2).sum(1) * inv
            ok = okd & (u >= 0) & (w_ >= 0) & (u + w_ <= 1) & (tt > 1e-4) & (tt < .07)
            if ok.any(): hit[v] = a[v] - tt[ok].min()
        # (no skin under it: as the nearest that found some, in (z, y))
        good = cand[np.isfinite(hit[cand])]; bad = cand[~np.isfinite(hit[cand])]
        if len(good) and len(bad):
            dk, jk = cKDTree(Q[good][:, 1:]).query(Q[bad][:, 1:], k=min(6, len(good)))
            hit[bad] = np.median(hit[good][np.atleast_2d(jk)], 1)
        if not len(cand): out[sg] = (0, 0, 0); continue
        tgt = np.maximum(hit[cand], .03) + PRESS_SKIN_UP
        # (smoothed among themselves: the skin under the hair is ragged in places)
        nb = cKDTree(Q[cand][:, 1:]).query_ball_point(Q[cand][:, 1:], .006)
        for _ in range(3): tgt = np.array([np.median(tgt[j]) for j in nb])
        # (a soft minimum of where it is and the cap over the skin: no kink where the cap starts)
        th = a[cand] - (tgt - PRESS_SKIN_UP); cap = cap_all[cand]; kk_ = PRESS_CONE[4]
        newa = (tgt - PRESS_SKIN_UP) + np.minimum(-kk_ * np.logaddexp(-th / kk_, -cap / kk_), th)
        mv = a[cand] > newa + 2e-4
        Q[cand[mv], 0] = X0 + sg * newa[mv]; moved[cand[mv]] = True
        out[sg] = (int(mv.sum()), int(len(good)), int(len(bad)))
    # the welded copies of a moved point move with it
    Wq = np.zeros((len(first), 3)); Wn = np.zeros(len(first)); np.add.at(Wq, weld[moved], Q[moved]); np.add.at(Wn, weld[moved], 1)
    wm = Wn > 0; Wq[wm] /= Wn[wm, None]; sel = wm[weld]; Q[sel] = Wq[weld[sel]]; moved |= sel
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); Nw = np.zeros((len(first), 3))
    for c in range(3): np.add.at(Nw, weld[I[:, c]], fn)
    Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12); N[moved] = Nw[weld[moved]]
    lb[moved] = np.maximum(lb[moved], SIDE_LINE)
    return out


def sides(Q, N, UV, I, lb, tex, skin_rgb, debug=None):
    """Q, N, UV, I, lb: the head (positions, normals, uvs, triangles, outline push); tex: its texture (painted in place).
    Moves Q, N, lb in place; returns a summary per side, the texels painted (count) and their mask (TS, TS)."""
    skin_rgb = np.asarray(skin_rgb, float); TS = tex.shape[0]
    W, H, to_g, from_g = grid()
    gu, gv = np.meshgrid(np.arange(W) + .5, np.arange(H) + .5); gz, gy = from_g(gu, gv); wg = weight(gz, gy)
    ear_p, sheet_skin, ear_img = sheet_ear(skin_rgb)
    pu, pv = to_panel(gz, gy); iu, iv = np.round(pu).astype(int), np.round(pv).astype(int)
    inp = (iu >= 0) & (iu < ear_p.shape[1]) & (iv >= 0) & (iv < ear_p.shape[0])
    ear_g = np.zeros((H, W), bool); ear_g[inp] = ear_p[iv[inp], iu[inp]]
    near_g = np.zeros((H, W), bool); near_g[inp] = sheet_skin[iv[inp], iu[inp]]
    d_ear = ndimage.distance_transform_edt(~ear_g) * SIDE_PX
    keep_skin = (d_ear < SIDE_EAR_PAD) | (near_g & (d_ear < SIDE_NEAR_EAR))
    keep_f = ndimage.gaussian_filter(keep_skin.astype(float), 1.)
    vc = tex[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)]
    r_, g_, b_ = vc[:, 0], vc[:, 1], vc[:, 2]
    collar = (g_ > r_ + 5) | ((vc.mean(1) > 165) & (r_ - b_ < 60) & (np.abs(r_ - g_) < 30))   # (the collar's teal and cream, the shirt)
    tri_ok = ~collar[I].all(1)
    z0, z1, y0, y1 = SIDE_BOX
    def window_tris(sg):
        C3 = Q[I].mean(1)
        return np.nonzero(tri_ok & (C3[:, 2] > z0 - .008) & (C3[:, 2] < z1 + .008) & (C3[:, 1] > y0 - .008) & (C3[:, 1] < y1 + .008) & (sg * (C3[:, 0] - X0) > .012))[0]
    masks, out = {}, {}
    for sg in (1, -1):
        amax, amin, tid, col = raster(Q, UV, I, tex, sg, window_tris(sg))
        on = amax > -9; H0 = on & is_hair(col)
        # (the hair: the dark that hangs from the head's hair above the window, not Meshy's dark marks on the neck)
        lab_, n_ = ndimage.label(H0); top_ = np.unique(lab_[:SIDE_TOP_PX]); top_ = top_[top_ > 0]; H0 = np.isin(lab_, top_)
        C, nt = clean(H0)
        M = np.where(wg > .5, C, H0) & on & ~keep_skin
        # (the cleaned hair's signed distance from its edge, m: + in the hair)
        sd = (ndimage.distance_transform_edt(M) - ndimage.distance_transform_edt(~M)) * SIDE_PX
        # (the skin painted plain: where the hair went and around it, near the hair's edge)
        gone = H0 & ~M; d_gone = ndimage.distance_transform_edt(~gone) * SIDE_PX
        skz = ~M & ((sd > -SIDE_SKIN) | (d_gone < SIDE_SKIN))
        # (the skin's own tone around: its light, unmarked texels seen, carried over the rest)
        clean_sk = on & ~is_hair(col) & (col[..., 0] > 200) & (col[..., 0] - col[..., 2] > 80) & (col.mean(-1) > 160)
        sk_map = np.stack([ndimage.gaussian_filter(laplace_fill(col[..., c], clean_sk, 150), 6) for c in range(3)], -1) if clean_sk.any() else np.broadcast_to(skin_rgb, col.shape).copy()
        masks[sg] = (M, sd, skz, sk_map)
        out[sg] = dict(tips=nt, hair_px=int(H0.sum()), hair_after=int(M.sum()), skin_from_hair=int((H0 & ~M & (wg > .5)).sum()), hair_from_skin=int((M & ~H0).sum()))
        if debug is not None: debug[sg] = dict(H0=H0, C=C, M=M, sd=sd, amax=amax, col=col, on=on, wg=wg)
    pr = press(Q, N, UV, I, lb, tex)
    for sg in (1, -1): out[sg]['pressed'] = pr[sg]
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]])
    # the paint (the outermost surface seen again, after the moves)
    cov = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(cov)
    for tr_ in UV[I] * TS: dr.polygon([tuple(v) for v in tr_], fill=255)
    covered = np.asarray(cov) > 0
    painted = np.zeros((TS, TS), bool); n_px = 0
    fnu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    for sg in (1, -1):
        M, sd, skz, sk_map = masks[sg]; tris = window_tris(sg)
        amax = raster(Q, UV, I, tex, sg, tris)[0]
        sdl = ndimage.gaussian_filter(sd, .7); skf = ndimage.gaussian_filter(skz.astype(float), .7)
        for t in tris:
            face = fnu[t, 0] * sg; fw_t = ss(SIDE_FACE[0], SIDE_FACE[1], face)
            q, P3 = texels_wide(UV[I[t]] * TS, Q[I[t]], TS, covered)
            if not len(q): continue
            u, v = to_g(P3[:, 2], P3[:, 1]); w = weight(P3[:, 2], P3[:, 1])
            # (on the ear and the skin kept around it every triangle, the walls too: no hair's piece left on the ear)
            kz = bilinear(keep_f, u, v) > .5
            sel = (w > .5) & ((fw_t > 0) | kz)
            if not sel.any(): continue
            q, P3, u, v, w, kz = q[sel], P3[sel], u[sel], v[sel], w[sel], kz[sel]
            a = sg * (P3[:, 0] - X0); top = a > bilinear(amax, u, v) - .002   # (on the outermost surface)
            s_ = bilinear(sdl, u, v); c0 = tex[q[:, 1], q[:, 0]]; hc = is_hair(c0)
            pu_, pv_ = to_panel(P3[:, 2], P3[:, 1])
            ine = np.zeros(len(q), bool); ok_ = (pu_ >= 0) & (pu_ < ear_p.shape[1] - 1) & (pv_ >= 0) & (pv_ < ear_p.shape[0] - 1)
            ine[ok_] = ear_p[np.round(pv_[ok_]).astype(int), np.round(pu_[ok_]).astype(int)]
            new = c0.copy(); ch = np.zeros(len(q), bool)
            # the skin plain (and the hair's colours left in it near the hair)
            sk = (s_ < 0) & ((bilinear(skf, u, v) > .5) | (hc & (s_ > -SIDE_SPECKS)))
            skc = bilinear(sk_map, u, v); new[sk] = skc[sk]; ch |= sk
            # the gaps between the locks in the hair's tone (outermost only)
            gp = (s_ >= 0) & ~hc & top
            new[gp] = HAIR[1]; ch |= gp
            # the ink along the edge (outermost only)
            ink = ss(-SIDE_INK[1], SIDE_INK[1], s_) * (1 - ss(SIDE_INK[0] - SIDE_INK[1], SIDE_INK[0] + SIDE_INK[1], s_)) * top
            ink *= ss(.0008, .0016, bilinear(d_ear, u, v))   # (not along the ear: its drawing has its own line)
            li = ink > .01
            new[li] = new[li] * (1 - ink[li, None]) + INK * ink[li, None]; ch |= li
            # the ear: the sheet's drawing on the outermost surface facing the side, plain skin elsewhere
            if ine.any():
                fw = ss(SIDE_EAR_FACE - .1, SIDE_EAR_FACE + .1, face) * top[ine]
                new[ine] = bilinear(ear_img, pu_[ine], pv_[ine]) * fw[:, None] + skc[ine] * (1 - fw[:, None]); ch |= ine
            hz = (s_ >= 0) & (np.where(kz, 1., fw_t) > .5); painted[q[hz, 1], q[hz, 0]] = True   # (the hair's texels: the neck's marks leave them too)
            if not ch.any(): continue
            ww = (ss(.5, .8, w[ch]) * np.where(kz[ch], 1., fw_t))[:, None]
            tex[q[ch, 1], q[ch, 0]] = c0[ch] * (1 - ww) + new[ch] * ww
            painted[q[ch, 1], q[ch, 0]] |= ww[:, 0] > .5; n_px += int((ww > .5).sum())
    return out, n_px, painted


if __name__ == '__main__':
    d = sys.argv[1]; sys.path.insert(0, HERE)
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
    print('sides:', out, '; texels painted', n)
    if dbg is not None: np.savez_compressed(sys.argv[2], **{'%s_%d' % (k, s): v for s in dbg for k, v in dbg[s].items()})
    def put(key, arr):
        o, cnt = h[key]; B[o:o + 4 * cnt] = np.ascontiguousarray(arr, np.float32).tobytes()
    put('pos', Q.ravel()); put('nor', N.ravel()); put('lb', lb)
    open(os.path.join(d, 'ren_head.bin'), 'wb').write(bytes(B))
    Image.fromarray(np.clip(tex, 0, 255).round().astype(np.uint8)).save(os.path.join(d, 'ren_head.jpg'), quality=88, optimize=True)
