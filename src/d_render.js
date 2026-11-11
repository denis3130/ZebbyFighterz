// Renderer: the WebGL canvas, the side camera, the 3D arena (d_arena.js), drifting leaves, the fighters
// (e_fighter3d.js), their blob shadows and toScreen. Graphics only: it reads the sim state and never writes it.
// The 3D world is in metres: x = F.x/1000, y = F.y/1000, z = 0 (side 0 at +0.05, side 1 at -0.05); the camera looks
// along -z without pitch; the arena's far layers reach z = -70, hence the far plane.

const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('game'), antialias: false});
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(CFG.cam.fov, 1, .1, 200);
const cam = {x: 0, y: 0, dist: CFG.cam.dist0};   // the camera as computed, in metres (y follows from dist)
// Private state: W, H = screen in CSS px, v = scratch vector, shadows = one disc per side.
const RD = {W: 1, H: 1, v: new THREE.Vector3(), shadows: [], seed: 7};
// Cosmetic values (not balance). Shadow disc: w x d metres, scaled by max(min, 1 - height/fade) (height in metres).
// Leaves: z and the height range of the front/back half; ranges are [min, spread] (metres, m/s, rad/s); amp = bob
// height, bob/turn = rates of the bob and of the turning (the narrowing); swing = [amplitude rad, rate as a share of
// the bob rate] of the rotation; margin = metres beyond the widest view where a leaf wraps round.
const RD_SHADOW = {w: 1.1, d: .7, fade: 2.5, min: .3};
const RD_LEAF = {z: [1.5, -2], y: [[.35, 2.3], [.6, 3]], size: [.13, .08], speed: [.45, .6], amp: [.12, .22],
  bob: [1, 1.2], turn: [1.5, 2], swing: [.7, .8], margin: .5};

// A texture from an embedded image (an ASSETS data URI), once the image is decoded.
function rdTexture(key) {
  const img = new Image();
  img.src = ASSETS[key];
  return img.decode().then(() => { const t = new THREE.Texture(img); t.needsUpdate = true; return t; },
    () => { throw new Error('cannot decode asset ' + key); });
}

// A small canvas texture drawn by draw(ctx, size).
function rdCanvasTexture(size, draw) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  draw(c.getContext('2d'), size);
  return new THREE.CanvasTexture(c);
}

// Render-only generator (mulberry32 on RD.seed), so a frame drawn at a given time is always the same.
function rdRand() {
  let t = RD.seed = RD.seed + 0x6D2B79F5 | 0;
  t = Math.imul(t ^ t >>> 15, 1 | t); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296;
}
function rdIn(r) { return r[0] + rdRand() * r[1]; }   // in the range [min, spread]

// Builds the arena (its textures decoded and uploaded, so the first frame does not stall), the leaves, the shadows,
// the fighters and the effects.
function renderInit() {
  renderer.autoClear = false;
  return arenaBuild(CFG.arenas[CFG.arenaOn]).then(() => {
    rdLeavesBuild(); rdShadowsBuild(); rdFightersBuild(); fxBuild();
    renderer.compile(scene, camera);   // the shaders now, not on the first frame of a fight
    window.addEventListener('resize', renderResize);
    renderResize();
  });
}

