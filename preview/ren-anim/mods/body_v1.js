// --- body_v1.js: the first style layer (published 11/11/2026, v1), kept only as the baseline to compare against. ---
Object.assign(RN, {H: 1,
  moves: {
    p1: {tw: 7, lean: 5, dip: .012, coil: .8}, p2: {tw: 10, lean: 7, dip: .015, coil: .9}, p3: {tw: 14, lean: 6, dip: .02, coil: 1},
    hp: {tw: 20, lean: 11, dip: .035, coil: 1.2}, k1: {tw: 9, lean: -5, dip: .008, coil: .8}, k2: {tw: 14, lean: -7, dip: .01, coil: 1},
    hk: {tw: 22, lean: -9, dip: .015, coil: 1.3}, cp: {tw: 8, lean: 7, dip: .01, coil: .8}, ck: {tw: 10, lean: 6, dip: .01, coil: .9},
    chp: {tw: 12, lean: -9, dip: .045, coil: 1.1}, chk: {tw: 12, lean: -11, dip: .03, coil: 1},
    jp: {tw: 8, lean: 6, dip: 0, coil: .8}, jk: {tw: 10, lean: 6, dip: 0, coil: .9}, jhp: {tw: 14, lean: 10, dip: 0, coil: 1}, jhk: {tw: 14, lean: 8, dip: 0, coil: 1},
    spec: {tw: 18, lean: 12, dip: .04, coil: 1.4, s: 14, a: 4, r: 30}, thr: {tw: 10, lean: 9, dip: .02, coil: .8, s: 4, a: 2, r: 24},
  },
  blend: 6, hitBlend: 3,   // frames: easing into a new free act / into a hit reaction
  tmp: {q: [0, 1, 2].map(() => new THREE.Quaternion()), v: [0, 1].map(() => new THREE.Vector3()), m: new THREE.Matrix4()},
});

// The move's style curve at frame af: 0 -> -1 (coil, first 60% of startup) -> +1 (the impact) held through the
// active frames -> a damped wave back to 0 over the recovery.
function rnCurve(af, m) {
  const s = Math.max(1, m.s), a = m.a, r = m.r === 'land' ? 14 : m.r;
  if (af <= 0) return 0;
  if (af <= s) { const u = af / s; return u < .6 ? -rnSm(u / .6) : -1 + 2 * rnSm((u - .6) / .4); }
  if (af <= s + a) return 1;
  const v = Math.min(1, (af - s - a) / r);
  return Math.exp(-3.5 * v) * Math.cos(2.6 * Math.PI * v) * (1 - v);
}

// Turns bone i of p by deg about a model-space axis (its children follow).
function rnTurn(md, p, i, axis, deg) {
  const T = RN.tmp, par = md.bones[i].p;
  const pw = par < 0 ? T.q[0].identity() : T.q[0].setFromRotationMatrix(mdWorld(md, p, par, T.m));
  T.q[1].setFromAxisAngle(axis, deg * F3_DEG);
  T.q[2].copy(pw).invert().multiply(T.q[1]).multiply(pw).multiply(MD_QA.fromArray(p.q, i * 4)).toArray(p.q, i * 4);
}

// The planted feet of p (ankle near the floor of the rest pose): [leg, position, world rotation].
function rnFeet(md, p) {
  const out = [];
  for (const leg of ['L', 'R']) {
    const w = mdWorld(md, p, md.index[leg === 'L' ? 'LeftFoot' : 'RightFoot'], new THREE.Matrix4()), pos = new THREE.Vector3().setFromMatrixPosition(w);
    if (pos.y < RN.ankle + .05 * RN.H) out.push([leg, pos.toArray(), new THREE.Quaternion().setFromRotationMatrix(w)]);
  }
  return out;
}

