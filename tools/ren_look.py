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
        of the head, FLAT_BODY on the rest of the front, fading to 0 by the sides, where tools/paint_from_drawing.py
        paints the drawing): the drawing has its own shading (the anime muscles too), the light only darkened it in
        muddy bands; the sides and the back keep the toon light, for the volume
  line: [byte offset, count] float32 per vertex: the outline's width there (1; LINE_FACE on the front of the face,
        where the shell around the nose showed as a dark wedge; LINE_FINGER on the fingers, whose shells stuck out
        between the curled fingers of the fist)
  sash: {ribbons: [{j: SASH_SEG + 1 points in the Hips bone's frame, from under the band to the tip; fix: how many of
        them stay fixed on the hips; tuck: m under the band; w: width; a: unit across; n: unit out of its face; c: colour}], body: [body_shape of each of BODY], blend: [byte offset, count] uint16: the
        vertices shared between the parts (BLEND_W)}: the
        sash's two hanging tails as ribbons of their own (Meshy fused them with the trousers and the vest), where the
        drawing has them seen from the front; tools/paint_from_drawing.py paints the old ones over
  spikes: [{p (base), d (unit direction), t (unit: the lock's thin side, outward), len, r}] in the Head bone's frame:
        anime hair locks where DRAWING (Denis's character sheet, fit as tools/paint_from_drawing.py) has the tips of its
        hair's silhouette seen from the front (each reaching that tip, tilted back), and clumps on the back of the head
        kept inside that silhouette (Meshy's hair is a round mass seen from the side and the back)
"""
import heapq, json, os, sys
import numpy as np
from PIL import Image

HAND_W = .3          # vertices with at least this weight on a hand bone belong to the hand
LINE_FACE = .2       # outline width kept on the front of the face
LINE_FINGER = .4     # and on the fingers
FLAT_BODY = 1.       # flat light on the front of the body (the drawing), as on the face
PERSIST = .015       # a finger stands out at least this far (geodesic, m) from where it joins the hand
FINGER_SEG = (.45, .30, .25)    # proximal, middle and distal phalanx: shares of a finger's length
FREE = .80           # the free part of a finger (from the web between the fingers to the tip): share of its length
THUMB_IP = .5        # the thumb's last joint: this share of its free part from the web
BLEND = .35          # a joint's skin blend reaches this share of the shorter phalanx beside it, on each side
FIST = (82, 100, 60)    # the fist: bend (degrees) at the knuckle, middle and last joint of a finger
THUMB_ON = 1.1      # in the fist the thumb lies across the index and middle finger, this many radii in front of them
NAMES = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')
# The sash's tails: on the model, orange below SASH_BAND (m, the band's lower edge) in pieces of at least SASH_MIN
# vertices (painted over, tools/paint_from_drawing.py); as ribbons, the drawing's two tails seen from the front, each of
# SASH_SEG bones, SASH_GAP m in front of the body, SASH_W m wide (clamped).
SASH_BAND, SASH_MIN, SASH_SEG, SASH_GAP, SASH_W = 1.06, 200, 9, .018, (.06, .1)
SASH_TUCK, SASH_FIX = .012, .05   # a ribbon starts this far under the band's front; fixed on the hips to this far below it
# The body the sash stays out of: around each of these bones (to its child), the volume of the mesh's vertices that
# follow it (weight BODY_W and more: the trousers, the vest's front flaps on the thighs, the hips with the crotch and the
# belly), full
# (all of it, the gaps under the flaps too), measured in BODY_BINS slices along the bone and BODY_SECT sectors around it:
# per cell the farthest vertex, widened to its neighbours' (none is missed between two cells).
BODY = {'Hips': 'Spine02', 'Spine02': 'Spine01', 'LeftUpLeg': 'LeftLeg', 'LeftLeg': 'LeftFoot', 'RightUpLeg': 'RightLeg', 'RightLeg': 'RightFoot'}   # bone: its child
BODY_W, BODY_BINS, BODY_SECT = {'*': .5, 'Hips': .25}, 12, 24   # the hips' with the crotch (shared by the hips and both thighs)
# The body between those parts (the trousers' crotch between the legs, the knees, the hips' creases): its vertices with
# BLEND_W and more of their weight on a second part, one about every BLEND_D m between the heights BLEND_Y (m). They
# stretch between the parts as the legs move, so no part's shape holds them: the sash keeps off them as drawn each frame.
BLEND_W, BLEND_D, BLEND_Y = .2, .025, (.25, 1.1)


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


# Hair spikes: those of the drawing's silhouette (front view) are tilted SPIKE_TILT degrees back and start SPIKE_IN m
# inside the hair mass; a tip less than SPIKE_MIN m beyond the model's hair is left out. HAIR_BELOW: the hair is looked
# for down to this far (m) below the head's centre. BACK_SPIKES: (azimuth from the front, elevation, upward flow).
SPIKE_TILT, SPIKE_IN, SPIKE_MIN, HAIR_BELOW = 25, .025, .012, .08
BACK_SPIKES = [(110, 5, -.25), (140, 8, -.3), (165, 10, -.35), (195, 10, -.35), (220, 8, -.3), (250, 5, -.25),
               (125, 35, .1), (160, 40, .1), (200, 40, .1), (235, 35, .1), (145, 65, .4), (215, 65, .4), (180, 75, .5)]


def hair_profile(D, mask, c, below):
    """The drawing's hair seen from the front, as its outer radius (px) from the head's centre c per degree (from up,
    clockwise): the dark, grey-purple part of the silhouette above c's height + below (the vest's teal is not hair)."""
    from scipy import ndimage
    R, G, B = D[..., 0], D[..., 1], D[..., 2]
    hc = (D.max(2) < 150) & (np.abs(R - B) < 35) & (G - R < 25) & (B - G < 30)
    rows = np.zeros_like(mask); rows[:int(c[1] + below)] = True
    hair = ndimage.binary_closing(mask & rows & hc, iterations=2)
    lab, n = ndimage.label(hair); hair = lab == (np.argmax(ndimage.sum(hair, lab, range(1, n + 1))) + 1)
    ys, xs = np.nonzero(hair); ang = (np.degrees(np.arctan2(xs - c[0], -(ys - c[1]))) % 360).astype(int)
    prof = np.zeros(360); np.maximum.at(prof, ang, np.hypot(xs - c[0], ys - c[1]))
    return ndimage.uniform_filter1d(prof, 3, mode='wrap')


def hair_tips(prof):
    """The spikes of a hair profile: (angle, radius px, width px) at each local maximum within 10 degrees that stands
    6 px above its surroundings, then one every 15 degrees where none is near, over the hair's top half."""
    tips = []
    for a in range(360):
        if prof[a] <= 0: continue
        win = prof[[(a + k) % 360 for k in range(-10, 11)]]
        if prof[a] == win.max() and prof[a] - win.min() > 6: tips.append(a)
    for a in range(-90, 91, 15):
        if prof[a % 360] > 0 and all(min(abs(a % 360 - t), 360 - abs(a % 360 - t)) > 8 for t in tips): tips.append(a % 360)
    out = []
    for a in sorted(tips):
        r = prof[a]; w = 1
        while w < 20 and prof[(a - w) % 360] > r - 15 and prof[(a + w) % 360] > r - 15: w += 1
        out.append((a, float(r), float(2 * r * np.sin(np.radians(w)))))
    return [t for t in out if t[0] <= 100 or t[0] >= 260]



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


def sash_tails(P, col, I):
    """The orange sash's two hanging tails (Meshy made them part of the trousers' and the vest's skin): per tail the
    mesh's vertex indices, the largest first. col: the texture's colour at each vertex."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    orange = (col[:, 0] > 170) & (col[:, 1] > 70) & (col[:, 1] < 170) & (col[:, 2] < 90) & (col[:, 0] - col[:, 1] > 50)
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    nw = len(first); ow = np.zeros(nw); np.add.at(ow, weld, orange.astype(float)); ow = ow / np.bincount(weld, minlength=nw) > .5
    Pw = P[first]; ring = ow & (Pw[:, 1] > SASH_BAND)
    tail = ow & (Pw[:, 1] <= SASH_BAND) & (np.abs(Pw[:, 0]) < .33)
    T = weld[I]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    E = E[tail[E[:, 0]] & tail[E[:, 1]]]
    lab = connected_components(coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(nw, nw)), directed=False)[1]
    ids, n = np.unique(lab[tail], return_counts=True)
    return [np.nonzero(tail[weld] & (lab[weld] == ids[k]))[0] for k in np.argsort(-n) if n[k] >= SASH_MIN]


def sash_orange(D):
    """The drawing's pixels of the sash's orange (not the skin's warm shadows: far less blue than red)."""
    R, G, B = D[..., 0], D[..., 1], D[..., 2]
    return (R > 170) & (G > 60) & (G < 185) & (R - B > 140)


def sash_band_end(orange):
    """The last row of the sash's band in the drawing: the first run of rows more than 100 px orange (the tails widen
    lower down, two of them can be as wide again)."""
    cnt = orange.sum(1); b = int(np.argmax(cnt > 100))
    while b + 1 < len(cnt) and cnt[b + 1] > 100: b += 1
    return b


def body_shape(P, J, W, G, idx, bone, child):
    """The body around a bone, for the sash not to go into it: in the bone's bind frame, along its axis (to child's joint)
    in BODY_BINS slices over its vertices (weight BODY_W[bone] and more), the radius per BODY_SECT sectors around the axis: the
    farthest vertex in the cell, then the largest of the cell and its 8 neighbours. {b, ax, u (sector 0's direction),
    len, t: [t0, t1] (bone lengths), r: [bins][sectors]}."""
    b = idx[bone]; inv = np.linalg.inv(G[b]); w = ((J == b) * W).sum(1); Q = P[w >= BODY_W.get(bone, BODY_W['*'])] @ inv[:3, :3].T + inv[:3, 3]
    a = inv[:3, :3] @ G[idx[child]][:3, 3] + inv[:3, 3]; ln = float(np.linalg.norm(a)); ax = a / ln
    u = unit(np.cross(ax, [1., 0, 0] if abs(ax[0]) < .9 else [0, 0, 1.])); v = np.cross(ax, u)
    t = Q @ ax / ln; rad = Q - np.outer(t * ln, ax); r = np.linalg.norm(rad, axis=1)
    sec = ((np.arctan2(rad @ v, rad @ u) + np.pi) / (2 * np.pi) * BODY_SECT).astype(int) % BODY_SECT
    t0, t1 = float(t.min()), float(t.max()); bi = np.clip(((t - t0) / (t1 - t0) * BODY_BINS).astype(int), 0, BODY_BINS - 1)
    R = np.zeros((BODY_BINS, BODY_SECT)); np.maximum.at(R, (bi, sec), r)
    for _ in range(BODY_SECT):   # empty cells from their neighbours
        Z = R == 0
        if not Z.any(): break
        N = np.maximum(np.roll(R, 1, 1), np.roll(R, -1, 1)); N = np.maximum(N, np.vstack([R[1:], R[-1:]])); N = np.maximum(N, np.vstack([R[:1], R[:-1]]))
        R[Z] = N[Z]
    D = R.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            D = np.maximum(D, np.roll(np.vstack([R[:1]] * max(0, -di) + [R] + [R[-1:]] * max(0, di))[max(0, di):len(R) + max(0, di)], dj, 1))
    return {'b': bone, 'ax': [round(float(x), 5) for x in ax], 'u': [round(float(x), 5) for x in u], 'len': round(ln, 5),
            't': [round(t0, 4), round(t1, 4)], 'r': [[round(float(x), 4) for x in row] for row in D]}


def drawing_tails(D):
    """The sash's two hanging tails in the drawing (front view): per tail, largest first, {top: (x, y) px of the middle of
    its first row under the band, tip: its lowest pixel, w: px wide (median of its upper half's rows), c: its colour}."""
    from scipy import ndimage
    orange = sash_orange(D); below = orange.copy(); below[:sash_band_end(orange) + 6] = False
    lab, n = ndimage.label(below); sizes = ndimage.sum(below, lab, range(1, n + 1)); out = []
    for k in np.argsort(-sizes)[:2]:
        ys, xs = np.nonzero(lab == k + 1); r0 = ys.min(); rw = []
        for y in range(r0, r0 + (ys.max() - r0) // 2):
            x = xs[ys == y]
            if len(x): rw.append(x.max() - x.min() + 1)
        top = xs[ys == r0].mean(); i = np.argmax(ys)
        out.append({'top': (float(top), float(r0)), 'tip': (float(xs[i]), float(ys[i])), 'w': float(np.median(rw)), 'c': [int(v) for v in np.median(D[ys, xs], 0)]})
    return out


def ribbon_of(t, P, sc, cx, by, mid):
    """A hanging ribbon for drawing tail t, in model space: {j: SASH_SEG + 1 points evenly along it, from under the band
    (SASH_TUCK m behind its front at the height mid) out of the band's lower edge (SASH_BAND) where the drawing's tail
    starts across, straight down to the drawing's tip (front view), in front of the body (SASH_GAP, half of it at the band);
    fix: how many from the top stay fixed on the hips (those under the band and SASH_FIX m below it); tuck: m of it under
    the band; w: width (m); a: unit across; n: unit out of its face (forward); c: colour}."""
    def front(x, y):
        near = P[(np.abs(P[:, 0] - x) < .02) & (np.abs(P[:, 1] - y) < .012)]
        return float(near[:, 2].max()) if len(near) else 0.
    x0, x1, y1 = (t['top'][0] - cx) / sc, (t['tip'][0] - cx) / sc, (by - t['tip'][1]) / sc
    path = [[x0, mid, front(x0, mid) - SASH_TUCK]]
    for u in np.linspace(0, 1, 16):
        x, y = x0 + (x1 - x0) * u, SASH_BAND + (y1 - SASH_BAND) * u
        path.append([x, y, front(x, y) + SASH_GAP * (.5 + .5 * min(1, (SASH_BAND - y) / .1))])
    path = np.array(path); arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    at = np.linspace(0, arc[-1], SASH_SEG + 1); j = np.array([np.interp(at, arc, path[:, k]) for k in range(3)]).T
    fix = int((at <= arc[1] + SASH_FIX + 1e-9).sum())
    d = unit(j[-1] - j[1]); a = unit(np.cross(d, [0, 0, 1.])); n = unit(np.cross(a, d))
    if n[2] < 0: n, a = -n, -a
    return {'j': j, 'fix': fix, 'tuck': float(arc[1]), 'w': float(np.clip(t['w'] / sc, SASH_W[0], SASH_W[1])), 'a': a, 'n': n, 'c': t['c']}


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
    hair = hair_profile(D, mask, (cx + c[0] * sc, by - c[1] * sc), HAIR_BELOW * sc)
    def add(base, axis, ln, r):
        rad = unit(base - c); t = rad - axis * (rad @ axis); t = unit(t) if np.linalg.norm(t) > 1e-6 else unit(np.cross(axis, [1., 0, 0]))
        spikes.append({'p': [round(float(v), 5) for v in inv[:3, :3] @ base + inv[:3, 3]], 'd': [round(float(v), 5) for v in inv[:3, :3] @ axis],
                       't': [round(float(v), 5) for v in inv[:3, :3] @ t], 'len': round(float(ln), 4), 'r': round(float(r), 4)})
    # the drawing's spikes, seen from the front: each reaches where the drawing's tip is, tilted back
    tilt = np.radians(SPIKE_TILT)
    for th, rpx, width in hair_tips(hair):
        dp = np.array([np.sin(np.radians(th)), np.cos(np.radians(th)), 0.]); r0 = ray_far(P, Th, c, dp); rt = rpx / sc
        if r0 <= 0 or rt - r0 < SPIKE_MIN: continue
        axis = unit(dp * np.cos(tilt) + np.array([0, 0, -np.sin(tilt)])); base = c + dp * (r0 - SPIKE_IN)
        ln = (rt - r0 + SPIKE_IN) / np.cos(tilt)
        add(base, axis, ln, np.clip(width / sc * .5, .022, .045))
    nf = len(spikes)
    # the back of the head (no drawing there): clumps out and back, the crown's up, the nape's down; from the front
    # each stays inside the drawing's silhouette
    for k, (az, el, up) in enumerate(BACK_SPIKES):
        a, e = np.radians(az), np.radians(el)
        d = np.array([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)]); r0 = ray_far(P, Th, c, d)
        if r0 <= 0: continue
        axis = unit(d + np.array([0, up, -.35])); base = c + d * (r0 - SPIKE_IN); ln = .13 - .03 * ((k * 7919) % 5) / 4
        while ln > .05 and not inside(base + axis * ln): ln -= .01
        if ln <= .05: continue
        add(base, axis, ln, .03 + .01 * ((k * 104729) % 5) / 4)
    print('spikes', nf, 'from the drawing,', len(spikes) - nf, 'on the back')
    # --- the sash: its tails become ribbons hanging from the band (the tails painted on the body go, paint_from_drawing) ---
    UVs = f(me['uv']).reshape(-1, 2); tex0 = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(int)
    col0 = tex0[np.clip((UVs[:, 1] * tex0.shape[0]).astype(int), 0, tex0.shape[0] - 1), np.clip((UVs[:, 0] * tex0.shape[1]).astype(int), 0, tex0.shape[1] - 1)]
    hp = idx['Hips']; Gh = G[hp]; ih = np.linalg.inv(Gh); ribbons = []
    ring = []   # the band: the heights where the sash's orange goes all around the waist
    for y0 in np.arange(.9, 1.3, .01):
        sel = (col0[:, 0] > 170) & (col0[:, 0] - col0[:, 1] > 50) & (col0[:, 2] < 90) & (P[:, 1] >= y0) & (P[:, 1] < y0 + .01) & (np.abs(P[:, 0]) < .3)
        if sel.any() and len(np.unique((np.degrees(np.arctan2(P[sel, 0], P[sel, 2])) % 360 // 15).astype(int))) * 15 >= 200: ring.append(y0 + .005)
    mid = (min(ring) + max(ring)) / 2
    for t in drawing_tails(D):
        r = ribbon_of(t, P, sc, cx, by, mid)
        ribbons.append({'j': [[round(float(v), 5) for v in ih[:3, :3] @ q + ih[:3, 3]] for q in r['j']], 'w': round(r['w'], 4), 'fix': r['fix'], 'tuck': round(r['tuck'], 4),
                        'a': [round(float(v), 5) for v in ih[:3, :3] @ r['a']], 'n': [round(float(v), 5) for v in ih[:3, :3] @ r['n']], 'c': r['c']})
    print('sash band from %.2f to %.2f m; ribbons fixed at the top: %s' % (min(ring) - .005, max(ring) + .005, [r['fix'] for r in ribbons]))
    for r in ribbons: r['c'] = ribbons[0]['c']   # one orange for both tails (their own differed a little)
    body = [body_shape(P, J, W, G, idx, b, c) for b, c in BODY.items()]
    Wb = np.stack([((J == idx[b]) * W).sum(1) for b in BODY], 1); second = np.sort(Wb, 1)[:, -2]
    shared = (second >= BLEND_W) & (Wb.sum(1) >= .9) & (P[:, 1] > BLEND_Y[0]) & (P[:, 1] < BLEND_Y[1])
    _, one = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True)   # one copy of each seam's vertices
    cand = one[shared[one]]
    blend = np.sort(cand[np.unique(np.floor(P[cand] / BLEND_D).astype(np.int64), axis=0, return_index=True)[1]]).astype(np.uint16)
    print('sash ribbons', [(len(r['j']), r['w']) for r in ribbons], 'body shapes', [(x['b'], round(float(np.max(x['r'])), 3)) for x in body], 'shared points', len(blend))
    # --- the outline on the face: thin where the head faces forward and the texture is skin ---
    N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2)
    tex = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(int); ts = tex.shape[0]
    col = tex[np.clip((UV[:, 1] * ts).astype(int), 0, ts - 1), np.clip((UV[:, 0] * ts).astype(int), 0, ts - 1)]
    skin = (col[:, 0] > 150) & (col[:, 1] > 95) & (col[:, 0] - col[:, 2] > 50)
    face = (wh >= .5) & (N[:, 2] > .15) & skin
    line = np.ones(len(P), np.float32); line[face] = LINE_FACE
    on = (wn * (jn >= len(bones))).sum(1); line = np.minimum(line, 1 - (1 - LINE_FINGER) * on).astype(np.float32)
    print('outline thinned on', int(face.sum()), 'face and', int((on > 0).sum()), 'finger vertices')
    flat = np.maximum(smooth(.05, .45, N[:, 2]) * smooth(.3, .7, wh), FLAT_BODY * smooth(.1, .45, N[:, 2])).astype(np.float32)
    print('flat light on', int((flat > .5).sum()), 'vertices (head', int(((flat > .5) & (wh > .5)).sum()), ')')
    blob = line.tobytes(); oj = len(blob); blob += jn.astype(np.uint8).tobytes(); ow = len(blob); blob += wn.astype(np.float32).tobytes()
    of = len(blob); blob += flat.tobytes(); ob = len(blob); blob += blend.tobytes()
    look = {'v': 3, 'fingers': fingers, 'skin': [[oj, int(jn.size)], [ow, int(wn.size)]], 'line': [0, int(line.size)],
            'flat': [of, int(flat.size)], 'spikes': spikes, 'sash': {'ribbons': ribbons, 'body': body, 'blend': [ob, int(blend.size)]}}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(out, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look', len(blob), 'B,', len(fingers), 'finger bones')


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
