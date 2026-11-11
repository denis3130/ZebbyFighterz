#!/usr/bin/env python3
"""Anime character cut-out (IS-Net "isnet-anime", run on the CPU with onnxruntime): the alpha matte of the figure in a
reference panel, so the interface's placeholder characters are real layers instead of rectangles of painted background.

usage: python3 tools/cutout_anime.py IN.png OUT_mask.png [--model PATH]
       (python module: matte(pil_image, model_path) -> PIL 'L' mask, same size)

Needs `pip install onnxruntime` and the model of the rembg release
(https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-anime.onnx), path in --model or $ISNET_ANIME.
"""
import os, sys
import numpy as np
from PIL import Image

SIZE = 1024
MEAN = (0.485, 0.456, 0.406)
_SESS = {}


def matte(img, model=None):
    import onnxruntime as ort
    model = model or os.environ.get('ISNET_ANIME', '')
    if model not in _SESS:
        _SESS[model] = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
    s = _SESS[model]
    a = np.asarray(img.convert('RGB').resize((SIZE, SIZE), Image.LANCZOS)).astype(np.float32)
    a = a / max(1.0, a.max())
    x = np.stack([(a[..., c] - MEAN[c]) for c in range(3)])[None].astype(np.float32)
    p = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    p = (p - p.min()) / (p.max() - p.min() + 1e-6)
    return Image.fromarray((p * 255).astype(np.uint8)).resize(img.size, Image.LANCZOS)


if __name__ == '__main__':
    a = sys.argv[1:]
    model = None
    if '--model' in a: i = a.index('--model'); model = a[i + 1]; del a[i:i + 2]
    matte(Image.open(a[0]), model).save(a[1])
