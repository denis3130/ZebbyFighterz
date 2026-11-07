#!/usr/bin/env python3
"""The "Ren dipinto" look data (7/11/2026, Denis's choices: fists, spiky hair from his drawing, a clean face outline),
computed from a tools/meshy_pack.py package. The game and the viewer use it only where CFG.looks turns it on.

usage: python3 tools/ren_look.py PACKAGE_DIR OUT_DIR DRAWING
  writes OUT_DIR/<name>_look.json and <name>_look.bin (for now viewer_assets/ren: only the viewer uses them):
  fingers: [{n (bone name), p (parent bone's name), t (offset from the parent, in its frame), fist ([x, y, z, w]: the
          local rotation that makes the fist; the rest rotation is none)}]: three bones for each finger and thumb of
          both hands, under the hand bones. Meshy's skeleton has no fingers: they are found on each hand's mesh (the
          branches of the geodesic distance from the wrist), with the joints at a hand's usual proportions.
  skin: [[byte offset, count] uint8 x4, [byte offset, count] float32 x4] per vertex: the package's skin with the
        fingers on their bones (bone index: the package's bones, then the fingers in the order above)
  flat: [byte offset, count] float32 per vertex: how much of the light the toon shading leaves out there (1 on the front
        of the head, fading to 0 by its sides): the drawing painted on the face has its own shading, the light's only
        darkened half of it
  line: [byte offset, count] float32 per vertex: the outline's width there (1; LINE_FACE on the front of the face,
        where the shell around the nose showed as a dark wedge; LINE_FINGER on the fingers, whose shells stuck out
        between the curled fingers of the fist)
  spikes: [{p (base), d (unit direction), len, r}] in the Head bone's frame: anime hair spikes on the sides, back and
        top of the hair (Meshy's hair is a round mass seen from the side), each kept inside the drawing's silhouette
        seen from the front (DRAWING: Denis's character sheet, the same front fit as tools/paint_from_drawing.py)
"""
import heapq, json, os, sys
import numpy as np
from PIL import Image

HAND_W = .3          # vertices with at least this weight on a hand bone belong to the hand
LINE_FACE = .2       # outline width kept on the front of the face
LINE_FINGER = .4     # and on the fingers
PERSIST = .015       # a finger stands out at least this far (geodesic, m) from where it joins the hand
FINGER_SEG = (.45, .30, .25)    # proximal, middle and distal phalanx: shares of a finger's length
FREE = .80           # the free part of a finger (from the web between the fingers to the tip): share of its length
THUMB_IP = .5        # the thumb's last joint: this share of its free part from the web
BLEND = .35          # a joint's skin blend reaches this share of the shorter phalanx beside it, on each side
FIST = (82, 100, 60)    # the fist: bend (degrees) at the knuckle, middle and last joint of a finger
THUMB_ON = 1.1      # in the fist the thumb lies across the index and middle finger, this many radii in front of them
NAMES = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')


