#!/usr/bin/env python3
"""The cameras of Denis's six head images of Kael, and (tried, not used) his hair reshaped to their outlines (10/11/2026,
Denis on the new head: "l'hai migliorato MA TROPPO POCO").

- The cameras, one per image (docs/ref/personaggi/kael_testa_<view>.png): fit on the face alone, by its skin (the hair
  differs), with tools/sheet_scan.py's fit (only the skin's triangles drawn, the others in front of them hiding them;
  the images' skin); written to docs/meshy/kael_head_cams.json (tools/kael_head.py paints the hair from the images
  through them) and read from there afterwards.
- The fit: the hair's points (by their paint, as tools/kael_head.py's; the face, the ears, the earrings and the collar
  stay) move so that the head's outline seen from each camera falls on the image's: each point on the outline in a view
  (within EDGE px of it) toward the image's outline along the outline's normal there (the distance found along that
  line, up to REACH px; the image's black line, LINE px, inside it). How (MODE): 'points', every point, the moves smooth
  over the mesh (SMOOTH; the outlines overlapped 86-90% instead of 81-85%, but the locks lost their points: a mop);
  'radial' and 'sweep', the mane as a whole scaled and its locks turned (smooth functions of the direction; 1-3%
  better); 'spikes', each lock's tip along the lock (1-3% better, ragged tips). Not used: the outlines overlapped 84%
  already, the difference was inside the hair (its tufts and their black edges), which the painting from the images
  answers. Prints, per view, how much the outlines overlap before and after.

usage: python3 tools/kael_hair_fit.py BUST.glb OUT.glb [--cams]   (BUST: the decimated bust; OUT: the same with its
hair moved; --cams: fit the cameras again)"""
import io, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.sparse import block_diag, csr_matrix, diags, identity, vstack
from scipy.sparse.linalg import spsolve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
import glbio
import kael_head as KH
from sheet_scan import classes, fit, BG_TOL

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CAMS = os.path.join(ROOT, 'docs/meshy/kael_head_cams.json')
VIEWS = (('fronte', (-8, 8)), ('34_dx', (-50, -10)), ('profilo_dx', (-100, -70)), ('dietro', (165, 195)),
         ('profilo_sx', (70, 100)), ('34_sx', (10, 50)))   # (the yaw's search range, degrees)
S_GUESS = 3900.                     # px per m
EDGE, REACH, LINE = 1.5, 160, 3     # px
SMOOTH, HOLD, STAY, ROUNDS, STEP = 3., 20., .05, 10, .008
# MODE (see the top): 'points', 'radial', 'sweep' or 'spikes'. 'radial' and 'sweep': the mane's reach beyond R0 m from CENTER (all of it from R1) scaled by a smooth function of the
# direction (polynomials up to DEG on the sphere), not in front of the face (the directions with z over FACE_Z, under
# FACE_Y up: the bangs over it); KEEP: the penalty on the moves (per point, against the outline's pulls)
MODE, CENTER, R0, R1, DEG, KEEP = 'spikes', (.008, 1.615, -.012), .075, .105, 4, .02
# MODE 'spikes' (see main): a tip is the hair's point farthest from CENTER within TIP_R m over the mesh; its lock the hair
# within LOCK_L m of it (moved less away from the tip); per round each tip goes along its lock's axis to where the images
# (the median over the views that see it on the outline) draw the mane's edge, at most SPIKE_OUT longer, SPIKE_IN shorter
# (m), SPIKE_GAIN of the way
TIP_R, LOCK_L, SPIKE_ROUNDS, SPIKE_OUT, SPIKE_IN, SPIKE_GAIN = .015, .04, 3, .04, .03, .7
DEG_TURN = 3                        # MODE 'sweep': the locks' turn about the head, a smooth function of the direction too
FACE_Z, FACE_Y = (.35, .6), (.45, .75)


def image(view):
    return np.asarray(Image.open(os.path.join(ROOT, 'docs/ref/personaggi/kael_testa_%s.png' % view)).convert('RGB')).astype(np.float64)


