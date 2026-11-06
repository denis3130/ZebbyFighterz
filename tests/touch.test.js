T.test('touch controls are hidden before a match and after touchShow(false), which releases held buttons', () => {
  T.ok(!vis('tP'), 'hidden at start');
  __VF.touchShow(true); T.ok(vis('tP'), 'shown'); pd('tP',0,0,30); T.eq(__VF.inputRead(0)&B.P, B.P);
  __VF.touchShow(false); T.ok(!vis('tP') && !vis('stickZone'), 'hidden again'); T.eq(__VF.inputRead(0), 0); T.ok(!$('tP').classList.contains('down')); });
T.test('touch controls are shown', () => { __VF.startMatch('training',{seed:1,dummy:'fermo'}); for(const id of ['tP','tK','tS','tDash','tGuard','stickZone']) T.ok(vis(id), id); });
T.test('stick right and up', () => { pd('stickZone',100,250,1); pm('stickZone',160,200,1); T.eq(__VF.inputRead(0)&(B.R|B.U), B.R|B.U); pu('stickZone',160,200,1); T.eq(__VF.inputRead(0),0); });
T.test('stick thresholds and knob clamp', () => {
  pd('stickZone',100,250,1); pm('stickZone',100+20,250,1); T.eq(__VF.inputRead(0), 0, 'inside dead zone');
  pm('stickZone',100-30,250+30,1); T.eq(__VF.inputRead(0), B.L|B.D);
  const k=$('stickKnob').getBoundingClientRect(), b=$('stickBase').getBoundingClientRect();
  const d=Math.hypot(k.x+k.width/2-(b.x+b.width/2), k.y+k.height/2-(b.y+b.height/2)); T.ok(d<=56.5, 'knob inside radius, got '+d);
  pm('stickZone',700,250,1); T.ok(true); pu('stickZone',700,250,1);
  const k2=$('stickKnob').getBoundingClientRect(), b2=$('stickBase').getBoundingClientRect();
  T.near(k2.x+k2.width/2, b2.x+b2.width/2, 1, 'knob recentred'); });
T.test('button press shows .down and sets the bit', () => { pd('tP',0,0,2); T.ok($('tP').classList.contains('down')); T.eq(__VF.inputRead(0)&B.P, B.P); pu('tP',0,0,2); T.ok(!$('tP').classList.contains('down')); T.eq(__VF.inputRead(0),0); });
T.test('pointercancel releases a held button', () => { pd('tK',0,0,3); fire('tK','pointercancel',0,0,3); T.eq(__VF.inputRead(0)&B.K, 0); T.ok(!$('tK').classList.contains('down')); });
T.test('all five buttons map to their bits', () => {
  [['tP',B.P],['tK',B.K],['tS',B.S],['tDash',B.DASH],['tGuard',B.GUARD]].forEach(([id,bit],i)=>{ pd(id,0,0,10+i); T.eq(__VF.inputRead(0), bit, id); pu(id,0,0,10+i); }); });
T.test('window blur releases touch', () => { pd('tS',0,0,20); pd('stickZone',100,250,21); pm('stickZone',170,250,21); window.dispatchEvent(new Event('blur'));
  T.eq(__VF.inputRead(0), 0); T.ok(!$('tS').classList.contains('down')); });
T.test('P and K pressed together throw (touch)', () => { __VF.startMatch('training',{seed:1,dummy:'fermo'}); skipIntro(); nearG(); pd('tP',0,0,4); pd('tK',0,0,5); __VF.frame(1); pu('tP',0,0,4); pu('tK',0,0,5); __VF.frame(45); T.eq(F(__VF.G.S,1).hp,880); });
T.test('buttons fit inside a 390 px tall screen and do not overlap', () => {
  const ids=['tP','tK','tS','tDash','tGuard'], rs=ids.map(id=>$(id).getBoundingClientRect());
  ids.forEach((id,i)=>{ const r=rs[i]; T.ok(r.bottom<=390&&r.right<=844&&r.left>=0&&r.top>=0&&r.width>=48&&r.height>=44, id+' '+JSON.stringify(r)); });
  for(let i=0;i<5;i++)for(let j=i+1;j<5;j++){ const a=rs[i],b=rs[j]; T.ok(a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top, ids[i]+' overlaps '+ids[j]); } });
T.test('captions are Italian', () => { T.ok(/PUGNO/.test(txt('tP'))); T.ok(/CALCIO/.test(txt('tK'))); T.ok(/SPEC/.test(txt('tS'))); T.ok(/SCATTO/.test(txt('tDash'))); T.ok(/GUARDIA/.test(txt('tGuard'))); });
