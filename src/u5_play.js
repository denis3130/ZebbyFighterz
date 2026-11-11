// The way into a match (spec §3): main menu, the «Gioca» block, the local versus options. Later tasks add the fighter
// select, the arena, the VS screen and the results to this file. Locked entries say what is still to come.
const VSOPT = {r: null, tm: null};   // the versus options chosen in this session (indexes into CFG.ui.vsOpts)

function playScreens() {
  // --- Main menu: entries on the left, the «Gioca» block under them (Arcade, Online, Versus locale), the player's chip
  // top right, the last fighter used large on the right with the rival behind (the layered scene).
  navRegister({id: 'menu', scene: 'menu', layers: () => ({hero: (SV && SV.lastChar) || 'ren'}),
    build(r) {
      const soon = 'In arrivo nella prossima versione';
      r.appendChild(cLogo('s'));
      const list = uiEl('div', 'mmList');
      list.setAttribute('data-wrap', '');
      const vs = cItem({label: 'Versus locale', act0: 'vs', act: () => navGo('vsopts')});
      vs.classList.add('mmVs');
      list.append(cItem({label: 'Gioca', act0: 'play', act: () => navFocus(vs)}),
        cItem({label: 'Allenamento', act0: 'train', act: dev => { if (dev === 'touch') mnFullscreen(); mnStart('training', dev); }}),
        cItem({label: 'Profilo', locked: true, note: soon}), cItem({label: 'Pass stagionale', locked: true, note: soon}), cItem({label: 'Impostazioni', locked: true, note: soon}));
      const cards = uiEl('div', 'mmCards');
      cards.append(cCard({label: 'Arcade', img: ASSETS['ui/card_arcade.webp'], locked: true, note: 'Arcade in arrivo'}),
        cCard({label: 'Online', img: ASSETS['ui/card_online.webp'], locked: true, note: 'Modalità online in arrivo'}));
      const play = uiEl('div', 'mmPlay');
      play.append(cards, vs);
      const chip = uiEl('div', 'mmChip');
      r.append(list, play, chip);
    },
    enter() { const c = this.root.querySelector('.mmChip'); c.innerHTML = ''; c.appendChild(cChip()); },
    back() { return false; }});
  // --- Local versus: rounds and time, Ren for player 1 on the left and Kael for player 2 on the right, «Combatti».
  navRegister({id: 'vsopts', scene: 'versus', layers: () => ({hero: 'ren', rival: 'kael'}),
    build(r) {
      const O = CFG.ui.vsOpts;
      if (VSOPT.r === null) { VSOPT.r = O.r; VSOPT.tm = O.tm; }
      r.appendChild(cBack());
      const head = cHead('Versus locale', 'Scontro tra due giocatori sullo stesso dispositivo.');
      const mid = uiEl('div', 'voMid');
      mid.append(cStepper({label: 'Round', values: O.rounds, i: VSOPT.r, onChange: v => { VSOPT.r = O.rounds.indexOf(v); }}),
        cStepper({label: 'Tempo', values: O.time, i: VSOPT.tm, fmt: v => (v ? String(v) : '∞'), onChange: v => { VSOPT.tm = O.time.indexOf(v); }}));
      const tags = uiEl('div', 'voTags', '<span class="voTag">Giocatore 1</span><span class="voTag">Giocatore 2</span>');
      const go = cBtn({label: 'Combatti', kind: 'main', act0: 'fight', act: dev => {
        if (dev === 'touch') mnFullscreen();
        mnStart('versus', dev, {rounds: O.rounds[VSOPT.r], timeS: O.time[VSOPT.tm]});
      }});
      go.querySelector('.ub').setAttribute('data-first', '');
      r.append(head, mid, tags, go);
    }});
}
