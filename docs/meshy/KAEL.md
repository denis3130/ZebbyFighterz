# Kael di Meshy (10/11/2026)

Kael è fatto da Meshy dal disegno di Denis di lui vestito, `docs/ref/personaggi/kael_nero.png` (tuta nera con le parti
viola, tatuaggi neri sulle spalle; Denis: "eccolo tieni, mi raccomando fallo bene"), con lo scheletro di Meshy, le 25
animazioni di Ren riportate sul suo scheletro, le ossa delle dita e una pulizia fatta da me dopo averlo guardato in 3D
da ogni lato e da vicino (`docs/meshy/CONTROLLI.md`). Il nome nel gioco è **Kael** ("Ken" è di un altro picchiaduro).

I GLB stanno in `meshy/meshy_output/` (fuori dal repository: i link di Meshy scadono). Nel repository c'è il pacchetto
pronto in `wip_assets/kael/`: `mk.sh` lo mette solo nell'anteprima di Kael (`viewer_kael.html`), non nel gioco (il
gioco usa un pacchetto Meshy appena lo trova in `assets/` o `viewer_assets/`: `src/d_render.js`, `modelBuild(c) ||
fighterBuild(c)`). Per metterlo nel gioco: spostare `wip_assets/kael/` in `viewer_assets/kael/`, test, pubblicare.

## Task Meshy e crediti (saldo prima: 1100, dopo: 1000)
| Passo | Task | Crediti |
|---|---|---|
| Corpo senza capelli né vestiti (`kael_base.png`) — superato | image-to-3d `01a1c4dd-548a-70d1-9dad-05e513084c49` | 30 |
| Il suo scheletro — superato | rigging `01a1c4df-3d59-711e-b4e5-2e7f5a85127b` | 5 |
| **Kael vestito** (`kael_nero.png`; meshy-7 standard, texture 2K, A-pose, image enhancement off, luci tolte) | image-to-3d `01a1c53b-d7ee-776a-9170-273efbf5504f` | 30 |
| **Scheletro** (1,8 m) sul modello alleggerito | rigging `01a1c53f-c3ef-76e8-82bd-4186736248a3` | 5 |
| Animazioni: le 25 di Ren, riportate sul suo scheletro | nessun task | 0 |
| **Testa e capelli** dalle 4 immagini di Denis (vedi "Testa da Meshy") | multi-image-to-3d `01a1c6e9-6c56-778a-a146-b95efc0bfed6` | 30 |
| **Totale** | | **100** |

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

## Testa da Meshy (10/11, da approvare): `tools/kael_head.py`
Denis: "se facessimo kael a pezzi su meshy? cioe prima testa e capelli e poi busto e braccia ed infine gambe e piedi?".
Ha fatto le immagini della testa: fronte, due profili, dietro (`docs/ref/personaggi/kael_testa_fronte.png`,
`_profilo_dx.png`, `_dietro.png`, `_profilo_sx.png`; più due di tre quarti, `_34_dx.png` e `_34_sx.png`, per i
controlli), "si ok, usa queste 4". **Non pubblicata: le immagini vanno a Denis e si pubblica solo col suo ok.**
- Task: multi-image-to-3d con le 4 immagini in quest'ordine (fronte, profilo dx, dietro, profilo sx), texture 4k
  senza PBR, con un texture prompt della testa; 30 crediti, saldo da 1030 a 1000. Il GLB è in
  `meshy/meshy_output/20261110_192241_voidrise-kael-testa_01a1c6e9/testa_k1.glb`.
- Rifarla:
  1. `python3 tools/mesh_prep/decimate_glb.py meshy/meshy_output/20261110_192241_voidrise-kael-testa_01a1c6e9/testa_k1.glb meshy/head/kael_k1_face.glb 17000 4500 -0.25 0.40 -0.62 0.15 0.2 3000 -0.50`
     — 17.000 triangoli: 4.500 nel viso, 3.000 nel colletto (con meno triangoli il bordo viola veniva a denti), il
     resto ai capelli.
  2. `python3 tools/kael_head.py meshy/head/kael_k1_face.glb` (scrive `wip_assets/kael/kael_head.*` e toglie i
     `kael_fringe.*` della proposta di prima), poi `bash mk.sh`.
