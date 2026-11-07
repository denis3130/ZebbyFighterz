// The Meshy fighters (Tappa 2a): a character packed by tools/meshy_pack.py (ASSETS '<key>/<key>.json', '.bin', '.jpg'),
// drawn as a toon SkinnedMesh with a skinned outline. Its pose is a pure function of the sim state (mdPoseOf), put on the
// bones on every drawn frame (mdSync, called by f3Sync for the items of kind 'model'). Graphics only: it reads the
// state and never writes it. Model space as the placeholder's: metres, the feet at y=0, forward +z.

const MD = {};   // decoded packages by key (see mdData)
const MD_OUTLINE = .012;   // outline width, metres in the world

// The decoded package of key: {meta, nb, bones, index (bone name -> index), geo, clips: {id: {n, fps, q, h}}}, or null
// when ASSETS has no such package. Memoised per meta object (a package swapped in ASSETS is decoded again).
function mdData(key) {
  const meta = ASSETS[key + '/' + key + '.json'], b64 = ASSETS[key + '/' + key + '.bin'];
  if (!meta || !b64) return null;
  if (MD[key] && MD[key].meta === meta) return MD[key];
  const s = atob(b64), u8 = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
  const buf = u8.buffer, m = meta.mesh, f32 = a => new Float32Array(buf, a[0], a[1]), geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(f32(m.pos), 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(f32(m.nor), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(f32(m.uv), 2));
  geo.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(new Uint8Array(buf, m.jnt[0], m.jnt[1]), 4));
  geo.setAttribute('skinWeight', new THREE.BufferAttribute(f32(m.wgt), 4));
  geo.setIndex(new THREE.BufferAttribute(m.verts > 65535 ? new Uint32Array(buf, m.idx[0], m.idx[1]) : new Uint16Array(buf, m.idx[0], m.idx[1]), 1));
  const clips = {}, index = {};
  for (const id in meta.clips) { const c = meta.clips[id]; clips[id] = {n: c.n, fps: c.fps, q: f32(c.q), h: f32(c.h)}; }
  meta.bones.forEach((b, i) => { index[b.n] = i; });
  return MD[key] = {meta, nb: meta.bones.length, bones: meta.bones, index, geo, clips};
}

