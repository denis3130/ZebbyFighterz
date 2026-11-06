// Renderer: the WebGL canvas, the side camera, the painted backdrop with the flowing waterfall, drifting leaves, the
// fighters' blob shadows and toScreen. Graphics only: it reads the sim state and never writes it.
// The 3D world is in metres: x = F.x/1000, y = F.y/1000, z = 0 (side 0 at +0.05, side 1 at -0.05); the camera looks
// along -z without pitch. The backdrop is a full-screen quad drawn first, with its own camera, so the 3D scene
// (fighters, leaves, shadows) draws over it.

const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('game'), antialias: false});
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(CFG.cam.fov, 1, .1, 60);
const cam = {x: 0, y: 0, dist: CFG.cam.dist0};   // the camera as computed, in metres (y follows from dist)
// mat = the backdrop's ShaderMaterial, leaves = the leaves' Group, footRowY() = screen y (px) of the image's foot row.
const ARENA = {mat: null, leaves: new THREE.Group(), footRowY: rdFootRowY};
// Private state: the backdrop's scene and camera (a fixed clip-space square: nothing to update on resize),
// W, H = screen in CSS px, imgW, imgH = backdrop image in px, v = scratch vector, shadows = one disc per side.
const RD = {bgScene: new THREE.Scene(), bgCam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1), W: 1, H: 1,
  imgW: 1, imgH: 1, v: new THREE.Vector3(), shadows: [], seed: 7};
// Cosmetic values (not balance). Shadow disc: w x d metres, scaled by max(min, 1 - height/fade) (height in metres).
// Leaves: z and the height range of the front/back half; ranges are [min, spread] (metres, m/s, rad/s); amp = bob
// height, bob/turn = rates of the bob and of the turning (the narrowing); swing = [amplitude rad, rate as a share of
// the bob rate] of the rotation; margin = metres beyond the widest view where a leaf wraps round.
const RD_SHADOW = {w: 1.1, d: .7, fade: 2.5, min: .3};
const RD_LEAF = {z: [1.5, -2], y: [[.35, 2.3], [.6, 3]], size: [.13, .08], speed: [.45, .6], amp: [.12, .22],
  bob: [1, 1.2], turn: [1.5, 2], swing: [.7, .8], margin: .5};

// The backdrop quad covers the clip square; uPlace maps its screen uv (0..1, y up) to image uv: xy + vS * zw.
const RD_BG_VERT = 'varying vec2 vS;\nvoid main(){ vS = uv; gl_Position = vec4(position.xy, 0., 1.); }';
// Colour grade (contrast/lift); on the waterfall (mask m) the image shimmers (wobble) and stretched value noise
// scrolls down as streaks. The noise runs only where m > 0, so the rest of the backdrop costs two texture reads.
// The hash is Inigo Quilez's sin-free one; the noise repeats every 64 cells in y, so its scroll wraps without a seam
// and the hash input stays small (precise in long sessions).
const RD_BG_FRAG = `
uniform sampler2D uMap, uMask;
uniform vec4 uPlace;
uniform float uTime, uContrast, uLift, uFlow, uStreak, uWobble;
varying vec2 vS;
float rdHash(vec2 p){ p = 50. * fract(p * .3183099 + vec2(.71, .113)); return fract(p.x * p.y * (p.x + p.y)); }
float rdNoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  float y0 = mod(i.y, 64.), y1 = mod(i.y + 1., 64.);
  return mix(mix(rdHash(vec2(i.x, y0)), rdHash(vec2(i.x + 1., y0)), f.x),
             mix(rdHash(vec2(i.x, y1)), rdHash(vec2(i.x + 1., y1)), f.x), f.y);
}
void main(){
  vec2 uv = uPlace.xy + vS * uPlace.zw;
  float m = texture2D(uMask, uv).r;
  vec2 w = uv + vec2(0., sin(uv.x * 90. + mod(uTime * 3., 6.2831853)) * uWobble * m);
  vec3 c = (texture2D(uMap, w).rgb - .5) * uContrast + .5 + uLift;
  if (m > .004) c += m * (rdNoise(vec2(uv.x * 140., uv.y * 6. + mod(uTime * uFlow * 6., 64.))) - .5) * uStreak;
  gl_FragColor = vec4(c, 1.);
}`;

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

