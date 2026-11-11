#!/usr/bin/env python3
"""The drawn light of Denis's head images of Kael (10/11/2026; tools/cel_light.py): where they shade the skin and the
hair, on the new head (wip_assets/kael/kael_head.*, tools/kael_head.py). The images shade the skin where a lock lies just
over it (a thin band under the bangs, along the temples), on the nose's side, in the ears and under the jaw; the hair
under the locks over it and on their undersides (a true light from above put most of the face in the bangs' shadow:
they are long and many). The model, skin and hair apart: in shadow where a lock lies within R m of it, more than FRONT m
out of its surface (cel_light.contact; for the skin, with UP, only locks not under it), or where it turns from the
light L (n . L under TERM).

Each image's camera is its scan's (tools/sheet_scan.py OUT.json, the head part); each texel of the head's skin and hair
that the camera sees (the front-most surface there, facing it) is lit or in shadow in the image (its colour there, of
its own kind: skin darker than SKIN_T, hair than HAIR_T, not the lines). A model's score: per image, the share of the
image's lit texels it gives lit and of its shadowed ones it gives shadow (their mean), then the images' mean; the
parameters on a grid. Prints the best for the skin and for the hair, and their scores per image.

usage: python3 tools/kael_light.py SCAN_DIR   (SCAN_DIR: the scans' fronte.json, 34_dx.json, ... of the head images)"""
import itertools, json, os, sys
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paint_views import texel_table
from cel_light import contact, view_depth
from kael_head import is_skin, is_hair

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
VIEWS = ('fronte', '34_dx', 'profilo_dx', 'dietro', 'profilo_sx', '34_sx')
SKIN_T, HAIR_T, LINE_T = 165., 190., 90.   # the images' shadow (mean rgb under) and their lines (under: not counted)
SEEN, STEP, CAST_STEP = .002, 3, 4         # m: the front-most surface within this; every STEP-th texel; the casters' every CAST_STEP-th
GRID = {'az': (-60, -30, 0, 30, 60), 'el': (-20, 0, 20, 40), 'term': (-.4, -.2, 0., .2),
        'skin': [(r, fr, up) for r in (.003, .005, .008, .012) for fr in (.0005, .0015) for up in (False, True)],
        'hair': [(r, fr) for r in (.004, .008, .012) for fr in (.001, .002, .004)]}


def light(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)])


def main(scan_dir):
    d = os.path.join(ROOT, 'wip_assets/kael'); j = json.load(open(os.path.join(d, 'kael_head.json'))); B = open(os.path.join(d, 'kael_head.bin'), 'rb').read()
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    Q = f(j['pos']).reshape(-1, 3).astype(np.float64); N = f(j['nor']).reshape(-1, 3).astype(np.float64)
    UV = f(j['uv']).reshape(-1, 2).astype(np.float64); I = f(j['idx'], np.uint16 if j['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    tp = os.path.join(d, 'kael_head.png'); T = np.asarray(Image.open(tp if os.path.exists(tp) else tp[:-3] + 'jpg').convert('RGB')).astype(np.float64); TS = T.shape[0]
    ys, xs, ks, _, pos_all, nor_all = texel_table(Q, N, UV, I, TS)
    c = T[ys, xs]; kind_all = np.where(is_skin(c), 1, np.where(is_hair(c) & (c.mean(1) > LINE_T), 2, 0))
    casters = pos_all[kind_all == 2][::CAST_STEP]; tree = cKDTree(casters)
    sel = np.nonzero(kind_all > 0)[0][::STEP]; pos, nor, kind = pos_all[sel], nor_all[sel], kind_all[sel]
    labels = []   # (view, its texels, their shadow in the image)
    for v in VIEWS:
        if not os.path.exists(os.path.join(scan_dir, v + '.json')): print('%s: no scan' % v); continue
        cam = json.load(open(os.path.join(scan_dir, v + '.json')))[0]
        D = np.asarray(Image.open(os.path.join(ROOT, 'docs/ref/personaggi/kael_testa_%s.png' % v)).convert('RGB')).astype(np.float64); H, W = D.shape[:2]
        Z, proj = view_depth(Q, I, cam, W, H); u, vv, dep = proj(pos)
        ui, vi = np.clip(u.astype(int), 0, W - 1), np.clip(vv.astype(int), 0, H - 1)
        t = np.radians(cam['yaw']); toward = np.array([np.sin(t), 0, np.cos(t)])
        seen = (dep >= Z[vi, ui] - SEEN) & (nor @ toward > .15) & (u >= 0) & (u < W) & (vv >= 0) & (vv < H)
        px = D[vi, ui]; L = px.mean(1)
        own = np.where(kind == 1, is_skin(px), (px.max(1) - px.min(1) < 60) & (px[:, 2] >= px[:, 1] - 5)) & (L > LINE_T)
        k = np.nonzero(seen & own)[0]
        sh = np.where(kind[k] == 1, L[k] < SKIN_T, L[k] < HAIR_T)
        labels.append((v, k, sh)); print('%s: %d texels seen (%d skin %.0f%% in shadow, %d hair %.0f%%)' % (
            v, len(k), int((kind[k] == 1).sum()), 100 * sh[kind[k] == 1].mean(), int((kind[k] == 2).sum()), 100 * sh[kind[k] == 2].mean()))
    def ba(pred, kd):
        per = []
        for v, k, sh in labels:
            m = kind[k] == kd; p = pred[k][m]; s = sh[m]
            per.append(.5 * ((p & s).sum() / max(s.sum(), 1) + (~p & ~s).sum() / max((~s).sum(), 1)) if s.any() and (~s).any() else np.nan)
        return np.nanmean(per), per
    nl = {(az, el): nor @ light(az, el) for az, el in itertools.product(GRID['az'], GRID['el'])}
    for kd, name, variants in ((1, 'skin', GRID['skin']), (2, 'hair', GRID['hair'])):
        best = (-1,)
        for var in variants:
            if kd == 1: cont = contact(pos, nor, casters, var[0], var[1], up=(0., 1., 0.) if var[2] else None, tree=tree)
            else: cont = contact(pos, nor, casters, var[0], var[1], tree=tree)
            for (az, el), n_l in nl.items():
                for term in GRID['term']:
                    sc, per = ba(cont | (n_l < term), kd)
                    if sc > best[0]: best = (sc, var, az, el, term, per)
        sc, var, az, el, term, per = best
        print('%s: best contact %s, light az %d el %d (L %s), term %.2f: %.3f; per image %s' % (
            name, var, az, el, np.round(light(az, el), 3).tolist(), term, sc, {v: round(float(p), 3) for (v, _, _), p in zip(labels, per)}))


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
