// --- fx.js: something to hit, and the hit's feel (viewer only). ---
// A training dummy (the code-built placeholder fighter) stands on the fight line in front of Ren. When a move's box
// touches it on the first active frame: the game's hitstop (CFG.stop: both freeze), a white flash and a squash of the
// dummy, a spark at the contact point, a camera shake on heavy hits (CFG.fx), then the dummy's reaction with the move's
// own numbers (hitstun and push, knockdown, launch). It comes back to its spot; Ren waits for it in his guard.
// The energy shot charges a glow between the hands and leaves as a projectile. "Manichino" hides all of it.
const RX = {home: 850, D: null, dm: null, stop: 0, wait: null, flash: 0, squash: 0, shake: 0, shakeAmp: 0, shakeMs: 1, sparks: [], proj: null, glow: null, t: 0,
  plays: {2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1}, dir: new THREE.Vector3(), v: new THREE.Vector3(), aim: 0, wide: 1};
function rxOn() { return RN.on && RN.opt.dummy && !!RX.plays[VW.playing]; }
function rxReady() { const D = RX.D; return D.act === 'idle' && Math.abs(D.x - RX.home) < 5; }

function rxTex(draw) { const c = document.createElement('canvas'); c.width = c.height = 128; draw(c.getContext('2d')); return new THREE.CanvasTexture(c); }
function rxSprite(tex) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({map: tex, transparent: true, depthWrite: false, depthTest: false})); s.visible = false; s.renderOrder = 5; return s;
}

