// Round flow, training and dummy. fight(), trainingFight(), near(), B, F come from tests/lib.js.
T.test('intro ignores inputs for 100 frames', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); T.eq(S.phase,'intro'); T.feed(S,99,B.R,0); T.eq(F(S,0).x,-1200); T.feed(S,1,0,0); T.eq(S.phase,'fight'); });
T.test('timer counts 99 s only in fight', () => { const S=fight(); T.eq(S.timer,99*60); T.feed(S,60,0,0); T.eq(S.timer,98*60); });
T.test('KO ends the round and the winner gets a win', () => { const S=fight(); F(S,1).hp=20; near(S); T.feed(S,1,B.P,0); T.feed(S,6,0,0); T.eq(S.phase,'ko'); T.feed(S,150,0,0); T.eq(S.wins[0],1); T.eq(S.round,2); T.eq(S.phase,'intro'); T.eq(F(S,1).hp,1000); });
T.test('time up: more health wins', () => { const S=fight(); F(S,0).hp=500; S.timer=1; T.feed(S,1,0,0); T.eq(S.phase,'timeup'); T.feed(S,150,0,0); T.eq(S.wins[1],1); });
T.test('double KO is a draw round', () => { const S=fight(); F(S,0).hp=10; F(S,1).hp=10; near(S); T.feed(S,1,B.P,B.P); T.feed(S,200,0,0); T.eq(S.wins[0],1); T.eq(S.wins[1],1); T.ok(['intro','fight'].includes(S.phase)); });
T.test('best of 3: 2 wins end the match', () => { const S=fight(); S.wins=[1,0]; F(S,1).hp=1; near(S); T.feed(S,1,B.P,0); T.feed(S,200,0,0); T.eq(S.phase,'end'); T.eq(S.winner,0); });
T.test('2-2 after draws is a draw match', () => { const S=fight(); S.wins=[1,1]; F(S,0).hp=1; F(S,1).hp=1; near(S); T.feed(S,1,B.P,B.P); T.feed(S,200,0,0); T.eq(S.winner,2); });
T.test('training: no timer, health refills 60 frames after the combo', () => { const S=__VF.simCreate({seed:1,mode:'training',chars:['ren','kael'],dummy:'fermo'}); T.feed(S,100,0,0); T.eq(S.timer,-1); near(S); T.feed(S,1,B.P,0); T.feed(S,30,0,0); T.ok(F(S,1).hp<1000); T.feed(S,60,0,0); T.eq(F(S,1).hp,1000); });
T.test('training: health never below 1', () => { const S=trainingFight(); F(S,1).hp=5; near(S); T.feed(S,1,B.P,0); T.feed(S,6,0,0); T.eq(F(S,1).hp,1); T.ok(S.phase==='fight'); });
T.test('dummy fermo sends nothing', () => { const S=trainingFight(); T.eq(__VF.dummyInput(S,1),0); });
T.test('dummy casuale is deterministic and moves', () => { const run=()=>{const S=__VF.simCreate({seed:5,mode:'training',chars:['ren','kael'],dummy:'casuale'}); for(let i=0;i<600;i++) __VF.simStep(S,0,__VF.dummyInput(S,1)); return S;};
  const a=run(), b=run(); T.eq(__VF.simHash(a),__VF.simHash(b)); T.ok(F(a,1).x!==1200,'it moved'); });

// Behaviour of this task that the tests above do not pin down.
T.test('round and fight events: round at the intro start, fight when it ends', () => { const S=__VF.simCreate({seed:1,mode:'versus'}); const seen=[]; for(let i=0;i<100;i++){ T.feed(S,1,0,0); for(const e of S.ev) seen.push(e.t+'@'+(i+1)); } T.eq(seen.join(),'round@1,fight@100'); });
T.test('KO: event, hitstop, the loser falls and stays down; inputs are ignored', () => { const S=fight(); F(S,1).hp=20; near(S); T.feed(S,1,B.P,0); let ko=null; for(let i=0;i<10&&!ko;i++){ T.feed(S,1,0,0); ko=S.ev.find(e=>e.t==='ko'); }
  T.ok(ko,'ko event'); T.eq(ko.side,1); T.eq(S.stop,40); T.eq(F(S,1).hp,0); T.feed(S,100,B.R|B.U,B.L|B.U); T.eq(F(S,1).act,'ko'); T.eq(F(S,1).y,0); T.eq(F(S,0).act,'idle'); });
T.test('chip damage from a blocked projectile can KO', () => { const S=fight(); F(S,1).hp=5; T.feed(S,1,B.S,0); T.feed(S,1,0,B.GUARD); let ko=false; for(let i=0;i<80;i++){ T.feed(S,1,0,B.GUARD); if(S.ev.some(e=>e.t==='ko')) ko=true; } T.ok(ko,'chip KO'); T.eq(S.phase,'ko'); T.feed(S,150,0,0); T.eq(S.wins[0],1); });
T.test('time up with equal health is a draw round; timeup event', () => { const S=fight(); S.timer=1; let ev=false; T.feed(S,1,0,0); ev=S.ev.some(e=>e.t==='timeup'); T.ok(ev); T.feed(S,150,0,0); T.eq(S.wins[0],1); T.eq(S.wins[1],1); });
T.test('the timer also runs during hitstop', () => { const S=fight(); near(S); T.feed(S,1,B.P,0); T.feed(S,40,0,0); T.eq(S.timer,99*60-41); });
T.test('next round: start positions, full health, meter kept, no projectiles', () => { const S=fight(); F(S,0).meter=700; F(S,1).hp=20; F(S,0).x=-2000; near(S); T.feed(S,1,B.P,0); T.feed(S,170,0,0);
  T.eq(S.round,2); T.eq(F(S,0).x,-1200); T.eq(F(S,1).x,1200); T.eq(F(S,0).hp,1000); T.ok(F(S,0).meter>=700); T.eq(S.proj.length,0); T.eq(S.timer,99*60); T.feed(S,100,0,0); T.eq(S.phase,'fight'); });
T.test('training refill waits while the combo goes on', () => { const S=trainingFight(); F(S,1).hp=500; F(S,1).combo=1; T.feed(S,100,0,0); T.eq(F(S,1).hp,500); F(S,1).combo=0; T.feed(S,59,0,0); T.eq(F(S,1).hp,500); T.feed(S,1,0,0); T.eq(F(S,1).hp,1000); });
T.test('startMatch and frame(n)', () => { __VF.startMatch('training',{seed:3,dummy:'fermo'}); const G=__VF.G; T.eq(G.state,'fight'); T.eq(G.mode,'training'); T.eq(G.S.phase,'intro'); __VF.frame(100); T.eq(G.S.phase,'fight'); T.eq(G.S.frame,100);
  __VF.startMatch('versus'); __VF.frame(250); T.eq(G.S.timer,99*60-150); });
