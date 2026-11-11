# Voidrise Fighters — Design dell'interfaccia (UI/UX e navigazione)

Data: 11/11/2026 · Scelte di Denis raccolte in chat (domande a risposta multipla), da rileggere qui.
Riferimenti: `docs/ref/ui/00-…04-*.png` (stile nuovo, **vince sul primo riferimento** per menu e HUD). La lotta resta quella della spec Tappa 1 (`2026-11-06-voidrise-tappa1-design.md`).

## 1. Obiettivo

Interfaccia dall'aspetto **tripla A**, anime cinematografico, coerente con Ren e Kael: colori sobri (blu-viola scuro, tramonto, oro e arancione), testi chiari, personaggi in primo piano, luce d'atmosfera, transizioni curate. **Tutto in italiano.** Pensata per **telefono in orizzontale**, funziona anche con mouse, tastiera e controller.

Regole:
- Niente schermate solo decorative: ogni pulsante fa qualcosa, oppure è **dichiarato** «In arrivo» (lucchetto o avviso). Mai simulare come funzionante ciò che non c'è (niente ricerca online finta, niente classifica globale inventata).
- Ogni schermata prevede: selezione, caricamento, conferma, errore, ritorno indietro.
- Logica dei menu **separata** dalla lotta. Stessi componenti e stesse regole di navigazione ovunque.
- Personalizzazione dei personaggi esclusa. Niente audio in questa fase (le impostazioni audio si salvano, con nota «Suoni in arrivo»).

## 2. Stile visivo a strati

Ogni schermata è una scena a strati, non un'immagine ferma:

| Strato | Contenuto | Animazione |
|---|---|---|
| 1 Cielo | tramonto viola-arancione, nuvole | nuvole che scorrono lente, sole che pulsa piano |
| 2 Lontano | rovine, arco, stendardi | parallasse al cambio schermata e al movimento del fuoco; stendardi che ondeggiano |
| 3 Nebbia | 2 fasce di nebbia | scorrono a velocità diverse |
| 4 Personaggi | Ren/Kael scontornati | respiro (scala 1–1,01), luce di bordo arancione/viola che pulsa, ingresso scivolando |
| 5 Davanti | scintille, braci, polvere (canvas 2D leggero) | particelle che salgono |
| 6 Interfaccia | testi, pulsanti | ingresso a cascata, fuoco oro con lama di luce che scorre |

- Tecnica (scelta A): **HTML + CSS** per testi e pulsanti (sempre nitidi), strati come immagini mosse con `transform`/`opacity` (scheda video), un solo `<canvas>` 2D per le particelle. Three.js resta solo per la lotta. Nei menu il motore 3D è fermo.
- **Qualità** Bassa/Media/Alta (automatica al primo avvio): in Bassa niente nebbia animata e particelle ridotte.
- **Transizioni** (~0,4 s): lama di luce arancione obliqua che attraversa lo schermo, strati che scivolano a velocità diverse, pulsanti che entrano a cascata.
- **Componenti** (uno per tipo, riusati ovunque): logo VOIDRISE, titolo di sezione con barra arancione e sottotitolo corsivo, pulsante obliquo (normale / fuoco / premuto / bloccato), carta (modalità, arena, stagione), linguetta, cursore, selettore ‹ valore ›, griglia di ritratti, barra di progresso, finestra di conferma, avviso «In arrivo», messaggio d'errore con «Riprova», barra di caricamento, chip giocatore (avatar + nome + livello) in alto a destra, pulsante ‹ Indietro.
- Caratteri: titoli con grazie spaziate (stile del logo, Google Fonts), corsivo con grazie per sottotitoli e voci; numeri grandi per timer e punteggi.
- Game feel nei menu: pulsanti che si schiacciano, fuoco che "scatta" con un piccolo rimbalzo, contatori XP che salgono e rimbalzano.

### Immagini
Generate **a pezzi separati in alta risoluzione** (Blueprint Studio, dalla prossima sessione: rete già aperta; prima di generare: saldo e costo stimato a Denis). Fino ad allora: **segnaposto a strati veri** fatti da `tools/make_ui_assets.py`: Ren e Kael scontornati dalle loro schede (`docs/ref/personaggi/*.png`, sfondo grigio uniforme), rovine separate dal cielo e portate al tramonto da `docs/ref/sfondo-rovine.png`, cielo al tramonto disegnato, ritratti e anteprime ritagliati. Stessi nomi di file delle immagini definitive, così entrano senza cambiare codice.

