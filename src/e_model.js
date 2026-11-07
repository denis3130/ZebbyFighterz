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
function modelBuild(key) {
  const md = mdData(key);
  if (!md) return null;
  f3Shared();
  const root = new THREE.Group(), body = new THREE.Group(), s = CFG.body.h / 1000 / md.meta.height;
  body.scale.setScalar(s); root.add(body);
  const bones = md.bones.map(b => { const o = new THREE.Bone(); o.name = b.n; o.position.fromArray(b.t); o.quaternion.fromArray(b.q); return o; });
  md.bones.forEach((b, i) => (b.p < 0 ? body : bones[b.p]).add(bones[i]));
  // The texture appears once decoded; until then the mesh draws with an empty map (no error, no warning).
  const img = new Image(), tex = new THREE.Texture(img);
  tex.flipY = false;   // glTF UVs
  img.src = ASSETS[key + '/' + key + '.jpg'];
  img.decode().then(() => { tex.needsUpdate = true; }, () => {});
  const main = new THREE.MeshToonMaterial({map: tex, gradientMap: F3.grad, skinning: true});
  const line = new THREE.MeshBasicMaterial({color: F3_OUTLINE.color, side: THREE.BackSide, skinning: true}), w = (MD_OUTLINE / s).toFixed(5);
  line.onBeforeCompile = sh => { sh.vertexShader = sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\ttransformed += normal * ' + w + ';'); };
  const mesh = new THREE.SkinnedMesh(md.geo, main), outline = new THREE.SkinnedMesh(md.geo, line);
  mesh.frustumCulled = outline.frustumCulled = false;
  body.add(mesh, outline);
  root.updateMatrixWorld(true);
  const skel = new THREE.Skeleton(bones);
  mesh.bind(skel); outline.bind(skel);
  const limbs = {}, B = n => bones[md.index[n]];
  for (const l in md.meta.limbs) { const d = md.meta.limbs[l], o = new THREE.Object3D(); o.position.fromArray(d.p); B(d.b).add(o); limbs[l] = o; }
  return {kind: 'model', key, root, body, bones, mesh, outline, headEnd: B(md.meta.head), limbs, mats: {main},
    joints: {pelvis: B('Hips'), chest: B('Spine'), neck: B('neck'), head: B('Head')}};
}

// --- Poses: {q: local rotations, nb x 4, h: the Hips' local position} ---
// The rest pose of md (the bind pose).
function mdRest(md) {
  const q = new Float32Array(md.nb * 4);
  md.bones.forEach((b, i) => q.set(b.q, i * 4));
  return {q, h: Float32Array.from(md.bones[0].t)};
}

// The pose of fighter F now (its character's package), or null when it has none. Pure: only F and S.
function mdPoseOf(F, S) {
  const md = mdData(F.char);
  return md ? mdRest(md) : null;
}

// a and b blended: k = 0 is a, 1 is b (slerp per bone, lerp of the Hips).
const MD_QA = new THREE.Quaternion(), MD_QB = new THREE.Quaternion();
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
// face * F3_YAW, a change to a free or movement act eased in over CFG.anim.blend frames by F.af).
function mdSync(it, side, S) {
  it.root.visible = !!S;
  if (!S) { it.F = null; return; }
  const F = fighterOf(S, side), n = CFG.anim.blend;
  it.root.position.set(F.x / 1000, F.y / 1000, side ? -.05 : .05);
  it.root.rotation.y = F.face * F3_YAW;
  let p = mdPoseOf(F, S) || mdRest(mdData(it.key));
  if (F !== it.F) it.from = null;
  else if (F.act !== it.act) it.from = F3_EASE[F.act] ? it.pose : null;
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
