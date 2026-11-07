#!/usr/bin/env python3
"""Packs a Meshy rigged character and its Meshy animation clips for the game (Tappa 2a).

usage: python3 tools/meshy_pack.py RIG_GLB ANIM_DIR OUT_DIR
  RIG_GLB  the rigging task's rigged_character_glb (one skinned mesh, one texture)
  ANIM_DIR a<ID>.glb files, one Meshy animation task each (the same rig); the clip id is the file name ('a89')
  OUT_DIR  gets <name>.json (layout), <name>.bin (data) and <name>.jpg (texture), name = the folder's name

Space of the output: metres, y up, the feet at y=0, forward +z, the Hips centred in x and z; Meshy's Armature scale
(0.01) is baked in. ren.json: {v, height, bones:[{n, p, t, q}], mesh:{verts, tris, pos, nor, uv, jnt, wgt, idx},
clips:{id:{name, n, fps, q, h}}, limbs:{handL|handR|footL|footR: {b, p}}, head}; every array field is [byte offset into
the .bin, element count]. The .bin is little-endian: pos/nor float32x3, uv float32x2, jnt uint8x4 (bone indices of the
bones list), wgt float32x4 (sum 1), idx uint16 (uint32 above 65535 vertices); a clip's q is n frames x bones x 4
float32 (local rotations, every bone), h n x 3 float32 (the Hips' local position). Blocks start on 4-byte boundaries.
"""
import io, json, os, struct, sys
import numpy as np
from PIL import Image

CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
HEAD_ROUND = .85                      # how far the head's normals turn toward a sphere (clean toon face)
LIMB_W = .6                           # a vertex belongs to a limb point from this weight on
LIMBS = {'handL': ('LeftHand', ['LeftHand']), 'handR': ('RightHand', ['RightHand']),
         'footL': ('LeftFoot', ['LeftFoot', 'LeftToeBase']), 'footR': ('RightFoot', ['RightFoot', 'RightToeBase'])}
TEX_SIZE, TEX_Q = 2048, 85


def read_glb(path):
    b = open(path, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    o = 20 + n; bl = struct.unpack('<I', b[o:o + 4])[0]
    return j, b[o + 8:o + 8 + bl]


def acc(j, BIN, i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]; dt = CT[a['componentType']]; nc = NC[a['type']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0); st = bv.get('byteStride'); isz = np.dtype(dt).itemsize * nc
    if st and st != isz:
        raw = np.frombuffer(BIN, np.uint8, a['count'] * st, off).reshape(a['count'], st)[:, :isz].copy()
        out = raw.view(dt).reshape(a['count'], nc)
    else:
        out = np.frombuffer(BIN, dt, a['count'] * nc, off).reshape(a['count'], nc).copy()
    if a.get('normalized'):
        out = out.astype(np.float64) / np.iinfo(dt).max
    return out


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_q(m):
    """Quaternion [x, y, z, w] of a rotation matrix."""
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1) * 2; w = .25 * s; x = (m[2, 1] - m[1, 2]) / s; y = (m[0, 2] - m[2, 0]) / s; z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; w = (m[2, 1] - m[1, 2]) / s; x = .25 * s; y = (m[0, 1] + m[1, 0]) / s; z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; w = (m[0, 2] - m[2, 0]) / s; x = (m[0, 1] + m[1, 0]) / s; y = .25 * s; z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; w = (m[1, 0] - m[0, 1]) / s; x = (m[0, 2] + m[2, 0]) / s; y = (m[1, 2] + m[2, 1]) / s; z = .25 * s
    q = np.array([x, y, z, w]); return q / np.linalg.norm(q)


def node_local(nd):
    if 'matrix' in nd:
        return np.array(nd['matrix'], dtype=np.float64).reshape(4, 4).T
    m = np.eye(4); s = nd.get('scale', [1, 1, 1]); r = qmat(nd.get('rotation', [0, 0, 0, 1]))
    m[:3, :3] = r * np.array(s); m[:3, 3] = nd.get('translation', [0, 0, 0])
    return m


def world_mats(j):
    parent = {}
    for i, nd in enumerate(j['nodes']):
        for c in nd.get('children', []): parent[c] = i
    memo = {}
    def g(i):
        if i not in memo: memo[i] = (g(parent[i]) if i in parent else np.eye(4)) @ node_local(j['nodes'][i])
        return memo[i]
    return [g(i) for i in range(len(j['nodes']))], parent


def rot_part(m):
    """Rotation of an affine matrix with a uniform scale; returns (R, scale)."""
    s = np.linalg.norm(m[:3, 0]); return m[:3, :3] / s, s


def qangle(a, b):
    """Angle in degrees between unit quaternions a and b (last axis)."""
    return np.degrees(2 * np.arccos(np.clip(np.abs((a * b).sum(-1)), 0, 1)))


