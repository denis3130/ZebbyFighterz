// The Meshy Ren (Tappa 2a): the packed model in ASSETS, the skinned toon fighter on side 0, its animations driven by the sim.
T.test('the Ren package is in ASSETS', () => { const m=__VF.ASSETS['ren/ren.json'];
  T.ok(m&&m.v===1); T.eq(m.bones.length,24); T.eq(Object.keys(m.clips).length,25); T.ok(m.mesh.verts>20000&&m.mesh.tris===29999);
  T.ok(typeof __VF.ASSETS['ren/ren.bin']==='string'); T.ok(__VF.ASSETS['ren/ren.jpg'].startsWith('data:image/jpeg'));
  T.near(m.height,1.8,.08); T.eq(m.bones[0].n,'Hips'); });
T.test('side 0 is the Meshy Ren, toon with a skinned outline', () => { const it=__VF.F3D[0]; T.eq(it.kind,'model');
  T.ok(it.mesh.isSkinnedMesh&&it.mesh.material.isMeshToonMaterial&&it.mesh.material.skinning&&it.mesh.material.map);
  T.ok(it.outline.isSkinnedMesh&&it.outline.material.side===THREE.BackSide&&it.outline.material.skinning); T.eq(__VF.F3D[1].kind,undefined); });
T.test('the model follows the sim and hides on the title', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); F(S,0).x=-900; F(S,0).y=200; __VF.renderFrame(S,0);
  const r=__VF.F3D[0].root; T.ok(r.visible); T.near(r.position.x,-.9,1e-9); T.near(r.position.y,.2,1e-9); __VF.renderFrame(null,0); T.ok(!r.visible); });
T.test('model draws before its texture is ready', () => { const it=__VF.F3D[0], img=it.mesh.material.map.image; const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0); T.ok(img!==undefined); });
T.test('missing model falls back to the placeholder', () => { const a=__VF.ASSETS, j=a['ren/ren.json']; delete a['ren/ren.json']; try { T.eq(__VF.modelBuild('ren'),null); T.eq(__VF.mdData('nobody'),null); } finally { a['ren/ren.json']=j; } });
T.test('idle feet on the floor, head at standing height', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0);
  for(const l of ['footL','footR']) T.near(__VF.limbWorld(0,l).y,.06,.05,l); const h=__VF.headTop(0); T.ok(h>1.4&&h<1.9,'head top '+h.toFixed(2)); });
T.test('a hit flashes the model', () => { const it=__VF.F3D[0]; T.ok(it.mats.main.emissive&&Object.keys(it.mats).length===1); });
T.test('every limb is inside its hitbox on every active frame, both facings', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const face of [1,-1]) for(const [id,m] of Object.entries(__VF.CFG.moves)) for(let af=m.s+1;af<=m.s+m.a;af++){ Object.assign(f,{x:0,face,act:id,af,air:id[0]==='j',y:id[0]==='j'?900:0}); __VF.renderFrame(S,0);
    const e=__VF.CFG.clips[id], limb=(e&&e.limb)||m.limb;   // the Meshy clip may strike with another limb than the placeholder
    const p=__VF.limbWorld(0,limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' face '+face+' af '+af+' '+limb+' at '+[p.x.toFixed(2),p.y.toFixed(2)]); } });
T.test('planted poses keep both feet on the floor', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const [act,af] of [['idle',1],['idle',37],['guard',8],['crouch',8],['guardC',8],['jumpSquat',3],['block',4],['landing',2]]){ Object.assign(f,{act,af,land:5,stun:4}); S.frame=af*7; __VF.renderFrame(S,0);
    for(const l of ['footL','footR']) T.near(__VF.limbWorld(0,l).y,.06,.05, act+' '+l); } });
