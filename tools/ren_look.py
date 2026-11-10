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
        fingers on their bones (bone index: the package's bones, then the fingers in the order above) and the band's
        back on the Hips (band_on_hips)
  nor: [byte offset, count] float32 x3 per vertex: the normals the light uses (smoothed, smooth_normals)
  flat: [byte offset, count] float32 per vertex: how much of the light the toon shading leaves out there (1 on the front
        of the head, FLAT_BODY on the rest of the front, fading to 0 by the sides, where tools/paint_from_drawing.py
        paints the drawing): the drawing has its own shading (the anime muscles too), the light only darkened it in
        muddy bands; the sides and the back keep the toon light, for the volume
  line: [byte offset, count] float32 per vertex: the outline's width there (1; LINE_FACE on the front of the face,
        where the shell around the nose showed as a dark wedge; LINE_FINGER on the fingers, whose shells stuck out
        between the curled fingers of the fist)
  sash: {ribbons: [{j: SASH_SEG + 1 points in the Hips bone's frame, from under the band (its edge the 2nd) to the tip;
        fix: how many of them stay on the body; sk: per point from the top, the skin ([bone, weight] x4) of the body
        behind it (the fixed ones and those lying on the vest's flaps); tuck: m under the band; wp: width at each
        point; w: the widest; cut: share of the length of the tip's slanted cut; out: the side of a (1, -1) away from
        the middle; a: unit across; n: unit out of its face; c: colour (the band's)}], body: [body_shape of each of
        BODY], blend: [byte offset, count] uint16: the vertices shared between the parts (BLEND_W)}: the sash's two
        hanging tails as ribbons of their own (Meshy fused them with the trousers and the vest), where the drawing has
        them seen from the front, as wide as there, coming out from under the band's knot; tools/paint_from_drawing.py
        paints the old ones over
  face: the face decal, laid per pixel by its bind position's front projection (fit: drawing_fit's scale, cx, by; decal:
        FACE_DECAL) where it is on the front of the face and the neck (depth: face_depth's {box, z, n, map: [byte
        offset, count] uint8 x2 per cell}; within seen m of it), faded as its bind normal turns away (front:
        FACE_FRONT); and the shadow under the jaw (shade: JAW_SHADE; jaw: {axis: JAW_AXIS, th: JAW_TH, y: the heights'
        range, deep: the deepest band, up: JAW_UP, map: [byte offset, count] uint8 x2 per angle: jaw_ring's edge height
        over y, band depth over deep})
  move: {idx: [byte offset, count] uint16, pos, nor: [byte offset, count] float32 x3}: the vertices drawn_shape changes
        (the nose flatter, the fringe off the eyes, the collar's points), their bind positions and normals (all the
        rest is measured on it)
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
LINE_THUMB = (.08, .92)   # none where the thumb's skin turns into the hand's (this share of it on the thumb's bones)
LINE_RAMP = .02      # m: on the hands the outline grows from none to full over this (see main)
LINE_PALM = .2       # nor on the hand's inner side (its normal this far toward the palm's): curled into the fist, it
                     # faces itself, its shell showed as black wedges in the gaps between the fingers (Denis: "lo spigolo")
FLAT_BODY = 1.       # flat light on the front of the body (the drawing), as on the face
WRAP_LIGHT, WRAP_GREY = 150, 45   # the wraps in Meshy's texture: every channel over WRAP_LIGHT, their spread under WRAP_GREY
PERSIST = .015       # a finger stands out at least this far (geodesic, m) from where it joins the hand
FINGER_SEG = (.45, .30, .25)    # proximal, middle and distal phalanx: shares of a finger's length
FREE = .80           # the free part of a finger (from the web between the fingers to the tip): share of its length
THUMB_IP = .5        # the thumb's last joint: this share of its free part from the web
BLEND = .35          # a joint's skin blend reaches this share of the shorter phalanx beside it, on each side
FIST = (82, 100, 60)    # the fist: bend (degrees) at the knuckle, middle and last joint of a finger
THUMB_SMOOTH = 20   # rounds the palm's share on the thumb's first bone is spread over its neighbours (see main)
THUMB_ON = 1.1      # in the fist the thumb lies across the index and middle finger, this many radii in front of them
NAMES = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')
# The sash's tails: on the model, orange below SASH_BAND (m) in pieces of at least SASH_MIN vertices (painted over,
# tools/paint_from_drawing.py); as ribbons, the drawing's two tails seen from the front (its orange under its band on
# each side of the middle, in pieces of at least SASH_PIECE px: the dark folds split a tail), each a chain of SASH_SEG
# bones: one under the band, from SASH_TUCK m behind its front to its lower edge, where the ribbon comes out (its front
# face SASH_OUT m out of the body; SASH_TH m thick, as e_model.js MD_RIB.th), then evenly down to the drawing's tip,
# SASH_GAP m in front of the body from 10 cm under the band; as wide as the drawing's tail there (across it, clamped
# to SASH_W). Its top (under the band, and down to SASH_FIX m under it) moves with the skin of the body there: of the
# SASH_SKIN front vertices nearest to each of its points, seen from the front (Meshy skinned the band to the hips and the
# thighs: in the guard it is up to 10 cm from where the hips alone would carry it); so does the shape the rest hangs in,
# down to SASH_LIE m under the band (lying on the vest's flaps, which follow the thighs).
SASH_BAND, SASH_MIN, SASH_SEG, SASH_GAP, SASH_W = 1.06, 200, 9, .018, (.02, .1)
SASH_TUCK, SASH_FIX, SASH_OUT, SASH_TH, SASH_PIECE, SASH_SKIN, SASH_LIE = .015, .05, .002, .012, 1000, 8, .15
# Meshy's old tails (sash_tails) hidden on the body (tools/ren_head.py) and their paint left out (tools/paint_meshy.py): the
# triangles with TAILS_TOUCH of their vertices or more (with 2, the row that joined them to the vest stayed: teeth along
# its edge)
TAILS_TOUCH = 1
TAILS_STUB = (.01, 1.088, .04)   # see tail_stubs()
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
# The band's back on the hips (9/11/2026, Denis: "la fascia si distorce quando si abbassa"): Meshy skinned the band a third
# to the thighs and its top to the spine, so crouching (the thighs up, the spine bent forward) stretched its back to three
# times its height. A belt follows the pelvis: the trunk's vertices (BAND_TRUNK of their weight on the trunk's bones and the
# thighs, all of them from [1]) between the band's heights (sash_band) all on the Hips, blending into their own skin over
# BAND_T m above and below; behind (all of it under BAND_Z[0] m, none over [1]: the front keeps its skin, the thighs
# rising into it in the crouch, the ribbons' tops on it).
BAND_T, BAND_TRUNK, BAND_Z = .03, (.8, .95), (-.04, .04)
# The toon light's normals smoothed (9/11/2026, Denis's close-up of the shoulder: "devi assolutamente aggiustare tutto quello
# che c'è nell'immagine"): on Meshy's lumpy surface and across its texture seams the light's bands broke into angular
# patches on the vest and the arms; the light follows the broad form instead (as the drawings' shadows): the vertices'
# normals (the mesh welded across its seams) averaged with their neighbours' NOR_ITER times (half each time), the hands'
# kept (their weight, up to all of it: the fingers' small forms)
NOR_ITER = 12
HAND_NOR_ITER = 8    # the hands' light normals: smoothed this many rounds (not NOR_ITER: their knuckles kept)


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


