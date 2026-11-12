// Interface: the fight HUD and the touch controls in the interface's style (Denis: «la lotta stona»; reference 02): serif
// type (Cinzel) for the names, the time, the banners and the captions, gold edges, the time in a hexagon, slanted
// portraits; the same elements and ids as the game's HUD (its own tests: hud.test.js, touch.test.js).
const cs = (id, p, pseudo) => getComputedStyle(typeof id === 'string' ? $(id) : id, pseudo || null)[p];
T.test('names, time, banner, combo and captions use the interface\'s serif type', () => { __VF.startMatch('versus', {seed: 1}); __VF.frame(2);
  for (const el of [$('name0'), $('timer'), $('banner'), document.querySelector('#combo0 i'), $('tP'), $('tGuard')]) T.ok(/Cinzel/.test(cs(el, 'fontFamily')), (el.id || el.className) + ' ' + cs(el, 'fontFamily'));
  T.ok(/Cormorant/.test(cs(document.querySelector('#combo0 b'), 'fontFamily')), 'combo number'); T.eq(cs('banner', 'fontStyle'), 'normal'); });
T.test('the time sits in a hexagon with a gold edge, the portraits are slanted', () => {
  const c = cs('timerBox', 'clipPath'); T.ok(c.startsWith('polygon') && c.split(',').length === 6, c);
  T.ok(/polygon\(16%/.test(cs(document.querySelector('#hs0 .face'), 'clipPath')), 'slanted portrait'); });
T.test('health bars are thin with a gold edge, the touch buttons dark glass with a gold ring', () => {
  const b = document.querySelector('#hs0 .bar').getBoundingClientRect(); T.ok(b.height <= Math.max(14, innerHeight * .04), 'thin ' + b.height);
  const ring = cs('tP', 'borderTopColor'); T.ok(/rgba?\(226, 196, 150/.test(ring), ring); });
T.test('each portrait slants like its gold frame (Kael\'s picture is mirrored: its clip must be too)', () => {
  const pts = c => c.replace(/^polygon\(|\)$/g, '').split(',').map(p => p.trim().split(/\s+/).map(parseFloat));
  for (const id of ['hs0', 'hs1']) {
    const frame = pts(cs(document.querySelector('#' + id + ' .face'), 'clipPath')), pic = document.querySelector('#' + id + ' .face i');
    const flip = new DOMMatrix(cs(pic, 'transform')).a < 0, seen = pts(cs(pic, 'clipPath')).map(([x, y]) => [flip ? 100 - x : x, y]);
    const key = a => a.map(p => p.join(' ')).sort().join(','); T.eq(key(seen), key(frame), id); } });
T.test('a dark band behind the top of the HUD keeps it readable on a bright arena', () => { T.ok(/gradient/.test(cs('hudTop', 'backgroundImage', '::before')), 'band'); });
T.test('the banners cost no filter (a blurred shadow on big text cost frames at every round start); a band shows behind them', () => {
  __VF.startMatch('versus', {seed: 1}); __VF.frame(2); T.ok($('banner').classList.contains('on')); T.eq(cs('banner', 'filter'), 'none');
  T.eq(+cs('hud', 'opacity', '::before'), 1, 'band behind the banner'); __VF.frame(160); T.ok(!$('banner').classList.contains('on')); T.eq(+cs('hud', 'opacity', '::before'), 0); __VF.menu.toTitle(); });
