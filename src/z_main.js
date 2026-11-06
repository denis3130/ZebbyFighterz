// Entry point: game state and boot. Later tasks add the fixed-step loop, input and rendering.
const G={state:'boot',mode:null,S:null,acc:0,last:0};
function boot(){G.state='title';}
window.__VF={G,CFG,ASSETS};
boot();
