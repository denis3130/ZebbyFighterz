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
// Where CFG.looks[key] asks for them, the look data's parts: finger bones (fists), hair spikes, the face's thin outline,
// the face's flat light, the outline's own width, the face's shape and its decal (the drawn features).
function modelBuild(key) {
  const md = mdData(key);
  if (!md) return null;
  f3Shared();
  const root = new THREE.Group(), body = new THREE.Group(), s = CFG.body.h / 1000 / md.meta.height;
  body.scale.setScalar(s); root.add(body);
  const bones = md.bones.map(b => { const o = new THREE.Bone(); o.name = b.n; o.position.fromArray(b.t); o.quaternion.fromArray(b.q); return o; });
  md.bones.forEach((b, i) => (b.p < 0 ? body : bones[b.p]).add(bones[i]));
  const B = n => bones[md.index[n]], lk = CFG.looks[key] || {}, look = (lk.fists || lk.spikes || lk.faceLine || lk.flatFace || lk.sash || lk.faceShape || lk.smoothNormals) && mdLookData(md, key);
  const head = lk.head && mdHeadData(md, key);   // the new head (its old one, neck and collar's top hidden)
  // fists: the fingers' bones under the hands (after the package's in the skeleton, as the look's skin counts them)
  const fingers = look && lk.fists ? look.fingers.map(f => { const o = new THREE.Bone(); o.name = f.n; o.position.fromArray(f.t); return o; }) : [];
  fingers.forEach((o, k) => (B(look.fingers[k].p) || fingers.find(g => g.name === look.fingers[k].p)).add(o));
  // sash: a chain of bones under the Hips for each ribbon (after the fingers in the skeleton)
  const sash = look && lk.sash && look.sash ? look.sash.ribbons.map(r => r.j.slice(0, -1).map((p, k) => {
    const o = new THREE.Bone(); o.name = 'Sash' + k; o.position.fromArray(k ? p.map((v, i) => v - r.j[k - 1][i]) : p); return o; })) : [];
  sash.forEach(ch => ch.forEach((o, k) => (k ? ch[k - 1] : B('Hips')).add(o)));
  const per = look && lk.faceLine ? ' * aLine' : '', flat = look && lk.flatFace, shape = look && lk.faceShape && !head && look.move;   // (with the new head: the old head is hidden and the old collar keeps its own shape, its pulled points stuck out beside the new collar)
  const smoothN = look && lk.smoothNormals && look.nor;   // (the light's normals smoothed: clean bands, not Meshy's lumps)
  const geo = fingers.length || per || flat || shape || head || smoothN ? new THREE.BufferGeometry() : md.geo;
  if (geo !== md.geo) {   // the package's geometry, its attributes shared (not copied), with the look's skin and outline widths
    for (const a in md.geo.attributes) geo.setAttribute(a, md.geo.attributes[a]);
    geo.setIndex(md.geo.index);
    if (head) {   // without the triangles the new head replaces
      const src = md.geo.index.array, drop = new Uint8Array(src.length / 3), keep = [];
      head.hide.forEach(t => { drop[t] = 1; });
      for (let t = 0; t < drop.length; t++) if (!drop[t]) keep.push(src[3 * t], src[3 * t + 1], src[3 * t + 2]);
      geo.setIndex(new THREE.BufferAttribute(src instanceof Uint32Array ? Uint32Array.from(keep) : Uint16Array.from(keep), 1));
    }
    if (fingers.length) { geo.setAttribute('skinIndex', look.skin[0]); geo.setAttribute('skinWeight', look.skin[1]); }
    if (smoothN) { geo.userData.bindNormal = md.geo.attributes.normal; geo.setAttribute('normal', look.nor); }
    if (per) geo.setAttribute('aLine', look.line);
    if (flat) geo.setAttribute('aFlat', look.flat);
    if (shape) {   // the face's shape: copies of the positions and normals, the moved vertices changed
      const p = new Float32Array(md.geo.attributes.position.array), n = new Float32Array((smoothN || md.geo.attributes.normal).array), m = look.move;
      m.idx.forEach((v, i) => { p.set(m.pos.subarray(i * 3, i * 3 + 3), v * 3); n.set(m.nor.subarray(i * 3, i * 3 + 3), v * 3); });
      geo.setAttribute('position', new THREE.BufferAttribute(p, 3)); geo.setAttribute('normal', new THREE.BufferAttribute(n, 3));
    }
  }
  // The texture appears once decoded; until then the mesh draws with an empty map (no error, no warning).
  const img = new Image(), tex = new THREE.Texture(img);
  tex.flipY = false;   // glTF UVs
  img.src = (lk.paint && (ASSETS[key + '/' + key + '_painted.png'] || ASSETS[key + '/' + key + '_painted.jpg'])) || ASSETS[key + '/' + key + '.jpg'];   // (the look's: the drawing painted on it; a PNG for flat colours, tools/kael_body.py)
  img.decode().then(() => { tex.needsUpdate = true; }, () => {});
  const main = new THREE.MeshToonMaterial({map: tex, gradientMap: F3.grad, skinning: true});
  if (flat) {   // the look's flat light: per vertex, the share of the texture's own colour (the face's drawn shading)
    main.onBeforeCompile = sh => {
      sh.vertexShader = 'attribute float aFlat;\nvarying float vFlat;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\tvFlat = aFlat;');
      sh.fragmentShader = 'varying float vFlat;\n' + sh.fragmentShader.replace('vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;',
        '$&\n\toutgoingLight = mix(outgoingLight, diffuseColor.rgb + totalEmissiveRadiance, vFlat);');
    };
    main.customProgramCacheKey = () => 'flat';
  }
  // the face decal (look data face, ASSETS '<char>/<char>_face.png'): shown once decoded (an empty texture reads black)
  const face = shape && look.face && !head && ASSETS[key + '/' + key + '_face.png'] ? {tex: new THREE.Texture(new Image()), on: {value: 0}, want: true, ready: false} : null;   // (not under the new head: the old face is hidden)
  if (face) {
    const fd = look.face, dp = fd.depth;   // the face's and the neck's surface seen from the front, as a small texture (mdFaceMat)
    face.depth = new THREE.DataTexture(Uint8Array.from({length: dp.n[0] * dp.n[1] * 4}, (_, i) => i % 4 === 0 ? dp.map[i >> 2] : i % 4 === 3 ? 255 : 0), dp.n[0], dp.n[1], THREE.RGBAFormat);
    face.depth.magFilter = face.depth.minFilter = THREE.LinearFilter; face.depth.generateMipmaps = false; face.depth.needsUpdate = true;
    face.depthBox = new THREE.Vector4(dp.box[0], dp.box[1], 1 / (dp.box[2] - dp.box[0]), 1 / (dp.box[3] - dp.box[1]));
    face.depthZ = new THREE.Vector4(dp.z[0], dp.z[1] - dp.z[0], fd.seen, 0); face.depthCell = new THREE.Vector2(.5 / dp.n[0], .5 / dp.n[1]);
    // the decal's mapping: bind x, y -> the drawing's px (scale, cx, by) -> the decal's box; where it fades as it turns away
    face.map = new THREE.Vector3(...fd.fit); face.decal = new THREE.Vector4(...fd.decal); face.front = new THREE.Vector2(...fd.front);
    const jw = fd.jaw;   // the shadow under the jaw: per angle around the neck, the jaw's edge height (r) and the band's depth (g)
    face.jaw = new THREE.DataTexture(Uint8Array.from({length: jw.th[2] * 4}, (_, i) => i % 4 < 2 ? jw.map[(i >> 2) * 2 + i % 4] : i % 4 === 3 ? 255 : 0), jw.th[2], 1, THREE.RGBAFormat);
    face.jaw.magFilter = face.jaw.minFilter = THREE.LinearFilter; face.jaw.generateMipmaps = false; face.jaw.needsUpdate = true;
    face.jawAxis = new THREE.Vector2(...jw.axis); face.jawTh = new THREE.Vector3(...jw.th); face.jawY = new THREE.Vector4(jw.y[0], jw.y[1] - jw.y[0], jw.deep, jw.up);
    face.shade = new THREE.Vector3(...fd.shade);
    face.tex.flipY = false; face.tex.image.src = ASSETS[key + '/' + key + '_face.png'];
    face.tex.image.decode().then(() => { face.tex.needsUpdate = true; face.ready = true; mdFaceShow(face, face.want); }, () => {});
    mdFaceMat(main, face);
  }
  const ol = lk.line || {w: MD_OUTLINE, back: 0}, line = mdLineMat({skinning: true, w: (ol.w / s).toFixed(5), per, back: ol.back});
  // (with the new head's lining: the vest's lapels also drawn from behind in their paint, not their outline's black; and
  // their folded corners, noline, left out of the outline: pushed out past the lining it drew a black Z over the shirt,
  // and only pushed back, slid aside, as black dashes beside them)
  const src = md.geo.index.array, ln = head && head.lining, nl = head && head.noline;
  const mesh = new THREE.SkinnedMesh(ln ? mdTris(geo, src, head.hide, [], ln) : geo, main), outline = new THREE.SkinnedMesh(nl ? mdTris(geo, src, head.hide, nl) : geo, line);
  mesh.frustumCulled = outline.frustumCulled = false;
  body.add(mesh, outline);
  root.updateMatrixWorld(true);
  const skel = new THREE.Skeleton(bones.concat(fingers, ...sash));
  mesh.bind(skel); outline.bind(skel);
  if (head) {   // the new head: its own toon mesh and outline on the same skeleton (bound in the body, as the body's)
    const tex = new THREE.Texture(new Image()); tex.flipY = false; tex.image.src = head.jpg;
    tex.anisotropy = 4;   // (its flat colours and thin lines stay sharp on the surfaces seen at a slant: the mane's sides)
    tex.image.decode().then(() => { tex.needsUpdate = true; }, () => {});
    // (both sides: the bust is cut above the shoulders, its coat open there; seen into it, the outline's inner shell
    // showed as black patches on the shoulders: now the coat's own colour, as a lining)
    const hm = new THREE.MeshToonMaterial({map: tex, gradientMap: F3.grad, skinning: true, side: THREE.DoubleSide});
    // flat light: the sheet's own shading is in its texture (the hit flash's emissive kept); per vertex where the head
    // says so (aFlat: its collar's outside lit as the body, one teal with the vest)
    const hideU = head.geo.attributes.aHide ? {value: new THREE.Vector2()} : null;
    const headFlat = (perV, hu) => sh => {
      if (perV) sh.vertexShader = 'attribute float aFlat;\nvarying float vFlat;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\tvFlat = aFlat;');
      sh.fragmentShader = (perV ? 'varying float vFlat;\n' : '') + sh.fragmentShader.replace('vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;',
        '$&\n\toutgoingLight = mix(outgoingLight, diffuseColor.rgb + totalEmissiveRadiance, ' + (perV ? 'vFlat * ' : '') + MD_HEAD_FLAT.toFixed(2) + ');');
      if (hu) {   // (Kael's head)
        mdHideShader(sh, hu);
        // (a lock is one sheet: seen from behind, where a lock before it is hidden or across the forehead from the other side, it showed its
        // outer side's light paint, pale flakes with no outline. Its inner side: the hair's shadow tone, as the drawings' under-hair)
        sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', '#include <map_fragment>\n\tif (!gl_FrontFacing && distance(diffuseColor.rgb, vec3(' + MD_HAIR_IN[0].map(v => (v / 255).toFixed(4)).join(', ')
          + ')) < .1) diffuseColor.rgb = vec3(' + MD_HAIR_IN[1].map(v => (v / 255).toFixed(4)).join(', ') + ');');
      }
    };
    const perV = !!head.geo.attributes.aFlat;
    hm.onBeforeCompile = headFlat(perV, hideU); hm.customProgramCacheKey = () => (perV ? 'headV' : 'head') + (hideU ? 'H' : '');
    const hmesh = new THREE.SkinnedMesh(head.geo, hm), hline = new THREE.SkinnedMesh(head.geo, mdLineMat({skinning: true, w: (MD_HEAD_LINE[0] / s).toFixed(5), per: head.geo.attributes.aLine ? ' * aLine' : '', back: MD_HEAD_LINE[1], perBack: !!head.geo.attributes.aBack, hide: hideU}));
    hmesh.frustumCulled = hline.frustumCulled = false; body.add(hmesh, hline);
    hmesh.bind(skel, mesh.matrixWorld); hline.bind(skel, mesh.matrixWorld);
    if (hideU) hmesh.onBeforeRender = hline.onBeforeRender = mdHeadHide(hmesh, skel, B('Head'), head.j.hideAz, hideU);
    head.mesh = hmesh; head.line = hline; head.mat = hm;
    if (head.fringe) {   // (flat as the head; alpha-tested: the locks' edges are the sheet's lines; no outline: drawn in it)
      const ft = new THREE.Texture(new Image()); ft.flipY = false; ft.image.src = head.fringe.png;
      ft.image.decode().then(() => { ft.needsUpdate = true; }, () => {});
      const fm = new THREE.MeshToonMaterial({map: ft, gradientMap: F3.grad, skinning: true, side: THREE.DoubleSide, alphaTest: .5});
      fm.onBeforeCompile = headFlat(false); fm.customProgramCacheKey = () => 'headFringe';
      const fmesh = new THREE.SkinnedMesh(head.fringe.geo, fm); fmesh.frustumCulled = false; body.add(fmesh); fmesh.bind(skel, mesh.matrixWorld);
      head.fringeMesh = fmesh; head.fringeMat = fm;
    }
  }
  const limbs = {};
  for (const l in md.meta.limbs) { const d = md.meta.limbs[l], o = new THREE.Object3D(); o.position.fromArray(d.p); B(d.b).add(o); limbs[l] = o; }
  const it = {kind: 'model', key, root, body, scale: s, bones, mesh, outline, headEnd: B(md.meta.head), limbs, mats: {main},
    joints: {pelvis: B('Hips'), chest: B('Spine'), neck: B('neck'), head: B('Head')}};
  if (fingers.length) { it.fingers = fingers; it.fist = look.fingers.map(f => new THREE.Quaternion().fromArray(f.fist)); }
  if (head) { it.head = head.mesh; it.mats.head = head.mat; if (head.fringeMat) { it.fringe = head.fringeMesh; it.mats.fringe = head.fringeMat; } }
  if (face) it.face = face;
  if (sash.length) {   // the ribbons: skinned to their chains, the chains moved by mdSash
    let at = bones.length + fingers.length;
    const HB = skel.boneInverses[md.index.Hips].clone().invert(), hb = md.bones[md.index.Hips];   // the Hips at bind (world; in the body)
    const HM = new THREE.Matrix4().compose(new THREE.Vector3().fromArray(hb.t), new THREE.Quaternion().fromArray(hb.q), new THREE.Vector3(1, 1, 1));
    it.sash = {frame: 0, F: null, ribbons: look.sash.ribbons.map((r, i) => {
      const m = mdRibbon(md, r, at, skel, ol, s, body); at += sash[i].length; it.mats['sash' + i] = m.mesh.material;
      return {bones: sash[i], w: r.w, wp: r.wp || r.j.map(() => r.w), s, fix: r.fix || 1, tuckRows: m.tuckRows, a: new THREE.Vector3().fromArray(r.a), j: r.j.map(p => new THREE.Vector3().fromArray(p)),
        P: r.j.map(() => new THREE.Vector3()), Q: r.j.map(() => new THREE.Vector3()), T: r.j.map(() => new THREE.Vector3()), L: [],
        sk: (r.sk || []).map((l, k) => ({b: l.map(e => e[0]), w: l.map(e => e[1]), p: new THREE.Vector3().fromArray(r.j[k]).applyMatrix4(HB)})),   // the top's skin (mdSash)
        jb: r.j.map(p => new THREE.Vector3().fromArray(p).applyMatrix4(HM))};   // at bind, in the body
    }), body: look.sash.body.map(x => {   // the body it stays out of (mdBodyOut)
      const ax = new THREE.Vector3().fromArray(x.ax), u = new THREE.Vector3().fromArray(x.u);
      return {bone: B(x.b), ax, u, v: new THREE.Vector3().crossVectors(ax, u), len: x.len, t0: x.t[0], t1: x.t[1], nb: x.r.length, ns: x.r[0].length,
        r: Float32Array.from(x.r.flat()), rmax: Float32Array.from(x.r.map(row => Math.max(...row))), inv: new THREE.Matrix4(), pinv: new THREE.Matrix4(), world: null, c: new THREE.Vector3(),
        ball: ((x.t[1] - x.t[0]) / 2 + .03) * x.len + Math.max(...x.r.flat()) + .05};   // package metres (with the gap)
    }), blend: mdBlendData(look.sash.blend, geo, skel, mesh)};
  }
  if (!md.hitT) mdMeasure(md, it);
  if (look && lk.spikes && !head) B('Head').add(mdSpikes(look.spikes, ol.back));
  return it;
}

