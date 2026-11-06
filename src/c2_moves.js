// Command reading and the action state machine. Pure, like c1_sim.js.
// An action's first frame has af = 1: setAct zeroes af and the frame's advance (af++) follows it,
// so the active frames of a move with startup s and a active frames are af = s+1 .. s+a.

// Free ground states: the fighter takes new commands and turns to face the opponent.
const FREE = {idle: 1, walkF: 1, walkB: 1, crouch: 1, guard: 1, guardC: 1};

function setAct(F, act) { F.act = act; F.af = 0; F.hit = 0; }

// Forward and back buttons for the fighter's facing.
function fwdBit(F) { return F.face > 0 ? BTN.R : BTN.L; }
function backBit(F) { return F.face > 0 ? BTN.L : BTN.R; }

// The command the buttons ask for, or null. By priority: dash (DASH press, back + DASH = back dash, or a double
// tap forward), jump (U held), guard (GUARD, low with D), crouch (D), walk forward or back.
function readCommand(S, F, bits) {
  if (bits & ~F.prev & BTN.DASH) return bits & backBit(F) ? 'dashB' : 'dashF';
  if (doubleTapDir(S, F, bits) === fwdBit(F)) return 'dashF';
  if (bits & BTN.U) return 'jump';
  if (bits & BTN.GUARD) return bits & BTN.D ? 'guardC' : 'guard';
  if (bits & BTN.D) return 'crouch';
  if (bits & fwdBit(F)) return 'walkF';
  if (bits & backBit(F)) return 'walkB';
  return null;
}

// Starts what a command asks for (null = idle). Holding the same walk, crouch or guard keeps its af counting.
function startCommand(S, F, cmd) {
  const act = cmd === 'jump' ? 'jumpSquat' : cmd || 'idle';
  if (act === F.act) return;
  setAct(F, act);
  if (act === 'dashF' || act === 'dashB') simEmit(S, 'dash', F);
}

// Length in frames of the timed actions; the others last until something ends them.
function actLength(F) {
  switch (F.act) {
    case 'jumpSquat': return CFG.jump.squat;
    case 'landing': return F.land;
    case 'dashF': return CFG.dash.f.n;
    case 'dashB': return CFG.dash.b.n;
    default: return Infinity;
  }
}

// Dash speed on frame af (1..n): integer interpolation from v0 to v1.
function dashSpeed(d, af) { return d.v0 + Math.trunc((d.v1 - d.v0) * (af - 1) / Math.max(1, d.n - 1)); }

// Horizontal speed of a ground action on its frame af.
function groundSpeed(F) {
  switch (F.act) {
    case 'walkF': return F.face * CFG.walk.f;
    case 'walkB': return -F.face * CFG.walk.b;
    case 'dashF': return F.face * dashSpeed(CFG.dash.f, F.af);
    case 'dashB': return -F.face * dashSpeed(CFG.dash.b, F.af);
    default: return 0;
  }
}

// End of the squat: the jump goes forward or back by the direction held now, relative to the facing.
function takeoff(S, F, bits) {
  setAct(F, 'air'); F.air = true; F.vy = CFG.jump.v;
  F.vx = bits & fwdBit(F) ? F.face * CFG.jump.vxF : bits & backBit(F) ? F.face * CFG.jump.vxB : 0;
  simEmit(S, 'jump', F);
}

// Physics finds the touchdown after this frame's advance, so this frame is the landing's first (af = 1).
function touchdown(S, F) {
  setAct(F, 'landing'); F.af = 1; F.land = CFG.jump.land;
  simEmit(S, 'land', F);
}

// One frame of a fighter's action: end a finished timed action, read a command in a free state,
// advance af, then set the ground speed (in the air the takeoff speed is kept).
function actionStep(S, F, bits) {
  if (F.af >= actLength(F)) { if (F.act === 'jumpSquat') takeoff(S, F, bits); else setAct(F, 'idle'); }
  if (FREE[F.act]) startCommand(S, F, readCommand(S, F, bits));
  F.af++;
  if (!F.air) F.vx = groundSpeed(F);
}
