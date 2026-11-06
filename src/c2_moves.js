// Command reading (tap and hold, chains, buffer) and the action state machine. Pure, like c1_sim.js.
// An action's first frame has af = 1: setAct zeroes af and the frame's advance (af++) follows it,
// so the active frames of a move with startup s and a active frames are af = s+1 .. s+a.

// Free ground states: the fighter takes any command and turns to face the opponent.
const FREE = {idle: 1, walkF: 1, walkB: 1, crouch: 1, guard: 1, guardC: 1};
// Actions that move the fighter by themselves: their speed stops with them (setAct). Every other ground action
// keeps the pushback of a hit sliding (groundSpeed).
const SELF_MOVED = {walkF: 1, walkB: 1, dashF: 1, dashB: 1, rollF: 1, rollB: 1};
// The normal that a P/K tap or heavy command gives in each posture: [standing, crouching (D held), in the air].
const NORMALS = {P: ['p1', 'cp', 'jp'], K: ['k1', 'ck', 'jk'], HP: ['hp', 'chp', 'jhp'], HK: ['hk', 'chk', 'jhk']};

function setAct(F, act) { if (SELF_MOVED[F.act]) F.vx = 0; F.act = act; F.af = 0; F.hit = 0; }

// Forward and back buttons for the fighter's facing.
function fwdBit(F) { return F.face > 0 ? BTN.R : BTN.L; }
function backBit(F) { return F.face > 0 ? BTN.L : BTN.R; }

// The command this frame's buttons give, or null. Commands are events, so they can wait in the buffer (F.buf).
// By priority: 'thr' = P and K pressed within input.both frames of each other (the two releases afterwards, and a
// heavy, are muted: F.mute), 'spec' = S press (not while this side has a projectile alive), 'P'/'K' = released after
// a tap (held less than input.hold), 'HP'/'HK' = held to input.hold (a heavy; its release does nothing), 'dashF'/'dashB' = DASH press (back + DASH =
// back dash) or a double tap forward, 'jump' = U press.
function readCommand(S, F, bits) {
  const hold = CFG.input.hold, mP = F.mute & BTN.P, mK = F.mute & BTN.K;
  if ((bits & (BTN.P | BTN.K)) === (BTN.P | BTN.K) && !mP && !mK && (F.hold[0] === 1 || F.hold[1] === 1) &&
      Math.abs(F.hold[0] - F.hold[1]) <= CFG.input.both) return 'thr';
  if (bits & ~F.prev & BTN.S && !S.proj.some(p => p.side === F.side)) return 'spec';
  if (F.prev & BTN.P && !(bits & BTN.P) && F.hold[0] < hold && !mP) return 'P';
  if (F.prev & BTN.K && !(bits & BTN.K) && F.hold[1] < hold && !mK) return 'K';
  if (bits & BTN.P && F.hold[0] === hold && !mP) return 'HP';
  if (bits & BTN.K && F.hold[1] === hold && !mK) return 'HK';
  if (bits & ~F.prev & BTN.DASH) return bits & backBit(F) ? 'dashB' : 'dashF';
  if (doubleTapDir(S, F, bits) === fwdBit(F)) return 'dashF';
  if (bits & ~F.prev & BTN.U) return 'jump';
  return null;
}

// What the held buttons ask for in a free ground state when no command starts: jump (U held, so holding U
// jumps again on landing), guard (GUARD, low with D), crouch (D), walk forward or back; null = idle.
function holdCommand(F, bits) {
  if (bits & BTN.U) return 'jump';
  if (bits & BTN.GUARD) return bits & BTN.D ? 'guardC' : 'guard';
  if (bits & BTN.D) return 'crouch';
  if (bits & fwdBit(F)) return 'walkF';
  if (bits & backBit(F)) return 'walkB';
  return null;
}

// The normal for a P/K tap or heavy command in the fighter's posture now.
function normalFor(F, cmd, bits) { return NORMALS[cmd][F.air ? 2 : bits & BTN.D ? 1 : 0]; }

