// Entry point: game state, the fixed step and boot. Later tasks add the full real-time loop (tick) and the menus.
const G={state:'boot',mode:null,S:null,opts:null,acc:0,last:null};
// Input first, then the renderer: the title comes only once the arena's textures are decoded.
function boot(){saveLoad();inputInit();hudInit();menuInit();renderInit().then(()=>{G.state='title';navReset('intro');menuOrient();requestAnimationFrame(loop);});}
// The animation-frame callback: the next frame is scheduled first, and an exception in one frame is reported, not fatal.
function loop(now){requestAnimationFrame(loop);try{tick(now);}catch(e){console.error(e);}}
// The real-time cycle: an accumulator of 1000/60 ms feeds stepGame (at most CFG.loop.maxSteps per tick, the rest of a
// long stall is dropped), then one render and one HUD update. Steps only in a fight, and only with a known last time
// (the first tick after a start or a resume just records it, so a pause is never caught up).
function tick(now){
  const dt=1000/60; let simMs=0,n=0;
  menuPad();
  if(G.state==='fight'&&G.S){
    if(G.last===null){G.last=now;G.acc=0;}
    else{
      G.acc+=Math.min(now-G.last,250);G.last=now;
      while(G.acc>=dt&&n<CFG.loop.maxSteps&&G.state==='fight'){
        const t0=performance.now();stepGame(now);simMs+=performance.now()-t0;G.acc-=dt;n++;
      }
      if(G.acc>dt)G.acc=dt;
    }
  }
  menuCheckEnd();
  const t1=performance.now();
  if(G.state==='title'||G.state==='end')uiFrame(now);   // menus and results: the layered scene covers the arena, which is not drawn
  else if(G.state!=='boot'){renderFrame(G.S,now);hudUpdate(G.S);}
  menuFps(now,simMs,n,performance.now()-t1);
}
// One game step: read the inputs (player 1 is the dummy in training), advance the sim, hand its events to the effects and the HUD.
function stepGame(now){
  const S=G.S;
  const in0=typeof inputRead==='function'?inputRead(0):0;
  const in1=S.mode==='training'?dummyInput(S,1):typeof inputRead==='function'?inputRead(1):0;
  simStep(S,in0,in1);
  if(typeof fxEvents==='function') fxEvents(S,now);
  if(typeof hudEvents==='function') hudEvents(S);
  if(typeof uiEvents==='function') uiEvents(S);   // the match statistics for the results (reads the events only)
}
// n game steps, then one render if there is a renderer.
function frame(n){
  const now=performance.now();
  for(let i=0;i<n;i++) stepGame(now);
  if(typeof renderFrame==='function') renderFrame(G.S,now);
  if(typeof hudUpdate==='function') hudUpdate(G.S);
}
// o = {seed, dummy, chars, rounds, timeS}: G.opts keeps them, so a restart plays the same match again with a new seed.
function startMatch(mode,o){
  o=o||{};
  G.opts={chars:o.chars||['ren','kael'],rounds:o.rounds,timeS:o.timeS};
  G.S=simCreate({seed:o.seed===undefined?1:o.seed,mode,chars:G.opts.chars,dummy:o.dummy,rounds:o.rounds,timeS:o.timeS});
  if(typeof renderCast==='function')renderCast(G.opts.chars);   // the chosen fighters on their sides
  if(typeof hudReset==='function')hudReset(G.S);                 // their names and faces in the HUD at once
  G.mode=mode; G.state='fight'; G.acc=0; G.last=null; menuSync();
}
window.__VF={G,CFG,ASSETS,BTN,simCreate,simStep,simClone,simHash,fighterOf,simRand,hitstunFor,scaleFor,canBeHit,moveBox,hurtBoxes,isBlocking,dummyInput,startMatch,frame,tick,menu,menuMove,menuPress,menuBack,menuPad,menuOrient,menuFpsInit,navRegister,navGo,navBack,navReset,navReplace,navClear,navMove,navPress,navTab,navFocus,navPadPoll,uiTap,cLogo,cHead,cBtn,cItem,cCard,cTabs,cStepper,cStatBar,cProgress,cChip,cBack,uiToast,uiConfirm,layersSet,layersShift,layersDepth,layersQuality,layersFrame,uiFrame,introAt,introSkip,F3D_BY,renderCast,fxRecast,bridgePreload,bridgeWarm,bridgeStart,bridgeResult,bridgeArenaShot,uiEvents,inputInit,inputRead,inputAssign,IN,touchShow,renderInit,renderFrame,renderResize,cam,toScreen,ARENA,scene,camera,renderer,F3D,fighterBuild,poseOf,limbWorld,modelBuild,mdData,mdPoseOf,mdMix,mdSample,mdApply,headTop,FX,fxEvents,fxUpdate,hudInit,hudUpdate,hudEvents,HUD,UI:{get SV(){return SV;},NAV,LY,INTRO,UIB,VS,RS},MN,vsLife,rsLife,layersBurst,saveDefaults,saveLoad,saveWrite,progLevel,progMatchXp,progAddXp,progRecord};
boot();
