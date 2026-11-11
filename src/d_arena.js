// The 3D arena: far painted layers (sky, cliffs with the flowing waterfall, mist) on big planes at their own depth,
// and near 3D pieces in the fighters' toon style (stone terrace with grass, column with a waving banner, lantern,
// rocks, bushes). Built from CFG.arenas[name] (arenaBuild) and animated once per drawn frame (arenaStep). Graphics
// only: it reads the sim state and never writes it. Metres; the fighters stand at z ~ 0 on y = 0 (the slabs' tops);
// the camera looks along -z (d_render.js).

// group = the whole arena; layers = {sky, cliffs, mist} meshes; banner = the cloth mesh; leaves = the drifting leaves
// (d_render.js); waterMat = the cliffs' ShaderMaterial; stats() = {draws, tris} of the arena group.
const ARENA = {group: null, layers: {}, banner: null, leaves: new THREE.Group(), waterMat: null, stats: arStats};
// Private: def = the arena's CFG entry, seed = render-only generator, cloth = the banner's points.
const AR = {def: null, seed: 11, cloth: null, last: -1, acc: 0};

const AR_LAYER_VERT = 'varying vec2 vUv;\nvoid main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }';
// Sky and cliffs. uScale turns layer uv into painting uv (the water's numbers are the flat backdrop's, per painting
// width/height). SKY: the clouds sway in u (mirrored past the edges). WATER: the mask (uWater) shimmers and scrolls
// streaks as before; ALPHA: the cliffs' cut-out (uAlpha).
const AR_LAYER_FRAG = `
uniform sampler2D uMap, uAlpha, uWater;
uniform vec2 uScale;
uniform float uTime, uContrast, uLift, uFlow, uStreak, uWobble, uSkyOff;
varying vec2 vUv;
float arHash(vec2 p){ p = 50. * fract(p * .3183099 + vec2(.71, .113)); return fract(p.x * p.y * (p.x + p.y)); }
float arNoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  float y0 = mod(i.y, 64.), y1 = mod(i.y + 1., 64.);
  return mix(mix(arHash(vec2(i.x, y0)), arHash(vec2(i.x + 1., y0)), f.x),
             mix(arHash(vec2(i.x, y1)), arHash(vec2(i.x + 1., y1)), f.x), f.y);
}
void main(){
  vec2 uv = vUv;
#ifdef SKY
  uv.x = 1. - abs(1. - mod(uv.x + uSkyOff + 2., 2.));
#endif
  float a = 1.;
#ifdef ALPHA
  a = texture2D(uAlpha, uv).r;
  if (a < .01) discard;
#endif
  vec3 c;
#ifdef WATER
  float m = texture2D(uWater, uv).r;
  vec2 p = uv * uScale;
  vec2 w = uv + vec2(0., sin(p.x * 90. + mod(uTime * 3., 6.2831853)) * uWobble * m / uScale.y);
  c = (texture2D(uMap, w).rgb - .5) * uContrast + .5 + uLift;
  if (m > .004) c += m * (arNoise(vec2(p.x * 140., p.y * 6. + mod(uTime * uFlow * 6., 64.))) - .5) * uStreak;
#else
  c = (texture2D(uMap, uv).rgb - .5) * uContrast + .5 + uLift;
#endif
  gl_FragColor = vec4(c, a);
}`;
// The mist band: alpha from the noise texture (red), drifting in u, in the painting's mist colour.
const AR_MIST_FRAG = `
uniform sampler2D uMap;
uniform vec3 uColor;
uniform float uTime, uDrift, uOpacity, uRep;
varying vec2 vUv;
void main(){
  float a = texture2D(uMap, vec2(vUv.x * uRep + uTime * uDrift, vUv.y)).r * uOpacity;
  a *= smoothstep(0., .08, vUv.x) * smoothstep(1., .92, vUv.x);
  gl_FragColor = vec4(uColor, a);
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
  const keys = ['sky.jpg', 'cliffs.jpg', 'cliffs_a.png', 'water.png', 'mist.png'].map(k => 'arena/cascata_' + k);
  return Promise.all(keys.map(rdTexture)).then(([sky, cliffs, alpha, water, mist]) => {
    const gl2 = renderer.capabilities.isWebGL2;
    for (const t of [sky, cliffs, alpha, water]) {   // not powers of two: WebGL1 has no mipmaps for them
      t.generateMipmaps = gl2; t.minFilter = gl2 ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
      t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
    }
    mist.wrapS = THREE.RepeatWrapping;
    f3Shared();
    arLayers(def, sky, cliffs, alpha, water, mist);
    arTerrace(def);
    arProps(def);
    scene.add(g);
    for (const t of [sky, cliffs, alpha, water, mist]) renderer.initTexture(t);
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

// A plane at depth z covering the layer whose painting box (in layer uv) is box = {u0, u1, v0, v1}.
function arLayerPlane(def, P, box, z) {
  const pu = U => (U - box.u0) / (box.u1 - box.u0), pv = V => (V - box.v0) / (box.v1 - box.v0);
  const [x0, y0] = arPaintToWorld(def, P, pu(0), pv(0), z), [x1, y1] = arPaintToWorld(def, P, pu(1), pv(1), z);
  const geo = new THREE.PlaneGeometry(x1 - x0, y1 - y0);
  geo.translate((x0 + x1) / 2, (y0 + y1) / 2, z);
  return {geo, rect: [x0, y0, x1, y1]};
}

function arLayers(def, sky, cliffs, alpha, water, mist) {
  const P = arRefPlace(def), meta = ASSETS['arena/cascata_layers.json'], L = def.layers;
  const base = {uTime: {value: 0}, uContrast: {value: def.contrast}, uLift: {value: def.lift}, uFlow: {value: def.flow},
    uStreak: {value: def.streak}, uWobble: {value: def.wobble}, uSkyOff: {value: 0}};
  const scale = b => new THREE.Vector2(1 / (b.u1 - b.u0), 1 / (b.v1 - b.v0));
  // Sky: opaque, first.
  const sp = arLayerPlane(def, P, meta.sky, L.sky);
  const skyMat = new THREE.ShaderMaterial({vertexShader: AR_LAYER_VERT, fragmentShader: AR_LAYER_FRAG, defines: {SKY: 1},
    depthWrite: false, uniforms: Object.assign({}, base, {uMap: {value: sky}, uScale: {value: scale(meta.sky)}})});
  // Cliffs: cut out of the sky, with the waterfall; drawn after the opaque scene (transparent), behind everything.
  const cp = arLayerPlane(def, P, meta.cliffs, L.cliffs);
  ARENA.waterMat = new THREE.ShaderMaterial({vertexShader: AR_LAYER_VERT, fragmentShader: AR_LAYER_FRAG,
    defines: {ALPHA: 1, WATER: 1}, transparent: true, depthWrite: false,
    uniforms: Object.assign({}, base, {uTime: {value: 0}, uMap: {value: cliffs}, uAlpha: {value: alpha},
      uWater: {value: water}, uScale: {value: scale(meta.cliffs)}})});
  // Mist: painting rows mist.rows projected at its depth, as wide as the cliffs' plane there.
  const m = def.mist, [ih] = [def.ref.img[1]];
  const [, ytop] = arPaintToWorld(def, P, .5, 1 - m.rows[0] / ih, L.mist), [, ybot] = arPaintToWorld(def, P, .5, 1 - m.rows[1] / ih, L.mist);
  const k = (CFG.cam.distMax - L.mist) / (CFG.cam.distMax - L.cliffs), mw = (cp.rect[2] - cp.rect[0]) * k;
  const mgeo = new THREE.PlaneGeometry(mw, ytop - ybot);
  mgeo.translate(0, (ytop + ybot) / 2, L.mist);
  const mc = new THREE.Color().fromArray(meta.mistColor);
  mc.r = Math.min(1, mc.r + m.lift); mc.g = Math.min(1, mc.g + m.lift); mc.b = Math.min(1, mc.b + m.lift);
  const mistMat = new THREE.ShaderMaterial({vertexShader: AR_LAYER_VERT, fragmentShader: AR_MIST_FRAG, transparent: true,
    depthWrite: false, uniforms: {uMap: {value: mist}, uColor: {value: mc}, uTime: {value: 0}, uDrift: {value: m.drift},
      uOpacity: {value: m.opacity}, uRep: {value: Math.max(1, Math.round(mw / 30))}}});
  const add = (name, geo, mat, order) => {
    const me = new THREE.Mesh(geo, mat); me.name = name; me.renderOrder = order; me.frustumCulled = false;
    ARENA.layers[name] = me; ARENA.group.add(me);
  };
  add('sky', sp.geo, skyMat, -3); add('cliffs', cp.geo, ARENA.waterMat, -2); add('mist', mgeo, mistMat, -1);
  ARENA.layers.rects = {sky: sp.rect, cliffs: cp.rect};
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
// A toon mesh and its outline shell (width w) from M, added to the arena.
function arToon(M, map, w, name) {
  const geo = arGeo(M), mat = new THREE.MeshToonMaterial({map, vertexColors: true, gradientMap: F3.grad});
  const mesh = new THREE.Mesh(geo, mat); mesh.name = name; ARENA.group.add(mesh);
  if (w > 0) {
    const om = F3.outMat.clone(); om.uniforms.uW.value = w;
    const out = new THREE.Mesh(f3OutlineGeo(geo), om); out.name = name + '.line'; ARENA.group.add(out);
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
function arTerrace(def) {
  const T = def.terrace, M = arMesh(), warm = T.warm.map(c => new THREE.Color(c)), cool = T.cool.map(c => new THREE.Color(c));
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
  arToon(M, arStoneTex(), T.line, 'terrace');
  arGrass(def);
}

// Grass tufts: two crossed quads per tuft, one instanced mesh; in the gaps between rows (never in the fighters'
// lane), along the lip and round the props' feet.
function arGrass(def) {
  const T = def.terrace, tex = arCanvas(128, (g, n, r) => {
    g.clearRect(0, 0, n, n);
    for (let i = 0; i < 26; i++) {   // thin blades fanning out of one root, dark at the root, light at the tips
      const x = n * (.42 + (r() - .5) * .25), a = (r() - .5) * 1.5, h = n * (.35 + r() * .6);
      const tx = x + Math.sin(a) * h, ty = n - Math.cos(a) * h, gr = g.createLinearGradient(0, n, 0, ty);
      gr.addColorStop(0, '#3f6a24'); gr.addColorStop(.55, i % 4 ? '#79a83a' : '#94b842'); gr.addColorStop(1, '#c8d66a');
      g.fillStyle = gr; g.beginPath(); g.moveTo(x - 2.2, n); g.quadraticCurveTo(x + (tx - x) * .4, n - h * .55, tx, ty);
      g.quadraticCurveTo(x + (tx - x) * .4 + 1, n - h * .5, x + 2.2, n); g.fill();
    }
  });
  tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
  const geo = new THREE.BufferGeometry(), p = [], uv = [], idx = [];
  for (const a of [0, Math.PI / 2]) {
    const c = Math.cos(a) / 2, s = Math.sin(a) / 2, o = p.length / 3;
    p.push(-c, 0, -s, c, 0, s, c, 1, s, -c, 1, -s); uv.push(0, 0, 1, 0, 1, 1, 0, 1); idx.push(o, o + 1, o + 2, o, o + 2, o + 3);
  }
  geo.setAttribute('position', new THREE.Float32BufferAttribute(p, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setIndex(idx);
  const spots = [];
  const rows = AR.rows;
  for (let i = 0; i < T.grass; i++) {
    const z = rows[Math.floor(arRand() * rows.length)];
    if (Math.abs(z) < T.keep) continue;
    spots.push([(arRand() * 2 - 1) * (T.half - .5), z, .12 + arRand() * .14]);
  }
  for (let x = -T.half + .3; x < T.half; x += .35 + arRand() * .9) spots.push([x, T.back - T.lip[0] * .5, .22 + arRand() * .25]);
  for (const [x, z, r] of def.rocks) for (let k = 0; k < 4; k++)
    spots.push([x + (arRand() - .5) * r * 3, z + .2 + arRand() * .4, .2 + arRand() * .2]);
  for (const [x, z, r] of def.bushes) for (let k = 0; k < 9; k++)   // bushes: dense clumps of tall tufts
    spots.push([x + (arRand() - .5) * r * 1.6, z + (arRand() - .5) * r * .6, r * (.55 + arRand() * .45)]);
  spots.push(...[0, 1, 2, 3, 4].map(() => [def.column.x + (arRand() - .5) * 1.2, def.column.z + .35 + arRand() * .3, .25 + arRand() * .2]));
  spots.push(...[0, 1, 2].map(() => [def.lantern.x + (arRand() - .5) * 1, def.lantern.z + .3 + arRand() * .3, .22 + arRand() * .18]));
  const mat = new THREE.MeshBasicMaterial({map: tex, alphaTest: .5, side: THREE.DoubleSide});
  const im = new THREE.InstancedMesh(geo, mat, spots.length), mx = new THREE.Matrix4(), q = new THREE.Quaternion();
  const c = new THREE.Color(), e = new THREE.Euler();
  spots.forEach(([x, z, s], i) => {
    e.set(0, arRand() * Math.PI, 0); q.setFromEuler(e);
    mx.compose(new THREE.Vector3(x, z < T.back - .05 ? T.lip[1] * .8 : 0, z), q, new THREE.Vector3(s * 1.6, s, s * 1.6));
    im.setMatrixAt(i, mx);
    const b = .78 + arRand() * .22; c.setRGB(b, b * (.95 + arRand() * .08), b * .85); im.setColorAt(i, c);
  });
  im.name = 'grass'; ARENA.group.add(im);
}

// --- Props ---
// A deterministic jitter in [-1, 1] of a position (so the copies of a vertex shared by faces move together).
function arJit(x, y, z, k) {
  const h = Math.sin(x * 127.1 + y * 311.7 + z * 74.7 + k * 19.3) * 43758.5453;
  return (h - Math.floor(h)) * 2 - 1;
}
// Stone with ivy for the column: joints every ~0.5 m, ivy leaves climbing up from the foot (u wraps round).
function arColumnTex() {
  return arCanvas(256, (g, n, r) => {
    g.fillStyle = '#ece8e0'; g.fillRect(0, 0, n, n);
    for (let i = 0; i < 160; i++) { g.fillStyle = 'hsla(35,10%,' + (68 + r() * 26).toFixed(0) + '%,.25)'; g.beginPath(); g.arc(r() * n, r() * n, 3 + r() * 14, 0, 6.283); g.fill(); }
    g.strokeStyle = 'rgba(80,70,64,.55)'; g.lineWidth = 1.5;
    for (let y = n * .12; y < n; y += n * .16) { g.beginPath(); g.moveTo(0, y + r() * 3); g.lineTo(n, y + r() * 3); g.stroke(); }
    for (let v = 0; v < 6; v++) {   // vines: from the bottom (canvas y = n) up, thinning out
      let x = r() * n, y = n; const top = n * (.15 + r() * .5);
      while (y > top) {
        const leaves = 1 + Math.round(r() * 2 * (y / n));
        for (let k = 0; k < leaves; k++) {
          const lx = x + (r() - .5) * 18, ly = y + (r() - .5) * 10, s = 4 + r() * 5;
          g.fillStyle = ['#4f7f2a', '#6f9e34', '#9cc048', '#3d6522'][Math.floor(r() * 4)];
          g.beginPath(); g.ellipse(lx, ly, s, s * .6, r() * 3, 0, 6.283); g.fill();
        }
        x += (r() - .5) * 14; y -= 6 + r() * 6;
      }
    }
  });
}

function arProps(def) {
  const C = def.column, M = arMesh(), white = new THREE.Color(0xd6cdbf), stoneC = new THREE.Color(0xcbc1b2), mx = new THREE.Matrix4();
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
  arToon(M, arColumnTex(), .014, 'column');

  // Pole (bronze), lantern, rocks and bushes: one mesh, stone texture tinted per vertex.
  const P = arMesh(), bronze = new THREE.Color(0x8a6a3c), pole = C.pole, px0 = C.x + C.r * .6, pz = C.z + .12;
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
  arToon(P, arStoneTex(), .012, 'props');
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
  const d = AR.def, t = nowMs / 1000, L = ARENA.layers;
  L.cliffs.material.uniforms.uTime.value = t;
  L.sky.material.uniforms.uSkyOff.value = d.skyDrift * Math.sin(t * 6.2831853 / d.skyPeriod);
  L.mist.material.uniforms.uTime.value = t % 1000;
  if (!AR.cloth) return;
  if (AR.last < 0 || nowMs < AR.last || nowMs - AR.last > 1000) AR.last = nowMs;   // first frame, a reset or a long pause
  let n = Math.floor((nowMs - AR.last) * .06);
  if (n > 0) { AR.last += n / .06; n = Math.min(4, n); for (let i = 0; i < n; i++) arClothStep(d); arClothSync(); }
}

// Draw calls and triangles of the arena group as it is (visible meshes; instanced meshes count once).
function arStats() {
  let draws = 0, tris = 0;
  ARENA.group.traverse(o => {
    if (!o.isMesh || !o.visible) return;
    const g = o.geometry, n = g.index ? g.index.count : g.attributes.position.count;
    draws++; tris += n / 3 * (o.isInstancedMesh ? o.count : 1);
  });
  return {draws, tris};
}