RN.hooks.boot.push(VW => {
  rnOpt('dummy', 'Manichino', true);
  VW.yaw = F3_YAW; VW.spin = false; vwPress('spin', false);   // the game's own view of the two: the fight line across the screen
  const dm = RX.dm = fighterBuild('kael'), D = RX.D = newFighter(1, 'kael');
  D.x = RX.home; D.face = -1; D.t = 0;
  VW.scene.add(dm.root);
  const sh = VW.shadow.clone(); RX.shadow = sh; VW.scene.add(sh);
  // a burst: a white core, cyan rays
  const burst = rxTex(g => {
    g.translate(64, 64);
    for (let i = 0; i < 10; i++) { g.rotate(Math.PI / 5); g.fillStyle = i % 2 ? 'rgba(120,235,255,.95)' : 'rgba(255,255,255,.95)';
      g.beginPath(); g.moveTo(0, -6); g.lineTo(i % 2 ? 44 : 62, 0); g.lineTo(0, 6); g.fill(); }
    const r = g.createRadialGradient(0, 0, 0, 0, 0, 34); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.5, 'rgba(210,248,255,.9)'); r.addColorStop(1, 'rgba(53,216,255,0)');
    g.fillStyle = r; g.beginPath(); g.arc(0, 0, 34, 0, 7); g.fill();
  });
  for (let i = 0; i < 3; i++) { const s = rxSprite(burst); s.material = s.material.clone(); VW.scene.add(s); RX.sparks.push({s, left: 0, life: 1, size: 1}); }
  const glow = rxTex(g => {
    const r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.28, 'rgba(190,245,255,.95)'); r.addColorStop(.6, 'rgba(53,216,255,.4)'); r.addColorStop(1, 'rgba(53,216,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  });
  RX.glow = rxSprite(glow); RX.ball = rxSprite(glow); RX.ball.material = RX.ball.material.clone(); VW.scene.add(RX.glow, RX.ball);
});

RN.hooks.reset.push(() => {
  const D = RX.D; if (!D) return;
  Object.assign(D, {x: RX.home, y: 0, vx: 0, vy: 0, act: 'idle', af: 0, air: false, stun: 0, t: 0});
  RX.stop = 0; RX.wait = null; RX.proj = null; RX.flash = RX.squash = RX.shake = 0;
});
RN.hooks.opt.push((k, v) => {
  if (!RX.D) return;
  if (k === 'on' && !v) {   // the old animation: Ren alone, as the page was
    RX.dm.root.visible = RX.shadow.visible = RX.glow.visible = RX.ball.visible = false;
    for (const sp of RX.sparks) sp.s.visible = false;
    VW.aimX = 0; VW.wide = 1; RX.aim = 0; RX.wide = 1;
  }
  if (k === 'dummy' && VW.playing !== undefined) vwPlay(VW.playing);
});

// One frame of the dummy: it flies and falls, lies and gets up, slides while stunned, walks back to its spot.
function rxDummy() {
  const D = RX.D;
  D.af++;
  if (D.act === 'thrown') return;
  if (D.air) {
    D.x += D.vx; D.y += D.vy; D.vy -= CFG.jump.g;
    if (D.y <= 0) { D.y = 0; D.vy = 0; D.vx = 0; D.air = false; D.act = 'knock'; D.af = 0; D.t = CFG.knock.ground; RX.squash = CFG.fx.squashMs; }
    return;
  }
  const d = RX.home - D.x;
  switch (D.act) {
    case 'hitStun': D.x += D.vx; D.vx = Math.max(0, D.vx - CFG.phys.pushFric); if (D.af > 6) D.x += d * .14; if (--D.stun <= 0) { D.act = 'idle'; D.af = 0; } break;
    case 'knock': if (--D.t <= 0) { D.act = 'getup'; D.af = 0; D.t = CFG.knock.getup; } break;
    case 'getup': if (--D.t <= 0) { D.act = 'idle'; D.af = 0; } break;
    default:
      if (Math.abs(d) > 4) { const a = d < 0 ? 'walkF' : 'walkB'; if (D.act !== a) { D.act = a; D.af = 0; } D.x += Math.sign(d) * Math.min(Math.abs(d), 70); }
      else { D.x = RX.home; if (D.act !== 'idle') { D.act = 'idle'; D.af = 0; } }
  }
}
// Move m (a CFG.moves entry, CFG.thr or CFG.spec) lands on the dummy at sim point (x, y) mm: hitstop, effects, reaction.
function rxHit(m, x, y) {
  const D = RX.D, heavy = m.stop === 'heavy' || m.stop === 'thr', fx = CFG.fx;
  RX.stop = CFG.stop[m.stop] || 6; RX.flash = fx.flashMs; RX.squash = fx.squashMs;
  if (heavy) { RX.shake = RX.shakeMs = fx.shakeHeavy[1]; RX.shakeAmp = fx.shakeHeavy[0]; }
  const sp = RX.sparks.find(s => s.left <= 0) || RX.sparks[0];
  sp.size = heavy ? fx.spark.heavy : fx.spark.light; sp.life = sp.left = heavy ? 230 : 160; sp.x = x; sp.y = y; sp.rot = (x * 7 + y * 3) % 6;
  D.af = 0; D.stun = 0;
  if (m.knock) { D.act = 'knock'; D.air = true; D.y = 1; D.vx = (m.vx || 0) * .8; D.vy = m.vy; }
  else if (m.launch) { D.act = 'juggle'; D.air = true; D.y = 1; D.vx = m.vx || 0; D.vy = m.vy; }
  else { D.act = 'hitStun'; D.stun = m.hs || 14; D.vx = (m.push || 0) * .5; }
}

// Before a sim step: the hitstop holds it; Ren waits in his guard while the dummy is not back on its spot.
RN.hooks.hold.push(VW => {
  const F = VW.F, on = rxOn();
  if (RX.stop > 0) { RX.stop--; return true; }
  if (!on) { if (RX.wait) { F.act = RX.wait.act; F.af = 0; VW.name = RX.wait.name; RX.wait = null; } return false; }
  const strike = CFG.moves[F.act] || F.act === 'spec' || (F.act === 'thr' && !F.hit);
  if (RX.wait) {
    VW.S.frame++; F.af++; rxDummy();
    if (rxReady()) { F.act = RX.wait.act; F.af = 0; VW.name = RX.wait.name; RX.wait = null; }
    return 'wait';
  }
  if (strike && F.af === 0 && !F.air && !rxReady()) { RX.wait = {act: F.act, name: VW.name}; F.act = 'idle'; F.af = 0; VW.name = VW_NAMES.idle; return 'wait'; }
  return false;
});
// After a sim step: the dummy's frame, then contacts (a move's first active frame, the throw's hit, the projectile).
RN.hooks.step.push(VW => {
  const F = VW.F, D = RX.D, m = CFG.moves[F.act], on = rxOn();
  rxDummy();
  if (F.act === 'spec' && F.af === CFG.spec.spawn) RX.proj = {x: CFG.spec.x, y: CFG.spec.y};
  if (RX.proj) {
    RX.proj.x += CFG.spec.speed;
    if (on && D.act !== 'knock' && D.act !== 'getup' && RX.proj.x + CFG.spec.box >= D.x - CFG.body.hurt) { rxHit(CFG.spec, D.x - CFG.body.hurt, RX.proj.y); RX.proj = null; }
    else if (RX.proj.x > 4200) RX.proj = null;
  }
  if (!on) return;
  if (F.act === 'thr' && F.hit) {
    if (F.af < CFG.thr.hitF && D.act !== 'knock') { D.act = 'thrown'; D.x = RX.home - 180; }
    else if (F.af === CFG.thr.hitF) { D.act = 'idle'; rxHit(CFG.thr, D.x - 150, 1100); }
  } else if (D.act === 'thrown') { D.act = 'idle'; D.af = 0; }
  if (m && F.af === m.s + 1 && D.act !== 'getup' && !(D.act === 'knock' && !D.air)) {
    const b = moveBox(F, F.act);
    if (b) for (const h of hurtBoxes(D)) {
      const x0 = Math.max(b.x0, h.x0), x1 = Math.min(b.x1, h.x1), y0 = Math.max(b.y0, h.y0), y1 = Math.min(b.y1, h.y1);
      if (x0 < x1 && y0 < y1) { rxHit(m, x0, (y0 + y1) / 2); break; }
    }
  }
});

// Each drawn frame: the dummy's pose and place, the flash, squash, sparks, shake, glow and projectile; the camera
// frames Ren and the dummy together.
RN.hooks.draw.push((VW, dt, cam) => {
  const D = RX.D, dm = RX.dm, on = rxOn(), ms = VW.hold ? dt : dt * Math.max(.25, VW.speed) * VW_PACE, th = VW.yaw - F3_YAW;
  const dir = RX.dir.set(Math.cos(th), 0, -Math.sin(th));   // the fight line (the sim's +x) in the viewer's world
  RX.t += dt;
  dm.root.visible = RX.shadow.visible = on;
  if (on) {
    const S = VW.S, jit = RX.stop > 0 && D.act !== 'thrown' ? .016 * Math.sin(RX.t * .09) : 0;
    dm.root.position.copy(dir).multiplyScalar(D.x / 1000 + jit).setY(D.y / 1000);
    dm.root.rotation.y = th - F3_YAW;
    f3Apply(dm, f3Solve(f3Raw(D, S)));
    RX.flash = Math.max(0, RX.flash - ms); RX.squash = Math.max(0, RX.squash - ms);
    const fl = RX.flash > 0 ? 1 : 0, q = Math.sin(Math.PI * RX.squash / CFG.fx.squashMs), sq = CFG.fx.squash;
    for (const k in dm.mats) dm.mats[k].emissive.setScalar(fl * .9);
    dm.root.scale.set(1 + (sq[0] - 1) * q, 1 + (sq[1] - 1) * q, 1 + (sq[0] - 1) * q);
    RX.shadow.position.copy(dm.root.position).setY(.004); RX.shadow.scale.setScalar(Math.max(.35, 1 - D.y / 2500));
  }
  // sparks: full size at once, held, then shrinking and fading
  for (const sp of RX.sparks) {
    sp.left = Math.max(0, sp.left - ms); sp.s.visible = on && sp.left > 0;
    if (!sp.s.visible) continue;
    const u = 1 - sp.left / sp.life, hold = CFG.fx.spark.hold, k = u < hold ? 1 : 1 - (u - hold) / (1 - hold);
    sp.s.position.copy(dir).multiplyScalar(sp.x / 1000).setY(sp.y / 1000).addScaledVector(RX.v.copy(cam.position).sub(sp.s.position).normalize(), .25);
    sp.s.scale.setScalar(sp.size * (.75 + .25 * k)); sp.s.material.opacity = k; sp.s.material.rotation = sp.rot + u * .5;
  }
  // the energy shot: a glow between the hands growing until it leaves, then the projectile on the fight line
  const F = VW.F, it = VW.it, sp = CFG.spec.spawn, g = RX.glow, b = RX.ball;
  g.visible = F.act === 'spec' && F.af <= sp + 4;
  if (g.visible) {
    it.root.updateMatrixWorld(true);
    g.position.addVectors(it.limbs.handL.getWorldPosition(RX.v), it.limbs.handR.getWorldPosition(new THREE.Vector3())).multiplyScalar(.5);
    g.scale.setScalar(Math.max(.02, F.af <= sp ? .12 + .42 * rnSm(F.af / sp) + .035 * Math.sin(RX.t * .05) : .75 * (1 - (F.af - sp) / 4)));
  }
  b.visible = !!RX.proj;
  if (b.visible) { b.position.copy(dir).multiplyScalar(RX.proj.x / 1000).setY(RX.proj.y / 1000); b.scale.setScalar(CFG.fx.proj.halo * (1 + .08 * Math.sin(RX.t * .06))); }
  // camera: between the two, wide enough for both; a decaying shake on heavy hits
  const aim = on ? .42 * dir.x : 0, wide = on ? Math.max(1, (Math.abs(dir.x) * RX.home / 1000 + 1.55) / VW_WIDE) : 1, e = Math.min(1, dt * .008);
  RX.aim += (aim - RX.aim) * e; RX.wide += (wide - RX.wide) * e; VW.aimX = RX.aim; VW.wide = RX.wide;
  if (RX.shake > 0) {
    RX.shake = Math.max(0, RX.shake - ms);
    const a = RX.shakeAmp * RX.shake / RX.shakeMs;
    cam.position.x += a * Math.sin(RX.t * .11); cam.position.y += a * Math.cos(RX.t * .14);
  }
});
