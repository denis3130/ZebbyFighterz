# Voidrise Fighters · Tappa 2a "Ren di Meshy in gioco" · Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** il lato 0 (Ren) usa il modello Meshy con scheletro e le 25 animazioni Meshy al posto del lottatore provvisorio; Kael resta provvisorio. Il colpo si vede nel fotogramma in cui la logica colpisce.

**Architecture:** uno strumento Python (`tools/meshy_pack.py`) impacchetta il modello con scheletro e le animazioni in `assets/ren/` (metadati JSON, un binario, la texture JPG); `build.py` li incorpora in `ASSETS`, così `index.html` resta un solo file e funziona offline. Un nuovo modulo grafico (`src/e_model.js`) decodifica il pacchetto in modo sincrono, costruisce uno `SkinnedMesh` toon con contorno e calcola la posa con una funzione pura dello stato (`mdPoseOf(F, S)`), campionando le clip a 30 fps: niente `AnimationMixer`, niente tempo reale. La logica non cambia.

**Tech Stack:** Three.js r128 (`SkinnedMesh`, `Skeleton`, `MeshToonMaterial` con `skinning: true`), JavaScript vanilla, Python 3 + numpy + Pillow per l'impacchettamento, Playwright per i test.

**Spec:** `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md` (tappa 2: "I 2 personaggi Meshy (Ren e Kael) con animazioni e mosse proprie"; architettura: "Sostituire i lottatori provvisori con i modelli Meshy non tocca la logica"). Questa è la prima metà della tappa 2: solo Ren, con la tabella di mosse comune.

## Global Constraints

- "La grafica legge lo stato della logica e lo disegna … Non cambia mai lo stato." La posa è funzione pura di `F` e `S` (più la memoria dell'ultimo disegno per l'ammorbidimento, come in `f3Sync`).
- I file `c*_*.js` non si toccano.
- Nessuna libreria in più: niente `GLTFLoader`, niente CDN nuovi. Il gioco deve restare un solo `index.html` e l'app `play/` deve funzionare offline.
- Numeri della grafica in `CFG` (`src/a0_cfg.js`): la tabella delle clip va in `CFG.clips`.
- "Gli effetti non allungano le lotte" e "obiettivo 60 [FPS] su telefono di fascia media": si misura prima e dopo (`tests/perf.test.js`).
- "Prima di pubblicare: tutti i test verdi e nessun errore nella console."
- Ogni funzione va su touch, mouse e tastiera, e controller (qui non cambia nulla dei comandi).
- Meshy: niente nuove spese senza saldo, costo e ok di Denis. Questa tappa non ne prevede.

## Review Focus

1. La texture (data URI) non è ancora decodificata nei primi fotogrammi. Atteso: il modello si disegna lo stesso, nessun errore in console. Test in Task 2 `model draws before its texture is ready`.
2. `ASSETS` senza il pacchetto di Ren (build vecchia o file mancante). Atteso: il lato 0 torna al lottatore provvisorio, il gioco parte. Test in Task 2 `missing model falls back to the placeholder`.
3. Un `act` che la tabella non conosce. Atteso: la posa di guardia, nessun errore. Test in Task 3 `unknown act draws the idle pose`.
4. Hitstop lungo o fotogrammi saltati (telefono lento). Atteso: la posa dipende solo dallo stato, non dal tempo reale. Test in Task 3 `pose is a pure function of the state`.
5. Ren girato a sinistra (lato destro dello schermo). Atteso: il colpo sta nella sua hitbox anche così. Test in Task 3 `every limb is inside its hitbox on every active frame, both facings`.

---

## Mappa dei file

