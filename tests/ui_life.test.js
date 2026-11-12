// Interface: life in the screens (Denis: «poco vivo»). All motion is a function of time driven from JS: the characters slide
// in when a scene opens, the sky drifts, the rays breathe, the VS slams in (faces, mark, flash, shake, sparks), the results
// crash in, sparks burst over the screens only while they live, the logo's light sweeps, the focused button shines again.
const st = (el, p) => getComputedStyle(el)[p];
const RES = w => ({mode: 'versus', chars: ['ren', 'kael'], winner: w, wins: w ? [1, 2] : [2, 1], rounds: 3, hits: [9, 4], maxCombo: [4, 2], timeS: 90});
T.test('a scene opening slides its characters in from their side, then they rest', () => {
  const L = __VF.UI.LY, t = performance.now(); __VF.UI.SV.name = 'Denis'; __VF.navReset('menu'); __VF.navGo('vsopts');
  __VF.layersFrame(t + 16); const a = parseFloat(st($('lyHero'), 'translate')); T.ok(a < -1, 'hero (left) starts out to the left ' + a);
  const b = parseFloat(st($('lyRival'), 'translate')); T.ok(b > 1, 'rival (right) starts out to the right ' + b);
  __VF.layersFrame(t + 900); T.near(parseFloat(st($('lyHero'), 'translate')) || 0, 0, .01); T.near(parseFloat(st($('lyRival'), 'translate')) || 0, 0, .01); __VF.navReset('menu'); });
T.test('the sky drifts and the rays breathe in the menus, no rays behind the VS', () => {
  __VF.navReset('menu'); const t = performance.now(); __VF.layersFrame(t); const s1 = st($('lySky'), 'translate'), r1 = +st($('lyRays'), 'opacity');
  __VF.layersFrame(t + 4000); T.ok(st($('lySky'), 'translate') !== s1, 'sky moved'); T.ok(r1 > 0 && +st($('lyRays'), 'opacity') > 0, 'rays ' + r1);
  __VF.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); __VF.layersFrame(t + 5000); T.eq(+st($('lyRays'), 'opacity'), 0); __VF.navReset('menu'); });
T.test('the VS slams in: faces from the sides, the mark crashes with a flash, a shake and sparks, the names rise', () => {
  __VF.CFG.ui.vs.minMs = 1e9; __VF.navReset('menu'); __VF.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'});
  const r = $('sc-vs'), q = s => r.querySelector(s), V = __VF.UI.VS;
  __VF.vsLife(40); T.ok(parseFloat(st(q('.vsF.l'), 'translate')) < -20, 'left face coming'); T.ok(+st(q('.vsF.r'), 'opacity') === 0, 'right face not yet'); T.eq(+st(q('.vsMark'), 'opacity'), 0);
  __VF.vsLife(300); T.ok(+st(q('.vsMark'), 'scale') > 1.3, 'mark falling ' + st(q('.vsMark'), 'scale'));
  const n = __VF.UI.LY.bursts.length; V.burst = false; __VF.vsLife(420); T.ok(+st(q('.vsFlash'), 'opacity') > .5, 'flash');
  T.eq(__VF.UI.LY.bursts.length, n + 1, 'sparks'); T.ok(+st(q('.vsSide.l'), 'opacity') < .1, 'names not yet');
  let m = 0; for (const t of [400, 433, 466, 499, 532]) { __VF.vsLife(t); m = Math.max(m, Math.abs(parseFloat(st(q('.vsStage'), 'translate')) || 0)); } T.ok(m > .5, 'shake ' + m);
  __VF.vsLife(2000); T.near(parseFloat(st(q('.vsF.l'), 'translate')) || 0, 0, .05); T.eq(+st(q('.vsFlash'), 'opacity'), 0); T.eq(+st(q('.vsSide.r'), 'opacity'), 1); T.near(+st(q('.vsMark'), 'scale'), 1, .05);
  __VF.CFG.ui.vs.minMs = 2500; __VF.navReset('menu'); });
T.test('the results crash in: «Vittoria» from large, the laurels open, a burst of sparks', () => {
  __VF.G.state = 'end'; __VF.navReset('results', RES(0)); const r = $('sc-results'), title = r.querySelector('.rsTitle'), n0 = __VF.UI.LY.bursts.length;
  __VF.rsLife(r, 60); T.ok(+st(title, 'scale') > 1.3, 'large ' + st(title, 'scale'));
  __VF.rsLife(r, 400); T.ok(__VF.UI.LY.bursts.length > n0, 'sparks'); __VF.rsLife(r, 1e4); T.eq(+st(title, 'scale'), 1); T.eq(+st(title, 'opacity'), 1);
  __VF.G.state = 'title'; __VF.navReset('menu'); });