// Ren's layer on pose p (facing right) for fighter F; md = the package.
function rnStyle(md, p, F, S) {
  if (RN.ankle === undefined) { const r = mdRest(md); RN.H = md.meta.height; RN.ankle = new THREE.Vector3().setFromMatrixPosition(mdWorld(md, r, md.index.LeftFoot, new THREE.Matrix4())).y; }
  const ix = md.index, H = RN.H, t = S.frame + 23 * F.side, act = F.act;
  const feet = F.air ? [] : rnFeet(md, p);
  let tw = 0, lean = 0, dip = 0, head = 0, hipTw = 0;
  const st = RN.moves[act], m = st && (st.s ? st : CFG.moves[act]);
  if (st && m) {
    const k = rnCurve(F.af, m), e = (CFG.clips[act] || {}), limb = e.limb || (e.up && e.up.limb) || (CFG.moves[act] || {}).limb || 'handR';
    const side = /R$/.test(limb) ? 1 : -1;
    tw = st.tw * side * (k < 0 ? k * st.coil : k);
    lean = st.lean * (k < 0 ? .35 * k : k);   // coiling leans a little the other way
    dip = st.dip * Math.abs(k) * H; hipTw = tw * .35;
  } else switch (act) {
    case 'idle': case 'intro': case 'guard': {   // the flowing stance: a slow figure-eight of the hips, the shoulders following late
      const a = Math.sin(t * .075), b = Math.sin(t * .15 + .6);
      tw = 3.5 * a; hipTw = -1.5 * a; dip = (.008 + .006 * b) * H; lean = 1.5 * b; head = -1.2 * Math.sin(t * .075 - .8);
      break;
    }
    case 'crouch': case 'guardC': tw = 2.5 * Math.sin(t * .075); dip = .004 * H * (1 + Math.sin(t * .15)); break;
    case 'walkF': lean = 6; tw = 4 * Math.sin(F.x / 1000 * 4.4); break;
    case 'walkB': lean = -2; tw = -3 * Math.sin(F.x / 1000 * 4.4); break;
    case 'dashF': { const u = rnSm(F.af / 5) * (1 - rnSm((F.af - 12) / 6)); lean = 16 * u; dip = .03 * H * u; break; }
    case 'dashB': { const u = rnSm(F.af / 5) * (1 - rnSm((F.af - 12) / 8)); lean = -9 * u; dip = .02 * H * u; break; }
    case 'jumpSquat': dip = .03 * H * rnSm(F.af / 3); lean = 4; break;
    case 'landing': { const u = Math.exp(-F.af / 3.5) * (1 - Math.exp(-F.af * 1.4)); dip = .09 * H * u; lean = 8 * u; break; }
    case 'air': { const u = mdUp((CFG.jump.v - F.vy) / (2 * CFG.jump.v)); lean = 6 - 10 * u; break; }   // rising: forward, falling: opening up
    case 'hitStun': case 'thrown': { const u = Math.exp(-F.af / 5); lean = -12 * u; head = -14 * u; tw = -6 * u; dip = .02 * H * u; break; }
    case 'block': { const u = Math.exp(-F.af / 4); lean = -6 * u; dip = .025 * H * u; head = 6 * u; break; }
  }
  if (hipTw) mdHipsTurn(p, MD_Y, hipTw, false);
  if (lean) mdHipsTurn(p, MD_X, lean, false);
  if (tw) { rnTurn(md, p, ix.Spine02, MD_Y, (tw - hipTw) * .45); rnTurn(md, p, ix.Spine01, MD_Y, (tw - hipTw) * .55); }
  if (lean < 0 && !F.air) rnTurn(md, p, ix.Spine01, MD_X, lean * -.3);   // a lean back bends the back, not just the hips
  if (head) mdBoneTurn(p, ix.Head, MD_X, head);
  if (dip) p.h[1] -= dip;
  for (const [leg, pos, q] of feet) mdLegIK(md, p, leg, pos, q);
  if (!F.air && !RN_LYING[act]) rnFloor(md, p);
  return p;
}
const RN_LYING = {knock: 1, ko: 1, juggle: 1, getup: 1, rollF: 1, rollB: 1};
// No ankle under the rest pose's ankle height: a foot pushed into the floor (by the dip or a blend) is lifted back by IK.
function rnFloor(md, p) {
  for (const leg of ['L', 'R']) {
    const w = mdWorld(md, p, md.index[leg === 'L' ? 'LeftFoot' : 'RightFoot'], new THREE.Matrix4()), pos = new THREE.Vector3().setFromMatrixPosition(w);
    if (pos.y < RN.ankle - .002 * RN.H) { pos.y = RN.ankle; mdLegIK(md, p, leg, pos.toArray(), new THREE.Quaternion().setFromRotationMatrix(w)); }
  }
}


RN.moveT = (t, m, af, hit) => {
  const h = hit === undefined ? (t[0] + t[1]) / 2 : hit;
  if (af <= m.s) return t[0] + (h - t[0]) * Math.pow(Math.max(0, af) / m.s, 1.5);
  if (af <= m.s + m.a) return h;
  const v = Math.min(1, (af - m.s - m.a) / (m.r === 'land' ? 8 : m.r));
  return h + (t[1] - h) * (1 - (1 - v) * (1 - v));
};
RN.pure = (md, F, S) => rnStyle(md, mdPoseOf(F, S) || mdRest(md), F, S);
RN.pose = (it, F, S) => {
  const md = mdData(it.key), m = CFG.moves[F.act] || (F.act === 'spec' ? RN.moves.spec : null);
  const hit = {hitStun: 1, block: 1, thrown: 1, knock: 1, juggle: 1}[F.act];
  const n = m ? Math.min(CFG.anim.strikeIn, m.s - 1) : hit ? RN.hitBlend : {getup: 1, rollF: 1, rollB: 1}[F.act] ? 0 : RN.blend;
  let p = RN.pure(md, F, S);
  if (F !== it.F) it.from = null;
  else if (F.act !== it.act || F.af < it.af) it.from = n > 0 ? it.pose : null;
  if (it.from && F.af < n) {
    const feet = F.air || RN_LYING[F.act] ? [] : rnFeet(md, p);
    p = mdMix(it.from, p, rnSm(Math.max(0, F.af) / n));
    for (const [leg, pos, q] of feet) mdLegIK(md, p, leg, pos, q);
    if (!F.air && !RN_LYING[F.act]) rnFloor(md, p);
  }
  return p;
};
