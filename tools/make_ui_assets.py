#!/usr/bin/env python3
"""The interface's placeholder images, in layers, ONLY from Denis's interface references docs/ref/ui/00-04 (Denis: no
other image, never the A-pose sheets nor the older backdrops). Every picture taken from a reference is made 4x sharper
(Real-ESRGAN anime, tools/upscale_anime.py) and each character is cut out of its painted background (IS-Net anime,
tools/cutout_anime.py): the models come from tools/fetch_ui_models.sh, the results are cached in ~/.cache/voidrise-ui.

usage: python3 tools/make_ui_assets.py

They stand in for the final art (to be generated as separate high-resolution pieces): the same file names, so the
final images go in without code changes. Written to assets/ui/ (WebP); build.py embeds them in the page.

  sky.webp            the backdrop: the dusk ruins with the arch behind «Scegli l'arena» (01, first panel)
  clouds.webp, fog1.webp, fog2.webp  drifting cloud and fog bands, drawn here (no picture)
  ren_full.webp, kael_full.webp  Ren of the main menu (00) and Kael of the settings (03), cut out
  ren_vs.webp, kael_vs.webp      the two faces of the VS (01), also the title's two sides, cut out
  ren_win.webp        Ren with the fist up of «Vittoria» (03, last panel), cut out
  face_ren/kael/astra/raigon.webp 320x320  portraits (VS and pass references); silhouette.webp 256x256 (drawn: a coming fighter)
  arena_rovine.webp   the same dusk ruins; arena_montagne/tetti/foresta/deserto.webp the arena thumbnails (01)
  card_arcade.webp, card_online.webp  the two mode cards of the main menu (00)
  intro_ren.webp, intro_kael.webp  the two halves of the clash of the opening (00, first panel), cut out, split where
                      Ren's wrist wraps meet Kael's fist (their places in the panel: CFG.ui.intro)
No picture of «La Grande Cascata» exists in the references: its card shows a snapshot of the real arena taken in the game.
No near ruins layer (ruins.webp) yet: the references paint each scene in one piece; the final art brings it.
Prints each file's size; fails if they add up to more than BUDGET_KB (the page keeps the interface under 3 MB as base64).
"""
import hashlib, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the sharp pictures: Real-ESRGAN anime 4x and the IS-Net anime cut-out (tools/fetch_ui_models.sh), cached because the
# CPU takes about half a minute per panel
MODELS = os.environ.get('VOIDRISE_MODELS', os.path.join(os.path.expanduser('~'), '.cache', 'voidrise-models'))
CACHE = os.environ.get('VOIDRISE_UI_CACHE', os.path.join(os.path.expanduser('~'), '.cache', 'voidrise-ui'))
REF = os.path.join(ROOT, 'docs', 'ref')
OUT = os.path.join(ROOT, 'assets', 'ui')
BUDGET_KB = 2200
Q = 82
RNG = np.random.default_rng(7)

U0, U1, U3, U4 = 'ui/00-intro-titolo-menu-personaggi.png', 'ui/01-arena-vs-arcade-versus.png', 'ui/03-profilo-impostazioni-pausa-vittoria.png', 'ui/04-pass-missioni-archivio-sblocco.png'
FACES = {'ren': (U1, (980, 92, 1172, 284)), 'kael': (U1, (1392, 66, 1592, 266)),
         'astra': (U4, (420, 22, 556, 158)), 'raigon': (U4, (676, 62, 796, 182))}
ARENA_BG = (300, 0, 836, 262)   # the clean dusk ruins above the arena cards in 01
CARDS = {'arcade': (34, 740, 146, 800), 'online': (162, 740, 274, 800)}   # the pictures of the two mode cards in 00
# The opening's clash (00, first panel), 4x: split at INTRO_CUT (x where Ren's wrist wraps end and Kael's fist starts),
# the two halves overlapping by INTRO_LAP px (Kael is drawn over Ren); the panel's own edges fade (INTRO_FADE: share of the
# width or height for Ren's left, Kael's right and the bottom), so no straight cut shows; INTRO_H = the whole panel's height.
# The characters of the menus, cut out of the references 4x sharper (name: sheet, box, output height px)
CUTS = {
    'ren_full': (U0, (290, 470, 836, 941), 1200),
    'kael_full': (U3, (850, 52, 1132, 470), 1200),
    'ren_vs': (U1, (836, 54, 1196, 338), 1100),
    'kael_vs': (U1, (1306, 0, 1672, 338), 1100),
    'ren_win': (U3, (836, 525, 1241, 852), 1200),
}
KEEP_SHARE = .15
EDGE_FADE = .06
INTRO = (U0, (0, 0, 836, 412))
INTRO_CUT, INTRO_LAP, INTRO_H = 1752, 8, 1240
INTRO_FADE = {'left': .03, 'right': .04, 'bottom': .06}
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


