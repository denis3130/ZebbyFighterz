// The 3D arena: far painted layers (sky, cliffs with the flowing waterfall, mist) on big planes at their own depth,
// and near 3D pieces in the fighters' toon style (stone terrace with grass, column with a waving banner, lantern,
// rocks, bushes). Built from CFG.arenas[name] (arenaBuild) and animated once per drawn frame (arenaStep). Graphics
// only: it reads the sim state and never writes it. Metres; the fighters stand at z ~ 0 on y = 0 (the slabs' tops);
// the camera looks along -z (d_render.js).

// group = the near 3D arena (in the scene); layers = {bg (the far layers' full-screen quad), rects}; banner = the cloth
// mesh; leaves = the drifting leaves (d_render.js); waterMat = the far layers' ShaderMaterial; stats() = {draws, tris}.
const ARENA = {group: null, layers: {}, banner: null, leaves: new THREE.Group(), waterMat: null, stats: arStats};
// Private: def = the arena's CFG entry, seed = render-only generator, cloth = the banner's points, bgScene/bgCam = the
// far layers' own scene and clip-space camera (drawn before the 3D scene).
const AR = {def: null, seed: 11, cloth: null, last: -1, bgScene: new THREE.Scene(),
  bgCam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)};

// The far layers in one full-screen pass (no overdraw, no blending): per pixel, the camera ray (the camera looks along
// -z without pitch: uTan = tan of the half view, x and y) meets each layer's plane at its depth (uZ: sky, cliffs,
// mist), where the layer's rect (x0, y0, x1, y1, metres) gives its uv. Sky: the clouds sway in u (mirrored past the
// edges; not read where the cliffs hide it); cliffs over it by their alpha (red of uAW), the waterfall (green of uAW) shimmering and streaking as on the flat backdrop (uScale = layer
// uv to painting uv); the mist band over both. A ray that meets the ground in front of uCover is under the terrace,
// drawn over it: it only writes the grout colour.
const AR_BG_VERT = 'varying vec2 vS;\nvoid main(){ vS = uv; gl_Position = vec4(position.xy, 0., 1.); }';
const AR_BG_FRAG = `
uniform sampler2D uSky, uCliffs, uAW, uMist;
uniform vec3 uCam, uZ, uMistColor, uGround;
uniform vec2 uTan, uScale;
uniform vec4 uSkyRect, uCliffRect, uMistRect;
uniform float uTime, uContrast, uLift, uFlow, uStreak, uWobble, uSkyOff, uMistDrift, uMistOpacity, uMistRep, uCover;
uniform vec4 uFoam;
uniform vec3 uWater;
uniform vec2 uSpray, uCrest;
varying vec2 vS;
float arHash(vec2 p){ p = 50. * fract(p * .3183099 + vec2(.71, .113)); return fract(p.x * p.y * (p.x + p.y)); }
float arNoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  float y0 = mod(i.y, 64.), y1 = mod(i.y + 1., 64.);
  return mix(mix(arHash(vec2(i.x, y0)), arHash(vec2(i.x + 1., y0)), f.x),
             mix(arHash(vec2(i.x, y1)), arHash(vec2(i.x + 1., y1)), f.x), f.y);
}
vec2 arAt(vec3 d, float z, vec4 r){ return (uCam.xy + d.xy * (uCam.z - z) - r.xy) / (r.zw - r.xy); }
void main(){
  vec3 d = vec3((vS * 2. - 1.) * uTan, -1.);
  if (d.y < 0. && uCam.z - uCam.y / -d.y > uCover) { gl_FragColor = vec4(uGround, 1.); return; }
  vec2 uc = arAt(d, uZ.y, uCliffRect);
  vec2 aw = texture2D(uAW, uc).rg;
  float a = aw.r;
  vec3 c = vec3(0.);
  if (a < .996) {
    vec2 us = arAt(d, uZ.x, uSkyRect);
    us.x = 1. - abs(1. - mod(us.x + uSkyOff + 2., 2.));
    c = texture2D(uSky, us).rgb;
  }
  if (a > .004) {
    float m = aw.g;
    vec2 p = uc * uScale;
    vec2 sh = uc + vec2(0., sin(p.x * 90. + mod(uTime * 3., 6.2831853)) * uWobble * m / uScale.y);
    vec3 cc = texture2D(uCliffs, sh).rgb;
    if (m > .004) {
      // The painted water slides down: two copies, half a cycle apart, each sampled from higher up as its cycle runs;
      // each fades out as it jumps back (weights 1 - |2ph - 1| and the rest), so no seam ever shows.
      // A copy counts only where it samples water too (near the crest it would pull down the sky above).
      float ph = fract(uTime * uWater.x), wa = 1. - abs(2. * ph - 1.);
      vec2 sa = sh + vec2(0., ph * uWater.y), sb = sh + vec2(0., fract(ph + .5) * uWater.y);
      float ka = wa * texture2D(uAW, sa).g, kb = (1. - wa) * texture2D(uAW, sb).g;
      vec3 fl = texture2D(uCliffs, sa).rgb * ka + texture2D(uCliffs, sb).rgb * kb + cc * (1. - ka - kb);
      cc = mix(cc, fl, m * uWater.z * smoothstep(uCrest.x, uCrest.y, uc.y));
      cc += m * (arNoise(vec2(p.x * 140., p.y * 6. + mod(uTime * uFlow * 6., 64.))) - .5) * uStreak / uContrast;
    }
    // Spray at the foot: rising, boiling puffs of white, fading out to the rect's edges.
    vec2 f = (uc - uFoam.xy) / (uFoam.zw - uFoam.xy);
    if (f.x > 0. && f.x < 1. && f.y > 0. && f.y < 1.) {
      float e = smoothstep(0., .18, f.x) * smoothstep(1., .82, f.x) * smoothstep(1., .45, f.y) * smoothstep(0., .12, f.y);
      float t = mod(uTime * uSpray.y, 64.);
      float n = arNoise(vec2(f.x * 26., f.y * 7. - t)) * .6 + arNoise(vec2(f.x * 61. + 7., f.y * 16. - t * 1.7)) * .4;
      cc = mix(cc, vec3(.93, .98, 1.) / uContrast, smoothstep(.42, .78, n) * e * uSpray.x);
    }
    c = mix(c, cc, a);
  }
  c = (c - .5) * uContrast + .5 + uLift;
  vec2 um = arAt(d, uZ.z, uMistRect);
  if (um.y > 0. && um.y < 1.) {
    float ma = texture2D(uMist, vec2(um.x * uMistRep + mod(uTime * uMistDrift, 1.), um.y)).r * uMistOpacity;
    c = mix(c, uMistColor, ma * smoothstep(0., .08, um.x) * smoothstep(1., .92, um.x));
  }
  gl_FragColor = vec4(c, 1.);
}`;

