# Voidrise Fighters — Arene 3D, tappa A1 "La Grande Cascata in 3D"

Data: 11/11/2026 · Scelte di Denis in chat: arene in **3D vero**, metodo **misto** (vicino in 3D, lontano strati dipinti), prima tappa **solo la Cascata**, strati lontani **tagliati dal disegno attuale**. Parte 1 (cosa si vede) approvata ("ok inizia").
Ramo: `claude/festive-volta-756gmk`, partito da `tappa2-ren-meshy` (11/11, commit 31551bd).

## 1. Obiettivo

Sostituire il fondale dipinto piatto della Cascata con un'arena in 3D: profondità vera quando la telecamera si muove, stesso look del disegno approvato (`docs/ref/sfondo-cascata.png`), stesso stile dei lottatori (toon a 3 fasce, contorno nero). È la base per le arene successive (Rovine, scelta dell'arena), che saranno la tappa A2.

Successo:
- l'arena si legge come il disegno, ma colonna, lanterna e pavimento sono oggetti 3D che scorrono davanti alle rupi, e le rupi davanti al cielo;
- nessun buco o bordo visibile in nessuna inquadratura del gioco (distanza da `dist0` a `distMax`, `cam.x` fino a ±`xMax`, super salto, tremolio, schermi da 4:3 a 21:9);
- la lotta è identica: la logica non cambia, la durata media del round non cambia;
- il costo misurato per fotogramma resta vicino a quello di oggi (vedi 5).

## 2. Cosa si vede

**Vicino, in 3D** (metri; i lottatori stanno a z ≈ 0, la telecamera guarda verso −z):
- **Terrazza di lastre di pietra**: x da −14 a +14, z da +3 (davanti, fuori dall'inquadratura in basso) a −3,5 (bordo dietro). Lastre come blocchi bassi smussati (le facce di sopra a y = 0, piccole differenze di colore e di inclinazione solo visive, mai sopra 1 cm), fughe scure, erba in qualche crepa. Bordo di dietro: un gradino di pietra con ciuffi d'erba, poi il vuoto sulla nebbia.
- **Sinistra**: colonna rotta (cima spezzata, edera verde) con un'asta e lo **stendardo rosso** strappato in basso, che sventola (griglia di punti con gravità e vento, solo grafica, un passo per fotogramma disegnato). Posizione di partenza x −5, z −2,6: al bordo sinistro quando la telecamera è al centro, come nel disegno.
- **Destra**: **lanterna di pietra** (base, fusto, camera della luce, tetto con il pomo, muschio), x +5,2, z −2,8. Qualche roccia e cespuglio vicino a colonna e lanterna.
- Le **foglie** di oggi restano (metà davanti e metà dietro i lottatori).
- **Ombre**: restano i dischi scuri sotto i lottatori, ora sulle lastre 3D.
- Luce: sole caldo da in alto a sinistra, come nel disegno; toon a 3 fasce con la stessa texture a gradini dei lottatori; contorno nero con il guscio rovesciato come in `e_fighter3d.js`, più sottile sugli oggetti lontani.
- Le texture della pietra, dell'erba e dello stendardo sono dipinte nel codice su canvas (macchie, crepe, muschio) con i colori presi dal disegno. Niente file in più.

**Lontano, strati dipinti** tagliati dal disegno, ognuno su un piano grande a una sua distanza:
- **Cielo con le nuvole** (z −70): le nuvole scorrono piano (spostamento della texture).
- **Rupi con la cascata grande** (z −30): l'acqua scorre con lo stesso shader di oggi (maschera dell'acqua, strisce, tremolio).
- **Nebbia** (z −12, trasparente): sale dal fondo della cascata e copre il bordo basso delle rupi; ondeggia lenta.

I piani sono abbastanza grandi da coprire ogni inquadratura del gioco (calcolati dalle posizioni estreme della telecamera, con margine per il tremolio). Il risultato visivo da raggiungere: alla telecamera di partenza (`dist0`, `cam.x` 0, 844×390) l'arena assomiglia al disegno di oggi.

## 3. Come è fatto

