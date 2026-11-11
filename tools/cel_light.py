#!/usr/bin/env python3
"""A light baked into a head's paint as the drawings' cel shading (10/11/2026, Denis on Kael's new head: "è fatto bene ma
so che puoi fare di meglio, guarda bene queste immagini e rendi il modello 3d identico"): Meshy's texture came without
the drawings' shadows (it strips the lighting), the face flat where his images shade it under the bangs, on its side
and under the chin. One fixed light (L: toward it) gives each point of the head lit or in shadow: in shadow where its
surface turns away from the light (n . L under TERM) or where the head itself stands between it and the light (a depth
map seen from the light: the hair's shadow on the forehead, the jaw's on the neck). Projecting the images instead
doubled the drawing (tools/paint_head.py on Ren's eyes); a light is the same from every side.

Functions: zbuffer (triangles to the front-most depth per pixel), frame (a light's axes), shadow (per point: in
shadow?), occlusion (its cast part), view_depth (a scan camera's depth map, tools/sheet_scan.py's: which points a drawing's view sees)."""
import numpy as np


def zbuffer(U, V, D, I, W, H):
    """The front-most (largest) D per pixel of the triangles I (vertices at pixel coordinates U, V): H x W, -inf where none."""
    Z = np.full((H, W), -np.inf)
    u, v, d = U[I], V[I], D[I]
    x0 = np.clip(np.floor(u.min(1)).astype(int), 0, W - 1); x1 = np.clip(np.ceil(u.max(1)).astype(int), 0, W - 1)
    y0 = np.clip(np.floor(v.min(1)).astype(int), 0, H - 1); y1 = np.clip(np.ceil(v.max(1)).astype(int), 0, H - 1)
    den = (v[:, 1] - v[:, 2]) * (u[:, 0] - u[:, 2]) + (u[:, 2] - u[:, 1]) * (v[:, 0] - v[:, 2])
    for k in np.nonzero(np.abs(den) > 1e-12)[0]:
        gx, gy = np.meshgrid(np.arange(x0[k], x1[k] + 1), np.arange(y0[k], y1[k] + 1)); px, py = gx + .5, gy + .5
        a = ((v[k, 1] - v[k, 2]) * (px - u[k, 2]) + (u[k, 2] - u[k, 1]) * (py - v[k, 2])) / den[k]
        b = ((v[k, 2] - v[k, 0]) * (px - u[k, 2]) + (u[k, 0] - u[k, 2]) * (py - v[k, 2])) / den[k]
        c = 1 - a - b; ok = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6)
        if ok.any(): np.maximum.at(Z, (gy[ok], gx[ok]), (a * d[k, 0] + b * d[k, 1] + c * d[k, 2])[ok])
    return Z


def frame(L):
    """The light's axes: two across it and L itself (unit)."""
    l = np.asarray(L, float); l = l / np.linalg.norm(l)
    a = np.cross([0., 1., 0.], l) if abs(l[1]) < .95 else np.cross([1., 0., 0.], l); a /= np.linalg.norm(a)
    return a, np.cross(l, a), l


def shadow(Q, I, pos, nor, L, cell=.0004, bias=.0015, term=0.):
    """Per point (pos, its normal nor): True in the light's shadow. Q, I: the triangles casting it (m)."""
    return occlusion(Q, I, pos, L, cell, bias) | (nor @ frame(L)[2] < term)


def occlusion(Q, I, pos, L, cell=.0004, bias=.0015):
    """Per point: True where the triangles Q, I stand between it and the light."""
    a, b, l = frame(L)
    pu, pv, pd = Q @ a, Q @ b, Q @ l
    u0, v0 = pu.min() - 4 * cell, pv.min() - 4 * cell
    W, H = int((pu.max() - u0) / cell) + 8, int((pv.max() - v0) / cell) + 8
    Z = zbuffer((pu - u0) / cell, (pv - v0) / cell, pd, I, W, H)
    qu = np.clip(((pos @ a - u0) / cell).astype(int), 0, W - 1); qv = np.clip(((pos @ b - v0) / cell).astype(int), 0, H - 1)
    from scipy import ndimage
    Zm = ndimage.maximum_filter(np.where(np.isfinite(Z), Z, -1e9), size=3)   # (the front-most of the cell and its neighbours: no speckles at the edges)
    return pos @ l < Zm[qv, qu] - bias


def contact(pos, nor, casters, R, front=.0005, up=None, below=-.001, k=24, tree=None):
    """Per point (pos, normal nor): True where one of the casters (points) lies within R m of it and more than front m
    out of its surface (along nor): the drawings' shadow hugging the locks that lie over the skin, and in the hair the
    locks under other locks. With up (a direction), only casters not under the point by more than -below along it."""
    from scipy.spatial import cKDTree
    tree = tree or cKDTree(casters)
    d, j = tree.query(pos, k=k, distance_upper_bound=R); ok = np.isfinite(d)
    rel = casters[np.where(ok, j, 0)] - pos[:, None, :]
    hit = ok & ((rel * nor[:, None, :]).sum(2) > front)
    if up is not None: hit &= rel @ np.asarray(up, float) > below
    return hit.any(1)


def view_depth(Q, I, cam, W, H):
    """A scan camera's (tools/sheet_scan.py: yaw degrees, s px per m, cx, by px) depth map of the triangles and the
    points' projection: (Z, u(p), v(p), depth(p)) for any points p (a function)."""
    t = np.radians(cam['yaw']); s, cx, by = cam['s'], cam['cx'], cam['by']
    proj = lambda P: (cx + s * (P[:, 0] * np.cos(t) - P[:, 2] * np.sin(t)), by - s * P[:, 1], P[:, 0] * np.sin(t) + P[:, 2] * np.cos(t))
    U, V, D = proj(Q)
    return zbuffer(U, V, D, I, W, H), proj
