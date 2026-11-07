// Character viewer ("Anteprima 3D", 7/11/2026): one Meshy fighter alone on a stage, turned by drag, pinch and wheel,
// playing the game's own animation: a stand-alone fighter state stepped 60 times a second and drawn by mdSync, so what
// shows here is exactly what the game draws for that act and frame. A separate page (viewer.html, built by mk.sh).

const VW = {it: null, F: null, S: null, renderer: null, scene: null, camera: null, shadow: null, plan: [], step: 0, left: 0,
  name: '', speed: 1, acc: 0, last: null, yaw: .55, zoom: 1, fit: 5.4, spin: true, idleMs: 0, pointers: new Map(), pinch: 0, tex: {}, mats: {}};
const VW_DT = 1000 / 60, VW_YAW = .55, VW_TALL = 2.15, VW_WIDE = 2.1;   // metres that fit above the controls, and across
// What each button plays: a list of steps [act, frames, mode]; a move id alone takes its frame data from CFG.moves.
// Modes: 'jump' (take-off at the jump speed, falls with gravity until the floor), 'jumpAtk' (the same, the air kick
// starting 8 frames in), 'fly' (knocked up, flies until the floor), 'walkF'/'walkB'/'dash' (walks the fighter state).
const VW_PLAYS = [
  ['Guardia', [['idle', 150], ['guard', 60], ['crouch', 60], ['guardC', 60]]],
  ['Cammina', [['walkF', 110, 'walkF'], ['walkB', 110, 'walkB'], ['dashF', CFG.dash.f.n, 'dash'], ['dashB', CFG.dash.b.n, 'dash']]],
  ['Pugni', ['p1', 'p2', 'p3', 'hp']],
  ['Calci', ['k1', 'k2', 'hk']],
  ['In basso', ['cp', 'ck', 'chp', 'chk']],
  ['Salto', [['jumpSquat', CFG.jump.squat], ['air', 0, 'jump'], ['landing', CFG.jump.land + 6], ['jumpSquat', CFG.jump.squat], ['jk', 0, 'jumpAtk'], ['landing', CFG.jump.landAtk + 6]]],
  ['Speciale', ['spec']],
  ['Presa', [['thr', CFG.thr.s + CFG.thr.a], ['thrHit', CFG.thr.anim]]],
  ['Colpito', [['hitStun', 24], ['block', 16]]],
  ['A terra', [['knock', 0, 'fly'], ['knock', CFG.knock.ground], ['getup', CFG.knock.getup]]],
];
const VW_NAMES = {idle: 'Guardia', guard: 'Parata', crouch: 'Accovacciato', guardC: 'Parata bassa', walkF: 'Cammina avanti',
  walkB: 'Cammina indietro', dashF: 'Scatto avanti', dashB: 'Scatto indietro', p1: 'Pugno 1', p2: 'Pugno 2', p3: 'Pugno 3',
  hp: 'Pugno forte', k1: 'Calcio 1', k2: 'Calcio 2', hk: 'Calcio forte', cp: 'Pugno basso', ck: 'Calcio basso',
  chp: 'Montante', chk: 'Calcio lanciante', jumpSquat: 'Salto', air: 'In volo', landing: 'Atterraggio', jk: 'Calcio in volo',
  spec: 'Colpo energetico', thr: 'Presa', thrHit: 'Lancio', hitStun: 'Colpito', block: 'Para il colpo', knock: 'A terra',
  getup: 'Si rialza'};

function vwBoot() {
  const it = modelBuild('ren');
  if (!it) { document.getElementById('now').textContent = 'Il modello di Ren non è nel pacchetto.'; return; }
  const cv = document.getElementById('view');
  VW.renderer = new THREE.WebGLRenderer({canvas: cv, antialias: true, alpha: true, preserveDrawingBuffer: true});
  VW.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  VW.scene = new THREE.Scene(); VW.camera = new THREE.PerspectiveCamera(30, 1, .1, 50);
  VW.scene.add(...f3Lights(), it.root, vwShadow());
  VW.it = it; VW.F = {side: 0, char: 'ren', x: 0, y: 0, vx: 0, vy: 0, face: 1, act: 'idle', af: 0, air: false, hit: 0, stun: 0, prev: 0, land: CFG.jump.land, hold: [0, 0]};
  VW.S = {frame: 0, sides: [{team: [VW.F], cur: 0}]};
  // the two paints: the drawing projected on the model (tools/paint_from_drawing.py) and Meshy's own
  VW.tex.meshy = it.mats.main.map;
  const img = new Image(), t = new THREE.Texture(img); t.flipY = false;
  img.src = ASSETS['ren/ren_painted.jpg'] || ASSETS['ren/ren.jpg']; img.decode().then(() => { t.needsUpdate = true; }, () => {});
  VW.tex.draw = t;
  VW.mats.toon = it.mats.main; VW.mats.flat = new THREE.MeshBasicMaterial({map: t, skinning: true});
  document.getElementById('stage').style.backgroundImage = 'url(' + ASSETS['arena/cascata.jpg'] + ')';
  vwUi(); vwInput(); vwResize(); addEventListener('resize', vwResize);
  vwPlay(0); vwPaint('draw'); vwLight('toon'); vwSpeed(1);
  requestAnimationFrame(vwLoop);
}

