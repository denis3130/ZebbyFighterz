#!/usr/bin/env python3
"""Pose sheet of the side-0 fighter (the Meshy Ren): every act at 4 of its frames, cropped from the real game at
844x390 and laid out in a labelled grid, for a visual check of CFG.clips.

usage: python3 tools/pose_sheet.py OUT.png [moves|acts|all]   (default all; needs game_w.html from mk.sh)
Moves show frame 1, the end of startup, the first active frame and the middle of recovery; the other acts frames
chosen for them (air acts at take-off, rising, apex, falling).
"""
import asyncio, io, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox']
CHROME = next((c for c in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/opt/pw-browsers/chromium') if os.path.isfile(c)), None)
OTHER = [('idle', [1, 15, 30, 45]), ('walkF', [2, 6, 10, 14]), ('walkB', [2, 6, 10, 14]), ('dashF', [1, 5, 10, 15]),
         ('dashB', [1, 5, 10, 15]), ('crouch', [1, 4, 10, 20]), ('guard', [1, 4, 10, 20]), ('guardC', [1, 4, 10, 20]),
         ('block', [1, 3, 6, 10]), ('blockLow', [1, 3, 6, 10]), ('jumpSquat', [0, 1, 2, 4]), ('air', [147, 70, 0, -120]),
         ('landing', [0, 1, 2, 4]), ('hitStun', [0, 3, 6, 12]), ('knockAir', [70, 20, -40, -100]), ('knock', [1, 10, 20, 35]),
         ('getup', [1, 5, 10, 15]), ('rollF', [1, 7, 14, 21]), ('thr', [1, 3, 5, 6]), ('thrHit', [1, 15, 30, 39]),
         ('thrWhiff', [1, 8, 16, 23]), ('thrown', [1, 6, 12, 20]), ('spec', [1, 10, 14, 30]), ('win', [1, 6, 12, 18]),
         ('ko', [1, 10, 20, 40])]

JS_SET = """([act, x]) => {
  const S = __VF.G.S, f = S.sides[0].team[0], m = __VF.CFG.moves[act], st = {x: -500, y: 0, face: 1, air: false, vy: 0, hit: 0, stun: 8, prev: 0, land: 5};
  let a = act, af = x;
  if (act === 'blockLow') { a = 'block'; st.prev = __VF.BTN.D | __VF.BTN.L; }
  if (act === 'air') { af = 5; st.air = true; st.y = 800; st.vy = x; }
  if (act === 'knockAir') { a = 'knock'; af = 3; st.air = true; st.y = 700; st.vy = x; }
  if (act === 'thrHit') { a = 'thr'; st.hit = 1; }
  if (m && m.r === 'land') { st.air = true; st.y = 900; }
  if (act === 'walkF' || act === 'dashF') st.x = -500 + x * 60;
  if (act === 'walkB' || act === 'dashB') st.x = -500 - x * 50;
  Object.assign(f, st, {act: a, af});
  __VF.F3D[0].F = null;   // no easing from the previous tile
  const o = S.sides[1].team[0]; Object.assign(o, {x: 900, y: 0, act: 'idle', af: 1, air: false});
  return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => {
    const p = __VF.toScreen(f.x / 1000, f.y / 1000 + .9, 0); r([p.x, p.y]); })));
}"""


async def route(r):
    u = r.request.url
    if 'three.min.js' in u: await r.fulfill(path=os.path.join(ROOT, 'three.min.js'), content_type='application/javascript')
    elif u.startswith('file://'): await r.continue_()
    else: await r.abort()


async def main(out, which):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=ARGS)
        pg = await b.new_page(viewport={'width': 844, 'height': 390}); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('**/*', route); await pg.goto('file://' + os.path.join(ROOT, 'game_w.html'))
        await pg.wait_for_function("window.__VF && __VF.G.state==='title'", timeout=60000)
        moves = await pg.evaluate("() => Object.entries(__VF.CFG.moves).map(([k, m]) => [k, m.s, m.a, m.r])")
        rows = []
        if which in ('moves', 'all'):
            for k, s, a, r in moves:
                rr = 8 if r == 'land' else r
                rows.append((k, [1, s, s + 1, s + a + rr // 2]))
        if which in ('acts', 'all'): rows += OTHER
        await pg.evaluate("() => { __VF.startMatch('training', {seed: 1, dummy: 'fermo'}); __VF.frame(110); __VF.G.state = 'sheet'; const h = document.getElementById('hud'); if (h) h.style.visibility = 'hidden'; }")
        await pg.wait_for_timeout(800)
        TW, TH = 150, 210; font = ImageFont.load_default()
        for fp in ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
            if os.path.isfile(fp): font = ImageFont.truetype(fp, 13); break
        sheet = Image.new('RGB', (110 + 4 * TW, 8 + len(rows) * TH), (20, 18, 28)); d = ImageDraw.Draw(sheet)
        for ri, (act, frames) in enumerate(rows):
            d.text((6, 8 + ri * TH + TH // 2 - 8), act, fill=(255, 122, 26), font=font)
            for ci, x in enumerate(frames):
                cx, cy = await pg.evaluate(JS_SET, [act, x])
                shot = Image.open(io.BytesIO(await pg.screenshot())).convert('RGB')
                box = (int(cx - 95), int(cy - 150), int(cx + 95), int(cy + 120))
                tile = shot.crop(box).resize((TW - 4, TH - 18))
                sheet.paste(tile, (110 + ci * TW, 8 + ri * TH))
                d.text((112 + ci * TW, 8 + ri * TH + TH - 17), ('vy ' if act in ('air', 'knockAir') else 'af ') + str(x), fill=(230, 230, 235), font=font)
        sheet.save(out); print(out, sheet.size, 'errors', errs)
        await b.close()


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'all'))
