// Menu, pause, end screen and the real-time loop (Task 11). Tests share page state and run in order, starting on the title.
T.test('title → training with keyboard', () => { key('Enter'); keyUp('Enter'); T.eq(__VF.G.state,'fight'); T.eq(__VF.G.mode,'training'); });
T.test('Esc pauses, Esc resumes', () => { key('Escape'); keyUp('Escape'); T.eq(__VF.G.state,'pause'); key('Escape'); keyUp('Escape'); T.eq(__VF.G.state,'fight'); });
T.test('pause stops the sim', () => { __VF.menu.pause(); const f=__VF.G.S.frame; __VF.tick(performance.now()+500); T.eq(__VF.G.S.frame,f); __VF.menu.resume(); });
T.test('opponent toggle in training', () => { __VF.menu.pause(); clickText('AVVERSARIO'); T.eq(__VF.G.S.dummy,'casuale'); __VF.menu.resume(); });
T.test('gamepad navigates the title and becomes G1', () => { __VF.menu.toTitle(); fakePads([{buttons:{13:1}}]); padTick(); fakePads([{buttons:{0:1}}]); padTick(); fakePads([]); padTick(); T.eq(__VF.G.mode,'versus'); T.eq(__VF.IN.assign[0].pad,0); });
T.test('match end screen and rematch', () => { endMatch(0); T.eq(__VF.G.state,'end'); T.eq(txt('endTitle'),'VINCE REN!'); clickText('RIVINCITA'); T.eq(__VF.G.state,'fight'); });
T.test('mouse click on pause button', () => { $('tPause').click(); T.eq(__VF.G.state,'pause'); __VF.menu.resume(); });
T.test('hidden tab pauses and does not catch up', () => { Object.defineProperty(document,'hidden',{value:true,configurable:true}); document.dispatchEvent(new Event('visibilitychange'));
  T.eq(__VF.G.state,'pause'); Object.defineProperty(document,'hidden',{value:false,configurable:true}); __VF.menu.resume(); const f=__VF.G.S.frame; __VF.tick(performance.now()+5000); T.ok(__VF.G.S.frame-f<=4); });
T.test('restart resets the match', () => { __VF.startMatch('versus',{seed:1}); __VF.frame(200); __VF.menu.pause(); clickText('RICOMINCIA'); T.eq(__VF.G.state,'fight'); T.eq(__VF.G.S.frame,0); });
T.test('pad disconnect pauses', () => { __VF.startMatch('versus',{seed:1}); fakePads([{}]); __VF.inputAssign('versus',{pad:0}); __VF.menu.resume(); window.dispatchEvent(new Event('gamepaddisconnected')); T.eq(__VF.G.state,'pause'); fakePads([]); });
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
