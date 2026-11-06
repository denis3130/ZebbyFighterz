// Placeholder fighters (Tappa 1; the Meshy models replace them in Tappa 2): a rig of THREE.Group joints carrying
// toon-shaded parts, each with a black outline shell, posed on every drawn frame from the sim state. Graphics only:
// it reads the state and never writes it. d_render.js builds them (fighterBuild) and calls f3Sync(S) per frame.
// Model space: forward +z, up +y, the fighter's left +x, metres, the root at the feet; 1.8 m tall. The root turns to
// face the opponent (face * 90°), 25° of it back toward the camera.

const F3D = [];   // per side: {root, joints: {name: Group}, limbs: {handL, handR, footL, footR}: Object3D, mats: {slot: material}}
// Shared by both fighters: toon gradient, outline material, shapes (and their outline shells), scratch objects.
const F3 = {grad: null, outMat: null, geo: {}, out: new Map(), v: new THREE.Vector3(), e: new THREE.Euler(),
  m: new THREE.Matrix4(), m2: new THREE.Matrix4(), m3: new THREE.Matrix4(), memo: {}};
const F3_DEG = Math.PI / 180, F3_YAW = 65 * F3_DEG, F3_OUTLINE = {w: .018, color: 0x0b0a10};
// Material slots (the brief's palette). main = the outfit's main colour: Ren's vest, Kael's suit.
const F3_COL = {
  ren: {skin: 0xe8b48a, hair: 0x2a2230, main: 0x2f6f6e, inner: 0x3a3040, sash: 0xf07a22, pants: 0x3b3340, wrap: 0xe9e2d6,
    fist: 0xe8b48a, boot: 0x2f6f6e, sole: 0x1b1b1f},
  kael: {skin: 0xe8b48a, hair: 0xece8f4, main: 0x3a2d4a, inner: 0x9b5fe0, sash: 0x9b5fe0, pants: 0x3a2d4a, wrap: 0x2a2233,
    fist: 0x2a2233, boot: 0x2a2233, sole: 0x9b5fe0},
};
// Rest skeleton, parents first: joint -> [parent, x, y, z] offset from the parent. Arms and legs hang straight down.
const F3_BONE = {pelvis: [null, 0, 1, 0], spine: ['pelvis', 0, .11, 0], chest: ['spine', 0, .19, 0], neck: ['chest', 0, .21, 0],
  head: ['neck', 0, .07, 0], shL: ['chest', .22, .17, 0], elL: ['shL', 0, -.29, 0], wrL: ['elL', 0, -.26, 0],
  shR: ['chest', -.22, .17, 0], elR: ['shR', 0, -.29, 0], wrR: ['elR', 0, -.26, 0], hipL: ['pelvis', .1, -.05, 0],
  knL: ['hipL', 0, -.43, 0], anL: ['knL', 0, -.44, 0], hipR: ['pelvis', -.1, -.05, 0], knR: ['hipR', 0, -.43, 0], anR: ['knR', 0, -.44, 0]};
const F3_J = Object.keys(F3_BONE);
// The points that hit (limbWorld): fist centres and boot centres (0.05 m up when standing).
const F3_LIMB = {handL: ['wrL', 0, -.055, 0], handR: ['wrR', 0, -.055, 0], footL: ['anL', 0, -.03, .045], footR: ['anR', 0, -.03, .045]};
// Parts: [joint, material slot, shape]. 22 meshes per fighter, each with its outline shell.
const F3_PART = [['pelvis', 'pants', 'hips'], ['pelvis', 'sash', 'sash'], ['spine', 'main', 'belly'], ['chest', 'main', 'chest'],
  ['chest', 'inner', 'panel'], ['neck', 'skin', 'neck'], ['head', 'skin', 'head'], ['head', 'hair', 'hair'],
  ['shL', 'skin', 'upper'], ['elL', 'wrap', 'fore'], ['wrL', 'fist', 'fist'], ['shR', 'skin', 'upper'], ['elR', 'wrap', 'fore'],
  ['wrR', 'fist', 'fist'], ['hipL', 'pants', 'thigh'], ['knL', 'pants', 'shin'], ['anL', 'boot', 'boot'], ['anL', 'sole', 'sole'],
  ['hipR', 'pants', 'thigh'], ['knR', 'pants', 'shin'], ['anR', 'boot', 'boot'], ['anR', 'sole', 'sole']];

