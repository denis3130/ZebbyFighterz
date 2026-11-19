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
  Ren's, scaled), the fists' turns Ren's (src/e_model.js: the part's fingers in place of the look's); thumb_fist and
  THUMB_SCALE (the thumbs folded and made smaller) tried and off: Ren's fists as they are, Kael's glove drawn on them.
- The glove's edge on the hands drawn by the game (src/e_model.js aGlove: per vertex its signed distance to the painted
  edge): in the fist the painted edge, bent over the knuckles, broke into teeth.
- Light: flat (its paint has the sheet's shadows), but on the hands the game's (HAND_FLAT; Denis, 11/11, on the fists in
  flat light, dark blocks: "sono da migliorare nettamente guarda le sue immagini di riferimento").
- His own triangles hidden: those mostly on the upper body's bones (HIDE_W), his torso from under its sash up (his sash
  and its knot were wider than its), and his trousers under its skirt. The skirt (the sheet's tunic, over the trousers):
  where his baggy trousers stood out of it (1-2 cm at the sides), pushed out SKIRT_OUT over them, smoothed. His old sash's
  tails stay (they hang from under its knot) until the ribbons.

usage: python3 tools/kael_bust_attach.py BUST.glb [FIST.glb OPEN.glb [OUTFIT.glb]]   (with Meshy's forearms, fist and open: arm_parts; with Meshy's clothes: outfit_part; writes wip_assets/kael/kael_bust.json, .bin, .png; Kael's look needs
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
from kael_gear import crop_paint, write_part, clip_iso, shell, glove_edge, near_index, cuff_band, ring_radius, flare, ring_frame, skirt as make_skirt, ring as make_ring, loop_subdivide, vertex_normals

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
KAEL_PKG = os.path.join(ROOT, 'wip_assets', 'kael')
REN = os.path.join(ROOT, 'assets', 'ren', 'ren.json'), os.path.join(ROOT, 'viewer_assets', 'ren', 'ren_look.json')
REN_PAINT = os.path.join(ROOT, 'viewer_assets', 'ren', 'ren_painted.jpg')   # Ren's paint as the game draws him (his hands' part is cut out of it)
SCALE, SASH_B, SASH_K, CENTRE = .42, -.21, 1.08, (-.005, 0.)
SHOULDER = (.015, -.010, .022)   # m: the bust's shoulder joints from his: inward, up, forward
SIDES = (('Left', 1), ('Right', -1))   # (his left: +x)
GROUPS = ('Arm', 'ForeArm', 'Hand')    # (with the torso: the pose's four)
FACE = .3                              # (nearest points: their normals within this of each other's)
SMOOTH, SEAM, SEAM_SMOOTH = 4, .03, 6
HIDE_W = .5
GLOVE_PAD = .007                         # bust units (3 mm): the texture's glove painted skin so far from its edge
GLOVE_C, BLACK_C, INK_C, SKIN_C = (65, 49, 74), (26, 21, 27), (9, 6, 9), (250, 191, 151)   # the bust's palette (tools/kael_bust.py PAL)
GLOVE_EDGE = None if os.environ.get('KAEL_GLOVE_EDGE') == 'paint' else dict(back=.012, palm=.004, thumb=-.008, thumb_r=.003, soft=.006)   # m: the glove's edge (tools/kael_gear.py glove_edge): so far before the knuckles on the back and on the palm, the thumb free so far before its second joint, so much wider than it, the blend; None: the texture's painted edge (in the fist, teeth)
ARM_CUT, ARM_CLEAR, ARM_WRIST, ARM_WIDE = .010, .002, 1.08, 1.2   # Meshy's forearms (arm_parts): the bust kept so far (m) into their elbow band, the band so far (m) over it; as thick as the bust's forearm all along, the hand ARM_WRIST less wide than its wrist band asks (its length Denis's), at most ARM_WIDE times as wide as long
OUTFIT_TAT, OUTFIT_LEG, OUTFIT_SMOOTH, OUTFIT_TEX, OUTFIT_ARM_Y, OUTFIT_BITS, OUTFIT_FORE, OUTFIT_ELBOW = .12, 1., 3, 2048, 1.0, .01, .5, .07   # Meshy's clothes (outfit_part): their elbow band looked for so far (m) past the shoulder (its tattoo before); the legs turned so much of the way onto his; rounds of smoothing of their skin; their texture's size on the page; the arms looked for over this height (m: the trousers below); pieces left loose by the cuts under this share of its triangles cut; its vertices over this share on the forearms and hands cut, further than [7] m from the bands' tops
GLOVE_T, GLOVE_WALL = .002, .0015   # m: the gloves' shell over the hands' skin, and its edge's strip down toward the skin (tools/kael_gear.py shell)
HAND_STYLE = os.environ.get('KAEL_HAND_STYLE', 'foglio')   # Kael's hands: 'ren' (Ren's as on him: his paint, light, outline) or 'foglio' (as the sheet draws them: smooth, two flat tones, black lines between the fingers; 19/11, Denis: "mani e polsi ancora brutti")
FOGLIO = dict(subdiv=1, skin=(250, 191, 151), line_push=.1, line_w=.7, ink_w=.002)   # 'foglio': Loop rounds; the sheet's skin; the outline pushed back so much of the body's (lines between the fingers) and so wide; the glove's edge ink half width, m
RING = dict(clear=.003, bulge=.002, lip=.004, under=.0025, n_th=48, height=.185)   # m: the wrists' rings over what they cover, their bulge, their lips' depth; what is under them kept so far inside; their height: of the bracer, as the sheet's (its wrist band 23 px, 124 px between the bands' middles)
ARM_LINE = (float(os.environ.get('KAEL_ARM_PUSH', .3)), .7)   # the arms' outline: its push back (of the body's) and its width
HAND_LINE, BODY_LINE_BACK = tuple(float(v) for v in os.environ.get('KAEL_HAND_LINE', '1,1').split(',')), .02   # the hands' outline: its push back (of the body's, BODY_LINE_BACK m: CFG.looks.kael.line.back) and its width (Ren's hands: the body's, the silhouette only; tried (.10, .65): lines drawn inside them)
FINGER_THICK = 1.                        # the fingers' thickness about their bones (tried 1.25: the fingers merged into a lump, the fist a skin blob, the open hand a mitten)
HAND_MUL = float(os.environ.get('KAEL_HAND_MUL', .9))   # the hands this much bigger than HAND_RATIO makes them (Denis, 12/11, choosing among 90, 100, 115%: "meglio 90%")
HAND_RATIO = 1.03                        # the hands' length (cuff to fingertip) over the bracer's, as the sheet draws them (Denis, 12/11: "dimensioni delle mani falle come si deve")
HAND_REN_NORMALS = 1                     # Ren's hands lit by Ren's own smoothed normals (his look's), as on him
HAND_NSMOOTH = int(os.environ.get('KAEL_HAND_NSMOOTH', 6))                         # rounds of smoothing of the hands' normals (the light's bands clean)
HAND_SMOOTH = 0                          # rounds of smoothing of the weights on Ren's hands (tried 4: the fist opened, a hole by the thumb)
THUMB_BASE = dict(zip(('Right', 'Left'), (float(v) for v in os.environ.get('KAEL_THUMB_BASE', '25,40').split(','))))   # degrees, per hand: the thumb's first bone turned at most so far in the fist (Ren's 55-60 turned it all from its base: the skin between it and the palm stretched into a blade toward the wrist), its middle joint bending instead
CUFF = (1.15, -.10, .02)   # the cuffs' rims: no vertex further from the forearm's axis than [0] times its 5 mm slice's median, from [1] to [2] m along the forearm from the wrist
THUMB_IP = float(os.environ.get('KAEL_THUMB_IP', 40.))   # degrees: the thumb's last joint bent at least so far in the fist (left free, the right's came out straight: a skin blade across the fingers)
THUMB_FOLD = int(os.environ.get('KAEL_THUMB_FOLD', 0))   # the thumbs folded by thumb_fist (1) or Ren's fists as they are (0; Denis, 12/11: "taglia i pugni di ren e attaccali a kael"; then, circling the fists in guard, the wedge his thumb's base made in the glove: folded again; 17/11, the hands remade as Ren's with a real glove over them: as his again)
THUMB_SCALE = tuple(float(v) for v in os.environ.get('KAEL_THUMB_SCALE', '1,1').split(','))   # the thumb past its web: so long, so thick (Ren's as long as the index finger; Denis, 12/11: "fallo più piccolo"; all of it at .7 a pencil beside the fingers)
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
                + THUMB_FIST[4] * np.sum((x - x0) ** 2) * 1e-4 + .05 * max(0., np.linalg.norm(x[:3]) - np.radians(THUMB_BASE[side])) ** 2 + .05 * max(0., np.radians(THUMB_IP) - x[4]) ** 2)
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


def main(bust, arms=None, outfit=None):
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
        J[sd] = dict(Ak=Ak, Ek=Ek, Hk=Hk, Ab=Ab, Eb=Eb, Hb=Hb, top_b=top_b, cuff_b=cuff_b, bracer=float(np.linalg.norm(cuff_b - top_b)))
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
        j['top_full'], j['cuff_full'] = j['Eb'] + ax * top, cb   # (the bracer's ends: its top band's top, its cuff's bottom; arm_parts)
        hv = X[isR & s_]; tip = hv[np.argmax(np.linalg.norm(hv - cb, axis=1))]
        want = HAND_RATIO * (bot - top); lo, hi = .5, 2.
        for _ in range(40):   # (the scale about the wrist joint giving the tip that far from the cuff's bottom)
            mid = (lo + hi) / 2; lo, hi = (mid, hi) if np.linalg.norm(j['Hb'] + (tip - j['Hb']) * mid - cb) < want else (lo, mid)
        hsc[sd] = float(os.environ.get('KAEL_HAND_SCALE', lo)) * HAND_MUL
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
    if HAND_REN_NORMALS:   # (Ren's hands lit by his look's smoothed normals, as on him: turned as his hands were laid on the bust)
        Lb = open(REN[1][:-4] + 'bin', 'rb').read(); Ln = np.frombuffer(Lb, np.float32, RL['nor'][1], RL['nor'][0]).reshape(-1, 3).astype(float)
        for side, sd in SIDES:
            m_ = isR & ((X[:, 0] >= 0) == (sd > 0)); NX[m_] = Ln[rid[m_]] @ np.asarray(sim[sd]['R']).T
        NX /= np.maximum(np.linalg.norm(NX, axis=1, keepdims=True), 1e-9)
    # the pose
    X2 = X * G[:, :1]; N2 = NX * G[:, :1]
    for side, sd in SIDES:
        j = J[sd]; s_ = (X[:, 0] >= 0) == (sd > 0)   # (each vertex on one side)
        for g, (Rm, piv, piv2) in enumerate(((j['Ru'], j['Ab'], j['Ab']), (j['Rf'], j['Eb'], j['Eb2']), (j['Rh'], j['Hb'], j['Hb2'])), 1):
            w = np.where(s_, G[:, g], 0.)[:, None]; X2 += w * ((X - piv) @ Rm.T + piv2); N2 += w * (NX @ Rm.T)
    N2 /= np.maximum(np.linalg.norm(N2, axis=1, keepdims=True), 1e-9)
    # (the cuffs' rims round: by the wrist Meshy left flaps standing out of the band (the left's to 8.5 cm from the forearm's
    # axis, the band's 3.5; Denis circled it): per 5 mm slice along the forearm, the vertices further out than CUFF[0] times
    # the slice's median brought in to it)
    for side, sd in SIDES:
        j = J[sd]; ax = (j['Hb2'] - j['Eb2']) / np.linalg.norm(j['Hb2'] - j['Eb2']); D = X2 - j['Hb2']; t = D @ ax; rad = D - np.outer(t, ax); r = np.linalg.norm(rad, axis=1)
        s_ = ((X2[:, 0] >= 0) == (sd > 0)) & ~isR & (t > CUFF[1]) & (t < CUFF[2]) & (r < .12); moved = 0
        for a in np.arange(CUFF[1], CUFF[2], .005):
            m = s_ & (t >= a) & (t < a + .005)
            if m.sum() < 5: continue
            rm = np.median(r[m]); far = m & (r > CUFF[0] * rm)
            X2[far] = j['Hb2'] + np.outer(t[far], ax) + rad[far] * (CUFF[0] * rm / r[far])[:, None]; moved += far.sum()
        print('%s cuff: %d vertices brought in to %.2f of their slice\'s median' % (side, moved, CUFF[0]))
    N2_ren = N2.copy()   # (the hands' part: Ren's normals, only turned with the hand, as on him)
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
    for side, sd in (SIDES[::-1] if THUMB_FOLD else ()):   # (the right first: the left's laid as the right's)
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
    if GLOVE_EDGE:   # (the edge as the sheet draws it, a line before the knuckles and a ring round the thumb: tools/kael_gear.py glove_edge)
        from scipy.spatial.transform import Rotation
        d_paint = d.copy()
        for side, sd in SIDES:
            Rk = Wm[names.index(side + 'Hand')][:3, :3]; fd = {f['n']: f for f in fingers}
            pos = lambda n: J[sd]['Hb2'] + Rk @ np.array(fd[n]['t']) if fd[n]['p'] == side + 'Hand' else pos(fd[n]['p']) + Rk @ np.array(fd[n]['t'])
            Kn = np.array([pos(side + 'Hand%s1' % f) for f in ('Index', 'Middle', 'Ring', 'Pinky')])
            v = np.array(fd[side + 'HandMiddle2']['t']); palm = Rk @ (Rotation.from_quat(fd[side + 'HandMiddle1']['fist']).apply(v) - v)
            T2, T3 = pos(side + 'HandThumb2'), pos(side + 'HandThumb3'); ax = (T3 - T2) / np.linalg.norm(T3 - T2)
            ith = [allnames.index(side + 'HandThumb%d' % k) for k in (2, 3)]; wth = (tw * np.isin(top, ith)).sum(1)
            th_v = (wth > .5) & ((X2[:, 0] >= 0) == (sd > 0)); Q = X2[th_v] - T2
            r_th = float(np.percentile(np.linalg.norm(Q - np.outer(Q @ ax, ax), axis=1), 95)) + GLOVE_EDGE['thumb_r']
            m = (X2[vh, 0] >= 0) == (sd > 0)
            d[m] = glove_edge(X2[vh[m]], J[sd]['Hb2'], Kn, palm, T2, T3, r_th, GLOVE_EDGE['back'], GLOVE_EDGE['palm'], GLOVE_EDGE['thumb'], GLOVE_EDGE['soft'])
            e = m & (np.abs(d_paint) < .0015)
            print('%s glove edge: a line %.1f mm before the knuckles (back), %.1f (palm), the thumb free %.1f mm before its joint within %.1f mm; '
                  'the painted edge on it at %.1f mm (+-%.1f), %d of %d vertices on the other side' % (
                      side, 1000 * GLOVE_EDGE['back'], 1000 * GLOVE_EDGE['palm'], 1000 * GLOVE_EDGE['thumb'], 1000 * r_th,
                      1000 * d[e].mean(), 1000 * d[e].std(), int((m & ((d < 0) != (d_paint < 0))).sum()), int(m.sum())))
        # (skin only on the fingers and the thumb: islands of it inside the glove, where the thumb's free round met the palm
        # by its base, were holes in the glove, its ink round them shards in the fist; welded, Meshy's seams split the mesh)
        loc = -np.ones(len(X), np.int64); loc[vh] = np.arange(len(vh)); sk_ = d > 0
        T_ = loc[Ib[(loc[Ib] >= 0).all(1)]]; ew = wv[vh]
        E_ = np.r_[T_[:, [0, 1]], T_[:, [1, 2]], T_[:, [2, 0]]]; E_ = E_[sk_[E_].all(1)]
        nw = wv.max() + 1; _, lab = connected_components(coo_matrix((np.ones(len(E_)), (ew[E_[:, 0]], ew[E_[:, 1]])), shape=(nw, nw)), directed=False)
        lv = lab[ew]
        for side, sd in SIDES:
            m = sk_ & ((X2[vh, 0] >= 0) == (sd > 0)); ids, cnt = np.unique(lv[m], return_counts=True)
            isl = ids[cnt < .1 * cnt.max()]; fl = m & np.isin(lv, isl); d[fl] = -d[fl]
            print('%s glove: the skin in %d pieces (%s vertices), %d islands closed (%d vertices)' % (side, len(ids), sorted(cnt.tolist(), reverse=True)[:6], len(isl), int(fl.sum())))
    gfield = np.zeros((len(X), 2), np.float32); gfield[:, 0] = 1.; gfield[vh, 0] = d; gfield[vh, 1] = 1.
    near_edge = gl & (ts_.query(tpos)[0] < GLOVE_PAD) | (th & near_c(INK_C))
    bt2 = bt.copy(); bt2[ys[near_edge], xs[near_edge]] = SKIN_C; BT = Image.fromarray(bt2.astype(np.uint8))   # (only by the edge: skin painted under all of the glove bled into the seam's triangles, skin hairlines at the cuff)
    print('glove: its edge drawn by the game on %d vertices (%d in the glove), the texture by the edge skin (%d texels)' % (len(vh), int(in_g.sum()), int(near_edge.sum())))
    # the parts: the bust without Ren's hands (their triangles, all three corners his) and the hands on their own (17/11, Denis:
    # "a me non piacciono soprattutto le mani": Ren's as the game draws him, his paint cut out of his texture, not resampled
    # into the bust's; his normals as on him; his light and outline per vertex). The seam's triangles, part hand part arm,
    # stay in the bust, under the wrist's ring.
    whole = isR[Ib].all(1); Ih = Ib[whole]
    hv_all = isR.copy(); hv_all[Ib[isR[Ib].any(1)].ravel()] = True; hv_all = hv_all.astype(float)
    Ib = Ib[~whole]
    used = np.unique(Ib); mp = -np.ones(len(X), np.int64); mp[used] = np.arange(len(used)); It = mp[Ib]
    usedh = np.unique(Ih); mph = -np.ones(len(X), np.int64); mph[usedh] = np.arange(len(usedh)); rh = rid[usedh]
    # the gloves (17/11, Denis's choice: "Mano di Ren + guanto vero"): a real shell GLOVE_T over the hands' skin where the glove
    # is (the signed distance to its edge, gfield: under 0), cut along its edge; along the edge a strip down toward the skin, in
    # ink (its thickness); skinned as the skin under it; the outline as the hand's there
    Lb = open(REN[1][:-4] + 'bin', 'rb').read(); Lf = lambda k_: np.frombuffer(Lb, np.float32, RL[k_][1], RL[k_][0])
    Wd = np.zeros((len(usedh), len(allnames))); np.add.at(Wd, (np.repeat(np.arange(len(usedh)), 4), top[usedh].ravel()), tw[usedh].ravel())
    # (the hands' surface: Ren's as it is, or for 'foglio' rounded by Loop subdivision, its normals the smooth surface's)
    Hp, HI, HN = X2[usedh].copy(), mph[Ih], N2_ren[usedh]; HA = {'W': Wd, 'D': gfield[usedh, 0], 'line': Lf('line')[rh], 'flat': Lf('flat')[rh], 'dseam': dseam[usedh]}
    if HAND_STYLE == 'foglio':
        for _ in range(FOGLIO['subdiv']): Hp, HI, HA = loop_subdivide(Hp, HI, HA)
        HN = vertex_normals(Hp, HI)
    if os.environ.get('KAEL_ATTACH_DUMP'): np.savez(os.environ['KAEL_ATTACH_DUMP'], rid=rid[used], side=(X2[used, 0] >= 0), dseam=dseam[used], style=HAND_STYLE,
                                                    hands_rid=rh if HAND_STYLE == 'ren' else -np.ones(len(Hp), np.int64), hands_side=(Hp[:, 0] >= 0), hands_dseam=HA['dseam'], hands_D=HA['D'])   # (each part vertex's in Ren's package (Ren's style): tests/kael_gear_check.py, the fists' shape)
    Pc, Nc, Wc, Dc, Ic = clip_iso(Hp, HN, HA['W'], HA['D'], HI)
    Ps, Ns, Ds, Is, ink, src = shell(Pc, Nc, Dc, Ic, GLOVE_T, GLOVE_WALL, (Hp, HI))
    Ws = Wc[src]; near = near_index(Pc[src], Hp)
    col = np.where(ink[:, None] > 0, np.array(INK_C) / 255., np.array(GLOVE_C) / 255.); gline = HA['line'][near]
    # the wrists' rings (Denis, circling the wrist: "è ancora fatto male"): on each bracer's purple cuff band a raised ring, round
    # all of it (the cuff, the seam to Ren's hand, the glove's start), its lips going in under them; what is under it brought in
    # (Meshy's flap of the cuff); the glove flared out to the ring's inside on the hand's side (no neck)
    rings, Rg = [], []
    for side, sd in SIDES:
        j = J[sd]; sx = (X2[:, 0] >= 0) == (sd > 0); c, ax, hb = cuff_band(X2, pur_b, sx & ~isR, j['Eb2'], j['Hb2'])
        h = RING['height'] * j['bracer']; c = c + ax * (h - hb) / 2   # (from the painted band's elbow edge toward the hand: over the join to the glove)
        ref = np.cross(ax, [0., 0., 1.]); ref /= np.linalg.norm(ref)
        ss = (Ps[:, 0] >= 0) == (sd > 0); near_w = sx & (np.linalg.norm(np.cross(X2 - c, ax), axis=1) < .12)
        r_th = ring_radius(np.r_[X2[near_w], Ps[ss]], c, ax, ref, h, RING['clear'], RING['n_th']); r_in = r_th - RING['lip']
        lim = 2 * np.median(r_th)
        hs = ((Hp[:, 0] >= 0) == (sd > 0)) & (np.linalg.norm(np.cross(Hp - c, ax), axis=1) < .12)
        for P_, m_ in ((X2, near_w), (Ps, ss), (Hp, hs)):   # (under the ring: kept RING['under'] inside its surface)
            t, r, k = ring_frame(P_, c, ax, ref, RING['n_th']); m = m_ & (np.abs(t) <= h / 2 + .002) & (r > r_th[k] - RING['under']) & (r < lim)
            u = ((P_ - c) - np.outer(t, ax)) / np.maximum(r, 1e-9)[:, None]
            P_[m] = c + np.outer(t[m], ax) + u[m] * (r_th[k[m]] - RING['under'])[:, None]
        Ps[ss] = flare(Ps[ss], c, ax, ref, r_in, h)
        # (and the glove's open end by the wrist, where Ren's hand starts, carried into the ring: in the gap the bust's paint by
        # the seam showed, a light line)
        Pt, Nt, It_, v = make_skirt(Ps, Ds, Is, c, ax, ref, r_in, h, ss)
        Ps, Ns, Is = np.r_[Ps, Pt], np.r_[Ns, Nt], np.r_[Is, It_]; Ds, ink, Ws, col, gline, near = (np.r_[a, a[v]] for a in (Ds, ink, Ws, col, gline, near))
        # (and the cuff's end and the hand's skin under the glove with it, GLOVE_T and 1 mm less: flared to the same radius the
        # skin and the glove met, and the skin showed through the glove in patches)
        X2[near_w] = flare(X2[near_w], c, ax, ref, r_in - GLOVE_T - .001, h)
        Hp[hs] = flare(Hp[hs], c, ax, ref, r_in - GLOVE_T - .001, h)
        Pr, Nr, Ir, Dr, sr = make_ring(c, ax, ref, r_th, h, RING['bulge'], RING['lip'])
        tb, rb, _ = ring_frame(X2, c, ax, ref, RING['n_th']); ins = sx & (np.abs(tb) <= h / 2) & (rb < lim)
        # (skinned as what it covers: each ring vertex the mean weights of the 8 points under it nearest, then smoothed round
        # the ring; with fixed shares of forearm and hand the hand's start came out of it when the wrist bent)
        iv = np.nonzero(ins)[0]; Wi = np.zeros((len(iv), len(allnames))); np.add.at(Wi, (np.repeat(np.arange(len(iv)), 4), top[iv].ravel()), tw[iv].ravel())
        _, nn = cKDTree(X2[iv]).query(Pr, 8); Wr = Wi[nn].mean(1).reshape(-1, RING['n_th'], len(allnames))
        for _ in range(3): Wr = (Wr + np.roll(Wr, 1, 1) + np.roll(Wr, -1, 1)) / 3
        Wr = Wr.reshape(-1, len(allnames)); Wr /= Wr.sum(1, keepdims=True)
        rings.append(dict(side=side, c=c.tolist(), ax=ax.tolist(), ref=ref.tolist(), h=float(h), r=r_th.tolist(), rin=r_in.tolist(),
                          inBust=mp[ins & (mp >= 0)].tolist(), inHands=np.nonzero(hs & (np.abs(ring_frame(Hp, c, ax, ref, RING['n_th'])[0]) <= h / 2))[0].tolist()))
        Rg.append((Pr, Nr, Ir, Dr, Wr))
        print('%s ring: from the cuff band (%.1f cm) toward the hand, %.1f cm high, %.1f to %.1f cm round the axis' % (side, 100 * hb, 100 * h, 100 * r_th.min(), 100 * r_th.max()))
    # (the outline on the hands drawn inside them too, as a drawing's lines: where a finger lies over another, the thumb over the
    # fingers, the fist over the palm. The body's outline is pushed 2 cm back from the camera: only the hand's silhouette was
    # drawn and the fist read as one block. On the hands, by their share, HAND_LINE[0] of that push and HAND_LINE[1] of its width)
    hw = np.clip(G[:, 3], 0, 1) * hv_all
    # (and on the arms ARM_LINE: where the deltoid lies over the biceps, the triceps over the elbow, the forearm over the upper arm,
    # their lines drawn as the sheet traces the muscles; Denis, 12/11: "ricalca anche i muscoli delle braccia")
    aw = np.clip(G[:, 1] + G[:, 2], 0, 1) * (1 - hw)
    push = 1 + hw * (HAND_LINE[0] - 1) + aw * (ARM_LINE[0] - 1); width = 1 + hw * (HAND_LINE[1] - 1) + aw * (ARM_LINE[1] - 1)
    if outfit:   # (19/11, Denis: "rifai in meshy i vestiti"): Meshy's clothes in place of the bust and his own body
        Wbu = np.zeros((len(used), len(allnames))); np.add.at(Wbu, (np.repeat(np.arange(len(used)), 4), top[used].ravel()), tw[used].ravel())
        under = outfit_part(outfit, J, K, X2[used], N2[used], Wbu, names, allnames,
                    {'scale': SCALE, 'bones': {k_: [round(float(v), 5) for v in t_] for k_, t_ in bones.items()}, 'fingers': fingers, 'fistFrame': frames})
    else: under = None
    armhide = np.zeros(0, np.uint32)
    if arms:   # (19/11, Denis: "rifai ste mani di merda su meshy", "anche polso e avambraccio"): Meshy's forearms, fist and open
        armhide = arm_parts(arms, J, fingers, Wm, names, allnames, X2[used], It, isR[used], under)
    write_part(KAEL_PKG, 'kael_bust', {'pos': X2[used], 'nor': N2[used], 'uv': UVb[used], 'jnt': top[used], 'wgt': tw[used], 'idx': It, 'hide': hide, 'armhide': armhide,
                                       'flat': np.where(isR, HAND_FLAT, 1.)[used],   # (its light: flat, the hands the game's)
                                       'glove': gfield[used],   # (the hands' glove: the signed distance to its edge, m; 1 a hand's vertex)
                                       'lb': ((push - 1) * BODY_LINE_BACK)[used], 'line': width[used]},
               {'scale': SCALE, 'bones': {k_: [round(float(v), 5) for v in t_] for k_, t_ in bones.items()}, 'fingers': fingers, 'fistFrame': frames}, BT, 'png')
    print('written: kael_bust (%d vertices, %d triangles)' % (len(used), len(It)))
    topH = np.argsort(-HA['W'], 1)[:, :4]; twH = np.take_along_axis(HA['W'], topH, 1); twH /= np.maximum(twH.sum(1, keepdims=True), 1e-12)
    if HAND_STYLE == 'foglio':   # (the sheet's: one skin colour, the game's two tones, lines between the fingers)
        # (no line inside the glove: there the hand's, wider than the shell, came out through it in black shards by the thumb; the glove draws its own)
        write_part(KAEL_PKG, 'kael_hands', {'pos': Hp, 'nor': HN, 'uv': np.zeros((len(Hp), 2)), 'jnt': topH, 'wgt': twH, 'idx': HI,
                                            'col': np.tile(np.array(FOGLIO['skin']) / 255., (len(Hp), 1)), 'flat': np.zeros(len(Hp)),
                                            'line': HA['line'] * FOGLIO['line_w'] * np.clip((HA['D'] + .002) / .004, 0, 1), 'lb': np.full(len(Hp), (FOGLIO['line_push'] - 1) * BODY_LINE_BACK)}, {'style': 'foglio'})
        print('written: kael_hands (%d vertices, %d triangles; as the sheet: %d Loop round(s), flat skin)' % (len(Hp), len(HI), FOGLIO['subdiv']))
    else:
        tex, uvh = crop_paint(Image.open(REN_PAINT), R['UV'][rh])
        write_part(KAEL_PKG, 'kael_hands', {'pos': Hp, 'nor': HN, 'uv': uvh, 'jnt': topH, 'wgt': twH, 'idx': HI, 'flat': HA['flat'], 'line': HA['line']}, None, tex)
        print('written: kael_hands (%d vertices, %d triangles; Ren\'s paint cut %dx%d)' % (len(Hp), len(HI), *tex.size))
    # the gloves' part: the shells, then the rings (their outer wall's vertices for tests/viewer_check.py)
    P_, N_, I_, D_, W_, C_, L_, Nn = [Ps], [Ns], [Is], [Ds], [Ws], [col], [gline], [near]; at = len(Ps)
    for g, (Pr, Nr, Ir, Dr, Wr) in zip(rings, Rg):
        g['outer'] = [at + 2 * RING['n_th'], 7 * RING['n_th']]
        P_.append(Pr); N_.append(Nr); I_.append(Ir + at); D_.append(Dr); W_.append(Wr); C_.append(np.tile(np.array(BUST_PURPLE) / 255., (len(Pr), 1)))
        L_.append(np.ones(len(Pr))); Nn.append(-np.ones(len(Pr), np.int64)); at += len(Pr)
    Pg, Ng, Ig, Dg, Wg = (np.concatenate(a) for a in (P_, N_, I_, D_, W_))
    topg = np.argsort(-Wg, 1)[:, :4]; twg = np.take_along_axis(Wg, topg, 1); twg /= np.maximum(twg.sum(1, keepdims=True), 1e-12)
    write_part(KAEL_PKG, 'kael_gloves', {'pos': Pg, 'nor': Ng, 'uv': np.zeros((len(Pg), 2)), 'jnt': topg, 'wgt': twg, 'idx': Ig, 'col': np.concatenate(C_),
                                         'glove': np.c_[Dg, np.ones(len(Dg))], 'line': np.concatenate(L_), 'near': np.concatenate(Nn)},
               {'rings': rings, **({'style': 'foglio', 'inkW': FOGLIO['ink_w']} if HAND_STYLE == 'foglio' else {})})
    print('written: kael_gloves (%d vertices, %d triangles: the shells %.1f mm over the skin, %d edge vertices; 2 rings)' % (len(Pg), len(Ig), 1000 * GLOVE_T, int(ink.sum())))


def bracer_axis(j, Xb, sd):
    """the bust's bracer's ends (its top band's top, its cuff's bottom) on its forearm's axis, in the pose (as arm_parts)"""
    top2 = (j['top_full'] - j['Eb']) @ j['Rf'].T + j['Eb2']; cuff2 = (j['cuff_full'] - j['Eb']) @ j['Rf'].T + j['Eb2']
    sx = (Xb[:, 0] >= 0) == (sd > 0)
    for _ in range(3):
        af = (cuff2 - top2) / np.linalg.norm(cuff2 - top2); L_ = np.linalg.norm(cuff2 - top2); D = Xb - top2; t = D @ af
        r = np.linalg.norm(D - np.outer(t, af), axis=1); C = []
        for a in np.linspace(.15, .85, 8) * L_:
            m_ = sx & (np.abs(t - a) < .006) & (r < .07)
            if m_.sum() > 8: C.append(Xb[m_].mean(0))
        C = np.array(C); c0 = C.mean(0); d0 = np.linalg.svd(C - c0)[2][0]; d0 = d0 if d0 @ af > 0 else -d0
        top2, cuff2 = c0 + ((top2 - c0) @ d0) * d0, c0 + ((cuff2 - c0) @ d0) * d0
    return top2, cuff2


def outfit_part(glb, J, K, Xb, Nb, Wb, names, allnames, extra):
    """Kael's clothes from Meshy (19/11/2026, Denis: "rifai in meshy i vestiti e mettili sopra a quelli vecchi, cioè toglili e
    sostituiscili con quelli nuovi"; docs/meshy/KAEL.md "Vestiti da Meshy"): one piece from the collar's top to the soles
    (top, collar, shoulder wing, sash, skirt, trousers, boots, the upper arms), laid on him: its soles on his, its collar's
    top on the bust's, centred on the bust's chest; each upper arm turned about the bust's shoulder joint onto the bust's
    upper arm (to its bracer's top, where Meshy's forearms start), each leg about its hip onto his leg; skinned as the
    bust (its nearest vertex facing the same way) above, as his own legs below; cut under the head's collar and past the
    forearms' elbow bands. Writes kael_outfit: its 'hide' all of his own triangles (the bust is not drawn with it); extra
    (the bust's bones, fingers, fists' frames) in its json, as the bust's."""
    m = glbio.read(glb); P, N, UV, I = m['pos'].astype(float), m['nor'].astype(float), m['uv'].astype(float), m['idx'].astype(np.int64)
    painted = glb[:-4] + '_painted.png'
    img = Image.open(painted if os.path.exists(painted) else io.BytesIO(m['img'])).convert('RGB')
    if img.size[0] > OUTFIT_TEX: img = img.resize((OUTFIT_TEX, OUTFIT_TEX), Image.LANCZOS)   # (the page's size)
    T = np.asarray(Image.open(io.BytesIO(m['img'])).convert('RGB')).astype(int); S = T.shape[0]
    col = T[np.clip((UV[:, 1] * S).astype(int), 0, S - 1), np.clip((UV[:, 0] * S).astype(int), 0, S - 1)]
    pur = (col[:, 2] > 140) & (col[:, 2] - col[:, 1] > 60)
    sole = K['P'][:, 1].min(); top = Xb[:, 1].max()
    s = (top - sole) / (P[:, 1].max() - P[:, 1].min()); X = (P - [0., P[:, 1].min(), 0.]) * s + [0., sole, 0.]
    chest = lambda Y: Y[(Y[:, 1] > 1.22) & (Y[:, 1] < 1.34) & (np.abs(Y[:, 0]) < .16)][:, [0, 2]].mean(0)
    d = chest(Xb) - chest(X); X[:, [0, 2]] += d
    print('outfit: %.3f m per unit, its chest moved %s m onto the bust\'s' % (s, np.round(d, 3)))
    Nn = N.copy()
    sm = lambda v: (lambda t: t * t * (3 - 2 * t))(np.clip(v, 0, 1))
    def turn_about(X, Nn, piv, a, b, w):   # (the points turned about piv taking a onto b and stretched along it to its length (not
        # thinner: only along it), by w)
        R = turn(a, b); k = np.linalg.norm(b) / np.linalg.norm(a); ub = b / np.linalg.norm(b)
        Q = (X - piv) @ R.T; Xr = piv + Q + np.outer((Q @ ub) * (k - 1), ub)
        return X + (Xr - X) * w[:, None], Nn + ((Nn @ R.T) - Nn) * w[:, None]
    cut = np.zeros(len(I), bool); cutv = np.zeros(len(X), bool)
    for side, sd in SIDES:
        j = J[sd]; Ab = j['Ab']; top2, cuff2 = bracer_axis(j, Xb, sd)
        # (its upper arm: the arm's line (its points well out of the shoulder), from the shoulder joint; its elbow band's top:
        # the first purple slices along it past OUTFIT_TAT (the shoulder's tattoo before))
        arm = (sd * X[:, 0] > sd * Ab[0] + .05) & (X[:, 1] < Ab[1]) & (X[:, 1] > OUTFIT_ARM_Y)   # (not the trousers)
        c = X[arm].mean(0); u = np.linalg.svd(X[arm] - c, full_matrices=False)[2][0]; u = u if u[1] < 0 else -u
        tau = (X - c) @ u; rad = np.linalg.norm((X - c) - np.outer(tau, u), axis=1); near = rad < .07
        t0 = (Ab - c) @ u; ts = np.arange(t0 + OUTFIT_TAT, tau[arm].max(), .005)
        fr = np.array([pur[near & (np.abs(tau - a) < .005)].mean() if (near & (np.abs(tau - a) < .005)).sum() > 5 else 0 for a in ts])
        tb = ts[np.argmax(fr > .35)]; eo = c + u * tb
        if os.environ.get('KAEL_OUTFIT_DEBUG'): print('   Ab', np.round(Ab, 3), 'arm line c', np.round(c, 3), 'u', np.round(u, 2), 't0 %.3f' % t0, 'profile', [(round(float(a - t0), 3), round(float(f), 2)) for a, f in zip(ts, fr)][::2])
        fore = ((X[:, 0] >= 0) == (sd > 0)) & (tau > tb - .01) & (rad < .12) & (X[:, 1] > OUTFIT_ARM_Y - .35)   # (its forearm, from its band)
        wfo = sm((tau - tb + .01) / .03) * fore
        ua = (eo - Ab) / np.linalg.norm(eo - Ab); ta = (X - Ab) @ ua
        da = np.linalg.norm((X - Ab) - np.outer(np.clip(ta, 0, None), ua), axis=1)
        w = sm(ta / .08) * sm((.085 - da) / .03)
        ang = np.degrees(np.arccos(np.clip(ua @ ((top2 - Ab) / np.linalg.norm(top2 - Ab)), -1, 1)))
        X, Nn = turn_about(X, Nn, Ab, eo - Ab, top2 - Ab, w)
        # (its forearm bent at the elbow band onto the bust's forearm (Meshy's forearms lie there): its line from the band's top)
        af = (cuff2 - top2) / np.linalg.norm(cuff2 - top2); fm = fore & (tau > tb + .03) & (rad < .07)
        Fc = X[fm].mean(0); df = np.linalg.svd(X[fm] - Fc, full_matrices=False)[2][0]; df = df if df @ af > 0 else -df
        X, Nn = turn_about(X, Nn, top2, df, af, wfo)
        # (past the band's top along it, round it: under Meshy's forearms, cut)
        Dv = X - top2; tv = Dv @ af
        cutv |= ((X[:, 0] >= 0) == (sd > 0)) & (tv > ARM_CUT) & (np.linalg.norm(Dv - np.outer(tv, af), axis=1) < .10)
        print('outfit %s arm: its elbow band %.3f m from the shoulder, turned %.1f deg onto the bust\'s (%.3f m)' % (side, np.linalg.norm(eo - Ab), ang, np.linalg.norm(top2 - Ab)))
        # (its leg: the line of its trousers' slices' middles onto his leg's (hip joint to ankle))
        hip = K['Wm'][names.index(side + 'UpLeg')][:3, 3]; ank = K['Wm'][names.index(side + 'Foot')][:3, 3]
        lg = ((X[:, 0] >= 0) == (sd > 0)) & (X[:, 1] < hip[1] - .12) & (X[:, 1] > ank[1] + .08) & (np.abs(X[:, 0]) > .02)
        C = np.array([X[lg & (np.abs(X[:, 1] - y) < .02)].mean(0) for y in np.linspace(ank[1] + .12, hip[1] - .16, 8)])
        c0 = C.mean(0); dl = np.linalg.svd(C - c0)[2][0]; dl = dl if dl[1] < 0 else -dl
        a_ = c0 + dl * ((ank - c0) @ dl) - hip; b_ = ank - hip
        wl = ((X[:, 0] >= 0) == (sd > 0)) * sm((hip[1] - .04 - X[:, 1]) / .14)
        X, Nn = turn_about(X, Nn, hip, a_, b_, wl * OUTFIT_LEG)
        print('outfit %s leg: turned %.1f deg onto his' % (side, np.degrees(np.arccos(np.clip(a_ @ b_ / np.linalg.norm(a_) / np.linalg.norm(b_), -1, 1)))))
    Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)
    cen = X[I].mean(1); cut |= cutv[I].any(1)
    cut |= (cen[:, 1] > COLLAR_CUT[0]) & (np.hypot(cen[:, 0] - COLLAR_CUT[1][0], cen[:, 2] - COLLAR_CUT[1][1]) < COLLAR_CUT[2])
    # (the skin: the bust's above, his own legs' below)
    up = np.isin(K['JN'], [names.index(n) for n in UPPER]); wu = (K['WG'] * up).sum(1)
    lv = (wu < .5) & (K['P'][:, 1] < .95)
    Wk = np.zeros((int(lv.sum()), len(allnames))); np.add.at(Wk, (np.repeat(np.arange(int(lv.sum())), 4), K['JN'][lv].ravel()), K['WG'][lv].ravel())
    DP = np.r_[Xb, K['P'][lv]]; DN = np.r_[Nb, K['N'][lv]]; DW = np.r_[Wb, Wk]
    W = DW[nearest_facing(DP, DN, X, Nn)]
    wv, A, deg = weld_graph(X, I); W = smooth(W, wv, A, deg, OUTFIT_SMOOTH)
    topo = np.argsort(-W, 1)[:, :4]; tw = np.take_along_axis(W, topo, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-12)
    # (and all that moves mostly with the forearms and the hands: Meshy's forearms are there; its thumbs, out of the arm's line
    # in its pose, were left floating by the fists)
    fh = np.array([n.endswith(('ForeArm', 'Hand')) or 'Hand' in n for n in allnames])
    wf = (W * fh).sum(1) / np.maximum(W.sum(1), 1e-12)
    tops = np.array([bracer_axis(J[sd], Xb, sd)[0] for _, sd in SIDES]); far = cKDTree(tops).query(X)[0] > OUTFIT_ELBOW   # (not the elbows': into the bands)
    cut |= ((wf > OUTFIT_FORE) & far)[I].any(1)
    print('outfit: %d vertices mostly on the forearms and hands (over %.2f), away from the elbows, cut' % (int(((wf > OUTFIT_FORE) & far).sum()), OUTFIT_FORE))
    # (and what the cuts left loose: pieces of the hands (fingers past the cut), small, apart from the rest; welded, Meshy's
    # seams split it)
    from scipy.sparse import coo_matrix as _coo
    from scipy.sparse.csgraph import connected_components as _cc
    wv2 = np.unique(np.round(X / 1e-6).astype(np.int64), axis=0, return_inverse=True)[1].ravel(); Ik = I[~cut]; tk = np.nonzero(~cut)[0]
    e_ = wv2[np.r_[Ik[:, [0, 1]], Ik[:, [1, 2]]]]; nw = wv2.max() + 1
    _, lab = _cc(_coo((np.ones(len(e_)), (e_[:, 0], e_[:, 1])), shape=(nw, nw)), directed=False)
    tl = lab[wv2[Ik[:, 0]]]; cnt = np.bincount(tl); small = cnt[tl] < OUTFIT_BITS * len(Ik)
    cut[tk[small]] = True
    print('outfit: %d loose pieces cut (%d triangles; the pieces kept: %s triangles)' % (len(np.unique(tl[small])), int(small.sum()), sorted(np.unique(cnt[tl[~small]]).tolist(), reverse=True)))
    keep = ~cut; It = I[keep]
    write_part(KAEL_PKG, 'kael_outfit', {'pos': X, 'nor': Nn, 'uv': UV, 'jnt': topo, 'wgt': tw, 'idx': It, 'hide': np.arange(len(K['I']), dtype=np.uint32)},
               dict(extra, meshy=os.path.basename(glb)), img, 'png' if os.path.exists(painted) else 'jpg')   # (Meshy's own paint, as it is (Denis, 19/11: "usa quell'immagine così com'è"): a JPEG, the page's size)
    print('written: kael_outfit (%d vertices, %d triangles, %d cut: under the head\'s collar and the forearms; all of his own %d hidden)' % (len(X), len(It), int(cut.sum()), len(K['I'])))
    return X[np.unique(It)]