| File | Responsabilità | Task |
|---|---|---|
| `tools/meshy_pack.py` | GLB con scheletro + GLB delle animazioni → `assets/ren/ren.json`, `ren.bin`, `ren.jpg` | 1 |
| `tools/mesh_prep/` (`glbio.py`, `decimate_glb.py`, `lift_bangs.py`) | preparazione del modello prima dello scheletro (30k triangoli, frangia), già usati | 1 |
| `build.py` | incorpora anche `.json` (oggetto) e `.bin` (base64) di `assets/` | 1 |
| `assets/ren/` | il pacchetto di Ren (nel repository) | 1 |
| `src/e_model.js` | decodifica, `SkinnedMesh` toon con contorno, punti dei colpi, campionamento e miscela delle pose, `mdSync` | 2, 3 |
| `src/a0_cfg.js` | `CFG.clips`: per ogni `act` la clip e i tempi | 3 |
| `src/d_render.js`, `src/e_fighter3d.js` | lato 0 = modello Meshy se c'è; `f3Sync` passa i modelli a `mdSync` | 2 |
| `mk.sh` | `e_model.js` in `FILES` dopo `e_fighter3d.js` | 2 |
| `tests/model.test.js` | test del modello Meshy | 1, 2, 3 |
| `tests/fighter3d.test.js` | i test del provvisorio passano al lato 1 (Kael) | 2 |
| `tools/pose_sheet.py` | foglio di controllo: ogni `act` a più fotogrammi in un PNG | 4 |
| `docs/meshy/REN.md`, `docs/HANDOFF.md`, registro | task Meshy, crediti, comandi, stato | 4 |

## Il pacchetto (formato)

`ren.json`:
```
{v:1, height, bones:[{n, p (indice del padre, -1), t:[x,y,z] m, q:[x,y,z,w]}],
 mesh:{verts, tris, pos, nor, uv, jnt, wgt, idx},          // ognuno [offset in byte, lunghezza in elementi]
 clips:{a89:{name, n (fotogrammi), fps:30, q, h}, …},      // q: n × bones × 4 float32; h: n × 3 float32 (Hips)
 limbs:{handL:{b:'LeftHand', p:[x,y,z]}, handR, footL, footR}, head:'head_end'}
```
`ren.bin`: little-endian; `pos`, `nor` float32×3, `uv` float32×2, `jnt` uint8×4, `wgt` float32×4, `idx` uint16 (uint32 se più di 65535 vertici), poi le clip. Spazio: metri, y in alto, piedi a y=0, davanti +z, Hips centrato in x/z (lo stesso spostamento vale per la traslazione di Hips nelle clip). La scala 0.01 dell'Armature di Meshy è già applicata.

---

### Task 1: Impacchettare Ren

**Files:**
- Create: `tools/meshy_pack.py`, `tools/mesh_prep/glbio.py`, `tools/mesh_prep/decimate_glb.py`, `tools/mesh_prep/lift_bangs.py`, `assets/ren/ren.json`, `assets/ren/ren.bin`, `assets/ren/ren.jpg`, `tests/model.test.js`
- Modify: `build.py` (`assets()`)

**Interfaces:**
- Produces: `ASSETS['ren/ren.json']` (oggetto, formato sopra), `ASSETS['ren/ren.bin']` (stringa base64), `ASSETS['ren/ren.jpg']` (data URI). Clip: gli id Meshy con la `a` davanti (`a3 a7 a8 a16 a17 a20 a21 a54 a89 a138 a174 a191 a192 a193 a194 a207 a209 a210 a214 a215 a217 a421 a422 a457 a466`).