// --- Shapes ---
// Built once, shared by both fighters; metres in the joint's frame, baked (never scaled on the mesh, so the outline
// keeps its width). Pieces merged into one shape share its material.
function f3Cyl(rt, rb, h, x, y, z, seg, sz) { return new THREE.CylinderGeometry(rt, rb, h, seg || 8).scale(1, 1, sz || 1).translate(x, y, z); }
function f3Sph(r, x, y, z, sx, sy, sz, ws, hs) { return new THREE.SphereGeometry(r, ws || 10, hs || 7).scale(sx, sy, sz).translate(x, y, z); }
function f3Box(w, h, d, x, y, z) { return new THREE.BoxGeometry(w, h, d).translate(x, y, z); }
// A cone from base point (x, y, z) along direction (dx, dy, dz), length len, base radius r.
function f3Spike(x, y, z, dx, dy, dz, len, r) {
  const g = new THREE.ConeGeometry(r, len, 5).translate(0, len / 2, 0), d = new THREE.Vector3(dx, dy, dz).normalize();
  return g.applyMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d))).translate(x, y, z);
}
// Positions, normals and indices of indexed geometries in one geometry (the uvs are not needed: no textures).
function f3Merge(gs) {
  let n = 0, m = 0;
  for (const g of gs) { n += g.attributes.position.count; m += g.index.count; }
  const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), idx = new Uint16Array(m);
  let v = 0, k = 0;
  for (const g of gs) {
    pos.set(g.attributes.position.array, v * 3); nor.set(g.attributes.normal.array, v * 3);
    for (let i = 0; i < g.index.count; i++) idx[k++] = g.index.array[i] + v;
    v += g.attributes.position.count; g.dispose();
  }
  const o = new THREE.BufferGeometry();
  o.setAttribute('position', new THREE.BufferAttribute(pos, 3)); o.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  o.setIndex(new THREE.BufferAttribute(idx, 1));
  return o;
}
// Hair: a cap over the top and back of the head plus spikes [x, y, z, dx, dy, dz, len, r] (head frame).
function f3Hair(cap, spikes) { return f3Merge([f3Sph(cap, 0, .125, -.008, 1, .96, 1.06, 12, 8)].concat(spikes.map(s => f3Spike(...s)))); }
const F3_SHAPE = {
  hips: () => f3Cyl(.15, .162, .2, 0, -.05, 0, 10, .86),
  // Waist band, a knot at the front and two tails hanging down the front (seen from either side).
  sash: () => f3Merge([f3Cyl(.166, .168, .075, 0, .02, 0, 10, .88), f3Sph(.047, .03, .02, .142, 1, .9, .8, 8, 6),
    f3Box(.07, .3, .02, .052, -.13, .15).rotateZ(.1), f3Box(.06, .25, .02, .002, -.105, .152).rotateZ(-.08)]),
  belly: () => f3Cyl(.165, .15, .2, 0, .09, 0, 10, .84),
  // Tapered chest: broad shoulders.
  chest: () => f3Cyl(.225, .165, .25, 0, .1, 0, 10, .74),
  // A flat triangle on the front, point down, and the standing collar: Ren's shirt in the open vest, Kael's purple.
  panel: () => f3Merge([new THREE.ConeGeometry(.1, .26, 3).rotateY(Math.PI / 3).rotateZ(Math.PI).scale(1, 1, .25).translate(0, .1, .14),
    f3Cyl(.09, .105, .09, 0, .235, -.01, 10)]),
  neck: () => f3Cyl(.056, .064, .12, 0, .05, 0, 8),
  head: () => f3Sph(.105, 0, .11, .01, .9, 1.1, 1, 12, 9),
  // Deltoid, upper arm and elbow ball.
  upper: () => f3Merge([f3Sph(.086, 0, -.02, 0, 1, 1, 1), f3Cyl(.072, .056, .29, 0, -.145, 0), f3Sph(.055, 0, -.29, 0, 1, 1, 1, 8, 6)]),
  // Forearm with two raised wraps (Ren's bandages, Kael's glove bands).
  fore: () => f3Merge([f3Cyl(.059, .046, .26, 0, -.13, 0), f3Cyl(.063, .061, .025, 0, -.09, 0), f3Cyl(.056, .053, .025, 0, -.19, 0)]),
  fist: () => f3Sph(.064, 0, -.055, .005, .9, 1, 1.05, 9, 7),
  // Baggy trousers: wider at the knee, gathered at the ankle.
  thigh: () => f3Cyl(.1, .128, .45, 0, -.215, 0, 10),
  shin: () => f3Cyl(.128, .07, .4, 0, -.18, 0, 10),
  boot: () => f3Merge([f3Cyl(.062, .066, .15, 0, .04, 0), f3Box(.11, .085, .25, 0, -.035, .05)]),
  sole: () => f3Box(.118, .025, .26, 0, -.0675, .05),
  hair_ren: () => f3Hair(.12, [[0, .2, -.04, 0, .75, -.66, .2, .055], [.05, .2, -.03, .45, .8, -.4, .17, .05], [-.05, .2, -.03, -.45, .8, -.4, .17, .05],
    [0, .14, -.09, 0, .2, -1, .17, .055], [.06, .08, -.08, .6, -.1, -.8, .13, .045], [-.06, .08, -.08, -.6, -.1, -.8, .13, .045],
    [.09, .13, -.02, 1, .25, -.1, .11, .04], [-.09, .13, -.02, -1, .25, -.1, .11, .04], [.01, .21, .04, .1, .9, .4, .14, .05],
    [0, .19, .07, 0, -.5, .87, .1, .035], [.04, .18, .07, .35, -.6, .7, .09, .03], [-.04, .18, .07, -.35, -.6, .7, .09, .03]]),
  hair_kael: () => f3Hair(.122, [[0, .21, -.02, 0, 1, -.3, .24, .06], [.05, .2, -.02, .5, .85, -.25, .2, .055], [-.05, .2, -.02, -.5, .85, -.25, .2, .055],
    [0, .17, -.08, 0, .5, -.87, .22, .06], [.06, .13, -.08, .55, .3, -.78, .18, .05], [-.06, .13, -.08, -.55, .3, -.78, .18, .05],
    [.09, .14, 0, .95, .3, .1, .14, .045], [-.09, .14, 0, -.95, .3, .1, .14, .045], [.085, .1, .03, .5, -.85, .2, .14, .035],
    [-.085, .1, .03, -.5, -.85, .2, .14, .035], [.02, .2, .05, .2, .6, .78, .15, .05], [-.02, .18, .075, -.2, -.5, .85, .11, .035]]),
};

