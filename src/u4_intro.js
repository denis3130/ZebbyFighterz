// The opening (spec §3, «Intro»; redone for Denis: «che si avvicinino e si dessero quel pugno», no close-ups). Ren dashes
// in from the left and Kael from the right, their fists charged; they face off, draw back and lunge; the fists meet:
// a white flash, an impact frame (black figures on white), shock rings, lightning, sparks and rocks, a hard shake; a
// slow-motion hold while the two energies (Ren's orange, Kael's violet) push against each other; the light swells into a
// white-out; the logo slams in where the title has it, the title's scene shows through, and the title follows.
// The fighters are the two halves of the reference clash (tools/make_ui_assets.py: intro_ren / intro_kael, placed in the
// panel by CFG.ui.intro): at the hit they rebuild the reference picture. The effects are drawn on two canvases, behind and
// in front of the fighters, at most 1.5 pixels per CSS pixel.
// introAt(ms) sets the whole scene for that time, a pure function of ms (sparks, rocks and lightning come from seeded
// numbers), with no CSS animation (see u3_layers.js); the screen's clock advances only on shown frames. «Salta» skips at
// any time; after the first viewing any key, button or tap does.
// The filmed opening (CFG.ui.intro.video) plays instead when its clip is ready: mode 'wait' (the clip is still loading, the
// screen stays dark and the clock still), 'video' (the clip, then the white-out and the drawn logo) or 'drawn' (the
// sequence below). vid = the <video>, vok = its first frame is ready.
const INTRO = {t: 0, last: 0, el: {}, w: 0, h: 0, dpr: 1, q: 1, scene: null, spr: [null, null], ghostA: 0, vid: null, vok: false, mode: 'drawn', waited: 0};
const IN_SHOTS = [[0, 'dark'], [250, 'rush'], [1300, 'impact'], [1700, 'hold'], [3500, 'burst'], [3900, 'logo']];
// the beats (ms): the dash in, face to face, the draw back, the hit, the end of the freeze, the impact frame, the hold,
// the burst, the white-out, the letters, the title's scene showing through
const IN_T = {in0: 250, in1: 650, face: 1000, pull: 1080, hit: 1300, imp0: 1350, imp1: 1440, freeze: 1420, hold: 1700, burst: 3500, white: 3900, logo: 4000, title: 4650};
const IN_GHOSTS = [[34, .5], [68, .3], [102, .16]];    // afterimages: how many ms behind, opacity at full speed (drawn on the back canvas)
const IN_COL = ['#ff9a3c', '#a77bff'];                 // Ren's energy, Kael's
const IN_QN = {alta: 1, media: .6, bassa: .3};          // share of the particles per quality
const inK = (t, a, b) => Math.max(0, Math.min(1, (t - a) / (b - a)));   // progress of t through [a, b]
const inOut = x => 1 - (1 - x) * (1 - x) * (1 - x);                    // ease out
const inIn = x => x * x * x;                                            // ease in
const inR = (i, k) => { const s = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return s - Math.floor(s); };   // seeded 0..1
const inA = (hex, a) => 'rgba(' + parseInt(hex.slice(1, 3), 16) + ',' + parseInt(hex.slice(3, 5), 16) + ',' + parseInt(hex.slice(5, 7), 16) + ',' + a + ')';

function introBuild(r) {
  const C = CFG.ui.intro, A = k => ASSETS['ui/' + k + '.webp'] || '';
  r.innerHTML = '<div class="inStage"><i class="inSky"></i><i class="inSplit"><i class="inWarm"></i><i class="inCool"></i></i><canvas class="inBack"></canvas>' +
    '<div class="inPanel"><i class="inF r"></i><i class="inF k"></i></div><canvas class="inFront"></canvas><i class="inVig"></i></div>' +
    '<i class="inTitleBg"></i><i class="inFlash"></i><div class="inLogoBox"><i class="inHalo"></i><div class="ulogo l"><svg class="ulogoArc" viewBox="0 0 100 100" aria-hidden="true">' +
    '<path d="M70 8a44 44 0 1 1-52 64" pathLength="100"/></svg><span class="ulogoTx">' + 'VOIDRISE'.split('').map(c => '<b>' + c + '</b>').join('') +
    '</span><i class="ulogoCut"></i></div></div>';
  const q = s => r.querySelector(s), E = INTRO.el;
  E.stage = q('.inStage'); E.sky = q('.inSky'); E.split = q('.inSplit'); E.vig = q('.inVig');
  E.back = q('.inBack'); E.front = q('.inFront'); E.bc = E.back.getContext('2d'); E.fc = E.front.getContext('2d'); E.panel = q('.inPanel');
  E.ren = q('.inF.r'); E.kael = q('.inF.k');
  E.titleBg = q('.inTitleBg'); E.flash = q('.inFlash'); E.logo = q('.inLogoBox'); E.halo = q('.inHalo'); E.letters = [...r.querySelectorAll('.ulogoTx b')];
  E.arc = q('.ulogoArc path'); E.cut = q('.ulogoCut');
  E.sky.style.backgroundImage = 'url(' + A('sky') + ')';
  // each half in its place in the panel, turning around its fist
  const put = (el, b, f, img) => { const w = b[2] - b[0], h = b[3] - b[1];
    Object.assign(el.style, {left: b[0] * 100 + '%', top: b[1] * 100 + '%', width: w * 100 + '%', height: h * 100 + '%', backgroundImage: 'url(' + img + ')',
      transformOrigin: ((f[0] - b[0]) / w * 100).toFixed(2) + '% ' + ((f[1] - b[1]) / h * 100).toFixed(2) + '%'}); };
  put(E.ren, C.ren, C.fist.ren, A('intro_ren')); put(E.kael, C.kael, C.fist.kael, A('intro_kael'));
  // the afterimages: each fighter as a flat silhouette in his energy's colour, made once at a third of the size and drawn
  // on the back canvas (no extra big layers to move on the phone)
  [A('intro_ren'), A('intro_kael')].forEach((src, s) => {
    if (!src) return;
    const img = new Image();
    img.onload = () => { const c = document.createElement('canvas'), g = c.getContext('2d');
      c.width = Math.max(1, Math.round(img.naturalWidth / 3)); c.height = Math.max(1, Math.round(img.naturalHeight / 3));
      g.drawImage(img, 0, 0, c.width, c.height); g.globalCompositeOperation = 'source-in'; g.fillStyle = s ? '#9b6bff' : '#ff8a33'; g.fillRect(0, 0, c.width, c.height);
      INTRO.spr[s] = c; };
    img.src = src;
  });
  E.stage.style.transformOrigin = '50% ' + C.hitY * 100 + '%';
  inVideoBuild();
  INTRO.w = 0;
  const skip = cBtn({label: 'Salta', kind: 'small', act: () => introSkip()});
  skip.classList.add('inSkip');
  r.appendChild(skip);
}
// The canvases and the panel follow the screen's size.
function inSize() {
  const w = innerWidth, h = innerHeight, dpr = Math.min(window.devicePixelRatio || 1, 1.5), E = INTRO.el;
  if (w === INTRO.w && h === INTRO.h && dpr === INTRO.dpr) return;
  INTRO.w = w; INTRO.h = h; INTRO.dpr = dpr; INTRO.bdpr = Math.min(dpr, 1);   // the back canvas only has soft lights and silhouettes
  E.back.width = Math.round(w * INTRO.bdpr); E.back.height = Math.round(h * INTRO.bdpr);
  E.front.width = Math.round(w * dpr); E.front.height = Math.round(h * dpr);
  const G = inGeo(), C = CFG.ui.intro;
  Object.assign(E.panel.style, {width: G.pw.toFixed(1) + 'px', height: G.ph.toFixed(1) + 'px', left: (G.cx - C.hit[0] * G.pw).toFixed(1) + 'px', top: (G.cy - C.hit[1] * G.ph).toFixed(1) + 'px'});
}
// The panel on screen (px): its height and width, where the fists meet; inAt = a point of the panel (fractions) on screen.
// On screens narrower than 16:9 (a tablet) the panel shrinks so both faces stay in view.
function inGeo() { const C = CFG.ui.intro, ph = C.panelH * INTRO.h * Math.min(1, INTRO.w / INTRO.h / 1.75); return {ph, pw: ph * C.aspect, cx: INTRO.w / 2, cy: C.hitY * INTRO.h, w: INTRO.w, h: INTRO.h}; }
const inAt = (G, u, v) => [G.cx + (u - CFG.ui.intro.hit[0]) * G.pw, G.cy + (v - CFG.ui.intro.hit[1]) * G.ph];
// Effect time: ms after the hit, slowed down during the hold.
const inFx = t => t < IN_T.hold ? t - IN_T.hit : IN_T.hold - IN_T.hit + .35 * (t - IN_T.hold);