T.test('the walk barely slides', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), feet=()=>[__VF.limbWorld(0,'footL'),__VF.limbWorld(0,'footR')];
  for(const [act,face,dx] of [['walkF',1,__VF.CFG.walk.f],['walkB',-1,__VF.CFG.walk.b],['walkF',-1,-__VF.CFG.walk.f]]){ Object.assign(f,{act,af:10,x:0,face}); let n=0;
    for(let i=0;i<60;i++){ __VF.renderFrame(S,0); const a=feet(); f.x+=dx; f.af++; __VF.renderFrame(S,0); const b=feet();
      // the support foot: on the floor and lower than the swinging one in both frames (Meshy's walk-back drags the swinging foot low)
      for(const k of [0,1]) if(a[k].y<.11&&b[k].y<.11&&a[k].y<a[1-k].y-.01&&b[k].y<b[1-k].y-.01){ n++; T.ok(a[k].distanceTo(b[k])<.02, act+' face '+face+' frame '+i+' slid '+a[k].distanceTo(b[k]).toFixed(3)); } }
    T.ok(n>20, act+' planted frames '+n); } });
T.test('act changes ease in', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), it=__VF.F3D[0];
  const pts=()=>[it.joints.head,it.joints.chest,it.limbs.footL,it.limbs.footR,it.limbs.handL,it.limbs.handR].map(o=>o.getWorldPosition(new THREE.Vector3()));
  for(const act of ['crouch','walkF','guardC','hitStun']){ Object.assign(f,{act,af:1,x:-1200,stun:act==='hitStun'?14:0}); for(let i=0;i<20;i++){ __VF.renderFrame(S,0); f.af++; if(act==='walkF') f.x+=__VF.CFG.walk.f; }
    __VF.renderFrame(S,0); let a=pts(), worst=0; Object.assign(f,{act:'idle',af:1});
    for(let i=0;i<12;i++){ __VF.renderFrame(S,0); const b=pts(); for(let k=0;k<a.length;k++) worst=Math.max(worst,a[k].distanceTo(b[k])); a=b; f.af++; }
    T.ok(worst<.15, act+' to idle: '+worst.toFixed(3)); } });
T.test('pose is a pure function of the state', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const act of ['idle','walkF','p2','hk','air','knock','getup']){ Object.assign(f,{act,af:5,x:300,vy:act==='air'?40:0,air:act==='air'}); const a=Array.from(__VF.mdPoseOf(f,S).q), b=Array.from(__VF.mdPoseOf(f,S).q); T.eq(JSON.stringify(a),JSON.stringify(b),act); } });
T.test('every act has its own pose', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), idle=JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q));
  const acts=['walkF','walkB','crouch','jumpSquat','air','dashF','dashB','guard','guardC','block','hitStun','juggle','knock','getup','rollF','rollB','thr','thrWhiff','thrown','landing','ko','win','spec'].concat(Object.keys(__VF.CFG.moves));
  for(const act of acts){ Object.assign(f,{act,af:3,x:400,air:act==='air'||act[0]==='j',vy:act==='air'?40:0,land:5,stun:8}); T.ok(JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q))!==idle, act); } });
T.test('unknown act draws the idle pose', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), idle=JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q));
  f.act='nonsense'; T.eq(JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q)),idle); });
T.test('crouched acts keep the head down', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), top=__VF.CFG.body.hCrouch/1000+.1;
  for(const [act,n] of [['crouch',20],['guardC',20],['cp',15],['ck',19]]) for(let af=1;af<=n;af++){ Object.assign(f,{act,af}); __VF.renderFrame(S,0); T.ok(__VF.headTop(0)<=top, act+' af '+af+' head '+__VF.headTop(0).toFixed(2)); }
  Object.assign(f,{act:'block',af:2,stun:8,prev:B.D|B.L}); __VF.renderFrame(S,0); T.ok(__VF.headTop(0)<=top,'crouching block'); });
T.test('facing left mirrors the limbs', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0); Object.assign(f,{x:0,face:-1,act:'p1',af:5}); __VF.renderFrame(S,0); T.ok(__VF.limbWorld(0,'handL').x<-.2); });
