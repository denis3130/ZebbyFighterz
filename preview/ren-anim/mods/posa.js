// --- posa.js: "Pose di Ren", an editor of key poses (13/11/2026). ---
// Denis (13/11): "mi puoi fare un'anteprima del personaggio dove posso muoverlo come voglio toccando per esempio le
// gambe o le braccia per fare nuove animazioni? così capisci meglio cosa intendo". His choice (A): key poses only, as
// his sheets have them (posa 1, 2, 3...), and a "Riproduci" that shows them in a row at one fixed speed; the timing he
// tells in words (the notes). Built on the kit (kit.js, loaded before this): the same Ren, base guard and solver. One
// act, 'posa', whose style, feet, arms, hands and head are the pose being edited or, while it plays, the mix of two.
// Touch and mouse: a part's handle dragged on the picture moves in the plane facing the camera (turn the view to move
// it in depth); a drag elsewhere turns the view, a pinch or the wheel zooms, as in the viewer. Keyboard and controller:
// the same, part by part. The poses are saved in the page's database (collection "animazioni", one document per
// animation: Claude reads them there) and on this device (localStorage) when the database is not there.
//
// A pose, on top of the kit's base guard (RK.g); metres and degrees (pzDoc writes this legend into each document):
//   b      {yaw, chest, leanL, leanS, lx, lz, dip}: the hips' turn, the chest's own twist, the lean toward the
//          opponent and sideways (+: toward his right), the pelvis along the fight line, across it (+: his left), down
//   h      {yaw, nod}: the head's turn and nod (< 0: chin up)
//   L, R   {p, e, k, roll, wrist}: the wrist from its shoulder and the elbow's way from it, both in the chest's frame
//          ([across: his left, up, forward]); how closed the hand is (0 open, fingers together .. 1 fist); the palm's
//          roll about the forearm (0: toward the elbow's side, "giù" when the elbow is down; 90 "di lato", inward;
//          180 "su") and the wrist's bend (> 0 back, as in a palm strike; < 0 toward the palm)
//   fL, fR {x, z, up, heel, yaw, toe}: the foot moved along the fight line, across it and up; its heel lifted, its
//          turn on its tip, its toes' point once it is in the air
//   note   Denis's words for this pose
// Left is the lead side (the front hand and foot), right the rear.

const PZ = {
  T: 24, hold: 40, back: 24, rest: 14,   // playing: frames from a pose to the next (0.4 s), held on the last, back to the first, held there
  max: 24, turn: 10,                     // poses in one animation; degrees a turn button turns
  poses: [], cur: 0, sel: 'hL', play: null, undo: [], guard: null, fk: null, ver: 0, now: {af: NaN, v: -1, P: null},
  id: null, name: 'Nuova animazione', note: '', pending: null,
  db: null, col: null, list: [], loaded: false, edited: false, busy: false, dirty: false, retry: 0, timer: 0,
  drag: null, el: {}, scr: {}, showH: true, pad: {}, padT: 0, padMove: false, lastPush: 0, ui: {}, sub: '',
  ySign: 1, nSign: 1,                    // the head's turn and nod against the gaze's (from the rig: tests/posa.js checks them)
};
const PZ_FOOT = () => ({x: 0, z: 0, up: 0, heel: 0, yaw: 0, toe: 15});
PZ.base = {b: {yaw: 0, chest: 0, leanL: 0, leanS: 0, lx: 0, lz: 0, dip: 0}, h: {yaw: 0, nod: 0}, L: null, R: null, fL: PZ_FOOT(), fR: PZ_FOOT(), note: ''};
const PZ_PARTS = [
  {id: 'head', name: 'Testa', c: '#f4f1fb', kind: 'head'},
  {id: 'chest', name: 'Busto', c: '#f4f1fb', kind: 'chest'},
  {id: 'hips', name: 'Bacino', c: '#f4f1fb', kind: 'hips'},
  {id: 'hL', name: 'Mano sinistra (davanti)', c: '#35d8ff', kind: 'hand'},
  {id: 'eL', name: 'Gomito sinistro', c: '#35d8ff', kind: 'elbow'},
  {id: 'hR', name: 'Mano destra (dietro)', c: '#ff7a1a', kind: 'hand'},
  {id: 'eR', name: 'Gomito destro', c: '#ff7a1a', kind: 'elbow'},
  {id: 'fL', name: 'Piede sinistro (davanti)', c: '#35d8ff', kind: 'foot'},
  {id: 'fR', name: 'Piede destro (dietro)', c: '#ff7a1a', kind: 'foot'},
  {id: 'all', name: 'Tutto il corpo', c: '#f4f1fb', kind: 'all'},
];
// What each kind of part offers besides its drag: groups of values (the pose's field, [value, label]) or a turn.
const PZ_OPTS = {
  hand: {hint: '', groups: [
    {label: 'Mano', key: 'k', vals: [[1, 'Pugno'], [.55, 'Socchiusa'], [0, 'Aperta']]},
    {label: 'Palmo', key: 'roll', vals: [[0, 'Giù'], [90, 'Di lato'], [180, 'Su']]},
    {label: 'Polso', key: 'wrist', vals: [[-50, 'Avanti'], [0, 'Dritto'], [70, 'Indietro']]}]},
  foot: {hint: '', groups: [
    {label: 'Tallone', key: 'heel', vals: [[0, 'Giù'], [15, 'Su'], [30, 'Punta']]},
    {label: 'In aria', key: 'toe', vals: [[45, 'Punta tesa'], [15, 'Normale'], [-5, 'Martello']]},
    {label: 'Gira', turn: true}]},
  elbow: {hint: 'Trascina il gomito: sceglie da che parte si piega il braccio.', groups: []},
  chest: {hint: 'Trascina per piegarlo.', groups: [{label: 'Gira il busto', turn: true}]},
  hips: {hint: 'Trascina per spostarlo o abbassarlo.', groups: [{label: 'Gira il bacino', turn: true}]},
  head: {hint: 'Trascina il punto: è dove guarda.', groups: [{label: 'Gira', turn: true}]},
  all: {hint: 'Trascina il punto a terra: sposta tutto Ren.', groups: []},
};
const PZ_KEY = 'pose-ren-v1';   // localStorage: {id, doc} of the animation open on this device
const pzV = () => new THREE.Vector3();
const pzClone = o => JSON.parse(JSON.stringify(o));
const pzC = (x, a, b) => Math.max(a, Math.min(b, x));
const pzW = a => Math.atan2(Math.sin(a), Math.cos(a));   // an angle back into -pi..pi
const pzR = a => a.map(x => Math.round(x * 1000) / 1000);
const pzPart = id => PZ_PARTS.find(p => p.id === id);