T.test('sparks show #uiFx only while they live, and never over a fight', () => {
  const fx = $('uiFx'), t = performance.now(); __VF.navReset('menu'); __VF.layersBurst(200, 150, 30, '#ffc46a'); __VF.uiFrame(t + 50); T.eq(st(fx, 'display'), 'block');
  __VF.uiFrame(t + 3000); T.eq(st(fx, 'display'), 'none'); T.eq(__VF.UI.LY.bursts.length, 0);
  __VF.layersBurst(200, 150, 30); __VF.uiFrame(performance.now() + 50); T.eq(st(fx, 'display'), 'block', 'sparks alive');
  __VF.startMatch('versus', {seed: 3}); T.eq(st(fx, 'display'), 'none', 'hidden by the fight'); T.eq(__VF.UI.LY.bursts.length, 0); __VF.menu.toTitle(); });
T.test('the VS mark stays centred on its place while it crashes down and after', () => {
  __VF.CFG.ui.vs.minMs = 1e9; __VF.navReset('menu'); __VF.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'});
  const m = $('sc-vs').querySelector('.vsMark');
  for (const t of [230, 300, 1000, 2400]) { __VF.vsLife(t); const r = m.getBoundingClientRect();
    T.near(r.left + r.width / 2, innerWidth / 2, 3); T.near(r.top + r.height / 2, innerHeight * .44, 3); }
  __VF.CFG.ui.vs.minMs = 2500; __VF.navReset('menu'); });
T.test('after its entrance the VS stands still (no style written every frame)', () => {
  __VF.CFG.ui.vs.minMs = 1e9; __VF.navReset('menu'); __VF.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'});
  const r = $('sc-vs'), els = [...r.querySelectorAll('.vsF,.vsMark,.vsMark i,.vsStage,.vsLines,.vsFlash,.vsSide')];
  const snap = () => els.map(e => [e.style.opacity, e.style.translate, e.style.scale].join(' ')).join('|');
  __VF.vsLife(1200); const a = snap(); __VF.vsLife(1900); __VF.vsLife(2600); T.eq(snap(), a); __VF.CFG.ui.vs.minMs = 2500; __VF.navReset('menu'); });
T.test('the focused entry\'s breathing restarts no CSS transition every frame', () => {
  __VF.navReset('menu'); const f = __VF.UI.NAV.focus, t = performance.now(); __VF.uiFrame(t + 10); __VF.uiFrame(t + 300); __VF.uiFrame(t + 600);
  T.eq(document.getAnimations().filter(a => a instanceof CSSTransition && a.effect.target === f && a.effect.pseudoElement === '::after').length, 0); });
T.test('the logo has a light that sweeps across its word, laid exactly over it', () => {
  __VF.navReset('title'); const lg = document.querySelector('#sc-title .ulogo'), a = lg.querySelector('.ulogoTx').getBoundingClientRect(), b = lg.querySelector('.ulogoSh .ulogoTx').getBoundingClientRect();
  T.near(b.left, a.left, .6); T.near(b.top, a.top, .6); T.near(b.width, a.width, .6);
  const e = lg.querySelector('.ulogoSh .ulogoTx'), base = 5200 * 1000; __VF.uiFrame(base + 650); const p1 = e.style.backgroundPosition; __VF.uiFrame(base + 900); T.ok(e.style.backgroundPosition !== p1, 'sweeping'); });
T.test('the focused button shines again every few seconds (a short, finite animation)', () => {
  __VF.navReset('menu'); __VF.navGo('vsopts'); const b = document.querySelector('#sc-vsopts .ub.main'); __VF.navFocus(b); const t0 = __VF.UI.NAV.focusAt;
  __VF.uiFrame(t0 + 100); T.ok(!b.classList.contains('shine')); __VF.uiFrame(t0 + 3300); T.ok(b.classList.contains('shine'), 'shine again');
  T.eq(document.getAnimations().filter(a => a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity).length, 0); __VF.navReset('menu'); });
T.test("the select's figures breathe and the light behind takes the fighter's colour", () => {
  __VF.navReset('menu'); __VF.navGo('select', {mode: 'versus', step: 0, picks: []}); const r = $('sc-select'), a = r.querySelector('.selAura.l');
  T.ok(['ren', 'kael'].includes(a.dataset.c), 'colour ' + a.dataset.c); __VF.uiFrame(performance.now() + 100); T.ok(+st(a, 'opacity') > .3, 'lit ' + st(a, 'opacity')); __VF.navReset('menu'); });
