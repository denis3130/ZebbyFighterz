#!/usr/bin/env python3
"""Screenshots of the arena from the game's camera extremes, to look at (needs Playwright; build with mk.sh first).

usage: python3 tools/arena_shots.py OUTDIR [--viewport WxH] [--page game_w.html] [--fighters]

Writes OUTDIR/<w>x<h>_<name>.png for: start (both fighters at their start), left/right (camera at -xMax/+xMax,
fighters apart), far (fighters at max separation: the camera at distMax), jump (a super jump), plus 'magenta' copies
with the renderer cleared to magenta (holes show). The fighters are hidden unless --fighters.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
import run  # noqa: E402  (chrome args, asset routing)
from playwright.async_api import async_playwright  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = {  # name: (x0 mm, x1 mm, y0 mm)
    'start': (-1200, 1200, 0), 'left': (-6000, -2000, 0), 'right': (2000, 6000, 0), 'far': (-2750, 2750, 0),
    'jump': (-600, 600, 2314)}


async def main(a):
    w, h = (int(v) for v in a.viewport.lower().split('x'))
    os.makedirs(a.out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=run.chrome_path(), args=run.CHROME_ARGS)
        pg = await (await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.route('**/*', run.route_assets)
        await pg.goto('file://' + os.path.join(ROOT, a.page), wait_until='domcontentloaded')
        await pg.wait_for_function("window.__VF && __VF.G.state==='title'", timeout=60000)
        await pg.evaluate("__VF.startMatch('training',{seed:1,dummy:'fermo'}); __VF.G.state='pause';"
                          "document.querySelectorAll('.screen,#hud,#touch').forEach(e=>e.style.display='none')")
        for name, (x0, x1, y0) in SHOTS.items():
            for mag in (False, True):
                await pg.evaluate('''([x0,x1,y0,mag,show])=>{ const V=__VF,S=V.G.S,a=V.fighterOf(S,0),b=V.fighterOf(S,1);
                  a.x=x0;b.x=x1;a.y=y0; V.F3D.forEach(f=>f.root.visible=show);
                  V.renderer.setClearColor(mag?0xff00ff:0x000000,1);
                  for(let i=0;i<90;i++) V.renderFrame(S,1000+i*16); }''', [x0, x1, y0, mag, a.fighters])
                await pg.screenshot(path=os.path.join(a.out, '%dx%d_%s%s.png' % (w, h, name, '_magenta' if mag else '')))
        print('\n'.join(errs) or 'no errors')
        await b.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--viewport', default='844x390')
    ap.add_argument('--page', default='game_w.html')
    ap.add_argument('--fighters', action='store_true')
    asyncio.run(main(ap.parse_args()))