// One Meshy fighter (an F3D item), or null without its package: bones in the rest pose, the toon mesh and its outline
// (same geometry, same skeleton), the limb points and one material (mats.main: the hit flash). Not yet in the scene.
// Where CFG.looks[key] asks for them, the look data's parts: finger bones (fists), hair spikes, the face's thin outline.
function modelBuild(key) {
  const md = mdData(key);
  if (!md) return null;
  f3Shared();
  const root = new THREE.Group(), body = new THREE.Group(), s = CFG.body.h / 1000 / md.meta.height;
  body.scale.setScalar(s); root.add(body);
  const bones = md.bones.map(b => { const o = new THREE.Bone(); o.name = b.n; o.position.fromArray(b.t); o.quaternion.fromArray(b.q); return o; });
  md.bones.forEach((b, i) => (b.p < 0 ? body : bones[b.p]).add(bones[i]));
  const B = n => bones[md.index[n]], lk = CFG.looks[key] || {}, look = (lk.fists || lk.spikes || lk.faceLine) && mdLookData(md, key);
  // fists: the fingers' bones under the hands (after the package's in the skeleton, as the look's skin counts them)
  const fingers = look && lk.fists ? look.fingers.map(f => { const o = new THREE.Bone(); o.name = f.n; o.position.fromArray(f.t); return o; }) : [];
  fingers.forEach((o, k) => (B(look.fingers[k].p) || fingers.find(g => g.name === look.fingers[k].p)).add(o));
  const per = look && lk.faceLine ? ' * aLine' : '', geo = fingers.length || per ? new THREE.BufferGeometry() : md.geo;
  if (geo !== md.geo) {   // the package's geometry, its attributes shared (not copied), with the look's skin and outline widths
    for (const a in md.geo.attributes) geo.setAttribute(a, md.geo.attributes[a]);
    geo.setIndex(md.geo.index);
    if (fingers.length) { geo.setAttribute('skinIndex', look.skin[0]); geo.setAttribute('skinWeight', look.skin[1]); }
    if (per) geo.setAttribute('aLine', look.line);
  }
  // The texture appears once decoded; until then the mesh draws with an empty map (no error, no warning).
  const img = new Image(), tex = new THREE.Texture(img);
  tex.flipY = false;   // glTF UVs
  img.src = ASSETS[key + '/' + key + '.jpg'];
  img.decode().then(() => { tex.needsUpdate = true; }, () => {});
  const main = new THREE.MeshToonMaterial({map: tex, gradientMap: F3.grad, skinning: true});
  const line = new THREE.MeshBasicMaterial({color: F3_OUTLINE.color, side: THREE.BackSide, skinning: true}), w = (MD_OUTLINE / s).toFixed(5);
  line.onBeforeCompile = sh => { sh.vertexShader = (per ? 'attribute float aLine;\n' : '') + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\ttransformed += normal * ' + w + per + ';'); };
  line.customProgramCacheKey = () => w + per;
  const mesh = new THREE.SkinnedMesh(geo, main), outline = new THREE.SkinnedMesh(geo, line);
  mesh.frustumCulled = outline.frustumCulled = false;
  body.add(mesh, outline);
  root.updateMatrixWorld(true);
  const skel = new THREE.Skeleton(bones.concat(fingers));
  mesh.bind(skel); outline.bind(skel);
  const limbs = {};
  for (const l in md.meta.limbs) { const d = md.meta.limbs[l], o = new THREE.Object3D(); o.position.fromArray(d.p); B(d.b).add(o); limbs[l] = o; }
  const it = {kind: 'model', key, root, body, scale: s, bones, mesh, outline, headEnd: B(md.meta.head), limbs, mats: {main},
    joints: {pelvis: B('Hips'), chest: B('Spine'), neck: B('neck'), head: B('Head')}};
  if (fingers.length) { it.fingers = fingers; it.fist = look.fingers.map(f => new THREE.Quaternion().fromArray(f.fist)); }
  if (!md.hitT) mdMeasure(md, it);
  if (look && lk.spikes) B('Head').add(mdSpikes(look.spikes));
  return it;
}

// The hair spikes of the look data on the head: flattened cones in the hair colour of Denis's drawing, with outlines.
const MD_HAIR = 0x4a3d45, MD_LINE = new THREE.MeshBasicMaterial({color: F3_OUTLINE.color, side: THREE.BackSide});
function mdSpikes(list) {
  const g = new THREE.Group(), mat = new THREE.MeshToonMaterial({color: MD_HAIR, gradientMap: F3.grad}), up = new THREE.Vector3(0, 1, 0);
  for (const s of list) {
    const geo = new THREE.ConeGeometry(s.r, s.len, 7, 1); geo.translate(0, s.len / 2, 0); geo.scale(1, 1, .5);
    const m = new THREE.Mesh(geo, mat), o = new THREE.Mesh(geo, MD_LINE);
    o.scale.set(1.22, 1.07, 1.35); m.add(o);
    m.position.fromArray(s.p); m.quaternion.setFromUnitVectors(up, new THREE.Vector3().fromArray(s.d));
    g.add(m);
  }
  return g;
}

// The look data of package key ('<key>/<key>_look.json' and '.bin', tools/ren_look.py), decoded once onto md, or null:
// {fingers: the finger bones, skin: [skinIndex, skinWeight] with them, line: the outline widths, spikes}.
function mdLookData(md, key) {
  if (md.look !== undefined) return md.look;
  const j = ASSETS[key + '/' + key + '_look.json'], b64 = ASSETS[key + '/' + key + '_look.bin'];
  if (!j || !b64) return md.look = null;
  const s = atob(b64), u8 = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
  const f32 = a => new Float32Array(u8.buffer, a[0], a[1]);
  return md.look = {fingers: j.fingers, spikes: j.spikes,
    skin: [new THREE.Uint16BufferAttribute(new Uint8Array(u8.buffer, j.skin[0][0], j.skin[0][1]), 4), new THREE.BufferAttribute(f32(j.skin[1]), 4)],
    line: new THREE.BufferAttribute(f32(j.line), 1)};
}

// --- Poses: {q: local rotations, nb x 4, h: the Hips' local position} ---
// The rest pose of md (the bind pose).
function mdRest(md) {
  const q = new Float32Array(md.nb * 4);
  md.bones.forEach((b, i) => q.set(b.q, i * 4));
  return {q, h: Float32Array.from(md.bones[0].t)};
}

// The pose of fighter F now (its character's package), or null when it has none: the act's entry of CFG.clips
// evaluated at F's state. Pure: only F, S and the package (with the hit times and walk speeds found at its build).
function mdPoseOf(F, S) {
  const md = mdData(F.char);
  if (!md) return null;
  const C = CFG.clips, c = {F, S, m: CFG.moves[F.act], id: F.act};
  let e = C[F.act];
  switch (F.act) {
    case 'block': e = F.prev & BTN.D ? C.guardC : C.guard; break;   // a block with down held is crouched, as in the sim
    case 'air': c.u = mdUp((CFG.jump.v - F.vy) / (2 * CFG.jump.v)); break;
    case 'thr': if (F.hit) e = C.thrHit; break;
    case 'thrown': e = C.hitStun; break;
    case 'juggle': case 'knock': case 'ko':   // flying (tilting as it falls), then lying on the floor
      if (F.air) { e = C.fly; c.u = mdUp((60 - F.vy) / 140); } else e = C.down;
      break;
    case 'rollF': case 'rollB': e = C.roll; break;
  }
  const p = mdEval(md, e || C.idle, c), lk = CFG.looks[F.char];
  if (lk && lk.headUp) mdBoneTurn(p, md.index.Head, MD_X, -lk.headUp);
  return p;
}
function mdUp(u) { return Math.max(0, Math.min(1, u)); }

// Entry e of CFG.clips (see there) as a pose; c = {F, S, m: the move, id: the act, u (air acts), force (a clip time
// used instead of the move's, by the hit-time search)}. The Hips stay over the root in x and z (the sim moves the
// fighter); y is the clip's unless the entry fixes it ('cap': never above the rest pose's, for clips that leave the
// floor while the sim stays on it). plant = the feet ('L', 'R' or 'LR') held by IK where the entry's t[0] pose has them,
// so a grounded strike neither slides nor lifts its support foot. Poses are those of a fighter facing right: facing
// left is drawn as the mirror image (mdSync).
function mdEval(md, e, c) {
  if (e.kick) return mdKick(md, e, c);
  if (e.low) return mdLayer(md, mdEval(md, e.low, c), mdEval(md, e.up, c));
  const F = c.F;
  let t = 0, loop = false;
  if (e.loop) { t = (c.S.frame + 23 * F.side) / 60; loop = true; }
  else if (e.walk) { t = mdWalkT(md, e, F); loop = true; }
  else if (e.at !== undefined) t = e.at;
  else if (e.t) t = c.force !== undefined ? c.force : mdMoveT(e.t, c.m, F.af, md.hitT[c.id]);
  else if (e.k) t = mdKey(e.k, c.u !== undefined ? c.u : F.af);
  const p = mdRoot(md, e, mdSample(md, e.c, t, loop));
  if (e.breathe) {   // a held pose breathes: the body bobs and the chest rises with S.frame
    const b = Math.sin((c.S.frame + 23 * F.side) * .09);
    p.h[1] += .009 * b; mdBoneTurn(p, md.index.Spine01, MD_X, -1.4 * b);
  }
  if (e.walk) mdHipsTurn(p, MD_Y, 90 - F3_YAW / F3_DEG, md.index.Spine02);
  if (e.plant) {   // each planted foot held where the t[0] pose has it, turned as it is there
    const p0 = mdRoot(md, e, mdSample(md, e.c, e.t ? e.t[0] : 0, false));
    for (const leg of e.plant) {
      const i = md.index[leg === 'L' ? 'LeftFoot' : 'RightFoot'], w = mdWorld(md, p0, i, MD_M[1]);
      mdLegIK(md, p, leg, MD_V[3].setFromMatrixPosition(w).toArray(), new THREE.Quaternion().setFromRotationMatrix(w));
    }
  }
  return p;
}

// The Hips of a sampled pose over the root (x, z), and its y as the entry asks ('cap': at most the Hips' height in the
// entry's t[0] pose, the stance the move starts from).
function mdRoot(md, e, p) {
  p.h[0] = 0; p.h[2] = 0;
  if (e.y === 'cap') p.h[1] = Math.min(p.h[1], md.clips[e.c].h[Math.round((e.t ? e.t[0] : 0) * md.clips[e.c].fps) * 3 + 1]);
  else if (e.y !== undefined) p.h[1] = e.y;
  if (e.pitch) mdHipsTurn(p, MD_X, e.pitch, false);
  return p;
}

// A move's clip time at frame af: startup from t[0] to the hit frame, the active frames held on it, recovery to t[1]
// (r = 'land': in 8 frames, then held until the landing). hit undefined (no package build yet): the middle.
function mdMoveT(t, m, af, hit) {
  const h = hit === undefined ? (t[0] + t[1]) / 2 : hit;
  if (af <= m.s) return t[0] + (h - t[0]) * Math.max(0, af) / m.s;
  if (af <= m.s + m.a) return h;
  return h + (t[1] - h) * Math.min(1, (af - m.s - m.a) / (m.r === 'land' ? 8 : m.r));
}

// A walk's clip time from the distance walked (F.x along the facing, the clip's own direction): with walk = 1 through
// the clip's planted-foot distance table (md.walkD: the foot on the floor moves exactly as far as the body), else at
// the constant speed walk m/s.
function mdWalkT(md, e, F) {
  const key = e.c + ':' + e.walk, v = md.walkV[key], p = F.x * F.face / 1000 * (v < 0 ? 1 : -1), D = md.walkD[key];
  if (!D) return p / Math.abs(v);
  const tot = D[D.length - 1], u = ((p % tot) + tot) % tot;
  let lo = 0, hi = D.length - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (D[mid] <= u) lo = mid; else hi = mid; }
  return (lo + (u - D[lo]) / Math.max(1e-9, D[hi] - D[lo])) / md.clips[e.c].fps;
}