// Render-only generator (mulberry32 on AR.seed), so the arena is built the same every time.
function arRand() {
  let t = AR.seed = AR.seed + 0x6D2B79F5 | 0;
  t = Math.imul(t ^ t >>> 15, 1 | t); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296;
}

// Loads the layers, builds the arena from def (a CFG.arenas entry) and adds it to the scene. Resolves when the
// textures are decoded.
function arenaBuild(def) {
  AR.def = def; AR.seed = 11;
  const g = ARENA.group = new THREE.Group();
  g.name = 'arena';
  const keys = ['sky.jpg', 'cliffs.jpg', 'cliffs_aw.png', 'mist.png'].map(k => 'arena/cascata_' + k);
  return Promise.all(keys.map(rdTexture)).then(([sky, cliffs, aw, mist]) => {
    for (const t of [sky, cliffs, aw]) {   // seen at about their own size: no mipmaps (cheaper, and WebGL1 has none for them)
      t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
    }
    mist.wrapS = THREE.RepeatWrapping;
    f3Shared();
    arLayers(def, sky, cliffs, aw, mist);
    const M = arMesh();   // terrace, column and props: one mesh and one outline (each draw costs, on phones too)
    arTerrace(def, M);
    AR.props = [M.p.length / 3]; arProps(def, M); AR.props.push(M.p.length / 3);   // the props' vertices (for the tests)
    const G = arMesh(); arGrass(def, G);
    const stone = arStoneTex(); stone.minFilter = THREE.LinearFilter; stone.generateMipmaps = false;   // seen magnified
    arToon(M, stone, def.terrace.line, 'stone', G);
    scene.add(g);
    for (const t of [sky, cliffs, aw, mist]) renderer.initTexture(t);
    renderer.compile(AR.bgScene, AR.bgCam);
  });
}

// --- Far layers ---
// The flat backdrop's placement on the ref screen at the start camera, as (painting u, v) -> screen uv: {px, py, su, sv}.
function arRefPlace(def) {
  const r = def.ref, [iw, ih] = r.img, W = r.w, H = r.h, gy = CFG.cam.footScreen * H;
  const s = Math.max(Math.max(W / iw, H / ih) * r.cover, W / iw, gy / (r.footRow * ih), (H - gy) / ((1 - r.footRow) * ih));
  const su = W / (iw * s), sv = H / (ih * s);
  return {px: .5 - su / 2, py: 1 - r.footRow - (H - gy) / (ih * s), su, sv};
}

// World point at depth z of painting uv (u, v): where the flat backdrop showed it at the start camera on the ref screen.
function arPaintToWorld(def, P, u, v, z) {
  const k = CFG.cam, t = Math.tan(k.fov * Math.PI / 360), asp = def.ref.w / def.ref.h, L = k.dist0 - z;
  const y0 = k.dist0 * (k.footScreen - .5) * 2 * t;
  return [((u - P.px) / P.su * 2 - 1) * L * t * asp, y0 + ((v - P.py) / P.sv * 2 - 1) * L * t];
}

// The rect (x0, y0, x1, y1, metres) at depth z of the layer whose painting box (in layer uv) is box = {u0, u1, v0, v1}.
function arLayerRect(def, P, box, z) {
  const pu = U => (U - box.u0) / (box.u1 - box.u0), pv = V => (V - box.v0) / (box.v1 - box.v0);
  return arPaintToWorld(def, P, pu(0), pv(0), z).concat(arPaintToWorld(def, P, pu(1), pv(1), z));
}

