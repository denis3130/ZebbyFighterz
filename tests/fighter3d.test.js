// The placeholder fighter (Tappa 1). Since Tappa 2a it is only on side 1 (Kael): the side-0 checks moved there; the Meshy Ren is in model.test.js.
T.test('every limb is inside its hitbox on the active frames', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,1); f.x=0; f.face=1;
  for(const [id,m] of Object.entries(__VF.CFG.moves)){ f.air=id[0]==='j'; f.y=f.air?900:0; f.act=id; f.af=m.s+1+Math.floor(m.a/2); __VF.renderFrame(S,0);
    const p=__VF.limbWorld(1,m.limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' '+m.limb+' at '+[p.x,p.y]); } });
T.test('facing left mirrors the limbs', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,1); f.x=0; f.face=-1; f.act='p1'; f.af=5; __VF.renderFrame(S,0); T.ok(__VF.limbWorld(1,'handL').x<-.2); });
T.test('fighters have an outline and toon shading', () => { const it=__VF.F3D[1]; let toon=0, out=0; it.root.traverse(o=>{ if(o.material&&o.material.isMeshToonMaterial)toon++; if(o.material&&o.material.side===THREE.BackSide)out++; }); T.ok(toon>10&&out>10); });
T.test('ren and kael colours differ', () => { T.ok(__VF.F3D[0].mats.main.color.getHex()!==__VF.F3D[1].mats.main.color.getHex()); });
T.test('pose is a pure function', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const a=JSON.stringify(__VF.poseOf(F(S,1),S)), b=JSON.stringify(__VF.poseOf(F(S,1),S)); T.eq(a,b); });
T.test('feet touch the ground when idle', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0); T.near(__VF.limbWorld(1,'footL').y,.05,.06); });

// Beyond the brief: the same hit check for the fighter on the right (Kael, facing left), every move on every active frame.
T.test('facing left, every limb is inside its hitbox on every active frame', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,1); f.x=0; f.face=-1;
  for(const [id,m] of Object.entries(__VF.CFG.moves)) for(let af=m.s+1;af<=m.s+m.a;af++){ f.air=id[0]==='j'; f.y=f.air?900:0; f.act=id; f.af=af; __VF.renderFrame(S,0);
    const p=__VF.limbWorld(1,m.limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' af '+af+' '+m.limb+' at '+[p.x,p.y]); } });
T.test('every act has its own pose', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1), idle=JSON.stringify(__VF.poseOf(f,S));
  const acts=['walkF','walkB','crouch','jumpSquat','air','dashF','dashB','guard','guardC','block','hitStun','juggle','knock','getup','rollF','rollB','thr','thrWhiff','thrown','landing','ko','win','intro','spec'].concat(Object.keys(__VF.CFG.moves));
  for(const act of acts){ Object.assign(f,{act,af:3,x:400,air:act==='air'||act[0]==='j',vy:act==='air'?40:0,land:5,stun:8}); T.ok(JSON.stringify(__VF.poseOf(f,S))!==idle, act); } });
T.test('planted poses keep both feet on the floor', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1);
  for(const [act,af] of [['idle',1],['idle',37],['guard',8],['crouch',8],['guardC',8],['jumpSquat',3],['block',4],['landing',2]]){ Object.assign(f,{act,af,land:5}); S.frame=af*7; __VF.renderFrame(S,0);
    for(const l of ['footL','footR']) T.near(__VF.limbWorld(1,l).y,.05,.03, act+' '+l); } });
// A foot on the floor while the other one swings (transition frames excluded) must not move, walking either way.
T.test('the walk never slides: a planted foot stays put', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1), feet=()=>[__VF.limbWorld(1,'footL'),__VF.limbWorld(1,'footR')];
  for(const [act,face,dx] of [['walkF',1,__VF.CFG.walk.f],['walkB',-1,__VF.CFG.walk.b],['walkF',-1,-__VF.CFG.walk.f]]){ Object.assign(f,{act,af:10,x:0,face}); let n=0;
    for(let i=0;i<40;i++){ __VF.renderFrame(S,0); const a=feet(); f.x+=dx; f.af++; __VF.renderFrame(S,0); const b=feet();
      for(const k of [0,1]) if(a[k].y<.06&&b[k].y<.06&&a[1-k].y>.06&&b[1-k].y>.06){ n++; T.ok(a[k].distanceTo(b[k])<.01, act+' face '+face+' frame '+i+' slid '+a[k].distanceTo(b[k]).toFixed(3)); } }
    T.ok(n>20, act+' face '+face+' planted frames '+n); } });