// Piecewise linear: k = [[x0, t0], [x1, t1], ...] at x (clamped to the ends).
function mdKey(k, x) {
  if (x <= k[0][0]) return k[0][1];
  for (let i = 1; i < k.length; i++) if (x <= k[i][0]) return k[i - 1][1] + (k[i][1] - k[i - 1][1]) * (x - k[i - 1][0]) / (k[i][0] - k[i - 1][0]);
  return k[k.length - 1][1];
}

// The lower body (Hips and legs) of low with the rest of up; the Hips' position from low.
const MD_LOWER = ['Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase'];
function mdLayer(md, low, up) {
  const q = up.q.slice();
  for (const n of MD_LOWER) { const i = md.index[n] * 4; q.set(low.q.subarray(i, i + 4), i); }
  return {q, h: low.h.slice()};
}

// Turns bone i of pose p by deg about axis in its own frame.
function mdBoneTurn(p, i, axis, deg) {
  MD_QA.fromArray(p.q, i * 4).multiply(MD_QR.setFromAxisAngle(axis, deg * F3_DEG)).toArray(p.q, i * 4);
}

// Turns the whole body about axis (model space) by deg at the Hips. keep = index of the Hips' child that keeps its
// world orientation (the spine, when only the legs should turn), or false.
const MD_X = new THREE.Vector3(1, 0, 0), MD_Y = new THREE.Vector3(0, 1, 0), MD_QR = new THREE.Quaternion(), MD_QH = new THREE.Quaternion();
function mdHipsTurn(p, axis, deg, keep) {
  MD_QR.setFromAxisAngle(axis, deg * F3_DEG);
  MD_QH.fromArray(p.q, 0);
  if (keep !== false) {   // child' = hips^-1 * turn^-1 * hips * child
    MD_QA.copy(MD_QH).invert().multiply(MD_QB.copy(MD_QR).invert()).multiply(MD_QH).multiply(MD_QB.fromArray(p.q, keep * 4)).toArray(p.q, keep * 4);
  }
  MD_QA.copy(MD_QR).multiply(MD_QH).toArray(p.q, 0);
}