function arLayers(def, sky, cliffs, aw, mist) {
  const P = arRefPlace(def), meta = ASSETS['arena/cascata_layers.json'], L = def.layers, m = def.mist, ih = def.ref.img[1];
  const sr = arLayerRect(def, P, meta.sky, L.sky), cr = arLayerRect(def, P, meta.cliffs, L.cliffs);
  // Mist: painting rows mist.rows projected at its depth, as wide as the cliffs' rect there.
  const [, ytop] = arPaintToWorld(def, P, .5, 1 - m.rows[0] / ih, L.mist), [, ybot] = arPaintToWorld(def, P, .5, 1 - m.rows[1] / ih, L.mist);
  const mw = (cr[2] - cr[0]) * (CFG.cam.distMax - L.mist) / (CFG.cam.distMax - L.cliffs), mr = [-mw / 2, ybot, mw / 2, ytop];
  const mc = new THREE.Color().fromArray(meta.mistColor);
  mc.r = Math.min(1, mc.r + m.lift); mc.g = Math.min(1, mc.g + m.lift); mc.b = Math.min(1, mc.b + m.lift);
  const T = def.terrace, v4 = r => new THREE.Vector4(...r), U = v => ({value: v});
  ARENA.waterMat = new THREE.ShaderMaterial({vertexShader: AR_BG_VERT, fragmentShader: AR_BG_FRAG, depthTest: false,
    depthWrite: false, uniforms: {uSky: U(sky), uCliffs: U(cliffs), uAW: U(aw), uMist: U(mist),
      uCam: U(new THREE.Vector3()), uTan: U(new THREE.Vector2()), uZ: U(new THREE.Vector3(L.sky, L.cliffs, L.mist)),
      uSkyRect: U(v4(sr)), uCliffRect: U(v4(cr)), uMistRect: U(v4(mr)),
      uScale: U(new THREE.Vector2(1 / (meta.cliffs.u1 - meta.cliffs.u0), 1 / (meta.cliffs.v1 - meta.cliffs.v0))),
      uTime: U(0), uContrast: U(def.contrast), uLift: U(def.lift), uFlow: U(def.flow), uStreak: U(def.streak),
      uWobble: U(def.wobble), uSkyOff: U(0), uMistColor: U(mc), uMistDrift: U(m.drift), uMistOpacity: U(m.opacity),
      uMistRep: U(Math.max(1, Math.round(mw / 30))), uWater: U(new THREE.Vector3(def.water.rate, def.water.len, def.water.mix)),
      uSpray: U(new THREE.Vector2(def.water.spray, def.water.sprayRate)), uFoam: U(arFoamRect(def, meta.cliffs)),
      uCrest: U(new THREE.Vector2(...def.water.crest.map(r => meta.cliffs.v0 + (1 - r / def.ref.img[1]) * (meta.cliffs.v1 - meta.cliffs.v0)))), uCover: U(T.back - T.lip[0] + .05), uGround: U(new THREE.Color(0x4a3f3a))}});
  const bg = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), ARENA.waterMat);
  bg.frustumCulled = false; bg.name = 'far';
  AR.bgScene.add(bg);
  ARENA.layers = {bg, rects: {sky: sr, cliffs: cr, mist: mr}};
}

// The spray's rect (painting px [x0, x1, row0, row1]) in cliffs-layer uv (v from the bottom): x0, v0, x1, v1.
function arFoamRect(def, b) {
  const [iw, ih] = def.ref.img, [x0, x1, r0, r1] = def.water.foam, U = x => b.u0 + x / iw * (b.u1 - b.u0), V = r => b.v0 + (1 - r / ih) * (b.v1 - b.v0);
  return new THREE.Vector4(U(x0), V(r1), U(x1), V(r0));
}

// Draws the far layers through the camera as it is now (with any shake), before the 3D scene.
function arenaDrawBack() {
  const u = ARENA.waterMat.uniforms, t = Math.tan(camera.fov * Math.PI / 360);
  u.uCam.value.copy(camera.position); u.uTan.value.set(t * camera.aspect, t);
  renderer.render(AR.bgScene, AR.bgCam);
}