// Material m with the face decal over its map (face: {tex, on: a uniform, 1 shown}): per pixel, the decal (the drawn
// face's features on the skin's colour) at the front projection of its bind position (face.map, face.decal) where that
// point is on the front of the face or the neck (face.depth's r: their depth seen from the front; the fringe's locks in
// front of the face and the sides behind the chin take none) and its colour is skin's (never on the collar or the hair
// beside them), faded as its bind normal turns away from the front (face.front) and as the surface turns edge-on to the
// camera (MD_FACE_SEE: the cosine of the angle between them where it is gone and where it is whole). And the shadow under
// the jaw, in face.shade, with crisp smooth edges the same from every side: on the skin whose bind position, at its
// angle around the neck (face.jawAxis; face.jawTh: the first angle, step and count of face.jaw), is from face.jawY.w m
// above the jaw's edge (face.jaw's r, over face.jawY.x + face.jawY.y) down to the band's depth under it (g, times
// face.jawY.z; none where there is no jaw). Chained after m's own shader changes.
const MD_FACE_SEE = [.15, .4];
function mdFaceMat(m, face) {
  const prev = m.onBeforeCompile, key = m.customProgramCacheKey();
  m.onBeforeCompile = (sh, r) => {
    prev.call(m, sh, r);
    sh.uniforms.uFace = {value: face.tex}; sh.uniforms.uFaceOn = face.on;
    Object.assign(sh.uniforms, {uDepth: {value: face.depth}, uDepthBox: {value: face.depthBox}, uDepthZ: {value: face.depthZ}, uDepthCell: {value: face.depthCell},
      uMap: {value: face.map}, uDecal: {value: face.decal}, uFront: {value: face.front}, uShade: {value: face.shade}, uJaw: {value: face.jaw}, uJawAxis: {value: face.jawAxis}, uJawTh: {value: face.jawTh}, uJawY: {value: face.jawY}});
    // seen edge-on (the far eye of a turned head, its surface turning away), the decal fades out: drawn there it smeared
    const lit = sh.vertexShader.includes('vNormal = normalize( transformedNormal )');   // (the toon material; the basic one has no normals)
    sh.vertexShader = 'varying float vFaceSee;\nvarying vec3 vBind;\nvarying vec3 vBindN;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\tvBind = transformed; vBindN = normal;')
      .replace('#include <project_vertex>', '#include <project_vertex>\n\tvFaceSee = ' + (lit ? 'smoothstep(' + MD_FACE_SEE[0].toFixed(2) + ', ' + MD_FACE_SEE[1].toFixed(2) + ', dot(normalize(transformedNormal), normalize(-mvPosition.xyz)))' : '1.0') + ';');
    sh.fragmentShader = 'uniform sampler2D uFace;\nuniform float uFaceOn;\n' +
      'uniform sampler2D uDepth;\nuniform vec4 uDepthBox;\nuniform vec4 uDepthZ;\nuniform vec2 uDepthCell;\nuniform vec3 uMap;\nuniform vec4 uDecal;\nuniform vec2 uFront;\nuniform vec3 uShade;\nuniform sampler2D uJaw;\nuniform vec2 uJawAxis;\nuniform vec3 uJawTh;\nuniform vec4 uJawY;\n' +
      'varying float vFaceSee;\nvarying vec3 vBind;\nvarying vec3 vBindN;\n' + sh.fragmentShader.replace('#include <map_fragment>',
      '#include <map_fragment>' +
      '\n\tvec2 dUv = (vBind.xy - uDepthBox.xy) * uDepthBox.zw;\n\tfloat dIn = step(0.0, dUv.x) * step(dUv.x, 1.0) * step(0.0, dUv.y) * step(dUv.y, 1.0);' +
      '\n\tif (dIn * uFaceOn > 0.0) {' +   // (only the head and the neck: the rest of the body skips it)
      '\n\tvec4 dTex = texture2D(uDepth, uDepthCell + clamp(dUv, 0.0, 1.0) * (1.0 - 2.0 * uDepthCell));' +
      '\n\tfloat dz = uDepthZ.x + dTex.r * uDepthZ.y - vBind.z;' +   // (the face's surface minus this point's depth)
      '\n\tfloat onFace = dIn * (1.0 - smoothstep(uDepthZ.z, 2.0 * uDepthZ.z, abs(dz)));\n\tvec3 nb = normalize(vBindN);' +
      '\n\tfloat skinLike = smoothstep(0.12, 0.22, diffuseColor.r - diffuseColor.b) * smoothstep(0.45, 0.6, diffuseColor.r);' +   // (the texture there: skin, not the collar's teal nor the hair)
      '\n\tvec4 jw = texture2D(uJaw, vec2(((degrees(atan(vBind.x - uJawAxis.x, vBind.z - uJawAxis.y)) - uJawTh.x) / uJawTh.y + 0.5) / uJawTh.z, 0.5));' +
      '\n\tfloat yEdge = uJawY.x + jw.r * uJawY.y, yUp = yEdge + uJawY.w * clamp(jw.g * uJawY.z / 0.005, 0.0, 1.0);' +   // (the top: the edge, a little above it along the jaw)
      '\n\tfloat under = smoothstep(yEdge - jw.g * uJawY.z, yEdge - jw.g * uJawY.z + 0.0005, vBind.y) * (1.0 - smoothstep(yUp - 0.0005, yUp, vBind.y)) * skinLike * uFaceOn;' +
      '\n\tdiffuseColor.rgb = mix(diffuseColor.rgb, uShade, under);' +
      '\n\tvec4 faceTexel = texture2D(uFace, vec2((uMap.y + vBind.x * uMap.x - uDecal.x + 0.5) / (uDecal.z - uDecal.x), (uMap.z - vBind.y * uMap.x - uDecal.y + 0.5) / (uDecal.w - uDecal.y)));' +
      '\n\tfloat faceShare = onFace * skinLike * smoothstep(uFront.x, uFront.y, nb.z) * vFaceSee * uFaceOn * (1.0 - under);' +
      '\n\tdiffuseColor.rgb = mix(diffuseColor.rgb, faceTexel.rgb, faceShare);\n\t}');
  };
  m.customProgramCacheKey = () => key + '|face';
  return m;
}
// The face decal shown or not (once its texture is decoded).
function mdFaceShow(face, show) { face.want = show; face.on.value = face.ready && show ? 1 : 0; }

