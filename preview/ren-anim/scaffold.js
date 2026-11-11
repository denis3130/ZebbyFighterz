// --- Ren's animation layer: the scaffold (viewer proposal, 11/11/2026). Graphics only: the sim's frames are untouched. ---
// The layer is a set of modules (mods/*.js, joined after this file by build.py) that plug into the hooks below.
// RN.on = false draws the original animation (mdSync) with none of this.
//   RN.pose(it, F, S) -> the final pose {q, h} of fighter F for the model item it (may keep blend state on it: when it is
//     called, it.F / it.act / it.af / it.pose still hold the last drawn frame's fighter, act, frame and pose).
//   RN.pure(md, F, S) -> the same without blending or any state: a pure function of F and S, continuous in F.af
//     (fractional frames are valid: the viewer draws between two sim frames, the trail samples sub-frames).
//   RN.moveT(t, m, af, hit) -> optional: a move's clip time (replaces mdMoveT's linear startup and recovery).
// Hooks (arrays of functions):
//   boot(VW)              once, the scene, camera and model are built;
//   hold(VW)              before each sim step: true holds the step (hitstop: nothing moves), another truthy value
//                         means the hook made its own step instead;
//   step(VW)              after each sim step;
//   applied(it, F, S, p)  each drawn frame after the pose is on the bones and before the sash (bone scales, springs);
//   draw(VW, dtMs, cam)   each drawn frame after the camera is placed and before the render;
//   reset(VW)             a play starts from its first step;
//   opt(key, value)       an option changed (rnOpt keys, and 'on' for new/old).
const RN = {on: true, opt: {}, hooks: {boot: [], hold: [], step: [], applied: [], draw: [], reset: [], opt: []}, pose: null, pure: null, moveT: null};
function rnSm(t) { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); }

// The state the viewer draws: with the layer on, a copy of the fighter k of a frame after its last sim step (k in 0..1:
// the pose is a continuous function of the frame, so slow motion and the viewer's own pace show no stepping). The
// fighter moves on as its mode says. S.int = the stepped state (whole frames: what steps physics once per sim frame).
const RN_D = {F: null, S: null};
function rnDrawState(k) {
  if (!RN.on) return VW.S;
  const F = VW.F, D = RN_D.F || (RN_D.F = {}), S = RN_D.S || (RN_D.S = {frame: 0, sides: [{team: [D], cur: 0}], int: VW.S});
  if (k === undefined) k = VW.hold ? RN_D.k || 0 : RN.opt.smooth && VW.speed > 0 ? Math.max(0, Math.min(1, VW.acc / VW_DT)) : 0;   // (held: where it stopped)
  RN_D.k = k;
  Object.assign(D, F);
  D.af = F.af + k; S.frame = VW.S.frame + k; S.k = k;
  if (k) {
    if (F.air) D.y = Math.max(0, F.y + F.vy * k);
    if (VW.mode === 'walkF') D.x += CFG.walk.f * F.face * k;
    else if (VW.mode === 'walkB') D.x -= CFG.walk.b * F.face * k;
    else if (VW.mode === 'dash') D.x += (F.act === 'dashF' ? 1 : -1) * 100 * F.face * k;
  }
  return S;
}

// mdSync with the layer: the same placement and fists, the pose from RN.pose, then the applied hooks and the sash.
function rnSync(it, side, S) {
  if (!RN.on || !RN.pose) return mdSync(it, side, S);
  it.root.visible = !!S;
  if (!S) { it.F = null; return; }
  const F = fighterOf(S, side);
  it.root.position.set(F.x / 1000, F.y / 1000, side ? -.05 : .05);
  it.root.rotation.y = F.face * F3_YAW;
  it.body.scale.x = it.scale * F.face;
  if (it.fingers) {
    const k = CFG.looks[it.key].openHands.includes(F.act) ? 0 : 1;
    if (F !== it.F || F.act !== it.act) it.curl0 = F === it.F ? it.curl : k;
    it.curl = it.curl0 + (k - it.curl0) * Math.min(1, Math.max(0, F.af) / MD_CURL);
    for (let i = 0; i < it.fingers.length; i++) it.fingers[i].quaternion.copy(MD_Q1).slerp(it.fist[i], it.curl);
  }
  const p = RN.pose(it, F, S);
  it.F = F; it.act = F.act; it.af = F.af; it.pose = p;
  mdApply(it, p);
  for (const f of RN.hooks.applied) f(it, F, S, p);
  if (it.sash) mdSash(it, S.int || S);
}