# The shape (bind pose, model space) where Meshy's differs from the drawing; the paint (tools/paint_from_drawing.py) and
# the model (look data move, CFG.looks.ren.faceShape) use the same (Denis, 7/11: "la faccia è troppo buggata", "creali un
# naso piccolo coerente con tutto", "occhi mezzi coperti", "il colletto ... a punta"):
# - the face: Meshy made the nose a thin ridge with a zigzag front, the mouth a slit 2-3 cm deep, the eyes sockets and
#   the cheeks and jaw creased (the drawing projected on them stretched into smears, the outline showed through the
#   creases as black lines; Denis, 7/11: "non riesci a farlo come un viso normale?"): the ridge flattened and the slit
#   filled to a quadratic fitted to Meshy's face there (FACE_X: its middle; robustly, the ridge and the slit left out;
#   NOSE_BOX, MOUTH_BOX, fading to Meshy's over NOSE_FADE m at the boxes' edges); then the whole face smoothed (face_region:
#   from under the fringe to under the chin, in front of the ears; FACE_SMOOTH rounds of Taubin smoothing, its border
#   with the hair and the neck kept), and a small nose put on it (NOSE: from its root between the eyes to its tip, h m out
#   at the tip, half as wide as w at the root and the tip, back on the face at end); its normals the smooth surface's;
# - the fringe: hanging 2-4 cm in front of the face down to the eyes (a camera a little above saw them half covered): its
#   hair more than FRINGE_Z m in front of the forehead (z FRINGE_FACE) lifted to the brows (y FRINGE_CUT[0]; the lock
#   between the eyes, FRINGE_CUT[2] m either side of x FRINGE_X, down to FRINGE_CUT[1], as drawn), what hung below
#   kept FRINGE_KEEP as long, and pulled FRINGE_BACK of the way back toward the face from 2 cm above the cut down;
# - the collar: a round roll; its top corners seen from the front (the highest and outermost of its teal and light rim
#   by the neck) pulled out and up by COLLAR_TIP m into the drawing's points, less with the distance (gone at COLLAR_R).
FACE_X, NOSE = .0124, {'root': 1.581, 'tip': 1.555, 'end': 1.548, 'h': .009, 'w': (.005, .009)}   # (where the drawing's nose is)
NOSE_BOX, MOUTH_BOX, NOSE_FADE = (.014, (1.532, 1.586)), (.032, (1.497, 1.537)), .005   # (half width about FACE_X, y range)
FACE_SMOOTH, FACE_BOX = 30, (.066, (1.465, 1.66), -.035)   # face_region's box: half width about FACE_X, y range, in front of z
FRINGE_X, FRINGE_CUT, FRINGE_KEEP, FRINGE_BACK, FRINGE_FACE, FRINGE_Z = .005, (1.628, 1.600, .016), .3, .35, .078, .006
COLLAR_TIP, COLLAR_R = (.025, .02), .05
# The face's decal (CFG.looks.ren.faceShape): Meshy left the nose and the mouth only a few texels of its texture (the
# drawing painted there came out blurred, in blocks), so the drawn face's features are a texture of their own
# (tools/paint_from_drawing.py: <name>_face.png, the drawing's FACE_DECAL box, x0, y0, x1, y1 px: the eyes and brows, the
# nose, the mouth) laid on the face by their own coordinates: each point's front projection on the drawing
# (drawing_fit; the smooth face's chin is where the drawn one is). Shown on the front of the head in front of the ears
# and of the neck (FACE_ZONE: half width about FACE_X, y range), as it faces the front (FACE_FRONT: the normal's z where
# it starts and where it is all).
# Under the jaw (Denis, 7/11 and 8/11: "non voglio bug o cose strane", "di lato sembra troppo fatto male"): a shadow in
# the drawing's shadow colour under the jaw (JAW_SHADE, 0..1) on the model's own shape, the same from every side: around
# the neck's axis (JAW_AXIS: x, z) the jaw's lower edge at each angle from the front (jaw_ring: scanning down from
# JAW_SCAN[0] (from JAW_NOSE[0] at the front, under the nose, widening to the sides by JAW_NOSE[1] degrees), the first
# height where the outermost surface of the face and the neck steps in more than JAW_STEP m within JAW_WIN m, at that
# step's steepest mm: the chin's front onto its underside, the jaw's sides onto the neck; along the angle, the piece
# through the front without jumps of JAW_JUMP m (single missing angles filled in), smoothed; its ends: under the ears,
# where the jaw meets the neck), and under it
# a band as deep as the drawing's shadow (JAW_DEEP: m at the chin, m at the sides, from JAW_DEEP[2] degrees), narrowing
# to nothing over the last JAW_TAPER degrees toward the ears, where the jaw meets the neck; from JAW_UP m above the edge.
# Its edges compare each point's own position with those smooth curves: crisp and smooth from every side. Tried and
# dropped (docs/HANDOFF.md): the drawing's V laid from the front, the shadow from the jaw's height over the neck or where
# the skin faces down (Meshy's neck is lumpy: blotches), a band seen from the front (from the side it covered the jaw's
# side and the neck's back like a stain). The jaw's line is the outline.
FACE_DECAL = (440, 130, 580, 250)
JAW_AXIS, JAW_SCAN, JAW_NOSE, JAW_STEP, JAW_WIN, JAW_JUMP, JAW_UP = (FACE_X - .001, -.05), (1.575, 1.45), (1.545, 30.), .008, .006, .012, .0015
JAW_DEEP, JAW_TAPER, JAW_TH = (.028, .0145, 25.), 15., (-100., 1., 201)   # JAW_TH: the look data's angles (first, step, count)
JAW_SHADE = (162 / 255, 104 / 255, 75 / 255)
FACE_ZONE, FACE_FRONT, FACE_FLAT, FACE_SEEN, FACE_CELL = (.06, (1.47, 1.635)), (.3, .55), .035, .003, .001   # FACE_FLAT: half width of the face's middle, all flat lit


# The skin of the head and the neck (Denis, 7/11: "la faccia è ancora fatta malissimo, non voglio bug o cose strane"):
# Meshy's skin-coloured texture there is one big piece (the face, the jaw, the neck) and small islands among the hair
# (its glints, the tips of the ears showing through the locks): those are hair; the islands on the face's front
# (FACE_ZONE[0] about FACE_X, in front of z SKIN_FRONT_Z: the forehead between the fringe's locks, beside the eyes) are
# skin. On the skin the light is flat (the toon light's bands followed the facets of Meshy's cheeks, jaw and neck:
# blocks); the shadow under the jaw is the drawing's, in the face decal.
SKIN_FRONT_Z = .02
# The neck's front down to the collarbones (NECK_ZONE: x about its middle, its half width; y range; in front of z), clean
# skin and flat light like the face (the drawing painted there fell in blotches; and Meshy skinned it to the spine: the
# head's and the neck's skin above did not reach it).
NECK_ZONE = (.006, .065, (1.455, 1.53), -.04)


def neck_zone(p):
    """True for the points p (n x 3) in NECK_ZONE."""
    return (np.abs(p[:, 0] - NECK_ZONE[0]) < NECK_ZONE[1]) & (p[:, 1] > NECK_ZONE[2][0]) & (p[:, 1] < NECK_ZONE[2][1]) & (p[:, 2] > NECK_ZONE[3])


