T.test('every limb is inside its hitbox on the active frames', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,0); f.x=0; f.face=1;
  for(const [id,m] of Object.entries(__VF.CFG.moves)){ f.air=id[0]==='j'; f.y=f.air?900:0; f.act=id; f.af=m.s+1+Math.floor(m.a/2); __VF.renderFrame(S,0);
    const p=__VF.limbWorld(0,m.limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' '+m.limb+' at '+[p.x,p.y]); } });
T.test('facing left mirrors the limbs', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,0); f.x=0; f.face=-1; f.act='p1'; f.af=5; __VF.renderFrame(S,0); T.ok(__VF.limbWorld(0,'handL').x<-.2); });
T.test('fighters have an outline and toon shading', () => { const it=__VF.F3D[0]; let toon=0, out=0; it.root.traverse(o=>{ if(o.material&&o.material.isMeshToonMaterial)toon++; if(o.material&&o.material.side===THREE.BackSide)out++; }); T.ok(toon>10&&out>10); });
T.test('ren and kael colours differ', () => { T.ok(__VF.F3D[0].mats.main.color.getHex()!==__VF.F3D[1].mats.main.color.getHex()); });
T.test('pose is a pure function', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const a=JSON.stringify(__VF.poseOf(F(S,0),S)), b=JSON.stringify(__VF.poseOf(F(S,0),S)); T.eq(a,b); });
T.test('feet touch the ground when idle', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0); T.near(__VF.limbWorld(0,'footL').y,.05,.06); });

// Beyond the brief: the same hit check for the fighter on the right (Kael, facing left), every move on every active frame.
T.test('facing left, every limb is inside its hitbox on every active frame', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); const f=F(S,1); f.x=0; f.face=-1;
  for(const [id,m] of Object.entries(__VF.CFG.moves)) for(let af=m.s+1;af<=m.s+m.a;af++){ f.air=id[0]==='j'; f.y=f.air?900:0; f.act=id; f.af=af; __VF.renderFrame(S,0);
    const p=__VF.limbWorld(1,m.limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' af '+af+' '+m.limb+' at '+[p.x,p.y]); } });
T.test('every act has its own pose', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), idle=JSON.stringify(__VF.poseOf(f,S));
  const acts=['walkF','walkB','crouch','jumpSquat','air','dashF','dashB','guard','guardC','block','hitStun','juggle','knock','getup','rollF','rollB','thr','thrWhiff','thrown','landing','ko','win','intro','spec'].concat(Object.keys(__VF.CFG.moves));
  for(const act of acts){ Object.assign(f,{act,af:3,x:400,air:act==='air'||act[0]==='j',vy:act==='air'?40:0,land:5}); T.ok(JSON.stringify(__VF.poseOf(f,S))!==idle, act); } });
T.test('planted poses keep both feet on the floor', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const [act,af] of [['idle',1],['idle',37],['guard',8],['crouch',8],['guardC',8],['jumpSquat',3],['block',4],['landing',2]]){ Object.assign(f,{act,af,land:5}); S.frame=af*7; __VF.renderFrame(S,0);
    for(const l of ['footL','footR']) T.near(__VF.limbWorld(0,l).y,.05,.03, act+' '+l); } });
// A foot on the floor while the other one swings (transition frames excluded) must not move, walking either way.
T.test('the walk never slides: a planted foot stays put', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), feet=()=>[__VF.limbWorld(0,'footL'),__VF.limbWorld(0,'footR')];
  for(const [act,face,dx] of [['walkF',1,__VF.CFG.walk.f],['walkB',-1,__VF.CFG.walk.b],['walkF',-1,-__VF.CFG.walk.f]]){ Object.assign(f,{act,af:10,x:0,face}); let n=0;
    for(let i=0;i<40;i++){ __VF.renderFrame(S,0); const a=feet(); f.x+=dx; f.af++; __VF.renderFrame(S,0); const b=feet();
      for(const k of [0,1]) if(a[k].y<.06&&b[k].y<.06&&a[1-k].y>.06&&b[1-k].y>.06){ n++; T.ok(a[k].distanceTo(b[k])<.01, act+' face '+face+' frame '+i+' slid '+a[k].distanceTo(b[k]).toFixed(3)); } }
    T.ok(n>20, act+' face '+face+' planted frames '+n); } });
T.test('fighters follow the sim and hide on the title', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); F(S,1).x=1500; F(S,1).y=300; __VF.renderFrame(S,0);
  const r=__VF.F3D[1].root; T.ok(r.visible); T.near(r.position.x,1.5,1e-9); T.near(r.position.y,.3,1e-9); __VF.renderFrame(null,0); T.ok(!r.visible&&!__VF.F3D[0].root.visible); });
