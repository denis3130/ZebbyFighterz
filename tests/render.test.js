// The arena itself (no holes, depth, water, slabs, banner) is tested in arena.test.js.
T.test('the ground sits at 86% of the screen', () => { __VF.startMatch('versus',{seed:1}); for(let i=0;i<30;i++) __VF.renderFrame(__VF.G.S,i*16); const g=__VF.toScreen(__VF.cam.x,0,0).y; T.near(g/innerHeight, .86, .02); });
T.test('camera keeps both fighters in view at max separation', () => { const S=__VF.G.S; F(S,0).x=-2750; F(S,1).x=2750; for(let i=0;i<60;i++) __VF.renderFrame(S,i*16);
  for(const i of [0,1]){ const p=__VF.toScreen(F(S,i).x/1000,.9,0); T.ok(p.x>0&&p.x<innerWidth,'side '+i); } });
T.test('camera fits a super jump and the ground stays at 86%', () => { const S=__VF.G.S; F(S,0).y=2314; for(let i=0;i<60;i++) __VF.renderFrame(S,i*16);
  T.ok(__VF.toScreen(F(S,0).x/1000,(2314+1800)/1000,0).y>0,'head off screen'); T.near(__VF.toScreen(__VF.cam.x,0,0).y/innerHeight, .86, .02); });
T.test('the picture covers the whole screen', () => { for(const [u,v] of [[0,0],[1,0],[0,1],[1,1]]){ const p=pxAt(0,u,v); T.ok(p[3]===255 && sum(p)>30, u+','+v); } });
T.test('render does not change the sim', () => { const h=__VF.simHash(__VF.G.S); __VF.renderFrame(__VF.G.S,0); T.eq(__VF.simHash(__VF.G.S),h); });
T.test('resize keeps the ground at 86%', () => { setViewport(740,360); window.dispatchEvent(new Event('resize')); __VF.renderFrame(__VF.G.S,0); T.near(__VF.toScreen(__VF.cam.x,0,0).y/innerHeight, .86, .02); });