- [ ] **Step 1: test** — `tests/model.test.js`:
```js
T.test('the Ren package is in ASSETS', () => { const m=__VF.ASSETS['ren/ren.json'];
  T.ok(m&&m.v===1); T.eq(m.bones.length,24); T.eq(Object.keys(m.clips).length,25); T.ok(m.mesh.verts>20000&&m.mesh.tris===29999);
  T.ok(typeof __VF.ASSETS['ren/ren.bin']==='string'); T.ok(__VF.ASSETS['ren/ren.jpg'].startsWith('data:image/jpeg'));
  T.near(m.height,1.8,.08); T.eq(m.bones[0].n,'Hips'); });
```
- [ ] **Step 2: verifica** — `bash mk.sh && python3 tests/run.py tests/model.test.js` → FAIL (`m` undefined).
- [ ] **Step 3: `tools/meshy_pack.py RIG_GLB ANIM_DIR OUT_DIR`**
  - Ossa = i joint della skin nell'ordine della skin; padri dal grafo dei nodi; `t`, `q` locali in metri (la scala dell'Armature moltiplicata nelle traslazioni). Vertici: posizioni della skin (già nello spazio della scena), poi lo spostamento comune (piedi a 0, Hips a x=z=0).
  - `jnt` riportati all'ordine delle ossa; pesi normalizzati a somma 1.
  - Normali della testa: per i vertici con peso su `Head` ≥ 0,5, normale = normalize(lerp(normale, direzione dal centro della testa, 0,85)), centro = media di quei vertici (faccia pulita nel toon, come provato il 7/11).
  - Clip: per ogni `a<ID>.glb` le rotazioni di tutte le ossa animate (le altre: quella di riposo) e la traslazione di Hips in metri con lo stesso spostamento; tutte le clip sono già a 30 fps lineari (verificato: le altre traslazioni e le scale sono costanti).
  - `limbs`: centro dei vertici con peso ≥ 0,6 su `LeftHand`/`RightHand` (pugni) e su `LeftFoot`+`LeftToeBase` / `RightFoot`+`RightToeBase` (piedi), nello spazio locale dell'osso (`LeftHand`, `RightHand`, `LeftFoot`, `RightFoot`).
  - Texture: l'immagine del GLB, 2048 px, JPEG qualità 85.
  - Lancio: `python3 tools/meshy_pack.py meshy/meshy_output/20261107_104314_voidrise-ren-v2_01a1b59a/rigged.glb meshy/meshy_output/20261107_104314_voidrise-ren-v2_01a1b59a/anims assets/ren`
- [ ] **Step 4: `build.py`** — `.json` entra come oggetto (`json.load`), `.bin` come stringa base64 senza prefisso; jpg/png come prima.
- [ ] **Step 5: verifica** — `bash mk.sh` stampa `SYNTAX_OK`; `model` → PASS; `smoke`, `render` → PASS; `python3 tests/play_check.py` → 0 failed. Annota la dimensione di `index.html`.
- [ ] **Step 6: commit** — `git add tools/meshy_pack.py tools/mesh_prep assets/ren build.py tests/model.test.js && git commit -m "Tappa 2a: pacchetto del modello Meshy di Ren"`

### Task 2: Ren di Meshy sul lato 0

**Files:**
- Create: `src/e_model.js`
- Modify: `src/d_render.js:247-251`, `src/e_fighter3d.js` (`f3Sync`), `src/z_main.js` (`__VF`: `modelBuild`, `mdData`, `mdPoseOf`, `headTop`), `mk.sh`, `tests/fighter3d.test.js`, `tests/model.test.js`

**Interfaces:**
- Consumes: `ASSETS` (Task 1), `F3`, `f3Shared()`, `F3_YAW`, `F3_OUTLINE`, `F3_EASE` (`e_fighter3d.js`), `rdTexture(key)` (`d_render.js`).
- Produces:
  - `mdData(key) -> {meta, nb, bones:[{n,p,t,q}], geo: THREE.BufferGeometry, clips:{id:{n, q: Float32Array, h: Float32Array}}} | null` (memorizzato; `null` se manca il pacchetto).
  - `modelBuild(key) -> item | null`, item = `{kind:'model', key, root, body, bones:[THREE.Bone], mesh, outline, joints:{pelvis, chest, neck, head}, limbs:{handL, handR, footL, footR}, mats:{main}}`. `root` come nel provvisorio (piedi a terra, davanti +z); `body` = scala `CFG.body.h/1000/meta.height`.
  - Posa: `{q: Float32Array(nb*4), h: Float32Array(3)}`; `mdApply(it, pose)` la mette sulle ossa.
  - `mdSync(it, side, S)`: come `f3Sync` per un lato (visibile, posizione, `rotation.y = face * F3_YAW`, ammorbidimento dei cambi verso gli `act` di `F3_EASE` in `CFG.anim.blend` fotogrammi con `mdMix`).
  - `headTop(side) -> number` (m): y mondo della cima della testa (osso `head_end` per il modello, il vertice più alto della testa per il provvisorio).