def head_skin(P, I, col, whn):
    """Per vertex, True on the skin of the head and the neck (see above). P: positions; col: the texture's colour at each
    vertex (Meshy's); whn: each vertex's weight on the head and the neck bones."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel(); nw = len(first)
    sk = (col[:, 0] > 120) & (col[:, 1] > 75) & (col[:, 0] - col[:, 2] > 40)
    skw = np.zeros(nw); np.add.at(skw, weld, sk.astype(float)); skw = skw / np.bincount(weld, minlength=nw) > .5
    hn = np.zeros(nw); np.maximum.at(hn, weld, whn); sel = skw & (hn > .3)
    T = weld[I]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0); E = E[sel[E[:, 0]] & sel[E[:, 1]]]
    lab = connected_components(coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(nw, nw)), directed=False)[1]
    ids, cnt = np.unique(lab[sel], return_counts=True); big = ids[np.argmax(cnt)]
    Pw = P[first]; front = (np.abs(Pw[:, 0] - FACE_X) < FACE_ZONE[0]) & (Pw[:, 2] > SKIN_FRONT_Z)
    keep = sel & ((lab == big) | front)
    print('head and neck skin: %d vertices (the big piece %d), %d in islands among the hair' % (int(keep.sum()), int((sel & (lab == big)).sum()), int((sel & ~keep).sum())))
    return keep[weld]


def face_and_neck(face, hs, col, P):
    """Per vertex: the face (drawn_shape's), the head's and the neck's skin (head_skin's hs) and the neck's front
    (NECK_ZONE, skin-coloured in Meshy's texture: col)."""
    return face | hs | ((col[:, 0] > 120) & (col[:, 1] > 75) & (col[:, 0] - col[:, 2] > 40) & neck_zone(P))


def jaw_ring(P, I, sel):
    """The shadow under the jaw (JAW_*) around the neck's axis: at each angle of JAW_TH (degrees from the front, toward
    +x), the jaw's edge height and the band's depth under it (0 where there is no jaw), from the triangles of sel
    (face_and_neck: not the hair, nor the collar). (heights, depths, the first and last angle of the jaw)"""
    from scipy import ndimage
    th = np.degrees(np.arctan2(P[:, 0] - JAW_AXIS[0], P[:, 2] - JAW_AXIS[1])); r = np.hypot(P[:, 0] - JAW_AXIS[0], P[:, 2] - JAW_AXIS[1])
    t0, dt, nt = JAW_TH; dy = .001; y0 = JAW_SCAN[1] - JAW_WIN; ny = int(round((JAW_SCAN[0] - y0) / dy)) + 1
    R = np.full((nt, ny), -np.inf)   # the outermost surface's distance from the axis, per angle and height
    for a, b, c in I[sel[I].all(1)]:
        tt, yy, rr = th[[a, b, c]], P[[a, b, c], 1], r[[a, b, c]]
        if tt.max() - tt.min() > 90: continue   # (across the back)
        lo = np.maximum([int(np.floor((tt.min() - t0) / dt)), int(np.floor((yy.min() - y0) / dy))], 0); hi = np.minimum([int(np.ceil((tt.max() - t0) / dt)), int(np.ceil((yy.max() - y0) / dy))], [nt - 1, ny - 1])
        d = (yy[1] - yy[2]) * (tt[0] - tt[2]) + (tt[2] - tt[1]) * (yy[0] - yy[2])
        if (hi < lo).any() or abs(d) < 1e-12: continue
        gt, gy = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1), indexing='ij'); X = t0 + gt * dt; Y = y0 + gy * dy
        u = ((yy[1] - yy[2]) * (X - tt[2]) + (tt[2] - tt[1]) * (Y - yy[2])) / d; v = ((yy[2] - yy[0]) * (X - tt[2]) + (tt[0] - tt[2]) * (Y - yy[2])) / d; w = 1 - u - v
        rz = u * rr[0] + v * rr[1] + w * rr[2]; up = (u >= -.01) & (v >= -.01) & (w >= -.01) & (rz > R[gt, gy])
        R[gt[up], gy[up]] = rz[up]
    k = int(round(JAW_WIN / dy)); edge = np.full(nt, np.nan); ang = t0 + np.arange(nt) * dt
    with np.errstate(invalid='ignore'):
        for i in range(nt):   # from the top down: the first height whose surface steps in by JAW_STEP within JAW_WIN below it
            top = int(round((JAW_SCAN[0] - (JAW_SCAN[0] - JAW_NOSE[0]) * max(0., 1 - abs(ang[i]) / JAW_NOSE[1]) - y0) / dy))
            st = np.nonzero(R[i, k:top + 1] - R[i, :top + 1 - k] > JAW_STEP)[0]
            if not len(st) or st[-1] + k >= top: continue   # (none, or at the scan's top: higher up)
            j = st[-1] + k; w = R[i, j - k + 1:j + 1] - R[i, j - k:j]   # (that step's steepest mm)
            edge[i] = y0 + (j - k + 1 + int(np.nanargmax(w))) * dy
    prev, nxt = np.r_[np.nan, edge[:-1]], np.r_[edge[1:], np.nan]; gap = np.isnan(edge) & np.isfinite(prev) & np.isfinite(nxt)
    edge[gap] = (prev + nxt)[gap] / 2   # (a single missing angle)
    ok = np.isfinite(edge); ok[1:] &= ~(np.abs(np.diff(edge)) > JAW_JUMP); runs = np.split(np.nonzero(ok)[0], np.nonzero(np.diff(np.nonzero(ok)[0]) > 1)[0] + 1)
    run = next(q for q in runs if q[0] <= int(round(-t0 / dt)) <= q[-1])   # (the piece through the front)
    e = edge[run]; med = ndimage.median_filter(e, 5, mode='nearest'); good = np.abs(e - med) <= .004
    e = ndimage.gaussian_filter1d(np.interp(run, run[good], e[good]), 2., mode='nearest')
    a0, a1 = ang[run[0]], ang[run[-1]]
    heights = np.interp(np.arange(nt), run, e)   # (beyond the jaw: as at its ends)
    deep = JAW_DEEP[1] + (JAW_DEEP[0] - JAW_DEEP[1]) * np.clip(1 - np.abs(ang) / JAW_DEEP[2], 0, 1) ** 2
    deep *= np.clip((ang - a0) / JAW_TAPER, 0, 1) * np.clip((a1 - ang) / JAW_TAPER, 0, 1)
    print('jaw ring: the edge from %.0f to %.0f degrees, at %.3f..%.3f m (the chin %.3f)' % (a0, a1, e.min(), e.max(), heights[int(round(-t0 / dt))]))
    return heights, deep, (a0, a1)


def front_depth(P, I, x0, x1, y0, y1, g=.001):
    """The front view's depth (the largest z) of the mesh (positions P, triangles I) on a grid of g m over x0..x1,
    y0..y1: a function of (x, y) arrays (-inf where nothing is)."""
    nx, ny = int(round((x1 - x0) / g)) + 1, int(round((y1 - y0) / g)) + 1; Z = np.full((nx, ny), -np.inf); cent = P[I].mean(1)
    for k in np.nonzero((cent[:, 0] > x0 - .02) & (cent[:, 0] < x1 + .02) & (cent[:, 1] > y0 - .02) & (cent[:, 1] < y1 + .02))[0]:
        a, b, c = P[I[k]]
        lo = np.maximum(np.floor((np.minimum(np.minimum(a, b), c)[:2] - [x0, y0]) / g).astype(int), 0); hi = np.minimum(np.ceil((np.maximum(np.maximum(a, b), c)[:2] - [x0, y0]) / g).astype(int), [nx - 1, ny - 1])
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if (hi < lo).any() or abs(d) < 1e-14: continue
        gx, gy = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1), indexing='ij'); X = x0 + gx * g; Y = y0 + gy * g
        u = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d; v = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d; w = 1 - u - v
        zz = u * a[2] + v * b[2] + w * c[2]; up = (u >= -.01) & (v >= -.01) & (w >= -.01) & (zz > Z[gx, gy])
        Z[gx[up], gy[up]] = zz[up]
    return lambda x, y: Z[np.clip(np.round((x - x0) / g).astype(int), 0, nx - 1), np.clip(np.round((y - y0) / g).astype(int), 0, ny - 1)]