def hd(sheet, box):
    """The reference box 4x sharper (Real-ESRGAN anime), cached in CACHE (the key holds the box and a hash of the reference
    picture and of the models, so a changed reference or model makes a new one)."""
    h = hashlib.sha1(open(os.path.join(REF, sheet), 'rb').read())
    for m in ('realesrgan-x4plus-anime.bin', 'isnet-anime.onnx'):
        p = os.path.join(MODELS, m)
        h.update(('%s:%d' % (m, os.path.getsize(p) if os.path.exists(p) else 0)).encode())
    key = '%s_%d_%d_%d_%d_%s' % ((os.path.basename(sheet)[:2],) + tuple(box) + (h.hexdigest()[:10],))
    p = os.path.join(CACHE, key + '_x4.png')
    if not os.path.exists(p):
        if not os.path.exists(os.path.join(MODELS, 'realesrgan-x4plus-anime.bin')):
            sys.exit('models missing: run bash tools/fetch_ui_models.sh')
        from upscale_anime import upscale
        os.makedirs(CACHE, exist_ok=True)
        upscale(Image.open(os.path.join(REF, sheet)).convert('RGB').crop(box), 'realesrgan-x4plus-anime', MODELS).save(p)
    return Image.open(p).convert('RGB'), key


def cut_out(img, key):
    """The figure of a 4x picture with a clean edge: the IS-Net matte (cached), tightened, and the edge colours taken from
    just inside the figure (no halo of the painted background around it). Returns RGBA."""
    p = os.path.join(CACHE, key + '_mask.png')
    if not os.path.exists(p):
        from cutout_anime import matte
        matte(img, os.path.join(MODELS, 'isnet-anime.onnx')).save(p)
    a = np.asarray(Image.open(p).convert('L')).astype(np.float32) / 255
    rgb = np.asarray(img).astype(np.float32) / 255
    blur = lambda x, r: np.asarray(Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255
    a2 = np.clip((a - .2) / .65, 0, 1)
    inner = (a > .97).astype(np.float32)
    den = blur(inner, 6)[..., None]
    fg = np.stack([blur(rgb[..., c] * inner, 6) for c in range(3)], -1) / np.maximum(den, 1e-3)
    w = np.sqrt(a2)[..., None]
    rgb = np.where((a[..., None] < .97) & (den > 1e-3), rgb * w + np.clip(fg, 0, 1) * (1 - w), rgb)
    out = np.dstack([rgb, a2])
    return (np.clip(out, 0, 1) * 255 + .5).astype(np.uint8)


def keep_main(a):
    """The alpha of a cut-out without the bits that are not the figure (another small figure, an icon of the reference's
    interface): keeps the largest connected shape, what touches it and any shape at least KEEP_SHARE as large."""
    small = Image.fromarray(a).resize((a.shape[1] // 4, a.shape[0] // 4), Image.BILINEAR)
    m = np.asarray(small) > 128
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    sizes, n = [0], 0
    for y0 in range(h):
        for x0 in range(w):
            if not m[y0, x0] or lab[y0, x0]: continue
            n += 1; lab[y0, x0] = n; st = [(y0, x0)]; cnt = 0
            while st:
                y, x = st.pop(); cnt += 1
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n; st.append((yy, xx))
            sizes.append(cnt)
    if n <= 1: return a
    big = int(np.argmax(sizes))
    near = np.asarray(Image.fromarray(((lab == big) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 0
    keep = np.zeros(n + 1, bool)
    for i in range(1, n + 1): keep[i] = sizes[i] >= KEEP_SHARE * sizes[big] or bool(np.any(near & (lab == i)))
    # what is dropped: the shapes not kept, grown a little (their soft edge goes too)
    drop = Image.fromarray((((lab > 0) & ~keep[lab]) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).resize((a.shape[1], a.shape[0]), Image.BILINEAR)
    return (a * (1 - np.asarray(drop).astype(np.float32) / 255)).astype(np.uint8)


def cut_figure(name, sheet, box, height):
    """A character from a reference: 4x sharper, cut out, only the figure, cropped to it, height px tall. Where the figure
    runs into the left or right edge of the reference's box (cut by it), it fades out over EDGE_FADE of the width, so no
    straight vertical cut shows in the middle of a screen (the top and bottom cuts sit on the screen's edges)."""
    up, key = hd(sheet, box)
    px = cut_out(up, key)
    px[..., 3] = keep_main(px[..., 3])
    a = px[..., 3].astype(np.float32)
    W = a.shape[1]
    x = np.arange(W)[None, :] / W
    if (a[:, 0] > 128).mean() > .05: a *= np.clip(x / EDGE_FADE, 0, 1)
    if (a[:, -1] > 128).mean() > .05: a *= np.clip((1 - x) / EDGE_FADE, 0, 1)
    px[..., 3] = (a + .5).astype(np.uint8)
    ys, xs = np.where(px[..., 3] > 3)
    img = Image.fromarray(px[ys.min():ys.max() + 1, xs.min():xs.max() + 1], 'RGBA')
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def intro_pieces(sizes):
    """intro_ren.webp and intro_kael.webp; prints their boxes in the panel (fractions), to copy in CFG.ui.intro."""
    up, key = hd(*INTRO)
    px = cut_out(up, key)
    H, W = px.shape[:2]
    x, y = np.arange(W)[None, :] / W, np.arange(H)[:, None] / H
    a = px[..., 3].astype(np.float32) * np.clip((1 - y) / INTRO_FADE['bottom'], 0, 1)
    k = INTRO_H / H
    for name, keep in (('ren', (x < (INTRO_CUT + INTRO_LAP) / W) * np.clip(x / INTRO_FADE['left'], 0, 1)),
                       ('kael', (x >= (INTRO_CUT - INTRO_LAP) / W) * np.clip((1 - x) / INTRO_FADE['right'], 0, 1))):
        part = px.copy()
        part[..., 3] = (a * keep + .5).astype(np.uint8)
        ys, xs = np.where(part[..., 3] > 3)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        img = Image.fromarray(part[y0:y1, x0:x1], 'RGBA')
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
        sizes['intro_%s.webp' % name] = save(img, 'intro_%s.webp' % name)
        print('intro_%s box in the panel: [%.4f, %.4f, %.4f, %.4f]' % (name, x0 / W, y0 / H, x1 / W, y1 / H))
    print('intro panel aspect %.4f' % (W / H))


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
    arena_bg = hd(U1, ARENA_BG)[0]
    sizes['sky.webp'] = save(arena_bg.resize((1920, round(1920 * arena_bg.height / arena_bg.width)), Image.LANCZOS), 'sky.webp')
    sizes['clouds.webp'] = save(noise_band((1600, 300), (96, 48, 24), .7, (196, 150, 170), 3), 'clouds.webp')
    sizes['fog1.webp'] = save(noise_band((1600, 300), (120, 60, 30), .55, (176, 160, 196), 5), 'fog1.webp')
    sizes['fog2.webp'] = save(noise_band((1600, 300), (160, 80, 40), .45, (150, 134, 176), 9), 'fog2.webp')
    for name, (sheet, box, height) in CUTS.items():
        sizes[name + '.webp'] = save(cut_figure(name, sheet, box, height), name + '.webp')
    sizes['silhouette.webp'] = save(silhouette(), 'silhouette.webp')
    for c, (f, box) in FACES.items():
        sizes['face_%s.webp' % c] = save(hd(f, box)[0].resize((320, 320), Image.LANCZOS), 'face_%s.webp' % c)
    sizes['arena_rovine.webp'] = save(arena_bg.resize((640, round(640 * arena_bg.height / arena_bg.width)), Image.LANCZOS), 'arena_rovine.webp')
    for k, box in CARDS.items():
        sizes['card_%s.webp' % k] = save(hd(U0, box)[0].resize((320, round(320 * (box[3] - box[1]) / (box[2] - box[0]))), Image.LANCZOS), 'card_%s.webp' % k)
    for k, box in THUMBS.items():
        sizes['arena_%s.webp' % k] = save(hd(U1, box)[0].resize((320, 140), Image.LANCZOS), 'arena_%s.webp' % k)
    intro_pieces(sizes)
    total = 0
    for k in sorted(sizes):
        total += sizes[k]
        print('%-22s %6.1f KB' % (k, sizes[k] / 1024))
    print('total %.1f KB (budget %d KB)' % (total / 1024, BUDGET_KB))
    if total / 1024 > BUDGET_KB:
        sys.exit('over budget')


if __name__ == '__main__':
    main()
