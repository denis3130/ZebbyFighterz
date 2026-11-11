// The one door between the menus and the fight (spec §6): preload (real work: one hidden frame of the arena with the two
// fighters, so the shaders and textures are ready before the match and its first frames do not stall), start, the result
// of a match for the results screen, and the match statistics counted from the fight's events (read only).
// UIB.preload is the function the VS screen calls: a test may replace it to see the error path.
const UIB = {hits: [0, 0], maxCombo: [0, 0], S: null, shot: null, preload: null};

// The arena and the fighters drawn once, behind the menus (the 3D canvas is covered): compiles and uploads what the
// fight draws, so its first frames do not stall. Throws if the arena cannot be loaded.
function bridgeWarm(arena, chars) {
  if (arena !== 'cascata') throw new Error('arena ' + arena + ' not in the game yet');
  if (chars) renderCast(chars);
  renderFrame(simCreate({seed: 1, mode: 'versus', chars: chars || ['ren', 'kael']}), performance.now());
}
// The loading the VS screen waits for (a Promise, ready for arenas that will load their pictures over time).
function bridgePreload(arena, chars) {
  return new Promise((resolve, reject) => { try { bridgeWarm(arena, chars); resolve(); } catch (e) { reject(e); } });
}
UIB.preload = bridgePreload;
// A picture of the real arena for its card (no reference shows it): the backdrop drawn once, taken from the 3D canvas.
function bridgeArenaShot() {
  if (UIB.shot) return UIB.shot;
  try { renderFrame(null, performance.now()); UIB.shot = renderer.domElement.toDataURL('image/jpeg', .82); }
  catch (_) { UIB.shot = ''; }
  return UIB.shot;
}
// o = {mode, chars, arena, rounds, timeS, dev}: dev = the device that confirmed (G1). The player's last fighter is remembered.
function bridgeStart(o) {
  inputAssign(o.mode, o.dev || 'kb');
  inputMaskHeld();
  if (SV) { SV.lastChar = o.chars[0]; saveWrite(); }
  startMatch(o.mode, {seed: mnSeed(), dummy: 'fermo', chars: o.chars, rounds: o.rounds, timeS: o.timeS});
}
// Once per sim step (stepGame): hits landed by each side (strikes and projectiles) and the longest combo each side landed.
function uiEvents(S) {
  if (UIB.S !== S) { UIB.S = S; UIB.hits = [0, 0]; UIB.maxCombo = [0, 0]; }
  for (const e of S.ev) if (e.t === 'hit' || e.t === 'projHit') UIB.hits[e.side]++;
  for (let d = 0; d < 2; d++) { const c = fighterOf(S, d).combo; if (c > UIB.maxCombo[1 - d]) UIB.maxCombo[1 - d] = c; }
}
// The finished match for the results screen and the statistics: side 0 is G1, the player of this device.
function bridgeResult(S) {
  const own = UIB.S === S;
  return {mode: S.mode, chars: [fighterOf(S, 0).char, fighterOf(S, 1).char], winner: S.winner, wins: S.wins.slice(), rounds: S.round,
    hits: own ? UIB.hits.slice() : [0, 0], maxCombo: own ? UIB.maxCombo.slice() : [0, 0], timeS: Math.round(S.frame / 60)};
}
