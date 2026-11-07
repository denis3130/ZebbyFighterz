"""Shorten the bangs that hang over the eyes: hair vertices in front of the face, between the tips (Y_MIN) and the hair
root (Y_TOP), are pulled up toward the root so the tips end at Y_TO (just above the painted brows). Face map from front rays.
Usage: python3 lift_bangs.py in.glb out.glb Y_TOP Y_MIN Y_TO X0 X1   (model units, front = +z)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glbio, numpy as np
src, dst = sys.argv[1], sys.argv[2]; Y_TOP, Y_MIN, Y_TO, X0, X1 = map(float, sys.argv[3:8])
m = glbio.read(src); P, UV, T = m['pos'].copy(), m['uv'], m['idx']
ymax = P[:, 1].max(); H = ymax - P[:, 1].min()
head = np.nonzero(P[T].mean(1)[:, 1] > ymax - .2 * H)[0]; Th = T[head]
# the face surface depth: on each front ray, the last hit still in the front half of the head
X = np.linspace(X0 - .03, X1 + .03, 90); Y = np.linspace(Y_TOP + .01, Y_MIN - .02, 90); ZF = np.full((len(Y), len(X)), np.nan)
for i, y in enumerate(Y):
    for k, r in enumerate(glbio.raycast_z(P, Th, X, [y] * len(X))):
        rr = [h for h in r if h[0] > .02]
        if rr: ZF[i, k] = rr[-1][0]
def zface(x, y):
    i = np.clip(np.round((Y[0] - y) / (Y[0] - Y[-1]) * (len(Y) - 1)).astype(int), 0, len(Y) - 1)
    k = np.clip(np.round((x - X[0]) / (X[-1] - X[0]) * (len(X) - 1)).astype(int), 0, len(X) - 1)
    return ZF[i, k]
def smooth(e0, e1, v): t = np.clip((v - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
x, y, z = P[:, 0], P[:, 1], P[:, 2]
zf = zface(x, y)
wx = smooth(X0 - .02, X0, x) * (1 - smooth(X1, X1 + .02, x))
wz = np.where(np.isnan(zf), 0, smooth(.002, .008, z - np.nan_to_num(zf, nan=9)))
wy = (y < Y_TOP) & (y > Y_MIN - .03)
w = wx * wz * wy
k = (Y_TOP - Y_TO) / (Y_TOP - Y_MIN)
ynew = Y_TOP - (Y_TOP - np.maximum(y, Y_MIN - .03)) * k
# vertices that share a position move together (UV seams): use the max weight per position
key = np.round(m['pos'] * 1e5).astype(np.int64); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.reshape(-1)
wmax = np.zeros(inv.max() + 1); np.maximum.at(wmax, inv, w); w = wmax[inv]
P[:, 1] = y + w * (ynew - y)
print('moved verts', int((w > .01).sum()), 'of', len(P), 'max lift', float((w * (ynew - y)).max()))
# smooth normals per position
fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]]); VN = np.zeros((inv.max() + 1, 3))
for c in range(3): np.add.at(VN, inv[T[:, c]], fn)
VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)
glbio.write(dst, m, P, VN[inv], UV, T); print(dst)
