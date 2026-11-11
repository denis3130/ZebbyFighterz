// Interface U1, Task 7: the title («Tocca per iniziare», following the device) and the player's name on the first launch.
T.test('prompt follows the device', () => { __VF.UI.NAV.dev = 'pad'; __VF.navReset('title'); T.ok(txt('sc-title').includes('Premi A'));
  __VF.UI.NAV.dev = 'kb'; __VF.navReset('title'); T.ok(txt('sc-title').includes('Premi un tasto')); __VF.UI.NAV.dev = 'touch'; __VF.navReset('title'); T.ok(txt('sc-title').includes('Tocca per iniziare')); });
T.test('the title shows Ren and Kael with the logo', () => { __VF.navReset('title'); T.eq($('lyHero').dataset.c, 'ren'); T.eq($('lyRival').dataset.c, 'kael'); T.ok(vis('lyHero') && vis('lyRival')); T.ok(txt('sc-title').includes('VOIDRISE')); });
T.test('first launch asks the name', () => { __VF.UI.SV.name = null; __VF.navReset('title'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'name'); T.ok($('uName').value.length >= 3); T.eq(txt('uNameErr'), ''); });
T.test('name errors and confirm', () => { const f = $('uName'); type(f, 'ab'); T.eq(txt('uNameErr'), 'Usa almeno 3 caratteri'); T.ok(byText('Conferma').classList.contains('off'));
  uiClick('Conferma'); T.eq(__VF.UI.NAV.cur, 'name', 'an invalid name is not confirmed');
  type(f, 'Lama#1'); T.eq(txt('uNameErr'), 'Solo lettere, numeri, spazi, - e _'); type(f, 'x'.repeat(17)); T.eq(txt('uNameErr'), 'Al massimo 16 caratteri');
  type(f, '  Lama Nera '); T.eq(txt('uNameErr'), ''); T.ok(!byText('Conferma').classList.contains('off')); uiClick('Conferma'); T.eq(__VF.UI.SV.name, 'Lama Nera'); T.eq(__VF.UI.NAV.cur, 'menu');
  T.eq(JSON.parse(localStorage.getItem('voidrise.save')).name, 'Lama Nera'); });
T.test('named player goes straight to the menu', () => { __VF.navReset('title'); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('Enter in the field confirms', () => { __VF.UI.SV.name = null; __VF.navReset('name'); const f = $('uName'); type(f, 'Brace'); f.focus(); keyTap('Enter'); T.eq(__VF.UI.SV.name, 'Brace'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('a tap on the field does not confirm it', () => { __VF.UI.SV.name = null; __VF.navReset('name'); tapEl($('uName'), 21); T.eq(__VF.UI.NAV.cur, 'name'); });
T.test('controller letter grid', () => { __VF.UI.SV.name = null; __VF.navReset('title'); padsAt([{}]); padTick(); padsAt([{buttons: {0: 1}}]); padTick(); padsAt([{}]); padTick(); T.eq(__VF.UI.NAV.cur, 'name'); T.ok(vis('uKeys'));
  type($('uName'), 'Ca'); later(800, () => { uiClick('⌫'); uiClick('B'); uiClick('Spazio'); uiClick('7'); T.eq($('uName').value, 'CB 7'); uiClick('Fatto'); });   // (after the tap of the test before: its own click is dropped for 700 ms)
  T.eq(__VF.UI.SV.name, 'CB 7'); T.eq(__VF.UI.NAV.cur, 'menu'); fakePads([]); padTick(); });
T.test('Backspace inside the field deletes, it does not go back', () => { __VF.UI.SV.name = null; __VF.navReset('title'); keyTap('Enter'); const f = $('uName'); type(f, 'Lama'); f.focus(); key('Backspace'); keyUp('Backspace'); T.eq(__VF.UI.NAV.cur, 'name'); f.blur(); });
T.test('Esc on the name goes back to the title', () => { keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'title'); });