// Where a fighter (0 Ren, 1 Kael) is at time t: g = how far from the hit (panel widths), y = how much higher (panel heights,
// negative = up), r = tilt (deg, around the fist). Kael comes in a little after Ren.
function inPose(t, side) {
  const T = IN_T, d = side ? 60 : 0, bob = x => .006 * Math.sin(x / (side ? 150 : 170));
  if (t < T.in1 + d) { const k = inOut(inK(t, T.in0 + d, T.in1 + d)); return {g: .6 - .5 * k, y: -.05 * (1 - k), r: (side ? 6 : -6) * (1 - k)}; }   // the dash in
  if (t < T.face) return {g: .1 - .015 * inK(t, T.in1 + d, T.face), y: bob(t - T.in1 - d), r: 0};                                                  // face to face
  if (t < T.pull) return {g: .085 + .02 * inOut(inK(t, T.face, T.pull)), y: bob(T.face - T.in1 - d) * (1 - inK(t, T.face, T.pull)), r: 0};          // drawing back
  if (t < T.hit) return {g: .105 * (1 - inIn(inK(t, T.pull, T.hit))), y: 0, r: 0};                                                                 // the lunge
  if (t < T.freeze) return {g: 0, y: 0, r: 0};                                                                                                   // the hit
  // the blast pushes them apart a little, they press in again, trembling while the energies push
  const g = .014 * inOut(inK(t, T.freeze, T.freeze + 140)) * (1 - inOut(inK(t, T.freeze + 200, T.hold + 300)));
  return {g: g + (t < T.white ? .0018 * (inR(Math.floor(t / 33), side + 7) - .5) * inK(t, T.freeze, T.hold) : 0), y: 0, r: 0};
}
// How fast the fighters move (0..1): drives the afterimages, the speed lines and the trails.
function inSpeed(t, side) { return Math.min(1, Math.abs(inPose(t, side).g - inPose(t - 16, side).g) / 16 / .0012); }

// Style writes only when the value changes (a still layer is left alone).
function inOp(el, v) { const s = v.toFixed(3); if (el._op !== s) { el._op = s; el.style.opacity = s; } }
function inBg(el, v) { const s = v.toFixed(3); if (el._bg !== s) { el._bg = s; el.style.backgroundColor = 'rgba(7,6,11,' + s + ')'; } }
function inPiece(el, box, side, p, op) {
  const w = box[2] - box[0], h = box[3] - box[1];
  el.style.opacity = op.toFixed(3);
  el.style.transform = 'translate(' + ((side ? p.g : -p.g) / w * 100).toFixed(3) + '%,' + (p.y / h * 100).toFixed(3) + '%) rotate(' + p.r.toFixed(2) + 'deg)';
}

