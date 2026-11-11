// --- extra.js: more animations in the viewer. ---
// 1. Two move proposals made from Meshy clips of Ren's package that the game does not use yet (frame data and boxes
//    are placeholders for the preview, to be balanced if Denis keeps them):
//    rk "Calcio rotante" (a207 Roundhouse_Kick: a jumping spin kick; the clip's own feet, it leaves the floor),
//    sw "Spazzata" (a217 Sweeping_Kick: a low spinning kick with the hands on the floor; the left foot stays planted).
// 2. A KO fall (a8 Dead), with the hips' own travel put back (he falls where he stands instead of sliding).
// 3. Plays of moves the game already has but the viewer did not show: the attacks in the air, combos, the victory pose.
CFG.moves.rk = {s: 13, a: 3, r: 22, dmg: 110, bs: 16, h: 'mid', box: [600, 1150, 1100, 1700], stop: 'heavy', limb: 'footR', knock: true, vx: 70, vy: 70};
CFG.moves.sw = {s: 11, a: 3, r: 20, dmg: 90, bs: 15, h: 'low', box: [600, 1150, 600, 1050], stop: 'heavy', limb: 'footR', knock: true, vx: 50, vy: 60};
CFG.clips.rk = {c: 'a207', t: [.95, 1.85]};
CFG.clips.sw = {c: 'a217', t: [.85, 1.9]};
CFG.clips.dead = {c: 'a8', k: [[0, .05], [150, 2.9]], travel: 1};
RB.moves.rk = {hip: 3, chest: -3, coil: .5, lean: 0, dip: .01, rise: 0, back: 0, fwd: 0, smear: .4};
RB.moves.sw = {hip: 3, chest: -3, coil: .5, lean: 0, dip: .005, rise: 0, back: 0, fwd: 0, smear: .4};
RB.keep.rk = 1;
Object.assign(VW_NAMES, {jp: 'Pugno in volo', jhp: 'Pugno forte in volo', jhk: 'Calcio forte in volo', rk: 'Calcio rotante', sw: 'Spazzata', win: 'Vittoria', dead: 'KO'});
{
  const J = [['jumpSquat', CFG.jump.squat]], land = [['landing', CFG.jump.landAtk + 6]], air = id => J.concat([[id, 0, 'jumpAtk']], land);
  VW_PLAYS.push(
    ['In aria', air('jp').concat(air('jhp'), air('jhk'))],
    // (a combo: each move cut where the next one cancels it, a few frames after it has hit)
    ['Combo', [['p1', 9], ['p2', 11], ['p3', 13], 'hp', ['idle', 45], ['k1', 12], ['k2', 14], 'hk', ['idle', 55]]],
    ['Calcio rotante', ['rk', ['idle', 45]]],
    ['Spazzata', ['sw', ['idle', 45]]],
    ['Vittoria', [['idle', 30], ['win', 110]]],
    ['KO', [['hitStun', 12], ['dead', 240]]]);
}
RN.hooks.boot.push(() => VW_PLAYS.forEach(([label], i) => { if (['In aria', 'Combo', 'Calcio rotante', 'Spazzata'].includes(label)) RX.plays[i] = 1; }));

// A clip entry with travel: the hips move over the floor as the clip's own do since its first pose.
{
  const pure = RN.pure;
  RN.pure = function (md, F, S) {
    const p = pure(md, F, S), e = CFG.clips[F.act];
    if (e && e.travel && e.k) {
      const a = mdSample(md, e.c, e.k[0][1], false).h, b = mdSample(md, e.c, mdKey(e.k, F.af), false).h;
      p.h[0] += b[0] - a[0]; p.h[2] += b[2] - a[2];
    }
    return p;
  };
}
// The camera goes with a body that travels (the KO's fall), a little wider.
RN.hooks.draw.push(VW => {
  const e = CFG.clips[VW.F.act];
  if (!e || !e.travel) return;
  VW.it.root.updateMatrixWorld(true);
  VW.aimX += .75 * VW.it.bones[0].getWorldPosition(new THREE.Vector3()).x; VW.wide = Math.max(VW.wide, 1.2);
});
