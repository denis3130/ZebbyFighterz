# Kael di Meshy (10/11/2026)

Denis, 10/11: "manca ken, ora te lo mando pelato e senza vestiti così gli aggiungiamo noi senza fare tutti i passaggi
infiniti che abbiamo fatto per ren", poi "crealo già con le ossa anche sulle dita". Il nome nel gioco è **Kael**
(nei documenti dal 6/11; "Ken" è un nome di un altro picchiaduro). Il corpo viene da Meshy, dal disegno di Denis senza
capelli né vestiti (`docs/ref/personaggi/kael_base.png`, in A-pose come Ren, solo pantaloncini neri); capelli e vestiti
del disegno completo (`docs/ref/personaggi/kael.png`) si costruiscono in codice, non si chiedono a Meshy.

I GLB stanno in `meshy/meshy_output/20261110_095010_voidrise-kael_01a1c4dd/` (fuori dal repository: i link di Meshy
scadono). Nel repository c'è il pacchetto pronto, in `wip_assets/kael/` finché capelli e vestiti non sono fatti:
`mk.sh` lo mette solo nell'anteprima di Kael (`viewer_kael.html`), non nel gioco (il gioco usa un pacchetto Meshy
appena lo trova in `assets/` o `viewer_assets/`: `src/d_render.js`, `modelBuild(c) || fighterBuild(c)`).

## Task Meshy e crediti (saldo prima: 1100, dopo: 1065)
| Passo | Task | Crediti |
|---|---|---|
| Modello (meshy-7 standard, texture 2K, A-pose, image enhancement off, luci tolte) | image-to-3d `01a1c4dd-548a-70d1-9dad-05e513084c49` | 30 |
| Scheletro (1,8 m) sul modello alleggerito | rigging `01a1c4df-3d59-711e-b4e5-2e7f5a85127b` | 5 |
| Animazioni: le 25 di Ren, riportate sul suo scheletro | nessun task | 0 |
| **Totale** | | **35** |

## Come rifare il pacchetto
1. Modello: `meshy image-to-3d create --image-url docs/ref/personaggi/kael_base.png --model-type standard --should-texture true
   --enable-pbr false --texture-resolution 2k --pose-mode a-pose --image-enhancement false --remove-lighting true
   --target-formats glb --async` (30 crediti) → `kael_v1.glb`, 321.598 triangoli.
2. `python3 tools/mesh_prep/decimate_glb.py kael_v1.glb kael_v1_30k.glb 30000` (gratis, texture e UV intatti).
3. Scheletro: `meshy rigging create --model-url kael_v1_30k.glb --height-meters 1.8 --async` (5 crediti) → `rigged.glb`:
   le stesse 24 ossa di Ren (stessi nomi, stessa gerarchia), senza dita.
4. `python3 tools/meshy_pack.py <Kael>/rigged.glb <Ren>/anims wip_assets/kael <Ren>/rigged.glb`: il quarto argomento è
   lo scheletro su cui sono fatte le clip; ogni osso prende la rotazione nel mondo che ha nella clip rispetto al suo
   riposo nello scheletro di Ren, applicata al suo riposo in quello di Kael, e il movimento dei fianchi è scalato
   dall'altezza dei due bacini (Ren: `meshy/meshy_output/20261107_104314_voidrise-ren-v2_01a1b59a/`).
5. `python3 tools/char_look.py wip_assets/kael wip_assets/kael` → `kael_look.json` + `.bin`: le ossa delle dita (3 per dito
   e pollice, dal mesh, come quelle di Ren: `ren_look.finger_rig`), la pelle sulle dita, il pugno; le larghezze del
   contorno (sottile sul viso e sulle dita, niente alla radice del pollice e sui palmi); le normali della luce lisciate.
6. `python3 tools/kael_outfit.py wip_assets/kael` (dopo `char_look.py`): i vestiti, vedi sotto.
7. `bash mk.sh` (scrive anche `viewer_kael.html`), prova: `python3 tests/viewer_check.py --page=viewer_kael.html`.

