// Key poses of the placeholder fighters (data for e_fighter3d.js, which resolves, blends and solves them).
// A pose: {joint: [x, y, z] degrees (Euler XYZ in the parent joint's frame), pos: [x, y, z] pelvis offset (m)}, and
// optionally fL / fR: an ankle target (model space, m; 0.08 up = standing) that the leg reaches by IK. Signs:
// pelvis/spine/chest/neck/head x+ = bend forward, y+ = turn the right shoulder forward, z+ = lean right; shoulder x- =
// arm forward, shL z+ / shR z- = arm out; elbow x- = bend; hip x- = leg forward, knee x+ = bend; ankle x+ = toes down.
// Key poses (b = based on another key; a key that sets a leg's angles drops the inherited target of that leg).
const F3_KEY = {
  // Fighting stance, left side forward: lead fist high, rear fist at the chin, knees soft.
  stance: {pos: [0, -.07, 0], fL: [.11, .08, .21], fR: [-.13, .08, -.2], pelvis: [0, -4, 0], spine: [6, -2, 0], chest: [4, -4, 0],
    neck: [0, 6, 0], head: [-8, 10, 0], shL: [-55, -10, 15], elL: [-105, 0, 0], shR: [-30, 10, -20], elR: [-130, 0, 0]},
  // Walks sit a little lower than the stance, so every step stays within the legs' reach (the feet never slide).
  walkF: {b: 'stance', pos: [0, -.1, 0]},
  walkB: {b: 'stance', pos: [0, -.1, 0], pelvis: [-4, -4, 0], spine: [2, -2, 0], head: [-4, 10, 0], shL: [-62, -14, 14], elL: [-112, 0, 0]},
  // Guard: lower, forearms up in front of the face.
  guard: {b: 'stance', pos: [0, -.14, -.03], spine: [14, -4, 0], chest: [10, -6, 0], head: [-6, 8, 0],
    shL: [-88, -10, -4], elL: [-128, 0, 0], shR: [-80, 10, 6], elR: [-132, 0, 0]},
  // Block: the guard pushed back; blockHitC is the crouching block (down held).
  blockHit: {b: 'guard', pos: [0, -.13, -.09], pelvis: [-6, -8, 0], spine: [2, -4, 0], head: [-20, 8, 0]},
  blockHitC: {b: 'guardC', pos: [0, -.62, -.05], pelvis: [13, -8, 0], spine: [14, -4, 0], head: [-24, 8, 0]},
  // Crouch: low (the crouching hurtbox is 1.05 m), leaning in, the head up to watch the opponent.
  crouch: {pos: [0, -.6, .02], fL: [.13, .08, .34], fR: [-.15, .08, -.13], pelvis: [15, -8, 0], spine: [16, -4, 0], chest: [12, -8, 0],
    neck: [-10, 6, 0], head: [-26, 10, 0], shL: [-90, -10, 15], elL: [-100, 0, 0], shR: [-70, 10, -20], elR: [-125, 0, 0]},
  guardC: {b: 'crouch', head: [-16, 8, 0], shL: [-112, -10, -4], elL: [-128, 0, 0], shR: [-104, 10, 6], elR: [-132, 0, 0]},
  squat: {b: 'stance', pos: [0, -.26, .03], spine: [16, -4, 0], shL: [-40, -10, 22], shR: [-20, 10, -26]},
  // In the air the feet stay at the root (F.y) or above it and the body spans about 1.6 m (the airborne hurtbox is 1.5).
  airUp: {pos: [0, -.3, 0], pelvis: [-10, 0, 0], spine: [12, 0, 0], head: [-10, 0, 0], hipL: [-95, 0, 8], knL: [110, 0, 0],
    anL: [20, 0, 0], hipR: [-60, 0, -8], knR: [120, 0, 0], anR: [30, 0, 0], shL: [-80, 0, 30], elL: [-80, 0, 0], shR: [-50, 0, -30], elR: [-100, 0, 0]},
  airDown: {b: 'airUp', pos: [0, -.26, 0], fL: [.1, .1, .14], fR: [-.12, .1, -.1]},
  // Dashes skim off the floor: forward low with the arms trailing, back in a hop.
  dashF: {pos: [0, -.12, .05], fL: [.11, .26, .32], fR: [-.13, .2, -.5], pelvis: [15, -5, 0], spine: [20, 0, 0], chest: [10, -5, 0],
    head: [-25, 5, 0], shL: [40, 0, 20], elL: [-30, 0, 0], shR: [45, 0, -20], elR: [-30, 0, 0]},
  dashB: {b: 'stance', pos: [0, -.1, -.05], fL: [.11, .2, .18], fR: [-.13, .16, -.18], pelvis: [-8, -8, 0], spine: [-5, -4, 0]},
  // Hit: head and chest thrown back, arms flung.
  hurt: {pos: [0, -.1, -.08], fL: [.12, .08, .2], fR: [-.14, .08, -.22], pelvis: [-8, 5, 0], spine: [-12, 5, 0], chest: [-10, 5, 0],
    neck: [-10, 0, 0], head: [-25, -10, 0], shL: [-20, 0, 40], elL: [-40, 0, 0], shR: [-10, 0, -45], elR: [-35, 0, 0]},
  // Knocked into the air (tilting back as it falls), lying on the back, getting up (sitting, then on one knee),
  // rolling as a ball. The feet on the floor are IK targets, so the blends between these never sink into it.
  flyUp: {pos: [0, -.35, 0], pelvis: [-35, 0, 0], spine: [-15, 0, 0], chest: [-10, 0, 0], head: [-20, 0, 0], shL: [-150, 0, 40],
    elL: [-30, 0, 0], shR: [-140, 0, -40], elR: [-40, 0, 0], hipL: [-40, 0, 10], knL: [60, 0, 0], hipR: [-20, 0, -10], knR: [40, 0, 0]},
  flyDown: {b: 'flyUp', pos: [0, -.8, 0], pelvis: [-85, 0, 0], spine: [-5, 0, 0], chest: [0, 0, 0], head: [10, 0, 0],
    hipL: [-30, 0, 10], knL: [70, 0, 0], hipR: [-15, 0, -10], knR: [50, 0, 0]},
  down: {pos: [0, -.81, 0], fL: [.12, .09, .8], fR: [-.12, .08, .86], pelvis: [-90, 0, 0], spine: [-3, 0, 0], neck: [25, 0, 0],
    head: [10, 50, 0], shL: [-10, 0, 25], elL: [-20, 0, 0], shR: [-10, 0, -25], elR: [-20, 0, 0]},
  koDown: {b: 'down', fL: [.26, .08, .8], fR: [-.2, .08, .84], head: [10, 65, 0], shL: [-60, 0, 70], elL: [-10, 0, 0], shR: [-70, 0, -60], elR: [-15, 0, 0]},
  sit: {pos: [0, -.8, -.08], fL: [.12, .08, .45], fR: [-.13, .08, .36], pelvis: [-40, 0, 0], spine: [25, 0, 0], chest: [15, 0, 0], head: [-5, 0, 0],
    shL: [22, 0, 30], elL: [-20, 0, 0], shR: [22, 0, -30], elR: [-20, 0, 0]},
  kneel: {pos: [0, -.45, -.08], fL: [.12, .08, .3], fR: [-.13, .08, -.35], pelvis: [8, -5, 0], spine: [12, 0, 0], chest: [6, -5, 0], head: [-14, 8, 0],
    shL: [-40, 0, 10], elL: [-60, 0, 0], shR: [-30, 0, -15], elR: [-100, 0, 0]},
  tuck: {spine: [55, 0, 0], chest: [55, 0, 0], neck: [45, 0, 0], head: [30, 0, 0], shL: [-75, 0, 12], elL: [-95, 0, 0],
    shR: [-75, 0, -12], elR: [-95, 0, 0], hipL: [-120, 0, 10], knL: [150, 0, 0], anL: [30, 0, 0], hipR: [-120, 0, -10], knR: [150, 0, 0], anR: [30, 0, 0]},
  // Throw: reach with both hands, hold, pull back, shove; the one thrown doubles over.
  reach: {b: 'stance', pos: [0, -.1, .06], fL: [.11, .08, .3], spine: [12, 0, 0], chest: [6, 0, 0], head: [-14, 0, 0],
    shL: [-80, 0, 10], elL: [-15, 0, 0], shR: [-80, 0, -10], elR: [-15, 0, 0]},
  clinch: {b: 'reach', spine: [15, 0, 0], shL: [-75, 0, 18], elL: [-55, 0, 0], shR: [-75, 0, -18], elR: [-55, 0, 0]},
  tossW: {b: 'clinch', pos: [0, -.12, -.02], pelvis: [0, 20, 0], spine: [6, 15, 0], chest: [0, 20, 0], shL: [-50, 0, 10], elL: [-90, 0, 0], shR: [-30, 0, -25], elR: [-110, 0, 0]},
  toss: {b: 'reach', pos: [0, -.14, .1], fL: [.11, .08, .36], pelvis: [0, -10, 0], spine: [16, -5, 0], shL: [-85, 0, 0], elL: [-5, 0, 0], shR: [-85, 0, 0], elR: [-5, 0, 0]},
  held: {pos: [0, -.15, .05], fL: [.12, .08, .18], fR: [-.14, .08, -.18], pelvis: [15, 0, 0], spine: [20, 0, 0], chest: [15, 0, 0], head: [10, 0, 0],
    shL: [-30, 0, 10], elL: [-20, 0, 0], shR: [-30, 0, -10], elR: [-20, 0, 0]},
  // Special: both palms drawn back to the right hip, then thrust forward where the shot appears.
  specW: {b: 'stance', pos: [0, -.14, -.04], pelvis: [0, 20, 0], spine: [8, 15, 0], chest: [0, 20, 0], shL: [-20, 0, -25], elL: [-100, 0, 0],
    shR: [10, 0, -15], elR: [-90, 0, 0]},
  specH: {b: 'stance', pos: [0, -.14, .06], fL: [.11, .08, .3], fR: [-.13, .08, -.25], pelvis: [0, 0, 0], spine: [10, 0, 0], chest: [4, 0, 0],
    head: [-10, 0, 0], shL: [-85, 0, -8], elL: [-10, 0, 0], wrL: [60, 0, 0], shR: [-85, 0, 8], elR: [-10, 0, 0], wrR: [60, 0, 0]},
  win: {pos: [0, -.02, 0], fL: [.13, .08, .05], fR: [-.13, .08, -.05], chest: [-5, 0, 0], head: [-10, 0, 0], shL: [10, 0, 35], elL: [-80, 0, 0],
    shR: [-170, 0, -10], elR: [-20, 0, 0]},
  intro: {pos: [0, -.01, 0], fL: [.1, .08, .02], fR: [-.1, .08, -.02], head: [5, 0, 0], shL: [-45, 0, -20], elL: [-95, 0, 0], shR: [-45, 0, 20], elR: [-95, 0, 0]},
  // Moves: <id>W = wind-up (end of startup), <id>H = the strike (active frames). Limb in its box (see CFG.moves).
  // Air punches let the legs hang back, so the fist shows in front of the body.
  p1W: {b: 'stance', chest: [4, -4, 0], shL: [-50, -10, 18], elL: [-120, 0, 0]},
  p1H: {b: 'stance', spine: [8, -8, 0], chest: [6, -11, 0], head: [-8, 22, 0], shL: [-90, -8, 9], elL: [-12, 0, 0]},
  p2W: {b: 'stance', chest: [4, -14, 0], shR: [-40, 10, -18], elR: [-135, 0, 0]},
  p2H: {b: 'stance', pos: [0, -.09, .04], fL: [.11, .08, .24], pelvis: [0, 15, 0], spine: [8, 10, 0], chest: [6, 4, 0], head: [-8, -20, 0],
    shR: [-91, 8, -11], elR: [-8, 0, 0], shL: [-45, -10, 25], elL: [-125, 0, 0]},
  p3W: {b: 'stance', pos: [0, -.1, -.02], chest: [4, 10, 0], shL: [-40, -10, 30], elL: [-110, 0, 0]},
  p3H: {b: 'stance', pos: [0, -.12, .08], fL: [.11, .08, .32], pelvis: [0, -25, 0], spine: [10, -15, 0], chest: [6, 4, 0], head: [-8, 30, 0],
    shL: [-81, -10, 21], elL: [-22, 0, 0]},
  k1W: {b: 'stance', fL: [.1, .4, .2], fR: [-.1, .08, -.08], pelvis: [-5, -5, 0]},
  k1H: {b: 'stance', pos: [0, -.06, -.06], fR: [-.1, .08, -.08], pelvis: [-10, -5, 0], spine: [-4, 0, 0], hipL: [-88, 0, -2], knL: [17, 0, 0], anL: [35, 0, 0]},
  k2W: {b: 'stance', fL: [.1, .08, .05], fR: [-.3, .5, .05], pelvis: [0, 30, -5]},
  k2H: {b: 'stance', fL: [.1, .08, .05], pelvis: [0, 92, -18], spine: [0, -10, 10], chest: [0, -15, 0], head: [0, -25, -10],
    hipR: [-3, 0, -101], knR: [10, 0, 0], anR: [40, 0, 0]},
  hpW: {b: 'stance', pos: [0, -.12, -.04], pelvis: [0, -20, 0], chest: [4, -25, 0], shR: [-20, 10, -30], elR: [-130, 0, 0]},
  hpH: {b: 'stance', pos: [0, -.12, .12], fL: [.12, .08, .42], fR: [-.14, .08, -.28], pelvis: [0, 25, 0], spine: [12, 0, 0], chest: [8, 4, 0],
    head: [-12, -30, 0], shR: [-97, 0, -13], elR: [-9, 0, 0], shL: [-40, 0, 40], elL: [-110, 0, 0]},
  hkW: {b: 'stance', fL: [.1, .08, .05], fR: [-.25, .55, .12], pelvis: [-5, 25, -5]},
  hkH: {b: 'stance', fL: [.1, .08, .02], pelvis: [-10, 75, -31], spine: [-5, -10, 10], chest: [0, -15, 0], head: [0, -25, -10],
    hipR: [-50, 0, -71], knR: [5, 0, 0], anR: [40, 0, 0]},
  cpW: {b: 'crouch', chest: [10, -18, 0], shR: [-40, 10, -18], elR: [-130, 0, 0]},
  cpH: {b: 'crouch', spine: [13.5, 10, 0], chest: [8, -4.5, 0], head: [-26, -15, 0], shR: [-110.5, 5, 24.5], elR: [-45, 0, 0]},
  ckW: {b: 'crouch', fL: [.12, .14, .32]},
  ckH: {b: 'crouch', fL: [.08, .1, .66], fR: [-.15, .08, -.3], pelvis: [12, -25, 0], spine: [14, 4, 0], chest: [8, 8, 0], head: [-30, 15, 0]},
  chpW: {b: 'crouch', pos: [0, -.6, 0], chest: [10, -15, 0], shR: [-20, 10, -20], elR: [-120, 0, 0]},
  chpH: {b: 'crouch', pos: [0, -.58, .04], fL: [.12, .08, .3], fR: [-.15, .16, -.08], pelvis: [10, 5, 0], spine: [7, 15, 0], chest: [2, 25, 0],
    head: [-35, -20, 0], shR: [-172, 0, 8], elR: [-6.5, 0, 0], shL: [-40, -10, 25], elL: [-120, 0, 0]},
  chkW: {b: 'crouch', pos: [0, -.58, 0], fL: [.1, .08, .14], fR: [-.12, .42, .2], pelvis: [5, 10, 0]},
  chkH: {b: 'crouch', pos: [0, -.55, -.02], fL: [.1, .08, .14], fR: [-.08, 1, .5], pelvis: [-28, 15, 0], spine: [-8, 0, 0], chest: [-6, 0, 0],
    head: [12, -10, 0]},
  jpW: {b: 'airUp', chest: [10, -20, 0], shR: [-30, 10, -20], elR: [-130, 0, 0]},
  jpH: {b: 'airUp', pos: [0, -.22, 0], spine: [25, 20, 0], chest: [15, 15, 0], head: [-10, -20, 0], shR: [-55, 10, -15], elR: [-12, 0, 0], hipL: [-35, 0, 8], knL: [105, 0, 0], hipR: [-5, 0, -8], knR: [95, 0, 0]},
  jkW: {b: 'airUp', hipR: [-90, 0, -8], knR: [120, 0, 0]},
  jkH: {b: 'airUp', pelvis: [-15, 13, 0], hipR: [-36, 0, -1], knR: [9, 0, 0], anR: [35, 0, 0]},
  jhpW: {b: 'airUp', spine: [0, -10, 0], chest: [-10, -15, 0], shR: [-170, 0, -15], elR: [-60, 0, 0]},
  jhpH: {b: 'airUp', pos: [0, -.22, 0], spine: [40, 20, 0], chest: [20, 15, 0], head: [-20, -15, 0], shR: [-63, 0, -18], elR: [-18, 0, 0], hipL: [-35, 0, 8], knL: [105, 0, 0], hipR: [-5, 0, -8], knR: [95, 0, 0]},
  jhkW: {b: 'airUp', pelvis: [-5, 10, 0], hipR: [-100, 0, -8], knR: [130, 0, 0]},
  jhkH: {b: 'airUp', pelvis: [-7, 19, 0], hipR: [-38, 0, -6], knR: [0, 0, 0], anR: [30, 0, 0]},
};
// Cosmetic timings: walk stride (two steps, m), foot lift and fade-in frames; breathing rate (rad/frame) and depth.
const F3_WALK = {stride: .72, lift: .07, fade: 4}, F3_BREATH = {rate: .08, chest: 1.5, rise: .008};
// The posture each move starts from and returns to (the others: the stance, or the air pose for air moves).
const F3_FROM = {cp: 'crouch', ck: 'crouch', chp: 'crouch', chk: 'crouch'};
// The roll's ball: centre (y, z in the pelvis frame) and radius of the tuck pose, measured on the meshes: measure again
// if the tuck or the shapes change.
const F3_TUCK = {y: -.037, z: .238, r: .4};
