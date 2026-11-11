#!/usr/bin/env python3
"""In-page test runner for Voidrise Fighters.

usage: python3 tests/run.py tests/<file>.test.js [--viewport WxH] [--touch] [--mobile] [--seed N]

Loads the test build (game_w.html, made by mk.sh) in headless Chrome, waits for the title
state, injects window.TINDEX (text of index.html), tests/lib.js and the test file, runs T.run()
and prints one line per test: "PASS name" or "FAIL name: message", plus "INFO msg" lines from
T.info. Uncaught page errors print as PAGEERROR and console errors as CONSOLEERROR
(blocked-font "Failed to load resource" lines are ignored). Exit code 1 if anything failed or errored.
"""
import argparse, asyncio, json, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'game_w.html')
INDEX = os.path.join(ROOT, 'index.html')
CHROME_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
               '--ignore-gpu-blocklist', '--enable-webgl', '--no-sandbox']


async def route_assets(r):
    """three.js from the local copy, the page's own file as it is; nothing else."""
    u = r.request.url
    if 'three.min.js' in u:
        await r.fulfill(path=os.path.join(ROOT, 'three.min.js'), content_type='application/javascript')
    elif u.startswith('file://'):
        await r.continue_()
    else:
        await r.abort()


def chrome_path():
    """System Chrome/Chromium if present (or $VF_CHROME); None = Playwright's own Chromium."""
    if os.environ.get('VF_CHROME'):
        return os.environ['VF_CHROME']
    for c in ('/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/opt/pw-browsers/chromium'):
        if os.path.isfile(c):
            return c
    return None


async def main(a):
    w, h = (int(v) for v in a.viewport.lower().split('x'))
    errors = []
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome_path(), args=CHROME_ARGS)
        ctx = await b.new_context(viewport={'width': w, 'height': h}, has_touch=a.touch,
                                  is_mobile=a.mobile, device_scale_factor=1)
        pg = await ctx.new_page()

        def on_console(m):
            if m.type == 'error' and 'Failed to load resource' not in m.text:
                errors.append('CONSOLEERROR ' + m.text)
        pg.on('console', on_console)
        pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))

        await pg.route('**/*', route_assets)
        await pg.goto('file://' + PAGE, wait_until='domcontentloaded')
        await pg.wait_for_function("window.__VF && __VF.G.state==='title'", timeout=60000)
        await pg.add_script_tag(content='window.TINDEX=' + json.dumps(open(INDEX, encoding='utf-8').read()) + ';')
        await pg.add_script_tag(content=open(os.path.join(ROOT, 'tests', 'lib.js'), encoding='utf-8').read())
        await pg.add_script_tag(content=open(a.file, encoding='utf-8').read())
        await pg.evaluate('T.SEED=%d' % a.seed)
        res = await pg.evaluate('T.run()')
        infos = await pg.evaluate('window.TINFO||[]')
        await pg.wait_for_timeout(300)
        await b.close()
    bad = 0
    for r in res:
        if r['ok']:
            print('PASS ' + r['name'])
        else:
            bad += 1
            print('FAIL %s: %s' % (r['name'], r.get('msg', '')))
    for i in infos:
        print('INFO ' + i)
    for e in errors:
        print(e)
    print('%d passed, %d failed, %d errors (%s, seed %d)' % (len(res) - bad, bad, len(errors), os.path.basename(a.file), a.seed))
    return 1 if bad or errors or not res else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--viewport', default='640x360')
    ap.add_argument('--touch', action='store_true')
    ap.add_argument('--mobile', action='store_true')
    ap.add_argument('--seed', type=int, default=1, help='seed for Math.random during the tests (replay a failure)')
    sys.exit(asyncio.run(main(ap.parse_args())))
