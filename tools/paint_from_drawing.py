#!/usr/bin/env python3
"""Paints Denis's drawing onto a packed model's texture by front projection (7/11/2026, the "Ren dipinto" proposal).

usage: python3 tools/paint_from_drawing.py PACKAGE_DIR DRAWING.png OUT.jpg
  PACKAGE_DIR  a tools/meshy_pack.py output folder (name.json, name.bin, name.jpg, name = the folder's name)
  DRAWING      the front character sheet, on a flat background (its top-left corner is the background colour)
  writes OUT.jpg and, beside it, <name>_face.png: the face decal (the drawn face's features, see below)

The model's bind pose (A-pose, the one Meshy built from this same drawing) is projected orthographically from the front
onto the drawing with the scale and offset that put the most vertices inside the drawn silhouette. Every texel whose
surface faces the viewer and is visible from the front takes the drawing's colour (blended in by how much it faces
the front); the others keep the model's own texture. Outside the drawn silhouette the nearest drawn colour is used,
so model edges that stick out a little take the drawing's outline. On the hands (the drawing's are spread a little
differently) a texel that came out neither skin nor a dark line (the wraps' white, the background's grey on the
fingertips) takes the colour of the nearest skin texel of the hands instead. The texels between the UV pieces take
their nearest piece's colour at the end. The face is clean skin in the texture: its
features (eyes, brows, the nose's shadow, the mouth) are the face decal, laid on by tools/ren_look.py face_uv (Meshy left
the face only a few scattered texels). The hair: the drawing where it faces the front, the
hair's own colour elsewhere (the highlights stretched over its sides looked like horns; Meshy's white glints). The
sash's tails (ribbons of their own in the look) take the colour of what is under them; on the band and the vest just
under it the thin dark lines go. The model's shape is the look's (tools/ren_look.py drawn_shape: the face smooth with a
small nose, the fringe off the eyes, the collar's points). The collar is flat like the drawing's where the drawing does not reach it (its
teal, in shadow where Meshy's folds are darker; no glossy glints), the drawing is painted on the body's skin only where
it faces the front well (turned away, its lines stretched into streaks), and the drawing's background between its hair
locks is never a colour of the head.
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
    head = [i for i, b in enumerate(m['bones']) if b['n'] == 'Head']; neck = [i for i, b in enumerate(m['bones']) if b['n'] == 'neck']
    return name, P, N, UV, I, (np.isin(J, hands) * W).sum(1), (np.isin(J, head) * W).sum(1), (np.isin(J, neck) * W).sum(1)


if len(sys.argv) != 4: sys.exit(__doc__)
PKG, DRAWING, OUT = sys.argv[1:]
name, P, N, UV, I, HANDW, HEADW, NECKW = load(PKG)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ren_look import drawn_shape, drawing_fit, drawing_band, sash_tails, sash_orange, sash_band_end, SASH_BAND, FACE_X, FACE_DECAL, \
    head_skin, neck_zone
# the shape as the model draws it (ren_look.drawn_shape: a small nose, the fringe off the eyes, the collar's points)
T0 = np.asarray(Image.open(os.path.join(PKG, name + '.jpg')).convert('RGB')).astype(int)
P, N, _ = drawn_shape(P, N, I, HEADW, T0[np.clip((UV[:, 1] * T0.shape[0]).astype(int), 0, T0.shape[0] - 1), np.clip((UV[:, 0] * T0.shape[1]).astype(int), 0, T0.shape[1] - 1)])
D = np.asarray(Image.open(DRAWING).convert('RGB')).astype(np.float64)
H, Wd = D.shape[:2]
bg = D[5:40, 5:40].reshape(-1, 3).mean(0)
mask = np.abs(D - bg).sum(2) > 30
mask = ndimage.binary_opening(mask, iterations=1)
# background bled with the nearest character colour (model edges a little outside the drawing get its outline)
_, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
Dfill = D[iy, ix]

# --- global alignment: scale + offset maximising the silhouette overlap (tools/ren_look.py places the sash's ribbons
# with it too) ---
def project(s, cx, by): return cx + P[:, 0] * s, by - P[:, 1] * s
best = drawing_fit(P, mask)
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
# --- the body's skin (arms, chest, neck; not the head, not the hands): the drawing only where it faces the front well
# (SKIN_FRONT: the normal's z from where it starts to where it is all), Meshy's paint where it turns away (Denis, 7/11:
# "le righe del disegno sembrano graffi": turned away, the drawing's muscle lines stretched into streaks) ---
SKIN_FRONT = (.5, .72)
tsk = TEX[ys, xs]; skb = (tsk[:, 0] > 120) & (tsk[:, 1] > 75) & (tsk[:, 0] - tsk[:, 2] > 40) & (tsk[:, 1] > .6 * tsk[:, 0])   # (not the sash's orange)
skb &= ((HEADW[I[ks]] * bary).sum(1) < .5) & ((HANDW[I[ks]] * bary).sum(1) < .5)
ws = np.clip((nor[:, 2] - SKIN_FRONT[0]) / (SKIN_FRONT[1] - SKIN_FRONT[0]), 0, 1); ws = ws * ws * (3 - 2 * ws) * vis
csk = (col[:, 0] > 150) & (col[:, 1] > 95) & (col[:, 0] - col[:, 2] > 50) & (col[:, 1] > .62 * col[:, 0])
skin_body = np.median(col[skb & (ws > .9) & csk], 0)
out[ys[skb], xs[skb]] = col[skb] * ws[skb, None] + TEX[ys[skb], xs[skb]] * (1 - ws[skb, None])
print('body skin texels', int(skb.sum()), 'drawn (front)', int((skb & (ws > .5)).sum()), 'skin', np.round(skin_body))
# --- the collar flat as the drawing's (Denis, 7/11: "il colletto opaco"): where the drawing does not reach it, its teal
# lit or in shadow where Meshy painted its folds darker, instead of Meshy's glossy shading and white glints (it looked
# like a shiny tube); its light rim (Meshy's) a dark edge. The rest of the vest as Meshy painted it (Denis: the vest all
# flat "si fonde con le spalle") ---
VEST, VEST_SHADE, VEST_FOLD = np.array([66., 107, 113]), .72, .85
tc = TEX[ys, xs]; lum = tc.mean(1); collar = (pos[:, 1] > 1.42) & (np.hypot(pos[:, 0], pos[:, 2] + .01) < .17)
vest = (tc[:, 1] > tc[:, 0] + 10) & (tc[:, 2] > tc[:, 0] + 10) & collar
rim = (tc.min(1) > 125) & (tc.max(1) - tc.min(1) < 45) & collar & ((HEADW[I[ks]] * bary).sum(1) < .9)
two = np.where((lum < np.median(lum[vest]) * VEST_FOLD)[:, None], VEST * VEST_SHADE, VEST)
two[rim] = VEST * VEST_SHADE   # a dark edge (the drawing's light lining, on the round collar's top fold, read as a glint too)
vr = vest | rim
# on the vest the drawing gives its teal and its dark lines and shadows; anything else is the drawing's background, its
# collar's lining or the neck's skin where the model's collar stands higher or wider than the drawn one (on the round
# collar they showed as white glints)
okv = ((col[:, 1] > col[:, 0] + 8) & (col[:, 2] > col[:, 0] + 8)) | (col.mean(1) < 70)
colv = np.where(okv[:, None], col, two)
out[ys[vr], xs[vr]] = colv[vr] * wgt[vr, None] + two[vr] * (1 - wgt[vr, None])
print('collar texels', int(vest.sum()), 'in its flat teal where the drawing is not (%d), its rim %d' % (int((vest & (wgt < .5)).sum()), int(rim.sum())))
# --- the face (Denis, 7/11: "la faccia è troppo buggata"): its skin clean, in the drawing's skin colour; the drawn
# face's features (FACE_ZONES, drawing pixels: the eyes and brows, the lock between the eyes, the nose's shadow and
# nostril, the mouth, the mark on the cheek; each pixel by how far its colour is from the skin's, FACE_INK) in a texture
# of their own, the face decal (<name>_face.png: the drawing's ren_look.FACE_DECAL box, laid on the face by
# ren_look.face_uv): Meshy left the nose and the mouth only a few texels (painted here, they came out blurred, in
# blocks). The rest of the drawn face (its jaw's outline, the hair's strands and shadows over it) stretched over the
# model's face as dirt ---
FACE_INK = (18., 60.)
FACE_ZONES = [([(464, 151), (474, 151), (503, 164), (503, 181), (468, 181), (464, 172)], 0),   # left eye and brow
              ([(515, 164), (546, 151), (556, 151), (556, 172), (552, 181), (515, 181)], 0),   # right eye and brow
              ([(500, 146), (517, 146), (512, 181), (505, 181)], 0),               # the lock between the eyes
              ([(496, 190), (518, 190), (520, 206), (494, 206)], 1),               # the nose: its shadow and nostril (small;
              ([(493, 208), (528, 208), (528, 223), (493, 223)], 0),               # its light edge, a pink facet, left out)
              ([(534, 185), (550, 185), (550, 198), (534, 198)], 0)]               # the mark on the cheek; 1: darker only
sk = lambda c: (c[:, 0] > 120) & (c[:, 1] > 75) & (c[:, 0] - c[:, 2] > 40)
# the face: the head's skin, and all of the head in front of the ears from the brows down, the jaw's sides and underside
# too (Meshy painted its own eyes, lower, in dark colours: as hair they showed as dark bands under the drawn eyes; the
# drawing's jaw outline, stretched over the jaw's sides, as a dark stepped streak)
facez = (np.abs(pos[:, 0] - FACE_X) < .056) & (pos[:, 1] > 1.46) & (pos[:, 1] < 1.60) & (pos[:, 2] > -.05)
VCOL = T0[np.clip((UV[:, 1] * T0.shape[0]).astype(int), 0, T0.shape[0] - 1), np.clip((UV[:, 0] * T0.shape[1]).astype(int), 0, T0.shape[1] - 1)]
HS = head_skin(P, I, VCOL, HEADW + NECKW)   # the head's and the neck's skin (ren_look.head_skin: not the islands among the hair)
hst = (HS[I[ks]] * bary).sum(1) > .5; hnw = ((HEADW + NECKW)[I[ks]] * bary).sum(1)
facet = ((HEADW[I[ks]] * bary).sum(1) > .5) & (hst | facez)
patch = D[185:230, 470:545].reshape(-1, 3); skin_col = np.median(patch[sk(patch) & (patch.sum(1) > 520)], 0)   # the drawn face's skin
zone = []
for dark in (0, 1):
    zimg = Image.new('L', (Wd, H), 0); zd = ImageDraw.Draw(zimg)
    for z, d in FACE_ZONES:
        if d == dark: zd.polygon(z, fill=255)
    zone.append(ndimage.gaussian_filter(np.asarray(zimg).astype(np.float64) / 255, 1.2))
darker = np.clip((skin_col.mean() - D.mean(2) - 4) / 8, 0, 1)
ink = np.clip((np.linalg.norm(D - skin_col, axis=2) - FACE_INK[0]) / (FACE_INK[1] - FACE_INK[0]), 0, 1) * np.clip(zone[0] + zone[1] * darker, 0, 1)
# the decal covers the face's skin below the brows too (FACE_SKIN, drawing pixels: within its outline, not the hair at
# its sides), so the base texture does not show there at all: Meshy's face is in small scattered pieces of its texture,
# whose edges bled their neighbours' colours (a pink patch under the nose, streaks along the jaw); above, only the
# features (the fringe stands there)
FACE_SKIN = [(466, 164), (552, 164), (556, 182), (552, 205), (535, 224), (508, 239), (505, 239), (480, 218), (466, 203), (463, 182)]
zimg = Image.new('L', (Wd, H), 0); ImageDraw.Draw(zimg).polygon(FACE_SKIN, fill=255)
alpha = np.maximum(ink, ndimage.gaussian_filter(np.asarray(zimg).astype(np.float64) / 255, 2.))
Dface = skin_col * (1 - ink[..., None]) + D * ink[..., None]
x0, y0, x1, y1 = FACE_DECAL; R = 256   # the decal's texels: sampled at their centres (no resampling halos)
gx, gy = np.meshgrid(x0 - .5 + (np.arange(R) + .5) * (x1 - x0) / R, y0 - .5 + (np.arange(R) + .5) * (y1 - y0) / R)
dec = np.dstack([ndimage.map_coordinates(c, [gy, gx], order=1, mode='nearest') for c in (Dface[..., 0], Dface[..., 1], Dface[..., 2], alpha * 255)])
FACE_PNG = os.path.join(os.path.dirname(os.path.abspath(OUT)), name + '_face.png')
Image.fromarray(np.clip(dec, 0, 255).round().astype(np.uint8), 'RGBA').save(FACE_PNG, optimize=True)
out[ys[facet], xs[facet]] = skin_col
# the neck's skin clean too (the drawing's lines on it, stretched over its sides, read as smears; the jaw's shadow on it is
# drawn per pixel, ren_look.jaw_map)
neckt = ~facet & ((hst & (hnw > .5)) | (sk(TEX[ys, xs]) & neck_zone(pos)))   # (and its front down to the collarbones, ren_look.NECK_ZONE)
out[ys[neckt], xs[neckt]] = skin_col
print('neck texels', int(neckt.sum()))
print('face texels', int(facet.sum()), 'skin', np.round(skin_col), '; the decal', FACE_PNG, 'with', int((ink > .5).sum()), 'px of the drawing\'s features')
# the drawing's background between its hair locks (grey, near its colour; its anti-aliased edges too) and its skin are
# no colour of the hair: the hair's own there (the model's locks stand where the drawing has the face or the background:
# skin-coloured and grey patches on them looked torn)
# (on the hair only the drawing's hair colours: dark, purplish grey; its eyes' white and brown irises, on the locks hanging
# in front of the eyes, read as glints and streaks)
hairlike = (col.mean(1) < 125) & (np.abs(col[:, 0] - col[:, 2]) < 30) & (col[:, 1] <= col[:, 0] + 6)
bgl = ~hairlike
# --- the hair: the drawing where it faces the front, elsewhere the hair's own colour (no stretched highlights at the
# sides, no Meshy glints) ---
# (the hair: the head's texels that are neither skin nor the vest's teal, from the hair's lowest point up: the collar's
# teal and its light trim below stay)
# (the skin-coloured islands among the hair, ren_look.head_skin, are hair; the vest's teal is the collar only below its
# top, higher up a bluish white is Meshy's glint on the hair)
tc = TEX[ys, xs]; hv = ((HEADW[I[ks]] * bary).sum(1) > .5) & ~hst; teal = (tc[:, 1] > tc[:, 0] + 8) & (pos[:, 1] < 1.56)
like = hv & ~teal & ~facet & (tc.mean(1) <= 110); hairt = hv & ~teal & ~facet & (pos[:, 1] >= np.percentile(pos[like, 1], 1))
hair_col = np.median(tc[like], 0)
hw = np.clip((nor[:, 2] - .35) / .25, 0, 1); hw = hw * hw * (3 - 2 * hw) * vis
colh = np.where(bgl[:, None], hair_col, col)
out[ys[hairt], xs[hairt]] = colh[hairt] * hw[hairt, None] + hair_col * (1 - hw[hairt, None])
print('hair texels', int(hairt.sum()), 'drawn (front)', int((hairt & (hw > .5)).sum()), 'hair colour', np.round(hair_col), '; not the drawing\'s hair colours on', int((bgl & hairt & (hw > 0)).sum()), 'of them')
# --- the sash's tails: hanging ribbons in the look (tools/ren_look.py), so off the body: each tail texel takes the colour
# of the nearest texel (in space) that is not orange, the trousers or the vest under it ---
vcol = TEX[np.clip((UV[:, 1] * TS).astype(int), 0, TS - 1), np.clip((UV[:, 0] * TS).astype(int), 0, TS - 1)].astype(int)
tv = np.zeros(len(P), bool)
for t in sash_tails(P, vcol, I): tv[t] = True
for _ in range(2):   # the tails' darker edges too: two rings of neighbours
    tv2 = tv.copy(); tv2[I[tv[I].any(1)].ravel()] = True; tv = tv2
c = out[ys, xs]; orng = (c[:, 0] > c[:, 1] + 12) & (c[:, 0] - c[:, 2] > 25)   # warm: orange to its dark brown shadows
low = (pos[:, 1] < SASH_BAND) & (np.abs(pos[:, 0]) < .33)
tt = ((tv[I[ks]].sum(1) >= 2) & low) | (orng & low)    # the model's tails, and the drawing's painted below the band
# the drawing without its tails: each tail pixel (with its lines, a few px around) takes the colour of the nearest
# pixel of the vest or the trousers beside it (not a black line): flat colours, split down the middle of the tail
od = sash_orange(D); od[:sash_band_end(od) + 6] = False
od = ndimage.binary_dilation(ndimage.binary_closing(od, iterations=2), iterations=4)
warm = (D[..., 0] > D[..., 1] + 12) & (D[..., 0] - D[..., 2] > 25)   # the tails' orange edges and dark brown shadows
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
# --- the band: the drawing's own band (its two wraps crossing in the knot) on the model's band, at the model's height
# (the drawing has it a few cm higher: painted where it is in the drawing, its colours fell on the vest), where the band
# faces the front; the sides and the back in the drawing's orange, lit or in shadow where Meshy painted its folds darker.
# The drawing's orange that fell on the clothes around goes ---
BAND_Y, BAND_SHADOW = (1.02, 1.22), .82
TC = TEX[ys, xs]; area = (pos[:, 1] > BAND_Y[0]) & (pos[:, 1] < BAND_Y[1]) & (np.abs(pos[:, 0]) < .35)
R_ = np.maximum(TC[:, 0], 1.)
ring = area & (TC[:, 0] > 60) & (TC[:, 1] / R_ < .66) & ((TC[:, 0] - TC[:, 2]) / R_ > .65)   # Meshy's orange and its browns, not the skin
c = out[ys, xs]; skin_m = (TC[:, 0] > 150) & (TC[:, 1] > 95) & (TC[:, 0] - TC[:, 2] > 50) & (TC[:, 1] / R_ > .6)   # Meshy's skin
stray = area & ~ring & ~skin_m & (c[:, 0] > c[:, 1] + 12) & (c[:, 0] - c[:, 2] > 25)   # the drawing's sash's orange on the clothes
out[ys[stray], xs[stray]] = D[sy, sx][pvi[stray], pui[stray]]
# the model's band: the heights where Meshy's orange goes round the waist (as tools/ren_look.py finds it)
vo = (vcol[:, 0] > 170) & (vcol[:, 0] - vcol[:, 1] > 50) & (vcol[:, 2] < 90) & (np.abs(P[:, 0]) < .3); ring_y = []
for y0 in np.arange(.9, 1.3, .01):
    sl = vo & (P[:, 1] >= y0) & (P[:, 1] < y0 + .01)
    if sl.any() and len(np.unique((np.degrees(np.arctan2(P[sl, 0], P[sl, 2])) % 360 // 15).astype(int))) * 15 >= 200: ring_y.append(y0)
Y0, Y1 = min(ring_y), max(ring_y) + .01
low_ = ring & (pos[:, 1] < Y0 - .005)   # Meshy's orange under the band: the tops of its old tails, now ribbons of their own
out[ys[low_], xs[low_]] = D[sy, sx][pvi[low_], pui[low_]]; ring = ring & ~low_
# the drawing's band: the rows from its top while at least 45% as orange as its most orange row (the tails below are
# less), over gaps of up to 3 rows (the dark line between its two wraps)
odb = sash_orange(D); r0, r1 = drawing_band(D)
ext = [(np.nonzero(odb[r])[0].min() - 3, np.nonzero(odb[r])[0].max() + 3) if odb[r].any() else (1, 0) for r in range(r0, r1 + 1)]
band_px = D[r0:r1 + 1][odb[r0:r1 + 1]]; lit = np.median(band_px, 0); shade = lit * .8
ml = TC[ring].mean(1); two = np.where((ml < np.median(ml) * BAND_SHADOW)[:, None], shade, lit)   # sides and back
bp = pos[ring]; v = np.round(r0 + (Y1 - bp[:, 1]) / (Y1 - Y0) * (r1 - r0)).astype(int); u = np.round(cx + bp[:, 0] * s).astype(int)
inb = (v >= r0) & (v <= r1)
inb[inb] = [ext[vv - r0][0] <= uu <= ext[vv - r0][1] for vv, uu in zip(v[inb], u[inb])]
dcol = two.copy(); dcol[inb] = D[np.clip(v[inb], 0, H - 1), np.clip(u[inb], 0, Wd - 1)]
fw = np.clip((nor[ring, 2] - .25) / .35, 0, 1); fw = fw * fw * (3 - 2 * fw)
out[ys[ring], xs[ring]] = dcol * fw[:, None] + two * (1 - fw[:, None])
print('band: drawing rows %d-%d on the model at %.2f-%.2f m, %d texels (%d from the drawing), %d stray orange texels and %d of old tail tops repainted' % (r0, r1, Y0, Y1, int(ring.sum()), int((inb & (fw > .5)).sum()), int(stray.sum()), int(low_.sum())))
# --- padding: every texel outside the triangles takes its nearest triangle texel's colour (the gutters between UV pieces
# kept Meshy's old colours, which showed as thin cracks along the seams once filtered, the sash's orange most of all) ---
inside = tid >= 0
_, (gy, gx) = ndimage.distance_transform_edt(~inside, return_indices=True)
out[~inside] = out[gy[~inside], gx[~inside]]
Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(OUT, quality=85, optimize=True)
print(OUT, os.path.getsize(OUT))
