// Real-time smoke test of a built page: every play runs for a while with the page's own loop, the options are
// switched while it plays (new/old, Allungo, Manichino, speeds), on a phone-landscape viewport. No page error allowed.
//   node tests/smoke.js <page.html> [screenshot.png]
const {open} = require('./lib');
(async () => {
  const {browser, page, errors} = await open(process.argv[2], {w: 844, h: 390, dpr: 2});
  const click = id => page.evaluate(id => document.getElementById(id).click(), id);
  for (let i = 0; i < 10; i++) { await click('play' + i); await page.waitForTimeout(700); if (i === 3 && process.argv[3]) await page.screenshot({path: process.argv[3]}); }
  for (const id of ['aOld', 'play2', 'aNew', 'opt_smear', 'play3', 'opt_dummy', 'play6', 's4', 'opt_dummy', 'play7', 's1', 'opt_smear', 'spin', 'play4']) { await click(id); await page.waitForTimeout(450); }
  await page.keyboard.press('n'); await page.keyboard.press('m'); await page.keyboard.press('l'); await page.keyboard.press('ArrowRight'); await page.keyboard.press(' ');
  await page.waitForTimeout(500);
  const st = await page.evaluate(() => ({fps: VW.fps, on: VW.RN.on, opt: VW.RN.opt, act: VW.F.act, overflowX: document.documentElement.scrollWidth > innerWidth}));
  console.log(JSON.stringify({errors, st}));
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})();
