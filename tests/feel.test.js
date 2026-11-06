T.test('hit makes spark, flash and squash', () => { hitOnce(); T.ok(__VF.FX.sparks.length>0); T.ok(__VF.FX.flash[1]>0); T.ok(__VF.FX.squash[1]>0); });
T.test('light hit does not shake, heavy does', () => { hitOnce('p1'); T.eq(__VF.FX.shake.amp,0); hitOnce('hp'); T.near(__VF.FX.shake.amp,.06,.001); });
T.test('effects do not change the fight', () => { const run=on=>{ __VF.CFG.fx.on=on; const S=__VF.simCreate({seed:3,mode:'versus',chars:['ren','kael']}); for(let i=0;i<1200;i++){ __VF.simStep(S, scripted(i), __VF.dummyInput(S,1)); __VF.fxEvents(S,i*16); } return __VF.simHash(S); };
  T.eq(run(true), run(false)); __VF.CFG.fx.on=true; });
T.test('effects are pooled: no new objects after warm-up', () => { for(let i=0;i<30;i++) hitOnce(); const n=__VF.scene.children.length; for(let i=0;i<30;i++) hitOnce(); T.eq(__VF.scene.children.length,n); });
T.test('ren projectile core is whiter than the water', () => { const c=__VF.FX.projColor('ren'); T.ok(c.r+c.g+c.b>2.7); });
// Beyond the brief: restore, camera, projectile, charge glow, KO flash, fx off.
T.test('flash and squash end and restore the fighter', () => { const t=hitOnce(), d=__VF.F3D[1]; T.ok(d.mats.main.emissive.getHex()===0xffffff,'not flashing'); T.ok(d.root.scale.y<1,'not squashed');
  __VF.fxUpdate(t+1000); T.eq(d.mats.main.emissive.getHex(),0); T.eq(d.root.scale.y,1); T.eq(d.root.scale.x,1); T.eq(__VF.FX.sparks.length,0); });
T.test('shake moves only the drawn camera, not cam or toScreen', () => { const t=hitOnce('hp'), S=__VF.G.S; __VF.renderFrame(S,t); const a=__VF.toScreen(__VF.cam.x,0,0), cx=__VF.camera.position.x, cy=__VF.camera.position.y;
  for(let i=0;i<5;i++){ __VF.renderFrame(S,t+i); const b=__VF.toScreen(__VF.cam.x,0,0); T.near(b.x,a.x,1e-6); T.near(__VF.camera.position.x,cx,.02); } T.ok(__VF.FX.shake.amp>0); });
T.test('effects off: no sparks, no flash', () => { __VF.CFG.fx.on=false; try { hitOnce(); T.eq(__VF.FX.sparks.length,0); T.eq(__VF.F3D[1].mats.main.emissive.getHex(),0); } finally { __VF.CFG.fx.on=true; } });
T.test('the projectile is drawn with its trail while it flies', () => { hitOnce(); __VF.startMatch('versus',{seed:1}); skipIntro(); const S=__VF.G.S; T.feed(S,1,B.S,0); T.feed(S,CFG0().spec.spawn+10,0,0);
  T.ok(S.proj.length>0); __VF.renderFrame(S,5000); let shown=0; __VF.scene.traverse(o=>{ if(o.isSprite&&o.visible&&o.material.blending===THREE.AdditiveBlending) shown++; }); T.ok(shown>=7,'sprites '+shown);
  const x=S.proj[0].x/1000, ok=[]; __VF.scene.traverse(o=>{ if(o.isSprite&&o.visible&&Math.abs(o.position.x-x)<.01&&Math.abs(o.position.y-S.proj[0].y/1000)<.01) ok.push(o); }); T.ok(ok.length>=2,'core+halo at the projectile'); });
T.test('charge glow shows from chargeShow and grows', () => { __VF.startMatch('versus',{seed:1}); skipIntro(); nearG(); const S=__VF.G.S, glow=()=>{ let n=0,sz=0; __VF.scene.traverse(o=>{ if(o.isSprite&&o.visible&&o.material.color.getHex()===0xffc874){ n++; sz=o.scale.x; } }); return [n,sz]; };
  T.feed(S,2,B.P,0); __VF.renderFrame(S,1000); T.eq(glow()[0],0); T.feed(S,2,B.P,0); __VF.renderFrame(S,1016); const a=glow(); T.eq(a[0],1); T.feed(S,5,B.P,0); __VF.renderFrame(S,1032); T.ok(glow()[1]>a[1]*.9); T.feed(S,30,0,0); __VF.renderFrame(S,1100); T.eq(glow()[0],0); });
T.test('KO gives a full-screen white flash for 120 ms and a big shake', () => { __VF.fxUpdate(__VF.FX.now+1000); __VF.startMatch('versus',{seed:1}); skipIntro(); nearG(); const S=__VF.G.S; __VF.fighterOf(S,1).hp=1; let t=50000;
  for(let i=0;i<60&&!S.ev.some(e=>e.t==='ko');i++){ __VF.simStep(S,i===0?B.P:0,0); __VF.fxEvents(S,t); t+=16; }
  T.ok(S.ev.some(e=>e.t==='ko'),'no ko'); t-=16; __VF.fxUpdate(t); const el=document.querySelector('#hud div'); T.ok(parseFloat(el.style.opacity)>.9); T.near(__VF.FX.shake.amp,.12,.001);
  __VF.fxUpdate(t+130); T.eq(parseFloat(el.style.opacity),0); });
function CFG0() { return __VF.CFG; }