// An outline shell's material (the back faces drawn in the outline colour): o = {skinning, w (model units: the push
// along the normals, '' for none), per (' * aLine': times the per-vertex width), back (m: pushed away from the camera,
// so the shell shows around the silhouette and not through the body's folds)}.
function mdLineMat(o) {   // (perBack: a per-vertex extra push back, m, in the attribute aBack; hide: the head's uHide, mdHideShader)
  const m = new THREE.MeshBasicMaterial({color: F3_OUTLINE.color, side: THREE.BackSide, skinning: !!o.skinning}), per = o.per || '', pb = o.perBack ? ' + aBack' : '';
  m.onBeforeCompile = sh => {
    let v = (per ? 'attribute float aLine;\n' : '') + (pb ? 'attribute float aBack;\n' : '') + sh.vertexShader;
    if (o.w) v = v.replace('#include <begin_vertex>', '#include <begin_vertex>\n\ttransformed += normal * ' + o.w + per + ';');
    // (the per-vertex push goes along the line of sight: where it is drawn on the screen does not move, only its depth; with an
    // orthographic camera, tools/sheet_scan.py's, that is its z: scaled from the eye as for a perspective one, the hair's outline
    // moved up to 6 mm up the screen there, black shards over the locks that the game does not have)
    if (o.back) v = v.replace('#include <project_vertex>', '#include <project_vertex>\n\tmvPosition.z -= ' + o.back.toFixed(4) + ';'
      + (pb ? '\n\tif (isOrthographic) mvPosition.z -= aBack; else mvPosition.xyz *= 1.0 + aBack / length(mvPosition.xyz);' : '') + '\n\tgl_Position = projectionMatrix * mvPosition;');
    sh.vertexShader = v;
    if (o.hide) mdHideShader(sh, o.hide);
  };
  m.customProgramCacheKey = () => [o.w, per, o.back, pb, o.hide ? 'H' : ''].join('|');
  return m;
}

