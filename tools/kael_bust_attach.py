#!/usr/bin/env python3
"""Kael's Meshy bust on his bones (11/11/2026, Denis: "ora adopera"; docs/meshy/KAEL.md, "Busto sulle ossa"): the bust and
arms from Meshy, cleaned by tools/kael_bust.py with Ren's hands (busto_k6.glb and busto_k6_hands.npz beside it), as a part
of Kael's package like his head (src/e_model.js mdPartData): his own torso, arms and hands hidden under it, his head on top,
his legs below.

- Where: SCALE m per bust unit, its sash's middle (SASH_B, bust units) on his (SASH_K m), centred as his (CENTRE). Measured:
  at this scale its chest's depth, its shoulders' height and its sash lie on his; a fit of the whole torso's surface gave
  no better place (its shape is the sheet's, his the first drawing's: its deltoids are 3 cm narrower each).
- Its skirt's flat bottom left out (Meshy closed it: a black lid across the thighs; the skirt is drawn from both sides).
  Its collar's top left out under the head's collar (COLLAR_CUT: its trim stuck out of it as the head tipped back).
- Its joints: the elbows and the wrists from its bracers' purple bands (each band's middle; the joints as far from them as
  his are from his, in proportion to the bracers' lengths); the shoulders from the deltoids (a sphere fit on each, his
  measured the same way 1-2 cm from his joints): SHOULDER m from his (inward, up, forward). Its arms are a little
  shorter than his (the sheet's): his arm bones are shortened to them (src/e_model.js: the part's bones), the arms keep
  their shape.
- Posed as his bind pose (the animations are made for it): each upper arm turned about its shoulder onto his upper arm's
  direction, each forearm about its elbow onto his, each hand about its wrist as Ren's lies in the world in his (his hand
  bones and Kael's differ by 25 degrees on the left, 4 on the right, and the animations keep it: so in every pose the
  fists face as Ren's do; the fists' turns Ren's, turned into Kael's hand bones' frames). Skinned for that (provisional): the share of torso, upper arm, forearm and hand of his nearest
  point facing the same way (Ren's for his hands), smoothed.
- Skinned: his nearest point's weights facing the same way, its arms first stretched to his arms' lengths (so the elbow's
  and the wrist's bends fall where his do); Ren's own weights on Ren's hands, finger bones included; smoothed across the
  wrists' seams (SEAM m round them).
- The finger bones: Ren's, laid as his hands were (the fit of tools/kael_bust.py, the place, the pose: in the hand bone as
  Ren's, scaled), the fists' turns Ren's (src/e_model.js: the part's fingers in place of the look's), but the thumbs'
  (thumb_fist: folded over the fingers; his stood out straight ahead of the index finger).
- The glove's edge on the hands drawn by the game (src/e_model.js aGlove: per vertex its signed distance to the painted
  edge): in the fist the painted edge, bent over the knuckles, broke into teeth.
- Light: flat (its paint has the sheet's shadows), but on the hands the game's (HAND_FLAT; Denis, 11/11, on the fists in
  flat light, dark blocks: "sono da migliorare nettamente guarda le sue immagini di riferimento").
- His own triangles hidden: those mostly on the upper body's bones (HIDE_W), his torso from under its sash up (his sash
  and its knot were wider than its), and his trousers under its skirt. The skirt (the sheet's tunic, over the trousers):
  where his baggy trousers stood out of it (1-2 cm at the sides), pushed out SKIRT_OUT over them, smoothed. His old sash's
  tails stay (they hang from under its knot) until the ribbons.

usage: python3 tools/kael_bust_attach.py BUST.glb   (writes wip_assets/kael/kael_bust.json, .bin, .png; Kael's look needs
bust:true in CFG.looks.kael)"""
import io, json, os, sys
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mesh_prep'))
import glbio

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
KAEL_PKG = os.path.join(ROOT, 'wip_assets', 'kael')
REN = os.path.join(ROOT, 'assets', 'ren', 'ren.json'), os.path.join(ROOT, 'viewer_assets', 'ren', 'ren_look.json')
SCALE, SASH_B, SASH_K, CENTRE = .42, -.21, 1.08, (-.005, 0.)
SHOULDER = (.015, -.010, .022)   # m: the bust's shoulder joints from his: inward, up, forward
SIDES = (('Left', 1), ('Right', -1))   # (his left: +x)
GROUPS = ('Arm', 'ForeArm', 'Hand')    # (with the torso: the pose's four)
FACE = .3                              # (nearest points: their normals within this of each other's)
SMOOTH, SEAM, SEAM_SMOOTH = 4, .03, 6
HIDE_W = .5
GLOVE_PAD = .007                         # bust units (3 mm): the texture's glove painted skin so far from its edge
GLOVE_C, BLACK_C, INK_C, SKIN_C = (65, 49, 74), (26, 21, 27), (9, 6, 9), (250, 191, 151)   # the bust's palette (tools/kael_bust.py PAL)
ARM_LINE = (float(os.environ.get('KAEL_ARM_PUSH', .3)), .7)   # the arms' outline: its push back (of the body's) and its width
HAND_LINE, BODY_LINE_BACK = (.10, .65), .02   # the hands' outline: its push back (of the body's, BODY_LINE_BACK m: CFG.looks.kael.line.back) and its width
FINGER_THICK = 1.                        # the fingers' thickness about their bones (tried 1.25: the fingers merged into a lump, the fist a skin blob, the open hand a mitten)
HAND_RATIO = 1.03                        # the hands' length (cuff to fingertip) over the bracer's, as the sheet draws them (Denis, 12/11: "dimensioni delle mani falle come si deve")
HAND_NSMOOTH = 6                         # rounds of smoothing of the hands' normals (the light's bands clean)
HAND_SMOOTH = 0                          # rounds of smoothing of the weights on Ren's hands (tried 4: the fist opened, a hole by the thumb)
THUMB_BASE = dict(zip(('Right', 'Left'), (float(v) for v in os.environ.get('KAEL_THUMB_BASE', '25,40').split(','))))   # degrees, per hand: the thumb's first bone turned at most so far in the fist (Ren's 55-60 turned it all from its base: the skin between it and the palm stretched into a blade toward the wrist), its middle joint bending instead
THUMB_SCALE = tuple(float(v) for v in os.environ.get('KAEL_THUMB_SCALE', '.7,.85').split(','))   # the thumb past its web: so long, so thick (Ren's as long as the index finger; Denis, 12/11: "fallo più piccolo"; all of it at .7 a pencil beside the fingers)
THUMB_SIDE = tuple(float(v) for v in os.environ.get('KAEL_THUMB_SIDE', '20,.012').split(','))   # the thumb's tip held within [1] m of the index finger's side, with that push (the left one stood out past it, a hitchhiker's thumb)
THUMB_FIST = (1., 1., .002, 50., 1.)    # the thumb folded in the fist (thumb_fist): the pulls of its last joint to the index finger's middle bone and of its tip to the middle finger's, its skin so far (m) out of the fingers' with that push, the pull to its first turns
HAND_FLAT = 0.                           # the hands' share of flat light (the game's toon light: the fists' volume reads, as Ren's)
COLLAR_CUT = (1.472, (.0085, -.005), .11)   # m: its collar over this height within [2] of the neck's axis [1] (the head's collar from 1.464 m)
SASH = (-.32, -.10)                    # the bust's sash: its bottom, its top (bust units)
SKIRT_OUT, SKIRT_WIN, SKIRT_SMOOTH, HEM_KEEP = .006, (.012, .03), 10, .025   # the skirt over his trousers: so far out, looking within [1][0] m of its normal up to [1][1] m out; the push smoothed; his trousers kept up to [3] m over its hem (under it they showed the sky)
UPPER = ('Spine02', 'Spine01', 'Spine', 'neck', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand')
BUST_PURPLE, KAEL_PURPLE = (166, 92, 203), lambda c: (c[:, 2] > 95) & (c[:, 2] - c[:, 1] > 45)


def qm(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mq(R):
    """A rotation matrix's quaternion (x, y, z, w)."""
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1) * 2; return np.array([(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, .25 * s])
    i = int(np.argmax(np.diag(R))); j, k = (i + 1) % 3, (i + 2) % 3
    s = np.sqrt(1 + R[i, i] - R[j, j] - R[k, k]) * 2; q = np.zeros(4)
    q[i] = .25 * s; q[j] = (R[j, i] + R[i, j]) / s; q[k] = (R[k, i] + R[i, k]) / s; q[3] = (R[k, j] - R[j, k]) / s
    return q


def turn(a, b):
    """The least rotation taking direction a onto direction b."""
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = a @ b
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def package(js, pos_key='mesh'):
    J = json.load(open(js)); B = open(js[:-4] + 'bin', 'rb').read(); me = J[pos_key]
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    out = dict(J=J, P=f(me['pos']).reshape(-1, 3).astype(float), N=f(me['nor']).reshape(-1, 3).astype(float), UV=f(me['uv']).reshape(-1, 2).astype(float),
               JN=f(me['jnt'], np.uint8).reshape(-1, 4).astype(np.int64), WG=f(me['wgt']).reshape(-1, 4).astype(float),
               I=f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64), names=[b['n'] for b in J['bones']])
    Wm = []
    for b in J['bones']:
        M = np.eye(4); M[:3, :3] = qm(b['q']); M[:3, 3] = b['t']; Wm.append(Wm[b['p']] @ M if b['p'] >= 0 else M)
    out['Wm'] = np.array(Wm)
    return out


def look(js, n):
    L = json.load(open(js)); B = open(js[:-4] + 'bin', 'rb').read()
    si = np.frombuffer(B, np.uint8, L['skin'][0][1], L['skin'][0][0]).reshape(n, 4).astype(np.int64)
    sw = np.frombuffer(B, np.float32, L['skin'][1][1], L['skin'][1][0]).reshape(n, 4).astype(float)
    return L, si, sw


def fingers_world(fingers, names, Wm):
    """The finger bones' places (identity turns: the hand's) in the bind pose; and the hands' world turns."""
    pos = {}
    for f in fingers:
        if f['p'] in pos: pos[f['n']] = pos[f['p']] + Wm[names.index(f['p'].split('Hand')[0] + 'Hand')][:3, :3] @ np.array(f['t'])
        else: M = Wm[names.index(f['p'])]; pos[f['n']] = M[:3, 3] + M[:3, :3] @ np.array(f['t'])
    return pos


def thumb_fist(side, fingers, X, NX, top, tw, allnames, H, Rk, like=None):
    """The thumb's turns in the fist folded over the fingers (Denis, 12/11: "il pollice è ancora fatto male"): Ren's fist
    kept his thumb straight at its middle joint, its tip curled, and it stood out ahead of the index finger as a spike. In
    the hand bone's frame (the finger bones' rest turns are its), the other fingers as their fists pose them: the thumb's
    first bone turned freely, its second and third bent about the joint's own axis (Ren's tip's), so that its last joint
    lies on the index finger's middle bone and its tip on the middle finger's (THUMB_FIST[0], [1]: their pulls), its skin
    kept THUMB_FIST[2] m out of the fingers' (THUMB_FIST[3]: that push), near the turns it starts from (THUMB_FIST[4]).
    With like (the other hand's result) its last joint and tip as the other's lie by the index's and middle finger's
    middle bones, in the hand's own frame (from the wrist to the middle knuckle, from the little finger to the index, the
    palm's side): Ren's hands differ (his left thumb's first joint by its web, the right's by the wrist), one search
    folded the right thumb over the fingers and left the left one standing up beside the index finger.
    Returns the thumb bones' fists and where its last joint and tip lie in that frame."""
    from scipy.optimize import minimize
    fl = {f['n']: f for f in fingers if f['n'].startswith(side + 'Hand')}
    if os.environ.get('KAEL_THUMB_DUMP'): np.savez(os.environ['KAEL_THUMB_DUMP'] + side + '.npz', X=X, NX=NX, top=top, tw=tw, H=H, Rk=Rk, allnames=np.array(allnames), fingers=np.array(json.dumps([f for f in fingers])))
    rest = {side + 'Hand': np.zeros(3)}
    for n, f in fl.items(): rest[n] = rest[f['p']] + np.array(f['t'])
    th = [side + 'HandThumb%d' % k for k in (1, 2, 3)]
    hb = allnames.index(side + 'Hand'); fi = {n: allnames.index(n) for n in fl}
    on = np.isin(top, [hb] + list(fi.values())); hand = np.nonzero(on.any(1) & ((tw * on).sum(1) > .5))[0]
    V = (X[hand] - H) @ Rk; Nv = NX[hand] @ Rk; T, W = top[hand], tw[hand]
    share = lambda names: (W * np.isin(T, [fi[n] for n in names])).sum(1)
    def pose(q):
        R = {side + 'Hand': np.eye(3)}; P = {side + 'Hand': np.zeros(3)}
        for n in fl:   # (parents before children: the list's order)
            p = fl[n]['p']; R[n] = R[p] @ qm(q[n]); P[n] = P[p] + R[p] @ np.array(fl[n]['t'])
        out = np.zeros_like(V); nout = np.zeros_like(V)
        for k in range(4):
            for n in fl:
                m = T[:, k] == fi[n]
                if m.any(): out[m] += W[m, k, None] * ((V[m] - rest[n]) @ R[n].T + P[n]); nout[m] += W[m, k, None] * (Nv[m] @ R[n].T)
            m = ~np.isin(T[:, k], list(fi.values())); out[m] += W[m, k, None] * V[m]; nout[m] += W[m, k, None] * Nv[m]
        return out, nout, P
    q0 = {n: np.array(fl[n]['fist']) for n in fl}
    Vp, Np, _ = pose(q0)
    others = [n for n in fl if 'Thumb' not in n]
    col = share(others) > .5; Fp, Fn = Vp[col], Np[col] / np.maximum(np.linalg.norm(Np[col], axis=1, keepdims=True), 1e-9); tree = cKDTree(Fp)
    thv = share(th) > .5; t3 = share(th[2:]) > .5
    tip = np.nonzero(t3)[0][np.argmax(np.linalg.norm(V[t3] - rest[th[2]], axis=1))]
    # (the targets on the middle bones' outside: their centres pushed out from the fist's centre by a finger's and a thumb's
    # half thickness, so the thumb lies on them, not sunk into them)
    seg = lambda n: Vp[share([n]) > .5]; I2, M2 = seg(side + 'HandIndex2'), seg(side + 'HandMiddle2')
    rad = lambda P: np.sqrt(np.mean(np.sum((P - P.mean(0)) ** 2, 1)) / 2)   # (about a segment's half thickness)
    out_ = (I2.mean(0) + M2.mean(0)) / 2 - Vp.mean(0); out_ /= np.linalg.norm(out_); r_ = (rad(I2) + rad(M2)) / 2 + rad(V[share(th[2:]) > .5])
    cI = I2.mean(0) + out_ * r_; cM = M2.mean(0) + out_ * r_
    ax_ = rest[side + 'HandMiddle1'] / np.linalg.norm(rest[side + 'HandMiddle1']); zz = rest[side + 'HandIndex1'] - rest[side + 'HandPinky1']; zz -= (zz @ ax_) * ax_; zz /= np.linalg.norm(zz)
    yy = np.cross(zz, ax_) * (1 if side == 'Right' else -1); Fr = np.array([ax_, yy, zz])   # (the hand's own frame: a left hand's the right's mirrored)
    if like is not None: cI = I2.mean(0) + Fr.T @ like[0]; cM = M2.mean(0) + Fr.T @ like[1]
    zi = (Vp[share([n for n in others if 'Index' in n]) > .5] @ Fr[2]).max() + THUMB_SIDE[1]   # (the index finger's side, in the hand's frame)
    t3v = t3[thv]
    q3 = np.array(fl[th[2]]['fist']); ax = q3[:3] / np.linalg.norm(q3[:3])
    rv = lambda r: (lambda a: np.r_[np.sin(a / 2) * r / max(a, 1e-12), np.cos(a / 2)])(np.linalg.norm(r))
    def quats(x):   # (x: the first bone's turn, the middle and the last joints' bends about the joint's axis)
        q = dict(q0); q[th[0]] = rv(x[:3]); q[th[1]] = rv(x[3] * ax); q[th[2]] = rv(x[4] * ax)
        return q
    w0 = q0[th[0]]; a0 = 2 * np.arccos(np.clip(w0[3], -1, 1)); x0 = np.r_[w0[:3] / max(np.linalg.norm(w0[:3]), 1e-12) * a0, 0., 2 * np.arccos(np.clip(q3[3], -1, 1))]
    def cost(x):
        q = quats(x); Vq, _, P = pose(q)
        d, i = tree.query(Vq[thv]); s = ((Vq[thv] - Fp[i]) * Fn[i]).sum(1)
        pen = np.maximum(0, THUMB_FIST[2] - s) * (d < .03)
        side_ = np.sum(np.maximum(0, Vq[thv][t3v] @ Fr[2] - zi) ** 2)   # (its tip not standing out past the index finger's side)
        return (THUMB_SIDE[0] * side_ + THUMB_FIST[0] * np.sum((P[th[2]] - cI) ** 2) + THUMB_FIST[1] * np.sum((Vq[tip] - cM) ** 2) + THUMB_FIST[3] * np.sum(pen ** 2)
                + THUMB_FIST[4] * np.sum((x - x0) ** 2) * 1e-4 + .05 * max(0., np.linalg.norm(x[:3]) - np.radians(THUMB_BASE[side])) ** 2)
    x0 = x0.copy(); a_ = np.linalg.norm(x0[:3]); x0[:3] *= min(1., np.radians(THUMB_BASE[side]) / max(a_, 1e-9))
    best = min((minimize(cost, x0 + dx, method='Powell', options=dict(maxiter=4000, xtol=1e-4, ftol=1e-10)) for dx in (np.zeros(5), np.r_[0, 0, 0, .5, 0], np.r_[0, 0, 0, .9, .3])), key=lambda r: r.fun)
    q = quats(best.x); Vq, _, P = pose(q)
    d, i = tree.query(Vq[thv]); s = ((Vq[thv] - Fp[i]) * Fn[i]).sum(1)
    deg = lambda qq: np.degrees(2 * np.arccos(np.clip(abs(qq[3]), -1, 1)))
    print("%s thumb in the fist: turns %s deg (Ren's %s); its last joint %.1f mm from its place on the index's middle bone, its tip %.1f mm from its place on the middle finger's (%.1f mm out); its skin at most %.1f mm into the fingers'" % (
        side, [round(deg(q[n])) for n in th], [round(deg(q0[n])) for n in th], 1000 * np.linalg.norm(P[th[2]] - cI), 1000 * np.linalg.norm(Vq[tip] - cM), 1000 * r_, 1000 * max(0., -s[d < .03].min()) if (d < .03).any() else 0))
    return {n: q[n] for n in th}, (Fr @ (P[th[2]] - I2.mean(0)), Fr @ (Vq[tip] - M2.mean(0)))


def weld_graph(P, I):
    _, wv = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_inverse=True); wv = wv.ravel(); nw = wv.max() + 1; W = wv[I]
    E = np.unique(np.sort(np.concatenate([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]), 1), axis=0)
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr()
    return wv, A, np.maximum(np.asarray(A.sum(1)).ravel(), 1)