- [ ] **Step 1: test** — in `tests/model.test.js`:
```js
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
```
  `mdData('nobody')` usa la chiave `nobody/nobody.json`, che non esiste.
- [ ] **Step 2: verifica** — FAIL (`kind` undefined).
- [ ] **Step 3: `src/e_model.js`**
  - `mdData`: base64 → `Uint8Array` (`atob`), viste tipizzate agli offset del JSON; `BufferGeometry` con `position`, `normal`, `uv`, `skinIndex` (Uint8 → `Uint16BufferAttribute` o `Float32`), `skinWeight`, indice.
  - `modelBuild`: ossa `THREE.Bone` dal JSON (posizione `t`, quaternione `q`), `SkinnedMesh` con `MeshToonMaterial({map: rdTexture('ren/ren.jpg'), gradientMap: F3.grad, skinning: true})`, contorno = secondo `SkinnedMesh` con la stessa geometria e lo stesso `Skeleton`, `MeshBasicMaterial({color: F3_OUTLINE.color, side: THREE.BackSide, skinning: true})` con `onBeforeCompile` che dopo `#include <begin_vertex>` aggiunge `transformed += normal * uW;` (uW = 0,012 m / scala di `body`). `bind` con la radice all'origine. `frustumCulled = false` su entrambi. Punti dei colpi = `Object3D` figli delle ossa in `meta.limbs`. `joints` = Hips, Spine02, neck, Head.
  - `mdSync`/`mdApply` come sopra; finché il Task 3 non c'è, `mdPoseOf` restituisce la posa di riposo.
  - `rdFightersBuild`: lato 0 = `modelBuild('ren') || fighterBuild('ren')`; `f3Sync`: `if (it.kind === 'model') { mdSync(it, i, S); continue; }`.
  - `tests/fighter3d.test.js`: i test che controllano il provvisorio sul lato 0 (`feet touch the ground when idle`, `planted poses…`, `the walk never slides…`, `act changes ease in…`, `the eased pose settles…`, `a block with down held…`, `crouching moves keep the head down…`, `every limb is inside its hitbox on the active frames`, `facing left mirrors the limbs`, `fighters have an outline and toon shading`) passano al lato 1 (Kael provvisorio): `F(S,1)`, `limbWorld(1,…)`, `F3D[1]`, `joint(1,…)`, `headTop(1)`; con il lato 1 rivolto a destra dove il test lo vuole (`f.face=1`).
- [ ] **Step 4: verifica** — `model`, `fighter3d`, `render`, `feel`, `smoke` → PASS, console pulita.
- [ ] **Step 5: commit** — `git commit -am "Tappa 2a: Ren di Meshy sul lato 0, toon con contorno"` (più `git add src/e_model.js`).

### Task 3: Le animazioni seguono la logica

**Files:**
- Modify: `src/e_model.js` (`mdPoseOf`, `mdClipPose`, `mdMix`, `mdLayer`, tempi dei colpi), `src/a0_cfg.js` (`CFG.clips`), `tests/model.test.js`

**Interfaces:**
- Consumes: `mdData`, `modelBuild`, `mdApply` (Task 2), `CFG.moves`, `moveBox`, `hurtBoxes`.
- Produces: `mdPoseOf(F, S) -> pose` (pura), `mdClipPose(md, spec, t) -> pose`, `mdMix(a, b, k) -> pose`, `mdLayer(low, up) -> pose`, `it.hitT = {moveId: secondi}`.

