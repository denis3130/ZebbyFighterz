// --- posa.js: "Pose di Ren", key poses made with buttons (13/11/2026, second version). ---
// Denis (13/11): "mi puoi fare un'anteprima del personaggio dove posso muoverlo come voglio [...] per fare nuove
// animazioni? così capisci meglio cosa intendo"; his choice A: key poses as his sheets have them (posa 1, 2, 3...),
// a "Riproduci" that shows them in a row at one fixed speed, the timing told in words (the notes). The first version
// had handles to drag on every part; Denis found it too hard ("NO BRO TROPPO DIFFICILE") and chose ready positions,
// buttons only. A pose is a set of choices:
//   Braccio avanti / dietro   Guardia, Avanti, Alto, Al viso      (avanti = the lead arm, his left)
//   Mano avanti / dietro      Pugno, Socchiusa, Aperta            (one button each, it goes round)
//   Gamba avanti / dietro     A terra, Ginocchio su, Calcio
//   Busto                     Dritto, Avanti, Indietro
//   Altezza                   Normale, Basso, Alto
// and the body follows by itself: a straight arm brings its shoulder in (the hips and chest turn, the weight goes
// forward), a kick leans him back and lifts him on the standing leg (whose foot turns on its tip), both feet off the
// floor make a jump, the eyes stay on the opponent. The positions are the kit's (kit.js, loaded before this: the same
// Ren, base guard and solver). A change eases in (a few frames); "Riproduci" plays pose 1 to 2 to ... at one speed.
// Touch and mouse: the buttons (a drag on the picture turns the view, a double tap brings back the side view).
// Keyboard and controller: rows and choices (the hint). The poses are saved by themselves in the page's database
// (collection "animazioni", one document per animation, format 2: the choices by name), where Claude reads them, and
// on this device when the database is not there. Documents of the first version (format 1) stay and are not listed.

const PZ = {
  T: 24, hold: 40, back: 24, rest: 14,   // playing: frames from a pose to the next (0.4 s), held on the last, back to the first, held there
  ease: 12,                              // frames a changed pose takes to be reached (0.2 s: from rest to rest)
  max: 24,                               // poses in one animation
  poses: [], cur: 0, row: 0, kb: false, play: null, undo: [], D: null, Daf: NaN, ver: 0, lastPush: 0,
  id: null, name: 'Nuova animazione', note: '', db: null, col: null, list: [], loaded: false, edited: false, busy: false,
  dirty: false, retry: 0, timer: 0, pad: {}, padRep: {}, ui: {},
};
// the rows of choices: the pose's field, its label, its values [name, label]
const PZ_ROWS = [
  {key: 'bA', label: 'Braccio avanti', vals: [['guardia', 'Guardia'], ['avanti', 'Avanti'], ['alto', 'Alto'], ['viso', 'Al viso']]},
  {key: 'bD', label: 'Braccio dietro', vals: [['guardia', 'Guardia'], ['avanti', 'Avanti'], ['alto', 'Alto'], ['viso', 'Al viso']]},
  {key: 'mani', label: 'Mani', hands: [['mA', 'Mano avanti'], ['mD', 'Mano dietro']]},
  {key: 'gA', label: 'Gamba avanti', vals: [['terra', 'A terra'], ['ginocchio', 'Ginocchio su'], ['calcio', 'Calcio']]},
  {key: 'gD', label: 'Gamba dietro', vals: [['terra', 'A terra'], ['ginocchio', 'Ginocchio su'], ['calcio', 'Calcio']]},
  {key: 'busto', label: 'Busto', vals: [['dritto', 'Dritto'], ['avanti', 'Avanti'], ['indietro', 'Indietro']]},
  {key: 'alt', label: 'Altezza', vals: [['normale', 'Normale'], ['basso', 'Basso'], ['alto', 'Alto']]},
];
const PZ_HANDS = [['pugno', 'Pugno', 1], ['socchiusa', 'Socchiusa', .55], ['aperta', 'Aperta', 0]];   // [name, label, how closed]
const PZ_GUARD = {bA: 'guardia', mA: 'pugno', bD: 'guardia', mD: 'socchiusa', gA: 'terra', gD: 'terra', busto: 'dritto', alt: 'normale'};   // the kit's guard
const PZ_KEY = 'pose-ren-v2';   // localStorage: {id, doc} of the animation open on this device
const pzClone = o => JSON.parse(JSON.stringify(o));
const pzC = (x, a, b) => Math.max(a, Math.min(b, x));
const pzSame = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const pzNew0 = () => Object.assign({}, PZ_GUARD, {note: ''});
// a pose read back (the database's or this device's): each choice checked against the row's values
function pzFill(p) {
  const o = pzNew0();
  if (!p || typeof p !== 'object') return o;
  for (const r of PZ_ROWS) {
    if (r.vals && r.vals.some(v => v[0] === p[r.key])) o[r.key] = p[r.key];
    if (r.hands) for (const [k] of r.hands) if (PZ_HANDS.some(h => h[0] === p[k])) o[k] = p[k];
  }
  if (typeof p.note === 'string') o.note = p.note.slice(0, 300);
  return o;
}

