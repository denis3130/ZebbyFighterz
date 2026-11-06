// Attacks: tap and hold, hits, chains, damage scaling, hitstop, launcher, knockdown. B, N, F, near, comboPPPH come from tests/lib.js.
T.test('tap P releases a light punch', () => { const S=N(); T.feed(S,3,B.P,0); T.eq(F(S,0).act,'idle'); T.feed(S,1,0,0); T.eq(F(S,0).act,'p1'); });
T.test('hold P 12 frames fires the heavy punch at the 12th', () => { const S=N(); T.feed(S,11,B.P,0); T.ok(F(S,0).act!=='hp'); T.feed(S,1,B.P,0); T.eq(F(S,0).act,'hp'); T.feed(S,5,0,0); T.eq(F(S,0).act,'hp','releasing after the heavy does nothing'); });
T.test('charge event from the 4th held frame', () => { const S=N(); T.feed(S,3,B.P,0); T.ok(!S.ev.some(e=>e.t==='charge')); T.feed(S,1,B.P,0); T.ok(S.ev.some(e=>e.t==='charge')); });
T.test('crouch versions and air versions', () => { const S=N(); T.feed(S,2,B.D|B.K,0); T.feed(S,1,B.D,0); T.eq(F(S,0).act,'ck'); const A=N(); T.feed(A,1,B.U,0); T.feed(A,8,0,0); T.feed(A,1,B.P,0); T.feed(A,1,0,0); T.eq(F(A,0).act,'jp'); });
T.test('p1 hits: damage, hitstun, hitstop', () => { const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,1,0,0); T.feed(S,4,0,0); const h=S.ev.find(e=>e.t==='hit'); T.ok(h,'no hit on frame 5'); T.eq(F(S,1).hp,970); T.eq(S.stop,6); T.eq(F(S,1).act,'hitStun'); });
T.test('P,P,P chain is p1 p2 p3', () => { const S=N(); near(S); const seq=[]; for(let i=0;i<60;i++){ T.feed(S,1,(i%6===0)?B.P:0,0); const a=F(S,0).act; if(seq[seq.length-1]!==a&&/^p\d$/.test(a))seq.push(a);} T.eq(seq.slice(0,3).join(),'p1,p2,p3'); });
T.test('chain only on contact', () => { const S=N(); let saw=false; for(let i=0;i<40;i++){ T.feed(S,1,(i%3===0)?B.P:0,0); if(F(S,0).act==='p2')saw=true; } T.ok(!saw, 'whiffed p1 must not chain'); });
// Fixed from the plan: the combo starts at point blank (520 mm, pushboxes touching). From near()'s 700 mm the
// pushback of p1+p2+p3 carries the defender out of hp's reach (body edge 610 mm, hp reaches 550) for any hold timing.
T.test('damage scaling from the 3rd hit, floor 30%', () => { const S=N(); near(S); F(S,1).x=170; comboPPPH(S); T.eq(1000-F(S,1).hp, 30+35+45+72); T.eq(__VF.scaleFor(12),30); });
T.test('hitstun decays from the 6th hit', () => { T.eq(__VF.hitstunFor(14,6),13); T.eq(__VF.hitstunFor(14,5),14); T.eq(__VF.hitstunFor(14,40),6); });
T.test('no infinite: mashing P and K in the corner ends before 20 hits', () => { const S=N(); F(S,1).x=5700; F(S,0).x=5000; let max=0; for(let i=0;i<600;i++){ T.feed(S,1,[B.P,0,B.K,0,B.D|B.P,0][i%6],0); max=Math.max(max,F(S,1).combo);} T.ok(max<20,'combo '+max); });
T.test('launcher then super jump chase and air hit', () => { const S=N(); near(S); T.feed(S,12,B.D|B.K,0); let n=0; while(!S.ev.some(e=>e.t==='hit')&&n<20){T.feed(S,1,B.D,0);n++;}
  T.eq(F(S,1).act,'juggle'); T.feed(S,1,B.U|B.R,0); T.feed(S,16,B.R,0); T.ok(F(S,0).sj,'super jump (buffered through the hitstop)');
  let pressed=false; for(let i=0;i<60&&F(S,1).combo<2;i++){ const go=!pressed&&Math.abs(F(S,0).y-F(S,1).y)<300; T.feed(S,1,go?B.P:0,0); if(go){pressed=true; T.feed(S,1,0,0);} } T.ok(F(S,1).combo>=2,'air hit'); });