// --- Poses: mixing, filling (a pose read back from the database is checked field by field), the one drawn now ---
function pzMix(a, b, u) {
  if (typeof a === 'number') return a + (b - a) * u;
  if (Array.isArray(a)) return a.map((x, i) => x + (b[i] - x) * u);
  const o = {};
  for (const k in a) o[k] = typeof a[k] === 'string' ? a[k] : pzMix(a[k], b[k], u);
  if (o.e) { const l = Math.hypot(o.e[0], o.e[1], o.e[2]) || 1; o.e = o.e.map(x => x / l); }   // (the elbow's way stays a way)
  return o;
}
function pzFill(p) {
  const o = pzClone(PZ.guard); o.note = '';
  if (!p || typeof p !== 'object') return o;
  for (const k of ['b', 'h', 'L', 'R', 'fL', 'fR']) {
    const src = p[k];
    if (!src || typeof src !== 'object') continue;
    for (const j in o[k]) {
      const v = src[j];
      if (typeof o[k][j] === 'number' && typeof v === 'number' && isFinite(v)) o[k][j] = v;
      else if (Array.isArray(o[k][j]) && Array.isArray(v) && v.length === 3 && v.every(x => typeof x === 'number' && isFinite(x))) o[k][j] = v.slice();
    }
  }
  if (typeof p.note === 'string') o.note = p.note.slice(0, 300);
  return o;
}
// The pose of fighter state F: the edited one, or while it plays the mix of two (cached per frame and pose version).
function pzNow(F) {
  const c = PZ.now;
  if (c.af === F.af && c.v === PZ.ver) return c.P;
  const n = PZ.poses.length;
  c.P = !PZ.guard || !n ? PZ.base : PZ.play && n > 1 ? pzPlayAt(F.af - PZ.play.f0) : PZ.poses[Math.min(PZ.cur, n - 1)];
  c.af = F.af; c.v = PZ.ver;
  return c.P;
}
// Playing: pose 1 to 2 to ... n, PZ.T frames each (from rest to rest: each key pose is reached and seen), held on the
// last, then back to the first and held there; again.
function pzPlayAt(t) {
  const P = PZ.poses, n = P.length, run = (n - 1) * PZ.T, len = run + PZ.hold + PZ.back + PZ.rest, at = PZ.play.at;
  t = ((t % len) + len) % len;
  if (t < run) { const i = Math.min(n - 2, Math.floor(t / PZ.T)), u = rnSm((t - i * PZ.T) / PZ.T); at.a = i; at.b = i + 1; at.back = false; return pzMix(P[i], P[i + 1], u); }
  t -= run;
  if (t < PZ.hold) { at.a = at.b = n - 1; at.back = false; return P[n - 1]; }
  t -= PZ.hold;
  if (t < PZ.back) { at.a = n - 1; at.b = 0; at.back = true; return pzMix(P[n - 1], P[0], rnSm(t / PZ.back)); }
  at.a = at.b = 0; at.back = true;
  return P[0];
}

// --- The act: style, feet, arms, head, kicking legs, hands ---
RB.pin.posa = 1;
RB.styleFor.posa = (y, F) => {
  const P = pzNow(F), b = P.b;
  y.yaw = b.yaw; y.chest = b.chest; y.leanL = b.leanL; y.leanS = b.leanS; y.lx = b.lx; y.lz = b.lz; y.dip = .004 + b.dip; y.head = P.h.nod;
  rkBase(y);
};
// a foot in the air (by its height) leaves its heel to the leg (rkKickLeg below sets it against the shin)
const pzAir = f => rnSm((f.up - .03) / .12);
RB.feetFor.posa = (s, c, st, L, F) => {
  const f = pzNow(F)['f' + s];
  rkFoot(s, c, st, L, f.heel * (1 - pzAir(f)), f.yaw, f.x, f.up, 0);
  if (f.z) c.G.addScaledVector(RB_SIDE, f.z);
};
// Arm s of pose p to hand A (a pose's L or R). First where the arm goes (the hand's own way does not change it): the
// forearm's frame from it, x along the forearm, y toward the elbow's side, z its hinge (a frame that exists for any
// arm: the elbow is never on the forearm's line). Then the palm rolled about the forearm and bent at the wrist in that
// frame, and the arm solved again from where it was, with that hand.
function pzArm(md, p, s, A) {
  const T = THREE, ix = md.index, n = s === 'L' ? 'Left' : 'Right', iA = ix[n + 'Arm'], iF = ix[n + 'ForeArm'], iH = ix[n + 'Hand'];
  let W = rbFK(md, p, RB.W);
  const qC = W.q[ix.Spine01].clone(), sh = W.p[iA].clone();
  const tgt = new T.Vector3().fromArray(A.p).applyQuaternion(qC).add(sh), eh = new T.Vector3().fromArray(A.e).applyQuaternion(qC).normalize();
  const keep = [iA, iF, iH].map(i => [i, Array.from(p.q.slice(i * 4, i * 4 + 4))]);
  rsArm(md, p, W, s, tgt, eh, eh, eh, 1, 1);
  W = rbFK(md, p, RB.W);
  const Ap = W.p[iA], E = W.p[iF], H = W.p[iH], dir = H.clone().sub(Ap).normalize(), Pe = E.clone().sub(Ap);
  Pe.addScaledVector(dir, -Pe.dot(dir));
  const ax = H.clone().sub(E).normalize(), y = Pe.addScaledVector(ax, -Pe.dot(ax)).normalize(), z = new T.Vector3().crossVectors(ax, y);
  const r = A.roll * RB_R, w = A.wrist * RB_R, sg = s === 'L' ? -1 : 1;
  const n0 = y.clone().multiplyScalar(Math.cos(r)).addScaledVector(z, sg * Math.sin(r));
  const nn = n0.clone().multiplyScalar(Math.cos(w)).addScaledVector(ax, Math.sin(w)), ff = ax.clone().multiplyScalar(Math.cos(w)).addScaledVector(n0, -Math.sin(w));
  for (const [i, q] of keep) for (let k = 0; k < 4; k++) p.q[i * 4 + k] = q[k];
  rsArm(md, p, rbFK(md, p, RB.W), s, tgt, eh, ff, nn, 1, 0);
  return {ax, y, z, sg};
}
// The base guard in these numbers (the kit's guard: the lead fist straight out, the rear hand half closed on the
// stomach), from the first pose drawn; the first pose of a new animation.
function pzMakeGuard(md, p) {
  const T = THREE, W = rbFK(md, p, RB.W), ix = md.index, C1 = W.p[ix.Spine01].clone(), qi = W.q[ix.Spine01].clone().invert();
  const l = a => rsVec(a, new T.Vector3()), c = a => rsChest(md, W, a, new T.Vector3());
  const sh = {L: W.p[ix.LeftArm].clone(), R: W.p[ix.RightArm].clone()};
  const armL = sh.L.distanceTo(W.p[ix.LeftForeArm]) + W.p[ix.LeftForeArm].distanceTo(W.p[ix.LeftHand]);
  const G = {L: {p: l(RS.lead.dir).normalize().multiplyScalar(RS.lead.reach * armL).add(sh.L), n: l(RS.lead.palm).normalize(), e: l(RS.lead.elbow).normalize(), k: RK_HAND.fist},
    R: {p: c(RS.rear.pos).add(C1), n: c(RS.rear.palm).normalize(), e: c(RS.rear.elbow).normalize(), k: RK_HAND.rear}};
  const g = pzClone(PZ.base);
  for (const s of ['L', 'R']) {
    const A = G[s];
    g[s] = {p: pzR(A.p.clone().sub(sh[s]).applyQuaternion(qi).toArray()), e: pzR(A.e.clone().applyQuaternion(qi).toArray()), k: A.k, roll: 0, wrist: 0};
    const fr = pzArm(md, p, s, g[s]), nv = A.n.clone().addScaledVector(fr.ax, -A.n.dot(fr.ax));   // the guard's palm, about the forearm it takes
    g[s].roll = Math.round(Math.atan2(nv.dot(fr.z) * fr.sg, nv.dot(fr.y)) / RB_R);
    g[s].wrist = Math.round(Math.asin(pzC(A.n.dot(fr.ax), -1, 1)) / RB_R);
  }
  g.L.roll = 90; g.L.wrist = 0;   // (the lead fist as the buttons name it: palm in, wrist straight; it comes out at 101 and 1)
  PZ.guard = g;
  // the head's own axes (its look and its up, in its bone's frame): the rest pose faces +z
  const R = rbFK(md, mdRest(md), rbSpace(md.nb)), qh = R.q[ix.Head].clone().invert();
  PZ.hFwd = new T.Vector3(0, 0, 1).applyQuaternion(qh); PZ.hUp = new T.Vector3(0, 1, 0).applyQuaternion(qh);
  if (!PZ.poses.length) PZ.poses = [pzClone(g)];
  if (PZ.pending) { const d = PZ.pending; PZ.pending = null; pzLoad(d.id, d.doc, true); }
  PZ.ver++; PZ.ui.dirty = true;
}
RB.post.push((md, p, F) => {
  if (F.act !== 'posa' || F.air) return;
  if (!PZ.guard) pzMakeGuard(md, p);
  const P = pzNow(F), ix = md.index;
  pzArm(md, p, 'L', P.L); pzArm(md, p, 'R', P.R);
  mdBoneTurn(p, ix.Head, MD_Y, RK.g.headYaw + P.h.yaw);   // (the nod: the style's)
  for (const s of ['L', 'R']) { const f = P['f' + s], air = pzAir(f); if (air > 0) rkKickLeg(md, p, {s, pole: [1, 1, 0], point: f.toe, air}, 0); }
  // where the parts are now (model space): the handles and the drags start from here
  const W = rbFK(md, p, RB.W), V = pzV;
  const k = PZ.fk || (PZ.fk = {w: {L: V(), R: V()}, e: {L: V(), R: V()}, sh: {L: V(), R: V()}, ank: {L: V(), R: V()}, hip: {L: V(), R: V()},
    arm: {}, leg: {}, chest: V(), hips: V(), hp: V(), gaze: V(), qC: new THREE.Quaternion(), t: V()});
  for (const s of ['L', 'R']) {
    const n = s === 'L' ? 'Left' : 'Right', L = RB.leg[s];
    k.w[s].copy(W.p[ix[n + 'Hand']]); k.e[s].copy(W.p[ix[n + 'ForeArm']]); k.sh[s].copy(W.p[ix[n + 'Arm']]);
    k.arm[s] = k.sh[s].distanceTo(k.e[s]) + k.e[s].distanceTo(k.w[s]);
    k.ank[s].copy(W.p[L.ia]); k.hip[s].copy(W.p[L.iu]); k.leg[s] = L.a + L.b;
  }
  k.chest.copy(W.p[ix.Spine]); k.hips.copy(W.p[ix.Hips]); k.qC.copy(W.q[ix.Spine01]);   // (the rig's spine: Hips, Spine02, Spine01, Spine, up)
  k.hp.copy(W.p[ix.Head]).addScaledVector(k.t.copy(PZ.hUp).applyQuaternion(W.q[ix.Head]), .07);
  k.gaze.copy(k.hp).addScaledVector(k.t.copy(PZ.hFwd).applyQuaternion(W.q[ix.Head]), .3);
});
RN.hooks.applied.push((it, F) => {   // the hands: open with the fingers together (and the thumb along them), half closed, a fist
  if (!it.fingers || F.act !== 'posa' || !PZ.guard) return;
  const P = pzNow(F);
  for (let i = 0; i < it.fingers.length; i++) rkSetFinger(it, i, (/^Left/.test(it.fingers[i].name) ? P.L : P.R).k, true);
});

