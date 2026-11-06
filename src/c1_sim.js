// Fight simulation core: buttons, state, seeded generator, the fixed step, physics, pushboxes and facing.
// Pure and deterministic: integers only (mm, mm/frame, frames), no THREE, DOM, clock or Math.random.
// One step = one frame at 60 per second, fed one integer of buttons per player; graphics only read the state.

const BTN={U:1, D:2, L:4, R:8, P:16, K:32, S:64, DASH:128, GUARD:256};   // directions are absolute (L = screen left)

// af = frame of the current action (1 on its first frame); hold = frames P/K held (see inputPhase);
// prev = last frame's clean buttons; tap = last horizontal press {dir: BTN.L|BTN.R, f: frame}, dir 0 = none;
// land = recovery frames of the current landing; hit = the move in progress has touched (1 hit, 2 blocked).
function newFighter(side, char) {
  return {side, char, x: side ? CFG.stage.startX : -CFG.stage.startX, y: 0, vx: 0, vy: 0, face: side ? -1 : 1,
    hp: CFG.body.hp, meter: 0, act: 'idle', af: 0, air: false, stun: 0, combo: 0, comboDmg: 0, juggle: 0,
    hit: 0, inv: 0, hold: [0, 0], prev: 0, tap: {dir: 0, f: 0}, buf: {cmd: null, left: 0}, sj: false, land: 0};
}

// opts = {seed, mode: 'versus'|'training', chars: [c0, c1], dummy: 'fermo'|'casuale'}.
// Starts in 'fight': round phases, timer (-1 = none), pf (frames in the phase) and dum (dummy state) are Task 5's.
function simCreate(o) {
  const chars = o.chars || ['ren', 'kael'];
  return {frame: 0, rng: o.seed | 0, mode: o.mode || 'versus', phase: 'fight', pf: 0, round: 1, timer: -1,
    wins: [0, 0], winner: -1, stop: 0, sides: [0, 1].map(i => ({team: [newFighter(i, chars[i])], cur: 0})),
    proj: [], ev: [], dummy: o.dummy || 'fermo', dum: [{act: null, left: 0}, {act: null, left: 0}]};
}

function fighterOf(S, side) { const s = S.sides[side]; return s.team[s.cur]; }

// Deep copy: the state is plain JSON (numbers, strings, booleans, null, arrays and objects).
function simClone(S) { return JSON.parse(JSON.stringify(S)); }

// 32-bit FNV-1a, in hex, of the state without this frame's events.
function simHash(S) {
  const {ev, ...state} = S, s = JSON.stringify(state);
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193);
  return (h >>> 0).toString(16).padStart(8, '0');
}

// Seeded generator (mulberry32 on the integer S.rng): an integer in [0, n).
function simRand(S, n) {
  const a = S.rng = S.rng + 0x6D2B79F5 | 0;
  let t = Math.imul(a ^ a >>> 15, 1 | a);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
  return ((t ^ t >>> 14) >>> 0) % n;
}

// Adds an event of this frame, {t, side, x, y, move, dmg, heavy}, at the fighter's position.
function simEmit(S, t, F) {
  S.ev.push({t, side: F.side, x: F.x, y: F.y, move: null, dmg: 0, heavy: false});
}

// Input phase, before the command: SOCD-clean buttons (L+R = no horizontal, U+D = no vertical) and the hold
// counters. hold[i] = frames P (i=0) / K (i=1) has been held in this press; on the release frame it still holds
// the press length, so the command reader can tell a tap from a heavy, and the frame after it is back to 0.
function inputPhase(F, raw) {
  let b = raw & 511;   // the 9 BTN bits; a missing input becomes 0
  if ((b & BTN.L) && (b & BTN.R)) b &= ~(BTN.L | BTN.R);
  if ((b & BTN.U) && (b & BTN.D)) b &= ~(BTN.U | BTN.D);
  for (let i = 0; i < 2; i++) {
    const btn = i ? BTN.K : BTN.P;
    if (b & btn) F.hold[i] = F.prev & btn ? F.hold[i] + 1 : 1;
    else if (!(F.prev & btn)) F.hold[i] = 0;
  }
  return b;
}

