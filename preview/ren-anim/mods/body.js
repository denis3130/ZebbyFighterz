// --- body.js: Ren's body. The style of every act and the solver that keeps the body physically right. ---
// Graphics only and pure: RN.pure(md, F, S) is a function of the fighter's act and frame (fractional frames are valid).
// Model space (metres): +y up, +z forward (the way the fighter faces), +x the fighter's left.
//
// 1. The clip's pose (mdPoseOf), with the move's clip time warped: a slow coil, a whip into the hit, a lock, a settle.
// 2. Style on the pelvis and the spine: twist (the hips lead, the chest follows a little later), lean, dip and rise,
//    weight shifted back in the coil and onto the front foot at the hit, a short vibration after the impact. The head
//    keeps most of the clip's own direction (the eyes stay on the opponent while the body turns under it).
// 3. Feet. Every standing, crouching or striking act shares ONE stance: the balls of the feet stay where the guard
//    pose has them (no slide between acts). A foot is free to pivot on its ball and to lift its heel: the driving foot
//    of a punch follows the hips, the support foot of a kick pivots; a heel also lifts by itself when the leg would
//    not reach. Then the pelvis is brought within reach of both legs (a leg never straighter than RB.ext), the knees
//    are placed by a pole (between where the pelvis carries them and over the toes), the toes stay flat on the floor.
//    Walks, dashes and the throw keep the clip's own foot placement (held through the style), never under the floor.
// 4. Balance: the body's mass (pelvis and chest) stays over the feet in contact, within RB.bal metres.
// 5. Hit accuracy: on the active frames the hitting limb is brought inside the move's box (the pelvis moves, the feet stay).
// The last part of a grounded move's recovery eases back into the stance, so the next act starts from the guard.

const RB = {
  ext: .965,          // a leg in contact is never straighter than this share of its length
  heelMax: 30,        // degrees a heel may lift (the shoe is rigid: it turns on its toe tip)
  bal: .1,            // metres the mass may be off the support before the pelvis is brought back
  blend: 6, hitBlend: 3,   // frames: easing into a new free act / into a hit reaction
  md: null, W: null, sty: null, con: null, pol: 'none',
  // Per move. hip/chest = twist at the impact (degrees; the sign follows the hitting side), coil = share wound the other
  // way first, lean = pitch at the impact (degrees, < 0 back) and leanCoil in the coil, dip = pelvis drop in the coil and
  // rise at the impact (shares of the height; rise < 0 sinks into the hit), back/fwd = metres the pelvis moves back in
  // the coil and forward at the hit, heel = degrees the driving (punch) or support (kick) foot lifts its heel, heel2 =
  // the other foot's, vib = degrees of the impact's vibration, smear = stretch of the hitting limb just before the hit.
  moves: {
    p1: {hip: 8, chest: 12, coil: .6, lean: 6, dip: .012, rise: 0, back: .02, fwd: .06, heel: 7, vib: .8, smear: .22},
    p2: {hip: 16, chest: 18, coil: .8, lean: 9, dip: .02, rise: 0, back: .03, fwd: .09, heel: 20, vib: 1.1, smear: .28},
    p3: {hip: 18, chest: 22, coil: .9, lean: 4, dip: .03, rise: -.01, back: .03, fwd: .05, heel: 14, vib: 1.5, smear: .3},
    hp: {hip: 24, chest: 28, coil: 1, lean: 14, leanCoil: -7, dip: .05, rise: -.015, back: .07, fwd: .14, heel: 26, heel2: 0, vib: 2.6, smear: .5},
    k1: {hip: 6, chest: -8, coil: .6, lean: -7, dip: .015, rise: 0, back: 0, fwd: .02, heel: 6, vib: .8, smear: .22},
    k2: {hip: 12, chest: -12, coil: .8, lean: -11, dip: .025, rise: .005, back: 0, fwd: .02, heel: 9, vib: 1.2, smear: .3},
    hk: {hip: 20, chest: -20, coil: 1, lean: -15, leanCoil: 6, dip: .045, rise: .01, back: 0, fwd: .03, heel: 12, vib: 2.6, smear: .5},
    cp: {hip: 10, chest: 14, coil: .7, lean: 9, dip: .01, rise: 0, back: .03, fwd: .1, heel: 12, vib: .8, smear: .22},
    ck: {hip: 6, chest: -6, coil: .6, lean: -3, dip: .008, rise: 0, back: 0, fwd: .02, heel: 6, vib: .7, smear: .2},
    chp: {hip: 14, chest: 20, coil: 1, lean: -9, leanCoil: 12, dip: .055, rise: .05, back: .02, fwd: .05, heel: 24, heel2: 14, vib: 2.2, smear: .45},
    chk: {hip: 10, chest: -12, coil: 1, lean: -12, leanCoil: 8, dip: .05, rise: .025, back: 0, fwd: .03, heel: 14, vib: 2.2, smear: .45},
    jp: {hip: 8, chest: 12, coil: .7, lean: 6, dip: 0, rise: 0, back: 0, fwd: 0, heel: 0, vib: .8, smear: .22},
    jk: {hip: 8, chest: -10, coil: .7, lean: 5, dip: 0, rise: 0, back: 0, fwd: 0, heel: 0, vib: .9, smear: .25},
    jhp: {hip: 12, chest: 18, coil: 1, lean: 9, dip: 0, rise: 0, back: 0, fwd: 0, heel: 0, vib: 2, smear: .45},
    jhk: {hip: 12, chest: -14, coil: 1, lean: 8, dip: 0, rise: 0, back: 0, fwd: 0, heel: 0, vib: 2, smear: .45},
    spec: {hip: 14, chest: 14, coil: 1.3, lean: 12, leanCoil: -6, dip: .05, rise: -.01, back: .07, fwd: .11, heel: 20, vib: 2.2, smear: 0, fd: {s: 14, a: 4, r: 26}, limb: 'handR'},
  },
  pin: {idle: 1, intro: 1, guard: 1, crouch: 1, guardC: 1, block: 1, hitStun: 1, thrown: 1, jumpSquat: 1, landing: 1, spec: 1},
  keep: {walkF: 1, walkB: 1, dashF: 1, dashB: 1, thr: 1, win: 1},
};
const RB_UP = new THREE.Vector3(0, 1, 0), RB_X = new THREE.Vector3(1, 0, 0), RB_R = Math.PI / 180;
// the fight line in model space: the sim's forward (+x of a fighter facing right) as the model, drawn turned F3_YAW, has it
const RB_LINE = new THREE.Vector3(Math.cos(F3_YAW), 0, Math.sin(F3_YAW));

