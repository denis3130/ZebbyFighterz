#!/usr/bin/env python3
"""Milliseconds per frame (logic + draw, the GPU synced with readPixels every frame), as measured since Tappa 2a:
training against the random dummy, 120 frames after a 60-frame warm-up, RUNS runs (needs Playwright; build first).

usage: python3 tools/frame_ms.py [--page game_w.html] [--viewport 844x390] [--runs 3]
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
import run  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

JS = '''(n) => { const V = __VF, gl = V.renderer.getContext(), px = new Uint8Array(4);
  V.startMatch('training', {seed: 3, dummy: 'casuale'}); V.frame(V.CFG.round.intro);
  for (let i = 0; i < 60; i++) { V.frame(1); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); }
  const t = performance.now();
  for (let i = 0; i < n; i++) { V.frame(1); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); }
  return (performance.now() - t) / n; }'''


async def main(a):
    w, h = (int(v) for v in a.viewport.lower().split('x'))
    page = os.path.abspath(a.page)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=run.chrome_path(), args=run.CHROME_ARGS)
        pg = await (await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)).new_page()
        await pg.route('**/*', run.route_assets)
        await pg.goto('file://' + page, wait_until='domcontentloaded')
        await pg.wait_for_function("window.__VF && __VF.G.state==='title'", timeout=90000)
        ms = [await pg.evaluate(JS, 120) for _ in range(a.runs)]
        print('%s: %s ms per frame (mean %.1f)' % (a.page, ' / '.join('%.1f' % m for m in ms), sum(ms) / len(ms)))
        await b.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default='game_w.html')
    ap.add_argument('--viewport', default='844x390')
    ap.add_argument('--runs', type=int, default=3)
    asyncio.run(main(ap.parse_args()))
