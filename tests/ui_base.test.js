// Interface U1, Task 1: the UI configuration, the UI style sheet and WebP images are part of the page.
T.test('ui config is in CFG', () => { T.eq(__VF.CFG.ui.roster.length, 12); T.eq(__VF.CFG.ui.arenas[0].id, 'cascata'); T.eq(__VF.CFG.prog.levelXp, 1000); });
T.test('ui style is in the page', () => { T.eq(getComputedStyle(document.documentElement).getPropertyValue('--u-gold').trim(), '#d8a657'); });
T.test('webp assets are embedded as data URIs', () => { const k = Object.keys(__VF.ASSETS).find(k => k.endsWith('.webp')); T.ok(k, 'no webp'); T.ok(__VF.ASSETS[k].startsWith('data:image/webp;base64,')); });
