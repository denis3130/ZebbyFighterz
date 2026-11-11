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
  ren_full.webp, kael_full.webp  Ren of the main menu and Kael of the settings in docs/ref/ui/ (Denis: only the characters
                      of those references, never the A-pose sheets), their painted background faded out at the edges
  ren_vs.webp, kael_vs.webp      the two faces of the VS reference; title_ren.webp, title_kael.webp the title's profiles
  face_ren/kael/astra/raigon.webp 256x256  portraits (VS and pass references); silhouette.webp 256x256 (drawn: a coming fighter)
  arena_cascata.webp, arena_rovine.webp 640x360; arena_montagne/tetti/foresta/deserto.webp 320x140
  intro_clash.webp    1280x720  the clash of the opening (docs/ref/ui/00-*.png, first panel)
Prints each file's size; fails if they add up to more than BUDGET_KB (the page keeps the interface under 3 MB as base64).
"""
import os, sys
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
U0, U1, U3, U4 = 'ui/00-intro-titolo-menu-personaggi.png', 'ui/01-arena-vs-arcade-versus.png', 'ui/03-profilo-impostazioni-pausa-vittoria.png', 'ui/04-pass-missioni-archivio-sblocco.png'
FACES = {'ren': (U1, (980, 92, 1172, 284)), 'kael': (U1, (1392, 66, 1592, 266)),
         'astra': (U4, (420, 22, 556, 158)), 'raigon': (U4, (676, 62, 796, 182))}
# Characters cut from the references (sheet, box, polygon in box coordinates kept opaque, feather px, output height). The
# polygon follows the figure loosely; outside it the painted background fades away.
CROPS = {
    'ren_full': (U0, (290, 470, 836, 941), [(70, 16), (360, 16), (378, 100), (322, 168), (420, 250), (546, 300), (546, 471), (44, 471), (64, 330), (84, 120)], 26, 900),
    'kael_full': (U3, (850, 52, 1132, 470), [(44, 14), (236, 14), (256, 120), (256, 418), (26, 418), (26, 140)], 22, 900),
    'ren_vs': (U1, (836, 54, 1196, 338), [(0, 0), (330, 0), (360, 150), (360, 284), (0, 284)], 22, 600),
    'kael_vs': (U1, (1306, 0, 1672, 338), [(30, 0), (366, 0), (366, 338), (0, 338), (0, 160)], 22, 600),
    'title_ren': (U0, (900, 0, 1092, 300), [(0, 0), (168, 0), (168, 270), (0, 270)], 24, 600),
    'title_kael': (U0, (1416, 0, 1600, 320), [(22, 0), (184, 0), (184, 290), (22, 290)], 24, 600),
}
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


def crop_masked(sheet, box, poly, feather, height):
    """A figure cut from a reference panel: inside the polygon opaque, the edges and the rest fading to transparent."""
    im = Image.open(os.path.join(REF, sheet)).convert('RGB').crop(box)
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather))
    # the panel's own edge where the figure is cut by it (the bottom, a side) stays opaque: only the inner sides fade
    out = im.convert('RGBA')
    out.putalpha(m)
    return out.resize((round(out.width * height / out.height), height), Image.LANCZOS)


def silhouette(size=256):
    """A coming fighter: a dark head-and-shoulders shape with a faint violet rim."""
    s = size * 4
    m = Image.new('L', (s, s), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((s * .34, s * .16, s * .66, s * .52), fill=255)                      # head
    d.polygon([(s * .44, s * .48), (s * .56, s * .48), (s * .6, s * .62), (s * .4, s * .62)], fill=255)   # neck
    d.ellipse((s * .08, s * .58, s * .92, s * 1.4), fill=255)                      # shoulders
    m = m.resize((size, size), Image.LANCZOS)
    rim = Image.new('RGBA', (size, size), (70, 58, 92, 255)); rim.putalpha(m.filter(ImageFilter.MaxFilter(5)))
    body = Image.new('RGBA', (size, size), (26, 22, 36, 255)); body.putalpha(m)
    bg = Image.new('RGBA', (size, size), (20, 17, 28, 255))
    bg.alpha_composite(rim); bg.alpha_composite(body)
    return bg.convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    sizes = {}
    far, near = layers_from_ruins()
    sizes['sky.webp'] = save(far, 'sky.webp')
    sizes['ruins.webp'] = save(near, 'ruins.webp')
    sizes['clouds.webp'] = save(noise_band((1600, 300), (96, 48, 24), .7, (196, 150, 170), 3), 'clouds.webp')
    sizes['fog1.webp'] = save(noise_band((1600, 300), (120, 60, 30), .55, (176, 160, 196), 5), 'fog1.webp')
    sizes['fog2.webp'] = save(noise_band((1600, 300), (160, 80, 40), .45, (150, 134, 176), 9), 'fog2.webp')
    for name, (sheet, box, poly, feather, height) in CROPS.items():
        sizes[name + '.webp'] = save(crop_masked(sheet, box, poly, feather, height), name + '.webp')
    sizes['silhouette.webp'] = save(silhouette(), 'silhouette.webp')
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
