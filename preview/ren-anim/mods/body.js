// --- body.js: Ren's body. The style of every act and the solver that keeps the body physically right. ---
// Graphics only and pure: RN.pure(md, F, S) is a function of the fighter's act and frame (fractional frames are valid).
// Model space (metres): +y up, +z forward (the way the fighter faces), +x the fighter's left.
//
// The Meshy clips are motion capture of an actor who travels while striking (the heavy kick's hips move 60 cm, the jab
// steps half a metre), played here on a fighter who stays on his spot. So:
// 1. Feet. Every standing, crouching or striking act shares ONE stance: the toe tips stay where the guard pose has them
//    (no slide between acts, a rigid shoe turning on its tip). In a strike each planted foot turns and lifts its heel as
//    the actor's did (eased in over the startup, out over the recovery; its sideways tilt removed, its heel lift capped).
// 2. Pelvis. It goes where the capture has it RELATIVE TO THE FEET: moved by the mean of what separates the pinned feet
//    from where the clip's legs would put them (within RB.travel metres). The legs then stay close to the captured
//    ones: the hips' own travel comes back as a weight shift over the feet instead of stretched or folded legs.
// 3. Legs by IK from the captured leg, changed as little as possible (its twist kept): a leg never straighter than
//    RB.ext (the pelvis comes down), the knee kept on its side, pulled toward the toes only beyond 40 degrees.
// 4. Balance: on one foot (a kick) the pelvis moves until the body's mass is over the standing foot, as the actor's.
// 5. A little style on top: a twist of hips then chest, a lean, a dip (a coil the other way first, then the hit, then a
//    settle), the clip's time eased (slower coil, faster release). The head keeps most of the clip's own direction.
// 6. Hit accuracy: on the active frames the hitting limb is brought inside the move's box (the pelvis moves, the feet stay).
// Everything is continuous in the frame: no stepwise search, no threshold that flips. The last part of a grounded
// move's recovery eases back into the stance, so the next act starts from the guard.

const RB = {
  ext: .965,          // a leg in contact is never straighter than this share of its length
  heelMax: 30,        // degrees a heel may lift (the shoe is rigid: it turns on its toe tip)
  travel: [.2, .3],   // metres the pelvis may follow the feet's captured place: both feet planted, one foot (kicks)
  bal1: .08,          // metres the body's mass may be from the middle of the standing foot in a kick (the actor's: 6-14 cm)
  blend: 6, hitBlend: 3,   // frames: easing into a new free act / into a hit reaction
  md: null, W: null, sty: null, con: null, pol: 'none', rawOk: {},
  post: [],           // functions (md, p, F, S, y) applied to the finished pose (other modules: arms, hands, head)
  styleFor: {},       // act -> function (y, F, S, st) setting the style of an act another module owns
  // Per move, what the style adds to the clip. hip/chest = twist at the impact (degrees; the sign follows the hitting
  // side), coil = share wound the other way first, lean = pitch at the impact (degrees, < 0 back) and leanCoil in the
  // coil, dip = pelvis drop in the coil and rise at the impact (shares of the height), back/fwd = metres the pelvis
  // moves back in the coil and forward at the hit, smear = stretch of the hitting limb just before the hit ("Allungo"),
  // pivot = share of the hips' turn the foot on the punching side turns with (on its ball, heel out: the knee follows the
  // hips instead of folding outward), arms = how far the arms go toward the guard [kicking side, other] (the actor's
  // raised arms read as flailing).
  moves: {
    p1: {pivot: .3, hip: 4, chest: 6, coil: .5, lean: 3, dip: .008, rise: 0, back: .01, fwd: .03, smear: .22},
    p2: {pivot: .85, hip: 6, chest: 9, coil: .7, lean: 5, dip: .012, rise: 0, back: .02, fwd: .04, smear: .28},
    p3: {pivot: .7, hip: 7, chest: 10, coil: .8, lean: 2, dip: .015, rise: 0, back: .015, fwd: .02, smear: .3},
    hp: {pivot: .85, hip: 9, chest: 13, coil: 1, lean: 7, leanCoil: -3, dip: .025, rise: 0, back: .03, fwd: .06, smear: .5},
    k1: {arms: [.35, .2], hip: 3, chest: -4, coil: .5, lean: -3, dip: .008, rise: 0, back: 0, fwd: .01, smear: .22},
    k2: {arms: [.75, .35], hip: 5, chest: -6, coil: .7, lean: -5, dip: .012, rise: 0, back: 0, fwd: .01, smear: .3},
    hk: {arms: [.75, .35], hip: 8, chest: -9, coil: 1, lean: -7, leanCoil: 3, dip: .02, rise: 0, back: 0, fwd: .015, smear: .5},
    cp: {pivot: .5, hip: 5, chest: 8, coil: .6, lean: 5, dip: .006, rise: 0, back: .02, fwd: .06, smear: .22},
    ck: {hip: 3, chest: -3, coil: .5, lean: -2, dip: .005, rise: 0, back: 0, fwd: .01, smear: .2},
    chp: {pivot: .6, hip: 7, chest: 10, coil: 1, lean: -5, leanCoil: 7, dip: .03, rise: .02, back: .01, fwd: .03, smear: .45},
    chk: {hip: 5, chest: -6, coil: .8, lean: -6, leanCoil: 4, dip: .025, rise: .01, back: 0, fwd: .015, smear: .45},
    jp: {hip: 5, chest: 8, coil: .7, lean: 4, dip: 0, rise: 0, back: 0, fwd: 0, smear: .22},
    jk: {hip: 5, chest: -6, coil: .7, lean: 4, dip: 0, rise: 0, back: 0, fwd: 0, smear: .25},
    jhp: {hip: 7, chest: 10, coil: 1, lean: 6, dip: 0, rise: 0, back: 0, fwd: 0, smear: .45},
    jhk: {hip: 7, chest: -8, coil: 1, lean: 6, dip: 0, rise: 0, back: 0, fwd: 0, smear: .45},
    spec: {pivot: .5, hip: 7, chest: 8, coil: 1, lean: 6, leanCoil: -3, dip: .025, rise: 0, back: .03, fwd: .05, smear: 0, fd: {s: 14, a: 4, r: 26}, limb: 'handR'},
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
      hu: new T.Vector3(1, 0, 0).applyQuaternion(W.q[iu].clone().invert()),   // the knee's hinge axis in the thigh's frame
      up: new T.Vector3(0, 1, 0).applyQuaternion(W.q[ia].clone().invert()),   // the sole's normal in the foot's frame
      sd: f0.clone().applyQuaternion(W.q[ia].clone().invert()),   // the sole's direction (heel to toes) and its side-to-side axis there
      lat: new T.Vector3().crossVectors(RB_UP, f0).normalize().applyQuaternion(W.q[ia].clone().invert()),
      toe: new T.Quaternion().fromArray(md.bones[it].q), ball: W.p[it].y, ank: W.p[ia].y};
  }
  const mk = () => ({w: 0, G: new T.Vector3(), Q: new T.Quaternion(), T: new T.Vector3(), yaw: 0, heel: 0, auto: false, flat: null, loc: null});
  RB.con = {L: mk(), R: mk()}; RB.sav = {L: mk(), R: mk()};
  RB.sty = {h: {L: 0, R: 0}};
  RB.t = {dir: new T.Vector3(), hipF: new T.Vector3(0, 0, 1), lift: 0, raw: {L: null, R: null}, rawOf: {L: {dir: new T.Vector3(), lift: 0}, R: {dir: new T.Vector3(), lift: 0}}, q: [0, 1, 2, 3, 4, 5].map(() => new T.Quaternion()), v: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(() => new T.Vector3()), m: new T.Matrix4(), qHead: new T.Quaternion(),
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
    st[s] = {G: new T.Vector3(W.p[L.it].x + f.x * L.far, 0, W.p[L.it].z + f.z * L.far), B: new T.Vector3(W.p[L.it].x, 0, W.p[L.it].z), Q: q, fwd: f,
      axis: new T.Vector3().crossVectors(RB_UP, f).normalize()};   // G: the toe tip, B: under the ball of the foot, both on the floor
  }
  st.yaw = rbYaw(W.q[0]); st.rear = st.L.G.z < st.R.G.z ? 'L' : 'R'; st.front = st.rear === 'L' ? 'R' : 'L';
  F0.act = 'crouch'; st.crouch = mdPoseOf(F0, {frame: 0});
  return RB.stance = st;
}
function rbYaw(q) { const v = RB.t.v[9].set(0, 0, 1).applyQuaternion(q); return Math.atan2(v.x, v.z); }