// --- Editing: a part's handle where the part is, a drag in the camera's plane, its model-space move on the pose ---
function pzModel(id) {
  const k = PZ.fk;
  if (!k) return null;
  switch (id) {
    case 'head': return k.gaze.clone();
    case 'chest': return k.chest.clone();
    case 'hips': return k.hips.clone().addScaledVector(RB_UP, -.1);   // (a little low: the rear hand rests just above the pelvis)
    case 'hL': case 'hR': return k.w[id[1]].clone();
    case 'eL': case 'eR': return k.e[id[1]].clone();
    case 'fL': case 'fR': return k.ank[id[1]].clone();
    case 'all': return new THREE.Vector3(k.hips.x, 0, k.hips.z);
  }
  return null;
}
function pzCtx() {
  const k = PZ.fk, two = o => ({L: o.L.clone(), R: o.R.clone()});
  return {qi: k.qC.clone().invert(), sh: two(k.sh), e: two(k.e), w: two(k.w), ank: two(k.ank), hip: two(k.hip), arm: {L: k.arm.L, R: k.arm.R}, leg: {L: k.leg.L, R: k.leg.R},
    chest: k.chest.clone(), hips: k.hips.clone(), hp: k.hp.clone(), gaze: k.gaze.clone()};
}
// Pose P0 with part id moved by d (model space, m), x = where the parts were (pzCtx): a new pose.
function pzApply(id, P0, d, x) {
  const P = pzClone(P0), L = RB_LINE, S = RB_SIDE, deg = 1 / RB_R, s = id[1];
  if (id === 'hL' || id === 'hR') {   // the wrist, in the chest's frame, within the arm's reach
    const v = pzV().fromArray(P0[s].p).add(d.clone().applyQuaternion(x.qi)), n = v.length(), hi = .99 * x.arm[s];
    if (n > hi) v.multiplyScalar(hi / n); else if (n < .1 && n > 1e-6) v.multiplyScalar(.1 / n);
    P[s].p = pzR(v.toArray());
  } else if (id === 'eL' || id === 'eR') {   // the elbow's side: where the pointer is about the shoulder-wrist line
    const ax = x.w[s].clone().sub(x.sh[s]).normalize(), v = x.e[s].clone().add(d).sub(x.sh[s]);
    v.addScaledVector(ax, -v.dot(ax));   // (only its way off that line: along it, it would turn the arm's later moves)
    if (v.lengthSq() > 1e-8) P[s].e = pzR(v.normalize().applyQuaternion(x.qi).toArray());
  } else if (id === 'chest') {   // the upper body tipped about the pelvis: toward the opponent, and sideways
    const v0 = x.chest.clone().sub(x.hips), v1 = v0.clone().add(d), aL = a => Math.atan2(a.dot(L), a.y), aS = a => Math.atan2(a.dot(S), a.y);
    P.b.leanL = pzC(P0.b.leanL + pzW(aL(v1) - aL(v0)) * deg, -60, 75);
    P.b.leanS = pzC(P0.b.leanS - pzW(aS(v1) - aS(v0)) * deg, -45, 45);
  } else if (id === 'hips') {
    P.b.lx = pzC(P0.b.lx + d.dot(L), -2, 2); P.b.lz = pzC(P0.b.lz + d.dot(S), -2, 2); P.b.dip = pzC(P0.b.dip - d.y, -.15, .6);
  } else if (id === 'fL' || id === 'fR') {   // the ankle: never under the floor, within the leg's reach
    const f0 = P0['f' + s], f = P['f' + s], a = x.ank[s].clone().add(d), up = f0.up + d.y;
    if (up < 0) a.y -= up;
    const r = a.clone().sub(x.hip[s]), n = r.length(), max = .96 * x.leg[s];
    if (n > max) a.copy(x.hip[s]).addScaledVector(r, max / n);
    const dd = a.sub(x.ank[s]);
    f.x = pzC(f0.x + dd.dot(L), -2.5, 2.5); f.z = pzC(f0.z + dd.dot(S), -2, 2); f.up = pzC(f0.up + dd.y, 0, 1.3);
  } else if (id === 'all') {   // the pelvis and both feet along the floor
    const dx = d.dot(L), dz = d.dot(S);
    P.b.lx = pzC(P0.b.lx + dx, -2, 2); P.b.lz = pzC(P0.b.lz + dz, -2, 2);
    for (const k of ['fL', 'fR']) { P[k].x = pzC(P0[k].x + dx, -2.5, 2.5); P[k].z = pzC(P0[k].z + dz, -2, 2); }
  } else if (id === 'head') {   // the head turned and nodded to look at the dragged point
    const v0 = x.gaze.clone().sub(x.hp), v1 = v0.clone().add(d), el = a => Math.atan2(a.y, Math.hypot(a.x, a.z));
    P.h.yaw = pzC(P0.h.yaw + PZ.ySign * pzW(Math.atan2(v1.x, v1.z) - Math.atan2(v0.x, v0.z)) * deg, -80, 80);
    P.h.nod = pzC(P0.h.nod - PZ.nSign * (el(v1) - el(v0)) * deg, -50, 50);
  }
  return P;
}
function pzPush() {
  PZ.undo.push({poses: pzClone(PZ.poses), cur: PZ.cur});
  if (PZ.undo.length > 80) PZ.undo.shift();
}
function pzSet(P) { PZ.poses[PZ.cur] = P; PZ.ver++; }
function pzStop() { if (PZ.play) pzPlay(); }
// the pointer on the plane (camera's ray)
function pzRay(sx, sy, plane) {
  const rc = PZ.rc || (PZ.rc = new THREE.Raycaster());
  rc.setFromCamera(new THREE.Vector2(sx / innerWidth * 2 - 1, 1 - sy / innerHeight * 2), VW.camera);
  return rc.ray.intersectPlane(plane, pzV());
}
function pzDown(e) {
  if (PZ.drag || !PZ.fk || !PZ.guard) return;
  e.preventDefault(); e.stopPropagation();
  pzStop();
  let id = e.currentTarget.dataset.id, best = 1e9;   // (handles that overlap: the nearest, the selected one first)
  for (const part of PZ_PARTS) {
    const q = PZ.scr[part.id];
    if (!q) continue;
    const d = Math.hypot(q.x - e.clientX, q.y - e.clientY) - (part.id === PZ.sel ? 8 : 0);
    if (d < best && d < 26) { best = d; id = part.id; }
  }
  try { e.currentTarget.setPointerCapture(e.pointerId); } catch (_) { /* (not capturable: the window's listeners still follow it) */ }
  pzSelect(id);
  const it = VW.it, M = it.body.matrixWorld, w = pzModel(id).applyMatrix4(M);
  const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(VW.camera.getWorldDirection(pzV()), w);
  pzPush();
  PZ.drag = {id, pid: e.pointerId, plane, hit0: pzRay(e.clientX, e.clientY, plane) || w, Mi: M.clone().invert(), P0: pzClone(PZ.poses[PZ.cur]), x: pzCtx()};
  PZ.el[id].classList.add('on');
}
function pzMove(e) {
  const D = PZ.drag;
  if (!D || e.pointerId !== D.pid) return;
  const hit = pzRay(e.clientX, e.clientY, D.plane);
  if (!hit) return;
  const d = hit.applyMatrix4(D.Mi).sub(D.hit0.clone().applyMatrix4(D.Mi));
  pzSet(pzApply(D.id, D.P0, d, D.x));
}
function pzUp(e) {
  const D = PZ.drag;
  if (!D || e.pointerId !== D.pid) return;
  PZ.drag = null; PZ.el[D.id].classList.remove('on');
  if (JSON.stringify(D.P0) === JSON.stringify(PZ.poses[PZ.cur])) PZ.undo.pop();   // (a tap: nothing moved)
  else pzChanged();
}
// keys and controller: part sel moved by (dx, dy, dz) m along the camera's right, up and forward
function pzNudge(dx, dy, dz, held) {
  if (!PZ.fk || !PZ.guard || PZ.drag) return;
  pzStop();
  const now = performance.now();
  if (!held || now - PZ.lastPush > 900) pzPush();
  PZ.lastPush = now;
  const cam = VW.camera, M = VW.it.body.matrixWorld, Mi = M.clone().invert();
  const r = pzV().setFromMatrixColumn(cam.matrixWorld, 0), u = pzV().setFromMatrixColumn(cam.matrixWorld, 1), f = cam.getWorldDirection(pzV());
  const w0 = pzModel(PZ.sel).applyMatrix4(M), w1 = w0.clone().addScaledVector(r, dx).addScaledVector(u, dy).addScaledVector(f, dz);
  const d = w1.applyMatrix4(Mi).sub(w0.applyMatrix4(Mi));
  pzSet(pzApply(PZ.sel, PZ.poses[PZ.cur], d, pzCtx()));
  pzChanged();
}
// a value of the selected part (a button of its row), a turn (dir -1 / 1; 0 straight again)
function pzOpt(key, v) {
  const id = PZ.sel, P = PZ.poses[PZ.cur], o = id[0] === 'h' && id !== 'hips' && id !== 'head' ? P[id[1]] : id[0] === 'f' ? P[id] : null;
  if (!o || o[key] === v) return;
  pzStop(); pzPush();
  const N = pzClone(P);
  (id[0] === 'f' ? N[id] : N[id[1]])[key] = v;
  pzSet(N); pzChanged();
}
function pzTurn(dir) {
  const id = PZ.sel, P = pzClone(PZ.poses[PZ.cur]), t = PZ.turn * dir, kind = pzPart(id).kind;
  const go = (o, k, lim) => { o[k] = dir ? pzC(Math.round(o[k] + t), -lim, lim) : 0; };
  if (kind === 'chest') go(P.b, 'chest', 70);
  else if (kind === 'hips') go(P.b, 'yaw', 90);
  else if (kind === 'head') { if (dir) P.h.yaw = pzC(Math.round(P.h.yaw + t * PZ.ySign), -80, 80); else P.h.yaw = 0; }
  else if (kind === 'foot') go(P[id], 'yaw', 60);
  else if (kind === 'hand') { const h = P[id[1]]; h.roll = dir ? ((Math.round(h.roll / 45) * 45 + 45 * dir) % 360 + 360) % 360 : PZ.guard[id[1]].roll; if (h.roll > 180) h.roll -= 360; }
  else return;
  if (JSON.stringify(P) === JSON.stringify(PZ.poses[PZ.cur])) return;
  pzStop(); pzPush(); pzSet(P); pzChanged();
}
// the next value of one of the part's groups (keys and controller)
function pzCycle(g) {
  const part = pzPart(PZ.sel), o = PZ_OPTS[part.kind], grp = o.groups.filter(x => !x.turn)[g];
  if (!grp) { pzTurn(g ? 1 : -1); return; }
  const P = PZ.poses[PZ.cur], cur = (part.kind === 'foot' ? P[PZ.sel] : P[PZ.sel[1]])[grp.key];
  let i = grp.vals.findIndex(v => Math.abs(v[0] - cur) < 1e-6);
  pzOpt(grp.key, grp.vals[(i + 1) % grp.vals.length][0]);
}
function pzUndo() {
  const u = PZ.undo.pop();
  if (!u) { pzStatus('Niente da annullare'); return; }
  pzStop();
  PZ.poses = u.poses; PZ.cur = Math.min(u.cur, u.poses.length - 1); PZ.ver++;
  pzChanged();
}
function pzGuard() {
  if (!PZ.guard) return;
  const P = pzClone(PZ.guard); P.note = PZ.poses[PZ.cur].note;
  if (JSON.stringify(P) === JSON.stringify(PZ.poses[PZ.cur])) return;
  pzStop(); pzPush(); pzSet(P); pzChanged();
}
function pzGo(i) {
  if (!PZ.poses.length) return;
  pzStop();
  const n = PZ.poses.length, j = Math.max(0, Math.min(n - 1, i));
  if (j === PZ.cur) return;
  PZ.cur = j; PZ.ver++; PZ.ui.dirty = true;
}
function pzAdd() {
  if (!PZ.guard) return;
  if (PZ.poses.length >= PZ.max) { pzStatus('Massimo ' + PZ.max + ' pose'); return; }
  pzStop(); pzPush();
  const P = pzClone(PZ.poses[PZ.cur]); P.note = '';
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
  if (PZ.poses.length < 2) { pzStatus('Aggiungi almeno 2 pose per riprodurle'); return; }
  if (PZ.drag) return;
  PZ.play = {f0: VW.F.af + (RN_D.k || 0), at: {a: 0, b: 1, back: false}}; PZ.ver++; PZ.ui.dirty = true;
}
function pzView(k) { VW.yaw = F3_YAW - k * Math.PI / 4; PZ.view = k; PZ.ui.dirty = true; }   // 0 side, 1 three-quarters, 2 front