Elenco (in `assets/ui/`): `sky.jpg`, `ruins.png`, `fog1.png`, `fog2.png`, `ren_full.png`, `kael_full.png`, `ren_win.png`, `kael_win.png`, `ren_vs.png`, `kael_vs.png`, `intro_ren.png`, `intro_kael.png`, `intro_clash.png`, ritratti `face_ren/kael/astra/raigon.jpg`, `silhouette.png`, `astra_full.png`, `raigon_full.png`, anteprime arene `arena_cascata/rovine/montagne/tetti/foresta/deserto.jpg`, icone profilo e stendardi (6+6).

## 3. Mappa delle schermate e percorsi

```
Intro (6-8 s, «Salta») → Titolo «Tocca per iniziare» → [primo avvio: Nome] →
MENU PRINCIPALE  (Gioca · Allenamento · Profilo · Pass stagionale · Impostazioni; chip giocatore)
 ├ Gioca: carte Arcade · Online · Versus locale
 │   ├ Arcade → Personaggio → scala 1/8 → Arena → VS → Lotta → Risultati → scala …
 │   ├ Versus locale → Round/Tempo → Personaggio G1 → Personaggio G2 → Arena → VS → Lotta → Risultati
 │   └ Online → carte Partita rapida · Classificata · Lobby privata → avviso «Online in arrivo»
 ├ Allenamento → Personaggio → linguette Libero | Tutorial combo → Lotta (manichino)
 ├ Profilo → linguette Profilo | Statistiche | Classifica
 ├ Pass stagionale → linguette Pass | Missioni | Archivio  (→ Sblocco personaggio)
 └ Impostazioni → linguette Audio | Grafica | Comandi | Lingua
Lotta → Pausa (Riprendi · Lista mosse · Impostazioni · Abbandona*)
Risultati → Rivincita · Cambia personaggio · Menu principale
(* = chiede conferma)
```

