// --- style.js: Ren's own way of standing (stage 1 of "make him unique", 11/11/2026; hand-made, no new clips). ---
// The "flowing water" guard: open hands, the lead (left) hand reaching toward the opponent with its fingers up and its
// palm turned in, the rear hand open in front of the chest; both trace slow circles, opposite in phase, riding the
// bounce of the stance. The guard holds while he walks. Standing still, now and then he does something of his own:
// tightens the bandage of his lead forearm, or rolls his neck. On the way back from a move the arms flow into it.
// Arms by a two-bone IK from the clip's arm (its twist kept), the forearm rolling toward the palm's way, the hand set
// to its fingers' and palm's directions. Targets in the fight-line frame: origin the chest, forward = toward the
// opponent (RB_LINE), up, side = his left.

const RS = {
  // hand targets (metres from the chest: [forward, up, side]), fingers' and palm's ways ([forward, up, side]), elbow
  // hint ([forward, up, side]): lead = left, rear = right
  lead: {pos: [.46, .05, .03], fing: [.55, .8, -.1], palm: [0, 0, -1], elbow: [0, -1, .45]},
  rear: {pos: [.2, -.04, .02], fing: [.45, .25, .85], palm: [.3, -.9, 0], elbow: [-.1, -1, -.35]},
  flow: {period: 150, lead: .035, rear: .028},   // the hands' slow circles: frames per turn, radius (m)
  fidget: {first: 120, every: 220, len: [66, 54]},   // frames: when the first comes, how often, how long (bandage, neck)
  // palm normals in each hand's own frame (from the fist curl's direction: the fingers fold toward the palm)
  palmL: new THREE.Vector3(.78, 0, .62).normalize(), palmR: new THREE.Vector3(-.79, 0, .61).normalize(),
  open: ['idle', 'intro', 'walkF', 'walkB', 'guard', 'guardC', 'block'],
  t: {v: [0, 1, 2, 3, 4, 5, 6, 7].map(() => new THREE.Vector3()), q: [0, 1, 2, 3, 4].map(() => new THREE.Quaternion()), m: new THREE.Matrix4()},
};
const RS_UP = new THREE.Vector3(0, 1, 0), RS_SIDE = new THREE.Vector3().crossVectors(RS_UP, RB_LINE).normalize();
// [forward, up, side] in the fight-line frame -> a model-space vector (out)
function rsVec(a, out) { return out.copy(RB_LINE).multiplyScalar(a[0]).addScaledVector(RS_UP, a[1]).addScaledVector(RS_SIDE, a[2]); }

