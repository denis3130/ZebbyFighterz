// Entry point: game state, the fixed step and boot. Later tasks add the real-time loop, input and rendering.
const G={state:'boot',mode:null,S:null,acc:0,last:0};
function boot(){inputInit();G.state='title';}
// One game step: read the inputs (player 1 is the dummy in training), advance the sim, hand its events to the effects and the HUD.
function stepGame(now){
  const S=G.S;
  const in0=typeof inputRead==='function'?inputRead(0):0;
  const in1=S.mode==='training'?dummyInput(S,1):typeof inputRead==='function'?inputRead(1):0;
  simStep(S,in0,in1);
  if(typeof fxEvents==='function') fxEvents(S,now);
  if(typeof hudEvents==='function') hudEvents(S);
}
// n game steps, then one render if there is a renderer.
function frame(n){
  const now=performance.now();
  for(let i=0;i<n;i++) stepGame(now);
  if(typeof renderFrame==='function') renderFrame(G.S,now);
}
function startMatch(mode,o){
  o=o||{};
  G.S=simCreate({seed:o.seed===undefined?1:o.seed,mode,chars:['ren','kael'],dummy:o.dummy});
  G.mode=mode; G.state='fight';
}
window.__VF={G,CFG,ASSETS,BTN,simCreate,simStep,simClone,simHash,fighterOf,simRand,hitstunFor,scaleFor,canBeHit,moveBox,hurtBoxes,isBlocking,dummyInput,startMatch,frame,inputInit,inputRead,inputAssign,IN};
boot();
