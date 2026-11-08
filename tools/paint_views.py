#!/usr/bin/env python3
"""Paints Denis's other views of Ren onto the model, after tools/paint_from_drawing.py (the front drawing) (8/11/2026,
Denis with his body sheets: the rest of the body "disegnato come nelle immagini, senza cambiare proporzioni": only the
paint changes, never the shape).

usage: python3 tools/paint_views.py PACKAGE_DIR PAINTED.jpg [DEBUG_DIR]
  PACKAGE_DIR  the tools/meshy_pack.py package (its bind pose: the A-pose of the drawings)
  PAINTED.jpg  the texture paint_from_drawing.py wrote: painted over in place
  DEBUG_DIR    (optional) each view's fit: the model's projected outline on the sheet

The views (VIEWS; docs/ref/personaggi): the whole body from behind (ren_retro.png), the trousers and boots from three
quarters each side (ren_gambe_3viste.png, its side panels), the vest's sides from three quarters (ren_busto_3viste.png;
not the arms: drawn spread differently from the model's, their lines would land in the wrong places). Each view is the
bind pose seen orthographically from the direction d = (sin t, 0, cos t) (t = 180: from behind), its right (cos t, 0,
-sin t) along the sheet's columns: u = cx + s p.right, v = by - s p.y. The back view's scale and offset are fit to the
back view's silhouette (the most vertices inside it, as the front's); the side views' (t, s, cx, by) were fit once by
the materials (tools/paint_views.py --fit: the model drawn in its materials, correlated with the panel's) and are kept
in VIEWS.

A texel takes a view's colour where it faces that view and is seen from it (the triangle in front at its pixel, or one
of its neighbours), blended in by how much it faces it: the back view where it faces the back (BACK_FACE); a side view
where neither the front nor the back paints it (the front's and the back's weights, paint_from_drawing.py's and
BACK_FACE, leave the rest), the side it faces most. Each material keeps its own (the view's colour only where the view
shows the texel's material, its shades and folds, or one of the view's dark lines on a light material): the views'
orange tails, light edges or trim never land on the trousers or the boots' teal. Not the head (the new head replaces
it), the hands (drawn a little differently), the band (the drawing's band is at another height: the front's stays).
The wraps: their warm white with the view's lines only where they face the view well (as the front's).
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'ref', 'personaggi')
FRONT_FACE, BACK_FACE, BACK_SKIN = (.25, .55), (.25, .55), (.5, .72)
SIDE_FACE = (.1, .35)
WRAP_COL, WRAP_LINE, WRAP_FACE = np.array([230., 210, 202]), 8., (.55, .75)
BAND_Y = (1.08, 1.16)
LINE_LUM = 45
OTHER, SKIN, TEAL, DARK, LIGHT, ORANGE = range(6)
# (name, sheet, panel box (px), theta (deg), scale (px/m), cx, by, part: y range (m), arms too, the materials it paints)
VIEWS = [('back', 'ren_retro.png', None, 180., None, None, None, (-1., 9.), True, None),
         ('legs, +x', 'ren_gambe_3viste.png', (0, 0, 500, 950), 30., 650., 267.3, 902.6, (-1., 1.06), False, (DARK, TEAL, LIGHT)),
         ('legs, -x', 'ren_gambe_3viste.png', (1030, 0, 1536, 950), -30., 650., 242.8, 903.6, (-1., 1.06), False, (DARK, TEAL, LIGHT)),
         ('vest, +x', 'ren_busto_3viste.png', (0, 0, 520, 795), 47.5, 815.3, 247.1, 1356., (1.02, 9.), False, (TEAL,)),
         ('vest, -x', 'ren_busto_3viste.png', (1255, 0, 1774, 795), -47.5, 815.3, 260.1, 1356., (1.02, 9.), False, (TEAL,))]


def classes(c):
    """The material of each colour (n x 3): skin (with its shading), the vest's teal, dark (the trousers' purple grey, the
    boots' black, lines), light (wraps, trim, edges), orange (the sash), other."""
    r, g, b = c[:, 0], c[:, 1], c[:, 2]; lum = c.mean(1); out = np.full(len(c), OTHER)
    out[(lum < 110) & (np.abs(r - b) < 40) & (g <= r + 8)] = DARK
    out[(c.min(1) > 150) & (c.max(1) - c.min(1) < 60)] = LIGHT
    out[(g > r + 8) & (b > r + 8)] = TEAL
    out[(r > 110) & (r - b > 35) & (g >= .62 * r) & (c.min(1) <= 150)] = SKIN
    out[(r > 140) & (r - b > 90) & (g < .62 * r)] = ORANGE
    return out


def load(pkg):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2).astype(np.float64)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    J = f(me['jnt'], np.uint8).reshape(-1, 4); W = f(me['wgt']).reshape(-1, 4)
    bw = lambda keys: (np.isin(J, [i for i, b in enumerate(m['bones']) if any(k in b['n'] for k in keys)]) * W).sum(1)
    return (name, P, N, UV, I, bw(('Head',)), bw(('Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Pinky')), bw(('ForeArm',)),
            bw(('LeftArm', 'RightArm', 'ForeArm', 'Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Pinky')))