// --- Geometry helpers ---
// A growing indexed mesh (positions, normals, uvs, colours), merged into one BufferGeometry.
function arMesh() { return {p: [], n: [], uv: [], c: [], i: []}; }
// A quad a-b-c-d (counter-clockwise seen from its front), normal nrm, uvs, colour col (THREE.Color).
function arQuad(M, a, b, c, d, nrm, uvs, col) {
  const o = M.p.length / 3;
  for (const v of [a, b, c, d]) { M.p.push(v[0], v[1], v[2]); M.n.push(nrm[0], nrm[1], nrm[2]); M.c.push(col.r, col.g, col.b); }
  for (const u of uvs) M.uv.push(u[0], u[1]);
  M.i.push(o, o + 1, o + 2, o, o + 2, o + 3);
}
// A box x0..x1, y0..y1, z0..z1 without its bottom; uv from world coordinates times us.
function arBox(M, x0, x1, y0, y1, z0, z1, col, us) {
  const U = (a, b) => [a * us, b * us];
  arQuad(M, [x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0], [0, 1, 0], [U(x0, z1), U(x1, z1), U(x1, z0), U(x0, z0)], col);
  arQuad(M, [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], [0, 0, 1], [U(x0, y0), U(x1, y0), U(x1, y1), U(x0, y1)], col);
  arQuad(M, [x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [0, 0, -1], [U(x1, y0), U(x0, y0), U(x0, y1), U(x1, y1)], col);
  arQuad(M, [x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [-1, 0, 0], [U(z0, y0), U(z1, y0), U(z1, y1), U(z0, y1)], col);
  arQuad(M, [x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [1, 0, 0], [U(z1, y0), U(z0, y0), U(z0, y1), U(z1, y1)], col);
}
function arGeo(M) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(M.p, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(M.n, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(M.uv, 2));
  g.setAttribute('color', new THREE.Float32BufferAttribute(M.c, 3));
  g.setIndex(M.i);
  return g;
}
// A geometry (any three geometry) appended to M, moved by matrix mx, in colour col (or per-vertex colFn(x, y, z, nrm)).
function arAppend(M, geo, mx, col, colFn) {
  const g = geo.index ? geo : geo, p = g.attributes.position, n = g.attributes.normal, uv = g.attributes.uv;
  const o = M.p.length / 3, v = new THREE.Vector3(), nm = new THREE.Matrix3().getNormalMatrix(mx), w = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i).applyMatrix4(mx); w.fromBufferAttribute(n, i).applyMatrix3(nm).normalize();
    M.p.push(v.x, v.y, v.z); M.n.push(w.x, w.y, w.z);
    M.uv.push(uv ? uv.getX(i) : 0, uv ? uv.getY(i) : 0);
    const c = colFn ? colFn(v.x, v.y, v.z, w) : col;
    M.c.push(c.r, c.g, c.b);
  }
  if (g.index) for (let i = 0; i < g.index.count; i++) M.i.push(o + g.index.getX(i));
  else for (let i = 0; i < p.count; i++) M.i.push(o + i);
}
// The fighters' toon light (f3Lights: the sun through the 3-band gradient F3.grad, plus the sky/stone hemisphere)
// for normal n, as an RGB factor. The arena's pieces do not move, so it is baked into their vertex colours once
// (same look as MeshToonMaterial, without per-pixel lighting).
const AR_SUN = new THREE.Vector3(-4, 6, 5).normalize(), AR_SUN_C = new THREE.Color(0xfff2dc).multiplyScalar(.75);
const AR_SKY = new THREE.Color(0xdcecff), AR_GROUND = new THREE.Color(0x6b5a4a), AR_BANDS = [90 / 255, 170 / 255, 1];
function arLight(nx, ny, nz) {
  const g = Math.min(2, Math.floor((Math.max(-1, nx * AR_SUN.x + ny * AR_SUN.y + nz * AR_SUN.z) * .5 + .5) * 3));
  const w = ny * .5 + .5, b = AR_BANDS[g];
  return [AR_SUN_C.r * b + (AR_GROUND.r + (AR_SKY.r - AR_GROUND.r) * w) * .5,
    AR_SUN_C.g * b + (AR_GROUND.g + (AR_SKY.g - AR_GROUND.g) * w) * .5,
    AR_SUN_C.b * b + (AR_GROUND.b + (AR_SKY.b - AR_GROUND.b) * w) * .5];
}
// A mesh with the toon light baked in, and the outline shell (width w) of M; G (optional) joins the mesh without an
// outline (the grass blades).
function arToon(M, map, w, name, G) {
  for (const X of G ? [M, G] : [M]) for (let i = 0; i < X.c.length; i += 3) {
    const L = arLight(X.n[i], X.n[i + 1], X.n[i + 2]);
    X.c[i] *= L[0]; X.c[i + 1] *= L[1]; X.c[i + 2] *= L[2];
  }
  const line = w > 0 ? f3OutlineGeo(arGeo(M)) : null;
  if (G) {
    const o = M.p.length / 3;
    M.p.push(...G.p); M.n.push(...G.n); M.uv.push(...G.uv); M.c.push(...G.c); for (const i of G.i) M.i.push(o + i);
  }
  const mesh = new THREE.Mesh(arGeo(M), new THREE.MeshBasicMaterial({map, vertexColors: true}));
  mesh.name = name; ARENA.group.add(mesh);
  if (line) {
    const om = F3.outMat.clone(); om.uniforms.uW.value = w;
    const out = new THREE.Mesh(line, om); out.name = name + '.line'; ARENA.group.add(out);
  }
  return mesh;
}

// A canvas texture (size px) painted by draw(ctx, size, rand), repeating.
function arCanvas(size, draw) {
  const t = rdCanvasTexture(size, (g, n) => draw(g, n, arRand));
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}
// Pale mottled stone with a few cracks and moss flecks (tinted by the vertex colours).
function arStoneTex() {
  return arCanvas(256, (g, n, r) => {
    g.fillStyle = '#e9e4dc'; g.fillRect(0, 0, n, n);
    for (let i = 0; i < 260; i++) {
      const x = r() * n, y = r() * n, s = 4 + r() * 22, l = 70 + r() * 25;
      g.fillStyle = 'hsla(30,12%,' + l.toFixed(0) + '%,.22)';
      for (const dx of [-n, 0, n]) for (const dy of [-n, 0, n]) { g.beginPath(); g.arc(x + dx, y + dy, s, 0, 6.283); g.fill(); }
    }
    g.strokeStyle = 'rgba(70,58,50,.45)'; g.lineWidth = 1.2;
    for (let i = 0; i < 7; i++) {
      let x = r() * n, y = r() * n; g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < 5; k++) { x += (r() - .5) * 40; y += (r() - .3) * 30; g.lineTo(x, y); }
      g.stroke();
    }
    for (let i = 0; i < 90; i++) { g.fillStyle = 'rgba(110,140,60,' + (.15 + r() * .25).toFixed(2) + ')'; g.fillRect(r() * n, r() * n, 2 + r() * 4, 2 + r() * 3); }
  });
}