// The outline shell's push per vertex: the mean of the distinct normals found at that position, lengthened so every
// face moves out by the full width (so box edges and cylinder rims stay closed); at most twice, on sharp tips.
function f3OutlineGeo(g) {
  const p = g.attributes.position, nr = g.attributes.normal, at = new Map(), out = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const key = Math.round(p.getX(i) * 1e4) + ',' + Math.round(p.getY(i) * 1e4) + ',' + Math.round(p.getZ(i) * 1e4);
    if (!at.has(key)) at.set(key, []);
    at.get(key).push(i);
  }
  for (const ids of at.values()) {
    const ns = [], a = new THREE.Vector3();
    for (const i of ids) { const n = new THREE.Vector3().fromBufferAttribute(nr, i); if (!ns.some(u => u.dot(n) > .999)) ns.push(n); }
    for (const n of ns) a.add(n);
    if (a.lengthSq() < 1e-8) a.copy(ns[0]); else a.normalize();
    let lo = 1;
    for (const n of ns) lo = Math.min(lo, a.dot(n));
    a.multiplyScalar(1 / Math.max(.5, lo));
    for (const i of ids) out.set([a.x, a.y, a.z], i * 3);
  }
  const o = new THREE.BufferGeometry();
  o.setAttribute('position', p); o.setAttribute('aOut', new THREE.BufferAttribute(out, 3)); o.setIndex(g.index);
  g.computeBoundingSphere(); o.boundingSphere = g.boundingSphere.clone(); o.boundingSphere.radius += 2 * F3_OUTLINE.w;
  return o;
}

