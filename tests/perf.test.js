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
T.test('round length with and without hitstop (melee script, several offsets)', () => {
  // Melee-only attacker (walk in, P chain, heavy P, K, heavy K: no special, no throw) against an idle opponent. A frame-indexed
  // script is not real play: it only shows how much the freeze frames cost in this one pattern.
  const melee = (i, off) => {
    const k = (i + off) % 160;
    if (k < 30) return B.R;
    if (k === 35 || k === 45 || k === 55) return B.P;
    if (k >= 70 && k < 84) return B.P;
    if (k === 100 || k === 110) return B.K;
    if (k >= 125 && k < 139) return B.K;
    return 0;
  };
  const run = (off, stop) => {
    const saved = JSON.stringify(__VF.CFG.stop);
    try {
      if (!stop) for (const c in __VF.CFG.stop) __VF.CFG.stop[c] = 0;
      const S = fight(); let n = 0, frozen = 0;
      while (S.phase === 'fight' && n < 99 * 60) { __VF.simStep(S, melee(n, off), 0); n++; if (S.stop > 0) frozen++; }
      return {n, frozen, ko: S.phase !== 'fight' && F(S, 1).hp <= 0};
    } finally { Object.assign(__VF.CFG.stop, JSON.parse(saved)); }
  };
  const offs = [0, 17, 41, 73, 109], A = [], Z = [];
  for (const o of offs) { A.push(run(o, true)); Z.push(run(o, false)); }
  const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
  const mA = mean(A.map(r => r.n)), mZ = mean(Z.map(r => r.n));
  const share = mean(A.map(r => r.frozen / r.n));
  const rng = a => Math.min(...a.map(r => r.n)) + '-' + Math.max(...a.map(r => r.n));
  T.info('frames to KO (mean of ' + offs.length + ' offsets): hitstop ' + mA.toFixed(1) + ' [' + rng(A) + '], no hitstop ' + mZ.toFixed(1) + ' [' + rng(Z) + ']');
  T.info('difference ' + (mA - mZ).toFixed(1) + ' frames = ' + ((mA - mZ) / 60).toFixed(2) + ' s; frozen share with hitstop ' + (share * 100).toFixed(1) + '%; KO reached: ' + A.filter(r => r.ko).length + '/' + offs.length + ' with, ' + Z.filter(r => r.ko).length + '/' + offs.length + ' without');
  T.ok(A.concat(Z).every(r => Number.isFinite(r.n) && r.n > 0), 'finite');
  T.ok(mA >= mZ, 'hitstop must not shorten the round');
});
