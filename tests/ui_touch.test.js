// Interface U1, Task 12: the whole path by touch on a phone held sideways (run with --viewport 844x390 --touch --mobile):
// title → name → menu → Versus locale → Combatti → G1 → G2 → arena → VS → the fight with the touch controls.
T.test('the whole path by touch', () => { const V = __VF; V.UI.SV.name = null; V.navReset('title'); tapEl($('sc-title'), 1); T.eq(V.UI.NAV.cur, 'name');
  tapEl(byText('Conferma'), 2); T.eq(V.UI.NAV.cur, 'menu'); T.ok(V.UI.SV.name && V.UI.SV.name.length >= 3);
  tapEl(byText('Versus locale'), 3); tapEl(byText('Combatti'), 4); T.eq(V.UI.NAV.cur, 'select'); tapEl(slot(0), 5); tapEl(slot(1), 6); T.eq(V.UI.NAV.cur, 'arena');
  tapEl(byText('Conferma'), 7); T.eq(V.UI.NAV.cur, 'vs');
  return vsThrough(() => { T.eq(V.G.state, 'fight'); T.ok(vis('tP') && vis('tK') && vis('stickZone')); T.eq(V.UI.NAV.dev, 'touch'); T.ok(V.IN.assign[0].touch); }); });
T.test('pause by touch, then abandon with the confirm', () => { const V = __VF; tapEl($('tPause'), 8); T.eq(V.G.state, 'pause'); tapEl(byText('Abbandona'), 9); T.ok(vis('uiDlg'));
  tapEl(document.querySelector('#uiDlg [data-act="yes"]'), 10); return Promise.resolve().then(() => { T.eq(V.UI.NAV.cur, 'menu'); T.eq(V.G.state, 'title'); }); });
T.test('every tappable thing on the menu is at least 44 px', () => { __VF.menu.toTitle(); for (const el of document.querySelectorAll('#sc-menu [data-focus]')) { const r = el.getBoundingClientRect(); T.ok(Math.min(r.width, r.height) >= 43.5, el.textContent.trim() + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); } });
