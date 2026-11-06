T.test('keyboard G1 and G2 at the same time (versus)', () => { __VF.startMatch('versus',{seed:1}); __VF.inputAssign('versus','kb'); key('KeyD'); key('KeyJ'); key('ArrowLeft'); key('Numpad2');
  T.eq(__VF.inputRead(0), B.R|B.P); T.eq(__VF.inputRead(1), B.L|B.K); keyUpAll(); });
T.test('training: arrows also drive G1', () => { __VF.inputAssign('training','kb'); key('ArrowUp'); T.eq(__VF.inputRead(0)&B.U, B.U); keyUpAll(); });
T.test('gamepad mapping', () => { fakePads([{buttons:{2:1,5:1}, axes:[-.9,0]}]); __VF.inputAssign('training','kb'); T.eq(__VF.inputRead(0), B.P|B.DASH|B.L); fakePads([]); });
T.test('chooser pad becomes G1, keyboard set 2 is G2', () => { fakePads([{},{buttons:{0:1}}]); __VF.inputAssign('versus',{pad:1}); T.eq(__VF.inputRead(0)&B.K, B.K); T.eq(__VF.inputRead(1)&B.K, 0); fakePads([]); });
T.test('chooser keyboard: pad 0 goes to G2', () => { fakePads([{buttons:{1:1}}]); __VF.inputAssign('versus','kb'); T.eq(__VF.inputRead(1)&B.S, B.S); T.eq(__VF.inputRead(0)&B.S, 0); fakePads([]); });
T.test('keys are released on window blur', () => { __VF.inputAssign('training','kb'); key('KeyJ'); window.dispatchEvent(new Event('blur')); T.eq(__VF.inputRead(0)&B.P, 0); keyUpAll(); });
T.test('dpad, stick deadzone, guard and unplugged pads', () => {
  __VF.inputAssign('training','kb');
  fakePads([{buttons:{12:1,15:1,4:1}, axes:[.3,.3]}]); T.eq(__VF.inputRead(0), B.U|B.R|B.GUARD);
  fakePads([{axes:[0,.9]}]); T.eq(__VF.inputRead(0), B.D);
  fakePads([{axes:[.44,-.44]}]); T.eq(__VF.inputRead(0), 0);
  Object.defineProperty(navigator,'getGamepads',{value:()=>[null,null],configurable:true}); T.eq(__VF.inputRead(0), 0);
  fakePads([]); });
T.test('keyboard bits for all buttons of both sets', () => {
  __VF.inputAssign('versus','kb');
  for (const c of ['KeyW','KeyS','KeyA','KeyD','KeyJ','KeyK','KeyL','KeyU','KeyI']) key(c);
  T.eq(__VF.inputRead(0), 511); T.eq(__VF.inputRead(1), 0); keyUpAll();
  for (const c of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Numpad1','Numpad2','Numpad3','Numpad4','Numpad5']) key(c);
  T.eq(__VF.inputRead(1), 511); T.eq(__VF.inputRead(0), 0); keyUpAll(); });
T.test('override wins and game keys are default-prevented', () => {
  __VF.IN.override[0] = B.S; T.eq(__VF.inputRead(0), B.S); __VF.IN.override[0] = null;
  const e = new KeyboardEvent('keydown', {code:'Space', cancelable:true}); window.dispatchEvent(e); T.ok(!e.defaultPrevented, 'Space is not a game key');
  const a = new KeyboardEvent('keydown', {code:'ArrowUp', cancelable:true}); window.dispatchEvent(a); T.ok(a.defaultPrevented, 'arrows are prevented'); keyUp('ArrowUp'); });
T.test('touch UI is hidden on a mouse-only desktop', () => { T.ok(!vis('tP'), 'tP visible'); });

// Final fix wave: one guarded reader for the Gamepad API, and training reads the controller that confirmed.
T.test('a blocked Gamepad API (SecurityError) reads as no pads', () => {
  Object.defineProperty(navigator,'getGamepads',{value:()=>{ throw new DOMException('blocked by the permissions policy','SecurityError'); },configurable:true});
  try { __VF.inputAssign('training','kb'); __VF.inputAssign('versus',{pad:0}); key('KeyD'); T.eq(__VF.inputRead(0), B.R); keyUpAll(); }
  finally { fakePads([]); } });
T.test('training: the controller that confirmed drives G1, even at index 1', () => {
  padsAt([null,{buttons:{2:1}}]); __VF.inputAssign('training',{pad:1}); T.eq(__VF.IN.assign[0].pad,1); T.eq(__VF.inputRead(0)&B.P, B.P, 'pad 1 X');
  __VF.inputAssign('training','kb'); T.eq(__VF.IN.assign[0].pad,1,'keyboard confirm: the first connected pad'); T.eq(__VF.inputRead(0)&B.P, B.P);
  padsAt([]); __VF.inputAssign('training','kb'); T.eq(__VF.IN.assign[0].pad,0,'no pad yet: index 0, as before');
  fakePads([]); });