// Loads the backdrop and its water mask, then builds the backdrop, the leaves and the shadows. Resolves once the
// textures are decoded and uploaded, so the first frame does not stall.
function renderInit() {
  renderer.autoClear = false;
  return Promise.all([rdTexture('arena/cascata.jpg'), rdTexture('arena/cascata_mask.png')]).then(([map, mask]) => {
    const a = CFG.arena, gl2 = renderer.capabilities.isWebGL2;
    map.generateMipmaps = gl2;   // WebGL1 has no mipmaps for this non-power-of-two image (three would shrink it)
    map.minFilter = gl2 ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
    mask.generateMipmaps = false; mask.minFilter = THREE.LinearFilter;
    RD.imgW = map.image.width; RD.imgH = map.image.height;
    ARENA.mat = new THREE.ShaderMaterial({vertexShader: RD_BG_VERT, fragmentShader: RD_BG_FRAG, depthTest: false,
      depthWrite: false, uniforms: {uMap: {value: map}, uMask: {value: mask}, uPlace: {value: new THREE.Vector4()},
        uTime: {value: 0}, uContrast: {value: a.contrast}, uLift: {value: a.lift}, uFlow: {value: a.flow},
        uStreak: {value: a.streak}, uWobble: {value: a.wobble}}});
    const bg = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), ARENA.mat);
    bg.frustumCulled = false; RD.bgScene.add(bg);
    rdLeavesBuild(); rdShadowsBuild();
    renderer.initTexture(map); renderer.initTexture(mask);
    window.addEventListener('resize', renderResize);
    renderResize();
  });
}

// Screen size, pixel ratio (at most 2), the 3D camera's aspect and the backdrop placement.
function renderResize() {
  RD.W = Math.max(1, innerWidth); RD.H = Math.max(1, innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(RD.W, RD.H);
  camera.aspect = RD.W / RD.H; camera.updateProjectionMatrix();
  rdCamApply(); rdPlace();
}

// Draws S (null = no match: the empty arena) at nowMs: camera, backdrop, leaves, shadows, then the 3D scene.
function renderFrame(S, nowMs) {
  ARENA.mat.uniforms.uTime.value = nowMs / 1000;
  rdCamStep(S); rdPlace(); rdLeavesStep(nowMs); rdShadowsStep(S);
  renderer.clear();
  renderer.render(RD.bgScene, RD.bgCam);
  renderer.render(scene, camera);
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

// --- Backdrop ---
// Scale (screen px per image px) = the smallest cover of the screen x cover x (dist0/dist)^zoomPar, and never less
// than what still covers the screen; the image's footRow sits at the screen y of the ground under the camera (the
// zoom is centred there); parallax shifts the image by -cam.x * parX image widths.
function rdPlace() {
  const a = CFG.arena, W = RD.W, H = RD.H, iw = RD.imgW, ih = RD.imgH;
  RD.v.set(cam.x, 0, 0).project(camera);
  const gy = (1 - RD.v.y) / 2 * H, par = cam.x * a.parX;
  const s = Math.max(Math.max(W / iw, H / ih) * a.cover * Math.pow(CFG.cam.dist0 / cam.dist, a.zoomPar),
    W / (iw * (1 - 2 * Math.abs(par))), gy / (a.footRow * ih), (H - gy) / ((1 - a.footRow) * ih));
  const su = W / (iw * s), sv = H / (ih * s);   // image uv per screen uv
  ARENA.mat.uniforms.uPlace.value.set(.5 + par - su / 2, 1 - a.footRow - (H - gy) / (ih * s), su, sv);
}

// The screen y (px from the top) where the placed backdrop shows its foot row: the shader's mapping, inverted.
function rdFootRowY() {
  const p = ARENA.mat.uniforms.uPlace.value;
  return RD.H * (1 - (1 - CFG.arena.footRow - p.y) / p.w);
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
  for (let i = 0; i < CFG.arena.leaves; i++) {
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
