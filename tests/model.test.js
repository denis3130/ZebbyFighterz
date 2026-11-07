// The Meshy Ren (Tappa 2a): the packed model in ASSETS, the skinned toon fighter on side 0, its animations driven by the sim.
T.test('the Ren package is in ASSETS', () => { const m=__VF.ASSETS['ren/ren.json'];
  T.ok(m&&m.v===1); T.eq(m.bones.length,24); T.eq(Object.keys(m.clips).length,25); T.ok(m.mesh.verts>20000&&m.mesh.tris===29999);
  T.ok(typeof __VF.ASSETS['ren/ren.bin']==='string'); T.ok(__VF.ASSETS['ren/ren.jpg'].startsWith('data:image/jpeg'));
  T.near(m.height,1.8,.08); T.eq(m.bones[0].n,'Hips'); });