// A soft round shadow under the feet.
function vwShadow() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, 'rgba(0,0,0,.55)'); r.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1.3, .8), new THREE.MeshBasicMaterial({map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false}));
  m.rotation.x = -Math.PI / 2; m.position.y = .004; VW.shadow = m;
  return m;
}

function vwUi() {
  const row = document.getElementById('moves');
  VW_PLAYS.forEach(([label], i) => {
    const b = document.createElement('button'); b.id = 'play' + i; b.innerHTML = '<span>' + label + '</span>';
    b.addEventListener('click', () => vwPlay(i)); row.appendChild(b);
  });
  const on = (id, f) => document.getElementById(id).addEventListener('click', f);
  on('pDraw', () => vwPaint('draw')); on('pMeshy', () => vwPaint('meshy'));
  on('lToon', () => vwLight('toon')); on('lFlat', () => vwLight('flat'));
  on('s1', () => vwSpeed(1)); on('s2', () => vwSpeed(.5)); on('s4', () => vwSpeed(.25));
  on('spin', () => { VW.spin = !VW.spin; vwPress('spin', VW.spin); });
  vwPress('spin', VW.spin);
}
function vwPress(id, on) { document.getElementById(id).setAttribute('aria-pressed', on ? 'true' : 'false'); }
function vwPaint(k) { VW.paint = k; VW.mats.toon.map = VW.tex[k]; VW.mats.flat.map = VW.tex[k]; VW.mats.toon.needsUpdate = VW.mats.flat.needsUpdate = true; vwPress('pDraw', k === 'draw'); vwPress('pMeshy', k === 'meshy'); }
function vwLight(k) { VW.it.mesh.material = VW.mats[k]; vwPress('lToon', k === 'toon'); vwPress('lFlat', k === 'flat'); }
function vwSpeed(s) { VW.speed = s; vwPress('s1', s === 1); vwPress('s2', s === .5); vwPress('s4', s === .25); }

// Starts button i's steps from the first (the fighter back on the floor, in place).
function vwPlay(i) {
  VW.playing = i; VW.plan = VW_PLAYS[i][1].map(s => typeof s === 'string' ? [s, 0] : s); VW.step = -1;
  for (let k = 0; k < VW_PLAYS.length; k++) vwPress('play' + k, k === i);
  Object.assign(VW.F, {x: 0, y: 0, vy: 0, air: false, hit: 0}); vwNext();
}
function vwNext() {
  const F = VW.F;
  if (++VW.step >= VW.plan.length) VW.step = 0;
  const [act, n, mode] = VW.plan[VW.step], m = CFG.moves[act];
  VW.mode = mode || null; VW.left = n || (m ? m.s + m.a + (m.r === 'land' ? 0 : m.r) : 30);
  F.act = act === 'thrHit' ? 'thr' : act; F.af = act === 'thrHit' ? 1 : 0; F.hit = act === 'thrHit' ? 1 : 0;
  F.stun = act === 'hitStun' || act === 'block' ? VW.left : 0;
  if (mode === 'jump' || mode === 'jumpAtk') { F.air = true; F.y = 1; F.vy = CFG.jump.v; if (mode === 'jumpAtk') { F.act = 'air'; VW.atkIn = 8; } }
  if (mode === 'fly') { F.air = true; F.y = 1; F.vy = 70; }
  VW.name = VW_NAMES[act] || act;
}
// One frame of the fighter state.
function vwStep() {
  const F = VW.F, S = VW.S;
  S.frame++; F.af++; F.stun = Math.max(0, F.stun - 1);
  if (VW.mode === 'walkF') F.x += CFG.walk.f * F.face;
  else if (VW.mode === 'walkB') F.x -= CFG.walk.b * F.face;
  else if (VW.mode === 'dash') F.x += (F.act === 'dashF' ? 1 : -1) * 100 * F.face;
  if (F.air) {
    if (VW.mode === 'jumpAtk' && VW.atkIn > 0 && --VW.atkIn === 0) { F.act = 'jk'; F.af = 0; VW.name = VW_NAMES.jk; }
    F.y += F.vy; F.vy -= CFG.jump.g;
    if (F.y <= 0) { F.y = 0; F.vy = 0; F.air = false; vwNext(); }
    return;
  }
  if (--VW.left <= 0) vwNext();
}