// --- What a pose asks of the body: the style (on top of the kit's base guard), the feet, the arms' positions ---
function pzBody(c) {
  const b = {yaw: 0, chest: 0, leanL: 0, lx: 0, dip: 0, head: 0, jump: 0};
  if (c.busto === 'avanti') { b.leanL += 16; b.lx += .04; b.dip += .015; }
  else if (c.busto === 'indietro') { b.leanL -= 14; b.lx -= .05; }
  if (c.alt === 'basso') b.dip += .13; else if (c.alt === 'alto') b.dip -= .07;
  // a straight arm: its shoulder in (the kit's palm: hips -20, chest -25, 10 cm on); both: square to him (the double palm)
  const sA = c.bA === 'avanti', sD = c.bD === 'avanti';
  if (sA && sD) { b.yaw += 4; b.chest += 6; b.lx += .05; }
  else if (sA) { b.yaw -= 18; b.chest -= 22; b.lx += .07; }
  else if (sD) { b.yaw += 20; b.chest += 26; b.lx += .07; }
  // a kick leans him away from it and lifts him on the standing leg (the kit's kick: -34 degrees, 17 cm up); a knee less
  if (c.gA === 'calcio') { b.leanL -= 26; b.dip -= .15; b.yaw -= 5; b.lx -= .08; }
  else if (c.gA === 'ginocchio') { b.leanL -= 4; b.dip -= .06; b.lx -= .03; }
  if (c.gD === 'calcio') { b.leanL -= 22; b.dip -= .12; b.yaw -= 25; b.chest += 10; b.lx += .1; }   // (the rear hip comes forward)
  else if (c.gD === 'ginocchio') { b.leanL -= 2; b.dip -= .05; b.lx += .03; }
  if (c.gA !== 'terra' && c.gD !== 'terra') b.jump = .35;   // both feet off the floor: a jump
  b.leanL = pzC(b.leanL, -42, 32);
  b.head = -.5 * b.leanL;   // (the eyes stay on the opponent)
  return b;
}
// the feet: along the line (m, from the guard's spot), up, the heel (deg), the turn on the tip (deg), the toes' point in
// the air (deg: > 0 pointed, < 0 flexed, the sole forward: the kit's kick strikes with it) and how much in the air (0..1)
function pzFeet(c, b) {
  const F = {L: {x: 0, up: 0, heel: 0, yaw: 0, point: 30, air: 0}, R: {x: 0, up: 0, heel: 0, yaw: 0, point: 30, air: 0}};
  if (c.gA === 'ginocchio') Object.assign(F.L, {x: -.12, up: .5, point: 40, air: 1});
  else if (c.gA === 'calcio') Object.assign(F.L, {x: .33, up: 1.02, point: -5, air: 1});
  if (c.gD === 'ginocchio') Object.assign(F.R, {x: .55, up: .55, point: 40, air: 1});   // (the rear knee comes forward, up in front)
  else if (c.gD === 'calcio') Object.assign(F.R, {x: 1.15, up: .9, point: -5, air: 1});
  if (c.gA === 'calcio' && c.gD === 'terra') F.R.yaw = -30;   // the standing foot turned on its tip (the kit's)
  if (c.gD === 'calcio' && c.gA === 'terra') F.L.yaw = -40;
  if (b.jump) { F.L.up += b.jump; F.R.up += b.jump; }
  return F;
}
// The arms' positions, as the kit's poses are: (A, hand) -> {p: wrist, f: fingers' way, n: palm's way, e: elbow
// hint, s: 1 a straight wrist (the fist continues the forearm)}. A: the kit's frames (l: along the fight line
// [forward, up, side], c: the chest's [across, up, forward]), shoulders sL / sR, the chest C1, the guard G.
const PZ_UP = () => RB_UP.clone(), PZ_LN = () => RB_LINE.clone();
const pzPalm = () => ({f: PZ_UP().addScaledVector(RB_LINE, .2).normalize(), n: PZ_LN().addScaledVector(RB_UP, -.12).normalize(), s: 0});   // the kit's palm strike
const PZ_ARM = {
  L: {
    guardia: (A, h) => Object.assign({p: A.G.L.p, e: A.G.L.e}, h === 'aperta' ? {f: A.l([.55, .8, -.15]).normalize(), n: A.l([0, -.2, -1]).normalize(), s: 0} : {f: A.G.L.f, n: A.G.L.n, s: 0}),
    avanti: (A, h) => Object.assign({p: A.sL.clone().addScaledVector(RB_LINE, .965 * A.armL), e: A.l([0, -1, .3]).normalize()}, h === 'aperta' ? pzPalm() : {f: PZ_LN(), n: PZ_UP().negate(), s: 1}),
    alto: (A, h) => Object.assign({p: A.l([.2, .33, -.02]).add(A.sL), e: A.l([.35, -1, .55]).normalize()}, h === 'aperta' ? {f: PZ_UP().addScaledVector(RB_LINE, .15).normalize(), n: PZ_LN(), s: 0} : {f: PZ_UP(), n: A.l([0, 0, -1]), s: 1}),
    viso: (A, h) => h === 'aperta' ? {p: A.l([.18, .2, -.04]).add(A.sL), e: A.l([.15, -1, .25]).normalize(), f: PZ_UP(), n: PZ_LN(), s: 0}   // (the kit's cover)
      : {p: A.l([.2, .16, -.08]).add(A.sL), e: A.l([.2, -1, .3]).normalize(), f: A.l([.3, 1, 0]).normalize(), n: A.l([0, 0, -1]), s: 1},
  },
  R: {
    guardia: (A) => ({p: A.G.R.p, e: A.G.R.e, f: A.G.R.f, n: A.G.R.n, s: 0}),
    avanti: (A, h) => Object.assign({p: A.sR.clone().addScaledVector(RB_LINE, .965 * A.armR).addScaledVector(RB_UP, -.06), e: A.c([-.2, -1, -.1]).normalize()}, h === 'aperta' ? pzPalm() : {f: PZ_LN(), n: PZ_UP().negate(), s: 1}),
    alto: (A, h) => Object.assign({p: A.l([.22, .31, .05]).add(A.sR), e: A.c([-.8, -.45, .1]).normalize()}, h === 'aperta' ? {f: PZ_UP(), n: PZ_LN(), s: 0} : {f: PZ_UP(), n: A.c([1, 0, 0]), s: 1}),
    viso: (A, h) => h === 'aperta' ? {p: A.c([-.17, .2, .12]).add(A.C1), e: A.c([-.3, -1, -.1]).normalize(), f: PZ_UP().addScaledVector(RB_LINE, .1).normalize(), n: PZ_LN(), s: 0}   // (the kit's rHead)
      : {p: A.c([-.04, .26, .2]).add(A.C1), e: A.c([-.4, -1, -.2]).normalize(), f: A.c([1, .4, .2]).normalize(), n: A.c([0, 0, -1]), s: 0},   // (the kit's rChin)
  },
};
// A pose's numbers (body, feet, and per arm the weight of each position|hand), so two poses mix and a pose eases
// into another: every change is continuous.
function pzTarget(c) {
  const b = pzBody(c);
  return {b, f: pzFeet(c, b), arm: {L: {[c.bA + '|' + c.mA]: 1}, R: {[c.bD + '|' + c.mD]: 1}}};
}
function pzMixT(a, b, u) {
  const num = (x, y) => { const o = {}; for (const k in x) o[k] = x[k] + (y[k] - x[k]) * u; return o; };
  const w = (x, y) => { const o = {}; for (const k in x) o[k] = x[k] * (1 - u); for (const k in y) o[k] = (o[k] || 0) + y[k] * u; for (const k in o) if (o[k] < 1e-4) delete o[k]; return o; };
  return {b: num(a.b, b.b), f: {L: num(a.f.L, b.f.L), R: num(a.f.R, b.f.R)}, arm: {L: w(a.arm.L, b.arm.L), R: w(a.arm.R, b.arm.R)}};
}
// the pose drawn at fighter state F: while playing, the mix of two poses; else the pose being edited, reached from
// wherever the drawing was over PZ.ease frames (a tap in the middle of a change does not jump)
function pzDrawn(F) {
  const P = PZ.poses;
  if (!P.length) return pzTarget(PZ_GUARD);
  if (F.af === PZ.Daf && PZ.D && PZ.Dv === PZ.ver) return PZ.D;
  let D;
  if (PZ.play && P.length > 1) D = pzPlayAt(F.af - PZ.play.f0);
  else {
    const T = pzTarget(P[Math.min(PZ.cur, P.length - 1)]);
    if (PZ.D && PZ.Dv !== PZ.ver) PZ.tr = {from: PZ.D, f0: F.af};   // (a change: it starts here)
    const tr = PZ.tr;
    if (tr && F.af < tr.f0) tr.f0 = F.af;
    const u = tr ? rnSm((F.af - tr.f0) / PZ.ease) : 1;
    D = u >= 1 ? T : pzMixT(tr.from, T, u);
    if (u >= 1) PZ.tr = null;
  }
  PZ.D = D; PZ.Daf = F.af; PZ.Dv = PZ.ver;
  return D;
}
// Playing: pose 1 to 2 to ... n, PZ.T frames each (from rest to rest: each key pose is reached and seen), held on the
// last, then back to the first and held there; again.
function pzPlayAt(t) {
  const P = PZ.poses, n = P.length, run = (n - 1) * PZ.T, len = run + PZ.hold + PZ.back + PZ.rest, at = PZ.play.at;
  t = ((t % len) + len) % len;
  if (t < run) { const i = Math.min(n - 2, Math.floor(t / PZ.T)); at.a = i; at.b = i + 1; at.back = false; return pzMixT(pzTarget(P[i]), pzTarget(P[i + 1]), rnSm((t - i * PZ.T) / PZ.T)); }
  t -= run;
  if (t < PZ.hold) { at.a = at.b = n - 1; at.back = false; return pzTarget(P[n - 1]); }
  t -= PZ.hold;
  if (t < PZ.back) { at.a = n - 1; at.b = 0; at.back = true; return pzMixT(pzTarget(P[n - 1]), pzTarget(P[0]), rnSm(t / PZ.back)); }
  at.a = at.b = 0; at.back = true;
  return pzTarget(P[0]);
}

