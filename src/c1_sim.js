// Fight simulation core: buttons, state, seeded generator, the fixed step, physics, pushboxes, facing, and hits
// (contacts, damage, hitstop, hitstun, juggle, knockdown and getup).
// Pure and deterministic: integers only (mm, mm/frame, frames), no THREE, DOM, clock or Math.random.
// One step = one frame at 60 per second, fed one integer of buttons per player; graphics only read the state.

const BTN={U:1, D:2, L:4, R:8, P:16, K:32, S:64, DASH:128, GUARD:256};   // directions are absolute (L = screen left)

// af = frame of the current action (1 on its first frame); hold = frames P/K held (see inputPhase);
// prev = last frame's clean buttons; tap = last horizontal press {dir: BTN.L|BTN.R, f: frame}, dir 0 = none;
// land = recovery frames of the current landing; hit = the move in progress has touched (1 hit, 2 blocked);
// stun = hitstun frames left; inv = invulnerable frames left; juggle = hits taken in this juggle;
// buf = the command waiting for the fighter to be free ({cmd, left} frames); sj = this jump is a super jump.
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

// Adds an event of this frame, {t, side, x, y, move, dmg, heavy}: at the fighter's position unless o overrides it.
function simEmit(S, t, F, o) {
  const e = {t, side: F.side, x: F.x, y: F.y, move: null, dmg: 0, heavy: false};
  S.ev.push(o ? Object.assign(e, o) : e);
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

// --- Hits ---

// Damage of the n-th hit of a combo, in %: full for the first scaleFrom-1 hits, then scaleStep less per hit, down to minScale.
function scaleFor(n) { const c = CFG.combo; return Math.max(c.minScale, 100 - c.scaleStep * Math.max(0, n - c.scaleFrom + 1)); }

// Hitstun of the n-th hit of a combo: base up to hit decayFrom-1, then decay frames less per hit, down to minStun.
function hitstunFor(base, n) { const c = CFG.combo; return Math.max(c.minStun, base - c.decay * Math.max(0, n - c.decayFrom + 1)); }

// Knocked down or getting up: always invulnerable (inv counts the frames left, see knockLeft).
const KNOCKED = {knock: 1, getup: 1, rollF: 1, rollB: 1};
// Actions with the crouching hurtbox height.
const CROUCHED = {crouch: 1, guardC: 1, cp: 1, ck: 1, chp: 1, chk: 1};

// A hit can touch F: not invulnerable, not knocked down or getting up, and a juggle still under combo.juggleMax hits.
function canBeHit(F) { return F.inv <= 0 && !KNOCKED[F.act] && !(F.act === 'juggle' && F.juggle >= CFG.combo.juggleMax); }

// Hurtboxes in absolute mm, [body, head]: the body is ±body.hurt from the feet to the height minus body.headH,
// the head ±body.head from there to the height (body.h standing, hCrouch crouching, hAir in the air).
function hurtBoxes(F) {
  const b = CFG.body, top = F.y + (F.air ? b.hAir : CROUCHED[F.act] ? b.hCrouch : b.h), neck = top - b.headH;
  return [{x0: F.x - b.hurt, x1: F.x + b.hurt, y0: F.y, y1: neck}, {x0: F.x - b.head, x1: F.x + b.head, y0: neck, y1: top}];
}

// The box of move id in absolute mm, mirrored by the facing, while F is in that move's active frames; else null.
function moveBox(F, id) {
  const m = CFG.moves[id];
  if (!m || F.act !== id || F.af <= m.s || F.af > m.s + m.a) return null;
  const k = m.box, y0 = F.y + k[2], y1 = F.y + k[3];
  return F.face > 0 ? {x0: F.x + k[0], x1: F.x + k[1], y0, y1} : {x0: F.x - k[1], x1: F.x - k[0], y0, y1};
}

// Where A's move touches D, or null: the centre of the overlap of the move box with D's first hurtbox it
// overlaps (body, then head). Only a move in its active frames that has not touched yet, on a fighter that can be hit.
function touchPoint(A, D) {
  const box = A.hit ? null : moveBox(A, A.act);
  if (!box || !canBeHit(D)) return null;
  for (const h of hurtBoxes(D)) {
    const x0 = Math.max(box.x0, h.x0), x1 = Math.min(box.x1, h.x1), y0 = Math.max(box.y0, h.y0), y1 = Math.min(box.y1, h.y1);
    if (x0 < x1 && y0 < y1) return {x: (x0 + x1) >> 1, y: (y0 + y1) >> 1};
  }
  return null;
}

// End of the step: both fighters are checked before either hit lands, so two moves can trade on the same frame.
function contactPhase(S, fs) {
  const id0 = fs[0].act, id1 = fs[1].act, p0 = touchPoint(fs[0], fs[1]), p1 = touchPoint(fs[1], fs[0]);
  if (p0) resolveHit(S, fs[0], fs[1], id0, p0);
  if (p1) resolveHit(S, fs[1], fs[0], id1, p1);
}

// Move id of A touches D (Task 4 adds the block check here): damage scaled by the hit's number in the combo, meter
// to both, the hitstop of the move's class, the 'hit' event at the contact point, then D's reaction.
function resolveHit(S, A, D, id, pt) {
  const m = CFG.moves[id], n = D.combo + 1, dmg = Math.floor(m.dmg * scaleFor(n) / 100), max = CFG.body.meterMax;
  A.hit = 1;
  D.hp = Math.max(0, D.hp - dmg); D.combo = n; D.comboDmg += dmg;
  A.meter = Math.min(max, A.meter + Math.floor(dmg * CFG.meter.hit));
  D.meter = Math.min(max, D.meter + Math.floor(dmg * CFG.meter.taken));
  S.stop = Math.max(S.stop, CFG.stop[m.stop]);
  simEmit(S, 'hit', A, {x: pt.x, y: pt.y, move: id, dmg, heavy: m.stop === 'heavy'});
  hitReaction(A, D, m, n);
}

// D's reaction to the n-th hit of a combo, pushed the way the attacker faces:
// - knocked down (knock, or airKnock / spike on an airborne D): flies with the move's vx, vy, invulnerable;
// - launched (launch) or hit in the air: juggle, rising at least at the move's vy (else combo.lift), with the
//   move's vx (else its push); one more juggle hit;
// - else hitstun (hitstunFor) and a pushback of push that slides (groundSpeed); at the wall D stays and an
//   attacker on the ground slides back instead.
function hitReaction(A, D, m, n) {
  const dir = A.face, down = m.knock ? m : D.air ? m.airKnock || (m.spike ? m : null) : null;
  D.stun = 0;
  if (down) {
    setAct(D, 'knock'); D.air = true; D.vx = down.vx ? dir * down.vx : 0; D.vy = down.vy; D.inv = CFG.knock.ground;
  } else if (m.launch || D.air) {
    const vx = m.vx !== undefined ? m.vx : m.push;
    setAct(D, 'juggle'); D.air = true; D.juggle++; D.vx = vx ? dir * vx : 0;
    D.vy = Math.max(D.vy, m.vy !== undefined ? m.vy : CFG.combo.lift);
  } else {
    setAct(D, 'hitStun'); D.stun = hitstunFor(m.hs, n);
    if (dir * D.x >= CFG.stage.half - CFG.body.push && !A.air) { D.vx = 0; A.vx = -dir * m.push; }
    else D.vx = dir * m.push;
  }
}

// Leaving hitstun or a knockdown: the combo against F is over.
function recoverFrom(F, act) { setAct(F, act); F.combo = 0; F.comboDmg = 0; F.juggle = 0; }

// At the end of a knockdown's ground time: a roll while a direction is held (forward or back for the facing), else a getup.
function wakeAct(F, bits) { return bits & fwdBit(F) ? 'rollF' : bits & backBit(F) ? 'rollB' : 'getup'; }

// Invulnerable frames left while knocked down or getting up: the whole ground time while still flying,
// then to the end of the current action.
function knockLeft(F) { return F.act === 'knock' && F.air ? CFG.knock.ground : actLength(F) - F.af + 1; }

// Roll speed on frame af (1..knock.roll): integer steps that add up to knock.rollDist.
function rollSpeed(af) { const k = CFG.knock; return Math.floor(k.rollDist * af / k.roll) - Math.floor(k.rollDist * (af - 1) / k.roll); }

// One frame. Input first: clean buttons and hold counters, then the 'charge' event. In hitstop (S.stop > 0) nothing
// else moves: only the buffer takes this frame's command (without expiring) and the input history updates.
// Otherwise: per fighter command and action (c2_moves.js), then the input history -> physics -> pushboxes, walls,
// max separation -> facing -> contacts (a hit sets the next hitstop). frame++ either way.
function simStep(S, in0, in1) {
  S.ev.length = 0;
  const fs = [fighterOf(S, 0), fighterOf(S, 1)], bits = [inputPhase(fs[0], in0), inputPhase(fs[1], in1)];
  for (let i = 0; i < 2; i++) chargeEvent(S, fs[i], bits[i]);
  if (S.stop > 0) {
    S.stop--;
    for (let i = 0; i < 2; i++) { bufferCommand(S, fs[i], bits[i]); rememberInput(S, fs[i], bits[i]); }
  } else {
    for (let i = 0; i < 2; i++) { actionStep(S, fs[i], bits[i]); rememberInput(S, fs[i], bits[i]); }
    const x0 = [fs[0].x, fs[1].x];
    for (const f of fs) fighterPhysics(S, f);
    pushApart(fs[0], fs[1], x0);
    faceOpponent(fs[0], fs[1]); faceOpponent(fs[1], fs[0]);
    contactPhase(S, fs);
  }
  S.frame++;
}
