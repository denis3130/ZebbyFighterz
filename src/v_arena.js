// "Anteprima dell'arena": the 3D arena alone (no fighters, HUD or menus) with a free camera, to look at it from
// anywhere near the game's views. Built by mk.sh into arena.html (not committed) from the game's own arena and
// renderer modules (d_arena.js, d_render.js), so it shows exactly what the game draws.
// Controls: one finger / left mouse drag = move (or turn, with "Ruota"), right drag or Shift = the other one; two
// fingers = pinch to go forwards and backwards, drag to move; wheel = forwards/backwards; double tap = back to the game
// camera. Keyboard: A/D, W/S, R/F to move, arrows to look, Home or 0 to reset. Controller: left stick to move, right
// stick to look, LB/RB down/up, A to reset. Two ranges for the camera (buttons): "Come nel gioco" (default), a little
// past what the game's camera can reach; "Libera", much wider: the mountains, the mist, the sky and the floor go on
// as far as it can see (Denis, 11/11: "mantieni lo stile delle montagne fino ai limiti della modalità libera").

const VA = {x: 0, y: 0, z: 0, yaw: 0, pitch: 0, mode: 'move', ptrs: new Map(), pinch: 0, mid: null, keys: new Set(),
  hold: 0, last: 0, frames: 0, fpsT: 0, tap: 0};
// metres and radians: x, y, z ranges, yaw, pitch; speeds: move m/s, turn rad/s, drag (the scene at the mountains'
// depth follows the finger at 1), turnDrag rad per px, wheel m per wheel unit
const VA_LIMS = {game: {x: [-3.4, 3.4], y: [.6, 3.2], z: [4.5, 10], yaw: [-.14, .14], pitch: [-.1, .12]},
  free: {x: [-11, 11], y: [.35, 9], z: [-1, 22], yaw: [-.45, .45], pitch: [-.35, .42]}};
let VA_LIM = VA_LIMS.game;
const VA_SPEED = {move: 3.5, turn: .9, drag: .75, turnDrag: .004, wheel: .005};

function vaHome() {
  const k = CFG.cam, t = Math.tan(k.fov * Math.PI / 360);
  VA.x = 0; VA.z = k.dist0; VA.y = k.dist0 * (k.footScreen - .5) * 2 * t; VA.yaw = 0; VA.pitch = 0;
}

function vaClamp() {
  const L = VA_LIM, c = (v, r) => Math.max(r[0], Math.min(r[1], v));
  VA.x = c(VA.x, L.x); VA.y = c(VA.y, L.y); VA.z = c(VA.z, L.z); VA.yaw = c(VA.yaw, L.yaw); VA.pitch = c(VA.pitch, L.pitch);
}

// Moves the camera by (right, up, forward) metres in its own frame (forward along where it looks, level).
function vaMove(r, u, f) {
  const s = Math.sin(VA.yaw), c = Math.cos(VA.yaw);
  VA.x += r * c - f * s; VA.z -= r * s + f * c; VA.y += u;
  vaClamp();
}

function vaSetRange(k) {
  VA_LIM = VA_LIMS[k]; vaClamp();
  document.getElementById('rGame').setAttribute('aria-pressed', k === 'game' ? 'true' : 'false');
  document.getElementById('rFree').setAttribute('aria-pressed', k === 'free' ? 'true' : 'false');
}

function vaSetMode(m) {
  VA.mode = m;
  document.getElementById('mMove').setAttribute('aria-pressed', m === 'move' ? 'true' : 'false');
  document.getElementById('mTurn').setAttribute('aria-pressed', m === 'turn' ? 'true' : 'false');
}

// A drag of (dx, dy) screen px: the scene follows the finger (move) or the view turns with it (turn).
function vaDrag(dx, dy, turn) {
  if (turn) { VA.yaw += dx * VA_SPEED.turnDrag; VA.pitch += dy * VA_SPEED.turnDrag; vaClamp(); return; }
  const depth = Math.max(4, VA.z + 15), k = VA_SPEED.drag * depth * 2 * Math.tan(CFG.cam.fov * Math.PI / 360) / innerHeight;
  vaMove(-dx * k, dy * k, 0);
}