// --- The act: style, feet, arms, head, the legs in the air, hands ---
RB.pin.posa = 1;
RB.styleFor.posa = (y, F) => {
  const b = pzDrawn(F).b;
  y.yaw = b.yaw; y.chest = b.chest; y.leanL = b.leanL; y.lx = b.lx; y.dip = .004 + b.dip - b.jump; y.head = b.head;
  rkBase(y);
};
RB.feetFor.posa = (s, c, st, L, F) => {
  const f = pzDrawn(F).f[s];
  rkFoot(s, c, st, L, f.heel * (1 - f.air), f.yaw, f.x, f.up, 0);   // (in the air the leg sets the foot: rkKickLeg below)
};
// where a two-bone arm from shoulder sh, its wrist at tgt, puts its elbow for hint e (upper and lower lengths a, b),
// as rsArm does (the chest's own push left out): a point, so that two can be mixed
function pzElbow(sh, tgt, e, a, b) {
  const dir = tgt.clone().sub(sh), full = dir.length(), d = pzC(full, Math.abs(a - b) + 1e-3, (a + b) * .995);
  dir.multiplyScalar(1 / (full || 1e-9));
  const P = e.clone().addScaledVector(dir, -e.dot(dir));
  if (P.lengthSq() < 1e-8) P.set(0, -1, 0).addScaledVector(dir, dir.y);
  P.normalize();
  const cos = (a * a + d * d - b * b) / (2 * a * d), sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  return sh.clone().addScaledVector(dir, a * cos).addScaledVector(P, a * sin);
}
RB.post.push((md, p, F) => {
  if (F.act !== 'posa' || F.air) return;
  const D = pzDrawn(F), W = rbFK(md, p, RB.W), ix = md.index, C1 = W.p[ix.Spine01].clone();
  const c = a => rsChest(md, W, a, new THREE.Vector3()), l = a => rsVec(a, new THREE.Vector3());
  const sL = W.p[ix.LeftArm].clone(), sR = W.p[ix.RightArm].clone();
  const armL = sL.distanceTo(W.p[ix.LeftForeArm]) + W.p[ix.LeftForeArm].distanceTo(W.p[ix.LeftHand]);
  const armR = sR.distanceTo(W.p[ix.RightForeArm]) + W.p[ix.RightForeArm].distanceTo(W.p[ix.RightHand]);
  const G = {L: {p: l(RS.lead.dir).normalize().multiplyScalar(RS.lead.reach * armL).add(sL), f: l(RS.lead.fing).normalize(), n: l(RS.lead.palm).normalize(), e: l(RS.lead.elbow).normalize()},
    R: {p: c(RS.rear.pos).add(C1), f: c(RS.rear.fing).normalize(), n: c(RS.rear.palm).normalize(), e: c(RS.rear.elbow).normalize()}};
  const A = {W, ix, C1, c, l, sL, sR, armL, armR, G};
  for (const s of ['L', 'R']) {   // each arm: its positions mixed by their weights (one, but while it changes)
    const t = {p: new THREE.Vector3(), f: new THREE.Vector3(), n: new THREE.Vector3(), e: new THREE.Vector3(), s: 0};
    const sh = s === 'L' ? sL : sR, n = s === 'L' ? 'Left' : 'Right', ua = sh.distanceTo(W.p[ix[n + 'ForeArm']]), la = W.p[ix[n + 'ForeArm']].distanceTo(W.p[ix[n + 'Hand']]);
    const all = Object.entries(D.arm[s]).map(([k, w]) => { const [pos, hand] = k.split('|'); return {w, a: PZ_ARM[s][pos](A, hand)}; });
    let best = all[0];
    for (const x of all) {
      const {a, w} = x;
      t.p.addScaledVector(a.p, w); t.f.addScaledVector(a.f, w); t.n.addScaledVector(a.n, w); t.e.addScaledVector(a.e, w); t.s += a.s * w;
      if (w > best.w) best = x;
    }
    for (const k of ['f', 'n', 'e']) { if (t[k].lengthSq() < 1e-6) t[k].copy(best.a[k]); t[k].normalize(); }   // (two ways that cancel: the stronger one)
    if (all.length > 1) {
      // between two positions the elbow turns about the arm's line by the mixed angle of where each puts it, from its
      // outer side: it goes round by the side, as an arm that rises does (the hints' ways mixed can lie along the arm
      // half way, and the elbow would swing round it at once)
      const dir = t.p.clone().sub(sh).normalize(), r0 = c([s === 'L' ? 1 : -1, -.5, 0]).normalize();
      r0.addScaledVector(dir, -r0.dot(dir));
      if (r0.lengthSq() < 1e-4) r0.copy(c([0, 0, 1])).addScaledVector(dir, -c([0, 0, 1]).dot(dir));
      r0.normalize();
      const r1 = new THREE.Vector3().crossVectors(dir, r0), ang = x => { const v = pzElbow(sh, x.a.p, x.a.e, ua, la).sub(sh); return Math.atan2(v.dot(r1), v.dot(r0)); };
      const a0 = ang(best);
      let sum = 0;
      for (const x of all) { const d = ang(x) - a0; sum += x.w * (a0 + Math.atan2(Math.sin(d), Math.cos(d))); }
      t.e.copy(r0).multiplyScalar(Math.cos(sum)).addScaledVector(r1, Math.sin(sum));
    }
    rsArm(md, p, rbFK(md, p, RB.W), s, t.p, t.e, t.f, t.n, 1, t.s);
  }
  mdBoneTurn(p, ix.Head, MD_Y, RK.g.headYaw);   // the eyes on the opponent (the nod: the style's)
  for (const s of ['L', 'R']) { const f = D.f[s]; if (f.air > 0) rkKickLeg(md, p, {s, pole: [1, 1, 0], point: f.point, air: f.air}, 0); }
});
RN.hooks.applied.push((it, F) => {   // the hands: a fist, half closed, open (fingers together, the thumb along them)
  if (!it.fingers || F.act !== 'posa') return;
  const D = pzDrawn(F), k = {L: 0, R: 0};
  for (const s of ['L', 'R']) for (const [key, w] of Object.entries(D.arm[s])) k[s] += w * PZ_HANDS.find(h => h[0] === key.split('|')[1])[2];
  for (let i = 0; i < it.fingers.length; i++) rkSetFinger(it, i, /^Left/.test(it.fingers[i].name) ? k.L : k.R, true);
});