def smooth(V, wv, A, deg, rounds, sel=None):
    """Per vertex values averaged with their neighbours' (the welded copies as one), rounds times, on sel's vertices."""
    Vw = np.zeros((wv.max() + 1,) + V.shape[1:]); np.add.at(Vw, wv, V); Vw /= np.bincount(wv)[:, None]
    sw = None if sel is None else np.bincount(wv, weights=sel.astype(float)) > 0
    for _ in range(rounds):
        nxt = .5 * Vw + .5 * (A @ Vw) / deg[:, None]
        Vw = nxt if sw is None else np.where(sw[:, None], nxt, Vw)
    return Vw[wv]


def nearest_facing(src_P, src_N, dst_P, dst_N, k=24, far=.08):
    """For each dst point, the index of the nearest src point whose normal agrees (FACE), else the nearest."""
    d, nn = cKDTree(src_P).query(dst_P, k=k)
    agree = (src_N[nn] * dst_N[:, None, :]).sum(2) > FACE
    agree &= d < far
    first = np.where(agree.any(1), agree.argmax(1), 0)
    return nn[np.arange(len(dst_P)), first]


def forearm(X, pur, sel, E0, H0):
    """The forearm's line (slices' middles, from E0 toward H0) and its bracer's two purple bands' middles: the top's, the cuff's."""
    E, H = E0.copy(), H0.copy()
    for _ in range(4):
        ax = (H - E) / np.linalg.norm(H - E); L = np.linalg.norm(H - E); t = (X - E) @ ax; r = np.linalg.norm((X - E) - np.outer(t, ax), axis=1)
        s = sel & (r < .07); c1 = X[s & (t > .02) & (t < .06)].mean(0); c2 = X[s & (t > L - .06) & (t < L - .02)].mean(0)
        d = (c2 - c1) / np.linalg.norm(c2 - c1); E, H = c1 - d * .04, c2 + d * .04
    ax = (H - E) / np.linalg.norm(H - E); L = np.linalg.norm(H - E); t = (X - E) @ ax; r = np.linalg.norm((X - E) - np.outer(t, ax), axis=1)
    s = sel & (r < .09); ts = np.arange(-.05, L + .06, .01)
    fr = np.array([pur[s & (t >= a) & (t < a + .02)].mean() if (s & (t >= a) & (t < a + .02)).sum() > 5 else 0 for a in ts])
    half = L / 2; top = ts[np.argmax(np.where(ts < half, fr, -1))] + .01; cuff = ts[np.argmax(np.where(ts >= half, fr, -1))] + .01
    band = lambda tc: X[s & pur & (np.abs(t - tc) < .015)].mean(0)
    return band(top), band(cuff)