// --- Timing ---
// The style's curve of a move at frame af: 0, down to -coil (wound the other way), up to +1 at the impact, held through
// the active frames, then a smooth settle back to 0 by 60% of the recovery. Smooth everywhere (no corner).
function rbCurve(af, s, a, r, coil) {
  if (af <= 0) return 0;
  if (af <= s) {
    const u = af / s, uc = .5, c = coil * Math.min(1, s / 8);
    return u < uc ? -c * Math.sin(Math.PI / 2 * rnSm(u / uc)) : -c + (1 + c) * rnSm((u - uc) / (1 - uc));
  }
  if (af <= s + a) return 1;
  return 1 - rnSm((af - s - a) / (.6 * r));
}
// A move's clip time: a little slower through the coil, faster into the hit frame, held on it through the active
// frames, and at its end by 75% of the recovery.
RN.moveT = function (t, m, af, hit) {
  const h = hit === undefined ? (t[0] + t[1]) / 2 : hit, s = m.s;
  if (af <= s) { const u = Math.max(0, af) / s; return t[0] + (h - t[0]) * (.35 * u + .65 * u * u * (s <= 5 ? 1 : u)); }
  if (af <= s + m.a) return h;
  const x = 1 - Math.min(1, (af - s - m.a) / (.75 * (m.r === 'land' ? 8 : m.r)));
  return h + (t[1] - h) * (1 - x * x);
};

