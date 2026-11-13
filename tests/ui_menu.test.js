// Interface U1, Task 8: the main menu (entries, the «Gioca» block with Arcade / Online / Versus locale, the player's chip)
// and the local versus options (rounds and time, sent into the match).
T.test('main menu items and chip', () => { __VF.UI.SV.name = 'Lama'; __VF.navReset('menu'); for (const t of ['Gioca', 'Allenamento', 'Profilo', 'Pass stagionale', 'Impostazioni', 'Arcade', 'Online', 'Versus locale']) T.ok(byText(t), t);
  T.ok(txt('sc-menu').includes('Lama')); T.ok(txt('sc-menu').includes('VOIDRISE')); T.eq(focused(), 'Gioca'); });
T.test('the hero is the last fighter used', () => { __VF.UI.SV.lastChar = 'kael'; __VF.navReset('menu'); T.eq($('lyHero').dataset.c, 'kael'); __VF.UI.SV.lastChar = 'ren'; __VF.navReset('menu'); T.eq($('lyHero').dataset.c, 'ren'); });
T.test('locked entries say so and do nothing', () => { __VF.navReset('menu'); uiClick('Pass stagionale'); T.eq(__VF.UI.NAV.cur, 'menu'); T.ok(txt('uiToast').includes('In arrivo'));
  uiClick('Online'); T.eq(__VF.UI.NAV.cur, 'menu'); T.ok(txt('uiToast').includes('online in arrivo')); uiClick('Arcade'); T.ok(txt('uiToast').includes('Arcade in arrivo')); });
T.test('keyboard: Gioca → Versus locale → the cards above it', () => { __VF.navReset('menu'); T.eq(focused(), 'Gioca'); keyTap('Enter'); T.eq(focused(), 'Versus locale');
  keyTap('ArrowUp'); T.ok(['Arcade', 'Online'].includes(focused()), focused()); });
T.test('Versus locale opens the options', () => { __VF.navReset('menu'); uiClick('Versus locale'); T.eq(__VF.UI.NAV.cur, 'vsopts'); });
T.test('versus options: rounds and time, sent into the match', () => { __VF.navReset('menu'); uiClick('Versus locale'); T.ok(txt('sc-vsopts').includes('Round: 3')); T.ok(txt('sc-vsopts').includes('Tempo: 99'));
  navFocusText('Round'); keyTap('ArrowRight'); navFocusText('Tempo'); keyTap('ArrowRight'); T.ok(txt('sc-vsopts').includes('∞')); T.ok(txt('sc-vsopts').includes('Round: 5'));
  uiClick('Combatti'); T.eq(__VF.UI.NAV.cur, 'select'); keyTap('Enter'); keyTap('Enter'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'vs');
  return vsThrough(() => { T.eq(__VF.G.state, 'fight'); T.eq(__VF.G.mode, 'versus'); T.eq(__VF.G.S.need, 3); T.eq(__VF.G.S.timer, -1); __VF.menu.toTitle(); }); });
T.test('the options stay for the session', () => { __VF.navReset('menu'); uiClick('Versus locale'); T.ok(txt('sc-vsopts').includes('Round: 5')); T.ok(txt('sc-vsopts').includes('∞')); });
T.test('back from the options returns to the menu, focus on Versus locale', () => { __VF.navReset('menu'); navFocusText('Versus locale'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'vsopts'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'menu'); T.eq(focused(), 'Versus locale'); });
T.test('the options screen has a touch back button', () => { __VF.navReset('menu'); uiClick('Versus locale'); uiClick('Indietro'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('Allenamento opens the fighter select', () => { __VF.navReset('menu'); uiClick('Allenamento'); T.eq(__VF.UI.NAV.cur, 'select'); T.ok(txt('sc-select').includes('Allenamento')); __VF.menu.toTitle(); });
T.test('rematch keeps the versus options', () => { __VF.startMatch('versus', {seed: 1, rounds: 1, timeS: 60}); __VF.menu.restart(); T.eq(__VF.G.S.need, 1); T.eq(__VF.G.S.timer, 3600); __VF.menu.toTitle(); });