def main(bust):
    K = package(os.path.join(KAEL_PKG, 'kael.json')); names = K['names']; nb = len(names); Wm = K['Wm']
    KL, _, _ = look(os.path.join(KAEL_PKG, 'kael_look.json'), len(K['P']))
    KT = np.asarray(Image.open(os.path.join(KAEL_PKG, 'kael_painted.png')).convert('RGB')).astype(float); S = KT.shape[0]
    kvc = KT[np.clip((K['UV'][:, 1] * S).astype(int), 0, S - 1), np.clip((K['UV'][:, 0] * S).astype(int), 0, S - 1)]
    m = glbio.read(bust); Pb, Nb, UVb, Ib = m['pos'].astype(float), m['nor'].astype(float), m['uv'].astype(float), m['idx'].astype(np.int64)
    side_f = np.load(bust[:-4] + '_hands.npz'); rid = side_f['rid']
    assert np.abs(side_f['pos'] - Pb).max() < 1e-5, 'busto_*_hands.npz is not this GLB\'s'
    BT = Image.open(io.BytesIO(m['img'])).convert('RGB'); bt = np.asarray(BT).astype(float); BS = bt.shape[0]
    bvc = bt[np.clip((UVb[:, 1] * BS).astype(int), 0, BS - 1), np.clip((UVb[:, 0] * BS).astype(int), 0, BS - 1)]
    off = np.array([CENTRE[0], SASH_K - SASH_B * SCALE, CENTRE[1]])
    X = Pb * SCALE + off; NX = Nb / np.maximum(np.linalg.norm(Nb, axis=1, keepdims=True), 1e-9)
    print('placed: %.3f m per unit; from y %.3f to %.3f m' % (SCALE, X[:, 1].min(), X[:, 1].max()))
    # the skirt's lid (Meshy closed its bottom): the largest piece of triangles facing down under the waist
    fn = np.cross(Pb[Ib[:, 1]] - Pb[Ib[:, 0]], Pb[Ib[:, 2]] - Pb[Ib[:, 0]]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12); c = Pb[Ib].mean(1)
    cand = (fn[:, 1] < -.5) & (np.abs(c[:, 0]) < .35) & (c[:, 1] < -.45)
    wv, A, deg = weld_graph(Pb, Ib); W = wv[Ib]
    E = np.concatenate([np.c_[np.arange(len(Ib)), np.sort(W[:, [a, b]], 1)] for a, b in ((0, 1), (1, 2), (2, 0))])
    key = E[:, 1] * (wv.max() + 1) + E[:, 2]; o = np.argsort(key, kind='stable'); ks = key[o]; same = ks[1:] == ks[:-1]
    ta, tb = E[o[1:][same], 0], E[o[:-1][same], 0]; okp = cand[ta] & cand[tb]
    _, lab = connected_components(coo_matrix((np.ones(okp.sum()), (ta[okp], tb[okp])), shape=(len(Ib), len(Ib))), directed=False)
    lid = cand & (lab == np.bincount(lab[cand]).argmax())
    Ib = Ib[~lid]
    print('skirt: its lid left out, %d triangles' % int(lid.sum()))
    # its collar's top under his head's collar (tools/kael_head.py: from its bottom up, as wide as his old one): left out (its
    # purple trim stuck out of the head's as the head tipped back in the high kick)
    cX = X[Ib].mean(1); top = (cX[:, 1] > COLLAR_CUT[0]) & (np.hypot(cX[:, 0] - COLLAR_CUT[1][0], cX[:, 2] - COLLAR_CUT[1][1]) < COLLAR_CUT[2])
    Ib = Ib[~top]
    print('collar: its top over %.3f m left out, %d triangles' % (COLLAR_CUT[0], int(top.sum())))
    wv, A, deg = weld_graph(Pb, Ib)
    # Ren's: his package, his hands' weights and finger bones
    R = package(REN[0]); RL, rsi, rsw = look(REN[1], len(R['P'])); assert R['names'] == names and [f['n'] for f in RL['fingers']] == [f['n'] for f in KL['fingers']]
    fnames = [f['n'] for f in KL['fingers']]; allnames = names + fnames
    rf = fingers_world(RL['fingers'], names, R['Wm'])
    sim = {sd: {k_: side_f['%s_%s' % (side, k_)] for k_ in ('sc', 'mu_s', 'R', 'mu_d')} for side, sd in SIDES}
    to_bust = lambda Y, sd: (float(sim[sd]['sc']) * (Y - sim[sd]['mu_s']) @ sim[sd]['R'].T + sim[sd]['mu_d']) * SCALE + off
    isR = rid >= 0
    # the joints
    pur_b = np.abs(bvc - BUST_PURPLE).max(1) < 12; pur_k = KAEL_PURPLE(kvc)
    J = {}
    for side, sd in SIDES:
        Ak, Ek, Hk = (Wm[names.index(side + n)][:3, 3] for n in GROUPS)
        top_k, cuff_k = forearm(K['P'], pur_k, np.sign(K['P'][:, 0]) == sd, Ek, Hk)
        axk = (Hk - Ek) / np.linalg.norm(Hk - Ek); o_top = (top_k - Ek) @ axk; o_cuff = (Hk - cuff_k) @ axk; lk_ = (cuff_k - top_k) @ axk
        ring = np.zeros(len(X), bool); ring[Ib[(isR[Ib].sum(1) > 0) & (isR[Ib].sum(1) < 3)].ravel()] = True; ring &= ~isR & (np.sign(X[:, 0]) == sd)
        H0 = X[ring].mean(0); arm = ~isR & (sd * X[:, 0] > .17)
        E0 = X[arm & (np.abs(X[:, 1] - (H0[1] + .21)) < .01)].mean(0)
        top_b, cuff_b = forearm(X, pur_b, arm & (np.sign(X[:, 0]) == sd), E0, H0)
        axb = (cuff_b - top_b) / np.linalg.norm(cuff_b - top_b); k_ = np.linalg.norm(cuff_b - top_b) / lk_
        Eb = top_b - o_top * k_ * axb; Hb = cuff_b + o_cuff * k_ * axb
        Ab = Ak + np.array([-sd * SHOULDER[0], SHOULDER[1], SHOULDER[2]])
        J[sd] = dict(Ak=Ak, Ek=Ek, Hk=Hk, Ab=Ab, Eb=Eb, Hb=Hb)
        print('%s: bracer %.3f m (his %.3f); upper arm %.3f m (his %.3f), forearm %.3f m (his %.3f); elbow off his by %s, wrist %s' % (
            side, np.linalg.norm(cuff_b - top_b), lk_, np.linalg.norm(Eb - Ab), np.linalg.norm(Ek - Ak), np.linalg.norm(Hb - Eb), np.linalg.norm(Hk - Ek),
            np.round(Eb - Ek, 3), np.round(Hb - Hk, 3)))
    # the pose's turns
    for side, sd in SIDES:
        j = J[sd]; Ru = turn(j['Eb'] - j['Ab'], j['Ek'] - j['Ak']); Eb2 = j['Ab'] + Ru @ (j['Eb'] - j['Ab'])
        Rf = turn(Ru @ (j['Hb'] - j['Eb']), j['Hk'] - j['Ek']) @ Ru; Hb2 = Eb2 + Rf @ (j['Hb'] - j['Eb'])
        Rh = sim[sd]['R'].T   # (the hand turned as Ren's lies in the world in his rest pose: his hand bone and Kael's differ there by
        # 25 degrees on the left, 4 on the right, and the animations keep that difference; laid as Ren's lies in his hand bone,
        # Kael's left fist showed the camera its back where Ren's shows its knuckles)
        ang = lambda M: np.degrees(np.arccos(np.clip((np.trace(M) - 1) / 2, -1, 1)))
        print('%s: upper arm turned %.1f deg, forearm %.1f more, hand %.1f more' % (side, ang(Ru), ang(Rf @ Ru.T), ang(Rh @ Rf.T)))
        j.update(Ru=Ru, Rf=Rf, Rh=Rh, Eb2=Eb2, Hb2=Hb2)
    # provisional skin (the pose's four shares per vertex): his nearest point facing the same way, Ren's on Ren's hands
    gid = np.zeros(len(allnames), np.int64)
    for g, n in enumerate(GROUPS):
        for side, _ in SIDES: gid[allnames.index(side + n)] = g + 1
    for fnm in fnames: gid[allnames.index(fnm)] = 3
    near = nearest_facing(K['P'], K['N'], X, NX)
    G = np.zeros((len(X), 4)); np.add.at(G, (np.repeat(np.arange(len(X)), 4), gid[K['JN'][near]].ravel()), K['WG'][near].ravel())
    rr = rid[isR]; Gr = np.zeros((len(rr), 4)); np.add.at(Gr, (np.repeat(np.arange(len(rr)), 4), gid[rsi[rr]].ravel()), rsw[rr].ravel()); G[isR] = Gr
    G = smooth(G, wv, A, deg, SMOOTH); G /= G.sum(1, keepdims=True)
    # (the hands as long as the sheet draws them: from the cuff's bottom to the farthest fingertip HAND_RATIO of the bracer
    # (from its top band's top to the cuff's bottom; the sheet's: 0.206 m to 0.200 m). Meshy's arms gave the right hand 0.85
    # of that, the left 0.99: both scaled about the wrist to it, by their share of the hand)
    hsc = {}
    for side, sd in SIDES:
        j = J[sd]; s_ = (X[:, 0] >= 0) == (sd > 0); ax = (j['Hb'] - j['Eb']) / np.linalg.norm(j['Hb'] - j['Eb'])
        t = (X - j['Eb']) @ ax; r = np.linalg.norm((X - j['Eb']) - np.outer(t, ax), axis=1)
        band = pur_b & s_ & ~isR & (r < .07) & (t > -.05) & (t < np.linalg.norm(j['Hb'] - j['Eb']) + .03)
        top, bot = np.percentile(t[band], 1), np.percentile(t[band], 99.5); cb = j['Eb'] + ax * bot
        hv = X[isR & s_]; tip = hv[np.argmax(np.linalg.norm(hv - cb, axis=1))]
        want = HAND_RATIO * (bot - top); lo, hi = .5, 2.
        for _ in range(40):   # (the scale about the wrist joint giving the tip that far from the cuff's bottom)
            mid = (lo + hi) / 2; lo, hi = (mid, hi) if np.linalg.norm(j['Hb'] + (tip - j['Hb']) * mid - cb) < want else (lo, mid)
        hsc[sd] = float(os.environ.get('KAEL_HAND_SCALE', lo))
        print('%s hand: %.3f m from the cuff to the fingertip, the bracer %.3f m: scaled %.3f' % (side, np.linalg.norm(tip - cb), bot - top, hsc[sd]))
    for side, sd in SIDES:
        s_ = (X[:, 0] >= 0) == (sd > 0); k_ = 1 + (hsc[sd] - 1) * np.where(s_, G[:, 3], 0.)
        X = np.where(s_[:, None], J[sd]['Hb'] + (X - J[sd]['Hb']) * k_[:, None], X)
    # (the fingers FINGER_THICK times as thick about their bones, by their share on the finger bones (none on the hand's
    # back and palm): Ren's are long and slender, the sheet's fuller; in the fist they read as thin rods in a mitten)
    if FINGER_THICK != 1:
        fb = np.array([n.startswith(('LeftHand', 'RightHand')) and n[-1].isdigit() for n in allnames])
        for side, sd in SIDES:
            sel = np.nonzero(isR & ((X[:, 0] >= 0) == (sd > 0)))[0]; r_ = rid[sel]
            wf = (rsw[r_] * fb[rsi[r_]]).sum(1)
            segs = []
            for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
                jj = [rf[side + 'Hand' + f + str(k)] for k in (1, 2, 3)]; jj.append(jj[2] + (jj[2] - jj[1]) * .9)
                jb = [J[sd]['Hb'] + (to_bust(q[None], sd)[0] - J[sd]['Hb']) * hsc[sd] for q in jj]
                segs += [(jb[k], jb[k + 1]) for k in range(3)]
            Q = X[sel]; best = np.full(len(sel), 9.); foot = np.zeros_like(Q)
            for a, b in segs:
                ab = b - a; t = np.clip(((Q - a) @ ab) / (ab @ ab), 0, 1); c = a + np.outer(t, ab); d = np.linalg.norm(Q - c, axis=1); m = d < best; best[m] = d[m]; foot[m] = c[m]
            k_ = 1 + (FINGER_THICK - 1) * wf
            X[sel] = foot + (Q - foot) * k_[:, None]
        print('fingers: %.2f times as thick about their bones' % FINGER_THICK)
    # the pose
    X2 = X * G[:, :1]; N2 = NX * G[:, :1]
    for side, sd in SIDES:
        j = J[sd]; s_ = (X[:, 0] >= 0) == (sd > 0)   # (each vertex on one side)
        for g, (Rm, piv, piv2) in enumerate(((j['Ru'], j['Ab'], j['Ab']), (j['Rf'], j['Eb'], j['Eb2']), (j['Rh'], j['Hb'], j['Hb2'])), 1):
            w = np.where(s_, G[:, g], 0.)[:, None]; X2 += w * ((X - piv) @ Rm.T + piv2); N2 += w * (NX @ Rm.T)
    N2 /= np.maximum(np.linalg.norm(N2, axis=1, keepdims=True), 1e-9)
    if HAND_NSMOOTH:   # (the hands' light's normals smoothed: the game's light on Ren's low hands, scaled up, fell in blotches on the glove)
        hn = isR.copy(); hn[Ib[isR[Ib].any(1)].ravel()] = True
        N2 = smooth(N2, wv, A, deg, HAND_NSMOOTH, hn); N2 /= np.maximum(np.linalg.norm(N2, axis=1, keepdims=True), 1e-9)
    # the skin: his nearest point facing the same way, the arms stretched to his lengths first; Ren's on Ren's hands
    V = X2 * G[:, :1]
    for side, sd in SIDES:
        j = J[sd]; s_ = (X[:, 0] >= 0) == (sd > 0)   # (each vertex on one side)
        du = (j['Ek'] - j['Ak']) / np.linalg.norm(j['Ek'] - j['Ak']); dfa = (j['Hk'] - j['Ek']) / np.linalg.norm(j['Hk'] - j['Ek'])
        ku = np.linalg.norm(j['Ek'] - j['Ak']) / np.linalg.norm(j['Eb2'] - j['Ab']); kfa = np.linalg.norm(j['Hk'] - j['Ek']) / np.linalg.norm(j['Hb2'] - j['Eb2'])
        Su = np.eye(3) + (ku - 1) * np.outer(du, du); Sf = np.eye(3) + (kfa - 1) * np.outer(dfa, dfa)
        for g, (St, piv_b, piv_k) in enumerate(((Su, j['Ab'], j['Ak']), (Sf, j['Eb2'], j['Ek']), (np.eye(3), j['Hb2'], j['Hk'])), 1):
            V += np.where(s_, G[:, g], 0.)[:, None] * ((X2 - piv_b) @ St.T + piv_k)
    near = nearest_facing(K['P'], K['N'], V, N2)
    Wf = np.zeros((len(X), len(allnames))); np.add.at(Wf, (np.repeat(np.arange(len(X)), 4), K['JN'][near].ravel()), K['WG'][near].ravel())
    Wr = np.zeros((len(rr), len(allnames))); np.add.at(Wr, (np.repeat(np.arange(len(rr)), 4), rsi[rr].ravel()), rsw[rr].ravel()); Wf[isR] = Wr
    Wf = smooth(Wf, wv, A, deg, 2, ~isR)
    if HAND_SMOOTH: Wf = smooth(Wf, wv, A, deg, HAND_SMOOTH, isR)
    seam_c = np.zeros(len(X), bool); seam_c[Ib[(isR[Ib].sum(1) > 0) & (isR[Ib].sum(1) < 3)].ravel()] = True
    dseam = cKDTree(X2[seam_c]).query(X2)[0]
    Wf = smooth(Wf, wv, A, deg, SEAM_SMOOTH, dseam < SEAM)
    top = np.argsort(-Wf, 1)[:, :4]; tw = np.take_along_axis(Wf, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-12)
    print('skin: %s' % {allnames[i]: int(c_) for i, c_ in enumerate(np.bincount(top[:, 0], minlength=len(allnames))) if c_})
    # the bones: his arms' lengths as its, his shoulders' joints at its; the finger bones Ren's, laid on its hands
    bones = {}
    for side, sd in SIDES:
        j = J[sd]; sh = Wm[names.index(side + 'Shoulder')]
        bones[side + 'Arm'] = (sh[:3, :3].T @ (j['Ab'] - sh[:3, 3])).tolist()
        for n, a, b_, a2, b2 in (('ForeArm', 'Ak', 'Ek', 'Ab', 'Eb2'), ('Hand', 'Ek', 'Hk', 'Eb2', 'Hb2')):
            t0 = np.array(K['J']['bones'][names.index(side + n)]['t'])
            bones[side + n] = (t0 * np.linalg.norm(j[b2] - j[a2]) / np.linalg.norm(j[b_] - j[a])).tolist()
    fingers = []; frames = {}   # (frames: per hand the turn from Ren's hand frame into Kael's: the fists' own frame, tests/viewer_check.py)
    for f in RL['fingers']:
        side = 'Left' if f['n'].startswith('Left') else 'Right'; sd = dict(SIDES)[side]; j = J[sd]
        Rk = Wm[names.index(side + 'Hand')][:3, :3]; Rr = R['Wm'][names.index(side + 'Hand')][:3, :3]
        place = lambda Y: (to_bust(Y[None], sd)[0] - j['Hb']) * hsc[sd] @ j['Rh'].T + j['Hb2']
        p_w = place(rf[f['n']]); par = j['Hb2'] if f['p'] == side + 'Hand' else place(rf[f['p']])
        M = j['Rh'] @ sim[sd]['R']; C = Rk.T @ M @ Rr; qc = mq(C); qr = np.array(f['fist'])
        frames[side] = [round(float(v), 5) for v in qc]
        def qmul(a, b):
            x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
            return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])
        fist = qmul(qmul(qc, qr), qc * [-1, -1, -1, 1])
        fingers.append(dict(n=f['n'], p=f['p'], t=[round(float(v), 5) for v in Rk.T @ (p_w - par)], fist=[round(float(v), 5) for v in fist / np.linalg.norm(fist)]))
    # (the thumbs THUMB_SCALE as long and as thick from where they leave the palm (their web, tools/kael_bust.py) to their tips, the bones
    # with them: Ren's are long, as long as the index finger; Denis, 12/11, circling them in the fist: "fallo più piccolo")
    if THUMB_SCALE != (1., 1.):
        for side, sd in SIDES:
            j = J[sd]; Rk = Wm[names.index(side + 'Hand')][:3, :3]; th = [side + 'HandThumb%d' % k for k in (1, 2, 3)]
            fd = {f['n']: f for f in fingers}; T1 = j['Hb2'] + Rk @ np.array(fd[th[0]]['t']); T2 = T1 + Rk @ np.array(fd[th[1]]['t']); T3 = T2 + Rk @ np.array(fd[th[2]]['t'])
            ax = (T2 - T1) / np.linalg.norm(T2 - T1); web = X2[np.argmin(np.linalg.norm(Pb - side_f[side + '_web'], axis=1))]
            c = T1 + ((web - T1) @ ax) * ax   # (the scale's centre: the web on the thumb's axis)
            w = (tw * np.isin(top, [allnames.index(n) for n in th])).sum(1) * ((X2[:, 0] >= 0) == (sd > 0))
            sm = lambda u: (lambda v: v * v * (3 - 2 * v))(np.clip(u, 0, 1)); f_ = lambda P: 1 + (THUMB_SCALE[0] - 1) * sm(((P - c) @ ax) / .01)   # (its length)
            g_ = lambda P: 1 + (THUMB_SCALE[1] - 1) * sm(((P - c) @ ax) / .01)   # (its thickness)
            D = X2 - c; al = D @ ax; kl = 1 + (f_(X2) - 1) * w; kt = 1 + (g_(X2) - 1) * w
            X2 = c + np.outer(al * kl, ax) + (D - np.outer(al, ax)) * kt[:, None]
            T2n = c + (T2 - c) * f_(T2[None])[0]; T3n = c + (T3 - c) * f_(T3[None])[0]
            fd[th[1]]['t'] = [round(float(v), 5) for v in Rk.T @ (T2n - T1)]; fd[th[2]]['t'] = [round(float(v), 5) for v in Rk.T @ (T3n - T2n)]
            print('%s thumb past its web (%.1f mm from its first joint): %.2f as long, %.2f as thick' % (side, 1000 * (web - T1) @ ax, *THUMB_SCALE))
    # (the thumbs folded over the fingers in the fist: thumb_fist)
    like = None
    for side, sd in SIDES[::-1]:   # (the right first: the left's laid as the right's)
        tq, like = thumb_fist(side, fingers, X2, N2, top, tw, allnames, J[sd]['Hb2'], Wm[names.index(side + 'Hand')][:3, :3], like)
        for f in fingers:
            if f['n'] in tq: f['fist'] = [round(float(v), 5) for v in tq[f['n']] / np.linalg.norm(tq[f['n']])]
    # his own triangles under it: those mostly on the upper body's bones, all of his torso from under its sash up (his sash
    # and its knot stood out of it), and under its sash those inside its skirt (not under its hem)
    up = np.isin(K['JN'], [names.index(n) for n in UPPER]); wu = (K['WG'] * up).sum(1)
    hid = wu[K['I']].mean(1) > HIDE_W
    ck = K['P'][K['I']].mean(1); sash_y = SASH_K + (SASH[0] - SASH_B) * SCALE
    band = (ck[:, 1] > sash_y - .01) & (np.hypot(ck[:, 0] - CENTRE[0], ck[:, 2] - CENTRE[1]) < .3)
    # (its skirt over his trousers: where they stand out of it, pushed out to SKIRT_OUT m over them along its normal, the push
    # smoothed over the skirt; their parts under it then hidden)
    skirt = (X2[:, 1] < sash_y) & (G[:, 0] > .5) & ~isR & (np.abs(X2[:, 0]) < .3)
    kv = np.zeros(len(K['P']), bool); kv[K['I'][~(hid | band)].ravel()] = True; kp = np.nonzero(kv)[0]
    nh = N2.copy(); nh[:, 1] = 0; nh /= np.maximum(np.linalg.norm(nh, axis=1, keepdims=True), 1e-9)
    push = np.zeros(len(X2)); tree = cKDTree(K['P'][kp])
    for v in np.nonzero(skirt)[0]:
        cand = np.array(tree.query_ball_point(X2[v] + nh[v] * SKIRT_WIN[1] / 2, SKIRT_WIN[1] / 2 + SKIRT_WIN[0]), int)
        if not len(cand): continue
        Y = K['P'][kp[cand]] - X2[v]; t = Y @ nh[v]; lat = np.linalg.norm(Y - np.outer(t, nh[v]), axis=1)
        ok_ = (lat < SKIRT_WIN[0]) & (t > -.01) & (t < SKIRT_WIN[1])
        if ok_.any(): push[v] = max(0., t[ok_].max() + SKIRT_OUT)
    push = smooth(push[:, None], wv, A, deg, SKIRT_SMOOTH, skirt)[:, 0] * skirt
    X2 = X2 + nh * push[:, None]
    print('skirt: pushed out over his trousers at %d vertices (%.1f mm at most, %.1f mm on average where pushed)' % (
        int((push > 1e-4).sum()), 1000 * push.max(), 1000 * push[push > 1e-4].mean() if (push > 1e-4).any() else 0))
    sk = np.nonzero(skirt)[0]; d_, nn_ = cKDTree(X2[sk]).query(ck); q = sk[nn_]
    angle = lambda Y: np.degrees(np.arctan2(Y[:, 0] - CENTRE[0], Y[:, 2] - CENTRE[1]))
    ab = np.round((angle(X2[sk]) + 180) / 3).astype(int) % 120; hem = np.full(120, 9.); np.minimum.at(hem, ab, X2[sk, 1])
    for _ in range(2): hem = np.minimum(hem, np.minimum(np.roll(hem, 1), np.roll(hem, -1)))   # (its lowest within 6 degrees)
    hem_c = hem[np.round((angle(ck) + 180) / 3).astype(int) % 120]
    inside = (ck[:, 1] <= sash_y) & (((ck - X2[q]) * nh[q]).sum(1) < .003) & (d_ < .06) & (ck[:, 1] > hem_c + HEM_KEEP)
    hide = np.nonzero(hid | band | inside)[0].astype(np.uint32)
    print('his triangles hidden: %d (%d on the upper body, %d more of his torso, %d under the skirt)' % (
        len(hide), int(hid.sum()), int((band & ~hid).sum()), int((inside & ~hid & ~band).sum())))
    # the glove's edge on the hands drawn by the game (src/e_model.js, aGlove): per vertex of Ren's hands and of the seam its
    # signed distance (m) to the edge the texture paints (the glove under 0, the edge between its texels and the skin's) and
    # 1 (a hand's); the texture skin up to GLOVE_PAD into the glove (the game paints the glove and the edge's ink). In the fist the painted edge,
    # bent over the knuckles, broke into teeth; drawn from the distances it is straight in every triangle
    from paint_views import texel_table
    hv = isR.copy(); hv[Ib[isR[Ib].any(1)].ravel()] = True
    ys, xs, ks, bary, tpos, _ = texel_table(Pb, Nb, UVb, Ib, BS)
    th = hv[Ib[ks]].all(1); tcol = bt[ys, xs]; near_c = lambda c: np.abs(tcol - c).max(1) < 10
    gl = th & (near_c(GLOVE_C) | near_c(BLACK_C)); ink = th & near_c(INK_C); sk = th & ~gl & ~ink
    ti = np.nonzero(ink)[0]
    if len(ti):   # (the edge's ink: the side it is nearer)
        dg_, _ = cKDTree(tpos[gl]).query(tpos[ti]); ds_, _ = cKDTree(tpos[sk]).query(tpos[ti]); gl[ti[dg_ < ds_]] = True; sk[ti[dg_ >= ds_]] = True
    tg, ts_ = cKDTree(tpos[gl]), cKDTree(tpos[sk]); vh = np.nonzero(hv)[0]
    in_g = tg.query(Pb[vh])[0] < ts_.query(Pb[vh])[0]
    d = np.where(in_g, -ts_.query(Pb[vh])[0], tg.query(Pb[vh])[0]) * SCALE
    gfield = np.zeros((len(X), 2), np.float32); gfield[:, 0] = 1.; gfield[vh, 0] = d; gfield[vh, 1] = 1.
    near_edge = gl & (ts_.query(tpos)[0] < GLOVE_PAD) | (th & near_c(INK_C))
    bt2 = bt.copy(); bt2[ys[near_edge], xs[near_edge]] = SKIN_C; BT = Image.fromarray(bt2.astype(np.uint8))   # (only by the edge: skin painted under all of the glove bled into the seam's triangles, skin hairlines at the cuff)
    print('glove: its edge drawn by the game on %d vertices (%d in the glove), the texture by the edge skin (%d texels)' % (len(vh), int(in_g.sum()), int(near_edge.sum())))
    # the part
    used = np.unique(Ib); mp = -np.ones(len(X), np.int64); mp[used] = np.arange(len(used)); It = mp[Ib]
    hv_all = isR.copy(); hv_all[Ib[isR[Ib].any(1)].ravel()] = True; hv_all = hv_all.astype(float)
    if os.environ.get('KAEL_ATTACH_DUMP'): np.savez(os.environ['KAEL_ATTACH_DUMP'], rid=rid[used], side=(X2[used, 0] >= 0), dseam=dseam[used])   # (each part vertex's in Ren's package: tests of the fists' shape)
    pad = lambda bts: bts + b'\0' * (-len(bts) % 4)
    blob = b''; jo = {'v': 1, 'verts': int(len(used)), 'tris': int(len(It)), 'scale': SCALE}
    def put(key, arr):
        nonlocal blob
        blob = pad(blob); jo[key] = [len(blob), int(arr.size)]; blob += np.ascontiguousarray(arr).tobytes()
    put('pos', X2[used].astype(np.float32)); put('nor', N2[used].astype(np.float32)); put('uv', UVb[used].astype(np.float32))
    put('jnt', top[used].astype(np.uint8)); put('wgt', tw[used].astype(np.float32))
    put('idx', It.astype(np.uint16 if len(used) < 65536 else np.uint32)); put('hide', hide)
    put('flat', np.where(isR, HAND_FLAT, 1.)[used].astype(np.float32))   # (its light: flat, the hands the game's)
    put('glove', gfield[used])   # (the hands' glove: the signed distance to its edge, m; 1 a hand's vertex)
    # (the outline on the hands drawn inside them too, as a drawing's lines: where a finger lies over another, the thumb over the
    # fingers, the fist over the palm. The body's outline is pushed 2 cm back from the camera: only the hand's silhouette was
    # drawn and the fist read as one block. On the hands, by their share, HAND_LINE[0] of that push and HAND_LINE[1] of its width)
    hw = np.clip(G[:, 3], 0, 1) * hv_all
    # (and on the arms ARM_LINE: where the deltoid lies over the biceps, the triceps over the elbow, the forearm over the upper arm,
    # their lines drawn as the sheet traces the muscles; Denis, 12/11: "ricalca anche i muscoli delle braccia")
    aw = np.clip(G[:, 1] + G[:, 2], 0, 1) * (1 - hw)
    push = 1 + hw * (HAND_LINE[0] - 1) + aw * (ARM_LINE[0] - 1); width = 1 + hw * (HAND_LINE[1] - 1) + aw * (ARM_LINE[1] - 1)
    put('lb', ((push - 1) * BODY_LINE_BACK)[used].astype(np.float32)); put('line', width[used].astype(np.float32))
    jo['bones'] = {k_: [round(float(v), 5) for v in t_] for k_, t_ in bones.items()}; jo['fingers'] = fingers; jo['fistFrame'] = frames
    open(os.path.join(KAEL_PKG, 'kael_bust.bin'), 'wb').write(pad(blob)); json.dump(jo, open(os.path.join(KAEL_PKG, 'kael_bust.json'), 'w'), separators=(',', ':'))
    BT.save(os.path.join(KAEL_PKG, 'kael_bust.png'), optimize=True)
    print('written: kael_bust (%d vertices, %d triangles)' % (len(used), len(It)))


if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
