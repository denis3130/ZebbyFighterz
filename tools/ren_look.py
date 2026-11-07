#!/usr/bin/env python3
"""The "Ren dipinto" look data (7/11/2026, Denis's choices: fists, spiky hair from his drawing, a clean face outline),
computed from a tools/meshy_pack.py package. The game and the viewer use it only where CFG.looks turns it on.

usage: python3 tools/ren_look.py PACKAGE_DIR OUT_DIR DRAWING
  writes OUT_DIR/<name>_look.json and <name>_look.bin (for now viewer_assets/ren: only the viewer uses them):
  hands: {L|R: {bone, l, n (unit axes in the hand bone's frame: across the hand and out of the palm), c (fist centre),
         size (half sizes along l, the bone's y, n), thumb (+1/-1: the side along l where the thumb is)}}
  fold: [byte offset, count] float32 xyz per vertex: the bind positions with the open hands folded into the fists (a
        morph target: weight 1 hides the open hand inside the fist mesh)
  line: [byte offset, count] float32 per vertex: the outline's width there (1; LINE_FACE on the front of the face,
        where the shell around the nose showed as a dark wedge)
  spikes: [{p (base), d (unit direction), len, r}] in the Head bone's frame: anime hair spikes on the sides, back and
        top of the hair (Meshy's hair is a round mass seen from the side), each kept inside the drawing's silhouette
        seen from the front (DRAWING: Denis's character sheet, the same front fit as tools/paint_from_drawing.py)
"""
import json, os, sys
import numpy as np
from PIL import Image

HAND_W = .3          # vertices with at least this weight on a hand bone belong to the hand
LINE_FACE = .2       # outline width kept on the front of the face
FOLD = .2            # the folded hand keeps this share of its size around the fist centre


def qm(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# Spike directions (azimuth from the front around the up axis, elevation), degrees: sides, back and top, never the face.
SPIKES = [(75, 12), (115, 15), (150, 12), (180, 18), (210, 12), (245, 15), (285, 12), (95, 40), (135, 42), (180, 45),
          (225, 42), (265, 40), (125, 66), (180, 70), (235, 66), (180, 86)]


def ray_far(P, T, o, d):
    """Farthest hit (distance) of the ray o + t d with triangles T of points P (Moller-Trumbore), or 0."""
    v0, v1, v2 = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]; e1, e2 = v1 - v0, v2 - v0
    h = np.cross(np.broadcast_to(d, e2.shape), e2); a = (e1 * h).sum(1); ok = np.abs(a) > 1e-12; f = np.where(ok, 1 / np.where(ok, a, 1), 0)
    s = o - v0; u = f * (s * h).sum(1); q = np.cross(s, e1); v = f * (q @ d); t = f * (e2 * q).sum(1)
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
    return float(t[hit].max()) if hit.any() else 0.


