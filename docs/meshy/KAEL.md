# Kael di Meshy (10/11/2026)

Kael è fatto da Meshy dal disegno di Denis di lui vestito, `docs/ref/personaggi/kael_nero.png` (tuta nera con le parti
viola, tatuaggi neri sulle spalle; Denis: "eccolo tieni, mi raccomando fallo bene"), con lo scheletro di Meshy, le 25
animazioni di Ren riportate sul suo scheletro, le ossa delle dita e una pulizia fatta da me dopo averlo guardato in 3D
da ogni lato e da vicino (`docs/meshy/CONTROLLI.md`). Il nome nel gioco è **Kael** ("Ken" è di un altro picchiaduro).

I GLB stanno in `meshy/meshy_output/` (fuori dal repository: i link di Meshy scadono). Nel repository c'è il pacchetto
pronto in `wip_assets/kael/`: `mk.sh` lo mette solo nell'anteprima di Kael (`viewer_kael.html`), non nel gioco (il
gioco usa un pacchetto Meshy appena lo trova in `assets/` o `viewer_assets/`: `src/d_render.js`, `modelBuild(c) ||
fighterBuild(c)`). Per metterlo nel gioco: spostare `wip_assets/kael/` in `viewer_assets/kael/`, test, pubblicare.

## Task Meshy e crediti (saldo prima: 1100, dopo: 1030)
| Passo | Task | Crediti |
|---|---|---|
| Corpo senza capelli né vestiti (`kael_base.png`) — superato | image-to-3d `01a1c4dd-548a-70d1-9dad-05e513084c49` | 30 |
| Il suo scheletro — superato | rigging `01a1c4df-3d59-711e-b4e5-2e7f5a85127b` | 5 |
| **Kael vestito** (`kael_nero.png`; meshy-7 standard, texture 2K, A-pose, image enhancement off, luci tolte) | image-to-3d `01a1c53b-d7ee-776a-9170-273efbf5504f` | 30 |
| **Scheletro** (1,8 m) sul modello alleggerito | rigging `01a1c53f-c3ef-76e8-82bd-4186736248a3` | 5 |
| Animazioni: le 25 di Ren, riportate sul suo scheletro | nessun task | 0 |
| **Totale** | | **70** |

Il primo corpo (senza vestiti, per vestirlo in codice) è stato lasciato: la forma gonfiata per i pantaloni larghi non
andava (Denis: "perché l'hai ingrossato così tanto?"), i vestiti solo dipinti sul corpo aderente sembravano una tuta e
i capelli fatti in codice erano lontani dal disegno (Denis: "i vestiti dipinti e pure i capelli stanno uscendo molto
male"). Meglio Meshy dal disegno vestito, come Ren.

## Come rifare il pacchetto
1. Modello: `meshy image-to-3d create --image-url docs/ref/personaggi/kael_nero.png --model-type standard
   --should-texture true --enable-pbr false --texture-resolution 2k --pose-mode a-pose --image-enhancement false
   --remove-lighting true --target-formats glb --async` (30 crediti) → `kael_nero_v1.glb`, 921.858 triangoli.
2. `python3 tools/mesh_prep/decimate_glb.py kael_nero_v1.glb kael_nero_36k.glb 36000 8000 -0.2 0.2 0.67 1.0 -1`
   (gratis: 36.000 triangoli, 8.000 per la testa e i capelli; texture e UV intatti).
3. Scheletro: `meshy rigging create --model-url kael_nero_36k.glb --height-meters 1.8 --async` (5 crediti) →
   `rigged.glb`: le stesse 24 ossa di Ren, senza dita.
4. `python3 tools/meshy_pack.py <Kael>/rigged.glb <Ren>/anims wip_assets/kael <Ren>/rigged.glb`: il quarto argomento è
   lo scheletro su cui sono fatte le clip (Ren: `meshy/meshy_output/20261107_104314_voidrise-ren-v2_01a1b59a/`).
5. `python3 tools/char_look.py wip_assets/kael wip_assets/kael`: le ossa delle dita (3 per dito e pollice, dal mesh),
   la pelle sulle dita, il pugno; le larghezze del contorno; le normali della luce lisciate.
6. `python3 tools/kael_fix.py wip_assets/kael` (dopo `char_look.py`): la pulizia, vedi sotto.
7. `bash mk.sh` (scrive anche `viewer_kael.html`), prova: `python3 tests/viewer_check.py --page=viewer_kael.html`.

## Cosa ho sistemato guardandolo (`tools/kael_fix.py`)
- **Ciocca sull'occhio destro**: Meshy l'aveva fatta scendere sull'occhio, il disegno li mostra tutti e due con una
  ciocca in mezzo: alzata sopra il sopracciglio (come `lift_bangs.py` per la frangia di Ren).
- **Occhio destro**: sotto quella ciocca Meshy non aveva dipinto l'occhio (solo una macchia): la metà destra del viso è
  la copia a specchio della sinistra, attorno al naso (solo sulla pelle del viso, non sui capelli davanti).
- **Capelli e viso a chiazze**: la luce cartoon faceva macchie grigie sulle tante ciocche e una banda scura sul viso:
  capelli in luce piatta (la pittura di Meshy ha già le ombre del disegno), viso al 75%.
- **Orecchini** bianchicci: nel viola del disegno.
- **Pittura della tuta**: puntini e triangolini bianchi, graffi chiari, pezzetti viola sul nero, file di puntini
  grigi sulle cuciture, sfumature scure sui bordi del viola (come fatte con l'aerografo): via; il viola nei due toni del
  disegno (luce e ombra, netti), il nero come l'ha dipinto Meshy.
- Non toccato: la forma del corpo (è quella di Meshy dal disegno).

## Look nel gioco
`CFG.looks.kael` in `src/a0_cfg.js`: pugni sulle sue dita (aperti nello speciale e nella presa), contorno come Ren,
luce lisciata, testa alzata di 12° in guardia, la guardia `a191` che respira di Ren, `faceShape` (la ciocca alzata),
`flatFace` (capelli e viso in luce piatta), `paint` (`kael_painted.jpg`, la pittura pulita; il pulsante "Meshy"
dell'anteprima mostra quella originale).

## Per dopo
- Le code della fascia sono attaccate ai pantaloni (le ha fatte così Meshy): seguono le gambe, non oscillano. Se Denis
  le vuole libere come quelle di Ren, si fanno coi nastri (`CFG.looks.ren.sash`).
- Il nero della tuta resta quello di Meshy (in due toni diventava granuloso).