// --- Terrace ---
// Rows of slabs from the front (z = front) to the back (z = back), staggered, tops at y = 0, the dark grout bed under
// the gaps, the back step (lip) and its drop; one mesh and one outline. Colours: warm (sun) on the left, cool on the right.
function arTerrace(def, M) {
  const T = def.terrace, warm = T.warm.map(c => new THREE.Color(c)), cool = T.cool.map(c => new THREE.Color(c));
  const col = new THREE.Color(), tmp = new THREE.Color();
  AR.rows = [];
  for (let zf = T.front; zf > T.back + .01;) {
    let zb = zf - T.row[0] - arRand() * T.row[1];
    if (Math.abs(zb) < T.keep * .5) zb = -T.keep * .5;   // no gap between rows under the fighters' feet
    if (zb - T.back < T.row[0] * .6) zb = T.back;   // no thin last row
    AR.rows.push(zf);
    for (let x = -T.half - arRand() * T.len[0]; x < T.half;) {
      const L = T.len[0] + arRand() * T.len[1], xm = x + L / 2;
      const k = Math.min(1, Math.max(0, (xm + 7) / 14)), pick = arRand();
      col.copy(warm[pick < .5 ? 0 : 1]).lerp(tmp.copy(cool[pick < .5 ? 0 : 1]), k).multiplyScalar(.86 + arRand() * .2);
      const o = M.c.length;
      arBox(M, x + T.gap / 2, x + L - T.gap / 2, -T.depth, 0, zb + T.gap / 2, zf - T.gap / 2, col, .32);
      for (let j = o; j < o + 12; j += 3) { const f = .93 + arRand() * .12; M.c[j] *= f; M.c[j + 1] *= f; M.c[j + 2] *= f; }   // top corners: a little uneven
      x += L;
    }
    zf = zb;
  }
  const grout = new THREE.Color(0x4a3f3a), lip = new THREE.Color(T.cool[1]).multiplyScalar(.95);
  arQuad(M, [-T.half, T.grout, T.front], [T.half, T.grout, T.front], [T.half, T.grout, T.back], [-T.half, T.grout, T.back],
    [0, 1, 0], [[0, 0], [1, 0], [1, 1], [0, 1]], grout);
  for (let x = -T.half; x < T.half;) {   // the lip: blocks a little higher than the slabs, then the drop
    const L = 1.1 + arRand() * .8;
    arBox(M, x + .02, Math.min(T.half, x + L) - .02, -2.5, T.lip[1] * (.75 + arRand() * .5), T.back - T.lip[0], T.back - .01,
      col.copy(lip).multiplyScalar(.9 + arRand() * .14), .55);
    x += L;
  }
}