// --- Forward kinematics: every bone's model-space rotation and position, parents first, in one pass ---
function rbFK(md, p, W) {
  const bs = md.bones;
  for (let i = 0; i < md.nb; i++) {
    const par = bs[i].p, q = W.q[i].fromArray(p.q, i * 4), o = W.p[i];
    if (par < 0) o.fromArray(p.h);
    else { o.fromArray(bs[i].t).applyQuaternion(W.q[par]).add(W.p[par]); q.premultiply(W.q[par]); }
  }
  return W;
}
function rbSpace(n) { return {q: Array.from({length: n}, () => new THREE.Quaternion()), p: Array.from({length: n}, () => new THREE.Vector3())}; }

// Once per package: the legs' measures and frames from the rest pose (standing straight, soles flat on the floor).
function rbInit(md) {
  if (RB.md === md) return;
  const T = THREE, ix = md.index, rest = mdRest(md), W = rbSpace(md.nb);
  rbFK(md, rest, W);
  RB.md = md; RB.W = rbSpace(md.nb); RB.H = md.meta.height; RB.leg = {}; RB.stance = null;
  for (const s of ['L', 'R']) {
    const n = s === 'L' ? 'Left' : 'Right', iu = ix[n + 'UpLeg'], il = ix[n + 'Leg'], ia = ix[n + 'Foot'], it = ix[n + 'ToeBase'];
    const tl = new T.Vector3().fromArray(md.bones[il].t), ta = new T.Vector3().fromArray(md.bones[ia].t);
    const frame = (i, child) => {   // the transpose of the bone's local basis (hinge, along the bone, their cross)
      const along = child.clone().normalize(), hx = new T.Vector3(1, 0, 0).applyQuaternion(W.q[i].clone().invert());
      hx.addScaledVector(along, -hx.dot(along)).normalize();
      return new T.Matrix4().makeBasis(hx, along, new T.Vector3().crossVectors(hx, along)).transpose();
    };
    // the tip of the sole: the farthest low vertex of this side along the foot's direction, on the floor
    const f0 = new T.Vector3().fromArray(md.bones[it].t).applyQuaternion(W.q[ia]).setY(0).normalize(), ball0 = W.p[it], pos = md.geo.attributes.position;
    let far = 0;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      if (pos.getY(i) > .07 || (x > 0) !== (s === 'L')) continue;
      far = Math.max(far, (x - ball0.x) * f0.x + (pos.getZ(i) - ball0.z) * f0.z);
    }
    const tip = new T.Vector3(ball0.x + f0.x * far, 0, ball0.z + f0.z * far).sub(W.p[ia]).applyQuaternion(W.q[ia].clone().invert());
    RB.leg[s] = {iu, il, ia, it, tp: tip, far, a: tl.length(), b: ta.length(), tu: new T.Vector3().fromArray(md.bones[iu].t),
      tb: new T.Vector3().fromArray(md.bones[it].t), Mu: frame(iu, tl), Ml: frame(il, ta),
      up: new T.Vector3(0, 1, 0).applyQuaternion(W.q[ia].clone().invert()),   // the sole's normal in the foot's frame
      toe: new T.Quaternion().fromArray(md.bones[it].q), ball: W.p[it].y, ank: W.p[ia].y};
  }
  const mk = () => ({w: 0, G: new T.Vector3(), Q: new T.Quaternion(), T: new T.Vector3(), yaw: 0, heel: 0, auto: false, flat: null, loc: null});
  RB.con = {L: mk(), R: mk()}; RB.sav = {L: mk(), R: mk()};
  RB.sty = {h: {L: 0, R: 0}, p: {L: 0, R: 0}, auto: {L: false, R: false}};
  RB.t = {q: [0, 1, 2, 3, 4, 5].map(() => new T.Quaternion()), v: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(() => new T.Vector3()), m: new T.Matrix4(), qHead: new T.Quaternion(),
    cb: {L: new T.Vector3(), R: new T.Vector3()}, ca: {L: new T.Vector3(), R: new T.Vector3()}, cq: {L: new T.Quaternion(), R: new T.Quaternion()}};
}

