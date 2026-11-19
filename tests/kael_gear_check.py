#!/usr/bin/env python3
"""Checks of Kael's hands and wrists remade (docs/superpowers/plans/2026-11-17-kael-mani-polso.md): his hands Ren's, as
their own part (wip_assets/kael/kael_hands.*), the bust without them; later the gloves' shell and the wrists' rings
(kael_gloves.*). Plain asserts; prints OK.

The part vertices' places in Ren's package come from tools/kael_bust_attach.py's dump (KAEL_ATTACH_DUMP=<file.npz> when
it runs): the path as the argument or in KAEL_ATTACH_DUMP.

usage: python3 tests/kael_gear_check.py [DUMP.npz]"""
import json, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
KAEL = os.path.join(ROOT, 'wip_assets', 'kael')
REN_PKG, REN_LOOK, REN_PAINT = (os.path.join(ROOT, *p) for p in (('assets', 'ren', 'ren.json'), ('viewer_assets', 'ren', 'ren_look.json'), ('viewer_assets', 'ren', 'ren_painted.jpg')))


def part(name):
    """a part of Kael's package: its json and {key: array} of its blocks"""
    j = json.load(open(os.path.join(KAEL, 'kael_%s.json' % name))); b = open(os.path.join(KAEL, 'kael_%s.bin' % name), 'rb').read()
    n = j['verts']; dt = {'jnt': np.uint8, 'idx': np.uint16 if n < 65536 else np.uint32, 'hide': np.uint32, 'near': np.int32}
    width = {'pos': 3, 'nor': 3, 'uv': 2, 'jnt': 4, 'wgt': 4, 'idx': 3, 'glove': 2, 'col': 3}
    A = {}
    for k, v in j.items():
        if isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) for x in v) and k not in ('bones',):
            a = np.frombuffer(b, dt.get(k, np.float32), v[1], v[0]); A[k] = a.reshape(-1, width[k]) if k in width else a
    return j, A


def ren_look_block(key):
    L = json.load(open(REN_LOOK)); B = open(REN_LOOK[:-4] + 'bin', 'rb').read()
    return np.frombuffer(B, np.float32, L[key][1], L[key][0])


def sample(img, uv):
    a = np.asarray(img).astype(float); h, w = a.shape[:2]
    return a[np.clip((uv[:, 1] * h).astype(int), 0, h - 1), np.clip((uv[:, 0] * w).astype(int), 0, w - 1)]


def crop_paint_is_exact(D):
    """the hands' paint, cropped out of Ren's: at their new coordinates the same colours as Ren's at his"""
    if str(D['style']) != 'ren': return   # (the hands as the sheet draws them: not Ren's paint and normals)
    from kael_bust_attach import package
    j, A = part('hands'); R = package(REN_PKG); rid = D['hands_rid']
    k = np.random.default_rng(1).choice(len(rid), min(500, len(rid)), replace=False)
    mine = sample(Image.open(os.path.join(KAEL, 'kael_hands.jpg')).convert('RGB'), A['uv'][k])
    ren = sample(Image.open(REN_PAINT).convert('RGB'), R['UV'][rid[k]])
    d = np.abs(mine - ren).mean()
    assert d < 3, 'crop_paint_is_exact: mean difference %.2f levels' % d


def hands_part_is_rens(D):
    """the hands' light and outline per vertex Ren's own; their normals Ren's, only turned with the hand (away from the
    wrist: within 5 cm of the seam the pose blends the hand's turn with the forearm's, positions and normals alike)"""
    if str(D['style']) != 'ren': return   # (the hands as the sheet draws them: not Ren's paint and normals)
    j, A = part('hands'); rid = D['hands_rid']; side = D['hands_side']; far = D['hands_dseam'] > .05
    for key in ('flat', 'line'):
        err = np.abs(A[key] - ren_look_block(key)[rid]).max()
        assert err < 1e-6, 'hands_part_is_rens: %s differs from Ren\'s by %.2g' % (key, err)
    Rn = ren_look_block('nor').reshape(-1, 3)[rid].astype(float); Kn = A['nor'].astype(float)
    for s in (True, False):   # (per hand the turn that best lays Ren's normals on the part's: Kabsch)
        m = (side == s) & far; U, _, Vt = np.linalg.svd(Kn[m].T @ Rn[m]); Rot = U @ np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))]) @ Vt
        ang = np.degrees(np.arccos(np.clip(((Rn[m] @ Rot.T) * Kn[m]).sum(1), -1, 1)))
        assert np.percentile(ang, 99) < 2, 'hands_part_is_rens: normals off Ren\'s by %.2f deg (99th percentile)' % np.percentile(ang, 99)


def bust_has_no_hand_triangles(D):
    """the bust keeps no triangle of Ren's hands (the seam's, part hand part arm, stay: under the ring)"""
    j, A = part('bust'); rid = D['rid']
    whole = (rid[A['idx']] >= 0).all(1).sum()
    assert whole == 0, 'bust_has_no_hand_triangles: %d triangles of the hands still in the bust' % whole


