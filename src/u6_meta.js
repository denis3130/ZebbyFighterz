// Interface U2 (spec §3-4): the moves list and the settings, reachable from the pause (without leaving the fight) and
// from the main menu. Both show the controls of the device in use first (touch, keyboard or controller); the settings
// apply and save at once (the device save, u0_save.js).

// The moves of the Tappa 1 (spec 2026-11-06 §2), with the input on each device. Keyboard = player 1's keys (WASD, J K L U I).
const META_MOVES = [
  ['Muoversi e saltare', 'Levetta', 'W A S D', 'Levetta o croce'],
  ['Pugno', 'Pugno', 'J', 'X / Quadrato'],
  ['Calcio', 'Calcio', 'K', 'A / Croce'],
  ['Colpo forte', 'Tieni Pugno o Calcio', 'Tieni J o K', 'Tieni X o A'],
  ['Combo', 'Tocchi ripetuti, poi Calcio', 'J J J, poi K', 'X X X, poi A'],
  ['Lancio in aria', 'Giù + Calcio tenuto', 'S + K tenuto', 'Giù + A tenuto'],
  ['Speciale', 'Speciale', 'L', 'B / Cerchio'],
  ['Presa', 'Pugno + Calcio, da vicino', 'J + K, da vicino', 'X + A, da vicino'],
  ['Scatto', 'Scatto', 'U, o avanti due volte', 'Dorsale destro, o avanti due volte'],
  ['Scatto indietro', 'Indietro + Scatto', 'Indietro + U', 'Indietro + dorsale destro'],
  ['Guardia', 'Guardia', 'I, o tieni indietro', 'Dorsale sinistro, o tieni indietro'],
  ['Guardia bassa', 'Guardia accovacciati', 'I accovacciati', 'Dorsale sinistro accovacciati'],
];
const META_DEVS = ['Tocco', 'Tastiera', 'Controller'];
const metaDevIx = () => (NAV.dev === 'touch' ? 0 : NAV.dev === 'pad' ? 2 : 1);
// A list of «name — input» rows for one device (ix 0 touch, 1 keyboard, 2 controller), in two columns where there is room.
function metaMovesRows(ix) {
  const g = uiEl('div', 'mvGrid');
  for (const m of META_MOVES) g.appendChild(uiEl('div', 'mvRow', '<span class="mvN">' + uiEsc(m[0]) + '</span><span class="mvK">' + uiEsc(m[ix + 1]) + '</span>'));
  return g;
}

function metaScreens() {
  // --- Lista mosse: the moves with the inputs of the device in use; the tabs show the other devices.
  navRegister({id: 'moves', scene: 'menu', layers: () => ({hero: (SV && SV.lastChar) || 'ren'}),
    build(r) {
      r.appendChild(cBack());
      const top = uiEl('div', 'mtTop');
      top.appendChild(cHead('Lista mosse', 'Le stesse mosse per Ren e Kael.'));
      const body = uiEl('div', 'mtBody');
      const tabs = cTabs(META_DEVS, 1, k => { body.innerHTML = ''; body.appendChild(metaMovesRows(k)); });
      tabs.classList.add('mtTabs');
      top.appendChild(tabs);
      r.append(top, body);
      this.tabs = tabs;
    },
    enter(p, back) { if (!back) metaTabStart(this.tabs, metaDevIx()); }});

  // --- Impostazioni: Audio | Grafica | Comandi | Lingua, as Denis's reference 03. A change applies and is saved at once.
  navRegister({id: 'settings', scene: 'menu', layers: () => ({hero: 'kael'}),
    build(r) {
      r.appendChild(cBack());
      const top = uiEl('div', 'mtTop');
      top.appendChild(cHead('Impostazioni'));
      const body = uiEl('div', 'mtBody stBody');
      const tabs = cTabs(['Audio', 'Grafica', 'Comandi', 'Lingua'], 0, k => { body.innerHTML = ''; metaSettingsTab(body, k); });
      tabs.classList.add('mtTabs');
      top.appendChild(tabs);
      r.append(top, body);
      this.tabs = tabs;
    },
    enter(p, back) { if (!back) metaTabStart(this.tabs, (p && p.tab) || 0); }});
  metaProfileScreen();
}

