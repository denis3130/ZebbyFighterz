"""Minimal single-primitive GLB reader/writer for the Meshy models (positions, normals, uvs, indices, one embedded image)."""
import json, struct, io
import numpy as np
CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
def read(path):
    b = open(path, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    o = 20 + n; bl = struct.unpack('<I', b[o:o + 4])[0]; BIN = b[o + 8:o + 8 + bl]
    def acc(i):
        a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]; dt = CT[a['componentType']]; nc = NC[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        return np.frombuffer(BIN, dt, a['count'] * nc, off).reshape(a['count'], nc).copy()
    pr = j['meshes'][0]['primitives'][0]
    img = j['images'][0]; ibv = j['bufferViews'][img['bufferView']]
    return dict(j=j, pos=acc(pr['attributes']['POSITION']).astype(np.float64), nor=acc(pr['attributes']['NORMAL']).astype(np.float64),
                uv=acc(pr['attributes']['TEXCOORD_0']).astype(np.float64), idx=acc(pr['indices']).reshape(-1, 3).astype(np.int64),
                img=BIN[ibv.get('byteOffset', 0):ibv.get('byteOffset', 0) + ibv['byteLength']], mime=img.get('mimeType', 'image/jpeg'))
def write(path, m, pos, nor, uv, idx, img=None, mime=None):
    j = m['j']; img = m['img'] if img is None else img; mime = m['mime'] if mime is None else mime
    pos = pos.astype(np.float32); nor = nor.astype(np.float32); uv = uv.astype(np.float32)
    idx = idx.reshape(-1).astype(np.uint32 if len(pos) > 65535 else np.uint16)
    blobs = [idx.tobytes(), pos.tobytes(), nor.tobytes(), uv.tobytes(), img]; out = bytearray(); views = []
    for i, bb in enumerate(blobs):
        while len(out) % 4: out.append(0)
        v = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(bb)}
        if i == 0: v['target'] = 34963
        elif i < 4: v['target'] = 34962
        views.append(v); out += bb
    while len(out) % 4: out.append(0)
    node = {k: v for k, v in j['nodes'][0].items() if k in ('matrix', 'rotation', 'scale', 'translation')}; node['mesh'] = 0
    g = {'asset': {'version': '2.0', 'generator': 'voidrise glbio'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [node],
         'meshes': [{'primitives': [{'attributes': {'POSITION': 1, 'NORMAL': 2, 'TEXCOORD_0': 3}, 'indices': 0, 'mode': 4, 'material': 0}]}],
         'materials': j['materials'], 'textures': j['textures'], 'samplers': j.get('samplers', []),
         'images': [{'mimeType': mime, 'bufferView': 4}],
         'accessors': [{'bufferView': 0, 'componentType': 5125 if idx.dtype == np.uint32 else 5123, 'count': int(idx.size), 'type': 'SCALAR'},
                       {'bufferView': 1, 'componentType': 5126, 'count': len(pos), 'type': 'VEC3', 'min': pos.min(0).tolist(), 'max': pos.max(0).tolist()},
                       {'bufferView': 2, 'componentType': 5126, 'count': len(pos), 'type': 'VEC3'},
                       {'bufferView': 3, 'componentType': 5126, 'count': len(pos), 'type': 'VEC2'}],
         'bufferViews': views, 'buffers': [{'byteLength': len(out)}]}
    js = json.dumps(g, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    open(path, 'wb').write(struct.pack('<III', 0x46546C67, 2, 28 + len(js) + len(out)) + struct.pack('<II', len(js), 0x4E4F534A) + js
                           + struct.pack('<II', len(out), 0x004E4942) + bytes(out))
def raycast_z(P, T, ox, oy):
    """Rays from +z toward -z at points (ox, oy): for every ray, all hits as (t-order) lists of (z, tri). Vectorised Moller-Trumbore."""
    v0, v1, v2 = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    e1, e2 = v1 - v0, v2 - v0; d = np.array([0, 0, -1.0])
    h = np.cross(np.broadcast_to(d, e2.shape), e2); a = (e1 * h).sum(1)
    ok = np.abs(a) > 1e-12; f = np.where(ok, 1 / np.where(ok, a, 1), 0)
    zt = P[:, 2].max() + 1; res = []
    for x, y in zip(ox, oy):
        o = np.array([x, y, zt]); s = o - v0; u = f * (s * h).sum(1)
        q = np.cross(s, e1); v = f * (q @ d); t = f * (e2 * q).sum(1)
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        ids = np.nonzero(hit)[0]; zs = zt - t[ids]; order = np.argsort(-zs)
        res.append([(zs[k], ids[k], u[ids[k]], v[ids[k]]) for k in order])
    return res
