// Progression (U1 part): XP from a finished match, the profile level, the player's statistics. The player of this
// device is G1 (side 0, whoever confirmed); G2 in a local versus plays as a guest. Training gives no XP and no stats.

// Level from total XP: level 1 at 0 XP, one more every CFG.prog.levelXp. into = XP inside the level, need = its size.
function progLevel(xp) {
  const L = CFG.prog.levelXp, x = Math.max(0, Math.floor(xp) || 0);
  return {lvl: 1 + Math.floor(x / L), into: x % L, need: L};
}
// r = a match result (bridgeResult). The parts are shown one by one on the results screen.
function progMatchXp(r) {
  const X = CFG.prog.xp, parts = [{label: 'Incontro giocato', xp: X.played}];
  if (r.winner === 0) parts.push({label: 'Vittoria', xp: X.win});
  const w = r.wins ? r.wins[0] : 0;
  if (w > 0) parts.push({label: 'Round vinti ×' + w, xp: X.round * w});
  return {xp: parts.reduce((a, p) => a + p.xp, 0), parts};
}
function progAddXp(sv, xp) {
  const before = progLevel(sv.xp).lvl;
  sv.xp += xp;
  return {before, after: progLevel(sv.xp).lvl};
}
// The match in G1's statistics (side 0): result, rounds won, hits landed, best combo, time, per fighter.
function progRecord(sv, r) {
  const st = sv.stats, c = r.chars[0], bc = st.byChar[c] || (st.byChar[c] = {played: 0, won: 0});
  st.played++; bc.played++;
  if (r.winner === 0) { st.won++; bc.won++; } else if (r.winner === 1) st.lost++; else st.draw++;
  st.rounds += r.wins ? r.wins[0] : 0;
  st.hits += r.hits ? r.hits[0] : 0;
  st.maxCombo = Math.max(st.maxCombo, r.maxCombo ? r.maxCombo[0] : 0);
  st.timeS += r.timeS || 0;
}