// The stance every grounded act shares: the balls of the feet of the idle pose on the floor, each foot's flat
// orientation there, the pelvis' heading. Per character and look (the idle's clip entry).
function rbStance(md, F) {
  const lk = CFG.looks[F.char], key = lk && lk.clips ? lk.clips : CFG.clips;
  if (RB.stance && RB.stance.key === key) return RB.stance;
  const T = THREE, F0 = {side: 0, char: F.char, x: 0, y: 0, vx: 0, vy: 0, face: 1, act: 'idle', af: 0, air: false, hit: 0, stun: 0, prev: 0};
  const p = mdPoseOf(F0, {frame: 0}), W = rbFK(md, p, RB.W), st = {key, pose: p};
  for (const s of ['L', 'R']) {
    const L = RB.leg[s], q = W.q[L.ia].clone(), n = L.up.clone().applyQuaternion(q);
    q.premultiply(new T.Quaternion().setFromUnitVectors(n, RB_UP));   // the sole flat on the floor
    const f = L.tb.clone().applyQuaternion(q).setY(0).normalize();
    st[s] = {G: new T.Vector3(W.p[L.it].x + f.x * L.far, 0, W.p[L.it].z + f.z * L.far), Q: q, fwd: f, axis: new T.Vector3().crossVectors(RB_UP, f).normalize()};   // G: the toe tip, on the floor
  }
  st.yaw = rbYaw(W.q[0]); st.rear = st.L.G.z < st.R.G.z ? 'L' : 'R'; st.front = st.rear === 'L' ? 'R' : 'L';
  F0.act = 'crouch'; st.crouch = mdPoseOf(F0, {frame: 0});
  return RB.stance = st;
}
function rbYaw(q) { const v = RB.t.v[9].set(0, 0, 1).applyQuaternion(q); return Math.atan2(v.x, v.z); }

// --- Timing ---
// The style's curve of a move at frame af: 0, down to -coil (wound the other way, quick then held), a whip up to +1 at
// the impact, held through the active frames and the lock (first tenth of the recovery), then a settle that passes a
// little under 0 and is back at 0 by 62% of the recovery.
function rbCurve(af, s, a, r, coil) {
  if (af <= 0) return 0;
  if (af <= s) {
    const u = af / s, uc = s <= 5 ? .45 : .55, c = coil * Math.min(1, s / 7);
    if (u < uc) { const x = 1 - u / uc; return -c * (1 - x * x * x); }
    const x = (u - uc) / (1 - uc); return -c + (1 + c) * x * x * x;
  }
  if (af <= s + a) return 1;
  const v = (af - s - a) / r;
  if (v >= .62) return 0;
  if (v < .1) return 1;
  const w = (v - .1) / .52;
  return (1 - w) * (1 - w) * Math.cos(1.5 * Math.PI * w);
}
// A move's clip time: it stays near its start while the body coils, whips to the hit frame, holds it through the
// active frames and the lock, and is at its end by 70% of the recovery.
RN.moveT = function (t, m, af, hit) {
  const h = hit === undefined ? (t[0] + t[1]) / 2 : hit, s = m.s;
  if (af <= s) {
    const u = Math.max(0, af) / s, uc = .55;
    const g = s <= 5 ? Math.pow(u, 1.6) : u < uc ? .12 * u / uc : .12 + .88 * Math.pow((u - uc) / (1 - uc), 2.2);
    return t[0] + (h - t[0]) * g;
  }
  if (af <= s + m.a) return h;
  const v = Math.min(1, (af - s - m.a) / (m.r === 'land' ? 8 : m.r)), x = 1 - Math.min(1, Math.max(0, v - .1) / .6);
  return h + (t[1] - h) * (1 - x * x);
};

