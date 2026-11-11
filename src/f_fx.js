// Game feel (Task 9). Graphics only: it reads the sim's events and state and never writes them; everything runs on the
// render clock (ms) with its own seeded generator, so CFG.fx.on = false changes nothing in the fight. Hit sparks and
// bursts (sprites), the white flash and squash of the fighter hit, camera shake (heavy hits, KO), the charge
// glow while P/K is held, one projectile core + halo + trail per side and the full-screen KO flash. All sprites are
// pooled and built once (fxBuild, from renderInit): the scene's child count never changes afterwards.
// fxEvents(S, nowMs) once per sim step, fxUpdate(nowMs, S) once per drawn frame, fxShakeApply() around the scene draw.

// Sprite sizes in metres (the spark sizes are CFG.fx.spark), lives in ms, colours.
const FX_K = {pool: 16, life: {light: 170, heavy: 250, block: 150}, burst: 1.3, ko: 120, trail: 5, trailGap: .14,
  glow: [.25, .7], z: .2, pz: .1};
const FX_COL = {hit: 0xffe066, heavy: 0xffc233, block: 0xa6dcff, clash: 0xffffff, glow: 0xffc874, glowFull: 0xfff2d0};
// Projectile colours per character: core (white), halo and the saturated rim (and trail) that separates it from the foam.
const FX_PROJ = {ren: {core: 0xffffff, halo: 0xbff3ff, rim: 0x0a8fe0}, kael: {core: 0xffffff, halo: 0xc9a2ff, rim: 0x7a2cf0}};
for (const k in FX_PROJ) FX_PROJ[k].coreC = new THREE.Color(FX_PROJ[k].core);

// sparks = the active hit sparks, pool = the free ones; side[i] = flash/squash state of the fighter on side i
// (f/s = [start, end] ms, fon/son = applied now; each fighter keeps its materials' own emissive colours as it.em0, so they
// follow it when it changes side); flash, squash = the last
// ones started; shake = {amp m (0 = none), t0, until, dur}; screenFlash = [start, end] of the KO flash.
const FX = {built: false, now: 0, seed: 11, sparks: [], pool: [], glow: [], pc: [], side: [], shake: {amp: 0, t0: 0, until: 0, dur: 1},
  flash: [0, 0], squash: [0, 0], screenFlash: [0, 0], el: null, elOp: 0, v: new THREE.Vector3(),
  projColor: char => FX_PROJ[char].coreC};

function fxRand() {   // mulberry32 on FX.seed
  let t = FX.seed = FX.seed + 0x6D2B79F5 | 0;
  t = Math.imul(t ^ t >>> 15, 1 | t); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) / 4294967296;
}

// A soft round glow (kind 0), a spark: a glow with a four-pointed star (kind 1) or the projectile's rim: a ring (kind 2).
// Sparks, rims and trails are drawn normally, not added, so their colour stays visible over white (flash, foam).
function fxTex(kind) {
  return rdCanvasTexture(64, (g, n) => {
    const c = n / 2, gr = g.createRadialGradient(c, c, 0, c, c, c);
    if (kind === 2) {   // the rim: a transparent middle, a solid ring, a soft outer edge
      gr.addColorStop(0, 'rgba(255,255,255,.35)'); gr.addColorStop(.5, 'rgba(255,255,255,.55)'); gr.addColorStop(.72, 'rgba(255,255,255,1)');
      gr.addColorStop(.9, 'rgba(255,255,255,.9)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    } else if (kind) { gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.3, 'rgba(255,255,255,.85)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); }
    else { gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.45, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); }
    g.fillStyle = gr; g.fillRect(0, 0, n, n);
    if (kind !== 1) return;
    g.fillStyle = '#fff';
    for (let a = 0; a < 4; a++) {
      g.save(); g.translate(c, c); g.rotate(a * Math.PI / 2); g.beginPath();
      g.moveTo(0, -n * .48); g.lineTo(n * .06, -n * .06); g.lineTo(-n * .06, -n * .06); g.fill(); g.restore();
    }
  });
}
function fxSprite(tex, hex, add) {
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: tex, color: hex, blending: add === false ? THREE.NormalBlending : THREE.AdditiveBlending, transparent: true,
    depthWrite: false, fog: false}));
  sp.visible = false; scene.add(sp);
  return sp;
}

// The pools, the KO overlay and the fighters' original emissive colours. Needs the scene and the fighters.
function fxBuild() {
  if (FX.built || F3D.length < 2) return;
  FX.built = true;
  const star = fxTex(1), soft = fxTex(0), ring = fxTex(2);
  for (let i = 0; i < FX_K.pool; i++) FX.pool.push({sp: fxSprite(star, 0xffffff, false), t0: 0, life: 1, size: 1});
  for (let i = 0; i < 2; i++) {
    const it = F3D[i];
    if (!it.em0) it.em0 = Object.values(it.mats).map(m => m.emissive.clone());   // each fighter's own colours (they follow it if it changes side)
    FX.side.push({f: [0, 0], s: [0, 0], fon: false, son: false});
    FX.glow.push([fxSprite(soft, FX_COL.glow), fxSprite(soft, FX_COL.glow)]);
    const p = {core: fxSprite(soft, 0xffffff), halo: fxSprite(soft, 0xffffff), rim: fxSprite(ring, 0xffffff, false), trail: [], char: ''};
    for (let k = 0; k < FX_K.trail; k++) p.trail.push(fxSprite(soft, 0xffffff, false));
    FX.pc.push(p);
  }
  const el = FX.el = document.createElement('div');
  el.style.cssText = 'position:absolute;inset:0;background:#fff;opacity:0;pointer-events:none';
  (document.getElementById('hud') || document.body).appendChild(el);
}

