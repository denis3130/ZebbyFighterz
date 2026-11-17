#!/usr/bin/env python3
"""Kael's hands and wrists remade (17/11/2026; docs/superpowers/specs/2026-11-17-kael-mani-polso-design.md): the pieces
tools/kael_bust_attach.py writes beside his bust, as parts of his package (src/e_model.js mdPartData).

- crop_paint: Ren's paint cut out round his hands, pixel for pixel (no resampling: the hands keep his paint as on him).
- write_part: a part's json and bin (and its texture), in the bust's format."""
import json, os
import numpy as np


def crop_paint(img, uv, pad=4):
    """img (PIL) cropped to the pixels uv (n, 2) cover, pad pixels more on each side; uv remapped into the crop.
    The crop starts on whole pixels, so every texel keeps its colour and its place among its neighbours."""
    w, h = img.size; x, y = uv[:, 0] * w, uv[:, 1] * h
    x0, y0 = max(0, int(np.floor(x.min())) - pad), max(0, int(np.floor(y.min())) - pad)
    x1, y1 = min(w, int(np.ceil(x.max())) + pad), min(h, int(np.ceil(y.max())) + pad)
    return img.crop((x0, y0, x1, y1)), np.c_[(x - x0) / (x1 - x0), (y - y0) / (y1 - y0)]


def write_part(folder, name, arrays, extra=None, img=None, fmt='jpg'):
    """<folder>/<name>.json|.bin (and .jpg or .png): arrays in order, each as [byte offset, count] in the bin (4-byte
    aligned); 'idx' as uint16 under 65536 vertices, else uint32; 'jnt' as uint8; 'hide' an empty uint32 block unless
    given (mdPartData reads it); extra merged into the json."""
    pad = lambda b: b + b'\0' * (-len(b) % 4)
    n = len(arrays['pos']); blob = b''; jo = {'v': 1, 'verts': int(n), 'tris': int(len(arrays['idx']))}
    arrays = dict(arrays); arrays.setdefault('hide', np.zeros(0, np.uint32))
    for k, a in arrays.items():
        a = np.asarray(a)
        if k == 'idx': a = a.astype(np.uint16 if n < 65536 else np.uint32)
        elif k == 'jnt': a = a.astype(np.uint8)
        elif k in ('hide',): a = a.astype(np.uint32)
        elif k in ('near',): a = a.astype(np.int32)
        else: a = a.astype(np.float32)
        blob = pad(blob); jo[k] = [len(blob), int(a.size)]; blob += np.ascontiguousarray(a).tobytes()
    jo.update(extra or {})
    open(os.path.join(folder, name + '.bin'), 'wb').write(pad(blob))
    json.dump(jo, open(os.path.join(folder, name + '.json'), 'w'), separators=(',', ':'))
    if img is not None:
        if fmt == 'png': img.save(os.path.join(folder, name + '.png'), optimize=True)
        else: img.convert('RGB').save(os.path.join(folder, name + '.jpg'), quality=95)