function vwLoop(now) {
  requestAnimationFrame(vwLoop);
  const dt = VW.last === null ? 0 : Math.min(100, now - VW.last); VW.last = now;
  VW.acc += dt * VW.speed;
  while (VW.acc >= VW_DT) { vwStep(); VW.acc -= VW_DT; }
  if (VW.spin && VW.pointers.size === 0 && now - VW.idleMs > 2500) VW.yaw += dt * .00035;
  const it = VW.it, F = VW.F;
  mdSync(it, 0, VW.S);
  it.root.position.set(0, F.y / 1000, 0); it.root.rotation.y = VW.yaw; it.body.scale.x = it.scale;
  VW.shadow.scale.setScalar(Math.max(.35, 1 - F.y / 2500));
  const cy = .95 + F.y / 2000, c = VW.camera, d = VW.fit * VW.zoom;
  c.position.set(0, cy + .1, d); c.lookAt(0, cy, 0);
  VW.renderer.render(VW.scene, c);
  const m = CFG.moves[F.act], tot = m ? m.s + m.a + (m.r === 'land' ? 8 : m.r) : 0;
  const now2 = document.getElementById('now'), txt = VW.name + (m ? '<small>fotogramma ' + F.af + ' di ' + tot + (F.af > m.s && F.af <= m.s + m.a ? ' · colpisce' : '') + '</small>' : '');
  if (now2.innerHTML !== txt) now2.innerHTML = txt;
}

// The picture's centre sits in the middle of the space above the controls (a view offset), and the camera stands back
// just enough for VW_TALL metres to fit in that space (VW.zoom scales it: pinch and wheel).
function vwResize() {
  const w = innerWidth, h = innerHeight, free = Math.max(120, document.getElementById('bottom').getBoundingClientRect().top), dy = h - free, c = VW.camera;
  VW.renderer.setSize(w, h, false);
  c.fov = 30; c.aspect = w / (h + dy); c.setViewOffset(w, h + dy, 0, dy, w, h); c.updateProjectionMatrix();
  const t = Math.tan(c.fov * Math.PI / 360);
  VW.fit = Math.max(VW_TALL * (h + dy) / free / (2 * t), VW_WIDE / (2 * t * c.aspect)) / .92;
}

// Drag turns, pinch or wheel zooms, double tap resets.
function vwInput() {
  const cv = document.getElementById('view'), P = VW.pointers;
  cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); P.set(e.pointerId, {x: e.clientX, y: e.clientY}); VW.pinch = 0; VW.idleMs = performance.now(); });
  cv.addEventListener('pointermove', e => {
    const p = P.get(e.pointerId); if (!p) return;
    if (P.size === 1) VW.yaw += (e.clientX - p.x) * .012;
    else {
      const [a, b] = [...P.values()], d = Math.hypot(a.x - b.x, a.y - b.y);
      p.x = e.clientX; p.y = e.clientY;
      const d2 = Math.hypot([...P.values()][0].x - [...P.values()][1].x, [...P.values()][0].y - [...P.values()][1].y);
      if (d > 0 && d2 > 0) VW.zoom = Math.max(.45, Math.min(1.8, VW.zoom * d / d2));
    }
    p.x = e.clientX; p.y = e.clientY; VW.idleMs = performance.now();
  });
  const up = e => { P.delete(e.pointerId); VW.idleMs = performance.now(); };
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  cv.addEventListener('wheel', e => { e.preventDefault(); VW.zoom = Math.max(.45, Math.min(1.8, VW.zoom * (1 + e.deltaY * .001))); }, {passive: false});
  cv.addEventListener('dblclick', () => { VW.yaw = VW_YAW; VW.zoom = 1; });
}

vwBoot();