T.test('fighters follow the sim and hide on the title', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); F(S,1).x=1500; F(S,1).y=300; __VF.renderFrame(S,0);
  const r=__VF.F3D[1].root; T.ok(r.visible); T.near(r.position.x,1.5,1e-9); T.near(r.position.y,.3,1e-9); __VF.renderFrame(null,0); T.ok(!r.visible&&!__VF.F3D[1].root.visible); });
// Fix round 1. headTop(i) = top of the head mesh of side i (its highest vertex, world), joint(i, name) = a joint's world position.
function headTop(i) { const h=__VF.F3D[i].joints.head.children.find(o=>o.name==='head.head'), a=h.geometry.attributes.position, v=new THREE.Vector3(); let y=-1e9;
  h.updateWorldMatrix(true,false); for(let k=0;k<a.count;k++) y=Math.max(y, v.fromBufferAttribute(a,k).applyMatrix4(h.matrixWorld).y); return y; }
function joint(i, name) { return __VF.F3D[i].joints[name].getWorldPosition(new THREE.Vector3()); }
T.test('a block with down held is drawn crouched, a standing block standing', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1), top=__VF.CFG.body.hCrouch/1000+.1;
  for(const af of [0,1,4,9]){ Object.assign(f,{act:'block',af,stun:Math.max(0,10-af),prev:B.D|B.L}); __VF.renderFrame(S,0);
    T.ok(joint(1,'head').y<1.1, 'crouching block af '+af+' head at '+joint(1,'head').y); T.ok(headTop(1)<=top, 'head top '+headTop(1));
    for(const l of ['footL','footR']) T.near(__VF.limbWorld(1,l).y,.05,.03, 'crouching block af '+af+' '+l); }
  Object.assign(f,{act:'block',af:2,stun:8,prev:B.L}); __VF.renderFrame(S,0); T.ok(joint(1,'head').y>1.4, 'standing block head at '+joint(1,'head').y); });
// Act changes ease in (render side): driven frame by frame, no joint jumps more than 0.15 m between two drawn frames.
T.test('act changes ease in: crouch, walk, guard and hitstun to idle', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1), it=__VF.F3D[1];
  const pts=()=>[it.joints.head, it.joints.chest, it.limbs.footL, it.limbs.footR, it.limbs.handL, it.limbs.handR].map(o=>o.getWorldPosition(new THREE.Vector3()));
  for(const [act,step] of [['crouch',()=>{}],['walkF',()=>{f.x+=__VF.CFG.walk.f;}],['guardC',()=>{}],['hitStun',()=>{f.stun=Math.max(0,f.stun-1);}]]){
    Object.assign(f,{act,af:1,x:-1200,stun:act==='hitStun'?14:0}); for(let i=0;i<20&&!(act==='hitStun'&&f.stun===0);i++){ __VF.renderFrame(S,0); f.af++; step(); }
    __VF.renderFrame(S,0); let a=pts(), worst=0; Object.assign(f,{act:'idle',af:1});
    for(let i=0;i<12;i++){ __VF.renderFrame(S,0); const b=pts(); for(let k=0;k<a.length;k++) worst=Math.max(worst,a[k].distanceTo(b[k])); a=b; f.af++; }
    T.ok(worst<.15, act+' to idle: '+worst.toFixed(3)+' m in one frame'); } });
T.test('the eased pose settles on the new act and strikes still snap', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1);
  Object.assign(f,{act:'crouch',af:9}); __VF.renderFrame(S,0); Object.assign(f,{act:'idle',af:__VF.CFG.anim.blend}); __VF.renderFrame(S,0); T.near(joint(1,'head').y, (()=>{ const g=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(g,0); return joint(1,'head').y; })(), 1e-6, 'idle reached');
  const S2=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), g=F(S2,1); g.x=0; g.face=1; Object.assign(g,{act:'crouch',af:9}); __VF.renderFrame(S2,0); Object.assign(g,{act:'p1',af:5}); __VF.renderFrame(S2,0);
  const p=__VF.limbWorld(1,'handL'), b=__VF.moveBox(g,'p1'); T.ok(p.x*1000>=b.x0&&p.x*1000<=b.x1&&p.y*1000>=b.y0&&p.y*1000<=b.y1, 'p1 from a crouch at '+[p.x,p.y]); });
// The crouching moves stay low: the head top within 0.1 m of the crouching hurtbox (1.05 m) on every frame.
T.test('crouching moves keep the head down by the crouching hurtbox', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,1), top=__VF.CFG.body.hCrouch/1000+.1;
  for(const id of ['cp','ck','chp','chk']){ const m=__VF.CFG.moves[id]; for(let af=1;af<=m.s+m.a+m.r;af++){ Object.assign(f,{act:id,af}); __VF.renderFrame(S,0); T.ok(headTop(1)<=top, id+' af '+af+' head top '+headTop(1).toFixed(3)); } } });
