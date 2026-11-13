# Passaggio di consegne — Interfaccia (UI/UX) di Voidrise

- Design: `docs/superpowers/specs/2026-11-11-voidrise-interfaccia-design.md`. Piano U1: `docs/superpowers/plans/2026-11-11-voidrise-interfaccia-u1.md`.
- Riferimenti visivi: **solo** `docs/ref/ui/00-…04-*.png` (stile scuro, oro e arancione, caratteri con le grazie). Denis: nessun'altra immagine, mai le schede in A-pose di `docs/ref/personaggi/`.
- Ramo: `claude/cool-fermi-fkx4iq`, partito da `tappa2-ren-meshy` (la linea principale del gioco, Ren di Meshy acceso). Non è unito a nessun altro ramo.

## Giro di miglioramenti (12/11/2026, dopo la prova di Denis: «è ancora fatta male», «immagini sgranate, poco vivo, la lotta stona», «la intro fa schifo»)
- **Intro nuova** (5,2 s, senza primi piani, come ha scelto Denis): Ren e Kael arrivano dai lati coi pugni carichi, si guardano, caricano e affondano; impatto con lampo, fotogramma d'impatto (sagome nere sul bianco), anelli d'urto, fulmini, scintille, sassi e tremolio; spinta al rallentatore con le due energie (arancio e viola); esplosione bianca; il logo compare dove lo tiene il titolo e il titolo segue senza stacco. I due sono le metà dello scontro del riferimento 00 (`intro_ren`, `intro_kael`, posizioni in `CFG.ui.intro`).
- **Immagini nitide**: ogni immagine presa dai riferimenti è ingrandita 4 volte (Real-ESRGAN anime) e ogni personaggio è scontornato (IS-Net anime) da `tools/make_ui_assets.py` (modelli: `bash tools/fetch_ui_models.sh`; risultati in cache in `~/.cache/voidrise-ui`). Titolo, VS e risultati mettono i volti al loro posto con la tabella `CFG.ui.art` (dove sta il volto in ogni immagine): con le immagini definitive basta cambiare quei numeri.
- **Più vita** (tutto da JavaScript): cielo che si muove piano, raggi di luce, personaggi che entrano dal loro lato, aura del colore dell'eroe; VS che «sbatte» (volti dai lati, scritta che cade con lampo, tremolio e scintille); risultati con «Vittoria» che arriva da grande e scintille; luccichio dorato sul logo; luce che ripassa sul pulsante col fuoco; aure che lampeggiano nella selezione. Scintille su `#uiFx`, acceso solo finché vivono.
- **HUD della lotta e tasti touch** nello stile dell'interfaccia (riferimento 02): ritratti obliqui con cornice d'oro, nomi con le grazie, barre sottili, tempo nell'esagono, «N COLPI» con pennellata, scritte dorate, tasti in vetro scuro con anello d'oro. Stessi id: le prove del gioco non cambiano.
- Corretto: l'arco e il taglio del logo del menu finivano sopra la testa di Ren sui telefoni.
- **Revisione indipendente** del giro (12/11): corretti il ritratto di Kael nell'HUD (ritaglio specchiato), il centro della scritta VS, la luce di Ren che sbordava sul lato di Kael nell'intro, una prova delle scintille che passava per il motivo sbagliato, la pennellata del fuoco che riavviava una transizione a ogni fotogramma, il logo rifatto dopo un «Salta» tardivo, l'ancora dei volti rimasta vecchia, il lavoro nascosto sotto l'intro, la cache delle immagini e i bordi tagliati dei personaggi; l'intro ora aspetta se il telefono chiede di essere girato. Il punto principale era la fluidità: vedi «Misure».
- **Fluidità**: i livelli che si muovono ogni fotogramma stanno sulla scheda grafica (`will-change`, solo quelli che la scena mostra); le scie e le luci dell'intro sono immagini pronte disegnate sul canvas; il VS dopo l'entrata sta fermo; le scritte dei round non hanno più il filtro d'ombra (costava fotogrammi a ogni inizio round). Il contatore FPS ora si vede sopra ogni schermata.