// --- Editing: a choice, the hands, the poses ---
function pzPush() {
  PZ.undo.push({poses: pzClone(PZ.poses), cur: PZ.cur});
  if (PZ.undo.length > 80) PZ.undo.shift();
}
function pzStop() { if (PZ.play) pzPlay(); }
function pzChoose(key, v) {
  const P = PZ.poses[PZ.cur];
  if (!P || P[key] === v) return;
  pzStop(); pzPush();
  P[key] = v; pzChanged();
}
function pzHand(key, dir) {   // the next (or previous) hand: pugno, socchiusa, aperta, round again
  const P = PZ.poses[PZ.cur];
  if (!P) return;
  const i = PZ_HANDS.findIndex(h => h[0] === P[key]);
  pzChoose(key, PZ_HANDS[(i + (dir || 1) + PZ_HANDS.length) % PZ_HANDS.length][0]);
}
function pzStepRow(dir) {   // keys and controller: the selected row's previous or next choice
  const r = PZ_ROWS[PZ.row], P = PZ.poses[PZ.cur];
  if (!P) return;
  if (r.hands) { pzHand(r.hands[dir < 0 ? 0 : 1][0]); return; }
  const i = r.vals.findIndex(v => v[0] === P[r.key]);
  pzChoose(r.key, r.vals[pzC(i + dir, 0, r.vals.length - 1)][0]);
}
function pzRowGo(dir) { PZ.row = (PZ.row + dir + PZ_ROWS.length) % PZ_ROWS.length; PZ.kb = true; PZ.ui.dirty = true; }
function pzUndo() {
  const u = PZ.undo.pop();
  if (!u) { pzStatus('Niente da annullare'); return; }
  pzStop();
  PZ.poses = u.poses; PZ.cur = Math.min(u.cur, u.poses.length - 1);
  pzChanged();
}
function pzGuard() {
  const P = PZ.poses[PZ.cur];
  if (!P) return;
  const G = Object.assign({}, PZ_GUARD, {note: P.note});
  if (pzSame(G, P)) return;
  pzStop(); pzPush(); PZ.poses[PZ.cur] = G; pzChanged();
}
function pzGo(i) {
  if (!PZ.poses.length) return;
  pzStop();
  const j = pzC(i, 0, PZ.poses.length - 1);
  if (j === PZ.cur) return;
  PZ.cur = j; PZ.ver++; PZ.ui.dirty = true;
}
function pzAdd() {
  if (PZ.poses.length >= PZ.max) { pzStatus('Massimo ' + PZ.max + ' pose'); return; }
  pzStop(); pzPush();
  const P = pzClone(PZ.poses[PZ.cur] || pzNew0()); P.note = '';
  PZ.poses.splice(PZ.cur + 1, 0, P); PZ.cur++; PZ.pop = PZ.cur;
  pzChanged();
}
function pzDel() {
  if (PZ.poses.length < 2) { pzStatus('Serve almeno una posa'); return; }
  pzStop(); pzPush();
  PZ.poses.splice(PZ.cur, 1); PZ.cur = Math.min(PZ.cur, PZ.poses.length - 1);
  pzChanged(); pzStatus('Posa eliminata (Annulla la riporta)');
}
function pzPlay() {
  if (PZ.play) { PZ.play = null; PZ.ver++; PZ.ui.dirty = true; return; }
  if (PZ.poses.length < 2) { pzStatus('Fai almeno 2 pose («+ Posa») per riprodurle'); return; }
  PZ.play = {f0: VW.F.af + (RN_D.k || 0), at: {a: 0, b: 1, back: false}}; PZ.ver++; PZ.ui.dirty = true;
}
function pzView() { const side = Math.abs(VW.yaw - F3_YAW) < .02; VW.yaw = side ? F3_YAW - Math.PI / 4 : F3_YAW; PZ.ui.dirty = true; }   // the game's side view, or three-quarters

