// Input layer: two keyboard sets, up to two gamepads and the on-screen touch controls, each reduced to one integer of
// BTN bits per player. Devices are OR-ed together; opposite directions (SOCD) are left to the sim.
const IN={override:[null,null],keys:new Set(),pads:[],touchBits:0,assign:null,mask:{keys:new Set(),pad:[]}};
const IN_KEYS=[   // keyboard set 0 = G1 (WASD), set 1 = G2 (arrows + numpad)
  {KeyW:BTN.U,KeyS:BTN.D,KeyA:BTN.L,KeyD:BTN.R,KeyJ:BTN.P,KeyK:BTN.K,KeyL:BTN.S,KeyU:BTN.DASH,KeyI:BTN.GUARD},
  {ArrowUp:BTN.U,ArrowDown:BTN.D,ArrowLeft:BTN.L,ArrowRight:BTN.R,Numpad1:BTN.P,Numpad2:BTN.K,Numpad3:BTN.S,Numpad4:BTN.DASH,Numpad5:BTN.GUARD}];
const IN_PAD_BTN=[[2,BTN.P],[0,BTN.K],[1,BTN.S],[5,BTN.DASH],[4,BTN.GUARD],[12,BTN.U],[13,BTN.D],[14,BTN.L],[15,BTN.R]];   // standard mapping
const IN_DEAD=.45, IN_STICK_R=56;
const IN_TOUCH_BTN={tP:BTN.P,tK:BTN.K,tS:BTN.S,tDash:BTN.DASH,tGuard:BTN.GUARD};
const inTouch={btn:new Map(),stick:null,stickBits:0};   // btn: pointerId -> button id; stick: {id, ox, oy}

