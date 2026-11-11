// Interface U1, Task 2: the device save (versioned, safe when storage fails), XP, levels and match statistics.
const K = 'voidrise.save';
T.test('defaults when nothing is saved', () => { localStorage.removeItem(K); const s = __VF.saveLoad(); T.eq(s.v, 1); T.eq(s.xp, 0); T.eq(s.name, null); T.eq(s.settings.quality, 'auto'); });
T.test('round trip', () => { const s = __VF.saveLoad(); s.name = 'Lama'; s.xp = 1500; T.ok(__VF.saveWrite()); T.eq(__VF.saveLoad().name, 'Lama'); T.eq(__VF.saveLoad().xp, 1500); });
T.test('broken or old data: defaults', () => { localStorage.setItem(K, '{rotto'); T.eq(__VF.saveLoad().xp, 0); localStorage.setItem(K, JSON.stringify({v: 99, xp: 5})); T.eq(__VF.saveLoad().xp, 0); });
T.test('missing keys get their default (a save from before a new setting)', () => { localStorage.setItem(K, JSON.stringify({v: 1, name: 'Brace', xp: 40, settings: {}})); const s = __VF.saveLoad(); T.eq(s.name, 'Brace'); T.eq(s.settings.quality, 'auto'); T.eq(s.stats.played, 0); });
T.test('old FPS preference is carried over', () => { localStorage.removeItem(K); localStorage.setItem('voidrise.prefs', JSON.stringify({v: 1, fps: true})); T.eq(__VF.saveLoad().settings.showFps, true); localStorage.removeItem('voidrise.prefs'); });
T.test('storage that throws: playable, one toast', () => { const own = Object.getOwnPropertyDescriptor(window, 'localStorage'); let n = 0; const t = window.uiToast; window.uiToast = () => n++;
  Object.defineProperty(window, 'localStorage', {get() { throw new DOMException('denied', 'SecurityError'); }, configurable: true});
  try { T.eq(__VF.saveLoad().xp, 0); T.eq(__VF.saveWrite(), false); T.eq(__VF.saveWrite(), false); T.eq(n <= 1, true); }
  finally { if (own) Object.defineProperty(window, 'localStorage', own); else delete window.localStorage; window.uiToast = t; } });
T.test('levels from XP', () => { T.eq(__VF.progLevel(0).lvl, 1); T.eq(__VF.progLevel(999).lvl, 1); T.eq(__VF.progLevel(1000).lvl, 2); T.eq(__VF.progLevel(1250).into, 250); T.eq(__VF.progLevel(1250).need, 1000); });
T.test('match XP: played + win + rounds', () => { const r = {mode: 'versus', chars: ['ren', 'kael'], winner: 0, wins: [2, 1], hits: [20, 9], maxCombo: [5, 3], timeS: 120};
  const x = __VF.progMatchXp(r); T.eq(x.xp, 60 + 40 + 20); T.eq(x.parts.length, 3); T.eq(__VF.progMatchXp(Object.assign({}, r, {winner: 1, wins: [0, 2]})).xp, 60); });
T.test('record: stats of G1 and level up', () => { const s = __VF.saveDefaults(); s.xp = 950; const r = {mode: 'versus', chars: ['kael', 'ren'], winner: 0, wins: [2, 0], hits: [14, 3], maxCombo: [6, 2], timeS: 80};
  __VF.progRecord(s, r); const up = __VF.progAddXp(s, __VF.progMatchXp(r).xp); T.eq(s.stats.won, 1); T.eq(s.stats.byChar.kael.won, 1); T.eq(s.stats.maxCombo, 6); T.eq(up.before, 1); T.eq(up.after, 2); });
T.test('record: a loss and a draw', () => { const s = __VF.saveDefaults(); const r = {mode: 'versus', chars: ['ren', 'kael'], winner: 1, wins: [1, 2], hits: [5, 9], maxCombo: [2, 4], timeS: 99};
  __VF.progRecord(s, r); __VF.progRecord(s, Object.assign({}, r, {winner: 2, wins: [1, 1]})); T.eq(s.stats.lost, 1); T.eq(s.stats.draw, 1); T.eq(s.stats.played, 2); T.eq(s.stats.byChar.ren.played, 2); T.eq(s.stats.rounds, 2); T.eq(s.stats.timeS, 198); });