## Dove siamo (U1 finita, 11/11/2026)
Il percorso completo funziona su touch, mouse, tastiera e controller:
**intro** (Ren e Kael si scontrano, «Salta») → **titolo** («Tocca per iniziare» / «Premi un tasto» / «Premi A») → **nome** al primo avvio (tastiera a lettere per il controller) → **menu principale** (Gioca con Arcade, Online, Versus locale; Allenamento; Profilo, Pass, Impostazioni «In arrivo») → **Versus locale** (round 1/3/5, tempo 60/90/99/∞, salvati nella partita) → **selezione personaggi** (12 posti: Ren e Kael, Astra e Raigon bloccati dal pass, 8 «In arrivo»; G1 poi G2; niente scontro speculare) → **arena** (la Grande Cascata, con una foto della vera arena; le altre «In arrivo») → **VS** (volti, battute, caricamento vero) → **lotta vera** con i personaggi scelti → **risultati** (Vittoria/Pareggio, punteggio, XP voce per voce, livello) → Rivincita / Cambia personaggio / Menu.
- Pausa nel nuovo sistema: Riprendi, Ricomincia, Avversario (allenamento), FPS, Abbandona (con conferma). Durante la pausa l'HUD è nascosto.
- Salvataggio sul dispositivo (`voidrise.save`): nome, XP e livello, statistiche del G1, ultimo personaggio, impostazioni (la scelta degli FPS di `voidrise.prefs` viene portata qui).

## Come provarlo
- Pagina: https://claude.ai/artifact/PSAtwRuNWi6XUCg5uj2zR6 (pagina Claude «Voidrise Interfaccia», privata finché Denis non la condivide). Sul telefono in orizzontale; per gli FPS: pausa → «FPS: Sì».
- Build: `bash mk.sh` (deve stampare `SYNTAX_OK`). Immagini segnaposto: `python3 tools/make_ui_assets.py`.
- Test dell'interfaccia (oltre a quelli del gioco in `docs/HANDOFF.md`, adattati ai nuovi percorsi con le stesse intenzioni: `menu`, `touch`, `orient`, `hud`, `round`, `play_check`):
```
for f in ui_base ui_save ui_nav ui_comp ui_layers ui_intro ui_title ui_menu ui_select ui_flow ui_results ui_life ui_hud; do python3 tests/run.py tests/$f.test.js || break; done
python3 tests/run.py tests/ui_fps.test.js --viewport 844x390   # FPS nel ciclo vero (solo da confrontare tra versioni)
for v in 640x360 844x390 1280x720 1920x1080; do python3 tests/run.py tests/ui_layout.test.js --viewport $v || break; done
python3 tests/run.py tests/ui_touch.test.js --viewport 844x390 --touch --mobile
python3 tests/run.py tests/ui_perf.test.js --viewport 844x390
```

## Architettura in poche righe
- File nuovi in `src/`: `a1_ui_cfg.js` (numeri: `CFG.ui` con `art` = dove stanno i volti nelle immagini e `intro` = lo scontro, `CFG.prog`), `u_style.css` (stile, incollato da `build.py` con `<!--include:u_style.css-->`), `u0_save.js` (salvataggio), `u7_prog.js` (XP, livelli, statistiche), `u1_nav.js` (schermate, pila, fuoco 2D, input dei menu), `u2_comp.js` (componenti), `u3_layers.js` (scena a strati), `u4_intro.js` (intro, titolo, nome), `u5_play.js` (menu, Versus, selezione, arena, VS, risultati), `u9_bridge.js` (ponte verso la lotta).
- Toccati nel gioco: `c1_sim.js` (round e tempo nello stato: `S.need`, `S.timeS`, interi), `d_render.js` (`F3D_BY`, `renderCast`), `f_fx.js` (colori originali sul lottatore: `it.em0`, `fxRecast`), `g_hud.js` (volti dell'interfaccia), `h_menu.js` (pausa e ciclo sul nuovo sistema), `z_main.js` (avvio sull'intro, `uiFrame` nei menu, `uiEvents` nel passo, `G.opts`), `head.html`, `build.py` (`.webp`, include), `mk.sh`.
- Una schermata è `{id, scene, layers, build, enter, leave, back, tab, onFocus, frame, any, guardMs}` registrata con `navRegister`; si naviga con `navGo` / `navBack` / `navReset`. Il fuoco va all'elemento `data-focus` più vicino nella direzione; tocco e clic confermano al rilascio, un doppio tocco non salta due schermate.
- **Lezione**: niente animazioni CSS infinite nella pagina (rallentavano i fotogrammi della lotta anche quando erano nascoste: prova a raffica da 1,4 a 22-25 ms). Tutto il movimento dei menu (nuvole, nebbia, respiro, intro, contatori) è calcolato in JavaScript solo mentre un menu è aperto. Un test lo controlla.
- I menu non disegnano più l'arena 3D (gli strati la coprono): la preparazione grafica si fa nel caricamento del VS (`bridgeWarm`), così i primi istanti della lotta non scattano.
- L'intro è una funzione pura del tempo (`introAt(ms)`): due canvas (dietro e davanti ai lottatori, al massimo 1,5 pixel per pixel CSS) per scie, anelli, fulmini, scintille e sassi, tutti da numeri con seme. La vita dei menu è in `u3_layers.js` (`lyMotion`, `layersBurst`, `uiFocusLife`, `uiLogoLife`), quella del VS e dei risultati in `u5_play.js` (`vsLife`, `rsLife`).
- L'HUD della lotta nel nuovo stile è una sezione in fondo a `u_style.css` che sovrascrive solo l'aspetto di quello di `head.html`.

