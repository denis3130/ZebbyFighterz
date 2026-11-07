#!/usr/bin/env python3
"""Paints Denis's drawing onto a packed model's texture by front projection (7/11/2026, the "Ren dipinto" proposal).

usage: python3 tools/paint_from_drawing.py PACKAGE_DIR DRAWING.png OUT.jpg
  PACKAGE_DIR  a tools/meshy_pack.py output folder (name.json, name.bin, name.jpg, name = the folder's name)
  DRAWING      the front character sheet, on a flat background (its top-left corner is the background colour)

The model's bind pose (A-pose, the one Meshy built from this same drawing) is projected orthographically from the front
onto the drawing with the scale and offset that put the most vertices inside the drawn silhouette. Every texel whose
surface faces the viewer and is visible from the front takes the drawing's colour (blended in by how much it faces
the front); the others keep the model's own texture. Outside the drawn silhouette the nearest drawn colour is used,
so model edges that stick out a little take the drawing's outline. On the hands (the drawing's are spread a little
differently) a texel that came out neither skin nor a dark line (the wraps' white, the background's grey on the
fingertips) takes the colour of the nearest skin texel of the hands instead. The texels between the UV pieces take
their nearest piece's colour at the end. On the face (the head's skin) the drawing
is kept only where the surface faces the front squarely, plain skin where it turns away: the drawing's edges stretched
over the sides of the nose and the jaw read as dirt. The hair, likewise: the drawing where it faces the front, the
hair's own colour elsewhere (the highlights stretched over its sides looked like horns; Meshy's white glints). The
sash's tails (ribbons of their own in the look) take the colour of what is under them.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def load(pkg):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2).astype(np.float64)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    J = f(me['jnt'], np.uint8).reshape(-1, 4); W = f(me['wgt']).reshape(-1, 4)
    hands = [i for i, b in enumerate(m['bones']) if b['n'] in ('LeftHand', 'RightHand')]
    head = [i for i, b in enumerate(m['bones']) if b['n'] == 'Head']
    return name, P, N, UV, I, (np.isin(J, hands) * W).sum(1), (np.isin(J, head) * W).sum(1)


if len(sys.argv) != 4: sys.exit(__doc__)
PKG, DRAWING, OUT = sys.argv[1:]
name, P, N, UV, I, HANDW, HEADW = load(PKG)
D = np.asarray(Image.open(DRAWING).convert('RGB')).astype(np.float64)
H, Wd = D.shape[:2]
bg = D[5:40, 5:40].reshape(-1, 3).mean(0)
mask = np.abs(D - bg).sum(2) > 30
mask = ndimage.binary_opening(mask, iterations=1)
# background bled with the nearest character colour (model edges a little outside the drawing get its outline)
_, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
Dfill = D[iy, ix]

# --- global alignment: scale + offset maximising the silhouette overlap ---
def project(s, cx, by): return cx + P[:, 0] * s, by - P[:, 1] * s
ys_, xs_ = np.nonzero(mask); feet, top, mid = ys_.max(), ys_.min(), (xs_.min() + xs_.max()) / 2
s0 = (feet - top) / (P[:, 1].max() - P[:, 1].min()); best = None
for ds in (-.02, -.01, 0, .01, .02):
    for dx in (-8, -4, 0, 4, 8):
        for dy in (-8, -4, 0, 4, 8):
            s = s0 * (1 + ds); u, v = project(s, mid + dx, feet + dy)
            # cheap IoU on vertices: share of projected vertices inside the drawing mask
            ui = np.clip(u.round().astype(int), 0, Wd - 1); vi = np.clip(v.round().astype(int), 0, H - 1)
            score = mask[vi, ui].mean()
            if best is None or score > best[0]: best = (score, s, mid + dx, feet + dy)
print('alignment (vertices inside the drawing):', best)
_, s, cx, by = best
u, v = project(s, cx, by)

# --- front visibility: triangle ids drawn far to near ---
zc = P[I].mean(1)[:, 2]; order = np.argsort(zc)
idimg = Image.new('RGB', (Wd, H), (0, 0, 0)); dr = ImageDraw.Draw(idimg)
for k in order:
    t = I[k]; c = k + 1
    dr.polygon([(u[q], v[q]) for q in t], fill=(c & 255, (c >> 8) & 255, (c >> 16) & 255))
ida = np.asarray(idimg).astype(np.int64); front = ida[..., 0] + (ida[..., 1] << 8) + (ida[..., 2] << 16) - 1
# neighbours of each triangle (sharing a vertex) count as visible too (seams of the raster)
from collections import defaultdict
vt = defaultdict(set)
for k, t in enumerate(I):
    for q in t: vt[q].add(k)

# --- UV-space raster of the triangles ---
TEX = np.asarray(Image.open(os.path.join(PKG, name + '.jpg')).convert('RGB')).astype(np.float64)
TS = TEX.shape[0]
uvimg = Image.new('RGB', (TS, TS), (0, 0, 0)); dr = ImageDraw.Draw(uvimg)
for k, t in enumerate(I):
    c = k + 1; dr.polygon([(UV[q, 0] * TS, UV[q, 1] * TS) for q in t], fill=(c & 255, (c >> 8) & 255, (c >> 16) & 255))
ua = np.asarray(uvimg).astype(np.int64); tid = ua[..., 0] + (ua[..., 1] << 8) + (ua[..., 2] << 16) - 1
ys, xs = np.nonzero(tid >= 0); ks = tid[ys, xs]
# barycentrics of each texel in its triangle (UV space)
A = UV[I[ks, 0]] * TS; Bv = UV[I[ks, 1]] * TS; C = UV[I[ks, 2]] * TS
px = np.stack([xs + .5, ys + .5], 1)
v0 = Bv - A; v1 = C - A; v2 = px - A
d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
den = d00 * d11 - d01 * d01; den[np.abs(den) < 1e-12] = 1e-12
bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
bary = np.clip(np.stack([bu, bv, bw], 1), 0, 1); bary /= bary.sum(1, keepdims=True)
pos = (P[I[ks]] * bary[..., None]).sum(1); nor = (N[I[ks]] * bary[..., None]).sum(1)
nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
pu = cx + pos[:, 0] * s; pv = by - pos[:, 1] * s
pui = np.clip(pu.round().astype(int), 0, Wd - 1); pvi = np.clip(pv.round().astype(int), 0, H - 1)
fid = front[pvi, pui]
vis = (fid == ks)
near = ~vis & (fid >= 0)
for j in np.nonzero(near)[0]:
    if fid[j] in vt[I[ks[j], 0]] or fid[j] in vt[I[ks[j], 1]] or fid[j] in vt[I[ks[j], 2]]: vis[j] = True
face = np.clip((nor[:, 2] - .25) / .3, 0, 1); face = face * face * (3 - 2 * face)
wgt = face * vis
col = Dfill[pvi, pui]
out = TEX.copy()
out[ys, xs] = TEX[ys, xs] * (1 - wgt[:, None]) + col * wgt[:, None]
# --- the face: the drawing where the head's skin faces the front, its skin colour where it turns away ---
sk = lambda c: (c[:, 0] > 120) & (c[:, 1] > 75) & (c[:, 0] - c[:, 2] > 40)
facet = ((HEADW[I[ks]] * bary).sum(1) > .5) & sk(TEX[ys, xs])
fw = np.clip((nor[:, 2] - .45) / .2, 0, 1); fw = fw * fw * (3 - 2 * fw) * vis
pick = facet & (fw > .9) & sk(col)
skin_col = np.median(col[pick], 0) if pick.any() else np.array([246., 181, 131])
out[ys[facet], xs[facet]] = col[facet] * fw[facet, None] + skin_col * (1 - fw[facet, None])
print('face texels', int(facet.sum()), 'drawn (front) ', int((facet & (fw > .5)).sum()), 'skin', np.round(skin_col))
# --- the hair: the drawing where it faces the front, elsewhere the hair's own colour (no stretched highlights at the
# sides, no Meshy glints) ---
# (the hair: the head's texels that are neither skin nor the vest's teal, from the hair's lowest point up: the collar's
# teal and its light trim below stay)
tc = TEX[ys, xs]; hv = ((HEADW[I[ks]] * bary).sum(1) > .5) & ~sk(tc); teal = tc[:, 1] > tc[:, 0] + 8
like = hv & ~teal & (tc.mean(1) <= 110); hairt = hv & ~teal & (pos[:, 1] >= np.percentile(pos[like, 1], 1))
hair_col = np.median(tc[like], 0)
hw = np.clip((nor[:, 2] - .35) / .25, 0, 1); hw = hw * hw * (3 - 2 * hw) * vis
out[ys[hairt], xs[hairt]] = col[hairt] * hw[hairt, None] + hair_col * (1 - hw[hairt, None])
print('hair texels', int(hairt.sum()), 'drawn (front)', int((hairt & (hw > .5)).sum()), 'hair colour', np.round(hair_col))
# --- the sash's tails: hanging ribbons in the look (tools/ren_look.py), so off the body: each tail texel takes the colour
# of the nearest texel (in space) that is not orange, the trousers or the vest under it ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ren_look import sash_tails, sash_orange, sash_band_end, SASH_BAND
vcol = TEX[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)].astype(int)
tv = np.zeros(len(P), bool)
for t in sash_tails(P, vcol, I): tv[t] = True
for _ in range(2):   # the tails' darker edges too: two rings of neighbours
    tv2 = tv.copy(); tv2[I[tv[I].any(1)].ravel()] = True; tv = tv2
c = out[ys, xs]; orng = (c[:, 0] > 85) & (c[:, 0] > c[:, 1]) & (c[:, 0] - c[:, 2] > 55)   # warm: orange to its brown shadows
low = (pos[:, 1] < SASH_BAND) & (np.abs(pos[:, 0]) < .33)
tt = ((tv[I[ks]].sum(1) >= 2) & low) | (orng & low)    # the model's tails, and the drawing's painted below the band
# the drawing without its tails: each tail pixel (with its lines, a few px around) takes the colour of the nearest
# pixel of the vest or the trousers beside it (not a black line): flat colours, split down the middle of the tail
od = sash_orange(D); od[:sash_band_end(od) + 6] = False
od = ndimage.binary_dilation(ndimage.binary_closing(od, iterations=2), iterations=4)
warm = (D[..., 0] > 80) & (D[..., 0] > D[..., 1]) & (D[..., 0] - D[..., 2] > 40)   # the tails' orange edges, shadows
src = ndimage.binary_erosion(mask, iterations=3) & ~od & ~warm & (D.sum(2) > 150)   # not the light anti-aliased edge either
_, (sy, sx) = ndimage.distance_transform_edt(~src, return_indices=True)
out[ys[tt], xs[tt]] = D[sy, sx][pvi[tt], pui[tt]]
print('sash tail texels repainted', int(tt.sum()))
# --- the hands: neither skin nor a dark line -> the nearest skin texel of the hands ---
c = out[ys, xs]; hand = (HANDW[I[ks]] * bary).sum(1) > .5
skin = (c[:, 0] > 150) & (c[:, 1] > 95) & (c[:, 0] - c[:, 2] > 50); dark = c.sum(1) < 240
good = np.zeros((TS, TS), bool); good[ys[hand & skin], xs[hand & skin]] = True
_, (gy, gx) = ndimage.distance_transform_edt(~good, return_indices=True)
bad = hand & ~skin & ~dark
out[ys[bad], xs[bad]] = out[gy[ys[bad], xs[bad]], gx[ys[bad], xs[bad]]]
print('texels', len(ks), 'painted (w>.5)', int((wgt > .5).sum()), 'visible', int(vis.sum()), 'hand texels recoloured', int(bad.sum()), 'of', int(hand.sum()))
# --- padding: every texel outside the triangles takes its nearest triangle texel's colour (the gutters between UV pieces
# kept Meshy's old colours, which showed as thin cracks along the seams once filtered, the sash's orange most of all) ---
inside = tid >= 0
_, (gy, gx) = ndimage.distance_transform_edt(~inside, return_indices=True)
out[~inside] = out[gy[~inside], gx[~inside]]
Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(OUT, quality=85, optimize=True)
print(OUT, os.path.getsize(OUT))