// --- Style: what the act asks of the body at this frame (RB.sty, reused) ---
function rbStyle(F, S, st) {
  const y = RB.sty, act = F.act, H = RB.H, t = S.frame + 23 * F.side, af = F.af;
  y.yaw = y.chest = y.lean = y.dip = y.sz = y.head = 0; y.stab = .8; y.free = null; y.back = 0; y.backTo = null; y.box = 0; y.move = null;
  y.h.L = y.h.R = 0; y.p.L = y.p.R = .3; y.auto.L = y.auto.R = false;
  const mv = RB.moves[act], m = mv && (CFG.moves[act] || mv.fd);
  if (mv && m) {
    const s = m.s, a = m.a, r = m.r === 'land' ? 14 : m.r, e = CFG.clips[act] || {};
    const limb = e.limb || (e.up && e.up.limb) || m.limb || mv.limb, side = /R$/.test(limb) ? 1 : -1, kick = /^foot/.test(limb);
    const kH = rbCurve(af, s, a, r, mv.coil), kC = rbCurve(af - Math.min(2, s * .18), s, a, r, mv.coil), up = Math.max(0, kH), dn = Math.max(0, -kH);
    const ti = af - s, vib = ti > 0 && ti < 14 ? mv.vib * Math.exp(-ti / 3.5) * Math.sin(ti * 2.26) : 0;
    y.yaw = side * (mv.hip * kH + vib * .5); y.chest = side * (mv.chest * kC + vib);
    y.lean = mv.lean * up + (mv.leanCoil === undefined ? -.3 * mv.lean : mv.leanCoil) * dn;
    y.dip = H * (mv.dip * dn - mv.rise * up); y.sz = mv.fwd * up - mv.back * dn;
    const own = side > 0 ? 'R' : 'L', other = side > 0 ? 'L' : 'R';
    if (kick) { y.free = own; y.freeW = Math.max(1 - rnSm(af / 2.5), 0); y.h[other] = mv.heel * up; y.p[other] = .8; }   // (the support foot: no heel lifting by itself, the pelvis comes down instead)
    else { y.h[own] = mv.heel * up; y.p[own] = .75; y.auto[own] = true; y.h[other] = (mv.heel2 || 0) * up; y.p[other] = .25; y.auto[other] = true; }
    y.move = {id: act, m, limb, mv, s, a};
    if (!F.air) {
      const v = (af - s - a) / r;
      if (v > .55) { y.back = rnSm((v - .55) / .45); y.backTo = CROUCHED[act] ? 'crouch' : 'idle'; if (y.backTo === 'idle') rbIdle(y, t, y.back, st); }
      if (kick) y.freeW = Math.max(y.freeW, y.back);   // the kicking foot is back on its spot with the stance
    }
    if (CFG.moves[act]) y.box = af <= s - 1 || af >= s + a + 2 ? 0 : af <= s ? af - (s - 1) : af <= s + a ? 1 : 1 - (af - s - a) / 2;
    return y;
  }
  switch (act) {
    case 'idle': case 'intro': rbIdle(y, t, 1, st); break;
    case 'guard': case 'guardC': case 'crouch': y.chest = 1.5 * Math.sin(t * .075); y.dip = .003 * H * (1 + Math.sin(t * .15)); break;
    case 'walkF': y.lean = 6; y.chest = 4 * Math.sin(F.x / 1000 * 4.4); break;
    case 'walkB': y.lean = -2; y.chest = -3 * Math.sin(F.x / 1000 * 4.4); break;
    case 'dashF': { const u = rnSm(af / 4) * (1 - rnSm((af - 12) / 6)); y.lean = 17 * u; y.dip = .03 * H * u; break; }
    case 'dashB': { const u = rnSm(af / 4) * (1 - rnSm((af - 12) / 8)); y.lean = -9 * u; y.dip = .02 * H * u; break; }
    case 'jumpSquat': { const u = rnSm(af / 3); y.dip = .06 * H * u; y.lean = 7 * u; y.h.L = y.h.R = 6 * u; break; }
    case 'landing': { const u = Math.exp(-af / 3.5) * (1 - Math.exp(-af * 1.4)) * 1.6; y.dip = .085 * H * u; y.lean = 9 * u; break; }
    case 'air': { const u = mdUp((CFG.jump.v - F.vy) / (2 * CFG.jump.v)); y.lean = 7 - 12 * u; break; }   // rising: forward, falling: opening up
    case 'hitStun': case 'thrown': { const u = Math.exp(-af / 5), w = Math.sin(Math.min(af, 9) * .9) * Math.exp(-af / 4);
      y.lean = -13 * u; y.head = -15 * u; y.stab = 0; y.chest = -9 * u + 3 * w; y.yaw = -4 * u; y.sz = -.07 * u; y.dip = .03 * H * u; y.h[st.front] = 9 * u; break; }
    case 'block': { const u = Math.exp(-af / 4), w = Math.sin(Math.min(af, 8) * 1.3) * Math.exp(-af / 3);
      y.lean = -6 * u; y.sz = -.035 * u; y.dip = .028 * H * u; y.chest = 2 * w; y.head = 5 * u; break; }
  }
  return y;
}
// The guard's bounce on the balls of the feet (weight k): the pelvis bobs, both heels stay off the floor (the rear one
// more) and lift with it, the weight passes from one foot to the other at half the pace, the shoulders answer.
function rbIdle(y, t, k, st) {
  const ph = t * (2 * Math.PI / 26), up = (1 - Math.cos(ph)) / 2, sw = Math.sin(ph / 2);
  y.dip += k * (.014 - .026 * up);
  y.h[st.front] += k * (1 + 5 * up); y.h[st.rear] += k * (4 + 8 * up);
  y.sz += k * .02 * sw; y.chest += k * 2.4 * Math.sin(ph / 2 + .9); y.yaw += k * 1.2 * sw;
}

