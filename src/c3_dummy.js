// Training dummy: what the 'casuale' dummy presses. Pure and deterministic like the sim: it reads and advances only S
// (S.dum[side] and the seeded S.rng).

// The six things it picks from, with equal weight: stand still, walk forward, walk back, crouch, jump, guard (hold back).
const DUMMY_ACTS = [F => 0, F => fwdBit(F), F => backBit(F), F => BTN.D, F => BTN.U, F => backBit(F)];

// The buttons for side this frame (an integer of BTN bits): 0 for 'fermo'.
function dummyInput(S, side) {
  if (S.dummy !== 'casuale') return 0;
  const d = S.dum[side], k = CFG.dummy;
  if (d.left <= 0) { d.act = simRand(S, DUMMY_ACTS.length); d.left = k.min + simRand(S, k.max - k.min + 1); }
  d.left--;
  return DUMMY_ACTS[d.act](fighterOf(S, side));
}
