// --- posa.js: "Pose di Ren", key poses made with buttons (13/11/2026, second version). ---
// Denis (13/11): "mi puoi fare un'anteprima del personaggio dove posso muoverlo come voglio [...] per fare nuove
// animazioni? così capisci meglio cosa intendo"; his choice A: key poses as his sheets have them (posa 1, 2, 3...),
// a "Riproduci" that shows them in a row at one fixed speed, the timing told in words (the notes). The first version
// had handles to drag on every part; Denis found it too hard ("NO BRO TROPPO DIFFICILE") and chose ready positions,
// buttons only. A pose is a set of choices:
//   Braccio avanti / dietro   Guardia, Avanti, Alto, Viso, Gomito, Basso   (avanti = the lead arm, his left)
//   Mano avanti / dietro      Pugno, Socchiusa, Aperta            (one button each, it goes round)
//   Gamba avanti / dietro     A terra, Ginocchio, Calcio, Basso
//   Busto                     Dritto, Avanti, Indietro
//   Altezza                   Normale, Basso, Alto
//   Passo                     Indietro, Qui, Avanti, 2 avanti      (where he stands: one step is PZ_STEP)
// and the body follows by itself: a straight arm or an elbow brings its shoulder in (the hips and chest turn, the
// weight goes forward), a kick leans him back and lifts him on the standing leg (whose foot turns on its tip), both
// feet off the floor make a jump, a new place is reached by steps (one foot then the other, each lifted, none
// sliding), the eyes stay on the opponent. The positions are the kit's (kit.js, loaded before this: the same Ren, base
// guard and solver). A change eases in (a few frames); "Riproduci" plays pose 1 to 2 to ...: 24 frames each, unless a
// pose has its own timing (t frames to reach it, h frames held, e its ease: 'snap' faster and faster into it, a
// strike; 'out' fast then slowing; default even): the animations Claude made (14/11) have it.
// Touch and mouse: the buttons (a drag on the picture turns the view, a double tap brings back the side view).
// Keyboard and controller: rows and choices (the hint). The poses are saved by themselves in the page's database
// (collection "animazioni", one document per animation, format 2: the choices by name), where Claude reads them, and
// on this device when the database is not there. Documents of the first version (format 1) stay and are not listed.

const PZ = {
  T: 24, hold: 40, back: 24, rest: 14,   // playing: frames from a pose to the next (0.4 s), held on the last, back to the first, held there
  ease: 12,                              // frames a changed pose takes to be reached (0.2 s: from rest to rest)
  max: 24,                               // poses in one animation
  poses: [], cur: 0, row: 0, kb: false, play: null, undo: [], D: null, Daf: NaN, ver: 0, lastPush: 0,
  id: null, name: 'Nuova animazione', note: '', db: null, col: null, list: [], loaded: false, edited: false, busy: false,
  dirty: false, retry: 0, timer: 0, pad: {}, padRep: {}, ui: {},
  watch: true,                           // the preview, Anteprima (the animations one after another), or the editor (Modifica)
};
// the rows of choices: the pose's field, its label, its values [name, label]
const PZ_ARMV = [['guardia', 'Guardia'], ['avanti', 'Avanti'], ['alto', 'Alto'], ['viso', 'Viso'], ['gomito', 'Gomito'], ['basso', 'Basso']];
const PZ_LEGV = [['terra', 'A terra'], ['ginocchio', 'Ginocchio'], ['calcio', 'Calcio'], ['alto', 'Alto'], ['basso', 'Basso'], ['dietro', 'Dietro']];
const PZ_ROWS = [
  {key: 'bA', label: 'Braccio avanti', vals: PZ_ARMV},
  {key: 'bD', label: 'Braccio dietro', vals: PZ_ARMV},
  {key: 'mani', label: 'Mani', hands: [['mA', 'Mano avanti'], ['mD', 'Mano dietro']]},
  {key: 'gA', label: 'Gamba avanti', vals: PZ_LEGV},
  {key: 'gD', label: 'Gamba dietro', vals: PZ_LEGV},
  {key: 'busto', label: 'Busto', vals: [['dritto', 'Dritto'], ['avanti', 'Avanti'], ['indietro', 'Indietro']]},
  {key: 'alt', label: 'Altezza', vals: [['normale', 'Normale'], ['basso', 'Basso'], ['alto', 'Alto']]},
  {key: 'passo', label: 'Passo', vals: [['indietro', 'Indietro'], ['qui', 'Qui'], ['avanti', 'Avanti'], ['avanti2', '2 avanti']]},
];
const PZ_HANDS = [['pugno', 'Pugno', 1], ['socchiusa', 'Socchiusa', .55], ['aperta', 'Aperta', 0]];   // [name, label, how closed]
const PZ_GUARD = {bA: 'guardia', mA: 'pugno', bD: 'guardia', mD: 'socchiusa', gA: 'terra', gD: 'terra', busto: 'dritto', alt: 'normale', passo: 'qui'};   // the kit's guard
const PZ_STEP = .3, PZ_PASSO = {indietro: -1, qui: 0, avanti: 1, avanti2: 2};   // m a step; where each place is, in steps
const PZ_EASES = ['snap', 'out', 'lin', 'smooth'];
const PZ_FX = ['colpo', 'forte', 'energia', 'onda'];   // an impact, a heavy one, energy between the hands, an energy wave sent forward
const PZ_HIT = {mA: ['LeftHand'], mD: ['RightHand'], eA: ['LeftForeArm'], eD: ['RightForeArm'], gA: ['LeftLeg'], gD: ['RightLeg'], pA: ['LeftToeBase'], pD: ['RightToeBase'], due: ['LeftHand', 'RightHand']};   // the limb an effect comes from (the bones whose middle it is)
// the animations' groups (a document's cat), in the list's order; Denis's own have none
const PZ_CATS = ['Colpi', 'Calci', 'Combinazioni', 'Difese', 'Movimenti', 'Speciali'];
const PZ_KEY = 'pose-ren-v2';   // localStorage: {id, doc} of the animation open on this device
const pzClone = o => JSON.parse(JSON.stringify(o));
const pzC = (x, a, b) => Math.max(a, Math.min(b, x));
const pzSame = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const pzNew0 = () => Object.assign({}, PZ_GUARD, {note: ''});
// a pose read back (the database's or this device's): each choice checked against the row's values
function pzFill(p) {
  const o = pzNew0();
  if (!p || typeof p !== 'object') return o;
  for (const r of PZ_ROWS) {
    if (r.vals && r.vals.some(v => v[0] === p[r.key])) o[r.key] = p[r.key];
    if (r.hands) for (const [k] of r.hands) if (PZ_HANDS.some(h => h[0] === p[k])) o[k] = p[k];
  }
  if (typeof p.note === 'string') o.note = p.note.slice(0, 300);
  // its timing, when it has one (frames to reach it, frames held, the ease)
  if (Number.isFinite(p.t) && p.t >= 2 && p.t <= 240) o.t = Math.round(p.t);
  if (Number.isFinite(p.h) && p.h >= 0 && p.h <= 240) o.h = Math.round(p.h);
  if (PZ_EASES.includes(p.e)) o.e = p.e;
  // beyond the buttons (Claude's animations): the whole body's turn and flip (deg, counted on: 360 is round once),
  // a higher jump (m), a place in metres (instead of the steps), a glide (one long low step), an effect on reaching
  // the pose and the limb it comes from
  for (const [k, lo, hi] of [['giro', -1080, 1080], ['capriola', -1080, 1080], ['vola', 0, 1], ['x', -3, 3]]) if (Number.isFinite(p[k]) && p[k] >= lo && p[k] <= hi) o[k] = p[k];
  if (p.scatto === true) o.scatto = true;
  if (PZ_FX.includes(p.fx)) o.fx = p.fx;
  if (p.scia === true) o.scia = true;
  if (PZ_HIT[p.hit]) o.hit = p.hit;
  return o;
}
function pzEase(u, e) { u = pzC(u, 0, 1); return e === 'snap' ? rkEase(u, 'snap') : e === 'out' ? 1 - rkEase(1 - u, 'snap') : e === 'lin' ? u : rnSm(u); }

