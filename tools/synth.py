"""Guided image quilting (Efros & Freeman 2001, with a guide as in image analogies): fills the target pixels of a canvas
with blocks copied from a source picture, so a painted mountain goes on as more of itself (needs numpy).

A block is chosen where the source looks like what is already around it (the painting, or blocks placed before) and
where the source's guide (e.g. how far below the ridge, how high) matches the target's guide there; it is pasted
along a minimum-error cut through the overlap with the blocks before it (no visible seams), and never over the
painting itself (`known`). Blocks are placed outwards from what is filled, the most surrounded first.
"""
import numpy as np


def _valid_windows(valid, B):
    """Top-left positions (y, x) whose B x B window lies inside `valid` (integral image of the invalid pixels)."""
    bad = np.pad((~valid).astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    s = bad[B:, B:] - bad[:-B, B:] - bad[B:, :-B] + bad[:-B, :-B]
    return np.argwhere(s == 0)


def _cut_path(E, axis):
    """Minimum-cost path through E across `axis` (0: a path down the rows, one column per row; 1: along the columns,
    one row per column). Returns the path's index per row (axis 0) or per column (axis 1)."""
    if axis == 1:
        return _cut_path(E.T, 0)
    n, m = E.shape
    C = E.copy()
    back = np.zeros((n, m), np.int32)
    for i in range(1, n):
        prev = C[i - 1]
        l = np.r_[np.inf, prev[:-1]]
        r = np.r_[prev[1:], np.inf]
        stack = np.stack([l, prev, r])
        k = stack.argmin(0)
        C[i] += stack[k, np.arange(m)]
        back[i] = np.arange(m) + k - 1
    path = np.zeros(n, np.int32)
    path[-1] = int(C[-1].argmin())
    for i in range(n - 1, 0, -1):
        path[i - 1] = back[i, path[i]]
    return path


def quilt(canvas, filled, known, target, guide_t, src, src_valid, guide_s, block=36, overlap=12, n_cand=2500,
          w_guide=1.0, tol=.06, seed=1, sub=2, log=None):
    """Fills canvas (H, W, C float32; modified in place) at the target pixels (H, W bool) not yet filled.

    filled (H, W bool): pixels with content (the painting, or placed before) - updated. known (H, W bool): never
    overwritten. guide_t (H, W, G) / guide_s (h, w, G): the guides, compared over the whole block; colours are
    compared over the block's filled pixels (every `sub` px). src (h, w, C) with src_valid (h, w bool): where whole
    blocks may be taken from. Among the n_cand candidates closest in guide at the block's centre, a block within
    (1 + tol) of the best cost is taken at random (variety). Returns the number of blocks placed."""
    rng = np.random.default_rng(seed)
    B, ov = block, overlap
    step = B - ov
    H, W, Cn = canvas.shape
    # pad everything by one block so windows never leave the arrays
    P = B
    cv = np.zeros((H + 2 * P, W + 2 * P, Cn), np.float32); cv[P:P + H, P:P + W] = canvas
    fl = np.zeros((H + 2 * P, W + 2 * P), bool); fl[P:P + H, P:P + W] = filled
    kn = np.ones((H + 2 * P, W + 2 * P), bool); kn[P:P + H, P:P + W] = known        # outside: never written
    tg = np.zeros((H + 2 * P, W + 2 * P), bool); tg[P:P + H, P:P + W] = target
    G = guide_t.shape[2]
    gt = np.zeros((H + 2 * P, W + 2 * P, G), np.float32); gt[P:P + H, P:P + W] = guide_t
    gt[:P] = gt[P:P + 1]; gt[-P:] = gt[-P - 1:-P]; gt[:, :P] = gt[:, P:P + 1]; gt[:, -P:] = gt[:, -P - 1:-P]

    pos = _valid_windows(src_valid, B)                          # candidate source windows
    if not len(pos):
        raise ValueError('no valid source window')
    c = B // 2
    gcen = guide_s[pos[:, 0] + c, pos[:, 1] + c]                # their guide at the centre
    gy, gx = np.mgrid[0:B:4, 0:B:4]                             # guide compared on a 4 px grid
    gsrc = guide_s[pos[:, 0, None, None] + gy, pos[:, 1, None, None] + gx].reshape(len(pos), -1)

    ys = np.arange(P - step, P + H, step); xs = np.arange(P - step, P + W, step)
    todo = {(y, x) for y in ys for x in xs if (tg[y:y + B, x:x + B] & ~fl[y:y + B, x:x + B]).any()}
    placed = 0
    while todo:
        # the most surrounded block first (the share of its window already filled)
        best_k, best_f = None, -1.
        for k in todo:
            f = fl[k[0]:k[0] + B, k[1]:k[1] + B].mean()
            if f > best_f:
                best_k, best_f = k, f
        todo.discard(best_k)
        y, x = best_k
        F = fl[y:y + B, x:x + B]; K = kn[y:y + B, x:x + B]; T = tg[y:y + B, x:x + B] & ~F
        if not T.any():
            continue
        win = cv[y:y + B, x:x + B]
        g = gt[y:y + B, x:x + B]
        # candidates: closest in guide at the centre (plus a few random ones)
        d = ((gcen - g[c, c]) ** 2).sum(1)
        n = min(n_cand, len(pos))
        idx = np.argpartition(d, n - 1)[:n] if n < len(pos) else np.arange(len(pos))
        idx = np.r_[idx, rng.integers(0, len(pos), 200)]
        cost = w_guide * ((gsrc[idx] - g[gy, gx].reshape(1, -1)) ** 2).sum(1)
        fy, fx = np.nonzero(F)
        if len(fy):
            sel = slice(None, None, sub)
            fy, fx = fy[sel], fx[sel]
            S = src[pos[idx, 0, None] + fy, pos[idx, 1, None] + fx]          # (n, nF, C)
            cost = cost + ((S - win[fy, fx][None]) ** 2).sum((1, 2)) * sub
        lo = cost.min()
        ok = np.nonzero(cost <= lo * (1 + tol) + 1e-6)[0]
        j = idx[rng.choice(ok)]
        sy, sx = pos[j]
        patch = src[sy:sy + B, sx:sx + B]
        # where blocks placed before overlap this one: a minimum-error cut on each side keeps the old block outside it
        take = np.ones((B, B), bool)
        syn = F & ~K
        if syn.any():
            E = ((patch - win) ** 2).sum(2) * syn + (~syn) * 1e-3
            if syn[:, :ov].any():                                 # left strip: a path down it, old block on its left
                p = _cut_path(E[:, :ov], 0)
                take[:, :ov] &= np.arange(ov)[None, :] >= p[:, None]
            if syn[:, -ov:].any():                                # right strip
                p = _cut_path(E[:, -ov:], 0)
                take[:, -ov:] &= np.arange(ov)[None, :] <= p[:, None]
            if syn[:ov, :].any():                                 # top strip: a path along it, old block above it
                p = _cut_path(E[:ov, :], 1)
                take[:ov, :] &= np.arange(ov)[:, None] >= p[None, :]
            if syn[-ov:, :].any():                                # bottom strip
                p = _cut_path(E[-ov:, :], 1)
                take[-ov:, :] &= np.arange(ov)[:, None] <= p[None, :]
        take = (take & syn) | T                                  # never the painting; always the empty target pixels
        win[take] = patch[take]
        F[take] = True
        placed += 1
        if log and placed % 200 == 0:
            log('  %d blocks placed, %d to go' % (placed, len(todo)))
    canvas[:] = cv[P:P + H, P:P + W]
    filled[:] = fl[P:P + H, P:P + W]
    return placed
