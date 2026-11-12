// Interface U1, Task 12: every screen of the path fits the screen it is on (run at 640x360, 844x390, 1280x720, 1920x1080):
// each focusable element inside the window and at least 44 px (the grid slots aside), no text clipped, no sideways scroll.
const R = {mode: 'versus', chars: ['ren', 'kael'], winner: 0, wins: [2, 1], rounds: 3, hits: [9, 4], maxCombo: [4, 2], timeS: 90};
const SCREENS = [['title'], ['name'], ['menu'], ['vsopts'], ['select', {mode: 'versus', step: 0, picks: []}], ['select', {mode: 'versus', step: 1, picks: ['ren']}],
  ['arena', {mode: 'versus', chars: ['ren', 'kael']}], ['vs', {mode: 'versus', chars: ['ren', 'kael'], arena: 'cascata', dev: 'kb'}], ['results', R]];
for (const [id, p] of SCREENS) T.test('layout ' + id + (p && p.step ? ' G2' : ''), () => { __VF.CFG.ui.vs.minMs = 1e9; __VF.menu.toTitle(); if (id === 'name') __VF.UI.SV.name = null;
  if (id === 'results') { __VF.G.state = 'end'; } __VF.navReset(id, p); const root = $('sc-' + id);
  for (const el of root.querySelectorAll('[data-focus]')) { if (!el.getClientRects().length) continue; const r = el.getBoundingClientRect(), name = id + ': ' + (el.textContent.trim() || el.className);
    T.ok(r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1, name + ' off screen ' + JSON.stringify([r.left, r.top, r.right, r.bottom].map(Math.round)));
    T.ok(Math.min(r.width, r.height) >= 43.5 || el.classList.contains('uSlot'), name + ' too small ' + Math.round(r.width) + 'x' + Math.round(r.height)); }
  T.ok(document.scrollingElement.scrollWidth <= innerWidth, 'no sideways scroll'); T.ok(noOverflow(root), id + ': text clipped ' + noOverflow.last);
  for (const lg of root.querySelectorAll('.ulogo')) {   // the logo's crescent and cut stay on its word (they once flew off over the hero)
    const tx = lg.querySelector('.ulogoTx').getBoundingClientRect(), arc = lg.querySelector('.ulogoArc').getBoundingClientRect(), cut = lg.querySelector('.ulogoCut').getBoundingClientRect();
    T.ok(arc.left >= tx.left && arc.left <= tx.right && cut.left >= tx.left && cut.left <= tx.right, id + ': logo pieces off its word ' + JSON.stringify([tx.left, tx.right, arc.left, cut.left].map(Math.round))); }
  __VF.G.state = 'title'; __VF.CFG.ui.vs.minMs = 0; });
