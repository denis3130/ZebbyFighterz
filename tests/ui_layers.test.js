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