// --- What a pose asks of the body: the style (on top of the kit's base guard), the feet, the arms' positions ---
function pzBody(c) {
  const b = {yaw: 0, chest: 0, leanL: 0, lx: 0, dip: 0, head: 0, jump: 0};
  if (c.busto === 'avanti') { b.leanL += 16; b.lx += .04; b.dip += .015; }
  else if (c.busto === 'indietro') { b.leanL -= 14; b.lx -= .05; }
  if (c.alt === 'basso') b.dip += .13; else if (c.alt === 'alto') b.dip -= .07;
  // a straight arm or an elbow: its shoulder in (the kit's palm: hips -20, chest -25, 10 cm on; its elbow: -18, -24);
  // both: square to him (the double palm)
  const sA = c.bA === 'avanti' || c.bA === 'gomito', sD = c.bD === 'avanti' || c.bD === 'gomito';
  if (sA && sD) { b.yaw += 4; b.chest += 6; b.lx += .05; }
  else if (sA) { b.yaw -= 18; b.chest -= 23; b.lx += .07; }
  else if (sD) { b.yaw += 20; b.chest += 26; b.lx += .07; }
  if (c.bA === 'basso' || c.bD === 'basso') { b.leanL += 8; b.dip += .04; }   // (a low strike or block: in and down a little)
  // a kick leans him away from it and lifts him on the standing leg (the kit's kick: -34 degrees, 17 cm up); a knee less
  if (c.gA === 'calcio') { b.leanL -= 26; b.dip -= .15; b.yaw -= 5; b.lx -= .08; }
  else if (c.gA === 'alto') { b.leanL -= 34; b.dip -= .17; b.yaw -= 6; b.lx -= .1; }   // (the head kick: further back, up on the standing leg)
  else if (c.gA === 'dietro') { b.leanL += 26; b.dip -= .05; b.lx += .04; }   // (a kick behind: the chest goes the other way)
  else if (c.gA === 'ginocchio') { b.leanL -= 4; b.dip -= .06; b.lx -= .03; }
  else if (c.gA === 'basso') { b.leanL -= 8; b.dip -= .03; b.lx -= .04; }
  if (c.gD === 'calcio') { b.leanL -= 22; b.dip -= .12; b.yaw -= 25; b.chest += 10; b.lx += .1; }   // (the rear hip comes forward)
  else if (c.gD === 'alto') { b.leanL -= 30; b.dip -= .14; b.yaw -= 28; b.chest += 12; b.lx += .1; }
  else if (c.gD === 'dietro') { b.leanL += 24; b.dip -= .05; b.lx += .02; }
  else if (c.gD === 'ginocchio') { b.leanL -= 2; b.dip -= .05; b.lx += .03; }
  else if (c.gD === 'basso') { b.leanL -= 10; b.dip -= .03; b.yaw -= 12; b.lx += .08; }
  if (c.gA !== 'terra' && c.gD !== 'terra') b.jump = .35 + (c.vola || 0);   // both feet off the floor: a jump (higher with vola)
  b.leanL = pzC(b.leanL, -42, 32);
  b.head = -.5 * b.leanL;   // (the eyes stay on the opponent)
  b.tx = Number.isFinite(c.x) ? c.x : (PZ_PASSO[c.passo] || 0) * PZ_STEP;   // where he stands (m along the line)
  b.giro = c.giro || 0; b.flip = c.capriola || 0; b.glide = c.scatto ? 1 : 0;   // (the turn and flip: graphics, pzRootXf)
  return b;
}
// the feet: along the line (m, from the guard's spot), up, the heel (deg), the turn on the tip (deg), the toes' point in
// the air (deg: > 0 pointed, < 0 flexed, the sole forward: the kit's kick strikes with it) and how much in the air (0..1)
function pzFeet(c, b) {
  const F = {L: {x: 0, up: 0, heel: 0, yaw: 0, point: 30, air: 0, tx: b.tx}, R: {x: 0, up: 0, heel: 0, yaw: 0, point: 30, air: 0, tx: b.tx}};
  if (c.gA === 'ginocchio') Object.assign(F.L, {x: -.12, up: .5, point: 40, air: 1});
  else if (c.gA === 'calcio') Object.assign(F.L, {x: .27, up: 1, point: -5, air: 1});
  else if (c.gA === 'basso') Object.assign(F.L, {x: .2, up: .3, point: 0, air: 1});   // (a low kick: the sole at the shin, the leg not quite straight)
  else if (c.gA === 'alto') Object.assign(F.L, {x: .1, up: 1.24, point: -5, air: 1});   // (at the head)
  else if (c.gA === 'dietro') Object.assign(F.L, {x: -.85, up: .8, point: 10, air: 1});   // (behind him at the middle, the heel first)
  if (c.gD === 'ginocchio') Object.assign(F.R, {x: .55, up: .55, point: 40, air: 1});   // (the rear knee comes forward, up in front)
  else if (c.gD === 'calcio') Object.assign(F.R, {x: 1.15, up: .9, point: -5, air: 1});
  else if (c.gD === 'basso') Object.assign(F.R, {x: 1, up: .28, point: 0, air: 1});   // (the rear leg reaching forward low, nearly straight)
  else if (c.gD === 'alto') Object.assign(F.R, {x: .88, up: 1.14, point: -5, air: 1});
  else if (c.gD === 'dietro') Object.assign(F.R, {x: -.24, up: .7, point: 10, air: 1});
  // the standing foot turned on its tip (the kit's kick: 30 degrees), up on its ball to turn (a flat foot cannot
  // turn on the floor without sliding)
  if (c.gD === 'terra') F.R.yaw = c.gA === 'calcio' || c.gA === 'alto' ? -30 : c.gA === 'basso' ? -15 : 0;
  if (c.gA === 'terra') F.L.yaw = c.gD === 'calcio' || c.gD === 'alto' ? -40 : c.gD === 'basso' ? -20 : 0;
  for (const s of ['L', 'R']) if (F[s].yaw) F[s].heel = 12;
  if (((c.giro || 0) % 360 + 360) % 360 > 1) for (const s of ['L', 'R']) if (pzDown(F[s])) F[s].heel = 12;   // (turned round: up on the ball it turns on)
  if (b.jump) { F.L.up += b.jump; F.R.up += b.jump; }
  return F;
}
// The arms' positions, as the kit's poses are: (A, hand) -> {p: wrist, f: fingers' way, n: palm's way, e: elbow
// hint, s: 1 a straight wrist (the fist continues the forearm)}. A: the kit's frames (l: along the fight line
// [forward, up, side], c: the chest's [across, up, forward]), shoulders sL / sR, the chest C1, the guard G.
const PZ_UP = () => RB_UP.clone(), PZ_LN = () => RB_LINE.clone();
const pzPalm = () => ({f: PZ_UP().addScaledVector(RB_LINE, .2).normalize(), n: PZ_LN().addScaledVector(RB_UP, -.12).normalize(), s: 0});   // the kit's palm strike
function pzLow(A, sh, fwd, side, h) {   // side: 1 the lead (left) arm, -1 the rear
  const F = A.c([0, 0, 1]); F.y = 0; F.normalize();   // (where the chest faces, level)
  const p = sh.clone().addScaledVector(F, fwd).addScaledVector(RB_UP, -.36).addScaledVector(A.c([side, 0, 0]), .08), e = A.c([side, .2, -.2]).normalize();   // (a little out: the arm clear of the chest)
  return h === 'aperta' ? {p, e, f: F.clone().addScaledVector(RB_UP, -.25).normalize(), n: PZ_UP().negate(), s: 0} : {p, e, f: p.clone().sub(sh).normalize(), n: A.c([-side, 0, 0]), s: 1};
}
const PZ_ARM = {
  L: {
    guardia: (A, h) => Object.assign({p: A.G.L.p, e: A.G.L.e}, h === 'aperta' ? {f: A.l([.55, .8, -.15]).normalize(), n: A.l([0, -.2, -1]).normalize(), s: 0} : {f: A.G.L.f, n: A.G.L.n, s: 0}),
    avanti: (A, h) => Object.assign({p: A.sL.clone().addScaledVector(RB_LINE, .965 * A.armL), e: A.l([0, -1, .3]).normalize()}, h === 'aperta' ? pzPalm() : {f: PZ_LN(), n: PZ_UP().negate(), s: 1}),
    alto: (A, h) => Object.assign({p: A.l([.2, .33, -.02]).add(A.sL), e: A.l([.35, -1, .55]).normalize()}, h === 'aperta' ? {f: PZ_UP().addScaledVector(RB_LINE, .15).normalize(), n: PZ_LN(), s: 0} : {f: PZ_UP(), n: A.l([0, 0, -1]), s: 1}),
    viso: (A, h) => h === 'aperta' ? {p: A.l([.18, .2, -.04]).add(A.sL), e: A.l([.15, -1, .25]).normalize(), f: PZ_UP(), n: PZ_LN(), s: 0}   // (the kit's cover)
      : {p: A.l([.2, .16, -.08]).add(A.sL), e: A.l([.2, -1, .3]).normalize(), f: A.l([.3, 1, 0]).normalize(), n: A.l([0, 0, -1]), s: 1},
    // (the kit's elbow: the upper arm level, the elbow forward at shoulder height, the forearm folded flat before the
    // chest, the wrist straight; in the chest's frame, so that the forearm stays before the chest however he turns)
    gomito: (A) => ({p: A.c([-.08, .12, .22]).add(A.C1), e: A.c([.25, -.1, 1]).normalize(), f: A.c([-1, 0, .1]).normalize(), n: A.c([0, -1, 0]), s: 1}),
    // (a low strike or block: the arm reaching down and forward the way the chest faces, the elbow out: never across
    // the body, however he turns)
    basso: (A, h) => pzLow(A, A.sL, .32, 1, h),
  },
  R: {
    guardia: (A) => ({p: A.G.R.p, e: A.G.R.e, f: A.G.R.f, n: A.G.R.n, s: 0}),
    avanti: (A, h) => Object.assign({p: A.sR.clone().addScaledVector(RB_LINE, .965 * A.armR).addScaledVector(RB_UP, -.06), e: A.c([-.2, -1, -.1]).normalize()}, h === 'aperta' ? pzPalm() : {f: PZ_LN(), n: PZ_UP().negate(), s: 1}),
    alto: (A, h) => Object.assign({p: A.l([.22, .31, .05]).add(A.sR), e: A.c([-.8, -.45, .1]).normalize()}, h === 'aperta' ? {f: PZ_UP(), n: PZ_LN(), s: 0} : {f: PZ_UP(), n: A.c([1, 0, 0]), s: 1}),
    viso: (A, h) => h === 'aperta' ? {p: A.c([-.17, .2, .12]).add(A.C1), e: A.c([-.3, -1, -.1]).normalize(), f: PZ_UP().addScaledVector(RB_LINE, .1).normalize(), n: PZ_LN(), s: 0}   // (the kit's rHead)
      : {p: A.c([-.04, .26, .2]).add(A.C1), e: A.c([-.4, -1, -.2]).normalize(), f: A.c([1, .4, .2]).normalize(), n: A.c([0, 0, -1]), s: 0},   // (the kit's rChin)
    // (the elbow forward at shoulder height, the forearm folded across the chest toward the lead side, the fist before
    // the chest: in the chest's frame, as the rear shoulder sits behind it)
    gomito: (A) => ({p: A.c([.08, .12, .22]).add(A.C1), e: A.c([-.25, -.1, 1]).normalize(), f: A.c([1, 0, .1]).normalize(), n: A.c([0, -1, 0]), s: 1}),
    basso: (A, h) => pzLow(A, A.sR, .34, -1, h),
  },
};
// A pose's numbers (body, feet, and per arm the weight of each position|hand), so two poses mix and a pose eases
// into another: every change is continuous.
function pzTarget(c) {
  const b = pzBody(c), f = pzFeet(c, b), dL = pzDown(f.L), dR = pzDown(f.R);
  return {b, f, arm: {L: {[c.bA + '|' + c.mA]: 1}, R: {[c.bD + '|' + c.mD]: 1}}, pivot: dL !== dR ? (dL ? 'L' : 'R') : 'H'};
}
const pzDown = x => x.up < .005 && x.air < .05;   // (a foot on the floor)
// the guard's ankles and hip joints along the fight line and up (m; tests/posa.js checks them against the page's guard)
const PZ_LEG = {L: {ax: .4, ay: .1505, hx: .0698, hy: .7614}, R: {ax: -.4869, ay: .1505, hx: -.0902, hy: .7804}};
// a at 0 .. b at 1 over the change's own time raw (0..1), eased by e. Not all at once: the body (hips, chest, head)
// gets there first, by 80% of the change, the arms last, from 20% of it: the force goes from the feet through the
// hips and chest to the hand (Ren's brief), and a strike lands with the body already set behind it.
function pzMixT(a, b, raw, e) {
  raw = pzC(raw, 0, 1);
  const u = pzEase(raw, e), ub = pzEase(raw / .8, e), ua = pzEase((raw - .2) / .8, e);
  const num = (x, y, k) => { const o = {}; for (const j in x) o[j] = x[j] + (y[j] - x[j]) * k; return o; };
  const w = (x, y, k) => { const o = {}; for (const j in x) o[j] = x[j] * (1 - k); for (const j in y) o[j] = (o[j] || 0) + y[j] * k; for (const j in o) if (o[j] < 1e-4) delete o[j]; return o; };
  const B = num(a.b, b.b, ub), f = {L: num(a.f.L, b.f.L, u), R: num(a.f.R, b.f.R, u)};
  // the turn and the flip pivot on the foot that stays on the floor all through the change (none: on the hips); about
  // the hips they wait for the feet to leave the floor and end before they land again (the feet never sweep it)
  const stay = s => pzDown(a.f[s]) && pzDown(b.f[s]) && Math.abs(b.f[s].tx - a.f[s].tx) < 1e-6, sL = stay('L'), sR = stay('R');
  const pivot = sL !== sR ? (sL ? 'L' : 'R') : 'H';
  let heelT = null;
  {
    // (about the hips: both feet; on a foot: the other one) leaving the floor: the turn starts once it is off; landing:
    // the turn ends before it is down
    // the foot it turns on is up on its ball all through the turn: its heel goes up before it starts, down after it
    // ends (a flat foot turned about its tip would sweep the floor)
    const other = pivot === 'H' ? ['L', 'R'] : [pivot === 'L' ? 'R' : 'L'], up0 = other.some(s => pzDown(a.f[s])), down1 = other.some(s => pzDown(b.f[s]));
    let s0 = up0 ? .3 : 0, s1 = down1 ? .7 : 1;
    if (pivot !== 'H' && Math.abs(b.b.giro - a.b.giro) > .5) {
      const ha = a.f[pivot].heel, hb = b.f[pivot].heel, top = Math.max(12, ha, hb);
      if (ha < top - .5) s0 = Math.max(s0, .25);
      if (hb < top - .5) s1 = Math.min(s1, .75);
      heelT = {s: pivot, h: raw < s0 ? ha + (top - ha) * rnSm(raw / s0) : raw > s1 ? top + (hb - top) * rnSm((raw - s1) / (1 - s1)) : top};
    }
    const k = up0 && down1 ? (pivot === 'H' ? pzEase(raw, e) : ub) : pzEase((raw - s0) / (s1 - s0), e);
    B.giro = a.b.giro + (b.b.giro - a.b.giro) * k; B.flip = a.b.flip + (b.b.flip - a.b.flip) * k;
  }
  // a foot that leaves the floor goes up before it goes anywhere (and turns its toes down only once off it); one that
  // lands gets there first and comes down last: none drags its toes on the floor
  // (a jump, both feet off the floor, goes up and comes down with the feet, not ahead of them with the body: a body
  // that lands first would fold the legs up under it)
  const down = x => x.up < .005 && x.air < .05, ja = a.b.jump, jb = b.b.jump;
  const lifts = ['L', 'R'].some(s => down(a.f[s]) && !down(b.f[s])), lands = ['L', 'R'].some(s => !down(a.f[s]) && down(b.f[s]));
  B.jump = ja + (jb - ja) * (lifts ? rnSm(u / .85) : lands ? rnSm((u - .15) / .85) : u);
  for (const s of ['L', 'R']) {
    const fa = a.f[s], fb = b.f[s], off = down(fa) && !down(fb), on = !down(fa) && down(fb);
    let ku = u;
    if (!off && !on) {
      // a standing foot that turns (under a kick): up on its ball first, then the turn on its tip; back, the turn
      // first, then the heel down (a flat foot turning would slide on the floor)
      if (down(fa) && down(fb) && Math.abs(fb.yaw - fa.yaw) > .5) {
        const away = Math.abs(fb.yaw) > Math.abs(fa.yaw), kh = away ? rnSm(u / .4) : rnSm((u - .6) / .4), ky = away ? rnSm((u - .25) / .75) : rnSm(u / .75);
        f[s].heel = fa.heel + (fb.heel - fa.heel) * kh; f[s].yaw = fa.yaw + (fb.yaw - fa.yaw) * ky;
      }
    } else {
      const kx = off ? rnSm((u - .15) / .85) : rnSm(u / .85);
      ku = off ? rnSm(u / .85) : rnSm((u - .15) / .85);
      for (const k of ['x', 'air', 'point', 'heel', 'yaw']) f[s][k] = fa[k] + (fb[k] - fa[k]) * kx;
    }
    f[s].up = fa.up - ja + (fb.up - jb - fa.up + ja) * ku + B.jump;   // (its own height over the jump's)
  }
  if (heelT) f[heelT.s].heel = heelT.h;
  B.tx = a.b.tx + (b.b.tx - a.b.tx) * rnSm(raw);   // (the body's way to a new place: even, whatever the strike's ease)
  // to a new place by steps, each foot lifted and travelling inside its lift (it leaves the floor before it moves and
  // stops before it lands: none slides): forward the front (left) foot first, back the rear one; a step at a time
  // (a glide, scatto: steps of up to 60 cm, the feet low and close behind each other: a dash)
  const fwd = b.b.tx >= a.b.tx, gl = b.b.glide > .5, size = gl ? .6 : PZ_STEP, win = gl ? [0, .7, .25] : [0, .6, .4], lift = gl ? .02 : .045;
  for (const s of ['L', 'R']) {
    const d = b.f[s].tx - a.f[s].tx;
    if (Math.abs(d) < 1e-6) continue;
    const n = Math.max(1, Math.ceil(Math.abs(d) / size - .25)), q = raw * n, k = Math.min(n - 1, Math.floor(q)), r = q - k;
    const v = pzC((r - ((s === 'L') === fwd ? win[0] : win[2])) / win[1], 0, 1);
    f[s].tx = a.f[s].tx + d / n * (k + rnSm((v - .15) / .7));
    f[s].up += lift * Math.min(1, Math.abs(d) / n / .15) * Math.sin(Math.PI * v) ** 2;
  }
  // a foot that goes from one side of the hips to the other off the floor (the rear one coming up in front, the front
  // one kicking behind, a kick swung from front to back) goes round under them, not through them: its angle about the
  // hip and its distance from it mixed, the distance kept short enough to pass well above the floor (the leg folds
  // under him as it swings); away from its ends only (it leaves the floor and meets it straight up and down)
  for (const s of ['L', 'R']) {
    const fa = a.f[s], fb = b.f[s];
    if (down(fa) && down(fb)) continue;
    const G0 = PZ_LEG[s], rel = (x, bd) => { const h = G0.ax + x.x + x.tx - G0.hx - bd.lx - bd.tx, v = G0.ay + x.up - G0.hy + bd.dip - bd.jump; return {th: Math.atan2(h, -v), r: Math.hypot(h, v)}; };
    const A = rel(fa, a.b), Z = rel(fb, b.b);
    if (A.th * Z.th >= 0 || Math.min(Math.abs(A.th), Math.abs(Z.th)) < .14) continue;
    const off = down(fa), on = down(fb), kt = off ? rnSm((u - .15) / .85) : on ? rnSm(u / .85) : u, kr = off ? rnSm(u / .85) : on ? rnSm((u - .15) / .85) : u;
    const th = A.th + (Z.th - A.th) * kt, hx = G0.hx + B.lx + B.tx, hy = G0.hy - B.dip + B.jump, c = Math.cos(th);
    let r = A.r + (Z.r - A.r) * kr;
    if (c > .05) r = Math.min(r, (hy - G0.ay - .12 * Math.sin(Math.PI * kt)) / c);
    const wp = rnSm(kt / .3) * rnSm((1 - kt) / .3);
    f[s].x += (hx + r * Math.sin(th) - G0.ax - f[s].tx - f[s].x) * wp;
    f[s].up += (hy - r * c - G0.ay - f[s].up) * wp;
  }
  return {b: B, f, arm: {L: w(a.arm.L, b.arm.L, ua), R: w(a.arm.R, b.arm.R, ua)}, pivot};
}
// the pose drawn at fighter state F: while playing, the mix of two poses; else the pose being edited, reached from
// wherever the drawing was over PZ.ease frames (a tap in the middle of a change does not jump)
function pzDrawn(F) {
  const P = PZ.poses;
  if (!P.length) return pzTarget(PZ_GUARD);
  if (F.af === PZ.Daf && PZ.D && PZ.Dv === PZ.ver) return PZ.D;
  let D;
  if (PZ.play && P.length > 1) D = pzPlayAt(pzPlayT(F.af));
  else {
    const T = pzTarget(P[Math.min(PZ.cur, P.length - 1)]);
    if (PZ.D && PZ.Dv !== PZ.ver) PZ.tr = {from: PZ.D, f0: F.af};   // (a change: it starts here)
    const tr = PZ.tr;
    if (tr && F.af < tr.f0) tr.f0 = F.af;
    const raw = tr ? (F.af - tr.f0) / (PZ.ease * Math.max(1, 1.5 * Math.abs(T.b.tx - tr.from.b.tx) / PZ_STEP)) : 1;   // (a step: 18 frames each)
    D = raw >= 1 ? T : pzMixT(tr.from, T, raw);
    if (raw >= 1) PZ.tr = null;
  }
  PZ.D = D; PZ.Daf = F.af; PZ.Dv = PZ.ver;
  return D;
}
// Playing: pose 1 to 2 to ... n, each reached in its own t frames (PZ.T when it has none) with its ease and held its
// own h, the last held PZ.hold more, then back to the first (longer when there are steps back) and held there; again.
function pzTimeline() {
  const P = PZ.poses, key = PZ.ver;
  if (PZ.tl && PZ.tl.key === key) return PZ.tl;
  const seg = [];
  let t = 0;
  for (let i = 1; i < P.length; i++) { const T = P[i].t || PZ.T, H = P[i].h || 0; seg.push({i, t0: t, T, H, e: P[i].e}); t += T + H; }
  const steps = Math.round(Math.abs(pzTarget(P[P.length - 1]).b.tx - pzTarget(P[0]).b.tx) / PZ_STEP), back = PZ.back + 14 * steps;
  return PZ.tl = {key, seg, run: t, back, len: t + PZ.hold + back + PZ.rest};
}
function pzPlayAt(t) {
  const P = PZ.poses, n = P.length, L = pzTimeline(), at = PZ.play.at;
  t = ((t % L.len) + L.len) % L.len;
  for (const g of L.seg) {
    if (t < g.t0 + g.T) { at.a = g.i - 1; at.b = g.i; at.back = false; return pzMixT(pzTarget(P[g.i - 1]), pzTarget(P[g.i]), (t - g.t0) / g.T, g.e); }
    if (t < g.t0 + g.T + g.H) { at.a = at.b = g.i; at.back = false; return pzTarget(P[g.i]); }
  }
  t -= L.run;
  if (t < PZ.hold) { at.a = at.b = n - 1; at.back = false; return pzTarget(P[n - 1]); }
  t -= PZ.hold;
  if (t < L.back) {
    at.a = n - 1; at.b = 0; at.back = true;
    const A0 = pzTarget(P[n - 1]), B0 = pzTarget(P[0]), near = (x, y) => x + ((((y - x) % 360) + 540) % 360 - 180);   // (y's turn nearest x)
    B0.b.giro = near(A0.b.giro, B0.b.giro); B0.b.flip = near(A0.b.flip, B0.b.flip);
    return pzMixT(A0, B0, t / L.back);
  }
  at.a = at.b = 0; at.back = true;
  return pzTarget(P[0]);
}