// What a command starts in the fighter's state now, or null (it waits in the buffer). A free ground state takes
// any command, a jump ('air') its air normals. A move takes only its cancels, from the frame it touched to the end
// of its recovery: tapP/tapK, a heavy (heavy: true = the posture's heavy, or a list of moves), the Special (spec)
// and, after a hit (not a block), the super jump of a jc move. A throw never cancels.
function commandAct(F, cmd, bits) {
  const m = CFG.moves[F.act], normal = NORMALS[cmd] ? normalFor(F, cmd, bits) : null;
  if (m) {
    if (!F.hit) return null;
    if (cmd === 'P') return m.tapP || null;
    if (cmd === 'K') return m.tapK || null;
    if (cmd === 'spec') return m.spec ? 'spec' : null;
    if (cmd === 'jump') return m.jc && F.hit === 1 ? 'superJump' : null;
    return normal && (m.heavy === true || (m.heavy && m.heavy.indexOf(normal) >= 0)) ? normal : null;
  }
  if (F.act === 'air') return normal;
  return FREE[F.act] ? normal || cmd : null;
}

// Starts an action: a move, a movement action (jump = squat first, superJump = squat of a super jump) or idle
// (null). Holding the same walk, crouch or guard keeps its af counting.
function startCommand(S, F, cmd) {
  if (cmd === 'superJump') { setAct(F, 'jumpSquat'); F.sj = true; return; }
  const act = cmd === 'jump' ? 'jumpSquat' : cmd || 'idle';
  if (act === F.act) return;
  setAct(F, act);
  if (act === 'jumpSquat') F.sj = false;
  if (act === 'dashF' || act === 'dashB') simEmit(S, 'dash', F);
}

// This frame's command takes the buffer's place (the newest wins), where it waits up to input.buffer frames.
function bufferCommand(S, F, bits) {
  const cmd = readCommand(S, F, bits);
  if (cmd) { F.buf.cmd = cmd; F.buf.left = CFG.input.buffer; }
  if (cmd === 'thr') F.mute = BTN.P | BTN.K;
  return cmd;
}

// 'charge' once per press: on the frame a held P or K reaches input.chargeShow.
function chargeEvent(S, F, bits) {
  const n = CFG.input.chargeShow;
  if ((bits & BTN.P && F.hold[0] === n) || (bits & BTN.K && F.hold[1] === n)) simEmit(S, 'charge', F);
}

// Length in frames of the timed actions; the others last until something ends them: hitstun ends with stun, an
// air move and a knockdown's flight with the touchdown (the knockdown's ground time starts there).
function actLength(F) {
  const m = CFG.moves[F.act];
  if (m) return m.r === 'land' ? Infinity : m.s + m.a + m.r;
  switch (F.act) {
    case 'jumpSquat': return CFG.jump.squat;
    case 'thr': return F.hit ? CFG.thr.anim : CFG.thr.s + CFG.thr.a;
    case 'thrWhiff': return CFG.thr.whiff;
    case 'spec': return CFG.spec.spawn + CFG.spec.rec;
    case 'landing': return F.land;
    case 'dashF': return CFG.dash.f.n;
    case 'dashB': return CFG.dash.b.n;
    case 'knock': return F.air ? Infinity : CFG.knock.ground;
    case 'getup': return CFG.knock.getup;
    case 'rollF': case 'rollB': return CFG.knock.roll;
    default: return Infinity;
  }
}

// A finished action ends: the squat takes off; a throw that grabbed ends idle and one that missed in a whiff; a knockdown ends in a getup or a roll, and hitstun in idle, both
// ending the combo (recoverFrom); anything else returns to idle.
function endAction(S, F, bits) {
  if (F.act === 'jumpSquat') takeoff(S, F, bits);
  else if (F.act === 'knock') recoverFrom(F, wakeAct(F, bits));
  else if (F.act === 'hitStun') recoverFrom(F, 'idle');
  else if (F.act === 'thr' && !F.hit) setAct(F, 'thrWhiff');
  else setAct(F, 'idle');
}

// Dash speed on frame af (1..n): integer interpolation from v0 to v1.
function dashSpeed(d, af) { return d.v0 + Math.trunc((d.v1 - d.v0) * (af - 1) / Math.max(1, d.n - 1)); }

