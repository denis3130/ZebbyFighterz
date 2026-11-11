// --- hair.js: the hair follows the head a little late (a little, natural). ---
// The hair is one mesh with the head, so it moves in the vertex shader: the vertices away from the skull (the spikes
// and the locks, more toward their tips) are shifted by one vector, the lag of a damped spring that follows the top of
// the head once per sim frame. The head's toon mesh, its outline and the fringe get the same shift.
const RH = {u: {value: new THREE.Vector3()}, x: new THREE.Vector3(), v: new THREE.Vector3(), a: new THREE.Vector3(), d: new THREE.Vector3(), o: new THREE.Vector3(),
  m: new THREE.Matrix4(), frame: -1e9, bone: -1, k: .22, damp: .7, max: .045, ready: false};
RN.hooks.boot.push(VW => {
  const it = VW.it;
  if (!it.head) return;
  const hook = mat => {
    const prev = mat.onBeforeCompile, key = mat.customProgramCacheKey ? mat.customProgramCacheKey() : '';
    mat.onBeforeCompile = (sh, r) => {
      if (prev) prev(sh, r);
      sh.uniforms.uHair = RH.u;
      sh.vertexShader = 'uniform vec3 uHair;\n' + sh.vertexShader.replace('#include <begin_vertex>',
        '#include <begin_vertex>\n\ttransformed += uHair * (smoothstep(.105, .2, distance(position, vec3(.008, 1.6, -.01))) * smoothstep(1.57, 1.66, position.y));');
    };
    mat.customProgramCacheKey = () => key + '|hair'; mat.needsUpdate = true;
  };
  for (const o of it.body.children) if (o.isSkinnedMesh && (o.geometry === it.head.geometry || o === it.fringe)) hook(o.material);
  RH.bone = it.head.skeleton.bones.findIndex(b => b.name === 'Head'); RH.ready = RH.bone >= 0;
});
RN.hooks.opt.push((k, v) => { if (k === 'on' && !v) RH.u.value.set(0, 0, 0); });
RN.hooks.reset.push(() => { RH.frame = -1e9; });
RN.hooks.applied.push((it, F, S) => {
  if (!RH.ready) return;
  const frame = S.int ? S.int.frame : Math.floor(S.frame), sk = it.head.skeleton;
  it.root.updateMatrixWorld(true);
  it.headEnd.getWorldPosition(RH.a);
  let n = frame - RH.frame; RH.frame = frame;
  if (n < 0 || n > 8) { RH.x.copy(RH.a); RH.v.set(0, 0, 0); n = 0; }   // a new start: the hair at rest
  for (let i = 0; i < Math.min(n, 3); i++) { RH.v.addScaledVector(RH.d.subVectors(RH.a, RH.x), RH.k).multiplyScalar(RH.damp); RH.x.add(RH.v); }
  const d = RH.d.subVectors(RH.x, RH.a), l = d.length();
  if (l > RH.max) { d.multiplyScalar(RH.max / l); RH.x.addVectors(RH.a, d); }
  // the world shift as a shift of the bind pose (through the head bone's skinning matrix)
  RH.m.multiplyMatrices(sk.bones[RH.bone].matrixWorld, sk.boneInverses[RH.bone]).invert();
  RH.u.value.copy(d).applyMatrix4(RH.m).sub(RH.o.set(0, 0, 0).applyMatrix4(RH.m));
});