def arm_parts(glbs, J, fingers, Wm, names, allnames, Xb, Ib, rb, under=None):
    """Meshy's forearms (19/11/2026, docs/meshy/KAEL.md "Avambracci da Meshy"): glbs = (the fist's GLB, the open hand's), each
    a right forearm from below the elbow to the fingertips (tools/kael_gear.py place_arm). Laid on each arm of the bust (Xb,
    Ib: its part's vertices and triangles; rb: Ren's hands' vertices among them) from its bracer's top band to its cuff,
    the hand turned as the hand bone at rest; skinned rigid to the forearm, then the hand, blended over the glove's start.
    Writes kael_armfist and kael_armopen (both sides; the game shows the one the hands' curl asks for) and returns the bust's
    triangles under them (hidden with them: its forearms, the seams to the old hands)."""
    from scipy.spatial.transform import Rotation
    from kael_gear import arm_bands, place_arm
    hide = np.zeros(len(Ib), bool); fd = {f['n']: f for f in fingers}
    for name, g in zip(('armopen', 'armfist'), glbs[::-1]):   # (the open hand first: its length sets both hands' size)
        m = glbio.read(g); P, N, UV, I = m['pos'].astype(float), m['nor'].astype(float), m['uv'].astype(float), m['idx'].astype(np.int64)
        img = Image.open(io.BytesIO(m['img'])).convert('RGB'); T = np.asarray(img).astype(int); S = T.shape[0]
        painted = g[:-4] + '_painted.png'   # (its paint as the sheet draws it, tools/kael_arm_paint.py; Meshy's own if there is none)
        col = T[np.clip((UV[:, 1] * S).astype(int), 0, S - 1), np.clip((UV[:, 0] * S).astype(int), 0, S - 1)]
        y0, y1, ye = arm_bands(P, col, lambda c: (c[:, 2] > 140) & (c[:, 2] - c[:, 1] > 60))
        if name == 'armopen':   # (the hands as big as Denis chose (HAND_RATIO, HAND_MUL: cuff to fingertip of the bracer), the open one's measured; the fist's the same)
            kh = {sd: HAND_RATIO * HAND_MUL * (y1 - y0) / (P[:, 1].max() - y1) for _, sd in SIDES}
        out = []
        for side, sd in SIDES:
            j = J[sd]; Rk = Wm[names.index(side + 'Hand')][:3, :3]
            pos = lambda n: j['Hb2'] + Rk @ np.array(fd[n]['t']) if fd[n]['p'] == side + 'Hand' else pos(fd[n]['p']) + Rk @ np.array(fd[n]['t'])
            v = np.array(fd[side + 'HandMiddle2']['t']); palm = Rk @ (Rotation.from_quat(fd[side + 'HandMiddle1']['fist']).apply(v) - v)
            top2 = (j['top_full'] - j['Eb']) @ j['Rf'].T + j['Eb2']; cuff2 = (j['cuff_full'] - j['Eb']) @ j['Rf'].T + j['Eb2']
            # (the bracer's ends, its top band's top and its cuff's bottom, brought onto the forearm's axis: the slices' middles
            # of the bust's forearm)
            sx = (Xb[:, 0] >= 0) == (sd > 0)
            for _ in range(3):
                af = (cuff2 - top2) / np.linalg.norm(cuff2 - top2); L_ = np.linalg.norm(cuff2 - top2); D = Xb - top2; t = D @ af
                r = np.linalg.norm(D - np.outer(t, af), axis=1); C = []
                for a in np.linspace(.15, .85, 8) * L_:
                    m_ = sx & (np.abs(t - a) < .006) & (r < .07)
                    if m_.sum() > 8: C.append(Xb[m_].mean(0))
                C = np.array(C); c0 = C.mean(0); d0 = np.linalg.svd(C - c0)[2][0]; d0 = d0 if d0 @ af > 0 else -d0
                top2, cuff2 = c0 + ((top2 - c0) @ d0) * d0, c0 + ((cuff2 - c0) @ d0) * d0
            # (its elbow band over the bust's arm: the bust kept ARM_CUT m into the band, so its cut edge lies under it; the band
            # wide enough round it, ARM_CLEAR over the bust there)
            af = (cuff2 - top2) / np.linalg.norm(cuff2 - top2); sc = np.linalg.norm(cuff2 - top2) / (y1 - y0)
            D = Xb - top2; t = D @ af; r = np.linalg.norm(D - np.outer(t, af), axis=1)
            kept = np.zeros(len(Xb), bool); kept[Ib[~(sx & (t > ARM_CUT))[Ib].any(1)].ravel()] = True   # (the bust's vertices still drawn)
            near = sx & kept & (t > -.002) & (t < sc * (ye - y0)) & (r < .09)
            if under is not None:   # (with Meshy's clothes the arm under the band is theirs: its drawn vertices)
                Xu = under[under[:, 0] >= 0] if sd > 0 else under[under[:, 0] < 0]; Du = Xu - top2; tu = Du @ af; ru = np.linalg.norm(Du - np.outer(tu, af), axis=1)
                nu = (tu > -.02) & (tu < sc * (ye - y0)) & (ru < .055)   # (the arm's, not the flank's by the elbow)
            band = P[:, 1] < ye; cb = P[band][:, [0, 2]].mean(0); rp = sc * np.median(np.linalg.norm(P[band][:, [0, 2]] - cb, axis=1))
            rn = ru[nu] if under is not None else r[near]
            rb_ = float(np.percentile(rn, 98)) if len(rn) else 0.; k0 = max(1., (rb_ + ARM_CLEAR) / rp)
            # (as thick as the bust's forearm round its elbow (no step there; its band ARM_CLEAR over the bust kept under it),
            # thinning toward the wrist to its band ARM_WRIST of the hand's own (Denis's 90%: no neck at the glove))
            L_ = np.linalg.norm(cuff2 - top2); band = P[:, 1] < ye; cb = P[band][:, [0, 2]].mean(0); rr = np.linalg.norm(P[:, [0, 2]] - cb, axis=1)
            A_ = np.linspace(0, 1, 11); kb = []
            for a in A_:
                m_ = sx & (np.abs(t - a * L_) < .006) & (r < .08); mp_ = np.abs(P[:, 1] - (y0 + a * (y1 - y0))) < .04
                kb.append(np.median(r[m_]) / (sc * np.median(rr[mp_])) if m_.sum() > 5 and mp_.any() else np.nan)
            kb = np.array(kb); kb = np.where(np.isnan(kb), np.nanmedian(kb), kb); kb = np.convolve(np.r_[kb[0], kb, kb[-1]], np.ones(3) / 3, 'valid')
            ks = kb.copy(); hw = min(max(kh[sd], kb[-1] / ARM_WRIST), ARM_WIDE * kh[sd])   # (the hand as wide as its wrist band asks, ARM_WRIST under it, at most ARM_WIDE its length's scale; as long as Denis chose)
            ks[A_ * (y1 - y0) + y0 <= ye] = np.maximum(ks[A_ * (y1 - y0) + y0 <= ye], k0)
            ys = y0 + A_ * (y1 - y0)
            X, Nn, w = place_arm(P, N, y0, y1, top2, cuff2, j['Hb2'], pos(side + 'HandMiddle1') - j['Hb2'], -palm, side == 'Left', hand=(kh[sd], hw), radial=(ys, ks))
            jn = np.zeros((len(X), 4), np.int64); jn[:, 0] = allnames.index(side + 'ForeArm'); jn[:, 1] = allnames.index(side + 'Hand')
            wg = np.zeros((len(X), 4)); wg[:, 0] = 1 - w; wg[:, 1] = w
            out.append((X, Nn, UV, jn, wg, I[:, ::-1] if side == 'Left' else I))
            if name == 'armfist':   # (the bust's triangles under it: ARM_CUT into its elbow band, round the forearm's axis, to past the hand)
                on = sx & (t > ARM_CUT) & (t < np.linalg.norm(cuff2 - top2) + .25) & (r < .10)
                hide |= on[Ib].all(1)
            print('%s %s: from y %.2f to %.2f of its units on the bracer (%.3f m), %.4f m per unit, the hand %.2f times, the elbow band %.2f times '
                  '(%.1f mm round, the bust under it %.1f), as wide as %s along it, the hand %.2f wide, %d vertices' % (name, side, y0, y1, np.linalg.norm(cuff2 - top2), sc, kh[sd], k0, 1000 * rp, 1000 * rb_,
                  np.round(ks, 2).tolist(), hw, len(X)))
        at = 0; Is_ = []
        for o in out: Is_.append(o[5] + at); at += len(o[0])
        write_part(KAEL_PKG, 'kael_' + name, {'pos': np.concatenate([o[0] for o in out]), 'nor': np.concatenate([o[1] for o in out]),
                                              'uv': np.concatenate([o[2] for o in out]), 'jnt': np.concatenate([o[3] for o in out]),
                                              'wgt': np.concatenate([o[4] for o in out]), 'idx': np.concatenate(Is_)}, {'meshy': os.path.basename(g)},
                   Image.open(painted).convert('RGB') if os.path.exists(painted) else img, 'png' if os.path.exists(painted) else 'jpg')
    hide |= rb[Ib].any(1)
    print('arms: the bust\'s triangles under them hidden with them: %d' % int(hide.sum()))
    return np.nonzero(hide)[0].astype(np.uint32)


if __name__ == '__main__':
    if len(sys.argv) not in (2, 4, 5): sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:4] if len(sys.argv) >= 4 else None, sys.argv[4] if len(sys.argv) == 5 else None)