T.test('juggle limit makes the opponent invulnerable until landing', () => { const S=N(); const f=F(S,1); f.act='juggle'; f.air=true; f.y=800; f.juggle=6; T.eq(__VF.canBeHit(f),false); });
T.test('hk knocks down, then getup is invulnerable', () => { const S=N(); near(S); T.feed(S,14,B.K,0); T.feed(S,30,0,0); T.eq(F(S,1).act,'knock'); T.ok(F(S,1).inv>0); });
// Fixed from the plan: back is held only once hk has knocked the defender down (30 frames, as in the test above).
// Held from frame 15 it walks the defender back out of hk's reach before hk's first active frame (and in Task 4 it blocks).
T.test('holding back on the ground rolls', () => { const S=N(); near(S); T.feed(S,14,B.K,0); T.feed(S,30,0,0); let saw=false; for(let i=0;i<150&&!saw;i++){ T.feed(S,1,0,B.R); saw=F(S,1).act==='rollB'; } T.ok(saw); });
T.test('trade: both hit on the same frame', () => { const S=N(); near(S); T.feed(S,1,B.P,B.P); T.feed(S,5,0,0); T.ok(F(S,0).hp<1000&&F(S,1).hp<1000); });
T.test('meter: hit gives attacker dmg, defender half', () => { const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,6,0,0); T.eq(F(S,0).meter,30); T.eq(F(S,1).meter,15); });

// Behaviour of this task that the tests above do not pin down.
T.test('buffer: a command waits input.buffer frames for the fighter to be free', () => {
  // p1 starts on frame 2 and lasts 4+2+7 = 13 frames, so frame 15 is the first free one.
  const taps=(S,gap)=>{ T.feed(S,1,B.P,0); T.feed(S,1,0,0); T.feed(S,gap,0,0); T.feed(S,1,B.P,0); T.feed(S,1,0,0); };
  const ok=N(); taps(ok,3); T.feed(ok,7,0,0); T.eq(F(ok,0).af,13); T.feed(ok,1,0,0); T.eq(F(ok,0).act,'p1','released on frame 7, 8 frames early'); T.eq(F(ok,0).af,1);
  const late=N(); taps(late,2); T.feed(late,8,0,0); T.eq(F(late,0).af,13); T.feed(late,1,0,0); T.eq(F(late,0).act,'idle','released on frame 6, 9 frames early'); });
T.test('a held U does not jump-cancel the launcher: the super jump needs a U press', () => { const S=N(); near(S); T.feed(S,12,B.D|B.K,0); T.feed(S,30,B.U,0);
  T.eq(F(S,0).act,'chk'); T.ok(!F(S,0).sj); });
T.test('an air attack lands into jump.landAtk frames of landing', () => { const S=N(); T.feed(S,1,B.U,0); T.feed(S,4,0,0); T.feed(S,1,B.P,0); T.feed(S,1,0,0); T.eq(F(S,0).act,'jp');
  let n=0; while(F(S,0).act==='jp'&&n<60){ T.feed(S,1,0,0); n++; } T.eq(F(S,0).act,'landing'); T.eq(F(S,0).land,5); T.feed(S,4,0,0); T.eq(F(S,0).act,'landing'); T.feed(S,1,0,0); T.eq(F(S,0).act,'idle'); });
T.test('hitstun lasts hs frames after the hitstop, then the combo resets', () => { const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,5,0,0); const d=F(S,1); T.eq(d.combo,1); T.eq(d.comboDmg,30); T.eq(d.stun,14);
  T.feed(S,6+14,0,0); T.eq(d.act,'hitStun'); T.eq(d.combo,1); T.feed(S,1,0,0); T.eq(d.act,'idle'); T.eq(d.combo,0); T.eq(d.comboDmg,0); });
T.test('hit event: attacker side, move, scaled damage and the centre of the overlap', () => { const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,5,0,0); const h=S.ev.find(e=>e.t==='hit');
  T.eq(JSON.stringify([h.side,h.move,h.dmg,h.heavy,h.x,h.y]),'[0,"p1",30,false,225,1200]'); });
