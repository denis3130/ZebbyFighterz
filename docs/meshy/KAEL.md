# Kael di Meshy (10/11/2026)

Kael è fatto da Meshy dal disegno di Denis di lui vestito, `docs/ref/personaggi/kael_nero.png` (tuta nera con le parti
viola, tatuaggi neri sulle spalle; Denis: "eccolo tieni, mi raccomando fallo bene"), con lo scheletro di Meshy, le 25
animazioni di Ren riportate sul suo scheletro, le ossa delle dita e una pulizia fatta da me dopo averlo guardato in 3D
da ogni lato e da vicino (`docs/meshy/CONTROLLI.md`). Il nome nel gioco è **Kael** ("Ken" è di un altro picchiaduro).

I GLB stanno in `meshy/meshy_output/` (fuori dal repository: i link di Meshy scadono). Nel repository c'è il pacchetto
pronto in `wip_assets/kael/`: `mk.sh` lo mette solo nell'anteprima di Kael (`viewer_kael.html`), non nel gioco (il
gioco usa un pacchetto Meshy appena lo trova in `assets/` o `viewer_assets/`: `src/d_render.js`, `modelBuild(c) ||
fighterBuild(c)`). Per metterlo nel gioco: spostare `wip_assets/kael/` in `viewer_assets/kael/`, test, pubblicare.

## Task Meshy e crediti (saldo prima: 1100, dopo: 970)
| Passo | Task | Crediti |
|---|---|---|
| Corpo senza capelli né vestiti (`kael_base.png`) — superato | image-to-3d `01a1c4dd-548a-70d1-9dad-05e513084c49` | 30 |
| Il suo scheletro — superato | rigging `01a1c4df-3d59-711e-b4e5-2e7f5a85127b` | 5 |
| **Kael vestito** (`kael_nero.png`; meshy-7 standard, texture 2K, A-pose, image enhancement off, luci tolte) | image-to-3d `01a1c53b-d7ee-776a-9170-273efbf5504f` | 30 |
| **Scheletro** (1,8 m) sul modello alleggerito | rigging `01a1c53f-c3ef-76e8-82bd-4186736248a3` | 5 |
| Animazioni: le 25 di Ren, riportate sul suo scheletro | nessun task | 0 |
| **Testa e capelli** dalle 4 immagini di Denis (vedi "Testa da Meshy") | multi-image-to-3d `01a1c6e9-6c56-778a-a146-b95efc0bfed6` | 30 |
| **Busto e braccia** dalle 3 viste del foglio del busto senza le code della fascia (vedi "Busto da Meshy") | multi-image-to-3d `01a1cbc9-6df2-76aa-bd39-86e8ff4ee855` | 30 |
| **Totale** | | **130** |

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
9. `python3 tools/kael_body.py wip_assets/kael [CARTELLA_DEBUG]` (dopo `kael_arms.py`): il corpo nei colori dei fogli del
   corpo (vedi "Corpo dai fogli del corpo"); scrive `kael_painted.png`, che le pagine prendono al posto del JPEG.
10. Testa e busto da Meshy (pezzi a parte, sopra il corpo): `python3 tools/kael_head.py meshy/head/kael_k1_face.glb` (vedi
    "Testa da Meshy") e `python3 tools/kael_bust_attach.py meshy/meshy_output/20261111_kael-busto/busto_k6.glb` (vedi
    "Busto sulle ossa"; prima `tools/kael_bust.py`, che scrive anche `busto_k6_hands.npz`).
