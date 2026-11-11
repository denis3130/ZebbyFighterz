#!/usr/bin/env python3
"""Placeholder images of the interface, in layers, ONLY from Denis's interface references docs/ref/ui/00-04 (Denis: no other
image, never the A-pose sheets nor the older backdrops). Needs Pillow with WebP.

usage: python3 tools/make_ui_assets.py

They stand in for the final art (to be generated as separate high-resolution pieces): the same file names, so the
final images go in without code changes. Written to assets/ui/ (WebP); build.py embeds them in the page.

  sky.webp            the backdrop: the dusk ruins with the arch behind «Scegli l'arena» (01, first panel)
  clouds.webp, fog1.webp, fog2.webp  drifting cloud and fog bands, drawn here (no picture)
  ren_full.webp, kael_full.webp  Ren of the main menu (00) and Kael of the settings (03), their painted background faded out
  ren_vs.webp, kael_vs.webp      the two faces of the VS (01), also the title's two sides
  ren_win.webp        Ren with the fist up of «Vittoria» (03, last panel), without the logo and the buttons
  face_ren/kael/astra/raigon.webp 256x256  portraits (VS and pass references); silhouette.webp 256x256 (drawn: a coming fighter)
  arena_rovine.webp   the same dusk ruins; arena_montagne/tetti/foresta/deserto.webp the arena thumbnails (01)
  card_arcade.webp, card_online.webp  the two mode cards of the main menu (00)
  intro_clash.webp    the clash of the opening (00, first panel)
No picture of «La Grande Cascata» exists in the references: its card shows a snapshot of the real arena taken in the game.
No near ruins layer (ruins.webp) yet: the references paint each scene in one piece; the final art brings it.
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

U0, U1, U3, U4 = 'ui/00-intro-titolo-menu-personaggi.png', 'ui/01-arena-vs-arcade-versus.png', 'ui/03-profilo-impostazioni-pausa-vittoria.png', 'ui/04-pass-missioni-archivio-sblocco.png'
FACES = {'ren': (U1, (980, 92, 1172, 284)), 'kael': (U1, (1392, 66, 1592, 266)),
         'astra': (U4, (420, 22, 556, 158)), 'raigon': (U4, (676, 62, 796, 182))}
# Characters cut from the references (sheet, box, polygon in box coordinates kept opaque, feather px, output height). The
# polygon follows the figure loosely; outside it the painted background fades away.
CROPS = {
    'ren_full': (U0, (290, 470, 836, 941), [(70, 16), (360, 16), (378, 100), (322, 168), (420, 250), (546, 300), (546, 471), (44, 471), (64, 330), (84, 120)], 26, 900),
    'kael_full': (U3, (850, 52, 1132, 470), [(44, 14), (236, 14), (256, 120), (256, 418), (26, 418), (26, 140)], 22, 900),
    'ren_vs': (U1, (836, 54, 1196, 338), [(0, 0), (330, 0), (360, 150), (360, 284), (0, 284)], 22, 600),
    'ren_win': (U3, (836, 525, 1241, 852), [(0, 0), (372, 0), (372, 300), (0, 300)], 22, 700),
    'kael_vs': (U1, (1306, 0, 1672, 338), [(30, 0), (366, 0), (366, 338), (0, 338), (0, 160)], 22, 600),
}
ARENA_BG = (300, 0, 836, 262)   # the clean dusk ruins above the arena cards in 01
CARDS = {'arcade': (34, 740, 146, 800), 'online': (162, 740, 274, 800)}   # the pictures of the two mode cards in 00
THUMBS = {'montagne': (42, 272, 218, 348), 'tetti': (238, 272, 410, 348), 'foresta': (432, 272, 605, 348), 'deserto': (626, 272, 800, 348)}


def save(img, name):
    p = os.path.join(OUT, name)
    img.save(p, 'WEBP', quality=Q, method=6)
    return os.path.getsize(p)


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
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))   # transparent around the shape (slots and empty sides draw their own ground)
    out.alpha_composite(rim); out.alpha_composite(body)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    sizes = {}
    arena_bg = Image.open(os.path.join(REF, U1)).convert('RGB').crop(ARENA_BG)
    sizes['sky.webp'] = save(arena_bg.resize((1600, round(1600 * arena_bg.height / arena_bg.width)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(.6)), 'sky.webp')
    sizes['clouds.webp'] = save(noise_band((1600, 300), (96, 48, 24), .7, (196, 150, 170), 3), 'clouds.webp')
    sizes['fog1.webp'] = save(noise_band((1600, 300), (120, 60, 30), .55, (176, 160, 196), 5), 'fog1.webp')
    sizes['fog2.webp'] = save(noise_band((1600, 300), (160, 80, 40), .45, (150, 134, 176), 9), 'fog2.webp')
    for name, (sheet, box, poly, feather, height) in CROPS.items():
        sizes[name + '.webp'] = save(crop_masked(sheet, box, poly, feather, height), name + '.webp')
    sizes['silhouette.webp'] = save(silhouette(), 'silhouette.webp')
    for c, (f, box) in FACES.items():
        sizes['face_%s.webp' % c] = save(Image.open(os.path.join(REF, f)).convert('RGB').crop(box).resize((256, 256), Image.LANCZOS), 'face_%s.webp' % c)
    sizes['arena_rovine.webp'] = save(arena_bg.resize((640, round(640 * arena_bg.height / arena_bg.width)), Image.LANCZOS), 'arena_rovine.webp')
    menu_sheet = Image.open(os.path.join(REF, U0)).convert('RGB')
    for k, box in CARDS.items():
        sizes['card_%s.webp' % k] = save(menu_sheet.crop(box).resize((320, round(320 * (box[3] - box[1]) / (box[2] - box[0]))), Image.LANCZOS), 'card_%s.webp' % k)
    sheet = Image.open(os.path.join(REF, U1)).convert('RGB')
    for k, box in THUMBS.items():
        sizes['arena_%s.webp' % k] = save(sheet.crop(box).resize((320, 140), Image.LANCZOS), 'arena_%s.webp' % k)
    clash = Image.open(os.path.join(REF, U0)).convert('RGB').crop((0, 0, 836, 412))
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