def sheet(path, box):
    D = np.asarray(Image.open(path).convert('RGB')).astype(np.float64)
    bg = D[5:40, 5:40].reshape(-1, 3).mean(0)
    if box: x0, y0, x1, y1 = box; D = D[y0:y1, x0:x1]
    mask = ndimage.binary_opening(np.abs(D - bg).sum(2) > 30, iterations=1)
    lab, n = ndimage.label(mask); sz = ndimage.sum(mask, lab, range(1, n + 1)); mask = np.isin(lab, np.nonzero(sz > 2000)[0] + 1)
    _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
    return D, mask, D[iy, ix]   # (outside the figure: the nearest drawn colour)


def fit_back(P, mask):
    """The back view: (share inside, scale px/m, cx, by), the most vertices inside its silhouette."""
    ys, xs = np.nonzero(mask); feet, top, mid = ys.max(), ys.min(), (xs.min() + xs.max()) / 2
    s0 = (feet - top) / (P[:, 1].max() - P[:, 1].min()); best = None; H, Wd = mask.shape
    for ds in np.arange(-.04, .041, .01):
        for dx in range(-12, 13, 3):
            for dy in range(-12, 13, 3):
                s = s0 * (1 + ds); u, v = mid + dx - P[:, 0] * s, feet + dy - P[:, 1] * s
                score = mask[np.clip(v.round().astype(int), 0, H - 1), np.clip(u.round().astype(int), 0, Wd - 1)].mean()
                if best is None or score > best[0]: best = (score, s, mid + dx, feet + dy)
    return best


def axes(theta):
    t = np.radians(theta); return np.array([np.cos(t), 0, -np.sin(t)]), np.array([np.sin(t), 0, np.cos(t)])


def seen_ids(P, I, sel, u, v, depth, H, Wd):
    """The triangle in front at each pixel (-1: none): the selected triangles drawn far to near."""
    idimg = Image.new('RGB', (Wd, H), (0, 0, 0)); dr = ImageDraw.Draw(idimg)
    idx = np.nonzero(sel)[0]
    for k in idx[np.argsort(depth[I[idx]].mean(1))]:
        c = k + 1; dr.polygon([(u[q], v[q]) for q in I[k]], fill=(c & 255, (c >> 8) & 255, (c >> 16) & 255))
    a = np.asarray(idimg).astype(np.int64); return a[..., 0] + (a[..., 1] << 8) + (a[..., 2] << 16) - 1


def texel_table(P, N, UV, I, TS):
    """Every texel inside a triangle's piece: (rows, cols, its triangle, barycentrics, 3D point, normal)."""
    uvimg = Image.new('RGB', (TS, TS), (0, 0, 0)); dr = ImageDraw.Draw(uvimg)
    for k, t in enumerate(I):
        c = k + 1; dr.polygon([(UV[q, 0] * TS, UV[q, 1] * TS) for q in t], fill=(c & 255, (c >> 8) & 255, (c >> 16) & 255))
    ua = np.asarray(uvimg).astype(np.int64); tid = ua[..., 0] + (ua[..., 1] << 8) + (ua[..., 2] << 16) - 1
    ys, xs = np.nonzero(tid >= 0); ks = tid[ys, xs]
    A = UV[I[ks, 0]] * TS; Bv = UV[I[ks, 1]] * TS; C = UV[I[ks, 2]] * TS; px = np.stack([xs + .5, ys + .5], 1)
    v0 = Bv - A; v1 = C - A; v2 = px - A
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01; den[np.abs(den) < 1e-12] = 1e-12
    bv = (d11 * d20 - d01 * d21) / den; bw_ = (d00 * d21 - d01 * d20) / den
    bary = np.clip(np.stack([1 - bv - bw_, bv, bw_], 1), 0, 1); bary /= bary.sum(1, keepdims=True)
    pos = (P[I[ks]] * bary[..., None]).sum(1); nor = (N[I[ks]] * bary[..., None]).sum(1); nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    return ys, xs, ks, bary, pos, nor