// --- Saving: the database (collection "animazioni"), this device, the data for Claude ---
function pzDoc() {
  return {v: 1, name: PZ.name, note: PZ.note, frames: PZ.T, updated: Date.now(),
    legenda: 'Pose di Ren (preview/ren-anim/mods/posa.js). Ogni posa sopra la guardia base, metri e gradi: b {yaw bacino, chest torsione busto, leanL piega verso l\'avversario, leanS piega di lato (+ verso la sua destra), lx avanti, lz di lato (+ sua sinistra), dip giù}; h {yaw, nod (< 0 mento su)}; L/R mano {p polso dalla spalla e e gomito, nel busto [sua sinistra, su, avanti]; k 0 aperta .. 1 pugno; roll palmo 0 giù 90 di lato 180 su; wrist polso > 0 indietro}; fL/fR piede {x avanti, z di lato, up su, heel tallone, yaw giro, toe punta in aria}. L = davanti, R = dietro.',
    poses: PZ.poses.map(P => JSON.parse(JSON.stringify(P, (k, v) => typeof v === 'number' ? Math.round(v * 1000) / 1000 : v)))};
}
function pzLoad(id, doc, keepUndo) {
  if (!doc || !Array.isArray(doc.poses) || !doc.poses.length) return false;
  if (!PZ.guard) { PZ.pending = {id, doc}; return true; }
  PZ.id = id || null; PZ.name = typeof doc.name === 'string' && doc.name.trim() ? doc.name.slice(0, 60) : 'Animazione';
  PZ.note = typeof doc.note === 'string' ? doc.note.slice(0, 2000) : '';
  PZ.poses = doc.poses.slice(0, PZ.max).map(pzFill); PZ.cur = 0; PZ.play = null;
  if (!keepUndo) PZ.undo = [];
  PZ.ver++; PZ.ui.dirty = true; PZ.ui.notes = true;
  return true;
}
function pzLocal(doc) { try { localStorage.setItem(PZ_KEY, JSON.stringify({id: PZ.id, doc})); } catch (_) { /* (private window: the database alone) */ } }
function pzChanged() {
  PZ.ver++; PZ.edited = true; PZ.ui.dirty = true;
  clearTimeout(PZ.timer); PZ.timer = setTimeout(pzSave, 700);   // (a burst of edits: one write once they pause)
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
    PZ.retry = 0; pzLocal(doc); pzStatus('Salvato');
  } catch (e) {
    const code = e && e.code;
    if ((code === 'unavailable' || code === 'resource_exhausted') && PZ.retry < 2) { PZ.retry++; PZ.dirty = true; await new Promise(r => setTimeout(r, 1500 + 1500 * Math.random())); }
    else { PZ.retry = 0; pzStatus(pzErr(code)); if (code === 'invalid_argument' || code === 'revoked' || code === 'not_granted' || code === 'capability_disabled' || code === 'capability_removed') PZ.col = null; }
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
  try { const s = JSON.parse(localStorage.getItem(PZ_KEY) || 'null'); if (s && s.doc) { PZ.localDoc = s; pzLoad(s.id, s.doc); } } catch (_) { /* (none, or not readable) */ }
  pzStatus('Caricamento…');
  let db = null;
  try { const c = window.claude; db = c && typeof c.use === 'function' ? await c.use('db') : null; } catch (_) { db = null; }
  if (!db) { PZ.loaded = true; pzStatus('Salvo su questo dispositivo'); return; }
  PZ.db = db; PZ.col = db.collection('animazioni');
  const wait = setTimeout(() => { if (!PZ.loaded) pzStatus('Il salvataggio non risponde ancora'); }, 10000);
  PZ.col.orderBy('updated', 'desc').limit(50).onSnapshot(snap => {
    PZ.list = snap.docs.map(d => { const x = d.data() || {}; return {id: d.id, name: typeof x.name === 'string' ? x.name.slice(0, 60) : 'Animazione', updated: +x.updated || 0, doc: x}; });
    PZ.ui.list = true;
    if (snap.metadata.fromCache || PZ.loaded) return;
    clearTimeout(wait); PZ.loaded = true;
    // the first answer: the newest animation, unless this device has a newer copy of one, or Denis already began
    const L = PZ.localDoc, mine = L && PZ.list.find(a => a.id === L.id), open = mine || PZ.list[0];
    if (PZ.edited || (L && L.doc && (!mine || (+L.doc.updated || 0) > mine.updated))) pzSave();   // (this device's copy is newer, or was never saved there)
    else if (open) { pzLoad(open.id, open.doc); pzStatus('Aperta «' + open.name + '»'); }
    else pzStatus('Pronto: le pose si salvano da sole');
  }, err => { clearTimeout(wait); PZ.loaded = true; pzStatus(pzErr(err && err.code)); if (err && err.code !== 'unavailable') PZ.col = null; });
}
function pzNew() {
  if (!PZ.guard) return;
  pzStop();
  PZ.id = null; PZ.name = 'Animazione ' + (PZ.list.length + 1); PZ.note = ''; PZ.poses = [pzClone(PZ.guard)]; PZ.cur = 0; PZ.undo = [];
  PZ.ui.notes = true; pzChanged(); pzSave();
}
function pzCopy() {
  const txt = JSON.stringify(pzDoc());
  const show = () => { const t = document.getElementById('pzData'); t.hidden = false; t.value = txt; t.focus(); t.select(); pzStatus('Copia il testo qui sotto e incollalo a Claude'); };
  try { navigator.clipboard.writeText(txt).then(() => pzStatus('Dati copiati: incollali a Claude'), show); } catch (_) { show(); }
}

