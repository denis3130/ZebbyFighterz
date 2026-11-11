// --- swag.js: Ren's entrance and taunt, hand-made (11/11/2026; no new clips, no Meshy). ---
// Two acts keyed pose by pose on top of the guard clip, with the same solver as everything else (feet pinned on the
// stance, legs by IK, arms by IK from the clip's arm, nothing through the body):
//   'intro'  "Entrata": he stands tall and loose, head down, shaking out his hands; rolls his shoulders, lifts his eyes
//            to the opponent, then snaps into his guard with a stomp (a ring of water on the floor) and squeezes his
//            fists once before they settle half-open. 110 frames (the game's round intro is CFG.round.intro = 100).
//   'taunt'  "Provocazione": the lead hand comes up in front of the face, index finger raised, and wags "no-no" three
//            times while his chin lifts and the head shakes the other way; then back to the guard. 84 frames.
// Keys are [frame, value, ease]: values are numbers or arrays, ease 'out' (fast start: snaps), 'back' (a little past,
// then back), default smoothstep. Arm targets: the lead (left) hand in the fight-line frame (rsVec), the rear one in
// the chest's frame (rsChest), both from style.js; [forward, up, side] and [across, up, forward] as there.

const RW = {
  intro: {len: 110, snap: 54},
  taunt: {len: 84},
  ring: null, rings: [],
};

function rwEase(u, e) {
  u = Math.max(0, Math.min(1, u));
  if (e === 'out') return 1 - (1 - u) * (1 - u) * (1 - u);
  if (e === 'back') { const s = 1.6; return 1 + (s + 1) * Math.pow(u - 1, 3) + s * Math.pow(u - 1, 2); }
  return u * u * (3 - 2 * u);
}
// The value of keys at frame f.
function rwKey(keys, f) {
  if (f <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (f > keys[i][0]) continue;
    const [f0, a] = keys[i - 1], [f1, b, e] = keys[i], u = rwEase((f - f0) / (f1 - f0), e);
    return Array.isArray(a) ? a.map((x, k) => x + (b[k] - x) * u) : a + (b - a) * u;
  }
  return keys[keys.length - 1][1];
}

// --- The entrance ---
// g = 0 loose .. 1 guard (the snap: fast out, a little past, settled by frame 66)
const RW_IN = {
  g: [[0, 0], [46, 0], [56, 1.06, 'out'], [66, 1]],
  dip: [[0, -.05], [44, -.05], [50, -.06], [56, .075, 'out'], [64, .03], [80, .012], [110, .012]],
  lean: [[0, -2], [36, -3], [48, -5], [56, 9, 'out'], [66, 3], [110, 2]],
  yaw: [[0, -10], [44, -10], [56, 4, 'out'], [70, 0]],
  chest: [[0, 0], [26, 0], [34, -9], [42, 7], [50, -3], [56, 6, 'out'], [70, 0]],
  head: [[0, 15], [26, 15], [40, -7], [50, -4], [56, 3, 'out'], [70, 0]],
  curl: [[0, .25], [50, .3], [55, .9, 'out'], [68, .9], [80, .5]],
};
RB.styleFor.intro = (y, F) => {
  const f = Math.min(F.af, RW.intro.len), ki = RW_IN;
  y.dip = rwKey(ki.dip, f); y.lean = rwKey(ki.lean, f); y.yaw = rwKey(ki.yaw, f); y.chest = rwKey(ki.chest, f);
  y.head = rwKey(ki.head, f); y.stab = .35;
  const settle = rnSm((f - 70) / 30), ph = (F.af - 70) * (2 * Math.PI / 26);   // then the guard's own bounce takes over
  if (settle > 0) { y.dip += settle * .01 * Math.sin(ph); y.h.L += settle * 3; y.h.R += settle * 6; }
};