function inputPoll(){
  const l=navigator.getGamepads?navigator.getGamepads():[];
  IN.pads=[];
  for(let i=0;l&&i<l.length;i++) IN.pads[i]=l[i]&&l[i].connected!==false?l[i]:null;
}
function inputPadBits(g){
  let b=0;
  for(const [i,bit] of IN_PAD_BTN) if(g.buttons[i]&&(g.buttons[i].pressed||g.buttons[i].value>.5)) b|=bit;
  const x=g.axes[0]||0, y=g.axes[1]||0;
  if(x<-IN_DEAD) b|=BTN.L; if(x>IN_DEAD) b|=BTN.R; if(y<-IN_DEAD) b|=BTN.U; if(y>IN_DEAD) b|=BTN.D;
  return b;
}
function inputRead(p){
  if(IN.override[p]!==null&&IN.override[p]!==undefined) return IN.override[p];
  const a=IN.assign[p]; let b=0;
  for(const c of [...IN.mask.keys]) if(!IN.keys.has(c)) IN.mask.keys.delete(c);   // released: no longer masked
  for(const set of a.kb) for(const c of IN.keys) if(!IN.mask.keys.has(c)) b|=IN_KEYS[set][c]||0;
  inputPoll();
  if(a.pad!==null&&IN.pads[a.pad]){
    let pb=inputPadBits(IN.pads[a.pad]); const m=IN.mask.pad[a.pad]||0;
    if(m){ IN.mask.pad[a.pad]=m&pb; pb&=~m; }
    b|=pb;
  }
  if(a.touch) b|=IN.touchBits;
  return b;
}
// mode 'training' | 'versus'; chooser 'kb' | 'touch' | {pad:i} = the device that confirmed "2 Giocatori" (becomes G1).
function inputAssign(mode,chooser){
  if(mode==='training'){
    IN.assign=[{kb:[0,1],pad:0,touch:true},{kb:[],pad:null,touch:false}]; return;
  }
  inputPoll();
  const own=chooser&&typeof chooser==='object'?chooser.pad:null;
  let free=null;
  for(let i=0;i<IN.pads.length&&free===null;i++) if(IN.pads[i]&&i!==own) free=i;
  IN.assign=[{kb:[0],pad:own,touch:true},{kb:[1],pad:free,touch:false}];
}
// A menu confirm that closes into a fight: the attack/dash/guard keys and pad buttons held right now read as released until
// they really are released (a held J or pad A would otherwise punch or kick on frame 1, and its release would count as a tap).
function inputMaskHeld(){
  const dirs=BTN.U|BTN.D|BTN.L|BTN.R;
  IN.mask.keys=new Set([...IN.keys].filter(c=>((IN_KEYS[0][c]||IN_KEYS[1][c]||0)&~dirs)!==0));
  inputPoll(); IN.mask.pad=[];
  IN.pads.forEach((g,i)=>{ if(g) IN.mask.pad[i]=inputPadBits(g)&~dirs; });
}
function inputReleaseAll(){
  IN.keys.clear(); inTouch.btn.clear(); inTouch.stick=null; inTouch.stickBits=0; inputTouchSync(); inputStickDraw(null,0,0);
}
function inputTouchSync(){
  let b=inTouch.stickBits; const held=new Set(inTouch.btn.values());
  for(const id in IN_TOUCH_BTN){
    if(held.has(id)) b|=IN_TOUCH_BTN[id];
    const e=document.getElementById(id); if(e) e.classList.toggle('down',held.has(id));
  }
  IN.touchBits=b;
}
// Draws the stick: o = {x,y} origin in the zone (null = idle spot), (dx,dy) = knob offset in px.
function inputStickDraw(o,dx,dy){
  const base=document.getElementById('stickBase'), knob=document.getElementById('stickKnob'), zone=document.getElementById('stickZone');
  if(!base) return;
  base.classList.toggle('idle',!o);
  if(o){ const r=zone.getBoundingClientRect(); base.style.left=(o.x-r.left-IN_STICK_R)+'px'; base.style.top=(o.y-r.top-IN_STICK_R)+'px'; }
  else { base.style.left=''; base.style.top=''; }
  knob.style.transform='translate('+dx+'px,'+dy+'px)';
}
function inputStickMove(e){
  const s=inTouch.stick; let dx=e.clientX-s.ox, dy=e.clientY-s.oy;
  const d=Math.hypot(dx,dy); if(d>IN_STICK_R){ dx*=IN_STICK_R/d; dy*=IN_STICK_R/d; }
  const nx=dx/IN_STICK_R, ny=dy/IN_STICK_R; let b=0;
  if(ny<-IN_DEAD) b|=BTN.U; if(ny>IN_DEAD) b|=BTN.D; if(nx<-IN_DEAD) b|=BTN.L; if(nx>IN_DEAD) b|=BTN.R;
  inTouch.stickBits=b; inputTouchSync(); inputStickDraw({x:s.ox,y:s.oy},dx,dy);
}
function inputCapture(el,id){ try{ el.setPointerCapture(id); }catch(_){} }
// The touch overlay is shown only on touch devices and only while touchShow(true) (a fight); hiding releases everything held.
let inTouchOn=false;
function touchShow(on){
  const coarse=(window.matchMedia&&matchMedia('(pointer:coarse)').matches)||navigator.maxTouchPoints>0;
  inTouchOn=!!on;
  const root=document.getElementById('touch'); if(root) root.classList.toggle('on',inTouchOn&&!!coarse);
  if(!inTouchOn) inputReleaseAll();
}
function inputInitTouch(){
  const root=document.getElementById('touch'); if(!root) return;
  const zone=document.getElementById('stickZone');
  zone.addEventListener('pointerdown',e=>{
    if(inTouch.stick) return;
    e.preventDefault(); inputCapture(zone,e.pointerId);
    inTouch.stick={id:e.pointerId,ox:e.clientX,oy:e.clientY}; inputStickMove(e);
  });
  zone.addEventListener('pointermove',e=>{ if(inTouch.stick&&inTouch.stick.id===e.pointerId){ e.preventDefault(); inputStickMove(e); } });
  const stickEnd=e=>{ if(inTouch.stick&&inTouch.stick.id===e.pointerId){ inTouch.stick=null; inTouch.stickBits=0; inputTouchSync(); inputStickDraw(null,0,0); } };
  for(const t of ['pointerup','pointercancel','lostpointercapture']) zone.addEventListener(t,stickEnd);
  for(const id in IN_TOUCH_BTN){
    const el=document.getElementById(id);
    el.addEventListener('pointerdown',e=>{ e.preventDefault(); inputCapture(el,e.pointerId); inTouch.btn.set(e.pointerId,id); inputTouchSync(); });
    const end=e=>{ if(inTouch.btn.get(e.pointerId)===id){ inTouch.btn.delete(e.pointerId); inputTouchSync(); } };
    for(const t of ['pointerup','pointercancel','lostpointercapture']) el.addEventListener(t,end);
    el.addEventListener('contextmenu',e=>e.preventDefault());
  }
}
function inputInit(){
  inputAssign('training');
  window.addEventListener('keydown',e=>{
    if(!IN_KEYS[0][e.code]&&!IN_KEYS[1][e.code]) return;
    e.preventDefault(); IN.keys.add(e.code);
  });
  window.addEventListener('keyup',e=>{
    if(!IN_KEYS[0][e.code]&&!IN_KEYS[1][e.code]) return;
    e.preventDefault(); IN.keys.delete(e.code);
  });
  window.addEventListener('blur',inputReleaseAll);
  inputInitTouch();
}