// The head's locks the side images do not draw (tools/kael_fringe.py side_hide: Kael's, over his temples and cheeks; the
// front image draws them by his eyes): left out of shader sh as the camera is on their side of the head (aHide: per
// vertex, 1 where hidden from his right, from his left; hu.value: how far each side's are hidden, 0 to 1, mdHeadHide),
// dissolved through a 4x4 pattern of the screen's pixels as that goes from 0 to 1 (all at once at a half, a lock by
// his eye flicked on in one frame). Whole triangles (their corners are split from the rest's).
function mdHideShader(sh, hu) {
  sh.uniforms.uHide = hu;
  sh.vertexShader = 'attribute vec2 aHide;\nuniform vec2 uHide;\nvarying float vHide;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n\tvHide = dot(aHide, uHide);');
  sh.fragmentShader = 'varying float vHide;\nfloat mdB2(vec2 a) { a = mod(floor(a), 2.); return fract(a.x * .5 + a.y * .75); }\n'   // (a 2x2 pattern: 0, .5, .75, .25; from 0 and 1 alone: exact at any precision)
    + sh.fragmentShader.replace('void main() {', 'void main() {\n\tif (vHide > mdB2(.5 * gl_FragCoord.xy) * .25 + mdB2(gl_FragCoord.xy) + .03125) discard;');
}

// Before the head is drawn: where the camera is around it, seen from the Head bone (its bind frame: the package's, x his
// left, z his front): a = (camera's x - az[0], z - az[1]) degrees around. His right side's locks are shown as a is
// between az[2] (midway between the front image's angle and the right 3/4's) and MD_HIDE[3] (from the front and from
// his left: from further behind, what shows of them beyond the head is loose shards), his left side's between
// -MD_HIDE[3] and az[3]; hidden outside. A set changes once the angle has asked for it MD_HIDE[2] frames running, with
// MD_HIDE[0] degrees of play either way (at rest on the angle, walking, a lock blinked; a jab whips the head past it
// and back in 8 frames: the lock by his temple flashed on every one), then eases MD_HIDE[1] of the way a frame
// (hu.value: 0 shown to 1 hidden, the shader's dissolve). At once on the first frame, after MD_HIDE[4] renders without
// the head (the game draws two a frame) and with window.__HIDE_SNAP (the tools' stills). Per camera (its own state: a
// second view of the fighter does not pull the first's). hmesh: the head (its bind matrices), skel, hb the Head bone.
const MD_HIDE = [4, .3, 12, 100, 8];
const MD_HAIR_IN = [[226, 214, 227], [140, 121, 154]];   // Kael's hair: its light tone, seen from a lock's inner side, drawn as its shadow tone (tools/kael_flat.py PAL)
const MD_HV = [new THREE.Matrix4(), new THREE.Matrix4(), new THREE.Vector3()];
function mdHeadHide(hmesh, skel, hb, az, hu) {
  const hi = skel.bones.indexOf(hb), per = new WeakMap();
  return (renderer, scene, camera) => {
    let st = per.get(camera);
    if (!st) per.set(camera, st = {frame: -1, on: [0, 0], n: [0, 0], e: [0, 0]});
    if (st.frame !== renderer.info.render.frame) {   // (once a frame: the head and its outline both come here)
      const cut = st.frame < 0 || renderer.info.render.frame - st.frame > MD_HIDE[4] || (typeof window !== 'undefined' && window.__HIDE_SNAP);
      st.frame = renderer.info.render.frame;
      const M = MD_HV[0].multiplyMatrices(hmesh.matrixWorld, hmesh.bindMatrixInverse).multiply(MD_HV[1].multiplyMatrices(hb.matrixWorld, skel.boneInverses[hi])).multiply(hmesh.bindMatrix);
      const c = MD_HV[2].setFromMatrixPosition(camera.matrixWorld).applyMatrix4(M.invert()), a = Math.atan2(c.x - az[0], c.z - az[1]) * 180 / Math.PI;
      const from = [az[2], -MD_HIDE[3]], to = [MD_HIDE[3], az[3]], h = cut ? 0 : MD_HIDE[0];   // (each side's locks shown between from and to)
      for (let k = 0; k < 2; k++) {
        const w = a < from[k] - h || a > to[k] + h ? 1 : cut || (a > from[k] + h && a < to[k] - h) ? 0 : st.on[k];   // (asked for; in the play, as it is)
        if (w === st.on[k]) st.n[k] = 0; else if (cut || ++st.n[k] >= MD_HIDE[2]) { st.on[k] = w; st.n[k] = 0; }
        if (cut) st.e[k] = st.on[k];
        else { st.e[k] += (st.on[k] - st.e[k]) * MD_HIDE[1]; if (Math.abs(st.on[k] - st.e[k]) < .02) st.e[k] = st.on[k]; }
      }
    }
    hu.value.set(st.e[0], st.e[1]);
  };
}