function vaInput() {
  const cv = document.getElementById('game');
  cv.addEventListener('pointerdown', e => {
    cv.setPointerCapture(e.pointerId);
    VA.ptrs.set(e.pointerId, {x: e.clientX, y: e.clientY, turn: e.button === 2 || e.shiftKey});
    if (VA.ptrs.size === 2) { const p = [...VA.ptrs.values()]; VA.pinch = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y); VA.mid = {x: (p[0].x + p[1].x) / 2, y: (p[0].y + p[1].y) / 2}; }
    const now = performance.now();
    if (VA.ptrs.size === 1 && now - VA.tap < 300) vaHome();   // double tap: back to the game camera
    VA.tap = now;
  });
  cv.addEventListener('pointermove', e => {
    const p = VA.ptrs.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    if (VA.ptrs.size === 1) vaDrag(dx, dy, (VA.mode === 'turn') !== p.turn);
    else if (VA.ptrs.size === 2) {
      const q = [...VA.ptrs.values()], d = Math.hypot(q[0].x - q[1].x, q[0].y - q[1].y);
      const mid = {x: (q[0].x + q[1].x) / 2, y: (q[0].y + q[1].y) / 2};
      vaMove(0, 0, (d - VA.pinch) * .02); VA.pinch = d;
      if (VA.mid) vaDrag(mid.x - VA.mid.x, mid.y - VA.mid.y, false);
      VA.mid = mid;
    }
  });
  const up = e => { VA.ptrs.delete(e.pointerId); if (VA.ptrs.size < 2) VA.mid = null; };
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('wheel', e => { e.preventDefault(); vaMove(0, 0, -e.deltaY * VA_SPEED.wheel); }, {passive: false});
  addEventListener('keydown', e => {
    if (e.key === 'Home' || e.key === '0') { vaHome(); return; }
    VA.keys.add(e.key.toLowerCase());
    if (e.key.startsWith('Arrow')) e.preventDefault();
  });
  addEventListener('keyup', e => VA.keys.delete(e.key.toLowerCase()));
  addEventListener('blur', () => { VA.keys.clear(); VA.hold = 0; });
  document.getElementById('mMove').addEventListener('click', () => vaSetMode('move'));
  document.getElementById('mTurn').addEventListener('click', () => vaSetMode('turn'));
  document.getElementById('reset').addEventListener('click', vaHome);
  document.getElementById('rGame').addEventListener('click', () => vaSetRange('game'));
  document.getElementById('rFree').addEventListener('click', () => vaSetRange('free'));
  for (const [id, dir] of [['fwd', 1], ['back', -1]]) {   // held buttons: forwards / backwards while pressed
    const b = document.getElementById(id);
    b.addEventListener('pointerdown', e => { b.setPointerCapture(e.pointerId); VA.hold = dir; b.classList.add('held'); });
    const stop = () => { VA.hold = 0; b.classList.remove('held'); };
    b.addEventListener('pointerup', stop); b.addEventListener('pointercancel', stop);
  }
}

// Keys, held buttons and the controller, per frame (dt s).
function vaStep(dt) {
  const K = VA.keys, has = (...k) => k.some(x => K.has(x)), m = VA_SPEED.move * dt, t = VA_SPEED.turn * dt;
  let r = (has('d') ? 1 : 0) - (has('a') ? 1 : 0), u = (has('r', 'pageup') ? 1 : 0) - (has('f', 'pagedown') ? 1 : 0);
  let f = (has('w') ? 1 : 0) - (has('s') ? 1 : 0) + VA.hold;
  let yaw = (has('arrowleft', 'q') ? 1 : 0) - (has('arrowright', 'e') ? 1 : 0), pitch = (has('arrowup') ? 1 : 0) - (has('arrowdown') ? 1 : 0);
  let pads = [];
  try { pads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : []; } catch (e) { pads = []; }
  for (const p of pads) {
    const ax = i => Math.abs(p.axes[i] || 0) > .15 ? p.axes[i] : 0, bt = i => p.buttons[i] && p.buttons[i].pressed;
    r += ax(0); f -= ax(1); yaw -= ax(2); pitch -= ax(3);
    u += (bt(5) ? 1 : 0) - (bt(4) ? 1 : 0) + ((p.buttons[7] && p.buttons[7].value) || 0) - ((p.buttons[6] && p.buttons[6].value) || 0);
    if (bt(0)) vaHome();
  }
  if (r || u || f) vaMove(r * m, u * m, f * m);
  if (yaw || pitch) { VA.yaw += yaw * t; VA.pitch += pitch * t; vaClamp(); }
}

function vaLoop(now) {
  requestAnimationFrame(vaLoop);
  const dt = Math.min(.05, (now - (VA.last || now)) / 1000);
  VA.last = now;
  vaStep(dt);
  cam.x = VA.x;                                       // (the leaves drift round the camera)
  arenaStep(now, null); rdLeavesStep(now);
  camera.position.set(VA.x, VA.y, VA.z);
  camera.rotation.set(VA.pitch, VA.yaw, 0, 'YXZ');
  camera.updateMatrixWorld();
  renderer.clear(); renderer.render(scene, camera);
  VA.frames++;
  if (now - VA.fpsT >= 500) {
    document.getElementById('fps').firstChild.nodeValue = 'FPS ' + Math.round(VA.frames * 1000 / (now - VA.fpsT));
    VA.frames = 0; VA.fpsT = now;
  }
}

function vaBoot() {
  renderInit().then(() => {
    F3D.forEach(f => { f.root.visible = false; });
    rdShadowsStep(null);
    vaHome(); vaInput();
    requestAnimationFrame(vaLoop);
  });
}
// test hooks (arena.html is never the game page)
window.__VA = {VA, vaHome, vaMove, vaDrag, vaStep, vaSetRange, VA_LIMS, ARENA, camera, renderer, scene, cam};
vaBoot();