// --- Two-bone leg IK, in model space on a pose (pure math: the bones' rest offsets from md, rotations from p) ---
// World (model-space) matrix of bone i in pose p.
const MD_M = [new THREE.Matrix4(), new THREE.Matrix4()], MD_T = new THREE.Vector3(), MD_S1 = new THREE.Vector3(1, 1, 1);
function mdWorld(md, p, i, out) {
  const chain = [];
  for (let j = i; j >= 0; j = md.bones[j].p) chain.push(j);
  out.identity();
  for (let k = chain.length - 1; k >= 0; k--) {
    const j = chain[k], b = md.bones[j];
    MD_T.fromArray(j ? b.t : p.h); MD_QA.fromArray(p.q, j * 4);
    out.multiply(MD_M[0].compose(MD_T, MD_QA, MD_S1));
  }
  return out;
}
// The leg ('L' or 'R') of p bent so its ankle reaches target (model space, metres of the package), the knee staying
// on the side it bends to now; footQ (optional) = the foot's world rotation to keep. Rotations only, p changed in place.
const MD_V = [0, 1, 2, 3, 4, 5].map(() => new THREE.Vector3()), MD_QW = [0, 1, 2].map(() => new THREE.Quaternion());
function mdLegIK(md, p, leg, target, footQ) {
  const iu = md.index[leg === 'L' ? 'LeftUpLeg' : 'RightUpLeg'], il = md.index[leg === 'L' ? 'LeftLeg' : 'RightLeg'];
  const ia = md.index[leg === 'L' ? 'LeftFoot' : 'RightFoot'], V = MD_V, Q = MD_QW, m = MD_M[1];
  const A = V[0].setFromMatrixPosition(mdWorld(md, p, iu, m)), qu = Q[0].setFromRotationMatrix(m);
  const B = V[1].setFromMatrixPosition(mdWorld(md, p, il, m)), ql = Q[1].setFromRotationMatrix(m);
  const C = V[2].setFromMatrixPosition(mdWorld(md, p, ia, m)), qp = Q[2].setFromRotationMatrix(mdWorld(md, p, md.bones[iu].p, m));
  const a = A.distanceTo(B), b = B.distanceTo(C), T = V[3].fromArray(target), AT = V[4].subVectors(T, A);
  const d = Math.max(Math.abs(a - b) + 1e-4, Math.min(a + b - 1e-4, AT.length()));
  const dir = AT.normalize(), pole = V[5].subVectors(B, A), perp = pole.sub(dir.clone().multiplyScalar(pole.dot(dir)));
  if (perp.lengthSq() < 1e-10) perp.set(0, 0, 1).sub(dir.clone().multiplyScalar(dir.z));
  perp.normalize();
  const cos = (a * a + d * d - b * b) / (2 * a * d), sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  const B2 = A.clone().add(dir.clone().multiplyScalar(a * cos)).add(perp.multiplyScalar(a * sin));
  const d1 = new THREE.Quaternion().setFromUnitVectors(B.clone().sub(A).normalize(), B2.clone().sub(A).normalize());
  const C1 = C.clone().sub(A).applyQuaternion(d1).add(A), T2 = A.clone().add(dir.multiplyScalar(d));
  const d2 = new THREE.Quaternion().setFromUnitVectors(C1.sub(B2).normalize(), T2.sub(B2).normalize());
  const quW = d1.clone().multiply(qu), qlW = d2.multiply(d1).multiply(ql);
  qp.invert().multiply(quW).toArray(p.q, iu * 4);   // up leg local = parent^-1 * its new world rotation
  quW.invert().multiply(qlW).toArray(p.q, il * 4);  // lower leg local = up leg^-1 * its new world rotation
  if (footQ) qlW.invert().multiply(footQ).toArray(p.q, ia * 4);   // foot local = lower leg^-1 * the kept world rotation
}

