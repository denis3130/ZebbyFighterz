// The 3D arena (d_arena.js): no holes in any game view, real depth, feet on the slabs, flowing water, the banner, cost.
// Run at 640x360, 844x390, 1280x720 and 960x720 (see docs/HANDOFF.md).
const AD = () => __VF.CFG.arenas[__VF.CFG.arenaOn];
// Reads the pixel at u, v (0..1, v from the top) of what was just drawn (same JS turn).
function readAt(u, v) {
  const gl = __VF.renderer.getContext(), w = gl.drawingBufferWidth, h = gl.drawingBufferHeight, p = new Uint8Array(4);
  gl.readPixels(Math.min(w - 1, Math.floor(u * w)), h - 1 - Math.min(h - 1, Math.floor(v * h)), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p);
  return [p[0], p[1], p[2], p[3]];
}
// Puts the fighters at x0, x1 (mm) with fighter 0 at height y0, and lets the camera settle (fighters hidden).
function view(x0, x1, y0) {
  const V = __VF, S = V.G.S;
  V.fighterOf(S, 0).x = x0; V.fighterOf(S, 1).x = x1; V.fighterOf(S, 0).y = y0;
  for (let i = 0; i < 90; i++) V.renderFrame(S, 2000 + i * 16);
}
const VIEWS = {start: [-1200, 1200, 0], far: [-2750, 2750, 0], left: [-6000, -2000, 0], right: [2000, 6000, 0], jump: [-600, 600, 2314]};
const EDGE = [[0, 0], [.5, 0], [1, 0], [0, .5], [1, .5], [0, 1], [.5, 1], [1, 1], [.5, .5], [.25, .02], [.75, .02], [.02, .75], [.98, .75]];

T.test('no holes at the camera extremes', () => {
  const V = __VF; V.startMatch('versus', {seed: 1}); V.F3D.forEach(f => f.root.visible = false);
  V.renderer.setClearColor(0xff00ff, 1);
  try {
    for (const k in VIEWS) {
      view(...VIEWS[k]);
      for (const [sx, sy] of [[0, 0], [.15, .15], [-.15, -.15], [.15, -.15], [-.15, .15]]) {
        V.camera.position.x = V.cam.x + sx; V.camera.position.y = V.cam.y + sy; V.camera.updateMatrixWorld();
        V.renderer.clear(); V.renderer.render(V.scene, V.camera);
        for (const [u, v] of EDGE) { const p = readAt(u, v); T.ok(!(p[0] > 240 && p[1] < 20 && p[2] > 240), k + ' shake ' + sx + ',' + sy + ' hole at ' + u + ',' + v); }
      }
    }
  } finally { V.renderer.setClearColor(0x000000, 1); V.F3D.forEach(f => f.root.visible = true); view(-1200, 1200, 0); }
});

T.test('depth: near moves more than far', () => {
  const V = __VF, d = AD(), pl = V.ARENA.layers.planes;
  T.eq(pl.map(p => p.name).join(), 'LF,FL,FR,UL,UR,falls,far,haze,sky', 'planes nearest first');
  for (const p of pl) T.eq(p.z, d.layers[p.name], p.name + ' depth');
  view(-1200, 1200, 0);
  const pts = [[d.props.column.x, 2, d.props.column.z], [0, 5, d.layers.LF], [0, 5, d.layers.UL], [0, 5, d.layers.falls], [0, 5, d.layers.haze], [0, 10, d.layers.sky]], at = () => pts.map(p => V.toScreen(...p).x);
  const a = at(); V.camera.position.x += 1; V.camera.updateMatrixWorld(); const b = at(); view(-1200, 1200, 0);
  const m = a.map((x, i) => Math.abs(b[i] - x));
  T.ok(m.every((x, i) => i === 0 || (x < m[i - 1] && x > 0)), 'screen shift column > forest > high cliffs > falls > haze > sky: ' + m.map(x => x.toFixed(1)));
});

T.test('water flows, stone does not', () => {
  const V = __VF, d = AD(), P = V.arRefPlace(d); V.ARENA.leaves.visible = false; V.F3D.forEach(f => f.root.visible = false);
  try {
    view(-1200, 1200, 0);
    const w = V.arPaintToWorld(d, P, 900 / 1672, 1 - 420 / 941, d.layers.falls), ws = V.toScreen(w[0], w[1], d.layers.falls);
    const st = V.toScreen(V.cam.x + .8, 0, 1.2), u = [ws.x / innerWidth, ws.y / innerHeight], su = [st.x / innerWidth, st.y / innerHeight];
    T.ok(u[0] > 0 && u[0] < 1 && u[1] > 0 && u[1] < 1, 'waterfall on screen');
    V.renderFrame(V.G.S, 3000); const a = readAt(...u), s = readAt(...su);
    V.renderFrame(V.G.S, 3500); const b = readAt(...u), s2 = readAt(...su);
    T.ok(diff(a, b) > 6, 'water still: ' + a + ' / ' + b); T.ok(diff(s, s2) <= 2, 'stone moved: ' + s + ' / ' + s2);
  } finally { V.ARENA.leaves.visible = true; V.F3D.forEach(f => f.root.visible = true); }
});