// Horizontal speed of a ground action on its frame af. Walks, dashes and rolls set their own; any other action
// keeps the pushback of a hit, which slows down by phys.pushFric per frame.
function groundSpeed(F) {
  switch (F.act) {
    case 'walkF': return F.face * CFG.walk.f;
    case 'walkB': return -F.face * CFG.walk.b;
    case 'dashF': return F.face * dashSpeed(CFG.dash.f, F.af);
    case 'dashB': return -F.face * dashSpeed(CFG.dash.b, F.af);
    case 'rollF': return F.face * rollSpeed(F.af);
    case 'rollB': return -F.face * rollSpeed(F.af);
    default: return F.vx > 0 ? Math.max(0, F.vx - CFG.phys.pushFric) : Math.min(0, F.vx + CFG.phys.pushFric);
  }
}

// End of the squat: the jump goes forward or back by the direction held now, relative to the facing;
// a super jump (sj, from a jump cancel) rises at jump.superV.
function takeoff(S, F, bits) {
  setAct(F, 'air'); F.air = true; F.vy = F.sj ? CFG.jump.superV : CFG.jump.v;
  F.vx = bits & fwdBit(F) ? F.face * CFG.jump.vxF : bits & backBit(F) ? F.face * CFG.jump.vxB : 0;
  simEmit(S, 'jump', F);
}

// Physics finds the touchdown after this frame's advance, so this frame is the next action's first (af = 1).
// A knockdown (knock in flight, or a juggle) stays down and its ground time starts ('knock' event);
// an air attack lands into jump.landAtk frames of landing, a jump into jump.land ('land' event).
function touchdown(S, F) {
  if (F.act === 'ko') { F.af = 1; return; }   // a KO'd fighter stays down
  const down = F.act === 'knock' || F.act === 'juggle', m = CFG.moves[F.act];
  F.sj = false;
  setAct(F, down ? 'knock' : 'landing'); F.af = 1;
  if (down) { simEmit(S, 'knock', F); return; }
  F.land = m ? CFG.jump.landAtk : CFG.jump.land;
  simEmit(S, 'land', F);
}

// The Special's frame spawn: a projectile at spec.x ahead of F, heading the way F faces.
function spawnProjectile(S, F) {
  const k = CFG.spec, p = {side: F.side, x: F.x + F.face * k.x, y: k.y, vx: F.face * k.speed, live: 1};
  S.proj.push(p);
  simEmit(S, 'proj', F, {x: p.x, y: p.y});
}

// One frame of a fighter's action (hitstop skips it): this frame's command enters the buffer; a finished action
// ends; the buffered command starts if the state takes it ('heavyFire' for a heavy), else a free state follows
// the held buttons and a waiting command loses a frame. Then af, stun and inv advance, 'whiff' marks a move whose
// active frames ended without contact, and the ground speed is set (in the air the takeoff or hit speed is kept).
function actionStep(S, F, bits) {
  const cmd = bufferCommand(S, F, bits);
  if (F.act === 'hitStun' || F.act === 'block' ? F.stun <= 0 : F.af >= actLength(F)) endAction(S, F, bits);
  const act = F.buf.cmd && commandAct(F, F.buf.cmd, bits);
  if (act) {
    if (F.buf.cmd === 'HP' || F.buf.cmd === 'HK') simEmit(S, 'heavyFire', F, {move: act, heavy: true});
    F.buf.cmd = null; F.buf.left = 0;
    startCommand(S, F, act);
  } else {
    if (FREE[F.act]) startCommand(S, F, holdCommand(F, bits));
    if (F.buf.cmd && !cmd && --F.buf.left <= 0) F.buf.cmd = null;
  }
  F.af++;
  if (F.act === 'spec' && F.af === CFG.spec.spawn) spawnProjectile(S, F);
  if (F.stun > 0) F.stun--;
  F.inv = KNOCKED[F.act] ? knockLeft(F) : Math.max(0, F.inv - 1);
  const m = CFG.moves[F.act];
  if (m && !F.hit && F.af === m.s + m.a + 1) simEmit(S, 'whiff', F, {move: F.act});
  if (!F.air) F.vx = groundSpeed(F);
}
