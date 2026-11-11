#!/usr/bin/env python3
"""Placeholder images of the interface, in layers, from the references in docs/ref/ (needs Pillow with WebP).

usage: python3 tools/make_ui_assets.py

They stand in for the final art (to be generated as separate high-resolution pieces): the same file names, so the
final images go in without code changes. Written to assets/ui/ (WebP); build.py embeds them in the page.

  sky.webp            1600x900  the far layer: docs/ref/sfondo-rovine.png turned to dusk (violet, warm light low in the
                                middle, the blue sky into a sunset), its near ruins and floor blurred away (they are ruins.webp)
  ruins.webp          1600x900  the near layer, transparent: the arches at the sides and the stone floor, same dusk grade
  clouds.webp         1600x300  drifting cloud bands (drawn), transparent
  fog1.webp, fog2.webp 1600x300 fog bands (drawn), transparent
  ren_full.webp, kael_full.webp  height 900: the character sheets (docs/ref/personaggi/) without their grey background
  face_ren/kael/astra/raigon.webp 256x256  portraits; silhouette.webp 256x256 (a coming fighter)
  arena_cascata.webp, arena_rovine.webp 640x360; arena_montagne/tetti/foresta/deserto.webp 320x140
  intro_clash.webp    1280x720  the clash of the opening (docs/ref/ui/00-*.png, first panel)
Prints each file's size; fails if they add up to more than BUDGET_KB (the page keeps the interface under 3 MB as base64).
"""
import os, sys
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, 'docs', 'ref')
OUT = os.path.join(ROOT, 'assets', 'ui')
BUDGET_KB = 2200
Q = 82
RNG = np.random.default_rng(7)

# The near parts of sfondo-rovine.png (1672x941): the arch at each side and the floor, as polygons (x, y).
NEAR = [[(0, 40), (300, 40), (300, 380), (250, 720), (0, 720)],
        [(1330, 20), (1672, 20), (1672, 720), (1380, 720), (1330, 400)],
        [(0, 700), (1672, 700), (1672, 941), (0, 941)]]
NEAR_FEATHER = 6
FACES = {'ren': ('personaggi/ren.png', (392, 40, 632, 280)), 'kael': ('personaggi/kael.png', (392, 70, 632, 310)),
         'astra': ('ui/04-pass-missioni-archivio-sblocco.png', (420, 22, 556, 158)),
         'raigon': ('ui/04-pass-missioni-archivio-sblocco.png', (676, 62, 796, 182))}
THUMBS = {'montagne': (42, 272, 218, 348), 'tetti': (238, 272, 410, 348), 'foresta': (432, 272, 605, 348), 'deserto': (626, 272, 800, 348)}


def save(img, name):
    p = os.path.join(OUT, name)
    img.save(p, 'WEBP', quality=Q, method=6)
    return os.path.getsize(p)


def dusk(rgb):
    """The painting at dusk: desaturated, violet, a warm light low in the middle; saturated blue sky becomes a sunset."""
    a = np.asarray(rgb).astype(np.float32) / 255
    h, w, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = (.3 * r + .59 * g + .11 * b)[..., None]
    out = (a * .3 + lum * .7) * np.array([.40, .33, .56]) * 1.18
    out = np.clip((out - .5) * 1.12 + .5 - .04, 0, 1)   # a little more contrast, a little darker
    yy = np.linspace(0, 1, h)[:, None, None]
    xx = np.linspace(-1, 1, w)[None, :, None]
    warm = np.clip(1 - np.sqrt((xx * .62) ** 2 + ((yy - .58) * 1.9) ** 2), 0, 1) ** 1.6   # the sun low behind the middle
    out = out + warm * np.array([.95, .45, .16]) * (.3 + .9 * lum) * .75
    # sky: how blue and bright a pixel is (0..1) -> mixed toward a sunset gradient that keeps the clouds' light
    sky = np.clip(((b - r) - .18) / .25, 0, 1)[..., None] * np.clip((lum - .35) / .3, 0, 1) * np.clip(1.15 - yy * 1.6, 0, 1)
    top, mid, hor = np.array([.16, .12, .27]), np.array([.46, .27, .40]), np.array([.98, .58, .32])
    t = yy[..., 0][..., None] * np.ones((1, w, 1))
    sunset = np.where(t < .5, top + (mid - top) * (t / .5), mid + (hor - mid) * np.clip((t - .5) / .35, 0, 1))
    out = out * (1 - sky) + sunset * (.55 + .7 * lum) * sky
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def layers_from_ruins():
    src = Image.open(os.path.join(REF, 'sfondo-rovine.png')).convert('RGB')
    graded = dusk(src)
    mask = Image.new('L', src.size, 0)
    d = ImageDraw.Draw(mask)
    for poly in NEAR:
        d.polygon(poly, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(NEAR_FEATHER))
    # far layer: where the near parts were, a strong blur of the picture (a parallax step shows soft colour, not a second arch)
    far = Image.composite(graded.filter(ImageFilter.GaussianBlur(28)), graded, mask.filter(ImageFilter.MaxFilter(9)))
    near = graded.convert('RGBA')
    near.putalpha(mask)
    size = (1600, 900)
    return far.resize(size, Image.LANCZOS), near.resize(size, Image.LANCZOS)