def main(pkg, out, drawing):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); J = f(me['jnt'], np.uint8).reshape(-1, 4); W = f(me['wgt']).reshape(-1, 4)
    bones = m['bones']; idx = {b['n']: i for i, b in enumerate(bones)}
    G = [None] * len(bones)
    for i, b in enumerate(bones):
        M = np.eye(4); M[:3, :3] = qm(b['q']); M[:3, 3] = b['t']; G[i] = M if b['p'] < 0 else G[b['p']] @ M
    fold = P.copy(); hands = {}
    for side in ('Left', 'Right'):
        hi = idx[side + 'Hand']; w = ((J == hi) * W).sum(1); sel = np.nonzero(w >= HAND_W)[0]
        Gi = G[hi]; inv = np.linalg.inv(Gi); L = P[sel] @ inv[:3, :3].T + inv[:3, 3]
        core = L[w[sel] >= .6]
        c0 = core - core.mean(0); ev, evec = np.linalg.eigh(c0.T @ c0 / len(c0))
        y = np.array([0, 1., 0]); n = evec[:, 0] - y * (evec[:, 0] @ y); n /= np.linalg.norm(n)
        if (Gi[:3, :3] @ n)[2] < 0: n = -n            # palms face forward in the bind pose (Denis's drawing)
        l = np.cross(y, n); l /= np.linalg.norm(l)
        hy = core @ y; hl = core @ l; hn = core @ n
        lo = (hy > .02) & (hy < .09)
        thumb = 1 if np.percentile(hl[lo], 97) > -np.percentile(hl[lo], 3) else -1
        # the fist: from the wrist to the knuckles, as wide as the palm, curled fingers in front of the palm
        c = y * .068 + l * float(np.median(hl[lo])) + n * (float(np.median(hn)) + .012)
        size = [.039, .045, .033]
        hands[side[0]] = {'bone': side + 'Hand', 'l': [round(float(v), 5) for v in l], 'n': [round(float(v), 5) for v in n],
                          'c': [round(float(v), 5) for v in c], 'size': size, 'thumb': thumb}
        cw = Gi[:3, :3] @ c + Gi[:3, 3]
        k = np.clip((w[sel] - HAND_W) / .3, 0, 1)[:, None]
        fold[sel] = P[sel] * (1 - k) + (cw + (P[sel] - cw) * FOLD) * k
        print(side, 'hand', len(sel), 'verts, thumb side', thumb, 'fist centre', np.round(c, 3))
    # --- hair spikes ---
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    hi = idx['Head']; wh = ((J == hi) * W).sum(1); Th = I[(wh[I] >= .5).all(1)]
    head = P[wh >= .5]; c = np.median(head, 0); c[1] = head[:, 1].min() + (head[:, 1].max() - head[:, 1].min()) * .55
    D = np.asarray(Image.open(drawing).convert('RGB')).astype(np.float64); bg = D[5:40, 5:40].reshape(-1, 3).mean(0)
    mask = np.abs(D - bg).sum(2) > 30; ys, xs = np.nonzero(mask)
    sc = (ys.max() - ys.min()) / (P[:, 1].max() - P[:, 1].min()); cx = (xs.min() + xs.max()) / 2; by = ys.max()
    inside = lambda p: mask[int(np.clip(by - p[1] * sc, 0, mask.shape[0] - 1)), int(np.clip(cx + p[0] * sc, 0, mask.shape[1] - 1))]
    Gi = G[hi]; inv = np.linalg.inv(Gi); spikes = []
    for k, (az, el) in enumerate(SPIKES):
        a, e = np.radians(az), np.radians(el)
        d = np.array([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)])
        r = ray_far(P, Th, c, d)
        if r <= 0: continue
        flow = d + np.array([0, .25, -.2]); flow /= np.linalg.norm(flow)   # anime hair sweeps up and back
        base = c + d * (r - .018); ln = .085 + .05 * ((k * 7919) % 11) / 10
        while ln > .04 and not inside(base + flow * ln): ln -= .01
        if ln <= .04: continue
        spikes.append({'p': [round(float(v), 5) for v in inv[:3, :3] @ base + inv[:3, 3]], 'd': [round(float(v), 5) for v in inv[:3, :3] @ flow],
                       'len': round(float(ln), 4), 'r': round(.03 + .012 * ((k * 104729) % 7) / 6, 4)})
    print('spikes', len(spikes), 'of', len(SPIKES))
    # --- the outline on the face: thin where the head faces forward and the texture is skin ---
    N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2)
    tex = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(int); ts = tex.shape[0]
    col = tex[np.clip((UV[:, 1] * ts).astype(int), 0, ts - 1), np.clip((UV[:, 0] * ts).astype(int), 0, ts - 1)]
    skin = (col[:, 0] > 150) & (col[:, 1] > 95) & (col[:, 0] - col[:, 2] > 50)
    face = (wh >= .5) & (N[:, 2] > .15) & skin
    line = np.ones(len(P), np.float32); line[face] = LINE_FACE
    print('face outline thinned on', int(face.sum()), 'vertices')
    blob = fold.astype(np.float32).tobytes(); lo = len(blob); blob += line.tobytes()
    look = {'v': 1, 'hands': hands, 'fold': [0, int(fold.size)], 'line': [lo, int(line.size)], 'spikes': spikes}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(out, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look', len(blob), 'B')


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
