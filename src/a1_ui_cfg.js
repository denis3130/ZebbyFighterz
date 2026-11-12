// Interface numbers (menus, intro, selection, VS, results) and progression (XP, levels). Part of CFG like every other
// number of the game; kept in their own file so the interface work does not collide with a0_cfg.js.
Object.assign(CFG, {
  ui: {
    t: {go: 420, stagger: 40, toast: 2400, bump: 220, tapGuard: 350},   // ms: screen change, cascade step, toast, counter bump, pointer confirms ignored after a screen change
    repeat: [350, 130],                                                   // controller direction held in the menus: ms before the first repeat, then between repeats
    intro: {len: 5200, firstSkipAfter: 0,                                 // the opening sequence lasts 5.2 s; «Salta» is there from the start
      // the clash panel (tools/make_ui_assets.py prints these): width / height, the point where the fists meet, the box of
      // each half in it (fractions), the charged fists (Ren's is hidden behind Kael's in the picture: his glow covers it);
      // on screen the panel is panelH of the screen's height, the hit at hitY of the height, centred
      aspect: 2.0291, hit: [.5353, .6038], ren: [.0006, .1396, .5263, .9994], kael: [.5215, .2409, .9997, .9703],
      fist: {ren: [.522, .604], kael: [.549, .61]}, panelH: 1.1, hitY: .55},
    vs: {minMs: 2500, tapAfterMs: 600},                                   // the VS screen stays at least this long; a tap skips it after tapAfterMs once loaded
    par: {sky: .12, ruins: .35, fog: .6, hero: 1, step: 28},             // parallax: share of the shift per layer, px per navigation step
    q: {lowCores: 4, lowMem: 3, parts: {bassa: 0, media: 36, alta: 80}},  // quality 'auto': media at or below these cores / GB, else alta; particles per quality
    name: {min: 3, max: 16, re: '^[A-Za-z0-9À-ÖØ-öø-ÿ _-]+$', pool: ['Lama', 'Brace', 'Vento', 'Corvo', 'Ombra', 'Falco', 'Tuono', 'Cenere']},
    chars: {
      ren:    {name: 'Ren',    pot: 4, vel: 3, dif: 2, hue: '#2f8f86'},
      kael:   {name: 'Kael',   pot: 3, vel: 4, dif: 3, hue: '#8f6ad8'},
      astra:  {name: 'Astra',  lock: 'Pass gratuito · livello 50'},
      raigon: {name: 'Raigon', lock: 'Pass Premium · livello 50'},
    },
    roster: ['ren', 'kael', 'astra', 'raigon', null, null, null, null, null, null, null, null],   // null = a coming fighter («In arrivo»)
    arenas: [{id: 'cascata', name: 'La Grande Cascata', ok: true}, {id: 'rovine', name: "Rovine dell'acquedotto"},
             {id: 'montagne', name: 'Montagne'}, {id: 'tetti', name: 'Tetti della città'}, {id: 'foresta', name: 'Foresta'}, {id: 'deserto', name: 'Deserto'}],
    lines: {'ren>kael': ['Non mi tirerò indietro.', 'Allora dimostralo.'], 'kael>ren': ['Sei ancora in piedi?', 'Abbastanza per batterti.']},
    vsOpts: {rounds: [1, 3, 5], r: 1, time: [60, 90, 99, 0], tm: 2},   // indexes of the starting values (3 rounds, 99 s); time 0 = no timer (∞)
  },
  prog: {xp: {played: 60, win: 40, round: 10}, levelXp: 1000},   // XP per match played, per win, per round won; XP per profile level
});
