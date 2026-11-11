#!/usr/bin/env python3
"""Anime-style upscaling (Real-ESRGAN, run on the CPU with ncnn), for the interface's placeholder pictures cut from the
small reference panels (docs/ref/ui/: each panel is about 836x470, too small for a phone at 2-3x pixel density).

usage: python3 tools/upscale_anime.py IN.png OUT.png [--model realesrgan-x4plus-anime] [--models DIR]
       (python module: upscale(pil_image, model, models_dir) -> pil_image 4x)

Needs `pip install ncnn` and the models of the official Real-ESRGAN release
(https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip, folder
models/), whose path goes in --models or $ESR_MODELS. The picture is cut in overlapping tiles so memory stays small.
"""
import os, sys
import numpy as np
from PIL import Image

TILE, PAD = 160, 12


def _net(model, models_dir):
    import ncnn
    net = ncnn.Net()
    net.opt.use_vulkan_compute = False
    net.opt.num_threads = os.cpu_count() or 4
    net.load_param(os.path.join(models_dir, model + '.param'))
    net.load_model(os.path.join(models_dir, model + '.bin'))
    return net


def upscale(img, model='realesrgan-x4plus-anime', models_dir=None, scale=4):
    """img: PIL RGB or RGBA. The colour goes through the network; an alpha channel is resized with Lanczos."""
    import ncnn
    models_dir = models_dir or os.environ.get('ESR_MODELS', '')
    net = _net(model, models_dir)
    alpha = img.getchannel('A') if img.mode == 'RGBA' else None
    rgb = np.asarray(img.convert('RGB')).astype(np.float32) / 255
    h, w, _ = rgb.shape
    out = np.zeros((h * scale, w * scale, 3), np.float32)
    for y0 in range(0, h, TILE):
        for x0 in range(0, w, TILE):
            y1, x1 = min(h, y0 + TILE), min(w, x0 + TILE)
            py0, px0, py1, px1 = max(0, y0 - PAD), max(0, x0 - PAD), min(h, y1 + PAD), min(w, x1 + PAD)
            tile = np.ascontiguousarray(rgb[py0:py1, px0:px1].transpose(2, 0, 1))
            ex = net.create_extractor()
            ex.input('data', ncnn.Mat(tile))
            _, res = ex.extract('output')
            r = np.array(res).transpose(1, 2, 0)
            oy, ox = (y0 - py0) * scale, (x0 - px0) * scale
            out[y0 * scale:y1 * scale, x0 * scale:x1 * scale] = r[oy:oy + (y1 - y0) * scale, ox:ox + (x1 - x0) * scale]
    res = Image.fromarray((np.clip(out, 0, 1) * 255 + .5).astype(np.uint8))
    if alpha is not None:
        res = res.convert('RGBA'); res.putalpha(alpha.resize(res.size, Image.LANCZOS))
    return res


if __name__ == '__main__':
    a = sys.argv[1:]
    model, mdir = 'realesrgan-x4plus-anime', None
    if '--model' in a: i = a.index('--model'); model = a[i + 1]; del a[i:i + 2]
    if '--models' in a: i = a.index('--models'); mdir = a[i + 1]; del a[i:i + 2]
    upscale(Image.open(a[0]), model, mdir).save(a[1])
