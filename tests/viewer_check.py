#!/usr/bin/env python3
"""Check of the character viewer (viewer.html, built by mk.sh): it boots with Ren on the stage, every play button and
option works, the picture is not empty and the console stays clean. Phone landscape and portrait sizes, touch.

usage: python3 tests/viewer_check.py [OUT_DIR]   (OUT_DIR: also save a screenshot per size)
"""
import asyncio, os, sys, tempfile
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox']
CHROME = next((c for c in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/opt/pw-browsers/chromium') if os.path.isfile(c)), None)
# the published page gets this skeleton from the artifact host
WRAP = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light}body{margin:0;font:14px/1.4 system-ui,sans-serif}[hidden]{display:none!important}</style></head><body>%s</body></html>')


async def route(r):
    u = r.request.url
    if 'three.min.js' in u: await r.fulfill(path=os.path.join(ROOT, 'three.min.js'), content_type='application/javascript')
    elif u.startswith('file://'): await r.continue_()
    else: await r.abort()


async def main(out_dir):
    page_file = os.path.join(tempfile.mkdtemp(), 'viewer.html')
    open(page_file, 'w', encoding='utf-8').write(WRAP % open(os.path.join(ROOT, 'viewer.html'), encoding='utf-8').read())
    failed = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=ARGS)
        for w, h in ((844, 390), (390, 844)):
            ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True)
            pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
            pg.on('console', lambda m: errs.append('CONSOLE ' + m.text) if m.type in ('error', 'warning') and 'Failed to load resource' not in m.text else None)
            await pg.route('**/*', route); await pg.goto('file://' + page_file)
            await pg.wait_for_function("document.getElementById('now') && document.getElementById('now').textContent.length > 0", timeout=60000)
            n = await pg.evaluate("document.querySelectorAll('#moves button').length")
            for i in range(n):
                await pg.click('#play%d' % i); await pg.wait_for_timeout(250)
            for bid in ('pMeshy', 'lFlat', 's4', 'spin', 'pDraw', 'lToon', 's1', 'spin'):
                await pg.click('#' + bid)
            await pg.click('#play2'); await pg.wait_for_timeout(700)
            # the canvas shows the fighter: some pixels are not transparent in the middle of the picture
            drawn = await pg.evaluate("""() => { const c = document.getElementById('view'), g = document.createElement('canvas'); g.width = 64; g.height = 64;
              const x = g.getContext('2d'); x.drawImage(c, c.width * .35, c.height * .2, c.width * .3, c.height * .6, 0, 0, 64, 64);
              const d = x.getImageData(0, 0, 64, 64).data; let k = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) k++; return k; }""")
            # the proposal's look: fists in the guard (the fingers curled on their own bones, in the skeleton), open hands
            # in the special, spikes on the head, thin face outline
            look = await pg.evaluate("""async () => { const it = VW.it, r = {};
              document.getElementById('play0').click(); await new Promise(f => setTimeout(f, 300));
              r.fists = !!it.fingers && it.fingers.length === 30 && it.mesh.skeleton.bones.length === it.bones.length + 30 && it.curl === 1
                && it.fingers.every((o, i) => Math.abs(o.quaternion.dot(it.fist[i])) > .9999);
              document.getElementById('play6').click(); await new Promise(f => setTimeout(f, 300));
              r.open = it.curl === 0 && it.fingers.every(o => Math.abs(o.quaternion.w) > .9999);
              r.spikes = it.joints.head.children.some(g => g.isGroup && g.children.length >= 8);
              r.line = !!it.mesh.geometry.attributes.aLine; return r; }""")
            if not all(look.values()): errs.append('look ' + str(look))
            ok = n == 10 and drawn > 200 and not errs
            failed += not ok
            print(('PASS' if ok else 'FAIL') + ' viewer %dx%d: %d play buttons, %d drawn pixels of 4096 in the middle%s' % (w, h, n, drawn, (', ' + ' | '.join(errs[:3])) if errs else ''))
            if out_dir: await pg.screenshot(path=os.path.join(out_dir, 'viewer_%dx%d.png' % (w, h)))
            await ctx.close()
        await b.close()
    print('%d failed (viewer_check)' % failed)
    return failed


if __name__ == '__main__':
    sys.exit(1 if asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None)) else 0)