def qslerp(a, b, t):
    d = (a * b).sum()
    if d < 0: b, d = -b, -d
    if d > .9995: r = a + (b - a) * t; return r / np.linalg.norm(r)
    th = np.arccos(d); return (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / np.sin(th)


SPIKE_RES, SPIKE_RATIO = 12, 3   # a glitch: 1-2 frames off the path between their neighbours by > 12 deg and > 3x that gap


def despike(q, b):
    """Repairs Meshy's glitch frames of bone b in a clip's rotations (n x bones x 4, in place): a run of 1 or 2 frames
    farther than SPIKE_RES degrees (and SPIKE_RATIO times the gap between the neighbours) from the slerp between the
    frames around it is replaced by that slerp. Only the Hips are checked (seen on 7/11/2026: the walk-back clip's hips
    twist by 20 degrees for 2 frames and back, which flicks the feet); the limbs' fast strikes look alike and are real.
    Returns the repaired runs as (first, last)."""
    n = len(q); fixed = []; i = 0
    while i < n - 2:
        for L in (1, 2):
            j = i + L + 1
            if j >= n: continue
            gap = qangle(q[i, b], q[j, b]); res = max(qangle(q[i + k, b], qslerp(q[i, b], q[j, b], k / (L + 1))) for k in range(1, L + 1))
            if res > SPIKE_RES and res > SPIKE_RATIO * gap:
                for k in range(1, L + 1): q[i + k, b] = qslerp(q[i, b], q[j, b], k / (L + 1))
                fixed.append((i + 1, i + L)); break
        i += 1
    return fixed


def main(rig_path, anim_dir, out_dir):
    name = os.path.basename(os.path.normpath(out_dir)); os.makedirs(out_dir, exist_ok=True)
    j, BIN = read_glb(rig_path)
    G, parent = world_mats(j)
    skin = j['skins'][0]; joints = skin['joints']; nb = len(joints)
    names = [j['nodes'][k]['name'] for k in joints]; index = {k: i for i, k in enumerate(joints)}
    IBM = acc(j, BIN, skin['inverseBindMatrices']).reshape(nb, 4, 4).transpose(0, 2, 1).astype(np.float64)
    mesh_node = next(i for i, nd in enumerate(j['nodes']) if 'skin' in nd and 'mesh' in nd)
    pr = j['meshes'][j['nodes'][mesh_node]['mesh']]['primitives'][0]; at = pr['attributes']
    P = acc(j, BIN, at['POSITION']).astype(np.float64); N = acc(j, BIN, at['NORMAL']).astype(np.float64)
    UV = acc(j, BIN, at['TEXCOORD_0']).astype(np.float32); JN = acc(j, BIN, at['JOINTS_0']).astype(np.int64)
    WT = acc(j, BIN, at['WEIGHTS_0']).astype(np.float64); IDX = acc(j, BIN, pr['indices']).reshape(-1).astype(np.int64)
    WT /= np.maximum(WT.sum(1, keepdims=True), 1e-12)
    # Bind: every joint's G @ IBM must be the same matrix (the mesh's world transform at bind time).
    J = np.array([G[k] @ IBM[i] for i, k in enumerate(joints)])
    assert np.abs(J - J[0]).max() < 1e-3, 'joints disagree on the bind transform'
    M = J[0]; R0, _ = rot_part(M)
    Pw = P @ M[:3, :3].T + M[:3, 3]; Nw = N @ R0.T; Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12)
    # Bones in world space (metres): translation and rotation without the Armature's scale.
    bt = np.array([G[k][:3, 3] for k in joints]); bR = [rot_part(G[k])[0] for k in joints]
    hips = names.index('Hips'); off = np.array([-bt[hips][0], -Pw[:, 1].min(), -bt[hips][2]])
    Pw += off; bt = bt + off
    bpar = [index.get(parent.get(k), -1) for k in joints]
    assert all(p < i for i, p in enumerate(bpar)), 'parents must come first'
    bones = []
    for i in range(nb):
        p = bpar[i]
        if p < 0: lt, lR = bt[i], bR[i]
        else: lt, lR = bR[p].T @ (bt[i] - bt[p]), bR[p].T @ bR[i]
        bones.append({'n': names[i], 'p': p, 't': [round(float(v), 6) for v in lt], 'q': [round(float(v), 7) for v in mat_q(lR)]})
    # The head's normals turned toward a sphere around it (the outline and the toon bands follow them).
    hw = (JN == names.index('Head')) * WT; hv = hw.sum(1) >= .5
    if hv.any():
        c = Pw[hv].mean(0); d = Pw[hv] - c; d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
        n2 = Nw[hv] * (1 - HEAD_ROUND) + d * HEAD_ROUND; Nw[hv] = n2 / np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-12)
    # Limb points: the centre of the vertices that mostly follow the limb's bones, in the first bone's local frame.
    limbs = {}
    for l, (b, group) in LIMBS.items():
        w = sum(((JN == names.index(g)) * WT).sum(1) for g in group); sel = w >= LIMB_W
        c = Pw[sel].mean(0); i = names.index(b)
        limbs[l] = {'b': b, 'p': [round(float(v), 5) for v in bR[i].T @ (c - bt[i])]}
    # Clips: local rotations of every bone (rest where a bone is not animated) and the Hips' local position.
    rest_q = np.array([b['q'] for b in bones], dtype=np.float64)
    Ga = G[parent[joints[hips]]] if joints[hips] in parent else np.eye(4)   # the Armature above the Hips
    clips = {}
    for fn in sorted(os.listdir(anim_dir), key=lambda s: int(s[1:-4]) if s[1:-4].isdigit() else 0):
        if not (fn.startswith('a') and fn.endswith('.glb')): continue
        cid = fn[:-4]; aj, AB = read_glb(os.path.join(anim_dir, fn)); an = aj['animations'][0]
        anames = [nd.get('name') for nd in aj['nodes']]
        tracks = {}; n = None
        for ch in an['channels']:
            s = an['samplers'][ch['sampler']]; t = acc(aj, AB, s['input']).reshape(-1); v = acc(aj, AB, s['output']).astype(np.float64)
            assert s.get('interpolation', 'LINEAR') == 'LINEAR' and np.allclose(np.diff(t), 1 / 30, atol=2e-3), cid + ' is not 30 fps linear'
            n = len(t) if n is None else n; assert len(t) == n, cid + ' tracks of different lengths'
            tracks[(anames[ch['target']['node']], ch['target']['path'])] = v
        q = np.repeat(rest_q[None], n, 0)
        for i, bn in enumerate(names):
            if (bn, 'rotation') in tracks: q[:, i] = tracks[(bn, 'rotation')]
        q[:, hips] = np.array([mat_q(rot_part(Ga)[0] @ qmat(r)) for r in q[:, hips]])
        rep = despike(q, hips)
        if rep: print('  %s: Hips glitch frames repaired: %s' % (cid, ', '.join('%d-%d' % r for r in rep)))
        hraw = tracks.get(('Hips', 'translation'))
        h = (hraw @ Ga[:3, :3].T + Ga[:3, 3] + off) if hraw is not None else np.repeat(bt[hips][None], n, 0)
        clips[cid] = {'name': an.get('name', cid).split('|')[1] if '|' in an.get('name', '') else an.get('name', cid), 'n': n, 'fps': 30,
                      'q': q.astype(np.float32), 'h': h.astype(np.float32)}
    # The binary: mesh blocks, then the clips; every block on a 4-byte boundary.
    blob = bytearray(); lay = {}
    def put(arr):
        while len(blob) % 4: blob.append(0)
        o = len(blob); blob.extend(np.ascontiguousarray(arr).tobytes()); return [o, int(arr.size)]
    nv = len(Pw)
    mesh = {'verts': nv, 'tris': len(IDX) // 3, 'pos': put(Pw.astype(np.float32)), 'nor': put(Nw.astype(np.float32)),
            'uv': put(UV), 'jnt': put(JN.astype(np.uint8)), 'wgt': put(WT.astype(np.float32)),
            'idx': put(IDX.astype(np.uint32 if nv > 65535 else np.uint16))}
    cl = {}
    for cid, c in clips.items():
        cl[cid] = {'name': c['name'], 'n': c['n'], 'fps': 30, 'q': put(c['q']), 'h': put(c['h'])}
    meta = {'v': 1, 'height': round(float(Pw[:, 1].max()), 4), 'bones': bones, 'mesh': mesh, 'clips': cl, 'limbs': limbs, 'head': 'head_end'}
    open(os.path.join(out_dir, name + '.bin'), 'wb').write(bytes(blob))
    json.dump(meta, open(os.path.join(out_dir, name + '.json'), 'w'), separators=(',', ':'))
    img = j['images'][0]; ibv = j['bufferViews'][img['bufferView']]
    im = Image.open(io.BytesIO(BIN[ibv.get('byteOffset', 0):ibv.get('byteOffset', 0) + ibv['byteLength']])).convert('RGB')
    if max(im.size) > TEX_SIZE: im = im.resize((TEX_SIZE, TEX_SIZE), Image.LANCZOS)
    im.save(os.path.join(out_dir, name + '.jpg'), quality=TEX_Q, optimize=True)
    print('%s: %d bones, %d verts, %d tris, %d clips, height %.3f m, bin %d B, jpg %d B' % (
        name, nb, nv, len(IDX) // 3, len(cl), meta['height'], len(blob), os.path.getsize(os.path.join(out_dir, name + '.jpg'))))


if __name__ == '__main__':
    if len(sys.argv) != 4: sys.exit(__doc__)
    main(*sys.argv[1:])
