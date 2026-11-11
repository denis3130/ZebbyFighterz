// Interface U1, Task 6: the opening sequence (Ren and Kael rush in, their fists clash, the logo forms), skipping, and
// its clock (a pure function of the time; it stops while the page is hidden).
T.test('boot shows the intro first (or its end, the title, on a slow start)', () => { T.eq(__VF.G.state, 'title'); T.ok(['intro', 'title'].includes(__VF.UI.NAV.cur), __VF.UI.NAV.cur); });
T.test('shots in order', () => { __VF.UI.SV.introSeen = false; __VF.navReset('intro'); const c = () => $('sc-intro').className;
  __VF.introAt(300); T.ok(c().includes('s-dark'), c()); __VF.introAt(1000); T.ok(c().includes('s-ren'), c()); __VF.introAt(2500); T.ok(c().includes('s-kael'), c());
  __VF.introAt(3400); T.ok(c().includes('s-close'), c()); __VF.introAt(3800); T.ok(c().includes('s-impact'), c()); __VF.introAt(5300); T.ok(c().includes('s-white'), c());
  __VF.introAt(6000); T.ok(c().includes('s-logo'), c()); });
T.test('the impact flashes white and shakes', () => { __VF.introAt(3700); const f = +getComputedStyle(document.querySelector('#sc-intro .inFlash')).opacity; T.ok(f > .9, 'flash ' + f);
  __VF.introAt(3760); const s = new DOMMatrix(getComputedStyle(document.querySelector('#sc-intro .inStage')).transform); T.ok(Math.abs(s.e) + Math.abs(s.f) > .5, 'shake');
  __VF.introAt(4300); T.ok(+getComputedStyle(document.querySelector('#sc-intro .inFlash')).opacity < .05, 'flash gone'); });
T.test('the end goes to the title and remembers it', () => { __VF.introAt(__VF.CFG.ui.intro.len + 1); T.eq(__VF.UI.NAV.cur, 'title'); T.eq(__VF.UI.SV.introSeen, true); T.eq(JSON.parse(localStorage.getItem('voidrise.save')).introSeen, true); });
T.test('Salta skips', () => { __VF.navReset('intro'); uiClick('Salta'); T.eq(__VF.UI.NAV.cur, 'title'); });
T.test('first time: a tap elsewhere does not skip; later it does', () => { __VF.UI.SV.introSeen = false; __VF.navReset('intro'); tapEl($('sc-intro'), 3); T.eq(__VF.UI.NAV.cur, 'intro');
  __VF.UI.SV.introSeen = true; __VF.navReset('intro'); tapEl($('sc-intro'), 4); T.eq(__VF.UI.NAV.cur, 'title'); });
T.test('later: any key or pad button skips too', () => { __VF.UI.SV.introSeen = true; __VF.navReset('intro'); keyTap('KeyX'); T.eq(__VF.UI.NAV.cur, 'title');
  __VF.navReset('intro'); padsAt([{}]); padTick(); padsAt([{buttons: {3: 1}}]); padTick(); T.eq(__VF.UI.NAV.cur, 'title'); fakePads([]); padTick(); });
T.test('its clock runs on the frames shown: a long gap (hidden page) does not jump ahead', () => { __VF.navReset('intro'); const t = performance.now(); __VF.uiFrame(t); __VF.uiFrame(t + 16);
  const a = __VF.UI.INTRO.t; __VF.uiFrame(t + 60000); T.ok(__VF.UI.INTRO.t - a <= 100, 'advanced ' + (__VF.UI.INTRO.t - a)); T.eq(__VF.UI.NAV.cur, 'intro'); });
T.test('the intro never touches the fight state', () => { __VF.navReset('intro'); __VF.introAt(4000); T.eq(__VF.G.S, null); });
T.test('no endless CSS animation during the intro', () => { __VF.navReset('intro'); __VF.introAt(3800); T.eq(document.getAnimations().filter(a => a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity).length, 0); });
