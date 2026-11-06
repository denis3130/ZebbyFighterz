// Every balance number lives here. Units: logic in mm, mm/frame and frames (60 = 1 s);
// in fx, cam and arena (graphics only) metres and milliseconds. Later tasks add their sections.
const CFG={
  ver:1,
  stage:{half:6000, startX:1200, maxSep:5500},
  body:{push:260, hurt:250, head:150, headH:300, h:1800, hCrouch:1050, hAir:1500, passY:1000, hp:1000, meterMax:3000},   // in the air above passY a fighter neither pushes nor is pushed
  walk:{f:75, b:58},
  jump:{squat:4, v:147, g:7, vxF:62, vxB:-52, superV:180, land:2, landAtk:5},
  dash:{f:{n:18, v0:170, v1:40}, b:{n:20, v0:150, v1:30}, tap:10},   // speed eases from v0 to v1 over n frames; tap = double-tap window
  input:{hold:12, chargeShow:4, both:3, buffer:8},
  phys:{pushFric:2},
  combo:{scaleFrom:3, scaleStep:10, minScale:30, decayFrom:6, decay:1, minStun:6, juggleMax:6, lift:60},
  stop:{light:6, mid:8, heavy:11, spec:8, thr:10, ko:40, blockLight:5, blockHeavy:8},
  meter:{hit:1, block:.5, taken:.5},
  knock:{ground:36, getup:16, roll:22, rollDist:1300},
  // Throw: s/a = startup/active frames, range = max centre distance, whiff = recovery of a miss, anim = frames of a
  // grab, hitF = the grab's frame of the damage, then the opponent is knocked down (vx away, vy up). No height: no block.
  thr:{range:900, s:4, a:2, whiff:24, anim:40, hitF:30, dmg:120, vx:60, vy:60, stop:'thr', knock:true},
  // Special (energy shot): spawn = frame the projectile appears, rec = frames after it; speed in mm/frame; box = half-size;
  // x, y = spawn point (forward of the fighter, from the ground); hs/bs/chip as a move's (chip = damage on a block).
  spec:{spawn:14, rec:30, speed:120, box:150, dmg:70, hs:20, bs:16, chip:8, x:500, y:1100, h:'mid', push:0, stop:'spec'},
  // Rounds: intro/end in frames, timerS in seconds, wins to take the match; ko = the fall of a fighter KO'd on the ground.
  round:{intro:100, timerS:99, end:150, wins:2, ko:{vx:50, vy:50}},
  training:{refill:60},   // frames out of a combo before health refills
  dummy:{min:30, max:60},   // the random dummy changes what it does every min..max frames
  // The plan's move table. s/a/r = startup/active/recovery frames (r 'land' = until landing, then jump.landAtk);
  // hs/bs = hitstun/blockstun; h = height; box = [x0,x1,y0,y1] mm, x forward from the centre, y from the feet;
  // push = pushback speed of the one hit; stop = hitstop class. Chains, once the move has touched: tapP/tapK = move
  // for a P/K tap, heavy = true (any heavy of the posture) or a list, spec = into the Special, jc = super jump (hit only).
  // limb = model part that must sit in the box (Task 8). Effects: knock (knocked down with vx, vy), launch (juggle with
  // vx, vy), airKnock (knocked down, airborne opponent only), spike (slammed down with vx, vy, airborne opponent only).
  moves:{
    p1:{s:4, a:2, r:7, dmg:30, hs:14, bs:10, h:'mid', box:[200,700,900,1550], push:24, stop:'light', tapP:'p2', tapK:'k1', heavy:true, spec:true, limb:'handL'},
    p2:{s:5, a:3, r:9, dmg:35, hs:15, bs:11, h:'mid', box:[200,760,900,1550], push:24, stop:'light', tapP:'p3', tapK:'k1', heavy:true, spec:true, limb:'handR'},
    p3:{s:7, a:3, r:14, dmg:50, hs:18, bs:12, h:'mid', box:[200,780,900,1500], push:35, stop:'mid', heavy:true, spec:true, limb:'handL'},
    k1:{s:6, a:3, r:10, dmg:40, hs:15, bs:11, h:'mid', box:[200,820,700,1100], push:24, stop:'light', tapP:'p2', tapK:'k2', heavy:true, spec:true, limb:'footL'},
    k2:{s:8, a:3, r:15, dmg:55, hs:18, bs:12, h:'mid', box:[250,900,1100,1500], push:30, stop:'mid', heavy:true, spec:true, limb:'footR'},
    hp:{s:12, a:4, r:18, dmg:90, hs:22, bs:15, h:'mid', box:[250,900,900,1550], push:40, stop:'heavy', heavy:['chk'], spec:true, limb:'handR'},
    hk:{s:14, a:4, r:20, dmg:100, bs:16, h:'mid', box:[300,1000,1000,1600], stop:'heavy', spec:true, limb:'footR', knock:true, vx:70, vy:70},
    cp:{s:5, a:2, r:8, dmg:25, hs:13, bs:10, h:'mid', box:[200,700,700,1000], push:22, stop:'light', tapP:'p2', tapK:'ck', heavy:true, spec:true, limb:'handR'},
    ck:{s:6, a:3, r:10, dmg:30, hs:14, bs:10, h:'low', box:[250,900,0,300], push:24, stop:'light', heavy:true, spec:true, limb:'footL'},
    chp:{s:9, a:4, r:20, dmg:80, hs:20, bs:14, h:'mid', box:[150,650,1300,2100], push:30, stop:'heavy', spec:true, limb:'handR', airKnock:{vx:30, vy:50}},
    chk:{s:11, a:4, r:22, dmg:70, bs:14, h:'mid', box:[200,700,800,1900], stop:'heavy', spec:true, jc:true, limb:'footR', launch:true, vx:10, vy:160},
    jp:{s:5, a:4, r:'land', dmg:40, hs:15, bs:10, h:'high', box:[150,600,300,900], push:20, stop:'light', tapK:'jk', heavy:true, limb:'handR'},
    jk:{s:6, a:5, r:'land', dmg:45, hs:16, bs:11, h:'high', box:[150,700,-300,500], push:20, stop:'light', heavy:true, limb:'footR'},
    jhp:{s:10, a:4, r:'land', dmg:75, hs:20, bs:13, h:'high', box:[150,700,0,800], push:20, stop:'heavy', limb:'handR', spike:true, vx:0, vy:-120},
    jhk:{s:11, a:5, r:'land', dmg:80, hs:21, bs:14, h:'high', box:[150,800,-400,400], push:20, stop:'heavy', limb:'footR'},
  },
  // Side camera (graphics only, metres): fov = vertical degrees; dist from dist0 out to distMax so that both fighters
  // fit with marginX each side and the highest head with marginTop above it; the ground always sits at footScreen of
  // the screen height; smooth = share of the gap closed per drawn frame; xMax = limit of the camera's x.
  cam:{fov:30, dist0:6.5, distMax:9.6, footScreen:.86, marginX:1.0, marginTop:.35, smooth:.15, xMax:3.0},
  // Painted backdrop: footRow = image row (share of its height) where the feet stand; cover = times the smallest scale
  // that fills the screen; parX = image widths of shift per metre of camera x; zoomPar = exponent of the zoom with
  // the camera distance; contrast/lift = colour grade; flow/streak/wobble = the waterfall's flow speed, streak
  // strength and shimmer; leaves = number of drifting leaves. footRow and cover keep the waterfall's crest and the
  // temple on top (image rows 213-255) in view, with some sky, on 20:9 phones; footRow stays on the painted floor.
  arena:{footRow:.83, cover:1.1, parX:.012, zoomPar:.3, contrast:.9, lift:.03, flow:.35, streak:.22, wobble:.002, leaves:10},
  // Fighter animation (graphics only): blend = frames over which the pose eases into a new free or movement action.
  anim:{blend:5},
};