T.test('pushback slides the defender away, slowing by phys.pushFric; at the wall the attacker slides back', () => {
  const S=N(); near(S); T.feed(S,1,B.P,0); T.feed(S,5,0,0); T.eq(F(S,1).vx,24); T.feed(S,30,0,0); T.eq(F(S,1).x,350+132); T.eq(F(S,0).x,-350);
  const W=N(); F(W,1).x=5740; F(W,0).x=5040; T.feed(W,1,B.P,0); T.feed(W,5,0,0); T.eq(F(W,0).vx,-24); T.feed(W,30,0,0); T.eq(F(W,1).x,5740); T.eq(F(W,0).x,5040-132); });
T.test('a juggled fighter lands in knock, gets up invulnerable after knock.ground frames, then can be hit', () => {
  const S=N(); near(S); T.feed(S,12,B.D|B.K,0); T.feed(S,11,0,0); const d=F(S,1); T.eq(d.act,'juggle'); T.eq(JSON.stringify([d.vx,d.vy,d.juggle]),'[10,160,1]','launch: vx 10, vy 160');
  let n=0; while(d.air&&n<120){ T.feed(S,1,0,0); n++; } T.eq(d.act,'knock'); T.eq(d.af,1); T.ok(S.ev.some(e=>e.t==='knock'&&e.side===1),'knock event'); T.ok(!__VF.canBeHit(d)); T.eq(d.combo,1);
  T.feed(S,35,0,0); T.eq(d.act,'knock'); T.feed(S,1,0,0); T.eq(d.act,'getup'); T.ok(d.inv>0); T.eq(d.combo,0);
  T.feed(S,15,0,0); T.eq(d.act,'getup'); T.feed(S,1,0,0); T.eq(d.act,'idle'); T.eq(d.inv,0); T.ok(__VF.canBeHit(d)); });
T.test('a roll lasts knock.roll frames, covers rollDist mm and is invulnerable', () => { const S=N(); near(S); T.feed(S,14,B.K,0); T.feed(S,30,0,0); const d=F(S,1); let x=0, n=0;
  while(d.act!=='rollB'&&n<150){ x=d.x; T.feed(S,1,0,B.R); n++; } T.eq(d.af,1); T.feed(S,21,0,0); T.eq(d.act,'rollB'); T.ok(d.inv>0); T.eq(d.x-x,1300); T.feed(S,1,0,0); T.eq(d.act,'idle'); });
T.test('events: heavyFire when a heavy starts, whiff when the active frames end without contact', () => { const S=N(); T.feed(S,11,B.P,0); T.ok(!S.ev.some(e=>e.t==='heavyFire'));
  T.feed(S,1,B.P,0); const h=S.ev.find(e=>e.t==='heavyFire'); T.ok(h&&h.move==='hp'&&h.heavy&&h.side===0,'heavyFire '+JSON.stringify(h));
  T.feed(S,15,0,0); T.ok(!S.ev.some(e=>e.t==='whiff')); T.feed(S,1,0,0); const w=S.ev.find(e=>e.t==='whiff'); T.ok(w&&w.move==='hp','whiff on the first recovery frame'); });
T.test('a heavy cancels only into the heavies its move lists (hp: chk)', () => { const run=b=>{ const S=N(); near(S); T.feed(S,12,B.P,0); T.feed(S,12,0,0); T.ok(S.ev.some(e=>e.t==='hit'),'hp hits');
  T.feed(S,12,b,0); return F(S,0).act; }; T.eq(run(B.K),'hp'); T.eq(run(B.D|B.K),'chk'); });
T.test('on an airborne opponent chp knocks down and jhp spikes; on the ground they are plain hits', () => { const up=S=>Object.assign(F(S,1),{act:'air',air:true,y:600,vy:0});
  const a=N(); near(a); up(a); Object.assign(F(a,0),{act:'chp',af:9}); T.feed(a,1,0,0); T.eq(JSON.stringify([F(a,1).act,F(a,1).vx,F(a,1).vy]),'["knock",30,50]');
  const b=N(); near(b); up(b); Object.assign(F(b,0),{act:'jhp',af:10,air:true,y:1000,vy:0}); T.feed(b,1,0,0); T.eq(JSON.stringify([F(b,1).act,F(b,1).vx,F(b,1).vy]),'["knock",0,-120]');
  const c=N(); near(c); Object.assign(F(c,0),{act:'chp',af:9}); T.feed(c,1,0,0); T.eq(F(c,1).act,'hitStun'); });