// A kick made on a base pose (CFG.clips {kick: base entry, leg, to}): the ankle goes from where the base pose has it
// to the target 'to' (model space) during startup, holds it through the active frames and comes back in recovery.
function mdKick(md, e, c) {
  const p = mdEval(md, e.kick, c), m = c.m, af = c.F.af, i = md.index[e.leg === 'L' ? 'LeftFoot' : 'RightFoot'];
  const w = af <= m.s ? Math.max(0, af) / m.s : af <= m.s + m.a ? 1 : Math.max(0, 1 - (af - m.s - m.a) / m.r);
  const C = new THREE.Vector3().setFromMatrixPosition(mdWorld(md, p, i, MD_M[1]));
  mdLegIK(md, p, e.leg, C.lerp(MD_V[3].fromArray(e.to), w * w * (3 - 2 * w)).toArray());
  return p;
}

// Found once per package, on the bones of its first build: md.walkV['clip:walk'] = the planted-foot speed along the
// model's forward axis (m/s of clip time; < 0 when the clip walks forward), md.walkD['clip:1'] = per clip frame the
// distance the lower foot has moved along that axis since frame 0, md.hitT[move] = the hit frame's clip time.
function mdMeasure(md, it) {
  const C = CFG.clips, v = new THREE.Vector3(), at = (p, face) => {
    mdApply(it, p); it.root.position.set(0, 0, 0); it.root.rotation.y = face * F3_YAW; it.body.scale.x = it.scale * (face < 0 ? -1 : 1);
    it.root.updateMatrixWorld(true);
  };
  md.walkV = {}; md.walkD = {};
  for (const k in C) {
    const e = C[k];
    if (!e.walk || md.walkV[e.c + ':' + e.walk] !== undefined) continue;
    if (e.walk !== 1) { md.walkV[e.c + ':' + e.walk] = -e.walk; continue; }
    const n = md.clips[e.c].n, feet = [[], []];
    for (let f = 0; f < n; f++) {
      const p = mdSample(md, e.c, f / 30, false); p.h[0] = 0; p.h[2] = 0; at(p, 0);
      ['footL', 'footR'].forEach((l, j) => { it.limbs[l].getWorldPosition(v); feet[j].push([v.y, v.z]); });
    }
    let sum = 0, cnt = 0;
    for (const ft of feet) {
      const lo = Math.min(...ft.map(a => a[0]));
      for (let f = 0; f + 1 < n; f++) if (ft[f][0] < lo + .02 && ft[f + 1][0] < lo + .02) { sum += (ft[f + 1][1] - ft[f][1]) * 30; cnt++; }
    }
    md.walkV[e.c + ':' + e.walk] = cnt ? sum / cnt : -1;
    const D = new Float32Array(n);
    for (let f = 0; f + 1 < n; f++) { const k = feet[0][f][0] <= feet[1][f][0] ? 0 : 1; D[f + 1] = D[f] + Math.abs(feet[k][f + 1][1] - feet[k][f][1]); }
    md.walkD[e.c + ':' + e.walk] = D;
  }
  md.hitT = {};
  for (const id in CFG.moves) {
    const e = C[id], m = CFG.moves[id], te = e && (e.t ? e : e.up && e.up.t ? e.up : null);
    if (!te) continue;
    const limb = e.limb || m.limb, k = m.box, F = {face: 1, x: 0, af: 0, side: 0}, c = {F, S: {frame: 0}, m, id};
    let best = null;
    for (let t = te.t[0]; t <= te.t[1] + 1e-6; t += 1 / 30) {
      let worst = 0, reach = 0;
      for (const face of [1, -1]) {
        F.face = face; c.force = t; at(mdEval(md, e, c), face); it.limbs[limb].getWorldPosition(v);
        const x = v.x * face * 1000, y = v.y * 1000;
        worst = Math.max(worst, Math.hypot(Math.max(k[0] - x, 0, x - k[1]), Math.max(k[2] - y, 0, y - k[3]))); reach += x;
      }
      if (!best || worst < best.w - 1e-6 || (Math.abs(worst - best.w) <= 1e-6 && reach > best.r)) best = {t, w: worst, r: reach};
    }
    md.hitT[id] = best.t;
  }
  at(mdRest(md), 0);
}

