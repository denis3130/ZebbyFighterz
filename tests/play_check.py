#!/usr/bin/env python3
"""Checks play/ (the installable phone version) like a phone would: served over http, no CDN, manifest and icons,
service worker registered, then a reload with the network off still reaches the title and starts a fight.

usage: python3 tests/play_check.py   (after bash mk.sh)
"""
import asyncio, functools, http.server, json, os, socketserver, sys, threading
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAY = os.path.join(ROOT, 'play')
CHROME = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox']


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.webmanifest': 'application/manifest+json'}
        def log_message(self, *a): pass
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=PLAY))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d/' % srv.server_address[1]


def chrome():
    for c in (os.environ.get('VF_CHROME'), '/usr/bin/google-chrome', '/usr/bin/chromium', '/opt/pw-browsers/chromium'):
        if c and os.path.exists(c): return c
    return None


async def main():
    base, fails, errs = serve(), [], []
    def check(ok, msg): print(('PASS ' if ok else 'FAIL ') + msg); ok or fails.append(msg)
    m = json.load(open(os.path.join(PLAY, 'manifest.webmanifest')))
    check(m['display'] == 'fullscreen' and m['orientation'] == 'landscape' and {'192x192', '512x512'} <= {i['sizes'] for i in m['icons']}, 'manifest: fullscreen, landscape, icons 192 and 512')
    html = open(os.path.join(PLAY, 'index.html'), encoding='utf-8').read()
    check('cdnjs.cloudflare.com' not in html and 'window.__VF=' not in html, 'page: three.js inlined, no test API')
    check('name="viewport"' in html and 'apple-touch-icon' in html and 'rel="manifest"' in html, 'page: viewport, home-screen icon, manifest')
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=chrome(), args=CHROME)
        ctx = await b.new_context(viewport={'width': 844, 'height': 390}, has_touch=True, is_mobile=True, device_scale_factor=1)
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errs.append('PAGEERROR ' + str(e)))
        pg.on('console', lambda c: c.type == 'error' and 'Failed to load resource' not in c.text and 'net::ERR' not in c.text and errs.append('CONSOLEERROR ' + c.text))
        async def route(r):   # like a phone with no CDN: only the page's own server answers
            await (r.continue_() if r.request.url.startswith(base) else r.abort())
        await ctx.route('**/*', route)
        on = lambda sc: "document.getElementById('sc-%s') && document.getElementById('sc-%s').classList.contains('on')" % (sc, sc)
        title = "['intro','title','name','menu'].some(s => { const e = document.getElementById('sc-' + s); return e && e.classList.contains('on'); })"

        async def to_menu():   # through the opening screens like a player: «Salta», a tap on the title, «Conferma» on the name
            for _ in range(8):
                await pg.wait_for_timeout(500)   # (a tap in the first moments of a screen is taken for a double tap and ignored)
                if await pg.evaluate(on('menu')): return
                if await pg.evaluate(on('intro')): await pg.tap('#sc-intro .inSkip')
                elif await pg.evaluate(on('title')): await pg.tap('#sc-title')
                elif await pg.evaluate(on('name')): await pg.evaluate("document.querySelector('#sc-name .umw .ub').click()")
            raise RuntimeError('menu not reached')
        await pg.goto(base, wait_until='domcontentloaded')
        await pg.wait_for_function(title, timeout=60000)
        check(True, 'online: opening shown')
        ok = await pg.evaluate("navigator.serviceWorker.ready.then(r => !!r.active).catch(() => false)")
        check(ok, 'service worker active')
        await pg.wait_for_timeout(500)
        await ctx.set_offline(True)
        await pg.reload(wait_until='domcontentloaded')
        await pg.wait_for_function(title, timeout=60000)
        check(True, 'offline reload: opening shown')
        await to_menu()
        await pg.wait_for_timeout(500)
        await pg.tap('#sc-menu [data-act="train"]')
        await pg.wait_for_timeout(2000)
        st = await pg.evaluate("({hud: getComputedStyle(document.getElementById('hud')).visibility, touch: document.getElementById('touch').classList.contains('on'), timer: document.getElementById('timer').textContent})")
        check(st == {'hud': 'visible', 'touch': True, 'timer': '∞'}, 'offline: training fight with HUD and touch controls ' + json.dumps(st, ensure_ascii=False))
        if len(sys.argv) > 1: await pg.screenshot(path=sys.argv[1])
        await b.close()
    for e in errs: print(e)
    print('%d failed, %d errors (play_check)' % (len(fails), len(errs)))
    return 1 if fails or errs else 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