// --- Style: what the act asks of the body at this frame (RB.sty, reused) ---
function rbStyle(F, S, st) {
  const y = RB.sty, act = F.act, H = RB.H, t = S.frame + 23 * F.side, af = F.af;
  y.yaw = y.chest = y.lean = y.dip = y.sz = y.head = 0; y.stab = .6; y.free = null; y.freeW = 1; y.back = 0; y.backTo = null; y.box = 0; y.move = null; y.foot = 1; y.lift = 1; y.freeB = 1; y.after = false; y.knee = 0;
  y.h.L = y.h.R = 0;
  if (RB.styleFor[act]) { RB.styleFor[act](y, F, S, st); return y; }   // an act another module styles (swag.js)
  const mv = RB.moves[act], m = mv && (CFG.moves[act] || mv.fd);
  if (mv && m) {
    const s = m.s, a = m.a, r = m.r === 'land' ? 14 : m.r, e = CFG.clips[act] || {};
    const limb = e.limb || (e.up && e.up.limb) || m.limb || mv.limb, side = /R$/.test(limb) ? 1 : -1, kick = /^foot/.test(limb);
    const kH = rbCurve(af, s, a, r, mv.coil), kC = rbCurve(af - Math.min(1.5, s * .15), s, a, r, mv.coil), up = Math.max(0, kH), dn = Math.max(0, -kH);
    y.yaw = side * mv.hip * kH; y.chest = side * mv.chest * kC;
    y.lean = mv.lean * up + (mv.leanCoil === undefined ? -.3 * mv.lean : mv.leanCoil) * dn;
    y.dip = H * (mv.dip * dn - mv.rise * up); y.sz = mv.fwd * up - mv.back * dn;
    y.foot = 1; y.lift = rnSm(af / 3);   // the planted feet turn as the actor's did since the move began, and lift their heels as his
    if (kick) { y.free = side > 0 ? 'R' : 'L'; y.freeW = e.kick ? 1 - rnSm(af / Math.max(2.5, Math.min(5, .45 * s))) : -1;   // (-1: by how high the clip lifts the foot)
      y.freeB = 1 - rnSm(af / (.5 * s)); }   // the weight leaves the kicking foot over the first half of the startup
    y.move = {id: act, m, limb, mv, s, a}; y.after = af > s + a;
    if (mv.pivot && !kick) y.knee = rnSm(af / Math.max(2, .5 * s));   // a punch's knees go with the hips (eased in)
    if (!F.air) {
      const v = (af - s - a) / r;
      if (v > .5) {   // back into the stance: the pose, the feet's turn and (kicks) the kicking foot on its spot
        y.back = rnSm((v - .5) / .5); y.backTo = CROUCHED[act] ? 'crouch' : 'idle'; y.foot = 1 - y.back; y.lift *= 1 - y.back; y.knee *= 1 - y.back;
        if (y.backTo === 'idle') rbIdle(y, t, y.back, st);
      }
    }
    if (CFG.moves[act]) { const n = Math.max(2, .45 * s); y.box = af <= s ? rnSm((af - (s - n)) / n) : af <= s + a ? 1 : 1 - rnSm((af - s - a) / 3); }
    return y;
  }
  switch (act) {
    case 'idle': case 'intro': rbIdle(y, t, 1, st); break;
    case 'guard': case 'guardC': case 'crouch': y.chest = 1.5 * Math.sin(t * .075); y.dip = .003 * H * (1 + Math.sin(t * .15)); break;
    case 'walkF': y.lean = 4; y.chest = 3 * Math.sin(F.x / 1000 * 4.4); break;
    case 'walkB': y.lean = -2; y.chest = -2 * Math.sin(F.x / 1000 * 4.4); break;
    case 'dashF': { const u = rnSm(af / 4) * (1 - rnSm((af - 12) / 6)); y.lean = 12 * u; y.dip = .02 * H * u; break; }
    case 'dashB': { const u = rnSm(af / 4) * (1 - rnSm((af - 12) / 8)); y.lean = -7 * u; y.dip = .015 * H * u; break; }
    case 'jumpSquat': { const u = rnSm(af / 3); y.dip = .04 * H * u; y.lean = 5 * u; break; }
    case 'landing': { const u = Math.exp(-af / 3.5) * (1 - Math.exp(-af * 1.4)) * 1.6; y.dip = .06 * H * u; y.lean = 6 * u; break; }
    case 'air': { const u = mdUp((CFG.jump.v - F.vy) / (2 * CFG.jump.v)); y.lean = 5 - 9 * u; break; }   // rising: forward, falling: opening up
    case 'hitStun': case 'thrown': { const u = Math.exp(-af / 5) * rnSm(af / 1.5);
      y.lean = -9 * u; y.head = -10 * u; y.stab = 0; y.chest = -6 * u; y.yaw = -3 * u; y.sz = -.05 * u; y.dip = .02 * H * u; break; }
    case 'block': { const u = Math.exp(-af / 4) * rnSm(af / 1.5); y.lean = -5 * u; y.sz = -.03 * u; y.dip = .02 * H * u; y.head = 4 * u; break; }
  }
  return y;
}
// The guard's bounce on the balls of the feet (weight k): the pelvis bobs, the heels leave the floor a little with it
// (the rear one more), the weight passes from one foot to the other at half the pace, the shoulders answer.
function rbIdle(y, t, k, st) {
  const ph = t * (2 * Math.PI / 26), up = (1 - Math.cos(ph)) / 2, sw = Math.sin(ph / 2);
  y.dip += k * (.01 - .02 * up);
  y.h[st.front] += k * (1 + 4 * up); y.h[st.rear] += k * (3 + 6 * up);
  y.sz += k * .015 * sw; y.chest += k * 2 * Math.sin(ph / 2 + .9); y.yaw += k * sw;
}