// The shared gradient (3 bands), outline material and shapes, once.
function f3Shared() {
  if (F3.grad) return;
  const d = new Uint8Array([90, 90, 90, 255, 170, 170, 170, 255, 255, 255, 255, 255]);
  F3.grad = new THREE.DataTexture(d, 3, 1, THREE.RGBAFormat);
  F3.grad.minFilter = F3.grad.magFilter = THREE.NearestFilter; F3.grad.generateMipmaps = false; F3.grad.needsUpdate = true;
  F3.outMat = new THREE.ShaderMaterial({side: THREE.BackSide,
    uniforms: {uW: {value: F3_OUTLINE.w}, uColor: {value: new THREE.Color(F3_OUTLINE.color)}},
    vertexShader: 'attribute vec3 aOut;\nuniform float uW;\nvoid main(){ gl_Position = projectionMatrix * modelViewMatrix * vec4(position + aOut * uW, 1.); }',
    fragmentShader: 'uniform vec3 uColor;\nvoid main(){ gl_FragColor = vec4(uColor, 1.); }'});
  for (const k in F3_SHAPE) { const g = F3_SHAPE[k](); F3.geo[k] = g; F3.out.set(g, f3OutlineGeo(g)); }
}

// The fighters' light: a warm sun from the upper left (as in the painting, and a little in front) and a sky/stone fill.
function f3Lights() {
  const sun = new THREE.DirectionalLight(0xfff2dc, .75);
  sun.position.set(-4, 6, 5);
  return [sun, new THREE.HemisphereLight(0xdcecff, 0x6b5a4a, .5)];
}

// One fighter ('ren' | 'kael'): joints, toon parts with outlines, limb points and its own materials (so effects can
// flash one fighter). Not yet in the scene.
function fighterBuild(char) {
  f3Shared();
  const col = F3_COL[char], mats = {}, joints = {}, limbs = {}, root = new THREE.Group();
  for (const k in col) mats[k] = new THREE.MeshToonMaterial({color: col[k], gradientMap: F3.grad});
  for (const j of F3_J) { const b = F3_BONE[j], g = new THREE.Group(); g.position.set(b[1], b[2], b[3]); joints[j] = g; (b[0] ? joints[b[0]] : root).add(g); }
  for (const [j, slot, shape] of F3_PART) {
    const g = F3.geo[shape === 'hair' ? 'hair_' + char : shape], mesh = new THREE.Mesh(g, mats[slot]);
    mesh.name = j + '.' + shape;
    mesh.add(new THREE.Mesh(F3.out.get(g), F3.outMat));
    joints[j].add(mesh);
  }
  for (const l in F3_LIMB) { const b = F3_LIMB[l], o = new THREE.Object3D(); o.position.set(b[1], b[2], b[3]); joints[b[0]].add(o); limbs[l] = o; }
  return {root, joints, limbs, mats};
}

// Every drawn frame: each side's fighter at its sim position (feet at F.x, F.y; side 0 in front), facing and pose.
// S null (no match): hidden. Render-side smoothing: when the action changes to a free or movement one (F3_EASE), the
// pose eases from the last drawn one into the new action's over its first CFG.anim.blend frames (by F.af, so it
// follows the sim). Strikes, hits and throws snap: a strike shows exactly on its first active frame.
const F3_EASE = {idle: 1, walkF: 1, walkB: 1, crouch: 1, guard: 1, guardC: 1, jumpSquat: 1, air: 1, dashF: 1, dashB: 1, win: 1};
function f3Sync(S) {
  for (let i = 0; i < F3D.length; i++) {
    const it = F3D[i];
    it.root.visible = !!S;
    if (!S) { it.F = null; continue; }
    const F = fighterOf(S, i), n = CFG.anim.blend;
    it.root.position.set(F.x / 1000, F.y / 1000, i ? -.05 : .05);
    it.root.rotation.y = F.face * F3_YAW;
    let p = f3Raw(F, S);
    if (F !== it.F) it.from = null;   // a new fighter (new match or round): nothing to ease from
    else if (F.act !== it.act) it.from = F3_EASE[F.act] ? it.pose : null;
    if (it.from && F.af < n) p = f3Mix(it.from, p, Math.max(0, F.af) / n);
    it.F = F; it.act = F.act; it.pose = p;   // the drawn pose, legs solved below, ankle targets kept for the next ease
    f3Apply(it, f3Solve(p));
  }
}