function fxSpark(x, y, size, hex, life, now) {
  const s = FX.pool.pop() || FX.sparks.shift();   // all busy: the oldest one is reused
  s.t0 = now; s.life = life; s.size = size;
  s.sp.material.color.setHex(hex); s.sp.material.rotation = fxRand() * Math.PI / 2;
  s.sp.position.set(x / 1000, y / 1000, FX_K.z); s.sp.visible = true;
  FX.sparks.push(s);
}
function fxHurt(side, now) {   // flash + squash of the fighter on `side`
  const k = CFG.fx, d = FX.side[side];
  d.f[0] = FX.flash[0] = now; d.f[1] = FX.flash[1] = now + k.flashMs;
  d.s[0] = FX.squash[0] = now; d.s[1] = FX.squash[1] = now + k.squashMs;
}
function fxShake(a, now) {
  const [amp, ms] = a, sh = FX.shake;
  if (sh.amp * Math.max(0, sh.until - now) / sh.dur > amp) return;   // a stronger shake is still running
  sh.amp = amp; sh.t0 = now; sh.until = now + ms; sh.dur = ms;
}

// The events of one sim step, at render time now.
function fxEvents(S, now) {
  if (!CFG.fx.on || !FX.built) return;
  FX.now = now;
  const k = CFG.fx, sp = k.spark;
  for (const e of S.ev) {
    const char = fighterOf(S, e.side).char, halo = FX_PROJ[char] ? FX_PROJ[char].halo : FX_COL.hit;
    switch (e.t) {
      case 'hit':
        fxSpark(e.x, e.y, e.heavy ? sp.heavy : sp.light, e.heavy ? FX_COL.heavy : FX_COL.hit, FX_K.life[e.heavy ? 'heavy' : 'light'], now);
        fxHurt(1 - e.side, now);
        if (e.heavy) fxShake(k.shakeHeavy, now);
        break;
      case 'block': case 'projBlock':
        fxSpark(e.x, e.y, sp.block, FX_COL.block, FX_K.life.block, now); break;
      case 'projHit':
        fxSpark(e.x, e.y, sp.heavy, halo, FX_K.life.heavy, now); fxHurt(1 - e.side, now); break;
      case 'projClash':
        fxSpark(e.x, e.y, sp.heavy * FX_K.burst, FX_COL.clash, FX_K.life.heavy, now); break;
      case 'heavyFire': {   // a short flash of the whole body of the fighter who lets the heavy go
        const d = FX.side[e.side]; d.f[0] = FX.flash[0] = now; d.f[1] = FX.flash[1] = now + k.flashMs; break;
      }
      case 'ko':
        fxShake(k.shakeKO, now); FX.screenFlash[0] = now; FX.screenFlash[1] = now + FX_K.ko; break;
    }
  }
}

// Every drawn frame at nowMs: expires and animates the sparks, applies flash and squash, the shake bookkeeping, the KO
// flash and, given S (null = no match: hide them), the charge glow and the projectiles.
function fxUpdate(nowMs, S) {
  if (!FX.built) return;
  FX.now = nowMs;
  for (let i = FX.sparks.length - 1; i >= 0; i--) {
    const s = FX.sparks[i], age = nowMs - s.t0;
    if (age < 0 || age >= s.life) {
      s.sp.visible = false; FX.pool.push(s);
      FX.sparks[i] = FX.sparks[FX.sparks.length - 1]; FX.sparks.length--;
      continue;
    }
    const u = age / s.life, e = 1 - (1 - u) * (1 - u);
    const h = CFG.fx.spark.hold, f = u < h ? 0 : (u - h) / (1 - h);   // full size and opacity for the first share of its life
    s.sp.scale.setScalar(s.size * (.8 + .2 * Math.min(1, u / .15) - .3 * f * f)); s.sp.material.opacity = 1 - f * f;
  }
  for (let i = 0; i < 2; i++) fxHurtStep(i, nowMs);
  const sh = FX.shake;
  if (sh.amp && (nowMs < sh.t0 || nowMs >= sh.until)) sh.amp = 0;
  const sf = FX.screenFlash, a = nowMs >= sf[0] && nowMs < sf[1] ? 1 - (nowMs - sf[0]) / (sf[1] - sf[0]) : 0;
  if (a !== FX.elOp) { FX.elOp = a; FX.el.style.opacity = a; }
  if (S !== undefined) { fxGlowStep(nowMs, S); fxProjStep(nowMs, S); }
}