def noise_band(size, scale, alpha, tint, seed):
    """Soft cloud / fog band: blurred noise at a few scales, fading at the top and bottom."""
    w, h = size
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    for k, s in enumerate(scale):
        n = Image.fromarray((rng.random((max(2, h // s), max(2, w // s))) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += np.asarray(n.filter(ImageFilter.GaussianBlur(s / 2)), np.float32) / 255 / (k + 1)
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)
    y = np.linspace(0, 1, h)[:, None]
    edge = np.clip(np.sin(np.pi * y), 0, 1) ** 1.5
    a = np.clip((acc - .38) * 2.2, 0, 1) * edge * alpha
    # wrap the left and right edges into each other, so the band can scroll forever without a seam
    blend = np.linspace(0, 1, w // 8)[None, :]
    a[:, :w // 8] = a[:, :w // 8] * blend + a[:, -w // 8:] * (1 - blend)
    a[:, -w // 8:] = a[:, :w // 8]
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = tint
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')


def cutout(path):
    """A character sheet without its flat grey background: flood fill from the border over pixels near the corner colour."""
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int32)
    h, w, _ = a.shape
    bg = np.array([a[5, 5], a[5, w - 6], a[h - 6, 5], a[h - 6, w - 6]]).mean(0)
    near = np.sqrt(((a - bg) ** 2).sum(2)) < 26
    seen = np.zeros((h, w), bool)
    q = deque((y, x) for x in range(w) for y in (0, h - 1) if near[y, x])
    q.extend((y, x) for y in range(h) for x in (0, w - 1) if near[y, x])
    for y, x in q:
        seen[y, x] = True
    while q:
        y, x = q.popleft()
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < h and 0 <= xx < w and near[yy, xx] and not seen[yy, xx]:
                seen[yy, xx] = True
                q.append((yy, xx))
    alpha = Image.fromarray(np.where(seen, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))
    out = im.convert('RGBA')
    out.putalpha(alpha)
    return out.crop(alpha.getbbox())


def main():
    os.makedirs(OUT, exist_ok=True)
    sizes = {}
    far, near = layers_from_ruins()
    sizes['sky.webp'] = save(far, 'sky.webp')
    sizes['ruins.webp'] = save(near, 'ruins.webp')
    sizes['clouds.webp'] = save(noise_band((1600, 300), (96, 48, 24), .7, (196, 150, 170), 3), 'clouds.webp')
    sizes['fog1.webp'] = save(noise_band((1600, 300), (120, 60, 30), .55, (176, 160, 196), 5), 'fog1.webp')
    sizes['fog2.webp'] = save(noise_band((1600, 300), (160, 80, 40), .45, (150, 134, 176), 9), 'fog2.webp')
    for c in ('ren', 'kael'):
        im = cutout(os.path.join(REF, 'personaggi', c + '.png'))
        im = im.resize((round(im.width * 900 / im.height), 900), Image.LANCZOS)
        sizes[c + '_full.webp'] = save(im, c + '_full.webp')
        if c == 'ren':
            sil = Image.new('RGBA', im.size, (28, 24, 38, 255))
            a = im.getchannel('A')
            sil.putalpha(a)
            edge = a.filter(ImageFilter.MaxFilter(7))
            rim = Image.new('RGBA', im.size, (58, 50, 72, 255))
            rim.putalpha(edge)
            rim.alpha_composite(sil)
            head = rim.crop((im.width // 2 - 170, 0, im.width // 2 + 170, 340)).resize((256, 256), Image.LANCZOS)
            sizes['silhouette.webp'] = save(head, 'silhouette.webp')
    for c, (f, box) in FACES.items():
        sizes['face_%s.webp' % c] = save(Image.open(os.path.join(REF, f)).convert('RGB').crop(box).resize((256, 256), Image.LANCZOS), 'face_%s.webp' % c)
    sizes['arena_cascata.webp'] = save(Image.open(os.path.join(REF, 'sfondo-cascata.png')).convert('RGB').resize((640, 360), Image.LANCZOS), 'arena_cascata.webp')
    sizes['arena_rovine.webp'] = save(Image.open(os.path.join(REF, 'sfondo-rovine.png')).convert('RGB').resize((640, 360), Image.LANCZOS), 'arena_rovine.webp')
    sheet = Image.open(os.path.join(REF, 'ui', '01-arena-vs-arcade-versus.png')).convert('RGB')
    for k, box in THUMBS.items():
        sizes['arena_%s.webp' % k] = save(sheet.crop(box).resize((320, 140), Image.LANCZOS), 'arena_%s.webp' % k)
    clash = Image.open(os.path.join(REF, 'ui', '00-intro-titolo-menu-personaggi.png')).convert('RGB').crop((0, 0, 836, 412))
    sizes['intro_clash.webp'] = save(clash.resize((1280, 631), Image.LANCZOS), 'intro_clash.webp')
    total = 0
    for k in sorted(sizes):
        total += sizes[k]
        print('%-22s %6.1f KB' % (k, sizes[k] / 1024))
    print('total %.1f KB (budget %d KB)' % (total / 1024, BUDGET_KB))
    if total / 1024 > BUDGET_KB:
        sys.exit('over budget')


if __name__ == '__main__':
    main()
