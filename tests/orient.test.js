// "Gira il telefono" (Task 11): run with --viewport 390x844 --touch --mobile.
T.test('portrait shows the rotate screen and pauses a fight', () => { T.ok(vis('rotate')); __VF.startMatch('training',{seed:1,dummy:'fermo'}); window.dispatchEvent(new Event('resize')); T.eq(__VF.G.state,'pause'); });
T.test('landscape hides it', () => { setViewport(844,390); window.dispatchEvent(new Event('resize')); T.ok(!vis('rotate')); });
T.test('rotate while typing keeps the name', () => { setViewport(844, 390); window.dispatchEvent(new Event('resize')); __VF.UI.SV.name = null; __VF.navReset('name'); type($('uName'), 'Brace');
  setViewport(390, 844); window.dispatchEvent(new Event('resize')); T.ok(vis('rotate')); setViewport(844, 390); window.dispatchEvent(new Event('resize')); T.ok(!vis('rotate')); T.eq($('uName').value, 'Brace'); T.eq(__VF.UI.NAV.cur, 'name'); });