// --- The pose ---
RN.pure = function (md, F, S) {
  rbInit(md);
  const st = rbStance(md, F), act = F.act, y = rbStyle(F, S, st);
  let p = mdPoseOf(F, S) || mdRest(md);
  if (y.back > 0) p = mdMix(p, y.backTo === 'crouch' ? st.crouch : rbIdlePose(F, S), y.back);
  const pol = F.air ? 'none' : RB.pin[act] || CFG.moves[act] ? 'pin' : RB.keep[act] ? 'keep' : 'none';
  RB.pol = pol;
  rbBody(md, p, y);
  if (pol !== 'none') { rbContacts(md, p, y, st, pol); rbLegs(md, p, pol === 'pin'); }
  if (y.box > 0 && rbBox(md, p, F, y, pol)) rbBox(md, p, F, y, pol);   // (twice: the legs may pull the pelvis back a little)
  return p;
};
function rbIdlePose(F, S) {
  const D = RB.idleF || (RB.idleF = {}); Object.assign(D, F); D.act = 'idle'; D.af = 99; D.air = false; D.hit = 0;
  return mdPoseOf(D, S);
}

// Pelvis, spine and head of pose p as the style y asks. The clip's own feet, ankles and head are noted first (RB.t).
function rbBody(md, p, y) {
  const t = RB.t, W = rbFK(md, p, RB.W), ix = md.index, q = t.q;
  t.qHead.copy(W.q[ix.Head]);
  for (const s of ['L', 'R']) { const L = RB.leg[s]; t.cb[s].copy(W.p[L.it]); t.ca[s].copy(W.p[L.ia]); t.cq[s].copy(W.q[L.ia]); }
  // pelvis: turned about the vertical, then leant toward the opponent; moved along the facing and down
  const qH = q[0].copy(W.q[0]);
  if (y.yaw) qH.premultiply(q[1].setFromAxisAngle(RB_UP, y.yaw * RB_R));
  if (y.lean) qH.premultiply(q[1].setFromAxisAngle(RB_X, y.lean * RB_R));
  qH.toArray(p.q, 0);
  p.h[1] -= y.dip; p.h[2] += y.sz;
  // spine: the chest's twist spread over its three bones, each about the vertical
  const PW = q[2].copy(qH), chain = [ix.Spine02, ix.Spine01, ix.Spine], share = [.3, .35, .35];
  for (let k = 0; k < 3; k++) {
    const i = chain[k], ql = q[3].fromArray(p.q, i * 4);
    if (y.chest) {
      q[1].setFromAxisAngle(RB_UP, y.chest * share[k] * RB_R);
      ql.premultiply(PW).premultiply(q[1]).premultiply(q[4].copy(PW).invert());   // local = PW^-1 * turn * PW * local
      ql.toArray(p.q, i * 4);
    }
    PW.multiply(ql);
  }
  // head: most of the way back to where the clip had it looking, then the act's own nod
  PW.multiply(q[3].fromArray(p.q, ix.neck * 4));
  const hw = q[4].copy(PW).multiply(q[3].fromArray(p.q, ix.Head * 4));
  if (y.stab) hw.slerp(t.qHead, y.stab);
  q[1].copy(PW).invert().multiply(hw).toArray(p.q, ix.Head * 4);
  if (y.head) mdBoneTurn(p, ix.Head, MD_X, y.head);
}

