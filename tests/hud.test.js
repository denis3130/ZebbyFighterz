// HUD (Task 10): bars, red chip, timer, round pips, combo counter, energy, banners, portraits, layout.
T.test('health bar follows hp', () => { startFight(); F(__VF.G.S,1).hp=500; __VF.hudUpdate(__VF.G.S); T.near(barScale('hpFill1'),.5,.01); });
T.test('chip waits for the combo to end, then drains', () => { comboG(1); __VF.hudUpdate(__VF.G.S); T.near(barScale('hpChip1'),1,.01); __VF.frame(70); T.ok(barScale('hpChip1')<1); __VF.frame(120); T.near(barScale('hpChip1'),barScale('hpFill1'),.01); });
T.test('combo counter shows from 2 hits and bumps once per hit', () => { comboG(2); T.eq(txt('combo0').trim().startsWith('2'),true); T.ok($('combo0').classList.contains('bump')); });
// brief had frame(80): after the 2nd hit the defender stays in hitstun ~25 frames (hitstop + stun), so 60 more frames end at ~85 > 80. Wait 100 and also check it is still shown at 30.
T.test('combo counter hides 60 frames after the combo', () => { comboG(2); __VF.frame(30); T.ok(vis('combo0')); __VF.frame(70); T.ok(!vis('combo0')); });
T.test('timer shows seconds, ∞ in training', () => { startFight(); T.eq(txt('timer'),'99'); __VF.startMatch('training',{seed:1,dummy:'fermo'}); __VF.frame(110); T.eq(txt('timer'),'∞'); });
T.test('round banners', () => { __VF.startMatch('versus',{seed:1}); __VF.frame(2); T.eq(txt('banner'),'ROUND 1'); __VF.frame(99); T.eq(txt('banner'),'COMBATTI!'); });
T.test('portraits and names', () => { T.eq(txt('name0'),'REN'); T.eq(txt('name1'),'KAEL'); T.ok($('face0').style.backgroundImage.includes('data:image/jpeg')); });
T.test('HUD fits a 360 px tall screen and does not cover the fighters', () => { const t=$('timer').getBoundingClientRect(); T.ok(t.bottom < innerHeight*.25); for(const id of ['meter0','meter1']) T.ok($(id).getBoundingClientRect().bottom<=innerHeight); });
T.test('energy shows the level and fills the current segment', () => { startFight(); const S=__VF.G.S; F(S,0).meter=1500; __VF.hudUpdate(S); T.eq(txt('lvl0'),'1'); const b=[...$('meter0').querySelectorAll('b')].map(e=>new DOMMatrix(getComputedStyle(e).transform).a); T.near(b[0],1,.01); T.near(b[1],.5,.01); T.near(b[2],0,.01); });
T.test('round pips light up with the rounds won', () => { startFight(); const S=__VF.G.S; S.wins[1]=1; __VF.hudUpdate(S); T.eq($('wins1').querySelectorAll('.on').length,1); T.eq($('wins0').querySelectorAll('.on').length,0); });
T.test('banners: K.O., TEMPO!, winner', () => { startFight(); const S=__VF.G.S; F(S,1).hp=1; F(S,0).hp=1000; nearG(); __VF.IN.override[0]=B.P; for(let i=0;i<60&&S.phase==='fight';i++) __VF.frame(1); __VF.IN.override[0]=null; T.eq(S.phase,'ko'); T.eq(txt('banner'),'K.O.');
  startFight(); const S2=__VF.G.S; S2.timer=2; __VF.frame(3); T.eq(txt('banner'),'TEMPO!');
  startFight(); const S3=__VF.G.S; S3.phase='end'; S3.winner=1; __VF.hudUpdate(S3); T.eq(txt('banner'),'VINCE KAEL!'); S3.winner=2; __VF.hudUpdate(S3); T.eq(txt('banner'),'PAREGGIO'); });