// Grass tufts as blades of real geometry (thin triangles, dark at the root and light at the tip, both windings so
// they show from either side) in G: no texture, no transparency (cheap to draw, on phones too). In the gaps between
// rows (never in the fighters' lane), along the lip, round the rocks and props, and dense clumps for the bushes.
function arGrass(def, G) {
  const T = def.terrace, spots = [], rows = AR.rows;
  for (let i = 0; i < T.grass; i++) {
    const z = rows[Math.floor(arRand() * rows.length)];
    if (Math.abs(z) < T.keep) continue;
    spots.push([(arRand() * 2 - 1) * (T.half - .5), z, .12 + arRand() * .14, 7]);
  }
  for (let x = -T.half + .3; x < T.half; x += .35 + arRand() * .9) spots.push([x, T.back - T.lip[0] * .5, .22 + arRand() * .25, 7]);
  for (const [x, z, r] of def.rocks) for (let k = 0; k < 4; k++)
    spots.push([x + (arRand() - .5) * r * 3, z + .2 + arRand() * .4, .2 + arRand() * .2, 7]);
  for (const [x, z, r] of def.bushes) for (let k = 0; k < 9; k++)
    spots.push([x + (arRand() - .5) * r * 1.6, z + (arRand() - .5) * r * .6, r * (.55 + arRand() * .45), 10]);
  for (let k = 0; k < 5; k++) spots.push([def.column.x + (arRand() - .5) * 1.2, def.column.z + .35 + arRand() * .3, .25 + arRand() * .2, 8]);
  for (let k = 0; k < 3; k++) spots.push([def.lantern.x + (arRand() - .5) * 1, def.lantern.z + .3 + arRand() * .3, .22 + arRand() * .18, 8]);
  const root = new THREE.Color(0x3f6a24), tips = [0x79a83a, 0x94b842, 0xc8d66a].map(c => new THREE.Color(c)), up = [0, 1, 0];
  const tip = new THREE.Color(), base = new THREE.Color();
  for (const [x, z, s, n] of spots) {
    const y = z < T.back - .05 ? T.lip[1] * .8 : 0, b = .8 + arRand() * .2;
    for (let k = 0; k < n; k++) {
      const rx = x + (arRand() - .5) * s * .5, rz = z + (arRand() - .5) * s * .3, a = (arRand() - .5) * 1.4, yaw = arRand() * 6.283;
      const h = s * (.45 + arRand() * .6), w = s * (.05 + arRand() * .03);
      const tx = rx + Math.sin(a) * Math.cos(yaw) * h, ty = y + Math.cos(a) * h, tz = rz + Math.sin(a) * Math.sin(yaw) * h * .4;
      base.copy(root).multiplyScalar(b); tip.copy(tips[Math.floor(arRand() * 3)]).multiplyScalar(b);
      const o = G.p.length / 3;
      G.p.push(rx - w, y, rz, rx + w, y, rz, tx, ty, tz);
      for (let v = 0; v < 3; v++) { G.n.push(...up); G.uv.push(.5, .5); }
      G.c.push(base.r, base.g, base.b, base.r, base.g, base.b, tip.r, tip.g, tip.b);
      G.i.push(o, o + 1, o + 2, o, o + 2, o + 1);
    }
  }
}

// --- Props ---
// A deterministic jitter in [-1, 1] of a position (so the copies of a vertex shared by faces move together).
function arJit(x, y, z, k) {
  const h = Math.sin(x * 127.1 + y * 311.7 + z * 74.7 + k * 19.3) * 43758.5453;
  return (h - Math.floor(h)) * 2 - 1;
}
// Ivy on the column: a few vines climbing from the foot, small leaves (diamonds facing out of the shaft) in four greens.
function arIvy(def, M, shaftH) {
  const C = def.column, greens = [0x4f7f2a, 0x6f9e34, 0x9cc048, 0x3d6522].map(c => new THREE.Color(c)), R = C.r * 1.03 + .012;
  for (let v = 0; v < 6; v++) {
    let a = arRand() * 6.283, y = .4;
    const top = .36 + shaftH * (.35 + arRand() * .55);
    while (y < top) {
      const n = 1 + Math.round(arRand() * 2 * (1 - y / (top + .3)));
      for (let k = 0; k < n; k++) {
        const b = a + (arRand() - .5) * .35, h = y + (arRand() - .5) * .06, s = .045 + arRand() * .035;
        const nx = Math.sin(b), nz = Math.cos(b), cx = C.x + R * nx, cz = C.z + R * nz, tx = nz * s * .75, tz = -nx * s * .75;
        arQuad(M, [cx, h - s, cz], [cx + tx, h, cz + tz], [cx, h + s, cz], [cx - tx, h, cz - tz], [nx, 0, nz],
          [[.5, 0], [1, .5], [.5, 1], [0, .5]], greens[Math.floor(arRand() * 4)]);
      }
      a += (arRand() - .5) * .5; y += .06 + arRand() * .05;
    }
  }
}

