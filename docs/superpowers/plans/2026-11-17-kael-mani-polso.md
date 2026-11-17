# Voidrise Fighters · Mani e polsi di Kael rifatti · Piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (Denis, per Kael: "niente agenti per il corpo": niente subagenti su questo lavoro). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** nell'anteprima di Kael le mani sono quelle di Ren come si vedono su Ren, il mezzo guanto è un guscio vero sopra la pelle e al polso c'è un anello viola in rilievo che copre l'attacco col bracciale (niente collo, lembo, macchie).

**Architecture:** `tools/kael_bust_attach.py` calcola già posizioni, pesi e normali delle mani di Ren messe su Kael (i vertici `isR` del busto). Ora le scrive come **parti a sé** del pacchetto di Kael, accanto al busto: `kael_hands` (i triangoli delle mani con le coordinate della pittura di Ren e un ritaglio esatto di `ren_painted.jpg`) e `kael_gloves` (guscio dei guanti + bordo + anelli dei polsi, a colori per vertice). Le funzioni geometriche nuove stanno in un modulo nuovo, `tools/kael_gear.py`. In `src/e_model.js` `mdPartData` carica le due parti e `modelBuild` le disegna sullo stesso scheletro: le mani col materiale del corpo di Ren (toon + luce piatta per vertice), i guanti con un materiale toon a colori per vertice e la riga d'inchiostro sul bordo.

**Tech Stack:** Three.js r128 (`SkinnedMesh`, `MeshToonMaterial`, `onBeforeCompile`), JavaScript vanilla, Python 3 + numpy + scipy + Pillow, Playwright per controlli e immagini.

**Spec:** `docs/superpowers/specs/2026-11-17-kael-mani-polso-design.md` (approvato da Denis il 17/11: "si").

## Global Constraints

- Solo l'anteprima di Kael (`viewer_kael.html`, pacchetto in `wip_assets/kael/`): il gioco, l'app e Ren non cambiano (i 22 test devono restare verdi, `viewer.html` uguale).
- Non si toccano testa, occhi, sopracciglia, busto sopra il polso, gambe, fascia. Niente Meshy, niente agenti.
- Colori dei fogli del busto: guanto prugna `(65, 49, 74)`, inchiostro `(9, 6, 9)`, anello viola `(166, 92, 203)` con ombra `(108, 63, 138)` (`PAL` in `tools/kael_bust.py`, `MD_GLOVE` in `src/e_model.js`).
- Mani alla grandezza di adesso: `HAND_MUL` 0,9. Pugno di Ren com'è: `THUMB_FOLD` 0 (se torna il "cuneo" della base del pollice, `THUMB_FOLD` 1 e lo si dice a Denis).
- "Prima di pubblicare: tutti i test verdi e nessun errore nella console." Immagini a Denis prima; si pubblica l'anteprima di Kael solo col suo ok.
- Misura prima e dopo: triangoli disegnati e tempo per fotogramma dell'anteprima.

## Review Focus

1. Polso piegato al massimo (colpito, a terra, si rialza, presa): atteso che guanto e mano restino dentro l'anello. Test in Task 4 `ring covers the wrist in every move` (tutti i pulsanti, non solo la guardia).
2. Mani aperte (speciale, presa): atteso che il guscio stia sopra il palmo piatto senza bucarlo e che la base del pollice resti coperta. Test in Task 3 `shell stays over the skin in every move` (tutti i pulsanti).
3. Kael specchiato (nel gioco il lottatore a destra ha `body.scale.x` negativo): atteso che guanti e anelli non si vedano rovesciati. Materiale dei guanti `DoubleSide`; test in Task 3 `gloves render mirrored`.
4. Telecamera lontana del gioco: atteso niente sfarfallio tra guscio e pelle. Controllo a vista in Task 5 dalla distanza della telecamera del gioco (guscio di 2 mm).
5. Hit flash: atteso che anche mani, guanti e anelli lampeggino col corpo (`f_fx.js` accende tutti i materiali di `it.mats`). `it.mats.hands` e `it.mats.gloves` registrati in Task 2 e 3, prova `flash` in Task 2 (estesa ai guanti nel Task 3).

---

### Task 1: Telecamera delle mani (`tools/handcam.py`), misura di partenza

**Files:**
- Create: `tools/handcam.py`

