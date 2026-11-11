#!/usr/bin/env python3
"""Builds the game's images from the references in docs/ref/ (needs Pillow).

usage: python3 tools/make_assets.py

  assets/arena/cascata.jpg       the arena backdrop (1672x941 JPG, at most 600 KB)
  assets/arena/cascata_mask.png  where the water flows (836x471 grayscale; 255 = full effect)
  assets/ui/ren_face.jpg         HUD portraits (160x160 JPG)
  assets/ui/kael_face.jpg
build.py embeds every file under assets/ in the page as a data URI.
"""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, 'docs', 'ref')
OUT = os.path.join(ROOT, 'assets')

BACKDROP = (1672, 941)
BACKDROP_KB = 600
# The waterfall in backdrop pixels; from FOAM_Y down the mask fades to FOAM_MIN at FOAM_Y + FOAM_H (calmer foam).
WATER = [(672, 254), (1242, 247), (1240, 420), (1185, 470), (1165, 560), (1160, 640), (1080, 672), (820, 672),
         (705, 640), (676, 560)]
FOAM_Y, FOAM_H, FOAM_MIN = 590, 82, .4
MASK_BLUR, MASK_SIZE = 5, (836, 471)
# Portrait crops (left, top, right, bottom) of the character sheets, scaled to FACE x FACE.
FACES = {'ren': (392, 40, 632, 280), 'kael': (392, 70, 632, 310)}
FACE = 160


def out(*parts):
    p = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def backdrop():
    im = Image.open(os.path.join(REF, 'sfondo-cascata.png')).convert('RGB')
    assert im.size == BACKDROP, im.size
    p = out('arena', 'cascata.jpg')
    im.save(p, 'JPEG', quality=82, optimize=True)
    kb = os.path.getsize(p) / 1024
    assert kb <= BACKDROP_KB, '%s is %.0f KB' % (p, kb)
    return p


def foam_rows():
    """One grayscale column scaled across the image: 255 above FOAM_Y, then max(FOAM_MIN, 1-(y-FOAM_Y)/FOAM_H*.6)."""
    col = Image.new('L', (1, BACKDROP[1]))
    col.putdata([255 if y < FOAM_Y else round(255 * max(FOAM_MIN, 1 - (y - FOAM_Y) / FOAM_H * .6))
                 for y in range(BACKDROP[1])])
    return col.resize(BACKDROP, Image.NEAREST)


def mask():
    m = Image.new('L', BACKDROP, 0)
    ImageDraw.Draw(m).polygon(WATER, fill=255)
    m = ImageChops.multiply(m, foam_rows())
    m = m.filter(ImageFilter.GaussianBlur(MASK_BLUR)).resize(MASK_SIZE, Image.BOX)
    p = out('arena', 'cascata_mask.png')
    m.save(p, 'PNG', optimize=True)
    return p


def faces():
    ps = []
    for name, box in FACES.items():
        im = Image.open(os.path.join(REF, 'personaggi', name + '.png')).convert('RGB')
        p = out('ui', name + '_face.jpg')
        im.crop(box).resize((FACE, FACE), Image.LANCZOS).save(p, 'JPEG', quality=85, optimize=True)
        ps.append(p)
    return ps


if __name__ == '__main__':
    for p in [backdrop(), mask()] + faces():
        im = Image.open(p)
        print('%-28s %4dx%-4d %-3s %6.1f KB' % (os.path.relpath(p, ROOT), im.size[0], im.size[1], im.mode,
                                               os.path.getsize(p) / 1024))
