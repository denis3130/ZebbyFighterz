// --- style.js: Ren's own way of standing (stage 1 of "make him unique", 11/11/2026; hand-made, no new clips). ---
// Ren's guard (preset B, chosen by Denis among A/B/C): half-open hands, the lead (left) hand at chin level a little
// in front, the rear hand by the chin; both trace small slow circles, opposite in phase, riding the bounce of the
// stance. The guard holds while he walks. Standing still, now and then he rolls his neck. On the way back from a
// move the arms flow into it. (The bandage-tightening fidget was removed at Denis's request, 11/11/2026.)
// Arms by a two-bone IK from the clip's arm (its twist kept), the forearm rolling toward the palm's way, the hand set
// to its fingers' and palm's directions. The lead hand's targets are in the fight-line frame (origin the chest,
// forward = toward the opponent, RB_LINE, up, side = his left); the rear hand's in the chest's own frame (Spine01:
// across = his left, up, forward = the way the chest faces): Ren stands three-quarters on, and the fight line from his
// chest runs through his own side. No arm point goes into the chest: wrist and elbow are pushed out of it (RS.torso).

const RS = {
  // hand targets (metres from the chest: [forward, up, side]), fingers' and palm's ways ([forward, up, side]), elbow
  // hint ([forward, up, side]): lead = left, rear = right
  // rear: in the chest frame [across, up, forward]. curl = how closed the hands are (0 open .. 1 fist), armW = how much
  // of the arms is this guard (0: the clip's). Set by a preset (RS.presets, rsPreset).
  lead: null, rear: null, curl: 0, armW: 1,
  presets: {
    // A: a fighter's real guard, hands loosely closed: lead hand at eye level a forearm in front of the face, rear hand
    // by the cheek, elbows in over the ribs
    A: {curl: .78, armW: 1, flow: {period: 150, lead: .018, rear: .012},
      lead: {pos: [.3, .14, .01], fing: [.55, .8, -.15], palm: [0, -.25, -1], elbow: [0, -1, .25]},
      rear: {pos: [-.07, .21, .2], fing: [.15, .95, .25], palm: [.9, 0, .4], elbow: [-.2, -1, .2]}},
    // B: half-open hands, a little more reach in the lead hand, at chin level
    B: {curl: .5, armW: 1, flow: {period: 150, lead: .025, rear: .018},
      lead: {pos: [.38, .09, .02], fing: [.55, .8, -.12], palm: [0, -.2, -1], elbow: [0, -1, .35]},
      rear: {pos: [-.05, .18, .25], fing: [.25, .92, .2], palm: [.85, 0, .5], elbow: [-.35, -1, .15]}},
    // C: the clip's boxing guard (fists), only the stance's own bounce
    C: {curl: 1, armW: 0, flow: {period: 150, lead: 0, rear: 0}},
    // O: the open hands of the first proposal
    O: {curl: 0, armW: 1, flow: {period: 150, lead: .035, rear: .028},
      lead: {pos: [.46, .05, .03], fing: [.55, .8, -.1], palm: [0, 0, -1], elbow: [0, -1, .45]},
      rear: {pos: [-.05, .17, .32], fing: [.35, .9, .15], palm: [.75, 0, .65], elbow: [-.55, -1, .1]}},
  },
  // the chest as an ellipse in the Spine01 frame (m): half-width, front, back, from Spine02 - lo to neck; arm radius
  torso: {w: .16, front: .13, back: .15, lo: .05, arm: .045},
  flow: {period: 150, lead: .035, rear: .028},   // the hands' slow circles: frames per turn, radius (m)
  fidget: {first: 120, every: 220, len: 54},   // frames: when the neck roll first comes, how often, how long
  // palm normals in each hand's own frame (from the fist curl's direction: the fingers fold toward the palm)
  palmL: new THREE.Vector3(.78, 0, .62).normalize(), palmR: new THREE.Vector3(-.79, 0, .61).normalize(),
  open: ['idle', 'intro', 'walkF', 'walkB', 'guard', 'guardC', 'block'],
  t: {v: [0, 1, 2, 3, 4, 5, 6, 7].map(() => new THREE.Vector3()), q: [0, 1, 2, 3, 4].map(() => new THREE.Quaternion()), m: new THREE.Matrix4()},
};
const RS_UP = new THREE.Vector3(0, 1, 0), RS_SIDE = new THREE.Vector3().crossVectors(RS_UP, RB_LINE).normalize();
// [forward, up, side] in the fight-line frame -> a model-space vector (out)
function rsVec(a, out) { return out.copy(RB_LINE).multiplyScalar(a[0]).addScaledVector(RS_UP, a[1]).addScaledVector(RS_SIDE, a[2]); }
// [across, up, forward] in the chest frame (W: the pose's forward kinematics) -> a model-space vector (out)
function rsChest(md, W, a, out) { return out.set(a[0], a[1], a[2]).applyQuaternion(W.q[md.index.Spine01]); }
// Point pt (model space) out of the chest's ellipse inflated by the arm's radius (and extra m): moved outward across
// the chest's up axis; true when it moved.
function rsOut(md, W, pt, extra) {
  const ix = md.index, C = W.p[ix.Spine01], q = RS.t.q[4].copy(W.q[ix.Spine01]).invert(), l = RS.t.v[7].copy(pt).sub(C).applyQuaternion(q), o = RS.torso;
  const lo = RS.t.v[6].copy(W.p[ix.Spine02]).sub(C).applyQuaternion(q).y - o.lo, hi = RS.t.v[6].copy(W.p[ix.neck]).sub(C).applyQuaternion(q).y;
  if (l.y < lo || l.y > hi) return false;
  const m = o.arm + (extra || 0), rx = o.w + m, rz = (l.z > 0 ? o.front : o.back) + m, k = Math.hypot(l.x / rx, l.z / rz);
  if (k >= 1) return false;
  if (k < 1e-4) l.z = rz; else { l.x /= k; l.z /= k; }
  pt.copy(l.applyQuaternion(q.invert())).add(C);
  return true;
}