def face_depth(P, I, sel):
    """The face's and the neck's surface seen from the front (CFG.looks.ren.faceShape; e_model mdFaceMat lays the face
    decal per pixel where a point is on it: a per-vertex mask faded over whole triangles of Meshy's coarse mesh, 5-8 mm,
    half an eye; and on the surfaces hidden behind the chin the decal stretched the mouth's lines): its depth (the
    largest z) over FACE_ZONE on a grid of FACE_CELL m, from the triangles of sel only (face_and_neck: not the fringe's
    locks in front of the face, nor the collar), its holes filled from their nearest cell and smoothed. ([x0, y0, x1,
    y1], [z0, z1], nx, ny, uint8 bytes per cell: the depth 0..255 over z0..z1)."""
    from scipy import ndimage
    x0, x1, y0, y1 = FACE_X - FACE_ZONE[0] - .01, FACE_X + FACE_ZONE[0] + .01, FACE_ZONE[1][0] - .01, FACE_ZONE[1][1] + .01
    t = I[sel[I].all(1)]; zf = front_depth(P, t, x0, x1, y0, y1, FACE_CELL)
    nx, ny = int(round((x1 - x0) / FACE_CELL)) + 1, int(round((y1 - y0) / FACE_CELL)) + 1
    gx, gy = np.meshgrid(x0 + np.arange(nx) * FACE_CELL, y0 + np.arange(ny) * FACE_CELL, indexing='ij'); Z = zf(gx, gy)
    have = np.isfinite(Z); _, (ix, iy) = ndimage.distance_transform_edt(~have, return_indices=True); Z = ndimage.gaussian_filter(Z[ix, iy], 1.)
    z0, z1 = float(Z.min()) - .002, float(Z.max()) + .002
    print('face and neck depth %d x %d cells of %.0f mm, z %.3f..%.3f (%d%% from them, the rest filled)' % (nx, ny, FACE_CELL * 1000, z0, z1, 100 * have.mean()))
    return [round(x0, 5), round(y0, 5), round(x1, 5), round(y1, 5)], [round(z0, 5), round(z1, 5)], nx, ny, np.round((Z - z0) / (z1 - z0) * 255).astype(np.uint8).T.tobytes()


def face_region(Pw, Nw, T, E, whw, hairw, skinw):
    """The face on the welded mesh (positions Pw, normals Nw, triangles T, edges E; per welded vertex its weight on the
    head, whether it is hair-coloured and skin-coloured in Meshy's texture): the head's vertices in FACE_BOX but the hair
    mass (the big hair-coloured piece); of that mass, the brows, lashes and eye lines Meshy painted on the face's own
    surface (in the eyes' band, not in front of a smooth fit of the face's skin by 3 mm) are face (the eye sockets
    behind it too). The piece that holds the nose. (face, its border: the face's vertices next to the rest)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    nw = len(Pw); cc = lambda m: connected_components(coo_matrix((np.ones(int(m.sum())), (E[m, 0], E[m, 1])), shape=(nw, nw)), directed=False)[1]
    lab = cc(hairw[E[:, 0]] & hairw[E[:, 1]]); ids, cnt = np.unique(lab[hairw], return_counts=True); mass = hairw & (lab == ids[np.argmax(cnt)])
    box = (whw > .5) & (np.abs(Pw[:, 0] - FACE_X) < FACE_BOX[0]) & (Pw[:, 1] > FACE_BOX[1][0]) & (Pw[:, 1] < FACE_BOX[1][1]) & (Pw[:, 2] > FACE_BOX[2])
    X = lambda p: np.stack([np.ones(len(p)), p[:, 0] - FACE_X, p[:, 1] - 1.58, (p[:, 0] - FACE_X) ** 2, (p[:, 1] - 1.58) ** 2, (p[:, 0] - FACE_X) * (p[:, 1] - 1.58),
                            (p[:, 0] - FACE_X) ** 2 * (p[:, 1] - 1.58), (p[:, 1] - 1.58) ** 3], 1)
    fr = box & skinw & (Nw[:, 2] > .3) & (Pw[:, 1] > 1.53) & (Pw[:, 1] < 1.64); use = fr
    for _ in range(5):
        c = np.linalg.lstsq(X(Pw[use]), Pw[use, 2], rcond=None)[0]; res = Pw[:, 2] - X(Pw) @ c; use = fr & (np.abs(res) < .005)
    painted = mass & (np.abs(Pw[:, 0] - FACE_X) < .048) & (Pw[:, 1] > 1.55) & (Pw[:, 1] < 1.622) & (res < .003)
    face = box & (~mass | painted)
    lab = cc(face[E[:, 0]] & face[E[:, 1]]); nose = np.argmin(np.where(face, np.hypot(Pw[:, 0] - FACE_X, Pw[:, 1] - 1.55), 9))
    face &= lab == lab[nose]
    out = np.zeros(nw, bool); a, b = E[:, 0], E[:, 1]; out[a[face[a] & ~face[b]]] = True; out[b[face[b] & ~face[a]]] = True
    return face, face & out


def drawn_shape(P, N, I, wh, col):
    """The shape as drawn (NOSE_*, FRINGE_*, COLLAR_*): (positions, normals, indices of the vertices that changed). P, N:
    the mesh's bind positions and normals; wh: each vertex's weight on the head; col: the texture's colour at each vertex
    (Meshy's: the hair dark, the vest teal). The copies of a vertex along the texture's seams move together; the vertices
    of the triangles around a moved one turn their normal as their surface turns (Meshy's own smoothing kept)."""
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel()
    Q = P.copy()
    X = lambda p: np.stack([np.ones(len(p)), p[:, 0] - FACE_X, p[:, 1] - 1.54, (p[:, 0] - FACE_X) ** 2, (p[:, 1] - 1.54) ** 2, (p[:, 0] - FACE_X) * (p[:, 1] - 1.54)], 1)
    low = (wh > .5) & (np.abs(P[:, 0] - FACE_X) < .045) & (P[:, 1] > 1.495) & (P[:, 1] < 1.58) & (P[:, 2] > -.02); use = low
    for _ in range(6):   # the fit again on the points near it (not the ridge, the slit, the jaw's underside)
        c = np.linalg.lstsq(X(P[use]), P[use, 2], rcond=None)[0]; r = P[:, 2] - X(P) @ c; use = low & (r > -.004) & (r < .006)
    zb = X(P) @ c
    def box(half, y0, y1):   # vertices in the box, and how far inside (0 at its edges, 1 from NOSE_FADE in)
        e = np.minimum(np.minimum(P[:, 0] - FACE_X + half, FACE_X + half - P[:, 0]), np.minimum(P[:, 1] - y0, y1 - P[:, 1]))
        return (wh > .5) & (e > 0), np.clip(e / NOSE_FADE, 0, 1)
    y, n = P[:, 1], NOSE
    h = np.where(y >= n['tip'], n['h'] * np.clip((n['root'] - y) / (n['root'] - n['tip']), 0, 1) ** 1.3, n['h'] * np.clip(1 - ((n['tip'] - y) / (n['tip'] - n['end'])) ** 2, 0, 1))
    w = n['w'][0] + (n['w'][1] - n['w'][0]) * np.clip((n['root'] - y) / (n['root'] - n['end']), 0, 1)
    nb, en = box(NOSE_BOX[0], *NOSE_BOX[1]); nose = nb & (P[:, 2] > zb - .03)
    Q[nose, 2] = P[nose, 2] * (1 - en[nose]) + zb[nose] * en[nose]   # (flat: the small nose goes on after the smoothing)
    mb, em = box(MOUTH_BOX[0], *MOUTH_BOX[1]); mouth = mb & ~nb & (P[:, 2] > zb - .06) & (P[:, 2] < zb - .001)
    Q[mouth, 2] = P[mouth, 2] * (1 - em[mouth]) + (zb[mouth] - .001) * em[mouth]
    hair = (wh > .5) & (col.mean(1) < 115) & ~(col[:, 1] > col[:, 0] + 8)
    cut = FRINGE_CUT[0] - (FRINGE_CUT[0] - FRINGE_CUT[1]) * np.clip(1 - np.abs(P[:, 0] - FRINGE_X) / FRINGE_CUT[2], 0, 1) ** 2
    fr = hair & (np.abs(P[:, 0] - FRINGE_X) < .07) & (P[:, 1] < cut + .02) & (P[:, 1] > cut - .06) & (P[:, 2] > FRINGE_FACE + FRINGE_Z)
    Q[fr, 1] = np.where(P[fr, 1] < cut[fr], cut[fr] - (cut[fr] - P[fr, 1]) * FRINGE_KEEP, P[fr, 1])
    Q[fr, 2] = P[fr, 2] - (P[fr, 2] - FRINGE_FACE) * FRINGE_BACK * np.clip((cut[fr] + .02 - P[fr, 1]) / .02, 0, 1)
    mv = nose | mouth | fr; Qw = np.zeros((len(first), 3)); Qw[weld[~mv]] = P[~mv]; Qw[weld[mv]] = Q[mv]   # (the moved copy wins)
    teal = (col[:, 1] > col[:, 0] + 10) & (col[:, 2] > col[:, 0] + 10); light = (col.min(1) > 125) & (col.max(1) - col.min(1) < 45)
    collar = np.zeros(len(first), bool); np.logical_or.at(collar, weld, (teal | light) & (P[:, 1] > 1.42) & (P[:, 1] < 1.56) & (np.abs(P[:, 0]) < .2))
    for side in (-1, 1):
        c = np.nonzero(collar & (np.sign(Qw[:, 0]) == side) & (Qw[:, 2] > -.04) & (Qw[:, 2] < .03))[0]
        tip = Qw[c[np.argmax(Qw[c, 1] + .3 * np.abs(Qw[c, 0]))]]
        w = np.clip(1 - np.linalg.norm(Qw - tip, axis=1) / COLLAR_R, 0, 1) ** 2 * collar
        Qw = Qw + np.outer(w, [side * COLLAR_TIP[0], COLLAR_TIP[1], 0])
    # the face smoothed (its border kept), the small nose on it
    nw = len(first); T = weld[I]; E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    per = lambda m: np.bincount(weld, m.astype(float), nw) / np.bincount(weld, minlength=nw) > .5
    whw = np.zeros(nw); np.maximum.at(whw, weld, wh)
    skinc = (col[:, 0] > 120) & (col[:, 1] > 75) & (col[:, 0] - col[:, 2] > 40)
    def area_normals(p):
        fn = np.cross(p[T[:, 1]] - p[T[:, 0]], p[T[:, 2]] - p[T[:, 0]]); acc = np.zeros((nw, 3))
        for c in range(3): np.add.at(acc, T[:, c], fn)
        return acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    face, border = face_region(Qw, area_normals(Qw), T, E, whw, per(hair | (col.mean(1) < 115) & ~teal) & (whw > .3), per(skinc))
    free = face & ~border
    from scipy.sparse import csr_matrix
    A = csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)); deg = np.asarray(A.sum(1)).ravel()
    before = Qw.copy()
    for _ in range(FACE_SMOOTH):
        for lam in (.5, -.53):   # Taubin: a step in, a step out (no shrinking)
            Qw[free] += lam * ((A @ Qw) / deg[:, None] - Qw)[free]
    y = Qw[:, 1]
    h = np.where(y >= n['tip'], n['h'] * np.clip((n['root'] - y) / (n['root'] - n['tip']), 0, 1) ** 1.3, n['h'] * np.clip(1 - ((n['tip'] - y) / (n['tip'] - n['end'])) ** 2, 0, 1))
    w = n['w'][0] + (n['w'][1] - n['w'][0]) * np.clip((n['root'] - y) / (n['root'] - n['end']), 0, 1)
    Qw[free, 2] += (h * np.clip(1 - ((Qw[:, 0] - FACE_X) / w) ** 2, 0, 1) ** 2)[free]
    smooth_d = np.linalg.norm(Qw - before, axis=1)[free]
    moved = np.abs(Qw - P[first]).sum(1) > 1e-9; Q = Qw[weld]
    aff = np.zeros(nw, bool); aff[T[moved[T].any(1)].ravel()] = True
    n0, n1 = area_normals(P[first]), area_normals(Qw); Nn = N.copy()
    for v in np.nonzero((face & ~border)[weld])[0]: Nn[v] = n1[weld[v]]   # the face's: the smooth surface's
    for v in np.nonzero((aff & ~(face & ~border))[weld])[0]:   # the others: each normal turned as its vertex's surface turned
        a, b = n0[weld[v]], n1[weld[v]]; c = np.cross(a, b); s = np.linalg.norm(c)
        if s < 1e-9: continue
        K = np.array([[0, -c[2], c[1]], [c[2], 0, -c[0]], [-c[1], c[0], 0]]) / s; ang = np.arctan2(s, float(a @ b))
        Nn[v] = (np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K) @ N[v]
    eyes = fr & (np.abs(P[:, 0] - FRINGE_X) > FRINGE_CUT[2])
    print('drawn shape: the face %d vertices smoothed (%d on its border kept; moved %.4f m on average, %.4f at most); nose %d vertices (out of the face up to %.3f -> %.3f m), mouth %d (up to %.3f m in -> filled), fringe %d (lowest in the eyes\' columns %.3f -> %.3f m), collar %d' % (
        int(free.sum()), int(border.sum()), smooth_d.mean(), smooth_d.max(), int(nose.sum()), (P[nose, 2] - zb[nose]).max(), n['h'], int(mouth.sum()),
        (zb[mouth] - P[mouth, 2]).max(), int(fr.sum()), P[eyes, 1].min(), Q[eyes, 1].min(), int((moved & collar).sum())))
    return Q, Nn, np.nonzero(moved[weld] | aff[weld])[0], face[weld]


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


