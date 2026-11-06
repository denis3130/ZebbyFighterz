// HUD (DOM, reads the sim state, never changes it). hudEvents(S) runs once per sim step and counts in frames: the red
// "chip" part of a health bar and the combo counter's lifetime. hudUpdate(S) runs once per drawn frame and only writes the
// DOM when a value changed.
const HUD = {S: null, chip: [1, 1], hold: [0, 0], hp: [1, 1], combo: [], el: {}, dom: {}};
function hudInit() {
  const e = HUD.el;
  for (const id of ['face0', 'face1', 'name0', 'name1', 'hpFill0', 'hpFill1', 'hpChip0', 'hpChip1', 'timer', 'wins0', 'wins1',
    'combo0', 'combo1', 'meter0', 'meter1', 'lvl0', 'lvl1', 'banner', 'hud']) e[id] = document.getElementById(id);
  e.face0.style.backgroundImage = 'url(' + ASSETS['ui/ren_face.jpg'] + ')';
  e.face1.style.backgroundImage = 'url(' + ASSETS['ui/kael_face.jpg'] + ')';
  HUD.seg = [0, 1].map(i => [...e['meter' + i].querySelectorAll('b')]);
  HUD.pip = [0, 1].map(i => [...e['wins' + i].children]);
  hudReset(null);
}
// A new match (a new S) starts from full bars and no counters.
function hudReset(S) {
  HUD.S = S; HUD.chip = [1, 1]; HUD.hold = [0, 0]; HUD.hp = [1, 1];
  HUD.combo = [{n: 0, last: 0, left: 0, seq: 0}, {n: 0, last: 0, left: 0, seq: 0}];
}
// One sim step. combo[a] = the combo side a is landing on side 1-a: shown from the 2nd hit, hidden hud.comboHide frames after it ends.
function hudEvents(S) {
  if (HUD.S !== S) hudReset(S);
  const H = CFG.hud;
  for (let d = 0; d < 2; d++) {
    const D = fighterOf(S, d), fill = D.hp / CFG.body.hp, k = HUD.combo[1 - d], c = D.combo;
    if (fill < HUD.hp[d]) HUD.hold[d] = H.chipDelay;          // hp lost (hit or chip damage): the red part waits
    HUD.hp[d] = fill;
    if (c > 0) HUD.hold[d] = H.chipDelay;                     // ...and keeps waiting while the combo goes on
    if (HUD.chip[d] < fill) HUD.chip[d] = fill;               // healed or refilled: no red part
    else if (HUD.hold[d] > 0) HUD.hold[d]--;
    else HUD.chip[d] = Math.max(fill, HUD.chip[d] - H.chipRate / 60);
    if (c > 0 && c < k.n) k.n = 0;                            // a new combo while the old counter lingers
    if (c >= 2 && c !== k.n) { k.n = c; k.seq++; }
    if (c === 0 && k.last > 0) k.left = H.comboHide;
    else if (c === 0 && k.left > 0 && --k.left === 0) k.n = 0;
    k.last = c;
  }
}
function hudSet(id, prop, v) {   // write the DOM only when the value changed
  const key = id + prop;
  if (HUD.dom[key] === v) return;
  HUD.dom[key] = v;
  if (prop === 't') HUD.el[id].textContent = v;
  else if (prop === 'x') HUD.el[id].style.transform = 'scaleX(' + v + ')';
  else if (prop === 'on') HUD.el[id].classList.toggle('on', v);
}
function hudBanner(S) {
  if (S.phase === 'intro') return 'ROUND ' + S.round;
  if (S.phase === 'fight') return S.pf < 40 ? 'COMBATTI!' : '';
  if (S.phase === 'ko') return 'K.O.';
  if (S.phase === 'timeup') return 'TEMPO!';
  if (S.phase === 'end') return S.winner === 2 ? 'PAREGGIO' : 'VINCE ' + fighterOf(S, S.winner).char.toUpperCase() + '!';
  return '';
}
function hudUpdate(S) {
  if (!S) return;
  if (HUD.S !== S) hudReset(S);
  hudSet('hud', 'on', true);
  const e = HUD.el, M = CFG.body.meterMax / 3;
  for (let i = 0; i < 2; i++) {
    const F = fighterOf(S, i), k = HUD.combo[i];
    hudSet('name' + i, 't', F.char.toUpperCase());
    hudSet('hpFill' + i, 'x', Math.max(0, Math.min(1, F.hp / CFG.body.hp)).toFixed(3));
    hudSet('hpChip' + i, 'x', Math.max(0, Math.min(1, HUD.chip[i])).toFixed(3));
    HUD.pip[i].forEach((p, j) => { const on = S.wins[i] > j; if (HUD.dom['p' + i + j] !== on) { HUD.dom['p' + i + j] = on; p.classList.toggle('on', on); } });
    hudSet('lvl' + i, 't', String(Math.min(3, Math.floor(F.meter / M))));
    HUD.seg[i].forEach((b, j) => { const v = Math.max(0, Math.min(1, (F.meter - j * M) / M)).toFixed(2); if (HUD.dom['s' + i + j] !== v) { HUD.dom['s' + i + j] = v; b.style.transform = 'scaleX(' + v + ')'; } });
    const f = fighterOf(S, 1 - i), shown = k.n >= 2 && (f.combo > 0 || k.left > 0);
    hudSet('combo' + i, 'on', shown);
    if (shown && HUD.dom['cs' + i] !== k.seq) {      // one bump per hit: restart the CSS animation with a reflow
      HUD.dom['cs' + i] = k.seq;
      const c = e['combo' + i];
      c.firstChild.textContent = k.n;
      c.classList.remove('bump'); void c.offsetWidth; c.classList.add('bump');
    }
  }
  hudSet('timer', 't', S.timer < 0 ? '∞' : String(Math.ceil(S.timer / 60)));
  const b = hudBanner(S), key = b + S.round + S.phase;
  if (b === '') hudSet('banner', 'on', false);
  else {
    if (HUD.dom.bk !== key) { HUD.dom.bk = key; e.banner.textContent = b; e.banner.classList.remove('on'); void e.banner.offsetWidth; e.banner.classList.add('on'); HUD.dom.banneron = true; }
    hudSet('banner', 'on', true);
  }
}