def qm(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def qaxis(a, deg):
    a = np.asarray(a, float) / np.linalg.norm(a); h = np.radians(deg) / 2
    return [*(a * np.sin(h)), np.cos(h)]


def qarc(u, v):
    """The shortest rotation taking unit u to unit v, [x, y, z, w]."""
    if u @ v < -.999: sys.exit('qarc: opposite directions, the turn is ambiguous')
    c = np.cross(u, v); q = np.array([*c, 1 + float(u @ v)])
    return list(q / np.linalg.norm(q))


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qinv(a):
    return [-a[0], -a[1], -a[2], a[3]]


def unit(v):
    return v / np.linalg.norm(v)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


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


def branches(Pw, nb, ws):
    """The fingers of a hand: per welded vertex the finger it is on (0, 1, ...) or -1 (the palm). Pw: welded positions in
    the hand's frame (y from the wrist toward the fingers), nb: adjacency [(vertex, length)], ws: the hand's vertices.
    Walking down the geodesic distance from the wrist, each finger is a part that ends where it joins the rest; bumps
    less than PERSIST tall are not fingers."""
    g = np.full(len(Pw), np.inf); hq = []
    for v in ws:
        if Pw[v, 1] < .012: g[v] = 0; hq.append((0., int(v)))
    heapq.heapify(hq)
    while hq:
        dv, v = heapq.heappop(hq)
        if dv > g[v]: continue
        for u, dl in nb[v]:
            if dv + dl < g[u]: g[u] = dv + dl; heapq.heappush(hq, (g[u], u))
    reach = ws[np.isfinite(g[ws])]
    order = reach[np.argsort(-g[reach], kind='stable')]
    par, tip, ended, mem, lab, done, final = {}, {}, {}, {}, np.full(len(Pw), -1), np.zeros(len(Pw), bool), []

    def find(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for v in map(int, order):
        roots = sorted({find(u) for u, _ in nb[v] if done[u]}, key=lambda r: -g[tip[r]])
        if not roots: par[v] = tip[v] = top = v; ended[v] = False; mem[v] = []
        else:
            top = roots[0]
            for r in roots[1:]:
                if g[tip[r]] - g[v] >= PERSIST: final.append(r); ended[top] = True   # a finger ends here
                elif ended[top]:                                                       # a bump on the palm
                    for x in mem[r]: lab[x] = -1
                else:                                                                  # a bump on a finger
                    for x in mem[r]: lab[x] = top
                    mem[top] += mem[r]
                par[r] = top
            par[v] = top
        done[v] = True
        if not ended[top]: lab[v] = top; mem[top].append(v)
    final.append(find(int(order[0])))
    out = np.full(len(Pw), -1)
    for k, r in enumerate(final): out[lab == r] = k
    return out


def fingers_of(Lw, lab, l, n, thumb):
    """The joints of a hand's fingers (hand frame), thumb first then from the index outward: {k (label), d (unit, toward
    the tip), r (radius), j: three joints (thumb: its base inside the palm, the web, the last joint; a finger: the
    knuckle, the middle and the last joint), tip}. In the fist (FIST) the four fingers end level: each knuckle is moved
    along its finger (the tip stays) until its lowest curled joint is at the fingers' mean height, as in a real fist
    (the longer fingers, bent from where their length put the knuckle, came out lower)."""
    y = np.array([0, 1., 0]); F = []
    for k in range(lab.max() + 1):
        Q = Lw[lab == k]
        if len(Q) < 8: continue
        c = Q.mean(0); d = np.linalg.svd(Q - c)[2][0]; d = d if d @ y > 0 else -d
        s = (Q - c) @ d; r = float(np.percentile(np.linalg.norm(Q - c - np.outer(s, d), axis=1), 70))
        F.append({'k': k, 'c': c, 'd': d, 'r': r, 'tip': s.max(), 'web': np.percentile(s, 3), 'side': float(c @ l * thumb), 'y': float(c[1])})
    if len(F) != 5: sys.exit('found %d fingers on a hand, not 5' % len(F))
    th = max(F, key=lambda f: f['side'] - 2 * f['y'])                  # the thumb: on its side and the lowest
    rest = sorted([f for f in F if f is not th], key=lambda f: -f['side'])
    free = th['tip'] - th['web']; at = lambda f, s: f['c'] + f['d'] * s
    out = [{'k': th['k'], 'd': th['d'], 'r': th['r'], 'tip': at(th, th['tip']),
            'j': [at(th, th['web'] - .8 * free), at(th, th['web'] + .1 * free), at(th, th['web'] + THUMB_IP * free)]}]
    joints = lambda f, b0: [at(f, b0), at(f, b0 + FINGER_SEG[0] * (f['tip'] - b0)), at(f, b0 + (FINGER_SEG[0] + FINGER_SEG[1]) * (f['tip'] - b0))]

    def low(f, b0):   # the lowest (y) joint of finger f curled into the fist, its knuckle at b0
        j = joints(f, b0); ax = unit(np.cross(f['d'], unit(n - f['d'] * (n @ f['d']))))
        j1 = j[0] + qm(qaxis(ax, FIST[0])) @ (j[1] - j[0]); j2 = j1 + qm(qaxis(ax, FIST[0] + FIST[1])) @ (j[2] - j[1])
        return min(j1[1], j2[1])
    b0 = [f['tip'] - (f['tip'] - f['web']) / FREE for f in rest]
    level = float(np.mean([low(f, b) for f, b in zip(rest, b0)]))
    for f, b in zip(rest, b0):
        lo, hi = b - .4 * (f['tip'] - b), b + .4 * (f['tip'] - b)    # low() grows with the knuckle's place: bisection
        for _ in range(40):
            mid = (lo + hi) / 2
            if low(f, mid) < level: lo = mid
            else: hi = mid
        out.append({'k': f['k'], 'd': f['d'], 'r': f['r'], 'tip': at(f, f['tip']), 'j': joints(f, (lo + hi) / 2)})
    return out


def finger_shares(p, lab, fingers):
    """The shares of [hand, thumb 1-3, index 1-3, ...] of a hand vertex at p (hand frame) with finger label lab. A finger's
    vertex goes to its bones by where it is along the finger, blended across each joint; a palm vertex near the knuckles
    goes with the nearest finger, one near the base of the thumb partly with the thumb."""
    sh = np.zeros(1 + 3 * len(fingers)); sh[0] = 1
    fi = next((i for i, f in enumerate(fingers) if f['k'] == lab), None)
    if fi is None:
        best = None
        for i, f in enumerate(fingers[1:], 1):
            j = f['j']; s = (p - j[0]) @ f['d']; ln = (f['tip'] - j[0]) @ f['d']
            if s < -.5 * BLEND * FINGER_SEG[0] * ln: continue
            dd = np.linalg.norm(p - j[0] - s * f['d'])
            if best is None or dd < best[0]: best = (dd, i)
        if best is None:
            th = fingers[0]; a, b = th['j'][0], th['j'][1]; ab = b - a; t = np.clip((p - a) @ ab / (ab @ ab), 0, 1)
            r = np.linalg.norm(p - a - ab * t); R = .03
            w = (1 - smooth(R * .5, R, r)) * smooth(0, .6, t)
            sh[0], sh[1] = 1 - w, w
            return sh
        fi = best[1]
    f = fingers[fi]; j = f['j']; s = (p - j[0]) @ f['d']
    b1, b2, ln = (j[1] - j[0]) @ f['d'], (j[2] - j[0]) @ f['d'], (f['tip'] - j[0]) @ f['d']
    h1, h2 = BLEND * min(b1, b2 - b1), BLEND * min(b2 - b1, ln - b2)
    w1, w2 = smooth(b1 - h1, b1 + h1, s), smooth(b2 - h2, b2 + h2, s)
    w0 = 1. if fi == 0 else smooth(-BLEND * b1 * .5, BLEND * b1 * .5, s)   # the thumb's own vertices are all off the palm
    sh[0] = 1 - w0; sh[1 + 3 * fi:4 + 3 * fi] = [w0 - w1, w1 - w2, w2]
    return sh


def fist_of(fg, l, n, thumb):
    """The fist's local rotations of the three bones of each finger of fingers_of. A finger bends toward the palm (n) by
    FIST at its joints; the thumb, from its base, lies across the middle phalanges of the curled index and middle
    finger: its last joint over the index's, its tip over the middle finger's."""
    out, mid = [], []
    for F in fg[1:]:
        j, d = F['j'], F['d']; ax = unit(np.cross(d, unit(n - d * (n @ d))))   # turning d toward n
        q = [qaxis(ax, a) for a in FIST]; out.append(q)
        R0, R1 = qm(q[0]), qm(qmul(q[0], q[1]))
        j1 = j[0] + R0 @ (j[1] - j[0]); j2 = j1 + R1 @ (j[2] - j[1]); mid.append((j1 + j2) / 2 + n * THUMB_ON * (F['r'] + fg[0]['r']))
    j, tip = fg[0]['j'], fg[0]['tip']; a, b = np.linalg.norm(j[1] - j[0]), np.linalg.norm(j[2] - j[1])
    I2 = mid[0]; T2 = I2 + unit(mid[1] - mid[0]) * np.linalg.norm(tip - j[2])
    u = I2 - j[0]; dist = np.clip(np.linalg.norm(u), abs(a - b) + 1e-6, a + b - 1e-6); u = unit(u)   # two-bone reach
    x = (a * a - b * b + dist * dist) / (2 * dist); pole = unit(thumb * l + n); pole = unit(pole - u * (pole @ u))
    M2 = j[0] + u * x + pole * np.sqrt(max(a * a - x * x, 0))
    W = [qarc(unit(j[1] - j[0]), unit(M2 - j[0]))]
    W.append(qarc(unit(j[2] - j[1]), unit(I2 - M2))); W.append(qarc(unit(tip - j[2]), unit(T2 - I2)))
    return [[W[0], qmul(qinv(W[0]), W[1]), qmul(qinv(W[1]), W[2])]] + out


def hand_frame(L, w, R):
    """Unit axes of a hand in its bone's frame: l across the hand, n out of the palm; and the side (+1/-1 along l) of
    the thumb. L: the hand's vertices in the bone's frame, w: their weights on it, R: the bone's bind rotation."""
    core = L[w >= .6]
    c0 = core - core.mean(0); evec = np.linalg.eigh(c0.T @ c0 / len(c0))[1]
    y = np.array([0, 1., 0]); n = evec[:, 0] - y * (evec[:, 0] @ y); n /= np.linalg.norm(n)
    if (R @ n)[2] < 0: n = -n            # palms face forward in the bind pose (Denis's drawing)
    l = np.cross(y, n); l /= np.linalg.norm(l)
    hy, hl = core @ y, core @ l; lo = (hy > .02) & (hy < .09)
    thumb = 1 if np.percentile(hl[lo], 97) > -np.percentile(hl[lo], 3) else -1
    return l, n, thumb


def main(pkg, out, drawing):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); J = f(me['jnt'], np.uint8).reshape(-1, 4); W = f(me['wgt']).reshape(-1, 4)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    bones = m['bones']; idx = {b['n']: i for i, b in enumerate(bones)}
    G = [None] * len(bones)
    for i, b in enumerate(bones):
        M = np.eye(4); M[:3, :3] = qm(b['q']); M[:3, 3] = b['t']; G[i] = M if b['p'] < 0 else G[b['p']] @ M
    # --- the fingers: the mesh welded across its texture seams, then each hand's fingers on it ---
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    weld = weld.ravel(); T = weld[I]
    E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    jn, wn = J.astype(np.int64).copy(), W.astype(np.float64).copy(); fingers = []
    for side in ('Left', 'Right'):
        hi = idx[side + 'Hand']; w = ((J == hi) * W).sum(1); Gi = G[hi]; inv = np.linalg.inv(Gi)
        L = P @ inv[:3, :3].T + inv[:3, 3]
        l, n, thumb = hand_frame(L[w >= HAND_W], w[w >= HAND_W], Gi[:3, :3])
        ws = np.unique(weld[w >= HAND_W]); ins = np.zeros(len(first), bool); ins[ws] = True
        Lw = L[first]; nb = [[] for _ in first]
        for u, v in E[ins[E[:, 0]] & ins[E[:, 1]]]:
            dl = float(np.linalg.norm(Lw[u] - Lw[v])); nb[u].append((int(v), dl)); nb[v].append((int(u), dl))
        lab = branches(Lw, nb, ws)
        fg = fingers_of(Lw, lab, l, n, thumb)
        base = len(bones) + len(fingers)
        fists = fist_of(fg, l, n, thumb)
        for i, F in enumerate(fg):
            j, fist = F['j'], fists[i]
            for k in range(3):
                fingers.append({'n': side + 'Hand' + NAMES[i] + str(k + 1), 'p': side + 'Hand' if k == 0 else side + 'Hand' + NAMES[i] + str(k),
                                't': [round(float(v), 5) for v in (j[0] if k == 0 else j[k] - j[k - 1])], 'fist': [round(float(v), 5) for v in fist[k]]})
        for v in np.nonzero(w >= HAND_W)[0]:
            sh = finger_shares(L[v], lab[weld[v]], fg)
            inf = {int(a): float(b) for a, b in zip(jn[v], wn[v]) if b > 0 and a != hi}
            for k, s in enumerate(sh):
                if s > 1e-4: inf[hi if k == 0 else base + k - 1] = inf.get(hi if k == 0 else base + k - 1, 0) + s * w[v]
            top = sorted(inf.items(), key=lambda kv: -kv[1])[:4]; tot = sum(b for _, b in top)
            jn[v] = [a for a, _ in top] + [0] * (4 - len(top)); wn[v] = [b / tot for _, b in top] + [0] * (4 - len(top))
        print(side, 'hand: thumb side', thumb, 'fingers', [int((lab == F['k']).sum()) for F in fg], 'vertices on them')
    if len(bones) + len(fingers) > 255: sys.exit('too many bones for uint8 skin indices')
    # --- hair spikes ---
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
    on = (wn * (jn >= len(bones))).sum(1); line = np.minimum(line, 1 - (1 - LINE_FINGER) * on).astype(np.float32)
    print('outline thinned on', int(face.sum()), 'face and', int((on > 0).sum()), 'finger vertices')
    flat = (smooth(.05, .45, N[:, 2]) * smooth(.3, .7, wh)).astype(np.float32)
    print('flat light on', int((flat > .5).sum()), 'vertices of the head')
    blob = line.tobytes(); oj = len(blob); blob += jn.astype(np.uint8).tobytes(); ow = len(blob); blob += wn.astype(np.float32).tobytes()
    of = len(blob); blob += flat.tobytes()
    look = {'v': 3, 'fingers': fingers, 'skin': [[oj, int(jn.size)], [ow, int(wn.size)]], 'line': [0, int(line.size)],
            'flat': [of, int(flat.size)], 'spikes': spikes}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(out, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look', len(blob), 'B,', len(fingers), 'finger bones')


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