- [ ] **Step 1: test** — in `tests/model.test.js` (`F`, `B` da `tests/lib.js`; `top = CFG.body.hCrouch/1000 + .1`):
```js
T.test('every limb is inside its hitbox on every active frame, both facings', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const face of [1,-1]) for(const [id,m] of Object.entries(__VF.CFG.moves)) for(let af=m.s+1;af<=m.s+m.a;af++){ Object.assign(f,{x:0,face,act:id,af,air:id[0]==='j',y:id[0]==='j'?900:0}); __VF.renderFrame(S,0);
    const p=__VF.limbWorld(0,m.limb), b=__VF.moveBox(f,id); T.ok(p.x*1000>=b.x0-100&&p.x*1000<=b.x1+100&&p.y*1000>=b.y0-100&&p.y*1000<=b.y1+100, id+' face '+face+' af '+af+' '+m.limb+' at '+[p.x.toFixed(2),p.y.toFixed(2)]); } });
T.test('planted poses keep both feet on the floor', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const [act,af] of [['idle',1],['idle',37],['guard',8],['crouch',8],['guardC',8],['jumpSquat',3],['block',4],['landing',2]]){ Object.assign(f,{act,af,land:5,stun:4}); S.frame=af*7; __VF.renderFrame(S,0);
    for(const l of ['footL','footR']) T.near(__VF.limbWorld(0,l).y,.06,.05, act+' '+l); } });
T.test('the walk barely slides', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), feet=()=>[__VF.limbWorld(0,'footL'),__VF.limbWorld(0,'footR')];
  for(const [act,face,dx] of [['walkF',1,__VF.CFG.walk.f],['walkB',-1,__VF.CFG.walk.b],['walkF',-1,-__VF.CFG.walk.f]]){ Object.assign(f,{act,af:10,x:0,face}); let n=0;
    for(let i=0;i<60;i++){ __VF.renderFrame(S,0); const a=feet(); f.x+=dx; f.af++; __VF.renderFrame(S,0); const b=feet();
      for(const k of [0,1]) if(a[k].y<.09&&b[k].y<.09){ n++; T.ok(a[k].distanceTo(b[k])<.02, act+' face '+face+' frame '+i+' slid '+a[k].distanceTo(b[k]).toFixed(3)); } }
    T.ok(n>20, act+' planted frames '+n); } });
T.test('act changes ease in', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), it=__VF.F3D[0];
  const pts=()=>[it.joints.head,it.joints.chest,it.limbs.footL,it.limbs.footR,it.limbs.handL,it.limbs.handR].map(o=>o.getWorldPosition(new THREE.Vector3()));
  for(const act of ['crouch','walkF','guardC','hitStun']){ Object.assign(f,{act,af:1,x:-1200,stun:act==='hitStun'?14:0}); for(let i=0;i<20;i++){ __VF.renderFrame(S,0); f.af++; if(act==='walkF') f.x+=__VF.CFG.walk.f; }
    __VF.renderFrame(S,0); let a=pts(), worst=0; Object.assign(f,{act:'idle',af:1});
    for(let i=0;i<12;i++){ __VF.renderFrame(S,0); const b=pts(); for(let k=0;k<a.length;k++) worst=Math.max(worst,a[k].distanceTo(b[k])); a=b; f.af++; }
    T.ok(worst<.15, act+' to idle: '+worst.toFixed(3)); } });
T.test('pose is a pure function of the state', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0);
  for(const act of ['idle','walkF','p2','hk','air','knock','getup']){ Object.assign(f,{act,af:5,x:300,vy:act==='air'?40:0,air:act==='air'}); const a=Array.from(__VF.mdPoseOf(f,S).q), b=Array.from(__VF.mdPoseOf(f,S).q); T.eq(JSON.stringify(a),JSON.stringify(b),act); } });
T.test('every act has its own pose', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), idle=JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q));
  const acts=['walkF','walkB','crouch','jumpSquat','air','dashF','dashB','guard','guardC','block','hitStun','juggle','knock','getup','rollF','rollB','thr','thrWhiff','thrown','landing','ko','win','spec'].concat(Object.keys(__VF.CFG.moves));
  for(const act of acts){ Object.assign(f,{act,af:3,x:400,air:act==='air'||act[0]==='j',vy:act==='air'?40:0,land:5,stun:8}); T.ok(JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q))!==idle, act); } });
T.test('unknown act draws the idle pose', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), idle=JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q));
  f.act='nonsense'; T.eq(JSON.stringify(Array.from(__VF.mdPoseOf(f,S).q)),idle); });
T.test('crouched acts keep the head down', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0), top=__VF.CFG.body.hCrouch/1000+.1;
  for(const [act,n] of [['crouch',20],['guardC',20],['cp',15],['ck',19]]) for(let af=1;af<=n;af++){ Object.assign(f,{act,af}); __VF.renderFrame(S,0); T.ok(__VF.headTop(0)<=top, act+' af '+af+' head '+__VF.headTop(0).toFixed(2)); }
  Object.assign(f,{act:'block',af:2,stun:8,prev:B.D|B.L}); __VF.renderFrame(S,0); T.ok(__VF.headTop(0)<=top,'crouching block'); });
T.test('facing left mirrors the limbs', () => { const S=__VF.simCreate({seed:1,mode:'versus',chars:['ren','kael']}), f=F(S,0); Object.assign(f,{x:0,face:-1,act:'p1',af:5}); __VF.renderFrame(S,0); T.ok(__VF.limbWorld(0,'handL').x<-.2); });
```
- [ ] **Step 2: verifica** — FAIL (posa di riposo).
- [ ] **Step 3: `CFG.clips`** (grafica; tempi in secondi della clip) e `mdPoseOf`:
  - Forme delle voci: `{c, loop:1}` (ciclo su `S.frame`, sfasato di 23 fotogrammi per il lato 1 quando avrà un modello); `{c, walk:1}` (tempo = distanza percorsa / velocità del piede appoggiato nella clip, calcolata al caricamento, divisa per sin 65° così il piede non scivola in x); `{c, at}` (posa ferma); `{c, t:[t0, t1]}` per le mosse (avvio: da `t0` a `hitT`, attivi: da `hitT` a `hitT + a/60`, recupero: fino a `t1`; nelle mosse in salto, con `r:'land'`, il recupero finisce a `t1` e lì resta fino all'atterraggio); `{low, up}` (gambe e bacino da una voce, busto, braccia e testa dall'altra). Opzioni: `root:'lunge'` (lo spostamento in avanti di Hips nella clip resta fino a `hitT` e poi torna a 0 entro `t1`; senza, x e z di Hips restano quelli del primo fotogramma); `y:'cap'` (y di Hips mai sopra quella di riposo: niente salto doppio quando la logica è in aria).
  - `hitT[id]`: al caricamento, per ogni mossa, il fotogramma della clip tra `t0` e `t1` in cui il punto del colpo (rivolto a destra, x=0) sta più dentro il box della mossa; a parità, il più avanti.
  - Tabella di partenza (da rifinire nel Task 4 guardando il foglio di controllo):
    - `idle`, `intro`: a89 ciclo. `walkF`: a21 walk. `walkB`: a20 walk. `dashF`: a16 walk (corsa). `dashB`: a20 walk.
    - `crouch`: low = a54 al fotogramma con Hips più basso, up = a89 ciclo. `guard`: a138 `at` 1.0. `guardC`: low del crouch + up a138 `at` 1.0. `block`: `guard`, o `guardC` con giù tenuto (`F.prev & BTN.D`).
    - `jumpSquat`: a466 da 0 alla spinta, `air`: a466 parte in volo secondo `F.vy` (salita → discesa), `landing`: a466 atterraggio; `y:'cap'`.
    - Mosse: `p1` a191, `p2` a192, `p3` a193, `hp` a210, `k1` a209, `k2` a215 (`lunge`), `hk` a207 (`lunge`), `cp` low crouch + up a192, `ck` a217, `chp` a194, `chk` a422 (`cap`), `jp`/`jhp` a457 (`cap`), `jk`/`jhk` a422 (`cap`).
    - `spec`: a214, la spinta delle mani nel fotogramma `CFG.spec.spawn`. `thr`: a421 (presa nei fotogrammi `s+a`, lancio a `CFG.thr.hitF`), `thrWhiff`: a421 presa e ritorno. `thrown`, `juggle`, `knock` in aria: a7 parte in volo (`cap`); a terra: a7 ultimo fotogramma; `ko`: a7. `getup`: a3 dalla seduta all'in piedi in `CFG.knock.getup` fotogrammi; `rollF`/`rollB`: a3 in `CFG.knock.roll`. `hitStun`: a174 dal colpo alla massima piega in 12 fotogrammi, poi fermo. `win`: a17 una volta, poi fermo sull'ultimo fotogramma.
    - `chp` e `chk` si alzano come anti-aerei: la regola della testa bassa vale per `crouch`, `guardC`, la parata bassa, `cp` e `ck` (deviazione dal provvisorio, da annotare nel registro).
  - `mdClipPose`: campiona `q` (slerp tra i due fotogrammi vicini) e `h`; `mdMix` = slerp per osso e lerp di Hips; `mdLayer`: `LOWER = {Hips, LeftUpLeg, LeftLeg, LeftFoot, LeftToeBase, RightUpLeg, RightLeg, RightFoot, RightToeBase}`.
  - Un `act` senza voce = `idle`.
