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
};