// The feet's contacts (RB.con) for pose p. 'pin': the shared stance's balls, each foot flat there, turned on its ball
// with the pelvis (by its pivot share) and its heel lifted as the style asks; the kicking leg is free (the clip's, as
// the pelvis carries it). 'keep': where the clip has the foot, never under the floor, free by how high the clip lifts it.
function rbContacts(md, p, y, st, pol) {
  const t = RB.t, T = THREE, dyaw = rbYaw(t.q[0].fromArray(p.q, 0)) - st.yaw;
  for (const s of ['L', 'R']) {
    const L = RB.leg[s], c = RB.con[s], hb = t.cb[s].y - L.ball;
    c.flat = null; c.auto = false; c.heel = 0; c.yaw = 0;
    if (pol === 'pin') {
      c.w = y.free === s ? y.freeW : 1;   // the kicking leg is the clip's (free) but at the move's two ends
      c.G.copy(st[s].G); c.flat = st[s]; c.auto = y.auto[s]; c.loc = L.tp;
      c.yaw = Math.max(-.9, Math.min(.9, y.p[s] * Math.atan2(Math.sin(dyaw), Math.cos(dyaw))));
      c.heel = Math.min(RB.heelMax, y.h[s] + Math.abs(c.yaw) / RB_R * .2);
      rbFoot(c, L);
    } else {
      c.w = 1 - rnSm((hb - .04) / .1);
      c.G.copy(t.cb[s]); if (c.G.y < L.ball) c.G.y = L.ball;
      c.Q.copy(t.cq[s]); c.loc = L.tb;
    }
  }
}
// A pinned foot's orientation: flat on the floor, heel lifted about the ball's axis, turned about the vertical.
function rbFoot(c, L) {
  const q = RB.t.q;
  c.Q.copy(c.flat.Q);
  if (c.heel) c.Q.premultiply(q[1].setFromAxisAngle(c.flat.axis, c.heel * RB_R));
  if (c.yaw) c.Q.premultiply(q[1].setFromAxisAngle(RB_UP, c.yaw));
}

// Legs of pose p onto their contacts: heels that lift by themselves when a leg is short, the mass over the feet, the
// pelvis within reach of both legs, then each leg by IK (a free leg stays as the pelvis carries it). balance = also
// keep the mass over the support.
function rbLegs(md, p, balance) {
  const t = RB.t, v = t.v, q = t.q, W = rbFK(md, p, RB.W), ix = md.index, con = RB.con;
  const qH = q[0].fromArray(p.q, 0), h = v[0].fromArray(p.h);
  const hip = (s, out) => out.copy(RB.leg[s].tu).applyQuaternion(qH).add(h);
  const ankle = (s, out) => out.copy(con[s].loc).applyQuaternion(con[s].Q).negate().add(con[s].G);
  // balance: pelvis and chest over the feet in contact
  if (balance) {
    const com = v[1].copy(W.p[ix.Spine]).multiplyScalar(.45).addScaledVector(h, .55).setY(0), l = con.L.w > .5, r = con.R.w > .5;
    if (l || r) {
      const near = v[2];
      if (l && r) {
        const ab = v[3].subVectors(con.L.G, con.R.G).setY(0), k = Math.max(.12, Math.min(.88, v[4].subVectors(com, con.R.G).setY(0).dot(ab) / ab.lengthSq()));
        near.copy(con.R.G).addScaledVector(ab, k).setY(0);
      } else near.copy(l ? con.L.G : con.R.G).setY(0);
      const d = near.sub(com), n = d.length(), lim = l && r ? RB.bal : RB.bal + .04;
      if (n > lim) { h.addScaledVector(d, .8 * (n - lim) / n); }
    }
  }
  // a heel lifts by itself, in steps, while its leg would be too straight
  for (const s of ['L', 'R']) {
    const c = con[s], L = RB.leg[s];
    if (c.w < .5 || !c.auto) continue;
    for (let k = 0; k < 9 && c.heel < RB.heelMax; k++) {
      if (hip(s, v[5]).distanceTo(ankle(s, v[6])) <= (L.a + L.b) * RB.ext) break;
      c.heel += 4; rbFoot(c, L);
    }
  }
  // the pelvis within reach of the legs in contact
  for (let k = 0; k < 4; k++) for (const s of ['L', 'R']) {
    const c = con[s], L = RB.leg[s];
    if (c.w <= 0) continue;
    const d = ankle(s, v[6]).sub(hip(s, v[5])), n = d.length(), ex = n - (L.a + L.b) * RB.ext;
    if (ex > 0) h.addScaledVector(d, ex / n * c.w);
  }
  h.toArray(p.h);
  // each leg: on its contact; partly free (a foot leaving or coming back to its spot: it steps, a little off the
  // floor); or free, as the pelvis carries the clip's leg. No foot under the floor, none rolled on its edge near it.
  for (const s of ['L', 'R']) {
    const c = con[s], L = RB.leg[s], A = hip(s, v[5]), tgt = c.T, Qf = q[5];
    const qU = q[1].copy(qH).multiply(q[2].fromArray(p.q, L.iu * 4)), knee = v[7].fromArray(md.bones[L.il].t).applyQuaternion(qU).add(A);
    let solve = c.w > 0;
    if (c.w >= 1) { ankle(s, tgt); Qf.copy(c.Q); }
    else {
      const qL = q[2].copy(qU).multiply(q[3].fromArray(p.q, L.il * 4)), fa = v[8].fromArray(md.bones[L.ia].t).applyQuaternion(qL).add(knee);
      qL.multiply(q[3].fromArray(p.q, L.ia * 4));   // the carried foot
      if (c.w > 0) { ankle(s, tgt).lerpVectors(fa, tgt, c.w); Qf.copy(qL).slerp(c.Q, c.w); tgt.y += .05 * Math.sin(Math.PI * c.w); }
      else { tgt.copy(fa); Qf.copy(qL); }
    }
    if (!c.flat || c.w < 1) {
      const ball = v[6].copy(L.tb).applyQuaternion(Qf).add(tgt), near = 1 - rnSm((ball.y - L.ball) / .08);
      if (near > 0) {   // near the floor: the sole's sideways tilt taken out
        const f = v[1].copy(L.tb).applyQuaternion(Qf).setY(0), n = v[2].copy(L.up).applyQuaternion(Qf);
        if (f.lengthSq() > 1e-6) {
          f.normalize();
          const roll = Math.atan2(n.dot(v[3].crossVectors(RB_UP, f)), n.y);
          if (Math.abs(roll) > .03) { Qf.premultiply(q[3].setFromAxisAngle(f, roll * near)); solve = true; ball.copy(L.tb).applyQuaternion(Qf).add(tgt); }
        }
      }
      const low = Math.max(L.ball - ball.y, -(v[1].copy(L.tp).applyQuaternion(Qf).y + tgt.y), .07 - tgt.y);   // ball, toe tip and ankle above the floor
      if (low > 0) { tgt.y += low; solve = true; }
    }
    if (!solve) continue;
    rbIK(md, p, L, qH, A, tgt, Qf, knee, c.w >= 1 && !!c.flat);
  }
}