def figure(D):
    """The image's figure: not its background (the corner's colour)."""
    bg = np.median(D[5:40, 5:40].reshape(-1, 3), 0)
    return ndimage.binary_fill_holes(ndimage.binary_opening(np.abs(D - bg).sum(2) > BG_TOL, iterations=1))


def project(P, cam):
    t = np.radians(cam['yaw'])
    return cam['cx'] + cam['s'] * (P[:, 0] * np.cos(t) - P[:, 2] * np.sin(t)), cam['by'] - cam['s'] * P[:, 1]


def raster(u, v, I, W, H):
    im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
    for a, b, c in I: dr.polygon([(u[a], v[a]), (u[b], v[b]), (u[c], v[c])], fill=1)
    return np.asarray(im) > 0


def load(bust):
    m = glbio.read(bust); Pb, UV, I = m['pos'], m['uv'], m['idx']
    tex = Image.open(io.BytesIO(m['img'])).convert('RGB')
    if tex.size[0] > KH.HEAD_TEX: tex = tex.resize((KH.HEAD_TEX, KH.HEAD_TEX), Image.LANCZOS)
    T = np.asarray(tex).astype(np.float64); TS = T.shape[0]
    s, off, _, _ = KH.placement(); P = Pb * s + off
    at = lambda uv: T[np.clip((uv[..., 1] * TS).astype(int), 0, TS - 1), np.clip((uv[..., 0] * TS).astype(int), 0, TS - 1)]
    return m, s, off, P, UV, I, at(UV), at(UV[I].mean(1))


def cameras(P, I, tc):
    """Per view: the camera that puts the model's face's skin on the image's (yaw, s px per m, cx, by px)."""
    mat = (classes(tc) == 1).astype(np.uint8)   # (skin 1; the rest 0: drawn over the skin behind it)
    out = {}
    for view, yr in VIEWS:
        D = image(view); F = figure(D); Fc = np.where(F & (classes(D) == 1), 1, 0).astype(np.uint8)
        sc, yaw, s, cx, by, ious, names = fit(P, I, mat, Fc, yr, (-10 ** 6, 10 ** 6), S_GUESS)
        out[view] = {'yaw': yaw, 's': s, 'cx': cx, 'by': by, 'skin_iou': ious[0]}
        print('camera %s: yaw %.0f, %.0f px/m, cx %.1f, by %.1f; the skin overlaps %.0f%%' % (view, yaw, s, cx, by, 100 * ious[0]))
    json.dump(out, open(CAMS, 'w'), indent=1)
    return out


def iou(a, b):
    return (a & b).sum() / max((a | b).sum(), 1)


