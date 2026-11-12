// The layered scene behind the menus (spec §2): sky, drifting clouds, ruins, light rays, two fog bands, the rival and the
// hero, embers on a 2D canvas, a soft vignette. Each layer moves by its own share of a parallax step (CFG.ui.par) as the
// player goes deeper into the menus and back. Everything that moves is driven from JS while a menu is shown (no CSS
// animation keeps running behind a fight); the scene is display:none during a fight. Quality 'bassa' keeps it still.
// Life (Denis: «poco vivo»): the sky drifts like a slow camera, the rays breathe, the characters slide in from their side
// when a scene opens, and the big moments (the VS, the results) throw bursts of sparks on #uiFx, over the screens.
const LY = {el: null, scene: null, depth: 0, q: 'alta', parts: [], last: 0, ctx: null, w: 0, h: 0, dpr: 1, enterAt: -1e9, bursts: [], fx: null, fxOn: false,
  settle() { const e = LY.el; e.classList.add('still'); void e.offsetWidth; e.classList.remove('still'); },
  // 'media' when the device has few cores or little memory (when it says), else 'alta'
  autoQuality(d) { const Q = CFG.ui.q; return (d.cores && d.cores <= Q.lowCores) || (d.mem && d.mem <= Q.lowMem) ? 'media' : 'alta'; }};
const LY_LAYERS = [['lySky', 'sky'], ['lyClouds', 'clouds'], ['lyArena', 'ruins'], ['lyRuins', 'ruins'], ['lyRays', 'ruins'], ['lyFog2', 'fog'], ['lyRival', 'rival'], ['lyFog1', 'fog'], ['lyGlow', 'hero'], ['lyHero', 'hero']];
// per scene: the side each character slides in from (hero, rival: -1 left, +1 right) and how bright the rays are
const LY_ENTER = {menu: [1, 1], title: [-1, 1], versus: [-1, 1], results: [-1, 0]};
const LY_RAYS = {menu: 1, title: .75, versus: .9, select: .7, results: .9};
const uiRand = (i, k) => { const s = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return s - Math.floor(s); };   // seeded 0..1
const LY_PAR = {sky: 'sky', clouds: 'sky', ruins: 'ruins', fog: 'fog', rival: 'ruins', hero: 'hero'};

