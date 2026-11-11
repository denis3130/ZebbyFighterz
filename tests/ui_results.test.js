// Interface U1, Task 11: the results (winner, score, XP counted up, level up), rematch, change fighter, back to the menu.
T.test('win: title, score, XP and save', () => { __VF.UI.SV.xp = 950; __VF.menu.toTitle(); __VF.bridgeStart({mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); __VF.G.S.wins = [2, 1]; endMatch(0);
  T.eq(__VF.UI.NAV.cur, 'results'); T.ok(txt('sc-results').includes('Vittoria')); T.ok(txt('sc-results').includes('Vince G1 · Ren')); T.ok(txt('sc-results').includes('2 – 1'));
  T.eq(__VF.UI.SV.xp, 950 + 60 + 40 + 20); T.ok(txt('sc-results').includes('Livello 2!')); T.eq(JSON.parse(localStorage.getItem('voidrise.save')).xp, 1070); T.eq(__VF.UI.SV.stats.won, 1); });
T.test('the XP parts are listed', () => { for (const t of ['Incontro giocato', '+60 XP', 'Round vinti ×2', '+40 XP', '+20 XP']) T.ok(txt('sc-results').includes(t), t); });
T.test('the winner is drawn large', () => { T.eq($('lyHero').dataset.c, 'ren'); T.ok(vis('lyHero')); });
T.test('the XP counter climbs on the frames shown', () => { const el = document.querySelector('#sc-results .rsXpN'), t = performance.now(); __VF.uiFrame(t); __VF.uiFrame(t + 50); const a = +el.textContent;
  for (let i = 2; i <= 24; i++) __VF.uiFrame(t + i * 50); T.ok(a > 0 && a < 120, 'climbing: ' + a); T.eq(el.textContent, '120'); T.ok($('sc-results').classList.contains('done')); });
T.test('confirm is ignored for a moment', () => { keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'results'); });
T.test('rematch keeps fighters and options', () => { later(__VF.CFG.menu.endGuardMs + 50, () => uiClick('Rivincita')); T.eq(__VF.G.state, 'fight'); T.eq(__VF.fighterOf(__VF.G.S, 0).char, 'ren'); });
T.test('change fighter goes to the select screen', () => { endMatch(1); T.ok(txt('sc-results').includes('Vince G2 · Kael')); later(__VF.CFG.menu.endGuardMs + 50, () => uiClick('Cambia personaggio'));
  T.eq(__VF.UI.NAV.cur, 'select'); T.eq(__VF.G.state, 'title'); T.eq(__VF.G.S, null); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'menu'); });
T.test('draw', () => { __VF.bridgeStart({mode: 'versus', chars: ['kael', 'ren'], arena: 'cascata', dev: 'kb'}); __VF.G.S.wins = [1, 1]; endMatch(2); T.ok(txt('sc-results').includes('Pareggio')); T.ok(txt('sc-results').includes('1 – 1')); });
T.test('back = main menu', () => { later(__VF.CFG.menu.endGuardMs + 50, () => __VF.navBack()); T.eq(__VF.UI.NAV.cur, 'menu'); T.eq(__VF.G.S, null); T.eq(__VF.G.state, 'title'); });
T.test('a loss gives the played XP only and no level jump', () => { __VF.UI.SV.xp = 100; __VF.bridgeStart({mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); __VF.G.S.wins = [0, 2]; endMatch(1);
  T.eq(__VF.UI.SV.xp, 160); T.ok(!txt('sc-results').includes('Livello 2!')); later(__VF.CFG.menu.endGuardMs + 50, () => __VF.navBack()); });
T.test('abandon from pause asks, then goes to the menu', () => { __VF.bridgeStart({mode: 'training', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); __VF.menu.pause(); later(800, () => uiClick('Abbandona')); T.ok(vis('uiOver'));
  later(800, () => uiClick('Abbandona')); return Promise.resolve().then(() => { T.eq(__VF.UI.NAV.cur, 'menu'); T.eq(__VF.G.state, 'title'); }); });