## Misure del giro di miglioramenti (12/11, stesso browser simulato, 844x390, prima = la versione U1 pubblicata l'11/11, alternate)
- FPS nel ciclo vero (`tests/ui_fps.test.js`): intro **34** contro 27; menu **37-39** contro 29; VS dopo l'entrata **41-44** contro 38,5 (entrata 12-14 contro 14); lotta, primi 5 s **21-23** contro 22-24 (dentro il rumore; a regime 27 in entrambe).
- Un `tick` nei menu: 0,06 ms (come prima). Un fotogramma dell'intro all'impatto: 0,2-0,3 ms di JavaScript.
- Il K.O. arriva negli stessi fotogrammi di prima (1040 con hitstop, 988 senza): le lotte non sono più lunghe.
- Immagini dell'interfaccia: 1,34 MB (WebP), 1,83 MB dentro la pagina.

## Misure U1 (Chromium headless con SwiftShader, 844x390: solo di riferimento, non è un telefono)
- Prima dell'interfaccia: un `tick` nei menu 0,20 ms; in lotta 2,36 ms; serie del gioco 21 comandi verdi.
- Dopo: un `tick` nei menu **0,05-0,09 ms** in qualità alta, 0,00-0,01 in bassa; un fotogramma dell'intro all'impatto 0,07-0,10 ms di JavaScript; in lotta 2,1-2,7 ms.
- Serie completa finale (gioco + interfaccia): **38 comandi, 453 prove, 0 errori**, più `play_check`; il KO arriva negli stessi fotogrammi di prima (1040 con hitstop contro 988 senza).
- Lotta, FPS nel ciclo reale: primi 5 s **20,4** con la preparazione del VS (20,6 prima dell'interfaccia, 19,2 senza preparazione); a regime 24,5 contro 25,3 (dentro il rumore).
- Immagini dell'interfaccia: 604 KB (WebP), circa 0,8 MB dentro la pagina.
- **FPS veri sul telefono: da misurare** (`?fps=1` o pausa → «FPS: Sì»), sia nei menu sia in lotta.

## Immagini segnaposto da sostituire (`assets/ui/`, stessi nomi = nessun cambio di codice)
Tutte ritagliate o ricavate dai 5 riferimenti dell'interfaccia, ingrandite 4 volte; i personaggi scontornati (per le definitive aggiornare anche `CFG.ui.art`). Le definitive vanno generate a pezzi separati in alta risoluzione (Blueprint Studio è installato e la rete è aperta, ma si collega solo in una sessione nuova e chiede l'accesso: prima di spendere crediti mostrare saldo e costo a Denis).