// A sash ribbon r of the look data ({j: its chain's points in the Hips' frame, top to tip; wp: its width at each (w
// alone: the same all along); tuck: m of it under the band; cut: the share of its length its tip's slanted cut takes, on
// its inner edge (out: the side of a, away from the middle, that runs to the tip); a: across; n: out of its face; c:
// colour}) as a thin slab, skinned along the chain (bone indices from at) and put in body: in the sash's colour, its
// light mostly flat as on the band's front (flat; its back, toward the body, shade as dark: the drawing's twisted tails),
// with an outline as the body's (ol, scale s) that starts at nothing where it comes out from under the band and grows
// over fade m (Denis, 7/11: "la fascia è staccata": a line across its top cut it off the band).
const MD_RIB = {rows: 3, th: .012, back: .004, flat: .7, shade: .8, fade: .03};   // rows per bone, thickness (m), outline push back (less than the body's: it shows on it)
function mdRibbon(md, r, at, skel, ol, s, body) {
  const H = new THREE.Matrix4().compose(new THREE.Vector3().fromArray(md.bones[md.index.Hips].t), new THREE.Quaternion().fromArray(md.bones[md.index.Hips].q), new THREE.Vector3(1, 1, 1));
  const C = r.j.map(p => new THREE.Vector3().fromArray(p).applyMatrix4(H)), a = new THREE.Vector3().fromArray(r.a).transformDirection(H), n = new THREE.Vector3().fromArray(r.n).transformDirection(H);
  const nb = C.length - 1, cum = [0], wp = r.wp || C.map(() => r.w), out = r.out || 1, tuck = r.tuck || 0;
  for (let k = 1; k <= nb; k++) cum.push(cum[k - 1] + C[k].distanceTo(C[k - 1]));
  const len = cum[nb], cut = r.cut !== undefined ? r.cut : Math.min(.35, 1.8 * r.w / len), pos = [], si = [], sw = [], col = [], lw = [], idx = [], rows = nb * MD_RIB.rows;
  const along = d => { let k = 0; while (k < nb - 1 && d > cum[k + 1]) k++; const f = Math.min(1, Math.max(0, (d - cum[k]) / (cum[k + 1] - cum[k]))); return {k, f, p: C[k].clone().lerp(C[k + 1], f)}; };
  for (let i = 0; i <= rows; i++) {
    for (const side of [1, -1]) {   // the outer edge to the tip, the inner one cut short: a slanted end
      const d = len * i / rows * (side === out ? 1 : 1 - cut), q = along(d), w = q.k < nb - 1 ? 1 - q.f : 1, b0 = at + q.k, b1 = at + Math.min(q.k + 1, nb - 1);
      const half = (wp[q.k] + (wp[q.k + 1] - wp[q.k]) * q.f) / 2, l = Math.min(1, Math.max(0, (d - tuck) / MD_RIB.fade));
      for (const face of [1, -1]) {
        const v = q.p.clone().addScaledVector(a, side * half).addScaledVector(n, face * MD_RIB.th / 2), c = face > 0 ? 1 : MD_RIB.shade;
        pos.push(v.x, v.y, v.z); si.push(b0, b1, 0, 0); sw.push(w, 1 - w, 0, 0); col.push(c, c, c); lw.push(l * l * (3 - 2 * l));
      }
    }
  }
  // four vertices a row: left front, left back, right front, right back (a = left, n = front, the rows go down)
  const quad = (A, B2, C2, D) => idx.push(A, B2, C2, A, C2, D);
  for (let i = 0; i < rows; i++) {
    const o = i * 4, u = o + 4;   // front, back, left and right faces, each wound to face outward
    quad(o, u, u + 2, o + 2); quad(o + 1, o + 3, u + 3, u + 1); quad(o, o + 1, u + 1, u); quad(o + 2, u + 2, u + 3, o + 3);
  }
  const e = rows * 4; quad(0, 2, 3, 1); quad(e, e + 1, e + 3, e + 2);   // the top and the tip
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx);
  g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4)); g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setAttribute('aLine', new THREE.Float32BufferAttribute(lw, 1));
  g.computeVertexNormals();
  const mat = new THREE.MeshToonMaterial({color: new THREE.Color(r.c[0] / 255, r.c[1] / 255, r.c[2] / 255), gradientMap: F3.grad, skinning: true, vertexColors: true});
  mat.onBeforeCompile = sh => {   // mostly flat light (the hit flash's emissive kept)
    sh.fragmentShader = sh.fragmentShader.replace('vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;',
      '$&\n\toutgoingLight = mix(outgoingLight, diffuseColor.rgb + totalEmissiveRadiance, ' + MD_RIB.flat.toFixed(2) + ');');
  };
  mat.customProgramCacheKey = () => 'ribbon';
  const mesh = new THREE.SkinnedMesh(g, mat);
  const line = new THREE.SkinnedMesh(g, mdLineMat({skinning: true, w: (ol.w / s).toFixed(5), per: ' * aLine', back: Math.min(ol.back || 0, MD_RIB.back)}));
  mesh.frustumCulled = line.frustumCulled = false;
  body.add(mesh, line); mesh.updateMatrixWorld(true); mesh.bind(skel, mesh.matrixWorld); line.bind(skel, mesh.matrixWorld);   // bound in the body
  return {mesh, line, tuckRows: Math.ceil((r.tuck || 0) / len * rows)};   // the rows under the band
}