def tail_stubs(P, col, I, tails):
    """The tails' tops (9/11/2026, Denis: "rimuovi le parti rimanenti della fascia vecchia"): the triangles in Meshy's
    orange between SASH_BAND - TAILS_STUB[0] m and TAILS_STUB[1] m (under the band's bottom edge), within TAILS_STUB[2] m of
    the tails (tails: their vertices, sash_tails): hidden with them (tools/ren_head.py), their torn ends hung from the band
    beside the look's ribbons; the vest is whole under them. col: the texture's colour at each vertex."""
    from scipy.spatial import cKDTree
    oc = col[I].mean(1); C = P[I].mean(1)
    orange = (oc[:, 0] > 170) & (oc[:, 1] > 70) & (oc[:, 1] < 170) & (oc[:, 2] < 90) & (oc[:, 0] - oc[:, 1] > 50)
    cand = np.nonzero(orange & (C[:, 1] > SASH_BAND - TAILS_STUB[0]) & (C[:, 1] < TAILS_STUB[1]))[0]
    if not len(cand) or not tails.any(): return cand[:0]
    return cand[cKDTree(P[tails]).query(C[cand])[0] < TAILS_STUB[2]]


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


def drawing_band(D):
    """The drawing's band: its first and last row (from its top while at least 45% as orange as its most orange row, the
    tails below are less, over gaps of up to 3 rows: the dark line between its two wraps)."""
    cnt = sash_orange(D).sum(1); r0 = int(np.argmax(cnt > .3 * cnt.max())); r1 = r0
    while any(r1 + k < len(cnt) and cnt[r1 + k] >= .45 * cnt.max() for k in (1, 2, 3, 4)):
        r1 += next(k for k in (1, 2, 3, 4) if cnt[r1 + k] >= .45 * cnt.max())
    return r0, r1


def drawing_fit(P, mask):
    """The front projection of the model (bind pose, P) on the drawing: the scale (px/m) and the drawing's point (cx, by)
    of the model's x = 0, y = 0 that put the most vertices inside the drawn silhouette (mask). (share inside, s, cx, by)."""
    ys, xs = np.nonzero(mask); feet, top, mid = ys.max(), ys.min(), (xs.min() + xs.max()) / 2
    s0 = (feet - top) / (P[:, 1].max() - P[:, 1].min()); best = None; H, Wd = mask.shape
    for ds in (-.02, -.01, 0, .01, .02):
        for dx in (-8, -4, 0, 4, 8):
            for dy in (-8, -4, 0, 4, 8):
                s = s0 * (1 + ds); u, v = mid + dx + P[:, 0] * s, feet + dy - P[:, 1] * s
                score = mask[np.clip(v.round().astype(int), 0, H - 1), np.clip(u.round().astype(int), 0, Wd - 1)].mean()
                if best is None or score > best[0]: best = (score, s, mid + dx, feet + dy)
    return best


