// Fight simulation core: buttons, state, seeded generator, the fixed step, physics, pushboxes, facing, and hits
// (contacts, damage, hitstop, hitstun, juggle, knockdown and getup).
// Pure and deterministic: integers only (mm, mm/frame, frames), no THREE, DOM, clock or Math.random.
// One step = one frame at 60 per second, fed one integer of buttons per player; graphics only read the state.

const BTN={U:1, D:2, L:4, R:8, P:16, K:32, S:64, DASH:128, GUARD:256};   // directions are absolute (L = screen left)

// af = frame of the current action (1 on its first frame); hold = frames P/K held (see inputPhase);
// prev = last frame's clean buttons; tap = last horizontal press {dir: BTN.L|BTN.R, f: frame}, dir 0 = none;
// land = recovery frames of the current landing; hit = the move in progress has touched (1 hit, 2 blocked);
// stun = hitstun frames left; inv = invulnerable frames left; juggle = hits taken in this juggle;
// buf = the command waiting for the fighter to be free ({cmd, left} frames); sj = this jump is a super jump;
// mute = P/K bits whose release (and heavy) is ignored until released, after a throw command (see readCommand).
function newFighter(side, char) {
  return {side, char, x: side ? CFG.stage.startX : -CFG.stage.startX, y: 0, vx: 0, vy: 0, face: side ? -1 : 1,
    hp: CFG.body.hp, meter: 0, act: 'idle', af: 0, air: false, stun: 0, combo: 0, comboDmg: 0, juggle: 0,
    hit: 0, inv: 0, hold: [0, 0], prev: 0, tap: {dir: 0, f: 0}, buf: {cmd: null, left: 0}, sj: false, land: 0, mute: 0};
}