// --- drawing helpers (canvas, CSS pixels) ---
// A soft round light (core = share of the radius at full strength), drawn from a sprite made once per colour and core:
// a scaled picture costs a phone much less than a gradient computed for every pixel.
const IN_GLOW = {};
function inGlowSprite(col, core) {
  const k = col + '/' + (core || 0);
  if (IN_GLOW[k]) return IN_GLOW[k];
  const c = IN_GLOW[k] = document.createElement('canvas'), g = c.getContext('2d'), r = 128;
  c.width = c.height = 2 * r;
  const gr = g.createRadialGradient(r, r, 0, r, r, r);
  gr.addColorStop(0, col); if (core) gr.addColorStop(core, col); gr.addColorStop(1, inA(col, 0));
  g.fillStyle = gr; g.fillRect(0, 0, 2 * r, 2 * r);
  return c;
}
function inGlow(c, x, y, r, col, a, core) {
  if (a <= .003 || r <= .5) return;
  c.globalAlpha = Math.min(1, a); c.drawImage(inGlowSprite(col, core), x - r, y - r, 2 * r, 2 * r);
}
function inHalf(c, G, side, fn) { c.save(); c.beginPath(); c.rect(side ? G.cx : G.cx - 2 * G.w, -G.h, G.w * 2, G.h * 3); c.clip(); fn(); c.restore(); }   // only one side of the hit
function inOrb(c, x, y, h, col, k, e) {         // a charged fist: a white core in a coloured glow (k = charge, about 0..1.6)
  if (k <= 0) return;
  const f = .88 + .24 * inR(e, 5), a = Math.min(1, k);
  inGlow(c, x, y, h * (.13 + .07 * k) * f, col, .5 * a);
  inGlow(c, x, y, h * (.065 + .02 * k) * f, col, .9 * a, .25);
  inGlow(c, x, y, h * (.048 + .012 * k), '#fff8ee', a, .5);
}
function inBolt(c, x, y, ang, len, seed, w, col, a) {   // a lightning bolt from (x, y), jagged, with a glow and a branch
  const n = 8, ca = Math.cos(ang), sa = Math.sin(ang), pts = [[x, y]];
  for (let i = 1; i <= n; i++) { const d = len * i / n, j = (inR(seed, i) - .5) * len * (i === n ? .08 : .26); pts.push([x + ca * d - sa * j, y + sa * d + ca * j]); }
  const line = p => { c.beginPath(); c.moveTo(p[0][0], p[0][1]); for (const q of p) c.lineTo(q[0], q[1]); };
  const br = 3 + Math.floor(inR(seed, 20) * 3), ba = ang + (inR(seed, 21) - .5) * 1.6, bl = len * .4, bp = [pts[br]];
  for (let i = 1; i <= 4; i++) { const d = bl * i / 4, j = (inR(seed, 30 + i) - .5) * bl * .3; bp.push([pts[br][0] + Math.cos(ba) * d - Math.sin(ba) * j, pts[br][1] + Math.sin(ba) * d + Math.cos(ba) * j]); }
  for (const p of [pts, bp]) {
    line(p); c.globalAlpha = .32 * a; c.strokeStyle = col; c.lineWidth = w * 5; c.stroke();
    c.globalAlpha = a; c.strokeStyle = '#fffdf6'; c.lineWidth = p === pts ? w : w * .6; c.stroke();
  }
}
// A shock ring (an ellipse around the hit): its left half in Ren's colour, the right in Kael's; half = 'top' (behind the
// fighters), 'bottom' (in front) or 'all'.
function inRing(c, x, y, rx, ry, lw, a, half) {
  const P = Math.PI, parts = half === 'top' ? [[P, 1.5 * P, 0], [1.5 * P, 2 * P, 1]] : half === 'bottom' ? [[0, .5 * P, 1], [.5 * P, P, 0]] : [[.5 * P, 1.5 * P, 0], [-.5 * P, .5 * P, 1]];
  if (a <= .003) return;
  for (const [a0, a1, s] of parts) {
    c.beginPath(); c.ellipse(x, y, rx, ry, 0, a0, a1);
    c.globalAlpha = a * .5; c.strokeStyle = IN_COL[s]; c.lineWidth = lw * 2.8; c.stroke();
    c.globalAlpha = a; c.strokeStyle = '#fff6e6'; c.lineWidth = lw; c.stroke();
  }
}
// Focus lines toward the hit: thin wedges coming in from beyond the edges, flickering with the epoch e.
function inLines(c, G, e, n, a, col, r0) {
  if (a <= .003) return;
  const D = Math.hypot(G.w, G.h);
  c.globalAlpha = Math.min(1, a); c.fillStyle = col; c.beginPath();
  for (let i = 0; i < n; i++) {
    if (inR(e, i) < .25) continue;
    const ang = (i + inR(e, i + 50)) / n * 6.2832, ri = D * (r0 + .22 * inR(e, i + 100)), wd = D * (.003 + .009 * inR(e, i + 150)), ca = Math.cos(ang), sa = Math.sin(ang);
    c.moveTo(G.cx + ca * ri, G.cy + sa * ri); c.lineTo(G.cx + ca * D - sa * wd, G.cy + sa * D + ca * wd); c.lineTo(G.cx + ca * D + sa * wd, G.cy + sa * D - ca * wd); c.closePath();
  }
  c.fill();
}
// Sparks: streaks along their path, Ren's colour on his side, Kael's on the other. born(i) / life(i) in effect ms.
function inSparks(c, G, fx, list, w) {
  for (const s of [0, 1]) {
    c.beginPath();
    for (const p of list) if (p.s === s) { c.moveTo(p.x0, p.y0); c.lineTo(p.x1, p.y1); }
    c.globalAlpha = .55; c.strokeStyle = IN_COL[s]; c.lineWidth = w * 2.6; c.stroke();
    c.globalAlpha = .95; c.strokeStyle = '#fff4e2'; c.lineWidth = w; c.stroke();
  }
}
// The spark at age ms (effect time), thrown from (x, y) at angle ang and speed v (screen heights per s), falling.
function inSpark(G, x, y, ang, v, age, life, flat) {
  const pos = a => { const s = a / 1000, sp = v * G.h; return [x + Math.cos(ang) * sp * s, y + Math.sin(ang) * sp * s * flat + .45 * G.h * s * s]; };
  const p1 = pos(age), p0 = pos(Math.max(0, age - 24));
  return {x0: p0[0], y0: p0[1], x1: p1[0], y1: p1[1], s: p1[0] < G.cx ? 0 : 1, a: 1 - age / life};
}
function inRock(c, x, y, r, rot, seed, lit, a, lx, ly) {    // a rock: an irregular dark stone, lit on the side toward (lx, ly)
  if (a <= .01) return;
  const shape = (k, ox, oy) => { c.beginPath();
    for (let i = 0; i < 7; i++) { const an = rot + (i + .4 * inR(seed, i + 9)) / 7 * 6.2832, rr = r * k * (.5 + .6 * inR(seed, i)); c[i ? 'lineTo' : 'moveTo'](x + ox + Math.cos(an) * rr, y + oy + Math.sin(an) * rr); }
    c.closePath(); };
  const d = Math.hypot(lx - x, ly - y) || 1;
  c.globalAlpha = a; shape(1, 0, 0); c.fillStyle = '#1b1520'; c.fill();
  c.globalAlpha = a * .7; shape(.6, (lx - x) / d * r * .3, (ly - y) / d * r * .3); c.fillStyle = lit; c.fill();
}

