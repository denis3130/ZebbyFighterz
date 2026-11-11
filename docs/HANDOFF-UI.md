# Passaggio di consegne — Interfaccia (UI/UX) di Voidrise

- Design: `docs/superpowers/specs/2026-11-11-voidrise-interfaccia-design.md`. Piano U1: `docs/superpowers/plans/2026-11-11-voidrise-interfaccia-u1.md`.
- Riferimenti visivi: **solo** `docs/ref/ui/00-…04-*.png` (stile scuro, oro e arancione, caratteri con le grazie). Denis: nessun'altra immagine, mai le schede in A-pose di `docs/ref/personaggi/`.
- Ramo: `claude/cool-fermi-fkx4iq`, partito da `tappa2-ren-meshy` (la linea principale del gioco, Ren di Meshy acceso). Non è unito a nessun altro ramo.

## Dove siamo (U1 finita, 11/11/2026)
Il percorso completo funziona su touch, mouse, tastiera e controller:
**intro** (Ren e Kael si scontrano, «Salta») → **titolo** («Tocca per iniziare» / «Premi un tasto» / «Premi A») → **nome** al primo avvio (tastiera a lettere per il controller) → **menu principale** (Gioca con Arcade, Online, Versus locale; Allenamento; Profilo, Pass, Impostazioni «In arrivo») → **Versus locale** (round 1/3/5, tempo 60/90/99/∞, salvati nella partita) → **selezione personaggi** (12 posti: Ren e Kael, Astra e Raigon bloccati dal pass, 8 «In arrivo»; G1 poi G2; niente scontro speculare) → **arena** (la Grande Cascata, con una foto della vera arena; le altre «In arrivo») → **VS** (volti, battute, caricamento vero) → **lotta vera** con i personaggi scelti → **risultati** (Vittoria/Pareggio, punteggio, XP voce per voce, livello) → Rivincita / Cambia personaggio / Menu.
- Pausa nel nuovo sistema: Riprendi, Ricomincia, Avversario (allenamento), FPS, Abbandona (con conferma). Durante la pausa l'HUD è nascosto.
- Salvataggio sul dispositivo (`voidrise.save`): nome, XP e livello, statistiche del G1, ultimo personaggio, impostazioni (la scelta degli FPS di `voidrise.prefs` viene portata qui).

## Come provarlo
- Pagina: vedi `CLAUDE.md` («Interfaccia»). Sul telefono in orizzontale; `?fps=1` nell'indirizzo mostra gli FPS.
- Build: `bash mk.sh` (deve stampare `SYNTAX_OK`). Immagini segnaposto: `python3 tools/make_ui_assets.py`.
- Test dell'interfaccia (oltre a quelli del gioco in `docs/HANDOFF.md`, adattati ai nuovi percorsi con le stesse intenzioni: `menu`, `touch`, `orient`, `hud`, `round`, `play_check`):
```
for f in ui_base ui_save ui_nav ui_comp ui_layers ui_intro ui_title ui_menu ui_select ui_flow ui_results; do python3 tests/run.py tests/$f.test.js || break; done
for v in 640x360 844x390 1280x720 1920x1080; do python3 tests/run.py tests/ui_layout.test.js --viewport $v || break; done
python3 tests/run.py tests/ui_touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/ui_perf.test.js --viewport 844x390
```

## Architettura in poche righe
- File nuovi in `src/`: `a1_ui_cfg.js` (numeri: `CFG.ui`, `CFG.prog`), `u_style.css` (stile, incollato da `build.py` con `<!--include:u_style.css-->`), `u0_save.js` (salvataggio), `u7_prog.js` (XP, livelli, statistiche), `u1_nav.js` (schermate, pila, fuoco 2D, input dei menu), `u2_comp.js` (componenti), `u3_layers.js` (scena a strati), `u4_intro.js` (intro, titolo, nome), `u5_play.js` (menu, Versus, selezione, arena, VS, risultati), `u9_bridge.js` (ponte verso la lotta).
- Toccati nel gioco: `c1_sim.js` (round e tempo nello stato: `S.need`, `S.timeS`, interi), `d_render.js` (`F3D_BY`, `renderCast`), `f_fx.js` (colori originali sul lottatore: `it.em0`, `fxRecast`), `g_hud.js` (volti dell'interfaccia), `h_menu.js` (pausa e ciclo sul nuovo sistema), `z_main.js` (avvio sull'intro, `uiFrame` nei menu, `uiEvents` nel passo, `G.opts`), `head.html`, `build.py` (`.webp`, include), `mk.sh`.
- Una schermata è `{id, scene, layers, build, enter, leave, back, tab, onFocus, frame, any, guardMs}` registrata con `navRegister`; si naviga con `navGo` / `navBack` / `navReset`. Il fuoco va all'elemento `data-focus` più vicino nella direzione; tocco e clic confermano al rilascio, un doppio tocco non salta due schermate.
- **Lezione**: niente animazioni CSS infinite nella pagina (rallentavano i fotogrammi della lotta anche quando erano nascoste: prova a raffica da 1,4 a 22-25 ms). Tutto il movimento dei menu (nuvole, nebbia, respiro, intro, contatori) è calcolato in JavaScript solo mentre un menu è aperto. Un test lo controlla.
- I menu non disegnano più l'arena 3D (gli strati la coprono): la preparazione grafica si fa nel caricamento del VS (`bridgeWarm`), così i primi istanti della lotta non scattano.