def main(pkg, painted, debug=None):
    name, P, N, UV, I, HEADW, HANDW, FOREW, ARMW = load(pkg)
    TEX = np.asarray(Image.open(painted).convert('RGB')).astype(np.float64); TS = TEX.shape[0]
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, TS)   # (the texels: their triangle, barycentrics, 3D point and normal)
    from collections import defaultdict
    vt = defaultdict(set)
    for k, t in enumerate(I):
        for q in t: vt[q].add(k)
    sm = lambda x, a, b: (lambda t: t * t * (3 - 2 * t))(np.clip((x - a) / (b - a), 0, 1))
    at = lambda W_: (W_[I[ks]] * bary).sum(1)
    hw, hdw, fw, aw = at(HEADW), at(HANDW), at(FOREW), at(ARMW)
    skip = (hw > .5) | (hdw > .5) | ((pos[:, 1] > BAND_Y[0]) & (pos[:, 1] < BAND_Y[1]))
    t0 = TEX[ys, xs]; ct = classes(t0); wrap = (np.abs(t0 - WRAP_COL).max(1) < 30) & ((fw > .5) | (pos[:, 1] < .32))
    skt = ct == SKIN
    out = TEX.copy(); w_front = sm(nor[:, 2], *FRONT_FACE); w_back = sm(-nor[:, 2], *BACK_FACE)
    side_best = np.full(len(ks), -1.); side_col = np.zeros((len(ks), 3)); side_w = np.zeros(len(ks))
    for vname, sh, box, theta, s, cx, by, (ylo, yhi), arms, mats in VIEWS:
        D, mask, Dfill = sheet(os.path.join(REF, sh), box); H, Wd = mask.shape
        r, d = axes(theta)
        if s is None:
            score, s, cx, by = fit_back(P, mask) if theta == 180 else (None,) * 4
            print('%s: fit %.1f%% of the vertices inside, %.1f px/m' % (vname, 100 * score, s))
        u, v = cx + s * (P @ r), by - s * P[:, 1]; depth = P @ d
        part_t = (P[I][:, :, 1] > ylo).any(1) & (P[I][:, :, 1] < yhi).any(1) & ((ARMW[I] < .5).all(1) | arms)
        seen = seen_ids(P, I, np.ones(len(I), bool) if theta == 180 else part_t | ((ARMW[I] >= .5).any(1)), u, v, depth, H, Wd)
        if debug:
            sil = seen >= 0; edge = sil & ~ndimage.binary_erosion(sil, iterations=2); o = D.copy(); o[edge] = (255, 0, 0)
            os.makedirs(debug, exist_ok=True); Image.fromarray(o.astype(np.uint8)).save(os.path.join(debug, vname.replace(', ', '_').replace('+', 'p').replace('-', 'm') + '.png'))
        pu = cx + s * (pos @ r); pv = by - s * pos[:, 1]
        pui = np.clip(pu.round().astype(int), 0, Wd - 1); pvi = np.clip(pv.round().astype(int), 0, H - 1)
        inside = (pu >= 0) & (pu < Wd) & (pv >= 0) & (pv < H)
        fid = seen[pvi, pui]; vis = (fid == ks) & inside
        for j in np.nonzero(~vis & (fid >= 0) & inside)[0]:
            if fid[j] in vt[I[ks[j], 0]] or fid[j] in vt[I[ks[j], 1]] or fid[j] in vt[I[ks[j], 2]]: vis[j] = True
        face = nor @ d
        inpart = (pos[:, 1] > ylo) & (pos[:, 1] < yhi) & ((aw < .5) | arms) & (np.isin(ct, mats) if mats else True)
        col = Dfill[pvi, pui]; cs = classes(col)
        same = (ct == cs) | ((cs == DARK) & (col.mean(1) < LINE_LUM) & np.isin(ct, (SKIN, TEAL, ORANGE)))
        acc = np.zeros((TS, TS)); cnt = np.zeros((TS, TS)); acc[ys, xs] = same; cnt[ys, xs] = 1
        accs = ndimage.gaussian_filter(acc, 1.) / np.maximum(ndimage.gaussian_filter(cnt, 1.), 1e-6)   # (no speckle at the materials' edges)
        keep_ = np.where(wrap, 1., np.clip((accs[ys, xs] - .5) * 3 + .5, 0, 1))
        keepl = np.clip((WRAP_COL.mean() - col.mean(1) - WRAP_LINE) / (WRAP_COL.mean() - 110), 0, 1) * sm(face, *WRAP_FACE)
        new = np.where(wrap[:, None], WRAP_COL * (1 - keepl[:, None]) + col * keepl[:, None], col)
        if theta == 180:
            w = sm(face, *BACK_FACE) * vis * ~skip * keep_; w[skt] *= sm(face[skt], *BACK_SKIN)
            out[ys, xs] = out[ys, xs] * (1 - w[:, None]) + new * w[:, None]
            print('%s: %d texels painted (%d facing it well); %d left as they were (another material there)' % (
                vname, int((w > 0).sum()), int((w > .5).sum()), int((~same & (sm(face, *BACK_FACE) * vis > .5)).sum())))
        else:   # (the side it faces most, where neither the front nor the back paints)
            w = np.clip(1 - w_front - w_back, 0, 1) * sm(face, *SIDE_FACE) * vis * inpart * ~skip * keep_
            better = (face > side_best) & (w > 0)
            side_best[better] = face[better]; side_col[better] = new[better]; side_w[better] = w[better]
            print('%s: %d texels it sees best (%d of them well)' % (vname, int(better.sum()), int((better & (w > .5)).sum())))
    sw = side_w[:, None]; out[ys, xs] = out[ys, xs] * (1 - sw) + side_col * sw
    print('sides: %d texels painted (%d well)' % (int((side_w > 0).sum()), int((side_w > .5).sum())))
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(painted, quality=85, optimize=True)   # (as paint_from_drawing.py)


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4): sys.exit(__doc__)
    main(*sys.argv[1:])