def drawing_tails(D, cx):
    """The sash's two hanging tails in the drawing (front view), the left one first: its orange under the band
    (drawing_band) on each side of cx, in pieces of at least SASH_PIECE px. Per tail {top: (x, y) px, the middle of its
    first row; tip: its lowest pixel; wp: its width (px) across it (square to top-tip), each row from the top to its
    widest (9 rows' median), where the tip's slanted cut starts; cut: the share of its length that cut takes; c: its
    colour}."""
    from scipy import ndimage
    below = sash_orange(D); below[:drawing_band(D)[1] + 3] = False
    lab, n = ndimage.label(below); sizes = ndimage.sum(below, lab, range(1, n + 1)); out = []
    for side in (-1, 1):
        ids = [k + 1 for k in range(n) if sizes[k] >= SASH_PIECE and np.sign(np.nonzero(lab == k + 1)[1].mean() - cx) == side]
        ys, xs = np.nonzero(np.isin(lab, ids)); t0, t1 = int(ys.min()), int(ys.max())
        top, tip = (float(xs[ys == t0].mean()), float(t0)), (float(xs[ys == t1].mean()), float(t1))
        cos = (t1 - t0) / np.hypot(tip[0] - top[0], t1 - t0)
        w = ndimage.median_filter(np.array([np.ptp(xs[ys == y]) + 1 if (ys == y).any() else 0 for y in range(t0, t1 + 1)]) * cos, 9)
        peak = int(np.argmax(w))
        out.append({'top': top, 'tip': tip, 'wp': [float(x) for x in w[:peak + 1]], 'cut': 1 - peak / (t1 - t0), 'c': [int(v) for v in np.median(D[ys, xs], 0)]})
    return out


def ribbon_of(t, P, sc, cx, by, mid, y0):
    """A hanging ribbon for drawing tail t, in model space: {j: SASH_SEG + 1 points: under the band (SASH_TUCK m behind
    its front at the height mid), at its lower edge y0 where it comes out (its front face SASH_OUT m out of the body),
    then evenly down to the drawing's tip (front view), in front of the body (SASH_GAP from 10 cm under the band); fix:
    how many from the top move with the body (those two, and those SASH_FIX m under the band); tuck: m of it under the
    band; wp: its width (m) at each point, the drawing's; w: its widest; cut: the share of its length its tip's slanted
    cut takes; out: the side of a (1 or -1) away from the middle (that edge runs to the tip, the inner one is cut); a:
    unit across; n: unit out of its face (forward); c: colour}."""
    def front(x, y):
        near = P[(np.abs(P[:, 0] - x) < .02) & (np.abs(P[:, 1] - y) < .012)]
        return float(near[:, 2].max()) if len(near) else 0.
    x0, x1, y1 = (t['top'][0] - cx) / sc, (t['tip'][0] - cx) / sc, (by - t['tip'][1]) / sc
    path = []
    for u in np.linspace(0, 1, 24):
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u; f = min(1., (y0 - y) / .1)
        path.append([x, y, front(x, y) + (SASH_OUT - SASH_TH / 2) * (1 - f) + SASH_GAP * f])
    path = np.array(path); arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    at = np.linspace(0, arc[-1], SASH_SEG); top = [x0, mid, front(x0, mid) - SASH_TUCK]
    j = np.vstack([top, np.array([np.interp(at, arc, path[:, k]) for k in range(3)]).T])
    wp = np.array(t['wp']); w = np.clip(np.r_[wp[0], wp[np.minimum((at / arc[-1] * (t['tip'][1] - t['top'][1])).astype(int), len(wp) - 1)]] / sc, *SASH_W)
    d = unit(j[-1] - j[1]); a = unit(np.cross(d, [0, 0, 1.])); n = unit(np.cross(a, d))
    if n[2] < 0: n, a = -n, -a
    return {'j': j, 'fix': 1 + int((at <= SASH_FIX + 1e-9).sum()), 'tuck': float(np.linalg.norm(j[1] - j[0])), 'wp': w, 'w': float(w.max()),
            'cut': float(t['cut']), 'out': 1 if a[0] * x0 > 0 else -1, 'a': a, 'n': n, 'c': t['c']}


def smooth_normals(P, I, keep_w):
    """Per vertex the normal of the welded surface smoothed (see NOR_ITER); keep_w (per vertex, 0-1): how much of its
    normal smoothed HAND_NOR_ITER rounds it keeps instead (the hands)."""
    from scipy.sparse import coo_matrix
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld = weld.ravel(); nw = len(first)
    T = weld[I]; fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])   # (area-weighted)
    Nw = np.zeros((nw, 3))
    for k in range(3): np.add.at(Nw, T[:, k], fn)
    Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12)
    E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    A = coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(nw, nw)).tocsr()
    deg = np.maximum(np.asarray(A.sum(1)).ravel(), 1)
    own = Nw.copy(); S = Nw.copy()
    for k in range(max(NOR_ITER, HAND_NOR_ITER)):
        if k == HAND_NOR_ITER: own = S.copy()   # (the hands' normals: HAND_NOR_ITER rounds; unsmoothed, the toon light's
        S = .5 * S + .5 * (A @ S) / deg[:, None]; S /= np.maximum(np.linalg.norm(S, axis=1, keepdims=True), 1e-12)   # bands on the fists were blocks)
    kw = np.zeros(nw); np.maximum.at(kw, weld, keep_w)
    out = S * (1 - kw)[:, None] + own * kw[:, None]; out /= np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)
    return out[weld].astype(np.float32)