// --- The taunt ---
const RW_TA = {
  up: [[0, 0], [14, 1, 'out'], [64, 1], [80, 0]],   // the lead hand up in front of the face
  wag: [[0, 0], [16, 0], [20, 1], [58, 1], [62, 0]],   // the wag's weight (3 wags between 18 and 60)
  lean: [[0, 0], [14, -6], [64, -6], [80, 0]],
  chest: [[0, 0], [14, 6], [64, 6], [80, 0]],
  dip: [[0, 0], [14, -.025], [64, -.025], [80, 0]],
  head: [[0, 0], [14, -7], [64, -7], [80, 0]],
};
RB.styleFor.taunt = (y, F) => {
  const f = F.af, kt = RW_TA;
  y.lean = rwKey(kt.lean, f); y.chest = rwKey(kt.chest, f); y.dip = rwKey(kt.dip, f); y.head = rwKey(kt.head, f); y.stab = .5;
  y.h.L = 2; y.h.R = 5;
};

// --- Arms (after the pose, as style.js does its guard) ---
RB.post.push((md, p, F, S, y) => {
  const act = F.act;
  if (F.air || (act !== 'intro' && act !== 'taunt')) return;
  const W = rbFK(md, p, RB.W), ix = md.index, C1 = W.p[ix.Spine01], O = W.p[ix.Spine].clone();
  const c = a => rsChest(md, W, a, new THREE.Vector3()), l = a => rsVec(a, new THREE.Vector3());
  // the guard's targets (style.js's, without the flow)
  const G = {lp: l(RS.lead.pos).add(O), lf: l(RS.lead.fing).normalize(), lpn: l(RS.lead.palm).normalize(), le: l(RS.lead.elbow).normalize(),
    rp: c(RS.rear.pos).add(C1), rf: c(RS.rear.fing).normalize(), rpn: c(RS.rear.palm).normalize(), re: c(RS.rear.elbow).normalize()};
  let T = G;
  if (act === 'intro') {
    const f = Math.min(F.af, RW.intro.len), g = rwKey(RW_IN.g, f);
    // loose: hands by the thighs, fingers down, palms in, elbows a little back; shaking out (wrist flicks) early on
    const sh = Math.sin(Math.PI * rnSm((f - 4) / 30)) * (f < 36 ? 1 : 0), fl = Math.sin(F.af * 1.25), fr = Math.sin(F.af * 1.25 + 1.7);
    const L = {lp: c([.25, -.42 + .02 * sh * fl, .07]).add(C1), lf: c([0, -1, .15 + .45 * sh * fl]).normalize(), lpn: c([-1, 0, 0]), le: c([.3, 0, -1]).normalize(),
      rp: c([-.25, -.42 + .02 * sh * fr, .05]).add(C1), rf: c([0, -1, .1 + .45 * sh * fr]).normalize(), rpn: c([1, 0, 0]), re: c([-.3, 0, -1]).normalize()};
    // the shoulder roll lifts both hands a little (frames 28-44)
    const roll = Math.sin(Math.PI * rnSm((f - 28) / 16)) * (f > 28 && f < 44 ? 1 : 0);
    L.lp.addScaledVector(RS_UP, .05 * roll); L.rp.addScaledVector(RS_UP, .05 * roll);
    const mix = (a, b, k) => a.clone().lerp(b, k);
    // g past 1 (the snap's overshoot) carries the hands a little beyond the guard
    T = {lp: mix(L.lp, G.lp, g), lf: mix(L.lf, G.lf, Math.min(1, g)).normalize(), lpn: mix(L.lpn, G.lpn, Math.min(1, g)).normalize(), le: mix(L.le, G.le, Math.min(1, g)).normalize(),
      rp: mix(L.rp, G.rp, g), rf: mix(L.rf, G.rf, Math.min(1, g)).normalize(), rpn: mix(L.rpn, G.rpn, Math.min(1, g)).normalize(), re: mix(L.re, G.re, Math.min(1, g)).normalize()};
  } else {
    const f = F.af, up = rwKey(RW_TA.up, f), wg = rwKey(RW_TA.wag, f), a = Math.sin((f - 18) * (2 * Math.PI / 14)) * wg;   // 3 wags
    // the lead hand in front of the face, a forearm out, fingers (the index) up, palm toward the opponent, swinging
    const fing = l([.1, 1, 0]).applyAxisAngle(RB_LINE, .45 * a).normalize();
    const pos = l([.33, .16, .02]).add(O).addScaledVector(RS_SIDE, .035 * a);
    T = Object.assign({}, G, {lp: G.lp.clone().lerp(pos, up), lf: G.lf.clone().lerp(fing, up).normalize(),
      lpn: G.lpn.clone().lerp(l([1, 0, -.15]).normalize(), up).normalize(), le: G.le.clone().lerp(l([-.2, -1, .3]).normalize(), up).normalize()});
    if (up > 0) mdBoneTurn(p, ix.Head, MD_Y, -9 * a * up);   // the head shakes the other way
  }
  rsArm(md, p, W, 'L', T.lp, T.le, T.lf, T.lpn, 1);
  rsArm(md, p, rbFK(md, p, RB.W), 'R', T.rp, T.re, T.rf, T.rpn, 1);
});

