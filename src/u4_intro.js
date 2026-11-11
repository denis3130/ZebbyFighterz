// The opening (spec §3, «Intro»): a sequence of shots, not frame-by-frame animation. Ren rushes in from the left, Kael
// from the right, the view closes in, their fists clash (white flash, shock ring, shake, flying rocks), a slow-motion
// hold on the clash, a white-out, then the logo forms and the title follows. CFG.ui.intro.len ms in all.
// introAt(ms) sets the whole scene for that time (a pure function of ms: no CSS animation, see u3_layers.js); the
// screen's clock advances only on shown frames (a hidden page does not jump ahead). «Salta» skips at any time; after the
// first viewing any key, button or tap does.
const INTRO = {t: 0, last: 0, el: {}};
const IN_SHOTS = [[0, 'dark'], [600, 'ren'], [2000, 'kael'], [3200, 'close'], [3700, 'impact'], [5000, 'white'], [5600, 'logo']];
const IN_ROCKS = 12;
const inK = (t, a, b) => Math.max(0, Math.min(1, (t - a) / (b - a)));   // progress of t through [a, b]
const inOut = x => 1 - (1 - x) * (1 - x) * (1 - x);                    // ease out
const inIn = x => x * x * x;                                            // ease in

function introBuild(r) {
  const h = '<div class="inStage"><i class="inLines"></i><i class="inRen"></i><i class="inKael"></i><i class="inClash"></i><i class="inRing"></i><div class="inRocks">' +
    '<i></i>'.repeat(IN_ROCKS) + '</div></div><i class="inFlash"></i>' +
    '<div class="inLogo"><svg class="inArc" viewBox="0 0 100 100" aria-hidden="true"><path d="M70 8a44 44 0 1 1-52 64" pathLength="100"/></svg><span class="inWord">' +
    'VOIDRISE'.split('').map(c => '<b>' + c + '</b>').join('') + '</span><i class="inCut"></i></div>';
  r.innerHTML = h;
  const q = s => r.querySelector(s), E = INTRO.el;
  E.stage = q('.inStage'); E.lines = q('.inLines'); E.ren = q('.inRen'); E.kael = q('.inKael'); E.clash = q('.inClash'); E.ring = q('.inRing');
  E.rocks = [...r.querySelectorAll('.inRocks i')]; E.flash = q('.inFlash'); E.logo = q('.inLogo'); E.letters = [...r.querySelectorAll('.inWord b')];
  E.arc = q('.inArc path'); E.cut = q('.inCut');
  E.ren.style.backgroundImage = 'url(' + (ASSETS['ui/ren_full.webp'] || '') + ')';
  E.kael.style.backgroundImage = 'url(' + (ASSETS['ui/kael_full.webp'] || '') + ')';
  E.clash.style.backgroundImage = 'url(' + (ASSETS['ui/intro_clash.webp'] || '') + ')';
  const skip = cBtn({label: 'Salta', kind: 'small', act: () => introSkip()});
  skip.classList.add('inSkip');
  r.appendChild(skip);
}
const inSet = (el, op, tf) => { el.style.opacity = op.toFixed(3); if (tf !== undefined) el.style.transform = tf; };