// --- The page: handles over the picture, the poses' row, the selected part's row, tools, notes ---
function pzStatus(t) { const s = document.getElementById('pzSt'); if (s && s.textContent !== t) s.textContent = t; }
function pzBtn(label, f, id) {
  const b = document.createElement('button'); if (id) b.id = id;
  b.innerHTML = '<span></span>'; b.firstChild.textContent = label; b.addEventListener('click', f);
  return b;
}
function pzSelect(id) { if (PZ.sel === id) return; PZ.sel = id; PZ.ui.dirty = true; }
function pzStep(dir) { const i = PZ_PARTS.findIndex(p => p.id === PZ.sel); pzSelect(PZ_PARTS[(i + dir + PZ_PARTS.length) % PZ_PARTS.length].id); }
// the selected part's row: its name's hint and its groups of values
function pzPartUi() {
  const row = PZ.ui.part0, part = pzPart(PZ.sel), o = PZ_OPTS[part.kind], P = PZ.poses[PZ.cur];
  if (PZ.ui.partFor !== part.id) {
    PZ.ui.partFor = part.id; row.textContent = '';
    if (o.hint) { const h = document.createElement('span'); h.className = 'pzMsg'; h.textContent = o.hint; row.appendChild(h); }
    for (const g of o.groups) {
      const box = document.createElement('div'); box.className = 'opt'; box.append(g.label + ' ');
      if (g.turn) for (const [lab, d] of [['◀', -1], ['▶', 1], ['Azzera', 0]]) { const b = pzBtn(lab, () => pzTurn(d)); if (d) b.setAttribute('aria-label', g.label + (d < 0 ? ' a sinistra' : ' a destra')); box.appendChild(b); }
      else for (const [v, lab] of g.vals) { const b = pzBtn(lab, () => pzOpt(g.key, v)); b.dataset.key = g.key; b.dataset.v = v; box.appendChild(b); }
      row.appendChild(box);
    }
  }
  if (!P) return;
  const src = part.kind === 'hand' ? P[part.id[1]] : part.kind === 'foot' ? P[part.id] : null;
  for (const b of row.querySelectorAll('button[data-key]')) vwPressEl(b, !!src && Math.abs(src[b.dataset.key] - +b.dataset.v) < 1e-6);
}
function vwPressEl(b, on) { const v = on ? 'true' : 'false'; if (b.getAttribute('aria-pressed') !== v) b.setAttribute('aria-pressed', v); }
// the poses' row: one numbered button per pose, the current one pressed
function pzStrip() {
  const box = PZ.ui.chips, n = PZ.poses.length;
  while (box.children.length > n) box.lastChild.remove();
  while (box.children.length < n) { const i = box.children.length, b = pzBtn(String(i + 1), () => pzGo(i)); b.className = 'chip'; b.setAttribute('aria-label', 'Posa ' + (i + 1)); box.appendChild(b); }
  const at = PZ.play && PZ.play.at;
  [...box.children].forEach((b, i) => vwPressEl(b, at ? i === at.b : i === PZ.cur));
  if (PZ.pop !== undefined && box.children[PZ.pop]) { const b = box.children[PZ.pop]; b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop'); b.scrollIntoView({block: 'nearest', inline: 'nearest'}); PZ.pop = undefined; }
  PZ.ui.play.firstChild.textContent = PZ.play ? 'Ferma' : 'Riproduci'; vwPressEl(PZ.ui.play, !!PZ.play);
  PZ.ui.del.disabled = n < 2; PZ.ui.add.disabled = n >= PZ.max;
}
function pzTitle() {
  const sm = document.querySelector('#name small'), at = PZ.play && PZ.play.at;
  const t = at ? (at.back ? 'Riproduzione · torna alla posa 1' : at.a === at.b ? 'Riproduzione · posa ' + (at.a + 1) : 'Riproduzione · posa ' + (at.a + 1) + ' → ' + (at.b + 1))
    : 'Posa ' + (PZ.cur + 1) + ' di ' + PZ.poses.length + ' · ' + pzPart(PZ.sel).name;
  if (sm && sm.textContent !== t) sm.textContent = t;
}
function pzNotes(open) {
  const N = document.getElementById('pzN');
  if (open === undefined) open = N.hidden;
  N.hidden = !open; vwPressEl(document.getElementById('pzNb'), open);
  if (open) { PZ.ui.notes = true; pzNotesUi(); } else document.getElementById('pzData').hidden = true;
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
  add('', PZ.list.length ? 'Apri un\'animazione salvata…' : 'Nessun\'altra animazione salvata');
  for (const a of PZ.list) add(a.id, a.name + (a.id === PZ.id ? ' (aperta)' : ''));
  sel.disabled = !PZ.list.length;
}
function pzUi(VW) {
  const css = document.createElement('style');
  css.textContent = `
#moves,#bottom>.row:not(.pz),#now{display:none!important}
#pzH{position:fixed;inset:0;z-index:2;pointer-events:none}
.pzh{position:absolute;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;pointer-events:auto;cursor:grab;touch-action:none}
.pzh::before{content:"";position:absolute;inset:8px;border-radius:50%;border:3px solid var(--c);background:rgba(20,18,28,.35);box-shadow:0 0 0 1.5px rgba(0,0,0,.75),0 2px 6px rgba(0,0,0,.45);transition:transform .12s ease-out,background .12s}
.pzh[aria-pressed="true"]::before{background:var(--c);transform:scale(1.3)}
.pzh.on{cursor:grabbing}.pzh.on::before{transform:scale(1.6)}
@media (pointer:coarse){.pzh{width:44px;height:44px;margin:-22px 0 0 -22px}.pzh::before{inset:12px}}
#top{flex-wrap:wrap}
#pzTop{display:flex;align-items:center;justify-content:flex-end;gap:6px;pointer-events:auto;min-width:0;margin-left:auto}
#pzChips{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;max-width:40vw;padding:3px 2px;touch-action:pan-x}#pzChips::-webkit-scrollbar{display:none}
#pzChips .chip{flex:0 0 auto;min-width:36px;padding:5px 9px 4px}
#pzTop>button{flex:0 0 auto}
button:disabled{opacity:.4;cursor:default}
.row.pz{align-items:center;min-height:32px;gap:6px 12px}
.pzMsg{color:var(--dim);font-size:15px}
#pzInfo{display:block;font-family:var(--body);font-style:italic;font-size:13px;letter-spacing:.04em;color:var(--dim);text-shadow:0 1px 3px #000;transform:none;margin-top:2px}
#pzInfo #fps{display:inline;font-size:inherit;color:inherit}#pzInfo #fps:not(:empty)::before{content:" · "}
#pzN{position:fixed;z-index:5;left:50%;bottom:calc(10px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);width:min(560px,calc(100vw - 32px));max-height:calc(100vh - 20px);overflow:auto;
  background:rgba(20,18,28,.96);border:1px solid var(--line);padding:12px;display:flex;flex-direction:column;gap:8px;box-shadow:0 8px 30px rgba(0,0,0,.6)}
#pzN[hidden]{display:none}
#pzN label{display:flex;flex-direction:column;gap:4px;color:var(--dim);font-size:14px}
#pzN input,#pzN textarea,#pzN select{font:inherit;font-style:normal;font-weight:600;font-size:16px;color:var(--ink);background:#0d0c13;border:1px solid var(--line);padding:6px 8px;user-select:text;-webkit-user-select:text;min-width:0}
#pzN textarea{resize:vertical}
#pzN .row{align-items:center}
@keyframes pzPop{0%{transform:skewX(-10deg) scale(.55)}60%{transform:skewX(-10deg) scale(1.18)}100%{transform:skewX(-10deg) scale(1)}}
.pop{animation:pzPop .28s ease-out}
@media (max-height:430px){#name{font-size:34px}#name small{font-size:14px}.row.pz{min-height:28px}.pzMsg{font-size:13px}}
@media (pointer:coarse) and (max-height:430px){#hint{display:none}}
@media (prefers-reduced-motion:reduce){.pop{animation:none}.pzh::before{transition:none}}`;
  document.head.appendChild(css);
  // the handles
  const box = document.createElement('div'); box.id = 'pzH';
  for (const part of PZ_PARTS) {
    const h = document.createElement('div'); h.className = 'pzh'; h.dataset.id = part.id; h.style.setProperty('--c', part.c);
    h.setAttribute('role', 'button'); h.setAttribute('aria-label', part.name); h.title = part.name;
    h.addEventListener('pointerdown', pzDown);
    box.appendChild(h); PZ.el[part.id] = h;
  }
  document.getElementById('stage').after(box); PZ.ui.handles = box;
  addEventListener('pointermove', pzMove); addEventListener('pointerup', pzUp); addEventListener('pointercancel', pzUp);
  // the poses' row (top right)
  const top = document.createElement('div'); top.id = 'pzTop';
  const chips = document.createElement('div'); chips.id = 'pzChips'; chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', 'Pose');
  PZ.ui.chips = chips;
  PZ.ui.add = pzBtn('+ Posa', pzAdd, 'pzAdd'); PZ.ui.del = pzBtn('Elimina', pzDel, 'pzDel'); PZ.ui.play = pzBtn('Riproduci', pzPlay, 'pzPlay');
  top.append(chips, PZ.ui.add, PZ.ui.del, PZ.ui.play);
  document.getElementById('top').appendChild(top);
  // the part's row and the tools' row (bottom)
  const bottom = document.getElementById('bottom'), hint = document.getElementById('hint');
  const part = document.createElement('div'); part.className = 'row pz'; part.id = 'pzPart'; PZ.ui.part0 = part;
  const tools = document.createElement('div'); tools.className = 'row pz'; tools.id = 'pzTools';
  const view = document.createElement('div'); view.className = 'opt'; view.append('Vista ');
  PZ.ui.views = [['Lato', 0], ['3/4', 1], ['Fronte', 2]].map(([t, k]) => { const b = pzBtn(t, () => pzView(k)); view.appendChild(b); return b; });
  const hb = pzBtn('Punti', () => { PZ.showH = !PZ.showH; PZ.ui.dirty = true; }, 'pzHb'); hb.setAttribute('aria-label', 'Mostra i punti da trascinare'); PZ.ui.hb = hb;
  tools.append(pzBtn('Annulla', pzUndo, 'pzUndo'), pzBtn('Guardia', pzGuard, 'pzGuard'), view, hb, pzBtn('Note', () => pzNotes(), 'pzNb'));
  // the saving's state and the frames per second: a line under the title (the tools' row stays one line on a phone)
  const info = document.createElement('small'); info.id = 'pzInfo';
  const st = document.createElement('span'); st.id = 'pzSt'; st.setAttribute('role', 'status'); info.appendChild(st);
  const fps = document.getElementById('fps'); if (fps) info.appendChild(fps);
  document.getElementById('name').appendChild(info);
  bottom.insertBefore(part, hint); bottom.insertBefore(tools, hint);
  if (hint) hint.innerHTML = 'Trascina i punti colorati per muovere Ren; altrove per girare la vista, rotella o pizzico per avvicinarti.'
    + '<span class=kb> Tastiera: Tab parte, frecce sposta, PagSu/PagGiù in profondità, Q/E gira, 1-3 e 4-6 le scelte della parte, [ ] posa, N nuova posa, P riproduci, G guardia, Ctrl+Z annulla.'
    + ' Controller: levetta sinistra sposta, destra vista e profondità, dorsali parte, grilletti posa, A e X le scelte, Y riproduci, B annulla, Start nuova posa.</span>';
  // the notes (for Claude): the animation's name and words, each pose's own, the saved animations, the data
  const N = document.createElement('div'); N.id = 'pzN'; N.hidden = true; N.setAttribute('role', 'dialog'); N.setAttribute('aria-label', 'Note per Claude');
  N.innerHTML = '<label>Nome dell\'animazione<input id="pzName" maxlength="60" autocomplete="off"></label>'
    + '<label>Note per Claude: i tempi e cosa deve succedere<textarea id="pzNote" rows="3" maxlength="2000" placeholder="Es. dalla 2 alla 3 velocissimo, la 4 tenuta un attimo"></textarea></label>'
    + '<label>Nota della posa <span id="pzPn">1</span><input id="pzPnote" maxlength="300" autocomplete="off" placeholder="Es. qui colpisce"></label>'
    + '<textarea id="pzData" rows="3" readonly hidden aria-label="I dati delle pose"></textarea>'
    + '<div class="row"><select id="pzList" aria-label="Animazioni salvate"></select></div>'
    + '<div class="row"></div>';
  N.lastChild.append(pzBtn('Nuova animazione', pzNew, 'pzNew'), pzBtn('Copia i dati', pzCopy, 'pzCopy'));
  const bg = document.getElementById('kitBg'); if (bg) N.lastChild.appendChild(bg);   // (the kit's floor or arena)
  N.lastChild.appendChild(pzBtn('Chiudi', () => pzNotes(false), 'pzClose'));
  document.body.appendChild(N);
  const typed = (id, f) => document.getElementById(id).addEventListener('input', e => { f(e.target.value); PZ.edited = true; clearTimeout(PZ.timer); PZ.timer = setTimeout(pzSave, 900); });
  typed('pzName', v => { PZ.name = v.slice(0, 60); });
  typed('pzNote', v => { PZ.note = v.slice(0, 2000); });
  typed('pzPnote', v => { if (PZ.poses[PZ.cur]) PZ.poses[PZ.cur].note = v.slice(0, 300); });
  document.getElementById('pzList').addEventListener('change', e => {
    const a = PZ.list.find(x => x.id === e.target.value);
    e.target.blur();
    if (a && a.id !== PZ.id) { pzStop(); if (pzLoad(a.id, a.doc)) { pzLocal(pzDoc()); pzStatus('Aperta «' + a.name + '»'); } }
    PZ.ui.list = true;
  });
  PZ.ui.dirty = true; PZ.ui.list = true;
  dispatchEvent(new Event('resize'));
}
// keys (taken before the viewer's own: its plays and speeds are not this page's)
function pzKeys() {
  addEventListener('keydown', e => {
    const t = e.target, tag = t && t.tagName, typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    e.stopImmediatePropagation();
    if (typing) { if (e.key === 'Escape') { t.blur(); pzNotes(false); } return; }
    if (e.key === 'Escape') { pzNotes(false); pzStop(); return; }
    const k = e.key, K = k.length === 1 ? k.toLowerCase() : k, step = e.shiftKey ? .05 : .01, onBtn = tag === 'BUTTON';
    if ((e.ctrlKey || e.metaKey) && K === 'z') { e.preventDefault(); pzUndo(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const act = {
      ArrowLeft: () => pzNudge(-step, 0, 0, e.repeat), ArrowRight: () => pzNudge(step, 0, 0, e.repeat),
      ArrowUp: () => pzNudge(0, step, 0, e.repeat), ArrowDown: () => pzNudge(0, -step, 0, e.repeat),
      PageUp: () => pzNudge(0, 0, step, e.repeat), PageDown: () => pzNudge(0, 0, -step, e.repeat),
      q: () => pzTurn(-1), e: () => pzTurn(1), '[': () => pzGo(PZ.cur - 1), ']': () => pzGo(PZ.cur + 1),
      n: () => pzAdd(), p: () => pzPlay(), g: () => pzGuard(), z: () => pzUndo(), h: () => { PZ.showH = !PZ.showH; PZ.ui.dirty = true; },
      v: () => pzView(((PZ.view || 0) + 1) % 3), Delete: () => pzDel(),
    }[K];
    const d = '123456'.indexOf(K);
    if (K === 'Tab' && !onBtn) { e.preventDefault(); pzStep(e.shiftKey ? -1 : 1); }
    else if (act && !(onBtn && (K === 'Enter' || K === ' '))) { e.preventDefault(); if (!e.repeat || /^Arrow|^Page/.test(K)) act(); }
    else if (d >= 0 && !e.repeat) { e.preventDefault(); pzPick(Math.floor(d / 3), d % 3); }
  }, true);
}
// value i of the part's group g (keys 1-3: the first group, 4-6: the second)
function pzPick(g, i) {
  const grp = PZ_OPTS[pzPart(PZ.sel).kind].groups.filter(x => !x.turn)[g];
  if (grp && grp.vals[i]) pzOpt(grp.key, grp.vals[i][0]);
}
// the controller: sticks move (left: in the camera's plane; right: x turns the view, y in depth), shoulders the part,
// triggers the pose, A and X the part's groups, Y plays, B undoes, Start a new pose, Back the guard
function pzPad() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [], now = performance.now(), dt = Math.min(.05, (now - (PZ.padT || now)) / 1000);
  PZ.padT = now;
  for (const g of pads) {
    if (!g) continue;
    const b = i => !!(g.buttons[i] && g.buttons[i].pressed), was = PZ.pad, hit = i => b(i) && !was[i];
    const ax = i => { const v = g.axes[i] || 0; return Math.abs(v) < .2 ? 0 : (v - Math.sign(v) * .2) / .8; };
    if (hit(4)) pzStep(-1); if (hit(5)) pzStep(1);
    if (hit(6)) pzGo(PZ.cur - 1); if (hit(7)) pzGo(PZ.cur + 1);
    if (hit(0)) pzCycle(0); if (hit(2)) pzCycle(1);
    if (hit(3)) pzPlay(); if (hit(1)) pzUndo(); if (hit(9)) pzAdd(); if (hit(8)) pzGuard();
    const mx = ax(0) + (b(15) ? 1 : 0) - (b(14) ? 1 : 0), my = -ax(1) + (b(12) ? 1 : 0) - (b(13) ? 1 : 0), mz = -ax(3), v = .5 * dt;   // (.5 m/s at full tilt)
    if (mx || my || mz) { pzNudge(mx * v, my * v, mz * v, PZ.padMove); PZ.padMove = true; } else PZ.padMove = false;
    if (ax(2)) VW.yaw += ax(2) * 2.2 * dt;
    for (let i = 0; i < 17; i++) was[i] = b(i);
    break;
  }
}
RN.hooks.boot.push(VW => {
  VW_PLAYS[0][1][0][1] = 1e9;   // (the kit's boot sets its guard's length on the first play: this page's one play lasts)
  CFG.looks.ren.clips = Object.assign({}, CFG.looks.ren.clips, {posa: {c: 'a191', at: 0}});   // the kit's held guard clip under it
  VW.PZ = PZ;   // (tests)
  pzUi(VW); pzKeys(); pzStore();
});
// each drawn frame: the controller, the handles where their parts are, the rows when something changed
RN.hooks.draw.push((VW, dt, cam) => {
  if (RN.pad !== pzPad) RN.pad = pzPad;   // (the scaffold sets its own after the boot hooks)
  const it = VW.it, show = PZ.showH && !PZ.play && !!PZ.fk, box = PZ.ui.handles;
  if (PZ.fk) {   // zoomed in (pinch, wheel), the camera closes on the selected part, not on the face
    it.root.updateMatrixWorld(true);
    const k = pzC((1 - VW.zoom) / .55, 0, 1), T = PZ.camT || (PZ.camT = pzV());
    if (!PZ.drag) { const p = pzModel(PZ.sel).applyMatrix4(it.body.matrixWorld); T.set(VW.aimX + (p.x - VW.aimX) * k, .95 + (p.y - .95) * k, 0); }
    cam.position.set(T.x, T.y + .1 * (1 - k), cam.position.z); cam.lookAt(T.x, T.y, 0); cam.updateMatrixWorld();
  }
  if (box.style.display !== (show ? '' : 'none')) box.style.display = show ? '' : 'none';
  if (show) {
    it.root.updateMatrixWorld(true);
    const M = it.body.matrixWorld, w = innerWidth, h = innerHeight;
    for (const part of PZ_PARTS) {
      const v = pzModel(part.id).applyMatrix4(M).project(cam), x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h, el = PZ.el[part.id];
      PZ.scr[part.id] = {x, y};
      el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
      vwPressEl(el, part.id === PZ.sel);
    }
  }
  if (PZ.play) { const a = PZ.play.at, key = a.a + ',' + a.b + ',' + a.back; if (key !== PZ.ui.at) { PZ.ui.at = key; PZ.ui.dirty = true; } }
  if (PZ.ui.dirty && PZ.guard) {
    PZ.ui.dirty = false;
    pzStrip(); pzPartUi(); pzTitle(); pzNotesUi();
    vwPressEl(PZ.ui.hb, PZ.showH);
    const th = pzW(VW.yaw - F3_YAW);
    PZ.ui.views.forEach((b, k) => vwPressEl(b, Math.abs(th + k * Math.PI / 4) < .02));
    // the part's row may be taller or shorter: the picture fits the space left (not in the middle of a drag)
    const top = document.getElementById('bottom').getBoundingClientRect().top;
    if (PZ.ui.partTop !== undefined && Math.abs(top - PZ.ui.partTop) > .5 && !PZ.drag) dispatchEvent(new Event('resize'));
    if (!PZ.drag) PZ.ui.partTop = top;
  }
  if (PZ.ui.list) { PZ.ui.list = false; pzListUi(); }
});
// one play: the pose being edited, for as long as the page is open
VW_PLAYS.length = 0;
VW_PLAYS.push(['Posa', [['posa', 1e9]]]);
VW_NAMES.posa = 'Posa';