// opts = {seed, mode: 'versus'|'training', chars: [c0, c1], dummy: 'fermo'|'casuale'}.
// Starts in the round-1 'intro'. timer = frames left in the round (-1 = none, in training); pf = frames in the
// phase; dum = the training dummy's state (c3_dummy.js); rf = frames each fighter has been out of a combo (training refill).
function simCreate(o) {
  const chars = o.chars || ['ren', 'kael'], training = o.mode === 'training';
  return {frame: 0, rng: o.seed | 0, mode: o.mode || 'versus', phase: 'intro', pf: 0, round: 1,
    timer: training ? -1 : CFG.round.timerS * 60, rf: [0, 0],
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

// Input history, once the command has read it: this frame's buttons, the muted buttons still held and the last
// horizontal tap (a double tap uses the tap up, so a third press starts a new pair).
function rememberInput(S, F, bits) {
  F.mute &= bits;
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

// Fighters in a free ground state or landing turn to face the opponent (a jump, a dash, a move and a stun keep their
// facing). The landing turns so that back, forward and a dash pressed in it already count for the side it landed on.
function faceOpponent(F, O) { if ((FREE[F.act] || F.act === 'landing') && O.x !== F.x) F.face = O.x > F.x ? 1 : -1; }

// --- Hits ---

// Damage of the n-th hit of a combo, in %: full for the first scaleFrom-1 hits, then scaleStep less per hit, down to minScale.
function scaleFor(n) { const c = CFG.combo; return Math.max(c.minScale, 100 - c.scaleStep * Math.max(0, n - c.scaleFrom + 1)); }

// Hitstun of the n-th hit of a combo: base up to hit decayFrom-1, then decay frames less per hit, down to minStun.
function hitstunFor(base, n) { const c = CFG.combo; return Math.max(c.minStun, base - c.decay * Math.max(0, n - c.decayFrom + 1)); }

// Knocked down or getting up: always invulnerable (inv counts the frames left, see knockLeft).
const KNOCKED = {knock: 1, getup: 1, rollF: 1, rollB: 1};
// Actions with the crouching hurtbox height (and block while down is held: a crouching block, see isBlocking).
const CROUCHED = {crouch: 1, guardC: 1, cp: 1, ck: 1, chp: 1, chk: 1};

// A hit can touch F: not invulnerable, not knocked down, not KO'd, getting up or held in a throw, and a juggle still under combo.juggleMax hits.
function canBeHit(F) { return F.inv <= 0 && !KNOCKED[F.act] && F.act !== 'ko' && F.act !== 'thrown' && !(F.act === 'juggle' && F.juggle >= CFG.combo.juggleMax); }

// Hurtboxes in absolute mm, [body, head]: the body is ±body.hurt from the feet to the height minus body.headH,
// the head ±body.head from there to the height (body.h standing, hCrouch crouching or blocking with down held,
// hAir in the air).
function hurtBoxes(F) {
  const b = CFG.body, low = CROUCHED[F.act] || (F.act === 'block' && (F.prev & BTN.D));
  const top = F.y + (F.air ? b.hAir : low ? b.hCrouch : b.h), neck = top - b.headH;
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

// States that can guard (with GUARD or back held at the moment of contact).
const GUARDING = {idle: 1, walkB: 1, crouch: 1, guard: 1, guardC: 1, block: 1};

// F blocks an attack of this height now: on the ground in a guarding state, holding GUARD or back, and for the
// height: mid either way, low only crouching (D held), high only standing. The held buttons are F.prev (this frame's).
function isBlocking(F, height) {
  if (!GUARDING[F.act] || F.air || !(F.prev & (BTN.GUARD | backBit(F)))) return false;
  const crouching = (F.prev & BTN.D) !== 0;
  return height === 'low' ? crouching : height === 'high' ? !crouching : true;
}

// End of the step: both fighters are checked before either hit lands, so two moves can trade on the same frame.
// Then the throws and the projectiles. Contacts resolve only in the 'fight' phase: after a KO or time-up the hp stays
// as it was when the round ended (a grab under way plays out without its damage). A held fighter whose thrower got
// hit meanwhile (a projectile can), or whose grab ended, is released.
function contactPhase(S, fs) {
  if (S.phase === 'fight') {
    const id0 = fs[0].act, id1 = fs[1].act, p0 = touchPoint(fs[0], fs[1]), p1 = touchPoint(fs[1], fs[0]);
    if (p0) fs[0].hit = resolveHit(S, fs[0], fs[1], CFG.moves[id0], id0, p0, fs[0].face);
    if (p1) fs[1].hit = resolveHit(S, fs[1], fs[0], CFG.moves[id1], id1, p1, fs[1].face);
    throwPhase(S, fs);
    projectilePhase(S, fs);
  }
  for (const D of fs) if (D.act === 'thrown' && !(fs[1 - D.side].act === 'thr' && fs[1 - D.side].hit)) setAct(D, 'idle');
}

// Move m (id in the events: a move, 'spec' or 'thr') of A touches D, pushing the way dir points. Returns 1 for a
// hit, 2 for a block (what A.hit holds). A blocked move (m.h set, see isBlocking) costs D m.chip, gives A
// meter.block of its damage, hitstops for the block class and leaves D in 'block' for m.bs frames. A hit: damage
// scaled by its number in the combo, meter to both, the hitstop of the move's class, the event at the contact
// point, then D's reaction. The projectile ('spec') has its own events and never sets A.hit (the caller does).
function resolveHit(S, A, D, m, id, pt, dir) {
  const proj = id === 'spec', max = CFG.body.meterMax;
  if (m.h && isBlocking(D, m.h)) {
    const chip = Math.min(D.hp, m.chip || 0);
    D.hp -= chip;
    A.meter = Math.min(max, A.meter + Math.floor(m.dmg * CFG.meter.block));
    S.stop = Math.max(S.stop, CFG.stop[m.stop === 'light' ? 'blockLight' : 'blockHeavy']);
    simEmit(S, proj ? 'projBlock' : 'block', A, {x: pt.x, y: pt.y, move: id, dmg: chip, heavy: m.stop === 'heavy'});
    setAct(D, 'block'); D.stun = m.bs;
    if (dir * D.x >= CFG.stage.half - CFG.body.push && !A.air) { D.vx = 0; A.vx = -dir * m.push; }
    else D.vx = dir * m.push;
    return 2;
  }
  const n = D.combo + 1, dmg = Math.floor(m.dmg * scaleFor(n) / 100);
  D.hp = Math.max(0, D.hp - dmg); D.combo = n; D.comboDmg += dmg;
  A.meter = Math.min(max, A.meter + Math.floor(dmg * CFG.meter.hit));
  D.meter = Math.min(max, D.meter + Math.floor(dmg * CFG.meter.taken));
  S.stop = Math.max(S.stop, CFG.stop[m.stop]);
  simEmit(S, proj ? 'projHit' : 'hit', A, {x: pt.x, y: pt.y, move: id, dmg, heavy: m.stop === 'heavy'});
  hitReaction(A, D, m, n, dir);
  return 1;
}

// A throw (act 'thr', see c2_moves.js) of fighter A: in its active frames it grabs D if the centres are within
// thr.range and D stands on the ground free of stun, not invulnerable and not already held ('thr' event: A plays
// the grab from af 1, D is 'thrown'); at af thr.hitF of the grab the throw hits through resolveHit (it has no height,
// so no block) and D is knocked down. Side 0 goes first, so it wins a grab on the same frame.
function throwPhase(S, fs) {
  const t = CFG.thr;
  for (const A of fs) {
    const D = fs[1 - A.side];
    if (A.act !== 'thr') continue;
    if (!A.hit) {
      if (A.af <= t.s || A.af > t.s + t.a || Math.abs(A.x - D.x) > t.range) continue;
      if (D.air || D.y > 0 || D.stun > 0 || !canBeHit(D)) continue;
      A.hit = 1; A.af = 1; A.vx = 0; D.vx = 0;
      setAct(D, 'thrown'); D.stun = 0;
      simEmit(S, 'thr', A, {x: D.x, y: D.y + CFG.spec.y});
    } else if (A.af === t.hitF) {
      resolveHit(S, A, D, t, 'thr', {x: D.x, y: D.y + CFG.spec.y}, A.face);
    }
  }
}

// Projectiles move at the start of a free step. Here, after the fighters' contacts: two that touch vanish together
// ('projClash'); one that touches the other side's fighter (hurtbox, one that can be hit) hits or is blocked through
// resolveHit and vanishes, and one beyond stage.half + 1000 vanishes too.
function projectilePhase(S, fs) {
  const k = CFG.spec, P = S.proj;
  if (P.length === 2 && Math.abs(P[0].x - P[1].x) <= 2 * k.box && Math.abs(P[0].y - P[1].y) <= 2 * k.box) {
    simEmit(S, 'projClash', fs[P[0].side], {x: (P[0].x + P[1].x) >> 1, y: P[0].y});
    P.length = 0;
    return;
  }
  const keep = [];
  for (const p of P) {
    const D = fs[1 - p.side], pt = canBeHit(D) ? projTouch(p, D) : null;
    if (pt) resolveHit(S, fs[p.side], D, k, 'spec', pt, p.vx > 0 ? 1 : -1);
    else if (Math.abs(p.x) <= CFG.stage.half + 1000) keep.push(p);
  }
  P.length = 0; for (const p of keep) P.push(p);
}

// Centre of the overlap of projectile p (a square of half-size spec.box) with D's first hurtbox it overlaps, or null.
function projTouch(p, D) {
  const b = CFG.spec.box;
  for (const h of hurtBoxes(D)) {
    const x0 = Math.max(p.x - b, h.x0), x1 = Math.min(p.x + b, h.x1), y0 = Math.max(p.y - b, h.y0), y1 = Math.min(p.y + b, h.y1);
    if (x0 < x1 && y0 < y1) return {x: (x0 + x1) >> 1, y: (y0 + y1) >> 1};
  }
  return null;
}

// D's reaction to the n-th hit of a combo, pushed toward dir (the way the attack or projectile goes):
// - knocked down (knock, or airKnock / spike on an airborne D): flies with the move's vx, vy, invulnerable;
// - launched (launch) or hit in the air: juggle, rising at least at the move's vy (else combo.lift), with the
//   move's vx (else its push); one more juggle hit;
// - else hitstun (hitstunFor) and a pushback of push that slides (groundSpeed); at the wall D stays and an
//   attacker on the ground slides back instead (a move without push, like the projectile, moves nobody).
function hitReaction(A, D, m, n, dir) {
  const down = m.knock ? m : D.air ? m.airKnock || (m.spike ? m : null) : null;
  D.stun = 0;
  if (down) {
    setAct(D, 'knock'); D.air = true; D.vx = down.vx ? dir * down.vx : 0; D.vy = down.vy; D.inv = CFG.knock.ground;
  } else if (m.launch || D.air) {
    const vx = m.vx !== undefined ? m.vx : m.push;
    setAct(D, 'juggle'); D.air = true; D.juggle++; D.vx = vx ? dir * vx : 0;
    D.vy = Math.max(D.vy, m.vy !== undefined ? m.vy : CFG.combo.lift);
  } else {
    setAct(D, 'hitStun'); D.stun = hitstunFor(m.hs, n);
    if (m.push && dir * D.x >= CFG.stage.half - CFG.body.push && !A.air) { D.vx = 0; A.vx = -dir * m.push; }
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

// --- Rounds ---

// Round phases: 'intro' (round.intro frames, inputs ignored) -> 'fight' -> 'ko' | 'timeup' (inputs ignored, physics
// runs on and the actions under way run out, but no command, contact or projectile: the hp is the one of the frame
// the round ended) -> round.end frames later the round is scored -> next 'intro' or 'end'. In training there is no timer
// and no KO: hp stays at 1 or more and refills, once, when the fighter has been out of a combo (and not blocking)
// for training.refill frames.
function roundStep(S, fs) {
  const R = CFG.round, training = S.mode === 'training';
  if (training) trainingStep(S, fs);
  if (S.phase === 'intro') {
    if (S.pf === 0) simEmit(S, 'round', fs[0]);   // the HUD reads S.round
    if (++S.pf >= R.intro) { S.phase = 'fight'; S.pf = 0; simEmit(S, 'fight', fs[0]); }
  } else if (S.phase === 'fight') {
    S.pf++;
    if (fs[0].hp <= 0 || fs[1].hp <= 0) endRound(S, fs, 'ko');   // whatever the source (chip damage too)
    else if (S.timer > 0 && --S.timer === 0) endRound(S, fs, 'timeup');
  } else if (S.phase === 'end') {
    S.pf++;
  } else if (++S.pf >= R.end) scoreRound(S, fs);   // 'ko' or 'timeup'
}

function trainingStep(S, fs) {
  for (const F of fs) {
    F.hp = Math.max(1, F.hp);
    S.rf[F.side] = F.combo > 0 || F.act === 'block' ? 0 : Math.min(CFG.training.refill + 1, S.rf[F.side] + 1);
    if (S.rf[F.side] === CFG.training.refill) F.hp = CFG.body.hp;   // once, so a hp set by hand is not undone
  }
}

// The round is over: 'ko' (the fighters at 0 hp fall, the KO hitstop) or 'timeup'. Projectiles in flight vanish.
function endRound(S, fs, kind) {
  S.phase = kind; S.pf = 0; S.proj.length = 0;
  if (kind === 'timeup') { simEmit(S, 'timeup', fs[0]); return; }
  S.stop = CFG.stop.ko;
  for (const F of fs) {
    if (F.hp > 0) continue;
    setAct(F, 'ko'); F.stun = 0;
    if (!F.air) { F.air = true; F.vy = CFG.round.ko.vy; F.vx = (F.x < fs[1 - F.side].x ? -1 : 1) * CFG.round.ko.vx; }
    simEmit(S, 'ko', F);
  }
}

// More hp takes the round; equal hp gives it to both. Then the match ends (winner 0, 1 or 2 = both) or the next round starts.
function scoreRound(S, fs) {
  const d = fs[0].hp - fs[1].hp;
  if (d) { const w = d > 0 ? 0 : 1; S.wins[w]++; simEmit(S, 'win', fs[w]); }
  else { S.wins[0]++; S.wins[1]++; simEmit(S, 'draw', fs[0]); }
  const w0 = S.wins[0] >= CFG.round.wins, w1 = S.wins[1] >= CFG.round.wins;
  S.pf = 0;
  if (w0 || w1) { S.phase = 'end'; S.winner = w0 && w1 ? 2 : w0 ? 0 : 1; return; }
  for (const side of S.sides) { const old = side.team[side.cur]; side.team[side.cur] = Object.assign(newFighter(old.side, old.char), {meter: old.meter}); }
  S.round++; S.phase = 'intro'; S.stop = 0;
  S.timer = S.mode === 'training' ? -1 : CFG.round.timerS * 60;
}

// One frame. Input first: clean buttons and hold counters, then the 'charge' event. In hitstop (S.stop > 0) nothing
// else moves: only the buffer takes this frame's command (without expiring) and the input history updates.
// Otherwise: per fighter command and action (c2_moves.js), then the input history -> physics -> pushboxes, walls,
// max separation -> facing -> contacts (a hit sets the next hitstop). Then the round flow. frame++ either way.
// Commands are read only in the 'fight' phase (see actionStep).
function simStep(S, in0, in1) {
  S.ev.length = 0;
  const live = S.phase === 'fight';
  if (!live) { in0 = 0; in1 = 0; }   // intro, KO, time up and the end ignore the buttons
  const fs = [fighterOf(S, 0), fighterOf(S, 1)], bits = [inputPhase(fs[0], in0), inputPhase(fs[1], in1)];
  for (let i = 0; i < 2; i++) chargeEvent(S, fs[i], bits[i]);
  if (S.stop > 0) {
    S.stop--;
    for (let i = 0; i < 2; i++) { if (live) bufferCommand(S, fs[i], bits[i]); rememberInput(S, fs[i], bits[i]); }
  } else {
    for (const p of S.proj) p.x += p.vx;
    for (let i = 0; i < 2; i++) { actionStep(S, fs[i], bits[i]); rememberInput(S, fs[i], bits[i]); }
    const x0 = [fs[0].x, fs[1].x];
    for (const f of fs) fighterPhysics(S, f);
    pushApart(fs[0], fs[1], x0);
    faceOpponent(fs[0], fs[1]); faceOpponent(fs[1], fs[0]);
    contactPhase(S, fs);
  }
  roundStep(S, fs);
  S.frame++;
}