def main(bust, out, refit=False):
    m, s_b, off, P, UV, I, vc, tc = load(bust)
    cams = cameras(P, I, tc) if refit or not os.path.exists(CAMS) else json.load(open(CAMS))
    # what moves: the hair (not the earrings' boxes, the collar)
    C = (P[I].mean(1) - off) / s_b   # (the triangles' middles, bust units)
    ear_t = np.zeros(len(I), bool)
    for (x0, x1), (y0, y1), (z0, z1) in KH.BUST['ears']:
        ear_t |= (C[:, 0] > x0) & (C[:, 0] < x1) & (C[:, 1] > y0) & (C[:, 1] < y1) & (C[:, 2] > z0) & (C[:, 2] < z1)
    ear_v = np.zeros(len(P), bool); ear_v[I[ear_t].ravel()] = True
    hair = KH.is_hair(vc) & ~KH.is_skin(vc) & ~ear_v & ~(KH.is_cloth(vc) & (P[:, 1] < KH.JAW_Y + .01))
    # welded (the copies along the texture's seams move as one)
    _, first, inv = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    nw = len(first); X = P[first].copy(); Tw = inv[I]
    free = np.zeros(nw, bool); np.logical_or.at(free, inv, hair)
    fixed = np.zeros(nw, bool); np.logical_or.at(fixed, inv, ~hair); free &= ~fixed   # (a point on hair and on skin: held)
    E = np.unique(np.sort(np.concatenate([Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]), 1), axis=0)
    A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw))
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1); L = identity(nw, format='csr') - diags(1 / deg) @ A
    print('hair: %d of %d points move' % (int(free.sum()), nw))
    views = []
    for view, _ in VIEWS:
        D = image(view); F = figure(D); H, W = F.shape
        Fin = ndimage.binary_erosion(F, iterations=LINE)   # (the model's outline is drawn outside its edge: the image's line inside it)
        views.append((view, cams[view], Fin, H, W))
    def overlap(X):
        res = {}
        for view, cam, Fin, H, W in views:
            u, v = project(X, cam); res[view] = iou(raster(u, v, Tw, W, H), Fin)
        return res
    before = overlap(X)
    def constraints(X):
        """The outline's points of the hair in every view: (their point, the 3D direction in the view's plane, the move
        along it that puts them on the image's outline, m)."""
        ks, n3s, ts = [], [], []
        for view, cam, Fin, H, W in views:
            u, v = project(X, cam); M = raster(u, v, Tw, W, H)
            din = ndimage.distance_transform_edt(M); dout = ndimage.distance_transform_edt(~M)
            gy, gx = np.gradient(ndimage.gaussian_filter(dout - din, 2.))   # (the model's outline: its normal)
            ui, vi = np.clip(np.round(u).astype(int), 0, W - 1), np.clip(np.round(v).astype(int), 0, H - 1)
            k = np.nonzero(free & (din[vi, ui] <= EDGE) & (u >= 0) & (u < W) & (v >= 0) & (v < H))[0]
            nu, nv = gx[vi[k], ui[k]], gy[vi[k], ui[k]]; nn = np.hypot(nu, nv); ok = nn > 1e-6
            k, nu, nv = k[ok], nu[ok] / nn[ok], nv[ok] / nn[ok]
            st = np.arange(0, REACH + 1)
            inside = lambda a, b: Fin[np.clip(np.round(b).astype(int), 0, H - 1), np.clip(np.round(a).astype(int), 0, W - 1)] & (a >= 0) & (a < W) & (b >= 0) & (b < H)
            Ao = inside(u[k, None] + nu[:, None] * st[None], v[k, None] + nv[:, None] * st[None])   # (outward)
            Ai = inside(u[k, None] - nu[:, None] * st[None], v[k, None] - nv[:, None] * st[None])   # (inward)
            here = Ao[:, 0]
            t_out = np.where((~Ao).any(1), np.argmax(~Ao, 1), -1); t_in = np.where(Ai.any(1), np.argmax(Ai, 1), -1)
            t = np.where(here, t_out, -t_in).astype(float); good = np.where(here, t_out >= 0, t_in >= 0) & (np.abs(t) >= 1)
            k, nu, nv, t = k[good], nu[good], nv[good], t[good]
            th = np.radians(cam['yaw']); right = np.array([np.cos(th), 0, -np.sin(th)])
            ks.append(k); n3s.append(nu[:, None] * right[None] - nv[:, None] * np.array([0., 1., 0.])[None]); ts.append(t / cam['s'])
        return np.concatenate(ks), np.concatenate(n3s), np.concatenate(ts)
    if MODE == 'radial':   # the mane as a whole: its reach beyond the scalp scaled by a smooth function of the direction
        X0 = X.copy(); c = np.array(CENTER); rel = X0 - c; r0 = np.linalg.norm(rel, axis=1); om = rel / np.maximum(r0[:, None], 1e-9)
        sm = lambda e0, e1, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - e0) / (e1 - e0), 0, 1))
        wgt = free * sm(R0, R1, r0) * (1 - sm(FACE_Z[0], FACE_Z[1], om[:, 2]) * (1 - sm(FACE_Y[0], FACE_Y[1], om[:, 1])))
        ex = [(a, b_, g) for a in range(DEG + 1) for b_ in range(DEG + 1 - a) for g in range(DEG + 1 - a - b_)]
        Bas = np.stack([om[:, 0] ** a * om[:, 1] ** b_ * om[:, 2] ** g for a, b_, g in ex], 1)   # (polynomials on the sphere: its harmonics up to DEG)
        reach = (wgt * np.maximum(r0 - R0, 0))[:, None] * om   # (the move per unit of the function, along the direction)
        coef = np.zeros(len(ex)); mv = np.nonzero(wgt > 0)[0]
        for rnd in range(ROUNDS):
            k, n3, t = constraints(X)
            J = ((n3 * reach[k]).sum(1))[:, None] * Bas[k]   # (each constraint's row: d(n3 . move)/d coef)
            G = reach[mv][:, :, None] * Bas[mv][:, None, :]   # (the moves' size, for the penalty)
            Areg = np.sqrt(KEEP) * G.reshape(-1, len(ex))
            Mt = np.vstack([J, Areg]); bt = np.r_[t, -np.sqrt(KEEP) * (G.reshape(-1, len(ex)) @ coef)]
            dc = np.linalg.lstsq(Mt, bt, rcond=None)[0]
            dmax = np.abs(reach[mv] * (Bas[mv] @ dc)[:, None]).max()
            if dmax > STEP: dc *= STEP / dmax
            coef += dc; X = X0 + reach * (Bas @ coef)[:, None]
            print('round %d: %d outline points pulled (%.1f mm on average); the mane moved up to %.1f mm' % (
                rnd + 1, len(k), 1000 * np.abs(t).mean(), 1000 * np.linalg.norm(X - X0, axis=1).max()))
    elif MODE == 'spikes':   # each lock's tip pulled out or in along the lock, to where the images draw the mane's edge
        import heapq
        Ew = np.linalg.norm(X[E[:, 0]] - X[E[:, 1]], axis=1); nbr = [[] for _ in range(nw)]
        for (a, b_), w_ in zip(E, Ew): nbr[a].append((b_, w_)); nbr[b_].append((a, w_))
        def reach_of(s0, lim):   # (the hair within lim m of s0 over the mesh: its distances)
            dist = {s0: 0.}; h = [(0., s0)]
            while h:
                d0, u0 = heapq.heappop(h)
                if d0 > dist.get(u0, 9e9) or d0 > lim: continue
                for v0, w0 in nbr[u0]:
                    if free[v0] and d0 + w0 < dist.get(v0, 9e9) and d0 + w0 <= lim: dist[v0] = d0 + w0; heapq.heappush(h, (d0 + w0, v0))
            return dist
        c = np.array(CENTER); r = np.linalg.norm(X - c, axis=1)
        cand = np.nonzero(free & (r > np.percentile(r[free], 40)))[0]
        tips = [v0 for v0 in cand if all(r[u0] <= r[v0] for u0 in reach_of(v0, TIP_R))]
        locks = []
        for tp in tips:   # (each tip's lock: the hair within LOCK_L of it, its axis from the far half's middle to the tip)
            reg = reach_of(tp, LOCK_L); far = [u0 for u0, d0 in reg.items() if d0 > .5 * LOCK_L]
            if len(far) < 3: continue
            ax = X[tp] - X[far].mean(0); ln = np.linalg.norm(ax)
            if ln < 1e-6: continue
            ids = np.array(list(reg.keys())); gd = np.array([reg[u0] for u0 in ids])
            locks.append((tp, ax / ln, ids, (1 - gd / LOCK_L) ** 2))
        print('locks: %d tips' % len(locks))
        X0 = X.copy()
        for rnd in range(SPIKE_ROUNDS):
            ext = np.full(len(locks), np.nan); per = []
            for view, cam, Fin, H, W in views:
                u, v = project(X, cam); M = raster(u, v, Tw, W, H); din = ndimage.distance_transform_edt(M)
                th = np.radians(cam['yaw']); right = np.array([np.cos(th), 0, -np.sin(th)])
                vals = np.full(len(locks), np.nan)
                for j, (tp, ax, ids, wv) in enumerate(locks):
                    ui, vi = int(round(u[tp])), int(round(v[tp]))
                    if not (0 <= ui < W and 0 <= vi < H) or din[vi, ui] > EDGE + 1: continue   # (only where its tip is on the outline)
                    a2 = np.array([ax @ right, -ax[1]]); la = np.linalg.norm(a2)
                    if la < .5: continue   # (the lock seen end-on)
                    a2 /= la; st = np.arange(0, REACH + 1)
                    pu, pv = u[tp] + a2[0] * st, v[tp] + a2[1] * st; qu, qv = u[tp] - a2[0] * st, v[tp] - a2[1] * st
                    ins = lambda a_, b2: Fin[np.clip(np.round(b2).astype(int), 0, H - 1), np.clip(np.round(a_).astype(int), 0, W - 1)] & (a_ >= 0) & (a_ < W) & (b2 >= 0) & (b2 < H)
                    io_, ii = ins(pu, pv), ins(qu, qv)
                    if io_[0]:
                        if (~io_).any(): vals[j] = np.argmax(~io_) / (cam['s'] * la)    # (the image's mane goes on: out)
                    elif ii.any(): vals[j] = -np.argmax(ii) / (cam['s'] * la)            # (the tip past the image's edge: in)
                per.append(vals)
            Vv = np.array(per); ext = np.nanmedian(np.where(np.isnan(Vv), np.nan, Vv), 0) if len(per) else ext
            disp = np.zeros((nw, 3)); wmax = np.zeros(nw); n_out = n_in = 0
            for j, (tp, ax, ids, wv) in enumerate(locks):
                e = ext[j]
                if not np.isfinite(e) or abs(e) < 1e-3: continue
                e = float(np.clip(e, -SPIKE_IN, SPIKE_OUT)) * SPIKE_GAIN; n_out += e > 0; n_in += e < 0
                upd = wv > wmax[ids]; wmax[ids[upd]] = wv[upd]; disp[ids[upd]] = ax[None] * e * wv[upd, None]
            X = X + disp
            print('round %d: %d locks longer, %d shorter (%.1f mm on average)' % (rnd + 1, n_out, n_in, 1000 * np.abs(disp[wmax > .99]).max(1).mean() if (wmax > .99).any() else 0))
    elif MODE == 'sweep':   # the mane's reach scaled (as 'radial') and its locks turned about the head (their tips swept)
        X0 = X.copy(); c = np.array(CENTER); q0 = X0 - c; r0 = np.linalg.norm(q0, axis=1); om = q0 / np.maximum(r0[:, None], 1e-9)
        sm = lambda e0, e1, x: (lambda q: q * q * (3 - 2 * q))(np.clip((x - e0) / (e1 - e0), 0, 1))
        wgt = free * sm(R0, R1, r0) * (1 - sm(FACE_Z[0], FACE_Z[1], om[:, 2]) * (1 - sm(FACE_Y[0], FACE_Y[1], om[:, 1])))
        basis = lambda deg: np.stack([om[:, 0] ** a * om[:, 1] ** b_ * om[:, 2] ** g for a in range(deg + 1) for b_ in range(deg + 1 - a) for g in range(deg + 1 - a - b_)], 1)
        Br, Bt = basis(DEG), basis(DEG_TURN); nr, nt = Br.shape[1], Bt.shape[1]
        reach = wgt * np.maximum(r0 - R0, 0)
        cr = np.zeros(nr); ct = np.zeros((3, nt)); mv = np.nonzero(wgt > 0)[0]
        def place(cr, ct):
            q1 = q0 + (reach * (Br @ cr))[:, None] * om   # (the reach)
            th = wgt[:, None] * (Bt @ ct.T)              # (the turn, per point: a rotation vector)
            ang = np.linalg.norm(th, axis=1); ax = th / np.maximum(ang[:, None], 1e-12)
            cs, sn = np.cos(ang)[:, None], np.sin(ang)[:, None]
            q2 = q1 * cs + np.cross(ax, q1) * sn + ax * (ax * q1).sum(1, keepdims=True) * (1 - cs)   # (Rodrigues)
            return c + q2
        for rnd in range(ROUNDS):
            X = place(cr, ct); k, n3, t = constraints(X)
            qk = X[k] - c; dirk = qk / np.maximum(np.linalg.norm(qk, axis=1, keepdims=True), 1e-9)
            Jr = ((n3 * dirk).sum(1) * reach[k])[:, None] * Br[k]
            Jt = [((n3 * np.cross(np.eye(3)[a][None], qk)).sum(1) * wgt[k])[:, None] * Bt[k] for a in range(3)]
            J = np.hstack([Jr] + Jt)
            qm = X[mv] - c; dm = qm / np.maximum(np.linalg.norm(qm, axis=1, keepdims=True), 1e-9)
            G = [(reach[mv][:, None] * dm)[:, :, None] * Br[mv][:, None, :]] + [(wgt[mv][:, None] * np.cross(np.eye(3)[a][None], qm))[:, :, None] * Bt[mv][:, None, :] for a in range(3)]
            G = np.concatenate(G, 2).reshape(-1, nr + 3 * nt)
            Mt = np.vstack([J, np.sqrt(KEEP) * G]); bt = np.r_[t, np.zeros(len(G))]
            dc = np.linalg.lstsq(Mt, bt, rcond=None)[0]
            dmax = np.abs(G @ dc).max()
            if dmax > STEP: dc *= STEP / dmax
            cr += dc[:nr]; ct += dc[nr:].reshape(3, nt)
            Xn = place(cr, ct)
            print('round %d: %d outline points pulled (%.1f mm on average); the mane moved up to %.1f mm' % (
                rnd + 1, len(k), 1000 * np.abs(t).mean(), 1000 * np.linalg.norm(Xn - X0, axis=1).max()))
        X = place(cr, ct)
    else:   # every point free, the moves smooth (the outlines closer, the locks lost their points: a mop)
        for rnd in range(ROUNDS):
            k, n3, t = constraints(X); nc = len(k)
            R = csr_matrix((n3.T.ravel(), (np.tile(np.arange(nc), 3), np.r_[k, nw + k, 2 * nw + k])), shape=(nc, 3 * nw))
            Lblk = block_diag([SMOOTH * L] * 3, format='csr'); Hblk = diags(np.tile(np.where(free, STAY, HOLD), 3))
            Mtx = vstack([R, Lblk, Hblk]).tocsr(); rhs_all = np.concatenate([t, np.zeros(6 * nw)])
            d = spsolve((Mtx.T @ Mtx).tocsc(), Mtx.T @ rhs_all).reshape(3, nw).T
            ln = np.linalg.norm(d, axis=1); d *= np.minimum(1, STEP / np.maximum(ln, 1e-12))[:, None]
            X += d
            print('round %d: %d outline points pulled (%.1f mm on average)' % (rnd + 1, nc, 1000 * np.abs(t).mean()))
    after = overlap(X)
    for view, _ in VIEWS: print('%s: the outlines overlap %.1f%% -> %.1f%%' % (view, 100 * before[view], 100 * after[view]))
    # back to the bust's units, its normals renewed (area weighted, over the welded points)
    fn = np.cross(X[Tw[:, 1]] - X[Tw[:, 0]], X[Tw[:, 2]] - X[Tw[:, 0]]); acc = np.zeros((nw, 3))
    for c in range(3): np.add.at(acc, Tw[:, c], fn)
    Nw = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    moved = np.linalg.norm(X - P[first], axis=1) > 1e-7
    N = m['nor'].copy(); sel = moved[inv]; N[sel] = Nw[inv[sel]]
    glbio.write(out, m, (X[inv] - off) / s_b, N, UV, I)
    print('written %s: %d points moved (%.1f mm on average, at most %.1f)' % (out, int(moved.sum()), 1000 * np.linalg.norm(X - P[first], axis=1)[moved].mean(), 1000 * np.linalg.norm(X - P[first], axis=1).max()))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2: sys.exit(__doc__)
    main(args[0], args[1], '--cams' in sys.argv)