**File nuovi**
- `tools/make_layers.py` (Pillow + numpy, niente OpenCV): da `docs/ref/sfondo-cascata.png` produce `assets/arena/cascata_sky.jpg`, `cascata_cliffs.jpg` + `cascata_cliffs_a.png` (trasparenza), `cascata_mist.png` e `cascata_water.png` (maschera dell'acqua, come quella di oggi ma per lo strato delle rupi). Toglie colonna, stendardo, lanterna, erba davanti e pavimento: i buchi si riempiono allungando i pixel vicini e sfocando (rupi e cielo lì sono poco dettagliati), poi sono comunque coperti per lo più dagli oggetti 3D. Le zone da tagliare sono poligoni scritti nello script. Peso totale degli strati: al massimo 700 KB (oggi `cascata.jpg` + maschera ≈ 330 KB).
- `src/d_arena.js`: costruisce l'arena da una descrizione (`arenaBuild(def)`) e la anima (`arenaStep(nowMs, S)`): strati lontani, terrazza, oggetti, stendardo, nebbia, nuvole. Esporta `ARENA` (vedi sotto). Solo grafica: legge lo stato, non lo cambia.
- `tests/arena.test.js`: i test della sezione 6.

**File cambiati**
- `src/a0_cfg.js`: `CFG.arena` diventa la descrizione dell'arena 3D (`CFG.arenas.cascata`: posizioni, misure, colori, distanze degli strati, vento dello stendardo, velocità di nuvole e nebbia) e `CFG.arenaOn = 'cascata'`. I valori grafici della cascata di oggi (`flow`, `streak`, `wobble`, `contrast`, `lift`) si spostano lì.
- `src/d_render.js`: toglie il fondale piatto (`RD_BG_*`, `rdPlace`, `rdShift`, `rdFootRowY`) e chiama `arenaBuild`/`arenaStep`. Telecamera, `toScreen`, foglie, ombre e lottatori restano. Il tremolio muove solo la telecamera: ora l'arena è nella stessa scena, quindi trema insieme senza correzioni.
- `mk.sh`: `d_arena.js` in `FILES` dopo `d_render.js`; `tools/make_layers.py` non entra nella build (i file prodotti sono nel repository, come oggi).
- `src/v_viewer.js` (anteprima dei personaggi): continua a usare `cascata.jpg` come sfondo CSS. Il file resta nel repository solo per questo.
- `tests/render.test.js`, `tests/feel.test.js`: i test che leggono `ARENA.footRowY` e `uPlace` cambiano (sezione 6).

**Interfaccia `ARENA`** (in `__VF`): `{group (THREE.Group di tutta l'arena), layers: {sky, cliffs, mist} (Mesh), banner (Mesh), leaves (Group, come oggi), waterMat (ShaderMaterial delle rupi), stats() -> {draws, tris}}`.

**Costo, per restare leggeri sul telefono**
- Lastre unite in una sola geometria (un solo disegno), il loro contorno in un'altra; erba con un solo `InstancedMesh`; colonna, lanterna e rocce unite per materiale.
- Obiettivo: arena intera al massimo **25 disegni** e **25.000 triangoli**, texture al massimo 2048 px di lato. Il test lo controlla con `renderer.info`.
- Il calcolo dello stendardo: griglia 10×14 punti, circa 0,05 ms per fotogramma (misurato nel test).

## 4. Cosa non cambia

- Logica: `CFG.stage` (±6 m, muri invisibili), mosse, fisica, round: nessun file `c*_*.js` toccato. `simHash` uguale con e senza arena.
- Telecamera: stessa regola (`CFG.cam`), il suolo resta all'86% dell'altezza dello schermo.
- HUD, menu, input, lottatori, effetti.

## 5. Misure prima e dopo

Con lo stesso metodo della Tappa 2a (Chromium headless, SwiftShader, 844×390, allenamento con il manichino casuale, `readPixels` a ogni fotogramma, 120 fotogrammi, 3 prove): ms per fotogramma **prima** (fondale piatto) e **dopo** (arena 3D). Limite accettato: al massimo +3 ms nella grafica software. Se si supera: meno erba, contorno solo su colonna e lanterna, strati più piccoli. Durata media del round con la sonda di `perf.test.js`: deve restare uguale (la logica non cambia). Gli FPS veri sul telefono li misura Denis dal menu di pausa ("FPS: SÌ").

## 6. Test

`tests/arena.test.js` (lanciato a 640×360, 844×390, 1280×720 e 960×720):
- **Nessun buco**: per una griglia di inquadrature (dist0 e distMax, `cam.x` −3/0/+3, super salto, tremolio massimo) i pixel ai bordi e agli angoli dello schermo non hanno il colore di sfondo del renderer (messo a magenta nel test).
- **Profondità**: spostando `cam.x` di 1 m, un punto della colonna si sposta sullo schermo più di uno delle rupi, e uno delle rupi più di uno del cielo.
- **Piedi sulle lastre**: la cima delle lastre sotto ogni posizione possibile dei lottatori (x da −6 a +6) è a y = 0 entro 1 cm (raggio verticale sulla geometria).
- **L'acqua scorre, la pietra no**: un pixel sulla cascata cambia nel tempo, uno su una lastra no (foglie nascoste).
- **Lo stendardo si muove** e i suoi punti restano numeri finiti dopo 10 minuti simulati.
- **Costo**: `ARENA.stats()` entro 25 disegni e 25.000 triangoli; lo stendardo entro 0,2 ms per fotogramma.
- **La grafica non cambia la logica**: come oggi.

`tests/render.test.js`: "feet stand on the painted floor" e "resize keeps feet on the painted floor" diventano "il suolo resta all'86% dello schermo" (anche dopo il resize); "water flows" e "backdrop covers the whole screen" passano in `arena.test.js`. `tests/feel.test.js`: "the shake moves the painted floor" diventa "il tremolio muove la telecamera e l'arena insieme" (un punto delle lastre e i piedi si spostano dello stesso numero di pixel).

Tutti i test di oggi (comandi in `docs/HANDOFF.md`) devono restare verdi, console senza errori. Prima di mostrarla a Denis: screenshot a 844×390 e 1280×720 nelle inquadrature della griglia, guardati uno per uno (buchi, aloni intorno ai tagli, contorni sbagliati, colori fuori dal disegno), e un confronto affiancato con il fondale di oggi.

## 7. Consegna

Pagina giocabile pubblicata (una pagina Claude nuova "Voidrise · Arena 3D", per non toccare quella del gioco finché Denis non approva), FPS e misure prima/dopo, come provarla. Si unisce al ramo del gioco solo con l'ok di Denis.

## 8. Per dopo (tappa A2 e oltre, non ora)

Rovine dell'acquedotto in 3D con lo stesso sistema; scelta dell'arena prima della lotta (Cascata, Rovine, Casuale) con touch, tastiera e controller; luce diversa per arena (tramonto, notte); oggetti che reagiscono ai colpi (polvere sulle lastre, stendardo che si scuote al K.O.).