function f3Apply(it, p) {
  const J = it.joints, D = F3_DEG, b = F3_BONE.pelvis;
  for (const j of F3_J) { const r = p[j]; J[j].rotation.set(r[0] * D, r[1] * D, r[2] * D); }
  J.pelvis.position.set(b[1] + p.pos[0], b[2] + p.pos[1], b[3] + p.pos[2]);
}

// World position (metres) of a limb point of side's fighter, as last posed.
function limbWorld(side, limb) { return F3D[side].limbs[limb].getWorldPosition(new THREE.Vector3()); }

// --- Poses --- (the key-pose table F3_KEY and the cosmetic timings are in e_poses.js)
function f3Lerp3(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
function f3Smooth(t) { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); }

// A key pose, resolved once (every joint, legs with a target solved).
function f3Key(name) {
  if (F3.memo[name]) return F3.memo[name];
  const k = F3_KEY[name], base = k.b ? f3Key(k.b) : null, p = {};
  for (const j of F3_J) p[j] = (k[j] || (base ? base[j] : [0, 0, 0])).slice();
  p.pos = (k.pos || (base ? base.pos : [0, 0, 0])).slice();
  [['fL', 'hipL', 'knL', 'anL'], ['fR', 'hipR', 'knR', 'anR']].forEach(([f, h, kn, an], side) => {
    const t = k[f] || (!k[h] && !k[kn] && !k[an] && base && base[f]);
    if (t) { p[f] = t.slice(); f3Leg(p, side, p[f]); }
  });
  return F3.memo[name] = p;
}

// The pose between a and b (t from 0 to 1); ankle targets blend when both poses have one.
function f3Mix(a, b, t) {
  const o = {pos: f3Lerp3(a.pos, b.pos, t)};
  for (const j of F3_J) o[j] = f3Lerp3(a[j], b[j], t);
  if (a.fL && b.fL) o.fL = f3Lerp3(a.fL, b.fL, t);
  if (a.fR && b.fR) o.fR = f3Lerp3(a.fR, b.fR, t);
  return o;
}

// Two-bone IK for one leg (side 0 left, 1 right): hip flexion and abduction and knee bend so the ankle reaches t
// (model space), then the ankle undoes the chain so the sole is level and turned with the pelvis.
function f3Leg(p, side, t) {
  const B = F3_BONE, h = side ? B.hipR : B.hipL, L1 = -B.knL[2], L2 = -B.anL[2], D = F3_DEG, v = F3.v, m = F3.m, m2 = F3.m2, e = F3.e;
  const P = p.pelvis, pel = F3.m3.makeRotationFromEuler(e.set(P[0] * D, P[1] * D, P[2] * D));
  // The target from the hip, in the pelvis frame.
  v.set(h[1], h[2], h[3]).applyMatrix4(pel);
  v.set(t[0] - B.pelvis[1] - p.pos[0] - v.x, t[1] - B.pelvis[2] - p.pos[1] - v.y, t[2] - B.pelvis[3] - p.pos[2] - v.z);
  v.applyMatrix4(m.copy(pel).transpose());
  const len = v.length(), d = Math.min(L1 + L2 - 1e-4, Math.max(.05, len));
  v.multiplyScalar(d / len);
  // Knee bend from the distance; the bent leg (ankle at (0, vy, vz) in the hip frame) turned onto the target:
  // abduction g about z, then flexion a about x.
  const cosK = Math.max(-1, Math.min(1, (d * d - L1 * L1 - L2 * L2) / (2 * L1 * L2))), k = Math.acos(cosK);
  const vy = -L1 - L2 * cosK, vz = -L2 * Math.sin(k), g = Math.asin(Math.max(-1, Math.min(1, -v.x / vy)));
  let a = Math.atan2(v.z, v.y) - Math.atan2(vz, vy * Math.cos(g));
  a = Math.atan2(Math.sin(a), Math.cos(a));
  p[side ? 'hipR' : 'hipL'] = [a / D, 0, g / D]; p[side ? 'knR' : 'knL'] = [k / D, 0, 0];
  // Ankle = (pelvis * hip * knee)^-1 * (the pelvis's turn): the sole level, pointing where the hips point.
  m.copy(pel).multiply(m2.makeRotationFromEuler(e.set(a, 0, g))).multiply(m2.makeRotationX(k)).transpose();
  e.setFromRotationMatrix(m.multiply(m2.makeRotationY(P[1] * D)));
  p[side ? 'anR' : 'anL'] = [e.x / D, e.y / D, e.z / D];
}

