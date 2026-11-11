// Interface U1, Task 4: the shared components (buttons, menu items, cards, tabs, steppers, chip), the notices and the confirm dialog.
T.test('locked button: no action, a «In arrivo» toast', () => { let n = 0; mount([__VF.cBtn({label: 'Online', act: () => n++, locked: true})]); uiClick('Online'); T.eq(n, 0); T.ok(vis('uiToast')); T.ok(txt('uiToast').includes('In arrivo')); });
T.test('locked with its own note', () => { mount([__VF.cCard({label: 'Foresta', locked: true, note: 'Arena in arrivo'})]); keyTap('Enter'); T.ok(txt('uiToast').includes('Arena in arrivo')); });
T.test('button act gets the device', () => { let d; mount([__VF.cBtn({label: 'Vai', act: dev => d = dev})]); keyTap('Enter'); T.eq(d, 'kb'); });
T.test('main button: the focusable part is the button itself', () => { let n = 0; mount([__VF.cBtn({label: 'Conferma', kind: 'main', act: () => n++})]); T.eq(focused(), 'Conferma'); keyTap('Enter'); T.eq(n, 1); });
T.test('stepper changes with left/right while focused', () => { let v; mount([__VF.cStepper({label: 'Round', values: [1, 3, 5], i: 1, onChange: x => v = x})]); keyTap('ArrowRight'); T.eq(v, 5); keyTap('ArrowRight'); T.eq(v, 5); T.ok(txt('sc-uiMount').includes('5')); keyTap('ArrowLeft'); T.eq(v, 3); });
T.test('stepper arrows work by touch', () => { let v; mount([__VF.cStepper({label: 'Tempo', values: [60, 90, 99, 0], i: 2, fmt: x => x ? String(x) : '∞', onChange: x => v = x})]);
  tapEl(document.querySelector('#sc-uiMount .ustep [data-d="1"]'), 5); T.eq(v, 0); T.ok(txt('sc-uiMount').includes('∞')); });
T.test('confirm: focus trapped, Esc says no, focus restored', () => { mount([__VF.cBtn({label: 'Abbandona', act: () => {}}), __VF.cBtn({label: 'Altro', act: () => {}})]); keyTap('ArrowDown'); let r = null;
  __VF.uiConfirm({title: 'Abbandonare?', text: 'La partita andrà persa.', yes: 'Abbandona', no: 'Annulla'}).then(x => r = x); keyTap('ArrowUp'); T.ok(focused() === 'Annulla' || focused() === 'Abbandona');
  keyTap('Escape'); return Promise.resolve().then(() => { T.eq(r, false); T.eq(focused(), 'Altro'); T.ok(!vis('uiDlg')); }); });
T.test('confirm: yes by touch', () => { mount([__VF.cBtn({label: 'X', act: () => {}})]); let r = null; __VF.uiConfirm({title: 'Sicuro?', text: '', yes: 'Sì', no: 'No'}).then(x => r = x);
  tapEl(byText('Sì'), 11); return Promise.resolve().then(() => { T.eq(r, true); }); });
T.test('tabs call onPick and tab() moves them', () => { let p = -1; mount([__VF.cTabs(['Audio', 'Grafica'], 0, i => p = i)]); keyTap('KeyE'); T.eq(p, 1); keyTap('KeyQ'); T.eq(p, 0); });
T.test('chip shows name and level', () => { __VF.UI.SV.name = 'Lama'; __VF.UI.SV.xp = 3100; mount([__VF.cChip()]); T.ok(txt('sc-uiMount').includes('Lama')); T.ok(txt('sc-uiMount').includes('Liv. 4')); });
T.test('a toast replaces the one before', () => { __VF.uiToast('Primo', 'info'); __VF.uiToast('Secondo', 'info'); T.eq(document.querySelectorAll('#uiToast').length, 1); T.ok(txt('uiToast').includes('Secondo')); });
T.test('a toast does not take the focus scope', () => { mount([__VF.cBtn({label: 'Uno', act: () => {}}), __VF.cBtn({label: 'Due', act: () => {}})]); __VF.uiToast('Avviso', 'info'); keyTap('ArrowDown'); T.eq(focused(), 'Due'); });
T.test('pause «Abbandona» asks first', () => { __VF.startMatch('training', {seed: 1}); __VF.menu.pause(); later(800, () => uiClick('Abbandona'));   // (a click right after the tap of the test before is that tap's own click: dropped)
  T.ok(vis('uiDlg')); T.eq(__VF.G.state, 'pause'); keyTap('Escape'); return Promise.resolve().then(() => { T.eq(__VF.G.state, 'pause'); T.ok(!vis('uiDlg')); __VF.menu.resume(); }); });
T.test('the pause screen hides the HUD and fits a 390 px tall screen', () => { __VF.startMatch('training', {seed: 1}); __VF.frame(1); T.ok(vis('hud'), 'shown in the fight'); __VF.menu.pause(); T.ok(!vis('hud'), 'hidden in the pause');
  for (const b of document.querySelectorAll('#sc-pause [data-focus]')) { if (!b.getClientRects().length) continue; const r = b.getBoundingClientRect(); T.ok(r.top >= 0 && r.bottom <= innerHeight, b.textContent + ' off screen'); }
  __VF.menu.resume(); __VF.frame(1); T.ok(vis('hud'), 'back in the fight'); });
