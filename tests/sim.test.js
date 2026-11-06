// Fight simulation: state, movement, pushboxes, facing, determinism. B, N, F come from tests/lib.js.
T.test('start positions', () => { const S=N(); T.eq(F(S,0).x,-1200); T.eq(F(S,1).x,1200); T.eq(F(S,0).face,1); T.eq(F(S,1).face,-1); });
T.test('walk forward 20f', () => { const S=N(); T.feed(S,20,B.R,0); T.eq(F(S,0).x,-1200+75*20); });
T.test('walk back is slower', () => { const S=N(); T.feed(S,30,B.L,0); T.eq(F(S,0).x,-1200-58*30); });
T.test('neutral jump lands after squat + airtime', () => { const S=N(); T.feed(S,1,B.U,0); let n=1; while(F(S,0).act!=='idle'&&n<200){T.feed(S,1,0,0);n++;}
  T.ok(n>=4+40&&n<=4+44+2, 'frames '+n); T.eq(F(S,0).y,0); });
T.test('jump apex about 1.55 m', () => { const S=N(); let top=0; T.feed(S,1,B.U,0); for(let i=0;i<60;i++){T.feed(S,1,0,0);top=Math.max(top,F(S,0).y);} T.near(top,1550,80); });
T.test('dash forward by button and by double tap', () => { const a=N(); T.feed(a,1,B.DASH,0); T.eq(F(a,0).act,'dashF');
  const b=N(); T.feed(b,1,B.R,0); T.feed(b,2,0,0); T.feed(b,1,B.R,0); T.eq(F(b,0).act,'dashF'); });
T.test('back + dash = back dash', () => { const S=N(); T.feed(S,1,B.L|B.DASH,0); T.eq(F(S,0).act,'dashB'); });
T.test('fighters never overlap and stay inside walls', () => { const S=N(); T.feed(S,200,B.R,B.L); T.ok(F(S,1).x-F(S,0).x>=2*260); const W=N(); T.feed(W,400,B.L,B.L); T.eq(F(W,0).x,-6000+260); T.eq(F(W,1).x,-6000+3*260); });
T.test('max separation', () => { const S=N(); T.feed(S,300,B.L,B.R); T.ok(F(S,1).x-F(S,0).x<=5500); });
T.test('sides switch when jumping over', () => { const S=N(); F(S,1).x=0; T.feed(S,1,0,B.U|B.L); T.feed(S,80,0,B.L); T.ok(F(S,1).x<F(S,0).x); T.feed(S,5,0,0); T.eq(F(S,0).face,-1); T.eq(F(S,1).face,1); });
T.test('determinism: same inputs same hash', () => { const run=()=>{const S=N(); let r=7; for(let i=0;i<900;i++){r=(r*1103515245+12345)>>>0; T.feed(S,1,r>>>16&511,r>>>7&511);} return __VF.simHash(S);}; T.eq(run(),run()); });
T.test('clone then continue gives the same hash', () => { const A=N(); T.feed(A,120,B.R,B.L|B.U); const C=__VF.simClone(A); T.feed(A,200,B.U|B.R,B.D); T.feed(C,200,B.U|B.R,B.D); T.eq(__VF.simHash(A),__VF.simHash(C)); });
T.test('sim is pure: no Math.random, no clock', () => { const mr=Math.random, pn=performance.now, dn=Date.now; Math.random=()=>{throw Error('Math.random');}; performance.now=()=>{throw Error('clock');}; Date.now=performance.now;
  try{ const S=N(); T.feed(S,300,B.R|B.P,B.L|B.K); } finally { Math.random=mr; performance.now=pn; Date.now=dn; } });
T.test('left+right is neutral', () => { const S=N(); T.feed(S,30,B.L|B.R,0); T.eq(F(S,0).x,-1200); });

