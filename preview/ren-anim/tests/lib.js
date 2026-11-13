// Shared test helpers: opens a built preview page in headless Chromium (three.js served from tests/three.min.js,
// since the page asks a CDN for it) and collects the page's errors.
const {chromium} = require('playwright');
const path = require('path');

async function open(html, o) {
  o = o || {};
  const browser = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader']});
  // o.mobile: a phone (touch, coarse pointer); o.init: a script run in the page before its own (a stand-in for the viewer's
  // services, say)
  const page = await browser.newPage({viewport: {width: o.w || 900, height: o.h || 420}, deviceScaleFactor: o.dpr || 1, isMobile: !!o.mobile, hasTouch: !!o.mobile});
  if (o.init) await page.addInitScript(o.init);
  const errors = [];
  page.on('pageerror', e => errors.push(String(e.message)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.route('**/three.min.js', r => r.fulfill({path: path.join(__dirname, 'three.min.js'), contentType: 'text/javascript'}));
  await page.goto('file://' + path.resolve(html));
  await page.waitForFunction(() => window.VW && window.VW.it && window.VW.renderer, null, {timeout: 60000});
  await page.waitForTimeout(o.settle === undefined ? 800 : o.settle);
  return {browser, page, errors};
}

// In the page: stop the real-time stepping and the auto spin, so that only VW.tick moves the fighter.
async function freeze(page) { await page.evaluate(() => { VW.speed = 0; VW.spin = false; VW.acc = 0; }); }
// Two drawn frames, so the canvas shows the current state.
async function drawn(page) { await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))); }

module.exports = {open, freeze, drawn};