// --- The act: style, feet, arms, head, the legs in the air, hands ---
RB.pin.posa = 1;
RS.torso.soft = {lo: .04, hi: .06};   // (this page's arms go anywhere: the chest's push fades in at its top and bottom, style.js)
RB.softKnee = true;   // (and its legs too: a standing foot's knee rule fades in, body.js)
RB.softHeel = true;   // (and a standing leg near its stretch lifts its heel gradually, body.js)
RB.styleFor.posa = (y, F) => {
  const D = pzDrawn(F), b = D.b, open = Math.min(1, Math.abs(D.f.L.tx - D.f.R.tx) / PZ_STEP);   // (a step half done: the stance wider)
  y.yaw = b.yaw; y.chest = b.chest; y.leanL = b.leanL; y.lx = b.lx + b.tx; y.dip = .004 + b.dip - b.jump + .03 * open; y.head = b.head;
  rkBase(y);
};
RB.feetFor.posa = (s, c, st, L, F) => {
  const f = pzDrawn(F).f[s];
  rkFoot(s, c, st, L, f.heel * (1 - f.air), f.yaw, f.x + f.tx, f.up, 0);   // (in the air the leg sets the foot: pzKickLeg below)
  c.knee = 1 - rnSm((f.up - .02) / .13);   // (the knee over the toes near the floor only: higher up, the toes' way says nothing)
};
// A leg off the floor, as kit.js's rkKickLeg sets it, with two weights: the leg turned about its hip-ankle line until
// its knee points its own way by wk, the foot set against the shin (the rest ankle bent by point degrees) by wf. The
// knee's own way is the leg's line turned a quarter forward about the body's side: down -> forward (standing), forward
// -> up (a kick), up -> back, back -> down (a kick behind); never along the leg, however it swings. The turn is the
// knee's own part, not a full turn by a share: halfway it never goes round the other side (a turn of nearly 180
// degrees by a share would flip its way as the angle passes 180).
function pzKickLeg(md, p, s, point, wk, wf, wo) {
  const T = THREE, L = RB.leg[s], W = rbFK(md, p, RB.W), A = W.p[L.iu].clone(), K = W.p[L.il].clone(), E = W.p[L.ia].clone();
  const dir = E.sub(A).normalize(), off = K.sub(A), pole = new T.Vector3().crossVectors(dir, RB_SIDE);
  off.addScaledVector(dir, -off.dot(dir));
  if (wo > 0 && off.lengthSq() > 1e-6 && pole.lengthSq() > 1e-6) {
    const bend = rnSm((off.length() - .02) / .05);
    off.normalize(); pole.normalize();
    // the knee's way: over the toes (as a standing foot's, low down), its own (higher up, wk), mixed as ways
    // (no angle to share out: halfway it never goes round the other side); then from the solver's by wo
    const toes = L.sd.clone().applyQuaternion(RB.con[s].Q).setY(0); toes.addScaledVector(dir, -toes.dot(dir));
    let want = toes.lengthSq() > 1e-6 ? toes.normalize().multiplyScalar(1 - wk).addScaledVector(pole, wk) : pole.clone();
    if (want.lengthSq() < 1e-8) want = pole.clone();
    want.normalize().multiplyScalar(wo * bend).addScaledVector(off, 1 - wo * bend);
    if (want.lengthSq() > 1e-8) {
      want.normalize();
      const phi = Math.atan2(new T.Vector3().crossVectors(off, want).dot(dir), off.dot(want));
      const par = md.bones[L.iu].p, qU = W.q[L.iu].clone().premultiply(new T.Quaternion().setFromAxisAngle(dir, phi));
      const footW = W.q[L.ia].clone(), shinW = qU.clone().multiply(new T.Quaternion().fromArray(p.q, L.il * 4));
      W.q[par].clone().invert().multiply(qU).toArray(p.q, L.iu * 4);
      shinW.invert().multiply(footW).toArray(p.q, L.ia * 4);   // (the foot keeps its own turn: only the knee goes round)
    }
  }
  if (wf <= 0) return;
  const R = RK.restLeg || (RK.restLeg = {});
  const r = R[s] || (R[s] = (() => {
    const rest = mdRest(md), qL = new T.Quaternion().fromArray(rest.q, L.il * 4), qF = new T.Quaternion().fromArray(rest.q, L.ia * 4);
    return {qF, hinge: L.hu.clone().applyQuaternion(qL.clone().invert()).normalize()};
  })());
  const want = r.qF.clone().premultiply(new T.Quaternion().setFromAxisAngle(r.hinge, point * RB_R));
  new T.Quaternion().fromArray(p.q, L.ia * 4).slerp(want, wf).toArray(p.q, L.ia * 4);
}
// where a two-bone arm from shoulder sh, its wrist at tgt, puts its elbow for hint e (upper and lower lengths a, b),
// as rsArm does (the chest's own push left out): a point, so that two can be mixed
function pzElbow(sh, tgt, e, a, b) {
  const dir = tgt.clone().sub(sh), full = dir.length(), d = pzC(full, Math.abs(a - b) + 1e-3, (a + b) * .995);
  dir.multiplyScalar(1 / (full || 1e-9));
  const P = e.clone().addScaledVector(dir, -e.dot(dir));
  if (P.lengthSq() < 1e-8) P.set(0, -1, 0).addScaledVector(dir, dir.y);
  P.normalize();
  const cos = (a * a + d * d - b * b) / (2 * a * d), sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  return sh.clone().addScaledVector(dir, a * cos).addScaledVector(P, a * sin);
}
RB.post.push((md, p, F) => {
  if (F.act !== 'posa' || F.air) return;
  const D = pzDrawn(F), W = rbFK(md, p, RB.W), ix = md.index, C1 = W.p[ix.Spine01].clone();
  const c = a => rsChest(md, W, a, new THREE.Vector3()), l = a => rsVec(a, new THREE.Vector3());
  const sL = W.p[ix.LeftArm].clone(), sR = W.p[ix.RightArm].clone();
  const armL = sL.distanceTo(W.p[ix.LeftForeArm]) + W.p[ix.LeftForeArm].distanceTo(W.p[ix.LeftHand]);
  const armR = sR.distanceTo(W.p[ix.RightForeArm]) + W.p[ix.RightForeArm].distanceTo(W.p[ix.RightHand]);
  const G = {L: {p: l(RS.lead.dir).normalize().multiplyScalar(RS.lead.reach * armL).add(sL), f: l(RS.lead.fing).normalize(), n: l(RS.lead.palm).normalize(), e: l(RS.lead.elbow).normalize()},
    R: {p: c(RS.rear.pos).add(C1), f: c(RS.rear.fing).normalize(), n: c(RS.rear.palm).normalize(), e: c(RS.rear.elbow).normalize()}};
  const A = {W, ix, C1, c, l, sL, sR, armL, armR, G};
  for (const s of ['L', 'R']) {   // each arm: its positions mixed by their weights (one, but while it changes)
    const t = {p: new THREE.Vector3(), f: new THREE.Vector3(), n: new THREE.Vector3(), e: new THREE.Vector3(), s: 0};
    const sh = s === 'L' ? sL : sR, n = s === 'L' ? 'Left' : 'Right', ua = sh.distanceTo(W.p[ix[n + 'ForeArm']]), la = W.p[ix[n + 'ForeArm']].distanceTo(W.p[ix[n + 'Hand']]);
    const all = Object.entries(D.arm[s]).map(([k, w]) => { const [pos, hand] = k.split('|'); return {w, a: PZ_ARM[s][pos](A, hand)}; });
    let best = all[0];
    for (const x of all) {
      const {a, w} = x;
      t.p.addScaledVector(a.p, w); t.f.addScaledVector(a.f, w); t.n.addScaledVector(a.n, w); t.e.addScaledVector(a.e, w); t.s += a.s * w;
      if (w > best.w) best = x;
    }
    for (const k of ['f', 'n', 'e']) { if (t[k].lengthSq() < 1e-6) t[k].copy(best.a[k]); t[k].normalize(); }   // (two ways that cancel: the stronger one)
    if (all.length > 1) {
      // between two positions the elbow turns about the arm's line by the mixed angle of where each puts it, from its
      // outer side: it goes round by the side, as an arm that rises does (the hints' ways mixed can lie along the arm
      // half way, and the elbow would swing round it at once)
      const dir = t.p.clone().sub(sh).normalize(), r0 = c([s === 'L' ? 1 : -1, -.5, 0]).normalize();
      r0.addScaledVector(dir, -r0.dot(dir));
      if (r0.lengthSq() < 1e-4) r0.copy(c([0, 0, 1])).addScaledVector(dir, -c([0, 0, 1]).dot(dir));
      r0.normalize();
      // (each position's angle about its own arm's line, from that arm's outer side: the same for it all through the
      // change; measured about the line the arm has now, a position far from it could come out on the inner side and
      // turn over. Each counts by how far its elbow is off its line too: an elbow near it has no clear side)
      const r1 = new THREE.Vector3().crossVectors(dir, r0), out = c([s === 'L' ? 1 : -1, -.5, 0]).normalize(), fw = c([0, 0, 1]);
      const ang = x => {
        const d0 = x.a.p.clone().sub(sh).normalize(), q0 = out.clone().addScaledVector(d0, -out.dot(d0));
        if (q0.lengthSq() < 1e-4) q0.copy(fw).addScaledVector(d0, -fw.dot(d0));
        q0.normalize();
        const q1 = new THREE.Vector3().crossVectors(d0, q0), v = pzElbow(sh, x.a.p, x.a.e, ua, la).sub(sh);
        v.addScaledVector(d0, -v.dot(d0));
        return {a: Math.atan2(v.dot(q1), v.dot(q0)), w: x.w * v.length()};
      };
      // (the angles from the arm's outer side, never unwrapped round another one: an elbow is on the outer half of the
      // arm, and the mean of two goes round by that side; picking the shorter way flips when the two are opposite)
      const g = all.map(ang);
      let sum = 0, ws = 0;
      for (const x of g) { sum += x.w * x.a; ws += x.w; }
      const th = ws > 1e-6 ? sum / ws : ang(best).a;
      t.e.copy(r0).multiplyScalar(Math.cos(th)).addScaledVector(r1, Math.sin(th));
    }
    // (a wrist near or past the arm's reach comes in smoothly: the arm never snaps straight as it gets there)
    const dv = t.p.clone().sub(sh), dl = dv.length() / (ua + la);
    if (dl > .9) t.p.copy(sh).addScaledVector(dv, (.9 + .09 * (1 - Math.exp(-(dl - .9) / .09))) / dl);
    rsArm(md, p, rbFK(md, p, RB.W), s, t.p, t.e, t.f, t.n, 1, t.s);
  }
  mdBoneTurn(p, ix.Head, MD_Y, RK.g.headYaw);   // the eyes on the opponent (the nod: the style's)
  for (const s of ['L', 'R']) {
    const f = D.f[s];
    // a foot off the floor: its knee's way is set here (over the toes low down, the leg's own higher up), not left to
    // the solver's carried leg, whose knee can turn over as the leg swings far; on the floor, the solver's
    const wo = rnSm(f.up / .1), wk = Math.max(f.air, rnSm((f.up - .05) / .15));
    if (wo > 0 || f.air > 0) pzKickLeg(md, p, s, f.point, wk, f.air, wo);
  }
});
RN.hooks.applied.push((it, F) => {   // the hands: a fist, half closed, open (fingers together, the thumb along them)
  if (!it.fingers || F.act !== 'posa') return;
  const D = pzDrawn(F), k = {L: 0, R: 0};
  for (const s of ['L', 'R']) for (const [key, w] of Object.entries(D.arm[s])) k[s] += w * PZ_HANDS.find(h => h[0] === key.split('|')[1])[2];
  for (let i = 0; i < it.fingers.length; i++) rkSetFinger(it, i, /^Left/.test(it.fingers[i].name) ? k.L : k.R, true);
});