11. `bash mk.sh` (scrive anche `viewer_kael.html`), prova: `python3 tests/viewer_check.py --page=viewer_kael.html`.

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
    pelle accanto (`HIDE_FOOT`), i pezzetti che resterebbero in aria e le **pareti interne** delle ciocche vicine che
    si vedrebbero attraverso il vuoto (`HIDE_IN`: erano blocchi grigio-lilla sulla tempia), mai gli orecchini. La
    prova dei buchi non vale per le ciocche intere né per i pezzetti sospesi (oltre il bordo del viso dietro non c'è
    niente, ma non è un buco); diventa parte del viso solo un triangolo girato verso la telecamera. Nel gioco
    (`mdHeadHide`, `MD_HIDE`): le ciocche del lato destro si vedono quando la telecamera è tra -12,5° e 100° attorno
    alla testa, quelle del sinistro tra -100° e +11° (da dietro di loro restavano solo schegge oltre la testa); il
    cambio parte solo se l'angolo lo chiede per 12 fotogrammi di fila (un jab gira la testa e torna in 8: la ciocca
    lampeggiava a ogni colpo), con 4° di gioco, e poi è una dissolvenza a puntini di circa 10 fotogrammi
    (`mdHideShader`). Al primo fotogramma, dopo 8 disegni senza la testa e con `window.__HIDE_SNAP` (per le immagini
    degli strumenti) lo stato è subito quello finale;
  - **una ciocca disegnata sulla pelle al bordo della zona dell'immagine di fronte** (accanto all'angolo dell'occhio)
    veniva sfumata con la pelle: una macchia chiara sulla tempia. Ora lì è tutta o niente (`side_paint`);
  - **righe a pettine, trattini e scaglie nei capelli**: `paint` prendeva le righe anche da un'immagine che vede quel
    punto di striscio. Ora un'immagine dipinge i capelli solo se li vede con più di 0,3 e le righe scure con più di
    0,4 (`PAINT['min']`, `PAINT['line_min']`); i grigi neutri di Meshy rimasti sui triangoli dei capelli prendono il
    lavanda dipinto più vicino (`GREY`);
  - **puntini attorno agli orecchini e riga viola sul collo**: la maschera degli orecchini disegnati ora copre anche
    il loro bordo sfumato (`JEWEL[7]`); sulla pelle non si dipinge mai viola, e in basso sul collo (sotto
    `NECK_LOW`) nemmeno le righe scure: le immagini disegnano il colletto più in alto del modello e il suo bordo
    finiva sul collo (si vedeva quando la testa si piega nel "colpito"); sotto e dietro le orecchie niente color
    capelli dalle immagini di lato né righe scure da quella di fronte;
  - **macchia lilla nell'orecchio**: nelle scatole degli orecchini (`BUST['ears']`) anche le righe scure dell'orecchio
    contavano come orecchino: dipinte color argento, e i triangoli vicini saltati dalla pittura dalle immagini. Ora
    orecchino è solo ciò che pende dal lobo (`EAR_HANG`), più i pezzi del gancio lungo il suo asse (`EAR_AXIS`);
    dentro l'orecchio si usa solo il profilo dove lo vede (i due disegni dell'orecchio non cadono nello stesso punto);
  - **orecchini**: una luce sola li lasciava scuri da dietro e dal lato sinistro: ora ognuno è illuminato dal suo
    lato esterno, davanti e dietro uguale. Sopra la punta del cristallo tutto è gancio e perlina (`EAR_APEX`), nel
    lavanda del disegno (`EAR_SILVER`, misurato sulle immagini di profilo) e col contorno nero come il cristallo
    (prima il contorno del gancio era spinto dietro la testa con quello della frangia: una striscia chiara senza
    bordo). La forma resta quella di Meshy (un nastrino, senza anellino né perlina tonda);
  - **macchietta sopra il sopracciglio destro**: una mia regola (`LOCK_FILL`, il color pelle sulle ciocche in piedi
    diventa capelli) prendeva anche i triangoli misti sulla cresta del sopracciglio che l'immagine di fronte aveva
    appena dipinto come pelle. Ora non tocca ciò che le immagini hanno dipinto e prende il colore solo dai capelli;
  - **segni sulle guance e all'attaccatura**: i pezzetti di capelli rimasti appoggiati al viso fanno parte del viso,
    dipinti come pelle e senza contorno (`SCRAP`); `skin_fill` in alto sulla fronte riempie solo triangoli con un
    vertice di pelle (prima riempiva di pelle le righe scure tra i capelli alla radice della ciocca); la riga sotto il
    mento dell'immagine di fronte non viene più dipinta sul sotto della mascella (`JAW_UNDER`: era una seconda riga);
  - provato e lasciato: togliere i resti delle ciocche tolte sopra la fronte (i triangoli oltre 12 mm davanti al piano
    della fronte): di profilo il ciuffetto sporgeva meno, ma da destra si apriva una chiazza di pelle tra i capelli;
  - resta: il ciuffetto sfrangiato in alto davanti alla fronte visto di profilo (i resti delle ciocche tolte sopra
    l'occhio destro); vicino alla coda delle sopracciglia, con le ciocche nascoste, qualche trattino lilla (la ciocca
    dell'immagine di fronte e la coda del sopracciglio dei profili dipinte sugli stessi punti); la ciocca grande, vista di fronte e da destra, arriva fino alla guancia (da
    sinistra è nascosta) e di profilo da destra è un filo lungo staccato dalla fronte: se Denis vuole si può
    accorciare con la punta sopra il sopracciglio come l'altra, ma è un cambio di forma e serve il suo ok; il gancio
    dell'orecchino si può rifare in codice come nel disegno (anellino nel lobo e perlina tonda): anche questo è un
    cambio di forma; sotto la mascella il cuneo nero ha ancora i bordi a dentini (lo dipingono sia `face` sia
    `side_paint`); un piccolo triangolo scuro al centro del bordo del colletto sulla nuca.