// Opens tab k and gives it the first focus (the navigation focuses [data-first] when the screen shows).
function metaTabStart(tabs, k) { [...tabs.children].forEach((t, j) => t.toggleAttribute('data-first', j === k)); tabs.children[k].uiAct(); }
// One settings row: a label on the left, its control on the right.
function metaRow(label, ctrl, note) {
  const row = uiEl('div', 'stRow', '<span class="stL">' + uiEsc(label) + (note ? '<em class="stNote">' + uiEsc(note) + '</em>' : '') + '</span>');
  row.appendChild(ctrl);
  return row;
}
function metaSave(fn) { if (SV) { fn(SV.settings); saveWrite(); } }
const META_Q = ['auto', 'bassa', 'media', 'alta'], META_QN = {auto: 'Auto', bassa: 'Bassa', media: 'Media', alta: 'Alta'};
function metaSettingsTab(body, k) {
  const S = SV ? SV.settings : {};
  if (k === 0) {        // Audio: the levels are kept for when the sounds arrive
    const pct = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], at = v => Math.max(0, pct.indexOf(Math.round((v === undefined ? 70 : v) / 10) * 10));
    body.append(metaRow('Musica', cStepper({label: 'Volume', values: pct, i: at(S.music), fmt: v => v + '%', onChange: v => metaSave(s => { s.music = v; })})),
      metaRow('Effetti', cStepper({label: 'Volume', values: pct, i: at(S.sfx === undefined ? 85 : S.sfx), fmt: v => v + '%', onChange: v => metaSave(s => { s.sfx = v; })})),
      uiEl('p', 'stInfo', 'Musica ed effetti sonori sono in arrivo: i volumi scelti restano salvati.'));
  } else if (k === 1) { // Grafica: the quality of the menus' scene (Auto = chosen for this device), the FPS counter
    body.append(metaRow('Qualità', cStepper({label: 'Scena', values: META_Q, i: Math.max(0, META_Q.indexOf(S.quality || 'auto')), fmt: v => META_QN[v], onChange: v => {
      metaSave(s => { s.quality = v; });
      layersQuality(v === 'auto' ? LY.autoQuality({cores: navigator.hardwareConcurrency, mem: navigator.deviceMemory}) : v);
    }}), 'Bassa: scena ferma, più fluida sui telefoni lenti'),
      metaRow('Contatore', cBtn({label: 'FPS: ' + (MN.fps.on ? 'Sì' : 'No'), id: 'bFps', txId: 'fpsTx', act: () => mnFpsSet(!MN.fps.on, true)}), 'Fotogrammi al secondo, in basso al centro'));
  } else if (k === 2) { // Comandi: what each device does today; changing them comes later
    const g = uiEl('div', 'stCmd');
    g.appendChild(uiEl('div', 'stCmdH', '<span></span>' + META_DEVS.map(d => '<b>' + d + '</b>').join('')));
    for (const m of META_MOVES.filter(m => ['Pugno', 'Calcio', 'Speciale', 'Scatto', 'Guardia', 'Muoversi e saltare'].includes(m[0])))
      g.appendChild(uiEl('div', 'stCmdR', '<span>' + uiEsc(m[0]) + '</span>' + m.slice(1).map(x => '<i>' + uiEsc(x) + '</i>').join('')));
    body.append(g, uiEl('p', 'stInfo', 'Giocatore 2 in tastiera: frecce, tastierino 1 2 3, 4 Scatto, 5 Guardia. Spostare i tasti è in arrivo.'));
  } else {              // Lingua
    body.append(metaRow('Lingua', cBtn({label: 'Italiano', act: () => uiToast('Altre lingue in arrivo', 'soon')})),
      uiEl('p', 'stInfo', 'Altre lingue in arrivo.'));
  }
}