GLOVE_T = .002   # m: the glove's shell over the skin (tools/kael_gear.py shell)


def clip_edge_on_iso(D):
    """clip_iso keeps the triangles' part with D <= 0: the cut's vertices on D = 0, the area kept right (a 10x10 plane, D = x - .3)"""
    from kael_gear import clip_iso
    g = np.linspace(0, 1, 11); X, Y = np.meshgrid(g, g); P = np.c_[X.ravel(), Y.ravel(), np.zeros(121)]
    I = np.array([[r * 11 + c, r * 11 + c + 1, (r + 1) * 11 + c + 1] for r in range(10) for c in range(10)]
                 + [[r * 11 + c, (r + 1) * 11 + c + 1, (r + 1) * 11 + c] for r in range(10) for c in range(10)])
    N = np.tile([0, 0, 1.], (121, 1)); W = np.c_[P[:, 0], 1 - P[:, 0]]; Dv = P[:, 0] - .3
    P2, N2, W2, D2, I2 = clip_iso(P, N, W, Dv, I)
    assert (D2 <= 1e-9).all(), 'clip_edge_on_iso: a vertex kept past the edge'
    new = np.abs(P2[:, 0] - .3) < 1e-9
    assert new.sum() >= 11 and np.abs(D2[new]).max() < 1e-6, 'clip_edge_on_iso: the cut is not on D = 0'
    assert np.allclose(W2, np.c_[P2[:, 0], 1 - P2[:, 0]], atol=1e-9), 'clip_edge_on_iso: the weights not interpolated'
    area = np.abs(np.cross(P2[I2[:, 1]] - P2[I2[:, 0]], P2[I2[:, 2]] - P2[I2[:, 0]])[:, 2]).sum() / 2
    assert abs(area - .3) < .003, 'clip_edge_on_iso: kept area %.4f, not 0.3' % area


def shell_offset(D):
    """the glove's shell: GLOVE_T over the skin it comes from, inside the glove (more than 3 mm from its edge), past where it
    flares out to the wrist's ring (2.5 cm past the ring's edge: flare_no_neck)"""
    j, G = part('gloves'); _, H = part('hands')
    m = (G['glove'][:, 0] < -.003) & (G['near'] >= 0)
    for g in j.get('rings', []):
        t, r, k = ring_frame(g, G['pos'].astype(float)); m &= ~((t < g['h'] / 2 + .025) & (r < .1))
    d = np.linalg.norm(G['pos'][m] - H['pos'][G['near'][m]], axis=1)
    assert m.sum() > 200 and d.min() > GLOVE_T - .0002 and d.max() < GLOVE_T + .002, 'shell_offset: %d vertices, %.2f to %.2f mm from their skin' % (m.sum(), 1000 * d.min(), 1000 * d.max())


def surface_points(P, I, k=8):
    """points spread over the triangles (k + 1 rows of barycentric samples each, about 1 mm apart on Ren's hands)"""
    u = np.array([(a, b) for a in range(k + 1) for b in range(k + 1 - a)]) / k; w = 1 - u.sum(1)
    return (w[None, :, None] * P[I[:, 0]][:, None] + u[None, :, 0, None] * P[I[:, 1]][:, None] + u[None, :, 1, None] * P[I[:, 2]][:, None]).reshape(-1, 3)


def shell_clears_skin(D):
    """the shell clears the hands' skin round it, not only the point it comes from (Ren's skin by the wrist has 1 mm bumps):
    each shell vertex inside the glove at least GLOVE_T - 0.5 mm from the skin's surface (sampled about every mm), past 2 cm
    from the wrist's seam (there the ring covers the join and the glove flares out to it: ring_clears_wrist, flare_no_neck, glove_meets_ring)"""
    from scipy.spatial import cKDTree
    j, G = part('gloves'); _, H = part('hands')
    m = (G['glove'][:, 0] < -.003) & (G['near'] >= 0)
    m[m] = D['hands_dseam'][G['near'][m]] > .02
    for g in j.get('rings', []):   # (and past where the glove and the skin flare out to the ring together)
        t, r, k = ring_frame(g, G['pos'].astype(float)); m &= ~((t < g['h'] / 2 + .025) & (r < .1))
    d, _ = cKDTree(surface_points(H['pos'].astype(float), H['idx'].astype(np.int64))).query(G['pos'][m])
    assert d.min() > GLOVE_T - .0005, 'shell_clears_skin: %d shell vertices nearer the skin than %.1f mm (the nearest %.2f mm)' % (
        (d < GLOVE_T - .0005).sum(), 1000 * (GLOVE_T - .0005), 1000 * d.min())