// Behaviour of this task that the tests above do not pin down.
T.test('up+down is neutral', () => { const S=N(); T.feed(S,10,B.U|B.D,0); T.eq(F(S,0).act,'idle'); T.eq(F(S,0).y,0); });
T.test('crouch and guard do not walk; guard + down is the low guard', () => { const S=N();
  T.feed(S,5,B.D|B.R,0); T.eq(F(S,0).act,'crouch'); T.feed(S,5,B.GUARD|B.R,0); T.eq(F(S,0).act,'guard'); T.feed(S,5,B.GUARD|B.D,0); T.eq(F(S,0).act,'guardC'); T.eq(F(S,0).x,-1200); });
T.test('jump direction is the one held when the squat ends', () => { const S=N(); T.feed(S,1,B.U,0); T.feed(S,3,B.R,0); T.eq(F(S,0).act,'jumpSquat');
  T.feed(S,1,B.L,0); T.eq(F(S,0).act,'air'); T.eq(F(S,0).vx,-52); const f=N(); T.feed(f,1,B.U,0); T.feed(f,3,0,0); T.feed(f,1,B.R,0); T.eq(F(f,0).vx,62); T.eq(F(f,0).x,-1200+62); });
T.test('landing lasts jump.land frames, then the fighter can act', () => { const S=N(); T.feed(S,1,B.U,0); T.feed(S,46,0,0); T.eq(F(S,0).act,'landing'); T.eq(F(S,0).af,1); T.eq(F(S,0).y,0);
  T.feed(S,1,B.R,0); T.eq(F(S,0).act,'landing','no walking while landing'); T.eq(F(S,0).x,-1200); T.feed(S,1,B.R,0); T.eq(F(S,0).act,'walkF'); });
T.test('dash speed eases from v0 to v1 over n frames, then idle', () => { const S=N(), v=[]; T.feed(S,1,B.DASH,0); v.push(F(S,0).vx);
  for(let i=1;i<18;i++){ T.feed(S,1,0,0); v.push(F(S,0).vx); } T.eq(v[0],170); T.eq(v[17],40); T.ok(v.every((x,i)=>!i||x<=v[i-1]),'slows down '+v); T.eq(F(S,0).act,'dashF'); T.feed(S,1,0,0); T.eq(F(S,0).act,'idle');
  const b=N(); T.feed(b,1,B.L|B.DASH,0); T.eq(F(b,0).vx,-150); T.feed(b,19,0,0); T.eq(F(b,0).vx,-30); T.eq(F(b,0).act,'dashB'); T.feed(b,1,0,0); T.eq(F(b,0).act,'idle'); });
T.test('hold counts the frames P and K are held; the release frame keeps the press length', () => { const S=N(); T.feed(S,3,B.P,0); T.eq(F(S,0).hold[0],3);
  T.feed(S,1,B.K,0); T.eq(F(S,0).hold[0],3); T.eq(F(S,0).hold[1],1); T.feed(S,1,B.K,0); T.eq(F(S,0).hold[0],0); T.eq(F(S,0).hold[1],2); });
T.test('double tap: forward only, within dash.tap frames, and it uses the first tap up', () => { const S=N(); T.feed(S,1,B.R,0); T.feed(S,9,0,0); T.feed(S,1,B.R,0); T.eq(F(S,0).act,'dashF'); T.eq(F(S,0).tap.dir,0);
  const late=N(); T.feed(late,1,B.R,0); T.feed(late,10,0,0); T.feed(late,1,B.R,0); T.eq(F(late,0).act,'walkF'); const back=N(); T.feed(back,1,B.L,0); T.feed(back,2,0,0); T.feed(back,1,B.L,0); T.eq(F(back,0).act,'walkB'); });