// --- Hands: how closed each finger is (after the pose) ---
RN.hooks.applied.push((it, F) => {
  if (!it.fingers || (F.act !== 'intro' && F.act !== 'taunt')) return;
  let curlL, curlR, index = 0;
  if (F.act === 'intro') curlL = curlR = rwKey(RW_IN.curl, Math.min(F.af, RW.intro.len));
  else { curlL = .95; curlR = RS.curl; index = rwKey(RW_TA.up, F.af); }   // the lead hand a fist with its index finger straight
  for (let i = 0; i < it.fingers.length; i++) {
    const n = it.fingers[i].name, left = /^Left/.test(n);
    let k = left ? curlL : curlR;
    if (left && index > 0 && /Index/.test(n)) k *= 1 - index;
    it.fingers[i].quaternion.copy(MD_Q1).slerp(it.fist[i], k);
  }
});

// --- The stomp's ring of water on the floor (two rings, one a little after the other) ---
RN.hooks.boot.push(VW => {
  RB.pin.taunt = 1;
  Object.assign(VW_NAMES, {intro: 'Entrata', taunt: 'Provocazione'});
  VW_PLAYS.push(['Entrata', [['intro', RW.intro.len], ['idle', 40]]], ['Provocazione', [['idle', 20], ['taunt', RW.taunt.len], ['idle', 30]]]);
  for (let k = 0; k < 2; k++) {
    const m = new THREE.Mesh(new THREE.RingGeometry(.86, 1, 48), new THREE.MeshBasicMaterial({color: 0x7fe6ff, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending}));
    m.rotation.x = -Math.PI / 2; m.position.y = .012; m.visible = false; VW.scene.add(m); RW.rings.push(m);
  }
  // (the viewer builds its play buttons before the boot hooks: add the two new ones)
  const row = document.getElementById('moves'), n = VW_PLAYS.length;
  for (let i = n - 2; i < n; i++) {
    if (document.getElementById('play' + i)) continue;
    const b = document.createElement('button'); b.id = 'play' + i; b.innerHTML = '<span>' + VW_PLAYS[i][0] + '</span>';
    b.addEventListener('click', () => vwPlay(i)); row.appendChild(b);
  }
});
RN.hooks.draw.push(VW => {
  const F = RN_D.F || VW.F, on = RN.on && F.act === 'intro';
  RW.rings.forEach((m, k) => {
    const u = on ? (F.af - RW.intro.snap - 1 - 4 * k) / 22 : -1;
    m.visible = u > 0 && u < 1;
    if (!m.visible) return;
    m.position.x = VW.it.root.position.x; m.position.z = VW.it.root.position.z;
    m.scale.setScalar(.25 + 1.05 * rwEase(u, 'out') * (1 - .25 * k)); m.material.opacity = .85 * (1 - u) * (1 - .4 * k);
  });
});