def glove_covers(D):
    """every point of the hands inside the glove (more than 3 mm from its edge) has the shell over it, within GLOVE_T + 2 mm
    (the shell is GLOVE_T over the skin, up to 1.5 mm more over its bumps)"""
    from scipy.spatial import cKDTree
    j, G = part('gloves'); _, H = part('hands')
    inside = D['hands_D'] < -.003
    for g in j.get('rings', []):   # (by the ring the glove flares out to it, away from the skin: flare_no_neck, ring_clears_wrist)
        t, r, k = ring_frame(g, H['pos'].astype(float)); inside &= ~((t < g['h'] / 2 + .025) & (r < .1))
    d, _ = cKDTree(G['pos']).query(H['pos'][inside])
    assert inside.sum() > 200 and d.max() < GLOVE_T + .002, 'glove_covers: %d skin points, one %.2f mm from the shell' % (inside.sum(), 1000 * d.max())


def ring_frame(g, P):
    """the points P in a ring's frame: along its axis from its middle (toward the hand), their radius, their angle's bin"""
    c, ax, ref = (np.array(g[k]) for k in ('c', 'ax', 'ref')); d = P - c; t = d @ ax; rad = d - np.outer(t, ax)
    th = np.arctan2(rad @ np.cross(ax, ref), rad @ ref); n = len(g['r'])
    return t, np.linalg.norm(rad, axis=1), np.round(th / (2 * np.pi) * n).astype(int) % n


def ring_clears_wrist(D):
    """each wrist's ring at least 2 mm over everything inside its height (the bust's cuff, the hands, the glove), all round"""
    j, G = part('gloves'); parts = [part('bust')[1]['pos'], part('hands')[1]['pos'], G['pos'][G['near'] >= 0]]
    assert len(j.get('rings', [])) == 2, 'ring_clears_wrist: %d rings' % len(j.get('rings', []))
    for g in j['rings']:
        for P in parts:
            t, r, k = ring_frame(g, P.astype(float)); m = (np.abs(t) <= g['h'] / 2) & (r < 2 * np.median(g['r']))   # (round the wrist, not the torso in the same slice)
            gap = (np.array(g['r'])[k[m]] - r[m]).min() if m.any() else 1.
            assert gap >= .002, 'ring_clears_wrist: a point %.1f mm under the ring\'s surface' % (1000 * gap)


def flare_no_neck(D):
    """by the ring's edge on the hand's side the glove is as wide as the ring's inside (less 1 mm): no neck between them"""
    j, G = part('gloves'); S = G['pos'][G['near'] >= 0].astype(float)
    for g in j['rings']:
        t, r, k = ring_frame(g, S); m = (t >= g['h'] / 2) & (t <= g['h'] / 2 + .004)
        assert m.sum() > 5, 'flare_no_neck: no glove by the ring'
        short = (np.array(g['rin'])[k[m]] - .001 - r[m]).max()
        assert short <= 0, 'flare_no_neck: the glove %.1f mm inside the ring\'s inside by its edge' % (1000 * short)


def glove_meets_ring(D):
    """the glove's open end by the wrist (its boundary that is not its edge over the fingers) goes inside its ring: no gap
    between them (where the bust's paint by the seam showed, a light line)"""
    j, G = part('gloves'); sh = np.nonzero(G['near'] >= 0)[0]; I = G['idx'].astype(np.int64)
    I = I[np.isin(I, sh).all(1)]; E = np.concatenate([I[:, [0, 1]], I[:, [1, 2]], I[:, [2, 0]]])
    key = np.round(G['pos'] / 1e-6).astype(np.int64); _, grp = np.unique(key, axis=0, return_inverse=True); grp = grp.ravel()
    ks = np.sort(grp[E], 1); _, inv, cnt = np.unique(ks, axis=0, return_inverse=True, return_counts=True)
    bnd = E[cnt[inv.ravel()] == 1]; bnd = bnd[(np.abs(G['glove'][bnd, 0]) > 1e-6).any(1)]   # (not its edge over the fingers: D = 0 there, nor its strip)
    v = np.unique(bnd); far = 0.
    for g in j['rings']:
        t, r, k = ring_frame(g, G['pos'][v].astype(float)); m = r < .1
        if m.any(): far = max(far, (t[m] - g['h'] / 2).max())
    assert len(v) > 10 and far <= 0, 'glove_meets_ring: the glove\'s open end %.1f mm past its ring' % (1000 * far)


CHECKS = (crop_paint_is_exact, hands_part_is_rens, bust_has_no_hand_triangles, clip_edge_on_iso, shell_offset, shell_clears_skin, glove_covers, ring_clears_wrist, flare_no_neck, glove_meets_ring)

if __name__ == '__main__':
    dump = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('KAEL_ATTACH_DUMP')
    if not dump: sys.exit(__doc__)
    D = np.load(dump)
    for c in CHECKS: c(D)
    print('OK')