// --- The pose ---
RN.pure = function (md, F, S) {
  rbInit(md);
  const st = rbStance(md, F), act = F.act, t0 = RB.moves[act] && !F.air && !RB.keep[act] ? rbT0(md, F, S) : null,
    fix = CFG.moves[act] && RB.moves[act] ? (RB.inFix ? RB.fix.of[act] : rbBoxFix(md, F, S)) : null, y = rbStyle(F, S, st);
  let p = mdPoseOf(F, S) || mdRest(md);
  if (y.back > 0) p = mdMix(p, y.backTo === 'crouch' ? st.crouch : rbIdlePose(F, S), y.back);
  if (y.move && y.move.mv.arms && !F.air) rbArms(md, p, st.pose, y, F.af);
  const pol = F.air ? 'air' : RB.keep[act] ? 'keep' : RB.pin[act] || CFG.moves[act] ? 'pin' : 'none';
  RB.pol = pol; RB.floor = F.air ? -F.y / 1000 : 0;   // the floor in the model's frame (under a fighter in the air)
  rbBody(md, p, y);
  rbRawFeet(md, F, y);
  if (pol !== 'none') rbContacts(md, p, y, st, pol, t0);
  if (pol === 'pin' && y.free) rbBalance(md, p, y);
  RB.lf = null;
  if (fix && y.box > 0) {
    if (fix.leg && y.free === fix.leg && !F.air) RB.lf = {s: fix.leg, x: fix.x * y.box, y: fix.y * y.box, z: fix.z * y.box};   // a kick: its leg
    else { p.h[0] += fix.x * y.box; p.h[1] += fix.y * y.box; p.h[2] += fix.z * y.box; }   // else the body
  }
  if (pol !== 'none') rbLegs(md, p);
  for (const f of RB.post) f(md, p, F, S, y);
  return p;
};
// The arms of a kick toward the guard pose g (their local rotations: the guard's fists in front of the face, carried by
// the chest as it turns): by mv.arms[0] the arm on the kicking side, [1] the other, eased in over the first 3 frames
// (the stance's own way back takes over at the end).
const RB_ARM = {R: ['RightShoulder', 'RightArm', 'RightForeArm', 'RightHand'], L: ['LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand']};
function rbArms(md, p, g, y, af) {
  const kick = /R$/.test(y.move.limb) ? 'R' : 'L', e = rnSm(af / 3), q = RB.t.q;
  for (const s of ['L', 'R']) {
    const w = (s === kick ? y.move.mv.arms[0] : y.move.mv.arms[1]) * e;
    if (w <= 0) continue;
    for (const n of RB_ARM[s]) { const i = md.index[n] * 4; q[0].fromArray(p.q, i).slerp(q[1].fromArray(g.q, i), w).toArray(p.q, i); }
  }
}

// The shift that puts move F.act's hitting limb inside its box (15 mm in from its edges) on its first active frame,
// found once per move on that frame's pose: RN.pure brings it in and out smoothly around the active frames. A kick on
// the ground shifts its kicking foot (the leg bends or reaches a little more: the body stays balanced over the
// standing foot); anything else shifts the body.
function rbBoxFix(md, F, S) {
  const id = F.act, key = RB.stance.key;
  if (!RB.fix || RB.fix.key !== key) RB.fix = {key, of: {}};
  if (RB.fix.of[id]) return RB.fix.of[id];
  const m = CFG.moves[id], e = CFG.clips[id] || {}, limb = e.limb || (e.up && e.up.limb) || m.limb, meta = md.meta.limbs[limb], bi = md.index[meta.b], k = m.box, g = 15;
  const D = Object.assign({}, F, {af: m.s + 1}), fix = RB.fix.of[id] = {x: 0, y: 0, z: 0, leg: /^foot/.test(limb) && m.r !== 'land' ? (/R$/.test(limb) ? 'R' : 'L') : null}, v = new THREE.Vector3();
  RB.inFix = true;   // RN.pure below uses the shift found so far (and does not come back here)
  for (let i = 0; i < 4; i++) {   // (the legs answer the shift, so a few rounds)
    const W = rbFK(md, RN.pure(md, D, S), RB.W), pt = v.fromArray(meta.p).applyQuaternion(W.q[bi]).add(W.p[bi]), x = pt.dot(RB_LINE) * 1000, yy = pt.y * 1000;
    const ex = x < k[0] + g ? k[0] + g - x : x > k[1] - g ? k[1] - g - x : 0, ey = yy < k[2] + g ? k[2] + g - yy : yy > k[3] - g ? k[3] - g - yy : 0;
    if (!ex && !ey) break;
    fix.x += RB_LINE.x * ex / 1000; fix.z += RB_LINE.z * ex / 1000; fix.y += ey / 1000;
  }
  RB.inFix = false;
  return fix;
}
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

// The direction (on the floor) and the heel lift (degrees, 0..RB.heelMax) of a foot of rotation q: RB.t.dir, RB.t.lift.
// From the foot's side-to-side axis, which stays level however high the heel is (the sole's own direction, flattened,
// flips when the foot stands on its toes).
function rbFootOf(q, L) {
  const t = RB.t, k = t.v[1].copy(L.lat).applyQuaternion(q).setY(0);
  if (k.lengthSq() < 1e-8) k.set(1, 0, 0);
  t.dir.crossVectors(k.normalize(), RB_UP);
  t.lift = Math.max(0, Math.min(RB.heelMax, Math.asin(Math.max(-1, Math.min(1, -t.v[2].copy(L.sd).applyQuaternion(q).y))) / RB_R));
}