T.test('moveBox: absolute, mirrored when facing left, only on the active frames', () => { const S=N(), f=F(S,0); Object.assign(f,{x:100,act:'p1',af:4}); T.eq(__VF.moveBox(f,'p1'),null); f.af=5;
  T.eq(JSON.stringify(__VF.moveBox(f,'p1')),'{"x0":300,"x1":800,"y0":900,"y1":1550}'); f.face=-1; T.eq(JSON.stringify(__VF.moveBox(f,'p1')),'{"x0":-600,"x1":-100,"y0":900,"y1":1550}');
  f.af=7; T.eq(__VF.moveBox(f,'p1'),null); Object.assign(f,{act:'jk',air:true,y:900,af:7,face:1}); T.eq(JSON.stringify(__VF.moveBox(f,'jk')),'{"x0":250,"x1":800,"y0":600,"y1":1400}'); });
T.test('hurtBoxes: body and head, standing, crouching and in the air', () => { const S=N(), f=F(S,0); f.x=0;
  T.eq(JSON.stringify(__VF.hurtBoxes(f)),'[{"x0":-250,"x1":250,"y0":0,"y1":1500},{"x0":-150,"x1":150,"y0":1500,"y1":1800}]');
  f.act='crouch'; T.eq(__VF.hurtBoxes(f)[0].y1,750); T.eq(__VF.hurtBoxes(f)[1].y1,1050); Object.assign(f,{act:'air',air:true,y:400}); T.eq(JSON.stringify(__VF.hurtBoxes(f).map(b=>[b.y0,b.y1])),'[[400,1600],[1600,1900]]'); });
T.test('a heavy fires once per press, and its release is never a tap', () => { const S=N(); T.feed(S,60,B.P,0); T.eq(F(S,0).act,'idle','one hp, then idle while P stays held');
  const R=N(); T.feed(R,1,B.P,0); T.feed(R,1,0,0); T.feed(R,12,B.P,0); T.eq(F(R,0).act,'p1'); T.feed(R,1,0,0); T.eq(F(R,0).act,'hp','the heavy buffered in the recovery, not replaced by its release'); });
T.test('walks and dashes stop dead: only pushback slides', () => { const S=N(); T.feed(S,10,B.R,0); const x=F(S,0).x; T.feed(S,5,0,0); T.eq(F(S,0).x,x);
  T.feed(S,1,B.DASH,0); T.feed(S,17,0,0); T.eq(F(S,0).act,'dashF'); const d=F(S,0).x; T.feed(S,5,0,0); T.eq(F(S,0).x,d); T.eq(F(S,0).vx,0); });
T.test('a 6th hit lands with its scaled damage and decayed hitstun', () => { const S=N(); near(S); F(S,1).combo=5; T.feed(S,1,B.P,0); T.feed(S,5,0,0);
  T.eq(F(S,1).combo,6); T.eq(1000-F(S,1).hp,Math.floor(30*__VF.scaleFor(6)/100)); T.eq(F(S,1).stun,__VF.hitstunFor(14,6)); T.eq(F(S,1).stun,13); });
T.test('a hit in the air juggles: rising at least at combo.lift, a faster riser keeps its speed', () => { const run=vy=>{ const S=N(); near(S); Object.assign(F(S,1),{act:'air',air:true,y:600,vy});
  Object.assign(F(S,0),{act:'p1',af:4}); T.feed(S,1,0,0); const d=F(S,1); return JSON.stringify([d.act,d.vx,d.vy,d.juggle]); };
  T.eq(run(0),'["juggle",24,60,1]'); T.eq(run(100),'["juggle",24,93,1]'); });
T.test('a knockdown from high up stays down until it lands, then its ground time starts', () => { const S=N(), d=F(S,1); Object.assign(d,{act:'knock',air:true,y:5000,vy:0,inv:36});
  let n=0; while(d.air&&n<80){ T.feed(S,1,0,0); n++; T.eq(d.act,'knock','frame '+n+' of the fall'); } T.ok(n>__VF.CFG.knock.ground,'fall of '+n+' frames'); T.eq(d.af,1); T.ok(d.inv>0); });
