// Interface: the opening (redone for Denis: Ren and Kael dash in, face off, lunge and their fists meet; impact frame, shock,
// a slow-motion hold, a white-out, the logo where the title has it), skipping, and its clock (a pure function of the time;
// it stops while the page is hidden).
const inRoot = () => $('sc-intro'), inEl = s => document.querySelector('#sc-intro ' + s);
const inOp = s => +getComputedStyle(inEl(s)).opacity;
const inTx = el => new DOMMatrix(getComputedStyle(el).transform).e;
function inFresh() { __VF.UI.SV.introSeen = false; __VF.navReset('intro'); }
T.test('boot shows the intro first (or its end, the title, on a slow start)', () => { T.eq(__VF.G.state, 'title'); T.ok(['intro', 'title'].includes(__VF.UI.NAV.cur), __VF.UI.NAV.cur); });
T.test('it lasts about five seconds', () => { T.ok(__VF.CFG.ui.intro.len >= 4500 && __VF.CFG.ui.intro.len <= 6000, __VF.CFG.ui.intro.len); });
T.test('shots in order', () => { inFresh(); const c = () => inRoot().className;
  for (const [t, s] of [[100, 'dark'], [800, 'rush'], [1320, 'impact'], [2500, 'hold'], [3700, 'burst'], [4500, 'logo']]) { __VF.introAt(t); T.ok(c().includes('s-' + s), t + ' ' + c()); } });
T.test('they come from the sides and meet: far apart at the start, the two halves rebuild the picture at the hit', () => { inFresh();
  const ren = inEl('.inF.r:not(.g)'), kael = inEl('.inF.k:not(.g)');
  __VF.introAt(300); T.ok(inTx(ren) < -100 && inTx(kael) > 100, 'apart ' + inTx(ren) + ' ' + inTx(kael));
  __VF.introAt(800); const a = inTx(kael) - inTx(ren);
  __VF.introAt(1200); const b = inTx(kael) - inTx(ren); T.ok(b < a, 'closing in ' + a + ' ' + b);
  __VF.introAt(1310); T.near(inTx(ren), 0, .5); T.near(inTx(kael), 0, .5); T.ok(inOp('.inF.r:not(.g)') === 1 && inOp('.inF.k:not(.g)') === 1); });
T.test('afterimages (coloured silhouettes on the back canvas) trail them while they dash, none while they stand', () => new Promise(done => {
  const I = __VF.UI.INTRO, go = () => { if (!I.spr[0] || !I.spr[1]) return setTimeout(go, 50);
    inFresh(); __VF.introAt(420); T.ok(I.ghostA > .05, 'dash ' + I.ghostA); __VF.introAt(1390); T.eq(I.ghostA, 0, 'at the hit'); done(); };
  go(); }));
T.test('the hit flashes white, then the impact frame (black figures), then a hard shake', () => { inFresh();
  __VF.introAt(1300); T.ok(inOp('.inFlash') > .9, 'flash ' + inOp('.inFlash'));
  __VF.introAt(1400); T.ok(inRoot().classList.contains('imp'), 'impact frame'); T.ok(getComputedStyle(inEl('.inF.r:not(.g)')).filter.includes('brightness(0)'));
  __VF.introAt(1500); T.ok(!inRoot().classList.contains('imp'), 'impact frame over');
  let m = 0; for (const t of [1310, 1340, 1370, 1460, 1490]) { __VF.introAt(t); const s = new DOMMatrix(getComputedStyle(inEl('.inStage')).transform); m = Math.max(m, Math.abs(s.e) + Math.abs(s.f)); }
  T.ok(m > 2, 'shake ' + m);
  __VF.introAt(2200); T.ok(inOp('.inFlash') < .05, 'flash gone'); });
T.test('the effects are drawn on the canvases (behind and in front), the logo is hidden until the white-out', () => { inFresh();
  const ink = c => { const d = c.getContext('2d', {willReadFrequently: true}).getImageData(0, 0, c.width, c.height).data; let s = 0; for (let i = 3; i < d.length; i += 4) s += d[i]; return s; };
  __VF.introAt(2400); T.ok(ink(inEl('.inFront')) > 0 && ink(inEl('.inBack')) > 0, 'drawn'); T.eq(inOp('.inLogoBox'), 0);
  __VF.introAt(4600); T.eq(inOp('.inLogoBox'), 1); T.eq(inOp('.inF.r:not(.g)'), 0); });
T.test('the end goes to the title, the logo exactly where the intro left it, and remembers it', () => { inFresh();
  __VF.introAt(__VF.CFG.ui.intro.len - 30); const a = inEl('.ulogoTx').getBoundingClientRect();
  __VF.introAt(__VF.CFG.ui.intro.len + 1); T.eq(__VF.UI.NAV.cur, 'title'); T.ok($('sc-title').classList.contains('keep'), 'no entrance');
  const b = document.querySelector('#sc-title .ulogoTx').getBoundingClientRect();
  T.near(b.left, a.left, 3); T.near(b.top, a.top, 3); T.near(b.width, a.width, 4);
  T.eq(__VF.UI.SV.introSeen, true); T.eq(JSON.parse(localStorage.getItem('voidrise.save')).introSeen, true); });
T.test('Salta skips (the title then enters as usual)', () => { __VF.navReset('intro'); uiClick('Salta'); T.eq(__VF.UI.NAV.cur, 'title'); T.ok(!$('sc-title').classList.contains('keep')); });
T.test('first time: a tap elsewhere does not skip; later it does', () => { __VF.UI.SV.introSeen = false; __VF.navReset('intro'); tapEl($('sc-intro'), 3); T.eq(__VF.UI.NAV.cur, 'intro');
  __VF.UI.SV.introSeen = true; __VF.navReset('intro'); tapEl($('sc-intro'), 4); T.eq(__VF.UI.NAV.cur, 'title'); });
T.test('later: any key or pad button skips too', () => { __VF.UI.SV.introSeen = true; __VF.navReset('intro'); keyTap('KeyX'); T.eq(__VF.UI.NAV.cur, 'title');
  __VF.navReset('intro'); padsAt([{}]); padTick(); padsAt([{buttons: {3: 1}}]); padTick(); T.eq(__VF.UI.NAV.cur, 'title'); fakePads([]); padTick(); });
T.test('its clock runs on the frames shown: a long gap (hidden page) does not jump ahead', () => { __VF.navReset('intro'); const t = performance.now(); __VF.uiFrame(t); __VF.uiFrame(t + 16);
  const a = __VF.UI.INTRO.t; __VF.uiFrame(t + 60000); T.ok(__VF.UI.INTRO.t - a <= 100, 'advanced ' + (__VF.UI.INTRO.t - a)); T.eq(__VF.UI.NAV.cur, 'intro'); });
T.test('a pure function of the time: the same moment draws the same picture', () => { inFresh();
  const snap = () => { __VF.introAt(2600); return inEl('.inFront').toDataURL().length + ':' + inEl('.inStage').style.transform + ':' + inEl('.inF.k:not(.g)').style.transform; };
  const a = snap(); __VF.introAt(900); __VF.introAt(4000); T.eq(snap(), a); });
T.test('the intro never touches the fight state', () => { __VF.navReset('intro'); __VF.introAt(2000); T.eq(__VF.G.S, null); });
T.test('no endless CSS animation during the intro', () => { __VF.navReset('intro'); __VF.introAt(1400); T.eq(document.getAnimations().filter(a => a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity).length, 0); });