// The feet's contacts (RB.con) for pose p. 'pin': the shared stance's toe tips. Each foot is the stance's (flat, a
// rigid shoe), turned on its tip by as much as the clip's foot has turned (in a strike: since the move began, so it
// starts as it stands; else: from the stance's direction), within 60 degrees (90 for a kick's support foot), its heel
// lifted as the clip's and as the style asks; the kicking leg is free (the clip's). Then the pelvis moves by the mean
// of what separates the pinned tips from where the clip's legs put them (within RB.travel): the capture's place of the
// pelvis over the feet. 'keep': each foot where the clip has it, never under the floor, free by how high the clip
// lifts it. 'air': the clip's legs.
function rbContacts(md, p, y, st, pol, t0) {
  const t = RB.t, q = t.q;
  let ox = 0, oz = 0, n = 0;
  for (const s of ['L', 'R']) {
    const L = RB.leg[s], c = RB.con[s], hb = t.cb[s].y - L.ball;
    c.flat = null; c.auto = false;
    if (pol === 'pin') {
      // the kicking leg is the clip's (free) once the clip lifts its foot (a kick made by IK: after the first frames), and
      // back on its spot with the stance (in the first half of it: the foot is down before the weight moves back)
      // before the hit by how far the clip's foot has left its place (up, or along the floor: a sweep), after it on the
      // move's own timing (the actor's foot lands forward, as he steps: this one waits for the way back)
      let wk = y.freeW;
      if (y.free === s && wk < 0) wk = y.after ? 0 : 1 - rnSm((Math.max(hb, t0 ? Math.hypot(t.cb[s].x - t0.ball[s].x, t.cb[s].z - t0.ball[s].z) : 0) - .02) / .1);
      c.w = y.free === s ? Math.max(rnSm(2 * y.back), wk) : 1;
      c.G.copy(st[s].G); c.flat = st[s]; c.loc = L.tp; c.auto = !y.move;
      // the clip's own foot: for a foot the clip entry holds in place (plant), the capture's foot before that hold
      // (the hold freezes it as it stood on the move's first frame: the body turned over a foot that did not)
      if (t.raw[s]) { t.dir.copy(t.raw[s].dir); t.lift = t.raw[s].lift; } else rbFootOf(t.cq[s], L);
      // its turn: the clip's foot against its first pose (a move) or against the stance, softly limited: 160 degrees
      // for a kick's support foot (it pivots as the actor's), 20 in a punch (he stepped), 60 otherwise; a kicking foot
      // takes the clip's direction over the first half of the startup, so it does not spin as it leaves the floor
      const kicker = y.free === s, ref = t0 && !kicker ? t0[s] : st[s].fwd, lim = (kicker ? 170 : y.free ? 160 : y.move ? 20 : 60) * RB_R;
      const soft = (x, l) => { const a = Math.abs(x); return Math.sign(x) * (a <= .7 * l ? a : .7 * l + .3 * l * Math.tanh((a - .7 * l) / (.3 * l))); };
      let turn = soft(Math.atan2(ref.z * t.dir.x - ref.x * t.dir.z, ref.x * t.dir.x + ref.z * t.dir.z), lim) * (kicker ? 1 - Math.max(y.freeB, y.back) : y.foot);
      let lift = Math.min(RB.heelMax, t.lift * (kicker ? 1 - Math.max(y.freeB, y.back) : y.lift) + y.h[s]);
      const mv = y.move && y.move.mv;
      if (mv && mv.pivot && !y.free && t0 && s === (/R$/.test(y.move.limb) ? 'R' : 'L')) {   // the foot under the punch turns with the hips
        let dh = rbYaw(q[2].fromArray(p.q, 0)) - t0.hy; dh = Math.atan2(Math.sin(dh), Math.cos(dh));
        turn = soft(mv.pivot * dh, 75 * RB_R) * y.foot;
        lift = Math.min(RB.heelMax, lift + .4 * Math.abs(turn) / RB_R);
      }
      c.Q.copy(st[s].Q);
      if (lift > 0) c.Q.premultiply(q[1].setFromAxisAngle(st[s].axis, lift * RB_R));
      if (turn) { c.Q.premultiply(q[1].setFromAxisAngle(RB_UP, turn)); c.G.sub(st[s].B).applyAxisAngle(RB_UP, turn).add(st[s].B); }   // on the ball of the foot
      const wb = y.free === s ? (y.after ? c.w : y.freeB) : 1;   // this foot's say in where the pelvis goes
      if (wb > 0) { const tip = t.v[4].copy(L.tp).applyQuaternion(c.Q).add(t.ca[s]); ox += (c.G.x - tip.x) * wb; oz += (c.G.z - tip.z) * wb; n += wb; }
    } else {
      c.w = pol === 'air' ? 0 : 1 - rnSm((hb - .04) / .1);   // in the air: the clip's legs, kept above the floor that comes up
      c.G.copy(t.cb[s]); if (c.G.y < L.ball) c.G.y = L.ball;
      c.Q.copy(t.cq[s]); c.loc = L.tb;
    }
  }
  if (n) {
    ox /= n; oz /= n;
    const d = Math.hypot(ox, oz), lim = RB.travel[1] + (RB.travel[0] - RB.travel[1]) * Math.max(0, Math.min(1, n - 1)), k = d > 1e-6 ? lim * Math.tanh(d / lim) / d : 1;   // (a soft limit)
    p.h[0] += ox * k; p.h[2] += oz * k;
  }
}
// Balance on one foot (a kick): the body's mass over the standing foot, as the actor's is (his stays 6-14 cm from it;
// held where the stance has it, it hung 35 cm off). Bones weighted as a body's segments; the standing leg ends on its
// foot, so its thigh moves with the pelvis, its knee half as much, its foot not at all. The pelvis moves until the
// mass is within RB.bal1 metres of the middle of the standing foot, by the share of the weight already on it (it
// passes from both feet to the standing one over the first half of the startup, and back with the stance).
const RB_MASS = {Hips: .14, Spine02: .1, Spine01: .1, Spine: .1, Head: .08, LeftArm: .028, RightArm: .028, LeftForeArm: .016, RightForeArm: .016,
  LeftHand: .006, RightHand: .006, LeftUpLeg: .1, RightUpLeg: .1, LeftLeg: .0465, RightLeg: .0465, LeftFoot: .0145, RightFoot: .0145};
