// Interface U2: round pips for 1, 3 or 5 rounds, the full pause (Lista mosse, Impostazioni without leaving the fight),
// the settings saved at once (also from the main menu), «Gira il telefono» in the new style with no endless CSS animation.
const u2Open = () => { __VF.startMatch('versus', {seed: 3}); __VF.menu.pause(); };
const u2Pips = i => $('wins' + i).children.length;
T.test('one round pip per round to win: 1, 3 and 5 rounds', () => {
  for (const [r, n] of [[1, 1], [3, 2], [5, 3]]) { __VF.startMatch('versus', {seed: 1, rounds: r}); __VF.hudUpdate(__VF.G.S); T.eq(u2Pips(0), n, r + ' rounds'); T.eq(u2Pips(1), n); }
  const S = __VF.G.S; S.wins[0] = 3; __VF.hudUpdate(S); T.eq($('wins0').querySelectorAll('.on').length, 3, 'three lit'); __VF.menu.toTitle(); });
T.test('the pause has Riprendi, Lista mosse, Impostazioni and Abbandona, as the reference', () => { u2Open();
  for (const t of ['Riprendi', 'Lista mosse', 'Impostazioni', 'Ricomincia', 'Abbandona']) T.ok(byText(t), t); T.eq(focused(), 'Riprendi'); });
T.test('Lista mosse from the pause: the moves, the device in use first, back to the pause still paused', () => { u2Open(); __VF.UI.NAV.dev = 'kb';
  uiClick('Lista mosse'); T.eq(__VF.UI.NAV.cur, 'moves'); T.eq(__VF.G.state, 'pause');
  const rows = [...document.querySelectorAll('#sc-moves .mvRow')]; T.eq(rows.length, 12); T.ok(rows.some(r => r.textContent.includes('Presa') && r.textContent.includes('J + K')), 'keyboard inputs');
  T.eq(focused(), 'Tastiera'); uiClick('Tocco'); T.ok(document.querySelector('#sc-moves .mvGrid').textContent.includes('Levetta'), 'touch inputs');
  key('Escape'); keyUp('Escape'); T.eq(__VF.UI.NAV.cur, 'pause'); T.eq(__VF.G.state, 'pause'); T.eq(focused(), 'Lista mosse'); __VF.menu.resume(); });
T.test('Impostazioni from the pause, then back to the fight', () => { u2Open(); uiClick('Impostazioni'); T.eq(__VF.UI.NAV.cur, 'settings'); T.eq(__VF.G.state, 'pause');
  for (const t of ['Audio', 'Grafica', 'Comandi', 'Lingua']) T.ok(byText(t), t);
  key('Escape'); keyUp('Escape'); T.eq(__VF.UI.NAV.cur, 'pause'); uiClick('Riprendi'); T.eq(__VF.G.state, 'fight'); });
T.test('Impostazioni from the main menu (no more «In arrivo»)', () => { __VF.UI.SV.name = __VF.UI.SV.name || 'Lama'; __VF.menu.toTitle(); uiClick('Impostazioni');
  T.eq(__VF.UI.NAV.cur, 'settings'); T.ok(vis('sc-settings')); key('Escape'); keyUp('Escape'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('audio levels change with the arrows and are saved at once', () => { __VF.navReset('menu'); uiClick('Impostazioni'); const SV = __VF.UI.SV, m0 = SV.settings.music;
  T.ok(byText('Volume').textContent.includes(m0 + '%'));
  const st = document.querySelector('#sc-settings .ustep'); __VF.navFocus(st); key('ArrowRight'); keyUp('ArrowRight');
  T.eq(SV.settings.music, Math.min(100, m0 + 10)); T.eq(JSON.parse(localStorage.getItem('voidrise.save')).settings.music, SV.settings.music, 'saved');
  T.ok(document.querySelector('#sc-settings .stInfo').textContent.includes('in arrivo'), 'says the sounds are coming'); });
T.test('quality: Bassa stops the menu scene, saved; Auto chooses again', () => { __VF.navReset('menu'); uiClick('Impostazioni'); uiClick('Grafica');
  const st = [...document.querySelectorAll('#sc-settings .ustep')].find(e => e.textContent.includes('Scena')); __VF.navFocus(st);
  key('ArrowRight'); keyUp('ArrowRight'); T.eq(__VF.UI.SV.settings.quality, 'bassa'); T.eq(__VF.UI.LY.q, 'bassa');
  key('ArrowLeft'); keyUp('ArrowLeft'); T.eq(__VF.UI.SV.settings.quality, 'auto'); T.ok(['media', 'alta'].includes(__VF.UI.LY.q), __VF.UI.LY.q); });
T.test('Comandi shows the three devices; Lingua says other languages are coming', () => { __VF.navReset('menu'); uiClick('Impostazioni'); uiClick('Comandi');
  const t = $('sc-settings').textContent; for (const d of ['Tocco', 'Tastiera', 'Controller', 'J', 'X / Quadrato']) T.ok(t.includes(d), d);
  uiClick('Lingua'); uiClick('Italiano'); T.ok($('uiToast').textContent.includes('lingue'), 'toast'); });
T.test('nothing overflows the screen in the settings and the moves list', () => { for (const id of ['settings', 'moves']) { __VF.navReset(id);
  for (const e of $('sc-' + id).querySelectorAll('.mvRow,.stRow,.stCmdR,.utab')) { const r = e.getBoundingClientRect(); T.ok(r.left >= -1 && r.right <= innerWidth + 1, id + ' ' + e.textContent.slice(0, 20)); } } });
T.test('«Gira il telefono»: the new style and no endless CSS animation; the phone turns from JS', () => new Promise(done => {
  __VF.navReset('menu'); __VF.MN.rot = true; __VF.menuSync(); T.ok(vis('rotate'), 'shown');
  T.eq(getComputedStyle($('rotate').querySelector('svg')).animationName, 'none');
  T.eq(document.getAnimations().filter(a => a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity).length, 0);
  T.ok($('rotSub').textContent.length > 10);
  setTimeout(() => { T.ok(/rotate\(-?\d/.test($('rotate').querySelector('svg').style.transform || ''), 'turning ' + $('rotate').querySelector('svg').style.transform);
    __VF.MN.rot = false; __VF.menuSync(); T.ok(!vis('rotate'), 'hidden'); done(); }, 1500); }));