- **Colori piatti, niente sfumature né sovrapposizioni** (11/11, Denis rimandando le sei immagini: "rendere la testa del
  modello 3d senza sfumature o sovrapposizioni tra le cose", poi "occhi e sopracciglia non si toccano, perfeziona ciò
  che vedi fuori posto e rimuovi se vedi le cose di troppo"). Pubblicata nell'anteprima di Kael l'11/11 (versione 9
  della pagina) su richiesta di Denis ("non mi hai dato l'anteprima da vedere"); aspetta il suo giudizio.
  `tools/kael_flat.py`, chiamato alla fine di
  `tools/kael_head.py` (`FLAT = True`):
  - la pittura veniva da sei disegni proiettati su una forma che non è la loro: dove due si incontrano erano
    sfumati tra loro, ognuno portava i suoi bordi morbidi e, visto di striscio, veniva stirato. I disegni invece sono
    cel: pochi colori piatti con righe nere sopra, ogni bordo netto. Misurato: nei disegni i pixel "morbidi" sono il
    10-11% della figura (i bordi delle righe), nel modello erano il 12,5-14%; ora circa il 9,5%;
  - **due strati, sulla superficie** (non nell'atlante: le isole di Meshy sono piccole e sparse): sotto, per ogni
    texel uno dei colori piatti dei disegni (`PAL`: capelli chiaro e ombra, pelle e la sua ombra, il colletto i
    suoi); sopra, le righe nere disegnate, rimaste dov'erano e rese nette (`INK`). Un texel in un'area piatta è
    sicuro; gli altri (bordi, sfumature, toni di mezzo, righe) prendono, tra i colori dei texel sicuri vicini, quello
    che li spiega meglio come "quel colore con un po' di inchiostro sopra": una sfumatura diventa un gradino e il
    bordo morbido di una riga non diventa il tono scuro. Poi i bordi tra i colori sono arrotondati (`SMOOTH`) e
    spariscono le macchie troppo piccole per essere una cosa (`SMALL`: sotto 40 mm² sui capelli, 12 altrove), i
    trattini (`DASH`, `SHORT`: sui capelli le righe più corte di 5 mm; `LONE`: i puntini soli accanto a una riga)
    e la foschia grigia; i bordi a dentini delle campiture nere sono chiusi (`INK_FILL`);
  - **niente sovrapposizioni tra le cose**: un'isola dei colori della pelle quasi tutta circondata da capelli (o il
    contrario) prende il colore di ciò che la circonda (`ISLE`: un tratto d'ombra della pelle dentro una ciocca,
    un blocco color capelli sulla guancia); un triangolo tutto capelli prende solo i due colori dei capelli (le
    immagini di lato avevano dipinto pelle su alcuni); il lato interno delle ciocche (`INNER`, che si vede dove una
    ciocca è nascosta) è tutto nel tono d'ombra, senza righe;
  - **sotto la mascella e sul collo** (`JAW`): la riga spessa della mascella dei disegni, proiettata da sei immagini
    su una mascella che non è la loro, era una fascia a tratteggio con schegge nere attorno e un pezzetto nero
    staccato sul mento. Ora il cuneo nero è intero e lì spariscono i tratti sotto 60 mm² (sotto 100 dietro le
    orecchie: le macchie nere sotto i lobi);
  - **i capelli visti dall'alto** (`TOP`): nessun disegno li mostra; avevano i toni dei disegni di lato presi di
    striscio e quelli di Meshy, macchie a mimetica che non seguono nessuna ciocca (si vedevano da accovacciato).
    Ora lì il tono viene dalla forma: ombra negli avvallamenti tra le ciocche, chiaro altrove;
  - **occhi e sopracciglia non si toccano** (`EYE`, `HALO`, `eyes_zone`): nella fascia degli occhi, sulla superficie
    del viso (non le ciocche davanti, non le tempie), tutto ciò che non è pelle (bianco, iridi, ciglia, sopracciglia
    e le loro righe) e 2,5 mm attorno resta com'era, al pixel (verificato di fronte e di tre quarti: nessuna
    differenza); la pelle nel resto della fascia è pulita come le guance (lì erano rimaste strisce e aloni morbidi).
    Anche gli orecchini restano com'erano (i loro triangoli; la pelle del lobo e i capelli attorno al gancio ora
    sono puliti come il resto);
  - **dove l'atlante dà pochi texel a un triangolo** (il 10% dei capelli ha texel più larghi di 0,7 mm) i vicini si
    cercano più lontano (`PITCH`), così anche lì spariscono macchioline e bordi a blocchi;
  - **la pittura è un PNG** (`kael_head.png`, senza perdite; prima JPEG, che sporca ogni bordo tra due colori piatti e
    dimezza la risoluzione dei colori). Il gioco legge il PNG se c'è (`mdHeadData`); la texture della testa ha
    `anisotropy = 4` (colori e righe restano netti sulle superfici viste di striscio);
  - **l'interno delle ciocche nel gioco** (`MD_HAIR_IN` in `src/e_model.js`, solo la testa di Kael): una ciocca è un
    foglio solo; vista da dietro (dove una ciocca davanti è nascosta, o attraverso la fronte dall'altro lato) mostrava
    la pittura chiara del lato esterno, scaglie pallide senza contorno. Ora il lato interno è nel tono d'ombra dei
    capelli;
  - **triangolo nero sulla nuca**: i triangoli che uniscono il collo al colletto erano tutti scuri; uno saliva sulla
    nuca sopra il bordo. Ora sono scuri solo fino al bordo del colletto (`SHELF_TOP` in `tools/kael_head.py`, `RIM` in
    `tools/kael_flat.py`), sopra è pelle del collo;
  - **cose di troppo**: i pezzi dei capelli appesi al resto per un solo vertice (`corner_pieces` in
    `tools/kael_fringe.py`): i monconi delle ciocche tolte davanti alla fronte (una scheggia di 4 cm² in alto a
    destra, visibile da ogni lato) e un lembo di 5 cm² accanto alla tempia destra quando le ciocche sono nascoste;
  - misure: pixel "morbidi" nelle viste dei disegni ora 0,5-1,6% della figura (erano 12,5-14%); niente pezzi staccati
    nel modello in nessuno dei quattro stati delle ciocche nascoste;
  - **resta** (trovato dai controlli, non fatto): la fascia viola del colletto ha il bordo inferiore a dentini e, al
    centro dietro, una tacca nera che la taglia (il colletto ha 4 volte meno texel del viso: andrebbe dipinto con una
    regola per altezza); dall'alto (accovacciato, salto) tra le ciocche della frangia si vede la fronte (è la forma:
    servirebbe una fodera sotto la frangia o limitare l'inclinazione della testa, da mostrare a Denis); i bordi dei
    cristalli degli orecchini a dentini da vicino; **nel gioco** (non nell'anteprima) il contorno dei capelli a
    grandezza vera si spezza in puntini perché il gioco disegna senza antialiasing (`src/d_render.js`,
    `antialias:false`; con antialiasing i punti sbagliati a 130 px passano dal 10,4% al 3,8%): da decidere misurando
    gli FPS quando Kael di Meshy entrerà nel gioco. Il filtro della texture (mipmap + anisotropia 4) è già il
    migliore dei cinque provati;
  - misure del controllo indipendente sui capelli (da tenere presenti): le ombre dei capelli non seguono le ciocche
    del modello (i bordi tra i due toni cadono su una piega del modello solo per caso) perché vengono dai disegni,
    che hanno ciocche diverse; le righe nere sono un terzo di quelle dei disegni. La cura vera sarebbe ridipingere
    i capelli dalla forma del modello (ombra dove la superficie guarda in basso o è coperta, righe lungo le pieghe):
    cambia l'aspetto di tutta la chioma, **solo con l'ok di Denis**;
  - provato e lasciato: ridisporre le isole dell'atlante con spazio tra loro (per quando la testa è piccola e la
    scheda grafica legge le copie ridotte della pittura): a 130 pixel i punti lontani dall'ideale passavano solo dal
    14,3% al 13,8%, con un'immagine grande il doppio. Non è quella la causa di ciò che resta a quella grandezza.
- **Tempia tra orecchio e occhio, puntini sulla guancia** (11/11, Denis sull'anteprima pubblicata, cerchiando la
  tempia destra vista da dietro di lato: lì c'era una macchia marrone con sotto la punta di una ciocca dipinta, dove
  il suo disegno di profilo ha le ciocche pulite davanti all'orecchio):
  - **causa**: accanto agli angoli esterni degli occhi (`EYE_ZONE`, fino a 56 mm dal centro del viso) dipinge solo il
    disegno di fronte, perché le ciocche dei disegni di lato non finiscano sugli occhi. Ma di fronte quella striscia
    di tempia è dietro le ciocche: il disegno di fronte lì non dipingeva niente. La striscia restava con la pelle di
    Meshy e l'ombra cotta delle ciocche che di lato spariscono (`SHADE`, "sotto le ciocche"), oppure con la sola ombra
    del disegno di tre quarti dove quello disegna pelle e il profilo una ciocca. Lo stesso su tutti e due i lati;
  - **cura** (`side_paint` e `face` in `tools/kael_fringe.py`): quello che il disegno di fronte non ha dipinto
    (`front_done`), oltre la zona dei lineamenti (`FEAT[0]`, 42 mm) e fuori dagli occhi e dalle sopracciglia veri
    (`eyes_mask` di `tools/kael_flat.py`, più 4 mm: `EYE_KEEP`), è dei disegni di lato come il resto della tempia:
    ora lì ci sono le ciocche del profilo, intere, fino alla punta sulla guancia. Quei texel non contano come
    "sopracciglia" nel passaggio dei colori piatti (`not_eye`): sono capelli e vengono puliti come gli altri;
  - **puntini sulla guancia** (si vedevano nella stessa foto): i texel dei triangoli tolti dal modello (le ciocche di
    Meshy sopra il viso) tenevano la loro pittura da capelli, e i triangoli disegnati accanto nell'atlante la
    prendevano lungo i bordi: puntini lavanda e neri sulla guancia sotto la punta di una ciocca. Ora i texel che
    nessun triangolo disegnato usa prendono il colore del texel disegnato più vicino (`tools/kael_head.py`, alla
    scrittura della pittura), tranne entro 6 texel dagli occhi, dalle sopracciglia e dagli orecchini (`PAD_KEEP`): lì
    resta tutto com'era;
  - **i due puntini neri sulla guancia destra** (versione 12): non erano pittura ma il moncone di una ciocca tolta,
    alto fino a 4 mm sulla guancia con alcuni triangoli girati verso l'interno, e sotto un buco nella pelle: di lato i
    suoi fianchi erano facce di dietro e il guscio del contorno li disegnava neri, dal buco si vedeva l'interno della
    testa. Ora (`cheek_stumps` in `tools/kael_head.py`, `STUMP`) un buco piccolo sul davanti delle guance con la pelle
    attorno perde i triangoli girati di oltre 37° entro 4 mm, e quello che resta aperto è chiuso con un ventaglio di
    triangoli nuovi su un texel di pelle piatta, col contorno della guancia. Su questa testa: un posto, 10 triangoli
    tolti e 5 aggiunti; provato nel motore vero da 16 angoli;
  - **occhi e sopracciglia**: geometria e ciocche nascoste identiche (`kael_head.bin` e `.json` uguali byte per
    byte); nella pittura, dentro la maschera di occhi e sopracciglia cambiano 13 texel su 52.721, e non sono né occhio
    né sopracciglio (un'ombra scura vecchia oltre la coda del sopracciglio destro, presa dalla maschera per il
    colore);
  - pubblicata nell'anteprima di Kael l'11/11 (versione 10 della pagina) su richiesta di Denis ("anteprima?"), con
    tutti i 22 test verdi; i controllori indipendenti erano ancora al lavoro;
  - **dopo i controllori indipendenti** (quattro, ognuno con uno scettico che ha rifatto le prove; tutti: la parte
    cerchiata è sistemata, occhi e sopracciglia uguali) sono stati tolti i resti della cura (versione 11):
    - la ciocca dipinta era tagliata su una riga dritta accanto all'angolo dell'occhio destro, dove finisce la zona
      tenuta di occhi e sopracciglia: il pezzo di riempimento che arriva a quella zona senza contorno torna com'era
      (`CUT` in `side_paint`, pezzi fino a 120 mm², qui uno di 29 mm²) e la ciocca finisce sul suo contorno;
    - righe grigie tra i due contorni della ciocca nuova, una macchia grigia e trattini sul suo bordo basso, macchie
      nere morbide dentro la ciocca a sinistra: l'inchiostro è tutto o niente sulla pittura nuova delle tempie e sui
      texel grossi della pelle (oltre 0,6 mm, `COARSE` in `tools/kael_flat.py`);
    - tempia sinistra: un cuneo marrone, due capi di contorno tagliati e un trattino staccato restavano alla punta della
      ciocca, perché due pezzetti staccati (contorni di ciocca e un ritaglio di capelli, presi per "lineamenti" dal loro
      colore) facevano parte della maschera di occhi e sopracciglia. Ora la maschera lascia fuori i suoi pezzi tutti
      oltre 42 mm dal centro e ad almeno 6 mm dal resto (`EYE_PIECE`); la coda del sopracciglio sinistro, un gruppo a
      sé visto di tre quarti ma a 2-4 mm dal resto, resta;
    - i texel della pittura nuova che starebbero nella maschera di occhi e sopracciglia calcolata senza di essa tornano
      com'erano (in `tools/kael_head.py`, prima dei colori piatti). Rispetto alla versione pubblicata prima, dentro la
      maschera cambiano solo i 372 texel dei pezzetti staccati a sinistra (tra 5 e 20 mm sotto la riga degli occhi,
      oltre 45 mm dal centro: né occhio né sopracciglio) e 5 texel dell'ombra scura sopra la coda del sopracciglio
      destro, di pochi livelli;
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

## Corpo dai fogli del corpo (`tools/kael_body.py`, 11/11)
Denis, rimandando i fogli del busto, delle gambe e della schiena (`kael_busto_3viste.png`, `kael_gambe_3viste.png`,
`kael_retro.png`): "ora migliorami il corpo come hai fatto per il viso deve essere identico senza usare agenti". Messo
il corpo accanto ai fogli dalle stesse inquadrature (`tools/sheet_scan.py`; camere in `docs/meshy/kael_body_cams.json`):
la stoffa era quasi nera (nei fogli viola scuro con ombre nere a punte), i tatuaggi neri (nei fogli fulmini viola), la
fascia una banda liscia (nei fogli annodata) e dietro due code e un pezzo viola in più. Per le forme serviva Meshy (60
crediti, saldo 1000): Denis ha scelto di tenere le forme e ridipingere ("Solo ridipingere, gratis").
- **I colori dei fogli** (misurati sui tre fogli): stoffa viola scuro (76,58,84) e le sue ombre nere (28,24,30), il
  viola in luce e in ombra, la pelle e la sua ombra, le righe nere. La pittura di `kael_fix.py` ci passa tono per tono
  (antracite -> viola scuro, pieghe -> nero, i viola ai due del foglio), poi ogni texel è uno dei colori piatti.
- **Proiettare i fogli è stato provato e lasciato davanti e di lato**: le forme di Meshy non sono le loro (nodo della
  fascia, orlo, pieghe; i profili coincidono al 62-78%), proiettati i disegni erano strisce viola sbavate e ombre
  doppie. La ricolorazione delle forme del modello, che vengono dallo stesso personaggio, è pulita e vicina ai fogli.
- **La schiena dal foglio della schiena** (coincide all'85%): dove la si vede bene (oltre 0,5), non le spalle e le
  braccia (lì il foglio cadeva di traverso, macchie viola sul deltoide). Le gambe di tre quarti e di fronte dipingono
  solo i gambali degli stivali (Meshy li aveva tutti neri), e solo coi colori scuri.
- **Tatuaggi**: i pezzi scuri delle spalle e delle braccia con almeno metà pelle attorno entro 6 mm (in 3D: nella
  texture i vicini possono essere un altro pezzo dell'atlante, e le ombre della schiena diventavano viola), non le
  righe sottili dei muscoli, in viola col bordo viola scuro: ora sono fulmini viola come nei fogli.
- **Colletto della testa**: era nei colori scuri delle immagini della testa, un anello nero sul gilet viola scuro; ora
  nei colori del gilet (`COLLAR_OUT` in `tools/kael_flat.py`), scelti con quelli di prima.
- La pittura è un PNG (`kael_painted.png`, colori piatti senza le sbavature del JPEG); `mk.sh` toglie il JPEG dalla
  pagina dell'anteprima.
- **Niente colori sovrapposti sul vestito** (versione 14; Denis sulla 13: "ci sei quasi alcuni colori si sovrappongono
  ancora sul vestito"): `kael_fix.py` aveva messo le pieghe nere anche sui pezzi viola (fascia, code, strisce) e i viola
  sbordavano sulla stoffa di un texel o due. Ora ogni texel sa di che pezzo è (stoffa, viola, pelle: dalla pittura di
  Meshy, che nei pezzi viola tiene il viola anche nelle pieghe, lisciata sulla superficie; dove dipinge il foglio, il
  suo): sul viola il nero diventa l'ombra viola e il viola scuro della stoffa il viola; sulla stoffa i viola diventano
  stoffa e ombra nera (`MAT`). Poi i puntini sotto 8 mm² (righe sotto 1) prendono il colore attorno e i bordi sono
  lisciati (`SPECK`, `SMOOTH`); pelle e tatuaggi restano come sono. Su questo modello: 30.141 texel di stoffa sui
  pezzi viola, 4.630 di viola sulla stoffa, 8.086 di puntini.
- **Zone cerchiate sulla versione 14** (versione 15; Denis, cerchiando due immagini dal gioco):
  - **dita**: il bordo del guanto a strappi sulle dita: ora le dita (le loro ossa oltre metà) sono pelle, il dorso e il
    palmo (l'osso della mano, poco dito) sono guanto (`HAND`);
  - **polsiere al gomito**: sopra il gomito (più osso del braccio che dell'avambraccio) niente polsiera, la pelle;
  - **polsiere, guanti e stivali** (`BIG`): i loro pezzi lisciati più largo, i pezzi viola in viola pieno (via le
    strisce nere sui polsini e sui cinturini e le macchie sulle suole), i gambali viola scuro (prima a chiazze nere);
  - **dietro sui pantaloni**: il foglio della schiena dipinge solo le ombre della stoffa (i suoi viola cadevano accanto
    ai pezzi viola del modello: macchie viola); sui pezzi viola niente ombre (erano strisce scure) e i pezzi di stoffa
    dentro un pezzo viola fino a 150 mm² sono viola (`MAT[4]`);
  - **spalle**: i tratti scuri accanto ai tatuaggi (le loro parti sottili rimaste nere) diventano viola, e le schegge
    viola fino a 30 mm² sulla pelle delle braccia diventano pelle (`TAT[5:]`). Resta qualche scheggia viola sotto la
    punta del colletto sulla spalla destra (è il bordo della punta visto da sotto o il tatuaggio a pezzi: da guardare);
  - niente inchiostro proprio sul corpo: le righe sono quelle del contorno.
- Resta (forme di Meshy, non toccate per scelta di Denis): la fascia è una banda e non un nodo, dietro sui fianchi due
  code e il bordo viola dell'orlo, le strisce viola del davanti sono quelle di Meshy (simili, non le stesse del foglio).

## Busto da Meshy (11/11 sera, non ancora attaccato a Kael)
Denis, rimandando il foglio del busto: "creami il modello in 3d su meshy, ricordati se ti conviene creare quella fascia
viola tu senza meshy dimmelo, che voglio che si animi come quelle arancioni di ren". Le code della fascia le facciamo in
codice come i nastri di Ren (Meshy le incolla al corpo: quelle di oggi sono attaccate ai pantaloni e non si muovono);
il nodo in vita resta di Meshy (Denis: "no il nodo in vita no solo togli meglio quella che hai gia tolto").
- Immagini (`tools/kael_notails.py`, scelte da Denis dopo due giri: "rimuovi meglio la fascia e annerisci leggermente la
  tuta"): le due code tolte dalle 3 viste, il gilet sotto ridipinto lungo il suo orlo con le ombre nere a punte del
  foglio, la tuta un po' più scura; ogni vista da sola su un quadrato del fondo:
  `docs/ref/personaggi/kael_busto_senza_code_{fronte,destra,sinistra}.png` (e il foglio intero, `kael_busto_senza_code.png`).
- Task: multi-image-to-3d con le 3 viste (fronte, destra, sinistra), texture 4k senza PBR, texture prompt del busto; 30
  crediti, saldo da 1000 a 970. GLB in `meshy/meshy_output/20261111_kael-busto/busto_k1.glb` (631.722 triangoli,
  texture 4096; non nel repository).
- Com'è: davanti, di lato e i tatuaggi come il foglio; dietro Meshy ha inventato la gonna del gilet anche sulla schiena
  (il foglio della schiena non ce l'ha: lì ci sono i pantaloni sotto la fascia).
- **Pulito prima delle ossa** (Denis: "prima di mettere il busto sulle ossa di kael miglioriamolo al meglio"):
  alleggerito a 30.000 triangoli (`tools/mesh_prep/decimate_glb.py busto_k1.glb busto_k1_30k.glb 30000`), poi
  `tools/kael_bust.py busto_k1_30k.glb busto_k2.glb`: la pittura di Meshy nei colori piatti delle 3 viste, pezzo per
  pezzo (pelle, stoffa, viola dal colore di Meshy; il nero della stoffa nella quota del disegno), i tatuaggi viola col
  bordo scuro, e le ombre della pelle (scelta di Denis, "Ombre sulla pelle") come una luce dall'alto più gli incavi,
  quanto ne ombreggia il disegno (14%). Proiettare le 3 viste sul modello è stato provato e lasciato: coincidono
  all'85-92% e le ombre venivano a pezzi, i bordi sfilacciati. La gonna dietro resta (Denis non l'ha scelta).
- **Braccia e mani** (Denis: "ok migliora i disegni sulle braccia e mani"; `tools/kael_bust.py`, `arms`, versione
  `busto_k3.glb`): sulla pelle delle braccia le righe e le ombre dei muscoli dei disegni, ogni braccio adattato alla sua
  vista (rotazione, scala e spostamento: coincide all'84-88%; le braccia lontane, mezze nascoste, non si usano;
  misure in `docs/meshy/kael_bust_cams.json`, si rifanno con `--fit`); i tatuaggi restano quelli del modello (quelli del
  disegno cadevano accanto e li spezzavano); il tatuaggio destro, che Meshy aveva dipinto a pezzi, è il sinistro
  specchiato e appoggiato sulla spalla destra; le isole scure di Meshy nella pelle e i pezzetti rimasti sulle spalle
  sono pelle; le mani: dita pelle pulita, guanto viola scuro con le sue ombre nere grandi, bordi lisciati, niente viola
  oltre il polsino.
- **Pollici e bordi neri** (Denis: "sistema i pollici che sono buggati e dipingi meglio i bordi neri delle dita e del
  resto"; `finish` in `tools/kael_bust.py`, versione `busto_k4.glb`): la forma dei pollici era a posto (vista col
  render con z-buffer e il contorno come nel gioco), era la pittura: guanto attraverso il pollice e macchie di pelle sul
  palmo accanto, il pollice sembrava tagliato in due. Ora il pollice è tutto pelle dalla base (lungo la superficie dalla
  punta, `THUMB`), tra pollice e indice guanto; il bordo del guanto sulle dita è quello di Meshy lisciato su 1,2 cm
  (`GLOVE_R`, prima a sfrangiature), il nero del guanto solo nelle pieghe grandi e non accanto al bordo; dietro le spalle
  i tatuaggi che Meshy aveva fatto viola scuro col bordo nero sono viola col bordo viola scuro, come nel foglio della
  schiena; poi le linee nere dove le disegna il foglio: tra pelle e stoffa o viola (bordo dei guanti, scalfi, collo),
  attorno a fascia, polsini e bordo del colletto, tra le pieghe della fascia; non attorno alle strisce del gilet né ai
  tatuaggi. Le dita hanno il loro contorno dal contorno del gioco (dipinte negli incavi erano cunei neri).
- **Pollice in più tolto** (Denis: "noto che kael ha due pollici, rimuovi completamente quello in piu"; versione
  `busto_k5.glb`): Meshy aveva fatto su ogni mano due pollici dalla stessa base, uno verso l'esterno (quello del foglio)
  e uno in avanti (che avevo preso per la nocca). Quello in avanti (10 cm di superficie dalla punta, più vicino alla sua
  punta che a quella del pollice vero: 70 e 61 vertici) è appiattito nel palmo (`remove_extra_thumbs`: i suoi vertici su
  una membrana tesa sul suo bordo, l'anello attorno lisciato, normali rifatte); lì il guanto, e sulle mani solo la pelle
  attaccata alle dita o alla punta del pollice. Il pollice vero resta com'era.
- **Mani di Ren** (Denis: "ora rendi quelle mani simili come quelli di ren"; versione `busto_k6.glb`, gratis): le mani
  di Meshy tolte oltre il polsino e al loro posto quelle di Ren (`assets/ren`, senza la sua fascia del polso), messe al
  posto giusto con polso e cinque punte (scala 2,1-2,2; scarto 1-4 cm sulle dita, 10 cm sul pollice che Ren ha più
  aperto), il polso raccordato al taglio e cucito (triangoli della cucitura girati come i vicini: niente buchi). Nuova
  mappa dei colori (xatlas). Sopra: la pelle e le righe di Ren (pieghe delle nocche; i pezzetti sotto 4 mm² tolti, prima
  sembravano graffi) e il mezzo guanto del foglio: prugna piatto sul palmo fino a un bordo dritto 2 cm sotto le nocche
  (le nocche trovate dove le dita si separano), dita e pollice scoperti dalla base (il pollice fino al suo incavo, misurato
  sulla superficie dalla punta), bordo lisciato; sotto i polsini, dove c'era la mano di Meshy, via il nero e le isolette
  viola. Provati e lasciati: bordo a distanza dal taglio (a zig-zag sui triangoli grandi di Ren), pollice dentro un
  cilindro (lasciava una linguetta di pelle nell'incavo), nero sul guanto dalla luce (macchie).
- Prossimo passo: le code della fascia come nastri (vedi "Busto sulle ossa").

## Busto sulle ossa (11/11 sera, `tools/kael_bust_attach.py`; pubblicato, versione 18)
Denis: "ora adopera". Il busto `busto_k6.glb` è un pezzo del pacchetto come la testa (`wip_assets/kael/kael_bust.json`,
`.bin`, `.png`; `CFG.looks.kael.bust`, `src/e_model.js` `mdPartData`): sotto di lui busto, braccia e mani di Kael sono
nascosti, sopra c'è la testa, sotto le gambe di adesso. Pubblicato nell'anteprima di Kael (versione 18) dopo le immagini a
Denis ("manda anteprima").
- Posto: 0,42 m per unità del busto, la fascia sulla sua (1,08 m). A questa scala profondità del petto, altezza delle
  spalle e fascia coincidono; le spalle del foglio del busto sono 3 cm più strette per lato di quelle del primo disegno.
- Giunture misurate sul busto: gomiti e polsi dalle bande viola delle polsiere (alla stessa distanza dalle bande che hanno
  in Kael, in proporzione alla polsiera), spalle dai deltoidi (sfere: 1,5 cm più dentro, 1 cm più giù, 2 cm più avanti
  delle sue). Le braccia del busto sono il 7-10% più corte delle sue: si accorciano le ossa delle braccia
  (`bones` nel pezzo), le braccia restano come sono.
- Posa: messe nella posa di riposo di Kael (le animazioni sono fatte per quella): braccio 12-15° più aperto, avambraccio
  32-38°, la mano girata come quella di Ren sta nell'osso della mano di Ren (le animazioni e i pugni sono di Ren).
- Pelle: i pesi del punto di Kael più vicino rivolto dallo stesso lato, con le braccia prima allungate alle sue lunghezze
  (così gomito e polso piegano dove piegano i suoi); sulle mani i pesi di Ren con le ossa delle dita (quelle di Ren messe
  sulle mani nuove, i suoi pugni così come sono); lisciati attorno alla cucitura dei polsi.
- Gonna della tunica (il pannello del foglio sotto la fascia): sopra i pantaloni larghi. Il tappo nero piatto con cui
  Meshy l'aveva chiusa sotto è tolto (gonna aperta, disegnata dai due lati); dove i pantaloni sporgevano (1-2 cm ai lati) è
  spinta fuori di 6 mm sopra di loro, lisciata; i pantaloni sotto la gonna sono nascosti, ma non negli ultimi 2,5 cm sopra
  l'orlo (si vedeva il cielo).
- Di Kael nascosti: i triangoli per lo più sulle ossa del busto e delle braccia, tutto il suo busto da sotto la fascia in su
  (la sua fascia e il nodo sporgevano dalla nuova) e i pantaloni sotto la gonna. Le code della vecchia fascia restano
  (pendono da sotto il nodo) finché non ci sono i nastri.
- Luce piatta sul busto (la sua pittura ha le ombre del foglio, come nelle immagini viste da Denis), contorno del corpo.
- Controllato nel visore: guardia, pugno forte, calcio forte, calcio lanciante, speciale (mani aperte), presa, a terra; pugni,
  collo e spalle da vicino. Triangoli disegnati 84.000 → 111.000 (con i contorni).
- **Pugni come le immagini** (Denis, sulla versione 18, cerchiando i due pugni e il polso in guardia: "sono da migliorare
  nettamente guarda le sue immagini di riferimento"). Misurate, le proporzioni di mano e polsiera erano già quelle del
  disegno; i problemi erano tre:
  - in luce piatta il pugno era una macchia scura senza volume: le mani ora hanno la luce del gioco, come i pugni di Ren
    (`HAND_FLAT`, il resto del busto resta in luce piatta);
  - il bordo del guanto cadeva sulla piega delle nocche e nel pugno si rompeva a dentini: ora lo disegna il gioco
    (`aGlove`: per ogni punto della mano la distanza dal bordo; dove è sotto zero il prugna del guanto, lungo il bordo la
    riga nera), dritto in ogni triangolo; la pittura sotto le mani è pelle fino a 3 mm dentro il guanto;
  - il polso di Ren era il 70-75% della banda viola, una strozzatura col polso piegato: allargato del 32% dalla
    cucitura, sfumando sul palmo (`WRIST` in `tools/kael_bust.py`), come nel disegno dove il guanto esce largo dalla polsiera.
  Provato e lasciato: ammorbidire i pesi della pelle sulle mani (il pugno si apriva, un buco vicino al pollice).
- **Pugni, "ancora un po"** (Denis, dopo le immagini dei pugni):
  - la mano sinistra era girata di 25 gradi rispetto a quella di Ren in ogni posa (le ossa delle mani di Kael e di Ren
    differiscono di tanto nella posa di riposo e le animazioni lo conservano; a destra 4 gradi): ora le mani stanno nel
    mondo come quelle di Ren nella sua posa di riposo, così in ogni posa i pugni sono girati come i suoi;
  - luce a due toni come il foglio: dove la luce del gioco mette la mano in ombra, il guanto è il nero del foglio e la
    pelle il colore della sua ombra; altrove i colori pieni (prima tre bande grigie, un pugno fangoso);
  - normali delle mani lisciate (`HAND_NSMOOTH`): niente macchie sul guanto;
  - grandezza: le proporzioni della mano sono quelle del foglio, ma accanto alle polsiere grosse il pugno sembra piccolo
    (quello di Ren è più grande del suo polso). Pronta la prova a +15% (`KAEL_HAND_SCALE=1.15`, `HAND_SCALE`): è un
    cambio di forma, aspetta l'ok di Denis.


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
