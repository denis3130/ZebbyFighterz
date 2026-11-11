# Arene 3D, tappa A1 "La Grande Cascata in 3D" · Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** sostituire il fondale piatto della Cascata con un'arena 3D mista (terrazza, colonna con stendardo, lanterna in 3D; cielo, rupi con la cascata e nebbia come strati dipinti a distanze diverse), senza toccare la logica.

**Architecture:** nuovo modulo `src/d_arena.js` (solo grafica) che costruisce l'arena da `CFG.arenas.cascata` e la anima ogni fotogramma disegnato; `d_render.js` perde il fondale piatto e chiama `arenaBuild`/`arenaStep`. Gli strati lontani escono da `tools/make_layers.py` (Pillow + numpy) e stanno in `assets/arena/`.

**Tech Stack:** Three.js r128, JavaScript vanilla, Python 3 + Pillow + numpy, test Playwright esistenti (`tests/run.py`).

**Spec:** `docs/superpowers/specs/2026-11-11-voidrise-arene3d-cascata-design.md`

## Global Constraints

- Nessun file `src/c*_*.js` cambia; `simHash` identico con l'arena.
- Tutti i numeri dell'arena in `CFG.arenas.cascata` (`src/a0_cfg.js`); `CFG.arenaOn = 'cascata'`.
- Arena intera: al massimo 25 disegni e 25.000 triangoli (`ARENA.stats()`); texture al massimo 2048 px di lato; strati in tutto al massimo 700 KB.
- Generatore della sola grafica con seme (come `rdRand`), niente `Math.random`: lo stesso fotogramma si disegna sempre uguale.
- Costo in grafica software (844×390, metodo della Tappa 2a): al massimo +3 ms per fotogramma.
- Testi per Denis in italiano. `cascata.jpg` resta (lo usa `v_viewer.js`).
- Test con `VF_CHROME=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome` in questo ambiente.

## Review Focus

1. Schermo molto largo (21:9) o quasi quadrato (4:3) alla massima distanza con `cam.x` = ±3 e il tremolio: atteso nessun bordo degli strati visibile. Test in Task 2 `no holes at the camera extremes` (4 viewport).
2. Lottatore al muro (x = ±6 m) mentre la telecamera è al limite: atteso piedi sulle lastre, colonna e lanterna non coprono i lottatori. Test in Task 3 `slabs top is y=0 under every fighter x` e Task 4 `props stay out of the fighters' lane`.
3. Partita lunga (stendardo e nuvole dopo molti minuti): atteso numeri finiti, nessuna deriva. Test in Task 4 `banner stays finite after 10 minutes`.
4. Ridimensionamento o rotazione durante la lotta: atteso suolo ancora all'86%, nessun buco. Test in Task 2 `resize keeps the ground at 86%`.
5. Telefono WebGL1: texture non potenza di 2 senza mipmap. Atteso: nessun errore in console. Coperto da `run.py` (fallisce sugli errori) più il controllo `minFilter` in Task 2.

---

### Task 1: Strati dal disegno

**Files:** Create `tools/make_layers.py`, `assets/arena/cascata_sky.jpg`, `assets/arena/cascata_cliffs.jpg`, `assets/arena/cascata_cliffs_a.png`, `assets/arena/cascata_water.png`, `assets/arena/cascata_mist.png`.

**Produces:** strati allargati rispetto al disegno (25% per lato in larghezza; cielo +30% in alto; rupi +45% in basso, riempito con la nebbia); `tools/make_layers.py` stampa e scrive in `assets/arena/cascata_layers.json` il riquadro del disegno originale dentro ogni strato (`{sky:{u0,v0,u1,v1}, cliffs:{...}}`, v dal basso), che `CFG` copia.

