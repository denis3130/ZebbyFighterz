#!/usr/bin/env python3
"""The look of a new Meshy fighter (10/11/2026: Kael, from Denis's drawing of his body without hair or clothes,
docs/ref/personaggi/kael_base.png), without Ren's own parts (his drawn face, his sash, his new head): what every
fighter needs to fight as Ren does.

- the fingers' bones (the Meshy API's skeleton has none, 24 bones: Denis asked for "le ossa anche sulle dita"): 3 per
  finger and thumb from the mesh, the skin on them, the fist (ren_look.finger_rig: the same as Ren's);
- the outline's width per vertex: thin on the front of the face and on the fingers, none at the thumbs' roots and on
  the palms, ramped on the hands (ren_look's LINE_* rules);
- the light's normals smoothed (ren_look.smooth_normals: NOR_ITER rounds, the hands HAND_NOR_ITER);
- no flat light (the drawing is not painted on him yet).
Writes OUT_DIR/<name>_look.json + .bin in ren_look's layout (e_model.js mdLookData reads it).

usage: python3 tools/char_look.py PACKAGE_DIR OUT_DIR"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ren_look import (finger_rig, smooth_normals, qm, LINE_FACE, LINE_FINGER, LINE_THUMB, LINE_PALM, LINE_RAMP)


def main(pkg, out):
    name = os.path.basename(os.path.normpath(pkg))
    m = json.load(open(os.path.join(pkg, name + '.json'))); B = open(os.path.join(pkg, name + '.bin'), 'rb').read(); me = m['mesh']
    f = lambda a, dt=np.float32: np.frombuffer(B, dt, a[1], a[0])
    P = f(me['pos']).reshape(-1, 3).astype(np.float64); N = f(me['nor']).reshape(-1, 3).astype(np.float64)
    J = f(me['jnt'], np.uint8).reshape(-1, 4); W = f(me['wgt']).reshape(-1, 4); UV = f(me['uv']).reshape(-1, 2)
    I = f(me['idx'], np.uint16 if me['verts'] < 65536 else np.uint32).reshape(-1, 3).astype(np.int64)
    bones = m['bones']; idx = {b['n']: i for i, b in enumerate(bones)}
    G = [None] * len(bones)
    for i, b in enumerate(bones):
        Mi = np.eye(4); Mi[:3, :3] = qm(b['q']); Mi[:3, 3] = b['t']; G[i] = Mi if b['p'] < 0 else G[b['p']] @ Mi
    fingers, jn, wn, palms, thumb_root, on_finger, first, weld, E = finger_rig(P, J, W, I, bones, idx, G)
    if len(bones) + len(fingers) > 255: sys.exit('too many bones for uint8 skin indices')
    # the outline (as ren_look's): thin on the face's front skin and the fingers, none at the thumbs' roots and the palms
    tex = np.asarray(Image.open(os.path.join(pkg, name + '.jpg')).convert('RGB')).astype(int); ts = tex.shape[0]
    col = tex[np.clip((UV[:, 1] * ts).astype(int), 0, ts - 1), np.clip((UV[:, 0] * ts).astype(int), 0, ts - 1)]
    wh = ((J == idx['Head']) * W).sum(1)
    skin = (col[:, 0] > 150) & (col[:, 1] > 95) & (col[:, 0] - col[:, 2] > 50)
    face = (wh >= .5) & (N[:, 2] > .15) & skin
    line = np.ones(len(P), np.float32); line[face] = LINE_FACE
    line = np.minimum(line, 1 - (1 - LINE_FINGER) * on_finger).astype(np.float32)
    web = (thumb_root > LINE_THUMB[0]) & (thumb_root < LINE_THUMB[1]); line[web] = 0
    inner = np.zeros(len(P), bool)
    for w, pn in palms: inner |= (w + on_finger > .5) & (N @ pn > LINE_PALM)
    line[inner] = 0
    hw = sum(((J == idx[s + 'Hand']) * W).sum(1) for s in ('Left', 'Right')); nw = len(first)
    hwm = np.zeros(nw); np.maximum.at(hwm, weld, hw); lwm = np.full(nw, 9.); np.minimum.at(lwm, weld, line)
    z = np.nonzero((lwm < .01) & (hwm > .3))[0]; Le = np.linalg.norm(P[first][E[:, 0]] - P[first][E[:, 1]], axis=1)
    Gr = coo_matrix((np.r_[Le, Le, np.full(len(z), 1e-9)], (np.r_[E[:, 0], E[:, 1], np.full(len(z), nw)], np.r_[E[:, 1], E[:, 0], z])), shape=(nw + 1, nw + 1)).tocsr()
    cap = np.where(hwm > .3, np.clip(dijkstra(Gr, indices=nw)[:nw] / LINE_RAMP, 0, 1), 1.)
    line = np.minimum(line, cap[weld]).astype(np.float32)
    print('outline thinned on', int(face.sum()), 'face and', int((on_finger > 0).sum()), 'finger vertices; none on', int(web.sum()), 'of the thumbs\' roots and', int(inner.sum()), 'of the palms')
    flat = np.zeros(len(P), np.float32)
    blob = line.tobytes(); oj = len(blob); blob += jn.astype(np.uint8).tobytes(); ow = len(blob); blob += wn.astype(np.float32).tobytes()
    of = len(blob); blob += flat.tobytes()
    nsm = smooth_normals(P, I, np.clip(hw / .5, 0, 1)); blob += b'\0' * (-len(blob) % 4); onor = len(blob); blob += nsm.tobytes()
    look = {'v': 3, 'fingers': fingers, 'skin': [[oj, int(jn.size)], [ow, int(wn.size)]], 'line': [0, int(line.size)],
            'nor': [onor, int(nsm.size)], 'flat': [of, int(flat.size)]}
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, name + '_look.bin'), 'wb').write(blob)
    json.dump(look, open(os.path.join(out, name + '_look.json'), 'w'), separators=(',', ':'))
    print('look %d B, %d finger bones' % (len(blob), len(fingers)))


if __name__ == '__main__':
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(*sys.argv[1:])
