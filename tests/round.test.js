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

// Final fix wave: after TEMPO! nothing new resolves (no command, contact or projectile), so the round goes to whoever
// was ahead at time-up.
T.test('time up: a P held through TEMPO! does not punch after it', () => { const S=fight(); near(S); F(S,0).hp=500; F(S,1).hp=510; S.timer=3; const late=[]; let hp=null;
  for(let i=0;i<160;i++){ T.feed(S,1,i<5?B.P:0,0); if(S.phase==='timeup') hp=[F(S,0).hp,F(S,1).hp]; if(S.phase!=='fight') for(const e of S.ev) if(/^(hit|block|thr|proj|projHit|projBlock)$/.test(e.t)) late.push(e.t+'@'+i); }
  T.eq(late.join(),'','after time-up'); T.eq(hp.join(),'500,510','hp until the round is scored'); T.eq(S.wins.join(),'0,1'); });
T.test('time up: a Special still in startup does not fire after TEMPO!', () => { const S=fight(); F(S,0).hp=500; F(S,1).hp=560; S.timer=6; T.feed(S,1,B.S,0); T.eq(F(S,0).act,'spec');
  let proj=false, hp=null; for(let i=0;i<160;i++){ T.feed(S,1,0,0); proj=proj||S.proj.length>0||S.ev.some(e=>/^proj/.test(e.t)); if(S.phase==='timeup') hp=F(S,1).hp; }
  T.ok(!proj,'projectile after time-up'); T.eq(hp,560,'hp until the round is scored'); T.eq(S.wins.join(),'0,1'); });
T.test('time up: a heavy still in startup at TEMPO! does not land', () => { const S=fight(); near(S); F(S,0).hp=500; F(S,1).hp=520; S.timer=14;
  T.feed(S,12,B.P,0); T.eq(F(S,0).act,'hp'); T.feed(S,2,0,0); T.eq(S.phase,'timeup'); T.feed(S,140,0,0); T.eq(F(S,1).hp,520,'hp until the round is scored'); T.feed(S,10,0,0); T.eq(S.wins.join(),'0,1'); });
T.test('KO: a P held through the KO does not come out after the freeze', () => { const S=fight(); near(S); F(S,1).hp=20; T.feed(S,1,B.P,0); T.feed(S,1,0,0);
  let n=0; while(S.phase==='fight'&&n<20){ T.feed(S,1,B.P,0); n++; } T.eq(S.phase,'ko'); const acts=[];
  for(let i=0;i<120;i++){ T.feed(S,1,0,0); if(acts[acts.length-1]!==F(S,0).act) acts.push(F(S,0).act); } T.eq(acts.join(),'p1,idle','acts after the KO'); });
// Interface U1, Task 8: the match options chosen in the menus (rounds to play, time per round), kept in the state.
T.test('rounds option: 1 round wins the match', () => { const S = N({rounds: 1}); T.eq(S.need, 1); F(S, 1).hp = 1; near(S); T.feed(S, 1, B.P, 0); T.feed(S, 400, 0, 0); T.eq(S.phase, 'end'); T.eq(S.winner, 0); });
T.test('rounds option: 5 rounds need 3 wins', () => { T.eq(N({rounds: 5}).need, 3); T.eq(N({rounds: 3}).need, 2); T.eq(N({}).need, __VF.CFG.round.wins); });
T.test('time option: 0 = no timer, 60 = 3600 frames, every round', () => { T.eq(N({timeS: 0}).timer, -1); T.eq(N({timeS: 60}).timer, 3600); T.eq(N({}).timer, __VF.CFG.round.timerS * 60);
  const S = N({timeS: 60, rounds: 3}); F(S, 1).hp = 1; near(S); T.feed(S, 1, B.P, 0); T.feed(S, 400, 0, 0); T.eq(S.round, 2); T.ok(S.timer > 3400 && S.timer <= 3600, 'next round timer ' + S.timer); });