// One leg by IK: hip joint A, ankle target tgt, the foot's rotation Qf, knee = where the knee is now (its side of the
// leg is kept, pulled over the toes: never more than 40 degrees from the foot's direction), rigid = the shoe keeps its
// rest shape (a pinned foot turns on its toe tip as one piece: bent at the toes this boot folds badly).
function rbIK(md, p, L, qH, A, tgt, Qf, knee, rigid) {
  const T = THREE, a = L.a, b = L.b;
  const dir = new T.Vector3().subVectors(tgt, A), full = dir.length(), d = Math.max(Math.abs(a - b) + 1e-3, Math.min((a + b) * .999, full));
  dir.multiplyScalar(1 / (full || 1e-9));
  const Pf = L.tb.clone().applyQuaternion(Qf).setY(0); Pf.addScaledVector(dir, -Pf.dot(dir));
  if (Pf.lengthSq() < 1e-8) Pf.set(0, 0, 1).addScaledVector(dir, -dir.z);
  Pf.normalize();
  const Pc = new T.Vector3().subVectors(knee, A); Pc.addScaledVector(dir, -Pc.dot(dir));
  const P = Pc.lengthSq() < 1e-6 ? Pf.clone() : Pc.normalize().lerp(Pf, .5).normalize();
  for (let k = 0; k < 3 && P.dot(Pf) < .766; k++) P.lerp(Pf, .5).normalize();
  const cos = (a * a + d * d - b * b) / (2 * a * d), sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  const dU = dir.clone().multiplyScalar(cos).addScaledVector(P, sin), B = A.clone().addScaledVector(dU, a);
  const dL = A.clone().addScaledVector(dir, d).sub(B).normalize(), n = new T.Vector3().crossVectors(P, dir).normalize();
  const m = RB.t.m, z = new T.Vector3();
  const qU = new T.Quaternion().setFromRotationMatrix(m.makeBasis(n, dU, z.crossVectors(n, dU)).multiply(L.Mu));
  const qL = new T.Quaternion().setFromRotationMatrix(m.makeBasis(n, dL, z.crossVectors(n, dL)).multiply(L.Ml));
  const inv = new T.Quaternion();
  inv.copy(qH).invert().multiply(qU).toArray(p.q, L.iu * 4);
  inv.copy(qU).invert().multiply(qL).toArray(p.q, L.il * 4);
  inv.copy(qL).invert().multiply(Qf).toArray(p.q, L.ia * 4);
  if (rigid) L.toe.toArray(p.q, L.it * 4);
}