- [ ] **Step 4: verifica** — `model` → PASS (se un colpo resta fuori dal suo box, prima si cambia `t0`/`t1` o la clip della voce; solo per ultimo il box in `CFG.moves`, annotandolo nel registro). Poi `fighter3d`, `render`, `feel`, `attack`, `guard`, `round`, `sim` → PASS.
- [ ] **Step 5: commit** — `git commit -am "Tappa 2a: le animazioni di Ren seguono la logica"`

### Task 4: Rifinitura, misure, pubblicazione

**Files:**
- Create: `tools/pose_sheet.py`, `docs/meshy/REN.md`, `docs/superpowers/plans/2026-11-07-voidrise-tappa2a-ren-meshy.ledger.md`
- Modify: `src/a0_cfg.js` (`CFG.clips`, se serve), `docs/HANDOFF.md`, `CLAUDE.md` (se cambia qualcosa del pubblicare)

- [ ] **Step 1: foglio di controllo** — `python3 tools/pose_sheet.py out.png`: per ogni `act` 4 fotogrammi (inizio, avvio, attivo, recupero) del lato 0 a 844×390, in una griglia con le scritte. Guardalo: pugni e calci si leggono, i piedi non affondano, la testa non sparisce. Ritocca `CFG.clips` e rilancia finché va.
- [ ] **Step 2: misure** — `tests/perf.test.js` prima (dal commit del Task 1) e dopo: ms per fotogramma di disegno e durata media del round (non deve cambiare: la logica è la stessa). Scrivi i valori in `docs/HANDOFF.md`.
- [ ] **Step 3: tutti i test** — i 17 comandi di `docs/HANDOFF.md` più `model` e `python3 tests/play_check.py` → tutti PASS, console pulita.
- [ ] **Step 4: documenti** — `docs/meshy/REN.md` (id dei task Meshy, crediti spesi, come rifare il pacchetto); registro della tappa; HANDOFF (stato, misure, "per dopo": capelli più a punte, rotolata vera, Kael Meshy).
- [ ] **Step 5: pubblica** — `bash mk.sh`, Artifact con `index.html` sulla pagina "Voidrise Fighters", commit, `git push origin tappa1-basi` e `git push origin tappa1-basi:gh-pages` per l'app.
- [ ] **Step 6: commit** — `git commit -am "Tappa 2a: rifinitura, misure e documenti"`
