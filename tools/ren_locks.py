"""The locks on the sides of the new head drawn with their black contours (10/11/2026, night; Denis, on two photos of the
head's sides: "vorrei che i capelli avessero più ciocche coi contorni neri come i capelli sopra").

On top of the head Meshy's locks stand apart: the outline draws their edges. On the sides they lie close over each other
(a few mm apart: under the outline's push back) and the hair there is painted in its flat tones (ren_hair.head_sides,
ren_side.sides): the locks are in the shape (seen in its normals) but not seen. Here, per side, in a window (LOCK_WIN: z
from, to; y from, to, m) seen along x (a picture SIDE_PX m per px: the outermost surface's depth, triangle and colour):
- where the outermost surface steps down by more than LOCK_STEP[0] m to a neighbour (the edge of a lock lying over
  another), a black line along the step, on the upper lock (not the one under it), LOCK_W[0] to LOCK_W[1] m wide by
  the step's size (full at LOCK_STEP[1]: the lines thin out toward the locks' tips, as an outline does);
- only on the hair (its colours: not the skin, the ear, the collar), not on the eyes nor beside them (LOCK_EYE m), not
  on edges shorter than LOCK_MIN m (specks), and fading out above LOCK_TOP[0] over LOCK_TOP[1] m (the top: its outline
  draws it); the steps are taken on the surface as it is and as it was before ren_side pressed the flaps (LOCK_IN m and
  more inside the hair: the locks it laid flat keep their contours);
- painted in the texels of the triangles facing that side (their normal's share along x over LOCK_FACE) that are the
  outermost surface there (within LOCK_DEPTH m of it: a lock under it keeps its paint).
locks() returns the texels it painted (count, mask): the neck's clean (ren_head.py, NECK_CLEAN) leaves them.

usage (prototyping on a head already made): python3 tools/ren_locks.py HEAD_DIR"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ren_side import SIDE_PX, X0, INK, is_hair, ss, bilinear, texels_wide, eyes

LOCK_WIN = (-.125, .10, 1.50, 1.77)      # the window: z from, to; y from, to (m)
LOCK_STEP = (.001, .005)                 # m: a step over [0] is a lock's edge; its line full width from [1]
LOCK_W = (.0008, .0026)                  # m: the line's width, at the smallest step and at the full one
LOCK_IN = .003                           # m: see lines()
LOCK_MIN = .004                          # m: a lock's edge shorter than this is not lined (specks)
LOCK_TOP = (1.70, .02)                   # m: the lines fade out above [0] over [1]
LOCK_EYE = .006                          # m: no line within this of an eye's triangle (in the picture)
LOCK_FACE, LOCK_DEPTH = .2, .0015        # see above


def _grid():
    z0, z1, y0, y1 = LOCK_WIN
    W, H = int((z1 - z0) / SIDE_PX), int((y1 - y0) / SIDE_PX)
    return W, H, (lambda z, y: ((z - z0) / SIDE_PX, (y1 - y) / SIDE_PX))


def _raster(Q, UV, I, tex, sg, tris):
    """The window seen from side sg along x: per px the outermost surface's depth |x - X0|, its triangle and colour."""
    W, H, to_g = _grid(); TS = tex.shape[0]
    amax = np.full((H, W), -9.); tid = np.full((H, W), -1, np.int64); col = np.zeros((H, W, 3))
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
    return amax, tid, col


def _steps(amax):
    """Per px how far the outermost surface steps down to its lowest neighbour (m; 0 off the head)."""
    on = amax > -9; step = np.zeros(amax.shape)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        b = np.roll(np.roll(amax, dy, 0), dx, 1); onb = np.roll(np.roll(on, dy, 0), dx, 1)
        step = np.maximum(step, np.where(on & onb, amax - b, 0))
    return step