// This frame's horizontal press if it completes a double tap (same direction twice within dash.tap frames), else 0.
function doubleTapDir(S, F, bits) {
  const h = bits & ~F.prev & (BTN.L | BTN.R);
  return h && h === F.tap.dir && S.frame - F.tap.f <= CFG.dash.tap ? h : 0;
}

// Input history, once the command has read it: this frame's buttons and the last horizontal tap
// (a double tap uses the tap up, so a third press starts a new pair).
function rememberInput(S, F, bits) {
  const h = bits & ~F.prev & (BTN.L | BTN.R);
  if (h) { F.tap.dir = doubleTapDir(S, F, bits) ? 0 : h; F.tap.f = S.frame; }
  F.prev = bits;
}

// Velocity, gravity and touchdown at y = 0.
function fighterPhysics(S, F) {
  F.x += F.vx;
  if (!F.air) return;
  F.y += F.vy; F.vy -= CFG.jump.g;
  if (F.y <= 0) { F.y = 0; F.vx = 0; F.vy = 0; F.air = false; touchdown(S, F); }
}

// Pushboxes, walls and maximum separation. Overlapping pushboxes split the overlap half and half, but not while
// either fighter is in the air above body.passY, so a jump can cross over. Walls stop the centres at
// ±(stage.half - body.push), and a fighter in the corner makes the other one take the whole push. Beyond
// stage.maxSep the excess is taken back from whoever moved away this frame (x0 = x before physics, by side).
function pushApart(a, b, x0) {
  const P2 = 2 * CFG.body.push, W = CFG.stage.half - CFG.body.push;
  const solid = a.y <= CFG.body.passY && b.y <= CFG.body.passY;
  const aLeft = a.x !== b.x ? a.x < b.x : a.face >= b.face;
  const l = aLeft ? a : b, r = aLeft ? b : a;
  if (solid && r.x - l.x < P2) { const ov = P2 - (r.x - l.x), h = ov >> 1; l.x -= h; r.x += ov - h; }
  l.x = Math.max(-W, Math.min(W, l.x)); r.x = Math.max(-W, Math.min(W, r.x));
  if (solid && r.x - l.x < P2) { if (l.x === -W) r.x = l.x + P2; else l.x = r.x - P2; }
  const ex = r.x - l.x - CFG.stage.maxSep;
  if (ex > 0) {
    const outL = Math.max(0, x0[l.side] - l.x), outR = Math.max(0, r.x - x0[r.side]);
    let tl = Math.min(outL, Math.max(ex >> 1, ex - outR));   // half each when both moved away
    const tr = Math.min(outR, ex - tl);
    tl += (ex - tl - tr) >> 1;   // more than this frame's motion (fighters placed by hand): split the rest
    l.x += tl; r.x -= ex - tl;
  }
}

// Only fighters in a free ground state turn to face the opponent (a jump or a dash keeps its facing).
function faceOpponent(F, O) { if (FREE[F.act] && O.x !== F.x) F.face = O.x > F.x ? 1 : -1; }

// One frame: input (clean buttons, hold counters) -> command and action (c2_moves.js), then the input history
// -> physics -> pushboxes, walls, max separation -> facing -> frame++.
function simStep(S, in0, in1) {
  S.ev.length = 0;
  const fs = [fighterOf(S, 0), fighterOf(S, 1)], bits = [inputPhase(fs[0], in0), inputPhase(fs[1], in1)];
  for (let i = 0; i < 2; i++) { actionStep(S, fs[i], bits[i]); rememberInput(S, fs[i], bits[i]); }
  const x0 = [fs[0].x, fs[1].x];
  for (const f of fs) fighterPhysics(S, f);
  pushApart(fs[0], fs[1], x0);
  faceOpponent(fs[0], fs[1]); faceOpponent(fs[1], fs[0]);
  S.frame++;
}