### Dettaglio
- **Intro**: sequenza a inquadrature (non animazione disegnata fotogramma per fotogramma). Ren entra da sinistra con linee di velocità → Kael da destra → primo piano: i pugni si scontrano, lampo, onda d'urto, rallentatore, sassi, tremolio → lampo bianco → il logo si forma → Titolo. A ogni avvio; «Salta» sempre visibile; dopo la prima volta si salta anche toccando ovunque o con qualsiasi tasto.
- **Titolo**: logo su Ren e Kael di profilo, rovine e tramonto. La scritta si adatta all'ultimo dispositivo usato: «Tocca per iniziare» / «Premi un tasto» / «Premi A». Al primo tocco: schermo intero e blocco orizzontale (dentro `try`).
- **Nome** (solo al primo avvio, poi dal Profilo): campo con nome proposto già scritto, 3-16 caratteri, errori chiari e senza colpe («Usa almeno 3 caratteri»). Tastiera a schermo del sistema; col controller una griglia di lettere.
- **Menu principale**: voci a sinistra (la voce col fuoco è grande con barra arancione), eroe a destra (l'ultimo personaggio usato), rivale sfumato dietro, chip giocatore in alto a destra. Sotto «Gioca» le carte Arcade, Online, Versus locale.
- **Selezione personaggi**: griglia 2×6 in basso. Ren e Kael giocabili; **Astra** (lucchetto «Pass gratuito · livello 50») e **Raigon** (lucchetto «Pass Premium · livello 50»); gli altri 8 posti sono **sagome «In arrivo»**. In alto il personaggio scelto a figura intera con respiro, nome e barre **Potenza / Velocità / Difficoltà** (valori in `CFG.ui.chars`). In Versus prima sceglie G1 e poi G2 (stesso personaggio permesso). Bloccato → avviso che spiega come sbloccarlo.
- **Arena**: carte La Grande Cascata (giocabile), Rovine dell'acquedotto, Montagne, Tetti della città, Foresta, Deserto («In arrivo», con anteprima). L'arena col fuoco riempie lo sfondo con un leggero zoom.
- **VS**: i due volti entrano dai lati, il «VS» oro si forma con una lama di luce, una battuta di dialogo per ciascuno (tabella per coppia in `CFG.ui.lines`, es. Ren «Non mi tirerò indietro.» / Kael «Allora dimostralo.»). La barra «Caricamento…» segue il caricamento vero dell'arena; dura almeno 2,5 s; poi un tocco la salta. Errore → «Impossibile caricare l'arena» con Riprova / Indietro.
- **Risultati**: «Vittoria» / «Sconfitta» / «Pareggio» (in Versus: «Vince G1 · Ren»), punteggio 2-1 con i due volti, XP guadagnati che salgono con un contatore, missioni completate e livello del pass che avanza (con scritta «Livello N!»). Pulsanti Rivincita, Cambia personaggio, Menu principale.
- **Pausa**: Riprendi, Lista mosse (dalla tabella delle mosse della Tappa 1), Impostazioni (le stesse schermate, senza uscire), Abbandona (conferma). In Allenamento in più: Avversario fermo/casuale.
- **Arcade**: scala da 8 come nel riferimento con difficoltà. Posto 1 = il rivale (Kael se scegli Ren e viceversa); posti 2-8 «In arrivo». L'avversario oggi è il **manichino provvisorio** della Tappa 1, dichiarato in schermata; diventa il computer vero nella Tappa 4.
- **Online**: tre carte come nel riferimento (Classificata: «Grado: non classificato»), premendo appare l'avviso «Modalità online in arrivo». Nessuna ricerca, codice stanza o giocatore finto.
- **Allenamento**: HUD con ∞, linguette Libero / Tutorial combo. Il tutorial è a **lezioni a passi** (movimento, colpi, colpo forte, combo, lancio, guardia, presa, speciale): ogni lezione mostra i tasti del dispositivo in uso, controlla l'esecuzione leggendo gli eventi della lotta e dice «Riuscito!»; «Ripeti» e lezione successiva.
- **Profilo**: avatar (icona scelta), stendardo, nome (modificabile), livello profilo, vittorie, sconfitte, percentuale. **Statistiche**: per personaggio e totali (incontri, vittorie, combo massima, colpi, tempo di gioco). **Classifica**: «Classifica globale in arrivo» (niente nomi inventati); intanto mostra il record personale.
- **Impostazioni**: Audio (cursori Musica/Effetti salvati, nota «Suoni in arrivo»); Grafica (Qualità Auto/Bassa/Media/Alta, Limite FPS 30/60, Mostra FPS); Comandi (editor dei tasti touch: trascina levetta e pulsanti, dimensione e trasparenza, Ripristina; riassegnazione tasti di tastiera e controller premendo quello nuovo; vibrazione sì/no); Lingua (Italiano; altre «In arrivo»). «Salva» attivo solo se qualcosa è cambiato; uscire con modifiche non salvate chiede conferma.
- **Orientamento**: in verticale la schermata «Gira il telefono» (e la lotta va in pausa).

## 4. Interfaccia in lotta (U2)

Nello stile nuovo, legge lo stato della lotta senza cambiarlo (sostituisce l'HUD semplice della Tappa 1):
- In alto: ritratti in cornice obliqua, nomi, barre della vita oro con la parte persa rossa che cala piano, barra dell'energia sotto, timer in esagono (∞ in allenamento), round vinti; pulsante pausa «II» sopra il timer.
- Contatore «N COLPI» grande corsivo che rimbalza.
- Tasti touch (decisione: quelli della Tappa 1): levetta a sinistra; a destra **Pugno, Calcio, Speciale** grandi e **Scatto, Guardia** sotto; cerchi scuri bordati d'oro, si schiacciano al tocco; posizione, dimensione e trasparenza dalle Impostazioni.
- Scritte «ROUND N», «COMBATTI!», «K.O.», «TEMPO!» nello stile nuovo.

## 5. Progressi (funzionanti in locale)

Tutto salvato sul dispositivo; numeri in `CFG.prog`.

- **XP**: ogni incontro dà XP (giocato + bonus vittoria + bonus combo), le missioni danno XP. Gli stessi XP alzano il **livello profilo** (non si azzera mai) e il **livello del pass** attivo.
- **Pass stagionale**: 50 livelli, due percorsi.
  - **Gratuito**: premi intermedi (icone e stendardi del profilo, monete, lingotti) e **Astra** al livello 50.
  - **Premium**: visibile con i premi e **Raigon** al 50, **non acquistabile**: «Attiva Premium» mostra «Acquisti in arrivo». I livelli avanzano comunque, così i premi sono pronti quando si attiverà. Nel salvataggio «Premium attivo» è un interruttore che in futuro accenderà l'acquisto vero degli store.
  - **Livelli non acquistabili**: si avanza solo giocando e con le missioni.
  - Durata: circa **25-30 giorni** giocando 20-30 minuti al giorno con le missioni.
  - Stagione con data di inizio e fine in `CFG.prog.seasons`; conto alla rovescia «Fine stagione tra …».
- **Missioni**: giornaliere (3, rinnovo a mezzanotte locale) e settimanali (3, rinnovo il lunedì), estratte da un elenco: incontri giocati/vinti, combo e colpi, vittorie con un personaggio, lezioni del tutorial. Barra di progresso, XP, «Riscuoti».
- **Archivio pass**: stagioni scadute con progresso, **Riattiva** (conferma) per completarle; un solo pass alla volta riceve XP (quello attivo). Oggi esiste solo la Stagione 01, quindi l'archivio mostra lo stato vuoto «Nessuna stagione passata ancora».
- **Sblocco**: al livello 50 schermata «Astra sbloccata» con «Continua». **Prova personaggio** e Astra giocabile restano «In arrivo» finché il suo lottatore non esiste (non ha modello né mosse): nella griglia appare sbloccata con la nota «In arrivo».
- **Premi**: icone e stendardi si scelgono nel Profilo; monete e lingotti si accumulano e mostrano «Negozio in arrivo».
- Salvataggio con versione e controllo; se non si può salvare (memoria piena o bloccata) appare un avviso e il gioco continua.

## 6. Architettura

```
src/a1_ui_cfg.js   CFG.ui (tempi, animazioni, personaggi, battute, arene) e CFG.prog (XP, pass, missioni, stagioni)
src/u0_save.js     salvataggio versionato su localStorage, con try/catch e migrazione
src/u1_nav.js      pila delle schermate, fuoco, indietro, input dei menu (tastiera, mouse/touch, controller a fronti)
src/u2_comp.js     componenti riusabili (crea DOM + comportamento)
src/u3_layers.js   scena a strati, parallasse, particelle, qualità
src/u4_intro.js    intro e titolo
src/u5_play.js     scelta modalità, personaggi, arena, VS, risultati, arcade, online
src/u6_meta.js     profilo, statistiche, impostazioni, editor comandi
src/u7_prog.js     XP, livelli, pass, missioni, archivio (logica pura, testabile senza DOM)
src/u8_hud.js      HUD della lotta e tasti touch (U2)
src/u9_bridge.js   ponte verso la lotta vera (startMatch, risultato, eventi in sola lettura)
src/u_head.html    CSS (variabili di colore e caratteri) e radice #ui
tools/make_ui_assets.py   ritagli segnaposto e compressione delle immagini
```
- Ogni schermata è un oggetto `{id, enter(params), leave(), items, back}` registrato in `u1_nav`. `nav.go(id, params)`, `nav.back()`, `nav.replace(id)`.
- Il fuoco si muove in 2D (vicino più prossimo nella direzione) tra gli elementi con `data-focus`; il tocco e il mouse spostano il fuoco e confermano.
- **Ponte verso la lotta** (`u9_bridge.js`), unico punto di contatto:
  - `bridgePreload(arena) → Promise` (per la barra del VS);
  - `bridgeStart({mode, chars, arena})` chiama `startMatch` della lotta vera (la Tappa 1 è finita, la Tappa 2 è in corso sul ramo `tappa2-ren-meshy`);
  - a fine partita `bridgeResult(S)` dà `{winner, wins:[a,b], chars, mode, hits:[a,b], maxCombo:[a,b], timeS}`, che aggiorna statistiche e XP (e dalla U4 missioni e pass);
  - gli eventi della lotta arrivano in sola lettura da `uiEvents(S)`, chiamata da `stepGame` come `fxEvents` e `hudEvents`.
  - Aggiornamento dell'11/11: la Tappa 1 è già pronta, quindi **niente lotta di prova**: il percorso arriva subito alla lotta vera.
- Lato del giocatore e personaggi: il lato 0 (sinistra) è G1 con il personaggio che ha scelto. Il disegno dei lottatori segue i personaggi scelti (oggi era fisso: lato 0 Ren, lato 1 Kael). Lo **scontro speculare** (stesso personaggio da tutti e due i lati) è «In arrivo»: servono una seconda copia del modello e il colore alternativo.
- Profilo, XP e statistiche sono del **G1** (chi ha confermato); il G2 in Versus locale gioca da ospite.
- La pausa della lotta usa `menu.pause/resume` della Tappa 1; la schermata di pausa è disegnata da questa parte.
- Nota: i numeri dell'interfaccia stanno nell'oggetto `CFG` ma in un file a parte (`a1_ui_cfg.js`) per non scontrarsi con la Tappa 1 su `a0_cfg.js`; si possono unire quando i rami si uniscono.
- Build: i file `u*` entrano nel `mk.sh` del gioco (ramo di partenza: `tappa2-ren-meshy`, la linea principale). I test usano `game_w.html` e `window.__VF` come il resto del gioco. Le immagini dell'interfaccia hanno un tetto di **3 MB** dentro la pagina (la pagina intera resta sotto i 16 MB); `build.py` accetta anche `.webp`.
- Pubblicazione: una pagina Claude a parte, «Voidrise · Interfaccia», finché Denis non decide di unirla al gioco. L'app del telefono (`gh-pages`) non si tocca senza il suo ok.

## 7. Tappe

Ognuna giocabile, provata e pubblicata come pagina:
1. **U1**: sistema (componenti, navigazione, strati, transizioni, salvataggio) + Intro + Titolo + Nome + Menu principale + Gioca + Selezione personaggi + Arena + VS + lotta vera + Risultati (XP base) + la Pausa attuale portata nel nuovo sistema (Riprendi, Ricomincia, Avversario, FPS, Abbandona).
2. **U2**: HUD della lotta, tasti touch, Pausa completa (Lista mosse, Impostazioni), «Gira il telefono» nel nuovo stile.
3. **U3**: Profilo, Statistiche, Classifica, Impostazioni con editor dei comandi.
4. **U4**: Pass stagionale, Missioni, Archivio, Sblocco.
5. **U5**: Arcade, Allenamento e Tutorial, schermate Online.

## 8. Prove e misure

Test automatici (Playwright, come la Tappa 1):
- Percorso completo con tastiera, con controller finto, con tocco su 844×390 e con mouse a 1280×720: Titolo → Menu → Versus → G1 → G2 → Arena → VS → Lotta → Risultati → Rivincita / Menu.
- Indietro da ogni schermata torna alla precedente con il fuoco dove era.
- Gli elementi bloccati non avviano nulla e mostrano l'avviso giusto.
- Salvataggio: nome, XP, impostazioni sopravvivono al ricaricamento; `localStorage` che lancia errori → avviso e gioco che continua.
- Progressi (logica pura): XP → livelli, rinnovo missioni a mezzanotte e il lunedì (data finta), livello 50 → sblocco, Premium non attivabile.
- Layout: nessun testo tagliato o sovrapposto a 640×360, 844×390, 1280×720, 1920×1080; pulsanti touch almeno 44 px; zone sicure (`env(safe-area-inset-*)`).
- Nessun errore in console.
- **FPS** misurati prima e dopo, nei menu e nell'intro, in Bassa e Alta (obiettivo 60 su telefono medio).

## 9. Per dopo (annotato, non costruito)

Acquisto vero del Premium dagli store (Google Play, App Store, Steam) con controllo ricevute su server; online, lobby e classifica globale; negozio per monete e lingotti; altre lingue; musica e suoni; scelta simultanea dei personaggi con due dispositivi; colore alternativo per lo stesso personaggio contro se stesso; intro con i modelli 3D Meshy; Astra e Raigon giocabili.