// --- the filmed opening ---
// The clip is embedded in the page as a data URI; the <video> plays it from a blob (Safari does not play a long data URI
// inline). Muted and inline, so phones play it without a tap. It sits in the stage, under the canvases and the flash.
function inVideoBuild() {
  const src = ASSETS['ui/video/intro.mp4'], E = INTRO.el;
  if (!src || !CFG.ui.intro.video || INTRO.vid) return;
  const v = document.createElement('video');
  v.className = 'inVideo'; v.muted = true; v.defaultMuted = true; v.playsInline = true; v.preload = 'auto';
  v.setAttribute('muted', ''); v.setAttribute('playsinline', ''); v.setAttribute('webkit-playsinline', ''); v.setAttribute('aria-hidden', 'true');
  v.addEventListener('loadeddata', () => { INTRO.vok = true; });
  try {
    const b = atob(src.slice(src.indexOf(',') + 1)), u = new Uint8Array(b.length);
    for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
    v.src = URL.createObjectURL(new Blob([u], {type: 'video/mp4'}));
  } catch (e) { return; }
  E.stage.insertBefore(v, E.stage.firstChild);
  E.vid = INTRO.vid = v;
  v.load();
  // a hidden page stops the clip (the intro's clock stops too: frames are not drawn)
  document.addEventListener('visibilitychange', () => { if (document.hidden && !v.paused) v.pause(); });
}
// The whole filmed opening (ms): the clip, the white-out, then the drawn intro from its white-out to its end.
const inVideoTotal = () => { const V = CFG.ui.intro.video; return (INTRO.vlen || V.len) + V.white + CFG.ui.intro.len - IN_T.white; };
// The time in the drawn intro that a moment of the filmed one shows (only its end is drawn: the white-out and the logo).
const inVideoDrawn = t => { const V = CFG.ui.intro.video; return IN_T.white + t - (INTRO.vlen || V.len) - V.white; };
// The filmed opening at time t: the clip (kept on time by seeking only when it drifts), a flash and a shake when the fists
// land, a white-out over its last frame, then the drawn intro's logo over the dark.
function introVideoAt(t) {
  const V = CFG.ui.intro.video, E = INTRO.el, v = INTRO.vid, L = INTRO.vlen || V.len;
  if (t >= inVideoTotal()) { introEnd(true); return; }
  INTRO.t = t;
  if (t >= L + V.white) {                                  // the logo: the drawn intro's end, the clip gone
    if (!v.paused) v.pause();
    inOp(v, 0);
    introAt(inVideoDrawn(t), true);
    return;
  }
  inSize();
  const root = NAV.screens.intro.root, shot = t < L ? 'film' : 'burst';
  if (root.dataset.shot !== shot) { root.dataset.shot = shot; root.className = root.className.replace(/\bs-\w+/g, '').trim() + ' s-' + shot; }
  if (root.classList.contains('imp')) root.classList.remove('imp');
  if (INTRO.scene !== 'intro') { INTRO.scene = 'intro'; layersSet('intro', {}); }
  inOp(v, 1);
  if (t < L) { if (Math.abs(v.currentTime * 1000 - t) > 120) v.currentTime = t / 1000; }
  else if (!v.paused) v.pause();
  inOp(E.sky, 0); inOp(E.split, 0); for (const el of [E.ren, E.kael, E.logo, E.titleBg, E.halo]) el.style.opacity = '0';
  inBg(E.stage, 1); inOp(E.vig, .55);
  // the hit: a white flash and a hard shake, fading; then the white-out over the last frame
  const k = inK(t, V.hit, V.hit + 300), e33 = Math.floor(t / 33), H = INTRO.h;
  const flash = t >= L ? inIn(inK(t, L, L + V.white)) : t >= V.hit ? .85 * (1 - inOut(k)) : 0;
  E.flash.style.opacity = flash.toFixed(3);
  const sh = t >= V.hit && t < L ? .02 * (1 - inK(t, V.hit, V.hit + 450)) : 0;
  E.stage.style.transform = 'translate(' + (sh * (inR(e33, 1) - .5) * 2 * H).toFixed(2) + 'px,' + (sh * (inR(e33, 2) - .5) * 2 * H).toFixed(2) + 'px) scale(' + (1.04 + .03 * (1 - inOut(k)) * (t >= V.hit ? 1 : 0)).toFixed(4) + ')';
  // the canvases: only focus lines toward the impact, for a moment
  const G = inGeo(), dpr = INTRO.dpr, fc = E.fc, bc = E.bc;
  for (const c of [bc, fc]) { const kk = c === bc ? INTRO.bdpr : dpr; c.setTransform(kk, 0, 0, kk, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.clearRect(0, 0, G.w, G.h); }
  if (t >= V.hit && t < V.hit + 350) { fc.globalCompositeOperation = 'lighter'; inLines(fc, {...G, cy: G.h * .45}, Math.floor(t / 40), Math.round(44 * Math.max(INTRO.q, .5)), .55 * (1 - k), '#fff4e6', .18); }
}

// --- the scene at time t (ms since the intro started) ---
// fromVideo = the filmed opening draws its end with this (its time is already the drawn intro's)
function introAt(t, fromVideo) {
  if (NAV.cur !== 'intro') return;
  if (!fromVideo && INTRO.mode === 'video') { introVideoAt(t); return; }
  if (!fromVideo && INTRO.mode === 'wait') {   // the clip is still loading: only the dark (a second viewing must not show the last one's logo)
    INTRO.t = 0; const E = INTRO.el;
    inOp(E.sky, 0); inOp(E.split, 0); for (const el of [E.ren, E.kael, E.logo, E.titleBg, E.flash, E.halo]) el.style.opacity = '0';
    inBg(E.stage, 1); return;
  }
  if (t >= CFG.ui.intro.len) { introEnd(true); return; }
  if (INTRO.vid && !fromVideo) inOp(INTRO.vid, 0);
  if (!fromVideo) INTRO.t = t;
  inSize();
  const E = INTRO.el, root = NAV.screens.intro.root, T = IN_T, C = CFG.ui.intro, G = inGeo(), H = G.h;
  let shot = IN_SHOTS[0][1];
  for (const [at, name] of IN_SHOTS) if (t >= at) shot = name;
  if (root.dataset.shot !== shot) { root.dataset.shot = shot; root.className = root.className.replace(/\bs-\w+/g, '').trim() + ' s-' + shot; }
  const imp = t >= T.imp0 && t < T.imp1;    // the impact frame
  if (root.classList.contains('imp') !== imp) root.classList.toggle('imp', imp);
  // the title's scene shows through at the end (the menus' layers fade in under the logo)
  const scene = t >= T.title ? 'title' : 'intro';
  if (INTRO.scene !== scene) { INTRO.scene = scene; layersSet(scene, scene === 'title' ? {hero: 'ren', rival: 'kael', pose: 'vs'} : {}); }

  // the fighters (their afterimages are drawn on the back canvas, below)
  const pR = inPose(t, 0), pK = inPose(t, 1), on = t >= T.in0 && t < T.white ? 1 : 0, spR = inSpeed(t, 0), spK = inSpeed(t, 1);
  inPiece(E.ren, C.ren, 0, pR, on); inPiece(E.kael, C.kael, 1, pK, on);
  // the camera: closes in on the lunge, kicks on the hit, pushes slowly through the hold, rushes into the white; shakes
  let z = 1 + .03 * inK(t, T.in1, T.face) - .01 * inOut(inK(t, T.face, T.pull)) + .16 * inIn(inK(t, T.pull, T.hit)), rot = 0, sh = 0;
  if (t >= T.hit) {
    z = 1.12 + .1 * (1 - inOut(inK(t, T.hit, T.hit + 260))) + .08 * inK(t, T.hold, T.burst) + .3 * inIn(inK(t, T.burst, T.white));
    rot = -1.2 * inOut(inK(t, T.freeze, T.hold + 800));
    sh = .024 * (1 - inK(t, T.hit, T.hit + 520)) + .0022 * inK(t, T.freeze, T.hold) + .018 * inIn(inK(t, T.burst, T.white));
  }
  if (t >= T.white) { z = 1; rot = 0; sh = 0; }
  const e33 = Math.floor(t / 33);
  E.stage.style.transform = 'translate(' + (sh * (inR(e33, 1) - .5) * 2 * H).toFixed(2) + 'px,' + (sh * (inR(e33, 2) - .5) * 2 * H).toFixed(2) + 'px) rotate(' + rot.toFixed(3) + 'deg) scale(' + z.toFixed(4) + ')';
  // the sky: out of the dark, lit by the hold's energies (Ren's warm side, Kael's cold side), dimmed under the logo, then
  // gone as the title's scene shows through
  const lit = t < T.hit ? .42 * inK(t, 0, 500) : t < T.white ? .55 + .12 * inR(Math.floor(t / 50), 3) * inK(t, T.hold, T.hold + 1) : .45;
  const out = 1 - inK(t, T.title, T.title + 500);
  inOp(E.sky, lit * out);
  inBg(E.stage, out);   // the dark under everything, gone as the title's scene shows through
  inOp(E.split, t >= T.hit && t < T.white ? .78 * inOut(inK(t, T.freeze, T.hold + 300)) * (.88 + .24 * inR(Math.floor(t / 50), 4)) : 0);   // the two energies' light, flickering
  inOp(E.vig, out);
  E.titleBg.style.opacity = inK(t, T.title, T.title + 500).toFixed(3);
  // white: the flash of the hit, after the impact frame a fading glare, the white-out, fading into the logo
  const flash = t >= T.hit && t < T.imp0 ? 1 : t >= T.imp1 && t < T.hold ? .7 * (1 - inOut(inK(t, T.imp1, T.imp1 + 200))) :
    t >= T.burst && t < T.white ? inIn(inK(t, T.burst, T.white)) : t >= T.white ? 1 - inOut(inK(t, T.white, T.white + 450)) : 0;
  E.flash.style.opacity = flash.toFixed(3);

  // --- the canvases ---
  const n = INTRO.q, bc = E.bc, fc = E.fc, dpr = INTRO.dpr, fx = inFx(t), e50 = Math.floor(t / 50);
  for (const c of [bc, fc]) { const k = c === bc ? INTRO.bdpr : dpr; c.setTransform(k, 0, 0, k, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.clearRect(0, 0, G.w, G.h); c.lineJoin = c.lineCap = 'round'; }
  bc.globalCompositeOperation = fc.globalCompositeOperation = 'lighter';
  const fR = inAt(G, C.fist.ren[0] - pR.g, C.fist.ren[1] + pR.y), fK = inAt(G, C.fist.kael[0] + pK.g, C.fist.kael[1] + pK.y);
  // the afterimages, behind the fighters: where each fighter was a few ms ago, as a silhouette in his colour
  INTRO.ghostA = 0;
  for (const [s, sp, box, fist] of [[0, spR, C.ren, C.fist.ren], [1, spK, C.kael, C.fist.kael]]) {
    const spr = INTRO.spr[s];
    if (!on || sp < .02 || !spr) continue;
    for (const [lag, a] of IN_GHOSTS) {
      const p = inPose(t - lag, s), dx = (s ? p.g : -p.g) * G.pw, dy = p.y * G.ph, [fx0, fy0] = inAt(G, fist[0], fist[1]), [x0, y0] = inAt(G, box[0], box[1]);
      bc.save(); bc.globalCompositeOperation = 'source-over'; bc.globalAlpha = a * sp; INTRO.ghostA = Math.max(INTRO.ghostA, a * sp);
      bc.translate(fx0 + dx, fy0 + dy); bc.rotate(p.r * Math.PI / 180); bc.translate(-fx0, -fy0);
      bc.drawImage(spr, x0, y0, (box[2] - box[0]) * G.pw, (box[3] - box[1]) * G.ph); bc.restore();
    }
  }
  if (t < T.hit) {
    // behind: the two lights coming from the edges, the speed lines, each fighter's trail and aura
    const come = inK(t, 0, 300) * (1 - inK(t, T.in0, T.in0 + 300));
    inGlow(bc, 0, G.cy, H * (.25 + .3 * come), IN_COL[0], .7 * come); inGlow(bc, G.w, G.cy, H * (.25 + .3 * come), IN_COL[1], .7 * come);
    const sp = Math.max(spR, spK);
    if (sp > .02) for (let i = 0; i < 30 * n; i++) {     // speed streaks: soft lines of light flying outward from the middle
      const s = i % 2, y = H * (.08 + .84 * inR(i, 61)), len = G.w * (.06 + .16 * inR(i, 63)), ph = (inR(i, 65) + t * (.0016 + .0016 * inR(i, 67))) % 1;
      const x = s ? G.cx + ph * (G.w / 2 + len * 2) : G.cx - ph * (G.w / 2 + len * 2), th = .7 + 1.6 * inR(i, 69);
      bc.save(); bc.translate(x, y); bc.scale(len / th, 1); inGlow(bc, 0, 0, th, s ? '#e4d6ff' : '#ffe0bc', (.25 + .45 * inR(i, 70)) * sp, .3); bc.restore();
    }
    const charge = t < T.in0 ? 0 : .6 + .4 * inK(t, T.in1, T.face) + .5 * inIn(inK(t, T.pull, T.hit));
    for (const [s, f, spd] of [[0, fR, spR], [1, fK, spK]]) {
      const dir = s ? 1 : -1, a = Math.min(1, .25 * charge + .7 * spd);
      bc.save(); bc.translate(f[0] + dir * G.w * .2, f[1] - H * .06); bc.scale(3.2, 1); inGlow(bc, 0, 0, H * .3, IN_COL[s], .45 * a); bc.restore();   // the trail
      inGlow(bc, f[0] + dir * H * .45, f[1] - H * .12, H * .5, IN_COL[s], (.16 + .1 * inR(e50, s)) * Math.min(1, charge));                                // the aura
    }
    // in front: focus lines closing on the fists as they lunge, the charged fists, small crackles around them
    inLines(fc, G, Math.floor(t / 40), Math.round(40 * Math.max(n, .5)), .3 * inK(t, T.pull, T.hit), '#fff1e0', .4);
    inOrb(fc, fR[0], fR[1], H, IN_COL[0], charge, Math.floor(t / 40));
    inOrb(fc, fK[0], fK[1], H, IN_COL[1], charge, Math.floor(t / 40) + 9);
    if (t > T.in1) for (let i = 0; i < 3; i++) {
      const s = i % 2, f = s ? fK : fR, sd = e50 * 7 + i;
      if (inR(sd, 1) < .5) inBolt(fc, f[0], f[1], inR(sd, 2) * 6.2832, H * (.06 + .08 * inR(sd, 3)) * charge, sd, 1.2, IN_COL[s], .8);
    }
  } else if (imp) {
    // the impact frame: black focus lines on the white
    fc.globalCompositeOperation = 'source-over';
    inLines(fc, G, Math.floor(t / 30), Math.round(56 * Math.max(n, .5)), .92, '#140f18', .08);
  } else if (t < T.white) {
    const burst = inIn(inK(t, T.burst, T.white)), hold = inK(t, T.freeze, T.hold);
    // behind: the split light of the two energies, the upper halves of the shock rings, rocks rising in the hold
    const ring = (i, half, c) => {
      const k = inK(fx, i * 80, i * 80 + 650); if (k <= 0 || k >= 1) return;
      const rx = G.w * (.03 + (.62 + .2 * i) * inOut(k)), ry = rx * (i === 1 ? .92 : .3);
      inRing(c, G.cx, G.cy, rx, ry, H * .016 * (1 - k) + 1, Math.pow(1 - k, 1.4), i === 1 ? 'all' : half);
    };
    ring(0, 'top', bc); ring(2, 'top', bc);
    bc.globalCompositeOperation = 'source-over';
    for (let i = 0; i < 9 * n; i++) {
      const s = (t - T.freeze) / 1000, y = H * (.8 + .35 * inR(i, 71)) - H * (.04 + .06 * inR(i, 72)) * s * 1.6, x = G.w * (.06 + .88 * inR(i, 73));
      inRock(bc, x, y, H * (.008 + .016 * inR(i, 74)), s * (inR(i, 75) - .5) * 2, i + 300, IN_COL[x < G.cx ? 0 : 1], .8 * hold * (1 - burst), G.cx, G.cy);
    }
    bc.globalCompositeOperation = 'lighter';
    // in front: the flying rocks and sparks of the hit, the stream of sparks of the hold, the lower halves of the rings,
    // the round ring, the white focus lines fading, the energy sphere, lightning
    const sparks = [];
    for (let i = 0; i < 64 * n; i++) {
      const life = 350 + 650 * inR(i, 21); if (fx > life) continue;
      const sp = inSpark(G, G.cx, G.cy, inR(i, 22) * 6.2832, .55 + 1.5 * inR(i, 23), fx, life, .62); sparks.push(sp);
    }
    if (fx > 380) {
      const j1 = Math.floor((fx - 380) / 26), j0 = Math.max(0, j1 - 30);
      for (let j = j0; j <= j1; j++) {
        if (inR(j, 30) > n) continue;
        const born = 380 + j * 26, life = 300 + 420 * inR(j, 31), age = fx - born; if (age < 0 || age > life) continue;
        const up = inR(j, 32) < .72, ang = (up ? -Math.PI / 2 : Math.PI / 2) + (inR(j, 33) - .5) * (up ? 2.4 : 1.6);
        sparks.push(inSpark(G, G.cx + (inR(j, 34) - .5) * H * .05, G.cy, ang, .3 + .7 * inR(j, 35), age, life, 1));
      }
    }
    inSparks(fc, G, fx, sparks, 1.6);
    ring(0, 'bottom', fc); ring(1, 'all', fc); ring(2, 'bottom', fc);
    fc.globalCompositeOperation = 'source-over';
    for (let i = 0; i < 16 * n; i++) {
      const ang = inR(i, 41) * 6.2832, v = (.35 + .9 * inR(i, 42)) * H, s = fx / 1000, x = G.cx + Math.cos(ang) * v * s, y = G.cy + Math.sin(ang) * v * s * .7 + .3 * H * s * s;
      inRock(fc, x, y, H * (.008 + .02 * inR(i, 43)), s * (inR(i, 44) - .5) * 9, i, IN_COL[Math.cos(ang) < 0 ? 0 : 1], 1 - inK(fx, 900, 1400), G.cx, G.cy);
    }
    fc.globalCompositeOperation = 'lighter';
    inLines(fc, G, Math.floor(t / 40), Math.round(48 * Math.max(n, .5)), .5 * (1 - inK(t, T.imp1, T.hold + 200)) + .5 * burst, '#fff4e6', .1);
    const R = H * (.075 + .012 * Math.sin(t / 47) + .008 * inR(e33, 9) + .03 * hold) * (1 + 7 * burst);
    inHalf(fc, G, 0, () => inGlow(fc, G.cx, G.cy, R * 2.4, IN_COL[0], .75));
    inHalf(fc, G, 1, () => inGlow(fc, G.cx, G.cy, R * 2.4, IN_COL[1], .75));
    inGlow(fc, G.cx, G.cy, R, '#fffaf2', .95, .35);
    fc.save(); fc.translate(G.cx, G.cy); fc.scale(1, .03); inGlow(fc, 0, 0, G.w * .6, '#d8e4ff', .55 + .3 * burst); fc.restore();   // the lens streak
    fc.save(); fc.translate(G.cx, G.cy); fc.scale(.012, 1); inGlow(fc, 0, 0, H * 1.1, '#fff1dc', .35 * hold); fc.restore();          // the seam between the two energies
    const bolts = Math.round((3 + 5 * hold) * Math.max(n, .5));
    for (let i = 0; i < bolts; i++) {
      const sd = e50 * 13 + i; if (inR(sd, 1) < .3) continue;
      const s = inR(sd, 2) < .5 ? 0 : 1, ang = (s ? 0 : Math.PI) + (inR(sd, 3) - .5) * 2.6;
      inBolt(fc, G.cx, G.cy, ang, H * (.18 + .4 * inR(sd, 4)) * (1 + burst), sd, 1.6, IN_COL[s], .95);
    }
  } else {
    // the logo: embers rising over the dark
    for (let i = 0; i < 30 * n; i++) {
      const v = .04 + .05 * inR(i, 81), y = H * (1.05 - ((inR(i, 82) + (t - T.white) / 1000 * v) % 1.1)), x = G.w * inR(i, 83) + Math.sin(t / 700 + i) * H * .02;
      inGlow(bc, x, y, H * (.006 + .006 * inR(i, 84)), '#ffb070', .7 * out);
    }
  }
  // the logo: the letters slam in one after the other (a glow as each lands), the crescent is drawn, the orange cut
  E.logo.style.opacity = t >= T.white ? '1' : '0';
  E.halo.style.opacity = (inK(t, T.logo, T.logo + 300) * (1 - .5 * inK(t, T.logo + 500, T.logo + 1100))).toFixed(3);
  E.letters.forEach((b, i) => {
    const t0 = T.logo + i * 55, k = inK(t, t0, t0 + 170), g = 1 - inK(t, t0 + 120, t0 + 520);
    b.style.opacity = Math.min(1, k * 1.6).toFixed(3);
    b.style.transform = 'scale(' + (1 + 1.4 * (1 - inOut(k))).toFixed(3) + ')';
    b.style.textShadow = k > 0 && g > 0 ? '0 0 ' + (4 + 18 * g).toFixed(1) + 'px rgba(255,190,110,' + (.9 * g).toFixed(2) + ')' : '';
  });
  E.arc.style.strokeDashoffset = (100 - 100 * inOut(inK(t, T.logo + 480, T.logo + 900))).toFixed(1);
  E.cut.style.clipPath = 'inset(0 ' + (100 - 100 * inOut(inK(t, T.logo + 820, T.logo + 1020))).toFixed(1) + '% 0 0)';
}
// The end: to the title (whole = it played to the end: the title keeps the logo still, as the intro left it).
function introEnd(whole) {
  if (NAV.cur !== 'intro') return;
  if (SV) { SV.introSeen = true; saveWrite(); }
  navReset('title', whole ? {fromIntro: true} : {});
}
// once the logo has formed, the title keeps it still
function introSkip() { introEnd((INTRO.mode === 'video' ? inVideoDrawn(INTRO.t) : INTRO.t) >= IN_T.logo + 600); }
// Which opening plays: the filmed one when its clip is ready (wait for it a moment at most), else the drawn one.
function introMode() {
  const V = CFG.ui.intro.video, v = INTRO.vid;
  if (!v || !V || !V.on) return 'drawn';
  if (INTRO.vok) { if (isFinite(v.duration) && v.duration > 1) INTRO.vlen = Math.round(v.duration * 1000); return 'video'; }
  return INTRO.waited < V.wait ? 'wait' : 'drawn';
}
function introStart(mode) {
  INTRO.mode = mode; INTRO.t = 0;
  const v = INTRO.vid;
  if (mode === 'video') { v.currentTime = 0; const p = v.play(); if (p && p.catch) p.catch(() => { if (INTRO.mode === 'video' && INTRO.t < 300) introStart('drawn'); }); }
  else if (v) { v.pause(); inOp(v, 0); }
  introAt(0);
}

function introScreens() {
  navRegister({id: 'intro', scene: 'intro', build: introBuild,
    enter() { INTRO.t = 0; INTRO.last = 0; INTRO.scene = null; INTRO.q = IN_QN[LY.q] || 1; INTRO.waited = 0; introStart(introMode()); },
    leave() { INTRO.scene = null; if (INTRO.vid) { INTRO.vid.pause(); inOp(INTRO.vid, 0); } },
    frame(now) {
      const v = INTRO.vid;
      if (MN.rot) { INTRO.last = now; if (v && !v.paused) v.pause(); return; }   // «Gira il telefono» covers it: the intro waits
      const dt = INTRO.last ? Math.min(100, now - INTRO.last) : 0; INTRO.last = now;
      if (INTRO.mode === 'wait') { INTRO.waited += dt; const m = introMode(); if (m !== 'wait') introStart(m); return; }
      if (INTRO.mode === 'video') {
        const L = INTRO.vlen || CFG.ui.intro.video.len;
        if (INTRO.t < L && v.paused && !v.ended) { const p = v.play(); if (p && p.catch) p.catch(() => {}); }
        // the clip keeps the time while it plays (its own clock), the frames shown keep it after
        if (INTRO.t < L && !v.paused && !v.ended && v.currentTime > 0) { introAt(Math.max(INTRO.t, Math.min(INTRO.t + 100, v.currentTime * 1000))); return; }
      }
      introAt(INTRO.t + dt);
    },
    any() { if (!SV || !SV.introSeen) return false; introSkip(); return true; },
    back() { return false; }});
  titleScreens();
}

// --- The title: the big logo between Ren and Kael, the ruins at dusk, a prompt that follows the device. Any key, button
// or tap goes on: to the name on the first launch, else to the menu. A tap also asks for full screen and landscape.
const TITLE_PROMPT = {touch: 'Tocca per iniziare', kb: 'Premi un tasto', pad: 'Premi A'};
const NAME_KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('');
function uiNameError(v) {
  const N = CFG.ui.name;
  if (v.length < N.min) return 'Usa almeno ' + N.min + ' caratteri';
  if (v.length > N.max) return 'Al massimo ' + N.max + ' caratteri';
  if (!new RegExp(N.re).test(v)) return 'Solo lettere, numeri, spazi, - e _';
  return '';
}
function uiNameProposal() { const p = CFG.ui.name.pool; return p[(Math.random() * p.length) | 0] + (10 + ((Math.random() * 90) | 0)); }
function titleScreens() {
  navRegister({id: 'title', scene: 'title', layers: () => ({hero: 'ren', rival: 'kael', pose: 'vs'}),
    build(r) {
      r.appendChild(cLogo('l'));
      r.appendChild(uiEl('div', 'uprompt', '<i></i><span id="uPrompt"></span><i></i>'));
    },
    enter(p) {   // from the end of the intro the logo is already in its place: no entrance (class keep)
      NAV.screens.title.root.classList.toggle('keep', !!(p && p.fromIntro));
      document.getElementById('uPrompt').textContent = TITLE_PROMPT[NAV.dev] || TITLE_PROMPT.kb;
    },
    frame(now) { document.getElementById('uPrompt').style.opacity = (.8 + .2 * Math.cos(now / 520)).toFixed(3); },   // the prompt breathes (from JS, no CSS animation)
    any(dev) { if (dev === 'touch') mnFullscreen(); if (SV && SV.name) navReset('menu'); else navGo('name'); return true; },
    back() { return false; }});
  // --- The name (first launch; later from the profile): a proposed name already written, an error under the field as it
  // is typed, «Conferma» only for a valid name. With a controller, a grid of letters.
  navRegister({id: 'name', scene: 'menu', layers: () => ({hero: 'ren'}),
    build(r) {
      r.appendChild(cHead('Come ti chiami?', 'Il nome compare nel profilo e nei risultati.'));
      const box = uiEl('div', 'uname', '<label class="unameL" for="uName">Nome</label><input id="uName" class="unameF" type="text" autocomplete="off" autocapitalize="words" spellcheck="false" maxlength="24" enterkeyhint="done"><div class="unameE" id="uNameErr" aria-live="polite"></div>');
      r.appendChild(box);
      const f = box.querySelector('input');
      f.setAttribute('data-focus', '');
      f.uiAct = () => nameConfirm();
      f.addEventListener('input', nameCheck);
      const keys = uiEl('div', 'ukeys');
      keys.id = 'uKeys';
      const put = ch => { f.value = (f.value + ch).slice(0, CFG.ui.name.max); nameCheck(); };
      for (const ch of NAME_KEYS) keys.appendChild(cBtn({label: ch, kind: 'small', act: () => put(ch)}));
      keys.appendChild(cBtn({label: 'Spazio', kind: 'small', act: () => put(' ')}));
      keys.appendChild(cBtn({label: '⌫', kind: 'small', act: () => { f.value = f.value.slice(0, -1); nameCheck(); }}));
      keys.appendChild(cBtn({label: 'Fatto', kind: 'small', act: () => nameConfirm()}));
      r.appendChild(keys);
      const ok = cBtn({label: 'Conferma', kind: 'main', act: () => nameConfirm()});
      ok.classList.add('unameOk');
      r.appendChild(ok);
    },
    enter(p, back) {
      const f = document.getElementById('uName');
      if (!back) f.value = (SV && SV.name) || uiNameProposal();
      nameCheck(); nameGrid();
    },
    frame() { nameGrid(); }});
}
// The grid of letters is there while the controller is the device in use.
function nameGrid() { const r = NAV.screens.name.root; if (r.classList.contains('pad') !== (NAV.dev === 'pad')) r.classList.toggle('pad', NAV.dev === 'pad'); }
function nameCheck() {
  const v = document.getElementById('uName').value.trim(), e = uiNameError(v);
  document.getElementById('uNameErr').textContent = e;
  NAV.screens.name.root.querySelector('.unameOk .ub').classList.toggle('off', !!e);
  return e;
}
function nameConfirm() {
  const f = document.getElementById('uName');
  if (nameCheck()) { f.classList.remove('bad'); void f.offsetWidth; f.classList.add('bad'); return; }
  SV.name = f.value.trim();
  saveWrite();
  f.blur();
  navReset('menu');
}
