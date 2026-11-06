// Menu, pause, end screen and the real-time loop (Task 11). Tests share page state and run in order, starting on the title.
T.test('title → training with keyboard', () => { key('Enter'); keyUp('Enter'); T.eq(__VF.G.state,'fight'); T.eq(__VF.G.mode,'training'); });
T.test('Esc pauses, Esc resumes', () => { key('Escape'); keyUp('Escape'); T.eq(__VF.G.state,'pause'); key('Escape'); keyUp('Escape'); T.eq(__VF.G.state,'fight'); });
T.test('pause stops the sim', () => { __VF.menu.pause(); const f=__VF.G.S.frame; __VF.tick(performance.now()+500); T.eq(__VF.G.S.frame,f); __VF.menu.resume(); });
T.test('opponent toggle in training', () => { __VF.menu.pause(); clickText('AVVERSARIO'); T.eq(__VF.G.S.dummy,'casuale'); __VF.menu.resume(); });
T.test('gamepad navigates the title and becomes G1', () => { __VF.menu.toTitle(); fakePads([{buttons:{13:1}}]); padTick(); fakePads([{buttons:{0:1}}]); padTick(); fakePads([]); padTick(); T.eq(__VF.G.mode,'versus'); T.eq(__VF.IN.assign[0].pad,0); });
T.test('match end screen and rematch', () => { endMatch(0); T.eq(__VF.G.state,'end'); T.eq(txt('endTitle'),'VINCE REN!'); later(__VF.CFG.menu.endGuardMs+50,()=>clickText('RIVINCITA')); T.eq(__VF.G.state,'fight'); });
T.test('mouse click on pause button', () => { $('tPause').click(); T.eq(__VF.G.state,'pause'); __VF.menu.resume(); });
T.test('hidden tab pauses and does not catch up', () => { __VF.tick(performance.now()); T.ok(__VF.G.last!==null);
  Object.defineProperty(document,'hidden',{value:true,configurable:true}); document.dispatchEvent(new Event('visibilitychange'));
  T.eq(__VF.G.state,'pause'); T.eq(__VF.G.last,null); const f0=__VF.G.S.frame; __VF.tick(performance.now()+5000); T.eq(__VF.G.S.frame,f0,'no steps while hidden');
  Object.defineProperty(document,'hidden',{value:false,configurable:true}); __VF.menu.resume(); T.eq(__VF.G.last,null); const f=__VF.G.S.frame; __VF.tick(performance.now()+5000); T.eq(__VF.G.S.frame,f); });
T.test('restart resets the match', () => { __VF.startMatch('versus',{seed:1}); __VF.frame(200); __VF.menu.pause(); clickText('RICOMINCIA'); T.eq(__VF.G.state,'fight'); T.eq(__VF.G.S.frame,0); });
T.test('pad disconnect pauses only an assigned pad; the player keeps the keyboard', () => {
  const V=__VF, ev=i=>{ const e=new Event('gamepaddisconnected'); if(i!==undefined) e.gamepad={index:i}; window.dispatchEvent(e); };
  V.startMatch('versus',{seed:1}); fakePads([{},{}]); V.inputAssign('versus',{pad:0}); V.menu.resume();
  T.eq(V.IN.assign[0].pad,0); T.eq(V.IN.assign[1].pad,1);
  ev(5); T.eq(V.G.state,'fight','unassigned index: no pause');
  ev(1); T.eq(V.G.state,'pause','G2 pad gone'); fakePads([{}]); V.menu.resume();
  T.eq(V.G.state,'fight'); T.ok((V.inputRead(1)&B.L)===0); key('ArrowLeft'); T.ok((V.inputRead(1)&B.L)!==0,'G2 plays on keyboard set 2'); keyUp('ArrowLeft');
  ev(0); T.eq(V.G.state,'pause','G1 pad gone'); fakePads([]); V.menu.resume();
  key('KeyA'); T.ok((V.inputRead(0)&B.L)!==0,'G1 plays on keyboard set 1'); keyUp('KeyA');
  V.startMatch('versus',{seed:1}); V.inputAssign('versus','kb'); V.menu.resume(); ev(0); T.eq(V.G.state,'fight','keyboard-only match: no pause');
  V.startMatch('versus',{seed:1}); fakePads([{}]); V.inputAssign('versus',{pad:0}); V.menu.resume(); window.dispatchEvent(new Event('gamepaddisconnected')); T.eq(V.G.state,'pause'); fakePads([]); });
