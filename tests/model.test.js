// The Meshy Ren (Tappa 2a): the packed model in ASSETS, the skinned toon fighter on side 0, its animations driven by the sim.
T.test('the Ren package is in ASSETS', () => { const m=__VF.ASSETS['ren/ren.json'];
  T.ok(m&&m.v===1); T.eq(m.bones.length,24); T.eq(Object.keys(m.clips).length,25); T.ok(m.mesh.verts>20000&&m.mesh.tris===29999);
  T.ok(typeof __VF.ASSETS['ren/ren.bin']==='string'); T.ok(__VF.ASSETS['ren/ren.jpg'].startsWith('data:image/jpeg'));
  T.near(m.height,1.8,.08); T.eq(m.bones[0].n,'Hips'); });
T.test('side 0 is the Meshy Ren, toon with a skinned outline', () => { const it=__VF.F3D[0]; T.eq(it.kind,'model');
  T.ok(it.mesh.isSkinnedMesh&&it.mesh.material.isMeshToonMaterial&&it.mesh.material.skinning&&it.mesh.material.map);
  T.ok(it.outline.isSkinnedMesh&&it.outline.material.side===THREE.BackSide&&it.outline.material.skinning); T.eq(__VF.F3D[1].kind,undefined); });
T.test('the model follows the sim and hides on the title', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); F(S,0).x=-900; F(S,0).y=200; __VF.renderFrame(S,0);
  const r=__VF.F3D[0].root; T.ok(r.visible); T.near(r.position.x,-.9,1e-9); T.near(r.position.y,.2,1e-9); __VF.renderFrame(null,0); T.ok(!r.visible); });
T.test('model draws before its texture is ready', () => { const it=__VF.F3D[0], img=it.mesh.material.map.image; const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0); T.ok(img!==undefined); });
T.test('missing model falls back to the placeholder', () => { const a=__VF.ASSETS, j=a['ren/ren.json']; delete a['ren/ren.json']; try { T.eq(__VF.modelBuild('ren'),null); T.eq(__VF.mdData('nobody'),null); } finally { a['ren/ren.json']=j; } });
T.test('idle feet on the floor, head at standing height', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}); __VF.renderFrame(S,0);
  for(const l of ['footL','footR']) T.near(__VF.limbWorld(0,l).y,.06,.05,l); T.near(__VF.headTop(0),1.8,.12); });
T.test('a hit flashes the model', () => { const it=__VF.F3D[0]; T.ok(it.mats.main.emissive&&Object.keys(it.mats).length===1); });