// Arm s ('L' | 'R') of pose p (W its forward kinematics) toward wrist target tgt, elbow hint eh, fingers' way fd and
// palm's way pn (model space, unit), by weight w (0 = the clip's arm).
function rsArm(md, p, W, s, tgt, eh, fd, pn, w) {
  if (w <= 0) return;
  const n = s === 'L' ? 'Left' : 'Right', ix = md.index, iS = ix[n + 'Shoulder'], iA = ix[n + 'Arm'], iF = ix[n + 'ForeArm'], iH = ix[n + 'Hand'];
  const T = THREE, A = W.p[iA].clone(), E = W.p[iF].clone(), H = W.p[iH].clone(), qU = W.q[iA].clone(), qL = W.q[iF].clone(), qHl = new T.Quaternion().fromArray(p.q, iH * 4);
  const a = A.distanceTo(E), b = E.distanceTo(H), goal = H.clone().lerp(tgt, w);
  rsOut(md, W, goal, .02);   // (the hand's own thickness)
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
  // an elbow (or the forearm's middle) inside the chest: the elbow turns about the shoulder-wrist line until it is out
  for (let k = 0; k < 12; k++) {
    const mid = B.clone().lerp(end, .5), inB = rsOut(md, W, B.clone()), inM = rsOut(md, W, mid);
    if (!inB && !inM) break;
    const C = W.p[md.index.Spine01], away = B.clone().sub(C); away.addScaledVector(dir, -away.dot(dir));
    const sgn = new T.Vector3().crossVectors(P, away).dot(dir) >= 0 ? 1 : -1;
    P.applyAxisAngle(dir, sgn * 12 * Math.PI / 180);
    B.copy(A).addScaledVector(dir, a * cos).addScaledVector(P, a * sin);
  }
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
  if (F.air || !RS.armW) return 0;
  if ({idle: 1, intro: 1, walkF: 1, walkB: 1}[F.act]) return 1;
  if (y.move && y.backTo === 'idle') return y.back;
  return 0;
}

// The neck roll at idle frame af: {u: 0..1 through it} or null. A pure function of af.
function rsFidget(F) {
  if (F.act !== 'idle' && F.act !== 'intro') return null;
  const fg = RS.fidget, x = F.af - fg.first;
  if (x < 0) return null;
  const t = x % fg.every;
  return t < fg.len ? {u: t / fg.len} : null;
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
  const C1 = W.p[ix.Spine01];
  const rp = rsChest(md, W, Rr.pos, v[1]).add(C1).addScaledVector(RS_SIDE, -RS.flow.rear * Math.cos(ph + .8)).addScaledVector(RS_UP, RS.flow.rear * Math.sin(ph + .8));
  const lf = rsVec(L.fing, v[2]).applyAxisAngle(RB_LINE, .12 * Math.sin(ph)).normalize(), lpn = rsVec(L.palm, v[3]).normalize();
  const rf = rsChest(md, W, Rr.fing, v[4]).normalize(), rpn = rsChest(md, W, Rr.palm, v[5]).normalize();
  let le = rsVec(L.elbow, new THREE.Vector3()).normalize(), re = rsChest(md, W, Rr.elbow, new THREE.Vector3()).normalize();
  rsArm(md, p, W, 'L', lp, le, lf, lpn, w);
  rsArm(md, p, rbFK(md, p, RB.W), 'R', rp, re, rf, rpn, w);
  if (fid) {   // the neck: a slow roll, down to one side, around, up on the other, the eyes back on the opponent
    const e = Math.sin(Math.PI * fid.u), a = 2 * Math.PI * fid.u;
    mdBoneTurn(p, ix.Head, MD_X, 14 * e * Math.max(0, Math.sin(a)));     // (down)
    mdBoneTurn(p, ix.Head, new THREE.Vector3(0, 0, 1), 22 * e * Math.cos(a / 2));   // (side to side)
    mdBoneTurn(p, ix.neck, new THREE.Vector3(0, 0, 1), 8 * e * Math.cos(a / 2));
  }
});

// A preset of the guard (RS.presets) by name.
function rsPreset(name) { const o = RS.presets[name]; RS.preset = name; RS.curl = o.curl; RS.armW = o.armW; RS.flow = o.flow; if (o.lead) { RS.lead = o.lead; RS.rear = o.rear; } }
rsPreset('B');   // Denis's choice (11/11/2026): half-open hands
// The hands: the guard's acts as closed as the preset says; the rest as the game has them (open where openHands says).
RN.curlFor = (it, F) => RS.open.includes(F.act) ? RS.curl : CFG.looks[it.key].openHands.includes(F.act) ? 0 : 1;
RN.hooks.boot.push(VW => {
  VW_PLAYS[0][1][0][1] = 300;   // the viewer's guard lasts long enough to show the neck roll
  VW.rsPreset = rsPreset;   // (tests and the variant sheets)
});