def sash_band(P, col):
    """The band's heights (m): (bottom, top), where the sash's orange (col: Meshy's texture at each vertex) goes around
    the waist (200 degrees and more of it, in 15 degree sectors, per cm)."""
    ring = []
    for y0 in np.arange(.9, 1.3, .01):
        sel = (col[:, 0] > 170) & (col[:, 0] - col[:, 1] > 50) & (col[:, 2] < 90) & (P[:, 1] >= y0) & (P[:, 1] < y0 + .01) & (np.abs(P[:, 0]) < .3)
        if sel.any() and len(np.unique((np.degrees(np.arctan2(P[sel, 0], P[sel, 2])) % 360 // 15).astype(int))) * 15 >= 200: ring.append(y0 + .005)
    return min(ring) - .005, max(ring) + .005


def band_on_hips(P, J, W, idx, band):
    """The skin J, W (n x 4: bones, weights) with the band's back on the Hips (see BAND_*; band: its heights, sash_band): new J
    (int64) and W (float64), 4 bones a vertex summing to 1."""
    J = np.asarray(J).astype(np.int64).copy(); W = np.asarray(W).astype(np.float64).copy()
    trunk = (np.isin(J, [idx[b] for b in ('Hips', 'Spine02', 'Spine01', 'Spine', 'LeftUpLeg', 'RightUpLeg')]) * W).sum(1)
    y = P[:, 1]; s = smooth(band[0] - BAND_T, band[0], y) * (1 - smooth(band[1], band[1] + BAND_T, y)) * smooth(BAND_TRUNK[0], BAND_TRUNK[1], trunk) * (np.abs(P[:, 0]) < .3) * (1 - smooth(BAND_Z[0], BAND_Z[1], P[:, 2]))
    ch = np.nonzero(s > 0)[0]
    if not len(ch): return J, W
    Wd = np.zeros((len(ch), max(int(J.max()) + 1, len(idx))))
    for k in range(4): np.add.at(Wd, (np.arange(len(ch)), J[ch, k]), W[ch, k])
    Wd *= (1 - s[ch])[:, None]; Wd[:, idx['Hips']] += s[ch]
    top = np.argsort(-Wd, 1, kind='stable')[:, :4]; tw = np.take_along_axis(Wd, top, 1)
    J[ch] = top; W[ch] = tw / tw.sum(1, keepdims=True)
    return J, W


def skin_near(p, P, ok, J, W):
    """The skin of the body's front at p (model space): the bones and weights (up to 4, summing to 1) of the SASH_SKIN
    vertices ok (the front of the trunk and the legs) nearest to p seen from the front (x, y), of those at most 6 cm
    behind it, the nearer counting more."""
    near = np.nonzero(ok & (P[:, 2] > p[2] - .06))[0]
    d = np.hypot(P[near, 0] - p[0], P[near, 1] - p[1]); o = np.argsort(d)[:SASH_SKIN]; acc = {}
    for v, dv in zip(near[o], d[o]):
        for b, w in zip(J[v], W[v]):
            if w > 0: acc[int(b)] = acc.get(int(b), 0) + float(w) / float(dv + .005)
    top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(w for _, w in top)
    return [[b, round(w / tot, 4)] for b, w in top]


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
    # --- the shape as drawn (drawn_shape): all below is measured on it ---
    N = f(me['nor']).reshape(-1, 3).astype(np.float64); UV = f(me['uv']).reshape(-1, 2)
    tex = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(int); ts = tex.shape[0]
    col = tex[np.clip((UV[:, 1] * ts).astype(int), 0, ts - 1), np.clip((UV[:, 0] * ts).astype(int), 0, ts - 1)]
    P, N, moved, face_mask = drawn_shape(P, N, I, ((J == idx['Head']) * W).sum(1), col)
    # --- the fingers: the mesh welded across its texture seams, then each hand's fingers on it ---
    _, first, weld = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True)
    weld = weld.ravel(); T = weld[I]
    E = np.unique(np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1), axis=0)
    jn, wn = J.astype(np.int64).copy(), W.astype(np.float64).copy(); fingers = []; palms = []; thumb_root = np.zeros(len(P)); on_finger = np.zeros(len(P))
    for side in ('Left', 'Right'):
        hi = idx[side + 'Hand']; w = ((J == hi) * W).sum(1); Gi = G[hi]; inv = np.linalg.inv(Gi)
        L = P @ inv[:3, :3].T + inv[:3, 3]
        l, n, thumb = hand_frame(L[w >= HAND_W], w[w >= HAND_W], Gi[:3, :3])
        palms.append((w, Gi[:3, :3] @ n))   # the side the palm faces, in the model
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
        # the thumb's root: the palm's share on the thumb's first bone spread over its neighbours (THUMB_SMOOTH rounds of
        # their mean; the thumb's own vertices and those off the hand stay): turned some 55 degrees in the fist, the palm's
        # piece that went with it whole stood out of the thumb's side of the fist as a flat fin with a sharp corner (10/11,
        # Denis: "lo spigolo che ti avevo cerchiato ... rende le mani innaturali"); spread, that side bends round. The
        # outline keeps its rules on the weights as they were (LINE_THUMB, LINE_FINGER)
        t1 = base; vv = np.nonzero(w >= HAND_W)[0]
        thumb_root[vv] = (wn[vv] * np.isin(jn[vv], [base, base + 1, base + 2])).sum(1); on_finger[vv] = (wn[vv] * (jn[vv] >= len(bones))).sum(1)
        share = np.zeros(len(first)); cnt = np.zeros(len(first)); np.add.at(share, weld[vv], (wn[vv] * (jn[vv] == t1)).sum(1)); np.add.at(cnt, weld[vv], 1)
        share[cnt > 0] /= cnt[cnt > 0]
        free_ = ins & (lab != fg[0]['k']); fu = np.nonzero(free_)[0]
        for _ in range(THUMB_SMOOTH):
            new = share.copy()
            for u in fu:
                if nb[u]: new[u] = .5 * share[u] + .5 * np.mean([share[x] for x, _ in nb[u]])
            share = new
        nch = 0
        for v in vv:
            if not free_[weld[v]]: continue
            d_ = share[weld[v]] - (wn[v] * (jn[v] == t1)).sum()
            if abs(d_) < 1e-4: continue
            inf = {int(a): float(b) for a, b in zip(jn[v], wn[v]) if b > 0}
            inf[t1] = inf.get(t1, 0) + d_; inf[hi] = inf.get(hi, 0) - d_
            inf = {a: max(b, 0.) for a, b in inf.items() if b > 1e-5}
            top = sorted(inf.items(), key=lambda kv: -kv[1])[:4]; tot = sum(b for _, b in top)
            jn[v] = [a for a, _ in top] + [0] * (4 - len(top)); wn[v] = [b / tot for _, b in top] + [0] * (4 - len(top)); nch += 1
        print(side, 'hand: the thumb\'s root spread over', nch, 'palm vertices')
        print(side, 'hand: thumb side', thumb, 'fingers', [int((lab == F['k']).sum()) for F in fg], 'vertices on them')
    if len(bones) + len(fingers) > 255: sys.exit('too many bones for uint8 skin indices')
    # --- the band's back on the hips (band_on_hips): it no longer stretches when the thighs and the spine bend ---
    band = sash_band(P, col); jn, wn = band_on_hips(P, jn, wn, idx, band)
    print('the band\'s back on the hips: from %.2f to %.2f m, blending over %.0f cm' % (band[0], band[1], 100 * BAND_T))
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
    b0, b1 = sash_band(P, col0); mid, y0 = (b0 + b1) / 2, b0   # the band: the heights where the sash's orange goes all around the waist
    # placed as tools/paint_from_drawing.py paints the drawing (its band, with the tails' tops, on the model's band)
    from scipy import ndimage
    fit = drawing_fit(P, ndimage.binary_opening(mask, iterations=1)); Nv = f(me['nor']).reshape(-1, 3).astype(np.float64)
    trunk = np.isin(J, [idx[b] for b in set(BODY) | set(BODY.values()) | {'LeftFoot', 'RightFoot'}])
    front_ok = ((trunk * W).sum(1) >= .9) & (Nv[:, 2] > .2)   # the front of the trunk and the legs (not the arms)
    for t in drawing_tails(D, fit[2]):
        r = ribbon_of(t, P, fit[1], fit[2], fit[3], mid, y0)
        ribbons.append({'j': [[round(float(v), 5) for v in ih[:3, :3] @ q + ih[:3, 3]] for q in r['j']], 'w': round(r['w'], 4), 'wp': [round(float(v), 4) for v in r['wp']],
                        'fix': r['fix'], 'tuck': round(r['tuck'], 4), 'cut': round(r['cut'], 3), 'out': r['out'], 'sk': [skin_near(q, P, front_ok, J, W) for k, q in enumerate(r['j']) if k < r['fix'] or y0 - q[1] <= SASH_LIE + 1e-9],
                        'a': [round(float(v), 5) for v in ih[:3, :3] @ r['a']], 'n': [round(float(v), 5) for v in ih[:3, :3] @ r['n']], 'c': r['c']})
        print('ribbon from x %.3f (y %.3f) to the tip (%.3f, %.3f), widths %s, cut %.2f, fixed %d, its top on the skin of %s' % (r['j'][1][0], y0, r['j'][-1][0], r['j'][-1][1],
              np.round(r['wp'], 3).tolist(), r['cut'], r['fix'], [[(bones[b]['n'], w) for b, w in s] for s in ribbons[-1]['sk']]))
    print('sash band from %.2f to %.2f m (the drawing fit: %s)' % (y0, b1, np.round(fit, 3).tolist()))
    r0, r1 = drawing_band(D); od = sash_orange(D)
    for r in ribbons: r['c'] = [int(v) for v in np.median(D[r0:r1 + 1][od[r0:r1 + 1]], 0)]   # the band's orange, as painted
    body = [body_shape(P, J, W, G, idx, b, c) for b, c in BODY.items()]
    Wb = np.stack([((J == idx[b]) * W).sum(1) for b in BODY], 1); second = np.sort(Wb, 1)[:, -2]
    shared = (second >= BLEND_W) & (Wb.sum(1) >= .9) & (P[:, 1] > BLEND_Y[0]) & (P[:, 1] < BLEND_Y[1])
    _, one = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True)   # one copy of each seam's vertices
    cand = one[shared[one]]
    blend = np.sort(cand[np.unique(np.floor(P[cand] / BLEND_D).astype(np.int64), axis=0, return_index=True)[1]]).astype(np.uint16)
    print('sash ribbons', [(len(r['j']), r['w']) for r in ribbons], 'body shapes', [(x['b'], round(float(np.max(x['r'])), 3)) for x in body], 'shared points', len(blend))
    # --- the outline on the face: thin where the head faces forward and the texture is skin ---
    skin = (col[:, 0] > 150) & (col[:, 1] > 95) & (col[:, 0] - col[:, 2] > 50)
    face = (wh >= .5) & (N[:, 2] > .15) & skin
    line = np.ones(len(P), np.float32); line[face] = LINE_FACE
    on = on_finger; line = np.minimum(line, 1 - (1 - LINE_FINGER) * on).astype(np.float32)
    tw = thumb_root; web = (tw > LINE_THUMB[0]) & (tw < LINE_THUMB[1]); line[web] = 0
    inner = np.zeros(len(P), bool)
    for w, pn in palms: inner |= (w + on > .5) & (N @ pn > LINE_PALM)
    line[inner] = 0
    # (and on the hands, the outline's width no more than the distance over the mesh to where it is none (the thumb's
    # root, the palm) over LINE_RAMP: a full width beside none tilted the outline's shell out through the thumb's side of
    # the fist, a black flag)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    hw_ = sum(((J == idx[s_ + 'Hand']) * W).sum(1) for s_ in ('Left', 'Right')); nw_ = len(first)
    hwm = np.zeros(nw_); np.maximum.at(hwm, weld, hw_); lwm = np.full(nw_, 9.); np.minimum.at(lwm, weld, line)
    z_ = np.nonzero((lwm < .01) & (hwm > .3))[0]; Le = np.linalg.norm(P[first][E[:, 0]] - P[first][E[:, 1]], axis=1)
    G_ = coo_matrix((np.r_[Le, Le, np.full(len(z_), 1e-9)], (np.r_[E[:, 0], E[:, 1], np.full(len(z_), nw_)], np.r_[E[:, 1], E[:, 0], z_])), shape=(nw_ + 1, nw_ + 1)).tocsr()
    cap = np.where(hwm > .3, np.clip(dijkstra(G_, indices=nw_)[:nw_] / LINE_RAMP, 0, 1), 1.)
    ramped = int((cap[weld] < line - 1e-4).sum()); line = np.minimum(line, cap[weld]).astype(np.float32)
    print('outline thinned on', int(face.sum()), 'face and', int((on > 0).sum()), 'finger vertices; none on', int(web.sum()), 'of the thumbs\' roots and', int(inner.sum()), 'of the hands\' inner side;', ramped, 'ramped to them')
    flat = np.maximum(smooth(.05, .45, N[:, 2]) * smooth(.3, .7, wh), FLAT_BODY * smooth(.1, .45, N[:, 2]))
    # the middle of the face all flat (the nose's sides and underside too: the drawn nose has its shadow in the face
    # decal; the toon light's bands on its few facets read as a pink and a brown patch), and no outline on the nose
    mid = (wh > .5) & (np.abs(P[:, 0] - FACE_X) < FACE_FLAT) & (P[:, 1] > FACE_ZONE[1][0]) & (P[:, 1] < FACE_ZONE[1][1]) & (P[:, 2] > -.01)
    flat = np.maximum(flat, mid * smooth(-.2, .1, N[:, 2]))
    whn = wh + ((J == idx['neck']) * W).sum(1); hs = head_skin(P, I, col, whn)
    skc = (col[:, 0] > 120) & (col[:, 1] > 75) & (col[:, 0] - col[:, 2] > 40)
    flat = np.maximum(flat, np.maximum(hs * smooth(.3, .7, whn), skc & neck_zone(P)))   # the head's and the neck's skin all flat
    # the white wraps (forearms, ankles) all flat too (Denis, 8/11: "niente cose strane"): the toon light's bands on them,
    # along Meshy's facets, were grey blocks; the drawing's wraps are white with thin lines (WRAP_*: Meshy's colour there)
    wraps = (col.min(1) > WRAP_LIGHT) & (col.max(1) - col.min(1) < WRAP_GREY) & (wh < .5)
    fw = ((J == idx['LeftForeArm']) * W).sum(1) + ((J == idx['RightForeArm']) * W).sum(1)
    wraps |= (fw > .5) & (col.max(1) - col.min(1) < 40) & (col.mean(1) > 95)   # (and Meshy's grey shading on the forearms' wraps)
    _, first_, weld_ = np.unique(np.round(P / 1e-6).astype(np.int64), axis=0, return_index=True, return_inverse=True); weld_ = weld_.ravel()
    ww = np.zeros(len(first_), bool); np.logical_or.at(ww, weld_, wraps); T_ = weld_[I]
    ring = np.zeros(len(first_), bool); ring[T_[ww[T_].sum(1) >= 2].ravel()] = True   # (one ring more, where most of a triangle is wrap)
    wraps = (ww | ring)[weld_] & ((col.max(1) - col.min(1) < 60) | (col.mean(1) < 70)) & (wh < .5)   # (not the skin beside them)
    flat = np.maximum(flat, wraps.astype(float)).astype(np.float32)
    print('flat light on the wraps: %d vertices' % int(wraps.sum()))
    nose = (wh > .5) & (np.abs(P[:, 0] - FACE_X) < NOSE_BOX[0]) & (P[:, 1] > NOSE_BOX[1][0]) & (P[:, 1] < NOSE_BOX[1][1]); line[nose] = 0
    print('flat light on', int((flat > .5).sum()), 'vertices (head', int(((flat > .5) & (wh > .5)).sum()), ')')
    blob = line.tobytes(); oj = len(blob); blob += jn.astype(np.uint8).tobytes(); ow = len(blob); blob += wn.astype(np.float32).tobytes()
    of = len(blob); blob += flat.tobytes(); op = len(blob); blob += P[moved].astype(np.float32).tobytes(); on = len(blob); blob += N[moved].astype(np.float32).tobytes()
    ob = len(blob); blob += blend.tobytes(); om = len(blob); blob += moved.astype(np.uint16).tobytes()
    handw = sum(((J == idx[s_ + 'Hand']) * W).sum(1) for s_ in ('Left', 'Right'))
    nsm = smooth_normals(P, I, np.clip(handw / .5, 0, 1)); blob += b'\0' * (-len(blob) % 4); onor = len(blob); blob += nsm.tobytes()   # (float32: 4-aligned)
    print('normals smoothed for the light: %d vertices (%d rounds; the hands %d)' % (len(nsm), NOR_ITER, HAND_NOR_ITER))
    fn = face_and_neck(face_mask, hs, col, P)
    dbox, dz, dnx, dny, ddata = face_depth(P, I, fn)
    odm = len(blob); blob += ddata
    jh, jd, _ = jaw_ring(P, I, fn)
    ojr = len(blob); blob += np.stack([np.round((jh - JAW_SCAN[1]) / (JAW_SCAN[0] - JAW_SCAN[1]) * 255), np.round(jd / JAW_DEEP[0] * 255)], 1).astype(np.uint8).tobytes()
    look = {'v': 3, 'fingers': fingers, 'skin': [[oj, int(jn.size)], [ow, int(wn.size)]], 'line': [0, int(line.size)], 'nor': [onor, int(nsm.size)],
            'flat': [of, int(flat.size)], 'spikes': spikes, 'sash': {'ribbons': ribbons, 'body': body, 'blend': [ob, int(blend.size)]},
            'move': {'idx': [om, len(moved)], 'pos': [op, 3 * len(moved)], 'nor': [on, 3 * len(moved)]},
            'face': {'fit': [round(float(v), 5) for v in fit[1:]], 'decal': list(FACE_DECAL), 'front': list(FACE_FRONT), 'seen': FACE_SEEN,
                     'depth': {'box': dbox, 'z': dz, 'n': [dnx, dny], 'map': [odm, len(ddata)]}, 'shade': [round(v, 4) for v in JAW_SHADE],
                     'jaw': {'axis': [round(v, 5) for v in JAW_AXIS], 'th': list(JAW_TH), 'y': [JAW_SCAN[1], JAW_SCAN[0]], 'deep': JAW_DEEP[0], 'up': JAW_UP,
                             'map': [ojr, 2 * JAW_TH[2]]}}}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(out, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look', len(blob), 'B,', len(fingers), 'finger bones')


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
