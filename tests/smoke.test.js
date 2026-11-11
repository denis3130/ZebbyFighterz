T.test('boots to title', () => T.eq(__VF.G.state, 'title'));
T.test('index has no test API', () => T.ok(!/window\.__VF=/.test(TINDEX), 'index.html contiene __VF'));
T.test('assets object exists', () => T.eq(typeof __VF.ASSETS, 'object'));