const MD_QA = new THREE.Quaternion(), MD_QB = new THREE.Quaternion(), MD_Q1 = new THREE.Quaternion(), MD_CURL = 5;
// Clip id of md at t seconds: rotations slerped between the two nearest frames, the Hips' position lerped. Clamped to
// the clip, or wrapped over its length when loop is set (the first and last frames of a cycle are the same pose).
function mdSample(md, id, t, loop) {
  const c = md.clips[id], nb = md.nb, last = c.n - 1, q = new Float32Array(nb * 4), h = new Float32Array(3);
  let f = t * c.fps;
  f = loop ? ((f % last) + last) % last : Math.max(0, Math.min(last, f));
  const i = Math.min(last - 1, Math.floor(f)), k = f - i, a = i * nb * 4, b = a + nb * 4;
  for (let j = 0; j < nb * 4; j += 4) MD_QA.fromArray(c.q, a + j).slerp(MD_QB.fromArray(c.q, b + j), k).toArray(q, j);
  for (let j = 0; j < 3; j++) h[j] = c.h[i * 3 + j] + (c.h[i * 3 + 3 + j] - c.h[i * 3 + j]) * k;
  return {q, h};
}

// a and b blended: k = 0 is a, 1 is b (slerp per bone, lerp of the Hips).
function mdMix(a, b, k) {
  const q = new Float32Array(a.q.length), h = new Float32Array(3);
  for (let i = 0; i < q.length; i += 4) {
    MD_QA.fromArray(a.q, i).slerp(MD_QB.fromArray(b.q, i), k).toArray(q, i);
  }
  for (let i = 0; i < 3; i++) h[i] = a.h[i] + (b.h[i] - a.h[i]) * k;
  return {q, h};
}

