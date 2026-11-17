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


CHECKS = (crop_paint_is_exact, hands_part_is_rens, bust_has_no_hand_triangles)

if __name__ == '__main__':
    dump = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('KAEL_ATTACH_DUMP')
    if not dump: sys.exit(__doc__)
    D = np.load(dump)
    for c in CHECKS: c(D)
    print('OK')
