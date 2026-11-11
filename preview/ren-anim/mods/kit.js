// --- kit.js: Ren's fighting kit, keyed by hand from Denis's four reference sheets (12/11/2026). ---
// Stage 1 (what Denis asked to see first): the guard loop, the gliding step and the snapping palm. Everything is a
// pure function of the act's frame, drawn through the same solver as the rest (body.js): feet placed where the keys
// say (a planted foot does not move in the world), legs and arms by IK from the held guard pose, nothing through the
// body. No new clips, no effects: the pose alone (the hair and the sash follow it, a little late, as everywhere).
//
// Identity (from Denis's brief): agile, technical, explosive up close. Open guard, knees slightly bent, low steps,
// palms; the force starts in the feet, goes through the pelvis and the torso and arrives at the hand. Controlled in the
// guard, a short load, a dry acceleration into the strike, a quick but believable recovery.
//
// Frames are the game's (60 a second). All the numbers of these three are PROPOSALS: the project defines none of them.
//   idle  "Guardia elastica": the sheets' guard (3/4 toward the camera, a wide low stance, the lead (left) hand open
//         and forward at chest height, the rear hand open on the stomach), a loop of 144 frames (2.4 s): two breaths
//         (72 each) and one shift of the weight forward and back. Feet flat and still.
//   pr    "Passo radente": 26 frames, 0.40 m forward: load 0-7 (the weight onto the rear leg, the knees give), push
//         7-14 (the rear leg drives, the front foot leaves on frame 8, 10 cm up at most with its toes up, and lands on
//         14), landing 14-17 (a deep lunge, the front knee takes the weight), follow 15-23 (the rear foot skims 3 cm off
//         the floor, lands on 22; the stance as it was). The body travels the same 0.40 m, without a stop on the landing.
//   palm  "Palmo a scatto" (the lead hand, as the sheet has it): 28 frames = startup 9 + active 3 + recovery 16: load
//         0-5 (hips and chest square up a little, the knees give, the lead hand drawn back in front of the face), drive
//         5-10 in a chain (the rear leg pushes the hips 10 cm forward, 5-9; hips then chest turn the lead side forward,
//         the body blades; the arm last, straight out at shoulder height, fastest at the impact on frame 10), active
//         10-12 (palm out, fingers up; the rear hand up by the head), recovery 13-28 (a quick recoil, then a
//         controlled settle into the guard).

const RK = {
  loop: 144, breath: 72, d: .4,
  len: {pr: 26, palm: 28},
  reach: .965,      // share of the arm's length from shoulder to wrist at the impact (the elbow a little bent)
  // The base guard all three start from and come back to (the sheets' "Guardia", pose 1): from the held guard clip,
  // the hips turned toward the opponent (yaw, deg: the clip's body faces the camera more than the sheets' 3/4), the
  // chest's own twist (chest), a lean toward the opponent (leanL), the pelvis lower (dip, m: a wider, deeper stance),
  // the head following the chest more (stab: how much of the clip's own head direction it keeps; head: its nod, deg,
  // < 0 chin up; headYaw: its turn toward the opponent), the feet moved along the fight line (front, rear: m) and
  // turned toward it about their ankles (frontYaw, rearYaw: deg).
  g: {yaw: 27, chest: -5, leanL: 8, dip: .1, head: -14, stab: .25, headYaw: 10, front: .08, rear: -.17, frontYaw: 25, rearYaw: 72},
  base: 0,          // mm: the fighter's x when the current gliding step began (the viewer moves F.x with the step)
  grid: null, show: 'neutro',
};