// The scene at time t (ms since the intro started).
function introAt(t) {
  if (NAV.cur !== 'intro') return;
  if (t >= CFG.ui.intro.len) { introEnd(); return; }
  INTRO.t = t;
  const E = INTRO.el, root = NAV.screens.intro.root;
  let shot = IN_SHOTS[0][1];
  for (const [at, name] of IN_SHOTS) if (t >= at) shot = name;
  if (root.dataset.shot !== shot) { root.dataset.shot = shot; root.className = root.className.replace(/\bs-\w+/g, '').trim() + ' s-' + shot; }
  // the two fighters rush in (vw from the centre), drift, then close in; gone at the impact (the clash picture takes over)
  const ren = -70 + 52 * inOut(inK(t, 600, 1500)) + 4 * inK(t, 1500, 3200) + 8 * inIn(inK(t, 3200, 3700));
  const kael = 70 - 52 * inOut(inK(t, 2000, 2900)) - 4 * inK(t, 2900, 3200) - 8 * inIn(inK(t, 3200, 3700));
  const vis = t >= 600 && t < 3700 ? 1 : 0;
  inSet(E.ren, vis * inK(t, 600, 750), 'translateX(' + ren.toFixed(2) + 'vw)');
  inSet(E.kael, (t >= 2000 && t < 3700 ? 1 : 0) * inK(t, 2000, 2150), 'translateX(' + kael.toFixed(2) + 'vw) scaleX(-1)');
  // speed lines while someone rushes in
  const rush = Math.max(Math.sin(Math.PI * inK(t, 600, 1500)), Math.sin(Math.PI * inK(t, 2000, 2900)), .6 * Math.sin(Math.PI * inK(t, 3200, 3700)));
  inSet(E.lines, .45 * rush, 'translateX(' + (-((t * 1.6) % 240)).toFixed(1) + 'px)');
  // the view: closes in before the impact, shakes on it, a slow push during the hold
  const zoom = 1 + .25 * inIn(inK(t, 3200, 3700)) - .25 * inK(t, 3700, 3720) + .06 * inK(t, 3700, 5000);
  const sh = t >= 3700 && t < 4150 ? 18 * (1 - inK(t, 3700, 4150)) : 0;
  E.stage.style.transform = 'translate(' + (sh * Math.sin(t * .11)).toFixed(2) + 'px,' + (sh * Math.cos(t * .093)).toFixed(2) + 'px) scale(' + zoom.toFixed(4) + ')';
  // the clash picture, the shock ring, the rocks
  inSet(E.clash, t >= 3700 && t < 5600 ? inK(t, 3700, 3820) : 0, 'scale(' + (1 + .06 * inK(t, 3700, 5000)).toFixed(4) + ')');
  const rk = inK(t, 3700, 4250);
  inSet(E.ring, t >= 3700 ? .9 * (1 - rk) : 0, 'translate(-50%,-50%) scale(' + (.15 + 3.2 * inOut(rk)).toFixed(3) + ')');
  const slow = t < 3700 ? 0 : Math.min(t - 3700, 120) + .35 * Math.max(0, t - 3820);   // slow motion after the first instant
  E.rocks.forEach((e, i) => {
    const a = i * 2.39996 + .4, v = .9 + (i % 4) * .35, d = slow * v * .55;
    inSet(e, t >= 3700 && t < 5000 ? 1 - inK(t, 4500, 5000) : 0, 'translate(' + (Math.cos(a) * d).toFixed(1) + 'px,' + (Math.sin(a) * d + .00045 * slow * slow).toFixed(1) + 'px) rotate(' + (slow * (i % 2 ? .6 : -.5)).toFixed(0) + 'deg)');
  });
  // white: the flash of the impact, the white-out before the logo, fading into it
  const flash = t >= 3700 && t < 4000 ? 1 - inK(t, 3700, 3830) : t >= 5000 ? (t < 5600 ? inIn(inK(t, 5000, 5600)) : 1 - inOut(inK(t, 5600, 6050))) : 0;
  inSet(E.flash, flash);
  // the logo: letters one after the other, the crescent drawn, the orange cut
  const lg = t >= 5600;
  E.logo.style.opacity = lg ? '1' : '0';
  E.letters.forEach((b, i) => { const k = inOut(inK(t, 5750 + i * 70, 6100 + i * 70)); inSet(b, k, 'translateY(' + ((1 - k) * 14).toFixed(1) + 'px)'); });
  E.arc.style.strokeDashoffset = (100 - 100 * inOut(inK(t, 5900, 6600))).toFixed(1);
  E.cut.style.transform = 'rotate(-22deg) scaleX(' + inOut(inK(t, 6400, 6750)).toFixed(3) + ')';
}
function introEnd() {
  if (NAV.cur !== 'intro') return;
  if (SV) { SV.introSeen = true; saveWrite(); }
  navReset('title');
}
function introSkip() { introEnd(); }

function introScreens() {
  navRegister({id: 'intro', scene: 'intro', build: introBuild,
    enter() { INTRO.t = 0; INTRO.last = 0; introAt(0); },
    frame(now) { const dt = INTRO.last ? Math.min(100, now - INTRO.last) : 0; INTRO.last = now; introAt(INTRO.t + dt); },
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
    enter() { document.getElementById('uPrompt').textContent = TITLE_PROMPT[NAV.dev] || TITLE_PROMPT.kb; },
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