function rbBalance(md, p, y) {
  // (the weight goes over the standing foot before the kicking one leaves the floor, and comes back as that one comes down)
  const w = (1 - y.freeB) * (y.after ? 1 - RB.con[y.free].w : 1);
  if (w <= 0) return;
  const t = RB.t, v = t.v, sup = y.free === 'R' ? 'L' : 'R', c = RB.con[sup], L = RB.leg[sup], n = sup === 'L' ? 'Left' : 'Right';
  const ank = v[1].copy(c.loc).applyQuaternion(c.Q).negate().add(c.G), mid = v[2].copy(L.tb).applyQuaternion(c.Q).multiplyScalar(.5).add(ank);
  const W = rbFK(md, p, RB.W), com = v[3].set(0, 0, 0);
  let M = 0, still = 0;
  for (const b in RB_MASS) {
    const m = RB_MASS[b], i = md.index[b];
    if (b === n + 'Foot') { com.addScaledVector(ank, m); still += m; }
    else if (b === n + 'Leg') { com.addScaledVector(v[4].addVectors(W.p[md.index[n + 'UpLeg']], ank).multiplyScalar(.5), m); still += m / 2; }
    else com.addScaledVector(W.p[i], m);
    M += m;
  }
  com.multiplyScalar(1 / M);
  const gx = mid.x - com.x, gz = mid.z - com.z, g = Math.hypot(gx, gz), ex = g - RB.bal1;
  if (ex <= 0) return;
  const k = w * ex / g * M / (M - still);   // (the standing leg's part of the mass moves less than the pelvis)
  p.h[0] += gx * k; p.h[2] += gz * k;
}

// The capture's own feet of a move whose clip entry holds them in place (plant): their directions and heel lifts
// (RB.t.raw.L / .R, null for a foot the entry does not hold), read from the clip itself at the move's time counted
// evenly (not eased: the feet turn all through the startup, not in its last frames). A foot whose capture turns more
// than 150 degrees somewhere in the move is left held (a spin: its turn has no single direction).
function rbRawFeet(md, F, y) {
  const t = RB.t, lk = CFG.looks[F.char], e = y.move && !F.air ? (lk && lk.clips ? mdLookClips(lk) : CFG.clips)[F.act] : null;
  t.raw.L = t.raw.R = null;
  if (!e || !e.plant || !e.t) return;
  const m = y.move.m, h = md.hitT[F.act] === undefined ? (e.t[0] + e.t[1]) / 2 : md.hitT[F.act], af = F.af, r = m.r === 'land' ? 8 : m.r;
  const ok = RB.rawOk[F.act] || (RB.rawOk[F.act] = rbRawOk(md, e));
  const time = af <= m.s ? e.t[0] + (h - e.t[0]) * Math.max(0, af) / m.s : af <= m.s + m.a ? h : h + (e.t[1] - h) * Math.min(1, (af - m.s - m.a) / r);
  const W = rbFK(md, mdSample(md, e.c, time, false), RB.W);
  for (const s of e.plant) { if (!ok[s]) continue; const L = RB.leg[s], o = t.rawOf[s]; rbFootOf(W.q[L.ia], L); o.dir.copy(t.dir); o.lift = t.lift; t.raw[s] = o; }
}
function rbRawOk(md, e) {
  const ok = {L: true, R: true}, d0 = {};
  for (let k = 0; k <= 24; k++) {
    const W = rbFK(md, mdSample(md, e.c, e.t[0] + (e.t[1] - e.t[0]) * k / 24, false), RB.W);
    for (const s of ['L', 'R']) {
      rbFootOf(W.q[RB.leg[s].ia], RB.leg[s]);
      if (!k) d0[s] = RB.t.dir.clone(); else if (d0[s].dot(RB.t.dir) < -.866) ok[s] = false;
    }
  }
  return ok;
}
// The planted feet's directions and their balls' places at the start of move F.act (its clip's first pose), once per move.
function rbT0(md, F, S) {
  const id = F.act, key = RB.stance.key;
  if (!RB.t0 || RB.t0.key !== key) RB.t0 = {key, of: {}};
  if (RB.t0.of[id]) return RB.t0.of[id];
  const W = rbFK(md, mdPoseOf(Object.assign({}, F, {af: 0}), S), RB.W), o = {ball: {}, hy: rbYaw(W.q[0])};
  for (const s of ['L', 'R']) { rbFootOf(W.q[RB.leg[s].ia], RB.leg[s]); o[s] = RB.t.dir.clone(); o.ball[s] = W.p[RB.leg[s].it].clone(); }
  return RB.t0.of[id] = o;
}

