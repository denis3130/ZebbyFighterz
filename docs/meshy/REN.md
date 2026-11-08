# Ren di Meshy (Tappa 2a, 7/11/2026)

Il modello e le animazioni di Ren nel gioco vengono da Meshy (CLI `meshy-cli@0.4.0`). I file sorgente (GLB) stanno in
`meshy/meshy_output/` (fuori dal repository, i link di Meshy scadono); nel repository c'è il pacchetto già pronto,
`assets/ren/ren.json` + `ren.bin` + `ren.jpg`, che contiene tutto (mesh, scheletro, 25 clip a 30 fps).

## Task Meshy e crediti (saldo prima: 1345, dopo: 1225)
| Passo | Task | Crediti |
|---|---|---|
| Primo modello (meshy-t2, smart topology 15k) — scartato | image-to-3d `01a1b55c-5be1-7674-9f17-0e7df4dd5d5a` | 15 |
| Retexture col disegno di Denis come riferimento — scartato | retexture `01a1b58d-0095-770a-ad6f-878e5392d7df` | 10 |
| Modello finale (meshy-7, 2K, A-pose, image enhancement off, luci tolte) | image-to-3d `01a1b59a-e229-73d1-9b42-94f4375bbfa4` | 30 |
| Scheletro (1,8 m) sul modello alleggerito | rigging `01a1b5aa-7164-7046-9616-0c81a520aa72` | 5 |
| 25 animazioni (una per task) | animate, id azione nel nome della clip (`a89` = azione 89) | 75 |
| **Totale** | | **135** |

Attenzione: nel catalogo delle animazioni `is_free: true` (Idle, Arise, BeHit FlyUp, Dead, Run Fast, Skill 1...)
**non** vale per la API: ogni azione costa 3 crediti. Previsti 60 per le animazioni, spesi 75.

## Preparazione del modello (gratis, prima dello scheletro)
1. `python3 tools/mesh_prep/decimate_glb.py ren_v2.glb ren_v2_30k.glb 30000` — da 1.026.680 a 30.000 triangoli, texture e UV
   intatti (pymeshlab, quadric edge collapse con texture; serve `libopengl0`).
2. `python3 tools/mesh_prep/lift_bangs.py ren_v2_30k.glb ren_v2_30k_frangia.glb 0.80 0.712 0.752 -0.055 0.075` — la
   frangia davanti agli occhi viene accorciata fino a sopra le sopracciglia (gli occhi da anime erano dipinti sotto).
3. Scheletro Meshy su quel GLB (`--model-url`, `--height-meters 1.8`).

## Rifare il pacchetto
`python3 tools/meshy_pack.py <rigged.glb> <cartella con a<ID>.glb> assets/ren`, poi `bash mk.sh`.
Il pacchetto: spazio in metri, piedi a 0, davanti +z; normali della testa arrotondate (faccia pulita nel toon);
corregge i fotogrammi difettosi dei fianchi (Walk Fight Back: fotogrammi 3-4 e 23-24).

## Quali clip per cosa
La tabella è `CFG.clips` in `src/a0_cfg.js` (commentata lì). Il colpo cade nel fotogramma in cui la logica colpisce:
il tempo del colpo di ogni mossa si trova al caricamento (il punto del colpo più dentro la hitbox). Il calcio basso
(`ck`) è fatto con una IK sulla gamba sinistra, perché la clip "Sweeping Kick" non scende abbastanza.
Foglio di controllo di tutte le pose: `python3 tools/pose_sheet.py out.png [moves|acts|all]`.

## Dita (7/11/2026)
- Lo scheletro della API non ha le dita: 24 ossa, solo `LeftHand`/`RightHand` (controllato anche nel FBX del task di
  rigging). Il rigging fatto sul sito meshy.ai le ha: Denis ne ha fatto uno lì (modello da 95.085 facce). Nel
  frattempo il saldo è sceso da 1225 a 1190 (35 crediti, quasi certamente quel modello: sito e API usano lo stesso).
- I modelli fatti sul sito **non si raggiungono dalla API**: gli elenchi della API mostrano solo i task della API e
  `input_task_id` accetta solo task della API (la documentazione Meshy lo dice: i task della API restano nella API e
  non compaiono in "My Assets"). Per usarne uno serve scaricarlo dal sito (Download → GLB) e metterlo nel repository.
- Le dita di Ren le calcola `tools/ren_look.py` dal suo mesh (le mani hanno dita separate): 3 ossa per dito e per il
  pollice, pesi della pelle sfumati sulle articolazioni, nel pugno le quattro dita chiuse alla stessa altezza (le nocche
  spostate lungo le dita) e il pollice sopra indice e medio. Solo dove
  `CFG.looks.ren.fists` è acceso (per ora nell'anteprima).


## Testa nuova dal foglio delle 3 viste (8/11/2026)
Denis ha dato il foglio `docs/ref/personaggi/ren_testa_3viste.png` (destra, fronte, sinistra): "fallo IDENTICO da
tripla A". La testa vecchia di Meshy (fatta dal disegno del corpo intero) non aveva capelli, mento, orecchie e colletto
come il foglio, quindi la testa è nuova; corpo, scheletro e animazioni restano.

| Passo | Task | Crediti |
|---|---|---|
| Prova 1: multi-image-to-3d con le 3 viste intere (fino al petto), texture 2k — scartata (viso meno definito) | `01a1b8b6-0401-7601-96e5-44ae018760ec` | 30 |
| Prova 2: le 3 viste ritagliate su testa e colletto, texture 4k — usata | `01a1b8c5-75d7-778c-b63e-38a5817727a9` | 30 |
| Prova 3: viste strette sulla testa (le punte dei capelli più grandi nell'immagine), texture 4k — scartata: punte più lunghe in miniatura, ma misurata sul foglio sopra il colletto la sagoma non è più vicina (sovrapposizione media 0,863 contro 0,876 della prova 2) | `01a1b942-88c8-74d9-aafc-4598f8478250` | 30 |
| **Totale** (saldo da 1190 a 1100; il tetto approvato da Denis era 90, cioè 3 prove) | | **90** |

Rifarla (i GLB stanno in `meshy/meshy_output/20261108_011130_voidrise-ren-testa_4183/`, fuori dal repository):
1. `python3 tools/mesh_prep/decimate_glb.py testa_v2.glb meshy/head/testa_v2_face.glb 16000 4500 -0.3 0.3 -0.16 0.34 0.1`
   — 16.000 triangoli, di cui 4.500 nel viso (il riquadro del viso nelle unità del GLB): occhi e mascella precisi.
2. `python3 tools/ren_head.py meshy/head/testa_v2_face.glb assets/ren viewer_assets/ren` — taglio sopra le spalle,
   posizione sul corpo, ossa, occhi a filo del viso, frangia vicina al viso, colori del foglio; scrive `ren_head.json`,
   `.bin`, `.jpg` (i punti di riferimento di ogni busto stanno in `BUSTS`).
3. `python3 tools/paint_from_drawing.py assets/ren docs/ref/personaggi/ren.png viewer_assets/ren/ren_painted.jpg` (pulisce
   il petto sotto il colletto nuovo), poi `bash mk.sh`.
