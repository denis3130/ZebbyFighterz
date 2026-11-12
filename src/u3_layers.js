// The layered scene behind the menus (spec §2): sky, drifting clouds, ruins, two fog bands, the rival and the hero, embers
// on a 2D canvas, a soft vignette. Each layer moves by its own share of a parallax step (CFG.ui.par) as the player goes
// deeper into the menus and back. CSS animations (clouds and fog scrolling, the hero breathing) use only transform-type
// properties; the scene is display:none during a fight, so it costs nothing there. Quality 'bassa' stops the animations
// and the embers.
const LY = {el: null, scene: null, depth: 0, q: 'alta', parts: [], last: 0, ctx: null, w: 0, h: 0, dpr: 1,
  settle() { const e = LY.el; e.classList.add('still'); void e.offsetWidth; e.classList.remove('still'); },
  // 'media' when the device has few cores or little memory (when it says), else 'alta'
  autoQuality(d) { const Q = CFG.ui.q; return (d.cores && d.cores <= Q.lowCores) || (d.mem && d.mem <= Q.lowMem) ? 'media' : 'alta'; }};
const LY_LAYERS = [['lySky', 'sky'], ['lyClouds', 'clouds'], ['lyArena', 'ruins'], ['lyRuins', 'ruins'], ['lyFog2', 'fog'], ['lyRival', 'rival'], ['lyFog1', 'fog'], ['lyGlow', 'hero'], ['lyHero', 'hero']];
const LY_PAR = {sky: 'sky', clouds: 'sky', ruins: 'ruins', fog: 'fog', rival: 'ruins', hero: 'hero'};

function layersInit() {
  const e = LY.el = document.getElementById('uiLayers');
  for (const [id] of LY_LAYERS) { const d = document.createElement('div'); d.className = 'ly'; d.id = id; e.appendChild(d); }
  const img = (id, key) => { const v = ASSETS['ui/' + key + '.webp']; if (v) document.getElementById(id).style.backgroundImage = 'url(' + v + ')'; };
  img('lySky', 'sky'); img('lyClouds', 'clouds'); img('lyRuins', 'ruins'); img('lyFog1', 'fog1'); img('lyFog2', 'fog2');
  const c = document.createElement('canvas'); c.id = 'uiParts'; e.appendChild(c);
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
  if (el.dataset.k === key) return;
  el.dataset.k = key; el.dataset.c = c || '';
  el.style.backgroundImage = key && ASSETS[key] ? 'url(' + ASSETS[key] + ')' : 'none';
  // where the face is, for the scenes that place a face (CSS: --ax = its distance from the picture's left edge in picture
  // heights, --ay = its height share)
  const A = CFG.ui.art[key.slice(3, -5)];
  if (A) { el.style.setProperty('--ax', (A[0] * A[1]).toFixed(4)); el.style.setProperty('--ay', A[2]); }
}
// scene: 'menu' | 'title' | 'intro' | 'select' | 'vs' | 'results' | 'off' (CSS places the layers per scene); o = {hero, rival,
// pose, arena (an id: its card picture), arenaImg (a picture: the real arena's snapshot)}. The characters' pictures come only from Denis's interface references (docs/ref/ui/), never the A-pose sheets.
function layersSet(scene, o) {
  o = o || {};
  LY.scene = scene;
  LY.el.dataset.scene = scene;
  const hero = o.hero || null, rival = o.rival !== undefined ? o.rival : hero ? (hero === 'ren' ? 'kael' : 'ren') : null;
  lyChar('lyHero', hero, o.pose); lyChar('lyRival', rival, o.pose);
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
  const s = now / 1000;
  for (const [id, period, dir] of LY_DRIFT) { const f = (s / period) % 1; document.getElementById(id).style.translate = (-(dir > 0 ? f : 1 - f) * 50).toFixed(3) + '% 0'; }
  const breath = (t, p, ph) => (1 + .006 * (1 - Math.cos(6.2832 * (t / p + ph)))).toFixed(4);
  document.getElementById('lyHero').style.scale = breath(s, 4.6, 0);
  document.getElementById('lyRival').style.scale = breath(s, 5.3, .17);
  document.getElementById('lyGlow').style.opacity = (.775 + .225 * Math.cos(6.2832 * s / 5)).toFixed(3);
}
// Embers: small warm sparks rising and swaying, drawn added to the scene. Their number follows the quality.
function layersFrame(now) {
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
  const d = navDef();
  if (d && d.frame) d.frame(now);
}