// Legs of pose p onto their contacts: a standing foot lifts its heel a little when its leg is short, the pelvis comes
// within reach of the legs in contact, then each leg by IK (a free leg stays as the pelvis carries it, above the floor).
function rbLegs(md, p) {
  const t = RB.t, v = t.v, q = t.q, con = RB.con;
  const qH = q[0].fromArray(p.q, 0), h = v[0].fromArray(p.h);
  t.hipF.set(0, 0, 1).applyQuaternion(qH);
  const hip = (s, out) => out.copy(RB.leg[s].tu).applyQuaternion(qH).add(h);
  const ankle = (s, out) => out.copy(con[s].loc).applyQuaternion(con[s].Q).negate().add(con[s].G);
  // a short leg first lifts its heel (smoothly with what is missing: 4 cm = 10 degrees), on standing feet only
  for (const s of ['L', 'R']) {
    const c = con[s], L = RB.leg[s];
    if (c.w < 1 || !c.auto) continue;
    const ex = hip(s, v[5]).distanceTo(ankle(s, v[6])) - (L.a + L.b) * RB.ext;
    if (ex > 0) { const f = v[1].copy(L.tp).applyQuaternion(c.Q).setY(0).normalize(); c.Q.premultiply(q[1].setFromAxisAngle(v[2].crossVectors(RB_UP, f).normalize(), Math.min(12, ex * 250) * RB_R)); }
  }
  // the pelvis within reach of the legs in contact (a foot only partly on its spot, leaving it or coming back to it,
  // has no pull: it reaches as far as its leg does)
  for (let k = 0; k < 4; k++) for (const s of ['L', 'R']) {
    const c = con[s], L = RB.leg[s], pull = rnSm((c.w - .75) / .25);
    if (pull <= 0) continue;
    const d = ankle(s, v[6]).sub(hip(s, v[5])), n = d.length(), ex = n - (L.a + L.b) * RB.ext;
    if (ex > 0) h.addScaledVector(d, ex / n * pull);
  }
  h.toArray(p.h);
  // each leg: on its contact; partly free (a foot leaving or coming back to its spot: it steps, a little off the
  // floor); or free, as the pelvis carries the clip's leg. No foot under the floor, none tilted on its edge near it.
  for (const s of ['L', 'R']) {
    const c = con[s], L = RB.leg[s], A = hip(s, v[5]), tgt = c.T, Qf = q[5];
    const qU = q[1].copy(qH).multiply(q[2].fromArray(p.q, L.iu * 4)), knee = v[7].fromArray(md.bones[L.il].t).applyQuaternion(qU).add(A);
    const qL = q[2].copy(qU).multiply(q[3].fromArray(p.q, L.il * 4)), fa = v[8].fromArray(md.bones[L.ia].t).applyQuaternion(qL).add(knee);
    if (c.w >= 1) { ankle(s, tgt); Qf.copy(c.Q); }
    else {
      Qf.copy(qL).multiply(q[3].fromArray(p.q, L.ia * 4));   // the carried foot
      if (c.w > 0) {
        const far = Math.hypot(ankle(s, tgt).x - fa.x, tgt.z - fa.z);   // a foot that travels steps: off the floor by how far it goes
        tgt.lerpVectors(fa, tgt, c.w); Qf.slerp(c.Q, c.w); tgt.y += Math.min(.05, .3 * far) * Math.sin(Math.PI * c.w);
      } else tgt.copy(fa);
      const lf = RB.lf;
      if (lf && lf.s === s) { tgt.x += lf.x * (1 - c.w); tgt.y += lf.y * (1 - c.w); tgt.z += lf.z * (1 - c.w); }   // the kick's foot into its box
    }
    if (!c.flat || c.w < 1) {
      const fl = RB.floor, ball = v[6].copy(L.tb).applyQuaternion(Qf).add(tgt), near = 1 - rnSm((ball.y - fl - L.ball) / .14);
      if (near > 0) {   // near the floor: the sole's sideways tilt taken out
        const f = v[1].copy(L.tb).applyQuaternion(Qf).setY(0), n = v[2].copy(L.up).applyQuaternion(Qf);
        if (f.lengthSq() > 1e-6) { f.normalize(); Qf.premultiply(q[3].setFromAxisAngle(f, Math.atan2(n.dot(v[3].crossVectors(RB_UP, f)), n.y) * near)); ball.copy(L.tb).applyQuaternion(Qf).add(tgt); }
      }
      const low = Math.max(L.ball + fl - ball.y, fl - (v[1].copy(L.tp).applyQuaternion(Qf).y + tgt.y), .07 + fl - tgt.y);   // ball, toe tip and ankle above the floor
      if (low > 0) tgt.y += low;
    }
    rbIK(md, p, L, qH, A, tgt, Qf, qU, qL, knee, fa, c.w >= 1 && !!c.flat, c.loc === L.tp ? c.w : 0);   // (the clip's own foot: its knee is right)
  }
}

// The side the knee of a carried leg bends to once the leg points at its target (dir, unit, from the hip joint A):
// where its own knee lies off its hip-ankle line, swung with the leg (R = that swing, set here); a straight carried
// leg has none: then forward of the thigh's hinge. Unit, across dir.
function rbPole(L, A, dir, qU, knee, ank, R, P) {
  const T = THREE, cd = new T.Vector3().subVectors(ank, A).normalize();
  R.setFromUnitVectors(cd, dir);
  P.subVectors(knee, A); P.addScaledVector(cd, -P.dot(cd));
  const off = rnSm((P.length() - .03) / .09), Ph = new T.Vector3().crossVectors(dir, L.hu.clone().applyQuaternion(qU).applyQuaternion(R));
  if (Ph.lengthSq() < 1e-8) Ph.set(0, 0, 1).addScaledVector(dir, -dir.z);
  Ph.normalize();
  if (off > 1e-4) P.applyQuaternion(R).normalize().multiplyScalar(off).addScaledVector(Ph, 1 - off); else P.copy(Ph);
  if (P.lengthSq() < 1e-8) P.copy(Ph);
  return P.addScaledVector(dir, -P.dot(dir)).normalize();
}