- [ ] Cielo: per colonna, la linea del cielo = prima riga dall'alto con 6 pixel di fila non-cielo (cielo = blu `b>r+30 && b>g` oppure nuvola chiara poco satura); sulla cresta della cascata (x 672-1242) mai sotto la cima del poligono dell'acqua; mediana su 9 colonne. Sopra = cielo, sotto = rupi.
- [ ] Rupi: alfa 1 sotto la linea del cielo (bordo sfumato 1,5 px); zone da togliere (colonna e stendardo `x<330, y<725`; lanterna `1505..1640 × 520..725`; erba davanti `0..340 × 560..725` e `1360..1672 × 640..725`; pavimento `y≥725`) riempite con push-pull (media pesata dei vicini noti, piramide), poi sfocate 3 px. Sotto la riga 725 la nebbia si allunga verso il basso (media delle righe 690-720, schiarita verso il basso).
- [ ] Cielo: le zone delle rupi riempite con push-pull dal cielo; in alto un gradiente verso il blu della prima riga, un po' più scuro.
- [ ] Nebbia: texture 1024×256 con alfa da rumore morbido, colore medio delle righe 600-700 tra la cascata e le rupi.
- [ ] Acqua: il poligono di oggi (in `make_assets.py`) portato nelle coordinate dello strato delle rupi, sfocato.
- [ ] Larghezza finale: rupi 2048, cielo 1024; JPG qualità 82. Verifica: `python3 tools/make_layers.py && ls -l assets/arena/` (somma ≤ 700 KB) e guardo gli strati (linea del cielo pulita, niente colonna/lanterna).
- [ ] Commit.

### Task 2: Arena dagli strati, al posto del fondale piatto

**Files:** Create `src/d_arena.js`, `tests/arena.test.js`. Modify `src/d_render.js`, `src/a0_cfg.js`, `src/z_main.js` (`__VF.ARENA` resta, più `arenaStep`), `mk.sh` (`d_arena.js` dopo `d_render.js`), `tests/render.test.js`, `tests/feel.test.js`.