// --- Saving: the database (collection "animazioni"), this device, the data for Claude ---
const PZ_LEGENDA = 'Pose di Ren, formato 2 (preview/ren-anim/mods/posa.js). Ogni posa sono le scelte: bA braccio avanti e bD braccio dietro '
  + '(guardia, avanti, alto, viso), mA mano avanti e mD mano dietro (pugno, socchiusa, aperta), gA gamba avanti e gD gamba dietro '
  + '(terra, ginocchio, calcio), busto (dritto, avanti, indietro), alt altezza (normale, basso, alto); note: le parole di Denis. '
  + 'Avanti = il lato sinistro, quello davanti. Riproduci: 24 fotogrammi da una posa alla successiva.';
function pzDoc() {
  return {v: 2, name: PZ.name, note: PZ.note, frames: PZ.T, updated: Date.now(), legenda: PZ_LEGENDA, poses: pzClone(PZ.poses)};
}
function pzLoad(id, doc) {
  if (!doc || doc.v !== 2 || !Array.isArray(doc.poses) || !doc.poses.length) return false;
  PZ.id = id || null; PZ.name = typeof doc.name === 'string' && doc.name.trim() ? doc.name.slice(0, 60) : 'Animazione';
  PZ.note = typeof doc.note === 'string' ? doc.note.slice(0, 2000) : '';
  PZ.poses = doc.poses.slice(0, PZ.max).map(pzFill); PZ.cur = 0; PZ.play = null; PZ.undo = [];
  PZ.ver++; PZ.ui.dirty = true;
  return true;
}
function pzLocal(doc) { try { localStorage.setItem(PZ_KEY, JSON.stringify({id: PZ.id, doc})); } catch (_) { /* (private window: the database alone) */ } }
function pzChanged() {
  PZ.ver++; PZ.edited = true; PZ.ui.dirty = true;
  clearTimeout(PZ.timer); PZ.timer = setTimeout(pzSave, 700);   // (a burst of taps: one write once they pause)
}
async function pzSave() {
  clearTimeout(PZ.timer);
  const doc = pzDoc();
  pzLocal(doc);
  if (!PZ.col) { if (PZ.loaded) pzStatus('Salvato su questo dispositivo'); return; }
  if (PZ.busy) { PZ.dirty = true; return; }   // (one write at a time: the next one after it)
  PZ.busy = true; pzStatus('Salvataggio…');
  try {
    if (!PZ.id) PZ.id = PZ.col.doc().id;
    await PZ.col.doc(PZ.id).set(doc);
    PZ.retry = 0; pzStatus('Salvato');
  } catch (e) {
    const code = e && e.code;
    if ((code === 'unavailable' || code === 'resource_exhausted') && PZ.retry < 2) { PZ.retry++; PZ.dirty = true; await new Promise(r => setTimeout(r, 1500 + 1500 * Math.random())); }
    else { PZ.retry = 0; pzStatus(pzErr(code)); if (code !== 'unavailable' && code !== 'resource_exhausted' && code !== 'quota_exceeded') PZ.col = null; }
  }
  PZ.busy = false;
  if (PZ.dirty) { PZ.dirty = false; pzSave(); }
}
function pzErr(code) {
  if (code === 'quota_exceeded') return 'Spazio pieno: non salvato';
  if (code === 'invalid_argument') return 'Qui non puoi salvare: resta su questo dispositivo';
  if (code === 'revoked' || code === 'not_granted' || code === 'capability_disabled' || code === 'capability_removed') return 'Salvataggio non disponibile: resta su questo dispositivo';
  return 'Connessione assente: salvo alla prossima modifica';
}
async function pzStore() {
  try { const s = JSON.parse(localStorage.getItem(PZ_KEY) || 'null'); if (s && s.doc && pzLoad(s.id, s.doc)) PZ.localDoc = s; } catch (_) { /* (none, or not readable) */ }
  pzStatus('Caricamento…');
  let db = null;
  try { const c = window.claude; db = c && typeof c.use === 'function' ? await c.use('db') : null; } catch (_) { db = null; }
  if (!db) { PZ.loaded = true; pzStatus('Salvo su questo dispositivo'); return; }
  PZ.db = db; PZ.col = db.collection('animazioni');
  const wait = setTimeout(() => { if (!PZ.loaded) pzStatus('Il salvataggio non risponde ancora'); }, 10000);
  PZ.col.orderBy('updated', 'desc').limit(50).onSnapshot(snap => {
    PZ.list = snap.docs.map(d => ({id: d.id, doc: d.data() || {}})).filter(a => a.doc.v === 2)
      .map(a => ({id: a.id, name: typeof a.doc.name === 'string' ? a.doc.name.slice(0, 60) : 'Animazione', updated: +a.doc.updated || 0, doc: a.doc}));
    PZ.ui.list = true;
    if (snap.metadata.fromCache || PZ.loaded) return;
    clearTimeout(wait); PZ.loaded = true;
    // the first answer: the animation this device had open (unless its own copy is newer), else the newest one
    const L = PZ.localDoc, mine = L && PZ.list.find(a => a.id === L.id), open = mine || PZ.list[0];
    if (PZ.edited || (L && (!mine || (+L.doc.updated || 0) > mine.updated))) pzSave();
    else if (open) { pzLoad(open.id, open.doc); pzStatus('Aperta «' + open.name + '»'); }
    else pzStatus('Pronto: le pose si salvano da sole');
  }, err => { clearTimeout(wait); PZ.loaded = true; pzStatus(pzErr(err && err.code)); if (err && err.code !== 'unavailable') PZ.col = null; });
}
function pzNewAnim() {
  pzStop();
  PZ.id = null; PZ.name = 'Animazione ' + (PZ.list.length + 1); PZ.note = ''; PZ.poses = [pzNew0()]; PZ.cur = 0; PZ.undo = [];
  pzChanged(); pzSave();
}
function pzCopy() {
  const txt = JSON.stringify(pzDoc());
  const show = () => { const t = document.getElementById('pzData'); t.hidden = false; t.value = txt; t.focus(); t.select(); pzStatus('Copia il testo qui sotto e incollalo a Claude'); };
  try { navigator.clipboard.writeText(txt).then(() => pzStatus('Dati copiati: incollali a Claude'), show); } catch (_) { show(); }
}