// --- Keys ---
// rkKey: [frame, value, ease] (value a number or an array), each segment eased on its own: 'snap' (from rest, faster
// and faster, 1.5 times the mean speed at its end: a strike), 'lin', default smoothstep (from rest to rest).
// rkMono: [frame, value] through a monotone cubic (the speed carries through a key, no overshoot; at rest at both
// ends): the body's tracks, so a step or a drive never stops on a key.
function rkEase(u, e) {
  u = Math.max(0, Math.min(1, u));
  if (e === 'snap') return u * u * (3 - u) / 2;
  if (e === 'lin') return u;
  return u * u * (3 - 2 * u);
}
function rkKey(keys, f) {
  if (f <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (f > keys[i][0]) continue;
    const [f0, a] = keys[i - 1], [f1, b, e] = keys[i], u = rkEase((f - f0) / (f1 - f0), e);
    return Array.isArray(a) ? a.map((x, k) => x + (b[k] - x) * u) : a + (b - a) * u;
  }
  return keys[keys.length - 1][1];
}
function rkMono(keys) {
  const n = keys.length, x = keys.map(k => k[0]), y = keys.map(k => k[1]), d = [], m = new Array(n).fill(0);
  for (let i = 0; i + 1 < n; i++) d.push((y[i + 1] - y[i]) / (x[i + 1] - x[i]));
  for (let i = 1; i + 1 < n; i++) {   // (Fritsch-Butland: a weighted harmonic mean of the slopes beside the key)
    if (d[i - 1] * d[i] <= 0) continue;
    const h0 = x[i] - x[i - 1], h1 = x[i + 1] - x[i];
    m[i] = 3 * (h0 + h1) / ((2 * h1 + h0) / d[i - 1] + (h1 + 2 * h0) / d[i]);
  }
  return f => {
    if (f <= x[0]) return y[0];
    if (f >= x[n - 1]) return y[n - 1];
    let i = 0; while (f > x[i + 1]) i++;
    const h = x[i + 1] - x[i], t = (f - x[i]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * y[i] + (t3 - 2 * t2 + t) * h * m[i] + (3 * t2 - 2 * t3) * y[i + 1] + (t3 - t2) * h * m[i + 1];
  };
}
// A bump 0 -> 1 -> 0 over frames f0..f1 (a stepping foot's height), leaving and meeting the floor at no speed.
function rkArc(f, f0, f1) { if (f <= f0 || f >= f1) return 0; const s = Math.sin(Math.PI * (f - f0) / (f1 - f0)); return s * s; }
const rkF = (F, act) => Math.max(0, Math.min(RK.len[act], F.af));

// --- The guard ("Guardia elastica"): style.js's preset K, from the sheets: the lead hand open, forward at chest height,
// fingers up, palm toward the opponent; the rear hand open by the solar plexus, fingers across, palm in. ---
RS.presets.K = {curl: .15, armW: 1, flow: {period: 150, lead: 0, rear: 0},
  lead: {pos: [.33, -.02, .06], fing: [.4, .9, 0], palm: [1, -.1, -.2], elbow: [.15, -1, .4]},   // (pos: from the lead shoulder)
  rear: {pos: [-.02, -.08, .21], fing: [.8, .1, .5], palm: [0, .15, -1], elbow: [-.6, -1, -.35]}};
rsPreset('K');
RS.fidget.first = 1e9;   // (no neck roll here: the loop is breath and weight only)
const RK_OWN = {idle: 1, pr: 1, palm: 1};
const rkWeight0 = rsWeight;
rsWeight = (F, y) => RK_OWN[F.act] ? 0 : rkWeight0(F, y);   // (style.js's guard arms: these acts' arms are done below)

// breath b (0 out .. 1 in) and weight w (-1 back .. 1 forward) at a frame: both periodic in RK.loop
function rkGuard(t) {
  return {b: .5 - .5 * Math.cos(2 * Math.PI * t / RK.breath), w: Math.sin(2 * Math.PI * t / RK.loop)};
}
// the base guard on top of an act's own style
function rkBase(y) { const g = RK.g; y.yaw += g.yaw; y.chest += g.chest; y.leanL += g.leanL; y.dip += g.dip; y.head += g.head; y.stab = g.stab; }
RB.styleFor.idle = (y, F, S) => {
  const t = S.frame + 23 * F.side, g = rkGuard(t);
  y.lx = .035 * g.w;                       // the weight forward over the front foot, then back over the rear one
  y.dip = .004 + .01 * g.w * g.w;          // the knees give a little at either end of the shift
  y.leanL = 1.8 * g.w; y.chest = 2 * g.w;
  y.head = -.8 * g.b;
  rkBase(y);
};

// --- Passo radente ---
const RK_PR = {
  root: rkMono([[0, 0], [7, -.03], [14, .2], [17, .25], [23, RK.d], [26, RK.d]]),   // m along the fight line (the fighter)
  leanL: rkMono([[0, 0], [7, 5], [12, 9], [15, 6], [21, 1.5], [26, 0]]),
  dip: rkMono([[0, .004], [7, .035], [12, .04], [15, .07], [18, .06], [23, .012], [26, .004]]),
  chest: rkMono([[0, 0], [7, -4], [13, 5], [18, 2], [26, 0]]),
  head: rkMono([[0, 0], [7, 2], [13, -2], [26, 0]]),
  // feet: where along the line (m, in the world), how high (bump: from, to, m) and the heel's lift (deg)
  L: {x: [[0, 0], [8.8, 0], [13.4, RK.d]], up: [8, 14, .1], heel: [[0, 0], [7, 6], [8, 4], [14, 0], [26, 0]], toe: [[0, 0], [8, 0], [11, 20], [14, 0]]},
  R: {x: [[0, 0], [15.6, 0], [21.4, RK.d]], up: [14.8, 22.2, .03], heel: [[0, 0], [7, 3], [12, 12], [15, 14], [18, 7], [21.4, 0], [26, 0]], toe: [[0, 0]]},
  lead: [[0, 0], [8, 0], [13, 1], [20, .3], [26, 0]],   // the lead hand reaching a little ahead with the push
  phase: [[0, 'Caricamento'], [7, 'Spinta'], [14, 'Appoggio'], [17, 'Ritorno']],
};
RB.styleFor.pr = (y, F) => {
  const f = rkF(F, 'pr'), k = RK_PR;
  y.leanL = k.leanL(f); y.dip = k.dip(f); y.chest = k.chest(f); y.head = k.head(f);
  rkBase(y);
};

// --- Palmo a scatto: the lead hand, as the sheet has it (the rear hand comes up by the head) ---
// Load: the lead shoulder back a little (hips and chest square up), the knees give, the lead hand drawn back in front
// of the face. Drive: the rear leg pushes the hips forward 10 cm, hips then chest turn the lead side forward (the body
// blades: from the side camera the chest opens toward it), the arm last, straight out at shoulder height.
const RK_PA = {
  yaw: rkMono([[0, 0], [5, 5], [9, -20], [12, -20], [17, -7], [28, 0]]),
  chest: rkMono([[0, 0], [5, 6], [10, -25], [12, -25], [17, -9], [28, 0]]),
  leanL: rkMono([[0, 0], [5, -1], [9, 6], [12, 6], [17, 2], [28, 0]]),
  lx: rkMono([[0, 0], [5, -.02], [9, .10], [12, .105], [17, .04], [28, 0]]),
  dip: rkMono([[0, .004], [5, .025], [9, .03], [12, .03], [18, .01], [28, .004]]),
  head: rkMono([[0, 0], [5, 2], [9, -1], [28, 0]]),
  guard: rkMono([[0, 0], [3, 0], [8, 1], [14, 1], [24, 0]]),   // the rear hand up by the head
  back: rkMono([[12, 0], [16, .6], [28, 1]]),                  // the striking hand's way back to the guard
  flat: [[0, 0], [5, .6], [9, 1], [13, 1], [24, 0]],           // its fingers straight and together
  phase: [[0, 'Caricamento'], [5, 'Spinta'], [10, 'Impatto'], [13, 'Recupero']],
};
RB.styleFor.palm = (y, F) => {
  const f = rkF(F, 'palm'), k = RK_PA;
  y.yaw = k.yaw(f); y.chest = k.chest(f); y.leanL = k.leanL(f); y.lx = k.lx(f); y.dip = k.dip(f); y.head = k.head(f);
  rkBase(y);
};
CFG.moves.palm = {s: 9, a: 3, r: 16, h: 'mid', box: [250, 860, 1050, 1400], limb: 'handL'};   // PROPOSAL (the box: the palm reaches 0.83 m at 1.21 m, tests/kit.js)

// --- Feet: where each foot is (body.js asks, per act) ---
// The base guard's spot of foot s (the stance's, turned toward the fight line about the ankle and moved along it), its heel
// lifted (the rigid shoe turns on its toe tip), turned about its tip (yaw: a foot that pivots stands on its tip, so
// nothing slides), moved along the fight line by x (m, the fighter's own travel already taken out) and lifted by up (m).
const RK_AX = new THREE.Vector3();
function rkFoot(s, c, st, L, heel, yaw, x, up, toe) {
  const q = RB.t.q[1], g = RK.g, by = (s === st.front ? g.frontYaw : g.rearYaw) * RB_R;
  c.w = 1; c.flat = st[s]; c.loc = L.tp; c.auto = true;
  const A0 = RB.t.v[7].copy(L.tp).applyQuaternion(st[s].Q).negate().add(st[s].G).setY(0);   // (turned about the ankle: the leg keeps its reach)
  c.G.copy(st[s].G).sub(A0).applyAxisAngle(RB_UP, by).add(A0).addScaledVector(RB_LINE, s === st.front ? g.front : g.rear);
  c.Q.copy(st[s].Q).premultiply(q.setFromAxisAngle(RB_UP, by));
  if (heel) c.Q.premultiply(q.setFromAxisAngle(RK_AX.copy(st[s].axis).applyAxisAngle(RB_UP, by), Math.min(RB.heelMax, heel) * RB_R));
  if (yaw) c.Q.premultiply(q.setFromAxisAngle(RB_UP, yaw * RB_R));
  if (toe) {   // the toes up (a foot in the air, its heel leading): turned about its ankle, which stays
    const ank = RB.t.v[8].copy(L.tp).applyQuaternion(c.Q).negate().add(c.G);
    c.Q.premultiply(q.setFromAxisAngle(RK_AX.copy(st[s].axis).applyAxisAngle(RB_UP, by), -toe * RB_R));
    c.G.copy(L.tp).applyQuaternion(c.Q).add(ank);
  }
  if (x) c.G.addScaledVector(RB_LINE, x);
  if (up) c.G.y += up;
}
RB.feetFor.idle = (s, c, st, L) => rkFoot(s, c, st, L, 0, 0, 0, 0);   // flat and still
RB.feetFor.pr = (s, c, st, L, F) => {
  const f = rkF(F, 'pr'), k = RK_PR[s], [u0, u1, h] = k.up;
  rkFoot(s, c, st, L, rkKey(k.heel, f), 0, rkKey(k.x, f) - RK_PR.root(f), h * rkArc(f, u0, u1), rkKey(k.toe, f));
};
RB.feetFor.palm = (s, c, st, L) => rkFoot(s, c, st, L, 0, 0, 0, 0);   // both stay where they are (a heel lifts only if its leg must reach)
RB.pin.pr = 1;

// --- Arms (after the pose: style.js's guard arms are redone here for these acts) ---
const RK_V = () => new THREE.Vector3();
RB.post.push((md, p, F, S, y) => {
  const act = F.act;
  if (F.air || !RK_OWN[act]) return;
  const W = rbFK(md, p, RB.W), ix = md.index, C1 = W.p[ix.Spine01], O = W.p[ix.Spine].clone();
  const c = a => rsChest(md, W, a, RK_V()), l = a => rsVec(a, RK_V());
  const mix = (a, b, k) => a.clone().lerp(b, k), nmix = (a, b, k) => a.clone().lerp(b, k).normalize();
  const t = S.frame + 23 * F.side, g = rkGuard(t), br = act === 'idle' ? g.b : 0;
  // the guard's targets (preset K), the breath lifting both hands a little
  const G = {lp: l(RS.lead.pos).add(W.p[ix.LeftArm]).addScaledVector(RB_UP, .012 * br), lf: l(RS.lead.fing).normalize(), lpn: l(RS.lead.palm).normalize(), le: l(RS.lead.elbow).normalize(),
    rp: c(RS.rear.pos).add(C1).addScaledVector(RB_UP, .009 * br), rf: c(RS.rear.fing).normalize(), rpn: c(RS.rear.palm).normalize(), re: c(RS.rear.elbow).normalize()};
  let T = G;
  if (act === 'pr') {
    const r = rkKey(RK_PR.lead, rkF(F, 'pr'));
    T = Object.assign({}, G, {lp: G.lp.clone().addScaledVector(RB_LINE, .05 * r).addScaledVector(RB_UP, -.01 * r)});
  } else if (act === 'palm') {
    const f = rkF(F, 'palm');
    // the striking (lead) hand. The load: drawn back in front of the face, fingers up, palm forward. The drive:
    // straight out along the line at shoulder height, faster and faster, the wrist at RK.reach of the arm from the
    // shoulder on frame 10; it presses 8 mm on through the active frames; then a quick recoil and the settle.
    const sh = W.p[ix.LeftArm], arm = sh.distanceTo(W.p[ix.LeftForeArm]) + W.p[ix.LeftForeArm].distanceTo(W.p[ix.LeftHand]);
    const P = sh.clone().addScaledVector(RB_LINE, RK.reach * arm);
    const Pf = RB_UP.clone().addScaledVector(RB_LINE, .2).normalize(), Ppn = RB_LINE.clone().addScaledVector(RB_UP, -.12).normalize(), Pe = l([0, -1, .3]).normalize();
    const Lp = l([.2, .13, -.02]).add(sh), Lf = RB_UP.clone().addScaledVector(RB_LINE, .15).normalize(), Lpn = RB_LINE.clone(), Le = l([0, -1, .25]).normalize();
    let lp, lf, lpn, le;
    if (f <= 5.5) { const k = rkEase(f / 5.5); lp = mix(G.lp, Lp, k); lf = nmix(G.lf, Lf, k); lpn = nmix(G.lpn, Lpn, k); le = nmix(G.le, Le, k); }
    else if (f <= 10) { const u = (f - 5.5) / 4.5, k = rkEase(u, 'snap'), kr = rkEase(Math.min(1, u * 1.4)); lp = mix(Lp, P, k); lf = nmix(Lf, Pf, kr); lpn = nmix(Lpn, Ppn, kr); le = nmix(Le, Pe, kr); }
    else if (f <= 12) { lp = P.clone().addScaledVector(RB_LINE, .008 * Math.sin(Math.PI * (f - 10) / 2)); lf = Pf; lpn = Ppn; le = Pe; }
    else { const k = RK_PA.back(f); lp = mix(P, G.lp, k); lf = nmix(Pf, G.lf, k); lpn = nmix(Ppn, G.lpn, k); le = nmix(Pe, G.le, k); }
    // the rear hand: up by the side of the head as the palm goes out (it covers), back to the stomach in the recovery
    const cv = RK_PA.guard(f), Hp = c([-.17, .2, .12]).add(C1), Hf = RB_UP.clone().addScaledVector(RB_LINE, .1).normalize();
    const Hpn = RB_LINE.clone(), He = c([-.3, -1, -.1]).normalize();
    const Hm = c([-.1, .1, .27]).add(C1), rp = G.rp.clone().multiplyScalar((1 - cv) * (1 - cv)).addScaledVector(Hm, 2 * (1 - cv) * cv).addScaledVector(Hp, cv * cv);   // (up in front of the chest, not through it)
    T = {lp, lf, lpn, le, rp, rf: nmix(G.rf, Hf, cv), rpn: nmix(G.rpn, Hpn, cv), re: nmix(G.re, He, cv)};
  }
  rsArm(md, p, W, 'L', T.lp, T.le, T.lf, T.lpn, 1);
  rsArm(md, p, rbFK(md, p, RB.W), 'R', T.rp, T.re, T.rf, T.rpn, 1);
  if (br) mdBoneTurn(p, ix.Spine01, MD_X, -2 * br);   // the chest opens on the breath in
  if (RK.g.headYaw) mdBoneTurn(p, ix.Head, MD_Y, RK.g.headYaw);   // the eyes on the opponent
});

// --- Hands: open in the guard; in the palm the striking (lead) hand's fingers straight and together, the thumb tucked ---
RN.hooks.applied.push((it, F) => {
  if (!it.fingers || !RN.on || !RK_OWN[F.act]) return;
  const kL = .15, kR = .3, flat = F.act === 'palm' ? rkKey(RK_PA.flat, rkF(F, 'palm')) : 0;
  for (let i = 0; i < it.fingers.length; i++) {
    const n = it.fingers[i].name, left = /^Left/.test(n);
    let k = left ? kL : kR;
    if (left && flat) k += ((/Thumb/.test(n) ? .45 : 0) - k) * flat;
    it.fingers[i].quaternion.copy(MD_Q1).slerp(it.fist[i], k);
  }
});

// --- The viewer: three plays, the game's speed, a floor grid, the fighter carried along the step ---
VW_PLAYS.length = 0;
VW_PLAYS.push(['Guardia elastica', [['idle', 2 * RK.loop]]],
  ['Passo radente', [['idle', 40], ['pr', RK.len.pr], ['idle', 50]]],
  ['Palmo a scatto', [['idle', 40], ['palm', RK.len.palm], ['idle', 50]]]);
Object.assign(VW_NAMES, {idle: 'Guardia elastica', pr: 'Passo radente', palm: 'Palmo a scatto'});

// the fighter's travel along the step (mm), at a (fractional) frame of the act
function rkX(F, af) { return F.act === 'pr' ? RK.base + 1000 * F.face * RK_PR.root(Math.max(0, Math.min(RK.len.pr, af))) : F.x; }
RN.hooks.reset.push(VW => { RK.base = 0; VW.F.x = 0; VW.prevAct = null; });
RN.hooks.step.push(VW => {
  const F = VW.F;
  if (VW.step === 0 && F.af <= 1) { RK.base = 0; F.x = 0; }   // a play starts again from its first step: back to the start
  if (F.act === 'pr') F.x = rkX(F, F.af); else if (VW.prevAct === 'pr') RK.base = F.x;
  VW.prevAct = F.act;
  // the phase's name (and, for the step, the frame: the viewer counts a move's frames itself)
  const ph = F.act === 'pr' ? RK_PR.phase : F.act === 'palm' ? RK_PA.phase : null;
  if (ph) { let n = ph[0][1]; for (const [f0, nm] of ph) if (F.af >= f0) n = nm; VW.name = VW_NAMES[F.act] + ' · ' + n + (F.act === 'pr' ? '<small>fotogramma ' + F.af + ' di ' + RK.len.pr + '</small>' : ''); }
  else VW.name = VW_NAMES[F.act] || F.act;
});
RN.hooks.boot.push(VW => {
  VW.pace = 1; VW.yaw = F3_YAW; VW.spin = false; vwPress('spin', false);   // the game's speed and its side view
  VW.RK = RK; VW.RS = RS;   // (tests)
  VW_PLAYS[0][1][0][1] = 2 * RK.loop;   // (style.js lengthens the first play for its neck roll: not here)
  document.getElementById('view').addEventListener('dblclick', () => { VW.yaw = F3_YAW; });   // (after the viewer's own reset)
  // the three acts on the same held guard pose (the viewer's own breathing off: the guard breathes here, on its loop)
  const K = {c: 'a191', at: 0};
  CFG.looks.ren.clips = Object.assign({}, CFG.looks.ren.clips, {idle: K, pr: K, palm: K});
  vwAnim = () => {};   // (no old animation of these acts to compare with: N and the controller's A do nothing)
  const hint = document.getElementById('hint');
  if (hint) hint.innerHTML = 'Trascina per girare, pizzica o usa la rotella per avvicinarti, doppio tocco per tornare alla vista laterale.'
    + '<span class=kb> Tastiera: 1-3 mosse, frecce per cambiare, spazio velocità. Controller: dorsali = mossa, B velocità.</span>';
  for (const id of ['aNew', 'aOld', 'opt_smear']) { const b = document.getElementById(id); if (b) (id === 'opt_smear' ? b : b.parentNode).style.display = 'none'; }
  // a plain floor with a 25 cm grid (a foot that slides or sinks shows at once), or the arena: one button
  const T = THREE, grid = RK.grid = new T.GridHelper(6, 24, 0x2a2f38, 0x5d6573); grid.position.y = .001; VW.scene.add(grid);
  const row = document.getElementById('rnOpts'), b = document.createElement('button'); b.id = 'kitBg';
  const set = v => {
    RK.show = v; grid.visible = v === 'neutro';
    document.getElementById('stage').style.backgroundImage = v === 'neutro' ? 'none' : 'url(' + ASSETS['arena/cascata.jpg'] + ')';
    document.getElementById('stage').style.backgroundColor = v === 'neutro' ? '#8a909c' : '';
    b.innerHTML = '<span>Sfondo: ' + (v === 'neutro' ? 'neutro' : 'cascata') + '</span>';
  };
  b.addEventListener('click', () => set(RK.show === 'neutro' ? 'cascata' : 'neutro')); row.appendChild(b); set('neutro');
});
RN.hooks.applied.push((it, F) => { if (F.act === 'pr') it.root.position.x = rkX(F, F.af) / 1000; });   // (the sash's simulation: where the body is)
RN.hooks.draw.push((VW, dt) => {
  const it = VW.it, D = RN_D.F || VW.F, th = VW.yaw - F3_YAW, x = rkX(D, D.af) / 1000;
  const dir = new THREE.Vector3(Math.cos(th), 0, -Math.sin(th));
  it.root.position.copy(dir).multiplyScalar(x).setY(D.y / 1000);
  VW.shadow.position.set(it.root.position.x, .004, it.root.position.z);
  const aim = VW.playing === 1 ? RK.d / 2 : 0, e = Math.min(1, dt * .006);   // the step's play frames both ends of the step
  VW.aimX += (aim * dir.x - VW.aimX) * e;
});