**Interfaces:**
- `arenaBuild(def) -> Promise` (aggiunge `ARENA.group` a `scene`), `arenaStep(nowMs, S)`.
- `ARENA = {group, layers:{sky, cliffs, mist}, banner:null, leaves, waterMat, stats() -> {draws, tris}}`.
- Piano di uno strato a profondità `z`: la sua parte "disegno originale" occupa nel mondo esattamente il riquadro che il fondale di oggi mostrava alla telecamera di partenza su 844×390 (riferimento `CFG.arenas.cascata.ref = {w:844, h:390}`, stessa formula di `rdPlace` con `cam.x=0, dist=dist0`), proiettato a quella profondità; il resto della texture (l'allargamento) continua oltre.
- `camera.far` da 60 a 200.

- [ ] Test (falliscono prima): `no holes at the camera extremes` (sfondo del renderer magenta; per dist0/distMax × cam.x −3/0/+3 × tremolio ±0,15 m, 9 pixel sul bordo dello schermo non sono magenta); `depth: near moves more than far` (cam.x +1 m: spostamento a schermo di un punto a z −2,6 > uno a z −30 > uno a z −70); `water flows, stone does not` (pixel della cascata cambia tra t=0 e t=500, pixel delle lastre no; foglie nascoste); `ground stays at 86%` e `resize keeps the ground at 86%` (sostituiscono i due test "painted floor" di `render.test.js`); `render does not change the sim`; `textures without mipmaps on WebGL1`. In `feel.test.js` il test del tremolio diventa: il punto (cam.x, 0, 0) e il piede del lottatore si spostano dello stesso numero di pixel.
- [ ] Implementazione: shader degli strati = colore `(c-.5)*contrast+.5+lift`, alfa dalla seconda texture, acqua come lo shader di oggi (maschera, tremolio, strisce), nuvole del cielo che scorrono in u (`skyDrift` u/s, ripetizione a specchio); nebbia trasparente che ondeggia (`mistDrift`). Fondale piatto tolto da `d_render.js` (`RD_BG_*`, `rdPlace`, `rdShift`, `rdFootRowY`); il tremolio ora muove solo la telecamera.
- [ ] Verifica: `arena`, `render`, `feel` verdi a 640×360, 844×390, 1280×720, 960×720. Screenshot 844×390 confrontato con il fondale di oggi.
- [ ] Commit.

### Task 3: Terrazza di lastre

**Files:** Modify `src/d_arena.js`, `src/a0_cfg.js` (`terrace`), `tests/arena.test.js`.

- [ ] Test: `slabs top is y=0 under every fighter x` (Raycaster verso il basso da y 1 a x −6..+6 passo 0,25, z 0: colpisce le lastre a |y| ≤ 0,01); `terrace covers the bottom of the screen` (già nel test dei buchi).
- [ ] Implementazione: lastre x −14..+14, z +4..−3,5, file da 0,9 m in profondità, lunghezze 0,9-1,6 m sfalsate; blocchi alti 0,25 m con la cima a y 0 (variazione solo di colore per lastra, colori dal disegno, più caldi a sinistra), fughe di 3 cm; tutte in una geometria con colori per vertice e texture di pietra su canvas (512 px, coordinate dal mondo); contorno con `f3OutlineGeo` + `F3.outMat` (larghezza `terrace.line`). Gradino in fondo (z −3,5..−3,9, cima +0,08). Erba: `InstancedMesh` di due quadrati incrociati (texture su canvas, `alphaTest`), nelle fughe e lungo il gradino, posizioni dal generatore con seme, mai a |z| < 0,6 (non sui piedi).
- [ ] Verifica e commit.

### Task 4: Colonna, stendardo, lanterna, rocce

**Files:** Modify `src/d_arena.js`, `src/a0_cfg.js` (`props`, `banner`), `tests/arena.test.js`.

- [ ] Test: `banner moves` (dopo 1 s un punto della punta si sposta di più di 2 cm); `banner stays finite after 10 minutes` (36.000 passi di `arenaStep`: tutte le posizioni finite e entro 3 m dall'asta); `props stay out of the fighters' lane` (riquadro di ogni oggetto con z < −1,5 oppure |x| > 6,5); `arena within 25 draws and 25000 triangles`; `banner step under 0.2 ms`.
- [ ] Implementazione: colonna (prisma a 10 lati r 0,34, alta 3,1 m con la cima spezzata, base squadrata, edera dipinta sulla texture) a x −5, z −2,6; asta orizzontale verso destra a y 2,75; stendardo 0,75×2,3 m, griglia 10×14 (Verlet, gravità, vento a raffiche da sinistra con seme, 2 iterazioni di vincoli, riga alta fissa), bordo basso strappato (alfa), rosso toon a due facce; lanterna (base, fusto, camera con le finestre scure, tetto a 4 falde, pomo; muschio sulle facce in alto) a x 5,2, z −2,8; 3 rocce e 2 cespugli vicino a colonna e lanterna. Contorno su tutti. Lo stendardo avanza a passi fissi di 1/60 s presi dal tempo dei fotogrammi disegnati (al massimo 4 per fotogramma).
- [ ] Verifica e commit.

### Task 5: Misure, controllo visivo, consegna

- [ ] Misura prima (commit 31551bd) e dopo: ms per fotogramma con `readPixels` (844×390, allenamento, manichino casuale, 120 fotogrammi, 3 prove); `ARENA.stats()`; durata del round con `perf.test.js`.
- [ ] Screenshot di tutte le inquadrature della griglia a 844×390 e 1280×720, guardati; confronto affiancato con il fondale di oggi; correggo quello che non va.
- [ ] Tutti i comandi di test di `docs/HANDOFF.md` verdi.
- [ ] `docs/HANDOFF.md`: sezione "Arene 3D"; pubblicazione su una pagina Claude nuova "Voidrise · Arena 3D"; push.