**Interfaces:**
- Produces: `python3 tools/handcam.py OUT [--page=viewer_kael.html] [--ref=viewer.html]` scrive in `OUT/` i fogli `pugno_Left.png`, `pugno_Right.png`, `aperta_Left.png`, `aperta_Right.png`, `polso_guardia_Left.png`, `polso_guardia_Right.png`, `polso_pugno_Left.png`, `polso_pugno_Right.png` (riga sopra Kael, sotto Ren, 8 lati per foglio, sfondo grigio neutro senza il palco) e stampa per ogni foglio una riga `pugno_Left skin dE 12.3 (kael L 61 a 18 b 30, ren L 74 a 16 b 27)`. Codice di uscita 0.

- [ ] **Step 1: Scrivere lo strumento** partendo dagli script di prova di oggi (`hands.py`, `wrist.py`, `bind.py` nello scratchpad): la camera a 0,42-0,5 m dall'osso `<Side>Hand` (polso) o 6 cm oltre (mano), 8 yaw a passi di 45° con pitch 0,2; pugno = pulsante 0 dopo `VW.tick(40)`; pugno sferrato = pulsante 2 dopo `VW.tick(7)`; mano aperta = `skeleton.pose()` di tutte le `SkinnedMesh` con `requestAnimationFrame` fermato; `#stage` nascosto e `VW.renderer.setClearColor(0x808080)`. Pelle = pixel con tinta 15-60°, croma > 15, L > 35 (Lab); `dE` = CIE76 tra le medie di Kael e di Ren.
- [ ] **Step 2: Lanciarlo sulla versione 21 (misura di partenza)**

Run: `python3 tools/handcam.py /tmp/claude-0/-home-user/0d6d7b95-dc0a-502a-a10b-27f5040eba0c/scratchpad/hc0`
Expected: 8 fogli scritti, 8 righe `skin dE`; annotare i valori (attesi alti su `pugno_*` e `aperta_*`: le dita marroni).
- [ ] **Step 3: Commit**

```bash
git add tools/handcam.py
git commit -m "tools/handcam.py: Kael's and Ren's hands and wrists side by side, the skin's colour difference"
```

---

### Task 2: Le mani di Ren come parte a sé (`kael_hands`)

**Files:**
- Create: `tools/kael_gear.py`, `tests/kael_gear_check.py`
- Modify: `tools/kael_bust_attach.py` (fine di `main`: la parte `hands`; il busto senza i triangoli delle mani; `THUMB_FOLD` 0)
- Modify: `src/e_model.js` (`mdPartData`, `modelBuild`: parte `hands`; la luce piatta per vertice in una funzione)
- Modify: `src/a0_cfg.js` (`CFG.looks.kael.hands: true`)
- Modify: `tests/viewer_check.py` (prove `hands`, `flash`; `KAEL_ONLY`)

