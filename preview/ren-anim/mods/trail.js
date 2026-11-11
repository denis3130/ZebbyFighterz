// --- trail.js: the heavy hits' trail. ---
// Only moves of the heavy class (CFG.moves stop 'heavy') draw one: a smooth, tapering arc of Ren's cyan behind the
// hitting limb, along the path it really travels. The path is sampled once per move from the pose itself at quarter
// frames (RN.pure is a pure function of the frame), so the arc has no corners however fast the limb is. It is drawn
// pushed away from the camera, so the body always covers it: it shows around the limb, never on top of it.
const RT = {step: .25, before: 5.5, span: 4.5, n: 26, w: .055, back: 1.2, paths: {}, mesh: null, v: [0, 1, 2, 3].map(() => new THREE.Vector3())};

// The limb's path (model space) of heavy move id: frames s - before .. s + 1 (the first active frame), every RT.step.
function rtPath(md, key, id) {
  if (RT.paths[id]) return RT.paths[id];
  const m = CFG.moves[id], e = CFG.clips[id] || {}, limb = e.limb || (e.up && e.up.limb) || m.limb, meta = md.meta.limbs[limb], bi = md.index[meta.b];
  const F = {side: 0, char: key, x: 0, y: 0, vx: 0, vy: 0, face: 1, act: id, af: 0, air: m.r === 'land', hit: 0, stun: 0, prev: 0}, S = {frame: 0, sides: [{team: [F], cur: 0}]};
  const a0 = m.s - RT.before, pts = [];
  for (let af = a0; af <= m.s + 1 + 1e-6; af += RT.step) {
    F.af = Math.max(0, af);
    const W = rbFK(md, RN.pure(md, F, S), RB.W);
    pts.push(new THREE.Vector3().fromArray(meta.p).applyQuaternion(W.q[bi]).add(W.p[bi]));
  }
  return RT.paths[id] = {a0, pts};
}

RN.hooks.boot.push(VW => {
  const g = new THREE.BufferGeometry(), n = RT.n, idx = [];
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 6), 3));
  g.setAttribute('aA', new THREE.BufferAttribute(new Float32Array(n * 2), 1));
  for (let i = 0; i + 1 < n; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  g.setIndex(idx);
  RT.mesh = new THREE.Mesh(g, new THREE.ShaderMaterial({transparent: true, depthWrite: false, side: THREE.DoubleSide, uniforms: {uBack: {value: RT.back}},
    vertexShader: 'attribute float aA; uniform float uBack; varying float vA;\nvoid main(){ vA = aA; vec4 mv = modelViewMatrix * vec4(position, 1.0); mv.xyz += normalize(mv.xyz) * uBack; gl_Position = projectionMatrix * mv; }',
    fragmentShader: 'varying float vA;\nvoid main(){ gl_FragColor = vec4(mix(vec3(.21, .85, 1.), vec3(1.), vA * vA * .85), vA * .9); }'}));
  RT.mesh.frustumCulled = false; RT.mesh.visible = false;
  VW.it.body.add(RT.mesh);
  for (const id in CFG.moves) if (CFG.moves[id].stop === 'heavy') rtPath(mdData(VW.it.key), VW.it.key, id);   // sampled once, at the start
});
RN.hooks.opt.push(k => { if (k === 'on' && RT.mesh) RT.mesh.visible = false; });

RN.hooks.draw.push((VW, dt, cam) => {
  const F = VW.F, m = CFG.moves[F.act], it = VW.it, mesh = RT.mesh, af = RN_D.F ? RN_D.F.af : F.af;
  const live = m && m.stop === 'heavy' && af > m.s - RT.before + 1 && af < m.s + 1 + 9;
  mesh.visible = !!live;
  if (!live) return;
  const P = rtPath(mdData(it.key), it.key, F.act), pts = P.pts, last = pts.length - 1, v = RT.v;
  // the head runs with the limb up to the first active frame; after it the tail catches up and the arc fades
  const after = Math.max(0, af - (m.s + 1)) / 9, head = Math.min(last, (Math.min(af, m.s + 1) - P.a0) / RT.step);
  const tail = Math.max(0, head - RT.span / RT.step * (1 - after)), fade = 1 - after;
  const pos = mesh.geometry.attributes.position.array, aA = mesh.geometry.attributes.aA.array, n = RT.n;
  const eye = it.body.worldToLocal(v[0].copy(cam.position));
  const at = (x, out) => { const i = Math.min(last - 1, Math.floor(x)), k = x - i; return out.lerpVectors(pts[i], pts[i + 1], k); };
  for (let i = 0; i < n; i++) {
    const u = i / (n - 1), x = tail + (head - tail) * u, c = at(x, v[1]);
    const tan = at(Math.min(last, x + .5), v[2]).sub(at(Math.max(0, x - .5), v[3])), side = tan.cross(v[3].subVectors(eye, c));
    const w = RT.w * Math.pow(u, .7) * (1 - .75 * rnSm((u - .8) / .2));   // thin at the tail, full near the head, a point at the limb
    if (side.lengthSq() < 1e-12) side.set(0, 1, 0);
    side.normalize().multiplyScalar(w);
    pos[i * 6] = c.x + side.x; pos[i * 6 + 1] = c.y + side.y; pos[i * 6 + 2] = c.z + side.z;
    pos[i * 6 + 3] = c.x - side.x; pos[i * 6 + 4] = c.y - side.y; pos[i * 6 + 5] = c.z - side.z;
    aA[i * 2] = aA[i * 2 + 1] = Math.pow(u, 1.4) * fade * (head - tail > 1 ? 1 : 0);
  }
  mesh.geometry.attributes.position.needsUpdate = mesh.geometry.attributes.aA.needsUpdate = true;
});