def lines(amax, col, tid, eye_t, amax0=None):
    """The lines' share per px of the picture (see above); amax0: the outermost surface before ren_side pressed the
    flaps (its steps taken too, LOCK_IN m and more inside the hair: the locks it laid flat keep their contours)."""
    H, W = amax.shape; on = amax > -9
    hair = on & is_hair(col)
    step = _steps(amax)
    if amax0 is not None:
        c = col.astype(float); skin = on & ~hair & (c[..., 0] > 140) & (c[..., 0] - c[..., 2] > 45)
        deep = hair & (ndimage.distance_transform_edt(~skin) * SIDE_PX > LOCK_IN)
        step = np.maximum(step, np.where(deep, _steps(amax0), 0))
    st = hair & (step > LOCK_STEP[0])
    lab, n = ndimage.label(st, structure=np.ones((3, 3))); sz = np.bincount(lab.ravel()); sz[0] = 0
    st &= (sz >= LOCK_MIN / SIDE_PX)[lab]   # (not the specks: steps shorter than LOCK_MIN m along)
    if not st.any(): return np.zeros((H, W))
    w = LOCK_W[0] + (LOCK_W[1] - LOCK_W[0]) * np.clip((step - LOCK_STEP[0]) / (LOCK_STEP[1] - LOCK_STEP[0]), 0, 1)
    dist, ind = ndimage.distance_transform_edt(~st, return_indices=True)
    wn = np.where(st, w, 0)[ind[0], ind[1]] / SIDE_PX
    a_ = amax if amax0 is None else np.where(amax0 > -9, amax0, amax)   # (the side of the step the lock is on: before the press)
    under = a_ < a_[ind[0], ind[1]] - LOCK_STEP[0] * .5   # (the lock under the step: not lined)
    al = np.clip(wn - dist + .5, 0, 1) * hair * ~under
    eye = np.isin(tid, np.nonzero(eye_t)[0]) & on
    if eye.any(): al *= ndimage.distance_transform_edt(~eye) * SIDE_PX > LOCK_EYE
    yy = LOCK_WIN[3] - (np.arange(H) + .5)[:, None] * SIDE_PX
    return al * (1 - ss(LOCK_TOP[0], LOCK_TOP[0] + LOCK_TOP[1], yy))


def locks(Q, UV, I, tex, Q0=None):
    """Q, UV, I: the head (positions, uvs, triangles); tex: its texture, painted in place; Q0: its positions before
    ren_side.sides() (see lines()). Returns the texels painted (count) and their mask (TS, TS)."""
    TS = tex.shape[0]; W, H, to_g = _grid(); z0, z1, y0, y1 = LOCK_WIN
    _, _, eye_t = eyes(Q, UV, I, tex)
    fn = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]]); fnu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    cov = Image.new('L', (TS, TS), 0); dr = ImageDraw.Draw(cov)
    for tr_ in UV[I] * TS: dr.polygon([tuple(v) for v in tr_], fill=255)
    covered = np.asarray(cov) > 0; painted = np.zeros((TS, TS), bool); n_px = 0
    C3 = Q[I].mean(1)
    for sg in (1, -1):
        tris = np.nonzero((C3[:, 2] > z0 - .01) & (C3[:, 2] < z1 + .01) & (C3[:, 1] > y0 - .01) & (C3[:, 1] < y1 + .01) & (sg * (C3[:, 0] - X0) > .012))[0]
        amax, tid, col = _raster(Q, UV, I, tex, sg, tris)
        amax0 = _raster(Q0, UV, I, tex, sg, tris)[0] if Q0 is not None else None
        al = lines(amax, col, tid, eye_t, amax0)
        for t in tris:
            if sg * fnu[t, 0] < LOCK_FACE or eye_t[t]: continue
            q, P3 = texels_wide(UV[I[t]] * TS, Q[I[t]], TS, covered)
            if not len(q): continue
            u, v = to_g(P3[:, 2], P3[:, 1]); ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
            q, u, v, P3 = q[ok], u[ok], v[ok], P3[ok]
            if not len(q): continue
            w = bilinear(al, u, v)
            top = amax[np.clip(v.astype(int), 0, H - 1), np.clip(u.astype(int), 0, W - 1)]
            w = w * (sg * (P3[:, 0] - X0) > top - LOCK_DEPTH)
            c0 = tex[q[:, 1], q[:, 0]]; w = w * is_hair(c0)
            sel = w > 1e-3
            if not sel.any(): continue
            q, w, c0 = q[sel], w[sel], c0[sel]
            tex[q[:, 1], q[:, 0]] = c0 * (1 - w[:, None]) + INK * w[:, None]
            painted[q[w > .5, 1], q[w > .5, 0]] = True; n_px += int((w > .5).sum())
    return n_px, painted


if __name__ == '__main__':
    d = sys.argv[1]
    h = json.load(open(os.path.join(d, 'ren_head.json'))); B = open(os.path.join(d, 'ren_head.bin'), 'rb').read()
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    Q = f(h['pos']).reshape(-1, 3).astype(float); UV = f(h['uv']).reshape(-1, 2).astype(float)
    I = f(h['idx'], np.uint32 if h['verts'] > 65535 else np.uint16).reshape(-1, 3).astype(np.int64)
    tex = np.asarray(Image.open(os.path.join(d, 'ren_head.jpg')).convert('RGB')).astype(float).copy()
    n, _ = locks(Q, UV, I, tex)
    print('locks: %d texels of the locks\' contours painted' % n)
    Image.fromarray(np.clip(tex, 0, 255).round().astype(np.uint8)).save(os.path.join(d, 'ren_head.jpg'), quality=88, optimize=True)