**Interfaces:**
- Produces in `tools/kael_gear.py`: `crop_paint(img: PIL.Image, uv: ndarray(n,2), pad=4) -> (PIL.Image, ndarray(n,2))` — ritaglio al pixel del rettangolo delle coordinate, coordinate rimappate senza ricampionare.
- Produces in `tools/kael_gear.py`: `write_part(dir, name, arrays: dict, extra: dict, img=None)` — stesso formato del busto (`v`, `verts`, `tris`, blocchi `[offset, count]` nel `.bin`, `hide` vuoto se manca), più l'immagine `<name>.jpg` (qualità 95) se data.
- Produces nel pacchetto: `wip_assets/kael/kael_hands.json|.bin|.jpg` con `pos, nor, uv, jnt, wgt, idx, flat, line` (niente `lb`: il contorno spinto indietro come il corpo di Ren, `back` 0,02).
- Produces in `src/e_model.js`: `mdFlatLight(mat)` (l'attuale blocco `if (flat) {...}` di `modelBuild`, usato dal corpo e dalle mani); `it.hands` (`SkinnedMesh`), `it.mats.hands`.

- [ ] **Step 1: Scrivere i controlli in `tests/kael_gear_check.py`** (script con `assert`, stampa `OK` alla fine):
  - `crop_paint_is_exact`: per 500 punti a caso delle mani, il colore del ritaglio alle coordinate nuove è quello di `ren_painted.jpg` alle vecchie (differenza media < 3 livelli, dopo la ricodifica JPG);
  - `hands_part_is_rens`: in `kael_hands.json` ogni vertice ha `flat` e `line` uguali a quelli del vertice di Ren corrispondente (`viewer_assets/ren/ren_look.json`, entro 1e-6) e normali uguali a quelle di Ren girate come la mano (entro 1°);
  - `bust_has_no_hand_triangles`: nessun triangolo di `kael_bust` ha tutti e tre i vertici sulle mani (servono i `rid` del busto: `KAEL_ATTACH_DUMP`).
- [ ] **Step 2: Lanciarli e vederli fallire**

Run: `python3 tests/kael_gear_check.py`
Expected: FAIL (`kael_hands.json` non esiste).
- [ ] **Step 3: Implementare `crop_paint`, `write_part` e, in `kael_bust_attach.main`, la parte `hands`**: i triangoli con tutti i vertici `isR` vanno nella parte (coordinate `R['UV'][rid]`, normali di Ren girate *prima* di `HAND_NSMOOTH`, `flat`/`line` del look di Ren, gli stessi `top`/`tw`); il busto tiene gli altri (le cuciture mezze e mezze restano nel busto, sotto l'anello). `THUMB_FOLD` di default 0.
- [ ] **Step 4: Rifare il pacchetto e rilanciare i controlli**

Run: `KAEL_ATTACH_DUMP=/tmp/claude-0/-home-user/0d6d7b95-dc0a-502a-a10b-27f5040eba0c/scratchpad/dump.npz python3 tools/kael_bust_attach.py meshy/meshy_output/20261111_kael-busto/busto_k11.glb && python3 tests/kael_gear_check.py`
Expected: `OK`.
- [ ] **Step 5: Aggiungere a `tests/viewer_check.py` le prove di Kael** (filtrate per Ren con `KAEL_ONLY = ('hands', 'flash', 'gloves', 'shell', 'ring', 'mirror')`):
  - `hands`: `!!it.hands && it.hands.isSkinnedMesh && it.hands.skeleton === it.mesh.skeleton && it.hands.geometry.index.count / 3 > 2000`;
  - `flash`: il lampo del colpo (`f_fx.js`) accende tutti i materiali di `it.mats`: `Object.values(it.mats).includes(it.hands.material)` (e, dal Task 3, `it.gloves.material`).
- [ ] **Step 6: Disegnare la parte** in `modelBuild`: `mdPartData(md, key, 'hands')` se `lk.hands`; materiale `MeshToonMaterial({map, gradientMap: F3.grad, skinning: true})` con `mdFlatLight`; contorno `mdLineMat({skinning: true, w: (ol.w / s).toFixed(5), per: ' * aLine', back: ol.back})`; `bind(skel, mesh.matrixWorld)`; `it.hands`, `it.mats.hands`. `CFG.looks.kael.hands = true`.
- [ ] **Step 7: Build, controlli, immagini**

Run: `bash mk.sh && python3 tests/viewer_check.py --page=viewer_kael.html && python3 tests/viewer_check.py && python3 tools/handcam.py /tmp/claude-0/-home-user/0d6d7b95-dc0a-502a-a10b-27f5040eba0c/scratchpad/hc2`
Expected: `SYNTAX_OK`; i due controlli dell'anteprima verdi; `skin dE` < 5 su `pugno_*` e `aperta_*` (prima: i valori del Task 1). Guardare i fogli: la pelle come quella di Ren; se si vede il cuneo alla base del pollice, `KAEL_THUMB_FOLD=1` e nota per Denis.
- [ ] **Step 8: Commit**

```bash
git add tools/kael_gear.py tools/kael_bust_attach.py tests/kael_gear_check.py tests/viewer_check.py src/e_model.js src/a0_cfg.js wip_assets/kael/kael_hands.* wip_assets/kael/kael_bust.*
git commit -m "Kael's hands: Ren's, as their own part (his paint cropped, his normals, his light and outline)"
```

---

### Task 3: Il guscio dei guanti (`kael_gloves`, prima metà)

**Files:**
- Modify: `tools/kael_gear.py`, `tools/kael_bust_attach.py`, `src/e_model.js`, `src/a0_cfg.js`, `tests/kael_gear_check.py`, `tests/viewer_check.py`

**Interfaces:**
- Consumes: la distanza firmata dal bordo del guanto per vertice delle mani (`gfield[:, 0]` di `kael_bust_attach.main`, m, negativa dentro il guanto), le posizioni/normali/pesi della parte `hands` (Task 2).
- Produces in `tools/kael_gear.py`:
  - `clip_iso(P, N, W, D, I) -> (P, N, W, D, I)`: i triangoli tagliati lungo `D = 0` (si tiene `D <= 0`), attributi interpolati sul lato, pesi rinormalizzati ai 4 maggiori;
  - `shell(P, N, D, I, t=.002, wall=.0015) -> (P, N, D, I, ink)`: copia spinta di `t` lungo la normale, più la striscia del bordo (dal guscio verso la pelle, `wall` di altezza) con `ink` = 1 sui suoi vertici;
  - `near_index(P_shell, P_hands) -> ndarray(int)`: per ogni vertice del guscio il vertice delle mani da cui viene.
- Produces nel pacchetto: `kael_gloves.json|.bin` (senza immagine) con `pos, nor, uv` (zeri), `jnt, wgt, idx, col` (rgb 0-1 per vertice), `glove` (`[D, 1]`: la riga d'inchiostro dove `|D| < MD_GLOVE.w`), `line`, `near`.
- Produces in `src/e_model.js`: `mdPartData` accetta una parte senza immagine se ha `col` (attributo `color`); `it.gloves`, `it.mats.gloves`.

- [ ] **Step 1: Scrivere i controlli** in `tests/kael_gear_check.py`:
  - `clip_edge_on_iso`: ogni vertice nuovo del taglio ha `|D| < 1e-6`; l'area tenuta è quella con `D <= 0` (entro 1%) su una mesh di prova (un piano 10×10 con `D = x - .3`);
  - `shell_offset`: sui vertici interni (`D < -.003`) la distanza dal vertice delle mani da cui vengono è `t` ± 0,2 mm;
  - `glove_covers`: ogni vertice delle mani con `D < -.003` ha un vertice del guscio entro `t + 1` mm.
- [ ] **Step 2: Lanciarli e vederli fallire** — Run: `python3 tests/kael_gear_check.py` — Expected: FAIL (`clip_iso` non esiste).
- [ ] **Step 3: Implementare `clip_iso`, `shell`, `near_index`** e in `kael_bust_attach.main` la parte `gloves` (per ora solo i gusci): colore `PAL.plum`, `ink` → `PAL.ink`; `line` del vertice delle mani da cui viene.
- [ ] **Step 4: Rilanciare** — Run: come Task 2 Step 4 — Expected: `OK`.
- [ ] **Step 5: Prove nell'anteprima** in `tests/viewer_check.py`:
  - `gloves`: `!!it.gloves && !!it.gloves.geometry.attributes.color && !!it.gloves.geometry.attributes.aGlove`;
  - `shell`: per tutti i pulsanti, 1 fotogramma ogni 6, su 300 vertici del guscio con `D < -.003`: posizione con `boneTransform`, e quella del vertice `near` delle mani più 1 mm lungo la sua normale; lo scarto lungo la normale > 0,5 mm nel 99% dei casi;
  - `mirror`: con `it.body.scale.x` negativo il guscio si disegna (pixel prugna nell'inquadratura del pugno);
  - `flash` esteso: `Object.values(it.mats).includes(it.gloves.material)`.
- [ ] **Step 6: Disegnare la parte** in `modelBuild`: `MeshToonMaterial({vertexColors: true, gradientMap: F3.grad, skinning: true, side: THREE.DoubleSide})`, `onBeforeCompile` con `aGlove` (inchiostro `MD_GLOVE.ink` dove `abs(vGlove.x) < MD_GLOVE.w`), contorno come le mani. `CFG.looks.kael.gloves = true`; `it.mats.gloves` nel lampo.
- [ ] **Step 7: Build, controlli, immagini** — Run: `bash mk.sh && python3 tests/viewer_check.py --page=viewer_kael.html && python3 tools/handcam.py /tmp/claude-0/-home-user/0d6d7b95-dc0a-502a-a10b-27f5040eba0c/scratchpad/hc3` — Expected: verdi; nei fogli il guanto ha volume, bordo nero netto, nessuna pelle che lo buca.
- [ ] **Step 8: Commit** — `git commit -m "Kael's gloves: a real shell over Ren's hands, their edge in ink"` (con i file del task e il pacchetto).

---

### Task 4: Gli anelli dei polsi e il guanto che entra nell'anello

**Files:**
- Modify: `tools/kael_gear.py`, `tools/kael_bust_attach.py`, `tests/kael_gear_check.py`, `tests/viewer_check.py`

**Interfaces:**
- Consumes: per lato l'asse dell'avambraccio (`J[sd]['Eb2']` → `J[sd]['Hb2']`), la banda viola del polsino (`forearm(...)` di `kael_bust_attach.py`: centro e altezza), i vertici di busto e mani attorno al polso.
- Produces in `tools/kael_gear.py`:
  - `ring(c, ax, ref, r_th, h, bulge=.002, n_th=48, n_h=7) -> (P, N, I, edge)`: tubo attorno all'asse, raggio per angolo `r_th` (array `n_th`), bombato di `bulge` a metà altezza, `edge` = distanza dal bordo più vicino lungo l'asse (per la riga d'inchiostro dei due orli);
  - `ring_radius(Pn, c, ax, ref, h, clear=.003, n_th=48) -> ndarray(n_th)`: per angolo il raggio più grande dei vertici entro l'altezza dell'anello più `clear`, lisciato in cerchio;
  - `flare(P, c, ax, ref, r_th, span=.025) -> P`: i vertici del guscio entro `span` dall'orlo dell'anello verso la mano portati almeno al raggio interno dell'anello meno 1 mm, sfumando.
- Produces nel pacchetto: gli anelli nella parte `gloves` (colore `PAL.purple`, `glove` = `[-edge, 1]` così gli orli hanno la riga), pesi: avambraccio 1 all'orlo verso il gomito, avambraccio 0,5 e mano 0,5 all'orlo verso la mano; `inside` (vertici di busto e mani dentro l'altezza dell'anello) e `ringOuter` (i vertici esterni degli anelli) nel json.

- [ ] **Step 1: Scrivere i controlli**: `ring_clears_wrist` (a ogni angolo il raggio dell'anello supera di almeno 2 mm ogni vertice di busto, mani e guscio dentro la sua altezza, nella posa di riposo); `flare_no_neck` (dopo `flare`, il raggio del guscio a `span` dall'anello non è sotto il raggio interno dell'anello meno 1 mm).
- [ ] **Step 2: Lanciarli e vederli fallire** — Expected: FAIL (`ring` non esiste).
- [ ] **Step 3: Implementare `ring`, `ring_radius`, `flare`** e aggiungere gli anelli alla parte `gloves` in `kael_bust_attach.main`.
- [ ] **Step 4: Rilanciare** — Expected: `OK`.
- [ ] **Step 5: Prova nell'anteprima** `ring`: per tutti i pulsanti, 1 fotogramma ogni 6, ogni vertice `inside` (posizione con `boneTransform`) sta dalla parte interna del vertice `ringOuter` più vicino (scarto lungo la sua normale < 0) nel 99,5% dei casi.
- [ ] **Step 6: Build, controlli, immagini** — Run: `bash mk.sh && python3 tests/viewer_check.py --page=viewer_kael.html && python3 tools/handcam.py /tmp/claude-0/-home-user/0d6d7b95-dc0a-502a-a10b-27f5040eba0c/scratchpad/hc4` — Expected: verdi; nei fogli `polso_*` niente collo, niente lembo, niente macchie nere, l'anello fa tutto il giro.
- [ ] **Step 7: Commit** — `git commit -m "Kael's wrists: a raised purple ring over the join, the glove flared into it"`.

---

### Task 5: Controllo completo, misure, documenti, immagini a Denis

**Files:**
- Modify: `docs/meshy/KAEL.md` (sezione nuova "Mani e polsi rifatti (17/11)"), `docs/HANDOFF.md`

- [ ] **Step 1: Controllo a vista** (regola di Denis: guardarlo io da ogni lato prima di mostrarlo): `tools/handcam.py` più il personaggio intero da 4 lati in guardia, pugno forte, calcio forte, accovacciato, speciale, presa, colpito, a terra, e dalla distanza della telecamera del gioco (sfarfallio guscio/pelle). Correggere quello che si trova e ripetere.
- [ ] **Step 2: Misure prima/dopo**: triangoli disegnati (`VW.renderer.info.render.triangles`) e ms per fotogramma dell'anteprima con la GPU sincronizzata (come nelle misure del 10/11), versione 21 contro questa.
- [ ] **Step 3: Tutti i test** — Run: i 22 comandi di `docs/HANDOFF.md` ("Build e test") più `python3 tests/kael_gear_check.py` — Expected: tutti verdi, nessun errore in console.
- [ ] **Step 4: Documenti**: `KAEL.md` (cosa è cambiato, valori, provati e lasciati), `HANDOFF.md` ("Prossimo passo": in attesa dell'ok di Denis sulle immagini).
- [ ] **Step 5: Commit e push** — `git push origin tappa2-ren-meshy`.
- [ ] **Step 6: Immagini a Denis** (prima/dopo: pugni, mani aperte, polsi, personaggio intero) e aspettare il suo ok. **Solo dopo l'ok**: `bash mk.sh`, Artifact con `viewer_kael.html` sull'URL dell'anteprima di Kael (`CLAUDE.md`), `HANDOFF.md` con la versione pubblicata, commit, push.