// The sash's own motion (graphics only), each sim frame since the last call: per ribbon a chain of points from under the
// band to the tip. Its top (fix points: under the band and at its lower edge, where it comes out) moves with the body's
// skin there (mdGlue); the rest with gravity, damping and a weak pull toward the shape it hangs in (the drawing's: its
// first points on the skin too, lying on the vest's flaps that follow the thighs; from there on as the Hips carry it;
// itself kept out of the body), kept at the chain's lengths (as drawn), unfolding (points two apart no closer than at
// rest, by bend), above the floor and out of the body (mdBodyOut: the full volumes around the hips, the belly, the
// thighs with the vest's flaps, the shins), its middle and both its edges; then each bone put at its point and turned
// along its segment. A new fighter, or one moved farther than jump a sim frame (put back), starts hanging at rest.
const MD_SASH = {g: 9.8, damp: .93, pull: .08, top: 2, bend: .5, iter: 4, steps: 4, jump: .3, gap: .012, floor: .012, reach: .06, foot: .035, was: .006};
// g (m/s²), damp, pull: a light cloth (Denis, 7/11: "alleggerisci il peso della fascia così si muove meglio"); top: the
// pull is 1 + top times as strong just under the band as at the tip (the cloth near the knot holds its shape);
// bend: share of a fold undone each round; reach, foot, was: m (mdBlendOut)
// jump: m the band moves in a frame beyond which the sash starts over at rest (the fighter put back); gap: m kept off
// the body (half the ribbon's thickness and its straight runs over the curves); floor: m kept above the floor (y = 0)
const MD_SV = [0, 1, 2, 3, 4, 5, 6, 7].map(() => new THREE.Vector3()), MD_SM = new THREE.Matrix4(), MD_GV = [new THREE.Vector3(), new THREE.Vector3()], MD_GM = new THREE.Matrix4();
// Point k of ribbon r (look data sk: the skin of the body behind its first points) where the body's skin carries it
// (world, in out): the band is skinned to the hips and the thighs, up to 10 cm from where the Hips alone would carry it
// in the guard, and the vest's flaps under it follow the thighs.
function mdGlue(it, r, k, out) {
  const g = r.sk[k], skel = it.mesh.skeleton;
  if (!g) return out.copy(r.j[k]).applyMatrix4(it.bones[mdData(it.key).index.Hips].matrixWorld);
  out.set(0, 0, 0);
  for (let i = 0; i < g.b.length; i++) out.addScaledVector(MD_GV[0].copy(g.p).applyMatrix4(MD_GM.multiplyMatrices(skel.bones[g.b[i]].matrixWorld, skel.boneInverses[g.b[i]])), g.w[i]);
  return out;
}
function mdSash(it, S) {
  const sa = it.sash, hips = it.bones[mdData(it.key).index.Hips];
  it.root.updateMatrixWorld(true);
  const r0 = sa.ribbons[0], band = mdGlue(it, r0, 0, MD_SV[0]), frames = Math.max(0, S.frame - sa.frame);
  const fresh = sa.F !== it.F || band.distanceTo(r0.P[0]) > MD_SASH.jump * Math.max(1, frames), n = fresh ? 0 : Math.min(MD_SASH.steps, frames);
  sa.F = it.F; sa.frame = S.frame;
  for (const sh of sa.body) {
    sh.pinv.copy(fresh ? MD_SM.copy(sh.bone.matrixWorld).invert() : sh.inv); sh.world = sh.bone.matrixWorld; sh.inv.copy(sh.world).invert();
    sh.c.copy(sh.ax).multiplyScalar((sh.t0 + sh.t1) / 2 * sh.len).applyMatrix4(sh.world); sh.s2 = it.scale * it.scale;   // a ball around it, world (quick skip)
  }
  mdBlend(sa.blend, fresh);
  const gdt = MD_SASH.g / 3600, gap = MD_SASH.gap / it.scale;   // in the bones' frames (package metres)
  for (const r of sa.ribbons) {
    r.T0 = r.T0 || r.T.map(() => new THREE.Vector3()); r.T.forEach((t, k) => r.T0[k].copy(t));   // last frame's
    const lie = Math.max(r.fix, r.sk.length);   // (look data without sk: on the Hips)
    for (let k = 0; k < lie; k++) mdGlue(it, r, k, r.T[k]);   // the top on the body's skin: fixed under the band and at its edge, then lying on the vest
    const off = MD_GV[1].copy(r.j[lie - 1]).applyMatrix4(hips.matrixWorld).negate().add(r.T[lie - 1]);
    for (let k = lie; k < r.j.length; k++) {   // the rest as the Hips carry it, on from there, out of the body
      r.T[k].copy(r.j[k]).applyMatrix4(hips.matrixWorld).add(off);
      mdBodyOut(r.T[k], sa.body, gap); mdBlendOut(r.T[k], fresh ? null : r.T0[k], sa.blend, gap * it.scale);
    }
    if (fresh) {
      r.T.forEach((t, k) => { r.P[k].copy(t); r.Q[k].copy(t); r.T0[k].copy(t); });
      const B = r.jb.map(p => p.clone().applyMatrix4(it.body.matrixWorld));   // its lengths as drawn (not of the targets: pushed out of a leg, they stretch)
      r.L = B.slice(1).map((t, k) => t.distanceTo(B[k])); r.L2 = B.slice(2).map((t, k) => t.distanceTo(B[k]));
    }
    // across the ribbon at each point, in the world (from its bones as they were turned last)
    r.A = r.P.map((p, k) => (r.A && r.A[k] || new THREE.Vector3()).copy(r.a).transformDirection(r.bones[Math.min(k, r.bones.length - 1)].matrixWorld));
    for (let step = 0; step < n; step++) {   // frames missed in between: the targets go there a step at a time
      const f = (step + 1) / n, T = k => MD_SV[0].copy(r.T0[k]).lerp(r.T[k], f), nf = r.P.length - r.fix;
      for (let k = 0; k < r.fix; k++) { r.P[k].copy(T(k)); r.Q[k].copy(r.P[k]); }   // the top: fixed on the body
      for (let k = r.fix; k < r.P.length; k++) {
        const v = MD_SV[1].subVectors(r.P[k], r.Q[k]).multiplyScalar(MD_SASH.damp);
        r.Q[k].copy(r.P[k]); r.P[k].add(v).addScaledVector(MD_SV[2].subVectors(T(k), r.P[k]), MD_SASH.pull * (1 + MD_SASH.top * (1 - (k - r.fix) / nf))); r.P[k].y -= gdt;
      }
      for (let it2 = 0; it2 < MD_SASH.iter; it2++) {
        mdSashLengths(r);
        for (let k = Math.max(0, r.fix - 2); k + 2 < r.P.length; k++) {   // no sharp folds
          const d = MD_SV[1].subVectors(r.P[k + 2], r.P[k]), l = d.length() || 1e-9, e = (l - r.L2[k]) / l * MD_SASH.bend;
          if (e >= 0) continue;
          if (k < r.fix) r.P[k + 2].addScaledVector(d, -e); else { r.P[k].addScaledVector(d, e / 2); r.P[k + 2].addScaledVector(d, -e / 2); }
        }
        mdSashOut(r, sa, gap, it2 === MD_SASH.iter - 1);   // the edges in the last round
      }
      mdSashChain(r); mdSashOut(r, sa, gap, true); mdSashChain(r);   // as the bones will draw it: exact lengths from the band
    }
    let parent = hips;
    r.bones.forEach((b, k) => {   // at its point (the top's: where the skin took it), turned so its segment points at the next
      const inv = MD_SM.copy(parent.matrixWorld).invert(), want = MD_SV[3].subVectors(r.P[k + 1], r.P[k]).transformDirection(inv);
      b.position.copy(r.P[k]).applyMatrix4(inv);
      b.quaternion.setFromUnitVectors(MD_SV[4].subVectors(r.j[k + 1], r.j[k]).normalize(), want);
      b.updateMatrixWorld(); parent = b;
    });
  }
}
// Ribbon r's chain back to its segments' lengths, both ends of each moving (the fixed top stays).
function mdSashLengths(r) {
  for (let k = r.fix - 1; k + 1 < r.P.length; k++) {
    const d = MD_SV[1].subVectors(r.P[k + 1], r.P[k]), l = d.length() || 1e-9, e = (l - r.L[k]) / l;
    if (k < r.fix) r.P[k + 1].addScaledVector(d, -e); else { r.P[k].addScaledVector(d, e / 2); r.P[k + 1].addScaledVector(d, -e / 2); }
  }
}
// The same from the fixed top down, each point put at its exact length from the one above (the chain the bones draw).
function mdSashChain(r) {
  for (let k = r.fix - 1; k + 1 < r.P.length; k++) {
    const d = MD_SV[1].subVectors(r.P[k + 1], r.P[k]), l = d.length() || 1e-9;
    r.P[k + 1].copy(r.P[k]).addScaledVector(d, r.L[k] / l);
  }
}
// Ribbon r's points (but the fixed top's) above the floor and out of the body: each point, and (edges) each edge beside it
// (half the width across), moved by what takes it out.
function mdSashOut(r, sa, gap, edges) {
  const out = (p, q) => mdBodyOut(p, sa.body, gap, q) | mdBlendOut(p, q, sa.blend, gap * r.s);
  for (let k = r.fix; k < r.P.length; k++) {
    out(r.P[k], r.Q[k]);
    if (edges) for (const side of [1, -1]) {
      const e = MD_SV[5].copy(r.P[k]).addScaledVector(r.A[k], side * r.wp[k] / 2 * r.s), e0 = MD_SV[6].copy(e);
      if (out(e, MD_SV[7].copy(r.Q[k]).addScaledVector(r.A[k], side * r.wp[k] / 2 * r.s))) r.P[k].add(e.sub(e0));
    }
  }
}
// Point p (world) above the floor and out of the body shapes (look data body_shape, each with its bone's world matrix and
// inverse of this frame, and the inverse of the last frame's), gap (package metres) beyond their radius there; true when
// it moved. q (optional): where p was a step ago. Pushed out on the side it was then, not on the side it is now: a limb
// that swept past it in one frame (a kick) carries it along in front, instead of letting it through.
function mdBodyOut(p, body, gap, q) {
  let moved = false;
  if (p.y < MD_SASH.floor) { p.y = MD_SASH.floor; moved = true; }
  for (const sh of body) {
    if (p.distanceToSquared(sh.c) > sh.ball * sh.ball * sh.s2) continue;
    const L = MD_SV[2].copy(p).applyMatrix4(sh.inv), t = L.dot(sh.ax) / sh.len;
    if (t < sh.t0 - .03 || t > sh.t1 + .03) continue;
    const rad = MD_SV[3].copy(L).addScaledVector(sh.ax, -t * sh.len), d = rad.length(), bi = Math.max(0, Math.min(sh.nb - 1, Math.floor((t - sh.t0) / (sh.t1 - sh.t0) * sh.nb)));
    if (d >= Math.max(sh.rmax[bi], sh.rmax[Math.min(sh.nb - 1, bi + 1)], sh.rmax[Math.max(0, bi - 1)]) + gap || d >= mdBodyR(sh, t, rad) + gap) continue;
    if (q) {   // the side it came from
      const Lq = MD_SV[4].copy(q).applyMatrix4(sh.pinv), rq = Lq.addScaledVector(sh.ax, -Lq.dot(sh.ax));
      if (rq.lengthSq() > 1e-8) rad.copy(rq);
    }
    const rl = rad.length(); if (rl < 1e-9) continue;
    L.copy(rad).multiplyScalar((mdBodyR(sh, t, rad) + gap) / rl).addScaledVector(sh.ax, t * sh.len); p.copy(L.applyMatrix4(sh.world)); moved = true;
  }
  return moved;
}
// Shape sh's radius at t (bone lengths) toward rad (its local frame, across the axis).
function mdBodyR(sh, t, rad) {
  const fb = Math.max(0, Math.min(sh.nb - 1.001, (t - sh.t0) / (sh.t1 - sh.t0) * sh.nb - .5)), fs = ((Math.atan2(rad.dot(sh.v), rad.dot(sh.u)) + Math.PI) / (2 * Math.PI) * sh.ns - .5 + sh.ns) % sh.ns;
  const i = Math.floor(fb), j = Math.floor(fs), di = fb - i, dj = fs - j, j2 = (j + 1) % sh.ns, R = sh.r, ns = sh.ns;
  return (R[i * ns + j] * (1 - dj) + R[i * ns + j2] * dj) * (1 - di) + (R[(i + 1) * ns + j] * (1 - dj) + R[(i + 1) * ns + j2] * dj) * di;
}