function arProps(def, M) {
  const C = def.column, white = new THREE.Color(0xd6cdbf), stoneC = new THREE.Color(0xcbc1b2), mx = new THREE.Matrix4();
  // Column: base, shaft, capital, broken stub with a jagged top.
  const box = (w, h, d, x, y, z, ry) => { const g = new THREE.BoxGeometry(w, h, d); mx.makeRotationY(ry || 0).setPosition(x, y, z); return g; };
  arAppend(M, box(.98, .2, .98, C.x, .1, C.z), mx, white);
  arAppend(M, box(.82, .16, .82, C.x, .28, C.z, .05), mx, white);
  const shaftH = C.h - .62, shaft = new THREE.CylinderGeometry(C.r, C.r * 1.06, shaftH, 14, 4);
  mx.makeRotationY(.2).setPosition(C.x, .36 + shaftH / 2, C.z); arAppend(M, shaft, mx, white);
  arAppend(M, box(.86, .3, .86, C.x + .03, .36 + shaftH + .15, C.z, -.08), mx, white);
  // The broken top: two tilted chunks of the capital's upper block, one corner lower than the rest.
  const chunk = (w, h, d, x, y, z, rx, ry, rz) => {
    const g = new THREE.BoxGeometry(w, h, d), p = g.attributes.position;
    for (let i = 0; i < p.count; i++) if (p.getY(i) > 0) p.setY(i, p.getY(i) - h * .6 * Math.max(0, arJit(Math.sign(p.getX(i)), 0, Math.sign(p.getZ(i)), 4)));
    g.computeVertexNormals();
    mx.makeRotationFromEuler(new THREE.Euler(rx, ry, rz)).setPosition(x, y, z); arAppend(M, g, mx, stoneC);
  };
  chunk(.62, .34, .7, C.x - .1, .36 + shaftH + .47, C.z, 0, .3, .07);
  chunk(.3, .26, .36, C.x + .2, .36 + shaftH + .42, C.z + .1, .1, -.4, -.25);
  arIvy(def, M, shaftH);

  // Pole (bronze), lantern, rocks.
  const P = M, bronze = new THREE.Color(0x8a6a3c), pole = C.pole, px0 = C.x + C.r * .6, pz = C.z + .12;
  const rod = new THREE.CylinderGeometry(.032, .032, pole.len, 8);
  mx.makeRotationZ(Math.PI / 2).setPosition(px0 + pole.len / 2, pole.y, pz); arAppend(P, rod, mx, bronze);
  mx.makeTranslation(px0 + pole.len, pole.y, pz); arAppend(P, new THREE.SphereGeometry(.055, 8, 6), mx, bronze);
  const Lt = def.lantern, k = Lt.h / 1.55, stone = new THREE.Color(0xc9c2b6), dark = new THREE.Color(0x2b2622);
  const moss = (base) => (x, y, z, n) => n.y > .55 && arJit(x, y, z, 2) > -.2 ? new THREE.Color(0x8fae4a) : base;
  const lb = (w, h, d, y, col, ry) => { mx.makeRotationY(ry || 0).setPosition(Lt.x, y * k, Lt.z); arAppend(P, new THREE.BoxGeometry(w * k, h * k, d * k), mx, null, moss(col)); };
  lb(.62, .12, .62, .06, stone); lb(.44, .1, .44, .17, stone);
  mx.makeTranslation(Lt.x, .51 * k, Lt.z); arAppend(P, new THREE.CylinderGeometry(.1 * k, .12 * k, .58 * k, 8), mx, stone);
  lb(.52, .08, .52, .84, stone); lb(.36, .34, .36, 1.05, stone);
  mx.makeTranslation(Lt.x, 1.05 * k, Lt.z + .181 * k); arAppend(P, new THREE.BoxGeometry(.17 * k, .17 * k, .01), mx, dark);
  mx.makeTranslation(Lt.x - .181 * k, 1.05 * k, Lt.z); arAppend(P, new THREE.BoxGeometry(.01, .17 * k, .17 * k), mx, dark);
  mx.makeRotationY(Math.PI / 4).setPosition(Lt.x, 1.35 * k, Lt.z); arAppend(P, new THREE.ConeGeometry(.46 * k, .26 * k, 4), mx, null, moss(stone));
  mx.makeTranslation(Lt.x, 1.53 * k, Lt.z); arAppend(P, new THREE.SphereGeometry(.07 * k, 8, 6), mx, stone);
  // Rocks: low icosahedra, jittered, mossy on top.
  for (const [x, z, r] of def.rocks) {
    const g = new THREE.IcosahedronGeometry(r, 1), p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const f = 1 + .22 * arJit(p.getX(i), p.getY(i), p.getZ(i), 3); p.setXYZ(i, p.getX(i) * f, p.getY(i) * f * .62, p.getZ(i) * f); }
    g.computeVertexNormals();
    mx.makeRotationY(x).setPosition(x, r * .3, z); arAppend(P, g, mx, null, moss(new THREE.Color(0xa49d96)));
  }
  arBanner(def, px0, pz);
}

