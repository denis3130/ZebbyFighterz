"""Kael's head in the flat colours of Denis's drawings (11/11: "senza sfumature o sovrapposizioni tra le cose").

The head's texture is painted from six drawings projected on a shape that is not theirs: where two of them meet they
were cross-faded, each brings its soft edges, and what faces a drawing at a slant takes it stretched. The drawings
themselves are cel art: a few flat colours with black lines over them, every border a step. flatten() gives the
texture back that look, on the surface (not in the atlas: Meshy's islands are small and scattered), as two layers:

1. the flat colour under each texel (PAL: the hair's two lavenders, the skin and its shadow; the collar its own set).
   A texel in a flat area of one of them (within TOL of it, its neighbours within FLAT of it) is sure (a core); every
   other texel (an edge, a ramp, an in-between tone, a line) takes, of the colours of the cores within REACH of it on
   its side of the surface, the one that explains it best as that colour with some ink over it (the least left over,
   LAM for the ink it needs): a ramp between two colours becomes a step, a line's soft edge does not turn into the
   darker of the two tones. Then the borders are smoothed (the commonest colour around, then by wider surroundings:
   rounder shapes), what is too small to be a thing takes the colour around it (areas under SMALL mm2), and so does an
   island of one thing in another (ISLE: the skin's colours inside the hair, the hair's on the skin);
2. the ink over it: how much of the way from its flat colour to black each texel is, sharpened (INK: under [0] none,
   over [1] all): the drawn lines keep their place and their width, smears and greys go. The strokes' toothed edges
   are closed (INK_FILL); strokes under DASH mm2, the small ones alone (LONE) and the faint ink that touches no
   stroke are left out (dashes, crumbs, haze). Under the jaw and on the neck (JAW) the black wedge is made whole and
   the strokes under JAW[1] mm2 go: the drawings' thick jaw line, projected from six images on a jaw that is not
   theirs, was a hatched band with shards around it.

An all-hair triangle takes the hair's colours alone (the side images had painted skin on some), and the locks' inner
sides (INNER) the shadow's tone with no lines. Where Meshy's atlas gives a triangle few texels the neighbourhoods
reach further (PITCH).

The eyes and the brows as the front image draws them (EYE, HALO: what is not skin there, and a little around it) and
the earrings are never touched (Denis, 11/11: "occhi e sopracciglia non si toccano").
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix, coo_matrix
from scipy.sparse.csgraph import connected_components

PAL = {'hairL': (226, 214, 227), 'hairS': (140, 121, 154), 'skin': (247, 188, 146), 'skinS': (172, 116, 90),
       'coat': (55, 44, 61), 'coatL': (80, 62, 92), 'coatD': (42, 35, 45), 'trim': (160, 99, 196)}
INKC = (22, 18, 22)
HEAD = ('hairL', 'hairS', 'skin', 'skinS')        # the hair, the skin, the ears, the neck
COLLAR = ('coat', 'coatL', 'coatD', 'trim')
TOL, FLAT, EDGE = 16, 22, 60       # a core: within TOL of its colour (the largest channel difference), its neighbours within FLAT of it (or none of them darker by EDGE: no line beside it)
LAM = .8                           # the cost of ink: levels per share of ink a colour needs to explain a texel (times 255)
INK = (.38, .68)                   # the ink's share sharpened: none under [0], all over [1]
KNN, NEAR = 9, .0009               # the surface's graph: each texel's KNN - 1 nearest within NEAR m, on its side (normals agreeing over SIDE)
WIDE = (33, .0016)                 # the surroundings: the WIDE[0] - 1 nearest within WIDE[1] m
SIDE = .2
REACH = (.0012, .003, .008)        # an edge texel looks for cores this far (m), further if it finds none
SMOOTH = (1, 3, 2)                 # rounds of the borders' smoothing: (near neighbours, everywhere), (the surroundings, on the hair's triangles), (the same on the others)
INK_FILL = (2, 6)                  # rounds of the strokes' edges' smoothing; a texel with this many of its 8 nearest ink is ink
SMALL, DASH = (40., 12.), (2.5, .5) # mm2: (on the hair's triangles, on the others): the smallest area, the smallest ink stroke
SHORT = .005                       # an ink stroke on the hair shorter than this (m, its box's diagonal): left out (the dashes a line arrives in on a shape not its own)
RIM = .0015                        # the collar's texels on a triangle joining it to the neck: under its collar corners' top plus this (m)
TOP = (.55, .006, .0006)           # the hair seen from above: normals' y over [0]; a hollow: the surface within [1] m stands over the texel by [2] m in the mean
INNER = -.5                        # the locks' inner sides (all-hair triangles turned to the head's middle by over this): the shadow's tone, no lines
PITCH = (1.6, 2.5, .006)           # where the texels are coarse the graph reaches further: [0] (near) and [1] (wide) texels' pitches, up to [2] m
LONE = (2., .0012)                 # an ink stroke under [0] mm2 off the hair with no larger one within [1] m: left out (a dot beside a line, a tick alone)
ISLE = (40., .7)                   # an area under [0] mm2 of the skin's colours over [1] of whose border is the hair's (or the other way round) takes that
JAW = (.028, 60., .5, 2, 100.)           # under the chin plus [0] m, off the hair: ink strokes under [1] mm2 left out; a texel over [2] of whose surroundings are
# ink is ink ([3] rounds): the jaw's black wedge whole, no black shards on the neck; behind the ears' plane strokes under [4] mm2 left out (blots under the ears)
COARSE = .0006                     # m: the skin's texels coarser than this get their ink all or none (see flatten)
HALO = (.0025, 22., .35)           # the eyes and the brows: what is not skin (further than [1] from the skin's tones with under [2] of ink) and [0] m around it
EYE_PIECE = (.0012, .042, .006)    # see eyes_mask(): its pieces (texels within [0] m) wholly beyond [1] m from the middle and [2] m or more from the rest
EYE = (.064, .030, .008, .045, .05, .004, 9, .0012)   # the eyes and the brows, never touched (Denis, 11/11: "occhi e sopracciglia non si toccano"): see eyes_zone():
# |x - middle| under [0], |y - eyes - [2]| under [1], z over [3] (m), facing the front over [4], within [5] m of the skin's surface there ([6]: mm);
# and whatever lies within [7] m of those


def _graph(pos, nor, pitch):
    """Each texel's nearest on its side of the surface: their indices (WIDE[0] - 1), which count as its surroundings (within WIDE[1] m,
    or PITCH[1] of its own pitch where its texels are coarse), which as near (the first KNN - 1, within NEAR m or PITCH[0] pitches)."""
    d, j = cKDTree(pos).query(pos, k=WIDE[0], distance_upper_bound=PITCH[2], workers=-1)
    j = j[:, 1:]; d = d[:, 1:]; fin = np.isfinite(d); j = np.where(fin, j, 0).astype(np.int32)
    for a in range(0, len(pos), 200000): fin[a:a + 200000] &= (nor[a:a + 200000, None, :] * nor[j[a:a + 200000]]).sum(2) > SIDE
    okw = fin & (d < np.maximum(WIDE[1], PITCH[1] * pitch)[:, None])
    ok = fin[:, :KNN - 1] & (d[:, :KNN - 1] < np.maximum(NEAR, PITCH[0] * pitch)[:, None])
    return j, okw, ok


def _dist(c, cols):   # (largest channel difference to each colour)
    return np.abs(c[:, None, :] - cols[None, :, :]).max(2)


def _mode(lab, j, ok, n, keep=None, own=1):
    """Per texel the commonest label of its neighbours and itself (own: its own weight); keep: texels left as they are."""
    N = len(lab); cnt = np.zeros(N * n, np.int32)
    for a in range(0, N, 200000):
        o = ok[a:a + 200000]; idx = (np.arange(a, min(N, a + 200000))[:, None] * n + lab[j[a:a + 200000]])[o]
        cnt += np.bincount(idx, minlength=N * n).astype(np.int32)
    cnt = cnt.reshape(N, n); cnt[np.arange(N), lab] += own
    out = cnt.argmax(1)
    return out if keep is None else np.where(keep, lab, out)


def _small(lab, j, ok, area, least, fixed, rounds=3):
    """Components (of one label, on the surface's graph) under least[label, texel] mm2 take the commonest label around them."""
    N = len(lab); total = 0
    for _ in range(rounds):
        same = ok & (lab[j] == lab[:, None]); r = np.repeat(np.arange(N), j.shape[1])[same.ravel()]; c = j[same]
        _, comp = connected_components(coo_matrix((np.ones(len(r), np.int8), (r, c)), shape=(N, N)).tocsr(), directed=False)
        ca = np.bincount(comp, weights=area); lim = np.zeros(comp.max() + 1); np.maximum.at(lim, comp, least)
        hasfix = np.zeros(comp.max() + 1, bool); np.logical_or.at(hasfix, comp, fixed)
        sm = (ca < lim) & ~hasfix; t = np.nonzero(sm[comp])[0]
        if not len(t): break
        diff = ok[t] & (lab[j[t]] != lab[t][:, None]); n = int(lab.max()) + 1
        tab = np.zeros((comp.max() + 1, n), np.int32); np.add.at(tab, (np.repeat(comp[t], j.shape[1])[diff.ravel()], lab[j[t]][diff]), 1)
        new = tab.argmax(1); has = tab.sum(1) > 0; ch = has[comp[t]]
        lab[t[ch]] = new[comp[t[ch]]]; total += int(ch.sum())
    return total


def eyes_zone(p, n, mid, eye_m, skin):
    """Per texel (place p, normal n; skin: of a triangle with two corners skin's or more): of the eyes and the brows as
    the front image draws them (EYE): in their box, facing the front, on the face's own layer (the skin's surface there,
    carried across the eyes, whose whites are not skin's colour: within EYE[5] m of it; not the locks before them nor
    those beside the face)."""
    from scipy import ndimage
    box = (np.abs(p[:, 0] - mid) < EYE[0]) & (np.abs(p[:, 1] - eye_m - EYE[2]) < EYE[1]) & (p[:, 2] > EYE[3]) & (n[:, 2] > EYE[4])
    b = np.nonzero(box)[0]; out = np.zeros(len(p), bool)
    if not len(b): return out
    gx = np.floor((p[b, 0] - mid + EYE[0]) / .001).astype(int); gy = np.floor((p[b, 1] - eye_m - EYE[2] + EYE[1]) / .001).astype(int)
    Z = np.full((gx.max() + 1, gy.max() + 1), np.inf); sk = skin[b]; np.minimum.at(Z, (gx[sk], gy[sk]), p[b[sk], 2])
    known = np.isfinite(Z); dist, (ix, iy) = ndimage.distance_transform_edt(~known, return_indices=True)
    Zf = np.where(dist <= EYE[6], Z[ix, iy], np.inf)   # (across the eyes: the nearest skin's, up to EYE[6] mm away)
    out[b[np.abs(p[b, 2] - Zf[gx, gy]) < EYE[5]]] = True
    return out


def eyes_mask(p, n, c, skin2, mid, eye_m, halo=None, skip=None):
    """Per texel (place p, normal n, colour c; skin2: of a triangle with two corners skin's or more): of the eyes and the
    brows themselves, which flatten() leaves as painted: in eyes_zone() and what lies within EYE[7] m of it (the crumbs
    inside the zone that face away or sit a little off the skin), what is not the skin's (their whites, irises, lashes,
    the brows and their lines) and halo m (HALO[0]) around it; the skin in the rest of the zone is the cheeks'. skip: the
    texels that are not theirs whatever their colour (the locks kael_fringe.side_paint() paints on the temples by the
    eyes' corners: hair's colours, they would count as brows and stay soft)."""
    names = list(PAL); cols = np.array([PAL[k] for k in names], np.float32)
    eye = eyes_zone(p, n, mid, eye_m, skin2)
    if skip is not None: eye &= ~skip
    if eye.any():
        rest = np.nonzero(~eye & (np.abs(p[:, 0] - mid) < EYE[0] + .004) & (np.abs(p[:, 1] - eye_m - EYE[2]) < EYE[1] + .004) & (True if skip is None else ~skip))[0]
        dd, _ = cKDTree(p[eye]).query(p[rest], distance_upper_bound=EYE[7]); eye[rest[np.isfinite(dd)]] = True
    if eye.any():
        e = np.nonzero(eye)[0]; feat = ~_skinish(c[e], cols, names)
        if feat.any():
            dd, _ = cKDTree(p[e[feat]]).query(p[e], distance_upper_bound=HALO[0] if halo is None else halo); eye[e[~np.isfinite(dd)]] = False
    if eye.any():   # (not the pieces of it lying wholly beyond EYE_PIECE[1] from the middle, EYE_PIECE[2] or more from the rest: a drawn lock's
        # outline ends and a hair-coloured scrap on his left temple, counted as features by their colour, held a brown wedge there unpainted and
        # soft. The eyes and the brows start inside EYE_PIECE[1]; the left brow's tail end, a group of its own seen from the 3/4, lies 2-4 mm
        # from the rest of the brow and stays)
        e = np.nonzero(eye)[0]; pr = cKDTree(p[e]).query_pairs(EYE_PIECE[0], output_type='ndarray')
        _, lab_ = connected_components(coo_matrix((np.ones(len(pr), np.int8), (pr[:, 0], pr[:, 1])), shape=(len(e), len(e))).tocsr(), directed=False)
        far = np.ones(lab_.max() + 1, bool); np.logical_and.at(far, lab_, np.abs(p[e, 0] - mid) > EYE_PIECE[1])
        near_ = ~far[lab_]
        if far.any() and near_.any():
            tr = cKDTree(p[e[near_]]); gone = 0
            for q in np.nonzero(far)[0]:
                inn = lab_ == q; dd, _ = tr.query(p[e[inn]])
                if dd.min() >= EYE_PIECE[2]: eye[e[inn]] = False; gone += int(inn.sum())
            if gone: print('eyes: %d texels of the mask\'s far pieces, detached from the eyes and the brows, left out of it' % gone)
    return eye


def _split(c, cols):
    """Each colour c as each flat colour with ink over it: (the ink's share, what is left over), per flat colour."""
    v = np.array(INKC, np.float32)[None] - cols; vv = (v * v).sum(1)
    al = np.zeros((len(c), len(cols)), np.float32); r = np.zeros((len(c), len(cols)), np.float32)
    for a in range(0, len(c), 200000):
        d = c[a:a + 200000, None, :] - cols[None]; t = np.clip((d * v[None]).sum(2) / vv[None], 0, 1)
        al[a:a + 200000] = t; r[a:a + 200000] = np.linalg.norm(d - t[..., None] * v[None], axis=2)
    return al, r


def _skinish(c, cols, names):
    """Per colour: one of the skin's tones (between the skin's and its shadow's, with under HALO[2] of ink over it), within HALO[1]."""
    a, b = cols[names.index('skin')], cols[names.index('skinS')]; out = np.zeros(len(c), bool)
    for t in np.linspace(0, 1, 9):
        base = (a + (b - a) * t)[None]; al, r = _split(c, base); out |= (r[:, 0] < HALO[1]) & (al[:, 0] < HALO[2])
    return out


def _comps(lab, j, ok):
    N = len(lab); same = ok & (lab[j] == lab[:, None]); r = np.repeat(np.arange(N), j.shape[1])[same.ravel()]
    return connected_components(coo_matrix((np.ones(len(r), np.int8), (r, j[same])), shape=(N, N)).tocsr(), directed=False)[1]


def flatten(out, It, ys, xs, ks, pos, nor, hair_v, skin_v, ear_v, collar_v, keep_t, mid, eye_m, chin_m, face_t=None, log=print, not_eye=None):
    names = list(PAL); cols = np.array([PAL[k] for k in names], np.float32); nl = len(names)
    use = np.nonzero(keep_t[ks])[0]   # (the triangles left out are not drawn)
    p = pos[use].astype(np.float64); n = nor[use].astype(np.float32); c = out[ys[use], xs[use]].astype(np.float32); T = It[ks[use]]
    hair = hair_v[T].sum(1) >= 2
    # (the collar's: its own triangles, and of those joining it to the neck what lies under its rim (their collar corners' top plus RIM m); the rest
    # of them is the neck's skin. All of them the collar's, one reaching up the nape was a black triangle on the skin)
    rim = np.where(collar_v[It], VERT[It][:, :, 1], -1e9).max(1)[ks[use]]; col = collar_v[T].all(1) | (collar_v[T].any(1) & (p[:, 1] < rim + RIM))
    # (the earrings': their own triangles, and on those joining them to the lobe and the hair the crystals' purples; the skin and the hair there are
    # cleaned as the rest: soft smears stayed round each hook)
    ear = ear_v[T].all(1) | (ear_v[T].any(1) & (c[:, 2] - c[:, 1] > 60))
    if face_t is not None: hair &= ~face_t[ks[use]]   # (not the hair's scraps that are part of the face: tools/kael_fringe.py)
    hair3 = hair & (hair_v[T].sum(1) == 3) & ~col & ~ear   # (all hair: the hair's two colours alone; a triangle on the hairline may be part skin)
    eye = eyes_mask(p, n, c, skin_v[T].sum(1) >= 2, mid, eye_m, skip=None if not_eye is None else not_eye[use])
    fixed = ear | eye
    allow = np.zeros((len(use), nl), bool)
    allow[np.ix_(~col, [names.index(k) for k in HEAD])] = True; allow[np.ix_(col, [names.index(k) for k in COLLAR])] = True
    allow[np.ix_(hair3, [names.index('skin'), names.index('skinS')])] = False
    tri = ks[use]; cnt = np.bincount(tri, minlength=len(It)).astype(np.float64)
    area = TRI_AREA[tri] * 1e6 / np.maximum(cnt[tri], 1)   # (the texels' areas, mm2: their triangle's over its texels)
    jw, okw, ok = _graph(p, n, np.sqrt(area) * 1e-3); j = jw[:, :KNN - 1]
    c0 = np.array([mid, eye_m + .03, -.01]); rad = p - c0; rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-9)
    inner = hair3 & ~fixed & ((n * rad).sum(1) < INNER)   # (the locks' inner sides: seen where a lock is hidden or from below; one tone, no lines)
    # 1. the flat colour under each texel: the cores, then the others from the cores near them
    D = _dist(c, cols); D[~allow] = 1e9; near = D.argmin(1); dn = D[np.arange(len(use)), near]
    L = c.mean(1); rng = np.where(ok, np.abs(c[j] - c[:, None, :]).max(2), 0).max(1); drop = np.where(ok, L[:, None] - L[j], 0).max(1)
    core = (dn <= TOL) & ((rng <= FLAT) | (drop < EDGE))
    lab = near.astype(np.int64)
    al, res = _split(c, cols); cost = res + LAM * 255 * al; cost[~allow] = 1e9
    todo = np.nonzero(~core)[0]; done = np.zeros(len(todo), bool); ci = np.nonzero(core)[0]; tree = cKDTree(p[ci])
    for R in REACH:
        t = todo[~done]
        if not len(t): break
        pres = np.zeros((len(t), nl), bool)
        for a in range(0, len(t), 100000):
            tt = t[a:a + 100000]; m = cKDTree(p[tt]).sparse_distance_matrix(tree, R, output_type='coo_matrix')
            r, q = m.row, ci[m.col]; side = (n[tt[r]] * n[q]).sum(1) > SIDE
            pres[a + r[side], lab[q[side]]] = True
        pres &= allow[t]; got = pres.any(1)
        dd = np.where(pres, cost[t], 1e9); lab[t[got]] = dd[got].argmin(1); done[np.nonzero(~done)[0][got]] = True
    t = todo[~done]; lab[t] = cost[t].argmin(1)
    log('flat: %d texels of %d in a flat area of one of the drawings\' colours; %d on edges, ramps and lines took the colour beside them that explains them best (%d found none near)' % (
        int(core.sum()), len(use), int(done.sum()), len(t)))
    lab[inner] = names.index('hairS')
    top = hair3 & ~fixed & ~inner & (n[:, 1] > TOP[0])   # (the hair seen from above, which no drawing shows: its tones were the side drawings', taken at a slant, and
    # Meshy's own: blotches that follow no lock. By the shape: the shadow's tone in the hollows between the locks (the surface around a texel, within
    # TOP[1] m, standing over it by TOP[2] m or more in the mean), the light's elsewhere)
    if top.any():
        cl = np.nonzero(hair)[0][::5]; tr = cKDTree(p[cl]); ti = np.nonzero(top)[0]; hol = np.zeros(len(ti), bool)
        for a in range(0, len(ti), 20000):
            tt = ti[a:a + 20000]; m = cKDTree(p[tt]).sparse_distance_matrix(tr, TOP[1], output_type='coo_matrix')
            off = ((p[cl[m.col]] - p[tt[m.row]]) * n[tt[m.row]]).sum(1); sm_ = np.bincount(m.row, weights=off, minlength=len(tt)); cn_ = np.bincount(m.row, minlength=len(tt))
            hol[a:a + 20000] = sm_ / np.maximum(cn_, 1) > TOP[2]
        lab[ti] = np.where(hol, names.index('hairS'), names.index('hairL'))
        log('flat: the hair seen from above (%d texels): the shadow\'s tone in the hollows between the locks (%.0f%%), the light\'s elsewhere' % (len(ti), 100 * hol.mean()))
    for _ in range(SMOOTH[0]):
        m = _mode(lab, j, ok, nl, keep=fixed | inner)
        lab = np.where(allow[np.arange(len(use)), m], m, lab)
    for r in range(max(SMOOTH[1], SMOOTH[2])):   # (by their surroundings, rounder shapes: the hair's two tones, and the skin's and its shadow's)
        m = _mode(lab, jw, okw, nl, keep=fixed | col | inner | (hair & (r >= SMOOTH[1])) | (~hair & (r >= SMOOTH[2])))
        lab = np.where(allow[np.arange(len(use)), m], m, lab)
    ns = _small(lab, j, ok, area, np.where(hair, SMALL[0], SMALL[1]), fixed | inner)
    lab[inner] = names.index('hairS')
    # (an area of the skin's colours nearly all of whose border is the hair's, or of the hair's in the skin: a stroke of the skin's shadow inside
    # a lock, a hair-coloured block on the cheek. And the crumbs standing at an angle to what is around them, with no neighbour on their side)
    isk = np.isin(lab, [names.index('skin'), names.index('skinS')]); kind = np.where(col, 2, np.where(isk, 0, 1))
    comp = _comps(lab, j, ok); ca = np.bincount(comp, weights=area); nc = len(ca)
    diff = ok & (comp[j] != comp[:, None]); rr = np.repeat(np.arange(len(lab)), j.shape[1])[diff.ravel()]; qq = j[diff]
    bk = np.zeros((nc, 3)); np.add.at(bk, (comp[rr], kind[qq]), 1.); ck = np.zeros(nc, np.int64); ck[comp] = kind
    hasfix = np.zeros(nc, bool); np.logical_or.at(hasfix, comp, fixed)
    other = 1 - np.minimum(ck, 1); share = bk[np.arange(nc), other] / np.maximum(bk.sum(1), 1)
    isle = (ca < ISLE[0]) & (ck < 2) & (share > ISLE[1]) & ~hasfix & (bk.sum(1) > 0)
    lone = (ca < SMALL[1]) & (bk.sum(1) == 0) & ~hasfix & (ck < 2)   # (no neighbour on its side: by the nearest of any side)
    ni = 0
    for sel in (isle, lone):
        t = np.nonzero(sel[comp])[0]
        if not len(t): continue
        cand = np.nonzero(~sel[comp] & ~col)[0]; dd, jj = cKDTree(p[cand]).query(p[t], distance_upper_bound=.004)
        okk = np.isfinite(dd); tab = np.zeros((nc, nl)); np.add.at(tab, (comp[t[okk]], lab[cand[jj[okk]]]), 1.)
        if sel is isle:   # (the other kind's colours alone)
            tab[:, [names.index('skin'), names.index('skinS')]] *= (ck == 1)[:, None]; tab[:, [names.index('hairL'), names.index('hairS')]] *= (ck == 0)[:, None]
        has = tab.sum(1) > 0; ch = has[comp[t]]; lab[t[ch]] = tab.argmax(1)[comp[t[ch]]]; ni += int(ch.sum())
    # 2. the ink over it
    a_ = al[np.arange(len(use)), lab]; q = np.clip((a_ - INK[0]) / (INK[1] - INK[0]), 0, 1); a_ = q * q * (3 - 2 * q)
    a_[inner] = 0.
    ink = (a_ >= .5).astype(np.int64)
    for _ in range(INK_FILL[0]):   # (the strokes' edges: a texel most of whose neighbours are ink is ink (the notches of a toothed edge), one with
        # none of them is not (crumbs). The thin lines are left as they are)
        nb = np.where(ok, ink[j], 0).sum(1); nn = ok.sum(1)
        fill = (ink == 0) & ~fixed & (nb >= INK_FILL[1]); drop = (ink == 1) & ~fixed & (nb == 0) & (nn >= 4)
        ink[fill] = 1; a_[fill] = 1.; ink[drop] = 0; a_[drop] = 0.
    jaw = ~hair & ~col & ~fixed & (p[:, 1] < chin_m + JAW[0])   # (the jaw and the neck: see JAW)
    for _ in range(JAW[3]):
        sh = np.where(okw, ink[jw], 0).sum(1) / np.maximum(okw.sum(1), 1); fill = jaw & (ink == 0) & (sh > JAW[2]); ink[fill] = 1; a_[fill] = 1.
    nd = _small(ink, j, ok, area, np.where(ink == 1, np.where(hair, DASH[0], np.where(jaw, np.where(p[:, 2] < 0, JAW[4], JAW[1]), DASH[1])), 0.), fixed, rounds=1)   # (the dashes: strokes too small)
    comp = _comps(ink, j, ok); nc = int(comp.max()) + 1   # (the short strokes on the hair)
    lo = np.full((nc, 3), 1e9); hi = np.full((nc, 3), -1e9); np.minimum.at(lo, comp, p); np.maximum.at(hi, comp, p)
    hf = np.zeros(nc, bool); np.logical_or.at(hf, comp, fixed); onh = np.zeros(nc); np.add.at(onh, comp, hair * 1.); cn = np.bincount(comp, minlength=nc)
    short = (np.linalg.norm(hi - lo, axis=1) < SHORT) & ~hf & (onh > .5 * cn); gone = (ink == 1) & short[comp]; ink[gone] = 0; nd += int(gone.sum())
    comp = _comps(ink, j, ok); ca = np.bincount(comp, weights=area); big = (ca >= LONE[0])[comp] & (ink == 1); sm = (ink == 1) & ~big & ~hair & ~fixed
    if sm.any() and big.any():   # (the lone small strokes)
        dd, _ = cKDTree(p[big]).query(p[sm], distance_upper_bound=LONE[1]); lc = np.zeros(len(ca), bool); np.logical_or.at(lc, comp[sm], np.isfinite(dd))
        gone = sm & ~lc[comp]; ink[gone] = 0; nd += int(gone.sum())
    a_ = np.where((a_ >= .5) & (ink == 0), 0., a_)
    touch = (np.where(ok, ink[j], 0).max(1) > 0) | (ink == 1); haze = (a_ > 0) & ~touch; a_[haze] = 0.
    # (all or none: the locks painted on the temples by the eyes' corners (not_eye) and the skin's coarse texels (over COARSE m). There a share of
    # ink was a grey band between two outlines, a grey smear on a 1 mm texel, soft black blobs inside a lock)
    crisp = ~fixed & (skin_v[T].all(1) & (area > (COARSE * 1e3) ** 2))
    if not_eye is not None: crisp |= ~fixed & not_eye[use]
    a_ = np.where(crisp, (a_ >= .5).astype(a_.dtype), a_)
    log('flat: %d texels of islands of one thing in another (under %.0f mm2) took its colour' % (ni, ISLE[0]))
    log('flat: %d texels of specks took the colour around them (areas under %.0f mm2 on the hair, %.0f elsewhere); ink: %d texels of lines, %d of dashes (under %.1f mm2 on the hair, %.1f elsewhere) and %d of haze left out' % (
        ns, SMALL[0], SMALL[1], int(ink.sum()), nd, DASH[0], DASH[1], int(haze.sum())))
    w = ~fixed; before = c[w].copy(); newc = cols[lab[w]] * (1 - a_[w, None]) + np.array(INKC, np.float32)[None] * a_[w, None]
    out[ys[use[w]], xs[use[w]]] = newc
    ch = np.abs(newc - before).max(1)
    log('flat: %d texels flat (%d of the eyes, the brows and the earrings left as they are); %.1f%% changed by over 20 levels, %.1f%% by over 60' % (int(w.sum()), int(fixed.sum()), 100 * (ch > 20).mean(), 100 * (ch > 60).mean()))
    return lab, a_, use, fixed