// The body's vertices shared between its parts (look data blend): their bind positions, normals and skin, where they
// are drawn now and were drawn last frame (world), and a hash grid of them.
const MD_GRID = 1024;
function mdBlendData(idx, geo, skel, mesh) {
  const n = idx.length, P = geo.attributes.position.array, N = (geo.userData.bindNormal || geo.attributes.normal).array, J = geo.attributes.skinIndex.array, W = geo.attributes.skinWeight.array;   // (the mesh's own normals: the sash keeps off its real surface, not the light's smoothed one)
  const S = {n, B: new Float32Array(n * 3), N0: new Float32Array(n * 3), J: new Uint16Array(n * 4), W: new Float32Array(n * 4), X: new Float32Array(n * 3),
    N: new Float32Array(n * 3), PX: new Float32Array(n * 3), PN: new Float32Array(n * 3), head: new Int32Array(MD_GRID), next: new Int32Array(n), used: [], slot: {},
    lo: new THREE.Vector3(), hi: new THREE.Vector3()};
  for (let i = 0; i < n; i++) {
    const v = idx[i];
    for (let k = 0; k < 3; k++) { S.B[i * 3 + k] = P[v * 3 + k]; S.N0[i * 3 + k] = N[v * 3 + k]; }
    for (let k = 0; k < 4; k++) {
      S.J[i * 4 + k] = J[v * 4 + k]; S.W[i * 4 + k] = W[v * 4 + k];
      if (W[v * 4 + k] > 0 && S.slot[J[v * 4 + k]] === undefined) { S.slot[J[v * 4 + k]] = S.used.length; S.used.push(J[v * 4 + k]); }
    }
  }
  // a vertex at bind is moved by bone.matrixWorld * boneInverse * bindMatrix (three's skinning, the mesh 'attached')
  S.K = S.used.map(b => new THREE.Matrix4().multiplyMatrices(skel.boneInverses[b], mesh.bindMatrix)); S.M = S.used.map(() => new THREE.Matrix4());
  S.bones = S.used.map(b => skel.bones[b]);
  return S;
}
function mdBlend(S, fresh) {
  S.PX.set(S.X); S.PN.set(S.N);
  const e = S.M.map((m, i) => m.multiplyMatrices(S.bones[i].matrixWorld, S.K[i]).elements), B = S.B, N0 = S.N0, c = MD_SASH.reach;
  S.head.fill(-1);
  for (let i = 0; i < S.n; i++) {
    const bx = B[i * 3], by = B[i * 3 + 1], bz = B[i * 3 + 2], ax = N0[i * 3], ay = N0[i * 3 + 1], az = N0[i * 3 + 2];
    let x = 0, y = 0, z = 0, nx = 0, ny = 0, nz = 0;
    for (let k = 0; k < 4; k++) {
      const w = S.W[i * 4 + k]; if (!w) continue;
      const m = e[S.slot[S.J[i * 4 + k]]];
      x += w * (m[0] * bx + m[4] * by + m[8] * bz + m[12]); y += w * (m[1] * bx + m[5] * by + m[9] * bz + m[13]); z += w * (m[2] * bx + m[6] * by + m[10] * bz + m[14]);
      nx += w * (m[0] * ax + m[4] * ay + m[8] * az); ny += w * (m[1] * ax + m[5] * ay + m[9] * az); nz += w * (m[2] * ax + m[6] * ay + m[10] * az);
    }
    const l = Math.hypot(nx, ny, nz) || 1;
    S.X[i * 3] = x; S.X[i * 3 + 1] = y; S.X[i * 3 + 2] = z; S.N[i * 3] = nx / l; S.N[i * 3 + 1] = ny / l; S.N[i * 3 + 2] = nz / l;
    const h = mdHash(Math.floor(x / c), Math.floor(y / c), Math.floor(z / c)); S.next[i] = S.head[h]; S.head[h] = i;
    if (!i) S.lo.set(x, y, z), S.hi.set(x, y, z); else S.lo.min(MD_SV[0].set(x, y, z)), S.hi.max(MD_SV[0]);
  }
  S.lo.subScalar(c); S.hi.addScalar(c);   // their box, with the reach: points outside it skip the grid
  if (fresh) { S.PX.set(S.X); S.PN.set(S.N); }
}
function mdHash(x, y, z) { return (Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791)) & (MD_GRID - 1); }
// Point p (world, q: where it was a step ago) kept off the shared vertices: of those within reach whose small patch it is
// over or under (foot across their plane), the one it went deepest behind while it had been in front of it last frame;
// moved gap (world) in front of that plane. True when moved.
function mdBlendOut(p, q, S, gap) {
  if (!q || p.x < S.lo.x || p.y < S.lo.y || p.z < S.lo.z || p.x > S.hi.x || p.y > S.hi.y || p.z > S.hi.z) return false;
  const c = MD_SASH.reach, ix = Math.floor(p.x / c), iy = Math.floor(p.y / c), iz = Math.floor(p.z / c), X = S.X, N = S.N, PX = S.PX, PN = S.PN;
  const R2 = c * c, F2 = MD_SASH.foot * MD_SASH.foot;
  let best = -1, bd = gap;
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
    for (let i = S.head[mdHash(ix + dx, iy + dy, iz + dz)]; i >= 0; i = S.next[i]) {
      const ex = p.x - X[i * 3], ey = p.y - X[i * 3 + 1], ez = p.z - X[i * 3 + 2], d2 = ex * ex + ey * ey + ez * ez;
      if (d2 > R2) continue;
      const d = ex * N[i * 3] + ey * N[i * 3 + 1] + ez * N[i * 3 + 2];
      if (d >= bd || d2 - d * d > F2) continue;
      const dq = (q.x - PX[i * 3]) * PN[i * 3] + (q.y - PX[i * 3 + 1]) * PN[i * 3 + 1] + (q.z - PX[i * 3 + 2]) * PN[i * 3 + 2];
      if (dq < -MD_SASH.was) continue;   // it was behind this face already: the other side of the cloth, or inside
      bd = d; best = i;
    }
  }
  if (best < 0) return false;
  const i = best; p.x += (gap - bd) * N[i * 3]; p.y += (gap - bd) * N[i * 3 + 1]; p.z += (gap - bd) * N[i * 3 + 2];
  return true;
}

// The hair spikes of the look data on the head: flat cones (thin along t, the head's outward direction, so each lies
// on the hair like a lock) in the hair colour of Denis's drawing, with outlines (a scaled shell, pushed back by back m
// as the body's).
const MD_HAIR = 0x3b303a;
function mdSpikes(list, back) {
  const g = new THREE.Group(), mat = new THREE.MeshToonMaterial({color: MD_HAIR, gradientMap: F3.grad});
  const line = mdLineMat({back}), k = back ? [1.12, 1.04, 1.18] : [1.22, 1.07, 1.35], M = new THREE.Matrix4();
  for (const s of list) {
    const geo = new THREE.ConeGeometry(s.r, s.len, 14, 3); geo.translate(0, s.len / 2, 0); geo.scale(1, 1, .45);
    const m = new THREE.Mesh(geo, mat), o = new THREE.Mesh(geo, line), a = new THREE.Vector3().fromArray(s.d), t = new THREE.Vector3().fromArray(s.t);
    o.scale.set(...k); m.add(o);
    m.position.fromArray(s.p); m.quaternion.setFromRotationMatrix(M.makeBasis(new THREE.Vector3().crossVectors(a, t), a, t));
    g.add(m);
  }
  return g;
}