## Misure (Chromium headless con SwiftShader, 844x390: solo di riferimento, non è un telefono)
- Prima dell'interfaccia: un `tick` nei menu 0,20 ms; in lotta 2,36 ms; serie del gioco 21 comandi verdi.
- Dopo: un `tick` nei menu **0,05-0,09 ms** in qualità alta, 0,00-0,01 in bassa; un fotogramma dell'intro all'impatto 0,07-0,10 ms di JavaScript; in lotta 2,1-2,5 ms.
- Lotta, FPS nel ciclo reale: primi 5 s **20,4** con la preparazione del VS (20,6 prima dell'interfaccia, 19,2 senza preparazione); a regime 24,5 contro 25,3 (dentro il rumore).
- Immagini dell'interfaccia: 604 KB (WebP), circa 0,8 MB dentro la pagina.
- **FPS veri sul telefono: da misurare** (`?fps=1` o pausa → «FPS: Sì»), sia nei menu sia in lotta.

## Immagini segnaposto da sostituire (`assets/ui/`, stessi nomi = nessun cambio di codice)
Tutte ritagliate o ricavate dai 5 riferimenti dell'interfaccia. Le definitive vanno generate a pezzi separati in alta risoluzione (Blueprint Studio è installato e la rete è aperta, ma si collega solo in una sessione nuova e chiede l'accesso: prima di spendere crediti mostrare saldo e costo a Denis).

| File | Ora | Definitiva |
|---|---|---|
| `sky.webp` | le rovine al tramonto dietro «Scegli l'arena» | cielo e rovine lontane |
| `ruins.webp` | manca: lo strato vicino è vuoto | archi e pavimento in primo piano, trasparente |
| `clouds.webp`, `fog1/2.webp` | disegnate in codice | possono restare |
| `ren_full.webp`, `kael_full.webp` | Ren del menu, Kael delle impostazioni, col loro fondo sfumato | a mezzo busto, scontornati |
| `ren_vs.webp`, `kael_vs.webp` | i volti del VS (anche ai lati del titolo) | volti grandi scontornati |
| `ren_win.webp` | Ren col pugno alzato di «Vittoria» | idem per Kael (manca: ora usa `kael_full`) |
| `face_*.webp` | volti del VS e del pass | ritratti quadrati |
| `intro_clash.webp` | il pugno contro pugno dell'intro | alta risoluzione, a strati se possibile |
| `arena_*.webp`, `card_*.webp` | miniature dei riferimenti | anteprime delle arene vere |
| `silhouette.webp` | disegnata in codice | sagoma «In arrivo» |

## Scelte
- Le pagine costruite (`index.html`, `play/`) entrano nei commit solo quando si pubblica: ogni build pesa circa 10 MB.
- Ogni decisione presa durante il lavoro è nel registro dell'esecuzione (righe «Ruling»), riassunta a Denis alla consegna.

## Per dopo (annotato, non costruito)
- U2: HUD della lotta nel nuovo stile (i pallini dei round sono ancora 2: con 5 round ne servono 3), tasti touch, pausa completa (Lista mosse, Impostazioni), «Gira il telefono» nel nuovo stile.
- U3: Profilo, Statistiche, Classifica, Impostazioni (la qualità Auto/Bassa/Media/Alta è già nel codice). U4: Pass, Missioni, Archivio, Sblocco. U5: Arcade, Tutorial, schermate Online.
- Acquisto del Premium dagli store (Google Play, App Store, Steam) con controllo delle ricevute su un server; online e classifica globale; negozio; altre lingue; musica e suoni; scelta simultanea dei personaggi con due dispositivi; scontro speculare (seconda copia del modello e colore alternativo); intro con i modelli 3D; Astra e Raigon giocabili.
- Il VS non ha un pulsante «Indietro» a schermo (come nel riferimento): Esc / B tornano all'arena; dura 2,5 s.

## Prossimo passo
Denis prova la pagina sul telefono (percorso intero fino ai risultati) e dice cosa cambiare. Poi U2 (HUD della lotta e pausa completa) o le immagini definitive, a sua scelta.
