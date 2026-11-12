// Interface U1, Task 5: the layered scene behind the menus (sky, ruins, clouds, fog, the characters, embers), its parallax,
// quality levels, and its cost: hidden in a fight, and the menus do not draw the 3D scene.
const tx = id => new DOMMatrix(getComputedStyle($(id)).transform).e;
T.test('menu scene shows sky, ruins, fog and the hero', () => { __VF.menu.toTitle(); __VF.layersSet('menu', {hero: 'ren'}); for (const id of ['lySky', 'lyRuins', 'lyFog1', 'lyHero']) T.ok(vis(id), id); });
T.test('the hero picture follows the character', () => { __VF.layersSet('menu', {hero: 'kael'}); T.ok(getComputedStyle($('lyHero')).backgroundImage.includes('data:image/webp')); T.eq($('lyHero').dataset.c, 'kael'); });
T.test('a shift moves the far layers less than the near ones', () => { __VF.layersSet('menu', {hero: 'ren'}); __VF.UI.LY.settle(); const a = [tx('lySky'), tx('lyRuins'), tx('lyHero')];
  __VF.layersShift(1); __VF.UI.LY.settle(); const d = [tx('lySky') - a[0], tx('lyRuins') - a[1], tx('lyHero') - a[2]];
  T.ok(d[2] !== 0, 'the hero moved'); T.ok(Math.abs(d[0]) < Math.abs(d[1]) && Math.abs(d[1]) < Math.abs(d[2]), 'far < near: ' + d.join(' ')); __VF.layersShift(-1); });
T.test('navigating deeper shifts the layers, coming back returns them', () => { __VF.menu.toTitle(); __VF.UI.LY.settle(); const x0 = tx('lyRuins');
  __VF.navRegister({id: 'lyT', scene: 'menu'}); __VF.navGo('lyT'); __VF.UI.LY.settle(); T.ok(tx('lyRuins') !== x0, 'shifted'); __VF.navBack(); __VF.UI.LY.settle(); T.near(tx('lyRuins'), x0, .5); });
T.test('quality bassa: a still scene, no embers; alta: drifting fog, breathing hero, embers', () => { const t = performance.now(); __VF.menu.toTitle();
  __VF.layersQuality('bassa'); __VF.layersFrame(t); const f = $('lyFog1').style.translate, h = $('lyHero').style.scale; __VF.layersFrame(t + 5000);
  T.eq($('lyFog1').style.translate, f, 'fog still'); T.eq($('lyHero').style.scale, h, 'hero still'); T.eq(__VF.UI.LY.parts.length, 0);
  __VF.layersQuality('alta'); __VF.layersFrame(t); const f2 = $('lyFog1').style.translate, h2 = $('lyHero').style.scale; __VF.layersFrame(t + 1300);
  T.ok($('lyFog1').style.translate !== f2, 'fog drifts'); T.ok($('lyHero').style.scale !== h2, 'hero breathes');
  for (let i = 0; i < 30; i++) __VF.layersFrame(t + 1300 + i * 16); T.ok(__VF.UI.LY.parts.length > 0); });
T.test('no endless CSS animation in the menus (they slow the fight frames even once hidden: the scene moves from JS)', () => { __VF.menu.toTitle();
  const endless = document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.getComputedTiming().iterations === Infinity);
  T.eq(endless.length, 0, endless.map(a => (a.effect.target && a.effect.target.id) + ':' + a.animationName).join(' ')); });
T.test('quality auto picks media on a small device, alta otherwise', () => { T.eq(__VF.UI.LY.autoQuality({cores: 4, mem: 8}), 'media'); T.eq(__VF.UI.LY.autoQuality({cores: 8, mem: 2}), 'media'); T.eq(__VF.UI.LY.autoQuality({cores: 8, mem: 8}), 'alta'); T.eq(__VF.UI.LY.autoQuality({}), 'alta'); });
T.test('hidden during a fight, back in the menus', () => { __VF.startMatch('training', {seed: 1}); T.ok(!vis('uiLayers')); __VF.menu.pause(); T.ok(!vis('uiLayers'), 'pause shows the fight'); __VF.menu.toTitle(); T.ok(vis('uiLayers')); });
T.test('UI images stay under 3 MB in the page', () => { const n = Object.entries(__VF.ASSETS).filter(([k]) => k.startsWith('ui/') && k.endsWith('.webp')).reduce((a, [, v]) => a + v.length, 0); T.info('ui images ' + (n / 1e6).toFixed(2) + ' MB'); T.ok(n < 3e6); });
T.test('menus do not draw the 3D scene', () => { __VF.menu.toTitle(); const n = __VF.renderer.info.render.frame; __VF.tick(performance.now() + 1e5); T.eq(__VF.renderer.info.render.frame, n); });
T.test('a fight still draws it', () => { __VF.startMatch('training', {seed: 1}); const n = __VF.renderer.info.render.frame; __VF.tick(performance.now() + 2e5); T.ok(__VF.renderer.info.render.frame > n); __VF.menu.toTitle(); });
// The cut-out characters (sharp, 4x): each face where its scene wants it, from the face table CFG.ui.art (title: a fifth of
// the width from each side; results: the winner's at 36%), and the faces stay opaque (the fading starts past them).
T.test('the title and the results place each face from the face table', () => {
  const at = (id, share) => { const el = $(id), s = getComputedStyle(el), ax = +s.getPropertyValue('--ax');
    T.ok(ax > 0, id + ' --ax ' + ax); T.near(parseFloat(s.backgroundPositionX) + ax * innerHeight, share * innerWidth, 1.5); };
  __VF.UI.SV.name = 'Denis'; __VF.navReset('title'); __VF.UI.LY.settle(); at('lyHero', .2); at('lyRival', .8);
  const A = __VF.CFG.ui.art.ren_vs; T.near(+getComputedStyle($('lyHero')).getPropertyValue('--ax'), A[0] * A[1], .001);
  __VF.G.state = 'end'; __VF.navReset('results', {mode: 'versus', chars: ['ren', 'kael'], winner: 0, wins: [2, 1], rounds: 3, hits: [9, 4], maxCombo: [4, 2], timeS: 90});
  __VF.UI.LY.settle(); at('lyHero', .36); __VF.G.state = 'title'; __VF.navReset('menu'); });
T.test('the characters are sharp cut-outs: transparent around the figure, tall enough for a phone screen', async () => {
  for (const k of ['ren_full', 'kael_full', 'ren_vs', 'kael_vs', 'ren_win', 'intro_ren', 'intro_kael']) {
    const img = new Image(); img.src = __VF.ASSETS['ui/' + k + '.webp']; await img.decode();
    const box = k.startsWith('intro_') ? __VF.CFG.ui.intro[k.slice(6)] : null, full = box ? img.naturalHeight / (box[3] - box[1]) : img.naturalHeight;   // the intro's halves: the whole panel's height
    T.ok(full >= 1000, k + ' height ' + Math.round(full));
    const c = document.createElement('canvas'); c.width = 64; c.height = 64; const g = c.getContext('2d'); g.drawImage(img, 0, 0, 64, 64);
    const d = g.getImageData(0, 0, 64, 64).data; let clear = 0; for (let i = 3; i < d.length; i += 4) if (d[i] < 8) clear++;
    T.ok(clear > 64 * 64 * .04, k + ' has no transparent surroundings (' + clear + ')');
    if (__VF.CFG.ui.art[k]) T.near(img.naturalWidth / img.naturalHeight, __VF.CFG.ui.art[k][0], .01);
  } });