// The banner: a cols x rows cloth hanging from the pole (top row fixed), torn at the bottom, moved by gravity and a
// gusty wind from the left (Verlet, fixed 1/60 s steps, iters constraint passes). Graphics only.
function arBanner(def, px0, pz) {
  const B = def.banner, C = def.column, n = B.cols * B.rows, x0 = px0 + .12, y0 = C.pole.y - .03;
  const dx = B.w / (B.cols - 1), dy = B.h / (B.rows - 1), pos = new Float32Array(n * 3);
  for (let r = 0; r < B.rows; r++) for (let c = 0; c < B.cols; c++) pos.set([x0 + c * dx, y0 - r * dy, pz], (r * B.cols + c) * 3);
  AR.cloth = {pos, prev: pos.slice(), rest: pos.slice(0, B.cols * 3), dx, dy, t: 0, xMin: C.x + C.r + .04};
  const tex = rdCanvasTexture(128, (g, w) => {   // 128 x 128 stretched on the banner: red, darker hems, torn bottom
    g.clearRect(0, 0, w, w);
    g.fillStyle = '#c8372d'; g.beginPath(); g.moveTo(0, 0); g.lineTo(w, 0);
    for (let i = 0; i <= 12; i++) {   // the tear: higher on the left, a long tail on the right
      const x = w - i * w / 12, base = w * (.98 - .32 * (i / 12) ** 1.4);
      g.lineTo(x, base - (i % 2 ? w * (.04 + .05 * arRand()) : 0));
    }
    g.closePath(); g.fill();
    g.globalCompositeOperation = 'source-atop';   // hems and flecks only on the cloth
    g.fillStyle = 'rgba(90,16,14,.55)'; g.fillRect(0, 0, w, w * .045); g.fillRect(0, 0, w * .05, w); g.fillRect(w * .95, 0, w * .05, w);
    g.fillStyle = 'rgba(255,170,120,.18)';
    for (let i = 0; i < 18; i++) g.fillRect(arRand() * w, arRand() * w * .8, 2 + arRand() * 6, 2 + arRand() * 10);
  });
  const geo = new THREE.PlaneGeometry(B.w, B.h, B.cols - 1, B.rows - 1);
  geo.attributes.position.array.set(pos);
  const mesh = new THREE.Mesh(geo, new THREE.MeshToonMaterial({color: 0xffffff, map: tex, alphaTest: .5,
    side: THREE.DoubleSide, gradientMap: F3.grad}));
  mesh.name = 'banner'; mesh.frustumCulled = false;
  ARENA.banner = mesh; ARENA.group.add(mesh);
  for (let i = 0; i < 240; i++) arClothStep(def);   // settled before the first frame
  arClothSync();
}

// One 1/60 s step of the banner.
function arClothStep(def) {
  const B = def.banner, K = AR.cloth, p = K.pos, q = K.prev, h = 1 / 60, cols = B.cols, n = cols * B.rows;
  const t = K.t += h, gust = .5 + .5 * Math.sin(t * 1.3) * Math.sin(t * .37 + 1);
  for (let i = cols; i < n; i++) {
    const r = Math.floor(i / cols), c = i % cols, j = i * 3, f = r / (B.rows - 1);
    const ax = (B.wind[0] + B.wind[1] * gust) * (.4 + .6 * f) + .6 * Math.sin(t * 2.1 + r * .5);
    const az = B.flutter * Math.sin(t * 3.1 + r * .7 + c * .9) * f + .8 * Math.sin(c * 1.7 + t * .8) * f, ay = -9.8;
    for (let k = 0; k < 3; k++) {
      const v = (p[j + k] - q[j + k]) * B.drag; q[j + k] = p[j + k];
      p[j + k] += v + [ax, ay, az][k] * h * h;
    }
  }
  const link = (a, b, L) => {
    const A = a * 3, Bb = b * 3, ex = p[Bb] - p[A], ey = p[Bb + 1] - p[A + 1], ez = p[Bb + 2] - p[A + 2];
    const d = Math.sqrt(ex * ex + ey * ey + ez * ez) || 1e-6, k = (d - L) / d * (a < cols ? 1 : .5);   // a fixed: b takes it all
    if (a >= cols) { p[A] += ex * k; p[A + 1] += ey * k; p[A + 2] += ez * k; }
    p[Bb] -= ex * k; p[Bb + 1] -= ey * k; p[Bb + 2] -= ez * k;
  };
  for (let it = 0; it < B.iters; it++) {
    for (let i = 0; i < n; i++) {
      const c = i % cols;
      if (c < cols - 1 && i >= cols) link(i, i + 1, K.dx);
      if (i + cols < n) link(i, i + cols, K.dy);
    }
    for (let i = 0; i < cols * 3; i++) p[i] = K.rest[i];   // the top row stays on the pole
    for (let i = cols; i < n; i++) if (p[i * 3] < K.xMin) p[i * 3] = K.xMin;   // never into the column
  }
}

function arClothSync() {
  const g = ARENA.banner.geometry;
  g.attributes.position.array.set(AR.cloth.pos); g.attributes.position.needsUpdate = true;
  g.computeVertexNormals();
}

// Once per drawn frame: water, clouds, mist (time only) and the banner (fixed 1/60 s steps of the drawn time).
function arenaStep(nowMs, S) {
  const d = AR.def, t = nowMs / 1000, u = ARENA.waterMat.uniforms;
  u.uTime.value = t;
  u.uSkyOff.value = d.skyDrift * Math.sin(t * 6.2831853 / d.skyPeriod);
  if (!AR.cloth) return;
  if (AR.last < 0 || nowMs < AR.last || nowMs - AR.last > 1000) AR.last = nowMs;   // first frame, a reset or a long pause
  let n = Math.floor((nowMs - AR.last) * .06);
  if (n > 0) { AR.last += n / .06; n = Math.min(4, n); for (let i = 0; i < n; i++) arClothStep(d); arClothSync(); }
}

// Draw calls and triangles of the arena group as it is (visible meshes; instanced meshes count once).
function arStats() {
  let draws = 1, tris = 2;   // the far layers' quad
  ARENA.group.traverse(o => {
    if (!o.isMesh || !o.visible) return;
    const g = o.geometry, n = g.index ? g.index.count : g.attributes.position.count;
    draws++; tris += n / 3 * (o.isInstancedMesh ? o.count : 1);
  });
  return {draws, tris};
}