// Arm s ('L' | 'R') of pose p (W its forward kinematics) toward wrist target tgt, elbow hint eh, fingers' way fd and
// palm's way pn (model space, unit), by weight w (0 = the clip's arm).
function rsArm(md, p, W, s, tgt, eh, fd, pn, w) {
  if (w <= 0) return;
  const n = s === 'L' ? 'Left' : 'Right', ix = md.index, iS = ix[n + 'Shoulder'], iA = ix[n + 'Arm'], iF = ix[n + 'ForeArm'], iH = ix[n + 'Hand'];
  const T = THREE, A = W.p[iA].clone(), E = W.p[iF].clone(), H = W.p[iH].clone(), qU = W.q[iA].clone(), qL = W.q[iF].clone(), qHl = new T.Quaternion().fromArray(p.q, iH * 4);
  const a = A.distanceTo(E), b = E.distanceTo(H), goal = H.clone().lerp(tgt, w);
  const dir = goal.clone().sub(A), full = dir.length(), d = Math.max(Math.abs(a - b) + 1e-3, Math.min((a + b) * .995, full));
  dir.multiplyScalar(1 / (full || 1e-9));
  const cd = H.clone().sub(A).normalize(), R = new T.Quaternion().setFromUnitVectors(cd, dir);
  // the elbow's side: the clip's (swung with the arm) toward the hint, by w
  const Pc = E.clone().sub(A); Pc.addScaledVector(cd, -Pc.dot(cd)); if (Pc.lengthSq() > 1e-8) Pc.normalize().applyQuaternion(R);
  const Ph = eh.clone().addScaledVector(dir, -eh.dot(dir)); if (Ph.lengthSq() > 1e-8) Ph.normalize();
  const P = Pc.multiplyScalar(1 - w).add(Ph.multiplyScalar(w)); P.addScaledVector(dir, -P.dot(dir));
  if (P.lengthSq() < 1e-8) P.set(0, -1, 0).addScaledVector(dir, dir.y);
  P.normalize();
  const cos = (a * a + d * d - b * b) / (2 * a * d), sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  const B = A.clone().addScaledVector(dir, a * cos).addScaledVector(P, a * sin), end = A.clone().addScaledVector(dir, d);
  const d1 = new T.Quaternion().setFromUnitVectors(E.clone().sub(A).normalize(), B.clone().sub(A).normalize());
  const d2 = new T.Quaternion().setFromUnitVectors(H.clone().sub(E).applyQuaternion(d1).normalize(), end.clone().sub(B).normalize());
  const nU = d1.clone().multiply(qU), nL = d2.multiply(d1).multiply(qL);
  // the forearm rolls 60% of the way the palm must turn (about its own line); the wrist does the rest
  const palmLoc = s === 'L' ? RS.palmL : RS.palmR, ax = end.clone().sub(B).normalize();
  const cur = palmLoc.clone().applyQuaternion(nL.clone().multiply(qHl)); cur.addScaledVector(ax, -cur.dot(ax));
  const want = pn.clone().addScaledVector(ax, -pn.dot(ax));
  if (cur.lengthSq() > 1e-6 && want.lengthSq() > 1e-6) {
    cur.normalize(); want.normalize();
    const th = Math.atan2(new T.Vector3().crossVectors(cur, want).dot(ax), cur.dot(want));
    nL.premultiply(new T.Quaternion().setFromAxisAngle(ax, .6 * th * w));
  }
  // the hand: fingers along fd, palm toward pn (as a basis), from the forearm's hand by w
  const f = fd.clone().normalize(), pnn = pn.clone().addScaledVector(f, -pn.dot(f)).normalize();
  const lf = new T.Vector3(0, 1, 0), lp = palmLoc.clone().addScaledVector(lf, -palmLoc.dot(lf)).normalize();
  const Mw = new T.Matrix4().makeBasis(f, pnn, new T.Vector3().crossVectors(f, pnn)), Ml = new T.Matrix4().makeBasis(lf, lp, new T.Vector3().crossVectors(lf, lp));
  const qWant = new T.Quaternion().setFromRotationMatrix(Mw.multiply(Ml.transpose()));
  const qHw = nL.clone().multiply(qHl).slerp(qWant, w);
  const inv = new T.Quaternion();
  inv.copy(W.q[iS]).invert().multiply(nU).toArray(p.q, iA * 4);
  inv.copy(nU).invert().multiply(nL).toArray(p.q, iF * 4);
  inv.copy(nL).invert().multiply(qHw).toArray(p.q, iH * 4);
}

// How much of the guard style the act takes (0..1): standing and walking all of it, a move's way back as it eases into
// the stance (y.back), nothing else.
function rsWeight(F, y) {
  if (F.air) return 0;
  if ({idle: 1, intro: 1, walkF: 1, walkB: 1}[F.act]) return 1;
  if (y.move && y.backTo === 'idle') return y.back;
  return 0;
}

// The fidget at idle frame af: {kind: 0 bandage | 1 neck, u: 0..1 through it} or null. A pure function of af.
function rsFidget(F) {
  if (F.act !== 'idle' && F.act !== 'intro') return null;
  const fg = RS.fidget, x = F.af - fg.first;
  if (x < 0) return null;
  const k = Math.floor(x / fg.every), kind = k % 2, t = x - k * fg.every, len = fg.len[kind];
  return t < len ? {kind, u: t / len} : null;
}