- Grandezza e posto: occhi e mento dove li ha il disegno intero (`kael_nero.png`); così anche la cima dei capelli e la
  loro larghezza vengono come nel disegno. Il collo va sull'asse del colletto del corpo.
- Colletto: è quello della testa, cioè quello delle immagini (alto, bordo viola, aperto davanti). È allargato alla
  misura del colletto del corpo e prende il posto della sua parte alta. Quello del corpo arrivava 2-4 cm sopra la
  mascella nuova, col bordo viola di traverso, e senza la testa vecchia era un guscio sottile e bucato.
- Ossa:
  - viso e capelli sulla testa;
  - collo e nuca che passano dal collo alla testa salendo;
  - colletto rigido: le spalle passano alla schiena e in cima è metà testa e metà collo. Prima il bordo si
    sfrangiava nella presa e nel calcio alto, e la pelle del collo si stirava.
- Colori dalle immagini:
  - capelli nei loro due lavanda, con tanta ombra quanta se ne vede nelle immagini (36-41%);
  - pelle e sua ombra;
  - tolta la riga chiara sul naso;
  - bordo del colletto viola, non scambiato per i capelli.
- Contorno: sottile su capelli (0,4) e orecchini (0,3). Per le ciocche davanti al viso è spinto dietro il viso, come
  per Ren: prima faceva fasce nere sul viso.
- Controllato:
  - da 6 lati contro le immagini, e il viso da vicino;
  - Kael intero in tutte le mosse;
  - collo e colletto da 8 lati, da vicino, anche solo la testa, solo il corpo e senza contorni, in guardia, presa,
    calcio alto e montante.
