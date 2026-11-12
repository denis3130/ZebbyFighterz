// Interface: frames per second in the real loop (the page's own requestAnimationFrame, headless Chromium + SwiftShader:
// for comparing builds, not phones): the intro played in real time, the main menu, the VS and the first 5 s of a fight.
// In a file of its own: tests that draw hundreds of frames at once (ui_perf) leave the simulated GPU busy for seconds.
function rafFps(ms) { return new Promise(done => { let n = 0, long = 0, prev = 0; const t0 = performance.now();
  const f = now => { if (prev && now - prev > 50) long++; prev = now; n++; if (now - t0 < ms) requestAnimationFrame(f); else done([n / (ms / 1000), long]); };
  requestAnimationFrame(f); }); }
T.test('real-loop fps: intro, menu, VS, fight', () => new Promise(r => setTimeout(r, 800)).then(async () => {
  const V = __VF, out = [];
  V.UI.SV.introSeen = false; V.navReset('intro'); out.push(['intro', await rafFps(5000)]);
  V.UI.SV.name = V.UI.SV.name || 'Denis'; V.navReset('menu'); out.push(['menu', await rafFps(3000)]);
  V.CFG.ui.vs.minMs = 1e9; V.navGo('vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}); out.push(['VS', await rafFps(2500)]);
  V.CFG.ui.vs.minMs = 2500; V.bridgeWarm('cascata', ['ren', 'kael']); V.startMatch('versus', {seed: 2}); out.push(['fight', await rafFps(5000)]); V.menu.toTitle();
  T.info('real-loop fps ' + out.map(([k, [f, l]]) => k + ' ' + f.toFixed(1) + (l ? ' (' + l + ' over 50 ms)' : '')).join(', '));
  T.ok(out.every(([, [f]]) => f > 0)); }));