// Legs with a target solved, then only the joints and pos (a fresh object).
function f3Solve(p) {
  if (p.fL) f3Leg(p, 0, p.fL);
  if (p.fR) f3Leg(p, 1, p.fR);
  const o = {pos: p.pos};
  for (const j of F3_J) o[j] = p[j];
  return o;
}

// The pose of fighter F now: a pure function of F.act, F.af, F.x and F.face (walk), F.air, F.vy, F.hit (throw),
// F.stun (hit and block recovery), F.prev (a block with down held is crouched), F.land (landing) and S.frame (breathing).
function poseOf(F, S) { return f3Solve(f3Raw(F, S)); }
// The same before the legs are solved (ankle targets kept, for blending). Crouched on the ground (the sim's crouching
// hurtbox: crouch, guardC, the crouching moves, a block with down held) the head stays within F3_HEADROOM of the
// hurtbox's top: if a pose would raise it higher, the pelvis drops by the difference (the planted feet follow by IK).
const F3_HEADROOM = .1;
function f3Raw(F, S) {
  const m = CFG.moves[F.act], p = m ? f3Move(F, m) : f3Act(F, S);
  if (F.air) return p;
  const top = (hurtBoxes(F)[1].y1 - F.y) / 1000;
  if (top < CFG.body.h / 1000) {
    const over = f3Point(p, F3_HEAD, 0, .11, .01)[1] + F3_HEAD_R - top - F3_HEADROOM;
    if (over > 0) p.pos = [p.pos[0], p.pos[1] - over, p.pos[2]];
  }
  return p;
}

// Moves follow their frame data: from the posture to the wind-up by the end of startup, the strike held through the
// active frames, back to the posture by the end of recovery; kicks fold back through the wind-up (the chamber) first.
// Air moves hold a recovery pose until landing: kicks the chamber, punches most of the way back to the air pose.
function f3Move(F, m) {
  const id = F.act, af = F.af, air = m.r === 'land', from = air ? f3Air(F) : f3Key(F3_FROM[id] || 'stance');
  const W = F3_KEY[id + 'W'] ? f3Key(id + 'W') : from, H = F3_KEY[id + 'H'] ? f3Key(id + 'H') : from;
  if (af <= m.s) return f3Mix(from, W, f3Smooth(af / m.s));
  if (af <= m.s + m.a) return f3Mix(H, H, 0);
  const kick = m.limb[0] === 'f', since = af - m.s - m.a;
  if (air) return kick ? f3Mix(H, W, f3Smooth(since / 8)) : f3Mix(H, from, .6 * f3Smooth(since / 8));
  const t = since / m.r;
  if (kick) return t < .5 ? f3Mix(H, W, f3Smooth(2 * t)) : f3Mix(W, from, f3Smooth(2 * t - 1));
  return f3Mix(H, from, f3Smooth(t));
}