// --- U3, Profilo (spec §3, reference 03): Profilo | Statistiche | Classifica. Only true numbers from this device's save:
// the global ranking needs the online (it says so, with no invented names) and meanwhile shows the player's own record.
const META_AV = ['ren', 'kael'];
const metaAvatar = () => (SV && META_AV.includes(SV.avatar) ? SV.avatar : (SV && SV.lastChar) || 'ren');
function metaPct(st) { return st.played ? Math.round(100 * st.won / st.played) + '%' : '—'; }
function metaTime(s) { s = Math.max(0, Math.round(s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s / 60) % 60; return h ? h + ' h ' + m + ' min' : m ? m + ' min ' + (s % 60) + ' s' : s + ' s'; }
function metaStat(label, value) { return uiEl('div', 'pfStat', '<span>' + uiEsc(label) + '</span><b>' + uiEsc(String(value)) + '</b>'); }
function metaProfileTab(body, k) {
  const st = SV ? SV.stats : {played: 0, won: 0, lost: 0, draw: 0, rounds: 0, hits: 0, maxCombo: 0, timeS: 0, byChar: {}};
  const L = progLevel(SV ? SV.xp : 0);
  if (k === 0) {
    const card = uiEl('div', 'pfCard', '<i class="pfFace" style="background-image:url(' + uiFace(metaAvatar()) + ')"></i><div class="pfWho"><b class="pfName">' +
      uiEsc((SV && SV.name) || 'Giocatore') + '</b><span class="pfLvl">Livello ' + L.lvl + '</span></div>');
    const bar = cProgress(L.into / L.need); bar.classList.add('pfBar');
    card.querySelector('.pfWho').append(bar, uiEl('span', 'pfXp', L.into + ' / ' + L.need + ' XP al livello ' + (L.lvl + 1)));
    const acts = uiEl('div', 'pfActs');
    acts.append(cStepper({label: 'Ritratto', values: META_AV, i: Math.max(0, META_AV.indexOf(metaAvatar())), fmt: v => CFG.ui.chars[v].name, onChange: v => {
      if (SV) { SV.avatar = v; saveWrite(); } card.querySelector('.pfFace').style.backgroundImage = 'url(' + uiFace(v) + ')'; }}),
      cBtn({label: 'Cambia nome', act0: 'name', act: () => navGo('name', {from: 'profile'})}));
    const stats = uiEl('div', 'pfStats');
    stats.append(metaStat('Vittorie', st.won), metaStat('Sconfitte', st.lost), metaStat('Pareggi', st.draw), metaStat('Percentuale vittorie', metaPct(st)));
    body.append(card, acts, stats);
  } else if (k === 1) {
    const tot = uiEl('div', 'pfStats pfWide');
    tot.append(metaStat('Incontri', st.played), metaStat('Vittorie', st.won), metaStat('Round vinti', st.rounds), metaStat('Colpi a segno', st.hits),
      metaStat('Combo massima', st.maxCombo), metaStat('Tempo di gioco', metaTime(st.timeS)));
    const per = uiEl('div', 'pfPer');
    for (const c of META_AV) {
      const b = (st.byChar || {})[c] || {played: 0, won: 0};
      per.appendChild(uiEl('div', 'pfPerRow', '<i class="pfMini" style="background-image:url(' + uiFace(c) + ')"></i><b>' + uiEsc(CFG.ui.chars[c].name) + '</b><span>' +
        b.played + ' incontri</span><span>' + b.won + ' vittorie</span><span>' + metaPct(b) + '</span>'));
    }
    body.append(tot, per, uiEl('p', 'stInfo', 'Contano le partite del Giocatore 1 in Versus; l\'allenamento non conta.'));
  } else {
    body.append(uiEl('div', 'pfRank', UI_ICON.soon + '<span>La classifica globale arriva con le partite online.</span>'));
    const own = uiEl('div', 'pfStats');
    own.append(metaStat('Il tuo livello', L.lvl), metaStat('XP totali', SV ? SV.xp : 0), metaStat('Combo massima', st.maxCombo), metaStat('Vittorie', st.won));
    body.append(uiEl('b', 'pfSub', 'Il tuo record'), own);
  }
}
function metaProfileScreen() {
  navRegister({id: 'profile', scene: 'menu', layers: () => ({hero: metaAvatar()}),
    build(r) {
      r.appendChild(cBack());
      const top = uiEl('div', 'mtTop');
      top.appendChild(cHead('Profilo'));
      const body = uiEl('div', 'mtBody pfBody');
      const tabs = cTabs(['Profilo', 'Statistiche', 'Classifica'], 0, k => { this.tab = k; body.innerHTML = ''; metaProfileTab(body, k); });
      tabs.classList.add('mtTabs');
      top.appendChild(tabs);
      r.append(top, body);
      this.tabs = tabs;
    },
    enter(p, back) { if (!back) metaTabStart(this.tabs, (p && p.tab) || 0); else this.tabs.children[this.tab || 0].uiAct(); }});   // back from the name: the new name shown
}
