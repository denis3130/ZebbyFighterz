// Entry point: game state, the fixed step and boot. Later tasks add the full real-time loop (tick) and the menus.
const G={state:'boot',mode:null,S:null,acc:0,last:0};
// Input first, then the renderer: the title comes only once the arena's textures are decoded.
function boot(){inputInit();hudInit();renderInit().then(()=>{G.state='title';requestAnimationFrame(drawLoop);});}
// Until the full loop (tick) exists: every animation frame redraws the title or the fight; the sim does not step here.
function drawLoop(now){if(G.state==='fight'||G.state==='title') renderFrame(G.S,now);
  if(G.state==='fight') hudUpdate(G.S);requestAnimationFrame(drawLoop);}
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
  if(typeof hudUpdate==='function') hudUpdate(G.S);
}
function startMatch(mode,o){
  o=o||{};
  G.S=simCreate({seed:o.seed===undefined?1:o.seed,mode,chars:['ren','kael'],dummy:o.dummy});
  G.mode=mode; G.state='fight'; touchShow(true);
}
window.__VF={G,CFG,ASSETS,BTN,simCreate,simStep,simClone,simHash,fighterOf,simRand,hitstunFor,scaleFor,canBeHit,moveBox,hurtBoxes,isBlocking,dummyInput,startMatch,frame,inputInit,inputRead,inputAssign,IN,touchShow,renderInit,renderFrame,renderResize,cam,toScreen,ARENA,scene,camera,renderer,F3D,fighterBuild,poseOf,limbWorld,FX,fxEvents,fxUpdate,hudInit,hudUpdate,hudEvents,HUD};
boot();
