"""Texture-preserving decimation of a single-primitive Meshy GLB: python3 decimate_glb.py in.glb out.glb TARGET_TRIANGLES
[FACE_TRIANGLES X0 X1 Y0 Y1 Z0 [LOW_TRIANGLES LOW_Y]]
Keeps the original texture and UVs (quadric edge collapse with texture), rebuilds smooth normals per position.
With FACE_*: the triangles in that box (their corners within x0..x1, y0..y1 and in front of z0, in the GLB's own units:
a face) keep FACE_TRIANGLES of the target, the rest takes the others (two passes, each on its own selection); with LOW_*,
the triangles all under LOW_Y outside the face's box (a bust's collar: its trim's edge came out in teeth) keep
LOW_TRIANGLES (a third pass)."""
import json, struct, sys
import numpy as np, pymeshlab

src, dst, target = sys.argv[1], sys.argv[2], int(sys.argv[3])
face = (int(sys.argv[4]), [float(v) for v in sys.argv[5:10]]) if len(sys.argv) >= 10 else None
low = (int(sys.argv[10]), float(sys.argv[11])) if len(sys.argv) >= 12 else None
b = open(src, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
o = 20 + n; bl = struct.unpack('<I', b[o:o + 4])[0]; BIN = b[o + 8:o + 8 + bl]
CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
def acc(i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]; dt = CT[a['componentType']]; nc = NC[a['type']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0); cnt = a['count']
    st = bv.get('byteStride'); isz = np.dtype(dt).itemsize * nc
    if st and st != isz:
        raw = np.frombuffer(BIN, np.uint8, cnt * st, off).reshape(cnt, st)[:, :isz].copy()
        return raw.view(dt).reshape(cnt, nc)
    return np.frombuffer(BIN, dt, cnt * nc, off).reshape(cnt, nc).copy()
assert len(j['meshes']) == 1 and len(j['meshes'][0]['primitives']) == 1, 'one mesh, one primitive expected'
pr = j['meshes'][0]['primitives'][0]
P = acc(pr['attributes']['POSITION']).astype(np.float64); UV = acc(pr['attributes']['TEXCOORD_0']).astype(np.float64)
I = acc(pr['indices']).reshape(-1, 3).astype(np.int64)
print('in: verts', len(P), 'tris', len(I))
# weld by position so decimation sees one connected surface; UVs ride on the face corners (wedges)
key = np.round(P * 1e5).astype(np.int64)
_, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.reshape(-1)
V = P[first]; F = inv[I].astype(np.int32); W = UV[I.reshape(-1)]
ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2]); F = F[ok]; W = W.reshape(-1, 3, 2)[ok].reshape(-1, 2)
# MeshLab marks wedge UVs as textured only when they come with a texture, so hand it an OBJ + MTL
import os, tempfile
td = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(dst)))
open(os.path.join(td, 't.png'), 'wb').write(b'')
uk, uinv = np.unique(np.round(W * 1e6).astype(np.int64), axis=0, return_inverse=True); uinv = uinv.reshape(-1)
UVu = uk / 1e6
with open(os.path.join(td, 'm.mtl'), 'w') as f: f.write('newmtl m\nmap_Kd t.png\n')
with open(os.path.join(td, 'm.obj'), 'w') as f:
    f.write('mtllib m.mtl\nusemtl m\n')
    f.write(''.join('v %.7f %.7f %.7f\n' % tuple(p) for p in V))
    f.write(''.join('vt %.7f %.7f\n' % tuple(t) for t in UVu))
    fv = F + 1; ft = uinv.reshape(-1, 3) + 1
    f.write(''.join('f %d/%d %d/%d %d/%d\n' % (a[0], b[0], a[1], b[1], a[2], b[2]) for a, b in zip(fv, ft)))