function fxHurtStep(i, now) {
  const d = FX.side[i], root = F3D[i].root, mats = Object.values(F3D[i].mats);
  const fon = now >= d.f[0] && now < d.f[1];
  if (fon !== d.fon) { d.fon = fon; mats.forEach((m, k) => fon ? m.emissive.setRGB(1, 1, 1) : m.emissive.copy(F3D[i].em0[k])); }
  const son = now >= d.s[0] && now < d.s[1];
  if (son) {
    const u = 1 - (now - d.s[0]) / (d.s[1] - d.s[0]), e = u * u, q = CFG.fx.squash;
    root.scale.set(1 + (q[0] - 1) * e, 1 + (q[1] - 1) * e, 1 + (q[0] - 1) * e);
  } else if (d.son) root.scale.set(1, 1, 1);
  d.son = son;
}

// While P / K is held from input.chargeShow on: a pulsing glow at the hand of the heavy punch / the foot of the heavy
// kick, growing until input.hold (then whiter).
function fxGlowStep(now, S) {
  const c = CFG.input, g = FX_K.glow;
  for (let i = 0; i < 2; i++) for (let k = 0; k < 2; k++) {
    const sp = FX.glow[i][k], h = S ? fighterOf(S, i).hold[k] : 0, on = CFG.fx.on && S && S.phase === 'fight' && h >= c.chargeShow;
    sp.visible = !!on;
    if (!on) continue;
    const u = Math.min(1, (h - c.chargeShow) / (c.hold - c.chargeShow));
    F3D[i].limbs[CFG.moves[k ? 'hk' : 'hp'].limb].getWorldPosition(FX.v);
    sp.position.set(FX.v.x, FX.v.y, FX.v.z + .08);
    sp.scale.setScalar((g[0] + (g[1] - g[0]) * u) * (1 + .14 * Math.sin(now * .03)));
    sp.material.opacity = .55 + .35 * u; sp.material.color.setHex(u >= 1 ? FX_COL.glowFull : FX_COL.glow);
  }
}

// One projectile per side: a white core in a coloured halo, a trail of fading discs behind it.
function fxProjStep(now, S) {
  for (let i = 0; i < 2; i++) {
    const pc = FX.pc[i];
    let p = null;
    if (S && CFG.fx.on) for (const q of S.proj) if (q.side === i && q.live) p = q;
    pc.core.visible = pc.halo.visible = pc.rim.visible = !!p;
    for (const t of pc.trail) t.visible = !!p;
    if (!p) continue;
    const col = FX_PROJ[fighterOf(S, i).char], dir = p.vx < 0 ? -1 : 1, x = p.x / 1000, y = p.y / 1000, pulse = 1 + .1 * Math.sin(now * .04 + i);
    if (pc.char !== col) {
      pc.char = col; pc.core.material.color.setHex(col.core); pc.halo.material.color.setHex(col.halo); pc.rim.material.color.setHex(col.rim);
      for (const t of pc.trail) t.material.color.setHex(col.rim);
    }
    const pk = CFG.fx.proj;
    pc.rim.position.set(x, y, FX_K.pz - .005); pc.rim.scale.setScalar(pk.rim * pulse); pc.rim.material.opacity = .95;
    pc.halo.position.set(x, y, FX_K.pz); pc.halo.scale.setScalar(pk.halo * pulse); pc.halo.material.opacity = .8;
    pc.core.position.set(x, y, FX_K.pz + .01); pc.core.scale.setScalar(pk.core * pulse);
    pc.trail.forEach((t, k) => {
      t.position.set(x - dir * (k + 1) * FX_K.trailGap, y + .03 * Math.sin(now * .02 + k * 1.7), FX_K.pz - .01);
      t.scale.setScalar(pk.halo * (1 - (k + 1) / (FX_K.trail + 1) * .7)); t.material.opacity = .6 * (1 - k / FX_K.trail);
    });
  }
}

// Moves the camera by the shake's decaying random offset for the scene draw; true if it did (renderFrame then moves the
// backdrop by the same screen offset, and afterwards puts both back, so cam and toScreen stay as computed). Render clock only.
function fxShakeApply() {
  const sh = FX.shake;
  if (!sh.amp) return false;
  const a = sh.amp * Math.max(0, sh.until - FX.now) / sh.dur;
  camera.position.x += (fxRand() * 2 - 1) * a; camera.position.y += (fxRand() * 2 - 1) * a;
  camera.updateMatrixWorld();
  return true;
}

// The fighters changed sides (renderCast): every fighter back to its own colours and size, no flash or squash carried over.
function fxRecast() {
  if (!FX.built) return;
  for (const it of Object.values(F3D_BY)) {
    if (!it.em0) it.em0 = Object.values(it.mats).map(m => m.emissive.clone());
    Object.values(it.mats).forEach((m, k) => m.emissive.copy(it.em0[k]));
    it.root.scale.set(1, 1, 1);
  }
  for (const d of FX.side) { d.fon = d.son = false; d.f = [0, 0]; d.s = [0, 0]; }
}