T.test('a jump keeps its facing until it lands', () => { const S=N(); F(S,1).x=0; T.feed(S,1,0,B.U|B.L); T.feed(S,30,0,B.L); T.ok(F(S,1).x<F(S,0).x,'crossed'); T.eq(F(S,1).act,'air'); T.eq(F(S,1).face,-1); T.eq(F(S,0).face,-1); });
T.test('max separation holds back only the fighter moving away', () => { const S=N(); T.feed(S,300,0,B.R); T.eq(F(S,0).x,-1200); T.eq(F(S,1).x,-1200+5500); });
T.test('movement events: dash, jump, land', () => { const S=N(), seen=[]; const step=b=>{ T.feed(S,1,b,0); for(const e of S.ev) seen.push(e.t+':'+e.side+'@'+S.frame); };
  step(B.DASH); for(let i=0;i<18;i++) step(0); step(B.U); for(let i=0;i<60;i++) step(0); T.eq(seen.join(),'dash:0@1,jump:0@24,land:0@66'); });
T.test('clone is a deep copy', () => { const A=N(); T.feed(A,5,B.R,0); const C=__VF.simClone(A); T.ok(C!==A&&F(C,0)!==F(A,0)&&F(C,0).tap!==F(A,0).tap,'shares objects');
  T.eq(__VF.simHash(C),__VF.simHash(A)); T.feed(A,10,B.R,0); T.eq(F(C,0).x,-1200+5*75); T.eq(C.frame,5); });
T.test('hash is FNV-1a hex of the state without ev, and follows the state', () => { T.eq(__VF.simHash({ev:[{t:'hit'}],a:1}),'8b9e4511');
  const a=N(), b=N(); T.eq(__VF.simHash(a),__VF.simHash(b)); T.feed(b,1,B.R,0); T.ok(__VF.simHash(a)!==__VF.simHash(b)); });
T.test('seeded generator is mulberry32 on S.rng', () => { const take=S=>[0,1,2,3,4].map(()=>__VF.simRand(S,4294967296)); const a=N({seed:42}), x=take(a);
  T.eq(x.join(),'2581720956,1925393290,3661312704,2876485805,750819978'); T.eq(take(N({seed:42})).join(),x.join()); T.ok(take(N({seed:43})).join()!==x.join());
  for(let i=0;i<50;i++){ const v=__VF.simRand(a,6); T.ok(v>=0&&v<6&&v%1===0,'out of range '+v); } });

// Final fix wave: after a cross-up the fighter faces the opponent before its next action starts. crossUp() = side 0 jumps
// forward over side 1 and lands against the right wall, still facing the wall: back on its landing.
function crossUp() { const S=N(); F(S,0).x=3400; F(S,1).x=5200; T.feed(S,5,B.U|B.R,0); let n=0; while(F(S,0).act!=='landing'&&n<100){ T.feed(S,1,0,0); n++; }
  T.ok(F(S,0).x>F(S,1).x,'crossed over'); T.eq(F(S,0).act,'landing'); return S; }
T.test('after a cross-up, a P tapped during the landing comes out facing the opponent and hits', () => { const S=crossUp();
  T.feed(S,1,B.P,0); T.feed(S,1,0,0); let box=null, hit=false;
  for(let i=0;i<12;i++){ T.feed(S,1,0,0); box=box||__VF.moveBox(F(S,0),'p1'); hit=hit||S.ev.some(e=>e.t==='hit'&&e.side===0); }
  T.ok(box&&box.x1<=F(S,0).x,'p1 box faces the opponent: '+JSON.stringify(box)+' at '+F(S,0).x); T.ok(hit,'p1 hits'); T.eq(F(S,0).face,-1); });
T.test('after a cross-up, a dash pressed during the landing is toward or away from the opponent as pressed', () => { const S=crossUp(), x=F(S,0).x;
  T.feed(S,1,B.L|B.DASH,0); T.feed(S,4,0,0); T.eq(F(S,0).act,'dashF','left = toward the opponent = forward'); T.ok(F(S,0).x<x,'it dashes toward the opponent');
  const A=crossUp(); T.feed(A,1,B.R|B.DASH,0); T.feed(A,4,0,0); T.eq(F(A,0).act,'dashB','right = away from the opponent = back'); });
