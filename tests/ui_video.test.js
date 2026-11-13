// Interface: the filmed opening (Denis's storyboard animated with ComfyUI, assets/ui/video/intro.mp4): it plays muted and
// inline when ready, a flash and a shake when the fists land, a white-out, the drawn intro's logo, then the title; it
// stops when the intro is left, while the phone asks to be turned, and the drawn intro plays if the clip never loads.
const vEl = () => document.querySelector('#sc-intro video.inVideo'), vI = () => __VF.UI.INTRO, vC = () => __VF.CFG.ui.intro;
const vOp = el => +getComputedStyle(el).opacity, vQ = s => document.querySelector('#sc-intro ' + s);
const vWait = (ok, ms = 8000) => new Promise((done, fail) => { const t0 = performance.now(), go = () => ok() ? done() : performance.now() - t0 > ms ? fail(new Error('timeout')) : setTimeout(go, 50); go(); });
const vLen = () => vI().vlen || vC().video.len, vTotal = () => vLen() + vC().len - 3900;
function vFresh() { vC().video.on = true; __VF.UI.SV.introSeen = false; __VF.navReset('intro'); }
T.test('the clip is in the page, muted and inline, played from a blob', () => { const v = vEl();
  T.ok(v, 'video element'); T.ok(v.src.startsWith('blob:'), v.src.slice(0, 20)); T.ok(v.muted && v.playsInline, 'muted inline'); });
T.test('its first frame loads', () => vWait(() => vI().vok).then(() => T.ok(vEl().videoWidth >= 900, 'size ' + vEl().videoWidth)));
T.test('when ready the intro plays the clip, which keeps the intro\'s clock', () => vWait(() => vI().vok).then(() => { vFresh();
  T.eq(vI().mode, 'video'); T.near(vLen(), 4530, 200);
  return new Promise(r => setTimeout(r, 900)).then(() => { const v = vEl();
    T.ok(!v.paused, 'playing'); T.ok(v.currentTime > .3, 'time ' + v.currentTime); T.ok(vI().t > 300, 'clock ' + vI().t);
    T.eq(vOp(v), 1); T.eq(__VF.UI.NAV.cur, 'intro'); }); }));
T.test('a flash and a shake when the fists land', () => { vFresh(); const H = vC().video.hit;
  __VF.introAt(H - 100); T.ok(vOp(vQ('.inFlash')) < .05, 'no flash before');
  __VF.introAt(H + 10); T.ok(vOp(vQ('.inFlash')) > .5, 'flash ' + vOp(vQ('.inFlash')));
  let m = 0; for (const t of [H + 20, H + 60, H + 100]) { __VF.introAt(t); const s = new DOMMatrix(getComputedStyle(vQ('.inStage')).transform); m = Math.max(m, Math.abs(s.e) + Math.abs(s.f)); }
  T.ok(m > 1, 'shake ' + m); __VF.introAt(H + 700); T.ok(vOp(vQ('.inFlash')) < .05, 'flash gone'); });
T.test('the white-out over the last moments of the clip (still showing), then the logo over the dark and the clip gone', () => { vFresh(); const L = vLen(), W = vC().video.white;
  __VF.introAt(L - W / 2); const f = vOp(vQ('.inFlash')); T.ok(f > .05 && f < .6, 'rising ' + f); T.eq(vOp(vEl()), 1);
  __VF.introAt(L - 20); T.ok(vOp(vQ('.inFlash')) > .8, 'white ' + vOp(vQ('.inFlash'))); T.eq(vOp(vQ('.inLogoBox')), 0);
  __VF.introAt(L + 700); T.eq(vOp(vQ('.inLogoBox')), 1); T.eq(vOp(vEl()), 0); T.ok(vEl().paused, 'clip stopped'); });
T.test('the drawn fighters and effects stay hidden under the clip', () => { vFresh(); __VF.introAt(1500);
  T.eq(vOp(vQ('.inF.r')), 0); T.eq(vOp(vQ('.inF.k')), 0); T.eq(vOp(vQ('.inSky')), 0); T.eq(vOp(vQ('.inLogoBox')), 0); });
T.test('the end goes to the title, the logo kept still', () => { vFresh(); __VF.introAt(vTotal() + 1);
  T.eq(__VF.UI.NAV.cur, 'title'); T.ok($('sc-title').classList.contains('keep'), 'no entrance'); T.ok(vEl().paused, 'clip stopped'); T.eq(vOp(vEl()), 0); });
T.test('Salta stops and hides the clip', () => { vFresh(); uiClick('Salta'); T.eq(__VF.UI.NAV.cur, 'title'); T.ok(vEl().paused); T.eq(vOp(vEl()), 0); });
T.test('the clip stops while the phone asks to be turned, and goes on after', () => { vFresh(); const t = performance.now(); __VF.uiFrame(t); __VF.uiFrame(t + 16);
  __VF.MN.rot = true; __VF.uiFrame(t + 32); T.ok(vEl().paused, 'paused'); __VF.MN.rot = false; __VF.uiFrame(t + 48); T.ok(!vEl().paused, 'playing again'); });
T.test('a clip that is not ready: a dark wait, then the drawn intro', () => { const ok = vI().vok; vI().vok = false; vFresh();
  T.eq(vI().mode, 'wait'); T.eq(vOp(vQ('.inLogoBox')), 0);
  const t = performance.now(); __VF.uiFrame(t); for (let i = 1; i <= 20; i++) __VF.uiFrame(t + i * 100);
  T.eq(vI().mode, 'drawn'); vI().vok = ok; });
T.test('the drawn intro when the clip is switched off', () => { vC().video.on = false; __VF.UI.SV.introSeen = false; __VF.navReset('intro'); T.eq(vI().mode, 'drawn'); T.eq(vOp(vEl()), 0); vC().video.on = true; });
T.test('no endless CSS animation and no fight state during the clip', () => { vFresh(); __VF.introAt(2000);
  T.eq(document.getAnimations().filter(a => a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity).length, 0); T.eq(__VF.G.S, null); });
