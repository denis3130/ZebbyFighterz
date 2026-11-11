// The 3D arena: far painted depth planes, like an anime multiplane camera (the dark forest low on the left, the near
// cliffs, the high cliffs, the waterfall, the far haze, the sky, with drifting mist banks between them), and near 3D
// pieces in the fighters' toon style (stone terrace with grass, column with a waving banner, lantern, rocks). Built
// from CFG.arenas[name] (arenaBuild) and animated once per drawn frame (arenaStep). Graphics only: it reads the sim
// state and never writes it. Metres; the fighters stand at z ~ 0 on y = 0 (the slabs' tops); the camera looks along
// -z (d_render.js).

// group = the near 3D arena; far = the far planes' group; layers = {planes: [{name, z, rect, box}] nearest first,
// mists: [{z, rect}]}; banner = the cloth mesh; leaves = the drifting leaves (d_render.js); waterMat = the waterfall
// plane's ShaderMaterial; stats() = {draws, tris} of the arena (near and far).
const ARENA = {group: null, far: null, layers: {}, banner: null, leaves: new THREE.Group(), waterMat: null, stats: arStats};
// Private: def = the arena's CFG entry, seed = render-only generator, cloth = the banner's points, mats = the far
// planes' materials (their time uniforms), skyK = sky sway per painting width.
const AR = {def: null, seed: 11, cloth: null, last: -1, mats: [], skyK: 1};

// The far planes are real 3D meshes at their own depth, each made only of its strips (tight quads, tools/
// make_layers.py), drawn far to near with alpha blending after the near scene, so whatever the terrace and the fighters
// cover is never drawn. uv = the texel in the atlas (uC colours, uM: red = alpha, green = water); aU = the plane's own
// uv (0..1 over its painting box).
const AR_FAR_VERT = `attribute vec2 aU;
varying vec2 vUv, vU;
void main(){ vUv = uv; vU = aU; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const AR_FAR_HEAD = `uniform sampler2D uC, uM, uMist;
uniform float uTime, uContrast, uLift;
varying vec2 vUv, vU;
vec3 arGrade(vec3 c){ return (c - .5) * uContrast + .5 + uLift; }
float arHash(vec2 p){ p = 50. * fract(p * .3183099 + vec2(.71, .113)); return fract(p.x * p.y * (p.x + p.y)); }
float arNoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  float y0 = mod(i.y, 64.), y1 = mod(i.y + 1., 64.);
  return mix(mix(arHash(vec2(i.x, y0)), arHash(vec2(i.x + 1., y0)), f.x),
             mix(arHash(vec2(i.x, y1)), arHash(vec2(i.x + 1., y1)), f.x), f.y);
}
`;
const AR_FAR_FRAG = {
  // A plane: its colours by its alpha (the colour is read only where it shows).
  // No discard anywhere: with it the GPU would shade the pixels the near scene hides before testing their depth.
  plane: `void main(){ float a = texture2D(uM, vUv).r; vec3 c = vec3(0.); if (a > .003) c = arGrade(texture2D(uC, vUv).rgb); gl_FragColor = vec4(c, a); }`,
  // The sky: opaque, the clouds sway in u (mirrored past the edges); uAt = its atlas rect (u0, v0, du, dv).
  sky: `uniform vec4 uAt; uniform float uSkyOff;
void main(){ vec2 u = vec2(1. - abs(1. - mod(vU.x + uSkyOff + 2., 2.)), vU.y);
  gl_FragColor = vec4(arGrade(texture2D(uC, uAt.xy + clamp(u, .002, .998) * uAt.zw).rgb), 1.); }`,
  // A mist bank: the noise band drifting in u, in the painting's mist colour.
  mist: `uniform vec3 uColor; uniform float uRep, uDrift, uOpacity;
