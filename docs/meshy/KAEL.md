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
7. `python3 tools/kael_arms.py wip_assets/kael [CARTELLA_DEBUG]` (dopo `kael_fix.py`): le braccia dipinte dai fogli,
   vedi sotto (circa 1 minuto).
8. `python3 tools/kael_face.py wip_assets/kael [CARTELLA_DEBUG]` (dopo `kael_fix.py`): il viso dipinto dal foglio della
   testa, vedi sotto (circa 30 secondi). I passi 5-8 si possono rifare sempre da capo: danno sempre lo stesso risultato.
9. `bash mk.sh` (scrive anche `viewer_kael.html`), prova: `python3 tests/viewer_check.py --page=viewer_kael.html`.

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

## Tuta meno scura (`tools/kael_fix.py`, 10/11)
Denis: "cambiare il colore del modello 3d di kael da troppo scuro a più come nelle foto". Misurato in 3D contro
`kael_nero.png`: pelle, capelli e viola uguali; la tuta no (Meshy l'aveva dipinta quasi tutta nera: luminosità media 23
contro 39 del disegno, dove più di metà della tuta è grigio antracite e le pieghe nere). Ora il nero è nei due toni del
disegno (antracite 46,45,48 e pieghe 14,13,15, seguendo le pieghe dipinte da Meshy, senza puntini), e il davanti del
corpo è in luce piatta come quello di Ren (i colori del disegno, senza le bande scure della luce). In guardia la figura
ha luminosità media 79 (prima 74, disegno 77), la tuta 38.

## Viso dal foglio della testa (`tools/kael_face.py`, 10/11)
Denis: "la faccia fa ancora schifo", "no per la testa fai tu niente meshy". La testa di Meshy resta com'è; il viso è
ridipinto dal pannello di fronte di `kael_testa_3viste.png`:
- allineato sui punti del viso (iridi, punta del naso, bocca, mento): gli occhi del modello cadono già entro 3 pixel
  da quelli del disegno, il mento del foglio è 17 mm più in basso (viso più lungo sotto la bocca): la corrispondenza è
  a tratti fra quei punti, poi una deformazione morbida esatta sui punti;
- pelle pulita come il viso di Ren, con i tratti del disegno (occhi viola, sopracciglia, ombra del naso, bocca e ombra
  del labbro, l'ombra sotto il mento): le altre ombre del foglio sono quelle delle ciocche disegnate sopra il viso, che
  sul modello sono altrove (sulle tempie diventavano strisce marroni);
- la metà destra sopra il naso è il riflesso della sinistra (nel foglio una ciocca copre il sopracciglio e l'occhio
  destro; senza, l'occhio destro spariva);
- tutto in luce piatta. Le viste di tre quarti non dipingono: le loro ombre sulle guance cadono in altri punti e dove si
  incontravano col davanti facevano strisce.
- Errori trovati e corretti guardando: occhio destro sparito (il suo bianco toccava la ciocca), righe della ciocca sul
  sopracciglio, strisce marroni sulle tempie, tratti di Meshy rimasti ai lati del viso e sotto il mento.

## Braccia dai fogli (`tools/kael_arms.py`, 10/11)
Denis: "tutto il resto cerca di farlo identico come nelle foto, soprattutto viso e capelli e braccia" (tuta, tatuaggi e
guanti neri come sono). Lo scanner (`tools/sheet_scan.py`, inquadrature in `docs/meshy/kael_scan.json`) mostrava le
braccia di Meshy pallide e a schizzi, con scarabocchi neri sulle spalle, e un po' più larghe del disegno.
- La pelle di spalle, braccia e gomiti è tutta ridipinta: dal disegno di fronte (`kael_nero.png`), dal retro
  (`kael_retro.png`) e dalle viste di tre quarti del busto (`kael_busto_3viste.png`, a ±30°: il lato esterno del
  braccio, quello che si vede di più in gioco); ogni punto prende la vista che guarda di più, con un passaggio stretto
  (niente righe doppie). Dove nessun disegno arriva (cima della spalla, sotto il braccio) la pelle in luce del disegno.
- Ogni braccio è allineato al suo disegno (rotazione, scala e spostamento: sovrapposizione dal 72-86% all'88-94%).
- I tatuaggi viola dei fogli diventano neri come quelli di `kael_nero.png`. Il bracciale, il guanto, la tuta e la
  punta del colletto non si toccano.
- Luce piatta sulla pelle dipinta (le ombre sono quelle disegnate), come la parte davanti del corpo di Ren.
- Errori trovati e corretti guardando in 3D: righe chiare lungo le cuciture della texture (i vertici doppi sulle
  cuciture facevano fallire il controllo di visibilità), una macchia marrone al gomito (il colore del bordo del
  disegno), trattini neri di Meshy vicino ai bracciali, una macchia color pelle sulla punta del colletto (pesata sulle
  ossa del braccio: ora esclusa).

## Look nel gioco
`CFG.looks.kael` in `src/a0_cfg.js`: pugni sulle sue dita (aperti nello speciale e nella presa), contorno come Ren,
luce lisciata, testa alzata di 12° in guardia, la guardia `a191` che respira di Ren, `faceShape` (la ciocca alzata),
`flatFace` (capelli e viso in luce piatta), `paint` (`kael_painted.jpg`, la pittura pulita; il pulsante "Meshy"
dell'anteprima mostra quella originale).

## Per dopo
- Le code della fascia sono attaccate ai pantaloni (le ha fatte così Meshy): seguono le gambe, non oscillano. Se Denis
  le vuole libere come quelle di Ren, si fanno coi nastri (`CFG.looks.ren.sash`).
- Il nero della tuta resta quello di Meshy (in due toni diventava granuloso).
- I tatuaggi del disegno di fronte (fiamme) e quelli dei fogli (fulmini) non sono uguali: davanti fiamme, di lato e
  dietro fulmini. Se Denis vuole un solo disegno, si dipinge quello su tutta la spalla.
- I capelli hanno la forma di Meshy (ciocche a punte), non quella del foglio (massa morbida e larga); le orecchie del
  foglio con gli orecchini a goccia non ci sono (le copre la forma dei capelli). Senza Meshy si possono solo ridipingere.