// Screen size, pixel ratio (at most 2) and the 3D camera's aspect.
function renderResize() {
  RD.W = Math.max(1, innerWidth); RD.H = Math.max(1, innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(RD.W, RD.H);
  camera.aspect = RD.W / RD.H; camera.updateProjectionMatrix();
  rdCamApply();
}

// Draws S (null = no match: the empty arena) at nowMs: camera, arena, leaves, shadows, fighters, effects, one scene.
// A shake (fxShakeApply) moves the camera for this draw only: the arena is in the same scene, so the whole picture
// trembles together; afterwards cam and toScreen are as computed.
function renderFrame(S, nowMs) {
  rdCamStep(S); arenaStep(nowMs, S); rdLeavesStep(nowMs); rdShadowsStep(S); f3Sync(S);
  fxUpdate(nowMs, S);
  renderer.clear();
  const shaken = fxShakeApply();
  renderer.render(scene, camera);
  if (shaken) rdCamApply();
}

// World point (metres) -> screen px {x, y} from the top left, through the camera as last placed.
function toScreen(xm, ym, zm) {
  const v = RD.v.set(xm, ym, zm).project(camera);
  return {x: (v.x + 1) / 2 * RD.W, y: (1 - v.y) / 2 * RD.H};
}

// --- Camera ---
// Target x = the fighters' midpoint (within ±xMax); target dist = the largest of dist0, the distance that fits both
// fighters with marginX each side (for this screen's aspect) and the one that fits the highest head (feet + body.h)
// with marginTop, at most distMax. cam closes `smooth` of the gap per drawn frame.
function rdCamStep(S) {
  const k = CFG.cam, t = Math.tan(k.fov * Math.PI / 360);
  let x = 0, d = k.dist0;
  if (S) {
    const a = fighterOf(S, 0), b = fighterOf(S, 1);
    x = Math.max(-k.xMax, Math.min(k.xMax, (a.x + b.x) / 2000));
    const half = Math.max(Math.abs(a.x / 1000 - x), Math.abs(b.x / 1000 - x)) + k.marginX;
    const top = (Math.max(a.y, b.y) + CFG.body.h) / 1000 + k.marginTop;
    d = Math.min(k.distMax, Math.max(d, half / (t * camera.aspect), top / (2 * k.footScreen * t)));
  }
  cam.x += (x - cam.x) * k.smooth; cam.dist += (d - cam.dist) * k.smooth;
  rdCamApply();
}

// cam.y keeps the ground (y = 0 under the camera) at footScreen of the screen height, at any distance.
function rdCamApply() {
  const k = CFG.cam;
  cam.y = cam.dist * (k.footScreen - .5) * 2 * Math.tan(k.fov * Math.PI / 360);
  camera.position.set(cam.x, cam.y, cam.dist);
  camera.updateMatrixWorld();
}

// --- Leaves ---
// arena.leaves sprites, half in front of the fighters and half behind, each with its own size, speed and flutter
// (and its own material: a sprite's rotation lives on its material).
function rdLeavesBuild() {
  const L = RD_LEAF, tex = rdCanvasTexture(64, (g, n) => {
    const gr = g.createLinearGradient(0, n * .3, 0, n * .7);
    gr.addColorStop(0, '#eef27c'); gr.addColorStop(1, '#93be3a');
    g.fillStyle = gr; g.beginPath(); g.moveTo(n * .06, n / 2);
    g.quadraticCurveTo(n * .4, n * .14, n * .94, n / 2); g.quadraticCurveTo(n * .4, n * .86, n * .06, n / 2); g.fill();
    g.strokeStyle = 'rgba(92,124,34,.8)'; g.lineWidth = n / 32;
    g.beginPath(); g.moveTo(n * .1, n / 2); g.lineTo(n * .86, n / 2); g.stroke();
  });
  for (let i = 0; i < CFG.arenas[CFG.arenaOn].leaves; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: tex, transparent: true, depthWrite: false})), k = i % 2;
    sp.userData = {z: L.z[k], y0: rdIn(L.y[k]), x0: rdRand() * 100, v: rdIn(L.speed), amp: rdIn(L.amp), bob: rdIn(L.bob),
      turn: rdIn(L.turn), rot: rdRand() * 6.283, ph: rdRand() * 6.283, size: rdIn(L.size)};
    ARENA.leaves.add(sp);
  }
  scene.add(ARENA.leaves);
}

// Each leaf drifts left to right through a window around the camera that is wider than the view even at distMax, so
// it wraps round off screen; it bobs, swings and turns (the narrowing) as it goes. A function of nowMs only.
function rdLeavesStep(nowMs) {
  const t = nowMs / 1000, tn = Math.tan(CFG.cam.fov * Math.PI / 360), ch = ARENA.leaves.children, R = RD_LEAF;
  for (let i = 0; i < ch.length; i++) {
    const sp = ch[i], L = sp.userData;
    const span = 2 * ((CFG.cam.distMax - L.z) * tn * camera.aspect + R.margin), left = cam.x - span / 2;
    sp.position.set(left + ((L.x0 + L.v * t - left) % span + span) % span, L.y0 + L.amp * Math.sin(L.bob * t + L.ph), L.z);
    sp.scale.set(L.size, L.size * (.2 + .8 * Math.abs(Math.cos(L.turn * t + L.ph))), 1);
    sp.material.rotation = L.rot + R.swing[0] * Math.sin(R.swing[1] * L.bob * t + L.ph);
  }
}

// --- Shadows ---
// A black radial disc (45% at the centre) flat on the ground under each fighter; it shrinks as the fighter rises.
function rdShadowsBuild() {
  const tex = rdCanvasTexture(64, (g, n) => {
    const gr = g.createRadialGradient(n / 2, n / 2, 0, n / 2, n / 2, n / 2);
    gr.addColorStop(0, 'rgba(0,0,0,.45)'); gr.addColorStop(.6, 'rgba(0,0,0,.36)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, n, n);
  });
  const geo = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  const mat = new THREE.MeshBasicMaterial({map: tex, transparent: true, depthWrite: false});
  for (let i = 0; i < 2; i++) { const m = new THREE.Mesh(geo, mat); m.visible = false; RD.shadows.push(m); scene.add(m); }
}

function rdShadowsStep(S) {
  for (let i = 0; i < 2; i++) {
    const m = RD.shadows[i];
    m.visible = !!S;
    if (!S) continue;
    const F = fighterOf(S, i), k = Math.max(RD_SHADOW.min, 1 - F.y / 1000 / RD_SHADOW.fade);
    m.position.set(F.x / 1000, .005, i ? -.05 : .05);
    m.scale.set(RD_SHADOW.w * k, 1, RD_SHADOW.d * k);
  }
}

// --- Fighters ---
// The two fighters (side 0 Ren, side 1 Kael; F3D): a Meshy model when its package is in ASSETS (e_model.js), else
// the placeholder; and the light they are shaded by.
function rdFightersBuild() {
  scene.add(...f3Lights());
  for (const c of ['ren', 'kael']) { const it = modelBuild(c) || fighterBuild(c); F3D.push(it); scene.add(it.root); }
}