// --- The page: Ren on the left, the choices on the right (below him when the screen stands up) ---
function pzStatus(t) { const s = document.getElementById('pzSt'); if (s && s.textContent !== t) s.textContent = t; }
function pzBtn(label, f, id) {
  const b = document.createElement('button'); if (id) b.id = id;
  b.innerHTML = '<span></span>'; b.firstChild.textContent = label; b.addEventListener('click', f);
  return b;
}
function pzPress(b, on) { const v = on ? 'true' : 'false'; if (b.getAttribute('aria-pressed') !== v) b.setAttribute('aria-pressed', v); }
function pzRowsUi() {
  const P = PZ.poses[PZ.cur], at = PZ.play && PZ.play.at, show = at ? PZ.poses[at.b] : P;
  for (const r of PZ_ROWS) {
    const row = PZ.ui.rows[r.key];
    row.classList.toggle('kb', PZ.kb && PZ_ROWS[PZ.row] === r);
    if (!show) continue;
    if (r.hands) for (const [k, lab] of r.hands) { const b = PZ.ui.hands[k], h = PZ_HANDS.find(x => x[0] === show[k]), t = lab + ': ' + h[1]; if (b.firstChild.textContent !== t) b.firstChild.textContent = t; }
    else for (const b of row.querySelectorAll('button')) pzPress(b, show[r.key] === b.dataset.v);
  }
}
function pzStrip() {
  const box = PZ.ui.chips, n = PZ.poses.length, at = PZ.play && PZ.play.at;
  while (box.children.length > n) box.lastChild.remove();
  while (box.children.length < n) { const i = box.children.length, b = pzBtn(String(i + 1), () => pzGo(i)); b.className = 'chip'; b.setAttribute('aria-label', 'Posa ' + (i + 1)); box.appendChild(b); }
  [...box.children].forEach((b, i) => pzPress(b, at ? i === at.b : i === PZ.cur));
  if (PZ.pop !== undefined && box.children[PZ.pop]) { const b = box.children[PZ.pop]; b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop'); b.scrollIntoView({block: 'nearest', inline: 'nearest'}); PZ.pop = undefined; }
  PZ.ui.play.firstChild.textContent = PZ.play ? 'Ferma' : 'Riproduci'; pzPress(PZ.ui.play, !!PZ.play);
  PZ.ui.del.disabled = n < 2; PZ.ui.add.disabled = n >= PZ.max;
  const side = Math.abs(VW.yaw - F3_YAW) < .02; PZ.ui.view.firstChild.textContent = side ? 'Vista: lato' : 'Vista: 3/4';
}
function pzTitle() {
  const sm = document.querySelector('#name small'), at = PZ.play && PZ.play.at;
  const t = at ? (at.back ? 'Riproduzione · torna alla posa 1' : at.a === at.b ? 'Riproduzione · posa ' + (at.a + 1) : 'Riproduzione · posa ' + (at.a + 1) + ' → ' + (at.b + 1))
    : 'Posa ' + (PZ.cur + 1) + ' di ' + PZ.poses.length + (PZ.name ? ' · ' + PZ.name : '');
  if (sm && sm.textContent !== t) sm.textContent = t;
}
function pzNotes(open) {
  const N = document.getElementById('pzN');
  if (open === undefined) open = N.hidden;
  N.hidden = !open; pzPress(document.getElementById('pzNb'), open);
  if (open) pzNotesUi(); else document.getElementById('pzData').hidden = true;
}
function pzNotesUi() {
  const N = document.getElementById('pzN');
  if (N.hidden) return;
  const a = document.activeElement, set = (id, v) => { const el = document.getElementById(id); if (el !== a && el.value !== v) el.value = v; };
  set('pzName', PZ.name); set('pzNote', PZ.note); set('pzPnote', (PZ.poses[PZ.cur] || {}).note || '');
  document.getElementById('pzPn').textContent = String(PZ.cur + 1);
}
function pzListUi() {
  const sel = document.getElementById('pzList');
  if (!sel || sel === document.activeElement) return;
  sel.textContent = '';
  const add = (v, t) => { const o = document.createElement('option'); o.value = v; o.textContent = t; sel.appendChild(o); };
  add('', PZ.list.length ? 'Apri un\'animazione salvata…' : 'Nessun\'animazione salvata');
  for (const a of PZ.list) add(a.id, a.name + (a.id === PZ.id ? ' (aperta)' : ''));
  sel.disabled = !PZ.list.length;
}
// the camera: Ren in the middle of the space the panel leaves him (left of it, or above it), below the title
function pzResize() {
  const w = innerWidth, h = innerHeight, c = VW.camera, P = document.getElementById('pzP').getBoundingClientRect(), top = document.getElementById('name').getBoundingClientRect().bottom + 4;
  const right = P.left > w * .25, x1 = right ? P.left : w, y1 = right ? h : P.top, y0 = Math.min(top, y1 - 120);
  const fw = Math.max(80, x1), fh = Math.max(80, y1 - y0), cx = x1 / 2, cy = (y0 + y1) / 2;
  const FW = 2 * Math.max(cx, w - cx), FH = 2 * Math.max(cy, h - cy);
  c.fov = 30; c.aspect = FW / FH; c.setViewOffset(FW, FH, FW / 2 - cx, FH / 2 - cy, w, h); c.updateProjectionMatrix();
  const t = Math.tan(c.fov * Math.PI / 360);
  VW.fit = Math.max(2 * FH / (fh * 2 * t), 1.6 * FW / (fw * 2 * t * c.aspect)) / .94;   // 2 m tall (Ren is 1.8), 1.6 m wide fit
}
function pzUi() {
  const css = document.createElement('style');
  css.textContent = `
#moves,#bottom>.row,#now{display:none!important}
#pzP{position:fixed;z-index:3;top:0;right:0;bottom:0;width:min(500px,57vw);box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:6px;overflow-y:auto;
  padding:calc(8px + env(safe-area-inset-top,0px)) max(14px,env(safe-area-inset-right,0px)) calc(8px + env(safe-area-inset-bottom,0px)) 14px;
  background:rgba(20,18,28,.82);border-left:1px solid var(--line);scrollbar-width:thin}
#bottom{right:min(500px,57vw)}
.pzR{display:flex;align-items:center;gap:5px;flex-wrap:wrap;border-radius:4px;padding:1px 2px}
.pzR.kb{outline:2px solid var(--cyan);outline-offset:2px}
.pzL{flex:0 0 96px;color:var(--dim);font-size:14px;line-height:1.1}
#pzP button{font-size:15px;padding:5px 10px 4px}
#pzP .hand{min-width:150px;text-align:left}
#pzTopRow{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
#pzChips{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;padding:3px 2px;flex:1 1 60px;min-width:0;touch-action:pan-x}#pzChips::-webkit-scrollbar{display:none}
#pzChips .chip{flex:0 0 auto;min-width:36px}
#pzTools{display:flex;gap:5px;flex-wrap:wrap;margin-top:2px}
button:disabled{opacity:.4;cursor:default}
#pzInfo{display:block;font-family:var(--body);font-style:italic;font-size:13px;letter-spacing:.04em;color:var(--dim);text-shadow:0 1px 3px #000;transform:none;margin-top:2px}
#pzInfo #fps{display:inline;font-size:inherit;color:inherit}#pzInfo #fps:not(:empty)::before{content:" · "}
#pzN{position:fixed;z-index:5;left:50%;bottom:calc(10px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);width:min(560px,calc(100vw - 32px));max-height:calc(100vh - 20px);overflow:auto;box-sizing:border-box;
  background:rgba(20,18,28,.97);border:1px solid var(--line);padding:12px;display:flex;flex-direction:column;gap:8px;box-shadow:0 8px 30px rgba(0,0,0,.6)}
#pzN[hidden]{display:none}
#pzN label{display:flex;flex-direction:column;gap:4px;color:var(--dim);font-size:14px}
#pzN input,#pzN textarea,#pzN select{font:inherit;font-style:normal;font-weight:600;font-size:16px;color:var(--ink);background:#0d0c13;border:1px solid var(--line);padding:6px 8px;user-select:text;-webkit-user-select:text;min-width:0}
#pzN textarea{resize:vertical}
#pzN .row{align-items:center}
@keyframes pzPop{0%{transform:skewX(-10deg) scale(.55)}60%{transform:skewX(-10deg) scale(1.18)}100%{transform:skewX(-10deg) scale(1)}}
.pop{animation:pzPop .28s ease-out}
@media (max-height:430px){#name{font-size:34px}#name small{font-size:14px}#pzP{gap:4px}#pzP button{font-size:14px;padding:4px 9px 3px}.pzL{font-size:13px;flex-basis:88px}#pzP .hand{min-width:136px}}
@media (max-height:370px){#pzP{gap:3px}#pzP button{padding:3px 8px 2px}}
@media (pointer:coarse){#hint{display:none}}
@media (orientation:portrait){#pzP{top:auto;left:0;width:auto;max-height:56vh;justify-content:flex-start;border-left:0;border-top:1px solid var(--line)}#bottom{display:none}}
@media (prefers-reduced-motion:reduce){.pop{animation:none}}`;
  document.head.appendChild(css);
  const P = document.createElement('div'); P.id = 'pzP';
  // the poses' row
  const top = document.createElement('div'); top.id = 'pzTopRow';
  const chips = document.createElement('div'); chips.id = 'pzChips'; chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', 'Pose');
  PZ.ui.chips = chips; PZ.ui.add = pzBtn('+ Posa', pzAdd, 'pzAdd'); PZ.ui.play = pzBtn('Riproduci', pzPlay, 'pzPlay');
  top.append(chips, PZ.ui.add, PZ.ui.play); P.appendChild(top);
  // the choices
  PZ.ui.rows = {}; PZ.ui.hands = {};
  for (const r of PZ_ROWS) {
    const row = document.createElement('div'); row.className = 'pzR'; row.setAttribute('role', 'group'); row.setAttribute('aria-label', r.label);
    const lab = document.createElement('span'); lab.className = 'pzL'; lab.textContent = r.label; row.appendChild(lab);
    if (r.hands) for (const [k, l] of r.hands) { const b = pzBtn(l, () => pzHand(k), 'pz_' + k); b.className = 'hand'; row.appendChild(b); PZ.ui.hands[k] = b; }
    else for (const [v, l] of r.vals) { const b = pzBtn(l, () => pzChoose(r.key, v)); b.dataset.v = v; row.appendChild(b); }
    row.addEventListener('pointerdown', () => { PZ.kb = false; PZ.row = PZ_ROWS.indexOf(r); PZ.ui.dirty = true; });
    PZ.ui.rows[r.key] = row; P.appendChild(row);
  }
  // the tools
  const tools = document.createElement('div'); tools.id = 'pzTools';
  PZ.ui.del = pzBtn('Elimina posa', pzDel, 'pzDel'); PZ.ui.view = pzBtn('Vista: lato', pzView, 'pzView');
  tools.append(pzBtn('Annulla', pzUndo, 'pzUndo'), pzBtn('Guardia', pzGuard, 'pzGuard'), PZ.ui.del, pzBtn('Note', () => pzNotes(), 'pzNb'), PZ.ui.view);
  P.appendChild(tools);
  document.body.appendChild(P);
  // the saving's state and the frames per second: a line under the title
  const info = document.createElement('small'); info.id = 'pzInfo';
  const st = document.createElement('span'); st.id = 'pzSt'; st.setAttribute('role', 'status'); info.appendChild(st);
  const fps = document.getElementById('fps'); if (fps) info.appendChild(fps);
  document.getElementById('name').appendChild(info);
  const hint = document.getElementById('hint');
  if (hint) hint.innerHTML = 'Tocca le scelte a destra; trascina Ren per girarlo, doppio tocco per tornare di lato.'
    + '<span class=kb> Tastiera: frecce su e giù la riga, sinistra e destra la scelta, N nuova posa, [ ] cambia posa, P riproduci, G guardia, Ctrl+Z annulla.'
    + ' Controller: croce per righe e scelte, A nuova posa, B annulla, X guardia, Y riproduci, dorsali cambia posa.</span>';
  // the notes (for Claude): the animation's name and words, each pose's own, the saved animations, the data
  const N = document.createElement('div'); N.id = 'pzN'; N.hidden = true; N.setAttribute('role', 'dialog'); N.setAttribute('aria-label', 'Note per Claude');
  N.innerHTML = '<label>Nome dell\'animazione<input id="pzName" maxlength="60" autocomplete="off"></label>'
    + '<label>Note per Claude: i tempi e cosa deve succedere<textarea id="pzNote" rows="3" maxlength="2000" placeholder="Es. dalla 2 alla 3 velocissimo, la 4 tenuta un attimo"></textarea></label>'
    + '<label>Nota della posa <span id="pzPn">1</span><input id="pzPnote" maxlength="300" autocomplete="off" placeholder="Es. qui colpisce"></label>'
    + '<textarea id="pzData" rows="3" readonly hidden aria-label="I dati delle pose"></textarea>'
    + '<div class="row"><select id="pzList" aria-label="Animazioni salvate"></select></div>'
    + '<div class="row"></div>';
  N.lastChild.append(pzBtn('Nuova animazione', pzNewAnim, 'pzNew'), pzBtn('Copia i dati', pzCopy, 'pzCopy'));
  const bg = document.getElementById('kitBg'); if (bg) N.lastChild.appendChild(bg);   // (the kit's floor or arena)
  N.lastChild.appendChild(pzBtn('Chiudi', () => pzNotes(false), 'pzClose'));
  document.body.appendChild(N);
  const typed = (id, f) => document.getElementById(id).addEventListener('input', e => { f(e.target.value); PZ.edited = true; PZ.ui.dirty = true; clearTimeout(PZ.timer); PZ.timer = setTimeout(pzSave, 900); });
  typed('pzName', v => { PZ.name = v.slice(0, 60); });
  typed('pzNote', v => { PZ.note = v.slice(0, 2000); });
  typed('pzPnote', v => { if (PZ.poses[PZ.cur]) PZ.poses[PZ.cur].note = v.slice(0, 300); });
  document.getElementById('pzList').addEventListener('change', e => {
    const a = PZ.list.find(x => x.id === e.target.value);
    e.target.blur();
    if (a && a.id !== PZ.id) { pzStop(); if (pzLoad(a.id, a.doc)) { pzLocal(pzDoc()); pzStatus('Aperta «' + a.name + '»'); pzNotesUi(); } }
    PZ.ui.list = true;
  });
  addEventListener('resize', pzResize); pzResize();
  PZ.ui.dirty = true; PZ.ui.list = true;
}
// keys (taken before the viewer's own: its plays and speeds are not this page's)
function pzKeys() {
  addEventListener('keydown', e => {
    const t = e.target, tag = t && t.tagName, typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    e.stopImmediatePropagation();
    if (typing) { if (e.key === 'Escape') { t.blur(); pzNotes(false); } return; }
    if (e.key === 'Escape') { pzNotes(false); pzStop(); return; }
    const k = e.key, K = k.length === 1 ? k.toLowerCase() : k, onBtn = tag === 'BUTTON';
    if ((e.ctrlKey || e.metaKey) && K === 'z') { e.preventDefault(); pzUndo(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const act = {
      ArrowUp: () => pzRowGo(-1), ArrowDown: () => pzRowGo(1), ArrowLeft: () => { PZ.kb = true; pzStepRow(-1); }, ArrowRight: () => { PZ.kb = true; pzStepRow(1); },
      '[': () => pzGo(PZ.cur - 1), ']': () => pzGo(PZ.cur + 1), n: () => pzAdd(), p: () => pzPlay(), g: () => pzGuard(), z: () => pzUndo(), v: () => pzView(), Delete: () => pzDel(),
    }[K];
    if (act && !(onBtn && (K === 'Enter' || K === ' '))) { e.preventDefault(); if (!e.repeat || /^Arrow/.test(K)) act(); }
  }, true);
}
// the controller: the d-pad (or the left stick) rows and choices, A a new pose, B undo, X the guard, Y plays, the
// shoulders the pose
function pzPad() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [], now = performance.now();
  for (const g of pads) {
    if (!g) continue;
    const b = i => !!(g.buttons[i] && g.buttons[i].pressed), was = PZ.pad, hit = i => b(i) && !was[i];
    const ax = (i, s) => (g.axes[i] || 0) * s > .6;
    // the d-pad or the stick: once on the press, then again every 250 ms while held
    const dir = {up: b(12) || ax(1, -1), down: b(13) || ax(1, 1), left: b(14) || ax(0, -1), right: b(15) || ax(0, 1)};
    for (const [d, on] of Object.entries(dir)) {
      const r = PZ.padRep;
      if (!on) { r[d] = 0; continue; }
      if (r[d] && now < r[d]) continue;
      r[d] = now + (r[d] ? 250 : 420);
      PZ.kb = true;
      if (d === 'up') pzRowGo(-1); else if (d === 'down') pzRowGo(1); else pzStepRow(d === 'left' ? -1 : 1);
    }
    if (hit(0)) pzAdd(); if (hit(1)) pzUndo(); if (hit(2)) pzGuard(); if (hit(3)) pzPlay();
    if (hit(4)) pzGo(PZ.cur - 1); if (hit(5)) pzGo(PZ.cur + 1);
    for (let i = 0; i < 17; i++) was[i] = b(i);
    break;
  }
}
RN.hooks.boot.push(VW => {
  VW_PLAYS[0][1][0][1] = 1e9;   // (the kit's boot sets its guard's length on the first play: this page's one play lasts)
  CFG.looks.ren.clips = Object.assign({}, CFG.looks.ren.clips, {posa: {c: 'a191', at: 0}});   // the kit's held guard clip under it
  VW.PZ = PZ; VW.pz = {target: pzTarget, rows: PZ_ROWS, hands: PZ_HANDS, guard: PZ_GUARD};   // (tests)
  PZ.poses = [pzNew0()];
  pzUi(); pzKeys(); pzStore();
});
// each drawn frame: the controller, the camera on the body, the panel when something changed
RN.hooks.draw.push((VW, dt, cam) => {
  if (RN.pad !== pzPad) RN.pad = pzPad;   // (the scaffold sets its own after the boot hooks)
  const j = PZ.D ? PZ.D.b.jump : 0;   // (a jump: the camera goes up with half of it)
  cam.position.set(VW.aimX, .95 + .5 * j + .1, cam.position.z); cam.lookAt(VW.aimX, .95 + .5 * j, 0); cam.updateMatrixWorld();
  if (PZ.play) { const a = PZ.play.at, key = a.a + ',' + a.b + ',' + a.back; if (key !== PZ.ui.at) { PZ.ui.at = key; PZ.ui.dirty = true; } }
  const side = Math.abs(VW.yaw - F3_YAW) < .02; if (side !== PZ.ui.side) { PZ.ui.side = side; PZ.ui.dirty = true; }   // (the view's button names it)
  if (PZ.ui.dirty) { PZ.ui.dirty = false; pzStrip(); pzRowsUi(); pzTitle(); pzNotesUi(); }
  if (PZ.ui.list) { PZ.ui.list = false; pzListUi(); }
});
// one play: the pose being edited, for as long as the page is open
VW_PLAYS.length = 0;
VW_PLAYS.push(['Posa', [['posa', 1e9]]]);
VW_NAMES.posa = 'Posa';