// The air pose: tucked while rising, legs reaching down while falling.
function f3Air(F) { return f3Mix(f3Key('airUp'), f3Key('airDown'), f3Smooth((CFG.jump.v - F.vy) / (2 * CFG.jump.v))); }

function f3Act(F, S) {
  const K = f3Key, af = F.af, st = K('stance');
  switch (F.act) {
    case 'walkF': case 'walkB': return f3Walk(F);
    case 'crouch': case 'guard': case 'guardC': return f3Breathe(f3Mix(K(F.act), K(F.act), 0), S);
    case 'jumpSquat': return f3Mix(K('squat'), K('squat'), 0);
    case 'landing': return f3Mix(K('squat'), st, f3Smooth(af / Math.max(1, F.land)));
    case 'air': return f3Air(F);
    case 'dashF': case 'dashB': return f3Mix(K(F.act), K(F.act), 0);
    // Block and hit snap into their recoil on the contact frame (it holds through the hitstop), then ease back to the
    // guard / the stance as the stun runs out. A block with down held is the crouching block (as in the sim).
    case 'block': {
      const low = F.prev & BTN.D;
      return f3Mix(K(low ? 'guardC' : 'guard'), K(low ? 'blockHitC' : 'blockHit'), f3Smooth(F.stun / 6));
    }
    case 'hitStun': return f3Mix(st, K('hurt'), f3Smooth(F.stun / 8));
    case 'juggle': case 'knock': case 'ko': {   // flying (tilting back as it falls), then lying on the floor
      if (F.air) return f3Mix(K('flyUp'), K('flyDown'), f3Smooth((60 - F.vy) / 140));
      const down = K(F.act === 'ko' ? 'koDown' : 'down');
      return f3Mix(down, down, 0);
    }
    case 'getup': return af < 5 ? f3Mix(K('down'), K('sit'), f3Smooth(af / 5)) : af < 10 ? f3Mix(K('sit'), K('kneel'), f3Smooth((af - 5) / 5))
      : f3Mix(K('kneel'), st, f3Smooth((af - 10) / 6));
    case 'rollF': case 'rollB': return f3Roll(F);
    case 'thr': return f3Throw(F);
    case 'thrWhiff': return f3Mix(K('reach'), st, f3Smooth((af - 4) / 18));
    case 'thrown': return f3Mix(K('held'), K('held'), 0);
    case 'spec': return f3Spec(af);
    case 'win': return f3Breathe(f3Mix(K('win'), K('win'), 0), S);
    case 'intro': return f3Breathe(f3Mix(K('intro'), K('intro'), 0), S);
    default: return f3Breathe(f3Mix(st, st, 0), S);   // idle
  }
}

// Breathing on the free stances: the chest and shoulders rise and fall (the IK keeps the feet planted).
function f3Breathe(p, S) {
  const B = F3_BREATH, b = Math.sin(S.frame * B.rate);
  p.chest[0] += B.chest * b; p.pos[1] += B.rise * b; p.shL[2] += B.chest * b; p.shR[2] -= B.chest * b;
  return p;
}

// Walk: the stance's feet step along the walking line (the world x axis seen from the model) by distance, F.x * face:
// each foot is planted for half a stride, moving back under the body exactly as far as the body moves, then swings.
function f3Walk(F) {
  const W = F3_WALK, k = f3Smooth(F.af / W.fade), p = f3Mix(f3Key('stance'), f3Key(F.act), k);
  const ph = F.x * F.face / 1000 / W.stride, wx = F.face * Math.cos(F3_YAW), wz = Math.sin(F3_YAW), D = W.stride / 2;
  [['fL', 0], ['fR', .5]].forEach(([f, o]) => {
    const u = ((ph + o) % 1 + 1) % 1, sw = u >= .5, s = sw ? D * (2 * u - 1.5) : D * (.5 - 2 * u);
    const t = p[f], lift = sw ? W.lift * Math.sin(Math.PI * (2 * u - 1)) : 0;
    p[f] = [t[0] + wx * s * k, t[1] + lift * k, t[2] + wz * s * k];
  });
  return p;
}

