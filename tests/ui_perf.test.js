// Interface U1: cost of one real-time tick (ms, headless Chromium, reference only) in the menus at each quality and in a fight.
function tickMs(n) { const V = __VF; let t = performance.now() + 3e5; const t0 = performance.now(); for (let i = 0; i < n; i++) { t += 1000 / 60; V.tick(t); } return (performance.now() - t0) / n; }
T.test('tick ms in the menus (alta, bassa) and in a fight', () => {
  const V = __VF; V.menu.toTitle(); V.layersQuality('alta'); const hi = tickMs(300); V.layersQuality('bassa'); const lo = tickMs(300); V.layersQuality('alta');
  V.startMatch('versus', {seed: 2}); const fight = tickMs(300); V.menu.toTitle();
  T.info('tick ms: menus alta ' + hi.toFixed(2) + ', menus bassa ' + lo.toFixed(2) + ', fight ' + fight.toFixed(2));
  T.ok(hi > 0 && lo > 0 && fight > 0);
});
