# Pose di Ren: editor di pose chiave (13/11/2026)

## Perché
Denis: "mi puoi fare un'anteprima del personaggio dove posso muoverlo come voglio toccando per esempio le gambe o le
braccia per fare nuove animazioni? così capisci meglio cosa intendo". Serve a lui per mostrare a Claude le animazioni
che ha in mente, senza lunghe descrizioni e senza rifare le cose molte volte.

## Approcci considerati
- **A, scelto da Denis**: solo pose chiave, come le sue tavole (posa 1, 2, 3...), un "Riproduci" che le mostra in
  fila a velocità fissa; i tempi li dice a parole (note). Semplice da usare sul telefono.
- B: una linea del tempo con i fotogrammi di ogni posa. Più preciso sui tempi, più complicato da toccare sul telefono.

## Seconda versione (13/11, stesso giorno): solo tasti
La prima versione (punti da trascinare su ogni parte, sotto) per Denis era "TROPPO DIFFICILE". Tra tre strade
(di lato con 5 punti grossi; pose pronte solo a tasti; un omino 2D da muovere) ha scelto **le pose pronte, solo
tasti**:
- Braccio avanti / dietro: Guardia, Avanti, Alto, Al viso. Mano avanti / dietro (un tasto che gira): Pugno,
  Socchiusa, Aperta. Gamba avanti / dietro: A terra, Ginocchio su, Calcio. Busto: Dritto, Avanti, Indietro.
  Altezza: Normale, Basso, Alto. La prima posa è la guardia del kit.
- Il corpo segue da solo (scelte di Claude): un braccio dritto porta dentro la sua spalla (fianchi e busto girano,
  il peso avanti), entrambi squadrano; un calcio inclina indietro e alza sulla gamba d'appoggio, il cui piede gira
  sulla punta; due piedi in aria fanno un salto; gli occhi restano sull'avversario. Posizioni prese dal kit.
- Ren a sinistra, tutte le scelte a destra senza menu nascosti (in verticale sotto). Ogni cambio arriva in 12
  fotogrammi; il gomito tra due posizioni gira attorno al braccio passando dal fianco (nessuno scatto).
- Salvataggio: formato 2 (le scelte per nome); i documenti della prima versione restano e non si elencano.
- Verificato: tutte le 11.664 combinazioni (nessun braccio nel petto, nessun piede sotto il pavimento, nessuna gamba
  tirata) e ognuno dei 288 cambi di una riga senza scatti.

## Terza tappa (14/11): le animazioni di Claude
Denis: "creami tantissime animazioni inventatene almeno 50 [...] basta che siano fatte bene e senza bug o
comportamenti del corpo strane". Scelte di Claude per farle bene con gli stessi tasti:
- Tempi per posa (t fotogrammi per arrivarci, h ferma, e: snap = sempre più veloce, un colpo; out = veloce poi frena),
  nascosti nei tasti ma conservati se Denis modifica una posa; senza tempi resta 24 fotogrammi.
- Posizioni nuove: Gomito e Basso per le braccia, Basso per le gambe, e la riga Passo (Indietro, Qui, Avanti,
  2 avanti) con passi veri (un piede alla volta, alzato, mai strisciato).
- Il corpo: un piede che si stacca sale prima di avanzare e atterra per ultimo; il piede d'appoggio sale sulla punta
  prima di girare; il gomito tra due posizioni gira dal lato esterno del braccio; la spinta fuori dal busto sfuma ai
  bordi (nessuno scatto quando un braccio entra nella fascia del petto).
- 66 animazioni in sei gruppi, elenco "Animazioni" nella pagina (un tocco: si apre e parte).
- Verificate fotogramma per fotogramma (tests/posa_anims.js) e guardate una per una.

## Quarta tappa (14/11): combo e mosse speciali
Denis: "aggiungi anche tante combo / non basarti solo su movimenti macchinosi inventati anche qualche figata, come combo
speciali, mosse speciali ecc". Scelte di Claude:
- Due posizioni nuove per le gambe, Alto (calcio alla testa) e Dietro (calcio indietro, di tallone).
- Campi oltre i tasti, conservati se Denis modifica una posa: giro e capriola di tutto il corpo (gradi contati: il
  giro sulla punta del piede che resta a terra, il cui tallone sale prima e scende dopo; nessun piede striscia), vola
  (salto più alto), x (posto in metri), scatto (balzo radente), fx (colpo, forte, energia, onda) dal punto hit, scia.
  Il giro va in senso orario visto dall'alto: continua la guardia di profilo, come un vero calcio girato.
- Effetti solo grafici: scintille d'impatto, lampo bianco e tremolio leggero sui colpi forti, sfera di energia tra le
  mani, onda che parte in avanti, scia ciano degli arti; niente pause sul tempo (le lotte non si allungano); spenti
  con "riduci movimento".