RB.post.push((md, p, F, S, y) => {
  const w = rsWeight(F, y);
  if (w <= 0) return;
  const W = rbFK(md, p, RB.W), ix = md.index, v = RS.t.v, t = S.frame + 23 * F.side;
  const O = W.p[ix.Spine].clone();
  const ph = 2 * Math.PI * t / RS.flow.period, fid = rsFidget(F);
  // the guard's targets with the flow's circles (lead clockwise in the side-up plane, rear the other way)
  const L = RS.lead, Rr = RS.rear;
  const lp = rsVec(L.pos, v[0]).add(O).addScaledVector(RS_SIDE, RS.flow.lead * Math.cos(ph)).addScaledVector(RS_UP, RS.flow.lead * Math.sin(ph));
  const rp = rsVec(Rr.pos, v[1]).add(O).addScaledVector(RS_SIDE, -RS.flow.rear * Math.cos(ph + .8)).addScaledVector(RS_UP, RS.flow.rear * Math.sin(ph + .8));
  const lf = rsVec(L.fing, v[2]).applyAxisAngle(RB_LINE, .12 * Math.sin(ph)).normalize(), lpn = rsVec(L.palm, v[3]).normalize();
  const rf = rsVec(Rr.fing, v[4]).normalize(), rpn = rsVec(Rr.palm, v[5]).normalize();
  let le = rsVec(L.elbow, new THREE.Vector3()).normalize(), re = rsVec(Rr.elbow, new THREE.Vector3()).normalize();
  if (fid && fid.kind === 0) {   // the bandage: the lead forearm comes in across the chest, the rear hand grips it and pulls twice toward the wrist
    const e = Math.sin(Math.PI * Math.min(1, fid.u * 1.15)) ** .6;   // in, hold, out
    lp.lerp(rsVec([.3, -.06, -.04], new THREE.Vector3()).add(O), e);
    lf.lerp(rsVec([.25, .35, -.9], new THREE.Vector3()).normalize(), e).normalize();
    lpn.lerp(rsVec([.1, -.95, 0], new THREE.Vector3()).normalize(), e).normalize();
    const pull = Math.max(0, Math.sin(4 * Math.PI * Math.min(1, Math.max(0, (fid.u - .25) / .55))));   // two pulls
    rp.lerp(lp.clone().add(rsVec([-.03, .02, .16 - .1 * pull], new THREE.Vector3())), e);
    rf.lerp(rsVec([.2, -.2, .95], new THREE.Vector3()).normalize(), e).normalize();
    rpn.lerp(rsVec([-.2, -.95, .1], new THREE.Vector3()).normalize(), e).normalize();
  }
  rsArm(md, p, W, 'L', lp, le, lf, lpn, w);
  rsArm(md, p, rbFK(md, p, RB.W), 'R', rp, re, rf, rpn, w);
  if (fid && fid.kind === 1) {   // the neck: a slow roll, down to one side, around, up on the other, the eyes back on the opponent
    const e = Math.sin(Math.PI * fid.u), a = 2 * Math.PI * fid.u;
    mdBoneTurn(p, ix.Head, MD_X, 14 * e * Math.max(0, Math.sin(a)));     // (down)
    mdBoneTurn(p, ix.Head, new THREE.Vector3(0, 0, 1), 22 * e * Math.cos(a / 2));   // (side to side)
    mdBoneTurn(p, ix.neck, new THREE.Vector3(0, 0, 1), 8 * e * Math.cos(a / 2));
  }
});

RN.hooks.boot.push(VW => {
  const lk = CFG.looks.ren;
  for (const a of RS.open) if (!lk.openHands.includes(a)) lk.openHands.push(a);
  VW_PLAYS[0][1][0][1] = 480;   // the viewer's guard lasts long enough to show both fidgets
});
RN.hooks.opt.push((k, v) => {   // the old animation: fists as the page had them
  if (k !== 'on') return;
  const lk = CFG.looks.ren;
  lk.openHands = v ? lk.openHands.concat(RS.open.filter(a => !lk.openHands.includes(a))) : lk.openHands.filter(a => !RS.open.includes(a));
});