function layersInit() {
  const e = LY.el = document.getElementById('uiLayers');
  for (const [id] of LY_LAYERS) { const d = document.createElement('div'); d.className = 'ly'; d.id = id; e.appendChild(d); }
  const img = (id, key) => { const v = ASSETS['ui/' + key + '.webp']; if (v) document.getElementById(id).style.backgroundImage = 'url(' + v + ')'; };
  img('lySky', 'sky'); img('lyClouds', 'clouds'); img('lyRuins', 'ruins'); img('lyFog1', 'fog1'); img('lyFog2', 'fog2');
  const c = document.createElement('canvas'); c.id = 'uiParts'; e.appendChild(c);
  const fx = document.getElementById('uiFx'); if (fx) LY.fx = fx.getContext('2d');
  const v = document.createElement('div'); v.className = 'ly'; v.id = 'lyShade'; e.appendChild(v);
  LY.ctx = c.getContext('2d');
  const q = SV && SV.settings.quality !== 'auto' ? SV.settings.quality : LY.autoQuality({cores: navigator.hardwareConcurrency, mem: navigator.deviceMemory});
  layersQuality(q);
  layersSet('menu', {hero: (SV && SV.lastChar) || 'ren'});
}
// A character layer: c = 'ren' | 'kael' | null; pose = which picture: '<c>_<pose>' when there is one ('vs' the big faces of
// the title, 'win' Ren's victory), else '<c>_full' (the menus).
function lyChar(id, c, pose) {
  const el = document.getElementById(id), key = !c ? '' : pose && ASSETS['ui/' + c + '_' + pose + '.webp'] ? 'ui/' + c + '_' + pose + '.webp' : 'ui/' + c + '_full.webp';
  if (el.dataset.k === key) return false;
  el.dataset.k = key; el.dataset.c = c || '';
  el.style.backgroundImage = key && ASSETS[key] ? 'url(' + ASSETS[key] + ')' : 'none';
  // where the face is, for the scenes that place a face (CSS: --ax = its distance from the picture's left edge in picture
  // heights, --ay = its height share)
  const A = CFG.ui.art[key.slice(3, -5)];
  if (A) { el.style.setProperty('--ax', (A[0] * A[1]).toFixed(4)); el.style.setProperty('--ay', A[2]); }
  else { el.style.removeProperty('--ax'); el.style.removeProperty('--ay'); }   // (the CSS's own default then applies)
  return true;
}
// scene: 'menu' | 'title' | 'intro' | 'select' | 'vs' | 'results' | 'off' (CSS places the layers per scene); o = {hero, rival,
// pose, arena (an id: its card picture), arenaImg (a picture: the real arena's snapshot)}. The characters' pictures come only from Denis's interface references (docs/ref/ui/), never the A-pose sheets.
function layersSet(scene, o) {
  o = o || {};
  const moved = LY.scene !== scene;
  LY.scene = scene;
  LY.el.dataset.scene = scene;
  const hero = o.hero || null, rival = o.rival !== undefined ? o.rival : hero ? (hero === 'ren' ? 'kael' : 'ren') : null;
  const changed = lyChar('lyHero', hero, o.pose) | lyChar('lyRival', rival, o.pose);
  if (moved || changed) LY.enterAt = performance.now();   // the characters slide in
  document.getElementById('lyGlow').dataset.c = hero || '';   // the hero's light takes his colour
  const a = document.getElementById('lyArena'), src = o.arenaImg || (o.arena ? ASSETS['ui/arena_' + o.arena + '.webp'] : null);
  if (src) a.style.backgroundImage = 'url(' + src + ')';
  a.classList.toggle('on', !!src);
  lyPlace();
}
// Parallax: the layers' horizontal offset for the current depth in the menus (dir +1 = one screen deeper, -1 = back).
function layersShift(dir) { LY.depth = Math.max(0, Math.min(6, LY.depth + dir)); lyPlace(); }
function layersDepth(d) { LY.depth = d; lyPlace(); }
function lyPlace() {
  const P = CFG.ui.par;
  for (const [id, kind] of LY_LAYERS) document.getElementById(id).style.transform = 'translateX(' + (-LY.depth * P.step * P[LY_PAR[kind]]).toFixed(1) + 'px)';
}
function layersQuality(q) {
  LY.q = q;
  LY.el.classList.remove('q-bassa', 'q-media', 'q-alta');
  LY.el.classList.add('q-' + q);
  const n = CFG.ui.q.parts[q] || 0;
  if (LY.parts.length > n) LY.parts.length = n;
  if (!n && LY.ctx) LY.ctx.clearRect(0, 0, LY.w, LY.h);
}
// The slow motions of the scene, driven from here (only while a menu is shown: no CSS animation is left running behind a
// fight): clouds and fog scrolling at their own speed (seconds per loop, direction), the characters breathing, the
// warm light behind the hero pulsing. 'bassa' keeps everything still.
const LY_DRIFT = [['lyClouds', 150, 1], ['lyFog2', 80, -1], ['lyFog1', 46, 1]];
function lyMotion(now) {
  const s = now / 1000, $ = id => document.getElementById(id);
  for (const [id, period, dir] of LY_DRIFT) { const f = (s / period) % 1; $(id).style.translate = (-(dir > 0 ? f : 1 - f) * 50).toFixed(3) + '% 0'; }
  const breath = (t, p, ph) => (1 + .008 * (1 - Math.cos(6.2832 * (t / p + ph)))).toFixed(4);
  $('lyHero').style.scale = breath(s, 4.6, 0);
  $('lyRival').style.scale = breath(s, 5.3, .17);
  $('lyGlow').style.opacity = LY.scene === 'menu' ? (.7 + .3 * Math.cos(6.2832 * s / 5) * (.8 + .2 * Math.sin(s * 2.3))).toFixed(3) : '0';   // the hero's light: the menu only
  // a slow camera on the sky and on the arena's picture; the rays breathe and sway
  $('lySky').style.scale = (1.05 + .015 * Math.sin(s / 23)).toFixed(4);
  $('lySky').style.translate = (.9 * Math.sin(s / 31)).toFixed(3) + '% ' + (.5 * Math.cos(s / 27)).toFixed(3) + '%';
  $('lyArena').style.scale = (1.04 + .02 * Math.sin(s / 11)).toFixed(4);
  $('lyRays').style.opacity = ((LY_RAYS[LY.scene] || 0) * (.6 + .22 * Math.sin(s / 3.7) + .12 * Math.sin(s * 1.3 + 1))).toFixed(3);
  $('lyRays').style.translate = (1.6 * Math.sin(s / 9)).toFixed(2) + '% 0';
  // the entrance: the characters slide in from their side as the scene opens
  const k = Math.min(1, (now - LY.enterAt) / 650), e = 1 - Math.pow(1 - k, 3), dir = LY_ENTER[LY.scene] || [0, 0];
  $('lyHero').style.translate = (dir[0] * 8 * (1 - e)).toFixed(2) + 'vw 0';
  $('lyRival').style.translate = (dir[1] * 8 * (1 - e)).toFixed(2) + 'vw 0';
}
// A burst of sparks at (x, y) (CSS px), n sparks of colour col, for a big moment; spread scales their speed.
function layersBurst(x, y, n, col, spread) {
  if (!LY.fx) return;
  LY.bursts.push({x, y, t0: performance.now(), n: Math.max(4, Math.round(n * (LY.q === 'bassa' ? .35 : LY.q === 'media' ? .6 : 1))), col: col || '#ffc070', sp: spread || 1, seed: (Math.random() * 997) | 0});
}
// The bursts on #uiFx: shown only while one lives, each spark a pure function of its age (a streak, then a fading dot).
function lyBursts(now) {
  const c = LY.fx;
  if (!c) return;
  const live = LY.bursts.filter(b => now - b.t0 < 1300);
  if (!live.length) { if (LY.fxOn) { LY.fxOn = false; c.canvas.style.display = 'none'; } LY.bursts.length = 0; return; }
  LY.bursts = live;
  const dpr = Math.min(window.devicePixelRatio || 1, 1.5), w = innerWidth, h = innerHeight;
  if (!LY.fxOn) { LY.fxOn = true; c.canvas.style.display = 'block'; }
  if (c.canvas.width !== Math.round(w * dpr) || c.canvas.height !== Math.round(h * dpr)) { c.canvas.width = Math.round(w * dpr); c.canvas.height = Math.round(h * dpr); }
  c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h);
  c.globalCompositeOperation = 'lighter'; c.lineCap = 'round';
  for (const b of live) {
    const a = (now - b.t0) / 1000;
    for (let i = 0; i < b.n; i++) {
      const life = .55 + .6 * uiRand(b.seed, i), k = a / life;
      if (k >= 1) continue;
      const ang = uiRand(b.seed + 1, i) * 6.2832, v = (110 + 420 * uiRand(b.seed + 2, i)) * b.sp * (h / 400), drag = 1 - .45 * a;
      const pos = t => [b.x + Math.cos(ang) * v * t * drag, b.y + Math.sin(ang) * v * t * .8 * drag + 140 * (h / 400) * t * t];
      const p1 = pos(a), p0 = pos(Math.max(0, a - .035));
      c.globalAlpha = (1 - k) * .9; c.strokeStyle = b.col; c.lineWidth = 2.2;
      c.beginPath(); c.moveTo(p0[0], p0[1]); c.lineTo(p1[0], p1[1]); c.stroke();
      c.globalAlpha = (1 - k); c.strokeStyle = '#fff6e6'; c.lineWidth = .9; c.stroke();
    }
  }
  c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
}
// The focused element's life: a button's light sweeps across it again every few seconds, the brush stroke behind the
// focused entry or button breathes.
function uiFocusLife(now) {
  const f = NAV.focus;
  if (!f) return;
  if (f.classList.contains('ub')) {
    const k = Math.floor((now - (NAV.focusAt || 0)) / 3200);
    if (k !== NAV.shineK) { NAV.shineK = k; if (k > 0) { f.classList.remove('shine'); void f.offsetWidth; f.classList.add('shine'); } }
  }
  f.style.setProperty('--br', (.8 + .2 * Math.sin(now / 380)).toFixed(3));
}
// The logo's light: a sweep across the word every few seconds (the logo of the screen shown, if it has one).
function uiLogoLife(d, now) {
  if (d._sh === undefined) d._sh = d.root ? d.root.querySelector('.ulogoSh .ulogoTx') : null;
  const e = d._sh;
  if (!e) return;
  const p = (now % 5200) / 1300;
  if (p < 1) { e.style.backgroundPosition = (125 - 150 * p).toFixed(1) + '% 0'; e.dataset.on = '1'; }
  else if (e.dataset.on) { e.style.backgroundPosition = '125% 0'; e.dataset.on = ''; }
}
// Embers: small warm sparks rising and swaying, drawn added to the scene. Their number follows the quality.
function layersFrame(now) {
  if (LY.scene === 'intro') {   // the layers are hidden under the intro: nothing to move or draw
    if (LY.parts.length) { LY.parts.length = 0; if (LY.ctx) LY.ctx.clearRect(0, 0, LY.w, LY.h); }
    LY.last = now; return;
  }
  if (LY.q !== 'bassa') lyMotion(now);
  const n = CFG.ui.q.parts[LY.q] || 0, c = LY.ctx;
  if (!c) return;
  const dt = Math.min(50, LY.last ? now - LY.last : 16) / 1000;
  LY.last = now;
  const dpr = Math.min(window.devicePixelRatio || 1, 1.5), w = Math.round(innerWidth * dpr), h = Math.round(innerHeight * dpr);
  if (w !== LY.w || h !== LY.h) { c.canvas.width = LY.w = w; c.canvas.height = LY.h = h; LY.dpr = dpr; }
  if (!n) { if (LY.parts.length) { LY.parts.length = 0; c.clearRect(0, 0, w, h); } return; }
  // spawn toward the target, a few per frame, from below the bottom edge
  for (let k = 0; k < 3 && LY.parts.length < n; k++)
    LY.parts.push({x: Math.random() * w, y: h + Math.random() * h * .2, v: (24 + Math.random() * 46) * dpr, r: (.8 + Math.random() * 1.8) * dpr,
      ph: Math.random() * 6.3, sw: (8 + Math.random() * 20) * dpr, life: 1});
  c.clearRect(0, 0, w, h);
  c.globalCompositeOperation = 'lighter';
  for (const p of LY.parts) {
    p.y -= p.v * dt; p.ph += dt * 1.3;
    if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
    const x = p.x + Math.sin(p.ph) * p.sw, f = Math.min(1, p.y / h * 1.4);   // fainter higher up
    c.globalAlpha = .35 + .5 * f;
    c.fillStyle = '#ff9d4a';
    c.beginPath(); c.arc(x, p.y, p.r * 2.4, 0, 6.283); c.globalAlpha *= .25; c.fill();
    c.globalAlpha = .55 + .45 * f; c.fillStyle = '#ffd9a0';
    c.beginPath(); c.arc(x, p.y, p.r, 0, 6.283); c.fill();
  }
  c.globalAlpha = 1;
  c.globalCompositeOperation = 'source-over';
}
// Once per animation frame while a menu is shown: the scene, then the current screen's own clock (intro, VS).
function uiFrame(now) {
  layersFrame(now);
  lyBursts(now);
  const d = navDef();
  if (d && LY.q !== 'bassa') { uiFocusLife(now); uiLogoLife(d, now); }
  if (d && d.frame) d.frame(now);
}
