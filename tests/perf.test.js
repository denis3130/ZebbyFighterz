// Task 12 — measurement probes with sanity assertions. Numbers are printed as INFO lines (copy them into docs/HANDOFF.md).
T.test('sim step under 0.3 ms', () => {
  const S = __VF.simCreate({seed: 2, mode: 'versus', chars: ['ren', 'kael']});
  const t = performance.now();
  for (let i = 0; i < 6000; i++) __VF.simStep(S, scripted(i), __VF.dummyInput(S, 1));
  const ms = (performance.now() - t) / 6000;
  T.info('sim ms/frame ' + ms.toFixed(4));
  T.ok(ms < .3, 'sim ms/frame ' + ms);
});
T.test('render ms per frame (headless, reference only)', () => {
  __VF.startMatch('versus', {seed: 2});
  const t = performance.now();
  for (let i = 0; i < 300; i++) __VF.frame(1);
  const ms = (performance.now() - t) / 300;
  T.info('render+sim ms/frame ' + ms.toFixed(2));
  T.ok(Number.isFinite(ms) && ms > 0, 'render ms ' + ms);
});
T.test('round length with and without hitstop', () => {
  const len = stop => {
    const k = JSON.stringify(__VF.CFG.stop);
    if (!stop) for (const c in __VF.CFG.stop) __VF.CFG.stop[c] = 0;
    const S = fight(); let n = 0, frozen = 0;
    while (S.phase === 'fight' && n < 99 * 60) { __VF.simStep(S, scripted(n), 0); n++; if (S.stop > 0) frozen++; }
    Object.assign(__VF.CFG.stop, JSON.parse(k));
    return {n, frozen};
  };
  const a = len(true), b = len(false), withStop = a.n, without = b.n;
  T.info('frames to KO: hitstop ' + withStop + ', no hitstop ' + without + ' (frozen frames: ' + a.frozen + ' / ' + b.frozen + ')');
  T.ok(Number.isFinite(withStop) && Number.isFinite(without), 'finite');
  T.ok(withStop >= without, 'hitstop must not shorten the round');
});