// Rolls: lying on the back the body tucks into a ball, which then tumbles (450° forward, 270° back: both end upright)
// about its own centre, opens into the crouch (the feet go straight down to the floor: IK from where the ball's feet
// are) and rises into the stance; F3_TUCK (e_poses.js) is the ball's centre and radius.
function f3Roll(F) {
  const t = F.af / CFG.knock.roll, spin = F.act === 'rollF' ? 450 : -270, cr = f3Key('crouch');
  if (t >= .8) return f3Mix(cr, f3Key('stance'), f3Smooth((t - .8) / .2));
  const a = -90 + spin * f3Smooth((t - .15) / .6), r = a * F3_DEG, c = F3_TUCK, p = f3Mix(f3Key('down'), f3Key('tuck'), f3Smooth(t / .2));
  const y = c.r - F3_BONE.pelvis[2] - (c.y * Math.cos(r) - c.z * Math.sin(r)), z = -(c.y * Math.sin(r) + c.z * Math.cos(r));
  p.pelvis[0] = a; p.pos = f3Lerp3(f3Key('down').pos, [0, y, z], f3Smooth(t / .2));
  if (t < .65) return p;
  const end = f3Mix(cr, cr, 0);
  end.pelvis[0] += spin - 90;   // the crouch's pitch, after the whole turn
  p.fL = f3Ankle(p, 0); p.fR = f3Ankle(p, 1);
  return f3Mix(p, end, f3Smooth((t - .65) / .15));
}

// Model-space position of point (x, y, z) of the last joint of chain (root first) in pose p: forward kinematics, as
// the rig computes it. F3_HEAD = the chain to the head; F3_HEAD_R = the head sphere's largest radius (its centre is at
// (0, .11, .01) in the head frame, see the head shape).
const F3_HEAD = ['pelvis', 'spine', 'chest', 'neck', 'head'], F3_HEAD_R = .1155;
function f3Point(p, chain, x, y, z) {
  const v = F3.v.set(x, y, z), D = F3_DEG;
  for (let i = chain.length - 1; i >= 0; i--) {
    const j = chain[i], r = p[j], b = F3_BONE[j], o = j === 'pelvis' ? p.pos : [0, 0, 0];
    v.applyMatrix4(F3.m.makeRotationFromEuler(F3.e.set(r[0] * D, r[1] * D, r[2] * D)));
    v.set(v.x + b[1] + o[0], v.y + b[2] + o[1], v.z + b[3] + o[2]);
  }
  return [v.x, v.y, v.z];
}
function f3Ankle(p, side) { return f3Point(p, side ? ['pelvis', 'hipR', 'knR', 'anR'] : ['pelvis', 'hipL', 'knL', 'anL'], 0, 0, 0); }

// Throw: the reach on the attempt (a miss goes on in thrWhiff); after a grab (F.hit, af from 1 again) hold, pull back
// and shove at thr.hitF, the frame the throw hits, then back to the stance.
function f3Throw(F) {
  const K = f3Key, af = F.af, t = CFG.thr;
  if (!F.hit) return f3Mix(K('stance'), K('reach'), f3Smooth(af / t.s));
  if (af <= t.hitF - 8) return f3Mix(K('reach'), K('clinch'), f3Smooth(af / 6));
  if (af < t.hitF) return f3Mix(K('clinch'), K('tossW'), f3Smooth((af - t.hitF + 8) / 6));
  return f3Mix(K('toss'), K('stance'), f3Smooth((af - t.hitF - 2) / (t.anim - t.hitF - 2)));
}

// Special: charge until 2 frames before the shot, thrust on the spawn frame, hold, then back to the stance.
function f3Spec(af) {
  const K = f3Key, n = CFG.spec.spawn, r = CFG.spec.rec;
  if (af <= n - 2) return f3Mix(K('stance'), K('specW'), f3Smooth(af / (n - 2)));
  if (af <= n) return f3Mix(K('specW'), K('specH'), f3Smooth((af - n + 2) / 2));
  return f3Mix(K('specH'), K('stance'), f3Smooth((af - n - 10) / (r - 10)));
}
