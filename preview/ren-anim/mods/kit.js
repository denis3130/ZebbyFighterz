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
//   idle  "Guardia elastica": the sheets' guard (3/4 toward the camera, a wide low stance, the rear hand on the
//         stomach) with Denis's change (12/11): the lead (left) arm straight out toward the opponent, the hand a closed
//         fist, as if to keep him away; the rear (right) hand half closed. A loop of 144 frames (2.4 s): two breaths
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
// and faster, 1.5 times the mean speed at its end: a strike), 'whip' (the same, .75 times at its end), 'lin', default
// smoothstep (from rest to rest).
// rkMono: [frame, value] through a monotone cubic (the speed carries through a key, no overshoot; at rest at both
// ends): the body's tracks, so a step or a drive never stops on a key.
function rkEase(u, e) {
  u = Math.max(0, Math.min(1, u));
  if (e === 'snap') return u * u * (3 - u) / 2;
  if (e === 'whip') return .5 * u * u * (3 - u) / 2 + .5 * u * u * (3 - 2 * u);   // (a strike that arrives a little slower: a kick)
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

// --- The guard ("Guardia elastica"): style.js's preset K. The lead arm straight out from the shoulder along the fight
// line, a little down (reach: share of the arm's length, dir: [forward, up, side]), the fist's knuckles forward and its
// palm in (toward his right); the rear hand half closed on the stomach, fingers across, palm in. ---
RS.presets.K = {curl: .15, armW: 1, flow: {period: 150, lead: 0, rear: 0},
  lead: {reach: .975, dir: [1, -.12, .03], fing: [1, -.1, 0], palm: [0, 0, -1], elbow: [0, -1, .2]},
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
  lead: [[0, 0], [8, 0], [13, 1], [20, .3], [26, 0]],   // the lead fist dipping a little with the push
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
  const sL = W.p[ix.LeftArm], armL = sL.distanceTo(W.p[ix.LeftForeArm]) + W.p[ix.LeftForeArm].distanceTo(W.p[ix.LeftHand]);
  const G = {lp: l(RS.lead.dir).normalize().multiplyScalar(RS.lead.reach * armL).add(sL).addScaledVector(RB_UP, .012 * br), lf: l(RS.lead.fing).normalize(), lpn: l(RS.lead.palm).normalize(), le: l(RS.lead.elbow).normalize(),
    rp: c(RS.rear.pos).add(C1).addScaledVector(RB_UP, .009 * br), rf: c(RS.rear.fing).normalize(), rpn: c(RS.rear.palm).normalize(), re: c(RS.rear.elbow).normalize()};
  let T = G;
  const mv = RK_MOVES[act];
  if (mv) {
    const sR = W.p[ix.RightArm], armR = sR.distanceTo(W.p[ix.RightForeArm]) + W.p[ix.RightForeArm].distanceTo(W.p[ix.RightHand]);
    const A = {W, ix, O, C1, c, l, sL, sR, armL, armR, G: {L: {p: G.lp, f: G.lf, n: G.lpn, e: G.le}, R: {p: G.rp, f: G.rf, n: G.rpn, e: G.re}}};
    const R = rkMoveArms(mv, A, rkF(F, act));
    T = {lp: R.L.p, lf: R.L.f, lpn: R.L.n, le: R.L.e, rp: R.R.p, rf: R.R.f, rpn: R.R.n, re: R.R.e};
  } else if (act === 'pr') {
    const r = rkKey(RK_PR.lead, rkF(F, 'pr'));
    T = Object.assign({}, G, {lp: G.lp.clone().addScaledVector(RB_UP, -.015 * r)});   // (the arm already straight: the fist dips a little with the push)
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

// --- Hands: the lead a closed fist and the rear half closed (Denis, 12/11). In the palm the lead fist snaps open as it
// is drawn back: the thumb first, out of the way, then the fingers, index to little finger, each from its knuckle out
// (the knuckle a little past straight, then back: the snap); on the impact the fingers press straight; in the recovery
// the hand closes the other way round, little finger first, each from its tip, the thumb last over them. ---
const RK_HAND = {
  open: {at: 2.2, len: 2.4, finger: .25, joint: .45, snap: .16},   // frames: start, length, delay per finger / per joint; snap: the knuckle past straight
  press: {at: 9.5, len: 3, k: .07},                             // on the impact the knuckles press a little past straight
  close: {at: 12.6, len: 4.2, finger: .45, joint: .35},        // (closed before the hand turns back to point forward)
  thumb: {open: [1.2, 2.6], close: [16.5, 3.5], lie: [.95, .3], tip: .15},   // when it moves (start, length); open, it lies along the
                                                                // index (lie: shares along the hand and toward the index), its tip a little bent
  together: .7,                                                 // the open fingers brought toward the middle one (share of their spread)
  fist: 1, rear: .55,                                           // the guard's lead fist and the half closed rear hand
};
RK.hand = RK_HAND;   // (tests)
const RK_FINGER = {Index: 0, Middle: 1, Ring: 2, Pinky: 3};
const rkBump = (u) => u <= 0 || u >= 1 ? 0 : Math.sin(Math.PI * u) ** 2;
// How closed finger bone n ('LeftHandIndex2') of a hand that snaps open and closes again is at frame f: 1 fist .. 0
// straight (< 0 past it); for the thumb, 1 fist .. 0 lying along the index. o: when (frames) the fingers start to open,
// press (the impact, or null), start to close, the thumb opens and closes, and where the closing takes over (split:
// every finger open and the press over by then; thumbSplit the same for the thumb). The shape: RK_HAND.
const RK_SNAP = {palm: {open: 2.2, press: 9.5, close: 12.6, thumbOpen: 1.2, thumbClose: 16.5, split: 12.5, thumbSplit: 12}};
function rkSnapK(n, f, o) {
  const m = /(Thumb|Index|Middle|Ring|Pinky)(\d)/.exec(n), h = RK_HAND, joint = +m[2] - 1;
  if (m[1] === 'Thumb') {
    const t = h.thumb;
    return f < o.thumbSplit ? 1 - rkEase((f - o.thumbOpen) / t.open[1]) : rkEase((f - o.thumbClose) / t.close[1]);
  }
  const j = RK_FINGER[m[1]];
  if (f < o.split) {
    const op = h.open, u = (f - o.open - op.finger * j - op.joint * joint) / op.len;
    let k = 1 - rkEase(u);
    if (!joint) k -= op.snap * rkBump((u - .55) / .9) + (o.press === null ? 0 : h.press.k * rkBump((f - o.press) / h.press.len));
    return k;
  }
  const c = h.close;
  return rkEase((f - o.close - c.finger * (3 - j) - c.joint * (2 - joint)) / c.len);
}
const rkFingerK = (n, f) => rkSnapK(n, f, RK_SNAP.palm);   // (the palm's lead hand)
// An open thumb: its first bone turned (from the rest pose, where it points half out of the palm) to lie along the
// side of the index finger, in the palm's plane. Per hand ('Left' / 'Right'), once per model, from the hand's bones.
function rkThumbLie(it, h) {
  const key = 'rkThumb' + h;
  if (it[key]) return it[key];
  const T = THREE, b = n => it.fingers.find(x => x.name === h + 'Hand' + n), i1 = b('Index1'), p1 = b('Pinky1'), m1 = b('Middle1'), t2 = b('Thumb2');
  const along = m1.position.clone().normalize(), side = i1.position.clone().sub(p1.position); side.addScaledVector(along, -side.dot(along)).normalize();
  const want = along.multiplyScalar(RK_HAND.thumb.lie[0]).addScaledVector(side, RK_HAND.thumb.lie[1]).normalize();
  return it[key] = new T.Quaternion().setFromUnitVectors(t2.position.clone().normalize(), want);
}
// Open fingers together (a palm strike, not a spread hand): each finger's first bone turned toward the middle finger's
// direction by RK_HAND.together of the angle between them (in the hand's frame; their rest pose spreads them). Once per
// model; null for the bones it does not turn.
function rkFingerTogether(it, n) {
  if (!it.rkTogether) {
    const b = x => it.fingers.find(y => y.name === x);
    it.rkTogether = {};
    for (const h of ['Left', 'Right']) {
      const mid = b(h + 'HandMiddle2').position.clone().normalize();
      for (const f of ['Index', 'Ring', 'Pinky']) {
        const d = b(h + 'Hand' + f + '2').position.clone().normalize(), to = d.clone().lerp(mid, RK_HAND.together).normalize();
        it.rkTogether[h + 'Hand' + f + '1'] = new THREE.Quaternion().setFromUnitVectors(d, to);
      }
    }
  }
  return it.rkTogether[n] || null;
}
// Finger bone i of it at closedness k: its open end the snapping hand's (fingers together, thumb along the index) when
// that hand opens in this act, else the rest pose's.
function rkSetFinger(it, i, k, snap) {
  const b = it.fingers[i], n = b.name, h = /^Left/.test(n) ? 'Left' : 'Right', tog = snap && rkFingerTogether(it, n);
  if (tog) b.quaternion.copy(tog).slerp(it.fist[i], k);
  else if (snap && /Thumb1/.test(n)) b.quaternion.copy(rkThumbLie(it, h)).slerp(it.fist[i], k);
  else if (snap && /Thumb/.test(n)) b.quaternion.copy(MD_Q1).slerp(it.fist[i], RK_HAND.thumb.tip + (1 - RK_HAND.thumb.tip) * k);
  else b.quaternion.copy(MD_Q1).slerp(it.fist[i], k);
}
RN.hooks.applied.push((it, F) => {
  if (!it.fingers || !RN.on || !RK_OWN[F.act]) return;
  const mv = RK_MOVES[F.act], palm = F.act === 'palm', f = RK.len[F.act] ? rkF(F, F.act) : 0;
  for (let i = 0; i < it.fingers.length; i++) {
    const n = it.fingers[i].name, left = /^Left/.test(n), h = left ? 'L' : 'R';
    let k = left ? RK_HAND.fist : RK_HAND.rear, snap = false;
    if (palm && left) { k = rkFingerK(n, f); snap = true; }
    else if (mv && mv.hands && mv.hands[h]) { const r = mv.hands[h](n, f); if (typeof r === 'number') k = r; else { k = r.k; snap = true; } }
    rkSetFinger(it, i, k, snap);
  }
});


// ===== Stage 2 (12/11/2026): more of the sheets' moves, each a table read by the same few functions below. =====
// A move: len (frames); name; phase [[from, name]]; cfg (CFG.moves entry when it hits: s/a/r, box, limb or bone);
// root (f -> m the fighter travels along the line, optional); body: tracks of the style on top of the base guard (yaw,
// chest, leanL, lx, dip, head); feet.L / feet.R: x (m along the line, in the world), up (m) and bumps ([[from, to,
// height]]: a step's lift), heel and yaw (deg, the shoe turning on its tip), toe (deg, about the ankle, < 0 toes
// down), free (a foot in the air: no automatic heel); arms.L / arms.R: keys [[frame, pose, ease]] between poses (the
// guard's, 'guard', or the move's poses: (A, f) -> {p: wrist, f: fingers' way, n: palm's way, e: elbow hint}; a key's
// fourth entry: a pose the wrist curves toward on the way, a Bezier control point); hands.L
// / hands.R: (bone name, f) -> closedness, or {k} for a hand that snaps open (fingers together, thumb along the index).
// A track is a number, keys ([[frame, value, ease]]: rkKey) or a function of the frame (rkMono).
const RK_MOVES = {};
const rkTrack = (t, f) => t === undefined ? 0 : typeof t === 'function' ? t(f) : Array.isArray(t) ? rkKey(t, f) : t;
function rkAddMove(id, m) {
  RK_MOVES[id] = m; RK_OWN[id] = 1; RK.len[id] = m.len; RB.pin[id] = 1; VW_NAMES[id] = m.name;
  if (m.cfg) CFG.moves[id] = m.cfg;
  RB.styleFor[id] = (y, F) => {
    const f = rkF(F, id), b = m.body || {};
    y.yaw = rkTrack(b.yaw, f); y.chest = rkTrack(b.chest, f); y.leanL = rkTrack(b.leanL, f); y.lx = rkTrack(b.lx, f);
    y.dip = rkTrack(b.dip, f); y.head = rkTrack(b.head, f);
    rkBase(y);
  };
  RB.feetFor[id] = (s, c, st, L, F) => {
    const f = rkF(F, id), k = (m.feet && m.feet[s]) || {}, root = m.root ? m.root(f) : 0;
    let up = rkTrack(k.up, f);
    if (k.bumps) for (const [a, b, h] of k.bumps) up += h * rkArc(f, a, b);
    rkFoot(s, c, st, L, rkTrack(k.heel, f), rkTrack(k.yaw, f), rkTrack(k.x, f) - root, up, rkTrack(k.toe, f));
    if (k.free) c.auto = false;
  };
}
// The arm targets of move m at frame f: each arm between the poses of its keys.
function rkMoveArms(m, A, f) {
  const T = {};
  for (const s of ['L', 'R']) {
    const keys = (m.arms && m.arms[s]) || [[0, 'guard']], pose = (name) => name === 'guard' ? A.G[s] : ((m.poses && m.poses[name]) || RK_POSE[name])(A, f, s);
    let i = 0; while (i + 1 < keys.length && f > keys[i + 1][0]) i++;
    const a = pose(keys[i][1]);
    let r = a;
    if (i + 1 < keys.length && f > keys[i][0]) {
      const b = pose(keys[i + 1][1]), u = rkEase((f - keys[i][0]) / (keys[i + 1][0] - keys[i][0]), keys[i + 1][2]), via = keys[i + 1][3];
      const p = via ? a.p.clone().multiplyScalar((1 - u) * (1 - u)).addScaledVector(pose(via).p, 2 * u * (1 - u)).addScaledVector(b.p, u * u) : a.p.clone().lerp(b.p, u);
      r = {p, f: a.f.clone().lerp(b.f, u).normalize(), n: a.n.clone().lerp(b.n, u).normalize(), e: a.e.clone().lerp(b.e, u).normalize()};
    }
    T[s] = r;
  }
  return T;
}
const rkSnap = (o) => (n, f) => ({k: rkSnapK(n, f, o)});   // a hand that snaps open at o's times
// Poses several moves share (a move's own poses come first).
const RK_POSE = {
  rChin: A => ({p: A.c([-.04, .26, .2]).add(A.C1), f: A.c([1, .4, .2]).normalize(), n: A.c([0, 0, -1]), e: A.c([-.4, -1, -.2]).normalize()}),
  rChest: A => ({p: A.c([.02, .02, .22]).add(A.C1), f: A.c([1, .3, 0]).normalize(), n: A.c([0, 0, -1]), e: A.c([-.5, -1, -.3]).normalize()}),
  rHead: A => ({p: A.c([-.17, .2, .12]).add(A.C1), f: RB_UP.clone().addScaledVector(RB_LINE, .1).normalize(), n: RB_LINE.clone(), e: A.c([-.3, -1, -.1]).normalize()}),
  rFront: A => ({p: A.c([-.06, .12, .32]).add(A.C1)}),   // (in front of the chest: a rear hand's way up and down)
};

// --- Gomito spezzaguardia: the lead elbow, as the sheet has it ---
// Entry: the rear foot slides in 18 cm, the lead fist comes up by the face (the elbow low), the rear fist to the chest.
// Drive: the hips square up a little, then turn the lead side forward and push 13 cm; the lead elbow sweeps up and
// forward at shoulder height, the forearm flat across the chest, the fist by the right collarbone; the rear hand opens
// up by the head. Recovery: the rear foot back out, the arm back to the guard's straight fist.
rkAddMove('elbow', {
  len: 34, name: 'Gomito spezzaguardia',
  phase: [[0, 'Entrata'], [9, 'Spinta'], [14, 'Impatto'], [17, 'Recupero']],
  cfg: {s: 13, a: 3, r: 18, h: 'mid', box: [150, 700, 1050, 1450], limb: 'elbowL', bone: 'LeftForeArm'},   // PROPOSAL
  body: {
    yaw: rkMono([[0, 0], [9, 8], [14, -18], [17, -18], [23, -6], [34, 0]]),
    chest: rkMono([[0, 0], [9, 12], [15, -24], [17, -24], [24, -8], [34, 0]]),
    leanL: rkMono([[0, 0], [9, 3], [14, 9], [17, 9], [24, 3], [34, 0]]),
    lx: rkMono([[0, 0], [9, .06], [14, .13], [17, .13], [26, .05], [34, 0]]),
    dip: rkMono([[0, .004], [9, .03], [14, .04], [17, .04], [25, .012], [34, .004]]),
    head: rkMono([[0, 0], [9, 3], [14, -2], [34, 0]]),
  },
  feet: {R: {x: [[0, 0], [3.6, 0], [8.6, .18], [23.2, .18], [27.8, 0]], bumps: [[2.4, 9.8, .02], [22, 29.4, .02]], heel: [[0, 0], [3, 0], [6, 6], [9.2, 0], [14, 8], [17, 8], [22, 0]]}},
  arms: {L: [[0, 'guard'], [9, 'eUp'], [14, 'eHit', 'snap'], [17, 'eHit'], [25, 'eBack'], [34, 'guard']],
    R: [[0, 'guard'], [8, 'rChest'], [13, 'rHead', undefined, 'rFront'], [18, 'rHead'], [30, 'guard', undefined, 'rFront']]},
  poses: {
    rFront: A => ({p: A.c([-.06, .12, .32]).add(A.C1)}),   // (in front of the chest: the rear hand's way up and down)
    eUp: A => ({p: A.l([.1, .18, .03]).add(A.sL), f: A.l([.15, 1, 0]).normalize(), n: A.l([-.3, 0, -1]).normalize(), e: A.l([.2, -1, .3]).normalize()}),
    eHit: A => ({p: A.l([.05, .05, -.24]).add(A.sL), f: A.l([-.2, 0, -1]).normalize(), n: A.l([0, -1, 0]), e: A.l([1, .3, 0]).normalize()}),
    eBack: A => ({p: A.l([.3, -.05, -.02]).add(A.sL), f: A.l([1, 0, 0]), n: A.l([0, 0, -1]), e: A.l([0, -1, .3]).normalize()}),
    rChest: A => ({p: A.c([.02, .02, .22]).add(A.C1), f: A.c([1, .3, 0]).normalize(), n: A.c([0, 0, -1]), e: A.c([-.5, -1, -.3]).normalize()}),
    rHead: A => ({p: A.c([-.17, .2, .12]).add(A.C1), f: RB_UP.clone().addScaledVector(RB_LINE, .1).normalize(), n: RB_LINE.clone(), e: A.c([-.3, -1, -.1]).normalize()}),
  },
  hands: {R: (n, f) => rkKey([[0, RK_HAND.rear], [6, 1], [10, 1], [13, .15], [18, .15], [28, RK_HAND.rear]], f)},
});

// --- Deviazione circolare: absorb, a circle of the lead forearm that turns the attack aside, a palm in answer ---
// Absorb: the weight back and down, the lead hand up in front of the forehead (open), the rear fist to the chin.
// Deflect: the lead hand circles down, forward and up (the forearm sweeps the attack out of the line). Answer: the
// rear foot slides in, the hips push and the lead palm goes out straight; then the front foot steps on and the guard.
rkAddMove('dev', {
  len: 42, name: 'Deviazione circolare',
  phase: [[0, 'Assorbimento'], [7, 'Deviazione'], [15, 'Risposta'], [25, 'Recupero']],
  cfg: {s: 21, a: 3, r: 18, h: 'mid', box: [250, 900, 1050, 1400], limb: 'handL'},   // PROPOSAL (it turns attacks aside on frames 7-14)
  root: rkMono([[0, 0], [15, 0], [24, .15], [42, .15]]),
  body: {
    yaw: rkMono([[0, 0], [6, 4], [11, -6], [15, -2], [21, -16], [25, -16], [32, -5], [42, 0]]),
    chest: rkMono([[0, 0], [6, 6], [11, -10], [15, -4], [22, -20], [25, -20], [32, -6], [42, 0]]),
    leanL: rkMono([[0, 0], [6, -5], [11, -2], [15, 0], [21, 7], [25, 7], [32, 2], [42, 0]]),
    lx: rkMono([[0, 0], [6, -.07], [11, -.05], [15, -.03], [21, .08], [25, .08], [33, .02], [42, 0]]),
    dip: rkMono([[0, .004], [6, .045], [11, .035], [15, .03], [25, .03], [33, .012], [42, .004]]),
    head: rkMono([[0, 0], [6, 4], [11, 1], [21, -1], [42, 0]]),
  },
  feet: {R: {x: [[0, 0], [15, 0], [21, .15]], bumps: [[14.4, 21.6, .025]], heel: [[0, 0], [15, 0], [18, 8], [21, 0]]},
    L: {x: [[0, 0], [25, 0], [31, .15]], bumps: [[24.4, 31.6, .03]]}},
  arms: {L: [[0, 'guard'], [6, 'dCover'], [7, 'dCover'], [15, 'dCircle', 'lin'], [21, 'dPush', 'snap'], [25, 'dPush'], [34, 'guard']],
    R: [[0, 'guard'], [6, 'rChin'], [26, 'rChin'], [36, 'guard']]},
  poses: {
    dCover: A => ({p: A.l([.1, .2, -.06]).add(A.sL), f: RB_UP.clone(), n: RB_LINE.clone(), e: A.l([.15, -1, .25]).normalize()}),
    // (the circle: the wrist from the cover around a centre in front of the face, down, forward and up)
    dCircle: (A, f) => {
      const u = Math.max(0, Math.min(1, (f - 7) / 8)), th = (125 + 265 * rkEase(u)) * RB_R, R = .14;
      const C = A.l([.24, .06, -.02]).add(A.sL), dir = A.l([Math.cos(th), Math.sin(th), 0]);
      return {p: C.addScaledVector(dir, R * (1 + .15 * u)), f: RB_UP.clone().addScaledVector(RB_LINE, .4 * u).normalize(), n: dir.clone().addScaledVector(RB_LINE, .5).normalize(), e: A.l([.1, -1, .3]).normalize()};
    },
    dPush: A => ({p: A.sL.clone().addScaledVector(RB_LINE, RK.reach * A.armL), f: RB_UP.clone().addScaledVector(RB_LINE, .2).normalize(), n: RB_LINE.clone().addScaledVector(RB_UP, -.12).normalize(), e: A.l([0, -1, .3]).normalize()}),
    rChin: A => ({p: A.c([-.04, .26, .2]).add(A.C1), f: A.c([1, .4, .2]).normalize(), n: A.c([0, 0, -1]), e: A.c([-.4, -1, -.2]).normalize()}),
  },
  hands: {L: rkSnap({open: 1, press: 21, close: 26.5, thumbOpen: .4, thumbClose: 30.5, split: 24.5, thumbSplit: 24}),
    R: (n, f) => rkKey([[0, RK_HAND.rear], [6, .9], [26, .9], [34, RK_HAND.rear]], f)},
});

// --- Calcio a frusta: the lead leg, the standing foot turning with the hips ---
// Load: the rear foot steps in under the body (30 cm), the weight goes onto it, the lead knee comes up (the foot under
// it, toes down). Pivot and whip: the standing foot turns on its tip as the hips turn over (never a body turning on a
// planted foot), the body leans away and the shin snaps out at hip height. Back: the knee folds back in, the foot lands
// where it was, the rear foot steps back out, the guard.
rkAddMove('kick', {
  len: 34, name: 'Calcio a frusta',
  phase: [[0, 'Caricamento'], [9, 'Pivot'], [14, 'Impatto'], [17, 'Rientro'], [26, 'Guardia']],
  cfg: {s: 13, a: 3, r: 18, h: 'mid', box: [300, 1000, 650, 1150], limb: 'footL'},   // PROPOSAL
  body: {
    yaw: rkMono([[0, 0], [6, -6], [10, -14], [14, -40], [17, -40], [22, -18], [28, 0]]),
    chest: rkMono([[0, 0], [6, -4], [14, -12], [17, -12], [24, -2], [30, 0]]),
    leanL: rkMono([[0, 0], [6, -3], [10, -6], [14, -18], [17, -18], [22, -7], [30, 0]]),
    lx: rkMono([[0, 0], [5, -.14], [14, -.1], [17, -.1], [22, -.12], [27, .02], [33, 0]]),
    dip: rkMono([[0, .004], [5, -.025], [14, -.04], [17, -.04], [22, -.03], [26, .03], [30, .012], [34, .004]]),
    head: rkMono([[0, 0], [14, -4], [17, -4], [28, 0]]),
  },
  feet: {
    R: {x: [[0, 0], [.6, 0], [4, .3], [27.8, .3], [32, 0]], bumps: [[0, 5, .025], [27, 33, .02]],
      heel: [[0, 0], [6, 0], [9, 10], [17, 12], [22, 6], [25, 0]], yaw: [[0, 0], [7, 0], [12, -65], [18, -65], [22.5, -6], [23.5, 0]]},   // (turned back while still on its tip)
    L: {free: true, heel: [[0, 0], [3.5, 0], [5, 16], [25, 16], [27, 0]],   // (it lands on its toes, then the heel comes down)
      x: [[0, 0], [5, 0], [9.5, -.2], [14, .36, 'whip'], [16, .36], [21, -.2], [24.8, 0]],
      up: [[0, 0], [5, 0], [9.5, .42], [14, .77, 'whip'], [16, .77], [21, .42], [25, 0]],
      toe: [[0, 0], [5, 0], [9.5, -30], [14, -60], [16, -60], [21, -30], [24.5, 0]]},
  },
  arms: {L: [[0, 'guard'], [6, 'kLow'], [18, 'kLow'], [28, 'guard']], R: [[0, 'guard'], [6, 'rChin'], [22, 'rChin'], [30, 'guard']]},
  poses: {
    kLow: A => ({p: A.l([.36, -.14, .04]).add(A.sL), f: A.l([1, -.3, 0]).normalize(), n: A.l([0, 0, -1]), e: A.l([0, -1, .2]).normalize()}),
    rChin: A => ({p: A.c([-.04, .26, .2]).add(A.C1), f: A.c([1, .4, .2]).normalize(), n: A.c([0, 0, -1]), e: A.c([-.4, -1, -.2]).normalize()}),
  },
  hands: {R: (n, f) => rkKey([[0, RK_HAND.rear], [6, .95], [22, .95], [30, RK_HAND.rear]], f)},
});

// --- Passo spezzato (the signature): half a step back to draw the attack, down under the opponent's line, a low burst
// forward, in with the shoulder, a double palm ---
// The rear foot steps back, the body leans away (the feint); the front foot comes back to it and he coils low on the
// balls of his feet, hands up by the face (the compression); the rear leg drives him forward low, the front foot
// lands far ahead (the burst), the rear foot follows; the lead shoulder goes in first, fists tight at the chest (the
// entry); the hips square and both palms go out (the double palm); then he settles and comes back to the guard, 0.30 m
// further on than he started.
rkAddMove('ps', {
  len: 74, name: 'Passo spezzato',
  phase: [[0, 'Finta indietro'], [10, 'Compressione'], [20, 'Scatto basso'], [30, 'Entrata di spalla'], [38, 'Doppio palmo'], [48, 'Assestamento'], [60, 'Ritorno in guardia']],
  cfg: {s: 43, a: 3, r: 28, h: 'mid', box: [250, 950, 950, 1400], limb: 'handL'},   // PROPOSAL
  root: rkMono([[0, 0], [8, -.1], [20, -.22], [26, .06], [33, .3], [74, .3]]),
  body: {
    yaw: rkMono([[0, 0], [10, 6], [20, 4], [26, -6], [33, -24], [38, -24], [43, 4], [47, 4], [58, 0], [74, 0]]),
    chest: rkMono([[0, 0], [10, 8], [20, 6], [26, -4], [33, -18], [38, -18], [43, 6], [47, 6], [60, 0], [74, 0]]),
    leanL: rkMono([[0, 0], [10, -6], [20, 14], [26, 24], [33, 10], [38, 8], [47, 8], [60, 2], [74, 0]]),
    lx: rkMono([[0, 0], [10, -.04], [20, 0], [26, .04], [33, .02], [38, .04], [43, .1], [47, .1], [60, .02], [74, 0]]),
    dip: rkMono([[0, .004], [10, .025], [20, .16], [26, .15], [33, .07], [38, .05], [43, .045], [49, .045], [60, .012], [74, .004]]),
    head: rkMono([[0, 0], [10, 3], [20, -6], [26, -10], [33, -2], [43, -2], [60, 0], [74, 0]]),
  },
  feet: {
    R: {x: [[0, 0], [1.2, 0], [7.4, -.15], [26.8, -.15], [32.2, .3]], bumps: [[0, 8.4, .03], [26, 33, .035]],
      heel: [[0, 0], [12, 0], [18, 15], [24, 25], [26.8, 25], [32, 0]]},
    L: {x: [[0, 0], [10.8, 0], [16.2, -.45], [20.8, -.45], [25.4, .3]], bumps: [[10, 17, .03], [20, 26.2, .05]],
      toe: [[0, 0], [20.5, 0], [23, 15], [25.4, 0]]},
  },
  arms: {
    L: [[0, 'guard'], [9, 'pFeint'], [16, 'pCoverL'], [20, 'pCoverL'], [26, 'pReachL'], [31, 'pTuckL'], [36, 'pTuckL'], [43, 'pPalmL', 'snap'], [46, 'pPalmL'], [56, 'pBackL'], [72, 'guard']],
    R: [[0, 'guard'], [14, 'rChin', undefined, 'rFront'], [26, 'rChest'], [31, 'rChin'], [36, 'rChin'], [43, 'pPalmR', 'snap'], [46, 'pPalmR'], [56, 'pBackR'], [72, 'guard']],
  },
  poses: {
    pFeint: A => ({p: A.l([.25, .02, .03]).add(A.sL), f: A.l([1, 0, 0]), n: A.l([0, 0, -1]), e: A.l([0, -1, .25]).normalize()}),
    pCoverL: A => ({p: A.l([.18, .2, -.04]).add(A.sL), f: RB_UP.clone(), n: RB_LINE.clone(), e: A.l([.15, -1, .25]).normalize()}),
    pReachL: A => ({p: A.l([.36, -.1, .02]).add(A.sL), f: A.l([1, .3, 0]).normalize(), n: A.l([.5, -1, 0]).normalize(), e: A.l([0, -1, .3]).normalize()}),
    pTuckL: A => ({p: A.l([.12, .08, -.14]).add(A.sL), f: RB_UP.clone(), n: A.l([0, 0, -1]), e: A.l([.3, -1, .1]).normalize()}),
    pPalmL: A => ({p: A.sL.clone().addScaledVector(RB_LINE, RK.reach * A.armL).addScaledVector(RB_UP, .02), f: RB_UP.clone().addScaledVector(RB_LINE, .2).normalize(), n: RB_LINE.clone().addScaledVector(RB_UP, -.12).normalize(), e: A.l([0, -1, .3]).normalize()}),
    pPalmR: A => ({p: A.sR.clone().addScaledVector(RB_LINE, RK.reach * A.armR).addScaledVector(RB_UP, -.08), f: RB_UP.clone().addScaledVector(RB_LINE, .2).normalize(), n: RB_LINE.clone().addScaledVector(RB_UP, -.12).normalize(), e: A.c([-.2, -1, -.1]).normalize()}),
    pBackL: A => ({p: A.l([.25, 0, .02]).add(A.sL), f: A.l([1, .3, 0]).normalize(), n: A.l([0, 0, -1]), e: A.l([0, -1, .25]).normalize()}),
    pBackR: A => ({p: A.c([.02, .02, .25]).add(A.C1), f: A.c([1, .3, 0]).normalize(), n: A.c([0, 0, -1]), e: A.c([-.5, -1, -.3]).normalize()}),
  },
  hands: {
    L: rkSnap({open: 10, press: 44, close: 50, thumbOpen: 9.4, thumbClose: 54, split: 47.5, thumbSplit: 47}),
    R: (n, f) => f < 36 ? rkKey([[0, RK_HAND.rear], [12, 1]], f) : f < 60 ? {k: rkSnapK(n, f, {open: 37, press: 44, close: 50, thumbOpen: 36.4, thumbClose: 54, split: 47.5, thumbSplit: 47})} : rkKey([[60, 1], [68, RK_HAND.rear]], f),
  },
});

// --- The viewer: the plays, the game's speed, a floor grid, the fighter carried along his steps ---
VW_PLAYS.length = 0;
VW_PLAYS.push(['Guardia elastica', [['idle', 2 * RK.loop]]],
  ['Passo radente', [['idle', 40], ['pr', RK.len.pr], ['idle', 50]]],
  ['Palmo a scatto', [['idle', 40], ['palm', RK.len.palm], ['idle', 50]]],
  ['Gomito spezzaguardia', [['idle', 40], ['elbow', RK.len.elbow], ['idle', 50]]],
  ['Deviazione circolare', [['idle', 40], ['dev', RK.len.dev], ['idle', 50]]],
  ['Calcio a frusta', [['idle', 40], ['kick', RK.len.kick], ['idle', 50]]],
  ['Passo spezzato', [['idle', 40], ['ps', RK.len.ps], ['idle', 50]]]);
Object.assign(VW_NAMES, {idle: 'Guardia elastica', pr: 'Passo radente', palm: 'Palmo a scatto'});

// the fighter's travel along the step (mm), at a (fractional) frame of the act
const rkRoot = act => act === 'pr' ? RK_PR.root : RK_MOVES[act] && RK_MOVES[act].root;
function rkX(F, af) { const r = rkRoot(F.act); return r ? RK.base + 1000 * F.face * r(Math.max(0, Math.min(RK.len[F.act], af))) : F.x; }
RN.hooks.reset.push(VW => { RK.base = 0; VW.F.x = 0; VW.prevAct = null; });
RN.hooks.step.push(VW => {
  const F = VW.F;
  if (VW.step === 0 && F.af <= 1) { RK.base = 0; F.x = 0; }   // a play starts again from its first step: back to the start
  if (rkRoot(F.act)) F.x = rkX(F, F.af); else if (rkRoot(VW.prevAct)) RK.base = F.x;
  VW.prevAct = F.act;
  // the phase's name (and, for a move that does not hit, the frame: the viewer counts an attack's frames itself)
  const mv = RK_MOVES[F.act], ph = F.act === 'pr' ? RK_PR.phase : F.act === 'palm' ? RK_PA.phase : mv ? mv.phase : null;
  if (ph) { let n = ph[0][1]; for (const [f0, nm] of ph) if (F.af >= f0) n = nm; VW.name = VW_NAMES[F.act] + ' · ' + n + (CFG.moves[F.act] ? '' : '<small>fotogramma ' + F.af + ' di ' + RK.len[F.act] + '</small>'); }
  else VW.name = VW_NAMES[F.act] || F.act;
});
RN.hooks.boot.push(VW => {
  VW.pace = 1; VW.yaw = F3_YAW; VW.spin = false; vwPress('spin', false);   // the game's speed and its side view
  VW.RK = RK; VW.RS = RS;   // (tests)
  VW_PLAYS[0][1][0][1] = 2 * RK.loop;   // (style.js lengthens the first play for its neck roll: not here)
  document.getElementById('view').addEventListener('dblclick', () => { VW.yaw = F3_YAW; });   // (after the viewer's own reset)
  // the three acts on the same held guard pose (the viewer's own breathing off: the guard breathes here, on its loop)
  const K = {c: 'a191', at: 0};
  CFG.looks.ren.clips = Object.assign({}, CFG.looks.ren.clips, ...Object.keys(RK_OWN).map(a => ({[a]: K})));
  vwAnim = () => {};   // (no old animation of these acts to compare with: N and the controller's A do nothing)
  const hint = document.getElementById('hint');
  if (hint) hint.innerHTML = 'Trascina per girare, pizzica o usa la rotella per avvicinarti, doppio tocco per tornare alla vista laterale.'
    + '<span class=kb> Tastiera: 1-' + VW_PLAYS.length + ' mosse, frecce per cambiare, spazio velocità. Controller: dorsali = mossa, B velocità.</span>';
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
RN.hooks.applied.push((it, F) => { if (rkRoot(F.act)) it.root.position.x = rkX(F, F.af) / 1000; });   // (the sash's simulation: where the body is)
RN.hooks.draw.push((VW, dt) => {
  const it = VW.it, D = RN_D.F || VW.F, th = VW.yaw - F3_YAW, x = rkX(D, D.af) / 1000;
  const dir = new THREE.Vector3(Math.cos(th), 0, -Math.sin(th));
  it.root.position.copy(dir).multiplyScalar(x).setY(D.y / 1000);
  VW.shadow.position.set(it.root.position.x, .004, it.root.position.z);
  const act = (VW.plan.find(s => rkRoot(s[0])) || [])[0], r = act && rkRoot(act), e = Math.min(1, dt * .006);
  const aim = r ? r(RK.len[act]) / 2 : 0;   // a play that travels frames both ends of its travel
  VW.aimX += (aim * dir.x - VW.aimX) * e;
});
