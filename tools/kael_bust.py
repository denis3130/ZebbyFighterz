#!/usr/bin/env python3
"""Kael's bust and arms from Meshy (11/11/2026: docs/meshy/KAEL.md "Busto da Meshy"), cleaned before it goes on his
bones (Denis: "prima di mettere il busto sulle ossa di kael miglioriamolo al meglio"): Meshy's own paint in the bust
sheet's flat palette, piece by piece, and the skin's shadow (Denis chose "Ombre sulla pelle").

- Input: the decimated GLB (tools/mesh_prep/decimate_glb.py busto_k1.glb busto_k1_30k.glb 30000): its texture and UVs.
- Each texel's piece by Meshy's colour (skin, dark cloth, purple), smoothed on the surface (its thin dark strokes inside
  the skin are the skin's lines); its tone by Meshy's lightness: the cloth's darkest share black as the drawing's share
  (SHARE), the purple's darkest share its shadow, the skin's brown strokes its shadow or ink (SKIN_T).
  (Tried and left: the three views projected onto the model. They overlap it by 85-92% only: the skin's shadows came
  out in fragments and the borders frayed.)
- The tattoos (purple pieces whose rim is mostly skin): purple with a thin rim of its shadow, as the sheet draws them.
- The skin's shadow baked: light from above (SHADE: n . L minus the occlusion's weight), as much of it as the drawing
  shades (14%, fit on the three views: light from above and the hollows matched their shadows best), crumbs under
  SKIN_SMALL mm2 left out.
- Palette (PAL): measured on the three views sent to Meshy (docs/ref/personaggi/kael_busto_senza_code_*.png).

usage: python3 tools/kael_bust.py IN_30k.glb OUT.glb [--png OUT.png]"""
import io, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
import glbio
import kael_flat as KF
from paint_views import texel_table

TS = 2048                              # the texture's size
SC = .443                              # m per unit of Meshy's GLB (the bust, collar's top to hem, about 0.75 m)
PAL = dict(plum=(65, 49, 74), black=(26, 21, 27), skin=(250, 191, 151), skinS=(164, 112, 85), purple=(166, 92, 203), purpleS=(108, 63, 138), ink=(9, 6, 9))
SHARE = dict(black=.37, purpleS=.21)   # the drawing's: black of the cloth, the shadow of the purple
SKIN_T = (120, 182)                    # Meshy's skin lightness: under [0] ink, under [1] the skin's shadow (its brown strokes only)
SKIN_SMALL = 15.                       # mm2: the skin's shadow pieces under this: skin
SHADE = (0., 60., 1., .144)            # the skin's shadow: light from azimuth [0], elevation [1] (degrees), occlusion's weight [2], its share [3]
AO_DIRS, AO_RES, AO_EPS = 96, 700, .025   # the occlusion: directions, depth maps' size, self-test (GLB units)


def occlusion(P, N, I):
    """Per vertex: the share of AO_DIRS directions (weighted by the normal) from which it is seen."""
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9); Q = P - (P.min(0) + P.max(0)) / 2; R = np.linalg.norm(Q, axis=1).max() * 1.02; S = AO_RES
    i = np.arange(AO_DIRS) + .5; phi = np.arccos(1 - 2 * i / AO_DIRS); th = np.pi * (1 + 5 ** .5) * i
    D = np.c_[np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)]; vis = np.zeros(len(P)); ws = np.zeros(len(P))
    for dv in D:
        up = np.array([0, 1, 0]) if abs(dv[1]) < .9 else np.array([1, 0, 0]); ex = np.cross(up, dv); ex /= np.linalg.norm(ex); ey = np.cross(dv, ex)
        u = (Q @ ex / R * .5 + .5) * (S - 1); v = (Q @ ey / R * -.5 + .5) * (S - 1); z = Q @ dv
        im = Image.new('F', (S, S), -1e9); dr = ImageDraw.Draw(im)
        for t in np.argsort(z[I].mean(1)): a, b, c = I[t]; dr.polygon([(u[a], v[a]), (u[b], v[b]), (u[c], v[c])], fill=float(z[I[t]].mean()))
        Z = np.asarray(im)[np.clip(np.round(v).astype(int), 0, S - 1), np.clip(np.round(u).astype(int), 0, S - 1)]
        w = np.clip(N @ dv, 0, 1); vis += w * (z >= Z - AO_EPS); ws += w
    return vis / np.maximum(ws, 1e-9)


