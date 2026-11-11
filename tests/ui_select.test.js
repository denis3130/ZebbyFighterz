// Interface U1, Task 9: the fighter select (12 slots: Ren and Kael playable, Astra and Raigon locked by the pass, 8 coming;
// the focused fighter large with name and stats; G1 then G2 in a local versus; no mirror match yet).
const sel = p => __VF.navGo('select', Object.assign({mode: 'versus', step: 0, picks: []}, p));
T.test('grid: 12 slots, 2 playable, 2 pass locks, 8 coming', () => { __VF.navReset('menu'); sel(); T.eq(document.querySelectorAll('#sc-select .uSlot').length, 12);
  T.eq(document.querySelectorAll('#sc-select .uSlot.lock').length, 2); T.eq(document.querySelectorAll('#sc-select .uSlot.soon').length, 8); });
T.test('focus shows the fighter and stats', () => { navFocusSlot(1); T.ok(txt('uSelName').includes('Kael')); T.eq(document.querySelectorAll('#uSelStats .on').length, 3 + 4 + 3);
  navFocusSlot(0); T.ok(txt('uSelName').includes('Ren')); T.eq(document.querySelectorAll('#uSelStats .on').length, 4 + 3 + 2); });
T.test('Astra explains how to unlock', () => { navFocusSlot(2); T.ok(txt('uSelName').includes('Astra')); keyTap('Enter'); T.ok(txt('uiToast').includes('Pass gratuito · livello 50')); T.eq(__VF.UI.NAV.cur, 'select'); });
T.test('a coming slot says so', () => { navFocusSlot(7); keyTap('Enter'); T.ok(txt('uiToast').includes('Nuovo combattente in arrivo')); T.eq(__VF.UI.NAV.cur, 'select'); });
T.test('versus: G1 then G2, no mirror', () => { navFocusSlot(0); keyTap('Enter'); T.eq(__VF.UI.NAV.stack.at(-1).params.step, 1); T.ok(txt('sc-select').includes('Giocatore 2'));
  navFocusSlot(0); keyTap('Enter'); T.ok(txt('uiToast').includes('Scontro speculare in arrivo')); T.eq(__VF.UI.NAV.stack.at(-1).params.step, 1);
  navFocusSlot(1); keyTap('Enter'); T.eq(__VF.UI.NAV.cur, 'arena'); T.eq(JSON.stringify(__VF.UI.NAV.stack.at(-1).params.chars), '["ren","kael"]'); });
T.test('back from G2 returns to G1 with the focus on the first pick', () => { keyTap('Escape'); keyTap('Escape'); T.eq(__VF.UI.NAV.cur, 'select'); T.eq(__VF.UI.NAV.stack.at(-1).params.step, 0); T.eq(focusedSlot(), 0); });
T.test('training: one pick, the rival is the other fighter', () => { __VF.navReset('menu'); uiClick('Allenamento'); T.eq(__VF.UI.NAV.cur, 'select'); navFocusSlot(1); keyTap('Enter');
  T.eq(__VF.UI.NAV.cur, 'arena'); T.eq(JSON.stringify(__VF.UI.NAV.stack.at(-1).params.chars), '["kael","ren"]'); });
T.test('a tap on a fighter picks it', () => { __VF.navReset('menu'); uiClick('Versus locale'); uiClick('Combatti'); T.eq(__VF.UI.NAV.cur, 'select'); tapEl(slot(1), 31); T.eq(__VF.UI.NAV.stack.at(-1).params.step, 1);
  later(800, () => { tapEl(slot(0), 32); }); T.eq(__VF.UI.NAV.cur, 'arena'); T.eq(JSON.stringify(__VF.UI.NAV.stack.at(-1).params.chars), '["kael","ren"]'); });
T.test('the versus options travel with the picks', () => { const p = __VF.UI.NAV.stack.at(-1).params; T.eq(p.mode, 'versus'); T.ok(p.rounds > 0); T.ok(p.timeS !== undefined); });
T.test('the select starts on the last fighter used', () => { __VF.UI.SV.lastChar = 'kael'; __VF.navReset('menu'); sel(); T.eq(focusedSlot(), 1); __VF.UI.SV.lastChar = 'ren'; });