// (the sash's simulation sees the body turned and flipped as it is drawn: it hangs from him as gravity takes it, not
// stuck to him upside down. The viewer sets the yaw alone each frame: last frame's flip goes first)
RN.hooks.applied.push((it, F) => {
  if (F.act !== 'posa' || !PZ.D || !it.pose) return;
  it.root.rotation.set(0, it.root.rotation.y, 0);
  const xf = pzRootXf(PZ.D, it.pose, mdData(it.key)), q0 = it.root.quaternion.clone();
  if (xf.q.w < 1 - 1e-9 || xf.t.lengthSq() > 0) { it.root.quaternion.multiply(xf.q); it.root.position.add(xf.t.clone().multiplyScalar(it.scale).applyQuaternion(q0)); }
});

// --- The whole body turned and flipped (Claude's spins and somersaults): graphics only, on top of the pose ---
// The turn (giro, about the vertical) pivots on the one foot on the floor (its ball: it turns where it stands), on
// the hips over the floor when he is in the air or on both feet; the flip (capriola, about his side axis) on the hips.
// (A change of pivot while turned would jump: the animations change it only when the turn is a whole one.) Returns
// the model-space transform X -> q X + t for drawn state D on pose p.
function pzRootXf(D, p, md) {
  const o = PZ.xf || (PZ.xf = {q: new THREE.Quaternion(), t: new THREE.Vector3()});
  const th = (D.b.giro || 0) * RB_R, ph = (D.b.flip || 0) * RB_R;
  o.q.identity(); o.t.set(0, 0, 0);
  if (Math.abs(th) < 1e-6 && Math.abs(ph) < 1e-6) return o;
  const T = THREE, W = rbFK(md, p, RB.W), ix = md.index, pv = D.pivot || 'H';
  const P = (pv === 'H' ? W.p[ix.Hips] : RB.con[pv].G).clone().setY(0);   // (a foot: its toe tip on the floor, where it turns)
  const q = new T.Quaternion().setFromAxisAngle(RB_UP, th), t = P.clone().sub(P.clone().applyQuaternion(q));
  if (ph) {
    const H = W.p[ix.Hips].clone().applyQuaternion(q).add(t), qf = new T.Quaternion().setFromAxisAngle(RB_SIDE.clone().applyQuaternion(q), ph);
    t.applyQuaternion(qf).add(H).sub(H.clone().applyQuaternion(qf)); q.premultiply(qf);
  }
  o.q.copy(q); o.t.copy(t);
  return o;
}
// The effects of a pose (fx) while it plays: an impact (colpo, forte: a burst at the limb, the picture shaking, a white
// flash for a heavy one), energy between the hands (energia), an energy wave sent forward from them (onda); a trail
// behind the limb on its way into the pose (scia). Each from the play's time: an animation looks the same each time.
const PZ_FXC = {};
function pzFxInit(VW) {
  const T = THREE, tex = draw => { const c = document.createElement('canvas'); c.width = c.height = 128; draw(c.getContext('2d')); return new T.CanvasTexture(c); };
  const sprite = (m, add) => { const s = new T.Sprite(new T.SpriteMaterial({map: m, transparent: true, depthWrite: false, depthTest: false, blending: add ? T.AdditiveBlending : T.NormalBlending})); s.visible = false; s.renderOrder = 6; VW.scene.add(s); return s; };
  const burst = tex(g => {   // a white core, rays of Ren's cyan
    g.translate(64, 64);
    for (let i = 0; i < 12; i++) { g.rotate(Math.PI / 6); g.fillStyle = i % 2 ? 'rgba(120,235,255,.95)' : 'rgba(255,255,255,.95)'; g.beginPath(); g.moveTo(0, -5); g.lineTo(i % 2 ? 46 : 62, 0); g.lineTo(0, 5); g.fill(); }
    const r = g.createRadialGradient(0, 0, 0, 0, 0, 34); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.5, 'rgba(210,248,255,.9)'); r.addColorStop(1, 'rgba(53,216,255,0)');
    g.fillStyle = r; g.beginPath(); g.arc(0, 0, 34, 0, 7); g.fill();
  });
  const glow = tex(g => { const r = g.createRadialGradient(64, 64, 0, 64, 64, 64); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.25, 'rgba(190,245,255,.95)'); r.addColorStop(.6, 'rgba(53,216,255,.4)'); r.addColorStop(1, 'rgba(53,216,255,0)'); g.fillStyle = r; g.fillRect(0, 0, 128, 128); });
  PZ_FXC.burst = [0, 1, 2].map(() => sprite(burst, false)); PZ_FXC.glow = sprite(glow, true); PZ_FXC.ball = sprite(glow, true); PZ_FXC.ring = sprite(burst, true);
  // the trail: a ribbon of N points, its alpha from the head (the limb) to the tail
  const N = PZ_FXC.N = 16, g = new T.BufferGeometry(), idx = [];
  g.setAttribute('position', new T.BufferAttribute(new Float32Array(N * 6), 3)); g.setAttribute('aA', new T.BufferAttribute(new Float32Array(N * 2), 1));
  for (let i = 0; i < N - 1; i++) { const a = 2 * i; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  g.setIndex(idx);
  const m = new T.ShaderMaterial({transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
    vertexShader: 'attribute float aA; varying float vA; void main(){ vA = aA; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'varying float vA; void main(){ gl_FragColor = vec4(vec3(.21, .85, 1.) * vA + vec3(.6) * vA * vA, vA); }'});
  PZ_FXC.trail = new T.Mesh(g, m); PZ_FXC.trail.frustumCulled = false; PZ_FXC.trail.visible = false; PZ_FXC.trail.renderOrder = 5; VW.scene.add(PZ_FXC.trail);
  PZ_FXC.hist = []; PZ_FXC.calm = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const fl = document.createElement('div'); fl.id = 'pzFlash'; fl.style.cssText = 'position:fixed;inset:0;z-index:2;pointer-events:none;background:#fff;opacity:0';
  document.getElementById('stage').after(fl); PZ_FXC.flash = fl;
}
// where the limb of key k is (world): the middle of its bones
function pzLimb(it, k) {
  const names = PZ_HIT[k] || PZ_HIT.mA, v = new THREE.Vector3(), w = new THREE.Vector3();
  for (const n of names) v.add(it.bones.find(b => b.name === n).getWorldPosition(w));
  return v.multiplyScalar(1 / names.length);
}
// the effects at play time t (frames into the loop); returns the camera's shake (m)
function pzFx(VW, it, t, cam) {
  const C = PZ_FXC, L = pzTimeline(), P = PZ.poses, shake = {x: 0, y: 0};
  for (const b of C.burst) b.visible = false;
  C.glow.visible = C.ball.visible = C.ring.visible = false;
  let flash = 0, trail = null, bi = 0;
  for (const g of L.seg) {
    const pose = P[g.i], arr = g.t0 + g.T, age = t - arr, end = arr + g.H + (L.seg[L.seg.indexOf(g) + 1] ? L.seg[L.seg.indexOf(g) + 1].T * .5 : 20);
    if ((pose.fx === 'colpo' || pose.fx === 'forte') && age >= 0 && age < 12 && bi < C.burst.length) {
      const big = pose.fx === 'forte', k = age / 12, b = C.burst[bi++];
      if (!C.at || C.at.key !== g.i + ':' + Math.floor(PZ.loop || 0)) C.at = {key: g.i + ':' + Math.floor(PZ.loop || 0), p: pzLimb(it, pose.hit || 'mA')};
      b.position.copy(C.at.p); b.visible = true; b.scale.setScalar((big ? .55 : .36) * (.5 + k * .9)); b.material.opacity = 1 - k * k; b.material.rotation = g.i * 1.7 + k * .6;
      const a = (big ? .035 : .012) * (1 - k) * (1 - k);
      shake.x += a * Math.sin(t * 2.9 + g.i); shake.y += a * Math.cos(t * 3.7 + g.i);
      if (big) flash = Math.max(flash, .38 * (1 - age / 6));
    }
    if (pose.fx === 'energia' && t >= arr - g.T * .7 && t < end) {   // charging: it grows on the way in, pulses while held
      const k = pzC((t - (arr - g.T * .7)) / (g.T * .7), 0, 1), out = pzC((end - t) / 6, 0, 1);
      C.glow.position.copy(pzLimb(it, pose.hit || 'due')); C.glow.visible = true;
      C.glow.scale.setScalar((.18 + .3 * k) * (1 + .08 * Math.sin(t * .9)) * out); C.glow.material.opacity = .9 * out;
    }
    if (pose.fx === 'onda' && age >= 0 && age < 40) {   // the wave: from the hands, forward along the line, growing, then gone
      if (!C.wave || C.wave.key !== g.i + ':' + Math.floor(PZ.loop || 0)) C.wave = {key: g.i + ':' + Math.floor(PZ.loop || 0), p: pzLimb(it, pose.hit || 'due')};
      const k = age / 40, dir = new THREE.Vector3(Math.cos(VW.yaw - F3_YAW), 0, -Math.sin(VW.yaw - F3_YAW));
      C.ball.position.copy(C.wave.p).addScaledVector(dir, 3.2 * k); C.ball.visible = true; C.ball.scale.setScalar(.45 + .5 * k); C.ball.material.opacity = 1 - k * k * k;
      C.ring.position.copy(C.wave.p); C.ring.visible = age < 10; C.ring.scale.setScalar(.4 + age * .06); C.ring.material.opacity = 1 - age / 10;
      if (age < 8) { const a = .02 * (1 - age / 8); shake.x += a * Math.sin(t * 3.3); shake.y += a * Math.cos(t * 2.1); }
    }
    if (pose.scia && t >= g.t0 - 1 && t < arr + 10) trail = {g, pose, age: t - arr};
  }
  // the trail: the limb's last places (drawn frames), smoothed, its tail fading; gone over 10 frames after arrival
  if (trail) {
    const key = trail.g.i + ':' + Math.floor(PZ.loop || 0);
    if (C.trKey !== key) { C.trKey = key; C.hist = []; }
    if (trail.age < 0) { C.hist.push(pzLimb(it, trail.pose.hit || 'mA')); if (C.hist.length > 10) C.hist.shift(); }
    const H = C.hist, N = C.N;
    if (H.length >= 2) {
      const pos = C.trail.geometry.attributes.position, al = C.trail.geometry.attributes.aA, fade = trail.age < 0 ? 1 : 1 - trail.age / 10;
      const camDir = cam.getWorldDirection(new THREE.Vector3());
      for (let i = 0; i < N; i++) {   // a Catmull-Rom curve through the samples, head (newest) last
        const f = i / (N - 1) * (H.length - 1), j = Math.min(H.length - 2, Math.floor(f)), u = f - j, P0 = H[Math.max(0, j - 1)], P1 = H[j], P2 = H[j + 1], P3 = H[Math.min(H.length - 1, j + 2)];
        const pt = new THREE.Vector3(), u2 = u * u, u3 = u2 * u;
        for (const c of ['x', 'y', 'z']) pt[c] = .5 * (2 * P1[c] + (-P0[c] + P2[c]) * u + (2 * P0[c] - 5 * P1[c] + 4 * P2[c] - P3[c]) * u2 + (-P0[c] + 3 * P1[c] - 3 * P2[c] + P3[c]) * u3);
        const tan = new THREE.Vector3().subVectors(P2, P1), side = new THREE.Vector3().crossVectors(tan, camDir).normalize().multiplyScalar(.045 * (i / (N - 1)) + .005);
        pos.setXYZ(2 * i, pt.x + side.x, pt.y + side.y, pt.z + side.z); pos.setXYZ(2 * i + 1, pt.x - side.x, pt.y - side.y, pt.z - side.z);
        const a = (i / (N - 1)) ** 1.5 * .85 * fade; al.setX(2 * i, a); al.setX(2 * i + 1, a);
      }
      pos.needsUpdate = al.needsUpdate = true; C.trail.visible = true;
    } else C.trail.visible = false;
  } else { C.trail.visible = false; C.trKey = null; }
  if (C.calm) { flash = 0; shake.x = shake.y = 0; }
  const fo = flash.toFixed(3); if (C.flash.style.opacity !== fo) C.flash.style.opacity = fo;
  return shake;
}

// --- Editing: a choice, the hands, the poses ---
function pzPush() {
  PZ.undo.push({poses: pzClone(PZ.poses), cur: PZ.cur});
  if (PZ.undo.length > 80) PZ.undo.shift();
}
function pzStop() { if (PZ.play) pzPlay(); }
function pzChoose(key, v) {
  const P = PZ.poses[PZ.cur];
  if (!P || P[key] === v) return;
  pzStop(); pzPush();
  P[key] = v; pzChanged();
}
function pzHand(key, dir) {   // the next (or previous) hand: pugno, socchiusa, aperta, round again
  const P = PZ.poses[PZ.cur];
  if (!P) return;
  const i = PZ_HANDS.findIndex(h => h[0] === P[key]);
  pzChoose(key, PZ_HANDS[(i + (dir || 1) + PZ_HANDS.length) % PZ_HANDS.length][0]);
}
function pzStepRow(dir) {   // keys and controller: the selected row's previous or next choice
  const r = PZ_ROWS[PZ.row], P = PZ.poses[PZ.cur];
  if (!P) return;
  if (r.hands) { pzHand(r.hands[dir < 0 ? 0 : 1][0]); return; }
  const i = r.vals.findIndex(v => v[0] === P[r.key]);
  pzChoose(r.key, r.vals[pzC(i + dir, 0, r.vals.length - 1)][0]);
}
function pzRowGo(dir) { PZ.row = (PZ.row + dir + PZ_ROWS.length) % PZ_ROWS.length; PZ.kb = true; PZ.ui.dirty = true; }
function pzUndo() {
  const u = PZ.undo.pop();
  if (!u) { pzStatus('Niente da annullare'); return; }
  pzStop();
  PZ.poses = u.poses; PZ.cur = Math.min(u.cur, u.poses.length - 1);
  pzChanged();
}
function pzGuard() {
  const P = PZ.poses[PZ.cur];
  if (!P) return;
  const G = Object.assign({}, PZ_GUARD, {note: P.note});
  if (pzSame(G, P)) return;
  pzStop(); pzPush(); PZ.poses[PZ.cur] = G; pzChanged();
}
function pzGo(i) {
  if (!PZ.poses.length) return;
  pzStop();
  const j = pzC(i, 0, PZ.poses.length - 1);
  if (j === PZ.cur) return;
  PZ.cur = j; PZ.ver++; PZ.ui.dirty = true;
}
function pzAdd() {
  if (PZ.poses.length >= PZ.max) { pzStatus('Massimo ' + PZ.max + ' pose'); return; }
  pzStop(); pzPush();
  const P = pzClone(PZ.poses[PZ.cur] || pzNew0()); P.note = '';
  PZ.poses.splice(PZ.cur + 1, 0, P); PZ.cur++; PZ.pop = PZ.cur;
  pzChanged();
}
function pzDel() {
  if (PZ.poses.length < 2) { pzStatus('Serve almeno una posa'); return; }
  pzStop(); pzPush();
  PZ.poses.splice(PZ.cur, 1); PZ.cur = Math.min(PZ.cur, PZ.poses.length - 1);
  pzChanged(); pzStatus('Posa eliminata (Annulla la riporta)');
}
function pzPlay() {
  if (PZ.play) { PZ.play = null; PZ.ver++; PZ.ui.dirty = true; return; }
  if (PZ.poses.length < 2) { pzStatus('Fai almeno 2 pose («+ Posa») per riprodurle'); return; }
  PZ.play = {f0: VW.F.af + (RN_D.k || 0), at: {a: 0, b: 1, back: false}}; PZ.ver++; PZ.ui.dirty = true;
}
// the play's own time at drawn frame af (held where it is while the preview's pause holds it)
function pzPlayT(af) { return PZ.play.paused !== undefined ? PZ.play.paused : af - PZ.play.f0; }
function pzPause() {   // (the preview: the play held on the frame it is at, or going on from there)
  if (!PZ.play) { pzPlay(); return; }
  const af = VW.F.af + (RN_D.k || 0);
  if (PZ.play.paused !== undefined) { PZ.play.f0 = af - PZ.play.paused; delete PZ.play.paused; } else PZ.play.paused = af - PZ.play.f0;
  PZ.ver++; PZ.ui.dirty = true;
}
const pzRun = () => { if (!PZ.play && PZ.poses.length > 1) pzPlay(); };   // (playing, if it is not)
// the preview (Anteprima): the animations one after another, in the list's order (Denis's own first, then Claude's by kind), round
// again at either end; Modifica opens the editor on the one playing
function pzOrder() { return [null].concat(PZ_CATS).flatMap(c => PZ.list.filter(a => a.cat === c)); }
function pzNext(dir) {
  const L = pzOrder();
  if (!L.length) return;
  const i = L.findIndex(a => a.id === PZ.id);
  pzOpen(L[i < 0 ? (dir > 0 ? 0 : L.length - 1) : (i + dir + L.length) % L.length]);
}
function pzWatch(on) {
  PZ.watch = on; document.body.classList.toggle('pzWatch', on);
  if (on) pzRun(); else { pzStop(); pzAnims(false); }
  pzHint(); pzResize(); PZ.ui.dirty = true;
}
function pzView() { const side = Math.abs(VW.yaw - F3_YAW) < .02; VW.yaw = side ? F3_YAW - Math.PI / 4 : F3_YAW; PZ.ui.dirty = true; }   // the game's side view, or three-quarters

// --- Saving: the database (collection "animazioni"), this device, the data for Claude ---
const PZ_LEGENDA = 'Pose di Ren, formato 2 (preview/ren-anim/mods/posa.js). Ogni posa sono le scelte: bA braccio avanti e bD braccio dietro '
  + '(guardia, avanti, alto, viso, gomito, basso), mA mano avanti e mD mano dietro (pugno, socchiusa, aperta), gA gamba avanti e gD gamba dietro '
  + '(terra, ginocchio, calcio, alto, basso, dietro), busto (dritto, avanti, indietro), alt altezza (normale, basso, alto), passo (indietro, qui, '
  + 'avanti, avanti2: dove sta, a passi di 30 cm); note: le parole di Denis. Avanti = il lato sinistro, quello davanti. Riproduci: 24 fotogrammi da '
  + 'una posa alla successiva, se la posa non ha i suoi tempi: t fotogrammi per arrivarci, h fotogrammi ferma, e (snap: sempre più veloce, un colpo; '
  + 'out: veloce poi frena). Oltre i tasti (le mosse speciali di Claude): giro e capriola, tutto il corpo girato su se stesso (sul piede che resta '
  + 'a terra) e capovolto (in avanti; negativa: all\'indietro), in gradi contati (360 = un giro intero); vola, salto più alto (m); x, dove sta in '
  + 'metri (al posto di passo); scatto, ci arriva in un balzo radente; fx, un effetto all\'arrivo (colpo, forte: un impatto; energia: si raccoglie '
  + 'tra le mani; onda: un\'onda di energia in avanti) dal punto hit (mA, mD le mani, eA, eD i gomiti, gA, gD le ginocchia, pA, pD i piedi, due: '
  + 'le due mani); scia, la scia di quel punto. cat e ord: gruppo e ordine nell\'elenco delle animazioni.';
function pzDoc() {
  const d = {v: 2, name: PZ.name, note: PZ.note, frames: PZ.T, updated: Date.now(), legenda: PZ_LEGENDA, poses: pzClone(PZ.poses)};
  if (PZ.cat) d.cat = PZ.cat;
  if (PZ.ord !== undefined) d.ord = PZ.ord;
  return d;
}
function pzLoad(id, doc) {
  if (!doc || doc.v !== 2 || !Array.isArray(doc.poses) || !doc.poses.length) return false;
  PZ.id = id || null; PZ.name = typeof doc.name === 'string' && doc.name.trim() ? doc.name.slice(0, 60) : 'Animazione';
  PZ.note = typeof doc.note === 'string' ? doc.note.slice(0, 2000) : '';
  PZ.cat = PZ_CATS.includes(doc.cat) ? doc.cat : null; PZ.ord = Number.isFinite(doc.ord) ? doc.ord : undefined;
  PZ.poses = doc.poses.slice(0, PZ.max).map(pzFill); PZ.cur = 0; PZ.play = null; PZ.undo = [];
  PZ.ver++; PZ.ui.dirty = true;
  return true;
}
function pzLocal(doc) { try { localStorage.setItem(PZ_KEY, JSON.stringify({id: PZ.id, doc})); } catch (_) { /* (private window: the database alone) */ } }
// Claude's animations (ids c-...) stay as Claude made them: the first change to one makes Denis's own copy (in "Le
// tue"), which takes it and the ones after it
function pzMine() {
  if (!PZ.id || !/^c-/.test(PZ.id)) return;
  PZ.id = null; PZ.name = (PZ.name + ' (mia)').slice(0, 60); PZ.cat = null; PZ.ord = undefined;
  pzStatus('Copia tua: l\'originale di Claude resta com\'è');
}
function pzChanged() {
  pzMine();
  PZ.ver++; PZ.edited = true; PZ.ui.dirty = true;
  clearTimeout(PZ.timer); PZ.timer = setTimeout(pzSave, 700);   // (a burst of taps: one write once they pause)
}
async function pzSave() {
  clearTimeout(PZ.timer);
  const doc = pzDoc();
  pzLocal(doc);
  if (!PZ.col) { if (PZ.loaded) pzStatus('Salvato su questo dispositivo'); return; }
  if (PZ.busy) { PZ.dirty = true; return; }   // (one write at a time: the next one after it)
  PZ.busy = true; pzStatus('Salvataggio…');
  try {
    if (!PZ.id) PZ.id = PZ.col.doc().id;
    await PZ.col.doc(PZ.id).set(doc);
    PZ.retry = 0; pzStatus('Salvato');
  } catch (e) {
    const code = e && e.code;
    if ((code === 'unavailable' || code === 'resource_exhausted') && PZ.retry < 2) { PZ.retry++; PZ.dirty = true; await new Promise(r => setTimeout(r, 1500 + 1500 * Math.random())); }
    else { PZ.retry = 0; pzStatus(pzErr(code)); if (code !== 'unavailable' && code !== 'resource_exhausted' && code !== 'quota_exceeded') PZ.col = null; }
  }
  PZ.busy = false;
  if (PZ.dirty) { PZ.dirty = false; pzSave(); }
}
function pzErr(code) {
  if (code === 'quota_exceeded') return 'Spazio pieno: non salvato';
  if (code === 'invalid_argument') return 'Qui non puoi salvare: resta su questo dispositivo';
  if (code === 'revoked' || code === 'not_granted' || code === 'capability_disabled' || code === 'capability_removed') return 'Salvataggio non disponibile: resta su questo dispositivo';
  return 'Connessione assente: salvo alla prossima modifica';
}
async function pzStore() {
  try { const s = JSON.parse(localStorage.getItem(PZ_KEY) || 'null'); if (s && s.doc && pzLoad(s.id, s.doc)) PZ.localDoc = s; } catch (_) { /* (none, or not readable) */ }
  pzStatus('Caricamento…');
  let db = null;
  try { const c = window.claude; db = c && typeof c.use === 'function' ? await c.use('db') : null; } catch (_) { db = null; }
  if (!db) { PZ.loaded = true; pzStatus('Salvo su questo dispositivo'); pzWatch(false); return; }
  PZ.db = db; PZ.col = db.collection('animazioni');
  const wait = setTimeout(() => { if (!PZ.loaded) pzStatus('Il salvataggio non risponde ancora'); }, 10000);
  PZ.col.orderBy('updated', 'desc').limit(300).onSnapshot(snap => {
    PZ.list = snap.docs.map(d => ({id: d.id, doc: d.data() || {}})).filter(a => a.doc.v === 2)
      .map(a => ({id: a.id, name: typeof a.doc.name === 'string' ? a.doc.name.slice(0, 60) : 'Animazione', updated: +a.doc.updated || 0, doc: a.doc,
        cat: PZ_CATS.includes(a.doc.cat) ? a.doc.cat : null, ord: Number.isFinite(a.doc.ord) ? a.doc.ord : 1e9}))
      .sort((a, b) => (a.cat ? PZ_CATS.indexOf(a.cat) : -1) - (b.cat ? PZ_CATS.indexOf(b.cat) : -1) || a.ord - b.ord || b.updated - a.updated);
    PZ.ui.list = true;
    if (snap.metadata.fromCache || PZ.loaded) return;
    clearTimeout(wait); PZ.loaded = true;
    // the first answer: the animation this device had open (unless its own copy is newer: one of Denis's own changed
    // here and not saved yet; a copy of one of Claude's never goes over it, the original opens); a first visit: the
    // first of the list. On the preview, playing; nothing to watch: the editor
    const L = PZ.localDoc, mine = L && PZ.list.find(a => a.id === L.id), open = mine || PZ.list.find(a => a.cat) || PZ.list[0];
    if (PZ.edited || (L && !/^c-/.test(L.id || '') && (!mine || (+L.doc.updated || 0) > mine.updated))) pzSave();
    else if (open) { pzLoad(open.id, open.doc); pzLocal(open.doc); pzStatus('Aperta «' + open.name + '»'); }
    else pzStatus('Pronto: le pose si salvano da sole');
    if (PZ.watch && PZ.list.length) pzRun(); else pzWatch(false);
  }, err => { clearTimeout(wait); PZ.loaded = true; pzStatus(pzErr(err && err.code)); if (err && err.code !== 'unavailable') PZ.col = null; pzWatch(false); });
}
function pzNewAnim() {
  pzStop();
  PZ.id = null; PZ.name = 'Animazione ' + (PZ.list.filter(a => !a.cat).length + 1); PZ.note = ''; PZ.cat = null; PZ.ord = undefined;
  PZ.poses = [pzNew0()]; PZ.cur = 0; PZ.undo = [];
  pzChanged(); pzSave(); pzAnims(false);
}
// an animation of the list (or the preview's next): opened on the preview and played from its start
function pzOpen(a) {
  pzStop();
  if (a.id !== PZ.id && pzLoad(a.id, a.doc)) { pzLocal(pzDoc()); pzStatus('Aperta «' + a.name + '»'); }
  pzAnims(false); pzWatch(true);
}
function pzCopy() {
  const txt = JSON.stringify(pzDoc());
  const show = () => { const t = document.getElementById('pzData'); t.hidden = false; t.value = txt; t.focus(); t.select(); pzStatus('Copia il testo qui sotto e incollalo a Claude'); };
  try { navigator.clipboard.writeText(txt).then(() => pzStatus('Dati copiati: incollali a Claude'), show); } catch (_) { show(); }
}

// --- The page: Ren on the left, the choices on the right (below him when the screen stands up) ---
function pzStatus(t) { const s = document.getElementById('pzSt'); if (s && s.textContent !== t) s.textContent = t; }
function pzBtn(label, f, id) {
  const b = document.createElement('button'); if (id) b.id = id;
  b.innerHTML = '<span></span>'; b.firstChild.textContent = label; b.addEventListener('click', f);
  return b;
}
function pzPress(b, on) { const v = on ? 'true' : 'false'; if (b.getAttribute('aria-pressed') !== v) b.setAttribute('aria-pressed', v); }
function pzRowsUi() {
  const P = PZ.poses[PZ.cur], at = PZ.play && PZ.play.at, show = at ? PZ.poses[at.b] : P;
  for (const r of PZ_ROWS) {
    const row = PZ.ui.rows[r.key];
    row.classList.toggle('kb', PZ.kb && PZ_ROWS[PZ.row] === r);
    if (!show) continue;
    if (r.hands) for (const [k, lab] of r.hands) { const b = PZ.ui.hands[k], h = PZ_HANDS.find(x => x[0] === show[k]), t = lab + ': ' + h[1]; if (b.firstChild.textContent !== t) b.firstChild.textContent = t; }
    else for (const b of row.querySelectorAll('button')) pzPress(b, show[r.key] === b.dataset.v);
  }
}
function pzStrip() {
  const box = PZ.ui.chips, n = PZ.poses.length, at = PZ.play && PZ.play.at;
  while (box.children.length > n) box.lastChild.remove();
  while (box.children.length < n) { const i = box.children.length, b = pzBtn(String(i + 1), () => pzGo(i)); b.className = 'chip'; b.setAttribute('aria-label', 'Posa ' + (i + 1)); box.appendChild(b); }
  [...box.children].forEach((b, i) => pzPress(b, at ? i === at.b : i === PZ.cur));
  if (PZ.pop !== undefined && box.children[PZ.pop]) { const b = box.children[PZ.pop]; b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop'); b.scrollIntoView({block: 'nearest', inline: 'nearest'}); PZ.pop = undefined; }
  PZ.ui.play.firstChild.textContent = PZ.play ? 'Ferma' : 'Riproduci'; pzPress(PZ.ui.play, !!PZ.play);
  PZ.ui.del.disabled = n < 2; PZ.ui.add.disabled = n >= PZ.max;
  const side = Math.abs(VW.yaw - F3_YAW) < .02; PZ.ui.view.firstChild.textContent = side ? 'Vista: lato' : 'Vista: 3/4';
}
function pzTitle() {
  const sm = document.querySelector('#name small'), at = PZ.play && PZ.play.at;
  const t = at ? (PZ.play.paused !== undefined ? 'In pausa · ' : 'Riproduzione · ') + (at.back ? 'torna alla posa 1' : at.a === at.b ? 'posa ' + (at.a + 1) : 'posa ' + (at.a + 1) + ' → ' + (at.b + 1))
    : 'Posa ' + (PZ.cur + 1) + ' di ' + PZ.poses.length + (PZ.name ? ' · ' + PZ.name : '');
  if (sm && sm.textContent !== t) sm.textContent = t;
}
function pzNotes(open) {
  const N = document.getElementById('pzN');
  if (open === undefined) open = N.hidden;
  N.hidden = !open; pzPress(document.getElementById('pzNb'), open);
  if (open) { pzNotesUi(); const A = document.getElementById('pzA'); if (A && !A.hidden) pzAnims(false); } else document.getElementById('pzData').hidden = true;
}
function pzNotesUi() {
  const N = document.getElementById('pzN');
  if (N.hidden) return;
  const a = document.activeElement, set = (id, v) => { const el = document.getElementById(id); if (el !== a && el.value !== v) el.value = v; };
  set('pzName', PZ.name); set('pzNote', PZ.note); set('pzPnote', (PZ.poses[PZ.cur] || {}).note || '');
  document.getElementById('pzPn').textContent = String(PZ.cur + 1);
}
// the animations' sheet: a button each, in groups (Denis's own first, then Claude's by kind)
function pzAnims(open) {
  const A = document.getElementById('pzA');
  if (open === undefined) open = A.hidden;
  A.hidden = !open; pzPress(document.getElementById('pzList'), open);
  if (open) { pzNotes(false); pzListUi(); }
}
function pzListUi() {
  const box = document.getElementById('pzAl');
  if (!box) return;
  box.textContent = '';
  const groups = [[null, 'Le tue']].concat(PZ_CATS.map(c => [c, c]));
  for (const [cat, title] of groups) {
    const items = PZ.list.filter(a => a.cat === cat);
    if (!items.length) continue;
    const h = document.createElement('h3'); h.textContent = title + ' · ' + items.length; box.appendChild(h);
    const row = document.createElement('div'); row.className = 'pzAr';
    for (const a of items) { const b = pzBtn(a.name, () => pzOpen(a)); b.dataset.id = a.id; pzPress(b, a.id === PZ.id); row.appendChild(b); }
    box.appendChild(row);
  }
  if (!box.children.length) { const p = document.createElement('p'); p.className = 'pzMsg'; p.textContent = 'Nessun\'animazione salvata.'; box.appendChild(p); }
}
// the preview's panel: the animation's kind and place in it, its name and words, the pause's state
function pzWatchUi() {
  if (!PZ.watch) return;
  const L = pzOrder(), a = L.find(x => x.id === PZ.id), set = (id, t) => { const e = document.getElementById(id); if (e.textContent !== t) e.textContent = t; };
  const group = a ? L.filter(x => x.cat === a.cat) : [];
  set('pzWc', a ? (a.cat || 'Le tue') + ' · ' + (group.indexOf(a) + 1) + ' di ' + group.length : PZ.loaded ? 'Non salvata' : 'Caricamento…');
  set('pzWn', PZ.name || 'Animazione'); set('pzWd', PZ.note || '');
  const held = !!(PZ.play && PZ.play.paused !== undefined), b = PZ.ui.pause, t = !PZ.play ? 'Riproduci' : held ? 'Riprendi' : 'Pausa';
  if (b.firstChild.textContent !== t) b.firstChild.textContent = t;
  pzPress(b, held);
  for (const id of ['pzNext', 'pzPrev']) document.getElementById(id).disabled = !L.length;
}
// the keys and the controller for the page's two halves, under the title (shown with a mouse)
function pzHint() {
  const hint = document.getElementById('hint');
  if (!hint) return;
  hint.innerHTML = PZ.watch
    ? '«Successiva» e «Precedente» cambiano animazione; trascina Ren per girarlo, doppio tocco per tornare di lato.'
      + '<span class=kb> Tastiera: frecce sinistra e destra cambiano animazione, spazio pausa, L elenco, M modifica.'
      + ' Controller: croce o dorsali cambiano animazione, A pausa, X elenco, Y o Start modifica.</span>'
    : 'Tocca le scelte a destra; trascina Ren per girarlo, doppio tocco per tornare di lato.'
      + '<span class=kb> Tastiera: frecce su e giù la riga, sinistra e destra la scelta, N nuova posa, [ ] cambia posa, P riproduci, G guardia, Ctrl+Z annulla, M anteprima.'
      + ' Controller: croce per righe e scelte, A nuova posa, B annulla, X guardia, Y riproduci, dorsali cambia posa, Start anteprima.</span>';
}
// (the one open, marked in place: the list is built again only when its animations change, never under a finger)
function pzListMark() { for (const b of document.querySelectorAll('#pzAl button[data-id]')) pzPress(b, b.dataset.id === PZ.id); }
// the camera: Ren in the middle of the space the panel leaves him (left of it, or above it), below the title
function pzResize() {
  const w = innerWidth, h = innerHeight, c = VW.camera, P = document.getElementById(PZ.watch ? 'pzW' : 'pzP').getBoundingClientRect(), top = document.getElementById('name').getBoundingClientRect().bottom + 4;
  const right = P.left > w * .25, x1 = right ? P.left : w, y1 = right ? h : P.top, y0 = Math.min(top, y1 - 120);
  const fw = Math.max(80, x1), fh = Math.max(80, y1 - y0), cx = x1 / 2, cy = (y0 + y1) / 2;
  const FW = 2 * Math.max(cx, w - cx), FH = 2 * Math.max(cy, h - cy);
  c.fov = 30; c.aspect = FW / FH; c.setViewOffset(FW, FH, FW / 2 - cx, FH / 2 - cy, w, h); c.updateProjectionMatrix();
  const t = Math.tan(c.fov * Math.PI / 360);
  VW.fit = Math.max(2 * FH / (fh * 2 * t), 1.6 * FW / (fw * 2 * t * c.aspect)) / .94;   // 2 m tall (Ren is 1.8), 1.6 m wide fit
}
function pzUi() {
  const css = document.createElement('style');
  css.textContent = `
#moves,#bottom>.row,#now{display:none!important}
#pzP{position:fixed;z-index:3;top:0;right:0;bottom:0;width:min(500px,57vw);box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:6px;overflow-y:auto;
  padding:calc(8px + env(safe-area-inset-top,0px)) max(14px,env(safe-area-inset-right,0px)) calc(8px + env(safe-area-inset-bottom,0px)) 14px;
  background:rgba(20,18,28,.82);border-left:1px solid var(--line);scrollbar-width:thin}
#bottom{right:min(500px,57vw)}
#pzW{position:fixed;z-index:3;top:0;right:0;bottom:0;width:min(300px,40vw);box-sizing:border-box;display:none;flex-direction:column;justify-content:center;gap:10px;
  padding:calc(10px + env(safe-area-inset-top,0px)) max(16px,env(safe-area-inset-right,0px)) calc(10px + env(safe-area-inset-bottom,0px)) 16px;
  background:rgba(20,18,28,.82);border-left:1px solid var(--line)}
body.pzWatch #pzW{display:flex}body.pzWatch #pzP{display:none}body.pzWatch #bottom{right:min(300px,40vw)}
#pzWi{display:flex;flex-direction:column;gap:3px;min-height:0;padding:0 2px 2px}
#pzWc{color:var(--orange);font-size:14px;letter-spacing:.06em}
#pzWn{font-family:var(--display);font-style:normal;font-weight:400;font-size:30px;line-height:1;letter-spacing:.03em}
#pzWd{color:var(--dim);font-size:15px;line-height:1.18;font-weight:600;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
#pzW button{width:100%;min-height:44px}
#pzW #pzNext{font-size:22px;min-height:54px;padding:12px 14px 11px;background:var(--orange);border-color:var(--orange);color:#1a0f05}
#pzW #pzPrev{font-size:18px;padding:9px 14px 8px}
#pzNext>span,#pzPrev>span{display:inline-flex;align-items:center;gap:10px}
#pzWt{display:flex;gap:6px}
#pzW #pzWt button{flex:1;min-width:0;font-size:15px;padding:7px 4px 6px}
.pzR{display:flex;align-items:center;gap:5px;flex-wrap:wrap;border-radius:4px;padding:1px 2px}
.pzR.kb{outline:2px solid var(--cyan);outline-offset:2px}
.pzL{flex:0 0 64px;color:var(--dim);font-size:13px;line-height:1.02}
#pzP button{font-size:14px;padding:4px 9px 3px}
#pzP .hand{min-width:142px;text-align:left}
#pzTopRow{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
#pzChips{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;padding:3px 2px;flex:1 1 60px;min-width:0;touch-action:pan-x}#pzChips::-webkit-scrollbar{display:none}
#pzChips .chip{flex:0 0 auto;min-width:36px}
#pzTools{display:flex;gap:5px;flex-wrap:wrap;margin-top:2px}
button:disabled{opacity:.4;cursor:default}
#pzInfo{display:block;font-family:var(--body);font-style:italic;font-size:13px;letter-spacing:.04em;color:var(--dim);text-shadow:0 1px 3px #000;transform:none;margin-top:2px}
#pzInfo #fps{display:inline;font-size:inherit;color:inherit}#pzInfo #fps:not(:empty)::before{content:" · "}
#pzN{position:fixed;z-index:5;left:50%;bottom:calc(10px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);width:min(560px,calc(100vw - 32px));max-height:calc(100vh - 20px);overflow:auto;box-sizing:border-box;
  background:rgba(20,18,28,.97);border:1px solid var(--line);padding:12px;display:flex;flex-direction:column;gap:8px;box-shadow:0 8px 30px rgba(0,0,0,.6)}
#pzN[hidden],#pzA[hidden]{display:none}
#pzA{position:fixed;z-index:5;left:50%;top:50%;transform:translate(-50%,-50%);width:min(760px,calc(100vw - 24px));max-height:calc(100vh - 16px);overflow:auto;box-sizing:border-box;
  background:rgba(20,18,28,.97);border:1px solid var(--line);padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px;box-shadow:0 8px 30px rgba(0,0,0,.6)}
#pzA h3{margin:6px 0 0;font:inherit;font-size:15px;color:var(--orange);letter-spacing:.04em}
#pzA .pzAr{display:flex;flex-wrap:wrap;gap:5px}
#pzA .pzAr button{font-size:14px;padding:4px 9px 3px}
#pzAtop{display:flex;align-items:center;gap:8px;position:sticky;top:-10px;background:rgba(20,18,28,.97);padding:4px 0}
#pzAtop .pzMsg{flex:1;min-width:0}
#pzN label{display:flex;flex-direction:column;gap:4px;color:var(--dim);font-size:14px}
#pzN input,#pzN textarea,#pzN select{font:inherit;font-style:normal;font-weight:600;font-size:16px;color:var(--ink);background:#0d0c13;border:1px solid var(--line);padding:6px 8px;user-select:text;-webkit-user-select:text;min-width:0}
#pzN textarea{resize:vertical}
#pzN .row{align-items:center}
@keyframes pzPop{0%{transform:skewX(-10deg) scale(.55)}60%{transform:skewX(-10deg) scale(1.18)}100%{transform:skewX(-10deg) scale(1)}}
.pop{animation:pzPop .28s ease-out}
@media (max-height:430px){#name{font-size:34px}#name small{font-size:14px}#pzP{gap:3px}#pzP button{font-size:13.5px;padding:3px 8px 2px}.pzL{font-size:12px}#pzP .hand{min-width:132px}}
@media (max-height:370px){#pzP{gap:2px}#pzP button{padding:2px 7px 1px}#pzW{gap:7px}#pzWn{font-size:26px}}
@media (pointer:coarse){#hint{display:none}}
@media (orientation:portrait){#pzP,#pzW{top:auto;left:0;width:auto;max-height:56vh;justify-content:flex-start;border-left:0;border-top:1px solid var(--line)}#bottom{display:none}}
@media (prefers-reduced-motion:reduce){.pop{animation:none}}`;
  document.head.appendChild(css);
  const P = document.createElement('div'); P.id = 'pzP';
  // the poses' row
  const top = document.createElement('div'); top.id = 'pzTopRow';
  const chips = document.createElement('div'); chips.id = 'pzChips'; chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', 'Pose');
  PZ.ui.chips = chips; PZ.ui.add = pzBtn('+ Posa', pzAdd, 'pzAdd'); PZ.ui.play = pzBtn('Riproduci', pzPlay, 'pzPlay');
  top.append(chips, PZ.ui.add, PZ.ui.play); P.appendChild(top);
  // the choices
  PZ.ui.rows = {}; PZ.ui.hands = {};
  for (const r of PZ_ROWS) {
    const row = document.createElement('div'); row.className = 'pzR'; row.setAttribute('role', 'group'); row.setAttribute('aria-label', r.label);
    const lab = document.createElement('span'); lab.className = 'pzL'; lab.innerHTML = r.label.replace(' ', '<br>'); row.appendChild(lab);
    if (r.hands) for (const [k, l] of r.hands) { const b = pzBtn(l, () => pzHand(k), 'pz_' + k); b.className = 'hand'; row.appendChild(b); PZ.ui.hands[k] = b; }
    else for (const [v, l] of r.vals) { const b = pzBtn(l, () => pzChoose(r.key, v)); b.dataset.v = v; row.appendChild(b); }
    row.addEventListener('pointerdown', () => { PZ.kb = false; PZ.row = PZ_ROWS.indexOf(r); PZ.ui.dirty = true; });
    PZ.ui.rows[r.key] = row; P.appendChild(row);
  }
  // the tools
  const tools = document.createElement('div'); tools.id = 'pzTools';
  PZ.ui.del = pzBtn('Elimina', pzDel, 'pzDel'); PZ.ui.view = pzBtn('Vista: lato', pzView, 'pzView'); PZ.ui.del.setAttribute('aria-label', 'Elimina la posa');
  tools.append(pzBtn('Annulla', pzUndo, 'pzUndo'), pzBtn('Guardia', pzGuard, 'pzGuard'), PZ.ui.del, pzBtn('Anteprima', () => pzWatch(true), 'pzWb'), pzBtn('Note', () => pzNotes(), 'pzNb'), PZ.ui.view);
  P.appendChild(tools);
  document.body.appendChild(P);
  // the preview: the animation playing (its kind and place in it, name, words), the next one, the one before, pause, the
  // list, the editor on it. (A tap leaves no focus on its button: space is the pause, not that button again.)
  const W = document.createElement('div'); W.id = 'pzW'; W.setAttribute('role', 'group'); W.setAttribute('aria-label', 'Anteprima delle animazioni');
  W.innerHTML = '<div id="pzWi"><span id="pzWc"></span><b id="pzWn"></b><span id="pzWd"></span></div>';
  const chev = d => '<svg viewBox="0 0 12 20" width="11" height="18" aria-hidden="true"><path d="' + (d > 0 ? 'M2.5 2.5l7 7.5-7 7.5' : 'M9.5 2.5l-7 7.5 7 7.5') + '" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const next = pzBtn('Successiva', () => pzNext(1), 'pzNext'), prev = pzBtn('Precedente', () => pzNext(-1), 'pzPrev'), wt = document.createElement('div'); wt.id = 'pzWt';
  next.firstChild.insertAdjacentHTML('beforeend', chev(1)); prev.firstChild.insertAdjacentHTML('afterbegin', chev(-1));
  next.setAttribute('aria-label', 'Animazione successiva'); prev.setAttribute('aria-label', 'Animazione precedente');
  PZ.ui.pause = pzBtn('Pausa', pzPause, 'pzPause');
  wt.append(PZ.ui.pause, pzBtn('Elenco', () => pzAnims(), 'pzList'), pzBtn('Modifica', () => pzWatch(false), 'pzEdit'));
  W.append(next, prev, wt);
  W.addEventListener('click', e => { if (e.detail > 0 && document.activeElement && document.activeElement.blur) document.activeElement.blur(); });
  document.body.appendChild(W); document.body.classList.toggle('pzWatch', PZ.watch);
  // the saving's state and the frames per second: a line under the title
  const info = document.createElement('small'); info.id = 'pzInfo';
  const st = document.createElement('span'); st.id = 'pzSt'; st.setAttribute('role', 'status'); info.appendChild(st);
  const fps = document.getElementById('fps'); if (fps) info.appendChild(fps);
  document.getElementById('name').appendChild(info);
  pzHint();
  // the notes (for Claude): the animation's name and words, each pose's own, the saved animations, the data
  const N = document.createElement('div'); N.id = 'pzN'; N.hidden = true; N.setAttribute('role', 'dialog'); N.setAttribute('aria-label', 'Note per Claude');
  N.innerHTML = '<label>Nome dell\'animazione<input id="pzName" maxlength="60" autocomplete="off"></label>'
    + '<label>Note per Claude: i tempi e cosa deve succedere<textarea id="pzNote" rows="3" maxlength="2000" placeholder="Es. dalla 2 alla 3 velocissimo, la 4 tenuta un attimo"></textarea></label>'
    + '<label>Nota della posa <span id="pzPn">1</span><input id="pzPnote" maxlength="300" autocomplete="off" placeholder="Es. qui colpisce"></label>'
    + '<textarea id="pzData" rows="3" readonly hidden aria-label="I dati delle pose"></textarea>'
    + '<div class="row"></div>';
  N.lastChild.append(pzBtn('Copia i dati', pzCopy, 'pzCopy'));
  const bg = document.getElementById('kitBg'); if (bg) N.lastChild.appendChild(bg);   // (the kit's floor or arena)
  N.lastChild.appendChild(pzBtn('Chiudi', () => pzNotes(false), 'pzClose'));
  document.body.appendChild(N);
  const typed = (id, f) => document.getElementById(id).addEventListener('input', e => { pzMine(); f(e.target.value); PZ.edited = true; PZ.ui.dirty = true; clearTimeout(PZ.timer); PZ.timer = setTimeout(pzSave, 900); });
  typed('pzName', v => { PZ.name = v.slice(0, 60); });
  typed('pzNote', v => { PZ.note = v.slice(0, 2000); });
  typed('pzPnote', v => { if (PZ.poses[PZ.cur]) PZ.poses[PZ.cur].note = v.slice(0, 300); });
  const A = document.createElement('div'); A.id = 'pzA'; A.hidden = true; A.setAttribute('role', 'dialog'); A.setAttribute('aria-label', 'Animazioni');
  A.innerHTML = '<div id="pzAtop"><span class="pzMsg">Tocca un\'animazione: parte, poi «Successiva» va avanti.</span></div><div id="pzAl"></div>';
  A.firstChild.append(pzBtn('+ Nuova', pzNewAnim, 'pzNew'), pzBtn('Chiudi', () => pzAnims(false), 'pzAclose'));
  document.body.appendChild(A);
  addEventListener('resize', pzResize); pzResize();
  PZ.ui.dirty = true; PZ.ui.list = true;
}
// keys (taken before the viewer's own: its plays and speeds are not this page's)
function pzKeys() {
  addEventListener('keydown', e => {
    const t = e.target, tag = t && t.tagName, typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    e.stopImmediatePropagation();
    if (typing) { if (e.key === 'Escape') { t.blur(); pzNotes(false); } return; }
    if (e.key === 'Escape') { pzNotes(false); pzAnims(false); if (!PZ.watch) pzStop(); return; }
    const k = e.key, K = k.length === 1 ? k.toLowerCase() : k, onBtn = tag === 'BUTTON';
    if ((e.ctrlKey || e.metaKey) && K === 'z') { e.preventDefault(); if (!PZ.watch) pzUndo(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const act = PZ.watch ? {   // (the preview: nothing here changes an animation)
      ArrowLeft: () => pzNext(-1), ArrowRight: () => pzNext(1), ' ': () => pzPause(), p: () => pzPause(), l: () => pzAnims(), m: () => pzWatch(false), v: () => pzView(),
    }[K] : {
      ArrowUp: () => pzRowGo(-1), ArrowDown: () => pzRowGo(1), ArrowLeft: () => { PZ.kb = true; pzStepRow(-1); }, ArrowRight: () => { PZ.kb = true; pzStepRow(1); },
      '[': () => pzGo(PZ.cur - 1), ']': () => pzGo(PZ.cur + 1), n: () => pzAdd(), p: () => pzPlay(), g: () => pzGuard(), z: () => pzUndo(), v: () => pzView(), Delete: () => pzDel(),
      m: () => pzWatch(true),
    }[K];
    if (act && !(onBtn && (K === 'Enter' || K === ' '))) { e.preventDefault(); if (!e.repeat || /^Arrow/.test(K)) act(); }
  }, true);
}
// the controller: on the preview the d-pad (or the left stick) and the shoulders the next or previous animation, A the
// pause, X the list, Y the editor; in the editor the d-pad rows and choices, A a new pose, B undo, X the guard, Y
// plays, the shoulders the pose; Start goes from one to the other
function pzPad() {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [], now = performance.now();
  for (const g of pads) {
    if (!g) continue;
    const b = i => !!(g.buttons[i] && g.buttons[i].pressed), was = PZ.pad, hit = i => b(i) && !was[i];
    const ax = (i, s) => (g.axes[i] || 0) * s > .6;
    // the d-pad or the stick: once on the press, then again every 250 ms while held
    const dir = {up: b(12) || ax(1, -1), down: b(13) || ax(1, 1), left: b(14) || ax(0, -1), right: b(15) || ax(0, 1)};
    const watch = PZ.watch;
    for (const [d, on] of Object.entries(dir)) {
      const r = PZ.padRep;
      if (!on) { r[d] = 0; continue; }
      if (r[d] && now < r[d]) continue;
      r[d] = now + (r[d] ? 250 : 420);
      if (watch) { if (d === 'left' || d === 'right') pzNext(d === 'left' ? -1 : 1); continue; }
      PZ.kb = true;
      if (d === 'up') pzRowGo(-1); else if (d === 'down') pzRowGo(1); else pzStepRow(d === 'left' ? -1 : 1);
    }
    if (hit(9)) pzWatch(!watch);
    else if (watch) { if (hit(0)) pzPause(); if (hit(2)) pzAnims(); if (hit(3)) pzWatch(false); if (hit(4)) pzNext(-1); if (hit(5)) pzNext(1); }
    else { if (hit(0)) pzAdd(); if (hit(1)) pzUndo(); if (hit(2)) pzGuard(); if (hit(3)) pzPlay(); if (hit(4)) pzGo(PZ.cur - 1); if (hit(5)) pzGo(PZ.cur + 1); }
    for (let i = 0; i < 17; i++) was[i] = b(i);
    break;
  }
}
RN.hooks.boot.push(VW => {
  VW_PLAYS[0][1][0][1] = 1e9;   // (the kit's boot sets its guard's length on the first play: this page's one play lasts)
  CFG.looks.ren.clips = Object.assign({}, CFG.looks.ren.clips, {posa: {c: 'a191', at: 0}});   // the kit's held guard clip under it
  VW.PZ = PZ; VW.pz = {target: pzTarget, rows: PZ_ROWS, hands: PZ_HANDS, guard: PZ_GUARD, load: pzLoad, fill: pzFill, timeline: pzTimeline, step: PZ_STEP,
    rootOf: p => pzRootXf(PZ.D, p, mdData('ren')), leg: PZ_LEG};   // (tests)
  PZ.poses = [pzNew0()];
  pzUi(); pzKeys(); pzStore(); pzFxInit(VW);
});
// each drawn frame: the controller, the camera on the body, the panel when something changed
RN.hooks.draw.push((VW, dt, cam) => {
  if (RN.pad !== pzPad) RN.pad = pzPad;   // (the scaffold sets its own after the boot hooks)
  const j = PZ.D ? PZ.D.b.jump : 0, x = PZ.D ? PZ.D.b.tx * Math.cos(VW.yaw - F3_YAW) : 0;   // (a jump: the camera goes up with half of it; steps: it follows him)
  // the whole body's turn and flip (on top of the viewer's own placing of the model), the shadow under his hips
  const it = VW.it;
  if (PZ.D && it.pose) {
    it.root.rotation.set(0, it.root.rotation.y, 0);   // (the viewer sets the yaw alone each frame: last frame's flip goes)
    const xf = pzRootXf(PZ.D, it.pose, mdData(it.key)), q0 = it.root.quaternion.clone();
    if (xf.q.w < 1 - 1e-9 || xf.t.lengthSq() > 0) { it.root.quaternion.multiply(xf.q); it.root.position.add(xf.t.clone().multiplyScalar(it.scale).applyQuaternion(q0)); }
    it.root.updateMatrixWorld(true);
    const h = it.bones[mdData(it.key).index.Hips].getWorldPosition(new THREE.Vector3()); VW.shadow.position.set(h.x, .004, h.z);
  }
  let sh = {x: 0, y: 0};
  if (PZ.play && PZ_FXC.burst) {
    const L = pzTimeline(), tt = pzPlayT(RN_D.F ? RN_D.F.af : VW.F.af);
    PZ.loop = Math.floor(tt / L.len); sh = pzFx(VW, it, ((tt % L.len) + L.len) % L.len, cam);
  } else if (PZ_FXC.burst) { for (const b of PZ_FXC.burst) b.visible = false; PZ_FXC.glow.visible = PZ_FXC.ball.visible = PZ_FXC.ring.visible = PZ_FXC.trail.visible = false; PZ_FXC.flash.style.opacity = '0'; }
  cam.position.set(x + sh.x, .95 + .5 * j + .1 + sh.y, cam.position.z); cam.lookAt(x + sh.x, .95 + .5 * j + sh.y, 0); cam.updateMatrixWorld();
  if (PZ.play) { const a = PZ.play.at, key = a.a + ',' + a.b + ',' + a.back; if (key !== PZ.ui.at) { PZ.ui.at = key; PZ.ui.dirty = true; } }
  const side = Math.abs(VW.yaw - F3_YAW) < .02; if (side !== PZ.ui.side) { PZ.ui.side = side; PZ.ui.dirty = true; }   // (the view's button names it)
  if (PZ.ui.dirty) { PZ.ui.dirty = false; pzStrip(); pzRowsUi(); pzTitle(); pzNotesUi(); pzWatchUi(); if (!document.getElementById('pzA').hidden) pzListMark(); }
  if (PZ.ui.list) { PZ.ui.list = false; pzListUi(); pzWatchUi(); }
});
// one play: the pose being edited, for as long as the page is open
VW_PLAYS.length = 0;
VW_PLAYS.push(['Posa', [['posa', 1e9]]]);
VW_NAMES.posa = 'Posa';