// The hitting limb inside its move's box (15 mm in from its edges) on the active frames, eased in and out by y.box:
// the pelvis moves by what is missing (along the fight line and up or down), the legs follow on their contacts.
function rbBox(md, p, F, y, pol) {
  const mvn = y.move, k = mvn.m.box, meta = md.meta.limbs[mvn.limb], i = md.index[meta.b], v = RB.t.v, W = rbFK(md, p, RB.W);
  const pt = v[1].fromArray(meta.p).applyQuaternion(W.q[i]).add(W.p[i]), x = pt.dot(RB_LINE) * 1000, yy = pt.y * 1000, g = 15;
  const ex = x < k[0] + g ? k[0] + g - x : x > k[1] - g ? k[1] - g - x : 0, ey = yy < k[2] + g ? k[2] + g - yy : yy > k[3] - g ? k[3] - g - yy : 0;
  if (!ex && !ey) return false;
  p.h[0] += RB_LINE.x * ex / 1000 * y.box; p.h[2] += RB_LINE.z * ex / 1000 * y.box; p.h[1] += ey / 1000 * y.box;
  if (pol !== 'none') rbLegs(md, p, false);
  return true;
}

// --- The drawn pose: RN.pure eased in from the last drawn pose when the act changes ---
// A strike eases in over at most its startup minus 1 (its active frames are exact), a hit reaction over RB.hitBlend
// frames, a rise from the floor not at all, anything else over RB.blend. The eased pose's feet go to the new pose's
// contacts (at once when the last pose stood on the same stance, else as the ease advances).
RN.pose = function (it, F, S) {
  const md = mdData(it.key);
  let p = RN.pure(md, F, S);
  const pol = RB.pol, m = CFG.moves[F.act] || (RB.moves[F.act] && RB.moves[F.act].fd);
  const hit = {hitStun: 1, block: 1, thrown: 1, knock: 1, juggle: 1}[F.act];
  const n = m ? Math.min(CFG.anim.strikeIn, m.s - 1) : hit ? RB.hitBlend : {getup: 1, rollF: 1, rollB: 1}[F.act] ? 0 : RB.blend;
  if (F !== it.F) it.from = null;
  else if (F.act !== it.act || F.af < it.af - .5) { it.from = n > 0 ? it.pose : null; it.fromPin = it.pin; }
  if (it.from && F.af < n) {
    const k = rnSm(Math.max(0, F.af) / n), con = RB.con, sav = RB.sav, same = pol === 'pin' && it.fromPin;
    for (const s of ['L', 'R']) { sav[s].w = con[s].w; sav[s].G.copy(con[s].G); }
    p = mdMix(it.from, p, k);
    if (pol !== 'none') {
      const W = rbFK(md, p, RB.W);
      for (const s of ['L', 'R']) {
        const L = RB.leg[s], c = con[s];
        c.w = sav[s].w * (same ? 1 : k); c.flat = null; c.auto = false;   // (c.loc: the new pose's pinned point)
        c.Q.copy(W.q[L.ia]); c.G.copy(sav[s].G);
      }
      rbLegs(md, p, false);
    }
  }
  it.pin = pol === 'pin';
  return p;
};

// --- Smear ("Allungo"): the hitting forearm or shin stretched along itself just before the impact (about 3 frames),
// thinner as it gets longer; on the first active frame it has its true size again (the hit is exact). ---
RN.hooks.boot.push(() => rnOpt('smear', 'Allungo', true));
RN.hooks.applied.push((it, F) => {
  const md = mdData(it.key), ix = md.index, mv = RB.moves[F.act], m = mv && (CFG.moves[F.act] || mv.fd);
  let on = null, sc = 1;
  if (RN.opt.smear && mv && m && mv.smear) {
    const e = CFG.clips[F.act] || {}, limb = e.limb || (e.up && e.up.limb) || m.limb || mv.limb, x = F.af - (m.s - .8);
    const k = x < -1.7 || x > 1.4 ? 0 : x < 0 ? 1 + x / 1.7 : 1 - x / 1.4;
    if (k > 0) { on = (/L$/.test(limb) ? 'Left' : 'Right') + (/^foot/.test(limb) ? 'Leg' : 'ForeArm'); sc = 1 + mv.smear * k; }
  }
  for (const n of ['LeftForeArm', 'RightForeArm', 'LeftLeg', 'RightLeg']) {
    const b = it.bones[ix[n]];
    if (n === on) b.scale.set(1 / Math.sqrt(sc), sc, 1 / Math.sqrt(sc)); else if (b.scale.y !== 1) b.scale.set(1, 1, 1);
  }
});