| File | Ora | Definitiva |
|---|---|---|
| `sky.webp` | le rovine al tramonto dietro «Scegli l'arena» | cielo e rovine lontane |
| `ruins.webp` | manca: lo strato vicino è vuoto | archi e pavimento in primo piano, trasparente |
| `clouds.webp`, `fog1/2.webp` | disegnate in codice | possono restare |
| `ren_full.webp`, `kael_full.webp` | Ren del menu, Kael delle impostazioni, scontornati | a mezzo busto, scontornati |
| `ren_vs.webp`, `kael_vs.webp` | i volti del VS (anche ai lati del titolo) | volti grandi scontornati |
| `ren_win.webp` | Ren col pugno alzato di «Vittoria» | idem per Kael (manca: ora usa `kael_full`) |
| `face_*.webp` | volti del VS e del pass | ritratti quadrati |
| `intro_ren.webp`, `intro_kael.webp` | le due metà del pugno contro pugno del riferimento 00 (il pugno di Ren è nascosto dietro quello di Kael: nella corsa lo copre la luce del pugno carico) | i due in corsa, a strati, col pugno di Ren intero |
| `arena_*.webp`, `card_*.webp` | miniature dei riferimenti | anteprime delle arene vere |
| `silhouette.webp` | disegnata in codice | sagoma «In arrivo» |

## Scelte
- Le pagine costruite (`index.html`, `play/`) entrano nei commit solo quando si pubblica: ogni build pesa circa 10 MB.
- Ogni decisione presa durante il lavoro è nel registro dell'esecuzione (righe «Ruling»), riassunta a Denis alla consegna.

## Per dopo (annotato, non costruito)
- Titolo su schermi 4:3 (tablet): i volti vanno bene ma il logo si stringe tra loro; Kael non ha una posa di vittoria nei riferimenti (nei risultati usa quella delle impostazioni).
- L'arena della lotta è luminosa e di giorno, l'interfaccia è al tramonto: l'HUD ora ha lo stesso stile, il resto dipende dalla grafica della lotta (l'altra sessione).
- U3: Profilo, Statistiche, Classifica, Impostazioni (la qualità Auto/Bassa/Media/Alta è già nel codice). U4: Pass, Missioni, Archivio, Sblocco. U5: Arcade, Tutorial, schermate Online.
- Acquisto del Premium dagli store (Google Play, App Store, Steam) con controllo delle ricevute su un server; online e classifica globale; negozio; altre lingue; musica e suoni; scelta simultanea dei personaggi con due dispositivi; scontro speculare (seconda copia del modello e colore alternativo); intro con i modelli 3D; Astra e Raigon giocabili.
- Il VS non ha un pulsante «Indietro» a schermo (come nel riferimento): Esc / B tornano all'arena; dura 2,5 s.

## U2 (13/11): pausa completa, round, «Gira il telefono»
- **Pausa** come il riferimento 03: Riprendi, **Lista mosse**, **Impostazioni**, Ricomincia, Avversario (allenamento), Abbandona.
  Mosse e impostazioni si aprono senza lasciare la lotta (resta in pausa sotto un velo scuro); Esc / B tornano alla pausa.
- **Lista mosse** (`src/u6_meta.js`, `META_MOVES`): 12 mosse della Tappa 1 con i comandi di Tocco / Tastiera / Controller;
  si apre sul dispositivo in uso, le linguette mostrano gli altri.