## Dita
- Nel modello di Meshy le quattro dita di ogni mano sono **un pezzo solo** (attaccate fino alla punta, come una
  manopola; già nel modello da 321.598 triangoli, non è colpa dell'alleggerimento). `ren_look.split_fused` lo divide
  di traverso in quattro dita (`FUSED_W`: 26, 27, 25 e 22% della larghezza dal lato del pollice); con 5 dita già
  separate (Ren) non fa niente: il look di Ren rifatto è identico byte per byte.
- Da vicino il pugno è meno pulito di quello di Ren (le dita si piegano ma la pelle tra l'una e l'altra resta unita).
  I mezzi guanti del disegno copriranno il dorso e il palmo.

## Look nel gioco
`CFG.looks.kael` in `src/a0_cfg.js`: pugni sulle sue dita (aperti nello speciale e nella presa), contorno come Ren
(7 mm, solo sul bordo esterno, sottile sul viso e sulle dita), luce lisciata, testa alzata di 12° in guardia, la
guardia `a191` che respira di Ren; dal 10/11 i vestiti dipinti dai fogli (`paint`).

## Vestiti (10/11/2026, dai fogli di Denis)
Denis ha mandato i fogli del resto: `docs/ref/personaggi/kael_testa_3viste.png`, `kael_busto_3viste.png`,
`kael_gambe_3viste.png`, `kael_retro.png`. Il disegno intero vestito `kael.png` combacia col disegno del corpo
`kael_base.png` (stessa posa e misure), da cui Meshy ha fatto il corpo: lo si proietta sul modello senza aggiustamenti.

Tappa 1, i vestiti che seguono il corpo (`tools/kael_outfit.py`): dipinti dai fogli sulla pelle del corpo. Nella prima
versione (anteprima v2) la pelle era anche spostata in fuori fino alla sagoma del disegno (pantaloni larghi ecc.); Denis
l'ha vista (10/11: "perché l'hai ingrossato così tanto? il modello iniziale la forma andava benissimo") e ora il corpo
tiene la forma di Meshy (`MOVE = False`): le forme dei capi servono solo a sapere dove è ogni capo (i materiali della
pittura) e ad adattare il foglio da dietro.
- Capi: maglia senza maniche, colletto alto (cilindro attorno al collo, pesi solo di collo e schiena), fascia in vita,
  pantaloni larghi (il profilo misurato su `kael.png`: di lato fino a 5,5 cm in più della gamba), stivali con la
  cinghia e la suola viola, polsiere con i bordi rialzati, mezzi guanti. Ogni capo lisciato da solo, i bordi netti.
- Dove finiscono pelle e stoffa (spalle, polsiere, guanti) lo decide il disegno: davanti `kael.png`, dietro
  `kael_retro.png` (adattato alla sagoma, 86% dei vertici dentro).
- Pittura: davanti e dietro proiettati; sui fianchi, che nessuna delle due viste vede bene, il colore del capo. Le viste
  di tre quarti dei fogli non si usano: disegnate in modo diverso da una vera rotazione, non combaciano col modello
  (provato con l'adattamento della sagoma).
- Non dipinti sul corpo i pezzi che pendono (le code della fascia, la parte della maglia sotto la fascia, lo spallaccio):
  diventano pezzi veri nella tappa 3. La testa resta quella di Meshy fino ai capelli (tappa 2).
- Nel look: `paint` (`kael_painted.jpg`).

Tappa 2, i capelli (in corso, non accesi): `tools/kael_hair.py` costruisce in codice la massa e le ciocche (con i bordi
neri disegnati sulle ciocche e le punte prese dalla sagoma del disegno) e gli orecchini, come pezzo del look
(`kael_hair.json|bin|png`, `CFG.looks.kael.parts: ['hair']`, `e_model` `mdPartData`). La prima prova davanti sembra un
casco con bastoncini ai lati: da rifare prima di accenderla.