T.test('the floor is at y=0 under every fighter x', () => {
  const V = __VF, rc = new THREE.Raycaster(), floor = V.ARENA.group.getObjectByName('floor'), down = new THREE.Vector3(0, -1, 0);
  for (const z of [-.05, 0, .05]) for (let x = -6; x <= 6.001; x += .25) {
    rc.set(new THREE.Vector3(x, 1, z), down); const h = rc.intersectObject(floor)[0];
    T.ok(h && Math.abs(h.point.y) < .001, 'no floor under x ' + x + ': ' + (h && h.point.y));
  }
});

T.test('ground stays at 86%', () => { view(-1200, 1200, 0); const g = __VF.toScreen(__VF.cam.x, 0, 0).y; T.near(g / innerHeight, .86, .02); });

T.test('banner moves', () => {
  const V = __VF, B = AD().banner, p = V.AR.cloth.pos, i = (B.rows * B.cols - 2) * 3, a = [p[i], p[i + 1], p[i + 2]];
  for (let k = 1; k <= 60; k++) V.arenaStep(10000 + k * 16.7, V.G.S);
  T.ok(Math.hypot(p[i] - a[0], p[i + 1] - a[1], p[i + 2] - a[2]) > .02, 'the banner tip stayed put');
});

T.test('banner stays finite after 10 minutes', () => {
  const V = __VF, d = AD(), p = V.AR.cloth.pos, x0 = V.AR.cloth.rest[0], y0 = V.AR.cloth.rest[1];
  for (let k = 0; k < 36000; k++) V.arClothStep(d);
  for (let i = 0; i < p.length; i += 3) {
    T.ok(isFinite(p[i]) && isFinite(p[i + 1]) && isFinite(p[i + 2]), 'not finite at ' + i);
    T.ok(Math.hypot(p[i] - x0, p[i + 1] - y0) < 3, 'too far from the pole at ' + i);
  }
});

T.test('banner step under 0.2 ms', () => {
  const V = __VF, d = AD(), t = performance.now();
  for (let k = 0; k < 600; k++) V.arClothStep(d);
  const ms = (performance.now() - t) / 600; T.info('banner step ' + ms.toFixed(4) + ' ms'); T.ok(ms < .2, ms + ' ms');
});

T.test("props stay out of the fighters' lane", () => {
  const V = __VF, p = V.ARENA.group.getObjectByName('props').geometry.attributes.position;
  let zMax = -99;   // column, pole, lantern, rocks, tufts: the props mesh
  for (let i = V.AR.props[0]; i < V.AR.props[1]; i++) zMax = Math.max(zMax, p.getZ(i));
  T.ok(zMax < -1.5, 'props reach z ' + zMax.toFixed(2));
  const b = new THREE.Box3().setFromObject(V.ARENA.group.getObjectByName('banner'));
  T.ok(b.max.z < -1.5, 'banner reaches z ' + b.max.z.toFixed(2));
});

T.test('arena within 25 draws and 25000 triangles', () => {
  const s = __VF.ARENA.stats(); T.info('arena ' + s.draws + ' draws, ' + Math.round(s.tris) + ' triangles');
  T.ok(s.draws <= 25, s.draws + ' draws'); T.ok(s.tris <= 25000, s.tris + ' triangles');
});

T.test('far planes without mipmaps (none on WebGL1 for them, and not needed)', () => {
  const u = __VF.ARENA.waterMat.uniforms;
  for (const k of ['uC', 'uM']) { const t = u[k].value; T.eq(t.generateMipmaps, false, k); T.eq(t.minFilter, THREE.LinearFilter, k); }
});

T.test('render does not change the sim', () => { const h = __VF.simHash(__VF.G.S); __VF.renderFrame(__VF.G.S, 0); __VF.arenaStep(5000, __VF.G.S); T.eq(__VF.simHash(__VF.G.S), h); });

T.test('resize keeps the ground at 86%', () => {
  setViewport(740, 360); window.dispatchEvent(new Event('resize')); view(-1200, 1200, 0);
  T.near(__VF.toScreen(__VF.cam.x, 0, 0).y / innerHeight, .86, .02);
});