- **Le ombre disegnate delle immagini** (10/11 sera, Denis: "è fatto bene ma so che puoi fare di meglio, guarda bene
  queste immagini e rendi il modello 3d identico"). Meshy toglie le luci dalla pittura: il viso era tutto chiaro dove
  le immagini lo ombreggiano. Ora le ombre sono cotte nella pittura (`tools/cel_light.py`, `SHADE` in
  `tools/kael_head.py`), quindi seguono la testa in ogni mossa:
  - pelle: una striscia d'ombra sotto le ciocche che stanno sopra la pelle (frangia, tempie), il lato del naso e delle
    guance lontano dalla luce, l'ombra della mascella sul collo;
  - capelli: in ombra sotto le altre ciocche e sotto le punte (luce dall'alto, uguale da ogni lato), più i punti più
    scuri di Meshy; ombra 36-42% di fronte, di tre quarti e di lato come nelle immagini (36-41%), dietro 47% (38%);
  - una luce sola non basta: `tools/kael_light.py` l'ha misurata sulle immagini allineate e nessuna direzione dà le loro
    ombre (sono disegnate dove le ciocche toccano la pelle).
- Orecchini: solo il cristallo, la perlina e il gancio (prima prendevano anche pelle e capelli vicini), il cristallo
  nei quattro viola del disegno secondo le sue facce, perlina e gancio d'argento.
- **I capelli dipinti dalle immagini** (10/11 notte, Denis: "l'hai migliorato MA TROPPO POCO"):
  - prima ho misurato le differenze: le sagome dei capelli e delle immagini si sovrappongono già all'84% da ogni lato;
    la differenza è dentro i capelli (nelle immagini ciocche grandi con linee pulite, nel modello tanti ciuffetti, ognuno
    col suo bordo nero);
  - le 6 camere sono rifatte sulla sola pelle del viso (`tools/kael_hair_fit.py`, in `docs/meshy/kael_head_cams.json`:
    il viso coincide al 71-77%, da dietro al 58%);
  - ogni punto dei capelli prende il colore dalle immagini che lo vedono e lì disegnano capelli (`PAINT`, `paint()` in
    `tools/kael_head.py`, quasi solo dalla vista migliore: niente linee doppie); il viso, gli orecchini e il colletto no
    (sul viso cadevano le ciocche del disegno dove il modello ha pelle);
  - il contorno dei capelli è spinto 12 mm indietro (`HAIR_BACK`): resta solo il bordo esterno della criniera, le linee
    dentro sono quelle delle immagini;
  - da 50°, 65° (la vista del gioco), 120° e 150° nessuna cucitura.
- **Il viso dalle immagini** (11/11 notte, Denis cerchiando il viso in ogni vista: "voglio che le parti che ho cerchiato
  siano perfettamente identiche alle immagini sue. faccia occhi e naso sopratutto, le orecchie vanno bene";
  `tools/kael_fringe.py`, `FACE = 'paint'` in `tools/kael_head.py`):
  - la pelle del viso dipinta dalle immagini che la vedono e lì disegnano il viso; occhi, sopracciglia, naso, bocca e
    mento solo dall'immagine di fronte (da più immagini gli occhi si sdoppiavano);
  - le ciocche di Meshy davanti agli occhi e alla fronte tolte (entro 4,6 cm dal centro del viso, con i pezzi rimasti
    staccati), la frangia dell'immagine di fronte dipinta sulla fronte;
  - il controllo con le camere delle immagini (`docs/meshy/kael_head_cams.json`): da davanti modello e immagine hanno
    pelle e capelli negli stessi punti quasi ovunque (restano qualche ciocca davanti alle orecchie e una riga lungo la
    mascella); di tre quarti e di lato le differenze sono alle tempie (Meshy ha più capelli lì) e qualche ciocca;
  - provato e lasciato: la frangia come un foglio davanti al viso (di lato strisce e pezzi), le ciocche alzate sopra le
    sopracciglia (sono attaccate alla fronte: la stiravano in strisce), le ciocche tolte dove i profili mostrano il viso
    (dietro ce ne sono altre: buchi e pezzi), tutta l'area cerchiata dipinta dall'immagine migliore per ogni punto
    (capelli a macchie).
- **Tempie, guance e occhio destro di Kael** (11/11 notte, Denis cerchiandoli nelle viste: "migliora ancora questi punti
  come nelle immagini", poi "quella ciocca davanti l'occhio rimpiccioliscila mettila davanti con la punta della ciocca
  sopra al sopracciglio", "accorciare o semplicemente rimuovere senza lasciare tracce"; `tools/kael_fringe.py`,
  `SIDES = True` in `tools/kael_head.py`):
  - le immagini non vanno d'accordo tra loro: quella di fronte disegna ciocche accanto agli occhi, i profili e i tre
    quarti disegnano lì tempia e guancia libere (e il profilo e il tre quarti dello stesso lato discordano sopra
    l'orecchio). Un solo modello fermo non può darle tutte;
  - **ciocche nascoste secondo la vista** (`side_hide`, nel gioco `mdHeadHide` in `src/e_model.js`): per ognuna delle
    4 immagini di lato, le ciocche di Meshy che da lì stanno davanti al viso dove l'immagine disegna pelle hanno un
    segno per vertice (`hv` nel pacchetto, `aHide`); lo shader le lascia fuori, con il loro contorno, quando la
    telecamera è dove era quell'immagine (per l'angolo attorno alla testa visto dall'osso Head: segue la testa anche
    nelle mosse; di fronte non si nasconde niente; dal 11/11 un insieme per lato e dissolvenza, vedi sotto "ciocche
    nascoste, ora intere e senza scatti"). Triangoli interi: i loro
    vertici sono separati da quelli dei vicini (con le quote per vertice si tagliava anche la pelle accanto). Il viso
    dietro di loro è lo strato più arretrato tra quelli girati verso la telecamera (per colore il bianco degli occhi
    passava per capelli);
  - **niente buchi** (`covers_gap`): sotto alcune ciocche la pelle di Meshy ha dei vuoti. Un triangolo non si nasconde
    né si toglie se in uno dei suoi punti la superficie più vicina dietro è oltre 4 cm (si vedrebbe dentro la
    testa); se è appoggiato al viso (entro 6 mm) diventa parte del viso, dipinto come la pelle (sulla guancia era
    un puntino scuro);
  - sotto le ciocche nascoste c'è la pelle di Meshy: dipinta dalle immagini di lato, ognuna con la testa come si vede
    da lì (`side_paint`: tutto il disegno, pelle, righe e ciocche; le righe scure solo dall'immagine che vede meglio
    quel punto; anche le orecchie). Una ciocca che resta in piedi davanti al viso non prende la pelle dell'immagine
    (dall'altro lato erano pezzi color pelle davanti al viso). La pelle che nessuna immagine vede e che era rimasta
    color capelli prende la pelle dipinta vicina (`skin_fill`);
  - i contorni delle ciocche non sono righe del viso (`lock_lines`): prima il contorno della punta di una ciocca
    dell'immagine di fronte finiva dipinto sulla guancia, due tratti scuri visti di tre quarti;
  - **occhio destro di Kael** (a sinistra nell'immagine di fronte): l'immagine di fronte ritoccata in codice
    (`front_edit`, non il file di Denis): le due ciocche sopra l'occhio finiscono a punta sopra il sopracciglio;
    sotto, occhio, sopracciglio e pelle dall'altro occhio specchiato (accanto al naso il colore della pelle). Tutte le
    ciocche di Meshy davanti al viso entro 4,6 cm dal centro tolte (anche davanti a occhi e sopracciglia), occhi e
    sopracciglia dipinti dall'immagine di fronte qualunque fosse il colore di prima (`EYE_ZONE`: Meshy ci aveva
    dipinto sopra le ciocche);
  - provato e lasciato: schiacciare le ciocche sulla testa (`press`: sparivano anche di fronte, dove l'immagine le
    disegna; a strati facevano pezzetti e schegge nere); nasconderle con quote per vertice per lato (buchi nella
    pelle); togliere le ciocche accanto agli occhi fino a 5,8 cm dal centro (le tagliava a metà: le metà rimaste erano
    schegge viste dall'altro lato); tenere sulla fronte i triangoli sopra i vuoti (chiazze color pelle tra i capelli);
  - **lo scanner mostrava schegge nere che nel gioco non ci sono**: il contorno dei capelli è spinto indietro lungo la
    linea di vista (`aBack`); con la telecamera ortografica di `tools/sheet_scan.py` quella spinta lo spostava fino a
    6 mm in alto sullo schermo. Ora con una telecamera ortografica la spinta è solo in profondità (`mdLineMat`). Le
    righe scure che Meshy ha dipinto tra le ciocche hanno il contorno sottile dei capelli (`hairish`);
  - resta: sopra e davanti all'orecchio, visti di tre quarti, i capelli di Meshy sono più disordinati che
    nell'immagine (lì profilo e tre quarti disegnano cose diverse sugli stessi punti).
- **Nuca, ciocca davanti, lobi e orecchini** (11/11, Denis cerchiandoli sulle immagini della guardia: "migliora le parti
  cerchiate"). Per trovare le cause: quale passaggio ha dipinto ogni punto della texture (vedi "Come cercare un
  difetto" qui sotto) e un controllo indipendente zona per zona, anche in movimento con la telecamera del gioco.
  Cause e correzioni (`tools/kael_fringe.py`, `tools/kael_head.py`, `src/e_model.js`):
  - **nuca e capelli dietro le orecchie**: `side_paint` dipingeva dalle immagini di profilo fino a dietro la testa;
    lì i profili vedono i capelli di taglio (strisce) e disegnano il collo dove il modello ha le punte dei capelli
    (pezzi color pelle sulle ciocche). Ora arriva fino a 105° attorno alla testa e sfuma in 15° (`SIDE_PAINT[3:5]`);
    i capelli dietro l'orecchio non prendono mai la pelle delle immagini (`BEHIND_EAR`); l'immagine di dietro dà alla
    nuca solo la sua pelle, non il bordo tra punte e collo;
  - **macchie nere e strisce sul collo**: erano le righe di contorno delle immagini (il bordo della figura) e i
    campioni presi di striscio. Ora una riga scura si prende solo da un'immagine che vede quel punto di fronte e non
    dal bordo della figura (`LINE_RULE`), il collo solo da immagini che lo vedono bene (`NECK_FACING`), niente righe
    scure sotto e dietro le orecchie (`UNDER_EAR`), e la pelle del collo non prende i capelli né i loro contorni
    disegnati più in basso che nel modello (`NECK_SKIN`). La pelle del collo rimasta color capelli prende la pelle
    vicina (`skin_fill` ora anche attorno al collo); sotto la mascella resta l'ombra nera del disegno;
  - **"secondo orecchino" dipinto sul collo**: le immagini disegnano gli orecchini, che finivano dipinti sulla pelle
    dietro quelli veri. Ora ogni immagine ha la maschera dei suoi orecchini (`jewel_mask`: i cristalli viola vicino
    alla scatola dell'orecchino vero, con gancio e perlina sopra) e lì non dipinge;
  - **punte dei capelli chiare e a pezzi**: un terzo dei capelli della nuca non è visto da nessuna immagine e restava
    in due toni piatti lungo i bordi dei triangoli. Ora prende il colore dei capelli dipinti più vicini
    (`HAIR_FILL`); il contorno della punta disegnata non viene più stampato a metà ciocca;
  - **ripiano tra collo e colletto**: i triangoli che uniscono il collo al colletto allargato non erano dipinti da
    nessun passaggio (pezzetto lilla). Ora hanno il colore della fodera e niente contorno (`COLLAR_SHELF`);
  - **ciocca grande davanti alla fronte** (quella davanti al suo sopracciglio sinistro, 3 cm staccata dal viso):
    aveva chiazze color pelle (presa dall'immagine di lato, dove dietro la ciocca non c'è niente), era tagliata per il
    lungo (`face` toglieva le ciocche entro 4,6 cm dal centro e lei sta a cavallo: guscio aperto, nero lungo il
    taglio, l'interno visto da destra), tagliata a moncone dalle viste di sinistra e a strisce (le righe dei capelli
    del profilo dipinte di traverso). Ora `free_locks` trova le ciocche che pendono davanti al viso (pezzi di capelli
    oltre 6 mm davanti al viso visto di fronte): quella libera (meno di metà dentro i 4,6 cm e oltre 2 cm staccata
    vista di lato) resta intera, non viene dipinta dalle immagini (due lavanda puliti) e i suoi texel color pelle
    prendono il colore dei capelli vicini (`LOCK_FILL`, anche per le altre ciocche in piedi);
  - **ciocche nascoste, ora intere e senza scatti**: prima ogni immagine di lato aveva il suo insieme e lo shader li
    scambiava di colpo a metà strada (a -47°, tra la guardia e la parata: una ciocca accanto all'occhio scattava a
    ogni parata e lampeggiava camminando all'indietro); le ciocche erano tagliate dove l'immagine smette di
    disegnare pelle (monconi sopra l'occhio, pezzi segati visti da dietro) e spariva il gancio dell'orecchino
    sinistro. Ora c'è **un insieme per lato** (`hv` a 2 valori: nascosto dal suo lato destro, dal sinistro), le
    ciocche davanti al viso si nascondono **intere o per niente** (`HIDE_WHOLE`), con loro i "piedi" appoggiati sulla
    pelle accanto (`HIDE_FOOT`) e i pezzetti che resterebbero in aria, mai gli orecchini. La prova dei buchi non vale
    per le ciocche intere né per i pezzetti sospesi (oltre il bordo del viso dietro non c'è niente, ma non è un buco). Nel gioco (`mdHeadHide`) il lato destro si nasconde quando la telecamera è oltre
    -12,5° attorno alla testa, il sinistro oltre +11°, con 4° di gioco (isteresi) e una dissolvenza a puntini in
    circa 6 fotogrammi (`mdHideShader`, `MD_HIDE`); un salto di oltre 40° in un fotogramma cambia subito;
  - **macchia lilla nell'orecchio**: nelle scatole degli orecchini (`BUST['ears']`) anche le righe scure dell'orecchio
    contavano come orecchino: dipinte color argento, e i triangoli vicini saltati dalla pittura dalle immagini. Ora
    orecchino è solo ciò che pende dal lobo (`EAR_HANG`), più i pezzi del gancio lungo il suo asse (`EAR_AXIS`);
    dentro l'orecchio si usa solo il profilo dove lo vede (i due disegni dell'orecchio non cadono nello stesso punto);
  - **orecchini**: una luce sola li lasciava scuri da dietro e dal lato sinistro: ora ognuno è illuminato dal suo
    lato esterno, davanti e dietro uguale. Sopra la punta del cristallo tutto è gancio e perlina, color argento
    (`EAR_APEX`), qualunque colore avesse dato Meshy;
  - **segni sulle guance e all'attaccatura**: i pezzetti di capelli rimasti appoggiati al viso fanno parte del viso,
    dipinti come pelle e senza contorno (`SCRAP`); `skin_fill` in alto sulla fronte riempie solo triangoli con un
    vertice di pelle (prima riempiva di pelle le righe scure tra i capelli alla radice della ciocca); la riga sotto il
    mento dell'immagine di fronte non viene più dipinta sul sotto della mascella (`JAW_UNDER`: era una seconda riga);
  - provato e lasciato: togliere i resti delle ciocche tolte sopra la fronte (i triangoli oltre 12 mm davanti al piano
    della fronte): di profilo il ciuffetto sporgeva meno, ma da destra si apriva una chiazza di pelle tra i capelli;
  - resta: il ciuffetto sfrangiato in alto davanti alla fronte visto di profilo (i resti delle ciocche tolte sopra
    l'occhio destro); vicino alla coda delle sopracciglia, con le ciocche nascoste, qualche trattino lilla (la ciocca
    dell'immagine di fronte e la coda del sopracciglio dei profili dipinte sugli stessi punti); la ciocca grande, vista di fronte e da destra, arriva fino alla guancia (da
    sinistra è nascosta): se Denis vuole si può accorciare con la punta sopra il sopracciglio come l'altra, ma è un
    cambio di forma e serve il suo ok.
- **Come cercare un difetto** (strumenti di lavoro, non nel repository): registrare quale passaggio di
  `tools/kael_head.py` ha scritto per ultimo ogni texel (avvolgendo `paint`, `side_paint`, `skin_fill` e confrontando
  la texture prima e dopo), poi disegnare la testa in software da qualunque angolo colorando ogni pixel per passaggio o
  per classe di Meshy (pelle, capelli, misto): si vede subito se una macchia viene da Meshy, dai capelli dipinti
  dalle immagini, dal viso, dai lati o dal riempimento. Contare i texel "triangolo di capelli ma color pelle" per
  passaggio dice quale regola correggere.
- Provato e lasciato (`tools/kael_hair_fit.py`, `MODE`): rimodellare i capelli sulle sagome delle 6 immagini. Punto per
  punto alza la sovrapposizione al 86-90% ma fa una zazzera senza punte; tutta la criniera insieme ('radial', 'sweep')
  e le punte allungate ('spikes') guadagnano solo 1-3% e fanno punte sfrangiate. La forma resta quella di Meshy:
  di lato la cresta in alto, dietro i capelli più corti delle immagini.
- Scanner: `tools/sheet_scan.py` ora mette anche la testa nuova (`<nome>_head.*`) al posto di quella che nasconde.
  Scansioni delle immagini della testa: `--part=1.44:1.80` e la rotazione di ogni immagine (fronte -8:8, tre quarti
  -50:-20 e 20:50, profili -100:-78 e 78:100, dietro 168:192).
- Nel look: `CFG.looks.kael.head:true`. Per tornare alla versione 6, togliere `head:true`. La proposta con la testa di
  Ren (`tools/kael_ren_head.py`) è superata.
- Per dopo: il busto e le braccia, poi le gambe e i piedi da Meshy (il piano di Denis), sempre con saldo, costo e ok
  prima. Col busto nuovo il colletto verrà dal busto.

## Versione 6 (10/11): capelli, mascella, tuta uguale davanti e dietro
Denis: "continua a migliorare il viso ed tutto il resto fino a che non viene quasi identico alle foto di kael".
Misurato in 3D contro i fogli dalla stessa inquadratura:
- **Capelli**: Meshy li aveva dipinti quasi bianchi (luminosità media 232); nel foglio della testa sono lavanda chiaro
  (225,214,224) con circa il 40% in ombra lavanda (129,111,138). Ora nei due toni del foglio, seguendo le ciocche
  dipinte da Meshy, e con il contorno più sottile (`HAIR_LINE`: nel foglio le linee delle ciocche sono fini). I
  segni chiari di Meshy sulla pelle (mascella, collo) non contano come capelli (`HAIR_SKIN`).
- **Mascella**: contorno più spesso sulla linea della mascella (`JAW_LINE`) e il sotto della mascella nero col bordo
  netto (`kael_face.py` `JAW_NY`): la V nera del foglio vista di fronte, l'ombra sul collo di tre quarti.
- **Tuta**: Meshy l'aveva dipinta più scura dietro che davanti; ora antracite e pieghe nella stessa proporzione del
  disegno davanti, dietro e di lato (`SUIT_BINS`).
- **Colletto**: via i quadratini color pelle sul bordo viola e nero del colletto (alcuni li aveva dipinti Meshy,
  altri li aggiungeva il passo del viso: la regola del mento prendeva i riflessi lavanda del colletto). Il colletto
  non fa mai parte del viso (`COLLAR_Y`) e i pezzetti di altri colori sopra di esso prendono il suo (`COLLAR_SPECK`).
- Provato e tolto: luce piatta anche sulla schiena (nell'anteprima non cambiava niente: le luci girano col modello).

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
- (Versione 6, superate dalla testa da Meshy: forma dei capelli, orecchie e orecchini a cristallo ora sono quelli
  delle immagini di Denis.)
- Capelli che si muovono un po' nelle mosse (Denis, 10/11: "saresti in grado di farlo muovere leggermente i capelli
  quando fa movimenti?"): ossa a molla sulle ciocche grandi (la cresta, le punte ai lati e dietro), figlie della testa,
  che restano un po' indietro e oscillano come i nastri della fascia di Ren; solo grafica, la logica del combattimento
  non cambia. I pesi delle ciocche crescono verso le punte.
- Stile più anime (Denis, 10/11: "così sembra troppo realistico"). In Meshy non c'è un'opzione "anime" per
  image-to-3d: lo stile viene dall'immagine, ma il modello standard aggiunge dettagli realistici (muscoli, pieghe,
  ombre nella pittura). Tre strade:
  - in Meshy, il modello "smart topology": più semplice e pulito, a pezzi separati;
  - in Meshy, "retexture" con un disegno di Denis come riferimento di stile, per colori piatti;
  - da noi, gratis: luce toon a due toni netti, pittura ripulita a colori piatti, contorni.
  Prima di provarle in Meshy: prezzo dal listino (docs.meshy.ai/en/api/pricing), saldo e ok di Denis.