// One leg by IK, from the leg as the pelvis carries it (qU, qL = its thigh's and shin's rotations, knee, ank = its
// knee and ankle): hip joint A, ankle target tgt, the foot's rotation Qf. The carried leg is swung as one piece so that
// it points at the target (its own twist and the side its knee bends to are kept), a foot on the floor then turns it
// about that line to bring the knee within 40 degrees of its toes (by the contact's weight w; a free leg keeps the
// clip's knee), and the knee opens or closes to the target's distance. Solving an already solved leg changes
// nothing. rigid = the shoe keeps its rest shape (a pinned foot turns on its toe tip as one piece: bent at the toes
// this boot folds badly).
function rbIK(md, p, L, qH, A, tgt, Qf, qU, qL, knee, ank, rigid, w) {
  const T = THREE, a = L.a, b = L.b;
  const dir = new T.Vector3().subVectors(tgt, A), full = dir.length(), d = Math.max(Math.abs(a - b) + 1e-3, Math.min((a + b) * .999, full));
  dir.multiplyScalar(1 / (full || 1e-9));
  const R = new T.Quaternion(), P = rbPole(L, A, dir, qU, knee, ank, R, new T.Vector3());
  if (w > 0) {
    // a foot on the floor: the knee within 40 degrees of its toes, on the side it was; one that pointed nearly opposite
    // the toes (no side to choose) goes over them. Continuous everywhere: no side that flips.
    // (the toes' way: the sole's direction on the floor, across the leg; the ankle-to-ball line runs nearly along a bent
    // leg and its part across the leg flips side as they pass parallel)
    const Pf = L.sd.clone().applyQuaternion(Qf).setY(0); Pf.addScaledVector(dir, -Pf.dot(dir));
    if (Pf.lengthSq() > .04) {
      Pf.normalize();
      // angles about the leg's line, from the toes: the knee's (aP) and the hips' forward (aH). In a punch (weight k)
      // the knee goes toward the hips' way (60% of it from the toes, a rear knee driving in with the punch) within 15
      // degrees; else within 40 degrees of the toes.
      const sa = (a, b) => Math.atan2(new T.Vector3().crossVectors(a, b).dot(dir), a.dot(b));
      const Hf = RB.t.hipF.clone(); Hf.addScaledVector(dir, -Hf.dot(dir));
      const aP = sa(Pf, P), aH = Hf.lengthSq() > .04 ? sa(Pf, Hf.normalize()) : 0, k = RB.sty.knee;
      const c = k * Math.max(-.8, Math.min(.8, .6 * aH)) * (1 - rnSm((Math.abs(aH) - 2.4) / .6)), tol = (40 - 25 * k) * RB_R;
      const g = rnSm((Math.abs(aP) - 2.5) / .5), want = Math.max(c - tol, Math.min(c + tol, aP)) * (1 - g) + c * g, turn = (want - aP) * w;
      if (Math.abs(turn) > 1e-5) { const tw = new T.Quaternion().setFromAxisAngle(dir, turn); P.applyQuaternion(tw); R.premultiply(tw); }
    }
  }
  const cos = (a * a + d * d - b * b) / (2 * a * d), sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  const B = A.clone().addScaledVector(dir, a * cos).addScaledVector(P, a * sin), end = A.clone().addScaledVector(dir, d);
  const d1 = new T.Quaternion().setFromUnitVectors(new T.Vector3().subVectors(knee, A).applyQuaternion(R).normalize(), new T.Vector3().subVectors(B, A).normalize()).multiply(R);
  const d2 = new T.Quaternion().setFromUnitVectors(new T.Vector3().subVectors(ank, knee).applyQuaternion(d1).normalize(), end.sub(B).normalize());
  const nU = d1.clone().multiply(qU), nL = d2.multiply(d1).multiply(qL), inv = new T.Quaternion();
  inv.copy(qH).invert().multiply(nU).toArray(p.q, L.iu * 4);
  inv.copy(nU).invert().multiply(nL).toArray(p.q, L.il * 4);
  inv.copy(nL).invert().multiply(Qf).toArray(p.q, L.ia * 4);
  if (rigid) L.toe.toArray(p.q, L.it * 4);
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
  const n = m ? Math.min(CFG.anim.strikeIn, m.s - 1) : hit ? RB.hitBlend : {getup: 1, rollF: 1, rollB: 1}[F.act] ? 4 : RB.blend;
  if (F !== it.F) it.from = null;
  else if (F.act !== it.act || F.af < it.af - .5) {
    it.from = n > 0 ? it.pose : null; it.fromPin = it.pin; it.fromW = it.conW ? Object.assign({}, it.conW) : null;
    it.fromG = it.conG ? {L: it.conG.L.clone(), R: it.conG.R.clone()} : null;
  }
  if (it.from && F.af < n) {
    const k = rnSm(Math.max(0, F.af) / n), con = RB.con, sav = RB.sav, same = pol === 'pin' && it.fromPin;
    for (const s of ['L', 'R']) { sav[s].w = con[s].w; sav[s].G.copy(con[s].G); }
    p = mdMix(it.from, p, k);
    if (pol !== 'none') {
      const W = rbFK(md, p, RB.W);
      for (const s of ['L', 'R']) {
        const L = RB.leg[s], c = con[s];
        // a foot that was on its spot stays there; one that was in the air (a kick cut by the next move) comes down
        // over the ease, not at once; a pose from elsewhere settles onto the new contacts as the ease advances
        const w0 = same ? (it.fromW ? it.fromW[s] : 1) : 0;
        c.w = w0 + (sav[s].w - w0) * k; c.flat = null; c.auto = false;   // (c.loc: the new pose's pinned point)
        c.Q.copy(W.q[L.ia]); c.G.copy(sav[s].G);
        if (same && it.fromG) c.G.lerpVectors(it.fromG[s], sav[s].G, k);   // (a foot turned on its ball turns back over the ease)
      }
      rbLegs(md, p);
    }
  }
  it.pin = pol === 'pin'; it.conW = it.conW || {}; it.conW.L = RB.con.L.w; it.conW.R = RB.con.R.w;
  it.conG = it.conG || {L: new THREE.Vector3(), R: new THREE.Vector3()}; it.conG.L.copy(RB.con.L.G); it.conG.R.copy(RB.con.R.G);
  return p;
};

// --- Smear ("Allungo"): the hitting forearm or shin stretched along itself just before the impact (about 3 frames),
// thinner as it gets longer; on the first active frame it has its true size again (the hit is exact). ---
RN.hooks.boot.push(() => rnOpt('smear', 'Allungo', false));   // off until Denis asks for it: a stretched limb reads as a distortion
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