- **Impostazioni** (anche dal menu principale, non più «In arrivo»): Audio (Musica / Effetti salvati, «suoni in arrivo»),
  Grafica (Qualità Auto/Bassa/Media/Alta applicata subito; contatore FPS, spostato qui dalla pausa), Comandi (i tasti dei tre
  dispositivi; spostarli è in arrivo), Lingua (Italiano; altre in arrivo). Ogni scelta si applica e si salva subito: niente
  «Salva» (scelta di questa tappa, il riferimento 03 lo mostra: si può aggiungere con l'editor dei comandi della U3).
- **Pallini dei round**: uno per round da vincere (1, 2 o 3 con 1, 3 o 5 round), rifatti a ogni partita (`hudReset`).
- **«Gira il telefono»** nello stile dell'interfaccia; il telefono gira da JavaScript (`mnRotLoop`) solo mentre la schermata si
  vede (prima era un'animazione CSS infinita); in lotta dice che la partita è in pausa.
- Prove: `tests/ui_u2.test.js` (10, anche a 640×360 … 1920×1080); `menu.test.js` apre l'FPS da Impostazioni → Grafica.

## U3, prima parte (13/11): Profilo
- **Profilo** dal menu principale (`src/u6_meta.js`, `metaProfileScreen`), riferimento 03: Profilo | Statistiche | Classifica.
  Profilo = ritratto tondo (scelta Ren / Kael salvata in `SV.avatar`, usata anche dal chip del menu), nome, livello, barra XP,
  «Cambia nome» (la schermata del nome torna al profilo), vittorie / sconfitte / pareggi / percentuale (— senza partite).
  Statistiche = totali e per lottatore dal salvataggio. Classifica = «arriva con le partite online» e il record personale:
  nessun nome inventato (regola del design §1).
- Prove: `tests/ui_u3.test.js` (7). Restano per la U3: l'editor dei comandi touch e la riassegnazione dei tasti.
- **Fuoco nelle liste** (`navBest`, `u1_nav.js`): la distanza «di traverso» ora è 0 finché il candidato si sovrappone
  all'elemento col fuoco (stessa colonna o riga, qualunque la larghezza) più un po' dello scarto dei centri. Prima, da «Gioca»
  la freccia giù saltava ad «Allenamento» o a «Profilo» a seconda di quanto erano lunghe le parole (si è visto togliendo il
  lucchetto a Profilo).

## Intro filmata (13/11, dallo storyboard di Denis)
- **L'intro ora è un video**: `assets/ui/video/intro.mp4` (960×432, 32 fps, 4,5 s, 0,6 MB). Ren e Kael si alzano in guardia,
  scattano e si colpiscono in faccia insieme (Ren col sinistro, Kael col destro); poi lampo bianco, il logo dell'intro disegnata
  e il titolo, come prima. In tutto circa 5,8 s; «Salta» e il tocco/tasto (dopo la prima volta) restano uguali.
- 13/11 sera, dopo la prova di Denis («lo scenario a volte si muove altre no»): clip rifatte con lo sfondo sempre in
  movimento (`c1v` 1103 + `fin2v` 1103, misurate fotogramma per fotogramma) e il bianco finale che sale sugli ultimi 400 ms
  del video ancora in movimento, invece che sopra l'ultimo fotogramma fermo.
- Fatto sul PC di Denis con ComfyUI (Wan 2.2 14B, primo e ultimo fotogramma) dai suoi fotogrammi chiave `docs/ref/intro/`
  (`partenza.png`, `storyboard.png`); scelte, bozze e script in `docs/comfy/ANIMAZIONI.md`. Denis ha scelto di togliere la parata.
- Codice: `src/u4_intro.js` (`inVideoBuild`, `introVideoAt`, `introMode`): il video è nella pagina come data URI e parte da un
  blob, muto e in linea; si ferma quando si lascia l'intro, con «Gira il telefono» e a pagina nascosta. Se non è pronto entro
  `CFG.ui.intro.video.wait` (1,5 s) parte l'intro disegnata, che resta intera (`video.on: false` la rimette). Numeri in
  `CFG.ui.intro.video` (`hit` = quando i pugni arrivano in faccia: lampo e tremolio). `build.py` accetta `.mp4`.
- Prove: `tests/ui_video.test.js` (12); `ui_intro.test.js` prova l'intro disegnata con il video spento.
- FPS nel ciclo vero (`ui_fps`, 844×390, Chrome di Windows senza scheda video, solo da confrontare): intro **68** contro 38,8
  (il video costa meno dei canvas dell'intro disegnata), menu 45 contro 38, VS 21,6 contro 23,6, lotta 41 contro 41,8 (rumore).
- Sul PC di Windows la serie gira con il Chrome di sistema (`run.py` e `play_check.py` lo cercano in `C:/Program Files/...`)
  e Node portatile per `mk.sh`; con `PYTHONIOENCODING=utf-8` (la console di Windows non stampa le frecce dei nomi delle prove).
- Già prima di questo lavoro (provato sulla versione precedente): `touch.test.js` «stick thresholds and knob clamp» fallisce
  di 1,2 px sulla levetta ricentrata (98,8 contro 100 ±1) in Chrome per Windows. Da guardare (per dopo).

## Animazioni con ComfyUI (12/11, scelta di Denis)
Denis genera le animazioni sul suo PC (RTX 3060 12 GB) con ComfyUI, partendo da immagini che manda lui: intro col pugno vero
(primo e ultimo fotogramma), personaggi vivi nei menu e sfondi in ciclo. Guida, prompt e impostazioni: `docs/comfy/ANIMAZIONI.md`.

## Prossimo passo
Denis prova sul telefono l'intro filmata e la U2 (pausa, Lista mosse, Impostazioni). Poi U3: Profilo, Statistiche, Classifica e l'editor dei comandi (riferimento 03).
