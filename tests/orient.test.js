// "Gira il telefono" (Task 11): run with --viewport 390x844 --touch --mobile.
T.test('portrait shows the rotate screen and pauses a fight', () => { T.ok(vis('rotate')); __VF.startMatch('training',{seed:1,dummy:'fermo'}); window.dispatchEvent(new Event('resize')); T.eq(__VF.G.state,'pause'); });
T.test('landscape hides it', () => { setViewport(844,390); window.dispatchEvent(new Event('resize')); T.ok(!vis('rotate')); });