// The look data of package key ('<key>/<key>_look.json' and '.bin', tools/ren_look.py), decoded once onto md, or null:
// {fingers: the finger bones, skin: [skinIndex, skinWeight] with them, line: the outline widths, flat: the flat light's
// share, spikes, sash: {ribbons, body: the shapes the sash stays out of, blend: the vertices between them}}.
// the new head's light (its share left flat: its texture, from the sheet, has the shading) and outline: [width, pushed back
// from the camera] m (thin as the sheet's lines; pushed back less than the body's, so the jaw's line shows over the neck
// as on the sheet; less still, the hair's locks drew black shards over the eyes)
const MD_HEAD_FLAT = 1, MD_HEAD_LINE = [.004, .006];
// The new head (ASSETS '<key>/<key>_head.json|bin|jpg', tools/ren_head.py): its geometry, skinned to the package's bones
// in the package's bind space, its texture, the package's triangles it replaces (hide), those lined (lining: drawn from
// behind too, mdTris) and those left out of the outline (noline); null without it.
function mdHeadData(md, key) {
  const j = ASSETS[key + '/' + key + '_head.json'], b64 = ASSETS[key + '/' + key + '_head.bin'], jpg = ASSETS[key + '/' + key + '_head.png'] || ASSETS[key + '/' + key + '_head.jpg'];   // (its texture: a PNG where its colours are flat, tools/kael_head.py)
  if (!j || !b64 || !jpg) return null;
  if (md.head && md.head.j === j) return {j, geo: md.head.geo, hide: md.head.hide, lining: md.head.lining, noline: md.head.noline, jpg, fringe: md.head.fringe};
  const s = atob(b64), u8 = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
  const buf = u8.buffer, f32 = a => new Float32Array(buf, a[0], a[1]), geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(f32(j.pos), 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(f32(j.nor), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(f32(j.uv), 2));
  geo.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(new Uint8Array(buf, j.jnt[0], j.jnt[1]), 4));
  geo.setAttribute('skinWeight', new THREE.BufferAttribute(f32(j.wgt), 4));
  geo.setIndex(new THREE.BufferAttribute(j.verts > 65535 ? new Uint32Array(buf, j.idx[0], j.idx[1]) : new Uint16Array(buf, j.idx[0], j.idx[1]), 1));
  if (j.lb) geo.setAttribute('aBack', new THREE.BufferAttribute(f32(j.lb), 1));   // (the hair over the face: its outline further back)
  if (j.flat) geo.setAttribute('aFlat', new THREE.BufferAttribute(f32(j.flat), 1));   // (its light: flat, but its collar's outside lit as the body)
  if (j.line) geo.setAttribute('aLine', new THREE.BufferAttribute(f32(j.line), 1));   // (its outline's width per vertex: Kael's earrings' thin)
  if (j.hv) geo.setAttribute('aHide', new THREE.BufferAttribute(f32(j.hv), 2));   // (the locks hidden when seen from his right, from his left: mdHeadHide)
  md.head = {j, geo, hide: new Uint32Array(buf, j.hide[0], j.hide[1]), lining: j.lining && j.lining[1] ? new Uint32Array(buf, j.lining[0], j.lining[1]) : null,
    noline: j.noline && j.noline[1] ? new Uint32Array(buf, j.noline[0], j.noline[1]) : null, fringe: mdFringeData(md, key)};
  return {j, geo, hide: md.head.hide, lining: md.head.lining, noline: md.head.noline, jpg, fringe: md.head.fringe};
}

// A geometry with the body's attributes (g's, shared) and the package's triangles (of its index src) but those of hide and
// skip, in their order, then those of rev again, reversed: drawn from behind in the same material (the lining).
function mdTris(g, src, hide, skip, rev) {
  const l = new THREE.BufferGeometry(), drop = new Uint8Array(src.length / 3), out = [];
  for (const k in g.attributes) l.setAttribute(k, g.attributes[k]);
  l.userData = g.userData;
  hide.forEach(t => { drop[t] = 1; }); skip.forEach(t => { drop[t] = 1; });
  for (let t = 0; t < drop.length; t++) if (!drop[t]) out.push(src[3 * t], src[3 * t + 1], src[3 * t + 2]);
  if (rev) rev.forEach(t => out.push(src[3 * t], src[3 * t + 2], src[3 * t + 1]));
  l.setIndex(new THREE.BufferAttribute(src instanceof Uint32Array ? Uint32Array.from(out) : Uint16Array.from(out), 1));
  return l;
}

// The face's locks drawn from the sheet (<key>_fringe.*, tools/ren_fringe.py): a thin pillow hanging from the crown's
// front edge down to the brows, its texture the sheet's own front view (line art and sheen), its alpha the locks' shape;
// all on the Head bone.
function mdFringeData(md, key) {
  const j = ASSETS[key + '/' + key + '_fringe.json'], b64 = ASSETS[key + '/' + key + '_fringe.bin'], png = ASSETS[key + '/' + key + '_fringe.png'];
  if (!j || !b64 || !png) return null;
  const s = atob(b64), u8 = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
  const buf = u8.buffer, f32 = a => new Float32Array(buf, a[0], a[1]), geo = new THREE.BufferGeometry(), n = j.verts;
  geo.setAttribute('position', new THREE.BufferAttribute(f32(j.pos), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(f32(j.uv), 2));
  const si = new Uint16Array(n * 4), sw = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) { si[i * 4] = md.index.Head; sw[i * 4] = 1; }
  geo.setAttribute('skinIndex', new THREE.BufferAttribute(si, 4)); geo.setAttribute('skinWeight', new THREE.BufferAttribute(sw, 4));
  geo.setIndex(new THREE.BufferAttribute(n > 65535 ? new Uint32Array(buf, j.idx[0], j.idx[1]) : new Uint16Array(buf, j.idx[0], j.idx[1]), 1));
  geo.computeVertexNormals();
  return {geo, png};
}

function mdLookData(md, key) {
  if (md.look !== undefined) return md.look;
  const j = ASSETS[key + '/' + key + '_look.json'], b64 = ASSETS[key + '/' + key + '_look.bin'];
  if (!j || !b64) return md.look = null;
  const s = atob(b64), u8 = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
  const f32 = a => new Float32Array(u8.buffer, a[0], a[1]);
  return md.look = {fingers: j.fingers, spikes: j.spikes, sash: j.sash && {ribbons: j.sash.ribbons, body: j.sash.body, blend: new Uint16Array(u8.buffer, j.sash.blend[0], j.sash.blend[1])},
    move: j.move && {idx: new Uint16Array(u8.buffer, j.move.idx[0], j.move.idx[1]), pos: f32(j.move.pos), nor: f32(j.move.nor)},
    face: j.face && Object.assign({}, j.face, {depth: Object.assign({}, j.face.depth, {map: new Uint8Array(u8.buffer, j.face.depth.map[0], j.face.depth.map[1])}),
      jaw: Object.assign({}, j.face.jaw, {map: new Uint8Array(u8.buffer, j.face.jaw.map[0], j.face.jaw.map[1])})}),
    skin: [new THREE.Uint16BufferAttribute(new Uint8Array(u8.buffer, j.skin[0][0], j.skin[0][1]), 4), new THREE.BufferAttribute(f32(j.skin[1]), 4)],
    line: new THREE.BufferAttribute(f32(j.line), 1), flat: new THREE.BufferAttribute(f32(j.flat), 1), nor: j.nor && new THREE.BufferAttribute(f32(j.nor), 3)};
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
  const lk = CFG.looks[F.char], C = lk && lk.clips ? mdLookClips(lk) : CFG.clips, c = {F, S, m: CFG.moves[F.act], id: F.act};
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
  const p = mdEval(md, e || C.idle, c);
  // the look's raised head, not when crouched (as the sim's hurtboxes: there it lifted the head above the crouching one)
  if (lk && lk.headUp && !(CROUCHED[F.act] || (F.act === 'block' && (F.prev & BTN.D)))) mdBoneTurn(p, md.index.Head, MD_X, -lk.headUp);
  return p;
}
function mdUp(u) { return Math.max(0, Math.min(1, u)); }
// CFG.clips with a look's own entries (lk.clips) over them, made once per look (and again if either changes).
const MD_LOOK_CLIPS = new WeakMap();
function mdLookClips(lk) {
  const m = MD_LOOK_CLIPS.get(lk);
  if (m && m.base === CFG.clips && m.own === lk.clips) return m.C;
  const C = Object.assign({}, CFG.clips, lk.clips); MD_LOOK_CLIPS.set(lk, {base: CFG.clips, own: lk.clips, C}); return C;
}

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
  if (it.sash) mdSash(it, S);
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