- Correzioni al corpo trovate provando: in un salto il bacino sale e scende con i piedi (prima atterrava prima di loro
  e piegava le gambe); il ginocchio in aria segue il lato naturale della gamba (prima poteva girarsi passando da
  davanti a dietro); un piede che passa da davanti a dietro il bacino (o il contrario) gira sotto di esso ad arco,
  la gamba che si piega, invece di attraversarlo; il tallone d'appoggio vicino alla gamba tesa sale piano; un braccio
  che arriva quasi teso ci arriva morbido (prima il gomito scattava dritto); il gomito tra due posizioni gira dal lato
  giusto anche quando le due sono lontane; la fascia segue il corpo nei giri e nelle capriole; la capriola non lascia
  più Ren storto.
- 38 animazioni nuove (103 in tutto): 15 combinazioni, 12 mosse speciali, 5 calci, 2 difese, 4 movimenti; impatti
  aggiunti anche alle 65 di prima.
- Verificate fotogramma per fotogramma (tutte, scivolamento massimo 0,8 mm) e guardate una per una.

## Quinta tappa (14/11): l'Anteprima
Denis: "scusa ho eliminato per sbaglio due movimenti puoi rimetterli e darmi l'anteprima in modo diverso? che tipo
faccio successivo e mi parte l'animazione successiva? che cosi è troppo macchinoso". Scelte di Claude:
- Nel database le 103 animazioni erano tutte intatte (controllate una per una): la cancellazione era rimasta solo
  nella copia sul telefono. Una copia di un'animazione di Claude rimasta su un dispositivo non va mai sopra
  l'originale: si riapre quello del database.
- Le animazioni di Claude non si cambiano per sbaglio: la prima modifica a una crea la copia di Denis in «Le tue»
  («… (mia)»), che prende quella modifica e le successive; l'originale resta com'era.
- L'Anteprima è la vista con cui si apre la pagina (l'editor solo se non c'è niente da guardare): Ren in grande, a
  destra gruppo e posizione («Calci · 3 di 17»), nome, descrizione, «Successiva» (grande, arancione), «Precedente»,
  Pausa (ferma il fotogramma, effetti compresi), Elenco, Modifica. Nell'Anteprima nessun tasto cambia
  un'animazione. Ordine: quello dell'elenco, e alla fine si ricomincia. Tasti ≥ 44 px. Tastiera: frecce sinistra e
  destra, spazio, L, M; controller: croce o dorsali, A, X, Y; Start passa tra Anteprima ed editor.
- Nell'editor il tasto «Animazioni» diventa «Anteprima» (l'elenco è nell'Anteprima; si chiama Anteprima e non
  Guarda per non confondersi con «Guardia»).
- L'elenco aperto non si ridisegna più a ogni posa (un tocco poteva cadere su un tasto appena sostituito).

## La prima versione (sostituita)

### Cosa faceva
- Lo stesso Ren della pagina delle tecniche (kit.js): stessa guardia, stesso risolutore (gambe e braccia per IK,
  piedi in appoggio fermi). La guardia è la prima posa di ogni animazione nuova.
- Punti da trascinare: testa (il punto davanti al viso, dove guarda), busto (piega), bacino (sposta e abbassa),
  mani, gomiti (da che parte si piega il braccio), piedi (sposta e alza), tutto il corpo. Si muovono nel piano di
  fronte alla camera; per la profondità si gira la vista (Lato, 3/4, Fronte o trascinando).
- Per mano: Pugno / Socchiusa / Aperta, Palmo giù / di lato / su, Polso avanti / dritto / indietro. Per piede:
  tallone giù / su / punta, punta in aria tesa / normale / a martello, gira. Busto, bacino e testa: gira.
- Pose numerate in alto, + Posa (copia quella corrente), Elimina, Riproduci (24 fotogrammi da una posa all'altra,
  tenuta sull'ultima, poi torna alla prima), Annulla, Guardia, Note (nome, note per Claude, nota della posa,
  animazioni salvate, nuova animazione, copia dei dati).
- Tocco, mouse, tastiera e controller per tutto (tasti e controller nel suggerimento in basso).
- Salvataggio automatico nel database della pagina (raccolta `animazioni`, un documento per animazione, con la
  legenda dei numeri dentro), e su questo dispositivo quando il database non c'è.

### Scelte di Claude
- Mani nel riferimento del busto (il busto che gira o si piega porta le braccia con sé); gomito come "lato verso
  cui si piega" (mai un punto: così muovere la mano dopo non lo ribalta); rotazione del palmo e piega del polso
  misurate sull'avambraccio, quindi sempre definite.
- Zoom con due dita: si avvicina alla parte scelta, non al viso.
- Grafica sola: lo stato del combattimento non cambia; costo per fotogramma +0,02 ms rispetto alla guardia.

## Per dopo (non costruito)
- Linea del tempo con i fotogrammi (approccio B), se le note non bastano.
- Altre posizioni pronte se servono (es. spazzata), su richiesta di Denis.
- Mosse speciali come tasti nella pagina (oggi solo nelle animazioni di Claude): giro, capriola, effetti.
- Anteprima «di fila»: ogni animazione una volta, poi da sola la successiva.
- Specchiare una posa; eliminare un'animazione salvata.