// One sim step of the viewer, unless a hold hook holds it (hitstop).
function vwStep() {
  VW.hold = 0;
  for (const f of RN.hooks.hold) { const r = RN.on && f(VW); if (r) { VW.hold = r === true ? 1 : 0; return; } }   // true: frozen (hitstop); other: the hook stepped something itself
  vwStep0();
  if (RN.on) for (const f of RN.hooks.step) f(VW);
}
function rnReset() { VW.hold = 0; for (const f of RN.hooks.reset) f(VW); }

// An on/off option of the layer as a button of the viewer's options row: RN.opt[key], def at the start.
function rnOpt(key, label, def) {
  RN.opt[key] = def;
  const row = document.getElementById('rnOpts'), b = document.createElement('button');
  if (!row) return;
  b.id = 'opt_' + key; b.innerHTML = '<span>' + label + '</span>'; b.setAttribute('aria-pressed', def ? 'true' : 'false');
  b.addEventListener('click', () => rnSet(key, !RN.opt[key]));
  row.appendChild(b);
}
function rnSet(key, v) {
  RN.opt[key] = v;
  const b = document.getElementById('opt_' + key);
  if (b) b.setAttribute('aria-pressed', v ? 'true' : 'false');
  for (const f of RN.hooks.opt) f(key, v);
}
// New / old animation: the old is mdSync as it was (bone scales back to 1, the play starts again).
function vwAnim(on) {
  RN.on = on; vwPress('aNew', on); vwPress('aOld', !on);
  if (VW.it) for (const b of VW.it.bones) b.scale.set(1, 1, 1);
  for (const f of RN.hooks.opt) f('on', on);
  if (VW.playing !== undefined) vwPlay(VW.playing);
}

// Once, at the end of vwBoot: the layer's buttons, keys and controller, then the modules' boot hooks.
function rnBoot() {
  VW.aimX = 0; VW.wide = 1; VW.hold = 0;
  document.getElementById('aNew').addEventListener('click', () => vwAnim(true));
  document.getElementById('aOld').addEventListener('click', () => vwAnim(false));
  RN.opt.smooth = true;   // the pose drawn between two sim frames (no button: there is nothing to choose)
  for (const f of RN.hooks.boot) f(VW);
  vwPress('aNew', RN.on); vwPress('aOld', !RN.on);
  const cycle = () => vwSpeed(VW.speed === 1 ? .5 : VW.speed === .5 ? .25 : 1), n = VW_PLAYS.length;
  addEventListener('keydown', e => {
    const d = '1234567890'.indexOf(e.key), k = e.key.toLowerCase();
    if (e.repeat) return;
    if (d >= 0 && d < n) vwPlay(d);
    else if (k === 'n') vwAnim(!RN.on);
    else if (k === ' ') { e.preventDefault(); cycle(); }
    else if (k === 'arrowright') vwPlay((VW.playing + 1) % n);
    else if (k === 'arrowleft') vwPlay((VW.playing + n - 1) % n);
    else if (k === 'm' && 'dummy' in RN.opt) rnSet('dummy', !RN.opt.dummy);
    else if (k === 'l' && 'smear' in RN.opt) rnSet('smear', !RN.opt.smear);
  });
  RN.pad = () => {   // controller: shoulders change the play, A new/old, B speed, X dummy, Y smear
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const g of pads) {
      if (!g) continue;
      const b = i => !!(g.buttons[i] && g.buttons[i].pressed), was = VW.pad || {};
      if (b(5) && !was[5]) vwPlay((VW.playing + 1) % n);
      if (b(4) && !was[4]) vwPlay((VW.playing + n - 1) % n);
      if (b(0) && !was[0]) vwAnim(!RN.on);
      if (b(1) && !was[1]) cycle();
      if (b(2) && !was[2] && 'dummy' in RN.opt) rnSet('dummy', !RN.opt.dummy);
      if (b(3) && !was[3] && 'smear' in RN.opt) rnSet('smear', !RN.opt.smear);
      VW.pad = {0: b(0), 1: b(1), 2: b(2), 3: b(3), 4: b(4), 5: b(5)};
      break;
    }
  };
}
// Drawn frames per second over the last second (shown in the options row), and the controller's poll.
function rnFps(now) {
  VW.fc = (VW.fc || 0) + 1;
  if (!VW.ft) VW.ft = now;
  if (now - VW.ft >= 1000) { VW.fps = Math.round(VW.fc * 1000 / (now - VW.ft)); document.getElementById('fps').textContent = VW.fps + ' FPS'; VW.fc = 0; VW.ft = now; }
  if (RN.pad) RN.pad();
}