def main(src, dst, png=None):
    m = glbio.read(src); P, N, UV, I = m['pos'], m['nor'], m['uv'], m['idx']
    T = np.asarray(Image.open(io.BytesIO(m['img'])).convert('RGB').resize((TS, TS), Image.LANCZOS)).astype(float)
    ys, xs, ks, bary, pos, nor = texel_table(P, N, UV, I, TS); nor = nor / np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    names = list(PAL); cols = np.array([PAL[k] for k in names], float); ix = {k: i for i, k in enumerate(names)}
    KF.prepare(P * SC, I); cnt = np.bincount(ks, minlength=len(I)).astype(float); area = KF.TRI_AREA[ks] * 1e6 / np.maximum(cnt[ks], 1)
    jw, okw, ok = KF._graph(pos * SC, nor.astype(np.float32), np.sqrt(area) * 1e-3); j = jw[:, :KF.KNN - 1]
    mey = T[ys, xs]; r, g, b = mey[:, 0], mey[:, 1], mey[:, 2]; L = mey.mean(1)
    # the pieces: 0 skin, 1 dark cloth, 2 purple
    mat = np.ones(len(ks), np.int64); mat[(r > 150) & (r - b > 35)] = 0; mat[(b > 95) & (b - g > 55) & ~(mat == 0)] = 2
    lines = (mat == 1) & (KF._mode(mat, j, ok, 3, own=0) == 0); mat[lines] = 0
    for _ in range(2): mat = KF._mode(mat, jw, okw, 3, keep=lines)
    KF._small(mat, j, ok, area, np.full(len(ks), 30.), np.zeros(len(ks), bool))
    # the tones
    lab = np.zeros(len(ks), np.int64); brown = (r - b > 55) & (b - g < 40)
    s = mat == 0; lab[s] = np.where((L[s] < SKIN_T[0]) & brown[s], ix['ink'], np.where((L[s] < SKIN_T[1]) & brown[s], ix['skinS'], ix['skin']))
    s = mat == 1; lab[s] = np.where(L[s] < np.quantile(L[s], SHARE['black']), ix['black'], ix['plum'])
    s = mat == 2; lab[s] = np.where(L[s] < np.quantile(L[s], SHARE['purpleS']), ix['purpleS'], ix['purple'])
    # the tattoos
    comp = KF._comps(mat, j, ok); nc = comp.max() + 1
    diff = ok & (comp[j] != comp[:, None]); rr = np.repeat(np.arange(len(mat)), j.shape[1])[diff.ravel()]; qq = j[diff]
    rim_sk = np.bincount(comp[rr], weights=(mat[qq] == 0).astype(float), minlength=nc); rim_n = np.bincount(comp[rr], minlength=nc)
    cm = np.zeros(nc, np.int64); cm[comp] = mat; tat_c = (cm == 2) & (rim_sk > .6 * np.maximum(rim_n, 1)); tat = tat_c[comp]
    edge = tat & np.where(ok, mat[j] != 2, False).any(1); edge |= tat & np.where(ok, edge[j], False).any(1)
    lab[tat] = ix['purple']; lab[edge] = ix['purpleS']
    print('pieces: skin %.1f%%, cloth %.1f%%, purple %.1f%%; tattoos: %d pieces' % (*(100 * np.bincount(mat, minlength=3) / len(mat)), int(tat_c.sum())))
    # the skin's shadow
    ao = occlusion(P, N, I)[cKDTree(P).query(pos)[1]]
    az, el = np.radians(SHADE[0]), np.radians(SHADE[1]); Lv = np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])
    sc = nor @ Lv - SHADE[2] * (1 - ao); sk = (mat == 0) & ~tat; tau = np.quantile(sc[sk], SHADE[3])
    lab[sk & (lab == ix['skin']) & (sc < tau)] = ix['skinS']
    nl = len(names)
    for _ in range(5): lab = KF._mode(lab, jw, okw, nl, keep=(lab == ix['ink']) | tat | (mat != 0))
    for _ in range(2): lab = KF._mode(lab, j, ok, nl, keep=(lab == ix['ink']) | tat)
    KF._small(lab, j, ok, area, np.where(lab == ix['ink'], 1.5, np.where(lab == ix['skinS'], SKIN_SMALL, 10.)), tat)
    print('  '.join('%s %.1f%%' % (n, 100 * (lab == i).mean()) for i, n in enumerate(names)))
    out = np.zeros((TS, TS, 3)); cov = np.zeros((TS, TS), bool); out[ys, xs] = cols[lab]; cov[ys, xs] = True
    _, (iy, jx) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], jx[~cov]]
    im = Image.fromarray(out.round().astype(np.uint8)); bio = io.BytesIO(); im.save(bio, 'PNG', optimize=True)
    if png: im.save(png)
    glbio.write(dst, m, P, N, UV, I, img=bio.getvalue(), mime='image/png'); print('written', dst)


if __name__ == '__main__':
    av = sys.argv[1:]; png = None
    if '--png' in av: k = av.index('--png'); png = av[k + 1]; av = av[:k] + av[k + 2:]
    if len(av) != 2: sys.exit(__doc__)
    main(av[0], av[1], png)