ms = pymeshlab.MeshSet(); ms.load_new_mesh(os.path.join(td, 'm.obj'))
print('loaded: tris', ms.current_mesh().face_number(), 'wedge uv', ms.current_mesh().has_wedge_tex_coord())
dec = dict(qualitythr=0.6, extratcoordw=1.0, preserveboundary=True, boundaryweight=1.0, optimalplacement=True, preservenormal=True, planarquadric=True)
if face:
    nf, (fx0, fx1, fy0, fy1, fz0) = face
    inbox = ' && '.join('(x%d > %r && x%d < %r && y%d > %r && y%d < %r && z%d > %r)' % (k, fx0, k, fx1, k, fy0, k, fy1, k, fz0) for k in range(3))
    ms.apply_filter('compute_selection_by_condition_per_face', condselect=inbox); n_in = ms.current_mesh().selected_face_number()
    nl = 0
    if low:
        nl, ly = low; lowbox = '(%s) && ((%s) == 0)' % (' && '.join('y%d < %r' % (k, ly) for k in range(3)), inbox)   # (muParser: no '!')
        ms.apply_filter('compute_selection_by_condition_per_face', condselect=lowbox); n_low = ms.current_mesh().selected_face_number()
        ms.apply_filter('compute_selection_by_condition_per_face', condselect='((%s) == 0) && ((%s) == 0)' % (inbox, lowbox))
        ms.apply_filter('meshing_decimation_quadric_edge_collapse_with_texture', targetfacenum=target - nf - nl, selected=True, **dec)   # (selected: the target is theirs)
        ms.apply_filter('compute_selection_by_condition_per_face', condselect=lowbox)
        print('low box: %d triangles -> %d' % (n_low, nl))
        ms.apply_filter('meshing_decimation_quadric_edge_collapse_with_texture', targetfacenum=nl, selected=True, **dec)
    else:
        ms.apply_filter('apply_selection_inverse', invfaces=True)
        ms.apply_filter('meshing_decimation_quadric_edge_collapse_with_texture', targetfacenum=target - nf, selected=True, **dec)   # (selected: the target is theirs)
    ms.apply_filter('compute_selection_by_condition_per_face', condselect=inbox)
    print('face box: %d triangles -> %d; the rest -> %d' % (n_in, nf, target - nf - nl))
    ms.apply_filter('meshing_decimation_quadric_edge_collapse_with_texture', targetfacenum=nf, selected=True, **dec)
    ms.apply_filter('set_selection_none')
elif target < len(F):
    ms.apply_filter('meshing_decimation_quadric_edge_collapse_with_texture', targetfacenum=target, **dec)
m = ms.current_mesh(); V2 = m.vertex_matrix(); F2 = m.face_matrix(); W2 = m.wedge_tex_coord_matrix().reshape(-1, 3, 2)
print('out: tris', len(F2))
# smooth normals per position (area weighted)
fn = np.cross(V2[F2[:, 1]] - V2[F2[:, 0]], V2[F2[:, 2]] - V2[F2[:, 0]])
VN = np.zeros_like(V2)
for c in range(3): np.add.at(VN, F2[:, c], fn)
VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)
# split vertices by (position, uv)
corner_v = F2.reshape(-1); corner_uv = W2.reshape(-1, 2)
k2 = np.concatenate([corner_v[:, None].astype(np.int64), np.round(corner_uv * 1e6).astype(np.int64)], axis=1)
_, cf, cinv = np.unique(k2, axis=0, return_index=True, return_inverse=True); cinv = cinv.reshape(-1)
pos = V2[corner_v[cf]].astype(np.float32); nor = VN[corner_v[cf]].astype(np.float32); uv = corner_uv[cf].astype(np.float32)
idx = cinv.astype(np.uint32 if len(pos) > 65535 else np.uint16)
print('out: verts', len(pos))
# write the GLB: geometry + the original image and material
img = j['images'][0]; ibv = j['bufferViews'][img['bufferView']]; IMG = BIN[ibv.get('byteOffset', 0):ibv.get('byteOffset', 0) + ibv['byteLength']]
blobs = [idx.tobytes(), pos.tobytes(), nor.tobytes(), uv.tobytes(), IMG]
out = bytearray(); views = []
for i, bb in enumerate(blobs):
    while len(out) % 4: out.append(0)
    v = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(bb)}
    if i == 0: v['target'] = 34963
    elif i < 4: v['target'] = 34962
    views.append(v); out += bb
while len(out) % 4: out.append(0)
g = {'asset': {'version': '2.0', 'generator': 'voidrise decimate_glb'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
     'nodes': [{k: v for k, v in j['nodes'][0].items() if k in ('mesh', 'matrix', 'rotation', 'scale', 'translation')}],
     'meshes': [{'primitives': [{'attributes': {'POSITION': 1, 'NORMAL': 2, 'TEXCOORD_0': 3}, 'indices': 0, 'mode': 4, 'material': 0}]}],
     'materials': j['materials'], 'textures': j['textures'], 'samplers': j.get('samplers', []),
     'images': [{'mimeType': img.get('mimeType', 'image/jpeg'), 'bufferView': 4}],
     'accessors': [{'bufferView': 0, 'componentType': 5125 if idx.dtype == np.uint32 else 5123, 'count': int(idx.size), 'type': 'SCALAR'},
                   {'bufferView': 1, 'componentType': 5126, 'count': len(pos), 'type': 'VEC3', 'min': pos.min(0).tolist(), 'max': pos.max(0).tolist()},
                   {'bufferView': 2, 'componentType': 5126, 'count': len(pos), 'type': 'VEC3'},
                   {'bufferView': 3, 'componentType': 5126, 'count': len(pos), 'type': 'VEC2'}],
     'bufferViews': views, 'buffers': [{'byteLength': len(out)}]}
g['nodes'][0]['mesh'] = 0
js = json.dumps(g, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
glb = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(out)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(out), 0x004E4942) + bytes(out)
open(dst, 'wb').write(glb); print(dst, len(glb))
import shutil; shutil.rmtree(td, ignore_errors=True)