TRI_AREA = VERT = None


def prepare(Q, It):
    """The vertices and the triangles' areas (m2; flatten needs them: call first)."""
    global TRI_AREA, VERT
    VERT = Q; TRI_AREA = .5 * np.linalg.norm(np.cross(Q[It[:, 1]] - Q[It[:, 0]], Q[It[:, 2]] - Q[It[:, 0]]), axis=1)


if __name__ == '__main__':   # (the pass alone, to work on it: python3 tools/kael_flat.py DUMP.npz DIR, on the builder's state before it, saved
    # by KAEL_FLAT_DUMP=DUMP.npz python3 tools/kael_head.py ...; writes DIR/kael_head.png for a package already built there)
    import sys, os
    from PIL import Image
    from scipy import ndimage
    d = np.load(sys.argv[1]); out = d['out'].astype(np.float64); prepare(d['Q'], d['It'])
    flatten(out, d['It'], d['ys'], d['xs'], d['ks'], d['pos'], d['nor'], d['hair_v'], d['skin_v'], d['ear_v'], d['collar_v'], d['keep_t'], float(d['mid']), float(d['eye_m']), float(d['chin_m']),
            face_t=d['face_t'] if 'face_t' in d else None, not_eye=d['not_eye'] if 'not_eye' in d else None)
    TS = out.shape[0]; cov = np.zeros((TS, TS), bool); kt = d['keep_t'][d['ks']]; cov[d['ys'][kt], d['xs'][kt]] = True   # (as tools/kael_head.py, but for the eyes' surroundings)
    _, (iy, ix) = ndimage.distance_transform_edt(~cov, return_indices=True); out[~cov] = out[iy[~cov], ix[~cov]]
    Image.fromarray(np.clip(out, 0, 255).round().astype(np.uint8)).save(os.path.join(sys.argv[2], 'kael_head.png'), optimize=True)
    print('written', os.path.join(sys.argv[2], 'kael_head.png'), os.path.getsize(os.path.join(sys.argv[2], 'kael_head.png')), 'bytes')