void main(){ float a = texture2D(uMist, vec2(vU.x * uRep + mod(uTime * uDrift, 1.), vU.y)).r * uOpacity;
  gl_FragColor = vec4(uColor, a); }`,
  // The waterfall: the painted water falls, slow under the crest and faster and faster lower down (uFlowV.xy = px/s at
  // painting rows uRows.x and uRows.y); each stream (a few tens of px wide) has its own speed and its own beat, so the
  // fall never pulses as one; two copies of the painting half a beat apart (uFlowV.z = s), each counting only where
  // it samples water too, starting softly under the crest (uCrest rows), mixed in by uFlowV.w; at its foot the spray
  // boils up: a light veil and puffs. uBox = the plane's painting box (x0, y0, x1, y1, px, y down), uAt = its atlas
  // rect. (The first stage's shimmer and noise streaks are gone: Denis, 11/11.)
  water: `uniform vec4 uBox, uAt, uFoam, uFlowV; uniform vec2 uSpray, uCrest, uRows;
void main(){
  vec2 am = texture2D(uM, vUv).rg; float a = am.r, m = am.g;
  if (a < .003) { gl_FragColor = vec4(0.); return; }
  vec2 u = vU, px = vec2(uBox.x + u.x * (uBox.z - uBox.x), uBox.w - u.y * (uBox.w - uBox.y));
  float hy = uBox.w - uBox.y;
  vec3 c = texture2D(uC, vUv).rgb;
  if (m > .004) {
    float s = arNoise(vec2(px.x / 38., 3.7)), o = arNoise(vec2(px.x / 23., 9.1));
    float v = mix(uFlowV.x, uFlowV.y, smoothstep(uRows.x, uRows.y, px.y)) * (.7 + .6 * s);
    float ph = fract(uTime / uFlowV.z + o), wa = 1. - abs(2. * ph - 1.), d = v * uFlowV.z / hy;
    vec2 sa = uAt.xy + clamp(u + vec2(0., ph * d), 0., 1.) * uAt.zw;
    vec2 sb = uAt.xy + clamp(u + vec2(0., fract(ph + .5) * d), 0., 1.) * uAt.zw;
    float ka = wa * texture2D(uM, sa).g, kb = (1. - wa) * texture2D(uM, sb).g;
    vec3 fl = texture2D(uC, sa).rgb * ka + texture2D(uC, sb).rgb * kb + c * (1. - ka - kb);
    c = mix(c, fl, m * uFlowV.w * smoothstep(uCrest.x, uCrest.y, px.y));
  }
  vec2 f = vec2((px.x - uFoam.x) / (uFoam.y - uFoam.x), (uFoam.w - px.y) / (uFoam.w - uFoam.z));
  if (f.x > 0. && f.x < 1. && f.y > 0. && f.y < 1.) {
    float e = smoothstep(0., .18, f.x) * smoothstep(1., .82, f.x) * smoothstep(1., .45, f.y) * smoothstep(0., .12, f.y);
    float t = mod(uTime * uSpray.y, 64.), sx = (f.x - .5) * (1. + f.y * .6);   // the puffs spread as they rise
    float n = arNoise(vec2(sx * 26., f.y * 7. - t)) * .6 + arNoise(vec2(sx * 61. + 7., f.y * 16. - t * 1.7)) * .4;
    c = mix(c, vec3(.93, .98, 1.) / uContrast, (smoothstep(.4, .85, n) * .8 + .14) * e * uSpray.x);
  }
  gl_FragColor = vec4(arGrade(c), a);
}`};

// Render-only generator (mulberry32 on AR.seed), so the arena is built the same every time.
function arRand() {
  let t = AR.seed = AR.seed + 0x6D2B79F5 | 0;
  t = Math.imul(t ^ t >>> 15, 1 | t); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296;
}

// Loads the planes, builds the arena from def (a CFG.arenas entry) and adds it to the scene. Resolves when the
// textures are decoded.
function arenaBuild(def) {
  AR.def = def; AR.seed = 11; AR.mats = [];
  const g = ARENA.group = new THREE.Group();
  g.name = 'arena';
  const keys = ['atlas.jpg', 'atlas_m.png', 'mist.png', 'floor.jpg', 'props.jpg', 'props_a.png'].map(k => 'arena/cascata_' + k);
  return Promise.all(keys.map(rdTexture)).then(([col, msk, mist, floor, pc, pa]) => {
    for (const t of [col, msk]) {   // seen at about their own size: no mipmaps (cheaper, and WebGL1 has none for them)
      t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
    }
    mist.wrapS = THREE.RepeatWrapping;
    arLayers(def, col, msk, mist);
    arFloor(def, floor);
    for (const t of [pc, pa]) { t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; }
    arProps(def, pc, pa);
    scene.add(g, ARENA.far);
    for (const t of [col, msk, mist, floor, pc, pa]) renderer.initTexture(t);
  });
}

// --- Far planes ---
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

// The rect (x0, y0, x1, y1, metres) at depth z of a painting box (x0, y0, x1, y1 painting px, y down).
function arBoxRect(def, P, b, z) {
  const [iw, ih] = def.ref.img;
  return arPaintToWorld(def, P, b[0] / iw, 1 - b[3] / ih, z).concat(arPaintToWorld(def, P, b[2] / iw, 1 - b[1] / ih, z));
}

// One far mesh at depth z: a quad per entry of quads ({rect: the plane's rect, f: the quad in the plane's uv, uv: in
// the atlas}), with atlas uv and plane uv per vertex.
function arFarMesh(name, quads, z, mat, order) {
  const p = [], uv = [], au = [], idx = [];
  for (const q of quads) {
    const [x0, y0, x1, y1] = q.rect, f = q.f, o = p.length / 3, X = k => x0 + (x1 - x0) * k, Y = k => y0 + (y1 - y0) * k;
    p.push(X(f[0]), Y(f[1]), z, X(f[2]), Y(f[1]), z, X(f[2]), Y(f[3]), z, X(f[0]), Y(f[3]), z);
    uv.push(q.uv[0], q.uv[1], q.uv[2], q.uv[1], q.uv[2], q.uv[3], q.uv[0], q.uv[3]);
    au.push(f[0], f[1], f[2], f[1], f[2], f[3], f[0], f[3]);
    idx.push(o, o + 1, o + 2, o, o + 2, o + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute('aU', new THREE.Float32BufferAttribute(au, 2));
  g.setIndex(idx);
  const mesh = new THREE.Mesh(g, mat);
  mesh.name = name; mesh.renderOrder = order; mesh.frustumCulled = false;
  ARENA.far.add(mesh);
  return mesh;
}

// A far material of kind (AR_FAR_FRAG), with the shared uniforms and its own. core = for the opaque cores (drawn
// first, near to far, writing depth); otherwise blended, far to near, and only where nothing nearer is (depth Less:
// not over its own core either).
function arFarMat(kind, uni, core) {
  const d = AR.def, U = v => ({value: v});
  const m = new THREE.ShaderMaterial({vertexShader: AR_FAR_VERT, fragmentShader: AR_FAR_HEAD + AR_FAR_FRAG[kind],
    transparent: !core, depthWrite: !!core, uniforms: Object.assign({uC: U(AR.tex[0]), uM: U(AR.tex[1]), uMist: U(AR.tex[2]),
      uTime: U(0), uContrast: U(d.contrast), uLift: U(d.lift)}, uni)});
  if (!core) m.depthFunc = THREE.LessDepth;
  AR.mats.push(m);
  return m;
}

// A plane group's quads: its strips, or the opaque cores of its strips.
function arQuads(pls, cores) {
  return pls.flatMap(pl => pl.strips.flatMap(st => cores ? st.cores.map(c => ({rect: pl.rect, f: c.f, uv: c.uv}))
    : [{rect: pl.rect, f: st.f, uv: st.uv}]));
}

function arLayers(def, col, msk, mist) {
  const P = arRefPlace(def), meta = ASSETS['arena/cascata_layers.json'], k = CFG.cam, [iw, ih] = def.ref.img, U = v => ({value: v});
  AR.tex = [col, msk, mist];
  ARENA.far = new THREE.Group(); ARENA.far.name = 'far';
  const planes = meta.planes.map(p => ({name: p.name, z: def.layers[p.name], box: p.box, strips: p.strips,
    rect: arBoxRect(def, P, p.box, def.layers[p.name])}));
  const at = st => new THREE.Vector4(st.uv[0], st.uv[1], st.uv[2] - st.uv[0], st.uv[3] - st.uv[1]);
  // One pair of meshes per depth: the opaque cores (renderOrder after the near scene, nearest first) and the whole
  // strips blended over them (renderOrder = depth: far to near); the sky is opaque, cores only.
  const byZ = new Map();
  for (const pl of planes) { if (!byZ.has(pl.z)) byZ.set(pl.z, []); byZ.get(pl.z).push(pl); }
  const zs = [...byZ.keys()].sort((a, b) => b - a);
  for (const z of zs) {
    const pls = byZ.get(z), name = pls.map(p => p.name).join('+'), rank = 10 + zs.indexOf(z);
    if (name === 'sky') {
      AR.skyK = iw / (pls[0].box[2] - pls[0].box[0]);
      const st = pls[0].strips[0];
      arFarMesh('sky', [{rect: pls[0].rect, f: st.f, uv: st.uv}], z, arFarMat('sky', {uAt: U(at(st)), uSkyOff: U(0)}, true), rank);
      continue;
    }
    const W = def.water, uni = name === 'falls' ? () => ({uBox: U(new THREE.Vector4(...pls[0].box)), uAt: U(at(pls[0].strips[0])),
      uFoam: U(new THREE.Vector4(...W.foam)), uFlowV: U(new THREE.Vector4(W.v[0], W.v[1], W.beat, W.mix)),
      uRows: U(new THREE.Vector2(...W.rows)), uSpray: U(new THREE.Vector2(W.spray, W.sprayRate)), uCrest: U(new THREE.Vector2(...W.crest)),
      }) : () => ({});
    const kind = name === 'falls' ? 'water' : 'plane';
    arFarMesh(name + '.core', arQuads(pls, true), z, arFarMat(kind, uni(), true), rank);
    const edge = arFarMesh(name, arQuads(pls, false), z, arFarMat(kind, uni()), Math.round(z));
    if (name === 'falls') ARENA.waterMat = edge.material;
  }
  // Mist banks: painting rows projected at their depth, wide enough for the widest view there.
  const mc = new THREE.Color().fromArray(meta.mistColor), lift = def.mistLift, mists = [];
  mc.r = Math.min(1, mc.r + lift); mc.g = Math.min(1, mc.g + lift); mc.b = Math.min(1, mc.b + lift);
  for (const m of def.mists) {
    const [, ytop] = arPaintToWorld(def, P, .5, 1 - m.rows[0] / ih, m.z), [, ybot] = arPaintToWorld(def, P, .5, 1 - m.rows[1] / ih, m.z);
    const half = (k.distMax - m.z) * Math.tan(k.fov * Math.PI / 360) * def.view.aspect + k.xMax + 2, rect = [-half, ybot, half, ytop];
    const mat = arFarMat('mist', {uColor: U(mc), uRep: U(Math.max(1, Math.round(2 * half / 30))), uDrift: U(m.drift), uOpacity: U(m.opacity)});
    arFarMesh('mist' + m.z, [{rect, f: [0, 0, 1, 1], uv: [0, 0, 1, 1]}], m.z, mat, Math.round(m.z));
    mists.push({z: m.z, rect});
  }
  planes.sort((a, b) => b.z - a.z);
  ARENA.layers = {planes: planes.map(p => ({name: p.name, z: p.z, rect: p.rect, box: p.box})), mists};
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
function arGeo(M) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(M.p, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(M.n, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(M.uv, 2));
  g.setAttribute('color', new THREE.Float32BufferAttribute(M.c, 3));
  g.setIndex(M.i);
  return g;
}

// --- Floor ---
// The painted floor (tools/make_props.py: the painting's slabs seen from above, so at the start camera it looks
// exactly like the painting and it stays on the floor when the camera moves), one flat mesh at y = 0: the slabs from
// the front (z = terrace.front) to the painting's back edge, and on both sides a ledge going on further back, where
// the column and the lantern stand. Its colours are the painting's own light (no light of its own, no outline).
function arFloor(def, tex) {
  const T = def.terrace, F = ASSETS['arena/cascata_floor.json'], [x0, z1, x1, zb] = F.rect, M = arMesh();
  const U = (x, z) => [(x - x0) / (x1 - x0), 1 - (z - z1) / (zb - z1)];
  const quad = (xa, xb, za, zf, col) => arQuad(M, [xa, 0, zf], [xb, 0, zf], [xb, 0, za], [xa, 0, za], [0, 1, 0],
    [U(xa, zf), U(xb, zf), U(xb, za), U(xa, za)], col);
  quad(-T.half, T.half, F.back, T.front, new THREE.Color(1, 1, 1));
  const moss = new THREE.Color(...T.moss);   // the ledges: the stone gone mossy and dark under the grass
  quad(-T.half, T.ledge[0], T.ledge[2], F.back, moss);
  quad(T.ledge[1], T.half, T.ledge[2], F.back, moss);
  tex.wrapS = tex.wrapT = THREE.MirroredRepeatWrapping;
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const mesh = new THREE.Mesh(arGeo(M), new THREE.MeshBasicMaterial({map: tex, vertexColors: true}));
  mesh.name = 'floor'; ARENA.group.add(mesh);
  AR.back = F.back;
}

// --- Props ---
// The near pieces wear the painting itself (tools/make_props.py cuts them out: cascata_props.jpg, their outlines in
// cascata_props_a.png): each vertex takes the painting's colour where the start camera sees it, so at the start
// camera they look exactly as painted, and when the camera moves they turn as the 3D shapes they are. The outlines
// (alpha) cut the shapes: the broken capital, the lantern's see-through windows, the banner's tears.

// Painting px (X, Y down) of world point (x, y, z), through the start camera on the ref screen (arPaintToWorld's inverse).
function arToPainting(def, P, x, y, z) {
  const k = CFG.cam, t = Math.tan(k.fov * Math.PI / 360), asp = def.ref.w / def.ref.h, L = k.dist0 - z, [iw, ih] = def.ref.img;
  const y0 = k.dist0 * (k.footScreen - .5) * 2 * t;
  const sx = (x / (L * t * asp) + 1) / 2, sy = ((y - y0) / (L * t) + 1) / 2;
  return [(P.px + sx * P.su) * iw, (1 - (P.py + sy * P.sv)) * ih];
}
// Metres per painting px at depth z (at the start camera).
function arPxSize(def, P, z) {
  const k = CFG.cam;
  return 2 * (k.dist0 - z) * Math.tan(k.fov * Math.PI / 360) * def.ref.w / def.ref.h / (def.ref.img[0] * P.su);
}
// The props atlas uv of painting px (X, Y) in prop key's crop (clamped to it).
function arPropUV(key, X, Y) {
  const b = AR.pm[key].box, uv = AR.pm[key].uv;
  const fx = Math.min(1, Math.max(0, (X - b[0]) / (b[2] - b[0]))), fy = Math.min(1, Math.max(0, (Y - b[1]) / (b[3] - b[1])));
  return [uv[0] + fx * (uv[2] - uv[0]), uv[3] - fy * (uv[3] - uv[1])];
}
// geo (any three geometry) appended to M where matrix mx puts it, painted from prop key's crop with the painting's
// colours where the start camera sees it at mPaint (default: where it stands; a copy elsewhere keeps the original's
// paint).
function arPainted(M, geo, mx, key, mPaint) {
  const def = AR.def, p = geo.attributes.position, v = new THREE.Vector3(), w = new THREE.Vector3(), o = M.p.length / 3;
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i); w.copy(v).applyMatrix4(mPaint || mx); v.applyMatrix4(mx);
    const [X, Y] = arToPainting(def, AR.P, w.x, w.y, w.z), uv = arPropUV(key, X, Y);
    M.p.push(v.x, v.y, v.z); M.n.push(0, 1, 0); M.uv.push(uv[0], uv[1]); M.c.push(1, 1, 1);
  }
  if (geo.index) for (let i = 0; i < geo.index.count; i++) M.i.push(o + geo.index.getX(i));
  else for (let i = 0; i < p.count; i++) M.i.push(o + i);
}
// A flat card facing the camera (a tuft of grass or ivy): prop key's picture, w x h metres, its foot at (x, y, z).
function arCard(M, key, x, y, z, w, h, flip) {
  const uv = AR.pm[key].uv, u0 = flip ? uv[2] : uv[0], u1 = flip ? uv[0] : uv[2];
  arQuad(M, [x - w / 2, y, z], [x + w / 2, y, z], [x + w / 2, y + h, z], [x - w / 2, y + h, z], [0, 0, 1],
    [[u0, uv[1]], [u1, uv[1]], [u1, uv[3]], [u0, uv[3]]], new THREE.Color(1, 1, 1));
}
// A tuft card where the painting has it (its crop's box seen at depth z): same size and place as painted.
function arCardAt(M, key, z) {
  const def = AR.def, P = AR.P, b = AR.pm[key].box, s = arPxSize(def, P, z), [iw, ih] = def.ref.img;
  const [x, y] = arPaintToWorld(def, P, (b[0] + b[2]) / 2 / iw, 1 - b[3] / ih, z);
  arCard(M, key, x, y, z, (b[2] - b[0]) * s, (b[3] - b[1]) * s);
}

function arProps(def, pc, pa) {
  AR.P = arRefPlace(def); AR.pm = ASSETS['arena/cascata_props.json'];
  const D = def.props, C = D.column, M = arMesh(), mx = new THREE.Matrix4(), q = new THREE.Quaternion(), E = new THREE.Euler();
  const at = (x, y, z, ry, sx, sy, sz) => mx.compose(new THREE.Vector3(x, y, z), q.setFromEuler(E.set(0, ry || 0, 0)),
    new THREE.Vector3(sx || 1, sy || 1, sz || 1)).clone();
  // The column: a square shaft and its broken capital (the painted outline breaks it), facing the camera.
  arPainted(M, new THREE.BoxGeometry(C.shaft[0], C.shaft[2], C.shaft[1], 2, 12, 2), at(C.x, C.shaft[2] / 2, C.z), 'column');
  arPainted(M, new THREE.BoxGeometry(C.cap[0], C.cap[3] - C.cap[2], C.cap[1], 3, 4, 2), at(C.x + C.cap[4], (C.cap[2] + C.cap[3]) / 2, C.z), 'column');
  // The pole, from the column's face to its knob, slanting towards the camera as painted.
  const pp = AR.pm.pole_ends, [iw, ih] = def.ref.img, P = AR.P;
  const S = new THREE.Vector3(...arPaintToWorld(def, P, pp[0][0] / iw, 1 - pp[0][1] / ih, D.pole[0]), D.pole[0]);
  const Ee = new THREE.Vector3(...arPaintToWorld(def, P, pp[1][0] / iw, 1 - pp[1][1] / ih, D.pole[1]), D.pole[1]);
  const len = S.distanceTo(Ee), rod = new THREE.CylinderGeometry(.045, .045, len, 8, 1);
  mx.lookAt(S, Ee, new THREE.Vector3(0, 1, 0));
  const rot = new THREE.Matrix4().makeRotationX(Math.PI / 2);
  const pm = new THREE.Matrix4().copy(mx).multiply(rot).setPosition(S.clone().add(Ee).multiplyScalar(.5));
  arPainted(M, rod, pm, 'pole');
  arPainted(M, new THREE.SphereGeometry(.065, 10, 8), at(Ee.x, Ee.y, Ee.z), 'pole');
  // The lantern, corner-on as painted: base, platform, firebox, roof, knob.
  const L = D.lantern, Q = Math.PI / 4;
  arPainted(M, new THREE.BoxGeometry(.46, .4, .46), at(L.x, .2, L.z, Q), 'lantern');
  arPainted(M, new THREE.BoxGeometry(.6, .11, .6), at(L.x, .455, L.z, Q), 'lantern');
  arPainted(M, new THREE.BoxGeometry(.4, .3, .4, 2, 2, 2), at(L.x, .66, L.z, Q), 'lantern');
  arPainted(M, new THREE.ConeGeometry(.6, .3, 4, 1), at(L.x, .93, L.z), 'lantern');
  arPainted(M, new THREE.SphereGeometry(.11, 10, 8), at(L.x, 1.15, L.z), 'lantern');
  // The rock at the column's foot, and smaller copies of it (wearing its paint) by the lantern.
  const R = D.rock, rock = new THREE.IcosahedronGeometry(1, 1), mR = at(R[0], R[1], R[2], 0, R[3], R[4], R[5]);
  arPainted(M, rock, mR, 'rock');
  for (const [x, z, s, w] of [[4.55, -2.45, .55, 1.2], [6.2, -2.55, .7, .9], [-6.4, -2.35, .6, 1.1]])   // not turned: the paint faces the camera
    arPainted(M, rock, at(x, R[1] * s, z, 0, R[3] * s * w, R[4] * s, R[5] * s), 'rock', mR);
  // Grass and ivy, painted: the tufts where the painting has them, then many more along both ledges.
  arCardAt(M, 'ivy', C.z + .45);
  arCardAt(M, 'grass_l', R[2] + .05);
  arCardAt(M, 'grass_m', L.z + .3);
  arCardAt(M, 'grass_r', L.z + .3);
  // a hedge of painted grass along both ledges' front edge (two rows), hiding the ledge's edge as the painting does
  const T = def.terrace, back = AR.back, keys = ['grass_l', 'grass_m', 'grass_r'], s0 = arPxSize(def, P, -2.3);
  for (const [a, b] of [[-T.half + .2, T.ledge[0] + .1], [T.ledge[1] - .1, T.half - .2]])
    for (const row of [1, 0]) for (let x = a + arRand() * .3; x < b; x += D.tufts.step[0] + arRand() * D.tufts.step[1]) {
      const key = keys[Math.floor(arRand() * 3)], bx = AR.pm[key].box, k = D.tufts.scale[0] + arRand() * D.tufts.scale[1];
      arCard(M, key, x, 0, back - .04 - row * .3 - arRand() * .12, (bx[2] - bx[0]) * s0 * k, (bx[3] - bx[1]) * s0 * k, arRand() < .5);
    }
  const mat = new THREE.MeshBasicMaterial({map: pc, alphaMap: pa, transparent: true, alphaTest: .04});
  const mesh = new THREE.Mesh(arGeo(M), mat);
  mesh.name = 'props'; ARENA.group.add(mesh);
  AR.props = [0, M.p.length / 3];
  arBanner(def, S, Ee, pc, pa);
}

// The banner: a cols x rows cloth hanging from the pole (top row fixed along it, between where the painted banner
// starts and ends), moved by gravity and a gusty wind from the left (Verlet, fixed 1/60 s steps, iters constraint
// passes); it wears the painted banner, unrolled onto the cloth (its folds and tears). Graphics only.
function arBanner(def, S, E, pc, pa) {
  const B = def.banner, n = B.cols * B.rows, pm = AR.pm, ed = pm.banner_edges, pp = pm.pole_ends;
  const along = X => (X - pp[0][0]) / (pp[1][0] - pp[0][0]);
  const A = S.clone().lerp(E, along(ed.left[0][0])), Bp = S.clone().lerp(E, along(ed.right[0][0]));
  const dy = B.h / (B.rows - 1), pos = new Float32Array(n * 3), cur = new THREE.Vector3();
  for (let r = 0; r < B.rows; r++) for (let c = 0; c < B.cols; c++) {
    cur.copy(A).lerp(Bp, c / (B.cols - 1)); pos.set([cur.x, cur.y - r * dy, cur.z], (r * B.cols + c) * 3);
  }
  const C = def.props.column;
  AR.cloth = {pos, prev: pos.slice(), rest: pos.slice(0, B.cols * 3), dx: A.distanceTo(Bp) / (B.cols - 1), dy, t: 0,
    xMin: C.x + C.shaft[0] / 2 + .04};
  // uv: row r at fraction r/(rows-1) down both painted edges (by length), column c between them
  const walk = (pl, f) => {
    const seg = []; let tot = 0;
    for (let i = 1; i < pl.length; i++) { const l = Math.hypot(pl[i][0] - pl[i - 1][0], pl[i][1] - pl[i - 1][1]); seg.push(l); tot += l; }
    let d = f * tot;
    for (let i = 0; i < seg.length; i++) {
      if (d <= seg[i] || i === seg.length - 1) { const k = Math.min(1, d / seg[i]); return [pl[i][0] + (pl[i + 1][0] - pl[i][0]) * k, pl[i][1] + (pl[i + 1][1] - pl[i][1]) * k]; }
      d -= seg[i];
    }
  };
  const geo = new THREE.PlaneGeometry(1, 1, B.cols - 1, B.rows - 1), uv = geo.attributes.uv;
  for (let r = 0; r < B.rows; r++) {
    const l = walk(ed.left, r / (B.rows - 1)), rr = walk(ed.right, r / (B.rows - 1));
    for (let c = 0; c < B.cols; c++) {
      const k = c / (B.cols - 1), t = arPropUV('banner', l[0] + (rr[0] - l[0]) * k, l[1] + (rr[1] - l[1]) * k);
      uv.setXY(r * B.cols + c, t[0], t[1]);
    }
  }
  geo.attributes.position.array.set(pos);
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({map: pc, alphaMap: pa, transparent: true, alphaTest: .04,
    side: THREE.DoubleSide}));
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
  const d = AR.def, t = nowMs / 1000;
  ARENA.far.position.x = d.sway.amp * Math.sin(t * 6.2831853 / d.sway.period);   // nearer planes slide further on screen
  for (const m of AR.mats) {
    m.uniforms.uTime.value = t;
    if (m.uniforms.uSkyOff) m.uniforms.uSkyOff.value = d.skyDrift * AR.skyK * Math.sin(t * 6.2831853 / d.skyPeriod);
  }
  if (!AR.cloth) return;
  if (AR.last < 0 || nowMs < AR.last || nowMs - AR.last > 1000) AR.last = nowMs;   // first frame, a reset or a long pause
  let n = Math.floor((nowMs - AR.last) * .06);
  if (n > 0) { AR.last += n / .06; n = Math.min(4, n); for (let i = 0; i < n; i++) arClothStep(d); arClothSync(); }
}

// Draw calls and triangles of the arena group as it is (visible meshes; instanced meshes count once).
function arStats() {
  let draws = 0, tris = 0;
  for (const grp of [ARENA.group, ARENA.far]) grp.traverse(o => {
    if (!o.isMesh || !o.visible) return;
    const g = o.geometry, n = g.index ? g.index.count : g.attributes.position.count;
    draws++; tris += n / 3 * (o.isInstancedMesh ? o.count : 1);
  });
  return {draws, tris};
}