T.test('loop: fixed steps from real time, at most loop.maxSteps per tick', () => {
  __VF.startMatch('versus',{seed:1}); const S=__VF.G.S, t=performance.now()+10000;
  __VF.tick(t); T.eq(S.frame,0,'first tick only records the time');
  __VF.tick(t+1000/60*3+1); T.eq(S.frame,3);
  const f=S.frame; __VF.tick(t+1000/60*3+1+2000); T.eq(S.frame-f,__VF.CFG.loop.maxSteps);
});
T.test('menu keys move the focus and wrap', () => {
  __VF.menu.toTitle(); key('ArrowDown'); keyUp('ArrowDown'); T.ok(document.querySelectorAll('#title .mb')[1].classList.contains('f'));
  key('KeyW'); keyUp('KeyW'); key('KeyW'); keyUp('KeyW'); T.ok(document.querySelectorAll('#title .mb')[1].classList.contains('f'),'wraps to the last');
  key('Space'); keyUp('Space'); T.eq(__VF.G.mode,'versus'); T.eq(__VF.IN.assign[0].pad,null);
});
T.test('screens: one at a time, hud hidden on the title', () => {
  __VF.menu.toTitle(); T.ok(vis('title')); T.ok(!vis('pause')&&!vis('end')&&!vis('tPause')); T.ok(!vis('hud'));
  __VF.startMatch('training',{seed:1}); T.ok(!vis('title')&&vis('tPause'));
});
T.test('confirm key held into the fight does not attack', () => {
  const V=__VF; V.menu.toTitle(); key('KeyJ'); T.eq(V.G.state,'fight'); T.eq(V.inputRead(0)&B.P,0,'J held: no punch');
  keyUp('KeyJ'); T.eq(V.inputRead(0)&B.P,0,'its release is no tap'); key('KeyJ'); T.ok((V.inputRead(0)&B.P)!==0,'pressed again: counts'); keyUp('KeyJ');
  V.menu.toTitle(); key('Numpad1'); key('Enter'); keyUp('Enter'); T.eq(V.inputRead(0)&B.P,0,'Numpad1 held at confirm'); keyUp('Numpad1'); V.inputRead(0);
  V.menu.pause(); key('KeyJ'); T.eq(V.G.state,'fight'); T.eq(V.inputRead(0)&B.P,0,'resume with J'); keyUp('KeyJ'); V.inputRead(0);
  key('Escape'); keyUp('Escape'); key('KeyJ'); T.eq(V.inputRead(0)&B.P,0,'J held on resume click'); keyUp('KeyJ'); });
T.test('pad A held into the fight does not kick', () => {
  const V=__VF; V.menu.toTitle(); fakePads([{buttons:{0:1}}]); padTick(); T.eq(V.G.state,'fight'); T.eq(V.inputRead(0)&B.K,0,'A held: no kick');
  fakePads([{}]); T.eq(V.inputRead(0)&B.K,0); fakePads([{buttons:{0:1}}]); T.ok((V.inputRead(0)&B.K)!==0,'pressed again: counts'); fakePads([]); });
T.test('end screen ignores confirm and back for a moment', () => {
  const V=__VF; V.startMatch('versus',{seed:1}); endMatch(1); T.eq(V.G.state,'end');
  clickText('RIVINCITA'); V.menuPress('kb'); V.menuBack(); key('Space'); keyUp('Space'); T.eq(V.G.state,'end','guarded');
  later(V.CFG.menu.endGuardMs+50,()=>V.menuBack()); T.eq(V.G.state,'title','back works after the guard'); });