function mdApply(it, p) {
  const bs = it.bones;
  for (let i = 0; i < bs.length; i++) bs[i].quaternion.fromArray(p.q, i * 4);
  bs[0].position.fromArray(p.h);
}

// Every drawn frame, for side's Meshy fighter: as f3Sync does for the placeholders (visible, at F.x, F.y, turned
// face * F3_YAW, and mirrored when facing left), a change to a free or movement act eased in over CFG.anim.model frames by F.af, a strike over its
// first CFG.anim.strikeIn frames (never into its active frames: there the pose is the clip's). Hits and throws snap.
function mdSync(it, side, S) {
  it.root.visible = !!S;
  if (!S) { it.F = null; return; }
  const F = fighterOf(S, side), m = CFG.moves[F.act], n = m ? Math.min(CFG.anim.strikeIn, m.s - 1) : CFG.anim.model;
  it.root.position.set(F.x / 1000, F.y / 1000, side ? -.05 : .05);
  it.root.rotation.y = F.face * F3_YAW;
  it.body.scale.x = it.scale * F.face;   // facing left: the mirror image (fx's squash scales the root, not the body)
  if (it.fingers) {   // fists, opened where the act opens the hands: closing and opening in MD_CURL frames
    const k = CFG.looks[it.key].openHands.includes(F.act) ? 0 : 1;
    if (F !== it.F || F.act !== it.act) it.curl0 = F === it.F ? it.curl : k;
    it.curl = it.curl0 + (k - it.curl0) * Math.min(1, Math.max(0, F.af) / MD_CURL);
    for (let i = 0; i < it.fingers.length; i++) it.fingers[i].quaternion.copy(MD_Q1).slerp(it.fist[i], it.curl);
  }
  let p = mdPoseOf(F, S) || mdRest(mdData(it.key));
  if (F !== it.F) it.from = null;
  else if (F.act !== it.act) it.from = F3_EASE[F.act] || (m && n > 0) ? it.pose : null;
  if (it.from && F.af < n) p = mdMix(it.from, p, Math.max(0, F.af) / n);
  it.F = F; it.act = F.act; it.pose = p;
  mdApply(it, p);
}

// World y (m) of the top of side's head: the head's end bone of a model, the highest vertex of a placeholder's head.
function headTop(side) {
  const it = F3D[side];
  if (it.kind === 'model') { it.root.updateMatrixWorld(true); return it.headEnd.getWorldPosition(new THREE.Vector3()).y; }
  const h = it.joints.head.children.find(o => o.name === 'head.head'), a = h.geometry.attributes.position, v = new THREE.Vector3();
  let y = -1e9;
  h.updateWorldMatrix(true, false);
  for (let k = 0; k < a.count; k++) y = Math.max(y, v.fromBufferAttribute(a, k).applyMatrix4(h.matrixWorld).y);
  return y;
}
